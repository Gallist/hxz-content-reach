import io
import json
import shutil
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from unittest import mock
from test_push_recovery import pipe, make_workspace, FakeLark

class EventualReadbackTests(unittest.TestCase):
    def test_first_read_old_then_current_is_verified(self):
        wd=make_workspace(with_state=False)
        fake=FakeLark()
        reads=[]
        def external(args,cwd):
            result=fake(args,cwd)
            if args[1]=='+record-get':
                reads.append(1)
                if len(reads)==1:
                    out=Path(cwd,args[args.index('--output')+1])
                    row=json.loads(out.read_text(encoding='utf-8'))
                    row['收藏']=46
                    out.write_text(json.dumps(row)+'\n',encoding='utf-8')
            return result
        try:
            with mock.patch.object(pipe,'lark',external),mock.patch.object(pipe,'BASE','base-test'), \
                 mock.patch.object(pipe,'TABLE','table-test'),mock.patch.object(pipe.time,'sleep'), \
                 redirect_stdout(io.StringIO()) as buf:
                pipe.cmd_push(wd)
            self.assertGreaterEqual(len(reads),2)
            self.assertEqual(json.loads(buf.getvalue())['action'],'已存在，只更新互动数据')
            self.assertFalse(Path(wd).exists())
        finally:
            shutil.rmtree(wd,ignore_errors=True)

    def test_pending_first_read_old_then_current_is_verified(self):
        wd=make_workspace(with_state=True)
        fake=FakeLark()
        fake.uploaded=True
        reads=[]
        def external(args,cwd):
            result=fake(args,cwd)
            if args[1]=='+record-get':
                reads.append(1)
                if len(reads)==1:
                    out=Path(cwd,args[args.index('--output')+1])
                    row=json.loads(out.read_text(encoding='utf-8'))
                    row['收藏']=46
                    out.write_text(json.dumps(row)+'\n',encoding='utf-8')
            return result
        try:
            with mock.patch.object(pipe,'lark',external),mock.patch.object(pipe,'BASE','base-test'), \
                 mock.patch.object(pipe,'TABLE','table-test'),mock.patch.object(pipe.time,'sleep'), \
                 redirect_stdout(io.StringIO()) as buf:
                pipe.cmd_push(wd)
            self.assertGreaterEqual(len(reads),2)
            self.assertEqual(json.loads(buf.getvalue())['action'],'恢复并验收入库')
            self.assertFalse(Path(wd).exists())
        finally:
            shutil.rmtree(wd,ignore_errors=True)

if __name__=='__main__':
    unittest.main()
