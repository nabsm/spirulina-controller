from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from .config import settings


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_local() -> datetime:
    return now_utc().astimezone(ZoneInfo(settings.timezone))
