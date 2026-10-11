## =========================================================================== ##
# MIT License
# Copyright (c) 2026 JIC Smart Factory
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
# File Name: ../Parameters/Catalogue.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp
# Dataclasses (Data Classes)
from dataclasses import dataclass, field

"""
Description:
    Initialization of constants.

    The structures a catalogue item becomes (Configuration.Core.Load_Catalogue): one part the
    catalogue mode inspects, read from Data/Catalogue/<item>/<item>.yaml. Qt-free and
    dependency-free. A field with no default here is REQUIRED in the file; an optional one's default
    is the value written here, and the catalogue file documents it.
"""


@dataclass
class Catalogue_Outline_Str:
    """
    Description:
        The part's outline seen from above: its two sides and the tolerance they are checked
        against. The check is independent of orientation: the longer measured side is compared
        with Length_Mm, the shorter with Width_Mm.
    """

    # The nominal long and short side. REQUIRED, both; Length_Mm >= Width_Mm.
    #   Unit [float] (mm)
    Length_Mm: float = 0.0
    Width_Mm: float = 0.0
    # The tolerance both sides are checked against (nominal ± this). The item's Tolerance_Mm unless
    # the outline sets its own.
    #   Unit [float] (mm)
    Tolerance_Mm: float = 0.0


@dataclass
class Catalogue_Reference_Str:
    """
    Description:
        One reference image of the catalogue part: one side, photographed lying on the table, in its
        OK state, with the part's bounding box (Data/Catalogue/<item>/reference_image/<side>.png and
        <side>.txt, a YOLO line). The catalogue mode compares every object with these (Vision.Identifier).
    """

    # The side: 'front' or 'back'.
    #   Unit [string]
    Side: str = ''
    # The image (absolute) and the part's box in it as YOLO gives it: centre x, centre y, width and
    # height, each a fraction of the image's size.
    #   Unit [string] / [Vector<float> 1x4]
    Image_Path: str = ''
    Box: tp.Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


@dataclass
class Catalogue_Side_Str:
    """
    Description:
        One side of the catalogue part as a person describes it: what it is called and what it looks
        like. Its Name is read now (the side sentence of a judged object's description); its Description
        is validated and waits for the describer (phase D of the catalogue mode).
    """

    # The side: 'front' or 'back', as its reference image is named.
    #   Unit [string]
    Side: str = ''
    # What the side is called ('machined front'), and what it looks like ('' when not described).
    #   Unit [string]
    Name: str = ''
    Description: str = ''


@dataclass
class Catalogue_Defect_Str:
    """
    Description:
        One defect the catalogue part can have, as a person describes it: what it is called, the side it is
        looked for on, what it looks like, and what looks like it but is not. Validated, and read by nothing
        yet: the stain, hole and logo checks and the describer use it from phases C and D.
    """

    # The defect's name, and the side it is looked for on ('front' or 'back').
    #   Unit [string]
    Name: str = ''
    Side: str = ''
    # What it looks like, and what looks like it but is not a defect ('' when not described).
    #   Unit [string]
    Looks_Like: str = ''
    Not_A_Defect: str = ''


@dataclass
class Catalogue_Item_Str:
    """
    Description:
        One catalogue item, loaded and validated as a whole. Only Configuration.Core.Load_Catalogue
        builds one, so holding one means every field is usable.
    """

    # The item's file (absolute) and its name: the folder's name, which the file's name repeats
    # ('mounting_plate/mounting_plate.yaml').
    #   Unit [string]
    Path: str = ''
    Name: str = ''
    # The item as a person names it ('Mounting plate'): the configuration-loaded line names it.
    #   Unit [string]
    Display_Name: str = ''
    # The part as a whole, and how a dimension is read on it beyond its nominal value ('' when not
    # described). Validated, read by the describer from phase D.
    #   Unit [string]
    Description: str = ''
    Measurement_Rules: str = ''
    # The part's thickness. The camera looks from above and does not measure it; the scale is
    # corrected to the part's top face with it (Configuration.Core.Scale_At_Height).
    #   Unit [float] (mm)
    Thickness_Mm: float = 0.0
    # The tolerance every dimension is checked against unless it sets its own.
    #   Unit [float] (mm)
    Tolerance_Mm: float = 0.0
    # The outline check.
    Outline: Catalogue_Outline_Str = field(default_factory=Catalogue_Outline_Str)
    # The reference images, front then back (reference_image/ beside the file).
    #   Unit [Vector<Catalogue_Reference_Str(object)>]
    References: tp.List[Catalogue_Reference_Str] = field(default_factory=list)
    # The two sides as a person describes them, front then back, and the defects (none when not described).
    #   Unit [Vector<Catalogue_Side_Str(object)>] / [Vector<Catalogue_Defect_Str(object)>]
    Sides: tp.List[Catalogue_Side_Str] = field(default_factory=list)
    Defects: tp.List[Catalogue_Defect_Str] = field(default_factory=list)
    # What the loader has to say about this file, as (level, message): each optional field that fell
    # back to its default, each key it did not recognise. They join the configuration's Notes.
    #   Unit [Vector<Tuple<string> 1x2>]
    Notes: tp.List[tp.Tuple[str, str]] = field(default_factory=list)
