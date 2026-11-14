import json
import tempfile
import unittest
from pathlib import Path

from compiler.bytecode.instructions import Instruction, Op
from compiler.codegen.compiler import Compiler
from compiler.diagnostics import SourceSpan, SwarnaNameError, SwarnaRuntimeError, SwarnaTypeError, SwarnaZeroDivisionError
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from runtime.interpreter import Interpreter
from runtime.vm import VM


def run_vm(source: str) -> dict[str, object]:
    program = Parser(Lexer(source)).parse_program()
    code = Compiler().compile(program)
    return VM().run(code)


class TestVM(unittest.TestCase):
    def test_vm_let_expression(self):
        env = run_vm("let x = 1 + 2 * 3")
        self.assertEqual(env["x"], 7)

    def test_vm_identifier_and_assignment(self):
        env = run_vm("let x = 1 x = x + 2")
        self.assertEqual(env["x"], 3)

    def test_vm_const_binding(self):
        env = run_vm("const x = 5")
        self.assertEqual(env["x"], 5)

    def test_vm_const_assignment_fails(self):
        with self.assertRaises(RuntimeError):
            run_vm("const x = 0 x = 1")

    def test_vm_undefined_assignment_fails(self):
        with self.assertRaises(NameError):
            run_vm("x = 1")

    def test_vm_unary_and_div(self):
        env = run_vm("let x = -7 / 2")
        self.assertEqual(env["x"], -3.5)

    def test_vm_integer_division(self):
        env = run_vm("let x = 7 // 2")
        self.assertEqual(env["x"], 3)

    def test_vm_integer_division_requires_ints(self):
        with self.assertRaises(TypeError):
            run_vm("let x = 7.0 // 2")

    def test_vm_integer_division_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            run_vm("let x = 1 // 0")

    def test_vm_modulo(self):
        env = run_vm("let a = 7 % 2 let b = -7 % 2 let c = 7.5 % 2.0")
        self.assertEqual(env["a"], 1)
        self.assertEqual(env["b"], 1)
        self.assertEqual(env["c"], 1.5)

    def test_vm_modulo_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            run_vm("let x = 1 % 0")

    def test_vm_undefined_name(self):
        with self.assertRaises(NameError):
            run_vm("let y = x + 1")

    def test_vm_type_mismatch_has_explanation(self):
        with self.assertRaises(SwarnaTypeError) as raised:
            run_vm('let x = 1 + "a"')
        self.assertIsNotNone(raised.exception.resolved_explanation)

    def test_vm_comparisons_bools_and_print(self):
        program = Parser(Lexer("let a = 1 == 2 let b = !false print(b) print(1 < 2)")).parse_program()
        code = Compiler().compile(program)
        vm = VM()
        env = vm.run(code)
        self.assertEqual(env["a"], False)
        self.assertEqual(env["b"], True)
        self.assertEqual(vm.output, [True, True])

    def test_jump_skips_following_instructions(self):
        # CONST 111; PRINT; JUMP 5; CONST 222; PRINT; HALT
        code = [
            Instruction(Op.CONST, 111),
            Instruction(Op.PRINT),
            Instruction(Op.JUMP, 5),
            Instruction(Op.CONST, 222),
            Instruction(Op.PRINT),
            Instruction(Op.HALT),
        ]
        vm = VM()
        vm.run(code)
        self.assertEqual(vm.output, [111])

    def test_jump_if_false_takes_branch_when_false(self):
        # if 0 { print(111) } else { print(222) }
        code = [
            Instruction(Op.CONST, 0),
            Instruction(Op.JUMP_IF_FALSE, 4),
            Instruction(Op.CONST, 111),
            Instruction(Op.PRINT),
            Instruction(Op.CONST, 222),
            Instruction(Op.PRINT),
            Instruction(Op.HALT),
        ]
        vm = VM()
        vm.run(code)
        self.assertEqual(vm.output, [222])

    def test_jump_if_false_falls_through_when_true(self):
        # if 1 { print(111) } else { print(222) }
        # The then-branch ends with JUMP over the else-branch.
        code = [
            Instruction(Op.CONST, 1),
            Instruction(Op.JUMP_IF_FALSE, 5),
            Instruction(Op.CONST, 111),
            Instruction(Op.PRINT),
            Instruction(Op.JUMP, 7),
            Instruction(Op.CONST, 222),
            Instruction(Op.PRINT),
            Instruction(Op.HALT),
        ]
        vm = VM()
        vm.run(code)
        self.assertEqual(vm.output, [111])

    def test_jump_if_false_requires_stack_value(self):
        code = [Instruction(Op.JUMP_IF_FALSE, 1), Instruction(Op.HALT)]
        with self.assertRaises(RuntimeError):
            VM().run(code)

    def test_invalid_jump_target_is_rejected(self):
        for target in (-1, 99, "nope"):
            with self.subTest(target=target):
                code = [Instruction(Op.JUMP, target), Instruction(Op.HALT)]
                with self.assertRaises(RuntimeError):
                    VM().run(code)

    def test_vm_if_else_matches_interpreter(self):
        sources = [
            "let x = 0 if 1 < 2 { x = 1 } else { x = 2 } print(x)",
            "let x = 0 if 1 > 2 { x = 1 } else { x = 2 } print(x)",
            "if true { if false { print(1) } else { print(2) } } else { print(3) }",
        ]
        for source in sources:
            with self.subTest(source=source):
                program = Parser(Lexer(source)).parse_program()
                interpreter = Interpreter()
                expected_env = interpreter.eval(program)

                vm = VM()
                actual_env = vm.run(Compiler().compile(program))

                self.assertEqual(actual_env, expected_env)
                self.assertEqual(vm.output, interpreter.output)

    def test_vm_if_expression_matches_interpreter(self):
        sources = [
            "let x = if true { 1 } else { 2 } print(x)",
            "let x = if false { 1 } else { 2 } print(x)",
            'let x = if 10 >= 50 { "pass" } else { "fail" } print(x)',
            "let x = if true { if false { 1 } else { 2 } } else { 3 } print(x)",
            "let x = if 1 < 2 { 3 + 4 } else { 5 * 6 } print(x)",
            "let x = if true { let y = 1 y + 2 } else { let y = 3 y + 4 } print(x)",
            "let x = if false { let y = 1 y + 2 } else { let y = 3 y + 4 } print(x)",
            "let y = 0 let x = if true { y = 5 y } else { y = 9 y } print(x) print(y)",
            "let i = 0 let x = if true { while i < 3 { i = i + 1 } i } else { 0 } print(x)",
            "let x = if true { print(1) 2 } else { print(3) 4 } print(x)",
            "let x = if true { let y = 1 if y > 0 { 10 } else { 20 } } else { 30 } print(x)",
        ]
        for source in sources:
            with self.subTest(source=source):
                program = Parser(Lexer(source)).parse_program()
                interpreter = Interpreter()
                expected_env = interpreter.eval(program)

                vm = VM()
                actual_env = vm.run(Compiler().compile(program))

                self.assertEqual(actual_env, expected_env)
                self.assertEqual(vm.output, interpreter.output)

    def test_vm_while_matches_interpreter(self):
        sources = [
            "let i = 0 while i < 3 { i = i + 1 } print(i)",
            "let i = 5 while i < 3 { i = i + 1 } print(i)",
            "let i = 0 while i < 3 { if i == 1 { print(99) } i = i + 1 } print(i)",
            "let i = 0 while true { i = i + 1 if i == 3 { break } } print(i)",
            "let i = 0 let total = 0 "
            "while i < 5 { i = i + 1 if i == 3 { continue } total = total + i } print(total)",
        ]
        for source in sources:
            with self.subTest(source=source):
                program = Parser(Lexer(source)).parse_program()
                interpreter = Interpreter()
                expected_env = interpreter.eval(program)

                vm = VM()
                actual_env = vm.run(Compiler().compile(program))

                self.assertEqual(actual_env, expected_env)
                self.assertEqual(vm.output, interpreter.output)

    def test_vm_floats_match_interpreter(self):
        sources = [
            "let x = 3.5 print(x)",
            "let x = 3.5 / 2 print(x)",
            "let x = 7 / 2 print(x)",
            "let i = 0.5 while i < 2.5 { i = i + 0.5 } print(i)",
        ]
        for source in sources:
            with self.subTest(source=source):
                program = Parser(Lexer(source)).parse_program()
                interpreter = Interpreter()
                expected_env = interpreter.eval(program)

                vm = VM()
                actual_env = vm.run(Compiler().compile(program))

                self.assertEqual(actual_env, expected_env)
                self.assertEqual(vm.output, interpreter.output)

    def test_vm_division_matches_interpreter(self):
        sources = [
            "let x = 7 / 2 print(x)",
            "let x = 7 // 2 print(x)",
            "let x = -7 // 2 print(x)",
            "let x = 7 % 2 print(x)",
            "let x = -7 % 2 print(x)",
            "let x = 7.5 % 2.0 print(x)",
            "let x = 3.5 / 2 print(x)",
            "let x = 7 // 2 / 2 print(x)",
        ]
        for source in sources:
            with self.subTest(source=source):
                program = Parser(Lexer(source)).parse_program()
                interpreter = Interpreter()
                expected_env = interpreter.eval(program)

                vm = VM()
                actual_env = vm.run(Compiler().compile(program))

                self.assertEqual(actual_env, expected_env)
                self.assertEqual(vm.output, interpreter.output)

    def test_vm_assignment_errors_match_interpreter(self):
        cases = [
            ("x = 1", NameError),
            ("const x = 0 x = 1", RuntimeError),
        ]
        for source, exc in cases:
            with self.subTest(source=source):
                program = Parser(Lexer(source)).parse_program()
                with self.assertRaises(exc):
                    Interpreter().eval(program)
                with self.assertRaises(exc):
                    VM().run(Compiler().compile(program))

    def test_vm_strings_match_interpreter(self):
        sources = [
            'let s = "hello" print(s)',
            'let s = "hello" let t = s + " world" print(t)',
            'print("a" == "a")',
        ]
        for source in sources:
            with self.subTest(source=source):
                program = Parser(Lexer(source)).parse_program()
                interpreter = Interpreter()
                expected_env = interpreter.eval(program)

                vm = VM()
                actual_env = vm.run(Compiler().compile(program))

                self.assertEqual(actual_env, expected_env)
                self.assertEqual(vm.output, interpreter.output)

    def test_dup_duplicates_top(self):
        code = [
            Instruction(Op.CONST, 5),
            Instruction(Op.DUP),
            Instruction(Op.ADD),
            Instruction(Op.PRINT),
            Instruction(Op.HALT),
        ]
        vm = VM()
        vm.run(code)
        self.assertEqual(vm.output, [10])

    def test_dup_requires_stack_value(self):
        with self.assertRaises(RuntimeError):
            VM().run([Instruction(Op.DUP), Instruction(Op.HALT)])

    def test_bool_coerces_top(self):
        code = [
            Instruction(Op.CONST, 0),
            Instruction(Op.BOOL),
            Instruction(Op.PRINT),
            Instruction(Op.CONST, 5),
            Instruction(Op.BOOL),
            Instruction(Op.PRINT),
            Instruction(Op.HALT),
        ]
        vm = VM()
        vm.run(code)
        self.assertEqual(vm.output, [False, True])

    def test_bool_requires_stack_value(self):
        with self.assertRaises(RuntimeError):
            VM().run([Instruction(Op.BOOL), Instruction(Op.HALT)])

    def test_vm_short_circuit_and(self):
        self.assertIs(run_vm("let x = true && false")["x"], False)
        # The right operand would raise if evaluated.
        self.assertIs(run_vm("let x = false && (1 / 0 == 0)")["x"], False)

    def test_vm_short_circuit_or(self):
        self.assertIs(run_vm("let x = false || true")["x"], True)
        # The right operand would raise if evaluated.
        self.assertIs(run_vm("let x = true || (1 / 0 == 0)")["x"], True)

    def test_compiled_instructions_carry_spans(self):
        program = Parser(Lexer("let y = x + 1")).parse_program()
        code = Compiler().compile(program)
        load_x = next(ins for ins in code if ins.op == Op.LOAD_NAME and ins.arg == "x")
        add = next(ins for ins in code if ins.op == Op.ADD)
        self.assertEqual(load_x.span, SourceSpan(1, 9, 1))
        self.assertEqual(add.span, SourceSpan(1, 11, 1))

    def test_vm_undefined_name_diagnostic_has_span(self):
        with self.assertRaises(SwarnaNameError) as raised:
            run_vm("let y = x + 1")
        self.assertEqual(raised.exception.span, SourceSpan(1, 9, 1))

    def test_vm_const_assignment_diagnostic_has_span(self):
        with self.assertRaises(SwarnaRuntimeError) as raised:
            run_vm("const x = 0 x = 1")
        self.assertEqual(raised.exception.span, SourceSpan(1, 13, 1))

    def test_vm_division_by_zero_diagnostic_has_span(self):
        with self.assertRaises(SwarnaZeroDivisionError) as raised:
            run_vm("let x = 1 / 0")
        self.assertEqual(raised.exception.span, SourceSpan(1, 11, 1))

    def test_vm_integer_division_type_diagnostic_has_span(self):
        with self.assertRaises(SwarnaTypeError) as raised:
            run_vm("let x = 7.0 // 2")
        self.assertEqual(raised.exception.span, SourceSpan(1, 13, 2))

    def test_vm_logical_ops_match_interpreter(self):
        sources = [
            "let x = true && false print(x)",
            "let x = false || true print(x)",
            "let x = false && (1 / 0 == 0) print(x)",
            "let x = true || (1 / 0 == 0) print(x)",
            "let x = 0 && 5 print(x)",
            "let x = 0 || 5 print(x)",
            "let x = true && false || true print(x)",
            "if true && false { print(1) } else { print(2) }",
            "let i = 0 while i < 3 && i >= 0 { i = i + 1 } print(i)",
            "let x = true and false print(x)",
            "let x = false or true print(x)",
            "let x = not false print(x)",
            "let x = not true and false print(x)",
        ]
        for source in sources:
            with self.subTest(source=source):
                program = Parser(Lexer(source)).parse_program()
                interpreter = Interpreter()
                expected_env = interpreter.eval(program)

                vm = VM()
                actual_env = vm.run(Compiler().compile(program))

                self.assertEqual(actual_env, expected_env)
                self.assertEqual(vm.output, interpreter.output)


