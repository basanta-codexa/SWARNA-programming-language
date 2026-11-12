from __future__ import annotations


Value = int | float | bool | str | list["Value"] | dict["Value", "Value"]


def value_type_name(value: Value) -> str:
    """Return the user-facing name of a runtime value's type."""

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


def format_value(value: Value) -> str:
    """Format a value for print output."""

    if type(value) is bool:
        return "true" if value else "false"
    if isinstance(value, list):
        return "[" + ", ".join(_format_item(item) for item in value) + "]"
    if isinstance(value, dict):
        return (
            "{"
            + ", ".join(
                f"{_format_item(key)}: {_format_item(item)}"
                for key, item in value.items()
            )
            + "}"
        )
    return str(value)


def format_literal(value: Value) -> str:
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
    return format_value(value)


def _format_item(value: Value) -> str:
    return format_literal(value)
