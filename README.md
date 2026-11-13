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

```
Get-Content examples/team_averages.sw -Raw | python -m swarna --run
```

Prints `{"Blue": 90.0, "Red": 82.0}`. If a score cell is not a number, `read_csv` reports the file, row, column, and bad value before arithmetic runs.

## What works

- integers, floats, strings, booleans
- `let` for mutable bindings, `const` for immutable ones
- arithmetic, comparisons, `and`/`or`/`not`, `&&`/`||`/`!`
- `if`/`else` statements and `if` expressions with single-expression or block branches
- `while` loops
- `for` loops over lists and map keys, with a loop variable scoped to the loop
- named `fn` declarations with optional parameter and return annotations
- explicit types: `Int`, `Float`, `String`, `Bool`, `List[T]`, and `Map[K, V]`, including nested types such as `Map[String, List[Float]]`, on parameters, returns, and `let`/`const` bindings
- recursion, mutual recursion, hoisted calls, and function-local scopes
- functions in the interpreter, the VM, and the REPL
- list literals such as `[1, 2, 3]`, indexing with `values[i]`, negative indexing, `len(...)`, list equality, and `+` concatenation
- inferred element types for lists, including nested lists
- map literals such as `{ "Ada": 36 }`, indexing with `map[key]`, `map[key] = value`, `get(map, key, default)`, `len(...)`, map equality, and inferred key and value types
- `read_file(path)`, which returns a UTF-8 text file's contents with diagnostics for missing files, directories, and invalid text
- `read_csv(path, { name: String, score: Float })`, which validates the header and each cell against the schema and returns rows as maps; a bad cell names the file, row, column, and value
- `print`, with readable list and map output such as `["Ada", "Grace"]` and `{"Ada": 36}`
- inferred static types for the current expressions and bindings
- a REPL that keeps bindings and functions between lines
- caret diagnostics with hints for lexer, parser, semantic, and runtime errors
- `--explain` (or the REPL `:explain` toggle) adds a plain-language explanation to errors; undefined-name and type-mismatch categories are covered first, with explanations stored in a central registry
- a stack VM checked against the interpreter by differential tests, including function calls, lists, maps, and `for` loops

## What does not work yet

Records, modules, file writing, and the standard library are still missing. `read_file` and `read_csv` are the file operations; there is no CSV writing. CSV rows are maps, and their column values are statically `Unknown` until schema-aware row types land. There are no grouping or aggregation helpers yet; use `for` loops, map assignment, `get`, and variables. `for` loops iterate over lists and map keys; there are no ranges or string iteration yet, and there is no `break` or `continue`. Lists cannot be mutated; build a new list with `+`. Maps support `map[key] = value` for existing and new keys, but there is no insert or delete helper. Lists are homogeneous: `[1, 2.5]` is rejected, so write `[1.0, 2.5]` when you want a list of floats. Maps are homogeneous in both positions, and keys must be `Int`, `Float`, `String`, or `Bool`; a list key is rejected. List and map type annotations such as `List[Int]` and `Map[String, Int]` are supported, including nested types; user-defined generic types and type aliases are not, and an unannotated collection parameter is `Unknown`. Function limitations: no first-class functions, no `return` keyword, no nested declarations, no expression statements, and no global mutation. A function body must end with a value, so procedures are not supported. User-defined generics, type aliases, comments, string interpolation, concurrency, and tooling (debugger, formatter, LSP) are also missing.

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
