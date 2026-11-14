import json
import tempfile
import unittest
from pathlib import Path

from compiler.diagnostics import SourceSpan, SwarnaNameError, SwarnaRuntimeError, SwarnaTypeError, SwarnaZeroDivisionError, render_diagnostic
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from runtime.interpreter import Interpreter


def run(source: str) -> dict[str, object]:
    program = Parser(Lexer(source)).parse_program()
    return Interpreter().eval(program)


class TestInterpreter(unittest.TestCase):
    def test_input_builtin(self):
        import io
        from unittest.mock import patch

        with patch("sys.stdin", io.StringIO("Ada\n")):
            env = run("let name = input()")
        self.assertEqual(env["name"], "Ada")

    def test_let_expression(self):
        env = run("let x = 1 + 2 * 3")
        self.assertEqual(env["x"], 7)

    def test_multiple_lets_and_identifier(self):
        env = run("let x = 1 let y = x + 2")
        self.assertEqual(env, {"x": 1, "y": 3})

    def test_unary_minus(self):
        env = run("let x = -1 + 2")
        self.assertEqual(env["x"], 1)

    def test_division(self):
        env = run("let x = 7 / 2")
        self.assertEqual(env["x"], 3.5)

    def test_float_literals_and_division(self):
        env = run("let x = 3.5 let y = x / 2 let z = 7 / 2")
        self.assertEqual(env["x"], 3.5)
        self.assertEqual(env["y"], 1.75)
        self.assertEqual(env["z"], 3.5)

    def test_integer_division(self):
        env = run("let a = 7 // 2 let b = -7 // 2")
        self.assertEqual(env["a"], 3)
        self.assertEqual(env["b"], -4)

    def test_integer_division_requires_ints(self):
        with self.assertRaises(TypeError):
            run("let x = 7.0 // 2")

    def test_integer_division_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            run("let x = 1 // 0")

    def test_modulo(self):
        env = run("let a = 7 % 2 let b = -7 % 2 let c = 7.5 % 2.0")
        self.assertEqual(env["a"], 1)
        self.assertEqual(env["b"], 1)
        self.assertEqual(env["c"], 1.5)

    def test_modulo_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            run("let x = 1 % 0")

    def test_string_literals_and_concatenation(self):
        program = Parser(Lexer('let s = "hello" let t = s + " world" print(t)')).parse_program()
        interpreter = Interpreter()
        env = interpreter.eval(program)
        self.assertEqual(env["s"], "hello")
        self.assertEqual(env["t"], "hello world")
        self.assertEqual(interpreter.output, ["hello world"])

    def test_undefined_name(self):
        with self.assertRaises(NameError):
            run("let y = x + 1")

    def test_division_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            run("let x = 1 / 0")

    def test_bool_literals(self):
        env = run("let a = true let b = false")
        self.assertIs(env["a"], True)
        self.assertIs(env["b"], False)

    def test_comparisons(self):
        env = run("let a = 1 == 1 let b = 1 != 2 let c = 1 < 2 let d = 3 >= 4 let e = 1 + 2 <= 3")
        self.assertEqual(env, {"a": True, "b": True, "c": True, "d": False, "e": True})

    def test_logical_ops(self):
        env = run("let a = !false let b = true && false let c = true || false let d = true || false && false")
        self.assertEqual(env, {"a": True, "b": False, "c": True, "d": True})

    def test_word_operators(self):
        env = run("let a = true and false let b = false or true let c = not false")
        self.assertEqual(env, {"a": False, "b": True, "c": True})

    def test_if_else(self):
        env = run("let x = 0 if true { let x = 1 } else { let x = 2 }")
        self.assertEqual(env["x"], 1)
        env = run("let x = 0 if false { let x = 1 } else { let x = 2 }")
        self.assertEqual(env["x"], 2)

    def test_if_condition_expression(self):
        env = run("let a = 5 let r = 0 if a > 3 { let r = 10 }")
        self.assertEqual(env["r"], 10)

    def test_if_expression(self):
        env = run("let a = if true { 1 } else { 2 } let b = if false { 1 } else { 2 }")
        self.assertEqual(env["a"], 1)
        self.assertEqual(env["b"], 2)

    def test_if_expression_with_condition(self):
        env = run('let score = 42 let label = if score >= 50 { "pass" } else { "fail" }')
        self.assertEqual(env["label"], "fail")

    def test_nested_if_expression(self):
        env = run("let x = if true { if false { 1 } else { 2 } } else { 3 }")
        self.assertEqual(env["x"], 2)

    def test_if_expression_with_block_branches(self):
        env = run("let x = if true { let y = 1 y + 2 } else { let y = 3 y + 4 }")
        self.assertEqual(env["x"], 3)
        env = run("let x = if false { let y = 1 y + 2 } else { let y = 3 y + 4 }")
        self.assertEqual(env["x"], 7)

    def test_if_expression_block_assignment(self):
        env = run("let y = 0 let x = if true { y = 5 y } else { y = 9 y }")
        self.assertEqual(env["x"], 5)
        self.assertEqual(env["y"], 5)

    def test_if_expression_block_print(self):
        program = Parser(Lexer("let x = if true { print(1) 2 } else { print(3) 4 } print(x)")).parse_program()
        interpreter = Interpreter()
        env = interpreter.eval(program)
        self.assertEqual(env["x"], 2)
        self.assertEqual(interpreter.output, [1, 2])

    def test_if_expression_block_while(self):
        env = run("let i = 0 let x = if true { while i < 3 { i = i + 1 } i } else { 0 }")
        self.assertEqual(env["x"], 3)
        self.assertEqual(env["i"], 3)

    def test_if_expression_block_scope_leaks(self):
        env = run("let x = if true { let y = 1 y } else { 0 }")
        self.assertEqual(env["y"], 1)

    def test_if_expression_block_nested_if_value(self):
        env = run("let x = if true { let y = 1 if y > 0 { 10 } else { 20 } } else { 30 }")
        self.assertEqual(env["x"], 10)

    def test_if_expression_block_undefined_name_span(self):
        with self.assertRaises(SwarnaNameError) as raised:
            run("let x = if true { let y = 1 missing } else { 0 }")
        self.assertEqual(raised.exception.span, SourceSpan(1, 29, 7))

    def test_let_assignment(self):
        env = run("let x = 0 x = x + 1 x = x + 1")
        self.assertEqual(env["x"], 2)

    def test_const_binding(self):
        env = run("const x = 42")
        self.assertEqual(env["x"], 42)

    def test_assign_to_const_fails(self):
        with self.assertRaises(RuntimeError):
            run("const x = 0 x = 1")

    def test_assign_to_undefined_fails(self):
        with self.assertRaises(NameError):
            run("x = 1")

    def test_while_loop(self):
        env = run("let i = 0 while i < 3 { i = i + 1 }")
        self.assertEqual(env["i"], 3)

    def test_while_break_exits_loop(self):
        env = run("let i = 0 while true { i = i + 1 if i == 3 { break } }")
        self.assertEqual(env["i"], 3)

    def test_while_continue_skips_rest_of_body(self):
        env = run(
            "let i = 0 let total = 0 "
            "while i < 5 { i = i + 1 if i == 3 { continue } total = total + i }"
        )
        self.assertEqual(env["total"], 12)

    def test_undefined_name_diagnostic_has_span(self):
        with self.assertRaises(SwarnaNameError) as raised:
            run("let y = x + 1")
        error = raised.exception
        self.assertEqual(error.span, SourceSpan(1, 9, 1))
        self.assertIsNotNone(error.hint)

    def test_undefined_assignment_diagnostic_has_span(self):
        with self.assertRaises(SwarnaNameError) as raised:
            run("x = 1")
        self.assertEqual(raised.exception.span, SourceSpan(1, 1, 1))

    def test_const_assignment_diagnostic_has_span(self):
        with self.assertRaises(SwarnaRuntimeError) as raised:
            run("const x = 0 x = 1")
        error = raised.exception
        self.assertEqual(error.span, SourceSpan(1, 13, 1))
        self.assertIsNotNone(error.hint)

    def test_division_by_zero_diagnostic_has_span(self):
        with self.assertRaises(SwarnaZeroDivisionError) as raised:
            run("let x = 1 / 0")
        self.assertEqual(raised.exception.span, SourceSpan(1, 11, 1))

    def test_integer_division_type_diagnostic_has_span(self):
        with self.assertRaises(SwarnaTypeError) as raised:
            run("let x = 7.0 // 2")
        self.assertEqual(raised.exception.span, SourceSpan(1, 13, 2))

    def test_type_mismatch_diagnostic_has_span(self):
        with self.assertRaises(SwarnaTypeError) as raised:
            run('let x = 1 + "a"')
        self.assertEqual(raised.exception.span, SourceSpan(1, 11, 1))

    def test_type_mismatch_diagnostic_has_explanation(self):
        with self.assertRaises(SwarnaTypeError) as raised:
            run('let x = 1 + "a"')
        self.assertIsNotNone(raised.exception.resolved_explanation)


