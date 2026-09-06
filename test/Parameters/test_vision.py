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
# File Name: ../test/Parameters/test_vision.py
## =========================================================================== ##

# Dataclasses (Data Classes)
import dataclasses
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan domain — data structures
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Analysis_Str

"""
Description:
    Tests for the extracted vision data structures. They are plain, Qt-free data
    carriers, so these pin the field names the whole pipeline reads, the defaults,
    and the independence of the mutable Objects list.
"""


def test_detection_str_defaults() -> None:
    """
    Description:
        A Detection_Str built with only the two required fields carries the
        documented defaults for the rest.
    """

    det = Detection_Str(Label='hex bolt', Bbox=(10, 20, 30, 40))

    assert det.Label == 'hex bolt'
    assert det.Bbox == (10, 20, 30, 40)
    assert det.Confidence is None
    assert det.Text is None
    assert det.Detail == ''
    assert det.Sentence == ''
    # The mask-pipeline fields carry their documented defaults.
    assert det.Mask is None
    assert det.Change_Coverage == 0.0
    assert det.Segmenter_Score is None


def test_detection_str_requires_label_and_bbox() -> None:
    """
    Description:
        Label and Bbox have no default, so constructing without them fails — the
        pipeline always supplies both, and a Detection without a box is meaningless.
    """

    with pytest.raises(TypeError):
        Detection_Str()


def test_analysis_str_defaults() -> None:
    """
    Description:
        A freshly constructed Analysis_Str is the idle state the panel starts in.
    """

    analysis = Analysis_Str()

    assert analysis.Summary == ''
    assert analysis.Objects == []
    assert analysis.Note == ''
    assert analysis.Latency_Ms == 0
    assert analysis.Verdict == 'Idle'
    assert analysis.Verdict_Level == 'idle'
    assert analysis.Task == 'detailed caption'


def test_analysis_str_objects_default_is_independent() -> None:
    """
    Description:
        The Objects default is a per-instance list (field(default_factory=list)),
        not one list shared across every Analysis_Str.
    """

    first = Analysis_Str()
    second = Analysis_Str()
    first.Objects.append(Detection_Str(Label='x', Bbox=(0, 0, 1, 1)))

    assert first.Objects != second.Objects
    assert second.Objects == []


def test_field_names_are_pascal_snake_case() -> None:
    """
    Description:
        The field names are the RP Pascal_Snake_Case the consumers read; guard
        against a silent revert to the old lower-case names.
    """

    detection_field_order = [f.name for f in dataclasses.fields(Detection_Str)]
    analysis_fields = {f.name for f in dataclasses.fields(Analysis_Str)}

    # The mask-pipeline fields are appended after Sentence; the original order is
    # preserved so positional construction and the operator-visible contract hold.
    assert detection_field_order == ['Label', 'Bbox', 'Confidence', 'Text', 'Detail',
                                     'Sentence', 'Mask', 'Change_Coverage', 'Segmenter_Score']
    assert analysis_fields == {'Summary', 'Objects', 'Note', 'Latency_Ms',
                               'Verdict', 'Verdict_Level', 'Task'}
