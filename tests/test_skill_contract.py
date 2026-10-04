"""Contract tests for the single-video -> Feishu product documentation.

Reads the real SKILL.md and docs/CONFIGURATION.md on disk. These prove the
documented contract text is present and internally consistent. They do NOT
prove that a future agent session obeys the contract -- that gate needs a
fresh-session real-link run, which is tracked outside these tests. No real
Feishu target or sample note id is asserted here: the target lives in local
config only.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'SKILL.md'
CONFIG_DOC = ROOT / 'docs' / 'CONFIGURATION.md'
VERIFY_DOC = ROOT / 'docs' / 'VERIFICATION.md'


class SkillEntryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SKILL.read_text(encoding='utf-8')

    def test_trigger_is_documented(self):
        self.assertIn('/hxz-content-reach', self.text)
        self.assertNotIn('@hxz-content-reach', self.text)

    def test_note_json_fallback_is_documented(self):
        self.assertIn('--note-json', self.text)

    def test_push_entry_point_is_documented(self):
        self.assertIn('xhs_pipeline.py push', self.text)

    def test_default_defers_ai_rewrite_of_transcript(self):
        self.assertIn('不再让 AI 重写全文', self.text)

    def test_link_plus_skill_is_ingestion_authorization(self):
        self.assertIn('视为授权', self.text)
        self.assertIn('再次询问确认', self.text)

    def test_missing_counts_stay_empty(self):
        self.assertIn('缺失互动数字留空', self.text)
        self.assertIn('评论数未显示时写 0', self.text)

    def test_user_chrome_must_not_be_killed(self):
        self.assertIn('禁止结束用户浏览器进程', self.text)

    def test_points_to_configuration_doc(self):
        self.assertIn('docs/CONFIGURATION.md', self.text)

    def test_default_flow_does_not_ask_for_save_location(self):
        default_flow = self.text.split('## 非默认', 1)[0]
        self.assertNotIn('问保存到哪里', default_flow)
        self.assertNotIn('使用当前工作区', default_flow)

    def test_description_advertises_video_to_feishu(self):
        frontmatter = self.text.split('---', 2)[1]
        self.assertIn('飞书', frontmatter)
        self.assertIn('视频', frontmatter)

    def test_uses_skill_dir_relative_paths(self):
        self.assertIn('SKILL_DIR', self.text)


class ConfigDocContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = CONFIG_DOC.read_text(encoding='utf-8')

    def test_documents_target_keys_not_values(self):
        self.assertIn('base_token', self.text)
        self.assertIn('table_id', self.text)
        self.assertIn('XHS_BASE_TOKEN', self.text)
        self.assertIn('XHS_TABLE_ID', self.text)

    def test_config_file_contract(self):
        self.assertIn('config.local.json', self.text)
        self.assertIn('XHS_CONFIG_FILE', self.text)


class VerificationDocContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = VERIFY_DOC.read_text(encoding='utf-8')

    def test_title_fallback_order(self):
        self.assertIn('封面大字', self.text)
        self.assertIn('正文首句', self.text)

    def test_missing_counts_left_blank(self):
        self.assertIn('留空', self.text)

    def test_does_not_claim_zero_cost(self):
        self.assertIn('不调用云端全文校对', self.text)
        self.assertNotIn('零成本', self.text)

    def test_does_not_claim_fixed_total_runtime(self):
        self.assertIn('不是未来整条链路的固定耗时', self.text)

    def test_documents_acceptance_readback(self):
        self.assertIn('record-get', self.text)

    def test_documents_browser_fallback(self):
        self.assertIn('browser_exec', self.text)

    def test_doctor_and_note_json_documented(self):
        self.assertIn('doctor', self.text)
        self.assertIn('--note-json', self.text)


if __name__ == '__main__':
    unittest.main()
