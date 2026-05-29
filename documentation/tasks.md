# Brobier Implementation Tasks

This checklist is derived from documentation/spec.md and is organized by backend and frontend workstreams.

Task ID format:
- Backend: `BE-<section>.<item>` (example: `BE-3.4`)
- Frontend: `FE-<section>.<item>` (example: `FE-5.2`)
- Milestones: `MS-<letter>` (example: `MS-D`)

## Backend Tasks

### 1. Project and Runtime Setup
- [x] `BE-1.1` Create backend folder structure (`app/core`, `app/db`, `app/models`, `app/schemas`, `app/api/routes`, `app/services`, `app/auth`, `app/email`, `app/seeds`).
  - **Done when:** All directories exist under `backend/app/` with `__init__.py` files so they are importable as Python packages.
- [x] `BE-1.2` Add backend `Dockerfile` (Python 3.14 slim, install deps, uvicorn reload command).
  - **Done when:** `backend/Dockerfile` uses `python:3.14-slim`, runs `uv sync --frozen`, and starts uvicorn with `--reload`. `docker compose build backend` completes without errors.
- [x] `BE-1.3` Add `pyproject.toml` and `uv.lock` with uv-managed dependencies for FastAPI, SQLAlchemy, psycopg, cryptography, pytest, pytest-asyncio, Ruff, ty.
  - **Done when:** `uv sync --frozen` installs all listed packages without errors, and `uv run ruff check .` and `uv run ty check` can be invoked.
- [x] `BE-1.4` Add backend `.env.example` with DB, session, encryption, SMTP, CORS, environment settings.
  - **Done when:** `backend/.env.example` contains all keys from spec section 4: `DATABASE_URL`, `SESSION_COOKIE_NAME`, `SESSION_SECRET`, `SESSION_EXPIRE_SECONDS`, `BEER_ENCRYPTION_KEY`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, `SMTP_USE_TLS`, `LOGIN_CODE_EXPIRE_MINUTES`, `CORS_ORIGINS`, `ENVIRONMENT`.

### 2. Configuration and Database Foundation
- [x] `BE-2.1` Implement `app/core/config.py` with Pydantic Settings and env parsing.
  - **Done when:** `Settings` reads all `.env.example` keys via `pydantic-settings`. Importing `from app.core.config import settings` works in any module. A missing required key raises a clear `ValidationError` at startup.
- [x] `BE-2.2` Implement `app/db/session.py` with engine setup and `get_db` dependency.
  - **Done when:** `engine` is created from `settings.DATABASE_URL`. `get_db` is an async-compatible FastAPI dependency that yields a `Session` and closes it on completion. The module imports without error.
- [x] `BE-2.4` Add `GET /health` endpoint.
  - **Done when:** `GET /health` returns `200 {"status": "ok"}` with no authentication required, confirmed with `curl http://localhost/api/health`.

### 3. Data Models (SQLAlchemy)
- [x] `BE-3.1` Implement `User` model in `app/models/user.py`.
  - **Done when:** Model has all columns from spec 5.1: `id` (int PK), `email` (unique, indexed, not null), `display_name` (not null), `role` (enum `"user"/"admin"`, default `"user"`), `is_active` (bool, default `True`), `created_at`, `updated_at`. `Base.metadata.create_all` creates the `users` table with the correct schema.
- [x] `BE-3.2` Implement `LoginCode` model in `app/models/login_code.py`.
  - **Done when:** Model has all columns from spec 5.2: `id` (int PK), `user_id` (FK → User), `code_hash` (not null), `expires_at` (not null), `used_at` (nullable), `created_at`, `updated_at`. The FK to `users` is enforced by the database.
- [x] `BE-3.3` Implement `Session` model in `app/models/session.py`.
  - **Done when:** Model has all columns from spec 5.3: `id` (UUID PK), `user_id` (FK → User), `session_token_hash` (not null, indexed), `expires_at` (not null), `created_at`, `last_seen_at`, `revoked_at` (nullable). The FK to `users` is enforced by the database.
- [x] `BE-3.4` Implement `BeerEntry` model in `app/models/beer_entry.py`.
  - **Done when:** Model has all columns: `id` (int PK), `user_id` (FK → User), `beer_name_encrypted` (not null), `brewery_encrypted` (not null), `untappd_url_encrypted` (nullable), `comment_encrypted` (nullable), `bought_from` (not null), `bought_at` (not null datetime), `created_at`, `updated_at`.
