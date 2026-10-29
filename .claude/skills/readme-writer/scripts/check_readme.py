#!/usr/bin/env python3
"""Check a GitHub README for objective defects and report judgement calls.

Standard library only. Run from anywhere:

    python3 check_readme.py README.md
    python3 check_readme.py docs/README.md --root . --max-visible 250

Every finding is printed as ``path:line: LEVEL [check] message``:

- ERROR: an objective defect (a missing file, a broken anchor, a fence without a
  language tag, an absolute local path, an incomplete <picture>, a semicolon in
  prose, ...). Exit code 1.
- WARN: a judgement call for the author (length, filler words, table alignment,
  size budget, ...). Does not change the exit code.
- INFO: facts the author verifies by hand (static badges, Mermaid blocks, counts).
"""

import argparse
import fnmatch
import html
import json
import os
import re
import sys
import unicodedata
import urllib.parse
from dataclasses import dataclass, field

DEFAULT_MIN_ALT_WORDS = 12
DEFAULT_MAX_VISIBLE = 250
DEFAULT_MAX_IMAGE_KB = 400
DEFAULT_MAX_MEDIA_MB = 6.0
MAX_VISIBLE_TABLE_COLUMNS = 6

BADGE_HOSTS = ('img.shields.io', 'badgen.net', 'badge.fury.io', 'codecov.io', 'coveralls.io',
               'readthedocs.org', 'zenodo.org/badge', 'api.securityscorecards.dev', 'pepy.tech')
ALERT_TYPES = ('NOTE', 'TIP', 'IMPORTANT', 'WARNING', 'CAUTION')
FILLER_WORDS = ('simply', 'just', 'easy', 'easily', 'powerful', 'seamless', 'seamlessly',
                'effortless', 'effortlessly', 'blazing', 'cutting-edge', 'state-of-the-art',
                'revolutionary', 'robust and scalable', 'best-in-class', 'obviously')
LICENCE_IDS = (('MIT License', 'mit'), ('Apache License', 'apache'),
               ('GNU AFFERO GENERAL PUBLIC LICENSE', 'agpl'),
               ('GNU LESSER GENERAL PUBLIC LICENSE', 'lgpl'),
               ('GNU GENERAL PUBLIC LICENSE', 'gpl'), ('Mozilla Public License', 'mpl'),
               ('BSD', 'bsd'), ('The Unlicense', 'unlicense'), ('ISC License', 'isc'),
               ('Creative Commons', 'cc'), ('Boost Software License', 'bsl'))

SECRET_PATTERNS = (
    (r'ghp_[A-Za-z0-9]{20,}', 'a GitHub token'),
    (r'github_pat_[A-Za-z0-9_]{20,}', 'a GitHub token'),
    (r'AKIA[0-9A-Z]{16}', 'an AWS access key'),
    (r'-----BEGIN [A-Z ]*PRIVATE KEY-----', 'a private key'),
    (r'\bsk-[A-Za-z0-9]{20,}', 'an API key'),
    (r'\bxox[baprs]-[A-Za-z0-9-]{10,}', 'a Slack token'),
)
LOCAL_PATH_PATTERNS = (
    r'(?<![\w.~])/Users/[^\s)"\'`<>]+',
    r'(?<![\w.~])/home/[a-z_][\w.-]*/[^\s)"\'`<>]*',
    r'\b[A-Za-z]:\\Users\\[^\s)"\'`<>]*',
    r'file://[^\s)"\'`<>]+',
    # Machine-specific temporary directories: macOS's per-user /var/folders/... and /private/...
    # (where /tmp and /var resolve), which a script's output shows when it prints a resolved path.
    r'(?<![\w.~])/private/[^\s)"\'`<>]+',
    r'(?<![\w.~])/var/folders/[^\s)"\'`<>]+',
)
# A bare /tmp/... is portable (an output directory in a documented command), but it may also be a
# machine's output pasted verbatim: a judgement call, for the project reference to accept.
TMP_PATH_PATTERN = r'(?<![\w.~/])/tmp/[^\s)"\'`<>]*'

