## =========================================================================== ##
# MIT License
# Copyright (c) 2026 JIC Smart Factory
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
# File Name: ../Example/UI/analysis_animation.py
## =========================================================================== ##

# System (Default)
import argparse
import os
import sys
import tempfile
import time
from datetime import datetime
# Typing (Support for type hints)
import typing as tp

"""
Description:
    Write the README's animation, images/anyscan-analysis.webp: the application replaying one recorded frame,
    SCAN then ANALYZE, in a catalogue mode. It runs the real window offscreen with a saved frame for a camera (as
    App/run.py --frame does) and the real models, loads the mode through the Configuration dialog as an operator
    does, clicks CONNECT, SCAN and ANALYZE, and grabs the window on events, never on a timer: the connected window,
    SCAN pressed, the frame taken, every change of the Camera View's badge while it analyses ('Analysing object 3
    of 7…'), and the result. Each kind of frame is shown for a fixed time, so the analysis, however long it takes on
    this machine, plays in CONST_ANALYSIS_MS, and the clip in at most 10 s. The script prints how long it took.

    The window's clock is frozen at CONST_CLOCK, so the clip shows no time of the run. What still differs between
    runs is the measured inference time in the panel, and on another machine the descriptions' wording (Gemma on
    another backend), so the file is regenerated, never edited, and is not compared byte for byte
    (readme-writer references/project.md > Figures).

        .venv/bin/python Example/UI/analysis_animation.py --frame <set>_raw.png    # example: a recorded frame

    The session log and the capture set the analysis writes go to a temporary directory that is removed after.
"""
# The project folder, from this file's own location (Example/UI -> ..).
#   Unit [string]
CONST_PROJECT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
CONST_OUTPUT_FILE = os.path.join(CONST_PROJECT_FOLDER, 'images', 'anyscan-analysis.webp')
# The mode the clip shows: the mounting-plate catalogue mode, as shipped.
#   Unit [string]
CONST_MODE_FILE = os.path.join(CONST_PROJECT_FOLDER, 'Configuration', 'Mode',
                               'Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_Mounting_Plate.yaml')
# The window's size, 16:9 like the station's screen, and the clip's width.
#   Unit [Vector<int> 1x2] / [px]
CONST_WINDOW_SIZE = (1600, 900)
CONST_WIDTH = 960
# How long each kind of frame is shown: the connected window, SCAN pressed, the frame taken, the whole analysis
# (shared by its frames), and the result. 9.6 s in all.
#   Unit [ms]
CONST_IDLE_MS = 1000
CONST_SCANNING_MS = 400
CONST_SCANNED_MS = 1200
CONST_ANALYSIS_MS = 3000
CONST_RESULT_MS = 4000
# The longest each step may take before the script gives up.
#   Unit [s]
CONST_LOAD_TIMEOUT_S = 300.0
CONST_STEP_TIMEOUT_S = 600.0
# A settling pass, and the longest the window may take to draw the result the same twice.
#   Unit [s]
CONST_SETTLE_PASS_S = 0.1
CONST_SETTLE_TIMEOUT_S = 5.0
# The window's frozen clock: the time the station recorded for set 20261029-144501_15, the frame the README's
# clip replays.
#   Unit [datetime]
CONST_CLOCK = datetime(2026, 10, 29, 14, 45, 1)
# WebP's lossy quality and encoder effort.
#   Unit [-]
CONST_QUALITY = 70
CONST_METHOD = 6
# The window's private members the script drives, as Python mangles them.
#   Unit [string]
CONST_MANGLE = '_AnyScan_Window_Cls__'


def _Frozen_Now(cls: type, tz: tp.Any = None) -> datetime:
    """
    Description:
        The frozen clock's now(): always CONST_CLOCK.

    Args:
        (1) cls [type]: The frozen datetime class.
        (2) tz [tzinfo or None]: Ignored; the clock has no zone.

    Returns:
        (1) parameter [datetime(object)]: CONST_CLOCK, as cls.
    """

    return cls(CONST_CLOCK.year, CONST_CLOCK.month, CONST_CLOCK.day, CONST_CLOCK.hour, CONST_CLOCK.minute,
               CONST_CLOCK.second)


def Freeze_Window_Clock(ui_core: tp.Any) -> None:
    """
    Description:
        Freeze the clock the window reads (UI.Core's datetime) at CONST_CLOCK.

    Args:
        (1) ui_core [module]: The imported UI.Core module.
    """

    ui_core.datetime = type('Frozen_Datetime', (datetime,), {'now': classmethod(_Frozen_Now)})


