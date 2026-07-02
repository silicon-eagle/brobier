from datetime import datetime
from zoneinfo import ZoneInfo

APP_TIMEZONE = ZoneInfo('Europe/Amsterdam')


def current_time() -> datetime:
    return datetime.now(APP_TIMEZONE)
