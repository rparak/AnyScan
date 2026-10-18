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
# File Name: ../UI/Views/Log.py
## =========================================================================== ##

# System (Default)
import typing as tp
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import (QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
                             QScrollArea, QFrame)
# Custom Lib.: AnyScan UI — design tokens, style helpers and shared widgets
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
from UI.Utilities.Style import Font
#   ../UI/Widgets
from UI.Widgets import Card_Cls, Card_Head_Cls, Segmented_Control_Cls
# Custom Lib.: AnyScan — the logger's ONE line parser (format and inverse live together)
#   ../Logger/Core
from Logger.Core import Parse_Line, CONST_LEVEL_INFO, CONST_LEVEL_WARNING, CONST_LEVEL_ERROR

# The most lines the view holds; past it the oldest go (the file keeps every line). Each row is a
# widget with three labels, and a new row costs more the more rows the layout holds — measured
# offscreen: ~1 ms a line and +46 MB at 1,000 rows, ~13 ms a line and +455 MB at 10,000, ~39 ms
# and +909 MB at 20,000. A long shift writes well past 10,000 lines, so the view is capped.
#   Unit [int]
CONST_MAX_ROWS = 1000

"""
Description:
    The Log view — the session log shown live in the central area. Its source of truth is the
    logger: the logger hands each line's fields (and the formatted line) to a sink as it writes
    it, and this view renders from that sink, seeded once from the file at startup. The view
    NEVER formats a line and never re-derives the fields on its own — a live line arrives as the
    fields the logger wrote, and a seeded line is split by the logger's one Parse_Line — then
    lays date, time, level and message in columns. One formatter, so the file and the view
    cannot drift.

    Reading concerns that belong to the view, not the file: the timestamp and level are
    monospace and fixed-width so the message column starts at a consistent x; the level and
    message are coloured by severity (the timestamp stays muted, so the eye lands on severity
    first); a filter hides lines by level WITHOUT touching the file, and a count of the lines
    currently shown makes an empty filter read as 'none occurred'; and the view follows the
    tail unless the operator has scrolled up, in which case it holds their position and shows
    that new lines have arrived rather than yanking them back down.
"""
# The filter segments, in order, as (key, label). 'all' is first, so it is the default
# selection of the segmented control.
#   Unit [Vector<Tuple<string> 1x2>]
CONST_FILTER_SEGMENTS = (('all', 'All'), ('info', 'Info'), ('warning', 'Warning'),
                         ('error', 'Error'))
# The filter key -> level string mapping. 'all' is absent: it matches every level and is
# handled as the no-filter case, never by a lookup here.
#   Unit [Dict<string, string>]
CONST_FILTER_TO_LEVEL = {'info': CONST_LEVEL_INFO, 'warning': CONST_LEVEL_WARNING,
                         'error': CONST_LEVEL_ERROR}
# The level -> font weight ramp lives in Style (Style.CONST_LEVEL_WEIGHTS / Log_Level_Weight),
# shared with the confidence colouring: severity is carried by the level word, its colour AND its
# weight, because the WARNING amber and ERROR red collapse to nearly one colour under a red-green
# deficiency (ΔE ~8 in deuteranopia), so a heavier weight for the more severe level keeps them
# apart for a viewer who cannot rely on the colour.
# The widest sample of each fixed-width column, measured once to set the column widths so the
# message starts at the same x on every row regardless of content.
#   Unit [string]
CONST_TS_SAMPLE = '0000-00-00 00:00:00'
CONST_LEVEL_SAMPLE = CONST_LEVEL_WARNING          # the longest level word
# The gap between the timestamp, level and message columns, and the top/bottom padding of a
# row (px).
#   Unit [int]
CONST_COL_GAP = 14
CONST_ROW_PAD = 2
# How close to the bottom (px) still counts as 'at the bottom' for tail-following, so a
# rounding of the scrollbar range never leaves the view one pixel short and stops following.
#   Unit [int]
CONST_TAIL_EPSILON = 4


