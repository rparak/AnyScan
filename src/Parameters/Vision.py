## =========================================================================== ##
# MIT License
# Copyright (c) 2025 Roman Parak
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
# Author   : Roman Parak
# Email    : Roman.Parak@outlook.com
# Github   : https://github.com/rparak
# File Name: ../Parameters/Vision.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp
# Dataclasses (Data Classes)
from dataclasses import dataclass, field


@dataclass
class Detection_Str(object):
    """
    Description:
        The structure of one object the vision pipeline located in a frame.

        Note:
            Order is meaningful: the position of a Detection_Str in the analysis'
            object list is the number the operator sees, both on the box drawn
            over the frame and at the start of the matching line of text. Never
            reorder the list after composing.

    Initialization of the Class:
        Args:
            (1) Label [string]: The distilled noun-phrase label (e.g. 'hex bolt').
            (2) Bbox [Vector<int> 1x4]: The box as (x, y, w, h) in frame pixels.

        Example:
            Initialization:
                # Initialization of the structure.
                Cls = Detection_Str(Label='hex bolt', Bbox=(10, 20, 30, 40))

            Features:
                # Access the fields of the structure.
                Cls.Label; Cls.Bbox; Cls.Detail; Cls.Sentence
    """

    # The distilled noun-phrase label shown at the start of the object's line.
    #   Unit [string]
    Label: str
    # The bounding box as (x, y, w, h) in full-frame pixels.
    #   Unit [Vector<int> 1x4]
    Bbox: tp.Tuple[int, int, int, int]
    # The detector's confidence score, or None when the backend emits none.
    #   Unit [float]
    Confidence: tp.Optional[float] = None
    # Any text read off the object (e.g. a marking), or None.
    #   Unit [string]
    Text: tp.Optional[str] = None
    # The model's full caption, rendered as the object line's second sentence.
    #   Unit [string]
    Detail: str = ''
    # The final composed sentence the panel prints for this object.
    #   Unit [string]
    Sentence: str = ''


@dataclass
class Analysis_Str(object):
    """
    Description:
        The structure of a completed scene analysis — everything the Scene
        Understanding panel renders from a single backend call.

    Initialization of the Class:
        Args:
            (1) Summary [string]: The lead sentence introducing the objects.

        Example:
            Initialization:
                # Initialization of the structure.
                Cls = Analysis_Str(Summary='The frame contains one object...')

            Features:
                # Access the fields of the structure.
                Cls.Objects; Cls.Note; Cls.Verdict; Cls.Verdict_Level; Cls.Task
    """

    # The lead sentence introducing the objects (or the empty-scene statement).
    #   Unit [string]
    Summary: str = ''
    # The located objects, in the order the operator reads them.
    #   Unit [Vector<Detection_Str(object)>]
    Objects: tp.List[Detection_Str] = field(default_factory=list)
    # A closing note — the empty-scene explanation and its next action, if any.
    #   Unit [string]
    Note: str = ''
    # The wall-clock latency of the analysis, in milliseconds.
    #   Unit [int]
    Latency_Ms: int = 0
    # The verdict-badge wording (e.g. 'Empty', '1 found', 'Low confidence').
    #   Unit [string]
    Verdict: str = 'Idle'
    # The verdict severity that drives the badge colour: 'ok' | 'warn' | 'idle'.
    #   Unit [string]
    Verdict_Level: str = 'idle'
    # The human-readable name of the model task that produced the reading.
    #   Unit [string]
    Task: str = 'detailed caption'
