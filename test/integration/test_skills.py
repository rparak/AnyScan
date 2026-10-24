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
# File Name: ../test/integration/test_skills.py
## =========================================================================== ##

# System (Default)
import os
import re
import json
import glob
# Typing (Support for type hints)
import typing as tp
# pytest (One case per project layer)
import pytest

"""
Description:
    Initialization of constants.

    The skills are personal (~/.claude/skills/, rparak/rp-claude-skills); this repository keeps only
    each skill's project layer, .claude/skills/<skill>/references/. A SKILL.md here would be ignored in
    favour of the personal skill of the same name and drift unseen, as the copies once did (CLAUDE.md;
    project-style-rpx references/structure.md > Skills layout). These tests hold the layout: exactly
    the declared layers, no SKILL.md, each project.md with the sections it binds, the checker's
    configuration, and CLAUDE.md naming every layer.
"""
# The repository's skills directory, relative to its root.
#   Unit [string]
CONST_SKILLS_DIR = os.path.join('.claude', 'skills')

# The skills whose project layer this repository keeps, each with the sections its references/project.md
# must hold. project-bootstrap has none on purpose: it is for new repositories.
#   Unit [Dict<string, Tuple<string>>]
CONST_PROJECT_LAYERS = {
    'project-style-rpx': ('## Header and checker', '## Layout and layers', '## Root', '## Configuration',
                          '## Records', '## UI - Qt code', '## Unsettled'),
    'jic-sf-ui-style': ('## Modules', "## AnyScan's state colours", '## The vision overlays', '## Unsettled'),
    'feature-manager': ('## Records', '## Domain checklist', '## Docs'),
    'project-optimize': ('## Outputs compared byte for byte', '## The frozen clock', '## Normalisation filter',
                         '## Never touched', '## Reached without a grep hit'),
    'readme-writer': ('## Readers', '## Sources of numbers', '## Triggers', '## Statuses', '## Figures',
                      '## README tests'),
}
# A citation of a README section in prose, "README > <section>": the section's name follows, and where it
# ends is found against the README's headings.
#   Unit [Pattern]
CONST_README_CITATION = re.compile(r'README > (\S(?:(?!README > )[^\n"])*)')
# A Markdown link to the README with an anchor, "(<relative path>README.md#<anchor>)".
#   Unit [Pattern]
CONST_README_LINK = re.compile(r'\]\(([^)#\s]*README\.md)#([^)\s]+)\)')
# A README heading that can be linked: level 2 or 3, outside a code fence.
#   Unit [Pattern]
CONST_README_HEADING = re.compile(r'^#{2,3} (.+?)\s*$')


def test_the_skills_directory_holds_exactly_the_declared_project_layers(project_root) -> None:
    """
    Description:
        .claude/skills/ holds one folder per declared project layer and nothing else, so a new skill
        folder (or a stray copy) changes this list, CLAUDE.md and the layers' tests together.
    """

    assert set(os.listdir(os.path.join(project_root, CONST_SKILLS_DIR))) == set(CONST_PROJECT_LAYERS)


def test_no_skill_md_is_kept_in_the_repository(project_root) -> None:
    """
    Description:
        No SKILL.md at any depth under .claude/skills/: the personal skill of the same name wins.
    """

    assert glob.glob(os.path.join(project_root, CONST_SKILLS_DIR, '**', 'SKILL.md'), recursive=True) == []


@pytest.mark.parametrize('skill', sorted(CONST_PROJECT_LAYERS))
def test_each_skill_keeps_only_its_project_layer(project_root, skill) -> None:
    """
    Description:
        The skill's folder holds references/ and nothing else, and references/project.md is this
        project's reference for that skill with the sections it binds.
    """

    folder = os.path.join(project_root, CONST_SKILLS_DIR, skill)
    assert sorted(os.listdir(folder)) == ['references'], '%s holds more than references/.' % folder

    with open(os.path.join(folder, 'references', 'project.md'), encoding='utf-8') as file:
        text = file.read()
    assert text.startswith('# %s: project reference for AnyScan\n' % skill)
    for section in CONST_PROJECT_LAYERS[skill]:
        assert '\n' + section in text, '%s project.md has no %r section.' % (skill, section)
    assert '{{' not in text, '%s project.md holds an unfilled template field.' % skill


def test_the_style_checker_configuration_is_complete_and_reasoned(project_root) -> None:
    """
    Description:
        The personal checker reads references/check_style.json: every field it requires, this
        project's holder, and a reason for each exclusion.
    """

    path = os.path.join(project_root, CONST_SKILLS_DIR, 'project-style-rpx', 'references', 'check_style.json')
    with open(path, encoding='utf-8') as file:
        config = json.load(file)
    assert set(config) == {'licence', 'holder', 'class_roots', 'test_roots', 'check_roots', 'exclude'}
    assert config['holder'] == 'JIC Smart Factory'
    assert all(entry.get('reason', '').strip() for entry in config['exclude'])


