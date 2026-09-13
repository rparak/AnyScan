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
# File Name: ../test/Vision/Utilities/test_discovery.py
## =========================================================================== ##

# System (Default)
import os
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan domain — data-file discovery
#   ../Vision/Utilities/Discovery
import Vision.Utilities.Discovery as Discovery
from Vision.Utilities.Discovery import Discovery_Error_Cls

"""
Description:
    Tests for the data-file discovery rules (scene glob + background selection).
    They run on synthetic empty files created under tmp_path, so the rules are
    exercised deterministically with no camera, no weights and no dependence on the
    committed Data/Camera/ set.
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


def test_background_single_reference_is_returned(tmp_path) -> None:
    """
    Description:
        A lone reference is unambiguous and is returned whatever its index.
    """

    __Touch(str(tmp_path), 'Image_Background_001.png', 'Image_002.png')

    chosen = Discovery.Select_Background(str(tmp_path))
    assert os.path.basename(chosen) == 'Image_Background_001.png'


def test_background_highest_index_wins(tmp_path) -> None:
    """
    Description:
        With several references present, the highest index wins — never the first
        match by name.
    """

    __Touch(str(tmp_path), 'Image_Background_001.png', 'Image_Background_002.png',
            'Image_Background_010.png')

    chosen = Discovery.Select_Background(str(tmp_path))
    assert os.path.basename(chosen) == 'Image_Background_010.png'


def test_background_configured_name_wins(tmp_path) -> None:
    """
    Description:
        A configured name overrides the highest-index rule, as long as it exists.
    """

    __Touch(str(tmp_path), 'Image_Background_001.png', 'Image_Background_009.png')

    chosen = Discovery.Select_Background(str(tmp_path), configured_name='Image_Background_001.png')
    assert os.path.basename(chosen) == 'Image_Background_001.png'


def test_background_configured_name_missing_raises(tmp_path) -> None:
    """
    Description:
        A configured name that is not present is an error, not a silent fallback to
        the highest index.
    """

    __Touch(str(tmp_path), 'Image_Background_001.png')

    with pytest.raises(Discovery_Error_Cls):
        Discovery.Select_Background(str(tmp_path), configured_name='Image_Background_099.png')


def test_background_none_present_raises(tmp_path) -> None:
    """
    Description:
        No reference at all is a clear error naming the glob and the directory.
    """

    __Touch(str(tmp_path), 'Image_002.png')

    with pytest.raises(Discovery_Error_Cls):
        Discovery.Select_Background(str(tmp_path))


def test_background_ambiguous_set_raises(tmp_path) -> None:
    """
    Description:
        References whose names carry no comparable index leave no unique highest
        one, so the choice is refused rather than made by filename luck.
    """

    __Touch(str(tmp_path), 'Image_Background_left.png', 'Image_Background_right.png')

    with pytest.raises(Discovery_Error_Cls):
        Discovery.Select_Background(str(tmp_path))
