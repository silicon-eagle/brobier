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
| Backend language | Python 3.14 |
| Web framework | FastAPI |
| ORM | SQLAlchemy |
| Validation | Pydantic v2 |
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
| Containerisation | Docker + Docker Compose v2 |
| Reverse proxy | Nginx (Alpine) |
| Testing | pytest + pytest-asyncio (backend), Vitest + React Testing Library (frontend) |
| Linting / formatting | Ruff |
| Type checking | ty |
| Local email | Mailpit |

---

## 3. Infrastructure & Docker Compose

### Services

| Service | Image / Build | Purpose | Internal port | Exposed port |
|---|---|---|---|---|
| `db` | `postgres:18` | PostgreSQL database | 5432 | 5432 (dev only) |
| `mailpit` | `axllent/mailpit` | SMTP catch-all + web UI | 1025 (SMTP), 8025 (HTTP) | 8025 |
| `backend` | `./backend` (custom) | FastAPI application | 8000 | — (nginx only) |
| `frontend` | `./frontend` (custom) | Vite dev server | 5173 | — (nginx only) |
| `nginx` | `nginx:alpine` | Reverse proxy entry point | 80 | 80 |

All user-facing traffic enters through `nginx` on port 80. The `backend` and `frontend` services are not exposed directly to the host.

### Docker Compose behaviour

- `backend` depends on `db` being healthy (healthcheck via `pg_isready`).
- `backend` depends on `mailpit` being started.
- `frontend` depends on `backend` being started.
- `nginx` depends on `backend` and `frontend` being started.
- All inter-service communication uses Docker Compose service names (e.g. `db`, `backend`, `frontend`, `mailpit`). IP addresses are never hard-coded.
- Environment variables are supplied via `.env` files mounted per service.
- Volumes:
  - `postgres_data` persists the database across restarts.
  - The `backend` source directory is bind-mounted for hot reload in dev.
  - The `frontend` source directory is bind-mounted for HMR in dev.
  - The `nginx/nginx.conf` file is bind-mounted so proxy rules can be changed without rebuilding the image.

### Backend Dockerfile (development)

- Base: `python:3.14-slim`
- Install dependencies with `uv sync --frozen` using `pyproject.toml` and `uv.lock`.
- Run with `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`.
- On startup, run `init_db.py` to create tables and seed data if the database is empty.

### Frontend Dockerfile (development)

- Base: `node:24-alpine`
- Install with `npm install`.
- Run `npm run dev -- --host` to expose Vite HMR outside the container.

### Nginx configuration (`nginx/nginx.conf`)

- Listen on port 80.
- Route `/api/` → `http://backend:8000/` (proxy pass, strip `/api` prefix).
- Route `/` → `http://frontend:5173/` (proxy pass, preserve path).
- Forward `Host`, `X-Real-IP`, and `X-Forwarded-For` headers on all proxied requests.
- Enable WebSocket upgrade headers on the frontend upstream to support Vite HMR (`Connection: Upgrade`, `Upgrade: $http_upgrade`).
- No SSL termination in development; add SSL block for production deployments.

```nginx
upstream backend {
    server backend:8000;
}

upstream frontend {
    server frontend:5173;
}

server {
    listen 80;
    server_name _;

    # API traffic → FastAPI
    location /api/ {
        proxy_pass         http://backend/;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }

    # All other traffic → Vite dev server (including HMR WebSocket)
    location / {
        proxy_pass         http://frontend/;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade           $http_upgrade;
        proxy_set_header   Connection        "upgrade";
    }
}
```

> **Note:** The `/api/` prefix is stripped by nginx before forwarding to FastAPI. FastAPI routes therefore do **not** include `/api` in their path definitions. The frontend API client must prefix all requests with `/api`.

---

## 4. Environment Configuration

### Backend `.env.example`

```
# Database
DATABASE_URL=postgresql+psycopg://brobier:brobier@db:5432/brobier

# JWT
JWT_SECRET=change-me-in-production
JWT_ACCESS_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=7
JWT_REFRESH_COOKIE_NAME=brobier_refresh

# Encryption
BEER_ENCRYPTION_KEY=<Fernet key — generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">

# Email (Mailpit in dev)
SMTP_HOST=mailpit
SMTP_PORT=1025
SMTP_FROM=noreply@brobier.local
SMTP_USE_TLS=false

# Login code
LOGIN_CODE_EXPIRE_MINUTES=10

# CORS — allow requests originating from the nginx entry point
CORS_ORIGINS=http://localhost

# Environment
ENVIRONMENT=development
```

### Frontend `.env.example`