class TestInterpreterForLoops(unittest.TestCase):
    def test_for_loop_accumulates(self):
        env = run("let total = 0 for x in [1, 2, 3] { total = total + x }")
        self.assertEqual(env["total"], 6)

    def test_range_builtin(self):
        env = run(
            "let a = range(5) "
            "let b = range(2, 6) "
            "let c = range(5, 0, -2) "
            "let total = 0 for i in range(4) { total = total + i }"
        )
        self.assertEqual(env["a"], [0, 1, 2, 3, 4])
        self.assertEqual(env["b"], [2, 3, 4, 5])
        self.assertEqual(env["c"], [5, 3, 1])
        self.assertEqual(env["total"], 6)

    def test_for_loop_prints_each_item(self):
        program = Parser(Lexer("for x in [1, 2, 3] { print(x) }")).parse_program()
        interpreter = Interpreter()
        interpreter.eval(program)
        self.assertEqual(interpreter.output, [1, 2, 3])

    def test_for_loop_variable_does_not_leak(self):
        env = run("for x in [1, 2] { }")
        self.assertNotIn("x", env)

    def test_for_loop_restores_outer_binding(self):
        env = run("let x = 10 for x in [1, 2] { }")
        self.assertEqual(env["x"], 10)

    def test_for_loop_restores_const_outer_binding(self):
        env = run("const x = 10 for x in [1, 2] { x = 5 }")
        self.assertEqual(env["x"], 10)

    def test_for_loop_variable_is_mutable(self):
        env = run("for x in [1] { x = x + 10 let y = x }")
        self.assertEqual(env["y"], 11)
        self.assertNotIn("x", env)

    def test_for_loop_body_declarations_leak(self):
        env = run("for x in [1, 2] { let y = x + 1 }")
        self.assertEqual(env, {"y": 3})

    def test_for_loop_over_empty_list(self):
        env = run("let total = 0 for x in [] { total = total + 1 }")
        self.assertEqual(env, {"total": 0})

    def test_for_loop_break_stops_iteration(self):
        program = Parser(
            Lexer("for x in [1, 2, 3, 4] { if x == 3 { break } print(x) }")
        ).parse_program()
        interpreter = Interpreter()
        interpreter.eval(program)
        self.assertEqual(interpreter.output, [1, 2])

    def test_for_loop_continue_skips_item(self):
        program = Parser(
            Lexer("for x in [1, 2, 3, 4] { if x == 2 { continue } print(x) }")
        ).parse_program()
        interpreter = Interpreter()
        interpreter.eval(program)
        self.assertEqual(interpreter.output, [1, 3, 4])

    def test_break_only_exits_inner_loop(self):
        program = Parser(
            Lexer(
                "for x in [1, 2] { "
                "for y in [10, 20] { if y == 20 { break } print(x + y) } "
                "print(x) }"
            )
        ).parse_program()
        interpreter = Interpreter()
        interpreter.eval(program)
        self.assertEqual(interpreter.output, [11, 1, 12, 2])

    def test_nested_for_loops(self):
        env = run(
            "let total = 0 "
            "for x in [1, 2] { for y in [10, 20] { total = total + x + y } }"
        )
        self.assertEqual(env["total"], 66)

    def test_nested_for_loops_restore_same_name(self):
        env = run(
            "let total = 0 "
            "for x in [1, 2] { for x in [10, 20] { total = total + x } total = total + x }"
        )
        self.assertEqual(env["total"], 63)

    def test_for_loop_evaluates_iterable_once(self):
        program = Parser(
            Lexer("fn values() { print(1) [1, 2] } for x in values() { print(x) }")
        ).parse_program()
        interpreter = Interpreter()
        interpreter.eval(program)
        self.assertEqual(interpreter.output, [1, 1, 2])

    def test_for_loop_over_function_parameter(self):
        program = Parser(
            Lexer("fn show(xs) { for x in xs { print(x) } 0 } let y = show([1, 2])")
        ).parse_program()
        interpreter = Interpreter()
        env = interpreter.eval(program)
        self.assertEqual(env["y"], 0)
        self.assertEqual(interpreter.output, [1, 2])

    def test_for_loop_requires_iterable(self):
        with self.assertRaisesRegex(SwarnaTypeError, "`for` expects a List, Map, or String, got Int"):
            run("for x in 1 { print(x) }")

    def test_for_loop_iterates_string(self):
        program = Parser(Lexer('for c in "abc" { print(c) }')).parse_program()
        interpreter = Interpreter()
        interpreter.eval(program)
        self.assertEqual(interpreter.output, ["a", "b", "c"])

    def test_string_indexing(self):
        env = run('let s = "hello" let a = s[0] let b = s[-1]')
        self.assertEqual(env["a"], "h")
        self.assertEqual(env["b"], "o")

    def test_for_loop_restores_outer_binding_on_error(self):
        interpreter = Interpreter()
        program = Parser(Lexer("let x = 10 for x in [1] { let y = missing }")).parse_program()
        with self.assertRaises(SwarnaNameError):
            interpreter.eval(program)
        self.assertEqual(interpreter.env["x"], 10)

    def test_for_loop_removes_loop_variable_on_error(self):
        interpreter = Interpreter()
        program = Parser(Lexer("for x in [1] { let y = missing }")).parse_program()
        with self.assertRaises(SwarnaNameError):
            interpreter.eval(program)
        self.assertNotIn("x", interpreter.env)


