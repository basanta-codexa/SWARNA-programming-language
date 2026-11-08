import unittest

from compiler.lexer.tokens import Token, TokenType


class TestTokens(unittest.TestCase):
    def test_keyword_let_name(self):
        self.assertTrue(hasattr(TokenType, "KEYWORD_LET"))
        self.assertEqual(TokenType.KEYWORD_LET.name, "KEYWORD_LET")

    def test_token_is_frozen(self):
        tok = Token(TokenType.IDENTIFIER, "x", 1, 5)
        with self.assertRaises(Exception):
            tok.value = "y"  # type: ignore[misc]

    def test_let_binding_token_sequence(self):
        tokens = [
            Token(TokenType.KEYWORD_LET, "let", 1, 1),
            Token(TokenType.IDENTIFIER, "x", 1, 5),
            Token(TokenType.EQUAL, "=", 1, 7),
            Token(TokenType.INTEGER, "42", 1, 9),
            Token(TokenType.EOF, "", 1, 11),
        ]
        self.assertEqual([t.type for t in tokens], [
            TokenType.KEYWORD_LET,
            TokenType.IDENTIFIER,
            TokenType.EQUAL,
            TokenType.INTEGER,
            TokenType.EOF,
        ])


if __name__ == "__main__":
    unittest.main()
