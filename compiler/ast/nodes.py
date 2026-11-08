from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Identifier:
    name: str


@dataclass(frozen=True)
class IntegerLiteral:
    value: int


@dataclass(frozen=True)
class BoolLiteral:
    value: bool


@dataclass(frozen=True)
class UnaryExpression:
    operator: str
    operand: "Expression"


@dataclass(frozen=True)
class BinaryExpression:
    left: "Expression"
    operator: str
    right: "Expression"


Expression = IntegerLiteral | BoolLiteral | BinaryExpression | Identifier | UnaryExpression


@dataclass(frozen=True)
class LetStatement:
    name: Identifier
    value: Expression
    mutable: bool = False


@dataclass(frozen=True)
class PrintStatement:
    value: Expression


@dataclass(frozen=True)
class BlockStatement:
    statements: list["Statement"]


@dataclass(frozen=True)
class IfStatement:
    condition: Expression
    then_branch: BlockStatement
    else_branch: BlockStatement | None = None


Statement = LetStatement | PrintStatement | IfStatement | BlockStatement


@dataclass(frozen=True)
class Program:
    statements: list[Statement]
