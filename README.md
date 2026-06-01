# brobier
Website voor de jaarlijkse brobeer advent traditie! Ik brobier maar wat...

## Auth flow
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
