import unittest

from compiler.codegen.compiler import Compiler
from compiler.diagnostics import SwarnaSemanticError
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.checker import Type, TypeChecker
from runtime.interpreter import Interpreter
from runtime.vm import VM
from runtime.values import format_value


def _parse(source: str):
    return Parser(Lexer(source)).parse_program()


def _check(source: str):
    checker = TypeChecker()
    checker.check(_parse(source))
    return checker


def _interpreter_output(source: str) -> list[str]:
    interpreter = Interpreter()
    interpreter.eval(_parse(source))
    return [format_value(value) for value in interpreter.output]


def _vm_output(source: str) -> list[str]:
    vm = VM()
    vm.run(Compiler().compile(_parse(source)))
    return [format_value(value) for value in vm.output]


class TestUpperLower(unittest.TestCase):
    def _assert_both(self, source: str, expected: list[str]) -> None:
        self.assertEqual(_interpreter_output(source), expected)
        self.assertEqual(_vm_output(source), expected)

    def test_checker_returns_string(self):
        checker = _check('let s = upper("aBc")')
        self.assertIs(checker.env["s"].type, Type.STRING)

    def test_upper(self):
        self._assert_both('print(upper("hello"))', ["HELLO"])

    def test_lower(self):
        self._assert_both('print(lower("HeLLo"))', ["hello"])

    def test_non_ascii_input_is_preserved(self):
        self._assert_both('print(upper("café"))', ["CAFÉ"])

    def test_wrong_argument_type(self):
        with self.assertRaises(SwarnaSemanticError):
            _check("upper(1)")

    def test_wrong_argument_count(self):
        with self.assertRaises(SwarnaSemanticError):
            _check('upper("a", "b")')


class TestContains(unittest.TestCase):
    def _assert_both(self, source: str, expected: list[str]) -> None:
        self.assertEqual(_interpreter_output(source), expected)
        self.assertEqual(_vm_output(source), expected)

    def test_checker_returns_bool(self):
        checker = _check('let b = contains("hello", "ell")')
        self.assertIs(checker.env["b"].type, Type.BOOL)

    def test_found(self):
        self._assert_both('print(contains("hello", "ell"))', ["true"])

    def test_not_found(self):
        self._assert_both('print(contains("hello", "xyz"))', ["false"])

    def test_empty_part(self):
        self._assert_both('print(contains("hello", ""))', ["true"])

    def test_wrong_argument_count(self):
        with self.assertRaises(SwarnaSemanticError):
            _check('contains("hello")')

    def test_wrong_argument_type(self):
        with self.assertRaises(SwarnaSemanticError):
            _check('contains(1, "a")')


class TestSplit(unittest.TestCase):
    def _assert_both(self, source: str, expected: list[str]) -> None:
        self.assertEqual(_interpreter_output(source), expected)
        self.assertEqual(_vm_output(source), expected)

    def test_checker_returns_list_of_string(self):
        checker = _check('let parts = split("a,b", ",")')
        self.assertEqual(checker.env["parts"].type.label, "List[String]")

    def test_basic_split(self):
        self._assert_both('print(split("a,b,c", ","))', ['["a", "b", "c"]'])

    def test_multi_character_separator(self):
        self._assert_both('print(split("a::b::c", "::"))', ['["a", "b", "c"]'])

    def test_missing_separator_returns_whole_string(self):
        self._assert_both('print(split("abc", ","))', ['["abc"]'])

    def test_empty_separator_is_rejected(self):
        with self.assertRaises(SwarnaSemanticError):
            _check('split("abc", "")')

    def test_wrong_argument_count(self):
        with self.assertRaises(SwarnaSemanticError):
            _check('split("a,b")')

    def test_wrong_argument_type(self):
        with self.assertRaises(SwarnaSemanticError):
            _check('split(1, ",")')


if __name__ == "__main__":
    unittest.main()
