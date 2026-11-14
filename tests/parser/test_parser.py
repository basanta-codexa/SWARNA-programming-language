import unittest

from compiler.ast.nodes import AssignmentStatement, BinaryExpression, BlockExpression, BlockStatement, BoolLiteral, BreakStatement, CallExpression, ContinueStatement, ExpressionStatement, FloatLiteral, ForStatement, FunctionDeclaration, Identifier, IfExpression, IfStatement, IndexAssignmentStatement, IndexExpression, IntegerLiteral, LetStatement, ListLiteral, MapLiteral, Parameter, PrintStatement, Program, StringLiteral, TypeAnnotation, UnaryExpression, UnitLiteral, WhileStatement
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
        with self.assertRaisesRegex(SyntaxError, "requires a final else branch"):
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

    def test_parse_function_block_with_for(self):
        parser = Parser(Lexer("fn f(xs) { for x in xs { print(x) } 0 }"))
        program = parser.parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, FunctionDeclaration)
        body = stmt.body
        assert isinstance(body, BlockExpression)
        self.assertEqual(len(body.statements), 1)
        self.assertIsInstance(body.statements[0], ForStatement)
        self.assertEqual(body.value, IntegerLiteral(0))

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

    def test_parse_if_expression_block_without_final_expression_yields_unit(self):
        program = Parser(Lexer("let x = if true { let y = 1 } else { 0 }")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        assert isinstance(stmt.value, IfExpression)
        assert isinstance(stmt.value.then_value, BlockExpression)
        self.assertIsInstance(stmt.value.then_value.value, UnitLiteral)

    def test_parse_block_with_trailing_statement_yields_unit(self):
        program = Parser(Lexer("let x = if true { 1 let y = 2 } else { 0 }")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        assert isinstance(stmt.value, IfExpression)
        assert isinstance(stmt.value.then_value, BlockExpression)
        self.assertIsInstance(stmt.value.then_value.value, UnitLiteral)

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

    def test_parse_for(self):
        program = Parser(Lexer("for x in [1, 2] { print(x) }")).parse_program()
        self.assertEqual(
            program.statements,
            [
                ForStatement(
                    name=Identifier("x"),
                    iterable=ListLiteral(elements=[IntegerLiteral(1), IntegerLiteral(2)]),
                    body=BlockStatement(statements=[PrintStatement(value=Identifier("x"))]),
                )
            ],
        )

    def test_parse_for_requires_in(self):
        parser = Parser(Lexer("for x [1] { print(x) }"))
        with self.assertRaisesRegex(SyntaxError, "Expected 'in' after the loop variable"):
            parser.parse_program()

    def test_parse_for_requires_loop_variable(self):
        parser = Parser(Lexer("for in [1] { print(1) }"))
        with self.assertRaisesRegex(SyntaxError, "Expected a loop variable after 'for'"):
            parser.parse_program()

    def test_parse_for_allows_empty_body(self):
        program = Parser(Lexer("for x in [] { }")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, ForStatement)
        self.assertEqual(stmt.body.statements, [])

    def test_parse_break(self):
        program = Parser(Lexer("while true { break }")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, WhileStatement)
        self.assertEqual(stmt.body.statements, [BreakStatement()])

    def test_parse_continue(self):
        program = Parser(Lexer("while true { continue }")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, WhileStatement)
        self.assertEqual(stmt.body.statements, [ContinueStatement()])

    def test_parse_break_and_continue_in_for(self):
        program = Parser(Lexer("for x in [1] { if x > 0 { continue } break }")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, ForStatement)
        self.assertIsInstance(stmt.body.statements[0], IfStatement)
        self.assertEqual(stmt.body.statements[1], BreakStatement())

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
                        Parameter(name=Identifier("a"), type_name=TypeAnnotation("Int", [])),
                        Parameter(name=Identifier("b"), type_name=TypeAnnotation("Int", [])),
                    ],
                    return_type=TypeAnnotation("Int", []),
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
        self.assertEqual(stmt.parameters, [Parameter(name=Identifier("a"), type_name=TypeAnnotation("Int", []))])

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

    def test_parse_bare_call_statement(self):
        program = Parser(Lexer("add(1, 2)")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, ExpressionStatement)
        self.assertEqual(
            stmt.expression,
            CallExpression(callee=Identifier("add"), arguments=[IntegerLiteral(1), IntegerLiteral(2)]),
        )

    def test_parse_function_with_empty_body_yields_unit(self):
        program = Parser(Lexer("fn f() { }")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, FunctionDeclaration)
        self.assertIsInstance(stmt.body, UnitLiteral)

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

    def test_parse_map_literal(self):
        program = Parser(Lexer('let m = { "a": 1, "b": 2 }')).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        self.assertEqual(
            stmt.value,
            MapLiteral(
                entries=[
                    (StringLiteral("a"), IntegerLiteral(1)),
                    (StringLiteral("b"), IntegerLiteral(2)),
                ]
            ),
        )

    def test_parse_empty_map_literal(self):
        program = Parser(Lexer("let m = {}")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        self.assertEqual(stmt.value, MapLiteral(entries=[]))

    def test_parse_map_literal_allows_trailing_comma(self):
        program = Parser(Lexer('let m = { "a": 1, }')).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        self.assertEqual(
            stmt.value,
            MapLiteral(entries=[(StringLiteral("a"), IntegerLiteral(1))]),
        )

    def test_parse_nested_map_literal(self):
        program = Parser(Lexer('let m = { "a": { "b": 2 } }')).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        self.assertEqual(
            stmt.value,
            MapLiteral(
                entries=[
                    (
                        StringLiteral("a"),
                        MapLiteral(entries=[(StringLiteral("b"), IntegerLiteral(2))]),
                    )
                ]
            ),
        )

    def test_parse_map_literal_as_if_branch(self):
        program = Parser(Lexer('let m = if true { { "a": 1 } } else { {} }')).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        self.assertIsInstance(stmt.value, IfExpression)

    def test_parse_map_missing_colon_rejected(self):
        parser = Parser(Lexer('let m = { "a" 1 }'))
        with self.assertRaisesRegex(SyntaxError, "Expected ':' after map key"):
            parser.parse_program()

    def test_parse_map_missing_brace_rejected(self):
        parser = Parser(Lexer('let m = { "a": 1'))
        with self.assertRaisesRegex(SyntaxError, "Expected '}' after map entries"):
            parser.parse_program()

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

    def test_parse_index_assignment(self):
        program = Parser(Lexer('xs[0] = 1')).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, IndexAssignmentStatement)
        self.assertEqual(
            stmt.target,
            IndexExpression(collection=Identifier("xs"), index=IntegerLiteral(0)),
        )
        self.assertEqual(stmt.value, IntegerLiteral(1))

    def test_parse_nested_index_assignment(self):
        program = Parser(Lexer('m["a"]["b"] = 2')).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, IndexAssignmentStatement)
        self.assertEqual(
            stmt.target,
            IndexExpression(
                collection=IndexExpression(
                    collection=Identifier("m"), index=StringLiteral("a")
                ),
                index=StringLiteral("b"),
            ),
        )
        self.assertEqual(stmt.value, IntegerLiteral(2))

    def test_parse_index_assignment_in_block(self):
        program = Parser(Lexer("let x = if true { xs[0] = 1 0 } else { 0 }")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        branch = stmt.value
        assert isinstance(branch, IfExpression)
        assignment = branch.then_value
        assert isinstance(assignment, BlockExpression)
        self.assertIsInstance(assignment.statements[0], IndexAssignmentStatement)

    def test_parse_generic_type_annotation(self):
        program = Parser(
            Lexer("fn f(xs: List[Int], m: Map[String, List[Float]]) -> List[Map[String, Float]] { xs }")
        ).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, FunctionDeclaration)
        self.assertEqual(
            stmt.parameters[0].type_name,
            TypeAnnotation("List", [TypeAnnotation("Int", [])]),
        )
        self.assertEqual(
            stmt.parameters[1].type_name,
            TypeAnnotation(
                "Map",
                [
                    TypeAnnotation("String", []),
                    TypeAnnotation("List", [TypeAnnotation("Float", [])]),
                ],
            ),
        )
        self.assertEqual(
            stmt.return_type,
            TypeAnnotation(
                "List",
                [
                    TypeAnnotation(
                        "Map",
                        [TypeAnnotation("String", []), TypeAnnotation("Float", [])],
                    )
                ],
            ),
        )

    def test_parse_binding_type_annotation(self):
        program = Parser(Lexer("let totals: Map[String, Float] = {}")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        self.assertEqual(
            stmt.type_name,
            TypeAnnotation(
                "Map",
                [TypeAnnotation("String", []), TypeAnnotation("Float", [])],
            ),
        )

    def test_parse_empty_type_arguments_rejected(self):
        parser = Parser(Lexer("fn f(xs: List[]) { xs }"))
        with self.assertRaisesRegex(SyntaxError, "Type 'List' needs a type argument"):
            parser.parse_program()

    def test_parse_trailing_type_argument_comma_rejected(self):
        parser = Parser(Lexer("fn f(xs: List[Int,]) { xs }"))
        with self.assertRaisesRegex(SyntaxError, "Type argument list ends with a comma"):
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

    def test_parse_return_statement(self):
        from compiler.ast.nodes import ReturnStatement
        program = Parser(Lexer("fn f() { return 1 }")).parse_program()
        fn = program.statements[0]
        assert isinstance(fn, FunctionDeclaration)
        assert isinstance(fn.body, BlockExpression)
        self.assertIsInstance(fn.body.statements[0], ReturnStatement)

    def test_parse_if_expression_else_if_chain(self):
        from compiler.ast.nodes import IfExpression
        program = Parser(Lexer("let x = if a { 1 } else if b { 2 } else { 3 }")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        assert isinstance(stmt.value, IfExpression)
        assert isinstance(stmt.value.else_value, IfExpression)

    def test_parse_if_expression_elif_chain(self):
        from compiler.ast.nodes import IfExpression
        program = Parser(Lexer("let x = if a { 1 } elif b { 2 } else { 3 }")).parse_program()
        stmt = program.statements[0]
        assert isinstance(stmt, LetStatement)
        assert isinstance(stmt.value, IfExpression)
        assert isinstance(stmt.value.else_value, IfExpression)


if __name__ == "__main__":
    unittest.main()
