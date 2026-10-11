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
# File Name: ../Vision/Describe_Fallback.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp

"""
Description:
    Initialization of constants.

    A model-free describer: it reads an object's geometry and dominant colour off
    the mask and crop and writes a plain label and sentence, with no VLM. It is a
    real backend, selected by setting the code constant Vision.Core.CONST_DESCRIBER to
    'fallback' (the harness and the weight-free tests do; it is not configuration, and the
    application always runs Gemma), not a test stub — it lets stages 1-3 run and be judged
    end to end without loading a model. It does NOT stand in when the weights are absent:
    then the Gemma load fails with a Vision_Error_Cls naming the missing weights.

    Colour is a per-pixel MAJORITY VOTE over the masked pixels, classified in HSV.
    The vote is deliberate, not an average: OpenCV hue wraps at 0/180, and red sits at
    BOTH ends (a real red part scatters pixels near hue 0 AND near hue 179), so the
    median or mean hue of a red object lands halfway between the two lobes — around
    109, which reads as blue. Voting on each pixel's colour name instead lets both red
    lobes count as 'red', so a red object votes red. Neutrals (low saturation) skip
    the hue entirely and are unaffected, which is why only red mis-read before.

    Note:
        OpenCV (cv2) and NumPy (np) are injected, the Qt-free vision-domain contract.
"""
# Colour is voted per masked pixel. Below this value a pixel is 'black'; below this
# saturation it is greyscale ('white' above the light cutoff, else 'grey'); otherwise
# its hue names it. OpenCV hue is 0..179. The saturation cutoff is set for machined
# metal: bare steel under the green-lit rig carries a genuine but weak colour cast, which a
# low cutoff mis-reads as blue, while a real coloured part sits higher — so the cutoff sits in
# that gap. Median saturation on Data/Images/Test/All (2026-09-28; the previous set, no longer in the
# repository, recoverable from 1061966): metal, plastic and white
# parts 2-78, the blue parts 168-189, the red block 124-143 — the tight side of the gap.
CONST_COLOR_VALUE_MIN = 40
CONST_COLOR_SAT_MIN = 120
CONST_COLOR_LIGHT_MIN = 180
# Hue upper bounds (OpenCV 0..179) mapped to a colour name; red wraps both ends.
CONST_COLOR_HUE_BANDS = ((10, 'red'), (20, 'orange'), (33, 'yellow'), (85, 'green'),
                         (128, 'blue'), (160, 'purple'), (180, 'red'))
# Aspect ratio (long side / short side) at or above which an object reads as
# 'elongated' rather than 'compact'.
CONST_SHAPE_ELONGATED_RATIO = 1.6
# Solidity (mask area / convex-hull area) below which an object reads as 'irregular'
# rather than 'smooth'.
CONST_SHAPE_SOLID_MIN = 0.9
# Object area as a fraction of the frame: below the first is 'small', above the
# second is 'large', between is 'medium'.
CONST_SIZE_SMALL_FRAC = 0.02
CONST_SIZE_LARGE_FRAC = 0.10


def Describe_Fallback(image: tp.List[tp.List[int]], mask: tp.List[tp.List[int]],
                      bbox: tp.Tuple[int, int, int, int], frame_shape: tp.Tuple[int, int, int],
                      cv2: tp.Any, np: tp.Any) -> tp.Tuple[str, str]:
    """
    Description:
        A model-free (Label, Detail) for one object, from its mask and crop: dominant
        colour (HSV), size, position, aspect and solidity. No model is loaded.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The full frame (BGR).
        (2) mask [Matrix<bool> HxW]: The object's mask, frame resolution.
        (3) bbox [Vector<int> 1x4]: The object's tight box as (x, y, w, h).
        (4) frame_shape [Tuple<int>]: The frame's (h, w, c) shape.
        (5) cv2 [module]: The OpenCV module, injected by the caller.
        (6) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Tuple<string> 1x2]: The (Label, Detail) pair.
    """

    colour = __Dominant_Colour(image, mask, bbox, cv2, np)
    size = __Size_Word(bbox, frame_shape)
    position = __Position_Phrase(bbox, frame_shape)
    shape = __Shape_Word(mask, bbox, cv2, np)

    label = ('%s object' % colour) if colour else 'object'
    detail = ('A %s %s %s object in the %s of the frame.'
              % (size, colour or 'neutral', shape, position))
    return label, detail


