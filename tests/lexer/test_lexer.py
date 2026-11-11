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

    def test_const_binding(self):
        lexer = Lexer("const x = 42")
        tokens = lexer.tokenize()
        self.assertEqual(
            [(t.type, t.value) for t in tokens],
            [
                (TokenType.KEYWORD_CONST, "const"),
                (TokenType.IDENTIFIER, "x"),
                (TokenType.EQUAL, "="),
                (TokenType.INTEGER, "42"),
                (TokenType.EOF, ""),
            ],
        )

    def test_mut_is_identifier(self):
        tokens = Lexer("mut").tokenize()
        self.assertEqual(tokens[0].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[0].value, "mut")

    def test_list_brackets(self):
        tokens = Lexer("[1, 2]").tokenize()
        self.assertEqual(
            [(t.type, t.value) for t in tokens],
            [
                (TokenType.LBRACKET, "["),
                (TokenType.INTEGER, "1"),
                (TokenType.COMMA, ","),
                (TokenType.INTEGER, "2"),
                (TokenType.RBRACKET, "]"),
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

    def test_division_operators(self):
        lexer = Lexer("7 // 2 / 3")
        tokens = lexer.tokenize()
        self.assertEqual(
            [(t.type, t.value) for t in tokens[:-1]],
            [
                (TokenType.INTEGER, "7"),
                (TokenType.SLASHSLASH, "//"),
                (TokenType.INTEGER, "2"),
                (TokenType.SLASH, "/"),
                (TokenType.INTEGER, "3"),
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

    def test_word_operators(self):
        lexer = Lexer("and or not")
        tokens = lexer.tokenize()
        self.assertEqual(
            [(t.type, t.value) for t in tokens[:-1]],
            [
                (TokenType.KEYWORD_AND, "and"),
                (TokenType.KEYWORD_OR, "or"),
                (TokenType.KEYWORD_NOT, "not"),
            ],
        )

    def test_word_operator_prefix_is_identifier(self):
        tokens = Lexer("android").tokenize()
        self.assertEqual(tokens[0].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[0].value, "android")

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

    def test_for_and_in_keywords(self):
        tokens = Lexer("for x in xs").tokenize()
        self.assertEqual(
            [(t.type, t.value) for t in tokens],
            [
                (TokenType.KEYWORD_FOR, "for"),
                (TokenType.IDENTIFIER, "x"),
                (TokenType.KEYWORD_IN, "in"),
                (TokenType.IDENTIFIER, "xs"),
                (TokenType.EOF, ""),
            ],
        )

    def test_semicolon(self):
        lexer = Lexer("let x = 1; let y = 2;")
        tokens = lexer.tokenize()
        types = [t.type for t in tokens]
        self.assertIn(TokenType.SEMICOLON, types)
        self.assertEqual(types.count(TokenType.SEMICOLON), 2)

    def test_function_tokens(self):
        lexer = Lexer("fn add(a: Int) -> Int { a }")
        tokens = lexer.tokenize()
        self.assertEqual(
            [(t.type, t.value) for t in tokens[:-1]],
            [
                (TokenType.KEYWORD_FN, "fn"),
                (TokenType.IDENTIFIER, "add"),
                (TokenType.LPAREN, "("),
                (TokenType.IDENTIFIER, "a"),
                (TokenType.COLON, ":"),
                (TokenType.IDENTIFIER, "Int"),
                (TokenType.RPAREN, ")"),
                (TokenType.ARROW, "->"),
                (TokenType.IDENTIFIER, "Int"),
                (TokenType.LBRACE, "{"),
                (TokenType.IDENTIFIER, "a"),
                (TokenType.RBRACE, "}"),
            ],
        )

    def test_minus_and_arrow_are_distinct(self):
        tokens = Lexer("-1 -> Int").tokenize()
        self.assertEqual(
            [(t.type, t.value) for t in tokens[:-1]],
            [
                (TokenType.MINUS, "-"),
                (TokenType.INTEGER, "1"),
                (TokenType.ARROW, "->"),
                (TokenType.IDENTIFIER, "Int"),
            ],
        )

    def test_fn_prefix_is_identifier(self):
        tokens = Lexer("fnord").tokenize()
        self.assertEqual(tokens[0].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[0].value, "fnord")

    def test_comma(self):
        tokens = Lexer("f(1, 2)").tokenize()
        self.assertIn(TokenType.COMMA, [t.type for t in tokens])


if __name__ == "__main__":
    unittest.main()