- [x] `BE-3.5` Implement `CalendarEntry` model in `app/models/calendar_entry.py`.
  - **Done when:** Model has all columns from spec 5.5: `id` (UUID PK), `year` (not null, indexed, check `year ≥ 2020`), `day` (not null, check `1 ≤ day ≤ 24`), `unlock_date` (not null), `published_at` (nullable), `title` (not null), `content` (not null), `image_url` (nullable), `beer_entry_id` (nullable FK → BeerEntry), `created_at`, `updated_at`.
- [x] `BE-3.6` Add constraints: `UNIQUE(year, day)` and `UNIQUE(beer_entry_id)` on `CalendarEntry`.
  - **Done when:** Attempting to insert two `CalendarEntry` rows with the same `(year, day)` raises a unique constraint error. Attempting to assign the same `beer_entry_id` to two rows also raises a unique constraint error.
- [x] `BE-3.7` Validate model relationships and FK directions against the spec diagram.
  - **Done when:** All six FKs from spec section 5 exist: `BeerEntry.user_id → User.id`, `LoginCode.user_id → User.id`, `Session.user_id → User.id`, `CalendarEntry.beer_entry_id → BeerEntry.id`, `UserRating.user_id → User.id`, `UserRating.beer_entry_id → BeerEntry.id`. SQLAlchemy `relationship()` attributes are navigable in both directions where relevant. A quick `pytest` or `python -c` smoke test confirms the ORM joins work.
- [x] `BE-3.8` Implement `UserRating` model in `app/models/user_rating.py`.
  - **Done when:** Model has all columns from spec 5.6: `id` (int PK), `user_id` (FK → User), `beer_entry_id` (FK → BeerEntry), `rating` (float, not null, DB check `1.0 ≤ rating ≤ 5.0`), `comment` (nullable), `drank_at` (nullable datetime), `created_at`, `updated_at`. A `UNIQUE(user_id, beer_entry_id)` constraint prevents a user from rating the same beer twice.

### 4. Seed and Init Logic
- [x ] `BE-4.1` Implement startup initialization flow in `app/main.py` (create schema +seed call).
    - **Done when:** On `docker compose up`, the backend logs confirm tables were created (or already exist) and seed data was checked. `GET /health` responds `200 {"status": "ok"}` after startup without manual intervention.
- [x] `BE-4.2` Implement `app/db/init_db.py` to run `Base.metadata.create_all(engine)`.
  - **Done when:** Calling `init_db()` creates all tables in a fresh database without error. A second call on an existing database is a no-op (no error, no data loss).
- [x] `BE-4.3` Implement `app/seeds/seed.py` with idempotent seed strategy.
  - **Done when:** `run_seed(db)` checks whether the `users` table is empty before inserting. Running it twice against the same database produces identical data with no duplicate rows and no exception.
- [x] `BE-4.4` Seed admin + participant users.
  - **Done when:** After seeding, the database contains exactly these 5 users: `admin@brobier.local` (role=admin), `alice@brobier.local`, `bob@brobier.local`, `carol@brobier.local` (all role=user, is_active=true), and `dave@brobier.local` (role=user, is_active=false).
- [] `BE-4.5` Seed sample beer entries for active users.
  - **Done when:** Alice, Bob, and Carol each have at least 3 beer entries in the database after seeding. All `beer_name_encrypted` and `brewery_encrypted` columns contain valid Fernet ciphertext (not plaintext).
- [ ] `BE-4.6` Seed 24 calendar rows for target year (preserve prior-year history, only fill missing rows).
  - **Done when:** After seeding against a fresh database, there are exactly 24 `CalendarEntry` rows for the current UTC year (days 1–24), each with `unlock_date` set to December `day` of that year at 08:00 UTC. Running the seed again does not add duplicate rows. If rows for a prior year already exist they are unchanged.
- [ ] `BE-4.7` Assign sample beers to early calendar days for demo.
  - **Done when:** After seeding, calendar entries for days 1–5 of the seeded year each have a non-null `beer_entry_id` pointing to a valid beer entry. No single beer entry is assigned to more than one day.

