import re
from datetime import UTC, datetime

import httpx2
import pytest
from backend.auth.jwt import decode_access_token
from backend.auth.tokens import hash_token
from backend.db.engine import get_engine
from backend.db.models import LoginCode, RefreshToken, User
from backend.services.auth_service import logout, refresh, request_code, verify_code
from sqlalchemy.orm import Session


def _get_code_from_email(mailpit: str) -> str:
    response = httpx2.get(f'{mailpit}/messages')
    response.raise_for_status()
    message_id = response.json()['messages'][0]['ID']

    response = httpx2.get(f'{mailpit}/message/{message_id}')
    response.raise_for_status()
    text = response.json()['Text']

    match = re.search(r'login code is: (\d+)', text)
    assert match, f'Could not extract login code from email: {text!r}'
    return match.group(1)


@pytest.mark.usefixtures('database')
class TestAuthService:
    def test_request_code(self, mailpit: str) -> None:
        email = 'alice@brobier.local'
        before = datetime.now(UTC)
        request_code(email=email)
        with Session(get_engine()) as db:
            user = db.scalar(db.query(User).where(User.email == email))
            login_code = db.scalar(db.query(LoginCode).where(LoginCode.user_id == user.id).where(LoginCode.created_at >= before))
            assert login_code is not None
            assert login_code.code_hash is not None

            response = httpx2.get(f'{mailpit}/message/latest')
            response.raise_for_status()
            message = response.json()
            assert message['Subject'] == 'Your Brobier login code'

    def test_verify_code(self, mailpit: str) -> None:
        email = 'alice@brobier.local'
        httpx2.request('DELETE', f'{mailpit}/messages').raise_for_status()
        request_code(email=email)
        code = _get_code_from_email(mailpit)

        access_token, raw_refresh_token, user = verify_code(email=email, code=code)

        with Session(get_engine()) as db:
            login_code = db.scalar(db.query(LoginCode).where(LoginCode.code_hash == hash_token(code)))
            assert login_code is not None
            assert login_code.used_at is not None

            token_row = db.scalar(db.query(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_refresh_token)))
            assert token_row is not None
            assert token_row.revoked_at is None

        payload = decode_access_token(access_token)
        assert payload['sub'] == str(user.id)

        with pytest.raises(ValueError):
            verify_code(email=email, code=code)  # code cannot be reused

        with pytest.raises(ValueError):
            verify_code(email=email, code='000000')  # wrong code

        with pytest.raises(ValueError):
            verify_code(email='dave@brobier.local', code='000000')  # inactive user

    def test_refresh_token(self, mailpit: str) -> None:
        email = 'alice@brobier.local'
        httpx2.request('DELETE', f'{mailpit}/messages').raise_for_status()
        request_code(email=email)
        code = _get_code_from_email(mailpit)
        _, raw_refresh_token, user = verify_code(email=email, code=code)

        new_access_token = refresh(raw_refresh_token)

        payload = decode_access_token(new_access_token)
        assert payload['sub'] == str(user.id)

        with pytest.raises(ValueError):
            refresh('invalid-token')

    def test_logout(self, mailpit: str) -> None:
        email = 'alice@brobier.local'
        httpx2.request('DELETE', f'{mailpit}/messages').raise_for_status()
        request_code(email=email)
        code = _get_code_from_email(mailpit)
        _, raw_refresh_token, _ = verify_code(email=email, code=code)

        before = datetime.now(UTC)
        logout(raw_refresh_token)

        with Session(get_engine()) as db:
            token_row = db.scalar(db.query(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_refresh_token)))
            assert token_row is not None
            assert token_row.revoked_at is not None
            assert token_row.revoked_at >= before

        with pytest.raises(ValueError):
            refresh(raw_refresh_token)  # revoked token cannot be used

    def test_integration(self, mailpit: str) -> None:
        email = 'alice@brobier.local'
        httpx2.request('DELETE', f'{mailpit}/messages').raise_for_status()

        request_code(email=email)
        code = _get_code_from_email(mailpit)

        access_token, raw_refresh_token, user = verify_code(email=email, code=code)
        payload = decode_access_token(access_token)
        assert payload['sub'] == str(user.id)

        new_access_token = refresh(raw_refresh_token)
        new_payload = decode_access_token(new_access_token)
        assert new_payload['sub'] == str(user.id)

        logout(raw_refresh_token)

        with pytest.raises(ValueError):
            refresh(raw_refresh_token)  # token revoked after logout
