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
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontDatabase, QIcon, QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QWidget

"""
Description:
    Initialization of constants.

    The console's design tokens and the small Qt style/asset helpers. The colour
    and layout tokens mirror the :root block of the approved web build one for one
    — change a value here, never in a widget: a hard-coded colour in a widget is
    how a design system stops being one.
"""
# Assets (logos, icon, optional fonts) live in App/assets/. Resolved from this
# file's location (src/UI/Utilities -> ../../../App/assets).
CONST_ASSETS = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'App', 'assets'))

CONST_BG            = '#eceded'   # page background
CONST_CARD          = '#ffffff'   # card fill
CONST_CARD_BORDER   = '#e8e8ea'   # card outline
CONST_INK           = '#16181d'   # primary text, and the primary button
CONST_INK_SOFT      = '#3f434b'   # secondary text, object sentences
CONST_INK_MUTE      = '#8a8f98'   # labels, empty states, disclaimer
CONST_LINE          = '#edeef0'   # dividers

CONST_BRAND         = '#ff005c'   # EDIH-DIGIMAT magenta: object 1 and focus only
CONST_OK            = '#16a34a'   # connected, pass
CONST_OK_INK        = '#15803d'
CONST_OK_SOFT       = '#f2faf5'
CONST_OK_BORDER     = '#cfe9d8'
CONST_WARN          = '#d97706'   # degraded but working
CONST_WARN_INK      = '#b45309'
CONST_WARN_SOFT     = '#fdf8ef'
CONST_WARN_BORDER   = '#f3e2c3'

CONST_VIEWPORT      = '#1e1f21'   # the one dark surface in the console
CONST_VIEWPORT_TEXT = '#71767d'

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

# One colour pair per detection index, shared by the frame overlay and the text.
# `box` is the stroke on the dark viewport; `ink` is a darkened twin of the same
# hue for type on white, because a saturated stroke colour set as 14.5px text
# falls below readable contrast. Green, red and amber are deliberately absent:
# here they mean pass, fail and degraded. An object numbered 3 is not 'the good one'.
CONST_INDEX_COLORS = [
    ('#ff005c', '#b3003f'),
    ('#0ea5e9', '#0369a1'),
    ('#7c3aed', '#5b21b6'),
    ('#14b8a6', '#0f766e'),
    ('#6366f1', '#4338ca'),
    ('#d946ef', '#a21caf'),
]

CONST_TAGLINE = 'The camera sees, the model describes.'

# The resolved UI/monospace font families. NOT CONST_*: Load_Fonts reassigns them
# once at startup to the nearest available faces — they are resolved state, not
# constants.
FONT_UI = 'Inter'       # resolved in Load_Fonts
FONT_MONO = 'Consolas'  # resolved in Load_Fonts


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

    f = QFont(FONT_MONO if mono else FONT_UI)
    f.setPointSizeF(size)
    f.setWeight(weight)
    if tracking:
        f.setLetterSpacing(QFont.PercentageSpacing, 100 + tracking)
    return f


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
