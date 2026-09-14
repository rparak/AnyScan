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
# readable contrast. Green, red and amber are deliberately ABSENT: here they mean
# pass, fail and degraded (see the verdict tokens above). An object numbered 3 is not
# 'the good one'.
#   Unit [Vector<Tuple<string> 1x2>]
CONST_INDEX_COLORS = [
    ('#ff005c', '#b3003f'),
    ('#0ea5e9', '#0369a1'),
    ('#7c3aed', '#5b21b6'),
    ('#14b8a6', '#0f766e'),
    ('#6366f1', '#4338ca'),
    ('#d946ef', '#a21caf'),
]

# Reserved hue bands (fraction of the wheel, 0..1) an object colour must avoid: an
# object painted in the pass/fail/degraded hues would misread as a verdict. Guards
# both the base palette and every generated variant (__Assert_No_Reserved_Hue).
#   Unit [Vector<Tuple<float> 1x2>]
CONST_RESERVED_HUE_BANDS = [
    (0.97, 1.00), (0.00, 0.03),   # true red (~0deg)   — fail (NOT the brand magenta,
                                  #                      hue ~0.94, which is object 1)
    (0.06, 0.15),                 # amber    (~40deg)  — degraded
    (0.25, 0.42),                 # green    (~120deg) — pass
]

# The lightness/saturation steps (delta_l, delta_s) that extend the six base pairs
# past the sixth object. Applied to a base colour with its HUE HELD FIXED, so a
# variant can never drift into a reserved hue; only the shade changes. Enough steps
# to keep a ten-object frame (Image_006's successor, Image_001) distinct.
#   Unit [Vector<Tuple<float> 1x2>]
CONST_INDEX_VARIANT_STEPS = [
    (0.16, -0.18), (-0.16, -0.10), (0.26, -0.30), (-0.24, -0.04),
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


def Index_Color(index: int) -> tp.Tuple[str, str]:
    """
    Description:
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
    cycle = index // base
    if cycle == 0:
        return box_hex, ink_hex
    delta_l, delta_s = CONST_INDEX_VARIANT_STEPS[(cycle - 1) % len(CONST_INDEX_VARIANT_STEPS)]
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
