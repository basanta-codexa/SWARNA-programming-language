import unittest

from compiler.ast.nodes import AssignmentStatement, BinaryExpression, BlockExpression, BlockStatement, BoolLiteral, CallExpression, FloatLiteral, FunctionDeclaration, Identifier, IfExpression, IfStatement, IndexExpression, IntegerLiteral, LetStatement, ListLiteral, Parameter, PrintStatement, Program, StringLiteral, UnaryExpression, WhileStatement
from compiler.diagnostics import SourceSpan
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser


class TestParser(unittest.TestCase):
    def test_parse_let_integer(self):
        parser = Parser(Lexer("let x = 42"))
        program = parser.parse_program()
        self.assertEqual(
            program,
            Program(statements=[LetStatement(name=Identifier("x"), value=IntegerLiteral(42), constant=False)]),
        )

    def test_parse_const_integer(self):
        parser = Parser(Lexer("const x = 42"))
        program = parser.parse_program()
        self.assertEqual(
            program,
            Program(statements=[LetStatement(name=Identifier("x"), value=IntegerLiteral(42), constant=True)]),
        )

    def test_parse_let_mut_migration_error(self):
        parser = Parser(Lexer("let mut x = 1"))
        with self.assertRaisesRegex(SyntaxError, "let mut"):
            parser.parse_program()

    def test_parse_integer_expression_precedence(self):
        parser = Parser(Lexer("let x = 1 + 2 * 3"))
        program = parser.parse_program()
        expected = Program(
            statements=[
                LetStatement(
                    name=Identifier("x"),
                    value=BinaryExpression(
                        left=IntegerLiteral(1),
                        operator="+",
                        right=BinaryExpression(
                            left=IntegerLiteral(2),
                            operator="*",
                            right=IntegerLiteral(3),
                        ),
                    ),
                    constant=False,
                )
            ]
        )
        self.assertEqual(program, expected)

    def test_parse_parenthesized_expression(self):
        parser = Parser(Lexer("let x = (1 + 2) * 3"))
        program = parser.parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        self.assertEqual(stmt.value.operator, "*")
        assert isinstance(stmt.value.left, BinaryExpression)
        self.assertEqual(stmt.value.left.operator, "+")

    def test_parse_identifier_in_expression(self):
        parser = Parser(Lexer("let y = x + 1"))
        program = parser.parse_program()
        expected = Program(
            statements=[
                LetStatement(
                    name=Identifier("y"),
                    value=BinaryExpression(
                        left=Identifier("x"),
                        operator="+",
                        right=IntegerLiteral(1),
                    ),
                    constant=False,
                )
            ]
        )
        self.assertEqual(program, expected)

    def test_parse_unary_minus(self):
        parser = Parser(Lexer("let x = -1 + 2"))
        program = parser.parse_program()
        expected = Program(
            statements=[
                LetStatement(
                    name=Identifier("x"),
                    value=BinaryExpression(
                        left=UnaryExpression(operator="-", operand=IntegerLiteral(1)),
                        operator="+",
                        right=IntegerLiteral(2),
                    ),
                    constant=False,
                )
            ]
        )
        self.assertEqual(program, expected)

    def test_parse_multiple_let_statements(self):
        parser = Parser(Lexer("let x = 1 let y = x + 2"))
        program = parser.parse_program()
        self.assertEqual(len(program.statements), 2)
        self.assertEqual(program.statements[0].name.name, "x")
        self.assertEqual(program.statements[1].name.name, "y")
        assert isinstance(program.statements[1].value, BinaryExpression)
        self.assertEqual(program.statements[1].value.left, Identifier("x"))

    def test_parse_print_statement(self):
        parser = Parser(Lexer("print(42)"))
        program = parser.parse_program()
        self.assertEqual(program, Program(statements=[PrintStatement(value=IntegerLiteral(42))]))

    def test_parse_print_expression(self):
        parser = Parser(Lexer("let x = 1 print(x + 2)"))
        program = parser.parse_program()
        self.assertEqual(len(program.statements), 2)
        assert isinstance(program.statements[1], PrintStatement)
        assert isinstance(program.statements[1].value, BinaryExpression)

    def test_parse_bool_literals(self):
        parser = Parser(Lexer("let a = true let b = false"))
        program = parser.parse_program()
        self.assertEqual(program.statements[0], LetStatement(name=Identifier("a"), value=BoolLiteral(True), constant=False))
        self.assertEqual(program.statements[1], LetStatement(name=Identifier("b"), value=BoolLiteral(False), constant=False))

    def test_parse_comparison(self):
        parser = Parser(Lexer("let x = 1 + 2 <= 3"))
        program = parser.parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        assert isinstance(stmt.value, BinaryExpression)
        self.assertEqual(stmt.value.operator, "<=")
        assert isinstance(stmt.value.left, BinaryExpression)
        self.assertEqual(stmt.value.left.operator, "+")

    def test_parse_logical_precedence(self):
        parser = Parser(Lexer("let x = true || false && false"))
        program = parser.parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        assert isinstance(stmt.value, BinaryExpression)
        self.assertEqual(stmt.value.operator, "||")
        assert isinstance(stmt.value.right, BinaryExpression)
        self.assertEqual(stmt.value.right.operator, "&&")

    def test_parse_word_operators_match_symbols(self):
        symbolic = Parser(Lexer("let x = true && false || !true")).parse_program()
        words = Parser(Lexer("let x = true and false or not true")).parse_program()
        self.assertEqual(words, symbolic)

    def test_parse_unary_bang(self):
        parser = Parser(Lexer("let x = !true"))
        program = parser.parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        self.assertEqual(stmt.value, UnaryExpression(operator="!", operand=BoolLiteral(True)))

    def test_parse_if_else(self):
        parser = Parser(Lexer("if true { let x = 1 } else { let x = 2 }"))
        program = parser.parse_program()
        self.assertEqual(len(program.statements), 1)
        stmt = program.statements[0]
        assert isinstance(stmt, IfStatement)
        self.assertEqual(stmt.condition, BoolLiteral(True))
        self.assertIsNotNone(stmt.else_branch)
        assert isinstance(stmt.then_branch, BlockStatement)
        self.assertEqual(len(stmt.then_branch.statements), 1)

    def test_parse_if_expression(self):
        parser = Parser(Lexer("let x = if true { 1 } else { 2 }"))
        program = parser.parse_program()
        self.assertEqual(
            program,
            Program(statements=[
                LetStatement(
                    name=Identifier("x"),
                    value=IfExpression(
                        condition=BoolLiteral(True),
                        then_value=IntegerLiteral(1),
                        else_value=IntegerLiteral(2),
                    ),
                    constant=False,
                )
            ]),
        )

    def test_parse_if_expression_requires_else(self):
        parser = Parser(Lexer("let x = if true { 1 }"))
        with self.assertRaisesRegex(SyntaxError, "requires an else branch"):
            parser.parse_program()

    def test_parse_nested_if_expression(self):
        parser = Parser(Lexer("let x = if true { if false { 1 } else { 2 } } else { 3 }"))
        program = parser.parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        assert isinstance(stmt.value, IfExpression)
        assert isinstance(stmt.value.then_value, IfExpression)

    def test_parse_if_expression_with_block_branches(self):
        parser = Parser(Lexer("let x = if true { let y = 1 y + 2 } else { let y = 3 y + 4 }"))
        program = parser.parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        assert isinstance(stmt.value, IfExpression)
        then_block = stmt.value.then_value
        else_block = stmt.value.else_value
        assert isinstance(then_block, BlockExpression)
        assert isinstance(else_block, BlockExpression)
        self.assertEqual(len(then_block.statements), 1)
        self.assertIsInstance(then_block.statements[0], LetStatement)
        self.assertEqual(
            then_block.value,
            BinaryExpression(left=Identifier("y"), operator="+", right=IntegerLiteral(2)),
        )
        self.assertEqual(len(else_block.statements), 1)
        self.assertIsInstance(else_block.statements[0], LetStatement)
        self.assertEqual(
            else_block.value,
            BinaryExpression(left=Identifier("y"), operator="+", right=IntegerLiteral(4)),
        )

    def test_parse_if_expression_block_with_assignment(self):
        parser = Parser(Lexer("let x = if true { let y = 1 y = y + 1 y } else { 0 }"))
        program = parser.parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        assert isinstance(stmt.value, IfExpression)
        block = stmt.value.then_value
        assert isinstance(block, BlockExpression)
        self.assertEqual(len(block.statements), 2)
        self.assertIsInstance(block.statements[0], LetStatement)
        self.assertIsInstance(block.statements[1], AssignmentStatement)
        self.assertEqual(block.value, Identifier("y"))

    def test_parse_if_expression_block_with_print_and_while(self):
        parser = Parser(Lexer("let x = if true { print(1) while false { print(2) } 3 } else { 0 }"))
        program = parser.parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        assert isinstance(stmt.value, IfExpression)
        block = stmt.value.then_value
        assert isinstance(block, BlockExpression)
        self.assertEqual(len(block.statements), 2)
        self.assertIsInstance(block.statements[0], PrintStatement)
        self.assertIsInstance(block.statements[1], WhileStatement)
        self.assertEqual(block.value, IntegerLiteral(3))

    def test_parse_if_expression_block_with_nested_if_value(self):
        parser = Parser(Lexer("let x = if true { let y = 1 if y > 0 { 10 } else { 20 } } else { 30 }"))
        program = parser.parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        assert isinstance(stmt.value, IfExpression)
        block = stmt.value.then_value
        assert isinstance(block, BlockExpression)
        self.assertEqual(len(block.statements), 1)
        self.assertIsInstance(block.value, IfExpression)

    def test_parse_if_expression_block_allows_trailing_semicolons(self):
        parser = Parser(Lexer("let x = if true { let y = 1; y + 2; } else { 0; }"))
        program = parser.parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        assert isinstance(stmt.value, IfExpression)
        block = stmt.value.then_value
        assert isinstance(block, BlockExpression)
        self.assertEqual(
            block.value,
            BinaryExpression(left=Identifier("y"), operator="+", right=IntegerLiteral(2)),
        )

    def test_parse_if_expression_block_requires_final_value(self):
        parser = Parser(Lexer("let x = if true { let y = 1 } else { 0 }"))
        with self.assertRaisesRegex(SyntaxError, "Block value needs a final expression"):
            parser.parse_program()

    def test_parse_if_expression_block_rejects_statement_after_value(self):
        parser = Parser(Lexer("let x = if true { 1 let y = 2 } else { 0 }"))
        with self.assertRaises(SyntaxError) as raised:
            parser.parse_program()
        self.assertEqual(raised.exception.message, "Expected '}' after block value")
        self.assertIn("Only the last item", raised.exception.hint)

    def test_parse_if_expression_block_rejects_invalid_assignment_target(self):
        parser = Parser(Lexer("let x = if true { y + 1 = 2 0 } else { 0 }"))
        with self.assertRaisesRegex(SyntaxError, "Invalid assignment target"):
            parser.parse_program()

    def test_parse_assignment(self):
        parser = Parser(Lexer("x = 1 + 2"))
        program = parser.parse_program()
        self.assertEqual(
            program.statements[0],
            AssignmentStatement(
                name=Identifier("x"),
                value=BinaryExpression(left=IntegerLiteral(1), operator="+", right=IntegerLiteral(2)),
            ),
        )

    def test_parse_while(self):
        parser = Parser(Lexer("while i < 3 { i = i + 1 }"))
        program = parser.parse_program()
        self.assertEqual(len(program.statements), 1)
        stmt = program.statements[0]
        assert isinstance(stmt, WhileStatement)
        assert isinstance(stmt.condition, BinaryExpression)
        self.assertEqual(stmt.condition.operator, "<")
        self.assertEqual(len(stmt.body.statements), 1)

    def test_parse_float_literal(self):
        parser = Parser(Lexer("let x = 3.5"))
        program = parser.parse_program()
        self.assertEqual(
            program,
            Program(statements=[LetStatement(name=Identifier("x"), value=FloatLiteral(3.5), constant=False)]),
        )

    def test_parse_integer_division(self):
        parser = Parser(Lexer("let x = 7 // 2"))
        program = parser.parse_program()
        self.assertEqual(
            program,
            Program(statements=[LetStatement(
                name=Identifier("x"),
                value=BinaryExpression(left=IntegerLiteral(7), operator="//", right=IntegerLiteral(2)),
                constant=False,
            )]),
        )

    def test_parse_string_literal(self):
        parser = Parser(Lexer('let s = "hello"'))
        program = parser.parse_program()
        self.assertEqual(
            program,
            Program(statements=[LetStatement(name=Identifier("s"), value=StringLiteral("hello"), constant=False)]),
        )

    def test_parse_optional_semicolons(self):
        parser = Parser(Lexer("let x = 1; let y = 2; print(y);"))
        program = parser.parse_program()
        self.assertEqual(len(program.statements), 3)
        self.assertEqual(program.statements[0].name.name, "x")
        self.assertEqual(program.statements[1].name.name, "y")

    def test_parse_requires_equals(self):
        parser = Parser(Lexer("let x 42"))
        with self.assertRaises(SyntaxError):
            parser.parse_program()

    def test_nodes_carry_source_spans(self):
        program = Parser(Lexer("let x = 1 + 2")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        assert isinstance(stmt.value, BinaryExpression)
        self.assertEqual(program.span, SourceSpan(1, 1, 3))
        self.assertEqual(stmt.span, SourceSpan(1, 1, 3))
        self.assertEqual(stmt.name.span, SourceSpan(1, 5, 1))
        self.assertEqual(stmt.value.span, SourceSpan(1, 11, 1))
        self.assertEqual(stmt.value.left.span, SourceSpan(1, 9, 1))
        self.assertEqual(stmt.value.right.span, SourceSpan(1, 13, 1))

    def test_statement_spans(self):
        program = Parser(
            Lexer("print(1) if true { let x = 1 } while false { let y = 2 }")
        ).parse_program()
        print_stmt, if_stmt, while_stmt = program.statements
        assert isinstance(print_stmt, PrintStatement)
        assert isinstance(if_stmt, IfStatement)
        assert isinstance(while_stmt, WhileStatement)
        self.assertEqual(print_stmt.span, SourceSpan(1, 1, 5))
        self.assertEqual(if_stmt.span, SourceSpan(1, 10, 2))
        self.assertEqual(if_stmt.then_branch.span, SourceSpan(1, 18, 1))
        self.assertEqual(while_stmt.span, SourceSpan(1, 32, 5))
        self.assertEqual(while_stmt.body.span, SourceSpan(1, 44, 1))

    def test_if_expression_span(self):
        program = Parser(Lexer("let x = if true { 1 } else { 2 }")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        assert isinstance(stmt.value, IfExpression)
        self.assertEqual(stmt.value.span, SourceSpan(1, 9, 2))

    def test_assignment_span(self):
        program = Parser(Lexer("x = 1")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, AssignmentStatement)
        self.assertEqual(stmt.span, SourceSpan(1, 1, 1))
        self.assertEqual(stmt.name.span, SourceSpan(1, 1, 1))

    def test_parse_function_declaration(self):
        program = Parser(Lexer("fn add(a: Int, b: Int) -> Int { a + b }")).parse_program()
        self.assertEqual(
            program,
            Program(statements=[
                FunctionDeclaration(
                    name=Identifier("add"),
                    parameters=[
                        Parameter(name=Identifier("a"), type_name=Identifier("Int")),
                        Parameter(name=Identifier("b"), type_name=Identifier("Int")),
                    ],
                    return_type=Identifier("Int"),
                    body=BinaryExpression(left=Identifier("a"), operator="+", right=Identifier("b")),
                )
            ]),
        )

    def test_parse_function_without_annotations(self):
        program = Parser(Lexer("fn identity(x) { x }")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, FunctionDeclaration)
        self.assertEqual(stmt.parameters, [Parameter(name=Identifier("x"), type_name=None)])
        self.assertIsNone(stmt.return_type)
        self.assertEqual(stmt.body, Identifier("x"))

    def test_parse_function_with_block_body(self):
        program = Parser(Lexer("fn total(a: Int) -> Int { let b = a + 1 b }")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, FunctionDeclaration)
        body = stmt.body
        assert isinstance(body, BlockExpression)
        self.assertEqual(len(body.statements), 1)
        self.assertIsInstance(body.statements[0], LetStatement)
        self.assertEqual(body.value, Identifier("b"))

    def test_parse_function_allows_trailing_parameter_comma(self):
        program = Parser(Lexer("fn f(a: Int,) { a }")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, FunctionDeclaration)
        self.assertEqual(stmt.parameters, [Parameter(name=Identifier("a"), type_name=Identifier("Int"))])

    def test_parse_call_expression(self):
        program = Parser(Lexer("let x = add(1, 2)")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        self.assertEqual(
            stmt.value,
            CallExpression(
                callee=Identifier("add"),
                arguments=[IntegerLiteral(1), IntegerLiteral(2)],
            ),
        )

    def test_parse_call_with_no_arguments(self):
        program = Parser(Lexer("let x = now()")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        self.assertEqual(stmt.value, CallExpression(callee=Identifier("now"), arguments=[]))

    def test_parse_call_in_binary_expression(self):
        program = Parser(Lexer("let x = add(1, 2) * 3")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        assert isinstance(stmt.value, BinaryExpression)
        self.assertEqual(stmt.value.operator, "*")
        self.assertEqual(
            stmt.value.left,
            CallExpression(callee=Identifier("add"), arguments=[IntegerLiteral(1), IntegerLiteral(2)]),
        )
        self.assertEqual(stmt.value.right, IntegerLiteral(3))

    def test_parse_call_allows_trailing_argument_comma(self):
        program = Parser(Lexer("let x = add(1, 2,)")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        self.assertEqual(
            stmt.value,
            CallExpression(callee=Identifier("add"), arguments=[IntegerLiteral(1), IntegerLiteral(2)]),
        )

    def test_parse_bare_call_statement_rejected(self):
        parser = Parser(Lexer("add(1, 2)"))
        with self.assertRaisesRegex(SyntaxError, "Function calls cannot be used as statements yet"):
            parser.parse_program()

    def test_parse_function_requires_body_value(self):
        parser = Parser(Lexer("fn f() { }"))
        with self.assertRaisesRegex(SyntaxError, "Block value needs a final expression"):
            parser.parse_program()

    def test_parse_function_requires_return_type_after_arrow(self):
        parser = Parser(Lexer("fn f() -> { 1 }"))
        with self.assertRaisesRegex(SyntaxError, "Expected a return type after '->'"):
            parser.parse_program()

    def test_parse_function_requires_parameter_type_after_colon(self):
        parser = Parser(Lexer("fn f(a:) { a }"))
        with self.assertRaisesRegex(SyntaxError, "Expected a type after ':'"):
            parser.parse_program()

    def test_parse_list_literal(self):
        program = Parser(Lexer("let xs = [1, 2, 3]")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        self.assertEqual(
            stmt.value,
            ListLiteral(elements=[IntegerLiteral(1), IntegerLiteral(2), IntegerLiteral(3)]),
        )

    def test_parse_empty_list_literal(self):
        program = Parser(Lexer("let xs = []")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        self.assertEqual(stmt.value, ListLiteral(elements=[]))

    def test_parse_list_literal_allows_trailing_comma(self):
        program = Parser(Lexer("let xs = [1, 2,]")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        self.assertEqual(stmt.value, ListLiteral(elements=[IntegerLiteral(1), IntegerLiteral(2)]))

    def test_parse_nested_list_literal(self):
        program = Parser(Lexer("let xs = [[1], [2, 3]]")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        self.assertEqual(
            stmt.value,
            ListLiteral(
                elements=[
                    ListLiteral(elements=[IntegerLiteral(1)]),
                    ListLiteral(elements=[IntegerLiteral(2), IntegerLiteral(3)]),
                ]
            ),
        )

    def test_parse_index_expression(self):
        program = Parser(Lexer("let x = xs[0]")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        self.assertEqual(
            stmt.value,
            IndexExpression(collection=Identifier("xs"), index=IntegerLiteral(0)),
        )

    def test_parse_chained_index_expression(self):
        program = Parser(Lexer("let x = xs[0][1]")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        self.assertEqual(
            stmt.value,
            IndexExpression(
                collection=IndexExpression(collection=Identifier("xs"), index=IntegerLiteral(0)),
                index=IntegerLiteral(1),
            ),
        )

    def test_parse_index_on_call_result(self):
        program = Parser(Lexer("let x = values()[0]")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        self.assertEqual(
            stmt.value,
            IndexExpression(
                collection=CallExpression(callee=Identifier("values"), arguments=[]),
                index=IntegerLiteral(0),
            ),
        )

    def test_parse_empty_index_rejected(self):
        parser = Parser(Lexer("let x = xs[]"))
        with self.assertRaisesRegex(SyntaxError, "List index is empty"):
            parser.parse_program()

    def test_parse_index_assignment_rejected(self):
        parser = Parser(Lexer("xs[0] = 1"))
        with self.assertRaisesRegex(SyntaxError, "Index assignment is not supported yet"):
            parser.parse_program()

    def test_parse_index_assignment_in_block_rejected(self):
        parser = Parser(Lexer("let x = if true { xs[0] = 1 0 } else { 0 }"))
        with self.assertRaisesRegex(SyntaxError, "Index assignment is not supported yet"):
            parser.parse_program()

    def test_parse_generic_type_annotation_rejected(self):
        parser = Parser(Lexer("fn f(xs: List[Int]) -> Int { 0 }"))
        with self.assertRaisesRegex(SyntaxError, "Generic type annotations are not supported yet"):
            parser.parse_program()

    def test_parse_list_missing_comma_rejected(self):
        parser = Parser(Lexer("let xs = [1 2]"))
        with self.assertRaisesRegex(SyntaxError, "Expected ']' after list elements"):
            parser.parse_program()

    def test_function_and_call_spans(self):
        program = Parser(Lexer("fn add(a: Int) -> Int { a } let x = add(1)")).parse_program()
        declaration, binding = program.statements
        assert isinstance(declaration, FunctionDeclaration)
        assert isinstance(binding, LetStatement)
        self.assertEqual(declaration.span, SourceSpan(1, 1, 2))
        self.assertEqual(declaration.name.span, SourceSpan(1, 4, 3))
        self.assertEqual(declaration.parameters[0].name.span, SourceSpan(1, 8, 1))
        self.assertEqual(declaration.parameters[0].type_name.span, SourceSpan(1, 11, 3))
        self.assertEqual(declaration.return_type.span, SourceSpan(1, 19, 3))
        self.assertEqual(binding.value.span, SourceSpan(1, 37, 3))


if __name__ == "__main__":
    unittest.main()
