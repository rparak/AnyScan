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
    # The part's thickness. The camera looks from above and does not measure it; the scale is
    # corrected to the part's top face with it (Configuration.Core.Scale_At_Height).
    #   Unit [float] (mm)
    Thickness_Mm: float = 0.0
    # The tolerance every dimension is checked against unless it sets its own.
    #   Unit [float] (mm)
    Tolerance_Mm: float = 0.0
    # The outline check.
    Outline: Catalogue_Outline_Str = field(default_factory=Catalogue_Outline_Str)
    # What the loader has to say about this file, as (level, message): each optional field that fell
    # back to its default, each key it did not recognise. They join the configuration's Notes.
    #   Unit [Vector<Tuple<string> 1x2>]
    Notes: tp.List[tp.Tuple[str, str]] = field(default_factory=list)