def _Readme_Headings(text: str) -> tp.Tuple[tp.List[str], tp.Set[str]]:
    """
    Description:
        The README's level-2 and level-3 headings, outside code fences, and the anchors GitHub gives them:
        lower case, punctuation other than '-' and '_' removed, spaces as hyphens, a repeated one
        suffixed -1, -2.

    Args:
        (1) text [string]: The README.

    Returns:
        (1) parameter [List<string>]: The headings' text, in order.
        (2) parameter [Set<string>]: Their anchors.
    """

    headings, anchors, seen, fenced = [], set(), {}, False
    for line in text.splitlines():
        if line.lstrip().startswith('```'):
            fenced = not fenced
            continue
        match = None if fenced else CONST_README_HEADING.match(line)
        if match is None:
            continue
        headings.append(match.group(1))
        anchor = re.sub(r'[^\w\- ]', '', match.group(1).lower()).replace(' ', '-')
        anchors.add(anchor if anchor not in seen else '%s-%d' % (anchor, seen[anchor]))
        seen[anchor] = seen.get(anchor, 0) + 1
    return headings, anchors


def _Stale_Readme_References(root: str, layers: tp.List[str]) -> tp.List[str]:
    """
    Description:
        Every reference to a README section in the given files that the README does not hold: a
        "README > <section>" citation whose words start with no heading of the README (a heading must
        end at a word's end), and a link to README.md#<anchor> whose path is not the root README or
        whose anchor no heading has.

    Args:
        (1) root [string]: The repository's root, with README.md.
        (2) layers [List<string>]: The files to read, relative to the root.

    Returns:
        (1) parameter [List<string>]: One 'file:line: reference' per stale reference; empty when none is.
    """

    with open(os.path.join(root, 'README.md'), encoding='utf-8') as file:
        headings, anchors = _Readme_Headings(file.read())
    readme = os.path.realpath(os.path.join(root, 'README.md'))
    stale = []
    for layer in layers:
        with open(os.path.join(root, layer), encoding='utf-8') as file:
            lines = file.read().splitlines()
        for number, line in enumerate(lines, 1):
            for match in CONST_README_CITATION.finditer(line):
                cited = match.group(1)
                if not any(re.match(re.escape(h) + r'(?![\w])', cited) for h in headings):
                    stale.append('%s:%d: README > %s' % (layer, number, cited.rstrip()))
            for match in CONST_README_LINK.finditer(line):
                target = os.path.realpath(os.path.join(root, os.path.dirname(layer), match.group(1)))
                if target != readme or match.group(2) not in anchors:
                    stale.append('%s:%d: %s#%s' % (layer, number, match.group(1), match.group(2)))
    return stale


def _Project_Layer_Files(root: str) -> tp.List[str]:
    """
    Description:
        Every file of the skills' project layers: each references/project.md and check_style.json.

    Args:
        (1) root [string]: The repository's root.

    Returns:
        (1) parameter [List<string>]: The files, relative to the root, sorted.
    """

    found = glob.glob(os.path.join(root, CONST_SKILLS_DIR, '*', 'references', '*'))
    return sorted(os.path.relpath(path, root) for path in found if path.endswith(('.md', '.json')))


def test_every_readme_section_the_project_layers_cite_exists(project_root) -> None:
    """
    Description:
        The project layers cite README sections by name ("README > Platform") and link to them by anchor
        (README.md#platform); a README rewrite that renames, merges or drops a section must update them.
        Every citation must start with one of the README's level-2 or level-3 headings, and every link
        must reach the root README and an anchor one of its headings has. The layers were found pointing
        at "Describer model" and "Source layout" after both sections were folded into others.
    """

    layers = _Project_Layer_Files(project_root)
    assert '.claude/skills/project-style-rpx/references/check_style.json' in layers
    assert _Stale_Readme_References(project_root, layers) == []


def test_a_stale_readme_reference_is_reported(project_root, tmp_path) -> None:
    """
    Description:
        The check finds what it is for: in a scratch copy of the layout, a citation of a section the
        README does not have, a link to a missing anchor and a link that misses the README are each
        reported, and the citations and links that match are not.
    """

    (tmp_path / 'README.md').write_text('# T\n\n## Platform\n\n```bash\n## Not a heading\n```\n\n'
                                        '### Measurements are repeatable, not absolute\n', encoding='utf-8')
    layer = tmp_path / '.claude' / 'skills' / 'x' / 'references'
    layer.mkdir(parents=True)
    (layer / 'project.md').write_text(
        'README > Platform. README > Platforms. README > Not a heading.\n'
        '[a](../../../../README.md#platform) [b](../../../../README.md#describer-model)\n'
        '[c](../../../README.md#platform) [d](../../../../README.md#measurements-are-repeatable-not-absolute)\n',
        encoding='utf-8')

    stale = _Stale_Readme_References(str(tmp_path), ['.claude/skills/x/references/project.md'])
    assert stale == ['.claude/skills/x/references/project.md:1: README > Platforms.',
                     '.claude/skills/x/references/project.md:1: README > Not a heading.',
                     '.claude/skills/x/references/project.md:2: ../../../../README.md#describer-model',
                     '.claude/skills/x/references/project.md:3: ../../../README.md#platform']


def test_claude_md_names_every_project_layer_and_the_checker(project_root) -> None:
    """
    Description:
        CLAUDE.md is where a session learns the layout: it names each skill with a project layer, the
        checker by its personal path, and where the internal records are.
    """

    with open(os.path.join(project_root, 'CLAUDE.md'), encoding='utf-8') as file:
        text = file.read()
    for skill in CONST_PROJECT_LAYERS:
        assert '`%s`' % skill in text, 'CLAUDE.md does not name %s.' % skill
    assert '~/.claude/skills/project-style-rpx/scripts/check_style.py' in text
    assert '`.claude/project-docs/`' in text
