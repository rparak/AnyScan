## =========================================================================== ##
# MIT License
# Copyright (c) 2026 JIC Smart Factory
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
# File Name: ../test/integration/test_citation.py
## =========================================================================== ##

# System (Default)
import os
import re
# Subprocess (Subprocess management)
import subprocess
# Typing (Support for type hints)
import typing as tp
# PyYAML (YAML parsing)
import yaml
# Pytest (Testing framework) [pip3 install pytest]
import pytest

"""
Description:
    CITATION.cff, the repository's citation metadata (R5): it parses, its licence is LICENSE's, its authors are
    README > Authors in order, and once the tag v<version> exists at a commit that holds the file, its version and
    release date are that tag's. Each expectation is read from its own source, never from CITATION.cff.
"""
# The citation file and the files it is held to, relative to the root.
#   Unit [string]
CONST_CITATION = 'CITATION.cff'
CONST_LICENSE = 'LICENSE'
CONST_README = 'README.md'
# An author's name in README > Authors: the bold name in each avatar cell.
#   Unit [Pattern]
CONST_AUTHOR_NAME = re.compile(r'<strong>([^<]+)</strong>')


def _Citation(project_root: str) -> tp.Dict[str, tp.Any]:
    """CITATION.cff, parsed."""
    with open(os.path.join(project_root, CONST_CITATION), 'r', encoding='utf-8') as handle:
        return yaml.safe_load(handle)


def _Git(project_root: str, *arguments: str) -> subprocess.CompletedProcess:
    """A git command in the repository, its output as text."""
    return subprocess.run(['git', *arguments], cwd=project_root, capture_output=True, text=True, timeout=60)


def test_the_citation_parses_as_citation_file_format_1_2_0(project_root) -> None:
    """
    Description:
        CITATION.cff is a YAML mapping in the Citation File Format 1.2.0 with the fields GitHub reads: the title,
        the authors, the version and the release date.
    """

    citation = _Citation(project_root)
    assert isinstance(citation, dict)
    assert citation['cff-version'] == '1.2.0'
    assert citation['title'] == 'AnyScan'
    assert {'authors', 'version', 'date-released', 'license', 'repository-code'} <= set(citation)


def test_the_citations_licence_is_the_licence_file(project_root) -> None:
    """
    Description:
        The licence named in CITATION.cff is the one LICENSE grants, read from its first line ('MIT License').
    """

    with open(os.path.join(project_root, CONST_LICENSE), 'r', encoding='utf-8') as handle:
        first_line = handle.readline().strip()
    assert first_line == 'MIT License'
    assert _Citation(project_root)['license'] == 'MIT'


def test_the_citations_authors_are_the_readmes_in_order(project_root) -> None:
    """
    Description:
        The authors in CITATION.cff, each 'given-names family-names' with the affiliation JIC Smart Factory, are
        the names in README > Authors, in the same order.
    """

    with open(os.path.join(project_root, CONST_README), 'r', encoding='utf-8') as handle:
        readme = handle.read()
    section = readme.split('\n## Authors\n', 1)[1].split('\n## ', 1)[0]
    expected = CONST_AUTHOR_NAME.findall(section)
    assert len(expected) == 4, expected
    authors = _Citation(project_root)['authors']
    assert ['%s %s' % (author['given-names'], author['family-names']) for author in authors] == expected
    assert {author['affiliation'] for author in authors} == {'JIC Smart Factory'}


def test_the_version_and_release_date_are_the_tags(project_root) -> None:
    """
    Description:
        Once the annotated tag v<version> exists and its commit holds CITATION.cff, that commit's file names the
        same version, and its date-released is the tag commit's date. Before the tag is moved to the release
        commit (its commit holds no CITATION.cff) or without git history, the test skips and says why.
    """

    if _Git(project_root, 'rev-parse', '--git-dir').returncode != 0:
        pytest.skip('CITATION TAG CHECK NOT RUN: %s is not a git repository.' % project_root)
    version = str(_Citation(project_root)['version'])
    tag = 'v%s' % version
    commit = _Git(project_root, 'rev-parse', '--verify', '--quiet', '%s^{commit}' % tag)
    if commit.returncode != 0:
        pytest.skip('CITATION TAG CHECK NOT RUN: the tag %s does not exist.' % tag)
    tagged = _Git(project_root, 'show', '%s:%s' % (commit.stdout.strip(), CONST_CITATION))
    if tagged.returncode != 0:
        pytest.skip('CITATION TAG CHECK NOT RUN: %s is at %s, which holds no %s; it moves to the release commit.'
                    % (tag, commit.stdout.strip()[:7], CONST_CITATION))
    date = _Git(project_root, 'show', '-s', '--format=%cd', '--date=short', commit.stdout.strip())
    assert date.returncode == 0, date.stderr
    citation = yaml.safe_load(tagged.stdout)
    assert str(citation['version']) == version
    assert str(citation['date-released']) == date.stdout.strip()
