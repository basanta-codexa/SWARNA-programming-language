from compiler.lexer.tokens import Token, TokenType


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.position = 0
        self.line = 1
        self.column = 1
        self.current_char = source[0] if source else None

    def advance(self) -> None:
        if self.current_char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        self.position += 1
        if self.position < len(self.source):
            self.current_char = self.source[self.position]
        else:
            self.current_char = None

    def _skip_whitespace(self) -> None:
        while self.current_char is not None and self.current_char.isspace():
            self.advance()

    def _read_identifier(self) -> str:
        start = self.position
        while self.current_char is not None and (self.current_char.isalnum() or self.current_char == "_"):
            self.advance()
        return self.source[start:self.position]

    def _read_number(self) -> tuple[TokenType, str]:
        start = self.position
        while self.current_char is not None and self.current_char.isdigit():
            self.advance()
        if self.current_char == ".":
            nxt = self.position + 1
            if nxt < len(self.source) and self.source[nxt].isdigit():
                self.advance()  # consume '.'
                while self.current_char is not None and self.current_char.isdigit():
                    self.advance()
                return TokenType.FLOAT, self.source[start:self.position]
        return TokenType.INTEGER, self.source[start:self.position]

    def _read_string(self) -> str:
        self.advance()  # opening quote
        chars: list[str] = []
        while self.current_char is not None and self.current_char != '"':
            if self.current_char == "\\":
                self.advance()
                if self.current_char is None:
                    raise SyntaxError("Unterminated string literal")
                escapes = {'"': '"', "\\": "\\", "n": "\n", "t": "\t"}
                chars.append(escapes.get(self.current_char, self.current_char))
                self.advance()
            else:
                chars.append(self.current_char)
                self.advance()
        if self.current_char != '"':
            raise SyntaxError("Unterminated string literal")
        self.advance()  # closing quote
        return "".join(chars)

    def _peek(self) -> str | None:
        nxt = self.position + 1
        if nxt < len(self.source):
            return self.source[nxt]
        return None

    def next_token(self) -> Token:
        self._skip_whitespace()

        if self.current_char is None:
            return Token(TokenType.EOF, "", self.line, self.column)

        line, column = self.line, self.column
        ch = self.current_char

        if ch.isalpha() or ch == "_":
            value = self._read_identifier()
            if value == "let":
                return Token(TokenType.KEYWORD_LET, value, line, column)
            if value == "mut":
                return Token(TokenType.KEYWORD_MUT, value, line, column)
            if value == "true":
                return Token(TokenType.KEYWORD_TRUE, value, line, column)
            if value == "false":
                return Token(TokenType.KEYWORD_FALSE, value, line, column)
            return Token(TokenType.IDENTIFIER, value, line, column)

        if ch.isdigit():
            tok_type, value = self._read_number()
            return Token(tok_type, value, line, column)

        if ch == '"':
            value = self._read_string()
            return Token(TokenType.STRING, value, line, column)

        if ch == "=":
            self.advance()
            if self.current_char == "=":
                self.advance()
                return Token(TokenType.EQEQ, "==", line, column)
            return Token(TokenType.EQUAL, "=", line, column)
        if ch == "!":
            self.advance()
            if self.current_char == "=":
                self.advance()
                return Token(TokenType.BANGEQ, "!=", line, column)
            raise SyntaxError(f"Unexpected character '!' at line {line}, column {column}")
        if ch == "<":
            self.advance()
            if self.current_char == "=":
                self.advance()
                return Token(TokenType.LTEQ, "<=", line, column)
            return Token(TokenType.LT, "<", line, column)
        if ch == ">":
            self.advance()
            if self.current_char == "=":
                self.advance()
                return Token(TokenType.GTEQ, ">=", line, column)
            return Token(TokenType.GT, ">", line, column)

        single_char = {
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.STAR,
            "/": TokenType.SLASH,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
        }
        if ch in single_char:
            self.advance()
            return Token(single_char[ch], ch, line, column)

        raise SyntaxError(f"Unexpected character {ch!r} at line {line}, column {column}")

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while True:
            tok = self.next_token()
            tokens.append(tok)
            if tok.type == TokenType.EOF:
                break
        return tokens
