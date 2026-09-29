#!/usr/bin/env bash
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
# File Name: ../install.sh
## =========================================================================== ##

# Description:
#   Set up AnyScan on macOS (Apple silicon) or Linux (x86_64): create the project's
#   virtual environment, install the dependencies that match the hardware, and download
#   and verify the FastSAM and Gemma weights into models/.
#
#   Order is cheapest-failure-first: the Python version, then the platform, then the
#   environment, the packages, and only then the ~5.3 GB of weights. Every step first
#   checks what is already in place and reports it, so running the script twice is safe
#   and the second run changes nothing.
#
#   Usage:
#       ./install.sh                 Install (or confirm) everything.
#       ./install.sh --detect-only   Report the Python, platform and plan; change nothing.
#       ./install.sh --cpu           Linux only: install the CPU builds when no usable NVIDIA GPU
#                                    is found, instead of stopping. Unmeasured, expected to be
#                                    far slower.
#       PYTHON=python3.11 ./install.sh
#                                    Create .venv from that interpreter instead of the
#                                    first suitable one found on PATH.
#
#   Every line is written in the application's log format (src/Logger/Core.py):
#       2026-09-24 13:05:07 [INFO   ] message
#
#   Written for bash 3.2, the version macOS ships: no associative arrays, no mapfile,
#   no ${var,,}.

# Description:
#   Initialization of constants.

# The repository root, resolved from this file's location, so the script works from any
# current directory.
#   Unit [string]
CONST_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The project's virtual environment. Everything is installed into it and nothing else.
#   Unit [string]
CONST_VENV_DIR="${CONST_ROOT}/.venv"
# The Python the project needs. The floor is a hard requirement: mlx 0.32.2, mlx-vlm 0.7.2
# and torch 2.14 all declare requires_python >=3.10. The ceiling is only the tested range
# (the application was developed on 3.10); every pinned package publishes wheels above it.
#   Unit [string]
CONST_PYTHON_FLOOR='3.10'
CONST_PYTHON_TESTED_MAX='3.12'
# Interpreters tried, in order, when neither .venv nor $PYTHON names one.
#   Unit [string]
CONST_PYTHON_CANDIDATES='python3.12 python3.11 python3.10 python3.13 python3.14 python3 python'
# The oldest macOS the mlx wheels are built for (macosx_14_0_arm64).
#   Unit [string]
CONST_MACOS_MIN='14'
# The oldest glibc the mlx Linux wheels are built for (manylinux_2_35).
#   Unit [string]
CONST_GLIBC_MIN='2.35'
# The NVIDIA requirements of MLX 0.32.2's CUDA backend (MLX docs, "Install > CUDA"):
# driver >= 550.54.14 and compute capability >= 7.5 for CUDA 12; driver >= 580 for CUDA 13.
#   Unit [string]
CONST_MLX_CUDA12_MIN_DRIVER='550.54.14'
CONST_MLX_CUDA13_MIN_DRIVER='580'
CONST_MLX_CUDA_MIN_COMPUTE_CAP='7.5'
# The VRAM GPU 0 must have, read from nvidia-smi (MiB). The describer's model and FastSAM share
# the card. Measured on Linux (2026-09-29, CUDA 13): the whole application peaks at 9.5 GB of GPU
# memory, 6.99 GB of it MLX (docs/design-decisions.md, "E4B stays the describer on both machines"),
# so 11 GiB is the floor, with room above that peak (12 GB cards report ~12,280 MiB).
#   Unit [MiB]
CONST_MIN_VRAM_MIB='11264'
# Memory already in use on GPU 0 (a display, another process) above which the plan warns.
#   Unit [MiB]
CONST_BUSY_VRAM_MIB='1536'
# The PyTorch wheel index. A CUDA build cannot be selected by an environment marker, so the
# script passes the index for the detected backend (cu126, cu130 or cpu) when it installs
# torch and torchvision - together, so torchvision is built for the same CUDA as torch.
#   Unit [string]
CONST_TORCH_INDEX_BASE='https://download.pytorch.org/whl'
# The requirement files: the portable list, and one selectable MLX-backend line per Linux path.
#   Unit [string]
CONST_REQUIREMENTS="${CONST_ROOT}/requirements.txt"
CONST_REQUIREMENTS_DIR="${CONST_ROOT}/requirements"
# FastSAM-x: the ultralytics release asset, and the SHA-256 GitHub publishes for it (the
# asset's 'digest' field on the v8.4.0 release). Paths are relative to the repository root,
# as the configuration writes them.
#   Unit [string]
CONST_FASTSAM_URL='https://github.com/ultralytics/assets/releases/download/v8.4.0/FastSAM-x.pt'
CONST_FASTSAM_REL='models/FastSAM/FastSAM-x.pt'
CONST_FASTSAM_SIZE='144972346'
CONST_FASTSAM_SHA256='752cadc2828edb1cd4bc4f9eb587100631af06ea2108f4c9ed56df4755701e76'
# Gemma 4 E4B, 4-bit MLX, at the revision the application was measured with. The same
# repository serves every path: the weights are MLX affine 4-bit (group size 64), which
# MLX's Metal, CUDA and CPU backends all implement.
#   Unit [string]
CONST_GEMMA_REPO='mlx-community/gemma-4-e4b-it-4bit'
CONST_GEMMA_REVISION='475b9088d29754a3379866cf5aeb6b41acd313c2'
CONST_GEMMA_REL='models/gemma-4-e4b-it-4bit'
# Every file of that revision, as Hugging Face publishes it: 'name size kind hash'. 'sha256'
# is the LFS SHA-256; 'blob' is the git blob SHA-1 (the hash of 'blob <size>\0' + content),
# which is what the Hub publishes for small files.
#   Unit [string]
CONST_GEMMA_FILES='.gitattributes 1570 blob 52373fe24473b1aa44333d318f578ae6bf04b49b
README.md 593 blob 04f02899dc45b0d9deffa167305da20699790e0e
chat_template.jinja 17336 blob c19999a347da729cf62806a8ddb7eb8e315223b5
config.json 6628 blob 4ee08502c4f98810dd43800ec849bd69f94adc98
generation_config.json 208 blob e605bb4523b1462ea9d9a3810b9e3ecf7ab7b1f6
model.safetensors 5146800534 sha256 932b8271fc3fe65adcc78b96c10c6268bbfb13e8f67d1358727c0d6ee97e1eff
model.safetensors.index.json 240961 blob c03ce5f7086b735345038501f731634de064493b
processor_config.json 1316 blob a086fb7e04b477c291a120b0a004abb78b11c6d2
tokenizer.json 32169626 sha256 cc8d3a0ce36466ccc1278bf987df5f71db1719b9ca6b4118264f45cb627bfe0f
tokenizer_config.json 2740 blob cf6235aee46a24bf71f251c0a4e7a0379948f7d2'
# Files at least this large get a "hashing, this takes a while" line and their own elapsed
# time, so a pause on the 5.1 GB file is not mistaken for a hang.
#   Unit [int]
CONST_SLOW_HASH_BYTES='104857600'
# The width the bracketed level is padded to, matching src/Logger/Core.py (CONST_LEVEL_WIDTH).
#   Unit [int]
CONST_LEVEL_WIDTH='7'

