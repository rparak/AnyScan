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
# File Name: ../Logger/Core.py
## =========================================================================== ##

# System (Default)
import os
import csv
import atexit
import signal
import threading
from datetime import datetime
# Dataclasses (Data Classes)
from dataclasses import dataclass
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan — the one parser of a configuration file's name (hardware / mode)
#   ../Configuration/Core
from Configuration.Core import Hardware_And_Mode

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
# The complete set of levels the logger ever writes. Parse_Line accepts a bracketed field as
# a level ONLY when it is one of these, so a message that merely contains a '[WORD]' sequence
# is never mistaken for a level field.
#   Unit [Tuple<string>]
CONST_LEVELS = (CONST_LEVEL_INFO, CONST_LEVEL_WARNING, CONST_LEVEL_ERROR)
# The width the bracketed level is padded to — the longest level ('WARNING') — so the
# message column starts at the same offset on every line.
#   Unit [int]
CONST_LEVEL_WIDTH = 7
# The timestamp formats. The date and the per-line time are configurable. The filename
# time carries seconds: one run, one file. At minute resolution a relaunch within the same
# minute (the Configuration dialog asks for a relaunch) reopened the previous run's file with
# 'w' and wiped it, and both CSV rows then named the one surviving file.
#   Unit [string]
CONST_DATE_FORMAT = '%Y-%m-%d'
CONST_TIME_FORMAT = '%H:%M:%S'
CONST_FILENAME_TIME_FORMAT = '%H-%M-%S'
# The timestamp formats used inside the run-summary CSV. These are fixed by the
# CSV column contract and are deliberately independent of the per-line formats
# above, so the injected line formats never change the CSV layout.
#   Unit [string]
CONST_CSV_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
# The run-summary CSV is named after the HARDWARE of the loaded configuration, never a constant
# here: a run on 'Config_<Hardware>_Mode_<Mode>.yaml' summarises into 'log_<Hardware>.csv', so
# two modes on one camera share one summary and another camera starts its own file instead of
# silently appending into this one's. (The row is a time account only, so modes never mix
# measurements in it.) A name without a mode part keeps its whole stem, so the pre-mode
# 'Config_<id>.yaml' gave, and still gives, 'log_<id>.csv'. A logger given no configuration
# (tests, tooling) writes to an explicitly unattributed file that belongs to no hardware.
#   Unit [string]
CONST_CSV_FILENAME_TEMPLATE = 'log_{config_id}.csv'
CONST_CSV_UNCONFIGURED_ID = 'unconfigured'
# The run-summary CSV's delimiter.
#   Unit [string]
CONST_CSV_DELIMITER = ','
# The run-summary CSV columns, in the exact order they are written. The header row is this list;
# each data row is rendered one-to-one from a Summary_Str. The row is the run's TIME ACCOUNT only:
# when the application ran, for how long, how much of that a camera was connected, and how much
# it was idle (cycle_time == total_session_time + idle_time exactly). Counts, errors, confidence
# and inference figures are not summarised here; the '.txt' log beside each row holds every event.
#   Unit [Vector<string>]
CONST_CSV_COLUMNS = ['log_file', 'application_start', 'application_stop', 'cycle_time',
                     'total_session_time', 'idle_time']
# A CSV whose header is not exactly CONST_CSV_COLUMNS is never appended to: its rows would mean
# something different from the rows after them. It is renamed aside, byte-for-byte unchanged, as
# '<name>_until_<date>.csv' — the date its last row was written — and the canonical name starts
# afresh with the current header, so the file a reader finds under the canonical name is the live
# one and the history sits beside it under a name that says what it is.
#   Unit [string]
CONST_CSV_ARCHIVE_TEMPLATE = '{stem}_until_{date}{suffix}{extension}'
# The byte-order mark written once at the head of a freshly created CSV, so Excel
# opens the file as UTF-8. It is written explicitly (rather than via the
# 'utf-8-sig' codec) because that codec re-emits the mark on every append, which
# would corrupt the file mid-stream when a row is added to an existing file.
#   Unit [string]
CONST_CSV_BOM = '﻿'
# The event markers: a fixed token at the END of the message of each line that opens or closes the run
# or a camera connection. A reader of the log (Logger.Station_Events) matches these tokens, never the
# sentence before them, so a line can be reworded freely as long as it keeps its marker — and a line
# that loses its marker fails test/Logger/test_station_events.py. They name the LOG's own events; what
# they mean to another system is that reader's mapping, not the logger's.
#   Unit [string]
CONST_MARKER_RUN_START = '#run-start'
CONST_MARKER_RUN_STOP = '#run-stop'
CONST_MARKER_CONNECTION_START = '#connection-start'
CONST_MARKER_CONNECTION_END = '#connection-end'
#   Unit [Tuple<string>]
CONST_MARKERS = (CONST_MARKER_RUN_START, CONST_MARKER_RUN_STOP, CONST_MARKER_CONNECTION_START,
                 CONST_MARKER_CONNECTION_END)
# The line that opens every run, written by the logger itself at its start time — so the run's start
# in the log, the '.txt' file name and the CSV's application_start are one moment.
#   Unit [string]
CONST_RUN_START_LINE = 'Application started. ' + CONST_MARKER_RUN_START


