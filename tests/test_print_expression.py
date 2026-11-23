import unittest

from compiler.codegen.compiler import Compiler
from compiler.diagnostics import SwarnaSemanticError
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.checker import Type, TypeChecker
from runtime.interpreter import Interpreter
from runtime.vm import VM
from runtime.values import UNIT, format_value


def _parse(source: str):
    return Parser(Lexer(source)).parse_program()


def _check(source: str):
    checker = TypeChecker()
    checker.check(_parse(source))
    return checker


def _interpreter_output(source: str) -> list[str]:
    checker = _check(source)
    interpreter = Interpreter()
    interpreter.eval(_parse(source), checker.expression_types)
    return [format_value(value) for value in interpreter.output]


def _vm_output(source: str) -> list[str]:
    checker = _check(source)
    vm = VM()
    vm.run(Compiler(checker.expression_types).compile(_parse(source)))
    return [format_value(value) for value in vm.output]


class TestPrintExpression(unittest.TestCase):
    def test_checker_infers_unit(self):
        checker = _check("let u = print(1)")
        self.assertIs(checker.env["u"].type, Type.UNIT)

    def test_print_returns_unit_in_interpreter(self):
        interpreter = Interpreter()
        interpreter.eval(_parse("let u = print(1)"))
        self.assertEqual(interpreter.output, [1])
        self.assertIs(interpreter.env["u"], UNIT)

    def test_engine_parity(self):
        source = "let u = print(1) print(u)"
        self.assertEqual(_interpreter_output(source), ["1", "()"])
        self.assertEqual(_vm_output(source), ["1", "()"])

    def test_multiple_arguments(self):
        source = 'let u = print("a", 2)'
        self.assertEqual(_interpreter_output(source), ["a, 2"])
        self.assertEqual(_vm_output(source), ["a, 2"])

    def test_nested_print(self):
        source = "print(print(1))"
        self.assertEqual(_interpreter_output(source), ["1", "()"])
        self.assertEqual(_vm_output(source), ["1", "()"])

    def test_statement_form_is_unchanged(self):
        interpreter = Interpreter()
        interpreter.eval(_parse("print(1)"))
        self.assertEqual(interpreter.output, [1])

    def test_zero_arguments_are_rejected(self):
        with self.assertRaises(SwarnaSemanticError):
            _check("let u = print()")


if __name__ == "__main__":
    unittest.main()
