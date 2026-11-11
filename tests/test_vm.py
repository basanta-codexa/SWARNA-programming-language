import unittest

from compiler.bytecode.instructions import Instruction, Op
from compiler.codegen.compiler import Compiler
from compiler.diagnostics import SourceSpan, SwarnaNameError, SwarnaRuntimeError, SwarnaTypeError, SwarnaZeroDivisionError
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from runtime.interpreter import Interpreter
from runtime.vm import VM


def run_vm(source: str) -> dict[str, int | float | bool | str]:
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

    def test_vm_undefined_name(self):
        with self.assertRaises(NameError):
            run_vm("let y = x + 1")

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


if __name__ == "__main__":
    unittest.main()
