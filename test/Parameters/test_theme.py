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

# Pytest (Testing framework) [pip3 install pytest]
import pytest
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
        NOK magenta. Because the box is drawn INTO the frame, it must also clear the project's
        distinctness floor against the real annotation surfaces — and its worst case, having no
        hue to lean on, is grey-on-grey against bright machined steel.
    """

    import colorsys

    neutral = Theme.CONST_DETECTION_COLORS[0]
    ok = Theme.CONST_VERDICT_COLORS['OK'][0]
    nok = Theme.CONST_VERDICT_COLORS['NOK'][0]

    # A distinct token, not an alias.
    assert Theme.CONST_DETECTION_COLORS != Theme.CONST_VERDICT_COLORS['OK']
    assert Theme.Detection_Color() == Theme.CONST_DETECTION_COLORS

    # Clearly separated from OK, and more so than before (lightening it along the grey axis to
    # clear the steel also pushed it further from the medium-dark OK indigo, ΔE ~46 -> ~53).
    assert Theme.Delta_E(neutral, ok) > 46
    # Off the indigo axis: a low-saturation grey, not a saturated indigo like OK.
    def _sat(hex_color):
        r, g, b = (v / 255.0 for v in Theme.Hex_To_Rgb(hex_color))
        return colorsys.rgb_to_hls(r, g, b)[2]
    assert _sat(neutral) < 0.20 < _sat(ok)
    # Still calm, and far from the loud NOK.
    assert Theme.Delta_E(neutral, nok) > 60

    # Drawn into the frame, so it must clear the distinctness floor against the real annotation
    # surfaces. The worst case is grey-on-grey against bright machined steel (sets 003/005),
    # where the earlier #949AA6 sat at the steel's own lightness and collapsed under the floor.
    from Vision.Utilities.Annotate import CONST_ANNOTATE_MIN_DELTA_E
    bright_steel = '#808083'  # ~(128,128,131), the machined-steel surface in sets 003/005
    assert Theme.Delta_E(neutral, bright_steel) > CONST_ANNOTATE_MIN_DELTA_E


def test_label_mask_fill_is_a_visible_tint_of_its_box() -> None:
    """
    Description:
        Every object colour carries a third entry, the label-mask fill, and the fill must do its
        job on screen, not only exist as a token. For the two verdict colours and the neutral
        detection colour:
          - the box outline stays clearly visible against its own fill (ΔE >= the fill floor,
            stricter than the general distinctness floor);
          - the fill is not white — the failure it replaced (ΔE from white >= its floor);
          - the fill reads as light against the black mask ground (>= 4.5:1), so the silhouette
            stays obvious;
          - a chromatic fill is recognisably the box's own hue (within a few degrees, at a real
            fraction of the box's chroma), not a near-grey.
    """

    triples = {'OK': Theme.CONST_VERDICT_COLORS['OK'], 'NOK': Theme.CONST_VERDICT_COLORS['NOK'],
               'neutral': Theme.CONST_DETECTION_COLORS}
    for name, (box, _ink, fill) in triples.items():
        assert Theme.Delta_E(box, fill) >= Theme.CONST_MASK_FILL_MIN_BOX_DELTA_E, \
            '%s: outline %s barely separates from fill %s (ΔE=%.1f)' % (name, box, fill,
                                                                     Theme.Delta_E(box, fill))
        assert Theme.Delta_E(fill, '#FFFFFF') >= Theme.CONST_MASK_FILL_MIN_WHITE_DELTA_E, \
            '%s: fill %s reads as white (ΔE=%.1f)' % (name, fill, Theme.Delta_E(fill, '#FFFFFF'))
        assert Theme.Ground_Contrast(fill) >= Theme.CONST_MASK_FILL_MIN_GROUND_CONTRAST, \
            '%s: fill %s does not read as light on black (%.1f:1)' % (name, fill,
                                                                   Theme.Ground_Contrast(fill))

    for name in ('OK', 'NOK'):
        box, _ink, fill = triples[name]
        _Lb, box_chroma, box_hue = Theme.Lch_Of(box)
        _Lf, fill_chroma, fill_hue = Theme.Lch_Of(fill)
        shift = abs((fill_hue - box_hue + 180.0) % 360.0 - 180.0)
        assert shift <= Theme.CONST_MASK_FILL_MAX_HUE_SHIFT, (name, shift)
        assert fill_chroma >= Theme.CONST_MASK_FILL_MIN_CHROMA_FRACTION * box_chroma, \
            (name, fill_chroma, box_chroma)


def test_neutral_fill_is_derived_from_its_box_inside_the_valid_window() -> None:
    """
    Description:
        The neutral fill is DERIVED from the neutral box, not hand-set, and the window it has to
        fit is under 3 L* wide: darker than ~48.9 falls under 4.5:1 against the black ground,
        lighter than the box's L* minus 25 collides with the outline. So the test asserts the
        window directly — its bounds, and the shipped fill's L* at least the stated margin (0.5
        L*) inside BOTH bounds — on top of the floors, so a change to the box that squeezes the
        fill toward an edge fails here by number, not by inspection. The fill also keeps the box's
        hue and chroma and is darker than the box.
    """

    box, _ink, fill = Theme.CONST_DETECTION_COLORS
    assert box == Theme.CONST_DETECTION_BOX
    assert fill == Theme.Neutral_Mask_Fill(box)                   # derived, not a free literal

    lower, upper = Theme.Neutral_Fill_Window(box)
    margin = Theme.CONST_MASK_FILL_WINDOW_MARGIN
    assert (round(lower, 2), round(upper, 2)) == (48.88, 51.85)     # the window stated in Theme
    fill_l = Theme.Lch_Of(fill)[0]
    assert lower + margin <= fill_l <= upper - margin, \
        'neutral fill L* %.2f is within %.1f of its window [%.2f, %.2f]' % (fill_l, margin,
                                                                         lower, upper)

    box_l, box_c, box_h = Theme.Lch_Of(box)
    fill_l, fill_c, fill_h = Theme.Lch_Of(fill)
    assert fill_l < box_l                                          # darker: the outline is lighter
    assert abs(fill_c - box_c) < 1.0                                # the box's own chroma
    assert abs((fill_h - box_h + 180.0) % 360.0 - 180.0) < 5.0      # and its own hue


def test_neutral_fill_follows_the_box_and_fails_loudly_when_no_fill_fits() -> None:
    """
    Description:
        Changing the neutral box moves the derived fill with it, still clearing every floor. A
        box too dark to leave a window of twice the margin (below L* 74.88) has NO valid darker
        fill: the derivation raises, naming the window, instead of clamping to a fill that breaks
        a floor — and since the shipped token is derived at import, such a box fails the import.
    """

    for box in ('#C4CAD6', '#BFC3CC'):                             # lighter neutral boxes
        fill = Theme.Neutral_Mask_Fill(box)
        assert Theme.Delta_E(box, fill) >= Theme.CONST_MASK_FILL_MIN_BOX_DELTA_E
        assert Theme.Ground_Contrast(fill) >= Theme.CONST_MASK_FILL_MIN_GROUND_CONTRAST
        assert Theme.Delta_E(fill, '#FFFFFF') >= Theme.CONST_MASK_FILL_MIN_WHITE_DELTA_E

    with pytest.raises(ValueError, match='No valid neutral mask fill'):
        Theme.Neutral_Mask_Fill('#949AA6')                          # the earlier, darker neutral
