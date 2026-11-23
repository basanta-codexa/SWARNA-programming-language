import unittest

from compiler.diagnostics import SwarnaSemanticError
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.checker import Binding, Type, TypeChecker


def check(source: str, checker: TypeChecker | None = None) -> TypeChecker:
    target = checker or TypeChecker()
    target.check(Parser(Lexer(source)).parse_program())
    return target


class TestDuplicateDeclarations(unittest.TestCase):
    def test_const_then_let_is_rejected(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "already declared"):
            check("const x = 1 let x = 2")

    def test_let_twice_is_rejected(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "already declared"):
            check("let x = 1 let x = 2")

    def test_duplicate_map_key_is_rejected(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "Duplicate map key"):
            check('let m = { "a": 1, "a": 2 }')

    def test_distinct_numeric_keys_are_accepted(self):
        check('let m = { 1: "a", 1.0: "b" }')

    def test_existing_binding_can_be_redeclared_in_a_new_check(self):
        checker = TypeChecker({"x": Binding(Type.INT)})
        check("let x = 2", checker)


if __name__ == "__main__":
    unittest.main()
