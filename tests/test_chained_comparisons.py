import unittest

from compiler.diagnostics import SwarnaSyntaxError
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser


def parse(source: str) -> None:
    Parser(Lexer(source)).parse_program()


class TestChainedComparisons(unittest.TestCase):
    def test_two_comparisons_are_rejected(self):
        with self.assertRaises(SwarnaSyntaxError) as raised:
            parse("let x = 1 < 2 < 3")
        self.assertIn("cannot be chained", raised.exception.message)
        self.assertIsNotNone(raised.exception.span)

    def test_print_argument_chain_is_rejected(self):
        with self.assertRaises(SwarnaSyntaxError) as raised:
            parse("print(1 < 2 < 3)")
        self.assertIn("cannot be chained", raised.exception.message)

    def test_mixed_comparison_operators_are_rejected(self):
        with self.assertRaises(SwarnaSyntaxError) as raised:
            parse("let x = 1 < 2 == true")
        self.assertIn("cannot be chained", raised.exception.message)

    def test_parenthesized_comparisons_are_accepted(self):
        parse("let x = (1 < 2) && (2 < 3)")


if __name__ == "__main__":
    unittest.main()
