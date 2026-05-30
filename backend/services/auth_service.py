from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth.jwt import create_access_token
from backend.auth.tokens import generate_login_code, generate_refresh_token, hash_token
from backend.core.config import get_settings
from backend.db.engine import get_engine
from backend.db.models.login_code import LoginCode
from backend.db.models.refresh_token import RefreshToken
from backend.db.models.user import User
from backend.services.sender import send_login_code_email


def request_code(email: str) -> None:
    with Session(get_engine()) as db:
        user = db.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
        if not user:
            return

        settings = get_settings()
        code = generate_login_code()
        db.add(LoginCode(
            user_id=user.id,
            code_hash=hash_token(code),
            expires_at=datetime.now(UTC) + timedelta(minutes=settings.login_code_expire_minutes),
        ))
        db.commit()
    send_login_code_email(email, code)


def verify_code(email: str, code: str) -> tuple[str, str, User]:
    with Session(get_engine()) as db:
        user = db.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
        if not user:
            raise ValueError('Invalid or expired code.')

        login_code = (
            db.query(LoginCode)
            .filter(
                LoginCode.user_id == user.id,
                LoginCode.code_hash == hash_token(code),
                LoginCode.used_at.is_(None),
                LoginCode.expires_at > datetime.now(UTC),
            )
            .first()
        )
        if not login_code:
            raise ValueError('Invalid or expired code.')

        login_code.used_at = datetime.now(UTC)

        settings = get_settings()
        raw_token = generate_refresh_token()
        db.add(RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.now(UTC) + timedelta(days=settings.jwt_refresh_expire_days),
        ))
        db.commit()
        db.refresh(user)

    access_token = create_access_token(user.id, user.role)
    return access_token, raw_token, user


def refresh(raw_refresh_token: str) -> str:
    with Session(get_engine()) as db:
        token_row = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == hash_token(raw_refresh_token),
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(UTC),
            )
            .first()
        )
        if not token_row:
            raise ValueError('Invalid or expired refresh token.')

        user = db.scalar(select(User).where(User.id == token_row.user_id))
        if not user or not user.is_active:
            raise ValueError('Invalid or expired refresh token.')

    return create_access_token(user.id, user.role)


def logout(raw_refresh_token: str) -> None:
    with Session(get_engine()) as db:
        token_row = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == hash_token(raw_refresh_token),
                RefreshToken.revoked_at.is_(None),
            )
            .first()
        )
        if token_row:
            token_row.revoked_at = datetime.now(UTC)
            db.commit()
