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
# File Name: ../test/Install/test_install.py
## =========================================================================== ##

# System (Default)
import os
import re
import sys
import shutil
import hashlib
import subprocess
# Typing (Support for type hints)
import typing as tp
# Pytest (Testing framework) [pip3 install pytest]
import pytest

"""
Description:
    Tests for install.sh. Each test sources the script in a fresh /bin/bash (bash 3.2 on
    macOS, the shell the script must run under there), calls ONE step, and inspects its log
    lines and the globals it set. The PATH is hermetic: a directory of stubs for the commands
    that describe the machine (uname, sysctl, sw_vers, getconf, nvidia-smi, curl, python,
    hf) ahead of a directory of links to the real coreutils, so a test on a Linux box with a
    real nvidia-smi still sees only the stub.

    WHAT WAS EXERCISED FOR REAL, AND WHAT ONLY WITH STUBS
    -----------------------------------------------------
    Real, on macOS 26.6.2 / Apple M2 Pro / Python 3.10.10 (2026-09-24):
      - the macOS Apple-silicon branch and the Python check against the existing .venv
        (./install.sh --detect-only); and pip's merge of requirements.txt's mlx==0.32.2 with
        a backend file's unversioned mlx[cuda12] into one mlx 0.32.2 [cuda12] (a dry-run
        resolve on macOS, where the extra's Linux-only dependencies are not resolved).
      - two full runs of ./install.sh against the existing .venv and models/: pip into .venv
        (nothing changed - 'pip freeze' identical before and after), the import check (MLX on
        Device(gpu, 0), PyTorch 2.14.0 on mps), the SHA-256 / git-blob verification of the
        real FastSAM file and all ten Gemma files (the skip path), and the check of the
        shipped configuration. The 5.1 GB hash took 3 s with macOS 26's native
        /sbin/sha256sum; the shasum fallback older macOS uses takes ~15 s on the same file.
      - the FastSAM download path end to end: Ensure_Fastsam against an empty scratch root
        fetched the v8.4.0 asset with the real curl, verified the .part file, moved it into
        place (no .part left), and a second call skipped it as present and verified.
    Real, on Linux / RTX 5070 Ti (16 GB, driver 595.91.07) / Python 3.11.16 (2026-09-29;
    design-decisions.md, "The installer on Linux: ..."):
      - detection (./install.sh --detect-only): the CUDA 13 branch, mlx[cuda13] and the cu130
        PyTorch build, 15.9 GB on GPU 0.
      - the Gemma download: Ensure_Gemma fetched E4B with the real hf and verified every file.
        Whether its --force-download re-fetch of a mismatched file ran is not recorded.
      - not the full install: that machine's environment was set up by hand, so the .venv
        creation, the pip resolves (the cu130 index, the mlx extra), the import check, the
        FastSAM step and the configuration check have not run on Linux.
    Stubs only - UNVERIFIED in the sense of README > Platform:
      - every other Linux branch (CUDA 12, the refusal and the --cpu opt-in, failing /
        missing / old nvidia-smi, low compute capability, GPU 0's memory against the 11 GB
        floor, a busy card, old glibc, musl, aarch64), macOS on Intel, macOS < 14, and
        Rosetta. The stubs reproduce the command outputs as documented (nvidia-smi's CSV
        queries and banner, sysctl, getconf). The pip resolves on the cu126 and cpu paths
        have not been performed. The Gemma download has not run on macOS (its skip path
        has); in these tests hf is a stub everywhere.
"""
# The repository root and the script under test.
#   Unit [string]
CONST_PROJECT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
CONST_INSTALL_SCRIPT = os.path.join(CONST_PROJECT_FOLDER, 'install.sh')
# The real tools the script uses besides the stubbed ones, linked into the hermetic PATH.
#   Unit [Vector<string>]
CONST_REAL_TOOLS = ['date', 'head', 'tail', 'sed', 'grep', 'cut', 'tr', 'awk', 'cat', 'wc', 'dirname', 'basename',
                    'mkdir', 'mv', 'rm', 'df', 'diff', 'mktemp', 'shasum', 'sha256sum', 'sha1sum', 'perl', 'env', 'cp',
                    'chmod', 'printf', 'sleep']
# One log line: the application's format - date, time, the level padded to 7 inside
# brackets, then the message (src/Logger/Core.py).
#   Unit [string]
CONST_LOG_LINE = re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \[(INFO   |WARNING|ERROR  )\] \S')

# nvidia-smi as a working driver reports itself: the CSV query and the banner's CUDA version.
#   Unit [string]
CONST_NVIDIA_SMI_TEMPLATE = '''case "$*" in
    *name,driver_version*) printf '%s\\n' {rows} ;;
    *compute_cap*) echo "{cap}" ;;
    *memory.total*) echo "{total}, {used}" ;;
    "") echo "| NVIDIA-SMI {driver}      Driver Version: {driver}      CUDA Version: {cuda}     |" ;;
esac'''


class Sandbox_Cls(object):
    """
    Description:
        A hermetic place to run one step of install.sh: a stub directory, a directory of links
        to the real tools, and a scratch root. Stubs are small bash scripts written per test.

    Initialization of the Class:
        Args:
            (1) root [string]: The pytest tmp_path.

        Example:
            Initialization:
                Sandbox_Cls(tmp_path)

            Features:
                # Methods
                sandbox.Stub('nvidia-smi', 'exit 9')
                sandbox.Run('Detect_Platform; Show MLX_BACKEND')
    """

    def __init__(self, root: str) -> None:
        # << PRIVATE >> #
        self.__root = str(root)
        self.__stubs = os.path.join(self.__root, 'stubs')
        self.__tools = os.path.join(self.__root, 'tools')
        os.makedirs(self.__stubs)
        os.makedirs(self.__tools)
        for tool in CONST_REAL_TOOLS:
            path = shutil.which(tool)
            if path is not None:
                os.symlink(path, os.path.join(self.__tools, tool))
        # The script under test is a COPY inside the sandbox, so its CONST_ROOT (resolved from the
        # script's own location) is the sandbox from the first line: no step can reach the real
        # repository's models/ or .venv, even in a test that forgets to override CONST_ROOT.
        self.__script = os.path.join(self.__root, 'install.sh')
        shutil.copyfile(CONST_INSTALL_SCRIPT, self.__script)

    @property
    def Root(self) -> str:
        """
        Description:
            The scratch directory tests use as CONST_ROOT and for fixtures.

        Returns:
            (1) parameter [string]: The path.
        """

        return self.__root

    def Stub(self, name: str, body: str) -> str:
        """
        Description:
            Write an executable bash stub onto the hermetic PATH.

        Args:
            (1) name [string]: The command name.
            (2) body [string]: The bash body after the shebang.

        Returns:
            (1) parameter [string]: The stub's path.
        """

        path = os.path.join(self.__stubs, name)
        with open(path, 'w') as handle:
            handle.write('#!/bin/bash\n' + body + '\n')
        os.chmod(path, 0o755)

        return path

    def Run(self, snippet: str, env: tp.Optional[tp.Dict[str, str]] = None) -> subprocess.CompletedProcess:
        """
        Description:
            Source install.sh in a fresh /bin/bash and run a snippet. 'Show VAR...' prints
            'RESULT VAR=value' lines the test can read back.

        Args:
            (1) snippet [string]: Bash to run after sourcing.
            (2) env [Dictionary<string, string>]: Extra environment variables.

        Returns:
            (1) parameter [CompletedProcess(object)]: The finished process (stdout+stderr in stdout).
        """

        script = ('source "$1"\n'
                  'Show() { local v; for v in "$@"; do eval "echo \\"RESULT $v=\\${$v}\\""; done; }\n'
                  + snippet + '\n')
        environment = {'PATH': self.__stubs + os.pathsep + self.__tools, 'HOME': self.__root,
                       'TMPDIR': self.__root, 'LC_ALL': 'C'}
        environment.update(env or {})

        return subprocess.run(['/bin/bash', '-c', script, 'test', self.__script], env=environment,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=60)


