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
# File Name: ../test/Vision/test_segmenter.py
## =========================================================================== ##

# Dataclasses (the shipped segmentation parameters, pointed at the stand-in weights)
import dataclasses
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan — the segmenter and the configuration layer
#   ../Vision/Segmenter
from Vision.Segmenter import Fast_Sam_Cls
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    The FastSAM segmenter's device sync, without weights or an accelerator: the real Fast_Sam_Cls on
    stand-in torch / ultralytics (test/conftest.py fake_runtimes). It synchronises the device its
    weights are actually on, and nothing on the CPU — where the MPS and CUDA syncs would raise.
"""


def _Segmenter(runtime, device_setting: str) -> Fast_Sam_Cls:
    """The real segmenter on the stand-in weights, with the given configured device."""
    params = Load_Configuration(CONST_DEFAULT_CONFIG_FILE).Segmentation
    return Fast_Sam_Cls(dataclasses.replace(params, Model_Path=runtime.segmenter_path, Device=device_setting))


def test_a_model_on_the_cpu_is_never_synchronised(fake_runtimes) -> None:
    """
    Description:
        With the weights on the CPU, Segment calls neither the MPS nor the CUDA sync — on a machine
        without them those raise (the stand-ins do) — and the frame is segmented.
    """

    fake_runtimes.model_device, fake_runtimes.sync_raises = 'cpu', True
    masks, scores = _Segmenter(fake_runtimes, 'cpu').Segment(np.zeros((40, 60, 3), np.uint8))
    assert fake_runtimes.torch_syncs == []
    assert len(masks) == 1 and scores == [pytest.approx(0.9)]


@pytest.mark.parametrize('device', ['mps', 'cuda'])
def test_the_device_the_weights_are_on_is_synchronised(fake_runtimes, device) -> None:
    """
    Description:
        The sync follows the device the model's weights report, not the configured setting ('auto'
        here): MPS weights sync MPS, CUDA weights sync CUDA, once per Segment.
    """

    fake_runtimes.model_device = device
    _Segmenter(fake_runtimes, 'auto').Segment(np.zeros((40, 60, 3), np.uint8))
    assert fake_runtimes.torch_syncs == [device]
