import contextlib
import io
import unittest
from unittest.mock import patch

from compiler.diagnostics import SwarnaSemanticError
from runtime.interpreter import Interpreter
from swarna.__main__ import emit_bytecode_source, lex_source, main, parse_source, run_source


class FakeStdin:
    def isatty(self) -> bool:
        return True

    def read(self) -> str:
        return ""


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

    def test_emit_bytecode_includes_function_table(self):
        out = emit_bytecode_source("fn add(a: Int, b: Int) -> Int { a + b } print(add(2, 3))")
        self.assertIn("FUNCTION add/2", out)
        self.assertIn("CALL ('add', 2)", out)
        self.assertIn("LOAD_NAME 'a'", out)
        self.assertIn("RETURN", out)

    def test_emit_bytecode_includes_list_ops(self):
        out = emit_bytecode_source("let xs = [1, 2] print(xs[0] + len(xs))")
        self.assertIn("BUILD_LIST 2", out)
        self.assertIn("INDEX", out)
        self.assertIn("LEN", out)

    def test_emit_bytecode_includes_for_ops(self):
        out = emit_bytecode_source("for x in [1, 2] { print(x) }")
        self.assertIn("ITER_START 'x'", out)
        self.assertIn("ITER_NEXT", out)
        self.assertIn("JUMP", out)

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

    def test_run_source_prints_value(self):
        self.assertEqual(run_source("print(1 + 2)"), "3")

    def test_run_source_formats_booleans(self):
        self.assertEqual(run_source("print(true) print(false)"), "true\nfalse")

    def test_run_source_formats_strings_without_quotes(self):
        self.assertEqual(run_source('print("hi")'), "hi")

    def test_run_source_without_output_is_empty(self):
        self.assertEqual(run_source("let x = 1"), "")

    def test_run_source_executes_if_expression(self):
        self.assertEqual(
            run_source('let score = 42 print(if score >= 50 { "pass" } else { "fail" })'),
            "fail",
        )

    def test_run_source_executes_while_loop(self):
        self.assertEqual(
            run_source("let i = 0 while i < 3 { print(i) i = i + 1 }"),
            "0\n1\n2",
        )

    def test_run_source_executes_for_loop(self):
        self.assertEqual(
            run_source("let total = 0 for x in [1, 2, 3] { total = total + x } print(total)"),
            "6",
        )

    def test_run_source_for_loop_variable_does_not_leak(self):
        with self.assertRaises(SwarnaSemanticError):
            run_source("for x in [1] { } print(x)")

    def test_run_source_for_loop_requires_list(self):
        with self.assertRaises(SwarnaSemanticError):
            run_source("for x in 1 { print(x) }")

    def test_run_source_executes_function(self):
        self.assertEqual(
            run_source("fn add(a: Int, b: Int) -> Int { a + b } print(add(2, 3))"),
            "5",
        )

    def test_run_source_executes_recursive_function(self):
        self.assertEqual(
            run_source(
                "fn factorial(n: Int) -> Int { if n <= 1 { 1 } else { n * factorial(n - 1) } } "
                "print(factorial(5))"
            ),
            "120",
        )

    def test_run_source_executes_list_index_and_len(self):
        self.assertEqual(
            run_source("let xs = [1, 2, 3] print(xs[0] + len(xs))"),
            "4",
        )

    def test_run_source_formats_lists(self):
        self.assertEqual(
            run_source('print([1, 2, 3]) print(["Ada", "Grace"]) print([true, false])'),
            '[1, 2, 3]\n["Ada", "Grace"]\n[true, false]',
        )

    def test_run_source_reports_list_index_type_error(self):
        with self.assertRaises(SwarnaSemanticError):
            run_source('let xs = [1, 2] print(xs["a"])')

    def test_run_source_reports_mixed_list_error(self):
        with self.assertRaises(SwarnaSemanticError):
            run_source('let xs = [1, "a"]')

    def test_run_source_reports_undefined_name(self):
        with self.assertRaises(SwarnaSemanticError):
            run_source("x = 1")

    def test_run_source_accepts_existing_interpreter(self):
        interpreter = Interpreter()
        self.assertEqual(run_source("let x = 1", interpreter), "")
        self.assertEqual(run_source("print(x + 1)", interpreter), "2")

    def test_run_source_returns_only_new_output(self):
        interpreter = Interpreter()
        self.assertEqual(run_source("print(1)", interpreter), "1")
        self.assertEqual(run_source("print(2)", interpreter), "2")

    def test_run_source_does_not_share_state_by_default(self):
        self.assertEqual(run_source("let x = 1"), "")
        with self.assertRaises(SwarnaSemanticError):
            run_source("print(x)")

    def test_run_cli_prints_output(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["--run", "print(1 + 2)"])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), "3\n")

    def test_run_cli_accepts_multiline_source(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["--run", "let x = 1\nprint(x + 1)"])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), "2\n")

    def test_run_cli_executes_for_loop(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["--run", "for x in [1, 2] { print(x) }"])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), "1\n2\n")

    def test_run_cli_renders_syntax_error(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--run", "let x 42"])
        self.assertEqual(code, 1)
        output = stderr.getvalue()
        self.assertIn("error: Expected '='", output)
        self.assertIn("hint:", output)

    def test_run_cli_reports_undefined_name(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--run", "x = 1"])
        self.assertEqual(code, 1)
        self.assertIn("Undefined name 'x'", stderr.getvalue())

    def test_run_cli_reports_const_assignment_error(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--run", "const x = 1 x = 2"])
        self.assertEqual(code, 1)
        self.assertIn("Cannot assign to const binding 'x'", stderr.getvalue())

    def test_run_cli_reports_division_by_zero(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--run", "print(1 / 0)"])
        self.assertEqual(code, 1)
        self.assertIn("division by zero", stderr.getvalue())

    def test_run_cli_reports_type_error(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--run", 'print(1 + "a")'])
        self.assertEqual(code, 1)
        output = stderr.getvalue()
        self.assertIn("`+` cannot combine Int and String", output)
        self.assertIn("--> 1:9", output)

    def test_run_cli_rejects_non_bool_condition(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--run", "if 1 { print(1) }"])
        self.assertEqual(code, 1)
        self.assertIn("`if` condition must be Bool, got Int", stderr.getvalue())

    def test_run_cli_rejects_mismatched_if_branches(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--run", 'let x = if true { 1 } else { "a" }'])
        self.assertEqual(code, 1)
        self.assertIn("`if` branches have incompatible types: Int and String", stderr.getvalue())

    def test_run_cli_executes_block_if_expression(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["--run", "let x = if true { let y = 1 y + 2 } else { 0 } print(x)"])
        self.assertEqual(code, 0)
        self.assertIn("3", stdout.getvalue())

    def test_run_cli_reports_error_inside_block_if_expression(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--run", 'let x = if true { let y = 1 y + "a" } else { 0 }'])
        self.assertEqual(code, 1)
        self.assertIn("`+` cannot combine Int and String", stderr.getvalue())

    def test_run_cli_reports_missing_block_value(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--run", "let x = if true { let y = 1 } else { 0 }"])
        self.assertEqual(code, 1)
        self.assertIn("Block value needs a final expression", stderr.getvalue())

    def test_emit_bytecode_rejects_type_error(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--emit-bytecode", 'let x = 1 + "a"'])
        self.assertEqual(code, 1)
        self.assertIn("`+` cannot combine Int and String", stderr.getvalue())

    def test_parse_does_not_type_check(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["--parse", 'let x = 1 + "a"'])
        self.assertEqual(code, 0)
        self.assertIn("BinaryExpression", stdout.getvalue())

    def test_run_cli_renders_undefined_name_with_caret(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--run", "let y = x + 1"])
        self.assertEqual(code, 1)
        output = stderr.getvalue()
        self.assertIn("error: Undefined name 'x'", output)
        self.assertIn("--> 1:9", output)
        self.assertIn("^", output)
        self.assertIn("hint: Declare it first", output)

    def test_run_cli_explain_shows_why(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--run", "--explain", "let y = x + 1"])
        self.assertEqual(code, 1)
        output = stderr.getvalue()
        self.assertIn("Undefined name 'x'", output)
        self.assertIn("= why:", output)
        self.assertIn("let name = value", output)

    def test_run_cli_explain_shows_why_for_type_mismatch(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--run", "--explain", 'print(1 + "a")'])
        self.assertEqual(code, 1)
        output = stderr.getvalue()
        self.assertIn("cannot combine Int and String", output)
        self.assertIn("= why:", output)

    def test_run_cli_explain_covers_type_mismatch_kinds(self):
        cases = {
            "assignment": 'let x = 1 x = "a"',
            "argument": 'fn f(x: Int) -> Int { x } let y = f("a")',
            "return": 'fn f() -> Int { "a" }',
            "if branches": 'let x = if true { 1 } else { "a" }',
        }
        for label, source in cases.items():
            with self.subTest(label=label):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    code = main(["--run", "--explain", source])
                self.assertEqual(code, 1)
                self.assertIn("= why:", stderr.getvalue())

    def test_run_cli_without_explain_hides_why(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--run", "let y = x + 1"])
        self.assertEqual(code, 1)
        self.assertNotIn("= why:", stderr.getvalue())

    def test_run_cli_renders_const_assignment_with_caret(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--run", "const x = 0 x = 1"])
        self.assertEqual(code, 1)
        output = stderr.getvalue()
        self.assertIn("--> 1:13", output)
        self.assertIn("^", output)

    def test_run_cli_renders_division_by_zero_with_caret(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--run", "print(1 / 0)"])
        self.assertEqual(code, 1)
        output = stderr.getvalue()
        self.assertIn("--> 1:9", output)
        self.assertIn("hint: The divisor must be non-zero.", output)

    def test_run_cli_renders_undefined_name_on_later_line(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["--run", "let x = 1\nprint(x + missing)"])
        self.assertEqual(code, 1)
        output = stderr.getvalue()
        self.assertIn("--> 2:11", output)
        self.assertIn("missing", output)

    def test_repl_runs_by_default_with_run_flag(self):
        stdout = io.StringIO()
        inputs = iter(["print(1 + 2)", ":q"])
        with (
            patch("sys.stdin", FakeStdin()),
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            contextlib.redirect_stdout(stdout),
        ):
            code = main(["--run"])
        self.assertEqual(code, 0)
        self.assertIn("3", stdout.getvalue())

    def test_repl_run_prefix(self):
        stdout = io.StringIO()
        inputs = iter([":run print(4 + 5)", ":q"])
        with (
            patch("sys.stdin", FakeStdin()),
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            contextlib.redirect_stdout(stdout),
        ):
            code = main([])
        self.assertEqual(code, 0)
        self.assertIn("9", stdout.getvalue())

    def test_repl_reports_undefined_name(self):
        stderr = io.StringIO()
        inputs = iter(["x = 1", ":q"])
        with (
            patch("sys.stdin", FakeStdin()),
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(stderr),
        ):
            code = main(["--run"])
        self.assertEqual(code, 0)
        self.assertIn("Undefined name 'x'", stderr.getvalue())

    def test_repl_preserves_state_between_lines(self):
        stdout = io.StringIO()
        inputs = iter(["let x = 1", "print(x + 1)", ":q"])
        with (
            patch("sys.stdin", FakeStdin()),
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            contextlib.redirect_stdout(stdout),
        ):
            code = main(["--run"])
        self.assertEqual(code, 0)
        self.assertIn("2", stdout.getvalue())

    def test_repl_executes_for_loop(self):
        stdout = io.StringIO()
        inputs = iter(["for x in [1, 2, 3] { print(x) }", ":q"])
        with (
            patch("sys.stdin", FakeStdin()),
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            contextlib.redirect_stdout(stdout),
        ):
            code = main(["--run"])
        self.assertEqual(code, 0)
        output = stdout.getvalue()
        self.assertIn("1", output)
        self.assertIn("2", output)
        self.assertIn("3", output)

    def test_repl_preserves_function_between_lines(self):
        stdout = io.StringIO()
        inputs = iter([
            "fn add(a: Int, b: Int) -> Int { a + b }",
            "print(add(2, 3))",
            ":q",
        ])
        with (
            patch("sys.stdin", FakeStdin()),
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            contextlib.redirect_stdout(stdout),
        ):
            code = main(["--run"])
        self.assertEqual(code, 0)
        self.assertIn("5", stdout.getvalue())

    def test_repl_uses_inferred_function_return_type(self):
        stderr = io.StringIO()
        inputs = iter([
            "fn f() { 1 }",
            "if f() { print(1) }",
            ":q",
        ])
        with (
            patch("sys.stdin", FakeStdin()),
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(stderr),
        ):
            code = main(["--run"])
        self.assertEqual(code, 0)
        self.assertIn("`if` condition must be Bool, got Int", stderr.getvalue())

    def test_repl_preserves_collection_annotations(self):
        stderr = io.StringIO()
        inputs = iter([
            "fn first(xs: List[Int]) -> Int { xs[0] }",
            'let x = first(["a"])',
            ":q",
        ])
        with (
            patch("sys.stdin", FakeStdin()),
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(stderr),
        ):
            code = main(["--run"])
        self.assertEqual(code, 0)
        self.assertIn(
            "Argument 1 of 'first' must be List[Int], got List[String]",
            stderr.getvalue(),
        )

    def test_repl_preserves_function_after_runtime_error(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        inputs = iter([
            "fn f() -> Int { 1 } print(1 / 0)",
            "print(f())",
            ":q",
        ])
        with (
            patch("sys.stdin", FakeStdin()),
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            code = main(["--run"])
        self.assertEqual(code, 0)
        self.assertIn("division by zero", stderr.getvalue())
        self.assertIn("1", stdout.getvalue())

    def test_repl_redefines_function(self):
        stdout = io.StringIO()
        inputs = iter([
            "fn f() -> Int { 1 }",
            "fn f() -> Int { 2 }",
            "print(f())",
            ":q",
        ])
        with (
            patch("sys.stdin", FakeStdin()),
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            contextlib.redirect_stdout(stdout),
        ):
            code = main(["--run"])
        self.assertEqual(code, 0)
        self.assertIn("2", stdout.getvalue())

    def test_repl_preserves_list_type_between_lines(self):
        stdout = io.StringIO()
        inputs = iter([
            "let xs = [1, 2, 3]",
            "print(xs[0] + len(xs))",
            ":q",
        ])
        with (
            patch("sys.stdin", FakeStdin()),
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            contextlib.redirect_stdout(stdout),
        ):
            code = main(["--run"])
        self.assertEqual(code, 0)
        self.assertIn("4", stdout.getvalue())

    def test_repl_rejects_list_type_change(self):
        stderr = io.StringIO()
        inputs = iter([
            "let xs = [1, 2]",
            "xs = [1.0]",
            ":q",
        ])
        with (
            patch("sys.stdin", FakeStdin()),
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(stderr),
        ):
            code = main(["--run"])
        self.assertEqual(code, 0)
        self.assertIn("Cannot assign List[Float] to List[Int]", stderr.getvalue())

    def test_repl_preserves_const_binding(self):
        stderr = io.StringIO()
        inputs = iter(["const x = 1", "x = 2", ":q"])
        with (
            patch("sys.stdin", FakeStdin()),
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(stderr),
        ):
            code = main(["--run"])
        self.assertEqual(code, 0)
        self.assertIn("Cannot assign to const binding 'x'", stderr.getvalue())

    def test_repl_run_prefix_shares_state(self):
        stdout = io.StringIO()
        inputs = iter(["let x = 4", ":run print(x + 1)", ":q"])
        with (
            patch("sys.stdin", FakeStdin()),
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            contextlib.redirect_stdout(stdout),
        ):
            code = main(["--run"])
        self.assertEqual(code, 0)
        self.assertIn("5", stdout.getvalue())

    def test_repl_explain_toggle(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        inputs = iter([":explain", "print(missing)", ":explain", "print(missing)", ":q"])
        with (
            patch("sys.stdin", FakeStdin()),
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            code = main(["--run"])
        self.assertEqual(code, 0)
        self.assertIn("explanations on", stdout.getvalue())
        self.assertIn("explanations off", stdout.getvalue())
        self.assertEqual(stderr.getvalue().count("= why:"), 1)

    def test_repl_explain_flag_starts_enabled(self):
        stderr = io.StringIO()
        inputs = iter(["print(missing)", ":q"])
        with (
            patch("sys.stdin", FakeStdin()),
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(stderr),
        ):
            code = main(["--run", "--explain"])
        self.assertEqual(code, 0)
        self.assertIn("= why:", stderr.getvalue())

    def test_repl_continues_after_error(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        inputs = iter(["print(missing)", "print(1 + 1)", ":q"])
        with (
            patch("sys.stdin", FakeStdin()),
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            code = main(["--run"])
        self.assertEqual(code, 0)
        self.assertIn("Undefined name 'missing'", stderr.getvalue())
        self.assertIn("2", stdout.getvalue())

    def test_repl_continues_after_type_error(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        inputs = iter(['print(1 + "a")', "print(1 + 1)", ":q"])
        with (
            patch("sys.stdin", FakeStdin()),
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            code = main(["--run"])
        self.assertEqual(code, 0)
        self.assertIn("`+` cannot combine Int and String", stderr.getvalue())
        self.assertIn("2", stdout.getvalue())

    def test_repl_rejects_assignment_type_change(self):
        stderr = io.StringIO()
        inputs = iter(["let x = 1", 'x = "a"', ":q"])
        with (
            patch("sys.stdin", FakeStdin()),
            patch("builtins.input", side_effect=lambda _: next(inputs)),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(stderr),
        ):
            code = main(["--run"])
        self.assertEqual(code, 0)
        self.assertIn("Cannot assign String to Int binding 'x'", stderr.getvalue())

    def test_run_cli_executes_source_file(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "program.sw"
            path.write_text("let x = 2\nprint(x + 3)\n", encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["--run", str(path)])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), "5\n")

    def test_run_cli_reports_error_with_source_file_name(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.sw"
            path.write_text("print(missing)\n", encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = main(["--run", str(path)])
        self.assertEqual(code, 1)
        output = stderr.getvalue()
        self.assertIn("Undefined name 'missing'", output)
        self.assertIn(str(path), output)


if __name__ == "__main__":
    unittest.main()
