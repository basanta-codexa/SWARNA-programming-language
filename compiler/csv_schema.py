from __future__ import annotations

from dataclasses import dataclass

from compiler.ast.nodes import Expression, Identifier, MapLiteral, StringLiteral
from compiler.diagnostics import SourceSpan


COLUMN_TYPES = frozenset({"Int", "Float", "String", "Bool"})


@dataclass(frozen=True)
class CsvColumn:
    name: str
    type_name: str


class CsvSchemaError(Exception):
    """A schema literal that `read_csv` cannot use."""

    def __init__(self, message: str, span: SourceSpan | None, hint: str):
        self.message = message
        self.span = span
        self.hint = hint
        super().__init__(message)


def parse_csv_schema(argument: Expression) -> tuple[CsvColumn, ...]:
    """Read a schema literal such as `{ name: String, score: Float }`."""

    if not isinstance(argument, MapLiteral):
        raise CsvSchemaError(
            "`read_csv` expects a schema literal as its second argument",
            argument.span,
            "Write the schema as `{ name: String, score: Float }`.",
        )
    if not argument.entries:
        raise CsvSchemaError(
            "`read_csv` schema must declare at least one column",
            argument.span,
            "Add a column such as `{ name: String }`.",
        )

    columns: list[CsvColumn] = []
    seen: set[str] = set()
    for key, value in argument.entries:
        name = _column_name(key)
        if name is None:
            raise CsvSchemaError(
                "Schema column names must be identifiers or strings",
                key.span,
                "Write a column as `name: String`.",
            )
        if name in seen:
            raise CsvSchemaError(
                f"Schema repeats column '{name}'",
                key.span,
                "Give each column a unique name.",
            )
        if not isinstance(value, Identifier):
            raise CsvSchemaError(
                f"Column '{name}' needs a type",
                value.span,
                "Use `Int`, `Float`, `String`, or `Bool`.",
            )
        if value.name not in COLUMN_TYPES:
            raise CsvSchemaError(
                f"Unknown column type '{value.name}' for column '{name}'",
                value.span,
                "Use `Int`, `Float`, `String`, or `Bool`.",
            )
        seen.add(name)
        columns.append(CsvColumn(name=name, type_name=value.name))
    return tuple(columns)


def _column_name(key: Expression) -> str | None:
    if isinstance(key, Identifier):
        return key.name
    if isinstance(key, StringLiteral):
        return key.value
    return None
