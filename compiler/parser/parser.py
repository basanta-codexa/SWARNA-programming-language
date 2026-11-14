from compiler.ast.nodes import AssignmentStatement, BinaryExpression, BlockExpression, BlockStatement, BoolLiteral, BreakStatement, CallExpression, ContinueStatement, Expression, FloatLiteral, ForStatement, FunctionDeclaration, Identifier, IfExpression, IfStatement, IndexAssignmentStatement, IndexExpression, IntegerLiteral, LetStatement, ListLiteral, MapLiteral, Parameter, PrintStatement, Program, ReturnStatement, Statement, StringLiteral, TypeAnnotation, UnaryExpression, WhileStatement
from compiler.diagnostics import SwarnaSyntaxError
from compiler.lexer.lexer import Lexer
from compiler.lexer.tokens import TokenType


class Parser:
    def __init__(self, lexer: Lexer):
        self.lexer = lexer
        self.current = self.lexer.next_token()

    def _save(self):
        return (
            self.current,
            self.lexer.position,
            self.lexer.line,
            self.lexer.column,
            self.lexer.current_char,
        )

    def _restore(self, state) -> None:
        self.current, self.lexer.position, self.lexer.line, self.lexer.column, self.lexer.current_char = state

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
        if self.current.type == TokenType.KEYWORD_FOR:
            return self.parse_for_statement()
        if self.current.type == TokenType.KEYWORD_BREAK:
            token = self.current
            self._advance()
            return BreakStatement(span=token.span)
        if self.current.type == TokenType.KEYWORD_CONTINUE:
            token = self.current
            self._advance()
            return ContinueStatement(span=token.span)
        if self.current.type == TokenType.KEYWORD_RETURN:
            token = self.current
            self._advance()
            value = self.parse_expression()
            return ReturnStatement(value=value, span=token.span)
        if self.current.type == TokenType.KEYWORD_FN:
            return self.parse_function_declaration()
        if self.current.type == TokenType.IDENTIFIER and self.current.value == "print":
            return self.parse_print_statement()
        if self.current.type == TokenType.IDENTIFIER:
            return self.parse_assignment_statement()
        raise SwarnaSyntaxError(
            "Expected statement",
            self.current.span,
            hint="Expected `let`, `const`, `fn`, `if`, `while`, `for`, `break`, `continue`, `return`, `print`, or an assignment.",
        )

    def parse_assignment_statement(self) -> AssignmentStatement | IndexAssignmentStatement:
        name_token = self.current
        name = Identifier(name_token.value, span=name_token.span)
        self._advance()
        if self.current.type == TokenType.LPAREN:
            raise SwarnaSyntaxError(
                "Function calls cannot be used as statements yet",
                self.current.span,
                hint="Use the call in a `let` binding or inside `print(...)`.",
            )
        if self.current.type == TokenType.LBRACKET:
            target = self.parse_index(name)
            while self.current.type == TokenType.LBRACKET:
                target = self.parse_index(target)
            self._expect(
                TokenType.EQUAL,
                "Expected '=' in index assignment",
                hint="Assign an element as `values[index] = value`.",
            )
            value = self.parse_expression()
            return IndexAssignmentStatement(target=target, value=value, span=name_token.span)
        self._expect(
            TokenType.EQUAL,
            "Expected '=' in assignment",
            hint="Assignments use `name = value`.",
        )
        value = self.parse_expression()
        return AssignmentStatement(name=name, value=value, span=name_token.span)

    def parse_function_declaration(self) -> FunctionDeclaration:
        fn_token = self.current
        self._expect(TokenType.KEYWORD_FN, "Expected 'fn'", hint="Write `fn name(...) { ... }`.")
        name_token = self.current
        name_value = self._expect(
            TokenType.IDENTIFIER,
            "Expected a function name",
            hint="Write `fn name(...) { ... }`.",
        )
        name = Identifier(name_value, span=name_token.span)
        self._expect(
            TokenType.LPAREN,
            "Expected '(' after function name",
            hint="Write the parameters in parentheses: `fn name(a: Int) { ... }`.",
        )
        parameters: list[Parameter] = []
        if self.current.type != TokenType.RPAREN:
            while True:
                parameters.append(self.parse_parameter())
                if self.current.type == TokenType.COMMA:
                    self._advance()
                    if self.current.type == TokenType.RPAREN:
                        break
                    continue
                break
        self._expect(
            TokenType.RPAREN,
            "Expected ')' after parameters",
            hint="Close the parameter list with `)`.",
        )
        return_type = None
        if self.current.type == TokenType.ARROW:
            self._advance()
            return_type = self.parse_type_annotation(
                "Expected a return type after '->'",
                "Use `Int`, `Float`, `String`, `Bool`, `List[T]`, or `Map[K, V]`.",
            )
        body = self.parse_block_expression()
        return FunctionDeclaration(
            name=name,
            parameters=parameters,
            return_type=return_type,
            body=body,
            span=fn_token.span,
        )

    def parse_parameter(self) -> Parameter:
        name_token = self.current
        name_value = self._expect(
            TokenType.IDENTIFIER,
            "Expected parameter name",
            hint="Write a parameter as `name` or `name: Type`.",
        )
        name = Identifier(name_value, span=name_token.span)
        type_name = None
        if self.current.type == TokenType.COLON:
            self._advance()
            type_name = self.parse_type_annotation(
                "Expected a type after ':'",
                "Use `Int`, `Float`, `String`, `Bool`, `List[T]`, or `Map[K, V]`.",
            )
        return Parameter(name=name, type_name=type_name)

    def parse_type_annotation(
        self,
        message: str = "Expected a type",
        hint: str = "Use `Int`, `Float`, `String`, `Bool`, `List[T]`, or `Map[K, V]`.",
    ) -> TypeAnnotation:
        type_token = self.current
        type_value = self._expect(
            TokenType.IDENTIFIER,
            message,
            hint=hint,
        )
        arguments: list[TypeAnnotation] = []
        if self.current.type == TokenType.LBRACKET:
            self._advance()
            if self.current.type == TokenType.RBRACKET:
                raise SwarnaSyntaxError(
                    f"Type '{type_value}' needs a type argument",
                    self.current.span,
                    hint="Write `List[Int]` or `Map[String, Float]`.",
                )
            while True:
                arguments.append(self.parse_type_annotation())
                if self.current.type == TokenType.COMMA:
                    self._advance()
                    if self.current.type == TokenType.RBRACKET:
                        raise SwarnaSyntaxError(
                            "Type argument list ends with a comma",
                            self.current.span,
                            hint="Remove the trailing comma.",
                        )
                    continue
                break
            self._expect(
                TokenType.RBRACKET,
                "Expected ']' after type arguments",
                hint=f"Close the type with `]`, as in `{type_value}[Int]`.",
            )
        return TypeAnnotation(type_value, arguments, span=type_token.span)

    def parse_if_statement(self) -> IfStatement:
        if_token = self.current
        self._expect(TokenType.KEYWORD_IF, "Expected 'if'", hint="Write `if condition { ... }`.")
        return self._parse_if_statement_after_keyword(if_token)

    def _parse_if_statement_after_keyword(self, keyword_token) -> IfStatement:
        condition = self.parse_expression()
        then_branch = self.parse_block()
        else_branch = None
        if self.current.type == TokenType.KEYWORD_ELSE:
            else_token = self.current
            self._advance()
            if self.current.type == TokenType.KEYWORD_IF:
                else_branch = BlockStatement(statements=[self.parse_if_statement()], span=else_token.span)
            elif self.current.type == TokenType.KEYWORD_ELIF:
                elif_token = self.current
                self._advance()
                else_branch = BlockStatement(
                    statements=[self._parse_if_statement_after_keyword(elif_token)],
                    span=elif_token.span,
                )
            else:
                else_branch = self.parse_block()
        elif self.current.type == TokenType.KEYWORD_ELIF:
            elif_token = self.current
            self._advance()
            else_branch = BlockStatement(
                statements=[self._parse_if_statement_after_keyword(elif_token)],
                span=elif_token.span,
            )
        return IfStatement(
            condition=condition,
            then_branch=then_branch,
            else_branch=else_branch,
            span=keyword_token.span,
        )

    def parse_while_statement(self) -> WhileStatement:
        while_token = self.current
        self._expect(TokenType.KEYWORD_WHILE, "Expected 'while'", hint="Write `while condition { ... }`.")
        condition = self.parse_expression()
        body = self.parse_block()
        return WhileStatement(condition=condition, body=body, span=while_token.span)

    def parse_for_statement(self) -> ForStatement:
        for_token = self.current
        self._expect(
            TokenType.KEYWORD_FOR,
            "Expected 'for'",
            hint="Write `for item in values { ... }`.",
        )
        name_token = self.current
        name_value = self._expect(
            TokenType.IDENTIFIER,
            "Expected a loop variable after 'for'",
            hint="Write `for item in values { ... }`.",
        )
        name = Identifier(name_value, span=name_token.span)
        self._expect(
            TokenType.KEYWORD_IN,
            "Expected 'in' after the loop variable",
            hint="Write `for item in values { ... }`.",
        )
        iterable = self.parse_expression()
        body = self.parse_block()
        return ForStatement(name=name, iterable=iterable, body=body, span=for_token.span)

    def parse_if_expression(self) -> IfExpression:
        if_token = self.current
        self._expect(TokenType.KEYWORD_IF, "Expected 'if'", hint="Write `if condition { value } else { value }`.")
        return self._parse_if_expression_after_keyword(if_token)

    def _parse_if_expression_after_keyword(self, keyword_token) -> IfExpression:
        condition = self.parse_expression()
        then_value = self.parse_block_expression()
        if self.current.type == TokenType.KEYWORD_ELSE:
            self._advance()
            if self.current.type == TokenType.KEYWORD_IF:
                else_value = self.parse_if_expression()
            elif self.current.type == TokenType.KEYWORD_ELIF:
                elif_token = self.current
                self._advance()
                else_value = self._parse_if_expression_after_keyword(elif_token)
            else:
                else_value = self.parse_block_expression()
        elif self.current.type == TokenType.KEYWORD_ELIF:
            elif_token = self.current
            self._advance()
            else_value = self._parse_if_expression_after_keyword(elif_token)
        else:
            raise SwarnaSyntaxError(
                "if used as an expression requires a final else branch",
                self.current.span,
                hint="Add a final `else { ... }` so every path produces a value, or use `if` as a statement when no value is needed.",
            )
        return IfExpression(
            condition=condition,
            then_value=then_value,
            else_value=else_value,
            span=keyword_token.span,
        )

    def parse_block_expression(self) -> Expression:
        lbrace_token = self.current
        self._expect(
            TokenType.LBRACE,
            "Expected '{'",
            hint="A block value is written as `{ ... value }`.",
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

            if self.current.type == TokenType.KEYWORD_RETURN:
                return_stmt = self.parse_statement()
                statements.append(return_stmt)
                value = return_stmt.value
                break

            if self.current.type == TokenType.KEYWORD_IF:
                state = self._save()
                try:
                    if_stmt = self.parse_if_statement()
                    while self.current.type == TokenType.SEMICOLON:
                        self._advance()
                    if self.current.type == TokenType.RBRACE:
                        self._restore(state)
                    else:
                        statements.append(if_stmt)
                        continue
                except SwarnaSyntaxError:
                    self._restore(state)

            if self.current.type in (
                TokenType.KEYWORD_LET,
                TokenType.KEYWORD_CONST,
                TokenType.KEYWORD_WHILE,
                TokenType.KEYWORD_FOR,
                TokenType.KEYWORD_BREAK,
                TokenType.KEYWORD_CONTINUE,
                TokenType.KEYWORD_FN,
            ):
                statements.append(self.parse_statement())
            elif self.current.type == TokenType.IDENTIFIER and self.current.value == "print":
                statements.append(self.parse_print_statement())
            else:
                expr = self.parse_expression()
                if self.current.type == TokenType.EQUAL:
                    if isinstance(expr, IndexExpression):
                        self._advance()
                        value = self.parse_expression()
                        statements.append(
                            IndexAssignmentStatement(
                                target=expr, value=value, span=expr.span
                            )
                        )
                        while self.current.type == TokenType.SEMICOLON:
                            self._advance()
                        continue
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
                hint="Only the last item in a block value can be an expression; use `let` to name intermediate values or `return` to exit early.",
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
        type_name = None
        if self.current.type == TokenType.COLON:
            self._advance()
            type_name = self.parse_type_annotation(
                "Expected a type after ':'",
                "Use `Int`, `Float`, `String`, `Bool`, `List[T]`, or `Map[K, V]`.",
            )
        self._expect(
            TokenType.EQUAL,
            "Expected '='",
            hint="Bindings use `let name = value` or `let name: Type = value`.",
        )
        value = self.parse_expression()
        return LetStatement(
            name=name,
            value=value,
            constant=constant,
            type_name=type_name,
            span=keyword_token.span,
        )

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
        while self.current.type in (TokenType.STAR, TokenType.SLASH, TokenType.SLASHSLASH, TokenType.PERCENT):
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
        node = self.parse_primary()
        while self.current.type == TokenType.LBRACKET:
            node = self.parse_index(node)
        return node

    def parse_primary(self) -> Expression:
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
        if self.current.type == TokenType.LBRACKET:
            return self.parse_list_literal()
        if self.current.type == TokenType.LBRACE:
            return self.parse_map_literal()
        if self.current.type == TokenType.IDENTIFIER:
            token = self.current
            self._advance()
            callee = Identifier(token.value, span=token.span)
            if self.current.type == TokenType.LPAREN:
                return self.parse_call(callee)
            return callee
        if self.current.type == TokenType.LPAREN:
            self._advance()
            node = self.parse_expression()
            self._expect(TokenType.RPAREN, "Expected ')'", hint="Add a closing `)`.")
            return node
        raise SwarnaSyntaxError(
            "Expected expression",
            self.current.span,
            hint="Expected a literal, list, name, function call, or parenthesized expression.",
        )

    def parse_list_literal(self) -> ListLiteral:
        lbracket_token = self.current
        self._expect(
            TokenType.LBRACKET,
            "Expected '['",
            hint="A list is written as `[1, 2, 3]`.",
        )
        elements: list[Expression] = []
        if self.current.type != TokenType.RBRACKET:
            while True:
                elements.append(self.parse_expression())
                if self.current.type == TokenType.COMMA:
                    self._advance()
                    if self.current.type == TokenType.RBRACKET:
                        break
                    continue
                break
        self._expect(
            TokenType.RBRACKET,
            "Expected ']' after list elements",
            hint="Close the list with `]`, or separate elements with commas.",
        )
        return ListLiteral(elements=elements, span=lbracket_token.span)

    def parse_map_literal(self) -> MapLiteral:
        lbrace_token = self.current
        self._expect(
            TokenType.LBRACE,
            "Expected '{'",
            hint='A map is written as `{ "key": value }`.',
        )
        entries: list[tuple[Expression, Expression]] = []
        if self.current.type != TokenType.RBRACE:
            while True:
                key = self.parse_expression()
                self._expect(
                    TokenType.COLON,
                    "Expected ':' after map key",
                    hint='Write a map entry as `"key": value`.',
                )
                value = self.parse_expression()
                entries.append((key, value))
                if self.current.type == TokenType.COMMA:
                    self._advance()
                    if self.current.type == TokenType.RBRACE:
                        break
                    continue
                break
        self._expect(
            TokenType.RBRACE,
            "Expected '}' after map entries",
            hint="Close the map with `}`, or separate entries with commas.",
        )
        return MapLiteral(entries=entries, span=lbrace_token.span)

    def parse_index(self, collection: Expression) -> IndexExpression:
        lbracket_token = self.current
        self._expect(
            TokenType.LBRACKET,
            "Expected '['",
            hint="Index a list as `values[index]`.",
        )
        if self.current.type == TokenType.RBRACKET:
            raise SwarnaSyntaxError(
                "List index is empty",
                self.current.span,
                hint="Put an Int index inside the brackets, for example `values[0]`.",
            )
        index = self.parse_expression()
        self._expect(
            TokenType.RBRACKET,
            "Expected ']' after index",
            hint="Close the index with `]`.",
        )
        return IndexExpression(collection=collection, index=index, span=lbracket_token.span)

    def parse_call(self, callee: Identifier) -> CallExpression:
        lparen_token = self.current
        self._expect(
            TokenType.LPAREN,
            "Expected '(' after function name",
            hint="Write a call as `name(arguments)`.",
        )
        arguments: list[Expression] = []
        if self.current.type != TokenType.RPAREN:
            while True:
                arguments.append(self.parse_expression())
                if self.current.type == TokenType.COMMA:
                    self._advance()
                    if self.current.type == TokenType.RPAREN:
                        break
                    continue
                break
        self._expect(
            TokenType.RPAREN,
            "Expected ')' after arguments",
            hint="Close the call with `)`.",
        )
        return CallExpression(
            callee=callee,
            arguments=arguments,
            span=callee.span if callee.span is not None else lparen_token.span,
        )
