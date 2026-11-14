from __future__ import annotations

import math
import sys
from dataclasses import dataclass

from compiler.ast.nodes import AssignmentStatement, BinaryExpression, BlockExpression, BlockStatement, BoolLiteral, BreakStatement, CallExpression, ContinueStatement, Expression, ExpressionStatement, FloatLiteral, ForStatement, FunctionDeclaration, Identifier, IfExpression, IfStatement, IndexAssignmentStatement, IndexExpression, IntegerLiteral, LetStatement, ListLiteral, MapLiteral, PrintStatement, Program, ReturnStatement, Statement, StringLiteral, ThrowStatement, TryCatchStatement, TypeAnnotation, UnaryExpression, UnitLiteral, WhileStatement
from compiler.csv_schema import CsvSchemaError, parse_csv_schema
from compiler.diagnostics import SourceSpan, SwarnaNameError, SwarnaRuntimeError, SwarnaTypeError, SwarnaZeroDivisionError
from runtime.csv import read_csv_data
from runtime.files import read_text_file
from runtime.values import UNIT, Value, format_literal, format_value, value_type_name


class _LoopSignal(BaseException):
    """Control-flow signal for `break` and `continue`.

    This derives from BaseException so a broad `except Exception` in the
    runtime cannot swallow it, and so it is not reported as an error.
    """


class _LoopBreak(_LoopSignal):
    pass


class _LoopContinue(_LoopSignal):
    pass


class _ReturnSignal(BaseException):
    def __init__(self, value: Value):
        self.value = value
        super().__init__("return")


@dataclass(frozen=True)
class Function:
    name: str
    parameters: tuple[str, ...]
    body: Expression
    span: SourceSpan | None = None
    parameter_annotations: tuple[TypeAnnotation | None, ...] = ()
    return_annotation: TypeAnnotation | None = None


