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
# File Name: ../test/integration/test_capabilities_doc.py
## =========================================================================== ##

# System (Default)
import os
import re
import glob
import subprocess
# Typing (Support for type hints)
import typing as tp
# YAML (The configuration files' format)
import yaml
# pytest (A repository without its git history skips the review check, loudly)
import pytest
# Custom Lib.: AnyScan configuration — the mode-file name split
#   ../Configuration/Core
from Configuration.Core import Hardware_And_Mode
# Custom Lib.: AnyScan UI — the view switch, the Camera View renders, the capture-set files
#   ../UI/Core
#   ../UI/Widgets
#   ../UI/Capture
from UI.Core import AnyScan_Window_Cls
from UI.Widgets import View_Toggle_Cls
from UI.Capture import CONST_CAPTURE_SUFFIXES
# Custom Lib.: AnyScan logger — the run-summary columns and the station event types
#   ../Logger/Core
#   ../Logger/Station_Events
from Logger.Core import CONST_CSV_COLUMNS
from Logger.Station_Events import CONST_STATION_EVENT_TYPES, CONST_CYCLE_START, CONST_CYCLE_DONE

"""
Description:
    Initialization of constants.

    docs/capabilities.md describes what the application does, and a capability document that is
    wrong is worse than none. These tests hold it to the code in both directions: everything the
    code names (src/ packages, configuration sections, modes, views, records) is in the document, and every
    configuration key the document names is in a configuration file. Its prose and its hardware
    table cannot be checked; its links can.
"""
# The document under test, relative to the repository root.
#   Unit [string]
CONST_CAPABILITIES_DOC = os.path.join('docs', 'capabilities.md')

# A backticked span, and inside one a dotted configuration key path ('Segmentation.Fusion',
# 'General.Station_Events.Directory'). A path is only checked when its first segment is a section the
# document's own tables name, so 'Configuration.Core.Load_Configuration' is not taken for a key.
#   Unit [Pattern]
CONST_CODE_SPAN = re.compile(r'`([^`]+)`')
CONST_KEY_PATH = re.compile(r'(?<![\w.])([A-Z][A-Za-z0-9_]*(?:\.[A-Z][A-Za-z0-9_]*)+)')

# A Markdown link's target; external links and mail are not checked.
#   Unit [Pattern]
CONST_LINK = re.compile(r'\]\(([^)\s]+)\)')

# The line naming the commit the document was last reviewed against the code at, and the paths whose
# changes a review must cover: the application, its configuration, and the harnesses it lists.
#   Unit [Pattern]
CONST_LAST_REVIEWED = re.compile(r'^Last reviewed against the code at commit `([0-9a-f]{7,40})`', re.M)
#   Unit [Vector<string>]
CONST_REVIEWED_PATHS = ['src', 'App', 'Configuration', 'Example']

# The Live card titles the window builds, read from its source (they are literals in the builders).
#   Unit [Pattern]
CONST_CARD_HEAD = re.compile(r"Card_Head_Cls\('\w+', '([^']+)'")
# The Trends chart titles.
#   Unit [Pattern]
CONST_CHART_CARD = re.compile(r"__Chart_Card\('[^']+', '([^']+)'")


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


def Section(text: str, heading: str) -> str:
    """
    Description:
        The body of one Markdown section: from the line after the heading to the next heading of
        the same or a higher level. Fails the test when the heading is absent, so a renamed section
        is reported as missing rather than read as empty.

    Args:
        (1) text [string]: The Markdown document.
        (2) heading [string]: The heading line, with its #'s ('## Configuration').

    Returns:
        (1) parameter [string]: The section's body.
    """

    lines = text.split('\n')
    level = len(heading) - len(heading.lstrip('#'))
    assert heading in lines, "docs/capabilities.md has no '%s' section." % heading
    start = lines.index(heading) + 1
    end = len(lines)
    for i in range(start, len(lines)):
        hashes = len(lines[i]) - len(lines[i].lstrip('#'))
        if 0 < hashes <= level and lines[i][hashes:hashes + 1] == ' ':
            end = i
            break

    return '\n'.join(lines[start:end])


