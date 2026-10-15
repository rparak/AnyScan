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
# File Name: ../test/UI/test_text_contrast.py
## =========================================================================== ##

# System (Default)
import collections
import os
import re
import subprocess
import sys
import time
from datetime import datetime
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Typing (Support for type hints)
import typing as tp
# OpenCV (Computer vision) [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QFontInfo, QImage, QPainter, QPalette
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
# Custom Lib.: AnyScan UI — the window, the History thumbnail, the capture writer
import UI.Core as Core
from UI.Core import AnyScan_Window_Cls
from UI.Views.History import Thumb_Card_Cls, CONST_INFO_SLIDE_MS
from UI.Capture import Capture_Writer_Cls, Capture_Set_Str, Build_Set_Metadata
import UI.Utilities.Style as Style
# Custom Lib.: AnyScan domain — the palette, the camera and vision interfaces, the logger, the records
import Parameters.Theme as Theme
from Camera.Core import Camera_Backend_Cls
from Vision.Core import Vision_Backend_Cls
from Logger.Core import Session_Logger_Cls
from Parameters.Vision import Analysis_Str, Detection_Str
# Custom Lib.: AnyScan — the configuration layer
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    Every text the console draws clears 4.5:1 against the ground it is drawn on. The window is built and
    driven through the states the 2026-09-29 audit rendered (startup: configuration not loaded, camera
    offline; loading; working: loaded, connected, one analysis, capture sets, History's Info panel), and
    each visible label is measured where it is shown: its colour is the one the widget resolved from its
    stylesheet (the token the code handed it), the colours inside its rich text are the spans it renders,
    painted text is the pen it was drawn with, and its ground is the colour that fills most of the label
    in the grabbed window, which must itself be a theme token. The token values are read from
    Parameters.Theme when the test runs, never copied here.

    The same walk records each text's resolved point size: on a low-density display (DPR 1, this run) no
    text is below 9 pt (Style.CONST_TYPE_FLOOR_LOW_DENSITY, docs/design-decisions.md, "A 9 pt type floor
    on a low-density display"). The module runs itself again at DPR 2 (QT_SCALE_FACTOR=2), where the
    contrast is measured once more and the window must draw exactly the pixels it draws with no floor.

    Exempt, by the project's rules: a disabled widget (its lower contrast says 'not available'; held by
    test_control_contrast.py to look different from enabled); a status dot '●', a graphic held to 3:1
    (WCAG 1.4.11). Not measured here: buttons, whose label colour depends on the state and is measured
    from rendered pixels by test_control_contrast.py; the logo's tagline, which is artwork (6.86:1); the
    Configuration dialog's list items, which are not widgets (INK on the card, INK_MUTE when disabled).
"""
CONST_MANGLE = '_AnyScan_Window_Cls'
# The floors: WCAG AA for text, and for a non-text graphic.
#   Unit [-] (contrast ratio)
CONST_TEXT_FLOOR = 4.5
CONST_GRAPHIC_FLOOR = 3.0
# A text made only of this is a status dot, a graphic.
#   Unit [string]
CONST_DOT = '●'
# One text of every style the 2026-09-29 audit flagged that is a label or painted text, so the walk is
# known to have reached each of them (docs/design-decisions.md, "Text clears 4.5:1 ..."). The funding band's
# disclaimer left the window on 2026-10-15 (its band carries logos only).
#   Unit [Tuple<string>]
CONST_FLAGGED_TEXTS = (
    'Configuration not loaded.', 'Loading configuration', 'Configuration loaded.', 'Camera offline', 'Camera live',
    'No frame', 'Idle', 'Connect a camera and scan a frame', 'CAMERA', 'Disconnected', 'Models not loaded',
    'Connected', 'Ready', 'Cumulative objects', 'No analyses in this run yet.',
    'Rolling window', 'No captures in this run yet.', 'Select a capture set.', 'lines', 'Connection sessionA',
    '10:00:00', 'objects', 'Annotated', 'Mask', 'ANALYSIS\nFAILED', 'found by background subtraction',
    'Note from the composer.')
# The smallest point size on a low-density display, and the ratio the second run uses for a 2x display.
#   Unit [float] (point size) / [string]
CONST_LOW_DENSITY_MINIMUM_PT = 9.0
CONST_HIGH_DENSITY_SCALE = '2'
# The views the window switches between.
#   Unit [Tuple<string>]
CONST_VIEWS = ('live', 'trends', 'history', 'log')


class _Idle_Camera_Cls(Camera_Backend_Cls):
    """
    Description:
        A camera that connects at once and grabs a fixed frame.
    """

    def _Open(self) -> None:
        """
        Description:
            Nothing to open.
        """

        pass

    def _Close(self) -> None:
        """
        Description:
            Nothing to close.
        """

        pass

    def _Grab(self) -> np.ndarray:
        """
        Description:
            A fixed dark frame.

        Returns:
            (1) parameter [Matrix<uint8> HxWx3]: The frame.
        """

        return np.zeros((40, 60, 3), dtype=np.uint8)

    @property
    def Resolution(self) -> tp.Tuple[int, int]:
        """
        Description:
            The frame size.

        Returns:
            (1) parameter [Vector<int> 1x2]: (width, height).
        """

        return (60, 40)


class _Vision_Cls(Vision_Backend_Cls):
    """
    Description:
        A vision backend whose models are loaded, or not, as told.
    """

    def __init__(self, loaded: bool) -> None:
        self.Models_Loaded = loaded
        self.Name, self.Model_Names = 'JIC_AnyScan_All_v1', ('FastSAM-x.pt', 'gemma-4-e4b-it-4bit')

    def Configure(self, Configuration_Str: tp.Any, stage_cb: tp.Optional[tp.Callable] = None) -> None:
        """
        Description:
            Loaded at once.

        Args:
            (1) Configuration_Str [Configuration_Str(object)]: Ignored.
            (2) stage_cb [function]: Ignored.
        """

        self.Models_Loaded = True


def _Private(owner: tp.Any, name: str, mangle: str = CONST_MANGLE) -> tp.Any:
    """
    Description:
        A name-mangled private attribute of an object.

    Args:
        (1) owner [object]: The object.
        (2) name [string]: The bare private name.
        (3) mangle [string]: The owner's mangling prefix.

    Returns:
        (1) parameter [object]: The attribute.
    """

    return getattr(owner, mangle + name)


def _Pixels(image: QImage) -> np.ndarray:
    """
    Description:
        An image's RGB pixels as an array.

    Args:
        (1) image [QImage(object)]: The image.

    Returns:
        (1) parameter [Matrix<uint8> HxWx3]: Its pixels.
    """

    image = image.convertToFormat(QImage.Format_ARGB32)
    pointer = image.constBits()
    pointer.setsize(image.byteCount())
    return np.frombuffer(pointer, np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4)[:, :image.width(), 2::-1].copy()


def _Ground(pixels: np.ndarray) -> str:
    """
    Description:
        The colour that fills most of a region: the ground its text is drawn on.

    Args:
        (1) pixels [Matrix<uint8> HxWx3]: The region.

    Returns:
        (1) parameter [string]: The colour as '#rrggbb'.
    """

    values, counts = np.unique(pixels.reshape(-1, 3), axis=0, return_counts=True)
    return '#%02x%02x%02x' % tuple(int(v) for v in values[counts.argmax()])


def _Theme_Tokens() -> tp.Dict[str, tp.List[str]]:
    """
    Description:
        Every colour token in Parameters.Theme as it is now, by value.

    Returns:
        (1) parameter [Dict<string, Vector<string>>]: '#rrggbb' -> the token names with that value.
    """

    tokens = collections.defaultdict(list)
    for name, value in vars(Theme).items():
        if name.startswith('CONST_') and isinstance(value, str) and re.fullmatch('#[0-9a-fA-F]{6}', value):
            tokens[value.lower()].append(name)
    return tokens


def _Settle(window: QWidget) -> None:
    """
    Description:
        Let the window lay out and paint.

    Args:
        (1) window [QWidget(object)]: The window.
    """

    for _ in range(20):
        QApplication.instance().processEvents()


def _Measure(root: QWidget, state: str, painted: tp.List[tp.Tuple[int, str, str]],
             records: tp.List[tp.Dict[str, tp.Any]]) -> None:
    """
    Description:
        Grab a shown widget tree and record every visible text in it: each label's resolved colour and
        its rich-text span colours, and every text painted during the grab with its pen, each against the
        ground that fills most of its widget in the grab.

    Args:
        (1) root [QWidget(object)]: The shown window (or widget) to grab.
        (2) state [string]: The state's name, for the report.
        (3) painted [Vector<Tuple>]: The list the drawText hook fills: (widget id, text, pen colour, point size).
        (4) records [Vector<Dict>]: Where the records are appended.
    """

    _Settle(root)
    del painted[:]
    grab = root.grab()
    ratio = grab.devicePixelRatio()
    pixels = _Pixels(grab.toImage())

    def Region(widget: QWidget) -> np.ndarray:
        corner = widget.mapTo(root, QPoint(0, 0))
        return pixels[int(corner.y() * ratio):int((corner.y() + widget.height()) * ratio),
                      int(corner.x() * ratio):int((corner.x() + widget.width()) * ratio)]

    for label in root.findChildren(QLabel):
        if not label.isVisible() or not label.text() or (label.pixmap() is not None and not label.pixmap().isNull()):
            continue
        region = Region(label)
        if region.size == 0 or label.visibleRegion().isEmpty():
            continue
        ground = _Ground(region)
        plain = re.sub('<[^>]+>', '', label.text()).replace('&nbsp;', ' ')
        colour = label.palette().color(QPalette.Active if label.isEnabled() else QPalette.Disabled, QPalette.WindowText).name()
        spans = re.findall(r'<span style="color:\s*(#[0-9a-fA-F]{6})[^"]*">([^<]*)</span>', label.text())
        outside = re.sub(r'<span style="color:[^"]*">[^<]*</span>', '', label.text())
        texts = [(colour, plain)] if re.sub('<[^>]+>|&nbsp;|\\s', '', outside) or not spans else []
        texts += [(span_colour.lower(), span_text) for span_colour, span_text in spans]
        for text_colour, text in texts:
            records.append({'state': state, 'text': text, 'colour': text_colour, 'ground': ground,
                            'enabled': label.isEnabled(), 'painted': False, 'pt': QFontInfo(label.font()).pointSizeF()})
    widgets = {id(widget): widget for widget in root.findChildren(QWidget)}
    widgets[id(root)] = root
    for widget_id, text, pen, point_size in painted:
        widget = widgets.get(widget_id)
        if widget is None:
            continue
        records.append({'state': state, 'text': text, 'colour': pen, 'ground': _Ground(Region(widget)),
                        'enabled': True, 'painted': True, 'pt': point_size})


def _Window(tmp_path: tp.Any, loaded: bool) -> AnyScan_Window_Cls:
    """
    Description:
        A shown 1920 x 1080 window on the shipped configuration, with a real logger (so captures are
        written), an idle camera and a stand-in vision backend.

    Args:
        (1) tmp_path [Path(object)]: Where the log and the captures go.
        (2) loaded [bool]: Whether the stand-in's models are loaded.

    Returns:
        (1) parameter [AnyScan_Window_Cls(object)]: The window.
    """

    logger = Session_Logger_Cls(config_path=CONST_DEFAULT_CONFIG_FILE, log_dir=str(tmp_path / ('log%d' % loaded)),
                                install_handlers=False)
    window = AnyScan_Window_Cls(camera=_Idle_Camera_Cls(), logger=logger,
                                Configuration_Str=Load_Configuration(CONST_DEFAULT_CONFIG_FILE))
    setattr(window, CONST_MANGLE + '__vision', _Vision_Cls(loaded))
    _Private(window, '__Sync_Controls')()
    window.resize(1920, 1080)
    window.show()
    _Settle(window)
    return window


def _View(window: AnyScan_Window_Cls, key: str) -> None:
    """
    Description:
        Switch the central view, as a click on its segment does.

    Args:
        (1) window [AnyScan_Window_Cls(object)]: The window.
        (2) key [string]: The view key.
    """

    _Private(window, '__view_switch').Set_Selection(key)
    _Private(window, '__On_View_Selected')(key)
    _Settle(window)


def _Write_Set(root: str, set_id: str, run_id: str, scores: tp.Sequence[tp.Optional[float]]) -> None:
    """
    Description:
        Write a full capture set through the real writer, one object per score (None = found by the
        background cue alone, which History's Info panel notes).

    Args:
        (1) root [string]: The captures root.
        (2) set_id [string]: The set id.
        (3) run_id [string]: The application run the set belongs to.
        (4) scores [Vector<float>]: The objects' segmenter scores.
    """

    objects = [Detection_Str(Label='part', Bbox=(5 + 20 * i, 5, 15, 15), Segmenter_Score=score, Sentence='A part.',
                             Verdict='OK', Cue='both' if score is not None else 'background')
               for i, score in enumerate(scores)]
    metadata = Build_Set_Metadata('sessionA', set_id, '2026-09-20T10:00:00', objects, (60, 40), 'caption', 1180, 91, '',
                                  True, run_id, scale=None, configuration='Config_Test_Mode_A.yaml',
                                  station='', calibration='',
                                  background_reference='Data/Images/Background/Image_Background_001.png', hardware={},
                                  window=None)
    Capture_Writer_Cls(root).Write('sessionA', set_id, np.full((40, 60, 3), 30, np.uint8), np.full((40, 60, 3), 60, np.uint8),
                                   np.zeros((40, 60, 3), np.uint8), 'text', ['0 0.5 0.5 0.1 0.1'], ['0 0.4 0.4 0.6 0.6'],
                                   metadata, 'stamp', cv2, np, distorted_bgr=None, undistortion=None)


def _Working_Window(tmp_path: tp.Any) -> AnyScan_Window_Cls:
    """
    Description:
        The working state: loaded, connected, one analysis with a composer note and an unscored object,
        and two capture sets in History.

    Args:
        (1) tmp_path [Path(object)]: Where the log and the captures go.

    Returns:
        (1) parameter [AnyScan_Window_Cls(object)]: The shown window.
    """

    window = _Window(tmp_path, loaded=True)
    _Private(window, '__camera').Connect()
    _Private(window, '__Sync_Controls')()
    _Private(window, '__On_Scan_Button_Clicked')()
    objects = [Detection_Str(Label='ring', Bbox=(4, 4, 20, 16), Segmenter_Score=0.93, Sentence='A steel ring.', Cue='both'),
               Detection_Str(Label='nut', Bbox=(30, 6, 12, 12), Segmenter_Score=None, Sentence='A hex nut.', Cue='background')]
    _Private(window, '__On_Analysis_Finished')(Analysis_Str(Objects=objects, Latency_Ms=1180, Verdict='ok',
                                                             Verdict_Level='ok', Task='caption',
                                                             Note='Note from the composer.'))
    root, run_id = _Private(window, '__captures_root'), _Private(window, '__run_id')
    _Write_Set(root, 'set_0001', run_id, (0.91, 0.90))
    _Write_Set(root, 'set_0002', run_id, (0.91, None))
    return window


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """
    Description:
        A single offscreen QApplication for the module, with the fonts the application loads; held for the
        module so it outlives the records.

    Returns:
        (1) parameter [QApplication(object)]: The application.
    """

    app = QApplication.instance() or QApplication([])
    Style.Load_Fonts()
    return app


@pytest.fixture(scope='module')
def records(qt_app, tmp_path_factory) -> tp.List[tp.Dict[str, tp.Any]]:
    """
    Description:
        Every text measured across the states, with QPainter.drawText hooked so painted text reports its
        pen and the widget it is painted on.

    Returns:
        (1) parameter [Vector<Dict>]: The records.
    """

    app = qt_app
    tmp_path = tmp_path_factory.mktemp('contrast')
    painted = []
    # The class's own descriptor, restored as it was: QPainter.drawText read through the class is an
    # unbound builtin, and assigning that back breaks every later painter's drawText in the process.
    descriptor = QPainter.__dict__['drawText']
    draw_text = QPainter.drawText

    def Draw_Text(painter: QPainter, *args: tp.Any) -> tp.Any:
        texts = [arg for arg in args if isinstance(arg, str)]
        if texts and isinstance(painter.device(), QWidget):
            painted.append((id(painter.device()), texts[0], painter.pen().color().name(),
                            QFontInfo(painter.font()).pointSizeF()))
        return draw_text(painter, *args)

    QPainter.drawText = Draw_Text
    out = []
    try:
        # Startup: the configuration named but not loaded, the camera offline, nothing analysed.
        window = _Window(tmp_path, loaded=False)
        for key in CONST_VIEWS:
            _View(window, key)
            _Measure(window, 'startup/%s' % key, painted, out)
        # The configuration loading.
        _View(window, 'live')
        setattr(window, CONST_MANGLE + '__configuration_loading', True)
        _Private(window, '__Sync_Model_State')()
        _Measure(window, 'loading/live', painted, out)
        window.close()

        # Working: loaded, connected, one analysis with a composer note, capture sets in History.
        window = _Working_Window(tmp_path)
        for key in CONST_VIEWS:
            _View(window, key)
            _Measure(window, 'working/%s' % key, painted, out)
        _View(window, 'history')
        history = _Private(window, '__history_view')
        card = [card for card in _Private(history, '__cards', '_History_View_Cls') if card.Cap().Set_Id == 'set_0002'][0]
        _Private(history, '__Select', '_History_View_Cls')(card.Cap())
        _Private(history, '__info_button', '_History_View_Cls').click()
        deadline = time.time() + 2 * CONST_INFO_SLIDE_MS / 1000.0
        while time.time() < deadline:
            app.processEvents()
            time.sleep(0.01)
        _Measure(window, 'working/history-info', painted, out)
        window.close()

        # A failed set's thumbnail (drawn on the indigo viewport colour).
        thumb = Thumb_Card_Cls(Capture_Set_Str(Session_Id='sessionA', Set_Id='failset', Partial=True))
        thumb.show()
        thumb.Load()
        _Measure(thumb, 'history/failed-thumbnail', painted, out)
        thumb.close()
    finally:
        setattr(QPainter, 'drawText', descriptor)
    return out


def test_every_flagged_text_was_measured(records) -> None:
    """
    Description:
        The walk reached one text of every style the audit flagged, so the floor below covers them.
    """

    measured = ' | '.join(record['text'] for record in records)
    missing = [text for text in CONST_FLAGGED_TEXTS if text not in measured]
    assert not missing, 'not measured: %s' % missing


def test_every_text_ground_is_a_theme_token(records) -> None:
    """
    Description:
        Each text sits on a ground that is a theme token, so its contrast is a property of the palette.
    """

    tokens = _Theme_Tokens()
    loose = sorted({(record['state'], record['text'][:30], record['ground']) for record in records if record['ground'] not in tokens})
    assert not loose, 'grounds that are not a theme token: %s' % loose


def test_every_enabled_text_clears_the_floor(records) -> None:
    """
    Description:
        Every enabled text is at least CONST_TEXT_FLOOR (4.5:1) against its ground, and every status dot at
        least CONST_GRAPHIC_FLOOR (3:1). Disabled text is exempt.
    """

    tokens = _Theme_Tokens()
    failures = []
    for record in records:
        if not record['enabled']:
            continue
        floor = CONST_GRAPHIC_FLOOR if record['text'].strip() == CONST_DOT else CONST_TEXT_FLOOR
        ratio = Theme.Contrast_Ratio(record['colour'], record['ground'])
        if ratio < floor:
            failures.append('%.2f:1 < %.1f  %s  %r  %s on %s' % (
                ratio, floor, record['state'], record['text'][:40], '/'.join(tokens.get(record['colour'], [record['colour']])),
                '/'.join(tokens.get(record['ground'], [record['ground']]))))
    assert not failures, '\n' + '\n'.join(sorted(set(failures)))


def _Fixed_Now(cls: type, tz: tp.Any = None) -> datetime:
    """
    Description:
        A fixed moment, as the frozen datetime's now(), so two windows built a second apart show the same
        LAST UPDATE.

    Args:
        (1) cls [type]: The frozen datetime class.
        (2) tz [tzinfo]: Ignored.

    Returns:
        (1) parameter [datetime(object)]: 2026-09-29 12:34:56.
    """

    return cls(2026, 9, 29, 12, 34, 56)


# datetime with now() fixed; 'now' is the name datetime's own interface calls, set here rather than in a
# class body so the helper keeps the project's naming.
#   Unit [type]
CONST_FROZEN_DATETIME = type('Frozen_Datetime', (datetime,), {'now': classmethod(_Fixed_Now)})


def _Grab_Views(tmp_path: tp.Any) -> tp.Dict[str, np.ndarray]:
    """
    Description:
        The working window's Live and History views (the two with chrome below 9 pt), as grabbed pixels.

    Args:
        (1) tmp_path [Path(object)]: Where the log and the captures go.

    Returns:
        (1) parameter [Dict<string, Matrix<uint8>>]: The view key -> its grab.
    """

    window = _Working_Window(tmp_path)
    grabs = {}
    for key in ('live', 'history'):
        _View(window, key)
        grabs[key] = _Pixels(window.grab().toImage())
    window.close()
    return grabs


def test_every_text_is_at_least_9_pt_on_a_low_density_display(qt_app, records) -> None:
    """
    Description:
        Below DPR 1.5 no text the walk measured, labels and painted text alike, resolves below 9 pt.
    """

    if qt_app.devicePixelRatio() >= Style.CONST_LOW_DENSITY_DPR:
        pytest.skip('this run is at DPR %g; the floor is measured in the DPR 1 run' % qt_app.devicePixelRatio())
    small = sorted({(record['pt'], record['state'], record['text'][:30]) for record in records
                    if record['pt'] < CONST_LOW_DENSITY_MINIMUM_PT})
    assert not small, 'below %g pt: %s' % (CONST_LOW_DENSITY_MINIMUM_PT, small)


def test_a_high_density_display_draws_what_it_drew_without_the_floor(qt_app, tmp_path, monkeypatch) -> None:
    """
    Description:
        At DPR 1.5 and above the floor changes nothing: the Live and History views are pixel-identical to
        the same views drawn with the floor at 0 (no floor, the code before it). The clock is fixed so the
        two builds show the same time.
    """

    if qt_app.devicePixelRatio() < Style.CONST_LOW_DENSITY_DPR:
        pytest.skip('this run is at DPR %g; the high-density comparison runs at DPR 2' % qt_app.devicePixelRatio())
    monkeypatch.setattr(Core, 'datetime', CONST_FROZEN_DATETIME)
    shipped = _Grab_Views(tmp_path / 'shipped')
    monkeypatch.setattr(Style, 'CONST_TYPE_FLOOR_LOW_DENSITY', 0.0)
    without = _Grab_Views(tmp_path / 'without')
    for key in shipped:
        differing = int((shipped[key] != without[key]).any(axis=2).sum()) if shipped[key].shape == without[key].shape else -1
        assert differing == 0, '%s view: %d pixels differ from the view without the floor' % (key, differing)


def test_the_text_checks_run_again_at_dpr_2(qt_app, project_root) -> None:
    """
    Description:
        This module, run again in a fresh interpreter at DPR 2, passes: the contrast is measured there too,
        the high-density comparison passes, and the low-density floor test is the one that skips.
    """

    if qt_app.devicePixelRatio() >= Style.CONST_LOW_DENSITY_DPR:
        pytest.skip('this is the DPR %g run' % qt_app.devicePixelRatio())
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_SCALE_FACTOR=CONST_HIGH_DENSITY_SCALE, PYTHONDONTWRITEBYTECODE='1')
    run = subprocess.run([sys.executable, '-m', 'pytest', os.path.abspath(__file__), '-rA', '-p', 'no:cacheprovider'],
                         cwd=project_root, env=env, capture_output=True, text=True, timeout=600)
    report = run.stdout + run.stderr
    assert run.returncode == 0, report[-3000:]
    for passed in ('test_every_enabled_text_clears_the_floor', 'test_a_high_density_display_draws_what_it_drew_without_the_floor'):
        assert 'PASSED test/UI/test_text_contrast.py::%s' % passed in report, report[-3000:]
    assert 'the floor is measured in the DPR 1 run' in report, report[-3000:]
