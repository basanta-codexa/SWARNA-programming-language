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


class TestAppend(unittest.TestCase):
    def _assert_both(self, source: str, expected: list[str]) -> None:
        self.assertEqual(_interpreter_output(source), expected)
        self.assertEqual(_vm_output(source), expected)

    def test_append_mutates_list(self):
        self._assert_both("let xs = [1] append(xs, 2) print(xs)", ["[1, 2]"])

    def test_append_returns_unit(self):
        self._assert_both("let xs = [1] let u = append(xs, 2) print(u)", ["()"])

    def test_annotated_float_list(self):
        source = "let xs: List[Float] = [1.0] append(xs, 2) print(str(xs[1]))"
        self._assert_both(source, ["2.0"])

    def test_empty_list_refines(self):
        checker = TypeChecker()
        checker.check(_parse("let xs = [] append(xs, 1)"))
        self.assertEqual(checker.env["xs"].type.label, "List[Int]")

    def test_checker_rejects_wrong_element_type(self):
        with self.assertRaises(SwarnaSemanticError):
            TypeChecker().check(_parse('let xs = [1] append(xs, "a")'))

    def test_checker_rejects_empty_list_second_wrong_type(self):
        with self.assertRaises(SwarnaSemanticError):
            TypeChecker().check(_parse('let xs = [] append(xs, 1) append(xs, "a")'))

    def test_checker_rejects_non_list(self):
        with self.assertRaises(SwarnaSemanticError):
            TypeChecker().check(_parse("append(1, 2)"))

    def test_checker_rejects_wrong_argument_count(self):
        with self.assertRaises(SwarnaSemanticError):
            TypeChecker().check(_parse("append([1])"))


class TestFirstLast(unittest.TestCase):
    def _assert_both(self, source: str, expected: list[str]) -> None:
        self.assertEqual(_interpreter_output(source), expected)
        self.assertEqual(_vm_output(source), expected)

    def test_checker_preserves_element_type(self):
        checker = TypeChecker()
        checker.check(_parse("let x = first([1, 2]) let y = last([1, 2])"))
        self.assertEqual(checker.env["x"].type.label, "Int")
        self.assertEqual(checker.env["y"].type.label, "Int")

    def test_first(self):
        self._assert_both("print(first([1, 2]))", ["1"])

    def test_last(self):
        self._assert_both("print(last([1, 2]))", ["2"])

    def test_string_list(self):
        self._assert_both('print(first(["a", "b"])) print(last(["a", "b"]))', ["a", "b"])

    def test_empty_list_is_diagnostic(self):
        with self.assertRaises(SwarnaRuntimeError):
            _interpreter_output("print(first([]))")
        with self.assertRaises(SwarnaRuntimeError):
            _vm_output("print(last([]))")

    def test_checker_rejects_non_list(self):
        with self.assertRaises(SwarnaSemanticError):
            TypeChecker().check(_parse("first(1)"))

    def test_checker_rejects_wrong_argument_count(self):
        with self.assertRaises(SwarnaSemanticError):
            TypeChecker().check(_parse("last([1], [2])"))


class TestSum(unittest.TestCase):
    def _assert_both(self, source: str, expected: list[str]) -> None:
        self.assertEqual(_interpreter_output(source), expected)
        self.assertEqual(_vm_output(source), expected)

    def test_checker_returns_int_for_int_list(self):
        checker = TypeChecker()
        checker.check(_parse("let total = sum([1, 2, 3])"))
        self.assertEqual(checker.env["total"].type.label, "Int")

    def test_checker_returns_float_for_float_list(self):
        checker = TypeChecker()
        checker.check(_parse("let total = sum([1.5, 2.5])"))
        self.assertEqual(checker.env["total"].type.label, "Float")

    def test_sum_ints(self):
        self._assert_both("print(sum([1, 2, 3]))", ["6"])

    def test_sum_floats(self):
        self._assert_both("print(str(sum([1.5, 2.5])))", ["4.0"])

    def test_sum_empty_list(self):
        self._assert_both("print(sum([]))", ["0"])

    def test_checker_rejects_string_list(self):
        with self.assertRaises(SwarnaSemanticError):
            TypeChecker().check(_parse('sum(["a", "b"])'))

    def test_checker_rejects_non_list(self):
        with self.assertRaises(SwarnaSemanticError):
            TypeChecker().check(_parse("sum(1)"))

    def test_checker_rejects_wrong_argument_count(self):
        with self.assertRaises(SwarnaSemanticError):
            TypeChecker().check(_parse("sum([1], [2])"))


if __name__ == "__main__":
    unittest.main()
