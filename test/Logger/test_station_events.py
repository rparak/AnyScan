## =========================================================================== ##
# MIT License
# Copyright (c) 2026 JIC Smart Factory
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
# File Name: ../test/Logger/test_station_events.py
## =========================================================================== ##

# System (Default)
import os
import re
from datetime import datetime
# Zoneinfo (IANA time zones) [Python standard library]
from zoneinfo import ZoneInfo
# Typing (Support for type hints)
import typing as tp
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan — the session logger that writes the events, and the export under test
#   ../Logger/Core
from Logger.Core import Session_Logger_Cls
#   ../Logger/Station_Events
from Logger.Station_Events import (Read_Events, Export_Log, Export_Pending, Ledger_Path, Station_Events_Error_Cls,
                                   CONST_LEDGER_FILENAME)

"""
Description:
    Tests for the daily station event export. Every log is written by the real Session_Logger_Cls on an
    injected clock, so the events come from the logger's own lines and markers, and every row is read
    back from the file on disk. Times convert under Europe/Prague's rules (CEST +2 in summer, CET +1 in
    winter), the station's own zone.
"""
# The zone whose rules the tests convert under.
#   Unit [ZoneInfo(object)]
CONST_ZONE = ZoneInfo('Europe/Prague')
# The header line of a daily file.
#   Unit [string]
CONST_HEADER = 'station_id,event_type,ts'


class _Clock_Cls(object):
    """A settable clock for the logger."""

    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def _Run(log_dir: tp.Any, steps: tp.List[tp.Tuple[str, str]], close: bool = True) -> Session_Logger_Cls:
    """
    A run of the real logger: it starts at the first step's time, then performs each (time, action) —
    'connect', 'disconnect', 'lost' or 'stop' — on the clock. Times are 'YYYY-MM-DD HH:MM:SS', local.
    """
    clock = _Clock_Cls(datetime.strptime(steps[0][0], '%Y-%m-%d %H:%M:%S'))
    logger = Session_Logger_Cls(config_path=None, log_dir=str(log_dir), clock=clock, install_handlers=False,
                                csv_filename=os.path.join(str(log_dir), 'summary.csv'))
    for stamp, action in steps[1:]:
        clock.now = datetime.strptime(stamp, '%Y-%m-%d %H:%M:%S')
        {'connect': lambda: logger.Log_Camera_Connected(),
         'disconnect': lambda: logger.Log_Camera_Disconnected(),
         'lost': lambda: logger.Log_Camera_Connection_Lost('gone'),
         'stop': logger.Close}[action]()
    if close and steps[-1][1] != 'stop':
        logger.Close()
    return logger


def _Crash(logger: Session_Logger_Cls) -> None:
    """The process dies: the log's handle goes (and with it the lock) without Close."""
    getattr(logger, '_Session_Logger_Cls__file').close()


def _Lines(path: str) -> tp.List[str]:
    """A daily file's lines, exactly as on disk (newline-terminated)."""
    with open(path, 'r', encoding='utf-8', newline='') as handle:
        return handle.read().split('\n')


def test_a_new_file_gets_the_header_and_utc_rows_to_the_second(tmp_path) -> None:
    """
    Description:
        A date with no file yet gets one, starting with the header; each row is 'SF4,<event>,<ts>' with
        ts the UTC instant to the second ('2026-09-25T05:33:45Z' for 07:33:45 CEST), lines ending '\\n'.
    """

    events = tmp_path / 'events'
    events.mkdir()
    logger = _Run(tmp_path, [('2026-09-25 07:33:45', ''), ('2026-09-25 07:42:39', 'connect'),
                             ('2026-09-25 07:52:10', 'disconnect'), ('2026-09-25 15:02:11', 'stop')])
    assert Export_Log(logger.Path, str(events), CONST_ZONE) == 4
    assert _Lines(str(events / '2026-09-25.csv')) == [
        CONST_HEADER, 'SF4,STATION_ON,2026-09-25T05:33:45Z', 'SF4,CYCLE_START,2026-09-25T05:42:39Z',
        'SF4,CYCLE_DONE,2026-09-25T05:52:10Z', 'SF4,STATION_OFF,2026-09-25T13:02:11Z', '']
    with open(str(events / '2026-09-25.csv'), 'rb') as handle:
        assert not handle.read().startswith(b'\xef\xbb\xbf')                  # UTF-8, no byte-order mark
    for line in _Lines(str(events / '2026-09-25.csv'))[1:-1]:
        assert re.fullmatch(r'SF4,[A-Z_]+,\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', line)


