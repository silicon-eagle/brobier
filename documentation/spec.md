# Brobier — Beer Advent Calendar Application Specification

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Summary](#2-architecture-summary)
3. [Infrastructure & Docker Compose](#3-infrastructure--docker-compose)
4. [Environment Configuration](#4-environment-configuration)
5. [Database Models](#5-database-models)
6. [Encryption](#6-encryption)
7. [Authentication & JWT](#7-authentication--jwt)
8. [Backend API](#8-backend-api)
9. [Authorization Rules](#9-authorization-rules)
10. [Seed Data](#10-seed-data)
11. [Frontend Pages & Routing](#11-frontend-pages--routing)
12. [Frontend Architecture](#12-frontend-architecture)
13. [Project File Structure](#13-project-file-structure)
14. [Development Workflow](#14-development-workflow)
15. [Security Checklist](#15-security-checklist)
16. [Implementation Order](#16-implementation-order)

---

## 1. Project Overview

Brobier is a private, self-hosted web application that runs an advent-calendar-style beer discovery experience. Approved participants can log in without a password, submit beer entries, view a leaderboard, and open calendar doors that reveal a new beer each day. The calendar runs as a yearly edition (24 doors per year), and prior years remain available as history. Admin users manage participants and curate each year of the calendar.

### Goals

- Simple to run locally with a single command: `docker compose up --build`
- All business rules enforced server-side
- No public registration; all users are created by admins
- Preserve calendar history across years (no overwriting or deleting prior yearly editions during normal yearly setup)

---

## 2. Architecture Summary

| Layer | Technology |
|---|---|
| Backend language | Python 3.13 |
| Web framework | FastAPI |
| ORM | SQLAlchemy 2.0 |
| Validation | Pydantic v2 + pydantic-settings |
| Database | PostgreSQL 18 |
| Auth | Passwordless email code + JWT (access token) + refresh token |
| Token storage | Access JWT in memory (Authorization header); refresh token in HTTP-only cookie |
| Encryption | Fernet (authenticated symmetric encryption, from `cryptography`) |
| Frontend language | TypeScript |
| Frontend framework | React 19 |
| Build tool | Vite 6 |
| Routing | React Router v7 |
| Styling | Tailwind CSS v4 |
| API client | Typed fetch wrapper (hand-rolled, no codegen) |
| Package / task runner | uv |
| CLI | Click (`brobier serve`, `brobier generate-key`) |
| Containerisation (infra) | Docker + Docker Compose v2 |
| Reverse proxy | Nginx (Alpine) |
| Testing | pytest + pytest-asyncio (backend), Vitest + React Testing Library (frontend) |
| Linting / formatting | Ruff |
| Type checking | ty |
| Local email | Mailpit |
| Application timezone | Europe/Amsterdam (`core/time.py`) |

> The backend package is `brobier` (imported as `brobier.*`). In development it runs
> on the host via `uv run brobier serve --reload`; only the database, mail catcher,
> and nginx run in Docker.

---

## 3. Infrastructure & Docker Compose

In development, Docker Compose runs the **supporting infrastructure only**. The
FastAPI backend runs on the host with `uv run brobier serve --reload`.

### Services (`docker-compose.yml`)

| Service | Image | Purpose | Exposed port(s) |
|---|---|---|---|
| `proxy` | `nginx:alpine` | Reverse proxy entry point (`nginx/nginx.conf`) | 80 |
| `db-dev` | `postgres:18-alpine` | PostgreSQL database (dev) | 5432 |
| `mailpit` | `axllent/mailpit` | SMTP catch-all + web UI | 1025 (SMTP), 8025 (web) |

### Docker Compose behaviour

- `db-dev` has a healthcheck via `pg_isready` and restarts unless stopped.
- Environment variables come from the repo-root `.env` file.
- The database admin credentials (`POSTGRES_ADMIN_USER` / `POSTGRES_ADMIN_PASSWORD`) create the database; the init script then provisions a least-privilege app role.
- Volumes:
  - `db-dev-data` persists PostgreSQL data across restarts.
  - `./postgres/init` is mounted into `/docker-entrypoint-initdb.d` to run the role-creation script on first boot.
  - `./data` persists Mailpit messages.
  - `./nginx/nginx.conf` is bind-mounted so proxy rules can change without rebuilding.

### Database roles (`postgres/init/01-create-app-role.sh`)

On first boot the init script, run as the admin user, creates the application role
(`POSTGRES_APP_USER`) and grants it least-privilege access:

- `CONNECT` on the database and `USAGE` on the `public` schema.
- `SELECT, INSERT, UPDATE, DELETE` on tables and `USAGE, SELECT` on sequences via `ALTER DEFAULT PRIVILEGES`.
- `USAGE` on types.

The backend connects with the app role for normal queries (`get_app_engine`) and
with the admin role only to create tables (`get_admin_engine`).

### Backend (host, development)

- Python 3.13, dependencies installed with `uv sync`.
- Run with `uv run brobier serve --reload` (Click CLI → `uvicorn brobier.main:app`).
- On startup the FastAPI `lifespan` runs `init_db` (create missing tables, admin role) and `seed_database` (seed calendar entries).

> A `backend/Dockerfile` exists but is not wired into `docker-compose.yml`; the
> development workflow runs the backend on the host.

### Nginx configuration (`nginx/nginx.conf`)

The committed dev config is intentionally minimal — it listens on port 80 and
returns `200 OK` on `/` as a placeholder. Production proxying rules (routing to
the backend/frontend, SSL termination) are added per deployment.

```nginx
server {
    listen 80;
    server_name localhost;

    location / {
        return 200 'OK';
        add_header Content-Type text/plain;
    }
}
```

---

## 4. Environment Configuration

Settings are loaded by `pydantic-settings` from a single repo-root `.env` file
(see `backend/brobier/core/config.py`). The database URL is **built from parts**
(`DB_HOST`, `DB_PORT`, `DB_NAME` + per-role credentials), not supplied directly.

### `.env` (see `.env.example`)

```
# Environment: dev | tst | prd
ENV=dev

# Database connection
DB_HOST=localhost
DB_NAME=brobier_dev
DB_PORT=5432

# Application (least-privilege) role — used for normal queries
POSTGRES_APP_USER=brobier-dev
POSTGRES_APP_PASSWORD=

# Admin role — used to create the DB/tables and provision the app role
POSTGRES_ADMIN_USER=postgres
POSTGRES_ADMIN_PASSWORD=

# Drop & recreate all tables on startup (dev/test only — destroys data)
DB_OVERWRITE=True

# JWT
JWT_SECRET=change-me-in-production
JWT_ACCESS_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=7
JWT_REFRESH_COOKIE_NAME=brobier_refresh

# Email (Mailpit in dev)
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_FROM=fake-noreply@brobier.local
SMTP_USE_TLS=false

# Login code
LOGIN_CODE_EXPIRE_MINUTES=10
LOGIN_MAX_ATTEMPTS=5

# Encryption — Fernet key. Generate with: uv run brobier generate-key
BEER_ENCRYPTION_KEY=
```

> `JWT_ACCESS_EXPIRE_MINUTES` defaults to `60` in code if unset; the example env
> pins it to `15`. `LOGIN_MAX_ATTEMPTS` wrong codes deactivate a user's login codes.

---

## 5. Database Models

All models use SQLAlchemy. Table creation runs at startup via `Base.metadata.create_all(engine)`.

### 5.1 User

| Column | Type | Constraints |
|---|---|---|
| `id` | `UUID` | PK, generated |
| `email` | `str` | unique, not null, indexed |
| `display_name` | `str` | not null |
| `role` | `enum("user","admin")` | not null, default `"user"` |
| `is_active` | `bool` | not null, default `True` |
| `nr_wrong_login_attempts` | `int` | not null, default `0` |
| `created_at` | `datetime` | not null, default `now()` |
| `updated_at` | `datetime` | not null, updated on save |

- `nr_wrong_login_attempts` is incremented on each failed verify; when it reaches `LOGIN_MAX_ATTEMPTS` the user's login codes are deactivated and the counter resets.

### 5.2 LoginCode

| Column | Type | Constraints |
|---|---|---|
| `id` | `int` | PK, autoincrement |
| `user_id` | `UUID` | FK → User, not null |
| `code_hash` | `str` | not null |
| `expires_at` | `datetime` | not null |
| `is_active` | `bool` | not null, default `True` |
| `used_at` | `datetime` | nullable |
| `created_at` | `datetime` | not null, default `now()` |
| `updated_at` | `datetime` | not null, updated on save |

- A code is valid if `used_at IS NULL`, `is_active = True`, and `expires_at > now`.
- On use, set `used_at = now` immediately (single-use).
- Too many wrong attempts flips `is_active = False` for the user's codes.

### 5.3 RefreshToken

| Column | Type | Constraints |
|---|---|---|
| `id` | `int` | PK, autoincrement |
| `user_id` | `UUID` | FK → User, not null |
| `token_hash` | `str` | not null, indexed |
| `expires_at` | `datetime` | not null |
| `revoked_at` | `datetime` | nullable |
| `created_at` | `datetime` | not null, default `utcnow` |

- A refresh token is valid if `revoked_at IS NULL` and `expires_at > now`.
- Only the SHA-256 hash of the raw token is stored; the raw value is sent to the client as an HTTP-only cookie.
- Access JWTs are stateless and therefore **not** stored in the database; they are validated solely by their signature and expiry claim.

### 5.4 BeerEntry

| Column | Type | Constraints |
|---|---|---|
| `id` | `int` | PK, autoincrement |
| `user_id` | `UUID` | FK → User, not null |
| `year` | `int` | not null, indexed, check year ≥ 2020 |
| `beer_name_encrypted` | `str` | not null |
| `brewery_encrypted` | `str` | not null |
| `untappd_url_encrypted` | `str` | nullable |
| `comment_encrypted` | `str` | nullable |
| `bought_from` | `str` | not null |
| `bought_at` | `datetime` | not null |
| `created_at` | `datetime` | not null, default `now()` |
| `updated_at` | `datetime` | not null, updated on save |

- `year` scopes a beer to a calendar edition; a beer can only be assigned to a calendar day of the **same** year.

### 5.5 CalendarEntry

| Column | Type | Constraints |
|---|---|---|
| `id` | `int` | PK, autoincrement |
| `year` | `int` | not null, indexed, check year ≥ 2020 |
| `day` | `int` | not null, check 1 ≤ day ≤ 24 |
| `unlock_date` | `datetime` | not null |
| `published_at` | `datetime` | nullable |
| `title` | `str` | not null |
| `content` | `str` | not null |
| `image_url` | `str` | nullable |
| `beer_entry_id` | `int` | FK → BeerEntry, nullable, unique |
| `created_at` | `datetime` | not null, default `utcnow` |
| `updated_at` | `datetime` | not null, updated on save |

- Composite uniqueness constraint on (`year`, `day`) so each year has exactly one entry per day.
- Historical rows are immutable by year boundaries: creating a new year must not delete prior years.

### 5.6 UserRating

| Column | Type | Constraints |
|---|---|---|
| `id` | `int` | PK, autoincrement |
| `user_id` | `UUID` | FK → User, not null |
| `beer_entry_id` | `int` | FK → BeerEntry, not null |
| `rating` | `float` | not null, check 1.0 ≤ rating ≤ 5.0 |
| `comment` | `str` | nullable |
| `drank_at` | `datetime` | nullable |
| `created_at` | `datetime` | not null, default `utcnow` |
| `updated_at` | `datetime` | not null, updated on save |

- Composite uniqueness constraint on (`user_id`, `beer_entry_id`): each user can rate a beer only once.
- `rating` is a float to allow half-star granularity (e.g. 3.5).

### Relationships summary

```
DATABASE RELATIONSHIP DIAGRAM (ASCII)

    +------------------------+             1 ---- *             +------------------------+
    |          User          |--------------------------------->|       BeerEntry        |
    |------------------------|                                  |------------------------|
    | PK id (UUID)           |<---------------------------------| PK id (int)            |
    | email (UNIQUE, INDEX)  |          * ---- 1               | FK user_id -> User.id  |
    | display_name           |                                  | year (INDEX, >= 2020)  |
    | role, is_active        |<---------------------------------| beer_name_encrypted    |
    | nr_wrong_login_attempts|          * ---- 1               | brewery_encrypted      |
    | created_at, updated_at |                                  | untappd_url_encrypted? |
    +------------------------+                                  | comment_encrypted?     |
              ^    ^                                            | bought_from            |
              |    | * ---- 1                                   | bought_at              |
              |    |                                            | created_at, updated_at |
              |  +------------------------+                    +------------------------+
              |  |       LoginCode        |                               |
              |  |------------------------|                               | 1 ---- *
              |  | PK id (int)            |                               v
              |  | FK user_id -> User.id  |                    +------------------------+
              |  | code_hash, is_active   |                    |      UserRating        |
              |  | expires_at, used_at    |                    |------------------------|
              |  | created_at, updated_at |                    | PK id (int)            |
              |  +------------------------+                    | FK user_id -> User.id  |
              |                                                | FK beer_entry_id       |
              | * ---- 1                                       | rating (float, 1-5)    |
              |                                                | comment?               |
    +------------------------+                                 | drank_at?              |
    |      RefreshToken      |                                 | created_at, updated_at |
    |------------------------|                                 | UNIQUE(user, beer)     |
    | PK id (int)            |                                 +------------------------+
    | FK user_id -> User.id  |
    | token_hash (INDEX)     |                    +------------------------+
    | expires_at, revoked_at |                    |     CalendarEntry      |
    | created_at             |                    |------------------------|
    +------------------------+                    | PK id (int)            |
                                                  | year, day              |
                                                  | unlock_date            |
                                                  | published_at?          |
                                                  | title, content         |
                                                  | image_url?             |
                                                  | FK beer_entry_id?      |
                                                  | UNIQUE(year, day)      |
                                                  | UNIQUE(beer_entry_id)  |
                                                  | created_at, updated_at |
                                                  +------------------------+

    FK mapping
    - BeerEntry.user_id -> User.id
    - LoginCode.user_id -> User.id
    - RefreshToken.user_id -> User.id
    - CalendarEntry.beer_entry_id -> BeerEntry.id
    - UserRating.user_id -> User.id
    - UserRating.beer_entry_id -> BeerEntry.id

    * encrypted fields in BeerEntry: beer_name, brewery, untappd_url, comment
```

---

## 6. Encryption

### Library

Use `cryptography.fernet.Fernet` for authenticated symmetric encryption (AES-128-CBC + HMAC-SHA256). This ensures beer fields cannot be read from the database even with direct access.

### Key management

- The encryption key is a Fernet key stored as the `BEER_ENCRYPTION_KEY` environment variable.
- The key is never written to the database.
- Generate once with `Fernet.generate_key().decode()`.

### Helper functions (`backend/brobier/core/security.py`)

```python
def encrypt_field(value: str) -> str: ...
def decrypt_field(value: str) -> str: ...
def generate_encryption_key(file: Path | None = None) -> str: ...
```

- `encrypt_field` / `decrypt_field` operate on non-null strings; callers pass `None` through explicitly for optional fields (`untappd_url`, `comment`).
- `decrypt_field` raises `ValueError` if the token is invalid or tampered; `_get_fernet` raises `RuntimeError` if `BEER_ENCRYPTION_KEY` is unset.
- `generate_encryption_key` (exposed as `brobier generate-key`) creates a Fernet key and appends it to `.env`.

### Where encryption/decryption happens

| Operation | Where |
|---|---|
| Create beer entry (user submits) | Encrypt in the `POST /beers` service layer before writing to DB |
| Update beer entry | Encrypt updated fields before writing to DB |
| Read own beer entries (`GET /beers/me`) | Decrypt all fields in the service layer before returning |
| Admin views all beers (`GET /admin/beers`) | Decrypt all fields in the service layer before returning |
| Calendar unlock response | Decrypt linked beer fields in the calendar service layer only if `unlock_date ≤ now` for the requested year/day |
| Locked calendar response | Do not include any encrypted field or its ID |

---

## 7. Authentication & JWT

### 7.1 Login flow

```
1. POST /auth/request-code  { email }
   → Backend checks whether a matching active user exists.
   → If found: generate 6-digit code, hash it, store LoginCode, send email.
   → Always respond: { "message": "If that email is registered, a code has been sent." }
   → This generic response prevents email enumeration.

2. POST /auth/verify-code  { email, code }
   → Backend looks up LoginCode for the email that is unexpired and unused.
   → If valid: mark used_at = now, create RefreshToken (store hash), issue JWT access token.
   → Sets refresh token as an HTTP-only cookie.
   → Returns JWT access token + current user object in the response body.
   → If invalid: return 401 with a generic error.

3. POST /auth/refresh
   → Reads the refresh token from the HTTP-only cookie.
   → Validates it: not revoked, not expired, hash matches a DB row, user still active.
   → Rotates the token: revokes the old row, stores a new hashed refresh token, and sets a new cookie.
   → Issues a new JWT access token.
   → Returns { access_token, token_type: "bearer" } in the response body.
   → Returns 401 if the refresh token is absent, invalid, or expired.

4. POST /auth/logout
   → Sets revoked_at = now on the current RefreshToken row.
   → Clears the refresh-token cookie.

5. GET /auth/me
   → Requires a valid JWT in the Authorization: Bearer <token> header.
   → Returns the current user if the JWT is valid and not expired.
   → Returns 401 if the JWT is absent, invalid, or expired.
```

### 7.2 JWT access token

- Algorithm: `HS256` signed with `JWT_SECRET`.
- Expiry: `JWT_ACCESS_EXPIRE_MINUTES` (example env: **15 minutes**; code default 60).
- Payload claims: `sub` (user id as string), `role`, `iat`, `exp`.
- Transmitted by the client in the `Authorization: Bearer <token>` header.
- **Not stored in the database** — validated purely by signature and expiry.

### 7.3 Refresh token cookie

- Name: `JWT_REFRESH_COOKIE_NAME` from config (default `brobier_refresh`).
- `HttpOnly: true`
- `SameSite: Lax`
- `Secure: true` when `ENV=prd`; `false` otherwise.
- `Path: /auth` (sent to every `/auth/*` endpoint, including refresh and logout).
- Expiry: `JWT_REFRESH_EXPIRE_DAYS` (default 7 days).
- Only the SHA-256 hash of the raw token value is stored in the `refresh_tokens` table.
- Refresh **rotates** the token on every use (old row revoked, new cookie set).

### 7.4 Auth dependencies

```python
async def get_current_user(request: Request) -> User:
    # 1. Read Bearer token from Authorization header.
    # 2. Decode and verify JWT (signature + expiry) using JWT_SECRET.
    # 3. Extract user id from the `sub` claim.
    # 4. Load the User from the database (its own Session).
    # 5. Raise HTTP 401 if the token is absent, malformed, expired, or the user is missing/inactive.

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(403, 'Admin access required.')
    return current_user
```

### 7.5 Login code details

- Code: 6 random decimal digits (`secrets.choice(string.digits)` × 6).
- Hash: `hashlib.sha256(code.encode()).hexdigest()` — fast is acceptable because codes are short-lived (10 min).
- Expiry: `now + timedelta(minutes=LOGIN_CODE_EXPIRE_MINUTES)`.
- Single-use: `used_at` is set on first successful verification.
- Requesting a new code resets the user's wrong-attempt counter.
- After `LOGIN_MAX_ATTEMPTS` failed verifications, the user's codes are set `is_active = False` and the counter resets.

---

## 8. Backend API

### 8.1 Public / Auth endpoints

#### `GET /health`
- Returns `{ "status": "ok" }`.
- No authentication required.

#### `POST /auth/request-code`
- **Request body:** `{ "email": string }`
- **Logic:** Look up active user by email. If found, generate and send code. Always return success message.
- **Response 200:** `{ "message": "If that email is registered, a code has been sent." }`

#### `POST /auth/verify-code`
- **Request body:** `{ "email": string, "code": string }`
- **Logic:** Validate code, create RefreshToken (store hash), issue JWT access token, set refresh cookie.
- **Response 200:** `{ "access_token": string, "token_type": "bearer", "user": { "id", "display_name", "role" } }`
- **Response 401:** `{ "detail": "Invalid or expired code." }`

#### `POST /auth/refresh`
- **Auth required:** valid `brobier_refresh` HTTP-only cookie.
- **Logic:** Validate refresh token hash against DB; issue a new JWT access token.
- **Response 200:** `{ "access_token": string, "token_type": "bearer" }`
- **Response 401:** refresh token absent, invalid, revoked, or expired.

#### `POST /auth/logout`
- **Auth required:** valid `brobier_refresh` HTTP-only cookie.
- **Logic:** Revoke RefreshToken row (`revoked_at = now`), clear refresh cookie.
- **Response 200:** `{ "message": "Logged out." }`

#### `GET /auth/me`
- **Auth required:** valid JWT in `Authorization: Bearer <token>` header.
- **Response 200:** `{ "id", "display_name", "role" }`
- **Response 401:** JWT absent, invalid, or expired.

---

### 8.2 User endpoints

All require a valid JWT in the `Authorization: Bearer <token>` header.

#### `GET /beers/me`
- Returns the current user's beer entries, decrypted.
- **Response 200:** `[ BeerEntryOut ]`

#### `POST /beers`
- Creates a new beer entry owned by the current user.
- **Request body:** `BeerEntryCreate { beer_name, brewery, untappd_url?, comment?, bought_from, bought_at }`
- Encrypts fields before storage.
- **Response 201:** `BeerEntryOut`

#### `PUT /beers/{beer_id}`
- Updates a beer entry owned by the current user.
- **Authorization:** user must own the entry; entry must not be assigned to a calendar entry.
- **Request body:** `BeerEntryUpdate` (all fields optional).
- **Response 200:** `BeerEntryOut`
- **Response 403:** not owner.
- **Response 409:** assigned to calendar entry (cannot edit).

#### `DELETE /beers/{beer_id}`
- Deletes a beer entry owned by the current user.
- **Authorization:** user must own the entry; entry must not be assigned to a calendar entry.
- **Response 204:** no content.
- **Response 403:** not owner.
- **Response 409:** assigned to calendar entry (cannot delete).

#### `POST /beers/{beer_id}/ratings`
- Submits a rating for a beer entry on behalf of the current user.
- **Authorization:** any authenticated user may rate any beer entry (including beers they submitted themselves).
- **Request body:** `UserRatingCreate { rating, comment?, drank_at? }`
- **Response 201:** `UserRatingOut`
- **Response 404:** beer entry not found.
- **Response 409:** current user has already rated this beer (one rating per user per beer).

#### `PUT /beers/{beer_id}/ratings/me`
- Updates the current user's existing rating for a beer entry.
- **Request body:** `UserRatingUpdate` (all fields optional).
- **Response 200:** `UserRatingOut`
- **Response 404:** beer entry not found, or current user has not yet rated this beer.

#### `DELETE /beers/{beer_id}/ratings/me`
- Deletes the current user's rating for a beer entry.
- **Response 204:** no content.
- **Response 404:** beer entry not found, or current user has not yet rated this beer.

#### `GET /leaderboard`
- Returns non-admin users ranked by beer count for a year, descending (ties broken by display name).
- Optional query param: `year` (int). If omitted, defaults to the current year.
- Users with zero beers that year are still listed with `beer_count = 0`.
- **Response 200:** `[ { "display_name": string, "beer_count": int } ]`

#### `GET /calendar`
- Returns all calendar entries with unlock-aware content for a single year.
- Optional query param: `year` (int). If omitted, defaults to the current year.
- Locked entries return only safe fields (`id`, `year`, `day`, `unlock_date`, `is_locked`).
- Unlocked entries return full content and decrypted beer details if a beer is linked.
- **Response 200:** `[ CalendarEntryOut ]`

#### `GET /calendar/{year}/{day}`
- Returns a single calendar entry for the given `year` and `day` (1–24), both path params.
- **Day-gated:** returns `403` if the day is still locked (`unlock_date > now`) instead of the locked schema.
- **Response 200:** `CalendarEntryOut`
- **Response 403:** day not yet unlocked.
- **Response 404:** day/year not found.

#### `GET /calendar/years`
- Returns available calendar years (ascending) so the UI can browse history.
- **Response 200:** `[ { "year": int } ]`

---

### 8.3 Admin endpoints

All require a valid JWT with role `admin` in the `Authorization: Bearer <token>` header.

#### `GET /admin/users`
- Returns all users.
- **Response 200:** `[ AdminUserOut ]`

#### `POST /admin/users`
- Creates a new user.
- **Request body:** `UserCreate { email, display_name, role?, is_active? }`
- **Response 201:** `AdminUserOut`
- **Response 409:** email already exists.

#### `PUT /admin/users/{user_id}`
- Updates user fields (display_name, role, is_active).
- **Request body:** `UserUpdate` (all fields optional).
- **Response 200:** `AdminUserOut`
- **Response 404:** user not found.

#### `POST /admin/users/{user_id}/deactivate`
- Sets `is_active = False`.
- **Response 200:** `AdminUserOut`

#### `POST /admin/users/{user_id}/activate`
- Sets `is_active = True`.
- **Response 200:** `AdminUserOut`

#### `GET /admin/beers`
- Returns all beer entries for all users, decrypted, with owner display name.
- Optional query param: `year` (int) to filter by calendar year.
- **Response 200:** `[ AdminBeerEntryOut ]`

#### `GET /admin/calendar`
- Returns all calendar entries with full content (ignores unlock date) for a single year.
- Optional query param: `year` (int). If omitted, defaults to the current year.
- Includes decrypted beer details for any linked beer.
- **Response 200:** `[ AdminCalendarEntryOut ]`

#### `PUT /admin/calendar/{year}`
- Creates the 24 calendar days for the given year. Existing days are skipped (idempotent).
- **Response 204:** no content.

#### `DELETE /admin/calendar/{year}`
- Deletes all calendar days for the given year.
- **Response 204:** no content.
- **Response 409:** at least one day of that year has an assigned beer.

#### `PUT /admin/calendar/{year}/{day}/beer`
- Assigns a beer entry to the calendar day identified by `year` + `day`.
- **Request body:** `{ "beer_entry_id": int }`
- Enforces: the beer must exist, belong to the same `year`, and not already be assigned elsewhere.
- **Response 200:** `AdminCalendarEntryOut`
- **Response 404:** calendar entry or beer entry not found.
- **Response 409:** beer belongs to a different year, or is already assigned to a day.

#### `DELETE /admin/calendar/{year}/{day}/beer`
- Unassigns the beer entry from the calendar day (sets `beer_entry_id = null`).
- **Response 200:** `AdminCalendarEntryOut`
- **Response 404:** calendar entry not found.

> There is no per-entry `POST/PUT/DELETE /admin/calendar/{entry_id}` in the current
> implementation — days are created/removed a whole year at a time, and a day's
> title/content are seeded (not yet editable over the API).

---

### 8.4 Response schemas (Pydantic)

#### `UserOut` (auth `/auth/me`, `/auth/verify-code`)
```
id, display_name, role
```

#### `AdminUserOut` (admin user endpoints)
```
id, email, display_name, role, is_active, created_at, updated_at
```

#### `BeerEntryOut`
```
id, user_id, year, beer_name, brewery, untappd_url, comment, bought_from, bought_at, created_at, updated_at
```
(All encrypted fields decrypted in this schema. Encrypted column names are internal only.)

#### `AdminBeerEntryOut`
```
id, user_id, display_name (owner), year, beer_name, brewery, untappd_url, comment, bought_from, bought_at, created_at, updated_at
```

#### `UserRatingOut`
```
id, user_id, beer_entry_id, rating, comment, drank_at, created_at, updated_at
```

#### `CalendarEntryOut` (user-facing, unlock-aware)

Locked state:
```
id, year, day, unlock_date, is_locked: true   # title, content, image_url, beer are null
```

Unlocked state:
```
id, year, day, unlock_date, title, content, image_url, is_locked: false,
beer?: { id, beer_name, brewery, untappd_url, comment, bought_from, submitted_by, ratings: [UserRatingOut] }
```

#### `AdminCalendarEntryOut` (admin-facing, full data)
```
year, day, unlock_date, title, content, image_url,
beer_entry_id,
beer?: { id, user_id, display_name, beer_name, brewery, untappd_url, comment, bought_from, bought_at, ratings: [UserRatingOut] }
```

---

## 9. Authorization Rules

| Action | Rule |
|---|---|
| View own beers | Authenticated; query filters by `beer.user_id == current_user.id` |
| Create beer | Authenticated |
| Edit own beer | Authenticated; update query filters by `user_id` (others' beers → 404) |
| Delete own beer | Authenticated; owner-scoped; blocked (409) if beer is assigned to a calendar day or already has a rating |
| Submit rating | Authenticated; any user may rate any beer; one rating per user per beer |
| Edit own rating | Authenticated; `rating.user_id == current_user.id` |
| Delete own rating | Authenticated; `rating.user_id == current_user.id` |
| View leaderboard | Authenticated (router currently has no auth dependency); admins excluded from results |
| View calendar | Authenticated; year defaults to current year; locked entries return only safe fields |
| View locked beer | Blocked server-side; a locked single day returns `403` |
| All `/admin/*` routes | Role must be `"admin"` |
| Assign/unassign beer | Admin only (`PUT`/`DELETE /admin/calendar/{year}/{day}/beer`) |
| View any beer | Admin only (`GET /admin/beers`) |
| Create/edit/delete users | Admin only |
| Create/delete calendar years | Admin only |

---

## 10. Seed Data

Seeding runs at startup (`seeds/seed.py`). Each seeder is idempotent: it only
inserts rows when its table has not been seeded yet. The FastAPI `lifespan`
currently seeds **calendar entries**; the users seeder is available and runs when
the `users` table is empty.

### Admin user

```
email: admin@brobier.local
display_name: Admin
role: admin
is_active: true
```

### Participant users

```
email: alice@brobier.local, display_name: Alice, role: user, is_active: true
email: bob@brobier.local,   display_name: Bob,   role: user, is_active: true
email: carol@brobier.local, display_name: Carol, role: user, is_active: true
email: dave@brobier.local,  display_name: Dave,  role: user, is_active: false
```

### Calendar entries

The calendar seeder creates all 24 days for **three years**: previous, current,
and next (`current_year - 1`, `current_year`, `current_year + 1`). For each year:

- `day`: 1–24
- `unlock_date`: December `day` of that year at 08:00 in the app timezone (Europe/Amsterdam)
- `title`: `"Day {day}"`
- `content`: empty string
- `image_url`: null
- `beer_entry_id`: null (admins assign beers later)

Existing days for a year are preserved; only missing days are inserted, so prior
years are never overwritten.

> Beer entries and ratings are **not** seeded automatically. Admins create the
> calendar structure and assign beers via the admin API.

---

## 11. Frontend Pages & Routing

### Route table

| Path | Component | Auth | Notes |
|---|---|---|---|
| `/` | `CountdownPage` | Public | Christmas countdown |
| `/login` | `LoginPage` | Public (redirect if logged in) | Two-step: request code, verify code |
| `/dashboard` | `DashboardPage` | Authenticated | Own beer entries |
| `/leaderboard` | `LeaderboardPage` | Authenticated | |
| `/calendar` | `CalendarPage` | Authenticated | Redirects to current year overview |
| `/calendar/:year` | `CalendarPage` | Authenticated | 24 doors overview for a year |
| `/calendar/:year/:day` | `CalendarDayPage` | Authenticated | Single day detail for a year |
| `/admin` | `AdminDashboardPage` | Admin | Links to sub-pages |
| `/admin/users` | `AdminUsersPage` | Admin | User CRUD |
| `/admin/calendar` | `AdminCalendarPage` | Admin | Calendar + beer assignment for selected year |
| `/admin/beers` | `AdminBeersPage` | Admin | View all beers |

### Protected route components

```tsx
// ProtectedRoute — redirects to /login if not authenticated
// AdminRoute — renders ProtectedRoute + checks role === "admin", redirects to / if not admin
```

### Layout components

- `AppLayout` — shared header/nav, wraps authenticated pages.
- `AdminLayout` — admin sidebar nav, wraps admin pages.

---

## 12. Frontend Architecture

### `frontend/src/api/`

A typed API client module. Each backend route group gets its own file:

- `client.ts` — base fetch wrapper with credentials, base URL, and error handling.
- `auth.ts` — `requestCode`, `verifyCode`, `logout`, `me`.
- `beers.ts` — `getMyBeers`, `createBeer`, `updateBeer`, `deleteBeer`.
- `leaderboard.ts` — `getLeaderboard`.
- `calendar.ts` — `getCalendar(year?)`, `getCalendarDay(day, year?)`, `getCalendarYears`.
- `admin.ts` — all admin endpoints.

The base client:
- Reads `VITE_API_BASE_URL` from env.
- Stores the JWT access token in memory (React context / closure) and attaches it as `Authorization: Bearer <token>` on every authenticated request.
- Always sends `credentials: "include"` so the `brobier_refresh` cookie is forwarded to `/auth/refresh`.
- Automatically calls `POST /auth/refresh` when it receives a `401` response, then retries the original request once with the new access token.
- Throws a typed `ApiError` on non-2xx responses that cannot be recovered by a token refresh.

### `frontend/src/auth/`

- `AuthContext.tsx` — React context providing `user`, `isLoading`, `login`, `logout`, and the in-memory access token setter.
- `useAuth.ts` — convenience hook returning auth context.
- On mount, calls `POST /auth/refresh` (using the HttpOnly cookie) to hydrate auth state and obtain a fresh access token. Falls back to unauthenticated state on 401.

### `frontend/src/types/`

TypeScript interfaces mirroring backend response schemas:

- `User.ts`
- `BeerEntry.ts`
- `CalendarEntry.ts`
- `Leaderboard.ts`

---

## 13. Project File Structure

```
brobier/
├── docker-compose.yml         ← dev infra: proxy (nginx), db-dev (postgres), mailpit
├── .env.example               ← root-level env reference (loaded by the backend)
│
├── nginx/
│   └── nginx.conf             ← reverse proxy config (placeholder in dev)
│
├── postgres/
│   └── init/
│       └── 01-create-app-role.sh  ← provisions least-privilege app role
│
├── backend/
│   ├── Dockerfile             ← present but not used by docker-compose
│   ├── pyproject.toml
│   ├── uv.lock
│   └── brobier/
│       ├── main.py            ← FastAPI app, routers, lifespan (init + seed)
│       ├── cli.py             ← `brobier serve`, `brobier generate-key`
│       ├── core/
│       │   ├── config.py      ← pydantic-settings Settings
│       │   ├── security.py    ← Fernet encrypt/decrypt, key generation
│       │   ├── exceptions.py  ← typed AppError hierarchy
│       │   └── time.py        ← app timezone + current_time()
│       ├── db/
│       │   ├── engine.py      ← app/admin engines
│       │   ├── init_db.py     ← create/drop/recreate tables
│       │   ├── utils.py       ← Table enum
│       │   └── models/
│       │       ├── base.py
│       │       ├── user.py
│       │       ├── login_code.py
│       │       ├── refresh_token.py
│       │       ├── beer_entry.py
│       │       ├── calendar_entry.py
│       │       └── user_rating.py
│       ├── schemas/
│       │   ├── auth.py
│       │   ├── admin.py
│       │   ├── beer.py
│       │   ├── calendar.py
│       │   ├── leaderboard.py
│       │   └── user_rating.py
│       ├── api/
│       │   └── routes/
│       │       ├── auth.py
│       │       ├── beers.py
│       │       ├── leaderboard.py
│       │       ├── calendar.py
│       │       └── admin/
│       │           ├── users.py
│       │           ├── beers.py
│       │           └── calendar.py
│       ├── services/
│       │   ├── auth_service.py
│       │   ├── beers_service.py
│       │   ├── calendar_service.py
│       │   ├── leaderboard_service.py
│       │   ├── user_service.py
│       │   └── sender.py       ← send_login_code_email()
│       ├── auth/
│       │   ├── dependencies.py ← get_current_user, require_admin, get_refresh_token_raw
│       │   ├── jwt.py          ← create/decode access token
│       │   └── tokens.py       ← code/refresh token generation + hashing
│       ├── templates/
│       │   └── email/          ← Jinja login-code templates
│       └── seeds/
│           └── seed.py
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── postcss.config.cjs
│   ├── index.html
│   ├── .env.example
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   ├── client.ts
│       │   ├── auth.ts
│       │   ├── beers.ts
│       │   ├── leaderboard.ts
│       │   ├── calendar.ts
│       │   └── admin.ts
│       ├── auth/
│       │   ├── AuthContext.tsx
│       │   └── useAuth.ts
│       ├── components/
│       │   ├── CountdownTimer.tsx
│       │   ├── BeerCard.tsx
│       │   ├── BeerForm.tsx
│       │   ├── CalendarDoor.tsx
│       │   ├── LeaderboardTable.tsx
│       │   └── Navbar.tsx
│       ├── layouts/
│       │   ├── AppLayout.tsx
│       │   └── AdminLayout.tsx
│       ├── pages/
│       │   ├── CountdownPage.tsx
│       │   ├── LoginPage.tsx
│       │   ├── DashboardPage.tsx
│       │   ├── LeaderboardPage.tsx
│       │   ├── CalendarPage.tsx
│       │   ├── CalendarDayPage.tsx
│       │   ├── AdminDashboardPage.tsx
│       │   ├── AdminUsersPage.tsx
│       │   ├── AdminCalendarPage.tsx
│       │   └── AdminBeersPage.tsx
│       ├── routes/
│       │   ├── ProtectedRoute.tsx
│       │   └── AdminRoute.tsx
│       └── types/
│           ├── User.ts
│           ├── BeerEntry.ts
│           ├── CalendarEntry.ts
│           └── Leaderboard.ts
│
└── documentation/
    └── spec.md
```

---

## 14. Development Workflow

### Start the infrastructure

```bash
cp .env.example .env      # then fill in the blank secrets
docker compose up -d
```

This starts nginx (`proxy`), PostgreSQL (`db-dev`), and Mailpit.

- Nginx entry point: http://localhost (placeholder `OK` in dev)
- Mailpit web UI: http://localhost:8025
- PostgreSQL (dev only): localhost:5432

### Run the backend (host)

```bash
cd backend
uv sync
uv run brobier generate-key   # once, to populate BEER_ENCRYPTION_KEY in .env
uv run brobier serve --reload
```

- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

On startup the backend creates missing tables and seeds calendar entries.

### First login

1. `POST /auth/request-code` with `alice@brobier.local` (or any seeded user email).
2. Open http://localhost:8025 to read the login code email.
3. `POST /auth/verify-code` with the email + code to receive an access token and refresh cookie.

### Admin login

Use `admin@brobier.local` and the same flow; the returned user has `role = admin`.

### Reset the database

```bash
docker compose down -v    # drops the db-dev-data volume
docker compose up -d
```

Alternatively, set `DB_OVERWRITE=true` in `.env` (dev/test only) to drop and
recreate all tables on the next backend startup.

### Run the tests

```bash
cd backend && uv run pytest
```

---

## 15. Security Checklist

| Concern | Mitigation |
|---|---|
| Email enumeration | `/auth/request-code` always returns the same generic message |
| Brute-force login codes | Codes expire in 10 minutes; single-use; no detail on failure |
| Token fixation | A new refresh token is created on every successful login |
| Short-lived access tokens | JWT access tokens expire after 15 minutes; damage from token theft is time-bounded |
| XSS token theft | Refresh token in `HttpOnly` cookie; access token lives only in JS memory (never persisted to `localStorage`) |
| CSRF | `SameSite: Lax` cookie; refresh cookie is scoped to `Path: /auth/refresh`; state-changing endpoints use POST/PUT/DELETE (not GET) |
| Encrypted field leakage | Encrypted column values never appear in API responses; decryption happens in the service layer |
| Locked calendar leakage | Backend strips all sensitive fields before unlock date, regardless of auth level |
| Unauthorised admin access | `require_admin` dependency enforced on all `/admin/*` routes |
| SQL injection | All queries via SQLAlchemy ORM; no raw SQL strings |
| Secrets in source | Keys only in `.env` files; `.env` is in `.gitignore` |
| Insecure direct object reference | Ownership check (`beer.user_id == current_user.id`) on every mutating beer endpoint |
| Overly permissive CORS | Frontend and backend served same-origin behind `nginx`; no cross-origin requests, so no CORS is configured |
| Service network exposure | `backend` and `frontend` not bound to host; only `nginx` exposes port 80 |
| IP address hard-coding | All inter-service references use Docker Compose service names resolved by the internal DNS |
| Production hardening | `Secure` cookie flag on refresh token; `ENVIRONMENT` env var gates dev-only behaviour |

---

## 16. Implementation Order

The following sequence minimises blocked steps and ensures each phase is testable before the next begins.

1. **Project scaffolding** — Create directory structure, Docker Compose, Dockerfiles, `nginx/nginx.conf`, `backend/pyproject.toml`, `backend/uv.lock`, package.json.
2. **Backend config & DB connection** — `config.py` (Pydantic Settings), `db/session.py`, `main.py` startup.
3. **SQLAlchemy models** — Define all five models with correct types, constraints, and relationships.
4. **`init_db.py`** — `create_all` + call to seed function.
5. **Seed data** — Insert admin, participants, beers, and year-scoped calendar entries idempotently, preserving prior years.
6. **Encryption helpers** — `encrypt_field` / `decrypt_field` in `security.py`.
7. **Auth service** — `request_code`, `verify_code`, refresh token creation and revocation.
8. **Email sender** — `send_login_code` via SMTP (Mailpit in dev).
9. **Session dependency** — `get_current_user`, `require_admin` in `auth/dependencies.py`.
10. **Auth routes** — `/health`, `/auth/*`.
11. **Beer schemas & service** — Pydantic schemas, CRUD with encryption/decryption.
12. **Beer routes** — `/beers/me`, `POST /beers`, `PUT /beers/{id}`, `DELETE /beers/{id}`.
13. **Leaderboard route** — `GET /leaderboard`.
14. **Calendar service** — Year-aware unlock logic, field filtering, history retrieval.
15. **Calendar routes** — `GET /calendar`, `GET /calendar/{day}`, `GET /calendar/years`.
16. **Admin service** — User CRUD, beer reads, calendar CRUD, beer assignment.
17. **Admin routes** — All `/admin/*` endpoints.
18. **Frontend scaffolding** — Vite 6 + React 19 + TypeScript + Tailwind CSS v4 + React Router v7 setup.
19. **Type definitions** — `types/` interfaces.
20. **API client** — `api/client.ts` base wrapper + all endpoint modules.
21. **Auth context** — `AuthContext.tsx`, `useAuth.ts`, `ProtectedRoute`, `AdminRoute`.
22. **Countdown page** — `/` with live timer.
23. **Login page** — Two-step flow: request code → verify code.
24. **Dashboard page** — Beer list, create/edit/delete form.
25. **Leaderboard page** — Ranked table.
26. **Calendar overview page** — year navigation + 24 doors, locked/unlocked visual states.
27. **Calendar day page** — Single year/day detail with beer info if unlocked.
28. **Admin dashboard** — Links and overview.
29. **Admin users page** — Create, edit, activate/deactivate.
30. **Admin calendar page** — Create/edit calendar entries, assign/unassign beers.
31. **Admin beers page** — View all submitted beers.
32. **README** — Setup, development, reset, and first-login instructions.
33. **Final review** — Security checklist pass, CORS, cookie flags, env examples.
