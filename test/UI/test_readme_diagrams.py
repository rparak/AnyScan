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
# File Name: ../test/UI/test_readme_diagrams.py
## =========================================================================== ##

# System (Default)
import os
import re
import importlib.util
# Typing (Support for type hints)
import typing as tp
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pillow (Reading the images) [pip3 install Pillow]
from PIL import Image
# Pytest (Testing framework) [pip3 install pytest]
import pytest

"""
Description:
    Example/UI/readme_diagrams.py, the README's pipeline diagram, catalogue item card and models table: each committed
    image, light and dark, is the generator's output (the PNGs pixel by pixel, the WebP card within the encoder's
    tolerance), the dark versions lie on a transparent ground and the light ones on white, the README shows each
    through <picture>, the README's models table is the one install.sh gives (its pins the revisions the README's
    download commands use), the card states what the item file holds, and the pipeline follows the station's order.
"""
CONST_PROJECT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CONST_GENERATOR = os.path.join(CONST_PROJECT_FOLDER, 'Example', 'UI', 'readme_diagrams.py')
CONST_README = os.path.join(CONST_PROJECT_FOLDER, 'README.md')
CONST_FIGURES = {'anyscan-pipeline': 'png', 'anyscan-catalogue-item': 'webp'}
CONST_NAMES = ['%s-%s.%s' % (figure, version, kind) for figure, kind in CONST_FIGURES.items()
               for version in ('light', 'dark')]