def _Results(process: subprocess.CompletedProcess) -> tp.Dict[str, str]:
    """
    Description:
        Collect the 'RESULT NAME=value' lines a snippet printed.

    Args:
        (1) process [CompletedProcess(object)]: The finished run.

    Returns:
        (1) parameter [Dictionary<string, string>]: NAME -> value.
    """

    results = {}
    for line in process.stdout.splitlines():
        if line.startswith('RESULT '):
            name, _, value = line[len('RESULT '):].partition('=')
            results[name] = value

    return results


def _Log_Lines(process: subprocess.CompletedProcess) -> tp.List[str]:
    """
    Description:
        The lines the script itself logged (everything but the RESULT lines), each asserted
        to be in the application's log format.

    Args:
        (1) process [CompletedProcess(object)]: The finished run.

    Returns:
        (1) parameter [Vector<string>]: The log lines.
    """

    lines = [line for line in process.stdout.splitlines() if not line.startswith('RESULT ')]
    for line in lines:
        assert CONST_LOG_LINE.match(line), f'not in the log format: {line!r}'

    return lines

def _Levels(process: subprocess.CompletedProcess, level: str) -> tp.List[str]:
    """
    Description:
        The messages logged at one level.

    Args:
        (1) process [CompletedProcess(object)]: The finished run.
        (2) level [string]: INFO | WARNING | ERROR.

    Returns:
        (1) parameter [Vector<string>]: The messages, without timestamp and level.
    """

    return [line[30:] for line in _Log_Lines(process) if f'[{level:<7}]' in line]


@pytest.fixture
def sandbox(tmp_path) -> Sandbox_Cls:
    """
    Description:
        A fresh hermetic sandbox per test.

    Returns:
        (1) parameter [Sandbox_Cls(object)]: The sandbox.
    """

    return Sandbox_Cls(tmp_path)


def _Stub_Macos(sandbox: Sandbox_Cls, arm64: tp.Optional[str] = '1', machine: str = 'arm64',
                version: str = '15.1') -> None:
    """
    Description:
        Stub a Mac: uname, sysctl (hw.optional.arm64 absent on Intel when arm64 is None, as on
        older Intel macOS), and sw_vers.

    Args:
        (1) sandbox [Sandbox_Cls(object)]: The sandbox.
        (2) arm64 [string]: hw.optional.arm64's value, or None for 'unknown oid'.
        (3) machine [string]: uname -m (x86_64 under Rosetta).
        (4) version [string]: The macOS version.
    """

    sandbox.Stub('uname', f'case "$1" in -s) echo Darwin ;; -m) echo {machine} ;; esac')
    arm64_case = (f'echo {arm64}' if arm64 is not None
                  else "echo \"sysctl: unknown oid 'hw.optional.arm64'\" >&2; exit 1")
    sandbox.Stub('sysctl', f'case "$2" in hw.optional.arm64) {arm64_case} ;; '
                           'machdep.cpu.brand_string) echo "Apple M2 Pro" ;; esac')
    sandbox.Stub('sw_vers', f'echo {version}')


def _Stub_Linux(sandbox: Sandbox_Cls, machine: str = 'x86_64', glibc: tp.Optional[str] = '2.35') -> None:
    """
    Description:
        Stub a Linux machine: uname and getconf (None = no glibc, as on musl).

    Args:
        (1) sandbox [Sandbox_Cls(object)]: The sandbox.
        (2) machine [string]: uname -m.
        (3) glibc [string]: The glibc version, or None.
    """

    sandbox.Stub('uname', f'case "$1" in -s) echo Linux ;; -m) echo {machine} ;; esac')
    sandbox.Stub('getconf', f'echo "glibc {glibc}"' if glibc is not None
                            else 'echo "getconf: Unrecognized variable" >&2; exit 1')


def _Stub_Nvidia(sandbox: Sandbox_Cls, driver: str, cap: str = '8.6', cuda: str = '12.6', gpus: int = 1,
                 total: str = '24576', used: str = '300', name: str = 'NVIDIA GeForce RTX 3090') -> None:
    """
    Description:
        Stub a working nvidia-smi.

    Args:
        (1) sandbox [Sandbox_Cls(object)]: The sandbox.
        (2) driver [string]: The driver version.
        (3) cap [string]: The compute capability.
        (4) cuda [string]: The CUDA version the banner reports.
        (5) gpus [int]: How many GPUs the query lists.
        (6) total [string]: GPU 0's memory.total in MiB, as nvidia-smi prints it with nounits.
        (7) used [string]: GPU 0's memory.used in MiB.
        (8) name [string]: The card's name.
    """

    rows = ' '.join([f'"{name}, {driver}"'] * gpus)
    sandbox.Stub('nvidia-smi', CONST_NVIDIA_SMI_TEMPLATE.format(rows=rows, cap=cap, driver=driver, cuda=cuda,
                                                                total=total, used=used))


# ---- version comparison -----------------------------------------------------

@pytest.mark.parametrize('a, b, expected', [
    ('3.10.10', '3.10', True), ('3.9.18', '3.10', False), ('3.13.1', '3.12.999', True), ('3.12.7', '3.12.999', False),
    ('550.54.14', '550.54.14', True), ('550.54.13', '550.54.14', False), ('550.127.05', '550.54.14', True),
    ('535.183.01', '550.54.14', False), ('580.65.06', '580', True), ('575.57.08', '580', False),
    ('7.5', '7.5', True), ('7.0', '7.5', False), ('12.0', '7.5', True), ('2.31', '2.35', False),
    ('2.39', '2.35', True), ('14', '14', True), ('13.6.1', '14', False), ('3.10.0rc1', '3.10', True)])
def test_version_ge(sandbox, a, b, expected):
    process = sandbox.Run(f'if Version_Ge "{a}" "{b}"; then echo "RESULT GE=yes"; else echo "RESULT GE=no"; fi')

    assert _Results(process)['GE'] == ('yes' if expected else 'no')


# ---- Python version check ---------------------------------------------------

def _Stub_Python(sandbox: Sandbox_Cls, name: str, version: str, machine: str = 'arm64') -> str:
    """
    Description:
        Stub an interpreter that answers the version and platform.machine() queries.

    Args:
        (1) sandbox [Sandbox_Cls(object)]: The sandbox.
        (2) name [string]: The command name (python3, python3.12, ...).
        (3) version [string]: What it reports as its version.
        (4) machine [string]: What it reports as platform.machine().

    Returns:
        (1) parameter [string]: The stub's path.
    """

    return sandbox.Stub(name, f'case "$*" in *machine*) echo {machine} ;; *) echo {version} ;; esac')


