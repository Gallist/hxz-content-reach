"""Failure-recovery regression for cmd_push.

Only the external Feishu CLI boundary (xhs_pipeline.lark) is mocked; the real
cmd_push runs against a real workspace directory and real JSON state files.
Fixtures use the verified flat NDJSON shape (record_id + field names) and a
clearly synthetic note id.
"""
import io
import json
import os
import shutil
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import xhs_pipeline as pipe  # noqa: E402

import _support  # noqa: E402

RID = 'rec-test'
NID = 'abcdef0123456789abcdef01'  # synthetic 24-hex note id
BODY = '感谢邀请。\n\n今天讲十倍获客。'
NOTE = {
    'note_id': NID,
    'kind': '视频',
    'title': '标题X',
    'author': '作者X',
    'published': '2026-01-01 12:00',
    'clean_url': 'https://www.xiaohongshu.com/explore/' + NID,
    'collected_at': '2026-10-03 18:00',
    'tags': [],
    'counts': {'点赞': 28, '收藏': 47, '分享': 22},
}


def make_workspace(with_state, with_cover=True):
    wd = _support.make_temp_dir()
    Path(wd, 'note.json').write_text(json.dumps(NOTE, ensure_ascii=False), encoding='utf-8')
    Path(wd, 'reviewed.txt').write_text(BODY, encoding='utf-8')
    if with_cover:
        Path(wd, 'cover.jpg').write_bytes(b'cover-bytes')
    if with_state:
        Path(wd, 'write-state.json').write_text(
            json.dumps({'record_id': RID, 'status': 'written_unverified'}), encoding='utf-8')
    return wd


class FakeLark:
    """Stateful stand-in for pipe.lark. Writes the real NDJSON files it is asked for."""

    def __init__(self, dup_ids=(RID,), cover_after_upload=True, final_transcript=None,
                 attachment_ok=True):
        self.dup_ids = list(dup_ids)
        self.cover_after_upload = cover_after_upload
        self.final_transcript = final_transcript
        self.attachment_ok = attachment_ok
        self.calls = []
        self.uploaded = False

    def __call__(self, args, cwd):
        self.calls.append(list(args))
        sub = args[1]
        if sub == '+record-list':
            with open(os.path.join(cwd, 'dup.ndjson'), 'w', encoding='utf-8') as f:
                for rid in self.dup_ids:
                    f.write(json.dumps({'record_id': rid}, ensure_ascii=False) + '\n')
            return {'ok': True, 'data': {}}
        if sub == '+record-batch-create':
            return {'ok': True, 'data': {'record_id_list': [RID]}}
        if sub == '+record-batch-update':
            return {'ok': True, 'data': {}}
        if sub == '+record-upload-attachment':
            self.uploaded = True
            if self.attachment_ok:
                return {'ok': True, 'data': {}}
            return {'ok': False, 'code': 99999, 'msg': 'attachment fixture failure'}
        if sub == '+record-get':
            out = args[args.index('--output') + 1]
            row = {'record_id': RID, '标题': NOTE['title'], '作者': NOTE['author'],
                   '逐字稿': self.final_transcript if self.final_transcript is not None else BODY,
                   **NOTE['counts']}
            if self.uploaded and self.cover_after_upload:
                row['封面'] = [{'file_token': 'fixture'}]
            with open(os.path.join(cwd, out), 'w', encoding='utf-8') as f:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
            return {'ok': True, 'data': {}}
        return {'ok': False, 'raw': 'unexpected ' + sub}

    def subs(self):
        return [c[1] for c in self.calls]


class PushRecoveryTests(unittest.TestCase):
    def tearDown(self):
        for wd in getattr(self, '_dirs', []):
            shutil.rmtree(wd, ignore_errors=True)

    def _run(self, wd, fake):
        self._dirs = getattr(self, '_dirs', []) + [wd]
        buf = io.StringIO()
        with mock.patch.object(pipe, 'lark', fake), \
             mock.patch.object(pipe, 'BASE', 'base-test'), \
             mock.patch.object(pipe, 'TABLE', 'table-test'), \
             redirect_stdout(buf):
            pipe.cmd_push(wd)
        return buf.getvalue()

    def test_create_succeeds_but_attachment_failure_keeps_state(self):
        wd = make_workspace(with_state=False)
        fake = FakeLark(dup_ids=(), attachment_ok=False)
        with self.assertRaises(SystemExit):
            self._run(wd, fake)
        self.assertTrue(os.path.exists(wd))
        state = json.loads(Path(wd, 'write-state.json').read_text(encoding='utf-8'))
        self.assertEqual(state['record_id'], RID)
        self.assertEqual(state['status'], 'written_unverified')
        self.assertNotIn('+record-batch-create', fake.subs()[:1])  # only the create happened
        self.assertEqual(fake.subs().count('+record-batch-create'), 1)
        self.assertNotIn('+record-get', fake.subs())  # aborted before verification

    def test_recovery_updates_same_record_and_cleans_on_success(self):
        wd = make_workspace(with_state=True)
        fake = FakeLark()
        out = self._run(wd, fake)
        subs = fake.subs()
        self.assertNotIn('+record-batch-create', subs)
        self.assertEqual(subs.count('+record-batch-update'), 1)
        self.assertEqual(subs.count('+record-upload-attachment'), 1)
        self.assertFalse(os.path.exists(wd))  # cleaned only after verified
        parsed = json.loads(out.strip())
        self.assertEqual(parsed['action'], '恢复并验收入库')
        self.assertEqual(parsed['record_id'], RID)
        self.assertTrue(parsed['cleaned'])

    def test_recovery_readback_mismatch_keeps_workspace(self):
        wd = make_workspace(with_state=True)
        fake = FakeLark(final_transcript='短稿')
        with self.assertRaises(ValueError):
            self._run(wd, fake)
        self.assertTrue(os.path.exists(wd))
        self.assertTrue(os.path.exists(os.path.join(wd, 'write-state.json')))
        self.assertEqual(fake.subs().count('+record-batch-create'), 0)

    def test_recovery_rejects_record_not_matching_note(self):
        wd = make_workspace(with_state=True)
        fake = FakeLark(dup_ids=('rec-other',))
        with self.assertRaises(SystemExit):
            self._run(wd, fake)
        self.assertTrue(os.path.exists(wd))
        self.assertNotIn('+record-batch-update', fake.subs())

    def test_recovery_skips_upload_when_cover_present(self):
        wd = make_workspace(with_state=True)
        # cover already present on the remote row: no attachment call, still verified
        fake = FakeLark(cover_after_upload=True)
        fake.uploaded = True  # pretend the row already has a cover
        out = self._run(wd, fake)
        self.assertEqual(fake.subs().count('+record-upload-attachment'), 0)
        self.assertFalse(os.path.exists(wd))
        self.assertEqual(json.loads(out.strip())['record_id'], RID)


if __name__ == '__main__':
    unittest.main()
