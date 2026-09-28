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
# File Name: ../Example/UI/build_logo.py
## =========================================================================== ##

# System (Default)
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
# URL fetching (the pinned font) [Python standard library]
import urllib.request
# XML (Parse and rewrite the outlined SVG) [Python standard library]
import xml.etree.ElementTree as ET
# Typing (Support for type hints)
import typing as tp

"""
Description:
    Build the AnyScan logo (images/anyscan-logo.svg and its byte-identical copy App/assets/anyscan-logo.svg)
    from its text source, images/source/anyscan-logo-text.svg, by outlining every <text> in Inter 400.
    The shipped logo carries no text, so every renderer draws the same ink: PyQt5's QtSvg ignores CSS
    font rules and set the old text logo in the application's default font, which clipped its tagline
    on Linux (docs/design-decisions.md, "The logo's text is outlined").

    The font is not in the repository. It is fetched from a pinned google/fonts commit (or taken from
    --font) and its SHA-256 is checked; a missing or different file stops the build. Inkscape outlines
    the text (verified with 1.2.2), seeing ONLY that font through a private fontconfig file. The optical
    size of each text is pinned in the source (font-variation-settings), so Pango's automatic choice
    cannot change the outlines.

        python Example/UI/build_logo.py                        # rewrite both logo copies
        python Example/UI/build_logo.py --output /tmp/logo.svg  # build into one file only
        python Example/UI/build_logo.py --font Inter.ttf        # use a local copy of the pinned font

    After a rebuild, regenerate the diagram: python Example/UI/architecture_diagram.py.
"""
# The project folder, from this file's own location (Example/UI -> ..).
#   Unit [string]
CONST_PROJECT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
CONST_SOURCE_FILE = os.path.join(CONST_PROJECT_FOLDER, 'images', 'source', 'anyscan-logo-text.svg')
CONST_OUTPUT_FILES = (os.path.join(CONST_PROJECT_FOLDER, 'images', 'anyscan-logo.svg'),
                      os.path.join(CONST_PROJECT_FOLDER, 'App', 'assets', 'anyscan-logo.svg'))
# The font: Inter 4.001 (SIL OFL 1.1), at a pinned google/fonts commit, and its SHA-256.
#   Unit [string]
CONST_FONT_NAME = 'Inter[opsz,wght].ttf'
CONST_FONT_URL = ('https://raw.githubusercontent.com/google/fonts/e1d6480102fed30739fead0faee463101f892c8f/'
                  'ofl/inter/Inter%5Bopsz,wght%5D.ttf')
CONST_FONT_SHA256 = '29160a80ff49ddcab2c97711247e08b1fab27a484a329ce8b813d820dc559031'
# The Inkscape version the committed logo was built and verified with.
#   Unit [string]
CONST_INKSCAPE_VERIFIED = '1.2.2'
# Empty space around the ink on every side, in logo units. 5 keeps the height at 174 (ink 164 + 2 x 5),
# so the top bar's 54 px lockup keeps its scale.
#   Unit [-]
CONST_MARGIN = 5.0
# The SVG namespace, and the text-only properties dropped once the text is outlines.
#   Unit [string]
CONST_SVG_NS = 'http://www.w3.org/2000/svg'
CONST_TEXT_PROPERTIES = ('font-size', 'font-family', 'font-weight', 'font-variation-settings', 'text-anchor',
                         '-inkscape-font-specification', 'font-style', 'font-variant', 'font-stretch')