# Description:
#   What the detection found. Set by Detect_Platform and Select_Python, read by the
#   install steps.
#     PLATFORM_OS       macos | linux
#     PLATFORM_SUMMARY  one human-readable line for the final report
#     MLX_BACKEND       metal | cuda12 | cuda13 | cpu
#     TORCH_INDEX       '' (PyPI default, macOS) | cu126 | cu130 | cpu
#     BASE_PYTHON       the interpreter .venv is (or was) created from
#     PYTHON_VERSION    its version, e.g. 3.10.10
#     CPU_OPT_IN        1 when --cpu was given
#     GPU_MEMORY_MIB    GPU 0's total memory, when an NVIDIA GPU was found
#     MODEL_*           the describer model's name, repository, revision, directory and
#                       manifest (Selected_Model)
PLATFORM_OS=''
PLATFORM_SUMMARY=''
MLX_BACKEND=''
TORCH_INDEX=''
BASE_PYTHON=''
PYTHON_VERSION=''
DETECT_ONLY='0'
CPU_OPT_IN='0'
GPU_MEMORY_MIB=''
MODEL_NAME=''
MODEL_REPO=''
MODEL_REVISION=''
MODEL_REL=''
MODEL_FILES=''

# ---- output ----------------------------------------------------------------

Log() {
    # Description:
    #   Write one line in the application's log format: the date and time, the level
    #   padded to a fixed width inside brackets, then the message.
    #
    # Args:
    #   (1) level [string]: INFO | WARNING | ERROR, chosen by the call site.
    #   (2) message [string]: The message.

    printf '%s [%-*s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "${CONST_LEVEL_WIDTH}" "$1" "$2"
}

Die() {
    # Description:
    #   Report a failure as one or more ERROR lines and stop with a non-zero status. The
    #   last argument should say what to do.
    #
    # Args:
    #   (1..n) message [string]: One ERROR line each.

    local line
    for line in "$@"; do
        Log ERROR "${line}"
    done
    exit 1
}

On_Unexpected_Error() {
    # Description:
    #   The ERR trap: a command failed that no step anticipated. Say where, instead of
    #   leaving a bare non-zero exit.
    #
    # Args:
    #   (1) line [int]: The line the failing command is on.
    #   (2) command [string]: The failing command.

    Log ERROR "Unexpected failure at install.sh line $1: $2"
    Log ERROR "Nothing was reported as complete that is not. Re-run ./install.sh; if it fails at the same line, report it with the output above."
    exit 1
}

On_Interrupt() {
    # Description:
    #   The INT/TERM trap. A verified file is never partial, so re-running is always safe.

    Log ERROR 'Interrupted. Re-run ./install.sh to continue: verified files are kept and anything incomplete is fetched again.'
    exit 130
}

Format_Size() {
    # Description:
    #   Format a byte count for a message, in decimal units as the download tools print them.
    #
    # Args:
    #   (1) bytes [int]: The size.
    #
    # Returns:
    #   (1) parameter [string]: e.g. '5.1 GB', '145 MB' or '17 kB', on stdout.

    awk -v b="$1" 'BEGIN { if (b >= 1e9) printf "%.1f GB", b / 1e9; else if (b >= 1e6) printf "%.0f MB", b / 1e6; else printf "%.0f kB", b / 1e3 }'
}

# ---- helpers ---------------------------------------------------------------

Version_Ge() {
    # Description:
    #   Compare two dotted version numbers field by field, numerically (so 550.54.14 is
    #   older than 550.127.5). Missing fields count as 0; a non-numeric tail on a field
    #   ('0rc1') is ignored.
    #
    # Args:
    #   (1) a [string]: The version tested.
    #   (2) b [string]: The minimum.
    #
    # Returns:
    #   (1) parameter [status]: 0 when a >= b, 1 otherwise.

    local -a av bv
    local i x y
    IFS=. read -r -a av <<< "$1"
    IFS=. read -r -a bv <<< "$2"
    for i in 0 1 2 3; do
        x="${av[$i]:-0}"; y="${bv[$i]:-0}"
        x="${x%%[!0-9]*}"; y="${y%%[!0-9]*}"
        x="${x:-0}"; y="${y:-0}"
        if (( 10#${x} > 10#${y} )); then return 0; fi
        if (( 10#${x} < 10#${y} )); then return 1; fi
    done
    return 0
}

Hash_Sha256() {
    # Description:
    #   The SHA-256 of a file, with whichever tool the platform has: sha256sum when present
    #   (Linux, and macOS 26 ships /sbin/sha256sum), shasum -a 256 otherwise (older macOS).
    #
    # Args:
    #   (1) path [string]: The file.
    #
    # Returns:
    #   (1) parameter [string]: The lowercase hex digest, on stdout.

    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | cut -d ' ' -f 1
    else
        shasum -a 256 "$1" | cut -d ' ' -f 1
    fi
}

Hash_Git_Blob() {
    # Description:
    #   The git blob SHA-1 of a file - SHA-1 over 'blob <size>\0' followed by the content -
    #   which is what Hugging Face publishes for files not stored in LFS. Computed directly
    #   so git is not needed.
    #
    # Args:
    #   (1) path [string]: The file.
    #   (2) size [int]: Its size in bytes.
    #
    # Returns:
    #   (1) parameter [string]: The lowercase hex digest, on stdout.

    if command -v sha1sum >/dev/null 2>&1; then
        { printf 'blob %s\0' "$2"; cat "$1"; } | sha1sum | cut -d ' ' -f 1
    else
        { printf 'blob %s\0' "$2"; cat "$1"; } | shasum -a 1 | cut -d ' ' -f 1
    fi
}

File_Size() {
    # Description:
    #   A file's size in bytes, portable between BSD and GNU userlands.
    #
    # Args:
    #   (1) path [string]: The file.
    #
    # Returns:
    #   (1) parameter [int]: The size, on stdout.

    wc -c < "$1" | tr -d ' '
}

Verify_File() {
    # Description:
    #   Check a file against its published size and hash. The size is checked first, so a
    #   truncated download is rejected without hashing it. Files of CONST_SLOW_HASH_BYTES or
    #   more log that they are being hashed and how long it took.
    #
    # Args:
    #   (1) path [string]: The file.
    #   (2) size [int]: The published size in bytes.
    #   (3) kind [string]: sha256 | blob.
    #   (4) hash [string]: The published hash.
    #
    # Returns:
    #   (1) parameter [status]: 0 verified, 1 missing, 2 wrong size, 3 wrong hash.

    local path="$1" size="$2" kind="$3" expected="$4" actual start
    [ -f "${path}" ] || return 1
    [ "$(File_Size "${path}")" = "${size}" ] || return 2
    start="${SECONDS}"
    if [ "${size}" -ge "${CONST_SLOW_HASH_BYTES}" ]; then
        Log INFO "Hashing $(basename "${path}") ($(Format_Size "${size}")); this takes a while on large files."
    fi
    if [ "${kind}" = 'sha256' ]; then
        actual="$(Hash_Sha256 "${path}")"
    else
        actual="$(Hash_Git_Blob "${path}" "${size}")"
    fi
    if [ "${size}" -ge "${CONST_SLOW_HASH_BYTES}" ]; then
        Log INFO "Hashed $(basename "${path}") in $(( SECONDS - start )) s."
    fi
    [ "${actual}" = "${expected}" ] || return 3
    return 0
}

Describe_Verify_Status() {
    # Description:
    #   The words for a Verify_File status, for a log message.
    #
    # Args:
    #   (1) status [int]: The Verify_File return value.
    #
    # Returns:
    #   (1) parameter [string]: The description, on stdout.

    case "$1" in
        1) printf 'missing' ;;
        2) printf 'present with the wrong size (incomplete or a different file)' ;;
        3) printf 'present but its checksum does not match the published file' ;;
        *) printf 'verified' ;;
    esac
}