# The project's exceptions (readme-writer's project layer, as check_style.json is project-style-rpx's), each with its
# reason and reported as an INFO line when it applies:
#   uncaptioned_figures  figures that are not figures - a brand mark in the header - listed by their image file; they
#                        need no caption and are not numbered;
#   image_budgets        per-image size budgets by glob over the path as the README writes it ([{"glob", "max_kb",
#                        "reason"}], the first match wins), for media the project decided may be larger (an animated preview);
#   media_budget         the budget of all images shown together ({"max_mb", "reason"}).
# Precedence for both budgets: an explicit command-line option, then the file, then the defaults.
CONFIG_RELATIVE = os.path.join('.claude', 'skills', 'readme-writer', 'references', 'check_readme.json')

FENCE_RE = re.compile(r'^( {0,3})(`{3,}|~{3,})(.*)$')
HEADING_RE = re.compile(r'^ {0,3}(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$')
IMAGE_MD_RE = re.compile(r'!\[([^\]]*)\]\(\s*<?([^)\s>]*)>?(?:\s+"[^"]*")?\s*\)')
LINK_MD_RE = re.compile(r'(?<!!)\[([^\]]*)\]\(\s*<?([^)\s>]*)>?(?:\s+"[^"]*")?\s*\)')
REF_DEF_RE = re.compile(r'^ {0,3}\[([^\]]+)\]:\s*<?(\S+?)>?(?:\s+["\'(].*)?$')
TAG_RE = re.compile(r'<(img|source|a)\b([^>]*)>', re.IGNORECASE)
ATTR_RE = re.compile(r'([\w-]+)\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s>]+))')
CAPTION_RE = re.compile(r'^\s*(?:<[a-z]+[^>]*>\s*)*(?:\*\*|\*|_)?Figure\s+(\d+)\s*[:.]', re.IGNORECASE)
CLOSING_TAG_RE = re.compile(r'^\s*</(p|div|a|center)>\s*$', re.IGNORECASE)
IPV4_RE = re.compile(r'(?<![\w.])(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(?!\w|\.\d)')
EMOJI_RE = re.compile('[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U0001F000-\U0001F2FF☀-⛿]')


@dataclass
class Finding:
    level: str
    check: str
    line: int
    message: str


@dataclass
class Readme:
    path: str
    root: str
    lines: list
    prose: list            # lines with code fences, inline code and comments blanked
    in_fence: list         # per line: True inside a fenced code block (fence lines included)
    in_details: list       # per line: depth of <details> nesting
    fences: list = field(default_factory=list)   # (start line, info string, end line or None)


# ---------------------------------------------------------------- parsing


def blank(text):
    """Replace every character except newlines by a space, keeping offsets."""
    return re.sub(r'[^\n]', ' ', text)


def parse(path, root=None):
    with open(path, encoding='utf-8') as handle:
        text = handle.read()
    lines = text.split('\n')
    root = os.path.abspath(root or os.path.dirname(os.path.abspath(path)))
    in_fence, fences, prose = [], [], []
    open_fence = None
    for number, line in enumerate(lines, 1):
        match = FENCE_RE.match(line)
        if open_fence is None and match:
            open_fence = (match.group(2)[0], len(match.group(2)))
            fences.append([number, match.group(3).strip(), None])
            in_fence.append(True)
            prose.append('')
            continue
        if open_fence is not None:
            in_fence.append(True)
            prose.append('')
            if match and match.group(2)[0] == open_fence[0] and len(match.group(2)) >= open_fence[1] \
                    and not match.group(3).strip():
                fences[-1][2] = number
                open_fence = None
            continue
        in_fence.append(False)
        prose.append(line)
    joined = '\n'.join(prose)
    joined = re.sub(r'<!--.*?-->', lambda m: blank(m.group(0)), joined, flags=re.DOTALL)
    joined = re.sub(r'(`+)(?!`)(.+?)(?<!`)\1(?!`)', lambda m: blank(m.group(0)), joined)
    prose = joined.split('\n')
    in_details, depth = [], 0
    for line in prose:
        opened = len(re.findall(r'<details\b', line, re.IGNORECASE))
        closed = len(re.findall(r'</details>', line, re.IGNORECASE))
        depth += opened
        in_details.append(depth)
        depth = max(0, depth - closed)
    return Readme(path, root, lines, prose, in_fence, in_details, [tuple(f) for f in fences])


