from __future__ import annotations

from dataclasses import dataclass, field

from compiler.diagnostics import SourceSpan


@dataclass(frozen=True)
class Identifier:
    name: str
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class IntegerLiteral:
    value: int
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class FloatLiteral:
    value: float
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class StringLiteral:
    value: str
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class BoolLiteral:
    value: bool
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class UnaryExpression:
    operator: str
    operand: "Expression"
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class BinaryExpression:
    left: "Expression"
    operator: str
    right: "Expression"
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class IfExpression:
    condition: "Expression"
    then_value: "Expression"
    else_value: "Expression"
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class BlockExpression:
    statements: list["Statement"]
    value: "Expression"
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class CallExpression:
    callee: Identifier
    arguments: list["Expression"]
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


Expression = IntegerLiteral | FloatLiteral | StringLiteral | BoolLiteral | BinaryExpression | IfExpression | BlockExpression | CallExpression | Identifier | UnaryExpression


@dataclass(frozen=True)
class LetStatement:
    name: Identifier
    value: Expression
    constant: bool = False
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class AssignmentStatement:
    name: Identifier
    value: Expression
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class PrintStatement:
    value: Expression
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class BlockStatement:
    statements: list["Statement"]
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class IfStatement:
    condition: Expression
    then_branch: BlockStatement
    else_branch: BlockStatement | None = None
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class WhileStatement:
    condition: Expression
    body: BlockStatement
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class Parameter:
    name: Identifier
    type_name: Identifier | None = None


@dataclass(frozen=True)
class FunctionDeclaration:
    name: Identifier
    parameters: list[Parameter]
    return_type: Identifier | None
    body: Expression
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


Statement = LetStatement | AssignmentStatement | PrintStatement | IfStatement | WhileStatement | BlockStatement | FunctionDeclaration


@dataclass(frozen=True)
class Program:
    statements: list[Statement]
    span: SourceSpan | None = field(default=None, compare=False, repr=False)
