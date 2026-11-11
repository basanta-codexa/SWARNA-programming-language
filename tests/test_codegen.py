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
            "DECLARE_NAME 'x'",
            "HALT",
        ])

    def test_compile_identifier_and_unary(self):
        code = compile_source("let x = 1 let y = -x + 2")
        self.assertEqual([repr(i) for i in code], [
            "CONST 1",
            "DECLARE_NAME 'x'",
            "LOAD_NAME 'x'",
            "NEG",
            "CONST 2",
            "ADD",
            "DECLARE_NAME 'y'",
            "HALT",
        ])

    def test_compile_assignment(self):
        code = compile_source("let x = 1 x = x + 1")
        self.assertEqual([repr(i) for i in code], [
            "CONST 1",
            "DECLARE_NAME 'x'",
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
            "DECLARE_NAME 'a'",
            "CONST False",
            "NOT",
            "DECLARE_NAME 'b'",
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

    def test_compile_if_expression(self):
        code = compile_source("let x = if true { 1 } else { 2 }")
        self.assertEqual([repr(i) for i in code], [
            "CONST True",
            "JUMP_IF_FALSE 4",
            "CONST 1",
            "JUMP 5",
            "CONST 2",
            "DECLARE_NAME 'x'",
            "HALT",
        ])

    def test_compile_if_expression_with_block_branch(self):
        code = compile_source("let x = if true { let y = 1 y + 2 } else { 3 }")
        self.assertEqual([repr(i) for i in code], [
            "CONST True",
            "JUMP_IF_FALSE 8",
            "CONST 1",
            "DECLARE_NAME 'y'",
            "LOAD_NAME 'y'",
            "CONST 2",
            "ADD",
            "JUMP 9",
            "CONST 3",
            "DECLARE_NAME 'x'",
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
            "DECLARE_NAME 'x'",
            "HALT",
        ])

    def test_compile_integer_division(self):
        code = compile_source("let x = 7 // 2")
        self.assertEqual([repr(i) for i in code], [
            "CONST 7",
            "CONST 2",
            "IDIV",
            "DECLARE_NAME 'x'",
            "HALT",
        ])

    def test_compile_string_literal(self):
        code = compile_source('let s = "hi"')
        self.assertEqual([repr(i) for i in code], [
            "CONST 'hi'",
            "DECLARE_NAME 's'",
            "HALT",
        ])

    def test_compile_const_binding(self):
        code = compile_source("const x = 1")
        self.assertEqual([repr(i) for i in code], [
            "CONST 1",
            "STORE_CONST 'x'",
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
            "DECLARE_NAME 'x'",
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
            "DECLARE_NAME 'x'",
            "HALT",
        ])

    def test_compile_word_operators_match_symbols(self):
        symbolic = compile_source("let x = true && false || !true")
        words = compile_source("let x = true and false or not true")
        self.assertEqual([repr(i) for i in words], [repr(i) for i in symbolic])

    def test_compile_function_declaration_and_call(self):
        compiled = compile_source("fn add(a: Int, b: Int) -> Int { a + b } let x = add(2, 3)")
        self.assertEqual([repr(i) for i in compiled.instructions], [
            "CONST 2",
            "CONST 3",
            "CALL ('add', 2)",
            "DECLARE_NAME 'x'",
            "HALT",
        ])
        function = compiled.functions["add"]
        self.assertEqual(function.name, "add")
        self.assertEqual(function.parameters, ("a", "b"))
        self.assertEqual([repr(i) for i in function.instructions], [
            "LOAD_NAME 'a'",
            "LOAD_NAME 'b'",
            "ADD",
            "RETURN",
        ])

    def test_compile_function_with_block_body(self):
        compiled = compile_source("fn total(a: Int) -> Int { let b = a + 1 b } let x = total(1)")
        self.assertEqual([repr(i) for i in compiled.instructions], [
            "CONST 1",
            "CALL ('total', 1)",
            "DECLARE_NAME 'x'",
            "HALT",
        ])
        self.assertEqual([repr(i) for i in compiled.functions["total"].instructions], [
            "LOAD_NAME 'a'",
            "CONST 1",
            "ADD",
            "DECLARE_NAME 'b'",
            "LOAD_NAME 'b'",
            "RETURN",
        ])

    def test_compile_function_call_arguments_in_order(self):
        compiled = compile_source(
            "fn one() -> Int { 1 } "
            "fn add(a: Int, b: Int) -> Int { a + b } "
            "let x = add(one(), 2)"
        )
        self.assertEqual([repr(i) for i in compiled.instructions], [
            "CALL ('one', 0)",
            "CONST 2",
            "CALL ('add', 2)",
            "DECLARE_NAME 'x'",
            "HALT",
        ])
        self.assertEqual([repr(i) for i in compiled.functions["one"].instructions], [
            "CONST 1",
            "RETURN",
        ])

    def test_compile_function_call_before_declaration(self):
        compiled = compile_source("let x = add(2, 3) fn add(a: Int, b: Int) -> Int { a + b }")
        self.assertEqual([repr(i) for i in compiled.instructions], [
            "CONST 2",
            "CONST 3",
            "CALL ('add', 2)",
            "DECLARE_NAME 'x'",
            "HALT",
        ])
        self.assertIn("add", compiled.functions)

    def test_compile_recursive_function_call(self):
        compiled = compile_source(
            "fn factorial(n: Int) -> Int { if n <= 1 { 1 } else { n * factorial(n - 1) } }"
        )
        instructions = [repr(i) for i in compiled.functions["factorial"].instructions]
        self.assertIn("CALL ('factorial', 1)", instructions)
        self.assertEqual(instructions[-1], "RETURN")

    def test_compiled_program_is_iterable_and_indexable(self):
        compiled = compile_source("let x = 1")
        self.assertEqual(len(compiled), 3)
        self.assertEqual(repr(compiled[0]), "CONST 1")
        self.assertEqual([repr(i) for i in compiled], ["CONST 1", "DECLARE_NAME 'x'", "HALT"])

    def test_compile_nested_function_declaration_is_rejected(self):
        with self.assertRaisesRegex(NotImplementedError, "only allowed at the top level"):
            compile_source("if true { fn f() -> Int { 1 } }")

    def test_compile_duplicate_function_declaration_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Duplicate function 'f'"):
            compile_source("fn f() -> Int { 1 } fn f() -> Int { 2 }")


if __name__ == "__main__":
    unittest.main()
