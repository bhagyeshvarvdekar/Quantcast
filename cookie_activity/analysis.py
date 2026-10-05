import csv
import re
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import TextIO

EXPECTED_HEADER = ("cookie", "timestamp")
COOKIE_CONTROLS = re.compile(r"[\x00-\x1f\x7f]")
MISSING_HEADER = "missing cookie,timestamp header"
INVALID_HEADER = "expected header cookie,timestamp"
INVALID_COLUMNS = "expected exactly two columns"
EMPTY_COOKIE = "cookie must not be empty or whitespace-only"
INVALID_COOKIE = "cookie must not contain control characters"
INVALID_TIMESTAMP = "invalid ISO 8601 timestamp"
MISSING_OFFSET = "timestamp must include a UTC offset"
UTC_OVERFLOW = "timestamp is outside the supported UTC date range"
INVALID_CSV = "invalid CSV syntax or field exceeds the parser size limit"


@dataclass
class LogFormatError(ValueError):
    reason: str
    line_number: int | None = None

    def __str__(self) -> str:
        if self.line_number is None:
            return self.reason
        return f"record ending at line {self.line_number}: {self.reason}"


def _utc_date(value: str, line_number: int) -> date:
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError:
        raise LogFormatError(INVALID_TIMESTAMP, line_number) from None
    if timestamp.tzinfo is None:
        raise LogFormatError(MISSING_OFFSET, line_number)
    try:
        return timestamp.astimezone(timezone.utc).date()
    except OverflowError:
        raise LogFormatError(UTC_OVERFLOW, line_number) from None


def _parse_record(row: list[str], line_number: int) -> tuple[str, date]:
    if len(row) != len(EXPECTED_HEADER):
        raise LogFormatError(INVALID_COLUMNS, line_number)
    cookie, timestamp = row
    if not cookie.strip():
        raise LogFormatError(EMPTY_COOKIE, line_number)
    if COOKIE_CONTROLS.search(cookie):
        raise LogFormatError(INVALID_COOKIE, line_number)
    return cookie, _utc_date(timestamp, line_number)


def _cookies_on_date(stream: TextIO, target_date: date) -> Iterator[str]:
    reader = csv.reader(stream, strict=True)
    try:
        header = next((row for row in reader if row), None)
        if header is None:
            raise LogFormatError(MISSING_HEADER)
        if tuple(header) != EXPECTED_HEADER:
            raise LogFormatError(INVALID_HEADER, reader.line_num)
        for row in reader:
            if not row:
                continue
            cookie, utc_date = _parse_record(row, reader.line_num)
            if utc_date == target_date:
                yield cookie
    except csv.Error:
        raise LogFormatError(INVALID_CSV, reader.line_num) from None


def find_most_active_cookies(stream: TextIO, target_date: date) -> list[str]:
    counts = Counter(_cookies_on_date(stream, target_date))
    if not counts:
        return []
    max_count = max(counts.values())
    return sorted(cookie for cookie, count in counts.items() if count == max_count)
