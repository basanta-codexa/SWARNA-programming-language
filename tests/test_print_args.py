import io
import unittest
from contextlib import redirect_stdout

from compiler.ast.nodes import IntegerLiteral, PrintStatement, StringLiteral
from compiler.codegen.compiler import Compiler
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.checker import TypeChecker
from runtime.interpreter import Interpreter
from runtime.vm import VM
from runtime.values import format_value
from swarna.__main__ import main


def _parse(source: str):
    return Parser(Lexer(source)).parse_program()


class TestMultiplePrintArguments(unittest.TestCase):
    def test_parser_collects_all_arguments(self):
        program = _parse('print("Hello", 12)')
        statement = program.statements[0]
        self.assertIsInstance(statement, PrintStatement)
        self.assertEqual(statement.values, (StringLiteral("Hello"), IntegerLiteral(12)))

    def test_checker_accepts_multiple_arguments(self):
        TypeChecker().check(_parse('print("Hello", 12, true)'))

    def test_interpreter_joins_with_comma_and_space(self):
        interpreter = Interpreter()
        interpreter.eval(_parse('print("Hello", 12)'))
        self.assertEqual(interpreter.output, ["Hello, 12"])

    def test_vm_joins_with_comma_and_space(self):
        vm = VM()
        vm.run(Compiler().compile(_parse('print("Hello", 12)')))
        self.assertEqual(vm.output, ["Hello, 12"])

    def test_single_argument_still_yields_raw_value(self):
        interpreter = Interpreter()
        interpreter.eval(_parse("print(42)"))
        self.assertEqual(interpreter.output, [42])

    def test_cli_prints_multiple_arguments(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = main(["--run", 'print("Hello", 12)'])
        self.assertEqual(status, 0)
        self.assertEqual(stdout.getvalue().strip(), "Hello, 12")

    def test_engine_parity(self):
        source = 'print("Hello", 12, true, [1, 2])'
        interpreter = Interpreter()
        interpreter.eval(_parse(source))
        vm = VM()
        vm.run(Compiler().compile(_parse(source)))
        self.assertEqual(
            [format_value(value) for value in vm.output],
            [format_value(value) for value in interpreter.output],
        )


if __name__ == "__main__":
    unittest.main()