### 5. Security and Encryption
- [ ] `BE-5.1` Implement `app/core/security.py` — `encrypt_field` and `decrypt_field` via Fernet.
  - **Done when:** `encrypt_field("hello")` returns a non-empty string that is not `"hello"`. `decrypt_field(encrypt_field("hello"))` returns `"hello"`. Both return `None` when given `None`. Both raise a clear application error when `BEER_ENCRYPTION_KEY` is missing or the ciphertext is tampered with.
- [ ] `BE-5.2` Implement login code + session token hashing helpers in `app/core/security.py`.
  - **Done when:** `hash_token(raw)` returns the SHA-256 hex digest of `raw`. `generate_login_code()` returns a 6-character string of decimal digits (`"000000"`–`"999999"`). Both functions are covered by unit tests in `BE-8.2`.
- [ ] `BE-5.3` Ensure encrypted beer fields are never exposed raw in responses.
  - **Done when:** `GET /beers/me`, `POST /beers`, `PUT /beers/{id}`, and `GET /admin/beers` all return `beer_name`, `brewery`, `untappd_url`, `comment` as plaintext (decrypted). No response body anywhere in the API contains a key ending in `_encrypted`. Verified by inspecting the Pydantic response schemas and confirmed in the API tests for `BE-8.3`.
- [ ] `BE-5.4` Add runtime errors for missing/invalid encryption key and decryption failures.
  - **Done when:** Starting the app without `BEER_ENCRYPTION_KEY` set raises a startup error with a clear message. Passing corrupted ciphertext to `decrypt_field` raises an `HTTPException(500)` (or a custom app error) rather than an unhandled exception. Both scenarios are covered by unit tests.

### 6. Authentication and Session Management
- [ ] `BE-6.1` Implement `request_code` flow in `app/services/auth_service.py` and route `POST /auth/request-code`.
  - **Done when:** Posting a registered active email generates a 6-digit `LoginCode` row (with hashed code, expiry = now + `LOGIN_CODE_EXPIRE_MINUTES`) and triggers an email send. Posting any other email returns the same `200 {"message": "If that email is registered, a code has been sent."}` response — the response body is identical regardless of whether the email exists.
- [ ] `BE-6.2` Implement SMTP mail sender in `app/email/sender.py`.
  - **Done when:** `send_login_code_email(to, code)` sends an email via the configured SMTP server. In the Docker dev environment, the email appears in Mailpit at `http://localhost:8025` after triggering `POST /auth/request-code` with a valid email.
- [ ] `BE-6.3` Implement `verify_code` flow — route `POST /auth/verify-code`.
  - **Done when:** A valid (unexpired, unused) code + matching email returns `200 {"user": {id, display_name, role}}` and sets an `HttpOnly` session cookie. The `LoginCode.used_at` is set to now. A second attempt with the same code returns `401`. An expired code returns `401`. The response body for invalid codes is always `{"detail": "Invalid or expired code."}`.
- [ ] `BE-6.4` Implement `logout` flow — route `POST /auth/logout`.
  - **Done when:** Calling `POST /auth/logout` with a valid session cookie sets `Session.revoked_at = now` in the database and clears the session cookie. A subsequent `GET /auth/me` with the cleared cookie returns `401`.
- [ ] `BE-6.5` Implement `get_current_user` FastAPI dependency in `app/auth/dependencies.py`.
  - **Done when:** The dependency reads the raw token from the session cookie, hashes it, looks up the matching non-revoked, non-expired `Session` row, updates `last_seen_at`, and returns the linked `User`. Returns `401` if the cookie is absent, the session is revoked, or the session is expired.
- [ ] `BE-6.6` Implement `require_admin` FastAPI dependency in `app/auth/dependencies.py`.
  - **Done when:** The dependency wraps `get_current_user` and additionally checks `user.role == "admin"`. Returns `403` if the user is authenticated but not an admin. Any endpoint using `require_admin` is inaccessible to a regular user session (confirmed in `BE-8.4`).
- [ ] `BE-6.7` Enforce cookie flags and expiry by environment.
  - **Done when:** In development (`ENVIRONMENT=development`), the session cookie is set with `HttpOnly=True`, `SameSite=Lax`, `Secure=False`, and `Max-Age=SESSION_EXPIRE_SECONDS`. In production (`ENVIRONMENT=production`), the same cookie is set with `Secure=True`. Verified by inspecting the `Set-Cookie` header in the response from `POST /auth/verify-code`.