def test_python_below_floor_stops_first_and_names_both_versions(sandbox):
    _Stub_Python(sandbox, 'python3', '3.9.18')
    process = sandbox.Run(f'CONST_VENV_DIR="{sandbox.Root}/venv"; Select_Python; echo "RESULT REACHED=yes"')

    assert process.returncode == 1
    assert 'REACHED' not in _Results(process)
    errors = _Levels(process, 'ERROR')
    assert 'Python 3.10 or newer is required; found python3 3.9.18.' in errors[0]
    assert 'PYTHON=' in errors[-1]


def test_python_search_prefers_a_suitable_versioned_interpreter(sandbox):
    _Stub_Python(sandbox, 'python3', '3.9.18')
    _Stub_Python(sandbox, 'python3.11', '3.11.9')
    process = sandbox.Run(f'CONST_VENV_DIR="{sandbox.Root}/venv"; Select_Python; Show PYTHON_VERSION')

    assert process.returncode == 0
    assert _Results(process)['PYTHON_VERSION'] == '3.11.9'
    assert any('within the accepted range: 3.10 or newer, tested 3.10-3.12' in m for m in _Levels(process, 'INFO'))


def test_python_above_tested_range_is_accepted_with_an_informative_warning(sandbox):
    _Stub_Python(sandbox, 'python3.13', '3.13.1')
    process = sandbox.Run(f'CONST_VENV_DIR="{sandbox.Root}/venv"; Select_Python; Show PYTHON_VERSION')

    assert process.returncode == 0
    warning = _Levels(process, 'WARNING')[0]
    assert 'Python 3.13.1 is accepted (the floor is 3.10)' in warning
    assert 'newer than the tested range 3.10-3.12' in warning


def test_python_from_environment_variable_below_floor(sandbox):
    path = _Stub_Python(sandbox, 'oldpython', '3.8.20')
    process = sandbox.Run(f'CONST_VENV_DIR="{sandbox.Root}/venv"; Select_Python', env={'PYTHON': path})

    assert process.returncode == 1
    assert 'PYTHON=' in _Levels(process, 'ERROR')[0] and '3.8.20' in _Levels(process, 'ERROR')[0]


def test_existing_venv_decides_and_an_old_one_is_not_deleted(sandbox):
    venv = os.path.join(sandbox.Root, 'venv')
    os.makedirs(os.path.join(venv, 'bin'))
    sandbox.Stub('python-old', 'echo 3.9.6')
    os.rename(os.path.join(sandbox.Root, 'stubs', 'python-old'), os.path.join(venv, 'bin', 'python'))
    process = sandbox.Run(f'CONST_VENV_DIR="{venv}"; Select_Python')

    assert process.returncode == 1
    assert 'rm -rf .venv' in _Levels(process, 'ERROR')[-1]
    assert os.path.exists(os.path.join(venv, 'bin', 'python'))


def test_x86_64_python_on_apple_silicon_stops(sandbox):
    path = _Stub_Python(sandbox, 'python3', '3.10.14', machine='x86_64')
    process = sandbox.Run(f'PLATFORM_OS=macos; BASE_PYTHON="{path}"; PYTHON_VERSION=3.10.14; Check_Python_Architecture')

    assert process.returncode == 1
    assert 'Rosetta' in _Levels(process, 'ERROR')[0]


# ---- platform detection: macOS ----------------------------------------------

def test_macos_apple_silicon_selects_metal(sandbox):
    _Stub_Macos(sandbox)
    process = sandbox.Run('Detect_Platform; Show PLATFORM_OS MLX_BACKEND TORCH_INDEX')

    assert process.returncode == 0
    assert _Results(process) == {'PLATFORM_OS': 'macos', 'MLX_BACKEND': 'metal', 'TORCH_INDEX': ''}
    assert 'Detected macOS 15.1 on Apple silicon (Apple M2 Pro).' in _Levels(process, 'INFO')


def test_macos_under_rosetta_is_still_apple_silicon(sandbox):
    _Stub_Macos(sandbox, machine='x86_64')
    process = sandbox.Run('Detect_Platform; Show MLX_BACKEND')

    assert _Results(process)['MLX_BACKEND'] == 'metal'


@pytest.mark.parametrize('arm64', ['0', None])
def test_macos_intel_is_unsupported(sandbox, arm64):
    _Stub_Macos(sandbox, arm64=arm64, machine='x86_64')
    process = sandbox.Run('Detect_Platform; echo "RESULT REACHED=yes"')

    assert process.returncode == 1
    assert 'REACHED' not in _Results(process)
    assert 'Intel processor, which is unsupported' in _Levels(process, 'ERROR')[0]
    assert 'MLX needs Apple silicon' in _Levels(process, 'ERROR')[0]


def test_macos_older_than_14_stops(sandbox):
    _Stub_Macos(sandbox, version='13.6.1')
    process = sandbox.Run('Detect_Platform')

    assert process.returncode == 1
    assert 'macOS 14 or newer is required; this is 13.6.1' in _Levels(process, 'ERROR')[0]


# ---- platform detection: Linux ----------------------------------------------

@pytest.mark.parametrize('driver, cuda, backend, index', [
    ('560.35.03', '12.6', 'cuda12', 'cu126'),
    ('550.54.14', '12.4', 'cuda12', 'cu126'),
    ('575.57.08', '12.9', 'cuda12', 'cu126'),
    ('580.65.06', '13.0', 'cuda13', 'cu130'),
    ('590.44.01', '13.1', 'cuda13', 'cu130')])
def test_linux_nvidia_driver_selects_matching_builds(sandbox, driver, cuda, backend, index):
    _Stub_Linux(sandbox)
    _Stub_Nvidia(sandbox, driver, cuda=cuda)
    process = sandbox.Run('Detect_Platform; Show MLX_BACKEND TORCH_INDEX')

    assert process.returncode == 0
    assert _Results(process) == {'MLX_BACKEND': backend, 'TORCH_INDEX': index}
    infos = _Levels(process, 'INFO')
    assert f'Detected NVIDIA driver {driver} (CUDA {cuda}) on NVIDIA GeForce RTX 3090.' in infos
    assert any(f'mlx[{backend}]' in m and index in m for m in infos)
    assert not _Levels(process, 'WARNING')


def test_linux_multiple_gpus_reports_the_count(sandbox):
    _Stub_Linux(sandbox)
    _Stub_Nvidia(sandbox, '560.35.03', gpus=2)
    process = sandbox.Run('Detect_Platform')

    assert any('with 2 GPUs; MLX uses the first' in m for m in _Levels(process, 'INFO'))


def _No_Driver(sandbox: Sandbox_Cls) -> None:
    """
    Description:
        No nvidia-smi at all (the hermetic PATH has none).
    """


def _Driver_Unreachable(sandbox: Sandbox_Cls) -> None:
    """
    Description:
        The case the driver check exists for: nvidia-smi is present but cannot reach a driver.
    """

    sandbox.Stub('nvidia-smi', 'echo "NVIDIA-SMI has failed because it couldn\'t communicate with the NVIDIA driver. '
                               'Make sure that the latest NVIDIA driver is installed and running."; exit 9')


def _No_Devices(sandbox: Sandbox_Cls) -> None:
    """
    Description:
        nvidia-smi runs but lists no GPU.
    """

    sandbox.Stub('nvidia-smi', 'echo "No devices were found"; exit 0')


