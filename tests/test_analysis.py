import csv
import io
import unittest
from datetime import date

from cookie_activity.analysis import LogFormatError, find_most_active_cookies
from support import DAY, FIXTURE, HEADER, NEWER, OLDER, STAMP, log_text


def analyze(text: str, day: date = DAY) -> list[str]:
    with io.StringIO(text, newline="") as stream:
        return find_most_active_cookies(stream, day)


class AnalysisTests(unittest.TestCase):
    def test_sample_dates(self):
        text = FIXTURE.read_text(encoding="utf-8")
        cases = {
            7: ["4sMM2LxV07bPJzwf"],
            8: ["4sMM2LxV07bPJzwf", "SAZuXPGUrfbcn5UA", "fbcn5UAVanZf6UtG"],
            9: ["AtY0laUfhglK3lC7"],
            10: [],
        }
        for day, expected in cases.items():
            with self.subTest(day=day):
                self.assertEqual(analyze(text, date(2018, 12, day)), expected)

    def test_counting_and_ties(self):
        cases = [
            ("single", ["a"], ["a"]),
            ("duplicates", ["b", "a", "a"], ["a"]),
            ("tie", ["b", "a", "b", "a"], ["a", "b"]),
            ("case_sensitive", ["a", "A"], ["A", "a"]),
            ("preserve_spaces", ["A", " A", "B", "B"], ["B"]),
            ("quoted_comma", [" with,comma "], [" with,comma "]),
        ]
        for name, cookies, expected in cases:
            with self.subTest(case=name):
                self.assertEqual(analyze(log_text((cookie, STAMP) for cookie in cookies)), expected)

    def test_no_activity(self):
        for text in (HEADER, log_text([("new", NEWER), ("old", OLDER)])):
            with self.subTest(text=text):
                self.assertEqual(analyze(text), [])

    def test_unsorted_records(self):
        rows = [("a", STAMP), ("other", OLDER), ("b", STAMP), ("other", NEWER), ("a", STAMP)]
        self.assertEqual(analyze(log_text(rows)), ["a"])

    def test_utc_dates(self):
        cases = [
            ("midnight", "2018-12-09T00:00:00Z", True),
            ("last_microsecond", "2018-12-09T23:59:59.999999+00:00", True),
            ("next_midnight", "2018-12-10T00:00:00Z", False),
            ("positive_offset", "2018-12-10T00:30:00+01:00", True),
            ("negative_offset", "2018-12-08T23:30:00-01:00", True),
            ("previous_day", "2018-12-09T00:30:00+01:00", False),
        ]
        for name, stamp, included in cases:
            with self.subTest(case=name):
                self.assertEqual(analyze(log_text([("a", stamp)])), ["a"] if included else [])

    def test_invalid_timestamps(self):
        for stamp in ("bad-time", "2018-02-30T12:00:00Z", "2018-12-09T12:00:00",
                      "0001-01-01T00:00:00+01:00", "9999-12-31T23:59:59-01:00"):
            with self.subTest(timestamp=stamp):
                with self.assertRaises(LogFormatError) as raised:
                    analyze(log_text([("a", stamp)]))
                self.assertEqual(raised.exception.line_number, 2)

    def test_header_is_required(self):
        for text, line in (("", None), ("timestamp,cookie\n", 1), ("cookie,timestamp,cookie\n", 1)):
            with self.subTest(text=text):
                with self.assertRaises(LogFormatError) as raised:
                    analyze(text)
                self.assertEqual(raised.exception.line_number, line)
                self.assertTrue(str(raised.exception))

    def test_invalid_records(self):
        for row in ("a", f"a,{STAMP},extra", f",{STAMP}", f"  ,{STAMP}"):
            with self.subTest(row=row):
                with self.assertRaises(LogFormatError) as raised:
                    analyze(HEADER + row)
                self.assertEqual(raised.exception.line_number, 2)

    def test_control_characters_and_multiline_records(self):
        for cookie, line in (("private\nidentifier", 3), ("a\x1b", 2), ("a\x7f", 2)):
            with self.subTest(cookie=cookie):
                with self.assertRaises(LogFormatError) as raised:
                    analyze(log_text([(cookie, STAMP)]))
                self.assertEqual(raised.exception.line_number, line)
                self.assertNotIn(cookie, str(raised.exception))

    def test_invalid_csv(self):
        for row in ('"unclosed', f'"a"x,{STAMP}', "a" * (csv.field_size_limit() + 1)):
            with self.subTest(length=len(row)):
                with self.assertRaises(LogFormatError) as raised:
                    analyze(HEADER + row)
                self.assertEqual(raised.exception.line_number, 2)

    def test_blank_lines_and_line_endings(self):
        for ending in ("\n", "\r\n"):
            text = ending + HEADER.replace("\n", ending) + ending + f"a,{STAMP}"
            with self.subTest(ending=ending):
                self.assertEqual(analyze(text), ["a"])

    def test_analysis_leaves_the_stream_open(self):
        with io.StringIO(log_text([("a", STAMP)])) as stream:
            self.assertEqual(find_most_active_cookies(stream, DAY), ["a"])
            self.assertFalse(stream.closed)
