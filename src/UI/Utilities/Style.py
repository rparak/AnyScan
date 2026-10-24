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
# File Name: ../UI/Utilities/Style.py
## =========================================================================== ##

# System (Default)
import math
import os
# Typing (Support for type hints)
import typing as tp
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QFontDatabase, QIcon, QImage, QPixmap, QPainter
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QApplication, QWidget
# Custom Lib.: AnyScan domain — the confidence severity bands (Qt-free)
#   ../Parameters/Vision
from Parameters.Vision import Confidence_Severity, Confidence_Thresholds_Str
# Custom Lib.: AnyScan domain — the colour palette (Qt-free, the single source)
#   ../Parameters/Theme
from Parameters.Theme import (                                             # noqa: F401
    CONST_BG, CONST_CARD, CONST_CARD_BORDER, CONST_INK, CONST_INK_SOFT,
    CONST_INK_MUTE, CONST_LINE, CONST_CONTROL_BORDER, CONST_CONTROL_HOVER,
    CONST_CONTROL_HOVER_BORDER, CONST_INK_HOVER, CONST_INK_PRESSED, CONST_ON_INK,
    CONST_CONTROL_DISABLED_TEXT, CONST_CONTROL_DISABLED_BORDER, CONST_PRIMARY_DISABLED_FILL,
    CONST_PRIMARY_DISABLED_TEXT, CONST_SCRIM, CONST_SCRIM_ALPHA, Hex_To_Rgb, CONST_OK, CONST_OK_INK,
    CONST_BUSY_SCRIM, CONST_BUSY_SCRIM_ALPHA, CONST_BUSY_INK, CONST_BUSY_DIM_ALPHA,
    CONST_GRID_LINE, CONST_GRID_LINE_ALPHA, CONST_GRID_FILL, CONST_GRID_FILL_ALPHA,
    CONST_THUMB_HIGHLIGHT, CONST_THUMB_HIGHLIGHT_FILL_ALPHA, CONST_TOPBAR_DIVIDER, CONST_SCROLLBAR_HANDLE,
    CONST_OK_BORDER, CONST_WARN, CONST_WARN_INK, CONST_CONTROL_PRESSED, Label_Ground,
    CONST_OK_LABEL_GROUND, CONST_NOK_LABEL_GROUND, CONST_WARNING_BOX,
    CONST_INSPECTION_AREA, CONST_INSPECTION_AREA_EMPTY,
    CONST_WARN_BORDER, CONST_VIEWPORT, CONST_VIEWPORT_TEXT, CONST_LEGEND_MARK, CONST_BAND,
    CONST_BAND_LINE, CONST_BAND_TEXT, CONST_BAND_LINE_ALPHA, CONST_BAND_TEXT_ALPHA, CONST_CORNER_MOTIF,
    CONST_CORNER_MOTIF_ALPHA, CONST_LOGO_INK,
    CONST_LOG_WARNING, CONST_LOG_ERROR, Log_Level_Color, Status_Text_Color, Heatmap_Colors)

"""
Description:
    Initialization of constants.

    The console's Qt style/asset helpers and the NON-colour layout tokens. Every
    colour lives once in Parameters.Theme (Qt-free, so the annotation renderer reads
    the same palette); this module imports and re-exports them for the widgets, which
    still read them as Style.CONST_* — a hard-coded colour in a widget, or a second
    copy of one here, is how a design system stops being one.
"""
# Assets (logos, icon, optional fonts) live in App/assets/. Resolved from this
# file's location (src/UI/Utilities -> ../../../App/assets).
CONST_ASSETS = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'App', 'assets'))