# Every way a Linux machine can lack a usable GPU, with the reason the installer must name.
#   Unit [Vector<Tuple>]
CONST_NO_USABLE_GPU = [
    (_No_Driver, 'No NVIDIA driver found (nvidia-smi is not installed)'),
    (_Driver_Unreachable, "nvidia-smi is installed but failed (NVIDIA-SMI has failed because it couldn't communicate"),
    (_No_Devices, 'nvidia-smi reported no GPU (No devices were found)'),
    (lambda sandbox: _Stub_Nvidia(sandbox, '535.183.01', cuda='12.2'), 'older than 550.54.14'),
    (lambda sandbox: _Stub_Nvidia(sandbox, '560.35.03', cap='7.0'), 'compute capability 7.0'),
    (lambda sandbox: _Stub_Nvidia(sandbox, '560.35.03', total='8188', name='NVIDIA GeForce RTX 4060'),
     'NVIDIA GeForce RTX 4060 has 8.0 GB of memory'),
    (lambda sandbox: _Stub_Nvidia(sandbox, '560.35.03', total='[N/A]'), "did not report NVIDIA GeForce RTX 3090's memory")]


@pytest.mark.parametrize('setup, reason', CONST_NO_USABLE_GPU)
def test_linux_without_a_usable_gpu_stops_naming_the_reason_and_the_cpu_flag(sandbox, setup, reason):
    """
    Description:
        No silent CPU fallback: an install that succeeds and then runs unusably slowly is worse
        than a refusal that says why and how to opt in.
    """

    _Stub_Linux(sandbox)
    setup(sandbox)
    process = sandbox.Run('Detect_Platform; Show MLX_BACKEND')

    assert process.returncode == 1
    assert 'RESULT' not in process.stdout
    errors = _Levels(process, 'ERROR')
    assert reason in errors[0]
    assert 'at least 11 GB of memory' in errors[0]
    assert any('re-run with --cpu' in m for m in errors)


@pytest.mark.parametrize('setup, reason', CONST_NO_USABLE_GPU)
def test_linux_cpu_flag_takes_the_cpu_path_with_the_reason(sandbox, setup, reason):
    _Stub_Linux(sandbox)
    setup(sandbox)
    process = sandbox.Run('CPU_OPT_IN=1; Detect_Platform; Show MLX_BACKEND TORCH_INDEX')

    assert process.returncode == 0
    assert _Results(process) == {'MLX_BACKEND': 'cpu', 'TORCH_INDEX': 'cpu'}
    warning = _Levels(process, 'WARNING')[-1]
    assert reason in warning and 'as --cpu asks' in warning and 'slow' in warning


def test_linux_small_card_refusal_names_card_memory_and_minimum(sandbox):
    _Stub_Linux(sandbox)
    _Stub_Nvidia(sandbox, '560.35.03', total='8188', name='NVIDIA GeForce RTX 4060')
    process = sandbox.Run('Detect_Platform')

    error = _Levels(process, 'ERROR')[0]
    assert 'NVIDIA GeForce RTX 4060 has 8.0 GB of memory' in error
    assert '11264 MiB (11 GB) is the minimum' in error


@pytest.mark.parametrize('total, name', [('12282', 'NVIDIA GeForce RTX 4070'), ('16303', 'NVIDIA GeForce RTX 5070 Ti'),
                                         ('11264', 'NVIDIA GeForce RTX 2080 Ti')])
def test_linux_card_with_enough_memory_takes_the_gpu_path(sandbox, total, name):
    _Stub_Linux(sandbox)
    _Stub_Nvidia(sandbox, '580.65.06', cuda='13.0', total=total, cap='7.5', name=name)
    process = sandbox.Run('Detect_Platform; Show MLX_BACKEND GPU_MEMORY_MIB')

    assert process.returncode == 0
    assert _Results(process) == {'MLX_BACKEND': 'cuda13', 'GPU_MEMORY_MIB': total}
    assert any(m.startswith(f'{name} has ') and f'({total} MiB)' in m for m in _Levels(process, 'INFO'))
    assert not _Levels(process, 'WARNING')


def test_linux_busy_card_warns_with_the_memory_in_use(sandbox):
    _Stub_Linux(sandbox)
    _Stub_Nvidia(sandbox, '560.35.03', total='16303', used='3100')
    process = sandbox.Run('Detect_Platform; Show MLX_BACKEND')

    assert _Results(process)['MLX_BACKEND'] == 'cuda12'
    assert 'already has 3.0 GB in use' in _Levels(process, 'WARNING')[0]


def test_linux_cpu_flag_with_a_usable_gpu_installs_the_gpu_builds(sandbox):
    _Stub_Linux(sandbox)
    _Stub_Nvidia(sandbox, '560.35.03')
    process = sandbox.Run('CPU_OPT_IN=1; Detect_Platform; Show MLX_BACKEND')

    assert _Results(process)['MLX_BACKEND'] == 'cuda12'
    assert any(m.startswith('--cpu was given but has no effect here') for m in _Levels(process, 'WARNING'))


def test_linux_aarch64_stops_naming_pyqt5_and_what_would_be_needed(sandbox):
    _Stub_Linux(sandbox, machine='aarch64')
    process = sandbox.Run('Detect_Platform')

    assert process.returncode == 1
    errors = _Levels(process, 'ERROR')
    assert 'PyQt5 5.15.11' in errors[0] and 'no Linux aarch64 wheel' in errors[0]
    assert 'python3-pyqt5' in errors[1] and 'PyQt6' in errors[1]


def test_linux_old_glibc_stops(sandbox):
    _Stub_Linux(sandbox, glibc='2.31')
    process = sandbox.Run('Detect_Platform')

    assert process.returncode == 1
    assert 'glibc 2.35 or newer is required; this system has 2.31' in _Levels(process, 'ERROR')[0]


def test_linux_musl_stops(sandbox):
    _Stub_Linux(sandbox, glibc=None)
    process = sandbox.Run('Detect_Platform')

    assert process.returncode == 1
    assert 'without glibc' in _Levels(process, 'ERROR')[0]


# ---- skip-if-present and verification ---------------------------------------

def _Blob_Sha1(content: bytes) -> str:
    """
    Description:
        The git blob SHA-1 of some content, as Hugging Face publishes it for small files.

    Args:
        (1) content [bytes]: The file content.

    Returns:
        (1) parameter [string]: The hex digest.
    """

    return hashlib.sha1(b'blob %d\0' % len(content) + content).hexdigest()


def _Write(path: str, content: bytes) -> None:
    """
    Description:
        Write a fixture file, creating its directory.

    Args:
        (1) path [string]: The file.
        (2) content [bytes]: Its content.
    """

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as handle:
        handle.write(content)


@pytest.mark.parametrize('content, kind, expected', [
    (b'weights', 'sha256', 0), (b'weightz', 'sha256', 3), (b'weight', 'sha256', 2), (None, 'sha256', 1),
    (b'{"a": 1}\n', 'blob', 0), (b'{"a": 2}\n', 'blob', 3)])
def test_verify_file_statuses(sandbox, content, kind, expected):
    reference = b'weights' if kind == 'sha256' else b'{"a": 1}\n'
    digest = hashlib.sha256(reference).hexdigest() if kind == 'sha256' else _Blob_Sha1(reference)
    path = os.path.join(sandbox.Root, 'file.bin')
    if content is not None:
        _Write(path, content)
    process = sandbox.Run(f'status=0; Verify_File "{path}" {len(reference)} {kind} {digest} || status=$?; Show status')

    assert _Results(process)['status'] == str(expected)


