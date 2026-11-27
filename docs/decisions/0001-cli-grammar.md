# ADR 0001: CLI grammar for 0.2.0

**Status:** Accepted

**Date:** 2026-11-27

**Deciders:** project maintainer

## Context

The current CLI is flag-based. `swarna/__main__.py:158-180` defines:

- `--version`
- a mutually exclusive mode group: `--lex`, `--parse`, `--emit-bytecode`,
  `--run`, `--vm`
- `--explain`
- one optional positional `source` argument: inline source, or a `.sw` path
  that runs by default; stdin or REPL when omitted

This surface is exercised by 83 tests in `tests/test_cli.py` and by the wheel
smoke test in CI (`swarna --version` and `swarna --run "print(1 + 2)"`).
`tests/test_packaging.py` asserts those CI smoke steps remain present.

The production blueprint §9 lists a candidate subcommand surface:

```bash
swarna run main.sw
swarna check main.sw
swarna build main.sw
swarna fmt .
swarna lint .
swarna test
swarna doc
swarna repl
swarna debug main.sw
```

The same section says: "Preserve existing CLI commands and flags. Add new
commands without breaking current usage", and that documented flags such as
`--lex`, `--parse`, `--emit-bytecode`, and `--vm` should remain compatible
unless a versioned migration is approved.

There is therefore no conflict to resolve by breaking the current CLI: the
blueprint itself requires compatibility. The open question is whether
subcommands become the canonical grammar now or only an additive alias layer
later.

## Decision

1. For 0.2.0 the canonical CLI grammar stays flag-based with one optional
   positional source argument. No subcommand parser is added.
2. Future subcommands from blueprint §9 may be added only as **additive
   aliases** that dispatch to the same implementation as the corresponding
   flags. No existing flag, default behavior, or positional-source behavior may
   be removed or change meaning.
3. Specifically, `swarna run main.sw` may later become an alias for
   `swarna --run main.sw`. The canonical short form remains `swarna main.sw`,
   because an existing `.sw` path already runs by default.
4. Making subcommands exclusive or canonical requires a new ADR, a versioned
   migration plan, updates to README and the CLI tests, and new CI smoke steps.
   It must not be done as an incidental parser refactor.

## Consequences

- Positive: no breaking change for users; the 83 CLI tests, wheel smoke test,
  and README examples keep working; blueprint §9 compatibility is satisfied.
- Positive: the ADR directory required by `docs/TECHNICAL_DEBT.md` D12 now
  exists, giving later decisions a stable home.
- Negative: flags are less discoverable than verb-style subcommands, and the
  help text does not advertise a command tree.
- Negative: a future `run` alias must be disambiguated from the existing
  positional-source detection, so it needs its own tests before release.

## Alternatives considered

- **Adopt subcommands now and keep flags as deprecated aliases.** Rejected:
  churn in tests, docs, and CI smoke steps with no user-visible benefit for
  0.2.0, and "deprecated" flags would still be a compatibility risk.
- **Unify on subcommands and remove flags.** Rejected: directly violates
  blueprint §9 and breaks the installed-wheel smoke test.
- **Leave the CLI grammar undocumented.** Rejected: without a recorded rule,
  a later tooling task could silently convert the parser to subcommands.

## Verification

```bash
python -m unittest tests.test_cli tests.test_packaging -v
# Ran 88 tests ... OK

python -m unittest discover -s tests
# Ran 941 tests ... OK

python -m swarna --version
# swarna 0.1.0

python -m swarna --run "print(1 + 2)"
# 3
```

Full suite also passed on Python 3.10 and 3.13. No CLI source was changed by
this ADR, so all existing behavior is preserved by construction.

## References

- `SWARNA_1.0_Production_Engineering_Blueprint.md` §9
- `swarna/__main__.py:158-180` (argument parser)
- `tests/test_cli.py`, `tests/test_packaging.py`
- `.github/workflows/ci.yml` (wheel smoke test)
- `docs/ARCHITECTURE_AUDIT.md` §8
- `docs/TECHNICAL_DEBT.md` D12 and D15
