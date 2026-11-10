import unittest

from compiler.diagnostics import SourceSpan, SwarnaNameError, SwarnaRuntimeError, SwarnaTypeError, SwarnaZeroDivisionError
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from runtime.interpreter import Interpreter


def run(source: str) -> dict[str, int | float | bool | str]:
    program = Parser(Lexer(source)).parse_program()
    return Interpreter().eval(program)


class TestInterpreter(unittest.TestCase):
    def test_let_expression(self):
        env = run("let x = 1 + 2 * 3")
        self.assertEqual(env["x"], 7)

    def test_multiple_lets_and_identifier(self):
        env = run("let x = 1 let y = x + 2")
        self.assertEqual(env, {"x": 1, "y": 3})

    def test_unary_minus(self):
        env = run("let x = -1 + 2")
        self.assertEqual(env["x"], 1)

    def test_division(self):
        env = run("let x = 7 / 2")
        self.assertEqual(env["x"], 3.5)

    def test_float_literals_and_division(self):
        env = run("let x = 3.5 let y = x / 2 let z = 7 / 2")
        self.assertEqual(env["x"], 3.5)
        self.assertEqual(env["y"], 1.75)
        self.assertEqual(env["z"], 3.5)

    def test_integer_division(self):
        env = run("let a = 7 // 2 let b = -7 // 2")
        self.assertEqual(env["a"], 3)
        self.assertEqual(env["b"], -4)

    def test_integer_division_requires_ints(self):
        with self.assertRaises(TypeError):
            run("let x = 7.0 // 2")

    def test_integer_division_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            run("let x = 1 // 0")

    def test_string_literals_and_concatenation(self):
        program = Parser(Lexer('let s = "hello" let t = s + " world" print(t)')).parse_program()
        interpreter = Interpreter()
        env = interpreter.eval(program)
        self.assertEqual(env["s"], "hello")
        self.assertEqual(env["t"], "hello world")
        self.assertEqual(interpreter.output, ["hello world"])

    def test_undefined_name(self):
        with self.assertRaises(NameError):
            run("let y = x + 1")

    def test_division_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            run("let x = 1 / 0")

    def test_bool_literals(self):
        env = run("let a = true let b = false")
        self.assertIs(env["a"], True)
        self.assertIs(env["b"], False)

    def test_comparisons(self):
        env = run("let a = 1 == 1 let b = 1 != 2 let c = 1 < 2 let d = 3 >= 4 let e = 1 + 2 <= 3")
        self.assertEqual(env, {"a": True, "b": True, "c": True, "d": False, "e": True})

    def test_logical_ops(self):
        env = run("let a = !false let b = true && false let c = true || false let d = true || false && false")
        self.assertEqual(env, {"a": True, "b": False, "c": True, "d": True})

    def test_word_operators(self):
        env = run("let a = true and false let b = false or true let c = not false")
        self.assertEqual(env, {"a": False, "b": True, "c": True})

    def test_if_else(self):
        env = run("let x = 0 if true { let x = 1 } else { let x = 2 }")
        self.assertEqual(env["x"], 1)
        env = run("let x = 0 if false { let x = 1 } else { let x = 2 }")
        self.assertEqual(env["x"], 2)

    def test_if_condition_expression(self):
        env = run("let a = 5 let r = 0 if a > 3 { let r = 10 }")
        self.assertEqual(env["r"], 10)

    def test_if_expression(self):
        env = run("let a = if true { 1 } else { 2 } let b = if false { 1 } else { 2 }")
        self.assertEqual(env["a"], 1)
        self.assertEqual(env["b"], 2)

    def test_if_expression_with_condition(self):
        env = run('let score = 42 let label = if score >= 50 { "pass" } else { "fail" }')
        self.assertEqual(env["label"], "fail")

    def test_nested_if_expression(self):
        env = run("let x = if true { if false { 1 } else { 2 } } else { 3 }")
        self.assertEqual(env["x"], 2)

    def test_if_expression_with_block_branches(self):
        env = run("let x = if true { let y = 1 y + 2 } else { let y = 3 y + 4 }")
        self.assertEqual(env["x"], 3)
        env = run("let x = if false { let y = 1 y + 2 } else { let y = 3 y + 4 }")
        self.assertEqual(env["x"], 7)

    def test_if_expression_block_assignment(self):
        env = run("let y = 0 let x = if true { y = 5 y } else { y = 9 y }")
        self.assertEqual(env["x"], 5)
        self.assertEqual(env["y"], 5)

    def test_if_expression_block_print(self):
        program = Parser(Lexer("let x = if true { print(1) 2 } else { print(3) 4 } print(x)")).parse_program()
        interpreter = Interpreter()
        env = interpreter.eval(program)
        self.assertEqual(env["x"], 2)
        self.assertEqual(interpreter.output, [1, 2])

    def test_if_expression_block_while(self):
        env = run("let i = 0 let x = if true { while i < 3 { i = i + 1 } i } else { 0 }")
        self.assertEqual(env["x"], 3)
        self.assertEqual(env["i"], 3)

    def test_if_expression_block_scope_leaks(self):
        env = run("let x = if true { let y = 1 y } else { 0 }")
        self.assertEqual(env["y"], 1)

    def test_if_expression_block_nested_if_value(self):
        env = run("let x = if true { let y = 1 if y > 0 { 10 } else { 20 } } else { 30 }")
        self.assertEqual(env["x"], 10)

    def test_if_expression_block_undefined_name_span(self):
        with self.assertRaises(SwarnaNameError) as raised:
            run("let x = if true { let y = 1 missing } else { 0 }")
        self.assertEqual(raised.exception.span, SourceSpan(1, 29, 7))

    def test_let_assignment(self):
        env = run("let x = 0 x = x + 1 x = x + 1")
        self.assertEqual(env["x"], 2)

    def test_const_binding(self):
        env = run("const x = 42")
        self.assertEqual(env["x"], 42)

    def test_assign_to_const_fails(self):
        with self.assertRaises(RuntimeError):
            run("const x = 0 x = 1")

    def test_assign_to_undefined_fails(self):
        with self.assertRaises(NameError):
            run("x = 1")

    def test_while_loop(self):
        env = run("let i = 0 while i < 3 { i = i + 1 }")
        self.assertEqual(env["i"], 3)

    def test_undefined_name_diagnostic_has_span(self):
        with self.assertRaises(SwarnaNameError) as raised:
            run("let y = x + 1")
        error = raised.exception
        self.assertEqual(error.span, SourceSpan(1, 9, 1))
        self.assertIsNotNone(error.hint)

    def test_undefined_assignment_diagnostic_has_span(self):
        with self.assertRaises(SwarnaNameError) as raised:
            run("x = 1")
        self.assertEqual(raised.exception.span, SourceSpan(1, 1, 1))

    def test_const_assignment_diagnostic_has_span(self):
        with self.assertRaises(SwarnaRuntimeError) as raised:
            run("const x = 0 x = 1")
        error = raised.exception
        self.assertEqual(error.span, SourceSpan(1, 13, 1))
        self.assertIsNotNone(error.hint)

    def test_division_by_zero_diagnostic_has_span(self):
        with self.assertRaises(SwarnaZeroDivisionError) as raised:
            run("let x = 1 / 0")
        self.assertEqual(raised.exception.span, SourceSpan(1, 11, 1))

    def test_integer_division_type_diagnostic_has_span(self):
        with self.assertRaises(SwarnaTypeError) as raised:
            run("let x = 7.0 // 2")
        self.assertEqual(raised.exception.span, SourceSpan(1, 13, 2))

    def test_type_mismatch_diagnostic_has_span(self):
        with self.assertRaises(SwarnaTypeError) as raised:
            run('let x = 1 + "a"')
        self.assertEqual(raised.exception.span, SourceSpan(1, 11, 1))


if __name__ == "__main__":
    unittest.main()
