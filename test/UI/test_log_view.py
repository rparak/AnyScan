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
# File Name: ../test/UI/test_log_view.py
## =========================================================================== ##

# System (Default)
import os
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtWidgets import QApplication
# Custom Lib.: AnyScan UI — the log view; the palette; the logger's level constants
#   ../UI/Views/Log
from UI.Views.Log import Log_View_Cls
#   ../Parameters/Theme
from Parameters.Theme import (Log_Level_Color, CONST_LOG_INFO, CONST_LOG_WARNING,
                              CONST_LOG_ERROR)
#   ../Logger/Core
from Logger.Core import CONST_LEVEL_INFO, CONST_LEVEL_WARNING, CONST_LEVEL_ERROR

"""
Description:
    Headless (offscreen) tests for the Log view. They assert that the view renders the four
    fields in columns from an already-formatted line (never re-formatting), that the filter
    selects by level and reports the shown count including the empty case, the level-to-colour
    mapping, and that tail-following is suspended when the operator scrolls up. No logger, no
    camera and no weights needed — the view is fed lines directly.
"""
# The name-mangling prefix for the view's private state.
CONST_MANGLE = '_Log_View_Cls'


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


def _Private(view, name: str):
    """Fetch a name-mangled private attribute or method of the view."""
    return getattr(view, CONST_MANGLE + name)


def _Line(time: str, level: str, message: str) -> str:
    """One formatted log line, exactly as the logger writes it (level padded to width 7)."""
    return '2026-09-12 %s [%-7s] %s' % (time, level, message)


def _Row_Labels(view):
    """The (timestamp, level, message) QLabels of every rendered row, in order."""
    labels = []
    for _level, row in _Private(view, '__rows'):
        cells = [row.layout().itemAt(i).widget() for i in range(row.layout().count())]
        labels.append(tuple(cells))
    return labels


def _Set_Filter(view, key: str) -> None:
    """Select a filter key and apply it, exactly as a user click on the segment would."""
    _Private(view, '__filter').Set_Selection(key)
    _Private(view, '__Apply_Filter')()


def test_renders_the_four_fields_in_columns(qt_app) -> None:
    """
    Description:
        A row renders the logger's four fields — date, time, level, message — split by the
        logger's own parser, not re-formatted here. The timestamp is muted; the level and the
        message carry the level's colour; the timestamp and level columns are fixed-width so
        the message starts at the same x on every row.
    """

    view = Log_View_Cls()
    view.Append_Line(_Line('08:00:01', CONST_LEVEL_INFO, 'Application started.'))
    view.Append_Line(_Line('08:00:02', CONST_LEVEL_ERROR, 'Backend timed out.'))

    (ts0, lvl0, msg0), (ts1, lvl1, msg1) = _Row_Labels(view)

    assert ts0.text() == '2026-09-12 08:00:01'
    assert lvl0.text() == CONST_LEVEL_INFO
    assert msg0.text() == 'Application started.'

    # Timestamp muted; level and message coloured by the level's token.
    assert CONST_LOG_INFO in lvl0.styleSheet() and CONST_LOG_INFO in msg0.styleSheet()
    assert CONST_LOG_ERROR in lvl1.styleSheet() and CONST_LOG_ERROR in msg1.styleSheet()

    # Fixed, equal column widths -> the message starts at a consistent x.
    assert ts0.width() == ts1.width() and lvl0.width() == lvl1.width()


def test_level_to_colour_mapping(qt_app) -> None:
    """
    Description:
        Each level maps to its one theme token, and an unknown level falls back to INFO so a
        line always renders. This is the single mapping the view colours by.
    """

    assert Log_Level_Color(CONST_LEVEL_INFO) == CONST_LOG_INFO
    assert Log_Level_Color(CONST_LEVEL_WARNING) == CONST_LOG_WARNING
    assert Log_Level_Color(CONST_LEVEL_ERROR) == CONST_LOG_ERROR
    assert Log_Level_Color('SOMETHING_ELSE') == CONST_LOG_INFO
    # The three tokens are distinct, and ERROR is deliberately not the NOK verdict magenta.
    assert len({CONST_LOG_INFO, CONST_LOG_WARNING, CONST_LOG_ERROR}) == 3
    assert CONST_LOG_ERROR != '#ff005c'


