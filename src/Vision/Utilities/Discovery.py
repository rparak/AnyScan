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

    Data-file discovery for the vision pipeline: which scene frames to analyse and
    which empty-surface reference to subtract against. Both are globs, never a
    hard-coded range or the first match, so the set the harness runs and the
    reference the app subtracts are resolved by a documented rule instead of by
    filename luck.

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

# The empty-surface reference glob. Several may be present (one per re-shoot of the
# empty table); Select_Background picks between them by the documented rule.
#   Unit [string]
CONST_BACKGROUND_GLOB = 'Image_Background_*.png'

# Parses the trailing index out of a reference name (Image_Background_007.png -> 7).
# A reference whose name does not end in an index cannot take part in the
# highest-index rule, so a set mixing indexed and unindexed names reads as ambiguous.
#   Unit [re.Pattern]
CONST_BACKGROUND_INDEX = re.compile(r'Image_Background_(\d+)\.png$', re.IGNORECASE)


class Discovery_Error_Cls(RuntimeError):
    """
    Description:
        Raised when the scene set or the reference cannot be resolved to a single
        unambiguous choice. Its message is a full, actionable sentence — the harness
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


def Select_Background(data_dir: str, configured_name: tp.Optional[str] = None) -> str:
    """
    Description:
        The empty-surface reference to subtract against, selected from the
        CONST_BACKGROUND_GLOB matches in a directory by a documented rule:

            (1) a configured name wins — if configured_name is given it must exist,
                otherwise the choice is an error rather than a silent fallback;
            (2) otherwise the highest index wins — Image_Background_007 over
                Image_Background_001;
            (3) an ambiguous set is an error — two references whose names carry no
                comparable index leave no unique highest one, so the reference is
                never picked by filename luck.

        A single reference is unambiguous and is returned as-is. The rule never
        silently picks the first match.

    Args:
        (1) data_dir [string]: The directory to search for reference images.
        (2) configured_name [string]: An explicit reference filename that must win,
                                      or None to apply the highest-index rule.

    Returns:
        (1) parameter [string]: The absolute path to the selected reference.
    """

    candidates = sorted(glob.glob(os.path.join(data_dir, CONST_BACKGROUND_GLOB)),
                        key=__Natural_Key)

    # Rule (1): a configured name wins, but only if it is actually present.
    if configured_name is not None:
        target = os.path.join(data_dir, os.path.basename(configured_name))
        for path in candidates:
            if os.path.basename(path).lower() == os.path.basename(configured_name).lower():
                return os.path.abspath(path)
        raise Discovery_Error_Cls(
            'The configured background reference "%s" was not found in "%s". '
            'Place it there, or clear the configured name to select the '
            'highest-indexed reference automatically.'
            % (os.path.basename(configured_name), data_dir))

    if not candidates:
        raise Discovery_Error_Cls(
            'No empty-surface reference (%s) was found in "%s". Shoot the empty '
            'table from this camera and save it there, then analyse again.'
            % (CONST_BACKGROUND_GLOB, data_dir))

    # A single reference is unambiguous whatever its name.
    if len(candidates) == 1:
        return os.path.abspath(candidates[0])

    # Rule (2): the highest index wins — but only when every candidate carries a
    # comparable index and one of them is a unique maximum.
    indexed = [(int(match.group(1)), path) for path in candidates
               for match in [CONST_BACKGROUND_INDEX.search(os.path.basename(path))] if match]
    if len(indexed) == len(candidates):
        top_index = max(index for index, _ in indexed)
        winners = [path for index, path in indexed if index == top_index]
        if len(winners) == 1:
            return os.path.abspath(winners[0])

    # Rule (3): nothing selects a unique reference — refuse rather than guess.
    raise Discovery_Error_Cls(
        'The background reference is ambiguous: %d references match %s in "%s" '
        '(%s) with no unique highest index. Keep one, or pass an explicit '
        'configured name.'
        % (len(candidates), CONST_BACKGROUND_GLOB, data_dir,
           ', '.join(os.path.basename(path) for path in candidates)))
