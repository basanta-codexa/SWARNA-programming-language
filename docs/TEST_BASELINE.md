# SWARNA Test Baseline

**Date:** 2026-11-27

**Status:** verified snapshot at commit `9f42b0b`.

**Purpose:** record the current test surface, exact commands, pass counts,
coverage areas, and gaps before adding new layers from the production blueprint.

## 1. Framework and commands

The project uses the Python standard library `unittest` only. There is no
`pytest`, `tox`, `nox`, Hypothesis, lint, or type-check configuration in the
repository. Coverage is measured locally with `coverage.py`, installed as a dev
tool; it is not declared as a project dependency, configured in the repository,
or run in CI.

Canonical full-suite commands:

```bash
python -m unittest discover -s tests
# Ran 943 tests ... OK

python -m unittest discover -v
# Ran 943 tests ... OK
```

Both forms work because `tests/` is a package and discovery starts at the
repository root. The documented command in `README.md` uses `-s tests`.

Focused module example:

```bash
python -m unittest tests.test_vm -v
# Ran 140 tests ... OK
```

Direct file execution also works for the previously repaired files:

```bash
python tests/test_interpreter.py   # 151 tests, OK
python tests/test_type_checker.py  # 183 tests, OK
python tests/test_vm.py            # 140 tests, OK
```

## 2. Local and CI verification

Local runs were executed on Python:

| Version | Result |
|---|---|
| 3.10 | 943 tests, OK |
| 3.13 | 943 tests, OK |
| 3.14.1 | 943 tests, OK |

Python 3.11 and 3.12 are not installed locally, but CI covers them.

CI (`.github/workflows/ci.yml`) runs on:

- Ubuntu, Windows, macOS
- Python 3.10, 3.11, 3.12, 3.13, 3.14

Each matrix job performs:

1. `python -m unittest discover -s tests -v`
2. `python -m build`
3. `python -m pip install dist/*.whl`
4. `swarna --version`
5. `swarna --run "print(1 + 2)"`

CI runs #71, #72, and #74 completed successfully for the matrix-expanding and
audit commits. No skipped or expected-failure tests are currently recorded.

## 3. Test inventory

There are 40 Python test files. Per-module counts verified by direct
`python -m unittest <module>` invocation:

| Module | Tests | Area |
|---|---:|---|
| `tests.lexer.test_lexer` | 30 | tokens, literals, escapes, diagnostics |
| `tests.lexer.test_tokens` | 3 | token representation |
| `tests.parser.test_parser` | 88 | grammar, AST shapes, syntax errors |
| `tests.test_chained_comparisons` | 4 | comparison-chain diagnostics |
| `tests.test_checker_order` | 3 | order-independent return inference |
| `tests.test_cli` | 83 | CLI modes, REPL, errors, streaming, file handling |
| `tests.test_codegen` | 46 | bytecode emission |
| `tests.test_csv` | 23 | CSV parsing and typed cells |
| `tests.test_definite_assignment` | 7 | definite-assignment analysis |
| `tests.test_diagnostics` | 30 | spans, hints, rendering, error types |
| `tests.test_docs` | 2 | docs contradiction guards |
| `tests.test_duplicate_declarations` | 5 | duplicate bindings/map keys |
| `tests.test_engine_parity` | 7 | interpreter/VM exception parity |
| `tests.test_engine_parity_table` | 1 | generic interpreter/VM output and environment parity |
| `tests.test_examples` | 4 | runnable examples and VM parity |
| `tests.test_files` | 2 | BOM-aware file reading |
| `tests.test_float_coercion` | 10 | Float storage/annotation coercion |
| `tests.test_host_exceptions` | 5 | host traceback boundary |
| `tests.test_identifier_syntax` | 3 | identifier rules |
| `tests.test_index_diagnostics` | 4 | index error span parity |
| `tests.test_interpreter` | 151 | interpreter semantics |
| `tests.test_list_assignment` | 7 | mutable list index assignment |
| `tests.test_list_builtins` | 23 | `append`, `first`, `last`, `sum` |
| `tests.test_list_slices` | 8 | list slicing |
| `tests.test_map_iteration` | 3 | map mutation during iteration |
| `tests.test_map_refinement` | 5 | empty-map refinement |
| `tests.test_packaging` | 5 | pyproject, CLI script, CI matrix/build gates |
| `tests.test_print_args` | 7 | multi-argument `print` |
| `tests.test_print_expression` | 7 | `print` as expression |
| `tests.test_reserved_words` | 6 | keyword-name diagnostics |
| `tests.test_string_builtins` | 19 | `upper`, `lower`, `contains`, `split` |
| `tests.test_string_slices` | 7 | string slicing |
| `tests.test_suite_layout` | 1 | no test classes after `unittest.main()` |
| `tests.test_type_checker` | 183 | types, inference, semantic errors |
| `tests.test_value_cycles` | 5 | cyclic value formatting |
| `tests.test_values` | 6 | value formatting |
| `tests.test_vm` | 140 | VM semantics and diagnostics |

**Total: 943 tests.**

The suite layout is guarded: duplicate test classes that used to appear after
`unittest.main()` were removed, and `tests.test_suite_layout` prevents them
from returning.

## 4. Coverage by concern

### 4.1 Compiler front end

- lexer tokens, spans, escapes, identifiers, comments
- parser precedence, AST construction, syntax diagnostics
- reserved words, chained comparisons, print-specific syntax
- diagnostics rendering, spans, hints, categories

### 4.2 Semantic analysis

