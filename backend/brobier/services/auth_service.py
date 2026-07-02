from datetime import timedelta

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from brobier.auth.jwt import create_access_token
from brobier.auth.tokens import generate_login_code, generate_refresh_token, hash_token
from brobier.core.config import get_settings
from brobier.core.time import current_time
from brobier.db.engine import get_engine
from brobier.db.models.login_code import LoginCode
from brobier.db.models.refresh_token import RefreshToken
from brobier.db.models.user import User
from brobier.services.sender import send_login_code_email


def _generate_refresh_token(user: User, db: Session) -> str:
    settings = get_settings()
    raw_token = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=current_time() + timedelta(days=settings.jwt_refresh_expire_days),
        )
    )
    return raw_token


def _add_login_attempt(user: User, db: Session) -> None:
    user.nr_wrong_login_attempts += 1
    db.commit()


def _deactivate_login_codes(user: User, db: Session) -> None:
    db.query(LoginCode).filter(LoginCode.user_id == user.id).update({LoginCode.is_active: False})
    db.commit()


def _reset_user_login_attempts(user: User, db: Session) -> None:
    user.nr_wrong_login_attempts = 0
    db.commit()


def request_code(email: str) -> None:
    with Session(get_engine()) as db:
        user: User | None = db.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
        if user is None:
            return

        settings = get_settings()
        _reset_user_login_attempts(user, db)
        code = generate_login_code()
        db.add(
            LoginCode(
                user_id=user.id,
                code_hash=hash_token(code),
                expires_at=current_time() + timedelta(minutes=settings.login_code_expire_minutes),
            )
        )
        db.commit()
    send_login_code_email(email, code)


def verify_code(email: str, code: str) -> tuple[str, str, User]:
    with Session(get_engine()) as db:
        user: User | None = db.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
        if user is None:
            logger.warning(f'User tried to login with invalid email {email}')
            raise ValueError('Invalid or expired code.')

        login_code = (
            db.query(LoginCode)
            .filter(
                LoginCode.user_id == user.id,
                LoginCode.code_hash == hash_token(code),
                LoginCode.used_at.is_(None),
                LoginCode.expires_at > current_time(),
                LoginCode.is_active.is_(True),
            )
            .first()
        )
        if not login_code:
            logger.warning(f'User {user.email} tried to login with invalid or expired code')
            _add_login_attempt(user, db)

            if user.nr_wrong_login_attempts >= get_settings().login_max_attempts:
                logger.warning(f'Login codes for {user.email} have been set to inactive due to failed login attempts')
                _deactivate_login_codes(user, db)
                _reset_user_login_attempts(user, db)
            raise ValueError('Invalid or expired code.')

        login_code.used_at = current_time()
        _reset_user_login_attempts(user, db)

        raw_token = _generate_refresh_token(user, db)
        db.commit()
        db.refresh(user)

    access_token = create_access_token(user.id, user.role)
    return access_token, raw_token, user


def refresh(raw_refresh_token: str) -> tuple[str, str]:
    with Session(get_engine()) as db:
        token_row = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == hash_token(raw_refresh_token),
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > current_time(),
            )
            .first()
        )
        if not token_row:
            raise ValueError('Invalid or expired refresh token.')

        user: User | None = db.scalar(select(User).where(User.id == token_row.user_id))
        if user is None or not user.is_active:
            raise ValueError('Invalid or expired refresh token.')

        user_id, user_role = user.id, user.role
        token_row.revoked_at = current_time()

        new_raw_token = _generate_refresh_token(user, db)
        db.commit()

    return create_access_token(user_id, user_role), new_raw_token


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
            token_row.revoked_at = current_time()
            db.commit()
