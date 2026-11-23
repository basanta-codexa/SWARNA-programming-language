import unittest

from compiler.codegen.compiler import Compiler
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.checker import TypeChecker
from runtime.interpreter import Interpreter
from runtime.vm import VM
from runtime.values import format_value


def _parse(source: str):
    return Parser(Lexer(source)).parse_program()


def _checked(source: str):
    program = _parse(source)
    checker = TypeChecker()
    checker.check(program)
    return program, checker.expression_types


def _interpreter_output(source: str) -> list[str]:
    program, inferred_types = _checked(source)
    interpreter = Interpreter()
    interpreter.eval(program, inferred_types)
    return [format_value(value) for value in interpreter.output]


def _vm_output(source: str) -> list[str]:
    program, inferred_types = _checked(source)
    vm = VM()
    vm.run(Compiler(inferred_types).compile(program))
    return [format_value(value) for value in vm.output]


class TestFloatAnnotationCoercion(unittest.TestCase):
    def _assert_both(self, source: str, expected: list[str]) -> None:
        self.assertEqual(_interpreter_output(source), expected)
        self.assertEqual(_vm_output(source), expected)

    def test_annotated_let_declaration(self):
        self._assert_both("let x: Float = 1 print(str(x))", ["1.0"])

    def test_annotated_let_assignment(self):
        self._assert_both("let x: Float = 1.0 x = 2 print(str(x))", ["2.0"])

    def test_annotated_const(self):
        self._assert_both("const x: Float = 1 print(str(x))", ["1.0"])

    def test_annotated_list(self):
        self._assert_both("let xs: List[Float] = [1, 2] print(str(xs[0]))", ["1.0"])

    def test_annotated_map_index_assignment(self):
        self._assert_both(
            'let m: Map[String, Float] = {} m["a"] = 1 print(str(m["a"]))',
            ["1.0"],
        )

    def test_function_argument_and_return(self):
        self._assert_both("fn f(x: Float) -> Float { x } print(str(f(1)))", ["1.0"])

    def test_inferred_if_expression(self):
        self._assert_both("let x = if true { 1 } else { 2.0 } print(str(x))", ["1.0"])

    def test_inferred_list_literal(self):
        self._assert_both("let xs = [1, 2.5] print(str(xs[0]))", ["1.0"])

    def test_inferred_map_literal(self):
        self._assert_both('let m = { "a": 1.0, "b": 2 } print(str(m["b"]))', ["2.0"])

    def test_inferred_function_return(self):
        self._assert_both("fn f() { if true { 1 } else { 2.0 } } print(str(f()))", ["1.0"])


if __name__ == "__main__":
    unittest.main()
