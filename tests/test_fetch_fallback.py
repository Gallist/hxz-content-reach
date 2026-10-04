"""Contract test for the browser-tool fallback (--note-json).

Verifies that fetch consumes a provided page JSON, never launches the fixed-port
Chrome, and emits pure parseable JSON that reports the existing record. Only the
external Feishu boundary is mocked; no network or browser is touched, and the
fixtures use synthetic ids.
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

# A synthetic share link: the real one the operator tested with is kept out of
# the repository (see tests/test_distribution.py) and checked externally.
URL = 'https://xhslink.cn/o/EXAMPLE0000'
NOTE_ID = 'abcdef0123456789abcdef01'  # synthetic 24-hex note id
NOTE = {
    'href': f'https://www.xiaohongshu.com/explore/{NOTE_ID}?xsec_token=abc&xsec_source=app_share',
    'note_id': NOTE_ID,
    'title': '标题', 'desc': '', 'type': 'video', 'author': '作者', 'time': 1790952023000,
    'interact': {'commentCount': '', 'shareCount': '22', 'likedCount': '28', 'collectedCount': '47'},
    'tags': [], 'images': [], 'duration': 601, 'streams': [],
}


class FetchFallbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = _support.make_temp_dir()
        self.src = os.path.join(self.tmp, 'page-source.json')
        Path(self.src).write_text(json.dumps(NOTE, ensure_ascii=False), encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_note_json_hits_existing_record_without_chrome(self):
        def fake_lark(args, cwd):
            if args[1] == '+record-list':
                Path(cwd, 'dup.ndjson').write_text(
                    json.dumps({'record_id': 'rec-test'}, ensure_ascii=False) + '\n', encoding='utf-8')
                return {'ok': True, 'data': {}}
            return {'ok': True, 'data': {}}

        buf = io.StringIO()
        with mock.patch.object(pipe, 'SCRATCH', self.tmp), \
             mock.patch.object(pipe, 'BASE', 'base-test'), \
             mock.patch.object(pipe, 'TABLE', 'table-test'), \
             mock.patch.object(pipe, 'lark', fake_lark), \
             mock.patch.object(pipe, 'ensure_chrome', side_effect=AssertionError('Chrome must not start')), \
             mock.patch.object(sys, 'argv', ['xhs_pipeline.py', 'fetch', URL, '--note-json', self.src]), \
             redirect_stdout(buf):
            pipe.cmd_fetch(URL)
        parsed = json.loads(buf.getvalue())  # stdout must be pure JSON
        self.assertEqual(parsed['existing_record'], ['rec-test'])
        self.assertEqual(parsed['note_id'], NOTE_ID)
        self.assertEqual(parsed['counts'], {'点赞': 28, '收藏': 47, '分享': 22, '评论': 0})


if __name__ == '__main__':
    unittest.main()
