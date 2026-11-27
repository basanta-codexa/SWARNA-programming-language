"""Generic table-driven parity checks for the interpreter and the VM.

``run_both_engines`` is the reusable harness: it parses and type-checks a
source string once, runs both backends with the same inferred type map, and
returns their printed output and final environments. Error-path parity is
still covered by ``tests/test_engine_parity.py``.
"""

import unittest
from typing import NamedTuple

from compiler.codegen.compiler import Compiler
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.checker import TypeChecker
from runtime.interpreter import Interpreter
from runtime.vm import VM
from runtime.values import format_value


class EngineResult(NamedTuple):
    interpreter_output: list[str]
    vm_output: list[str]
    interpreter_env: dict[str, object]
    vm_env: dict[str, object]


def run_both_engines(source: str) -> EngineResult:
    """Run the same checked program through both engines and collect results."""

    program = Parser(Lexer(source)).parse_program()
    checker = TypeChecker()
    checker.check(program)

    interpreter = Interpreter()
    interpreter_env = interpreter.eval(program, checker.expression_types)
    interpreter_output = [format_value(value) for value in interpreter.output]

    vm = VM()
    vm_env = vm.run(Compiler(checker.expression_types).compile(program))
    vm_output = [format_value(value) for value in vm.output]

    return EngineResult(
        interpreter_output=interpreter_output,
        vm_output=vm_output,
        interpreter_env=interpreter_env,
        vm_env=vm_env,
    )


CASES: dict[str, str] = {
    "arithmetic_and_widening": (
        "let x = 1 + 2 let y = 1 / 2 "
        "let z: Float = 3 print(x) print(y) print(z)"
    ),
    "strings_and_slices": (
        'let s = "hello" print(upper(s)) print(lower(s)) '
        'print(s[1:3]) print(contains(s, "ell")) print(split("a,b", ","))'
    ),
    "list_mutation_and_builtins": (
        "let xs = [1, 2, 3] xs[0] = 9 append(xs, 4) print(xs) "
        "print(first(xs)) print(last(xs)) print(sum(xs)) print(xs[1:3])"
    ),
    "maps": (
        'let m: Map[String, Int] = {} m["a"] = 1 m["b"] = 2 '
        'print(m) print(len(m)) print(get(m, "missing", 0)) '
        "for k in m { print(k) }"
    ),
    "functions_and_for": (
        "fn fib(n: Int) -> Int { if n < 2 { n } else { fib(n - 1) + fib(n - 2) } } "
        "print(fib(6)) let total = 0 "
        "for i in range(4) { if i == 2 { continue } total = total + i } print(total)"
    ),
    "try_catch": (
        'let seen = 0 try { throw "boom" } catch e { seen = 1 print(e) } print(seen)'
    ),
    "conversions": (
        'print(int("12")) print(float("1.5")) print(str(3)) print(lower("ABC"))'
    ),
    "while_break": (
        "let i = 0 while true { i = i + 1 if i == 3 { break } } print(i)"
    ),
}


class TestEngineParityTable(unittest.TestCase):
    def test_outputs_and_environments_match(self):
        for name, source in CASES.items():
            with self.subTest(case=name):
                result = run_both_engines(source)
                self.assertEqual(result.interpreter_output, result.vm_output)
                self.assertEqual(result.interpreter_env, result.vm_env)


if __name__ == "__main__":
    unittest.main()