Ensure_Free_Space() {
    # Description:
    #   Stop before a download that cannot fit, rather than failing partway through it.
    #   Requires 10 % headroom over the bytes about to be written.
    #
    # Args:
    #   (1) directory [string]: Where the files will be written (must exist).
    #   (2) bytes [int]: How much is about to be downloaded.

    local available_kb needed_kb
    available_kb="$(df -Pk "$1" | awk 'NR == 2 { print $4 }')"
    needed_kb=$(( $2 / 1024 * 11 / 10 ))
    if [ -n "${available_kb}" ] && [ "${available_kb}" -lt "${needed_kb}" ]; then
        Die "Not enough free space in $1: the download needs about $(Format_Size $(( needed_kb * 1024 ))) and $(Format_Size $(( available_kb * 1024 ))) is free." \
            'Free some space (or move the repository to a larger disk) and re-run ./install.sh.'
    fi
}

Python_Version_Of() {
    # Description:
    #   Ask an interpreter for its version.
    #
    # Args:
    #   (1) python [string]: The interpreter (name on PATH or path).
    #
    # Returns:
    #   (1) parameter [string]: e.g. 3.10.10 on stdout; empty (status 1) if it does not run.

    "$1" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>/dev/null
}

# ---- 1: Python -------------------------------------------------------------

Select_Python() {
    # Description:
    #   Choose the interpreter and check it against the floor, before anything else - a
    #   failure here is free, one after a 5 GB download is not. An existing .venv decides
    #   (its Python is the one that will run the application); otherwise $PYTHON, otherwise
    #   the first of CONST_PYTHON_CANDIDATES at or above the floor. Sets BASE_PYTHON and
    #   PYTHON_VERSION.

    local candidate version found=''
    if [ -x "${CONST_VENV_DIR}/bin/python" ]; then
        BASE_PYTHON="${CONST_VENV_DIR}/bin/python"
        PYTHON_VERSION="$(Python_Version_Of "${BASE_PYTHON}")" || \
            Die "The existing virtual environment ${CONST_VENV_DIR} is broken: its Python does not run." \
                "Remove it (rm -rf .venv) and re-run ./install.sh to create it again."
        Log INFO "Found the existing virtual environment .venv, with Python ${PYTHON_VERSION}."
        if ! Version_Ge "${PYTHON_VERSION}" "${CONST_PYTHON_FLOOR}"; then
            Die "The existing .venv was created with Python ${PYTHON_VERSION}; AnyScan needs ${CONST_PYTHON_FLOOR} or newer (mlx, mlx-vlm and torch require it)." \
                "Remove it (rm -rf .venv) and re-run ./install.sh with a newer Python on PATH, or name one: PYTHON=python3.10 ./install.sh"
        fi
    elif [ -d "${CONST_VENV_DIR}" ]; then
        Die "${CONST_VENV_DIR} exists but has no bin/python, so it is not a usable virtual environment." \
            "Remove it (rm -rf .venv) and re-run ./install.sh."
    elif [ -n "${PYTHON:-}" ]; then
        BASE_PYTHON="${PYTHON}"
        PYTHON_VERSION="$(Python_Version_Of "${BASE_PYTHON}")" || \
            Die "PYTHON=${PYTHON} does not run as a Python interpreter." \
                "Set PYTHON to a Python ${CONST_PYTHON_FLOOR}+ interpreter, or unset it to search PATH."
        Log INFO "Found Python ${PYTHON_VERSION} (${BASE_PYTHON}, from \$PYTHON)."
        if ! Version_Ge "${PYTHON_VERSION}" "${CONST_PYTHON_FLOOR}"; then
            Die "Python ${CONST_PYTHON_FLOOR} or newer is required; PYTHON=${PYTHON} is ${PYTHON_VERSION}." \
                "Install Python ${CONST_PYTHON_FLOOR}-${CONST_PYTHON_TESTED_MAX} and point PYTHON at it."
        fi
    else
        for candidate in ${CONST_PYTHON_CANDIDATES}; do
            command -v "${candidate}" >/dev/null 2>&1 || continue
            version="$(Python_Version_Of "${candidate}")" || continue
            if Version_Ge "${version}" "${CONST_PYTHON_FLOOR}"; then
                BASE_PYTHON="$(command -v "${candidate}")"
                PYTHON_VERSION="${version}"
                break
            fi
            found="${found:+${found}, }${candidate} ${version}"
        done
        if [ -z "${BASE_PYTHON}" ]; then
            Die "Python ${CONST_PYTHON_FLOOR} or newer is required; found ${found:-no python3 on PATH}." \
                "Install Python ${CONST_PYTHON_FLOOR}-${CONST_PYTHON_TESTED_MAX} (e.g. from python.org, Homebrew or your distribution) and re-run, or name it: PYTHON=/path/to/python3.10 ./install.sh"
        fi
        Log INFO "Found Python ${PYTHON_VERSION} (${BASE_PYTHON})."
    fi
    # The range, stated either way, so the ceiling reads as information rather than alarm.
    if Version_Ge "${PYTHON_VERSION}" "${CONST_PYTHON_TESTED_MAX}.999"; then
        Log WARNING "Python ${PYTHON_VERSION} is accepted (the floor is ${CONST_PYTHON_FLOOR}) but newer than the tested range ${CONST_PYTHON_FLOOR}-${CONST_PYTHON_TESTED_MAX}. Every pinned package publishes wheels for it, so it is expected to work; it has not been run."
    else
        Log INFO "Python ${PYTHON_VERSION} is within the accepted range: ${CONST_PYTHON_FLOOR} or newer, tested ${CONST_PYTHON_FLOOR}-${CONST_PYTHON_TESTED_MAX}."
    fi
}

# ---- 2: platform and hardware ----------------------------------------------

Detect_Platform() {
    # Description:
    #   Identify the OS and hardware and choose the MLX backend and the PyTorch build.
    #   Stops, with the reason, on anything unsupported. Sets PLATFORM_OS, PLATFORM_SUMMARY,
    #   MLX_BACKEND and TORCH_INDEX.

    local os
    os="$(uname -s)"
    case "${os}" in
        Darwin) Detect_Macos ;;
        Linux)  Detect_Linux ;;
        *)      Die "This installer supports macOS (Apple silicon) and Linux; this system reports '${os}'." \
                    "Windows is not a target (README > Platform). Install manually per README > Setup if you want to try it." ;;
    esac
}