def Subheadings(body: str, level: int) -> tp.List[str]:
    """
    Description:
        The titles of the headings at one level inside a section's body, in order.

    Args:
        (1) body [string]: The section's body.
        (2) level [int]: The heading level (3 for '###').

    Returns:
        (1) parameter [Vector<string>]: The heading titles.
    """

    prefix = '#' * level + ' '
    return [line[len(prefix):].strip() for line in body.split('\n') if line.startswith(prefix)]


def Table_First_Column(body: str, header: str) -> tp.List[str]:
    """
    Description:
        The backticked names in the first column of the table whose first header cell is `header`.
        A cell may name several ('`Camera.Resolution`, `Camera.Offset`'); a cell with no backticks
        contributes its plain text. Fails the test when there is no such table.

    Args:
        (1) body [string]: The section's body holding the table.
        (2) header [string]: The table's first header cell.

    Returns:
        (1) parameter [Vector<string>]: The names, in the table's order.
    """

    names = []
    in_table = False
    found = False
    for line in body.split('\n'):
        if not line.startswith('|'):
            in_table = False
            continue
        cells = [cell.strip() for cell in line.strip('|').split('|')]
        if not in_table:
            in_table = True
            found = found or cells[0] == header
            collecting = cells[0] == header
            continue
        if set(cells[0]) <= set('-: '):
            continue
        if collecting:
            spans = CONST_CODE_SPAN.findall(cells[0])
            names.extend(spans if spans else [cells[0]])
    assert found, "docs/capabilities.md has no table headed '%s'." % header

    return names


def Key_Paths(node: tp.Any, prefix: str = '') -> tp.Set[str]:
    """
    Description:
        Every key path in a parsed YAML mapping, at every depth ('Camera', 'Camera.Custom_Cfg',
        'Camera.Custom_Cfg.Gain', ...).

    Args:
        (1) node [Any]: The parsed YAML.
        (2) prefix [string]: The path of `node` itself; empty at the root.

    Returns:
        (1) parameter [Set<string>]: The key paths.
    """

    paths = set()
    if isinstance(node, dict):
        for key, value in node.items():
            path = '%s.%s' % (prefix, key) if prefix else str(key)
            paths.add(path)
            paths |= Key_Paths(value, path)

    return paths


def Sections_Of(data: tp.Dict[str, tp.Any]) -> tp.Set[str]:
    """
    Description:
        A configuration file's sections: its top-level keys, and the mappings one level below them.
        Fields deeper than that are the file's own comments' business, not the document's.

    Args:
        (1) data [Dict<string, Any>]: The parsed file.

    Returns:
        (1) parameter [Set<string>]: The section paths.
    """

    sections = set(data)
    for key, value in data.items():
        if isinstance(value, dict):
            sections |= {'%s.%s' % (key, child) for child, grand in value.items() if isinstance(grand, dict)}

    return sections


def Mode_Files(project_root: str) -> tp.List[str]:
    """
    Description:
        The shipped mode files, Configuration/Mode/Config_<Hardware>_Mode_<Mode>.yaml.

    Args:
        (1) project_root [string]: The repository root.

    Returns:
        (1) parameter [Vector<string>]: Their paths, sorted.
    """

    return sorted(glob.glob(os.path.join(project_root, 'Configuration', 'Mode', 'Config_*_Mode_*.yaml')))


def Calibration_Files(project_root: str) -> tp.List[str]:
    """
    Description:
        The shipped calibration files, Configuration/Calibration/Calibration_*.yaml.

    Args:
        (1) project_root [string]: The repository root.

    Returns:
        (1) parameter [Vector<string>]: Their paths, sorted.
    """

    return sorted(glob.glob(os.path.join(project_root, 'Configuration', 'Calibration', 'Calibration_*.yaml')))


def Station_Files(project_root: str) -> tp.List[str]:
    """
    Description:
        The shipped station files, Configuration/Station/Station_*.yaml.

    Args:
        (1) project_root [string]: The repository root.

    Returns:
        (1) parameter [Vector<string>]: Their paths, sorted.
    """

    return sorted(glob.glob(os.path.join(project_root, 'Configuration', 'Station', 'Station_*.yaml')))


def Load_Yaml(path: str) -> tp.Dict[str, tp.Any]:
    """
    Description:
        Parse a configuration file as plain YAML. The loader is not used: these tests compare the
        file's structure with the document, and a file the loader rejects still has one.

    Args:
        (1) path [string]: The file.

    Returns:
        (1) parameter [Dict<string, Any>]: The parsed file.
    """

    with open(path, encoding='utf-8') as file:
        return yaml.safe_load(file)