class TestVMForLoops(unittest.TestCase):
    def test_vm_for_loop_accumulates(self):
        env = run_vm("let total = 0 for x in [1, 2, 3] { total = total + x }")
        self.assertEqual(env["total"], 6)

    def test_vm_for_loop_prints_each_item(self):
        program = Parser(Lexer("for x in [1, 2, 3] { print(x) }")).parse_program()
        vm = VM()
        vm.run(Compiler().compile(program))
        self.assertEqual(vm.output, [1, 2, 3])

    def test_vm_for_loop_variable_does_not_leak(self):
        env = run_vm("for x in [1, 2] { }")
        self.assertNotIn("x", env)

    def test_vm_for_loop_restores_outer_binding(self):
        env = run_vm("let x = 10 for x in [1, 2] { }")
        self.assertEqual(env["x"], 10)

    def test_vm_for_loop_restores_const_outer_binding(self):
        env = run_vm("const x = 10 for x in [1, 2] { x = 5 }")
        self.assertEqual(env["x"], 10)

    def test_vm_for_loop_variable_is_mutable(self):
        env = run_vm("for x in [1] { x = x + 10 let y = x }")
        self.assertEqual(env["y"], 11)
        self.assertNotIn("x", env)

    def test_vm_for_loop_body_declarations_leak(self):
        env = run_vm("for x in [1, 2] { let y = x + 1 }")
        self.assertEqual(env, {"y": 3})

    def test_vm_for_loop_over_empty_list(self):
        env = run_vm("let total = 0 for x in [] { total = total + 1 }")
        self.assertEqual(env, {"total": 0})

    def test_vm_for_loop_break_stops_iteration(self):
        program = Parser(
            Lexer("for x in [1, 2, 3, 4] { if x == 3 { break } print(x) }")
        ).parse_program()
        vm = VM()
        vm.run(Compiler().compile(program))
        self.assertEqual(vm.output, [1, 2])

    def test_vm_for_loop_continue_skips_item(self):
        program = Parser(
            Lexer("for x in [1, 2, 3, 4] { if x == 2 { continue } print(x) }")
        ).parse_program()
        vm = VM()
        vm.run(Compiler().compile(program))
        self.assertEqual(vm.output, [1, 3, 4])

    def test_vm_break_only_exits_inner_loop(self):
        program = Parser(
            Lexer(
                "for x in [1, 2] { "
                "for y in [10, 20] { if y == 20 { break } print(x + y) } "
                "print(x) }"
            )
        ).parse_program()
        vm = VM()
        vm.run(Compiler().compile(program))
        self.assertEqual(vm.output, [11, 1, 12, 2])

    def test_vm_nested_for_loops(self):
        env = run_vm(
            "let total = 0 "
            "for x in [1, 2] { for y in [10, 20] { total = total + x + y } }"
        )
        self.assertEqual(env["total"], 66)

    def test_vm_nested_for_loops_restore_same_name(self):
        env = run_vm(
            "let total = 0 "
            "for x in [1, 2] { for x in [10, 20] { total = total + x } total = total + x }"
        )
        self.assertEqual(env["total"], 63)

    def test_vm_for_loop_evaluates_iterable_once(self):
        program = Parser(
            Lexer("fn values() { print(1) [1, 2] } for x in values() { print(x) }")
        ).parse_program()
        vm = VM()
        vm.run(Compiler().compile(program))
        self.assertEqual(vm.output, [1, 1, 2])

    def test_vm_for_loop_over_function_parameter(self):
        program = Parser(
            Lexer("fn show(xs) { for x in xs { print(x) } 0 } let y = show([1, 2])")
        ).parse_program()
        vm = VM()
        env = vm.run(Compiler().compile(program))
        self.assertEqual(env["y"], 0)
        self.assertEqual(vm.output, [1, 2])

    def test_vm_for_loop_restores_parameter(self):
        env = run_vm("fn f(x) { for x in [1, 2] { } x } let y = f(10)")
        self.assertEqual(env, {"y": 10})

    def test_vm_for_loop_requires_list(self):
        with self.assertRaisesRegex(SwarnaTypeError, "`for` expects a List or Map, got Int"):
            run_vm("for x in 1 { print(x) }")

    def test_vm_for_loop_rejects_string_iteration(self):
        with self.assertRaisesRegex(SwarnaTypeError, "`for` expects a List or Map, got String"):
            run_vm('for x in "abc" { print(x) }')

    def test_vm_for_loops_match_interpreter(self):
        sources = [
            "let total = 0 for x in [1, 2, 3] { total = total + x } print(total)",
            "let x = 10 for x in [1, 2] { print(x) } print(x)",
            "for x in [] { print(x) } print(1)",
            "let total = 0 for x in [1, 2] { for y in [10, 20] { total = total + x + y } } print(total)",
            "let total = 0 for x in [1, 2] { for x in [10, 20] { total = total + x } total = total + x } print(total)",
            "fn show(xs) { for x in xs { print(x) } 0 } print(show([1, 2]))",
            "const x = 10 for x in [1, 2] { x = 5 } print(x)",
        ]
        for source in sources:
            with self.subTest(source=source):
                program = Parser(Lexer(source)).parse_program()
                interpreter = Interpreter()
                expected_env = interpreter.eval(program)

                vm = VM()
                actual_env = vm.run(Compiler().compile(program))

                self.assertEqual(actual_env, expected_env)
                self.assertEqual(vm.output, interpreter.output)

    def test_vm_for_loop_errors_match_interpreter(self):
        sources = [
            "for x in 1 { print(x) }",
            'for x in "abc" { print(x) }',
        ]
        for source in sources:
            with self.subTest(source=source):
                program = Parser(Lexer(source)).parse_program()
                with self.assertRaises(TypeError):
                    Interpreter().eval(program)
                with self.assertRaises(TypeError):
                    VM().run(Compiler().compile(program))

    def test_vm_for_loop_restores_outer_binding_on_error(self):
        vm = VM()
        program = Parser(Lexer("let x = 10 for x in [1] { let y = missing }")).parse_program()
        with self.assertRaises(SwarnaNameError):
            vm.run(Compiler().compile(program))
        self.assertEqual(vm.env["x"], 10)

    def test_vm_for_loop_removes_loop_variable_on_error(self):
        vm = VM()
        program = Parser(Lexer("for x in [1] { let y = missing }")).parse_program()
        with self.assertRaises(SwarnaNameError):
            vm.run(Compiler().compile(program))
        self.assertNotIn("x", vm.env)

    def test_vm_nested_for_loop_restores_bindings_on_error(self):
        vm = VM()
        program = Parser(
            Lexer("let x = 10 for x in [1] { for x in [2] { let y = missing } }")
        ).parse_program()
        with self.assertRaises(SwarnaNameError):
            vm.run(Compiler().compile(program))
        self.assertEqual(vm.env["x"], 10)

    def test_iter_next_requires_iter_start(self):
        code = [Instruction(Op.ITER_NEXT, 1), Instruction(Op.HALT)]
        with self.assertRaisesRegex(RuntimeError, "ITER_NEXT without ITER_START"):
            VM().run(code)


