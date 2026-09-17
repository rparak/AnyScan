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
# File Name: ../Logger/Core.py
## =========================================================================== ##

# System (Default)
import os
import csv
import atexit
import signal
import threading
from datetime import datetime, timedelta
# Dataclasses (Data Classes)
from dataclasses import dataclass, field
# Typing (Support for type hints)
import typing as tp

"""
Description:
    Initialization of constants.
"""
# The directory the session log files are written to, resolved relative to the
# application root (this file lives in src/Logger/, so the root is two levels up).
#   Unit [string]
CONST_DEFAULT_LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                     '..', '..', 'logger'))
# The severity levels. Each line carries one, in a FIXED-WIDTH field between the
# timestamp and the message, so the level stays a readable column. The level is chosen by
# the call site (which method logged the event), never derived from the message text.
#   Unit [string]
CONST_LEVEL_INFO = 'INFO'
CONST_LEVEL_WARNING = 'WARNING'
CONST_LEVEL_ERROR = 'ERROR'
# The width the bracketed level is padded to — the longest level ('WARNING') — so the
# message column starts at the same offset on every line.
#   Unit [int]
CONST_LEVEL_WIDTH = 7
# The timestamp formats. The date and the per-line time are configurable; the
# filename time keeps hours and minutes only.
#   Unit [string]
CONST_DATE_FORMAT = '%Y-%m-%d'
CONST_TIME_FORMAT = '%H:%M:%S'
CONST_FILENAME_TIME_FORMAT = '%H-%M'
# The timestamp formats used inside the run-summary CSV. These are fixed by the
# CSV column contract and are deliberately independent of the per-line formats
# above, so the injected line formats never change the CSV layout.
#   Unit [string]
CONST_CSV_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
CONST_CSV_TIME_FORMAT = '%H:%M:%S'
# The static run-summary CSV. The name identifies the camera + lens hardware
# setup; a different setup produces a different file without touching the logic.
# The hardware identifier is the only thing that varies, so it is kept apart from
# the filename template and both live here, in one place.
#   Unit [string]
CONST_CSV_HARDWARE_ID = 'a2A1920_51gcPRO_Computar_M1228_MPW3'
CONST_CSV_FILENAME_TEMPLATE = 'log_{hardware_id}.csv'
# The supported CSV delimiters. The default is a comma; a semicolon is exposed
# because Excel in a Czech locale expects it.
#   Unit [string]
CONST_CSV_DELIMITER_COMMA = ','
CONST_CSV_DELIMITER_SEMICOLON = ';'
CONST_CSV_DEFAULT_DELIMITER = CONST_CSV_DELIMITER_COMMA
# The run-summary CSV columns, in the exact order they are written. The header
# row is this list; each data row is rendered one-to-one from a Summary_Str.
#   Unit [Vector<string>]
CONST_CSV_COLUMNS = ['log_file', 'application_start', 'application_stop', 'cycle_time',
                     'cycle_hours', 'analyzed_images', 'analyzed_objects', 'sessions_count',
                     'total_session_time', 'idle_time', 'errors_count', 'total_error_time',
                     'session_details', 'error_details']
# The separator between the per-item entries packed into the 'session_details'
# and 'error_details' cells. It is sanitised out of free-text error messages so
# it can never be mistaken for a real boundary.
#   Unit [string]
CONST_CSV_DETAIL_SEPARATOR = ' | '
# The byte-order mark written once at the head of a freshly created CSV, so Excel
# opens the file as UTF-8. It is written explicitly (rather than via the
# 'utf-8-sig' codec) because that codec re-emits the mark on every append, which
# would corrupt the file mid-stream when a row is added to an existing file.
#   Unit [string]
CONST_CSV_BOM = '﻿'


def Format_HMS(total_seconds: float) -> str:
    """
    Description:
        Format a non-negative duration in seconds as HH:MM:SS. Hours are not capped
        at 24, so a run longer than a day still reads correctly (e.g. '25:03:07').

    Args:
        (1) total_seconds [float]: The duration in seconds.

    Returns:
        (1) parameter [string]: The duration formatted as HH:MM:SS.
    """

    seconds = int(round(max(0.0, total_seconds)))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}'


@dataclass
class Session_Str:
    """
    Description:
        One camera session: the interval from a camera connection to the matching
        disconnection, with its per-session analysis counters.
    """

    # The 1-based index of the session within the run.
    Index: int = 0
    # The connection time; the disconnection time (None while still open).
    Start: tp.Optional[datetime] = None
    End: tp.Optional[datetime] = None
    # True when the session was still open at shutdown and closed at the stop time.
    Closed_At_Shutdown: bool = False
    # Analysis counters accumulated while this session was open.
    Images: int = 0
    Objects: int = 0


@dataclass
class Error_Str:
    """
    Description:
        One tracked error: the identifier, its message, the time it occurred and the
        time it was resolved (None while unresolved).
    """

    # The 1-based identifier of the error within the run.
    Id: int = 0
    # The human-readable error message.
    Message: str = ''
    # The time the error occurred; the time it was resolved (None while unresolved).
    Start: tp.Optional[datetime] = None
    End: tp.Optional[datetime] = None
    # True once the error has been resolved.
    Resolved: bool = False


