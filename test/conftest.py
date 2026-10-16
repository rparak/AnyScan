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
# File Name: ../test/conftest.py
## =========================================================================== ##

# System (Default)
import os
import sys
import time
import traceback
import types
import atexit
import faulthandler
from datetime import datetime
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Typing (Support for type hints)
import typing as tp

"""
Description:
    Initialization of constants.
"""
# The repository root, resolved from this file's location (test/ -> ..). Every
# path fixture below is derived from it, so the suite is independent of the
# current working directory.
#   Unit [string]
CONST_PROJECT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# The committed reference background and its expected size. The size is the app's
# contract: segmentation differences a frame against this reference, so a frame
# must match it. cv2 reports shape as (height, width, channels).
#   Unit [string]
CONST_REFERENCE_BACKGROUND = os.path.join(CONST_PROJECT_FOLDER, 'Data', 'Images', 'Background', 'Image_Background_001.png')
#   Unit [Tuple<int> 1x3]
CONST_REFERENCE_SHAPE = (1200, 1920, 3)

# The model runtimes a weights test must meet as the installed packages, never as fake_runtimes'
# stand-ins (which have no file). 'mlx' itself is a namespace package with no file, so mlx.core
# stands for it.
#   Unit [Vector<string>]
CONST_RUNTIME_MODULES = ('torch', 'ultralytics', 'mlx.core', 'mlx_vlm', 'mlx_vlm.prompt_utils')

# Directories the domain code and the harness live in, added to the import path
# so tests can import the extracted src/ modules, the application entry (run) and
# the analysis harness (Example/Vision/analyze.py) without any package wrapping.
#   Unit [Vector<string>]
CONST_IMPORT_PATHS = [
    os.path.join(CONST_PROJECT_FOLDER, 'src'),
    os.path.join(CONST_PROJECT_FOLDER, 'App'),
    os.path.join(CONST_PROJECT_FOLDER, 'Example', 'Vision'),
]

for _path in CONST_IMPORT_PATHS:
    if _path not in sys.path:
        sys.path.insert(0, _path)

# The crash record: test/crash_records/crash_record.txt (git-ignored) names each test as it starts and
# receives faulthandler's dump of every thread on a fatal error, so a crash leaves its test and its stacks
# on disk even when the terminal output is lost. One full run on 2026-10-08 died with only a fatal-error
# dump's last line seen (KNOWN_ISSUES.md). A run that exits ends its record with CONST_CRASH_RECORD_CLEAN;
# the next run overwrites such a record and keeps one without it as crash_record_<its time>.txt, the
# newest CONST_CRASH_RECORD_KEEP of those, so running the suite again never deletes a crash. It is outside
# pytest's temp directories, which pytest rotates (three kept; a full run makes three).
#   Unit [string]
CONST_CRASH_RECORD_DIR = os.path.join(CONST_PROJECT_FOLDER, 'test', 'crash_records')
CONST_CRASH_RECORD_NAME = 'crash_record.txt'
CONST_CRASH_RECORD_CLEAN = 'CLEAN EXIT'
#   Unit [int]
CONST_CRASH_RECORD_KEEP = 10
# The environment: a folder in place of CONST_CRASH_RECORD_DIR (the crash-record test's probe runs), and
# the pid of the session that records. The suite's nested pytest runs (test_header.py's and
# test_text_contrast.py's DPR 2 re-runs) inherit it and record nothing: on the one fixed file they would
# take the running parent's unfinished record for a crash.
#   Unit [string]
CONST_CRASH_RECORD_DIR_VARIABLE = 'ANYSCAN_CRASH_RECORD_DIR'
CONST_CRASH_RECORD_OWNER_VARIABLE = 'ANYSCAN_CRASH_RECORD_OWNER'
#   Unit [StashKey(object)]
CONST_CRASH_RECORD_FD = pytest.StashKey[int]()
CONST_CRASH_RECORD_PATH = pytest.StashKey[str]()


