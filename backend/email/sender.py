import smtplib
from email.mime.text import MIMEText

from backend.core.config import get_settings


def send_login_code_email(to: str, code: str) -> None:
    settings = get_settings()
    body = (
        f'Your Brobier login code is: {code}\n\n'
        f'This code expires in {settings.login_code_expire_minutes} minutes.\n\n'
        'If you did not request this code, you can safely ignore this email.'
    )
    msg = MIMEText(body)
    msg['Subject'] = 'Your Brobier login code'
    msg['From'] = settings.smtp_from
    msg['To'] = to

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        if settings.smtp_use_tls:
            server.starttls()
        server.sendmail(settings.smtp_from, [to], msg.as_string())