def test_filter_selects_by_level_and_counts_including_the_empty_case(qt_app) -> None:
    """
    Description:
        The filter is a view operation: it hides and shows rows by level and never removes
        them. The shown-count follows the filter, so filtering to a level with no lines reads
        as '0' (none occurred) rather than a broken filter. Here only INFO and WARNING lines
        exist, so 'Error' shows none and 'All' shows every line again.
    """

    view = Log_View_Cls()
    view.Append_Line(_Line('08:00:01', CONST_LEVEL_INFO, 'One.'))
    view.Append_Line(_Line('08:00:02', CONST_LEVEL_WARNING, 'Two.'))
    view.Append_Line(_Line('08:00:03', CONST_LEVEL_INFO, 'Three.'))

    assert view.Shown_Count() == 3                       # 'All' by default

    _Set_Filter(view, 'info')
    assert view.Shown_Count() == 2

    _Set_Filter(view, 'warning')
    assert view.Shown_Count() == 1

    _Set_Filter(view, 'error')                           # the empty case
    assert view.Shown_Count() == 0

    _Set_Filter(view, 'all')
    assert view.Shown_Count() == 3

    # Filtering never drops the underlying rows — they are only hidden.
    assert len(_Private(view, '__rows')) == 3


def test_new_line_after_filter_respects_the_active_filter(qt_app) -> None:
    """
    Description:
        A line appended while a filter is active is shown only if it matches — the count
        stays truthful as new lines arrive. With the filter on 'error', a new INFO line does
        not raise the count, while a new ERROR line does.
    """

    view = Log_View_Cls()
    view.Append_Line(_Line('08:00:01', CONST_LEVEL_INFO, 'One.'))
    _Set_Filter(view, 'error')
    assert view.Shown_Count() == 0

    view.Append_Line(_Line('08:00:02', CONST_LEVEL_INFO, 'Still hidden.'))
    assert view.Shown_Count() == 0
    view.Append_Line(_Line('08:00:03', CONST_LEVEL_ERROR, 'Now shown.'))
    assert view.Shown_Count() == 1


def test_tail_following_suspended_on_manual_scroll(qt_app) -> None:
    """
    Description:
        The view follows the tail while the operator is at the bottom, but a manual scroll up
        suspends it: new lines then do NOT yank the view back down — the position is held and
        the pending new-line count rises. Returning to the bottom resumes following and clears
        the count.
    """

    view = Log_View_Cls()
    view.resize(700, 200)
    view.show()
    for _ in range(4):
        qt_app.processEvents()

    for i in range(120):
        view.Append_Line(_Line('08:%02d:%02d' % (i // 60, i % 60), CONST_LEVEL_INFO,
                               'Line number %d.' % i))
    for _ in range(4):
        qt_app.processEvents()

    bar = _Private(view, '__scroll').verticalScrollBar()
    assert bar.maximum() > 0                              # content taller than the viewport
    assert view.Is_Following()
    assert bar.value() == bar.maximum()                  # stuck to the bottom

    # Manual scroll up: following is suspended.
    bar.setValue(0)
    for _ in range(2):
        qt_app.processEvents()
    assert not view.Is_Following()

    # A new line does not pull the view down; the pending count rises and the position holds.
    view.Append_Line(_Line('09:00:00', CONST_LEVEL_WARNING, 'Arrived while scrolled up.'))
    for _ in range(2):
        qt_app.processEvents()
    assert not view.Is_Following()
    assert bar.value() == 0                               # not yanked back to the bottom
    assert view.New_Line_Count() == 1

    # Returning to the bottom resumes following and clears the pending count.
    bar.setValue(bar.maximum())
    for _ in range(2):
        qt_app.processEvents()
    assert view.Is_Following()
    assert view.New_Line_Count() == 0
