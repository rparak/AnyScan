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

    The lockup is the mark (an SVG) with the wordmark and tagline as live text (docs/design-decisions.md,
    "The header's wordmark and tagline are live text"). Its text must be the bundled Inter, sit where the
    outlined logo (images/anyscan-logo.svg) has it, and at DPR 1 be hinted: each is measured here in the
    grabbed pixels against a render of the outlined logo at the same height.

    The lockup's height follows the display's density (Style.Logo_Height). The module runs at the
    session's device pixel ratio (1 offscreen) and runs itself once more at DPR 2 in a fresh
    interpreter, so the height, the gaps and the lockup's layout are measured at both ratios.
"""
CONST_CONFIGURATION = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)
# The chosen gap (docs/design-decisions.md, "The logo's text is outlined"): the funding band's 32 px
# around its divider. Pinned here, so a change of the constant is a change of this decision.
#   Unit [px]
CONST_EXPECTED_GAP = 32
# A pixel is ink when it differs from the header background by more than this (sum over R, G, B).
#   Unit [-]
CONST_INK_THRESHOLD = 30
# The logo's heights (docs/design-decisions.md, "The logo is 59 px on a low-density display"), and the
# share of its height that is ink: the viewBox is the ink plus 5 units on each side of 174.
#   Unit [px] / [-]
CONST_LOGO_HEIGHT_LOW_DENSITY = 59
CONST_LOGO_HEIGHT_HIGH_DENSITY = 54
CONST_LOGO_INK_SHARE = (174 - 2 * 5) / 174.0
# How far the grabbed ink height may differ from that share: one anti-aliased row at the top and one at
# the bottom. The two heights' ink differs by 4.7 px, so the check still tells 59 from 54.
#   Unit [px]
CONST_INK_HEIGHT_TOLERANCE = 2
# The ratio the second run uses, standing in for a 2x (Retina) display.
#   Unit [-]
CONST_HIGH_DENSITY_SCALE = '2'
# Where the lockup's parts are told apart, in logo units: text starts right of x = 248 (the mark's ink
# ends at 228, the wordmark's starts at 268), and the tagline below y = 154 (the wordmark's "y" ends at
# 149.8, the tagline's capitals start at 157.8). The first glyph ("A", "T") is read over its first
# 0.40 / 0.45 em, which holds its apex or stem and stops short of the next glyph.
#   Unit [logo units] / [em]
CONST_TEXT_LEFT_UNITS = 248.0
CONST_LINE_SPLIT_UNITS = 154.0
CONST_FIRST_GLYPH_EMS = (0.40, 0.45)
# The face each lockup line must draw, by whether it is set in the display cut: its family and its file.
#   Unit [Dict<bool, Tuple<string> 1x2>]
CONST_LOCKUP_FACES = {True: ('Inter Display', 'InterDisplay-Regular.ttf'), False: ('Inter', 'Inter-Regular.ttf')}
# Where the live lockup may differ from the outlined logo: every offset within 1 px (device px).
#   Unit [px]
CONST_LOCKUP_TOLERANCE = 1.0
# The tagline's full-contrast ink share at DPR 1 (the low-density report's FCI: of the ink samples, each
# colour channel of each pixel at coverage >= 0.10, the share at >= 0.90), at least. Measured at 59 px:
# 0.08 for the outlined logo; 0.21 for the live text in this suite (offscreen, 100 dpi, where the 9 pt
# floor sets it at 12.5 px) and 0.18 on a 96 dpi display (12.2 px). The floor keeps a 0.06 margin below
# the suite's value and stays above the outlined logo's by as much again.
#   Unit [-]
CONST_TAGLINE_FCI_FLOOR = 0.15


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """
    A single offscreen QApplication for the module, with the bundled fonts loaded as the application
    loads them: the lockup's text is set in Inter.
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
    jic = [label for label in window.findChildren(QLabel) if label.pixmap() is not None and not label.pixmap().isNull()][0]
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
    rows = np.flatnonzero((np.abs(pixels - pixels[0, 0]).sum(axis=2) > CONST_INK_THRESHOLD).any(axis=1))
    return window, logo, (rows[-1] + 1 - rows[0]) / ratio