def Sha256(path: str) -> str:
    """
    Description:
        A file's SHA-256.

    Args:
        (1) path [string]: The file.

    Returns:
        (1) parameter [string]: The hex digest.
    """

    with open(path, 'rb') as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def Fetch_Font(font_path: tp.Optional[str], directory: str) -> str:
    """
    Description:
        The pinned font, verified: the given file, or a download of the pinned URL into a temporary
        directory. Stops the build when the file is absent, cannot be fetched, or is not the pinned file.

    Args:
        (1) font_path [string or None]: A local copy of the font, or None to download it.
        (2) directory [string]: The temporary directory a download goes into.

    Returns:
        (1) parameter [string]: The path of the verified font file, inside its own directory.
    """

    target = os.path.join(directory, 'fonts', CONST_FONT_NAME)
    os.makedirs(os.path.dirname(target))
    if font_path is not None:
        if not os.path.isfile(font_path):
            sys.exit('[ERROR] The font %s does not exist. Omit --font to download the pinned file.' % font_path)
        shutil.copyfile(font_path, target)
    else:
        print('[INFO] Downloading %s' % CONST_FONT_URL)
        try:
            with urllib.request.urlopen(CONST_FONT_URL, timeout=60) as response, open(target, 'wb') as handle:
                shutil.copyfileobj(response, handle)
        except OSError as error:
            sys.exit('[ERROR] The font could not be downloaded (%s). Download %s by hand and pass it with --font.'
                     % (error, CONST_FONT_URL))
    digest = Sha256(target)
    if digest != CONST_FONT_SHA256:
        sys.exit('[ERROR] The font is not the pinned file: SHA-256 %s, expected %s. The logo is built only from '
                 'the pinned Inter so that a rebuild reproduces it.' % (digest, CONST_FONT_SHA256))
    print('[INFO] Font verified: %s (SHA-256 %s).' % (CONST_FONT_NAME, digest[:16]))
    return target


def Check_Source(source: str) -> None:
    """
    Description:
        Stop unless every <text> in the source is set in Inter with a pinned optical size.

    Args:
        (1) source [string]: The text source SVG.
    """

    texts = re.findall(r'<text\b[^>]*>', source)
    if not texts:
        sys.exit('[ERROR] %s has no <text>: it is not the text source.' % CONST_SOURCE_FILE)
    for tag in texts:
        if 'font-family="Inter"' not in tag or not re.search(r"'opsz' \d+", tag):
            sys.exit('[ERROR] A <text> in the source is not Inter with a pinned optical size: %s' % tag)


def Clean(root: ET.Element) -> None:
    """
    Description:
        Rewrite Inkscape's output in the logo's own form: inline style becomes presentation attributes
        (every renderer, QtSvg included, reads those), Inkscape's ids and the text-only properties go,
        and an empty <defs> is removed.

    Args:
        (1) root [ET.Element(object)]: The outlined SVG's root, changed in place.
    """

    for element in root.iter():
        element.attrib.pop('id', None)
        style = element.attrib.pop('style', None)
        for declaration in (style or '').split(';'):
            if ':' in declaration:
                key, value = (part.strip() for part in declaration.split(':', 1))
                if key not in CONST_TEXT_PROPERTIES:
                    element.set(key, value)
        for key in [key for key in element.attrib if key in CONST_TEXT_PROPERTIES]:
            del element.attrib[key]
    for parent in list(root.iter()):
        for child in list(parent):
            if child.tag == '{%s}defs' % CONST_SVG_NS and len(child) == 0:
                parent.remove(child)
    root.attrib.pop('version', None)
    for key in [key for key in root.attrib if key.startswith('{')]:
        del root.attrib[key]