def test_an_existing_file_is_appended_to_in_order_without_a_second_header(tmp_path) -> None:
    """
    Description:
        A second run on the same date appends after the first run's rows, in the order they happened,
        and the file keeps its one header.
    """

    events = tmp_path / 'events'
    events.mkdir()
    first = _Run(tmp_path / 'a', [('2026-09-25 07:00:00', ''), ('2026-09-25 08:00:00', 'stop')])
    second = _Run(tmp_path / 'b', [('2026-09-25 09:00:00', ''), ('2026-09-25 09:10:00', 'connect'),
                                   ('2026-09-25 09:20:00', 'stop')])
    Export_Log(first.Path, str(events), CONST_ZONE)
    Export_Log(second.Path, str(events), CONST_ZONE)
    assert _Lines(str(events / '2026-09-25.csv')) == [
        CONST_HEADER, 'SF4,STATION_ON,2026-09-25T05:00:00Z', 'SF4,STATION_OFF,2026-09-25T06:00:00Z',
        'SF4,STATION_ON,2026-09-25T07:00:00Z', 'SF4,CYCLE_START,2026-09-25T07:10:00Z',
        'SF4,CYCLE_DONE,2026-09-25T07:20:00Z', 'SF4,STATION_OFF,2026-09-25T07:20:00Z', '']


def test_every_way_a_connection_ends_closes_its_cycle_and_closing_ends_it_before_station_off(tmp_path) -> None:
    """
    Description:
        The events come from the logger's markers, so each logger line that opens or closes the run or a
        connection must keep its marker — reword one without it and this fails. Every way a connection
        ends writes CYCLE_DONE: DISCONNECT, a lost connection, a CONNECT over an open connection, and
        closing while connected — that last one BEFORE STATION_OFF. A DISCONNECT or a loss with no
        connection open, and a message quoting a marker mid-sentence, are not events.
    """

    clock = _Clock_Cls(datetime(2026, 9, 25, 8, 0, 0))
    logger = Session_Logger_Cls(config_path=None, log_dir=str(tmp_path), clock=clock, install_handlers=False,
                                csv_filename=os.path.join(str(tmp_path), 'summary.csv'))
    logger.Log_Camera_Connected()
    logger.Log_Camera_Disconnected()                       # DISCONNECT
    logger.Log_Camera_Disconnected()                       # nothing open: no event
    logger.Log_Camera_Connected()
    logger.Log_Camera_Connected()                          # CONNECT over an open connection
    logger.Log_Camera_Connection_Lost('gone')              # lost
    logger.Log_Camera_Connection_Lost('gone again')        # nothing open: no event
    logger.Log_Info('The #run-stop marker is quoted here, mid-sentence.')
    logger.Log_Camera_Connected()
    logger.Close()                                         # closed while connected
    assert [event.Event_Type for event in Read_Events(logger.Path, CONST_ZONE)] == [
        'STATION_ON', 'CYCLE_START', 'CYCLE_DONE', 'CYCLE_START', 'CYCLE_DONE', 'CYCLE_START', 'CYCLE_DONE',
        'CYCLE_START', 'CYCLE_DONE', 'STATION_OFF']


def test_a_run_crossing_midnight_puts_each_row_in_the_file_of_its_own_local_date(tmp_path) -> None:
    """
    Description:
        A run and a cycle that start before local midnight and end after it are split by the rule —
        each row in the file of its own LOCAL date — so the CYCLE_START is in one file and its
        CYCLE_DONE in the next. Near midnight a row's UTC ts carries the PREVIOUS date from its file's
        name (00:00:10 CEST is 22:00:10Z the day before): the recorded consequence of a local file name
        with UTC timestamps.
    """

    events = tmp_path / 'events'
    events.mkdir()
    logger = _Run(tmp_path, [('2026-09-25 23:59:50', ''), ('2026-09-25 23:59:55', 'connect'),
                             ('2026-09-26 00:00:10', 'disconnect'), ('2026-09-26 00:00:20', 'stop')])
    Export_Log(logger.Path, str(events), CONST_ZONE)
    assert _Lines(str(events / '2026-09-25.csv')) == [
        CONST_HEADER, 'SF4,STATION_ON,2026-09-25T21:59:50Z', 'SF4,CYCLE_START,2026-09-25T21:59:55Z', '']
    assert _Lines(str(events / '2026-09-26.csv')) == [
        CONST_HEADER, 'SF4,CYCLE_DONE,2026-09-25T22:00:10Z', 'SF4,STATION_OFF,2026-09-25T22:00:20Z', '']