CONST_GAP           = 16          # gap between cards, everywhere
CONST_MARK_GAP      = 32          # gap between brand marks and either side of the divider between them
# The top bar's AnyScan lockup height on a high-density display. On a low-density one Logo_Height grows it until the
# tagline is CONST_TYPE_FLOOR_LOW_DENSITY (design-decisions.md, "The header draws the delivered logo and sets its
# tagline as live text").
#   Unit [int] (logical px)
CONST_LOGO_HEIGHT   = 54
# Below this device pixel ratio a display is low density (a 1x monitor): Is_Low_Density.
#   Unit [float]
CONST_LOW_DENSITY_DPR = 1.5
# The smallest type on a low-density display: Font raises any smaller size to it there. At DPR 1 a
# regular-weight 7.5-8.5 pt text (10-11 px) had 0.02-0.05 of its ink at full contrast in Inter; at 9 pt
# (12 px) 0.12-0.19. A 2x display draws those sizes with 15-17 device px per em and keeps them.
#   Unit [float] (point size)
CONST_TYPE_FLOOR_LOW_DENSITY = 9.0

# Busy-indicator animation, driven by a QTimer in the viewport while the worker runs: one tick per step of the
# pixel icon (UI.Utilities.Pixel_Motif.Busy_Cells), which repaints only then. Kept here so the whole console's
# tunable values live in one place.
CONST_BUSY_TICK_MS  = 120         # a task icon steps every few ticks (Pixel_Motif.CONST_BUSY_STEPS)
# The analysis grid (Viewport_Cls.Start_Analysis): a repaint every 40 ms, 25 a second, the reference animation's rate
# (20) or a little above, so its 0.5 s crossing takes a dozen steps. The frame is cut into CONST_GRID_COLUMNS square
# cells across (40 px each on a 1920 px frame, about 24 px on the rig's screen), finer than the parts.
#   Unit [int] (ms) / [int] (cells)
CONST_GRID_TICK_MS  = 40
CONST_GRID_COLUMNS  = 48

# What an empty value slot shows. It is a placeholder, not prose: the em dash
# stays out of sentences and out of labels, and appears only where a number or a
# timestamp will later sit.
CONST_NO_VALUE      = '—'

CONST_TAGLINE = 'The camera sees, the model describes.'

# The top bar's lockup (Widgets.Logo_Lockup_Cls): the delivered logo without its tagline, which
# Example/UI/build_logo.py derives in the logo's own viewBox, and the tagline set as live text where the logo outlines
# it, in logo units: the pen origin (x, baseline y) and the font size. The outlined tagline's "T" starts at x 167.25,
# its cap top is at y 110.25 and its baseline at 128.0, a cap height of 17.75; Public Sans draws a cap height of
# 0.723 em (1446 of 2000 units) and starts its "T" 0.023 em right of the pen, so the size is 17.75 / 0.723 = 24.55
# and the pen origin x 167.25 - 0.023 x 24.55 = 166.69. test/UI/test_header.py holds the live tagline to the outlined
# one within 1 device px.
#   Unit [string] / [Vector<float> 1x2] / [float] (logo units)
CONST_LOGO_WORDMARK_FILE = 'anyscan-logo-wordmark.svg'
CONST_LOGO_TAGLINE_ORIGIN = (166.69, 128.0)
CONST_LOGO_TAGLINE_SIZE = 24.55
# The logo's viewBox height, the unit the tagline's size is a share of.
#   Unit [float] (logo units)
CONST_LOGO_VIEWBOX_HEIGHT = 140.0
# Where the logo's mark ends, for grid-fitting it on a 1x display (UI.Utilities.Grid_Fit): its ink ends at 140.0 units
# and the wordmark's starts at 165.5, so every shape left of 152 is the mark's.
#   Unit [float] (logo units)
CONST_LOGO_MARK_RIGHT = 152.0
# The mark's thin-gap threshold for Grid_Fit: 0, every edge to its own nearest pixel. Nearly every gap of the mark
# delivered 2026-10-18 is under Grid_Fit's 10 px at the header's height, and chaining their rounded widths drew it
# 71 x 69 px at 69 px with edges up to 2 px off; each edge alone keeps it 69 x 69 (72 x 72 at 72) and every edge within
# 0.5 px, at the cost of one 5 px bar beside two of 6 at 69 px (the owner's choice, 2026-10-18).
#   Unit [float] (px)
CONST_LOGO_MARK_THIN_PX = 0.0
# The empty space the lockup keeps right of the tagline's ink, near the logo's own (its ink ends 5.9 units inside
# its viewBox), so no anti-aliased edge is clipped. Ink_Insets takes it off the gap to the divider.
#   Unit [float] (logo units)
CONST_LOGO_MARGIN = 5.0

