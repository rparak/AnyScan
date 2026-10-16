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
# Author   : JIC Smart Factory
# File Name: ../test/Camera/test_preview.py
## =========================================================================== ##

# Time (Time access and conversions)
import time
# Typing (Support for type hints)
import typing as tp
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Custom Lib.: AnyScan domain — the camera layer
#   ../Camera/Core
import Camera.Core as Camera_Core
from Camera.Core import Camera_Backend_Cls, Camera_Error_Cls, Camera_Motion_Error_Cls

"""
Description:
    Tests for the camera layer's live preview (Start_Preview, Preview_Frame, Stop_Preview) and its scan
    (Capture_Still), on a scripted stream backend that records every start, grab, stop and close — no hardware.
    The frames are small synthetic RGB arrays: a still pair is two identical frames, a moving pair two frames
    that differ over half the image, far beyond the stillness thresholds either way (Camera.Utilities.Stillness
    is tested on real frames in test_stillness.py).
"""
# The size of a scripted frame (height, width).
#   Unit [Tuple<int> 1x2]
CONST_SHAPE = (40, 60)


def _Frame(value: int) -> np.ndarray:
    """A scripted frame: the left half at the given grey, the right half mid-grey."""
    frame = np.full(CONST_SHAPE + (3,), 128, np.uint8)
    frame[:, :CONST_SHAPE[1] // 2] = value
    return frame


class _Stream_Camera_Cls(Camera_Backend_Cls):
    """
    A backend with a stream: each stream (from _Start_Stream) hands out the frames its script makes, in order;
    events records ('start', n), ('grab', n), ('stop', n), ('close',) in the order they happen.
    """

    def __init__(self, script: tp.Callable[[int, int], tp.Optional[np.ndarray]], delay: float = 0.0) -> None:
        super().__init__()
        self.script, self.delay = script, delay
        self.events, self.stream, self.index, self.streaming = [], 0, 0, False
        self.removed, self.failing = False, False
        # Which stream delivered each frame, by the frame's id.
        self.origin = {}

    def _Open(self) -> None:
        pass

    def _Close(self) -> None:
        self.events.append(('close',))

    def _Device_Removed(self) -> bool:
        return self.removed

    def _Start_Stream(self) -> None:
        self.stream += 1
        self.index = 0
        self.streaming = True
        self.events.append(('start', self.stream))

    def _Stop_Stream(self) -> None:
        self.streaming = False
        self.events.append(('stop', self.stream))

    def _Grab_Stream(self) -> tp.Optional[np.ndarray]:
        assert self.streaming, 'a frame was taken from a stream that was not running'
        time.sleep(self.delay)
        if self.failing:
            raise Camera_Error_Cls('The camera did not return a frame in time.')
        frame = self.script(self.stream, self.index)
        self.index += 1
        self.events.append(('grab', self.stream))
        if frame is not None:
            self._last_distorted = frame
            self.origin[id(frame)] = self.stream
        return frame

    def _Grab(self) -> np.ndarray:
        return _Frame(0)

    @property
    def Resolution(self) -> tp.Tuple[int, int]:
        return (CONST_SHAPE[1], CONST_SHAPE[0])


def _Still(stream: int, index: int) -> np.ndarray:
    """A still scene: every frame the same."""
    return _Frame(40)


def _Moving(stream: int, index: int) -> np.ndarray:
    """A scene that never stops moving: consecutive frames differ over half the image."""
    return _Frame(40 if index % 2 else 220)


def test_a_scan_takes_the_first_frame_that_shows_no_movement_since_the_one_before() -> None:
    """
    Description:
        The scan compares each frame with the one before it and takes the first that shows no movement: with a
        hand leaving the view (the first frame differs, the next two are the same), it returns the third frame
        itself — one frame as the camera delivered it, not an average — and stops its stream.
    """

    frames = [_Frame(220), _Frame(40), _Frame(40), _Frame(40)]
    cam = _Stream_Camera_Cls(lambda stream, index: frames[index])
    cam.Connect()
    frame = cam.Capture_Still()
    assert frame is frames[2]
    assert cam.events == [('start', 1), ('grab', 1), ('grab', 1), ('grab', 1), ('stop', 1)]
    assert cam.Last_Distorted_Frame is frames[2]


def test_a_scene_that_keeps_moving_is_refused_after_the_timeout(monkeypatch) -> None:
    """
    Description:
        A scene that is still moving CONST_STILL_TIMEOUT_S after the scan started is refused with
        Camera_Motion_Error_Cls, whose sentence says something is moving: no frame is taken (no distorted original
        is left behind), the stream is stopped, and the camera stays connected — it is fine.
    """

    monkeypatch.setattr(Camera_Core, 'CONST_STILL_TIMEOUT_S', 0.2)
    cam = _Stream_Camera_Cls(_Moving, delay=0.03)
    cam.Connect()
    start = time.monotonic()
    with pytest.raises(Camera_Motion_Error_Cls, match='Something is moving in the view'):
        cam.Capture_Still()
    assert 0.2 <= time.monotonic() - start < 0.5
    assert cam.events[-1] == ('stop', 1) and not cam.streaming
    assert cam.Connected and cam.Last_Distorted_Frame is None


def test_a_scan_never_takes_a_frame_the_preview_buffered() -> None:
    """
    Description:
        While the preview's stream runs, a scan is refused (Capture_Still and Capture alike), so it can never take a
        frame exposed before SCAN was pressed. Once the preview is stopped, the scan starts a stream of its own and
        every frame it compares or returns comes from that stream.
    """

    cam = _Stream_Camera_Cls(_Still)
    cam.Connect()
    cam.Start_Preview()
    preview_frame = cam.Preview_Frame()
    for capture in (cam.Capture_Still, cam.Capture):
        with pytest.raises(Camera_Error_Cls, match='live preview is still running'):
            capture()
    cam.Stop_Preview()
    frame = cam.Capture_Still()
    assert cam.origin[id(preview_frame)] == 1 and cam.origin[id(frame)] == 2
    assert cam.events == [('start', 1), ('grab', 1), ('stop', 1), ('start', 2), ('grab', 2), ('grab', 2), ('stop', 2)]


def test_a_preview_frame_leaves_the_last_captures_record() -> None:
    """
    Description:
        A preview frame is never a capture: the last scan's distorted original stays as it was through any number
        of preview frames.
    """

    cam = _Stream_Camera_Cls(lambda stream, index: _Frame(40 + stream))
    cam.Connect()
    scanned = cam.Capture_Still()
    cam.Start_Preview()
    assert cam.Preview_Frame() is not scanned and cam.Preview_Frame() is not scanned
    assert cam.Last_Distorted_Frame is scanned


def test_disconnect_during_the_preview_stops_the_stream_before_closing() -> None:
    """
    Description:
        DISCONNECT while the preview's stream runs stops the stream first, then closes the device; afterwards the
        backend is neither connected nor previewing, so nothing can be left grabbing.
    """

    cam = _Stream_Camera_Cls(_Still)
    cam.Connect()
    cam.Start_Preview()
    cam.Disconnect()
    assert cam.events == [('start', 1), ('stop', 1), ('close',)]
    assert not cam.Connected and not cam.Previewing


def test_device_lost_asks_without_closing() -> None:
    """
    Description:
        Device_Lost says whether the device is gone while connected without closing anything — what the window asks
        while a worker uses the camera — where Check_Connection would close it.
    """

    cam = _Stream_Camera_Cls(_Still)
    assert not cam.Device_Lost()                                        # not connected
    cam.Connect()
    cam.Start_Preview()
    assert not cam.Device_Lost()
    cam.removed = True
    assert cam.Device_Lost() and cam.Connected and cam.Previewing and ('close',) not in cam.events


def test_a_scan_on_a_removed_device_disconnects_and_a_transient_failure_does_not() -> None:
    """
    Description:
        As with Capture, a scan whose grab fails on a device reported removed disconnects before the error goes on
        (a lost connection), while the same failure on a device still there leaves it connected; the stream is
        stopped either way.
    """

    cam = _Stream_Camera_Cls(_Still)
    cam.Connect()
    cam.failing = True
    with pytest.raises(Camera_Error_Cls, match='did not return a frame'):
        cam.Capture_Still()
    assert cam.Connected and cam.events[-1] == ('stop', 1)
    cam.removed = True
    with pytest.raises(Camera_Error_Cls, match='did not return a frame'):
        cam.Capture_Still()
    assert not cam.Connected and cam.events[-2:] == [('stop', 2), ('close',)]


def test_incomplete_frames_are_skipped_and_a_stream_of_only_incomplete_ones_fails(monkeypatch) -> None:
    """
    Description:
        A frame the device delivered incompletely (None) is skipped, never compared or returned; a stream that
        delivers no complete frame within CONST_STILL_TIMEOUT_S fails with a sentence naming the link.
    """

    cam = _Stream_Camera_Cls(lambda stream, index: None if index == 0 else _Frame(40))
    cam.Connect()
    assert np.array_equal(cam.Capture_Still(), _Frame(40))
    monkeypatch.setattr(Camera_Core, 'CONST_STILL_TIMEOUT_S', 0.05)
    cam.script = lambda stream, index: None
    cam.delay = 0.01
    with pytest.raises(Camera_Error_Cls, match='only incomplete frames'):
        cam.Capture_Still()
    assert cam.Connected


def test_the_preview_needs_a_connected_camera_and_a_running_stream() -> None:
    """
    Description:
        The preview is refused without a connection, a preview frame without a running preview, and a second start
        is a no-op (one stream).
    """

    cam = _Stream_Camera_Cls(_Still)
    with pytest.raises(Camera_Error_Cls, match='not connected'):
        cam.Start_Preview()
    cam.Connect()
    with pytest.raises(Camera_Error_Cls, match='not running'):
        cam.Preview_Frame()
    cam.Start_Preview()
    cam.Start_Preview()
    assert cam.events == [('start', 1)] and cam.Previewing
    cam.Stop_Preview()
    cam.Stop_Preview()
    assert cam.events == [('start', 1), ('stop', 1)] and not cam.Previewing


def test_the_scan_hands_on_every_frame_its_check_grabs() -> None:
    """
    Description:
        Capture_Still calls its frame callback with every complete frame the stillness check grabs, in order, the
        frame it keeps last — what the window shows while the scan waits — and skips an incomplete one.
    """

    frames = [_Frame(220), None, _Frame(40), _Frame(40)]
    cam = _Stream_Camera_Cls(lambda stream, index: frames[index])
    cam.Connect()
    shown = []
    kept = cam.Capture_Still(frame_cb=shown.append)
    assert [id(frame) for frame in shown] == [id(frames[0]), id(frames[2]), id(frames[3])] and shown[-1] is kept
