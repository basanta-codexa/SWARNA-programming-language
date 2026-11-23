import unittest

from compiler.codegen.compiler import Compiler
from compiler.diagnostics import SwarnaRuntimeError
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from runtime.interpreter import Interpreter
from runtime.vm import VM


SOURCE = 'let m = { "a": 1, "b": 2 } for k in m { m["c"] = 3 } print(m)'


class TestMapMutationDuringIteration(unittest.TestCase):
    def _assert_diagnostic(self, runner) -> None:
        with self.assertRaises(SwarnaRuntimeError) as raised:
            runner(SOURCE)
        error = raised.exception
        self.assertIn("Cannot change a map while iterating", error.message)
        self.assertIsNotNone(error.span)
        self.assertTrue(error.hint)

    def test_interpreter_reports_diagnostic(self):
        def run(source: str) -> None:
            Interpreter().eval(Parser(Lexer(source)).parse_program())

        self._assert_diagnostic(run)

    def test_vm_reports_diagnostic(self):
        def run(source: str) -> None:
            VM().run(Compiler().compile(Parser(Lexer(source)).parse_program()))

        self._assert_diagnostic(run)

    def test_error_can_be_caught_by_swarna_try(self):
        source = (
            "let m = { \"a\": 1 } "
            "try { for k in m { m[\"b\"] = 2 } } catch e { print(e) }"
        )
        interpreter = Interpreter()
        interpreter.eval(Parser(Lexer(source)).parse_program())
        self.assertEqual(len(interpreter.output), 1)
        self.assertIn("Cannot change a map", interpreter.output[0])


if __name__ == "__main__":
    unittest.main()