class Log_View_Cls(Card_Cls):
    """
    Description:
        The session-log view. It renders from the logger's line sink (Sink) — plus a one-off
        seed from the file (Seed_From_File) — and never formats a line itself. Rows are laid
        in three columns (timestamp, level, message); the filter and the tail-follow behaviour
        are view concerns that never touch the file.

        Thread-safety: Sink is called from whichever thread logged the event, so it only emits
        a Qt signal (Record_Received); the actual widget work runs on the GUI thread in the
        connected slot. Emitting a signal is safe across threads, and the logger wraps the
        Sink call, so a render fault here can never stop a line reaching disk.
    """

    # << SIGNAL >> #
    # Internal plumbing: the sink emits this (thread-safe) and the GUI-thread slot renders it.
    # It carries the Log_Line_Str the logger already built, so the live path never parses.
    Record_Received = pyqtSignal(object)

    def __init__(self, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)

        # << PRIVATE >> #
        # One (level, row_widget) per rendered line, in order, for filtering — the newest
        # CONST_MAX_ROWS; whether older lines have been dropped (the count then says so).
        self.__rows = []
        self.__trimmed = False
        # The count of lines currently shown under the active filter.
        self.__shown = 0
        # Tail-follow state: True while the view sticks to the bottom; the count of lines that
        # arrived while the operator was scrolled up.
        self.__follow = True
        self.__new_count = 0

        # Fixed column widths, from the monospace metrics of the widest sample — so the
        # message column starts at the same x on every row.
        metrics = QFontMetrics(Font(Style.CONST_TYPE_LOG, mono=True))
        self.__ts_width = metrics.horizontalAdvance(CONST_TS_SAMPLE)
        self.__level_width = metrics.horizontalAdvance(CONST_LEVEL_SAMPLE)

        self.__Build_Head()
        self.__Build_Body()

        # Live lines arrive on the GUI thread through this slot; the sink only emits the signal.
        self.Record_Received.connect(self.__On_Record_Received)

    # ------------------------------------------------------------------ construction

    def __Build_Head(self) -> None:
        """
        Description:
            Build the card head: the title, the tail 'new lines' indicator, the shown-count,
            and the level filter (the console's one segmented-control look).
        """

        head = Card_Head_Cls('log', 'Session log')

        # The 'new lines' indicator — shown only while scrolled up; clicking it jumps to the
        # bottom and resumes following.
        self.__new_indicator = QPushButton('')
        self.__new_indicator.setCursor(Qt.PointingHandCursor)
        self.__new_indicator.setFont(Font(9, tracking=2))
        self.__new_indicator.setStyleSheet(
            'QPushButton { border: 1px solid %s; background: %s; color: %s;'
            'padding: 3px 12px; }'
            'QPushButton:hover { background: %s; color: %s; }'
            % (Style.CONST_CARD_BORDER, Style.CONST_CARD, Style.CONST_INK, Style.CONST_CONTROL_HOVER,
               Style.CONST_INK))
        self.__new_indicator.clicked.connect(self.__Scroll_To_Bottom)
        self.__new_indicator.hide()
        head.box.addWidget(self.__new_indicator)
        head.box.addSpacing(12)

        self.__count = QLabel('')
        self.__count.setFont(Font(9))
        self.__count.setStyleSheet('color: %s;' % Style.CONST_INK_MUTE)
        head.box.addWidget(self.__count)
        head.box.addSpacing(12)

        self.__filter = Segmented_Control_Cls(CONST_FILTER_SEGMENTS)
        self.__filter.Segment_Selected.connect(lambda _key: self.__Apply_Filter())
        head.box.addWidget(self.__filter)

        self.box.addWidget(head)
        self.__Set_Count(0)

    def __Build_Body(self) -> None:
        """
        Description:
            Build the scrolling rows area and wire the tail-follow signals. Rows are added to
            a top-aligned column inside a scroll area; the scrollbar's range/value changes
            drive the follow behaviour.
        """

        container = QWidget()
        container.setStyleSheet('background: transparent;')
        self.__rows_box = QVBoxLayout(container)
        self.__rows_box.setContentsMargins(14, 12, 14, 12)
        self.__rows_box.setSpacing(0)
        self.__rows_box.setAlignment(Qt.AlignTop)

        self.__scroll = QScrollArea()
        self.__scroll.setWidget(container)
        self.__scroll.setWidgetResizable(True)
        self.__scroll.setFrameShape(QFrame.NoFrame)
        self.__scroll.setStyleSheet(Style.Scroll_Style(framed=True))
        self.box.addWidget(self.__scroll, 1)

        bar = self.__scroll.verticalScrollBar()
        # rangeChanged fires after a row is added and laid out: jump to the new bottom only
        # while following. valueChanged tracks whether the operator is at the bottom.
        bar.rangeChanged.connect(self.__On_Range_Changed)
        bar.valueChanged.connect(self.__On_Value_Changed)

    # -------------------------------------------------------------------- public API

    def Sink(self, record: tp.Any, line: str) -> None:
        """
        Description:
            The logger's line sink. It is handed the line's fields ALREADY SEPARATED (a
            Log_Line_Str), so the live path never parses — parsing is only ever the seed path's
            job. It is called from whichever thread logged the event, so it does no widget
            work: it only emits Record_Received, delivering the record to the GUI thread.
            Emitting is safe across threads, and the logger wraps this call, so nothing here
            can stop a line reaching disk. The formatted `line` is part of the sink protocol
            (for a sink that wants the raw string); this view renders from the fields.

        Args:
            (1) record [Log_Line_Str(object)]: The line's fields, already separated.
            (2) line [string]: The formatted line (unused here — the view renders fields).
        """

        self.Record_Received.emit(record)

    def Seed_From_File(self, path: str) -> None:
        """
        Description:
            Seed the view once from the log file — the lines written before the sink was
            attached (e.g. the application-start line). Each line is parsed by Append_Line and
            rendered by Append_Record, as a live line is, so there is one rendering route. A missing or
            unreadable file seeds nothing rather than raising.

        Args:
            (1) path [string]: The log file to read.
        """

        try:
            with open(path, 'r', encoding='utf-8') as handle:
                lines = [line for line in handle.read().splitlines() if line]
        except OSError:
            return
        # Only the lines the view would keep are rendered: a long file is not built up row by row
        # only to be trimmed again.
        if len(lines) > CONST_MAX_ROWS:
            self.__trimmed = True
            lines = lines[-CONST_MAX_ROWS:]
        for line in lines:
            self.Append_Line(line)

    def Append_Line(self, line: str) -> None:
        """
        Description:
            The SEED path: render one already-formatted line read back from the file. It is the
            only place a line is parsed — with the logger's own Parse_Line, never a second
            formatter — because the file holds text the application does not control. The live
            path uses Append_Record instead and never parses.

        Args:
            (1) line [string]: The formatted line, without its trailing newline.
        """

        self.Append_Record(Parse_Line(line))

    def Append_Record(self, record: tp.Any) -> None:
        """
        Description:
            The LIVE path: render one line from its already-separated fields (a Log_Line_Str),
            with no parsing. Both paths funnel here; the seed path just parses first.

        Args:
            (1) record [Log_Line_Str(object)]: The line's fields.
        """

        row = self.__Build_Row(record)
        self.__rows.append((record.Level, row))
        self.__rows_box.addWidget(row)

        visible = self.__Filter_Matches(record.Level, self.__filter.Selection() or 'all')
        row.setVisible(visible)
        if visible:
            self.__shown += 1
            if not self.__follow:
                self.__new_count += 1
                self.__Show_New_Indicator()
        while len(self.__rows) > CONST_MAX_ROWS:
            self.__Drop_Oldest_Row()
        self.__Set_Count(self.__shown)

    def __Drop_Oldest_Row(self) -> None:
        """
        Description:
            Remove the oldest row (the file keeps the line). If the operator is scrolled up, the
            scroll position moves up by the row's height, so the lines they are reading stay put.
        """

        level, row = self.__rows.pop(0)
        self.__trimmed = True
        height = row.height() if not row.isHidden() else 0
        if self.__Filter_Matches(level, self.__filter.Selection() or 'all'):
            self.__shown -= 1
        self.__rows_box.removeWidget(row)
        row.setParent(None)
        row.deleteLater()
        if not self.__follow and height:
            bar = self.__scroll.verticalScrollBar()
            bar.setValue(max(0, bar.value() - height))

    def Is_Following(self) -> bool:
        """
        Description:
            Whether the view is following the tail (stuck to the bottom).

        Returns:
            (1) parameter [bool]: True while following.
        """

        return self.__follow

    def Shown_Count(self) -> int:
        """
        Description:
            The number of lines currently shown under the active filter.

        Returns:
            (1) parameter [int]: The shown-line count.
        """

        return self.__shown

    def New_Line_Count(self) -> int:
        """
        Description:
            The number of lines that have arrived while the operator was scrolled up and has
            not yet returned to the bottom.

        Returns:
            (1) parameter [int]: The pending new-line count.
        """

        return self.__new_count

    # ------------------------------------------------------------------- rendering

    def __Build_Row(self, record: tp.Any) -> QWidget:
        """
        Description:
            One log row. A parsed line lays three columns: the timestamp (muted, monospace,
            fixed width), the level (coloured AND weighted by severity, monospace, fixed
            width), and the message (coloured by severity, wrapping) — so the message starts at
            a consistent x, the eye lands on severity first, and severity survives a red-green
            deficiency through the level word and its weight, not colour alone. An UNPARSED
            line (a wrapped continuation, or foreign text in the file) is rendered raw across
            the full width in the muted tone — never mis-split, never dropped.

        Args:
            (1) record [Log_Line_Str(object)]: The line's fields.

        Returns:
            (1) parameter [QWidget(object)]: The row widget.
        """

        if not record.Parsed:
            return self.__Build_Raw_Row(record.Message)

        color = Style.Log_Level_Color(record.Level)

        row = QWidget()
        line = QHBoxLayout(row)
        line.setContentsMargins(0, CONST_ROW_PAD, 0, CONST_ROW_PAD)
        line.setSpacing(CONST_COL_GAP)

        stamp = QLabel(('%s %s' % (record.Date, record.Time)).strip())
        stamp.setFont(Font(Style.CONST_TYPE_LOG, mono=True))
        stamp.setStyleSheet('color: %s;' % Style.CONST_INK_MUTE)
        stamp.setFixedWidth(self.__ts_width)
        line.addWidget(stamp, 0, Qt.AlignTop)

        level = QLabel(record.Level)
        level.setFont(Font(Style.CONST_TYPE_LOG, Style.Log_Level_Weight(record.Level), mono=True))
        level.setStyleSheet('color: %s;' % color)
        level.setFixedWidth(self.__level_width)
        line.addWidget(level, 0, Qt.AlignTop)

        message = QLabel(record.Message)
        message.setFont(Font(Style.CONST_TYPE_LOG))
        message.setWordWrap(True)
        message.setTextInteractionFlags(Qt.TextSelectableByMouse)
        message.setStyleSheet('color: %s;' % color)
        line.addWidget(message, 1)
        return row

    def __Build_Raw_Row(self, text: str) -> QWidget:
        """
        Description:
            A row for an UNPARSED line: the raw text across the full width in the muted tone,
            monospace and wrapping. It carries no severity (there is none to trust), so it is
            never coloured as a level — the muted tone marks it as a continuation or foreign
            line rather than mis-attributing a severity to it.

        Args:
            (1) text [string]: The raw line text, verbatim.

        Returns:
            (1) parameter [QWidget(object)]: The row widget.
        """

        row = QWidget()
        line = QHBoxLayout(row)
        line.setContentsMargins(0, CONST_ROW_PAD, 0, CONST_ROW_PAD)
        line.setSpacing(0)

        raw = QLabel(text)
        raw.setFont(Font(Style.CONST_TYPE_LOG, mono=True))
        raw.setWordWrap(True)
        raw.setTextInteractionFlags(Qt.TextSelectableByMouse)
        raw.setStyleSheet('color: %s;' % Style.CONST_INK_MUTE)
        line.addWidget(raw, 1)
        return row

    def __Set_Count(self, count: int) -> None:
        """
        Description:
            Show the count of lines currently displayed, so filtering to a level with no lines
            reads as 'none occurred' rather than a broken filter.

        Args:
            (1) count [int]: The number of shown lines.
        """

        text = '%d %s' % (count, 'line' if count == 1 else 'lines')
        self.__count.setText(text + (' · the last %d kept here, all in the log file' % CONST_MAX_ROWS
                                     if self.__trimmed else ''))

    # --------------------------------------------------------------------- filtering

    def __Filter_Matches(self, level: str, key: str) -> bool:
        """
        Description:
            Whether a line of the given level is shown under the active filter key. 'all'
            matches every level; any other key matches only its one level.

        Args:
            (1) level [string]: The line's severity level.
            (2) key [string]: The active filter key ('all', 'info', 'warning', 'error').

        Returns:
            (1) parameter [bool]: True when the line is shown.
        """

        return key == 'all' or level == CONST_FILTER_TO_LEVEL.get(key)

    def __Apply_Filter(self) -> None:
        """
        Description:
            Re-apply the active filter to every row — a VIEW operation that hides and shows
            rows and never touches the file — and refresh the shown-count. If the filter change
            leaves the view at the bottom, it keeps following.
        """

        key = self.__filter.Selection() or 'all'
        shown = 0
        for level, row in self.__rows:
            visible = self.__Filter_Matches(level, key)
            row.setVisible(visible)
            if visible:
                shown += 1
        self.__shown = shown
        self.__Set_Count(shown)

    # ------------------------------------------------------------------- tail follow

    def __On_Range_Changed(self, _minimum: int, _maximum: int) -> None:
        """
        Description:
            The scroll range changed (a row was added and laid out). Jump to the new bottom
            only while following, so new lines stay in view without yanking a scrolled-up
            operator back down.

        Args:
            (1) _minimum [int]: The new range minimum (unused).
            (2) _maximum [int]: The new range maximum (unused).
        """

        if self.__follow:
            self.__Scroll_To_Bottom()

    def __On_Value_Changed(self, value: int) -> None:
        """
        Description:
            The scrollbar moved (by the operator or by a jump-to-bottom). Following is simply
            'the value is at the bottom'; returning to the bottom clears the new-lines
            indicator, and scrolling up suspends following.

        Args:
            (1) value [int]: The new scrollbar value.
        """

        bar = self.__scroll.verticalScrollBar()
        self.__follow = value >= bar.maximum() - CONST_TAIL_EPSILON
        if self.__follow:
            self.__Clear_New_Indicator()

    def __Scroll_To_Bottom(self) -> None:
        """
        Description:
            Move the scrollbar to the bottom (and, via the value-changed handler, resume
            following and clear the new-lines indicator).
        """

        bar = self.__scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def __Show_New_Indicator(self) -> None:
        """
        Description:
            Show the 'new lines' indicator with the pending count, so an operator reading
            older lines sees that the log has advanced without being pulled to the bottom.
        """

        self.__new_indicator.setText('↓  %d new' % self.__new_count)
        self.__new_indicator.show()

    def __Clear_New_Indicator(self) -> None:
        """
        Description:
            Clear the pending new-line count and hide the indicator — the operator is at the
            bottom and current again.
        """

        self.__new_count = 0
        self.__new_indicator.hide()

    def __On_Record_Received(self, record: tp.Any) -> None:
        """
        Description:
            GUI-thread slot for a record delivered through the sink signal — render it directly
            from its fields (the live path never parses).

        Args:
            (1) record [Log_Line_Str(object)]: The line's fields.
        """

        self.Append_Record(record)
