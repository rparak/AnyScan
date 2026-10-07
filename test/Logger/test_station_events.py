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
import csv
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

    A cycle is a scan (or a re-analysis) to the end of its analysis (Logger.Core.Cycles). The cycle tests
    read the cycles twice — from the daily rows and from the run-summary CSV's total_session_time — and
    hold both to the same hand-counted expectation.
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
    A run of the real logger: it starts at the first step's time, then performs each (time, action) on the
    clock — 'connect', 'disconnect', 'lost', 'scan' (SCAN pressed), 'scanned' (its capture succeeded),
    'scan failed', 'analyse' (an analysis starts), 'analysed' (it finished), 'analysis failed' or 'stop'.
    Times are 'YYYY-MM-DD HH:MM:SS', local, or 'HH:MM:SS' on the first step's date.
    """
    day = steps[0][0][:10]
    clock = _Clock_Cls(datetime.strptime(steps[0][0], '%Y-%m-%d %H:%M:%S'))
    logger = Session_Logger_Cls(config_path=None, log_dir=str(log_dir), clock=clock, install_handlers=False,
                                csv_filename=os.path.join(str(log_dir), 'summary.csv'))
    actions = {'connect': lambda: logger.Log_Camera_Connected(),
               'disconnect': lambda: logger.Log_Camera_Disconnected(),
               'lost': lambda: logger.Log_Camera_Connection_Lost('gone'),
               'scan': lambda: logger.Log_Scan_Started(),
               'scanned': lambda: logger.Log_Scan_Ended(),
               'scan failed': lambda: logger.Log_Scan_Failed(),
               'analyse': lambda: logger.Log_Analysis_Started(1, 'set'),
               'analysed': lambda: logger.Log_Analysis_Finished(1, 1000, 0, 0, None, 'set'),
               'analysis failed': lambda: logger.Log_Analysis_Failed(1, 'set'),
               'stop': logger.Close}
    for stamp, action in steps[1:]:
        clock.now = datetime.strptime(stamp if len(stamp) > 8 else '%s %s' % (day, stamp), '%Y-%m-%d %H:%M:%S')
        actions[action]()
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


def _Cycles(logger: Session_Logger_Cls) -> tp.List[tp.Tuple[str, str]]:
    """The log's CYCLE_START / CYCLE_DONE events as (type, local 'HH:MM:SS'), in order."""
    return [(event.Event_Type, event.Local.strftime('%H:%M:%S')) for event in Read_Events(logger.Path, CONST_ZONE)
            if event.Event_Type.startswith('CYCLE_')]


def _Session_Time(logger: Session_Logger_Cls) -> str:
    """The run-summary CSV's total_session_time for the run (its one row)."""
    with open(logger.Csv_Path, 'r', newline='', encoding='utf-8-sig') as handle:
        (row,) = list(csv.DictReader(handle))
    return row['total_session_time']


def test_a_new_file_gets_the_header_and_utc_rows_to_the_second(tmp_path) -> None:
    """
    Description:
        A date with no file yet gets one, starting with the header; each row is 'SF4,<event>,<ts>' with
        ts the UTC instant to the second ('2026-09-25T05:33:45Z' for 07:33:45 CEST), lines ending '\\n'.
    """

    events = tmp_path / 'events'
    events.mkdir()
    logger = _Run(tmp_path, [('2026-09-25 07:33:45', ''), ('07:42:39', 'scan'), ('07:42:40', 'scanned'),
                             ('07:42:41', 'analyse'), ('07:52:10', 'analysed'), ('15:02:11', 'stop')])
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
    first = _Run(tmp_path / 'a', [('2026-09-25 07:00:00', ''), ('08:00:00', 'stop')])
    second = _Run(tmp_path / 'b', [('2026-09-25 09:00:00', ''), ('09:10:00', 'scan'), ('09:10:01', 'scanned'),
                                   ('09:10:02', 'analyse'), ('09:20:00', 'analysed'), ('09:20:00', 'stop')])
    Export_Log(first.Path, str(events), CONST_ZONE)
    Export_Log(second.Path, str(events), CONST_ZONE)
    assert _Lines(str(events / '2026-09-25.csv')) == [
        CONST_HEADER, 'SF4,STATION_ON,2026-09-25T05:00:00Z', 'SF4,STATION_OFF,2026-09-25T06:00:00Z',
        'SF4,STATION_ON,2026-09-25T07:00:00Z', 'SF4,CYCLE_START,2026-09-25T07:10:00Z',
        'SF4,CYCLE_DONE,2026-09-25T07:20:00Z', 'SF4,STATION_OFF,2026-09-25T07:20:00Z', '']


