import unittest

from compiler.codegen.compiler import Compiler
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from runtime.interpreter import Interpreter
from runtime.vm import VM
from runtime.values import format_value


def _parse(source: str):
    return Parser(Lexer(source)).parse_program()


def _interpreter_output(source: str) -> list[str]:
    interpreter = Interpreter()
    interpreter.eval(_parse(source))
    return [format_value(value) for value in interpreter.output]


def _vm_output(source: str) -> list[str]:
    vm = VM()
    vm.run(Compiler().compile(_parse(source)))
    return [format_value(value) for value in vm.output]


class TestFloatAnnotationCoercion(unittest.TestCase):
    def _assert_both(self, source: str, expected: list[str]) -> None:
        self.assertEqual(_interpreter_output(source), expected)
        self.assertEqual(_vm_output(source), expected)

    def test_annotated_let_declaration(self):
        self._assert_both("let x: Float = 1 print(str(x))", ["1.0"])

    def test_annotated_let_assignment(self):
        self._assert_both("let x: Float = 1.0 x = 2 print(str(x))", ["2.0"])

    def test_annotated_const(self):
        self._assert_both("const x: Float = 1 print(str(x))", ["1.0"])

    def test_annotated_list(self):
        self._assert_both("let xs: List[Float] = [1, 2] print(str(xs[0]))", ["1.0"])

    def test_annotated_map_index_assignment(self):
        self._assert_both(
            'let m: Map[String, Float] = {} m["a"] = 1 print(str(m["a"]))',
            ["1.0"],
        )

    def test_function_argument_and_return(self):
        self._assert_both("fn f(x: Float) -> Float { x } print(str(f(1)))", ["1.0"])


if __name__ == "__main__":
    unittest.main()
