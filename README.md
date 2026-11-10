# SWARNA

SWARNA is a programming language written from scratch in Python. It has its own lexer, parser, AST, type checker, interpreter, bytecode compiler, and stack VM.

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

A block-valued `if`:

```
python -m swarna --run "let total = if true { let base = 100 base + 20 } else { 100 } print(total)"
```

Prints `120`.

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

`--run` uses the tree-walking interpreter. The REPL also executes lines by default when started with `--run`, and bindings persist between lines:

```
python -m swarna --run
```

## What works

- integers, floats, strings, booleans
- `let` for mutable bindings, `const` for immutable ones
- arithmetic, comparisons, `and`/`or`/`not`, `&&`/`||`/`!`
- `if`/`else` statements and `if` expressions with single-expression or block branches
- `while` loops
- `print`
- inferred static types for the current expressions and bindings
- a REPL that keeps bindings between lines
- caret diagnostics with hints for lexer, parser, semantic, and runtime errors
- a stack VM checked against the interpreter by differential tests

## What does not work yet

Functions, collections, and a complete type system are the big missing pieces. Type annotations, generics, and type checking across functions are not implemented. Modules, a standard library, comments, string interpolation, concurrency, and tooling (debugger, formatter, LSP) are also missing.

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
compiler/   lexer, parser, AST, semantic checker, bytecode, codegen
runtime/    interpreter, VM
swarna/     CLI and REPL
tests/      unit tests
docs/       design decisions
```
