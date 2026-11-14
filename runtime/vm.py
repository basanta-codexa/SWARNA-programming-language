from __future__ import annotations

import math
import operator
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Callable

from compiler.bytecode.instructions import Instruction, Op
from compiler.bytecode.program import CompiledProgram, FunctionInfo
from compiler.diagnostics import SwarnaNameError, SwarnaRuntimeError, SwarnaTypeError, SwarnaZeroDivisionError
from runtime.csv import read_csv_data
from runtime.files import read_text_file
from runtime.values import Value, format_literal, format_value, value_type_name


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
            elif ins.op == Op.MOD:
                b = self._pop(ins)
                a = self._pop(ins)
                if b == 0:
                    raise SwarnaZeroDivisionError(
                        "modulo by zero",
                        ins.span,
                        hint="The divisor must be non-zero.",
                    )
                try:
                    self.stack.append(a % b)
                except TypeError as e:
                    raise SwarnaTypeError(
                        str(e),
                        ins.span,
                        hint="The operands have incompatible types.",
                        category="type-mismatch",
                    ) from e
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
            elif ins.op == Op.BUILD_MAP:
                count = ins.arg
                if not isinstance(count, int) or count < 0:
                    raise SwarnaRuntimeError(
                        "Invalid BUILD_MAP count",
                        ins.span,
                        hint="The bytecode compiler produced an invalid map instruction.",
                    )
                if len(self.stack) < count * 2:
                    raise SwarnaRuntimeError(
                        "Stack underflow on BUILD_MAP",
                        ins.span,
                        hint="The bytecode compiler produced an invalid stack operation.",
                    )
                items = [self._pop(ins) for _ in range(count * 2)]
                items.reverse()
                result: dict[Value, Value] = {}
                for offset in range(0, count * 2, 2):
                    key, value = items[offset], items[offset + 1]
                    try:
                        hash(key)
                    except TypeError:
                        raise SwarnaTypeError(
                            f"Map keys must be Int, Float, String, or Bool, "
                            f"got {value_type_name(key)}",
                            ins.span,
                            hint="Use a scalar key.",
                        ) from None
                    result[key] = value
                self.stack.append(result)
            elif ins.op == Op.INDEX:
                index = self._pop(ins)
                collection = self._pop(ins)
                if isinstance(collection, dict):
                    try:
                        self.stack.append(collection[index])
                    except KeyError:
                        raise SwarnaRuntimeError(
                            f"Key {format_literal(index)} is not in the map",
                            ins.span,
                            hint="Check the key, or use a key that exists.",
                        ) from None
                    except TypeError:
                        raise SwarnaTypeError(
                            f"Map keys must be Int, Float, String, or Bool, "
                            f"got {value_type_name(index)}",
                            ins.span,
                            hint="Use a scalar key.",
                        ) from None
                elif isinstance(collection, str):
                    if type(index) is not int:
                        raise SwarnaTypeError(
                            "String index must be Int",
                            ins.span,
                            hint="Use an integer index, such as `text[0]`.",
                        )
                    try:
                        self.stack.append(collection[index])
                    except IndexError:
                        raise SwarnaRuntimeError(
                            f"Index {index} is out of range for a string of length {len(collection)}",
                            ins.span,
                            hint="Use an index from 0 to len(text) - 1, or a negative index from -len(text) to -1.",
                        ) from None
                elif isinstance(collection, list):
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
                else:
                    raise SwarnaTypeError(
                        f"Cannot index {value_type_name(collection)}",
                        ins.span,
                        hint="Only lists, maps, and strings can be indexed.",
                    )
            elif ins.op == Op.STORE_INDEX:
                value = self._pop(ins)
                index = self._pop(ins)
                collection = self._pop(ins)
                name = ins.arg
                if name in self.functions:
                    raise SwarnaNameError(
                        f"Cannot assign to function '{name}'",
                        ins.span,
                        hint="Call the function and assign its result to a variable.",
                    )
                if name not in self.env:
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
                if isinstance(collection, list):
                    raise SwarnaTypeError(
                        "Lists are immutable; cannot assign to an index",
                        ins.span,
                        hint="Build a new list with `+` instead.",
                    )
                if not isinstance(collection, dict):
                    raise SwarnaTypeError(
                        f"Cannot assign to {value_type_name(collection)}",
                        ins.span,
                        hint="Only maps support index assignment.",
                    )
                try:
                    collection[index] = value
                except TypeError:
                    raise SwarnaTypeError(
                        f"Map keys must be Int, Float, String, or Bool, "
                        f"got {value_type_name(index)}",
                        ins.span,
                        hint="Use a scalar key.",
                    ) from None
            elif ins.op == Op.MAP_GET:
                default = self._pop(ins)
                key = self._pop(ins)
                collection = self._pop(ins)
                if not isinstance(collection, dict):
                    raise SwarnaTypeError(
                        f"`get` expects a Map, got {value_type_name(collection)}",
                        ins.span,
                        hint="Pass a map as the first argument.",
                    )
                try:
                    if key in collection:
                        self.stack.append(collection[key])
                    else:
                        self.stack.append(default)
                except TypeError:
                    raise SwarnaTypeError(
                        f"Map keys must be Int, Float, String, or Bool, "
                        f"got {value_type_name(key)}",
                        ins.span,
                        hint="Use a scalar key.",
                    ) from None
            elif ins.op == Op.LEN:
                value = self._pop(ins)
                if isinstance(value, (list, dict, str)):
                    self.stack.append(len(value))
                else:
                    raise SwarnaTypeError(
                        f"`len` expects a List, Map, or String, got {value_type_name(value)}",
                        ins.span,
                        hint="Pass a list, map, or string to `len`.",
                    )
            elif ins.op == Op.READ_FILE:
                path = self._pop(ins)
                if type(path) is not str:
                    raise SwarnaTypeError(
                        f"`read_file` expects a String path, got {value_type_name(path)}",
                        ins.span,
                        hint='Pass a file path as a string, such as `read_file("notes.txt")`.',
                    )
                self.stack.append(read_text_file(path, ins.span))
            elif ins.op == Op.READ_CSV:
                path = self._pop(ins)
                if type(path) is not str:
                    raise SwarnaTypeError(
                        f"`read_csv` expects a String path, got {value_type_name(path)}",
                        ins.span,
                        hint='Pass a file path as a string, such as `read_csv("scores.csv", ...)`.',
                    )
                schema = ins.arg
                if not isinstance(schema, tuple):
                    raise SwarnaRuntimeError(
                        "Invalid READ_CSV schema",
                        ins.span,
                        hint="The bytecode compiler produced an invalid CSV instruction.",
                    )
                text = read_text_file(path, ins.span)
                self.stack.append(read_csv_data(text, path, schema))
            elif ins.op == Op.RANGE:
                arg_count = ins.arg
                if arg_count not in (1, 2, 3):
                    raise SwarnaRuntimeError(
                        "Invalid RANGE argument count",
                        ins.span,
                        hint="The bytecode compiler produced an invalid range instruction.",
                    )
                if len(self.stack) < arg_count:
                    raise SwarnaRuntimeError(
                        "Stack underflow on RANGE",
                        ins.span,
                        hint="The bytecode compiler produced an invalid stack operation.",
                    )
                values = [self._pop(ins) for _ in range(arg_count)]
                values.reverse()
                for value in values:
                    if type(value) is not int:
                        raise SwarnaTypeError(
                            f"`range` arguments must be Int, got {value_type_name(value)}",
                            ins.span,
                            hint="Use Int values for range bounds and step.",
                            category="type-mismatch",
                        )
                if arg_count == 1:
                    start, stop, step = 0, values[0], 1
                elif arg_count == 2:
                    start, stop, step = values[0], values[1], 1
                else:
                    start, stop, step = values[0], values[1], values[2]
                if step == 0:
                    raise SwarnaRuntimeError(
                        "`range` step must not be 0",
                        ins.span,
                        hint="Use a non-zero step, such as `1` or `-1`.",
                    )
                self.stack.append(list(range(start, stop, step)))
            elif ins.op == Op.INPUT:
                line = sys.stdin.readline()
                if line == "":
                    raise SwarnaRuntimeError(
                        "No input available",
                        ins.span,
                        hint="Provide input on stdin when using `input()`.",
                    )
                self.stack.append(line.rstrip("\r\n"))
            elif ins.op == Op.TO_INT:
                value = self._pop(ins)
                if type(value) is bool:
                    self.stack.append(1 if value else 0)
                elif type(value) is int:
                    self.stack.append(value)
                elif type(value) is float:
                    if not math.isfinite(value):
                        raise SwarnaRuntimeError(
                            f"Cannot convert non-finite Float {format_literal(value)} to Int",
                            ins.span,
                            hint="Convert only finite Float values to Int.",
                            category="type-mismatch",
                        )
                    self.stack.append(int(value))
                elif type(value) is str:
                    text = value.strip()
                    try:
                        self.stack.append(int(text))
                    except ValueError:
                        raise SwarnaRuntimeError(
                            f"Cannot convert String {format_literal(value)} to Int",
                            ins.span,
                            hint='Use an explicit whole-number string such as "42" (decimal integer form).',
                            category="type-mismatch",
                        ) from None
                else:
                    raise SwarnaTypeError(
                        f"Cannot convert {value_type_name(value)} to Int",
                        ins.span,
                        hint="Use `int(...)` with an Int, Float, Bool, or whole-number String.",
                        category="type-mismatch",
                    )
            elif ins.op == Op.TO_FLOAT:
                value = self._pop(ins)
                if type(value) is bool:
                    result = 1.0 if value else 0.0
                elif type(value) is int:
                    result = float(value)
                elif type(value) is float:
                    result = value
                elif type(value) is str:
                    text = value.strip()
                    try:
                        result = float(text)
                    except ValueError:
                        raise SwarnaRuntimeError(
                            f"Cannot convert String {format_literal(value)} to Float",
                            ins.span,
                            hint='Use a finite numeric string such as "3.14" or "1e3", or convert explicitly with the appropriate form.',
                            category="type-mismatch",
                        ) from None
                else:
                    raise SwarnaTypeError(
                        f"Cannot convert {value_type_name(value)} to Float",
                        ins.span,
                        hint="Use `float(...)` with an Int, Float, Bool, or numeric String.",
                        category="type-mismatch",
                    )
                if not math.isfinite(result):
                    raise SwarnaRuntimeError(
                        f"Cannot convert {value_type_name(value)} {format_literal(value)} to a finite Float",
                        ins.span,
                        hint="SWARNA `Float` values must be finite. Use a finite numeric value.",
                        category="type-mismatch",
                    )
                self.stack.append(result)
            elif ins.op == Op.TO_STR:
                value = self._pop(ins)
                self.stack.append(format_value(value))
            elif ins.op == Op.ITER_START:
                iterable = self._pop(ins)
                if not isinstance(iterable, (list, dict, str)):
                    raise SwarnaTypeError(
                        f"`for` expects a List, Map, or String, got {value_type_name(iterable)}",
                        ins.span,
                        hint="Use a list, map, or string after `in`.",
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
            elif ins.op == Op.ITER_END:
                if not self.iterators:
                    raise SwarnaRuntimeError(
                        "ITER_END without ITER_START",
                        ins.span,
                        hint="The bytecode compiler produced an invalid for loop.",
                    )
                self._restore_for_frame(self.iterators.pop())
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
        param_anns = getattr(function, "parameter_annotations", ())
        coerced = []
        for index, value in enumerate(arguments):
            ann = param_anns[index] if index < len(param_anns) else None
            if ann is not None and ann.name == "Float" and not ann.arguments and type(value) is int:
                coerced.append(float(value))
            else:
                coerced.append(value)
        self.stack.append(self._call_function(function, coerced, ins))

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
            ret_ann = getattr(function, "return_annotation", None)
            if ret_ann is not None and ret_ann.name == "Float" and not ret_ann.arguments and type(result) is int:
                result = float(result)
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