class TestVMFunctions(unittest.TestCase):
    def test_vm_uses_seeded_bindings(self):
        vm = VM()
        vm.env["x"] = 5
        program = Parser(Lexer("print(x + 1)")).parse_program()
        vm.run(Compiler().compile(program))
        self.assertEqual(vm.output, [6])

    def test_vm_function_call(self):
        env = run_vm("fn add(a: Int, b: Int) -> Int { a + b } let x = add(2, 3)")
        self.assertEqual(env["x"], 5)

    def test_vm_function_call_before_declaration(self):
        env = run_vm("let x = add(2, 3) fn add(a: Int, b: Int) -> Int { a + b }")
        self.assertEqual(env["x"], 5)

    def test_vm_function_call_with_zero_arguments(self):
        env = run_vm("fn answer() -> Int { 42 } let x = answer()")
        self.assertEqual(env["x"], 42)

    def test_vm_function_call_as_argument(self):
        env = run_vm("fn add(a: Int, b: Int) -> Int { a + b } fn one() -> Int { 1 } let x = add(one(), 2)")
        self.assertEqual(env["x"], 3)

    def test_vm_recursive_function(self):
        env = run_vm(
            "fn factorial(n: Int) -> Int { if n <= 1 { 1 } else { n * factorial(n - 1) } } "
            "let x = factorial(5)"
        )
        self.assertEqual(env["x"], 120)

    def test_vm_mutually_recursive_functions(self):
        env = run_vm(
            "fn is_even(n: Int) -> Bool { if n == 0 { true } else { is_odd(n - 1) } } "
            "fn is_odd(n: Int) -> Bool { if n == 0 { false } else { is_even(n - 1) } } "
            "let x = is_even(4)"
        )
        self.assertIs(env["x"], True)

    def test_vm_function_with_while_loop(self):
        env = run_vm(
            "fn sum_to(n: Int) -> Int { let total = 0 let i = 1 "
            "while i <= n { total = total + i i = i + 1 } total } "
            "let x = sum_to(5)"
        )
        self.assertEqual(env["x"], 15)

    def test_vm_function_local_binding_does_not_leak(self):
        env = run_vm("fn f() -> Int { let local = 1 local } let x = f()")
        self.assertEqual(env, {"x": 1})

    def test_vm_function_reads_global_binding(self):
        env = run_vm("let base = 10 fn add_base(x: Int) -> Int { x + base } let y = add_base(5)")
        self.assertEqual(env["y"], 15)

    def test_vm_function_assignment_does_not_mutate_global(self):
        env = run_vm("let x = 1 fn bump() -> Int { x = x + 1 x } let y = bump()")
        self.assertEqual(env, {"x": 1, "y": 2})

    def test_vm_function_print_output(self):
        program = Parser(Lexer("fn show(x: Int) -> Int { print(x) x + 1 } let y = show(4)")).parse_program()
        vm = VM()
        env = vm.run(Compiler().compile(program))
        self.assertEqual(env["y"], 5)
        self.assertEqual(vm.output, [4])

    def test_vm_function_calls_match_interpreter(self):
        sources = [
            "fn add(a: Int, b: Int) -> Int { a + b } let x = add(2, 3) print(x)",
            "fn one() -> Int { 1 } fn add(a: Int, b: Int) -> Int { a + b } print(add(one(), 2))",
            "fn factorial(n: Int) -> Int { if n <= 1 { 1 } else { n * factorial(n - 1) } } print(factorial(5))",
            "let base = 10 fn add_base(x: Int) -> Int { x + base } print(add_base(5))",
            "let x = 1 fn bump() -> Int { x = x + 1 x } print(bump()) print(x)",
            "fn sum_to(n: Int) -> Int { let total = 0 let i = 1 while i <= n { total = total + i i = i + 1 } total } print(sum_to(5))",
            "fn is_even(n: Int) -> Bool { if n == 0 { true } else { is_odd(n - 1) } } "
            "fn is_odd(n: Int) -> Bool { if n == 0 { false } else { is_even(n - 1) } } print(is_even(4))",
            "fn f() -> Int { const x = 1 x } let y = f() print(y)",
            "fn f() -> Int { let local = 1 local } let x = f() print(x)",
        ]
        for source in sources:
            with self.subTest(source=source):
                program = Parser(Lexer(source)).parse_program()
                interpreter = Interpreter()
                expected_env = interpreter.eval(program)

                vm = VM()
                actual_env = vm.run(Compiler().compile(program))

                self.assertEqual(actual_env, expected_env)
                self.assertEqual(vm.output, interpreter.output)

    def test_vm_wrong_argument_count(self):
        with self.assertRaisesRegex(RuntimeError, "expects 2 arguments, got 1"):
            run_vm("fn add(a: Int, b: Int) -> Int { a + b } let x = add(1)")

    def test_vm_undefined_function(self):
        with self.assertRaisesRegex(NameError, "Undefined function 'missing'"):
            run_vm("let x = missing(1)")

    def test_vm_bare_function_name_must_be_called(self):
        with self.assertRaisesRegex(NameError, "must be called"):
            run_vm("fn f() -> Int { 1 } let x = f")

    def test_vm_assignment_to_function_is_rejected(self):
        with self.assertRaisesRegex(NameError, "Cannot assign to function 'f'"):
            run_vm("fn f() -> Int { 1 } f = 2")

    def test_vm_function_local_const_assignment_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Cannot assign to const binding 'x'"):
            run_vm("fn f() -> Int { const x = 1 x = 2 x } let y = f()")

    def test_vm_recursion_depth_limit(self):
        with self.assertRaisesRegex(RuntimeError, "Maximum call depth"):
            run_vm("fn loop(n: Int) -> Int { loop(n + 1) } let x = loop(0)")


