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
# File Name: ../Parameters/Theme.py
## =========================================================================== ##

# System (Default)
import math
# Typing (Support for type hints)
import typing as tp

"""
Description:
    Initialization of constants.

    The console's colour palette, as pure values — no Qt, no OpenCV. Both the UI
    (UI.Utilities.Style, which imports and re-exports these for the widgets) and the
    Qt-free annotation renderer (Vision.Utilities.Annotate, which draws the on-disk
    result with OpenCV) read this ONE definition, so a box on the frame and its text
    in the panel are the same colour. This module lives in Parameters/ on purpose:
    the vision layer must never import UI/, or a UI/ import would sit inside a path
    that has to stay Qt-free and one careless addition would drag Qt into it.
"""
# The palette is the JIC Smart Factory brand's (docs/design-decisions.md, "The palette is the JIC Smart Factory
# brand's, one purple, measured on the frames"): its purple #640ABA, grey-lilac #E1DCE6 and periwinkle #C2C9FF, and
# from the wider JIC palette in the same guide its orange-red #FF6540, amber #FFC226 and green #3DBE4C. Where a guide
# colour is too light for text, its text twin is derived in the colour's own LCh hue at the lightness that clears
# 4.5:1 on the grey-lilac (6.2:1 on white). The guide's yellow #FFEF85 is decoration and appears nowhere here.
#
# Surface and text tokens: purple text on white, separated by thin grey-lilac rules.
#   Unit [string] (hex colour)
CONST_BG            = '#FFFFFF'   # page background
CONST_CARD          = '#FFFFFF'   # card fill
CONST_CARD_BORDER   = '#E1DCE6'   # the brand's grey-lilac: card outlines
CONST_INK           = '#640ABA'   # the brand purple: all text, outlines, the selected segment, the OK verdict
CONST_INK_SOFT      = CONST_INK   # secondary text: one purple, hierarchy by size and weight as in the guide
CONST_INK_MUTE      = '#6F5783'   # muted purple-grey: labels, empty states, timestamps, the Trends total
CONST_LINE          = '#E1DCE6'   # dividers
# CONST_INK_MUTE is text, so it clears 4.5:1 on every ground it is set on: 6.24:1 on white, 4.63:1 on the
# grey-lilac (the control hover). It is the purple's hue at chroma 28 and L* 41.

CONST_BRAND         = CONST_INK   # the architecture diagram's group tags

# The interactive-control tokens (segmented controls, tool buttons). A control state is ALWAYS
# a (background, label) PAIR: a state rule that moves the background without naming the label
# lets another rule's label colour leak onto it — a hovered SELECTED segment once kept the
# checked white label on the unselected hover fill (~1.1:1). Every pair is >= 4.5:1, pinned in
# test/UI/test_control_contrast.py by measuring the rendered pixels. Buttons are outlined, as the guide's
# are: a plain one in a 1 px purple rule, the primary (ANALYZE) in a 2 px one; a hovered plain button fills
# grey-lilac (purple on it 6.79:1), a pressed one periwinkle (5.71:1); the selected segment and a hovered or
# pressed primary fill purple under a white label (9.15:1). One purple: the hover of a filled control does not
# shift its colour.
#   Unit [string] (hex colour)
CONST_CONTROL_BORDER          = CONST_INK  # resting outline of an unselected segment / plain button
CONST_CONTROL_HOVER           = '#E1DCE6'  # unselected hover fill; the label stays CONST_INK
CONST_CONTROL_HOVER_BORDER    = CONST_INK  # plain-button outline under the cursor
CONST_CONTROL_PRESSED         = '#C2C9FF'  # plain-button pressed fill: the brand's periwinkle; the label stays CONST_INK
CONST_INK_HOVER               = CONST_INK  # selected / primary hover fill
CONST_INK_PRESSED             = CONST_INK  # primary pressed fill
CONST_ON_INK                  = '#FFFFFF'  # the label on any purple fill
# Disabled states are EXEMPT from the 4.5:1 text floor: their low contrast is what says 'not
# available'. They are held instead to looking different from enabled (ΔE76 >= 12 in label or
# fill) — see CONST_EXEMPT_STATES in test/UI/test_control_contrast.py.
CONST_CONTROL_DISABLED_TEXT   = '#B4A6BE'  # label of a disabled control (2.30:1 on white): the purple's hue, L* 70
CONST_CONTROL_DISABLED_BORDER = CONST_LINE # the outline fades to the divider tone
CONST_PRIMARY_DISABLED_FILL   = CONST_CARD # a disabled ANALYZE stays outlined, on the card
CONST_PRIMARY_DISABLED_TEXT   = CONST_CONTROL_DISABLED_TEXT

