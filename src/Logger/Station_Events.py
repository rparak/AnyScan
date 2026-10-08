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
# File Name: ../Logger/Station_Events.py
## =========================================================================== ##

# System (Default)
import os
import csv
from datetime import datetime, timezone, tzinfo
# Dataclasses (Data Classes)
from dataclasses import dataclass, field
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan — the session log's one line parser and its event markers
#   ../Logger/Core
from Logger.Core import (Parse_Line, Event_Marker, Line_Time, Cycles, CONST_MARKER_RUN_START, CONST_MARKER_RUN_STOP,
                         CONST_LOG_NAME_PATTERN)

"""
Description:
    Initialization of constants.

    The daily station event file: the one module that writes this format. An external system tracks the
    station's uptime from it — when the application ran (STATION_ON / STATION_OFF) and when it worked
    (CYCLE_START / CYCLE_DONE: a scan, or a re-analysis, to the end of its analysis). The file is never
    written live: it is EXPORTED from a finished session log ('log_*.txt'), read through the logger's own
    Parse_Line and matched on the logger's event markers, never on sentence wording. The cycles are the
    logger's own Cycles over those markers — the computation behind the run-summary CSV's
    total_session_time — so the two files' time accounts are one definition. Until 2026-10-07 a cycle was a
    camera connection (CONNECT to its end); files are never rewritten, so rows before that date mean that.

    When a log is exported:
        - At application close, by the logger's close callback, on every close path (the window, the
          launcher's try/finally, atexit, SIGINT/SIGTERM).
        - At the next start, for every log that is not in the ledger: a crashed run (killed, power lost),
          or one whose export at close failed. A log another running instance still holds is left to it.

    The ledger ('station_events_exported.txt' beside the logs) names each exported log, one per line. A
    log's line is written only AFTER all its rows are written, so a failed export is simply not marked and
    the next start retries it. A crash between the rows and the ledger line exports that log twice — two
    fsynced writes wide, accepted (docs/design-decisions.md). When no ledger exists yet, every log already
    there is recorded as handled without exporting: logs older than the markers carry no events.

    Qt-free. It never holds the session logger: it returns what happened, and the caller logs it.
"""
# The station's identity in the external contract. One station today, so a constant; a second station
# would make it a configuration field.
#   Unit [string]
CONST_STATION_ID = 'SF4'
# The file's columns, in order — the header row.
#   Unit [Vector<string>]
CONST_COLUMNS = ['station_id', 'event_type', 'ts']
# The station's two event types, from the logger's run markers; the cycles' two come from Cycles.
#   Unit [Dict<string, string>]
CONST_STATION_EVENT_TYPES = {CONST_MARKER_RUN_START: 'STATION_ON', CONST_MARKER_RUN_STOP: 'STATION_OFF'}
#   Unit [string]
CONST_CYCLE_START = 'CYCLE_START'
CONST_CYCLE_DONE = 'CYCLE_DONE'
# The file is named by the event's LOCAL date (the contract); ts is UTC to the second.
#   Unit [string]
CONST_FILENAME_FORMAT = '%Y-%m-%d.csv'
CONST_TS_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
# The ledger of exported logs, in the log directory.
#   Unit [string]
CONST_LEDGER_FILENAME = 'station_events_exported.txt'


class Station_Events_Error_Cls(OSError):
    """
    Description:
        A log's station events could not be exported. Its message is a full sentence naming the log, the
        directory and what to check; the log is not in the ledger, so the next start retries it.
    """


@dataclass
class Station_Event_Str:
    """
    Description:
        One row of the daily file, with the local date that names the file it goes to.
    """

    # STATION_ON, STATION_OFF, CYCLE_START or CYCLE_DONE.
    #   Unit [string]
    Event_Type: str = ''
    # The event's local time, as the log recorded it (no zone).
    #   Unit [datetime]
    Local: tp.Optional[datetime] = None
    # The same instant in UTC.
    #   Unit [datetime]
    Utc: tp.Optional[datetime] = None


@dataclass
class Pending_Export_Str:
    """
    Description:
        What the export of earlier logs at startup did, for the caller to log.
    """

    # The logs exported now (file names).
    #   Unit [Vector<string>]
    Exported: tp.List[str] = field(default_factory=list)
    # The logs whose export failed, as (file name, the error sentence); they stay out of the ledger.
    #   Unit [Vector<Tuple<string> 1x2>]
    Failed: tp.List[tp.Tuple[str, str]] = field(default_factory=list)
    # The logs another running instance still holds, left for it to export at its close.
    #   Unit [Vector<string>]
    Live: tp.List[str] = field(default_factory=list)
    # How many logs a new ledger recorded as handled without exporting them (0 once a ledger exists).
    #   Unit [int]
    Baselined: int = 0