# The resolved UI/monospace font families. NOT CONST_*: Load_Fonts reassigns them
# once at startup to the nearest available faces — they are resolved state, not
# constants.
FONT_UI = 'Public Sans'  # resolved in Load_Fonts
FONT_MONO = 'Consolas'  # resolved in Load_Fonts

# The faces Load_Fonts tries, in order: the design's face first, then the nearest system ones.
# Also the font stacks of the architecture diagram (Example/UI/architecture_diagram.py), so the
# figure falls back the way the application does.
#   Unit [Tuple<string>]
CONST_FONT_UI_CANDIDATES = ('Public Sans', 'Segoe UI Variable Display', 'Segoe UI', 'Helvetica Neue', 'Arial')
CONST_FONT_MONO_CANDIDATES = ('JetBrains Mono', 'Cascadia Mono', 'Consolas', 'DejaVu Sans Mono', 'Courier New')

# The console's modular type scale (point sizes), smallest to largest. Every type token below
# names a STEP in this scale rather than a literal, so a size change is 'move to the next step',
# a real and uniform operation, and never a fresh number at the call site.
#   Unit [Vector<float>] (point sizes)
CONST_TYPE_SCALE = (9.5, 10.5, 11.5, 12.5, 14.0, 15.5, 16.5, 18.0)

# The LIVE Scene-Understanding type steps. The card title ('Scene Understanding') is the panel's
# heading and stays largest. Under it the background paragraph — the shared header, the
# background sentence and the object count together — is ONE label in ONE style: the object-label
# size in REGULAR weight, no part of it bold, so the sentence pair reads as one paragraph. Then
# each object is a two-level block — the label line ('Object N · Confidence …') at the same size
# but heavier, the description beneath it smaller and regular. The hierarchy is size and weight
# only — everything is CONST_INK. The label stays clearly larger and heavier than the description
# below it (14.0 DemiBold over 12.5 regular); the confidence suffix is one step DOWN from the name
# AND a lighter weight, so it reads as secondary metadata attached to the name.
#
# These are the LIVE sizes: the Scene-Understanding block is glanced at across a workbench, so it
# runs large. The History Info panel (below) uses SEPARATE, smaller tokens because it is read up
# close while comparing two images — keeping them apart means adjusting one distance cannot move
# the other.
#   Unit [float] (point size)
CONST_TYPE_SCENE_BACKGROUND = CONST_TYPE_SCALE[4]   # 14.0 — the background paragraph, == the label
CONST_TYPE_OBJECT_LABEL = CONST_TYPE_SCALE[4]       # 14.0
CONST_TYPE_OBJECT_CONFIDENCE = CONST_TYPE_SCALE[3]  # 12.5 — one step down from the label
CONST_TYPE_OBJECT_BODY = CONST_TYPE_SCALE[3]        # 12.5 — the description

# The HISTORY INFO-PANEL type steps. Read up close, so smaller than the Live sizes, and ordered
# strictly largest → smallest: heading, then the object label (bold, for list structure), then
# the body (the background paragraph AND the descriptions, one consistent size), then the
# smallest tier (the confidence suffix and the unscored-object note). The heading is the largest
# thing in the panel — everything sits below it. Separate from the Live tokens on purpose (see
# above), so the two cannot drift into each other.
#   Unit [float] (point size)
CONST_TYPE_INFO_HEADING = CONST_TYPE_SCALE[3]       # 12.5 — the panel heading, largest
CONST_TYPE_INFO_LABEL = CONST_TYPE_SCALE[2]         # 11.5 — object labels (bold), under heading
CONST_TYPE_INFO_BODY = CONST_TYPE_SCALE[1]          # 10.5 — background paragraph + descriptions
CONST_TYPE_INFO_META = CONST_TYPE_SCALE[0]          # 9.5  — confidence suffix + unscored note

