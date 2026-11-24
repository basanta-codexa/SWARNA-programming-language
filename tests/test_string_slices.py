import unittest

from compiler.codegen.compiler import Compiler
from compiler.diagnostics import SwarnaSemanticError
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.checker import TypeChecker
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


class TestStringSlices(unittest.TestCase):
    def _assert_both(self, source: str, expected: list[str]) -> None:
        self.assertEqual(_interpreter_output(source), expected)
        self.assertEqual(_vm_output(source), expected)

    def test_basic_slice(self):
        self._assert_both('print("hello"[1:3])', ["el"])

    def test_negative_bounds(self):
        self._assert_both('print("hello"[-4:-1])', ["ell"])

    def test_omitted_start(self):
        self._assert_both('print("hello"[:2])', ["he"])

    def test_omitted_end(self):
        self._assert_both('print("hello"[3:])', ["lo"])

    def test_full_slice(self):
        self._assert_both('print("hello"[:])', ["hello"])

    def test_empty_slice(self):
        self._assert_both('print("hello"[2:2])', [""])

    def test_checker_rejects_map_slice(self):
        with self.assertRaises(SwarnaSemanticError):
            TypeChecker().check(_parse('let m = { "a": 1 }[0:1]'))


if __name__ == "__main__":
    unittest.main()
