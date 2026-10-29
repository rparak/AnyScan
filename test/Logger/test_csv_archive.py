## =========================================================================== ##
# MIT License
# Copyright (c) 2025 JIC Smart Factory
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
## =========================================================================== ##
# Author   : JIC Smart Factory
# File Name: ../test/Logger/test_csv_archive.py
## =========================================================================== ##

# System (Default)
import csv
import io
import os
import typing as tp
from datetime import datetime, timedelta
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan — the session logger and its CSV contract
#   ../Logger/Core
from Logger.Core import Session_Logger_Cls, CONST_CSV_COLUMNS, CONST_CSV_BOM, CONST_CSV_VERSION_SUFFIX

"""
Description:
    The run-summary CSV was cut to six columns, so a file written before the cut has rows that
    mean something different; so has a file of an earlier format version, whose header is the
    current one (version 1: total_session_time was connection time). Such a file is never appended
    to: it is renamed aside, byte-for-byte unchanged, as '<name>_until_<date>.csv', and the
    canonical name starts afresh. Tested end to end through the logger: the archive is identical to
    the old file, the new file carries only current-format rows, a current-format file is simply
    appended to, an earlier archive of the same day is never overwritten, and the '.txt' says what
    happened.
"""

# The 22-column header every file written before the cut carries, and two of its rows (one with a
# quoted detail cell holding commas and quotes).
CONST_OLD_COLUMNS = ['log_file', 'application_start', 'application_stop', 'cycle_time',
                     'cycle_hours', 'analyzed_images', 'analyzed_objects', 'sessions_count',
                     'total_session_time', 'idle_time', 'errors_count', 'total_error_time',
                     'session_details', 'error_details', 'run_id', 'classification_enabled',
                     'failed_analyses', 'scored_objects', 'nok_objects', 'mean_confidence',
                     'median_inference_ms', 'clears_count']
CONST_OLD_ROWS = [
    ['log_2026-09-19_10-02.txt', '2026-09-19 10:02:11', '2026-09-19 10:09:40', '00:07:29', '0.125',
     '2', '5', '1', '00:07:00', '00:00:29', '1', '00:00:04', '[{"index":1}]',
     '[{"id":1,"message":"Camera lost, \\"reconnected\\""}]', 'abc', 'false', '0', '5', '0', '91',
     '2483', '1'],
    ['log_2026-09-20_08-00.txt', '2026-09-20 08:00:00', '2026-09-20 08:00:06', '00:00:06', '0.002',
     '0', '0', '0', '00:00:00', '00:00:06', '0', '00:00:00', '', '', 'def', 'true', '0', '0', '0',
     '', '', '0'],
]
# The date the old file was last written, set on it so the archive name is deterministic.
CONST_OLD_MTIME = datetime(2026, 9, 20, 8, 0, 6)


