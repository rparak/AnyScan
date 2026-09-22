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
# File Name: ../Parameters/Theme.py
## =========================================================================== ##

# System (Default)
import colorsys
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
CONST_INK_MUTE      = '#8983a6'   # desaturated violet-grey: labels, empty states, disclaimer
CONST_LINE          = '#ecebf2'   # violet-tinted dividers

CONST_BRAND         = '#ff005c'   # EDIH-DIGIMAT magenta: object 1 and focus only

# The verdict colours. Green, red and amber are RESERVED here: they mean pass,
# degraded and fail on the badge, so they must never appear as an object colour — an
# object numbered 3 painted green would silently read as 'the good one'. This is why
# CONST_INDEX_COLORS below excludes those three hues, and why Index_Color's palette
# extension varies only lightness/saturation, never hue (see __Assert_No_Reserved_Hue).
CONST_OK            = '#16a34a'   # connected, pass
CONST_OK_INK        = '#15803d'
CONST_OK_SOFT       = '#f2faf5'
CONST_OK_BORDER     = '#cfe9d8'
CONST_WARN          = '#d97706'   # degraded but working
CONST_WARN_INK      = '#b45309'
CONST_WARN_SOFT     = '#fdf8ef'
CONST_WARN_BORDER   = '#f3e2c3'

CONST_VIEWPORT      = '#2b2455'   # the one dark surface in the console: the brand indigo
CONST_VIEWPORT_TEXT = '#9b95bd'   # readable lavender-grey on the indigo viewport

# The deep-indigo funding band tokens.
CONST_BAND          = '#2b2455'   # deep-indigo funding band
CONST_BAND_LINE     = '#4a4180'   # dividers on the band
CONST_BAND_TEXT     = '#b9b2d6'   # lavender text/disclaimer on the band

# One colour pair per detection index, shared by the frame overlay and the text.
# `box` is the stroke on the dark viewport; `ink` is a darkened twin of the same hue
# for type on white, because a saturated stroke colour set as 14.5px text falls below
# readable contrast. Green, amber AND the red-through-magenta wedge are deliberately
# ABSENT: green/amber are the pass/degraded verdicts, and the whole red-magenta wedge
# reads as 'fail' at a glance — including the brand magenta (#ff005c), which is a
# verdict-lookalike, so it stays the brand accent elsewhere but is NOT an object
# colour. An object's colour must never be mistakable for a verdict.
#   Unit [Vector<Tuple<string> 1x2>]
CONST_INDEX_COLORS = [
    ('#0ea5e9', '#0369a1'),   # cyan-blue
    ('#7c3aed', '#5b21b6'),   # violet
    ('#14b8a6', '#0f766e'),   # teal
    ('#6366f1', '#4338ca'),   # indigo
    ('#d946ef', '#a21caf'),   # magenta-purple (distinct from the red-magenta wedge)
]

