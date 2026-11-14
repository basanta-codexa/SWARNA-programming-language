# Contributing to SWARNA

Thanks for your interest in improving SWARNA. This project is developed incrementally with small, focused commits.

## Prerequisites

- Python 3.10+
- No third-party runtime dependencies

## Getting started

```bash
git clone https://github.com/basanta-codexa/SWARNA-programming-language.git
cd SWARNA-programming-language
python -m pip install -e .
```

Run the CLI:

```bash
python -m swarna --run "print(1 + 2)"
# or, if installed:
swarna --run "print(1 + 2)"
```

## Running tests

Run the full test suite before opening a pull request:

```bash
python -m unittest discover -s tests -v
```

CI runs the same test suite on supported Python versions for pushes and pull requests.

## Making changes

- Keep changes **small and focused**. Prefer one logical change per commit (feature/fix + its tests + relevant docs).
- Follow the existing code style and project structure (`compiler/`, `runtime/`, `swarna/`, `tests/`, `docs/`).
- Add or update tests for any behavior change. Documented features should have tests.
- If you change language behavior or diagnostics, update `README.md` and/or `docs/DESIGN_PRINCIPLES.md` / `docs/POSITIONING.md` as appropriate.
- Keep diagnostics helpful: include a clear message, source location/span where possible, and a hint when applicable.
- Do not commit generated artifacts (e.g. `__pycache__/`, `*.pyc`, build outputs).

## Design direction

See [docs/DESIGN_PRINCIPLES.md](docs/DESIGN_PRINCIPLES.md) and [docs/POSITIONING.md](docs/POSITIONING.md) for the project goals and accepted decisions. When in doubt, prefer changes that improve correctness, diagnostics, and the documented "switch test" path.

## Pull requests

- Describe what changed and why.
- Note any user-visible behavior or documentation updates.
- Ensure the test suite passes locally.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
