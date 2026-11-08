import unittest

from compiler.codegen.compiler import Compiler
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from runtime.vm import VM


def run_vm(source: str) -> dict[str, int | bool]:
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
        self.assertEqual(env["x"], -3)

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


if __name__ == "__main__":
    unittest.main()
