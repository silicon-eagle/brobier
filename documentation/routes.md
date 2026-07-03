# Brobier — API Routes Reference

In development the FastAPI backend runs on the host and is reachable directly at
`http://localhost:8000`. Routes below use paths relative to that base and do **not**
include an `/api` prefix.

---

## Health

| Status | Method | Path | Auth | Summary |
|--------|--------|------|------|---------|
| ✅ | `GET` | `/health` | 🔓 | Returns `{ "status": "ok" }` |
| ✅ | `GET` | `/healthz` | 🔓 | Alias of `/health` |

---

## Auth — `/auth`

| Status | Method | Path | Auth | Summary | Request body | Success response |
|--------|--------|------|------|---------|--------------|-----------------|
| ✅ | `POST` | `/auth/request-code` | 🔓 | Generate and email a login code | `{ email }` | `200 { message }` |
| ✅ | `POST` | `/auth/verify-code` | 🔓 | Verify code → issue access token + set refresh cookie | `{ email, code }` | `200 { access_token, token_type, user }` |
| ✅ | `POST` | `/auth/refresh` | 🍪 | Rotate refresh cookie → new access token (+ new refresh cookie) | — | `200 { access_token, token_type }` |
| ✅ | `POST` | `/auth/logout` | 🍪 | Revoke refresh token, clear cookie | — | `200 { message }` |
| ✅ | `GET` | `/auth/me` | 🔑 | Return current user | — | `200 UserOut { id, display_name, role }` |

> `POST /auth/refresh` **rotates** the refresh token: it revokes the presented token and sets a brand-new `brobier_refresh` cookie alongside the new access token.

### Error responses (auth)

| Endpoint | Code | Detail |
|----------|------|--------|
| `POST /auth/verify-code` | `401` | `"Invalid or expired code."` |
| `POST /auth/refresh` | `401` | Token absent, invalid, revoked, or expired |
| `POST /auth/logout` | `401` | Token absent or invalid |
| `GET /auth/me` | `401` | JWT absent, invalid, or expired |

---

## Beers — `/beers`

All require `🔑 JWT`.

| Status | Method | Path | Summary | Request body | Success response |
|--------|--------|------|---------|--------------|-----------------|
| ✅ | `GET` | `/beers/me` | Current user's beer entries (decrypted) | — | `200 [ BeerEntryOut ]` |
| ✅ | `POST` | `/beers` | Create a new beer entry | `BeerEntryCreate` | `201 BeerEntryOut` |
| ✅ | `PUT` | `/beers/{beer_id}` | Update own beer entry | `BeerEntryUpdate` (all fields optional) | `200 BeerEntryOut` |
| ✅ | `DELETE` | `/beers/{beer_id}` | Delete own beer entry | — | `204 No Content` |

Ownership is enforced inside the service layer: update and delete queries filter by
`user_id`, so another user's beer is simply reported as not found (`404`).

### `BeerEntryCreate` fields
`year`, `beer_name`, `brewery`, `untappd_url?`, `comment?`, `bought_from`, `bought_at`

### `BeerEntryOut` fields
`id`, `user_id`, `year`, `beer_name`, `brewery`, `untappd_url`, `comment`, `bought_from`, `bought_at`, `created_at`, `updated_at`

### Error responses (beers)

| Endpoint | Code | Detail |
|----------|------|--------|
| `PUT /beers/{id}` | `404` | `"Beer not found."` (missing or not owned) |
| `DELETE /beers/{id}` | `404` | `"Beer not found."` (missing or not owned) |
| `DELETE /beers/{id}` | `409` | `"Cannot delete beer assigned to a calendar day."` |
| `DELETE /beers/{id}` | `409` | `"Cannot delete beer with existing rating."` |

---

## Ratings — `/beers/{beer_id}/ratings`

All require `🔑 JWT`.