def test_a_camera_connection_is_no_cycle_and_a_quoted_marker_is_no_event(tmp_path) -> None:
    """
    Description:
        Since 2026-10-07 a connection defines no cycle: CONNECT, DISCONNECT, a lost connection, a CONNECT
        over an open connection and closing while connected write no CYCLE row and add nothing to
        total_session_time. A message quoting a marker mid-sentence is not an event.
    """

    logger = _Run(tmp_path, [('2026-09-25 08:00:00', ''), ('08:00:05', 'connect'), ('08:01:00', 'disconnect'),
                             ('08:02:00', 'connect'), ('08:03:00', 'connect'), ('08:04:00', 'lost'),
                             ('08:05:00', 'connect')], close=False)
    logger.Log_Info('The #run-stop and #scan-start markers are quoted here, mid-sentence.')
    logger.Close()
    assert [event.Event_Type for event in Read_Events(logger.Path, CONST_ZONE)] == ['STATION_ON', 'STATION_OFF']
    assert _Session_Time(logger) == '00:00:00'


def test_several_scans_each_close_their_own_cycle_and_are_summed(tmp_path) -> None:
    """
    Description:
        Each scan and its analysis is one cycle, from SCAN to the end of the analysis — the wait before
        Analyze included — and total_session_time is their sum: 60 s + 30 s.
    """

    logger = _Run(tmp_path, [('2026-09-25 08:00:00', ''),
                             ('08:01:00', 'scan'), ('08:01:02', 'scanned'), ('08:01:05', 'analyse'), ('08:02:00', 'analysed'),
                             ('08:10:00', 'scan'), ('08:10:02', 'scanned'), ('08:10:03', 'analyse'), ('08:10:30', 'analysed'),
                             ('08:20:00', 'stop')])
    assert _Cycles(logger) == [('CYCLE_START', '08:01:00'), ('CYCLE_DONE', '08:02:00'),
                               ('CYCLE_START', '08:10:00'), ('CYCLE_DONE', '08:10:30')]
    assert _Session_Time(logger) == '00:01:30'


def test_a_failed_analysis_closes_its_cycle_at_the_failure(tmp_path) -> None:
    """
    Description:
        An analysis that fails still ends its cycle, at the failure: the station was working.
    """

    logger = _Run(tmp_path, [('2026-09-25 08:00:00', ''), ('08:01:00', 'scan'), ('08:01:02', 'scanned'),
                             ('08:01:03', 'analyse'), ('08:01:40', 'analysis failed'), ('08:30:00', 'stop')])
    assert _Cycles(logger) == [('CYCLE_START', '08:01:00'), ('CYCLE_DONE', '08:01:40')]
    assert _Session_Time(logger) == '00:00:40'


@pytest.mark.parametrize('after, cycles, session_time', [
    ([('08:30:00', 'scan'), ('08:30:02', 'scanned'), ('08:30:03', 'analyse'), ('08:30:10', 'analysed')],
     [('CYCLE_START', '08:30:00'), ('CYCLE_DONE', '08:30:10')], '00:00:14'),
    ([('08:30:00', 'disconnect')], [], '00:00:04'),
    ([('08:30:00', 'lost')], [], '00:00:04'),
    ([], [], '00:00:04'),
], ids=['next SCAN', 'DISCONNECT', 'lost connection', 'close'])
def test_a_scan_never_analysed_ends_at_the_end_of_its_capture(tmp_path, after, cycles, session_time) -> None:
    """
    Description:
        A scan whose frame is never analysed is a cycle from SCAN to the END OF ITS CAPTURE (4 s), whatever
        comes next — another SCAN, DISCONNECT, a lost connection or closing the application half an hour
        later: the time after the capture is the operator's, not the station's.
    """

    logger = _Run(tmp_path, [('2026-09-25 08:00:00', ''), ('08:00:30', 'connect'), ('08:01:00', 'scan'),
                             ('08:01:04', 'scanned')] + after + [('09:00:00', 'stop')])
    assert _Cycles(logger) == [('CYCLE_START', '08:01:00'), ('CYCLE_DONE', '08:01:04')] + cycles
    assert _Session_Time(logger) == session_time


