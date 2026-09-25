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
# File Name: ../Vision/Utilities/Enhancement.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp

"""
Description:
    Initialization of constants.

    Stage 4 crop preparation: take the padded crop of an object and stretch its
    contrast/brightness before the describer sees it, so a washed-out part on the
    green surface exposes its surface detail, edges and true colour to the describer.

    The gain/bias (alpha/beta) are estimated from the OBJECT's own pixels only (a masked
    sample), so the uniform surround does not bias the histogram, and the stretch is given to
    the object alone: the surround is left as it was, so the object sits on its natural table
    for the model, not on a stretched, garish one. (A partial surround blend was a constant set
    to 0, which did nothing; it comes back only with a measurement showing a blend helps.)

    Note:
        OpenCV (cv2) and NumPy (np) are injected by the caller, the Qt-free contract
        the vision domain uses. Get_Alpha_Beta_Parameters (the histogram clip) is the
        single implementation in Camera.Utilities.Image_Processing; it is imported
        lazily inside Enhance_Crop, not at module load, so importing this module pulls
        no OpenCV — App/run.py imports the vision domain before the runtime exists.
"""
# Histogram clip, in percent, for the alpha/beta stretch. A small clip is a robust
# min/max: it ignores the extreme few percent of the object histogram, so a single
# specular highlight or dark speck does not flatten the whole stretch.
CONST_ENHANCE_CLIP_LIMIT = 1.0

# The padded-crop margin is configuration (Description.Object_Crop_Padding): it is passed to
# Padded_Bbox, never read from a constant here.

# The largest gain the stretch may apply. A very dark part gives a tiny histogram
# range and so an enormous gain (6-7x), which blows the object to a garish colour and
# makes the describer hallucinate texture; capping it keeps the stretch a stretch, not
# a solarisation. beta is rescaled with it so the object's floor still maps to black.
CONST_ENHANCE_MAX_ALPHA = 3.5

# The neighbour masks are the fused components, which sit slightly inside a part's
# bright edge; replacing only those pixels leaves a thin outline of the neighbour that
# the stretch then amplifies. Grow every other object's mask by this many pixels before
# subtracting it, so the whole neighbour — edge included — is replaced by table.
CONST_ENHANCE_NEIGHBOUR_DILATE = 11


def Padded_Bbox(bbox: tp.Tuple[int, int, int, int], frame_shape: tp.Tuple[int, int, int],
                padding: float) -> tp.Tuple[int, int, int, int]:
    """
    Description:
        Grow a tight (x, y, w, h) box by `padding` times its longer side, clamped to the
        frame — the box the crop is taken from.

    Args:
        (1) bbox [Vector<int> 1x4]: The tight box as (x, y, w, h).
        (2) frame_shape [Tuple<int>]: The frame's (h, w, c) shape.
        (3) padding [float]: The margin as a fraction of the box's longer side
                             (Description.Object_Crop_Padding).

    Returns:
        (1) parameter [Vector<int> 1x4]: The padded box as (x, y, w, h).
    """

    x, y, bw, bh = bbox
    h, w = frame_shape[:2]
    pad = int(padding * max(bw, bh))
    x1, y1 = max(0, x - pad), max(0, y - pad)
    x2, y2 = min(w, x + bw + pad), min(h, y + bh + pad)
    return (x1, y1, x2 - x1, y2 - y1)


def Crop(image: tp.List[tp.List[int]], bbox: tp.Tuple[int, int, int, int]) -> tp.List[tp.List[int]]:
    """
    Description:
        The (x, y, w, h) sub-image, as a view into the frame.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The frame.
        (2) bbox [Vector<int> 1x4]: The box as (x, y, w, h).

    Returns:
        (1) parameter [Matrix<uint8> hxwx3]: The crop.
    """

    x, y, bw, bh = bbox
    return image[y:y + bh, x:x + bw]


