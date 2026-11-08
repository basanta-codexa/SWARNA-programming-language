# SWARNA

SWARNA is a programming language and runtime under active development. The lexer, parser, AST, tree-walking interpreter, bytecode compiler, and stack virtual machine are written from scratch in this repository. The goal is a general-purpose language that a motivated non-programmer can use for real work, without giving up the engineering depth of a proper compiler and runtime.

Design decisions and working rules are in [docs/DESIGN_PRINCIPLES.md](docs/DESIGN_PRINCIPLES.md).

## Status

Early development, v0.1. Implemented and tested:

- Lexer and token set: identifiers, integers, floats, strings, booleans, operators, keywords, braces, semicolons.
- Numeric semantics: `/` is true division; `//` is floor integer division.
- String literals with escape sequences and `+` concatenation.
- `let` mutable bindings and `const` immutable bindings; the old `let mut` form is removed.
- `and`/`or`/`not` aliases for `&&`/`||`/`!`.
- Recursive-descent parser with operator precedence.
- AST for `let`/`const`, assignment, `print`, `if`/`else`, `while`, and blocks.
- Tree-walking interpreter with `const` enforcement.
- Bytecode compiler and stack VM for the current subset, including jumps, short-circuit `&&`/`||`, and `const` enforcement.
- CLI: `--lex`, `--parse`, `--emit-bytecode`, and a small REPL.

Not implemented yet: static type checking, functions and call frames, garbage collection, modules, the standard library, string interpolation, concurrency, debugger, formatter, and LSP.

## Try it

Requires Python 3.10 or newer. No third-party dependencies.

```
python -m swarna --lex "let x = 42"
python -m swarna --parse "let x = 1 + 2 * 3"
python -m swarna --emit-bytecode "let x = 1 + 2"
python -m swarna
```

## Tests

```
python -m unittest discover -s tests -v
```

## Layout

```
compiler/   lexer, parser, AST, bytecode, codegen
runtime/    interpreter, VM
swarna/     CLI and REPL
tests/      unit tests
docs/       design decisions
```
