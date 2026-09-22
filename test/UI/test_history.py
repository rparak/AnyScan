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
import time
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QKeyEvent
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


def _Write_Full(writer, session_id, set_id, classification=False, run_id=''):
    """Write a full (successful) set through the real writer, recording the flags and run id."""
    raw = np.full((40, 60, 3), 30, np.uint8)
    annotated = np.full((40, 60, 3), 60, np.uint8)
    mask = np.zeros((40, 60, 3), np.uint8)
    objects = _Objects()
    metadata = Build_Set_Metadata(session_id, set_id, '2026-09-20T10:00:00', objects, (60, 40),
                                  'caption', 1180, 91, '', classification, run_id, scale=None)
    writer.Write(session_id, set_id, raw, annotated, mask, 'text', ['0 0.5 0.5 0.1 0.1'],
                 ['0 0.4 0.4 0.6 0.6'], metadata, 'stamp', cv2, np, distorted_bgr=None, undistortion=None)


def _Set_Filter(view, key: str) -> None:
    """Select a filter key and rebuild, exactly as a user click on the segment would."""
    _Private(view, '__filter').Set_Selection(key)
    _Private(view, '__Rebuild_List')()


def _Settle(app, milliseconds: int = 300) -> None:
    """Pump the event loop over real time, so a running slide animation completes."""
    deadline = time.time() + milliseconds / 1000.0
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)