class TestVMCollections(unittest.TestCase):
    def test_vm_list_literal_and_index(self):
        env = run_vm("let xs = [1, 2, 3] let x = xs[0] let y = xs[-1]")
        self.assertEqual(env["xs"], [1, 2, 3])
        self.assertEqual(env["x"], 1)
        self.assertEqual(env["y"], 3)

    def test_vm_nested_list_index(self):
        env = run_vm("let xs = [[1], [2, 3]] let x = xs[1][0]")
        self.assertEqual(env["x"], 2)

    def test_vm_list_concatenation(self):
        env = run_vm("let xs = [1, 2] + [3, 4]")
        self.assertEqual(env["xs"], [1, 2, 3, 4])

    def test_vm_list_equality(self):
        env = run_vm("let x = [1, 2] == [1, 2] let y = [1] != [2]")
        self.assertIs(env["x"], True)
        self.assertIs(env["y"], True)

    def test_vm_len_of_list_and_string(self):
        env = run_vm('let xs = [1, 2, 3] let a = len(xs) let b = len("hello")')
        self.assertEqual(env["a"], 3)
        self.assertEqual(env["b"], 5)

    def test_vm_empty_list(self):
        env = run_vm("let xs = [] let n = len(xs)")
        self.assertEqual(env["xs"], [])
        self.assertEqual(env["n"], 0)

    def test_vm_list_print_output(self):
        program = Parser(Lexer("print([1, 2, 3])")).parse_program()
        vm = VM()
        vm.run(Compiler().compile(program))
        self.assertEqual(vm.output, [[1, 2, 3]])

    def test_vm_index_out_of_range(self):
        with self.assertRaisesRegex(RuntimeError, "Index 3 is out of range for a list of length 2"):
            run_vm("let xs = [1, 2] let x = xs[3]")

    def test_vm_index_must_be_int(self):
        with self.assertRaisesRegex(TypeError, "List index must be Int"):
            run_vm('let xs = [1, 2] let x = xs["a"]')

    def test_vm_only_lists_and_maps_can_be_indexed(self):
        with self.assertRaisesRegex(TypeError, "Cannot index Int"):
            run_vm("let x = 1[0]")

    def test_vm_len_requires_collection_or_string(self):
        with self.assertRaisesRegex(
            TypeError,
            "`len` expects a List, Map, or String, got Int",
        ):
            run_vm("let n = len(1)")

    def test_vm_map_literal_and_index(self):
        env = run_vm('let m = { "a": 1, "b": 2 } let x = m["a"]')
        self.assertEqual(env["m"], {"a": 1, "b": 2})
        self.assertEqual(env["x"], 1)

    def test_vm_empty_map(self):
        env = run_vm("let m = {} let n = len(m)")
        self.assertEqual(env["m"], {})
        self.assertEqual(env["n"], 0)

    def test_vm_nested_map_index(self):
        env = run_vm('let m = { "a": { "b": 2 } } let x = m["a"]["b"]')
        self.assertEqual(env["x"], 2)

    def test_vm_map_index_assignment_updates_existing_key(self):
        env = run_vm('let m = { "a": 1 } m["a"] = 2')
        self.assertEqual(env["m"], {"a": 2})

    def test_vm_map_index_assignment_adds_new_key(self):
        env = run_vm('let m = { "a": 1 } m["b"] = 2')
        self.assertEqual(env["m"], {"a": 1, "b": 2})

    def test_vm_map_index_assignment_accumulates(self):
        env = run_vm(
            'let totals = { "red": 0 } '
            'totals["red"] = totals["red"] + 5 '
            'totals["red"] = totals["red"] + 3'
        )
        self.assertEqual(env["totals"], {"red": 8})

    def test_vm_nested_map_index_assignment(self):
        env = run_vm('let m = { "a": { "b": 1 } } m["a"]["b"] = 2')
        self.assertEqual(env["m"], {"a": {"b": 2}})

    def test_vm_list_index_assignment_rejected(self):
        with self.assertRaisesRegex(
            SwarnaTypeError, "Lists are immutable; cannot assign to an index"
        ):
            run_vm("let xs = [1, 2] xs[0] = 3")

    def test_vm_const_map_index_assignment_rejected(self):
        with self.assertRaisesRegex(
            SwarnaRuntimeError, "Cannot assign to const binding 'm'"
        ):
            run_vm('const m = { "a": 1 } m["a"] = 2')

    def test_vm_index_assignment_to_undefined_name(self):
        with self.assertRaisesRegex(SwarnaNameError, "Undefined name 'm'"):
            run_vm('m["a"] = 1')

    def test_vm_index_assignment_requires_map(self):
        with self.assertRaisesRegex(
            SwarnaTypeError, "Cannot assign to Int"
        ):
            run_vm("let x = 1 x[0] = 2")

    def test_vm_index_assignment_key_must_be_hashable(self):
        with self.assertRaisesRegex(
            SwarnaTypeError,
            "Map keys must be Int, Float, String, or Bool, got List",
        ):
            run_vm('let m = { "a": 1 } m[[1]] = 2')

    def test_vm_get_existing_key(self):
        env = run_vm('let m = { "a": 1 } let x = get(m, "a", 0)')
        self.assertEqual(env["x"], 1)

    def test_vm_get_missing_key_returns_default(self):
        env = run_vm('let m = { "a": 1 } let x = get(m, "b", 0)')
        self.assertEqual(env["x"], 0)

    def test_vm_get_on_empty_map_returns_default(self):
        env = run_vm('let m = {} let x = get(m, "a", 3)')
        self.assertEqual(env["x"], 3)

    def test_vm_get_requires_map(self):
        with self.assertRaisesRegex(SwarnaTypeError, "`get` expects a Map, got Int"):
            run_vm('let x = get(1, "a", 0)')

    def test_vm_get_rejects_unhashable_key(self):
        with self.assertRaisesRegex(
            SwarnaTypeError,
            "Map keys must be Int, Float, String, or Bool, got List",
        ):
            run_vm('let m = { "a": 1 } let x = get(m, [1], 0)')

    def test_vm_map_equality(self):
        env = run_vm('let x = { "a": 1 } == { "a": 1 }')
        self.assertIs(env["x"], True)

    def test_vm_len_of_map(self):
        env = run_vm('let n = len({ "a": 1, "b": 2 })')
        self.assertEqual(env["n"], 2)

    def test_vm_missing_key(self):
        with self.assertRaisesRegex(RuntimeError, 'Key "missing" is not in the map'):
            run_vm('let m = { "a": 1 } let x = m["missing"]')

    def test_vm_map_print_output(self):
        program = Parser(Lexer('print({ "a": 1, "b": 2 })')).parse_program()
        vm = VM()
        vm.run(Compiler().compile(program))
        self.assertEqual(vm.output, [{"a": 1, "b": 2}])

    def test_vm_for_loop_iterates_map_keys(self):
        program = Parser(Lexer('for k in { "a": 1, "b": 2 } { print(k) }')).parse_program()
        vm = VM()
        vm.run(Compiler().compile(program))
        self.assertEqual(vm.output, ["a", "b"])

    def test_vm_map_literal_rejects_list_key(self):
        with self.assertRaisesRegex(
            TypeError,
            "Map keys must be Int, Float, String, or Bool, got List",
        ):
            run_vm("let m = { [1]: 2 }")

    def test_vm_collections_match_interpreter(self):
        sources = [
            "let xs = [1, 2, 3] print(xs[0] + len(xs))",
            "let xs = [1] + [2, 3] print(xs)",
            "let xs = [[1], [2, 3]] print(xs[1][0])",
            "let x = [1, 2] == [1, 2] print(x)",
            "fn first(xs) { xs[0] } print(first([9, 8]))",
            'let m = { "a": 1 } print(m["a"] + len(m))',
            'print({ "a": 1, "b": 2 })',
            'let m = { "a": { "b": 2 } } print(m["a"]["b"])',
        ]
        for source in sources:
            with self.subTest(source=source):
                program = Parser(Lexer(source)).parse_program()
                interpreter = Interpreter()
                expected_env = interpreter.eval(program)

                vm = VM()
                actual_env = vm.run(Compiler().compile(program))

                self.assertEqual(actual_env, expected_env)
                self.assertEqual(vm.output, interpreter.output)


