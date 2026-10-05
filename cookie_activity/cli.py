import argparse
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from cookie_activity.analysis import LogFormatError, find_most_active_cookies

PROGRAM_NAME = "most_active_cookie"
INPUT_ENCODING = "utf-8-sig"
EXIT_OK = 0
EXIT_ERROR = 1
LINE_END = "\n"
INVALID_ENCODING = "input must be valid UTF-8"
INPUT_FAILURE = "cannot read input file"
OUTPUT_FAILURE = "cannot write output"


def parse_date(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() == value:
            return parsed
    except ValueError:
        pass
    raise argparse.ArgumentTypeError(f"invalid date {value!a}: expected YYYY-MM-DD")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROGRAM_NAME,
        description="Print all most active cookies on one UTC date.",
        allow_abbrev=False,
    )
    parser.add_argument("-f", "--file", type=Path, required=True, help="cookie CSV file")
    parser.add_argument(
        "-d", "--date", type=parse_date, required=True, help="UTC date as YYYY-MM-DD"
    )
    return parser


def _report_error(message: str) -> None:
    print(f"{PROGRAM_NAME}: {message}", file=sys.stderr)


def _input_error_reason(error: OSError | UnicodeError | LogFormatError) -> str:
    if isinstance(error, LogFormatError):
        return str(error)
    if isinstance(error, UnicodeError):
        return INVALID_ENCODING
    return ascii(error.strerror or INPUT_FAILURE)[1:-1]


def _write_cookies(cookies: list[str]) -> None:
    try:
        if cookies:
            sys.stdout.write(LINE_END.join(cookies) + LINE_END)
        sys.stdout.flush()
    except (OSError, UnicodeError):
        try:
            sys.stdout.close()
        except (OSError, UnicodeError):
            pass
        raise


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        with args.file.open(encoding=INPUT_ENCODING, newline="") as stream:
            cookies = find_most_active_cookies(stream, args.date)
    except (OSError, UnicodeError, LogFormatError) as error:
        _report_error(f"{str(args.file)!a}: {_input_error_reason(error)}")
        return EXIT_ERROR
    try:
        _write_cookies(cookies)
    except (OSError, UnicodeError):
        _report_error(OUTPUT_FAILURE)
        return EXIT_ERROR
    return EXIT_OK
