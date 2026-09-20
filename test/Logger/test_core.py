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
# File Name: ../test/Logger/test_core.py
## =========================================================================== ##

# System (Default)
import os
import re
import csv
from datetime import datetime
# Typing (Support for type hints)
import typing as tp
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan — the session logger
#   ../Logger/Core
from Logger.Core import (Session_Logger_Cls, Format_HMS, Parse_Line, CONST_CSV_COLUMNS,
                         CONST_LEVEL_INFO, CONST_LEVEL_WARNING, CONST_LEVEL_ERROR)

"""
Description:
    Tests for the session logger. Every test injects a settable clock so the output
    is deterministic, and writes to a pytest tmp_path so the file system is isolated.
    The shutdown hooks are disabled (install_handlers=False) so a test never touches
    the process-wide atexit list or signal handlers.

    The run summary is persisted as one appended row per run in a single static CSV
    file; the '.txt' file keeps only the chronological event lines. Rows are read back
    with csv.DictReader rather than by comparing raw strings, except for the one
    golden-file test of the exact header line.
"""
# The golden file holding the exact CSV header line for the header-line test.
#   Unit [string]
CONST_GOLDEN_HEADER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'data', 'golden_header.csv')


class Clock_Cls(object):
    """
    Description:
        A settable, deterministic clock. Each call returns the datetime currently held
        in `now`; the test advances it explicitly before each logged event.

    Initialization of the Class:
        Args:
            (1) now [datetime(object)]: The initial time.
    """

    def __init__(self, now: datetime) -> None:
        # << PRIVATE >> #
        self.now = now

    def __call__(self) -> datetime:
        """
        Description:
            Return the time currently held by the clock.

        Returns:
            (1) parameter [datetime(object)]: The current time.
        """

        return self.now


def _T(hms: str) -> datetime:
    """
    Description:
        Build a datetime on the fixed test date 2026-09-12 from an 'HH:MM:SS' string.

    Args:
        (1) hms [string]: The time of day.

    Returns:
        (1) parameter [datetime(object)]: The datetime on the test date.
    """

    return datetime.strptime('2026-09-12 ' + hms, '%Y-%m-%d %H:%M:%S')


def _Hms_To_Seconds(hms: str) -> int:
    """
    Description:
        Parse an 'HH:MM:SS' duration back into whole seconds, for arithmetic checks on
        the formatted CSV cells.

    Args:
        (1) hms [string]: The duration as HH:MM:SS.

    Returns:
        (1) parameter [int]: The duration in seconds.
    """

    hours, minutes, seconds = (int(part) for part in hms.split(':'))
    return hours * 3600 + minutes * 60 + seconds


def _Read_Rows(path: str, delimiter: str = ',') -> tp.List[tp.Dict[str, str]]:
    """
    Description:
        Read every data row of a run-summary CSV back as an ordered list of dicts,
        keyed by the header. The 'utf-8-sig' codec strips the leading byte-order mark.

    Args:
        (1) path [string]: The CSV file path.
        (2) delimiter [string]: The CSV delimiter.

    Returns:
        (1) parameter [Vector<Dict[string, string]>]: The data rows.
    """

    with open(path, 'r', newline='', encoding='utf-8-sig') as csv_file:
        return list(csv.DictReader(csv_file, delimiter=delimiter))


def _Read_Header_Line(path: str) -> str:
    """
    Description:
        Read the raw first (header) line of a CSV, with the byte-order mark and the
        line terminator stripped.

    Args:
        (1) path [string]: The CSV file path.

    Returns:
        (1) parameter [string]: The header line.
    """

    with open(path, 'r', encoding='utf-8-sig') as csv_file:
        return csv_file.readline().rstrip('\r\n')


