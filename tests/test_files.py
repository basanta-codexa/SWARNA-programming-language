import json
import tempfile
import unittest
from pathlib import Path

from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from runtime.files import read_text_file
from runtime.interpreter import Interpreter


class TestFileEncoding(unittest.TestCase):
    def test_bom_is_stripped_from_text_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.txt"
            path.write_bytes(b"\xef\xbb\xbfhello\n")
            self.assertEqual(read_text_file(path.as_posix(), None), "hello\n")

    def test_bom_is_stripped_from_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scores.csv"
            path.write_bytes(b"\xef\xbb\xbfname,score\nalice,10\n")
            source = (
                f"let rows = read_csv({json.dumps(path.as_posix())}, "
                '{ name: String, score: Int })'
                ' print(rows[0]["name"])'
            )
            interpreter = Interpreter()
            interpreter.eval(Parser(Lexer(source)).parse_program())
            self.assertEqual(interpreter.output, ["alice"])


if __name__ == "__main__":
    unittest.main()
