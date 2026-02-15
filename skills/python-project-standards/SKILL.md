---
name: python-project-standards
description: Enforce opinionated Python engineering standards for new or existing Python codebases. Use when creating, modifying, reviewing, or maintaining Python projects, including package setup, dependency management, linting, type checking, testing, CLI development, and API service development. Apply when users ask for Python tooling setup, test strategy, architecture guidance, project scaffolding, or framework selection.
---

# Python Project Standards

## Overview

Apply these standards to all Python-related work. Treat deviations as errors unless the user explicitly overrides a rule.

## Required Toolchain

- Use `uv` exclusively for Python package/environment/dependency workflows.
- Do not use `pip`, `pip-tools`, `poetry`, `pipenv`, or `conda` unless explicitly requested.
- Use `ruff` exclusively for linting and formatting.
- Use `ty` exclusively for static type analysis.
- Use `prek` exclusively for pre-commit hook management.
- Use `pytest` exclusively for unit and integration tests.

## Command Conventions

- Prefer `uv run <tool>` for project-local tool execution.
- Install runtime dependencies with `uv add <pkg>`.
- Install dev dependencies with `uv add --dev <pkg>`.
- Run lint/format with `uv run ruff check .` and `uv run ruff format .`.
- Run type checks with `uv run ty check`.
- Run tests with `uv run pytest`.
- Run pre-commit hooks with `uv run prek run --all-files`.

## Testing Standard (Fake-Driven Testing)

- Follow fake-driven testing to enforce clean architecture boundaries.
- Define behavior at ports/interfaces first.
- Use fake adapters in tests before implementing real adapters.
- Keep domain/application logic independent from infrastructure.
- Prefer contract-style tests that validate behavior across fake and real implementations.
- Keep tests deterministic, isolated, and fast.
- Read `references/fake-driven-testing.md` before designing substantial test suites.

## CLI Standard

- Use `rich` for all terminal output in CLIs.
- Prefer clear, structured output (`Console`, `Table`, `Panel`, status/progress where useful).
- Avoid plain `print` for user-facing output unless explicitly requested.

## API Standard

- Use `fastapi` for HTTP APIs.
- Organize code around domain use-cases and dependency-injected interfaces.
- Keep framework concerns at the edge; keep core business logic framework-agnostic.

## Delivery Checklist

- Confirm Python dependencies and commands use `uv` only.
- Confirm linting/formatting is configured via `ruff`.
- Confirm static analysis is configured via `ty`.
- Confirm hooks use `prek`.
- Confirm tests run with `pytest` and follow fake-driven testing principles.
- Confirm CLI output uses `rich` when applicable.
- Confirm API services use `fastapi` when applicable.
