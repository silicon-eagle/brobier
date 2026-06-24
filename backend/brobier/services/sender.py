import smtplib
from email.message import EmailMessage
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from brobier.core.config import get_settings

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / 'templates'
TEMPLATE_ENV = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(
        disabled_extensions=('txt',),
        default=True,
    ),
)


def _render_login_code_email_bodies(code: str, expires_in_minutes: int) -> tuple[str, str]:
    template_context = {
        'code': code,
        'expires_in_minutes': expires_in_minutes,
    }
    text_body = TEMPLATE_ENV.get_template('email/login_code.txt.jinja').render(template_context).strip()
    html_body = TEMPLATE_ENV.get_template('email/login_code.html.jinja').render(template_context).strip()
    return text_body, html_body


def build_login_code_email(to: str, code: str, smtp_from: str, expires_in_minutes: int) -> EmailMessage:
    text_body, html_body = _render_login_code_email_bodies(
        code=code,
        expires_in_minutes=expires_in_minutes,
    )
    msg = EmailMessage()
    msg['Subject'] = 'Your Brobier login code'
    msg['From'] = smtp_from
    msg['To'] = to
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype='html')
    return msg


def send_login_code_email(to: str, code: str) -> EmailMessage:
    settings = get_settings()
    msg = build_login_code_email(
        to=to,
        code=code,
        smtp_from=settings.smtp_from,
        expires_in_minutes=settings.login_code_expire_minutes,
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        if settings.smtp_use_tls:
            server.ehlo()
            server.starttls()
            server.ehlo()
        server.send_message(msg)
    return msg
