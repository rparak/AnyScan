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
# File Name: ../test/conftest.py
## =========================================================================== ##

# System (Default)
import os
import sys
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Typing (Support for type hints)
import typing as tp

"""
Description:
    Initialization of constants.
"""
# The repository root, resolved from this file's location (test/ -> ..). Every
# path fixture below is derived from it, so the suite is independent of the
# current working directory.
#   Unit [string]
CONST_PROJECT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# The committed reference background and its expected size. The size is the app's
# contract: segmentation differences a frame against this reference, so a frame
# must match it. cv2 reports shape as (height, width, channels).
#   Unit [string]
CONST_REFERENCE_BACKGROUND = os.path.join(CONST_PROJECT_FOLDER, 'Data', 'Images', 'Background', 'Image_Background_001.png')
#   Unit [Tuple<int> 1x3]
CONST_REFERENCE_SHAPE = (1200, 1920, 3)

# Directories the domain code and the harness live in, added to the import path
# so tests can import the extracted src/ modules, the application entry (run) and
# the characterization harness without any package wrapping.
#   Unit [Vector<string>]
CONST_IMPORT_PATHS = [
    os.path.join(CONST_PROJECT_FOLDER, 'src'),
    os.path.join(CONST_PROJECT_FOLDER, 'App'),
    os.path.join(CONST_PROJECT_FOLDER, 'Example', 'Vision'),
]

for _path in CONST_IMPORT_PATHS:
    if _path not in sys.path:
        sys.path.insert(0, _path)


# << PYTEST HOOK >> #
def pytest_addoption(parser: pytest.Parser) -> None:
    """
    Description:
        Register the command-line flags:
          --runslow        Tests that genuinely need the model weights (FastSAM, Gemma) or other
                           heavy runtime are marked `slow` and skipped unless it is given, so the
                           default run needs no camera and no model.
          --update-golden  A golden-file test rewrites its committed file from the current
                           output instead of comparing against it — for an INTENDED behaviour
                           change; review the file's diff before committing it.

    Args:
        (1) parser [pytest.Parser(object)]: The pytest command-line parser.
    """

    parser.addoption('--runslow', action='store_true', default=False,
                     help='run tests marked slow (they need the model weights).')
    parser.addoption('--update-golden', action='store_true', default=False,
                     help='rewrite golden files from the current output (then review the diff).')


# << PYTEST HOOK >> #
def pytest_configure(config: pytest.Config) -> None:
    """
    Description:
        Register the `slow` marker so it does not raise under strict markers.

    Args:
        (1) config [pytest.Config(object)]: The active pytest configuration.
    """

    config.addinivalue_line('markers', 'slow: needs the model weights (FastSAM, Gemma) or other heavy runtime; '
                            'skipped unless --runslow.')


# << PYTEST HOOK >> #
def pytest_collection_modifyitems(config: pytest.Config, items: tp.List[pytest.Item]) -> None:
    """
    Description:
        Skip every `slow` test unless --runslow was passed, keeping the weights
        out of the default run.

    Args:
        (1) config [pytest.Config(object)]: The active pytest configuration.
        (2) items [Vector<pytest.Item>]: The collected test items.
    """

    if config.getoption('--runslow'):
        return

    skip_slow = pytest.mark.skip(reason='needs the model weights; pass --runslow to run.')
    for item in items:
        if 'slow' in item.keywords:
            item.add_marker(skip_slow)


@pytest.fixture
def project_root() -> str:
    """
    Description:
        The repository root as an absolute path.

    Returns:
        (1) parameter [string]: Absolute path to the repository root.
    """

    return CONST_PROJECT_FOLDER


@pytest.fixture
def reference_shape() -> tp.Tuple[int, int, int]:
    """
    Description:
        The reference background's expected shape (h, w, c) — the size a --frame
        input must match.

    Returns:
        (1) parameter [Tuple<int> 1x3]: (height, width, channels).
    """

    return CONST_REFERENCE_SHAPE


@pytest.fixture
def reference_background_path() -> str:
    """
    Description:
        Absolute path to the committed reference background (Data/Images/Background).

    Returns:
        (1) parameter [string]: Absolute path to Image_Background_001.png.
    """

    return CONST_REFERENCE_BACKGROUND


@pytest.fixture
def reference_background() -> np.ndarray:
    """
    Description:
        The reference background loaded as a BGR array, the way the pipeline reads
        it. Skips the test if the file is missing rather than failing obscurely.

    Returns:
        (1) parameter [Matrix<uint8> HxWx3]: The reference image (BGR).
    """

    image = cv2.imread(CONST_REFERENCE_BACKGROUND)
    if image is None:
        pytest.skip(f'reference background not readable at {CONST_REFERENCE_BACKGROUND}')
    return image


@pytest.fixture
def make_synthetic_frame() -> tp.Callable[[np.ndarray, tp.List[tp.Tuple[int, int, int, int]]], np.ndarray]:
    """
    Description:
        Factory that paints filled black rectangles onto a copy of a background,
        producing a same-size frame whose only difference is a known foreground.
        This is how the tests and the harness synthesize object frames without a
        camera.

    Returns:
        (1) parameter [function]: (background, rects) -> synthesized frame (BGR),
                                  where each rect is (x1, y1, x2, y2).
    """

    def _Build(background: np.ndarray,
               rects: tp.List[tp.Tuple[int, int, int, int]]) -> np.ndarray:
        frame = background.copy()
        for x1, y1, x2, y2 in rects:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 0), thickness=-1)
        return frame

    return _Build


def _Models_Inventory() -> tp.Dict[str, int]:
    """
    Description:
        Every file under the repository's models/ (the user's multi-GB, git-ignored weights) as
        {relative path: size}, Finder's .DS_Store excepted.

    Returns:
        (1) parameter [Dict<string, int>]: The inventory; empty when models/ holds no weights.
    """

    root = os.path.join(CONST_PROJECT_FOLDER, 'models')
    inventory = {}
    for folder, _dirs, files in os.walk(root):
        for name in files:
            if name != '.DS_Store':
                path = os.path.join(folder, name)
                inventory[os.path.relpath(path, root)] = os.path.getsize(path)
    return inventory


@pytest.fixture(scope='session', autouse=True)
def models_untouched() -> tp.Iterator[None]:
    """
    Description:
        The suite must leave models/ exactly as it found it: the weights are git-ignored, so git cannot
        restore them. The inventory is taken before the first test and compared after the last; any
        file removed, added or resized fails the run, naming each one — so a change is attributed to
        this run the moment it happens, not discovered later. (models/ was emptied by hand on 2026-09-24
        and again on 2026-09-25 — manual both times, not code; this fixture is what showed, run by run,
        that the suite had not done it. See docs/design-decisions.md.)
    """

    before = _Models_Inventory()
    yield
    after = _Models_Inventory()
    changes = (['removed: %s' % name for name in sorted(set(before) - set(after))]
               + ['added: %s' % name for name in sorted(set(after) - set(before))]
               + ['resized: %s' % name for name in sorted(set(before) & set(after)) if before[name] != after[name]])
    assert not changes, 'The test run changed models/:\n  ' + '\n  '.join(changes)
