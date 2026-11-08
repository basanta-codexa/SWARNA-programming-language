from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    KEYWORD_LET = auto()
    KEYWORD_MUT = auto()
    KEYWORD_TRUE = auto()
    KEYWORD_FALSE = auto()
    IDENTIFIER = auto()
    EQUAL = auto()
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    LPAREN = auto()
    RPAREN = auto()
    EOF = auto()


@dataclass(frozen=True)
class Token:
    type: TokenType
    value: str
    line: int
    column: int
