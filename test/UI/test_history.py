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
# File Name: ../test/UI/test_history.py
## =========================================================================== ##

# System (Default)
import os
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtWidgets import QApplication, QLabel
# Custom Lib.: AnyScan UI — the History view; the writer/metadata; the detection structure
#   ../UI/Views/History
from UI.Views.History import History_View_Cls
#   ../UI/Capture
from UI.Capture import Capture_Writer_Cls, Build_Set_Metadata
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str

"""
Description:
    Headless (offscreen) tests for the History view: the OK/NOK filter including the always-empty
    NOK case, a partial set rendering without error, and a malformed metadata file not crashing
    the view. Fixture sets are written through the real writer into a tmp captures root.
"""
# The view's name-mangling prefix, for reaching its private state.
CONST_MANGLE = '_History_View_Cls'


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


def _Private(view, name: str):
    """Fetch a name-mangled private attribute or method of the view."""
    return getattr(view, CONST_MANGLE + name)


def _Objects():
    """A two-object detection list (both OK — nothing assigns NOK today)."""
    return [Detection_Str(Label='ring', Bbox=(5, 5, 20, 15), Segmenter_Score=0.91,
                          Sentence='A silver ring.', Verdict='OK', Cue='both'),
            Detection_Str(Label='nut', Bbox=(30, 25, 10, 10), Segmenter_Score=0.9,
                          Sentence='A hex nut.', Verdict='OK', Cue='both')]


def _Write_Full(writer, session_id, set_id):
    """Write a full (successful) set through the real writer."""
    raw = np.full((40, 60, 3), 30, np.uint8)
    annotated = np.full((40, 60, 3), 60, np.uint8)
    mask = np.zeros((40, 60, 3), np.uint8)
    objects = _Objects()
    metadata = Build_Set_Metadata(session_id, set_id, '2026-09-20T10:00:00', objects, (60, 40),
                                  'caption', 1180, 91)
    writer.Write(session_id, set_id, raw, annotated, mask, 'text', ['0 0.5 0.5 0.1 0.1'],
                 ['0 0.4 0.4 0.6 0.6'], metadata, 'stamp', cv2, np)


def _Set_Filter(view, key: str) -> None:
    """Select a filter key and rebuild, exactly as a user click on the segment would."""
    _Private(view, '__filter').Set_Selection(key)
    _Private(view, '__Rebuild_List')()


def test_filter_including_the_always_empty_nok_case(qt_app, tmp_path) -> None:
    """
    Description:
        The filter narrows the grid by set verdict. Nothing assigns NOK today, so every set is
        OK: 'All' and 'OK' show the sets, and 'NOK' shows none — with an explicit message naming
        why it is empty (classification not enabled), not a blank panel that reads as broken.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    _Write_Full(writer, 'sessionA', 'set1')
    _Write_Full(writer, 'sessionA', 'set2')

    view = History_View_Cls(str(tmp_path))
    view.Refresh()
    assert len(_Private(view, '__cards')) == 2            # All

    _Set_Filter(view, 'ok')
    assert len(_Private(view, '__cards')) == 2            # every set is OK

    _Set_Filter(view, 'nok')
    assert len(_Private(view, '__cards')) == 0            # the always-empty case
    body = _Private(view, '__list_box')
    message = body.itemAt(0).widget()
    assert isinstance(message, QLabel)
    assert 'Classification is not yet enabled' in message.text()

    _Set_Filter(view, 'all')
    assert len(_Private(view, '__cards')) == 2            # restored


def test_selecting_a_full_set_renders_the_object_list(qt_app, tmp_path) -> None:
    """
    Description:
        Selecting a successful set renders its objects through the shared formatter (the same
        object list as Scene Understanding) and its set-level figures, with no failure banner.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    _Write_Full(writer, 'sessionA', 'set1')

    view = History_View_Cls(str(tmp_path))
    view.Refresh()
    # Refresh selects the first (only) set.
    assert _Private(view, '__object_list').box.count() == 2
    assert _Private(view, '__banner').isHidden()
    assert _Private(view, '__meta_task').text() == 'caption'
    assert _Private(view, '__meta_latency').text() == '1180 ms'
    assert _Private(view, '__meta_confidence').text() == '91%'


def test_partial_set_renders_without_error(qt_app, tmp_path) -> None:
    """
    Description:
        A partial set (a failed analysis, raw frame only) renders without error: the failure
        banner names the failure and the set id (so it can be found in the log), the object list
        is empty, and the set is shown, not hidden.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    raw = np.full((40, 60, 3), 30, np.uint8)
    writer.Write_Partial('sessionA', 'failset', raw,
                         'Analysis FAILED — partial capture (raw frame only). Failure: boom',
                         'stamp', cv2, np)

    view = History_View_Cls(str(tmp_path))
    view.Refresh()

    partial = next(cap for cap in _Private(view, '__sets') if cap.Set_Id == 'failset')
    _Private(view, '__Select')(partial)
    banner = _Private(view, '__banner')
    assert not banner.isHidden()
    assert 'failset' in banner.text() and 'failed' in banner.text().lower()
    assert _Private(view, '__object_list').box.count() == 0


def test_malformed_metadata_does_not_crash_the_view(qt_app, tmp_path) -> None:
    """
    Description:
        A set whose metadata is corrupt does not crash the view: it is discovered, reads as
        partial, and selecting it shows the failure banner rather than raising.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    _Write_Full(writer, 'sessionA', 'set1')
    (tmp_path / 'sessionA' / 'set1_objects.json').write_text('{ not valid json ]')

    view = History_View_Cls(str(tmp_path))
    view.Refresh()                                        # must not raise
    cap = next(cap for cap in _Private(view, '__sets') if cap.Set_Id == 'set1')
    assert cap.Partial
    _Private(view, '__Select')(cap)                       # must not raise
    assert not _Private(view, '__banner').isHidden()


def test_missing_captures_root_shows_empty_grid(qt_app, tmp_path) -> None:
    """
    Description:
        With no captures root (no logger) the view refreshes to an empty grid and an empty-state
        message, never a crash.
    """

    view = History_View_Cls(None)
    view.Refresh()
    assert _Private(view, '__cards') == []
    body = _Private(view, '__list_box')
    assert isinstance(body.itemAt(0).widget(), QLabel)   # the empty-state message
