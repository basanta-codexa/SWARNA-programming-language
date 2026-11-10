from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import NoReturn

from compiler.ast.nodes import (
    AssignmentStatement,
    BinaryExpression,
    BlockExpression,
    BlockStatement,
    BoolLiteral,
    CallExpression,
    Expression,
    FloatLiteral,
    FunctionDeclaration,
    Identifier,
    IfExpression,
    IfStatement,
    IntegerLiteral,
    LetStatement,
    PrintStatement,
    Program,
    Statement,
    StringLiteral,
    UnaryExpression,
    WhileStatement,
)
from compiler.diagnostics import SourceSpan, SwarnaSemanticError


class Type(Enum):
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    BOOL = auto()
    UNKNOWN = auto()

    @property
    def label(self) -> str:
        return self.name.title()


@dataclass(frozen=True)
class Binding:
    type: Type
    constant: bool = False
    span: SourceSpan | None = None


@dataclass(frozen=True)
class FunctionSignature:
    name: str
    parameters: tuple[Type, ...]
    return_type: Type | None
    span: SourceSpan | None = None


def type_of_value(value: object) -> Type:
    """Infer the static type of a value already held by the interpreter."""

    if type(value) is bool:
        return Type.BOOL
    if type(value) is int:
        return Type.INT
    if type(value) is float:
        return Type.FLOAT
    if type(value) is str:
        return Type.STRING
    return Type.UNKNOWN


