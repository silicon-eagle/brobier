import uuid
from datetime import timedelta

import jwt

from brobier.core.config import get_settings
from brobier.core.time import current_time


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    settings = get_settings()
    payload = {
        'sub': str(user_id),
        'role': role,
        'iat': current_time(),
        'exp': current_time() + timedelta(minutes=settings.jwt_access_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm='HS256')


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, get_settings().jwt_secret, algorithms=['HS256'])
    except jwt.ExpiredSignatureError as e:
        raise ValueError('JWT token has expired') from e
    except jwt.InvalidTokenError as e:
        raise ValueError('JWT token is invalid') from e
