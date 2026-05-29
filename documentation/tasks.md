# Brobier Implementation Tasks

This checklist is derived from documentation/spec.md and is organized by backend and frontend workstreams.

Task ID format:
- Backend: `BE-<section>.<item>` (example: `BE-3.4`)
- Frontend: `FE-<section>.<item>` (example: `FE-5.2`)
- Milestones: `MS-<letter>` (example: `MS-D`)

## Backend Tasks

### 1. Project and Runtime Setup
- [x] `BE-1.1` Create backend folder structure (`app/core`, `app/db`, `app/models`, `app/schemas`, `app/api/routes`, `app/services`, `app/auth`, `app/email`, `app/seeds`).
- [x] `BE-1.2` Add backend `Dockerfile` (Python 3.14 slim, install deps, uvicorn reload command).
- [x] `BE-1.3` Add `pyproject.toml` and `uv.lock` with uv-managed dependencies for FastAPI, SQLAlchemy, psycopg, cryptography, pytest, pytest-asyncio, Ruff, ty.
- [x] `BE-1.4` Add backend `.env.example` with DB, session, encryption, SMTP, CORS, environment settings.

### 2. Configuration and Database Foundation
- [x] `BE-2.1` Implement `app/core/config.py` with Pydantic Settings and env parsing.
- [x] `BE-2.2` Implement `app/db/session.py` with engine setup and `get_db` dependency.
- [ ] `BE-2.3` Implement startup initialization flow in `app/main.py` (create schema + seed call).
- [x] `BE-2.4` Add `GET /health` endpoint.

### 3. Data Models (SQLAlchemy)
- [ ] `BE-3.1` Implement `User` model with role enum, active flag, timestamps, unique email index.
- [ ] `BE-3.2` Implement `LoginCode` model with expiry + single-use fields.
- [ ] `BE-3.3` Implement `Session` model with hashed token, expiry, revocation, last seen.
- [ ] `BE-3.4` Implement `BeerEntry` model with encrypted field columns and rating validation.
- [ ] `BE-3.5` Implement `CalendarEntry` model with `year`, `day`, `unlock_date`, `published_at`, optional beer link, timestamps.
- [ ] `BE-3.6` Add constraints: `UNIQUE(year, day)` and `UNIQUE(beer_entry_id)`.
- [ ] `BE-3.7` Validate model relationships and FK directions against the spec diagram.

### 4. Seed and Init Logic
- [ ] `BE-4.1` Implement `app/db/init_db.py` to run `Base.metadata.create_all(engine)`.
- [ ] `BE-4.2` Implement `app/seeds/seed.py` with idempotent seed strategy.
- [ ] `BE-4.3` Seed admin + participant users.
- [ ] `BE-4.4` Seed sample beer entries for active users.
- [ ] `BE-4.5` Seed 24 calendar rows for target year (preserve prior-year history, only fill missing rows).
- [ ] `BE-4.6` Assign sample beers to early calendar days for demo.

### 5. Security and Encryption
- [ ] `BE-5.1` Implement `app/core/security.py` for field encryption/decryption via Fernet.
- [ ] `BE-5.2` Implement login code + session token hashing helpers.
- [ ] `BE-5.3` Ensure encrypted beer fields are never exposed raw in responses.
- [ ] `BE-5.4` Add runtime errors for missing/invalid encryption key and decryption failures.

### 6. Authentication and Session Management
- [ ] `BE-6.1` Implement `request_code` flow with generic anti-enumeration response.
- [ ] `BE-6.2` Implement SMTP mail sender in `app/email/sender.py` (Mailpit in development).
- [ ] `BE-6.3` Implement `verify_code` flow (validate active user, expiry, single-use, create session cookie).
- [ ] `BE-6.4` Implement `logout` flow (revoke DB session + clear cookie).
- [ ] `BE-6.5` Implement `get_current_user` dependency (cookie -> hash -> DB session -> user).
- [ ] `BE-6.6` Implement `require_admin` dependency.
- [ ] `BE-6.7` Enforce cookie flags and expiry by environment.

### 7. Schemas and API Routes
- [ ] `BE-7.1` Implement auth schemas and routes (`/auth/request-code`, `/auth/verify-code`, `/auth/logout`, `/auth/me`).
- [ ] `BE-7.2` Implement beer schemas and routes (`GET /beers/me`, `POST /beers`, `PUT /beers/{beer_id}`, `DELETE /beers/{beer_id}`).
- [ ] `BE-7.3` Implement ownership and calendar-assignment guardrails for beer mutations.
- [ ] `BE-7.4` Implement leaderboard route (`GET /leaderboard`).
- [ ] `BE-7.5` Implement user calendar routes with year-aware behavior.
- [ ] `BE-7.5a` `GET /calendar?year=`
- [ ] `BE-7.5b` `GET /calendar/{day}?year=`
- [ ] `BE-7.5c` `GET /calendar/years`
- [ ] `BE-7.6` Implement unlock-aware calendar response shaping (locked vs unlocked).
- [ ] `BE-7.7` Implement admin routes.
- [ ] `BE-7.7a` Users CRUD + activate/deactivate
- [ ] `BE-7.7b` `GET /admin/beers`
- [ ] `BE-7.7c` Calendar CRUD (year aware)
- [ ] `BE-7.7d` Assign/unassign beer to calendar entry

