from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from brobier.core.config import get_settings


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