def test_filter_including_the_always_empty_nok_case(qt_app, tmp_path) -> None:
    """
    Description:
        For sets written WITH classification the filter is shown and narrows the grid by verdict.
        No classifier assigns NOK, so every set is OK: 'All' and 'OK' show the sets, and 'NOK'
        shows none — with an explicit message that blames the missing classifier (not the config),
        not a blank panel that reads as broken.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    _Write_Full(writer, 'sessionA', 'set1', classification=True)
    _Write_Full(writer, 'sessionA', 'set2', classification=True)

    view = History_View_Cls(str(tmp_path), classification_enabled=True)
    view.Refresh()
    assert _Private(view, '__filter').isVisibleTo(view)   # a classified run -> filter present
    assert len(_Private(view, '__cards')) == 2            # All

    _Set_Filter(view, 'ok')
    assert len(_Private(view, '__cards')) == 2            # every set is OK

    _Set_Filter(view, 'nok')
    assert len(_Private(view, '__cards')) == 0            # the always-empty case
    body = _Private(view, '__list_box')
    message = body.itemAt(0).widget()
    assert isinstance(message, QLabel)
    assert 'no classifier is running yet' in message.text()

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
    assert _Private(view, '__identity_id').text() == 'set1'
    assert _Private(view, '__meta_session').text() == 'sessionA'
    assert _Private(view, '__meta_objects').text() == '2'
    assert _Private(view, '__meta_task').text() == 'caption'
    assert _Private(view, '__meta_latency').text() == '1180 ms'
    assert _Private(view, '__meta_confidence').text() == '91%'


def test_detect_only_sets_have_no_filter_and_a_neutral_outline(qt_app, tmp_path) -> None:
    """
    Description:
        A history of only detect-only sets (written with classification off) shows NO OK/NOK
        filter at all — its absence, not a disabled control, is the signal — and each set's
        selection outline is the neutral detection colour, not a verdict colour.
    """

    from Parameters.Theme import Detection_Color, Verdict_Color

    writer = Capture_Writer_Cls(str(tmp_path))
    _Write_Full(writer, 'sessionA', 'set1', classification=False)

    view = History_View_Cls(str(tmp_path))
    view.Refresh()
    assert not _Private(view, '__filter').isVisibleTo(view)   # the filter is removed
    cap = _Private(view, '__detail_cap')
    assert _Private(view, '__Set_Color')(cap) == Detection_Color()[0]
    assert _Private(view, '__Set_Color')(cap) != Verdict_Color('OK')[0]


def test_classified_sets_get_the_filter_and_a_verdict_outline(qt_app, tmp_path) -> None:
    """
    Description:
        A classified run shows the filter, and its set takes a verdict-coloured outline (read from
        the set's own recorded flag, so the outline is the record, not the current config).
    """

    from Parameters.Theme import Verdict_Color

    writer = Capture_Writer_Cls(str(tmp_path))
    _Write_Full(writer, 'sessionA', 'set1', classification=True)

    view = History_View_Cls(str(tmp_path), classification_enabled=True)
    view.Refresh()
    assert _Private(view, '__filter').isVisibleTo(view)
    cap = _Private(view, '__detail_cap')
    assert _Private(view, '__Set_Color')(cap) == Verdict_Color('OK')[0]


def test_history_lists_only_the_current_run(qt_app, tmp_path) -> None:
    """
    Description:
        History lists ONLY the sets of the current application run, matched by the run id written
        into each set's metadata — not every set on disk. A set from an earlier run stays on disk
        (retention manages it) but is not shown, and the match does not depend on timestamps.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    _Write_Full(writer, 'sessionA', 'old', run_id='run-earlier')
    _Write_Full(writer, 'sessionA', 'new1', run_id='run-current')
    _Write_Full(writer, 'sessionB', 'new2', run_id='run-current')   # a second camera connection

    view = History_View_Cls(str(tmp_path), run_id='run-current')
    view.Refresh()
    shown = sorted(c.Cap().Set_Id for c in _Private(view, '__cards'))
    assert shown == ['new1', 'new2']                     # both connections of THIS run, not 'old'


def test_empty_run_shows_the_run_scoped_message(qt_app, tmp_path) -> None:
    """
    Description:
        Before the first analysis of a run — no sets match the run id — the grid shows a short
        muted message inviting an analysis, not a blank panel (nor another run's sets).
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    _Write_Full(writer, 'sessionA', 'old', run_id='run-earlier')      # a different run's set

    view = History_View_Cls(str(tmp_path), run_id='run-current')
    view.Refresh()
    assert len(_Private(view, '__cards')) == 0
    message = _Private(view, '__list_box').itemAt(0).widget()
    assert isinstance(message, QLabel)
    assert message.text() == 'No captures in this run yet. Analyse an image to begin.'


def test_the_two_empty_nok_states_are_distinguishable(qt_app, tmp_path) -> None:
    """
    Description:
        The two reasons a NOK list can be empty must read differently. Detect-only sets: the filter
        is not there at all (you cannot reach an empty NOK — its absence is the answer). Classified
        sets with no NOK: the filter IS there and says why it is empty (no classifier yet). The two
        cannot be confused.
    """

    off_root = tmp_path / 'off'
    _Write_Full(Capture_Writer_Cls(str(off_root)), 's', 'a', classification=False)
    off = History_View_Cls(str(off_root), classification_enabled=False)
    off.Refresh()
    assert not _Private(off, '__filter').isVisibleTo(off)     # no filter — the absence is the signal

    on_root = tmp_path / 'on'
    _Write_Full(Capture_Writer_Cls(str(on_root)), 's', 'a', classification=True)
    on = History_View_Cls(str(on_root), classification_enabled=True)
    on.Refresh()
    assert _Private(on, '__filter').isVisibleTo(on)          # filter present
    _Set_Filter(on, 'nok')
    message = _Private(on, '__list_box').itemAt(0).widget().text()
    assert 'no classifier is running yet' in message         # says WHY, not that the config is off


def test_the_browser_panel_is_labelled_captures(qt_app, tmp_path) -> None:
    """
    Description:
        The left browser is 'Captures', not 'History' — so the same word does not name both the
        main switch and this panel.
    """

    view = History_View_Cls(str(tmp_path))
    titles = [w.text() for w in view.findChildren(QLabel) if w.text() in ('Captures', 'History')]
    assert 'Captures' in titles and 'History' not in titles


def test_two_panes_are_equal_size_and_scale_together(qt_app, tmp_path) -> None:
    """
    Description:
        A full set shows the Annotated and Mask panes side by side, both visible, captioned, and
        of equal size — comparing them is impossible if one is larger. (They hold the same-
        resolution images, so equal size means an equal scale.)
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    _Write_Full(writer, 'sessionA', 'set1')

    view = History_View_Cls(str(tmp_path))
    view.resize(1400, 780)
    view.show()
    view.Refresh()
    for _ in range(4):
        qt_app.processEvents()

    pane_a = _Private(view, '__pane_a')
    pane_b = _Private(view, '__pane_b')
    assert pane_a.isVisible() and pane_b.isVisible()
    assert _Private(view, '__caption_a').text() == 'Annotated'
    assert _Private(view, '__caption_b').text() == 'Mask'
    # Equal width and height -> they scale together.
    assert abs(pane_a.width() - pane_b.width()) <= 1
    assert _Private(view, '__image_a').height() == _Private(view, '__image_b').height()


def test_clicking_an_object_highlights_the_annotated_pane_with_info_open(qt_app, tmp_path) -> None:
    """
    Description:
        With the Info panel open, clicking an object row highlights that object's box in the
        Annotated pane (not the mask), and both stay visible — the Info panel narrows the images
        rather than covering them.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    _Write_Full(writer, 'sessionA', 'set1')

    view = History_View_Cls(str(tmp_path))
    view.Refresh()
    _Private(view, '__Open_Info')()
    cap = _Private(view, '__detail_cap')
    _Private(view, '__On_Object_Selected')(1)

    assert view.Is_Info_Open()
    assert getattr(_Private(view, '__image_a'), '_History_Image_Cls__highlight') == \
        tuple(cap.Objects[1].Bbox)
    assert getattr(_Private(view, '__image_b'), '_History_Image_Cls__highlight') is None


def test_missing_score_note_explains_unscored_objects(qt_app, tmp_path) -> None:
    """
    Description:
        An object with no FastSAM score shows 'Confidence —'; a single foot note (not per row)
        explains that such objects were found by background subtraction. The note appears only
        when at least one object is unscored.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    # One scored + one unscored object.
    scored = Detection_Str(Label='a', Bbox=(1, 1, 5, 5), Segmenter_Score=0.9, Sentence='A.',
                           Verdict='OK', Cue='both')
    unscored = Detection_Str(Label='b', Bbox=(7, 7, 5, 5), Segmenter_Score=None, Sentence='B.',
                             Verdict='OK', Cue='background')
    raw = np.full((40, 60, 3), 30, np.uint8)
    md = Build_Set_Metadata('sessionA', 'set1', '2026-09-20T10:00:00', [scored, unscored],
                            (60, 40), 'caption', 1000, 90, scale=None)
    writer.Write('sessionA', 'set1', raw, raw, np.zeros((40, 60, 3), np.uint8), 'text',
                 ['0 0.5 0.5 0.1 0.1'], ['0 0.4 0.4 0.6 0.6'], md, 'stamp', cv2, np, distorted_bgr=None, undistortion=None)

    view = History_View_Cls(str(tmp_path))
    view.Refresh()
    note = _Private(view, '__score_note')
    assert not note.isHidden()
    assert 'background subtraction' in note.text()


def test_evicting_the_selected_set_clears_the_detail_with_a_note(qt_app, tmp_path) -> None:
    """
    Description:
        Retention can delete the set the operator is viewing. When a Refresh finds the selected
        set gone (evicted), the view clears the detail with a note saying it fell outside the
        retention window and drops the selection — never pointing at deleted files, never
        raising.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    _Write_Full(writer, 'sessionA', 'keep')
    _Write_Full(writer, 'sessionA', 'gone')

    view = History_View_Cls(str(tmp_path))
    view.Refresh()
    getattr(view, '_History_View_Cls__Select')(
        next(c for c in _Private(view, '__sets') if c.Set_Id == 'gone'))
    assert view.Selected_Set_Id() == 'gone'

    # Simulate eviction: remove the selected set's files, then refresh.
    for name in os.listdir(str(tmp_path / 'sessionA')):
        if name.startswith('gone'):
            os.remove(str(tmp_path / 'sessionA' / name))
    view.Refresh()

    assert view.Selected_Set_Id() is None                 # selection dropped
    assert not _Private(view, '__banner').isHidden()
    assert 'retention window' in _Private(view, '__banner').text()


def test_a_new_set_appears_on_refresh_keeping_the_selection(qt_app, tmp_path) -> None:
    """
    Description:
        A set analysed while the operator sits in History appears on the next Refresh (the window
        refreshes History on every write), and the current selection is preserved rather than
        being reset to the newest.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    _Write_Full(writer, 'sessionA', 'first')

    view = History_View_Cls(str(tmp_path))
    view.Refresh()
    assert len(_Private(view, '__cards')) == 1
    assert view.Selected_Set_Id() == 'first'

    _Write_Full(writer, 'sessionA', 'second')             # a new analysis lands
    view.Refresh()
    assert len(_Private(view, '__cards')) == 2             # it appears
    assert view.Selected_Set_Id() == 'first'              # selection kept


def test_partial_set_renders_raw_full_width_with_the_banner(qt_app, tmp_path) -> None:
    """
    Description:
        A partial set (a failed analysis, raw frame only) renders its raw frame across the full
        width: the second (mask) pane is hidden so there is never an empty pane, the visible pane
        is captioned 'Raw', the failure banner names the failure and the set id, and the object
        list is empty. The set is shown, not hidden.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    raw = np.full((40, 60, 3), 30, np.uint8)
    writer.Write_Partial('sessionA', 'failset', raw,
                         'Analysis FAILED — partial capture (raw frame only). Failure: boom',
                         'stamp', cv2, np, distorted_bgr=None, undistortion=None)

    view = History_View_Cls(str(tmp_path))
    view.show()
    view.Refresh()

    partial = next(cap for cap in _Private(view, '__sets') if cap.Set_Id == 'failset')
    _Private(view, '__Select')(partial)
    banner = _Private(view, '__banner')
    assert not banner.isHidden()
    assert 'failset' in banner.text() and 'failed' in banner.text().lower()
    assert _Private(view, '__object_list').box.count() == 0
    # Raw full-width: the mask pane is hidden, the visible pane is captioned 'Raw'.
    assert _Private(view, '__pane_a').isVisible()
    assert _Private(view, '__pane_b').isHidden()
    assert _Private(view, '__caption_a').text() == 'Raw'
    # No Scene-Understanding to show: the Info control is disabled.
    assert not _Private(view, '__info_button').isEnabled()


def test_info_panel_opens_closes_and_narrows_without_covering(qt_app, tmp_path) -> None:
    """
    Description:
        The Info panel opens (Info button), narrows the images rather than covering them (it is a
        sibling in the same row, both visible), and closes with Info again or Escape.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    _Write_Full(writer, 'sessionA', 'set1')

    view = History_View_Cls(str(tmp_path))
    view.resize(1400, 780)
    view.show()
    view.Refresh()
    for _ in range(4):
        qt_app.processEvents()

    images = _Private(view, '__images_row')
    info = _Private(view, '__info_panel')
    wide = images.width()

    _Private(view, '__Toggle_Info')()                     # open
    _Settle(qt_app)
    assert view.Is_Info_Open()
    assert info.isVisible() and images.isVisible()        # side by side, not covering
    assert images.width() < wide                          # the images narrowed
    assert info.width() > 0

    _Private(view, '__Toggle_Info')()                     # close via Info again
    _Settle(qt_app)
    assert not view.Is_Info_Open()
    assert images.width() == wide                         # width given back to the images

    # Escape closes it too.
    _Private(view, '__Open_Info')()
    _Settle(qt_app)
    assert view.Is_Info_Open()
    view.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))
    _Settle(qt_app)
    assert not view.Is_Info_Open()