# The scrim laid over the window behind a modal dialog: the purple at low opacity, so the window
# recedes without going dark and the dialog reads as the one thing to act on.
#   Unit [string] (hex colour) / [float] (opacity 0..1)
CONST_SCRIM       = CONST_INK
CONST_SCRIM_ALPHA = 0.16
# The busy overlay laid over the Live view while a frame is analysed: the scrim's purple, far heavier
# (the frame underneath is being worked on, not merely in the background), a white spinner head
# and status text, and the spinner's track in white at low opacity.
#   Unit [string] (hex colour) / [float] (opacity 0..1)
CONST_BUSY_SCRIM       = CONST_INK
CONST_BUSY_SCRIM_ALPHA = 0.62
CONST_BUSY_INK         = '#FFFFFF'
CONST_BUSY_TRACK       = '#FFFFFF'
CONST_BUSY_TRACK_ALPHA = 0.157
# The highlight over the selected object on a History thumbnail: a white outline and a faint white
# wash, readable on any frame (0.176 -> 45 of 255).
#   Unit [string] (hex colour) / [float] (opacity 0..1)
CONST_THUMB_HIGHLIGHT            = '#FFFFFF'
CONST_THUMB_HIGHLIGHT_FILL_ALPHA = 0.176
# The handle of a scroll bar (the reading card, the Log, History's panels): the brand's periwinkle.
#   Unit [string] (hex colour)
CONST_SCROLLBAR_HANDLE = '#C2C9FF'
# The vertical rule in the top bar between the AnyScan and JIC Smart Factory logos, as on the poster.
#   Unit [string] (hex colour)
CONST_TOPBAR_DIVIDER = CONST_LINE
# The logo's one colour: the fill of the delivered, outlined logo (images/anyscan-logo.svg), the JIC Smart Factory
# purple, which the top bar's live tagline is set in so it matches the outlined wordmark beside it.
#   Unit [string] (hex colour)
CONST_LOGO_INK      = '#640ABA'

# The status colours: system health (the camera, the models, the system cell) and the Log's severities. Green
# (JIC #3DBE4C) means connected and ready, amber (JIC #FFC226) degraded; both are too light for a dot on white
# (2.42:1 and 1.62:1), so each is used as a dot in its hue at L* 60.5 (3.1:1, the 3:1 graphic floor) and as words
# in its hue at L* 41 (6.2:1). Green never marks an object: on the green table it would sit 28 degrees of hue from
# the surface (docs/design-decisions.md).
#   Unit [string] (hex colour)
CONST_OK            = '#1EA838'   # connected, ready
CONST_OK_INK        = '#00711B'
CONST_OK_BORDER     = '#3DBE4C'   # the JIC green: a pill's outline
CONST_WARN          = '#B98B00'   # degraded but working
CONST_WARN_INK      = '#7C5B00'
CONST_WARN_BORDER   = '#FFC226'   # the JIC amber: a pill's outline

# The text colour of a status colour. CONST_OK and CONST_WARN are dots, not words: a status word is drawn in the
# colour's _INK twin while its dot keeps the dot colour. Every other colour is its own text colour.
#   Unit [Dict<string, string>]
CONST_STATUS_TEXT_COLORS = {CONST_OK: CONST_OK_INK, CONST_WARN: CONST_WARN_INK}

# The viewport (the Camera View's ground, History's thumbnails): the brand's grey-lilac, light as the rest; the
# frame fills it and its marks never depend on it. Its text is the purple (6.79:1); error text on it is the Log's
# error colour (4.61:1).
#   Unit [string] (hex colour)
CONST_VIEWPORT      = '#E1DCE6'
CONST_VIEWPORT_TEXT = CONST_INK

# The funding band (at the foot of the window, and the architecture diagram's band): the purple, carrying the white
# institutional logos, white rules, the window's pixel motif in white, and the diagram's disclaimer in white (9.15:1).
#   Unit [string] (hex colour)
CONST_BAND          = CONST_INK
CONST_BAND_LINE     = '#FFFFFF'
CONST_BAND_TEXT     = '#FFFFFF'
# The band's rules and the diagram's disclaimer are white at an opacity, so the rules are a whisper and the
# disclaimer stays secondary to the logos (the logos are solid white).
#   Unit [float] (0..1)
CONST_BAND_LINE_ALPHA = 0.20
CONST_BAND_TEXT_ALPHA = 0.76
# The poster's pixel cluster, painted in the empty Camera View's top-right corner (docs/design-decisions.md, "The
# empty Camera View carries the poster's pixel cluster"): tone on tone, as the funding band's white squares are on the
# purple, the purple at two low opacities on the view's grey-lilac, so the squares read as a texture in its own hue.
# Decoration only.
#   Unit [string] (hex colour), [float] (0..1)
CONST_CORNER_MOTIF = CONST_INK
CONST_CORNER_MOTIF_ALPHA = (0.07, 0.12)

