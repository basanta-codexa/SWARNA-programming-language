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

Branches can be single expressions or block values. A block value runs its statements and uses its final expression as the branch value:

```
let total = if true {
    let base = 100
    base + 20
} else {
    100
}
```

Both branches must produce the same type. An `if` without `else` is only valid as a statement.

Reason: conditional values are common in real work: labels, defaults, formatting. Statement-only `if` forces a mutable temporary and more lines.

Status: implemented for the current language. `if` expressions with single-expression or block branches work in both the interpreter and the VM, and an `else` branch is required in expression position. The type checker enforces compatible branch types. A nested `if` statement before the final value of a block-valued branch is not supported yet; use a nested `if` expression as the final value.

### 4. Exceptions by default, `Result` by choice

Unhandled failures raise an exception with a source location and a readable message. `Result<T, E>` is available when a caller wants to handle failure as a value.

Reason: exceptions keep the common path linear. Forcing `Result` everywhere makes short scripts noisy. Explicit `Result` stays for code that must not unwind: library boundaries, batch jobs, anything that needs to continue after a failure.

Status: accepted, not yet implemented as a language feature. The runtime raises SWARNA diagnostic exceptions with source spans. The interpreter and VM now have call frames; a defined unwinding model and `Result` still need a dedicated error-handling design.

### 5. Word operators are accepted

`and`, `or`, and `not` work alongside `&&`, `||`, and `!`. Both forms produce the same AST.

Reason: `and` and `or` are readable to someone who has never seen C. The symbolic forms stay for people who prefer them.

Status: implemented. Both spellings produce the same AST and bytecode.

### 6. Braces and automatic formatting

Blocks use `{ }`. Semicolons are optional. A formatter owns indentation and spacing.

Reason: braces remove indentation ambiguity and keep parsing and tooling simple. Automatic formatting gives the visual calm of indentation-sensitive languages without the parser cost.

### 7. Inferred static types

Types are inferred and checked before execution. A ten-line script needs no annotations, imports, or build step. The detailed rules are in the Type checking section below.

Reason: a beginner should not have to write types to get the benefit of a type checker. Annotations stay available where an interface needs to be explicit.

Status: implemented as a separate pass for the current subset.

### 8. Functions are named declarations with expression bodies

```
fn add(a: Int, b: Int) -> Int {
    a + b
}

print(add(2, 3))
```

A function body is a block value: its statements run, and its final expression is the return value. There is no `return` keyword yet. Functions are declared at the top level and called by name. They are hoisted, so a call can appear before the declaration.

Parameter and return type annotations are optional. An unannotated parameter is `Unknown`; annotating parameters gives precise checking. An unannotated return type is inferred from the body after top-level statements are checked, so a top-level call to that function is checked as `Unknown`; annotate the return type when the call site needs precision. The REPL reuses the inferred signature on later lines. Function-local bindings do not leak. A function reads top-level bindings, and assignment inside a function changes a local copy rather than the global. Recursion and mutual recursion work.

Reason: functions are the next foundational feature. Named declarations are the smallest useful form; expression bodies reuse the block-value rule and avoid a separate `return` statement. Optional annotations keep scripts short while letting interfaces be checked.

Status: implemented in the interpreter, VM, and REPL. No first-class functions, `return`, nested declarations, expression statements, or global mutation yet. A function body must end with a value, so procedures are not supported.

### 9. Lists are built in and statically typed

```
let scores = [72, 85, 90]
print(scores[1])
print(len(scores))
```

A list is written `[value, value, ...]`. `values[index]` reads an element, and negative indices count from the end. `len(values)` returns the number of elements. `+` concatenates two lists, `==` and `!=` compare lists, and `print` shows a readable list.

Element types are inferred. `[1, 2, 3]` is `List[Int]`, and `[]` is `List[Unknown]` until it meets a known element type. Lists are homogeneous: `[1, 2.5]` is rejected; write `[1.0, 2.5]` for a list of floats. This matches the rest of the type system, which does not silently widen `Int` to `Float`.

