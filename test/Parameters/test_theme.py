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
    tests pin what both the UI and the annotation renderer depend on: the verdict colours
    come from one constant, the neutral detection colour and the label-mask pairs are
    derived and distinct, the heatmap scale rises in lightness clear of the reserved
    colours, and the hex conversions match OpenCV's channel order.
"""


def test_module_is_qt_free(top_level_imports) -> None:
    """
    Description:
        Theme imports no Qt and no OpenCV — it is pure values, so the Qt-free vision
        layer can read the same palette the UI does.
    """

    assert not top_level_imports(Theme.__file__) & {'PyQt5', 'cv2'}


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
    def _Saturation(hex_color: str) -> float:
        r, g, b = (v / 255.0 for v in Theme.Hex_To_Rgb(hex_color))
        return colorsys.rgb_to_hls(r, g, b)[2]
    assert _Saturation(neutral) < 0.20 < _Saturation(ok)
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

    # The pair that actually meets on the mask: a verdict box over its fill, and for detect-only
    # the mask's own darker neutral outline over the neutral fill (the frame's box never sits on it).
    triples = {'OK': Theme.CONST_VERDICT_COLORS['OK'], 'NOK': Theme.CONST_VERDICT_COLORS['NOK'],
               'neutral': (Theme.Detection_Mask_Outline(), None, Theme.Detection_Color()[2])}
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


def test_neutral_mask_pair_is_derived_light_fill_and_darker_outline() -> None:
    """
    Description:
        The label mask's neutral pair is DERIVED (Neutral_Mask_Colors), not hand-set: a LIGHT fill
        and its own darker outline, in the neutral box's hue and chroma. The frame's box keeps its
        lightness for the table and the parts; on the mask the outline only meets the fill and the
        black ground, so it is darker, which frees the fill to go light. The test states the two
        bounds and asserts the pair's placement against them with the margin:
          - fill: as light as the fill/white floor allows (L* <= 80.12 for this chroma at the
            floor of 21), placed at that bound less the 0.5 margin — never back to a dark fill;
          - outline: inside [48.88 (4.5:1 on black), fill L* - 25], at least 0.5 from the lower
            bound and at least 25 + 0.5 below the fill.
    """

    box = Theme.CONST_DETECTION_BOX
    outline, fill = Theme.Neutral_Mask_Colors(box)
    assert (outline, fill) == (Theme.Detection_Mask_Outline(), Theme.Detection_Color()[2])
    assert Theme.Detection_Color()[0] == box                        # the frame box is unchanged

    outline_lower, fill_upper = Theme.Neutral_Mask_Bounds(box)
    margin = Theme.CONST_MASK_FILL_WINDOW_MARGIN
    assert (round(outline_lower, 2), round(fill_upper, 2)) == (48.88, 80.12)   # stated in Theme
    outline_l, fill_l = Theme.Lch_Of(outline)[0], Theme.Lch_Of(fill)[0]
    assert abs(fill_l - (fill_upper - margin)) < 0.3                # the lightest allowed fill
    assert fill_l >= 79.0                                           # light — the L* ~80 fill
    assert outline_l >= outline_lower + margin, (outline_l, outline_lower)
    assert fill_l - outline_l >= Theme.CONST_MASK_FILL_MIN_BOX_DELTA_E + margin, (fill_l, outline_l)
    assert outline_l < Theme.Lch_Of(box)[0]                         # darker than the frame's box
    assert Theme.Ground_Contrast(outline) >= Theme.CONST_MASK_FILL_MIN_GROUND_CONTRAST

    box_l, box_c, box_h = Theme.Lch_Of(box)
    for colour in (outline, fill):                                  # the box's own hue and chroma
        _l, c, h = Theme.Lch_Of(colour)
        assert abs(c - box_c) < 1.0 and abs((h - box_h + 180.0) % 360.0 - 180.0) < 5.0


def test_neutral_mask_pair_ignores_box_lightness_and_fails_loudly_on_floors() -> None:
    """
    Description:
        The pair depends on the box's hue and chroma, not its lightness, so the frame's box can be
        re-tuned for the frame without moving the mask. The outline's window (~5.7 L* wide) is
        set by the floors; tighten the outline/fill floor past what it allows and the
        derivation raises, naming the window, instead of clamping to a pair that breaks one.
    """

    lighter = Theme.Neutral_Mask_Colors('#C4CAD6')
    for outline, fill in (lighter, Theme.Neutral_Mask_Colors(Theme.CONST_DETECTION_BOX)):
        assert Theme.Delta_E(outline, fill) >= Theme.CONST_MASK_FILL_MIN_BOX_DELTA_E
        assert Theme.Delta_E(fill, '#FFFFFF') >= Theme.CONST_MASK_FILL_MIN_WHITE_DELTA_E
        assert Theme.Ground_Contrast(outline) >= Theme.CONST_MASK_FILL_MIN_GROUND_CONTRAST

    previous = Theme.CONST_MASK_FILL_MIN_BOX_DELTA_E
    try:
        Theme.CONST_MASK_FILL_MIN_BOX_DELTA_E = previous + 6.0
        with pytest.raises(ValueError, match='No valid neutral mask pair'):
            Theme.Neutral_Mask_Colors(Theme.CONST_DETECTION_BOX)
    finally:
        Theme.CONST_MASK_FILL_MIN_BOX_DELTA_E = previous


def test_white_floor_rejects_what_reads_as_white_and_admits_the_l80_fill() -> None:
    """
    Description:
        The fill/white floor exists to stop a mask fill reading as white. It is 21, a chosen
        margin: it rejects the removed #F1F2F4 (ΔE 4.7, effectively white) and the L* 85 preview
        #CFD5E1 (ΔE ~16, where the fill starts drifting back toward white), and admits the shipped
        L* ~80 neutral fill. Rounding the floor back up to 25 would reject that fill — the test pins
        the reasoning, not just the number.
    """

    floor = Theme.CONST_MASK_FILL_MIN_WHITE_DELTA_E
    assert floor == 21.0
    assert Theme.Delta_E('#F1F2F4', '#FFFFFF') < floor               # the original white failure
    assert Theme.Delta_E('#CFD5E1', '#FFFFFF') < floor               # L* 85: drifting back to white
    shipped = Theme.Detection_Color()[2]
    assert Theme.Delta_E(shipped, '#FFFFFF') >= floor                # the L* ~80 fill clears it
    assert Theme.Delta_E(shipped, '#FFFFFF') < 25.0                  # and a 25 floor would reject it



def test_the_heatmap_colours_rise_in_lightness_across_the_scale() -> None:
    """
    Description:
        A hotter pixel always reads lighter: the heatmap's 256 colours rise in L* from a dark low end to
        a light high end, never falling by more than hex rounding (0.15 L*) between neighbours and
        rising strictly over every sixteenth step.
    """

    colors = Theme.Heatmap_Colors()
    lightness = [Theme.Lch_Of(color)[0] for color in colors]
    assert len(colors) == 256
    assert lightness[0] < 20.0 and lightness[-1] > 85.0
    assert all(lightness[i + 1] >= lightness[i] - 0.15 for i in range(255))
    assert all(lightness[i + 16] > lightness[i] for i in range(0, 240, 16))


def test_the_heatmap_colours_stay_clear_of_the_verdict_status_and_log_colours() -> None:
    """
    Description:
        No heatmap colour can be mistaken for a colour that means something else: every one of the 256
        clears the project's distinctness floor (CONST_ANNOTATE_MIN_DELTA_E) against the OK and NOK
        verdict colours (box, ink and fill), the status colours and their text twins, and the log and
        on-dark error colours. Viridis fails this (ΔE 4.2 from the OK ink), which is why the map is
        cividis.
    """

    from Vision.Utilities.Annotate import CONST_ANNOTATE_MIN_DELTA_E
    reserved = (list(Theme.CONST_VERDICT_COLORS['OK']) + list(Theme.CONST_VERDICT_COLORS['NOK'])
                + [Theme.CONST_OK, Theme.CONST_OK_INK, Theme.CONST_WARN, Theme.CONST_WARN_INK,
                   Theme.CONST_LOG_ERROR, Theme.CONST_ERROR_ON_DARK])
    closest = min((Theme.Delta_E(color, mark), color, mark) for color in Theme.Heatmap_Colors() for mark in reserved)
    assert closest[0] >= CONST_ANNOTATE_MIN_DELTA_E, closest
