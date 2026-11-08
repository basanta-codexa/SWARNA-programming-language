from compiler.ast.nodes import AssignmentStatement, BinaryExpression, BlockStatement, BoolLiteral, Expression, FloatLiteral, Identifier, IfStatement, IntegerLiteral, LetStatement, PrintStatement, Program, Statement, UnaryExpression, WhileStatement
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
        statements: list[Statement] = []
        while self.current.type != TokenType.EOF:
            statements.append(self.parse_statement())
            while self.current.type == TokenType.SEMICOLON:
                self._advance()
        return Program(statements=statements)

    def parse_statement(self) -> Statement:
        if self.current.type == TokenType.KEYWORD_LET:
            return self.parse_let_statement()
        if self.current.type == TokenType.KEYWORD_IF:
            return self.parse_if_statement()
        if self.current.type == TokenType.KEYWORD_WHILE:
            return self.parse_while_statement()
        if self.current.type == TokenType.IDENTIFIER and self.current.value == "print":
            return self.parse_print_statement()
        if self.current.type == TokenType.IDENTIFIER:
            return self.parse_assignment_statement()
        raise SyntaxError(
            f"Expected statement at line {self.current.line}, column {self.current.column}"
        )

    def parse_assignment_statement(self) -> AssignmentStatement:
        name = Identifier(self.current.value)
        self._advance()
        self._expect(TokenType.EQUAL, "Expected '=' in assignment")
        value = self.parse_expression()
        return AssignmentStatement(name=name, value=value)

    def parse_if_statement(self) -> IfStatement:
        self._expect(TokenType.KEYWORD_IF, "Expected 'if'")
        condition = self.parse_expression()
        then_branch = self.parse_block()
        else_branch = None
        if self.current.type == TokenType.KEYWORD_ELSE:
            self._advance()
            if self.current.type == TokenType.KEYWORD_IF:
                else_branch = BlockStatement(statements=[self.parse_if_statement()])
            else:
                else_branch = self.parse_block()
        return IfStatement(condition=condition, then_branch=then_branch, else_branch=else_branch)

    def parse_while_statement(self) -> WhileStatement:
        self._expect(TokenType.KEYWORD_WHILE, "Expected 'while'")
        condition = self.parse_expression()
        body = self.parse_block()
        return WhileStatement(condition=condition, body=body)

    def parse_block(self) -> BlockStatement:
        self._expect(TokenType.LBRACE, "Expected '{'")
        statements: list[Statement] = []
        while self.current.type != TokenType.RBRACE:
            if self.current.type == TokenType.EOF:
                raise SyntaxError("Expected '}' before end of input")
            statements.append(self.parse_statement())
            while self.current.type == TokenType.SEMICOLON:
                self._advance()
        self._advance()  # '}'
        return BlockStatement(statements=statements)

    def parse_print_statement(self) -> PrintStatement:
        self._advance()  # 'print'
        self._expect(TokenType.LPAREN, "Expected '(' after print")
        value = self.parse_expression()
        self._expect(TokenType.RPAREN, "Expected ')' after print argument")
        return PrintStatement(value=value)

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
        return self.parse_or()

    def parse_or(self) -> Expression:
        node = self.parse_and()
        while self.current.type == TokenType.PIPEPIPE:
            op = self.current.value
            self._advance()
            node = BinaryExpression(left=node, operator=op, right=self.parse_and())
        return node

    def parse_and(self) -> Expression:
        node = self.parse_comparison()
        while self.current.type == TokenType.AMPAMP:
            op = self.current.value
            self._advance()
            node = BinaryExpression(left=node, operator=op, right=self.parse_comparison())
        return node

    def parse_comparison(self) -> Expression:
        node = self.parse_additive()
        if self.current.type in (
            TokenType.EQEQ,
            TokenType.BANGEQ,
            TokenType.LT,
            TokenType.LTEQ,
            TokenType.GT,
            TokenType.GTEQ,
        ):
            op = self.current.value
            self._advance()
            node = BinaryExpression(left=node, operator=op, right=self.parse_additive())
        return node

    def parse_additive(self) -> Expression:
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
        if self.current.type in (TokenType.MINUS, TokenType.BANG):
            op = self.current.value
            self._advance()
            return UnaryExpression(operator=op, operand=self.parse_factor())
        if self.current.type == TokenType.INTEGER:
            value = IntegerLiteral(int(self.current.value))
            self._advance()
            return value
        if self.current.type == TokenType.FLOAT:
            value = FloatLiteral(float(self.current.value))
            self._advance()
            return value
        if self.current.type == TokenType.KEYWORD_TRUE:
            self._advance()
            return BoolLiteral(True)
        if self.current.type == TokenType.KEYWORD_FALSE:
            self._advance()
            return BoolLiteral(False)
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
