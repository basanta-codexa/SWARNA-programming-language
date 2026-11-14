# SWARNA

SWARNA is a programming language written from scratch in Python. It has its own lexer, parser, AST, type checker, interpreter, bytecode compiler, and stack VM.

It is early, and it is not ready for real programs yet. The current subset is enough to run small scripts; the rest of the language is still being built.

Design decisions and the reasoning behind them are in [docs/DESIGN_PRINCIPLES.md](docs/DESIGN_PRINCIPLES.md). The target user and the switch test are in [docs/POSITIONING.md](docs/POSITIONING.md).

## Run it

Requires Python 3.10+ and no third-party packages.

```bash
python -m swarna --run "let total = 1 + 2 * 3 print(total)"
```

To install the CLI locally (editable):

```bash
python -m pip install -e .
swarna --run "let total = 1 + 2 * 3 print(total)"
```

Run a `.sw` source file:

```bash
python -m swarna program.sw
# or explicitly:
python -m swarna --run program.sw
# or, if installed:
swarna program.sw
```

Prints `7`.

A `while` loop:

```
python -m swarna --run "let total = 0 let i = 1 while i <= 5 { total = total + i i = i + 1 } print(total)"
```

Prints `15`.

A `for` loop over a list:

```
python -m swarna --run "let scores = [72, 85, 90] let total = 0 for score in scores { total = total + score } print(total)"
```

Prints `247`.

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

A map:

```
@'
let ages = { "Ada": 36, "Grace": 45 }
print(ages["Ada"])
print(len(ages))
'@ | python -m swarna --run
```

Prints `36`, then `2`.

A map entry can be assigned. Assigning a missing key adds it:

```
@'
let totals = { "red": 0 }
totals["red"] = totals["red"] + 5
totals["blue"] = 3
print(totals)
'@ | python -m swarna --run
```

Prints `{"red": 5, "blue": 3}`.

For multi-line programs, pipe the source through stdin. In PowerShell (recommended there, to preserve double quotes):

```
@'
let score = 42
let label = if score >= 50 { "pass" } else { "fail" }
print(label)
'@ | python -m swarna --run
```

In bash/zsh:

```bash
printf 'let score = 42\nlet label = if score >= 50 { "pass" } else { "fail" }\nprint(label)\n' | python -m swarna --run
```

Both print `fail`. PowerShell can strip embedded double quotes when passing a source string to a native command; the here-string avoids that.

`--run` uses the tree-walking interpreter. The REPL also executes lines by default when started with `--run`, and bindings and function declarations persist between lines:

```
python -m swarna --run
```

`--emit-bytecode` prints the main instructions followed by each compiled function.

## Run the scores example

`examples/team_averages.sw` reads `examples/scores.csv`, accumulates a total and count per team, and prints the averages:

```
let rows = read_csv("examples/scores.csv", { name: String, team: String, score: Float })

let totals: Map[String, Float] = {}
let counts: Map[String, Int] = {}
let averages: Map[String, Float] = {}

for row in rows {
    let team = row["team"]
    totals[team] = get(totals, team, 0.0) + row["score"]
    counts[team] = get(counts, team, 0) + 1
    averages[team] = totals[team] / counts[team]
}

print(averages)
```

From the repository root:

```bash
python -m swarna --run examples/team_averages.sw
```

(Prints `{"Blue": 90.0, "Red": 82.0}`. You can also pipe the file contents to stdin if you prefer.) If a score cell is not a number, `read_csv` reports the file, row, column, and bad value before arithmetic runs.

## What works