def strip_inline_markdown(text):
    text = re.sub(r'!\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'(\*\*|__|\*|_|~~|`)', '', text)
    return html.unescape(text)


def slug(text):
    """GitHub's heading anchor: lower case, punctuation dropped, spaces to hyphens."""
    text = strip_inline_markdown(text).strip().lower()
    kept = []
    for char in text:
        category = unicodedata.category(char)
        if char in ' -_' or category[0] in 'LN' or category == 'Mn':
            kept.append('-' if char == ' ' else char)
    return ''.join(kept)


def headings(readme):
    """(line, level, text, anchor) for each heading, with GitHub's -1, -2 suffixes."""
    seen, result = {}, []
    for number, line in enumerate(readme.prose, 1):
        match = HEADING_RE.match(line)
        if not match:
            continue
        base = slug(match.group(2))
        count = seen.get(base, 0)
        seen[base] = count + 1
        result.append((number, len(match.group(1)), match.group(2), base if count == 0 else '%s-%d' % (base, count)))
    return result


def explicit_anchors(readme):
    anchors = set()
    for line in readme.prose:
        for match in re.finditer(r'<a\b[^>]*\b(?:id|name)\s*=\s*["\']([^"\']+)["\']', line, re.IGNORECASE):
            anchors.add(match.group(1))
    return anchors


def attributes(text):
    result = {}
    for match in ATTR_RE.finditer(text):
        value = next(v for v in match.groups()[2:] if v is not None)
        result[match.group(1).lower()] = html.unescape(value)
    return result


def is_external(target):
    return bool(re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target)) or target.startswith('//')


def is_badge(src):
    lowered = src.lower()
    return any(host in lowered for host in BADGE_HOSTS) or lowered.endswith('/badge.svg') \
        or '/badge.svg?' in lowered or '/badges/' in lowered


def line_of(readme, text, offset):
    return text.count('\n', 0, offset) + 1


# ---------------------------------------------------------------- references


@dataclass
class Ref:
    kind: str      # 'link', 'image', 'source'
    line: int
    target: str
    alt: str = None
    attrs: dict = None


def collect_refs(readme):
    """Every link and image target in the prose, Markdown and HTML."""
    refs = []
    text = '\n'.join(readme.prose)
    images_masked = text
    for match in IMAGE_MD_RE.finditer(text):
        refs.append(Ref('image', line_of(readme, text, match.start()), match.group(2), alt=match.group(1)))
        images_masked = images_masked[:match.start()] + 'x' * (match.end() - match.start()) + images_masked[match.end():]
    for match in LINK_MD_RE.finditer(images_masked):
        refs.append(Ref('link', line_of(readme, text, match.start()), match.group(2)))
    for match in TAG_RE.finditer(text):
        tag, attrs = match.group(1).lower(), attributes(match.group(2))
        number = line_of(readme, text, match.start())
        if tag == 'img' and 'src' in attrs:
            refs.append(Ref('image', number, attrs['src'], alt=attrs.get('alt'), attrs=attrs))
        elif tag == 'source' and 'srcset' in attrs:
            for candidate in attrs['srcset'].split(','):
                if candidate.strip():
                    refs.append(Ref('source', number, candidate.strip().split()[0], attrs=attrs))
        elif tag == 'a' and 'href' in attrs:
            refs.append(Ref('link', number, attrs['href']))
    for number, line in enumerate(readme.prose, 1):
        match = REF_DEF_RE.match(line)
        if match:
            refs.append(Ref('link', number, match.group(2)))
    return refs


def resolve(readme, target):
    """The local file a relative target points to, and its anchor."""
    path, _, anchor = target.partition('#')
    path = urllib.parse.unquote(path.split('?')[0])
    base = os.path.dirname(os.path.abspath(readme.path))
    return (os.path.normpath(os.path.join(base, path)) if path else None), anchor


# ---------------------------------------------------------------- checks


def check_links(readme, refs, findings):
    own = {h[3] for h in headings(readme)} | explicit_anchors(readme)
    other_cache = {}
    for ref in refs:
        target = ref.target.strip()
        if not target or is_external(target):
            continue
        if target.startswith('/'):
            findings.append(Finding('ERROR', 'links', ref.line, '%s is absolute; use a path relative to the README' % target))
            continue
        local, anchor = resolve(readme, target)
        if local is None:
            if anchor and urllib.parse.unquote(anchor) not in own:
                findings.append(Finding('ERROR', 'anchors', ref.line, '#%s matches no heading or anchor' % anchor))
            continue
        if not os.path.exists(local):
            findings.append(Finding('ERROR', 'links', ref.line, '%s does not exist' % target))
            continue
        if not os.path.abspath(local).startswith(readme.root + os.sep) and os.path.abspath(local) != readme.root:
            findings.append(Finding('ERROR', 'links', ref.line, '%s points outside the repository' % target))
        if anchor and local.lower().endswith('.md') and os.path.isfile(local):
            if local not in other_cache:
                other = parse(local, readme.root)
                other_cache[local] = {h[3] for h in headings(other)} | explicit_anchors(other)
            if urllib.parse.unquote(anchor) not in other_cache[local]:
                findings.append(Finding('ERROR', 'anchors', ref.line, '%s: #%s matches no heading there' % (target, anchor)))


def pictures(readme):
    """(start line, end line, body) of each <picture> element."""
    text = '\n'.join(readme.prose)
    result = []
    for match in re.finditer(r'<picture\b[^>]*>(.*?)</picture>', text, re.IGNORECASE | re.DOTALL):
        result.append((line_of(readme, text, match.start()), line_of(readme, text, match.end()), match.group(1)))
    opened = len(re.findall(r'<picture\b', text, re.IGNORECASE))
    return result, opened


def check_pictures(readme, findings):
    found, opened = pictures(readme)
    if opened != len(found):
        findings.append(Finding('ERROR', 'picture', 1, '%d <picture> opened, %d closed' % (opened, len(found))))
    for start, _, body in found:
        sources = [attributes(m.group(1)) for m in re.finditer(r'<source\b([^>]*)>', body, re.IGNORECASE)]
        images = [attributes(m.group(1)) for m in re.finditer(r'<img\b([^>]*)>', body, re.IGNORECASE)]
        dark = [s for s in sources if re.search(r'prefers-color-scheme\s*:\s*dark', s.get('media', ''))]
        if not dark:
            findings.append(Finding('ERROR', 'picture', start, '<picture> has no <source media="(prefers-color-scheme: dark)">'))
        for source in sources:
            if not source.get('srcset'):
                findings.append(Finding('ERROR', 'picture', start, '<source> without srcset'))
            if not source.get('media'):
                findings.append(Finding('ERROR', 'picture', start, '<source> without media'))
        if len(images) != 1:
            findings.append(Finding('ERROR', 'picture', start, '<picture> needs exactly one <img> fallback, found %d' % len(images)))
            continue
        image = images[0]
        if not image.get('src'):
            findings.append(Finding('ERROR', 'picture', start, '<img> without src'))
        if dark and image.get('src') and dark[0].get('srcset', '').split()[0:1] == [image['src']]:
            findings.append(Finding('ERROR', 'picture', start, 'the dark <source> and the <img> show the same file'))
        if not image.get('width') and not image.get('height'):
            findings.append(Finding('WARN', 'picture', start, '<img> has no explicit width'))


def figures(readme, with_source=False):
    """(line, end line, alt) of each figure: a <picture>, or a non-badge image outside one (with its image file last)."""
    found, _ = pictures(readme)
    spans = [(start, end) for start, end, _ in found]
    result = []
    for start, end, body in found:
        alt, source = None, None
        match = re.search(r'<img\b([^>]*)>', body, re.IGNORECASE)
        if match:
            alt, source = attributes(match.group(1)).get('alt'), attributes(match.group(1)).get('src')
        result.append((start, end, alt, source))
    for ref in collect_refs(readme):
        if ref.kind != 'image' or is_badge(ref.target) or any(s <= ref.line <= e for s, e in spans):
            continue
        result.append((ref.line, ref.line, ref.alt, ref.target))
    return sorted(item if with_source else item[:3] for item in result)


def load_config(readme, findings):
    """The project's check_readme.json under the README's root ({} without one); a broken file is an ERROR."""
    path = os.path.join(readme.root, CONFIG_RELATIVE)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding='utf-8') as handle:
            config = json.load(handle)
        for entry in config.get('uncaptioned_figures', []):
            if not isinstance(entry, dict) or not entry.get('src') or not entry.get('reason'):
                raise ValueError('each uncaptioned_figures entry needs "src" and "reason"')
        for entry in config.get('image_budgets', []):
            if not isinstance(entry, dict) or not entry.get('glob') or not entry.get('reason') \
                    or not _positive(entry.get('max_kb')):
                raise ValueError('each image_budgets entry needs "glob", a positive "max_kb" and "reason"')
        if 'media_budget' in config:
            entry = config['media_budget']
            if not isinstance(entry, dict) or not entry.get('reason') or not _positive(entry.get('max_mb')):
                raise ValueError('media_budget needs a positive "max_mb" and "reason"')
        return config
    except (ValueError, OSError) as error:
        findings.append(Finding('ERROR', 'config', 1, '%s: %s' % (CONFIG_RELATIVE, error)))
        return {}


def _positive(value):
    """True for a number above zero (a bool is not a number here)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def check_figures(readme, min_alt_words, findings, config):
    numbers = []
    exempt = {entry['src']: entry['reason'] for entry in config.get('uncaptioned_figures', [])}
    for start, end, alt, source in figures(readme, with_source=True):
        words = len((alt or '').split())
        if words < min_alt_words:
            findings.append(Finding('ERROR', 'alt-text', start, 'alt text has %d words, at least %d needed' % (words, min_alt_words)))
        caption, number = None, end + 1
        while number <= len(readme.prose):
            line = readme.prose[number - 1]
            if line.strip() and not CLOSING_TAG_RE.match(line):
                caption = CAPTION_RE.match(line)
                break
            number += 1
        if source in exempt:
            findings.append(Finding('INFO', 'caption', start, 'no caption needed (check_readme.json): %s' % exempt[source]))
        elif not caption:
            findings.append(Finding('ERROR', 'caption', start, 'no "Figure N:" caption below this figure'))
        else:
            numbers.append((start, int(caption.group(1))))
    for index, (start, value) in enumerate(numbers, 1):
        if value != index:
            findings.append(Finding('ERROR', 'caption', start, 'caption numbered %d, expected %d (numbered in order)' % (value, index)))
    for ref in collect_refs(readme):
        if ref.kind == 'image' and is_badge(ref.target) and not (ref.alt or '').strip():
            findings.append(Finding('ERROR', 'alt-text', ref.line, 'badge without alt text'))


def check_fences(readme, findings):
    for start, info, end in readme.fences:
        if not info:
            findings.append(Finding('ERROR', 'fences', start, 'code fence without a language tag (use text for plain output)'))
        if end is None:
            findings.append(Finding('ERROR', 'fences', start, 'code fence is never closed'))
        language = info.split()[0].lower() if info else ''
        if language in ('bash', 'sh', 'shell', 'zsh') and end:
            for number in range(start + 1, end):
                if re.match(r'^\s*\$ ', readme.lines[number - 1]):
                    findings.append(Finding('WARN', 'fences', number, 'shell prompt "$ " inside a copy-paste block (use console for transcripts)'))
                    break


def check_details(readme, findings):
    depth = 0
    for number, line in enumerate(readme.prose, 1):
        depth += len(re.findall(r'<details\b', line, re.IGNORECASE)) - len(re.findall(r'</details>', line, re.IGNORECASE))
        if depth < 0:
            findings.append(Finding('ERROR', 'details', number, '</details> without <details>'))
            depth = 0
        if re.search(r'</summary>\s*$', line, re.IGNORECASE) and number < len(readme.prose) \
                and readme.lines[number].strip():
            findings.append(Finding('ERROR', 'details', number, 'no blank line after </summary>: the Markdown below it renders as text'))
    if depth > 0:
        findings.append(Finding('ERROR', 'details', len(readme.lines), '%d <details> never closed' % depth))


def check_alerts(readme, findings):
    count = 0
    for number, line in enumerate(readme.prose, 1):
        match = re.match(r'^\s*>\s*\[!(\w+)\](.*)$', line)
        if not match:
            continue
        count += 1
        if match.group(1) not in ALERT_TYPES:
            findings.append(Finding('ERROR', 'alerts', number, '[!%s] is not a GitHub alert type (%s)' % (match.group(1), ', '.join(ALERT_TYPES))))
        if match.group(2).strip():
            findings.append(Finding('ERROR', 'alerts', number, 'text on the [!%s] line: GitHub renders it as a plain quote' % match.group(1)))
        previous = readme.prose[number - 2] if number > 1 else ''
        if previous.strip().startswith('>'):
            findings.append(Finding('ERROR', 'alerts', number, 'an alert must start its own blockquote'))
    if count > 2:
        findings.append(Finding('WARN', 'alerts', 1, '%d alerts; keep them for what readers must not miss' % count))


def check_headings(readme, findings):
    found = headings(readme)
    top = [h for h in found if h[1] == 1]
    if len(top) != 1:
        findings.append(Finding('WARN', 'headings', top[1][0] if len(top) > 1 else 1, '%d level-1 headings, expected one title' % len(top)))
    for previous, current in zip(found, found[1:]):
        if current[1] > previous[1] + 1:
            findings.append(Finding('WARN', 'headings', current[0], 'heading level jumps from %d to %d' % (previous[1], current[1])))


def check_contents(readme, findings):
    found = headings(readme)
    contents = next((h for h in found if re.fullmatch(r'(table of )?contents', strip_inline_markdown(h[2]).strip(), re.IGNORECASE)), None)
    if contents is None:
        return
    end = next((h[0] for h in found if h[0] > contents[0] and h[1] <= contents[1]), len(readme.prose) + 1)
    listed = set()
    for number in range(contents[0] + 1, end):
        listed |= {m.group(2)[1:] for m in LINK_MD_RE.finditer(readme.prose[number - 1]) if m.group(2).startswith('#')}
    by_anchor = {h[3]: h for h in found}
    for anchor in sorted(listed):
        heading = by_anchor.get(anchor)
        if heading and readme.in_details[heading[0] - 1]:
            findings.append(Finding('WARN', 'contents', contents[0], 'Contents lists #%s, which is inside <details>' % anchor))
    for heading in found:
        if heading[1] == contents[1] and heading is not contents and heading[0] > contents[0] \
                and not readme.in_details[heading[0] - 1] and heading[3] not in listed:
            findings.append(Finding('WARN', 'contents', heading[0], 'visible section "%s" is not in Contents' % strip_inline_markdown(heading[2])))


def check_badges(readme, refs, findings):
    licence_file = next((os.path.join(readme.root, name) for name in ('LICENSE', 'LICENSE.md', 'LICENSE.txt', 'LICENCE', 'COPYING')
                         if os.path.isfile(os.path.join(readme.root, name))), None)
    licence_id = None
    if licence_file:
        with open(licence_file, encoding='utf-8', errors='replace') as handle:
            head = handle.read(2000)
        licence_id = next((ident for marker, ident in LICENCE_IDS if marker.lower() in head.lower()), None)
    for ref in refs:
        if ref.kind != 'image' or not is_badge(ref.target):
            continue
        decoded = urllib.parse.unquote(ref.target).lower()
        workflow = re.search(r'github\.com/[^/]+/[^/]+/actions/workflows/([^/]+)/badge\.svg', decoded)
        if workflow and not os.path.isfile(os.path.join(readme.root, '.github', 'workflows', workflow.group(1))):
            findings.append(Finding('ERROR', 'badges', ref.line, 'CI badge for .github/workflows/%s, which does not exist' % workflow.group(1)))
        elif 'licen' in decoded or 'licen' in (ref.alt or '').lower():
            if not licence_file:
                findings.append(Finding('ERROR', 'badges', ref.line, 'licence badge but no LICENSE file'))
            elif licence_id and licence_id not in decoded + ' ' + (ref.alt or '').lower():
                findings.append(Finding('ERROR', 'badges', ref.line, 'licence badge does not match LICENSE (%s)' % licence_id))
        elif '/badge/' in decoded:
            findings.append(Finding('INFO', 'badges', ref.line, 'static badge "%s": confirm its claim against its source' % (ref.alt or ref.target)))


def check_leaks(readme, findings):
    for number, line in enumerate(readme.lines, 1):
        for pattern in LOCAL_PATH_PATTERNS:
            for match in re.finditer(pattern, line):
                findings.append(Finding('ERROR', 'local-paths', number, 'absolute local path %s' % match.group(0)))
        for match in re.finditer(TMP_PATH_PATTERN, line):
            findings.append(Finding('WARN', 'local-paths', number,
                                    '%s: a temporary path - fine as a documented output directory, not as pasted output' % match.group(0)))
        for pattern, what in SECRET_PATTERNS:
            if re.search(pattern, line):
                findings.append(Finding('ERROR', 'secrets', number, 'looks like %s' % what))
        for match in IPV4_RE.finditer(line):
            octets = [int(g) for g in match.groups()]
            if all(o <= 255 for o in octets) and match.group(0) not in ('127.0.0.1', '0.0.0.0'):
                findings.append(Finding('WARN', 'hosts', number, '%s looks like an IP address' % match.group(0)))


def check_wording(readme, findings):
    filler = re.compile(r'\b(%s)\b' % '|'.join(re.escape(w) for w in FILLER_WORDS), re.IGNORECASE)
    for number, line in enumerate(readme.prose, 1):
        text = re.sub(r'<[^>]+>|\]\([^)]*\)', ' ', line)
        for match in filler.finditer(text):
            findings.append(Finding('WARN', 'wording', number, 'filler or marketing word "%s"' % match.group(1)))
        if re.search(r'[A-Za-z0-9)]!(\s|$)', re.sub(r'\[!\w+\]', '', text)):
            findings.append(Finding('WARN', 'wording', number, 'exclamation mark'))
        if EMOJI_RE.search(line):
            findings.append(Finding('WARN', 'wording', number, 'emoji'))


def check_semicolons(readme, findings):
    """No semicolon in prose. Code blocks and inline code are already blanked in readme.prose; HTML tags
    and autolinks, link targets, HTML entities and bare URLs are taken out here, since a semicolon
    there is syntax, not punctuation."""
    for number, line in enumerate(readme.prose, 1):
        text = re.sub(r'<[^>]*>', ' ', line)
        text = re.sub(r'\]\([^)]*\)', ']', text)
        text = re.sub(r'&(#\d+|#x[0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);', ' ', text)
        text = re.sub(r'\b[a-zA-Z][a-zA-Z0-9+.-]*://\S+', ' ', text)
        if ';' in text:
            findings.append(Finding('ERROR', 'semicolons', number,
                                    'a semicolon in prose: make it two sentences, a comma, a colon or a dash'))


def split_row(line):
    return [cell.strip() for cell in re.split(r'(?<!\\)\|', line.strip().strip('|'))]


def check_tables(readme, findings):
    number = 1
    while number < len(readme.prose):
        header, rule = readme.prose[number - 1], readme.prose[number]
        if '|' in header and re.fullmatch(r'\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*', rule):
            aligns = split_row(rule)
            rows, cursor = [], number + 1
            while cursor < len(readme.prose) and '|' in readme.prose[cursor]:
                rows.append(split_row(readme.prose[cursor]))
                cursor += 1
            if not readme.in_details[number - 1] and len(aligns) > MAX_VISIBLE_TABLE_COLUMNS:
                findings.append(Finding('WARN', 'tables', number, '%d columns in the visible part (at most %d); move it into <details>' % (len(aligns), MAX_VISIBLE_TABLE_COLUMNS)))
            for column, align in enumerate(aligns):
                cells = [strip_inline_markdown(r[column]) for r in rows if column < len(r)]
                numeric = [c for c in cells if c not in ('', '—', '-', '–')]
                if numeric and all(re.fullmatch(r'[−+-]?\d[\d,.\s]*\s*(%|[a-zA-Zµ°/²³]{0,4})', c) for c in numeric) \
                        and not align.endswith(':'):
                    findings.append(Finding('WARN', 'tables', number, 'numeric column %d is not right-aligned' % (column + 1)))
            number = cursor
        number += 1


def check_images(readme, refs, max_image_kb, max_media_mb, findings, config=None):
    """Size budgets: an explicit max_image_kb / max_media_mb (not None) wins, then check_readme.json, then the defaults."""
    config = config or {}
    budgets = [] if max_image_kb is not None else config.get('image_budgets', [])
    if max_media_mb is None:
        media = config.get('media_budget')
        max_media_mb = media['max_mb'] if media else DEFAULT_MAX_MEDIA_MB
        if media:
            findings.append(Finding('INFO', 'image-size', 1, 'media budget %.1f MB (check_readme.json): %s'
                                    % (max_media_mb, media['reason'])))
    default_kb = max_image_kb if max_image_kb is not None else DEFAULT_MAX_IMAGE_KB
    used = set()
    seen, total = set(), 0
    for ref in refs:
        if ref.kind not in ('image', 'source') or is_external(ref.target) or ref.target.startswith('/'):
            continue
        local, _ = resolve(readme, ref.target)
        if local is None or not os.path.isfile(local) or local in seen:
            continue
        seen.add(local)
        size = os.path.getsize(local)
        total += size
        entry = next((e for e in budgets if fnmatch.fnmatch(ref.target, e['glob'])), None)
        budget = entry['max_kb'] if entry else default_kb
        if entry and entry['glob'] not in used:
            used.add(entry['glob'])
            findings.append(Finding('INFO', 'image-size', ref.line, 'image budget %d KB for %s (check_readme.json): %s'
                                    % (budget, entry['glob'], entry['reason'])))
        if size > budget * 1024:
            findings.append(Finding('WARN', 'image-size', ref.line, '%s is %d KB (budget %d KB)' % (ref.target, size // 1024, budget)))
    if total > max_media_mb * 1024 * 1024:
        findings.append(Finding('WARN', 'image-size', 1, 'images shown total %.1f MB (budget %.1f MB)' % (total / 1048576, max_media_mb)))
    return len(seen), total


def summary(readme, max_visible, findings):
    visible = sum(1 for depth in readme.in_details if depth == 0)
    if visible > max_visible:
        findings.append(Finding('WARN', 'length', 1, '%d visible lines (outside <details>), budget %d' % (visible, max_visible)))
    mermaid = [f for f in readme.fences if f[1].split()[:1] == ['mermaid']]
    for start, _, _ in mermaid:
        findings.append(Finding('INFO', 'mermaid', start, 'Mermaid block: check its syntax (mmdc) or verify the diagram on GitHub after push'))
    shown = figures(readme)
    collapsed = sum(1 for start, _, _ in shown if readme.in_details[start - 1])
    return {'total lines': len(readme.lines), 'visible lines': visible, 'figures visible': len(shown) - collapsed,
            'figures collapsed': collapsed, 'mermaid blocks': len(mermaid)}


def run(path, root=None, min_alt_words=DEFAULT_MIN_ALT_WORDS, max_visible=DEFAULT_MAX_VISIBLE,
        max_image_kb=None, max_media_mb=None):
    """All checks on one README; returns (findings, facts). A budget left None comes from check_readme.json or the default."""
    readme = parse(path, root)
    refs = collect_refs(readme)
    findings = []
    config = load_config(readme, findings)
    check_links(readme, refs, findings)
    check_pictures(readme, findings)
    check_figures(readme, min_alt_words, findings, config)
    check_fences(readme, findings)
    check_details(readme, findings)
    check_alerts(readme, findings)
    check_headings(readme, findings)
    check_contents(readme, findings)
    check_badges(readme, refs, findings)
    check_leaks(readme, findings)
    check_wording(readme, findings)
    check_semicolons(readme, findings)
    check_tables(readme, findings)
    images, size = check_images(readme, refs, max_image_kb, max_media_mb, findings, config)
    facts = summary(readme, max_visible, findings)
    facts['images shown'] = images
    facts['image size [MB]'] = round(size / 1048576, 2)
    order = {'ERROR': 0, 'WARN': 1, 'INFO': 2}
    findings.sort(key=lambda f: (order[f.level], f.line))
    return findings, facts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('readme', nargs='?', default='README.md')
    parser.add_argument('--root', help='repository root (default: the README folder)')
    parser.add_argument('--min-alt-words', type=int, default=DEFAULT_MIN_ALT_WORDS)
    parser.add_argument('--max-visible', type=int, default=DEFAULT_MAX_VISIBLE, help='visible-line budget')
    parser.add_argument('--max-image-kb', type=int, default=None,
                        help='per-image budget; overrides check_readme.json (default %d)' % DEFAULT_MAX_IMAGE_KB)
    parser.add_argument('--max-media-mb', type=float, default=None,
                        help='budget of all images; overrides check_readme.json (default %.1f)' % DEFAULT_MAX_MEDIA_MB)
    parser.add_argument('--errors-only', action='store_true', help='print only ERROR findings')
    args = parser.parse_args(argv)
    if not os.path.isfile(args.readme):
        print('%s: no such file' % args.readme, file=sys.stderr)
        return 2
    findings, facts = run(args.readme, args.root, args.min_alt_words, args.max_visible, args.max_image_kb, args.max_media_mb)
    for finding in findings:
        if args.errors_only and finding.level != 'ERROR':
            continue
        print('%s:%d: %s [%s] %s' % (args.readme, finding.line, finding.level, finding.check, finding.message))
    counts = {level: sum(1 for f in findings if f.level == level) for level in ('ERROR', 'WARN', 'INFO')}
    print('-- %s' % ', '.join('%s: %s' % item for item in facts.items()))
    print('-- %d errors, %d warnings, %d notes' % (counts['ERROR'], counts['WARN'], counts['INFO']))
    return 1 if counts['ERROR'] else 0


if __name__ == '__main__':
    sys.exit(main())