# The label-mask FILL floors. They live here, not in the renderer, because Theme DERIVES the
# neutral fill from them (Neutral_Mask_Colors) and the parameters layer must not import the vision
# layer. They are stricter than the general distinctness floor because a thin box outline must
# stand out against the fill it crosses, and the fill must actually be a colour:
#   - ΔE(box, fill) >= 25: the outline stays clearly visible against its own fill;
#   - ΔE(fill, white) >= 21: the fill does not read as white (see the note on the constant);
#   - >= 4.5:1 against the black mask ground (WCAG relative luminance): the silhouette reads;
#   - a chromatic fill keeps its box's hue (within 5°) at >= 40% of the box's chroma;
#   - a DERIVED fill sits at least 0.5 L* inside its valid window on both sides, so rounding to
#     hex (about 0.2 L*) can never push it across a floor.
#   Unit [float]
CONST_MASK_FILL_MIN_BOX_DELTA_E = 25.0
# The fill/white floor exists for ONE failure: a mask fill that reads as white. That failure was
# #F1F2F4, ΔE 4.7 from white — effectively white. 21 is a chosen margin above it, not a
# measurement limit: at 21 a near-neutral fill can reach L* ~80 and still reads clearly as grey
# (checked by eye on the previous test set's Image_001, eb00508^), while L* 85 (ΔE ~16 from white) starts drifting back toward the white it
# replaced. It was 25 for one round; 25 capped the neutral fill at L* ~75, which read darker than
# intended. Do not round it back up to 25 without re-checking the neutral mask: every point above
# 21 costs neutral fill lightness (L* <= 100 - sqrt(floor² - C*²)).
CONST_MASK_FILL_MIN_WHITE_DELTA_E = 21.0
CONST_MASK_FILL_MIN_GROUND_CONTRAST = 4.5
# The chromatic-fill floors (hue within 5° of the box, >= 40% of its chroma). No derivation code
# reads these two — they are the CONTRACT every verdict fill must meet, enforced by
# test/Parameters/test_theme.py::test_label_mask_fill_is_a_visible_tint_of_its_box. They stay here,
# beside the floors the derivation does read, so the constraint never drifts away from the colours
# it constrains (the neutral fill once drifted toward white with no floor beside it).
CONST_MASK_FILL_MAX_HUE_SHIFT = 5.0
CONST_MASK_FILL_MIN_CHROMA_FRACTION = 0.4
CONST_MASK_FILL_WINDOW_MARGIN = 0.5

# The per-object VERDICT colours, as (box, ink, fill) triples. The box is the stroke drawn on the frame, the
# object's chip and the mask contour; the ink is its twin for verdict text on the white card; the fill is the
# label-mask tint. These DRIVE the object rendering in both views (via Verdict_Color).
#
#   OK is the brand purple, #640ABA, as the poster marks a detected part; its ink is the same purple (9.15:1 on
#   white). NOK is the JIC orange-red #FF6540, as the poster marks a defect; its ink is its hue at L* 41 (6.23:1).
#   Warning (not the catalogue part, 2026-10-11) is the JIC amber #FFC226 with its ink at L* 41 (6.26:1).
#   UNSPECIFIED (probably several parts, not judged) is the neutral detection colour, assembled at the end of this
#   module (CONST_DETECTION_COLORS); on the label mask its outline is the mask's own darker neutral.
#
#   Measured on the test frames (2026-10-14; per-pixel WCAG ratio, median, against the surfaces under the marks:
#   the table L* 38, bright aluminium 66, the dark rusted plate 25, rust-stained metal 61):
#       OK       table 1.3  aluminium 3.5  dark plate 1.3  rust-stained 3.0   (reads on the table by hue, ΔE 119)
#       NOK      table 2.4  aluminium 1.2  dark plate 3.9  rust-stained 1.2   (reads on metal by hue, ΔE 76)
#       Warning  table 4.3  aluminium 1.6  dark plate 7.0  rust-stained 1.9
#   No single colour can reach 3:1 against both the dark plate and the aluminium (it would need relative
#   luminance >= 0.227 and <= 0.085). An outline under the marks lifts them on bright metal (to 3.5:1 in this
#   purple); the owner chose by eye, from renders of these frames, to draw none (docs/design-decisions.md).
#   The four boxes are >= ΔE 44 apart (NOK-Warning ΔE 27 under deuteranopia, where the words and the chips'
#   numerals carry the difference).
#
#   The FILL is a tint of the box in its own hue (within 5°, at >= 40 % of its chroma), so silhouette and contour
#   read as one object, built in LCh at L* 56-72 against the CONST_MASK_FILL_* floors:
#       OK       #CC9EF1  ΔE(box, fill) 63.5  ΔE(fill, white) 55.4  9.7:1 on black
#       NOK      #CD7157  ΔE(box, fill) 30.8  ΔE(fill, white) 62.2  6.1:1 on black
#       Warning  #B28508  ΔE(box, fill) 28.3  ΔE(fill, white) 75.3  6.3:1 on black
#   The boxes are light (but OK), so the fills sit below them, not above: a fill lighter than a light box would
#   read as white.
#   Unit [string] (hex colour) / [Dict<string, Tuple<string> 1x3>] (box, ink, fill)
CONST_NOK_BOX = '#FF6540'
CONST_WARNING_BOX = '#FFC226'
CONST_VERDICT_COLORS = {
    'OK':  (CONST_INK, CONST_INK, '#CC9EF1'),              # pass
    'NOK': (CONST_NOK_BOX, '#BA260B', '#CD7157'),          # fail
    'Warning': (CONST_WARNING_BOX, CONST_WARN_INK, '#B28508'),   # not the catalogue part
}
# The verdict a detection carries until classification sets one.
#   Unit [string]
CONST_VERDICT_DEFAULT = 'OK'