def test_the_repeated_hour_when_summer_time_ends_is_read_as_its_first_pass(tmp_path) -> None:
    """
    Description:
        On 2026-10-25 Prague's clocks go from 03:00 CEST back to 02:00 CET, so 02:00-03:00 local
        happens twice and the log, which stores no zone, cannot tell the passes apart. A log time in
        that hour is read as its first, summer-time pass: 02:30 is 00:30Z (not 01:30Z). Just outside
        the hour the reading is unambiguous: 01:59:59 is 23:59:59Z and 03:00:00 is 02:00:00Z.
    """

    events = tmp_path / 'events'
    events.mkdir()
    logger = _Run(tmp_path, [('2026-10-25 01:59:59', ''), ('2026-10-25 02:30:00', 'connect'),
                             ('2026-10-25 03:00:00', 'stop')])
    Export_Log(logger.Path, str(events), CONST_ZONE)
    assert _Lines(str(events / '2026-10-25.csv')) == [
        CONST_HEADER, 'SF4,STATION_ON,2026-10-24T23:59:59Z', 'SF4,CYCLE_START,2026-10-25T00:30:00Z',
        'SF4,CYCLE_DONE,2026-10-25T02:00:00Z', 'SF4,STATION_OFF,2026-10-25T02:00:00Z', '']


def test_a_crashed_run_is_exported_at_the_next_start_with_its_pairs_unclosed(tmp_path) -> None:
    """
    Description:
        A run killed while connected never closes, so it exports nothing itself. The next start exports
        it — what it recorded and nothing invented: STATION_ON and CYCLE_START with no CYCLE_DONE and no
        STATION_OFF, the unpaired rows that mean an abnormal exit. The new run's own log is not exported
        at startup; it is exported at its own close.
    """

    events = tmp_path / 'events'
    events.mkdir()
    Export_Pending(str(tmp_path), str(events), '', CONST_ZONE)        # an empty ledger: nothing earlier
    crashed = _Run(tmp_path, [('2026-09-25 07:00:00', ''), ('2026-09-25 07:05:00', 'connect')], close=False)
    _Crash(crashed)
    current = _Run(tmp_path, [('2026-09-25 09:00:00', '')], close=False)
    Pending_Export_Str = Export_Pending(str(tmp_path), str(events), current.Path, CONST_ZONE)
    assert Pending_Export_Str.Exported == [os.path.basename(crashed.Path)]
    assert Pending_Export_Str.Failed == [] and Pending_Export_Str.Live == []
    assert _Lines(str(events / '2026-09-25.csv')) == [
        CONST_HEADER, 'SF4,STATION_ON,2026-09-25T05:00:00Z', 'SF4,CYCLE_START,2026-09-25T05:05:00Z', '']
    current.Close()


def test_a_log_another_running_instance_holds_is_left_to_it(tmp_path) -> None:
    """
    Description:
        A second instance's log is still open and locked: it is not a crashed run, so the startup export
        leaves it — and leaves it out of the ledger — for that instance to export at its close.
    """

    events = tmp_path / 'events'
    events.mkdir()
    Export_Pending(str(tmp_path), str(events), '', CONST_ZONE)
    other = _Run(tmp_path, [('2026-09-25 07:00:00', '')], close=False)
    Pending_Export_Str = Export_Pending(str(tmp_path), str(events), 'log_this_run.txt', CONST_ZONE)
    assert Pending_Export_Str.Live == [os.path.basename(other.Path)] and Pending_Export_Str.Exported == []
    assert not os.path.exists(str(events / '2026-09-25.csv'))
    assert os.path.basename(other.Path) not in open(Ledger_Path(str(tmp_path)), encoding='utf-8').read()
    other.Close()


