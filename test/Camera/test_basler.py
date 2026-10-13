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
# File Name: ../test/Camera/test_basler.py
## =========================================================================== ##

# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — the Basler driver and the camera layer
#   ../Camera/Basler
pytest.importorskip('pypylon')
import Camera.Basler as Basler
from Camera.Basler import Basler_Cls, Basler_Settings_Error_Cls
#   ../Camera/Core
from Camera.Core import Basler_Camera_Cls, Camera_Error_Cls
#   ../Parameters/Camera
from Parameters.Camera import Camera_Configuration_Str

"""
Description:
    Tests for the sensor window: Basler_Cls sets Width / Height / OffsetX / OffsetY on every connect
    and reads them back, and the camera layer reports and logs what the camera read back.

    The device is a stand-in with the a2A1920-51gcPRO's geometry as the real camera reported it
    (read-only, 2026-09-24): a 1936 x 1216 sensor, Width from 4 in steps of 4, Height from 2 in steps
    of 2, OffsetX in steps of 4, OffsetY in steps of 2, and — the constraint the set order exists for
    — each offset capped by the current size and each size by the current offset, as GenICam does.
    On the real device (2026-09-24): the accessors (Value, Min, Max, Inc) were first checked read-only;
    then Basler_Camera_Cls.Connect with the shipped configuration took the camera from its factory
    1936 x 1216 at (0, 0) to 1920 x 1200 at (8, 8), read it back, logged the line, and the grabbed
    frame was 1200 x 1920 x 3. The refusal paths (no fit, off-grid, sticky value, SDK refusal) are
    exercised here only, against the stand-in.
"""
# The a2A1920-51gcPRO sensor, as the camera reports it.
#   Unit [Vector<int> 1x2] (px)
CONST_SENSOR = (1936, 1216)
# The camera settings a configuration hands over.
#   Unit [Dictionary]
CONST_CUSTOM_CFG = {'Exposure_Time': 10000, 'Gain': 10, 'Pixel_Format': 'BayerRG8',
                    'Balance_Ratios': {'Red': 0.95, 'Green': 0.9, 'Blue': 1.2}}


class _Node_Cls(object):
    """
    Description:
        One integer or float camera node: Value, SetValue, and the Min / Max / Inc limits. Max may be
        a callable, so a size's maximum can depend on the current offset and vice versa.
    """

    def __init__(self, device: '_Device_Cls', name: str, value: tp.Any, minimum: tp.Any = 0,
                 maximum: tp.Any = None, step: int = 1) -> None:
        self.device, self.name, self.Value = device, name, value
        self.Min, self.__maximum, self.Inc = minimum, maximum, step

    @property
    def Max(self) -> tp.Any:
        return self.__maximum() if callable(self.__maximum) else self.__maximum

    def SetValue(self, value: tp.Any) -> None:
        self.device.calls.append((self.name, value))
        if self.name in self.device.sticky:
            return                                                  # the camera silently keeps its value
        if self.Max is not None and not (self.Min <= value <= self.Max):
            raise RuntimeError('OutOfRangeException: %s %r not in [%r, %r]' % (self.name, value, self.Min, self.Max))
        self.Value = value


class _Ratio_Node_Cls(_Node_Cls):
    """
    Description:
        The BalanceRatio node: one ratio per colour, the one BalanceRatioSelector names, rounded to the node's
        step as the camera does. A step of 0 stands for a node that reports none (reading Inc raises).
    """

    def __init__(self, device: '_Device_Cls', step: float) -> None:
        self.ratios = {}
        super().__init__(device, 'BalanceRatio', None, 0.0, 15.0)
        self.__step = step

    @property
    def Inc(self) -> float:
        if not self.__step:
            raise RuntimeError('LogicalErrorException: BalanceRatio has no increment')
        return self.__step

    @Inc.setter
    def Inc(self, value: float) -> None:
        pass                                                        # the step is fixed at construction

    @property
    def Value(self) -> float:
        return self.ratios.get(self.device.BalanceRatioSelector.Value, 1.0)

    @Value.setter
    def Value(self, value: tp.Any) -> None:
        if value is not None:
            step = self.__step or 0.0
            self.ratios[self.device.BalanceRatioSelector.Value] = round(value / step) * step if step else value


