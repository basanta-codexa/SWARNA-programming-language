# SWARNA Technical Debt Register

**Date:** 2026-11-27

**Status:** verified snapshot at commit `bbe7229`.

**Method:** source inspection, test runs, CI records, and command-line checks.

**Purpose:** rank known debt so work can proceed in small, reviewable steps.

This register describes current debt. It does not propose a large rewrite. Each
item includes evidence, impact, and the smallest useful next step. Items tied to
future 1.0 features are marked deferred rather than treated as defects.

## 1. Severity scale

| Severity | Meaning |
|---|---|
| High | User-visible correctness, safety, or release-blocking risk |
| Medium | Maintainability, portability, or credibility risk for a portfolio release |
| Low | Polish or deferred feature work with limited current impact |

## 2. Debt register

| ID | Severity | Area | Debt | Evidence | Smallest next step |
|---|---|---|---|---|---|
| D01 | High | Packaging | Generic top-level packages `compiler` and `runtime` are collision-prone | `pyproject.toml:22` includes `compiler*` and `runtime*` | Decide namespace policy; if migration is approved, add ADR before moving files |
| D02 | High | Architecture | Package-level dependency inversion between compiler and runtime | `compiler/semantic/checker.py:43` imports `runtime.values`; `runtime/interpreter.py:7-12` and `runtime/vm.py:10-15` import `compiler.*` | Write an ADR defining allowed dependency direction |
| D03 | High | Diagnostics | Diagnostics have categories but no stable codes, severity, or structured secondary labels | `compiler/diagnostics.py` has `category`, no `code=`/`E0NNN`/severity fields | Add structured diagnostic codes without changing rendered CLI output |
| D04 | High | Testing | PARTIAL — coverage baseline measured, but no gate or declared dev dependency | 93% statement coverage at `bbe7229` (docs/TEST_BASELINE.md §4.5); no CI coverage step | Declare coverage as a dev dependency and add a `--fail-under` gate after triaging low-coverage areas |
| D05 | High | Release | RESOLVED — 0.2.0 section cut with migration notes | `039c086`; `CHANGELOG.md` has `[Unreleased]` then `[0.2.0] - 2026-11-27` with Added/Changed/Fixed/Migration Notes | None; keep `[Unreleased]` empty between releases |
| D06 | Medium | VM | No bytecode verifier or serialized bytecode format | no verifier module; VM consumes in-memory `CompiledProgram`; 60 opcodes exist | Document actual opcode stack effects before designing verification |
| D07 | Medium | Architecture | No typed HIR; compiler consumes AST directly | no `hir/` directory; `Compiler.compile()` walks AST in `compiler/codegen/compiler.py` | Write HIR ADR; prototype only for existing supported constructs |
| D08 | Medium | Runtime | Builtin dispatch is duplicated in interpreter and VM | `Interpreter.eval_call()` and VM builtin opcodes implement overlapping behavior | Add a shared builtin specification/helper table where practical; preserve parity |
| D09 | Medium | Testing | RESOLVED — generic table-driven parity harness added | `bbe7229`; `tests/test_engine_parity_table.py` has `run_both_engines()` plus 8 cases; 941 tests OK on 3.10/3.13/3.14 | Extend `CASES` when new language features land |
| D10 | Medium | Testing | No golden fixtures, property-based tests, fuzz tests, or benchmarks | `tests/golden/`, fuzz harnesses, and benchmark suite are absent | Add golden fixtures first; fuzz/property work after release gates are stable |
| D11 | Medium | CI | CI has no lint, type-check, coverage, dependency scan, or docs-example checks | `.github/workflows/ci.yml` runs tests, build, install, CLI smoke only | Add one check at a time, starting with `git diff --check`/compileall and coverage baseline |
| D12 | Medium | Documentation | Required 1.0 docs are missing | no `LANGUAGE_SPEC.md`, `GRAMMAR.md`, `TYPE_SYSTEM.md`, `SECURITY.md`, `decisions/`, etc. | Create ADR directory and spec docs incrementally from this baseline |
| D13 | Medium | Documentation | The production blueprint is untracked in the repo root | `SWARNA_1.0_Production_Engineering_Blueprint.md` is untracked | Decide whether to move it under `docs/` and track it |
| D14 | Medium | Compatibility | RESOLVED — reserved builtins documented as a migration note | `039c086`; `CHANGELOG.md` Migration Notes cover `first`, `last`, `sum`, `append`, `upper`, `lower`, `contains`, `split` | Repeat the guidance in a language spec when one exists |
| D15 | Medium | CLI | Blueprint proposes subcommands while current CLI is flag-only | blueprint §9 lists `swarna run main.sw`; current CLI uses `--run` | Choose CLI grammar in an ADR before adding subcommands |
| D16 | Medium | Robustness | No parser nesting/input-size limits; VM has call-depth but no instruction/memory limits | parser recursion and VM dispatch are unbounded by policy; CPython recursion eventually raises `RecursionError` | Define configurable limits as a reliability feature, not a security sandbox |
| D17 | Low | Runtime | `format_value` handles cycles but deep acyclic nesting can still hit Python recursion limits | `runtime/values.py` uses recursive formatting with a cycle set only | Add depth guard with a clear diagnostic if it becomes user-visible |
| D18 | Low | Examples | Only one realistic example program | `examples/team_averages.sw` and `scores.csv`; `tests/test_examples.py` covers only that example | Add a language-tour example using functions, slices, lists, maps, and errors |
| D19 | Deferred | Language | No structs, enums, traits, generics, modules, closures, optional types, or `Result` | absent from AST, checker, runtime, and docs | Treat as blueprint Tasks 5–11 with ADRs; do not implement prematurely |
| D20 | Deferred | VM | No GC, optimizer, debugger, formatter, linter, or LSP | absent; blueprint §6–§9 proposes them | Gate behind correctness, benchmarks, and explicit ADRs |