def __Dominant_Colour(image: tp.List[tp.List[int]], mask: tp.List[tp.List[int]],
                      bbox: tp.Tuple[int, int, int, int], cv2: tp.Any, np: tp.Any) -> str:
    """
    Description:
        The dominant colour name of the object's masked pixels, by per-pixel majority
        vote. Each masked pixel is named: below CONST_COLOR_VALUE_MIN value it is
        'black'; below CONST_COLOR_SAT_MIN saturation it is 'white' (light) or 'grey';
        otherwise its hue band names it. The most common name wins.

        The vote — not a median or mean of the hue — is what makes red robust: red
        scatters across BOTH ends of the 0..179 hue circle, so averaging its hue lands
        between the two lobes (~109, a false blue), while voting lets both lobes count
        as 'red'. It also shrugs off the minority of surface pixels the filled mask
        includes at drilled holes.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The full frame (BGR).
        (2) mask [Matrix<bool> HxW]: The object's mask.
        (3) bbox [Vector<int> 1x4]: The object's box as (x, y, w, h).
        (4) cv2 [module]: The OpenCV module, injected by the caller.
        (5) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [string]: The dominant colour name, or '' when the mask is empty.
    """

    x, y, w, h = bbox
    sub_image = image[y:y + h, x:x + w]
    sub_mask = mask[y:y + h, x:x + w]
    pixels = cv2.cvtColor(sub_image, cv2.COLOR_BGR2HSV)[sub_mask]
    if pixels.size == 0:
        return ''

    hue, saturation, value = pixels[:, 0], pixels[:, 1], pixels[:, 2]
    names = np.empty(len(pixels), dtype=object)
    black = value < CONST_COLOR_VALUE_MIN
    neutral = (~black) & (saturation < CONST_COLOR_SAT_MIN)
    chromatic = (~black) & (~neutral)
    names[black] = 'black'
    names[neutral & (value >= CONST_COLOR_LIGHT_MIN)] = 'white'
    names[neutral & (value < CONST_COLOR_LIGHT_MIN)] = 'grey'

    # Chromatic pixels: the hue band each falls in. searchsorted on the band upper
    # bounds names both red lobes (< 10 and >= 160) 'red', so red survives the vote.
    uppers = np.array([upper for upper, _ in CONST_COLOR_HUE_BANDS])
    band_names = [name for _, name in CONST_COLOR_HUE_BANDS]
    idx = np.clip(np.searchsorted(uppers, hue[chromatic], side='right'), 0, len(band_names) - 1)
    names[chromatic] = [band_names[i] for i in idx]

    values, counts = np.unique(names.astype(str), return_counts=True)
    return str(values[counts.argmax()])


def __Size_Word(bbox: tp.Tuple[int, int, int, int], frame_shape: tp.Tuple[int, int, int]) -> str:
    """
    Description:
        'small' / 'medium' / 'large' from the box area as a fraction of the frame.

    Args:
        (1) bbox [Vector<int> 1x4]: The object's box as (x, y, w, h).
        (2) frame_shape [Tuple<int>]: The frame's (h, w, c) shape.

    Returns:
        (1) parameter [string]: The size word.
    """

    _, _, w, h = bbox
    fh, fw = frame_shape[:2]
    frac = (w * h) / float(fh * fw)
    if frac < CONST_SIZE_SMALL_FRAC:
        return 'small'
    if frac > CONST_SIZE_LARGE_FRAC:
        return 'large'
    return 'medium'


def __Position_Phrase(bbox: tp.Tuple[int, int, int, int], frame_shape: tp.Tuple[int, int, int]) -> str:
    """
    Description:
        A coarse position for the box centre, e.g. 'top left' or 'centre'.

    Args:
        (1) bbox [Vector<int> 1x4]: The object's box as (x, y, w, h).
        (2) frame_shape [Tuple<int>]: The frame's (h, w, c) shape.

    Returns:
        (1) parameter [string]: The position phrase.
    """

    x, y, w, h = bbox
    fh, fw = frame_shape[:2]
    cx, cy = (x + w / 2.0) / fw, (y + h / 2.0) / fh
    horizontal = 'left' if cx < 0.34 else ('right' if cx > 0.66 else 'centre')
    vertical = 'top' if cy < 0.34 else ('bottom' if cy > 0.66 else 'middle')
    if horizontal == 'centre' and vertical == 'middle':
        return 'centre'
    if horizontal == 'centre':
        return vertical
    if vertical == 'middle':
        return horizontal
    return '%s %s' % (vertical, horizontal)


def __Shape_Word(mask: tp.List[tp.List[int]], bbox: tp.Tuple[int, int, int, int],
                 cv2: tp.Any, np: tp.Any) -> str:
    """
    Description:
        A shape hint from the box aspect ratio and the mask solidity: 'elongated' vs
        'compact', qualified 'irregular' when the mask is far from its convex hull.

    Args:
        (1) mask [Matrix<bool> HxW]: The object's mask.
        (2) bbox [Vector<int> 1x4]: The object's box as (x, y, w, h).
        (3) cv2 [module]: The OpenCV module, injected by the caller.
        (4) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [string]: The shape word.
    """

    _, _, w, h = bbox
    ratio = max(w, h) / float(max(1, min(w, h)))
    form = 'elongated' if ratio >= CONST_SHAPE_ELONGATED_RATIO else 'compact'

    solidity = __Solidity(mask, cv2, np)
    if solidity is not None and solidity < CONST_SHAPE_SOLID_MIN:
        return 'irregular %s' % form
    return form


def __Solidity(mask: tp.List[tp.List[int]], cv2: tp.Any, np: tp.Any) -> tp.Optional[float]:
    """
    Description:
        The mask's solidity — its area over its convex-hull area — or None when there
        is no contour. Near 1.0 for a convex blob, lower for a ragged or holed one.

    Args:
        (1) mask [Matrix<bool> HxW]: The object's mask.
        (2) cv2 [module]: The OpenCV module, injected by the caller.
        (3) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [float or None]: The solidity ratio.
    """

    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    hull_area = cv2.contourArea(cv2.convexHull(contour))
    if hull_area <= 0:
        return None
    return float(cv2.contourArea(contour)) / hull_area