def Github_Anchor(heading: str) -> str:
    """
    Description:
        The anchor GitHub gives a heading: lower case, everything but letters, digits, '_', '-' and
        spaces removed, spaces turned into '-'. Duplicate headings (a '-1' suffix) do not occur in
        the files linked.

    Args:
        (1) heading [string]: The heading's title, without its #'s.

    Returns:
        (1) parameter [string]: The anchor, without '#'.
    """

    anchor = re.sub(r'[^\w\- ]', '', heading.strip().lower())
    return anchor.replace(' ', '-')


def Anchors(path: str) -> tp.Set[str]:
    """
    Description:
        Every heading anchor of a Markdown file. Headings inside fenced code are skipped.

    Args:
        (1) path [string]: The Markdown file.

    Returns:
        (1) parameter [Set<string>]: The anchors.
    """

    anchors = set()
    fenced = False
    for line in Read_Text(path).split('\n'):
        if line.startswith('```'):
            fenced = not fenced
        elif not fenced and re.match(r'#{1,6} ', line):
            anchors.add(Github_Anchor(line.lstrip('#')))

    return anchors


def test_the_configuration_table_names_every_section_of_every_mode_file(project_root) -> None:
    """
    Description:
        The Configuration table's Section column is exactly the sections of the shipped mode files:
        a section added to a mode file without a row, or a row whose section has left the file,
        fails here.
    """

    doc = Read_Text(os.path.join(project_root, CONST_CAPABILITIES_DOC))
    documented = set(Table_First_Column(Section(doc, '## Configuration'), 'Section'))
    in_files = set()
    for path in Mode_Files(project_root):
        in_files |= Sections_Of(Load_Yaml(path))

    assert in_files, 'No mode file found under Configuration/Mode/.'
    assert documented == in_files, ('Configuration table out of step with the mode files. Missing from the '
                                    'document: %s. Not in any mode file: %s.'
                                    % (sorted(in_files - documented), sorted(documented - in_files)))


def test_the_calibration_table_names_every_section_of_the_calibration_file(project_root) -> None:
    """
    Description:
        The Calibration table's Section column is exactly the sections of the shipped calibration
        file(s), in both directions.
    """

    doc = Read_Text(os.path.join(project_root, CONST_CAPABILITIES_DOC))
    documented = set(Table_First_Column(Section(doc, '## Calibration'), 'Section'))
    in_files = set()
    for path in Calibration_Files(project_root):
        in_files |= Sections_Of(Load_Yaml(path))

    assert in_files, 'No calibration file found under Configuration/Calibration/.'
    assert documented == in_files, ('Calibration table out of step with the calibration file. Missing from '
                                    'the document: %s. Not in the file: %s.'
                                    % (sorted(in_files - documented), sorted(documented - in_files)))


def test_the_station_table_names_every_section_of_the_station_file(project_root) -> None:
    """
    Description:
        The Station table's Section column is exactly the sections of the shipped station file(s), in
        both directions: the camera and the reference moved there from the mode files, and a section
        added to the station file without a row fails here.
    """

    doc = Read_Text(os.path.join(project_root, CONST_CAPABILITIES_DOC))
    documented = set(Table_First_Column(Section(doc, '## Station'), 'Section'))
    in_files = set()
    for path in Station_Files(project_root):
        in_files |= Sections_Of(Load_Yaml(path))

    assert in_files, 'No station file found under Configuration/Station/.'
    assert documented == in_files, ('Station table out of step with the station file. Missing from the document: '
                                    '%s. Not in the file: %s.' % (sorted(in_files - documented),
                                                                  sorted(documented - in_files)))


