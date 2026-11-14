import argparse
import sys

from compiler.codegen.compiler import Compiler
from compiler.diagnostics import DiagnosticError, render_diagnostic
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.checker import Binding, FunctionSignature, Type, TypeChecker, type_from_annotation, type_of_value
from runtime.interpreter import Interpreter
from runtime.values import format_value
from swarna import __version__


def lex_source(source: str) -> str:
    tokens = Lexer(source).tokenize()
    return "\n".join(f"{t.type.name} {t.value!r} ({t.line}:{t.column})" for t in tokens)


def parse_source(source: str) -> str:
    program = Parser(Lexer(source)).parse_program()
    return repr(program)


def emit_bytecode_source(source: str) -> str:
    program = Parser(Lexer(source)).parse_program()
    TypeChecker().check(program)
    compiled = Compiler().compile(program)
    lines = [repr(i) for i in compiled.instructions]
    for function in compiled.functions.values():
        lines.append(f"FUNCTION {function.name}/{len(function.parameters)}")
        lines.extend(f"  {repr(i)}" for i in function.instructions)
    return "\n".join(lines)


def _bindings_from_interpreter(interpreter: Interpreter) -> dict[str, Binding]:
    return {
        name: Binding(
            type_of_value(value),
            constant=interpreter.constant.get(name, False),
        )
        for name, value in interpreter.env.items()
    }


def _functions_from_interpreter(interpreter: Interpreter) -> dict[str, FunctionSignature]:
    signatures: dict[str, FunctionSignature] = {}
    for name, function in interpreter.functions.items():
        annotations = function.parameter_annotations
        if len(annotations) != len(function.parameters):
            annotations = tuple(None for _ in function.parameters)
        parameters = tuple(
            type_from_annotation(annotation) if annotation is not None else Type.UNKNOWN
            for annotation in annotations
        )
        return_type = (
            type_from_annotation(function.return_annotation)
            if function.return_annotation is not None
            else None
        )
        signatures[name] = FunctionSignature(
            name=name,
            parameters=parameters,
            return_type=return_type,
            span=function.span,
        )
    return signatures


def run_source(
    source: str,
    interpreter: Interpreter | None = None,
    function_signatures: dict[str, FunctionSignature] | None = None,
) -> str:
    program = Parser(Lexer(source)).parse_program()
    if interpreter is None:
        interpreter = Interpreter()
    functions = _functions_from_interpreter(interpreter)
    if function_signatures is not None:
        functions.update(function_signatures)
    checker = TypeChecker(_bindings_from_interpreter(interpreter), functions)
    checker.check(program)
    if function_signatures is not None:
        function_signatures.clear()
        function_signatures.update(checker.functions)
    output_start = len(interpreter.output)
    interpreter.eval(program)
    return "\n".join(format_value(value) for value in interpreter.output[output_start:])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="swarna", description="SWARNA language tools (minimal)")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--lex", action="store_true", help="Print tokens for the input")
    mode.add_argument("--parse", action="store_true", help="Print AST for the input")
    mode.add_argument("--emit-bytecode", action="store_true", help="Print compiled bytecode for the input")
    mode.add_argument("--run", action="store_true", help="Run the input and print its output")
    parser.add_argument(
        "--explain",
        action="store_true",
        help="Expand errors with a plain-language explanation",
    )
    parser.add_argument("source", nargs="?", help="Source line; if omitted, reads stdin or starts REPL")
    args = parser.parse_args(argv)

    def render(source: str) -> str:
        if args.run:
            return run_source(source)
        if args.parse:
            return parse_source(source)
        if args.emit_bytecode:
            return emit_bytecode_source(source)
        return lex_source(source)

    if args.source is not None:
        try:
            output = render(args.source)
        except DiagnosticError as e:
            print(render_diagnostic(args.source, e, explain=args.explain), file=sys.stderr)
            return 1
        except SyntaxError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        except (NameError, TypeError, ZeroDivisionError, RuntimeError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print("interrupted", file=sys.stderr)
            return 130
        if output:
            print(output)
        return 0

    if not sys.stdin.isatty():
        source = sys.stdin.read()
        try:
            output = render(source)
        except DiagnosticError as e:
            print(render_diagnostic(source, e, explain=args.explain), file=sys.stderr)
            return 1
        except SyntaxError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        except (NameError, TypeError, ZeroDivisionError, RuntimeError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print("interrupted", file=sys.stderr)
            return 130
        if output:
            print(output)
        return 0

    interpreter = Interpreter()
    function_signatures: dict[str, FunctionSignature] = {}
    explain = args.explain
    print(
        "SWARNA (minimal) — enter a line, :lex/:parse/:bytecode/:run prefixes optional, "
        ":explain toggles full explanations, :q to quit"
    )
    while True:
        try:
            line = input("swarna> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if line.strip() in {":q", ":quit", ":exit"}:
            return 0
        if not line.strip():
            continue
        if line.strip() == ":explain":
            explain = not explain
            print(f"explanations {'on' if explain else 'off'}")
            continue
        action = "run" if args.run else "parse" if args.parse else "bytecode" if args.emit_bytecode else "lex"
        source = line
        if line.startswith(":parse "):
            action, source = "parse", line[7:]
        elif line.startswith(":bytecode "):
            action, source = "bytecode", line[10:]
        elif line.startswith(":run "):
            action, source = "run", line[5:]
        elif line.startswith(":lex "):
            action, source = "lex", line[5:]
        try:
            if action == "parse":
                print(parse_source(source))
            elif action == "bytecode":
                print(emit_bytecode_source(source))
            elif action == "run":
                output = run_source(source, interpreter, function_signatures)
                if output:
                    print(output)
            else:
                print(lex_source(source))
        except DiagnosticError as e:
            print(render_diagnostic(source, e, explain=explain), file=sys.stderr)
        except SyntaxError as e:
            print(f"error: {e}", file=sys.stderr)
        except (NameError, TypeError, ZeroDivisionError, RuntimeError) as e:
            print(f"error: {e}", file=sys.stderr)
        except KeyboardInterrupt:
            print("\ninterrupted", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
