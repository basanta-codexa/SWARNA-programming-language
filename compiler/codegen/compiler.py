from __future__ import annotations

from compiler.ast.nodes import (
    AssignmentStatement,
    BinaryExpression,
    BlockExpression,
    BlockStatement,
    BoolLiteral,
    Expression,
    FloatLiteral,
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
from compiler.bytecode.instructions import Instruction, Op
from compiler.diagnostics import SourceSpan


class Compiler:
    def __init__(self) -> None:
        self.instructions: list[Instruction] = []

    def compile(self, program: Program) -> list[Instruction]:
        self.instructions = []
        for stmt in program.statements:
            self.compile_statement(stmt)
        self.emit(Op.HALT, span=program.span)
        return list(self.instructions)

    def emit(self, op: Op, arg=None, span: SourceSpan | None = None) -> int:
        self.instructions.append(Instruction(op, arg, span=span))
        return len(self.instructions) - 1

    def patch(self, index: int, target: int) -> None:
        ins = self.instructions[index]
        if ins.op not in (Op.JUMP, Op.JUMP_IF_FALSE):
            raise RuntimeError(f"Cannot patch non-jump instruction at {index}: {ins!r}")
        self.instructions[index] = Instruction(ins.op, target, span=ins.span)

    def compile_statement(self, stmt: Statement) -> None:
        if isinstance(stmt, LetStatement):
            self.compile_expression(stmt.value)
            self.emit(
                Op.STORE_CONST if stmt.constant else Op.DECLARE_NAME,
                stmt.name.name,
                stmt.name.span,
            )
            return
        if isinstance(stmt, AssignmentStatement):
            self.compile_expression(stmt.value)
            self.emit(Op.STORE_NAME, stmt.name.name, stmt.name.span)
            return
        if isinstance(stmt, PrintStatement):
            self.compile_expression(stmt.value)
            self.emit(Op.PRINT, span=stmt.span)
            return
        if isinstance(stmt, IfStatement):
            self.compile_expression(stmt.condition)
            jump_to_else = self.emit(Op.JUMP_IF_FALSE, None, stmt.condition.span)
            self.compile_block(stmt.then_branch)
            if stmt.else_branch is not None:
                jump_to_end = self.emit(Op.JUMP, None, stmt.span)
                self.patch(jump_to_else, len(self.instructions))
                self.compile_block(stmt.else_branch)
                self.patch(jump_to_end, len(self.instructions))
            else:
                self.patch(jump_to_else, len(self.instructions))
            return
        if isinstance(stmt, WhileStatement):
            loop_start = len(self.instructions)
            self.compile_expression(stmt.condition)
            jump_to_end = self.emit(Op.JUMP_IF_FALSE, None, stmt.condition.span)
            self.compile_block(stmt.body)
            self.emit(Op.JUMP, loop_start, stmt.span)
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
            self.emit(Op.CONST, expr.value, expr.span)
            return
        if isinstance(expr, FloatLiteral):
            self.emit(Op.CONST, expr.value, expr.span)
            return
        if isinstance(expr, StringLiteral):
            self.emit(Op.CONST, expr.value, expr.span)
            return
        if isinstance(expr, BoolLiteral):
            self.emit(Op.CONST, expr.value, expr.span)
            return
        if isinstance(expr, BlockExpression):
            for stmt in expr.statements:
                self.compile_statement(stmt)
            self.compile_expression(expr.value)
            return
        if isinstance(expr, IfExpression):
            self.compile_expression(expr.condition)
            jump_to_else = self.emit(Op.JUMP_IF_FALSE, None, expr.condition.span)
            self.compile_expression(expr.then_value)
            jump_to_end = self.emit(Op.JUMP, None, expr.span)
            self.patch(jump_to_else, len(self.instructions))
            self.compile_expression(expr.else_value)
            self.patch(jump_to_end, len(self.instructions))
            return
        if isinstance(expr, Identifier):
            self.emit(Op.LOAD_NAME, expr.name, expr.span)
            return
        if isinstance(expr, UnaryExpression):
            self.compile_expression(expr.operand)
            if expr.operator == "-":
                self.emit(Op.NEG, span=expr.span)
                return
            if expr.operator == "!":
                self.emit(Op.NOT, span=expr.span)
                return
            raise NotImplementedError(f"Unary operator not implemented: {expr.operator!r}")
        if isinstance(expr, BinaryExpression):
            if expr.operator == "&&":
                self.compile_and(expr)
                return
            if expr.operator == "||":
                self.compile_or(expr)
                return
            self.compile_expression(expr.left)
            self.compile_expression(expr.right)
            ops = {
                "+": Op.ADD,
                "-": Op.SUB,
                "*": Op.MUL,
                "/": Op.DIV,
                "//": Op.IDIV,
                "==": Op.EQ,
                "!=": Op.NEQ,
                "<": Op.LT,
                "<=": Op.LTE,
                ">": Op.GT,
                ">=": Op.GTE,
            }
            if expr.operator not in ops:
                raise NotImplementedError(f"Binary operator not implemented: {expr.operator!r}")
            self.emit(ops[expr.operator], span=expr.span)
            return
        raise NotImplementedError(f"Expression codegen not implemented: {type(expr).__name__}")

    def compile_and(self, expr: BinaryExpression) -> None:
        self.compile_expression(expr.left)
        self.emit(Op.DUP, span=expr.span)
        jump_to_false = self.emit(Op.JUMP_IF_FALSE, None, expr.span)
        self.emit(Op.POP, span=expr.span)
        self.compile_expression(expr.right)
        self.emit(Op.BOOL, span=expr.span)
        jump_to_end = self.emit(Op.JUMP, None, expr.span)
        self.patch(jump_to_false, len(self.instructions))
        self.emit(Op.POP, span=expr.span)
        self.emit(Op.CONST, False, expr.span)
        self.patch(jump_to_end, len(self.instructions))

    def compile_or(self, expr: BinaryExpression) -> None:
        self.compile_expression(expr.left)
        self.emit(Op.DUP, span=expr.span)
        jump_to_false = self.emit(Op.JUMP_IF_FALSE, None, expr.span)
        self.emit(Op.POP, span=expr.span)
        self.emit(Op.CONST, True, expr.span)
        jump_to_end = self.emit(Op.JUMP, None, expr.span)
        self.patch(jump_to_false, len(self.instructions))
        self.emit(Op.POP, span=expr.span)
        self.compile_expression(expr.right)
        self.emit(Op.BOOL, span=expr.span)
        self.patch(jump_to_end, len(self.instructions))
