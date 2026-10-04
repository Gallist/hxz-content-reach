import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from product_rules import douyin_note, platform_of, profile_debug_port  # noqa: E402

import _support  # noqa: E402


DETAIL = {
    'aweme_id': '7000000000000000001',
    'desc': '示例抖音文案 #职场 #AI',
    'create_time': 1790976887,
    'author': {'nickname': '示例作者'},
    'statistics': {'digg_count': 291, 'collect_count': 153, 'comment_count': 0, 'share_count': 47},
    'text_extra': [{'hashtag_name': '职场'}, {'hashtag_name': 'AI'}, {}],
    'video': {
        'origin_cover': {'url_list': ['https://c/cover.jpeg']},
        'play_addr': {'url_list': ['https://v/play']},
        'bit_rate': [
            {'format': 'mp4', 'bit_rate': 900, 'play_addr': {'url_list': ['https://v/900a', 'https://v/900b'], 'data_size': 9}},
            {'format': 'dash', 'bit_rate': 100, 'play_addr': {'url_list': ['https://v/dash']}},
            {'format': 'mp4', 'bit_rate': 300, 'play_addr': {'url_list': ['https://v/300']}},
        ],
    },
}


class PlatformTest(unittest.TestCase):
    def test_platform_detection(self):
        self.assertEqual(platform_of('复制打开抖音 https://v.douyin.com/EXAMPLE11/ UYm:/'), '抖音')
        self.assertEqual(platform_of('https://www.douyin.com/video/1'), '抖音')
        self.assertEqual(platform_of('http://xhslink.cn/o/abc'), '小红书')


class DouyinNoteTest(unittest.TestCase):
    def setUp(self):
        self.note = douyin_note(DETAIL)

    def test_core_fields(self):
        n = self.note
        self.assertEqual(n['platform'], '抖音')
        self.assertEqual(n['note_id'], '7000000000000000001')
        self.assertEqual(n['href'], 'https://www.douyin.com/video/7000000000000000001')
        self.assertEqual(n['title'], '示例抖音文案')
        self.assertEqual(n['author'], '示例作者')
        self.assertEqual(n['time'], 1790976887000)
        self.assertEqual(n['type'], 'video')
        self.assertEqual(n['tags'], ['职场', 'AI'])
        self.assertEqual(n['images'], ['https://c/cover.jpeg'])

    def test_counts_keep_zero(self):
        ia = self.note['interact']
        self.assertEqual((ia['likedCount'], ia['collectedCount'], ia['commentCount'], ia['shareCount']), (291, 153, 0, 47))

    def test_streams_mp4_only_low_bitrate_first_then_default(self):
        urls = [s['url'] for s in self.note['streams']]
        self.assertEqual(urls, ['https://v/300', 'https://v/900a', 'https://v/play'])
        self.assertEqual(self.note['streams'][1]['backup'], ['https://v/900b'])

    def test_title_falls_back_when_desc_only_hashtags(self):
        n = douyin_note({**DETAIL, 'desc': '#职场 #AI', 'preview_title': ''})
        self.assertEqual(n['title'], '')


class ProfilePortTest(unittest.TestCase):
    def test_reads_devtools_active_port(self):
        d = _support.make_temp_dir()
        try:
            self.assertIsNone(profile_debug_port(d))
            Path(d, 'DevToolsActivePort').write_text('63806\n/devtools/browser/x', encoding='utf-8')
            self.assertEqual(profile_debug_port(d), 63806)
            Path(d, 'DevToolsActivePort').write_text('junk', encoding='utf-8')
            self.assertIsNone(profile_debug_port(d))
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