def _Build_Reference_Run(tmp_path: tp.Any) -> tp.Tuple[Session_Logger_Cls, Clock_Cls, datetime]:
    """
    Description:
        Drive the realistic reference scenario: two sessions (the second still open at
        shutdown), three analyzed images, and two errors (one resolved, one left
        unresolved). The clock is returned so a test can advance it to the stop time
        before closing the run.

    Args:
        (1) tmp_path [pathlib.Path(object)]: The pytest temporary directory.

    Returns:
        (1) parameter [Tuple[Session_Logger_Cls, Clock_Cls, datetime]]: The driven
            logger, its clock, and the application stop time.
    """

    clock = Clock_Cls(_T('14:37:02'))
    Session_Logger = Session_Logger_Cls(log_dir=str(tmp_path), clock=clock, install_handlers=False)

    clock.now = _T('14:37:12'); Session_Logger.Log_Camera_Connected()
    clock.now = _T('14:37:21'); Session_Logger.Log_Analysis_Finished(14, 1000, 3, 0, None)
    clock.now = _T('14:37:25'); Session_Logger.Log_Analysis_Finished(15, 1000, 2, 0, None)
    clock.now = _T('14:37:34'); error_id = Session_Logger.Log_Error('camera timeout')
    clock.now = _T('14:37:49'); Session_Logger.Log_Error_Resolved(error_id)
    clock.now = _T('14:40:02'); Session_Logger.Log_Camera_Disconnected()
    clock.now = _T('14:52:30'); Session_Logger.Log_Camera_Connected()
    clock.now = _T('15:05:00'); Session_Logger.Log_Analysis_Finished(42, 1000, 4, 0, None)
    clock.now = _T('15:20:01'); Session_Logger.Log_Error('analysis failed on image 233')

    return (Session_Logger, clock, _T('16:12:44'))


def test_format_hms() -> None:
    """
    Description:
        Format_HMS renders HH:MM:SS, clamps negatives to zero and does not cap hours.
    """

    assert Format_HMS(0) == '00:00:00'
    assert Format_HMS(170) == '00:02:50'
    assert Format_HMS(5742) == '01:35:42'
    assert Format_HMS(-10) == '00:00:00'
    assert Format_HMS(90061) == '25:01:01'


def test_filename_from_start_timestamp(tmp_path: tp.Any) -> None:
    """
    Description:
        The '.txt' filename is 'log_[date]_[hour-minutes].txt', taken from the start time.
    """

    clock = Clock_Cls(_T('14:37:02'))
    Session_Logger = Session_Logger_Cls(log_dir=str(tmp_path), clock=clock, install_handlers=False)
    assert os.path.basename(Session_Logger.Path) == 'log_2026-09-12_14-37.txt'
    Session_Logger.Close()


def test_csv_filename_is_static_hardware_template(tmp_path: tp.Any) -> None:
    """
    Description:
        The CSV filename is the static, hardware-identifying name and lives beside the
        '.txt' log in the same directory.
    """

    Session_Logger = Session_Logger_Cls(log_dir=str(tmp_path), clock=Clock_Cls(_T('09:00:00')),
                                        install_handlers=False)
    assert os.path.basename(Session_Logger.Csv_Path) == 'log_a2A1920_51gcPRO_Computar_M1228_MPW3.csv'
    assert os.path.dirname(Session_Logger.Csv_Path) == str(tmp_path)
    Session_Logger.Close()


def test_log_directory_created_when_missing(tmp_path: tp.Any) -> None:
    """
    Description:
        The log directory is created if it does not exist.
    """

    target = os.path.join(str(tmp_path), 'nested', 'logger')
    assert not os.path.isdir(target)
    Session_Logger = Session_Logger_Cls(log_dir=target, clock=Clock_Cls(_T('09:00:00')),
                                        install_handlers=False)
    assert os.path.isdir(target)
    assert os.path.isfile(Session_Logger.Path)
    Session_Logger.Close()


def test_line_format(tmp_path: tp.Any) -> None:
    """
    Description:
        Every event line is exactly '[Date] [Time] [LEVEL] message', with the level in a
        fixed-width field so it reads as a column.
    """

    clock = Clock_Cls(_T('14:37:02'))
    Session_Logger = Session_Logger_Cls(log_dir=str(tmp_path), clock=clock, install_handlers=False)
    Session_Logger.Log_Info('Application started')
    with open(Session_Logger.Path, 'r', encoding='utf-8') as f:
        first_line = f.readline().rstrip('\n')
    assert first_line == '2026-09-12 14:37:02 [INFO   ] Application started'
    Session_Logger.Close()


