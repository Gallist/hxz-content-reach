"""Doctor / help contract: offline diagnostics, no collection, no writes.

Doctor is a *file-existence and config-presence* check only. It never claims a
path is a working GPU / authorised Feishu / complete model: an unset or
non-existent core tool path makes it exit non-zero, while the optional Chrome
fallback only produces a warning.
"""
import io
import os
import shutil
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import xhs_pipeline as pipe  # noqa: E402

import _support  # noqa: E402

# Core tool paths that do not exist on disk: doctor must not call this "ready".
VIRTUAL = {
    'XHS_BASE_TOKEN': 'FAKEbase0000000000000000',
    'XHS_TABLE_ID': 'tblFAKE0000000001',
    'XHS_LARK_CLI': 'C:/virtual/lark-cli.cmd',
    'XHS_WHISPER_PYTHON': 'C:/virtual/venv/Scripts/python.exe',
    'XHS_TRANSCRIBE_SCRIPT': 'C:/virtual/transcribe.py',
    'XHS_PUNCT_MODEL': 'C:/virtual/punct/model.onnx',
    'XHS_CHROME_PATH': 'C:/virtual/Chrome/chrome.exe',
    'XHS_CHROME_PROFILE': 'C:/virtual/chrome-profile',
    'XHS_CDP_PORT': '9333',
}


class DoctorTests(unittest.TestCase):
    def tearDown(self):
        for d in getattr(self, '_dirs', []):
            shutil.rmtree(d, ignore_errors=True)

    def _temp(self):
        d = _support.make_temp_dir()
        self._dirs = getattr(self, '_dirs', []) + [d]
        return d

    def _isolated_env(self, extra=None):
        d = self._temp()
        env = {'XHS_CONFIG_FILE': str(Path(d, 'does-not-exist.json'))}
        env.update(extra or {})
        return env

    def _ready_env(self, with_chrome=False):
        """base/table set and every core tool path exists on disk."""
        d = self._temp()
        env = {'XHS_CONFIG_FILE': str(Path(d, 'does-not-exist.json')),
               'XHS_BASE_TOKEN': 'FAKEbase0000000000000000',
               'XHS_TABLE_ID': 'tblFAKE0000000001'}
        for key, name in (('XHS_LARK_CLI', 'lark-cli.cmd'), ('XHS_WHISPER_PYTHON', 'python.exe'),
                          ('XHS_TRANSCRIBE_SCRIPT', 'transcribe.py'), ('XHS_PUNCT_MODEL', 'model.onnx')):
            p = Path(d, name)
            p.write_text('', encoding='utf-8')
            env[key] = str(p)
        if with_chrome:
            chrome = Path(d, 'chrome.exe')
            chrome.write_text('', encoding='utf-8')
            env['XHS_CHROME_PATH'] = str(chrome)
        return env

    def test_doctor_without_config_reports_missing_and_exits_nonzero(self):
        buf = io.StringIO()
        with mock.patch.dict(os.environ, self._isolated_env(), clear=True), redirect_stdout(buf):
            code = pipe.main(['doctor'])
        out = buf.getvalue()
        self.assertNotEqual(code, 0)
        self.assertIn('base_token', out)
        self.assertIn('table_id', out)

    def test_doctor_with_unconfigured_core_tools_exits_nonzero(self):
        buf = io.StringIO()
        env = self._isolated_env({'XHS_BASE_TOKEN': 'FAKEbase0000000000000000', 'XHS_TABLE_ID': 'tblFAKE0000000001'})
        with mock.patch.dict(os.environ, env, clear=True), redirect_stdout(buf):
            code = pipe.main(['doctor'])
        out = buf.getvalue()
        self.assertNotEqual(code, 0)
        for key in ('lark_cli', 'whisper_python', 'punct_model'):
            self.assertIn(key, out)

    def test_doctor_with_configured_but_missing_paths_exits_nonzero(self):
        buf = io.StringIO()
        with mock.patch.dict(os.environ, self._isolated_env(VIRTUAL), clear=True), redirect_stdout(buf):
            code = pipe.main(['doctor'])
        out = buf.getvalue()
        self.assertNotEqual(code, 0)
        for key in pipe.xhs_config.CORE_TOOL_KEYS:
            self.assertIn(key, out)
        self.assertIn('路径', out)

    def test_doctor_with_example_placeholders_exits_nonzero(self):
        buf = io.StringIO()
        env = self._isolated_env({'XHS_BASE_TOKEN': 'YOUR_FEISHU_BASE_TOKEN', 'XHS_TABLE_ID': 'YOUR_FEISHU_TABLE_ID'})
        with mock.patch.dict(os.environ, env, clear=True), redirect_stdout(buf):
            code = pipe.main(['doctor'])
        self.assertNotEqual(code, 0)
        self.assertIn('missing_required', buf.getvalue())

    def test_doctor_with_ready_paths_exits_zero_and_never_launches(self):
        buf = io.StringIO()
        with mock.patch.dict(os.environ, self._ready_env(with_chrome=True), clear=True), \
             mock.patch.object(pipe, 'ensure_chrome', side_effect=AssertionError('no chrome')), \
             mock.patch.object(pipe, 'lark', side_effect=AssertionError('no lark')), \
             redirect_stdout(buf):
            code = pipe.main(['doctor'])
        self.assertEqual(code, 0)
        self.assertIn('"missing_tools": []', buf.getvalue())

    def test_doctor_warns_when_chrome_absent_but_still_ready(self):
        buf = io.StringIO()
        with mock.patch.dict(os.environ, self._ready_env(with_chrome=False), clear=True), redirect_stdout(buf):
            code = pipe.main(['doctor'])
        out = buf.getvalue()
        self.assertEqual(code, 0)  # Chrome is an optional fallback, not a core tool
        self.assertIn('browser_exec', out)

    def test_doctor_never_starts_chrome_or_lark(self):
        with mock.patch.dict(os.environ, self._ready_env(with_chrome=True), clear=True), \
             mock.patch.object(pipe, 'ensure_chrome', side_effect=AssertionError('no chrome')), \
             mock.patch.object(pipe, 'lark', side_effect=AssertionError('no lark')), \
             redirect_stdout(io.StringIO()):
            self.assertEqual(pipe.main(['doctor']), 0)

    def test_help_does_not_run_the_pipeline(self):
        for args in ([], ['--help'], ['help']):
            with self.subTest(args=args):
                buf = io.StringIO()
                with mock.patch.object(pipe, 'cmd_fetch', side_effect=AssertionError('must not fetch')), redirect_stdout(buf):
                    code = pipe.main(args)
                self.assertEqual(code, 0)
                self.assertIn('fetch', buf.getvalue())

    def test_unknown_command_is_rejected(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            code = pipe.main(['frobnicate'])
        self.assertNotEqual(code, 0)
        self.assertIn('frobnicate', buf.getvalue())


if __name__ == '__main__':
    unittest.main()
