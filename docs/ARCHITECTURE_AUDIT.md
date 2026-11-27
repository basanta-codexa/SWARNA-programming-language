# SWARNA Architecture Audit

**Date:** 2026-11-27  
**Commit:** `7966d50` (`remove duplicate test classes`)  
**Status:** verified snapshot; describes the repository as it exists today, not the target blueprint.

This document is the first deliverable of Task 1 in
`SWARNA_1.0_Production_Engineering_Blueprint.md`. It records verified facts
about the current architecture. Proposed future architecture belongs in ADRs,
not in this audit.

## 1. Evidence and baseline commands

Commands executed and observed results:

```bash
git status --short --branch
# ## main...origin/main
# ?? SWARNA_1.0_Production_Engineering_Blueprint.md
# ?? hello.sw

python --version
# Python 3.14.1

python -m unittest discover -s tests
# Ran 940 tests ... OK

python -m unittest discover -v
# Ran 940 tests ... OK
```

Local wheel verification was performed earlier in the project history:

```bash
python -m build
python -m pip install dist/swarna-0.1.0-py3-none-any.whl
swarna --version        # swarna 0.1.0
swarna --run "print(1 + 2)"  # 3
```

CI run #72 for this commit completed successfully. The current workflow runs
tests, builds the distribution, installs the wheel, and smoke-tests the CLI on
Ubuntu, Windows, and macOS with Python 3.10, 3.11, 3.12, 3.13, and 3.14.

Repository size at audit time:

- 25 Python source files under `compiler/`, `runtime/`, and `swarna/`
- 39 Python test files under `tests/`
- approximately 6,282 source lines and 6,118 test lines
- 60 bytecode opcodes in `compiler/bytecode/instructions.py`

## 2. Repository layout

```text
compiler/
  ast/          AST node definitions
  bytecode/     Op enum and CompiledProgram/FunctionInfo containers
  codegen/      AST-to-bytecode compiler
  lexer/        token types and lexer
  semantic/     TypeChecker and type model
  csv_schema.py CSV schema parsing shared by checker, interpreter, and compiler
  diagnostics.py DiagnosticError hierarchy and renderer

runtime/
  interpreter.py tree-walking execution backend
  vm.py          stack VM execution backend
  values.py      value formatting/coercion/cycle handling and runtime helpers
  files.py       safe text-file reading
  csv.py         CSV parsing and typed cell conversion

swarna/
  __main__.py   CLI, REPL, public helper functions used by tests

tests/          unit, parity, integration, and documentation guard tests
examples/       one CSV aggregation example and its fixture
docs/           design and positioning documents
```

There is no `stdlib/`, `hir/`, `modules/`, `memory/`, or `decisions/` directory
yet. Those appear only in the blueprint as proposed future structure.

## 3. Execution pipeline

### 3.1 Interpreter path

Entry point: `swarna/__main__.py:run_source()`.

```text
source text
  -> Lexer.tokenize()
  -> Parser.parse_program()
  -> TypeChecker.check(program)
  -> Interpreter.eval(program, checker.expression_types)
  -> interpreter.output values
  -> format_value() / print hook
```

`run_source()` can reuse an existing interpreter and function-signature table,
which is how the REPL preserves state across lines. The interpreter writes
each printed value to `Interpreter.output` and, when configured by the CLI,
to a `print_hook` that flushes immediately.

### 3.2 VM path

Entry point: `swarna/__main__.py:run_vm_source()`.

```text
source text
  -> Lexer.tokenize()
  -> Parser.parse_program()
  -> TypeChecker.check(program)
  -> Compiler(checker.expression_types).compile(program)
  -> VM.run(CompiledProgram(instructions, functions))
  -> vm.output values
  -> format_value() / print hook
```

`run_vm_source()` can reuse a `VM`, a compiled-function table, and a checker
signature table, which is how `--vm` REPL mode preserves state.

There is no typed HIR and no bytecode verifier. The compiler consumes the AST
directly. The VM consumes in-memory dataclass instructions, not a serialized
bytecode file.

