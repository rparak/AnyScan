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
# File Name: ../Vision/Utilities/Mask_Filter.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — the detection structure the survivors become
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str

"""
Description:
    Initialization of constants.

    Stage 3 of the pipeline: decide which segmenter masks are objects, and reduce
    them to one clean detection each. FastSAM has no notion of which masks matter —
    in everything-mode it returns the table, the fixture and the conveyor alongside
    the parts — so this module gates every mask against the stage-1 change mask,
    rejects whole-scene and border masks, suppresses the part-and-whole duplicates
    FastSAM routinely returns, orders the survivors left to right (the operator
    index contract) and hands back a Detection_Str per survivor.

    This replaces the old OpenCV region filtering (Find_Objects). The area cap and
    the crop padding are ported from it unchanged — they were generic blob hygiene,
    not part knowledge; the only intended change is what feeds them (per-instance
    masks, not connected-component blobs).

    Note:
        OpenCV (cv2) and NumPy (np) are passed in to every function rather than
        imported here, the same contract the rest of the Qt-free vision domain uses:
        the module imports at load time but the heavy runtime does not.
"""
# Keep a mask only if at least this fraction of it overlaps the stage-1 change
# mask. This is what discards the static scene; it is why stage 1 still returns a
# mask, and why that mask is dilated (an under-grown mask starves thin edges here).
CONST_FILTER_CHANGE_COVERAGE = 0.35
# Reject a mask smaller than this many pixels (a speck) ...
CONST_FILTER_MIN_AREA_PX = 400
# ... or larger than this fraction of the frame (a whole-scene / background mask).
CONST_FILTER_MAX_AREA_FRAC = 0.5
# The frame-edge band, and the most of a mask that may fall inside it before the
# mask is read as the background plane rather than a part on the surface.
CONST_FILTER_BORDER_MARGIN_PX = 4
CONST_FILTER_BORDER_MAX_FRAC = 0.30
# Mask NMS: suppress a lower-ranked mask overlapping a kept one above this.
# DO NOT change this to IoU. The overlap is measured as intersection over the
# SMALLER mask on purpose. The thing being suppressed is FastSAM returning a part
# AND its whole as two masks; a part inside its whole has, by construction, a LOW
# IoU (small intersection / large union) but a near-total intersection-over-smaller.
# Plain IoU therefore cannot catch containment — it would leave every part/whole
# pair live, which is exactly the failure this NMS exists to prevent.
CONST_FILTER_NMS_OVERLAP = 0.90
# Cap the survivors per analysis (ported from the segmentation object cap).
CONST_FILTER_MAX_OBJECTS = 12
# Padded-crop margin as a fraction of the object's size (ported from the crop pad).
CONST_FILTER_CROP_PAD_FRAC = 0.2
# BGR fill for the non-mask pixels of the masked crop — a flat, near-black ground
# so Florence-2 describes the object, not the neighbouring clutter in its box.
CONST_FILTER_MASK_FILL = (16, 16, 16)


def Filter_Masks(masks: tp.List, scores: tp.List[tp.Optional[float]],
                 change_mask: tp.List[tp.List[int]], cv2: tp.Any, np: tp.Any) -> tp.List[Detection_Str]:
    """
    Description:
        Reduce the segmenter's masks to the objects that matter, as ordered
        Detection_Str carriers. Each survivor passes the change-coverage gate, the
        area bounds and the border test; the part-and-whole duplicates are then
        suppressed, the field is capped, and the survivors are ordered left to right
        — the operator index contract, applied here explicitly and never inherited
        from the segmenter's own order.

        Each returned Detection_Str carries its Mask, tight Bbox (x, y, w, h),
        Change_Coverage and Segmenter_Score; Label and Detail are left for stage 4.

    Args:
        (1) masks [Vector<Matrix<bool> HxW>]: The segmenter masks, frame resolution.
        (2) scores [Vector<float or None>]: Per-mask confidence, aligned with masks.
        (3) change_mask [Matrix<uint8> HxW]: The stage-1 change mask (0 or 255).
        (4) cv2 [module]: The OpenCV module, injected by the caller.
        (5) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Vector<Detection_Str(object)>]: The survivors, left to right.
    """

    h, w = change_mask.shape[:2]
    frame_area = float(h * w)
    change_bool = change_mask > 0

    survivors = []
    for mask, score in zip(masks, scores):
        area = int(np.count_nonzero(mask))
        if area < CONST_FILTER_MIN_AREA_PX:
            continue
        if (area / frame_area) > CONST_FILTER_MAX_AREA_FRAC:
            continue
        coverage = float(np.count_nonzero(mask & change_bool)) / area
        if coverage < CONST_FILTER_CHANGE_COVERAGE:
            continue
        if __Border_Fraction(mask, area, np) > CONST_FILTER_BORDER_MAX_FRAC:
            continue
        survivors.append(Detection_Str(
            Label='object', Bbox=__Tight_Bbox(mask, np), Confidence=None,
            Mask=mask, Change_Coverage=coverage, Segmenter_Score=score))

    # Rank by change coverage first, then segmenter confidence — the NMS keeps the
    # higher-ranked mask of an overlapping pair.
    survivors.sort(key=lambda d: (d.Change_Coverage, d.Segmenter_Score or 0.0), reverse=True)
    kept = __Suppress_Overlaps(survivors, np)[:CONST_FILTER_MAX_OBJECTS]

    # Left to right (the index contract), applied explicitly on the tight box.
    kept.sort(key=lambda d: d.Bbox[0])
    return kept