class TestInterpreterFunctions(unittest.TestCase):
    def test_function_declaration_and_call(self):
        env = run("fn add(a: Int, b: Int) -> Int { a + b } let x = add(2, 3)")
        self.assertEqual(env["x"], 5)

    def test_function_without_annotations(self):
        env = run("fn add(a, b) { a + b } let x = add(2, 3)")
        self.assertEqual(env["x"], 5)

    def test_function_call_before_declaration_is_hoisted(self):
        env = run("let x = add(2, 3) fn add(a: Int, b: Int) -> Int { a + b }")
        self.assertEqual(env["x"], 5)

    def test_function_call_with_zero_arguments(self):
        env = run("fn answer() -> Int { 42 } let x = answer()")
        self.assertEqual(env["x"], 42)

    def test_function_call_as_argument(self):
        env = run("fn add(a: Int, b: Int) -> Int { a + b } fn one() -> Int { 1 } let x = add(one(), 2)")
        self.assertEqual(env["x"], 3)

    def test_recursive_function(self):
        env = run(
            "fn factorial(n: Int) -> Int { if n <= 1 { 1 } else { n * factorial(n - 1) } } "
            "let x = factorial(5)"
        )
        self.assertEqual(env["x"], 120)

    def test_mutually_recursive_functions(self):
        env = run(
            "fn is_even(n: Int) -> Bool { if n == 0 { true } else { is_odd(n - 1) } } "
            "fn is_odd(n: Int) -> Bool { if n == 0 { false } else { is_even(n - 1) } } "
            "let x = is_even(4)"
        )
        self.assertIs(env["x"], True)

    def test_function_with_while_loop(self):
        env = run(
            "fn sum_to(n: Int) -> Int { let total = 0 let i = 1 "
            "while i <= n { total = total + i i = i + 1 } total } "
            "let x = sum_to(5)"
        )
        self.assertEqual(env["x"], 15)

    def test_function_local_binding_does_not_leak(self):
        env = run("fn f() -> Int { let local = 1 local } let x = f()")
        self.assertEqual(env, {"x": 1})

    def test_function_reads_global_binding(self):
        env = run("let base = 10 fn add_base(x: Int) -> Int { x + base } let y = add_base(5)")
        self.assertEqual(env["y"], 15)

    def test_function_assignment_does_not_mutate_global(self):
        env = run("let x = 1 fn bump() -> Int { x = x + 1 x } let y = bump()")
        self.assertEqual(env, {"x": 1, "y": 2})

    def test_function_print_output(self):
        program = Parser(Lexer("fn show(x: Int) -> Int { print(x) x + 1 } let y = show(4)")).parse_program()
        interpreter = Interpreter()
        env = interpreter.eval(program)
        self.assertEqual(env["y"], 5)
        self.assertEqual(interpreter.output, [4])

    def test_print_function_call_result(self):
        program = Parser(Lexer("fn f() -> Int { 7 } print(f())")).parse_program()
        interpreter = Interpreter()
        interpreter.eval(program)
        self.assertEqual(interpreter.output, [7])

    def test_function_persists_across_eval_calls(self):
        interpreter = Interpreter()
        interpreter.eval(Parser(Lexer("fn f() -> Int { 1 }")).parse_program())
        env = interpreter.eval(Parser(Lexer("let x = f()")).parse_program())
        self.assertEqual(env["x"], 1)

    def test_wrong_argument_count(self):
        with self.assertRaisesRegex(RuntimeError, "expects 2 arguments, got 1"):
            run("fn add(a: Int, b: Int) -> Int { a + b } let x = add(1)")

    def test_undefined_function(self):
        with self.assertRaisesRegex(NameError, "Undefined function 'missing'"):
            run("let x = missing(1)")

    def test_bare_function_name_must_be_called(self):
        with self.assertRaisesRegex(NameError, "must be called"):
            run("fn f() -> Int { 1 } let x = f")

    def test_assignment_to_function_is_rejected(self):
        with self.assertRaisesRegex(NameError, "Cannot assign to function 'f'"):
            run("fn f() -> Int { 1 } f = 2")

    def test_duplicate_function_declaration(self):
        with self.assertRaisesRegex(RuntimeError, "declared more than once"):
            run("fn f() -> Int { 1 } fn f() -> Int { 2 } let x = f()")

    def test_duplicate_parameter(self):
        with self.assertRaisesRegex(RuntimeError, "Duplicate parameter 'a'"):
            run("fn f(a: Int, a: Int) -> Int { a } let x = f(1, 2)")

    def test_nested_function_declaration_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "only allowed at the top level"):
            run("if true { fn f() -> Int { 1 } }")

    def test_recursion_depth_limit(self):
        with self.assertRaisesRegex(RuntimeError, "Maximum call depth"):
            run("fn loop(n: Int) -> Int { loop(n + 1) } let x = loop(0)")

    def test_list_literal_and_index(self):
        env = run("let xs = [1, 2, 3] let x = xs[0] let y = xs[-1]")
        self.assertEqual(env["xs"], [1, 2, 3])
        self.assertEqual(env["x"], 1)
        self.assertEqual(env["y"], 3)

    def test_nested_list_index(self):
        env = run("let xs = [[1], [2, 3]] let x = xs[1][0]")
        self.assertEqual(env["x"], 2)

    def test_list_concatenation(self):
        env = run("let xs = [1, 2] + [3, 4]")
        self.assertEqual(env["xs"], [1, 2, 3, 4])

    def test_list_equality(self):
        env = run("let x = [1, 2] == [1, 2] let y = [1] != [2]")
        self.assertIs(env["x"], True)
        self.assertIs(env["y"], True)

    def test_len_of_list_and_string(self):
        env = run('let xs = [1, 2, 3] let a = len(xs) let b = len("hello")')
        self.assertEqual(env["a"], 3)
        self.assertEqual(env["b"], 5)

    def test_empty_list(self):
        env = run("let xs = [] let n = len(xs)")
        self.assertEqual(env["xs"], [])
        self.assertEqual(env["n"], 0)

    def test_list_print_output(self):
        program = Parser(Lexer("print([1, 2, 3])")).parse_program()
        interpreter = Interpreter()
        interpreter.eval(program)
        self.assertEqual(interpreter.output, [[1, 2, 3]])

    def test_index_out_of_range(self):
        with self.assertRaisesRegex(RuntimeError, "Index 3 is out of range for a list of length 2"):
            run("let xs = [1, 2] let x = xs[3]")

    def test_negative_index_out_of_range(self):
        with self.assertRaisesRegex(RuntimeError, "Index -3 is out of range for a list of length 2"):
            run("let xs = [1, 2] let x = xs[-3]")

    def test_index_must_be_int(self):
        with self.assertRaisesRegex(TypeError, "List index must be Int"):
            run('let xs = [1, 2] let x = xs["a"]')

    def test_only_lists_can_be_indexed(self):
        with self.assertRaisesRegex(TypeError, "Cannot index Int"):
            run("let x = 1[0]")

    def test_len_requires_collection_or_string(self):
        with self.assertRaisesRegex(
            TypeError,
            "`len` expects a List, Map, or String, got Int",
        ):
            run("let n = len(1)")

    def test_len_requires_one_argument(self):
        with self.assertRaisesRegex(RuntimeError, "Function 'len' expects 1 argument, got 2"):
            run("let n = len([1], [2])")