Detect_Macos() {
    # Description:
    #   macOS: Apple silicon or stop. hw.optional.arm64 is asked rather than uname -m,
    #   because a shell running under Rosetta reports x86_64 on an Apple-silicon Mac.

    local arm64 chip version
    arm64="$(sysctl -n hw.optional.arm64 2>/dev/null || true)"
    if [ "${arm64}" != '1' ]; then
        Die 'Detected macOS on an Intel processor, which is unsupported: the describer runs on MLX, and MLX needs Apple silicon.' \
            'Run AnyScan on an Apple-silicon Mac (M1 or newer) or on Linux; see README > Platform.'
    fi
    if [ "${CPU_OPT_IN}" = '1' ]; then
        Log WARNING '--cpu applies to Linux only; ignored on macOS, where the describer runs on the Apple GPU.'
    fi
    chip="$(sysctl -n machdep.cpu.brand_string 2>/dev/null || true)"
    version="$(sw_vers -productVersion 2>/dev/null || true)"
    Log INFO "Detected macOS ${version:-(unknown version)} on Apple silicon (${chip:-unknown chip})."
    if ! Version_Ge "${version:-0}" "${CONST_MACOS_MIN}"; then
        Die "macOS ${CONST_MACOS_MIN} or newer is required; this is ${version:-an unknown version}. The mlx wheels are built for macOS ${CONST_MACOS_MIN}+." \
            "Update macOS and re-run ./install.sh."
    fi
    PLATFORM_OS='macos'
    MLX_BACKEND='metal'
    TORCH_INDEX=''
    PLATFORM_SUMMARY="macOS ${version} on Apple silicon (${chip:-unknown chip})"
    Log INFO 'Selected MLX with the Metal backend, and the standard PyTorch build (Apple GPU through MPS).'
}

Detect_Linux() {
    # Description:
    #   Linux: x86_64 with glibc new enough for the mlx wheels, then the GPU.

    local arch glibc
    arch="$(uname -m)"
    case "${arch}" in
        x86_64|amd64) ;;
        aarch64|arm64)
            Die "Detected Linux on ${arch}, which this installer does not support: PyQt5 5.15.11 (the UI) publishes no Linux ${arch} wheel, so pip would try to build Qt from source - a long build that fails without a full Qt toolchain." \
                'Supporting it would need either PyQt5 from the distribution (e.g. apt install python3-pyqt5, with the venv created using --system-site-packages) or a port of the UI to PyQt6, which publishes Linux aarch64 wheels (glibc 2.39+). mlx and torch already have aarch64 wheels. Until then, use Linux x86_64 or an Apple-silicon Mac.' ;;
        *)
            Die "Detected Linux on ${arch}, which is unsupported: mlx publishes Linux wheels for x86_64 and aarch64 only." \
                'Use Linux x86_64 or an Apple-silicon Mac.' ;;
    esac
    glibc="$(getconf GNU_LIBC_VERSION 2>/dev/null | awk '{ print $2 }' || true)"
    if [ -z "${glibc}" ]; then
        Die 'Detected Linux x86_64 without glibc (musl, e.g. Alpine): mlx publishes glibc wheels only.' \
            "Use a glibc distribution with glibc ${CONST_GLIBC_MIN}+ (e.g. Ubuntu 22.04 or newer)."
    fi
    Log INFO "Detected Linux x86_64 with glibc ${glibc}."
    if ! Version_Ge "${glibc}" "${CONST_GLIBC_MIN}"; then
        Die "glibc ${CONST_GLIBC_MIN} or newer is required; this system has ${glibc}. The mlx Linux wheels are built for manylinux_2_35." \
            "Use a newer distribution (e.g. Ubuntu 22.04 or newer, Debian 12 or newer)."
    fi
    PLATFORM_OS='linux'
    Detect_Nvidia
    PLATFORM_SUMMARY="Linux x86_64 (glibc ${glibc}), MLX backend ${MLX_BACKEND}, PyTorch ${TORCH_INDEX}"
}

Select_Cpu_Backend() {
    # Description:
    #   The Linux CPU path, taken only with --cpu: CPU builds of both MLX and PyTorch, with the
    #   warning that the describer will be slow.
    #
    # Args:
    #   (1) reason [string]: Why the GPU path was not taken, for the warning.

    MLX_BACKEND='cpu'
    TORCH_INDEX='cpu'
    Log WARNING "$1; installing the CPU builds of MLX and PyTorch, as --cpu asks. Inference will be slow: the describer takes 2.22 s per object on the Apple GPU, and on a CPU it is unmeasured and expected to be far slower."
}

No_Usable_Gpu() {
    # Description:
    #   No NVIDIA GPU the application can use. Without --cpu, stop and say why: a silent CPU
    #   install succeeds and then leaves the operator with inference too slow to use, not
    #   knowing why. With --cpu, take the CPU path.
    #
    # Args:
    #   (1) reason [string]: What was found.

    if [ "${CPU_OPT_IN}" = '1' ]; then
        Select_Cpu_Backend "$1"
        return 0
    fi
    Die "$1. AnyScan on Linux needs an NVIDIA GPU with at least $(( CONST_MIN_VRAM_MIB / 1024 )) GB of memory (compute capability ${CONST_MLX_CUDA_MIN_COMPUTE_CAP} or newer, driver ${CONST_MLX_CUDA12_MIN_DRIVER} or newer)." \
        'To install the CPU builds anyway, re-run with --cpu: the describer is unmeasured on a CPU and expected to be far slower.'
}

Mib_To_Gb() {
    # Description:
    #   A MiB count as GB with one decimal, for messages (16303 -> 15.9).
    #
    # Args:
    #   (1) mib [int]: The count.
    #
    # Returns:
    #   (1) parameter [string]: The value, on stdout.

    awk -v m="$1" 'BEGIN { printf "%.1f", m / 1024 }'
}

