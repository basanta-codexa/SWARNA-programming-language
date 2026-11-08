from __future__ import annotations

from compiler.bytecode.instructions import Instruction, Op


class VM:
    def __init__(self) -> None:
        self.stack: list[int | bool] = []
        self.env: dict[str, int | bool] = {}
        self.output: list[int | bool] = []

    def run(self, instructions: list[Instruction]) -> dict[str, int | bool]:
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
                self.stack.append(int(a / b))
            elif ins.op == Op.NEG:
                self.stack.append(-self.stack.pop())
            elif ins.op == Op.NOT:
                self.stack.append(not bool(self.stack.pop()))
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
            elif ins.op == Op.POP:
                if self.stack:
                    self.stack.pop()
            elif ins.op == Op.HALT:
                break
            else:
                raise RuntimeError(f"Unsupported opcode: {ins.op}")
        return dict(self.env)
