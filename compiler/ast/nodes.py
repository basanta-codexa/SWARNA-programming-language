from __future__ import annotations

from dataclasses import dataclass, field

from compiler.diagnostics import SourceSpan


@dataclass(frozen=True)
class Identifier:
    name: str
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class TypeAnnotation:
    name: str
    arguments: list["TypeAnnotation"]
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


@dataclass(frozen=True)
class ListLiteral:
    elements: list["Expression"]
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class IndexExpression:
    collection: "Expression"
    index: "Expression"
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class MapLiteral:
    entries: list[tuple["Expression", "Expression"]]
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


Expression = IntegerLiteral | FloatLiteral | StringLiteral | BoolLiteral | BinaryExpression | IfExpression | BlockExpression | CallExpression | ListLiteral | IndexExpression | MapLiteral | Identifier | UnaryExpression


@dataclass(frozen=True)
class LetStatement:
    name: Identifier
    value: Expression
    constant: bool = False
    type_name: TypeAnnotation | None = None
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class AssignmentStatement:
    name: Identifier
    value: Expression
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class IndexAssignmentStatement:
    target: IndexExpression
    value: Expression
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class PrintStatement:
    value: Expression
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class BreakStatement:
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class ContinueStatement:
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class ReturnStatement:
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
class ForStatement:
    name: Identifier
    iterable: Expression
    body: BlockStatement
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class Parameter:
    name: Identifier
    type_name: TypeAnnotation | None = None


@dataclass(frozen=True)
class FunctionDeclaration:
    name: Identifier
    parameters: list[Parameter]
    return_type: TypeAnnotation | None
    body: Expression
    span: SourceSpan | None = field(default=None, compare=False, repr=False)


Statement = LetStatement | AssignmentStatement | IndexAssignmentStatement | PrintStatement | BreakStatement | ContinueStatement | ReturnStatement | IfStatement | WhileStatement | ForStatement | BlockStatement | FunctionDeclaration


@dataclass(frozen=True)
class Program:
    statements: list[Statement]
    span: SourceSpan | None = field(default=None, compare=False, repr=False)
