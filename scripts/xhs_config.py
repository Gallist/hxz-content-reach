"""Central configuration for the Xiaohongshu -> Feishu reach pipeline.

Resolution order (highest priority first):

1. environment variables (``XHS_*``)
2. a JSON config file -- ``$XHS_CONFIG_FILE`` if set, else ``config.local.json``
   next to this project's root (git-ignored)
3. portable defaults / PATH lookup

No value is ever printed by this module: :func:`describe` reports presence and
length only. Nothing here performs network I/O, launches a browser, downloads a
model or installs a dependency. Missing required keys are reported by
:func:`require` at the moment a command needs them -- importing this module is
always safe and offline.
"""
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# logical key -> environment variable
ENV_KEYS = {
    'base_token': 'XHS_BASE_TOKEN',
    'table_id': 'XHS_TABLE_ID',
    'lark_cli': 'XHS_LARK_CLI',
    'whisper_python': 'XHS_WHISPER_PYTHON',
    'transcribe_script': 'XHS_TRANSCRIBE_SCRIPT',
    'punct_model': 'XHS_PUNCT_MODEL',
    'scratch_dir': 'XHS_SCRATCH_DIR',
    'chrome_path': 'XHS_CHROME_PATH',
    'chrome_profile': 'XHS_CHROME_PROFILE',
    'cdp_port': 'XHS_CDP_PORT',
    # optional, used only by scripts/transcribe.py
    'whisper_model': 'XHS_WHISPER_MODEL',
    'hf_home': 'XHS_HF_HOME',
}

# keys without which a real fetch/push must refuse to run
REQUIRED_FOR_NETWORK = ('base_token', 'table_id')

# core tools a real fetch/push run needs; doctor reports them as missing when
# unset OR pointing at a path that does not exist on disk.
CORE_TOOL_KEYS = ('lark_cli', 'whisper_python', 'transcribe_script', 'punct_model')

# Chrome is an OPTIONAL fallback: without it the browser-tool (--note-json) path
# is the only collection route, so its absence is a warning, not a failure.
OPTIONAL_TOOL_KEYS = ('chrome_path', 'chrome_profile')

PATH_KEYS = CORE_TOOL_KEYS + OPTIONAL_TOOL_KEYS

# The values shipped in config.example.json. A config that still holds them has
# not been filled in. Deliberately small and explicit -- no format policing.
_EXAMPLE_PLACEHOLDERS = frozenset({'YOUR_FEISHU_BASE_TOKEN', 'YOUR_FEISHU_TABLE_ID'})


def is_placeholder(value):
    """True for an empty, untouched example value, or an ``<...>`` stub."""
    text = str(value).strip()
    if not text:
        return True
    if text in _EXAMPLE_PLACEHOLDERS:
        return True
    return bool(re.fullmatch(r'<[^<>]+>', text))

_LAUNCHERS = {
    'lark_cli': ('lark-cli', 'lark-cli.cmd', 'lark-cli.exe'),
    'chrome_path': ('chrome', 'chrome.exe', 'google-chrome', 'chromium'),
}


class ConfigError(Exception):
    """Raised when a command needs configuration that is not set."""


def config_path(env=None, root=None):
    env = os.environ if env is None else env
    root = ROOT if root is None else Path(root)
    explicit = env.get('XHS_CONFIG_FILE')
    return Path(explicit) if explicit else root / 'config.local.json'


def _read_file(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        raise ConfigError(f'配置文件无法解析: {path}: {exc}')
    if not isinstance(data, dict):
        raise ConfigError(f'配置文件必须是 JSON 对象: {path}')
    return data


def _which(candidates):
    for name in candidates:
        found = shutil.which(name)
        if found:
            return found
    return None


def load(env=None, root=None):
    """Return the resolved configuration as a plain dict of non-empty values."""
    env = os.environ if env is None else env
    file_data = _read_file(config_path(env, root))
    cfg = {}
    for key, env_name in ENV_KEYS.items():
        raw = env.get(env_name)
        if raw is None or str(raw).strip() == '':
            raw = file_data.get(key)
        if raw is None or str(raw).strip() == '':
            continue
        cfg[key] = raw
    # PATH-based defaults (never installs anything)
    for key, candidates in _LAUNCHERS.items():
        if key not in cfg:
            found = _which(candidates)
            if found:
                cfg[key] = found
    if 'transcribe_script' not in cfg:
        cfg['transcribe_script'] = str(ROOT / 'scripts' / 'transcribe.py')
    if 'scratch_dir' not in cfg:
        cfg['scratch_dir'] = str(ROOT / '.work')
    if 'cdp_port' not in cfg:
        cfg['cdp_port'] = 9333
    try:
        cfg['cdp_port'] = int(cfg['cdp_port'])
    except (TypeError, ValueError):
        raise ConfigError(f"cdp_port 必须是整数: {cfg['cdp_port']!r}")
    return cfg


def require(cfg, keys=REQUIRED_FOR_NETWORK):
    """Raise :class:`ConfigError` naming every missing/placeholder key, else return ``cfg``."""
    missing = [k for k in keys if not cfg.get(k) or is_placeholder(cfg.get(k))]
    if missing:
        envs = '、'.join(ENV_KEYS[k] for k in missing)
        raise ConfigError(
            '缺少必需配置（或仍是示例占位值）: ' + '、'.join(missing) + '。'
            f'请设置环境变量 {envs}，或在 config.local.json 中填入真实值'
            '（可从 config.example.json 复制并替换 YOUR_* 占位符）。见 docs/CONFIGURATION.md。')
    return cfg


def describe(cfg=None, env=None, root=None):
    """Return an offline, secret-free summary for ``doctor``.

    Checks config presence and file existence only -- it does not prove a GPU
    works, a Feishu authorisation is valid, or a model is complete.
    """
    env = os.environ if env is None else env
    cfg = load(env, root) if cfg is None else cfg
    path = config_path(env, root)
    report = {
        'config_file': str(path),
        'config_file_exists': path.is_file(),
        'values': {},
        'missing_required': [k for k in REQUIRED_FOR_NETWORK if not cfg.get(k) or is_placeholder(cfg.get(k))],
        'missing_tools': [],
        'warnings': [],
    }
    for key in ENV_KEYS:
        if key not in cfg:
            report['values'][key] = None
            continue
        value = cfg[key]
        if key in ('base_token', 'table_id'):
            report['values'][key] = f'set(len={len(str(value))})'
        else:
            report['values'][key] = str(value)
    # Core tools: unset or a path that does not exist on disk => not ready.
    for key in CORE_TOOL_KEYS:
        value = cfg.get(key)
        if not value or not Path(str(value)).exists():
            report['missing_tools'].append(key)
    # Chrome is optional: absent/nonexistent only downgrades to the fallback route.
    chrome_ok = bool(cfg.get('chrome_path')) and Path(str(cfg['chrome_path'])).exists()
    if not chrome_ok:
        report['warnings'].append(
            '未检测到可用的 Chrome（chrome_path）：标准采集需要带窗口 Chrome；'
            '未配置时只能走 browser_exec 备用路径（fetch --note-json），不能声称具备自动采集。')
    return report
