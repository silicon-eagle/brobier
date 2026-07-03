# Frontend Setup Plan — Brobier

> Planning document only. This describes how to scaffold the `frontend/` directory.
> No application code is implemented here.

## Scope

* **Scaffolding + small foundation only.** No API client, auth logic, or real pages/business logic.
* Vite dev proxy to the backend (same-origin, so no CORS or cookie changes needed).
* Include Vitest + React Testing Library config with a few key unit tests, plus a Playwright e2e setup.
* Include ESLint, Prettier, and a short README.

## Stack

* React 19 (19.2.7+)
* Vite 8 (8.1.x)
* TypeScript 6
* Tailwind CSS v4.3 (via the `@tailwindcss/vite` plugin)
* React Router v8 (8.1.x) — package `react-router` (`react-router-dom` is legacy/removed). Declarative routing APIs such as `BrowserRouter`, `Routes`, and `Route` come from `react-router`.
* Vitest 4 + React Testing Library
* Playwright for e2e
* pnpm package manager (lockfile `pnpm-lock.yaml`)

> **Node requirement:** react-router 8 requires Node `>=22.22.0` (the highest floor; Vite 8 needs a lower floor). Pin `engines.node` to `>=22.22.0`. Peer requires react/react-dom `>=19.2.7`.

## Backend dev facts

* Backend runs on `http://localhost:8000`. Router prefixes: `/auth`, `/beers`, `/calendar`, `/leaderboard`, `/admin`, `/health`.
* Refresh cookie `brobier_refresh` is HttpOnly, `path=/auth`. Same-origin via the Vite proxy avoids CORS + cookie issues.
* Frontend code should use relative URLs like `/health` or `/auth/...`; calling `http://localhost:8000/...` directly bypasses the proxy.

## Steps

### Phase 1 — Project init

1. `frontend/package.json` —

   * deps: `react@^19.2.7`, `react-dom@^19.2.7`, `react-router@^8.1.0`
   * dev: `vite@8`, `@vitejs/plugin-react`, `typescript@5`, `@types/react`, `@types/react-dom`, `@tailwindcss/vite`, `tailwindcss@4.3`, `vitest@4`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `jsdom`, `@playwright/test`, `eslint`, `@eslint/js`, `typescript-eslint`, `globals`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`, `prettier`, `eslint-config-prettier`
   * scripts: `dev`, `build`, `preview`, `lint`, `typecheck`, `test`, `test:ui`, `e2e`, `format`, `format:check`
   * `engines.node`: `>=22.22.0` (react-router 8 requirement)
2. `tsconfig.json` + `tsconfig.node.json` (Vite React TS defaults, `strict: true`, path alias `@/` → `src`; include Vitest globals/types if using `globals: true`).
3. `index.html` at the frontend root with `#root` and `/src/main.tsx`.

### Phase 2 — Build config

4. `vite.config.ts` — add Vitest config typing (`/// <reference types="vitest/config" />` or import `defineConfig` from `vitest/config`); plugins `react()` + `tailwindcss()`; `server.proxy` mapping `/auth`, `/beers`, `/calendar`, `/leaderboard`, `/admin`, `/health` → `http://localhost:8000` (`changeOrigin`); `resolve.alias` `@` → `./src`; embedded Vitest `test` block (environment `jsdom`, globals, `setupFiles`).
5. `src/index.css` — `@import "tailwindcss";`
6. `.env.example` — `VITE_API_BASE_URL=""` (empty → same-origin via proxy). `frontend/.gitignore` (`node_modules`, `dist`, `coverage`, `test-results`, `playwright-report`, `.env`). Optional `.npmrc` for pnpm settings.

### Phase 3 — Foundation source (minimal shell only)

7. `src/main.tsx` — mount the React root, import `index.css`, wrap in `BrowserRouter` (imported from `react-router`).
8. `src/App.tsx` — minimal `Routes`/`Route` (imported from `react-router`) with a single placeholder route (`/` → simple Home placeholder). No auth/business logic.
9. Create the placeholder folder structure per spec so future work has a home: `src/api/`, `src/auth/`, `src/components/`, `src/layouts/`, `src/pages/`, `src/routes/`, `src/types/` (each with a `.gitkeep` or a single tiny placeholder). Keep minimal — no business code.
10. `src/vite-env.d.ts` (Vite client types).

### Phase 4 — Testing setup

11. `src/test/setup.ts` — import `@testing-library/jest-dom`.
12. Unit tests (key foundation only): `src/App.test.tsx` (renders placeholder) and a smoke test that the router renders. Keep to 1–2 tests proving the config works.
13. Playwright: `playwright.config.ts` (testDir `e2e/`, baseURL `http://localhost:5173`, `webServer` runs `pnpm dev`, `reuseExistingServer: true`). `e2e/home.spec.ts` — loads `/` and asserts the placeholder is visible.
14. ESLint config (`eslint.config.js` flat config with `typescript-eslint` + react-hooks recommended + prettier compatibility).

### Phase 5 — Docs

15. `frontend/README.md` — install, dev (proxy note), test, e2e commands. Keep short.
16. Prettier config (`.prettierrc`) and package scripts `format` / `format:check`.

## Relevant files (all new under `frontend/`)

* `frontend/package.json`, `tsconfig.json`, `tsconfig.node.json`, `index.html`
* `frontend/vite.config.ts`, `eslint.config.js`, `playwright.config.ts`
* `frontend/.env.example`, `frontend/.gitignore`, `frontend/.npmrc`, `frontend/.prettierrc`
* `frontend/README.md`
* `frontend/src/main.tsx`, `App.tsx`, `index.css`, `vite-env.d.ts`
* `frontend/src/test/setup.ts`, `src/App.test.tsx`
* `frontend/e2e/home.spec.ts`
* placeholder dirs: `src/{api,auth,components,layouts,pages,routes,types}`

## Verification

1. `cd frontend && pnpm install` succeeds.
2. `pnpm dev` starts on `:5173`; proxy forwards `/health` to the backend (manual check `http://localhost:5173/health` returns backend ok when the backend is running).
3. `pnpm typecheck` passes.
4. `pnpm build` produces `dist` without TS errors.
5. `pnpm lint` passes.
6. `pnpm format:check` passes.
7. `pnpm test` runs Vitest; foundation tests green.
8. `pnpm e2e` runs the Playwright home spec green (auto-starts or reuses the dev server).

## Decisions

* Proxy-based same-origin dev (chosen) — no CORS/cookie changes needed.
* Scaffolding only; NO API client, auth context, or real pages implemented now — just directory placeholders + minimal shell.
* Tailwind v4 via the official `@tailwindcss/vite` plugin (no PostCSS/`tailwind.config` needed for the v4 default).
* Keep `VITE_API_BASE_URL` empty in dev so requests are same-origin and hit the proxy.
* Include Prettier to avoid formatting noise.
* Include the short README because the proxy behavior is important project knowledge.

## Open considerations

None for this scaffold.
