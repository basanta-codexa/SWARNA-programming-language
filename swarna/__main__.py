import argparse
import sys

from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser


def lex_source(source: str) -> str:
    tokens = Lexer(source).tokenize()
    return "\n".join(f"{t.type.name} {t.value!r} ({t.line}:{t.column})" for t in tokens)


def parse_source(source: str) -> str:
    program = Parser(Lexer(source)).parse_program()
    return repr(program)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="swarna", description="SWARNA language tools (minimal)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--lex", action="store_true", help="Print tokens for the input")
    mode.add_argument("--parse", action="store_true", help="Print AST for the input")
    parser.add_argument("source", nargs="?", help="Source line; if omitted, reads stdin or starts REPL")
    args = parser.parse_args(argv)

    if args.source is not None:
        source = args.source
        try:
            if args.parse:
                print(parse_source(source))
            else:
                print(lex_source(source))
        except SyntaxError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        return 0

    if not sys.stdin.isatty():
        source = sys.stdin.read()
        try:
            if args.parse:
                print(parse_source(source))
            else:
                print(lex_source(source))
        except SyntaxError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        return 0

    print("SWARNA (minimal) — enter a line, :lex/:parse prefixes optional, :q to quit")
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
        action = "lex"
        source = line
        if line.startswith(":parse "):
            action, source = "parse", line[7:]
        elif line.startswith(":lex "):
            action, source = "lex", line[5:]
        elif args.parse:
            action = "parse"
        try:
            if action == "parse":
                print(parse_source(source))
            else:
                print(lex_source(source))
        except SyntaxError as e:
            print(f"error: {e}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
