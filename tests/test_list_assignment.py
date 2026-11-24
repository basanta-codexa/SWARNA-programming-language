import unittest

from compiler.codegen.compiler import Compiler
from compiler.diagnostics import SwarnaRuntimeError, SwarnaSemanticError
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


class TestListAssignment(unittest.TestCase):
    def _assert_both(self, source: str, expected: list[str]) -> None:
        self.assertEqual(_interpreter_output(source), expected)
        self.assertEqual(_vm_output(source), expected)

    def test_positive_index(self):
        self._assert_both("let xs = [1, 2] xs[0] = 3 print(xs)", ["[3, 2]"])

    def test_negative_index(self):
        self._assert_both("let xs = [1, 2] xs[-1] = 3 print(xs)", ["[1, 3]"])

    def test_annotated_float_element(self):
        source = "let xs: List[Float] = [1.0, 2.0] xs[0] = 3 print(str(xs[0]))"
        self._assert_both(source, ["3.0"])

    def test_out_of_range_is_diagnostic(self):
        for runner in (_interpreter_output, _vm_output):
            with self.assertRaises(SwarnaRuntimeError):
                runner("let xs = [1, 2] xs[5] = 3")

    def test_checker_rejects_const_list(self):
        with self.assertRaises(SwarnaSemanticError):
            TypeChecker().check(_parse("const xs = [1, 2] xs[0] = 3"))

    def test_checker_rejects_wrong_element_type(self):
        with self.assertRaises(SwarnaSemanticError):
            TypeChecker().check(_parse('let xs = [1, 2] xs[0] = "a"'))

    def test_checker_rejects_float_index(self):
        with self.assertRaises(SwarnaSemanticError):
            TypeChecker().check(_parse("let xs = [1, 2] xs[1.0] = 3"))


if __name__ == "__main__":
    unittest.main()
