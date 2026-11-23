import unittest

from compiler.diagnostics import SwarnaSemanticError
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.checker import TypeChecker


def check(source: str) -> None:
    TypeChecker().check(Parser(Lexer(source)).parse_program())


class TestDefiniteAssignment(unittest.TestCase):
    def test_declaration_in_only_one_if_branch_is_rejected(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "may not have been assigned"):
            check("if false { let x = 1 } print(x)")

    def test_declaration_in_both_if_branches_is_accepted(self):
        check("if true { let x = 1 } else { let x = 2 } print(x)")

    def test_declaration_in_loop_body_is_rejected(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "may not have been assigned"):
            check("let i = 0 while i < 1 { let x = 1 i = i + 1 } print(x)")

    def test_declaration_in_for_body_is_rejected(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "may not have been assigned"):
            check("for v in [1] { let x = 1 } print(x)")

    def test_try_body_declaration_is_rejected(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "may not have been assigned"):
            check('try { let x = 1 throw "e" } catch e { } print(x)')

    def test_assignment_after_unassigned_branch_makes_name_available(self):
        check("if false { let x = 1 } x = 2 print(x)")

    def test_function_body_uses_same_analysis(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "may not have been assigned"):
            check("fn f() -> Int { if false { let x = 1 } x }")


if __name__ == "__main__":
    unittest.main()
