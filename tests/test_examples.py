import os
import unittest
from pathlib import Path

from compiler.codegen.compiler import Compiler
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.checker import TypeChecker
from runtime.interpreter import Interpreter
from runtime.values import format_value
from runtime.vm import VM
from swarna.__main__ import run_source


ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "team_averages.sw"
TOUR = ROOT / "examples" / "language_tour.sw"


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

    def test_language_tour_prints_report(self):
        output = self._in_repo(
            lambda: run_source(TOUR.read_text(encoding="utf-8"))
        )
        self.assertEqual(
            output,
            "\n".join(
                [
                    "Grade report",
                    "ADA: A",
                    "Ada scored 92",
                    "Grace scored 85",
                    "Linus scored 77",
                    "[85, 77]",
                    "254",
                    "Skipped: missing submission",
                    "Done",
                ]
            ),
        )

    def test_language_tour_vm_matches_interpreter(self):
        def run_both():
            program = Parser(Lexer(TOUR.read_text(encoding="utf-8"))).parse_program()
            checker = TypeChecker()
            checker.check(program)
            interpreter = Interpreter()
            interpreted = interpreter.eval(program, checker.expression_types)
            vm = VM()
            virtual = vm.run(Compiler(checker.expression_types).compile(program))
            interpreter_output = [format_value(v) for v in interpreter.output]
            vm_output = [format_value(v) for v in vm.output]
            return interpreted, virtual, interpreter_output, vm_output

        interpreted, virtual, interpreter_output, vm_output = self._in_repo(run_both)
        self.assertEqual(interpreter_output, vm_output)
        self.assertEqual(virtual, interpreted)
        self.assertEqual(
            interpreted["results"],
            {"Ada": 92, "Grace": 85, "Linus": 77},
        )
