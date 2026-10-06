"""Calculate calendar availability without suggested-day scheduling."""

from datetime import date, timedelta

from src.domains.recurring.models import Cadence, Period


def calc_period(cadence: Cadence, today: date) -> Period:
    """Return the current week, month, or quarter containing today.

    Weeks start Monday; months and quarters follow the Gregorian calendar.
    All intervals include the start and exclude the end.
    """
    if cadence == Cadence.WEEKLY:
        start = today - timedelta(days=today.weekday())
        return Period(start, start + timedelta(days=7))
    month = today.month
    width = 1
    if cadence == Cadence.QUARTERLY:
        month = ((month - 1) // 3) * 3 + 1
        width = 3
    start = date(today.year, month, 1)
    next_month = month + width
    end = date(
        today.year + (next_month - 1) // 12, (next_month - 1) % 12 + 1, 1
    )
    return Period(start, end)
