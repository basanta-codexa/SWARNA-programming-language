# SWARNA

SWARNA is a programming language implemented in Python, including a lexer, parser, AST, type checker, interpreter, bytecode compiler, and stack VM.

**Status:** Early development. It can run small scripts and examples, but many language and tooling features are not yet implemented.

- Design: [docs/DESIGN_PRINCIPLES.md](docs/DESIGN_PRINCIPLES.md)
- Roadmap: [docs/VISION.md](docs/VISION.md)
- Target users: [docs/POSITIONING.md](docs/POSITIONING.md)

## Requirements

- Python 3.10+
- No third-party dependencies

## Usage

Run a program from the command line:

```bash
python -m swarna --run "let total = 1 + 2 * 3 print(total)"  # 7
```

Run a `.sw` file (default when the argument is an existing file):

```bash
python -m swarna program.sw
# or
python -m swarna --run program.sw
```

Install the CLI locally (editable):

```bash
python -m pip install -e .
swarna --run "print(1 + 2)"
```

Start the REPL (keeps bindings/functions between lines):

```bash
python -m swarna --run
```

Inspect the pipeline:

```bash
python -m swarna --version
python -m swarna --lex "let x = 42"
python -m swarna --parse "let x = 1 + 2 * 3"
python -m swarna --emit-bytecode "let x = 1 + 2"
```

### Multi-line input

Piping source to stdin works for multi-line programs.

PowerShell (preserves quotes):

```powershell
@'
let score = 42
let label = if score >= 50 { "pass" } else { "fail" }
print(label)
'@ | python -m swarna --run
```

bash/zsh:

```bash
printf 'let score = 42\nlet label = if score >= 50 { "pass" } else { "fail" }\nprint(label)\n' | python -m swarna --run
```

## Examples

```bash
python -m swarna --run "let total = 0 let i = 1 while i <= 5 { total = total + i i = i + 1 } print(total)"  # 15
python -m swarna --run "let scores = [72, 85, 90] let total = 0 for score in scores { total = total + score } print(total)"  # 247
python -m swarna --run "fn add(a: Int, b: Int) -> Int { a + b } print(add(2, 3))"  # 5
```

CSV example (`examples/team_averages.sw`):

```bash
python -m swarna --run examples/team_averages.sw  # {"Blue": 90.0, "Red": 82.0}
```

## Current features

- Values/types: `Int`, `Float`, `String`, `Bool`, `List[T]`, `Map[K, V]`, `Unit`/`()`; `let`/`const` bindings.
- Operators: arithmetic (incl. `//`, `%`), comparisons, boolean logic (`and/or/not`, `&&/||/!`).
- Control flow: `if`/`else if`/`elif`/`else` (statements and expressions), `while`, `for` over lists/maps/strings, `break`, `continue`.
- Error handling (v1): `throw "message"` and `try { ... } catch e { ... }` (catches runtime/user errors; `e` is the error message string).
- Functions: `fn` declarations, optional param/return annotations, `return`, recursion/mutual recursion, local scope.
- Collections/strings: list/map literals, indexing, map assignment and `get`, `len`, list concat with `+`, string indexing/iteration, `range(...)`.
- I/O and built-ins: `print`, `len`, `get`, `range`, `input`, `int`, `float`, `str`, `read_file`, `read_csv`.
- Tooling/diagnostics: interpreter, bytecode VM, REPL, caret diagnostics with hints, `--explain` for some error categories.
- `#` line comments.

## Current limitations

- No records or user-defined types, modules/imports, generics, type aliases, string interpolation, or concurrency.
- Lists and strings are immutable by index (no element assignment, slicing, or string methods). Maps support `m[key] = value` and `get`, but not deletion or entry iteration helpers.
- Collections are homogeneous; map keys must be `Int`, `Float`, `String`, or `Bool`.
- No first-class or nested functions, and no global mutation from functions. Unannotated parameter/return types may be treated as `Unknown` at some call sites (annotate return types when needed).
- File I/O is limited to `read_file` and `read_csv` (no write APIs). No standard library beyond built-ins, and no formatter, debugger, or LSP.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Project layout

- `compiler/` — lexer, parser, AST, semantic checker, bytecode, codegen
- `runtime/` — interpreter, VM
- `swarna/` — CLI and REPL
- `tests/` — unit tests
- `docs/` — design and positioning docs

See also: [CONTRIBUTING.md](CONTRIBUTING.md), [CHANGELOG.md](CHANGELOG.md), [LICENSE](LICENSE).
