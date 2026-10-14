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
# File Name: ../test/integration/test_slow_marker.py
## =========================================================================== ##

# System (Default)
import os
# System (Default)
import sys
# System (Default)
import subprocess
# Typing (Support for type hints)
import typing as tp

"""
Description:
    The suite's slow gate (test/conftest.py, pytest_collection_modifyitems): without --runslow, a test is
    skipped exactly when it carries the slow marker. Proven in a separate pytest run loading this conftest,
    on a probe project in a folder named 'slow', since pytest's keywords also hold the names of a test's
    parents, the session's included, and the session is named after the folder the run starts in.
"""
CONST_TEST_FOLDER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
CONST_PROBE = '\n'.join(('import pytest', 'def test_plain():', '    pass', '@pytest.mark.slow',
                         'def test_marked():', '    pass', ''))


def test_only_a_slow_marked_test_is_skipped_even_in_a_folder_named_slow(tmp_path: tp.Any) -> None:
    """
    Description:
        In a project whose folder is named 'slow', a run without --runslow passes a plain test and skips
        only the one marked slow, with the gate's reason. (The gate once read 'slow' in item.keywords, which
        the folder's name satisfies, so it skipped every test there.)
    """

    probe = tmp_path / 'slow'
    probe.mkdir()
    (probe / 'test_probe.py').write_text(CONST_PROBE)
    (probe / 'pytest.ini').write_text('[pytest]\nmarkers =\n    slow: needs the model weights.\n')
    env = {key: value for key, value in os.environ.items() if key != 'ANYSCAN_CRASH_RECORD_OWNER'}
    env.update(PYTHONPATH=CONST_TEST_FOLDER, ANYSCAN_CRASH_RECORD_DIR=str(tmp_path / 'records'))
    run = subprocess.run([sys.executable, '-m', 'pytest', '-p', 'conftest', '-p', 'no:cacheprovider', '-rA',
                          '--basetemp', str(tmp_path / 'base'), str(probe)],
                         cwd=str(probe), env=env, capture_output=True, text=True, timeout=120)
    report = run.stdout + run.stderr

    assert run.returncode == 0, report[-3000:]
    assert 'PASSED test_probe.py::test_plain' in report, report[-3000:]
    assert 'SKIPPED [1] test_probe.py:4: needs the model weights; pass --runslow to run.' in report, report[-3000:]
