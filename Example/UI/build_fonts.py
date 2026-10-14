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
# File Name: ../Example/UI/build_fonts.py
## =========================================================================== ##

# System (Default)
import argparse
import hashlib
import os
import shutil
import sys
import tempfile
# URL fetching (the pinned fonts and licences) [Python standard library]
import urllib.request
# Typing (Support for type hints)
import typing as tp
# fontTools (Font instancing) [pip3 install fonttools]
import fontTools
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

"""
Description:
    Build the console's bundled UI fonts into App/assets/fonts/: static Public Sans (the UI face, the open
    font closest to the brand's GT America Standard: docs/design-decisions.md, "The UI is set in Public
    Sans") and JetBrains Mono at the four weights the UI requests (Regular 400, Medium 500, SemiBold 600,
    Bold 700), and each family's SIL Open Font License text, which the OFL requires to travel with the
    fonts. Style.Load_Fonts registers every .ttf in that directory (docs/design-decisions.md, "The UI fonts
    are bundled").

    google/fonts carries only the variable fonts, and Qt 5.15 uses a variable font's default instance
    alone (it synthesises every other weight), so each weight is instanced into its own static file with
    fontTools on the family's one axis. The name table and usWeightClass are set so Qt lists each family
    with its styles. The sources are the variable fonts at a pinned google/fonts commit, each
    checked against its SHA-256; a missing or different file stops the build. The output does not depend
    on the clock (the source's head timestamps are kept), so a rebuild reproduces the committed files.

        python Example/UI/build_fonts.py                         # rewrite App/assets/fonts/
        python Example/UI/build_fonts.py --output-dir /tmp/fonts # build elsewhere, e.g. to compare
        python Example/UI/build_fonts.py --sources DIR           # use local copies of the pinned files
"""
# The project folder, from this file's own location (Example/UI -> ..).
#   Unit [string]
CONST_PROJECT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
CONST_OUTPUT_DIR = os.path.join(CONST_PROJECT_FOLDER, 'App', 'assets', 'fonts')
# The google/fonts commit every source is taken from.
#   Unit [string]
CONST_GOOGLE_FONTS = 'https://raw.githubusercontent.com/google/fonts/e1d6480102fed30739fead0faee463101f892c8f/'
# Every pinned source: the file name it is kept under, its path in google/fonts, its SHA-256.
#   Unit [Dict<string, Tuple<string> 1x2>]
CONST_SOURCES = {
    'PublicSans[wght].ttf': ('ofl/publicsans/PublicSans%5Bwght%5D.ttf',
                             'd75a7dc1a27eb9e336d5b33f55489d2ecb5621bf694d5c43b2415bce2ca830a8'),
    'PublicSans-OFL.txt': ('ofl/publicsans/OFL.txt', '157a9e77f7580246e97c769490e2e977ae94399f9d30f4556015c41fe8c28bac'),
    'JetBrainsMono[wght].ttf': ('ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf',
                                '48715a42ec242c21e9f02692891e147d022299a52e48d5e413e1a942193ffeda'),
    'JetBrainsMono-OFL.txt': ('ofl/jetbrainsmono/OFL.txt', 'b2fe5e8987594e9ffd1d2ca52a2f5d73eb8335243893c5d6254b5ad69269591d')}
# The weights the UI requests (QFont Normal, Medium, DemiBold, Bold), each with its style name.
#   Unit [Vector<Tuple<string, int>>]
CONST_WEIGHTS = (('Regular', 400), ('Medium', 500), ('SemiBold', 600), ('Bold', 700))
# The families built: the family name Qt lists, the variable source, the axes held fixed besides the
# weight, the licence that ships beside it, and the weights built.
#   Unit [Vector<Tuple>]
CONST_FAMILIES = (('Public Sans', 'PublicSans[wght].ttf', {}, 'PublicSans-OFL.txt', CONST_WEIGHTS),
                  ('JetBrains Mono', 'JetBrainsMono[wght].ttf', {}, 'JetBrainsMono-OFL.txt', CONST_WEIGHTS))
# The fontTools version the committed fonts were built with.
#   Unit [string]
CONST_FONTTOOLS_VERIFIED = '4.66.0'
# OS/2 fsSelection bits: ITALIC, BOLD, REGULAR.
#   Unit [int]
CONST_FS_ITALIC, CONST_FS_BOLD, CONST_FS_REGULAR = 0x01, 0x20, 0x40


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


