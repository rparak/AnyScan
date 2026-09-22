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
# File Name: ../test/Vision/Utilities/test_caption.py
## =========================================================================== ##

# Custom Lib.: AnyScan domain — Florence-2 captioning
#   ../Vision/Utilities/Caption
import Vision.Utilities.Caption as Caption

"""
Description:
    Tests for the label distiller. Condense_Label is pure text and is pinned here.
    Describe is a thin wrapper around a Florence-2 generate() call — it needs the
    weights, so it is exercised by the slow end-to-end path, not here.
"""


def test_condense_label_strips_leadins_and_boundaries() -> None:
    """
    Description:
        Stacked Florence lead-ins are peeled and the phrase is cut at the first
        clause boundary, matching the characterization baseline.
    """

    assert Caption.Condense_Label('The image shows a close-up of a hex bolt on a green surface.') == 'hex bolt'
    assert Caption.Condense_Label('In this image we can see a washer.') == 'washer'
    assert Caption.Condense_Label('a photograph of two brass fittings sitting on a table') == \
        'two brass fittings'


def test_condense_label_empty_is_object() -> None:
    """
    Description:
        Nothing usable distils to the 'object' default.
    """

    assert Caption.Condense_Label('') == 'object'


def test_condense_label_caps_word_count() -> None:
    """
    Description:
        The label keeps at most CONST_LABEL_MAX_WORDS words.
    """

    label = Caption.Condense_Label('one two three four five six seven')
    assert len(label.split()) <= Caption.CONST_LABEL_MAX_WORDS


def test_condense_label_known_leadin_ordering_quirk() -> None:
    """
    Description:
        Known issue (KNOWN_ISSUES.md): 'this is a' matches before 'this is an',
        so 'This is an M6 ...' strands the 'n'. Pinned here so a future fix is a
        deliberate, visible change; the full caption is preserved in Detail
        regardless.
    """

    assert Caption.Condense_Label('This is an M6 stainless steel screw with a hexagonal head.') == \
        'n m6 stainless steel'


def test_module_has_no_toplevel_heavy_import() -> None:
    """
    Description:
        The module imports no Qt and no heavy runtime at load time — Describe
        injects cv2/np/torch/PIL, and Condense_Label needs none of them. This is
        what lets App/run.py import it without pulling the runtime.
    """

    source = open(Caption.__file__).read()
    assert 'PyQt' not in source
    assert '\nimport torch' not in source
    assert '\nimport cv2' not in source
