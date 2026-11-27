# Existing SWARNA Language Behavior

**Date:** 2026-11-27  
**Status:** descriptive baseline, not a proposed design.  
**Source of truth:** current source, tests, and CLI behavior at commit `1771fb9`.

This document records what SWARNA does today. It is the compatibility baseline
for Task 1 of `SWARNA_1.0_Production_Engineering_Blueprint.md`. Future changes
to these rules require an ADR and regression tests, not an undocumented edit.

## 1. Verification evidence

The following commands were used to verify the behavior described here:

```bash
python --version
# Python 3.14.1

python -m unittest discover -s tests
# Ran 940 tests ... OK

python -m swarna --version
# swarna 0.1.0

python -m swarna --run "print(1 + 2)"
# 3
```

CI runs the same suite plus build/install/CLI smoke tests on Ubuntu, Windows,
and macOS with Python 3.10 through 3.14.

## 2. Program structure and execution

A SWARNA program is a sequence of statements. There is no mandatory `main`
function; top-level statements execute directly.

```swarna
let x = 1
print(x)
```

Both execution backends are available:

- `python -m swarna --run ...` uses the tree-walking interpreter.
- `python -m swarna --vm ...` uses the bytecode VM.

Both engines share the same lexer, parser, checker, and printed-output
semantics. A persistent REPL is available in both modes; bindings and function
declarations survive across lines.

## 3. Lexical syntax

### 3.1 Identifiers

Identifiers use ASCII letters, digits, and underscore. They cannot start with
a digit. Non-ASCII identifier characters produce a syntax diagnostic.

```swarna
let user_name = "Ada"
let _hidden = true
```

### 3.2 Keywords

Reserved keywords include `let`, `const`, `true`, `false`, `if`, `else`,
`elif`, `while`, `for`, `in`, `break`, `continue`, `return`, `throw`, `try`,
`catch`, `fn`, `and`, `or`, and `not`. They cannot be used as binding or
function names.

### 3.3 Comments

`#` starts a line comment. Block comments are not supported.

### 3.4 String literals

String literals are double-quoted and cannot span physical lines. Use `\n` for
a newline. Supported escapes are `\"`, `\\`, `\n`, and `\t`; unknown escapes
are syntax errors.

```swarna
print("line one\nline two")
```

## 4. Types

Supported types:

| Type | Notes |
|---|---|
| `Int` | Arbitrary-precision Python-backed integer; parser/print limit of 4300 digits |
| `Float` | Finite IEEE-style float; `nan`/`inf` are rejected |
| `Bool` | `true` / `false` |
| `String` | Immutable text |
| `Unit` | Written `()`; result of some expressions and statements |
| `List[T]` | Homogeneous ordered list |
| `Map[K, V]` | Homogeneous map with scalar keys |

`Unknown` is an internal inference type. It suppresses cascading errors but is
not directly annotatable as a user-facing type.

### 4.1 Numeric rules

- `/` always produces `Float`, including `Int / Int`.
- `//` requires `Int` operands and produces `Int`.
- `%` accepts numeric operands.
- `Int` widens to `Float` where a `Float` is expected.
- `Float` to `Int` is not implicit; use `int(...)`.
- Division by zero is a runtime diagnostic.

### 4.2 Annotations

Bindings, parameters, and returns may be annotated:

```swarna
let score: Float = 1
fn double(x: Int) -> Int { x * 2 }
```

Annotations are checked. `let`/`const` annotations set the binding type;
reassignment must remain assignable to that type. Function return types are
checked against the body. Unannotated return types are inferred before call
sites are checked, including forward and mutual references.

## 5. Bindings and scope

- `let` declares a mutable binding.
- `const` declares an immutable binding. Assignment to a `const` is a semantic
  error.
- Redeclaring a binding in the same check is an error.
- A binding keeps the type of its first value.
- `let mut` is a migration error; `mut` was removed.

```swarna
let count = 1
count = count + 1

const limit = 10
limit = 11  # semantic error
```

Function bodies run in a local environment copied from top-level bindings.
Local declarations do not leak. Assignment to a top-level name inside a
function changes the local copy, not the global binding.

`if` and loop bodies currently leak declarations into the surrounding
environment, matching the existing block model. Loop variables are restored
after the loop.

## 6. Expressions and operators

Supported arithmetic: `+`, `-`, `*`, `/`, `//`, `%`.

Supported comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`. Chained comparisons
such as `1 < 2 < 3` are syntax errors; combine them with `&&`.

Boolean logic supports both word and symbol forms:

```swarna
let ok = a && b || !c
let also_ok = a and b or not c
```

String concatenation uses `+` only with another string. There is no implicit
conversion to or from `String`; use `str(...)`, `int(...)`, or `float(...)`.

List concatenation uses `+` with compatible element types.

## 7. Control flow

### 7.1 `if`

`if` is both a statement and an expression. A value-producing `if` expression
requires a final `else`. Statement-form `if` may omit `else`.

```swarna
let label = if score >= 50 { "pass" } else { "fail" }

