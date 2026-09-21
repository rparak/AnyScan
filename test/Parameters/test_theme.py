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
# File Name: ../test/Parameters/test_theme.py
## =========================================================================== ##

# System (Default)
import itertools
# Custom Lib.: AnyScan domain — the Qt-free colour palette
#   ../Parameters/Theme
import Parameters.Theme as Theme

"""
Description:
    Tests for the Qt-free colour palette. The palette is a shared design token, so the
    tests pin what both the UI and the annotation renderer depend on: the index colours
    are stable and distinct, the palette extension never lands on a reserved verdict
    hue, and the hex conversions match OpenCV's channel order.
"""


def test_module_is_qt_free() -> None:
    """
    Description:
        Theme imports no Qt and no OpenCV — it is pure values, so the Qt-free vision
        layer can read the same palette the UI does.
    """

    source = open(Theme.__file__).read()
    assert 'PyQt' not in source and 'import cv2' not in source


def test_base_indices_are_the_hand_tuned_pairs() -> None:
    """
    Description:
        The first six indices return the hand-tuned base pairs unchanged; the same
        index always returns the same colour (stable across runs and files).
    """

    for i, pair in enumerate(Theme.CONST_INDEX_COLORS):
        assert Theme.Index_Color(i) == pair
    assert Theme.Index_Color(3) == Theme.Index_Color(3)


def test_ten_objects_get_ten_distinct_colours() -> None:
    """
    Description:
        A ten-object frame (Image_001) gets ten distinct box colours: past the sixth,
        the palette is extended by shading a base colour rather than repeating it.
    """

    boxes = [Theme.Index_Color(i)[0] for i in range(10)]
    assert len(set(boxes)) == 10


def test_no_index_colour_is_a_reserved_verdict_hue() -> None:
    """
    Description:
        Neither the base palette nor its generated variants may fall in a reserved
        pass/fail/degraded hue — an object painted green would silently read as 'the
        good one'. Checks well past a realistic object count.
    """

    for i in range(len(Theme.CONST_INDEX_COLORS) * 3):
        box = Theme.Index_Color(i)[0]
        hue = Theme.Hue_Of(box)
        assert not any(low <= hue <= high for low, high in Theme.CONST_RESERVED_HUE_BANDS), \
            'Index_Color(%d)=%s hue=%.3f is reserved' % (i, box, hue)


def test_twelve_index_colours_are_perceptually_distinct() -> None:
    """
    Description:
        The ΔE distinctness invariant, targeted at Index_Color DIRECTLY — the object
        rendering is now keyed by verdict colour, so this no longer describes the default
        mask; it guards the RETAINED per-object palette (used by the diagnostic index-fill
        mask). Every pair of the first twelve index colours is at least a clear perceptual
        distance apart (CIE76 ΔE), not merely a different hex — a dense frame leans on the
        generated variants, and the diagnostic colour coding is worthless if two objects
        read as the same colour. Checked in Lab, not RGB, which does not match the eye.
    """

    for a, b in itertools.combinations(range(12), 2):
        distance = Theme.Delta_E(Theme.Index_Color(a)[0], Theme.Index_Color(b)[0])
        assert distance >= 12.0, \
            'index %d and %d are too close (ΔE=%.1f)' % (a, b, distance)


def test_verdict_colour_comes_from_the_one_constant() -> None:
    """
    Description:
        Verdict_Color reads the (box, ink) pair for a verdict from the single
        CONST_VERDICT_COLORS definition, and an unknown or empty verdict falls back to
        the default (OK) rather than raising — so a detection with no verdict still
        renders, and the fail colour lives in exactly one place.
    """

    assert Theme.Verdict_Color('OK') == Theme.CONST_VERDICT_COLORS['OK']
    assert Theme.Verdict_Color('NOK') == Theme.CONST_VERDICT_COLORS['NOK']
    assert Theme.Verdict_Color('OK')[0] == '#6C63B5'
    assert Theme.Verdict_Color('NOK')[0] == '#ff005c'
    # An unknown/empty verdict falls back to OK, never raises.
    assert Theme.Verdict_Color('') == Theme.CONST_VERDICT_COLORS['OK']
    assert Theme.Verdict_Color('bogus') == Theme.CONST_VERDICT_COLORS[Theme.CONST_VERDICT_DEFAULT]


def test_hex_conversions_match_opencv_order() -> None:
    """
    Description:
        Hex_To_Rgb returns (R, G, B); Hex_To_Bgr returns the same colour in OpenCV's
        (B, G, R) order, so a token drawn with cv2 is the colour it names.
    """

    assert Theme.Hex_To_Rgb('#ff005c') == (255, 0, 92)
    assert Theme.Hex_To_Bgr('#ff005c') == (92, 0, 255)
    assert Theme.Hex_To_Bgr('#ffffff') == (255, 255, 255)


def test_neutral_detection_colour_is_distinct_and_off_the_indigo_axis() -> None:
    """
    Description:
        The neutral detection colour ('detected, not judged') must be visibly different from the
        OK verdict colour, not a quieter shade of it — otherwise a detect-only set and an all-OK
        classified set look the same and the per-set flag distinction cannot be seen. It is a
        distinct token, well separated from OK in perceptual distance (ΔE >> the ~26 of the old
        slate-indigo), off the indigo axis (a low-saturation grey), and calm — far from the loud
        NOK magenta.
    """

    import colorsys

    neutral = Theme.CONST_DETECTION_COLORS[0]
    ok = Theme.CONST_VERDICT_COLORS['OK'][0]
    nok = Theme.CONST_VERDICT_COLORS['NOK'][0]

    # A distinct token, not an alias.
    assert Theme.CONST_DETECTION_COLORS != Theme.CONST_VERDICT_COLORS['OK']
    assert Theme.Detection_Color() == Theme.CONST_DETECTION_COLORS

    # Clearly separated from OK, and much more so than the old same-axis slate-indigo (ΔE ~26).
    assert Theme.Delta_E(neutral, ok) > 35
    # Off the indigo axis: a low-saturation grey, not a saturated indigo like OK.
    def _sat(hex_color):
        r, g, b = (v / 255.0 for v in Theme.Hex_To_Rgb(hex_color))
        return colorsys.rgb_to_hls(r, g, b)[2]
    assert _sat(neutral) < 0.20 < _sat(ok)
    # Still calm, and far from the loud NOK.
    assert Theme.Delta_E(neutral, nok) > 60
