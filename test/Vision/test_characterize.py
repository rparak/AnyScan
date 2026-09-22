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
# File Name: ../test/Vision/test_characterize.py
## =========================================================================== ##

# System (Default)
import os
# Pytest (Testing framework) [pip3 install pytest]
import pytest

"""
Description:
    Scaffold tests for the pre-extraction state of the migration. Nothing has been
    moved into src/ yet, so these pin only the two things everything downstream
    relies on: the characterization harness imports, and the committed reference
    background resolves at the resolution the pipeline expects. As each module is
    extracted, its own test_<module>.py is added beside it in the same commit.

    The whole file runs with no camera and no model weights.
"""


def test_reference_background_file_exists(reference_background_path: str) -> None:
    """
    Description:
        The committed reference background is present at its Data/Camera/ path.
    """

    assert os.path.isfile(reference_background_path)


def test_reference_background_loads_at_expected_shape(reference_background, reference_shape) -> None:
    """
    Description:
        The reference loads as a BGR array at 1200x1920x3 — the size a --frame
        input must match, since segmentation differences the two.
    """

    assert reference_background.shape == reference_shape


def test_unused_second_background_is_absent(project_root: str) -> None:
    """
    Description:
        Image_Background_002.png was a mismatched-resolution extra and was removed;
        confirm it did not creep back into Data/Camera/.
    """

    stray = os.path.join(project_root, 'Data', 'Camera', 'Image_Background_002.png')
    assert not os.path.exists(stray)


def test_harness_module_imports() -> None:
    """
    Description:
        The characterization harness imports cleanly (which, pre-extraction, also
        imports App/run.py and therefore PyQt5) and still exposes the helpers the
        migration re-runs it through.
    """

    import characterize

    for name in ('main', '_Make_Synthetic_Frame', '_Characterize_Segmentation'):
        assert callable(getattr(characterize, name))


def test_harness_reference_constant_points_at_001() -> None:
    """
    Description:
        The harness reads the same committed reference these tests do, so the two
        can never silently diverge onto different files.
    """

    import characterize

    assert characterize.CONST_BACKGROUND_A.endswith(os.path.join('Data', 'Camera', 'Image_Background_001.png'))


def test_make_synthetic_frame_preserves_shape(reference_background, make_synthetic_frame) -> None:
    """
    Description:
        The synthetic-frame factory returns a same-size frame — the invariant that
        lets it be differenced against the reference without a size mismatch.
    """

    rects = [(300, 300, 560, 560)]
    frame = make_synthetic_frame(reference_background, rects)
    assert frame.shape == reference_background.shape
    # The drawn region actually changed; the rest is untouched.
    assert not (frame == reference_background).all()