# The Log-view row type size, so a long session stays legible at length. The timestamp and level
# render at this size in the monospace family (fixed-width, so the message column starts at a
# consistent x); the message at this size in the UI family.
#   Unit [float] (point size)
CONST_TYPE_LOG = CONST_TYPE_SCALE[2]                # 11.5 — the log row size

# The severity -> font-weight ramp, keyed by the log-level strings and SHARED by the Log view
# and the confidence colouring. Severity is carried by colour AND weight, never colour alone,
# because the WARNING amber (#b45309) and ERROR red (#b91c1c) collapse to nearly one colour
# under a red-green deficiency (measured ΔE ~8 in deuteranopia): the heavier weight keeps the
# two apart for a viewer who cannot rely on the hue. CSS weights mirror the QFont ones for the
# rich-text (HTML) confidence spans.
#   Unit [Dict<string, int>]
CONST_LEVEL_WEIGHTS = {'INFO': QFont.Normal, 'WARNING': QFont.DemiBold, 'ERROR': QFont.Bold}
CONST_LEVEL_CSS_WEIGHTS = {'INFO': 400, 'WARNING': 600, 'ERROR': 700}


def Scrim_Color() -> str:
    """
    Description:
        The scrim's stylesheet colour: the theme's scrim ink at the theme's scrim opacity.

    Returns:
        (1) parameter [string]: The colour as 'rgba(r, g, b, a)'.
    """

    return Token_Css(CONST_SCRIM, CONST_SCRIM_ALPHA)


def Token_Css(hex_color: str, alpha: float) -> str:
    """
    Description:
        A theme token at an opacity, as a stylesheet colour.

    Args:
        (1) hex_color [string]: The token, as '#rrggbb'.
        (2) alpha [float]: The opacity, 0..1.

    Returns:
        (1) parameter [string]: The colour as 'rgba(r, g, b, a)', a in 0..255.
    """

    r, g, b = Hex_To_Rgb(hex_color)
    return 'rgba(%d, %d, %d, %d)' % (r, g, b, int(round(255 * alpha)))


def Token_Color(hex_color: str, alpha: float = 1.0) -> QColor:
    """
    Description:
        A theme token as a QColor, at an opacity — so a painter never builds a colour from literal
        numbers (which is how a token's value gets hand-copied and then drifts from it).

    Args:
        (1) hex_color [string]: The token, as '#rrggbb'.
        (2) alpha [float]: The opacity, 0..1.

    Returns:
        (1) parameter [QColor(object)]: The colour.
    """

    r, g, b = Hex_To_Rgb(hex_color)
    return QColor(r, g, b, int(round(255 * alpha)))


def Log_Level_Weight(level: str) -> int:
    """
    Description:
        The QFont weight for a severity level, from the one shared ramp — so the Log view's
        level field and any confidence number at that severity carry the same weight.

    Args:
        (1) level [string]: The severity level ('INFO', 'WARNING' or 'ERROR').

    Returns:
        (1) parameter [int]: The QFont weight.
    """

    return CONST_LEVEL_WEIGHTS.get(level, QFont.Normal)


def Confidence_Number_Html(number: str, percent: tp.Optional[float],
                           Confidence_Thresholds_Str: Confidence_Thresholds_Str) -> str:
    """
    Description:
        A confidence number as rich text, coloured and weighted by its severity band so the
        number itself carries the warning/error state (the surrounding words stay the label's
        default ink). Reuses the log palette (Log_Level_Color) and the shared weight ramp,
        never a fresh literal. Only a WARNING or ERROR value is wrapped; a fine value (INFO) and
        an unscored value (None) are returned plain, so a passing or absent reading keeps the
        default colour and weight and no markup is emitted where nothing changes.

    Args:
        (1) number [string]: The already-formatted number (e.g. '73%').
        (2) percent [float]: Its value in percent (0..100), or None when unscored.
        (3) Confidence_Thresholds_Str [Confidence_Thresholds_Str(object)]: The thresholds in force.

    Returns:
        (1) parameter [string]: The number as an HTML span for WARNING/ERROR, else plain.
    """

    level = Confidence_Severity(percent, Confidence_Thresholds_Str)
    if percent is None or level == 'INFO':
        return number
    return '<span style="color: %s; font-weight: %d;">%s</span>' % (
        Log_Level_Color(level), CONST_LEVEL_CSS_WEIGHTS[level], number)


