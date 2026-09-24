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

# Custom Lib.: AnyScan domain — the label distiller
#   ../Vision/Utilities/Caption
import Vision.Utilities.Caption as Caption
#   ../Reporting/Core
import Reporting.Core as Reporting

"""
Description:
    Tests for the label distiller. Condense_Label is pure text and is pinned here, on Gemma's
    phrasing.
"""


def test_condense_label_peels_gemmas_opener_but_the_line_keeps_it() -> None:
    """
    Description:
        Gemma opens every description 'The object is a …'; the label distiller peels that opener
        (it used to cut at ' is ' and every label read 'object'), while the object LINE keeps the
        model's full sentence.
    """

    assert Caption.Condense_Label('The object is a rectangular metallic plate, appearing silver.') == \
        'rectangular metallic plate'
    assert Caption.Condense_Label('The part appears to be a metallic bolt or screw.') == 'metallic bolt'
    assert Reporting.Clean_Detail('The object is a circular ring.') == 'The object is a circular ring.'


def test_condense_label_takes_the_phrase_up_to_its_head_noun() -> None:
    """
    Description:
        The label runs up to the head noun, which ends an English noun phrase: a comma between
        adjectives does not cut it ('a rectangular, flat plate' was 'rectangular'); a comma that
        opens a clause (an '-ing' participle, a hedge) does. One word after 'or' is an alternative
        noun and goes; more words mean 'or' joined modifiers, and only 'or <modifier>' goes. The
        last words are kept, where the noun is. Part names ending in '-ing' and short '-ed' words
        (a colour) are never dropped as participles.
    """

    cases = {'The object is a rectangular, flat plate of a bright, silvery-grey metal.': 'rectangular flat plate',
             'a stainless steel washer or spacer.': 'stainless steel washer',
             'The object is a small, white, rectangular plastic or ceramic component with holes.':
                 'white rectangular plastic component',
             'The object is a rectangular, metallic plate, likely steel.': 'rectangular metallic plate',
             'The object is a rectangular, flat part rendered in a uniform red.': 'rectangular flat part',
             'The object is a circular ring, appearing to be made of metal.': 'circular ring',
             'a steel bearing housing with bolts': 'steel bearing housing',
             'a small red block.': 'small red block'}
    for caption, label in cases.items():
        assert Caption.Condense_Label(caption) == label, caption


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


def test_module_has_no_toplevel_heavy_import() -> None:
    """
    Description:
        The module imports no Qt and no heavy runtime at load time — Condense_Label is
        pure text. This is what lets App/run.py import it without pulling the runtime.
    """

    source = open(Caption.__file__).read()
    assert 'PyQt' not in source
    assert '\nimport torch' not in source
    assert '\nimport cv2' not in source
