from compiler.ast.nodes import Identifier, IntegerLiteral, LetStatement, Program
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
        name = Identifier(self._expect(TokenType.IDENTIFIER, "Expected identifier"))
        self._expect(TokenType.EQUAL, "Expected '='")
        if self.current.type != TokenType.INTEGER:
            raise SyntaxError(
                f"Expected integer literal at line {self.current.line}, column {self.current.column}"
            )
        value = IntegerLiteral(int(self.current.value))
        self._advance()
        return LetStatement(name=name, value=value, mutable=False)