class _Device_Cls(object):
    """
    Description:
        A stand-in pylon InstantCamera with the a2A1920-51gcPRO's window constraints.

    Initialization of the Class:
        Args:
            (1) width, height, offset_x, offset_y [int]: The window the camera starts at (default: the
                full sensor, its factory default after a power cycle).
            (2) sticky [Vector<string>]: Nodes that accept a write but keep their value.
            (3) ratio_step [float]: The BalanceRatio node's step (0: it reports none).
    """

    def __init__(self, width: int = CONST_SENSOR[0], height: int = CONST_SENSOR[1], offset_x: int = 0,
                 offset_y: int = 0, sticky: tp.Tuple[str, ...] = (), ratio_step: float = 1.0 / 64.0) -> None:
        self.calls, self.sticky, self.open, self.grabbing = [], sticky, True, False
        self.Width = _Node_Cls(self, 'Width', width, 4, lambda: CONST_SENSOR[0] - self.OffsetX.Value, 4)
        self.Height = _Node_Cls(self, 'Height', height, 2, lambda: CONST_SENSOR[1] - self.OffsetY.Value, 2)
        self.OffsetX = _Node_Cls(self, 'OffsetX', offset_x, 0, lambda: CONST_SENSOR[0] - self.Width.Value, 4)
        self.OffsetY = _Node_Cls(self, 'OffsetY', offset_y, 0, lambda: CONST_SENSOR[1] - self.Height.Value, 2)
        self.Gain = _Node_Cls(self, 'Gain', 0.0)
        self.ExposureTime = _Node_Cls(self, 'ExposureTime', 5000.0)
        self.PixelFormat = _Node_Cls(self, 'PixelFormat', 'Mono8')
        for name in ('BalanceWhiteAuto', 'BalanceRatioSelector', 'ExposureAuto', 'GainAuto'):
            setattr(self, name, _Node_Cls(self, name, None))
        self.BalanceRatio = _Ratio_Node_Cls(self, ratio_step)
        # Read, never set: the power-up user set's gamma and colour preset.
        self.Gamma = _Node_Cls(self, 'Gamma', 1.0)
        self.LightSourcePreset = _Node_Cls(self, 'LightSourcePreset', 'Daylight5000K')

    def IsGrabbing(self) -> bool:
        return self.grabbing

    def StopGrabbing(self) -> None:
        self.grabbing = False

    def IsOpen(self) -> bool:
        return self.open

    def Close(self) -> None:
        self.open = False


def _Connect(monkeypatch: tp.Any, device: _Device_Cls, resolution: tp.Tuple[int, int] = (1920, 1200),
             offset: tp.Tuple[int, int] = (8, 8), **pins: tp.Any) -> Basler_Cls:
    """
    Description:
        Construct Basler_Cls against the stand-in device: the connection hands it the device, and the
        GigE transport tuning (a property of the network, not of the window) is skipped.

    Args:
        (1) monkeypatch [MonkeyPatch(object)]: pytest's monkeypatch.
        (2) device [_Device_Cls(object)]: The stand-in camera.
        (3 - 4) resolution, offset [Vector<int> 1x2]: The configured window.
        (5) pins [Dict]: Custom_Cfg pins to add (Gamma, Light_Source_Preset).

    Returns:
        (1) parameter [Basler_Cls(object)]: The configured driver.
    """

    def _Connect_Stub(self, max_retries: int, retry_delay: int) -> None:
        self.camera = device

    monkeypatch.setattr(Basler_Cls, '_Basler_Cls__Connect', _Connect_Stub)
    monkeypatch.setattr(Basler_Cls, '_Basler_Cls__Configure_Transport', lambda self: None)
    monkeypatch.setattr(Basler.pylon, 'ImageFormatConverter', lambda: type('_Converter', (), {})())

    return Basler_Cls(config=dict(CONST_CUSTOM_CFG, **pins), resolution=resolution, offset=offset)


def test_a_factory_default_camera_is_set_to_the_configured_window(monkeypatch) -> None:
    """
    Description:
        From the state a power cycle leaves (the full 1936 x 1216 sensor), connecting sets the
        configured 1920 x 1200 at (8, 8): offsets to 0 first, then the size, then the offsets. What
        the camera reads back is reported, with the sensor size and the other settings.
    """

    device = _Device_Cls()
    camera = _Connect(monkeypatch, device)
    window = [call for call in device.calls if call[0] in ('Width', 'Height', 'OffsetX', 'OffsetY')]
    assert window == [('OffsetX', 0), ('OffsetY', 0), ('Width', 1920), ('Height', 1200), ('OffsetX', 8), ('OffsetY', 8)]
    applied = camera.Applied_Settings
    assert (applied['resolution'], applied['offset'], applied['sensor']) == ((1920, 1200), (8, 8), CONST_SENSOR)
    assert (applied['exposure_us'], applied['gain'], applied['pixel_format']) == (10000.0, 10.0, 'BayerRG8')
    assert applied['autos'] == {'ExposureAuto': 'Off', 'GainAuto': 'Off', 'BalanceWhiteAuto': 'Off'}
    # Gain auto is switched off before the gain is set, so a camera that powered up with it on keeps the value.
    names = [name for name, _value in device.calls]
    assert ('GainAuto', 'Off') in device.calls and names.index('GainAuto') < names.index('Gain')


