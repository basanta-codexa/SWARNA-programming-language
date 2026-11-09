from dataclasses import dataclass, field
from enum import Enum, auto

from compiler.diagnostics import SourceSpan


class TokenType(Enum):
    KEYWORD_LET = auto()
    KEYWORD_CONST = auto()
    KEYWORD_TRUE = auto()
    KEYWORD_FALSE = auto()
    KEYWORD_IF = auto()
    KEYWORD_ELSE = auto()
    KEYWORD_WHILE = auto()
    KEYWORD_AND = auto()
    KEYWORD_OR = auto()
    KEYWORD_NOT = auto()
    IDENTIFIER = auto()
    EQUAL = auto()
    EQEQ = auto()
    BANG = auto()
    BANGEQ = auto()
    LT = auto()
    LTEQ = auto()
    GT = auto()
    GTEQ = auto()
    AMPAMP = auto()
    PIPEPIPE = auto()
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    SLASHSLASH = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    SEMICOLON = auto()
    EOF = auto()


@dataclass(frozen=True)
class Token:
    type: TokenType
    value: str
    line: int
    column: int
    source_length: int | None = field(default=None, compare=False, repr=False)

    @property
    def span(self) -> SourceSpan:
        length = self.source_length if self.source_length is not None else max(1, len(self.value))
        return SourceSpan(self.line, self.column, length)