@dataclass
class Log_Line_Str:
    """
    Description:
        One log line's fields, as a reader (the UI log view) renders them: date, time, level
        and message. On the LIVE path the logger builds this at the write site from the fields
        it already has — before they are joined — and hands it to the sink, so the live view
        never parses. On the SEED path the view rebuilds it from a file line with Parse_Line.
        Either way it is the one structured form; nothing re-derives the fields by a second
        route, so the file and the view cannot drift.
    """

    # The date field, exactly as written (default CONST_DATE_FORMAT, '2026-09-12').
    #   Unit [string]
    Date: str = ''
    # The time field, exactly as written (default CONST_TIME_FORMAT, '12:16:04').
    #   Unit [string]
    Time: str = ''
    # The severity level, unpadded ('INFO', 'WARNING' or 'ERROR'); empty when a seeded line
    # could not be parsed.
    #   Unit [string]
    Level: str = ''
    # The human-readable message that follows the level field. For an UNPARSED seed line this
    # holds the whole raw line, so the view can render it verbatim.
    #   Unit [string]
    Message: str = ''
    # Whether the fields are trustworthy. True on the live path (built from real fields) and
    # for a file line that matched the format; False for a seed line that did not match (a
    # wrapped continuation of a multi-line message, or foreign text), which the view renders
    # raw in the muted tone rather than mis-splitting or dropping.
    #   Unit [bool]
    Parsed: bool = True


def __Looks_Like_Stamp(stamp: str) -> bool:
    """
    Description:
        Whether a candidate timestamp looks like '<date> <time-with-colon>' — a space between
        two non-empty tokens, the date starting with a digit and the time containing a colon.
        This rejects a message fragment that merely happens to sit before a '[WORD]' sequence,
        so Parse_Line does not mis-split it.

    Args:
        (1) stamp [string]: The text before the first ' [' delimiter.

    Returns:
        (1) parameter [bool]: True when the text is timestamp-shaped.
    """

    date, space, time = stamp.partition(' ')
    return bool(space) and bool(date) and date[0].isdigit() and ':' in time


def Parse_Line(line: str) -> Log_Line_Str:
    """
    Description:
        Split one already-written log line back into its four fields — the inverse of the
        '<date> <time> [LEVEL  ] message' shape __Write_Line produces. It lives beside that one
        formatter so the format and its inverse cannot drift, and it is the ONLY parser: it is
        used solely to SEED the view from the file (the live path is handed the fields directly
        and never parses), and the file holds text the application does not control — model
        descriptions, driver error strings, file paths, audit lines quoting arbitrary caption text.

        So it never guesses: a bracketed field is treated as a level ONLY when it is a real
        level (CONST_LEVELS) AND the text before it is timestamp-shaped. Anything else — a
        message containing '[WARNING]', a path with a ' [' in it, a wrapped continuation line
        of a multi-line message — is returned whole as the message with Parsed=False, so the
        view renders it raw rather than mis-splitting it. Nothing is ever dropped.

    Args:
        (1) line [string]: One formatted log line, without its trailing newline.

    Returns:
        (1) parameter [Log_Line_Str(object)]: The parsed fields, or the whole line as an
            unparsed message (Parsed=False) when it does not match the format.
    """

    # The timestamp ends at the first ' [' — the level bracket. A real timestamp never
    # contains '[', and a real level never contains ']', so the first ' [' and the first '] '
    # after it are the only candidate delimiters.
    stamp, sep, rest = line.partition(' [')
    if sep:
        level_field, closed, message = rest.partition('] ')
        level = level_field.strip()
        if closed and level in CONST_LEVELS and __Looks_Like_Stamp(stamp):
            date, _, time = stamp.partition(' ')
            return Log_Line_Str(Date=date, Time=time, Level=level, Message=message, Parsed=True)
    # Not a well-formed line: keep it whole, marked unparsed, so nothing is lost or mis-split.
    return Log_Line_Str(Message=line, Parsed=False)


def Event_Marker(Log_Line_Str: Log_Line_Str) -> str:
    """
    Description:
        The event marker a parsed log line ends with (CONST_MARKERS), or '' when it carries none. Only
        a parsed line counts, and only its LAST token, so a message that merely quotes a marker
        mid-sentence is not an event.

    Args:
        (1) Log_Line_Str [Log_Line_Str(object)]: One line, from Parse_Line.

    Returns:
        (1) parameter [string]: The marker, or ''.
    """

    if not Log_Line_Str.Parsed:
        return ''
    token = Log_Line_Str.Message.rsplit(' ', 1)[-1]
    return token if token in CONST_MARKERS else ''


def Line_Time(Log_Line_Str: Log_Line_Str) -> datetime:
    """
    Description:
        A parsed line's date and time as the naive LOCAL datetime the logger wrote (the default
        CONST_DATE_FORMAT and CONST_TIME_FORMAT, which the application uses). The log stores no zone.

    Args:
        (1) Log_Line_Str [Log_Line_Str(object)]: One parsed line, from Parse_Line.

    Returns:
        (1) parameter [datetime(object)]: The line's local time, without a zone.
    """

    return datetime.strptime('%s %s' % (Log_Line_Str.Date, Log_Line_Str.Time),
                             '%s %s' % (CONST_DATE_FORMAT, CONST_TIME_FORMAT))


