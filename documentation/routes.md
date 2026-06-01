# Brobier — API Routes Reference

All routes are served under the nginx reverse proxy at `http://localhost` (dev).
Backend routes are proxied from `/api/*` by default (adjust if nginx config differs).

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Implemented |
| ❌ | Not yet implemented |
| 🔓 | No authentication required |
| 🔑 | Requires valid JWT (`Authorization: Bearer <token>`) |
| 🛡️ | Requires JWT with `role = admin` |
| 🍪 | Requires valid `brobier_refresh` HTTP-only cookie |

---

## Health

| Status | Method | Path | Auth | Summary |
|--------|--------|------|------|---------|
| ✅ | `GET` | `/health` | 🔓 | Returns `{ "status": "ok" }` |

---

## Auth — `/auth`

| Status | Method | Path | Auth | Summary | Request body | Success response |
|--------|--------|------|------|---------|--------------|-----------------|
| ❌ | `POST` | `/auth/request-code` | 🔓 | Generate and email a login code | `{ email }` | `200 { message }` |
| ❌ | `POST` | `/auth/verify-code` | 🔓 | Verify code → issue access token + set refresh cookie | `{ email, code }` | `200 { access_token, token_type, user }` |
| ❌ | `POST` | `/auth/refresh` | 🍪 | Exchange refresh cookie for a new access token | — | `200 { access_token, token_type }` |
| ❌ | `POST` | `/auth/logout` | 🍪 | Revoke refresh token, clear cookie | — | `200 { message }` |
| ❌ | `GET` | `/auth/me` | 🔑 | Return current user | — | `200 UserOut` |

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
| ❌ | `GET` | `/beers/me` | Current user's beer entries (decrypted) | — | `200 [ BeerEntryOut ]` |
| ❌ | `POST` | `/beers` | Create a new beer entry | `BeerEntryCreate` | `201 BeerEntryOut` |
| ❌ | `PUT` | `/beers/{beer_id}` | Update own beer entry | `BeerEntryUpdate` (all fields optional) | `200 BeerEntryOut` |
| ❌ | `DELETE` | `/beers/{beer_id}` | Delete own beer entry | — | `204 No Content` |

### `BeerEntryCreate` fields
`beer_name`, `brewery`, `untappd_url?`, `comment?`, `bought_from`, `bought_at`

### `BeerEntryOut` fields
`id`, `user_id`, `beer_name`, `brewery`, `untappd_url`, `comment`, `bought_from`, `bought_at`, `created_at`, `updated_at`

### Error responses (beers)

| Endpoint | Code | Detail |
|----------|------|--------|
| `PUT /beers/{id}` | `403` | Not the owner |
| `PUT /beers/{id}` | `409` | Beer is assigned to a calendar entry |
| `DELETE /beers/{id}` | `403` | Not the owner |
| `DELETE /beers/{id}` | `409` | Beer is assigned to a calendar entry |

---

## Ratings — `/beers/{beer_id}/ratings`

All require `🔑 JWT`.

| Status | Method | Path | Summary | Request body | Success response |
|--------|--------|------|---------|--------------|-----------------|
| ❌ | `POST` | `/beers/{beer_id}/ratings` | Submit a rating for a beer | `UserRatingCreate` | `201 UserRatingOut` |
| ❌ | `PUT` | `/beers/{beer_id}/ratings/me` | Update current user's rating | `UserRatingUpdate` (all fields optional) | `200 UserRatingOut` |
| ❌ | `DELETE` | `/beers/{beer_id}/ratings/me` | Delete current user's rating | — | `204 No Content` |

### `UserRatingCreate` fields
`rating` (1.0–5.0), `comment?`, `drank_at?`

### `UserRatingOut` fields
`id`, `user_id`, `beer_entry_id`, `rating`, `comment`, `drank_at`, `created_at`, `updated_at`

### Error responses (ratings)

| Endpoint | Code | Detail |
|----------|------|--------|
| `POST /beers/{beer_id}/ratings` | `404` | Beer entry not found |
| `POST /beers/{beer_id}/ratings` | `409` | User has already rated this beer |
| `PUT /beers/{beer_id}/ratings/me` | `404` | Beer not found, or user has no rating yet |
| `DELETE /beers/{beer_id}/ratings/me` | `404` | Beer not found, or user has no rating yet |

---

## Leaderboard — `/leaderboard`

| Status | Method | Path | Auth | Summary | Success response |
|--------|--------|------|------|---------|-----------------|
| ❌ | `GET` | `/leaderboard` | 🔑 | Active users ranked by beer count | `200 [ { display_name, beer_count } ]` |

