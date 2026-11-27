import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TestSuiteLayout(unittest.TestCase):
    def test_no_test_classes_after_unittest_main(self):
        for path in sorted((ROOT / "tests").rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            marker = text.rfind('if __name__ == "__main__":')
            if marker == -1:
                continue
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertNotIn("class Test", text[marker:])


if __name__ == "__main__":
    unittest.main()
