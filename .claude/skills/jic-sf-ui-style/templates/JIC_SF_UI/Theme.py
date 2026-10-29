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
# File Name: JIC_SF_UI/Theme.py
## =========================================================================== ##

# System (Default)
import math
# Typing (Support for type hints)
import typing as tp

"""
Description:
    Initialization of constants.

    The JIC Smart Factory palette as pure values: no Qt, no OpenCV. The widgets (through Style, which re-exports
    these) and any Qt-free renderer (Annotate, an exported image, a generated figure) read this ONE definition, so a
    mark on an image and its words in the panel are the same colour. Generalised from AnyScan's
    src/Parameters/Theme.py; every value and every measured ratio below is AnyScan's.

    Rules this module carries (references/palette.md has the why):
      - Every colour in the application is a token here. A new colour is a new token, commented with its role.
      - One purple, #640ABA. No darker or lighter shade of it exists; hierarchy is size and weight.
      - A state has one colour in every view: OK #640ABA, NOK #FF6540, Warning #FFC226.
      - A colour is never lightened, darkened or rotated at a call site to gain contrast: legibility comes from the
        foreground (white numerals) or from a token's text twin.
"""
# The brand's own colours (JIC Smart Factory guide): purple, grey-lilac, periwinkle; from the wider JIC palette the
# orange-red, amber and green. The guide's yellow #FFEF85 is decoration and is no token.
#   Unit [string] (hex colour)
CONST_PURPLE        = '#640ABA'   # 9.15:1 on white, 6.79:1 on the grey-lilac
CONST_GREY_LILAC    = '#E1DCE6'   # rules, hover fill, the viewport ground
CONST_PERIWINKLE    = '#C2C9FF'   # pressed fill, scroll handle, OK word ground, analysis-grid lines
CONST_ORANGE_RED    = '#FF6540'   # NOK (2.92:1 on white)
CONST_AMBER         = '#FFC226'   # Warning (1.62:1 on white)
CONST_GREEN         = '#3DBE4C'   # system health only, never an object (2.42:1 on white)
CONST_WHITE         = '#FFFFFF'

# Surface and text: purple text on white, separated by thin grey-lilac rules.
#   Unit [string] (hex colour)
CONST_BG            = CONST_WHITE         # page background
CONST_CARD          = CONST_WHITE         # card fill
CONST_CARD_BORDER   = CONST_GREY_LILAC    # card outlines (1 px)
CONST_INK           = CONST_PURPLE        # all text, outlines, the selected segment, the OK state, icons
CONST_INK_SOFT      = CONST_INK           # secondary text: one purple, hierarchy by size and weight
CONST_INK_MUTE      = '#6F5783'           # labels, empty states, timestamps, a chart's total: 6.24:1 on white,
                                          # 4.63:1 on the grey-lilac (the purple's hue, C* 28, L* 41)
CONST_LINE          = CONST_GREY_LILAC    # dividers, gridlines
CONST_ON_INK        = CONST_WHITE         # words and icons on any purple fill (9.15:1)
CONST_LOGO_INK      = CONST_PURPLE        # the logo's one colour, and a live tagline set beside it

# Controls. A control state is ALWAYS a (fill, label) pair, each >= 4.5:1, measured from rendered pixels.
# Plain button: 1 px purple rule; hover fills grey-lilac (6.79:1), pressed periwinkle (5.71:1).
# Primary button (exactly one per action row): 2 px purple rule; hover and pressed fill purple under white (9.15:1).
# Disabled is exempt from 4.5:1 but must differ from enabled by dE76 >= 12 in label or fill.
#   Unit [string] (hex colour)
CONST_CONTROL_BORDER          = CONST_INK
CONST_CONTROL_HOVER           = CONST_GREY_LILAC
CONST_CONTROL_HOVER_BORDER    = CONST_INK
CONST_CONTROL_PRESSED         = CONST_PERIWINKLE
CONST_INK_HOVER               = CONST_INK     # selected / primary hover fill: one purple, no shift on hover
CONST_INK_PRESSED             = CONST_INK
CONST_CONTROL_DISABLED_TEXT   = '#B4A6BE'     # 2.30:1 on white: the purple's hue at L* 70
CONST_CONTROL_DISABLED_BORDER = CONST_LINE
CONST_PRIMARY_DISABLED_FILL   = CONST_CARD
CONST_PRIMARY_DISABLED_TEXT   = CONST_CONTROL_DISABLED_TEXT