def test_the_set_order_reaches_a_window_a_naive_order_cannot(monkeypatch) -> None:
    """
    Description:
        From a narrow window far to the right (Width 1000 at OffsetX 900), setting Width 1920 first
        is out of range (1920 + 900 > 1936). Zeroing the offsets first makes every step legal.
    """

    device = _Device_Cls(width=1000, height=600, offset_x=900, offset_y=600)
    camera = _Connect(monkeypatch, device)
    assert camera.Applied_Settings['resolution'] == (1920, 1200) and camera.Applied_Settings['offset'] == (8, 8)


@pytest.mark.parametrize('resolution, offset, words', [
    ((1936, 1216), (8, 8), 'does not fit this camera\'s 1936 × 1216 sensor'),
    ((1921, 1200), (8, 8), 'cannot set Width to 1921: it takes values from 4 in steps of 4'),
    ((1920, 1200), (6, 8), 'cannot set OffsetX to 6: it takes values from 0 in steps of 4')])
def test_a_window_the_camera_cannot_take_is_refused_and_the_device_closed(monkeypatch, resolution, offset,
                                                                          words) -> None:
    """
    Description:
        A window that does not fit the sensor, or is off the camera's step grid, is refused in the
        configuration's terms before anything is set — and the device is closed again, so a refused
        connect never leaves it locked for the next one.
    """

    device = _Device_Cls()
    with pytest.raises(Basler_Settings_Error_Cls, match=words):
        _Connect(monkeypatch, device, resolution, offset)
    assert not device.open
    assert ('Width', resolution[0]) not in device.calls


def test_a_camera_that_does_not_keep_the_window_fails_on_read_back(monkeypatch) -> None:
    """
    Description:
        The failure this exists for: a camera that accepts the write but keeps another size. The read
        back catches it at connect, naming what the camera reports and what was set, instead of the
        next frame of the wrong size being the first sign.
    """

    device = _Device_Cls(sticky=('OffsetY',))
    with pytest.raises(Basler_Settings_Error_Cls, match=r'did not keep the configured sensor window: it reports '
                                                        r'OffsetY 0 \(set 8\)'):
        _Connect(monkeypatch, device)
    assert not device.open


@pytest.mark.parametrize('node', ['ExposureAuto', 'GainAuto', 'BalanceWhiteAuto'])
def test_a_camera_that_keeps_an_automatic_mode_is_refused(monkeypatch, node: str) -> None:
    """
    Description:
        Exposure, gain and white balance stay as the station file sets them: a camera that accepts the
        switch to Off but keeps an automatic mode (here: still Continuous) is refused at connect, naming the
        mode, and closed — the colours, the background difference and the stain check assume them fixed.
    """

    device = _Device_Cls(sticky=(node,))
    getattr(device, node).Value = 'Continuous'
    with pytest.raises(Basler_Settings_Error_Cls, match='kept an automatic mode on after it was switched off: %s '
                                                        'Continuous' % node):
        _Connect(monkeypatch, device)
    assert not device.open


def test_an_sdk_refusal_while_setting_is_a_settings_error(monkeypatch) -> None:
    """
    Description:
        A camera that keeps its full width makes the next write (OffsetX 8) out of range inside the
        SDK. That is reported as a settings failure naming the window — never as a missing camera —
        and the device is closed.
    """

    device = _Device_Cls(sticky=('Width',))
    with pytest.raises(Basler_Settings_Error_Cls, match=r'refused the sensor window 1920 × 1200 at offset \(8, 8\)'):
        _Connect(monkeypatch, device)
    assert not device.open


def test_gamma_and_the_colour_preset_are_read_and_logged_never_set(monkeypatch) -> None:
    """
    Description:
        Unpinned (the shipped station file), gamma and the colour preset are read back and kept for the log,
        named as not pinned, and nothing is written to either node: they stay the camera's power-up user set.
    """

    device = _Device_Cls()
    applied = _Connect(monkeypatch, device).Applied_Settings
    assert applied['pinned'] == {'Gamma': 1.0, 'LightSourcePreset': 'Daylight5000K'}
    assert applied['unpinned'] == ['Gamma', 'LightSourcePreset']
    assert not [call for call in device.calls if call[0] in ('Gamma', 'LightSourcePreset')]


