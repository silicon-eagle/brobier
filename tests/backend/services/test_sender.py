import httpx2
import pytest
from backend.services.sender import build_login_code_email, send_login_code_email


@pytest.fixture
def login_code() -> str:
    return 'ABC123'

def test_build_login_code_email_includes_text_and_html_parts() -> None:
    message = build_login_code_email(
        to='friend@example.com',
        code='ABC123',
        smtp_from='noreply@brobier.local',
        expires_in_minutes=10,
    )

    assert message['Subject'] == 'Your Brobier login code'
    assert message['From'] == 'noreply@brobier.local'
    assert message['To'] == 'friend@example.com'
    assert message.get_content_type() == 'multipart/alternative'

    parts = list(message.iter_parts())
    assert len(parts) == 2
    assert parts[0].get_content_type() == 'text/plain'
    assert 'ABC123' in parts[0].get_content()
    assert parts[1].get_content_type() == 'text/html'
    assert 'Your login code' in parts[1].get_content()
    assert 'ABC123' in parts[1].get_content()
    assert '.card {' in parts[1].get_content()


def test_build_login_code_email_escapes_html_in_code() -> None:
    message = build_login_code_email(
        to='friend@example.com',
        code='<ABC123>',
        smtp_from='noreply@brobier.local',
        expires_in_minutes=10,
    )

    html_part = list(message.iter_parts())[1]
    assert '&lt;ABC123&gt;' in html_part.get_content()


def test_send_login_code_email_sends_email(login_code: str, mailpit: str) -> None:

    send_login_code_email(to='test@brobier.local', code=login_code)

    response = httpx2.get(f'{mailpit}/message/latest')
    response.raise_for_status()
    message = response.json()
    message_id = message['ID']

    assert message['Subject'] == 'Your Brobier login code'

    raw = httpx2.get(f'{mailpit}/message/{message_id}/raw')
    raw.raise_for_status()
    assert login_code in raw.text