def Fetch_Sources(sources: tp.Optional[str], directory: str) -> tp.Dict[str, str]:
    """
    Description:
        Every pinned source, verified: taken from a local directory, or downloaded from the pinned commit
        into a temporary directory. Stops the build when a file is absent, cannot be fetched, or is not the
        pinned file.

    Args:
        (1) sources [string or None]: A directory holding local copies under the CONST_SOURCES names, or None.
        (2) directory [string]: The temporary directory downloads go into.

    Returns:
        (1) parameter [Dict<string, string>]: Each source name -> its verified path.
    """

    paths = {}
    for name, (remote, pinned) in CONST_SOURCES.items():
        target = os.path.join(directory, name)
        if sources is not None:
            local = os.path.join(sources, name)
            if not os.path.isfile(local):
                sys.exit('[ERROR] %s is not in %s. Omit --sources to download the pinned files.' % (name, sources))
            shutil.copyfile(local, target)
        else:
            print('[INFO] Downloading %s' % (CONST_GOOGLE_FONTS + remote))
            try:
                with urllib.request.urlopen(CONST_GOOGLE_FONTS + remote, timeout=60) as response, open(target, 'wb') as handle:
                    shutil.copyfileobj(response, handle)
            except OSError as error:
                sys.exit('[ERROR] %s could not be downloaded (%s). Download it by hand and pass its directory with '
                         '--sources.' % (name, error))
        digest = Sha256(target)
        if digest != pinned:
            sys.exit('[ERROR] %s is not the pinned file: SHA-256 %s, expected %s. The fonts are built only from the '
                     'pinned sources so that a rebuild reproduces them.' % (name, digest, pinned))
        print('[INFO] Verified %s (SHA-256 %s).' % (name, digest[:16]))
        paths[name] = target
    return paths


def File_Name(family: str, style: str) -> str:
    """
    Description:
        A static font's file name: the family without spaces, then the style.

    Args:
        (1) family [string]: The family name.
        (2) style [string]: The style name.

    Returns:
        (1) parameter [string]: The file name.
    """

    return '%s-%s.ttf' % (family.replace(' ', ''), style)


def Build_Static(source: str, family: str, fixed: tp.Dict[str, float], style: str, weight: int, output: str) -> None:
    """
    Description:
        Instance one weight of a variable font into a static font and name it so Qt lists it as `style` of
        `family`: Regular and Bold as the RIBBI pair of the family, Medium and SemiBold as their own legacy
        family with the typographic family and style (name IDs 16, 17) naming the real ones.

    Args:
        (1) source [string]: The verified variable font.
        (2) family [string]: The family name.
        (3) fixed [Dict<string, float>]: Axes held at a value besides the weight.
        (4) style [string]: The style name.
        (5) weight [int]: The weight axis value and usWeightClass.
        (6) output [string]: Where the static font is written.
    """

    font = instancer.instantiateVariableFont(TTFont(source, recalcTimestamp=False), dict(fixed, wght=weight),
                                             updateFontNames=False)
    ribbi = style in ('Regular', 'Bold')
    names = {1: family if ribbi else '%s %s' % (family, style), 2: style if ribbi else 'Regular',
             4: '%s %s' % (family, style), 6: '%s-%s' % (family.replace(' ', ''), style), 16: family, 17: style}
    table = font['name']
    for name_id in (3, 25):
        table.removeNames(nameID=name_id)
    table.names = [record for record in table.names if record.nameID < 256]
    for name_id, value in names.items():
        table.setName(value, name_id, 3, 1, 0x409)
        table.setName(value, name_id, 1, 0, 0)
    table.setName('%s;%s' % (names[6], font['head'].fontRevision), 3, 3, 1, 0x409)
    os2 = font['OS/2']
    os2.usWeightClass = weight
    os2.fsSelection = (os2.fsSelection & ~(CONST_FS_ITALIC | CONST_FS_BOLD | CONST_FS_REGULAR)) | (
        CONST_FS_BOLD if style == 'Bold' else CONST_FS_REGULAR if style == 'Regular' else 0)
    font['head'].macStyle = 1 if style == 'Bold' else 0
    font.save(output)


def main() -> int:
    """
    Description:
        Parse the command line, fetch and verify the sources, and build every static font and licence into
        the output directory.

    Returns:
        (1) parameter [int]: The exit code.
    """

    parser = argparse.ArgumentParser(description='Build the bundled UI fonts (static Public Sans and JetBrains Mono).')
    parser.add_argument('--output-dir', default=CONST_OUTPUT_DIR, help='Where to write (default: App/assets/fonts/).')
    parser.add_argument('--sources', default=None, help='A directory with local copies of the pinned files.')
    args = parser.parse_args()

    if fontTools.version != CONST_FONTTOOLS_VERIFIED:
        print('[WARNING] fontTools %s; the committed fonts were built with %s. Compare the hashes before '
              'committing the result.' % (fontTools.version, CONST_FONTTOOLS_VERIFIED))
    directory = tempfile.mkdtemp(prefix='anyscan_fonts_')
    try:
        paths = Fetch_Sources(args.sources, directory)
        os.makedirs(args.output_dir, exist_ok=True)
        for family, source, fixed, licence, weights in CONST_FAMILIES:
            for style, weight in weights:
                output = os.path.join(args.output_dir, File_Name(family, style))
                Build_Static(paths[source], family, fixed, style, weight, output)
                print('[INFO] Wrote %s (%d bytes, SHA-256 %s).' % (output, os.path.getsize(output), Sha256(output)[:16]))
            shutil.copyfile(paths[licence], os.path.join(args.output_dir, licence))
            print('[INFO] Wrote %s.' % os.path.join(args.output_dir, licence))
    finally:
        shutil.rmtree(directory, ignore_errors=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