Detect_Nvidia() {
    # Description:
    #   Decide the GPU path from a working driver and the card itself, not from a device file:
    #   nvidia-smi must exist, run, and report a driver, a compute capability and the memory of
    #   GPU 0 - the device MLX and PyTorch use. Anything short of a usable card stops (or, with
    #   --cpu, takes the CPU path), naming what was found.
    #     driver >= 580                       -> mlx[cuda13] + torch cu130
    #     550.54.14 <= driver < 580           -> mlx[cuda12] + torch cu126
    #     GPU 0 below CONST_MIN_VRAM_MIB,
    #     older driver, compute cap. < 7.5,
    #     or nvidia-smi missing / failing     -> stop; with --cpu, mlx[cpu] + torch cpu

    local query first name driver count cuda cap memory total used required
    if ! command -v nvidia-smi >/dev/null 2>&1; then
        No_Usable_Gpu 'No NVIDIA driver found (nvidia-smi is not installed)'
        return 0
    fi
    if ! query="$(nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>&1)"; then
        No_Usable_Gpu "nvidia-smi is installed but failed ($(printf '%s\n' "${query}" | head -n 1)), so no GPU is usable"
        return 0
    fi
    first="$(printf '%s\n' "${query}" | head -n 1)"
    case "${first}" in
        *,*) ;;
        *) No_Usable_Gpu "nvidia-smi reported no GPU (${first:-empty output})"
           return 0 ;;
    esac
    name="${first%,*}"
    driver="$(printf '%s' "${first##*,}" | tr -d ' ')"
    count="$(printf '%s\n' "${query}" | grep -c ',')"
    cuda="$(nvidia-smi 2>/dev/null | sed -n 's/.*CUDA Version: *\([0-9][0-9.]*\).*/\1/p' | head -n 1 || true)"
    if [ "${count}" -gt 1 ]; then
        Log INFO "Detected NVIDIA driver ${driver} (CUDA ${cuda:-version not reported}) with ${count} GPUs; MLX uses the first, ${name}."
    else
        Log INFO "Detected NVIDIA driver ${driver} (CUDA ${cuda:-version not reported}) on ${name}."
    fi
    if ! Version_Ge "${driver}" "${CONST_MLX_CUDA12_MIN_DRIVER}"; then
        No_Usable_Gpu "NVIDIA driver ${driver} is older than ${CONST_MLX_CUDA12_MIN_DRIVER}, the minimum for MLX's CUDA backend (updating the driver enables the GPU path)"
        return 0
    fi
    cap="$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | head -n 1 | tr -d ' ' || true)"
    case "${cap}" in
        [0-9]*.[0-9]*) ;;
        *) No_Usable_Gpu "nvidia-smi did not report the GPU's compute capability (${cap:-no output})"
           return 0 ;;
    esac
    if ! Version_Ge "${cap}" "${CONST_MLX_CUDA_MIN_COMPUTE_CAP}"; then
        No_Usable_Gpu "${name} has compute capability ${cap}; MLX's CUDA backend needs ${CONST_MLX_CUDA_MIN_COMPUTE_CAP} or newer (Turing and later)"
        return 0
    fi
    # The card's memory: what decides whether the model fits, which the driver version cannot say.
    memory="$(nvidia-smi --query-gpu=memory.total,memory.used --format=csv,noheader,nounits 2>/dev/null | head -n 1 | tr -d ' ' || true)"
    total="${memory%%,*}"
    used="${memory##*,}"
    case "${total}:${used}" in
        [0-9]*:[0-9]*) ;;
        *) No_Usable_Gpu "nvidia-smi did not report ${name}'s memory (${memory:-no output})"
           return 0 ;;
    esac
    GPU_MEMORY_MIB="${total}"
    Log INFO "${name} has $(Mib_To_Gb "${total}") GB of memory (${total} MiB), $(Mib_To_Gb "${used}") GB of it in use now; compute capability ${cap}."
    if [ "${total}" -lt "${CONST_MIN_VRAM_MIB}" ]; then
        No_Usable_Gpu "${name} has $(Mib_To_Gb "${total}") GB of memory; the describer (Gemma 4 E4B) and FastSAM together peaked at 9.5 GB when measured, so ${CONST_MIN_VRAM_MIB} MiB ($(( CONST_MIN_VRAM_MIB / 1024 )) GB) is the minimum"
        return 0
    fi
    if [ "${used}" -gt "${CONST_BUSY_VRAM_MIB}" ]; then
        Log WARNING "${name} already has $(Mib_To_Gb "${used}") GB in use (a display or another process); the application's estimated peak comes on top of that, so free what you can before running it."
    fi
    if Version_Ge "${driver}" "${CONST_MLX_CUDA13_MIN_DRIVER}"; then
        MLX_BACKEND='cuda13'
        TORCH_INDEX='cu130'
        Log INFO "Selected MLX with the CUDA 13 backend (mlx[cuda13]) and the PyTorch cu130 build: driver ${driver} is ${CONST_MLX_CUDA13_MIN_DRIVER} or newer, compute capability ${cap}."
    else
        MLX_BACKEND='cuda12'
        TORCH_INDEX='cu126'
        Log INFO "Selected MLX with the CUDA 12 backend (mlx[cuda12]) and the PyTorch cu126 build: driver ${driver} is below ${CONST_MLX_CUDA13_MIN_DRIVER} (needed for CUDA 13), compute capability ${cap}."
    fi
    if [ "${CPU_OPT_IN}" = '1' ]; then
        Log WARNING '--cpu was given but has no effect here: a usable GPU was found, so the GPU builds are installed. --cpu only allows the CPU path when no usable GPU is found.'
    fi
}

Check_Python_Architecture() {
    # Description:
    #   On Apple silicon the interpreter itself must be arm64. An x86_64 Python (Rosetta)
    #   evaluates requirements.txt's arm64 markers as false and silently skips MLX, leaving
    #   a setup that looks complete and fails at the first description.

    local machine
    [ "${PLATFORM_OS}" = 'macos' ] || return 0
    machine="$("${BASE_PYTHON}" -c 'import platform; print(platform.machine())' 2>/dev/null || true)"
    if [ "${machine}" != 'arm64' ]; then
        Die "Python ${PYTHON_VERSION} (${BASE_PYTHON}) is an ${machine:-unknown}-architecture build running under Rosetta; MLX needs a native arm64 Python." \
            "Install an arm64 Python (python.org's universal2 installer, or Homebrew in /opt/homebrew) and re-run with PYTHON=/path/to/it; remove .venv first if it was created from this one."
    fi
}

Selected_Model() {
    # Description:
    #   The describer model: sets MODEL_NAME, MODEL_REPO, MODEL_REVISION, MODEL_REL and
    #   MODEL_FILES from the constants. Read at the point of use, so a test can override a
    #   constant first.

    MODEL_NAME='Gemma 4 E4B'
    MODEL_REPO="${CONST_GEMMA_REPO}"
    MODEL_REVISION="${CONST_GEMMA_REVISION}"
    MODEL_REL="${CONST_GEMMA_REL}"
    MODEL_FILES="${CONST_GEMMA_FILES}"
}

Manifest_Bytes() {
    # Description:
    #   The total size of a manifest's files.
    #
    # Args:
    #   (1) manifest [string]: 'name size kind hash' lines.
    #
    # Returns:
    #   (1) parameter [int]: The byte count, on stdout.

    printf '%s\n' "$1" | awk 'NF == 4 { total += $2 } END { printf "%d", total }'
}

Report_Plan() {
    # Description:
    #   Say what is about to be installed and downloaded, before any of it happens.

    local mlx_line torch_line
    case "${MLX_BACKEND}" in
        metal) mlx_line='mlx + mlx-vlm (Metal) from requirements.txt' ;;
        *)     mlx_line="mlx + mlx-vlm from requirements.txt, backend mlx[${MLX_BACKEND}] from requirements/linux-${MLX_BACKEND}.txt" ;;
    esac
    if [ -n "${TORCH_INDEX}" ]; then
        torch_line="torch + torchvision from ${CONST_TORCH_INDEX_BASE}/${TORCH_INDEX}"
    else
        torch_line='torch + torchvision from PyPI'
    fi
    Log INFO "Plan: virtual environment .venv (Python ${PYTHON_VERSION}); ${mlx_line}; ${torch_line}; the rest of requirements.txt."
    Selected_Model
    Log INFO "Plan: FastSAM-x -> ${CONST_FASTSAM_REL} ($(Format_Size "${CONST_FASTSAM_SIZE}")); ${MODEL_NAME}, ${MODEL_REPO}@${MODEL_REVISION:0:7} -> ${MODEL_REL} ($(Format_Size "$(Manifest_Bytes "${MODEL_FILES}")")). Each is skipped if already present and verified."
}

