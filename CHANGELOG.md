# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Exception handling v1: `throw` (with a `String` message) and `try { ... } catch name { ... }` to catch runtime/user errors, with the caught error message bound to `name` (lexer/parser/AST, type checking, interpreter, bytecode/VM, and tests).
- `break` and `continue` statements for `while` and `for` loops (lexer, parser, type checker, interpreter, VM, codegen, and tests).
- Packaging via `pyproject.toml`, editable installs, `swarna` console-script entry point, and `swarna.__version__`.
- Continuous integration workflow to run the test suite on Python 3.10–3.12.
- MIT `LICENSE`.
- `CONTRIBUTING.md` with development and contribution guidelines.
- This changelog.
- `--version` CLI flag.
- Running source files directly from the CLI (pass a `.sw` file path as the `source` argument).
- `#` line comments.
- `%` (modulo/remainder) operator.
- `range(...)` built-in for integer sequences (usable with `for` loops).
- String indexing (`text[i]`, including negative indices) and `for` iteration over strings.
- `input()` built-in to read a line from stdin.
- `int(...)`, `float(...)`, and `str(...)` conversion built-ins.
- `return` statements for early exit from functions.
- Statement-form `if` blocks inside block expressions/function bodies, enabling natural early-return control flow before a final expression.
- `else if` chaining for `if` expressions.
- `elif` keyword alias for `else if` in `if` statements and expressions.
- Expression statements, including function call statements, in statement contexts and block expressions (for side effects).
- `Unit` type and `()` literal, `return` without a value, and implicit `Unit`-valued blocks for simple procedure-style functions.
- `Int`-to-`Float` widening in type checking and key runtime coercions (annotated `let` bindings and function arguments/returns in interpreter/VM).

### Changed
- Hardened explicit conversions: `float(...)` requires finite numeric values (rejects `inf`/`nan`) and `int(...)` rejects non-finite `Float` inputs; improved conversion diagnostics and `+` string-combination hints.
- Documented explicit/implicit conversion rules (numeric widening only; no implicit `Bool↔Int`, `String↔number`, or value→`String` conversions).

### Changed
- Improved conditional diagnostics: clearer hints for non-`Bool` conditions, clearer errors when `if` expressions are missing a final `else`, and clearer branch-type mismatch messages for `if`/`elif` expression chains.

### Documentation
- Documented conditional/block-expression consistency rules (statement-form `if` before a final expression, trailing `if` as an expression value, and where block values are supported).

### Changed
- Documentation (`README.md`, `docs/DESIGN_PRINCIPLES.md`, `CHANGELOG.md`) updated to reflect new language features and behavior.
- Passing an existing source file now runs it by default; source files are read as UTF-8 with optional BOM.