### 3.3 Shared type information

`TypeChecker.check()` records inferred annotations per AST node in
`checker.expression_types`, keyed by `id(expr)`. The compiler and interpreter
use this map to insert runtime coercions for inferred `Int`→`Float` widening
and mixed numeric literals. Annotations on bindings are also tracked in
compiler/interpreter state so assignment and container writes coerce
consistently.

## 4. Component inventory

| Component | Responsibility | Main callers | Dependencies | Primary tests |
|---|---|---|---|---|
| `compiler/lexer/lexer.py` | Tokens, literals, comments, source spans, escape handling | Parser, CLI `lex_source` | `tokens.py`, `diagnostics.py` | `tests/lexer/test_lexer.py`, `tests/lexer/test_tokens.py` |
| `compiler/parser/parser.py` | Grammar, precedence, syntax diagnostics | CLI, tests | lexer, AST, token types | `tests/parser/test_parser.py`, `tests/test_chained_comparisons.py`, `tests/test_reserved_words.py` |
| `compiler/ast/nodes.py` | Frozen AST dataclasses | parser, checker, compiler, interpreter | diagnostics for spans | parser/AST assertions across parser tests |
| `compiler/semantic/checker.py` | Names, scopes, types, inference, definite assignment | CLI, VM path, tests | AST, diagnostics, `runtime.values`, csv schema | `tests/test_type_checker.py`, `tests/test_definite_assignment.py`, `tests/test_checker_order.py`, `tests/test_map_refinement.py` |
| `compiler/codegen/compiler.py` | AST-to-bytecode lowering, handler/catch bookkeeping, coercion emission | CLI VM path, tests | AST, bytecode, diagnostics, `runtime.values` | `tests/test_codegen.py`, VM and engine-parity tests |
| `compiler/bytecode/instructions.py` | `Op` enum and instruction representation | compiler, VM, tests | diagnostics for spans | codegen tests |
| `compiler/bytecode/program.py` | `CompiledProgram`, `FunctionInfo` containers | compiler, VM, CLI | AST annotations, instructions | codegen/VM tests |
| `compiler/csv_schema.py` | CSV schema parse/validation | checker, interpreter, compiler | diagnostics | `tests/test_csv.py`, `tests/test_type_checker.py` |
| `compiler/diagnostics.py` | `DiagnosticError` hierarchy, `render_diagnostic`, categories | all layers | none | `tests/test_diagnostics.py` |
| `runtime/values.py` | Value formatting, coercion helpers, cycle marker, slice/append/first/last/sum helpers | interpreter, VM, CLI, checker | diagnostics, AST annotations | `tests/test_values.py`, `tests/test_value_cycles.py`, feature tests |
| `runtime/interpreter.py` | Tree-walking execution, env/annotations/functions, try/catch, builtins | CLI `--run` path, tests | AST, diagnostics, compiler csv schema, runtime helpers | `tests/test_interpreter.py`, parity and feature tests |
| `runtime/vm.py` | Stack VM, call-frame state, handlers/catch scopes, iterators, builtins | CLI `--vm` path, tests | bytecode, diagnostics, runtime helpers | `tests/test_vm.py`, parity and feature tests |
| `runtime/files.py` | UTF-8-with-BOM text reading | interpreter, VM | diagnostics | `tests/test_files.py` |
| `runtime/csv.py` | CSV parsing and strict cell conversion | interpreter, VM | diagnostics, values | `tests/test_csv.py` |
| `swarna/__main__.py` | CLI flags, REPL, source helpers, wheel entry point | users, CLI tests | compiler and runtime modules | `tests/test_cli.py`, `tests/test_packaging.py` |

## 5. Interpreter and VM comparison

Both engines support the same documented language surface: bindings, control
flow, functions, exception handling, lists, maps, strings, slicing, mutable
list operations, string/list builtins, and `print`.

Verified parity areas include:

