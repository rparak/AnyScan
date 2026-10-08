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
    thread's stack, even when the terminal output is lost, and later runs keep it. Proven on deliberate
    crashes in separate pytest runs, recording into a temporary folder, so this run is never the one
    that dies and the repository's own records are untouched.
"""
# The repository's test directory, whose conftest the separate runs load as a plugin.
#   Unit [string]
CONST_TEST_FOLDER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
# The probe tests: one that passes, one that aborts the interpreter (os.abort, as qFatal does).
#   Unit [string]
CONST_PROBE = '\n'.join(('import os', 'def test_passes():', '    pass', 'def test_dies():', '    os.abort()', ''))


def _Probe_Run(tmp_path: tp.Any, records: tp.Any, select: str, owner: tp.Optional[str] = None) -> int:
    """
    Description:
        Run the probe tests in a separate pytest process loading this conftest, its crash record in
        records, its output discarded as a lost terminal would be.

    Args:
        (1) tmp_path [Path(object)]: The test's temporary directory (the probe lives in it).
        (2) records [Path(object)]: The crash-record folder.
        (3) select [string]: The -k expression choosing the probe tests to run.
        (4) owner [string or None]: The pid of a recording parent run, making this one nested, or None.

    Returns:
        (1) parameter [int]: The run's return code (negative when a signal killed it).
    """

    tests = tmp_path / 'probe'
    tests.mkdir(exist_ok=True)
    (tests / 'test_probe.py').write_text(CONST_PROBE)
    (tests / 'pytest.ini').write_text('[pytest]\n')
    env = {key: value for key, value in os.environ.items() if key != 'ANYSCAN_CRASH_RECORD_OWNER'}
    env.update(PYTHONPATH=CONST_TEST_FOLDER, ANYSCAN_CRASH_RECORD_DIR=str(records))
    if owner is not None:
        env['ANYSCAN_CRASH_RECORD_OWNER'] = owner
    return subprocess.run([sys.executable, '-m', 'pytest', '-p', 'conftest', '-p', 'no:cacheprovider',
                           '--basetemp', str(tmp_path / 'base'), '-k', select, str(tests)],
                          cwd=str(tests), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                          timeout=120).returncode


def test_a_crashed_runs_record_names_its_test_and_outlives_later_runs(tmp_path: tp.Any) -> None:
    """
    Description:
        A run that aborts leaves a record naming the test it died in, after the one that passed before
        it, with the fatal-error dump and the aborting frame. The next run keeps it, renamed with its
        time, and starts its own; a run after that overwrites the clean record and keeps the crashed one,
        so running the suite again never deletes a crash.
    """

    records = tmp_path / 'records'
    assert _Probe_Run(tmp_path, records, 'test_passes or test_dies') < 0      # killed by SIGABRT
    assert _Probe_Run(tmp_path, records, 'test_passes') == 0
    assert _Probe_Run(tmp_path, records, 'test_passes') == 0
    (crashed,) = [name for name in os.listdir(records) if name.startswith('crash_record_')]
    record = (records / crashed).read_text()
    started = [line for line in record.splitlines() if line.startswith('START ')]
    assert started == ['START test_probe.py::test_passes', 'START test_probe.py::test_dies']
    dump = record.split('START test_probe.py::test_dies', 1)[1]
    assert 'Fatal Python error: Aborted' in dump
    assert 'test_probe.py", line 5 in test_dies' in dump
    assert (records / 'crash_record.txt').read_text().splitlines()[-1] == 'CLEAN EXIT'


def test_only_the_newest_ten_crashed_records_are_kept(tmp_path: tp.Any) -> None:
    """
    Description:
        Kept records are capped at ten, the oldest removed first: with ten kept, one more crash keeps
        the newest ten.
    """

    records = tmp_path / 'records'
    records.mkdir()
    old = ['crash_record_2026-01-%02d_00-00-00.txt' % day for day in range(1, 11)]
    for name in old:
        (records / name).write_text('START earlier\n')
    assert _Probe_Run(tmp_path, records, 'test_dies') < 0
    assert _Probe_Run(tmp_path, records, 'test_passes') == 0
    kept = sorted(name for name in os.listdir(records) if name.startswith('crash_record_'))
    assert len(kept) == 10
    assert kept[:9] == old[1:]                                   # the oldest went
    assert 'START test_probe.py::test_dies' in (records / kept[9]).read_text()


def test_a_nested_run_leaves_the_parents_record_alone(tmp_path: tp.Any) -> None:
    """
    Description:
        A pytest run started by a recording run (the suite's DPR 2 re-runs) records nothing: on the one
        fixed file it would take the running parent's unfinished record for a crash and keep it.
    """

    records = tmp_path / 'records'
    records.mkdir()
    (records / 'crash_record.txt').write_text('START the parent, still running\n')
    assert _Probe_Run(tmp_path, records, 'test_passes', owner='1') == 0
    assert sorted(os.listdir(records)) == ['crash_record.txt']
    assert (records / 'crash_record.txt').read_text() == 'START the parent, still running\n'
