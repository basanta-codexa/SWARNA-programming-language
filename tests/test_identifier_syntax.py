import unittest

from compiler.diagnostics import SwarnaSyntaxError
from compiler.lexer.lexer import Lexer


class TestIdentifierSyntax(unittest.TestCase):
    def test_ascii_identifiers_are_allowed(self):
        tokens = Lexer("let _x1 = 1").tokenize()
        values = [token.value for token in tokens]
        self.assertIn("_x1", values)

    def test_non_ascii_identifier_is_rejected(self):
        with self.assertRaises(SwarnaSyntaxError) as raised:
            Lexer("let café = 1").tokenize()
        self.assertIn("non-ASCII", raised.exception.message)
        self.assertEqual(raised.exception.span.column, 8)

    def test_non_ascii_standalone_character_is_rejected(self):
        with self.assertRaises(SwarnaSyntaxError) as raised:
            Lexer("let x = é").tokenize()
        self.assertIn("non-ASCII", raised.exception.message)


if __name__ == "__main__":
    unittest.main()