@pytest.fixture(scope='module')
def generator() -> tp.Any:
    """The generator script, loaded as a module."""
    spec = importlib.util.spec_from_file_location('readme_diagrams', CONST_GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def figures(generator) -> tp.Dict[str, Image.Image]:
    """The four images as the generator draws them now."""
    return generator.Figures()


def test_the_generator_draws_the_four_images(figures) -> None:
    """
    Description:
        The generator draws each figure in a light and a dark version, under the names the README shows.
    """

    assert sorted(figures) == sorted(CONST_NAMES)


@pytest.mark.parametrize('name', CONST_NAMES)
def test_each_committed_diagram_is_the_generators_output(generator, figures, name) -> None:
    """
    Description:
        The committed image holds the pixels the generator draws from the current theme, icons, fonts and catalogue
        item (a PNG exactly, the WebP card within the encoder's error in every 16 px square), so a hand edit, or a
        change of one of them without regenerating, fails here. Fix it by running
        .venv/bin/python Example/UI/readme_diagrams.py, never by editing the image.
    """

    path = os.path.join(CONST_PROJECT_FOLDER, 'images', name)
    assert generator.Same_Pixels(path, figures[name]), \
        'images/%s is stale or hand-edited; run .venv/bin/python Example/UI/readme_diagrams.py' % name


@pytest.mark.parametrize('name', CONST_NAMES)
def test_the_dark_versions_lie_on_a_transparent_ground_and_the_light_on_white(name) -> None:
    """
    Description:
        A dark version is drawn for GitHub's dark page: its ground, read at the corners, is fully transparent. A light
        version is opaque, its corners white.
    """

    with Image.open(os.path.join(CONST_PROJECT_FOLDER, 'images', name)) as image:
        pixels = np.asarray(image.convert('RGBA'))
    corners = [pixels[0, 0], pixels[0, -1], pixels[-1, 0], pixels[-1, -1]]
    if '-dark.' in name:
        assert all(corner[3] == 0 for corner in corners)
    else:
        assert all(tuple(corner) == (255, 255, 255, 255) for corner in corners)


def test_the_readme_models_table_is_the_installers(generator) -> None:
    """
    Description:
        The README's models table is Models_Table() word for word: its pins are the first 7 characters of the
        revisions install.sh pins, which are the full revisions the README's download commands fetch, and its sizes
        are the installer's files summed.
    """

    with open(CONST_README, 'r', encoding='utf-8') as handle:
        readme = handle.read()
    with open(generator.CONST_INSTALLER, 'r', encoding='utf-8') as handle:
        installer = handle.read()
    assert generator.Models_Table() in readme, 'the README models table differs; run Example/UI/readme_diagrams.py'
    pins = generator.Read_Installer()
    for key, constant in (('gemma_pin', 'CONST_GEMMA_REVISION'), ('dino_pin', 'CONST_DINOV2_REVISION')):
        revision = generator.Installer_Value(installer, constant)
        assert pins[key] == 'revision ' + revision[:7]
        assert '--revision ' + revision + ' ' in readme or '--revision ' + revision + '\n' in readme
    assert (pins['fastsam_size'], pins['gemma_size'], pins['dino_size']) == ('145 MB', '5.2 GB', '346 MB')


def test_the_item_card_states_what_the_item_file_holds(generator) -> None:
    """
    Description:
        The catalogue item card lists the shipped item's outline and tolerance, each side's holes, the stain check and
        the known defect, read through the item's loader, with numbers the item file holds (typed here from it).
    """

    rows = dict((name, lines) for name, lines in generator.Item_Rows(generator.Load_Catalogue(generator.CONST_CATALOGUE_ITEM)))
    assert rows['OUTLINE'] == ['60 × 40 mm, ± 1.5 mm']
    assert rows['HOLES, MACHINED FRONT'] == ['2 countersinks, Ø 12 mm', '2 through-holes, Ø 6 mm, 25 mm apart']
    assert rows['HOLES, UNMACHINED BACK'] == ['2 through-holes, Ø 6 mm, 25 mm apart']
    assert rows['STAINS'] == ['none of 1 mm² or more on the machined front']
    assert rows['KNOWN DEFECTS'] == ['fingerprint, on the machined front']


@pytest.mark.parametrize('figure', sorted(CONST_FIGURES))
def test_the_readme_shows_each_figure_light_and_dark_through_picture(figure) -> None:
    """
    Description:
        The README shows each figure through <picture>: the dark version as the source for a dark appearance, the
        light one as the <img> fallback with its alt text, so GitHub picks the version for the reader's theme.
    """

    with open(CONST_README, 'r', encoding='utf-8') as handle:
        readme = handle.read()
    kind = CONST_FIGURES[figure]
    block = '<picture>\n  <source media="(prefers-color-scheme: dark)" srcset="images/%s-dark.%s">\n' \
            '  <img src="images/%s-light.%s" width="100%%" alt="' % (figure, kind, figure, kind)
    assert block in readme


def test_the_pipeline_follows_the_stations_order(generator) -> None:
    """
    Description:
        The pipeline diagram draws a catalogue mode's order (README > Architecture: each object is measured,
        recognised and checked before it is described, the describer told what the checks found): Frame, Find,
        Measure, Judge, Describe, Record, with Judge marked as the catalogue mode's step.
    """

    names = [name for _icon, name, _words in generator.CONST_PIPELINE_STEPS]
    assert names == ['Frame', 'Find', 'Measure', 'Judge', 'Describe', 'Record']
    assert generator.CONST_CATALOGUE_STEP == 'Judge'
    assert names.index('Judge') < names.index('Describe')


def test_the_readme_shows_no_animation() -> None:
    """
    Description:
        Every local image the README shows is one frame: no animated WebP, GIF or APNG (README v11, 2026-11-26).
    """

    with open(CONST_README, 'r', encoding='utf-8') as handle:
        readme = handle.read()
    shown = sorted(set(re.findall(r'(?:src|srcset)="(images/[^"]+)"|\]\((images/[^)\s]+)\)', readme)))
    paths = sorted({a or b for a, b in shown if not (a or b).endswith('.svg')})
    assert paths, 'the scan found no image at all'
    for path in paths:
        with Image.open(os.path.join(CONST_PROJECT_FOLDER, path)) as image:
            assert getattr(image, 'n_frames', 1) == 1, '%s is animated' % path