```
# All API calls go through the nginx reverse proxy at /api
VITE_API_BASE_URL=http://localhost/api
```

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
| `created_at` | `datetime` | not null, default `utcnow` |
| `updated_at` | `datetime` | not null, updated on save |

### 5.2 LoginCode

| Column | Type | Constraints |
|---|---|---|
| `id` | `int` | PK, autoincrement |
| `user_id` | `UUID` | FK → User, not null |
| `code_hash` | `str` | not null |
| `expires_at` | `datetime` | not null |
| `used_at` | `datetime` | nullable |
| `created_at` | `datetime` | not null, default `utcnow` |
| `updated_at` | `datetime` | not null, updated on save |

- A code is valid if `used_at IS NULL` and `expires_at > now`.
- On use, set `used_at = now` immediately (single-use).

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
| `beer_name_encrypted` | `str` | not null |
| `brewery_encrypted` | `str` | not null |
| `untappd_url_encrypted` | `str` | nullable |
| `comment_encrypted` | `str` | nullable |
| `bought_from` | `str` | not null |
| `bought_at` | `datetime` | not null |
| `created_at` | `datetime` | not null, default `utcnow` |
| `updated_at` | `datetime` | not null, updated on save |

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
    | PK id (int)            |<---------------------------------| PK id (int)            |
    | email (UNIQUE, INDEX)  |          * ---- 1               | FK user_id -> User.id  |
    | display_name           |                                  | beer_name_encrypted    |
    | role, is_active        |<---------------------------------| brewery_encrypted      |
    | created_at, updated_at |          * ---- 1               | untappd_url_encrypted? |
    +------------------------+                                  | comment_encrypted?     |
              ^    ^                                            | bought_from            |
              |    | * ---- 1                                   | bought_at              |
              |    |                                            | created_at, updated_at |
              |  +------------------------+                    +------------------------+
              |  |       LoginCode        |                               |
              |  |------------------------|                               | 1 ---- *
              |  | PK id (int)            |                               v
              |  | FK user_id -> User.id  |                    +------------------------+
              |  | code_hash              |                    |      UserRating        |
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

### Helper functions (`backend/app/core/security.py`)

```python
def encrypt_field(value: str | None) -> str | None: ...
def decrypt_field(value: str | None) -> str | None: ...
```

- `encrypt_field` returns `None` if `value` is `None`.
- `decrypt_field` returns `None` if `value` is `None`.
- Both raise an application error if the key is missing or decryption fails.

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
   → Validates it: not revoked, not expired, hash matches a DB row.
   → Issues a new JWT access token (15-minute expiry).
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
- Expiry: `JWT_ACCESS_EXPIRE_MINUTES` (default **15 minutes**).
- Payload claims: `sub` (user id as string), `exp`, `iat`.
- Transmitted by the client in the `Authorization: Bearer <token>` header.
- **Not stored in the database** — validated purely by signature and expiry.

### 7.3 Refresh token cookie

- Name: `JWT_REFRESH_COOKIE_NAME` from config (default `brobier_refresh`).
- `HttpOnly: true`
- `SameSite: Lax`
- `Secure: true` in production; `false` in development.
- `Path: /auth/refresh` (scoped so it is only sent to the refresh endpoint).
- Expiry: `JWT_REFRESH_EXPIRE_DAYS` (default 7 days).
- Only the SHA-256 hash of the raw token value is stored in the `refresh_tokens` table.

### 7.4 Auth dependencies

```python
async def get_current_user(request: Request, db: Session) -> User:
    # 1. Read Bearer token from Authorization header.
    # 2. Decode and verify JWT (signature + expiry) using JWT_SECRET.
    # 3. Extract user id from the `sub` claim.
    # 4. Load and return the User from the database.
    # 5. Raise HTTP 401 if the token is absent, malformed, expired, or the user no longer exists.

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(403)
    return current_user
```

### 7.5 Login code details

- Code: 6 random decimal digits (`secrets.randbelow` or `str(secrets.token_hex(3)).zfill(6)` resampled to 6 digits).
- Hash: `hashlib.sha256(code.encode()).hexdigest()` — fast is acceptable because codes are short-lived (10 min) and rate-limiting is acceptable at the application layer.
- Expiry: `now + timedelta(minutes=LOGIN_CODE_EXPIRE_MINUTES)`.
- Single-use: `used_at` is set on first successful verification.
- Old unused codes for the same user can be left in the database; only the most recently created valid code is accepted per user per verification attempt (or alternatively, invalidate prior codes on new request).

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
- Returns all active users ranked by total beer count, descending.
- **Response 200:** `[ { "display_name": string, "beer_count": int } ]`

