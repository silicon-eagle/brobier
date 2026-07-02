---
description: "Use when implementing or modifying backend FastAPI/SQLModel code or frontend React/TypeScript code in Brobier. Enforces readability-first conventions, service-layer boundaries, and year-aware calendar/security rules."
name: "Brobier Code Style"
applyTo:
  - 'backend/**/*.py'
  - 'frontend/**/*.ts'
  - 'frontend/**/*.tsx'
---
# Brobier Coding Instructions

## Readability First

- Keep functions small and focused.
- Use clear, concrete names for files, functions, and variables.
- Prefer explicit control flow and early returns over clever abstractions.
- Keep nesting shallow.

## Abstraction and Duplication

- Allow small local duplication when it improves clarity.
- Extract shared logic only when repetition is stable and the abstraction is simpler than inline code.
- Do not add generic utility layers "just in case."

## Backend Rules

- Keep route handlers thin: validate input, call service, return response.
- Keep business rules in service modules, not route modules.
- Keep shared security logic centralized in dedicated modules (hashing, encryption, auth checks).
- Prefer clear SQLModel queries over clever composition.
- Use single quotes for all strings in Python (`'value'`, not `"value"`). Use double quotes only when the string itself contains a single quote.

## Frontend Rules

- Keep pages focused on page-level state and layout.
- Move repeated UI into small, concrete components.
- Do not create overly generic components too early.
- Keep API calls in api modules, not scattered across components.

## Domain and Security Invariants

- Calendar behavior is year-aware; preserve history across years.
- Do not expose encrypted database fields directly in API responses.
- Enforce locked/unlocked calendar response rules server-side.
- Keep ownership and role checks explicit for mutating endpoints.

## Testing and Validation

- Backend tests use pytest and pytest-asyncio.
- Frontend tests use Vitest and React Testing Library.
- Add or update tests when changing business rules, auth/session behavior, calendar unlock logic, or authorization.
- Do not use mocking, monkeypatching, or similar test doubles unless explicitly requested.
- Prefer tests that execute real code paths and integrations in the local test environment.

## Python Path Handling

- Always use `pathlib.Path` for all path operations in Python.
- Never use `os.path`, `os.getcwd()`, `os.chdir()`, or any other `os` module path functions.
- Use `Path.cwd()`, `path.chdir()`, `path / 'subdir'`, `path.read_text()`, etc. instead.



- Choose the version that is easiest to read today.
- Keep change scope small.
- Refactor only after a pattern clearly repeats.
- 
# Repository workflow instructions

- Never run `git` commands in this repository.
- The user exclusively controls all version control actions, including status, diff, add, restore, commit, push, pull, checkout, merge, rebase, and reset.

