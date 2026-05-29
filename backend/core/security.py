from __future__ import annotations

import hashlib
import random
import string
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import jwt
from cryptography.fernet import Fernet, InvalidToken

from backend.core.config import get_settings


def generate_encryption_key(file: Path | None = None) -> str:
    """
    Generates a new Fernet encryption key and writes it to the .env file as BEER_ENCRYPTION_KEY.
    Appends to the file if it already exists.
    """
    key = Fernet.generate_key().decode()
    file = file or Path('.env')
    with open(file, 'a') as f:
        f.write(f'\nBEER_ENCRYPTION_KEY={key}\n')
    return key


def _get_fernet() -> Fernet:
    key = get_settings().beer_encryption_key
    if not key:
        raise RuntimeError('BEER_ENCRYPTION_KEY is not set')
    return Fernet(key.encode())


def encrypt_field(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt_field(value: str) -> str:
    try:
        return _get_fernet().decrypt(value.encode()).decode()
    except InvalidToken as e:
        raise ValueError('Failed to decrypt field: token is invalid or tampered') from e


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_login_code(length: int = 6) -> str:
    return ''.join(random.choices(string.digits, k=length))


def generate_jwt(user_id: uuid.UUID, role: str) -> str:
    settings = get_settings()
    payload = {
        'sub': str(user_id),
        'role': role,
        'iat': datetime.now(UTC),
        'exp': datetime.now(UTC) + timedelta(seconds=settings.session_expire_seconds),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm='HS256')


def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, get_settings().jwt_secret, algorithms=['HS256'])
    except jwt.ExpiredSignatureError as e:
        raise ValueError('JWT token has expired') from e
    except jwt.InvalidTokenError as e:
        raise ValueError('JWT token is invalid') from e