- type inference, annotations, assignability, widening
- function argument/return checking and hoisting
- forward/mutual reference inference
- definite assignment
- duplicate bindings and duplicate map keys
- empty-map refinement and scalar key enforcement
- reserved built-in names

### 4.3 Interpreter and VM

- core expressions, statements, bindings, functions, control flow
- try/catch, throw, handler cleanup, catch scope
- list/map mutation, slicing, builtins, cycle formatting
- numeric edge cases, Float coercion, CSV and file I/O
- host-exception boundary and index error spans
- both checked-in examples run on the interpreter and match the VM

Parity is covered by `tests/test_engine_parity.py` and feature-specific paired
tests. `tests/test_engine_parity_table.py` adds a reusable `run_both_engines()`
helper that checks a program once and compares printed output and final
environments across both engines over a table of representative programs.

### 4.4 CLI and packaging

- all current CLI flags and modes
- source file vs inline source detection
- stdin source, REPL state, `--vm` REPL state
- streaming output before errors
- wheel metadata, console script, CI matrix/build gates

### 4.5 Measured statement coverage

Measured locally with `coverage.py` 7.17.5 on Python 3.14.1 at commit
`9f42b0b`:

```bash
python -m pip install coverage
python -m coverage erase
python -m coverage run --source=compiler,runtime,swarna -m unittest discover -s tests
python -m coverage report -m
```

The run executed all 943 tests successfully. Statement coverage by module:

| Module | Stmts | Miss | Cover |
|---|---:|---:|---:|
| `compiler/__init__.py` | 0 | 0 | 100% |
| `compiler/ast/__init__.py` | 0 | 0 | 100% |
| `compiler/ast/nodes.py` | 159 | 0 | 100% |
| `compiler/bytecode/__init__.py` | 0 | 0 | 100% |
| `compiler/bytecode/instructions.py` | 75 | 0 | 100% |
| `compiler/bytecode/program.py` | 24 | 0 | 100% |
| `compiler/codegen/__init__.py` | 0 | 0 | 100% |
| `compiler/codegen/compiler.py` | 448 | 31 | 93% |
| `compiler/csv_schema.py` | 41 | 1 | 98% |
| `compiler/diagnostics.py` | 69 | 0 | 100% |
| `compiler/lexer/__init__.py` | 0 | 0 | 100% |
| `compiler/lexer/lexer.py` | 195 | 7 | 96% |
| `compiler/lexer/tokens.py` | 62 | 0 | 100% |
| `compiler/parser/__init__.py` | 0 | 0 | 100% |
| `compiler/parser/parser.py` | 493 | 23 | 95% |
| `compiler/semantic/__init__.py` | 2 | 0 | 100% |
| `compiler/semantic/checker.py` | 853 | 54 | 94% |
| `runtime/__init__.py` | 0 | 0 | 100% |
| `runtime/csv.py` | 171 | 2 | 99% |
| `runtime/files.py` | 18 | 3 | 83% |
| `runtime/interpreter.py` | 571 | 47 | 92% |
| `runtime/values.py` | 116 | 13 | 89% |
| `runtime/vm.py` | 569 | 63 | 89% |
| `swarna/__init__.py` | 2 | 0 | 100% |
| `swarna/__main__.py` | 243 | 55 | 77% |

**Total: 4,111 statements, 299 missed, 93% statement coverage.**

This exceeds the blueprint's 85% core coverage target. The lowest-covered
modules are the CLI entry point (`swarna/__main__.py`, 77%), the VM (89%), and
`runtime/values.py` (89%); the uncovered lines are mostly interactive REPL
branches, rare error paths, and VM instruction handlers. This is a baseline,
not a gate: no `--fail-under` threshold, repository config, or CI step has been
added.

## 5. Known test gaps

These are absent or incomplete and are candidates for later blueprint tasks:

1. **Coverage gate** — baseline measured locally at 93% statement coverage
   (§4.5), but there is no repository config, declared dev dependency, or CI
   gate. The blueprint's 85% core coverage target is already met by the
   baseline.
2. **Golden fixtures** — no `tests/golden/` tree with source/expected pairs.
3. **Property-based tests** — no Hypothesis or equivalent.
4. **Fuzz tests** — no random token streams, deep nesting, malformed bytecode,
   or resource-limit harness.
5. **Benchmarks** — no reproducible performance suite.
6. **Lint/type checks** — no configured formatter, linter, or static type
   checker in CI.
7. **Structured diagnostics assertions** — many tests assert rendered strings;
   there are no stable diagnostic codes yet.
8. **Bytecode verifier tests** — no verifier exists.
9. **Docs example checking** — two example programs are tested; README code
   snippets are not automatically executed.
10. **Module/package tests** — modules and package manager are not implemented.

## 6. Current release gates

What CI currently enforces:

- full `unittest` suite passes on 15 OS/version combinations
- distribution builds
- wheel installs cleanly
- `swarna --version` works from the installed wheel
- a simple program runs from the installed CLI

What it does **not** yet enforce from blueprint §10.7:

- lint and static checks
- coverage target (baseline measured locally at 93%; not yet a CI gate)
- fuzz smoke tests
- golden fixture suite
- example/docs snippet checks
- dependency/security scans
- performance benchmarks

## 7. Baseline conclusion

The current suite is a strong regression baseline for the implemented language:
943 tests, all passing locally and across the declared CI matrix. The highest
value next testing work is not more feature tests, but **test infrastructure**:
a generic engine-parity harness, structured diagnostic assertions, and golden
fixtures. Coverage is now measured at 93% but is not yet a CI gate.

This baseline should be updated whenever supported Python versions, CI steps,
or the canonical test command change.
