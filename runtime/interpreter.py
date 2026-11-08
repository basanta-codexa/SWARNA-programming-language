from __future__ import annotations

from compiler.ast.nodes import BinaryExpression, BlockStatement, BoolLiteral, Expression, Identifier, IfStatement, IntegerLiteral, LetStatement, PrintStatement, Program, Statement, UnaryExpression


class Interpreter:
    def __init__(self) -> None:
        self.env: dict[str, int | bool] = {}
        self.output: list[int | bool] = []

    def eval(self, program: Program) -> dict[str, int | bool]:
        for stmt in program.statements:
            self.eval_statement(stmt)
        return dict(self.env)

    def eval_statement(self, stmt: Statement) -> None:
        if isinstance(stmt, LetStatement):
            self.env[stmt.name.name] = self.eval_expression(stmt.value)
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
        if isinstance(stmt, BlockStatement):
            self.eval_block(stmt)
            return
        raise RuntimeError(f"Unsupported statement: {stmt!r}")

    def eval_block(self, block: BlockStatement) -> None:
        for stmt in block.statements:
            self.eval_statement(stmt)

    def eval_expression(self, expr: Expression) -> int | bool:
        if isinstance(expr, IntegerLiteral):
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
                return int(left / right)
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
