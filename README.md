# SWARNA

SWARNA is a programming language implemented in Python. The project includes a lexer, parser, abstract syntax tree (AST), type checker, tree-walking interpreter, bytecode compiler, and stack-based virtual machine.

This project is in an early stage of development. The current implementation supports a limited subset of the language suitable for small scripts and experimentation.

## Documentation

- [Design principles](docs/DESIGN_PRINCIPLES.md)
- [Roadmap and vision](docs/VISION.md)
- [Target users and positioning](docs/POSITIONING.md)

## Requirements

- Python 3.10 or later
- No third-party runtime dependencies

## Installation

To install the command-line interface in editable mode:

```bash
python -m pip install -e .
```

After installation, the `swarna` command is available. You can also run the tool without installing it using `python -m swarna`.

## Usage

Run a program from the command line:

```bash
python -m swarna --run "let total = 1 + 2 * 3 print(total)"
```

Run a `.sw` source file:

```bash
python -m swarna program.sw
# or
python -m swarna --run program.sw
```

Start the REPL (bindings and function declarations persist between lines):

```bash
python -m swarna --run
```

Inspect compiler and runtime stages:

```bash
python -m swarna --version
python -m swarna --lex "let x = 42"
python -m swarna --parse "let x = 1 + 2 * 3"
python -m swarna --emit-bytecode "let x = 1 + 2"
```

### Multi-line programs via stdin

Source can be piped to stdin for multi-line programs.

**PowerShell**

```powershell
@'
let score = 42
let label = if score >= 50 { "pass" } else { "fail" }
print(label)
'@ | python -m swarna --run
```

**bash/zsh**

```bash
printf 'let score = 42\nlet label = if score >= 50 { "pass" } else { "fail" }\nprint(label)\n' | python -m swarna --run
```

## Examples

```bash
python -m swarna --run "let total = 0 let i = 1 while i <= 5 { total = total + i i = i + 1 } print(total)"
python -m swarna --run "let scores = [72, 85, 90] let total = 0 for score in scores { total = total + score } print(total)"
python -m swarna --run "fn add(a: Int, b: Int) -> Int { a + b } print(add(2, 3))"
```

The repository includes a CSV example:

```bash
python -m swarna --run examples/team_averages.sw
```

## Language features

- **Types and bindings:** `Int`, `Float`, `String`, `Bool`, `List[T]`, `Map[K, V]`, and `Unit` (`()`); `let` and `const` bindings.
- **Operators:** Arithmetic (`+`, `-`, `*`, `/`, `//`, `%`), comparisons, and boolean logic (`and`, `or`, `not`, `&&`, `||`, `!`).
- **Control flow:** `if` / `else if` / `elif` / `else` (statements and expressions), `while`, `for` (lists, maps, strings), `break`, and `continue`.
- **Error handling (v1):** `throw "message"` and `try { ... } catch e { ... }`. Caught runtime/user errors bind the error message to `e` as a `String`.
- **Functions:** `fn` declarations, optional parameter and return annotations, `return`, recursion/mutual recursion, and local scope.
- **Collections and strings:** List and map literals, indexing, map assignment and `get`, `len`, list concatenation with `+`, string indexing/iteration, and `range(...)`.
- **Built-ins and I/O:** `print`, `len`, `get`, `range`, `input`, `int`, `float`, `str`, `read_file`, and `read_csv`.
- **Tooling:** Interpreter and bytecode VM execution paths, REPL, source diagnostics with hints, and `--explain` for selected error categories.
- **Syntax:** `#` line comments.

## Known limitations

- No user-defined types/records, modules/imports, generics, type aliases, string interpolation, or concurrency.
- Lists and strings do not support element assignment, slicing, or string methods. Maps support assignment and `get`, but not deletion or entry iteration helpers.
- Collections are homogeneous. Map keys must be `Int`, `Float`, `String`, or `Bool`.
- No first-class or nested functions, and no mutation of global bindings from within functions. Unannotated parameter or return types may be treated as `Unknown` at some call sites; annotate return types where call-site precision is required.
- File I/O is limited to `read_file` and `read_csv`. There is no standard library beyond the built-ins listed above, and no formatter, debugger, or language server.

## Development

Run the test suite:

```bash
python -m unittest discover -s tests -v
```

## Project structure

- `compiler/` — lexer, parser, AST, semantic checker, bytecode, and code generation
- `runtime/` — interpreter and virtual machine
- `swarna/` — command-line interface and REPL
- `tests/` — test suite
- `docs/` — design and project documentation
- `examples/` — sample programs

## Additional information

- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [License](LICENSE)
