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
# pytest (One case per skill)
import pytest

"""
Description:
    Initialization of constants.

    The repository ships its skills in .claude/skills/<skill>/: a generic SKILL.md, generic references, assets
    and scripts, and the skill's references/project.md, which holds every AnyScan decision for it (design-decisions,
    *The skills ship in the repository*). The personal copies of the same names are kept out of ~/.claude/skills by
    its sparse checkout, so these are the copies a session loads. These tests hold the layout: exactly the six skills
    and their licence, each SKILL.md's frontmatter, each skill's files, every pointer resolving, no project term in a
    generic file, each project.md with the sections it binds, the checker's configuration, the README sections the
    project layers cite, and CLAUDE.md naming the skills and the in-repo checker.
"""
# The repository's skills directory, relative to its root.
#   Unit [string]
CONST_SKILLS_DIR = os.path.join('.claude', 'skills')

# What .claude/skills/ holds beside the skills' folders: the skills' own licence (MIT, Roman Parak).
#   Unit [Vector<string>]
CONST_SKILLS_EXTRA = ('LICENSE',)

# Each shipped skill: the files it must hold (relative to its folder) and the sections its references/project.md
# must hold. support-brief's project layer is a stub until R2 (FEATURES.md).
#   Unit [Dict<string, Dict<string, Tuple<string>>>]
CONST_SKILLS = {
    'project-style-rpx': {
        'files': ('SKILL.md', 'references/project.md', 'references/check_style.json', 'references/python.md',
                  'references/yaml.md', 'references/structure.md', 'references/shell.md', 'references/markdown.md',
                  'references/figures.md', 'references/ui.md', 'assets/header.txt', 'assets/module_template.py',
                  'assets/script_template.py', 'assets/config_template.yaml', 'scripts/check_style.py',
                  'scripts/test_check_style.py'),
        'sections': ('## Header and checker', '## Layout and layers', '## Root', '## Configuration', '## Records',
                     '## UI - Qt code', '## Unsettled')},
    'feature-manager': {
        'files': ('SKILL.md', 'references/project.md', 'assets/handover_template.md'),
        'sections': ('## Records', '## Domain checklist', '## Docs')},
    'project-optimize': {
        'files': ('SKILL.md', 'references/project.md'),
        'sections': ('## Outputs compared byte for byte', '## The frozen clock', '## Normalisation filter',
                     '## Never touched', '## Reached without a grep hit')},
    'readme-writer': {
        'files': ('SKILL.md', 'references/project.md', 'references/check_readme.json', 'references/style.md',
                  'references/structure.md', 'references/figures.md', 'references/checklist.md',
                  'scripts/check_readme.py', 'scripts/render_readme.py', 'scripts/test_check_readme.py',
                  'scripts/test_render_readme.py'),
        'sections': ('## Readers', '## Sources of numbers', '## Triggers', '## Statuses', '## Figures',
                     '## README tests')},
    'jic-sf-ui-style': {
        'files': ('SKILL.md', 'references/project.md', 'references/palette.md', 'references/typography.md',
                  'references/layout-components.md', 'references/pixel-icons.md', 'references/charts.md',
                  'references/annotation.md', 'references/grid-fit.md', 'references/wording.md',
                  'references/testing.md', 'assets/logos/USAGE.md', 'assets/fonts/README.md',
                  'scripts/check_tokens.py', 'scripts/contrast.py', 'templates/example_app.py',
                  'templates/JIC_SF_UI/__init__.py'),
        'sections': ('## Modules', "## AnyScan's state colours", '## The vision overlays', '## Unsettled')},
    'support-brief': {
        'files': ('SKILL.md', 'references/project.md'),
        'sections': ('## Status',)},
}
# The longest description Claude Code accepts in a skill's frontmatter.
#   Unit [-]
CONST_DESCRIPTION_MAX = 1024

# The files of a skill that are its project layer, and may name the project: everything else is generic.
#   Unit [Vector<string>]
CONST_PROJECT_LAYER_FILES = ('references/project.md', 'references/check_style.json', 'references/check_readme.json')
# Terms of another project, or a path into a personal install, that no generic file may hold (case-insensitive).
#   Unit [Pattern]
CONST_FOREIGN_TERMS = re.compile(r'KINALI|Test-it-off|Test_it_off|cell\.py|MuJoCo|MG06|AUBO|VGC10|\bPCB\b|mjcf|'
                                 r'~/\.claude/skills/[\w-]+/', re.IGNORECASE)
# This project's names, which no generic file may hold; jic-sf-ui-style, the brand skill taken from AnyScan, names
# both by design (owner, 2026-10-29).
#   Unit [Pattern]
CONST_PROJECT_TERMS = re.compile(r'\bAnyScan\b|\bJIC\b')
#   Unit [Vector<string>]
CONST_PROJECT_TERMS_ALLOWED = ('jic-sf-ui-style',)
# Binary files a term search skips.
#   Unit [Vector<string>]
CONST_BINARY_SUFFIXES = ('.ttf', '.png', '.ico')