| Status | Method | Path | Summary | Request body | Success response |
|--------|--------|------|---------|--------------|-----------------|
| ✅ | `POST` | `/beers/{beer_id}/ratings` | Submit a rating for a beer | `UserRatingCreate` | `201 UserRatingOut` |
| ✅ | `PUT` | `/beers/{beer_id}/ratings/me` | Update current user's rating | `UserRatingUpdate` (all fields optional) | `200 UserRatingOut` |
| ✅ | `DELETE` | `/beers/{beer_id}/ratings/me` | Delete current user's rating | — | `204 No Content` |

### `UserRatingCreate` fields
`rating` (1.0–5.0), `comment?`, `drank_at?`

### `UserRatingOut` fields
`id`, `user_id`, `beer_entry_id`, `rating`, `comment`, `drank_at`, `created_at`, `updated_at`

### Error responses (ratings)

| Endpoint | Code | Detail |
|----------|------|--------|
| `POST /beers/{beer_id}/ratings` | `404` | `"Beer not found."` |
| `POST /beers/{beer_id}/ratings` | `409` | `"Rating already exists."` |
| `PUT /beers/{beer_id}/ratings/me` | `404` | `"Rating not found."` |
| `DELETE /beers/{beer_id}/ratings/me` | `404` | `"Rating not found."` |

---

## Leaderboard — `/leaderboard`

| Status | Method | Path | Auth | Summary | Query params | Success response |
|--------|--------|------|------|---------|--------------|-----------------|
| ✅ | `GET` | `/leaderboard` | 🔑 | Non-admin users ranked by beer count for a year | `year?` (defaults to current year) | `200 [ { display_name, beer_count } ]` |

Admin users are excluded. Users with zero beers for the year are still listed with `beer_count = 0`.

---

## Calendar — `/calendar`

All require `🔑 JWT`.

`GET /calendar` returns all entries for a year using the unlock-aware locked/unlocked schema (locked entries omit `title`, `content`, `image_url`, and `beer`).

`GET /calendar/{year}/{day}` is **day-gated**: if `unlock_date > now`, the endpoint returns `403` outright — it does **not** return the locked schema. This prevents clients from probing individual days to infer beer information before the door is meant to open.

| Status | Method | Path | Auth | Summary | Query params | Success response |
|--------|--------|------|------|---------|--------------|-----------------|
| ✅ | `GET` | `/calendar/years` | 🔑 | List available years (ascending) | — | `200 [ { year } ]` |
| ✅ | `GET` | `/calendar` | 🔑 | List all entries for a year (locked/unlocked schema) | `year?` (defaults to current year) | `200 [ CalendarEntryOut ]` |
| ✅ | `GET` | `/calendar/{year}/{day}` | 🔑 | Single unlocked entry only — blocked if still locked | — | `200 CalendarEntryOut` |

> **Note:** `/calendar/years` is registered **before** `/calendar/{year}/{day}` in the router so `years` is never matched as a year value.

### `CalendarEntryOut` — locked state
`id`, `year`, `day`, `unlock_date`, `is_locked: true` (`title`, `content`, `image_url`, `beer` are `null`)

### `CalendarEntryOut` — unlocked state
`id`, `year`, `day`, `unlock_date`, `title`, `content`, `image_url`, `is_locked: false`,
`beer?: { id, beer_name, brewery, untappd_url, comment, bought_from, submitted_by, ratings: [UserRatingOut] }`

### Error responses (calendar)

| Endpoint | Code | Detail |
|----------|------|--------|
| `GET /calendar/{year}/{day}` | `403` | `"This day is not yet unlocked."` (`unlock_date > now`) |
| `GET /calendar/{year}/{day}` | `404` | `"Calendar day not found."` |

---

## Admin — `/admin`

All require `🛡️ JWT with role = admin`.

### Users — `/admin/users`