### 7. Schemas and API Routes
- [ ] `BE-7.1` Implement auth schemas and routes (`/auth/request-code`, `/auth/verify-code`, `/auth/logout`, `/auth/me`).
  - **Done when:** All four auth endpoints are registered on the FastAPI app and respond with the exact shapes described in spec section 8.1. Pydantic schemas live in `app/schemas/auth.py`. Route handlers are thin (input validation + service call + return).
- [ ] `BE-7.2` Implement beer schemas and routes (`GET /beers/me`, `POST /beers`, `PUT /beers/{beer_id}`, `DELETE /beers/{beer_id}`).
  - **Done when:** All four endpoints are registered and respond with the shapes from spec section 8.2. `POST /beers` returns `201`. `DELETE /beers/{id}` returns `204`. Schemas live in `app/schemas/beer.py`. Business logic (encrypt, decrypt, ownership check) is in `app/services/beer_service.py`, not the route handler.
- [ ] `BE-7.2a` Implement user rating routes (`POST /beers/{beer_id}/ratings`, `PUT /beers/{beer_id}/ratings/me`, `DELETE /beers/{beer_id}/ratings/me`).
  - **Done when:** All three endpoints are registered and respond with the shapes from spec section 8.2. `POST` returns `201 UserRatingOut`; returns `409` if the user has already rated the beer. `PUT` returns `200 UserRatingOut`; returns `404` if no rating exists yet. `DELETE` returns `204`; returns `404` if no rating exists. Schemas live in `app/schemas/user_rating.py`. Business logic lives in `app/services/rating_service.py`.
- [ ] `BE-7.3` Implement ownership and calendar-assignment guardrails for beer mutations.
  - **Done when:** `PUT /beers/{id}` returns `403` when the requesting user does not own the beer, and `409` when the beer is currently assigned to a calendar entry. `DELETE /beers/{id}` returns the same `403`/`409` codes under the same conditions. These checks live in the service layer and are covered by tests in `BE-8.3`.
- [ ] `BE-7.4` Implement leaderboard route (`GET /leaderboard`).
  - **Done when:** `GET /leaderboard` returns a list ordered by `beer_count` descending, containing only active users. Each item is `{"display_name": str, "beer_count": int}`. Users with zero beers are included. Logic lives in `app/services/leaderboard_service.py`.
- [ ] `BE-7.5` Implement user calendar routes with year-aware behavior.
  - **Done when:** All three endpoints below exist and behave correctly:
    - `BE-7.5a` `GET /calendar?year=` — omitting `year` defaults to current UTC year. Returns a list of 24 `CalendarEntryOut` objects.
    - `BE-7.5b` `GET /calendar/{day}?year=` — omitting `year` defaults to current UTC year. Returns a single `CalendarEntryOut` or `404` if the day/year combination does not exist.
    - `BE-7.5c` `GET /calendar/years` — returns `[{"year": int}]` sorted descending, one entry per distinct year present in the `calendar_entries` table.
- [ ] `BE-7.6` Implement unlock-aware calendar response shaping (locked vs unlocked).
  - **Done when:** For a calendar entry where `unlock_date > now`: the response matches the locked schema (`{id, year, day, unlock_date, title, is_locked: true}`) with no `content`, `image_url`, or `beer` field present. For an entry where `unlock_date ≤ now`: the response matches the unlocked schema and includes decrypted `beer` fields if a beer is linked. This logic lives in `app/services/calendar_service.py` and is covered by tests in `BE-8.5`.
- [ ] `BE-7.7` Implement admin routes.
  - **Done when:** All endpoints below exist, return the specified schemas, and are protected by `require_admin`:
    - `BE-7.7a` `GET /admin/users`, `POST /admin/users` (201/409), `PUT /admin/users/{id}`, `POST /admin/users/{id}/activate`, `POST /admin/users/{id}/deactivate`.
    - `BE-7.7b` `GET /admin/beers` — returns all beer entries decrypted with owner `display_name`.
    - `BE-7.7c` `GET /admin/calendar?year=`, `POST /admin/calendar` (201/409), `PUT /admin/calendar/{entry_id}`, `DELETE /admin/calendar/{entry_id}` (204).
    - `BE-7.7d` `PUT /admin/calendar/{entry_id}/beer` (assigns, 409 if beer already assigned), `DELETE /admin/calendar/{entry_id}/beer` (unassigns).

