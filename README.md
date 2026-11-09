# SWARNA

SWARNA is a programming language written from scratch in Python. It has its own lexer, parser, AST, interpreter, bytecode compiler, and stack VM.

It is early, and it is not ready for real programs yet. The current subset is enough to run small scripts; the rest of the language is still being built.

Design decisions and the reasoning behind them are in [docs/DESIGN_PRINCIPLES.md](docs/DESIGN_PRINCIPLES.md).

## Run it

Requires Python 3.10+ and no third-party packages.

```
python -m swarna --run "let total = 1 + 2 * 3 print(total)"
```

Prints `7`.

A loop:

```
python -m swarna --run "let total = 0 let i = 1 while i <= 5 { total = total + i i = i + 1 } print(total)"
```

Prints `15`.

For multi-line programs, pipe the source through stdin. On PowerShell:

```
@'
let score = 42
let label = if score >= 50 { "pass" } else { "fail" }
print(label)
'@ | python -m swarna --run
```

Prints `fail`.

PowerShell strips embedded double quotes when passing a source string to a native command. The here-string above avoids that.

`--run` uses the tree-walking interpreter. The REPL also executes lines by default when started with `--run`:

```
python -m swarna --run
```

## What works

- integers, floats, strings, booleans
- `let` for mutable bindings, `const` for immutable ones
- arithmetic, comparisons, `and`/`or`/`not`, `&&`/`||`/`!`
- `if`/`else` statements and single-expression `if` expressions
- `while` loops
- `print`
- caret diagnostics with hints for lexer and parser errors
- a stack VM checked against the interpreter by differential tests

## What does not work yet

Functions, collections, and static types are the big missing pieces. Modules, a standard library, comments, string interpolation, concurrency, tooling (debugger, formatter, LSP), and source-spanned runtime errors are also missing.

## Inspect the pipeline

```
python -m swarna --lex "let x = 42"
python -m swarna --parse "let x = 1 + 2 * 3"
python -m swarna --emit-bytecode "let x = 1 + 2"
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