- integers, floats, strings, booleans
- `let` for mutable bindings, `const` for immutable ones
- arithmetic, comparisons, `and`/`or`/`not`, `&&`/`||`/`!`
- `if`/`else` statements and `if` expressions with single-expression or block branches
- `while` loops
- `for` loops over lists, map keys, and strings, with a loop variable scoped to the loop (use `range(...)` for numeric sequences)
- `break` and `continue` in `while` and `for` loops
- `#` line comments
- named `fn` declarations with optional parameter and return annotations
- explicit types: `Int`, `Float`, `String`, `Bool`, `List[T]`, and `Map[K, V]`, including nested types such as `Map[String, List[Float]]`, on parameters, returns, and `let`/`const` bindings
- recursion, mutual recursion, hoisted calls, and function-local scopes
- functions in the interpreter, the VM, and the REPL
- list literals such as `[1, 2, 3]`, indexing with `values[i]`, negative indexing, `len(...)`, list equality, and `+` concatenation
- string indexing with `text[i]` (including negative indices) and iteration over strings with `for` loops (yielding one-character strings)
- inferred element types for lists, including nested lists
- map literals such as `{ "Ada": 36 }`, indexing with `map[key]`, `map[key] = value`, `get(map, key, default)`, `len(...)`, map equality, and inferred key and value types
- `read_file(path)`, which returns a UTF-8 text file's contents with diagnostics for missing files, directories, and invalid text
- `read_csv(path, { name: String, score: Float })`, which validates the header and each cell against the schema and returns rows as maps; a bad cell names the file, row, column, and value
- built-ins: `print`, `len`, `get`, `range`, `input`, `int`, `float`, `str`, `read_file`, `read_csv` (e.g. `range(5)`, `range(2, 7, 2)` produce lists of integers; `input()` reads a line from stdin as a `String`; use `int(...)`, `float(...)`, or `str(...)` to convert values)
- readable list and map output such as `["Ada", "Grace"]` and `{"Ada": 36}`
- inferred static types for the current expressions and bindings
- a REPL that keeps bindings and functions between lines
- caret diagnostics with hints for lexer, parser, semantic, and runtime errors
- `--explain` (or the REPL `:explain` toggle) adds a plain-language explanation to errors; undefined-name and type-mismatch categories are covered first, with explanations stored in a central registry
- a stack VM checked against the interpreter by differential tests, including function calls, lists, maps, and `for` loops

## What does not work yet

**Language and data**
- No records/user-defined types, modules/imports, generics, type aliases, string interpolation, or concurrency.
- Strings are immutable (no index assignment) and have indexing/iteration, but no string methods or slicing yet.
- Lists are immutable (no index assignment/append/delete); build a new list with `+`.
- Maps support `map[key] = value` for existing and new keys and `get`; there is no delete helper or map iteration over values/entries.
- Lists are homogeneous (`[1, 2.5]` is rejected; use `[1.0, 2.5]` for floats). Maps are homogeneous in keys and values, and keys must be `Int`, `Float`, `String`, or `Bool`.

**Functions and types**
- No first-class functions, nested declarations, or global mutation from functions. Expression statements (including function calls) are supported for side effects. `return expr` is supported for early exit from functions; function bodies are still block values and must end with a value or `return` (no procedure/`Unit` return type yet).
- `List[T]` and `Map[K, V]` annotations are supported (including nested types); user-defined generic types are not.
- Unannotated parameter types are `Unknown`. An unannotated return type is inferred after top-level statements are checked, so a top-level call to that function is checked as `Unknown`; annotate the return type when the call site needs precision. The REPL reuses inferred signatures on later lines.
- CSV rows are maps with column values typed as `Unknown` until schema-aware row types land.

**I/O, libraries, and tooling**
- File operations are `read_file` and `read_csv` only (no file/CSV writing).
- No grouping/aggregation helpers yet (use `for` loops, map assignment, `get`, and variables).
- No standard library beyond the built-ins shown above, and no debugger, formatter, or LSP.

## Inspect the pipeline

```
python -m swarna --version
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

See also: [CONTRIBUTING.md](CONTRIBUTING.md), [CHANGELOG.md](CHANGELOG.md), and [LICENSE](LICENSE).