def test_no_log_is_exported_twice(tmp_path) -> None:
    """
    Description:
        A log exported at its close is in the ledger, so the next start does not export it again, and
        a log exported at startup is not exported by the start after it either: each row is on disk once.
    """

    events = tmp_path / 'events'
    events.mkdir()
    Export_Pending(str(tmp_path), str(events), '', CONST_ZONE)
    closed = _Run(tmp_path, [('2026-09-25 07:00:00', '')], close=False)
    closed.Set_Close_Callback(lambda path: Export_Log(path, str(events), CONST_ZONE))
    closed.Close()
    crashed = _Run(tmp_path, [('2026-09-25 08:00:00', '')], close=False)
    _Crash(crashed)
    for start in ('log_next.txt', 'log_after_that.txt'):
        Export_Pending(str(tmp_path), str(events), start, CONST_ZONE)
    assert _Lines(str(events / '2026-09-25.csv')) == [
        CONST_HEADER, 'SF4,STATION_ON,2026-09-25T05:00:00Z', 'SF4,STATION_OFF,2026-09-25T05:00:00Z',
        'SF4,STATION_ON,2026-09-25T06:00:00Z', '']


def test_a_failed_export_is_left_out_of_the_ledger_and_the_next_start_exports_it_once(tmp_path) -> None:
    """
    Description:
        The directory is gone when the run closes (a share unmounted): the export fails with a sentence
        naming the log and the directory, no row is written, and the log is NOT in the ledger. Once the
        directory is back, the next start exports it, and the start after that does not again.
    """

    events = tmp_path / 'events'
    Export_Pending(str(tmp_path), str(tmp_path), '', CONST_ZONE)
    logger = _Run(tmp_path, [('2026-09-25 07:00:00', ''), ('2026-09-25 07:30:00', 'stop')])
    with pytest.raises(Station_Events_Error_Cls, match='could not be exported to %s' % re.escape(str(events))):
        Export_Log(logger.Path, str(events), CONST_ZONE)
    assert os.path.basename(logger.Path) not in open(Ledger_Path(str(tmp_path)), encoding='utf-8').read()

    events.mkdir()
    for start in ('log_next.txt', 'log_after_that.txt'):
        Export_Pending(str(tmp_path), str(events), start, CONST_ZONE)
    assert _Lines(str(events / '2026-09-25.csv')) == [
        CONST_HEADER, 'SF4,STATION_ON,2026-09-25T05:00:00Z', 'SF4,STATION_OFF,2026-09-25T05:30:00Z', '']


def test_a_failure_at_startup_is_reported_per_log_and_the_others_still_export(tmp_path) -> None:
    """
    Description:
        At startup an earlier log that cannot be exported is reported (the caller logs it as an ERROR)
        and stays out of the ledger; the export of the others is not stopped by it.
    """

    events = tmp_path / 'events'
    events.mkdir()
    Export_Pending(str(tmp_path), str(events), '', CONST_ZONE)
    first = _Run(tmp_path, [('2026-09-25 07:00:00', '')])
    second = _Run(tmp_path, [('2026-09-25 08:00:00', '')])
    os.chmod(first.Path, 0o000)                                       # unreadable
    try:
        Pending_Export_Str = Export_Pending(str(tmp_path), str(events), 'log_now.txt', CONST_ZONE)
    finally:
        os.chmod(first.Path, 0o644)
    ((name, message),) = Pending_Export_Str.Failed
    assert name == os.path.basename(first.Path) and 'retried at the next start' in message
    assert Pending_Export_Str.Exported == [os.path.basename(second.Path)]
    assert name not in open(Ledger_Path(str(tmp_path)), encoding='utf-8').read()


def test_the_first_start_records_the_logs_already_there_without_exporting_them(tmp_path) -> None:
    """
    Description:
        With no ledger yet, the logs already in the directory (older than the markers, or simply before
        this version) are recorded as handled, not exported: the export history starts here. A log that
        appears after that is exported as usual.
    """

    events = tmp_path / 'events'
    events.mkdir()
    old = [_Run(tmp_path, [('2026-09-20 07:00:00', '')]), _Run(tmp_path, [('2026-09-21 07:00:00', '')])]
    current = _Run(tmp_path, [('2026-09-25 07:00:00', '')], close=False)
    Pending_Export_Str = Export_Pending(str(tmp_path), str(events), current.Path, CONST_ZONE)
    assert Pending_Export_Str.Baselined == 2 and Pending_Export_Str.Exported == []
    assert os.listdir(str(events)) == []
    with open(os.path.join(str(tmp_path), CONST_LEDGER_FILENAME), encoding='utf-8') as ledger:
        assert ledger.read().split() == [os.path.basename(logger.Path) for logger in old]
    current.Close()
    assert Export_Pending(str(tmp_path), str(events), 'log_next.txt', CONST_ZONE).Exported == \
        [os.path.basename(current.Path)]