class TestVMFiles(unittest.TestCase):
    def test_vm_read_file_returns_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.txt"
            path.write_text("hello\nworld", encoding="utf-8")
            env = run_vm(f"let text = read_file({json.dumps(path.as_posix())})")
            self.assertEqual(env["text"], "hello\nworld")

    def test_vm_read_file_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.txt"
            with self.assertRaisesRegex(RuntimeError, "file not found"):
                run_vm(f"let text = read_file({json.dumps(path.as_posix())})")

    def test_vm_read_file_requires_string_path(self):
        with self.assertRaisesRegex(TypeError, "`read_file` expects a String path, got Int"):
            run_vm("let text = read_file(1)")

    def test_vm_read_file_matches_interpreter(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.txt"
            path.write_text("one\ntwo\n", encoding="utf-8")
            source = f'let text = read_file({json.dumps(path.as_posix())}) print(text)'
            program = Parser(Lexer(source)).parse_program()

            interpreter = Interpreter()
            expected_env = interpreter.eval(program)

            vm = VM()
            actual_env = vm.run(Compiler().compile(program))

            self.assertEqual(actual_env, expected_env)
            self.assertEqual(vm.output, interpreter.output)


class TestVMCsv(unittest.TestCase):
    @staticmethod
    def _write(directory: str, text: str) -> Path:
        path = Path(directory) / "scores.csv"
        path.write_text(text, encoding="utf-8")
        return path

    def test_vm_read_csv_returns_typed_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                "name,team,score\nAda,Blue,88\nGrace,Blue,92.5\n",
            )
            env = run_vm(
                f"let rows = read_csv({json.dumps(path.as_posix())}, "
                "{ name: String, team: String, score: Float })"
            )
        self.assertEqual(
            env["rows"],
            [
                {"name": "Ada", "team": "Blue", "score": 88.0},
                {"name": "Grace", "team": "Blue", "score": 92.5},
            ],
        )

    def test_vm_read_csv_bad_cell_has_file_location(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                "name,team,score\nAda,Blue,88\nMargaret,Red,n/a\n",
            )
            with self.assertRaises(SwarnaRuntimeError) as raised:
                run_vm(
                    f"let rows = read_csv({json.dumps(path.as_posix())}, "
                    "{ name: String, team: String, score: Float })"
                )
        error = raised.exception
        self.assertEqual(error.span, SourceSpan(3, 14, 3))
        self.assertEqual(error.source_name, path.as_posix())
        self.assertIn("expected a Float in column 'score'", error.message)

    def test_vm_read_csv_requires_string_path(self):
        with self.assertRaisesRegex(TypeError, "`read_csv` expects a String path, got Int"):
            run_vm("let rows = read_csv(1, { name: String })")

    def test_vm_read_csv_matches_interpreter(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                "name,team,score\nAda,Blue,88\nGrace,Blue,92.5\n",
            )
            source = (
                f"let rows = read_csv({json.dumps(path.as_posix())}, "
                "{ name: String, team: String, score: Float })"
                ' let total = 0.0 for row in rows { total = total + row["score"] }'
                " print(total)"
            )
            program = Parser(Lexer(source)).parse_program()

            interpreter = Interpreter()
            expected_env = interpreter.eval(program)

            vm = VM()
            actual_env = vm.run(Compiler().compile(program))

        self.assertEqual(actual_env, expected_env)
        self.assertEqual(vm.output, interpreter.output)


if __name__ == "__main__":
    unittest.main()
