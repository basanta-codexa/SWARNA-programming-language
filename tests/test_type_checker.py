import unittest

from compiler.diagnostics import SourceSpan, SwarnaSemanticError
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.checker import Binding, FunctionSignature, Type, TypeChecker, type_of_value


def check(
    source: str,
    initial_bindings: dict[str, Binding] | None = None,
    initial_functions: dict[str, FunctionSignature] | None = None,
) -> TypeChecker:
    program = Parser(Lexer(source)).parse_program()
    checker = TypeChecker(initial_bindings, initial_functions)
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


class TestFunctions(unittest.TestCase):
    def test_annotated_function_call_type(self):
        checker = check("fn add(a: Int, b: Int) -> Int { a + b } let x = add(2, 3)")
        self.assertEqual(checker.functions["add"].parameters, (Type.INT, Type.INT))
        self.assertIs(checker.functions["add"].return_type, Type.INT)
        self.assertIs(checker.env["x"].type, Type.INT)

    def test_function_call_before_declaration(self):
        checker = check("let x = add(2, 3) fn add(a: Int, b: Int) -> Int { a + b }")
        self.assertIs(checker.env["x"].type, Type.INT)

    def test_unannotated_parameters_are_unknown(self):
        checker = check("fn add(a, b) { a + b } let x = add(1, 2)")
        self.assertEqual(checker.functions["add"].parameters, (Type.UNKNOWN, Type.UNKNOWN))
        self.assertIs(checker.functions["add"].return_type, Type.UNKNOWN)
        self.assertIs(checker.env["x"].type, Type.UNKNOWN)

    def test_annotated_return_type_allows_unknown_body(self):
        checker = check("fn add(a, b) -> Int { a + b } let x = add(1, 2)")
        self.assertIs(checker.functions["add"].return_type, Type.INT)
        self.assertIs(checker.env["x"].type, Type.INT)

    def test_unannotated_return_type_is_inferred(self):
        checker = check("fn add(a: Int, b: Int) { a + b } let x = add(2, 3)")
        self.assertIs(checker.functions["add"].return_type, Type.INT)
        self.assertIs(checker.env["x"].type, Type.UNKNOWN)

    def test_return_type_inferred_from_if_expression(self):
        checker = check("fn abs(x: Int) { if x < 0 { -x } else { x } }")
        self.assertIs(checker.functions["abs"].return_type, Type.INT)

    def test_function_body_type_error(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "cannot combine Int and String"):
            check('fn f(x: Int) -> Int { x + "a" }')

    def test_return_type_mismatch(self):
        with self.assertRaises(SwarnaSemanticError) as raised:
            check('fn bad() -> Int { "a" }')
        self.assertEqual(raised.exception.span, SourceSpan(1, 19, 3))
        self.assertIn("declares Int but its body produces String", str(raised.exception))

    def test_argument_count_mismatch(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "expects 2 arguments, got 1"):
            check("fn add(a: Int, b: Int) -> Int { a + b } let x = add(1)")

    def test_argument_type_mismatch(self):
        with self.assertRaisesRegex(
            SwarnaSemanticError,
            "Argument 2 of 'add' must be Int, got String",
        ):
            check('fn add(a: Int, b: Int) -> Int { a + b } let x = add(1, "a")')

    def test_float_argument_to_int_parameter_is_rejected(self):
        with self.assertRaisesRegex(
            SwarnaSemanticError,
            "Argument 1 of 'f' must be Int, got Float",
        ):
            check("fn f(x: Int) -> Int { x } let y = f(1.0)")

    def test_undefined_function(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "Undefined function 'missing'"):
            check("let x = missing(1)")

    def test_bare_function_name_must_be_called(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "Function 'f' must be called"):
            check("fn f() -> Int { 1 } let x = f")

    def test_assignment_to_function_is_rejected(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "Cannot assign to function 'f'"):
            check("fn f() -> Int { 1 } f = 2")

    def test_duplicate_function_declaration(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "Duplicate function 'f'"):
            check("fn f() -> Int { 1 } fn f() -> Int { 2 }")

    def test_duplicate_parameter(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "Duplicate parameter 'a' in function 'f'"):
            check("fn f(a: Int, a: Int) -> Int { a }")

    def test_unknown_parameter_type(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "Unknown type 'Number'"):
            check("fn f(a: Number) -> Int { 1 }")

    def test_unknown_return_type(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "Unknown type 'Number'"):
            check("fn f() -> Number { 1 }")

    def test_nested_function_declaration_is_rejected(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "only allowed at the top level"):
            check("if true { fn f() -> Int { 1 } }")

    def test_function_body_scope_does_not_leak(self):
        checker = check("fn f() -> Int { let local = 1 local } let x = f()")
        self.assertNotIn("local", checker.env)
        self.assertIs(checker.env["x"].type, Type.INT)

    def test_function_reads_global_binding(self):
        checker = check("let base = 10 fn add_base(x: Int) -> Int { x + base } let y = add_base(5)")
        self.assertIs(checker.env["y"].type, Type.INT)

    def test_function_assignment_to_global_is_checked_as_local_copy(self):
        checker = check("let x = 1 fn bump() -> Int { x = x + 1 x } let y = bump()")
        self.assertIs(checker.env["x"].type, Type.INT)
        self.assertIs(checker.env["y"].type, Type.INT)

    def test_function_assignment_to_global_wrong_type_is_rejected(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "Cannot assign String to Int"):
            check('let x = 1 fn bump() -> Int { x = "a" x }')

    def test_function_local_const_assignment_is_rejected(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "const binding 'x'"):
            check("fn f() -> Int { const x = 1 x = 2 x }")

    def test_function_call_inside_function(self):
        checker = check(
            "fn inc(x: Int) -> Int { x + 1 } "
            "fn twice(x: Int) -> Int { inc(inc(x)) } "
            "let y = twice(1)"
        )
        self.assertIs(checker.env["y"].type, Type.INT)

    def test_mutual_recursion_with_annotations(self):
        checker = check(
            "fn is_even(n: Int) -> Bool { if n == 0 { true } else { is_odd(n - 1) } } "
            "fn is_odd(n: Int) -> Bool { if n == 0 { false } else { is_even(n - 1) } } "
            "let x = is_even(4)"
        )
        self.assertIs(checker.env["x"].type, Type.BOOL)

    def test_function_call_in_condition_is_checked(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "`if` condition must be Bool, got Int"):
            check("fn one() -> Int { 1 } if one() { print(1) }")

    def test_function_name_conflicts_with_variable(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "Cannot bind a variable named 'f'"):
            check("fn f() -> Int { 1 } let f = 1")

    def test_function_name_conflicts_with_initial_binding(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "Cannot declare function 'f'"):
            check("fn f() -> Int { 1 }", initial_bindings={"f": Binding(Type.INT)})

    def test_parameter_name_conflicts_with_function(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "Parameter 'f' conflicts with a function name"):
            check("fn f(f: Int) -> Int { f }")

    def test_print_function_name_is_reserved(self):
        with self.assertRaisesRegex(SwarnaSemanticError, "Function name 'print' is reserved"):
            check("fn print(x: Int) -> Int { x }")

    def test_initial_function_is_visible(self):
        checker = check(
            "let x = f()",
            initial_functions={"f": FunctionSignature("f", (), Type.INT)},
        )
        self.assertIs(checker.env["x"].type, Type.INT)

    def test_failed_function_check_does_not_commit_signature(self):
        checker = TypeChecker()
        program = Parser(Lexer("fn f() -> Int { 1 } let x = missing")).parse_program()
        with self.assertRaises(SwarnaSemanticError):
            checker.check(program)
        self.assertNotIn("f", checker.functions)

    def test_function_can_be_redefined_across_checks(self):
        checker = TypeChecker()
        checker.check(Parser(Lexer("fn f() -> Int { 1 }")).parse_program())
        checker.check(Parser(Lexer("fn f() -> Int { 2 } let x = f()")).parse_program())
        self.assertIs(checker.env["x"].type, Type.INT)


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
