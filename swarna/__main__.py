import argparse
import sys

from compiler.codegen.compiler import Compiler
from compiler.diagnostics import DiagnosticError, render_diagnostic
from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser


def lex_source(source: str) -> str:
    tokens = Lexer(source).tokenize()
    return "\n".join(f"{t.type.name} {t.value!r} ({t.line}:{t.column})" for t in tokens)


def parse_source(source: str) -> str:
    program = Parser(Lexer(source)).parse_program()
    return repr(program)


def emit_bytecode_source(source: str) -> str:
    program = Parser(Lexer(source)).parse_program()
    code = Compiler().compile(program)
    return "\n".join(repr(i) for i in code)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="swarna", description="SWARNA language tools (minimal)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--lex", action="store_true", help="Print tokens for the input")
    mode.add_argument("--parse", action="store_true", help="Print AST for the input")
    mode.add_argument("--emit-bytecode", action="store_true", help="Print compiled bytecode for the input")
    parser.add_argument("source", nargs="?", help="Source line; if omitted, reads stdin or starts REPL")
    args = parser.parse_args(argv)

    def render(source: str) -> str:
        if args.parse:
            return parse_source(source)
        if args.emit_bytecode:
            return emit_bytecode_source(source)
        return lex_source(source)

    if args.source is not None:
        try:
            print(render(args.source))
        except DiagnosticError as e:
            print(render_diagnostic(args.source, e), file=sys.stderr)
            return 1
        except SyntaxError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        return 0

    if not sys.stdin.isatty():
        source = sys.stdin.read()
        try:
            print(render(source))
        except DiagnosticError as e:
            print(render_diagnostic(source, e), file=sys.stderr)
            return 1
        except SyntaxError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        return 0

    print("SWARNA (minimal) — enter a line, :lex/:parse/:bytecode prefixes optional, :q to quit")
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
        action = "parse" if args.parse else "bytecode" if args.emit_bytecode else "lex"
        source = line
        if line.startswith(":parse "):
            action, source = "parse", line[7:]
        elif line.startswith(":bytecode "):
            action, source = "bytecode", line[10:]
        elif line.startswith(":lex "):
            action, source = "lex", line[5:]
        try:
            if action == "parse":
                print(parse_source(source))
            elif action == "bytecode":
                print(emit_bytecode_source(source))
            else:
                print(lex_source(source))
        except DiagnosticError as e:
            print(render_diagnostic(source, e), file=sys.stderr)
        except (SyntaxError, NotImplementedError, NameError, RuntimeError, ZeroDivisionError) as e:
            print(f"error: {e}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