# The ground a verdict's WORDS sit on (the status badge, the diagram's verdict labels): the box colour where the
# purple reads at >= 4.5:1 on it (Warning 5.66:1, Unspecified 6.79:1), else the poster's tint of it: the part
# tag's periwinkle for OK (the purple box under purple words would be one colour; 5.71:1) and the defect tag's
# #FFD9D0 for NOK (7.01:1; the purple on the solid orange-red is 3.13:1).
#   Unit [string] (hex colour)
CONST_OK_LABEL_GROUND = '#C2C9FF'
CONST_NOK_LABEL_GROUND = '#FFD9D0'

# The numeral on a chip on the frame (an object's and a feature's), filled with its verdict's box as on the poster:
# white on the solid purple (9.15:1) and on the solid orange-red (2.92:1: the owner's deliberate exception for these
# short bold numerals, the only text below 4.5:1, docs/design-decisions.md), the purple on Warning's amber (5.66:1)
# and on the neutral (6.79:1). Keyed by the chip's colour, so a detect-only run's neutral chip reads the same.
#   Unit [string] (hex colour)
CONST_CHIP_NUMERAL_ON_DARK = '#FFFFFF'

# The NEUTRAL object colour, used when a configuration only DETECTS and does not classify
# (Configuration_Str.Classifies is false: it is not a catalogue mode), and for Unspecified: every object is drawn in
# this one colour, because there is no pass/fail to encode. It is the brand's grey-lilac, near-achromatic (chroma
# 5.5), far from the purple OK (ΔE 107) and the loud NOK (ΔE 80), so a judged set and an unjudged one never share a
# hue. Drawn into the frame, it is measured against the real surfaces at the project's distinctness floor (ΔE 12):
# ΔE 22 against bright aluminium (its worst case, grey on grey), 35 against the bright steel of the previous set,
# 60 against the table, 64 against the dark plate. Its ink, the purple's hue at chroma 10 and L* 41, is for text on
# the white card (6.22:1).
#
# THE LABEL MASK USES ITS OWN, DERIVED NEUTRAL PAIR — outline and fill — not this box: on the mask the outline only
# sits on the fill and on black, so it can be darker, which frees the fill to go light. Neutral_Mask_Colors derives
# the pair in this box's own hue and chroma:
#     fill     L* 79.09 (#C7C2CC) — as light as the fill/white floor allows: for chroma C*, ΔE to white >= 21 needs
#                                   L* <= 100 - sqrt(21² - C*²) = 79.74, less the 0.5 margin. The floor is 21, not
#                                   25, on purpose — see CONST_MASK_FILL_MIN_WHITE_DELTA_E;
#     outline  L* 51.52 (#7E7982) — the midpoint of [48.88 (4.5:1 against the black ground), fill L* - 25];
#     measured ΔE(outline, fill) 27.6, ΔE(fill, white) 21.7, fill 12.0:1 and outline 4.9:1 on black.
# The window closes only if the FLOORS change (not the box), and then Theme raises at import naming it.
#   Unit [string] (hex colour)
CONST_DETECTION_BOX = '#E1DCE6'
CONST_DETECTION_INK = '#655E6D'
# CONST_DETECTION_COLORS — the (box, ink, fill) triple — is assembled at the END of this module,
# once Neutral_Mask_Colors (which needs the colour-space helpers below) is defined.

# The Log-view severity text colours, one named semantic token per level. The log view colours the level field and
# the message by these (the timestamp stays muted); a level colour is NEVER a literal at the call site. INFO is the
# purple; WARNING the amber's text twin; ERROR the JIC pink's hue at L* 41 (6.22:1 on white, 4.61:1 on the
# grey-lilac viewport, where a failed set's thumbnail says so).
#
#   NOTE on CONST_LOG_ERROR vs the NOK orange-red: the log ERROR colour is DELIBERATELY not the NOK verdict's. NOK
#   means "this part is faulty"; a log ERROR means "the application failed". Painting them the same colour would
#   conflate an inspection result with a software fault, so errors take the pink family and defects the orange
#   (ΔE 55 between the error colour and the NOK box). Do NOT unify them.
#   Unit [string] (hex colour)
CONST_LOG_INFO    = CONST_INK
CONST_LOG_WARNING = CONST_WARN_INK
CONST_LOG_ERROR   = '#BE0362'

# The severity-to-colour mapping the log view reads, from the tokens above — keyed by the
# Logger's level strings, with INFO the fallback for an unknown level so a line always
# renders. Qt-free and pure, so the mapping is unit-testable without a widget.
#   Unit [Dict<string, string>]
CONST_LOG_LEVEL_COLORS = {'INFO': CONST_LOG_INFO, 'WARNING': CONST_LOG_WARNING,
                          'ERROR': CONST_LOG_ERROR}


