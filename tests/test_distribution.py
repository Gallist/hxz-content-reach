"""Structural distribution guard for the publishable project.

This file deliberately does NOT contain the real private identifiers -- not in
plaintext and not base64/hashed "hidden" form. Encoding a real id inside the
project's own test just moves the leak; it does not remove it. The exact-value
check against the real Feishu base/table/record ids, the real note id and the
author/title case data lives in an EXTERNAL acceptance script kept outside the
repository (under the operator's scratch dir), where a private value is allowed
to exist.

What stays here is the structural contract: no local runtime artifact, browser
login profile, media/transcript file, or machine-private absolute path default
is shipped, and ``config.example.json`` only carries obvious placeholders.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {'.git', '__pycache__', '.testtmp', '.work', '.pytest_cache'}

REQUIRED_FILES = [
    'SKILL.md',
    'config.example.json',
    '.gitignore',
    'requirements.txt',
    'scripts/xhs_pipeline.py',
    'scripts/xhs_config.py',
    'scripts/transcribe.py',
    'scripts/punctuate.py',
    'scripts/product_rules.py',
    'scripts/xhs_collect.mjs',
    'docs/CONFIGURATION.md',
    'docs/PROVENANCE.md',
    'tests/test_distribution.py',
]

# Local runtime artifacts that must never be published.
FORBIDDEN_NAMES = {'config.local.json', '.env', 'write-state.json',
                   'verify.ndjson', 'verify.manifest.json', 'DevToolsActivePort'}
FORBIDDEN_SUFFIXES = {'.mp4', '.wav', '.webp', '.onnx', '.pt', '.ckpt', '.bin'}
CHROME_PROFILE_NAMES = {'Login Data', 'Cookies', 'Local State'}

# drive:\Users\..., drive:\AI\..., drive:\home\... -- a private machine path.
PRIVATE_PATH_RE = re.compile(r'[A-Za-z]:[\\/](?:Users|AI|home)[\\/]', re.IGNORECASE)


def iter_files():
    for path in ROOT.rglob('*'):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        yield path


class DistributionTests(unittest.TestCase):
    def test_required_publishable_files_exist(self):
        for rel in REQUIRED_FILES:
            self.assertTrue((ROOT / rel).exists(), rel)

    def test_no_local_runtime_artifacts(self):
        offenders = []
        for path in iter_files():
            if path.name in FORBIDDEN_NAMES or path.name in CHROME_PROFILE_NAMES:
                offenders.append(str(path.relative_to(ROOT)))
            elif path.suffix.lower() in FORBIDDEN_SUFFIXES:
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [], f'runtime/private artifacts present: {offenders}')

    def test_example_config_base_and_table_are_placeholders(self):
        data = json.loads((ROOT / 'config.example.json').read_text(encoding='utf-8'))
        for key in ('base_token', 'table_id'):
            value = data.get(key)
            self.assertIsInstance(value, str, msg=key)
            self.assertTrue(value.startswith('YOUR_') or re.fullmatch(r'<[^<>]+>', value),
                            f'{key} must be an obvious placeholder, got {value!r}')

    def test_sources_have_no_machine_private_absolute_paths(self):
        offenders = []
        for pattern in ('*.py', '*.mjs'):
            for path in (ROOT / 'scripts').rglob(pattern):
                if PRIVATE_PATH_RE.search(path.read_text(encoding='utf-8')):
                    offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [], f'machine-private absolute path defaults: {offenders}')


if __name__ == '__main__':
    unittest.main()