def test_blob_hash_matches_git(sandbox):
    if shutil.which('git') is None:
        pytest.skip('git is not installed')
    path = os.path.join(sandbox.Root, 'config.json')
    _Write(path, b'{"model_type": "gemma4"}\n')
    process = sandbox.Run(f'echo "RESULT HASH=$(Hash_Git_Blob "{path}" 25)"')
    expected = subprocess.run(['git', 'hash-object', path], stdout=subprocess.PIPE, universal_newlines=True).stdout.strip()

    assert _Results(process)['HASH'] == expected


def _Fastsam_Snippet(sandbox: Sandbox_Cls, reference: bytes) -> str:
    """
    Description:
        Point the FastSAM constants at a scratch root and a fixture checksum.

    Args:
        (1) sandbox [Sandbox_Cls(object)]: The sandbox.
        (2) reference [bytes]: The content the 'published' checksum is of.

    Returns:
        (1) parameter [string]: The bash assignments.
    """

    return (f'CONST_ROOT="{sandbox.Root}"; CONST_FASTSAM_URL=https://example.invalid/FastSAM-x.pt; '
            f'CONST_FASTSAM_SIZE={len(reference)}; CONST_FASTSAM_SHA256={hashlib.sha256(reference).hexdigest()}; ')


def _Stub_Curl(sandbox: Sandbox_Cls, serves: bytes) -> str:
    """
    Description:
        A curl that records its arguments and writes the given content to --output.

    Args:
        (1) sandbox [Sandbox_Cls(object)]: The sandbox.
        (2) serves [bytes]: The content 'downloaded'.

    Returns:
        (1) parameter [string]: The file the call is recorded in.
    """

    record = os.path.join(sandbox.Root, 'curl.calls')
    served = os.path.join(sandbox.Root, 'served.bin')
    _Write(served, serves)
    sandbox.Stub('curl', f'echo "$*" >> "{record}"\n'
                         'while [ "$#" -gt 0 ]; do [ "$1" = --output ] && out="$2"; shift; done\n'
                         f'cp "{served}" "$out"')

    return record


def test_fastsam_present_and_correct_is_not_downloaded(sandbox):
    reference = b'fastsam-weights'
    _Write(os.path.join(sandbox.Root, 'models', 'FastSAM', 'FastSAM-x.pt'), reference)
    record = _Stub_Curl(sandbox, reference)
    process = sandbox.Run(_Fastsam_Snippet(sandbox, reference) + 'Ensure_Fastsam')

    assert process.returncode == 0
    assert not os.path.exists(record)
    assert any('already present and matches the published SHA-256' in m for m in _Levels(process, 'INFO'))


def test_fastsam_corrupt_is_downloaded_again_and_verified(sandbox):
    reference = b'fastsam-weights'
    target = os.path.join(sandbox.Root, 'models', 'FastSAM', 'FastSAM-x.pt')
    _Write(target, b'fastsam-weightz')
    record = _Stub_Curl(sandbox, reference)
    process = sandbox.Run(_Fastsam_Snippet(sandbox, reference) + 'Ensure_Fastsam')

    assert process.returncode == 0
    assert 'https://example.invalid/FastSAM-x.pt' in open(record).read()
    assert open(target, 'rb').read() == reference
    assert not os.path.exists(target + '.part')
    assert 'checksum does not match' in _Levels(process, 'WARNING')[0]


def test_fastsam_bad_download_replaces_nothing(sandbox):
    reference = b'fastsam-weights'
    target = os.path.join(sandbox.Root, 'models', 'FastSAM', 'FastSAM-x.pt')
    _Write(target, b'fastsam-old!!!!')
    _Stub_Curl(sandbox, b'<html>rate limited</html>')
    process = sandbox.Run(_Fastsam_Snippet(sandbox, reference) + 'Ensure_Fastsam')

    assert process.returncode == 1
    assert open(target, 'rb').read() == b'fastsam-old!!!!'
    assert not os.path.exists(target + '.part')
    assert 'nothing was replaced' in _Levels(process, 'ERROR')[0]


# The Gemma fixture: three small files standing in for the ten published ones, one of them
# over the (lowered) slow-hash threshold so the elapsed-time lines are exercised.
#   Unit [Dictionary<string, bytes>]
CONST_GEMMA_FIXTURE = {'config.json': b'{"model_type": "gemma4"}\n',
                       'model.safetensors': b'x' * 4096,
                       'tokenizer.json': b'{"version": "1.0"}\n'}


def _Gemma_Snippet(sandbox: Sandbox_Cls) -> str:
    """
    Description:
        Point the Gemma constants at a scratch root, a fixture manifest and a stub venv.

    Args:
        (1) sandbox [Sandbox_Cls(object)]: The sandbox.

    Returns:
        (1) parameter [string]: The bash assignments.
    """

    rows = []
    for name, content in CONST_GEMMA_FIXTURE.items():
        if name == 'model.safetensors':
            rows.append(f'{name} {len(content)} sha256 {hashlib.sha256(content).hexdigest()}')
        else:
            rows.append(f'{name} {len(content)} blob {_Blob_Sha1(content)}')
    manifest = '\n'.join(rows)

    return (f'CONST_ROOT="{sandbox.Root}"; CONST_VENV_DIR="{sandbox.Root}/venv"; CONST_SLOW_HASH_BYTES=1024; '
            f"CONST_GEMMA_FILES='{manifest}'; ")


def _Stub_Hf(sandbox: Sandbox_Cls, correct: bool = True) -> str:
    """
    Description:
        A .venv/bin/hf that records its arguments and writes the fixture content (or wrong
        content) for each file named on its command line into --local-dir.

    Args:
        (1) sandbox [Sandbox_Cls(object)]: The sandbox.
        (2) correct [bool]: Whether it 'downloads' the right bytes.

    Returns:
        (1) parameter [string]: The file the call is recorded in.
    """

    record = os.path.join(sandbox.Root, 'hf.calls')
    fixtures = os.path.join(sandbox.Root, 'hf-fixtures')
    for name, content in CONST_GEMMA_FIXTURE.items():
        _Write(os.path.join(fixtures, name), content if correct else content + b'!')
    path = sandbox.Stub('hf', f'echo "$*" >> "{record}"\n'
                              'names=""; while [ "$#" -gt 0 ]; do case "$1" in\n'
                              '  --local-dir) dir="$2"; shift ;; --revision) shift ;; --*|download) ;;\n'
                              '  */*) ;; *) names="$names $1" ;; esac; shift; done\n'
                              f'for n in $names; do cp "{fixtures}/$n" "$dir/$n"; done')
    os.makedirs(os.path.join(sandbox.Root, 'venv', 'bin'))
    os.rename(path, os.path.join(sandbox.Root, 'venv', 'bin', 'hf'))

    return record


def test_gemma_present_and_correct_is_not_downloaded_and_reports_time(sandbox):
    for name, content in CONST_GEMMA_FIXTURE.items():
        _Write(os.path.join(sandbox.Root, 'models', 'gemma-4-e4b-it-4bit', name), content)
    record = _Stub_Hf(sandbox)
    process = sandbox.Run(_Gemma_Snippet(sandbox) + 'Ensure_Gemma')

    assert process.returncode == 0
    assert not os.path.exists(record)
    infos = _Levels(process, 'INFO')
    assert any(m.startswith('Hashing model.safetensors') for m in infos)
    assert any(re.match(r'Hashed model\.safetensors in \d+ s\.', m) for m in infos)
    assert any(re.search(r'already present and every file matches the published hashes \(checked in \d+ s\)', m)
               for m in infos)


