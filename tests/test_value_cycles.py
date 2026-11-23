import io
import unittest
from contextlib import redirect_stderr, redirect_stdout

from runtime.values import format_literal, format_value
from swarna.__main__ import main


class TestCyclicValueFormatting(unittest.TestCase):
    def test_self_cyclic_map(self):
        value = {}
        value["self"] = value
        self.assertEqual(format_value(value), '{"self": <cycle>}')

    def test_cycle_through_list(self):
        value = {}
        value["xs"] = [value]
        self.assertEqual(format_value(value), '{"xs": [<cycle>]}')

    def test_repeated_non_cyclic_alias_is_still_expanded(self):
        shared = [1]
        value = {"a": shared, "b": shared}
        self.assertEqual(format_value(value), '{"a": [1], "b": [1]}')

    def test_format_literal_handles_cycles(self):
        value = {}
        value["self"] = value
        self.assertEqual(format_literal(value), '{"self": <cycle>}')

    def test_cli_prints_cycle_without_crashing(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = main(["--run", 'let m = {} m["self"] = m print(m)'])
        self.assertEqual(status, 0)
        self.assertEqual(stdout.getvalue().strip(), '{"self": <cycle>}')
        self.assertNotIn("Traceback", stderr.getvalue())