# Overlays, each a token at a named opacity (Style.Token_Color(token, alpha)), never a QColor of copied numbers.
#   Unit [string] (hex colour) / [float] (opacity 0..1)
CONST_SCRIM            = CONST_INK         # behind a modal dialog
CONST_SCRIM_ALPHA      = 0.16
CONST_BUSY_SCRIM       = CONST_GREY_LILAC  # the busy overlay over an image view: the view's own ground at 70 %
CONST_BUSY_SCRIM_ALPHA = 0.70
CONST_BUSY_INK         = CONST_INK         # the busy step's words and pixel icon, directly on the overlay
CONST_BUSY_DIM_ALPHA   = 0.18              # an animated icon's unlit cells
CONST_GRID_LINE        = CONST_PERIWINKLE  # the analysis grid: 1 px lines at 55 %
CONST_GRID_LINE_ALPHA  = 0.55
CONST_GRID_FILL        = '#CC9EF1'         # the purple's light tint (the OK mask fill) at 30 % inside the lines
CONST_GRID_FILL_ALPHA  = 0.30
CONST_SCROLLBAR_HANDLE = CONST_PERIWINKLE
CONST_TOPBAR_DIVIDER   = CONST_LINE        # the rule between the product lockup and the JIC logo

# Status colours: system health only (a camera, a model set, the system cell), never an object. Green and amber are
# too light for a dot on white, so each is used as a dot in its hue at L* 60.5 (3.1:1, the 3:1 graphic floor) and as
# words in its hue at L* 41 (6.2:1). A pill's outline takes the brand colour itself.
#   Unit [string] (hex colour)
CONST_OK            = '#1EA838'   # dot: connected, ready
CONST_OK_INK        = '#00711B'   # words
CONST_OK_BORDER     = CONST_GREEN
CONST_WARN          = '#B98B00'   # dot: degraded but working
CONST_WARN_INK      = '#7C5B00'   # words
CONST_WARN_BORDER   = CONST_AMBER
CONST_STATUS_TEXT_COLORS = {CONST_OK: CONST_OK_INK, CONST_WARN: CONST_WARN_INK}

# The viewport (an image view's ground): the grey-lilac; its text is the purple (6.79:1), error text the log red.
#   Unit [string] (hex colour)
CONST_VIEWPORT      = CONST_GREY_LILAC
CONST_VIEWPORT_TEXT = CONST_INK

# The funding band: the purple, white logos, white rules at 20 %, white motif squares, a white disclaimer at 76 %.
#   Unit [string] (hex colour) / [float] (opacity 0..1)
CONST_BAND            = CONST_INK
CONST_BAND_LINE       = CONST_WHITE
CONST_BAND_TEXT       = CONST_WHITE
CONST_BAND_LINE_ALPHA = 0.20
CONST_BAND_TEXT_ALPHA = 0.76      # 5.72:1 on the purple
# The pixel motif in the empty image view's top-right corner: the purple at 7 % and 12 % on the grey-lilac.
CONST_CORNER_MOTIF       = CONST_INK
CONST_CORNER_MOTIF_ALPHA = (0.07, 0.12)

# THE THREE STATES, as (box, ink, fill): the box is the stroke on an image, its chip and every chart series, legend
# sample and filter swatch of that state (one colour per state, in every view, no darker chart variant); the ink is
# its words' colour on a verdict-coloured element; the fill is a label-mask tint in the box's own hue.
#   OK       #640ABA  white numeral 9.15:1
#   NOK      #FF6540  white numeral 2.92:1 (the owner's accepted exception for short bold numerals)
#   Warning  #FFC226  white numeral 1.62:1 (the owner's accepted exception), every kind of Warning alike
# The kind of a Warning is told in words, never in colour.
#   Unit [Dict<string, Tuple<string> 1x3>]
CONST_VERDICT_COLORS = {
    'OK':      (CONST_PURPLE, CONST_PURPLE, '#CC9EF1'),
    'NOK':     (CONST_ORANGE_RED, CONST_ORANGE_RED, '#CD7157'),
    'Warning': (CONST_AMBER, CONST_AMBER, '#B28508'),
}
CONST_VERDICT_DEFAULT = 'OK'
# The ground a state's WORDS sit on (a badge): the purple words on a tint where the purple on the box is too weak:
# OK on the periwinkle 5.71:1, NOK on #FFD9D0 7.01:1, Warning on its amber 5.66:1.
#   Unit [string] (hex colour)
CONST_OK_LABEL_GROUND  = CONST_PERIWINKLE
CONST_NOK_LABEL_GROUND = '#FFD9D0'
# Every chip numeral on an image is plain white, in every state; no rim, no casing.
CONST_CHIP_NUMERAL = CONST_WHITE

