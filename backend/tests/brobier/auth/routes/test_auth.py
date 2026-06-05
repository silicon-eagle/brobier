import pytest
from brobier.schemas.auth import MessageResponse, RequestCodeIn, TokenResponse, VerifyCodeIn, VerifyCodeResponse
from httpx import AsyncClient, Cookies, Response
from tests.mailpit_helpers import extract_code, get_last_message_id, get_message_by_id


@pytest.fixture
async def request_code(async_client: AsyncClient, mailpit: str, tst_globals: dict[str, str]) -> str:
    user_email = tst_globals['USER']
    request_code = RequestCodeIn(email=user_email)
    await async_client.post('/auth/request-code', json=request_code.model_dump(exclude_none=True))
    msg_id = get_last_message_id(mailpit=mailpit)
    return extract_code(mailpit=mailpit, message_id=msg_id)

@pytest.fixture
async def user_login(async_client: AsyncClient, tst_globals: dict[str, str], request_code: str) -> Response:
    user_email = tst_globals['USER']
    verify_code_in = VerifyCodeIn(email=user_email, code=request_code)
    response = await async_client.post('/auth/verify-code', json=verify_code_in.model_dump(exclude_none=True))
    access_token = response.json()['access_token']
    async_client.headers['Authorization'] = f'Bearer {access_token}'
    return response

@pytest.mark.usefixtures('database')
class TestAuthRoutes:
    async def test_request_code(self, async_client: AsyncClient, tst_globals: dict[str, str], mailpit: str) -> None:
        user_email = tst_globals['USER']
        request_code = RequestCodeIn(email=user_email)
        response = await async_client.post('/auth/request-code', json=request_code.model_dump(exclude_none=True))
        parsed_response = MessageResponse.model_validate(response.json())
        assert response.status_code == 200
        assert parsed_response.message == 'If that email is registered, a code has been sent.'

        msg_id = get_last_message_id(mailpit=mailpit)
        msg = get_message_by_id(mailpit=mailpit, message_id=msg_id)
        assert msg['Subject'] == 'Your Brobier login code'
        assert 'Your Brobier login code is:' in msg['Text']

    async def test_verify_code(self, async_client: AsyncClient, tst_globals: dict[str, str], request_code: str) -> None:
        user_email = tst_globals['USER']
        verify_code_in = VerifyCodeIn(email=user_email, code=request_code)
        response = await async_client.post('/auth/verify-code', json=verify_code_in.model_dump(exclude_none=True))
        parsed_response = VerifyCodeResponse.model_validate(response.json())
        assert response.status_code == 200
        assert parsed_response.token_type == 'bearer'
        assert parsed_response.access_token is not None
        assert isinstance(response.cookies, Cookies)

    async def test_verify_code_fails_on_invalid_code(self, async_client: AsyncClient, tst_globals: dict[str, str]) -> None:
        user_email = tst_globals['USER']
        verify_code_in = VerifyCodeIn(email=user_email, code='invalid')
        response = await async_client.post('/auth/verify-code', json=verify_code_in.model_dump(exclude_none=True))
        assert response.status_code == 401

    async def test_refresh(self, async_client: AsyncClient, user_login: Response)-> None:
        refresh_response = await async_client.post('/auth/refresh')
        assert refresh_response.status_code == 200
        parsed_response = TokenResponse.model_validate(refresh_response.json())
        assert parsed_response.token_type == 'bearer'
        assert parsed_response.access_token is not None
        assert isinstance(refresh_response.cookies, Cookies)
        assert user_login.cookies != refresh_response.cookies

    async def test_logout(self, async_client: AsyncClient, user_login: Response) -> None:
        logout_response = await async_client.post('/auth/logout')
        assert logout_response.status_code == 200
        parsed_response = MessageResponse.model_validate(logout_response.json())
        assert parsed_response.message == 'Logged out.'
        assert logout_response.cookies.get('brobier_refresh') is None

        refresh_response = await async_client.post('/auth/refresh')
        assert refresh_response.status_code == 401
