import unittest

from compiler.diagnostics import SourceSpan, SwarnaRuntimeError, render_diagnostic
from runtime.csv import parse_csv, read_csv_data


SCHEMA = (("name", "String"), ("team", "String"), ("score", "Float"))


class TestParseCsv(unittest.TestCase):
    def test_parses_rows_and_tracks_positions(self):
        rows = parse_csv("a,b\n1,2\n")
        self.assertEqual(len(rows), 2)
        self.assertEqual([field.value for field in rows[0].fields], ["a", "b"])
        self.assertEqual(
            [(field.line, field.column, field.length) for field in rows[0].fields],
            [(1, 1, 1), (1, 3, 1)],
        )
        self.assertEqual(
            [(field.line, field.column) for field in rows[1].fields],
            [(2, 1), (2, 3)],
        )

    def test_quoted_field_with_comma(self):
        rows = parse_csv('x,"a,b",y\n')
        self.assertEqual(
            [field.value for field in rows[0].fields],
            ["x", "a,b", "y"],
        )
        self.assertEqual((rows[0].fields[1].column, rows[0].fields[1].length), (3, 5))

    def test_escaped_quotes(self):
        rows = parse_csv('"a""b",c\n')
        self.assertEqual([field.value for field in rows[0].fields], ['a"b', "c"])

    def test_newline_inside_quoted_field(self):
        rows = parse_csv('"a\nb",c\n')
        self.assertEqual([field.value for field in rows[0].fields], ["a\nb", "c"])
        self.assertEqual(
            [(field.line, field.column) for field in rows[0].fields],
            [(1, 1), (2, 4)],
        )

    def test_crlf_line_endings(self):
        rows = parse_csv("a,b\r\n1,2\r\n")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1].line, 2)
        self.assertEqual([field.value for field in rows[1].fields], ["1", "2"])

    def test_trailing_comma_makes_empty_field(self):
        rows = parse_csv("a,b,\n")
        self.assertEqual([field.value for field in rows[0].fields], ["a", "b", ""])
        self.assertEqual(rows[0].fields[2].column, 5)

    def test_blank_lines_are_skipped(self):
        rows = parse_csv("\n\na,b\n\n1,2\n")
        self.assertEqual([row.line for row in rows], [3, 5])

    def test_unterminated_quote_reports_start(self):
        with self.assertRaises(SwarnaRuntimeError) as raised:
            parse_csv('"a,b\n')
        self.assertEqual(raised.exception.span, SourceSpan(1, 1, 1))
        self.assertIn("Unterminated quoted field", raised.exception.message)


class TestReadCsvData(unittest.TestCase):
    def test_converts_values_by_schema(self):
        text = "name,team,score\nAda,Blue,88\nGrace,Blue,92.5\n"
        rows = read_csv_data(text, "scores.csv", SCHEMA)
        self.assertEqual(
            rows,
            [
                {"name": "Ada", "team": "Blue", "score": 88.0},
                {"name": "Grace", "team": "Blue", "score": 92.5},
            ],
        )

    def test_header_columns_can_be_in_any_order(self):
        text = "score,name,team\n88,Ada,Blue\n"
        rows = read_csv_data(text, "scores.csv", SCHEMA)
        self.assertEqual(rows, [{"name": "Ada", "team": "Blue", "score": 88.0}])

    def test_int_bool_and_string_columns(self):
        schema = (("id", "Int"), ("active", "Bool"), ("note", "String"))
        text = "id,active,note\n1,true,hello\n2,false,\n"
        rows = read_csv_data(text, "data.csv", schema)
        self.assertEqual(
            rows,
            [
                {"id": 1, "active": True, "note": "hello"},
                {"id": 2, "active": False, "note": ""},
            ],
        )

    def test_bad_float_names_file_row_column_and_value(self):
        text = (
            "name,team,score\n"
            "Ada,Blue,88\n"
            "Grace,Blue,92\n"
            "Linus,Red,79\n"
            "Margaret,Red,n/a\n"
        )
        with self.assertRaises(SwarnaRuntimeError) as raised:
            read_csv_data(text, "scores.csv", SCHEMA)
        error = raised.exception
        self.assertEqual(error.span, SourceSpan(5, 14, 3))
        self.assertIn("expected a Float in column 'score'", error.message)
        self.assertIn("got 'n/a'", error.message)
        self.assertEqual(error.source, text)
        self.assertEqual(error.source_name, "scores.csv")
        self.assertIn("Replace 'n/a' with a number", error.hint or "")
        rendered = render_diagnostic("program", error)
        self.assertIn("--> scores.csv:5:14", rendered)
        self.assertIn("Margaret,Red,n/a", rendered)
        self.assertIn("^^^", rendered)

    def test_bad_int_is_reported(self):
        schema = (("id", "Int"),)
        with self.assertRaisesRegex(RuntimeError, "expected an Int in column 'id'"):
            read_csv_data("id\n4.2\n", "data.csv", schema)

    def test_empty_numeric_value_is_reported(self):
        text = "name,team,score\nAda,Blue,\n"
        with self.assertRaisesRegex(RuntimeError, "got an empty value"):
            read_csv_data(text, "scores.csv", SCHEMA)

    def test_bad_bool_is_reported(self):
        schema = (("active", "Bool"),)
        with self.assertRaisesRegex(RuntimeError, "expected a Bool in column 'active'"):
            read_csv_data("active\nyes\n", "data.csv", schema)

    def test_header_missing_column(self):
        with self.assertRaisesRegex(RuntimeError, "missing column 'score'"):
            read_csv_data("name,team\nAda,Blue\n", "scores.csv", SCHEMA)

    def test_header_unexpected_column(self):
        with self.assertRaisesRegex(RuntimeError, "unexpected column 'extra'"):
            read_csv_data(
                "name,team,score,extra\nAda,Blue,88,x\n",
                "scores.csv",
                SCHEMA,
            )

    def test_header_duplicate_column(self):
        with self.assertRaisesRegex(RuntimeError, "repeats column 'team'"):
            read_csv_data(
                "name,team,team,score\nAda,Blue,Blue,88\n",
                "scores.csv",
                SCHEMA,
            )

    def test_row_with_wrong_column_count(self):
        with self.assertRaisesRegex(RuntimeError, "CSV row has 2 columns; expected 3"):
            read_csv_data(
                "name,team,score\nAda,Blue\n",
                "scores.csv",
                SCHEMA,
            )

    def test_header_only_returns_no_rows(self):
        self.assertEqual(read_csv_data("name,team,score\n", "scores.csv", SCHEMA), [])

    def test_empty_file_is_reported(self):
        with self.assertRaisesRegex(RuntimeError, "is empty"):
            read_csv_data("", "scores.csv", SCHEMA)


if __name__ == "__main__":
    unittest.main()
