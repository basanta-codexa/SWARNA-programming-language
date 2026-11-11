from __future__ import annotations

from dataclasses import dataclass

from compiler.ast.nodes import AssignmentStatement, BinaryExpression, BlockExpression, BlockStatement, BoolLiteral, CallExpression, Expression, FloatLiteral, FunctionDeclaration, Identifier, IfExpression, IfStatement, IndexExpression, IntegerLiteral, LetStatement, ListLiteral, PrintStatement, Program, Statement, StringLiteral, UnaryExpression, WhileStatement
from compiler.diagnostics import SourceSpan, SwarnaNameError, SwarnaRuntimeError, SwarnaTypeError, SwarnaZeroDivisionError
from runtime.values import Value, value_type_name


@dataclass(frozen=True)
class Function:
    name: str
    parameters: tuple[str, ...]
    body: Expression
    span: SourceSpan | None = None
    parameter_annotations: tuple[str | None, ...] = ()
    return_annotation: str | None = None


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
                    parameter.type_name.name if parameter.type_name is not None else None
                    for parameter in stmt.parameters
                ),
                return_annotation=stmt.return_type.name if stmt.return_type is not None else None,
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
            self.env[name] = self.eval_expression(stmt.value)
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
                )
            if self.constant.get(name, False):
                raise SwarnaRuntimeError(
                    f"Cannot assign to const binding '{name}'",
                    stmt.name.span,
                    hint="Change the binding to `let` if it needs to be reassigned.",
                )
            self.env[name] = value
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
                self.eval_block(stmt.body)
            return
        if isinstance(stmt, BlockStatement):
            self.eval_block(stmt)
            return
        raise SwarnaRuntimeError(
            f"Unsupported statement: {type(stmt).__name__}",
            stmt.span,
            hint="This statement is not supported by the interpreter yet.",
        )

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
                    hint="Pass one list or string to `len`.",
                )
            value = self.eval_expression(expr.arguments[0])
            if isinstance(value, (list, str)):
                return len(value)
            raise SwarnaTypeError(
                f"`len` expects a List or String, got {value_type_name(value)}",
                expr.arguments[0].span,
                hint="Pass a list or string to `len`.",
            )
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
            return self.eval_expression(function.body)
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
        if isinstance(expr, BlockExpression):
            return self.eval_block_expression(expr)
        if isinstance(expr, IfExpression):
            if bool(self.eval_expression(expr.condition)):
                return self.eval_expression(expr.then_value)
            return self.eval_expression(expr.else_value)
        if isinstance(expr, ListLiteral):
            return [self.eval_expression(element) for element in expr.elements]
        if isinstance(expr, IndexExpression):
            collection = self.eval_expression(expr.collection)
            index = self.eval_expression(expr.index)
            if not isinstance(collection, list):
                raise SwarnaTypeError(
                    f"Cannot index {value_type_name(collection)}",
                    expr.span,
                    hint="Only lists can be indexed right now.",
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
            if expr.operator == "//":
                if type(left) is not int or type(right) is not int:
                    raise SwarnaTypeError(
                        "'//' requires Int operands",
                        expr.span,
                        hint="Use `/` for true division or convert the operands to Int.",
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