class TestInterpreterMaps(unittest.TestCase):
    def test_map_literal_and_index(self):
        env = run('let m = { "a": 1, "b": 2 } let x = m["a"]')
        self.assertEqual(env["m"], {"a": 1, "b": 2})
        self.assertEqual(env["x"], 1)

    def test_empty_map(self):
        env = run("let m = {} let n = len(m)")
        self.assertEqual(env["m"], {})
        self.assertEqual(env["n"], 0)

    def test_nested_map(self):
        env = run('let m = { "a": { "b": 2 } } let x = m["a"]["b"]')
        self.assertEqual(env["x"], 2)

    def test_map_index_assignment_updates_existing_key(self):
        env = run('let m = { "a": 1 } m["a"] = 2')
        self.assertEqual(env["m"], {"a": 2})

    def test_map_index_assignment_adds_new_key(self):
        env = run('let m = { "a": 1 } m["b"] = 2')
        self.assertEqual(env["m"], {"a": 1, "b": 2})

    def test_map_index_assignment_accumulates(self):
        env = run(
            'let totals = { "red": 0 } '
            'totals["red"] = totals["red"] + 5 '
            'totals["red"] = totals["red"] + 3'
        )
        self.assertEqual(env["totals"], {"red": 8})

    def test_nested_map_index_assignment(self):
        env = run('let m = { "a": { "b": 1 } } m["a"]["b"] = 2')
        self.assertEqual(env["m"], {"a": {"b": 2}})

    def test_list_index_assignment_rejected(self):
        with self.assertRaisesRegex(
            SwarnaTypeError, "Lists are immutable; cannot assign to an index"
        ):
            run("let xs = [1, 2] xs[0] = 3")

    def test_const_map_index_assignment_rejected(self):
        with self.assertRaisesRegex(
            SwarnaRuntimeError, "Cannot assign to const binding 'm'"
        ):
            run('const m = { "a": 1 } m["a"] = 2')

    def test_index_assignment_to_undefined_name(self):
        with self.assertRaisesRegex(SwarnaNameError, "Undefined name 'm'"):
            run('m["a"] = 1')

    def test_index_assignment_requires_map(self):
        with self.assertRaisesRegex(
            SwarnaTypeError, "Cannot assign to Int"
        ):
            run("let x = 1 x[0] = 2")

    def test_index_assignment_key_must_be_hashable(self):
        with self.assertRaisesRegex(
            SwarnaTypeError,
            "Map keys must be Int, Float, String, or Bool, got List",
        ):
            run('let m = { "a": 1 } m[[1]] = 2')

    def test_index_assignment_requires_name_target(self):
        with self.assertRaisesRegex(
            SwarnaTypeError, "Index assignment must target a name"
        ):
            run(
                "fn values() { [1] } "
                "let x = if true { values()[0] = 2 0 } else { 0 }"
            )

    def test_get_existing_key(self):
        env = run('let m = { "a": 1 } let x = get(m, "a", 0)')
        self.assertEqual(env["x"], 1)

    def test_get_missing_key_returns_default(self):
        env = run('let m = { "a": 1 } let x = get(m, "b", 0)')
        self.assertEqual(env["x"], 0)

    def test_get_on_empty_map_returns_default(self):
        env = run('let m = {} let x = get(m, "a", 3)')
        self.assertEqual(env["x"], 3)

    def test_get_requires_map(self):
        with self.assertRaisesRegex(SwarnaTypeError, "`get` expects a Map, got Int"):
            run('let x = get(1, "a", 0)')

    def test_get_rejects_unhashable_key(self):
        with self.assertRaisesRegex(
            SwarnaTypeError,
            "Map keys must be Int, Float, String, or Bool, got List",
        ):
            run('let m = { "a": 1 } let x = get(m, [1], 0)')

    def test_map_equality(self):
        env = run('let x = { "a": 1 } == { "a": 1 }')
        self.assertIs(env["x"], True)

    def test_len_of_map(self):
        env = run('let n = len({ "a": 1, "b": 2 })')
        self.assertEqual(env["n"], 2)

    def test_missing_key(self):
        with self.assertRaisesRegex(RuntimeError, 'Key "missing" is not in the map'):
            run('let m = { "a": 1 } let x = m["missing"]')

    def test_missing_key_has_span_and_hint(self):
        with self.assertRaises(SwarnaRuntimeError) as raised:
            run('let m = { "a": 1 } let x = m["missing"]')
        self.assertIsNotNone(raised.exception.span)
        self.assertIsNotNone(raised.exception.hint)

    def test_map_print_output(self):
        program = Parser(Lexer('print({ "a": 1, "b": 2 })')).parse_program()
        interpreter = Interpreter()
        interpreter.eval(program)
        self.assertEqual(interpreter.output, [{"a": 1, "b": 2}])

    def test_for_loop_iterates_map_keys(self):
        program = Parser(Lexer('for k in { "a": 1, "b": 2 } { print(k) }')).parse_program()
        interpreter = Interpreter()
        interpreter.eval(program)
        self.assertEqual(interpreter.output, ["a", "b"])

    def test_map_key_must_be_hashable(self):
        with self.assertRaisesRegex(SwarnaTypeError, "Map keys must be scalar values"):
            run('let m = { "a": 1 } let x = m[[1]]')

    def test_map_literal_rejects_list_key(self):
        with self.assertRaisesRegex(
            SwarnaTypeError,
            "Map keys must be Int, Float, String, or Bool, got List",
        ):
            run("let m = { [1]: 2 }")


