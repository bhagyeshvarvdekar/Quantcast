# Most active cookie

Find the cookie that appears most often in a log on a given UTC date. If several cookies tie, the script prints all of them, one per line.

You'll need Python 3.12 or later. The script uses the standard library, so there's nothing else to install.

## Run it

From the project directory:

```sh
./most_active_cookie -f tests/fixtures/cookie_log.csv -d 2018-12-09
```

`-f` is the log file and `-d` is the date, written as `YYYY-MM-DD`. The sample above prints:

```text
AtY0laUfhglK3lC7
```

You can run it through Python too:

```sh
python3 most_active_cookie -f tests/fixtures/cookie_log.csv -d 2018-12-09
```

`--file` and `--date` also work. Use `--help` to see the options, and put quotes around filenames that contain spaces.

## Tests

```sh
make check
```

If you don't have make:

```sh
python3 -m unittest discover -s tests -v
```

To use a particular Python version, run something like `make check PYTHON=python3.13`. The tests cover the sample log, ties, date boundaries, and failures when reading input or writing results.

## Input and results

The file must be UTF-8 CSV with the header `cookie,timestamp` and two fields per record. Quoted fields work, and blank lines are ignored. A UTF-8 BOM and either Unix or Windows line endings are fine.

Timestamps need an offset, such as `+00:00` or `Z`. They're converted to UTC before checking the date. For example, `2018-12-10T00:30:00+01:00` counts toward December 9.

A few details worth knowing:

- Duplicate rows count as separate occurrences.
- Cookie names are case sensitive, and spaces aren't trimmed. Empty names, names containing only whitespace, and ASCII control characters are rejected.
- Tied results are sorted by cookie name. If nothing matches the date, the command prints nothing and succeeds.
- A file containing just the header is valid. A completely empty file isn't.

Bad CSV, invalid timestamps, or unreadable input cause an error on stderr. The CSV parser's default field-size limit applies. The script checks the whole file before printing results, so a bad record near the end won't leave you with a partial answer.

The exit code is `0` for success or help, `1` for an input or output failure, and `2` for invalid arguments. A broken output pipe is handled without a traceback, though output already written can't be taken back.

## How it works

`cookie_activity/analysis.py` reads the log one record at a time and counts matching cookies with `Counter`. It leaves the stream open for its caller. `cookie_activity/cli.py` handles the command line and owns the input file.

Scanning the whole file also means unsorted logs work. The input file should stay unchanged while the command runs.
