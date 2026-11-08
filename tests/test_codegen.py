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


if __name__ == "__main__":
    unittest.main()