def Isolate_Crop(frame_crop: tp.List[tp.List[int]], background_crop: tp.List[tp.List[int]],
                 own_mask: tp.List[tp.List[int]], others_mask: tp.List[tp.List[int]],
                 np: tp.Any) -> tp.List[tp.List[int]]:
    """
    Description:
        Replace, within a padded crop, the pixels that belong to OTHER detected objects
        with the empty-surface reference, so the crop holds exactly one object plus the
        table and no neighbours. A large object's padded crop otherwise swallows nearby
        parts, and the describer then narrates them ('two white circles on either
        side') — a fault that background stripping cannot fix, because a neighbouring
        object is not background.

    Args:
        (1) frame_crop [Matrix<uint8> hxwx3]: The padded crop from the frame (BGR).
        (2) background_crop [Matrix<uint8> hxwx3]: The same crop from the reference (BGR).
        (3) own_mask [Matrix<bool> hxw]: The object's own mask within the crop.
        (4) others_mask [Matrix<bool> hxw]: The union of every OTHER object's mask, cropped.
        (5) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Matrix<uint8> hxwx3]: The crop with neighbours replaced by table.
    """

    neighbours = (others_mask > 0) & ~(own_mask > 0)
    return np.where(neighbours[..., None], background_crop, frame_crop)


def Enhance_Crop(crop_bgr: tp.List[tp.List[int]], sample_mask: tp.Optional[tp.List[tp.List[int]]],
                 clip_limit: float, cv2: tp.Any, np: tp.Any) -> tp.List[tp.List[int]]:
    """
    Description:
        Contrast/brightness-stretch a padded crop via the alpha/beta histogram clip.
        The gain/bias are estimated with Get_Alpha_Beta_Parameters and applied to
        every channel as g = alpha * f + beta.

        When sample_mask is given and non-empty, ONLY the object pixels feed the
        histogram, so the uniform green surround does not bias the stretch, and only the
        object's pixels are stretched: the table around it is left as it was. Without a
        mask the whole crop is stretched. A flat histogram returns (1.0, 0.0), i.e. the
        crop unchanged.

    Args:
        (1) crop_bgr [Matrix<uint8> hxwx3]: The padded object crop (BGR).
        (2) sample_mask [Matrix<bool> hxw]: The object's mask within the crop, or None
                                            to estimate from the whole crop.
        (3) clip_limit [float]: Histogram clip in percent (CONST_ENHANCE_CLIP_LIMIT).
        (4) cv2 [module]: The OpenCV module, injected by the caller.
        (5) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Matrix<uint8> hxwx3]: The stretched crop (BGR).
    """

    # The histogram clip lives once in the camera utilities; import it lazily so this
    # module (imported at app load) pulls no OpenCV until an analysis runs.
    #   ../Camera/Utilities/Image_Processing
    from Camera.Utilities.Image_Processing import Get_Alpha_Beta_Parameters

    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    if sample_mask is not None and int(np.count_nonzero(sample_mask)) > 0:
        sample = gray[sample_mask > 0].reshape(-1, 1)   # object pixels only
    else:
        sample = gray
    alpha, beta = Get_Alpha_Beta_Parameters(sample, clip_limit)
    # Cap the gain so a very dark part's tiny histogram range cannot solarise it. beta
    # is rescaled by the same factor so the object's floor still maps to black.
    if alpha > CONST_ENHANCE_MAX_ALPHA:
        beta *= CONST_ENHANCE_MAX_ALPHA / alpha
        alpha = CONST_ENHANCE_MAX_ALPHA
    stretched = cv2.convertScaleAbs(crop_bgr, alpha=alpha, beta=beta)

    # The stretch is tuned to the OBJECT; applied to the surround it can push the table to a
    # garish colour. The object gets the stretch and the table keeps its own pixels.
    if sample_mask is None or int(np.count_nonzero(sample_mask)) == 0:
        return stretched
    return np.where(sample_mask[..., None] > 0, stretched, crop_bgr)
