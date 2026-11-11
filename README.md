# SWARNA

SWARNA is a programming language written from scratch in Python. It has its own lexer, parser, AST, type checker, interpreter, bytecode compiler, and stack VM.

It is early, and it is not ready for real programs yet. The current subset is enough to run small scripts; the rest of the language is still being built.

Design decisions and the reasoning behind them are in [docs/DESIGN_PRINCIPLES.md](docs/DESIGN_PRINCIPLES.md). The target user and the switch test are in [docs/POSITIONING.md](docs/POSITIONING.md).

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

A function:

```
python -m swarna --run "fn add(a: Int, b: Int) -> Int { a + b } print(add(2, 3))"
```

Prints `5`.

A list:

```
python -m swarna --run "let scores = [72, 85, 90] print(scores[1]) print(len(scores))"
```

Prints `85`, then `3`.

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

`--run` uses the tree-walking interpreter. The REPL also executes lines by default when started with `--run`, and bindings and function declarations persist between lines:

```
python -m swarna --run
```

`--emit-bytecode` prints the main instructions followed by each compiled function.

## What works

- integers, floats, strings, booleans
- `let` for mutable bindings, `const` for immutable ones
- arithmetic, comparisons, `and`/`or`/`not`, `&&`/`||`/`!`
- `if`/`else` statements and `if` expressions with single-expression or block branches
- `while` loops
- named `fn` declarations with optional parameter and return annotations
- recursion, mutual recursion, hoisted calls, and function-local scopes
- functions in the interpreter, the VM, and the REPL
- list literals such as `[1, 2, 3]`, indexing with `values[i]`, negative indexing, `len(...)`, list equality, and `+` concatenation
- inferred element types for lists, including nested lists
- `print`, with readable list output such as `["Ada", "Grace"]`
- inferred static types for the current expressions and bindings
- a REPL that keeps bindings and functions between lines
- caret diagnostics with hints for lexer, parser, semantic, and runtime errors
- a stack VM checked against the interpreter by differential tests, including function calls and lists

## What does not work yet

Maps, records, modules, file I/O, and the standard library are still missing. There is no `for` loop yet, and lists cannot be mutated or appended to; build a new list with `+`. Lists are homogeneous: `[1, 2.5]` is rejected, so write `[1.0, 2.5]` when you want a list of floats. List type annotations such as `List[Int]` are not supported yet, so an unannotated list parameter is `Unknown`. Function limitations: no first-class functions, no `return` keyword, no nested declarations, no expression statements, and no global mutation. A function body must end with a value, so procedures are not supported. Generics, type aliases, comments, string interpolation, concurrency, and tooling (debugger, formatter, LSP) are also missing.

Unannotated parameter types are `Unknown`. An unannotated return type is inferred from the body after top-level statements are checked, so a top-level call to that function is checked as `Unknown`; annotate the return type when the call site needs precision. The REPL reuses the inferred signature on later lines.

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
docs/       positioning and design decisions
```