def test_gemma_fetches_only_the_mismatched_file(sandbox):
    directory = os.path.join(sandbox.Root, 'models', 'gemma-4-e4b-it-4bit')
    for name, content in CONST_GEMMA_FIXTURE.items():
        _Write(os.path.join(directory, name), content)
    _Write(os.path.join(directory, 'tokenizer.json'), b'{"version": "0.9"}\n')
    record = _Stub_Hf(sandbox)
    process = sandbox.Run(_Gemma_Snippet(sandbox) + 'Ensure_Gemma')

    assert process.returncode == 0
    call = open(record).read().split()
    assert 'tokenizer.json' in call and 'config.json' not in call and 'model.safetensors' not in call
    assert '--force-download' in call and '--revision' in call
    assert open(os.path.join(directory, 'tokenizer.json'), 'rb').read() == CONST_GEMMA_FIXTURE['tokenizer.json']
    assert 'Gemma file tokenizer.json is present but its checksum does not match' in _Levels(process, 'WARNING')[0]


def test_gemma_missing_directory_fetches_everything(sandbox):
    record = _Stub_Hf(sandbox)
    process = sandbox.Run(_Gemma_Snippet(sandbox) + 'Ensure_Gemma')

    assert process.returncode == 0
    call = open(record).read().split()
    assert all(name in call for name in CONST_GEMMA_FIXTURE)
    assert not _Levels(process, 'WARNING')


def test_gemma_download_that_does_not_verify_fails(sandbox):
    _Stub_Hf(sandbox, correct=False)
    process = sandbox.Run(_Gemma_Snippet(sandbox) + 'Ensure_Gemma')

    assert process.returncode == 1
    assert 'After downloading, Gemma file' in _Levels(process, 'ERROR')[0]


def _Dinov2_Snippet(sandbox: Sandbox_Cls) -> str:
    """
    Description:
        Point the DINOv2 manifest at the same fixture files the Gemma tests use, in a scratch root.

    Args:
        (1) sandbox [Sandbox_Cls(object)]: The sandbox.

    Returns:
        (1) parameter [string]: The bash assignments.
    """

    return _Gemma_Snippet(sandbox).replace('CONST_GEMMA_FILES=', 'CONST_DINOV2_FILES=')


def test_dinov2_missing_is_fetched_at_its_pinned_revision_and_verified(sandbox):
    """
    Description:
        DINOv2 goes through the same verified download as Gemma: every listed file is fetched from
        facebook/dinov2-base at the pinned revision into models/dinov2-base, then verified.
    """

    record = _Stub_Hf(sandbox)
    process = sandbox.Run(_Dinov2_Snippet(sandbox) + 'Ensure_Dinov2')

    assert process.returncode == 0
    call = open(record).read().split()
    assert call[:2] == ['download', 'facebook/dinov2-base']
    assert call[call.index('--revision') + 1] == 'f9e44c814b77203eaa57a6bdbbd535f21ede1415'
    assert call[call.index('--local-dir') + 1] == os.path.join(sandbox.Root, 'models', 'dinov2-base')
    assert all(name in call for name in CONST_GEMMA_FIXTURE)
    assert any(m.startswith('DINOv2 base downloaded and every file verified') for m in _Levels(process, 'INFO'))


def test_dinov2_present_and_correct_is_not_downloaded(sandbox):
    for name, content in CONST_GEMMA_FIXTURE.items():
        _Write(os.path.join(sandbox.Root, 'models', 'dinov2-base', name), content)
    record = _Stub_Hf(sandbox)
    process = sandbox.Run(_Dinov2_Snippet(sandbox) + 'Ensure_Dinov2')

    assert process.returncode == 0 and not os.path.exists(record)
    assert any('DINOv2 base is already present and every file matches the published hashes' in m
               for m in _Levels(process, 'INFO'))


def test_dinov2_download_that_does_not_verify_fails(sandbox):
    _Stub_Hf(sandbox, correct=False)
    process = sandbox.Run(_Dinov2_Snippet(sandbox) + 'Ensure_Dinov2')

    assert process.returncode == 1
    assert 'After downloading, DINOv2 file' in _Levels(process, 'ERROR')[0]


@pytest.mark.parametrize('arguments, cpu', [('', '0'), ('--cpu', '1')])
def test_arguments_set_the_cpu_opt_in(sandbox, arguments, cpu):
    process = sandbox.Run(f'Parse_Arguments {arguments}; Show CPU_OPT_IN')

    assert _Results(process) == {'CPU_OPT_IN': cpu}


@pytest.mark.parametrize('arguments', ['--model 12b', '--model=e4b'])
def test_the_removed_model_option_is_refused(sandbox, arguments):
    """
    Description:
        The installer has one describer model; --model is no longer an option and stops as unknown.
    """

    process = sandbox.Run(f'Parse_Arguments {arguments}')

    assert process.returncode == 1
    assert _Levels(process, 'ERROR')[0].startswith("Unknown argument '--model")


def test_the_plan_names_e4b_and_warns_of_nothing(sandbox):
    process = sandbox.Run('PYTHON_VERSION=3.10.14; MLX_BACKEND=metal; Report_Plan')

    assert any('Gemma 4 E4B, mlx-community/gemma-4-e4b-it-4bit@475b908 -> models/gemma-4-e4b-it-4bit (5.2 GB)' in m
               for m in _Levels(process, 'INFO'))
    assert any('DINOv2 base, facebook/dinov2-base@f9e44c8 -> models/dinov2-base (346 MB)' in m
               for m in _Levels(process, 'INFO'))
    assert not _Levels(process, 'WARNING')


def test_cpu_with_a_usable_gpu_is_reported_again_at_the_end(sandbox):
    """
    Description:
        --cpu passed on purpose (testing, a driver workaround) that did not take effect is said at
        detection and again as the last warning, so it cannot pass unnoticed in a long run.
    """

    _Stub_Linux(sandbox)
    _Stub_Nvidia(sandbox, '580.65.06', cuda='13.0')
    process = sandbox.Run('CPU_OPT_IN=1; Detect_Platform; Report_Unused_Cpu_Flag')

    assert _Levels(process, 'WARNING')[0].startswith('--cpu was given but has no effect here')
    assert _Levels(process, 'WARNING')[-1:] == ['--cpu had no effect: the cuda13 GPU builds were installed.']
    quiet = sandbox.Run('CPU_OPT_IN=1; PLATFORM_OS=linux; MLX_BACKEND=cpu; Report_Unused_Cpu_Flag')
    assert not _Levels(quiet, 'WARNING')


# ---- OpenCV: the headless build only ----------------------------------------

