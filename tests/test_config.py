"""Configuration contract: env > config file > PATH defaults.

Fully offline: no network, no browser, no Feishu.
"""
import json
import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import xhs_config  # noqa: E402

import _support  # noqa: E402


def _write_cfg(data, name='config.local.json'):
    d = _support.make_temp_dir()
    p = Path(d, name)
    p.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    return d, str(p)


class ConfigResolutionTests(unittest.TestCase):
    def test_missing_file_is_not_fatal(self):
        cfg = xhs_config.load(env={})
        self.assertNotIn('base_token', cfg)
        self.assertNotIn('table_id', cfg)

    def test_config_file_is_loaded(self):
        d, p = _write_cfg({'base_token': 'file-base', 'table_id': 'file-table'})
        try:
            cfg = xhs_config.load(env={'XHS_CONFIG_FILE': p})
            self.assertEqual(cfg['base_token'], 'file-base')
            self.assertEqual(cfg['table_id'], 'file-table')
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_default_path_is_config_local_json(self):
        d, _ = _write_cfg({'base_token': 'root-base'})
        try:
            cfg = xhs_config.load(env={}, root=Path(d))
            self.assertEqual(cfg['base_token'], 'root-base')
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_env_overrides_file(self):
        d, p = _write_cfg({'base_token': 'file-base', 'table_id': 'file-table'})
        try:
            cfg = xhs_config.load(env={'XHS_CONFIG_FILE': p, 'XHS_TABLE_ID': 'env-table'})
            self.assertEqual(cfg['base_token'], 'file-base')  # not overridden
            self.assertEqual(cfg['table_id'], 'env-table')    # env wins
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_every_documented_env_var_is_honoured(self):
        env = {
            'XHS_BASE_TOKEN': 'b', 'XHS_TABLE_ID': 't', 'XHS_LARK_CLI': 'l',
            'XHS_WHISPER_PYTHON': 'w', 'XHS_TRANSCRIBE_SCRIPT': 'ts',
            'XHS_PUNCT_MODEL': 'pm', 'XHS_SCRATCH_DIR': 'sd',
            'XHS_CHROME_PATH': 'cp', 'XHS_CHROME_PROFILE': 'cpf', 'XHS_CDP_PORT': '1234',
        }
        cfg = xhs_config.load(env=env)
        for key, value in {'base_token': 'b', 'table_id': 't', 'lark_cli': 'l', 'whisper_python': 'w',
                           'transcribe_script': 'ts', 'punct_model': 'pm', 'scratch_dir': 'sd',
                           'chrome_path': 'cp', 'chrome_profile': 'cpf'}.items():
            self.assertEqual(cfg[key], value)
        self.assertEqual(cfg['cdp_port'], 1234)
        self.assertIsInstance(cfg['cdp_port'], int)


class DefaultsTests(unittest.TestCase):
    def test_portable_defaults(self):
        cfg = xhs_config.load(env={})
        self.assertTrue(cfg['transcribe_script'].endswith('transcribe.py'))
        self.assertEqual(cfg['cdp_port'], 9333)
        self.assertTrue(cfg['scratch_dir'])


class RequireTests(unittest.TestCase):
    def test_require_reports_missing_keys(self):
        with self.assertRaises(xhs_config.ConfigError) as ctx:
            xhs_config.require({'base_token': '', 'table_id': ''})
        msg = str(ctx.exception)
        self.assertIn('base_token', msg)
        self.assertIn('table_id', msg)

    def test_require_passes_when_present(self):
        cfg = {'base_token': 'b', 'table_id': 't'}
        self.assertEqual(xhs_config.require(cfg), cfg)

    def test_require_rejects_example_placeholders(self):
        # The untouched config.example.json values must not look "configured".
        for bad in ('YOUR_FEISHU_BASE_TOKEN', 'YOUR_FEISHU_TABLE_ID', '<YOUR_BASE_TOKEN>'):
            with self.subTest(value=bad):
                cfg = {'base_token': 'realbase', 'table_id': 'realtable'}
                key = 'base_token' if 'BASE' in bad or 'base' in bad else 'table_id'
                cfg[key] = bad
                with self.assertRaises(xhs_config.ConfigError):
                    xhs_config.require(cfg)


class DescribeToolTests(unittest.TestCase):
    def test_describe_flags_unset_core_tools(self):
        real_script = str(Path(xhs_config.ROOT, 'scripts', 'transcribe.py'))
        report = xhs_config.describe(cfg={'transcribe_script': real_script}, env={})
        for key in ('lark_cli', 'whisper_python', 'punct_model'):
            self.assertIn(key, report['missing_tools'])
        self.assertNotIn('transcribe_script', report['missing_tools'])

    def test_describe_flags_configured_but_missing_paths(self):
        cfg = {'lark_cli': 'C:/virtual/lark', 'whisper_python': 'C:/virtual/python.exe',
               'transcribe_script': 'C:/virtual/transcribe.py', 'punct_model': 'C:/virtual/model.onnx'}
        report = xhs_config.describe(cfg=cfg, env={})
        for key in xhs_config.CORE_TOOL_KEYS:
            self.assertIn(key, report['missing_tools'])

    def test_describe_warns_when_chrome_absent_without_failing(self):
        report = xhs_config.describe(cfg={}, env={})
        joined = ' '.join(report['warnings'])
        self.assertIn('browser_exec', joined)
        self.assertNotIn('chrome_path', report['missing_tools'])  # optional fallback, not a core failure

    def test_describe_marks_example_placeholder_required(self):
        report = xhs_config.describe(cfg={'base_token': 'YOUR_FEISHU_BASE_TOKEN', 'table_id': 'YOUR_FEISHU_TABLE_ID'}, env={})
        self.assertIn('base_token', report['missing_required'])
        self.assertIn('table_id', report['missing_required'])


if __name__ == '__main__':
    unittest.main()
