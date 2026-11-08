from compiler.ast.nodes import BinaryExpression, Expression, Identifier, IntegerLiteral, LetStatement, Program, UnaryExpression
from compiler.lexer.lexer import Lexer
from compiler.lexer.tokens import TokenType


class Parser:
    def __init__(self, lexer: Lexer):
        self.lexer = lexer
        self.current = self.lexer.next_token()

    def _advance(self) -> None:
        self.current = self.lexer.next_token()

    def _expect(self, token_type: TokenType, message: str) -> str:
        if self.current.type != token_type:
            raise SyntaxError(f"{message} at line {self.current.line}, column {self.current.column}")
        value = self.current.value
        self._advance()
        return value

    def parse_program(self) -> Program:
        statements: list[LetStatement] = []
        if self.current.type != TokenType.EOF:
            statements.append(self.parse_let_statement())
        if self.current.type != TokenType.EOF:
            raise SyntaxError(
                f"Unexpected token {self.current.value!r} at line {self.current.line}, column {self.current.column}"
            )
        return Program(statements=statements)

    def parse_let_statement(self) -> LetStatement:
        self._expect(TokenType.KEYWORD_LET, "Expected 'let'")
        mutable = False
        if self.current.type == TokenType.KEYWORD_MUT:
            mutable = True
            self._advance()
        name = Identifier(self._expect(TokenType.IDENTIFIER, "Expected identifier"))
        self._expect(TokenType.EQUAL, "Expected '='")
        value = self.parse_expression()
        return LetStatement(name=name, value=value, mutable=mutable)

    def parse_expression(self) -> Expression:
        node = self.parse_term()
        while self.current.type in (TokenType.PLUS, TokenType.MINUS):
            op = self.current.value
            self._advance()
            node = BinaryExpression(left=node, operator=op, right=self.parse_term())
        return node

    def parse_term(self) -> Expression:
        node = self.parse_factor()
        while self.current.type in (TokenType.STAR, TokenType.SLASH):
            op = self.current.value
            self._advance()
            node = BinaryExpression(left=node, operator=op, right=self.parse_factor())
        return node

    def parse_factor(self) -> Expression:
        if self.current.type == TokenType.MINUS:
            op = self.current.value
            self._advance()
            return UnaryExpression(operator=op, operand=self.parse_factor())
        if self.current.type == TokenType.INTEGER:
            value = IntegerLiteral(int(self.current.value))
            self._advance()
            return value
        if self.current.type == TokenType.IDENTIFIER:
            node = Identifier(self.current.value)
            self._advance()
            return node
        if self.current.type == TokenType.LPAREN:
            self._advance()
            node = self.parse_expression()
            self._expect(TokenType.RPAREN, "Expected ')'")
            return node
        raise SyntaxError(
            f"Expected expression at line {self.current.line}, column {self.current.column}"
        )
