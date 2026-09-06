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
# File Name: ../Vision/Describe_Fallback.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp

"""
Description:
    Initialization of constants.

    A model-free describer: it reads an object's geometry and dominant colour off
    the mask and crop and writes a plain label and sentence, with no VLM. It is a
    real, config-selectable backend (CONST_DESCRIBER == 'fallback'), not a test
    stub — it lets stages 1-3 run and be judged end to end without loading
    Florence-2, and it stands in when the weights are absent.

    Colour is classified in HSV, never by nearest-neighbour in BGR. A mid-dark
    saturated red is close to a 'brown' anchor in BGR (its B/G/R triple sits near
    brown's) but its HUE is unambiguously red; classifying on hue keeps it red.

    Note:
        OpenCV (cv2) and NumPy (np) are injected, the Qt-free vision-domain contract.
"""
# Colour is decided from the median HSV of the masked pixels. Below this value it is
# 'black'; below this saturation it is greyscale ('white' above the light cutoff,
# else 'grey'). OpenCV hue is 0..179.
CONST_COLOR_VALUE_MIN = 40
CONST_COLOR_SAT_MIN = 40
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

    colour = __Colour_Name(__Dominant_Hsv(image, mask, bbox, cv2, np))
    size = __Size_Word(bbox, frame_shape)
    position = __Position_Phrase(bbox, frame_shape)
    shape = __Shape_Word(mask, bbox, cv2, np)

    label = ('%s object' % colour) if colour else 'object'
    detail = ('A %s %s %s object in the %s of the frame.'
              % (size, colour or 'neutral', shape, position))
    return label, detail


def __Dominant_Hsv(image: tp.List[tp.List[int]], mask: tp.List[tp.List[int]],
                   bbox: tp.Tuple[int, int, int, int], cv2: tp.Any, np: tp.Any) -> tp.Optional[tp.Any]:
    """
    Description:
        The median HSV of the object's masked pixels within its box, or None when the
        mask is empty there. The median, not the mean, so a few edge pixels of the
        surrounding surface do not drag the colour.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The full frame (BGR).
        (2) mask [Matrix<bool> HxW]: The object's mask.
        (3) bbox [Vector<int> 1x4]: The object's box as (x, y, w, h).
        (4) cv2 [module]: The OpenCV module, injected by the caller.
        (5) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Vector<float> 1x3 or None]: Median (H, S, V), H in 0..179.
    """

    x, y, w, h = bbox
    sub_image = image[y:y + h, x:x + w]
    sub_mask = mask[y:y + h, x:x + w]
    hsv = cv2.cvtColor(sub_image, cv2.COLOR_BGR2HSV)
    pixels = hsv[sub_mask]
    if pixels.size == 0:
        return None
    return np.median(pixels, axis=0)


def __Colour_Name(hsv: tp.Optional[tp.Any]) -> str:
    """
    Description:
        A colour name from a median HSV. Value and saturation decide black / white /
        grey first; otherwise the hue band names the colour. Classifying on HUE is
        the point: a dark saturated red keeps its red hue where a BGR distance would
        pull it toward brown.

    Args:
        (1) hsv [Vector<float> 1x3 or None]: Median (H, S, V), H in 0..179, or None.

    Returns:
        (1) parameter [string]: The colour name, or '' when unknown.
    """

    if hsv is None:
        return ''
    hue, saturation, value = float(hsv[0]), float(hsv[1]), float(hsv[2])
    if value < CONST_COLOR_VALUE_MIN:
        return 'black'
    if saturation < CONST_COLOR_SAT_MIN:
        return 'white' if value >= CONST_COLOR_LIGHT_MIN else 'grey'
    for upper, name in CONST_COLOR_HUE_BANDS:
        if hue < upper:
            return name
    return 'red'


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
