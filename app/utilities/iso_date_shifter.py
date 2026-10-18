import re
from datetime import date, timedelta
from typing import Any

from app.constants.samples import ISO_DATE
from app.interfaces.utilities.date_shifter import IDateShifter


class IsoDateShifter(IDateShifter):
    def shift(self, value: Any, days: int) -> Any:
        if isinstance(value, str):
            return ISO_DATE.sub(lambda match: self._moved(match, days), value)
        if isinstance(value, list):
            return [self.shift(item, days) for item in value]
        if isinstance(value, dict):
            return {key: self.shift(item, days) for key, item in value.items()}
        return value

    @staticmethod
    def _moved(match: re.Match[str], days: int) -> str:
        try:
            original = date(int(match[1]), int(match[2]), int(match[3]))
        except ValueError:
            # Looks like a date but is not one; leave it as written.
            return match[0]
        return (original + timedelta(days=days)).isoformat()