def test_a_failed_capture_ends_its_cycle_at_the_failure(tmp_path) -> None:
    """
    Description:
        A capture that fails — a transient error, or the cable pulled during the grab, which is where a
        lost connection ends a cycle — closes the cycle at the failure. The frame held from the scan
        before is kept, and analysing it again opens a cycle at the analysis's own start.
    """

    logger = _Run(tmp_path, [('2026-09-25 08:00:00', ''),
                             ('08:01:00', 'scan'), ('08:01:02', 'scanned'), ('08:01:03', 'analyse'), ('08:01:10', 'analysed'),
                             ('08:05:00', 'scan'), ('08:05:03', 'scan failed'), ('08:05:03', 'lost'),
                             ('08:06:00', 'analyse'), ('08:06:20', 'analysed'), ('08:30:00', 'stop')])
    assert _Cycles(logger) == [('CYCLE_START', '08:01:00'), ('CYCLE_DONE', '08:01:10'),
                               ('CYCLE_START', '08:05:00'), ('CYCLE_DONE', '08:05:03'),
                               ('CYCLE_START', '08:06:00'), ('CYCLE_DONE', '08:06:20')]
    assert _Session_Time(logger) == '00:00:33'


def test_a_re_analysis_opens_its_own_cycle_at_its_start(tmp_path) -> None:
    """
    Description:
        Analysing the same frame again is real work with no scan of its own: it is a cycle from the
        analysis's start to its end, and the time between the two analyses is idle.
    """

    logger = _Run(tmp_path, [('2026-09-25 08:00:00', ''),
                             ('08:01:00', 'scan'), ('08:01:02', 'scanned'), ('08:01:03', 'analyse'), ('08:01:10', 'analysed'),
                             ('08:03:00', 'analyse'), ('08:03:15', 'analysed'), ('08:30:00', 'stop')])
    assert _Cycles(logger) == [('CYCLE_START', '08:01:00'), ('CYCLE_DONE', '08:01:10'),
                               ('CYCLE_START', '08:03:00'), ('CYCLE_DONE', '08:03:15')]
    assert _Session_Time(logger) == '00:00:25'


def test_a_lost_connection_does_not_cut_a_cycle_and_a_kept_frame_still_pairs_with_its_scan(tmp_path) -> None:
    """
    Description:
        A connection lost while an analysis runs does not stop it, so its cycle ends when it does (50 s).
        A frame scanned before a loss is kept, and analysing it later closes ITS scan's cycle — from the
        scan through the loss to the end of the analysis (9 min 30 s).
    """

    logger = _Run(tmp_path, [('2026-09-25 08:00:00', ''), ('08:00:30', 'connect'),
                             ('08:01:00', 'scan'), ('08:01:02', 'scanned'), ('08:01:03', 'analyse'), ('08:01:20', 'lost'),
                             ('08:01:50', 'analysed'),
                             ('08:02:00', 'connect'), ('08:03:00', 'scan'), ('08:03:02', 'scanned'), ('08:05:00', 'lost'),
                             ('08:12:00', 'analyse'), ('08:12:30', 'analysed'), ('08:30:00', 'stop')])
    assert _Cycles(logger) == [('CYCLE_START', '08:01:00'), ('CYCLE_DONE', '08:01:50'),
                               ('CYCLE_START', '08:03:00'), ('CYCLE_DONE', '08:12:30')]
    assert _Session_Time(logger) == '00:10:20'


def test_closing_during_an_analysis_cuts_its_cycle_at_the_close_before_station_off(tmp_path) -> None:
    """
    Description:
        The application is closed while an analysis runs: its cycle ends at the close, and its CYCLE_DONE
        comes before STATION_OFF.
    """

    logger = _Run(tmp_path, [('2026-09-25 08:00:00', ''), ('08:01:00', 'scan'), ('08:01:02', 'scanned'),
                             ('08:01:03', 'analyse'), ('08:01:30', 'stop')])
    assert [(event.Event_Type, event.Local.strftime('%H:%M:%S')) for event in Read_Events(logger.Path, CONST_ZONE)] \
        == [('STATION_ON', '08:00:00'), ('CYCLE_START', '08:01:00'), ('CYCLE_DONE', '08:01:30'),
            ('STATION_OFF', '08:01:30')]
    assert _Session_Time(logger) == '00:00:30'