#### `GET /calendar`
- Returns all 24 calendar entries with unlock-aware content for a single year.
- Optional query param: `year` (int). If omitted, default to current UTC year.
- Locked entries return only safe fields (day, unlock_date, title).
- Unlocked entries return full content and decrypted beer details if a beer is linked.
- **Response 200:** `[ CalendarEntryOut ]`

#### `GET /calendar/{day}`
- Returns a single calendar entry (1–24) for a single year.
- Optional query param: `year` (int). If omitted, default to current UTC year.
- Same unlock-aware logic as above.
- **Response 200:** `CalendarEntryOut`
- **Response 404:** day/year not found.

#### `GET /calendar/years`
- Returns available calendar years (descending) so the UI can browse history.
- **Response 200:** `[ { "year": int } ]`

---

### 8.3 Admin endpoints

All require a valid JWT with role `admin` in the `Authorization: Bearer <token>` header.

#### `GET /admin/users`
- Returns all users.
- **Response 200:** `[ UserOut ]`

#### `POST /admin/users`
- Creates a new user.
- **Request body:** `UserCreate { email, display_name, role?, is_active? }`
- **Response 201:** `UserOut`
- **Response 409:** email already exists.

#### `PUT /admin/users/{user_id}`
- Updates user fields (display_name, role, is_active).
- **Request body:** `UserUpdate` (all fields optional).
- **Response 200:** `UserOut`

#### `POST /admin/users/{user_id}/deactivate`
- Sets `is_active = False`.
- **Response 200:** `UserOut`

#### `POST /admin/users/{user_id}/activate`
- Sets `is_active = True`.
- **Response 200:** `UserOut`

#### `GET /admin/beers`
- Returns all beer entries for all users, decrypted, with owner display name.
- **Response 200:** `[ AdminBeerEntryOut ]`

#### `GET /admin/calendar`
- Returns all 24 calendar entries with full content (ignores unlock date) for a single year.
- Optional query param: `year` (int). If omitted, default to current UTC year.
- Includes decrypted beer details for any linked beer.
- **Response 200:** `[ AdminCalendarEntryOut ]`

#### `POST /admin/calendar`
- Creates a calendar entry for a specific year.
- **Request body:** `CalendarEntryCreate { year, day, unlock_date, title, content, image_url? }`
- **Response 201:** `AdminCalendarEntryOut`
- **Response 409:** day already exists for that year.

#### `PUT /admin/calendar/{entry_id}`
- Updates a calendar entry (does not touch beer assignment).
- **Request body:** `CalendarEntryUpdate` (all fields optional).
- **Response 200:** `AdminCalendarEntryOut`

#### `DELETE /admin/calendar/{entry_id}`
- Deletes a calendar entry. Does not delete the linked beer entry.
- **Response 204:** no content.

#### `PUT /admin/calendar/{entry_id}/beer`
- Assigns a beer entry to a calendar day in a specific year (identified by `entry_id`).
- **Request body:** `{ "beer_entry_id": UUID }`
- Enforces uniqueness: a beer entry can only be assigned to one day.
- **Response 200:** `AdminCalendarEntryOut`
- **Response 404:** beer entry not found.
- **Response 409:** beer already assigned to another day.

#### `DELETE /admin/calendar/{entry_id}/beer`
- Unassigns the beer entry from the calendar day (sets `beer_entry_id = null`).
- **Response 200:** `AdminCalendarEntryOut`

---

### 8.4 Response schemas (Pydantic)

#### `UserOut`
```
id, email, display_name, role, is_active, created_at, updated_at
```

#### `BeerEntryOut`
```
id, user_id, beer_name, brewery, untappd_url, comment, bought_from, bought_at, created_at, updated_at
```
(All encrypted fields decrypted in this schema. Encrypted column names are internal only.)

#### `AdminBeerEntryOut`
```
id, user_id, display_name (owner), beer_name, brewery, untappd_url, comment, bought_from, bought_at, created_at, updated_at
```

#### `UserRatingOut`
```
id, user_id, beer_entry_id, rating, comment, drank_at, created_at, updated_at
```

#### `CalendarEntryOut` (user-facing, unlock-aware)

Locked state:
```
id, year, day, unlock_date, title, is_locked: true
```

Unlocked state:
```
id, year, day, unlock_date, title, content, image_url, is_locked: false,
beer?: { id, beer_name, brewery, untappd_url, comment, bought_from, submitted_by, ratings: [UserRatingOut] }
```

#### `AdminCalendarEntryOut` (admin-facing, full data)
```
id, year, day, unlock_date, title, content, image_url,
beer_entry_id,
beer?: { id, user_id, display_name, beer_name, brewery, untappd_url, comment, bought_from, bought_at, ratings: [UserRatingOut] }
```

