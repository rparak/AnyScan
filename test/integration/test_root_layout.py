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
# The records, in .claude/project-docs/ (the generic place, with the capture checklist as a fourth),
# relative to the root.
#   Unit [Tuple<string>]
CONST_RECORDS = ('.claude/project-docs/SPEC.md', '.claude/project-docs/design-decisions.md',
                 '.claude/project-docs/KNOWN_ISSUES.md', '.claude/project-docs/capture-checklist.md')


def test_the_root_holds_only_the_declared_entries(project_root) -> None:
    """
    Description:
        The files git tracks at the root are the declared entries and nothing else.
    """

    result = subprocess.run(['git', 'ls-files'], cwd=project_root, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    entries = {path.split('/', 1)[0] for path in result.stdout.splitlines()}
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
