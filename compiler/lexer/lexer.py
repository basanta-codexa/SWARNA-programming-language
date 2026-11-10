from compiler.diagnostics import SourceSpan, SwarnaSyntaxError
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
        start_line, start_column = self.line, self.column
        self.advance()  # opening quote
        chars: list[str] = []
        while self.current_char is not None and self.current_char != '"':
            if self.current_char == "\\":
                self.advance()
                if self.current_char is None:
                    raise SwarnaSyntaxError(
                        "Unterminated string literal",
                        SourceSpan(start_line, start_column, 1),
                        hint='Add a closing double quote (") before the end of the line.',
                    )
                escapes = {'"': '"', "\\": "\\", "n": "\n", "t": "\t"}
                chars.append(escapes.get(self.current_char, self.current_char))
                self.advance()
            else:
                chars.append(self.current_char)
                self.advance()
        if self.current_char != '"':
            raise SwarnaSyntaxError(
                "Unterminated string literal",
                SourceSpan(start_line, start_column, 1),
                hint='Add a closing double quote (") before the end of the line.',
            )
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
            if value == "const":
                return Token(TokenType.KEYWORD_CONST, value, line, column)
            if value == "true":
                return Token(TokenType.KEYWORD_TRUE, value, line, column)
            if value == "false":
                return Token(TokenType.KEYWORD_FALSE, value, line, column)
            if value == "if":
                return Token(TokenType.KEYWORD_IF, value, line, column)
            if value == "else":
                return Token(TokenType.KEYWORD_ELSE, value, line, column)
            if value == "while":
                return Token(TokenType.KEYWORD_WHILE, value, line, column)
            if value == "fn":
                return Token(TokenType.KEYWORD_FN, value, line, column)
            if value == "and":
                return Token(TokenType.KEYWORD_AND, value, line, column)
            if value == "or":
                return Token(TokenType.KEYWORD_OR, value, line, column)
            if value == "not":
                return Token(TokenType.KEYWORD_NOT, value, line, column)
            return Token(TokenType.IDENTIFIER, value, line, column)

        if ch.isdigit():
            tok_type, value = self._read_number()
            return Token(tok_type, value, line, column)

        if ch == '"':
            start_position = self.position
            value = self._read_string()
            source_length = self.position - start_position
            return Token(TokenType.STRING, value, line, column, source_length=source_length)

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
            return Token(TokenType.BANG, "!", line, column)
        if ch == "&":
            self.advance()
            if self.current_char == "&":
                self.advance()
                return Token(TokenType.AMPAMP, "&&", line, column)
            raise SwarnaSyntaxError(
                "Unexpected character '&'",
                SourceSpan(line, column, 1),
                hint="Use '&&' for logical and, or remove the character.",
            )
        if ch == "|":
            self.advance()
            if self.current_char == "|":
                self.advance()
                return Token(TokenType.PIPEPIPE, "||", line, column)
            raise SwarnaSyntaxError(
                "Unexpected character '|'",
                SourceSpan(line, column, 1),
                hint="Use '||' for logical or, or remove the character.",
            )
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
        if ch == "/":
            self.advance()
            if self.current_char == "/":
                self.advance()
                return Token(TokenType.SLASHSLASH, "//", line, column)
            return Token(TokenType.SLASH, "/", line, column)
        if ch == "-":
            self.advance()
            if self.current_char == ">":
                self.advance()
                return Token(TokenType.ARROW, "->", line, column)
            return Token(TokenType.MINUS, "-", line, column)

        single_char = {
            "+": TokenType.PLUS,
            "*": TokenType.STAR,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            ";": TokenType.SEMICOLON,
            ":": TokenType.COLON,
            ",": TokenType.COMMA,
        }
        if ch in single_char:
            self.advance()
            return Token(single_char[ch], ch, line, column)

        raise SwarnaSyntaxError(
            f"Unexpected character {ch!r}",
            SourceSpan(line, column, 1),
            hint="Remove the character or check for a typo.",
        )

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while True:
            tok = self.next_token()
            tokens.append(tok)
            if tok.type == TokenType.EOF:
                break
        return tokens