class TestInterpreterFiles(unittest.TestCase):
    def test_read_file_returns_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.txt"
            path.write_text("hello\nworld", encoding="utf-8")
            env = run(f"let text = read_file({json.dumps(path.as_posix())})")
            self.assertEqual(env["text"], "hello\nworld")

    def test_read_empty_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.txt"
            path.write_text("", encoding="utf-8")
            env = run(f"let text = read_file({json.dumps(path.as_posix())})")
            self.assertEqual(env["text"], "")

    def test_read_file_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.txt"
            with self.assertRaisesRegex(RuntimeError, "file not found"):
                run(f"let text = read_file({json.dumps(path.as_posix())})")

    def test_read_file_missing_has_span_and_hint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.txt"
            with self.assertRaises(SwarnaRuntimeError) as raised:
                run(f"let text = read_file({json.dumps(path.as_posix())})")
        self.assertIsNotNone(raised.exception.span)
        self.assertIsNotNone(raised.exception.hint)

    def test_read_file_rejects_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "it is a directory"):
                run(f"let text = read_file({json.dumps(Path(directory).as_posix())})")

    def test_read_file_rejects_invalid_utf8(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "binary.dat"
            path.write_bytes(b"\xff\xfe")
            with self.assertRaisesRegex(RuntimeError, "not valid UTF-8 text"):
                run(f"let text = read_file({json.dumps(path.as_posix())})")

    def test_read_file_requires_string_path(self):
        with self.assertRaisesRegex(TypeError, "`read_file` expects a String path, got Int"):
            run("let text = read_file(1)")


class TestInterpreterCsv(unittest.TestCase):
    @staticmethod
    def _write(directory: str, text: str) -> Path:
        path = Path(directory) / "scores.csv"
        path.write_text(text, encoding="utf-8")
        return path

    def test_read_csv_returns_typed_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                "name,team,score\nAda,Blue,88\nGrace,Blue,92.5\n",
            )
            source = (
                f"let rows = read_csv({json.dumps(path.as_posix())}, "
                "{ name: String, team: String, score: Float })"
            )
            env = run(source)
        self.assertEqual(
            env["rows"],
            [
                {"name": "Ada", "team": "Blue", "score": 88.0},
                {"name": "Grace", "team": "Blue", "score": 92.5},
            ],
        )

    def test_read_csv_bad_cell_names_file_row_column_and_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                "name,team,score\n"
                "Ada,Blue,88\n"
                "Margaret,Red,n/a\n",
            )
            source = (
                f"let rows = read_csv({json.dumps(path.as_posix())}, "
                "{ name: String, team: String, score: Float })"
            )
            with self.assertRaises(SwarnaRuntimeError) as raised:
                run(source)
        error = raised.exception
        self.assertEqual(error.span, SourceSpan(3, 14, 3))
        self.assertEqual(error.source_name, path.as_posix())
        self.assertIn("expected a Float in column 'score'", error.message)
        self.assertIn("got 'n/a'", error.message)
        rendered = render_diagnostic("program", error)
        self.assertIn(f"--> {path.as_posix()}:3:14", rendered)
        self.assertIn("Margaret,Red,n/a", rendered)

    def test_read_csv_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.csv"
            with self.assertRaisesRegex(RuntimeError, "file not found"):
                run(
                    f'let rows = read_csv({json.dumps(path.as_posix())}, '
                    "{ name: String })"
                )

    def test_read_csv_rejects_non_schema(self):
        with self.assertRaisesRegex(RuntimeError, "expects a schema literal"):
            run('let rows = read_csv("scores.csv", 1)')

    def test_read_csv_requires_string_path(self):
        with self.assertRaisesRegex(TypeError, "`read_csv` expects a String path, got Int"):
            run("let rows = read_csv(1, { name: String })")


if __name__ == "__main__":
    unittest.main()
