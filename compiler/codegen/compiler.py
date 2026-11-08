from __future__ import annotations

from compiler.ast.nodes import (
    AssignmentStatement,
    BinaryExpression,
    BoolLiteral,
    Expression,
    Identifier,
    IntegerLiteral,
    LetStatement,
    PrintStatement,
    Program,
    Statement,
    UnaryExpression,
)
from compiler.bytecode.instructions import Instruction, Op


class Compiler:
    def __init__(self) -> None:
        self.instructions: list[Instruction] = []

    def compile(self, program: Program) -> list[Instruction]:
        self.instructions = []
        for stmt in program.statements:
            self.compile_statement(stmt)
        self.emit(Op.HALT)
        return list(self.instructions)

    def emit(self, op: Op, arg=None) -> None:
        self.instructions.append(Instruction(op, arg))

    def compile_statement(self, stmt: Statement) -> None:
        if isinstance(stmt, LetStatement):
            self.compile_expression(stmt.value)
            self.emit(Op.STORE_NAME, stmt.name.name)
            return
        if isinstance(stmt, AssignmentStatement):
            self.compile_expression(stmt.value)
            self.emit(Op.STORE_NAME, stmt.name.name)
            return
        if isinstance(stmt, PrintStatement):
            self.compile_expression(stmt.value)
            self.emit(Op.PRINT)
            return
        raise NotImplementedError(f"Codegen not implemented for: {type(stmt).__name__}")

    def compile_expression(self, expr: Expression) -> None:
        if isinstance(expr, IntegerLiteral):
            self.emit(Op.CONST, expr.value)
            return
        if isinstance(expr, BoolLiteral):
            self.emit(Op.CONST, expr.value)
            return
        if isinstance(expr, Identifier):
            self.emit(Op.LOAD_NAME, expr.name)
            return
        if isinstance(expr, UnaryExpression):
            self.compile_expression(expr.operand)
            if expr.operator == "-":
                self.emit(Op.NEG)
                return
            if expr.operator == "!":
                self.emit(Op.NOT)
                return
            raise NotImplementedError(f"Unary operator not implemented: {expr.operator!r}")
        if isinstance(expr, BinaryExpression):
            self.compile_expression(expr.left)
            self.compile_expression(expr.right)
            ops = {
                "+": Op.ADD,
                "-": Op.SUB,
                "*": Op.MUL,
                "/": Op.DIV,
                "==": Op.EQ,
                "!=": Op.NEQ,
                "<": Op.LT,
                "<=": Op.LTE,
                ">": Op.GT,
                ">=": Op.GTE,
            }
            if expr.operator not in ops:
                raise NotImplementedError(f"Binary operator not implemented: {expr.operator!r}")
            self.emit(ops[expr.operator])
            return
        raise NotImplementedError(f"Expression codegen not implemented: {type(expr).__name__}")