# ---- 3: virtual environment ------------------------------------------------

Ensure_Venv() {
    # Description:
    #   Create .venv if it does not exist, then confirm it really is a virtual environment
    #   (sys.prefix differs from sys.base_prefix). Nothing is ever installed into the system
    #   Python: every later pip call goes through .venv/bin/python.

    local is_venv
    if [ -n "${VIRTUAL_ENV:-}" ] && [ "${VIRTUAL_ENV}" != "${CONST_VENV_DIR}" ]; then
        Log INFO "Ignoring the active environment ${VIRTUAL_ENV}; the project installs into .venv only."
    fi
    if [ -x "${CONST_VENV_DIR}/bin/python" ]; then
        Log INFO 'The virtual environment .venv already exists; reusing it.'
    else
        if ! "${BASE_PYTHON}" -c 'import venv, ensurepip' >/dev/null 2>&1; then
            Die "Python ${PYTHON_VERSION} (${BASE_PYTHON}) cannot create virtual environments: its venv/ensurepip modules are missing." \
                "On Debian/Ubuntu install them (sudo apt install python${PYTHON_VERSION%.*}-venv) and re-run ./install.sh."
        fi
        Log INFO "Creating the virtual environment .venv from ${BASE_PYTHON}."
        "${BASE_PYTHON}" -m venv "${CONST_VENV_DIR}" || \
            Die "Creating .venv failed (see the message above)." "Remove any partial .venv (rm -rf .venv) and re-run ./install.sh."
    fi
    is_venv="$("${CONST_VENV_DIR}/bin/python" -c 'import sys; print(sys.prefix != sys.base_prefix)' 2>/dev/null || true)"
    if [ "${is_venv}" != 'True' ]; then
        Die "${CONST_VENV_DIR}/bin/python is not a virtual-environment interpreter (it reports the system prefix); refusing to install into a system Python." \
            'Remove .venv (rm -rf .venv) and re-run ./install.sh so it is created as a proper virtual environment.'
    fi
}

# ---- 4: dependencies -------------------------------------------------------

Run_Pip() {
    # Description:
    #   Run pip inside .venv, quietly, keeping its output in a temporary file. On failure
    #   the tail of that output is logged as ERROR lines, so the cause is visible without a
    #   screen of 'Requirement already satisfied'.
    #
    # Args:
    #   (1..n) arguments [string]: The pip arguments.
    #
    # Returns:
    #   (1) parameter [status]: pip's exit status.

    local output status=0 line
    output="$(mktemp "${TMPDIR:-/tmp}/anyscan-pip.XXXXXX")"
    "${CONST_VENV_DIR}/bin/python" -m pip "$@" --disable-pip-version-check --quiet >"${output}" 2>&1 || status=$?
    if [ "${status}" -ne 0 ]; then
        while IFS= read -r line; do
            Log ERROR "  pip: ${line}"
        done < <(tail -n 25 "${output}")
    fi
    rm -f "${output}"
    return "${status}"
}

Installed_Version() {
    # Description:
    #   The installed version of a distribution in .venv.
    #
    # Args:
    #   (1) name [string]: The distribution name.
    #
    # Returns:
    #   (1) parameter [string]: The version on stdout; empty when not installed.

    "${CONST_VENV_DIR}/bin/python" -c 'import sys, importlib.metadata as m
try:
    print(m.version(sys.argv[1]))
except m.PackageNotFoundError:
    pass' "$1" 2>/dev/null || true
}

Ensure_Torch_Build() {
    # Description:
    #   Linux only: install torch and torchvision from the PyTorch index for the detected
    #   backend, before requirements.txt, so that pip then sees torch satisfied and never
    #   pulls PyPI's default build (CUDA 13 on Linux - several GB of libraries a CPU machine
    #   cannot use and a pre-580 driver cannot load). A torch of the wrong build (e.g. after a
    #   driver change) is uninstalled first, so the right one replaces it.

    local installed start
    [ -n "${TORCH_INDEX}" ] || return 0
    installed="$(Installed_Version torch)"
    case "${installed}" in
        *"+${TORCH_INDEX}")
            Log INFO "PyTorch ${installed} is already installed - the ${TORCH_INDEX} build this machine needs."
            return 0 ;;
        '') ;;
        *)
            Log WARNING "PyTorch ${installed} is installed, but this machine needs the +${TORCH_INDEX} build; replacing torch and torchvision."
            Run_Pip uninstall --yes torch torchvision || \
                Die 'Uninstalling the mismatched PyTorch failed (pip output above).' 'Re-run ./install.sh; if it fails again, remove .venv (rm -rf .venv) and re-run.' ;;
    esac
    Log INFO "Installing torch + torchvision from ${CONST_TORCH_INDEX_BASE}/${TORCH_INDEX}; the CUDA builds are several GB, so this can take minutes."
    start="${SECONDS}"
    Run_Pip install torch torchvision --index-url "${CONST_TORCH_INDEX_BASE}/${TORCH_INDEX}" || \
        Die "Installing PyTorch from ${CONST_TORCH_INDEX_BASE}/${TORCH_INDEX} failed (pip output above)." \
            'Check the network connection and free disk space, then re-run ./install.sh.'
    Log INFO "Installed PyTorch $(Installed_Version torch) in $(( SECONDS - start )) s."
}

Install_Dependencies() {
    # Description:
    #   Install requirements.txt (plus the Linux backend file) into .venv and report whether
    #   anything changed, by comparing 'pip freeze' before and after. On a second run nothing
    #   changes and it says so.

    local before after changed start
    local -a requirement_args
    requirement_args=(-r "${CONST_REQUIREMENTS}")
    if [ "${PLATFORM_OS}" = 'linux' ]; then
        requirement_args+=(-r "${CONST_REQUIREMENTS_DIR}/linux-${MLX_BACKEND}.txt")
    fi
    before="$(mktemp "${TMPDIR:-/tmp}/anyscan-freeze.XXXXXX")"
    after="$(mktemp "${TMPDIR:-/tmp}/anyscan-freeze.XXXXXX")"
    "${CONST_VENV_DIR}/bin/python" -m pip freeze --disable-pip-version-check > "${before}" 2>/dev/null || true

    Ensure_Torch_Build
    if [ "${PLATFORM_OS}" = 'linux' ]; then
        Log INFO "Installing requirements.txt + requirements/linux-${MLX_BACKEND}.txt into .venv."
    else
        Log INFO 'Installing requirements.txt into .venv.'
    fi
    start="${SECONDS}"
    Run_Pip install "${requirement_args[@]}" || \
        Die 'Installing the requirements failed (pip output above).' \
            'Fix the cause pip names (network, disk space, a missing system library), then re-run ./install.sh; what is already installed is kept.'

    "${CONST_VENV_DIR}/bin/python" -m pip freeze --disable-pip-version-check > "${after}" 2>/dev/null || true
    changed="$(diff "${before}" "${after}" | grep -c '^>' || true)"
    rm -f "${before}" "${after}"
    if [ "${changed}" -eq 0 ]; then
        Log INFO "Dependencies already in place; pip changed nothing ($(( SECONDS - start )) s)."
    else
        Log INFO "Installed or updated ${changed} packages in $(( SECONDS - start )) s."
    fi
}

