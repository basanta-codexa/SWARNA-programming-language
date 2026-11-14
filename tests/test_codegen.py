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

    def test_compile_for(self):
        code = compile_source("for x in [1, 2] { print(x) }")
        self.assertEqual([repr(i) for i in code], [
            "CONST 1",
            "CONST 2",
            "BUILD_LIST 2",
            "ITER_START 'x'",
            "ITER_NEXT 9",
            "LOAD_NAME 'x'",
            "PRINT",
            "JUMP 4",
            "ITER_END",
            "HALT",
        ])

    def test_compile_for_with_empty_body(self):
        code = compile_source("for x in [] { }")
        self.assertEqual([repr(i) for i in code], [
            "BUILD_LIST 0",
            "ITER_START 'x'",
            "ITER_NEXT 5",
            "JUMP 2",
            "ITER_END",
            "HALT",
        ])

    def test_compile_function_with_for(self):
        compiled = compile_source("fn show(xs) { for x in xs { print(x) } 0 }")
        self.assertEqual([repr(i) for i in compiled.functions["show"].instructions], [
            "LOAD_NAME 'xs'",
            "ITER_START 'x'",
            "ITER_NEXT 7",
            "LOAD_NAME 'x'",
            "PRINT",
            "JUMP 2",
            "ITER_END",
            "CONST 0",
            "RETURN",
        ])

    def test_compile_while_break(self):
        code = compile_source("while true { break }")
        self.assertEqual([repr(i) for i in code], [
            "CONST True",
            "JUMP_IF_FALSE 4",
            "JUMP 4",
            "JUMP 0",
            "HALT",
        ])

    def test_compile_while_continue(self):
        code = compile_source("while true { continue }")
        self.assertEqual([repr(i) for i in code], [
            "CONST True",
            "JUMP_IF_FALSE 4",
            "JUMP 0",
            "JUMP 0",
            "HALT",
        ])

    def test_compile_for_break(self):
        code = compile_source("for x in [1, 2] { break }")
        self.assertEqual([repr(i) for i in code], [
            "CONST 1",
            "CONST 2",
            "BUILD_LIST 2",
            "ITER_START 'x'",
            "ITER_NEXT 8",
            "JUMP 7",
            "JUMP 4",
            "ITER_END",
            "HALT",
        ])

    def test_compile_for_continue(self):
        code = compile_source("for x in [1, 2] { continue }")
        self.assertEqual([repr(i) for i in code], [
            "CONST 1",
            "CONST 2",
            "BUILD_LIST 2",
            "ITER_START 'x'",
            "ITER_NEXT 8",
            "JUMP 4",
            "JUMP 4",
            "ITER_END",
            "HALT",
        ])

    def test_compile_nested_break_targets_inner_loop(self):
        code = compile_source("for x in [1] { for y in [2] { break } print(x) }")
        self.assertEqual([repr(i) for i in code], [
            "CONST 1",
            "BUILD_LIST 1",
            "ITER_START 'x'",
            "ITER_NEXT 15",
            "CONST 2",
            "BUILD_LIST 1",
            "ITER_START 'y'",
            "ITER_NEXT 11",
            "JUMP 10",
            "JUMP 7",
            "ITER_END",
            "LOAD_NAME 'x'",
            "PRINT",
            "JUMP 3",
            "ITER_END",
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

    def test_compile_list_literal(self):
        compiled = compile_source("let xs = [1, 2, 3]")
        self.assertEqual([repr(i) for i in compiled], [
            "CONST 1",
            "CONST 2",
            "CONST 3",
            "BUILD_LIST 3",
            "DECLARE_NAME 'xs'",
            "HALT",
        ])

    def test_compile_empty_list_literal(self):
        compiled = compile_source("let xs = []")
        self.assertEqual([repr(i) for i in compiled], [
            "BUILD_LIST 0",
            "DECLARE_NAME 'xs'",
            "HALT",
        ])

    def test_compile_map_literal(self):
        compiled = compile_source('let m = { "a": 1, "b": 2 }')
        self.assertEqual([repr(i) for i in compiled], [
            "CONST 'a'",
            "CONST 1",
            "CONST 'b'",
            "CONST 2",
            "BUILD_MAP 2",
            "DECLARE_NAME 'm'",
            "HALT",
        ])

    def test_compile_empty_map_literal(self):
        compiled = compile_source("let m = {}")
        self.assertEqual([repr(i) for i in compiled], [
            "BUILD_MAP 0",
            "DECLARE_NAME 'm'",
            "HALT",
        ])

    def test_compile_map_index_expression(self):
        compiled = compile_source('let m = { "a": 1 } let x = m["a"]')
        self.assertEqual([repr(i) for i in compiled], [
            "CONST 'a'",
            "CONST 1",
            "BUILD_MAP 1",
            "DECLARE_NAME 'm'",
            "LOAD_NAME 'm'",
            "CONST 'a'",
            "INDEX",
            "DECLARE_NAME 'x'",
            "HALT",
        ])

    def test_compile_map_index_assignment(self):
        compiled = compile_source('let m = { "a": 1 } m["a"] = 2')
        self.assertEqual([repr(i) for i in compiled], [
            "CONST 'a'",
            "CONST 1",
            "BUILD_MAP 1",
            "DECLARE_NAME 'm'",
            "LOAD_NAME 'm'",
            "CONST 'a'",
            "CONST 2",
            "STORE_INDEX 'm'",
            "HALT",
        ])

    def test_compile_nested_map_index_assignment(self):
        compiled = compile_source('let m = { "a": { "b": 1 } } m["a"]["b"] = 2')
        self.assertEqual(
            [repr(i) for i in compiled[-3:]],
            ["CONST 2", "STORE_INDEX 'm'", "HALT"],
        )
        self.assertEqual(
            [repr(i) for i in compiled[-6:-3]],
            ["CONST 'a'", "INDEX", "CONST 'b'"],
        )

    def test_compile_get_builtin(self):
        compiled = compile_source('let m = { "a": 1 } let x = get(m, "a", 0)')
        self.assertEqual([repr(i) for i in compiled], [
            "CONST 'a'",
            "CONST 1",
            "BUILD_MAP 1",
            "DECLARE_NAME 'm'",
            "LOAD_NAME 'm'",
            "CONST 'a'",
            "CONST 0",
            "MAP_GET",
            "DECLARE_NAME 'x'",
            "HALT",
        ])

    def test_compile_index_expression(self):
        compiled = compile_source("let xs = [1, 2] let x = xs[0]")
        self.assertEqual([repr(i) for i in compiled], [
            "CONST 1",
            "CONST 2",
            "BUILD_LIST 2",
            "DECLARE_NAME 'xs'",
            "LOAD_NAME 'xs'",
            "CONST 0",
            "INDEX",
            "DECLARE_NAME 'x'",
            "HALT",
        ])

    def test_compile_read_file_builtin(self):
        compiled = compile_source('let text = read_file("notes.txt")')
        self.assertEqual([repr(i) for i in compiled], [
            "CONST 'notes.txt'",
            "READ_FILE",
            "DECLARE_NAME 'text'",
            "HALT",
        ])

    def test_compile_read_csv_builtin(self):
        compiled = compile_source(
            'let rows = read_csv("scores.csv", { name: String, score: Float })'
        )
        self.assertEqual([repr(i) for i in compiled], [
            "CONST 'scores.csv'",
            "READ_CSV (('name', 'String'), ('score', 'Float'))",
            "DECLARE_NAME 'rows'",
            "HALT",
        ])

    def test_compile_len_builtin(self):
        compiled = compile_source("let xs = [1, 2] let n = len(xs)")
        self.assertEqual([repr(i) for i in compiled], [
            "CONST 1",
            "CONST 2",
            "BUILD_LIST 2",
            "DECLARE_NAME 'xs'",
            "LOAD_NAME 'xs'",
            "LEN",
            "DECLARE_NAME 'n'",
            "HALT",
        ])

    def test_compile_list_concatenation(self):
        compiled = compile_source("let xs = [1] + [2]")
        self.assertEqual([repr(i) for i in compiled], [
            "CONST 1",
            "BUILD_LIST 1",
            "CONST 2",
            "BUILD_LIST 1",
            "ADD",
            "DECLARE_NAME 'xs'",
            "HALT",
        ])

    def test_compile_len_rejects_wrong_argument_count(self):
        with self.assertRaisesRegex(RuntimeError, "`len` expects exactly one argument"):
            compile_source("let n = len([1], [2])")


if __name__ == "__main__":
    unittest.main()