def test_the_logo_is_59_px_on_a_low_density_display(qt_app) -> None:
    """
    Description:
        Below DPR 1.5 the header lockup is 59 px tall: the widget is 59 logical pixels, and the ink
        grabbed from the window spans the logo's ink share of 59 px (±CONST_INK_HEIGHT_TOLERANCE), not of 54.
    """

    if qt_app.devicePixelRatio() >= Style.CONST_LOW_DENSITY_DPR:
        pytest.skip('this run is at DPR %g; the low-density logo is measured in the DPR 1 run'
                    % qt_app.devicePixelRatio())
    window, logo, ink = _Shown_Logo(qt_app)
    assert logo.height() == CONST_LOGO_HEIGHT_LOW_DENSITY
    assert abs(ink - CONST_LOGO_HEIGHT_LOW_DENSITY * CONST_LOGO_INK_SHARE) <= CONST_INK_HEIGHT_TOLERANCE, 'logo ink is %.1f px tall' % ink
    window.close()


def test_the_logo_is_54_px_on_a_high_density_display(qt_app) -> None:
    """
    Description:
        At DPR 1.5 and above the header lockup is 54 px tall, as the logo has always been there: the widget
        is 54 logical pixels, and the grabbed ink spans the ink share of 54 px.
    """

    if qt_app.devicePixelRatio() < Style.CONST_LOW_DENSITY_DPR:
        pytest.skip('this run is at DPR %g; the high-density logo is measured in the DPR 2 run'
                    % qt_app.devicePixelRatio())
    window, logo, ink = _Shown_Logo(qt_app)
    assert logo.height() == CONST_LOGO_HEIGHT_HIGH_DENSITY
    assert abs(ink - CONST_LOGO_HEIGHT_HIGH_DENSITY * CONST_LOGO_INK_SHARE) <= CONST_INK_HEIGHT_TOLERANCE, 'logo ink is %.1f px tall' % ink
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


def _Lockup_Features(pixels: np.ndarray, ratio: float, height: int) -> tp.Dict[str, float]:
    """
    Description:
        Where the lockup's parts are, in device pixels from its top-left corner: the mark's ink left and
        top edges, and for the wordmark and the tagline the first glyph's left edge, cap top and baseline,
        the cap height, and the line's rightmost ink (read in the last span's colour), each edge read to a
        fraction of a pixel from the anti-aliased coverage; and the tagline's full-contrast ink share (FCI).

    Args:
        (1) pixels [Matrix HxWx3]: The lockup's RGB pixels on its ground (pixels[0, 0] is ground).
        (2) ratio [float]: Their device pixel ratio.
        (3) height [int]: The lockup's height in logical pixels.

    Returns:
        (1) parameter [Dict<string, float>]: The features, named '<part>_<feature>'.
    """

    box = QSvgRenderer(os.path.join(Style.CONST_ASSETS, Style.CONST_LOGO_MARK_FILE)).viewBoxF()
    scale = height * ratio / box.height()
    split_x = int((CONST_TEXT_LEFT_UNITS - box.x()) * scale)
    split_y = int((CONST_LINE_SPLIT_UNITS - box.y()) * scale)
    ground = pixels[0, 0].astype(float)
    ink = np.abs(pixels - ground).sum(axis=2) > CONST_INK_THRESHOLD
    features = {'mark_left': float(np.flatnonzero(ink[:, :split_x].any(axis=0))[0]),
                'mark_top': float(np.flatnonzero(ink[:, :split_x].any(axis=1))[0])}
    lines = (('wordmark', 0, split_y), ('tagline', split_y, pixels.shape[0]))
    for (name, top, bottom), ((_, size, _, spans), ems) in zip(lines, zip(Style.CONST_LOGO_TEXT, CONST_FIRST_GLYPH_EMS)):
        coverage = np.clip((ground - pixels[top:bottom, split_x:]) / (ground - _Rgb(spans[0][1])), 0.0, 1.0)
        ending = np.clip((ground - pixels[top:bottom, split_x:]) / (ground - _Rgb(spans[-1][1])), 0.0, 1.0).mean(axis=2).max(axis=0)
        last = np.flatnonzero(ending >= 0.1)[-1]
        mean = coverage.mean(axis=2)
        columns = mean.max(axis=0)
        first = np.flatnonzero(columns >= 0.1)[0]
        profile = mean[:, first:first + int(math.ceil(ems * size * scale))].max(axis=1)
        rows = np.flatnonzero(profile >= 0.1)
        cap_top = rows[0] + 1.0 - profile[rows[0]]
        baseline = rows[-1] + profile[rows[-1]]
        features.update({'%s_left' % name: split_x + first + 1.0 - columns[first], '%s_top' % name: top + cap_top,
                         '%s_baseline' % name: top + baseline, '%s_cap' % name: baseline - cap_top,
                         '%s_right' % name: split_x + last + ending[last]})
        if name == 'tagline':
            samples = coverage >= 0.1
            features['tagline_fci'] = float((coverage >= 0.9).sum()) / max(1, samples.sum())
    return features


def _Offsets(features: tp.Dict[str, float]) -> tp.Dict[str, float]:
    """
    Description:
        The lockup's internal offsets: mark to wordmark (the wordmark's left edge and baseline from the
        mark's ink), wordmark to tagline (left edge and baseline), each line's cap height, and the
        wordmark's width (left edge to rightmost ink). The tagline's width is not one: it is set in the text
        cut, wider than the logo's outlines by design.

    Args:
        (1) features [Dict<string, float>]: From _Lockup_Features.

    Returns:
        (1) parameter [Dict<string, float>]: The offsets in device pixels.
    """

    return {'mark -> wordmark, x': features['wordmark_left'] - features['mark_left'],
            'mark -> wordmark baseline, y': features['wordmark_baseline'] - features['mark_top'],
            'wordmark -> tagline, x': features['tagline_left'] - features['wordmark_left'],
            'wordmark -> tagline baseline, y': features['tagline_baseline'] - features['wordmark_baseline'],
            'wordmark cap height': features['wordmark_cap'], 'tagline cap height': features['tagline_cap'],
            'wordmark width': features['wordmark_right'] - features['wordmark_left']}


def _Live_And_Outlined(qt_app: QApplication) -> tp.Tuple[tp.Dict[str, float], tp.Dict[str, float]]:
    """
    Description:
        The features of the lockup as the shown header draws it, and of the outlined logo rendered at the
        same height on the same ground.

    Args:
        (1) qt_app [QApplication(object)]: The application.

    Returns:
        (1) parameter [Tuple<Dict, Dict>]: (live, outlined) features; the outlined ones also carry
                                           'tagline_drawn_scale', the tagline's expected drawn size over
                                           the logo's.
    """

    window, logo, _ = _Shown_Logo(qt_app)
    pixels, ratio = _Grab(window, logo)
    window.close()
    live = _Lockup_Features(pixels, ratio, logo.height())
    outlined = _Lockup_Features(_Outlined(logo.height(), pixels[0, 0].astype(float)), ratio, logo.height())
    # The pixel size the tagline should be drawn at over the logo's: the logo's size put through Style.Font,
    # which applies the type floor, at the size Qt draws (a whole pixel) — derived from the rule, never read
    # back from the lockup's own font, so a lockup that sizes its tagline wrongly still fails.
    (_, size, display, _), box = Style.CONST_LOGO_TEXT[1], QSvgRenderer(os.path.join(Style.CONST_ASSETS,
                                                                                    Style.CONST_LOGO_MARK_FILE)).viewBoxF()
    logo_px = size * logo.height() / box.height()
    expected = QFontInfo(Style.Font(logo_px * 72.0 / logo.logicalDpiY(), display=display)).pixelSize()
    outlined['tagline_drawn_scale'] = expected / logo_px
    return live, outlined


def test_the_lockup_matches_the_outlined_logo(qt_app) -> None:
    """
    Description:
        The live lockup reproduces the outlined logo's layout at this run's density: the mark-to-wordmark
        and wordmark-to-tagline offsets (left edges and baselines), both cap heights and the wordmark's
        width are within CONST_LOCKUP_TOLERANCE device px of the outlined logo's at the same height.
    """

    live, outlined = _Live_And_Outlined(qt_app)
    live_offsets, outlined_offsets = _Offsets(live), _Offsets(outlined)
    # The tagline's cap height is the logo's at the size the lockup DRAWS it: below 9 pt at DPR 1 the
    # type floor raises it (docs/design-decisions.md, "A 9 pt type floor on a low-density display") — at
    # the offscreen tests' 100 dpi the logo's 12.2 px tagline is 8.79 pt, drawn at 13 px — and Qt draws a
    # whole-pixel size. The offsets between the lines are still the logo's.
    outlined_offsets['tagline cap height'] *= outlined['tagline_drawn_scale']
    off = {name: (round(live_offsets[name], 2), round(outlined_offsets[name], 2)) for name in live_offsets
           if abs(live_offsets[name] - outlined_offsets[name]) > CONST_LOCKUP_TOLERANCE}
    assert not off, 'offsets (live, outlined) in device px beyond %g px: %s' % (CONST_LOCKUP_TOLERANCE, off)


def test_the_tagline_is_crisp_on_a_low_density_display(qt_app) -> None:
    """
    Description:
        At DPR 1 the tagline, as the shown header draws it, has at least CONST_TAGLINE_FCI_FLOOR of its ink
        at full contrast. Outlined, as an SVG picture, it had 0.08: its stems and baseline fall between
        pixels, where nothing hints them.
    """

    if qt_app.devicePixelRatio() >= Style.CONST_LOW_DENSITY_DPR:
        pytest.skip('this run is at DPR %g; the tagline is measured for sharpness in the DPR 1 run'
                    % qt_app.devicePixelRatio())
    live, outlined = _Live_And_Outlined(qt_app)
    assert live['tagline_fci'] >= CONST_TAGLINE_FCI_FLOOR, \
        'tagline FCI %.3f < %.2f (the outlined logo: %.3f)' % (live['tagline_fci'], CONST_TAGLINE_FCI_FLOOR, outlined['tagline_fci'])


def test_the_lockup_text_is_the_bundled_inter(qt_app) -> None:
    """
    Description:
        Every text the lockup draws is set in a bundled Inter Regular: the wordmark's spans in the display
        cut (Inter Display), the tagline in the text cut (Inter). The font each paints with resolves
        (QFontInfo) to that family at weight 400, and the face drawn is its file in App/assets/fonts/ (its
        name table is that file's), not a platform substitute.
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
    expected = {span: CONST_LOCKUP_FACES[display] for _, _, display, spans in Style.CONST_LOGO_TEXT for span, _ in spans}
    assert [text for text, _ in painted] == list(expected)
    resolved = {text: (QFontInfo(font).family(), QFontInfo(font).weight(), QFontInfo(font).styleName()) for text, font in painted}
    assert resolved == {text: (family, 50, 'Regular') for text, (family, _) in expected.items()}, \
        'the lockup text resolves to %s' % resolved
    for text, font in painted:
        bundled = QRawFont(os.path.join(Style.CONST_ASSETS, 'fonts', expected[text][1]), 12)
        assert QRawFont.fromFont(font).fontTable('name') == bundled.fontTable('name'), '%r is not drawn from %s' % (text, expected[text][1])


def test_the_header_is_measured_again_at_dpr_2(qt_app, project_root) -> None:
    """
    Description:
        This module, run again in a fresh interpreter at DPR 2 (QT_SCALE_FACTOR=2), passes: the high-density
        logo test, both gap tests and the lockup's layout pass there, and the low-density tests skip.
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
                   'test_the_lockup_text_is_the_bundled_inter'):
        assert 'PASSED test/UI/test_header.py::%s' % passed in report, report[-3000:]
    for skipped in ('the low-density logo is measured in the DPR 1 run',
                    'the tagline is measured for sharpness in the DPR 1 run'):
        assert skipped in report, report[-3000:]