@dataclass
class Summary_Str:
    """
    Description:
        The computed statistics for one application run. This is the pure result of
        reading the recorded state at a given stop time; it holds raw values (times
        and durations in seconds) so the CSV renderer, not the computation, owns the
        formatting. The per-item breakdowns keep their datetimes so the renderer can
        format them exactly as the compact detail cells require.
    """

    # The filename of the matching '.txt' log (e.g. 'log_2026-09-12_12-16.txt').
    #   Unit [string]
    Log_File: str = ''
    # The application start and stop times.
    #   Unit [datetime(object)]
    Application_Start: tp.Optional[datetime] = None
    Application_Stop: tp.Optional[datetime] = None
    # The whole-run cycle time, start -> stop.
    #   Unit [float]
    Cycle_Seconds: float = 0.0
    # The run-wide analysis counters.
    #   Unit [int]
    Analyzed_Images: int = 0
    Analyzed_Objects: int = 0
    # The number of camera sessions and their summed duration.
    #   Unit [int]
    Sessions_Count: int = 0
    #   Unit [float]
    Total_Session_Seconds: float = 0.0
    # The time no session was open, cycle_seconds - total_session_seconds.
    #   Unit [float]
    Idle_Seconds: float = 0.0
    # The number of tracked errors and their summed duration.
    #   Unit [int]
    Errors_Count: int = 0
    #   Unit [float]
    Total_Error_Seconds: float = 0.0
    # The per-session breakdown: each entry is (index, start, end, duration_seconds).
    #   Unit [Vector<Tuple[int, datetime, datetime, float]>]
    Session_Details: tp.List[tp.Tuple[int, datetime, datetime, float]] = field(default_factory=list)
    # The per-error breakdown: each entry is (id, start, end, duration_seconds, message).
    #   Unit [Vector<Tuple[int, datetime, datetime, float, string]>]
    Error_Details: tp.List[tp.Tuple[int, datetime, datetime, float, str]] = field(default_factory=list)


def Sanitize_Detail_Text(text: str) -> str:
    """
    Description:
        Sanitize a free-text fragment (an error message) so it survives the compact
        detail encoding: the entry separator is stripped out so it can never be read
        as a real boundary, and newlines are collapsed to spaces so one entry stays
        on one logical piece. Commas and quotes are left untouched — CSV quoting
        preserves them.

    Args:
        (1) text [string]: The raw fragment.

    Returns:
        (1) parameter [string]: The sanitised fragment.
    """

    return (text.replace(CONST_CSV_DETAIL_SEPARATOR.strip(), '/')
                .replace('\r', ' ').replace('\n', ' '))


def Encode_Session_Details(Summary_Str: Summary_Str) -> str:
    """
    Description:
        Encode the per-session breakdown into a single CSV cell. Each session is
        'index:start-end:duration' (times HH:MM:SS), joined by the detail separator;
        an empty string when there are no sessions.

    Args:
        (1) Summary_Str [Summary_Str(object)]: The computed run statistics.

    Returns:
        (1) parameter [string]: The compact 'session_details' cell.
    """

    parts = []
    for (index, start, end, duration_seconds) in Summary_Str.Session_Details:
        parts.append(f'{index}:{start.strftime(CONST_CSV_TIME_FORMAT)}-'
                     f'{end.strftime(CONST_CSV_TIME_FORMAT)}:{Format_HMS(duration_seconds)}')
    return CONST_CSV_DETAIL_SEPARATOR.join(parts)


def Encode_Error_Details(Summary_Str: Summary_Str) -> str:
    """
    Description:
        Encode the per-error breakdown into a single CSV cell. Each error is
        'id:start-end:duration:message' (times HH:MM:SS, message sanitised), joined
        by the detail separator; an empty string when there are no errors.

    Args:
        (1) Summary_Str [Summary_Str(object)]: The computed run statistics.

    Returns:
        (1) parameter [string]: The compact 'error_details' cell.
    """

    parts = []
    for (error_id, start, end, duration_seconds, message) in Summary_Str.Error_Details:
        parts.append(f'{error_id}:{start.strftime(CONST_CSV_TIME_FORMAT)}-'
                     f'{end.strftime(CONST_CSV_TIME_FORMAT)}:{Format_HMS(duration_seconds)}:'
                     f'{Sanitize_Detail_Text(message)}')
    return CONST_CSV_DETAIL_SEPARATOR.join(parts)