def test_the_daily_files_cycles_sum_to_the_run_summarys_total_session_time(tmp_path) -> None:
    """
    Description:
        The two files describe the same work from one definition: for a session with several scans, a
        failed analysis, a scan never analysed, a re-analysis, a failed capture, a loss during an analysis
        and a close during one — on a clock with sub-second parts — the CYCLE_DONE - CYCLE_START sums read
        back from the exported daily file equal the CSV's total_session_time, and both are the 191 s
        counted by hand (60 + 40 + 2 + 15 + 3 + 50 + 21).
    """

    events = tmp_path / 'events'
    events.mkdir()
    clock = _Clock_Cls(datetime(2026, 9, 25, 8, 0, 0, 300000))
    logger = Session_Logger_Cls(config_path=None, log_dir=str(tmp_path), clock=clock, install_handlers=False,
                                csv_filename=os.path.join(str(tmp_path), 'summary.csv'))
    logger.Set_Close_Callback(lambda path: Export_Log(path, str(events), CONST_ZONE))
    for stamp, action in [('08:00:30.900', logger.Log_Camera_Connected),
                          ('08:01:00.700', logger.Log_Scan_Started), ('08:01:02.100', logger.Log_Scan_Ended),
                          ('08:01:05.500', lambda: logger.Log_Analysis_Started(1)),
                          ('08:02:00.200', lambda: logger.Log_Analysis_Finished(1, 1000, 0, 0, None)),       # 60 s
                          ('08:05:00.999', logger.Log_Scan_Started), ('08:05:01.000', logger.Log_Scan_Ended),
                          ('08:05:02.000', lambda: logger.Log_Analysis_Started(2)),
                          ('08:05:40.400', lambda: logger.Log_Analysis_Failed(2)),                         # 40 s
                          ('08:07:00.600', logger.Log_Scan_Started), ('08:07:02.900', logger.Log_Scan_Ended),  # 2 s
                          ('08:09:00.000', logger.Log_Scan_Started), ('08:09:01.000', logger.Log_Scan_Ended),
                          ('08:09:02.000', lambda: logger.Log_Analysis_Started(3)),
                          ('08:09:15.000', lambda: logger.Log_Analysis_Finished(3, 1000, 0, 0, None)),       # 15 s
                          ('08:12:00.000', logger.Log_Scan_Started), ('08:12:03.000', logger.Log_Scan_Failed),  # 3 s
                          ('08:13:00.000', lambda: logger.Log_Analysis_Started(4)),
                          ('08:13:20.000', lambda: logger.Log_Camera_Connection_Lost('gone')),
                          ('08:13:50.000', lambda: logger.Log_Analysis_Finished(4, 1000, 0, 0, None)),       # 50 s
                          ('08:20:00.000', lambda: logger.Log_Analysis_Started(5))]:
        clock.now = datetime.strptime('2026-09-25 ' + stamp, '%Y-%m-%d %H:%M:%S.%f')
        action()
    clock.now = datetime(2026, 9, 25, 8, 20, 21, 800000)
    logger.Close()                                                                                    # 21 s

    starts, dones = [], []
    for line in _Lines(str(events / '2026-09-25.csv'))[1:-1]:
        _station, event_type, ts = line.split(',')
        if event_type in ('CYCLE_START', 'CYCLE_DONE'):
            (starts if event_type == 'CYCLE_START' else dones).append(datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ'))
    daily = sum((done - start).total_seconds() for start, done in zip(starts, dones, strict=True))
    hours, minutes, seconds = (int(part) for part in _Session_Time(logger).split(':'))
    assert daily == hours * 3600 + minutes * 60 + seconds == 191


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
    logger = _Run(tmp_path, [('2026-09-25 23:59:50', ''), ('2026-09-25 23:59:55', 'scan'),
                             ('2026-09-25 23:59:56', 'scanned'), ('2026-09-25 23:59:57', 'analyse'),
                             ('2026-09-26 00:00:10', 'analysed'), ('2026-09-26 00:00:20', 'stop')])
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
    logger = _Run(tmp_path, [('2026-10-25 01:59:59', ''), ('02:30:00', 'scan'), ('02:30:01', 'scanned'),
                             ('02:30:02', 'analyse'), ('03:00:00', 'stop')])
    Export_Log(logger.Path, str(events), CONST_ZONE)
    assert _Lines(str(events / '2026-10-25.csv')) == [
        CONST_HEADER, 'SF4,STATION_ON,2026-10-24T23:59:59Z', 'SF4,CYCLE_START,2026-10-25T00:30:00Z',
        'SF4,CYCLE_DONE,2026-10-25T02:00:00Z', 'SF4,STATION_OFF,2026-10-25T02:00:00Z', '']


def test_a_crashed_run_is_exported_at_the_next_start_with_its_pairs_unclosed(tmp_path) -> None:
    """
    Description:
        A run killed mid-cycle never closes, so it exports nothing itself. The next start exports it —
        what it recorded and nothing invented: STATION_ON and CYCLE_START with no CYCLE_DONE and no
        STATION_OFF, the unpaired rows that mean an abnormal exit — even for a scan never analysed, whose
        capture end is in the log: nothing after the log's end can say the analysis never came. The new
        run's own log is not exported at startup; it is exported at its own close.
    """

    events = tmp_path / 'events'
    events.mkdir()
    Export_Pending(str(tmp_path), str(events), '', CONST_ZONE)        # an empty ledger: nothing earlier
    crashed = _Run(tmp_path, [('2026-09-25 07:00:00', ''), ('07:05:00', 'scan'), ('07:05:02', 'scanned')],
                   close=False)
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
