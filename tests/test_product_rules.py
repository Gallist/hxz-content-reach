import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import product_rules as rules

import _support  # noqa: E402


class CountsTests(unittest.TestCase):
    def test_missing_comment_is_zero(self):
        self.assertEqual(
            rules.counts_from_page({'likedCount': '28', 'commentCount': ''}),
            {'点赞': 28, '评论': 0},
        )
        for value in (None, '', '   '):
            with self.subTest(value=value):
                self.assertEqual(rules.counts_from_page({'commentCount': value}), {'评论': 0})
        self.assertEqual(rules.counts_from_page({'commentCount': '12'}), {'评论': 12})
        self.assertEqual(rules.counts_from_page({'likedCount': None, 'shareCount': ''}), {'评论': 0})

    def test_explicit_zero_is_preserved(self):
        self.assertEqual(rules.counts_from_page({'commentCount': '0'}), {'评论': 0})
        self.assertEqual(rules.counts_from_page({'commentCount': 0}), {'评论': 0})

    def test_abbreviations_are_supported(self):
        self.assertEqual(rules.counts_from_page({'likedCount': '1.2万'}), {'点赞': 12000, '评论': 0})

    def test_unknown_display_is_omitted(self):
        self.assertEqual(rules.counts_from_page({'likedCount': '赞'}), {'评论': 0})


class RemarksTests(unittest.TestCase):
    def test_source_limitations_are_written(self):
        text = rules.make_remark({'点赞': 28, '收藏': 47, '分享': 22}, '封面大字')
        self.assertIn('未做AI全文校对', text)
        self.assertIn('评论未显示', text)
        self.assertIn('标题来源：封面大字', text)


class VerificationTests(unittest.TestCase):
    def test_exact_record_passes(self):
        row = {'record_id': 'rec-test', '标题': '标题', '作者': '作者',
               '逐字稿': '全文', '点赞': 28, '封面': [{'file_token': 'fixture-only'}]}
        rules.verify_record(row, 'rec-test', {'点赞': 28},
                            {'标题': '标题', '作者': '作者', '逐字稿': '全文'}, True)

    def test_missing_cover_fails(self):
        with self.assertRaisesRegex(ValueError, '封面'):
            rules.verify_record({'record_id': 'rec-test'}, 'rec-test', {}, {}, True)

    def test_changed_transcript_fails(self):
        with self.assertRaisesRegex(ValueError, '逐字稿'):
            rules.verify_record({'record_id': 'rec-test', '逐字稿': '短稿'},
                                'rec-test', {}, {'逐字稿': '全文'}, False)

    def test_wrong_record_id_fails(self):
        with self.assertRaisesRegex(ValueError, 'record_id'):
            rules.verify_record({'record_id': 'other'}, 'rec-test', {}, {}, False)

    def test_duplicate_stats_does_not_require_new_body(self):
        rules.verify_record({'record_id': 'rec-test', '点赞': 28},
                            'rec-test', {'点赞': 28}, {}, False)


class WriteStateTests(unittest.TestCase):
    def test_saved_state_is_readable(self):
        import json
        import shutil
        wd = _support.make_temp_dir()
        try:
            rules.save_write_state(wd, 'rec-test')
            state = json.loads((Path(wd) / 'write-state.json').read_text(encoding='utf-8'))
            self.assertEqual(state['record_id'], 'rec-test')
            self.assertEqual(state['status'], 'written_unverified')
        finally:
            shutil.rmtree(wd, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
