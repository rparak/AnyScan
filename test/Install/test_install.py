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
    Unverified end to end - its first exercise is the first real install on a fresh machine:
      - the Gemma download (hf download of 5.2 GB, then verification). The hf call is covered
        here by a stub only. What it shares with the FastSAM path that did run for real is the
        verification code (Verify_File and its hashes); the hf invocation, its --force-download
        re-fetch of a mismatched file, and the post-download re-verification loop have not run
        against the real Hub. The stale-status bug these tests caught in that loop is the kind
        only a fresh machine would otherwise have shown.
    Stubs only - UNVERIFIED in the sense of README > Platform:
      - every Linux branch (CUDA 12, CUDA 13, CPU, failing / missing / old nvidia-smi,
        low compute capability, old glibc, musl, aarch64), macOS on Intel, macOS < 14, and
        Rosetta. The stubs reproduce the command outputs as documented (nvidia-smi's CSV
        query and banner, sysctl, getconf); no Linux machine has run this script, and the
        pip resolves on the Linux paths (the PyTorch cu126/cu130/cpu indexes, the mlx
        extras) have not been performed. The Gemma download (hf) is stubbed everywhere:
        its skip path ran for real, its fetch path did not.
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
                Sandbox.Stub('nvidia-smi', 'exit 9')
                Sandbox.Run('Detect_Platform; Show MLX_BACKEND')
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

        return subprocess.run(['/bin/bash', '-c', script, 'test', CONST_INSTALL_SCRIPT], env=environment,
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
def Sandbox(tmp_path) -> Sandbox_Cls:
    """
    Description:
        A fresh hermetic sandbox per test.

    Returns:
        (1) parameter [Sandbox_Cls(object)]: The sandbox.
    """

    return Sandbox_Cls(tmp_path)


def _Stub_Macos(Sandbox: Sandbox_Cls, arm64: tp.Optional[str] = '1', machine: str = 'arm64',
                version: str = '15.1') -> None:
    """
    Description:
        Stub a Mac: uname, sysctl (hw.optional.arm64 absent on Intel when arm64 is None, as on
        older Intel macOS), and sw_vers.

    Args:
        (1) Sandbox [Sandbox_Cls(object)]: The sandbox.
        (2) arm64 [string]: hw.optional.arm64's value, or None for 'unknown oid'.
        (3) machine [string]: uname -m (x86_64 under Rosetta).
        (4) version [string]: The macOS version.
    """

    Sandbox.Stub('uname', f'case "$1" in -s) echo Darwin ;; -m) echo {machine} ;; esac')
    arm64_case = (f'echo {arm64}' if arm64 is not None
                  else "echo \"sysctl: unknown oid 'hw.optional.arm64'\" >&2; exit 1")
    Sandbox.Stub('sysctl', f'case "$2" in hw.optional.arm64) {arm64_case} ;; '
                           'machdep.cpu.brand_string) echo "Apple M2 Pro" ;; esac')
    Sandbox.Stub('sw_vers', f'echo {version}')


def _Stub_Linux(Sandbox: Sandbox_Cls, machine: str = 'x86_64', glibc: tp.Optional[str] = '2.35') -> None:
    """
    Description:
        Stub a Linux machine: uname and getconf (None = no glibc, as on musl).

    Args:
        (1) Sandbox [Sandbox_Cls(object)]: The sandbox.
        (2) machine [string]: uname -m.
        (3) glibc [string]: The glibc version, or None.
    """

    Sandbox.Stub('uname', f'case "$1" in -s) echo Linux ;; -m) echo {machine} ;; esac')
    Sandbox.Stub('getconf', f'echo "glibc {glibc}"' if glibc is not None
                            else 'echo "getconf: Unrecognized variable" >&2; exit 1')


def _Stub_Nvidia(Sandbox: Sandbox_Cls, driver: str, cap: str = '8.6', cuda: str = '12.6', gpus: int = 1) -> None:
    """
    Description:
        Stub a working nvidia-smi.

    Args:
        (1) Sandbox [Sandbox_Cls(object)]: The sandbox.
        (2) driver [string]: The driver version.
        (3) cap [string]: The compute capability.
        (4) cuda [string]: The CUDA version the banner reports.
        (5) gpus [int]: How many GPUs the query lists.
    """

    rows = ' '.join([f'"NVIDIA GeForce RTX 3090, {driver}"'] * gpus)
    Sandbox.Stub('nvidia-smi', CONST_NVIDIA_SMI_TEMPLATE.format(rows=rows, cap=cap, driver=driver, cuda=cuda))


# ---- version comparison -----------------------------------------------------

@pytest.mark.parametrize('a, b, expected', [
    ('3.10.10', '3.10', True), ('3.9.18', '3.10', False), ('3.13.1', '3.12.999', True), ('3.12.7', '3.12.999', False),
    ('550.54.14', '550.54.14', True), ('550.54.13', '550.54.14', False), ('550.127.05', '550.54.14', True),
    ('535.183.01', '550.54.14', False), ('580.65.06', '580', True), ('575.57.08', '580', False),
    ('7.5', '7.5', True), ('7.0', '7.5', False), ('12.0', '7.5', True), ('2.31', '2.35', False),
    ('2.39', '2.35', True), ('14', '14', True), ('13.6.1', '14', False), ('3.10.0rc1', '3.10', True)])
def test_version_ge(Sandbox, a, b, expected):
    process = Sandbox.Run(f'if Version_Ge "{a}" "{b}"; then echo "RESULT GE=yes"; else echo "RESULT GE=no"; fi')

    assert _Results(process)['GE'] == ('yes' if expected else 'no')


# ---- Python version check ---------------------------------------------------

def _Stub_Python(Sandbox: Sandbox_Cls, name: str, version: str, machine: str = 'arm64') -> str:
    """
    Description:
        Stub an interpreter that answers the version and platform.machine() queries.

    Args:
        (1) Sandbox [Sandbox_Cls(object)]: The sandbox.
        (2) name [string]: The command name (python3, python3.12, ...).
        (3) version [string]: What it reports as its version.
        (4) machine [string]: What it reports as platform.machine().

    Returns:
        (1) parameter [string]: The stub's path.
    """

    return Sandbox.Stub(name, f'case "$*" in *machine*) echo {machine} ;; *) echo {version} ;; esac')


def test_python_below_floor_stops_first_and_names_both_versions(Sandbox):
    _Stub_Python(Sandbox, 'python3', '3.9.18')
    process = Sandbox.Run(f'CONST_VENV_DIR="{Sandbox.Root}/venv"; Select_Python; echo "RESULT REACHED=yes"')

    assert process.returncode == 1
    assert 'REACHED' not in _Results(process)
    errors = _Levels(process, 'ERROR')
    assert 'Python 3.10 or newer is required; found python3 3.9.18.' in errors[0]
    assert 'PYTHON=' in errors[-1]


def test_python_search_prefers_a_suitable_versioned_interpreter(Sandbox):
    _Stub_Python(Sandbox, 'python3', '3.9.18')
    _Stub_Python(Sandbox, 'python3.11', '3.11.9')
    process = Sandbox.Run(f'CONST_VENV_DIR="{Sandbox.Root}/venv"; Select_Python; Show PYTHON_VERSION')

    assert process.returncode == 0
    assert _Results(process)['PYTHON_VERSION'] == '3.11.9'
    assert any('within the accepted range: 3.10 or newer, tested 3.10-3.12' in m for m in _Levels(process, 'INFO'))


def test_python_above_tested_range_is_accepted_with_an_informative_warning(Sandbox):
    _Stub_Python(Sandbox, 'python3.13', '3.13.1')
    process = Sandbox.Run(f'CONST_VENV_DIR="{Sandbox.Root}/venv"; Select_Python; Show PYTHON_VERSION')

    assert process.returncode == 0
    warning = _Levels(process, 'WARNING')[0]
    assert 'Python 3.13.1 is accepted (the floor is 3.10)' in warning
    assert 'newer than the tested range 3.10-3.12' in warning


def test_python_from_environment_variable_below_floor(Sandbox):
    path = _Stub_Python(Sandbox, 'oldpython', '3.8.20')
    process = Sandbox.Run(f'CONST_VENV_DIR="{Sandbox.Root}/venv"; Select_Python', env={'PYTHON': path})

    assert process.returncode == 1
    assert 'PYTHON=' in _Levels(process, 'ERROR')[0] and '3.8.20' in _Levels(process, 'ERROR')[0]


def test_existing_venv_decides_and_an_old_one_is_not_deleted(Sandbox):
    venv = os.path.join(Sandbox.Root, 'venv')
    os.makedirs(os.path.join(venv, 'bin'))
    Sandbox.Stub('python-old', 'echo 3.9.6')
    os.rename(os.path.join(Sandbox.Root, 'stubs', 'python-old'), os.path.join(venv, 'bin', 'python'))
    process = Sandbox.Run(f'CONST_VENV_DIR="{venv}"; Select_Python')

    assert process.returncode == 1
    assert 'rm -rf .venv' in _Levels(process, 'ERROR')[-1]
    assert os.path.exists(os.path.join(venv, 'bin', 'python'))


def test_x86_64_python_on_apple_silicon_stops(Sandbox):
    path = _Stub_Python(Sandbox, 'python3', '3.10.14', machine='x86_64')
    process = Sandbox.Run(f'PLATFORM_OS=macos; BASE_PYTHON="{path}"; PYTHON_VERSION=3.10.14; Check_Python_Architecture')

    assert process.returncode == 1
    assert 'Rosetta' in _Levels(process, 'ERROR')[0]


# ---- platform detection: macOS ----------------------------------------------

def test_macos_apple_silicon_selects_metal(Sandbox):
    _Stub_Macos(Sandbox)
    process = Sandbox.Run('Detect_Platform; Show PLATFORM_OS MLX_BACKEND TORCH_INDEX')

    assert process.returncode == 0
    assert _Results(process) == {'PLATFORM_OS': 'macos', 'MLX_BACKEND': 'metal', 'TORCH_INDEX': ''}
    assert 'Detected macOS 15.1 on Apple silicon (Apple M2 Pro).' in _Levels(process, 'INFO')


def test_macos_under_rosetta_is_still_apple_silicon(Sandbox):
    _Stub_Macos(Sandbox, machine='x86_64')
    process = Sandbox.Run('Detect_Platform; Show MLX_BACKEND')

    assert _Results(process)['MLX_BACKEND'] == 'metal'


@pytest.mark.parametrize('arm64', ['0', None])
def test_macos_intel_is_unsupported(Sandbox, arm64):
    _Stub_Macos(Sandbox, arm64=arm64, machine='x86_64')
    process = Sandbox.Run('Detect_Platform; echo "RESULT REACHED=yes"')

    assert process.returncode == 1
    assert 'REACHED' not in _Results(process)
    assert 'Intel processor, which is unsupported' in _Levels(process, 'ERROR')[0]
    assert 'MLX needs Apple silicon' in _Levels(process, 'ERROR')[0]


def test_macos_older_than_14_stops(Sandbox):
    _Stub_Macos(Sandbox, version='13.6.1')
    process = Sandbox.Run('Detect_Platform')

    assert process.returncode == 1
    assert 'macOS 14 or newer is required; this is 13.6.1' in _Levels(process, 'ERROR')[0]


# ---- platform detection: Linux ----------------------------------------------

@pytest.mark.parametrize('driver, cuda, backend, index', [
    ('560.35.03', '12.6', 'cuda12', 'cu126'),
    ('550.54.14', '12.4', 'cuda12', 'cu126'),
    ('575.57.08', '12.9', 'cuda12', 'cu126'),
    ('580.65.06', '13.0', 'cuda13', 'cu130'),
    ('590.44.01', '13.1', 'cuda13', 'cu130')])
def test_linux_nvidia_driver_selects_matching_builds(Sandbox, driver, cuda, backend, index):
    _Stub_Linux(Sandbox)
    _Stub_Nvidia(Sandbox, driver, cuda=cuda)
    process = Sandbox.Run('Detect_Platform; Show MLX_BACKEND TORCH_INDEX')

    assert process.returncode == 0
    assert _Results(process) == {'MLX_BACKEND': backend, 'TORCH_INDEX': index}
    infos = _Levels(process, 'INFO')
    assert f'Detected NVIDIA driver {driver} (CUDA {cuda}) on NVIDIA GeForce RTX 3090.' in infos
    assert any(f'mlx[{backend}]' in m and index in m for m in infos)
    assert not _Levels(process, 'WARNING')


def test_linux_multiple_gpus_reports_the_count(Sandbox):
    _Stub_Linux(Sandbox)
    _Stub_Nvidia(Sandbox, '560.35.03', gpus=2)
    process = Sandbox.Run('Detect_Platform')

    assert any('with 2 GPUs; MLX uses the first' in m for m in _Levels(process, 'INFO'))


def test_linux_without_nvidia_smi_uses_cpu_with_warning(Sandbox):
    _Stub_Linux(Sandbox)
    process = Sandbox.Run('Detect_Platform; Show MLX_BACKEND TORCH_INDEX')

    assert process.returncode == 0
    assert _Results(process) == {'MLX_BACKEND': 'cpu', 'TORCH_INDEX': 'cpu'}
    warning = _Levels(process, 'WARNING')[0]
    assert warning.startswith('No NVIDIA driver found (nvidia-smi is not installed); installing the CPU builds')
    assert 'slow' in warning


def test_linux_library_installed_but_no_working_gpu_uses_cpu(Sandbox):
    # The case the driver check exists for: nvidia-smi is present but cannot reach a driver.
    _Stub_Linux(Sandbox)
    Sandbox.Stub('nvidia-smi', 'echo "NVIDIA-SMI has failed because it couldn\'t communicate with the NVIDIA driver. '
                               'Make sure that the latest NVIDIA driver is installed and running."; exit 9')
    process = Sandbox.Run('Detect_Platform; Show MLX_BACKEND TORCH_INDEX')

    assert process.returncode == 0
    assert _Results(process) == {'MLX_BACKEND': 'cpu', 'TORCH_INDEX': 'cpu'}
    assert "nvidia-smi is installed but failed (NVIDIA-SMI has failed because it couldn't communicate" \
        in _Levels(process, 'WARNING')[0]


def test_linux_nvidia_smi_listing_no_gpu_uses_cpu(Sandbox):
    _Stub_Linux(Sandbox)
    Sandbox.Stub('nvidia-smi', 'echo "No devices were found"; exit 0')
    process = Sandbox.Run('Detect_Platform; Show MLX_BACKEND')

    assert _Results(process)['MLX_BACKEND'] == 'cpu'
    assert 'nvidia-smi reported no GPU (No devices were found)' in _Levels(process, 'WARNING')[0]


def test_linux_driver_too_old_for_mlx_cuda_uses_cpu(Sandbox):
    _Stub_Linux(Sandbox)
    _Stub_Nvidia(Sandbox, '535.183.01', cuda='12.2')
    process = Sandbox.Run('Detect_Platform; Show MLX_BACKEND TORCH_INDEX')

    assert _Results(process) == {'MLX_BACKEND': 'cpu', 'TORCH_INDEX': 'cpu'}
    assert 'older than 550.54.14' in _Levels(process, 'WARNING')[0]


def test_linux_gpu_below_compute_capability_uses_cpu(Sandbox):
    _Stub_Linux(Sandbox)
    _Stub_Nvidia(Sandbox, '560.35.03', cap='7.0')
    process = Sandbox.Run('Detect_Platform; Show MLX_BACKEND')

    assert _Results(process)['MLX_BACKEND'] == 'cpu'
    assert 'compute capability 7.0' in _Levels(process, 'WARNING')[0]


def test_linux_aarch64_stops_naming_pyqt5_and_what_would_be_needed(Sandbox):
    _Stub_Linux(Sandbox, machine='aarch64')
    process = Sandbox.Run('Detect_Platform')

    assert process.returncode == 1
    errors = _Levels(process, 'ERROR')
    assert 'PyQt5 5.15.11' in errors[0] and 'no Linux aarch64 wheel' in errors[0]
    assert 'python3-pyqt5' in errors[1] and 'PyQt6' in errors[1]


def test_linux_old_glibc_stops(Sandbox):
    _Stub_Linux(Sandbox, glibc='2.31')
    process = Sandbox.Run('Detect_Platform')

    assert process.returncode == 1
    assert 'glibc 2.35 or newer is required; this system has 2.31' in _Levels(process, 'ERROR')[0]


def test_linux_musl_stops(Sandbox):
    _Stub_Linux(Sandbox, glibc=None)
    process = Sandbox.Run('Detect_Platform')

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
def test_verify_file_statuses(Sandbox, content, kind, expected):
    reference = b'weights' if kind == 'sha256' else b'{"a": 1}\n'
    digest = hashlib.sha256(reference).hexdigest() if kind == 'sha256' else _Blob_Sha1(reference)
    path = os.path.join(Sandbox.Root, 'file.bin')
    if content is not None:
        _Write(path, content)
    process = Sandbox.Run(f'status=0; Verify_File "{path}" {len(reference)} {kind} {digest} || status=$?; Show status')

    assert _Results(process)['status'] == str(expected)


def test_blob_hash_matches_git(Sandbox):
    if shutil.which('git') is None:
        pytest.skip('git is not installed')
    path = os.path.join(Sandbox.Root, 'config.json')
    _Write(path, b'{"model_type": "gemma4"}\n')
    process = Sandbox.Run(f'echo "RESULT HASH=$(Hash_Git_Blob "{path}" 25)"')
    expected = subprocess.run(['git', 'hash-object', path], stdout=subprocess.PIPE, universal_newlines=True).stdout.strip()

    assert _Results(process)['HASH'] == expected


def _Fastsam_Snippet(Sandbox: Sandbox_Cls, reference: bytes) -> str:
    """
    Description:
        Point the FastSAM constants at a scratch root and a fixture checksum.

    Args:
        (1) Sandbox [Sandbox_Cls(object)]: The sandbox.
        (2) reference [bytes]: The content the 'published' checksum is of.

    Returns:
        (1) parameter [string]: The bash assignments.
    """

    return (f'CONST_ROOT="{Sandbox.Root}"; CONST_FASTSAM_URL=https://example.invalid/FastSAM-x.pt; '
            f'CONST_FASTSAM_SIZE={len(reference)}; CONST_FASTSAM_SHA256={hashlib.sha256(reference).hexdigest()}; ')


def _Stub_Curl(Sandbox: Sandbox_Cls, serves: bytes) -> str:
    """
    Description:
        A curl that records its arguments and writes the given content to --output.

    Args:
        (1) Sandbox [Sandbox_Cls(object)]: The sandbox.
        (2) serves [bytes]: The content 'downloaded'.

    Returns:
        (1) parameter [string]: The file the call is recorded in.
    """

    record = os.path.join(Sandbox.Root, 'curl.calls')
    served = os.path.join(Sandbox.Root, 'served.bin')
    _Write(served, serves)
    Sandbox.Stub('curl', f'echo "$*" >> "{record}"\n'
                         'while [ "$#" -gt 0 ]; do [ "$1" = --output ] && out="$2"; shift; done\n'
                         f'cp "{served}" "$out"')

    return record


def test_fastsam_present_and_correct_is_not_downloaded(Sandbox):
    reference = b'fastsam-weights'
    _Write(os.path.join(Sandbox.Root, 'models', 'sam-1', 'FastSAM-x.pt'), reference)
    record = _Stub_Curl(Sandbox, reference)
    process = Sandbox.Run(_Fastsam_Snippet(Sandbox, reference) + 'Ensure_Fastsam')

    assert process.returncode == 0
    assert not os.path.exists(record)
    assert any('already present and matches the published SHA-256' in m for m in _Levels(process, 'INFO'))


def test_fastsam_corrupt_is_downloaded_again_and_verified(Sandbox):
    reference = b'fastsam-weights'
    target = os.path.join(Sandbox.Root, 'models', 'sam-1', 'FastSAM-x.pt')
    _Write(target, b'fastsam-weightz')
    record = _Stub_Curl(Sandbox, reference)
    process = Sandbox.Run(_Fastsam_Snippet(Sandbox, reference) + 'Ensure_Fastsam')

    assert process.returncode == 0
    assert 'https://example.invalid/FastSAM-x.pt' in open(record).read()
    assert open(target, 'rb').read() == reference
    assert not os.path.exists(target + '.part')
    assert 'checksum does not match' in _Levels(process, 'WARNING')[0]


def test_fastsam_bad_download_replaces_nothing(Sandbox):
    reference = b'fastsam-weights'
    target = os.path.join(Sandbox.Root, 'models', 'sam-1', 'FastSAM-x.pt')
    _Write(target, b'fastsam-old!!!!')
    _Stub_Curl(Sandbox, b'<html>rate limited</html>')
    process = Sandbox.Run(_Fastsam_Snippet(Sandbox, reference) + 'Ensure_Fastsam')

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


def _Gemma_Snippet(Sandbox: Sandbox_Cls) -> str:
    """
    Description:
        Point the Gemma constants at a scratch root, a fixture manifest and a stub venv.

    Args:
        (1) Sandbox [Sandbox_Cls(object)]: The sandbox.

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

    return (f'CONST_ROOT="{Sandbox.Root}"; CONST_VENV_DIR="{Sandbox.Root}/venv"; CONST_SLOW_HASH_BYTES=1024; '
            f"CONST_GEMMA_FILES='{manifest}'; ")


def _Stub_Hf(Sandbox: Sandbox_Cls, correct: bool = True) -> str:
    """
    Description:
        A .venv/bin/hf that records its arguments and writes the fixture content (or wrong
        content) for each file named on its command line into --local-dir.

    Args:
        (1) Sandbox [Sandbox_Cls(object)]: The sandbox.
        (2) correct [bool]: Whether it 'downloads' the right bytes.

    Returns:
        (1) parameter [string]: The file the call is recorded in.
    """

    record = os.path.join(Sandbox.Root, 'hf.calls')
    fixtures = os.path.join(Sandbox.Root, 'hf-fixtures')
    for name, content in CONST_GEMMA_FIXTURE.items():
        _Write(os.path.join(fixtures, name), content if correct else content + b'!')
    path = Sandbox.Stub('hf', f'echo "$*" >> "{record}"\n'
                              'names=""; while [ "$#" -gt 0 ]; do case "$1" in\n'
                              '  --local-dir) dir="$2"; shift ;; --revision) shift ;; --*|download) ;;\n'
                              '  */*) ;; *) names="$names $1" ;; esac; shift; done\n'
                              f'for n in $names; do cp "{fixtures}/$n" "$dir/$n"; done')
    os.makedirs(os.path.join(Sandbox.Root, 'venv', 'bin'))
    os.rename(path, os.path.join(Sandbox.Root, 'venv', 'bin', 'hf'))

    return record


def test_gemma_present_and_correct_is_not_downloaded_and_reports_time(Sandbox):
    for name, content in CONST_GEMMA_FIXTURE.items():
        _Write(os.path.join(Sandbox.Root, 'models', 'gemma-4-e4b-it-4bit', name), content)
    record = _Stub_Hf(Sandbox)
    process = Sandbox.Run(_Gemma_Snippet(Sandbox) + 'Ensure_Gemma')

    assert process.returncode == 0
    assert not os.path.exists(record)
    infos = _Levels(process, 'INFO')
    assert any(m.startswith('Hashing model.safetensors') for m in infos)
    assert any(re.match(r'Hashed model\.safetensors in \d+ s\.', m) for m in infos)
    assert any(re.search(r'already present and every file matches the published hashes \(checked in \d+ s\)', m)
               for m in infos)


def test_gemma_fetches_only_the_mismatched_file(Sandbox):
    directory = os.path.join(Sandbox.Root, 'models', 'gemma-4-e4b-it-4bit')
    for name, content in CONST_GEMMA_FIXTURE.items():
        _Write(os.path.join(directory, name), content)
    _Write(os.path.join(directory, 'tokenizer.json'), b'{"version": "0.9"}\n')
    record = _Stub_Hf(Sandbox)
    process = Sandbox.Run(_Gemma_Snippet(Sandbox) + 'Ensure_Gemma')

    assert process.returncode == 0
    call = open(record).read().split()
    assert 'tokenizer.json' in call and 'config.json' not in call and 'model.safetensors' not in call
    assert '--force-download' in call and '--revision' in call
    assert open(os.path.join(directory, 'tokenizer.json'), 'rb').read() == CONST_GEMMA_FIXTURE['tokenizer.json']
    assert 'Gemma file tokenizer.json is present but its checksum does not match' in _Levels(process, 'WARNING')[0]


def test_gemma_missing_directory_fetches_everything(Sandbox):
    record = _Stub_Hf(Sandbox)
    process = Sandbox.Run(_Gemma_Snippet(Sandbox) + 'Ensure_Gemma')

    assert process.returncode == 0
    call = open(record).read().split()
    assert all(name in call for name in CONST_GEMMA_FIXTURE)
    assert not _Levels(process, 'WARNING')


def test_gemma_download_that_does_not_verify_fails(Sandbox):
    _Stub_Hf(Sandbox, correct=False)
    process = Sandbox.Run(_Gemma_Snippet(Sandbox) + 'Ensure_Gemma')

    assert process.returncode == 1
    assert 'After downloading, Gemma file' in _Levels(process, 'ERROR')[0]


# ---- configurations ---------------------------------------------------------

@pytest.mark.parametrize('gemma, expected_level', [('models/gemma-4-e4b-it-4bit', 'INFO'),
                                                   ('models/gemma-4-e4b-it-8bit', 'WARNING')])
def test_configuration_pointing_elsewhere_names_the_field(Sandbox, gemma, expected_level):
    pytest.importorskip('yaml')
    _Write(os.path.join(Sandbox.Root, 'Configuration', 'Config_Test.yaml'),
           f'Segmentation:\n  Model: models/sam-1/FastSAM-x.pt\nDescription:\n  Model: {gemma}\n'.encode())
    os.makedirs(os.path.join(Sandbox.Root, 'venv', 'bin'))
    os.symlink(sys.executable, os.path.join(Sandbox.Root, 'venv', 'bin', 'python'))
    process = Sandbox.Run(f'CONST_ROOT="{Sandbox.Root}"; CONST_VENV_DIR="{Sandbox.Root}/venv"; Check_Configurations')

    assert process.returncode == 0
    messages = _Levels(process, expected_level)
    line = [m for m in messages if 'Description.Model' in m][0]
    if expected_level == 'WARNING':
        assert "Description.Model is 'models/gemma-4-e4b-it-8bit'" in line
        assert 'Change Description.Model to models/gemma-4-e4b-it-4bit' in line
    assert any('Segmentation.Model points at the installed model' in m for m in _Levels(process, 'INFO'))


# ---- the whole detection path -----------------------------------------------

def test_detect_only_on_stubbed_linux_changes_nothing(Sandbox):
    _Stub_Linux(Sandbox)
    _Stub_Nvidia(Sandbox, '560.35.03')
    _Stub_Python(Sandbox, 'python3.10', '3.10.14', machine='x86_64')
    process = Sandbox.Run(f'CONST_ROOT="{Sandbox.Root}"; CONST_VENV_DIR="{Sandbox.Root}/.venv"; Main --detect-only')

    assert process.returncode == 0
    assert not os.path.exists(os.path.join(Sandbox.Root, '.venv'))
    infos = _Levels(process, 'INFO')
    assert any('requirements/linux-cuda12.txt' in m and 'whl/cu126' in m for m in infos)
    assert infos[-1] == 'Detection only (--detect-only): nothing was changed.'
