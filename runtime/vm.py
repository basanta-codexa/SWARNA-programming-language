from __future__ import annotations

import operator
from typing import Any, Callable

from compiler.bytecode.instructions import Instruction, Op
from compiler.diagnostics import SwarnaNameError, SwarnaRuntimeError, SwarnaTypeError, SwarnaZeroDivisionError


class VM:
    def __init__(self) -> None:
        self.stack: list[int | float | bool | str] = []
        self.env: dict[str, int | float | bool | str] = {}
        self.constant: set[str] = set()
        self.output: list[int | float | bool | str] = []

    def _pop(self, ins: Instruction) -> int | float | bool | str:
        if not self.stack:
            raise SwarnaRuntimeError(
                f"Stack underflow on {ins.op.name}",
                ins.span,
                hint="The bytecode compiler produced an invalid stack operation.",
            )
        return self.stack.pop()

    def _binary(self, ins: Instruction, operation: Callable[[Any, Any], Any]) -> None:
        b = self._pop(ins)
        a = self._pop(ins)
        try:
            self.stack.append(operation(a, b))
        except SwarnaTypeError:
            raise
        except TypeError as e:
            raise SwarnaTypeError(
                str(e),
                ins.span,
                hint="The operands have incompatible types.",
            ) from e

    def run(self, instructions: list[Instruction]) -> dict[str, int | float | bool | str]:
        self.stack = []
        ip = 0
        while ip < len(instructions):
            ins = instructions[ip]
            ip += 1
            if ins.op == Op.CONST:
                self.stack.append(ins.arg)
            elif ins.op == Op.LOAD_NAME:
                name = ins.arg
                if name not in self.env:
                    raise SwarnaNameError(
                        f"Undefined name '{name}'",
                        ins.span,
                        hint="Declare it first with `let name = value` or `const name = value`.",
                    )
                self.stack.append(self.env[name])
            elif ins.op == Op.STORE_NAME:
                value = self._pop(ins)
                name = ins.arg
                if name not in self.env:
                    raise SwarnaNameError(
                        f"Undefined name '{name}'",
                        ins.span,
                        hint="Declare it first with `let name = value` or `const name = value`.",
                    )
                if name in self.constant:
                    raise SwarnaRuntimeError(
                        f"Cannot assign to const binding '{name}'",
                        ins.span,
                        hint="Change the binding to `let` if it needs to be reassigned.",
                    )
                self.env[name] = value
            elif ins.op == Op.DECLARE_NAME:
                self.env[ins.arg] = self._pop(ins)
                self.constant.discard(ins.arg)
            elif ins.op == Op.STORE_CONST:
                self.env[ins.arg] = self._pop(ins)
                self.constant.add(ins.arg)
            elif ins.op == Op.DUP:
                if not self.stack:
                    raise SwarnaRuntimeError(
                        "Stack underflow on DUP",
                        ins.span,
                        hint="The bytecode compiler produced an invalid stack operation.",
                    )
                self.stack.append(self.stack[-1])
            elif ins.op == Op.ADD:
                self._binary(ins, operator.add)
            elif ins.op == Op.SUB:
                self._binary(ins, operator.sub)
            elif ins.op == Op.MUL:
                self._binary(ins, operator.mul)
            elif ins.op == Op.DIV:
                b = self._pop(ins)
                a = self._pop(ins)
                if b == 0:
                    raise SwarnaZeroDivisionError(
                        "division by zero",
                        ins.span,
                        hint="The divisor must be non-zero.",
                    )
                try:
                    self.stack.append(a / b)
                except TypeError as e:
                    raise SwarnaTypeError(
                        str(e),
                        ins.span,
                        hint="The operands have incompatible types.",
                    ) from e
            elif ins.op == Op.IDIV:
                b = self._pop(ins)
                a = self._pop(ins)
                if type(a) is not int or type(b) is not int:
                    raise SwarnaTypeError(
                        "'//' requires Int operands",
                        ins.span,
                        hint="Use `/` for true division or convert the operands to Int.",
                    )
                if b == 0:
                    raise SwarnaZeroDivisionError(
                        "integer division by zero",
                        ins.span,
                        hint="The divisor must be non-zero.",
                    )
                self.stack.append(a // b)
            elif ins.op == Op.NEG:
                value = self._pop(ins)
                try:
                    self.stack.append(-value)
                except TypeError as e:
                    raise SwarnaTypeError(
                        str(e),
                        ins.span,
                        hint="Unary `-` requires a number.",
                    ) from e
            elif ins.op == Op.NOT:
                self.stack.append(not bool(self._pop(ins)))
            elif ins.op == Op.BOOL:
                if not self.stack:
                    raise SwarnaRuntimeError(
                        "Stack underflow on BOOL",
                        ins.span,
                        hint="The bytecode compiler produced an invalid stack operation.",
                    )
                self.stack[-1] = bool(self.stack[-1])
            elif ins.op == Op.EQ:
                self._binary(ins, operator.eq)
            elif ins.op == Op.NEQ:
                self._binary(ins, operator.ne)
            elif ins.op == Op.LT:
                self._binary(ins, operator.lt)
            elif ins.op == Op.LTE:
                self._binary(ins, operator.le)
            elif ins.op == Op.GT:
                self._binary(ins, operator.gt)
            elif ins.op == Op.GTE:
                self._binary(ins, operator.ge)
            elif ins.op == Op.PRINT:
                self.output.append(self._pop(ins))
            elif ins.op == Op.JUMP:
                ip = self._jump_target(ins, len(instructions))
            elif ins.op == Op.JUMP_IF_FALSE:
                condition = self._pop(ins)
                if not bool(condition):
                    ip = self._jump_target(ins, len(instructions))
            elif ins.op == Op.POP:
                self._pop(ins)
            elif ins.op == Op.HALT:
                break
            else:
                raise SwarnaRuntimeError(
                    f"Unsupported opcode: {ins.op}",
                    ins.span,
                    hint="The bytecode compiler produced an unsupported instruction.",
                )
        return dict(self.env)

    @staticmethod
    def _jump_target(ins: Instruction, code_size: int) -> int:
        """Jump targets are absolute instruction indices and must be in bounds."""
        target = ins.arg
        if not isinstance(target, int) or not (0 <= target < code_size):
            raise SwarnaRuntimeError(
                f"Invalid jump target: {target!r}",
                ins.span,
                hint="The bytecode compiler produced an invalid jump.",
            )
        return target