def Log_Level_Color(level: str) -> str:
    """
    Description:
        The text colour for a log severity level, from the one CONST_LOG_LEVEL_COLORS
        mapping — the log view reads this, never a colour literal at the call site. An
        unknown or empty level falls back to the INFO colour, so a line always renders.

    Args:
        (1) level [string]: The severity level ('INFO', 'WARNING' or 'ERROR').

    Returns:
        (1) parameter [string]: The token hex colour for that level.
    """

    return CONST_LOG_LEVEL_COLORS.get(level, CONST_LOG_INFO)


def Status_Text_Color(color: str) -> str:
    """
    Description:
        The colour a status word is drawn in for a status colour: the _INK twin of CONST_OK and
        CONST_WARN (from CONST_STATUS_TEXT_COLORS), every other colour unchanged. The widgets that put
        a status colour on words read this, so a call site passes the status colour itself.

    Args:
        (1) color [string]: The status colour token.

    Returns:
        (1) parameter [string]: The token to draw the words in.
    """

    return CONST_STATUS_TEXT_COLORS.get(color, color)

def Hex_To_Rgb(hex_color: str) -> tp.Tuple[int, int, int]:
    """
    Description:
        A '#rrggbb' string as an (R, G, B) tuple of 0..255 integers.

    Args:
        (1) hex_color [string]: The colour as '#rrggbb'.

    Returns:
        (1) parameter [Vector<int> 1x3]: The colour as (R, G, B).
    """

    value = hex_color.lstrip('#')
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def Hex_To_Bgr(hex_color: str) -> tp.Tuple[int, int, int]:
    """
    Description:
        A '#rrggbb' string as a (B, G, R) tuple, the channel order OpenCV draws in.

    Args:
        (1) hex_color [string]: The colour as '#rrggbb'.

    Returns:
        (1) parameter [Vector<int> 1x3]: The colour as (B, G, R).
    """

    r, g, b = Hex_To_Rgb(hex_color)
    return (b, g, r)


def __Srgb_Linear(channel: float) -> float:
    """
    Description:
        Undo the sRGB gamma for one 0..255 channel, giving linear light 0..1 — the step both the
        L*a*b* conversion and the WCAG relative luminance start from.

    Args:
        (1) channel [float]: The channel value (0..255).

    Returns:
        (1) parameter [float]: The linear-light value (0..1).
    """

    channel /= 255.0
    return ((channel + 0.055) / 1.055) ** 2.4 if channel > 0.04045 else channel / 12.92


def __Lab_F(t: float) -> float:
    """
    Description:
        The CIELAB nonlinearity applied to a normalised XYZ component (L*a*b* from XYZ, and the L*
        of a given relative luminance).

    Args:
        (1) t [float]: The normalised component.

    Returns:
        (1) parameter [float]: The transformed component.
    """

    return t ** (1.0 / 3.0) if t > 0.008856 else 7.787 * t + 16.0 / 116.0


def __Lab(hex_color: str) -> tp.Tuple[float, float, float]:
    """
    Description:
        A colour as CIE L*a*b* (D65), the space perceptual distance is measured in.

    Args:
        (1) hex_color [string]: The colour as '#rrggbb'.

    Returns:
        (1) parameter [Vector<float> 1x3]: The (L, a, b) coordinates.
    """

    r, g, b = (__Srgb_Linear(c) for c in Hex_To_Rgb(hex_color))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = (0.2126 * r + 0.7152 * g + 0.0722 * b)
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    fx, fy, fz = __Lab_F(x), __Lab_F(y), __Lab_F(z)
    return (116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz))


def Delta_E(hex_a: str, hex_b: str) -> float:
    """
    Description:
        The CIE76 perceptual distance (ΔE) between two colours — the Euclidean distance
        in L*a*b*, which tracks the eye far better than an RGB distance. A ΔE below ~10
        is hard to tell apart; the palette and the rendered strokes are kept well above
        that so no two objects read as the same colour.

    Args:
        (1) hex_a [string]: The first colour as '#rrggbb'.
        (2) hex_b [string]: The second colour as '#rrggbb'.

    Returns:
        (1) parameter [float]: The ΔE76 distance.
    """

    la, aa, ba = __Lab(hex_a)
    lb, ab, bb = __Lab(hex_b)
    return ((la - lb) ** 2 + (aa - ab) ** 2 + (ba - bb) ** 2) ** 0.5


def Lch_Of(hex_color: str) -> tp.Tuple[float, float, float]:
    """
    Description:
        A colour as CIE LCh (D65): lightness, chroma and hue angle in degrees — the space the
        mask fills are built and checked in (hue held, lightness and chroma moved).

    Args:
        (1) hex_color [string]: The colour as '#rrggbb'.

    Returns:
        (1) parameter [Tuple<float> 1x3]: (L*, C*, h in degrees 0..360).
    """

    lightness, a, b = __Lab(hex_color)
    return (lightness, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360.0)


