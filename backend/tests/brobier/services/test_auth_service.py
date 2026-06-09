import re

import httpx
import pytest
from brobier.auth.jwt import decode_access_token
from brobier.auth.tokens import hash_token
from brobier.core.time import current_time
from brobier.db.engine import get_engine
from brobier.db.models import LoginCode, RefreshToken, User
from brobier.services.auth_service import logout, refresh, request_code, verify_code
from sqlalchemy.orm import Session


def _get_code_from_email(mailpit: str) -> str:
    response = httpx.get(f'{mailpit}/messages')
    response.raise_for_status()
    message_id = response.json()['messages'][0]['ID']

    response = httpx.get(f'{mailpit}/message/{message_id}')
    response.raise_for_status()
    text = response.json()['Text']

    match = re.search(r'login code is: (\d+)', text)
    assert match, f'Could not extract login code from email: {text!r}'
    return match.group(1)


@pytest.mark.usefixtures('database')
class TestAuthService:
    def test_request_code(self, mailpit: str, tst_globals: dict[str, str]) -> None:
        email = tst_globals['USER']
        request_code(email=email)
        with Session(get_engine()) as db:
            user = db.scalar(db.query(User).where(User.email == email))
            login_code = db.scalar(db.query(LoginCode).where(LoginCode.user_id == user.id))
            assert login_code is not None
            assert login_code.code_hash is not None

            response = httpx.get(f'{mailpit}/message/latest')
            response.raise_for_status()
            message = response.json()
            assert message['Subject'] == 'Your Brobier login code'

    def test_verify_code(self, mailpit: str, tst_globals: dict[str, str]) -> None:
        email = tst_globals['USER']
        httpx.request('DELETE', f'{mailpit}/messages').raise_for_status()
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

    def test_refresh_token(self, mailpit: str, tst_globals: dict[str, str]) -> None:
        email = tst_globals['USER']
        httpx.request('DELETE', f'{mailpit}/messages').raise_for_status()
        request_code(email=email)
        code = _get_code_from_email(mailpit)
        _, raw_refresh_token, user = verify_code(email=email, code=code)

        new_access_token, new_raw_refresh_token = refresh(raw_refresh_token)

        payload = decode_access_token(new_access_token)
        assert payload['sub'] == str(user.id)
        assert new_raw_refresh_token != raw_refresh_token

        with Session(get_engine()) as db:
            old_token_row = db.scalar(db.query(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_refresh_token)))
            assert old_token_row.revoked_at is not None

        with pytest.raises(ValueError):
            refresh(raw_refresh_token)  # old token revoked

        with pytest.raises(ValueError):
            refresh('invalid-token')

    def test_logout(self, mailpit: str, tst_globals: dict[str, str]) -> None:
        email = tst_globals['USER']
        httpx.request('DELETE', f'{mailpit}/messages').raise_for_status()
        request_code(email=email)
        code = _get_code_from_email(mailpit)
        _, raw_refresh_token, _ = verify_code(email=email, code=code)

        before = current_time()
        logout(raw_refresh_token)

        with Session(get_engine()) as db:
            token_row = db.scalar(db.query(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_refresh_token)))
            assert token_row is not None
            assert token_row.revoked_at is not None
            assert token_row.revoked_at >= before

        with pytest.raises(ValueError):
            refresh(raw_refresh_token)  # revoked token cannot be used

    def test_integration(self, mailpit: str, tst_globals: dict[str, str]) -> None:
        email = tst_globals['USER']
        httpx.request('DELETE', f'{mailpit}/messages').raise_for_status()

        request_code(email=email)
        code = _get_code_from_email(mailpit)

        access_token, raw_refresh_token, user = verify_code(email=email, code=code)
        payload = decode_access_token(access_token)
        assert payload['sub'] == str(user.id)

        new_access_token, new_raw_refresh_token = refresh(raw_refresh_token)
        new_payload = decode_access_token(new_access_token)
        assert new_payload['sub'] == str(user.id)

        logout(new_raw_refresh_token)

        with pytest.raises(ValueError):
            refresh(new_raw_refresh_token)  # token revoked after logout
