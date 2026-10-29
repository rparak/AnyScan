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
# File Name: JIC_SF_UI/Style.py
## =========================================================================== ##

# System (Default)
import math
import os
# Typing (Support for type hints)
import typing as tp
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtGui import QColor, QFont, QFontDatabase, QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QWidget
# JIC_SF_UI: the palette, re-exported so a widget reads every token as Style.CONST_*
from .Theme import *                                                       # noqa: F401,F403
from .Theme import Hex_To_Rgb, CONST_LINE, CONST_CARD, CONST_SCROLLBAR_HANDLE, CONST_SCRIM, CONST_SCRIM_ALPHA

"""
Description:
    Initialization of constants.

    The Qt side of the style: fonts, the type scale, the density check, tokens as Qt colours, the hairline and the
    scroll-area stylesheet, and the layout constants. Every colour lives once in Theme; a widget that names a colour
    by value, or a second copy of one here, is how a design system stops being one. Generalised from AnyScan's
    src/UI/Utilities/Style.py.
"""
# The assets the package draws: fonts/ and the logo SVGs. Resolved from this file; Set_Assets moves it.
#   Unit [string]
CONST_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')

# Spacing (logical px): the gap between cards everywhere, the window's outer margin and the gap between brand marks
# and either side of the rule between them (measured ink to ink, Ink_Insets).
#   Unit [int] (px)
CONST_GAP          = 16
CONST_PAGE_MARGIN  = 18
CONST_MARK_GAP     = 32
# A product lockup's height on a high-density display; Logo_Height grows it on a low-density one.
#   Unit [int] (px)
CONST_LOGO_HEIGHT  = 54
# Below this device pixel ratio a display is low density (a 1x monitor): Is_Low_Density is the ONE density check.
#   Unit [float]
CONST_LOW_DENSITY_DPR = 1.5
# The smallest type on a low-density display: Font raises any smaller size to it there (7.5-8.5 pt text at DPR 1
# has 0.02-0.05 of its ink at full contrast; 9 pt 0.12-0.19). A 2x display keeps the written sizes.
#   Unit [float] (pt)
CONST_TYPE_FLOOR_LOW_DENSITY = 9.0
# Animation ticks: a busy icon steps every CONST_BUSY_TICK_MS; the analysis grid repaints every CONST_GRID_TICK_MS
# and is CONST_GRID_COLUMNS square cells across the image.
#   Unit [int] (ms) / [int] (cells)
CONST_BUSY_TICK_MS = 120
CONST_GRID_TICK_MS = 40
CONST_GRID_COLUMNS = 48
# An empty value slot: a placeholder, not prose. The em dash appears only where a number or a time will sit.
#   Unit [string]
CONST_NO_VALUE = '—'

# The resolved families (Load_Fonts reassigns them): Public Sans for words, JetBrains Mono for machine values.
FONT_UI = 'Public Sans'
FONT_MONO = 'JetBrains Mono'
CONST_FONT_UI_CANDIDATES = ('Public Sans', 'Segoe UI Variable Display', 'Segoe UI', 'Helvetica Neue', 'Arial')
CONST_FONT_MONO_CANDIDATES = ('JetBrains Mono', 'Cascadia Mono', 'Consolas', 'DejaVu Sans Mono', 'Courier New')

# The content type scale (pt). Content (text the application produces and a person reads to decide something) takes
# a named step; chrome (labels around it) takes the per-widget sizes in references/typography.md.
#   Unit [Vector<float>] (pt)
CONST_TYPE_SCALE = (9.5, 10.5, 11.5, 12.5, 14.0, 15.5, 16.5, 18.0)
CONST_TYPE_HEADING = CONST_TYPE_SCALE[4]      # 14.0 a reading's lead paragraph and object labels (live, far)
CONST_TYPE_BODY = CONST_TYPE_SCALE[3]         # 12.5 descriptions (live, far)
CONST_TYPE_INFO_HEADING = CONST_TYPE_SCALE[3] # 12.5 the same content read up close: heading
CONST_TYPE_INFO_LABEL = CONST_TYPE_SCALE[2]   # 11.5 label
CONST_TYPE_INFO_BODY = CONST_TYPE_SCALE[1]    # 10.5 body
CONST_TYPE_INFO_META = CONST_TYPE_SCALE[0]    # 9.5 meta
CONST_TYPE_LOG = CONST_TYPE_SCALE[2]          # 11.5 a log row
# Severity carries a word, a colour AND a weight (the amber and the red collapse under deuteranopia, dE ~8).
#   Unit [Dict<string, int>]
CONST_LEVEL_WEIGHTS = {'INFO': QFont.Normal, 'WARNING': QFont.DemiBold, 'ERROR': QFont.Bold}
CONST_LEVEL_CSS_WEIGHTS = {'INFO': 400, 'WARNING': 600, 'ERROR': 700}