---

## Calendar — `/calendar`

All require `🔑 JWT`.

`GET /calendar` returns all 24 entries using the unlock-aware locked/unlocked schema (locked entries omit `content`, `image_url`, and `beer`).

`GET /calendar/{day}` is **day-gated**: if `unlock_date > now`, the endpoint returns `403` outright — it does **not** return the locked schema. This prevents clients from probing individual days to infer beer information before the door is meant to open.

| Status | Method | Path | Auth | Summary | Query params | Success response |
|--------|--------|------|------|---------|--------------|-----------------|
| ❌ | `GET` | `/calendar` | 🔑 | List all 24 entries for a year (locked/unlocked schema) | `year?` (defaults to current UTC year) | `200 [ CalendarEntryOut ]` |
| ❌ | `GET` | `/calendar/years` | 🔑 | List available years (descending) | — | `200 [ { year } ]` |
| ❌ | `GET` | `/calendar/{day}` | 🔑 | Single unlocked entry only — blocked if still locked | `year` (**required**) | `200 CalendarEntryOut` |

> **Note:** `/calendar/years` must be registered **before** `/calendar/{day}` in the router to avoid `years` being matched as a day value.

### `CalendarEntryOut` — locked state (list only)
`id`, `year`, `day`, `unlock_date`, `title`, `is_locked: true`

### `CalendarEntryOut` — unlocked state
`id`, `year`, `day`, `unlock_date`, `title`, `content`, `image_url`, `is_locked: false`,
`beer?: { id, beer_name, brewery, untappd_url, comment, bought_from, submitted_by, ratings: [UserRatingOut] }`

### Error responses (calendar)

| Endpoint | Code | Detail |
|----------|------|--------|
| `GET /calendar/{day}` | `422` | `year` query parameter is missing |
| `GET /calendar/{day}` | `403` | Entry exists but `unlock_date > now` (door not yet open) |
| `GET /calendar/{day}` | `404` | Day/year combination not found |

---

## Admin — `/admin`

All require `🛡️ JWT with role = admin`.

### Users

| Status | Method | Path | Summary | Request body | Success response |
|--------|--------|------|---------|--------------|-----------------|
| ❌ | `GET` | `/admin/users` | List all users | — | `200 [ UserOut ]` |
| ❌ | `POST` | `/admin/users` | Create a new user | `UserCreate` | `201 UserOut` |
| ❌ | `PUT` | `/admin/users/{user_id}` | Update user fields | `UserUpdate` (all fields optional) | `200 UserOut` |
| ❌ | `POST` | `/admin/users/{user_id}/activate` | Set `is_active = true` | — | `200 UserOut` |
| ❌ | `POST` | `/admin/users/{user_id}/deactivate` | Set `is_active = false` | — | `200 UserOut` |

#### `UserCreate` fields
`email`, `display_name`, `role?`, `is_active?`

#### `UserOut` fields
`id`, `email`, `display_name`, `role`, `is_active`, `created_at`, `updated_at`

#### Error responses (admin users)

| Endpoint | Code | Detail |
|----------|------|--------|
| `POST /admin/users` | `409` | Email already exists |

### Beers

| Status | Method | Path | Summary | Success response |
|--------|--------|------|---------|-----------------|
| ❌ | `GET` | `/admin/beers` | All beer entries (decrypted) with owner info | `200 [ AdminBeerEntryOut ]` |

#### `AdminBeerEntryOut` fields
`id`, `user_id`, `display_name` (owner), `beer_name`, `brewery`, `untappd_url`, `comment`, `bought_from`, `bought_at`, `created_at`, `updated_at`

### Calendar

| Status | Method | Path | Summary | Request body / Query params | Success response |
|--------|--------|------|---------|----------------------------|-----------------|
| ❌ | `GET` | `/admin/calendar` | All 24 entries (full content, unlock ignored) | `year?` (defaults to current UTC year) | `200 [ AdminCalendarEntryOut ]` |
| ❌ | `POST` | `/admin/calendar` | Create a calendar entry | `CalendarEntryCreate` | `201 AdminCalendarEntryOut` |
| ❌ | `PUT` | `/admin/calendar/{entry_id}` | Update calendar entry (not beer assignment) | `CalendarEntryUpdate` (all fields optional) | `200 AdminCalendarEntryOut` |
| ❌ | `DELETE` | `/admin/calendar/{entry_id}` | Delete calendar entry (beer entry unaffected) | — | `204 No Content` |
| ❌ | `PUT` | `/admin/calendar/{entry_id}/beer` | Assign a beer to this calendar day | `{ beer_entry_id }` | `200 AdminCalendarEntryOut` |
| ❌ | `DELETE` | `/admin/calendar/{entry_id}/beer` | Unassign beer from this calendar day | — | `200 AdminCalendarEntryOut` |