# A Markdown link, "](<target>)", and inline code, which holds example links that point nowhere on purpose.
#   Unit [Pattern]
CONST_MARKDOWN_LINK = re.compile(r'\]\(([^)\s]+)\)')
#   Unit [Pattern]
CONST_INLINE_CODE = re.compile(r'`[^`\n]*`')
# A file of a skill named in its SKILL.md's prose, "references/python.md": resolved in that skill, or in another
# skill it names (project-style-rpx `references/ui.md`).
#   Unit [Pattern]
CONST_SKILL_PATH = re.compile(r'(?<![\w/.-])((?:references|assets|scripts|templates)/[\w./-]+'
                              r'\.(?:md|py|json|txt|yaml|svg|ttf|sh))')

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

# The checker's in-repo path, as CLAUDE.md must name it.
#   Unit [string]
CONST_CHECKER = '.claude/skills/project-style-rpx/scripts/check_style.py'


def _Read(path: str) -> str:
    """
    Description:
        A text file's content.

    Args:
        (1) path [string]: The file.

    Returns:
        (1) parameter [string]: Its text.
    """

    with open(path, encoding='utf-8') as file:
        return file.read()


def _Frontmatter(text: str) -> tp.Dict[str, str]:
    """
    Description:
        The name and description of a SKILL.md's YAML frontmatter, read by hand (a 'key: value' line, or a '>-'
        block whose indented lines are folded with single spaces), so the test needs no YAML library.

    Args:
        (1) text [string]: The SKILL.md.

    Returns:
        (1) parameter [Dict<string, string>]: The keys found, empty when the file opens with no frontmatter.
    """

    lines = text.split('\n')
    if not lines or lines[0] != '---' or '---' not in lines[1:]:
        return {}
    fields, key = {}, None
    for line in lines[1:lines.index('---', 1)]:
        match = re.match(r'^([a-z_-]+):\s*(.*)$', line)
        if match is not None:
            key, value = match.group(1), match.group(2)
            fields[key] = '' if value in ('>-', '>', '|') else value
        elif key is not None and line.startswith(' '):
            fields[key] = (fields[key] + ' ' + line.strip()).strip()
    return fields


def _Broken_Pointers(root: str, skills: tp.List[str]) -> tp.List[str]:
    """
    Description:
        Every pointer in the skills that reaches nothing: a relative Markdown link (outside inline code) in any of
        their Markdown files whose target does not exist, and a skill file a SKILL.md names in its prose
        (references/, assets/, scripts/, templates/) that neither that skill nor any other skill holds.

    Args:
        (1) root [string]: The repository's root.
        (2) skills [List<string>]: The skills' folder names.

    Returns:
        (1) parameter [List<string>]: One 'file: target' per broken pointer; empty when every pointer resolves.
    """

    base, broken = os.path.join(root, CONST_SKILLS_DIR), []
    for path in sorted(glob.glob(os.path.join(base, '**', '*.md'), recursive=True)):
        for match in CONST_MARKDOWN_LINK.finditer(CONST_INLINE_CODE.sub('', _Read(path))):
            target = match.group(1).split('#')[0]
            if not target or re.match(r'[a-z]+:', target) or '<' in target or '{' in target:
                continue
            if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(path), target))):
                broken.append('%s: %s' % (os.path.relpath(path, root), target))
    for skill in skills:
        for match in CONST_SKILL_PATH.finditer(_Read(os.path.join(base, skill, 'SKILL.md'))):
            if not any(os.path.exists(os.path.join(base, owner, match.group(1))) for owner in [skill] + skills):
                broken.append('%s: %s' % (os.path.join(CONST_SKILLS_DIR, skill, 'SKILL.md'), match.group(1)))
    return broken


def _Project_Terms_In_Generic_Files(root: str) -> tp.List[str]:
    """
    Description:
        Every line of a generic skill file (anything but a project layer, the licence or a binary) that holds another
        project's term or a personal-install path, or this project's name outside the skills allowed to name it.

    Args:
        (1) root [string]: The repository's root.

    Returns:
        (1) parameter [List<string>]: One 'file:line: text' per hit; empty when the generic files are generic.
    """

    base, hits = os.path.join(root, CONST_SKILLS_DIR), []
    for path in sorted(glob.glob(os.path.join(base, '*', '**', '*'), recursive=True)):
        relative = os.path.relpath(path, base).replace(os.sep, '/')
        skill, inside = relative.split('/', 1)
        if (os.path.isdir(path) or inside in CONST_PROJECT_LAYER_FILES or path.endswith(CONST_BINARY_SUFFIXES)
                or '__pycache__' in relative or os.path.basename(path) == '.DS_Store'):
            continue
        with open(path, encoding='utf-8', errors='replace') as file:
            for number, line in enumerate(file, 1):
                if CONST_FOREIGN_TERMS.search(line) or (skill not in CONST_PROJECT_TERMS_ALLOWED
                                                        and CONST_PROJECT_TERMS.search(line)):
                    hits.append('%s:%d: %s' % (relative, number, line.strip()[:120]))
    return hits


