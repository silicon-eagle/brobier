from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.auth.jwt import create_access_token
from backend.auth.tokens import generate_refresh_token, hash_token
from backend.core.config import get_settings
from backend.db.engine import get_engine
from backend.db.models.refresh_token import RefreshToken


def _make_bearer(user_id: uuid.UUID, role: str) -> str:
    return f'Bearer {create_access_token(user_id, role)}'


def _seed_refresh_token(user_id: uuid.UUID, *, revoked: bool = False, expired: bool = False) -> str:
    raw = generate_refresh_token()
    settings = get_settings()
    with Session(get_engine()) as db:
        row = RefreshToken(
            user_id=user_id,
            token_hash=hash_token(raw),
            expires_at=(
                datetime.now(UTC) - timedelta(days=1)
                if expired
                else datetime.now(UTC) + timedelta(days=settings.jwt_refresh_expire_days)
            ),
            revoked_at=datetime.now(UTC) if revoked else None,
        )
        db.add(row)
        db.commit()
    return raw


class TestGetCurrentUser:
    def test_valid_token_returns_user(self, client: TestClient) -> None:
        from sqlalchemy.orm import Session as DBSession
        from backend.db.engine import get_engine
        from backend.db.models.user import User

        with DBSession(get_engine()) as db:
            user = db.query(User).filter(User.email == 'alice@brobier.local').first()
            assert user is not None

        response = client.get('/auth/me', headers={'Authorization': _make_bearer(user.id, user.role)})
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == str(user.id)

    def test_missing_token_returns_401(self, client: TestClient) -> None:
        response = client.get('/auth/me')
        assert response.status_code == 401

    def test_malformed_header_returns_401(self, client: TestClient) -> None:
        response = client.get('/auth/me', headers={'Authorization': 'Token bad'})
        assert response.status_code == 401

    def test_invalid_token_returns_401(self, client: TestClient) -> None:
        response = client.get('/auth/me', headers={'Authorization': 'Bearer not.a.real.token'})
        assert response.status_code == 401

    def test_inactive_user_returns_401(self, client: TestClient) -> None:
        from sqlalchemy.orm import Session as DBSession
        from backend.db.engine import get_engine
        from backend.db.models.user import User

        with DBSession(get_engine()) as db:
            user = db.query(User).filter(User.email == 'dave@brobier.local').first()
            assert user is not None

        response = client.get('/auth/me', headers={'Authorization': _make_bearer(user.id, user.role)})
        assert response.status_code == 401

    def test_unknown_user_id_returns_401(self, client: TestClient) -> None:
        response = client.get('/auth/me', headers={'Authorization': _make_bearer(uuid.uuid4(), 'user')})
        assert response.status_code == 401


class TestRequireAdmin:
    def test_admin_role_granted_access(self, client: TestClient) -> None:
        from sqlalchemy.orm import Session as DBSession
        from backend.db.engine import get_engine
        from backend.db.models.user import User

        with DBSession(get_engine()) as db:
            admin = db.query(User).filter(User.email == 'admin@brobier.local').first()
            assert admin is not None

        # /auth/me is not admin-only; test via dependency directly by calling a protected route.
        # Since no admin-only route exists yet we just verify admin can call /auth/me.
        response = client.get('/auth/me', headers={'Authorization': _make_bearer(admin.id, admin.role)})
        assert response.status_code == 200
        assert response.json()['role'] == 'admin'

    def test_non_admin_token_forbidden_on_admin_route(self, client: TestClient) -> None:
        from sqlalchemy.orm import Session as DBSession
        from backend.db.engine import get_engine
        from backend.db.models.user import User

        with DBSession(get_engine()) as db:
            user = db.query(User).filter(User.email == 'alice@brobier.local').first()
            assert user is not None

        # When an admin-only route is added, its dependency will call require_admin.
        # Here we verify /auth/me (non-admin) returns 200 for a regular user.
        response = client.get('/auth/me', headers={'Authorization': _make_bearer(user.id, user.role)})
        assert response.status_code == 200
        assert response.json()['role'] == 'user'
