import unittest

from compiler.lexer.lexer import Lexer
from compiler.lexer.tokens import TokenType


class TestLexer(unittest.TestCase):
    def test_tokenize_let_binding(self):
        lexer = Lexer("let x = 42")
        tokens = lexer.tokenize()
        self.assertEqual(
            [(t.type, t.value) for t in tokens],
            [
                (TokenType.KEYWORD_LET, "let"),
                (TokenType.IDENTIFIER, "x"),
                (TokenType.EQUAL, "="),
                (TokenType.INTEGER, "42"),
                (TokenType.EOF, ""),
            ],
        )

    def test_skips_whitespace(self):
        lexer = Lexer("  let   x =  42  ")
        tokens = lexer.tokenize()
        self.assertEqual(tokens[0].type, TokenType.KEYWORD_LET)
        self.assertEqual(tokens[1].value, "x")
        self.assertEqual(tokens[3].value, "42")
        self.assertEqual(tokens[-1].type, TokenType.EOF)

    def test_identifier_not_keyword(self):
        lexer = Lexer("letter")
        tokens = lexer.tokenize()
        self.assertEqual(tokens[0].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[0].value, "letter")

    def test_unexpected_character(self):
        lexer = Lexer("let x @ 1")
        with self.assertRaises(SyntaxError):
            lexer.tokenize()

    def test_simple_expression_tokens(self):
        lexer = Lexer("x + y * (2 - 1)")
        tokens = lexer.tokenize()
        self.assertEqual(
            [(t.type, t.value) for t in tokens[:-1]],
            [
                (TokenType.IDENTIFIER, "x"),
                (TokenType.PLUS, "+"),
                (TokenType.IDENTIFIER, "y"),
                (TokenType.STAR, "*"),
                (TokenType.LPAREN, "("),
                (TokenType.INTEGER, "2"),
                (TokenType.MINUS, "-"),
                (TokenType.INTEGER, "1"),
                (TokenType.RPAREN, ")"),
            ],
        )
        self.assertEqual(tokens[-1].type, TokenType.EOF)

    def test_let_mut_binding(self):
        lexer = Lexer("let mut x = 42")
        tokens = lexer.tokenize()
        self.assertEqual(
            [(t.type, t.value) for t in tokens],
            [
                (TokenType.KEYWORD_LET, "let"),
                (TokenType.KEYWORD_MUT, "mut"),
                (TokenType.IDENTIFIER, "x"),
                (TokenType.EQUAL, "="),
                (TokenType.INTEGER, "42"),
                (TokenType.EOF, ""),
            ],
        )

    def test_float_literal(self):
        lexer = Lexer("3.14 0.5 42")
        tokens = lexer.tokenize()
        self.assertEqual(
            [(t.type, t.value) for t in tokens[:-1]],
            [
                (TokenType.FLOAT, "3.14"),
                (TokenType.FLOAT, "0.5"),
                (TokenType.INTEGER, "42"),
            ],
        )

    def test_string_literal(self):
        lexer = Lexer('"hello" "a\\"b"')
        tokens = lexer.tokenize()
        self.assertEqual(tokens[0].type, TokenType.STRING)
        self.assertEqual(tokens[0].value, "hello")
        self.assertEqual(tokens[1].type, TokenType.STRING)
        self.assertEqual(tokens[1].value, 'a"b')

    def test_unterminated_string(self):
        lexer = Lexer('"hello')
        with self.assertRaises(SyntaxError):
            lexer.tokenize()

    def test_bool_keywords(self):
        lexer = Lexer("true false")
        tokens = lexer.tokenize()
        self.assertEqual(
            [(t.type, t.value) for t in tokens[:-1]],
            [(TokenType.KEYWORD_TRUE, "true"), (TokenType.KEYWORD_FALSE, "false")],
        )

    def test_comparison_operators(self):
        lexer = Lexer("== != < <= > >= =")
        tokens = lexer.tokenize()
        self.assertEqual(
            [(t.type, t.value) for t in tokens[:-1]],
            [
                (TokenType.EQEQ, "=="),
                (TokenType.BANGEQ, "!="),
                (TokenType.LT, "<"),
                (TokenType.LTEQ, "<="),
                (TokenType.GT, ">"),
                (TokenType.GTEQ, ">="),
                (TokenType.EQUAL, "="),
            ],
        )

    def test_logical_operators(self):
        lexer = Lexer("! && ||")
        tokens = lexer.tokenize()
        self.assertEqual(
            [(t.type, t.value) for t in tokens[:-1]],
            [(TokenType.BANG, "!"), (TokenType.AMPAMP, "&&"), (TokenType.PIPEPIPE, "||")],
        )

    def test_if_else_braces(self):
        lexer = Lexer("if x { } else { }")
        tokens = lexer.tokenize()
        types = [t.type for t in tokens[:-1]]
        self.assertEqual(types, [
            TokenType.KEYWORD_IF, TokenType.IDENTIFIER, TokenType.LBRACE, TokenType.RBRACE,
            TokenType.KEYWORD_ELSE, TokenType.LBRACE, TokenType.RBRACE,
        ])

    def test_while_keyword(self):
        lexer = Lexer("while x < 10 { }")
        tokens = lexer.tokenize()
        self.assertEqual(tokens[0].type, TokenType.KEYWORD_WHILE)
        self.assertEqual(tokens[0].value, "while")


if __name__ == "__main__":
    unittest.main()