def Render_Summary_Csv_Row(Summary_Str: Summary_Str) -> tp.List[str]:
    """
    Description:
        Render one computed summary into the ordered list of CSV cell values that
        matches CONST_CSV_COLUMNS one-to-one. This is pure and holds every formatting
        decision (HH:MM:SS durations, decimal hours to three places, the compact
        detail cells), so it can be tested without touching the file system.

    Args:
        (1) Summary_Str [Summary_Str(object)]: The computed run statistics.

    Returns:
        (1) parameter [Vector<string>]: The data row, aligned to CONST_CSV_COLUMNS.
    """

    return [Summary_Str.Log_File,
            Summary_Str.Application_Start.strftime(CONST_CSV_DATETIME_FORMAT),
            Summary_Str.Application_Stop.strftime(CONST_CSV_DATETIME_FORMAT),
            Format_HMS(Summary_Str.Cycle_Seconds),
            f'{Summary_Str.Cycle_Seconds / 3600.0:.3f}',
            str(Summary_Str.Analyzed_Images),
            str(Summary_Str.Analyzed_Objects),
            str(Summary_Str.Sessions_Count),
            Format_HMS(Summary_Str.Total_Session_Seconds),
            Format_HMS(Summary_Str.Idle_Seconds),
            str(Summary_Str.Errors_Count),
            Format_HMS(Summary_Str.Total_Error_Seconds),
            Encode_Session_Details(Summary_Str),
            Encode_Error_Details(Summary_Str)]


