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
# File Name: ../test/integration/test_support_chat.py
## =========================================================================== ##

# System (Default)
import os
import re
import subprocess
# pytest (A repository without its git history skips the commit check, loudly)
import pytest

"""
Description:
    Initialization of constants.

    .claude/project-docs/SUPPORT_CHAT.md is the brief the owner pastes into a new support chat. These tests hold
    what can be checked: its length against the bound in support-brief's project reference, the commit and date
    its sections 0 and 9 name (the commit in this branch's history), and the test count and times it repeats from
    CLAUDE.md, read from there rather than written here.
"""
# The brief, the skill's project reference that sets its bound, and the file holding the check tiers.
#   Unit [string]
CONST_BRIEF = os.path.join('.claude', 'project-docs', 'SUPPORT_CHAT.md')
CONST_BRIEF_REFERENCE = os.path.join('.claude', 'skills', 'support-brief', 'references', 'project.md')
CONST_CLAUDE_MD = 'CLAUDE.md'

# The brief's bound, counted as `wc -w` counts: runs of non-whitespace. Pinned here and in the project
# reference alike, so the bound cannot be raised in one place unseen.
#   Unit [int]
CONST_WORD_LIMIT = 2500

# Section 0's 'State as of commit `<hash>`, <date>' and section 9's 'Last updated <date>, checked against commit
# `<hash>`'.
#   Unit [Pattern]
CONST_SECTION_0_STAMP = re.compile(r'State as of commit `([0-9a-f]{7,40})`, (\d{4}-\d{2}-\d{2})')
CONST_SECTION_9_STAMP = re.compile(r'Last updated (\d{4}-\d{2}-\d{2}), checked against commit `([0-9a-f]{7,40})`')

# CLAUDE.md's two pytest lines, '... pytest -q   # <n> collected, <t> s' and the same with --runslow.
#   Unit [Pattern]
CONST_DEFAULT_TIER = re.compile(r'pytest -q +# (\d+) collected, (\d+) s')
CONST_SLOW_TIER = re.compile(r'pytest -q --runslow +# (\d+) collected, (\d+) s')


def Read_Text(path: str) -> str:
    """
    Description:
        Read a UTF-8 text file.

    Args:
        (1) path [string]: The file.

    Returns:
        (1) parameter [string]: Its text.
    """

    with open(path, encoding='utf-8') as file:
        return file.read()


def Section(text: str, number: int) -> str:
    """
    Description:
        One numbered '## <n>. …' section of the brief, up to the next '## ' heading.

    Args:
        (1) text [string]: The brief.
        (2) number [int]: The section's number.

    Returns:
        (1) parameter [string]: The section, empty when the brief has no such heading.
    """

    match = re.search(r'^## %d\. .*?(?=^## |\Z)' % number, text, re.M | re.S)
    return match.group(0) if match else ''


def test_the_brief_stays_within_its_word_limit(project_root) -> None:
    """
    Description:
        The brief is at most CONST_WORD_LIMIT words by `wc -w`, and support-brief's project reference states the
        same bound, so a longer brief is trimmed rather than the bound raised.
    """

    words = len(Read_Text(os.path.join(project_root, CONST_BRIEF)).split())
    reference = Read_Text(os.path.join(project_root, CONST_BRIEF_REFERENCE))
    assert '**At most {:,} words**'.format(CONST_WORD_LIMIT) in reference, (
        "support-brief's project reference no longer states the %d-word bound this test pins." % CONST_WORD_LIMIT)
    assert words <= CONST_WORD_LIMIT, ('%s has %d words by wc -w, over its bound of %d: trim sections 3 and 7 first, '
                                       'never raise the bound.' % (CONST_BRIEF, words, CONST_WORD_LIMIT))


def test_sections_0_and_9_name_the_same_commit_and_date(project_root) -> None:
    """
    Description:
        Section 0 says the state is as of a commit and a date, and section 9 says the brief was checked against
        a commit on a date. Both name the same commit and the same date.
    """

    text = Read_Text(os.path.join(project_root, CONST_BRIEF))
    head = CONST_SECTION_0_STAMP.search(Section(text, 0))
    tail = CONST_SECTION_9_STAMP.search(Section(text, 9))
    assert head, "Section 0 has no 'State as of commit `<hash>`, <YYYY-MM-DD>'."
    assert tail, "Section 9 has no 'Last updated <YYYY-MM-DD>, checked against commit `<hash>`'."
    assert (head.group(1), head.group(2)) == (tail.group(2), tail.group(1)), (
        'Section 0 names %s, %s and section 9 names %s, %s.' % (head.group(1), head.group(2),
                                                                 tail.group(2), tail.group(1)))


def test_the_named_commit_is_in_this_branchs_history(project_root) -> None:
    """
    Description:
        The commit the brief names exists and is an ancestor of HEAD, so a REFRESH can survey from it. A
        repository copied without its git history skips the check, naming why.
    """

    if subprocess.run(['git', 'rev-parse', '--git-dir'], cwd=project_root, capture_output=True,
                      timeout=60).returncode != 0:
        pytest.skip('COMMIT CHECK NOT RUN: %s is not a git repository.' % project_root)
    match = CONST_SECTION_0_STAMP.search(Read_Text(os.path.join(project_root, CONST_BRIEF)))
    assert match, "Section 0 has no 'State as of commit `<hash>`, <YYYY-MM-DD>'."
    result = subprocess.run(['git', 'merge-base', '--is-ancestor', match.group(1), 'HEAD'], cwd=project_root,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, ('The brief names commit %s, which is not an ancestor of HEAD (or does not '
                                    'exist): %s' % (match.group(1), result.stderr.strip()))


def test_the_test_count_and_times_match_claude_md(project_root) -> None:
    """
    Description:
        The brief repeats the two check tiers' count and times from CLAUDE.md > Commands. They are read from
        CLAUDE.md, so a re-measure that updates it fails here until the brief follows.
    """

    claude = Read_Text(os.path.join(project_root, CONST_CLAUDE_MD))
    default, slow = CONST_DEFAULT_TIER.search(claude), CONST_SLOW_TIER.search(claude)
    assert default and slow, 'CLAUDE.md > Commands no longer has its two pytest lines with a count and a time.'
    text = Read_Text(os.path.join(project_root, CONST_BRIEF))
    expected = ['%s tests collected' % default.group(1), '%s s by default' % default.group(2),
                '%s s with `--runslow`' % slow.group(2)]
    missing = [phrase for phrase in expected if phrase not in text]
    assert missing == [], 'The brief does not state, as CLAUDE.md does: %s.' % '; '.join(missing)
