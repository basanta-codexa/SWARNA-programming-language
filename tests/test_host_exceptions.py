import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from compiler.diagnostics import SwarnaRuntimeError, SwarnaSyntaxError
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from runtime.values import format_value
from swarna.__main__ import main


class TestHostExceptionBoundary(unittest.TestCase):
    """Host Python errors must never reach users as tracebacks."""

    def test_huge_integer_literal_is_a_syntax_diagnostic(self):
        source = "let x = " + "9" * 5000
        with self.assertRaises(SwarnaSyntaxError) as raised:
            Parser(Lexer(source)).parse_program()
        self.assertIn("too large", raised.exception.message)
        self.assertIsNotNone(raised.exception.span)

    def test_huge_integer_value_is_a_runtime_diagnostic(self):
        with self.assertRaises(SwarnaRuntimeError) as raised:
            format_value(2 ** 15000)
        self.assertIn("too large", raised.exception.message)

    def test_cli_reports_huge_literal_without_traceback(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            status = main(["--run", "let x = " + "9" * 5000])
        self.assertEqual(status, 1)
        self.assertIn("too large", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_cli_handles_path_check_failure_for_inline_source(self):
        stdout = io.StringIO()
        with patch(
            "swarna.__main__.Path.is_file",
            side_effect=OSError(36, "File name too long"),
        ):
            with redirect_stdout(stdout):
                status = main(["--run", "print(1)"])
        self.assertEqual(status, 0)
        self.assertEqual(stdout.getvalue().strip(), "1")

    def test_cli_reports_huge_computed_integer_without_traceback(self):
        source = (
            "let x = 1 let i = 0 "
            "while i < 15000 { x = x * 2 i = i + 1 } "
            "print(x)"
        )
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            status = main(["--run", source])
        self.assertEqual(status, 1)
        self.assertIn("too large", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
