# brobier
Website voor de jaarlijkse brobeer advent traditie! Ik brobier maar wat...

## Get Started

The repository ships a `docker-compose.yml` that runs the full local stack, including the **FastAPI backend**. You can either run everything in containers (handy when working on the frontend) or run the infrastructure in Docker and the backend on the host with `uv` for a faster edit/debug loop.

### Prerequisites

- Docker + Docker Compose v2
- Python 3.13 and [`uv`](https://docs.astral.sh/uv/) (for running the backend)

### 1. Configure environment

Copy the example env file and fill in the blanks:

```bash
cp .env.example .env
```

Set at least `POSTGRES_ADMIN_PASSWORD`, `POSTGRES_APP_PASSWORD`, `JWT_SECRET`, and `BEER_ENCRYPTION_KEY`. Generate a Fernet key with:

```bash
cd backend && uv run brobier generate-key
```

### 2. Start the stack

```bash
docker compose up -d
```

This starts four services:

| Service | Image | Purpose | Ports (host) |
|---|---|---|---|
| `proxy` | `nginx:alpine` | Reverse proxy entry point (`nginx/nginx.conf`) | `80` |
| `backend` | built from `backend/Dockerfile` | FastAPI application (JSON API) | `8000` |
| `db-dev` | `postgres:18-alpine` | PostgreSQL database (dev) | `5432` |
| `mailpit` | `axllent/mailpit` | Local SMTP catch-all + web UI for login-code emails | `1025` (SMTP), `8025` (web) |

The `backend` service reads the same `.env` file, but overrides `DB_HOST` and `SMTP_HOST` to the Docker network service names (`db-dev`, `mailpit`) so it can reach the other containers. Its source (`backend/brobier`) is mounted for live reload, and it waits for the database to be healthy before starting.

On first boot, `postgres/init/01-create-app-role.sh` creates a least-privilege application role (`POSTGRES_APP_USER`) that the backend connects with. The admin role is used only for creating tables. Database data persists in the `db-dev-data` volume; Mailpit persists to `./data`.

The API is available at `http://localhost:8000` (health check: `GET /health`). Sent login-code emails appear in the Mailpit web UI at `http://localhost:8025`.

### 3. Run the backend on the host (optional)

If you prefer to run the backend directly on your machine (e.g. for debugging), skip the `backend` container and run it with `uv` instead:

```bash
docker compose up -d db-dev mailpit proxy   # infrastructure only
cd backend
uv sync
uv run brobier serve --reload
```

On startup the backend creates any missing tables (using the admin role) and seeds calendar entries.

### Running tests

```bash
cd backend && uv run pytest
```

## Backend

The backend is a **FastAPI** application (Python 3.13) that serves the JSON API. It follows a thin-routes / service-layer split: route handlers validate input and shape responses, while all business rules live in the `services/` modules.

### Layout

```
backend/brobier/
├── main.py          # FastAPI app, router registration, lifespan (init + seed)
├── cli.py           # `brobier serve` and `brobier generate-key`
├── api/routes/      # HTTP routes (auth, beers, calendar, leaderboard, admin/*)
├── services/        # business logic (auth, beers, calendar, leaderboard, users, email)
├── schemas/         # Pydantic request/response models
├── db/              # SQLAlchemy engine, models, table init
├── auth/            # JWT, token hashing, FastAPI auth dependencies
└── core/            # config, security (encryption), time, typed errors
```

### What happens in the backend

- **Passwordless auth.** Users request a 6-digit login code by email; the code is SHA-256 hashed and stored with a short expiry. On verification the backend issues a short-lived **JWT access token** (signed HS256, carries `sub` + `role`) and a **refresh token** whose SHA-256 hash is stored in the DB while the raw value is set as an `HttpOnly` cookie scoped to `/auth`. Wrong-code attempts are counted and lock the user's codes after `LOGIN_MAX_ATTEMPTS`.
- **Authorization.** `get_current_user` decodes the `Authorization: Bearer` token and loads the active user; `require_admin` additionally enforces `role == admin`. Routers are protected at registration time via these dependencies.
- **Encryption at rest.** Beer name, brewery, Untappd URL, and comment are encrypted with **Fernet** (`BEER_ENCRYPTION_KEY`) before being written, and decrypted only in the service layer when returned. Encrypted columns never leave the database in plaintext.
- **Year-aware advent calendar.** Beers and calendar days both carry a `year`. `GET /calendar` returns all 24 days for a year using a locked/unlocked schema — locked days omit content and beer details, and `GET /calendar/{year}/{day}` returns `403` until the day's `unlock_date` passes, preventing clients from probing unopened doors. Admins create/delete whole calendar years and assign a beer (unique per day, same year) to each door.
- **Two database roles.** The app connects with a least-privilege role for normal queries (`get_app_engine`), while table creation uses an admin role (`get_admin_engine`). On startup `init_db` creates missing tables and `seed_database` seeds users and calendar entries. Set `DB_OVERWRITE=true` (dev/test only) to drop and recreate all tables.
- **Consistent errors.** Services raise typed `AppError` subclasses (`NotFoundError` → 404, `ConflictError` → 409, `ForbiddenError` → 403, `UnauthorizedError` → 401); a single exception handler maps them to JSON responses.
- **Email.** Login-code emails are rendered from Jinja templates and sent over SMTP (Mailpit in development).

See [documentation/spec.md](documentation/spec.md) for the full specification and [documentation/routes.md](documentation/routes.md) for the API reference.

### Auth flow
```text
1. POST /auth/request-code   ← email sent
2. POST /auth/verify-code    ← refresh token (cookie, 7d) + access token (15min)

   [normal usage]
3. POST /auth/refresh        ← swap refresh cookie → new access token
   (repeat every 15min)

4. refresh token expires / is revoked (logout)
   ↓
   back to step 1
```

```text
User               Frontend                        Backend                    DB / Mail
 |                    |                               |                           |
 | enter email        |                               |                           |
 |------------------->|                               |                           |
 |                    | POST /auth/request-code       |                           |
 |                    |------------------------------>| find active user          |
 |                    |                               |-------------------------->|
 |                    |                               | store hashed login code   |
 |                    |                               |-------------------------->|
 |                    |                               | send login code email     |
 |                    |                               |-------------------------> |
 |                    | 200 generic success           |                           |
 |                    |<------------------------------|                           |
 |                    |                               |                           |
 | enter email + code |                               |                           |
 |------------------->|                               |                           |
 |                    | POST /auth/verify-code        |                           |
 |                    |------------------------------>| validate code             |
 |                    |                               |-------------------------->|
 |                    |                               | mark code as used         |
 |                    |                               |-------------------------->|
 |                    |                               | store hashed refresh token|
 |                    |                               |-------------------------->|
 |                    | access_token + user           |                           |
 |                    |<------------------------------|                           |
 |                    | Set-Cookie: refresh=...       |                           |
 |                    |<------------------------------|                           |
 |                    |                               |                           |
 |                    | store access JWT in memory    |                           |
 |                    |-------------------------------x                           |
 |                    |                               |                           |
 |                    | Authorization: Bearer access  |                           |
 |                    |------------------------------>| verify JWT                |
 |                    |                               |                           |
 |                    | protected response            |                           |
 |                    |<------------------------------|                           |
 |                    |                               |                           |
 |                    | access expired?               |                           |
 |                    |------------- yes ------------>|                           |
 |                    | POST /auth/refresh            | refresh cookie auto-sent  |
 |                    |------------------------------>| validate refresh token    |
 |                    |                               |-------------------------->|
 |                    | new access_token              |                           |
 |                    |<------------------------------|                           |
 |                    | replace in-memory access JWT  |                           |
 |                    |-------------------------------x                           |
 |                    | retry protected request       |                           |
 |                    |------------------------------>|                           |
 |                    | protected response            |                           |
 |                    |<------------------------------|                           |
 |                    |                               |                           |
 | click logout       |                               |                           |
 |------------------->|                               |                           |
 |                    | POST /auth/logout             | refresh cookie auto-sent  |
 |                    |------------------------------>| revoke refresh token      |
 |                    |                               |-------------------------->|
 |                    | clear refresh cookie          |                           |
 |                    |<------------------------------|                           |
```