"""Unit coverage for WeChat Channels adapter; live smoke is a separate gate."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from wechat_channels import validate_link,parse_metadata,media_download,fetch

SAMPLE={
    "description":"示例标题",
    "author":"示例作者","created_at":1793323117,
    "h264_url":"https://finder.video.qq.com/251/sample",
    "stats":{"likes":"253","comments":"89","forwards":"1.7万","favorites":None},
}

class ChannelsContractTests(unittest.TestCase):
    def test_share_link(self):
        clean,vid=validate_link(" https://weixin.qq.com/sph/Sample123?extra=1 ")
        self.assertEqual(clean,"https://weixin.qq.com/sph/Sample123")
        self.assertEqual(vid,"Sample123")

    def test_reject_untrusted_or_malformed_urls(self):
        for src in ("https://evil.example/sph/Sample123",
                    "http://weixin.qq.com/sph/Sample123",
                    "https://weixin.qq.com/sph/../../private",
                    "https://weixin.qq.com/sph/"):
            with self.subTest(src=src),self.assertRaises(ValueError):
                validate_link(src)

    def test_stats_mapped_with_unknown_as_null(self):
        data=parse_metadata("https://weixin.qq.com/sph/Sample123",SAMPLE)
        self.assertEqual(data["likes"],253)
        self.assertEqual(data["forwards"],17000)
        self.assertIsNone(data["favorites"])
        self.assertEqual(data["published_at"],"2026-10-30T09:18:37+08:00")

    def test_reject_off_platform_download_host(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):
                media_download("https://evil.example/video.mp4",Path(t)/"video.mp4")

    def test_metadata_only_preserves_absence_of_media(self):
        with tempfile.TemporaryDirectory() as t:
            with patch("wechat_channels.resolve",return_value=SAMPLE):
                result=fetch("https://weixin.qq.com/sph/Sample123",t,True)
            folder=Path(result["output_dir"])
            self.assertTrue((folder/"metadata.json").exists())
            self.assertFalse((folder/"video.mp4").exists())
            self.assertFalse((folder/"transcript.txt").exists())
            self.assertIsNone(json.loads((folder/"metadata.json").read_text(encoding="utf8"))["favorites"])

    def test_main_pipeline_routes_videohao_without_chrome(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from xhs_pipeline import cmd_fetch
        from product_rules import platform_of
        link="https://weixin.qq.com/sph/Sample123"
        self.assertEqual(platform_of(link),"视频号")
        stdout=StringIO()
        with patch("wechat_channels.fetch",return_value={"platform":"视频号","work_id":"Sample123"}) as cap:
            with patch("xhs_pipeline.ensure_chrome") as browser:
                with redirect_stdout(stdout):
                    cmd_fetch(link)
                browser.assert_not_called()
                cap.assert_called_once_with(link)
        self.assertEqual(json.loads(stdout.getvalue())["work_id"],"Sample123")

    def test_missing_media_url_cannot_be_marked_success(self):
        with tempfile.TemporaryDirectory() as t:
            with patch("wechat_channels.resolve",return_value={**SAMPLE,"h264_url":None}):
                with self.assertRaises(RuntimeError):
                    fetch("https://weixin.qq.com/sph/Sample123",t,no_transcribe=True)

if __name__=="__main__":unittest.main()
