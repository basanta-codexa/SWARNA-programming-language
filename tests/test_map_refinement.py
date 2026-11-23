import unittest

from compiler.diagnostics import SwarnaSemanticError
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.checker import Type, TypeChecker


def check(source: str) -> TypeChecker:
    checker = TypeChecker()
    checker.check(Parser(Lexer(source)).parse_program())
    return checker


class TestEmptyMapRefinement(unittest.TestCase):
    def test_value_type_is_refined_from_first_assignment(self):
        checker = check('let m = {} m["a"] = 1 print(m["a"])')
        self.assertEqual(checker.env["m"].type.label, "Map[String, Int]")

    def test_second_value_of_a_different_type_is_rejected(self):
        with self.assertRaises(SwarnaSemanticError):
            check('let m = {} m["a"] = 1 m["b"] = "s"')

    def test_non_scalar_key_is_rejected(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "Map keys must be"):
            check("let m = {} m[[1]] = 2")

    def test_conflicting_key_types_are_rejected(self):
        with self.assertRaises(SwarnaSemanticError):
            check('let m = {} m[1] = 2 m["a"] = 3')

    def test_annotation_is_preserved(self):
        checker = check('let m: Map[String, Float] = {} m["a"] = 1.0')
        self.assertEqual(checker.env["m"].type, Type.map_of(Type.STRING, Type.FLOAT))
