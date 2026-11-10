from compiler.ast.nodes import AssignmentStatement, BinaryExpression, BlockExpression, BlockStatement, BoolLiteral, Expression, FloatLiteral, Identifier, IfExpression, IfStatement, IntegerLiteral, LetStatement, PrintStatement, Program, Statement, StringLiteral, UnaryExpression, WhileStatement
from compiler.diagnostics import SwarnaSyntaxError
from compiler.lexer.lexer import Lexer
from compiler.lexer.tokens import TokenType


class Parser:
    def __init__(self, lexer: Lexer):
        self.lexer = lexer
        self.current = self.lexer.next_token()

    def _advance(self) -> None:
        self.current = self.lexer.next_token()

    def _expect(self, token_type: TokenType, message: str, hint: str | None = None) -> str:
        if self.current.type != token_type:
            raise SwarnaSyntaxError(message, self.current.span, hint=hint)
        value = self.current.value
        self._advance()
        return value

    def parse_program(self) -> Program:
        program_span = self.current.span
        statements: list[Statement] = []
        while self.current.type != TokenType.EOF:
            statements.append(self.parse_statement())
            while self.current.type == TokenType.SEMICOLON:
                self._advance()
        return Program(statements=statements, span=program_span)

    def parse_statement(self) -> Statement:
        if self.current.type == TokenType.KEYWORD_LET:
            return self.parse_binding_statement(constant=False)
        if self.current.type == TokenType.KEYWORD_CONST:
            return self.parse_binding_statement(constant=True)
        if self.current.type == TokenType.KEYWORD_IF:
            return self.parse_if_statement()
        if self.current.type == TokenType.KEYWORD_WHILE:
            return self.parse_while_statement()
        if self.current.type == TokenType.IDENTIFIER and self.current.value == "print":
            return self.parse_print_statement()
        if self.current.type == TokenType.IDENTIFIER:
            return self.parse_assignment_statement()
        raise SwarnaSyntaxError(
            "Expected statement",
            self.current.span,
            hint="Expected `let`, `const`, `if`, `while`, `print`, or an assignment.",
        )

    def parse_assignment_statement(self) -> AssignmentStatement:
        name_token = self.current
        name = Identifier(name_token.value, span=name_token.span)
        self._advance()
        self._expect(
            TokenType.EQUAL,
            "Expected '=' in assignment",
            hint="Assignments use `name = value`.",
        )
        value = self.parse_expression()
        return AssignmentStatement(name=name, value=value, span=name_token.span)

    def parse_if_statement(self) -> IfStatement:
        if_token = self.current
        self._expect(TokenType.KEYWORD_IF, "Expected 'if'", hint="Write `if condition { ... }`.")
        condition = self.parse_expression()
        then_branch = self.parse_block()
        else_branch = None
        if self.current.type == TokenType.KEYWORD_ELSE:
            else_token = self.current
            self._advance()
            if self.current.type == TokenType.KEYWORD_IF:
                else_branch = BlockStatement(statements=[self.parse_if_statement()], span=else_token.span)
            else:
                else_branch = self.parse_block()
        return IfStatement(condition=condition, then_branch=then_branch, else_branch=else_branch, span=if_token.span)

    def parse_while_statement(self) -> WhileStatement:
        while_token = self.current
        self._expect(TokenType.KEYWORD_WHILE, "Expected 'while'", hint="Write `while condition { ... }`.")
        condition = self.parse_expression()
        body = self.parse_block()
        return WhileStatement(condition=condition, body=body, span=while_token.span)

    def parse_if_expression(self) -> IfExpression:
        if_token = self.current
        self._expect(TokenType.KEYWORD_IF, "Expected 'if'", hint="Write `if condition { value } else { value }`.")
        condition = self.parse_expression()
        then_value = self.parse_block_expression()
        self._expect(
            TokenType.KEYWORD_ELSE,
            "if used as an expression requires an else branch",
            hint="Add `else { ... }`, or use `if` as a statement.",
        )
        else_value = self.parse_block_expression()
        return IfExpression(condition=condition, then_value=then_value, else_value=else_value, span=if_token.span)

    def parse_block_expression(self) -> Expression:
        lbrace_token = self.current
        self._expect(
            TokenType.LBRACE,
            "Expected '{'",
            hint="An `if` expression branch is written as `{ value }`.",
        )
        statements: list[Statement] = []
        while self.current.type == TokenType.SEMICOLON:
            self._advance()

        while True:
            if self.current.type == TokenType.RBRACE:
                raise SwarnaSyntaxError(
                    "Block value needs a final expression",
                    self.current.span,
                    hint="End the block with a value, for example `{ let x = 1 x + 1 }`.",
                )

            if self.current.type in (
                TokenType.KEYWORD_LET,
                TokenType.KEYWORD_CONST,
                TokenType.KEYWORD_WHILE,
            ):
                statements.append(self.parse_statement())
            elif self.current.type == TokenType.IDENTIFIER and self.current.value == "print":
                statements.append(self.parse_print_statement())
            else:
                expr = self.parse_expression()
                if self.current.type == TokenType.EQUAL:
                    if not isinstance(expr, Identifier):
                        raise SwarnaSyntaxError(
                            "Invalid assignment target",
                            expr.span,
                            hint="Assignments must target a name, as in `name = value`.",
                        )
                    self._advance()
                    value = self.parse_expression()
                    statements.append(
                        AssignmentStatement(name=expr, value=value, span=expr.span)
                    )
                else:
                    value = expr
                    break

            while self.current.type == TokenType.SEMICOLON:
                self._advance()

        while self.current.type == TokenType.SEMICOLON:
            self._advance()
        if self.current.type != TokenType.RBRACE:
            raise SwarnaSyntaxError(
                "Expected '}' after block value",
                self.current.span,
                hint="Only the last item in a block value can be an expression; use `let` to name intermediate values.",
            )
        self._advance()  # '}'
        if not statements:
            return value
        return BlockExpression(
            statements=statements,
            value=value,
            span=value.span if value.span is not None else lbrace_token.span,
        )

    def parse_block(self) -> BlockStatement:
        lbrace_token = self.current
        self._expect(TokenType.LBRACE, "Expected '{'", hint="Blocks use `{ ... }`.")
        statements: list[Statement] = []
        while self.current.type != TokenType.RBRACE:
            if self.current.type == TokenType.EOF:
                raise SwarnaSyntaxError(
                    "Expected '}' before end of input",
                    self.current.span,
                    hint="Add a closing `}`.",
                )
            statements.append(self.parse_statement())
            while self.current.type == TokenType.SEMICOLON:
                self._advance()
        self._advance()  # '}'
        return BlockStatement(statements=statements, span=lbrace_token.span)

    def parse_print_statement(self) -> PrintStatement:
        print_token = self.current
        self._advance()  # 'print'
        self._expect(
            TokenType.LPAREN,
            "Expected '(' after print",
            hint="`print` takes one argument in parentheses: `print(value)`.",
        )
        value = self.parse_expression()
        self._expect(
            TokenType.RPAREN,
            "Expected ')' after print argument",
            hint="Close the `print` call with `)`.",
        )
        return PrintStatement(value=value, span=print_token.span)

    def parse_binding_statement(self, constant: bool) -> LetStatement:
        keyword_token = self.current
        self._advance()  # 'let' or 'const'
        if not constant and self.current.type == TokenType.IDENTIFIER and self.current.value == "mut":
            raise SwarnaSyntaxError(
                "`let mut` was removed",
                self.current.span,
                hint="Use `let` for a mutable binding or `const` for an immutable one.",
            )
        name_token = self.current
        name = Identifier(
            self._expect(
                TokenType.IDENTIFIER,
                "Expected identifier",
                hint="Provide a name after `let` or `const`.",
            ),
            span=name_token.span,
        )
        self._expect(
            TokenType.EQUAL,
            "Expected '='",
            hint="Bindings use `let name = value` or `const name = value`.",
        )
        value = self.parse_expression()
        return LetStatement(name=name, value=value, constant=constant, span=keyword_token.span)

    def parse_expression(self) -> Expression:
        return self.parse_or()

    def parse_or(self) -> Expression:
        node = self.parse_and()
        while self.current.type in (TokenType.PIPEPIPE, TokenType.KEYWORD_OR):
            op_token = self.current
            self._advance()
            node = BinaryExpression(left=node, operator="||", right=self.parse_and(), span=op_token.span)
        return node

    def parse_and(self) -> Expression:
        node = self.parse_comparison()
        while self.current.type in (TokenType.AMPAMP, TokenType.KEYWORD_AND):
            op_token = self.current
            self._advance()
            node = BinaryExpression(left=node, operator="&&", right=self.parse_comparison(), span=op_token.span)
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
            op_token = self.current
            op = self.current.value
            self._advance()
            node = BinaryExpression(left=node, operator=op, right=self.parse_additive(), span=op_token.span)
        return node

    def parse_additive(self) -> Expression:
        node = self.parse_term()
        while self.current.type in (TokenType.PLUS, TokenType.MINUS):
            op_token = self.current
            op = self.current.value
            self._advance()
            node = BinaryExpression(left=node, operator=op, right=self.parse_term(), span=op_token.span)
        return node

    def parse_term(self) -> Expression:
        node = self.parse_factor()
        while self.current.type in (TokenType.STAR, TokenType.SLASH, TokenType.SLASHSLASH):
            op_token = self.current
            op = self.current.value
            self._advance()
            node = BinaryExpression(left=node, operator=op, right=self.parse_factor(), span=op_token.span)
        return node

    def parse_factor(self) -> Expression:
        if self.current.type in (TokenType.MINUS, TokenType.BANG, TokenType.KEYWORD_NOT):
            op_token = self.current
            op = "-" if self.current.type == TokenType.MINUS else "!"
            self._advance()
            return UnaryExpression(operator=op, operand=self.parse_factor(), span=op_token.span)
        if self.current.type == TokenType.INTEGER:
            token = self.current
            self._advance()
            return IntegerLiteral(int(token.value), span=token.span)
        if self.current.type == TokenType.FLOAT:
            token = self.current
            self._advance()
            return FloatLiteral(float(token.value), span=token.span)
        if self.current.type == TokenType.STRING:
            token = self.current
            self._advance()
            return StringLiteral(token.value, span=token.span)
        if self.current.type == TokenType.KEYWORD_TRUE:
            token = self.current
            self._advance()
            return BoolLiteral(True, span=token.span)
        if self.current.type == TokenType.KEYWORD_FALSE:
            token = self.current
            self._advance()
            return BoolLiteral(False, span=token.span)
        if self.current.type == TokenType.KEYWORD_IF:
            return self.parse_if_expression()
        if self.current.type == TokenType.IDENTIFIER:
            token = self.current
            self._advance()
            return Identifier(token.value, span=token.span)
        if self.current.type == TokenType.LPAREN:
            self._advance()
            node = self.parse_expression()
            self._expect(TokenType.RPAREN, "Expected ')'", hint="Add a closing `)`.")
            return node
        raise SwarnaSyntaxError(
            "Expected expression",
            self.current.span,
            hint="Expected a literal, name, or parenthesized expression.",
        )
