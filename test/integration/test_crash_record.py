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
# File Name: ../test/integration/test_crash_record.py
## =========================================================================== ##

# System (Default)
import os
import sys
import subprocess
# Typing (Support for type hints)
import typing as tp

"""
Description:
    The suite's crash record (test/conftest.py): a fatal error at any point of a run — a segfault, a
    qFatal abort, a crash at interpreter exit — leaves on disk which test was running and every
    thread's stack, even when the terminal output is lost. Proven on a deliberate crash in a separate
    pytest process, so this run is never the one that dies.
"""
# The repository's test directory, whose conftest the separate run loads as a plugin.
#   Unit [string]
CONST_TEST_FOLDER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def test_a_fatal_error_leaves_the_test_and_every_threads_stack_on_disk(tmp_path: tp.Any) -> None:
    """
    Description:
        A test that aborts the interpreter (os.abort, as qFatal does) kills its pytest run; the crash
        record in the run's temp directory still names that test, after the one that passed before it,
        and holds the fatal-error dump with the aborting frame. The run's own output is discarded, as
        a lost terminal would be.
    """

    tests = tmp_path / 'probe'
    tests.mkdir()
    (tests / 'test_probe.py').write_text('\n'.join((
        'import os',
        'def test_passes():',
        '    pass',
        'def test_dies():',
        '    os.abort()',
        '')))
    (tests / 'pytest.ini').write_text('[pytest]\n')
    base = tmp_path / 'base'
    result = subprocess.run([sys.executable, '-m', 'pytest', '-p', 'conftest', '-p', 'no:cacheprovider',
                             '--basetemp', str(base), str(tests)],
                            cwd=str(tests), env=dict(os.environ, PYTHONPATH=CONST_TEST_FOLDER),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    assert result.returncode < 0                                   # killed by SIGABRT, no summary
    record = (base / 'crash_record.txt').read_text()
    started = [line for line in record.splitlines() if line.startswith('START ')]
    assert started == ['START test_probe.py::test_passes', 'START test_probe.py::test_dies']
    dump = record.split('START test_probe.py::test_dies', 1)[1]
    assert 'Fatal Python error: Aborted' in dump
    assert 'test_probe.py", line 5 in test_dies' in dump