def Grab(window: tp.Any, width: int) -> tp.Any:
    """
    Description:
        The window as it is drawn now, scaled to the clip's width.

    Args:
        (1) window [QWidget(object)]: The window.
        (2) width [int]: The clip's width [px].

    Returns:
        (1) parameter [PIL.Image(object)]: The frame (RGB).
    """

    # Pillow (Image handling) [pip3 install Pillow]
    from PIL import Image
    image = window.grab().toImage().convertToFormat(4)        # QImage.Format_RGB32
    pointer = image.constBits()
    pointer.setsize(image.byteCount())
    frame = Image.frombuffer('RGBA', (image.width(), image.height()), bytes(pointer), 'raw', 'BGRA',
                             image.bytesPerLine(), 1).convert('RGB')
    return frame.resize((width, round(width * frame.height / frame.width)), Image.LANCZOS)


def Wait(app: tp.Any, done: tp.Callable[[], bool], timeout: float, what: str,
         on_event: tp.Optional[tp.Callable[[], None]] = None) -> float:
    """
    Description:
        Run the event loop until done() holds, calling on_event after each pass.

    Args:
        (1) app [QApplication(object)]: The application.
        (2) done [function]: () -> bool, the condition waited for.
        (3) timeout [float]: The longest wait [s].
        (4) what [string]: What is waited for, for the error.
        (5) on_event [function or None]: () -> None, called after each pass of the event loop.

    Returns:
        (1) parameter [float]: How long it took [s].
    """

    start = time.time()
    while not done():
        app.processEvents()
        if on_event is not None:
            on_event()
        if time.time() - start > timeout:
            raise RuntimeError('%s did not finish within %.0f s.' % (what, timeout))
        time.sleep(0.01)
    app.processEvents()
    return time.time() - start


def Settled_Grab(app: tp.Any, window: tp.Any, width: int) -> tp.Any:
    """
    Description:
        Run the event loop until the window draws the same twice in a row, then return that frame: a panel that has
        just received the result lays its text out over a few passes, and a frame grabbed before that shows it
        overlapping.

    Args:
        (1) app [QApplication(object)]: The application.
        (2) window [QWidget(object)]: The window.
        (3) width [int]: The clip's width [px].

    Returns:
        (1) parameter [PIL.Image(object)]: The settled frame (RGB).
    """

    previous = Grab(window, width)
    deadline = time.time() + CONST_SETTLE_TIMEOUT_S
    while time.time() < deadline:
        app.processEvents()
        time.sleep(CONST_SETTLE_PASS_S)
        app.processEvents()
        current = Grab(window, width)
        if current.tobytes() == previous.tobytes():
            return current
        previous = current
    return previous


def Record_Analysis(app: tp.Any, window: tp.Any, mode_file: str, width: int) -> tp.Dict[str, tp.Any]:
    """
    Description:
        Load the mode through the window's Configuration dialog, then CONNECT, SCAN and ANALYZE, grabbing the window
        on each event. The loading is not recorded.

    Args:
        (1) app [QApplication(object)]: The application.
        (2) window [AnyScan_Window_Cls(object)]: The shown window, its camera a saved frame.
        (3) mode_file [string]: The mode file, listed in the dialog.
        (4) width [int]: The clip's width [px].

    Returns:
        (1) parameter [Dict]: 'frames', a list of (kind, image) with kind 'idle', 'scanning', 'scanned',
                              'analysing' or 'result'; 'load_s', 'analysis_s' [s].
    """

    def Member(name: str) -> tp.Any:
        """
        Description:
            One of the window's private members, by its unmangled name.

        Args:
            (1) name [string]: The name after its two leading underscores.

        Returns:
            (1) parameter [object]: The member.
        """

        return getattr(window, CONST_MANGLE + name)

    dialog = Member('Make_Configuration_Dialog')()
    dialog.Select(mode_file)
    dialog.Load()
    load_s = Wait(app, lambda: not dialog.Loading, CONST_LOAD_TIMEOUT_S, 'Loading the configuration')
    dialog.close()
    if not Member('button_connect').isEnabled():
        raise RuntimeError('The configuration did not load: CONNECT stays unavailable.')

    Member('button_connect').click()
    Wait(app, lambda: not Member('worker_running') and Member('button_scan').isEnabled(), CONST_STEP_TIMEOUT_S,
         'CONNECT')
    frames = [('idle', Grab(window, width))]

    Member('button_scan').click()
    app.processEvents()
    frames.append(('scanning', Grab(window, width)))
    Wait(app, lambda: not Member('worker_running'), CONST_STEP_TIMEOUT_S, 'SCAN')
    frames.append(('scanned', Grab(window, width)))

    badge = Member('frame_badge')
    shown = {'text': None}

    def On_Event() -> None:
        """
        Description:
            Grab the window when the Camera View's badge has changed since the last pass.
        """

        if badge.text() != shown['text']:
            shown['text'] = badge.text()
            frames.append(('analysing', Grab(window, width)))

    Member('button_analyze').click()
    analysis_s = Wait(app, lambda: not Member('worker_running'), CONST_STEP_TIMEOUT_S, 'ANALYZE', On_Event)
    frames.append(('result', Settled_Grab(app, window, width)))
    return {'frames': frames, 'load_s': load_s, 'analysis_s': analysis_s}