def Local_To_Utc(local: datetime, zone: tp.Optional[tzinfo] = None) -> datetime:
    """
    Description:
        A naive local time from the log, as UTC. The log stores no zone, so the local rules apply: the
        machine's (zone None) or a given zone. In the hour that repeats when summer time ends (02:00-03:00
        local, twice), the time is read as its FIRST occurrence — still summer time (fold=0); an event in
        the second pass is stamped one hour early. Recorded, not engineered around: the log cannot tell
        the two passes apart.

    Args:
        (1) local [datetime(object)]: The naive local time.
        (2) zone [tzinfo or None]: The zone whose rules apply; None for the machine's.

    Returns:
        (1) parameter [datetime(object)]: The instant in UTC (aware).
    """

    local = local.replace(fold=0)
    aware = local.astimezone() if zone is None else local.replace(tzinfo=zone)
    return aware.astimezone(timezone.utc)


def Read_Events(log_path: str, zone: tp.Optional[tzinfo] = None) -> tp.List[Station_Event_Str]:
    """
    Description:
        The station events one session log records, in time order: STATION_ON at the run's start line, a
        CYCLE_START / CYCLE_DONE pair for each of the logger's Cycles over the lines' event markers, and
        STATION_OFF at its stop line — the lines parsed by the logger's Parse_Line. A log holds one run, so
        its start comes first and its stop last, and every cycle lies between them (a cycle closed at its
        capture's end, decided later, still precedes the next event). A crashed run's log simply ends — no
        STATION_OFF, and an open cycle without its CYCLE_DONE — and nothing is invented to close it.

    Args:
        (1) log_path [string]: The session log.
        (2) zone [tzinfo or None]: The zone whose rules convert local time to UTC; None for the machine's.

    Returns:
        (1) parameter [Vector<Station_Event_Str>]: The events, in time order.
    """

    markers = []
    with open(log_path, 'r', encoding='utf-8', errors='replace') as log_file:
        for line in log_file:
            Log_Line_Str_i = Parse_Line(line.rstrip('\r\n'))
            marker = Event_Marker(Log_Line_Str_i)
            if marker:
                markers.append((marker, Line_Time(Log_Line_Str_i)))
    timed = [(CONST_STATION_EVENT_TYPES[marker], local) for marker, local in markers
             if marker == CONST_MARKER_RUN_START]
    for Cycle_Str_i in Cycles(markers):
        timed.append((CONST_CYCLE_START, Cycle_Str_i.Start))
        if Cycle_Str_i.End is not None:
            timed.append((CONST_CYCLE_DONE, Cycle_Str_i.End))
    timed += [(CONST_STATION_EVENT_TYPES[marker], local) for marker, local in markers
              if marker == CONST_MARKER_RUN_STOP]
    return [Station_Event_Str(Event_Type=event_type, Local=local, Utc=Local_To_Utc(local, zone))
            for event_type, local in timed]


def Write_Events(events: tp.List[Station_Event_Str], directory: str) -> None:
    """
    Description:
        Append events to the daily files, each to the file of its own LOCAL date, so one run (or one
        cycle) crossing midnight writes to two files. A file that does not exist is created with the
        header; one that exists is appended to, never given a second header. Every file the events need
        is opened before any row is written, so a missing or unwritable directory fails before a single
        row lands; each file is flushed and synced. UTF-8, no byte-order mark, rows ending in '\\n'.

    Args:
        (1) events [Vector<Station_Event_Str>]: The events, in order.
        (2) directory [string]: The daily files' directory.

    Raises:
        OSError: A file could not be opened or written.
    """

    by_file = {}
    for Station_Event_Str_i in events:
        by_file.setdefault(Station_Event_Str_i.Local.strftime(CONST_FILENAME_FORMAT), []).append(Station_Event_Str_i)
    handles = []
    try:
        for name in by_file:
            handles.append((open(os.path.join(directory, name), 'a', newline='', encoding='utf-8'), by_file[name]))
        for daily_file, rows in handles:
            writer = csv.writer(daily_file, lineterminator='\n')
            if os.fstat(daily_file.fileno()).st_size == 0:
                writer.writerow(CONST_COLUMNS)
            for Station_Event_Str_i in rows:
                writer.writerow([CONST_STATION_ID, Station_Event_Str_i.Event_Type,
                                 Station_Event_Str_i.Utc.strftime(CONST_TS_FORMAT)])
            daily_file.flush()
            os.fsync(daily_file.fileno())
    finally:
        for daily_file, _rows in handles:
            daily_file.close()


def Ledger_Path(log_dir: str) -> str:
    """
    Description:
        The ledger of exported logs in a log directory.

    Args:
        (1) log_dir [string]: The session logs' directory.

    Returns:
        (1) parameter [string]: The ledger's path.
    """

    return os.path.join(log_dir, CONST_LEDGER_FILENAME)


