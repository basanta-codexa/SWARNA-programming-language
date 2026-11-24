import unittest

from compiler.codegen.compiler import Compiler
from compiler.diagnostics import SwarnaRuntimeError
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from runtime.interpreter import Interpreter
from runtime.vm import VM


def _parse(source: str):
    return Parser(Lexer(source)).parse_program()


def _error_span(test: unittest.TestCase, runner, source: str):
    with test.assertRaises(SwarnaRuntimeError) as raised:
        runner(source)
    return raised.exception.span


class TestIndexDiagnosticParity(unittest.TestCase):
    def _interpreter(self, source: str) -> None:
        Interpreter().eval(_parse(source))

    def _vm(self, source: str) -> None:
        VM().run(Compiler().compile(_parse(source)))

    def _assert_same_span(self, source: str) -> None:
        interpreter_span = _error_span(self, self._interpreter, source)
        vm_span = _error_span(self, self._vm, source)
        self.assertEqual(vm_span, interpreter_span)

    def test_list_read_out_of_range_span(self):
        self._assert_same_span("let xs = [] print(xs[0])")

    def test_nested_list_read_out_of_range_span(self):
        self._assert_same_span("let xs = [[1]] print(xs[0][4])")

    def test_string_read_out_of_range_span(self):
        self._assert_same_span('let s = "ab" print(s[7])')

    def test_list_assignment_out_of_range_span(self):
        self._assert_same_span("let xs = [1] xs[9] = 2")


if __name__ == "__main__":
    unittest.main()
