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
# File Name: ../test/UI/test_header.py
## =========================================================================== ##

# System (Default)
import dataclasses
import math
import os
import subprocess
import sys
# Qt must never open a window during tests: the offscreen platform renders without a display.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Typing (Support for type hints)
import typing as tp
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import QPoint, QRect
from PyQt5.QtGui import QFontInfo, QImage, QPainter, QRawFont
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
# Custom Lib.: AnyScan UI — the main window
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
# Custom Lib.: AnyScan UI — the lockup the top bar shows
#   ../UI/Widgets
from UI.Widgets import Logo_Lockup_Cls
# Custom Lib.: AnyScan UI — the logo renderer and the fonts
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
# Custom Lib.: AnyScan — the one configuration layer
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    The top bar's brand group — the AnyScan lockup, a divider, the JIC mark — measured from a grab of
    the real header: the gaps are the space the eye sees, from the lockup's rightmost ink to the divider
    and from the divider to the JIC mark's first ink, found in the grabbed pixels, not in the SVG.

    The lockup is the delivered logo without its tagline (an SVG) and the tagline as live text where the logo
    outlines it (design-decisions.md, "The header draws the delivered logo and sets its tagline as live
    text"). It must draw as the outlined logo (images/anyscan-logo.svg) does at the same height, its tagline in the
    bundled Public Sans, and at DPR 1 be tall enough that the tagline is 9 pt and hinted. Each is measured here in
    the grabbed pixels against a render of the outlined logo at the same height.

    The lockup's height follows the display's density (Style.Logo_Height).

    The module runs at the session's device pixel ratio (1 offscreen) and runs itself once more at DPR 2 in a
    fresh interpreter, so the height, the gaps and the lockup's layout are measured at both ratios.
"""
CONST_CONFIGURATION = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)
# The chosen gap (design-decisions.md, "The logo's text is outlined"): the funding band's 32 px
# around its divider. Pinned here, so a change of the constant is a change of this decision.
#   Unit [px]
CONST_EXPECTED_GAP = 32
# A pixel is ink when it differs from the header background by more than this (sum over R, G, B).
#   Unit [-]
CONST_INK_THRESHOLD = 30
# The logo's height on a high-density display, and the share of it that is ink: the mark's corners fill the
# 140-unit viewBox from top to bottom. On a low-density display the height puts the tagline, 24.55 of those 140
# units, at 9 pt in the display's logical DPI (rounded up to a whole pixel).
#   Unit [px] / [-] / [logo units] / [pt]
CONST_LOGO_HEIGHT_HIGH_DENSITY = 54
# The JIC Smart Factory logo's height over the AnyScan lockup's: 26 px beside 54 px.
#   Unit [-]
CONST_JIC_SHARE = 26.0 / 54.0
CONST_LOGO_INK_SHARE = 1.0
CONST_LOGO_UNITS = 140.0
CONST_TAGLINE_UNITS = 24.55
CONST_TAGLINE_PT = 9.0
# How far the grabbed ink height may differ from that share: one anti-aliased row at the top and one at
# the bottom.
#   Unit [px]
CONST_INK_HEIGHT_TOLERANCE = 2
# The ratio the second run uses, standing in for a 2x (Retina) display.
#   Unit [-]
CONST_HIGH_DENSITY_SCALE = '2'
# Where the lockup's parts are told apart, in logo units: the wordmark starts right of x = 152 (the mark's ink
# ends at 139.9, the wordmark's starts at 165.5), and the live tagline right of x = 524 (the wordmark's ink ends at
# 511.5, the tagline's pen is at 537.1). The wordmark's first glyph ("A") is read over its first 30 units, which hold
# its apex; the tagline's ("T") over its first 0.45 em, which holds its stem and stops short of the "h".
#   Unit [logo units] / [em]
CONST_TEXT_LEFT_UNITS = 152.0
# The wordmark is read above y = 107.5 and the tagline below it (the wordmark's "y" ends at 105.1, the tagline's
# capitals start at 109.9). The wordmark's first glyph ("A") is read over its first 30 units, which hold its apex;
# the tagline's ("T") over its first 0.45 em, which holds its stem and stops short of the "h".
#   Unit [logo units] / [em]
CONST_LINE_SPLIT_UNITS = 107.5
CONST_WORDMARK_GLYPH_UNITS = 30.0
CONST_TAGLINE_GLYPH_EMS = 0.45
# The face the tagline must draw: its family and its file.
#   Unit [Tuple<string> 1x2]
CONST_TAGLINE_FACE = ('Public Sans', 'PublicSans-Regular.ttf')
# Where the live lockup may differ from the outlined logo: every offset within 1 px (device px).
#   Unit [px]
CONST_LOCKUP_TOLERANCE = 1.0
# The tagline's full-contrast ink share at DPR 1 (the low-density report's FCI: of the ink samples, each
# colour channel of each pixel at coverage >= 0.10, the share at >= 0.90), at least. Measured in this suite
# (offscreen, 100 dpi, the lockup 72 px, the tagline 9 pt at 13 px): 0.179 live, 0.147 for the logo's outlined
# tagline at the same height. At the logo's 54 px the outlined tagline is 0.009 and live text 0.011, which is why the
# lockup grows on a low-density display. The floor is the earlier logo's, kept.
#   Unit [-]
CONST_TAGLINE_FCI_FLOOR = 0.15


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """
    A single offscreen QApplication for the module, with the bundled fonts loaded as the application
    loads them: the lockup's tagline is set in Public Sans.
    """
    app = QApplication.instance() or QApplication([])
    Style.Load_Fonts()
    return app


def _Pixels(image: QImage) -> np.ndarray:
    """
    Description:
        An image's RGB pixels as an array.

    Args:
        (1) image [QImage(object)]: The image.

    Returns:
        (1) parameter [Matrix<int> HxWx3]: Its pixels, in R, G, B order.
    """

    image = image.convertToFormat(QImage.Format_ARGB32)
    pointer = image.constBits()
    pointer.setsize(image.byteCount())
    return np.frombuffer(pointer, np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4)[:, :image.width(), 2::-1].astype(int)


def _Rgb(colour: str) -> np.ndarray:
    """
    Description:
        A '#rrggbb' colour as an array.

    Args:
        (1) colour [string]: The colour.

    Returns:
        (1) parameter [Vector<int> 1x3]: R, G, B.
    """

    return np.array([int(colour[i:i + 2], 16) for i in (1, 3, 5)])


def _Shown_Window(qt_app: QApplication, width: int) -> AnyScan_Window_Cls:
    """
    Description:
        The main window, shown at a width and 900 px tall, laid out and painted.

    Args:
        (1) qt_app [QApplication(object)]: The application.
        (2) width [int]: The window width; 0 for its minimum.

    Returns:
        (1) parameter [AnyScan_Window_Cls(object)]: The window.
    """

    window = AnyScan_Window_Cls(Configuration_Str=CONST_CONFIGURATION)
    window.show()
    window.resize(width or window.minimumSizeHint().width(), 900)
    for _ in range(20):
        qt_app.processEvents()
    return window


def _Grab(window: QWidget, widget: QWidget) -> tp.Tuple[np.ndarray, float]:
    """
    Description:
        A widget as the shown window draws it.

    Args:
        (1) window [QWidget(object)]: The shown window.
        (2) widget [QWidget(object)]: The widget in it.

    Returns:
        (1) parameter [Tuple<Matrix<int> HxWx3, float>]: Its RGB pixels and their device pixel ratio.
    """

    grab = window.grab(QRect(widget.mapTo(window, QPoint(0, 0)), widget.size()))
    return _Pixels(grab.toImage()), grab.devicePixelRatio()


@pytest.mark.parametrize('width', [0, 1720])
def test_the_brand_marks_are_spaced_by_the_brand_gap_from_ink(qt_app, width) -> None:
    """
    Description:
        In the shown header, at the minimum window width and at 1720 px, the lockup's rightmost ink sits
        CONST_EXPECTED_GAP (±1 px) left of the divider, and the JIC mark's first ink CONST_EXPECTED_GAP
        right of it. A margin inside an image is space the eye sees, so it counts.
    """

    window = _Shown_Window(qt_app, width)
    logo = window.findChild(Logo_Lockup_Cls)
    jic = window.findChild(QWidget, 'jicLogo')
    bar = logo.parentWidget()
    divider = [w for w in bar.findChildren(QWidget) if w.objectName() == 'hairline' and w.parentWidget() is bar][0]

    pixels, ratio = _Grab(window, bar)
    ink = np.abs(pixels - pixels[1, 1]).sum(axis=2) > CONST_INK_THRESHOLD

    def Left(widget: QWidget) -> int:
        return widget.mapTo(bar, QPoint(0, 0)).x()

    logo_columns = np.flatnonzero(ink[:, int(Left(logo) * ratio):int((Left(logo) + logo.width()) * ratio)].any(axis=0))
    logo_ink_right = Left(logo) + (logo_columns[-1] + 1) / ratio
    jic_columns = np.flatnonzero(ink[:, int(Left(jic) * ratio):int((Left(jic) + jic.width()) * ratio)].any(axis=0))
    jic_ink_left = Left(jic) + jic_columns[0] / ratio

    gap = CONST_EXPECTED_GAP
    assert abs((Left(divider) - logo_ink_right) - gap) <= 1, \
        'logo ink -> divider is %.1f px, expected %d' % (Left(divider) - logo_ink_right, gap)
    assert abs((jic_ink_left - (Left(divider) + divider.width())) - gap) <= 1, \
        'divider -> JIC ink is %.1f px, expected %d' % (jic_ink_left - Left(divider) - divider.width(), gap)
    window.close()


def _Shown_Logo(qt_app: QApplication) -> tp.Tuple[AnyScan_Window_Cls, Logo_Lockup_Cls, float]:
    """
    Description:
        A shown window's header lockup, and the height of its ink as grabbed from the window.

    Args:
        (1) qt_app [QApplication(object)]: The application.

    Returns:
        (1) parameter [Tuple<AnyScan_Window_Cls, Logo_Lockup_Cls, float>]: The window, the lockup and the
                                                                         ink height in logical pixels.
    """

    window = _Shown_Window(qt_app, 1720)
    logo = window.findChild(Logo_Lockup_Cls)
    pixels, ratio = _Grab(window, logo)
    rows = np.flatnonzero((np.abs(pixels - pixels[0, -1]).sum(axis=2) > CONST_INK_THRESHOLD).any(axis=1))
    return window, logo, (rows[-1] + 1 - rows[0]) / ratio


def test_the_logo_puts_its_tagline_at_9_pt_on_a_low_density_display(qt_app) -> None:
    """
    Description:
        Below DPR 1.5 the header lockup is as tall as it must be for the logo's tagline to be CONST_TAGLINE_PT in the
        widget's logical DPI: the widget is that many logical pixels, and the ink grabbed from the window spans the
        logo's ink share of it (±CONST_INK_HEIGHT_TOLERANCE).
    """

    if qt_app.devicePixelRatio() >= Style.CONST_LOW_DENSITY_DPR:
        pytest.skip('this run is at DPR %g; the low-density logo is measured in the DPR 1 run'
                    % qt_app.devicePixelRatio())
    window, logo, ink = _Shown_Logo(qt_app)
    expected = int(math.ceil(CONST_TAGLINE_PT * logo.logicalDpiY() / 72.0 * CONST_LOGO_UNITS / CONST_TAGLINE_UNITS))
    assert logo.height() == expected
    assert abs(ink - expected * CONST_LOGO_INK_SHARE) <= CONST_INK_HEIGHT_TOLERANCE, 'logo ink is %.1f px tall' % ink
    window.close()


def test_the_logo_is_54_px_on_a_high_density_display(qt_app) -> None:
    """
    Description:
        At DPR 1.5 and above the header lockup is 54 px tall: the widget is 54 logical pixels, and the grabbed ink
        spans the ink share of 54 px.
    """

    if qt_app.devicePixelRatio() < Style.CONST_LOW_DENSITY_DPR:
        pytest.skip('this run is at DPR %g; the high-density logo is measured in the DPR 2 run'
                    % qt_app.devicePixelRatio())
    window, logo, ink = _Shown_Logo(qt_app)
    assert logo.height() == CONST_LOGO_HEIGHT_HIGH_DENSITY
    assert abs(ink - CONST_LOGO_HEIGHT_HIGH_DENSITY * CONST_LOGO_INK_SHARE) <= CONST_INK_HEIGHT_TOLERANCE, \
        'logo ink is %.1f px tall' % ink
    window.close()


def test_the_jic_logo_keeps_its_share_of_the_lockup(qt_app) -> None:
    """
    Description:
        The JIC Smart Factory logo is CONST_JIC_SHARE of the AnyScan lockup's height at this run's density: 26 px
        beside the 54 px lockup, and scaled with it where a low-density display grows the lockup (72 px offscreen),
        so the pair keeps its proportions. Read from the shown header's JIC logo widget, in logical pixels.
    """

    window, logo, _ = _Shown_Logo(qt_app)
    jic = window.findChild(QWidget, 'jicLogo')
    assert abs(jic.height() - CONST_JIC_SHARE * logo.height()) <= 0.5, (jic.height(), logo.height())
    window.close()


def _Outlined(height: int, ground: np.ndarray) -> np.ndarray:
    """
    Description:
        The outlined logo (images/anyscan-logo.svg, as App/assets carries it) rendered at a height the way
        the top bar rendered it, composited on a ground: the reference the live lockup is held to.

    Args:
        (1) height [int]: The height in logical pixels.
        (2) ground [Vector<int> 1x3]: The background's R, G, B.

    Returns:
        (1) parameter [Matrix<float> HxWx3]: The RGB pixels.
    """

    image = Style.Load_Svg('anyscan-logo.svg', height).toImage().convertToFormat(QImage.Format_ARGB32_Premultiplied)
    pointer = image.constBits()
    pointer.setsize(image.byteCount())
    bgra = np.frombuffer(pointer, np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4)[:, :image.width()].astype(float)
    alpha = bgra[..., 3:4] / 255.0
    return bgra[..., 2::-1] + (1.0 - alpha) * ground


def _Line_Features(pixels: np.ndarray, ground: np.ndarray, left: int, right: int, window: int) -> tp.Dict[str, float]:
    """
    Description:
        One line of the lockup's text, in device pixels from the lockup's top-left corner: its first glyph's left
        edge, cap top and baseline (read over the glyph's first `window` columns), its cap height, its rightmost
        ink, and its full-contrast ink share (FCI), each edge read to a fraction of a pixel from the anti-aliased
        coverage of the logo's colour.

    Args:
        (1) pixels [Matrix HxWx3]: The lockup's RGB pixels.
        (2) ground [Vector<float> 1x3]: The ground's R, G, B.
        (3 - 4) left, right [int]: The columns the line lies in.
        (5) window [int]: How many columns of the first glyph are read.

    Returns:
        (1) parameter [Dict<string, float>]: 'left', 'top', 'baseline', 'cap', 'right', 'fci'.
    """

    coverage = np.clip((ground - pixels[:, left:right]) / (ground - _Rgb(Style.CONST_LOGO_INK)), 0.0, 1.0)
    mean = coverage.mean(axis=2)
    columns = mean.max(axis=0)
    first = np.flatnonzero(columns >= 0.1)[0]
    last = np.flatnonzero(columns >= 0.1)[-1]
    profile = mean[:, first:first + window].max(axis=1)
    rows = np.flatnonzero(profile >= 0.1)
    top = rows[0] + 1.0 - profile[rows[0]]
    baseline = rows[-1] + profile[rows[-1]]
    samples = coverage >= 0.1
    return {'left': left + first + 1.0 - columns[first], 'top': top, 'baseline': baseline, 'cap': baseline - top,
            'right': left + last + columns[last], 'fci': float((coverage >= 0.9).sum()) / max(1, samples.sum())}


def _Lockup_Features(pixels: np.ndarray, ratio: float, height: int, tagline_px: float) -> tp.Dict[str, float]:
    """
    Description:
        Where the lockup's parts are, in device pixels from its top-left corner: the mark's ink left and top
        edges, and the wordmark's and the tagline's features (_Line_Features), named '<part>_<feature>'.

    Args:
        (1) pixels [Matrix HxWx3]: The lockup's RGB pixels on its ground (pixels[0, -1] is ground).
        (2) ratio [float]: Their device pixel ratio.
        (3) height [int]: The lockup's height in logical pixels.
        (4) tagline_px [float]: The tagline's pixel size, in device pixels.

    Returns:
        (1) parameter [Dict<string, float>]: The features.
    """

    box = QSvgRenderer(os.path.join(Style.CONST_ASSETS, Style.CONST_LOGO_WORDMARK_FILE)).viewBoxF()
    scale = height * ratio / box.height()
    split_x = int((CONST_TEXT_LEFT_UNITS - box.x()) * scale)
    ground = pixels[0, -1].astype(float)
    ink = np.abs(pixels - ground).sum(axis=2) > CONST_INK_THRESHOLD
    features = {'mark_left': float(np.flatnonzero(ink[:, :split_x].any(axis=0))[0]),
                'mark_top': float(np.flatnonzero(ink[:, :split_x].any(axis=1))[0])}
    split_y = int((CONST_LINE_SPLIT_UNITS - box.y()) * scale)
    lines = (('wordmark', 0, split_y, int(math.ceil(CONST_WORDMARK_GLYPH_UNITS * scale))),
             ('tagline', split_y, pixels.shape[0], int(math.ceil(CONST_TAGLINE_GLYPH_EMS * tagline_px))))
    for name, top, bottom, window in lines:
        line = _Line_Features(pixels[top:bottom], ground, split_x, pixels.shape[1], window)
        line.update({'top': top + line['top'], 'baseline': top + line['baseline']})
        features.update({'%s_%s' % (name, key): value for key, value in line.items()})
    return features


def _Live_And_Outlined(qt_app: QApplication) -> tp.Tuple[tp.Dict[str, float], tp.Dict[str, float], float]:
    """
    Description:
        The features of the lockup as the shown header draws it, and of the outlined logo rendered at the
        same height on the same ground; and the tagline's drawn size over the logo's: the logo's size put through
        Style.Font at the size Qt draws (a whole pixel), derived from the rule, never read back from the lockup's own
        font, so a lockup that sizes its tagline wrongly still fails.

    Args:
        (1) qt_app [QApplication(object)]: The application.

    Returns:
        (1) parameter [Tuple<Dict, Dict, float>]: (live, outlined, the tagline's drawn scale).
    """

    window, logo, _ = _Shown_Logo(qt_app)
    pixels, ratio = _Grab(window, logo)
    window.close()
    logo_px = CONST_TAGLINE_UNITS * logo.height() / CONST_LOGO_UNITS
    drawn_px = QFontInfo(Style.Font(logo_px * 72.0 / logo.logicalDpiY())).pixelSize()
    live = _Lockup_Features(pixels, ratio, logo.height(), drawn_px * ratio)
    outlined = _Lockup_Features(_Outlined(logo.height(), pixels[0, -1].astype(float)), ratio, logo.height(), logo_px * ratio)
    return live, outlined, drawn_px / logo_px


def test_the_lockup_matches_the_outlined_logo(qt_app) -> None:
    """
    Description:
        The live lockup reproduces the outlined logo's layout at this run's density: the mark-to-wordmark and
        wordmark-to-tagline offsets (left edges and baselines), both cap heights and the wordmark's width are within
        CONST_LOCKUP_TOLERANCE device px of the outlined logo's at the same height. The tagline's cap height is the
        logo's at the size Qt draws it, a whole pixel.
    """

    live, outlined, drawn_scale = _Live_And_Outlined(qt_app)

    def Offsets(features: tp.Dict[str, float]) -> tp.Dict[str, float]:
        return {'mark -> wordmark, x': features['wordmark_left'] - features['mark_left'],
                'mark -> wordmark baseline, y': features['wordmark_baseline'] - features['mark_top'],
                'wordmark -> tagline, x': features['tagline_left'] - features['wordmark_left'],
                'wordmark -> tagline baseline, y': features['tagline_baseline'] - features['wordmark_baseline'],
                'wordmark cap height': features['wordmark_cap'], 'tagline cap height': features['tagline_cap'],
                'wordmark width': features['wordmark_right'] - features['wordmark_left']}

    expected = Offsets(outlined)
    expected['tagline cap height'] *= drawn_scale
    measured = Offsets(live)
    off = {name: (round(measured[name], 2), round(value, 2)) for name, value in expected.items()
           if abs(measured[name] - value) > CONST_LOCKUP_TOLERANCE}
    assert not off, 'offsets (live, outlined) in device px beyond %g px: %s' % (CONST_LOCKUP_TOLERANCE, off)


def test_the_tagline_is_crisp_on_a_low_density_display(qt_app) -> None:
    """
    Description:
        At DPR 1 the tagline, as the shown header draws it, has at least CONST_TAGLINE_FCI_FLOOR of its ink
        at full contrast. Outlined, as an SVG picture, it has 0.147 at the same height and 0.009 at the logo's
        54 px: its stems and baseline fall between pixels, where nothing hints them.
    """

    if qt_app.devicePixelRatio() >= Style.CONST_LOW_DENSITY_DPR:
        pytest.skip('this run is at DPR %g; the tagline is measured for sharpness in the DPR 1 run'
                    % qt_app.devicePixelRatio())
    live, _, _ = _Live_And_Outlined(qt_app)
    assert live['tagline_fci'] >= CONST_TAGLINE_FCI_FLOOR, 'tagline FCI %.3f < %.2f' % (live['tagline_fci'], CONST_TAGLINE_FCI_FLOOR)


def test_the_lockup_tagline_is_the_bundled_public_sans(qt_app) -> None:
    """
    Description:
        The only text the lockup draws is the tagline, set in the bundled Public Sans Regular: the font it paints
        with resolves (QFontInfo) to that family at weight 400, and the face drawn is its file in App/assets/fonts/
        (its name table is that file's), not a platform substitute.
    """

    lockup = Logo_Lockup_Cls(Style.Logo_Height(QWidget()))
    painted = []
    # The class's own descriptor, restored as it was: QPainter.drawText read through the class is an
    # unbound builtin, and assigning that back breaks every later painter's drawText in the process.
    descriptor = QPainter.__dict__['drawText']
    draw_text = QPainter.drawText

    def Draw_Text(painter: QPainter, *args: tp.Any) -> tp.Any:
        painted.append(([arg for arg in args if isinstance(arg, str)][0], painter.font()))
        return draw_text(painter, *args)

    QPainter.drawText = Draw_Text
    try:
        lockup.Render()
    finally:
        setattr(QPainter, 'drawText', descriptor)
    assert [text for text, _ in painted] == [Style.CONST_TAGLINE]
    font = painted[0][1]
    assert (QFontInfo(font).family(), QFontInfo(font).weight(), QFontInfo(font).styleName()) == (CONST_TAGLINE_FACE[0], 50, 'Regular')
    bundled = QRawFont(os.path.join(Style.CONST_ASSETS, 'fonts', CONST_TAGLINE_FACE[1]), 12)
    assert QRawFont.fromFont(font).fontTable('name') == bundled.fontTable('name'), 'the tagline is not drawn from %s' % CONST_TAGLINE_FACE[1]


def test_the_header_is_measured_again_at_dpr_2(qt_app, project_root) -> None:
    """
    Description:
        This module, run again in a fresh interpreter at DPR 2 (QT_SCALE_FACTOR=2), passes: the high-density
        logo test, both gap tests, the lockup's layout and its face pass there, and the low-density tests skip.
    """

    if qt_app.devicePixelRatio() >= Style.CONST_LOW_DENSITY_DPR:
        pytest.skip('this is the DPR %g run' % qt_app.devicePixelRatio())
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_SCALE_FACTOR=CONST_HIGH_DENSITY_SCALE, PYTHONDONTWRITEBYTECODE='1')
    run = subprocess.run([sys.executable, '-m', 'pytest', os.path.abspath(__file__), '-rA', '-p', 'no:cacheprovider'],
                         cwd=project_root, env=env, capture_output=True, text=True, timeout=300)
    report = run.stdout + run.stderr
    assert run.returncode == 0, report[-3000:]
    for passed in ('test_the_logo_is_54_px_on_a_high_density_display',
                   'test_the_brand_marks_are_spaced_by_the_brand_gap_from_ink[0]',
                   'test_the_brand_marks_are_spaced_by_the_brand_gap_from_ink[1720]',
                   'test_the_lockup_matches_the_outlined_logo',
                   'test_the_jic_logo_keeps_its_share_of_the_lockup',
                   'test_the_lockup_tagline_is_the_bundled_public_sans'):
        assert 'PASSED test/UI/test_header.py::%s' % passed in report, report[-3000:]
    for skipped in ('the low-density logo is measured in the DPR 1 run',
                    'the tagline is measured for sharpness in the DPR 1 run'):
        assert skipped in report, report[-3000:]