def test_the_skills_directory_holds_exactly_the_shipped_skills_and_their_licence(project_root) -> None:
    """
    Description:
        .claude/skills/ holds one folder per shipped skill and the skills' LICENSE, and nothing else, so a new skill
        folder (or a stray copy) changes this list, CLAUDE.md and the skills' tests together.
    """

    found = set(os.listdir(os.path.join(project_root, CONST_SKILLS_DIR))) - {'.DS_Store'}
    assert found == set(CONST_SKILLS) | set(CONST_SKILLS_EXTRA)
    assert _Read(os.path.join(project_root, CONST_SKILLS_DIR, 'LICENSE')).startswith('MIT License\n')


@pytest.mark.parametrize('skill', sorted(CONST_SKILLS))
def test_each_skill_md_names_its_folder_with_a_description_claude_code_accepts(project_root, skill) -> None:
    """
    Description:
        Each SKILL.md opens with frontmatter whose name is its folder's and whose description, the text Claude Code
        matches a request against, is at most 1024 characters with no '<' or '>'.
    """

    fields = _Frontmatter(_Read(os.path.join(project_root, CONST_SKILLS_DIR, skill, 'SKILL.md')))
    assert fields.get('name') == skill, '%s/SKILL.md names %r.' % (skill, fields.get('name'))
    description = fields.get('description', '')
    assert 0 < len(description) <= CONST_DESCRIPTION_MAX, '%s: description of %d characters.' % (skill,
                                                                                                len(description))
    assert '<' not in description and '>' not in description, '%s: description holds < or >.' % skill


@pytest.mark.parametrize('skill', sorted(CONST_SKILLS))
def test_each_skill_holds_its_files_and_its_project_layer(project_root, skill) -> None:
    """
    Description:
        Each skill holds the files it is shipped with, and its references/project.md is this project's reference
        for that skill, with the sections it binds and no unfilled template field.
    """

    folder = os.path.join(project_root, CONST_SKILLS_DIR, skill)
    missing = [name for name in CONST_SKILLS[skill]['files'] if not os.path.isfile(os.path.join(folder, name))]
    assert missing == [], '%s lacks %s.' % (skill, missing)

    text = _Read(os.path.join(folder, 'references', 'project.md'))
    assert text.startswith('# %s: project reference for AnyScan\n' % skill)
    for section in CONST_SKILLS[skill]['sections']:
        assert '\n' + section in text, '%s project.md has no %r section.' % (skill, section)
    assert '{{' not in text, '%s project.md holds an unfilled template field.' % skill


def test_every_pointer_in_the_skills_resolves(project_root) -> None:
    """
    Description:
        Every relative link in the skills' Markdown, and every skill file a SKILL.md names, exists: a reference the
        copy left behind, or a file a rewrite removed, fails here by name.
    """

    assert _Broken_Pointers(project_root, sorted(CONST_SKILLS)) == []


def test_no_generic_skill_file_holds_a_project_term(project_root) -> None:
    """
    Description:
        The generic files hold no project's names, paths or numbers: no term of the project they were copied from,
        no path into a personal install, and no AnyScan or JIC outside the brand skill. AnyScan's part is in the
        project layers.
    """

    assert _Project_Terms_In_Generic_Files(project_root) == []


def test_the_style_checker_configuration_is_complete_and_reasoned(project_root) -> None:
    """
    Description:
        The checker reads references/check_style.json: every field it requires, this project's holder, and a
        reason for each exclusion.
    """

    path = os.path.join(project_root, CONST_SKILLS_DIR, 'project-style-rpx', 'references', 'check_style.json')
    config = json.loads(_Read(path))
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

    headings, anchors = _Readme_Headings(_Read(os.path.join(root, 'README.md')))
    readme = os.path.realpath(os.path.join(root, 'README.md'))
    stale = []
    for layer in layers:
        lines = _Read(os.path.join(root, layer)).splitlines()
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
        Every file of the skills' project layers: each references/project.md, check_style.json and
        check_readme.json. The generic references are not this README's and are not read.

    Args:
        (1) root [string]: The repository's root.

    Returns:
        (1) parameter [List<string>]: The files, relative to the root, sorted.
    """

    found = [os.path.join(root, CONST_SKILLS_DIR, skill, name) for skill in CONST_SKILLS
             for name in CONST_PROJECT_LAYER_FILES]
    return sorted(os.path.relpath(path, root) for path in found if os.path.isfile(path))


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


def test_claude_md_names_every_skill_and_the_in_repo_checker(project_root) -> None:
    """
    Description:
        CLAUDE.md is where a session learns the layout: it names each shipped skill, the checker by its path in
        this repository (never a personal install's), and where the internal records are.
    """

    text = _Read(os.path.join(project_root, 'CLAUDE.md'))
    for skill in CONST_SKILLS:
        assert '`%s`' % skill in text, 'CLAUDE.md does not name %s.' % skill
    assert CONST_CHECKER in text
    assert re.search(r'~/\.claude/skills/[\w-]+/', text) is None, 'CLAUDE.md points into a personal install.'
    assert '`.claude/project-docs/`' in text
