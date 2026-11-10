import unittest

from compiler.diagnostics import SourceSpan, SwarnaSemanticError
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.checker import Binding, Type, TypeChecker, type_of_value


def check(source: str, initial_bindings: dict[str, Binding] | None = None) -> TypeChecker:
    program = Parser(Lexer(source)).parse_program()
    checker = TypeChecker(initial_bindings)
    checker.check(program)
    return checker


class TestTypeInference(unittest.TestCase):
    def test_literals(self):
        checker = check('let i = 1 let f = 1.5 let s = "x" let b = true')
        self.assertIs(checker.env["i"].type, Type.INT)
        self.assertIs(checker.env["f"].type, Type.FLOAT)
        self.assertIs(checker.env["s"].type, Type.STRING)
        self.assertIs(checker.env["b"].type, Type.BOOL)

    def test_arithmetic(self):
        checker = check(
            "let a = 1 + 2 "
            "let b = 1 + 2.0 "
            "let c = 1.0 * 2 "
            "let d = 7 / 2 "
            "let e = 7 // 2"
        )
        self.assertIs(checker.env["a"].type, Type.INT)
        self.assertIs(checker.env["b"].type, Type.FLOAT)
        self.assertIs(checker.env["c"].type, Type.FLOAT)
        self.assertIs(checker.env["d"].type, Type.FLOAT)
        self.assertIs(checker.env["e"].type, Type.INT)

    def test_string_concatenation(self):
        checker = check('let s = "a" + "b"')
        self.assertIs(checker.env["s"].type, Type.STRING)

    def test_comparisons(self):
        checker = check(
            "let a = 1 == 1 "
            "let b = 1 != 2 "
            "let c = 1 < 2 "
            "let d = 1.0 >= 2 "
            'let e = "a" < "b"'
        )
        for name in "abcde":
            self.assertIs(checker.env[name].type, Type.BOOL)

    def test_logical(self):
        checker = check("let a = !false let b = true && false let c = true || false")
        for name in "abc":
            self.assertIs(checker.env[name].type, Type.BOOL)

    def test_if_expression(self):
        checker = check(
            "let a = if true { 1 } else { 2 } "
            "let b = if true { 1.0 } else { 2.0 } "
            'let c = if true { "a" } else { "b" } '
            "let d = if true { true } else { false }"
        )
        self.assertIs(checker.env["a"].type, Type.INT)
        self.assertIs(checker.env["b"].type, Type.FLOAT)
        self.assertIs(checker.env["c"].type, Type.STRING)
        self.assertIs(checker.env["d"].type, Type.BOOL)

    def test_assignment_keeps_type(self):
        checker = check("let x = 1 x = 2")
        self.assertIs(checker.env["x"].type, Type.INT)

    def test_division_by_zero_is_not_a_type_error(self):
        check("let a = 1 / 0 let b = 1 // 0")

    def test_print_accepts_any_type(self):
        check('print(1) print(1.5) print("a") print(true)')


