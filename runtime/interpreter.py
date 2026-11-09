from __future__ import annotations

from compiler.ast.nodes import AssignmentStatement, BinaryExpression, BlockStatement, BoolLiteral, Expression, FloatLiteral, Identifier, IfExpression, IfStatement, IntegerLiteral, LetStatement, PrintStatement, Program, Statement, StringLiteral, UnaryExpression, WhileStatement
from compiler.diagnostics import SwarnaNameError, SwarnaRuntimeError, SwarnaTypeError, SwarnaZeroDivisionError


class Interpreter:
    def __init__(self) -> None:
        self.env: dict[str, int | float | bool | str] = {}
        self.constant: dict[str, bool] = {}
        self.output: list[int | float | bool | str] = []

    def eval(self, program: Program) -> dict[str, int | float | bool | str]:
        for stmt in program.statements:
            self.eval_statement(stmt)
        return dict(self.env)

    def eval_statement(self, stmt: Statement) -> None:
        if isinstance(stmt, LetStatement):
            name = stmt.name.name
            self.env[name] = self.eval_expression(stmt.value)
            self.constant[name] = stmt.constant
            return
        if isinstance(stmt, AssignmentStatement):
            name = stmt.name.name
            value = self.eval_expression(stmt.value)
            if name not in self.env:
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

    def eval_expression(self, expr: Expression) -> int | float | bool | str:
        if isinstance(expr, IntegerLiteral):
            return expr.value
        if isinstance(expr, FloatLiteral):
            return expr.value
        if isinstance(expr, StringLiteral):
            return expr.value
        if isinstance(expr, BoolLiteral):
            return expr.value
        if isinstance(expr, IfExpression):
            if bool(self.eval_expression(expr.condition)):
                return self.eval_expression(expr.then_value)
            return self.eval_expression(expr.else_value)
        if isinstance(expr, Identifier):
            if expr.name not in self.env:
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
