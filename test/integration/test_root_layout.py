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
# File Name: ../test/integration/test_root_layout.py
## =========================================================================== ##

# System (Default)
import os
# Subprocess (Subprocess management)
import subprocess
# Typing (Support for type hints)
import typing as tp

"""
Description:
    Initialization of constants.

    The root holds only what is declared (project-style-rpx references/structure.md > The root holds
    only what is declared; this project's exceptions and their reasons are in
    .claude/skills/project-style-rpx/references/project.md > Root). The set is written out here, never
    read from the README or the filesystem it checks; a new root entry changes this set and that
    section in the same commit.
"""
# The entries git tracks at the root.
#   Unit [Set<string>]
CONST_ROOT_ENTRIES = {'.claude', '.gitattributes', '.gitignore', 'App', 'CLAUDE.md', 'Configuration', 'Data',
                      'Example', 'LICENSE', 'README.md', 'images', 'install.sh', 'logger', 'models', 'pytest.ini',
                      'requirements', 'requirements.txt', 'src', 'test'}
# The git-ignored entries the root may hold, each with what puts it there: the virtual environment install.sh
# creates, pytest's cache, Finder's folder metadata on macOS, and the owner's brand sources (/design/ in .gitignore,
# on the development Mac only). Nothing the application or its tools write lands in the root: their output is under
# logger/, Data/, Configuration/Calibration/, App/assets/, images/, models/ or test/crash_records/, or at an absolute
# path a configuration names (project-style-rpx references/project.md > Root).
#   Unit [Set<string>]
CONST_IGNORED_ROOT_ENTRIES = {'.venv', '.pytest_cache', '.DS_Store', 'design'}
# The records, in .claude/project-docs/ (the generic place, with the capture checklist as a fourth, the tracker and
# the support-chat brief), relative to the root.
#   Unit [Tuple<string>]
CONST_RECORDS = ('.claude/project-docs/SPEC.md', '.claude/project-docs/design-decisions.md',
                 '.claude/project-docs/KNOWN_ISSUES.md', '.claude/project-docs/capture-checklist.md',
                 '.claude/project-docs/FEATURES.md', '.claude/project-docs/SUPPORT_CHAT.md')


def _Git_Lines(project_root: str, *arguments: str) -> tp.List[str]:
    """The lines of a git command's output in the repository, the command required to succeed."""
    result = subprocess.run(['git', *arguments], cwd=project_root, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    return result.stdout.splitlines()


def _Root_Entries(paths: tp.List[str]) -> tp.Set[str]:
    """The first path component of each path, as git lists it (a directory with a trailing '/')."""
    return {path.rstrip('/').split('/', 1)[0] for path in paths}


def _Status_Paths(project_root: str, code: str) -> tp.List[str]:
    """The paths git status shows with a code ('??' untracked, '!!' ignored): what a person running it sees."""
    result = subprocess.run(['git', 'status', '--porcelain=v1', '-z', '--untracked-files=normal', '--ignored'],
                            cwd=project_root, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    return [entry[3:] for entry in result.stdout.split('\0') if entry.startswith(code + ' ')]


def test_the_root_holds_only_the_declared_entries(project_root) -> None:
    """
    Description:
        The files git tracks at the root are the declared entries and nothing else.
    """

    entries = _Root_Entries(_Git_Lines(project_root, 'ls-files'))
    assert entries == CONST_ROOT_ENTRIES, 'undeclared: %s; missing: %s' % (sorted(entries - CONST_ROOT_ENTRIES),
                                                                        sorted(CONST_ROOT_ENTRIES - entries))


def test_the_records_are_in_project_docs_and_none_in_docs(project_root) -> None:
    """
    Description:
        The records live where CLAUDE.md and the style project reference say: .claude/project-docs/,
        tracked by git (the .gitignore keeps the rest of .claude/ out). A docs/ folder beside them would
        split the records in two.
    """

    result = subprocess.run(['git', 'ls-files', *CONST_RECORDS], cwd=project_root, capture_output=True, text=True,
                            timeout=60)
    assert result.returncode == 0, result.stderr
    assert sorted(result.stdout.split()) == sorted(CONST_RECORDS)
    assert not os.path.exists(os.path.join(project_root, 'docs'))


def test_the_root_holds_no_untracked_entry(project_root) -> None:
    """
    Description:
        Nothing untracked and not ignored sits at the root, as git status lists it; a test that reads only what
        git tracks cannot see it (a copy of the media archive sat there unnoticed). An untracked file inside a
        declared folder is ordinary work in progress and is not counted. A new root entry is declared first, in
        CONST_ROOT_ENTRIES, and staged.
    """

    untracked = _Root_Entries(_Status_Paths(project_root, '??'))
    assert untracked - CONST_ROOT_ENTRIES == set(), (
        'untracked at the root: %s - commit it as a declared entry, or move it out of the repository'
        % sorted(untracked - CONST_ROOT_ENTRIES))


def test_the_root_holds_only_the_declared_ignored_entries(project_root) -> None:
    """
    Description:
        An ignored entry at the root is one of CONST_IGNORED_ROOT_ENTRIES. An ignore rule would otherwise hide
        clutter from git status as well as from the tracked-entries test; ignored files inside a declared folder
        (models/, logger/, Data/Results/) are that folder's business, not the root's.
    """

    ignored = _Root_Entries(_Status_Paths(project_root, '!!'))
    assert ignored - CONST_ROOT_ENTRIES - CONST_IGNORED_ROOT_ENTRIES == set(), (
        'ignored but undeclared at the root: %s - move it out of the repository, or declare it with its reason in '
        'CONST_IGNORED_ROOT_ENTRIES and project-style-rpx references/project.md > Root'
        % sorted(ignored - CONST_ROOT_ENTRIES - CONST_IGNORED_ROOT_ENTRIES))


def test_no_two_tracked_paths_differ_only_in_letter_case(project_root) -> None:
    """
    Description:
        No two tracked files or folders differ only in letter case: a case-insensitive file system (macOS by
        default) checks out only one of them. Every folder on a tracked path counts as well as the file.
    """

    paths = set()
    for path in _Git_Lines(project_root, 'ls-files'):
        parts = path.split('/')
        paths.update('/'.join(parts[:depth]) for depth in range(1, len(parts) + 1))
    by_folded = {}
    for path in paths:
        by_folded.setdefault(path.casefold(), []).append(path)
    clashes = sorted(sorted(group) for group in by_folded.values() if len(group) > 1)
    assert clashes == [], 'tracked paths that differ only in letter case: %s' % clashes