Lists are immutable for now. Index assignment and append are not implemented. `for` loops iterate over lists and map keys; ranges and strings are not iterable yet. List annotations such as `List[Int]` are supported on parameters, returns, and bindings; an unannotated list parameter still infers what it can from the body and call sites.

Reason: lists are the first collection and the base for `for` loops, maps, and CSV rows. Homogeneous elements make inference and diagnostics useful without user-defined generics. Deferring mutation kept the first collection increment small; annotations were added once the collection model was stable.

Status: implemented in the interpreter, VM, REPL, and type checker. `for` loops over lists work. No list mutation or list methods yet. Maps have their own decision below.

### 10. `for` loops iterate over lists and map keys

```
let scores = [72, 85, 90]
let total = 0
for score in scores {
    total = total + score
}
print(total)
```

The loop variable takes the list's element type, or the map's key type. It is mutable and scoped to the loop. If an outer binding has the same name, the outer binding is restored after the loop. Declarations inside the loop body leak, matching `while` and `if`.

The iterable must be a `List[T]` or a `Map[K, V]`; an `Unknown` iterable is accepted and makes the loop variable `Unknown`. Iterating a map yields its keys in insertion order, so `totals[team]` reads the value. `break` exits the nearest loop and `continue` skips to the next iteration. There is no iteration over ranges or strings yet.

Reason: list iteration is the smallest useful loop over a collection, and map keys are the other shape the CSV and grouping work needs. Reusing the existing block and binding rules keeps the feature small.

Status: implemented in the type checker, interpreter, VM, REPL, and CLI. `for` loops iterate over lists and map keys.

### 11. Maps are built in and statically typed

```
let ages = { "Ada": 36, "Grace": 45 }
print(ages["Ada"])
print(len(ages))
```

A map is written `{ key: value, ... }`; `{}` is the empty map. `map[key]` reads a value and `len(map)` returns the number of entries. `==` and `!=` compare maps, and `print` shows a readable map such as `{"Ada": 36}`.

`map[key] = value` assigns an entry. It updates an existing key or adds a missing one:

```
let totals = { "red": 0 }
totals["red"] = totals["red"] + 5
totals["blue"] = 3
print(totals)
```

Key and value types are inferred. `{ "Ada": 36 }` is `Map[String, Int]`, and `{}` is `Map[Unknown, Unknown]` until it meets a known type. Maps are homogeneous in both positions: all keys share one type and all values share one type. Keys must be `Int`, `Float`, `String`, or `Bool` so they stay hashable at runtime; a list key is rejected before the program runs. Values may be any supported type, including nested maps.

A map binding must be declared with `let` to be assigned; a `const` map rejects index assignment. Lists stay immutable: `values[0] = x` is an error, and list elements are changed by building a new list with `+`. `get(map, key, default)` reads a key and returns `default` when the key is missing, which keeps accumulation from special-casing the first row. `for` loops iterate over map keys in insertion order. Map annotations such as `Map[String, Int]` are supported on parameters, returns, and bindings; an unannotated map parameter still infers what it can.

Reason: maps are the shape of a CSV row and the base for the switch test. Restricting keys to scalars keeps hashing and equality predictable without a custom protocol. Index assignment is the smallest mutation that makes grouping and aggregation possible; keeping lists immutable preserves the simpler list model until a real need appears.

Status: implemented in the interpreter, VM, REPL, and type checker. No insert or delete helper or map iteration yet. The runnable aggregation example is `examples/team_averages.sw`.

## Rules for changes

1. An error must name the problem and the fix. A diagnostic without a suggested action is incomplete.
2. No silent coercion that loses data. `Float` to `Int` is explicit.
3. A ten-line script needs no type annotations, imports, or build step.
4. Advanced features are opt-in. Generics, traits, and async never appear in a basic program.
5. A standard-library gap is a language gap. If a common task needs a third-party package to be reasonable, the task is not finished.
6. Every documented feature has a test. Documentation does not run ahead of the implementation.

