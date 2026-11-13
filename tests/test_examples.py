import os
import unittest
from pathlib import Path

from compiler.codegen.compiler import Compiler
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.checker import TypeChecker
from runtime.interpreter import Interpreter
from runtime.vm import VM
from swarna.__main__ import run_source


ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "team_averages.sw"


class TestExamples(unittest.TestCase):
    def _in_repo(self, function):
        previous = os.getcwd()
        os.chdir(ROOT)
        try:
            return function()
        finally:
            os.chdir(previous)

    def test_team_averages_prints_averages(self):
        output = self._in_repo(
            lambda: run_source(EXAMPLE.read_text(encoding="utf-8"))
        )
        self.assertEqual(output, '{"Blue": 90.0, "Red": 82.0}')

    def test_team_averages_vm_matches_interpreter(self):
        def run_both():
            program = Parser(Lexer(EXAMPLE.read_text(encoding="utf-8"))).parse_program()
            TypeChecker().check(program)
            interpreted = Interpreter().eval(program)
            compiled = Compiler().compile(program)
            return interpreted, VM().run(compiled)

        interpreted, virtual = self._in_repo(run_both)
        self.assertEqual(interpreted["averages"], {"Blue": 90.0, "Red": 82.0})
        self.assertEqual(virtual["averages"], interpreted["averages"])
