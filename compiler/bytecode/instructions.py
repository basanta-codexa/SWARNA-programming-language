from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from compiler.diagnostics import SourceSpan


class Op(Enum):
    CONST = auto()
    LOAD_NAME = auto()
    STORE_NAME = auto()
    DECLARE_NAME = auto()
    STORE_CONST = auto()
    DUP = auto()
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    IDIV = auto()
    NEG = auto()
    NOT = auto()
    BOOL = auto()
    EQ = auto()
    NEQ = auto()
    LT = auto()
    LTE = auto()
    GT = auto()
    GTE = auto()
    PRINT = auto()
    JUMP = auto()
    JUMP_IF_FALSE = auto()
    POP = auto()
    BUILD_LIST = auto()
    INDEX = auto()
    LEN = auto()
    ITER_START = auto()
    ITER_NEXT = auto()
    CALL = auto()
    RETURN = auto()
    HALT = auto()


@dataclass(frozen=True)
class Instruction:
    op: Op
    arg: Any = None
    span: SourceSpan | None = field(default=None, compare=False, repr=False)

    def __repr__(self) -> str:
        if self.arg is None:
            return f"{self.op.name}"
        return f"{self.op.name} {self.arg!r}"