# A .venv/bin/python that plays pip and the two Python checks Ensure_Headless_Opencv runs, over a state
# directory: a file per installed OpenCV build holding its version, 'plugins' when cv2/qt/plugins exists,
# 'broken' when cv2 does not import. 'sticky' keeps the plugins through an uninstall and a reinstall,
# 'stays_broken' keeps cv2 broken through the reinstall. Every pip call is appended to 'calls'.
CONST_OPENCV_PYTHON_STUB = '''state="{state}"
if [ "$1" = -m ] && [ "$2" = pip ]; then
    echo "${{*:3}}" | sed 's/ --disable-pip-version-check --quiet//' >> "$state/calls"
    case "$3" in
        uninstall)
            rm -f "$state/opencv-python"; : > "$state/broken"
            [ -e "$state/sticky" ] || rm -f "$state/plugins" ;;
        install)
            pin="${{*: -3:1}}"; echo "${{pin#opencv-python-headless==}}" > "$state/opencv-python-headless"
            [ -e "$state/stays_broken" ] || rm -f "$state/broken" ;;
    esac
    exit 0
fi
case "$2" in
    *importlib.metadata*) cat "$state/$3" 2>/dev/null; exit 0 ;;
    *"import cv2"*)
        if [ -e "$state/broken" ]; then echo "import No module named 'cv2'"
        elif [ -e "$state/plugins" ]; then echo "plugins /venv/site-packages/cv2/qt/plugins"
        else echo ok; fi ;;
esac'''


def _Opencv_Venv(sandbox: Sandbox_Cls, *state: str, gui: str = '', headless: str = '5.0.0.93') -> str:
    """
    Description:
        A stub .venv whose OpenCV is in the given state, and a requirements.txt pinning the headless build.

    Args:
        (1) sandbox [Sandbox_Cls(object)]: The sandbox.
        (2) state [Vector<string>]: Flags set: 'plugins', 'broken', 'sticky', 'stays_broken'.
        (3) gui, headless [string]: The installed versions of opencv-python and opencv-python-headless ('' none).

    Returns:
        (1) parameter [string]: The snippet that points the script at the stub .venv and the requirements.
    """

    folder = os.path.join(sandbox.Root, 'opencv')
    os.makedirs(folder)
    for flag in state:
        _Write(os.path.join(folder, flag), b'')
    for name, version in (('opencv-python', gui), ('opencv-python-headless', headless)):
        if version:
            _Write(os.path.join(folder, name), version.encode() + b'\n')
    path = sandbox.Stub('venv-python', CONST_OPENCV_PYTHON_STUB.format(state=folder))
    os.makedirs(os.path.join(sandbox.Root, 'venv', 'bin'))
    os.rename(path, os.path.join(sandbox.Root, 'venv', 'bin', 'python'))
    _Write(os.path.join(sandbox.Root, 'requirements.txt'), b'PyQt5>=5.15\nopencv-python-headless==5.0.0.93\nnumpy>=2.2\n')

    return f'CONST_VENV_DIR="{sandbox.Root}/venv"; CONST_REQUIREMENTS="{sandbox.Root}/requirements.txt"; '


def _Pip_Calls(sandbox: Sandbox_Cls) -> tp.List[str]:
    """The pip commands the stub .venv ran, in order."""
    path = os.path.join(sandbox.Root, 'opencv', 'calls')
    return open(path).read().splitlines() if os.path.exists(path) else []


def test_the_gui_opencv_is_removed_and_the_headless_pin_reinstalled_whole(sandbox):
    """
    Description:
        The station's state after a requirements install: opencv-python beside opencv-python-headless, its Qt
        plugins in cv2's folder. It is uninstalled, which also deletes the files the two share, and the
        headless build is reinstalled at its pin, whole and without its dependencies; then cv2 imports and
        holds no Qt plugins, and the step says so.
    """

    setup = _Opencv_Venv(sandbox, 'plugins', gui='5.0.0.93')
    process = sandbox.Run(setup + 'Ensure_Headless_Opencv')

    assert process.returncode == 0, process.stdout
    assert _Pip_Calls(sandbox) == ['uninstall --yes opencv-python',
                                   'install --force-reinstall --no-deps opencv-python-headless==5.0.0.93']
    assert _Levels(process, 'INFO')[0].startswith('Removing opencv-python 5.0.0.93')
    assert _Levels(process, 'INFO')[-1] == ('OpenCV: opencv-python-headless 5.0.0.93 only; cv2 imports and carries '
                                            'no Qt plugins.')


def test_the_headless_opencv_step_is_idempotent(sandbox):
    """
    Description:
        A second run finds the pinned headless build alone and cv2 intact, and installs nothing; a headless
        build that lost its files (cv2 does not import) is reinstalled, without anything to uninstall.
    """

    setup = _Opencv_Venv(sandbox)
    process = sandbox.Run(setup + 'Ensure_Headless_Opencv; Ensure_Headless_Opencv')
    assert process.returncode == 0 and _Pip_Calls(sandbox) == []
    assert len(_Levels(process, 'INFO')) == 2

    _Write(os.path.join(sandbox.Root, 'opencv', 'broken'), b'')
    process = sandbox.Run(setup + 'Ensure_Headless_Opencv')
    assert process.returncode == 0
    assert _Pip_Calls(sandbox) == ['install --force-reinstall --no-deps opencv-python-headless==5.0.0.93']


@pytest.mark.parametrize('state, words', [
    (('plugins', 'sticky'), 'cv2 still carries Qt plugins (/venv/site-packages/cv2/qt/plugins)'),
    (('stays_broken',), "cv2 does not import after reinstalling opencv-python-headless 5.0.0.93: No module named 'cv2'"),
], ids=['plugins left', 'cv2 broken'])
def test_the_headless_opencv_step_stops_when_cv2_is_still_wrong(sandbox, state, words):
    """
    Description:
        After the swap cv2 must import and hold no Qt plugins; otherwise the install stops with an ERROR
        naming what is wrong and the commands that fix it inside .venv.
    """

    setup = _Opencv_Venv(sandbox, *state, gui='5.0.0.93')
    process = sandbox.Run(setup + 'Ensure_Headless_Opencv; echo "RESULT REACHED=yes"')

    assert process.returncode == 1 and 'REACHED' not in _Results(process)
    errors = _Levels(process, 'ERROR')
    assert errors[0].startswith(words)
    assert 'python -m pip install --force-reinstall --no-deps opencv-python-headless==5.0.0.93' in errors[-1]


@pytest.mark.parametrize('package, expected', [
    ('', 'ok'),
    ('plugins', 'plugins {site}/cv2/qt/plugins'),
    ('raises', 'import libGL.so.1: cannot open shared object file'),
], ids=['clean', 'qt plugins', 'import fails'])
def test_the_cv2_check_imports_cv2_and_looks_for_its_qt_plugins(sandbox, package, expected):
    """
    Description:
        Opencv_Status's own Python, run by a real interpreter against a cv2 package: one that imports and has no
        cv2/qt/plugins is 'ok'; one with that folder names it; one whose import fails gives the error's first line.
    """

    site = os.path.join(sandbox.Root, 'site')
    os.makedirs(os.path.join(site, 'cv2'))
    _Write(os.path.join(site, 'cv2', '__init__.py'),
           b"raise ImportError('libGL.so.1: cannot open shared object file')\n" if package == 'raises' else b'')
    if package == 'plugins':
        os.makedirs(os.path.join(site, 'cv2', 'qt', 'plugins'))
    os.makedirs(os.path.join(sandbox.Root, 'venv', 'bin'))
    os.symlink(sys.executable, os.path.join(sandbox.Root, 'venv', 'bin', 'python'))
    process = sandbox.Run(f'CONST_VENV_DIR="{sandbox.Root}/venv"; STATUS="$(Opencv_Status)"; Show STATUS',
                          env={'PYTHONPATH': site})

    assert _Results(process)['STATUS'] == expected.format(site=site)


