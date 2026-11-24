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


class TestListSlices(unittest.TestCase):
    def _assert_both(self, source: str, expected: list[str]) -> None:
        self.assertEqual(_interpreter_output(source), expected)
        self.assertEqual(_vm_output(source), expected)

    def test_checker_keeps_element_type(self):
        checker = TypeChecker()
        checker.check(_parse('let xs = [1, 2, 3][1:]'))
        self.assertEqual(checker.env["xs"].type.label, "List[Int]")

    def test_basic_slice(self):
        self._assert_both('print([1, 2, 3, 4][1:3])', ["[2, 3]"])

    def test_negative_bounds(self):
        self._assert_both('print([1, 2, 3, 4][-3:-1])', ["[2, 3]"])

    def test_omitted_start(self):
        self._assert_both('print([1, 2, 3][:2])', ["[1, 2]"])

    def test_omitted_end(self):
        self._assert_both('print([1, 2, 3][2:])', ["[3]"])

    def test_empty_and_full(self):
        self._assert_both('print([1, 2][1:1]) print([1, 2][:])', ["[]", "[1, 2]"])

    def test_nested_list_slice(self):
        self._assert_both('print([[1], [2], [3]][1:])', ["[[2], [3]]"])

    def test_map_slice_is_rejected(self):
        with self.assertRaises(SwarnaSemanticError):
            TypeChecker().check(_parse('let xs = { "a": 1 }[0:1]'))


if __name__ == "__main__":
    unittest.main()