# << PYTEST HOOK >> #
def pytest_addoption(parser: pytest.Parser) -> None:
    """
    Description:
        Register the command-line flags:
          --runslow        Tests that genuinely need the model weights (FastSAM, Gemma) or other
                           heavy runtime are marked `slow` and skipped unless it is given, so the
                           default run needs no camera and no model.
          --update-golden  A golden-file test rewrites its committed file from the current
                           output instead of comparing against it — for an INTENDED behaviour
                           change; review the file's diff before committing it.

    Args:
        (1) parser [pytest.Parser(object)]: The pytest command-line parser.
    """

    parser.addoption('--runslow', action='store_true', default=False,
                     help='run tests marked slow (they need the model weights).')
    parser.addoption('--update-golden', action='store_true', default=False,
                     help='rewrite golden files from the current output (then review the diff).')


# << PYTEST HOOK >> #
def pytest_collection_modifyitems(config: pytest.Config, items: tp.List[pytest.Item]) -> None:
    """
    Description:
        Skip every `slow` test unless --runslow was passed, keeping the weights
        out of the default run. A test is slow when it carries the marker (on itself, its class or its
        module), not when 'slow' is merely among its keywords: those also hold its parents' names, the
        session's included, which is the folder the run starts in, so a checkout in a folder named
        'slow' would skip every test.

    Args:
        (1) config [pytest.Config(object)]: The active pytest configuration.
        (2) items [Vector<pytest.Item>]: The collected test items.
    """

    if config.getoption('--runslow'):
        return

    skip_slow = pytest.mark.skip(reason='needs the model weights; pass --runslow to run.')
    for item in items:
        if item.get_closest_marker('slow') is not None:
            item.add_marker(skip_slow)



def _Keep_Crashed_Record(folder: str) -> None:
    """
    Description:
        Before a run overwrites the crash record, keep the previous one if its run did not exit — no
        CONST_CRASH_RECORD_CLEAN as its last line — as crash_record_<its last write>.txt, then remove
        all but the newest CONST_CRASH_RECORD_KEEP kept records, oldest first.

    Args:
        (1) folder [string]: The crash-record folder.
    """

    path = os.path.join(folder, CONST_CRASH_RECORD_NAME)
    if os.path.isfile(path):
        with open(path, 'r', encoding='utf-8', errors='replace') as handle:
            lines = handle.read().splitlines()
        if not lines or lines[-1] != CONST_CRASH_RECORD_CLEAN:
            stamp = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d_%H-%M-%S')
            kept, number = os.path.join(folder, 'crash_record_%s.txt' % stamp), 1
            while os.path.exists(kept):
                number += 1
                kept = os.path.join(folder, 'crash_record_%s_%d.txt' % (stamp, number))
            os.replace(path, kept)
    crashed = sorted(name for name in os.listdir(folder)
                     if name.startswith('crash_record_') and name.endswith('.txt'))
    for name in crashed[:-CONST_CRASH_RECORD_KEEP]:
        os.remove(os.path.join(folder, name))


