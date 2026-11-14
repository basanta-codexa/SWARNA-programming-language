from __future__ import annotations

from dataclasses import dataclass
from typing import NoReturn

from compiler.ast.nodes import (
    AssignmentStatement,
    BinaryExpression,
    BlockExpression,
    BlockStatement,
    BoolLiteral,
    BreakStatement,
    CallExpression,
    ContinueStatement,
    Expression,
    FloatLiteral,
    ForStatement,
    FunctionDeclaration,
    Identifier,
    IfExpression,
    IfStatement,
    IndexAssignmentStatement,
    IndexExpression,
    IntegerLiteral,
    LetStatement,
    ListLiteral,
    MapLiteral,
    PrintStatement,
    Program,
    Statement,
    StringLiteral,
    TypeAnnotation,
    UnaryExpression,
    WhileStatement,
)
from compiler.csv_schema import CsvSchemaError, parse_csv_schema
from compiler.diagnostics import SourceSpan, SwarnaSemanticError


@dataclass(frozen=True)
class Type:
    name: str
    arguments: tuple["Type", ...] = ()

    @property
    def label(self) -> str:
        if not self.arguments:
            return self.name
        return f"{self.name}[{', '.join(argument.label for argument in self.arguments)}]"

    @property
    def is_list(self) -> bool:
        return self.name == "List" and len(self.arguments) == 1

    @property
    def element_type(self) -> "Type":
        return self.arguments[0] if self.is_list else Type.UNKNOWN

    @property
    def is_map(self) -> bool:
        return self.name == "Map" and len(self.arguments) == 2

    @property
    def key_type(self) -> "Type":
        return self.arguments[0] if self.is_map else Type.UNKNOWN

    @property
    def value_type(self) -> "Type":
        return self.arguments[1] if self.is_map else Type.UNKNOWN

    @classmethod
    def list_of(cls, element: Type) -> "Type":
        return cls("List", (element,))

    @classmethod
    def map_of(cls, key: Type, value: Type) -> "Type":
        return cls("Map", (key, value))


# Scalar types stay as singleton class attributes so identity checks and the
# existing public Type.INT-style API remain stable.
Type.INT = Type("Int")
Type.FLOAT = Type("Float")
Type.STRING = Type("String")
Type.BOOL = Type("Bool")
Type.UNKNOWN = Type("Unknown")


BUILTIN_NAMES = frozenset({"print", "len", "get", "range", "read_file", "read_csv"})


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


def common_element_type(left: Type, right: Type) -> Type | None:
    """Unify two list element types without raising a diagnostic."""

    if left is Type.UNKNOWN:
        return right
    if right is Type.UNKNOWN:
        return left
    if left == right:
        return left
    if left.is_list and right.is_list:
        element_type = common_element_type(left.element_type, right.element_type)
        if element_type is None:
            return None
        return Type.list_of(element_type)
    if left.is_map and right.is_map:
        key_type = common_element_type(left.key_type, right.key_type)
        value_type = common_element_type(left.value_type, right.value_type)
        if key_type is None or value_type is None:
            return None
        return Type.map_of(key_type, value_type)
    return None


def is_scalar_type(type: Type) -> bool:
    """Return whether a type can be used as a map key.

    Keys must be hashable at runtime, so lists and maps are excluded.
    """

    return type is Type.INT or type is Type.FLOAT or type is Type.STRING or type is Type.BOOL