def Escape_Message(text: str) -> str:
    """
    Description:
        Make a message safe for the line-oriented log: a carriage return or newline becomes
        the two visible characters '\\r' / '\\n', so ONE logged event is always ONE physical
        file line. This is decided at the write end, not the read end — the same escaped text
        goes to the file and to the live sink, so a reloaded file reproduces the live view
        exactly, with no orphaned continuation line to reunite. Only line breaks are touched;
        backslashes are left as-is (the text is never turned back into a real newline, so the
        escape need not be invertible, and file paths stay readable).

    Args:
        (1) text [string]: The raw message, possibly multi-line.

    Returns:
        (1) parameter [string]: The message with its line breaks escaped to visible sequences.
    """

    return text.replace('\r', '\\r').replace('\n', '\\n')


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
        disconnection.
    """

    # The 1-based index of the session within the run.
    Index: int = 0
    # The connection time; the disconnection time (None while still open).
    Start: tp.Optional[datetime] = None
    End: tp.Optional[datetime] = None


@dataclass
class Error_Str:
    """
    Description:
        One tracked error: its message, the time it occurred and the time it was resolved
        (None while unresolved). The run keys it by its identifier (Log_Error's return value).
    """

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
        The computed time account for one application run. This is the pure result of reading
        the recorded state at a given stop time; it holds raw values (times and durations in
        seconds) so the CSV renderer, not the computation, owns the formatting.
    """

    # The filename of the matching '.txt' log (e.g. 'log_2026-09-12_12-16-04.txt').
    #   Unit [string]
    Log_File: str = ''
    # The application start and stop times.
    #   Unit [datetime(object)]
    Application_Start: tp.Optional[datetime] = None
    Application_Stop: tp.Optional[datetime] = None
    # The whole-run cycle time, start -> stop.
    #   Unit [float]
    Cycle_Seconds: float = 0.0
    # The summed duration of the camera sessions.
    #   Unit [float]
    Total_Session_Seconds: float = 0.0
    # The time no session was open, cycle_seconds - total_session_seconds.
    #   Unit [float]
    Idle_Seconds: float = 0.0


def Csv_Filename_For_Config(config_path: tp.Optional[str]) -> str:
    """
    Description:
        The run-summary CSV filename for a configuration file: 'log_<Hardware>.csv', the hardware
        part of 'Config_<Hardware>_Mode_<Mode>.yaml' (Configuration.Core.Hardware_And_Mode, the
        one parser of that name) — so 'Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_Seg_Anything
        .yaml' keeps the existing 'log_a2A1920_51gcPRO_Computar_M1228_MPW3.csv', shared by every
        mode on that camera. No configuration (None) gives 'log_unconfigured.csv', a file no
        camera's summary shares.

    Args:
        (1) config_path [string or None]: The loaded configuration file path, or None.

    Returns:
        (1) parameter [string]: The CSV filename (no directory).
    """

    if not config_path:
        return CONST_CSV_FILENAME_TEMPLATE.format(config_id=CONST_CSV_UNCONFIGURED_ID)
    hardware, _mode = Hardware_And_Mode(config_path)
    if not hardware:
        hardware = os.path.splitext(os.path.basename(config_path))[0]
    return CONST_CSV_FILENAME_TEMPLATE.format(config_id=hardware)


def Render_Summary_Csv_Row(Summary_Str: Summary_Str) -> tp.List[str]:
    """
    Description:
        Render one computed summary into the ordered list of CSV cell values that
        matches CONST_CSV_COLUMNS one-to-one. This is pure and holds every formatting
        decision (full-second datetimes, HH:MM:SS durations), so it can be tested without
        touching the file system.

    Args:
        (1) Summary_Str [Summary_Str(object)]: The computed run statistics.

    Returns:
        (1) parameter [Vector<string>]: The data row, aligned to CONST_CSV_COLUMNS.
    """

    return [Summary_Str.Log_File,
            Summary_Str.Application_Start.strftime(CONST_CSV_DATETIME_FORMAT),
            Summary_Str.Application_Stop.strftime(CONST_CSV_DATETIME_FORMAT),
            Format_HMS(Summary_Str.Cycle_Seconds),
            Format_HMS(Summary_Str.Total_Session_Seconds),
            Format_HMS(Summary_Str.Idle_Seconds)]


class Session_Logger_Cls(object):
    """
    Description:
        A plain-text session logger. It records the full lifecycle of one application
        run to a single '.txt' file, one '[Date] [Time] [Info]' line per event, ending
        with the 'Application stopped' line. When the application closes it also appends
        exactly one time-account row, per run, to a single run-summary CSV file that
        accumulates over every run and is never rewritten or truncated; a file with an older
        column set is renamed aside unchanged and a fresh one started (CONST_CSV_ARCHIVE_TEMPLATE).

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
            (6) csv_filename [string]: An explicit run-summary CSV filename, overriding the
                name derived from config_path. An absolute path is honoured as-is; otherwise it
                is resolved inside log_dir.
            (7) config_path [string or None]: REQUIRED, keyword-only: the configuration file the
                run loaded, which names the CSV (Csv_Filename_For_Config). It has no default so
                every caller states which setup the summary belongs to; None is an explicit 'no
                configuration' and writes to log_unconfigured.csv.

        Example:
            Initialization:
                # Initialize the class.
                Cls = Session_Logger_Cls(config_path=CONST_DEFAULT_CONFIG_FILE)

            Features:
                # Log lifecycle events and close (which appends the CSV summary row). The
                # 'Application started' line is the logger's own, written at construction.
                Cls.Log_Camera_Connected(); Cls.Close()
    """

    def __init__(self, log_dir: tp.Optional[str] = None,
                 clock: tp.Callable[[], datetime] = datetime.now,
                 date_format: str = CONST_DATE_FORMAT, time_format: str = CONST_TIME_FORMAT,
                 install_handlers: bool = True, csv_filename: tp.Optional[str] = None, *,
                 config_path: tp.Optional[str]) -> None:

        # << PRIVATE >> #
        # Injected time provider and formats.
        self.__clock = clock
        self.__date_format = date_format
        self.__time_format = time_format

        # The run's start time drives both the filename and the summary; it is taken
        # once, at construction, not at the first log line.
        self.__start_time = clock()
        self.__stop_time = None

        # The per-run bookkeeping: the camera sessions (the CSV's time account) and the tracked
        # errors (the '.txt' reports each one's resolution and how long it lasted).
        self.__sessions = []
        self.__open_session = None
        self.__errors = []
        self.__errors_by_id = {}
        self.__next_error_id = 1

        # A re-entrant lock guards every write and every state mutation, so the API is
        # safe to call from multiple threads.
        self.__lock = threading.RLock()
        self.__closed = False

        # An optional sink that receives each formatted line as it is written, so a live
        # reader (the UI log view) shows exactly what went to disk without a second
        # formatter. It is set after construction (Set_Line_Sink); the call is wrapped so a
        # failing sink can never stop a line reaching the file.
        self.__line_sink = None

        # Create the file for this run — never reopen an existing one. The directory is created if
        # it does not exist.
        self.__log_dir = os.path.abspath(log_dir) if log_dir is not None else CONST_DEFAULT_LOG_DIR
        os.makedirs(self.__log_dir, exist_ok=True)
        self.__path, self.__file = self.__Create_Log_File(self.__Build_Filename(self.__start_time))
        # The file is held under an exclusive lock for as long as the run writes it, so a reader of
        # earlier logs (Logger.Station_Events) can tell a live run's log from a crashed one.
        self.__Lock_File_Nonblocking(self.__file)
        # The run's first line, at its start time.
        with self.__lock:
            self.__Write_Line(CONST_RUN_START_LINE, self.__start_time)

        # An optional callback run with this log's path once Close has closed the file — the export
        # of what the log recorded (Set_Close_Callback). It runs on every close path.
        self.__close_callback = None

        # The run-summary CSV, named after the loaded configuration (Csv_Filename_For_Config);
        # an explicit csv_filename overrides it, an absolute one is honoured as-is, otherwise it
        # is resolved inside the log directory alongside the '.txt' file.
        csv_name = (csv_filename if csv_filename is not None
                    else Csv_Filename_For_Config(config_path))
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
            Build the per-run filename 'log_[date]_[hour-minutes-seconds].txt' from the
            start time (e.g. 'log_2026-09-12_14-37-02.txt').

        Args:
            (1) start_time [datetime(object)]: The application start time.

        Returns:
            (1) parameter [string]: The filename.
        """

        return (f'log_{start_time.strftime(self.__date_format)}'
                f'_{start_time.strftime(CONST_FILENAME_TIME_FORMAT)}.txt')

    def __Create_Log_File(self, filename: str) -> tp.Tuple[str, tp.TextIO]:
        """
        Description:
            Create this run's '.txt' log in the log directory without ever reopening an existing
            one. The file is opened with 'x', which fails if it exists; the name then takes '_2',
            '_3', ... (the CSV archive's convention), so two runs started within the same second —
            a double-clicked launcher — still get one file each, and neither wipes the other.

        Args:
            (1) filename [string]: The preferred filename (Build_Filename).

        Returns:
            (1) parameter [string]: The path of the file created.
            (2) parameter [file(object)]: Its handle, open for writing.
        """

        stem, extension = os.path.splitext(filename)
        number = 1
        while True:
            name = filename if number == 1 else '%s_%d%s' % (stem, number, extension)
            path = os.path.join(self.__log_dir, name)
            try:
                return path, open(path, 'x', encoding='utf-8')
            except FileExistsError:
                number += 1

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
        # Escape line breaks so one event is always one file line — decided here, the single
        # write choke point, so a newline from ANY source (an exception message, a driver
        # error string) is neutralised without auditing every call site. The escaped text is
        # what goes to both the file and the sink, so the seed reproduces the live view.
        info = Escape_Message(info)
        date = now.strftime(self.__date_format)
        time = now.strftime(self.__time_format)
        line = '%s %s [%-*s] %s\n' % (date, time, CONST_LEVEL_WIDTH, level, info)
        self.__file.write(line)
        self.__file.flush()
        try:
            os.fsync(self.__file.fileno())
        except (OSError, ValueError):
            # fsync is best-effort; a flush already went out.
            pass
        # Feed the live sink AFTER the line is safely on disk, so a sink failure can never cost
        # the write. The fields go SEPARATED — as they are here, before joining — so the live
        # view renders what it was handed and never parses; the formatted line goes too (minus
        # the trailing newline) for a sink that wants the raw string.
        record = Log_Line_Str(Date=date, Time=time, Level=level, Message=info, Parsed=True)
        self.__Emit_To_Sink(record, line[:-1] if line.endswith('\n') else line)

    def __Emit_To_Sink(self, record: Log_Line_Str, line: str) -> None:
        """
        Description:
            Hand one line's fields (and its formatted string) to the optional live sink,
            wrapped so any failure in the sink (a rendering error in the UI, a disconnected
            view) is swallowed and never propagates back into the write path. Assumes the lock
            is held; the disk write has already completed by the time this is called.

        Args:
            (1) record [Log_Line_Str(object)]: The line's fields, already separated.
            (2) line [string]: The formatted line, without its trailing newline.
        """

        sink = self.__line_sink
        if sink is None:
            return
        try:
            sink(record, line)
        except Exception:  # noqa: BLE001 - a sink failure must never break logging to disk
            pass

    # ------------------------------------------------------------------ public API

    def Set_Close_Callback(self, callback: tp.Optional[tp.Callable[[str], None]]) -> None:
        """
        Description:
            Register (or clear, with None) a callback run with this log's path at the very end of
            Close, after the 'Application stopped' line is written and the file closed — so it sees
            the complete log, on every close path (the window, the launcher's try/finally, atexit, a
            signal). It runs once, like Close. The log is closed by then, so the callback reports its
            own failures; one that escapes is printed and never stops the shutdown.

        Args:
            (1) callback [function or None]: A callable taking the log's path, or None to detach.
        """

        with self.__lock:
            self.__close_callback = callback

    def Set_Line_Sink(self, sink: tp.Optional[tp.Callable[[str], None]]) -> None:
        """
        Description:
            Register (or clear, with None) an optional sink that receives each formatted line
            as it is written to disk — the seam a live reader (the UI log view) renders from,
            so it shows exactly what the file holds with no second formatter. The sink is
            called after the disk write and is fully wrapped, so nothing it does can prevent a
            line reaching the file. The view seeds itself from the file once, then follows via
            this sink.

        Args:
            (1) sink [function or None]: A callable taking (record, line) — the line's fields
                                         as a Log_Line_Str (already separated, so the live view
                                         never parses) and the formatted line without its
                                         trailing newline — or None to detach.
        """

        with self.__lock:
            self.__line_sink = sink

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
            Error_Str_i = Error_Str(Message=message, Start=now)
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
                self.__Write_Line(f'An error resolution arrived with no matching error '
                                  f'(error_id={error_id}).', now, CONST_LEVEL_WARNING)
                return
            if Error_Str_i.Resolved:
                self.__Write_Line(f'That error was already resolved (error_id={error_id}).',
                                  now, CONST_LEVEL_WARNING)
                return
            Error_Str_i.End = now
            Error_Str_i.Resolved = True
            downtime = Format_HMS((now - Error_Str_i.Start).total_seconds())
            # INFO: it is the RESOLUTION being reported, not the fault — the fault was
            # logged as ERROR when it happened.
            self.__Write_Line(f'Error {error_id} resolved after {downtime}: {Error_Str_i.Message}',
                              now, CONST_LEVEL_INFO)

    def Log_Camera_Connection_Attempt(self, info: str = '') -> None:
        """
        Description:
            Log that a connection to the camera is being attempted.

        Args:
            (1) info [string]: Optional detail (e.g. 'id=cam0, ip=192.168.1.40').
        """

        with self.__lock:
            detail = f' ({info})' if info else ''
            self.__Write_Line(f'Connecting to the camera{detail}.', self.__clock())

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
                self.__Write_Line(f'Camera connected while connection '
                                  f'{self.__open_session.Index} was still open. Closed it. '
                                  f'{CONST_MARKER_CONNECTION_END}', now, CONST_LEVEL_WARNING)
                self.__open_session = None
            Session_Str_i = Session_Str(Index=len(self.__sessions) + 1, Start=now)
            self.__sessions.append(Session_Str_i)
            self.__open_session = Session_Str_i
            detail = f' {info}.' if info else '.'
            self.__Write_Line(f'Camera connected{detail} Connection {Session_Str_i.Index} started. '
                              f'{CONST_MARKER_CONNECTION_START}', now)
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
                self.__Write_Line('Camera disconnected, but no connection was open.',
                                  now, CONST_LEVEL_WARNING)
                return
            Session_Str_i = self.__open_session
            Session_Str_i.End = now
            self.__open_session = None
            duration = Format_HMS((now - Session_Str_i.Start).total_seconds())
            detail = f' {info}.' if info else ''
            self.__Write_Line(f'Camera disconnected. Connection {Session_Str_i.Index} ended after '
                              f'{duration}.{detail} {CONST_MARKER_CONNECTION_END}', now)

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
            self.__Write_Line(f'The camera connection was lost{detail}.', now, CONST_LEVEL_ERROR)
            if self.__open_session is not None:
                Session_Str_i = self.__open_session
                Session_Str_i.End = now
                self.__open_session = None
                duration = Format_HMS((now - Session_Str_i.Start).total_seconds())
                self.__Write_Line(f'Connection {Session_Str_i.Index} ended after {duration}. '
                                  f'{CONST_MARKER_CONNECTION_END}', now)

    def Log_Scan_Started(self, scan_id: tp.Optional[int] = None) -> None:
        """
        Description:
            Log the start of a scan.

        Args:
            (1) scan_id [int]: Optional scan identifier.
        """

        with self.__lock:
            detail = f' (scan {scan_id})' if scan_id is not None else ''
            self.__Write_Line(f'Frame scan started{detail}.', self.__clock())

    def Log_Scan_Ended(self, scan_id: tp.Optional[int] = None) -> None:
        """
        Description:
            Log the end of a scan.

        Args:
            (1) scan_id [int]: Optional scan identifier.
        """

        with self.__lock:
            detail = f' (scan {scan_id})' if scan_id is not None else ''
            self.__Write_Line(f'Frame scan finished{detail}.', self.__clock())

    def Log_Analysis_Started(self, index: int, set_id: tp.Optional[str] = None) -> None:
        """
        Description:
            Log the start of an analysis as a sentence, naming its capture set so the log
            points at the files.

        Args:
            (1) index [int]: The 1-based analysis index within the session.
            (2) set_id [string]: The capture-set identifier for this analysis.
        """

        with self.__lock:
            line = 'Analysis %d started.' % index
            if set_id:
                line += ' Capture set %s.' % set_id
            self.__Write_Line(line, self.__clock())

    def Log_Cleared(self) -> None:
        """
        Description:
            Log that the operator pressed Clear (it resets the frame, the counters and the
            reading panel in the UI).
        """

        with self.__lock:
            self.__Write_Line('Cleared the frame, the counters and the reading panel',
                              self.__clock())

    def Log_Analysis_Finished(self, index: int, latency_ms: int, objects: int, scored: int,
                              mean_confidence: tp.Optional[int],
                              set_id: tp.Optional[str] = None) -> None:
        """
        Description:
            Log a finished analysis as a sentence. It carries the inference time
            and the mean detector confidence WITH its coverage — how many of the objects
            were scored — because the log is the forensic record and a mean over a partial
            set must say so; the short percentage-only form belongs in the UI, not here.

        Args:
            (1) index [int]: The 1-based analysis index within the session.
            (2) latency_ms [int]: The inference time in milliseconds.
            (3) objects [int]: The number of objects detected.
            (4) scored [int]: How many of them carry a confidence score.
            (5) mean_confidence [int]: The mean confidence percentage over the scored
                                       objects, or None when none are scored.
            (6) set_id [string]: The capture-set identifier for this analysis.
        """

        with self.__lock:
            if objects == 0:
                count_clause = 'No objects detected'
            else:
                count_clause = '%d object%s detected' % (objects, '' if objects == 1 else 's')
                if scored:
                    count_clause += (', mean confidence %d%% over %d of %d scored'
                                     % (mean_confidence, scored, objects))
                else:
                    count_clause += ', none scored for confidence'
            line = 'Analysis %d finished in %d ms. %s.' % (index, latency_ms, count_clause)
            if set_id:
                line += ' Capture set %s.' % set_id
            self.__Write_Line(line, self.__clock())

    def Log_Analysis_Timing(self, index: int, total_ms: int, stages: tp.List[tp.Tuple[str, int]],
                            other_ms: int, measurement_ms: int, first_after_load: bool) -> None:
        """
        Description:
            Log where a finished analysis's time went, as one sentence after its 'finished in' line:
            the total (that line's number), each stage, and 'other' — the numbers as given, so they
            add up to the total exactly when the caller derived 'other' from them. The measurement
            runs after the total stops and is named as outside it. The first analysis after a load
            says so, so a slow first analysis is visible, not averaged away.

            A negative 'other' means the stages overlap (one was counted twice): the line keeps the
            number and a WARNING line follows, so the fault is reported, never clamped.

        Args:
            (1) index [int]: The 1-based analysis index within the session.
            (2) total_ms [int]: The analysis's inference time (the 'finished in' number).
            (3) stages [Vector<Tuple<string, int>>]: Each stage's name and milliseconds, in order.
            (4) other_ms [int]: The total minus the stages.
            (5) measurement_ms [int]: The measurement's milliseconds (outside the total).
            (6) first_after_load [bool]: Whether this is the first analysis after a load.
        """

        with self.__lock:
            terms = ' + '.join('%s %d' % (name, ms) for name, ms in stages)
            line = ('Analysis %d timing%s: %d ms = %s + other %d. Measurement %d ms (not in the inference time).'
                    % (index, ' (first after load)' if first_after_load else '', total_ms, terms,
                       other_ms, measurement_ms))
            self.__Write_Line(line, self.__clock())
            if other_ms < 0:
                self.__Write_Line('Analysis %d timing does not add up: its stages sum to %d ms, %d ms more than '
                                  'the total, so a stage was counted twice.'
                                  % (index, total_ms - other_ms, -other_ms), self.__clock(), CONST_LEVEL_WARNING)

    def Log_Object_Detected(self, label: str, confidence: tp.Optional[int] = None,
                            bbox: tp.Optional[tp.Tuple[int, int, int, int]] = None,
                            crop_ms: tp.Optional[int] = None, describe_ms: tp.Optional[int] = None,
                            tokens: tp.Optional[tp.Tuple[int, int]] = None) -> None:
        """
        Description:
            Log one detected object: its type, its confidence as a percentage (omitted for
            a background-cue object with no score), its bounding box, and, when the analysis was
            timed, how long its crop and its description took and the describer's input and output
            token counts. The generated description is NOT logged here — it lives in the
            '_understanding.txt' of the same capture set, and repeating it makes the log unreadable
            at nine objects a frame; the timing rides on this line for the same reason.

        Args:
            (1) label [string]: The object's noun-phrase label.
            (2) confidence [int]: The confidence percentage, or None when unscored.
            (3) bbox [Vector<int> 1x4]: The bounding box (x, y, w, h).
            (4) crop_ms [int]: The crop's milliseconds, or None when not timed.
            (5) describe_ms [int]: The description's milliseconds, or None when not timed.
            (6) tokens [Tuple<int> 1x2]: (input, output) token counts, or None when not reported.
        """

        with self.__lock:
            parts = ['type=%s' % label]
            if confidence is not None:
                parts.append('confidence=%d%%' % confidence)
            if bbox is not None:
                parts.append('bbox=(' + ','.join(str(int(v)) for v in bbox) + ')')
            if crop_ms is not None:
                parts.append('crop=%d ms' % crop_ms)
            if describe_ms is not None:
                parts.append('describe=%d ms' % describe_ms)
            if tokens is not None:
                parts.append('input tokens=%d, output tokens=%d' % tokens)
            self.__Write_Line('Object detected: ' + ', '.join(parts) + '.', self.__clock())

    # -------------------------------------------------------------------- shutdown

    def Compute_Summary(self, stop_time: tp.Optional[datetime] = None) -> Summary_Str:
        """
        Description:
            Compute the run's time account for a stop time. This is pure: it reads the
            recorded state and never mutates it, so it is safe to call more than once
            and holds no formatting — the CSV renderer (Render_Summary_Csv_Row) owns
            that. This keeps 'compute summary' and 'render summary' separately testable.

            An open session is closed at the stop time. With zero sessions the summary is
            still complete: the whole cycle is idle.

        Args:
            (1) stop_time [datetime(object)]: The application stop time (defaults to the
                recorded stop time, or the clock if the logger is not yet closed).

        Returns:
            (1) parameter [Summary_Str(object)]: The computed run statistics.
        """

        with self.__lock:
            if stop_time is None:
                stop_time = self.__stop_time if self.__stop_time is not None else self.__clock()

            # Every figure is derived from the values AS WRITTEN, so a row's arithmetic checks out
            # when someone recomputes it: the cycle from the whole-second start/stop the row
            # prints, the session total rounded to whole seconds, and idle as the cycle minus
            # that total, so cycle_time == total_session_time + idle_time exactly.
            start_s = self.__start_time.replace(microsecond=0)
            stop_s = stop_time.replace(microsecond=0)
            cycle_seconds = (stop_s - start_s).total_seconds()
            session_exact = sum(((Session_Str_i.End if Session_Str_i.End is not None else stop_time)
                                 - Session_Str_i.Start).total_seconds()
                                for Session_Str_i in self.__sessions)
            # A connection spanning the whole run can round a second past the whole-second cycle;
            # cap it so idle never goes negative and the three columns still add up.
            session_seconds = float(min(round(session_exact), cycle_seconds))

            return Summary_Str(Log_File=os.path.basename(self.__path),
                               Application_Start=self.__start_time,
                               Application_Stop=stop_time,
                               Cycle_Seconds=cycle_seconds,
                               Total_Session_Seconds=session_seconds,
                               Idle_Seconds=cycle_seconds - session_seconds)

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

    def __Lock_File_Nonblocking(self, file_obj: tp.Any) -> None:
        """
        Description:
            Take an exclusive advisory lock on this run's own '.txt' without waiting: the run is its
            only writer, so the lock exists to be SEEN — Logger.Station_Events skips a log another
            process still holds. Best-effort, like __Lock_File: without fcntl (Windows) there is no
            lock, and a second instance's live log can be taken for a crashed one.

        Args:
            (1) file_obj [file(object)]: The open file to lock.
        """

        try:
            # Fcntl (Unix file control) [Python standard library, POSIX only]
            import fcntl
            fcntl.flock(file_obj.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
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

    def __Is_Current_File(self, file_obj: tp.Any) -> bool:
        """
        Description:
            Whether an open handle still refers to the file now at the CSV path. Another run may
            have renamed the CSV aside (an older column set, archived) while this one waited for
            the lock; writing through the stale handle would put the row into the archived file.

        Args:
            (1) file_obj [file(object)]: The open, locked CSV handle.

        Returns:
            (1) parameter [bool]: True when the handle and the path are the same file.
        """

        try:
            held, current = os.fstat(file_obj.fileno()), os.stat(self.__csv_path)
        except OSError:
            return False
        return (held.st_dev, held.st_ino) == (current.st_dev, current.st_ino)

    def __Archive_Path(self, modified: float) -> str:
        """
        Description:
            The name an older-format CSV is renamed to: '<name>_until_<date>.csv', the date its
            last row was written; '_2', '_3', ... when that name is already taken.

        Args:
            (1) modified [float]: The file's modification time (epoch seconds).

        Returns:
            (1) parameter [string]: The archive path, beside the CSV.
        """

        stem, extension = os.path.splitext(self.__csv_path)
        date = datetime.fromtimestamp(modified).strftime(CONST_DATE_FORMAT)
        for number in range(1, 1000):
            path = CONST_CSV_ARCHIVE_TEMPLATE.format(stem=stem, date=date,
                                                      suffix='' if number == 1 else '_%d' % number,
                                                      extension=extension)
            if not os.path.exists(path):
                return path
        raise OSError('no free archive name for %s' % self.__csv_path)

    def __Archive_Older_Format(self, now: datetime) -> None:
        """
        Description:
            When the CSV at the canonical path has a header other than CONST_CSV_COLUMNS, rename
            it aside, byte-for-byte unchanged (__Archive_Path), so the next row starts a fresh file
            instead of appending rows that mean something different under a header that no longer
            describes them. The check and the rename run under the file lock; a handle that no
            longer refers to the file at the path (another run archived it meanwhile) re-checks
            the new file. On a platform that cannot rename a file this process holds open
            (Windows) the rename runs just after the handle closes. The '.txt' log records it.

        Args:
            (1) now [datetime(object)]: The stop time, used to timestamp the log line.
        """

        for _attempt in range(3):
            if not os.path.exists(self.__csv_path):
                return
            deferred = None
            with open(self.__csv_path, 'rb') as csv_file:
                self.__Lock_File(csv_file)
                try:
                    if not self.__Is_Current_File(csv_file):
                        continue
                    first = csv_file.readline().decode('utf-8-sig', errors='replace').rstrip('\r\n')
                    header = next(csv.reader([first], delimiter=CONST_CSV_DELIMITER), [])
                    if not first or header == CONST_CSV_COLUMNS:
                        return
                    archive = self.__Archive_Path(os.fstat(csv_file.fileno()).st_mtime)
                    try:
                        os.rename(self.__csv_path, archive)
                    except PermissionError:
                        deferred = archive
                finally:
                    self.__Unlock_File(csv_file)
            if deferred is not None:
                os.rename(self.__csv_path, deferred)
                archive = deferred
            self.__Write_Line('The run-summary CSV had an older column set (%d columns); it was '
                              'renamed, unchanged, to %s and a new %s was started with the current '
                              '%d columns.' % (len(header), os.path.basename(archive),
                                               os.path.basename(self.__csv_path),
                                               len(CONST_CSV_COLUMNS)), now)
            return

    def __Append_Csv_Summary(self, Summary_Str: Summary_Str, now: datetime) -> None:
        """
        Description:
            Append exactly one row to the run-summary CSV. The header row is written only
            when the file is created (or is empty); an existing file with the current
            columns is appended to, never rewritten, and one with an older column set is
            first archived unchanged (__Archive_Older_Format), so no row is ever written
            under a header that does not describe it. The append is guarded by an exclusive
            file lock so concurrent runs cannot interleave a row.

        Args:
            (1) Summary_Str [Summary_Str(object)]: The computed run statistics.
            (2) now [datetime(object)]: The stop time, used to timestamp any warning.
        """

        row = Render_Summary_Csv_Row(Summary_Str)
        os.makedirs(os.path.dirname(self.__csv_path) or '.', exist_ok=True)
        # An older-format file is renamed aside first, so the row below starts a fresh file.
        self.__Archive_Older_Format(now)

        # The file is opened as plain UTF-8; the byte-order mark is written by hand
        # only for a fresh file (see CONST_CSV_BOM), because the 'utf-8-sig' codec
        # would otherwise re-emit the mark on every append and corrupt the stream.
        for attempt in range(3):
            csv_file = open(self.__csv_path, 'a', newline='', encoding='utf-8')
            self.__Lock_File(csv_file)
            if self.__Is_Current_File(csv_file) or attempt == 2:
                break
            # Renamed while waiting for the lock (another run archived it): reopen at the path.
            self.__Unlock_File(csv_file)
            csv_file.close()
        with csv_file:
            try:
                write_header = os.fstat(csv_file.fileno()).st_size == 0
                writer = csv.writer(csv_file, delimiter=CONST_CSV_DELIMITER)
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
                self.__open_session = None
                duration = Format_HMS((now - Session_Str_i.Start).total_seconds())
                self.__Write_Line(f'Connection {Session_Str_i.Index} ended after {duration} '
                                  f'(closed at shutdown). {CONST_MARKER_CONNECTION_END}', now)

            # Append the run summary as one CSV row while the '.txt' handle is still
            # open, so a header-mismatch warning or a write failure can be reported into
            # it. The append never raises out of shutdown. This happens before the final
            # 'Application stopped' line, so that line always remains the last one in the
            # '.txt' file even when the CSV write fails.
            try:
                self.__Append_Csv_Summary(self.Compute_Summary(now), now)
            except Exception as error:  # noqa: BLE001 - shutdown must not raise
                self.__Write_Line(f'Failed to write the run-summary CSV row: {error}.',
                                  now, CONST_LEVEL_ERROR)

            self.__Write_Line('Application stopped. ' + CONST_MARKER_RUN_STOP, now)

            if self.__file is not None and not self.__file.closed:
                self.__file.flush()
                try:
                    os.fsync(self.__file.fileno())
                except (OSError, ValueError):
                    pass
                self.__file.close()

            if self.__install_handlers:
                self.__Remove_Handlers()

            # The log is complete and closed: hand it to the export of what it recorded. Nothing can
            # be written to the log any more, so an escaping failure goes to the console.
            if self.__close_callback is not None:
                try:
                    self.__close_callback(self.__path)
                except Exception as error:  # noqa: BLE001 - shutdown must not raise
                    print('[ERROR] The close callback of %s failed: %s' % (os.path.basename(self.__path), error))

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