---

## 9. Authorization Rules

| Action | Rule |
|---|---|
| View own beers | Authenticated; `beer.user_id == current_user.id` |
| Create beer | Authenticated |
| Edit own beer | Authenticated; `beer.user_id == current_user.id`; beer not assigned to calendar |
| Delete own beer | Authenticated; `beer.user_id == current_user.id`; beer not assigned to calendar |
| Submit rating | Authenticated; any user may rate any beer; one rating per user per beer |
| Edit own rating | Authenticated; `rating.user_id == current_user.id` |
| Delete own rating | Authenticated; `rating.user_id == current_user.id` |
| View leaderboard | Authenticated |
| View calendar | Authenticated; year defaults to current UTC year; locked entries return only safe fields |
| View locked beer | Blocked server-side regardless of auth level for non-admins |
| All `/admin/*` routes | Role must be `"admin"` |
| Assign/unassign beer | Admin only (`PUT /admin/calendar/{id}/beer`, `DELETE /admin/calendar/{id}/beer`) |
| Edit/delete any beer | Admin only (`GET /admin/beers` read; edit/delete via admin routes) |
| Create/edit/delete users | Admin only |

---

## 10. Seed Data

Seed data is inserted at startup if the `users` table is empty (idempotent check).

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
email: bob@brobier.local, display_name: Bob, role: user, is_active: true
email: carol@brobier.local, display_name: Carol, role: user, is_active: true
email: dave@brobier.local, display_name: Dave, role: user, is_active: false
```

### Sample beer entries

At least 3 beer entries per active participant (Alice, Bob, Carol), covering a variety of ratings.

### Calendar entries

24 entries, one per day, per year:
- `year`: current UTC year for new seed runs
- `day`: 1–24
- `unlock_date`: December 1–24 of that `year` at 08:00 UTC
- `title`: e.g., "Day 1", "Day 2", …
- `content`: placeholder description text
- `image_url`: null
- `beer_entry_id`: null (admin assigns later)

The seed should assign a few beer entries to early calendar days (days 1–5) for demo purposes in the seeded year.
If prior years already exist, seeding must keep them unchanged and only insert missing rows for the target year.

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
├── docker-compose.yml
├── .env.example               ← root-level reference (not used directly)
│
├── nginx/
│   └── nginx.conf             ← reverse proxy configuration
│
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── .env.example
│   └── app/
│       ├── main.py
│       ├── core/
│       │   ├── config.py      ← Pydantic Settings
│       │   └── security.py    ← hashing, encryption helpers
│       ├── db/
│       │   ├── session.py     ← engine + get_db dependency
│       │   └── init_db.py     ← create_all + seed
│       ├── models/
│       │   ├── user.py
│       │   ├── login_code.py
│       │   ├── refresh_token.py
│       │   ├── beer_entry.py
│       │   └── calendar_entry.py
│       ├── schemas/
│       │   ├── auth.py
│       │   ├── user.py
│       │   ├── beer.py
│       │   └── calendar.py
│       ├── api/
│       │   └── routes/
│       │       ├── health.py
│       │       ├── auth.py
│       │       ├── beers.py
│       │       ├── leaderboard.py
│       │       ├── calendar.py
│       │       └── admin.py
│       ├── services/
│       │   ├── auth_service.py
│       │   ├── beer_service.py
│       │   ├── calendar_service.py
│       │   └── admin_service.py
│       ├── auth/
│       │   └── dependencies.py ← get_current_user, require_admin
│       ├── email/
│       │   └── sender.py       ← send_login_code()
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

### Start everything

```bash
docker compose up --build
```

- Application (via nginx): http://localhost
- API (via nginx proxy): http://localhost/api
- API docs (Swagger, via nginx): http://localhost/api/docs
- Mailpit web UI (direct): http://localhost:8025
- PostgreSQL (direct, dev only): localhost:5432

### First login

1. Open http://localhost:5173/login.
2. Enter `alice@brobier.local` (or any seeded user email).
3. Open http://localhost:8025 to read the login code email.
4. Enter the code in the app.

### Admin login

1. Enter `admin@brobier.local` at the login page.
2. Retrieve code from Mailpit.
3. Admin nav will appear after login.

### Reset the database

```bash
docker compose down -v
docker compose up --build
```

This drops the `postgres_data` volume and recreates/reseeds the database.

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
| Overly permissive CORS | `CORS_ORIGINS` env var explicitly lists allowed origins (only `http://localhost` in dev) |
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