### 8. Testing, Linting, and Verification (Backend)
- [ ] `BE-8.1` Configure pytest + pytest-asyncio.
  - **Done when:** `uv run pytest` in the `backend/` directory discovers and runs at least a placeholder test file without configuration errors. `asyncio_mode = "auto"` is set in `pyproject.toml` so async test functions run without manual event-loop setup.
- [ ] `BE-8.2` Add unit tests for security helpers (hashing, encryption/decryption).
  - **Done when:** Tests cover: `encrypt_field` + `decrypt_field` round-trip; `encrypt_field(None)` returns `None`; `decrypt_field` raises on tampered ciphertext; `hash_token` is deterministic for the same input; `generate_login_code` returns a 6-digit decimal string. All tests pass with `uv run pytest tests/unit/test_security.py`.
- [ ] `BE-8.3` Add service tests for auth, beer ownership rules, and calendar unlock logic.
  - **Done when:** Tests cover: requesting a code for an unknown email returns the same message as a known email; a used code cannot be reused; a non-owner cannot edit/delete a beer; a beer assigned to a calendar entry cannot be edited or deleted. All tests pass.
- [ ] `BE-8.4` Add API tests for auth/session lifecycle and admin authorization.
  - **Done when:** Tests cover: full login → verify → `GET /auth/me` → logout → `GET /auth/me` returns 401; a regular-user session receives `403` on any `/admin/*` route; an unauthenticated request to a protected route receives `401`. All tests pass.
- [ ] `BE-8.5` Add tests for year/history behavior (`year` defaults, listing years, preserving old rows).
  - **Done when:** Tests cover: `GET /calendar` with no `year` param returns data for the current UTC year; `GET /calendar/years` lists all seeded years; a locked entry (future `unlock_date`) returns only the locked schema fields; an unlocked entry returns full content. Running the seed function twice does not duplicate rows. All tests pass.
- [ ] `BE-8.6` Run Ruff lint + format checks.
  - **Done when:** `uv run ruff check backend/` and `uv run ruff format --check backend/` both exit with code 0 and no reported violations.
- [ ] `BE-8.7` Run ty type checks.
  - **Done when:** `uv run ty check backend/` exits with code 0 and no type errors reported.

## Frontend Tasks

### 1. Project Setup
- [ ] `FE-1.1` Scaffold React 19 + TypeScript + Vite 6 frontend.
  - **Done when:** `frontend/` directory contains a Vite project (`vite.config.ts`, `tsconfig.json`, `src/main.tsx`). `npm run dev` inside the container starts the Vite dev server and the root page loads in a browser at `http://localhost`.
- [ ] `FE-1.2` Configure Tailwind CSS v4.
  - **Done when:** A Tailwind utility class (e.g. `bg-red-500`) applied to any element takes visible effect in the browser. `npm run build` completes without errors and the output CSS contains only used classes (purged).
- [ ] `FE-1.3` Configure React Router v7.
  - **Done when:** `BrowserRouter` (or `createBrowserRouter`) is set up in `src/main.tsx`. Navigating to an unregistered path shows a fallback (404 page or redirect) rather than a blank screen. The router config lives in a single `src/router.tsx` (or equivalent).
- [ ] `FE-1.4` Add frontend `Dockerfile` and `.env.example` (`VITE_API_BASE_URL=http://localhost/api`).
  - **Done when:** `frontend/Dockerfile` uses `node:24-alpine`, runs `npm install`, and starts `npm run dev -- --host`. `frontend/.env.example` contains `VITE_API_BASE_URL=http://localhost/api`. `docker compose build frontend` completes without errors.

### 2. API Client and Types
- [ ] `FE-2.1` Implement `src/api/client.ts` base fetch wrapper with `credentials: "include"`.
  - **Done when:** `client.ts` exports a typed `apiFetch(path, options?)` function that prefixes all requests with `VITE_API_BASE_URL`, sets `credentials: "include"`, and returns the parsed JSON body. Non-2xx responses throw an `ApiError` (see `FE-2.2`). No raw `fetch` calls exist outside this module.
- [ ] `FE-2.2` Implement typed `ApiError` handling for non-2xx responses.
  - **Done when:** An `ApiError` class exists in `src/api/errors.ts` (or `client.ts`) with at least `status: number` and `message: string` properties. Callers can use `instanceof ApiError` to detect API failures. A 401 response from the server produces an `ApiError` with `status === 401`.
