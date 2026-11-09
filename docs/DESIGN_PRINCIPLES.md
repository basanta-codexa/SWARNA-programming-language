# SWARNA Design Principles

This file records the decisions that shape SWARNA. It exists so future changes can be judged against stated goals instead of taste. A decision can change, but changing one requires a reason, a migration note, and an update to this file.

## Who SWARNA is for

SWARNA is a general-purpose language for people who need to compute something but do not consider themselves programmers: analysts, researchers, teachers, and engineers working outside software. It should also be reasonable for experienced developers, because a language that only works for beginners does not get used for real work.

The target is not "no code." The target is code that a motivated non-programmer can read, write, and repair without a computer science background.

## What "easy" means

Easy is not a property of syntax alone. We treat it as five layers, all of which have to hold up:

| Layer | What the user gets |
|---|---|
| Syntax | Few symbols, familiar shapes, optional ceremony |
| Semantics | Predictable rules, no silent data loss |
| Diagnostics | A location, a plain explanation, and a suggested fix |
| Standard library | Strings, collections, files, CSV/JSON, dates, math |
| Tooling | REPL, formatter, autocomplete, examples that run |

A clean grammar with a bad error message is still a hard language.

## Accepted decisions

### 1. `/` is true division; `//` is integer division

`7 / 2` is `3.5`. `7 // 2` is `3`, and `-7 // 2` is `-4` (floor division, matching Python).

`/` returns `Float` for numeric operands. `//` requires `Int` operands and returns `Int`; passing a `Float` raises `TypeError`. Converting a `Float` to an `Int` requires an explicit operation.

Reason: people outside programming expect division to divide. Truncating integer division is a quiet source of bugs, and one extra character for floor division is a small price.

Status: implemented in the interpreter and VM. `/` always produces `Float`; `//` floors toward negative infinity.

### 2. `let` is mutable; `const` is immutable

`let x = 1` creates a binding that can be reassigned. `const x = 1` creates one that cannot.

`const` means "cannot be reassigned." It does not promise compile-time evaluation.

Reason: the spreadsheet and scripting mental model is reassignment. Requiring `mut` on every counter adds friction for the audience we are targeting. Immutability remains available where it matters, and reassigning a `const` will produce a specific diagnostic.

Status: implemented. `let` is mutable, `const` is immutable, and `mut` was removed. Both the interpreter and the VM reject assignment to a `const`. `let mut` now produces a migration error.

### 3. `if` is an expression

```
let label = if score >= 50 { "pass" } else { "fail" }
```

Both branches must produce compatible types. An `if` without `else` produces unit and is only valid where a statement is expected.

Reason: conditional values are common in real work: labels, defaults, formatting. Statement-only `if` forces a mutable temporary and more lines.

Status: partly implemented. `if` expressions with a single expression per branch work in both the interpreter and the VM, and an `else` branch is required in expression position. Multi-statement branches, block values, and static branch-type compatibility are pending.

### 4. Exceptions by default, `Result` by choice

Unhandled failures raise an exception with a source location and a readable message. `Result<T, E>` is available when a caller wants to handle failure as a value.

Reason: exceptions keep the common path linear. Forcing `Result` everywhere makes short scripts noisy. Explicit `Result` stays for code that must not unwind: library boundaries, batch jobs, anything that needs to continue after a failure.

Status: accepted, not yet implemented. The interpreter currently raises host exceptions. The VM will get a defined unwinding model when functions and call frames exist.

### 5. Word operators are accepted

`and`, `or`, and `not` work alongside `&&`, `||`, and `!`. Both forms produce the same AST.

Reason: `and` and `or` are readable to someone who has never seen C. The symbolic forms stay for people who prefer them.

Status: implemented. Both spellings produce the same AST and bytecode.

### 6. Braces and automatic formatting

Blocks use `{ }`. Semicolons are optional. A formatter owns indentation and spacing.

Reason: braces remove indentation ambiguity and keep parsing and tooling simple. Automatic formatting gives the visual calm of indentation-sensitive languages without the parser cost.

## Rules for changes

1. An error must name the problem and the fix. A diagnostic without a suggested action is incomplete.
2. No silent coercion that loses data. `Float` to `Int` is explicit.
3. A ten-line script needs no type annotations, imports, or build step.
4. Advanced features are opt-in. Generics, traits, and async never appear in a basic program.
5. A standard-library gap is a language gap. If a common task needs a third-party package to be reasonable, the task is not finished.
6. Every documented feature has a test. Documentation does not run ahead of the implementation.

## Diagnostics

Lexer and parser errors carry a `SourceSpan` (line, column, length) and an optional hint. The CLI renders the offending source line, a caret, and the hint:

```
error: Expected '='
  --> 1:7
    |
  1 | let x 42
    |       ^^
    = hint: Bindings use `let name = value` or `const name = value`.
```

Runtime diagnostics will use the same shape once the runtime carries source spans.

Status: lexer and parser errors implemented. The CLI reports runtime errors without source spans yet.

## Non-goals

- No visual or no-code interface. Users write text.
- No indentation-sensitive grammar. Braces, with automatic formatting.
- Not dynamically typed. Types are checked but inferred, so users rarely write them.
- Not domain-specific. Finance and biology get libraries, not new syntax.
- Not a replacement for Python in large systems. SWARNA is general-purpose; it does not have to win every workload.

## How we will measure ease

- Clean checkout to first successful program using only the README: under five minutes.
- At least 90% of parser, type, and runtime errors include a source span and a suggested fix.
- At least three domain examples run end-to-end in CI: data cleaning, text processing, and a numeric task.
- No host-language traceback reaches a user in normal operation.
- A first-hour path covers variables, arithmetic, strings, `if`, `while`, lists, maps, functions, file reading, and one small program, with docs and tests for each.

## What this changes in the roadmap

- Diagnostics come before the type checker, not after it.
- The standard library is ordered by real tasks: strings and interpolation, lists, maps, ranges, file I/O, CSV/JSON, dates, math.
- The REPL and formatter are part of the core experience, not v1.0 extras.
- Type inference is required, not optional, because rule 3 depends on it.

## Decision log

| # | Decision | Status |
|---|---|---|
| 1 | `/` true division, `//` integer division | Implemented |
| 2 | `let` mutable, `const` immutable | Implemented |
| 3 | `if` is an expression | Partly implemented |
| 4 | Exceptions by default, `Result` opt-in | Accepted, pending |
| 5 | `and` / `or` / `not` aliases | Implemented |
| 6 | Braces, optional semicolons, automatic formatting | Partly implemented |