def test_levels_are_a_fixed_width_column_chosen_by_the_call_site(tmp_path: tp.Any) -> None:
    """
    Description:
        Every line carries its severity in a fixed-width bracketed field between the
        timestamp and the message, so the level reads as a column. The level is the call
        site's: a lost connection is ERROR (the operation failed), and an error's
        resolution is INFO (the resolution is the news, the fault was ERROR when it
        happened).
    """

    clock = Clock_Cls(_T('14:37:02'))
    logger = Session_Logger_Cls(log_dir=str(tmp_path), clock=clock, install_handlers=False)
    logger.Log_Info('an info line')
    logger.Log_Warning('a warning line')
    error_id = logger.Log_Error('an error line')
    logger.Log_Error_Resolved(error_id)
    logger.Log_Camera_Connected()
    logger.Log_Camera_Connection_Lost()
    with open(logger.Path, 'r', encoding='utf-8') as handle:
        content = handle.read()
    logger.Close()

    assert ' [INFO   ] an info line' in content
    assert ' [WARNING] a warning line' in content
    assert ' [ERROR  ] an error line (error_id=' in content
    assert ' [INFO   ] Error ' in content and 'resolved after' in content   # resolution is INFO
    assert ' [ERROR  ] The camera connection was lost' in content   # the loss is ERROR
    # The bracket sits at the same offset on every line (the level is one fixed column
    # after the 19-character 'YYYY-MM-DD HH:MM:SS' timestamp and a space).
    for line in (item for item in content.splitlines() if item):
        assert line[20] == '[' and line[28] == ']'


def test_single_session_duration(tmp_path: tp.Any) -> None:
    """
    Description:
        A single connect -> disconnect session records the correct duration.
    """

    clock = Clock_Cls(_T('10:00:00'))
    Session_Logger = Session_Logger_Cls(log_dir=str(tmp_path), clock=clock, install_handlers=False)
    clock.now = _T('10:00:05'); Session_Logger.Log_Camera_Connected()
    clock.now = _T('10:02:35'); Session_Logger.Log_Camera_Disconnected()

    assert len(Session_Logger.Sessions) == 1
    session = Session_Logger.Sessions[0]
    assert (session.End - session.Start).total_seconds() == 150.0
    Session_Logger.Close()


def test_image_and_object_counters(tmp_path: tp.Any) -> None:
    """
    Description:
        The run-wide image and object counters accumulate, and the per-session
        counters follow the open session.
    """

    clock = Clock_Cls(_T('08:00:00'))
    Session_Logger = Session_Logger_Cls(log_dir=str(tmp_path), clock=clock, install_handlers=False)
    clock.now = _T('08:00:01'); Session_Logger.Log_Camera_Connected()
    clock.now = _T('08:00:05'); Session_Logger.Log_Analysis_Finished(1, 1000, 3, 0, None)
    clock.now = _T('08:00:09'); Session_Logger.Log_Analysis_Finished(2, 1000, 2, 0, None)

    assert Session_Logger.Analyzed_Images == 2
    assert Session_Logger.Analyzed_Objects == 5
    assert Session_Logger.Sessions[0].Images == 2
    assert Session_Logger.Sessions[0].Objects == 5
    Session_Logger.Close()


def test_orphan_events_are_warnings(tmp_path: tp.Any) -> None:
    """
    Description:
        A disconnect without a connect, and a resolve without an error, are logged as
        warnings and do not corrupt the statistics.
    """

    clock = Clock_Cls(_T('07:00:00'))
    Session_Logger = Session_Logger_Cls(log_dir=str(tmp_path), clock=clock, install_handlers=False)
    Session_Logger.Log_Camera_Disconnected()
    Session_Logger.Log_Error_Resolved(999)

    assert len(Session_Logger.Sessions) == 0
    assert len(Session_Logger.Errors) == 0
    content = open(Session_Logger.Path, 'r', encoding='utf-8').read()
    assert '[WARNING] Camera disconnected, but no session was open.' in content
    assert '[WARNING] An error resolution arrived with no matching error (error_id=999).' in content
    Session_Logger.Close()