@pytest.mark.parametrize('pins, words', [
    ({'Gamma': 0.7}, 'Gamma reads 1.0, the station file pins 0.7'),
    ({'Light_Source_Preset': 'Tungsten2800K'}, 'LightSourcePreset reads Daylight5000K, the station file pins Tungsten2800K'),
], ids=['gamma', 'colour preset'])
def test_a_camera_that_does_not_match_a_pin_is_refused(monkeypatch, pins: tp.Dict, words: str) -> None:
    """
    Description:
        A station file that pins gamma or the colour preset refuses a camera that reads otherwise, naming both
        values, and the device is closed; a camera that matches its pins connects with nothing left unpinned.
    """

    device = _Device_Cls()
    with pytest.raises(Basler_Settings_Error_Cls, match='does not match the station file: %s' % words):
        _Connect(monkeypatch, device, **pins)
    assert not device.open
    matching = _Connect(monkeypatch, _Device_Cls(), Gamma=1.0, Light_Source_Preset='Daylight5000K')
    assert matching.Applied_Settings['unpinned'] == []


def test_a_node_the_camera_lacks_is_logged_and_refuses_a_pin(monkeypatch) -> None:
    """
    Description:
        A camera without a colour-preset node (the rig's a2A1920-51gcPRO, 2026-10-13) reads 'not available':
        logged and never an error when unpinned — with Gamma pinned, as the shipped station file has it — and
        refused when the station file pins a preset.
    """

    device = _Device_Cls()
    del device.LightSourcePreset
    applied = _Connect(monkeypatch, device, Gamma=1.0).Applied_Settings
    assert applied['pinned'] == {'Gamma': 1.0, 'LightSourcePreset': 'not available'}
    assert applied['unpinned'] == ['LightSourcePreset']
    device = _Device_Cls()
    del device.LightSourcePreset
    with pytest.raises(Basler_Settings_Error_Cls, match='LightSourcePreset reads not available'):
        _Connect(monkeypatch, device, Light_Source_Preset='Daylight5000K')


def test_the_white_balance_ratios_are_read_back_within_half_the_camera_step(monkeypatch) -> None:
    """
    Description:
        The camera rounds each ratio to its BalanceRatio step (here 1/64: 0.95 reads 0.953125), so the
        read-back is accepted within half that step; the ratios and the tolerance are kept for the log.
    """

    applied = _Connect(monkeypatch, _Device_Cls()).Applied_Settings
    assert applied['balance_ratios'] == {'Red': 0.953125, 'Green': 0.90625, 'Blue': 1.203125}
    assert applied['balance_tolerance'] == (1.0 / 128.0, 'half the camera\'s step')
    fine = _Connect(monkeypatch, _Device_Cls(ratio_step=1.0 / 1024.0)).Applied_Settings
    assert fine['balance_tolerance'] == (1.0 / 2048.0, 'half the camera\'s step')


def test_a_ratio_node_without_a_step_uses_the_fallback_tolerance(monkeypatch) -> None:
    """
    Description:
        A BalanceRatio node that reports no step is checked to CONST_BASLER_BALANCE_FALLBACK_TOLERANCE (1/128),
        and the log says so.
    """

    applied = _Connect(monkeypatch, _Device_Cls(ratio_step=0.0)).Applied_Settings
    assert applied['balance_ratios'] == {'Red': 0.95, 'Green': 0.9, 'Blue': 1.2}
    assert applied['balance_tolerance'] == (1.0 / 128.0, 'the camera reports no step')


def test_a_camera_that_does_not_keep_the_white_balance_is_refused(monkeypatch) -> None:
    """
    Description:
        The stain check's colour band was measured under the station file's ratios: a camera that accepts the
        ratios but keeps its own (here 1.0 for each) is refused at connect, naming each colour that differs,
        what it reads and what the station file sets, and the device is closed.
    """

    device = _Device_Cls(sticky=('BalanceRatio',))
    with pytest.raises(Basler_Settings_Error_Cls, match=r'did not keep the station file\'s white balance: Red reads 1, '
                                                        r'the station file sets 0.95; Green reads 1, the station file '
                                                        r'sets 0.9; Blue reads 1, the station file sets 1.2 '
                                                        r'\(tolerance ± 0.0078125, half the camera\'s step\)'):
        _Connect(monkeypatch, device)
    assert not device.open