## Diagnostics

Lexer, parser, semantic, and runtime errors carry a `SourceSpan` (line, column, length) and an optional hint. The CLI renders the offending source line, a caret, and the hint:

```
error: Expected '='
  --> 1:7
    |
  1 | let x 42
    |       ^^
    = hint: Bindings use `let name = value` or `const name = value`.
```

Semantic errors use the same shape:

```
error: Undefined name 'x'
  --> 1:9
    |
  1 | let y = x + 1
    |         ^
    = hint: Declare it first with `let name = value` or `const name = value`.
```

Runtime errors use the same shape:

```
error: division by zero
  --> 1:9
    |
  1 | print(1 / 0)
    |         ^
    = hint: The divisor must be non-zero.
```

Status: implemented for lexer, parser, semantic, and the current runtime errors in both the interpreter and the VM. A minimal `--explain` mode (and the REPL `:explain` toggle) appends a plain-language explanation; undefined-name and type-mismatch errors are the first covered categories. Explanations live in a category-keyed registry, so adding coverage does not repeat prose at every raise site.

## Type checking

The current language is statically checked but does not require annotations. A separate semantic pass infers `Int`, `Float`, `String`, `Bool`, `List[T]`, and `Map[K, V]`; an internal `Unknown` type suppresses cascading errors. Annotations are optional but checked when present, and a binding annotation sets the binding's type, so `let totals: Map[String, Float] = {}` starts with a precise map type.

The rules for the current subset:

- Literals infer their obvious type.
- A list literal infers a `List[T]` element type. All elements must have the same type, or be `Unknown`. An empty list is `List[Unknown]`. Nested lists infer nested element types.
- A map literal infers a `Map[K, V]` type. All keys must have one scalar type and all values one type, or be `Unknown`. An empty map is `Map[Unknown, Unknown]`. Nested maps infer nested value types. Keys must be `Int`, `Float`, `String`, or `Bool`.
- Indexing requires a list or a map. A list needs an `Int` index and produces the element type; a map needs a key assignable to `K` and produces `V`. Negative list indices are accepted at runtime and count from the end.
- Index assignment `map[key] = value` requires a mutable `let` map binding. The key must be assignable to `K` and the value to `V`. Assigning through a `const` binding is rejected, and a list index assignment is rejected because lists are immutable.
- `get(map, key, default)` requires a map, a key assignable to `K`, and a default assignable to `V`; it returns `V`. When `V` is `Unknown` (as in an empty map), the default's type becomes the result type.
- `len` accepts a list, a map, or a string and produces `Int`.
- `read_file` requires a `String` path and produces the file's text as `String`.
- `read_csv` requires a `String` path and a schema literal such as `{ name: String, score: Float }`. It returns `List[Map[String, Unknown]]`. The schema is checked against the file header and every cell at runtime; a bad cell points at its file, row, column, and value.
- `+` accepts two numbers, two strings, or two lists with the same element type. Mixed `Int`/`Float` arithmetic produces `Float`, but list element types must match exactly.
- `print` accepts any type, including lists and maps.
- List and map annotations use `List[T]` and `Map[K, V]`, including nested types such as `Map[String, List[Float]]`. A scalar type rejects type arguments; `List` needs one argument; `Map` needs two and its key must be a scalar type.
- A `let`/`const` annotation sets the binding's type and must accept the value. A function parameter or return annotation is checked against arguments and the body.
- `-`, `*`, and `/` accept numbers. `/` always produces `Float`.
- `//` requires two `Int` operands and produces `Int`.
- Equality accepts values of the same type, two numbers, or two lists or maps with compatible types. Ordered comparisons accept two numbers or two strings.
- `&&`, `||`, and `!` require `Bool`.
- `if` and `while` conditions require `Bool`.
- A `for` loop requires a `List[T]`, a `Map[K, V]`, or `Unknown`. The loop variable takes the element type `T` for a list, the key type `K` for a map (in insertion order), or `Unknown`. It is mutable and scoped to the loop. An outer binding with the same name is restored afterward. Body declarations leak, matching `while` and `if`. `break` and `continue` are only allowed inside a loop.
- Loop variables cannot conflict with functions or built-in names.
- Both branches of an `if` expression must produce the same type. `Int` and `Float` branches are not unified yet.
- An `if` expression branch may be a block value. Its statements run in the current scope, and its final expression determines the branch type.
- A binding keeps the type of its first value. Reassigning it to a different type is an error.
- Reassigning a `const` is a semantic error.
- Undefined names are semantic errors.
- `fn` declarations are hoisted, so a call can appear before the declaration. Duplicate function names and duplicate parameter names are errors.
- Parameter annotations are optional; an unannotated parameter is `Unknown`. Annotated parameter types may be scalar, `List[T]`, or `Map[K, V]`, including nested types.
- An annotated return type is checked against the body. An unannotated return type is inferred from the body after top-level statements are checked; a top-level call to that function is `Unknown`.
- Calls check the argument count and each annotated parameter type. A type error points at the argument that does not match.
- A function body runs in a local scope copied from the top-level bindings. Local bindings do not leak, and assignment to a top-level name changes the local copy, not the global.
- Function names and variable names must not conflict. Built-in names such as `print`, `len`, `get`, `read_file`, and `read_csv` are reserved: they cannot be used for functions, variables, or parameters.
- `print` accepts any type, including lists and maps.

