import unittest

from runtime.values import format_literal, format_value, value_type_name


class TestValueFormatting(unittest.TestCase):
    def test_format_value_keeps_top_level_strings_bare(self):
        self.assertEqual(format_value("hi"), "hi")

    def test_format_literal_quotes_strings(self):
        self.assertEqual(format_literal("hi"), '"hi"')

    def test_format_literal_escapes_quotes_and_newlines(self):
        self.assertEqual(format_literal('a"b\nc'), '"a\\"b\\nc"')

    def test_format_literal_formats_other_values(self):
        self.assertEqual(format_literal(1), "1")
        self.assertEqual(format_literal(True), "true")
        self.assertEqual(format_literal([1, "a"]), '[1, "a"]')

    def test_format_value_formats_map_with_quoted_string_keys(self):
        self.assertEqual(format_value({"a": 1}), '{"a": 1}')

    def test_value_type_name_for_maps(self):
        self.assertEqual(value_type_name({}), "Map")


if __name__ == "__main__":
    unittest.main()
