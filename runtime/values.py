from __future__ import annotations

import math

from compiler.ast.nodes import TypeAnnotation
from compiler.diagnostics import MAX_INT_DIGITS, SwarnaRuntimeError


class _UnitValue:
    __slots__ = ()

    def __repr__(self) -> str:
        return "UNIT"


UNIT = _UnitValue()

Value = int | float | bool | str | list["Value"] | dict["Value", "Value"] | _UnitValue

CYCLE_MARKER = "<cycle>"


def coerce_to_annotation(value: Value, annotation: TypeAnnotation | None) -> Value:
    """Apply the runtime coercions promised by an explicit annotation."""

    if annotation is None:
        return value
    if annotation.name == "Float" and not annotation.arguments:
        return float(value) if type(value) is int else value
    if annotation.name == "List" and len(annotation.arguments) == 1 and isinstance(value, list):
        element_annotation = annotation.arguments[0]
        return [coerce_to_annotation(item, element_annotation) for item in value]
    if annotation.name == "Map" and len(annotation.arguments) == 2 and isinstance(value, dict):
        key_annotation, value_annotation = annotation.arguments
        return {
            coerce_to_annotation(key, key_annotation): coerce_to_annotation(item, value_annotation)
            for key, item in value.items()
        }
    return value


def _int_digit_count(value: int) -> int:
    """Approximate decimal digits without converting the integer to a string."""
    if value == 0:
        return 1
    return int(abs(value).bit_length() * math.log10(2)) + 1


def value_type_name(value: Value) -> str:
    """Return the user-facing name of a runtime value's type."""

    if value is UNIT:
        return "Unit"
    if type(value) is bool:
        return "Bool"
    if type(value) is int:
        return "Int"
    if type(value) is float:
        return "Float"
    if type(value) is str:
        return "String"
    if isinstance(value, list):
        return "List"
    if isinstance(value, dict):
        return "Map"
    return type(value).__name__


def format_value(value: Value, *, _seen: set[int] | None = None) -> str:
    """Format a value for print output, marking cycles instead of recursing."""

    if value is UNIT:
        return "()"
    if type(value) is bool:
        return "true" if value else "false"
    if isinstance(value, (list, dict)):
        if _seen is None:
            _seen = set()
        marker = id(value)
        if marker in _seen:
            return CYCLE_MARKER
        _seen.add(marker)
        try:
            if isinstance(value, list):
                return "[" + ", ".join(_format_item(item, _seen) for item in value) + "]"
            return (
                "{"
                + ", ".join(
                    f"{_format_item(key, _seen)}: {_format_item(item, _seen)}"
                    for key, item in value.items()
                )
                + "}"
            )
        finally:
            _seen.discard(marker)
    if type(value) is int:
        try:
            if _int_digit_count(value) > MAX_INT_DIGITS:
                raise ValueError("too many digits")
            return str(value)
        except ValueError:
            raise SwarnaRuntimeError(
                "Integer value is too large to print",
                hint="Use a shorter value, or build and print it in smaller parts.",
            ) from None
    return str(value)


def format_literal(value: Value, *, _seen: set[int] | None = None) -> str:
    """Format a value as source-like text, quoting strings.

    Use this in diagnostics, where `Key "missing"` reads better than
    `Key missing`. `format_value` keeps top-level strings bare for `print`.
    """

    if type(value) is str:
        escaped = (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\t", "\\t")
        )
        return f'"{escaped}"'
    return format_value(value, _seen=_seen)


def _format_item(value: Value, seen: set[int] | None = None) -> str:
    return format_literal(value, _seen=seen)