def type_from_annotation(annotation: TypeAnnotation) -> Type:
    """Convert a validated annotation to a type, without raising diagnostics."""

    scalars = {
        "Int": Type.INT,
        "Float": Type.FLOAT,
        "String": Type.STRING,
        "Bool": Type.BOOL,
    }
    scalar = scalars.get(annotation.name)
    if scalar is not None:
        return scalar
    if annotation.name == "List" and len(annotation.arguments) == 1:
        return Type.list_of(type_from_annotation(annotation.arguments[0]))
    if annotation.name == "Map" and len(annotation.arguments) == 2:
        return Type.map_of(
            type_from_annotation(annotation.arguments[0]),
            type_from_annotation(annotation.arguments[1]),
        )
    return Type.UNKNOWN


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
    if isinstance(value, list):
        element_type = Type.UNKNOWN
        for item in value:
            item_type = type_of_value(item)
            unified = common_element_type(element_type, item_type)
            if unified is None:
                return Type.list_of(Type.UNKNOWN)
            element_type = unified
        return Type.list_of(element_type)
    if isinstance(value, dict):
        key_type = Type.UNKNOWN
        value_type = Type.UNKNOWN
        for key, item in value.items():
            unified_key = common_element_type(key_type, type_of_value(key))
            unified_value = common_element_type(value_type, type_of_value(item))
            if unified_key is None or unified_value is None:
                return Type.map_of(Type.UNKNOWN, Type.UNKNOWN)
            key_type, value_type = unified_key, unified_value
        return Type.map_of(key_type, value_type)
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
        self.loop_depth = 0

    def check(self, program: Program) -> None:
        saved_env = dict(self.env)
        saved_functions = dict(self.functions)
        self.loop_depth = 0
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
            if name in BUILTIN_NAMES:
                self._error(
                    f"Function name '{name}' is reserved",
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
                if parameter.name.name in BUILTIN_NAMES:
                    self._error(
                        f"Parameter '{parameter.name.name}' conflicts with a built-in name",
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
                    category="type-mismatch",
                )
        finally:
            self.env = saved_env

    def _resolve_type(self, type_name: TypeAnnotation | None, default: Type | None) -> Type | None:
        if type_name is None:
            return default
        scalars = {
            "Int": Type.INT,
            "Float": Type.FLOAT,
            "String": Type.STRING,
            "Bool": Type.BOOL,
        }
        scalar = scalars.get(type_name.name)
        if scalar is not None:
            if type_name.arguments:
                self._error(
                    f"Type '{type_name.name}' does not take type arguments",
                    type_name.span,
                    "Use a scalar type such as `Int`.",
                )
            return scalar
        if type_name.name == "List":
            if len(type_name.arguments) != 1:
                self._error(
                    "List needs exactly one type argument",
                    type_name.span,
                    "Write `List[Int]`.",
                )
            return Type.list_of(self._resolve_type(type_name.arguments[0], None))
        if type_name.name == "Map":
            if len(type_name.arguments) != 2:
                self._error(
                    "Map needs exactly two type arguments",
                    type_name.span,
                    "Write `Map[String, Float]`.",
                )
            key_type = self._resolve_type(type_name.arguments[0], None)
            value_type = self._resolve_type(type_name.arguments[1], None)
            if not is_scalar_type(key_type):
                self._error(
                    f"Map keys must be Int, Float, String, or Bool, got {key_type.label}",
                    type_name.arguments[0].span,
                    "Use a scalar key type.",
                )
            return Type.map_of(key_type, value_type)
        self._error(
            f"Unknown type '{type_name.name}'",
            type_name.span,
            "Use `Int`, `Float`, `String`, `Bool`, `List[T]`, or `Map[K, V]`.",
        )

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
            if stmt.name.name in BUILTIN_NAMES:
                self._error(
                    f"Cannot bind a variable named '{stmt.name.name}' because it is reserved",
                    stmt.name.span,
                    "Use a different name for the binding.",
                )
            value_type = self.check_expression(stmt.value)
            binding_type = value_type
            if stmt.type_name is not None:
                declared_type = self._resolve_type(stmt.type_name, None)
                if not self._is_assignable(declared_type, value_type):
                    self._error(
                        f"Cannot assign {value_type.label} to {declared_type.label} "
                        f"binding '{stmt.name.name}'",
                        stmt.value.span,
                        "Make the value match the annotation.",
                        category="type-mismatch",
                    )
                binding_type = declared_type
            self.env[stmt.name.name] = Binding(
                binding_type,
                constant=stmt.constant,
                span=stmt.name.span,
            )
            return

        if isinstance(stmt, AssignmentStatement):
            name = stmt.name.name
            value_type = self.check_expression(stmt.value)
            if name in BUILTIN_NAMES:
                self._error(
                    f"Cannot assign to reserved name '{name}'",
                    stmt.name.span,
                    "Use a different name for the binding.",
                )
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
                    category="undefined-name",
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
                    category="type-mismatch",
                )
            return

        if isinstance(stmt, IndexAssignmentStatement):
            value_type = self.check_expression(stmt.value)
            root = self._index_root(stmt.target)
            if root is None:
                self._error(
                    "Index assignment must target a name",
                    stmt.target.span,
                    "Assign through a variable, as in `m[key] = value`.",
                )
                return
            name = root.name
            if name in BUILTIN_NAMES:
                self._error(
                    f"Cannot assign to reserved name '{name}'",
                    root.span,
                    "Use a different name for the binding.",
                )
            binding = self.env.get(name)
            if binding is None:
                if name in self.functions:
                    self._error(
                        f"Cannot assign to function '{name}'",
                        root.span,
                        "Call the function and assign its result to a variable.",
                    )
                self._error(
                    f"Undefined name '{name}'",
                    root.span,
                    "Declare it first with `let name = value` or `const name = value`.",
                    category="undefined-name",
                )
            if binding.constant:
                self._error(
                    f"Cannot assign to const binding '{name}'",
                    root.span,
                    "Change the binding to `let` if it needs to be reassigned.",
                )
            collection_type, _ = self._check_index_types(stmt.target)
            if collection_type is Type.UNKNOWN:
                return
            if collection_type.is_list:
                self._error(
                    "Lists are immutable; cannot assign to an index",
                    stmt.target.span,
                    "Build a new list with `+` instead.",
                )
            if not self._is_assignable(collection_type.value_type, value_type):
                self._error(
                    f"Cannot assign {value_type.label} to {collection_type.label}",
                    stmt.value.span,
                    f"Use a {collection_type.value_type.label} value.",
                    category="type-mismatch",
                )
            return

        if isinstance(stmt, BreakStatement):
            if self.loop_depth == 0:
                self._error(
                    "`break` is only allowed inside a loop",
                    stmt.span,
                    "Move it into a `while` or `for` body.",
                )
            return

        if isinstance(stmt, ContinueStatement):
            if self.loop_depth == 0:
                self._error(
                    "`continue` is only allowed inside a loop",
                    stmt.span,
                    "Move it into a `while` or `for` body.",
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
            self.loop_depth += 1
            try:
                self.check_block(stmt.body)
            finally:
                self.loop_depth -= 1
            return

        if isinstance(stmt, ForStatement):
            iterable_type = self.check_expression(stmt.iterable)
            if iterable_type is not Type.UNKNOWN and not (
                iterable_type.is_list or iterable_type.is_map
            ):
                self._error(
                    f"`for` expects a List or Map, got {iterable_type.label}",
                    stmt.iterable.span,
                    "Use a list or map after `in`.",
                )
            name = stmt.name.name
            if name in self.functions:
                self._error(
                    f"Loop variable '{name}' conflicts with a function name",
                    stmt.name.span,
                    "Use a different name for the loop variable.",
                )
            if name in BUILTIN_NAMES:
                self._error(
                    f"Loop variable '{name}' conflicts with a built-in name",
                    stmt.name.span,
                    "Use a different name for the loop variable.",
                )
            if iterable_type.is_list:
                element_type = iterable_type.element_type
            elif iterable_type.is_map:
                element_type = iterable_type.key_type
            else:
                element_type = Type.UNKNOWN
            previous = self.env.get(name)
            self.env[name] = Binding(element_type, constant=False, span=stmt.name.span)
            self.loop_depth += 1
            try:
                self.check_block(stmt.body)
            finally:
                self.loop_depth -= 1
                if previous is None:
                    self.env.pop(name, None)
                else:
                    self.env[name] = previous
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

        if isinstance(expr, ListLiteral):
            element_type = Type.UNKNOWN
            for element in expr.elements:
                current_type = self.check_expression(element)
                unified = common_element_type(element_type, current_type)
                if unified is None:
                    hint = "Use values of one type, or convert them explicitly."
                    if self._is_numeric(element_type) and self._is_numeric(current_type):
                        hint = "Write the whole list with decimal points for Float, or without them for Int."
                    self._error(
                        f"List elements must have the same type, got "
                        f"{element_type.label} and {current_type.label}",
                        element.span,
                        hint,
                    )
                element_type = unified
            return Type.list_of(element_type)

        if isinstance(expr, MapLiteral):
            key_type = Type.UNKNOWN
            value_type = Type.UNKNOWN
            for key, value in expr.entries:
                current_key = self.check_expression(key)
                current_value = self.check_expression(value)
                if current_key is not Type.UNKNOWN and not is_scalar_type(current_key):
                    self._error(
                        f"Map keys must be Int, Float, String, or Bool, "
                        f"got {current_key.label}",
                        key.span,
                        "Use a scalar key.",
                        category="type-mismatch",
                    )
                unified_key = common_element_type(key_type, current_key)
                if unified_key is None:
                    self._error(
                        f"Map keys must have the same type, got "
                        f"{key_type.label} and {current_key.label}",
                        key.span,
                        "Use keys of one type.",
                        category="type-mismatch",
                    )
                unified_value = common_element_type(value_type, current_value)
                if unified_value is None:
                    self._error(
                        f"Map values must have the same type, got "
                        f"{value_type.label} and {current_value.label}",
                        value.span,
                        "Use values of one type.",
                        category="type-mismatch",
                    )
                key_type, value_type = unified_key, unified_value
            return Type.map_of(key_type, value_type)

        if isinstance(expr, IndexExpression):
            return self._check_index(expr)

        if isinstance(expr, CallExpression):
            if expr.callee.name == "print":
                self._error(
                    "`print` is a statement, not an expression",
                    expr.span,
                    "Use `print(value)` on its own line.",
                )
            if expr.callee.name == "len":
                if len(expr.arguments) != 1:
                    self._error(
                        f"Function 'len' expects 1 argument, got {len(expr.arguments)}",
                        expr.span,
                        "Pass one list, map, or string to `len`.",
                    )
                argument_type = self.check_expression(expr.arguments[0])
                if argument_type is Type.UNKNOWN:
                    return Type.INT
                if not (
                    argument_type.is_list
                    or argument_type.is_map
                    or argument_type is Type.STRING
                ):
                    self._error(
                        f"`len` expects a List, Map, or String, got {argument_type.label}",
                        expr.arguments[0].span,
                        "Pass a list, map, or string to `len`.",
                    )
                return Type.INT
            if expr.callee.name == "get":
                if len(expr.arguments) != 3:
                    self._error(
                        f"Function 'get' expects 3 arguments, got {len(expr.arguments)}",
                        expr.span,
                        "Pass a map, a key, and a default value to `get`.",
                    )
                map_type = self.check_expression(expr.arguments[0])
                key_type = self.check_expression(expr.arguments[1])
                default_type = self.check_expression(expr.arguments[2])
                if map_type is Type.UNKNOWN:
                    return Type.UNKNOWN
                if not map_type.is_map:
                    self._error(
                        f"`get` expects a Map, got {map_type.label}",
                        expr.arguments[0].span,
                        "Pass a map as the first argument.",
                        category="type-mismatch",
                    )
                if key_type is not Type.UNKNOWN and not self._is_assignable(
                    map_type.key_type, key_type
                ):
                    self._error(
                        f"`get` key must be {map_type.key_type.label}, "
                        f"got {key_type.label}",
                        expr.arguments[1].span,
                        "Use a key of the map's key type.",
                        category="type-mismatch",
                    )
                if map_type.value_type is Type.UNKNOWN:
                    return default_type
                if default_type is not Type.UNKNOWN and not self._is_assignable(
                    map_type.value_type, default_type
                ):
                    self._error(
                        f"`get` default must be {map_type.value_type.label}, "
                        f"got {default_type.label}",
                        expr.arguments[2].span,
                        "Use a default of the map's value type.",
                        category="type-mismatch",
                    )
                return map_type.value_type
            if expr.callee.name == "range":
                arg_count = len(expr.arguments)
                if arg_count < 1 or arg_count > 3:
                    self._error(
                        f"Function 'range' expects 1 to 3 arguments, got {arg_count}",
                        expr.span,
                        "Use `range(stop)`, `range(start, stop)`, or `range(start, stop, step)`.",
                    )
                for index, argument in enumerate(expr.arguments, start=1):
                    argument_type = self.check_expression(argument)
                    if argument_type is not Type.UNKNOWN and argument_type is not Type.INT:
                        self._error(
                            f"Argument {index} of 'range' must be Int, got {argument_type.label}",
                            argument.span,
                            "Use Int values for range bounds and step.",
                            category="type-mismatch",
                        )
                return Type.list_of(Type.INT)
            if expr.callee.name == "read_file":
                if len(expr.arguments) != 1:
                    self._error(
                        f"Function 'read_file' expects 1 argument, got {len(expr.arguments)}",
                        expr.span,
                        "Pass one string file path to `read_file`.",
                    )
                argument_type = self.check_expression(expr.arguments[0])
                if argument_type is not Type.UNKNOWN and argument_type is not Type.STRING:
                    self._error(
                        f"`read_file` expects a String path, got {argument_type.label}",
                        expr.arguments[0].span,
                        "Pass a file path as a string.",
                        category="type-mismatch",
                    )
                return Type.STRING
            if expr.callee.name == "read_csv":
                if len(expr.arguments) != 2:
                    self._error(
                        f"Function 'read_csv' expects 2 arguments, got {len(expr.arguments)}",
                        expr.span,
                        "Pass a file path and a schema literal to `read_csv`.",
                    )
                path_type = self.check_expression(expr.arguments[0])
                if path_type is not Type.UNKNOWN and path_type is not Type.STRING:
                    self._error(
                        f"`read_csv` expects a String path, got {path_type.label}",
                        expr.arguments[0].span,
                        "Pass a file path as a string.",
                        category="type-mismatch",
                    )
                try:
                    parse_csv_schema(expr.arguments[1])
                except CsvSchemaError as error:
                    self._error(error.message, error.span, error.hint)
                return Type.list_of(Type.map_of(Type.STRING, Type.UNKNOWN))
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
                        category="type-mismatch",
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
                if expr.name in BUILTIN_NAMES:
                    self._error(
                        f"Built-in '{expr.name}' must be called",
                        expr.span,
                        "Add parentheses and arguments, or use a different name.",
                    )
                self._error(
                    f"Undefined name '{expr.name}'",
                    expr.span,
                    "Declare it first with `let name = value` or `const name = value`.",
                    category="undefined-name",
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

    def _check_index(self, expr: IndexExpression) -> Type:
        _, result_type = self._check_index_types(expr)
        return result_type

    def _check_index_types(self, expr: IndexExpression) -> tuple[Type, Type]:
        """Validate an index expression and return its collection and result types."""

        collection_type = self.check_expression(expr.collection)
        index_type = self.check_expression(expr.index)
        if collection_type is not Type.UNKNOWN and not (
            collection_type.is_list or collection_type.is_map
        ):
            self._error(
                f"Cannot index {collection_type.label}; only lists and maps can be indexed",
                expr.collection.span if expr.collection.span is not None else expr.span,
                "Use a list or map value before the brackets.",
            )
        if collection_type.is_map:
            if index_type is not Type.UNKNOWN and not self._is_assignable(
                collection_type.key_type, index_type
            ):
                self._error(
                    f"Map index must be {collection_type.key_type.label}, "
                    f"got {index_type.label}",
                    expr.index.span,
                    "Use a key of the map's key type.",
                    category="type-mismatch",
                )
            return collection_type, collection_type.value_type
        if collection_type is Type.UNKNOWN:
            if index_type is not Type.UNKNOWN and index_type is not Type.INT:
                self._error(
                    f"List index must be Int, got {index_type.label}",
                    expr.index.span,
                    "Use an Int index, such as `values[0]`.",
                )
            return collection_type, Type.UNKNOWN
        if index_type is not Type.UNKNOWN and index_type is not Type.INT:
            self._error(
                f"List index must be Int, got {index_type.label}",
                expr.index.span,
                "Use an Int index, such as `values[0]`.",
            )
        return collection_type, collection_type.element_type

    @staticmethod
    def _index_root(target: IndexExpression) -> Identifier | None:
        node: Expression = target.collection
        while isinstance(node, IndexExpression):
            node = node.collection
        if isinstance(node, Identifier):
            return node
        return None

    def _check_binary(self, expr: BinaryExpression) -> Type:
        if expr.operator in ("&&", "||"):
            left_type = self.check_expression(expr.left)
            right_type = self.check_expression(expr.right)
            if not self._is_bool(left_type):
                self._error(
                    f"`{expr.operator}` requires Bool operands, got {left_type.label}",
                    expr.left.span,
                    "Use comparisons or `true`/`false`.",
                    category="type-mismatch",
                )
            if not self._is_bool(right_type):
                self._error(
                    f"`{expr.operator}` requires Bool operands, got {right_type.label}",
                    expr.right.span,
                    "Use comparisons or `true`/`false`.",
                    category="type-mismatch",
                )
            return Type.BOOL

        left_type = self.check_expression(expr.left)
        right_type = self.check_expression(expr.right)
        if left_type is Type.UNKNOWN or right_type is Type.UNKNOWN:
            return Type.UNKNOWN

        if expr.operator == "+":
            if left_type.is_list and right_type.is_list:
                element_type = self._require_common_element_type(
                    left_type.element_type,
                    right_type.element_type,
                    expr.right.span,
                    "List concatenation",
                )
                return Type.list_of(element_type)
            if left_type is Type.STRING and right_type is Type.STRING:
                return Type.STRING
            if self._is_numeric(left_type) and self._is_numeric(right_type):
                return self._numeric_result(left_type, right_type)
            self._error(
                f"`+` cannot combine {left_type.label} and {right_type.label}",
                expr.span,
                "Use two numbers, two strings, or two lists.",
                category="type-mismatch",
            )

        if expr.operator in ("-", "*", "%"):
            if self._is_numeric(left_type) and self._is_numeric(right_type):
                return self._numeric_result(left_type, right_type)
            self._error(
                f"`{expr.operator}` requires numeric operands, got {left_type.label} and {right_type.label}",
                expr.span,
                "Use Int or Float operands.",
                category="type-mismatch",
            )

        if expr.operator == "/":
            if self._is_numeric(left_type) and self._is_numeric(right_type):
                return Type.FLOAT
            self._error(
                f"`/` requires numeric operands, got {left_type.label} and {right_type.label}",
                expr.span,
                "Use Int or Float operands.",
                category="type-mismatch",
            )

        if expr.operator == "//":
            if left_type is not Type.INT or right_type is not Type.INT:
                self._error(
                    f"`//` requires Int operands, got {left_type.label} and {right_type.label}",
                    expr.span,
                    "Use `/` for true division or convert the operands to Int.",
                    category="type-mismatch",
                )
            return Type.INT

        if expr.operator in ("==", "!="):
            if not self._is_comparable(left_type, right_type):
                self._error(
                    f"`{expr.operator}` cannot compare {left_type.label} and {right_type.label}",
                    expr.span,
                    "Compare values of compatible types.",
                    category="type-mismatch",
                )
            return Type.BOOL

        if expr.operator in ("<", "<=", ">", ">="):
            if not self._is_ordered(left_type, right_type):
                self._error(
                    f"`{expr.operator}` cannot compare {left_type.label} and {right_type.label}",
                    expr.span,
                    "Compare two numbers or two strings.",
                    category="type-mismatch",
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
        if then_type == else_type:
            return then_type
        if then_type.is_list and else_type.is_list:
            element_type = self._require_common_element_type(
                then_type.element_type,
                else_type.element_type,
                expr.else_value.span,
                "`if` branches",
            )
            return Type.list_of(element_type)
        if then_type.is_map and else_type.is_map:
            key_type = self._require_common_element_type(
                then_type.key_type,
                else_type.key_type,
                expr.else_value.span,
                "`if` branches",
            )
            value_type = self._require_common_element_type(
                then_type.value_type,
                else_type.value_type,
                expr.else_value.span,
                "`if` branches",
            )
            return Type.map_of(key_type, value_type)
        self._error(
            f"`if` branches have incompatible types: {then_type.label} and {else_type.label}",
            expr.else_value.span if expr.else_value.span is not None else expr.span,
            "Both branches must produce the same type.",
            category="type-mismatch",
        )

    def _require_common_element_type(
        self,
        left: Type,
        right: Type,
        span: SourceSpan | None,
        context: str,
    ) -> Type:
        unified = common_element_type(left, right)
        if unified is None:
            self._error(
                f"{context} cannot combine element types {left.label} and {right.label}",
                span,
                "Use list elements of the same type.",
                category="type-mismatch",
            )
        return unified

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
        if target == value:
            return True
        if target.is_list and value.is_list:
            return TypeChecker._is_assignable(target.element_type, value.element_type)
        if target.is_map and value.is_map:
            return TypeChecker._is_assignable(
                target.key_type, value.key_type
            ) and TypeChecker._is_assignable(target.value_type, value.value_type)
        return False

    @staticmethod
    def _is_comparable(left: Type, right: Type) -> bool:
        if left is Type.UNKNOWN or right is Type.UNKNOWN:
            return True
        if left == right:
            return True
        if left in (Type.INT, Type.FLOAT) and right in (Type.INT, Type.FLOAT):
            return True
        if left.is_list and right.is_list:
            return common_element_type(left.element_type, right.element_type) is not None
        if left.is_map and right.is_map:
            return (
                common_element_type(left.key_type, right.key_type) is not None
                and common_element_type(left.value_type, right.value_type) is not None
            )
        return False

    @staticmethod
    def _is_ordered(left: Type, right: Type) -> bool:
        if left is Type.UNKNOWN or right is Type.UNKNOWN:
            return True
        if left is Type.STRING and right is Type.STRING:
            return True
        return left in (Type.INT, Type.FLOAT) and right in (Type.INT, Type.FLOAT)

    @staticmethod
    def _error(
        message: str,
        span: SourceSpan | None,
        hint: str | None = None,
        explanation: str | None = None,
        category: str | None = None,
    ) -> NoReturn:
        raise SwarnaSemanticError(
            message,
            span,
            hint,
            explanation=explanation,
            category=category,
        )
