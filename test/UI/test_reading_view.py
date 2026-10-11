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
# File Name: ../test/UI/test_reading_view.py
## =========================================================================== ##

# System (Default)
import os
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextDocument
from PyQt5.QtWidgets import QApplication, QLabel
# Custom Lib.: AnyScan UI — the window; domain — the camera, the result, the formatter
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Analysis_Str
#   ../Reporting/Core
from Reporting.Core import (Screen_Header, Object_Line, Object_Label, Object_Confidence,
                           Object_Label_Full, CONST_LABEL_SEPARATOR)
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
# Dataclasses (the shipped configuration, unscaled, for the window)
import dataclasses
# Custom Lib.: AnyScan — the configuration layer the window is built from
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    Headless (offscreen) tests that the Scene-Understanding view renders from the shared
    Reporting formatter (§2): the lead is Screen_Header (the background stated once with
    the count, one label) and each object line carries the shared Object_Line text, so the
    panel and the descriptions file cannot drift. No camera and no weights needed.
"""
# The window's configuration: the shipped one, loaded through the configuration layer, without a
# scale (nothing measured) — what these tests built the window with before configurations existed.
#   Unit [Configuration_Str(object)]
CONST_CONFIGURATION = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)

# The window's name-mangling prefix, for reaching its private state.
CONST_MANGLE = '_AnyScan_Window_Cls'


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


def _Private(window, name: str):
    """Fetch a name-mangled private attribute or method of the window."""
    return getattr(window, CONST_MANGLE + name)


def _Object(sentence: str, score=None) -> Detection_Str:
    """A detection whose composed Sentence is preset, with an optional FastSAM score."""
    return Detection_Str(Label='part', Bbox=(0, 0, 8, 8), Sentence=sentence, Cue='both',
                         Segmenter_Score=score)


def _Window_With(reference_background_path, result: Analysis_Str) -> AnyScan_Window_Cls:
    """A window that has scanned a frame and rendered the given result."""
    window = AnyScan_Window_Cls(Configuration_Str=CONST_CONFIGURATION, camera=File_Camera_Cls(reference_background_path))
    _Private(window, '__camera').Connect()
    _Private(window, '__Sync_Controls')()
    _Private(window, '__On_Scan_Button_Clicked')()
    _Private(window, '__On_Analysis_Finished')(result)
    return window


def _Label_Line_Widgets(block):
    """The (name, confidence, description) QLabels of one object block, in order."""
    column = block.layout()
    label_line = column.itemAt(0).widget()             # the label-line widget (name + conf)
    description = column.itemAt(1).widget()            # the description QLabel
    row = label_line.layout()
    name = row.itemAt(0).widget()
    confidence = row.itemAt(1).widget()
    return name, confidence, description


def _Shown(label: QLabel) -> str:
    """The text a label SHOWS: a rich-text label is rendered through Qt's HTML rules first (which
    collapse a plain leading space), so the comparison is with the screen, not the source string."""
    if label.textFormat() != Qt.RichText:
        return label.text()
    document = QTextDocument()
    document.setHtml(label.text())
    return document.toPlainText().replace('\xa0', ' ')


def _Line_Texts(window) -> list:
    """The (name, confidence, description) text triple each object block shows, in order."""
    layout = _Private(window, '__object_list').box
    triples = []
    for i in range(layout.count()):
        name, confidence, description = _Label_Line_Widgets(layout.itemAt(i).widget())
        triples.append((_Shown(name), _Shown(confidence), _Shown(description)))
    return triples


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


def test_background_paragraph_is_one_uniformly_styled_label(qt_app, reference_background_path) -> None:
    """
    Description:
        The background sentence and the object count are ONE paragraph: a single label holds the
        whole shared header, in one font (the object-label size, regular weight), as plain text so
        no markup can style part of it differently — no bold anywhere, the count included. No
        other label in the panel carries either half. A size-only check would miss a split into
        two labels (or a bold span inside one), so this asserts the structure, the text format and
        the one style. The card title above remains the panel's largest text.
    """

    objects = [_Object('A silver ring.', 0.91), _Object('A blue bracket.')]
    background = 'A green background that is very bright.'
    window = _Window_With(reference_background_path,
                          Analysis_Str(Objects=objects, Background=background,
                                       Verdict='2 found', Verdict_Level='ok', Task='caption'))
    header = Screen_Header(objects, background)
    lead = _Private(window, '__reading_lead')

    # One element: exactly one visible label shows either sentence, and it shows both.
    carriers = [label for label in window.findChildren(QLabel) if label.isVisibleTo(window)
                and (background in label.text() or 'described below' in label.text())]
    assert carriers == [lead]
    assert lead.text() == header
    # Uniform style: plain text (no rich-text spans), no weight or size set per part in a sheet.
    assert lead.textFormat() == Qt.PlainText
    assert 'font' not in lead.styleSheet() and '<' not in lead.text()
    # The one style: the object-label size, regular weight — not bold, not DemiBold.
    layout = _Private(window, '__object_list').box
    name, _confidence, description = _Label_Line_Widgets(layout.itemAt(0).widget())
    assert lead.font().pointSizeF() == name.font().pointSizeF() == Style.CONST_TYPE_SCENE_BACKGROUND
    assert lead.font().weight() == QFont.Normal < name.font().weight()
    assert not lead.font().bold()
    # The hierarchy around it: the card title is larger, the descriptions smaller.
    title = next(label for label in window.findChildren(QLabel)
                 if label.text() == 'Scene Understanding')
    assert title.font().pointSizeF() > lead.font().pointSizeF()
    assert lead.font().pointSizeF() > description.font().pointSizeF()


def test_object_blocks_carry_the_shared_label_and_description(qt_app, reference_background_path) -> None:
    """
    Description:
        Each object is a two-level block whose label line is the shared name
        (Object_Label) plus its own confidence (Object_Confidence), joined by the shared
        separator, and whose second line is the object's own sentence. The panel's two
        label parts spell exactly the file's Object_Label_Full, and Object_Line joins that
        full label to the same sentence — so the panel cannot number, word or score an
        object differently from the file. A mix of scored and unscored objects exercises
        both the '%' suffix and the '—' suffix.
    """

    objects = [_Object('A silver ring.', 0.91), _Object('A blue bracket.', 0.83),
               _Object('A hex nut.')]
    window = _Window_With(reference_background_path,
                          Analysis_Str(Objects=objects, Background='A plain surface.',
                                       Verdict='3 found', Verdict_Level='ok', Task='caption'))

    triples = _Line_Texts(window)
    assert len(triples) == len(objects)
    for i, det in enumerate(objects):
        name, confidence, description = triples[i]
        assert name == Object_Label(i)                  # 'Object N', the shared name
        # The confidence part is the separator plus the shared confidence suffix.
        assert confidence == CONST_LABEL_SEPARATOR + Object_Confidence(det)
        # The two panel parts spell exactly the file's one-line full label.
        assert name + confidence == Object_Label_Full(i, det)
        assert description == det.Sentence
        # The file's one-line form is the full label and the sentence joined.
        assert Object_Line(i, det) == '%s - %s' % (Object_Label_Full(i, det), description)

    # The confidence suffix carries the object's own score, or '—' when it has none.
    assert _Line_Texts(window)[0][1].endswith('Confidence 91%')
    assert _Line_Texts(window)[2][1].endswith('Confidence —')


def test_object_blocks_are_single_colour_two_level(qt_app, reference_background_path) -> None:
    """
    Description:
        Each object block is a SINGLE colour (Style.CONST_INK = '#2b2455') on two levels —
        the label line larger and heavier, the description smaller and regular — the
        hierarchy is size and weight, not colour, and there is no per-object colour on the
        text. Within the label line the name leads: it is heavier than its confidence, which
        shares the name's size but a lighter weight.
    """

    objects = [_Object('A silver ring.', 0.91), _Object('A blue bracket.')]
    window = _Window_With(reference_background_path,
                          Analysis_Str(Objects=objects, Background='A plain surface.',
                                       Verdict='2 found', Verdict_Level='ok', Task='caption'))

    layout = _Private(window, '__object_list').box
    for i in range(layout.count()):
        name, confidence, description = _Label_Line_Widgets(layout.itemAt(i).widget())
        # All three lines are the one panel colour, and none carries a per-object colour.
        for widget in (name, confidence, description):
            assert Style.CONST_INK in widget.styleSheet()
            assert 'border-left' not in widget.styleSheet()
        # The label is larger and heavier than the description (size and weight, from the theme).
        assert name.font().pointSizeF() > description.font().pointSizeF()
        assert name.font().weight() > description.font().weight()
        # The name is unmistakably the heading: its confidence is BOTH smaller and lighter,
        # so the two do not read as one continuous run of text.
        assert name.font().pointSizeF() > confidence.font().pointSizeF()
        assert name.font().weight() > confidence.font().weight()


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
    assert lead.text() == 'A plain surface. No objects were detected on it.'
    assert '0 object' not in lead.text()
    assert _Line_Texts(window) == []


def test_a_judged_object_shows_its_verdict_between_label_and_description(qt_app, reference_background_path) -> None:
    """
    Description:
        In a catalogue mode each object block shows its verdict lines (Reporting.Verdict_Lines) — the state
        word first, then the reasons and the size note — between the label line and the description, as
        plain text in the ink, weighted above the description. An object with no verdict (Segment
        Anything) keeps its two-level block.
    """

    from Parameters.Vision import Catalogue_Result_Str
    from Vision.Utilities.Dimensions import Check_Dimension
    from Reporting.Core import Verdict_Lines
    judged = Detection_Str(Label='plate', Bbox=(0, 0, 8, 8), Sentence='A machined plate.', Cue='both', Verdict='NOK',
                           Dimension_Checks=[Check_Dimension('length', 62.0, 60.0, 1.5)],
                           Catalogue=Catalogue_Result_Str(Similarity=0.91, Side='front', Identify_Similarity=0.75,
                                                          Area_Ratio=1.0, Unspecified_Area_Ratio=1.7,
                                                          Center_Distance_Mm=80.0, Verified_Radius_Mm=74.3))
    window = _Window_With(reference_background_path,
                          Analysis_Str(Objects=[judged, _Object('A washer.')], Background='A surface.',
                                       Verdict='2 found', Verdict_Level='ok', Task='caption'))
    layout = _Private(window, '__object_list').box
    first, second = layout.itemAt(0).widget().layout(), layout.itemAt(1).widget().layout()
    assert first.count() == 3 and second.count() == 2
    verdict = first.itemAt(1).widget()
    assert verdict.text() == '\n'.join(Verdict_Lines(judged))
    assert verdict.text() == ('State: NOK.\nReason: The length is 62.00 mm, expected 60.00 ± 1.50 mm.\n'
                              'Note: The size check is not verified here: 80 mm from the frame centre, verified to 74 mm.')
    assert verdict.textFormat() == Qt.PlainText and verdict.font().weight() > first.itemAt(2).widget().font().weight()
    assert first.itemAt(2).widget().text() == 'A machined plate.'


@pytest.mark.parametrize('level, ground, ink', [('fail', 'CONST_FAIL_SOFT', 'CONST_FAIL_INK'),
                                                ('warn', 'CONST_WARN_SOFT', 'CONST_WARN_INK'),
                                                ('ok', 'CONST_OK_SOFT', 'CONST_OK_INK')])
def test_the_badge_paints_each_verdict_level_legibly(qt_app, level: str, ground: str, ink: str) -> None:
    """
    Description:
        The status badge, rendered: a NOK paints the 'fail' level — the NOK ink on its magenta tint — and the
        warning and OK levels their own; on each, the darkest painted text clears 4.5:1 against the ground
        actually painted, and the ground is the level's token, so a NOK can never show green.
    """

    import numpy as np
    from UI.Widgets import Badge_Cls
    from Parameters.Theme import Contrast_Ratio
    badge = Badge_Cls()
    badge.Set_State('NOK · 2 of 5', level)
    badge.resize(badge.sizeHint())
    image = badge.grab().toImage().convertToFormat(4)          # QImage.Format_RGB32
    pixels = np.frombuffer(image.constBits().asstring(image.byteCount()), dtype=np.uint8)
    pixels = pixels.reshape(image.height(), image.bytesPerLine() // 4, 4)[:, :image.width(), 2::-1]
    hexes = ['#%02X%02X%02X' % tuple(int(v) for v in p) for p in pixels.reshape(-1, 3)]
    centre = '#%02X%02X%02X' % tuple(int(v) for v in pixels[pixels.shape[0] // 2, 3])
    assert centre.lower() == getattr(Style, ground).lower()
    darkest = min(hexes, key=lambda h: sum(int(h[i:i + 2], 16) for i in (1, 3, 5)))
    assert Contrast_Ratio(darkest, getattr(Style, ground)) >= 4.5
    assert Contrast_Ratio(getattr(Style, ink), getattr(Style, ground)) >= 4.5
