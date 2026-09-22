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
# File Name: ../UI/Utilities/Style.py
## =========================================================================== ##

# System (Default)
import os
# Typing (Support for type hints)
import typing as tp
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontDatabase, QIcon, QImage, QPixmap, QPainter
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QApplication, QWidget
# Custom Lib.: AnyScan domain — the confidence severity bands (Qt-free)
#   ../Parameters/Vision
from Parameters.Vision import Confidence_Severity
# Custom Lib.: AnyScan domain — the colour palette (Qt-free, the single source)
#   ../Parameters/Theme
from Parameters.Theme import (                                             # noqa: F401
    CONST_BG, CONST_CARD, CONST_CARD_BORDER, CONST_INK, CONST_INK_SOFT,
    CONST_INK_MUTE, CONST_LINE, CONST_BRAND, CONST_OK, CONST_OK_INK,
    CONST_OK_SOFT, CONST_OK_BORDER, CONST_WARN, CONST_WARN_INK, CONST_WARN_SOFT,
    CONST_WARN_BORDER, CONST_VIEWPORT, CONST_VIEWPORT_TEXT, CONST_BAND,
    CONST_BAND_LINE, CONST_BAND_TEXT,
    CONST_LOG_INFO, CONST_LOG_WARNING, CONST_LOG_ERROR, Log_Level_Color)

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

CONST_RADIUS_CARD   = 18
CONST_RADIUS_BTN    = 11
CONST_GAP           = 16          # gap between cards, everywhere

# Busy-indicator animation, driven by a QTimer in the viewport while the worker
# runs. Kept here so the whole console's tunable values live in one place.
CONST_BUSY_TICK_MS  = 33          # ~30 fps repaint
CONST_BUSY_SPIN_DEG = 6           # arc rotation per tick

# What an empty value slot shows. It is a placeholder, not prose: the em dash
# stays out of sentences and out of labels, and appears only where a number or a
# timestamp will later sit.
CONST_NO_VALUE      = '—'

CONST_TAGLINE = 'The camera sees, the model describes.'

# The resolved UI/monospace font families. NOT CONST_*: Load_Fonts reassigns them
# once at startup to the nearest available faces — they are resolved state, not
# constants.
FONT_UI = 'Inter'       # resolved in Load_Fonts
FONT_MONO = 'Consolas'  # resolved in Load_Fonts

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


def Confidence_Number_Html(number: str, percent: tp.Optional[float]) -> str:
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

    Returns:
        (1) parameter [string]: The number as an HTML span for WARNING/ERROR, else plain.
    """

    level = Confidence_Severity(percent)
    if percent is None or level == 'INFO':
        return number
    return '<span style="color: %s; font-weight: %d;">%s</span>' % (
        Log_Level_Color(level), CONST_LEVEL_CSS_WEIGHTS[level], number)


def Load_Fonts() -> None:
    """
    Description:
        Pick the closest available faces. Inter and JetBrains Mono are what the
        design is drawn in. Drop the .ttf files into App/assets/fonts/ and they
        are used; otherwise the nearest system face is chosen, which shifts the
        metrics slightly but keeps the layout intact.
    """

    global FONT_UI, FONT_MONO

    font_dir = os.path.join(CONST_ASSETS, 'fonts')
    if os.path.isdir(font_dir):
        for name in os.listdir(font_dir):
            if name.lower().endswith(('.ttf', '.otf')):
                QFontDatabase.addApplicationFont(os.path.join(font_dir, name))

    families = set(QFontDatabase().families())
    for candidate in ('Inter', 'Segoe UI Variable Display', 'Segoe UI',
                      'Helvetica Neue', 'Arial'):
        if candidate in families:
            FONT_UI = candidate
            break
    for candidate in ('JetBrains Mono', 'Cascadia Mono', 'Consolas',
                      'DejaVu Sans Mono', 'Courier New'):
        if candidate in families:
            FONT_MONO = candidate
            break


def App_Icon() -> QIcon:
    """
    Description:
        The window, taskbar and Alt-Tab icon. Several explicit sizes are
        registered rather than one large pixmap: Qt picks the nearest and scales,
        and a 256px render squeezed into a 16px title-bar slot loses the shape.

    Returns:
        (1) parameter [QIcon(object)]: The multi-size application icon.
    """

    # The .ico already carries every size (16…256) on the indigo brand ground, so
    # Qt loads it whole and picks the nearest slot itself — no manual downscaling.
    ico = os.path.join(CONST_ASSETS, 'anyscan-mark-white.ico')
    if os.path.isfile(ico):
        return QIcon(ico)

    # Fallback: rasterize the nearest available mark into explicit sizes, so a
    # 256px render is never squeezed straight into a 16px title-bar slot.
    icon = QIcon()
    for name in ('icon.png', 'anyscan-mark.png'):
        source = QPixmap(os.path.join(CONST_ASSETS, name))
        if not source.isNull():
            break
    else:
        return icon
    for size in (16, 20, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(source.scaled(size, size, Qt.KeepAspectRatio,
                                     Qt.SmoothTransformation))
    return icon


def Load_Logo(name: str, height: int) -> QPixmap:
    """
    Description:
        Load a logo and scale it for the display it will actually be drawn on.
        Scaling to height * devicePixelRatio and tagging the pixmap with that ratio
        hands Qt the pixels it needs and it draws them one to one, so the logo is
        crisp on a 125% or 150% display.

    Args:
        (1) name [string]: The asset filename under App/assets/.
        (2) height [int]: The target logical height in pixels.

    Returns:
        (1) parameter [QPixmap(object)]: The scaled pixmap (null if the file is missing).
    """

    pix = QPixmap(os.path.join(CONST_ASSETS, name))
    if pix.isNull():
        return pix
    app = QApplication.instance()
    dpr = app.devicePixelRatio() if app else 1.0
    dpr = max(1.0, float(dpr))
    scaled = pix.scaledToHeight(int(round(height * dpr)), Qt.SmoothTransformation)
    scaled.setDevicePixelRatio(dpr)
    return scaled


def Load_Svg(name: str, height: int) -> QPixmap:
    """
    Description:
        Rasterize an SVG asset for the display it will actually be drawn on.
        A vector lockup drawn at height * devicePixelRatio and tagged with that
        ratio hands Qt exactly the pixels it needs, so the wordmark stays crisp on a
        125% or 150% display — the same DPI handling as Load_Logo, but the source is
        rendered rather than scaled, which keeps the type sharp at any size.

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
    # Preserve the SVG's own aspect ratio: width follows from the viewBox.
    size = renderer.defaultSize()
    ratio = size.width() / float(size.height()) if size.height() else 1.0
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


def Font(size: float, weight: int = QFont.Normal, mono: bool = False,
         tracking: float = 0.0) -> QFont:
    """
    Description:
        Build a font. `tracking` is percentage letter spacing, as in the CSS.

    Args:
        (1) size [float]: Point size.
        (2) weight [int]: QFont weight.
        (3) mono [bool]: Use the monospace family.
        (4) tracking [float]: Percentage letter spacing (0 = none).

    Returns:
        (1) parameter [QFont(object)]: The configured font.
    """

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
