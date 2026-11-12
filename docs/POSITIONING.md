# SWARNA Positioning

Status: draft target. This file describes what SWARNA is trying to be and the test we will use to decide whether a feature belongs. It is not a claim that everything here works today. Current implemented features are in the README; accepted language decisions are in [DESIGN_PRINCIPLES.md](DESIGN_PRINCIPLES.md).

## One sentence

SWARNA is a small, statically checked language for getting a task done and understanding what went wrong.

## Who it is for

The primary user needs to compute something but does not consider themselves a programmer: an analyst cleaning a spreadsheet export, a researcher summarizing measurements, a teacher calculating grades, an engineer checking a calculation. They can learn a little code, but they do not want to learn a toolchain.

Experienced developers are the secondary user. A language that only works for beginners will not be used for real work. SWARNA should be pleasant for them too, but it does not need to win every workload.

## The bet

Most languages make the target user choose:

- Python is easy to start, but types are checked while the program runs, and a bad value can surface far from where it entered.
- Statically typed languages catch more before running, but they ask for annotations, build files, and vocabulary that the target user did not sign up for.

SWARNA's bet is that a small language with inferred static types, task-first libraries, and errors written for the person who has to fix them can be both easy to start and easy to trust.

This is not "no code." It is code that a motivated non-programmer can read, write, and repair.

## Four pillars

### 1. Errors that explain

Every user-facing error has a source location, a plain-language cause, and a concrete next action. A type error should say what was expected, what was found, and where. A bad CSV cell should name the file, row, column, and value. No host-language traceback reaches the user in normal operation.

The bar: a user can fix the error from the diagnostic alone, without searching the web.

### 2. Types without ceremony

Types are inferred and checked before the program runs. A ten-line script has no annotations, imports, or build step. Annotations are optional when they make an interface clearer. There is no silent coercion that loses data: `Int` and `Float` stay distinct, and converting a `Float` to an `Int` is explicit.

The bar: a type error is caught before the bad value is used, and the fix is local.

### 3. A task-first standard library

The standard library starts with the tasks the target user actually has: strings, lists, maps, files, CSV, JSON, dates, and math. Common tasks should not require a third-party package or a page of boilerplate. A gap in the standard library is a language gap.

The bar: the switch test below is short, readable, and has a useful failure mode without extra validation code.

### 4. One workflow from REPL to script

The REPL, the script runner, and the VM use the same semantics. There is no separate build step for small programs. Semicolons are optional; the formatter owns spacing. A program that works in the REPL can be saved as a file and run with one command.

The bar: a user can move from "try a line" to "run the file" without learning a second workflow.

## The switch test

The test is a small task a target user would actually have: read a CSV of scores, compute the average per team, and handle a bad score without hiding it.

Input `scores.csv`:

```
name,team,score
Ada,Blue,88
Grace,Blue,92
Linus,Red,79
Margaret,Red,n/a
```

The Python a target user might write on the first try:

```python
import csv

totals = {}
counts = {}
with open("scores.csv", newline="") as f:
    for row in csv.DictReader(f):
        score = float(row["score"])
        totals[row["team"]] = totals.get(row["team"], 0) + score
        counts[row["team"]] = counts.get(row["team"], 0) + 1

for team in sorted(totals):
    print(team, totals[team] / counts[team])
```

On this input, Python raises:

```
ValueError: could not convert string to float: 'n/a'
```

The traceback points at the `float(...)` line. It does not name the row or the person. To get a useful message, the user has to add validation code.

The SWARNA target:

```swarna
let rows = read_csv("scores.csv", { name: String, team: String, score: Float })
let averages = rows.group_by("team").mean("score")

for row in averages {
    print(row.team, row.mean)
}
```

On the same input, the target diagnostic is:

```
error: expected a number in column 'score'
  --> scores.csv:5:14
    |
  5 | Margaret,Red,n/a
    |              ^^^
    = hint: Replace 'n/a' with a number, or mark the row as missing.
```

This test is not runnable yet. Lists and `for` loops now exist, but maps, file I/O, and the CSV library are still milestones. The test is the bar for those features, not evidence that they exist. The target syntax is illustrative; names and shapes will be settled when the features are designed.

What the test is checking:

1. The SWARNA version is shorter and has no manual parsing or accumulator boilerplate.
2. The CSV reader validates the schema at the boundary, so a bad cell is named where it enters, not later in arithmetic.
3. The failure names the file, row, column, and value, and suggests a fix.
4. The same code works in the REPL and in a saved file.

The comparison is not "SWARNA vs. Python with a carefully written validation layer." It is "SWARNA vs. the Python a target user would write on the first try." Python is still a good language; the question is whether SWARNA removes a layer of boilerplate without making the program harder to read.

## What SWARNA is not

- Not a no-code or visual tool. Users write text.
- Not dynamically typed. Types are checked but inferred, so users rarely write them.
- Not a syntax clone of Python, Java, Rust, or Ruby. Familiar shapes are fine; the combination is the point.
- Not domain-specific. Finance and biology get libraries, not new syntax.
- Not a replacement for Python in large systems. SWARNA is general-purpose; it does not have to win every workload.

## Current status against the target

| Pillar | Today |
|---|---|
| Errors that explain | Implemented for lexer, parser, semantic, and current runtime errors, including function calls and lists. A minimal `--explain` mode adds a plain-language explanation for undefined-name errors; coverage will grow. |
| Types without ceremony | Inferred `Int`, `Float`, `String`, `Bool`, and `List[T]` for the current subset. Named functions with optional parameter and return annotations; unannotated returns are inferred. `for` loops over lists are checked and scoped. No maps, list annotations, or generics yet. |
| Task-first standard library | Not started. No standard library yet; only `print`, `len`, and built-in operators exist. |
| One workflow | REPL and `--run` exist; bindings, functions, and list types persist in the REPL. No formatter or file runner beyond `--run` yet. |

The switch test is the next concrete milestone. Until it runs and produces the diagnostic above, SWARNA is not ready for its target user.

## How this changes the roadmap

- Lists and maps come before broad syntax work; the switch test needs them. Lists, functions, and `for` loops are in place; maps are next.
- CSV and file I/O are not "later"; they are part of the first usable release.
- A feature that does not improve the switch test or the four pillars waits.
- The `--explain`/`why` diagnostic mode is a natural extension of pillar 1, not a separate product.
