## =========================================================================== ##
# MIT License
# Copyright (c) 2025 Roman Parak
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
# Author   : Roman Parak
# Email    : Roman.Parak@outlook.com
# Github   : https://github.com/rparak
# File Name: ../test/Logger/test_csv_extension.py
## =========================================================================== ##

# System (Default)
import csv
import io
import os
import typing as tp
from datetime import datetime
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan — the session logger and its CSV contract
#   ../Logger/Core
from Logger.Core import (Session_Logger_Cls, Extend_Csv_Header, CONST_CSV_COLUMNS, CONST_CSV_BOM,
                         CONST_CSV_EXTEND_SUFFIX)

"""
Description:
    The run-summary CSV gained columns. The header rewrite that lets an existing file carry them
    is the risky operation, so it is tested directly: a file with the OLD header and several rows
    is extended, every old row stays byte-identical and still reads correctly through
    csv.DictReader under the new header; a header that is NOT a prefix of the current columns
    still takes the align-and-warn path; and the new columns carry the whole-run figures, blank
    (never 0) where nothing was measured.
"""

# The column set before this change — the header every existing file carries.
CONST_OLD_COLUMNS = CONST_CSV_COLUMNS[:CONST_CSV_COLUMNS.index('error_details') + 1]
# Several realistic old rows, including a quoted error_details cell that holds commas and quotes.
CONST_OLD_ROWS = [
    ['log_2026-09-17_15-17.txt', '2026-09-17 15:17:29', '2026-09-17 15:21:43', '00:04:14', '0.071',
     '4', '16', '1', '00:04:04', '00:00:10', '0', '00:00:00', '1:15:17:37-15:21:41:00:04:04', ''],
    ['log_2026-09-18_07-23.txt', '2026-09-18 07:23:49', '2026-09-18 07:23:55', '00:00:06', '0.002',
     '0', '0', '0', '00:00:00', '00:00:06', '0', '00:00:00', '', ''],
    ['log_2026-09-19_10-02.txt', '2026-09-19 10:02:11', '2026-09-19 10:09:40', '00:07:29', '0.125',
     '2', '5', '1', '00:07:00', '00:00:29', '1', '00:00:04', '1:10:02:20-10:09:20:00:07:00',
     '1:10:05:01-10:05:05:00:00:04:Camera lost, "reconnected" (usb)'],
]


class Clock_Cls(object):
    """A settable clock for the logger."""

    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def _Old_File_Bytes(delimiter: str = ',') -> tp.Tuple[bytes, bytes]:
    """The bytes of an old CSV (BOM + old header + rows, csv-module CRLF endings) and its rows."""
    header, rows = io.StringIO(), io.StringIO()
    csv.writer(header, delimiter=delimiter).writerow(CONST_OLD_COLUMNS)
    writer = csv.writer(rows, delimiter=delimiter)
    for row in CONST_OLD_ROWS:
        writer.writerow(row)
    return (CONST_CSV_BOM.encode('utf-8') + header.getvalue().encode('utf-8')
            + rows.getvalue().encode('utf-8'), rows.getvalue().encode('utf-8'))


def _Logger(tmp_path: tp.Any, clock: Clock_Cls, delimiter: str = ',') -> Session_Logger_Cls:
    """A logger writing into tmp_path with no configuration attribution."""
    return Session_Logger_Cls(config_path=None, log_dir=str(tmp_path), clock=clock,
                              install_handlers=False, csv_delimiter=delimiter)


@pytest.mark.parametrize('delimiter', [',', ';'])
def test_extending_the_header_leaves_every_old_row_byte_identical(delimiter: str) -> None:
    """
    Description:
        The pure rewrite changes only the header line: the BOM is kept, the header gains exactly
        the appended names in order with the file's own CRLF terminator, and every byte after the
        header — every old row — is identical to what was there.
    """

    data, old_rows = _Old_File_Bytes(delimiter)
    result = Extend_Csv_Header(data, CONST_CSV_COLUMNS, delimiter)
    assert result is not None
    extended, added = result

    assert added == CONST_CSV_COLUMNS[len(CONST_OLD_COLUMNS):]
    bom = CONST_CSV_BOM.encode('utf-8')
    new_header = (delimiter.join(CONST_CSV_COLUMNS) + '\r\n').encode('utf-8')
    assert extended == bom + new_header + old_rows            # header swapped, rows untouched
    assert extended.endswith(old_rows)


