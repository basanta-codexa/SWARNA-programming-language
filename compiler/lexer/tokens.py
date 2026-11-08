from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    KEYWORD_LET = auto()
    IDENTIFIER = auto()
    EQUAL = auto()
    INTEGER = auto()
    EOF = auto()


@dataclass(frozen=True)
class Token:
    type: TokenType
    value: str
    line: int
    column: int
