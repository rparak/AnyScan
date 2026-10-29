"""
The JIC Smart Factory style, held by tests: the palette's measured ratios, no colour outside the theme, no rounded
corner, every control state >= 4.5:1 from rendered pixels, crisp pixel icons, the bundled fonts, and the whole module
run again at DPR 2. Break each test once (references/testing.md) before trusting it.
"""
import io
import os
import re
import subprocess
import sys
import tokenize

import numpy as np
import pytest
from PyQt5.QtCore import Qt, QEvent, QPoint, QPointF
from PyQt5.QtGui import QImage, QPainter, QMouseEvent, QFontInfo, QRegion
from PyQt5.QtWidgets import QPushButton, QWidget

from JIC_SF_UI import Theme, Style, Pixel_Motif
from JIC_SF_UI.Widgets import Tool_Button_Cls, Segmented_Control_Cls, Icon_Cls

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONST_HIGH_DENSITY_SCALE = '2'


# ---------------------------------------------------------------- the palette (Qt-free)

@pytest.mark.parametrize('fg, bg, floor', [
    (Theme.CONST_INK, Theme.CONST_CARD, 4.5),                 # all text on white, 9.15:1
    (Theme.CONST_INK, Theme.CONST_CONTROL_HOVER, 4.5),        # hovered plain button, 6.79:1
    (Theme.CONST_INK, Theme.CONST_CONTROL_PRESSED, 4.5),      # pressed plain button, 5.71:1
    (Theme.CONST_ON_INK, Theme.CONST_INK, 4.5),               # white on purple, 9.15:1
    (Theme.CONST_INK_MUTE, Theme.CONST_CARD, 4.5),            # 6.24:1
    (Theme.CONST_INK_MUTE, Theme.CONST_VIEWPORT, 4.5),        # 4.63:1
    (Theme.CONST_OK_INK, Theme.CONST_CARD, 4.5),
    (Theme.CONST_WARN_INK, Theme.CONST_CARD, 4.5),
    (Theme.CONST_LOG_ERROR, Theme.CONST_VIEWPORT, 4.5),       # 4.61:1
    (Theme.CONST_DETECTION_INK, Theme.CONST_CARD, 4.5),       # chart text, 6.22:1
    (Theme.CONST_CHART_LIGHT_INK, Theme.CONST_CARD, 3.0),     # a graphic, 3.07:1
    (Theme.CONST_OK, Theme.CONST_CARD, 3.0),                  # status dots
    (Theme.CONST_WARN, Theme.CONST_CARD, 3.0),
])
def test_every_pair_clears_its_floor(fg, bg, floor) -> None:
    assert Theme.Contrast_Ratio(fg, bg) >= floor, (fg, bg, Theme.Contrast_Ratio(fg, bg))


@pytest.mark.parametrize('state', ['OK', 'NOK', 'Warning'])
def test_the_purple_words_read_on_every_states_ground(state) -> None:
    assert Theme.Contrast_Ratio(Theme.CONST_INK, Theme.Label_Ground(state)) >= 4.5


def test_one_purple_and_three_state_colours() -> None:
    purples = {v for k, v in vars(Theme).items() if k.startswith('CONST_') and isinstance(v, str)
               and v.startswith('#') and abs(Theme.Lch_Of(v)[2] - Theme.Lch_Of(Theme.CONST_PURPLE)[2]) < 3
               and Theme.Lch_Of(v)[1] > 60}
    assert purples == {'#640ABA'}, purples
    assert [Theme.Verdict_Color(s)[0] for s in ('OK', 'NOK', 'Warning')] == ['#640ABA', '#FF6540', '#FFC226']
    assert Theme.CONST_CHIP_NUMERAL == '#FFFFFF'


# ---------------------------------------------------------------- the source

HEX = re.compile(r'#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b')


def _Sources():
    for root, dirs, names in os.walk(PROJECT):
        dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__', '.venv', 'venv', 'tests')]
        for name in names:
            if name.endswith('.py') and name != 'Theme.py':
                yield os.path.join(root, name)


def test_no_colour_is_named_outside_the_theme() -> None:
    found = []
    for path in _Sources():
        with open(path, encoding='utf-8') as handle:
            tokens = list(tokenize.generate_tokens(io.StringIO(handle.read()).readline))
        for i, token in enumerate(tokens):
            if token.type == tokenize.STRING and HEX.search(token.string) and \
                    not (tokens[i - 1].type in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.NL)
                         and tokens[i + 1].type in (tokenize.NEWLINE, tokenize.NL)):
                found.append('%s:%d' % (path, token.start[0]))
            if token.string == 'QColor' and tokens[i + 1].string == '(' and tokens[i + 2].type == tokenize.NUMBER:
                found.append('%s:%d' % (path, token.start[0]))
    assert not found, found


def test_no_corner_is_rounded() -> None:
    found = []
    for path in _Sources():
        with open(path, encoding='utf-8') as handle:
            for number, line in enumerate(handle, 1):
                if re.search(r'border-radius|drawRoundedRect|addRoundedRect|setRadius', line):
                    found.append('%s:%d' % (path, number))
    assert not found, found


# ---------------------------------------------------------------- rendered pixels

def _Render(widget, dpr: float = 2.0) -> np.ndarray:
    image = QImage(int(widget.width() * dpr), int(widget.height() * dpr), QImage.Format_RGB32)
    image.setDevicePixelRatio(dpr)
    widget.render(image)
    pointer = image.constBits()
    pointer.setsize(image.byteCount())
    array = np.frombuffer(pointer, np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4)
    return array[:, :image.width(), 2::-1].copy()


def _Hex(rgb) -> str:
    return '#%02X%02X%02X' % tuple(int(c) for c in rgb)


def _Label_Contrast(pixels: np.ndarray) -> float:
    """The label's highest-contrast pixel against the dominant fill, inside the widget's middle."""
    h, w = pixels.shape[:2]
    core = pixels[h // 4: 3 * h // 4, w // 6: 5 * w // 6].reshape(-1, 3)
    colours, counts = np.unique(core, axis=0, return_counts=True)
    fill = _Hex(colours[counts.argmax()])
    return max(Theme.Contrast_Ratio(_Hex(c), fill) for c in colours)


def _Hover(widget) -> None:
    widget.setAttribute(Qt.WA_UnderMouse, True)
    centre = QPointF(widget.width() / 2.0, widget.height() / 2.0)
    for kind in (QEvent.Enter, QEvent.HoverEnter):
        widget.event(QEvent(kind))
    widget.event(QMouseEvent(QEvent.MouseMove, centre, Qt.NoButton, Qt.NoButton, Qt.NoModifier))


@pytest.mark.parametrize('primary', [False, True])
@pytest.mark.parametrize('state', ['rest', 'hover', 'pressed'])
def test_every_button_state_clears_four_and_a_half(qt_app, primary, state) -> None:
    button = Tool_Button_Cls('Analyze', primary=primary)
    button.resize(160, 48)
    button.show()
    if state == 'hover':
        _Hover(button)
    if state == 'pressed':
        button.setDown(True)
    qt_app.processEvents()
    assert _Label_Contrast(_Render(button)) >= 4.5


def test_a_hovered_selected_segment_keeps_its_white_label(qt_app) -> None:
    control = Segmented_Control_Cls([('a', 'Live'), ('b', 'Trends')])
    control.resize(200, 30)
    control.show()
    button = control.findChildren(QPushButton)[0]                        # the first segment starts selected
    assert button.isChecked()
    _Hover(button)
    qt_app.processEvents()
    assert _Label_Contrast(_Render(button)) >= 4.5


@pytest.mark.parametrize('name', sorted(Pixel_Motif.CONST_PIXEL_ICONS))
def test_every_icon_is_a_twelve_grid_drawn_in_two_colours(qt_app, name) -> None:
    rows = Pixel_Motif.CONST_PIXEL_ICONS[name]
    assert len(rows) == 12 and all(len(r) == 12 and set(r) <= set('.#123456789') for r in rows)
    icon = Icon_Cls(name)
    for dpr in (1.0, 2.0):
        image = QImage(int(icon.width() * dpr), int(icon.height() * dpr), QImage.Format_RGB32)
        image.setDevicePixelRatio(dpr)
        image.fill(Qt.white)
        painter = QPainter(image)
        icon.render(painter, QPoint(0, 0), QRegion(), QWidget.DrawChildren)     # no palette background
        painter.end()
        colours = {image.pixel(x, y) & 0xFFFFFF for x in range(image.width()) for y in range(image.height())}
        assert colours == {0xFFFFFF, 0x640ABA}, (name, dpr, [hex(c) for c in colours])


def test_the_bundled_faces_are_used(qt_app) -> None:
    assert QFontInfo(Style.Font(10)).family() == 'Public Sans'
    assert QFontInfo(Style.Font(10, mono=True)).family() == 'JetBrains Mono'


def test_the_module_passes_again_at_dpr_2(qt_app) -> None:
    if qt_app.devicePixelRatio() >= Style.CONST_LOW_DENSITY_DPR:
        pytest.skip('this is the DPR 2 run')
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_SCALE_FACTOR=CONST_HIGH_DENSITY_SCALE)
    run = subprocess.run([sys.executable, '-m', 'pytest', os.path.abspath(__file__), '-q', '-p', 'no:cacheprovider',
                          '-k', 'not dpr_2'], env=env, capture_output=True, text=True, timeout=600)
    assert run.returncode == 0, run.stdout[-3000:] + run.stderr[-2000:]
