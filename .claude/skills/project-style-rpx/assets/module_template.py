## =========================================================================== ##
# MIT License
# Copyright (c) {{Year}} {{Holder}}
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
# Author   : {{Author}}
# File Name: ../{{Domain}}/Core.py
## =========================================================================== ##

# System (Default)
import os
# Typing (Support for type hints)
import typing as tp
# Dataclasses (Data Classes)
from dataclasses import dataclass
# Custom Lib.: {{what this module takes from it; only from a layer below this one (references/structure.md)}}
#   ../{{Lower_Domain}}/Core
from Lower_Domain.Core import Some_Function  # noqa: F401 (placeholder: import what the module uses)

"""
Description:
    Initialization of constants.

    {{What this module is for, in two or three sentences, and what it must never do (read a file
    format another module owns, print, hold state a caller cannot see).}}
"""
# {{What the constant means, its source (a manual page, a measurement) and why it has this value.}}
#   Unit [m]
CONST_THING_LIMIT = 0.0


class Thing_Error_Cls(ValueError):
    """
    Description:
        {{The failure the operator must see}}. Its message is a full sentence saying what is wrong
        and what to do; a script prints it verbatim as an [ERROR] line.
    """


@dataclass
class Thing_Parameters_Str:
    """
    Description:
        {{What the structure carries and who builds it.}}
    """

    # {{What the field means.}}
    #   Unit [m]
    Limit: float = CONST_THING_LIMIT


class Thing_Cls(object):
    """
    Description:
        {{What the class does.}}

    Initialization of the Class:
        Args:
            (1) Thing_Parameters_Str [Thing_Parameters_Str(object)]: {{The structure it is built from.}}

        Example:
            Initialization:
                # Initialization of the class.
                Cls = Thing_Cls(Thing_Parameters_Str)

            Features:
                # Properties of the class.
                Cls.Limit

                # Functions of the class.
                Cls.Check_Path({{arguments}})
    """

    def __init__(self, Thing_Parameters_Str: Thing_Parameters_Str) -> None:
        # << PRIVATE >> #
        self.__params = Thing_Parameters_Str

    @property
    def Limit(self) -> float:
        """
        Description:
            {{What it returns.}}

        Returns:
            (1) parameter [float]: {{The value}} [m].
        """

        return self.__params.Limit

    def Check_Path(self, path: str, log_cb: tp.Optional[tp.Callable[[str, str], None]] = None) -> str:
        """
        Description:
            {{What it does. A failure the operator must see raises Thing_Error_Cls; an event worth
            reporting goes through log_cb (level, message), never a print or a logger held here.}}

        Args:
            (1) path [string]: {{The input.}}
            (2) log_cb [function]: Optional (level, message) sink.

        Returns:
            (1) parameter [string]: {{The result.}}
        """

        if not os.path.isfile(path):
            raise Thing_Error_Cls('The file "%s" does not exist. {{What to do about it.}}' % path)
        if log_cb is not None:
            log_cb('INFO', 'Checked "%s".' % path)
        return path
