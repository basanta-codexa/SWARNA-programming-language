import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESIGN = (ROOT / "docs" / "DESIGN_PRINCIPLES.md").read_text(encoding="utf-8")


class TestDesignPrinciples(unittest.TestCase):
    def test_stale_claims_are_removed(self):
        stale_phrases = [
            "`Result<T, E>` is available",
            "There is no iteration over ranges or strings yet",
            "Lists stay immutable",
            "branches are not unified yet",
            "no list mutation",
            "no definite-assignment analysis",
            "not every runtime storage context is coerced yet",
        ]
        for phrase in stale_phrases:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, DESIGN)

    def test_current_features_are_documented(self):
        current_phrases = [
            "not implemented yet",
            "`append(xs, value)`",
            "`start:end` slicing",
            "Definite-assignment analysis",
            "unify to `Float`",
            "`for key in map`",
            "fixed point before call sites are checked",
        ]
        for phrase in current_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, DESIGN)


if __name__ == "__main__":
    unittest.main()