def Is_Low_Density(widget: tp.Optional[QWidget] = None) -> bool:
    """
    Description:
        Whether a widget is drawn on a low-density display: its device pixel ratio below
        CONST_LOW_DENSITY_DPR. This is the one density check; a style that differs by density asks it.
        Without a widget (Font, which builds a font before it is set on anything) it reads the
        application's ratio, which is what a widget reads before its window is shown.

        Note:
            The ratio is the widget's own (devicePixelRatioF), which Qt 5.15 takes from the screen of
            the widget's top-level window once that window has a native handle (it is shown). Before
            that — which is when the window builds its widgets — Qt returns the application's ratio,
            the highest of all screens, so a machine with a Retina and a 1x screen counts as high
            density. The answer is read once, where a style is built; nothing re-evaluates it when
            the window moves to a screen of another ratio.

    Args:
        (1) widget [QWidget(object)]: The widget the style is for; None for the application's ratio.

    Returns:
        (1) parameter [bool]: True below CONST_LOW_DENSITY_DPR.
    """

    if widget is not None:
        return widget.devicePixelRatioF() < CONST_LOW_DENSITY_DPR
    app = QApplication.instance()
    return app is not None and app.devicePixelRatio() < CONST_LOW_DENSITY_DPR


def Logo_Height(widget: QWidget) -> int:
    """
    Description:
        The top bar's lockup height for the display a widget is drawn on. On a high-density display it is
        CONST_LOGO_HEIGHT. On a low-density one (Is_Low_Density) it is the smallest whole height at which the
        logo's tagline (CONST_LOGO_TAGLINE_SIZE of the logo's 140 units) is CONST_TYPE_FLOOR_LOW_DENSITY in the
        widget's logical DPI, so the tagline keeps the logo's proportions at the size where live text is hinted:
        69 px at 96 dpi. At the logo's own 54 px the tagline is 7 pt, where neither its outlines nor live text are
        sharp at DPR 1 (0.009 and 0.011 of its ink at full contrast; 0.18 at 9 pt).

    Args:
        (1) widget [QWidget(object)]: The widget the lockup is placed in.

    Returns:
        (1) parameter [int]: The height in logical pixels.
    """

    if not Is_Low_Density(widget):
        return CONST_LOGO_HEIGHT
    floor_px = CONST_TYPE_FLOOR_LOW_DENSITY * widget.logicalDpiY() / 72.0
    return max(CONST_LOGO_HEIGHT, int(math.ceil(floor_px * CONST_LOGO_VIEWBOX_HEIGHT / CONST_LOGO_TAGLINE_SIZE)))


def Scroll_Style(framed: bool) -> str:
    """
    Description:
        The console's one scroll-area stylesheet: a slim, trackless vertical bar with a rounded
        handle. A framed area (the Live object list, the Log) sits in a hairline-bordered card
        panel; an unframed one (the History list) is transparent inside its card.

    Args:
        (1) framed [bool]: Draw the area's own hairline border and card background.

    Returns:
        (1) parameter [string]: The Qt stylesheet.
    """

    area = ('QScrollArea { border: 1px solid %s; background: %s; }'
            % (CONST_LINE, CONST_CARD) if framed else 'QScrollArea { border: none; background: transparent; }')
    return area + """
            QScrollBar:vertical { background: transparent; width: 9px; margin: 6px 3px; }
            QScrollBar::handle:vertical { background: %s;
                                          min-height: 30px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent; }
        """ % CONST_SCROLLBAR_HANDLE


