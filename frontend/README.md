# Brobier Frontend

React + Vite + TypeScript scaffold for the Brobier frontend.

## Requirements

- Node `>=22.22.0`
- pnpm

## Install

```sh
pnpm install
```

## Develop

```sh
pnpm dev
# equivalent to: pnpm run dev
```

Starts the dev server on `http://localhost:5173`. API requests to `/auth`, `/beers`,
`/calendar`, `/leaderboard`, `/admin`, and `/health` are proxied same-origin to the
backend at `http://localhost:8000`, so no CORS or cookie configuration is needed.
Make sure the backend is running separately.

## Test

```sh
pnpm test        # Vitest unit tests
pnpm test:ui     # Vitest with UI
pnpm e2e         # Playwright e2e tests (auto-starts the dev server)
```

## Other scripts

```sh
pnpm typecheck     # tsc --noEmit
pnpm build         # production build
pnpm lint          # ESLint
pnpm format        # Prettier write
pnpm format:check  # Prettier check
```