# << PYTEST HOOK >> #
@pytest.hookimpl(trylast=True)
def pytest_configure(config: pytest.Config) -> None:
    """
    Description:
        Start this run's crash record and send faulthandler's fatal-error dump to it, every thread's
        stack, after keeping the previous record if its run crashed. It runs after pytest's own
        faulthandler plugin, which pointed the dump at stderr, so the record replaces that destination
        for the whole session. A nested run (CONST_CRASH_RECORD_OWNER_VARIABLE set by another process)
        records nothing. The record ends with CONST_CRASH_RECORD_CLEAN when the process exits through
        Python; a crash after that, in the interpreter's own finalisation, is not kept.

    Args:
        (1) config [pytest.Config(object)]: The active pytest configuration.
    """

    owner = os.environ.get(CONST_CRASH_RECORD_OWNER_VARIABLE)
    if owner and owner != str(os.getpid()):
        return
    os.environ[CONST_CRASH_RECORD_OWNER_VARIABLE] = str(os.getpid())
    folder = os.environ.get(CONST_CRASH_RECORD_DIR_VARIABLE) or CONST_CRASH_RECORD_DIR
    os.makedirs(folder, exist_ok=True)
    _Keep_Crashed_Record(folder)
    path = os.path.join(folder, CONST_CRASH_RECORD_NAME)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_APPEND, 0o644)
    config.stash[CONST_CRASH_RECORD_FD] = fd
    config.stash[CONST_CRASH_RECORD_PATH] = path
    os.write(fd, ('pytest run started %s, pid %d: %s\n' % (datetime.now().isoformat(timespec='seconds'),
                                                           os.getpid(), ' '.join(sys.argv))).encode('utf-8'))
    faulthandler.enable(file=fd, all_threads=True)
    # Registered now, so it runs after every exit handler a test registers later (atexit is last-in, first-out).
    atexit.register(os.write, fd, (CONST_CRASH_RECORD_CLEAN + '\n').encode('utf-8'))


# << PYTEST HOOK >> #
def pytest_report_header(config: pytest.Config) -> str:
    """
    Description:
        Say where the crash record is, so whoever sees a run die knows where to look.

    Args:
        (1) config [pytest.Config(object)]: The active pytest configuration.

    Returns:
        (1) parameter [string]: The header line.
    """

    return 'crash record: %s' % config.stash.get(CONST_CRASH_RECORD_PATH, '(none)')


# << PYTEST HOOK >> #
@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(item: pytest.Item, nextitem: tp.Optional[pytest.Item]) -> None:
    """
    Description:
        Write the test's node id to the crash record before its setup starts, unbuffered, so a dump
        that follows it belongs to that test (its setup, call or teardown).

    Args:
        (1) item [pytest.Item(object)]: The test.
        (2) nextitem [pytest.Item(object)]: The next test, or None.

    Returns:
        (1) parameter [None]: None, so the run protocol goes on as usual.
    """

    fd = item.config.stash.get(CONST_CRASH_RECORD_FD, None)
    if fd is not None:
        os.write(fd, ('START %s\n' % item.nodeid).encode('utf-8'))
    return None


# << PYTEST HOOK >> #
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """
    Description:
        Mark the end of the tests in the crash record: a dump after this line is not a test's.

    Args:
        (1) session [pytest.Session(object)]: The test session.
        (2) exitstatus [int]: The session's exit status.
    """

    fd = session.config.stash.get(CONST_CRASH_RECORD_FD, None)
    if fd is not None:
        os.write(fd, ('SESSION FINISHED, exit status %d\n' % exitstatus).encode('utf-8'))


# << PYTEST HOOK >> #
@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config: pytest.Config) -> None:
    """
    Description:
        pytest's faulthandler plugin turns the dump off as it unconfigures; turn it back on to the crash
        record, so a crash at interpreter exit is recorded too. The descriptor stays open for that and
        closes with the process.

    Args:
        (1) config [pytest.Config(object)]: The active pytest configuration.
    """

    fd = config.stash.get(CONST_CRASH_RECORD_FD, None)
    if fd is not None:
        os.write(fd, b'UNCONFIGURED: a dump below happened at interpreter exit\n')
        faulthandler.enable(file=fd, all_threads=True)


