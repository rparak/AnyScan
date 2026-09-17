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
# File Name: ../test/UI/test_camera_view.py
## =========================================================================== ##

# System (Default)
import os
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtWidgets import QApplication
# Custom Lib.: AnyScan UI — the window; domain — the camera, the vision base, the result
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
#   ../Vision/Core
from Vision.Core import Vision_Backend_Cls
#   ../Parameters/Vision
from Parameters.Vision import Analysis_Str

"""
Description:
    Headless (offscreen) tests for the Camera View annotated/mask toggle (§2b), driven
    through the window's completion slot directly (no QThread — the threading guarantees
    live in test_threading.py). They assert: the toggle is hidden before an analysis and
    shown/enabled after; switching swaps the view WITHOUT invoking the pipeline; the
    chosen view persists across a second analysis; and a stale frame (a new scan or a
    disconnect) drops the renders and hides the toggle. No camera and no weights needed.
"""

# The window's name-mangling prefix, for reaching its private state.
CONST_MANGLE = '_AnyScan_Window_Cls'


class _Counting_Vision_Cls(Vision_Backend_Cls):
    """A vision backend that counts Analyze calls and returns an empty reading."""

    Name = 'Counting'

    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def Analyze(self, image, progress_cb=None, stage_cb=None) -> Analysis_Str:
        self.calls += 1
        return Analysis_Str(Objects=[], Verdict='Empty',
                            Verdict_Level='idle', Task='count')


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


def _Private(window, name: str):
    """Fetch a name-mangled private attribute or method of the window."""
    return getattr(window, CONST_MANGLE + name)


def _Scanned_Window(reference_background_path):
    """A window with the camera connected, a frame scanned, and a counting backend."""
    window = AnyScan_Window_Cls(camera=File_Camera_Cls(reference_background_path))
    setattr(window, CONST_MANGLE + '__vision', _Counting_Vision_Cls())
    _Private(window, '__camera').Connect()
    _Private(window, '__Sync_Controls')()
    _Private(window, '__On_Scan_Button_Clicked')()
    return window


def _Result() -> Analysis_Str:
    """An empty finished reading (both renders are valid for zero objects)."""
    return Analysis_Str(Objects=[], Verdict='Empty',
                        Verdict_Level='idle', Task='t')


def test_toggle_hidden_before_analysis_and_shown_after(qt_app, reference_background_path) -> None:
    """
    Description:
        The toggle is nothing to act on before an analysis, so it is hidden; once an
        analysis has delivered both renders it is visible and enabled.
    """

    window = _Scanned_Window(reference_background_path)
    toggle = _Private(window, '__view_toggle')
    viewport = _Private(window, '__viewport')

    assert toggle.isHidden()
    assert not viewport.Has_Views()

    _Private(window, '__On_Analysis_Finished')(_Result())

    assert viewport.Has_Views()
    assert not toggle.isHidden() and toggle.isEnabled()


def test_switching_view_does_not_invoke_the_pipeline(qt_app, reference_background_path) -> None:
    """
    Description:
        Switching between annotated and mask swaps the held render in place — it must
        never re-run analysis. The backend's Analyze is never called by a view switch.
    """

    window = _Scanned_Window(reference_background_path)
    vision = _Private(window, '__vision')
    viewport = _Private(window, '__viewport')
    _Private(window, '__On_Analysis_Finished')(_Result())

    assert vision.calls == 0                       # the completion slot was called directly
    assert viewport.Current_View() == 'annotated'

    _Private(window, '__On_View_Toggle')('mask')
    assert viewport.Current_View() == 'mask'
    _Private(window, '__On_View_Toggle')('annotated')
    assert viewport.Current_View() == 'annotated'

    assert vision.calls == 0                       # no switch touched the pipeline


def test_selected_view_persists_across_a_second_analysis(qt_app, reference_background_path) -> None:
    """
    Description:
        An operator working in mask view is not thrown back to annotated by the next
        Analyze: the remembered choice is reapplied when the second analysis completes.
    """

    window = _Scanned_Window(reference_background_path)
    viewport = _Private(window, '__viewport')
    _Private(window, '__On_Analysis_Finished')(_Result())
    _Private(window, '__On_View_Toggle')('mask')

    # A second analysis of the same session.
    _Private(window, '__On_Analysis_Finished')(_Result())
    assert viewport.Current_View() == 'mask'


def test_a_new_scan_makes_the_result_stale_and_hides_the_toggle(qt_app, reference_background_path) -> None:
    """
    Description:
        The staleness rule: a new frame's annotations would not line up with the old
        scene, so a new scan drops the renders and hides the toggle rather than showing
        a previous frame's overlay over a new one.
    """

    window = _Scanned_Window(reference_background_path)
    toggle = _Private(window, '__view_toggle')
    viewport = _Private(window, '__viewport')
    _Private(window, '__On_Analysis_Finished')(_Result())
    assert not toggle.isHidden()

    _Private(window, '__On_Scan_Button_Clicked')()   # a new frame arrives
    assert not viewport.Has_Views()
    assert toggle.isHidden()


def test_disconnect_drops_the_result_and_hides_the_toggle(qt_app, reference_background_path) -> None:
    """
    Description:
        A camera disconnect clears the frame, so any held analysis is stale: the renders
        are dropped and the toggle hidden.
    """

    window = _Scanned_Window(reference_background_path)
    toggle = _Private(window, '__view_toggle')
    viewport = _Private(window, '__viewport')
    _Private(window, '__On_Analysis_Finished')(_Result())
    assert not toggle.isHidden()

    _Private(window, '__On_Disconnect_Button_Clicked')()
    assert not viewport.Has_Views()
    assert toggle.isHidden()
