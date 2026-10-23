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
import re
import glob
# Typing (Support for type hints)
import typing as tp
# YAML (The skills' frontmatter format)
import yaml
# pytest (One case per skill file)
import pytest

"""
Description:
    Initialization of constants.

    The project's Claude Code skills (.claude/skills/<name>/SKILL.md) open with a YAML frontmatter that
    Claude Code parses to list and load them. Nothing else ever parsed it, so two faults went unseen.
    project-optimize's description (then project-cleanup's) held an unquoted ': ', which made the
    frontmatter invalid YAML, and the skill failed to load. project-style-rpx's held ' #', which YAML
    reads as the start of a comment, so its description was silently cut to its first 86 characters. These tests parse every SKILL.md
    as YAML, as Claude Code does, and check what it needs.
"""
# The repository root (test/integration/ -> ../..). The parametrization needs it at collection time,
# before the project_root fixture exists.
#   Unit [string]
CONST_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# The repository's skills directory, relative to its root.
#   Unit [string]
CONST_SKILLS_DIR = os.path.join('.claude', 'skills')

# The frontmatter: a '---' line opening the file, the YAML, and the next '---' line.
#   Unit [Pattern]
CONST_FRONTMATTER = re.compile(r'\A---\n(.*?)\n---\n', re.S)

# The skills whose project layer this repository keeps, each with the sections its references/project.md
# must hold (the layers in CLAUDE.md).
#   Unit [Dict<string, Tuple<string>>]
CONST_PROJECT_LAYERS = {
    'project-style-rpx': ('## Header and checker', '## Layout and layers', '## Configuration', '## Records',
                          '## UI - Qt code', '## Unsettled'),
    'jic-sf-ui-style': ('## Modules', "## AnyScan's state colours", '## The vision overlays', '## Unsettled'),
    'feature-manager': ('## Records instead of a SPEC', '## Domain checklist', '## Docs'),
}

# The description's raw text in the frontmatter: from its key to the next top-level key or the end.
#   Unit [Pattern]
CONST_RAW_DESCRIPTION = re.compile(r'^description:(.*?)(?=^\S|\Z)', re.S | re.M)


def Skill_Files(project_root: str) -> tp.List[str]:
    """
    Description:
        Every SKILL.md under .claude/skills/, at any depth.

    Args:
        (1) project_root [string]: The repository root.

    Returns:
        (1) parameter [Vector<string>]: Their paths relative to the root, sorted.
    """

    pattern = os.path.join(project_root, CONST_SKILLS_DIR, '**', 'SKILL.md')
    return sorted(os.path.relpath(path, project_root) for path in glob.glob(pattern, recursive=True))


def Words(text: str) -> str:
    """
    Description:
        Text with every run of whitespace made one space, so a folded block and the line it folds
        compare equal.

    Args:
        (1) text [string]: The text.

    Returns:
        (1) parameter [string]: Its words, single-spaced.
    """

    return ' '.join(text.split())


def test_the_skills_directory_holds_the_projects_skills(project_root) -> None:
    """
    Description:
        The parametrized check below runs once per file it finds, so a glob that finds nothing would
        pass with no cases. The skill the repository still ships with a SKILL.md must be found.
    """

    names = {os.path.basename(os.path.dirname(path)) for path in Skill_Files(project_root)}

    assert {'project-optimize'} <= names


@pytest.mark.parametrize('skill', sorted(CONST_PROJECT_LAYERS))
def test_each_skill_keeps_only_its_project_layer(project_root, skill) -> None:
    """
    Description:
        The skills are personal; a SKILL.md of the same name here would be ignored (a personal skill
        wins over a project skill) and drift. The repository keeps each skill's project layer only:
        the folder holds references/ and nothing else, and references/project.md is this project's
        reference for that skill with the sections it binds.
    """

    folder = os.path.join(project_root, CONST_SKILLS_DIR, skill)
    assert sorted(os.listdir(folder)) == ['references'], '%s holds more than references/.' % folder

    with open(os.path.join(folder, 'references', 'project.md'), encoding='utf-8') as file:
        text = file.read()
    assert text.startswith('# %s: project reference for AnyScan\n' % skill)
    for section in CONST_PROJECT_LAYERS[skill]:
        assert '\n' + section in text, '%s project.md has no %r section.' % (skill, section)


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


@pytest.mark.parametrize('skill_path', Skill_Files(CONST_PROJECT_ROOT))
def test_every_skill_frontmatter_parses_with_its_name_and_full_description(project_root, skill_path) -> None:
    """
    Description:
        The file opens with a frontmatter that parses as a YAML mapping; 'name' equals the skill's
        directory; 'description' is non-empty text; and the description YAML returns is all of the
        text written, word for word, so a ' #' that starts a comment, or anything else that cuts it
        short without an error, fails here.
    """

    with open(os.path.join(project_root, skill_path), encoding='utf-8') as file:
        text = file.read()
    match = CONST_FRONTMATTER.match(text)
    assert match, '%s does not open with a ---/--- frontmatter.' % skill_path
    try:
        front = yaml.safe_load(match.group(1))
    except yaml.YAMLError as error:
        pytest.fail('%s: the frontmatter is not valid YAML, so the skill does not load. %s' % (skill_path, error))

    assert isinstance(front, dict), '%s: the frontmatter is not a mapping.' % skill_path
    assert front.get('name') == os.path.basename(os.path.dirname(skill_path)), \
        "%s: 'name' is %r, not its directory's name." % (skill_path, front.get('name'))
    description = front.get('description')
    assert isinstance(description, str) and description.strip(), "%s: no 'description'." % skill_path

    raw = CONST_RAW_DESCRIPTION.search(match.group(1)).group(1).strip()
    if raw[:2] in ('>-', '>+', '|-', '|+') or raw[:1] in ('>', '|'):
        raw = raw.lstrip('>|+-')
    raw = raw.strip()
    if raw[:1] in ('"', "'") and raw[-1:] == raw[:1]:
        raw = raw[1:-1]
    assert Words(description) == Words(raw), \
        "%s: YAML reads the description as %r; the file holds more. Use a folded block (description: >-)." \
        % (skill_path, description)
