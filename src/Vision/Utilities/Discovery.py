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
# File Name: ../Vision/Utilities/Discovery.py
## =========================================================================== ##

# System (Default)
import os
import re
import glob
# Typing (Support for type hints)
import typing as tp

"""
Description:
    Initialization of constants.

    Data-file discovery for the harness: which scene frames to analyse — a glob, never a
    hard-coded range or the first match, so Image_010 and beyond are found. The empty-surface
    reference is NOT discovered: it is stated in the configuration
    (Segmentation.Background.Reference), because it decides every background-subtraction result
    and two ways of choosing it would be an ambiguity.

    Note:
        Pure stdlib (os, re, glob) — no OpenCV, no NumPy, no Qt. It resolves file
        paths, it does not read pixels, so App/run.py can import it at load time
        and the tests exercise it with synthetic files and no camera.
"""
# The scene-frame glob. Image_<n>.png (any number of digits) are the scene
# captures, so Image_010 and beyond are found rather than silently skipped. The
# empty-surface reference is excluded because the digit class requires a digit
# straight after 'Image_', which 'Image_Background_*' never has, so the two
# patterns never overlap.
#   Unit [string]
CONST_SCENE_GLOB = 'Image_[0-9]*.png'


class Discovery_Error_Cls(RuntimeError):
    """
    Description:
        Raised when the scene set cannot be resolved. Its message is a full, actionable sentence — the harness
        prints it straight to the operator, the same contract as Vision_Error_Cls.
    """


def __Natural_Key(path: str) -> tp.Tuple[tp.Any, ...]:
    """
    Description:
        Sort key that orders 'Image_2.png' before 'Image_10.png' by reading each
        run of digits in the basename as an integer rather than as text, so a
        natural (human) order is produced instead of a lexicographic one.

    Args:
        (1) path [string]: The file path to derive the key from.

    Returns:
        (1) parameter [Tuple]: A tuple of (int | str) segments for use as a sort key.
    """

    name = os.path.basename(path)
    # Split into digit and non-digit runs; digit runs compare as ints, the rest
    # as lower-cased text, so ('Image_', 2) sorts before ('Image_', 10).
    return tuple(int(chunk) if chunk.isdigit() else chunk.lower()
                for chunk in re.split(r'(\d+)', name))


def Discover_Scenes(data_dir: str) -> tp.List[str]:
    """
    Description:
        The scene frames in a directory, naturally sorted. Globs CONST_SCENE_GLOB
        and returns the matches in natural order (Image_2 before Image_10), never a
        hard-coded range: a gap in the numbering (a missing Image_001) is tolerated,
        and the empty-surface reference is not among the matches (its name does not
        begin 'Image_0').

    Args:
        (1) data_dir [string]: The directory to search for scene frames.

    Returns:
        (1) parameter [Vector<string>]: The scene-frame paths, naturally sorted.
    """

    matches = glob.glob(os.path.join(data_dir, CONST_SCENE_GLOB))
    return sorted(matches, key=__Natural_Key)