def Frame_Durations(kinds: tp.List[str]) -> tp.List[int]:
    """
    Description:
        How long each frame is shown: CONST_*_MS for its kind, the analysing frames sharing CONST_ANALYSIS_MS.

    Args:
        (1) kinds [Vector<string>]: Each frame's kind, in order.

    Returns:
        (1) parameter [Vector<int>]: Each frame's duration [ms].
    """

    analysing = max(1, kinds.count('analysing'))
    fixed = {'idle': CONST_IDLE_MS, 'scanning': CONST_SCANNING_MS, 'scanned': CONST_SCANNED_MS,
             'result': CONST_RESULT_MS, 'analysing': CONST_ANALYSIS_MS // analysing}
    return [fixed[kind] for kind in kinds]


def Write_Webp(frames: tp.List[tp.Tuple[str, tp.Any]], output: str) -> int:
    """
    Description:
        Write the frames as a looping animated WebP.

    Args:
        (1) frames [Vector<(string, PIL.Image)>]: Each frame's kind and image, in order.
        (2) output [string]: The file written.

    Returns:
        (1) parameter [int]: The clip's length [ms].
    """

    durations = Frame_Durations([kind for kind, _image in frames])
    images = [image for _kind, image in frames]
    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    images[0].save(output, format='WEBP', save_all=True, append_images=images[1:], duration=durations, loop=0,
                   quality=CONST_QUALITY, method=CONST_METHOD)
    return sum(durations)


def main() -> int:
    """
    Description:
        Replay the frame given through the shipped catalogue mode and write the clip.

    Returns:
        (1) parameter [int]: The exit code.
    """

    parser = argparse.ArgumentParser(description='Write the README\'s analysis animation from one recorded frame.')
    parser.add_argument('--frame', required=True, help='a recorded 1920 x 1200 frame, a capture set\'s _raw.png')
    parser.add_argument('--output', default=CONST_OUTPUT_FILE, help='the WebP written (default: %(default)s)')
    args = parser.parse_args()
    if not os.path.isfile(args.frame):
        print('[ERROR] The frame %s does not exist.' % args.frame)
        return 1

    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    sys.path.insert(0, os.path.join(CONST_PROJECT_FOLDER, 'src'))
    # PyQt5 (Qt bindings) [pip3 install PyQt5]
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication
    # Custom Lib.: AnyScan — the camera, the configuration, the window and the logger
    #   ../Camera/Core
    from Camera.Core import File_Camera_Cls
    #   ../Configuration/Core
    from Configuration.Core import Load_Configuration
    #   ../UI/Utilities/Style
    import UI.Utilities.Style as Style
    #   ../UI/Core
    import UI.Core as UI_Core
    #   ../Logger/Core
    from Logger.Core import Session_Logger_Cls

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    Style.Load_Fonts()
    Freeze_Window_Clock(UI_Core)
    with tempfile.TemporaryDirectory() as log_dir:
        logger = Session_Logger_Cls(config_path=CONST_MODE_FILE, log_dir=log_dir, install_handlers=False)
        window = UI_Core.AnyScan_Window_Cls(camera=File_Camera_Cls(os.path.abspath(args.frame)), logger=logger,
                                            Configuration_Str=Load_Configuration(CONST_MODE_FILE))
        window.resize(*CONST_WINDOW_SIZE)
        window.show()
        try:
            recording = Record_Analysis(app, window, CONST_MODE_FILE, CONST_WIDTH)
        except RuntimeError as error:
            print('[ERROR] %s' % error)
            return 1
        finally:
            window.close()
            logger.Close()
    length = Write_Webp(recording['frames'], args.output)
    print('[INFO] Configuration loaded in %.1f s, not recorded.' % recording['load_s'])
    print('[INFO] The analysis took %.1f s and is shown in %.1f s.'
          % (recording['analysis_s'], CONST_ANALYSIS_MS / 1000))
    print('[INFO] Wrote %s: %d frames, %.1f s, %d KB.' % (args.output, len(recording['frames']), length / 1000,
                                                         os.path.getsize(args.output) // 1024))
    return 0


if __name__ == '__main__':
    sys.exit(main())
