import argparse
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cookie_activity.cli import main, parse_date
from support import COMMAND, DAY_ARGUMENT, FIXTURE, HEADER, OLDER, PROCESS_TIMEOUT, SAMPLE_OUTPUT, STAMP, log_text

UTF8 = "utf-8"
OUTPUT_ERROR = "most_active_cookie: cannot write output\n"


def invoke(arguments: list[str]) -> tuple[int, str, str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            status = main(arguments)
        except SystemExit as error:
            status = error.code
    return status, stdout.getvalue(), stderr.getvalue()


class ArgumentTests(unittest.TestCase):
    def test_date_format(self):
        self.assertEqual(parse_date("2024-02-29").isoformat(), "2024-02-29")
        for value in ("2023-02-29", "20181209", "2018-W49-7", " 2018-12-09"):
            with self.subTest(date=value), self.assertRaises(argparse.ArgumentTypeError):
                parse_date(value)

    def test_bad_arguments(self):
        cases = [
            ["-d", DAY_ARGUMENT],
            ["-f", str(FIXTURE)],
            ["-f", str(FIXTURE), "-d", "2018-02-30"],
            ["--fi", str(FIXTURE), "-d", DAY_ARGUMENT],
        ]
        for arguments in cases:
            with self.subTest(arguments=arguments), patch.object(Path, "open") as open_file:
                status, stdout, stderr = invoke(arguments)
                self.assertEqual(status, 2)
                self.assertEqual(stdout, "")
                self.assertIn("usage:", stderr)
                open_file.assert_not_called()

    def test_help(self):
        status, stdout, stderr = invoke(["--help"])
        self.assertEqual(status, 0)
        self.assertIn("--file", stdout)
        self.assertIn("--date", stdout)
        self.assertEqual(stderr, "")


class FileTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "cookie log.csv"

    def run_file(self):
        return invoke(["-f", str(self.path), "-d", DAY_ARGUMENT])

    def assert_input_error(self, result):
        status, stdout, stderr = result
        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("most_active_cookie:", stderr)
        self.assertEqual(len(stderr.splitlines()), 1)

    def test_long_flags_and_utf8_file(self):
        self.path.write_bytes(log_text([("café", STAMP)]).encode("utf-8-sig"))
        result = invoke(["--file", str(self.path), "--date", DAY_ARGUMENT])
        self.assertEqual(result, (0, "café\n", ""))

    def test_no_matches(self):
        self.path.write_text(log_text([("a", OLDER)]), encoding=UTF8)
        self.assertEqual(self.run_file(), (0, "", ""))

    def test_missing_file(self):
        self.assert_input_error(self.run_file())

    def test_invalid_utf8(self):
        self.path.write_bytes(HEADER.encode(UTF8) + b"private-identifier,\xff")
        result = self.run_file()
        self.assert_input_error(result)
        self.assertIn("UTF-8", result[2])
        self.assertNotIn("private-identifier", result[2])

    def test_bad_row_does_not_print_partial_results(self):
        self.path.write_text(
            log_text([("winner", STAMP), ("older", OLDER), ("private", "bad-time")]),
            encoding=UTF8,
        )
        result = self.run_file()
        self.assert_input_error(result)
        self.assertIn("line 4", result[2])
        self.assertNotIn("private", result[2])

    def test_read_failure_closes_file(self):
        class FailingReader(io.StringIO):
            def __next__(self):
                line = super().__next__()
                if line.startswith("fail"):
                    raise OSError("read failed")
                return line

        stream = FailingReader(log_text([("winner", STAMP), ("fail", STAMP)]))
        with patch.object(Path, "open", return_value=stream):
            self.assert_input_error(self.run_file())
        self.assertTrue(stream.closed)


class ExecutableTests(unittest.TestCase):
    def test_sample_from_another_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(COMMAND), "-f", str(FIXTURE), "-d", DAY_ARGUMENT],
                cwd=directory, capture_output=True, text=True, check=False,
                timeout=PROCESS_TIMEOUT,
            )
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, SAMPLE_OUTPUT, ""))

    @unittest.skipUnless(os.name == "posix", "Unix executable permissions")
    def test_direct_executable(self):
        result = subprocess.run(
            [str(COMMAND), "-f", str(FIXTURE), "-d", DAY_ARGUMENT],
            capture_output=True, text=True, check=False, timeout=PROCESS_TIMEOUT,
        )
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, SAMPLE_OUTPUT, ""))

    def test_output_encoding_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unicode.csv"
            path.write_text(log_text([("café", STAMP)]), encoding=UTF8)
            result = subprocess.run(
                [sys.executable, str(COMMAND), "-f", str(path), "-d", DAY_ARGUMENT],
                env={**os.environ, "PYTHONIOENCODING": "ascii"},
                capture_output=True, text=True, check=False, timeout=PROCESS_TIMEOUT,
            )
        self.assertEqual((result.returncode, result.stdout, result.stderr), (1, "", OUTPUT_ERROR))

    def test_broken_pipe(self):
        read_fd, write_fd = os.pipe()
        os.close(read_fd)
        try:
            result = subprocess.run(
                [sys.executable, str(COMMAND), "-f", str(FIXTURE), "-d", DAY_ARGUMENT],
                stdout=write_fd, stderr=subprocess.PIPE, text=True,
                check=False, timeout=PROCESS_TIMEOUT,
            )
        finally:
            os.close(write_fd)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, OUTPUT_ERROR)
