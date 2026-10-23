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
import json
import glob
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
# must hold. project-bootstrap has none on purpose: it is for new repositories (CLAUDE.md).
#   Unit [Dict<string, Tuple<string>>]
CONST_PROJECT_LAYERS = {
    'project-style-rpx': ('## Header and checker', '## Layout and layers', '## Root', '## Configuration',
                          '## Records', '## UI - Qt code', '## Unsettled'),
    'jic-sf-ui-style': ('## Modules', "## AnyScan's state colours", '## The vision overlays', '## Unsettled'),
    'feature-manager': ('## Records instead of a SPEC', '## Domain checklist', '## Docs'),
    'project-optimize': ('## Outputs compared byte for byte', '## The frozen clock', '## Normalisation filter',
                         '## Never touched', '## Reached without a grep hit'),
    'readme-writer': ('## Readers', '## Sources of numbers', '## Triggers', '## Statuses', '## Figures',
                      '## README tests'),
}


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


def test_claude_md_names_every_project_layer_and_the_checker(project_root) -> None:
    """
    Description:
        CLAUDE.md is where a session learns the layout: it names each skill with a project layer, the
        checker by its personal path, and says project-bootstrap does not apply.
    """

    with open(os.path.join(project_root, 'CLAUDE.md'), encoding='utf-8') as file:
        text = file.read()
    for skill in CONST_PROJECT_LAYERS:
        assert '`%s`' % skill in text, 'CLAUDE.md does not name %s.' % skill
    assert '~/.claude/skills/project-style-rpx/scripts/check_style.py' in text
    assert '`project-bootstrap` skill does not apply' in text
