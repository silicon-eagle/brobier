from backend.services.sender import build_login_code_email


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