Verify_Imports() {
    # Description:
    #   Import what the application imports and report the devices MLX and PyTorch see, so a
    #   broken install fails here, with a message, rather than at the first ANALYZE. A GPU
    #   path whose libraries import but see no GPU is a warning: the software is installed,
    #   the hardware is not usable.

    local report mlx_device torch_line start
    Log INFO 'Checking that PyQt5, OpenCV, MLX, mlx-vlm, PyTorch and ultralytics import.'
    start="${SECONDS}"
    report="$("${CONST_VENV_DIR}/bin/python" - 2>&1 <<'PY'
import PyQt5.QtCore, cv2, ultralytics, mlx_vlm
import mlx.core as mx
import torch
print('MLX', mx.default_device())
print('TORCH', torch.__version__, 'cuda' if torch.cuda.is_available() else ('mps' if torch.backends.mps.is_available() else 'cpu'))
PY
)" || Die 'An import failed after installation:' "$(printf '%s\n' "${report}" | tail -n 1)" \
          'Re-run ./install.sh; if the same import fails, remove .venv (rm -rf .venv) and re-run.'
    mlx_device="$(printf '%s\n' "${report}" | sed -n 's/^MLX //p')"
    torch_line="$(printf '%s\n' "${report}" | sed -n 's/^TORCH //p')"
    Log INFO "Imports work ($(( SECONDS - start )) s). MLX device: ${mlx_device}; PyTorch ${torch_line%% *} on ${torch_line##* }."
    case "${MLX_BACKEND}" in
        metal|cuda12|cuda13)
            case "${mlx_device}" in
                *gpu*) ;;
                *) Log WARNING "MLX was installed for the ${MLX_BACKEND} GPU backend but reports ${mlx_device}; the describer will run on the CPU." ;;
            esac
            case "${torch_line##* }" in
                cpu) Log WARNING 'PyTorch sees no GPU; FastSAM will run on the CPU.' ;;
            esac ;;
    esac
}

# ---- 5: models -------------------------------------------------------------

Ensure_Fastsam() {
    # Description:
    #   FastSAM-x: skip when present and matching the published SHA-256; otherwise download
    #   to a .part file, verify that, and only then move it into place, so a failed or
    #   corrupt download never replaces anything or looks complete.

    local path="${CONST_ROOT}/${CONST_FASTSAM_REL}" part status=0 progress='--silent'
    Log INFO "Checking FastSAM-x at ${CONST_FASTSAM_REL}."
    Verify_File "${path}" "${CONST_FASTSAM_SIZE}" sha256 "${CONST_FASTSAM_SHA256}" || status=$?
    if [ "${status}" -eq 0 ]; then
        Log INFO 'FastSAM-x is already present and matches the published SHA-256; not downloading.'
        return 0
    fi
    if [ "${status}" -eq 1 ]; then
        Log INFO "FastSAM-x is missing; downloading it ($(Format_Size "${CONST_FASTSAM_SIZE}")) from ${CONST_FASTSAM_URL}."
    else
        Log WARNING "FastSAM-x is $(Describe_Verify_Status "${status}"); downloading it again."
    fi
    command -v curl >/dev/null 2>&1 || \
        Die 'curl is needed to download FastSAM-x and is not installed.' 'Install curl (e.g. sudo apt install curl) and re-run ./install.sh.'
    mkdir -p "$(dirname "${path}")"
    Ensure_Free_Space "$(dirname "${path}")" "${CONST_FASTSAM_SIZE}"
    part="${path}.part"
    rm -f "${part}"
    [ -t 1 ] && progress='--progress-bar'
    if ! curl --fail --location --retry 3 "${progress}" --show-error --output "${part}" "${CONST_FASTSAM_URL}"; then
        rm -f "${part}"
        Die "Downloading FastSAM-x from ${CONST_FASTSAM_URL} failed (curl's message is above)." \
            'Check the network connection and re-run ./install.sh.'
    fi
    status=0
    Verify_File "${part}" "${CONST_FASTSAM_SIZE}" sha256 "${CONST_FASTSAM_SHA256}" || status=$?
    if [ "${status}" -ne 0 ]; then
        rm -f "${part}"
        Die "The downloaded FastSAM-x is $(Describe_Verify_Status "${status}"); it was discarded and nothing was replaced." \
            "Re-run ./install.sh. If it fails again, the release asset has changed: compare ${CONST_FASTSAM_URL} with CONST_FASTSAM_SHA256 in install.sh."
    fi
    mv -f "${part}" "${path}"
    Log INFO 'Downloaded FastSAM-x and verified its SHA-256.'
}

Ensure_Gemma() {
    # Description:
    #   Gemma: verify every published file of the pinned revision; skip entirely when all
    #   match. Otherwise fetch only the missing or mismatched files with the Hugging Face
    #   CLI (--force-download, so a corrupt local file is not kept by hf's own cache check),
    #   then verify them again. Reports the elapsed time, since hashing 5.1 GB takes a while.

    local directory name size kind hash status
    local failing='' failing_bytes=0 start total_start quiet
    local -a failing_files
    Selected_Model
    directory="${CONST_ROOT}/${MODEL_REL}"
    Log INFO "Checking ${MODEL_NAME} at ${MODEL_REL} against ${MODEL_REPO}@${MODEL_REVISION:0:7} ($(printf '%s\n' "${MODEL_FILES}" | grep -c .) files)."
    total_start="${SECONDS}"
    while read -r name size kind hash; do
        [ -n "${name}" ] || continue
        status=0
        Verify_File "${directory}/${name}" "${size}" "${kind}" "${hash}" || status=$?
        if [ "${status}" -ne 0 ]; then
            if [ "${status}" -ne 1 ]; then
                Log WARNING "Gemma file ${name} is $(Describe_Verify_Status "${status}")."
            fi
            failing="${failing} ${name}"
            failing_bytes=$(( failing_bytes + size ))
        fi
    done <<< "${MODEL_FILES}"
    if [ -z "${failing}" ]; then
        Log INFO "${MODEL_NAME} is already present and every file matches the published hashes (checked in $(( SECONDS - total_start )) s); not downloading."
        return 0
    fi

    read -r -a failing_files <<< "${failing}"
    Log INFO "Downloading ${#failing_files[@]} ${MODEL_NAME} file(s) ($(Format_Size "${failing_bytes}")):${failing}."
    [ -x "${CONST_VENV_DIR}/bin/hf" ] || \
        Die 'The Hugging Face CLI (hf) is missing from .venv; it comes from huggingface_hub in requirements.txt.' 'Re-run ./install.sh so the requirements install completes.'
    mkdir -p "${directory}"
    Ensure_Free_Space "${directory}" "${failing_bytes}"
    start="${SECONDS}"
    status=0
    # hf's progress bars only on a terminal; in a log they are noise. An unquoted, possibly empty
    # word rather than an array: bash 3.2 (macOS) under nounset rejects an empty array expansion.
    quiet='HF_HUB_DISABLE_PROGRESS_BARS=1'
    [ -t 1 ] && quiet=''
    env ${quiet} "${CONST_VENV_DIR}/bin/hf" download "${MODEL_REPO}" "${failing_files[@]}" \
        --revision "${MODEL_REVISION}" --local-dir "${directory}" --force-download >/dev/null || status=$?
    if [ "${status}" -ne 0 ]; then
        Die "Downloading Gemma from ${MODEL_REPO} failed (hf's message is above)." \
            'Check the network connection and re-run ./install.sh; files already verified are kept.'
    fi
    Log INFO "Downloaded in $(( SECONDS - start )) s; verifying."
    while read -r name size kind hash; do
        case " ${failing} " in *" ${name} "*) ;; *) continue ;; esac
        status=0
        Verify_File "${directory}/${name}" "${size}" "${kind}" "${hash}" || status=$?
        if [ "${status}" -ne 0 ]; then
            Die "After downloading, Gemma file ${name} is $(Describe_Verify_Status "${status}")." \
                "Re-run ./install.sh. If it fails again, the revision no longer serves the published file: compare ${MODEL_REPO}@${MODEL_REVISION} with MODEL_FILES in install.sh."
        fi
    done <<< "${MODEL_FILES}"
    Log INFO "${MODEL_NAME} downloaded and every file verified ($(( SECONDS - total_start )) s in total)."
}