class TestSemanticErrors(unittest.TestCase):
    def test_undefined_name(self):
        with self.assertRaises(SwarnaSemanticError) as raised:
            check("let y = x + 1")
        self.assertEqual(raised.exception.span, SourceSpan(1, 9, 1))
        self.assertIn("Undefined name 'x'", str(raised.exception))

    def test_undefined_assignment(self):
        with self.assertRaises(SwarnaSemanticError) as raised:
            check("x = 1")
        self.assertEqual(raised.exception.span, SourceSpan(1, 1, 1))

    def test_const_assignment(self):
        with self.assertRaises(SwarnaSemanticError) as raised:
            check("const x = 1 x = 2")
        self.assertEqual(raised.exception.span, SourceSpan(1, 13, 1))
        self.assertIn("const binding 'x'", str(raised.exception))

    def test_assignment_type_mismatch(self):
        with self.assertRaises(SwarnaSemanticError) as raised:
            check('let x = 1 x = "a"')
        self.assertEqual(raised.exception.span, SourceSpan(1, 15, 3))
        self.assertIn("Cannot assign String to Int", str(raised.exception))

    def test_plus_type_mismatch(self):
        with self.assertRaises(SwarnaSemanticError) as raised:
            check('let x = 1 + "a"')
        self.assertEqual(raised.exception.span, SourceSpan(1, 11, 1))
        self.assertIn("`+` cannot combine Int and String", str(raised.exception))

    def test_bool_arithmetic_is_rejected(self):
        with self.assertRaises(SwarnaSemanticError):
            check("let x = true + 1")

    def test_numeric_operators_reject_strings(self):
        for source in ('let x = "a" - 1', 'let x = "a" * 2', 'let x = "a" / 2'):
            with self.subTest(source=source):
                with self.assertRaises(SwarnaSemanticError):
                    check(source)

    def test_integer_division_requires_ints(self):
        with self.assertRaises(SwarnaSemanticError) as raised:
            check("let x = 1.0 // 2")
        self.assertEqual(raised.exception.span, SourceSpan(1, 13, 2))
        self.assertIn("`//` requires Int operands", str(raised.exception))

    def test_equality_requires_compatible_types(self):
        with self.assertRaises(SwarnaSemanticError):
            check('let x = 1 == "a"')

    def test_ordered_comparison_requires_numbers_or_strings(self):
        with self.assertRaises(SwarnaSemanticError):
            check("let x = true < false")

    def test_logical_requires_bools(self):
        with self.assertRaises(SwarnaSemanticError) as raised:
            check("let x = 1 && true")
        self.assertEqual(raised.exception.span, SourceSpan(1, 9, 1))
        self.assertIn("`&&` requires Bool", str(raised.exception))

    def test_not_requires_bool(self):
        with self.assertRaises(SwarnaSemanticError) as raised:
            check("let x = !1")
        self.assertEqual(raised.exception.span, SourceSpan(1, 9, 1))

    def test_unary_minus_requires_number(self):
        with self.assertRaises(SwarnaSemanticError) as raised:
            check('let x = -"a"')
        self.assertEqual(raised.exception.span, SourceSpan(1, 9, 1))

    def test_if_condition_requires_bool(self):
        with self.assertRaises(SwarnaSemanticError) as raised:
            check("if 1 { print(1) }")
        self.assertEqual(raised.exception.span, SourceSpan(1, 4, 1))
        self.assertIn("`if` condition must be Bool", str(raised.exception))

    def test_while_condition_requires_bool(self):
        with self.assertRaises(SwarnaSemanticError) as raised:
            check("while 1 { print(1) }")
        self.assertEqual(raised.exception.span, SourceSpan(1, 7, 1))

    def test_if_expression_condition_requires_bool(self):
        with self.assertRaises(SwarnaSemanticError) as raised:
            check("let x = if 1 { 1 } else { 2 }")
        self.assertEqual(raised.exception.span, SourceSpan(1, 12, 1))

    def test_if_expression_branch_mismatch(self):
        with self.assertRaises(SwarnaSemanticError) as raised:
            check('let x = if true { 1 } else { "a" }')
        self.assertEqual(raised.exception.span, SourceSpan(1, 30, 3))
        self.assertIn("`if` branches have incompatible types", str(raised.exception))

    def test_int_and_float_branches_are_not_unified(self):
        with self.assertRaises(SwarnaSemanticError):
            check("let x = if true { 1 } else { 2.0 }")


class TestBlockExpressions(unittest.TestCase):
    def test_block_branch_infers_final_value(self):
        checker = check("let x = if true { let y = 1 y + 2 } else { let y = 3 y + 4 }")
        self.assertIs(checker.env["x"].type, Type.INT)

    def test_block_branch_checks_statements(self):
        with self.assertRaises(SwarnaSemanticError) as raised:
            check("let x = if true { let y = missing y } else { 0 }")
        self.assertIn("Undefined name 'missing'", str(raised.exception))

    def test_block_branch_assignment_type_is_checked(self):
        with self.assertRaises(SwarnaSemanticError):
            check('let x = if true { let y = 1 y = "a" y } else { 0 }')

    def test_block_branch_const_assignment_is_checked(self):
        with self.assertRaises(SwarnaSemanticError):
            check("let x = if true { const y = 1 y = 2 y } else { 0 }")

    def test_block_branch_mismatch_points_at_value(self):
        with self.assertRaises(SwarnaSemanticError) as raised:
            check('let x = if true { let y = 1 y } else { "a" }')
        self.assertEqual(raised.exception.span, SourceSpan(1, 40, 3))
        self.assertIn("`if` branches have incompatible types", str(raised.exception))

    def test_block_branch_string_value_type(self):
        checker = check('let x = if true { let y = 1 "a" } else { "b" }')
        self.assertIs(checker.env["x"].type, Type.STRING)

    def test_block_branch_bindings_leak_into_outer_scope(self):
        checker = check("let x = if true { let y = 1 y } else { 0 }")
        self.assertIs(checker.env["y"].type, Type.INT)


class TestInitialBindings(unittest.TestCase):
    def test_existing_binding_is_visible(self):
        checker = check(
            "print(x + 1)",
            initial_bindings={"x": Binding(Type.INT)},
        )
        self.assertIs(checker.env["x"].type, Type.INT)

    def test_existing_const_binding_is_enforced(self):
        with self.assertRaises(SwarnaSemanticError) as raised:
            check(
                "x = 2",
                initial_bindings={"x": Binding(Type.INT, constant=True)},
            )
        self.assertIn("const binding 'x'", str(raised.exception))

    def test_failed_check_does_not_commit_bindings(self):
        checker = TypeChecker()
        program = Parser(Lexer("let x = 1 let y = missing")).parse_program()
        with self.assertRaises(SwarnaSemanticError):
            checker.check(program)
        self.assertNotIn("x", checker.env)

    def test_type_of_value_distinguishes_bool_from_int(self):
        self.assertIs(type_of_value(True), Type.BOOL)
        self.assertIs(type_of_value(False), Type.BOOL)
        self.assertIs(type_of_value(1), Type.INT)
        self.assertIs(type_of_value(1.0), Type.FLOAT)
        self.assertIs(type_of_value("a"), Type.STRING)
        self.assertIs(type_of_value(object()), Type.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
