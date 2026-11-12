from __future__ import annotations

from dataclasses import dataclass


UNDEFINED_NAME_EXPLANATION = (
    "The program used a name that has not been declared yet. Create the name "
    "with `let name = value` (mutable) or `const name = value` (immutable) "
    "before the line that uses it. Function parameters and `for` loop variables "
    "are also names. Functions are hoisted, so they can be called before their "
    "declaration; variables cannot."
)


@dataclass(frozen=True)
class SourceSpan:
    """A location in source text. Lines and columns are 1-based."""

    line: int
    column: int
    length: int = 1


class DiagnosticError(Exception):
    """A user-facing error with an optional source span and suggested fix."""

    def __init__(
        self,
        message: str,
        span: SourceSpan | None = None,
        hint: str | None = None,
        explanation: str | None = None,
    ):
        self.message = message
        self.span = span
        self.hint = hint
        self.explanation = explanation
        super().__init__(self._format())

    def _format(self) -> str:
        if self.span is None:
            return self.message
        return f"{self.message} at line {self.span.line}, column {self.span.column}"


class SwarnaSyntaxError(DiagnosticError, SyntaxError):
    """A syntax diagnostic that remains catchable as a built-in SyntaxError."""


class SwarnaSemanticError(DiagnosticError):
    """A compile-time semantic diagnostic."""


class SwarnaRuntimeError(DiagnosticError, RuntimeError):
    """A runtime diagnostic that remains catchable as a built-in RuntimeError."""


class SwarnaNameError(SwarnaRuntimeError, NameError):
    """An undefined-name diagnostic that remains catchable as a built-in NameError."""


class SwarnaTypeError(SwarnaRuntimeError, TypeError):
    """A type diagnostic that remains catchable as a built-in TypeError."""


class SwarnaZeroDivisionError(SwarnaRuntimeError, ZeroDivisionError):
    """A division-by-zero diagnostic that remains catchable as a built-in ZeroDivisionError."""


def render_diagnostic(source: str, error: DiagnosticError, explain: bool = False) -> str:
    """Render a diagnostic with the offending line, a caret, and its hint.

    When ``explain`` is true and the error carries an explanation, the
    explanation is appended below the hint.
    """

    def with_explanation(lines: list[str]) -> str:
        if explain and error.explanation:
            lines.append(f"  = why: {error.explanation}")
        return "\n".join(lines)

    if error.span is None:
        lines = [f"error: {error.message}"]
        if error.hint:
            lines.append(f"  hint: {error.hint}")
        return with_explanation(lines)

    source_lines = source.splitlines() or [""]
    line_no = max(1, error.span.line)
    if line_no > len(source_lines):
        line_no = len(source_lines)
        column = len(source_lines[-1]) + 1
        length = 1
    else:
        column = max(1, error.span.column)
        length = max(1, error.span.length)

    source_line = source_lines[line_no - 1]
    column = min(column, len(source_line) + 1)
    caret_start = column - 1
    caret_length = min(length, max(1, len(source_line) - caret_start))
    caret = " " * caret_start + "^" * caret_length
    gutter = len(str(line_no))

    lines = [
        f"error: {error.message}",
        f"  --> {line_no}:{column}",
        f"  {' ' * gutter} |",
        f"  {line_no:>{gutter}} | {source_line}",
        f"  {' ' * gutter} | {caret}",
    ]
    if error.hint:
        lines.append(f"  {' ' * gutter} = hint: {error.hint}")
    return with_explanation(lines)
