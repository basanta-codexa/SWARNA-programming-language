import unittest

from compiler.codegen.compiler import Compiler
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from runtime.interpreter import Interpreter
from runtime.vm import VM
from runtime.values import format_value


def _interpreter_output(source: str) -> list[str]:
    program = Parser(Lexer(source)).parse_program()
    interpreter = Interpreter()
    interpreter.eval(program)
    return [format_value(value) for value in interpreter.output]


def _vm_output(source: str) -> list[str]:
    program = Parser(Lexer(source)).parse_program()
    vm = VM()
    vm.run(Compiler().compile(program))
    return [format_value(value) for value in vm.output]


class TestTryCatchEngineParity(unittest.TestCase):
    """The interpreter is the reference semantics for try/catch scopes."""

    def _assert_parity(self, source: str) -> None:
        self.assertEqual(_vm_output(source), _interpreter_output(source))

    def test_try_declaration_is_visible_in_catch(self):
        self._assert_parity('try { let x = 5 throw "boom" } catch e { print(x) }')

    def test_catch_assignment_is_discarded(self):
        self._assert_parity('let seen = 0 try { throw "boom" } catch e { seen = 1 } print(seen)')

    def test_catch_binding_does_not_overwrite_outer_binding(self):
        self._assert_parity('let e = "outer" try { throw "boom" } catch e { } print(e)')

    def test_try_assignment_before_throw_persists(self):
        self._assert_parity('let seen = 0 try { seen = 1 throw "boom" } catch e { } print(seen)')

    def test_break_from_catch_discards_catch_assignment(self):
        self._assert_parity(
            'let seen = 0 let i = 0 '
            'while i < 1 { i = i + 1 try { throw "boom" } catch e { seen = 1 break } } '
            'print(seen)'
        )

    def test_inner_catch_keeps_outer_catch_assignments(self):
        self._assert_parity(
            'let seen = 0 try { throw "a" } catch e { seen = 1 '
            'try { print(1 / 0) } catch inner { print(seen) } } print(seen)'
        )

    def test_error_in_catch_discards_catch_assignment(self):
        self._assert_parity(
            'let seen = 0 try { try { throw "a" } catch e { seen = 1 print(1 / 0) } '
            '} catch outer { print(seen) print(outer) }'
        )


if __name__ == "__main__":
    unittest.main()
