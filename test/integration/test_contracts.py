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
# File Name: ../test/integration/test_contracts.py
## =========================================================================== ##

# System (Default)
import os
import sys
import glob
import subprocess
# Custom Lib.: AnyScan domain — the camera backend
#   ../Camera/Core
from Camera.Core import File_Camera_Cls

"""
Description:
    The contracts the restructure was for. These pin the seams between the modules,
    so a failure names a broken connection rather than a broken module:
      (1) Capture() returns an RGB ndarray of the expected shape and dtype.
      (2) Analyze() accepts that array directly, with no conversion.
      (3) Every domain module imports with PyQt5 unavailable.
      (4) No Qt import may reappear in Camera/, Vision/ or Reporting/.
"""

# The Qt-free domain modules — none may import Qt.
CONST_DOMAIN_MODULES = [
    'Camera.Core', 'Camera.Basler', 'Camera.Utilities.Image_Processing',
    'Vision.Core', 'Vision.Utilities.Segmentation', 'Vision.Utilities.Caption',
    'Reporting.Core', 'Parameters.Vision',
]


def test_capture_returns_rgb_ndarray(reference_background_path, reference_shape) -> None:
    """
    Description:
        The camera's Capture() contract: a contiguous RGB ndarray at the reference
        resolution, uint8, three channels.
    """

    camera = File_Camera_Cls(reference_background_path)
    camera.Connect()
    frame = camera.Capture()

    assert frame.shape == reference_shape
    assert frame.ndim == 3 and frame.shape[2] == 3
    assert str(frame.dtype) == 'uint8'
    assert frame.flags['C_CONTIGUOUS']


def test_analyze_accepts_capture_output_directly(reference_background_path, fake_backend) -> None:
    """
    Description:
        The camera -> vision contract: the array Capture() returns is fed straight
        into Analyze(), with no QImage and no conversion in between.
    """

    camera = File_Camera_Cls(reference_background_path)
    camera.Connect()
    frame = camera.Capture()

    # No conversion between the two calls.
    result = fake_backend.Analyze(frame)
    assert result.Objects


def test_domain_modules_import_without_pyqt(project_root) -> None:
    """
    Description:
        Every domain module imports in a fresh interpreter where PyQt5 is blocked —
        the separation the migration was for. Run in a subprocess so the block is
        clean and cannot be defeated by a module Qt already loaded in this process.
    """

    src = os.path.join(project_root, 'src')
    script = (
        'import sys, builtins\n'
        'real = builtins.__import__\n'
        'def guard(name, *a, **k):\n'
        "    if name.startswith('PyQt5'):\n"
        "        raise ImportError('blocked ' + name)\n"
        '    return real(name, *a, **k)\n'
        'builtins.__import__ = guard\n'
        'sys.path.insert(0, %r)\n' % src +
        'import ' + ', '.join(CONST_DOMAIN_MODULES) + '\n'
        "assert 'PyQt5' not in sys.modules, 'PyQt5 leaked in'\n"
        "print('OK')\n"
    )
    result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True)
    assert result.returncode == 0, f'domain import under a PyQt5 block failed:\n{result.stderr}'
    assert result.stdout.strip() == 'OK'


def test_domain_source_has_no_qt_import(project_root) -> None:
    """
    Description:
        Fails if a Qt import ever reappears in the Qt-free domains. A stronger guard
        than the import test: it catches a Qt import that happens to be lazy or
        behind a branch the import test does not reach.
    """

    for domain in ('Camera', 'Vision', 'Reporting'):
        pattern = os.path.join(project_root, 'src', domain, '**', '*.py')
        for path in glob.glob(pattern, recursive=True):
            source = open(path).read()
            assert 'import PyQt' not in source and 'from PyQt' not in source, \
                f'a Qt import reappeared in {path}'