def test_requirements_without_the_headless_pin_stop_the_step(sandbox):
    """
    Description:
        The pin's one home is requirements.txt; without it the step stops rather than install an unpinned build.
    """

    setup = _Opencv_Venv(sandbox, gui='5.0.0.93')
    _Write(os.path.join(sandbox.Root, 'requirements.txt'), b'PyQt5>=5.15\nopencv-python-headless>=4.10\n')
    process = sandbox.Run(setup + 'Ensure_Headless_Opencv')

    assert process.returncode == 1 and _Pip_Calls(sandbox) == []
    assert _Levels(process, 'ERROR')[0].startswith('requirements.txt pins no opencv-python-headless version')


def test_the_requirements_install_is_followed_by_the_headless_opencv_step(sandbox):
    """
    Description:
        Install_Dependencies runs the swap right after pip installs the requirements, before 'pip freeze'
        compares, so a re-run in which pip brought opencv-python back and the swap removed it again reads as
        nothing changed.
    """

    stubs = ('Ensure_Torch_Build() { :; }; Run_Pip() { echo "STEP pip $1"; }; '
             'Ensure_Headless_Opencv() { echo "STEP opencv"; }; ')
    os.makedirs(os.path.join(sandbox.Root, 'venv', 'bin'))
    os.symlink(sys.executable, os.path.join(sandbox.Root, 'venv', 'bin', 'python'))
    process = sandbox.Run(f'CONST_VENV_DIR="{sandbox.Root}/venv"; PLATFORM_OS=macos; {stubs} Install_Dependencies')

    assert process.returncode == 0, process.stdout
    assert [line[5:] for line in process.stdout.splitlines() if line.startswith('STEP ')] == ['pip install', 'opencv']


# ---- configurations ---------------------------------------------------------

@pytest.mark.parametrize('gemma, expected_level', [('models/gemma-4-e4b-it-4bit', 'INFO'),
                                                   ('models/other-describer', 'WARNING')])
def test_configuration_pointing_elsewhere_names_the_field(sandbox, gemma, expected_level):
    pytest.importorskip('yaml')
    _Write(os.path.join(sandbox.Root, 'Configuration', 'Mode', 'Config_Test.yaml'),
           f'Segmentation:\n  Model: models/FastSAM/FastSAM-x.pt\nDescription:\n  Model: {gemma}\n'.encode())
    os.makedirs(os.path.join(sandbox.Root, 'venv', 'bin'))
    os.symlink(sys.executable, os.path.join(sandbox.Root, 'venv', 'bin', 'python'))
    process = sandbox.Run(f'CONST_ROOT="{sandbox.Root}"; CONST_VENV_DIR="{sandbox.Root}/venv"; Check_Configurations')

    assert process.returncode == 0
    messages = _Levels(process, expected_level)
    line = [m for m in messages if 'Description.Model' in m][0]
    if expected_level == 'WARNING':
        assert "Description.Model is 'models/other-describer'" in line
        assert 'Change Description.Model to models/gemma-4-e4b-it-4bit' in line
    assert any('Segmentation.Model points at the installed model' in m for m in _Levels(process, 'INFO'))


# ---- the whole detection path -----------------------------------------------

def test_the_sandboxed_script_resolves_its_root_to_the_sandbox(sandbox):
    """
    Description:
        The prevention, pinned: the sourced script is the sandbox's copy, so its CONST_ROOT — and with
        it models/ and .venv — is the sandbox before any snippet runs, not the real repository.
    """

    process = sandbox.Run('Show CONST_ROOT CONST_VENV_DIR')
    root = os.path.realpath(sandbox.Root)
    assert os.path.realpath(_Results(process)['CONST_ROOT']) == root
    assert os.path.realpath(_Results(process)['CONST_VENV_DIR']) == os.path.join(root, '.venv')


def test_detect_only_on_stubbed_linux_changes_nothing(sandbox):
    _Stub_Linux(sandbox)
    _Stub_Nvidia(sandbox, '560.35.03')
    _Stub_Python(sandbox, 'python3.10', '3.10.14', machine='x86_64')
    process = sandbox.Run(f'CONST_ROOT="{sandbox.Root}"; CONST_VENV_DIR="{sandbox.Root}/.venv"; Main --detect-only')

    assert process.returncode == 0
    assert not os.path.exists(os.path.join(sandbox.Root, '.venv'))
    infos = _Levels(process, 'INFO')
    assert any('requirements/linux-cuda12.txt' in m and 'whl/cu126' in m for m in infos)
    assert infos[-1] == 'Detection only (--detect-only): nothing was changed.'


@pytest.mark.parametrize('identifier, expected_level', [('models/dinov2-base', 'INFO'), ('models/other-identifier', 'WARNING')])
def test_a_catalogue_configuration_identifier_pointing_elsewhere_names_the_field(sandbox, identifier, expected_level):
    """
    Description:
        A catalogue mode also names the DINOv2 directory (Catalogue.Identifier); the check covers it as it
        covers the other two models, and leaves it out of a mode without a Catalogue block.
    """

    pytest.importorskip('yaml')
    _Write(os.path.join(sandbox.Root, 'Configuration', 'Mode', 'Config_Test.yaml'),
           ('Segmentation:\n  Model: models/FastSAM/FastSAM-x.pt\nDescription:\n  Model: models/gemma-4-e4b-it-4bit\n'
            'Catalogue:\n  Identifier: %s\n' % identifier).encode())
    _Write(os.path.join(sandbox.Root, 'Configuration', 'Mode', 'Config_Plain.yaml'),
           b'Segmentation:\n  Model: models/FastSAM/FastSAM-x.pt\nDescription:\n  Model: models/gemma-4-e4b-it-4bit\n')
    os.makedirs(os.path.join(sandbox.Root, 'venv', 'bin'))
    os.symlink(sys.executable, os.path.join(sandbox.Root, 'venv', 'bin', 'python'))
    process = sandbox.Run(f'CONST_ROOT="{sandbox.Root}"; CONST_VENV_DIR="{sandbox.Root}/venv"; Check_Configurations')

    assert process.returncode == 0
    lines = [m for m in _Levels(process, expected_level) if 'Catalogue.Identifier' in m]
    assert len(lines) == 1 and lines[0].startswith('Configuration Config_Test.yaml')
    if expected_level == 'WARNING':
        assert 'Change Catalogue.Identifier to models/dinov2-base' in lines[0]


def test_a_full_run_installs_every_model_after_the_environment(sandbox):
    """
    Description:
        Main runs the steps in order, and the model downloads — FastSAM, Gemma, DINOv2 — come after the
        environment they need (the hf CLI) and before the configuration check that names them. Each step is
        stood in by one that records its name, so this checks the sequence, not the steps.
    """

    steps = ('Select_Python', 'Detect_Platform', 'Check_Python_Architecture', 'Report_Plan', 'Ensure_Venv',
             'Install_Dependencies', 'Verify_Imports', 'Ensure_Fastsam', 'Ensure_Gemma', 'Ensure_Dinov2',
             'Check_Configurations', 'Report_Unused_Cpu_Flag')
    stubs = ' '.join('%s() { echo "STEP %s"; };' % (step, step) for step in steps)
    process = sandbox.Run(f'CONST_ROOT="{sandbox.Root}"; PLATFORM_OS=macos; {stubs} Main')

    assert process.returncode == 0, process.stdout
    assert [line.split()[1] for line in process.stdout.splitlines() if line.startswith('STEP ')] == list(steps)