# A screen-only inspection area: 1 px, solid, square, unfilled. Light amber over a camera image (4.71:1 on AnyScan's
# green table, 1.18:1 against the Warning amber, told apart by its 1 px against a frame's 2 px); the purple over the
# empty grey-lilac view, where the amber vanishes (1.01:1; the purple 6.79:1).
#   Unit [string] (hex colour)
CONST_INSPECTION_AREA       = '#FFD880'
CONST_INSPECTION_AREA_EMPTY = CONST_INK

# The neutrals: no pass/fail to encode.
#   CONST_DETECTION_INK: a detect-only mode's words, chart text (axis titles, legend labels, hover secondaries), the
#     dark chart neutral and threshold guides: 6.22:1 on white (the purple's hue, C* 10, L* 41). Far from every state
#     (dE 80-95), so a judged and an unjudged set never share a hue.
#   CONST_CHART_LIGHT_INK: the light chart neutral (a derived series, e.g. a running mean): the lightest of the dark
#     neutral's hue that clears the 3:1 a graphic needs, 3.07:1 on white, 2.02:1 and dE 19.9 from the dark one.
#   CONST_DETECTION_BOX: every object's box in a detect-only mode: the logo purple (it shows no verdict at all).
#   Unit [string] (hex colour)
CONST_DETECTION_INK   = '#655E6D'
CONST_CHART_LIGHT_INK = '#9890A0'
CONST_DETECTION_BOX   = CONST_LOGO_INK

# Log severities: a word, a weight AND a colour, never colour alone. ERROR is deliberately not the NOK orange-red:
# a faulty part is not a software fault (dE 55 apart).
#   Unit [string] (hex colour)
CONST_LOG_INFO    = CONST_INK
CONST_LOG_WARNING = CONST_WARN_INK
CONST_LOG_ERROR   = '#BE0362'       # 6.22:1 on white, 4.61:1 on the grey-lilac
CONST_LOG_LEVEL_COLORS = {'INFO': CONST_LOG_INFO, 'WARNING': CONST_LOG_WARNING, 'ERROR': CONST_LOG_ERROR}


def Verdict_Color(verdict: str) -> tp.Tuple[str, str, str]:
    """
    Description:
        The (box, ink, fill) triple of a state; an unknown state falls back to OK so a mark always renders.

    Args:
        (1) verdict [string]: 'OK', 'NOK' or 'Warning'.

    Returns:
        (1) parameter [Tuple<string> 1x3]: The (box, ink, fill) hex colours.
    """

    return CONST_VERDICT_COLORS.get(verdict, CONST_VERDICT_COLORS[CONST_VERDICT_DEFAULT])


def Label_Ground(verdict: str) -> str:
    """
    Description:
        The ground a state's words sit on (a badge): the purple words clear 4.5:1 on each.

    Args:
        (1) verdict [string]: 'OK', 'NOK' or 'Warning'.

    Returns:
        (1) parameter [string]: The ground colour.
    """

    return {'OK': CONST_OK_LABEL_GROUND, 'NOK': CONST_NOK_LABEL_GROUND}.get(verdict, Verdict_Color(verdict)[0])


def Status_Text_Color(color: str) -> str:
    """
    Description:
        The colour status WORDS are drawn in for a status colour: CONST_OK and CONST_WARN are dots, their words take
        the _INK twin; every other colour is its own text colour.

    Args:
        (1) color [string]: The status colour token.

    Returns:
        (1) parameter [string]: The token to draw the words in.
    """

    return CONST_STATUS_TEXT_COLORS.get(color, color)