def Load_Fonts() -> None:
    """
    Description:
        Register the bundled fonts and pick the faces. Public Sans and JetBrains Mono, what
        the design is drawn in, ship in App/assets/fonts/ as static Regular, Medium,
        SemiBold and Bold files (built by Example/UI/build_fonts.py), so every weight
        the UI requests has its own face on every platform. The candidate lists are
        the fallback for a missing directory: the nearest system face is chosen, which
        shifts the metrics and may merge weights (design-decisions.md, "The UI
        fonts are bundled").
    """

    global FONT_UI, FONT_MONO

    font_dir = os.path.join(CONST_ASSETS, 'fonts')
    if os.path.isdir(font_dir):
        for name in os.listdir(font_dir):
            if name.lower().endswith(('.ttf', '.otf')):
                QFontDatabase.addApplicationFont(os.path.join(font_dir, name))

    families = set(QFontDatabase().families())
    for candidate in CONST_FONT_UI_CANDIDATES:
        if candidate in families:
            FONT_UI = candidate
            break
    for candidate in CONST_FONT_MONO_CANDIDATES:
        if candidate in families:
            FONT_MONO = candidate
            break


def App_Icon() -> QIcon:
    """
    Description:
        The window, taskbar and Alt-Tab icon: anyscan-mark.ico, the mark on a transparent ground at every size
        from 16 to 256 px (Example/UI/build_logo.py renders each size), so Qt picks the nearest slot itself and
        a 256 px render is never squeezed into a 16 px title-bar slot. Without the file the icon is empty.

    Returns:
        (1) parameter [QIcon(object)]: The multi-size application icon.
    """

    ico = os.path.join(CONST_ASSETS, 'anyscan-mark.ico')
    return QIcon(ico) if os.path.isfile(ico) else QIcon()