def Set_Assets(path: str) -> None:
    """
    Description:
        Point the package at another assets folder (fonts/ and the logos). Call before Load_Fonts.

    Args:
        (1) path [string]: The folder.
    """

    global CONST_ASSETS
    CONST_ASSETS = os.path.abspath(path)


def Asset(name: str) -> str:
    """
    Description:
        The path of an asset file.

    Args:
        (1) name [string]: The file name under the assets folder.

    Returns:
        (1) parameter [string]: The absolute path.
    """

    return os.path.join(CONST_ASSETS, name)


def Load_Fonts() -> None:
    """
    Description:
        Register the bundled static fonts (Regular, Medium, SemiBold, Bold of Public Sans and JetBrains Mono, so every
        weight the UI requests has its own face; a variable font would be synthesised by Qt 5) and pick the families.
        Call once, right after the QApplication is built and before any widget.
    """

    global FONT_UI, FONT_MONO
    font_dir = Asset('fonts')
    if os.path.isdir(font_dir):
        for name in sorted(os.listdir(font_dir)):
            if name.lower().endswith(('.ttf', '.otf')):
                QFontDatabase.addApplicationFont(os.path.join(font_dir, name))
    families = set(QFontDatabase().families())
    FONT_UI = next((c for c in CONST_FONT_UI_CANDIDATES if c in families), FONT_UI)
    FONT_MONO = next((c for c in CONST_FONT_MONO_CANDIDATES if c in families), FONT_MONO)


def Is_Low_Density(widget: tp.Optional[QWidget] = None) -> bool:
    """
    Description:
        Whether text is drawn on a low-density display (DPR below CONST_LOW_DENSITY_DPR). The one place density is
        decided; read when a widget is built (before its window is shown Qt 5 reports the application's ratio).

    Args:
        (1) widget [QWidget(object) or None]: The widget, or None for the application's ratio.

    Returns:
        (1) parameter [bool]: True below CONST_LOW_DENSITY_DPR.
    """

    if widget is not None:
        return widget.devicePixelRatioF() < CONST_LOW_DENSITY_DPR
    app = QApplication.instance()
    return app is not None and app.devicePixelRatio() < CONST_LOW_DENSITY_DPR


def Font(size: float, weight: int = QFont.Normal, mono: bool = False, tracking: float = 0.0) -> QFont:
    """
    Description:
        Build a font: every UI font, painted text included, is built here, so the 9 pt floor at DPR 1 applies once.

    Args:
        (1) size [float]: Point size.
        (2) weight [int]: QFont.Normal, Medium, DemiBold or Bold (the four bundled weights; no other).
        (3) mono [bool]: JetBrains Mono, for machine values, times and fixed-width columns.
        (4) tracking [float]: Letter spacing in percent (6 for uppercase chrome, -2 for titles).

    Returns:
        (1) parameter [QFont(object)]: The font.
    """

    if size < CONST_TYPE_FLOOR_LOW_DENSITY and Is_Low_Density():
        size = CONST_TYPE_FLOOR_LOW_DENSITY
    font = QFont(FONT_MONO if mono else FONT_UI)
    font.setPointSizeF(size)
    font.setWeight(weight)
    if tracking:
        font.setLetterSpacing(QFont.PercentageSpacing, 100 + tracking)
    return font


def Logo_Height(widget: QWidget, tagline_size: float = 0.0, viewbox_height: float = 1.0) -> int:
    """
    Description:
        A lockup's height for its display: CONST_LOGO_HEIGHT on a high-density one; on a low-density one the smallest
        whole height at which a live tagline (tagline_size of viewbox_height logo units) reaches the 9 pt floor.

    Args:
        (1) widget [QWidget(object)]: The widget the lockup is placed in.
        (2) tagline_size [float]: The tagline's size in logo units (0: no live tagline).
        (3) viewbox_height [float]: The logo's viewBox height.

    Returns:
        (1) parameter [int]: The height in logical px.
    """

    if not tagline_size or not Is_Low_Density(widget):
        return CONST_LOGO_HEIGHT
    floor_px = CONST_TYPE_FLOOR_LOW_DENSITY * widget.logicalDpiY() / 72.0
    return max(CONST_LOGO_HEIGHT, int(math.ceil(floor_px * viewbox_height / tagline_size)))