def test_the_logger_extends_an_old_file_and_old_rows_read_under_the_new_header(tmp_path: tp.Any) -> None:
    """
    Description:
        End to end: a run closing onto a file with the old header extends it ONCE (an INFO line
        says so, no mismatch warning), keeps every old row byte-identical, and appends its own row
        with every column. csv.DictReader then reads the old rows under the new header with their
        values intact and the new columns empty, and a second run appends without extending again.
    """

    data, old_rows = _Old_File_Bytes()
    clock = Clock_Cls(datetime(2026, 9, 22, 9, 0, 0))
    first = _Logger(tmp_path, clock)
    with open(first.Csv_Path, 'wb') as f:
        f.write(data)
    first.Record_Run('run-abc', False)
    clock.now = datetime(2026, 9, 22, 9, 0, 30)
    first.Close()

    raw = open(first.Csv_Path, 'rb').read()
    header_line, _, rest = raw.partition(b'\r\n')
    assert header_line == CONST_CSV_BOM.encode('utf-8') + ','.join(CONST_CSV_COLUMNS).encode('utf-8')
    assert rest.startswith(old_rows)                            # old rows byte-identical, in order
    assert not os.path.exists(first.Csv_Path + CONST_CSV_EXTEND_SUFFIX)

    with open(first.Csv_Path, 'r', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == CONST_CSV_COLUMNS
        rows = list(reader)
    assert len(rows) == len(CONST_OLD_ROWS) + 1
    for old, parsed in zip(CONST_OLD_ROWS, rows):
        assert [parsed[c] for c in CONST_OLD_COLUMNS] == old     # quoted commas/quotes survive
        assert all(parsed[c] in (None, '') for c in CONST_CSV_COLUMNS[len(CONST_OLD_COLUMNS):])
    assert rows[-1]['run_id'] == 'run-abc' and rows[-1]['classification_enabled'] == 'false'

    log = open(first.Path, 'r', encoding='utf-8').read()
    assert 'Extended the run-summary CSV header with 8 new columns (run_id, ' in log
    assert 'does not match the current columns' not in log

    second = _Logger(tmp_path, Clock_Cls(datetime(2026, 9, 22, 10, 0, 0)))
    second.Close()
    assert open(second.Csv_Path, 'rb').read().startswith(raw)   # appended, nothing rewritten
    assert 'Extended the run-summary CSV header' not in open(second.Path, encoding='utf-8').read()


@pytest.mark.parametrize('stale_header', [
    [CONST_OLD_COLUMNS[1], CONST_OLD_COLUMNS[0]] + CONST_OLD_COLUMNS[2:],       # reordered
    CONST_OLD_COLUMNS[:5] + ['renamed_column'] + CONST_OLD_COLUMNS[6:],        # renamed
    CONST_CSV_COLUMNS + ['column_from_a_newer_version'],                      # longer than current
])
def test_a_non_prefix_header_still_takes_align_and_warn(tmp_path: tp.Any, stale_header) -> None:
    """
    Description:
        Only a strict prefix is extended. A reordered, renamed or longer header is never rewritten:
        the pure function declines, the file's header is left exactly as it was, the row is aligned
        to it, and the mismatch warning is logged.
    """

    header = io.StringIO()
    csv.writer(header).writerow(stale_header)
    data = CONST_CSV_BOM.encode('utf-8') + header.getvalue().encode('utf-8')
    assert Extend_Csv_Header(data, CONST_CSV_COLUMNS, ',') is None

    clock = Clock_Cls(datetime(2026, 9, 22, 11, 0, 0))
    logger = _Logger(tmp_path, clock)
    with open(logger.Csv_Path, 'wb') as f:
        f.write(data)
    clock.now = datetime(2026, 9, 22, 11, 0, 5)
    logger.Close()

    with open(logger.Csv_Path, 'r', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == stale_header
        assert len(list(reader)) == 1
    log = open(logger.Path, 'r', encoding='utf-8').read()
    assert '[WARNING] The run-summary CSV header does not match the current columns' in log
    assert 'Extended the run-summary CSV header' not in log


def test_new_columns_carry_whole_run_figures_and_blank_when_unmeasured(tmp_path: tp.Any) -> None:
    """
    Description:
        The new cells are whole-run: failures, scored and NOK objects, and Clear presses are
        counted; the run mean pools every scored object (each weighted once, rounded per object as
        the status bar does) and the inference figure is the median over completed analyses. A run
        that completed no analysis and scored nothing leaves both blank — never 0.
    """

    clock = Clock_Cls(datetime(2026, 9, 22, 12, 0, 0))
    logger = _Logger(tmp_path / 'measured', clock)
    logger.Record_Run('run-1', True)
    for confidence in (90, 90, 90, None):
        logger.Log_Object_Detected('p', confidence)
    logger.Log_Analysis_Finished(1, 1100, 4, 3, 90, nok=1)
    logger.Log_Cleared()
    logger.Log_Analysis_Failed('The model could not read the frame.')
    logger.Log_Object_Detected('p', 30)
    logger.Log_Analysis_Finished(2, 1500, 1, 1, 30, nok=0)
    logger.Log_Analysis_Finished(3, 1200, 0, 0, None, nok=0)
    clock.now = datetime(2026, 9, 22, 12, 1, 0)
    logger.Close()

    with open(logger.Csv_Path, 'r', newline='', encoding='utf-8-sig') as f:
        row = list(csv.DictReader(f))[-1]
    assert (row['analyzed_images'], row['analyzed_objects']) == ('3', '5')   # Clear ignored
    assert row['run_id'] == 'run-1' and row['classification_enabled'] == 'true'
    assert (row['failed_analyses'], row['scored_objects'], row['nok_objects']) == ('1', '4', '1')
    assert row['mean_confidence'] == '75'                       # (90*3 + 30) / 4, not 60
    assert row['median_inference_ms'] == '1200'
    assert row['clears_count'] == '1'

    empty = _Logger(tmp_path / 'empty', Clock_Cls(datetime(2026, 9, 22, 13, 0, 0)))
    empty.Close()
    with open(empty.Csv_Path, 'r', newline='', encoding='utf-8-sig') as f:
        blank = list(csv.DictReader(f))[-1]
    assert blank['mean_confidence'] == '' and blank['median_inference_ms'] == ''
    assert blank['classification_enabled'] == '' and blank['run_id'] == ''
    assert (blank['failed_analyses'], blank['nok_objects'], blank['clears_count']) == ('0', '0', '0')
