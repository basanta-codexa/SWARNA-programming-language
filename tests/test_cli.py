import contextlib
import io
import unittest

from swarna.__main__ import emit_bytecode_source, lex_source, main, parse_source


class TestCLIHelpers(unittest.TestCase):
    def test_lex_source(self):
        out = lex_source("let x = 42")
        self.assertIn("KEYWORD_LET 'let'", out)
        self.assertIn("INTEGER '42'", out)
        self.assertIn("EOF ''", out)

    def test_parse_source(self):
        out = parse_source("let x = 42")
        self.assertIn("LetStatement", out)
        self.assertIn("IntegerLiteral", out)
        self.assertIn("value=42", out)

    def test_emit_bytecode_source(self):
        out = emit_bytecode_source("let x = 1 + 2")
        self.assertIn("CONST 1", out)
        self.assertIn("CONST 2", out)
        self.assertIn("ADD", out)
        self.assertIn("DECLARE_NAME 'x'", out)
        self.assertIn("HALT", out)

    def test_emit_bytecode_const(self):
        out = emit_bytecode_source("const x = 1")
        self.assertIn("STORE_CONST 'x'", out)

    def test_parse_error_renders_span_and_hint(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--parse", "let x 42"])
        self.assertEqual(code, 1)
        output = stderr.getvalue()
        self.assertIn("error: Expected '='", output)
        self.assertIn("let x 42", output)
        self.assertIn("^^", output)
        self.assertIn("hint:", output)

    def test_lex_error_renders_span_and_hint(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--lex", "let x @ 1"])
        self.assertEqual(code, 1)
        output = stderr.getvalue()
        self.assertIn("Unexpected character", output)
        self.assertIn("hint:", output)


if __name__ == "__main__":
    unittest.main()
