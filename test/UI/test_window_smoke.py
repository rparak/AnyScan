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
# File Name: ../test/UI/test_window_smoke.py
## =========================================================================== ##

# System (Default)
import os
# Qt must render headless in the test environment; set the platform before any
# QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtWidgets import QApplication
# Custom Lib.: AnyScan UI
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
# Dataclasses (the shipped configuration, unscaled, for the window)
import dataclasses
# Custom Lib.: AnyScan — the configuration layer the window is built from
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    A headless (offscreen) smoke test for the whole UI. It builds the main window
    — which constructs every widget and wires every signal — and drives the
    synchronous scan path (capture -> ndarray -> QImage -> viewport), the one
    boundary the domain unit tests cannot reach. No display, no camera hardware and
    no model weights are needed.

    The private state is reached through name-mangling on purpose: the window
    exposes no test hooks, and a smoke test should not force it to.
"""
# The window's configuration: the shipped one, loaded through the configuration layer, without a
# scale (nothing measured) — what these tests built the window with before configurations existed.
#   Unit [Configuration_Str(object)]
CONST_CONFIGURATION = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)

# The window's name-mangling prefix, for reaching private state in the smoke test.
CONST_MANGLE = '_AnyScan_Window_Cls'


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """
    Description:
        A single offscreen QApplication for the module.

    Returns:
        (1) parameter [QApplication(object)]: The application instance.
    """

    app = QApplication.instance() or QApplication([])
    Style.Load_Fonts()
    return app


def _Private(window: AnyScan_Window_Cls, name: str):
    """
    Description:
        Fetch a name-mangled private attribute or method of the window.

    Args:
        (1) window [AnyScan_Window_Cls(Configuration_Str=CONST_CONFIGURATION, object)]: The window.
        (2) name [string]: The bare private name (e.g. '__viewport').

    Returns:
        (1) parameter [object]: The attribute or bound method.
    """

    return getattr(window, CONST_MANGLE + name)


def test_window_builds(qt_app, reference_background_path) -> None:
    """
    Description:
        The whole window constructs — every widget and every signal connection —
        against a File_Camera_Cls, with the model backend present but unloaded.
    """

    window = AnyScan_Window_Cls(Configuration_Str=CONST_CONFIGURATION, camera=File_Camera_Cls(reference_background_path))
    window.resize(1280, 800)

    assert window.windowTitle().startswith('AnyScan')
    assert _Private(window, '__viewport') is not None
    # The model pill reads the backend's presented name.
    assert _Private(window, '__vision').Name


class _Loaded_Vision_Cls(object):
    """A stand-in backend whose configuration is loaded; it is never asked to analyse."""
    Name, Models_Loaded, Model_Names = 'JIC_AnyScan_All_v1', True, ('FastSAM-x.pt', 'gemma')


def test_scan_path_displays_frame(qt_app, reference_background_path, reference_shape) -> None:
    """
    Description:
        Connect the camera and run the synchronous scan slot: the frame is captured
        as an ndarray, converted to a QImage for the viewport, and the badge shows
        the frame size. ANALYZE needs the frame AND a loaded configuration — with a frame but no
        loaded configuration it stays disabled. Then clear and disconnect return to the empty state.
    """

    window = AnyScan_Window_Cls(Configuration_Str=CONST_CONFIGURATION, camera=File_Camera_Cls(reference_background_path))

    _Private(window, '__camera').Connect()
    _Private(window, '__Sync_Controls')()
    _Private(window, '__On_Scan_Button_Clicked')()

    height, width, _ = reference_shape
    assert _Private(window, '__frame_badge').text() == '%d × %d · RGB' % (width, height)
    assert not _Private(window, '__button_analyze').isEnabled()          # no configuration loaded
    setattr(window, CONST_MANGLE + '__vision', _Loaded_Vision_Cls())
    _Private(window, '__Sync_Controls')()
    assert _Private(window, '__button_analyze').isEnabled()

    _Private(window, '__On_Clear_Button_Clicked')()
    assert _Private(window, '__frame_badge').text() == 'No frame'

    _Private(window, '__On_Disconnect_Button_Clicked')()
    assert not _Private(window, '__camera').Connected
