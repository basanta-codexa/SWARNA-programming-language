import unittest

from compiler.codegen.compiler import Compiler
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser


def compile_source(source: str):
    program = Parser(Lexer(source)).parse_program()
    return Compiler().compile(program)


class TestCodegen(unittest.TestCase):
    def test_compile_let_integer_expression(self):
        code = compile_source("let x = 1 + 2 * 3")
        self.assertEqual([repr(i) for i in code], [
            "CONST 1",
            "CONST 2",
            "CONST 3",
            "MUL",
            "ADD",
            "STORE_NAME 'x'",
            "HALT",
        ])

    def test_compile_identifier_and_unary(self):
        code = compile_source("let x = 1 let y = -x + 2")
        self.assertEqual([repr(i) for i in code], [
            "CONST 1",
            "STORE_NAME 'x'",
            "LOAD_NAME 'x'",
            "NEG",
            "CONST 2",
            "ADD",
            "STORE_NAME 'y'",
            "HALT",
        ])

    def test_compile_assignment(self):
        code = compile_source("let mut x = 1 x = x + 1")
        self.assertEqual([repr(i) for i in code], [
            "CONST 1",
            "STORE_NAME 'x'",
            "LOAD_NAME 'x'",
            "CONST 1",
            "ADD",
            "STORE_NAME 'x'",
            "HALT",
        ])

    def test_compile_comparisons_bools_and_print(self):
        code = compile_source("let a = 1 == 2 let b = !false print(b)")
        self.assertEqual([repr(i) for i in code], [
            "CONST 1",
            "CONST 2",
            "EQ",
            "STORE_NAME 'a'",
            "CONST False",
            "NOT",
            "STORE_NAME 'b'",
            "LOAD_NAME 'b'",
            "PRINT",
            "HALT",
        ])

    def test_compile_if_else(self):
        code = compile_source("if true { print(1) } else { print(2) }")
        self.assertEqual([repr(i) for i in code], [
            "CONST True",
            "JUMP_IF_FALSE 5",
            "CONST 1",
            "PRINT",
            "JUMP 7",
            "CONST 2",
            "PRINT",
            "HALT",
        ])

    def test_compile_if_without_else(self):
        code = compile_source("if false { print(1) }")
        self.assertEqual([repr(i) for i in code], [
            "CONST False",
            "JUMP_IF_FALSE 4",
            "CONST 1",
            "PRINT",
            "HALT",
        ])

    def test_compile_while(self):
        code = compile_source("while i < 3 { i = i + 1 }")
        self.assertEqual([repr(i) for i in code], [
            "LOAD_NAME 'i'",
            "CONST 3",
            "LT",
            "JUMP_IF_FALSE 9",
            "LOAD_NAME 'i'",
            "CONST 1",
            "ADD",
            "STORE_NAME 'i'",
            "JUMP 0",
            "HALT",
        ])

    def test_compile_float_division(self):
        code = compile_source("let x = 3.5 / 2")
        self.assertEqual([repr(i) for i in code], [
            "CONST 3.5",
            "CONST 2",
            "DIV",
            "STORE_NAME 'x'",
            "HALT",
        ])

    def test_compile_integer_division(self):
        code = compile_source("let x = 7 // 2")
        self.assertEqual([repr(i) for i in code], [
            "CONST 7",
            "CONST 2",
            "IDIV",
            "STORE_NAME 'x'",
            "HALT",
        ])

    def test_compile_string_literal(self):
        code = compile_source('let s = "hi"')
        self.assertEqual([repr(i) for i in code], [
            "CONST 'hi'",
            "STORE_NAME 's'",
            "HALT",
        ])

    def test_compile_short_circuit_and(self):
        code = compile_source("let x = true && false")
        self.assertEqual([repr(i) for i in code], [
            "CONST True",
            "DUP",
            "JUMP_IF_FALSE 7",
            "POP",
            "CONST False",
            "BOOL",
            "JUMP 9",
            "POP",
            "CONST False",
            "STORE_NAME 'x'",
            "HALT",
        ])

    def test_compile_short_circuit_or(self):
        code = compile_source("let x = false || true")
        self.assertEqual([repr(i) for i in code], [
            "CONST False",
            "DUP",
            "JUMP_IF_FALSE 6",
            "POP",
            "CONST True",
            "JUMP 9",
            "POP",
            "CONST True",
            "BOOL",
            "STORE_NAME 'x'",
            "HALT",
        ])


if __name__ == "__main__":
    unittest.main()
