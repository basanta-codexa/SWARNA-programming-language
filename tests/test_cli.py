import unittest

from swarna.__main__ import lex_source, parse_source


class TestCLIHelpers(unittest.TestCase):
    def test_lex_source(self):
        out = lex_source("let x = 42")
        self.assertIn("KEYWORD_LET 'let'", out)
        self.assertIn("INTEGER '42'", out)
        self.assertIn("EOF ''", out)

    def test_parse_source(self):
        out = parse_source("let x = 42")
        self.assertIn("LetStatement", out)
        self.assertIn("IntegerLiteral", out)
        self.assertIn("value=42", out)


if __name__ == "__main__":
    unittest.main()