if score >= 50 {
    print("pass")
}
```

`else if` and `elif` chains are supported.

Branches must produce compatible types. `Int` and `Float` branches unify to
`Float`, with runtime coercion applied.

### 7.2 Loops

`while` uses a `Bool` condition. `for` iterates over lists, map keys, strings,
and `range(...)` results.

```swarna
for x in [1, 2, 3] { print(x) }
for k in totals { print(k) }
for c in "abc" { print(c) }
for i in range(3) { print(i) }
```

`break` exits the nearest loop. `continue` skips to the next iteration.
Declarations in loop bodies leak; the loop variable itself is restored.

### 7.3 Functions

Functions are declared with `fn`, hoisted, and may call each other regardless
of declaration order.

```swarna
fn add(a: Int, b: Int) -> Int { a + b }
fn twice(x: Int) -> Int { add(x, x) }
```

- Optional parameter and return annotations are checked.
- Recursion and mutual recursion are supported.
- `return` exits a function; it does not exit arbitrary blocks.
- A block without an explicit final expression produces `Unit`.
- Function values, nested functions, and closures are not implemented.
- Function names and built-in names are reserved.

## 8. Collections and indexing

### 8.1 Lists

List literals are homogeneous. Mixed numeric literals widen to `Float`.

```swarna
let xs = [1, 2, 3]
print(xs[0])
print(xs[-1])
```

Lists declared with `let` support index assignment and `append`:

```swarna
xs[0] = 9
append(xs, 4)
```

Slicing uses `values[start:end]`, with either bound omitted and negative bounds
allowed. Bounds are clamped by Python slice semantics. Slice bounds must be
`Int`. Slicing returns a new list.

### 8.2 Maps

Map literals use `key: value` entries. Keys must be scalar: `Int`, `Float`,
`String`, or `Bool`. Values are homogeneous.

```swarna
let totals: Map[String, Float] = {}
totals["Ada"] = 90.0
print(get(totals, "Grace", 0.0))
```

- Map index assignment requires a mutable `let` binding.
- `const` maps reject index assignment.
- `get(map, key, default)` returns the default when the key is missing.
- `for k in map` iterates keys in insertion order.
- Empty maps refine to their first assigned key/value types.
- Duplicate literal keys are semantic errors.

### 8.3 Strings

Strings are immutable. They support indexing and slicing but not element
assignment. Empty slices and negative indices are allowed. Out-of-range single
index access is a runtime diagnostic.

## 9. Built-ins

Current built-ins:

| Built-in | Behavior |
|---|---|
| `print(value, ...)` | Statement or expression; joins multiple values with `, `; as expression returns `Unit` |
| `len(x)` | Length of list, map, or string |
| `get(map, key, default)` | Safe map lookup |
| `range(start, stop?, step?)` | Produces `List[Int]` |
| `input()` | Reads one stdin line without trailing newline |
| `int(x)` | Converts Int/Bool/Float/whole-number String; rejects non-finite Float |
| `float(x)` | Converts numeric value/finite String; rejects non-finite results |
| `str(x)` | Produces a String representation |
| `read_file(path)` | Reads UTF-8 text, stripping BOM |
| `read_csv(path, schema)` | Reads typed CSV rows with source spans for bad cells |
| `upper(text)` | Uppercase String |
| `lower(text)` | Lowercase String |
| `contains(text, part)` | Returns `Bool` |
| `split(text, sep)` | Returns `List[String]`; empty separator rejected |
| `append(xs, value)` | Mutates a `let` list; returns `Unit` |
| `first(xs)` / `last(xs)` | Return first/last element; empty list is runtime error |
| `sum(xs)` | Sums `List[Int]` or `List[Float]` |

All built-in names are reserved and cannot be used for user functions,
variables, or parameters.

## 10. Error handling

SWARNA v1 supports `throw` and `try`/`catch`:

```swarna
try {
    throw "something went wrong"
} catch error {
    print(error)
}
```

- `throw` requires a `String` message.
- `catch` binds the error message as a `String`.
- Try and catch blocks have separate scopes.
- Caught errors continue after the `try`/`catch`.
- Unhandled errors terminate the CLI with exit code 1.
- `Result<T, E>` is not implemented.

Runtime diagnostics carry source spans and hints where applicable. The CLI
streams printed output immediately, so output before an error is preserved.

Cyclic containers are printed as `<cycle>`. Mutating a map while iterating it
raises a catchable runtime diagnostic.

## 11. Diagnostics

Diagnostic errors include:

- message
- optional source span
- optional hint
- category such as `undefined-name` or `type-mismatch`
- optional external source name/text for CSV errors

Stable error codes, severity fields, and secondary labels are not implemented
yet.

## 12. CLI behavior

Current flags:

```bash
swarna --version
swarna --lex "let x = 42"
swarna --parse "let x = 1 + 2"
swarna --emit-bytecode "let x = 1 + 2"
swarna --run "print(1 + 2)"
swarna --vm "print(1 + 2)"
```

A `.sw` file argument runs by default. A non-existent path-like argument
produces a `file not found` diagnostic instead of being lexed as source. Source
can be piped through stdin. With no source and an interactive terminal, the CLI
starts a REPL with `:lex`, `:parse`, `:bytecode`, `:run`, and `:vm` prefixes.

There is no subcommand-style CLI such as `swarna run main.sw` yet.

## 13. Compatibility baseline

The following are intentional current behaviors and must not be changed
without an ADR:

- `/` produces `Float`; `//` requires `Int`.
- `let` is mutable and `const` is immutable.
- Lists and maps are homogeneous; keys are scalar.
- `Int` widens to `Float`, but `Float` to `Int` is explicit.
- `if` expressions require a final `else`.
- Functions are hoisted and have local scope.
- No general block scoping beyond functions, loop-variable restoration, and
  catch-scope isolation; `if` and loop body declarations leak.
- Built-in names and keywords are reserved.
- `print` is both a statement and a `Unit`-returning expression.
- Errors have spans/hints but no stable codes yet.
- The interpreter is the default CLI engine; `--vm` is explicit.

## 14. Known limitations

Not implemented: structs, enums, pattern matching, traits, generics, modules,
imports, package management, first-class functions, closures, optional types,
sets, tuples, user-defined types, `Result`, bytecode verifier, formatter,
linter, debugger, LSP, and custom garbage collection.

This document intentionally does not describe those proposed features. See
the production blueprint for future direction.