- [ ] `FE-2.3` Implement API modules in `src/api/`.
  - **Done when:** Each module exports typed async functions wrapping `apiFetch`:
    - `FE-2.3a` `auth.ts` — `requestCode(email)`, `verifyCode(email, code)`, `logout()`, `getMe()`.
    - `FE-2.3b` `beers.ts` — `getMyBeers()`, `createBeer(data)`, `updateBeer(id, data)`, `deleteBeer(id)`.
    - `FE-2.3c` `leaderboard.ts` — `getLeaderboard()`.
    - `FE-2.3d` `calendar.ts` — `getCalendar(year?)`, `getCalendarDay(year, day)`, `getCalendarYears()`.
    - `FE-2.3e` `admin.ts` — all admin user, beer, and calendar CRUD functions.
- [ ] `FE-2.4` Implement response/request TypeScript types in `src/types/`.
  - **Done when:** Types cover all API response shapes from spec section 8.4: `User`, `BeerEntryOut`, `AdminBeerEntryOut`, `CalendarEntryOut` (locked and unlocked variants using a discriminated union on `is_locked`), `AdminCalendarEntryOut`, `LeaderboardEntry`. TypeScript compilation (`npm run build` or `tsc --noEmit`) passes with no type errors.

### 3. Authentication State and Route Protection
- [ ] `FE-3.1` Implement `AuthContext` with startup session hydration (`GET /auth/me`).
  - **Done when:** On app load, `AuthContext` calls `getMe()`. If successful, `user` is set in context. If the call returns 401, `user` is `null`. The loading state is exposed so pages can show a spinner before auth is resolved. Context is provided at the root of the app.
- [ ] `FE-3.2` Implement `useAuth` hook.
  - **Done when:** `useAuth()` returns `{ user, isLoading, login, logout }`. `user` is the current `User` object or `null`. Calling `logout()` calls `auth.logout()`, clears the context user, and navigates to `/login`.
- [ ] `FE-3.3` Implement `ProtectedRoute`.
  - **Done when:** A component that wraps child routes. If `isLoading` is true, renders a loading state. If `user` is `null` after loading, redirects to `/login` with the intended path preserved in location state. Authenticated users render the children normally.
- [ ] `FE-3.4` Implement `AdminRoute`.
  - **Done when:** Wraps `ProtectedRoute`. If the authenticated user's `role !== "admin"`, redirects to `/` instead of rendering children. Regular-user sessions navigating to `/admin/*` are redirected to `/`.
- [ ] `FE-3.5` Ensure logout clears client auth state and redirects appropriately.
  - **Done when:** Clicking logout calls `useAuth().logout()`, the session cookie is cleared by the server, `user` becomes `null` in context, and the browser navigates to `/login`. A subsequent `GET /auth/me` (e.g. on page refresh) returns 401 and the user stays on `/login`.

### 4. Layout and Navigation
- [ ] `FE-4.1` Build `AppLayout` with authenticated navigation.
  - **Done when:** `AppLayout` renders a `Navbar` with links to Dashboard, Leaderboard, and Calendar. The current user's `display_name` is visible. A logout button is present. The layout wraps all authenticated pages as confirmed by navigating between routes.
- [ ] `FE-4.2` Build `AdminLayout` with admin navigation/sidebar.
  - **Done when:** `AdminLayout` renders a sidebar or header with links to Admin Dashboard, Users, Calendar, and Beers. It is only reachable by users with `role === "admin"` (enforced by `AdminRoute`).
- [ ] `FE-4.3` Add clear navigation for calendar year selection and history browsing.
  - **Done when:** The `CalendarPage` displays a year selector populated from `getCalendarYears()`. Selecting a different year navigates to `/calendar/:year`. The current year is pre-selected on initial load.

### 5. Public and User Pages
- [ ] `FE-5.1` Build `CountdownPage` at `/`.
  - **Done when:** The page displays a live countdown to December 1 of the current year (or December 1 of the next year if past December 24). The countdown updates every second. The page is accessible without authentication.
