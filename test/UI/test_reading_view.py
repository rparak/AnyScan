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
# File Name: ../test/UI/test_reading_view.py
## =========================================================================== ##

# System (Default)
import os
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtWidgets import QApplication, QLabel
# Custom Lib.: AnyScan UI — the window; domain — the camera, the result, the formatter
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Analysis_Str
#   ../Reporting/Core
from Reporting.Core import Screen_Header, Object_Line, Object_Label
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style

"""
Description:
    Headless (offscreen) tests that the Scene-Understanding view renders from the shared
    Reporting formatter (§2): the lead is Screen_Header (the background stated once with
    the count) and each object line carries the shared Object_Line text, so the panel and
    the descriptions file cannot drift. No camera and no weights needed.
"""

# The window's name-mangling prefix, for reaching its private state.
CONST_MANGLE = '_AnyScan_Window_Cls'


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


def _Private(window, name: str):
    """Fetch a name-mangled private attribute or method of the window."""
    return getattr(window, CONST_MANGLE + name)


def _Object(sentence: str) -> Detection_Str:
    """A detection whose composed Sentence is preset."""
    return Detection_Str(Label='part', Bbox=(0, 0, 8, 8), Sentence=sentence, Cue='both')


def _Window_With(reference_background_path, result: Analysis_Str) -> AnyScan_Window_Cls:
    """A window that has scanned a frame and rendered the given result."""
    window = AnyScan_Window_Cls(camera=File_Camera_Cls(reference_background_path))
    _Private(window, '__camera').Connect()
    _Private(window, '__Sync_Controls')()
    _Private(window, '__On_Scan_Button_Clicked')()
    _Private(window, '__On_Analysis_Finished')(result)
    return window


def _Line_Texts(window) -> list:
    """The (label, description) text pair of each object block, in order."""
    layout = _Private(window, '__object_list').box
    pairs = []
    for i in range(layout.count()):
        block = layout.itemAt(i).widget()
        inner = block.layout()
        labels = [inner.itemAt(j).widget() for j in range(inner.count())
                  if isinstance(inner.itemAt(j).widget(), QLabel)]
        pairs.append((labels[0].text(), labels[1].text()))
    return pairs


def test_lead_is_the_shared_screen_header(qt_app, reference_background_path) -> None:
    """
    Description:
        The reading lead is Screen_Header — the SAME first line the descriptions file
        carries — so the panel states the background once with the count, not a separate
        summary sentence.
    """

    objects = [_Object('A silver ring.'), _Object('A blue bracket.')]
    background = 'A green background that is very bright.'
    window = _Window_With(reference_background_path,
                          Analysis_Str(Objects=objects, Background=background,
                                       Verdict='2 found', Verdict_Level='ok', Task='caption'))

    lead = _Private(window, '__reading_lead')
    assert lead.text() == Screen_Header(objects, background)
    assert lead.text().startswith(background)
    assert 'There are 2 objects on it, described below.' in lead.text()


def test_object_blocks_carry_the_shared_label_and_description(qt_app, reference_background_path) -> None:
    """
    Description:
        Each object is a two-level block whose label is the shared Object_Label and whose
        second line is the object's own sentence — the same values Object_Line joins for
        the file — so the panel cannot number or word an object differently from the file.
    """

    objects = [_Object('A silver ring.'), _Object('A blue bracket.'), _Object('A hex nut.')]
    window = _Window_With(reference_background_path,
                          Analysis_Str(Objects=objects, Background='A plain surface.',
                                       Verdict='3 found', Verdict_Level='ok', Task='caption'))

    pairs = _Line_Texts(window)
    assert len(pairs) == len(objects)
    for i, det in enumerate(objects):
        label, description = pairs[i]
        assert label == Object_Label(i)                 # 'Obj. N', the shared label
        assert description == det.Sentence
        # The file's one-line form is the two joined, so the panel and file cannot drift.
        assert Object_Line(i, det) == '%s - %s' % (label, description)


def test_object_blocks_are_single_colour_two_level(qt_app, reference_background_path) -> None:
    """
    Description:
        Each object block is a SINGLE colour (Style.CONST_INK = '#2b2455') on two levels —
        the label larger and bold, the description smaller and regular — the hierarchy is
        size and weight, not colour, and there is no per-object colour on the text.
    """

    objects = [_Object('A silver ring.'), _Object('A blue bracket.')]
    window = _Window_With(reference_background_path,
                          Analysis_Str(Objects=objects, Background='A plain surface.',
                                       Verdict='2 found', Verdict_Level='ok', Task='caption'))

    layout = _Private(window, '__object_list').box
    for i in range(layout.count()):
        inner = layout.itemAt(i).widget().layout()
        label = inner.itemAt(0).widget()
        description = inner.itemAt(1).widget()
        # Both lines are the one panel colour, and neither carries a per-object colour.
        assert Style.CONST_INK in label.styleSheet() and Style.CONST_INK in description.styleSheet()
        assert 'border-left' not in label.styleSheet()
        # The label is larger and bold than the description (size and weight, from the theme).
        assert label.font().pointSizeF() > description.font().pointSizeF()
        assert label.font().weight() > description.font().weight()


def test_zero_objects_reads_sensibly(qt_app, reference_background_path) -> None:
    """
    Description:
        The zero case reads 'No objects were detected on it.' in the lead — never
        '0 objects' — and the object list is empty.
    """

    window = _Window_With(reference_background_path,
                          Analysis_Str(Objects=[], Background='A plain surface.',
                                       Verdict='Empty', Verdict_Level='idle', Task='caption'))

    lead = _Private(window, '__reading_lead')
    assert lead.text().endswith('No objects were detected on it.')
    assert '0 object' not in lead.text()
    assert _Line_Texts(window) == []
