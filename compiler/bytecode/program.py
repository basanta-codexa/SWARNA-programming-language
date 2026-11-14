from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from compiler.ast.nodes import TypeAnnotation
from compiler.bytecode.instructions import Instruction
from compiler.diagnostics import SourceSpan


@dataclass(frozen=True)
class FunctionInfo:
    name: str
    parameters: tuple[str, ...]
    instructions: tuple[Instruction, ...]
    span: SourceSpan | None = None
    parameter_annotations: tuple[TypeAnnotation | None, ...] = ()
    return_annotation: TypeAnnotation | None = None


@dataclass(frozen=True)
class CompiledProgram:
    instructions: tuple[Instruction, ...]
    functions: dict[str, FunctionInfo] = field(default_factory=dict)

    def __iter__(self) -> Iterator[Instruction]:
        return iter(self.instructions)

    def __len__(self) -> int:
        return len(self.instructions)

    def __getitem__(self, index: int) -> Instruction:
        return self.instructions[index]