class _Fake_Basler_Cls(object):
    """A stand-in Basler_Cls for the camera layer: the read-back settings, or a settings error."""

    refuse = ''

    def __init__(self, config: tp.Dict, resolution: tp.Tuple[int, int], offset: tp.Tuple[int, int]) -> None:
        if self.refuse:
            raise Basler_Settings_Error_Cls(self.refuse)
        self.camera = object()
        self.Applied_Settings = {'resolution': tuple(resolution), 'offset': tuple(offset), 'sensor': CONST_SENSOR,
                                 'exposure_us': 10000.0, 'gain': 9.999998795594486, 'pixel_format': 'BayerRG8',
                                 'autos': {'ExposureAuto': 'Off', 'GainAuto': 'Off', 'BalanceWhiteAuto': 'Off'},
                                 'balance_ratios': {'Red': 0.953125, 'Green': 0.90625, 'Blue': 1.203125},
                                 'balance_tolerance': (1.0 / 128.0, 'half the camera\'s step'),
                                 'pinned': {'Gamma': 1.0, 'LightSourcePreset': 'not available'},
                                 'unpinned': ['LightSourcePreset']}


def _Configured_Camera() -> Basler_Camera_Cls:
    """A Basler backend with the shipped window handed over, and its log captured in .events."""
    camera = Basler_Camera_Cls()
    camera.Set_Configuration(Camera_Configuration_Str(Custom_Cfg=dict(CONST_CUSTOM_CFG), Resolution=(1920, 1200),
                                                      Offset=(8, 8)), 'Config_Test.yaml', '')
    camera.events = []
    camera.Set_Log_Callback(lambda level, message: camera.events.append((level, message)))
    return camera


def test_the_camera_layer_logs_the_window_it_read_back(monkeypatch) -> None:
    """
    Description:
        On connect the session log gets one line with what the camera read back — the window, its
        offset, the sensor, the exposure, the gain and the pixel format — so a camera that ever
        reverts is visible in the log. Before connecting, Resolution is the configuration's window;
        with no configuration it is (0, 0), never a constant that happens to match.
    """

    monkeypatch.setattr(Basler, 'Basler_Cls', _Fake_Basler_Cls)
    assert Basler_Camera_Cls().Resolution == (0, 0)
    camera = _Configured_Camera()
    assert camera.Resolution == (1920, 1200)
    camera.Connect()
    assert camera.Resolution == (1920, 1200)
    assert ('INFO', 'Camera set to 1920 × 1200 at offset (8, 8) of its 1936 × 1216 sensor, exposure 10000 µs, gain '
                    '10.00, BayerRG8, ExposureAuto Off, GainAuto Off, BalanceWhiteAuto Off, BalanceRatio Red 0.953125, '
                    'Green 0.90625, Blue 1.20312 (± 0.0078125, half the camera\'s step), Gamma 1, LightSourcePreset '
                    'not available (read back from the camera; LightSourcePreset not pinned).') \
        in camera.events


def test_a_settings_error_is_reported_as_it_stands_not_as_no_camera(monkeypatch) -> None:
    """
    Description:
        A camera that was reached but refused the window is not reported as 'No Basler camera was
        detected': the operator gets the settings sentence, which says what to correct.
    """

    monkeypatch.setattr(Basler, 'Basler_Cls', _Fake_Basler_Cls)
    monkeypatch.setattr(_Fake_Basler_Cls, 'refuse', 'Camera.Resolution 1936 × 1216 at Camera.Offset (8, 8) does '
                                                    'not fit this camera\'s 1936 × 1216 sensor.')
    camera = _Configured_Camera()
    with pytest.raises(Camera_Error_Cls, match='does not fit') as error:
        camera.Connect()
    assert 'No Basler camera' not in str(error.value)


def test_a_frame_of_another_size_is_refused_at_the_grab(monkeypatch) -> None:
    """
    Description:
        The safety net behind the window set on connect: a delivered frame of another size than the
        configuration's is refused at the grab, naming both sizes, before undistortion or analysis.
    """

    import numpy as np
    camera = _Configured_Camera()
    device = type('_Device', (), {'Capture': lambda self: np.zeros((1216, 1936, 3), np.uint8)})()
    setattr(camera, '_Basler_Camera_Cls__cam', device)
    with pytest.raises(Camera_Error_Cls, match='delivered a 1936 × 1216 frame, but the configuration sets it to '
                                               '1920 × 1200'):
        camera._Grab()