# The two per-object VERDICT colours, as (box, ink) pairs like CONST_INDEX_COLORS. The
# box is the stroke drawn on the frame and the mask contour; the ink is the darkened
# twin for verdict text on the white card. These DRIVE the object rendering in both
# views (via Verdict_Color) — every object is drawn in its verdict colour, replacing the
# per-index palette there. Until classification lands every object is OK, so everything
# renders in the OK box.
#
#   NOTE on '#ff005c': this is the EDIH-DIGIMAT brand magenta that was deliberately
#   REMOVED from the object palette (see CONST_INDEX_COLORS) because it reads as a fail
#   marker at a glance. As the actual NOK marker it is now exactly right — do NOT
#   "restore" it to the object palette or swap it for a calmer red; its fail-lookalike
#   quality is the whole reason it belongs here.
#   The OK box '#6C63B5' is a deliberately LIGHTER tint than its ink twin '#4a4180':
#   '#4a4180' alone is too dark to read against the dark plates in Image_003/005, so the
#   box carries the lighter value and the ink is reserved for text on the white card.
#
#   The THIRD entry is the label-mask FILL: a light tint of the box (20% box + 80% white),
#   so the filled silhouette and its box outline read as ONE object of the same hue rather
#   than a white shape with an unrelated coloured border. It is stored, not derived at the
#   call site. It stays far enough from the box that the outline survives ON the fill, not
#   only against the black ground — measured ΔE(box, fill) is ~59 (OK) and ~75 (NOK) — and
#   it is light, so the index numeral stays legible in a dark tone on it.
#   Unit [Dict<string, Tuple<string> 1x3>] (box, ink, fill)
CONST_VERDICT_COLORS = {
    'OK':  ('#6C63B5', '#4a4180', '#E2E0F0'),   # pass
    'NOK': ('#ff005c', '#d1004a', '#FFCCDE'),   # fail — the brand magenta, now correctly the fail marker
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
# ~46). The darker ink twin is reserved for text on the white card. The THIRD entry is the
# label-mask FILL — a light tint of the box (20% box + 80% white), the same rule as the verdict
# fills, so a detect-only silhouette and its box read as one neutral object and imply no verdict
# nobody made. Measured ΔE(box, fill) ~20, above the distinctness floor, so the outline survives
# on the fill; and it is light, so the index numeral stays legible in a dark tone on it.
#   Unit [Tuple<string> 1x3] (box, ink, fill)
CONST_DETECTION_COLORS = ('#B8BECA', '#5C6270', '#F1F2F4')

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

# Reserved hue bands (fraction of the wheel, 0..1) an object colour must avoid: an
# object in a verdict hue would misread as pass/fail/degraded. The red end is the
# WHOLE red-through-magenta wedge, not just true red, because a rose/crimson reads as
# fail at a glance even though its hue is not 0. Guards both the base palette and every
# generated variant (__Assert_No_Reserved_Hue).
#   Unit [Vector<Tuple<float> 1x2>]
CONST_RESERVED_HUE_BANDS = [
    (0.83, 1.00), (0.00, 0.05),   # red through magenta (~300..360deg) — fail
    (0.05, 0.18),                 # amber / orange      (~20..65deg)   — degraded
    (0.22, 0.45),                 # green               (~80..160deg)  — pass
]

# The lightness LEVELS (delta_l, delta_s) that extend the five base pairs past the
# fifth object, applied to a base colour with its HUE HELD FIXED (so a variant never
# drifts into a reserved hue — only the shade changes). Each hue gets three well-
# separated lightness levels — base (medium), dark, then light — so twelve objects are
# five hues at distinct lightnesses rather than near-repeats of one another. A dark
# and a light teal read as clearly different colours; two whites do not.
#   Unit [Vector<Tuple<float> 1x2>]
CONST_INDEX_VARIANT_STEPS = [
    (-0.30, -0.05),   # level 1 — dark
    (0.30, -0.15),    # level 2 — light
]


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


def __Rgb_To_Hex(r: int, g: int, b: int) -> str:
    """
    Description:
        An (R, G, B) 0..255 triple as a '#rrggbb' string.

    Args:
        (1 - 3) r, g, b [int]: The colour channels (0..255).

    Returns:
        (1) parameter [string]: The colour as '#rrggbb'.
    """

    return '#%02x%02x%02x' % (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


def Hue_Of(hex_color: str) -> float:
    """
    Description:
        The hue of a colour as a fraction of the wheel (0..1) — the axis the reserved
        verdict hues are defined on.

    Args:
        (1) hex_color [string]: The colour as '#rrggbb'.

    Returns:
        (1) parameter [float]: The hue (0..1).
    """

    r, g, b = Hex_To_Rgb(hex_color)
    return colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)[0]


def __Lab(hex_color: str) -> tp.Tuple[float, float, float]:
    """
    Description:
        A colour as CIE L*a*b* (D65), the space perceptual distance is measured in.

    Args:
        (1) hex_color [string]: The colour as '#rrggbb'.

    Returns:
        (1) parameter [Vector<float> 1x3]: The (L, a, b) coordinates.
    """

    def _Linear(channel: float) -> float:
        """
        Description:
            Undo the sRGB gamma for one 0..255 channel, giving linear light 0..1.

        Args:
            (1) channel [float]: The channel value (0..255).

        Returns:
            (1) parameter [float]: The linear-light value (0..1).
        """

        channel /= 255.0
        return ((channel + 0.055) / 1.055) ** 2.4 if channel > 0.04045 else channel / 12.92

    r, g, b = (_Linear(c) for c in Hex_To_Rgb(hex_color))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = (0.2126 * r + 0.7152 * g + 0.0722 * b)
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def _F(t: float) -> float:
        """
        Description:
            The CIELAB nonlinearity applied to a normalised XYZ component.

        Args:
            (1) t [float]: The normalised component.

        Returns:
            (1) parameter [float]: The transformed component.
        """

        return t ** (1.0 / 3.0) if t > 0.008856 else 7.787 * t + 16.0 / 116.0

    fx, fy, fz = _F(x), _F(y), _F(z)
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


def __Is_Reserved_Hue(hue: float) -> bool:
    """
    Description:
        Whether a hue falls in a reserved verdict band (pass/fail/degraded).

    Args:
        (1) hue [float]: The hue as a fraction of the wheel (0..1).

    Returns:
        (1) parameter [bool]: True when the hue is reserved.
    """

    return any(low <= hue <= high for low, high in CONST_RESERVED_HUE_BANDS)


def __Shade(hex_color: str, delta_l: float, delta_s: float) -> str:
    """
    Description:
        Shift a colour's lightness and saturation while HOLDING ITS HUE, so the shade
        changes but the colour can never drift into a reserved verdict hue.

    Args:
        (1) hex_color [string]: The base colour as '#rrggbb'.
        (2) delta_l [float]: The lightness delta (clamped to a readable band).
        (3) delta_s [float]: The saturation delta.

    Returns:
        (1) parameter [string]: The shaded colour as '#rrggbb'.
    """

    r, g, b = Hex_To_Rgb(hex_color)
    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    l = min(0.85, max(0.25, l + delta_l))
    s = min(1.0, max(0.35, s + delta_s))
    nr, ng, nb = colorsys.hls_to_rgb(h, l, s)
    return __Rgb_To_Hex(int(round(nr * 255)), int(round(ng * 255)), int(round(nb * 255)))


def Verdict_Color(verdict: str) -> tp.Tuple[str, str, str]:
    """
    Description:
        The (box, ink, fill) colour triple for a per-object verdict, from the ONE
        CONST_VERDICT_COLORS definition — the object rendering reads this, never a colour
        literal at the call site, so the pass/fail colours are changed in one place. An
        unknown or empty verdict falls back to the default (OK), so a detection carrying
        no verdict still renders. The fill is the light label-mask tint of the box.

    Args:
        (1) verdict [string]: The verdict key ('OK' or 'NOK').

    Returns:
        (1) parameter [Tuple<string> 1x3]: The (box, ink, fill) hex colours.
    """

    return CONST_VERDICT_COLORS.get(verdict, CONST_VERDICT_COLORS[CONST_VERDICT_DEFAULT])


def Detection_Color() -> tp.Tuple[str, str, str]:
    """
    Description:
        The (box, ink, fill) colour triple for a plain, unjudged detection — used when the
        configuration only detects (classification off), so every object is one neutral colour.
        From the ONE CONST_DETECTION_COLORS definition, a distinct token from the verdict colours
        ('detected, not judged', never a pass/fail). The fill is the light label-mask tint of the
        box.

    Returns:
        (1) parameter [Tuple<string> 1x3]: The (box, ink, fill) hex colours.
    """

    return CONST_DETECTION_COLORS


def Index_Color(index: int) -> tp.Tuple[str, str]:
    """
    Description:
        RETAINED (not on the default render path). The object rendering is now keyed by
        VERDICT colour, not by index; Index_Color, the coordinated-stroke assignment in
        Vision.Utilities.Annotate and the ΔE distinctness test are kept for the diagnostic
        label-mask variant reachable by one constant (Annotate.CONST_ANNOTATE_MASK_FILL =
        'index'), which fills each object in its own colour to reveal a merge.

        The (box, ink) colour pair for a detection index (0-based), stable across runs
        and shared by the frame overlay and the label mask, so the same object is the
        same colour everywhere. The first six indices are the hand-tuned base pairs;
        past the sixth the palette is extended by shifting a base colour's
        lightness/saturation with its HUE HELD FIXED (CONST_INDEX_VARIANT_STEPS), so a
        variant is a distinct shade of a safe hue and never lands on the reserved
        pass/fail/degraded colours.

    Args:
        (1) index [int]: The 0-based object index.

    Returns:
        (1) parameter [Tuple<string> 1x2]: The (box, ink) hex colours.
    """

    base = len(CONST_INDEX_COLORS)
    box_hex, ink_hex = CONST_INDEX_COLORS[index % base]
    level = index // base
    if level == 0:
        return box_hex, ink_hex
    # A variant of a base colour at a distinct lightness level (dark, then light),
    # hue held fixed — so the same hue's base, dark and light variants are three
    # clearly different shades.
    delta_l, delta_s = CONST_INDEX_VARIANT_STEPS[(level - 1) % len(CONST_INDEX_VARIANT_STEPS)]
    box = __Shade(box_hex, delta_l, delta_s)
    # The ink twin: the same variant, darkened for readable text on white.
    ink = __Shade(box, -0.22, 0.05)
    return box, ink


def __Assert_No_Reserved_Hue() -> None:
    """
    Description:
        Load-time guard: neither the base palette nor the first two cycles of
        generated variants may fall in a reserved verdict hue. A generated variant
        landing on green would silently read as 'pass' to anyone reading the UI, so
        this fails loudly at import rather than shipping a misleading colour.
    """

    for i in range(len(CONST_INDEX_COLORS) * 3):
        box, _ = Index_Color(i)
        if __Is_Reserved_Hue(Hue_Of(box)):
            raise ValueError(
                'Index_Color(%d) = %s has a reserved verdict hue (%.3f); the palette '
                'or its variant steps must avoid pass/fail/degraded hues.'
                % (i, box, Hue_Of(box)))


__Assert_No_Reserved_Hue()
