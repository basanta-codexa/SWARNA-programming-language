from __future__ import annotations

from compiler.ast.nodes import AssignmentStatement, BinaryExpression, BlockStatement, BoolLiteral, Expression, FloatLiteral, Identifier, IfStatement, IntegerLiteral, LetStatement, PrintStatement, Program, Statement, StringLiteral, UnaryExpression, WhileStatement


class Interpreter:
    def __init__(self) -> None:
        self.env: dict[str, int | float | bool | str] = {}
        self.mutable: dict[str, bool] = {}
        self.output: list[int | float | bool | str] = []

    def eval(self, program: Program) -> dict[str, int | float | bool | str]:
        for stmt in program.statements:
            self.eval_statement(stmt)
        return dict(self.env)

    def eval_statement(self, stmt: Statement) -> None:
        if isinstance(stmt, LetStatement):
            name = stmt.name.name
            self.env[name] = self.eval_expression(stmt.value)
            self.mutable[name] = stmt.mutable
            return
        if isinstance(stmt, AssignmentStatement):
            name = stmt.name.name
            if name not in self.env:
                raise NameError(f"Undefined name '{name}'")
            if not self.mutable.get(name, False):
                raise RuntimeError(f"Cannot assign to immutable binding '{name}'")
            self.env[name] = self.eval_expression(stmt.value)
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
        raise RuntimeError(f"Unsupported statement: {stmt!r}")

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
        if isinstance(expr, Identifier):
            if expr.name not in self.env:
                raise NameError(f"Undefined name '{expr.name}'")
            return self.env[expr.name]
        if isinstance(expr, UnaryExpression):
            value = self.eval_expression(expr.operand)
            if expr.operator == "-":
                return -value
            if expr.operator == "!":
                return not bool(value)
            raise RuntimeError(f"Unsupported unary operator {expr.operator!r}")
        if isinstance(expr, BinaryExpression):
            if expr.operator == "&&":
                left = self.eval_expression(expr.left)
                return bool(self.eval_expression(expr.right)) if bool(left) else False
            if expr.operator == "||":
                left = self.eval_expression(expr.left)
                return True if bool(left) else bool(self.eval_expression(expr.right))
            left = self.eval_expression(expr.left)
            right = self.eval_expression(expr.right)
            if expr.operator == "+":
                return left + right
            if expr.operator == "-":
                return left - right
            if expr.operator == "*":
                return left * right
            if expr.operator == "/":
                if right == 0:
                    raise ZeroDivisionError("division by zero")
                return left / right
            if expr.operator == "//":
                if type(left) is not int or type(right) is not int:
                    raise TypeError("'//' requires Int operands")
                if right == 0:
                    raise ZeroDivisionError("integer division by zero")
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
            raise RuntimeError(f"Unsupported binary operator {expr.operator!r}")
        raise RuntimeError(f"Unsupported expression: {expr!r}")