def _Guard_Qt_Callbacks(phase: str) -> tp.Generator[None, tp.Any, tp.Any]:
    """
    Description:
        Run one phase of a test (setup, call or teardown) with sys.excepthook replaced, and fail that
        phase if an exception escaped a Qt callback during it. PyQt5 hands an exception raised in a
        Python override of a Qt virtual (paintEvent, eventFilter, ...) or in a slot to sys.excepthook
        when that hook has been replaced; left at Python's default it calls qFatal and the process
        aborts, which takes every later test's result with it. A test that sets its own hook
        (test_paint_smoke.py's paint_errors) handles its exceptions itself.

    Args:
        (1) phase [string]: The phase's name, for the failure message.

    Returns:
        (1) parameter [Generator]: The pluggy wrapper: yields once to run the phase.
    """

    errors = []
    previous = sys.excepthook
    sys.excepthook = lambda kind, value, trace: errors.append(''.join(traceback.format_exception(kind, value, trace)))
    try:
        result = yield
    finally:
        sys.excepthook = previous
    if errors:
        pytest.fail('%d unhandled exception(s) in a Qt callback during the test %s:\n\n%s'
                    % (len(errors), phase, '\n'.join(errors)), pytrace=False)
    return result


@pytest.hookimpl(wrapper=True)
def pytest_runtest_setup(item: pytest.Item) -> tp.Generator[None, tp.Any, tp.Any]:
    """
    Description:
        The test's setup (its fixtures), guarded by _Guard_Qt_Callbacks.

    Args:
        (1) item [pytest.Item(object)]: The test.

    Returns:
        (1) parameter [Generator]: The pluggy wrapper.
    """

    return (yield from _Guard_Qt_Callbacks('setup'))


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item: pytest.Item) -> tp.Generator[None, tp.Any, tp.Any]:
    """
    Description:
        The test itself, guarded by _Guard_Qt_Callbacks: an exception in a Qt callback fails the test.

    Args:
        (1) item [pytest.Item(object)]: The test.

    Returns:
        (1) parameter [Generator]: The pluggy wrapper.
    """

    return (yield from _Guard_Qt_Callbacks('call'))


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item: pytest.Item, nextitem: tp.Optional[pytest.Item]) -> tp.Generator[None, tp.Any, tp.Any]:
    """
    Description:
        The test's teardown, guarded by _Guard_Qt_Callbacks.

    Args:
        (1) item [pytest.Item(object)]: The test.
        (2) nextitem [pytest.Item(object)]: The next test, or None.

    Returns:
        (1) parameter [Generator]: The pluggy wrapper.
    """

    return (yield from _Guard_Qt_Callbacks('teardown'))


@pytest.fixture
def project_root() -> str:
    """
    Description:
        The repository root as an absolute path.

    Returns:
        (1) parameter [string]: Absolute path to the repository root.
    """

    return CONST_PROJECT_FOLDER


@pytest.fixture
def configuration_root(tmp_path: tp.Any, monkeypatch: pytest.MonkeyPatch) -> str:
    """
    Description:
        A Configuration/ of the test's own: tmp_path/Configuration with Mode/ (empty), Station/ and
        Calibration/ (copies of the shipped files), set as Configuration.Core.CONST_CONFIG_DIR. Every
        reference — a mode's Station, a station's Calibration — then resolves in it, and the
        Configuration dialog lists its Mode/, so a test writes mode, station and calibration files
        without touching the repository's.

    Returns:
        (1) parameter [string]: The Configuration/ directory (absolute).
    """

    import shutil
    import Configuration.Core as Configuration
    root = tmp_path / 'Configuration'
    for folder in (Configuration.CONST_MODE_FOLDER, Configuration.CONST_STATION_FOLDER,
                   Configuration.CONST_CALIBRATION_FOLDER):
        shipped = os.path.join(Configuration.CONST_CONFIG_DIR, folder)
        (root / folder).mkdir(parents=True)
        if folder != Configuration.CONST_MODE_FOLDER:
            for name in os.listdir(shipped):
                shutil.copy(os.path.join(shipped, name), root / folder)
    monkeypatch.setattr(Configuration, 'CONST_CONFIG_DIR', str(root))
    return str(root)


@pytest.fixture
def reference_shape() -> tp.Tuple[int, int, int]:
    """
    Description:
        The reference background's expected shape (h, w, c) — the size a --frame
        input must match.

    Returns:
        (1) parameter [Tuple<int> 1x3]: (height, width, channels).
    """

    return CONST_REFERENCE_SHAPE


