import unittest

from compiler.diagnostics import SwarnaSemanticError
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.checker import Type, TypeChecker


def check(source: str) -> TypeChecker:
    checker = TypeChecker()
    checker.check(Parser(Lexer(source)).parse_program())
    return checker


class TestFunctionOrderIndependence(unittest.TestCase):
    def test_invalid_forward_call_is_rejected_in_both_orders(self):
        first = 'fn a() { b() + 1 } fn b() { "s" } print(a())'
        second = 'fn b() { "s" } fn a() { b() + 1 } print(a())'
        for source in (first, second):
            with self.assertRaises(SwarnaSemanticError):
                check(source)

    def test_valid_forward_call_is_inferred_in_both_orders(self):
        first = "fn a() { b() + 1 } fn b() { 2 } print(a())"
        second = "fn b() { 2 } fn a() { b() + 1 } print(a())"
        for source in (first, second):
            checker = check(source)
            self.assertIs(checker.functions["a"].return_type, Type.INT)
            self.assertIs(checker.functions["b"].return_type, Type.INT)

    def test_mutual_unannotated_recursion_converges_in_both_orders(self):
        first = "fn a() { b() } fn b() { a() } print(a())"
        second = "fn b() { a() } fn a() { b() } print(a())"
        for source in (first, second):
            checker = check(source)
            self.assertIs(checker.functions["a"].return_type, Type.UNKNOWN)
            self.assertIs(checker.functions["b"].return_type, Type.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
