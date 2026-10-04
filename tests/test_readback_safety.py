"""Readback may not accept stale files from a previous attempt."""
import gc
import io
import json
import shutil
import unittest
import warnings
from pathlib import Path
from contextlib import redirect_stdout
from unittest import mock
from test_push_recovery import pipe, make_workspace, FakeLark, RID, BODY, NOTE

class ReadbackSafetyTests(unittest.TestCase):
    def setUp(self):
        self.wd = make_workspace(with_state=False)
    def tearDown(self):
        shutil.rmtree(self.wd, ignore_errors=True)
    def test_failed_readback_cannot_accept_previous_file(self):
        stale = {'record_id': RID, **NOTE['counts']}
        Path(self.wd, 'verify.ndjson').write_text(json.dumps(stale)+'\n',encoding='utf-8')
        fake = FakeLark()
        def external(args, cwd):
            if args[1] == '+record-get':
                return {'ok': False, 'error': {'message':'network fixture failure'}}
            return fake(args, cwd)
        with mock.patch.object(pipe, 'lark', external), \
             mock.patch.object(pipe, 'BASE', 'base-test'), \
             mock.patch.object(pipe, 'TABLE', 'table-test'), \
             redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                pipe.cmd_push(self.wd)
        self.assertTrue(Path(self.wd).exists())
    def test_duplicate_push_releases_file_handles(self):
        fake = FakeLark()
        with warnings.catch_warnings(record=True) as records:
            warnings.simplefilter('always', ResourceWarning)
            with mock.patch.object(pipe, 'lark', fake), \
                 mock.patch.object(pipe, 'BASE', 'base-test'), \
                 mock.patch.object(pipe, 'TABLE', 'table-test'), \
                 redirect_stdout(io.StringIO()):
                pipe.cmd_push(self.wd)
            gc.collect()
        self.assertEqual([str(w.message) for w in records if issubclass(w.category, ResourceWarning)], [])

if __name__ == '__main__':
    unittest.main()
