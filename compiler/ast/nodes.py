from dataclasses import dataclass


@dataclass(frozen=True)
class Identifier:
    name: str


@dataclass(frozen=True)
class IntegerLiteral:
    value: int


@dataclass(frozen=True)
class LetStatement:
    name: Identifier
    value: IntegerLiteral
    mutable: bool = False


@dataclass(frozen=True)
class Program:
    statements: list[LetStatement]
