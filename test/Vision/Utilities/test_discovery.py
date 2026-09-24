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
# File Name: ../test/Vision/Utilities/test_discovery.py
## =========================================================================== ##

# System (Default)
import os
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan domain — data-file discovery
#   ../Vision/Utilities/Discovery
import Vision.Utilities.Discovery as Discovery

"""
Description:
    Tests for the scene-frame discovery rule (the scene glob). They run on synthetic empty
    files created under tmp_path, so the rule is exercised deterministically with no camera,
    no weights and no dependence on the committed Data/Images/Test/ set. (The background reference
    is not discovered any more — it is the configuration's Segmentation.Background.Reference —
    so its selection-rule tests went with the rule.)
"""


def __Touch(directory: str, *names: str) -> None:
    """
    Description:
        Create each named empty file under a directory — a stand-in scene or
        reference whose pixels are never read, only its path resolved.

    Args:
        (1) directory [string]: The directory to create the files in.
        (2) names [Vector<string>]: The filenames to create.
    """

    for name in names:
        open(os.path.join(directory, name), 'w').close()


def test_scene_glob_orders_naturally_and_tolerates_a_gap(tmp_path) -> None:
    """
    Description:
        The scene glob finds the Image_<n> frames in natural order, tolerates the
        missing Image_001, and excludes both the empty-surface reference and any
        stray file — the glob-not-a-range contract. Image_010 is included and sorts
        after Image_008 (natural, not lexicographic, order), the guard against
        silently skipping a two-digit frame.
    """

    __Touch(str(tmp_path), 'Image_002.png', 'Image_010.png', 'Image_008.png',
            'Image_003.png', 'Image_Background_001.png', 'notes.txt')

    scenes = [os.path.basename(path) for path in Discovery.Discover_Scenes(str(tmp_path))]

    # The reference and the stray file are excluded; Image_010 is kept and ordered
    # after Image_008; the missing Image_001 is simply absent, not an error.
    assert scenes == ['Image_002.png', 'Image_003.png', 'Image_008.png', 'Image_010.png']


def test_scene_glob_empty_directory_returns_empty(tmp_path) -> None:
    """
    Description:
        A directory with no scene frames yields an empty list rather than raising —
        the caller decides whether "no scenes" is an error in its context.
    """

    assert Discovery.Discover_Scenes(str(tmp_path)) == []
