import unittest

from compiler.diagnostics import (
    DiagnosticError,
    SourceSpan,
    SwarnaNameError,
    SwarnaRuntimeError,
    SwarnaSyntaxError,
    SwarnaTypeError,
    SwarnaZeroDivisionError,
    render_diagnostic,
)
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser


class TestSourceSpan(unittest.TestCase):
    def test_default_length(self):
        span = SourceSpan(2, 5)
        self.assertEqual((span.line, span.column, span.length), (2, 5, 1))


class TestDiagnosticError(unittest.TestCase):
    def test_message_without_span(self):
        error = DiagnosticError("something went wrong")
        self.assertEqual(str(error), "something went wrong")
        self.assertIsNone(error.span)
        self.assertIsNone(error.hint)

    def test_message_with_span(self):
        error = DiagnosticError("something went wrong", SourceSpan(3, 7), "try this")
        self.assertEqual(str(error), "something went wrong at line 3, column 7")
        self.assertEqual(error.hint, "try this")

    def test_syntax_error_remains_catchable_as_syntax_error(self):
        error = SwarnaSyntaxError("bad syntax", SourceSpan(1, 2))
        self.assertIsInstance(error, SyntaxError)
        self.assertIsInstance(error, DiagnosticError)


class TestRuntimeDiagnosticTypes(unittest.TestCase):
    def test_runtime_error_remains_catchable_as_runtime_error(self):
        error = SwarnaRuntimeError("boom", SourceSpan(1, 2), "fix it")
        self.assertIsInstance(error, RuntimeError)
        self.assertIsInstance(error, DiagnosticError)

    def test_name_error_remains_catchable_as_name_error(self):
        self.assertIsInstance(SwarnaNameError("missing"), NameError)

    def test_type_error_remains_catchable_as_type_error(self):
        self.assertIsInstance(SwarnaTypeError("bad type"), TypeError)

    def test_zero_division_error_remains_catchable_as_zero_division_error(self):
        self.assertIsInstance(SwarnaZeroDivisionError("zero"), ZeroDivisionError)

    def test_renders_runtime_diagnostic(self):
        error = SwarnaNameError(
            "Undefined name 'x'",
            SourceSpan(1, 9),
            "Declare it first.",
        )
        rendered = render_diagnostic("let y = x + 1", error)
        self.assertIn("error: Undefined name 'x'", rendered)
        self.assertIn("--> 1:9", rendered)
        self.assertIn("^", rendered)
        self.assertIn("hint: Declare it first.", rendered)


class TestLexerDiagnostics(unittest.TestCase):
    def test_string_token_span_includes_quotes(self):
        tokens = Lexer('let s = "hi"').tokenize()
        self.assertEqual(tokens[3].span, SourceSpan(1, 9, 4))

    def test_string_token_span_counts_escape_source(self):
        tokens = Lexer('let s = "a\\nb"').tokenize()
        self.assertEqual(tokens[3].span, SourceSpan(1, 9, 6))

    def test_unexpected_character_has_span_and_hint(self):
        with self.assertRaises(SwarnaSyntaxError) as raised:
            Lexer("let x @ 1").tokenize()
        error = raised.exception
        self.assertEqual(error.span, SourceSpan(1, 7))
        self.assertIn("Unexpected character", error.message)
        self.assertIsNotNone(error.hint)

    def test_unterminated_string_has_span_and_hint(self):
        with self.assertRaises(SwarnaSyntaxError) as raised:
            Lexer('let s = "hello').tokenize()
        error = raised.exception
        self.assertEqual(error.span, SourceSpan(1, 9))
        self.assertIn("Unterminated", error.message)
        self.assertIsNotNone(error.hint)


class TestParserDiagnostics(unittest.TestCase):
    def test_expected_equals_has_span_and_hint(self):
        with self.assertRaises(SwarnaSyntaxError) as raised:
            Parser(Lexer("let x 42")).parse_program()
        error = raised.exception
        self.assertEqual(error.span, SourceSpan(1, 7, 2))
        self.assertEqual(error.message, "Expected '='")
        self.assertIsNotNone(error.hint)

    def test_let_mut_has_span_and_hint(self):
        with self.assertRaises(SwarnaSyntaxError) as raised:
            Parser(Lexer("let mut x = 1")).parse_program()
        error = raised.exception
        self.assertEqual(error.span, SourceSpan(1, 5, 3))
        self.assertEqual(error.message, "`let mut` was removed")
        self.assertIsNotNone(error.hint)

    def test_missing_else_has_span_and_hint(self):
        with self.assertRaises(SwarnaSyntaxError) as raised:
            Parser(Lexer("let x = if true { 1 }")).parse_program()
        error = raised.exception
        self.assertIn("requires an else branch", error.message)
        self.assertEqual(error.span.line, 1)
        self.assertIsNotNone(error.hint)


class TestRenderDiagnostic(unittest.TestCase):
    def test_renders_source_caret_and_hint(self):
        source = "let x 42"
        error = DiagnosticError(
            "Expected '='",
            SourceSpan(1, 7, 2),
            "Bindings use `let name = value` or `const name = value`.",
        )
        rendered = render_diagnostic(source, error)
        self.assertIn("error: Expected '='", rendered)
        self.assertIn("let x 42", rendered)
        self.assertIn("^^", rendered)
        self.assertIn("hint: Bindings use", rendered)

    def test_renders_last_line_for_eof(self):
        source = "let x = if true { 1 }"
        error = DiagnosticError("missing else", SourceSpan(2, 1), "Add `else`.")
        rendered = render_diagnostic(source, error)
        self.assertIn("let x = if true { 1 }", rendered)
        self.assertIn("^", rendered)
        self.assertIn("hint: Add `else`.", rendered)

    def test_renders_hint_without_span(self):
        error = DiagnosticError("boom", hint="fix it")
        self.assertEqual(render_diagnostic("", error), "error: boom\n  hint: fix it")


if __name__ == "__main__":
    unittest.main()
