from __future__ import annotations

import hashlib
import string
import uuid
from pathlib import Path

import pytest
from backend.auth.jwt import create_access_token, decode_access_token
from backend.auth.tokens import generate_login_code, hash_token
from backend.core.security import (
    decrypt_field,
    encrypt_field,
    generate_encryption_key,
)
from cryptography.fernet import Fernet


class TestGenerateEncryptionKey:
    def test_returns_valid_fernet_key(self, tmp_path: Path) -> None:
        env_file = tmp_path / '.env'
        key = generate_encryption_key(file=env_file)
        # A valid Fernet key must be accepted by Fernet without raising
        fernet = Fernet(key.encode())
        assert fernet is not None

    def test_writes_to_env_file(self, tmp_path: Path) -> None:
        env_file = tmp_path / '.env'
        key = generate_encryption_key(file=env_file)
        env_contents = env_file.read_text()
        assert f'BEER_ENCRYPTION_KEY={key}' in env_contents


@pytest.mark.usefixtures('needs_env_vars')
class TestEncryptField:
    def test_returns_non_empty_string(self) -> None:
        encrypted = encrypt_field('hello')
        assert isinstance(encrypted, str)
        assert len(encrypted) > 0
        assert encrypted != 'hello'

    def test_decrypt_roundtrip(self) -> None:
        original = 'super secret value'
        assert decrypt_field(encrypt_field(original)) == original

    def test_produces_different_ciphertext_each_call(self) -> None:
        value = 'same input'
        assert encrypt_field(value) != encrypt_field(value)


@pytest.mark.usefixtures('needs_env_vars')
class TestDecryptField:
    def test_raises_on_invalid_token(self) -> None:
        with pytest.raises(ValueError, match='Failed to decrypt field'):
            decrypt_field('not-a-valid-token')

    def test_raises_on_tampered_token(self) -> None:
        encrypted = encrypt_field('sensitive')
        tampered = encrypted[:-4] + 'XXXX'
        with pytest.raises(ValueError, match='Failed to decrypt field'):
            decrypt_field(tampered)


class TestHashToken:
    def test_returns_sha256_hex(self) -> None:
        token = 'mytoken'
        expected = hashlib.sha256(token.encode()).hexdigest()
        assert hash_token(token) == expected

    def test_is_deterministic(self) -> None:
        assert hash_token('abc') == hash_token('abc')

    def test_different_inputs_produce_different_hashes(self) -> None:
        assert hash_token('token_a') != hash_token('token_b')


class TestGenerateLoginCode:
    def test_default_length(self) -> None:
        code = generate_login_code()
        assert len(code) == 6

    def test_custom_length(self) -> None:
        code = generate_login_code(length=8)
        assert len(code) == 8

    def test_contains_only_digits(self) -> None:
        code = generate_login_code(length=20)
        assert all(c in string.digits for c in code)

    def test_is_not_always_identical(self) -> None:
        codes = {generate_login_code() for _ in range(20)}
        assert len(codes) > 1


class TestCreateAccessToken:
    def test_returns_non_empty_string(self) -> None:
        token = create_access_token(uuid.uuid4(), 'user')
        assert isinstance(token, str)
        assert len(token) > 0

    def test_payload_contains_subject_as_uuid_string(self) -> None:
        user_id = uuid.uuid4()
        token = create_access_token(user_id, 'user')
        payload = decode_access_token(token)
        assert payload['sub'] == str(user_id)

    def test_payload_contains_role(self) -> None:
        token = create_access_token(uuid.uuid4(), 'admin')
        payload = decode_access_token(token)
        assert payload['role'] == 'admin'

    def test_payload_contains_iat_and_exp(self) -> None:
        token = create_access_token(uuid.uuid4(), 'user')
        payload = decode_access_token(token)
        assert 'iat' in payload
        assert 'exp' in payload
        assert payload['exp'] > payload['iat']

    def test_different_users_produce_different_tokens(self) -> None:
        token_a = create_access_token(uuid.uuid4(), 'user')
        token_b = create_access_token(uuid.uuid4(), 'user')
        assert token_a != token_b


class TestDecodeAccessToken:
    def test_raises_on_invalid_token(self) -> None:
        with pytest.raises(ValueError, match='JWT token is invalid'):
            decode_access_token('not.a.valid.token')

    def test_raises_on_tampered_token(self) -> None:
        token = create_access_token(uuid.uuid4(), 'user')
        tampered = token[:-4] + 'XXXX'
        with pytest.raises(ValueError, match='JWT token is invalid'):
            decode_access_token(tampered)
