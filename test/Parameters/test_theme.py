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
    assert Theme.Verdict_Color('OK')[0] == '#640ABA'
    assert Theme.Verdict_Color('NOK')[0] == '#FF6540'
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


def test_every_warning_is_the_amber_and_the_retired_state_colours_are_gone() -> None:
    """
    Description:
        Three states, three colours (the owner's rule of 2026-10-16): every Warning, whatever its kind, is the amber
        #FFC226 with its mask fill #B28508, and no token, label ground or shown-state colour is left for the foreign
        object's grey #B4A6BE or Unspecified's blue #33A3FF and their badge grounds and mask pairs. The grey stays
        only as the disabled label's token, which is no verdict's.
    """

    assert Theme.Verdict_Color('Warning') == ('#FFC226', '#FFC226', '#B28508')
    assert (Theme.Label_Ground('Warning'), Theme.Mask_Outline_Color('Warning')) == ('#FFC226', '#FFC226')
    tokens = {name: value.upper() for name, value in vars(Theme).items()
              if name.startswith('CONST_') and isinstance(value, str)}
    assert not any(name.startswith(('CONST_FOREIGN', 'CONST_UNSPECIFIED')) for name in vars(Theme))
    assert not set(tokens.values()) & {'#33A3FF', '#C6E4FF', '#748DB1', '#CAC0D3', '#DBCCE5', '#897C93'}
    assert {name for name, value in tokens.items() if value == '#B4A6BE'} == {'CONST_CONTROL_DISABLED_TEXT',
                                                                            'CONST_PRIMARY_DISABLED_TEXT'}
    assert not hasattr(Theme, 'State_Color')


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
    # the mask's own derived neutral outline over the neutral fill (the frame's box never sits on it).
    triples = {'OK': Theme.CONST_VERDICT_COLORS['OK'], 'NOK': Theme.CONST_VERDICT_COLORS['NOK'],
               'Warning': Theme.CONST_VERDICT_COLORS['Warning'],
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

    for name in ('OK', 'NOK', 'Warning'):
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
        and its own outline, darker than the fill, in the neutral ink's hue and chroma (the detect-only mode's;
        Unspecified's box until 2026-10-16). That ink keeps its own lightness
        for the chip's white numeral; on the mask the outline only meets the fill and the black ground,
        where that box would miss the 4.5:1 floor. The test states the two
        bounds and asserts the pair's placement against them with the margin:
          - fill: as light as the fill/white floor allows (L* <= 81.31 for this chroma at the
            floor of 21), placed at that bound less the 0.5 margin — never back to a dark fill;
          - outline: inside [48.88 (4.5:1 on black), fill L* - 25], at least 0.5 from the lower
            bound and at least 25 + 0.5 below the fill.
    """

    box = Theme.CONST_DETECTION_INK                                 # derived from the neutral ink (not a verdict's)
    outline, fill = Theme.Neutral_Mask_Colors(box)
    assert (outline, fill) == (Theme.Detection_Mask_Outline(), Theme.Detection_Color()[2])

    outline_lower, fill_upper = Theme.Neutral_Mask_Bounds(box)
    margin = Theme.CONST_MASK_FILL_WINDOW_MARGIN
    assert (round(outline_lower, 2), round(fill_upper, 2)) == (48.88, 81.31)   # stated in Theme
    outline_l, fill_l = Theme.Lch_Of(outline)[0], Theme.Lch_Of(fill)[0]
    assert abs(fill_l - (fill_upper - margin)) < 0.3                # the lightest allowed fill
    assert fill_l >= 79.0                                           # light — the L* ~80 fill
    assert outline_l >= outline_lower + margin, (outline_l, outline_lower)
    assert fill_l - outline_l >= Theme.CONST_MASK_FILL_MIN_BOX_DELTA_E + margin, (fill_l, outline_l)
    assert Theme.Ground_Contrast(outline) >= Theme.CONST_MASK_FILL_MIN_GROUND_CONTRAST
    assert Theme.Ground_Contrast(box) < Theme.CONST_MASK_FILL_MIN_GROUND_CONTRAST  # why the mask has its own

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
    for outline, fill in (lighter, Theme.Neutral_Mask_Colors(Theme.CONST_DETECTION_INK)):
        assert Theme.Delta_E(outline, fill) >= Theme.CONST_MASK_FILL_MIN_BOX_DELTA_E
        assert Theme.Delta_E(fill, '#FFFFFF') >= Theme.CONST_MASK_FILL_MIN_WHITE_DELTA_E
        assert Theme.Ground_Contrast(outline) >= Theme.CONST_MASK_FILL_MIN_GROUND_CONTRAST

    previous = Theme.CONST_MASK_FILL_MIN_BOX_DELTA_E
    try:
        Theme.CONST_MASK_FILL_MIN_BOX_DELTA_E = previous + 6.0
        with pytest.raises(ValueError, match='No valid neutral mask pair'):
            Theme.Neutral_Mask_Colors(Theme.CONST_DETECTION_INK)
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
                   Theme.CONST_LOG_ERROR])
    closest = min((Theme.Delta_E(color, mark), color, mark) for color in Theme.Heatmap_Colors() for mark in reserved)
    assert closest[0] >= CONST_ANNOTATE_MIN_DELTA_E, closest


def test_every_catalogue_state_has_its_colour() -> None:
    """
    Description:
        Each of the three states a catalogue mode gives has a colour triple: OK the purple, NOK the orange-red and
        Warning the JIC amber, every kind of it; each state's ink, its colour in the charts, the legends and the History
        filter, is its box itself (one colour per state, the owner's rule of 2026-10-16); on the label mask every state
        keeps its box as the outline. The three boxes stay ΔE >= 12 apart.
    """

    from Parameters.Vision import CONST_VERDICTS
    from Vision.Utilities.Annotate import CONST_ANNOTATE_MIN_DELTA_E
    assert CONST_VERDICTS == ('OK', 'NOK', 'Warning')
    assert set(Theme.CONST_VERDICT_COLORS) == set(CONST_VERDICTS)
    expected = {'OK': '#640ABA', 'NOK': '#FF6540', 'Warning': '#FFC226'}
    assert {state: Theme.Verdict_Color(state)[:2] for state in expected} == {state: (c, c) for state, c in expected.items()}
    assert [Theme.Mask_Outline_Color(v) for v in CONST_VERDICTS] == [Theme.Verdict_Color(v)[0] for v in CONST_VERDICTS]
    boxes = [Theme.Verdict_Color(v)[0] for v in CONST_VERDICTS]
    assert min(Theme.Delta_E(a, b) for i, a in enumerate(boxes) for b in boxes[i + 1:]) >= CONST_ANNOTATE_MIN_DELTA_E


def test_every_chip_numeral_is_white() -> None:
    """
    Description:
        A chip on the frame is filled with its box (a verdict's, or the detect-only neutral) and its numeral is plain
        white on every one (docs/design-decisions.md, "Every chip carries a white numeral"): no per-chip exception and
        no rim. The ratios are pinned so a change to a box colour revisits them: the purple 9.15:1, and the owner's
        accepted exceptions, the NOK orange-red 2.92:1 and Warning's amber 1.62:1, every Warning's whatever its kind.
    """

    assert Theme.CONST_CHIP_NUMERAL == '#FFFFFF'
    for verdict, ratio in (('OK', 9.15), ('NOK', 2.92), ('Warning', 1.62)):
        assert round(Theme.Contrast_Ratio('#FFFFFF', Theme.Verdict_Color(verdict)[0]), 2) == ratio, verdict
    assert not any(hasattr(Theme, name) for name in ('CONST_CHIP_NUMERAL_EXCEPTIONS', 'CONST_CHIP_NUMERAL_OUTLINES',
                                                       'Chip_Numeral_Color', 'Chip_Numeral_Outline'))


def test_the_detect_only_box_is_the_logo_purple() -> None:
    """
    Description:
        The detect-only box and chip (Segment Anything) are the logo purple, the token itself (the owner's choice of
        2026-10-15): #655E6D all but vanished on the green table (1.12:1, capture 20261015-143622_s1, table median
        #176550), and the grey-lilac #E1DCE6 tried before it carried a white numeral at 1.35:1. The purple carries it at
        9.15:1 and reads on the table by hue (ΔE 120.7). It equals the OK colour, accepted because a detect-only mode
        shows no verdict. The neutral ink #655E6D stays the detect-only mode's words and the label mask's derived pair.
    """

    table = '#176550'
    box = Theme.Detection_Color()[0]
    assert box == Theme.CONST_DETECTION_BOX == Theme.CONST_LOGO_INK == '#640ABA'
    assert round(Theme.Contrast_Ratio('#FFFFFF', box), 2) == 9.15
    assert round(Theme.Contrast_Ratio(box, table), 2) == 1.31 and round(Theme.Delta_E(box, table), 1) == 120.7
    assert Theme.Detection_Color()[1] == '#655E6D'
    assert (Theme.Detection_Mask_Outline(), Theme.Detection_Color()[2]) == ('#817A8A', '#CEC6D7')
def test_the_palette_keeps_the_brands_rules() -> None:
    """
    Description:
        The palette's rules from the JIC Smart Factory brief: the guide's yellow (#FFEF85 and its two tints) is
        decoration and is no token, so it marks no status and no defect; no object is marked in the JIC green, which
        would sit in the green table's hue (every verdict box and fill >= ΔE 40 from it); a verdict's words clear
        4.5:1 on the ground they sit on (Label_Ground: the badge, the diagram's labels); and, one colour per state (the
        owner's rule of 2026-10-16), a verdict's colour on the white card is its box itself, with no darker shade of
        it (the markers' dark edge, Chart_Edge, is gone since 2026-10-18).
    """

    tokens = {value.upper() for name, value in vars(Theme).items() if name.startswith('CONST_') and isinstance(value, str)}
    assert not tokens & {'#FFEF85', '#F2E16A', '#E3CD35'}
    green = Theme.CONST_OK_BORDER
    for verdict in ('OK', 'NOK', 'Warning'):
        box, ink, fill = Theme.Verdict_Color(verdict)
        assert min(Theme.Delta_E(box, green), Theme.Delta_E(fill, green)) >= 40, verdict
        assert Theme.Contrast_Ratio(Theme.CONST_INK, Theme.Label_Ground(verdict)) >= 4.5, verdict
        assert ink == box, verdict
    assert not hasattr(Theme, 'Chart_Edge') and not hasattr(Theme, 'CONST_CHART_EDGE_LIGHTNESS')


def test_the_charts_light_ink_is_the_lightest_of_the_dark_inks_hue_that_clears_3_to_1() -> None:
    """
    Description:
        The Trends run mean's light neutral (CONST_CHART_LIGHT_INK) is #9890A0: the detection ink's own hue and chroma
        at L* 61, 3.07:1 on white, above the 3:1 a graphic needs (WCAG 1.4.11), and as far as that floor allows from the
        frame mean's dark #655E6D (2.02:1, ΔE 19.9): 1 more L* would fall under 3:1. It is no verdict colour and not
        the retired foreign grey #B4A6BE.
    """

    light, dark = Theme.CONST_CHART_LIGHT_INK, Theme.CONST_DETECTION_INK
    assert (light, dark) == ('#9890A0', '#655E6D')
    assert round(Theme.Contrast_Ratio(light, '#FFFFFF'), 2) == 3.07 and round(Theme.Contrast_Ratio(light, dark), 2) == 2.02
    assert round(Theme.Delta_E(light, dark), 1) == 19.9
    lightness, chroma, hue = Theme.Lch_Of(light)
    _l, dark_chroma, dark_hue = Theme.Lch_Of(dark)
    assert abs(hue - dark_hue) < 2.0 and abs(chroma - dark_chroma) < 1.0
    import math
    lighter = getattr(Theme, '__Lab_To_Hex')(lightness + 1.0, chroma * math.cos(math.radians(hue)),
                                            chroma * math.sin(math.radians(hue)))
    assert Theme.Contrast_Ratio(lighter, '#FFFFFF') < 3.0
    assert min(Theme.Delta_E(light, Theme.Verdict_Color(v)[0]) for v in ('OK', 'NOK', 'Warning')) > 60
    assert light != Theme.CONST_CONTROL_DISABLED_TEXT