def __Read_Ledger(path: str) -> tp.Set[str]:
    """
    Description:
        The log names the ledger records as exported.

    Args:
        (1) path [string]: The ledger.

    Returns:
        (1) parameter [Set<string>]: The names.
    """

    with open(path, 'r', encoding='utf-8') as ledger:
        return {line.strip() for line in ledger if line.strip()}


def __Append_Ledger(path: str, names: tp.List[str]) -> None:
    """
    Description:
        Record logs as exported: one name per line, appended, flushed and synced.

    Args:
        (1) path [string]: The ledger.
        (2) names [Vector<string>]: The log names.
    """

    with open(path, 'a', encoding='utf-8', newline='') as ledger:
        ledger.write(''.join('%s\n' % name for name in names))
        ledger.flush()
        os.fsync(ledger.fileno())


def __Is_Live(path: str) -> bool:
    """
    Description:
        Whether another running instance still holds this log (the logger's exclusive lock). Without
        fcntl (Windows) nothing is held, and every unexported log is taken as finished.

    Args:
        (1) path [string]: The session log.

    Returns:
        (1) parameter [bool]: True when the log is locked by a live run.
    """

    try:
        # Fcntl (Unix file control) [Python standard library, POSIX only]
        import fcntl
    except ImportError:
        return False
    try:
        log_file = open(path, 'r', encoding='utf-8')
    except OSError:
        # Unreadable: not held by anyone this can see — the export reports why it cannot read it.
        return False
    with log_file:
        try:
            fcntl.flock(log_file.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
        except OSError:
            return True
        fcntl.flock(log_file.fileno(), fcntl.LOCK_UN)
    return False


def Export_Log(log_path: str, directory: str, zone: tp.Optional[tzinfo] = None) -> int:
    """
    Description:
        Export one finished session log: its events into the daily files, THEN its name into the ledger.
        Only a fully written export is marked, so a failure leaves the log for the next start to retry.

    Args:
        (1) log_path [string]: The session log.
        (2) directory [string]: The daily files' directory.
        (3) zone [tzinfo or None]: The zone whose rules convert local time to UTC; None for the machine's.

    Returns:
        (1) parameter [int]: The number of rows written.

    Raises:
        Station_Events_Error_Cls: The log could not be read, or its rows or ledger line not written.
    """

    name = os.path.basename(log_path)
    try:
        events = Read_Events(log_path, zone)
        Write_Events(events, directory)
        __Append_Ledger(Ledger_Path(os.path.dirname(os.path.abspath(log_path))), [name])
    except OSError as error:
        raise Station_Events_Error_Cls(
            'The station events of %s could not be exported to %s (%s). Check that the directory exists, '
            'is writable and has free space; the export is retried at the next start.'
            % (name, directory, error.strerror or error)) from error
    return len(events)


def Export_Pending(log_dir: str, directory: str, current_log: str,
                   zone: tp.Optional[tzinfo] = None) -> Pending_Export_Str:
    """
    Description:
        At startup: export every session log the ledger does not name, oldest first — a crashed run, or
        one whose export at close failed — except this run's own log (exported at its close) and a log
        another running instance holds. Without a ledger, every log already there is recorded as handled
        and none is exported: the export history starts here.

    Args:
        (1) log_dir [string]: The session logs' directory.
        (2) directory [string]: The daily files' directory.
        (3) current_log [string]: This run's own log, never exported here.
        (4) zone [tzinfo or None]: The zone whose rules convert local time to UTC; None for the machine's.

    Returns:
        (1) parameter [Pending_Export_Str(object)]: What was exported, failed, left live or baselined.

    Raises:
        Station_Events_Error_Cls: The ledger could not be read or created.
    """

    Pending_Export_Str_i = Pending_Export_Str()
    current = os.path.basename(current_log)
    names = sorted(name for name in os.listdir(log_dir) if CONST_LOG_NAME_PATTERN.match(name) and name != current)
    ledger = Ledger_Path(log_dir)
    try:
        if not os.path.exists(ledger):
            __Append_Ledger(ledger, names)
            Pending_Export_Str_i.Baselined = len(names)
            return Pending_Export_Str_i
        exported = __Read_Ledger(ledger)
    except OSError as error:
        raise Station_Events_Error_Cls(
            'The station-event ledger %s could not be read or created (%s), so no earlier log was exported. '
            'Check that the log directory is writable.' % (ledger, error.strerror or error)) from error
    for name in (name for name in names if name not in exported):
        path = os.path.join(log_dir, name)
        if __Is_Live(path):
            Pending_Export_Str_i.Live.append(name)
            continue
        try:
            Export_Log(path, directory, zone)
        except Station_Events_Error_Cls as error:
            Pending_Export_Str_i.Failed.append((name, str(error)))
        else:
            Pending_Export_Str_i.Exported.append(name)
    return Pending_Export_Str_i
