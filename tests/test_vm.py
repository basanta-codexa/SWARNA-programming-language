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


if __name__ == "__main__":
    unittest.main()
