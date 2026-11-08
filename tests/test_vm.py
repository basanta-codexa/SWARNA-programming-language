import unittest

from compiler.bytecode.instructions import Instruction, Op
from compiler.codegen.compiler import Compiler
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
        env = run_vm("let mut x = 1 x = x + 2")
        self.assertEqual(env["x"], 3)

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
            "let mut x = 0 if 1 < 2 { x = 1 } else { x = 2 } print(x)",
            "let mut x = 0 if 1 > 2 { x = 1 } else { x = 2 } print(x)",
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

    def test_vm_while_matches_interpreter(self):
        sources = [
            "let mut i = 0 while i < 3 { i = i + 1 } print(i)",
            "let mut i = 5 while i < 3 { i = i + 1 } print(i)",
            "let mut i = 0 while i < 3 { if i == 1 { print(99) } i = i + 1 } print(i)",
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
            "let mut i = 0.5 while i < 2.5 { i = i + 0.5 } print(i)",
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


if __name__ == "__main__":
    unittest.main()
