import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class SkillRenameTests(unittest.TestCase):
    def test_directory_and_frontmatter_use_new_name(self):
        self.assertEqual(ROOT.name, 'hxz-content-reach')
        self.assertRegex((ROOT/'SKILL.md').read_text(encoding='utf-8'), r'(?m)^name: hxz-content-reach$')

    def test_old_name_is_not_offered_as_a_live_trigger(self):
        files = [ROOT/'SKILL.md', *sorted((ROOT/'docs').glob('*.md'))]
        self.assertTrue(files)
        for file in files:
            self.assertIsNone(re.search(r'hxz-xiaohongshu-reach', file.read_text(encoding='utf-8')), str(file))

    def test_old_directory_is_not_a_second_installed_copy(self):
        self.assertFalse((ROOT.parent/'xiaohongshu-reach').exists())

if __name__=='__main__':
    unittest.main()
