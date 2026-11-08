from __future__ import annotations

from compiler.bytecode.instructions import Instruction, Op


class VM:
    def __init__(self) -> None:
        self.stack: list[int | float | bool | str] = []
        self.env: dict[str, int | float | bool | str] = {}
        self.output: list[int | float | bool | str] = []

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
                    raise NameError(f"Undefined name '{name}'")
                self.stack.append(self.env[name])
            elif ins.op == Op.STORE_NAME:
                if not self.stack:
                    raise RuntimeError("Stack underflow on STORE_NAME")
                self.env[ins.arg] = self.stack.pop()
            elif ins.op == Op.DUP:
                if not self.stack:
                    raise RuntimeError("Stack underflow on DUP")
                self.stack.append(self.stack[-1])
            elif ins.op == Op.ADD:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a + b)
            elif ins.op == Op.SUB:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a - b)
            elif ins.op == Op.MUL:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a * b)
            elif ins.op == Op.DIV:
                b, a = self.stack.pop(), self.stack.pop()
                if b == 0:
                    raise ZeroDivisionError("division by zero")
                self.stack.append(a / b)
            elif ins.op == Op.IDIV:
                b, a = self.stack.pop(), self.stack.pop()
                if type(a) is not int or type(b) is not int:
                    raise TypeError("'//' requires Int operands")
                if b == 0:
                    raise ZeroDivisionError("integer division by zero")
                self.stack.append(a // b)
            elif ins.op == Op.NEG:
                self.stack.append(-self.stack.pop())
            elif ins.op == Op.NOT:
                self.stack.append(not bool(self.stack.pop()))
            elif ins.op == Op.BOOL:
                if not self.stack:
                    raise RuntimeError("Stack underflow on BOOL")
                self.stack[-1] = bool(self.stack[-1])
            elif ins.op == Op.EQ:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a == b)
            elif ins.op == Op.NEQ:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a != b)
            elif ins.op == Op.LT:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a < b)
            elif ins.op == Op.LTE:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a <= b)
            elif ins.op == Op.GT:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a > b)
            elif ins.op == Op.GTE:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a >= b)
            elif ins.op == Op.PRINT:
                if not self.stack:
                    raise RuntimeError("Stack underflow on PRINT")
                self.output.append(self.stack.pop())
            elif ins.op == Op.JUMP:
                ip = self._jump_target(ins, len(instructions))
            elif ins.op == Op.JUMP_IF_FALSE:
                if not self.stack:
                    raise RuntimeError("Stack underflow on JUMP_IF_FALSE")
                condition = self.stack.pop()
                if not bool(condition):
                    ip = self._jump_target(ins, len(instructions))
            elif ins.op == Op.POP:
                if self.stack:
                    self.stack.pop()
            elif ins.op == Op.HALT:
                break
            else:
                raise RuntimeError(f"Unsupported opcode: {ins.op}")
        return dict(self.env)

    @staticmethod
    def _jump_target(ins: Instruction, code_size: int) -> int:
        """Jump targets are absolute instruction indices and must be in bounds."""
        target = ins.arg
        if not isinstance(target, int) or not (0 <= target < code_size):
            raise RuntimeError(f"Invalid jump target: {target!r}")
        return target