def Token_Color(hex_color: str, alpha: float = 1.0) -> QColor:
    """
    Description:
        A theme token as a QColor at an opacity: a painter never builds a colour from literal numbers.

    Args:
        (1) hex_color [string]: The token.
        (2) alpha [float]: The opacity 0..1, itself a named theme constant.

    Returns:
        (1) parameter [QColor(object)]: The colour.
    """

    r, g, b = Hex_To_Rgb(hex_color)
    return QColor(r, g, b, int(round(255 * alpha)))


def Token_Css(hex_color: str, alpha: float) -> str:
    """
    Description:
        A theme token at an opacity, as a stylesheet colour.

    Args:
        (1) hex_color [string]: The token.
        (2) alpha [float]: The opacity 0..1.

    Returns:
        (1) parameter [string]: 'rgba(r, g, b, a)', a in 0..255.
    """

    r, g, b = Hex_To_Rgb(hex_color)
    return 'rgba(%d, %d, %d, %d)' % (r, g, b, int(round(255 * alpha)))


def Scrim_Color() -> str:
    """
    Description:
        The modal scrim's stylesheet colour.

    Returns:
        (1) parameter [string]: The colour.
    """

    return Token_Css(CONST_SCRIM, CONST_SCRIM_ALPHA)


def Log_Level_Weight(level: str) -> int:
    """
    Description:
        The QFont weight of a severity, from the one ramp the log and any number at that severity share.

    Args:
        (1) level [string]: 'INFO', 'WARNING' or 'ERROR'.

    Returns:
        (1) parameter [int]: The weight.
    """

    return CONST_LEVEL_WEIGHTS.get(level, QFont.Normal)


def Hairline(vertical: bool = True, length: tp.Optional[int] = None, color: str = CONST_LINE) -> QWidget:
    """
    Description:
        A 1 px rule. QFrame.VLine paints from the palette and ignores a stylesheet colour; a filled QWidget is exact.

    Args:
        (1) vertical [bool]: Vertical (True) or horizontal.
        (2) length [int or None]: A vertical rule's fixed length.
        (3) color [string]: The colour (a token, or a Token_Css value).

    Returns:
        (1) parameter [QWidget(object)]: The rule.
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


def Scroll_Style(framed: bool) -> str:
    """
    Description:
        The one scroll-area stylesheet: a slim trackless bar with a square periwinkle handle; a framed area sits in a
        hairline border on the card fill.

    Args:
        (1) framed [bool]: Draw the area's own hairline border.

    Returns:
        (1) parameter [string]: The stylesheet.
    """

    area = ('QScrollArea { border: 1px solid %s; background: %s; }' % (CONST_LINE, CONST_CARD) if framed
            else 'QScrollArea { border: none; background: transparent; }')
    return area + """
        QScrollBar:vertical { background: transparent; width: 9px; margin: 6px 3px; }
        QScrollBar::handle:vertical { background: %s; min-height: 30px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
    """ % CONST_SCROLLBAR_HANDLE


def Ink_Insets(pixmap: QPixmap) -> tp.Tuple[int, int]:
    """
    Description:
        The fully transparent columns at a render's left and right, in logical px: a layout spaces marks from their
        ink, the gap the eye sees, not from their image boxes.

    Args:
        (1) pixmap [QPixmap(object)]: A render tagged with its devicePixelRatio.

    Returns:
        (1) parameter [Vector<int> 1x2]: (left, right) insets; (0, 0) for an empty render.
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
    return int(round(columns[0] / dpr)), int(round((image.width() - 1 - columns[-1]) / dpr))


def Rgb_To_Qimage(rgb: np.ndarray) -> QImage:
    """
    Description:
        An RGB array (H, W, 3) as a detached QImage (the copy outlives the array).

    Args:
        (1) rgb [Matrix<uint8> HxWx3]: The image.

    Returns:
        (1) parameter [QImage(object)]: The image.
    """

    rgb = np.ascontiguousarray(rgb)
    h, w = rgb.shape[:2]
    return QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()


def Bgr_To_Qimage(bgr: np.ndarray) -> QImage:
    """
    Description:
        A BGR array (OpenCV's order) as a detached QImage.

    Args:
        (1) bgr [Matrix<uint8> HxWx3]: The image.

    Returns:
        (1) parameter [QImage(object)]: The image.
    """

    return Rgb_To_Qimage(bgr[..., ::-1])
