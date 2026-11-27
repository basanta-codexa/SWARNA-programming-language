# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-11-27

### Added
- `sum(xs)` list built-in returning Int or Float for numeric lists.
- `first(xs)` and `last(xs)` list built-ins preserving the element type.
- `append(xs, value)` list built-in returning `Unit` and mutating a `let` list.
- List slicing with `values[start:end]`, including omitted bounds and negative indices.
- `split(text, separator)` string built-in returning `List[String]`.
- `contains(text, part)` string built-in returning Bool.
- `upper(text)` and `lower(text)` string built-ins.
- String slicing with `text[start:end]`, including omitted bounds and negative indices.
- `--vm` CLI flag to run programs on the bytecode VM, alongside the interpreter path.
- `print(...)` can now be used as an expression; it prints as before and returns `Unit`.
- Multiple comma-separated arguments to `print`, joined with `, ` on one line (for example, `print("Hello", 12)`).
- Exception handling v1: `throw` (with a `String` message) and `try { ... } catch name { ... }`, binding the caught message to `name` (lexer, parser, AST, type checker, interpreter, bytecode/VM, and tests).
- `break` and `continue` statements for `while` and `for` loops (lexer, parser, type checker, interpreter, VM, codegen, and tests).
- Packaging via `pyproject.toml`, editable installs, a `swarna` console-script entry point, and `swarna.__version__`.
- `--version` CLI flag.
- Running `.sw` source files directly from the CLI.
- MIT `LICENSE` and `CONTRIBUTING.md`.
- This changelog.
- `#` line comments.
- `%` (modulo/remainder) operator.
- `range(...)` built-in for integer sequences (usable with `for` loops).
- String indexing (`text[i]`, including negative indices) and `for` iteration over strings.
- `input()` built-in to read a line from stdin.
- `int(...)`, `float(...)`, and `str(...)` conversion built-ins.
- `return` statements for early exit from functions.
- Statement-form `if` blocks inside block expressions/function bodies, enabling early-return control flow before a final expression.
- `else if` chaining and the `elif` keyword alias for `if` statements and expressions.
- Expression statements, including function call statements, for side effects.
- `Unit` type and `()` literal, `return` without a value, and implicit `Unit`-valued blocks.
- `Int`-to-`Float` widening in type checking and runtime coercions (annotated `let` bindings and function arguments/returns in the interpreter and VM).

### Changed
- Lists are mutable on `let` bindings: `xs[0] = value` updates the list with type and bounds checks.
- The `--vm` REPL now preserves bindings and function declarations across lines.
- The CLI now streams `print` output as it runs, so earlier output survives a later error.
- The CLI now runs an existing `.sw` file by default and reads source files as UTF-8 with an optional BOM.
- CI now covers Python 3.10–3.14 on Ubuntu, Windows, and macOS, and builds the distribution, installs the wheel, and smoke-tests the `swarna` CLI.
- Packaging now requires setuptools 77+ and reads the version from `swarna.__version__`.
- Inferred `Int`-to-`Float` widening now stores `Float` values, using type information passed from the checker to the interpreter and VM.
- Explicit `Float` annotations now coerce stored values consistently in the interpreter and VM, including assignments and list/map elements.
- Empty maps now refine their key and value types on index assignment; mixed value types and non-scalar keys are rejected.
- Reading a variable now requires it to be assigned on every path that reaches the use.
- Function return inference is now order-independent: unannotated return types are inferred to a fixed point before checking call sites.
- String literals can no longer span lines; use `\n` for a newline inside a string.

### Fixed
- Fixed VM `try`/`catch` handler cleanup for `break` and `continue`, and aligned VM catch scoping with the interpreter.
- Replaced host integer-limit crashes with SWARNA diagnostics at parse, print, and CLI boundaries.
- Cyclic lists and maps now format as `<cycle>` instead of crashing with `RecursionError`.
- Index errors now point at the same source span in the interpreter and VM.
- Removed duplicate test classes that were defined after `unittest.main()`.
- Duplicate bindings and duplicate literal map keys are now semantic errors instead of silent replacements.
- Mutating a map while iterating over it now raises a catchable SWARNA error with a source span and hint.
- The CLI now reports `file not found` for path-like source arguments instead of lexing them as inline code.
- `read_file` and `read_csv` now strip a leading UTF-8 BOM instead of treating it as data.
- CSV numeric cells now reject `nan`/`inf` floats and underscore separators.
- Hardened explicit conversions: `float(...)` requires finite numeric values (rejects `inf`/`nan`) and `int(...)` rejects non-finite `Float` inputs; improved conversion diagnostics and `+` string-combination hints.
- Identifiers are now explicitly ASCII-only, with a clear syntax diagnostic for non-ASCII characters.
- Chained comparisons now produce a clear error that suggests combining them with `&&`.
- Keywords used as variable, function, parameter, loop, or catch names now produce a clear reserved-keyword diagnostic.
- Assigning to `print` now produces a clear reserved-statement diagnostic instead of a misleading parser error.
- Unknown string escapes now produce a syntax diagnostic instead of silently dropping the backslash.
- Improved conditional diagnostics: clearer hints for non-`Bool` conditions, clearer errors when `if` expressions are missing a final `else`, and clearer branch-type mismatch messages for `if`/`elif` expression chains.

### Documentation
- Updated `DESIGN_PRINCIPLES.md` so its status and rule statements match the implemented language.
- Documented conditional/block-expression consistency rules (statement-form `if` before a final expression, trailing `if` as an expression value, and where block values are supported).
- Documented explicit/implicit conversion rules (numeric widening only; no implicit `Bool↔Int`, `String↔number`, or value→`String` conversions).
- Updated `README.md`, `docs/DESIGN_PRINCIPLES.md`, and `CHANGELOG.md` to reflect new language features and behavior.
- Added the Task 1 audit documents: `docs/ARCHITECTURE_AUDIT.md`, `docs/EXISTING_LANGUAGE_BEHAVIOR.md`, `docs/TEST_BASELINE.md`, and `docs/TECHNICAL_DEBT.md`.

### Migration Notes
- **Reserved built-in names.** `first`, `last`, `sum`, `append`, `upper`, `lower`, `contains`, and `split` are now reserved. They can no longer be used as variable, function, or parameter names. Rename any user-defined bindings that use these names (the internal tests renamed a helper from `first` to `head`).
- **Mutable lists.** Lists bound with `let` are now mutable: `xs[0] = value` and `append(xs, value)` modify the list in place. Code that relied on list immutability should rebuild lists explicitly.
- **`print` as an expression.** `print(...)` can now appear as an expression and returns `Unit`. Multiple arguments are joined with `, ` on one line.
- **Slicing.** Substring and sublist extraction now uses `text[start:end]` / `xs[start:end]`, with omitted bounds and negative indices allowed.
- **String literals.** Strings can no longer span physical lines; use `\n` for embedded newlines.
- **Identifiers.** Identifiers are ASCII-only; non-ASCII identifiers now produce a syntax diagnostic.
- **Reserved keywords and `print`.** Keywords used as names and assignments to `print` now produce clear diagnostics instead of misleading parser errors.
