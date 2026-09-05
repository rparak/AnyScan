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
# File Name: ../test/Reporting/test_core.py
## =========================================================================== ##

# System (Default)
import os
# Custom Lib.: AnyScan domain — data structures and report composer
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str
#   ../Reporting/Core
import Reporting.Core as Reporting

"""
Description:
    Tests for the report composer. This is the panel's one voice, so the sentences
    are pinned exactly. The composer is Qt-free and depends only on the data
    structures, so nothing here needs a camera or the model.
"""

# The frame size passed to the composer. Position is not part of any sentence, so
# only its being fixed matters.
CONST_SIZE = (1920, 1200)


def _Detection(label: str, detail: str = '', confidence=None, text=None) -> Detection_Str:
    """
    Description:
        Build a Detection_Str fixture with a fixed box.

    Args:
        (1) label [string]: The distilled label.
        (2) detail [string]: The raw caption.
        (3) confidence [float]: The score, or None.
        (4) text [string]: Any reading, or None.

    Returns:
        (1) parameter [Detection_Str(object)]: The fixture.
    """

    return Detection_Str(Label=label, Bbox=(0, 0, 10, 10), Detail=detail,
                         Confidence=confidence, Text=text)


def test_count_word() -> None:
    """
    Description:
        Numbers zero to ten are words; anything past ten falls back to digits.
    """

    assert Reporting.Count_Word(0) == 'no'
    assert Reporting.Count_Word(1) == 'one'
    assert Reporting.Count_Word(10) == 'ten'
    assert Reporting.Count_Word(11) == '11'


def test_summarise_counts() -> None:
    """
    Description:
        The lead sentence agrees with the object count in words.
    """

    assert Reporting.Summarise([]) == 'No objects were located in this frame.'
    assert Reporting.Summarise([_Detection('a')]) == \
        'The frame contains one object, described as follows:'
    three = [_Detection('a'), _Detection('b'), _Detection('c')]
    assert Reporting.Summarise(three) == \
        'The frame contains three objects, which are described as follows:'


def test_verdict_levels() -> None:
    """
    Description:
        Empty is idle; unscored objects pass; a score under threshold degrades.
    """

    assert Reporting.Verdict([]) == ('Empty', 'idle')
    assert Reporting.Verdict([_Detection('a'), _Detection('b')]) == ('2 found', 'ok')
    assert Reporting.Verdict([_Detection('a', confidence=0.20)]) == ('Low confidence', 'warn')


def test_caption_sentence_strips_florence_leadins() -> None:
    """
    Description:
        The fixed Florence template prefix is peeled off and the sentence is
        cleaned into the panel's capitalisation and terminal stop.
    """

    assert Reporting.Caption_Sentence('In this image we can see a washer.') == 'A washer.'
    assert Reporting.Caption_Sentence('the image shows a close-up of a hex bolt') == \
        'A hex bolt.'


def test_describe_object_detail_reading_and_fallback() -> None:
    """
    Description:
        The full detail becomes the line; a reading is appended; an empty detail
        falls back to 'A <label>.'.
    """

    verbose = _Detection('hex bolt', detail='In this image we can see a hex bolt on a green surface.')
    assert Reporting.Describe_Object(verbose, CONST_SIZE) == 'A hex bolt on a green surface.'

    reading = _Detection('screw', detail='A close-up of a screw.', text='M6')
    assert Reporting.Describe_Object(reading, CONST_SIZE) == 'A screw, reading “M6”.'

    fallback = _Detection('nut', detail='')
    assert Reporting.Describe_Object(fallback, CONST_SIZE) == 'A nut.'


def test_compose_sets_sentence_and_never_reorders() -> None:
    """
    Description:
        Compose writes each object's Sentence and returns the objects in the same
        order (the index contract), plus the summary and note.
    """

    objects = [_Detection('washer', detail='A metal washer.'),
               _Detection('nut', detail='')]
    returned, summary, note = Reporting.Compose(objects, CONST_SIZE)

    assert returned is objects
    assert objects[0].Sentence == 'A metal washer.'
    assert objects[1].Sentence == 'A nut.'
    assert summary == 'The frame contains two objects, which are described as follows:'
    assert note == ''


def test_scene_note_empty_scene_carries_caption_and_advice() -> None:
    """
    Description:
        With no objects the note is the empty-scene explanation followed by the
        next action.
    """

    note = Reporting.Scene_Note([], CONST_SIZE, caption=Reporting.CONST_EMPTY_SCENE_EXPLANATION)
    assert note == (Reporting.CONST_EMPTY_SCENE_EXPLANATION.rstrip('.') + '.'
                    + ' Check the lighting and the focus, then scan again.')


def test_module_is_qt_free() -> None:
    """
    Description:
        The composer imports no Qt — it is a reusable domain module.
    """

    source = open(Reporting.__file__).read()
    assert 'PyQt' not in source
    assert 'import cv2' not in source
    assert 'import torch' not in source