def Relative_Luminance(hex_color: str) -> float:
    """
    Description:
        The WCAG relative luminance of a colour: each sRGB channel is linearised (the gamma
        undone), then weighted by the eye's sensitivity to it.

    Args:
        (1) hex_color [string]: The colour as '#rrggbb'.

    Returns:
        (1) parameter [float]: The relative luminance (0 = black .. 1 = white).
    """

    r, g, b = (__Srgb_Linear(c) for c in Hex_To_Rgb(hex_color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def Contrast_Ratio(hex_a: str, hex_b: str) -> float:
    """
    Description:
        The WCAG contrast ratio between two colours — (L_light + 0.05) / (L_dark + 0.05) of their
        relative luminances. Order does not matter. 4.5:1 is the WCAG AA floor for body text,
        the floor every enabled control state is held to.

    Args:
        (1) hex_a [string]: The first colour as '#rrggbb'.
        (2) hex_b [string]: The second colour as '#rrggbb'.

    Returns:
        (1) parameter [float]: The contrast ratio (1.0 .. 21.0).
    """

    l_a = Relative_Luminance(hex_a); l_b = Relative_Luminance(hex_b)
    return (max(l_a, l_b) + 0.05) / (min(l_a, l_b) + 0.05)


def Ground_Contrast(hex_color: str) -> float:
    """
    Description:
        The contrast ratio of a colour against the black label-mask ground, from its WCAG
        relative luminance (linear light) — how clearly a fill reads as light on black.

    Args:
        (1) hex_color [string]: The colour as '#rrggbb'.

    Returns:
        (1) parameter [float]: The contrast ratio (>= 1.0).
    """

    return Contrast_Ratio(hex_color, '#000000')


def __Lab_To_Hex(lightness: float, a: float, b: float) -> str:
    """
    Description:
        The inverse of __Lab: a CIE L*a*b* (D65) colour as '#rrggbb', each channel clamped to the
        sRGB gamut and rounded.

    Args:
        (1) lightness [float]: L*.
        (2) a [float]: a*.
        (3) b [float]: b*.

    Returns:
        (1) parameter [string]: The colour as '#rrggbb'.
    """

    def _Inverse_F(t: float) -> float:
        """
        Description:
            The inverse CIELAB nonlinearity.

        Args:
            (1) t [float]: The transformed component.

        Returns:
            (1) parameter [float]: The normalised XYZ component.
        """

        return t ** 3 if t ** 3 > 0.008856 else (t - 16.0 / 116.0) / 7.787

    def _Encode(channel: float) -> int:
        """
        Description:
            Linear light 0..1 to an sRGB 0..255 channel, clamped to the gamut.

        Args:
            (1) channel [float]: The linear-light value.

        Returns:
            (1) parameter [int]: The channel value (0..255).
        """

        channel = min(1.0, max(0.0, channel))
        encoded = 12.92 * channel if channel <= 0.0031308 else 1.055 * channel ** (1.0 / 2.4) - 0.055
        return int(round(encoded * 255.0))

    fy = (lightness + 16.0) / 116.0
    x = _Inverse_F(fy + a / 500.0) * 0.95047
    y = _Inverse_F(fy)
    z = _Inverse_F(fy - b / 200.0) * 1.08883
    red = 3.2406 * x - 1.5372 * y - 0.4986 * z
    green = -0.9689 * x + 1.8758 * y + 0.0415 * z
    blue = 0.0557 * x - 0.2040 * y + 1.0570 * z
    return '#%02X%02X%02X' % (_Encode(red), _Encode(green), _Encode(blue))


def Neutral_Mask_Bounds(box_hex: str) -> tp.Tuple[float, float]:
    """
    Description:
        The two fixed bounds of the neutral label-mask pair, for a near-achromatic colour's hue
        and chroma: the darkest outline that still reads on the black ground (the L* whose relative
        luminance gives exactly the minimum ground contrast), and the lightest fill that is still
        clearly not white (ΔE to white = sqrt((100 - L*)² + C*²) >= the white floor, so
        L* <= 100 - sqrt(floor² - C*²)). Neither depends on the box's lightness.

    Args:
        (1) box_hex [string]: The neutral box colour as '#rrggbb' (its hue and chroma are used).

    Returns:
        (1) parameter [Tuple<float> 1x2]: (outline lower L*, fill upper L*).
    """

    y_min = CONST_MASK_FILL_MIN_GROUND_CONTRAST * 0.05 - 0.05
    f_min = __Lab_F(y_min)
    outline_lower = 116.0 * f_min - 16.0
    chroma = Lch_Of(box_hex)[1]
    white_floor = CONST_MASK_FILL_MIN_WHITE_DELTA_E
    fill_upper = 100.0 - math.sqrt(max(0.0, white_floor ** 2 - chroma ** 2))
    return (outline_lower, fill_upper)


def Neutral_Mask_Colors(box_hex: str) -> tp.Tuple[str, str]:
    """
    Description:
        The label mask's neutral (outline, fill) pair, DERIVED in the box's own hue and chroma so
        it cannot drift: the fill as LIGHT as the fill/white floor allows (its upper bound less the
        margin), and the outline at the midpoint of its window — no darker than reads on the black
        ground, no lighter than the fill minus the outline/fill floor. It fails LOUDLY — ValueError,
        raised at import for the shipped tokens — when that window is narrower than twice the
        margin, or when a rounded hex misses any floor; it never clamps to a pair that breaks one.

    Args:
        (1) box_hex [string]: The neutral box colour as '#rrggbb'.

    Returns:
        (1) parameter [Tuple<string> 1x2]: The (mask outline, mask fill) colours as '#rrggbb'.
    """

    outline_lower, fill_upper = Neutral_Mask_Bounds(box_hex)
    margin = CONST_MASK_FILL_WINDOW_MARGIN
    fill_l = fill_upper - margin
    outline_upper = fill_l - CONST_MASK_FILL_MIN_BOX_DELTA_E
    if outline_upper - outline_lower < 2.0 * margin:
        raise ValueError('No valid neutral mask pair for box %s: the outline L* window '
                         '[%.2f, %.2f] is narrower than 2 x %.1f. With the fill at L* %.2f (the '
                         'lightest that stays dE %.0f from white), the outline must be dE %.0f '
                         'below it yet keep %.1f:1 against the black ground.'
                         % (box_hex, outline_lower, outline_upper, margin, fill_l,
                            CONST_MASK_FILL_MIN_WHITE_DELTA_E, CONST_MASK_FILL_MIN_BOX_DELTA_E,
                            CONST_MASK_FILL_MIN_GROUND_CONTRAST))
    _lightness, a, b = __Lab(box_hex)
    fill = __Lab_To_Hex(fill_l, a, b)
    outline = __Lab_To_Hex((outline_lower + outline_upper) / 2.0, a, b)
    if (Delta_E(outline, fill) < CONST_MASK_FILL_MIN_BOX_DELTA_E
            or Delta_E(fill, '#FFFFFF') < CONST_MASK_FILL_MIN_WHITE_DELTA_E
            or Ground_Contrast(fill) < CONST_MASK_FILL_MIN_GROUND_CONTRAST
            or Ground_Contrast(outline) < CONST_MASK_FILL_MIN_GROUND_CONTRAST):
        raise ValueError('The derived neutral mask pair (%s, %s) for box %s misses a floor after '
                         'rounding.' % (outline, fill, box_hex))
    return (outline, fill)


def Verdict_Color(verdict: str) -> tp.Tuple[str, str, str]:
    """
    Description:
        The (box, ink, fill) colour triple for a per-object verdict, from the ONE
        CONST_VERDICT_COLORS definition — the object rendering reads this, never a colour
        literal at the call site, so the pass/fail colours are changed in one place. An
        unknown or empty verdict falls back to the default (OK), so a detection carrying
        no verdict still renders. The fill is the light label-mask tint of the box.

    Args:
        (1) verdict [string]: The verdict key ('OK', 'NOK', 'Unspecified' or 'Warning').

    Returns:
        (1) parameter [Tuple<string> 1x3]: The (box, ink, fill) hex colours.
    """

    return CONST_VERDICT_COLORS.get(verdict, CONST_VERDICT_COLORS[CONST_VERDICT_DEFAULT])


def Mask_Outline_Color(verdict: str) -> str:
    """
    Description:
        The outline a judged object takes on the LABEL MASK: its verdict box, except for a verdict drawn
        in the neutral colour (Unspecified), which takes the mask's own darker neutral outline — the
        neutral box would all but vanish on the neutral fill (Detection_Mask_Outline).

    Args:
        (1) verdict [string]: The verdict.

    Returns:
        (1) parameter [string]: The outline colour as '#rrggbb'.
    """

    box = Verdict_Color(verdict)[0]
    return Detection_Mask_Outline() if box == CONST_DETECTION_BOX else box


def Chip_Numeral_Color(chip_hex: str) -> str:
    """
    Description:
        The numeral colour on a chip filled with a box colour: CONST_CHIP_NUMERAL_ON_DARK on the OK purple, on the NOK
        orange-red (the owner's exception, 2.92:1) and on the label mask's darker neutral outline (4.2:1, white as it
        was there before the brand palette; the purple would be 2.1:1), the purple on Warning's amber and the
        neutral box.

    Args:
        (1) chip_hex [string]: The chip's colour as '#rrggbb'.

    Returns:
        (1) parameter [string]: The numeral colour.
    """

    dark = {CONST_VERDICT_COLORS['OK'][0].lower(), CONST_VERDICT_COLORS['NOK'][0].lower(), Detection_Mask_Outline().lower()}
    return CONST_CHIP_NUMERAL_ON_DARK if chip_hex.lower() in dark else CONST_INK


def Label_Ground(verdict: str) -> str:
    """
    Description:
        The ground a verdict's words sit on (the status badge, the diagram's verdict labels): the poster's tint for OK
        and NOK, the box colour for the others, where the purple words clear 4.5:1.

    Args:
        (1) verdict [string]: The verdict.

    Returns:
        (1) parameter [string]: The ground colour as '#rrggbb'.
    """

    return {'OK': CONST_OK_LABEL_GROUND, 'NOK': CONST_NOK_LABEL_GROUND}.get(verdict, Verdict_Color(verdict)[0])


def Detection_Color() -> tp.Tuple[str, str, str]:
    """
    Description:
        The (box, ink, fill) colour triple for a plain, unjudged detection — used when the
        configuration only detects (classification off), so every object is one neutral colour.
        From the ONE CONST_DETECTION_COLORS definition, a distinct token from the verdict colours
        ('detected, not judged', never a pass/fail). The fill is the label mask's neutral fill,
        DERIVED with its own darker outline (Neutral_Mask_Colors, Detection_Mask_Outline), never
        hand-set.

    Returns:
        (1) parameter [Tuple<string> 1x3]: The (box, ink, fill) hex colours.
    """

    return CONST_DETECTION_COLORS


def Detection_Mask_Outline() -> str:
    """
    Description:
        The neutral OUTLINE for the label mask — a darker shade of the neutral than the frame's box
        (Detection_Color()[0]), derived with the mask fill by Neutral_Mask_Colors. On the mask the
        outline only sits on the fill and on black, so it can be dark enough to leave the fill
        light; the frame's box keeps its own lightness for the table and the parts.

    Returns:
        (1) parameter [string]: The mask outline colour as '#rrggbb'.
    """

    return CONST_DETECTION_MASK_OUTLINE


# The neutral label-mask pair and the (box, ink, fill) triple, assembled here because the pair is
# DERIVED by Neutral_Mask_Colors (defined above). A pair that cannot clear every floor raises at
# import — loudly — instead of shipping a mask that breaks one.
#   Unit [string] (hex colour) / [Tuple<string> 1x3] (box, ink, fill)
CONST_DETECTION_MASK_OUTLINE, CONST_DETECTION_MASK_FILL = Neutral_Mask_Colors(CONST_DETECTION_BOX)
CONST_DETECTION_COLORS = (CONST_DETECTION_BOX, CONST_DETECTION_INK, CONST_DETECTION_MASK_FILL)
# Unspecified is not judged, so it takes the neutral colour (see CONST_VERDICT_COLORS).
CONST_VERDICT_COLORS['Unspecified'] = CONST_DETECTION_COLORS
# The Camera View's heatmap colours: cividis (Nuñez, Anderton & Renslow, 2018), 17 anchors taken from
# matplotlib's map at equal steps and expanded to 256 colours in L*a*b* (Heatmap_Colors). Cividis, not
# viridis: viridis passed ΔE 4.2 from the previous OK verdict's ink and 12.0 from the previous status green;
# cividis has no green, red or magenta, keeps every colour >= ΔE 12 (CONST_ANNOTATE_MIN_DELTA_E) from the verdict,
# status and log colours — the closest, 25.0, is the status amber's dot (12.5, from the previous indigo OK ink,
# before the JIC Smart Factory palette) — and is built for colour-vision deficiency. Its high end is a yellow
# that is a data scale, not the guide's decorative yellow and not a status. Its
# lightness rises from L* 13.8 to 91.3, so a hotter pixel always reads lighter. The expansion differs from
# matplotlib's map by up to ΔE 4.1; the tests pin the properties of THIS map, not that fidelity
# (test/Parameters/test_theme.py).
#   Unit [Tuple<string>] (hex colour)
CONST_HEATMAP_ANCHORS = ('#00224e', '#002e6a', '#1a386f', '#32436d', '#434e6c', '#535a6d', '#61656f', '#6f7073',
                         '#7d7c78', '#8b8778', '#9a9376', '#aaa073', '#bbad6d', '#ccba64', '#ddc858', '#efd748',
                         '#fee838')
# The number of colours the heatmap is drawn in: one per grey level of an 8-bit lookup table.
#   Unit [int]
CONST_HEATMAP_SIZE = 256


def Heatmap_Colors() -> tp.List[str]:
    """
    Description:
        The heatmap's CONST_HEATMAP_SIZE colours, low to high: CONST_HEATMAP_ANCHORS at equal steps,
        interpolated linearly in L*a*b* between neighbours (in RGB the map's dark end bends and the
        steps go uneven), and rounded to hex.

    Returns:
        (1) parameter [Vector<string>]: The colours (hex), the first for the scale's low end.
    """

    anchors = [__Lab(color) for color in CONST_HEATMAP_ANCHORS]
    spans = len(anchors) - 1
    colors = []
    for index in range(CONST_HEATMAP_SIZE):
        position = index * spans / (CONST_HEATMAP_SIZE - 1)
        low = min(int(position), spans - 1)
        t = position - low
        colors.append(__Lab_To_Hex(*(a + (b - a) * t for a, b in zip(anchors[low], anchors[low + 1]))))
    return colors
