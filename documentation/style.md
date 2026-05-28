# Brobier Code Style Guide

## Goal

Write code that is easy for a human to read in one pass.

Prefer straightforward code over clever code.

## Core Principles

1. Keep functions small and focused.
2. Use clear names for variables, functions, and files.
3. Avoid deep abstraction unless it removes real repeated complexity.
4. Accept small, local duplication when abstraction would hide intent.
5. Remove duplication once the same logic appears 3+ times or starts drifting.

## Simplicity Rules

- Prefer explicit control flow over metaprogramming.
- Keep nesting shallow. Use early returns.
- Avoid giant helper utilities that mix unrelated behavior.
- Use framework defaults unless there is a strong reason not to.
- Keep data transformations close to where they are used.

## Abstraction Rules

Create an abstraction only when all are true:

1. The logic is repeated and stable.
2. The shared behavior has one clear responsibility.
3. The new abstraction is easier to understand than the duplicated code.

If any of these are false, keep the logic inline for now.

## Duplication Guidelines

Good duplication:
- Two short route handlers with similar shape but different business rules.
- Small UI components that stay explicit for readability.

Bad duplication:
- Repeating auth, ownership checks, or encryption logic in many places.
- Copy-pasted validation logic with small differences.

When removing duplication:
- Extract the smallest useful function.
- Keep function names concrete.
- Do not create abstraction layers "just in case".

## Testing Policy

- Do not use mocking, monkeypatching, or similar test doubles unless explicitly requested.
- Prefer tests that exercise real code paths and real integrations in the local test environment.

## Backend Conventions

- Keep business rules in service layer, not in route handlers.
- Keep route handlers thin: validate input, call service, return response.
- Put shared security logic (hashing, encryption, auth checks) in dedicated modules.
- Prefer SQLModel query clarity over clever query composition.

## Frontend Conventions

- Keep pages focused on layout and page-level state.
- Move repeated UI pieces into small components.
- Do not create generic components too early.
- Keep API calls in api modules, not scattered across components.

## Readability Checklist

Before merge, verify:

1. Can a new teammate explain each function quickly?
2. Are names descriptive without extra comments?
3. Is there unnecessary indirection?
4. Is duplicated logic either intentional or extracted cleanly?
5. Does the code follow existing patterns in this repository?

## Non-Goals

- Perfection in DRY at the cost of clarity.
- Novel architecture patterns without clear need.
- Utility-first refactors that make call sites harder to read.

## Decision Heuristic

When in doubt:

- Choose the version that is easiest to read today.
- Keep change scope small.
- Refactor only after the pattern proves itself.