The checker runs before execution in `--run` and before code generation in `--emit-bytecode`. `--parse` and `--lex` do not run it. In the executing REPL, the checker is seeded from the interpreter's current bindings and function signatures, so types and inferred function returns persist between lines without a second symbol table.

Division by zero remains a runtime error; the checker does not evaluate expressions.

Known gaps: no user-defined generics or type aliases, no list mutation, no iteration over ranges or strings, no first-class functions, no general block scoping beyond function calls, no definite-assignment analysis, no flow-sensitive merging of branch bindings, no `Int`/`Float` widening in assignments or `if` branches, and only the first semantic error is reported. Block values are currently available only as `if` expression branches and function bodies, and a nested `if` statement cannot appear before the final value of a block-valued branch; use a nested `if` expression as the final value. Function bodies must end with a value; procedures are unsupported. `#` starts a line comment; block comments are not supported. The interpreter and VM keep their runtime checks so they can still be tested independently.

Status: implemented as a separate pass for the current subset.

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

- Diagnostics were built before the type checker, and the checker reuses the same spans and hints.
- The standard library is ordered by real tasks: strings and interpolation, lists, maps, ranges, file I/O, CSV/JSON, dates, math.
- The REPL and formatter are part of the core experience, not v1.0 extras.
- Type inference is required, not optional, because rule 3 depends on it.

## Decision log

| # | Decision | Status |
|---|---|---|
| 1 | `/` true division, `//` integer division | Implemented |
| 2 | `let` mutable, `const` immutable | Implemented |
| 3 | `if` is an expression | Implemented |
| 4 | Exceptions by default, `Result` opt-in | Accepted, pending |
| 5 | `and` / `or` / `not` aliases | Implemented |
| 6 | Braces, optional semicolons, automatic formatting | Partly implemented |
| 7 | Inferred static types, no annotations required | Implemented (minimal) |
| 8 | Functions are named declarations with expression bodies | Implemented (minimal) |
| 9 | Lists are built in, homogeneous, and statically inferred | Implemented (minimal) |
| 10 | `for` loops iterate over lists and map keys | Implemented (minimal) |
| 11 | Maps are built in, homogeneous, and statically inferred | Implemented (minimal) |
| 12 | `read_file` returns UTF-8 text with file-level diagnostics | Implemented (minimal) |
| 13 | `read_csv` validates a schema at the boundary | Implemented (minimal) |
| 14 | Explicit `List[T]` and `Map[K, V]` annotations are optional | Implemented |