class Clock_Cls(object):
    """A settable clock for the logger."""

    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def _Write_Old_File(path: str, columns: tp.List[str] = CONST_OLD_COLUMNS) -> bytes:
    """Write an older-format CSV (BOM, header, rows) at path, dated CONST_OLD_MTIME; its bytes."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    for row in CONST_OLD_ROWS:
        writer.writerow(row[:len(columns)])
    data = CONST_CSV_BOM.encode('utf-8') + buffer.getvalue().encode('utf-8')
    with open(path, 'wb') as handle:
        handle.write(data)
    stamp = CONST_OLD_MTIME.timestamp()
    os.utime(path, (stamp, stamp))
    return data


def _Run(tmp_path: tp.Any, start: datetime, session: bool = True) -> Session_Logger_Cls:
    """One run of 90 s, a scan and its analysis in the middle 60 s, closed (so its row is appended)."""
    clock = Clock_Cls(start)
    logger = Session_Logger_Cls(config_path=None, log_dir=str(tmp_path), clock=clock,
                                install_handlers=False)
    if session:
        clock.now = start + timedelta(seconds=15)
        logger.Log_Scan_Started()
        logger.Log_Scan_Ended()
        logger.Log_Analysis_Started(1)
        clock.now = start + timedelta(seconds=75)
        logger.Log_Analysis_Finished(1, 1000, 0, 0, None)
    clock.now = start + timedelta(seconds=90)
    logger.Close()
    return logger


def _Rows(path: str) -> tp.List[tp.List[str]]:
    """Every row of a CSV (header first), the byte-order mark stripped."""
    with open(path, 'r', newline='', encoding='utf-8-sig') as handle:
        return list(csv.reader(handle))


@pytest.mark.parametrize('columns', [CONST_OLD_COLUMNS, CONST_OLD_COLUMNS[:14]],
                         ids=['22 columns', '14 columns'])
def test_an_older_format_file_is_archived_unchanged_and_a_new_one_started(tmp_path, columns) -> None:
    """
    Description:
        A run closing onto a file with an older column set renames it, byte-for-byte unchanged, to
        '<name>_until_<date its last row was written>.csv', then starts the canonical file with the
        six current columns and its own row only — no row is ever written under a header that does
        not describe it. The '.txt' log names both files.
    """

    canonical = str(tmp_path / 'log_unconfigured.csv')
    old = _Write_Old_File(canonical, columns)
    logger = _Run(tmp_path, datetime(2026, 9, 23, 9, 0, 0))

    archive = tmp_path / 'log_unconfigured_until_2026-09-20.csv'
    assert archive.read_bytes() == old
    rows = _Rows(canonical)
    assert rows[0] == CONST_CSV_COLUMNS and len(rows) == 2
    with open(canonical, 'rb') as handle:
        assert handle.read().startswith(CONST_CSV_BOM.encode('utf-8'))
    with open(logger.Path, encoding='utf-8') as handle:
        text = handle.read()
    assert 'log_unconfigured_until_2026-09-20.csv' in text and 'older column set' in text
    assert '%d columns' % len(columns) in text


def test_a_current_format_file_is_appended_to_not_archived(tmp_path) -> None:
    """
    Description:
        Two runs append two rows to one file under one header; nothing is archived and the '.txt'
        says nothing about the CSV's format.
    """

    first = _Run(tmp_path, datetime(2026, 9, 23, 9, 0, 0))
    second = _Run(tmp_path, datetime(2026, 9, 23, 10, 0, 0))
    rows = _Rows(str(tmp_path / 'log_unconfigured.csv'))
    assert rows[0] == CONST_CSV_COLUMNS and len(rows) == 3
    assert (tmp_path / ('log_unconfigured.csv' + CONST_CSV_VERSION_SUFFIX)).read_text() == '2\n'
    assert not any('_until_' in name for name in os.listdir(tmp_path))
    for logger in (first, second):
        with open(logger.Path, encoding='utf-8') as handle:
            assert 'older column set' not in handle.read()


@pytest.mark.parametrize('version, read_as', [(None, 1), ('1\n', 1), ('two\n', 0)],
                         ids=['no version file', 'version 1', 'unreadable'])
def test_a_current_header_of_another_format_version_is_archived_with_its_version(tmp_path, version, read_as) -> None:
    """
    Description:
        A file with the current header but not format version 2 — no version file (every file written
        before 2026-10-07, when total_session_time was connection time), an older version, or one that
        is not a number — is archived unchanged like an older header, its version file moved beside the
        archive; the new file is version 2 with this run's row only, and the '.txt' names the version.
    """

    canonical = str(tmp_path / 'log_unconfigured.csv')
    old = _Write_Old_File(canonical, CONST_CSV_COLUMNS)
    if version is not None:
        with open(canonical + CONST_CSV_VERSION_SUFFIX, 'w', encoding='utf-8') as handle:
            handle.write(version)
    logger = _Run(tmp_path, datetime(2026, 10, 7, 9, 0, 0))

    archive = tmp_path / 'log_unconfigured_until_2026-09-20.csv'
    assert archive.read_bytes() == old
    archived_version = tmp_path / ('log_unconfigured_until_2026-09-20.csv' + CONST_CSV_VERSION_SUFFIX)
    if version is None:
        assert not archived_version.exists()
    else:
        assert archived_version.read_text() == version
    assert len(_Rows(canonical)) == 2
    with open(canonical + CONST_CSV_VERSION_SUFFIX, encoding='utf-8') as handle:
        assert handle.read() == '2\n'
    with open(logger.Path, encoding='utf-8') as handle:
        text = handle.read()
    assert 'was format version %d, whose rows mean something else' % read_as in text
    assert 'log_unconfigured_until_2026-09-20.csv' in text


def test_an_earlier_archive_of_the_same_day_is_never_overwritten(tmp_path) -> None:
    """
    Description:
        When '<name>_until_<date>.csv' already exists, the next archive of that date is '_2'.
    """

    earlier = tmp_path / 'log_unconfigured_until_2026-09-20.csv'
    earlier.write_bytes(b'earlier archive')
    old = _Write_Old_File(str(tmp_path / 'log_unconfigured.csv'))
    _Run(tmp_path, datetime(2026, 9, 23, 9, 0, 0))
    assert earlier.read_bytes() == b'earlier archive'
    assert (tmp_path / 'log_unconfigured_until_2026-09-20_2.csv').read_bytes() == old


def test_the_row_is_the_runs_time_account(tmp_path) -> None:
    """
    Description:
        The six cells: the log file, start and stop to the second, and three durations that add
        up — cycle_time == total_session_time + idle_time, the session time being the scan to the
        end of its analysis. A run with no scan is all idle.
    """

    logger = _Run(tmp_path, datetime(2026, 9, 23, 9, 0, 0))
    _Run(tmp_path, datetime(2026, 9, 23, 11, 0, 0), session=False)
    header, connected, idle = _Rows(str(tmp_path / 'log_unconfigured.csv'))
    assert connected == [os.path.basename(logger.Path), '2026-09-23 09:00:00', '2026-09-23 09:01:30',
                         '00:01:30', '00:01:00', '00:00:30']
    assert idle[3:] == ['00:01:30', '00:00:00', '00:01:30']
