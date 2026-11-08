from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Identifier:
    name: str


@dataclass(frozen=True)
class IntegerLiteral:
    value: int


@dataclass(frozen=True)
class BinaryExpression:
    left: "Expression"
    operator: str
    right: "Expression"


Expression = IntegerLiteral | BinaryExpression | Identifier


@dataclass(frozen=True)
class LetStatement:
    name: Identifier
    value: Expression
    mutable: bool = False


@dataclass(frozen=True)
class Program:
    statements: list[LetStatement]