class Interpreter:
    def __init__(self) -> None:
        self.global_env: dict[str, Value] = {}
        self.global_constant: dict[str, bool] = {}
        self.env: dict[str, Value] = self.global_env
        self.constant: dict[str, bool] = self.global_constant
        self.functions: dict[str, Function] = {}
        self.output: list[Value] = []
        self.call_depth = 0
        self.max_call_depth = 200

    def eval(self, program: Program) -> dict[str, Value]:
        self.env = self.global_env
        self.constant = self.global_constant
        seen: set[str] = set()
        for stmt in program.statements:
            if not isinstance(stmt, FunctionDeclaration):
                continue
            name = stmt.name.name
            if name in seen:
                raise SwarnaRuntimeError(
                    f"Function '{name}' is declared more than once",
                    stmt.name.span,
                    hint="Give each function a unique name.",
                )
            seen.add(name)
            parameter_names = tuple(parameter.name.name for parameter in stmt.parameters)
            if len(set(parameter_names)) != len(parameter_names):
                seen_parameters: set[str] = set()
                duplicate_parameter = stmt.parameters[0]
                for parameter in stmt.parameters:
                    if parameter.name.name in seen_parameters:
                        duplicate_parameter = parameter
                        break
                    seen_parameters.add(parameter.name.name)
                raise SwarnaRuntimeError(
                    f"Duplicate parameter '{duplicate_parameter.name.name}' in function '{name}'",
                    duplicate_parameter.name.span,
                    hint="Use a different name for each parameter.",
                )
            self.functions[name] = Function(
                name=name,
                parameters=parameter_names,
                body=stmt.body,
                span=stmt.span,
                parameter_annotations=tuple(
                    parameter.type_name for parameter in stmt.parameters
                ),
                return_annotation=stmt.return_type,
            )
        for stmt in program.statements:
            if isinstance(stmt, FunctionDeclaration):
                continue
            self.eval_statement(stmt)
        return dict(self.env)

    def eval_statement(self, stmt: Statement) -> None:
        if isinstance(stmt, FunctionDeclaration):
            raise SwarnaRuntimeError(
                "Function declarations are only allowed at the top level",
                stmt.span,
                hint="Move the function declaration outside the block.",
            )
        if isinstance(stmt, LetStatement):
            name = stmt.name.name
            value = self.eval_expression(stmt.value)
            if stmt.type_name is not None and stmt.type_name.name == "Float" and type(value) is int and not stmt.type_name.arguments:
                value = float(value)
            self.env[name] = value
            self.constant[name] = stmt.constant
            return
        if isinstance(stmt, AssignmentStatement):
            name = stmt.name.name
            value = self.eval_expression(stmt.value)
            if name not in self.env:
                if name in self.functions:
                    raise SwarnaNameError(
                        f"Cannot assign to function '{name}'",
                        stmt.name.span,
                        hint="Call the function and assign its result to a variable.",
                    )
                raise SwarnaNameError(
                    f"Undefined name '{name}'",
                    stmt.name.span,
                    hint="Declare it first with `let name = value` or `const name = value`.",
                    category="undefined-name",
                )
            if self.constant.get(name, False):
                raise SwarnaRuntimeError(
                    f"Cannot assign to const binding '{name}'",
                    stmt.name.span,
                    hint="Change the binding to `let` if it needs to be reassigned.",
                )
            self.env[name] = value
            return
        if isinstance(stmt, IndexAssignmentStatement):
            root = self._index_root(stmt.target)
            if root is None:
                raise SwarnaTypeError(
                    "Index assignment must target a name",
                    stmt.target.span,
                    hint="Assign through a variable, as in `m[key] = value`.",
                )
            name = root.name
            if name in self.functions:
                raise SwarnaNameError(
                    f"Cannot assign to function '{name}'",
                    root.span,
                    hint="Call the function and assign its result to a variable.",
                )
            if name not in self.env:
                raise SwarnaNameError(
                    f"Undefined name '{name}'",
                    root.span,
                    hint="Declare it first with `let name = value` or `const name = value`.",
                    category="undefined-name",
                )
            if self.constant.get(name, False):
                raise SwarnaRuntimeError(
                    f"Cannot assign to const binding '{name}'",
                    root.span,
                    hint="Change the binding to `let` if it needs to be reassigned.",
                )
            collection = self.eval_expression(stmt.target.collection)
            index = self.eval_expression(stmt.target.index)
            value = self.eval_expression(stmt.value)
            if isinstance(collection, list):
                raise SwarnaTypeError(
                    "Lists are immutable; cannot assign to an index",
                    stmt.target.span,
                    hint="Build a new list with `+` instead.",
                )
            if not isinstance(collection, dict):
                raise SwarnaTypeError(
                    f"Cannot assign to {value_type_name(collection)}",
                    stmt.target.span,
                    hint="Only maps support index assignment.",
                )
            try:
                hash(index)
            except TypeError:
                raise SwarnaTypeError(
                    f"Map keys must be Int, Float, String, or Bool, "
                    f"got {value_type_name(index)}",
                    stmt.target.index.span,
                    hint="Use a scalar key.",
                ) from None
            collection[index] = value
            return
        if isinstance(stmt, BreakStatement):
            raise _LoopBreak()
        if isinstance(stmt, ContinueStatement):
            raise _LoopContinue()
        if isinstance(stmt, ReturnStatement):
            raise _ReturnSignal(self.eval_expression(stmt.value))
        if isinstance(stmt, ThrowStatement):
            value = self.eval_expression(stmt.value)
            if type(value) is not str:
                raise SwarnaTypeError(
                    f"`throw` expects a String message, got {value_type_name(value)}",
                    stmt.value.span if stmt.value.span is not None else stmt.span,
                    hint='Throw a string message, for example `throw "something went wrong"`.'
                )
            raise SwarnaRuntimeError(value, stmt.span)
        if isinstance(stmt, TryCatchStatement):
            try:
                self.eval_block(stmt.try_block)
            except SwarnaRuntimeError as error:
                saved_env = self.env
                saved_constant = self.constant
                self.env = dict(self.env)
                self.constant = dict(self.constant)
                self.env[stmt.catch_name.name] = error.message
                self.constant[stmt.catch_name.name] = False
                try:
                    self.eval_block(stmt.catch_block)
                finally:
                    self.env = saved_env
                    self.constant = saved_constant
            return
        if isinstance(stmt, ExpressionStatement):
            self.eval_expression(stmt.expression)
            return
        if isinstance(stmt, PrintStatement):
            self.output.append(self.eval_expression(stmt.value))
            return
        if isinstance(stmt, IfStatement):
            if bool(self.eval_expression(stmt.condition)):
                self.eval_block(stmt.then_branch)
            elif stmt.else_branch is not None:
                self.eval_block(stmt.else_branch)
            return
        if isinstance(stmt, WhileStatement):
            while bool(self.eval_expression(stmt.condition)):
                try:
                    self.eval_block(stmt.body)
                except _LoopContinue:
                    continue
                except _LoopBreak:
                    break
            return
        if isinstance(stmt, ForStatement):
            iterable = self.eval_expression(stmt.iterable)
            if not isinstance(iterable, (list, dict, str)):
                raise SwarnaTypeError(
                    f"`for` expects a List, Map, or String, got {value_type_name(iterable)}",
                    stmt.iterable.span,
                    hint="Use a list, map, or string after `in`.",
                )
            name = stmt.name.name
            had_previous = name in self.env
            previous_value = self.env.get(name)
            previous_constant = self.constant.get(name, False)
            try:
                for item in iterable:
                    self.env[name] = item
                    self.constant[name] = False
                    try:
                        self.eval_block(stmt.body)
                    except _LoopContinue:
                        continue
                    except _LoopBreak:
                        break
            finally:
                if had_previous:
                    self.env[name] = previous_value
                    self.constant[name] = previous_constant
                else:
                    self.env.pop(name, None)
                    self.constant.pop(name, None)
            return
        if isinstance(stmt, BlockStatement):
            self.eval_block(stmt)
            return
        raise SwarnaRuntimeError(
            f"Unsupported statement: {type(stmt).__name__}",
            stmt.span,
            hint="This statement is not supported by the interpreter yet.",
        )

    @staticmethod
    def _index_root(target: IndexExpression) -> Identifier | None:
        node: Expression = target.collection
        while isinstance(node, IndexExpression):
            node = node.collection
        if isinstance(node, Identifier):
            return node
        return None

    def eval_block(self, block: BlockStatement) -> None:
        for stmt in block.statements:
            self.eval_statement(stmt)

    def eval_block_expression(self, block: BlockExpression) -> Value:
        for stmt in block.statements:
            self.eval_statement(stmt)
        return self.eval_expression(block.value)

    def eval_call(self, expr: CallExpression) -> Value:
        if expr.callee.name == "len":
            if len(expr.arguments) != 1:
                raise SwarnaRuntimeError(
                    f"Function 'len' expects 1 argument, got {len(expr.arguments)}",
                    expr.span,
                    hint="Pass one list, map, or string to `len`.",
                )
            value = self.eval_expression(expr.arguments[0])
            if isinstance(value, (list, dict, str)):
                return len(value)
            raise SwarnaTypeError(
                f"`len` expects a List, Map, or String, got {value_type_name(value)}",
                expr.arguments[0].span,
                hint="Pass a list, map, or string to `len`.",
            )
        if expr.callee.name == "get":
            if len(expr.arguments) != 3:
                raise SwarnaRuntimeError(
                    f"Function 'get' expects 3 arguments, got {len(expr.arguments)}",
                    expr.span,
                    hint="Pass a map, a key, and a default value to `get`.",
                )
            collection = self.eval_expression(expr.arguments[0])
            key = self.eval_expression(expr.arguments[1])
            default = self.eval_expression(expr.arguments[2])
            if not isinstance(collection, dict):
                raise SwarnaTypeError(
                    f"`get` expects a Map, got {value_type_name(collection)}",
                    expr.arguments[0].span,
                    hint="Pass a map as the first argument.",
                )
            try:
                if key in collection:
                    return collection[key]
            except TypeError:
                raise SwarnaTypeError(
                    f"Map keys must be Int, Float, String, or Bool, "
                    f"got {value_type_name(key)}",
                    expr.arguments[1].span,
                    hint="Use a scalar key.",
                ) from None
            return default
        if expr.callee.name == "range":
            arg_count = len(expr.arguments)
            if arg_count < 1 or arg_count > 3:
                raise SwarnaRuntimeError(
                    f"Function 'range' expects 1 to 3 arguments, got {arg_count}",
                    expr.span,
                    hint="Use `range(stop)`, `range(start, stop)`, or `range(start, stop, step)`.",
                )
            values = [self.eval_expression(argument) for argument in expr.arguments]
            for index, value in enumerate(values):
                if type(value) is not int:
                    raise SwarnaTypeError(
                        f"`range` arguments must be Int, got {value_type_name(value)}",
                        expr.arguments[index].span,
                        hint="Use Int values for range bounds and step.",
                        category="type-mismatch",
                    )
            if arg_count == 1:
                start, stop, step = 0, values[0], 1
            elif arg_count == 2:
                start, stop, step = values[0], values[1], 1
            else:
                start, stop, step = values[0], values[1], values[2]
            if step == 0:
                raise SwarnaRuntimeError(
                    "`range` step must not be 0",
                    expr.arguments[2].span if arg_count == 3 else expr.span,
                    hint="Use a non-zero step, such as `1` or `-1`.",
                )
            return list(range(start, stop, step))
        if expr.callee.name == "input":
            if len(expr.arguments) != 0:
                raise SwarnaRuntimeError(
                    f"Function 'input' expects 0 arguments, got {len(expr.arguments)}",
                    expr.span,
                    hint="Call `input()` with no arguments to read a line from stdin.",
                )
            line = sys.stdin.readline()
            if line == "":
                raise SwarnaRuntimeError(
                    "No input available",
                    expr.span,
                    hint="Provide input on stdin when using `input()`.",
                )
            return line.rstrip("\r\n")
        if expr.callee.name == "int":
            if len(expr.arguments) != 1:
                raise SwarnaRuntimeError(
                    f"Function 'int' expects 1 argument, got {len(expr.arguments)}",
                    expr.span,
                    hint="Pass one value to convert to Int, for example `int(\"42\")` or `int(3.9)`.",
                )
            value = self.eval_expression(expr.arguments[0])
            if type(value) is bool:
                return 1 if value else 0
            if type(value) is int:
                return value
            if type(value) is float:
                if not math.isfinite(value):
                    raise SwarnaRuntimeError(
                        f"Cannot convert non-finite Float {format_literal(value)} to Int",
                        expr.arguments[0].span,
                        hint="Convert only finite Float values to Int.",
                        category="type-mismatch",
                    )
                return int(value)
            if type(value) is str:
                text = value.strip()
                try:
                    return int(text)
                except ValueError:
                    raise SwarnaRuntimeError(
                        f"Cannot convert String {format_literal(value)} to Int",
                        expr.arguments[0].span,
                        hint='Use an explicit whole-number string such as "42" (decimal integer form).',
                        category="type-mismatch",
                    ) from None
            raise SwarnaTypeError(
                f"Cannot convert {value_type_name(value)} to Int",
                expr.arguments[0].span,
                hint="Use `int(...)` with an Int, Float, Bool, or whole-number String.",
                category="type-mismatch",
            )
        if expr.callee.name == "float":
            if len(expr.arguments) != 1:
                raise SwarnaRuntimeError(
                    f"Function 'float' expects 1 argument, got {len(expr.arguments)}",
                    expr.span,
                    hint="Pass one value to convert to Float, for example `float(\"3.14\")` or `float(1)`.",
                )
            value = self.eval_expression(expr.arguments[0])
            if type(value) is bool:
                return 1.0 if value else 0.0
            if type(value) is int:
                result = float(value)
            elif type(value) is float:
                result = value
            elif type(value) is str:
                text = value.strip()
                try:
                    result = float(text)
                except ValueError:
                    raise SwarnaRuntimeError(
                        f"Cannot convert String {format_literal(value)} to Float",
                        expr.arguments[0].span,
                        hint='Use a finite numeric string such as "3.14" or "1e3", or convert explicitly with the appropriate form.',
                        category="type-mismatch",
                    ) from None
            else:
                raise SwarnaTypeError(
                    f"Cannot convert {value_type_name(value)} to Float",
                    expr.arguments[0].span,
                    hint="Use `float(...)` with an Int, Float, Bool, or numeric String.",
                    category="type-mismatch",
                )
            if not math.isfinite(result):
                raise SwarnaRuntimeError(
                    f"Cannot convert {value_type_name(value)} {format_literal(value)} to a finite Float",
                    expr.arguments[0].span,
                    hint="SWARNA `Float` values must be finite. Use a finite numeric value.",
                    category="type-mismatch",
                )
            return result
        if expr.callee.name == "str":
            if len(expr.arguments) != 1:
                raise SwarnaRuntimeError(
                    f"Function 'str' expects 1 argument, got {len(expr.arguments)}",
                    expr.span,
                    hint="Pass one value to convert to String.",
                )
            value = self.eval_expression(expr.arguments[0])
            return format_value(value)
        if expr.callee.name == "read_file":
            if len(expr.arguments) != 1:
                raise SwarnaRuntimeError(
                    f"Function 'read_file' expects 1 argument, got {len(expr.arguments)}",
                    expr.span,
                    hint="Pass one string file path to `read_file`.",
                )
            path = self.eval_expression(expr.arguments[0])
            if type(path) is not str:
                raise SwarnaTypeError(
                    f"`read_file` expects a String path, got {value_type_name(path)}",
                    expr.arguments[0].span,
                    hint='Pass a file path as a string, such as `read_file("notes.txt")`.',
                )
            return read_text_file(path, expr.arguments[0].span)
        if expr.callee.name == "read_csv":
            if len(expr.arguments) != 2:
                raise SwarnaRuntimeError(
                    f"Function 'read_csv' expects 2 arguments, got {len(expr.arguments)}",
                    expr.span,
                    hint="Pass a file path and a schema literal to `read_csv`.",
                )
            path = self.eval_expression(expr.arguments[0])
            if type(path) is not str:
                raise SwarnaTypeError(
                    f"`read_csv` expects a String path, got {value_type_name(path)}",
                    expr.arguments[0].span,
                    hint='Pass a file path as a string, such as `read_csv("scores.csv", ...)`.',
                )
            try:
                columns = parse_csv_schema(expr.arguments[1])
            except CsvSchemaError as error:
                raise SwarnaRuntimeError(
                    error.message,
                    error.span,
                    hint=error.hint,
                ) from None
            text = read_text_file(path, expr.arguments[0].span)
            schema = tuple((column.name, column.type_name) for column in columns)
            return read_csv_data(text, path, schema)
        function = self.functions.get(expr.callee.name)
        if function is None:
            raise SwarnaNameError(
                f"Undefined function '{expr.callee.name}'",
                expr.callee.span,
                hint="Declare it first with `fn name(...) { ... }`.",
            )
        if len(expr.arguments) != len(function.parameters):
            raise SwarnaRuntimeError(
                f"Function '{function.name}' expects {len(function.parameters)} arguments, got {len(expr.arguments)}",
                expr.span,
                hint="Pass the number of arguments in the function declaration.",
            )
        arguments = [self.eval_expression(argument) for argument in expr.arguments]
        coerced_arguments = []
        for index, (arg, param_ann) in enumerate(zip(arguments, function.parameter_annotations), start=1):
            if param_ann is not None and param_ann.name == "Float" and not param_ann.arguments and type(arg) is int:
                coerced_arguments.append(float(arg))
            else:
                coerced_arguments.append(arg)
        arguments = coerced_arguments
        if self.call_depth >= self.max_call_depth:
            raise SwarnaRuntimeError(
                f"Maximum call depth of {self.max_call_depth} exceeded",
                expr.span,
                hint="Check for infinite recursion.",
            )
        saved_env = self.env
        saved_constant = self.constant
        local_env = dict(self.global_env)
        local_constant = dict(self.global_constant)
        for parameter, value in zip(function.parameters, arguments):
            local_env[parameter] = value
            local_constant[parameter] = False
        self.env = local_env
        self.constant = local_constant
        self.call_depth += 1
        try:
            try:
                result = self.eval_expression(function.body)
            except _ReturnSignal as signal:
                result = signal.value
            ret_ann = function.return_annotation
            if ret_ann is not None and ret_ann.name == "Float" and not ret_ann.arguments and type(result) is int:
                result = float(result)
            return result
        finally:
            self.call_depth -= 1
            self.env = saved_env
            self.constant = saved_constant

    def eval_expression(self, expr: Expression) -> Value:
        if isinstance(expr, IntegerLiteral):
            return expr.value
        if isinstance(expr, FloatLiteral):
            return expr.value
        if isinstance(expr, StringLiteral):
            return expr.value
        if isinstance(expr, BoolLiteral):
            return expr.value
        if isinstance(expr, UnitLiteral):
            return UNIT
        if isinstance(expr, BlockExpression):
            return self.eval_block_expression(expr)
        if isinstance(expr, IfExpression):
            if bool(self.eval_expression(expr.condition)):
                return self.eval_expression(expr.then_value)
            return self.eval_expression(expr.else_value)
        if isinstance(expr, ListLiteral):
            return [self.eval_expression(element) for element in expr.elements]
        if isinstance(expr, MapLiteral):
            result: dict[Value, Value] = {}
            for key_expr, value_expr in expr.entries:
                key = self.eval_expression(key_expr)
                try:
                    hash(key)
                except TypeError:
                    raise SwarnaTypeError(
                        f"Map keys must be Int, Float, String, or Bool, "
                        f"got {value_type_name(key)}",
                        key_expr.span,
                        hint="Use a scalar key.",
                    ) from None
                result[key] = self.eval_expression(value_expr)
            return result
        if isinstance(expr, IndexExpression):
            collection = self.eval_expression(expr.collection)
            index = self.eval_expression(expr.index)
            if isinstance(collection, dict):
                try:
                    return collection[index]
                except KeyError:
                    raise SwarnaRuntimeError(
                        f"Key {format_literal(index)} is not in the map",
                        expr.index.span,
                        hint="Check the key, or use a key that exists.",
                    ) from None
                except TypeError:
                    raise SwarnaTypeError(
                        "Map keys must be scalar values",
                        expr.index.span,
                        hint="Use an Int, Float, String, or Bool key.",
                    ) from None
            if isinstance(collection, str):
                if type(index) is not int:
                    raise SwarnaTypeError(
                        "String index must be Int",
                        expr.index.span,
                        hint="Use an integer index, such as `text[0]`.",
                    )
                try:
                    return collection[index]
                except IndexError:
                    raise SwarnaRuntimeError(
                        f"Index {index} is out of range for a string of length {len(collection)}",
                        expr.index.span,
                        hint="Use an index from 0 to len(text) - 1, or a negative index from -len(text) to -1.",
                    ) from None
            if not isinstance(collection, list):
                raise SwarnaTypeError(
                    f"Cannot index {value_type_name(collection)}",
                    expr.span,
                    hint="Only lists, maps, and strings can be indexed.",
                )
            if type(index) is not int:
                raise SwarnaTypeError(
                    "List index must be Int",
                    expr.index.span,
                    hint="Use an integer index, such as `values[0]`.",
                )
            try:
                return collection[index]
            except IndexError:
                raise SwarnaRuntimeError(
                    f"Index {index} is out of range for a list of length {len(collection)}",
                    expr.index.span,
                    hint="Use an index from 0 to len(list) - 1, or a negative index from -len(list) to -1.",
                ) from None
        if isinstance(expr, CallExpression):
            return self.eval_call(expr)
        if isinstance(expr, Identifier):
            if expr.name not in self.env:
                if expr.name in self.functions:
                    raise SwarnaNameError(
                        f"Function '{expr.name}' must be called",
                        expr.span,
                        hint="Add parentheses and arguments, or bind the result to a name.",
                    )
                raise SwarnaNameError(
                    f"Undefined name '{expr.name}'",
                    expr.span,
                    hint="Declare it first with `let name = value` or `const name = value`.",
                    category="undefined-name",
                )
            return self.env[expr.name]
        if isinstance(expr, UnaryExpression):
            value = self.eval_expression(expr.operand)
            if expr.operator == "-":
                try:
                    return -value
                except TypeError as e:
                    raise SwarnaTypeError(
                        str(e),
                        expr.span,
                        hint="Unary `-` requires a number.",
                    ) from e
            if expr.operator == "!":
                return not bool(value)
            raise SwarnaRuntimeError(
                f"Unsupported unary operator {expr.operator!r}",
                expr.span,
                hint="This operator is not implemented yet.",
            )
        if isinstance(expr, BinaryExpression):
            if expr.operator == "&&":
                left = self.eval_expression(expr.left)
                return bool(self.eval_expression(expr.right)) if bool(left) else False
            if expr.operator == "||":
                left = self.eval_expression(expr.left)
                return True if bool(left) else bool(self.eval_expression(expr.right))
            left = self.eval_expression(expr.left)
            right = self.eval_expression(expr.right)
            if expr.operator == "/" and right == 0:
                raise SwarnaZeroDivisionError(
                    "division by zero",
                    expr.span,
                    hint="The divisor must be non-zero.",
                )
            if expr.operator == "%":
                if right == 0:
                    raise SwarnaZeroDivisionError(
                        "modulo by zero",
                        expr.span,
                        hint="The divisor must be non-zero.",
                    )
            if expr.operator == "//":
                if type(left) is not int or type(right) is not int:
                    raise SwarnaTypeError(
                        "'//' requires Int operands",
                        expr.span,
                        hint="Use `/` for true division or convert the operands to Int.",
                        category="type-mismatch",
                    )
                if right == 0:
                    raise SwarnaZeroDivisionError(
                        "integer division by zero",
                        expr.span,
                        hint="The divisor must be non-zero.",
                    )
            try:
                if expr.operator == "+":
                    return left + right
                if expr.operator == "-":
                    return left - right
                if expr.operator == "*":
                    return left * right
                if expr.operator == "/":
                    return left / right
                if expr.operator == "//":
                    return left // right
                if expr.operator == "%":
                    return left % right
                if expr.operator == "==":
                    return left == right
                if expr.operator == "!=":
                    return left != right
                if expr.operator == "<":
                    return left < right
                if expr.operator == "<=":
                    return left <= right
                if expr.operator == ">":
                    return left > right
                if expr.operator == ">=":
                    return left >= right
            except SwarnaTypeError:
                raise
            except TypeError as e:
                raise SwarnaTypeError(
                    str(e),
                    expr.span,
                    hint="The operands have incompatible types.",
                    category="type-mismatch",
                ) from e
            raise SwarnaRuntimeError(
                f"Unsupported binary operator {expr.operator!r}",
                expr.span,
                hint="This operator is not implemented yet.",
            )
        raise SwarnaRuntimeError(
            f"Unsupported expression: {type(expr).__name__}",
            expr.span,
            hint="This expression is not supported by the interpreter yet.",
        )