## 3. Detailed notes on high-severity items

### D01–D02: packaging and layering

The distribution currently installs top-level `compiler` and `runtime`
packages. These names are generic and can collide with unrelated packages in a
user environment. The dependency direction is also mixed: the semantic checker
imports `runtime.values`, while runtime modules import compiler modules.

This is not a correctness bug today — tests and wheel installation pass — but
it is a maintainability and packaging risk. The smallest evidence-based step is
to record allowed dependency direction in an ADR before moving files.

### D03: diagnostic structure

`DiagnosticError` carries `message`, `span`, `hint`, `category`, `explanation`,
and optional external source text. It does not carry stable machine-readable
codes, severity, or secondary labels. The blueprint §5.4 target is therefore
not met.

Rendering already works well; the smallest step is to add codes internally
while preserving current CLI output.

### D04: coverage measurement

Baseline measured at `bbe7229`: 4,111 statements, 299 missed, 93% statement
coverage across `compiler/`, `runtime/`, and `swarna/` (docs/TEST_BASELINE.md
§4.5). This clears the blueprint's 85% core target. The remaining debt is
process: coverage is installed locally only, is not a declared dev dependency,
and has no CI gate. Low-coverage areas are the CLI REPL branches (77%),
`runtime/values.py` (89%), and the VM (89%).

### D05: release shape

RESOLVED at `039c086`. The changelog now has an empty `[Unreleased]` section
followed by a dated `0.2.0` section with Added, Changed, Fixed, Documentation,
and Migration Notes. The installed version is still `0.1.0`; bumping it and
tagging a release are separate steps, not part of this debt item.

## 4. Debt already retired

Earlier high-severity debt was fixed and verified. It should not be reopened
without new evidence:

- host Python tracebacks from huge integers and cyclic values
- `try`/`catch` handler corruption on `break`/`continue`
- interpreter/VM scoping divergence
- unsound function-order inference, definite assignment, empty-map refinement
- `Float` annotation/inference storage mismatch
- CLI output buffering on errors
- `--vm` REPL state loss
- CSV BOM/non-finite parsing errors
- stale design-principle contradictions
- duplicate test classes after `unittest.main()`
- narrow CI matrix and no wheel smoke test
- accumulated `[Unreleased]` changelog entries cut into a `0.2.0` section (`039c086`)
- reserved builtin names documented as a migration note (`039c086`)
- coverage baseline measured at 93% (`bbe7229`; gate still pending, see D04)
- generic interpreter/VM parity harness (`bbe7229`)

## 5. Prioritized next steps

Before calling the project portfolio-ready:

1. Create `docs/TECHNICAL_DEBT.md` — this document (done).
2. Cut a 0.2.0 changelog section with migration notes for reserved builtins — done at `039c086`.
3. Add a coverage baseline as a dev-only measurement — done at `c373805`, refreshed at `bbe7229`; gate still pending (D04).
4. Add a generic interpreter/VM parity harness — done at `bbe7229`.
5. Choose the CLI grammar (flags vs subcommands) in an ADR.
6. Add a language-tour example and test it in both engines.

Longer-term blueprint work (HIR, verifier, structs, enums, modules, tooling,
GC) should start only after these smaller items are complete.

## 6. Source of truth

This register is evidence-based. When an item is fixed, update it with the
commit hash and verification command rather than deleting the history. When a
proposed blueprint feature conflicts with current behavior, record the conflict
in an ADR before implementing it.
