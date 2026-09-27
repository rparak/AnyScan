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
# File Name: ../Vision/Utilities/Timing.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — the timing structures and the stage names
#   ../Parameters/Vision
from Parameters.Vision import Timing_Str, Object_Timing_Str, CONST_TIMING_STAGES

"""
Description:
    Initialization of constants.

    An analysis's stage timing (Build_Timing): the measured stage seconds become the whole
    milliseconds the log prints, and the remainder is derived so the printed numbers add up to the
    printed total. Pure arithmetic — no clock, no model — so the rounding rule is tested on its own.
"""


def Build_Timing(total_ms: int, stage_seconds: tp.Dict[str, float],
                 objects: tp.List[tp.Tuple[float, float, tp.Optional[tp.Tuple[int, int]]]],
                 first_after_load: bool) -> Timing_Str:
    """
    Description:
        Turn one analysis's measured stage times into its Timing_Str.

        Every value is TRUNCATED to a whole millisecond, as Latency_Ms is (int of the elapsed
        milliseconds). Truncation, not rounding: when the stages are disjoint parts of the
        analysis, the sum of their truncated values can never exceed the truncated total, so
        Other_Ms (the total minus that sum, derived, never measured on its own) is never negative
        by rounding alone. A negative Other_Ms therefore means the stages overlap — a stage was
        counted twice — and it is kept negative for the log to report, never clamped.

    Args:
        (1) total_ms [int]: The analysis's Latency_Ms.
        (2) stage_seconds [Dict<string, float>]: The measured seconds per stage (CONST_TIMING_STAGES);
                                                 a stage that did not run may be missing (0).
        (3) objects [Vector<Tuple>]: Per object, in order: (crop seconds, description seconds,
                                     (input tokens, output tokens) or None).
        (4) first_after_load [bool]: Whether this is the first analysis after a load.

    Returns:
        (1) parameter [Timing_Str(object)]: The timing; Measurement_Ms is set by the caller, after
                                            the measurement has run.
    """

    stages = [(name, int(stage_seconds.get(name, 0.0) * 1000)) for name in CONST_TIMING_STAGES]
    object_timings = [Object_Timing_Str(Crop_Ms=int(crop_s * 1000), Describe_Ms=int(describe_s * 1000),
                                        Input_Tokens=tokens[0] if tokens is not None else None,
                                        Output_Tokens=tokens[1] if tokens is not None else None)
                      for crop_s, describe_s, tokens in objects]
    return Timing_Str(Total_Ms=total_ms, Stages=stages, Other_Ms=total_ms - sum(ms for _name, ms in stages),
                      Objects=object_timings, First_After_Load=first_after_load)