def test_every_key_path_the_document_names_exists_in_a_configuration_file(project_root) -> None:
    """
    Description:
        A dotted key path anywhere in the document ('General.Classification.Enabled',
        'Calibration.Solved'), whose first segment is a section the document's tables name, is a key
        of a shipped mode, station or calibration file. A key removed or renamed in the files, and still
        written in the prose, fails here.
    """

    doc = Read_Text(os.path.join(project_root, CONST_CAPABILITIES_DOC))
    roots = {name.split('.')[0]
             for heading in ('## Configuration', '## Station', '## Calibration')
             for name in Table_First_Column(Section(doc, heading), 'Section')}
    keys = set()
    for path in Mode_Files(project_root) + Station_Files(project_root) + Calibration_Files(project_root):
        keys |= Key_Paths(Load_Yaml(path))

    named = {match for span in CONST_CODE_SPAN.findall(doc) for match in CONST_KEY_PATH.findall(span)
             if match.split('.')[0] in roots}

    assert named, 'The document names no configuration key path; the pattern no longer matches it.'
    assert named <= keys, 'docs/capabilities.md names keys no configuration file has: %s.' % sorted(named - keys)


def Src_Packages(project_root: str) -> tp.List[str]:
    """
    Description:
        The packages under src/: each directory holding Python source at any depth. A directory
        left with only caches (__pycache__) is not a package.

    Args:
        (1) project_root [string]: The repository root.

    Returns:
        (1) parameter [Vector<string>]: Their names, sorted.
    """

    src = os.path.join(project_root, 'src')
    return sorted(name for name in os.listdir(src)
                  if os.path.isdir(os.path.join(src, name))
                  and glob.glob(os.path.join(src, name, '**', '*.py'), recursive=True))


def test_the_architecture_table_names_exactly_the_src_packages(project_root) -> None:
    """
    Description:
        The Architecture section's Package table lists every package under src/, and only those: a
        package added without a row, or a row whose package has been removed or renamed, fails here.
    """

    doc = Read_Text(os.path.join(project_root, CONST_CAPABILITIES_DOC))
    documented = Table_First_Column(Section(doc, '## Architecture'), 'Package')
    packages = Src_Packages(project_root)

    assert packages, 'No package found under src/.'
    assert sorted(documented) == packages, ('Architecture table out of step with src/. Missing from the '
                                            'document: %s. Not a package: %s.'
                                            % (sorted(set(packages) - set(documented)),
                                               sorted(set(documented) - set(packages))))


def test_the_modes_table_names_exactly_the_shipped_mode_files(project_root) -> None:
    """
    Description:
        The Modes table lists every mode file in Configuration/Mode/ — its mode and its file name — and
        nothing else.
    """

    doc = Read_Text(os.path.join(project_root, CONST_CAPABILITIES_DOC))
    body = Section(doc, '## Modes')
    files = [os.path.basename(path) for path in Mode_Files(project_root)]
    modes = [Hardware_And_Mode(path)[1] for path in Mode_Files(project_root)]
    rows = [line for line in body.split('\n') if line.startswith('|')][2:]
    documented_files = [CONST_CODE_SPAN.findall(row.split('|')[2])[0] for row in rows]

    assert sorted(Table_First_Column(body, 'Mode')) == sorted(modes)
    assert sorted(documented_files) == sorted(files)


def test_the_view_headings_are_the_view_switch_labels(project_root) -> None:
    """
    Description:
        The '###' headings under UI views are exactly the central-view switch's labels, in its order:
        a view added to the switch without a description, or one described that no longer exists,
        fails here.
    """

    doc = Read_Text(os.path.join(project_root, CONST_CAPABILITIES_DOC))
    labels = [label for _key, label in AnyScan_Window_Cls.CONST_VIEW_SEGMENTS]

    assert Subheadings(Section(doc, '## UI views'), 3) == labels


def test_the_live_and_trends_views_name_what_the_code_draws(project_root) -> None:
    """
    Description:
        Under Live: every Camera View render and every card title the window builds, in bold. Under
        Trends: every chart title. These are the names an operator sees, so the document uses them.
    """

    doc = Read_Text(os.path.join(project_root, CONST_CAPABILITIES_DOC))
    live = Section(doc, '### Live')
    trends = Section(doc, '### Trends')
    window = Read_Text(os.path.join(project_root, 'src', 'UI', 'Core.py'))
    charts = Read_Text(os.path.join(project_root, 'src', 'UI', 'Views', 'Trends.py'))
    renders = [label for _key, label in View_Toggle_Cls.CONST_SEGMENTS]
    cards = CONST_CARD_HEAD.findall(window)
    titles = CONST_CHART_CARD.findall(charts)

    assert cards and titles, 'The card or chart pattern no longer matches the source.'
    assert [name for name in renders + cards if '**%s**' % name not in live] == []
    assert [name for name in titles if '**%s**' % name not in trends] == []


