from datetime import UTC, datetime

from app.interfaces.utilities.clock import IClock


class SystemClock(IClock):
    def now(self) -> datetime:
        return datetime.now(UTC)
