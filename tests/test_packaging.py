import re
import unittest
from pathlib import Path

import swarna


ROOT = Path(__file__).resolve().parents[1]


class TestPackaging(unittest.TestCase):
    def test_build_backend_supports_pep639_license_fields(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("setuptools>=77", text)
        self.assertIn('license = "MIT"', text)
        self.assertIn('license-files = ["LICENSE"]', text)

    def test_version_has_one_source(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('dynamic = ["version"]', text)
        self.assertIn('version = {attr = "swarna.__version__"}', text)
        self.assertIsNone(re.search(r'(?m)^version\s*=\s*"', text))
        self.assertTrue(re.fullmatch(r"\d+\.\d+\.\d+", swarna.__version__))

    def test_ci_builds_and_smoke_tests_package(self):
        text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("python -m build", text)
        self.assertIn("python -m pip install dist/*.whl", text)
        self.assertIn("swarna --version", text)
        self.assertIn('swarna --run "print(1 + 2)"', text)

    def test_console_script_is_declared(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("swarna = \"swarna.__main__:main\"", text)


if __name__ == "__main__":
    unittest.main()