# ---- 6: configurations -----------------------------------------------------

Check_Configurations() {
    # Description:
    #   Every Configuration/Config_*.yaml names its model files. If one does not point at
    #   what this script installed, the setup looks complete and fails at load - so name the
    #   file, the field and the value to change it to. The installed models are the same on
    #   every platform, so a mismatch means an edited configuration, not a platform difference.

    local file field value verdict expected report
    Selected_Model
    report="$("${CONST_VENV_DIR}/bin/python" - "${CONST_ROOT}" "${CONST_FASTSAM_REL}" "${MODEL_REL}" 2>&1 <<'PY'
import glob, os, sys
import yaml
root, fastsam, gemma = sys.argv[1:4]
for path in sorted(glob.glob(os.path.join(root, 'Configuration', 'Config_*.yaml'))):
    with open(path) as handle:
        data = yaml.safe_load(handle) or {}
    for section, expected in (('Segmentation', fastsam), ('Description', gemma)):
        value = (data.get(section) or {}).get('Model')
        resolved = value if value is None or os.path.isabs(str(value)) else os.path.join(root, str(value))
        same = value is not None and os.path.realpath(resolved) == os.path.realpath(os.path.join(root, expected))
        verdict = 'ok' if same else ('elsewhere' if value is not None and os.path.exists(resolved) else 'missing')
        print('\t'.join([os.path.basename(path), section + '.Model', str(value), verdict]))
PY
)" || Die 'Reading the configurations in Configuration/ failed:' "$(printf '%s\n' "${report}" | tail -n 1)" \
          'Fix the YAML file it names (the application would fail to load it too), then re-run ./install.sh.'
    if [ -z "${report}" ]; then
        Log WARNING 'No Configuration/Config_*.yaml found; the application needs one to load the models.'
        return 0
    fi
    while IFS="$(printf '\t')" read -r file field value verdict; do
        [ -n "${file}" ] || continue
        if [ "${verdict}" = 'ok' ]; then
            Log INFO "Configuration ${file}: ${field} points at the installed model (${value})."
        else
            case "${field}" in
                Segmentation.Model) expected="${CONST_FASTSAM_REL}" ;;
                *)                  expected="${MODEL_REL}" ;;
            esac
            if [ "${verdict}" = 'elsewhere' ]; then
                # Another model that is on disk (a directory the configuration was edited to name):
                # the configuration still loads, just not the model this run installed. The installer never
                # edits a configuration; it names the field.
                Log WARNING "Configuration ${file}: ${field} is '${value}', not the model this run installed. To use ${MODEL_NAME}, set ${field} to ${expected} in Configuration/${file} (the installer does not edit configurations)."
            else
                Log WARNING "Configuration ${file}: ${field} is '${value}', but this installer put that model at ${expected}. Change ${field} to ${expected}, or the application will fail when it loads the model."
            fi
        fi
    done <<< "${report}"
}

# ---- main ------------------------------------------------------------------

Parse_Arguments() {
    # Description:
    #   Read the command line.
    #
    # Args:
    #   (1..n) arguments [string]: The script's arguments.

    while [ "$#" -gt 0 ]; do
        case "$1" in
            --detect-only) DETECT_ONLY='1' ;;
            --cpu) CPU_OPT_IN='1' ;;
            -h|--help)
                awk 'NR > 24 && /^#/ { sub(/^# ?/, ""); print; next } NR > 24 { exit }' "${BASH_SOURCE[0]}"
                exit 0 ;;
            *) Die "Unknown argument '$1'." 'Run ./install.sh --help for the options.' ;;
        esac
        shift
    done
}

Report_Unused_Cpu_Flag() {
    # Description:
    #   The last word on a --cpu that did not take effect (a usable GPU was found): someone who
    #   passed it on purpose - testing, or working around a driver problem - must not leave the
    #   install believing the CPU builds are in place. Said at detection too; repeated at the end
    #   because a long run scrolls that away.

    if [ "${CPU_OPT_IN}" = '1' ] && [ "${PLATFORM_OS}" = 'linux' ] && [ "${MLX_BACKEND}" != 'cpu' ]; then
        Log WARNING "--cpu had no effect: the ${MLX_BACKEND} GPU builds were installed."
    fi
}

Main() {
    # Description:
    #   Run the steps, cheapest failure first. Each step reports what it found before it acts.
    #
    # Args:
    #   (1..n) arguments [string]: The script's arguments.

    local start="${SECONDS}"
    set -o errexit -o nounset -o pipefail -o errtrace
    trap 'On_Unexpected_Error "${LINENO}" "${BASH_COMMAND}"' ERR
    trap On_Interrupt INT TERM
    Parse_Arguments "$@"
    cd "${CONST_ROOT}"
    Log INFO "AnyScan installer, in ${CONST_ROOT}."

    Select_Python
    Detect_Platform
    Check_Python_Architecture
    Report_Plan
    if [ "${DETECT_ONLY}" = '1' ]; then
        Log INFO 'Detection only (--detect-only): nothing was changed.'
        return 0
    fi

    Ensure_Venv
    Install_Dependencies
    Verify_Imports
    Ensure_Fastsam
    Ensure_Gemma
    Check_Configurations

    Log INFO "Setup complete in $(( SECONDS - start )) s: ${PLATFORM_SUMMARY}."
    Report_Unused_Cpu_Flag
    if [ "${PLATFORM_OS}" = 'linux' ]; then
        Log INFO 'Linux was measured on one machine, with the CUDA 13 backend (README > Platform); the CUDA 12 and CPU builds have not been measured.'
    fi
    Log INFO 'Start the application with: .venv/bin/python App/run.py'
}

# Run only when executed, not when sourced (the tests source this file to call single steps).
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    Main "$@"
fi
