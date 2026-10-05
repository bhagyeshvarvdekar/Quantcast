import csv
import io
from collections.abc import Iterable
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "most_active_cookie"
FIXTURE = ROOT / "tests" / "fixtures" / "cookie_log.csv"
DAY = date(2018, 12, 9)
DAY_ARGUMENT = "2018-12-09"
STAMP = "2018-12-09T12:00:00+00:00"
OLDER = "2018-12-08T12:00:00+00:00"
NEWER = "2018-12-10T12:00:00+00:00"
HEADER = "cookie,timestamp\n"
SAMPLE_OUTPUT = "AtY0laUfhglK3lC7\n"
PROCESS_TIMEOUT = 10


def log_text(rows: Iterable[tuple[str, str]]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(("cookie", "timestamp"))
    writer.writerows(rows)
    return stream.getvalue()
