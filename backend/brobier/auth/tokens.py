import hashlib
import secrets
import string


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_login_code(length: int = 6) -> str:
    return ''.join(secrets.choice(string.digits) for _ in range(length))


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)