def Build(font: str, output: str, directory: str) -> None:
    """
    Description:
        Outline the source's text with Inkscape, clean the result and fit the viewBox to the ink bounds
        plus CONST_MARGIN.

    Args:
        (1) font [string]: The verified font file.
        (2) output [string]: Where the logo is written.
        (3) directory [string]: A temporary working directory.
    """

    with open(CONST_SOURCE_FILE, 'r', encoding='utf-8') as handle:
        source = handle.read()
    Check_Source(source)
    config = os.path.join(directory, 'fonts.conf')
    with open(config, 'w', encoding='utf-8') as handle:
        handle.write('<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n<fontconfig>\n'
                     '  <dir>%s</dir>\n  <cachedir>%s</cachedir>\n</fontconfig>\n'
                     % (os.path.dirname(font), os.path.join(directory, 'fccache')))
    env = dict(os.environ, FONTCONFIG_FILE=config)
    outlined = os.path.join(directory, 'outlined.svg')
    subprocess.run(['inkscape', CONST_SOURCE_FILE, '--export-text-to-path', '--export-plain-svg',
                    '--export-filename=' + outlined], env=env, check=True, stderr=subprocess.DEVNULL)
    query = subprocess.run(['inkscape', outlined, '--query-all'], env=env, check=True, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, universal_newlines=True).stdout
    # The first line is the whole drawing's visual bounding box (strokes included), relative to the
    # viewBox origin.
    bx, by, bw, bh = (float(v) for v in query.splitlines()[0].split(',')[1:5])
    ox, oy = (float(v) for v in re.search(r'viewBox="([-0-9.]+) ([-0-9.]+)', source).groups())

    ET.register_namespace('', CONST_SVG_NS)
    tree = ET.parse(outlined, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
    root = tree.getroot()
    Clean(root)
    vx, vy = round(ox + bx - CONST_MARGIN, 2), round(oy + by - CONST_MARGIN, 2)
    vw, vh = round(bw + 2 * CONST_MARGIN, 2), round(bh + 2 * CONST_MARGIN, 2)
    root.set('viewBox', '%g %g %g %g' % (vx, vy, vw, vh))
    root.set('width', '%g' % vw)
    root.set('height', '%g' % vh)
    ET.indent(tree, space='  ')
    body = ET.tostring(root, encoding='unicode').replace(' xmlns:svg="%s"' % CONST_SVG_NS, '')
    if re.search(r'<text\b|<tspan\b', body):
        sys.exit('[ERROR] Inkscape left text in the output; is the pinned font visible to it?')
    with open(output, 'w', encoding='utf-8') as handle:
        handle.write(body + '\n')
    print('[INFO] Wrote %s: ink %.2f..%.2f x %.2f..%.2f, viewBox %g %g %g %g (margin %g).'
          % (output, ox + bx, ox + bx + bw, oy + by, oy + by + bh, vx, vy, vw, vh, CONST_MARGIN))


def main() -> int:
    """
    Description:
        Parse the command line, fetch and verify the font, check Inkscape, and build the logo into
        both copies (or into --output).

    Returns:
        (1) parameter [int]: The exit code.
    """

    parser = argparse.ArgumentParser(description='Build the outlined AnyScan logo from its text source.')
    parser.add_argument('--output', default=None, help='Write only this file (default: both logo copies).')
    parser.add_argument('--font', default=None, help='A local copy of %s (default: download it).' % CONST_FONT_NAME)
    args = parser.parse_args()

    if shutil.which('inkscape') is None:
        sys.exit('[ERROR] Inkscape is not on PATH. Install Inkscape %s (e.g. brew install --cask inkscape).'
                 % CONST_INKSCAPE_VERIFIED)
    version = subprocess.run(['inkscape', '--version'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             universal_newlines=True).stdout.split()
    version = version[1] if len(version) > 1 else '?'
    if version != CONST_INKSCAPE_VERIFIED:
        print('[WARNING] Inkscape %s; the committed logo was built with %s. Compare the result before '
              'committing it.' % (version, CONST_INKSCAPE_VERIFIED))

    directory = tempfile.mkdtemp(prefix='anyscan_logo_')
    try:
        font = Fetch_Font(args.font, directory)
        first = args.output or CONST_OUTPUT_FILES[0]
        Build(font, first, directory)
        if args.output is None:
            shutil.copyfile(first, CONST_OUTPUT_FILES[1])
            print('[INFO] Copied it to %s. Now run python Example/UI/architecture_diagram.py.' % CONST_OUTPUT_FILES[1])
    finally:
        shutil.rmtree(directory, ignore_errors=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