### 8. Testing, Linting, and Verification (Backend)
- [ ] `BE-8.1` Configure pytest + pytest-asyncio.
- [ ] `BE-8.2` Add unit tests for security helpers (hashing, encryption/decryption).
- [ ] `BE-8.3` Add service tests for auth, beer ownership rules, and calendar unlock logic.
- [ ] `BE-8.4` Add API tests for auth/session lifecycle and admin authorization.
- [ ] `BE-8.5` Add tests for year/history behavior (`year` defaults, listing years, preserving old rows).
- [ ] `BE-8.6` Run Ruff lint + format checks.
- [ ] `BE-8.7` Run ty type checks.

## Frontend Tasks

### 1. Project Setup
- [ ] `FE-1.1` Scaffold React 19 + TypeScript + Vite 6 frontend.
- [ ] `FE-1.2` Configure Tailwind CSS v4.
- [ ] `FE-1.3` Configure React Router v7.
- [ ] `FE-1.4` Add frontend `Dockerfile` and `.env.example` (`VITE_API_BASE_URL=http://localhost/api`).

### 2. API Client and Types
- [ ] `FE-2.1` Implement `src/api/client.ts` base fetch wrapper with `credentials: "include"`.
- [ ] `FE-2.2` Implement typed `ApiError` handling for non-2xx responses.
- [ ] `FE-2.3` Implement API modules.
- [ ] `FE-2.3a` `auth.ts`
- [ ] `FE-2.3b` `beers.ts`
- [ ] `FE-2.3c` `leaderboard.ts`
- [ ] `FE-2.3d` `calendar.ts` (`getCalendar`, `getCalendarDay`, `getCalendarYears`)
- [ ] `FE-2.3e` `admin.ts`
- [ ] `FE-2.4` Implement response/request TypeScript types in `src/types/*` including year-aware calendar types.

### 3. Authentication State and Route Protection
- [ ] `FE-3.1` Implement `AuthContext` with startup session hydration (`GET /auth/me`).
- [ ] `FE-3.2` Implement `useAuth` hook.
- [ ] `FE-3.3` Implement `ProtectedRoute`.
- [ ] `FE-3.4` Implement `AdminRoute`.
- [ ] `FE-3.5` Ensure logout clears client auth state and redirects appropriately.

### 4. Layout and Navigation
- [ ] `FE-4.1` Build `AppLayout` with authenticated navigation.
- [ ] `FE-4.2` Build `AdminLayout` with admin navigation/sidebar.
- [ ] `FE-4.3` Add clear navigation for calendar year selection and history browsing.

### 5. Public and User Pages
- [ ] `FE-5.1` Build `CountdownPage`.
- [ ] `FE-5.2` Build `LoginPage` with two-step request-code/verify-code flow.
- [ ] `FE-5.3` Build `DashboardPage` for beer CRUD.
- [ ] `FE-5.4` Build `LeaderboardPage`.
- [ ] `FE-5.5` Build year-aware `CalendarPage`.
- [ ] `FE-5.5a` Handle `/calendar` redirect to current year.
- [ ] `FE-5.5b` Render `/calendar/:year` 24-door overview.
- [ ] `FE-5.5c` Show locked/unlocked states from API.
- [ ] `FE-5.6` Build `CalendarDayPage` for `/calendar/:year/:day`.

### 6. Admin Pages
- [ ] `FE-6.1` Build `AdminDashboardPage`.
- [ ] `FE-6.2` Build `AdminUsersPage` (create, edit, activate, deactivate).
- [ ] `FE-6.3` Build `AdminCalendarPage`.
- [ ] `FE-6.3a` Year selector and history browsing
- [ ] `FE-6.3b` Create/edit/delete day entries
- [ ] `FE-6.3c` Assign/unassign beer entries
- [ ] `FE-6.4` Build `AdminBeersPage` (all beers with owner display names).

### 7. Component Work
- [ ] `FE-7.1` Implement reusable components: `Navbar`, `BeerCard`, `BeerForm`, `LeaderboardTable`, `CalendarDoor`, `CountdownTimer`.
- [ ] `FE-7.2` Ensure form validation and optimistic/refresh UX for mutations.
- [ ] `FE-7.3` Ensure mobile + desktop responsive layout behavior.

### 8. Testing and Quality (Frontend)
- [ ] `FE-8.1` Configure Vitest + React Testing Library.
- [ ] `FE-8.2` Add unit tests for API client error handling and auth context behavior.
- [ ] `FE-8.3` Add component tests for protected routes and critical forms.
- [ ] `FE-8.4` Add page tests for login flow and year-aware calendar rendering.
- [ ] `FE-8.5` Add admin page tests for role-gated behavior.
- [ ] `FE-8.6` Run lint/type/build checks before merge.

## Suggested Execution Milestones
- [ ] `MS-A` Milestone A: Infra + backend models + seed + health endpoint.
- [ ] `MS-B` Milestone B: Auth/session complete end-to-end.
- [ ] `MS-C` Milestone C: Beer CRUD + leaderboard.
- [ ] `MS-D` Milestone D: Year-aware calendar + history endpoints.
- [ ] `MS-E` Milestone E: Admin features complete.
- [ ] `MS-F` Milestone F: Frontend pages complete.
- [ ] `MS-G` Milestone G: Automated tests + hardening pass.
