from enum import Enum, auto

from attr import dataclass

class TokenType(Enum):
    KEWORD_LET = auto()
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