- [ ] `FE-5.2` Build `LoginPage` at `/login` with two-step request-code/verify-code flow.
  - **Done when:** Step 1 shows an email input and submit button; on success the page transitions to Step 2 showing a 6-digit code input. Submitting a valid code calls `verifyCode`, sets the auth context user, and redirects to `/dashboard` (or the originally intended path). Invalid codes display an inline error. Already-authenticated users visiting `/login` are redirected away.
- [ ] `FE-5.3` Build `DashboardPage` at `/dashboard` for beer CRUD.
  - **Done when:** The page lists the current user's beer entries via `getMyBeers()`. A form (using `BeerForm`) allows creating a new entry. Each listed entry shows Edit and Delete buttons. Edits use `updateBeer()` and deletes use `deleteBeer()`. Beers assigned to a calendar entry have edit/delete disabled or show a tooltip explaining why.
- [ ] `FE-5.4` Build `LeaderboardPage` at `/leaderboard`.
  - **Done when:** The page calls `getLeaderboard()` and renders entries in rank order using `LeaderboardTable`. The page is only reachable by authenticated users (wrapped in `ProtectedRoute`).
- [ ] `FE-5.5` Build year-aware `CalendarPage`.
  - **Done when:**
    - `FE-5.5a` Navigating to `/calendar` redirects to `/calendar/:currentYear` (current UTC year).
    - `FE-5.5b` `/calendar/:year` renders 24 `CalendarDoor` components in a grid, one per day.
    - `FE-5.5c` Locked doors (where `is_locked === true`) show only the day number and lock icon. Unlocked doors show the title and are clickable, navigating to `/calendar/:year/:day`.
- [ ] `FE-5.6` Build `CalendarDayPage` at `/calendar/:year/:day`.
  - **Done when:** The page calls `getCalendarDay(year, day)` and renders the full entry content and decrypted beer details if unlocked. A locked entry (returned as locked schema) displays a "not yet unlocked" message. A 404 from the API shows a "day not found" message. A back link returns to `/calendar/:year`.

### 6. Admin Pages
- [ ] `FE-6.1` Build `AdminDashboardPage` at `/admin`.
  - **Done when:** The page renders a summary with links to Users, Calendar, and Beers admin sub-pages. Only reachable via `AdminRoute`.
- [ ] `FE-6.2` Build `AdminUsersPage` at `/admin/users` (create, edit, activate, deactivate).
  - **Done when:** The page lists all users from `GET /admin/users`. A form allows creating a new user (email, display_name, role). Each row has Edit, Activate, and Deactivate buttons that call the respective admin API functions. Changes are reflected immediately after the API call succeeds (re-fetch or optimistic update).
- [ ] `FE-6.3` Build `AdminCalendarPage` at `/admin/calendar`.
  - **Done when:**
    - `FE-6.3a` A year selector populated from `getCalendarYears()` controls which year's entries are shown.
    - `FE-6.3b` Each of the 24 days shows its title and unlock date. Create, Edit, and Delete actions call the respective admin calendar API functions.
    - `FE-6.3c` Each day shows its assigned beer (if any). An "Assign Beer" control calls `PUT /admin/calendar/{id}/beer`; an "Unassign" button calls `DELETE /admin/calendar/{id}/beer`.
- [ ] `FE-6.4` Build `AdminBeersPage` at `/admin/beers`.
  - **Done when:** The page calls `GET /admin/beers` and renders a table of all beer entries with columns for owner display name, beer name, brewery, rating. No edit/delete actions are required on this page (read-only overview).

### 7. Component Work
- [ ] `FE-7.1` Implement reusable components: `Navbar`, `BeerCard`, `BeerForm`, `LeaderboardTable`, `CalendarDoor`, `CountdownTimer`.
  - **Done when:** Each component is defined in its own file under `src/components/`. Each is used by at least one page. Props are typed with TypeScript interfaces. No component reaches into the API directly — data is passed as props.
- [ ] `FE-7.2` Ensure form validation and optimistic/refresh UX for mutations.
  - **Done when:** `BeerForm` prevents submission when required fields (`beer_name`, `brewery`) are empty and shows inline validation messages. After a successful create/update/delete, the beer list re-fetches (or updates optimistically) without a full page reload. API errors from the server are displayed as user-visible messages.
- [ ] `FE-7.3` Ensure mobile + desktop responsive layout behavior.
  - **Done when:** At a 375 px viewport width, the `Navbar` collapses or is replaced by a mobile menu, the calendar grid uses a single-column or two-column layout (not overflow), and the leaderboard table is readable without horizontal scroll. Verified by browser DevTools device emulation.