#### `CalendarEntryCreate` fields
`year`, `day`, `unlock_date`, `title`, `content`, `image_url?`

#### `AdminCalendarEntryOut` fields
`id`, `year`, `day`, `unlock_date`, `title`, `content`, `image_url`, `beer_entry_id`,
`beer?: { id, user_id, display_name, beer_name, brewery, untappd_url, comment, bought_from, bought_at, ratings: [UserRatingOut] }`

#### Error responses (admin calendar)

| Endpoint | Code | Detail |
|----------|------|--------|
| `POST /admin/calendar` | `409` | Day already exists for that year |
| `PUT /admin/calendar/{entry_id}/beer` | `404` | Beer entry not found |
| `PUT /admin/calendar/{entry_id}/beer` | `409` | Beer already assigned to another day |

---

## Summary — counts by status

| Status | Count |
|--------|-------|
| ✅ Implemented | 1 (`GET /health`) |
| ❌ Not implemented | 27 |
| **Total** | **28** |

---

## FastAPI Dependencies

Defined in `backend/auth/dependencies.py`.

### `get_current_user(request: Request) -> User` ✅
Reads the `Authorization: Bearer <token>` header, decodes and verifies the JWT, loads the matching active `User` from the database, and returns it.

| Condition | Response |
|-----------|----------|
| Header absent or not `Bearer …` | `401 Missing or invalid Authorization header.` |
| JWT malformed or expired | `401 <jwt error message>` |
| JWT has no `sub` claim | `401 Invalid token payload.` |
| User not found or `is_active = false` | `401 User not found or inactive.` |

**Used on:** all `🔑` routes.

---

### `require_admin(current_user = Depends(get_current_user)) -> User` ✅
Wraps `get_current_user` and additionally enforces `role == "admin"`.

| Condition | Response |
|-----------|----------|
| Not authenticated | delegates to `get_current_user` → `401` |
| Authenticated but `role != "admin"` | `403 Admin access required.` |

**Used on:** all `🛡️` routes (every `/admin/*` endpoint).

---

### `get_refresh_token_raw(request: Request) -> str` ❌
Reads the raw value of the `brobier_refresh` HTTP-only cookie from the request.

| Condition | Response |
|-----------|----------|
| Cookie absent | `401 Refresh token missing.` |

**Used on:** `POST /auth/refresh`, `POST /auth/logout`.

---

### `require_owns_beer(beer_id, current_user) -> BeerEntry` ❌
Loads the `BeerEntry` by `beer_id` and asserts `beer.user_id == current_user.id`.

| Condition | Response |
|-----------|----------|
| Beer not found | `404 Beer entry not found.` |
| User does not own the beer | `403 Not the owner.` |

**Used on:** `PUT /beers/{beer_id}`, `DELETE /beers/{beer_id}`.

---

### `require_beer_not_assigned(beer: BeerEntry) -> BeerEntry` ❌
Asserts the beer entry is not currently linked to any `CalendarEntry`.

| Condition | Response |
|-----------|----------|
| Beer is assigned to a calendar entry | `409 Beer is assigned to a calendar entry.` |

**Used on:** `PUT /beers/{beer_id}`, `DELETE /beers/{beer_id}` (chained after `require_owns_beer`).

---

## Router Structure

Defined in `backend/api/routes/`. Each module creates an `APIRouter` and is included in `main.py`.

```
backend/
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
app.include_router(auth_router,        prefix="/auth")
app.include_router(beers_router,       prefix="/beers",       dependencies=[Depends(get_current_user)])
app.include_router(calendar_router,    prefix="/calendar",    dependencies=[Depends(get_current_user)])
app.include_router(leaderboard_router, prefix="/leaderboard", dependencies=[Depends(get_current_user)])
app.include_router(admin_router,       prefix="/admin",       dependencies=[Depends(require_admin)])
```

> `POST /auth/refresh` and `POST /auth/logout` handle cookie auth inside the route handler via `get_refresh_token_raw` — they are **not** covered by the router-level `get_current_user` dependency.

### Route ordering within `calendar.py`

```python
router.get("/years")   # must be first — avoids "years" matching {day}
router.get("/{day}")
router.get("/")
```
