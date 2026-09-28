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
# File Name: ../Parameters/Configuration.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp
# Dataclasses (Data Classes)
from dataclasses import dataclass, field
# Custom Lib.: AnyScan — the camera, scale and confidence structures a configuration carries
#   ../Parameters/Camera
from Parameters.Camera import Camera_Configuration_Str
#   ../Parameters/Vision
from Parameters.Vision import Scale_Str, Confidence_Thresholds_Str
#   ../Parameters/General
from Parameters.General import CONST_CLASSIFICATION_ENABLED_DEFAULT

"""
Description:
    Initialization of constants.

    The structures a loaded configuration file becomes (Configuration.Core.Load_Configuration).
    Qt-free and dependency-free. The field defaults ARE the documented defaults: a configuration
    that omits an optional field gets the value written here (and the loader logs that it did).
    Each one is the value the pipeline ran with when it was still a module constant, so moving a
    constant into the file changed no behaviour. A field with no default here (a model path, a
    prompt) is REQUIRED: the loader fails naming it rather than invent one.
"""


@dataclass
class Segmentation_Parameters_Str:
    """
    Description:
        Stages 1-3: the FastSAM instance segmenter, the background difference and the fusion of
        the two. Read from the configuration's 'Segmentation' block.
    """

    # The FastSAM weights file, absolute once loaded. REQUIRED (no default).
    #   Unit [string]
    Model_Path: str = ''
    # Compute device: 'auto' picks cuda, then mps, then cpu. Chosen when the model loads.
    #   Unit [string]
    Device: str = 'auto'
    # FastSAM's own detection confidence and NMS-IoU thresholds, and its inference size.
    #   Unit [float] / [float] / [int] (px)
    Confidence: float = 0.4
    IoU: float = 0.9
    Image_Size: int = 1024
    # Stage 1 (background difference): the empty-surface reference every frame is differenced
    # against, absolute once loaded. REQUIRED, and the file must exist: it decides every
    # background-subtraction result, so which one is in use is stated, never discovered.
    #   Unit [string]
    Background_Reference: str = ''
    # Stage 1 (background difference): the floor under the Otsu threshold, so a near-empty frame
    # cannot promote the shadow halo and sensor noise to foreground.
    #   Unit [int] (grey level 0..255)
    Otsu_Floor: int = 28
    # Stage 1 morphology: the opening that erases the shadow halo and speckle, and the small
    # dilation that recovers the edges it eroded (0 disables the dilation).
    #   Unit [int] (px, kernel size)
    Open_Kernel: int = 5
    Dilate: int = 3
    # Stage 3 morphology: the closing that fills gaps and notches inside each fused component; it
    # never joins two components that were separate before it (Fusion.__Close_Within_Components).
    #   Unit [int] (px, kernel size)
    Close_Kernel: int = 15
    # Stage 3 area filter: a component smaller than this fraction of the frame is a speck.
    #   Unit [float] (fraction of the frame)
    Min_Area_Fraction: float = 5e-4
    # Stage 3 background rejection: a FastSAM mask covering this fraction of the frame is the
    # table outright; one covering Background_Area_Fraction AND touching Background_Borders of
    # the four image borders is the background plane too.
    #   Unit [float] / [float] / [int]
    Hard_Background_Fraction: float = 0.85
    Background_Area_Fraction: float = 0.50
    Background_Borders: int = 3


@dataclass
class Description_Parameters_Str:
    """
    Description:
        Stage 4: the Gemma describer, its two prompts and generation settings, and the limits the
        one background sentence is validated against. Read from the 'Description' block.
    """

    # The Gemma weights directory, absolute once loaded. REQUIRED (no default).
    #   Unit [string]
    Model_Path: str = ''
    # The per-object prompt and the background prompt, whitespace-normalised. REQUIRED: there is
    # no default wording — a prompt nobody wrote is never sent.
    #   Unit [string]
    Prompt_Object: str = ''
    Prompt_Background: str = ''
    # Generation. Temperature 0 is greedy decoding: the same crop and prompt give the same text.
    #   Unit [float] / [int]
    Temperature: float = 0.0
    Max_Tokens: int = 256
    # The empty reference is centre-cropped INWARD by this margin (fraction per side) before the
    # background sentence is described, so the frame-edge vignette stays out of it. It touches
    # only that one sentence — not the object crops (their padding is Object_Crop_Padding).
    #   Unit [float] (fraction per side)
    Background_Crop_Margin: float = 0.12
    # Each object's crop is padded outward by this fraction of its longer side before it is
    # enhanced and described — context around the part, at the cost of pulling neighbours in
    # (which is why the crop is isolated). Set when Florence-2 described a cut-out part poorly;
    # measured for Gemma: see docs/design-decisions.md.
    #   Unit [float] (fraction of the longer side)
    Object_Crop_Padding: float = 0.20
    # The background sentence is replaced by a neutral one when it runs past these limits.
    #   Unit [int]
    Background_Max_Words: int = 20
    Background_Max_Sentences: int = 1