def Load_Svg(name: str, height: int) -> QPixmap:
    """
    Description:
        Rasterize an SVG asset for the display it will actually be drawn on.
        A vector lockup drawn at height * devicePixelRatio and tagged with that
        ratio hands Qt exactly the pixels it needs, so the wordmark stays crisp on a
        125% or 150% display: the source is rendered rather than scaled, which keeps
        the type sharp at any size.

    Args:
        (1) name [string]: The .svg asset filename under App/assets/.
        (2) height [int]: The target logical height in pixels.

    Returns:
        (1) parameter [QPixmap(object)]: The rendered pixmap (null if the file is missing).
    """

    renderer = QSvgRenderer(os.path.join(CONST_ASSETS, name))
    if not renderer.isValid():
        return QPixmap()
    app = QApplication.instance()
    dpr = app.devicePixelRatio() if app else 1.0
    dpr = max(1.0, float(dpr))
    # Preserve the SVG's own aspect ratio: width follows from the viewBox, read as the real numbers it is.
    # defaultSize() truncates to whole units (the logo's 609.8 to 609), which squeezed it by 0.13 %.
    box = renderer.viewBoxF()
    ratio = box.width() / box.height() if box.height() else 1.0
    px_h = int(round(height * dpr))
    px_w = int(round(px_h * ratio))
    image = QImage(px_w, px_h, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    pix = QPixmap.fromImage(image)
    pix.setDevicePixelRatio(dpr)
    return pix


def Ink_Insets(pixmap: QPixmap) -> tp.Tuple[int, int]:
    """
    Description:
        The fully transparent columns at a pixmap's left and right edges, in logical pixels. A
        lockup's image keeps a margin around its artwork; subtracting it lets a layout space marks
        from their ink, which is the gap the eye sees, instead of from their image boxes.

    Args:
        (1) pixmap [QPixmap(object)]: The mark, tagged with its devicePixelRatio.

    Returns:
        (1) parameter [Vector<int> 1x2]: (left, right) inset in logical pixels, rounded; (0, 0) for a
                                         null or fully transparent pixmap.
    """

    if pixmap.isNull():
        return 0, 0
    image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
    pointer = image.constBits()
    pointer.setsize(image.byteCount())
    alpha = np.frombuffer(pointer, np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4)[:, :image.width(), 3]
    columns = np.flatnonzero(alpha.max(axis=0))
    if columns.size == 0:
        return 0, 0
    dpr = pixmap.devicePixelRatio()
    return (int(round(columns[0] / dpr)), int(round((image.width() - 1 - columns[-1]) / dpr)))


def Font(size: float, weight: int = QFont.Normal, mono: bool = False,
         tracking: float = 0.0) -> QFont:
    """
    Description:
        Build a font. `tracking` is percentage letter spacing, as in the CSS. On a low-density display
        (Is_Low_Density) a size below CONST_TYPE_FLOOR_LOW_DENSITY is raised to it; every UI font is
        built here, painted text included, so this is the one place the floor applies.

    Args:
        (1) size [float]: Point size.
        (2) weight [int]: QFont weight.
        (3) mono [bool]: Use the monospace family.
        (4) tracking [float]: Percentage letter spacing (0 = none).

    Returns:
        (1) parameter [QFont(object)]: The configured font.
    """

    if size < CONST_TYPE_FLOOR_LOW_DENSITY and Is_Low_Density():
        size = CONST_TYPE_FLOOR_LOW_DENSITY
    font = QFont(FONT_MONO if mono else FONT_UI)
    font.setPointSizeF(size)
    font.setWeight(weight)
    if tracking:
        font.setLetterSpacing(QFont.PercentageSpacing, 100 + tracking)
    return font


def Hairline(vertical: bool = True, length: tp.Optional[int] = None,
             color: str = CONST_LINE) -> QWidget:
    """
    Description:
        A one-pixel rule. QFrame.VLine draws from the widget palette and ignores a
        stylesheet colour, which is why hand-set frame lines come out the wrong
        shade or invisible; a plain filled QWidget is predictable.

    Args:
        (1) vertical [bool]: A vertical (True) or horizontal (False) rule.
        (2) length [int]: Optional fixed length for a vertical rule.
        (3) color [string]: The line colour.

    Returns:
        (1) parameter [QWidget(object)]: The rule widget.
    """

    line = QWidget()
    line.setObjectName('hairline')
    line.setStyleSheet('#hairline { background: %s; }' % color)
    if vertical:
        line.setFixedWidth(1)
        if length:
            line.setFixedHeight(length)
    else:
        line.setFixedHeight(1)
    return line


def Rgb_To_Qimage(rgb: tp.List[tp.List[int]]) -> QImage:
    """
    Description:
        An RGB ndarray (H, W, 3) as a QImage for the viewport to paint. This is the
        one place a frame crosses from the Qt-free exchange format into Qt.

        Note:
            QImage does not own the numpy buffer: it is a view over rgb.data with a
            3*w stride. .copy() detaches it so the frame survives rgb being garbage-
            collected, which otherwise tears the viewport or segfaults.

    Args:
        (1) rgb [Matrix<uint8> HxWx3]: The frame (RGB).

    Returns:
        (1) parameter [QImage(object)]: A detached QImage of the frame.
    """

    h, w = rgb.shape[:2]
    image = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
    return image.copy()


def Bgr_To_Qimage(bgr: tp.List[tp.List[int]]) -> QImage:
    """
    Description:
        A BGR ndarray (H, W, 3) as a QImage. The vision renderers (Draw_Annotated,
        Draw_Label_Mask) emit BGR, OpenCV's order; this is the crossing that lets the
        viewport show exactly the images the harness exports. The channels are reversed
        into a contiguous RGB buffer, then handed to Rgb_To_Qimage, which detaches it.

    Args:
        (1) bgr [Matrix<uint8> HxWx3]: The image (BGR).

    Returns:
        (1) parameter [QImage(object)]: A detached QImage of the image.
    """

    return Rgb_To_Qimage(np.ascontiguousarray(bgr[..., ::-1]))