def __Tight_Bbox(mask: tp.List[tp.List[int]], np: tp.Any) -> tp.Tuple[int, int, int, int]:
    """
    Description:
        The tight bounding box of a boolean mask as (x, y, w, h) in frame pixels.

    Args:
        (1) mask [Matrix<bool> HxW]: The instance mask.
        (2) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Vector<int> 1x4]: The box as (x, y, w, h).
    """

    ys, xs = np.where(mask)
    x1, y1 = int(xs.min()), int(ys.min())
    x2, y2 = int(xs.max()) + 1, int(ys.max()) + 1
    return (x1, y1, x2 - x1, y2 - y1)


def __Border_Fraction(mask: tp.List[tp.List[int]], area: int, np: tp.Any) -> float:
    """
    Description:
        The fraction of a mask's pixels that lie within CONST_FILTER_BORDER_MARGIN_PX
        of the frame edge — high for the background plane, low for a part.

    Args:
        (1) mask [Matrix<bool> HxW]: The instance mask.
        (2) area [int]: The mask's pixel count (its own denominator).
        (3) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [float]: The border-band fraction (0..1).
    """

    margin = CONST_FILTER_BORDER_MARGIN_PX
    band = np.zeros_like(mask, dtype=bool)
    band[:margin, :] = True
    band[-margin:, :] = True
    band[:, :margin] = True
    band[:, -margin:] = True
    return float(np.count_nonzero(mask & band)) / float(area)


def __Overlap_Over_Smaller(mask_a: tp.List[tp.List[int]], mask_b: tp.List[tp.List[int]],
                           np: tp.Any) -> float:
    """
    Description:
        Intersection of two masks over the area of the SMALLER one. Near 1.0 for
        both a near-duplicate and a part fully inside its whole. This is deliberately
        NOT IoU: a contained part has a low IoU but a high intersection-over-smaller,
        so IoU would miss exactly the part/whole pair the NMS must suppress. See
        CONST_FILTER_NMS_OVERLAP.

    Args:
        (1) mask_a [Matrix<bool> HxW]: The first mask.
        (2) mask_b [Matrix<bool> HxW]: The second mask.
        (3) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [float]: The intersection-over-smaller ratio (0..1).
    """

    intersection = int(np.count_nonzero(mask_a & mask_b))
    if intersection == 0:
        return 0.0
    smaller = min(int(np.count_nonzero(mask_a)), int(np.count_nonzero(mask_b)))
    return intersection / float(smaller)


def __Suppress_Overlaps(ranked: tp.List[Detection_Str], np: tp.Any) -> tp.List[Detection_Str]:
    """
    Description:
        Greedy mask NMS over a rank-ordered list: keep each mask, then drop every
        lower-ranked mask overlapping it above CONST_FILTER_NMS_OVERLAP. This is
        what removes FastSAM's part-and-whole duplicates.

    Args:
        (1) ranked [Vector<Detection_Str(object)>]: The survivors, highest rank first.
        (2) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Vector<Detection_Str(object)>]: The kept masks, rank order.
    """

    kept = []
    suppressed = [False] * len(ranked)
    for i in range(len(ranked)):
        if suppressed[i]:
            continue
        kept.append(ranked[i])
        for j in range(i + 1, len(ranked)):
            if suppressed[j]:
                continue
            if __Overlap_Over_Smaller(ranked[i].Mask, ranked[j].Mask, np) > CONST_FILTER_NMS_OVERLAP:
                suppressed[j] = True
    return kept


def Padded_Bbox(bbox: tp.Tuple[int, int, int, int],
                frame_shape: tp.Tuple[int, int, int]) -> tp.Tuple[int, int, int, int]:
    """
    Description:
        Grow a tight (x, y, w, h) box by CONST_FILTER_CROP_PAD_FRAC of its size,
        clamped to the frame — the box the crop is taken from.

    Args:
        (1) bbox [Vector<int> 1x4]: The tight box as (x, y, w, h).
        (2) frame_shape [Tuple<int>]: The frame's (h, w, c) shape.

    Returns:
        (1) parameter [Vector<int> 1x4]: The padded box as (x, y, w, h).
    """

    x, y, bw, bh = bbox
    h, w = frame_shape[:2]
    pad = int(CONST_FILTER_CROP_PAD_FRAC * max(bw, bh))
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


def Masked_Crop(image: tp.List[tp.List[int]], mask: tp.List[tp.List[int]],
                bbox: tp.Tuple[int, int, int, int], np: tp.Any) -> tp.List[tp.List[int]]:
    """
    Description:
        The (x, y, w, h) crop with every non-mask pixel flattened to
        CONST_FILTER_MASK_FILL, so a describer narrates the object and not the
        neighbouring clutter that shares its bounding box.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The frame.
        (2) mask [Matrix<bool> HxW]: The object's mask, frame resolution.
        (3) bbox [Vector<int> 1x4]: The box as (x, y, w, h).
        (4) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Matrix<uint8> hxwx3]: The masked crop.
    """

    x, y, bw, bh = bbox
    sub_image = image[y:y + bh, x:x + bw]
    sub_mask = mask[y:y + bh, x:x + bw]
    fill = np.array(CONST_FILTER_MASK_FILL, dtype=sub_image.dtype)
    return np.where(sub_mask[..., None], sub_image, fill)
