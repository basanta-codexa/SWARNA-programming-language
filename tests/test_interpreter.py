import unittest

from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from runtime.interpreter import Interpreter


def run(source: str) -> dict[str, int]:
    program = Parser(Lexer(source)).parse_program()
    return Interpreter().eval(program)


class TestInterpreter(unittest.TestCase):
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
        self.assertEqual(env["x"], 3)

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


if __name__ == "__main__":
    unittest.main()
