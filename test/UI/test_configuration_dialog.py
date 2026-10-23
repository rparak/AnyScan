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
# File Name: ../test/UI/test_configuration_dialog.py
## =========================================================================== ##

# System (Default)
import os
import json
import time
import threading
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Typing (Support for type hints)
import typing as tp
# PyYAML (YAML parser and emitter) [pip3 install pyyaml]
import yaml
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt, QEvent, QPointF, QTimer
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QApplication, QPushButton, QLabel, QListWidget, QProgressBar
# Custom Lib.: AnyScan UI — the window and the dialog under test
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
#   ../UI/Configuration_Dialog
from UI.Configuration_Dialog import Configuration_Dialog_Cls
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
# Custom Lib.: AnyScan domain — the camera, the vision interface, the logger, the capture reader
#   ../Camera/Core
from Camera.Core import Camera_Backend_Cls
#   ../Vision/Core
import Vision.Core as Vision_Core
from Vision.Core import Vision_Backend_Cls, Vision_Error_Cls, Vision_Pipeline_Cls
#   ../Logger/Core
from Logger.Core import Session_Logger_Cls
#   ../UI/Capture
from UI.Capture import Discover_Capture_Sets
#   ../Parameters/Vision
from Parameters.Vision import Analysis_Str
#   ../Parameters/Configuration
from Parameters.Configuration import Identity_Str
# Custom Lib.: AnyScan — the configuration layer
#   ../Configuration/Core
from Configuration.Core import (Load_Configuration, Mode_Directory, Station_Directory, Calibration_Directory,
                                CONST_DEFAULT_CONFIG_FILE)

"""
Description:
    The Configuration dialog and the configuration gates, without weights. A run starts with a
    configuration named but not loaded, so CONNECT (and with it everything after) waits for the
    dialog; the dialog lists the usable configurations in Configuration/, loads the chosen one on a
    worker thread, confirms what it loaded in a sentence and closes, or says why it did not; files
    it cannot load are logged, not listed; an empty directory says so. After the first CONNECT the
    configuration is fixed for the run. The window dims behind the dialog and the dim lifts on every
    close path. Capture sets record the configuration, its background reference and its hardware.
    A stand-in vision backend stands for the models (it sleeps where they would load).
"""
# The window's name-mangling prefix, and the shipped hardware.
#   Unit [string]
CONST_MANGLE = '_AnyScan_Window_Cls'
CONST_HARDWARE = 'a2A1920_51gcPRO_Computar_M1228_MPW3'
# The dialog's name-mangling prefix.
#   Unit [string]
CONST_DIALOG_MANGLE = '_Configuration_Dialog_Cls'
# How long each stand-in model step (a load, a segmentation, a description) takes, so every phase of
# a load stays on screen long enough to be seen.
#   Unit [float] (s)
CONST_MODEL_STEP = 0.25
# The confirmation for the shipped configuration's camera, lens and lighting.
#   Unit [string]
CONST_SENTENCE = ('Configuration loaded. Model set JIC_AnyScan_All_v1 on a Basler a2A1920-51gcPRO with a '
                  'Computar M1228-MPW3 lens, lit by an Effilux EFFI-FD-200-200-000.')


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


def _Private(owner: tp.Any, name: str) -> tp.Any:
    """A name-mangled private attribute of the window."""
    return getattr(owner, CONST_MANGLE + name)


class _Fake_Vision_Cls(Vision_Backend_Cls):
    """A vision backend whose configuration takes `delay` seconds to load on whatever thread loads it."""

    def __init__(self, loaded: bool = False, delay: float = 0.2, fail: tp.Optional[str] = None) -> None:
        self.Models_Loaded, self.delay, self.fail = loaded, delay, fail
        self.Name, self.Model_Names = 'JIC_AnyScan_All_v1', ('FastSAM-x.pt', 'gemma-4-e4b-it-4bit')
        self.threads = []

    def Configure(self, Configuration_Str, stage_cb=None) -> None:
        self.threads.append(threading.get_ident())
        time.sleep(self.delay)
        if self.fail:
            raise Vision_Error_Cls(self.fail)
        self.Models_Loaded, self.Name = True, Configuration_Str.Identity.Model_Set


class _Idle_Camera_Cls(Camera_Backend_Cls):
    """A camera that connects at once and grabs a fixed frame."""

    def _Open(self) -> None:
        pass

    def _Close(self) -> None:
        pass

    def _Grab(self):
        return np.zeros((40, 60, 3), dtype=np.uint8)

    @property
    def Resolution(self):
        return (60, 40)


def _Pump_Until(condition: tp.Callable[[], bool], timeout: float = 10.0) -> None:
    """Run the event loop until the condition holds (or the timeout passes)."""
    app, deadline = QApplication.instance(), time.time() + timeout
    while not condition() and time.time() < deadline:
        app.processEvents()
        time.sleep(0.005)


def _Mode_File(directory: tp.Any, mode: str, hardware: str = CONST_HARDWARE,
               edit: tp.Optional[tp.Callable[[tp.Dict], None]] = None) -> str:
    """
    A mode file (from the shipped one, optionally edited) in a directory, naming its hardware's station. For
    hardware other than the shipped one, that station and its calibration are written into the test's
    Configuration/ (configuration_root) from the shipped ones, renamed for the hardware.
    """
    with open(CONST_DEFAULT_CONFIG_FILE, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    data['Hardware'], data['Station'] = hardware, data['Station'].replace(CONST_HARDWARE, hardware)
    if edit is not None:
        edit(data)
    path = os.path.join(str(directory), 'Config_%s_Mode_%s.yaml' % (hardware, mode))
    with open(path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, sort_keys=False)
    for folder in (Station_Directory(), Calibration_Directory()):
        for name in [name for name in os.listdir(folder) if CONST_HARDWARE in name]:
            target = os.path.join(folder, name.replace(CONST_HARDWARE, hardware))
            if not os.path.exists(target):
                with open(os.path.join(folder, name), 'r', encoding='utf-8') as f:
                    text = f.read().replace(CONST_HARDWARE, hardware)
                with open(target, 'w', encoding='utf-8') as f:
                    f.write(text)
    return path


@pytest.fixture
def configurations(configuration_root) -> tp.Dict[str, str]:
    """A Configuration/Mode/ directory the dialog discovers: two modes on this camera, one on another
    camera, one broken file (Model_Set missing) and an unrelated YAML."""
    directory = Mode_Directory()
    paths = {'seg': _Mode_File(directory, 'Seg_Anything'),
             'second': _Mode_File(directory, 'Inspect', edit=lambda d: d['Identity'].update(Display_Name='Cfg. Inspection')),
             'other': _Mode_File(directory, 'Seg_Anything', hardware='acA2500_14gc_Fujinon_HF16',
                                 edit=lambda d: d['Identity'].update(Display_Name='Cfg. Bench Camera')),
             'broken': _Mode_File(directory, 'Draft', edit=lambda d: d['Identity'].pop('Model_Set'))}
    with open(os.path.join(directory, 'notes.yaml'), 'w', encoding='utf-8') as f:
        f.write('Hardware: x\n')
    paths['dir'] = directory
    return paths


def _Window(tmp_path: tp.Any, config_path: str, vision: _Fake_Vision_Cls) -> tp.Tuple[AnyScan_Window_Cls,
                                                                                    Session_Logger_Cls]:
    """A window started with a configuration (named, not loaded), a real logger, an idle camera."""
    logger = Session_Logger_Cls(config_path=config_path, log_dir=str(tmp_path / 'log'), install_handlers=False)
    window = AnyScan_Window_Cls(camera=_Idle_Camera_Cls(), logger=logger,
                                Configuration_Str=Load_Configuration(config_path))
    setattr(window, CONST_MANGLE + '__vision', vision)
    _Private(window, '__Sync_Controls')()
    return window, logger


def _Log_Text(logger: Session_Logger_Cls) -> str:
    """The current log file content."""
    with open(logger.Path, 'r', encoding='utf-8') as handle:
        return handle.read()


def _Press(button: QPushButton) -> None:
    """A mouse press on a (possibly disabled) button, delivered the way Qt delivers a click."""
    QApplication.sendEvent(button, QMouseEvent(QEvent.MouseButtonPress, QPointF(5, 5), Qt.LeftButton,
                                               Qt.LeftButton, Qt.NoModifier))


def _Load_Through_Dialog(window: AnyScan_Window_Cls, path: str) -> Configuration_Dialog_Cls:
    """Open the window's wired dialog (without its modal loop), choose a file, Load, and wait."""
    dialog = _Private(window, '__Make_Configuration_Dialog')()
    dialog.Select(path)
    dialog.Load()
    _Pump_Until(lambda: not dialog.Loading)
    return dialog


def _Texts(widget: tp.Any) -> tp.List[str]:
    """The visible label texts of a widget, with the display-only wrap points removed."""
    return [label.text().replace('​', '') for label in widget.findChildren(QLabel) if label.isVisible()]


def test_a_run_starts_named_but_not_loaded_and_connect_waits_for_the_configuration(qt_app, tmp_path,
                                                                                    configurations) -> None:
    """
    Description:
        At launch the configuration is named but not loaded: the header says so — with a dash where
        the model set goes, since no configuration is in force to name one — and CONNECT is
        disabled; its tooltip says why, and a press on it is logged as a refusal. Loading the
        configuration makes CONNECT available and the header names the model set.
    """

    window, logger = _Window(tmp_path, configurations['seg'], _Fake_Vision_Cls(loaded=False))
    connect = _Private(window, '__button_connect')
    assert _Private(window, '__label_models_state').text().endswith('Configuration not loaded.')
    assert _Private(window, '__label_model_name').text() == '—'
    assert not connect.isEnabled() and connect.toolTip() == 'Load a configuration first.'
    _Press(connect)

    _Load_Through_Dialog(window, configurations['seg'])
    assert connect.isEnabled() and connect.toolTip() == ''
    assert _Private(window, '__label_models_state').text().endswith('Configuration loaded.')
    assert _Private(window, '__label_model_name').text() == 'JIC_AnyScan_All_v1'
    logger.Close()
    assert 'CONNECT refused: no configuration is loaded' in _Log_Text(logger)


def test_after_the_first_connect_the_configuration_is_fixed_for_the_run(qt_app, tmp_path, configurations) -> None:
    """
    Description:
        CONFIGURATION is available until the first CONNECT; from then on it is disabled for the rest
        of the run — it does NOT come back on DISCONNECT — with the one-line tooltip, and a press is
        logged. CONNECT itself is restored on DISCONNECT: the configuration is still loaded.
    """

    window, logger = _Window(tmp_path, configurations['seg'], _Fake_Vision_Cls(loaded=True))
    button, connect = _Private(window, '__button_configuration'), _Private(window, '__button_connect')
    assert button.isEnabled() and button.toolTip() == ''

    _Private(window, '__On_Connect_Button_Clicked')()
    _Pump_Until(lambda: _Private(window, '__camera').Connected and _Private(window, '__conn_thread') is None)
    assert not button.isEnabled() and button.toolTip() == 'Restart to change configuration.'
    _Private(window, '__On_Disconnect_Button_Clicked')()
    assert not button.isEnabled() and button.toolTip() == 'Restart to change configuration.'
    assert connect.isEnabled()                                          # restored: still loaded
    _Press(button)
    logger.Close()
    log = _Log_Text(logger)
    assert 'Configuration change refused: the camera has connected in this run. Restart to change configuration.' in log
    assert "configuration '%s'" % os.path.basename(configurations['seg']) in log     # session-start line


def test_the_dialog_lists_usable_configurations_and_logs_the_rest(qt_app, tmp_path, configurations) -> None:
    """
    Description:
        The list holds the usable configurations by display name, the one in force marked (bold)
        and selected, this camera's first; another camera's is shown greyed and cannot be chosen.
        A file that cannot be loaded is not listed — it is logged at WARNING with its name and the
        reason, once — and a YAML that is not a mode file is ignored.
    """

    logged = []
    config = Load_Configuration(configurations['seg'])
    dialog = Configuration_Dialog_Cls(_Fake_Vision_Cls(), config, log_cb=lambda l, m: logged.append((l, m)))
    listed = dialog.findChild(QListWidget)
    items = [listed.item(row) for row in range(listed.count())]
    assert [item.text() for item in items] == ['Cfg. Inspection', 'Cfg. Segment Anything', 'Cfg. Bench Camera']
    assert listed.currentItem() is items[1] and items[1].font().bold()
    assert not items[2].flags() & Qt.ItemIsEnabled and 'Other hardware' in items[2].toolTip()
    (level, message), = logged
    assert level == 'WARNING' and os.path.basename(configurations['broken']) in message
    assert 'Identity.Model_Set is required but missing' in message


def test_an_empty_directory_says_so_where_the_list_would_be(qt_app, tmp_path, configuration_root) -> None:
    """
    Description:
        With no usable configuration the list is replaced by a message naming the directory searched
        and saying CONNECT stays unavailable — and there is nothing to Load.
    """

    empty = Mode_Directory()                                          # configuration_root's Mode/ is empty
    config = Load_Configuration(_Mode_File(tmp_path, 'Seg_Anything'))
    os.remove(config.Path)                                            # the one in force is gone too
    dialog = Configuration_Dialog_Cls(_Fake_Vision_Cls(), config)
    dialog.show()
    assert not dialog.findChild(QListWidget).isVisible()
    (text,) = [t for t in _Texts(dialog) if t.startswith('No usable configuration')]
    assert 'CONNECT stays unavailable' in text and os.path.basename(str(empty)) in text
    assert not {b.text(): b for b in dialog.findChildren(QPushButton)}['LOAD'].isEnabled()
    dialog.reject()


def test_loading_runs_off_the_gui_thread_then_confirms_and_stays_open(qt_app, tmp_path, configurations) -> None:
    """
    Description:
        Load runs on a WORKER thread: the event loop keeps turning, 'Loading configuration…' and the
        progress show, the controls are locked and the dialog refuses to close. It then confirms in
        a sentence built from the configuration — the model set, camera, lens and lighting, nothing
        about model files, load time or task — moves the marker, and STAYS OPEN, so the sentence can
        be read: LOAD has nothing left to do until another configuration is selected.
    """

    vision = _Fake_Vision_Cls(delay=0.3)
    config = Load_Configuration(configurations['seg'])
    dialog = Configuration_Dialog_Cls(vision, config)
    loaded, started = [], []
    dialog.Configuration_Loaded.connect(lambda c, s: loaded.append(c))
    dialog.Load_Started.connect(lambda: started.append(1))
    ticks = []
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start(20)
    dialog.show()
    dialog.Select(configurations['second'])
    dialog.Load()
    buttons = {button.text(): button for button in dialog.findChildren(QPushButton)}
    assert dialog.Loading and started and 'Loading configuration…' in _Texts(dialog)
    assert dialog.findChild(QProgressBar).isVisible()
    assert not buttons['LOAD'].isEnabled() and not buttons['CLOSE'].isEnabled()
    dialog.reject()
    assert dialog.isVisible()                                         # refused while loading
    _Pump_Until(lambda: not dialog.Loading)
    timer.stop()

    assert vision.threads[0] != threading.get_ident() and len(ticks) >= 5
    assert len(loaded) == 1 and loaded[0].Mode == 'Inspect'
    (sentence,) = [t for t in _Texts(dialog) if t.startswith('Configuration loaded.')]
    assert sentence == CONST_SENTENCE
    listed = dialog.findChild(QListWidget)
    assert listed.currentItem().text() == 'Cfg. Inspection' and listed.currentItem().font().bold()
    assert not buttons['LOAD'].isEnabled() and buttons['CLOSE'].isEnabled()
    _Pump_Until(lambda: False, timeout=2.5)
    assert dialog.isVisible()                                         # no auto-close
    dialog.Select(configurations['seg'])
    assert buttons['LOAD'].isEnabled()                                # another one: something to do
    dialog.reject()
    assert not dialog.isVisible()


@pytest.mark.parametrize('slot, fail', [('__On_Load_Finished', None), ('__On_Load_Failed', 'The model file is missing.')],
                         ids=['load finished', 'load failed'])
def test_the_load_thread_has_ended_when_the_dialog_has_taken_its_result(qt_app, monkeypatch, configurations, slot,
                                                                         fail) -> None:
    """
    Description:
        The dialog's slot that takes the loader's result joins the loader's thread before it lets the
        worker go (UI.Workers.Join_Worker_Thread), so the thread has ENDED when the slot returns. Without
        the join it is still running then, and letting the worker go makes PyQt delete it on that thread
        while the GUI thread goes on into the window's Configuration_Loaded handler: the deadlock the UI
        suite hung on (sampled in test_timing_log's configuration load).
    """

    config = Load_Configuration(configurations['seg'])
    dialog = Configuration_Dialog_Cls(_Fake_Vision_Cls(delay=0.05, fail=fail), config)
    seen = {'thread': None, 'running after the slot': []}
    original = getattr(Configuration_Dialog_Cls, CONST_DIALOG_MANGLE + slot)

    def _Observed(self, *args) -> None:
        original(self, *args)
        seen['running after the slot'].append(seen['thread'].isRunning())

    monkeypatch.setattr(Configuration_Dialog_Cls, CONST_DIALOG_MANGLE + slot, _Observed)
    dialog.Select(configurations['second'])
    dialog.Load()
    seen['thread'] = getattr(dialog, CONST_DIALOG_MANGLE + '__thread')
    _Pump_Until(lambda: bool(seen['running after the slot']))
    dialog.reject()
    assert seen['running after the slot'] == [False]


def test_a_failed_load_says_so_and_the_previous_configuration_stays(qt_app, tmp_path, configurations) -> None:
    """
    Description:
        When the configuration cannot be loaded the dialog says 'Configuration was not loaded.' with
        the reason, stays open, and the window keeps its configuration; the error is logged.
    """

    reason = 'The FastSAM weights are missing. Cfg. Segment Anything is still in force, not loaded.'
    window, logger = _Window(tmp_path, configurations['seg'], _Fake_Vision_Cls(delay=0.05, fail=reason))
    before = _Private(window, '__config')
    dialog = _Load_Through_Dialog(window, configurations['second'])
    dialog.show()
    assert 'Configuration was not loaded. %s' % reason in _Texts(dialog)
    assert _Private(window, '__config') is before
    assert not _Private(window, '__button_connect').isEnabled()
    dialog.reject()
    logger.Close()
    assert 'Configuration was not loaded. %s' % reason in _Log_Text(logger)


def test_a_loaded_configuration_is_applied_and_logged(qt_app, tmp_path, configurations) -> None:
    """
    Description:
        A loaded configuration is applied to the window — classification, the header's model set,
        the camera — and logged with its calibration and background reference, and the detail the
        dialog leaves out (model files, load time, task). Nothing is reset: nothing can have
        accumulated before the first CONNECT.
    """

    def _Edit(data):
        # A catalogue mode classifies.
        data['Catalogue'] = {'Item': 'Data/Catalogue/mounting_plate/mounting_plate.yaml',
                             'Identifier': 'models/dinov2-base'}
        data['Identity'].update(Display_Name='Cfg. Strict', Model_Set='JIC_AnyScan_Strict_v1')
        data['Identity'].pop('Task')

    strict = _Mode_File(configurations['dir'], 'Strict', edit=_Edit)
    window, logger = _Window(tmp_path, configurations['seg'], _Fake_Vision_Cls(delay=0.05))
    _Load_Through_Dialog(window, strict)
    config = _Private(window, '__config')
    assert config.Mode == 'Strict' and _Private(window, '__classification_enabled') is True
    assert _Private(window, '__label_model_name').text() == 'JIC_AnyScan_Strict_v1'
    assert _Private(window, '__camera')._configuration_name == config.Name
    logger.Close()
    log = _Log_Text(logger)
    assert "Loaded configuration '%s' ('Cfg. Strict'" % config.Name in log
    assert 'reads station ' in log and 'Station_%s.yaml, calibration ' % CONST_HARDWARE in log
    assert '%s, background reference' % os.path.basename(config.Calibration_Path) in log
    assert ('background reference Data/Images/Background/Image_Background_001.png and catalogue item '
            'Data/Catalogue/mounting_plate/mounting_plate.yaml' in log)
    # The file sets no Task, so the code's default is the one in force, read from where it is defined.
    assert "Models loaded for '%s' (JIC_AnyScan_Strict_v1, task '%s')" % (config.Name, Identity_Str().Task) in log
    assert 'Identity.Task not set; using the default' in log
    assert 'Run reset' not in log


def _Dim_While_Open(window: AnyScan_Window_Cls, act: tp.Callable[[Configuration_Dialog_Cls], None]) -> tp.List[bool]:
    """Open the dialog through the button (its real modal loop), run `act` inside it, and record
    whether the window was dimmed while it was open."""
    seen = []

    def _Inside():
        dialog = QApplication.activeModalWidget()
        seen.append(_Private(window, '__scrim').isVisible())
        act(dialog)

    QTimer.singleShot(50, _Inside)
    window.show()
    _Private(window, '__On_Configuration_Button_Clicked')()
    return seen


def test_the_window_dims_behind_the_dialog_and_the_dim_lifts_on_every_close(qt_app, tmp_path,
                                                                            configurations) -> None:
    """
    Description:
        The window is dimmed while the dialog is open, and the dim lifts however it closes: CLOSE
        with nothing loaded, and CLOSE after a load. A close attempted mid-load is refused, so the dim
        cannot be left behind by a dialog dismissed while loading. After the load and CLOSE the
        sequence holds: the dim is gone, the header says loaded, CONNECT is available.
    """

    window, logger = _Window(tmp_path, configurations['seg'], _Fake_Vision_Cls(delay=0.3))
    assert not _Private(window, '__scrim').isVisible()
    assert _Dim_While_Open(window, lambda dialog: dialog.reject()) == [True]
    assert not _Private(window, '__scrim').isVisible()

    refused_mid_load = []

    def _Load_Then_Try_To_Close(dialog):
        dialog.Select(configurations['second'])
        dialog.Load()
        dialog.reject()                                               # mid-load: refused
        refused_mid_load.append(dialog.isVisible())
        _Pump_Until(lambda: not dialog.Loading)
        assert _Private(window, '__scrim').isVisible()                # still dimmed while it is read
        dialog.reject()                                               # the deliberate CLOSE

    assert _Dim_While_Open(window, _Load_Then_Try_To_Close) == [True]
    assert refused_mid_load == [True]
    assert not _Private(window, '__scrim').isVisible()
    assert _Private(window, '__config').Mode == 'Inspect'
    assert _Private(window, '__label_models_state').text().endswith('Configuration loaded.')
    assert _Private(window, '__button_connect').isEnabled()
    window.close()
    logger.Close()


def test_each_capture_set_records_its_configuration_reference_and_hardware(qt_app, tmp_path,
                                                                          configurations, scan) -> None:
    """
    Description:
        Every capture set stores the configuration's name, the background reference it was
        differenced against, and the camera, lens and lighting — what photographed it and what lit
        it — and the set read back carries all three.
    """

    window, logger = _Window(tmp_path, configurations['seg'], _Fake_Vision_Cls(loaded=True))
    _Private(window, '__On_Connect_Button_Clicked')()
    _Pump_Until(lambda: _Private(window, '__camera').Connected and _Private(window, '__conn_thread') is None)
    scan(window)
    setattr(window, CONST_MANGLE + '__current_set_id', '20260924-100000_1')
    _Private(window, '__On_Analysis_Finished')(
        Analysis_Str(Objects=[], Background='A plain surface.', Latency_Ms=100, Verdict='Empty',
                     Verdict_Level='ok', Task='part inspection'))
    logger.Close()

    captures = os.path.join(str(tmp_path / 'log'), 'captures')
    (metadata_path,) = [os.path.join(root, name) for root, _dirs, names in os.walk(captures)
                        for name in names if name.endswith('_objects.json')]
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    name = os.path.basename(configurations['seg'])
    assert metadata['configuration'] == name and metadata['classification'] is False
    assert metadata['background_reference'] == os.path.join('Data', 'Images', 'Background', 'Image_Background_001.png')
    assert metadata['hardware'] == {'hardware': CONST_HARDWARE, 'camera': 'Basler a2A1920-51gcPRO',
                                    'lens': 'Computar M1228-MPW3', 'lighting': 'Effilux EFFI-FD-200-200-000'}
    (cap,) = Discover_Capture_Sets(captures)
    assert (cap.Configuration, cap.Background_Reference) == (name, metadata['background_reference'])
    assert cap.Hardware['lighting'] == 'Effilux EFFI-FD-200-200-000'


def test_each_capture_set_records_its_station_and_calibration(qt_app, tmp_path, configurations, scan) -> None:
    """
    Description:
        Calibrations are kept side by side and switched by one line in the station file, so the conversion
        factor alone does not say which one measured a set: every capture set records the file names of the
        station and of the calibration it was analysed under, and reads them back. A set written before they
        were recorded still loads, with both empty.
    """

    window, logger = _Window(tmp_path, configurations['seg'], _Fake_Vision_Cls(loaded=True))
    _Private(window, '__On_Connect_Button_Clicked')()
    _Pump_Until(lambda: _Private(window, '__camera').Connected and _Private(window, '__conn_thread') is None)
    scan(window)
    setattr(window, CONST_MANGLE + '__current_set_id', '20260924-100000_1')
    _Private(window, '__On_Analysis_Finished')(
        Analysis_Str(Objects=[], Background='A plain surface.', Latency_Ms=100, Verdict='Empty',
                     Verdict_Level='ok', Task='part inspection'))
    logger.Close()

    config = Load_Configuration(configurations['seg'])
    captures = os.path.join(str(tmp_path / 'log'), 'captures')
    (metadata_path,) = [os.path.join(root, name) for root, _dirs, names in os.walk(captures)
                        for name in names if name.endswith('_objects.json')]
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    assert (metadata['station'], metadata['calibration']) == (os.path.basename(config.Station_Path),
                                                              os.path.basename(config.Calibration_Path))
    assert metadata['calibration'].startswith('Calibration_%s_' % CONST_HARDWARE)
    (cap,) = Discover_Capture_Sets(captures)
    assert (cap.Station, cap.Calibration) == (metadata['station'], metadata['calibration'])

    del metadata['station'], metadata['calibration']                  # a set from before 2026-10-13
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f)
    (cap,) = Discover_Capture_Sets(captures)
    assert (cap.Station, cap.Calibration) == ('', '') and not cap.Partial     # read whole, not as malformed
    assert cap.Configuration == metadata['configuration'] and cap.Hardware == metadata['hardware']


class _Slow_Segmenter_Cls(object):
    """A stand-in FastSAM that takes a moment to load and to segment, and reports its load as FastSAM does."""
    Last_Inference_S = 0.0

    def __init__(self, Segmentation_Parameters_Str) -> None:
        self.params, self.Loaded = Segmentation_Parameters_Str, False

    @property
    def Model_Key(self):
        return (self.params.Model_Path, self.params.Device)

    def Set_Parameters(self, Segmentation_Parameters_Str) -> None:
        self.params = Segmentation_Parameters_Str

    def Load(self, stage_cb=None) -> None:
        if not self.Loaded:
            if stage_cb:
                stage_cb('Loading segmenter…')
            time.sleep(CONST_MODEL_STEP)
            self.Loaded = True

    def Release(self) -> None:
        self.Loaded = False

    def Segment(self, image, stage_cb=None):
        time.sleep(CONST_MODEL_STEP)
        return [], []


class _Slow_Describer_Cls(object):
    """A stand-in Gemma that takes a moment to load and to describe."""
    Last_Tokens = None

    def __init__(self, Description_Parameters_Str) -> None:
        self.params, self.Loaded = Description_Parameters_Str, False

    @property
    def Model_Key(self):
        return self.params.Model_Path

    def Set_Parameters(self, Description_Parameters_Str) -> None:
        self.params = Description_Parameters_Str

    def Load(self) -> None:
        time.sleep(CONST_MODEL_STEP)
        self.Loaded = True

    def Release(self) -> None:
        self.Loaded = False

    def Describe(self, image, purpose, prompt='') -> str:
        time.sleep(CONST_MODEL_STEP)
        return 'A plain surface.'


def _Grab(widget: tp.Any) -> np.ndarray:
    """What the widget paints now, as an HxWx4 BGRA array (the pixels, not its state)."""
    image = widget.grab().toImage().convertToFormat(4)          # QImage.Format_RGB32
    pointer = image.constBits()
    pointer.setsize(image.byteCount())
    return np.frombuffer(pointer, np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4).copy()


def test_the_loading_line_follows_the_loaders_phases(qt_app, configurations, monkeypatch) -> None:
    """
    Description:
        While a configuration loads, the line under the list follows the loader's own phases as they
        happen — 'Loading configuration…', 'Loading segmenter…', 'Loading model…', 'Warming up…' — so
        a ten-second load visibly moves instead of looking hung, and the warm-up the first analysis
        used to pay is named on screen. The phases come from the real Vision_Pipeline_Cls.Configure
        (stand-in models that take a moment per step; only 'Loading segmenter…' is the FastSAM
        stand-in's own). 'Warming up…' is checked as painted: the shown label's pixels carry text in
        the stage colour, and the text fits the label unclipped.
    """

    monkeypatch.setattr(Vision_Core, 'Fast_Sam_Cls', _Slow_Segmenter_Cls)
    monkeypatch.setattr(Vision_Core, 'Gemma_Describer_Cls', _Slow_Describer_Cls)
    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', 'gemma')
    config = Load_Configuration(configurations['seg'])
    dialog = Configuration_Dialog_Cls(Vision_Pipeline_Cls(Configuration_Str=config), config)
    dialog.show()
    dialog.Select(configurations['second'])
    stage = getattr(dialog, CONST_DIALOG_MANGLE + '__label_stage')
    seen, painted = [], {}

    def _Sample() -> bool:
        if stage.isVisible():
            if not seen or seen[-1] != stage.text():
                seen.append(stage.text())
            if stage.text() == 'Warming up…' and 'Warming up…' not in painted:
                painted['Warming up…'] = _Grab(stage)
        return not dialog.Loading

    dialog.Load()
    _Pump_Until(_Sample)

    assert seen == ['Loading configuration…', 'Loading segmenter…', 'Loading model…', 'Warming up…']
    ink = Style.CONST_INK_SOFT.lstrip('#')
    bgr = np.array([int(ink[4:6], 16), int(ink[2:4], 16), int(ink[0:2], 16)])
    pixels = painted['Warming up…'][:, :, :3].astype(int)
    assert (np.abs(pixels - bgr).max(axis=2) <= 24).sum() >= 20                  # glyphs, in the stage ink
    assert stage.fontMetrics().horizontalAdvance('Warming up…') <= stage.contentsRect().width()
    dialog.reject()


def test_a_mode_naming_another_station_event_directory_is_refused(qt_app, tmp_path, configurations) -> None:
    """
    Description:
        The station-event directory is fixed for the run by the startup configuration — this run's log
        is exported there at close — so a mode that names another is refused like one for other
        hardware: the dialog says why, naming both directories, and the configuration in force stays.
    """

    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    path = _Mode_File(configurations['dir'], 'Elsewhere', edit=lambda d: d['General']['Station_Events'].update(
        Directory=str(elsewhere)))
    window, logger = _Window(tmp_path, configurations['seg'], _Fake_Vision_Cls(loaded=False))
    in_force = _Private(window, '__config')
    dialog = _Load_Through_Dialog(window, path)
    dialog.show()
    shown = ' '.join(_Texts(dialog))
    assert 'exports station events to %s' % elsewhere in shown
    assert 'this run exports them to %s' % in_force.Station_Events_Directory in shown
    assert _Private(window, '__config') is in_force
    dialog.reject()
    logger.Close()
    assert '[WARNING] Configuration not loaded:' in _Log_Text(logger)