class TypeChecker:
    """Infer types and reject the semantic errors the current language can express.

    This is deliberately a separate pass. The interpreter and VM keep their runtime
    checks so they can still be tested as reference implementations.
    """

    def __init__(
        self,
        initial_bindings: dict[str, Binding] | None = None,
        initial_functions: dict[str, FunctionSignature] | None = None,
    ):
        self.env: dict[str, Binding] = dict(initial_bindings or {})
        self.functions: dict[str, FunctionSignature] = dict(initial_functions or {})

    def check(self, program: Program) -> None:
        saved_env = dict(self.env)
        saved_functions = dict(self.functions)
        try:
            self._declare_functions(program)
            for stmt in program.statements:
                if isinstance(stmt, FunctionDeclaration):
                    continue
                self.check_statement(stmt)
            for stmt in program.statements:
                if isinstance(stmt, FunctionDeclaration):
                    self.check_function(stmt)
        except SwarnaSemanticError:
            self.env = saved_env
            self.functions = saved_functions
            raise

    def _declare_functions(self, program: Program) -> None:
        seen: set[str] = set()
        for stmt in program.statements:
            if not isinstance(stmt, FunctionDeclaration):
                continue
            name = stmt.name.name
            if name in seen:
                self._error(
                    f"Duplicate function '{name}'",
                    stmt.name.span,
                    "Give each function a unique name.",
                )
            seen.add(name)
            if name == "print":
                self._error(
                    "Function name 'print' is reserved",
                    stmt.name.span,
                    "Use a different function name.",
                )
            if name in self.env:
                self._error(
                    f"Cannot declare function '{name}' because a variable with that name exists",
                    stmt.name.span,
                    "Use a different name for the function.",
                )
            parameter_types: list[Type] = []
            parameter_names: set[str] = set()
            for parameter in stmt.parameters:
                parameter_name = parameter.name.name
                if parameter_name in parameter_names:
                    self._error(
                        f"Duplicate parameter '{parameter_name}' in function '{name}'",
                        parameter.name.span,
                        "Use a different name for each parameter.",
                    )
                parameter_names.add(parameter_name)
                parameter_types.append(self._resolve_type(parameter.type_name, Type.UNKNOWN))
            return_type = self._resolve_type(stmt.return_type, None)
            self.functions[name] = FunctionSignature(
                name=name,
                parameters=tuple(parameter_types),
                return_type=return_type,
                span=stmt.name.span,
            )

    def check_function(self, stmt: FunctionDeclaration) -> None:
        signature = self.functions[stmt.name.name]
        saved_env = self.env
        self.env = dict(self.env)
        try:
            for parameter, parameter_type in zip(stmt.parameters, signature.parameters):
                if parameter.name.name in self.functions:
                    self._error(
                        f"Parameter '{parameter.name.name}' conflicts with a function name",
                        parameter.name.span,
                        "Use a different parameter name.",
                    )
                self.env[parameter.name.name] = Binding(
                    parameter_type,
                    constant=False,
                    span=parameter.name.span,
                )
            body_type = self.check_expression(stmt.body)
            if signature.return_type is None:
                self.functions[stmt.name.name] = FunctionSignature(
                    name=signature.name,
                    parameters=signature.parameters,
                    return_type=body_type,
                    span=signature.span,
                )
            elif not self._is_assignable(signature.return_type, body_type):
                self._error(
                    f"Function '{stmt.name.name}' declares {signature.return_type.label} "
                    f"but its body produces {body_type.label}",
                    stmt.body.span if stmt.body.span is not None else stmt.span,
                    "Make the final expression match the declared return type.",
                )
        finally:
            self.env = saved_env

    def _resolve_type(self, type_name: Identifier | None, default: Type | None) -> Type | None:
        if type_name is None:
            return default
        types = {
            "Int": Type.INT,
            "Float": Type.FLOAT,
            "String": Type.STRING,
            "Bool": Type.BOOL,
        }
        resolved = types.get(type_name.name)
        if resolved is None:
            self._error(
                f"Unknown type '{type_name.name}'",
                type_name.span,
                "Use `Int`, `Float`, `String`, or `Bool`.",
            )
        return resolved

    def check_statement(self, stmt: Statement) -> None:
        if isinstance(stmt, FunctionDeclaration):
            self._error(
                "Function declarations are only allowed at the top level",
                stmt.span,
                "Move the function declaration outside the block.",
            )
        if isinstance(stmt, LetStatement):
            if stmt.name.name in self.functions:
                self._error(
                    f"Cannot bind a variable named '{stmt.name.name}' because a function with that name exists",
                    stmt.name.span,
                    "Use a different name for the binding.",
                )
            value_type = self.check_expression(stmt.value)
            self.env[stmt.name.name] = Binding(
                value_type,
                constant=stmt.constant,
                span=stmt.name.span,
            )
            return

        if isinstance(stmt, AssignmentStatement):
            name = stmt.name.name
            value_type = self.check_expression(stmt.value)
            binding = self.env.get(name)
            if binding is None:
                if name in self.functions:
                    self._error(
                        f"Cannot assign to function '{name}'",
                        stmt.name.span,
                        "Call the function and assign its result to a variable.",
                    )
                self._error(
                    f"Undefined name '{name}'",
                    stmt.name.span,
                    "Declare it first with `let name = value` or `const name = value`.",
                )
            if binding.constant:
                self._error(
                    f"Cannot assign to const binding '{name}'",
                    stmt.name.span,
                    "Change the binding to `let` if it needs to be reassigned.",
                )
            if not self._is_assignable(binding.type, value_type):
                self._error(
                    f"Cannot assign {value_type.label} to {binding.type.label} binding '{name}'",
                    stmt.value.span,
                    "A binding keeps the type of its first value.",
                )
            return

        if isinstance(stmt, PrintStatement):
            self.check_expression(stmt.value)
            return

        if isinstance(stmt, IfStatement):
            self._check_condition(stmt.condition, "`if` condition")
            self.check_block(stmt.then_branch)
            if stmt.else_branch is not None:
                self.check_block(stmt.else_branch)
            return

        if isinstance(stmt, WhileStatement):
            self._check_condition(stmt.condition, "`while` condition")
            self.check_block(stmt.body)
            return

        if isinstance(stmt, BlockStatement):
            self.check_block(stmt)
            return

        self._error(
            f"Unsupported statement: {type(stmt).__name__}",
            stmt.span,
            "This statement is not supported by the type checker yet.",
        )

    def check_block(self, block: BlockStatement) -> None:
        for stmt in block.statements:
            self.check_statement(stmt)

    def check_expression(self, expr: Expression) -> Type:
        if isinstance(expr, IntegerLiteral):
            return Type.INT
        if isinstance(expr, FloatLiteral):
            return Type.FLOAT
        if isinstance(expr, StringLiteral):
            return Type.STRING
        if isinstance(expr, BoolLiteral):
            return Type.BOOL

        if isinstance(expr, CallExpression):
            signature = self.functions.get(expr.callee.name)
            if signature is None:
                self._error(
                    f"Undefined function '{expr.callee.name}'",
                    expr.callee.span,
                    "Declare it first with `fn name(...) { ... }`.",
                )
            if len(expr.arguments) != len(signature.parameters):
                self._error(
                    f"Function '{signature.name}' expects {len(signature.parameters)} arguments, "
                    f"got {len(expr.arguments)}",
                    expr.span,
                    "Pass the number of arguments in the function declaration.",
                )
            for index, (argument, parameter_type) in enumerate(
                zip(expr.arguments, signature.parameters),
                start=1,
            ):
                argument_type = self.check_expression(argument)
                if not self._is_assignable(parameter_type, argument_type):
                    self._error(
                        f"Argument {index} of '{signature.name}' must be {parameter_type.label}, "
                        f"got {argument_type.label}",
                        argument.span,
                        "Pass a value of the declared parameter type.",
                    )
            return signature.return_type if signature.return_type is not None else Type.UNKNOWN

        if isinstance(expr, Identifier):
            binding = self.env.get(expr.name)
            if binding is None:
                if expr.name in self.functions:
                    self._error(
                        f"Function '{expr.name}' must be called",
                        expr.span,
                        "Add parentheses and arguments, or bind the result to a name.",
                    )
                self._error(
                    f"Undefined name '{expr.name}'",
                    expr.span,
                    "Declare it first with `let name = value` or `const name = value`.",
                )
            return binding.type

        if isinstance(expr, UnaryExpression):
            operand_type = self.check_expression(expr.operand)
            if expr.operator == "-":
                if operand_type is Type.UNKNOWN:
                    return Type.UNKNOWN
                if not self._is_numeric(operand_type):
                    self._error(
                        f"Unary `-` requires a number, got {operand_type.label}",
                        expr.span,
                        "Use an Int or Float operand.",
                    )
                return operand_type
            if expr.operator == "!":
                if not self._is_bool(operand_type):
                    self._error(
                        f"`!` requires a Bool operand, got {operand_type.label}",
                        expr.span,
                        "Use a comparison or a boolean value.",
                    )
                return Type.BOOL
            self._error(
                f"Unsupported unary operator {expr.operator!r}",
                expr.span,
                "This operator is not supported by the type checker yet.",
            )

        if isinstance(expr, BinaryExpression):
            return self._check_binary(expr)

        if isinstance(expr, BlockExpression):
            for stmt in expr.statements:
                self.check_statement(stmt)
            return self.check_expression(expr.value)

        if isinstance(expr, IfExpression):
            self._check_condition(expr.condition, "`if` condition")
            then_type = self.check_expression(expr.then_value)
            else_type = self.check_expression(expr.else_value)
            return self._common_type(then_type, else_type, expr)

        self._error(
            f"Unsupported expression: {type(expr).__name__}",
            expr.span,
            "This expression is not supported by the type checker yet.",
        )

    def _check_binary(self, expr: BinaryExpression) -> Type:
        if expr.operator in ("&&", "||"):
            left_type = self.check_expression(expr.left)
            right_type = self.check_expression(expr.right)
            if not self._is_bool(left_type):
                self._error(
                    f"`{expr.operator}` requires Bool operands, got {left_type.label}",
                    expr.left.span,
                    "Use comparisons or `true`/`false`.",
                )
            if not self._is_bool(right_type):
                self._error(
                    f"`{expr.operator}` requires Bool operands, got {right_type.label}",
                    expr.right.span,
                    "Use comparisons or `true`/`false`.",
                )
            return Type.BOOL

        left_type = self.check_expression(expr.left)
        right_type = self.check_expression(expr.right)
        if left_type is Type.UNKNOWN or right_type is Type.UNKNOWN:
            return Type.UNKNOWN

        if expr.operator == "+":
            if left_type is Type.STRING and right_type is Type.STRING:
                return Type.STRING
            if self._is_numeric(left_type) and self._is_numeric(right_type):
                return self._numeric_result(left_type, right_type)
            self._error(
                f"`+` cannot combine {left_type.label} and {right_type.label}",
                expr.span,
                "Use two numbers or two strings.",
            )

        if expr.operator in ("-", "*"):
            if self._is_numeric(left_type) and self._is_numeric(right_type):
                return self._numeric_result(left_type, right_type)
            self._error(
                f"`{expr.operator}` requires numeric operands, got {left_type.label} and {right_type.label}",
                expr.span,
                "Use Int or Float operands.",
            )

        if expr.operator == "/":
            if self._is_numeric(left_type) and self._is_numeric(right_type):
                return Type.FLOAT
            self._error(
                f"`/` requires numeric operands, got {left_type.label} and {right_type.label}",
                expr.span,
                "Use Int or Float operands.",
            )

        if expr.operator == "//":
            if left_type is not Type.INT or right_type is not Type.INT:
                self._error(
                    f"`//` requires Int operands, got {left_type.label} and {right_type.label}",
                    expr.span,
                    "Use `/` for true division or convert the operands to Int.",
                )
            return Type.INT

        if expr.operator in ("==", "!="):
            if not self._is_comparable(left_type, right_type):
                self._error(
                    f"`{expr.operator}` cannot compare {left_type.label} and {right_type.label}",
                    expr.span,
                    "Compare values of compatible types.",
                )
            return Type.BOOL

        if expr.operator in ("<", "<=", ">", ">="):
            if not self._is_ordered(left_type, right_type):
                self._error(
                    f"`{expr.operator}` cannot compare {left_type.label} and {right_type.label}",
                    expr.span,
                    "Compare two numbers or two strings.",
                )
            return Type.BOOL

        self._error(
            f"Unsupported binary operator {expr.operator!r}",
            expr.span,
            "This operator is not supported by the type checker yet.",
        )

    def _check_condition(self, expr: Expression, context: str) -> None:
        condition_type = self.check_expression(expr)
        if not self._is_bool(condition_type):
            self._error(
                f"{context} must be Bool, got {condition_type.label}",
                expr.span,
                "Use a comparison or a boolean value.",
            )

    def _common_type(self, then_type: Type, else_type: Type, expr: IfExpression) -> Type:
        if then_type is Type.UNKNOWN:
            return else_type
        if else_type is Type.UNKNOWN:
            return then_type
        if then_type is else_type:
            return then_type
        self._error(
            f"`if` branches have incompatible types: {then_type.label} and {else_type.label}",
            expr.else_value.span if expr.else_value.span is not None else expr.span,
            "Both branches must produce the same type.",
        )

    @staticmethod
    def _is_numeric(type: Type) -> bool:
        return type in (Type.INT, Type.FLOAT)

    @staticmethod
    def _is_bool(type: Type) -> bool:
        return type is Type.BOOL or type is Type.UNKNOWN

    @staticmethod
    def _numeric_result(left: Type, right: Type) -> Type:
        if left is Type.FLOAT or right is Type.FLOAT:
            return Type.FLOAT
        return Type.INT

    @staticmethod
    def _is_assignable(target: Type, value: Type) -> bool:
        if target is Type.UNKNOWN or value is Type.UNKNOWN:
            return True
        return target is value

    @staticmethod
    def _is_comparable(left: Type, right: Type) -> bool:
        if left is Type.UNKNOWN or right is Type.UNKNOWN:
            return True
        if left is right:
            return True
        return left in (Type.INT, Type.FLOAT) and right in (Type.INT, Type.FLOAT)

    @staticmethod
    def _is_ordered(left: Type, right: Type) -> bool:
        if left is Type.UNKNOWN or right is Type.UNKNOWN:
            return True
        if left is Type.STRING and right is Type.STRING:
            return True
        return left in (Type.INT, Type.FLOAT) and right in (Type.INT, Type.FLOAT)

    @staticmethod
    def _error(message: str, span: SourceSpan | None, hint: str | None = None) -> NoReturn:
        raise SwarnaSemanticError(message, span, hint)