@pytest.fixture
def reference_background_path() -> str:
    """
    Description:
        Absolute path to the committed reference background (Data/Images/Background).

    Returns:
        (1) parameter [string]: Absolute path to Image_Background_001.png.
    """

    return CONST_REFERENCE_BACKGROUND


@pytest.fixture
def reference_background() -> np.ndarray:
    """
    Description:
        The reference background loaded as a BGR array, the way the pipeline reads
        it. Skips the test if the file is missing rather than failing obscurely.

    Returns:
        (1) parameter [Matrix<uint8> HxWx3]: The reference image (BGR).
    """

    image = cv2.imread(CONST_REFERENCE_BACKGROUND)
    if image is None:
        pytest.skip(f'reference background not readable at {CONST_REFERENCE_BACKGROUND}')
    return image


@pytest.fixture
def make_synthetic_frame() -> tp.Callable[[np.ndarray, tp.List[tp.Tuple[int, int, int, int]]], np.ndarray]:
    """
    Description:
        Factory that paints filled black rectangles onto a copy of a background,
        producing a same-size frame whose only difference is a known foreground.
        This is how the tests and the harness synthesize object frames without a
        camera.

    Returns:
        (1) parameter [function]: (background, rects) -> synthesized frame (BGR),
                                  where each rect is (x1, y1, x2, y2).
    """

    def _Build(background: np.ndarray,
               rects: tp.List[tp.Tuple[int, int, int, int]]) -> np.ndarray:
        frame = background.copy()
        for x1, y1, x2, y2 in rects:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 0), thickness=-1)
        return frame

    return _Build


# How long wait_for_scan waits for a scan's worker before it fails the test: a scan waits at most about a
# second for a still scene (Camera.Core.CONST_STILL_TIMEOUT_S), so this is reached only by a hang.
#   Unit [s]
CONST_SCAN_WAIT_S = 10.0


@pytest.fixture(scope='session')
def wait_for_scan() -> tp.Callable[[tp.Any], None]:
    """
    Description:
        Wait, processing Qt events, until a window's scan has ended: a scan runs on a worker thread
        (UI.Workers.Scan_Worker_Cls), so a test that presses SCAN reads the result only after the worker
        has reported. A scan that never ends fails the test after CONST_SCAN_WAIT_S.

    Returns:
        (1) parameter [function]: (window) -> None.
    """

    def _Wait(window: tp.Any) -> None:
        # Imported here: most tests never build a window, and this module imports no Qt at load.
        from PyQt5.QtWidgets import QApplication
        deadline = time.monotonic() + CONST_SCAN_WAIT_S
        while getattr(window, '_AnyScan_Window_Cls__scanning') or getattr(window, '_AnyScan_Window_Cls__scan_thread'):
            if time.monotonic() > deadline:
                pytest.fail('The scan did not end within %g s.' % CONST_SCAN_WAIT_S)
            QApplication.processEvents()
            time.sleep(0.002)

    return _Wait


@pytest.fixture(scope='session')
def scan(wait_for_scan: tp.Callable[[tp.Any], None]) -> tp.Callable[[tp.Any], None]:
    """
    Description:
        Press SCAN through the window's slot and wait until the scan has ended (wait_for_scan).

    Returns:
        (1) parameter [function]: (window) -> None.
    """

    def _Scan(window: tp.Any) -> None:
        getattr(window, '_AnyScan_Window_Cls__On_Scan_Button_Clicked')()
        wait_for_scan(window)

    return _Scan


