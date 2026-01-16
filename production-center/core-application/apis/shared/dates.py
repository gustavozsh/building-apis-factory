from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


def compute_date_range(
    timezone: str,
    start_date: str | None,
    end_date: str | None,
    reprocess_last_x_days: int,
) -> tuple[date, date]:
    tz = ZoneInfo(timezone)
    today = datetime.now(tz).date()

    if reprocess_last_x_days and (start_date or end_date):
        raise ValueError(
            "If using start_date/end_date, set reprocess_last_x_days to 0."
        )

    if reprocess_last_x_days > 0:
        start = today - timedelta(days=reprocess_last_x_days)
        end = today - timedelta(days=1)
        return start, end

    if start_date and end_date:
        return (
            datetime.strptime(start_date, "%Y-%m-%d").date(),
            datetime.strptime(end_date, "%Y-%m-%d").date(),
        )

    default_day = today - timedelta(days=1)
    return default_day, default_day


def build_date_list(start: date, end: date) -> list[str]:
    dates: list[str] = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates
