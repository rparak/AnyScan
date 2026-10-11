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
# Surface and text tokens (the :root block of the approved web build, one for one).
#   Unit [string] (hex colour)
CONST_BG            = '#f4f3f7'   # page background — faint lavender, not neutral grey
CONST_CARD          = '#ffffff'   # card fill
CONST_CARD_BORDER   = '#e6e4ef'   # violet-tinted card outline
CONST_INK           = '#2b2455'   # deep indigo: primary text, and the primary button
CONST_INK_SOFT      = '#4a4180'   # mid violet: secondary text, object sentences
CONST_INK_MUTE      = '#706a8c'   # desaturated violet-grey: labels, empty states, timestamps
CONST_LINE          = '#ecebf2'   # violet-tinted dividers
# CONST_INK_MUTE is text, so it clears 4.5:1 on every light ground it is set on: 5.09:1 on the card,
# 4.69:1 on the control hover and 4.60:1 on the page. It was '#8983a6' (3.58:1 on the card, 3.24:1 on the
# page) until 2026-09-29; the new value keeps its LCh hue and chroma and lowers only L* (56.4 -> 46.6).

CONST_BRAND         = '#ff005c'   # EDIH-DIGIMAT magenta: the architecture diagram's labels; NOK repeats it

# The interactive-control tokens (segmented controls, tool buttons). A control state is ALWAYS
# a (background, label) PAIR: a state rule that moves the background without naming the label
# lets another rule's label colour leak onto it — a hovered SELECTED segment once kept the
# checked white label on the unselected hover fill (~1.1:1). Every pair is >= 4.5:1, pinned in
# test/UI/test_control_contrast.py by measuring the rendered pixels.
#   Unit [string] (hex colour)
CONST_CONTROL_BORDER          = '#e3e0ee'  # resting outline of an unselected segment / plain button
CONST_CONTROL_HOVER           = '#f6f5fa'  # unselected hover fill; the label stays CONST_INK
CONST_CONTROL_HOVER_BORDER    = '#d5d1e6'  # plain-button outline under the cursor
CONST_INK_HOVER               = '#3a3270'  # selected / primary hover fill: a slight shift off CONST_INK
CONST_INK_PRESSED             = '#1f1a3f'  # primary pressed fill: a slight shift the other way
CONST_ON_INK                  = '#ffffff'  # the label on any CONST_INK-family fill
# Disabled states are EXEMPT from the 4.5:1 text floor: their low contrast is what says 'not
# available'. They are held instead to looking different from enabled (ΔE76 >= 12 in label or
# fill) — see CONST_EXEMPT_STATES in test/UI/test_control_contrast.py.
CONST_CONTROL_DISABLED_TEXT   = '#b6b2ca'  # label of a disabled segment / plain button (2.06:1 on white)
CONST_CONTROL_DISABLED_BORDER = CONST_LINE # the outline fades to the divider tone
CONST_PRIMARY_DISABLED_FILL   = '#cbc8db'  # disabled primary (ANALYZE) fill
# The disabled primary label is a muted ink, not a near-white: exempt from 4.5:1 means the FILL signals
# 'disabled' (ΔE 68 from enabled), not that the label should vanish. 2.19:1 on the fill reads as muted,
# not active. It was '#f2f1f6' (1.46:1), which was never a chosen pairing. It is the muted ink's value
# before CONST_INK_MUTE was darkened for text contrast, kept so the disabled control looks as it did.
CONST_PRIMARY_DISABLED_TEXT   = '#8983a6'

# The scrim laid over the window behind a modal dialog: the brand ink at low opacity, so the window
# recedes without going dark and the dialog reads as the one thing to act on.
#   Unit [string] (hex colour) / [float] (opacity 0..1)
CONST_SCRIM       = CONST_INK
CONST_SCRIM_ALPHA = 0.16
# The busy overlay laid over the Live view while a frame is analysed: the scrim's ink, far heavier
# (the frame underneath is being worked on, not merely in the background), a near-white spinner head
# and status text, and the spinner's track in white at low opacity. Opacities are chosen to keep the
# overlay's pixels as they were drawn from literals (0.62 -> 158 of 255, 0.157 -> 40).
#   Unit [string] (hex colour) / [float] (opacity 0..1)
CONST_BUSY_SCRIM       = CONST_INK
CONST_BUSY_SCRIM_ALPHA = 0.62
CONST_BUSY_INK         = '#f2f2f3'
CONST_BUSY_TRACK       = '#ffffff'
CONST_BUSY_TRACK_ALPHA = 0.157
# The highlight over the selected object on a History thumbnail: a white outline and a faint white
# wash, readable on any frame (0.176 -> 45 of 255).
#   Unit [string] (hex colour) / [float] (opacity 0..1)
CONST_THUMB_HIGHLIGHT            = '#ffffff'
CONST_THUMB_HIGHLIGHT_FILL_ALPHA = 0.176
# The handle of a scroll bar (the reading card, the Log, History's panels): a quiet violet-grey
# that shows where the view is without competing with the content.
#   Unit [string] (hex colour)
CONST_SCROLLBAR_HANDLE = '#c7c3d9'
# The vertical divider in the top bar between the AnyScan and JIC marks: darker than CONST_LINE, so
# it still reads on the bar.
#   Unit [string] (hex colour)
CONST_TOPBAR_DIVIDER = '#c9c5d8'
# The logo's palette, which the top bar's live wordmark and tagline are set in: the fills of the logo's
# text source (images/source/anyscan-logo-text.svg), value for value. Since 352688d the ink and the
# tagline are the theme's own CONST_INK and CONST_INK_SOFT; the magenta stays the logo's, not CONST_BRAND
# (docs/design-decisions.md, "The logo's palette predates the theme", as corrected 2026-10-03). On
# CONST_BG, the top bar's ground: 12.79:1, 4.65:1 and 8.06:1.
#   Unit [string] (hex colour)
CONST_LOGO_INK      = CONST_INK        # deep indigo: "Any", and the mark's frame and object
CONST_LOGO_MAGENTA  = '#d6006e'        # magenta: "Scan", and the mark's box and description
CONST_LOGO_TAGLINE  = CONST_INK_SOFT   # mid violet: the tagline

# The status colours. Green and red are RESERVED here: they mean pass and fail on the badge, so they
# never appear as an object colour (an OK object is indigo, a NOK one magenta). Amber is the one
# exception, decided 2026-10-11: a Warning object (not the catalogue part, not supposed to be there)
# takes CONST_WARN as its box, the same meaning — something to look at — on the frame as on the badge.
CONST_OK            = '#16a34a'   # connected, pass
CONST_OK_INK        = '#15803d'
CONST_OK_SOFT       = '#f2faf5'
CONST_OK_BORDER     = '#cfe9d8'
CONST_WARN          = '#d97706'   # degraded but working
CONST_WARN_INK      = '#b45309'
CONST_WARN_SOFT     = '#fdf8ef'
CONST_WARN_BORDER   = '#f3e2c3'
# The status badge's FAIL level: a catalogue mode with a NOK object on the surface. The ink is the NOK
# verdict's own ink (CONST_VERDICT_COLORS['NOK'][1]), so the badge and the marks on the frame say NOK in one
# colour (the owner's choice over the log's red); the tint and border are built in that ink's hue at the
# warning badge's lightness and chroma (L* 97.7 / C* 4.9 and L* 90.5 / C* 17.3), clipped to sRGB.
CONST_FAIL_INK      = '#d1004a'
CONST_FAIL_SOFT     = '#FFF5F6'
CONST_FAIL_BORDER   = '#FFD9DB'

# The text colour of a status colour. CONST_OK (3.30:1 on the card) and CONST_WARN (3.19:1) are bright
# enough for a dot or an outline, not for words: a status word is drawn in the colour's _INK twin
# (5.02:1 each) while its dot keeps the bright colour. Every other colour is its own text colour.
#   Unit [Dict<string, string>]
CONST_STATUS_TEXT_COLORS = {CONST_OK: CONST_OK_INK, CONST_WARN: CONST_WARN_INK}

CONST_VIEWPORT      = '#2b2455'   # the one dark surface in the console: the brand indigo
CONST_VIEWPORT_TEXT = '#9b95bd'   # readable lavender-grey on the indigo viewport
# Error text on the indigo viewport (a failed set's History thumbnail). CONST_LOG_ERROR is 2.18:1 there;
# this is its LCh hue at a higher lightness (L* 40.0 -> 61.0, same chroma), 4.61:1 on CONST_VIEWPORT.
CONST_ERROR_ON_DARK = '#fc5e4c'

# The deep-indigo funding band tokens.
CONST_BAND          = '#2b2455'   # deep-indigo funding band
CONST_BAND_LINE     = '#4a4180'   # dividers on the band
CONST_BAND_TEXT     = '#b9b2d6'   # lavender text/disclaimer on the band

# The label-mask FILL floors. They live here, not in the renderer, because Theme DERIVES the
# neutral fill from them (Neutral_Mask_Fill) and the parameters layer must not import the vision
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

# The two per-object VERDICT colours, as (box, ink, fill) triples. The box is the stroke
# drawn on the frame and the mask contour; the ink is the darkened twin for verdict text
# on the white card. These DRIVE the object rendering in both views (via Verdict_Color) —
# every object is drawn in its verdict colour. Until classification lands every object is
# OK, so everything renders in the OK box.
#
#   NOTE on '#ff005c': this is the EDIH-DIGIMAT brand magenta, kept as the NOK marker
#   precisely because it reads as a fail marker at a glance — do NOT swap it for a calmer
#   red; its fail-lookalike quality is the whole reason it belongs here.
#   The OK box '#6C63B5' is a deliberately LIGHTER tint than its ink twin '#4a4180':
#   '#4a4180' alone is too dark to read against the dark rusted plates (the previous test set's
#   Image_003/005, eb00508^; the same plates are in the dark rusted plate frames of
#   Data/Images/Test, e.g. Image_056), so the
#   box carries the lighter value and the ink is reserved for text on the white card.
#
#   The THIRD entry is the label-mask FILL: a tint of the box that is visibly the box's own
#   hue, so the filled silhouette and its outline read as ONE object. It is built in LCh with
#   the box's hue held and only lightness and chroma moved — both verdict fills sit at the
#   same L* 72 (only hue separates them, as with the boxes) at about half the box's chroma.
#   The first version mixed the box with 80% white in sRGB, which landed near white (OK:
#   ΔE 13 from white, chroma 8 of the box's 49) and drifted NOK's hue 22°; a mask you cannot
#   tell from white is a token that exists on paper and does nothing on screen. Measured
#   (the floors are CONST_MASK_FILL_* above, pinned in test_theme):
#       OK   #B4AADB  ΔE(box, fill) 33.6 (was 59.4)  ΔE(fill, white) 39.0 (was 13.2)
#       NOK  #FC929C  ΔE(box, fill) 46.8 (was 74.7)  ΔE(fill, white) 51.1 (was 24.6)
#   Both fills are ~9.7:1 against the black mask ground, so the silhouette stays obvious. The
#   index numeral never sits on the fill (it is drawn on its chip, in the box colour), so the
#   fill does not have to be pale.
#   Unit [Dict<string, Tuple<string> 1x3>] (box, ink, fill)
#
#   A catalogue mode adds two (2026-10-11). WARNING (not the part) is the status amber, its text twin and
#   a fill built the same way as the others: L* 72 at half the box's chroma, hue held —
#       Warning  #DFA475  ΔE(box, fill) 38.7  ΔE(fill, white) 46.2  9.7:1 on black, hue shift 0.2°.
#   UNSPECIFIED (probably several parts, not judged) is the neutral detection colour, assembled at the end
#   of this module (CONST_DETECTION_COLORS): not judged reads like detected, not judged. On the label mask
#   its outline is the mask's own darker neutral (Mask_Outline_Color), as for a detect-only run.
#   Unit [Dict<string, Tuple<string> 1x3>] (box, ink, fill)
CONST_VERDICT_COLORS = {
    'OK':  ('#6C63B5', '#4a4180', '#B4AADB'),   # pass
    'NOK': ('#ff005c', '#d1004a', '#FC929C'),   # fail — the brand magenta, now correctly the fail marker
    'Warning': (CONST_WARN, CONST_WARN_INK, '#DFA475'),   # not the catalogue part — amber, see above
}
# The verdict a detection carries until classification sets one; every object is OK today.
#   Unit [string]
CONST_VERDICT_DEFAULT = 'OK'

# The NEUTRAL object colour, used when a configuration only DETECTS and does not classify
# (General.Classification.Enabled = false): every object is drawn in this one colour, the box
# and its darker ink twin, because there is no pass/fail to encode.
#
# It is deliberately OFF THE INDIGO AXIS — a desaturated cool grey (HSL saturation ~0.10), not a
# quieter shade of the OK indigo #6C63B5 (saturation ~0.36). Recording the classification flag
# per set exists so a MIXED history can show which sets were judged and which were not; that only
# works if 'judged OK' and 'not judged' do not share a hue. Still a DISTINCT token from the
# verdict colours, so the two can diverge.
#
# The box is drawn INTO the frame — on the green table and on the parts — so it is measured
# against the real annotation surfaces, not the UI chrome. The gate that matters there is
# perceptual ΔE (CIE76), the project's distinctness floor of 12: a chromatic box rides on hue
# (OK #6C63B5 has only ~1.1 luminance contrast on the table yet ΔE ~70), but a neutral grey has
# no hue to lean on, so its worst case is grey-on-grey — the bright machined steel in sets
# 003/005 (~(120,120,125)). The earlier #949AA6 sat at the steel's own lightness and collapsed
# to ΔE ~10.7 there, under the floor. Lightening it along the grey axis (NOT back toward indigo,
# which would undo the separation from OK) pulls it clear: measured ΔE is now ~23 vs bright steel
# (~2x the floor), ~46 vs the table green, ~54 vs the dark plates, and ~53 to the OK box (up from
# ~46). The darker ink twin is reserved for text on the white card.
#
# THE LABEL MASK USES ITS OWN, DERIVED NEUTRAL PAIR — outline and fill — not this box. The box is
# drawn on the frame (it needs L* 76.85 to read on the green table and the parts); on the mask
# the outline only ever sits on the fill and on black, so it does not need that lightness. With
# the box as the mask outline, the ΔE 25 outline/fill floor forced the fill dark (L* 50); a darker
# mask outline frees the fill to go light. Neutral_Mask_Colors derives the pair in this box's own
# hue and chroma, and it no longer depends on the box's LIGHTNESS at all:
#     fill     L* 79.75 (#C0C6D2) — as light as the fill/white floor allows: for chroma C*, ΔE to
#                                   white >= 21 needs L* <= 100 - sqrt(21² - C*²) = 80.12, less the
#                                   0.5 margin (hex rounding lands it at 79.75). The floor is 21, not
#                                   25, on purpose — see CONST_MASK_FILL_MIN_WHITE_DELTA_E;
#     outline  L* 51.86 (#767C87) — the midpoint of [48.88 (4.5:1 against the black ground),
#                                   fill L* - 25 (the outline/fill floor)] = [48.88, 54.62];
#     measured ΔE(outline, fill) 27.9, ΔE(fill, white) 21.3, fill 12.2:1 and outline 5.0:1 on black.
# The outline's window is 5.74 L* wide. It closes only if the FLOORS change (not the box),
# and then Theme raises at import naming the window rather than shipping a pair that breaks one.
#   Unit [string] (hex colour)
CONST_DETECTION_BOX = '#B8BECA'
CONST_DETECTION_INK = '#5C6270'
# CONST_DETECTION_COLORS — the (box, ink, fill) triple — is assembled at the END of this module,
# once Neutral_Mask_Fill (which needs the colour-space helpers below) is defined.

# The Log-view severity text colours, one named semantic token per level. The log view
# colours the level field and the message by these (the timestamp stays muted); a level
# colour is NEVER a literal at the call site. INFO reuses the Scene-Understanding ink;
# WARNING and ERROR are the palette's darker amber/red inks, chosen to read clearly as small
# text on the white card (CONST_CARD).
#
#   NOTE on CONST_LOG_ERROR vs '#ff005c': the log ERROR colour is DELIBERATELY not the NOK
#   verdict magenta (CONST_VERDICT_COLORS['NOK'] = '#ff005c'). NOK means "this part is
#   faulty"; a log ERROR means "the application failed". Painting them the same colour would
#   conflate an inspection result with a software fault, so the two reds are kept distinct —
#   #b91c1c is a deep, true red (the red sibling of the OK green and WARNING amber inks),
#   clearly not the neon pink-magenta of the verdict. Do NOT unify them.
#   Unit [string] (hex colour)
CONST_LOG_INFO    = CONST_INK      # '#2b2455' — the Scene-Understanding text colour
CONST_LOG_WARNING = CONST_WARN_INK # '#b45309' — deep amber, readable as text on the card
CONST_LOG_ERROR   = '#b91c1c'      # deep true red — NOT the NOK verdict '#ff005c' (see note)

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
# viridis: viridis passes ΔE 4.2 from the OK verdict's ink and 12.0 from CONST_OK's green; cividis has no
# green, red or magenta, keeps every colour >= ΔE 12 (CONST_ANNOTATE_MIN_DELTA_E) from the verdict, status
# and log colours — the closest, 12.5, is the OK ink — and is built for colour-vision deficiency. Its
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
