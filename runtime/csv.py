from __future__ import annotations

from dataclasses import dataclass

from compiler.diagnostics import SourceSpan, SwarnaRuntimeError
from runtime.values import Value


COLUMN_TYPES = frozenset({"Int", "Float", "String", "Bool"})


@dataclass(frozen=True)
class CsvField:
    """A raw CSV field and the location of its text in the file."""

    value: str
    line: int
    column: int
    length: int


@dataclass(frozen=True)
class CsvRow:
    fields: list[CsvField]
    line: int


def parse_csv(text: str) -> list[CsvRow]:
    """Parse comma-separated text, keeping each field's source location.

    The parser handles quoted fields, escaped quotes, embedded newlines, and
    both LF and CRLF line endings. Blank lines are skipped.
    """

    rows: list[CsvRow] = []
    fields: list[CsvField] = []
    value: list[str] = []
    in_quotes = False
    field_start: tuple[int, int] | None = None
    field_raw_length = 0
    row_start_line: int | None = None

    line = 1
    column = 1
    index = 0
    text_length = len(text)

    def start_field() -> None:
        nonlocal field_start, row_start_line
        if field_start is None:
            field_start = (line, column)
            if row_start_line is None:
                row_start_line = line

    def finish_field() -> None:
        nonlocal field_start, field_raw_length, row_start_line
        if field_start is None:
            field_start = (line, column)
            if row_start_line is None:
                row_start_line = line
        fields.append(
            CsvField(
                value="".join(value),
                line=field_start[0],
                column=field_start[1],
                length=max(1, field_raw_length),
            )
        )
        value.clear()
        field_start = None
        field_raw_length = 0

    def finish_row() -> None:
        nonlocal row_start_line
        if field_start is None and not fields:
            return
        finish_field()
        rows.append(CsvRow(fields=list(fields), line=row_start_line or line))
        fields.clear()
        row_start_line = None

    while index < text_length:
        char = text[index]

        if in_quotes:
            if char == '"':
                if index + 1 < text_length and text[index + 1] == '"':
                    value.append('"')
                    index += 2
                    column += 2
                    field_raw_length += 2
                else:
                    in_quotes = False
                    index += 1
                    column += 1
                    field_raw_length += 1
            else:
                value.append(char)
                index += 1
                field_raw_length += 1
                if char == "\n":
                    line += 1
                    column = 1
                else:
                    column += 1
            continue

        if char == '"':
            start_field()
            in_quotes = True
            index += 1
            column += 1
            field_raw_length += 1
            continue

        if char == ",":
            start_field()
            finish_field()
            index += 1
            column += 1
            continue

        if char in ("\r", "\n"):
            finish_row()
            if char == "\r" and index + 1 < text_length and text[index + 1] == "\n":
                index += 2
            else:
                index += 1
            line += 1
            column = 1
            continue

        start_field()
        value.append(char)
        index += 1
        column += 1
        field_raw_length += 1

    if in_quotes:
        start_line, start_column = field_start or (line, column)
        raise SwarnaRuntimeError(
            "Unterminated quoted field in CSV data",
            SourceSpan(start_line, start_column, 1),
            hint="Add a closing double quote.",
            source=text,
        )

    finish_row()
    return rows


def read_csv_data(
    text: str,
    path: str,
    schema: tuple[tuple[str, str], ...],
) -> list[dict[str, Value]]:
    """Validate CSV text against a schema and return typed rows."""

    rows = parse_csv(text)
    if not rows:
        raise SwarnaRuntimeError(
            f"CSV file {_quoted(path)} is empty",
            SourceSpan(1, 1, 1),
            hint="Add a header row and at least one data row.",
            source=text,
            source_name=path,
        )

    header = rows[0]
    header_names = [field.value for field in header.fields]
    _check_header(header_names, schema, text, path)

    header_index = {name: index for index, name in enumerate(header_names)}
    typed_rows: list[dict[str, Value]] = []
    for row in rows[1:]:
        if len(row.fields) != len(header_names):
            raise SwarnaRuntimeError(
                f"CSV row has {len(row.fields)} columns; expected {len(header_names)}",
                SourceSpan(row.line, 1, 1),
                hint="Check for a missing or extra comma in this row.",
                source=text,
                source_name=path,
            )
        typed_row: dict[str, Value] = {}
        for column, type_name in schema:
            field = row.fields[header_index[column]]
            typed_row[column] = _convert_field(field, column, type_name, text, path)
        typed_rows.append(typed_row)
    return typed_rows


def _check_header(
    header_names: list[str],
    schema: tuple[tuple[str, str], ...],
    text: str,
    path: str,
) -> None:
    seen: set[str] = set()
    for field in header_names:
        if field in seen:
            raise SwarnaRuntimeError(
                f"CSV header repeats column {_quoted(field)}",
                SourceSpan(1, 1, 1),
                hint="Give each column a unique name.",
                source=text,
                source_name=path,
            )
        seen.add(field)

    expected = [column for column, _ in schema]
    for column in expected:
        if column not in seen:
            raise SwarnaRuntimeError(
                f"CSV header is missing column {_quoted(column)}",
                SourceSpan(1, 1, 1),
                hint="Add the column to the header, or remove it from the schema.",
                source=text,
                source_name=path,
            )
    for column in header_names:
        if column not in expected:
            raise SwarnaRuntimeError(
                f"CSV header has unexpected column {_quoted(column)}",
                SourceSpan(1, 1, 1),
                hint="Remove the column from the header, or add it to the schema.",
                source=text,
                source_name=path,
            )


def _convert_field(
    field: CsvField,
    column: str,
    type_name: str,
    text: str,
    path: str,
) -> Value:
    raw = field.value
    span = SourceSpan(field.line, field.column, field.length)

    if type_name == "String":
        return raw

    if raw == "":
        raise SwarnaRuntimeError(
            f"expected {_expected(type_name)} in column {_quoted(column)}, got an empty value",
            span,
            hint=f"Fill in {_expected(type_name)} value, or mark the row as missing.",
            source=text,
            source_name=path,
        )

    if type_name == "Int":
        try:
            return int(raw)
        except ValueError:
            pass
    elif type_name == "Float":
        try:
            return float(raw)
        except ValueError:
            pass
    elif type_name == "Bool":
        lowered = raw.strip().lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False

    raise SwarnaRuntimeError(
        f"expected {_expected(type_name)} in column {_quoted(column)}, "
        f"got {_quoted(raw)}",
        span,
        hint=_value_hint(type_name, raw),
        source=text,
        source_name=path,
    )


def _quoted(text: str) -> str:
    escaped = (
        text.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )
    return f"'{escaped}'"


def _expected(type_name: str) -> str:
    return "an Int" if type_name == "Int" else f"a {type_name}"


def _value_hint(type_name: str, raw: str) -> str:
    if type_name == "Int":
        return f"Replace {_quoted(raw)} with a whole number, or mark the row as missing."
    if type_name == "Float":
        return f"Replace {_quoted(raw)} with a number, or mark the row as missing."
    if type_name == "Bool":
        return f"Replace {_quoted(raw)} with `true` or `false`, or mark the row as missing."
    return "Fix the value, or mark the row as missing."