| Status | Method | Path | Summary | Request body | Success response |
|--------|--------|------|---------|--------------|-----------------|
| ✅ | `GET` | `/admin/users` | List all users | — | `200 [ AdminUserOut ]` |
| ✅ | `POST` | `/admin/users` | Create a new user | `UserCreate` | `201 AdminUserOut` |
| ✅ | `PUT` | `/admin/users/{user_id}` | Update user fields | `UserUpdate` (all fields optional) | `200 AdminUserOut` |
| ✅ | `POST` | `/admin/users/{user_id}/activate` | Set `is_active = true` | — | `200 AdminUserOut` |
| ✅ | `POST` | `/admin/users/{user_id}/deactivate` | Set `is_active = false` | — | `200 AdminUserOut` |

#### `UserCreate` fields
`email`, `display_name`, `role?` (default `user`), `is_active?` (default `true`)

#### `UserUpdate` fields
`display_name?`, `role?`, `is_active?`

#### `AdminUserOut` fields
`id`, `email`, `display_name`, `role`, `is_active`, `created_at`, `updated_at`

#### Error responses (admin users)

| Endpoint | Code | Detail |
|----------|------|--------|
| `POST /admin/users` | `409` | `"User with this email already exists."` |
| `PUT /admin/users/{user_id}` | `404` | `"User not found."` |
| `POST /admin/users/{user_id}/activate` | `404` | `"User not found."` |
| `POST /admin/users/{user_id}/deactivate` | `404` | `"User not found."` |

### Beers — `/admin/beers`

| Status | Method | Path | Summary | Query params | Success response |
|--------|--------|------|---------|--------------|-----------------|
| ✅ | `GET` | `/admin/beers` | All beer entries (decrypted) with owner info | `year?` | `200 [ AdminBeerEntryOut ]` |

#### `AdminBeerEntryOut` fields
`id`, `user_id`, `display_name` (owner), `year`, `beer_name`, `brewery`, `untappd_url`, `comment`, `bought_from`, `bought_at`, `created_at`, `updated_at`

### Calendar — `/admin/calendar`

The admin calendar is managed **per year and per day**. There is no per-entry create/update/delete endpoint: creating a year generates all 24 days, and editing a day's title/content is not currently exposed over the API.

| Status | Method | Path | Summary | Request body | Success response |
|--------|--------|------|---------|--------------|-----------------|
| ✅ | `GET` | `/admin/calendar` | All entries for a year (full content, unlock ignored) | `year?` (defaults to current year) | `200 [ AdminCalendarEntryOut ]` |
| ✅ | `PUT` | `/admin/calendar/{year}` | Create the 24 calendar days for a year (skips existing days) | — | `204 No Content` |
| ✅ | `DELETE` | `/admin/calendar/{year}` | Delete all days for a year | — | `204 No Content` |
| ✅ | `PUT` | `/admin/calendar/{year}/{day}/beer` | Assign a beer to this calendar day | `{ beer_entry_id }` | `200 AdminCalendarEntryOut` |
| ✅ | `DELETE` | `/admin/calendar/{year}/{day}/beer` | Unassign beer from this calendar day | — | `200 AdminCalendarEntryOut` |

#### `AdminCalendarEntryOut` fields
`year`, `day`, `unlock_date`, `title`, `content`, `image_url`, `beer_entry_id`,
`beer?: { id, user_id, display_name, beer_name, brewery, untappd_url, comment, bought_from, bought_at, ratings: [UserRatingOut] }`

#### Error responses (admin calendar)

| Endpoint | Code | Detail |
|----------|------|--------|
| `DELETE /admin/calendar/{year}` | `409` | `"Cannot delete calendar year because at least one day has an assigned beer."` |
| `PUT /admin/calendar/{year}/{day}/beer` | `404` | `"Calendar entry not found."` |
| `PUT /admin/calendar/{year}/{day}/beer` | `404` | `"Beer entry not found."` |
| `PUT /admin/calendar/{year}/{day}/beer` | `409` | `"Beer entry belongs to a different calendar year."` |
| `PUT /admin/calendar/{year}/{day}/beer` | `409` | `"Beer entry is already assigned to a calendar day."` |
| `DELETE /admin/calendar/{year}/{day}/beer` | `404` | `"Calendar entry not found."` |

