import unittest

from compiler.ast.nodes import AssignmentStatement, BinaryExpression, BlockStatement, BoolLiteral, FloatLiteral, Identifier, IfStatement, IntegerLiteral, LetStatement, PrintStatement, Program, UnaryExpression, WhileStatement
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser


class TestParser(unittest.TestCase):
    def test_parse_let_integer(self):
        parser = Parser(Lexer("let x = 42"))
        program = parser.parse_program()
        self.assertEqual(
            program,
            Program(statements=[LetStatement(name=Identifier("x"), value=IntegerLiteral(42), mutable=False)]),
        )

    def test_parse_let_mut_integer(self):
        parser = Parser(Lexer("let mut x = 42"))
        program = parser.parse_program()
        self.assertEqual(
            program,
            Program(statements=[LetStatement(name=Identifier("x"), value=IntegerLiteral(42), mutable=True)]),
        )

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
                    mutable=False,
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
                    mutable=False,
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
                    mutable=False,
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
        self.assertEqual(program.statements[0], LetStatement(name=Identifier("a"), value=BoolLiteral(True), mutable=False))
        self.assertEqual(program.statements[1], LetStatement(name=Identifier("b"), value=BoolLiteral(False), mutable=False))

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
            Program(statements=[LetStatement(name=Identifier("x"), value=FloatLiteral(3.5), mutable=False)]),
        )

    def test_parse_integer_division(self):
        parser = Parser(Lexer("let x = 7 // 2"))
        program = parser.parse_program()
        self.assertEqual(
            program,
            Program(statements=[LetStatement(
                name=Identifier("x"),
                value=BinaryExpression(left=IntegerLiteral(7), operator="//", right=IntegerLiteral(2)),
                mutable=False,
            )]),
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


if __name__ == "__main__":
    unittest.main()
