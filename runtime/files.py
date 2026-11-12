from __future__ import annotations

from pathlib import Path

from compiler.diagnostics import SourceSpan, SwarnaRuntimeError
from runtime.values import format_literal


def read_text_file(path: str, span: SourceSpan | None) -> str:
    """Read a UTF-8 text file, converting host errors into SWARNA diagnostics."""

    file_path = Path(path)
    if file_path.is_dir():
        raise SwarnaRuntimeError(
            f"Could not read file {format_literal(path)}: it is a directory",
            span,
            hint="Pass the path of a text file, not a directory.",
        )
    try:
        return file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SwarnaRuntimeError(
            f"Could not read file {format_literal(path)}: file not found",
            span,
            hint="Check the path, or create the file before running the program.",
        ) from None
    except PermissionError:
        raise SwarnaRuntimeError(
            f"Could not read file {format_literal(path)}: permission denied",
            span,
            hint="Check that the file is readable.",
        ) from None
    except UnicodeDecodeError:
        raise SwarnaRuntimeError(
            f"Could not read file {format_literal(path)}: it is not valid UTF-8 text",
            span,
            hint="Save the file as UTF-8 and try again.",
        ) from None
    except OSError as error:
        raise SwarnaRuntimeError(
            f"Could not read file {format_literal(path)}: {error.strerror or error}",
            span,
            hint="Check the path and that the file is readable.",
        ) from None