def test_info_panel_type_hierarchy_heading_is_largest(qt_app, tmp_path) -> None:
    """
    Description:
        The Info panel's type hierarchy is strictly largest → smallest: heading > object label >
        body (the background paragraph AND the descriptions, one size) > the confidence suffix and
        the unscored-object note. The heading is larger than everything beneath it, so an inverted
        hierarchy (the old bug, where the background paragraph outran the heading) fails here.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    _Write_Full(writer, 'sessionA', 'set1')

    view = History_View_Cls(str(tmp_path))
    view.Refresh()

    heading = _Private(view, '__info_title').font().pointSizeF()
    lead = _Private(view, '__info_lead').font().pointSizeF()
    note = _Private(view, '__score_note').font().pointSizeF()

    block = _Private(view, '__object_list').box.itemAt(0).widget()
    label_line = block.layout().itemAt(0).widget().layout()
    label_size = label_line.itemAt(0).widget().font().pointSizeF()
    confidence_size = label_line.itemAt(1).widget().font().pointSizeF()
    description_size = block.layout().itemAt(1).widget().font().pointSizeF()

    # Strict descending hierarchy: heading > label > body > meta.
    assert heading > label_size > description_size > confidence_size
    # Everything sits below the heading.
    assert heading > lead and heading > note
    # Background paragraph and descriptions are one consistent body size.
    assert lead == description_size
    # Confidence suffix and the unscored note are the same smallest tier.
    assert note == confidence_size


def test_info_panel_text_is_smaller_than_the_live_panel(qt_app, tmp_path) -> None:
    """
    Description:
        The Info panel (read up close) uses smaller tokens than the Live Scene-Understanding block
        (glanced at across a workbench) — separate tokens, so one cannot move the other.
    """

    import UI.Utilities.Style as Style
    assert Style.CONST_TYPE_INFO_BODY < Style.CONST_TYPE_OBJECT_BODY
    assert Style.CONST_TYPE_INFO_LABEL < Style.CONST_TYPE_OBJECT_LABEL
    assert Style.CONST_TYPE_INFO_HEADING < Style.CONST_TYPE_SCENE_BACKGROUND


def test_info_text_matches_the_shared_formatter(qt_app, tmp_path) -> None:
    """
    Description:
        The Info panel's text is the shared formatter's output, from '_objects.json' — the lead is
        Screen_Header (the background stated once with the count) and the rows are the shared
        object labels, the same as Scene Understanding and the '.txt'. Nothing parses the prose.
    """

    from Reporting.Core import Screen_Header, Object_Label, Object_Confidence, CONST_LABEL_SEPARATOR

    writer = Capture_Writer_Cls(str(tmp_path))
    objects = _Objects()
    md = Build_Set_Metadata('sessionA', 'set1', '2026-09-20T10:00:00', objects, (60, 40),
                            'caption', 1180, 91, 'A green background.', scale=None)
    raw = np.full((40, 60, 3), 30, np.uint8)
    writer.Write('sessionA', 'set1', raw, raw, np.zeros((40, 60, 3), np.uint8), 'text',
                 ['0 0.5 0.5 0.1 0.1'], ['0 0.4 0.4 0.6 0.6'], md, 'stamp', cv2, np, distorted_bgr=None, undistortion=None)

    view = History_View_Cls(str(tmp_path))
    view.Refresh()
    cap = _Private(view, '__detail_cap')
    detections = _Private(view, '__Detections')(cap)

    # The lead is exactly Screen_Header over the reconstructed objects and the stored background.
    assert _Private(view, '__info_lead').text() == Screen_Header(detections, cap.Background)
    assert _Private(view, '__info_lead').text().startswith('A green background.')

    # The rows are the shared labels (name + confidence), in order.
    layout = _Private(view, '__object_list').box
    for i, det in enumerate(objects):
        block = layout.itemAt(i).widget()
        name = block.layout().itemAt(0).widget().layout().itemAt(0).widget()
        assert name.text() == Object_Label(i)


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
