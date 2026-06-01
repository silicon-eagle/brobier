from __future__ import annotations

import uuid

import jwt
import pytest
from backend.auth.dependencies import get_current_user, require_admin
from backend.auth.jwt import create_access_token
from backend.core.config import get_settings
from backend.db.engine import get_engine
from backend.db.models.user import User, UserRole
from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.fixture
def active_user() -> User:
    with Session(get_engine()) as db:
        user = db.scalar(select(User).where(User.role == UserRole.user).where(User.is_active))
        assert user is not None
        return user


@pytest.fixture
def admin_user() -> User:
    with Session(get_engine()) as db:
        user = db.scalar(select(User).where(User.role == UserRole.admin).where(User.is_active))
        assert user is not None
        return user


@pytest.fixture
def inactive_user() -> User:
    with Session(get_engine()) as db:
        user = db.scalar(select(User).where(~User.is_active))
        if user is None:
            pytest.skip('No inactive user in database')
        return user


def make_request(authorization_header: str | None = None) -> Request:
    scope = {
        'type': 'http',
        'headers': [],
        'method': 'GET',
        'path': '/',
    }
    if authorization_header is not None:
        scope['headers'] = [(b'authorization', authorization_header.encode())]
    return Request(scope)


@pytest.mark.usefixtures('database')
class TestGetCurrentUser:
    def test_returns_user_with_valid_token(self, active_user: User) -> None:
        token = create_access_token(active_user.id, active_user.role)
        request = make_request(f'Bearer {token}')
        user = get_current_user(request)
        assert user.id == active_user.id
        assert user.is_active

    def test_raises_401_on_missing_authorization_header(self) -> None:
        request = make_request(None)
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)
        assert exc_info.value.status_code == 401
        assert 'Missing or invalid Authorization header' in str(exc_info.value.detail)

    def test_raises_401_on_invalid_header_format(self) -> None:
        request = make_request('InvalidFormat')
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)
        assert exc_info.value.status_code == 401
        assert 'Missing or invalid Authorization header' in str(exc_info.value.detail)

    def test_raises_401_on_missing_bearer_prefix(self) -> None:
        request = make_request('Token sometoken')
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)
        assert exc_info.value.status_code == 401
        assert 'Missing or invalid Authorization header' in str(exc_info.value.detail)

    def test_raises_401_on_invalid_token(self) -> None:
        request = make_request('Bearer invalid.token.here')
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)
        assert exc_info.value.status_code == 401

    def test_raises_401_on_tampered_token(self, active_user: User) -> None:
        token = create_access_token(active_user.id, active_user.role)
        tampered = token[:-4] + 'XXXX'
        request = make_request(f'Bearer {tampered}')
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)
        assert exc_info.value.status_code == 401

    def test_raises_401_on_missing_sub_in_token(self) -> None:
        settings = get_settings()
        payload = {'role': 'user'}
        token = jwt.encode(payload, settings.jwt_secret, algorithm='HS256')
        request = make_request(f'Bearer {token}')
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)
        assert exc_info.value.status_code == 401
        assert 'Invalid token payload' in str(exc_info.value.detail)

    def test_raises_401_on_user_not_found(self) -> None:
        fake_user_id = uuid.uuid4()
        token = create_access_token(fake_user_id, 'user')
        request = make_request(f'Bearer {token}')
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)
        assert exc_info.value.status_code == 401
        assert 'User not found or inactive' in str(exc_info.value.detail)

    def test_raises_401_on_inactive_user(self, inactive_user: User) -> None:
        token = create_access_token(inactive_user.id, inactive_user.role)
        request = make_request(f'Bearer {token}')
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request)
        assert exc_info.value.status_code == 401
        assert 'User not found or inactive' in str(exc_info.value.detail)


@pytest.mark.usefixtures('database')
class TestRequireAdmin:
    def test_returns_admin_user_when_user_is_admin(self, admin_user: User) -> None:
        result = require_admin(admin_user)
        assert result.id == admin_user.id
        assert result.role == UserRole.admin

    def test_raises_403_when_user_is_not_admin(self, active_user: User) -> None:
        with pytest.raises(HTTPException) as exc_info:
            require_admin(active_user)
        assert exc_info.value.status_code == 403
        assert 'Admin access required' in str(exc_info.value.detail)
