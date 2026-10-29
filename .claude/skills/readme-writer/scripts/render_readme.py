#!/usr/bin/env python3
"""Render a README the way GitHub does and report Markdown that did not render.

Two renderers:

- local (default): cmarkgfm, GitHub's own cmark-gfm. Not in the standard library; install it
  into a throwaway environment, never into the project:
      <explicit python> -m venv "$SCRATCH/readme-render" && "$SCRATCH/readme-render/bin/pip" install cmarkgfm
      "$SCRATCH/readme-render/bin/python" render_readme.py README.md --out "$SCRATCH/readme.html"
- --github-api: GitHub's Markdown API through the gh CLI. This UPLOADS the README text to
  GitHub; use it only with the user's consent.

Mermaid is not rendered by either; a Mermaid block is reported for checking after push.
Exit code 1 when leftover Markdown is found in the rendered text.
"""

import argparse
import html.parser
import json
import re
import subprocess
import sys

LEFTOVER = (
    (re.compile(r'\*\*\S'), 'literal ** (bold not rendered)'),
    (re.compile(r'!?\[[^\]]+\]\([^)]+\)'), 'literal [text](target) (link not rendered)'),
    (re.compile(r'^\s*#{1,6} \S'), 'literal # heading'),
    (re.compile(r'^\s*\|.*\|\s*$'), 'literal | table row'),
)
# GitHub turns > [!WARNING] into an alert after cmark-gfm has run, so only its API output can show
# whether an alert rendered; cmarkgfm keeps the marker in a plain quote.
ALERT = (re.compile(r'\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]'), 'literal alert marker')
SKIPPED_TAGS = ('code', 'pre', 'script', 'style')


class TextCollector(html.parser.HTMLParser):
    """The text nodes of rendered HTML, outside code."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.chunks = []

    def handle_starttag(self, tag, attrs):
        if tag in SKIPPED_TAGS:
            self.depth += 1

    def handle_endtag(self, tag):
        if tag in SKIPPED_TAGS and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if not self.depth:
            self.chunks.append(data)


def leftovers(rendered, alerts=False):
    """(problem, excerpt) for each piece of Markdown that survived rendering; alerts=True also
    reports an alert marker (only meaningful for GitHub's own rendering)."""
    collector = TextCollector()
    collector.feed(rendered)
    found = []
    for line in ''.join(collector.chunks).split('\n'):
        for pattern, problem in LEFTOVER + ((ALERT,) if alerts else ()):
            if pattern.search(line):
                found.append((problem, line.strip()[:100]))
    return found


def render_local(text):
    try:
        import cmarkgfm
        from cmarkgfm.cmark import Options
    except ImportError:
        sys.exit('cmarkgfm is not installed; see the docstring for a throwaway environment')
    return cmarkgfm.github_flavored_markdown_to_html(text, options=Options.CMARK_OPT_UNSAFE)


def render_github(text):
    payload = json.dumps({'text': text, 'mode': 'gfm'})
    result = subprocess.run(['gh', 'api', 'markdown', '--input', '-'], input=payload, capture_output=True, text=True)
    if result.returncode:
        sys.exit('gh api markdown failed: %s' % result.stderr.strip())
    return result.stdout


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('readme', nargs='?', default='README.md')
    parser.add_argument('--out', help='write the rendered HTML here')
    parser.add_argument('--github-api', action='store_true', help='render with GitHub (uploads the text; consent needed)')
    args = parser.parse_args(argv)
    with open(args.readme, encoding='utf-8') as handle:
        text = handle.read()
    rendered = render_github(text) if args.github_api else render_local(text)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as handle:
            handle.write('<!doctype html><meta charset="utf-8"><title>README render</title>\n' + rendered)
    found = leftovers(rendered, alerts=args.github_api)
    for problem, excerpt in found:
        print('LEFTOVER %s: %s' % (problem, excerpt))
    mermaid = len(re.findall(r'^\s*```mermaid', text, re.MULTILINE))
    alerts = len(re.findall(r'^\s*>\s*\[!\w+\]\s*$', text, re.MULTILINE))
    print('-- renderer: %s; %d leftover Markdown pieces; %d Mermaid blocks to verify after push'
          % ('GitHub API' if args.github_api else 'cmarkgfm (local)', len(found), mermaid))
    if alerts and not args.github_api:
        print('-- %d GitHub alerts: cmarkgfm shows them as quotes; check_readme.py checks their syntax' % alerts)
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
