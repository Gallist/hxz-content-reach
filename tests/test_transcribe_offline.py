"""Offline contract for scripts/transcribe.py: it must never download a model.

Two layers, no real model / GPU / network involved:

1. AST: every ``WhisperModel(...)`` construction in the script passes
   ``local_files_only=True`` (so a missing cache raises instead of downloading).
2. Execution: a stub ``faster_whisper`` module records the constructor kwargs and
   the resolved ``HF_HOME`` each time the script builds a model. This proves the
   CUDA attempt AND the CPU fallback are both offline, and that ``XHS_HF_HOME``
   overrides a pre-existing ``HF_HOME``.
"""
import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'scripts' / 'transcribe.py'

# A stand-in for faster_whisper.WhisperModel: records what it was called with,
# then fails, so the script never reaches ffmpeg / numpy / a real model.
STUB = '''
import json, os

_RECORD = os.environ['XHS_TEST_RECORD']


def _log(payload):
    with open(_RECORD, 'a', encoding='utf-8') as f:
        f.write(json.dumps(payload) + '\\n')


class WhisperModel:
    def __init__(self, model, **kwargs):
        _log({'model': model, 'kwargs': kwargs, 'HF_HOME': os.environ.get('HF_HOME')})
        raise RuntimeError('stub: refusing to load a real model')
'''


class AstOfflineTests(unittest.TestCase):
    def test_every_whispermodel_call_is_local_files_only(self):
        tree = ast.parse(SRC.read_text(encoding='utf-8'))
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and getattr(n.func, 'id', None) == 'WhisperModel']
        # Two explicit call sites: the CUDA attempt and the CPU fallback.
        self.assertGreaterEqual(len(calls), 2, 'expected explicit cuda + cpu construction')
        for call in calls:
            keywords = {k.arg: k.value for k in call.keywords}
            self.assertIn('local_files_only', keywords, ast.unparse(call))
            literal = keywords['local_files_only']
            self.assertIsInstance(literal, ast.Constant, ast.unparse(call))
            self.assertTrue(literal.value, ast.unparse(call))


class ExecutionOfflineTests(unittest.TestCase):
    def _run(self, cwd, xhs_hf_home=None, hf_home=None):
        record = Path(cwd, 'records.ndjson')
        stubdir = Path(cwd, 'stub')
        stubdir.mkdir()
        (stubdir / 'faster_whisper.py').write_text(STUB, encoding='utf-8')
        audio = Path(cwd, 'audio.wav')
        audio.write_bytes(b'')
        out = Path(cwd, 'out.txt')

        env = dict(os.environ)
        env.pop('XHS_HF_HOME', None)
        env.pop('HF_HOME', None)
        if xhs_hf_home is not None:
            env['XHS_HF_HOME'] = xhs_hf_home
        if hf_home is not None:
            env['HF_HOME'] = hf_home
        env['XHS_TEST_RECORD'] = str(record)
        env['PYTHONPATH'] = str(stubdir)

        result = subprocess.run([sys.executable, str(SRC), str(audio), str(out)],
                                capture_output=True, text=True, env=env, cwd=cwd, timeout=120)
        rows = [json.loads(line) for line in record.read_text(encoding='utf-8').splitlines() if line.strip()]
        return result, rows

    def test_both_attempts_are_offline_and_xhs_hf_home_wins(self):
        with tempfile.TemporaryDirectory() as d:
            result, rows = self._run(d, xhs_hf_home='X:/xhs-cache', hf_home='X:/global-cache')
        self.assertEqual(len(rows), 2, f'cuda + cpu attempts expected; stdout={result.stdout!r} stderr={result.stderr[-500:]!r}')
        for row in rows:
            self.assertIs(row['kwargs'].get('local_files_only'), True)
            self.assertEqual(row['HF_HOME'], 'X:/xhs-cache')  # XHS_HF_HOME overrides HF_HOME

    def test_missing_local_model_error_is_explicit(self):
        with tempfile.TemporaryDirectory() as d:
            result, _ = self._run(d, xhs_hf_home='X:/xhs-cache')
        combined = result.stdout + result.stderr
        self.assertIn('local_files_only', combined)
        self.assertIn('不会', combined)  # "不会联网下载"
        self.assertIn('XHS_WHISPER_MODEL', combined)

    def test_existing_hf_home_kept_when_xhs_unset(self):
        with tempfile.TemporaryDirectory() as d:
            _, rows = self._run(d, hf_home='X:/global-cache')
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row['HF_HOME'], 'X:/global-cache')

    def test_default_cache_when_neither_set(self):
        with tempfile.TemporaryDirectory() as d:
            _, rows = self._run(d)
        self.assertTrue(rows)
        for row in rows:
            self.assertTrue(row['HF_HOME'].replace('\\', '/').endswith('hxz-content-reach/hf'),
                            row['HF_HOME'])


if __name__ == '__main__':
    unittest.main()