def Log_Level_Color(level: str) -> str:
    """
    Description:
        The text colour of a log severity; an unknown level falls back to INFO.

    Args:
        (1) level [string]: 'INFO', 'WARNING' or 'ERROR'.

    Returns:
        (1) parameter [string]: The colour.
    """

    return CONST_LOG_LEVEL_COLORS.get(level, CONST_LOG_INFO)


def Hex_To_Rgb(hex_color: str) -> tp.Tuple[int, int, int]:
    """
    Description:
        A '#rrggbb' string as (R, G, B) integers 0..255.

    Args:
        (1) hex_color [string]: The colour.

    Returns:
        (1) parameter [Vector<int> 1x3]: (R, G, B).
    """

    value = hex_color.lstrip('#')
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def Hex_To_Bgr(hex_color: str) -> tp.Tuple[int, int, int]:
    """
    Description:
        A '#rrggbb' string as (B, G, R), the channel order OpenCV draws in.

    Args:
        (1) hex_color [string]: The colour.

    Returns:
        (1) parameter [Vector<int> 1x3]: (B, G, R).
    """

    r, g, b = Hex_To_Rgb(hex_color)
    return (b, g, r)


def __Linear(channel: float) -> float:
    """
    Description:
        Undo the sRGB gamma of one 0..255 channel (linear light 0..1).

    Args:
        (1) channel [float]: The channel.

    Returns:
        (1) parameter [float]: Linear light.
    """

    channel /= 255.0
    return ((channel + 0.055) / 1.055) ** 2.4 if channel > 0.04045 else channel / 12.92


def __Lab_F(t: float) -> float:
    """
    Description:
        The CIELAB nonlinearity.

    Args:
        (1) t [float]: A normalised XYZ component.

    Returns:
        (1) parameter [float]: The transformed component.
    """

    return t ** (1.0 / 3.0) if t > 0.008856 else 7.787 * t + 16.0 / 116.0


def Lab_Of(hex_color: str) -> tp.Tuple[float, float, float]:
    """
    Description:
        A colour as CIE L*a*b* (D65).

    Args:
        (1) hex_color [string]: The colour.

    Returns:
        (1) parameter [Vector<float> 1x3]: (L*, a*, b*).
    """

    r, g, b = (__Linear(c) for c in Hex_To_Rgb(hex_color))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    fx, fy, fz = __Lab_F(x), __Lab_F(y), __Lab_F(z)
    return (116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz))


def Lch_Of(hex_color: str) -> tp.Tuple[float, float, float]:
    """
    Description:
        A colour as CIE LCh: lightness, chroma, hue in degrees, the space text twins are derived in.

    Args:
        (1) hex_color [string]: The colour.

    Returns:
        (1) parameter [Vector<float> 1x3]: (L*, C*, h).
    """

    lightness, a, b = Lab_Of(hex_color)
    return (lightness, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360.0)


def Delta_E(hex_a: str, hex_b: str) -> float:
    """
    Description:
        The CIE76 distance between two colours; below ~10 two marks read as one colour, 12 is the project's floor.

    Args:
        (1) hex_a [string]: The first colour.
        (2) hex_b [string]: The second colour.

    Returns:
        (1) parameter [float]: dE76.
    """

    return math.dist(Lab_Of(hex_a), Lab_Of(hex_b))


def Relative_Luminance(hex_color: str) -> float:
    """
    Description:
        The WCAG relative luminance of a colour.

    Args:
        (1) hex_color [string]: The colour.

    Returns:
        (1) parameter [float]: 0 (black) .. 1 (white).
    """

    r, g, b = (__Linear(c) for c in Hex_To_Rgb(hex_color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def Contrast_Ratio(hex_a: str, hex_b: str) -> float:
    """
    Description:
        The WCAG contrast ratio of two colours: 4.5:1 is the floor for text, 3:1 for a graphic.

    Args:
        (1) hex_a [string]: The first colour.
        (2) hex_b [string]: The second colour.

    Returns:
        (1) parameter [float]: 1.0 .. 21.0.
    """

    l_a, l_b = Relative_Luminance(hex_a), Relative_Luminance(hex_b)
    return (max(l_a, l_b) + 0.05) / (min(l_a, l_b) + 0.05)