class Session_Logger_Cls(object):
    """
    Description:
        A plain-text session logger. It records the full lifecycle of one application
        run to a single '.txt' file, one '[Date] [Time] [Info]' line per event, ending
        with the 'Application stopped' line. When the application closes it also appends
        exactly one statistical row, per run, to a single static run-summary CSV file
        that accumulates over every run and is never rewritten, truncated or rotated.

        The logger is Qt-free and thread-safe. A single clock provider is injected so
        the behaviour is deterministic under test; nothing calls datetime.now directly.

        Note:
            Shutdown is made reliable in three overlapping ways: an explicit Close in
            the application's try/finally, an atexit hook, and (on the main thread)
            SIGINT/SIGTERM handlers. Every path appends the CSV row and closes the
            file, and Close is idempotent so running more than one of them is harmless.
            A failure to write the CSV row is logged into the '.txt' file and never
            prevents that file from closing cleanly.

    Initialization of the Class:
        Args:
            (1) log_dir [string]: Directory the log files are written to (created if missing).
            (2) clock [function]: A zero-argument provider returning the current datetime.
            (3) date_format [string]: strftime format for the date field.
            (4) time_format [string]: strftime format for the per-line time field.
            (5) install_handlers [bool]: Register the atexit and signal shutdown hooks.
            (6) csv_filename [string]: The run-summary CSV filename (default: derived from
                CONST_CSV_FILENAME_TEMPLATE and CONST_CSV_HARDWARE_ID). An absolute path is
                honoured as-is; otherwise it is resolved inside log_dir.
            (7) csv_delimiter [string]: The CSV delimiter (default ','; ';' for Excel in a
                Czech locale).

        Example:
            Initialization:
                # Initialize the class.
                Cls = Session_Logger_Cls()

            Features:
                # Log lifecycle events and close (which appends the CSV summary row).
                Cls.Log_Info('Application started'); Cls.Log_Camera_Connected(); Cls.Close()
    """

    def __init__(self, log_dir: tp.Optional[str] = None,
                 clock: tp.Callable[[], datetime] = datetime.now,
                 date_format: str = CONST_DATE_FORMAT, time_format: str = CONST_TIME_FORMAT,
                 install_handlers: bool = True, csv_filename: tp.Optional[str] = None,
                 csv_delimiter: str = CONST_CSV_DEFAULT_DELIMITER) -> None:

        # << PRIVATE >> #
        # Injected time provider and formats.
        self.__clock = clock
        self.__date_format = date_format
        self.__time_format = time_format

        # The run's start time drives both the filename and the summary; it is taken
        # once, at construction, not at the first log line.
        self.__start_time = clock()
        self.__stop_time = None

        # Run-wide analysis counters and the per-run bookkeeping of sessions/errors.
        self.__images_total = 0
        self.__objects_total = 0
        self.__sessions = []
        self.__open_session = None
        self.__errors = []
        self.__errors_by_id = {}
        self.__next_error_id = 1

        # A re-entrant lock guards every write and every state mutation, so the API is
        # safe to call from multiple threads.
        self.__lock = threading.RLock()
        self.__closed = False

        # Open the file for this run. The directory is created if it does not exist.
        self.__log_dir = os.path.abspath(log_dir) if log_dir is not None else CONST_DEFAULT_LOG_DIR
        os.makedirs(self.__log_dir, exist_ok=True)
        self.__path = os.path.join(self.__log_dir, self.__Build_Filename(self.__start_time))
        self.__file = open(self.__path, 'w', encoding='utf-8')

        # The static run-summary CSV. The default name is derived once, from the
        # hardware constant; an absolute csv_filename is honoured as-is, otherwise it
        # is resolved inside the log directory alongside the '.txt' file.
        self.__csv_delimiter = csv_delimiter
        csv_name = (csv_filename if csv_filename is not None
                    else CONST_CSV_FILENAME_TEMPLATE.format(hardware_id=CONST_CSV_HARDWARE_ID))
        self.__csv_path = os.path.join(self.__log_dir, csv_name)

        # Register the shutdown hooks so the summary is written even on a hard exit.
        self.__install_handlers = install_handlers
        self.__previous_signal_handlers = {}
        if install_handlers:
            self.__Install_Handlers()

    # ----------------------------------------------------------------- properties

    @property
    def Path(self) -> str:
        """
        Description:
            Absolute path to this run's log file.

        Returns:
            (1) parameter [string]: The log file path.
        """

        return self.__path

    @property
    def Csv_Path(self) -> str:
        """
        Description:
            Absolute path to the static run-summary CSV file this run appends to.

        Returns:
            (1) parameter [string]: The CSV file path.
        """

        return self.__csv_path

    @property
    def Analyzed_Images(self) -> int:
        """
        Description:
            The cumulative number of analyzed images over the whole run.

        Returns:
            (1) parameter [int]: The analyzed-image count.
        """

        return self.__images_total

    @property
    def Analyzed_Objects(self) -> int:
        """
        Description:
            The cumulative number of analyzed objects over the whole run.

        Returns:
            (1) parameter [int]: The analyzed-object count.
        """

        return self.__objects_total

    @property
    def Sessions(self) -> tp.List[Session_Str]:
        """
        Description:
            The recorded camera sessions, in order.

        Returns:
            (1) parameter [Vector<Session_Str>]: The sessions.
        """

        return self.__sessions

    @property
    def Errors(self) -> tp.List[Error_Str]:
        """
        Description:
            The tracked errors, in order of occurrence.

        Returns:
            (1) parameter [Vector<Error_Str>]: The errors.
        """

        return self.__errors

    # --------------------------------------------------------------------- naming

    def __Build_Filename(self, start_time: datetime) -> str:
        """
        Description:
            Build the per-run filename 'log_[date]_[hour-minutes].txt' from the start
            time (e.g. 'log_2026-09-12_14-37.txt').

        Args:
            (1) start_time [datetime(object)]: The application start time.

        Returns:
            (1) parameter [string]: The filename.
        """

        return (f'log_{start_time.strftime(self.__date_format)}'
                f'_{start_time.strftime(CONST_FILENAME_TIME_FORMAT)}.txt')

    # ---------------------------------------------------------------------- writes

    def __Write_Line(self, info: str, now: datetime, level: str = CONST_LEVEL_INFO) -> None:
        """
        Description:
            Write one '[Date] [Time] [LEVEL] message' line at the given time and flush it
            to disk, so a hard crash still leaves a usable log. The level sits in a
            fixed-width field between the timestamp and the message, so it reads as a
            column; it is passed by the call site, never parsed from the message. Assumes
            the lock is held.

        Args:
            (1) info [string]: The human-readable event text.
            (2) now [datetime(object)]: The timestamp for the line.
            (3) level [string]: The severity — CONST_LEVEL_INFO / _WARNING / _ERROR.
        """

        if self.__file is None or self.__file.closed:
            return
        stamp = '%s %s' % (now.strftime(self.__date_format), now.strftime(self.__time_format))
        line = '%s [%-*s] %s\n' % (stamp, CONST_LEVEL_WIDTH, level, info)
        self.__file.write(line)
        self.__file.flush()
        try:
            os.fsync(self.__file.fileno())
        except (OSError, ValueError):
            # fsync is best-effort; a flush already went out.
            pass

    # ------------------------------------------------------------------ public API

    def Log_Info(self, info: str) -> None:
        """
        Description:
            Log a plain informational event.

        Args:
            (1) info [string]: The event text.
        """

        with self.__lock:
            self.__Write_Line(info, self.__clock())

    def Log_Warning(self, info: str) -> None:
        """
        Description:
            Log a warning. Warnings do not enter the error statistics.

        Args:
            (1) info [string]: The warning text.
        """

        with self.__lock:
            self.__Write_Line(info, self.__clock(), CONST_LEVEL_WARNING)

    def Log_Error(self, message: str) -> int:
        """
        Description:
            Log an error and start tracking it. A fresh identifier is assigned and
            returned so the caller can later resolve it.

        Args:
            (1) message [string]: The error message.

        Returns:
            (1) parameter [int]: The identifier assigned to the error.
        """

        with self.__lock:
            now = self.__clock()
            error_id = self.__next_error_id
            self.__next_error_id += 1
            Error_Str_i = Error_Str(Id=error_id, Message=message, Start=now)
            self.__errors.append(Error_Str_i)
            self.__errors_by_id[error_id] = Error_Str_i
            self.__Write_Line(f'{message} (error_id={error_id})', now, CONST_LEVEL_ERROR)
            return error_id

    def Log_Error_Resolved(self, error_id: int) -> None:
        """
        Description:
            Mark a previously logged error as resolved and record its downtime. A
            resolve for an unknown or already-resolved identifier is logged as a
            warning and does not corrupt the statistics.

        Args:
            (1) error_id [int]: The identifier returned by Log_Error.
        """

        with self.__lock:
            now = self.__clock()
            Error_Str_i = self.__errors_by_id.get(error_id)
            if Error_Str_i is None:
                self.__Write_Line(f'error resolution without a matching error '
                                  f'(error_id={error_id})', now, CONST_LEVEL_WARNING)
                return
            if Error_Str_i.Resolved:
                self.__Write_Line(f'error already resolved (error_id={error_id})',
                                  now, CONST_LEVEL_WARNING)
                return
            Error_Str_i.End = now
            Error_Str_i.Resolved = True
            downtime = Format_HMS((now - Error_Str_i.Start).total_seconds())
            # INFO: it is the RESOLUTION being reported, not the fault — the fault was
            # logged as ERROR when it happened.
            self.__Write_Line(f'Error resolved: {Error_Str_i.Message} '
                              f'(error_id={error_id}, downtime={downtime})', now, CONST_LEVEL_INFO)

    def Log_Camera_Connection_Attempt(self, info: str = '') -> None:
        """
        Description:
            Log that a connection to the camera is being attempted.

        Args:
            (1) info [string]: Optional detail (e.g. 'id=cam0, ip=192.168.1.40').
        """

        with self.__lock:
            detail = f' ({info})' if info else ''
            self.__Write_Line(f'Connecting to camera{detail}', self.__clock())

    def Log_Camera_Connected(self, info: str = '') -> int:
        """
        Description:
            Log a successful camera connection and open a new session. A connection
            while a session is already open closes the previous one at this time and
            logs a warning, so the statistics never hold two open sessions.

        Args:
            (1) info [string]: Optional detail appended to the line.

        Returns:
            (1) parameter [int]: The 1-based index of the opened session.
        """

        with self.__lock:
            now = self.__clock()
            if self.__open_session is not None:
                self.__open_session.End = now
                self.__Write_Line(f'camera connected while session '
                                  f'{self.__open_session.Index} was still open; closing it',
                                  now, CONST_LEVEL_WARNING)
                self.__open_session = None
            Session_Str_i = Session_Str(Index=len(self.__sessions) + 1, Start=now)
            self.__sessions.append(Session_Str_i)
            self.__open_session = Session_Str_i
            detail = f' — {info}' if info else ''
            self.__Write_Line(f'Camera connected — session {Session_Str_i.Index} started{detail}', now)
            return Session_Str_i.Index

    def Log_Camera_Disconnected(self, info: str = '') -> None:
        """
        Description:
            Log a camera disconnection and close the open session. A disconnection with
            no open session is logged as a warning and does not corrupt the statistics.

        Args:
            (1) info [string]: Optional detail appended to the line.
        """

        with self.__lock:
            now = self.__clock()
            if self.__open_session is None:
                self.__Write_Line('camera disconnected without an open session',
                                  now, CONST_LEVEL_WARNING)
                return
            Session_Str_i = self.__open_session
            Session_Str_i.End = now
            self.__open_session = None
            duration = Format_HMS((now - Session_Str_i.Start).total_seconds())
            detail = f' — {info}' if info else ''
            self.__Write_Line(f'Camera disconnected — session {Session_Str_i.Index} ended '
                              f'(duration={duration}){detail}', now)

    def Log_Camera_Connection_Lost(self, info: str = '') -> None:
        """
        Description:
            Log a lost camera connection. The loss is an ERROR — the operation failed and
            the session ended unexpectedly — distinct from an operator-initiated
            disconnect (INFO). The open session (if any) is closed at this time.

        Args:
            (1) info [string]: Optional detail appended to the line.
        """

        with self.__lock:
            now = self.__clock()
            detail = f' ({info})' if info else ''
            self.__Write_Line(f'camera connection lost{detail}', now, CONST_LEVEL_ERROR)
            if self.__open_session is not None:
                Session_Str_i = self.__open_session
                Session_Str_i.End = now
                self.__open_session = None
                duration = Format_HMS((now - Session_Str_i.Start).total_seconds())
                self.__Write_Line(f'Camera disconnected — session {Session_Str_i.Index} ended '
                                  f'(duration={duration})', now)

    def Log_Scan_Started(self, scan_id: tp.Optional[int] = None) -> None:
        """
        Description:
            Log the start of a scan.

        Args:
            (1) scan_id [int]: Optional scan identifier.
        """

        with self.__lock:
            detail = f' (scan_id={scan_id})' if scan_id is not None else ''
            self.__Write_Line(f'Scan started{detail}', self.__clock())

    def Log_Scan_Ended(self, scan_id: tp.Optional[int] = None) -> None:
        """
        Description:
            Log the end of a scan.

        Args:
            (1) scan_id [int]: Optional scan identifier.
        """

        with self.__lock:
            detail = f' (scan_id={scan_id})' if scan_id is not None else ''
            self.__Write_Line(f'Scan ended{detail}', self.__clock())

    def __Set_Suffix(self, set_id: tp.Optional[str]) -> str:
        """
        Description:
            The ' (set=<id>)' suffix that links an analysis-related line to its capture
            set on disk, so an ERROR at a time points straight at the frame that produced
            it. Empty when no set id is given.

        Args:
            (1) set_id [string]: The capture-set identifier, or None.

        Returns:
            (1) parameter [string]: The suffix, or ''.
        """

        return f' (set={set_id})' if set_id else ''

    def Log_Analysis_Started(self, set_id: tp.Optional[str] = None) -> None:
        """
        Description:
            Log the start of an analysis, tagged with its capture-set id.

        Args:
            (1) set_id [string]: The capture-set identifier for this analysis.
        """

        with self.__lock:
            self.__Write_Line(f'Analysis started{self.__Set_Suffix(set_id)}', self.__clock())

    def Log_Analysis_Ended(self, latency_ms: tp.Optional[int] = None,
                           set_id: tp.Optional[str] = None) -> None:
        """
        Description:
            Log the end of an analysis, tagged with its capture-set id.

        Args:
            (1) latency_ms [int]: Optional inference time in milliseconds.
            (2) set_id [string]: The capture-set identifier for this analysis.
        """

        with self.__lock:
            detail = f' (latency={latency_ms} ms)' if latency_ms is not None else ''
            self.__Write_Line(f'Analysis ended{detail}{self.__Set_Suffix(set_id)}', self.__clock())

    def Log_Image_Analyzed(self, image_id: tp.Any, objects: int,
                           set_id: tp.Optional[str] = None) -> None:
        """
        Description:
            Log one analyzed image and advance the counters: the run-wide image and
            object totals, and the open session's per-session counters.

        Args:
            (1) image_id [any]: The image identifier.
            (2) objects [int]: The number of objects found in the image.
            (3) set_id [string]: The capture-set identifier for this analysis.
        """

        with self.__lock:
            now = self.__clock()
            self.__images_total += 1
            self.__objects_total += objects
            if self.__open_session is not None:
                self.__open_session.Images += 1
                self.__open_session.Objects += objects
            self.__Write_Line(f'Image analyzed (image_id={image_id}, objects={objects}, '
                              f'total_objects={self.__objects_total})'
                              f'{self.__Set_Suffix(set_id)}', now)

    def Log_Object_Detected(self, label: str, confidence: tp.Optional[float] = None,
                            bbox: tp.Optional[tp.Tuple[int, int, int, int]] = None,
                            sentence: str = '', set_id: tp.Optional[str] = None) -> None:
        """
        Description:
            Log the textual information about one analyzed object. The fields mirror the
            analysis result structure (Parameters/Vision.py, Detection_Str): the label,
            the optional confidence, the bounding box and the generated sentence.

        Args:
            (1) label [string]: The object's noun-phrase label.
            (2) confidence [float]: Optional detector confidence.
            (3) bbox [Vector<int> 1x4]: Optional bounding box (x, y, w, h).
            (4) sentence [string]: Optional generated description.
            (5) set_id [string]: The capture-set identifier for this analysis.
        """

        with self.__lock:
            parts = [f'type={label}']
            if confidence is not None:
                parts.append(f'confidence={confidence:.2f}')
            if bbox is not None:
                parts.append('bbox=(' + ','.join(str(int(v)) for v in bbox) + ')')
            if sentence:
                parts.append(f'text="{sentence}"')
            self.__Write_Line('Object detected: ' + ', '.join(parts)
                              + self.__Set_Suffix(set_id), self.__clock())

    # -------------------------------------------------------------------- shutdown

    def Compute_Summary(self, stop_time: tp.Optional[datetime] = None) -> Summary_Str:
        """
        Description:
            Compute the run statistics for a stop time. This is pure: it reads the
            recorded state and never mutates it, so it is safe to call more than once
            and holds no formatting — the CSV renderer (Render_Summary_Csv_Row) owns
            that. This keeps 'compute summary' and 'render summary' separately testable.

            An open session is closed at the stop time; an unresolved error's duration
            is measured up to the stop time. With zero sessions, errors or images the
            summary is still complete, with zero values.

        Args:
            (1) stop_time [datetime(object)]: The application stop time (defaults to the
                recorded stop time, or the clock if the logger is not yet closed).

        Returns:
            (1) parameter [Summary_Str(object)]: The computed run statistics.
        """

        with self.__lock:
            if stop_time is None:
                stop_time = self.__stop_time if self.__stop_time is not None else self.__clock()

            cycle_seconds = (stop_time - self.__start_time).total_seconds()

            # << Sessions: durations and the per-session breakdown. >>
            session_seconds = 0.0
            session_details = []
            for Session_Str_i in self.__sessions:
                end = Session_Str_i.End if Session_Str_i.End is not None else stop_time
                duration = (end - Session_Str_i.Start).total_seconds()
                session_seconds += duration
                session_details.append((Session_Str_i.Index, Session_Str_i.Start, end, duration))

            # << Errors: durations and the per-error breakdown. >>
            error_seconds = 0.0
            error_details = []
            for Error_Str_i in self.__errors:
                end = Error_Str_i.End if Error_Str_i.End is not None else stop_time
                duration = (end - Error_Str_i.Start).total_seconds()
                error_seconds += duration
                error_details.append((Error_Str_i.Id, Error_Str_i.Start, end, duration,
                                      Error_Str_i.Message))

            return Summary_Str(Log_File=os.path.basename(self.__path),
                               Application_Start=self.__start_time,
                               Application_Stop=stop_time,
                               Cycle_Seconds=cycle_seconds,
                               Analyzed_Images=self.__images_total,
                               Analyzed_Objects=self.__objects_total,
                               Sessions_Count=len(self.__sessions),
                               Total_Session_Seconds=session_seconds,
                               Idle_Seconds=cycle_seconds - session_seconds,
                               Errors_Count=len(self.__errors),
                               Total_Error_Seconds=error_seconds,
                               Session_Details=session_details,
                               Error_Details=error_details)

    def __Read_Existing_Header(self) -> tp.Optional[tp.List[str]]:
        """
        Description:
            Read the header row of the existing CSV, or None when the file is missing,
            empty or unreadable. The 'utf-8-sig' codec strips the leading byte-order
            mark, so the returned names never carry it.

        Returns:
            (1) parameter [Vector<string> or None]: The existing header, or None.
        """

        try:
            with open(self.__csv_path, 'r', newline='', encoding='utf-8-sig') as csv_file:
                for header in csv.reader(csv_file, delimiter=self.__csv_delimiter):
                    return header
                return None
        except (OSError, ValueError):
            return None

    def __Align_Row_To_Header(self, existing_header: tp.List[str],
                              row: tp.List[str]) -> tp.List[str]:
        """
        Description:
            Re-order a data row (aligned to CONST_CSV_COLUMNS) so it matches an existing
            header that differs from the current columns. Columns the existing header
            does not name are dropped; columns it names but the current run does not
            provide are left empty. This is the chosen behaviour for a header mismatch:
            never append a misaligned row silently — align it to what is already there
            and log a warning into the '.txt' file.

        Args:
            (1) existing_header [Vector<string>]: The header already in the file.
            (2) row [Vector<string>]: The data row aligned to CONST_CSV_COLUMNS.

        Returns:
            (1) parameter [Vector<string>]: The row re-ordered to the existing header.
        """

        values = dict(zip(CONST_CSV_COLUMNS, row))
        return [values.get(column, '') for column in existing_header]

    def __Lock_File(self, file_obj: tp.Any) -> None:
        """
        Description:
            Take an exclusive advisory lock on an open file, so two processes cannot
            interleave their appended rows. Best-effort: on a platform without fcntl
            (e.g. Windows) a single csv.writer.writerow is still one write() under the
            O_APPEND opened handle, which does not interleave for a small row.

        Args:
            (1) file_obj [file(object)]: The open file to lock.
        """

        try:
            # Fcntl (Unix file control) [Python standard library, POSIX only]
            import fcntl
            fcntl.flock(file_obj.fileno(), fcntl.LOCK_EX)
        except (ImportError, OSError, ValueError):
            pass

    def __Unlock_File(self, file_obj: tp.Any) -> None:
        """
        Description:
            Release the advisory lock taken by __Lock_File. Best-effort, matching it.

        Args:
            (1) file_obj [file(object)]: The open file to unlock.
        """

        try:
            # Fcntl (Unix file control) [Python standard library, POSIX only]
            import fcntl
            fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)
        except (ImportError, OSError, ValueError):
            pass

    def __Append_Csv_Summary(self, Summary_Str: Summary_Str, now: datetime) -> None:
        """
        Description:
            Append exactly one row to the static run-summary CSV. The header row is
            written only when the file is created (or is empty); an existing file is
            appended to, never rewritten. A header that does not match the current
            columns is not silently misaligned — the row is aligned to the existing
            header and a warning is logged into the '.txt' file. The append is guarded
            by an exclusive file lock so concurrent runs cannot interleave a row.

        Args:
            (1) Summary_Str [Summary_Str(object)]: The computed run statistics.
            (2) now [datetime(object)]: The stop time, used to timestamp any warning.
        """

        row = Render_Summary_Csv_Row(Summary_Str)
        os.makedirs(os.path.dirname(self.__csv_path) or '.', exist_ok=True)

        # The file is opened as plain UTF-8; the byte-order mark is written by hand
        # only for a fresh file (see CONST_CSV_BOM), because the 'utf-8-sig' codec
        # would otherwise re-emit the mark on every append and corrupt the stream.
        with open(self.__csv_path, 'a', newline='', encoding='utf-8') as csv_file:
            self.__Lock_File(csv_file)
            try:
                write_header = os.fstat(csv_file.fileno()).st_size == 0
                if not write_header:
                    existing_header = self.__Read_Existing_Header()
                    if existing_header is not None and existing_header != CONST_CSV_COLUMNS:
                        self.__Write_Line('run-summary CSV header does not match the '
                                          'current columns; the row is aligned to the existing '
                                          f'header ({self.__csv_path})', now, CONST_LEVEL_WARNING)
                        row = self.__Align_Row_To_Header(existing_header, row)

                writer = csv.writer(csv_file, delimiter=self.__csv_delimiter)
                if write_header:
                    csv_file.write(CONST_CSV_BOM)
                    writer.writerow(CONST_CSV_COLUMNS)
                writer.writerow(row)
                csv_file.flush()
                try:
                    os.fsync(csv_file.fileno())
                except (OSError, ValueError):
                    pass
            finally:
                self.__Unlock_File(csv_file)

    def Close(self) -> None:
        """
        Description:
            Close the run: stamp the stop time, close any open session at that time,
            write the 'Application stopped' line, append the run-summary CSV row, and
            close the file. Idempotent — running it from the try/finally, the atexit
            hook and a signal handler is harmless.

            The '.txt' file ends with the 'Application stopped' line; the statistical
            summary lives only in the CSV. A failure to append the CSV row is logged
            into the '.txt' file and never prevents that file from closing cleanly.
        """

        with self.__lock:
            if self.__closed:
                return
            self.__closed = True

            now = self.__clock()
            self.__stop_time = now

            # Close an open session at the stop time and mark it accordingly.
            if self.__open_session is not None:
                Session_Str_i = self.__open_session
                Session_Str_i.End = now
                Session_Str_i.Closed_At_Shutdown = True
                self.__open_session = None
                duration = Format_HMS((now - Session_Str_i.Start).total_seconds())
                self.__Write_Line(f'Camera disconnected — session {Session_Str_i.Index} ended '
                                  f'(duration={duration}) (closed at shutdown)', now)

            # Append the run summary as one CSV row while the '.txt' handle is still
            # open, so a header-mismatch warning or a write failure can be reported into
            # it. The append never raises out of shutdown. This happens before the final
            # 'Application stopped' line, so that line always remains the last one in the
            # '.txt' file even when the CSV write fails.
            try:
                self.__Append_Csv_Summary(self.Compute_Summary(now), now)
            except Exception as error:  # noqa: BLE001 - shutdown must not raise
                self.__Write_Line(f'failed to write the run summary CSV row: {error}',
                                  now, CONST_LEVEL_ERROR)

            self.__Write_Line('Application stopped', now)

            if self.__file is not None and not self.__file.closed:
                self.__file.flush()
                try:
                    os.fsync(self.__file.fileno())
                except (OSError, ValueError):
                    pass
                self.__file.close()

            if self.__install_handlers:
                self.__Remove_Handlers()

    # << CONTEXT MANAGER >> #
    def __enter__(self) -> 'Session_Logger_Cls':
        """
        Description:
            Enter the runtime context and return the logger itself.

        Returns:
            (1) parameter [Session_Logger_Cls(object)]: This logger.
        """

        return self

    # << CONTEXT MANAGER >> #
    def __exit__(self, exc_type: tp.Any, exc_value: tp.Any, traceback: tp.Any) -> bool:
        """
        Description:
            Leave the runtime context: close the run (appending the CSV summary row)
            and let any exception propagate, so a run that ends in an exception still
            leaves a complete '.txt' file and its CSV row.

        Args:
            (1) exc_type [any]: The exception type, or None.
            (2) exc_value [any]: The exception instance, or None.
            (3) traceback [any]: The traceback, or None.

        Returns:
            (1) parameter [bool]: Always False, so the exception is not suppressed.
        """

        self.Close()
        return False

    # ----------------------------------------------------------- shutdown handlers

    def __Install_Handlers(self) -> None:
        """
        Description:
            Register the atexit hook and, on the main thread, the SIGINT/SIGTERM
            handlers, so an interrupted or terminated run still writes its summary.
        """

        atexit.register(self.Close)
        if threading.current_thread() is threading.main_thread():
            for signum in (signal.SIGINT, signal.SIGTERM):
                try:
                    self.__previous_signal_handlers[signum] = signal.signal(signum, self.__Handle_Signal)
                except (ValueError, OSError):
                    # Signal not settable in this context; atexit still covers shutdown.
                    pass

    def __Remove_Handlers(self) -> None:
        """
        Description:
            Undo Install_Handlers: unregister the atexit hook and restore the previous
            signal handlers. Best-effort, so it never raises during shutdown.
        """

        try:
            atexit.unregister(self.Close)
        except Exception:  # noqa: BLE001 - shutdown must not raise
            pass
        for signum, handler in self.__previous_signal_handlers.items():
            try:
                signal.signal(signum, handler)
            except (ValueError, OSError, TypeError):
                pass
        self.__previous_signal_handlers = {}

    def __Handle_Signal(self, signum: int, frame: tp.Any) -> None:
        """
        Description:
            Signal handler for SIGINT/SIGTERM: write the summary via Close, then chain
            to the previous handler (or re-raise the default behaviour) so the process
            still terminates as it otherwise would.

        Args:
            (1) signum [int]: The signal number.
            (2) frame [any]: The interrupted stack frame.
        """

        self.Close()
        previous = self.__previous_signal_handlers.get(signum)
        if callable(previous):
            previous(signum, frame)
        elif signum == signal.SIGINT:
            raise KeyboardInterrupt