def test_the_records_tables_name_exactly_what_the_code_writes(project_root) -> None:
    """
    Description:
        The capture-set table names exactly the files a set holds, the run-summary table exactly the
        CSV's columns, and the station-event table exactly the event types — in both directions.
    """

    doc = Read_Text(os.path.join(project_root, CONST_CAPABILITIES_DOC))
    body = Section(doc, '## Records and exports')
    events = set(CONST_STATION_EVENT_TYPES.values()) | {CONST_CYCLE_START, CONST_CYCLE_DONE}

    assert sorted(Table_First_Column(body, 'File')) == sorted(CONST_CAPTURE_SUFFIXES)
    assert Table_First_Column(body, 'Column') == list(CONST_CSV_COLUMNS)
    assert set(Table_First_Column(body, 'Event')) == events


def test_every_relative_link_and_anchor_resolves(project_root) -> None:
    """
    Description:
        Every relative link in the document reaches a file, and every '#anchor' a heading in it, so a
        renamed design decision or known issue breaks this test rather than the reader's click.
    """

    doc_path = os.path.join(project_root, CONST_CAPABILITIES_DOC)
    broken = []
    for target in CONST_LINK.findall(Read_Text(doc_path)):
        if re.match(r'[a-z]+:', target):
            continue
        file_part, _, anchor = target.partition('#')
        path = os.path.normpath(os.path.join(os.path.dirname(doc_path), file_part)) if file_part else doc_path
        if not os.path.isfile(path):
            broken.append(target)
        elif anchor and anchor not in Anchors(path):
            broken.append(target)

    assert broken == [], 'Broken links in docs/capabilities.md: %s' % broken


def Git(project_root: str, *arguments: str) -> subprocess.CompletedProcess:
    """
    Description:
        Run git in the repository.

    Args:
        (1) project_root [string]: The repository root.
        (2) arguments [Vector<string>]: git's arguments.

    Returns:
        (1) parameter [subprocess.CompletedProcess(object)]: The finished run.
    """

    return subprocess.run(['git', '-C', project_root] + list(arguments), capture_output=True, text=True, timeout=60)


def test_every_code_change_since_the_last_review_updated_the_document(project_root) -> None:
    """
    Description:
        The drift tests catch a name that changed; they cannot catch a behaviour that changed under
        the same name. So a review is required, and recorded: the document names the commit it was
        last reviewed against, and every later commit that changes src/, App/, Configuration/ or
        Example/ must also change the document, either its content or, when the change affects no
        capability, that line. A code commit that skips the review fails here. A repository copied
        without its git history skips the check, naming why.
    """

    if Git(project_root, 'rev-parse', '--git-dir').returncode != 0:
        pytest.skip('REVIEW CHECK NOT RUN: %s is not a git repository, so the commits since the last '
                    'review cannot be listed.' % project_root)

    doc = Read_Text(os.path.join(project_root, CONST_CAPABILITIES_DOC))
    match = CONST_LAST_REVIEWED.search(doc)
    assert match, "docs/capabilities.md has no 'Last reviewed against the code at commit `<hash>`' line."
    reviewed = match.group(1)
    if Git(project_root, 'merge-base', '--is-ancestor', reviewed, 'HEAD').returncode != 0:
        pytest.fail('The last-reviewed commit %s is not in this branch\'s history (rewritten, or a shallow '
                    'clone). Review the document against the code and name HEAD\'s commit.' % reviewed)

    code_commits = Git(project_root, 'log', '--format=%h', '%s..HEAD' % reviewed, '--',
                       *CONST_REVIEWED_PATHS).stdout.split()
    unreviewed = [commit for commit in code_commits
                  if CONST_CAPABILITIES_DOC.replace(os.sep, '/') not in
                  Git(project_root, 'show', '--name-only', '--format=', commit).stdout.split('\n')]

    assert unreviewed == [], ('Commits changing the code since the last review (%s) left docs/capabilities.md '
                              'untouched: %s. Review the document against each: update it, or, when no '
                              'capability changed, move its Last reviewed line, in the same commit.'
                              % (reviewed, ', '.join(unreviewed)))
