# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `break` and `continue` statements for `while` and `for` loops (lexer, parser, type checker, interpreter, VM, codegen, and tests).
- Packaging via `pyproject.toml`, editable installs, `swarna` console-script entry point, and `swarna.__version__`.
- Continuous integration workflow to run the test suite on Python 3.10–3.12.
- MIT `LICENSE`.
- `CONTRIBUTING.md` with development and contribution guidelines.
- This changelog.
- `--version` CLI flag.
- Running source files directly from the CLI (pass a `.sw` file path as the `source` argument).

### Changed
- Documentation (`README.md`, `docs/DESIGN_PRINCIPLES.md`) updated to reflect `break`/`continue` support and direct file execution.
