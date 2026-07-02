# Brobier Project Summary

Brobier is a private, self-hosted beer advent calendar web application. Users log in with passwordless email codes, submit beer entries, view a leaderboard, and open calendar doors that reveal daily content and optional linked beer details.

The calendar is year-based (24 doors per year), and previous years are preserved as browseable history. Admin users manage participants, review all submissions, and curate yearly calendar entries, including beer assignments.

## Core Architecture

- Backend: FastAPI (Python 3.14), SQLAlchemy, PostgreSQL
- Frontend: React 19 + TypeScript, Vite 6, React Router v7, Tailwind CSS v4
- Auth: Passwordless login code flow + server-side sessions via HTTP-only cookies
- Security: Fernet encryption for sensitive beer fields, role-based authorization, unlock-aware calendar responses
- Infra: Docker Compose stack with PostgreSQL, Mailpit, backend, frontend, and Nginx reverse proxy

## Main Functional Areas

- Authentication: request code, verify code, session lifecycle (`/auth/*`)
- Beer submissions: create, edit, delete, and list own entries
- Calendar experience: year-aware listing, day detail, and locked/unlocked content rules
- Leaderboard: ranking users by beer submission count
- Admin operations: user management, full beer visibility, calendar CRUD, beer-to-day assignment

## Delivery Focus

The implementation is organized into backend and frontend task tracks with milestone-based execution. Priority is correctness of business rules, secure handling of sensitive data, and consistent year/history behavior across API and UI.