@dataclass
class Identity_Str:
    """
    Description:
        What the UI calls the configuration and its models, and the task a reading is labelled
        with (the Scene Understanding Task row, and 'task' in each capture set). Read from the
        'Identity' block. The model FILES never reach the UI: the header names the model set, the
        dialog the configuration, and the log carries the detail.
    """

    # The configuration's name in the Configuration dialog's list. REQUIRED (no default): a file
    # without it fails to load rather than show its file name.
    #   Unit [string]
    Display_Name: str = ''
    # The model set's name in the header pill. REQUIRED (no default).
    #   Unit [string]
    Model_Set: str = ''
    # The task a model-written reading is labelled with.
    #   Unit [string]
    Task: str = 'part inspection'


@dataclass
class Evaluation_Parameters_Str:
    """
    Description:
        Harness-only settings: read by Example/Vision/analyze.py, never by the application. The
        loader resolves the path and does not check it, so a missing directory never stops the
        application from loading; analyze.py checks it, and each frame's size.
    """

    # The directory of test frames (Image_NNN.png) analyze.py runs on — the pinned set the tests'
    # expectations refer to. Absolute after loading; '' when the configuration does not set it
    # (analyze.py then needs --input-dir).
    #   Unit [string]
    Frames: str = ''


@dataclass
class Configuration_Str:
    """
    Description:
        One loaded, fully validated configuration: a mode file plus the calibration of the
        hardware it names. Only Configuration.Core.Load_Configuration builds one, and only when the
        whole file is valid, so holding one means every field is usable.
    """

    # The mode file (absolute) and its file name — the name recorded in the log and every set.
    #   Unit [string]
    Path: str = ''
    Name: str = ''
    # The hardware the mode runs on and the mode itself, from 'Config_<Hardware>_Mode_<Mode>.yaml'.
    # The hardware keys everything camera-specific: the calibration file and the run-summary CSV.
    #   Unit [string]
    Hardware: str = ''
    Mode: str = ''
    # Whether this configuration classifies (OK/NOK) or only detects.
    #   Unit [bool]
    Classification_Enabled: bool = CONST_CLASSIFICATION_ENABLED_DEFAULT
    # The UI identity, the confidence thresholds, and the vision stages' parameters.
    Identity: Identity_Str = field(default_factory=Identity_Str)
    Confidence: Confidence_Thresholds_Str = field(default_factory=Confidence_Thresholds_Str)
    Segmentation: Segmentation_Parameters_Str = field(default_factory=Segmentation_Parameters_Str)
    Description: Description_Parameters_Str = field(default_factory=Description_Parameters_Str)
    # The camera block, with its Calibration filled from the hardware's calibration file.
    Camera: Camera_Configuration_Str = field(default_factory=Camera_Configuration_Str)
    # The harness-only settings (analyze.py's test frames).
    Evaluation: Evaluation_Parameters_Str = field(default_factory=Evaluation_Parameters_Str)
    # The calibration file the camera block's Calibration came from (absolute).
    #   Unit [string]
    Calibration_Path: str = ''
    # The measurement scale from that calibration, or None: no valid Conversion_Factor, so
    # objects are not measured (the documented 'default' — never an invented number).
    Scale: tp.Optional[Scale_Str] = None
    # What the loader has to say about this file, as (level, message): each optional field that
    # fell back to its default, each key it did not recognise. The caller logs them.
    #   Unit [Vector<Tuple<string> 1x2>]
    Notes: tp.List[tp.Tuple[str, str]] = field(default_factory=list)
