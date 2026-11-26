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
    Example/UI/readme_diagrams.py, the README's pipeline and models diagrams: each committed image, light and dark, is
    exactly the generator's output (compared pixel by pixel), the dark versions lie on a transparent ground and the
    light ones on white, the models diagram's pins are the revisions the README's download commands use, and the
    README shows each through <picture>, and the pipeline follows the station's order.
"""
CONST_PROJECT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CONST_GENERATOR = os.path.join(CONST_PROJECT_FOLDER, 'Example', 'UI', 'readme_diagrams.py')
CONST_README = os.path.join(CONST_PROJECT_FOLDER, 'README.md')
CONST_NAMES = ['anyscan-%s-%s.png' % (figure, version) for figure in ('pipeline', 'models')
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
        The generator draws each diagram in a light and a dark version, under the names the README shows.
    """

    assert sorted(figures) == sorted(CONST_NAMES)


@pytest.mark.parametrize('name', CONST_NAMES)
def test_each_committed_diagram_is_the_generators_output(generator, figures, name) -> None:
    """
    Description:
        The committed image holds exactly the pixels the generator draws from the current theme, icons, fonts and
        install.sh, so a hand edit, or a change of one of them without regenerating, fails here. Fix it by running
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
    if name.endswith('-dark.png'):
        assert all(corner[3] == 0 for corner in corners)
    else:
        assert all(tuple(corner) == (255, 255, 255, 255) for corner in corners)


def test_the_models_diagram_pins_the_revisions_the_readme_downloads(generator) -> None:
    """
    Description:
        The revisions install.sh pins, whose first 7 characters the models diagram states, are the full revisions the
        README's download commands fetch, and the sizes are the installer's files summed.
    """

    with open(CONST_README, 'r', encoding='utf-8') as handle:
        readme = handle.read()
    with open(generator.CONST_INSTALLER, 'r', encoding='utf-8') as handle:
        installer = handle.read()
    pins = generator.Read_Installer()
    for key, constant in (('gemma_pin', 'CONST_GEMMA_REVISION'), ('dino_pin', 'CONST_DINOV2_REVISION')):
        revision = generator.Installer_Value(installer, constant)
        assert pins[key] == 'revision ' + revision[:7]
        assert '--revision ' + revision + ' ' in readme or '--revision ' + revision + '\n' in readme
    assert (pins['fastsam_size'], pins['gemma_size'], pins['dino_size']) == ('145 MB', '5.2 GB', '346 MB')


@pytest.mark.parametrize('figure', ['anyscan-pipeline', 'anyscan-models'])
def test_the_readme_shows_each_diagram_light_and_dark_through_picture(figure) -> None:
    """
    Description:
        The README shows each diagram through <picture>: the dark version as the source for a dark appearance, the
        light one as the <img> fallback with its alt text, so GitHub picks the version for the reader's theme.
    """

    with open(CONST_README, 'r', encoding='utf-8') as handle:
        readme = handle.read()
    block = '<picture>\n  <source media="(prefers-color-scheme: dark)" srcset="images/%s-dark.png">\n' \
            '  <img src="images/%s-light.png" width="100%%" alt="' % (figure, figure)
    assert block in readme


def test_the_pipeline_follows_the_stations_order(generator) -> None:
    """
    Description:
        The pipeline diagram draws a catalogue mode's order (README > Detection logic: each object is measured,
        recognised and checked before it is described, the describer told what the checks found): Frame, Find,
        Measure, Judge, Describe, Record, with Judge marked as the catalogue mode's step.
    """

    names = [name for _icon, name, _words in generator.CONST_PIPELINE_STEPS]
    assert names == ['Frame', 'Find', 'Measure', 'Judge', 'Describe', 'Record']
    assert generator.CONST_CATALOGUE_STEP == 'Judge'
    assert names.index('Judge') < names.index('Describe')
