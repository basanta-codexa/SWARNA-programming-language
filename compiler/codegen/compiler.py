from __future__ import annotations

from compiler.ast.nodes import (
    AssignmentStatement,
    BinaryExpression,
    BlockStatement,
    BoolLiteral,
    Expression,
    FloatLiteral,
    Identifier,
    IfStatement,
    IntegerLiteral,
    LetStatement,
    PrintStatement,
    Program,
    Statement,
    UnaryExpression,
    WhileStatement,
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

    def emit(self, op: Op, arg=None) -> int:
        self.instructions.append(Instruction(op, arg))
        return len(self.instructions) - 1

    def patch(self, index: int, target: int) -> None:
        ins = self.instructions[index]
        if ins.op not in (Op.JUMP, Op.JUMP_IF_FALSE):
            raise RuntimeError(f"Cannot patch non-jump instruction at {index}: {ins!r}")
        self.instructions[index] = Instruction(ins.op, target)

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
        if isinstance(stmt, IfStatement):
            self.compile_expression(stmt.condition)
            jump_to_else = self.emit(Op.JUMP_IF_FALSE, None)
            self.compile_block(stmt.then_branch)
            if stmt.else_branch is not None:
                jump_to_end = self.emit(Op.JUMP, None)
                self.patch(jump_to_else, len(self.instructions))
                self.compile_block(stmt.else_branch)
                self.patch(jump_to_end, len(self.instructions))
            else:
                self.patch(jump_to_else, len(self.instructions))
            return
        if isinstance(stmt, WhileStatement):
            loop_start = len(self.instructions)
            self.compile_expression(stmt.condition)
            jump_to_end = self.emit(Op.JUMP_IF_FALSE, None)
            self.compile_block(stmt.body)
            self.emit(Op.JUMP, loop_start)
            self.patch(jump_to_end, len(self.instructions))
            return
        if isinstance(stmt, BlockStatement):
            self.compile_block(stmt)
            return
        raise NotImplementedError(f"Codegen not implemented for: {type(stmt).__name__}")

    def compile_block(self, block: BlockStatement) -> None:
        for stmt in block.statements:
            self.compile_statement(stmt)

    def compile_expression(self, expr: Expression) -> None:
        if isinstance(expr, IntegerLiteral):
            self.emit(Op.CONST, expr.value)
            return
        if isinstance(expr, FloatLiteral):
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
