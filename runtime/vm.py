from __future__ import annotations

import operator
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Callable

from compiler.bytecode.instructions import Instruction, Op
from compiler.bytecode.program import CompiledProgram, FunctionInfo
from compiler.diagnostics import SwarnaNameError, SwarnaRuntimeError, SwarnaTypeError, SwarnaZeroDivisionError
from runtime.values import Value, value_type_name


@dataclass
class ForFrame:
    name: str
    iterator: Iterator[Value]
    had_previous: bool
    previous_value: Value | None
    previous_constant: bool


class VM:
    def __init__(self) -> None:
        self.stack: list[Value] = []
        self.env: dict[str, Value] = {}
        self.constant: set[str] = set()
        self.output: list[Value] = []
        self.global_env: dict[str, Value] = self.env
        self.global_constant: set[str] = self.constant
        self.functions: dict[str, FunctionInfo] = {}
        self.iterators: list[ForFrame] = []
        self.call_depth = 0
        self.max_call_depth = 200

    def _pop(self, ins: Instruction) -> Value:
        if not self.stack:
            raise SwarnaRuntimeError(
                f"Stack underflow on {ins.op.name}",
                ins.span,
                hint="The bytecode compiler produced an invalid stack operation.",
            )
        return self.stack.pop()

    def _restore_for_frame(self, frame: ForFrame) -> None:
        if frame.had_previous:
            self.env[frame.name] = frame.previous_value
            if frame.previous_constant:
                self.constant.add(frame.name)
            else:
                self.constant.discard(frame.name)
        else:
            self.env.pop(frame.name, None)
            self.constant.discard(frame.name)

    def _cleanup_iterators(self, depth: int) -> None:
        while len(self.iterators) > depth:
            self._restore_for_frame(self.iterators.pop())

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
                category="type-mismatch",
            ) from e

    def run(self, program: CompiledProgram | list[Instruction]) -> dict[str, Value]:
        if isinstance(program, list):
            program = CompiledProgram(tuple(program))
        self.global_env = self.env
        self.global_constant = self.constant
        self.stack = []
        self.functions = program.functions
        self.iterators = []
        self.call_depth = 0
        try:
            self._execute(program.instructions, allow_return=False)
        finally:
            self._cleanup_iterators(0)
        return dict(self.env)

    def _execute(self, instructions: tuple[Instruction, ...], *, allow_return: bool) -> Value | None:
        ip = 0
        while ip < len(instructions):
            ins = instructions[ip]
            ip += 1
            if ins.op == Op.CONST:
                self.stack.append(ins.arg)
            elif ins.op == Op.LOAD_NAME:
                name = ins.arg
                if name not in self.env:
                    if name in self.functions:
                        raise SwarnaNameError(
                            f"Function '{name}' must be called",
                            ins.span,
                            hint="Add parentheses and arguments, or bind the result to a name.",
                        )
                    raise SwarnaNameError(
                        f"Undefined name '{name}'",
                        ins.span,
                        hint="Declare it first with `let name = value` or `const name = value`.",
                        category="undefined-name",
                    )
                self.stack.append(self.env[name])
            elif ins.op == Op.STORE_NAME:
                value = self._pop(ins)
                name = ins.arg
                if name not in self.env:
                    if name in self.functions:
                        raise SwarnaNameError(
                            f"Cannot assign to function '{name}'",
                            ins.span,
                            hint="Call the function and assign its result to a variable.",
                        )
                    raise SwarnaNameError(
                        f"Undefined name '{name}'",
                        ins.span,
                        hint="Declare it first with `let name = value` or `const name = value`.",
                        category="undefined-name",
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
                        category="type-mismatch",
                    ) from e
            elif ins.op == Op.IDIV:
                b = self._pop(ins)
                a = self._pop(ins)
                if type(a) is not int or type(b) is not int:
                    raise SwarnaTypeError(
                        "'//' requires Int operands",
                        ins.span,
                        hint="Use `/` for true division or convert the operands to Int.",
                        category="type-mismatch",
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
            elif ins.op == Op.BUILD_LIST:
                count = ins.arg
                if not isinstance(count, int) or count < 0:
                    raise SwarnaRuntimeError(
                        "Invalid BUILD_LIST count",
                        ins.span,
                        hint="The bytecode compiler produced an invalid list instruction.",
                    )
                if len(self.stack) < count:
                    raise SwarnaRuntimeError(
                        "Stack underflow on BUILD_LIST",
                        ins.span,
                        hint="The bytecode compiler produced an invalid stack operation.",
                    )
                elements = [self._pop(ins) for _ in range(count)]
                elements.reverse()
                self.stack.append(elements)
            elif ins.op == Op.INDEX:
                index = self._pop(ins)
                collection = self._pop(ins)
                if not isinstance(collection, list):
                    raise SwarnaTypeError(
                        f"Cannot index {value_type_name(collection)}",
                        ins.span,
                        hint="Only lists can be indexed right now.",
                    )
                if type(index) is not int:
                    raise SwarnaTypeError(
                        "List index must be Int",
                        ins.span,
                        hint="Use an integer index, such as `values[0]`.",
                    )
                try:
                    self.stack.append(collection[index])
                except IndexError:
                    raise SwarnaRuntimeError(
                        f"Index {index} is out of range for a list of length {len(collection)}",
                        ins.span,
                        hint="Use an index from 0 to len(list) - 1, or a negative index from -len(list) to -1.",
                    ) from None
            elif ins.op == Op.LEN:
                value = self._pop(ins)
                if isinstance(value, (list, str)):
                    self.stack.append(len(value))
                else:
                    raise SwarnaTypeError(
                        f"`len` expects a List or String, got {value_type_name(value)}",
                        ins.span,
                        hint="Pass a list or string to `len`.",
                    )
            elif ins.op == Op.ITER_START:
                iterable = self._pop(ins)
                if not isinstance(iterable, list):
                    raise SwarnaTypeError(
                        f"`for` expects a List, got {value_type_name(iterable)}",
                        ins.span,
                        hint="Use a list after `in`.",
                    )
                name = ins.arg
                if not isinstance(name, str):
                    raise SwarnaRuntimeError(
                        "Invalid ITER_START name",
                        ins.span,
                        hint="The bytecode compiler produced an invalid for loop.",
                    )
                self.iterators.append(
                    ForFrame(
                        name=name,
                        iterator=iter(iterable),
                        had_previous=name in self.env,
                        previous_value=self.env.get(name),
                        previous_constant=name in self.constant,
                    )
                )
            elif ins.op == Op.ITER_NEXT:
                if not self.iterators:
                    raise SwarnaRuntimeError(
                        "ITER_NEXT without ITER_START",
                        ins.span,
                        hint="The bytecode compiler produced an invalid for loop.",
                    )
                frame = self.iterators[-1]
                try:
                    item = next(frame.iterator)
                except StopIteration:
                    self.iterators.pop()
                    self._restore_for_frame(frame)
                    ip = self._jump_target(ins, len(instructions))
                else:
                    self.env[frame.name] = item
                    self.constant.discard(frame.name)
            elif ins.op == Op.CALL:
                self._call(ins)
            elif ins.op == Op.RETURN:
                if not allow_return:
                    raise SwarnaRuntimeError(
                        "RETURN outside a function",
                        ins.span,
                        hint="The bytecode compiler produced an invalid return.",
                    )
                return self._pop(ins)
            elif ins.op == Op.HALT:
                if allow_return:
                    raise SwarnaRuntimeError(
                        "Function ended without returning a value",
                        ins.span,
                        hint="The bytecode compiler produced an invalid function.",
                    )
                return None
            else:
                raise SwarnaRuntimeError(
                    f"Unsupported opcode: {ins.op}",
                    ins.span,
                    hint="The bytecode compiler produced an unsupported instruction.",
                )
        if allow_return:
            raise SwarnaRuntimeError(
                "Function ended without returning a value",
                instructions[-1].span if instructions else None,
                hint="The bytecode compiler produced an invalid function.",
            )
        return None

    def _call(self, ins: Instruction) -> None:
        target = ins.arg
        if not isinstance(target, tuple) or len(target) != 2:
            raise SwarnaRuntimeError(
                "Invalid CALL target",
                ins.span,
                hint="The bytecode compiler produced an invalid call.",
            )
        name, argument_count = target
        if not isinstance(name, str) or not isinstance(argument_count, int) or argument_count < 0:
            raise SwarnaRuntimeError(
                "Invalid CALL target",
                ins.span,
                hint="The bytecode compiler produced an invalid call.",
            )
        function = self.functions.get(name)
        if function is None:
            raise SwarnaNameError(
                f"Undefined function '{name}'",
                ins.span,
                hint="Declare it first with `fn name(...) { ... }`.",
            )
        if argument_count != len(function.parameters):
            raise SwarnaRuntimeError(
                f"Function '{name}' expects {len(function.parameters)} arguments, got {argument_count}",
                ins.span,
                hint="Pass the number of arguments in the function declaration.",
            )
        if len(self.stack) < argument_count:
            raise SwarnaRuntimeError(
                "Stack underflow on CALL",
                ins.span,
                hint="The bytecode compiler produced an invalid stack operation.",
            )
        arguments = [self._pop(ins) for _ in range(argument_count)]
        arguments.reverse()
        self.stack.append(self._call_function(function, arguments, ins))

    def _call_function(
        self,
        function: FunctionInfo,
        arguments: list[Value],
        call_ins: Instruction,
    ) -> Value:
        if self.call_depth >= self.max_call_depth:
            raise SwarnaRuntimeError(
                f"Maximum call depth of {self.max_call_depth} exceeded",
                call_ins.span,
                hint="Check for infinite recursion.",
            )
        saved_stack = self.stack
        saved_env = self.env
        saved_constant = self.constant
        local_env = dict(self.global_env)
        local_constant = set(self.global_constant)
        for parameter, value in zip(function.parameters, arguments):
            local_env[parameter] = value
            local_constant.discard(parameter)
        iterator_depth = len(self.iterators)
        self.stack = []
        self.env = local_env
        self.constant = local_constant
        self.call_depth += 1
        try:
            result = self._execute(function.instructions, allow_return=True)
            if result is None:
                raise SwarnaRuntimeError(
                    f"Function '{function.name}' did not return a value",
                    function.span,
                    hint="The bytecode compiler produced an invalid function.",
                )
            return result
        finally:
            self._cleanup_iterators(iterator_depth)
            self.call_depth -= 1
            self.stack = saved_stack
            self.env = saved_env
            self.constant = saved_constant

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