def test_csv_header_written_once_and_matches_golden(tmp_path: tp.Any) -> None:
    """
    Description:
        The first run creates the CSV, writes the header exactly once as the first
        line (matching the committed golden header) and then one data row.
    """

    Session_Logger = Session_Logger_Cls(log_dir=str(tmp_path), clock=Clock_Cls(_T('12:16:23')),
                                        install_handlers=False)
    Session_Logger.Close()

    with open(CONST_GOLDEN_HEADER, 'r', encoding='utf-8') as f:
        expected_header = f.read().rstrip('\r\n')
    assert _Read_Header_Line(Session_Logger.Csv_Path) == expected_header

    # The header appears exactly once, and the file holds one data row.
    with open(Session_Logger.Csv_Path, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    assert content.count('log_file,application_start') == 1
    assert len(_Read_Rows(Session_Logger.Csv_Path)) == 1


def test_second_run_appends_without_duplicate_header(tmp_path: tp.Any) -> None:
    """
    Description:
        A second run appends its row to the existing CSV and never re-writes the header.
    """

    first = Session_Logger_Cls(log_dir=str(tmp_path), clock=Clock_Cls(_T('09:00:00')),
                               install_handlers=False)
    csv_path = first.Csv_Path
    first.Close()

    second = Session_Logger_Cls(log_dir=str(tmp_path), clock=Clock_Cls(_T('10:00:00')),
                                install_handlers=False)
    second.Close()

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    assert content.count('log_file,application_start') == 1
    assert len(_Read_Rows(csv_path)) == 2


def test_three_runs_produce_three_rows_in_order(tmp_path: tp.Any) -> None:
    """
    Description:
        Three consecutive runs produce three data rows, in chronological order.
    """

    starts = ['08:00:00', '09:30:00', '11:15:00']
    csv_path = None
    for start in starts:
        Session_Logger = Session_Logger_Cls(log_dir=str(tmp_path), clock=Clock_Cls(_T(start)),
                                            install_handlers=False)
        csv_path = Session_Logger.Csv_Path
        Session_Logger.Close()

    rows = _Read_Rows(csv_path)
    assert len(rows) == 3
    starts_written = [row['application_start'] for row in rows]
    assert starts_written == ['2026-09-12 08:00:00', '2026-09-12 09:30:00', '2026-09-12 11:15:00']
    assert starts_written == sorted(starts_written)


def test_columns_present_in_declared_order_and_format(tmp_path: tp.Any) -> None:
    """
    Description:
        Every declared column is present, in the declared order, and each cell carries
        the declared format.
    """

    Session_Logger, clock, stop_time = _Build_Reference_Run(tmp_path)
    clock.now = stop_time; Session_Logger.Close()

    with open(Session_Logger.Csv_Path, 'r', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == CONST_CSV_COLUMNS
        row = next(reader)

    assert re.fullmatch(r'log_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}\.txt', row['log_file'])
    assert re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', row['application_start'])
    assert re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', row['application_stop'])
    for key in ('cycle_time', 'total_session_time', 'idle_time', 'total_error_time'):
        assert re.fullmatch(r'\d{2,}:\d{2}:\d{2}', row[key])
    assert re.fullmatch(r'\d+\.\d{3}', row['cycle_hours'])
    for key in ('analyzed_images', 'analyzed_objects', 'sessions_count', 'errors_count'):
        assert re.fullmatch(r'\d+', row[key])


def test_reference_run_row_values(tmp_path: tp.Any) -> None:
    """
    Description:
        The full data row for the realistic reference scenario carries the expected
        values in every column, including the compact per-session and per-error cells.
    """

    Session_Logger, clock, stop_time = _Build_Reference_Run(tmp_path)
    clock.now = stop_time; Session_Logger.Close()

    row = _Read_Rows(Session_Logger.Csv_Path)[0]
    assert row['log_file'] == 'log_2026-09-12_14-37.txt'
    assert row['application_start'] == '2026-09-12 14:37:02'
    assert row['application_stop'] == '2026-09-12 16:12:44'
    assert row['cycle_time'] == '01:35:42'
    assert row['cycle_hours'] == '1.595'
    assert row['analyzed_images'] == '3'
    assert row['analyzed_objects'] == '9'
    assert row['sessions_count'] == '2'
    assert row['total_session_time'] == '01:23:04'
    assert row['idle_time'] == '00:12:38'
    assert row['errors_count'] == '2'
    assert row['total_error_time'] == '00:52:58'
    assert row['session_details'] == '1:14:37:12-14:40:02:00:02:50 | 2:14:52:30-16:12:44:01:20:14'
    assert row['error_details'] == ('1:14:37:34-14:37:49:00:00:15:camera timeout | '
                                    '2:15:20:01-16:12:44:00:52:43:analysis failed on image 233')


def test_zero_activity_row_is_complete(tmp_path: tp.Any) -> None:
    """
    Description:
        A run with zero images, zero sessions and zero errors still produces one full
        row, with zeros and empty detail cells — never a skipped or partial row.
    """

    clock = Clock_Cls(_T('12:16:23'))
    Session_Logger = Session_Logger_Cls(log_dir=str(tmp_path), clock=clock, install_handlers=False)
    clock.now = _T('12:16:29'); Session_Logger.Close()

    rows = _Read_Rows(Session_Logger.Csv_Path)
    assert len(rows) == 1
    row = rows[0]
    assert set(row.keys()) == set(CONST_CSV_COLUMNS)
    assert row['cycle_time'] == '00:00:06'
    assert row['cycle_hours'] == '0.002'
    assert row['analyzed_images'] == '0'
    assert row['analyzed_objects'] == '0'
    assert row['sessions_count'] == '0'
    assert row['total_session_time'] == '00:00:00'
    assert row['idle_time'] == '00:00:06'
    assert row['errors_count'] == '0'
    assert row['total_error_time'] == '00:00:00'
    assert row['session_details'] == ''
    assert row['error_details'] == ''


def test_session_open_at_shutdown_is_counted(tmp_path: tp.Any) -> None:
    """
    Description:
        A session still open at shutdown is counted and its duration measured to the
        stop time; the '.txt' file marks it '(closed at shutdown)'.
    """

    clock = Clock_Cls(_T('12:00:00'))
    Session_Logger = Session_Logger_Cls(log_dir=str(tmp_path), clock=clock, install_handlers=False)
    clock.now = _T('12:00:10'); Session_Logger.Log_Camera_Connected()
    clock.now = _T('12:30:10'); Session_Logger.Close()

    row = _Read_Rows(Session_Logger.Csv_Path)[0]
    assert row['sessions_count'] == '1'
    assert row['total_session_time'] == '00:30:00'
    assert row['session_details'] == '1:12:00:10-12:30:10:00:30:00'

    content = open(Session_Logger.Path, 'r', encoding='utf-8').read()
    assert '(closed at shutdown)' in content


def test_multiple_sessions_total_session_time(tmp_path: tp.Any) -> None:
    """
    Description:
        Multiple sessions in one run each record their own duration, and the CSV's
        total session time is their sum.
    """

    clock = Clock_Cls(_T('10:00:00'))
    Session_Logger = Session_Logger_Cls(log_dir=str(tmp_path), clock=clock, install_handlers=False)
    clock.now = _T('10:00:00'); Session_Logger.Log_Camera_Connected()
    clock.now = _T('10:01:00'); Session_Logger.Log_Camera_Disconnected()    # 60 s
    clock.now = _T('10:05:00'); Session_Logger.Log_Camera_Connected()
    clock.now = _T('10:07:30'); Session_Logger.Log_Camera_Disconnected()    # 150 s
    clock.now = _T('10:10:00'); Session_Logger.Close()

    row = _Read_Rows(Session_Logger.Csv_Path)[0]
    assert row['sessions_count'] == '2'
    assert row['total_session_time'] == '00:03:30'      # 60 + 150 = 210 s


def test_unresolved_error_counted_to_shutdown(tmp_path: tp.Any) -> None:
    """
    Description:
        Errors are counted with a summed total; a resolved error records its downtime
        and an unresolved error's duration is measured up to shutdown.
    """

    clock = Clock_Cls(_T('13:00:00'))
    Session_Logger = Session_Logger_Cls(log_dir=str(tmp_path), clock=clock, install_handlers=False)
    clock.now = _T('13:00:10'); first_id = Session_Logger.Log_Error('camera timeout')
    clock.now = _T('13:00:25'); Session_Logger.Log_Error_Resolved(first_id)   # 15 s
    clock.now = _T('13:01:00'); Session_Logger.Log_Error('analysis failed')    # unresolved
    clock.now = _T('13:02:00'); Session_Logger.Close()                         # unresolved runs 60 s

    assert Session_Logger.Errors[1].Resolved is False
    row = _Read_Rows(Session_Logger.Csv_Path)[0]
    assert row['errors_count'] == '2'
    assert row['total_error_time'] == '00:01:15'        # 15 + 60 = 75 s
    assert row['error_details'] == ('1:13:00:10-13:00:25:00:00:15:camera timeout | '
                                    '2:13:01:00-13:02:00:00:01:00:analysis failed')


def test_idle_time_equals_cycle_minus_session(tmp_path: tp.Any) -> None:
    """
    Description:
        The idle time equals the cycle time minus the total session time.
    """

    Session_Logger, clock, stop_time = _Build_Reference_Run(tmp_path)
    clock.now = stop_time; Session_Logger.Close()

    row = _Read_Rows(Session_Logger.Csv_Path)[0]
    assert (_Hms_To_Seconds(row['idle_time'])
            == _Hms_To_Seconds(row['cycle_time']) - _Hms_To_Seconds(row['total_session_time']))


def test_details_round_trip_with_commas_and_quotes(tmp_path: tp.Any) -> None:
    """
    Description:
        A detail cell round-trips through csv.DictReader unchanged, preserving commas
        and quotes inside an error message; the entry separator is sanitised out of the
        message so it can never be read as a real boundary.
    """

    clock = Clock_Cls(_T('09:00:00'))
    Session_Logger = Session_Logger_Cls(log_dir=str(tmp_path), clock=clock, install_handlers=False)
    clock.now = _T('09:00:10'); Session_Logger.Log_Error('he said "wait, now" | really')
    clock.now = _T('09:00:25'); Session_Logger.Close()

    row = _Read_Rows(Session_Logger.Csv_Path)[0]
    # The comma and the quotes survive; the ' | ' separator inside the message is
    # sanitised to '/' so the packed cell stays unambiguous.
    assert row['error_details'] == '1:09:00:10-09:00:25:00:00:15:he said "wait, now" / really'


def test_semicolon_delimiter_is_configurable(tmp_path: tp.Any) -> None:
    """
    Description:
        The delimiter is configurable; a ';' file (for Excel in a Czech locale) is
        written and read back with the same delimiter.
    """

    clock = Clock_Cls(_T('09:00:00'))
    Session_Logger = Session_Logger_Cls(log_dir=str(tmp_path), clock=clock, install_handlers=False,
                                        csv_delimiter=';')
    clock.now = _T('09:00:06'); Session_Logger.Close()

    assert _Read_Header_Line(Session_Logger.Csv_Path) == ';'.join(CONST_CSV_COLUMNS)
    rows = _Read_Rows(Session_Logger.Csv_Path, delimiter=';')
    assert len(rows) == 1
    assert rows[0]['cycle_time'] == '00:00:06'


def test_csv_row_written_on_exception_exit(tmp_path: tp.Any) -> None:
    """
    Description:
        When the run exits via an unhandled exception, the context manager's Close
        still appends a complete CSV row before the exception propagates.
    """

    clock = Clock_Cls(_T('11:00:00'))
    csv_holder = {}
    with pytest.raises(RuntimeError):
        with Session_Logger_Cls(log_dir=str(tmp_path), clock=clock,
                                install_handlers=False) as Session_Logger:
            csv_holder['path'] = Session_Logger.Csv_Path
            clock.now = _T('11:00:05'); Session_Logger.Log_Camera_Connected()
            clock.now = _T('11:00:10'); Session_Logger.Log_Analysis_Finished(1, 1000, 2, 0, None)
            raise RuntimeError('boom')

    rows = _Read_Rows(csv_holder['path'])
    assert len(rows) == 1
    assert rows[0]['analyzed_images'] == '1'
    assert rows[0]['analyzed_objects'] == '2'
    assert rows[0]['sessions_count'] == '1'


def test_csv_write_failure_is_logged_and_not_raised(tmp_path: tp.Any) -> None:
    """
    Description:
        A CSV write failure (here, a path whose parent is a file, not a directory) is
        logged into the '.txt' file and never raises out of the shutdown path; the
        '.txt' file still closes cleanly, ending with 'Application stopped'.
    """

    blocker = os.path.join(str(tmp_path), 'blocker.txt')
    with open(blocker, 'w', encoding='utf-8') as f:
        f.write('not a directory')
    unreachable_csv = os.path.join(blocker, 'summary.csv')

    clock = Clock_Cls(_T('15:00:00'))
    Session_Logger = Session_Logger_Cls(log_dir=str(tmp_path), clock=clock, install_handlers=False,
                                        csv_filename=unreachable_csv)
    clock.now = _T('15:00:06')
    Session_Logger.Close()   # must not raise

    assert not os.path.exists(unreachable_csv)
    content = open(Session_Logger.Path, 'r', encoding='utf-8').read()
    assert '[ERROR  ] Failed to write the run-summary CSV row' in content
    assert content.rstrip().endswith('Application stopped.')


def test_header_mismatch_row_is_aligned_and_warned(tmp_path: tp.Any) -> None:
    """
    Description:
        When the existing CSV header does not match the current columns, the row is not
        appended misaligned: it is re-ordered to the existing header (columns the header
        does not name are dropped, columns it names but the run does not provide are left
        empty) and a warning is logged into the '.txt' file. This is the documented
        choice over failing loudly.
    """

    clock = Clock_Cls(_T('16:00:00'))
    Session_Logger = Session_Logger_Cls(log_dir=str(tmp_path), clock=clock, install_handlers=False)
    csv_path = Session_Logger.Csv_Path

    # Pre-seed the CSV with a header that differs from the current column set.
    stale_header = ['application_start', 'cycle_time', 'bogus_column']
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        csv.writer(f).writerow(stale_header)

    clock.now = _T('16:00:06'); Session_Logger.Close()

    rows = _Read_Rows(csv_path)
    assert len(rows) == 1
    row = rows[0]
    assert list(row.keys()) == stale_header             # the header was not rewritten
    assert row['application_start'] == '2026-09-12 16:00:00'
    assert row['cycle_time'] == '00:00:06'
    assert row['bogus_column'] == ''                    # named but not provided -> empty

    content = open(Session_Logger.Path, 'r', encoding='utf-8').read()
    assert '[WARNING] The run-summary CSV header does not match the current columns' in content


def test_txt_has_no_run_summary_block(tmp_path: tp.Any) -> None:
    """
    Description:
        The '.txt' file keeps only the chronological event lines and ends with the
        'Application stopped' line — the 'RUN SUMMARY' block is gone.
    """

    Session_Logger, clock, stop_time = _Build_Reference_Run(tmp_path)
    clock.now = stop_time; Session_Logger.Close()

    content = open(Session_Logger.Path, 'r', encoding='utf-8').read()
    assert 'RUN SUMMARY' not in content
    assert 'Camera connected. Session 1 started.' in content
    assert content.rstrip().endswith('Application stopped.')


def test_line_sink_receives_separated_fields_and_the_matching_line(tmp_path: tp.Any) -> None:
    """
    Description:
        The sink is handed each line's fields ALREADY SEPARATED (a Log_Line_Str) plus the
        formatted line — so a live reader renders the fields it was given and never parses. The
        record's fields are the real ones, Parsed is True, and the accompanying string equals
        the file line without its trailing newline (one formatter, no drift). A line logged
        before the sink is attached does not reach it (the file seeds those); every line after
        does.
    """

    clock = Clock_Cls(_T('08:00:00'))
    Session_Logger = Session_Logger_Cls(log_dir=str(tmp_path), clock=clock,
                                        install_handlers=False)
    received = []

    Session_Logger.Log_Info('Before the sink is attached.')      # seeds the file only
    Session_Logger.Set_Line_Sink(lambda record, line: received.append((record, line)))
    Session_Logger.Log_Info('After the sink is attached.')
    Session_Logger.Log_Warning('A warning.')

    # The record carries the separated fields (not a string to be parsed), marked trustworthy.
    (info_rec, info_line), (warn_rec, warn_line) = received
    assert (info_rec.Date, info_rec.Time, info_rec.Level, info_rec.Message, info_rec.Parsed) == \
        ('2026-09-12', '08:00:00', CONST_LEVEL_INFO, 'After the sink is attached.', True)
    assert warn_rec.Level == CONST_LEVEL_WARNING and warn_rec.Message == 'A warning.'

    # The accompanying line equals the file line without the trailing newline (same string).
    file_lines = open(Session_Logger.Path, 'r', encoding='utf-8').read().splitlines()
    assert info_line in file_lines and warn_line in file_lines
    assert info_line == '2026-09-12 08:00:00 [INFO   ] After the sink is attached.'


def test_a_sink_failure_never_prevents_the_write_to_disk(tmp_path: tp.Any) -> None:
    """
    Description:
        The sink is wrapped: a sink that raises on every call must not stop the line reaching
        the file. This is the guarantee that a rendering fault in the live view can never cost
        a logged line on disk.
    """

    clock = Clock_Cls(_T('09:15:00'))
    Session_Logger = Session_Logger_Cls(log_dir=str(tmp_path), clock=clock,
                                        install_handlers=False)

    def _Explode(_record, _line) -> None:
        raise RuntimeError('the view blew up')

    Session_Logger.Set_Line_Sink(_Explode)
    Session_Logger.Log_Info('This must still reach the file.')   # must not raise
    Session_Logger.Log_Error('And so must this.')               # must not raise

    content = open(Session_Logger.Path, 'r', encoding='utf-8').read()
    assert 'This must still reach the file.' in content
    assert 'And so must this.' in content


def test_parse_line_round_trips_real_lines(tmp_path: tp.Any) -> None:
    """
    Description:
        Parse_Line splits a written line back into its fields — the inverse of the one
        formatter, used only to seed the view from the file. Checked against real lines the
        logger produced, including an error line whose message carries its own '(error_id=N)'.
    """

    clock = Clock_Cls(_T('10:20:30'))
    Session_Logger = Session_Logger_Cls(log_dir=str(tmp_path), clock=clock,
                                        install_handlers=False)
    Session_Logger.Log_Info('A plain event.')
    Session_Logger.Log_Warning('Careful now.')
    Session_Logger.Log_Error('Backend timed out')
    Session_Logger.Close()

    lines = open(Session_Logger.Path, 'r', encoding='utf-8').read().splitlines()
    info = Parse_Line(lines[0])
    assert (info.Date, info.Time, info.Level, info.Message, info.Parsed) == \
        ('2026-09-12', '10:20:30', CONST_LEVEL_INFO, 'A plain event.', True)
    assert Parse_Line(lines[1]).Level == CONST_LEVEL_WARNING
    error = Parse_Line(lines[2])
    assert error.Level == CONST_LEVEL_ERROR and error.Message == 'Backend timed out (error_id=1)'


def test_parse_line_never_mis_splits_hostile_messages() -> None:
    """
    Description:
        The seed file holds text the application does not control — Florence captions, driver
        error strings, file paths, audit lines quoting arbitrary caption text. Parse_Line must
        never mis-split any of it. A real line's fields survive even when the MESSAGE contains
        the delimiters or a level-shaped token; anything that is not a real line (no timestamp,
        or a bracketed word that is not a real level) is returned whole with Parsed=False, so
        the view renders it raw rather than guessing. Nothing is ever dropped.
    """

    # A real INFO line whose message itself contains a level-shaped bracket sequence and the
    # '] ' delimiter: the split happens at the FIRST real delimiters, so the message survives.
    record = Parse_Line('2026-09-12 10:00:00 [INFO   ] stripped "[WARNING] on a table" -> ok')
    assert record.Parsed and record.Level == CONST_LEVEL_INFO
    assert record.Message == 'stripped "[WARNING] on a table" -> ok'

    # A message that is a bare bracketed level with no timestamp is NOT a line — Parsed False,
    # kept whole, so it is never mistaken for an ERROR row.
    hostile = Parse_Line('[ERROR] the caption literally said this')
    assert not hostile.Parsed and hostile.Level == ''
    assert hostile.Message == '[ERROR] the caption literally said this'

    # A file path with a ' [' and a '] ' is not a line — kept whole, not split into fields.
    path = Parse_Line('/var/log/cam [old] /backup.txt was rotated')
    assert not path.Parsed and path.Message == '/var/log/cam [old] /backup.txt was rotated'

    # A bracketed token that is not one of the real levels is not a level, even after a
    # timestamp-shaped prefix — kept whole rather than inventing a 'DEBUG' severity.
    unknown = Parse_Line('2026-09-12 10:00:00 [DEBUG  ] not a real level')
    assert not unknown.Parsed and unknown.Level == ''

    # An empty message on a real line stays a parsed line with an empty message.
    empty = Parse_Line('2026-09-12 10:00:00 [INFO   ] ')
    assert empty.Parsed and empty.Level == CONST_LEVEL_INFO and empty.Message == ''

    # A wrapped continuation of a multi-line message (no timestamp) is kept whole and muted-
    # rendered by the view; it is never dropped.
    cont = Parse_Line('    ...continued stack frame with no timestamp')
    assert not cont.Parsed and cont.Message == '    ...continued stack frame with no timestamp'


def test_multi_line_message_seeds_as_a_parsed_head_and_raw_continuations() -> None:
    """
    Description:
        A message containing newlines is written as several physical lines; on seeding, the
        first is a normal parsed line and each continuation is kept whole with Parsed=False.
        The view renders the head as a level row and the continuations raw and muted — nothing
        is dropped or mis-attributed.
    """

    written = '2026-09-12 10:00:00 [ERROR  ] first line\nsecond line\nthird line'
    physical = written.split('\n')
    head = Parse_Line(physical[0])
    assert head.Parsed and head.Level == CONST_LEVEL_ERROR and head.Message == 'first line'
    for continuation in physical[1:]:
        parsed = Parse_Line(continuation)
        assert not parsed.Parsed and parsed.Message == continuation