### 8. Testing and Quality (Frontend)
- [ ] `FE-8.1` Configure Vitest + React Testing Library.
  - **Done when:** `npm test` runs Vitest and discovers test files. A placeholder test (e.g. `expect(true).toBe(true)`) passes. `@testing-library/react` and `@testing-library/user-event` are installed and importable.
- [ ] `FE-8.2` Add unit tests for API client error handling and auth context behavior.
  - **Done when:** Tests cover: a non-2xx fetch response causes `apiFetch` to throw an `ApiError` with the correct `status`; `AuthContext` sets `user` to `null` when `getMe()` returns 401; `AuthContext` sets `user` to the returned object when `getMe()` succeeds. All tests pass with `npm test`.
- [ ] `FE-8.3` Add component tests for protected routes and critical forms.
  - **Done when:** Tests cover: `ProtectedRoute` redirects to `/login` when `user` is `null`; `AdminRoute` redirects to `/` when the user's role is `"user"`; `BeerForm` shows a validation error when submitted with an empty `beer_name` field. All tests pass.
- [ ] `FE-8.4` Add page tests for login flow and year-aware calendar rendering.
  - **Done when:** Tests cover: submitting a valid email on `LoginPage` transitions to the code input step; submitting a valid code calls `verifyCode` and navigates to `/dashboard`; `CalendarPage` renders 24 doors for the requested year; locked doors do not show content fields. All tests pass.
- [ ] `FE-8.5` Add admin page tests for role-gated behavior.
  - **Done when:** Tests cover: a user with `role === "user"` is redirected away from `/admin/users`; a user with `role === "admin"` sees the user list rendered by `AdminUsersPage`. All tests pass.
- [ ] `FE-8.6` Run lint/type/build checks before merge.
  - **Done when:** `npm run lint` exits with code 0 (no ESLint errors), `npx tsc --noEmit` exits with code 0 (no type errors), and `npm run build` produces a `dist/` directory without errors. All three checks run in CI (or are verified manually before merge).

## Suggested Execution Milestones
- [ ] `MS-A` Milestone A: Infra + backend models + seed + health endpoint.
  - **Done when:** `docker compose up --build` starts cleanly, `GET /api/health` returns `{"status": "ok"}`, all five tables exist in the database, and seed data is present (5 users, beers for Alice/Bob/Carol, 24 calendar rows for current year).
- [ ] `MS-B` Milestone B: Auth/session complete end-to-end.
  - **Done when:** A seeded user can request a login code (visible in Mailpit), submit it to `POST /auth/verify-code`, receive a session cookie, call `GET /auth/me` successfully, and log out. A second `GET /auth/me` after logout returns 401.
- [ ] `MS-C` Milestone C: Beer CRUD + leaderboard.
  - **Done when:** An authenticated user can create, update, and delete their own beer entries via the API. `GET /leaderboard` returns active users ranked by beer count. Ownership and calendar-assignment guardrails return the correct 403/409 status codes.
- [ ] `MS-D` Milestone D: Year-aware calendar + history endpoints.
  - **Done when:** `GET /calendar`, `GET /calendar/{day}`, and `GET /calendar/years` all respond correctly. Locked entries omit content and beer fields. Unlocked entries include decrypted beer details. Seeded prior-year data (if any) is preserved and accessible via `?year=`.
- [ ] `MS-E` Milestone E: Admin features complete.
  - **Done when:** All `/admin/*` endpoints are implemented and return correct responses. A non-admin session receives 403 on every admin route. Admin can create users, assign beers to calendar days, and view all beers.
- [ ] `MS-F` Milestone F: Frontend pages complete.
  - **Done when:** All pages listed in the frontend route table (spec section 11) render without runtime errors. The full user journey works in the browser: visit `/` → log in → view dashboard → browse calendar → view a day → log out. Admin journey: log in as admin → manage users → assign a beer to a calendar day.
- [ ] `MS-G` Milestone G: Automated tests + hardening pass.
  - **Done when:** `uv run pytest` passes all backend tests with no failures. `npm test` passes all frontend tests with no failures. `uv run ruff check backend/`, `uv run ty check backend/`, `npm run lint`, and `npm run build` all exit with code 0.