- try/catch scope and stale-handler behavior
- Float coercion for annotated and inferred values
- list/map mutation and index diagnostics
- string and list slicing
- builtins (`upper`, `lower`, `contains`, `split`, `append`, `first`, `last`, `sum`)
- REPL state persistence

Key implementation differences:

- The interpreter uses Python dicts for environments and a boolean constant
  map; the VM uses `env` plus a `constant` set and an operand stack.
- The interpreter dispatches AST nodes; the VM dispatches `Op` instructions.
- The interpreter evaluates builtins in `eval_call()`; the VM uses dedicated
  opcodes.
- Both engines share runtime helpers in `runtime/values.py` for formatting and
  many operations, but builtin dispatch is still implemented separately.

Parity is protected by `tests/test_engine_parity.py` and many paired feature
tests. There is not yet a single generic table-driven parity harness covering
all supported programs.

## 6. Runtime values and memory

Runtime values are native Python objects:

- scalars: `int`, `float`, `bool`, `str`
- `UNIT` singleton for `Unit`
- collections: Python `list` and `dict`

Memory management is CPython's automatic reference counting and cyclic GC.
SWARNA does not implement its own allocator, heap, or garbage collector. There
are no custom heap-managed object types.

Environments are Python dicts copied at function call boundaries. The VM also
maintains an operand stack, try-handler stack, catch-scope stack, and iterator
frames. No resource limits are currently configured beyond call-depth limits
and Python recursion limits.

## 7. Diagnostics

`compiler/diagnostics.py` defines `DiagnosticError` and subclasses for syntax,
semantic, name, type, runtime, and zero-division errors. Diagnostics carry an
optional `SourceSpan`, message, hint, explanation/category, and optional
external source text/name for CSV errors.

`render_diagnostic()` produces a caret snippet with hint and optional
explanation. The CLI renders diagnostics on stderr and returns exit code 1.
The CLI also catches a broad set of host exceptions as a final boundary, so
internal errors do not normally leak tracebacks.

Current gaps:

- no stable error codes such as `E0201`
- no explicit severity field
- no structured secondary labels or related diagnostics
- some tests assert rendered strings rather than structured diagnostic data

## 8. Packaging and CI

`pyproject.toml` uses setuptools 77+, PEP 639 license metadata, dynamic version
from `swarna.__version__`, and a console script `swarna = swarna.__main__:main`.
Runtime dependencies are empty.

CI (`.github/workflows/ci.yml`) runs on Ubuntu, Windows, and macOS across
Python 3.10–3.14. Each job runs the unittest suite, builds sdist and wheel,
installs the wheel, and smoke-tests `swarna --version` and a print program.

Known packaging debt:

- top-level `compiler` and `runtime` packages are generic and collision-prone
- package-level dependency inversion exists: compiler imports `runtime.values`
  while runtime modules import `compiler.*`
- no lint, type-check, coverage, dependency scan, or reproducible-build gate

## 9. Examples and documentation

`examples/` contains `team_averages.sw` and `scores.csv`.
`tests/test_examples.py` runs the example through the interpreter and checks
interpreter/VM parity for its final environment.

Current docs: `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`,
`docs/DESIGN_PRINCIPLES.md`, `docs/POSITIONING.md`, and `docs/VISION.md`.
`docs/DESIGN_PRINCIPLES.md` was corrected on 2026-11-27 to match implemented
behavior. The production blueprint is currently untracked in the repo root.

## 10. Architectural debt and next audit deliverables

Highest-value debt from this audit:

1. generic top-level package names and cross-layer imports
2. no typed HIR or shared semantic representation between engines
3. no bytecode verifier or serialized bytecode format
4. diagnostics lack stable codes and structured labels
5. no lint/type/coverage gates
6. only one realistic example program
7. blueprint and `hello.sw` are untracked

Remaining Task 1 audit documents to create next:

- `docs/EXISTING_LANGUAGE_BEHAVIOR.md`
- `docs/TEST_BASELINE.md`
- `docs/TECHNICAL_DEBT.md`

This audit intentionally recommends no broad rewrite. It records what exists so
the next steps can be small, evidence-based, and reviewable.
