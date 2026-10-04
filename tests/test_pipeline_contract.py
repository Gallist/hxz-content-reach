import ast
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'scripts' / 'xhs_pipeline.py'


class OutputContractTests(unittest.TestCase):
    def test_punctuation_output_is_captured(self):
        tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
        candidates = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'run':
                if 'punctuate.py' in ast.unparse(node):
                    candidates.append(node)
        self.assertEqual(len(candidates), 1)
        self.assertTrue(any(k.arg == 'capture_output' and isinstance(k.value, ast.Constant) and k.value.value is True
                            for k in candidates[0].keywords))


class AttachmentFailureTests(unittest.TestCase):
    def test_attachment_failure_aborts(self):
        src = SOURCE.read_text(encoding='utf-8')
        tree = ast.parse(src)
        self.assertNotIn("print('封面上传失败'", src)
        self.assertNotIn('print("封面上传失败', src)
        raises = [ast.unparse(n) for n in ast.walk(tree)
                  if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call)
                  and getattr(n.exc.func, 'id', None) == 'SystemExit']
        self.assertTrue(any('记录已创建但封面上传失败' in r for r in raises))


if __name__ == '__main__':
    unittest.main()