---

## Summary — counts by status

All routes are implemented.

| Status | Count |
|--------|-------|
| ✅ Implemented | 24 |
| ❌ Not implemented | 0 |
| **Total** | **24** |

---

## FastAPI Dependencies

Defined in `backend/brobier/auth/dependencies.py`.

### `get_current_user(request: Request) -> User` ✅
Reads the `Authorization: Bearer <token>` header, decodes and verifies the JWT, loads the matching active `User` from the database, and returns it.

| Condition | Response |
|-----------|----------|
| Header absent or not `Bearer …` | `401 Missing or invalid Authorization header.` |
| JWT malformed or expired | `401 JWT token is invalid` / `401 JWT token has expired` |
| JWT has no `sub` claim | `401 Invalid token payload.` |
| User not found or `is_active = false` | `401 User not found or inactive.` |

**Used on:** all `🔑` routes (registered on the `/beers` and `/calendar` routers).

---

### `require_admin(current_user = Depends(get_current_user)) -> User` ✅
Wraps `get_current_user` and additionally enforces `role == "admin"`.

| Condition | Response |
|-----------|----------|
| Not authenticated | delegates to `get_current_user` → `401` |
| Authenticated but `role != "admin"` | `403 Admin access required.` |

**Used on:** all `🛡️` routes (every `/admin/*` router).

---

### `get_refresh_token_raw(request: Request) -> str` ✅
Reads the raw value of the `brobier_refresh` HTTP-only cookie from the request.

| Condition | Response |
|-----------|----------|
| Cookie absent | `401 Refresh token missing.` |

**Used on:** `POST /auth/refresh`, `POST /auth/logout`.

---

> **Ownership & assignment checks** are enforced inside the service layer, not as
> FastAPI dependencies. Beer update/delete queries filter by `user_id`, and the
> beers service blocks deleting a beer that is assigned to a calendar day or that
> already has a rating.

## Router Structure

Defined in `backend/brobier/api/routes/`. Each module creates an `APIRouter` and is included in `main.py`.

```
backend/brobier/
└── api/
    └── routes/
        ├── __init__.py
        ├── auth.py          # /auth/*
        ├── beers.py         # /beers/* and /beers/{id}/ratings/*
        ├── calendar.py      # /calendar/*
        ├── leaderboard.py   # /leaderboard
        └── admin/
            ├── __init__.py
            ├── users.py     # /admin/users/*
            ├── beers.py     # /admin/beers
            └── calendar.py  # /admin/calendar/*
```

### Registration in `main.py`

```python
app.include_router(auth.router,           prefix='/auth')
app.include_router(leaderboard.router,    prefix='/leaderboard')
app.include_router(beers.router,          prefix='/beers',         dependencies=[Depends(get_current_user)])
app.include_router(calendar.router,       prefix='/calendar',      dependencies=[Depends(get_current_user)])
app.include_router(admin_users.router,    prefix='/admin/users',   dependencies=[Depends(require_admin)])
app.include_router(admin_beers.router,    prefix='/admin/beers',   dependencies=[Depends(require_admin)])
app.include_router(admin_calendar.router, prefix='/admin/calendar', dependencies=[Depends(require_admin)])
```

> Note: the `/leaderboard` router is currently registered **without** a router-level
> auth dependency, unlike `/beers` and `/calendar`.

> `POST /auth/refresh` and `POST /auth/logout` handle cookie auth inside the route handler via `get_refresh_token_raw` — they are **not** covered by the router-level `get_current_user` dependency.

### Route ordering within `calendar.py`

```python
router.get('/years')          # must be first — avoids "years" matching {year}
router.get('')                # list for a year
router.get('/{year}/{day}')   # single day
```
