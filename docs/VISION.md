# SWARNA Vision

This document defines what SWARNA is trying to become and how major features (including error handling and object-oriented modeling) should be designed. SWARNA is **not a clone** of existing languages; familiar ideas may be used only when they fit SWARNA’s goals and can be made simpler, safer, or more coherent.

## Ambition

Build a language that can **compete with popular languages for real work** by being dramatically better in clarity, correctness feedback, and ease of building reliable programs — without sacrificing a path to performance and serious tooling.

SWARNA should win by coherence and developer experience, not by copying feature lists.

## Target users and use cases

- **Primary:** motivated non-programmers and domain experts (analysts, researchers, teachers, engineers outside software) who need to compute, automate, and process data.
- **Secondary:** experienced developers who want a small, readable, dependable language for scripts, tools, and data-oriented programs.
- **Initial sweet spot:** scripting, data transformation/analysis (files, CSV/structured data), and small reliable tools with excellent diagnostics.

## Core differentiators (what SWARNA should be best at)

1. **Readable, low-ceremony code** — code that can be written and repaired without a CS background, while remaining precise enough for real programs.
2. **Outstanding diagnostics and debuggability** — every failure should explain what happened, where, and how to fix it; tooling should make the right thing obvious.
3. **Predictable, safe-by-default semantics** — no silent data loss, explicit conversions where meaning changes, clear mutability and scoping rules.
4. **Batteries-included practicality** — strong standard library and tooling for common tasks (text, collections, files/data formats, time/math), with a simple module/package story.
5. **Coherent growth path** — advanced capabilities (types, abstraction, concurrency, performance) are added in forms that stay consistent with the core.

## Design principles for new features

- **Compose, don’t bolt on:** features must fit existing semantics (expressions/blocks, `Unit`, explicit types, diagnostics model).
- **Simple first, powerful later:** ship the smallest useful form with clear rules; avoid complex hierarchies and special cases.
- **Explicit over surprising:** implicit behavior is allowed only when safe, predictable, and broadly beneficial (e.g. limited numeric widening) — never silent data loss or magic.
- **Errors are part of the language experience:** handling and propagation must preserve SWARNA-quality diagnostics.
- **Data modeling should be first-class:** prefer named, typed structures over ad-hoc maps for non-trivial programs.

## Feature direction: Error handling (SWARNA-native)

**Goal:** make failure handling explicit and ergonomic while keeping SWARNA’s “exceptions by default, high-quality diagnostics” philosophy.

**Proposed model (incremental):**
- **Structured errors:** runtime/user errors carry `message`, optional `kind`/category, and source context; errors remain diagnostic-quality.
- **`throw` / `fail` (naming TBD):** raise a structured error from user code.
- **`try { ... } catch e { ... }` (and optional `finally` later):** recover from runtime/user errors in a scoped, readable way. `e` provides access to error details (message/kind) without losing diagnostic context.
- **Propagation-friendly design:** keep error flow compatible with `return`, loops, and future `Result`/interop patterns (e.g. consider a propagation operator later, but do not require it now).
- **Not a clone:** avoid complex checked-exception hierarchies; prefer simple, explicit, composable handling.

**First implementation target:** minimal `try/catch` for runtime errors + a basic `throw/fail` for user errors, with full interpreter/VM/checker parity and diagnostics preserved.

## Feature direction: Object-oriented modeling (SWARNA-native)

**Goal:** provide powerful abstraction and encapsulation for real programs without inheriting the complexity of class-hierarchy-heavy OOP.

**Proposed model (incremental):**
- **Records/structs (user-defined types):** named types with typed fields, value construction, and field access (e.g. `Point { x: 1, y: 2 }`, `p.x`). This replaces ad-hoc maps for structured data.
- **Methods / associated behavior:** functions associated with types for encapsulation and readable APIs (e.g. method-call syntax or `impl`-style blocks — syntax TBD, semantics first).
- **Interfaces/traits/protocols:** behavior contracts for polymorphism and generic programming without mandatory inheritance.
- **Composition over inheritance:** prefer embedding/composition and traits; **no classical inheritance hierarchy in the initial model**. Revisit only if a clear, simple use-case demands it.

**Why this fits SWARNA:** delivers core OOP benefits (encapsulation, abstraction, polymorphism, modular modeling) in a simpler, more predictable form aligned with explicit types and diagnostics.

**First implementation target:** `struct`/record definitions + construction + typed field access (foundation for methods/traits).

## Near-term roadmap (foundations for differentiation)

1. **Error handling v1:** minimal `try/catch` and `throw/fail` with structured, diagnostic-quality errors.
2. **User-defined types v1:** structs/records + field access + type checking.
3. **Methods/behavior v1:** methods or associated functions on user-defined types.
4. **Modules/imports:** real code organization and reuse.
5. **Standard library & data tooling:** richer collections/strings, files/JSON/CSV ergonomics, and practical utilities.
6. **Tooling excellence:** formatter, LSP/editor support, better multi-diagnostics, and REPL improvements.
7. **Performance path:** optimize VM/bytecode and define a longer-term execution strategy.

## Non-goals (for now)

- Cloning syntax/semantics of Python, Java, C++, or JavaScript for familiarity alone.
- Complex class inheritance hierarchies, metaprogramming-heavy features, or implicit magic that obscures behavior.
- Sacrificing diagnostics, simplicity, or semantic clarity to add features quickly.