@pytest.fixture
def top_level_imports() -> tp.Callable[[str], tp.Set[str]]:
    """
    Description:
        The top-level packages a source file imports, from its parsed syntax tree — every
        'import x.y' and 'from x.y import z', at any depth (inside functions too). A text search
        for 'import cv2' misses 'from cv2 import imread'; this cannot.

    Returns:
        (1) parameter [function]: (path) -> the set of top-level package names.
    """

    import ast

    def _Imports(path: str) -> tp.Set[str]:
        with open(path, 'r', encoding='utf-8') as handle:
            tree = ast.parse(handle.read(), filename=path)
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                names.add(node.module.split('.')[0])
        return names

    return _Imports


@pytest.fixture
def require_weights(request: pytest.FixtureRequest) -> tp.Callable[[tp.List[str]], None]:
    """
    Description:
        The one rule for a test that needs model weights: it runs when they exist. When any is
        missing, the default run SKIPS — a fresh clone has no weights — with an impossible-to-miss
        banner naming each missing path; under --runslow, which asks for the real models, it FAILS,
        so a run that asked for them can never pass without them. Never a silent return.

        It also FAILS when a model runtime in sys.modules is a stand-in (fake_runtimes left behind by
        an earlier test): the test would then run the stand-ins with real weights on disk, and its
        structural assertions can pass on them.

    Returns:
        (1) parameter [function]: (paths) -> None; each path is a weights directory or file.
    """

    def _Require(paths: tp.List[str]) -> None:
        stand_ins = [name for name in CONST_RUNTIME_MODULES
                     if name in sys.modules and not getattr(sys.modules[name], '__file__', None)]
        if stand_ins:
            pytest.fail('STAND-IN RUNTIME LEFT IN sys.modules: %s — an earlier test did not restore the real '
                        'packages, so this test would not run the real models.' % ', '.join(stand_ins), pytrace=False)
        missing = [path for path in paths if not os.path.exists(path)]
        if not missing:
            return
        message = ('MODEL WEIGHTS ABSENT: the real vision path was NOT verified. Missing: '
                   + ', '.join(missing) + '. Download them (see README > Setup), then re-run `pytest`.')
        if request.config.getoption('--runslow'):
            pytest.fail(message, pytrace=False)
        reporter = request.config.pluginmanager.getplugin('terminalreporter')
        if reporter is not None:
            reporter.write_line('')
            reporter.write_sep('!', 'REAL VISION PATH NOT VERIFIED - model weights absent', red=True, bold=True)
            reporter.write_line('  ' + message, yellow=True)
            reporter.write_sep('!', red=True, bold=True)
        pytest.skip(message)

    return _Require


def _Models_Inventory() -> tp.Dict[str, int]:
    """
    Description:
        Every file under the repository's models/ (the user's multi-GB, git-ignored weights) as
        {relative path: size}, Finder's .DS_Store excepted.

    Returns:
        (1) parameter [Dict<string, int>]: The inventory; empty when models/ holds no weights.
    """

    root = os.path.join(CONST_PROJECT_FOLDER, 'models')
    inventory = {}
    for folder, _dirs, files in os.walk(root):
        for name in files:
            if name != '.DS_Store':
                path = os.path.join(folder, name)
                inventory[os.path.relpath(path, root)] = os.path.getsize(path)
    return inventory


@pytest.fixture(scope='session', autouse=True)
def models_untouched() -> tp.Iterator[None]:
    """
    Description:
        The suite must leave models/ exactly as it found it: the weights are git-ignored, so git cannot
        restore them. The inventory is taken before the first test and compared after the last; any
        file removed, added or resized fails the run, naming each one — so a change is attributed to
        this run the moment it happens, not discovered later. (models/ was emptied by hand on 2026-09-24
        and again on 2026-09-25 — manual both times, not code; this fixture is what showed, run by run,
        that the suite had not done it. See docs/design-decisions.md.)
    """

    before = _Models_Inventory()
    yield
    after = _Models_Inventory()
    changes = (['removed: %s' % name for name in sorted(set(before) - set(after))]
               + ['added: %s' % name for name in sorted(set(after) - set(before))]
               + ['resized: %s' % name for name in sorted(set(before) & set(after)) if before[name] != after[name]])
    assert not changes, 'The test run changed models/:\n  ' + '\n  '.join(changes)


