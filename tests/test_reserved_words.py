import unittest

from compiler.diagnostics import SwarnaSyntaxError
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser


def parse(source: str) -> None:
    Parser(Lexer(source)).parse_program()


class TestReservedWordNames(unittest.TestCase):
    def test_keyword_as_binding_name(self):
        with self.assertRaises(SwarnaSyntaxError) as raised:
            parse("let if = 1")
        self.assertIn("reserved keyword", raised.exception.message)
        self.assertIn("'if'", raised.exception.message)

    def test_keyword_as_function_name(self):
        with self.assertRaises(SwarnaSyntaxError) as raised:
            parse("fn let() { 1 }")
        self.assertIn("reserved keyword", raised.exception.message)

    def test_keyword_as_parameter_name(self):
        with self.assertRaises(SwarnaSyntaxError) as raised:
            parse("fn f(else) { 1 }")
        self.assertIn("reserved keyword", raised.exception.message)

    def test_keyword_as_loop_variable(self):
        with self.assertRaises(SwarnaSyntaxError) as raised:
            parse("for while in [1] { print(1) }")
        self.assertIn("reserved keyword", raised.exception.message)

    def test_keyword_as_catch_name(self):
        with self.assertRaises(SwarnaSyntaxError) as raised:
            parse('try { throw "x" } catch return { print(1) }')
        self.assertIn("reserved keyword", raised.exception.message)

    def test_normal_identifier_still_works(self):
        parse("let value = 1 fn other(count) { count }")


if __name__ == "__main__":
    unittest.main()
