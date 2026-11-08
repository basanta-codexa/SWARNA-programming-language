from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    KEYWORD_LET = auto()
    KEYWORD_MUT = auto()
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