class _Fake_Device_Cls(object):
    """
    Description:
        A stand-in accelerator queue (MPS, CUDA, Metal): work queued on it returns at once and
        completes only when something waits for it — a sync, or the next call that touches the
        device — as real GPU work does. Wait counts every wait, so a test can see a sync happened.
    """

    def __init__(self) -> None:
        self.waits = 0
        self.__done_at = 0.0

    def Queue(self, seconds: float) -> None:
        """
        Description:
            Queue work that completes `seconds` from now.

        Args:
            (1) seconds [float]: How long the queued work takes.
        """

        self.__done_at = time.perf_counter() + seconds

    def Wait(self) -> None:
        """
        Description:
            Block until the queued work has completed.
        """

        self.waits += 1
        remaining = self.__done_at - time.perf_counter()
        if remaining > 0:
            time.sleep(remaining)


class _Fake_Runtimes_Cls(object):
    """
    Description:
        Stand-ins for the model runtimes — torch and ultralytics (FastSAM), mlx and mlx_vlm (Gemma) —
        so the REAL Fast_Sam_Cls and Gemma_Describer_Cls run with no weights. Every delay is a knob
        (seconds): the synchronous part of a call sleeps, the device part is queued on a
        _Fake_Device_Cls and completes only when waited for.
    """

    def __init__(self, directory: str) -> None:
        # The delays. inference_s / generate_s: the synchronous part of a FastSAM / Gemma call;
        # segment_device_s / describe_device_s: the part queued on the device; post_s: extra time
        # moving FastSAM's masks off the device; *_load_s: loading each model.
        #   Unit [float] (s)
        self.inference_s = self.segment_device_s = self.post_s = 0.0
        self.generate_s = self.describe_device_s = 0.0
        self.segmenter_load_s = self.describer_load_s = 0.0
        # The device FastSAM's weights report being on ('cpu', 'mps', 'cuda'); each torch sync call
        # by device; and whether a torch sync raises (as it does on a machine without that device).
        #   Unit [string], [Vector<string>], [bool]
        self.model_device = 'mps'
        self.torch_syncs = []
        self.sync_raises = False
        # Whether a FastSAM call fails (as a lost device would).
        #   Unit [bool]
        self.segment_raises = False
        # The accelerator queues: torch's (MPS/CUDA) and MLX's (Metal).
        #   Unit [_Fake_Device_Cls(object)]
        self.gpu, self.metal = _Fake_Device_Cls(), _Fake_Device_Cls()
        # The weights the configuration must name: a FastSAM file and a Gemma directory.
        #   Unit [string]
        os.makedirs(directory, exist_ok=True)
        self.segmenter_path = os.path.join(directory, 'FastSAM-x.pt')
        self.describer_path = os.path.join(directory, 'gemma-4-e4b-it-4bit')
        with open(self.segmenter_path, 'wb') as handle:
            handle.write(b'stand-in weights')
        os.makedirs(self.describer_path, exist_ok=True)

    def Modules(self) -> tp.Dict[str, types.ModuleType]:
        """
        Description:
            The stand-in modules, by the names the code imports.

        Returns:
            (1) parameter [Dict<string, module>]: {'torch': …, 'ultralytics': …, 'mlx': …, 'mlx.core': …,
                                                   'mlx_vlm': …, 'mlx_vlm.prompt_utils': …}.
        """

        runtime = self

        def _Sync(device: str) -> tp.Callable[[], None]:
            def _Synchronize() -> None:
                runtime.torch_syncs.append(device)
                if runtime.sync_raises:
                    raise RuntimeError('%s is not available on this machine' % device)
                runtime.gpu.Wait()
            return _Synchronize

        torch = types.ModuleType('torch')
        torch.mps = types.SimpleNamespace(synchronize=_Sync('mps'))
        torch.cuda = types.SimpleNamespace(synchronize=_Sync('cuda'), is_available=lambda: False)
        torch.backends = types.SimpleNamespace(mps=types.SimpleNamespace(is_available=lambda: False))

        def _Tensor(array: np.ndarray, delay: float) -> types.SimpleNamespace:
            """A device tensor under torch's names: .cpu() waits for the device, then takes `delay` more."""
            tensor = types.SimpleNamespace(numpy=lambda: array)

            def _Cpu() -> types.SimpleNamespace:
                runtime.gpu.Wait()
                time.sleep(delay)
                return tensor

            tensor.cpu = _Cpu
            return tensor

        class _Fast_Sam_Model_Cls(object):
            """FastSAM: one empty mask per frame; the device part of the call is queued, not waited for."""

            def __init__(self, path: str) -> None:
                time.sleep(runtime.segmenter_load_s)
                parameter = types.SimpleNamespace(device=types.SimpleNamespace(type=runtime.model_device))
                self.model = types.SimpleNamespace(parameters=lambda: iter([parameter]))

            def __call__(self, image: np.ndarray, **kwargs: tp.Any) -> tp.List[tp.Any]:
                if runtime.segment_raises:
                    raise RuntimeError('MPS device lost')
                runtime.gpu.Wait()
                time.sleep(runtime.inference_s)
                runtime.gpu.Queue(runtime.segment_device_s)
                mask = np.zeros((1,) + image.shape[:2], np.uint8)
                return [types.SimpleNamespace(masks=types.SimpleNamespace(data=_Tensor(mask, runtime.post_s)),
                                              boxes=types.SimpleNamespace(conf=_Tensor(np.array([0.9]), 0.0)))]

        ultralytics = types.ModuleType('ultralytics')
        ultralytics.FastSAM = _Fast_Sam_Model_Cls

        def _Load(path: str) -> tp.Tuple[tp.Any, str]:
            time.sleep(runtime.describer_load_s)
            return types.SimpleNamespace(config='model-config'), 'processor'

        def _Generate(model: tp.Any, processor: tp.Any, formatted: str, **kwargs: tp.Any) -> tp.Any:
            runtime.metal.Wait()
            time.sleep(runtime.generate_s)
            runtime.metal.Queue(runtime.describe_device_s)
            return types.SimpleNamespace(text='A steel plate.', prompt_tokens=408, generation_tokens=65)

        mlx_vlm = types.ModuleType('mlx_vlm')
        mlx_vlm.load, mlx_vlm.generate = _Load, _Generate
        prompt_utils = types.ModuleType('mlx_vlm.prompt_utils')
        prompt_utils.apply_chat_template = lambda processor, config, prompt, **kwargs: 'formatted:' + prompt
        core = types.ModuleType('mlx.core')
        core.synchronize = self.metal.Wait
        mlx = types.ModuleType('mlx')
        mlx.core = core
        return {'torch': torch, 'ultralytics': ultralytics, 'mlx': mlx, 'mlx.core': core,
                'mlx_vlm': mlx_vlm, 'mlx_vlm.prompt_utils': prompt_utils}


@pytest.fixture
def fake_runtimes(monkeypatch: pytest.MonkeyPatch, tmp_path: tp.Any) -> _Fake_Runtimes_Cls:
    """
    Description:
        Install stand-in torch / ultralytics / mlx / mlx_vlm for this test, so the real FastSAM and
        Gemma classes load and run with no weights and controllable delays (_Fake_Runtimes_Cls). The
        real modules are put back afterwards.

    Returns:
        (1) parameter [_Fake_Runtimes_Cls(object)]: The runtimes and their delay knobs.
    """

    runtime = _Fake_Runtimes_Cls(str(tmp_path / 'weights'))
    for name, module in runtime.Modules().items():
        monkeypatch.setitem(sys.modules, name, module)
    return runtime
