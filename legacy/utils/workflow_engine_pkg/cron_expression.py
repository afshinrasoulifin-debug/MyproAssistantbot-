
"""
workflow_engine_pkg/cron_expression.py — CronExpression
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class CronExpression:
    """
    Parse and evaluate cron expressions.

    Format: minute hour day_of_month month day_of_week
    Supports: *, */n, n-m, n,m,o
    """

    def __init__(self, expression: str) -> None:
        parts = expression.strip().split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {expression}")
        self.minute = self._parse_field(parts[0], 0, 59)
        self.hour = self._parse_field(parts[1], 0, 23)
        self.day_of_month = self._parse_field(parts[2], 1, 31)
        self.month = self._parse_field(parts[3], 1, 12)
        self.day_of_week = self._parse_field(parts[4], 0, 6)

    def _parse_field(self, field: str, min_val: int, max_val: int) -> Set[int]:
        """Parse a single cron field into a set of valid values."""
        values: Set[int] = set()

        for part in field.split(","):
            if part == "*":
                values.update(range(min_val, max_val + 1))
            elif "/" in part:
                base, step = part.split("/")
                start = min_val if base == "*" else int(base)
                values.update(range(start, max_val + 1, int(step)))
            elif "-" in part:
                start, end = part.split("-")
                values.update(range(int(start), int(end) + 1))
            else:
                values.add(int(part))

        return values

    def matches(self, minute: int, hour: int, day: int,
                month: int, weekday: int) -> bool:
        """Check if the given time matches the cron expression."""
        return (
            minute in self.minute
            and hour in self.hour
            and day in self.day_of_month
            and month in self.month
            and weekday in self.day_of_week
        )




