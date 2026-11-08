import unittest

from compiler.ast.nodes import BinaryExpression, Identifier, IntegerLiteral, LetStatement, Program
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

    def test_parse_requires_equals(self):
        parser = Parser(Lexer("let x 42"))
        with self.assertRaises(SyntaxError):
            parser.parse_program()


if __name__ == "__main__":
    unittest.main()
