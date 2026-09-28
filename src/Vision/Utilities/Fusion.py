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
# File Name: ../Vision/Utilities/Fusion.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — the detection structure the objects become
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str
#   ../Parameters/Configuration
from Parameters.Configuration import Segmentation_Parameters_Str

"""
Description:
    Initialization of constants.

    Stage 3 of the pipeline: fuse the two segmentation cues into the objects. The
    foreground the objects are split from is the union of the FastSAM part-masks
    (stage 2) and the background-subtracted mask (stage 1), so an object survives if
    EITHER cue sees it — a part FastSAM misses is kept by the difference, and a dark
    part the difference barely sees is kept by FastSAM. The fused foreground is split
    into connected components, each closed on its own (never bridged to a neighbour),
    filtered by area and ordered left to right in row bands (the operator index contract). Each
    component becomes one Detection_Str carrying which cue(s) located it.

    Note:
        OpenCV (cv2) and NumPy (np) are passed in to every function rather than
        imported here, the same contract the rest of the Qt-free vision domain uses:
        the module imports at load time but the heavy runtime does not.
"""
# The background-like mask rejection (Hard_Background_Fraction, Background_Area_Fraction,
# Background_Borders), the closing kernel and the area filter are configuration, not constants:
# they arrive in Segmentation_Parameters_Str (the 'Segmentation.Fusion' block).
# Row-band height in pixels for the ordering key: components whose top edges fall in
# the same band are ordered left to right, so a slightly higher neighbour does not
# jump the index order. Matches the reading order a human uses across a row.
CONST_FUSE_ROW_BAND = 100
# The minimum fraction of a fused component a cue must cover to be credited with
# locating it. Below this for both cues, the larger contributor is credited, so an
# object is always attributed to at least one cue.
CONST_FUSE_CUE_MIN_OVERLAP = 0.10
# Safety valve: the most objects returned from one frame, so a badly over-segmented
# frame cannot flood stage 4. Ordered first, so it is the trailing components dropped.
CONST_FUSE_MAX_OBJECTS = 12


def Foreground_Union(masks: tp.List, h: int, w: int, np: tp.Any, *,
                     Segmentation_Parameters_Str: Segmentation_Parameters_Str) -> tp.List[tp.List[int]]:
    """
    Description:
        The union of the FastSAM masks, excluding the background-like ones. A mask
        covering at least Hard_Background_Fraction of the frame is the background
        outright; a mask covering at least Background_Area_Fraction that also touches
        at least Background_Borders image borders is the background plane. Every
        other mask contributes to the union — this is the FastSAM cue that stage 3
        fuses with the background-subtracted mask.

    Args:
        (1) masks [Vector<Matrix<bool> HxW>]: The FastSAM instance masks.
        (2) h [int]: The frame height.
        (3) w [int]: The frame width.
        (4) np [module]: The NumPy module, injected by the caller.
        (5) Segmentation_Parameters_Str [Segmentation_Parameters_Str(object)]: REQUIRED,
            keyword-only: the configured background-rejection fractions and border count.

    Returns:
        (1) parameter [Matrix<uint8> HxW]: The union mask (0 or 1).
    """

    Params = Segmentation_Parameters_Str
    union = np.zeros((h, w), np.uint8)
    for mask in masks:
        frac = float(np.count_nonzero(mask)) / float(h * w)
        if frac >= Params.Hard_Background_Fraction:
            continue
        if (frac >= Params.Background_Area_Fraction
                and __Border_Count(mask, np) >= Params.Background_Borders):
            continue
        union |= mask.astype(np.uint8)
    return union


def __Border_Count(mask: tp.List[tp.List[int]], np: tp.Any) -> int:
    """
    Description:
        The number of the four image borders a mask touches (0..4) — high for the
        background plane, zero for a part sitting clear of the frame edge.

    Args:
        (1) mask [Matrix<bool> HxW]: The mask to test.
        (2) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [int]: The count of borders touched (0..4).
    """

    return (int(bool(mask[0, :].any())) + int(bool(mask[-1, :].any()))
            + int(bool(mask[:, 0].any())) + int(bool(mask[:, -1].any())))


def Fuse_Objects(masks: tp.List, scores: tp.List[tp.Optional[float]],
                 background_fg: tp.List[tp.List[int]], cv2: tp.Any, np: tp.Any, *,
                 Segmentation_Parameters_Str: Segmentation_Parameters_Str) -> tp.List[Detection_Str]:
    """
    Description:
        Fuse the FastSAM masks and the background-subtracted mask into the objects.
        The FastSAM union (background-like masks removed) is OR-ed with the
        background foreground, so an object survives on either cue; the result is
        split with connectedComponentsWithStats, each component closed on its own (the
        closing fills its gaps but never joins it to a neighbour), filtered by area and ordered left to right in row bands. Each surviving
        component becomes a Detection_Str carrying its Mask, tight Bbox, the cue(s)
        that located it and the best overlapping FastSAM score. Label and Detail are
        left for stage 4.

    Args:
        (1) masks [Vector<Matrix<bool> HxW>]: The FastSAM instance masks (stage 2).
        (2) scores [Vector<float or None>]: Per-mask FastSAM confidence, aligned.
        (3) background_fg [Matrix<uint8> HxW]: The background-subtracted mask (stage 1).
        (4) cv2 [module]: The OpenCV module, injected by the caller.
        (5) np [module]: The NumPy module, injected by the caller.
        (6) Segmentation_Parameters_Str [Segmentation_Parameters_Str(object)]: REQUIRED,
            keyword-only: the configured rejection, closing kernel and area filter.

    Returns:
        (1) parameter [Vector<Detection_Str(object)>]: The objects, left to right.
    """

    h, w = background_fg.shape[:2]
    sam_fg = Foreground_Union(masks, h, w, np, Segmentation_Parameters_Str=Segmentation_Parameters_Str)
    bg_bool = background_fg > 0
    fused = (sam_fg.astype(bool) | bg_bool).astype(np.uint8)
    if int(fused.max()) == 0:
        return []

    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(fused, connectivity=8)
    labels = __Close_Within_Components(labels, n_labels, stats, Segmentation_Parameters_Str.Close_Kernel, cv2, np)
    min_area = Segmentation_Parameters_Str.Min_Area_Fraction * h * w
    areas = np.bincount(labels.ravel(), minlength=n_labels)
    components = [i for i in range(1, n_labels) if areas[i] >= min_area]

    # Each component's tight box after its closing (the closing can grow it by up to the kernel).
    boxes = {}
    for i in components:
        ys, xs = np.nonzero(labels == i)
        boxes[i] = (int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))

    # Order left to right within row bands (the operator index contract), applied
    # explicitly here and never inherited from the label numbering.
    components.sort(key=lambda i: (boxes[i][1] // CONST_FUSE_ROW_BAND, boxes[i][0]))
    components = components[:CONST_FUSE_MAX_OBJECTS]

    sam_bool = sam_fg > 0
    objects = []
    for i in components:
        comp_mask = labels == i
        x, y, bw, bh = boxes[i]
        area = float(areas[i])

        bg_overlap = float(np.count_nonzero(comp_mask & bg_bool)) / area
        sam_overlap = float(np.count_nonzero(comp_mask & sam_bool)) / area
        objects.append(Detection_Str(
            Label='object', Bbox=(x, y, bw, bh), Confidence=None, Mask=comp_mask,
            Segmenter_Score=__Component_Score(comp_mask, (x, y, bw, bh), masks, scores, np),
            Cue=__Cue(sam_overlap, bg_overlap)))
    return objects


def __Close_Within_Components(labels: tp.List[tp.List[int]], n_labels: int, stats: tp.List[tp.List[int]],
                              close_size: int, cv2: tp.Any, np: tp.Any) -> tp.List[tp.List[int]]:
    """
    Description:
        Close each fused component ON ITS OWN, so the closing fills gaps and notches inside one
        component and never joins two that were separate before it. A pixel a component already
        owns stays its own; a pixel the closing adds is given to the one component that reaches it,
        and to none when two do — the bridge between near neighbours is exactly what must not form.
        Closing the fused mask as a whole joined any two parts less than the kernel apart (two
        plates 9.8 and 10.8 px apart became one object), while on the 20 real test frames it healed
        nothing: every count was the same with no closing at all.

    Args:
        (1) labels [Matrix<int32> HxW]: The fused mask's connected-component labels (0 = ground).
        (2) n_labels [int]: The number of labels, ground included.
        (3) stats [Matrix<int> Nx5]: connectedComponentsWithStats' per-label statistics.
        (4) close_size [int]: The closing kernel [px]; 0 disables the closing.
        (5) cv2 [module]: The OpenCV module, injected by the caller.
        (6) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Matrix<int32> HxW]: The labels with each component's closing added.
    """

    if close_size <= 0:
        return labels
    h, w = labels.shape[:2]
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_size, close_size))
    closed = labels.copy()
    contested = np.zeros((h, w), bool)
    for i in range(1, n_labels):
        # Only the component's box, padded by the kernel, can change.
        x0 = max(0, int(stats[i, cv2.CC_STAT_LEFT]) - close_size)
        y0 = max(0, int(stats[i, cv2.CC_STAT_TOP]) - close_size)
        x1 = min(w, int(stats[i, cv2.CC_STAT_LEFT] + stats[i, cv2.CC_STAT_WIDTH]) + close_size)
        y1 = min(h, int(stats[i, cv2.CC_STAT_TOP] + stats[i, cv2.CC_STAT_HEIGHT]) + close_size)
        window = labels[y0:y1, x0:x1]
        grown = cv2.morphologyEx((window == i).astype(np.uint8), cv2.MORPH_CLOSE, kernel).astype(bool)
        added = grown & (window == 0)
        target, lost = closed[y0:y1, x0:x1], contested[y0:y1, x0:x1]
        clash = added & (target != 0) & (target != i)
        lost |= clash
        target[added & ~lost] = i
        target[lost & (window == 0)] = 0
    return closed


def __Cue(sam_overlap: float, bg_overlap: float) -> str:
    """
    Description:
        Attribute a fused component to the cue(s) that located it: 'both' when each
        cue covers at least CONST_FUSE_CUE_MIN_OVERLAP of it, otherwise the single
        cue that does; when neither reaches the threshold (a component bridged by the
        closing), the larger contributor is credited so an object is never unattributed.

    Args:
        (1) sam_overlap [float]: Fraction of the component the FastSAM union covers.
        (2) bg_overlap [float]: Fraction the background-subtracted mask covers.

    Returns:
        (1) parameter [string]: 'both', 'fastsam' or 'background'.
    """

    seen_sam = sam_overlap >= CONST_FUSE_CUE_MIN_OVERLAP
    seen_bg = bg_overlap >= CONST_FUSE_CUE_MIN_OVERLAP
    if seen_sam and seen_bg:
        return 'both'
    if seen_sam:
        return 'fastsam'
    if seen_bg:
        return 'background'
    return 'fastsam' if sam_overlap >= bg_overlap else 'background'


def __Component_Score(comp_mask: tp.List[tp.List[int]], bbox: tp.Tuple[int, int, int, int], masks: tp.List,
                      scores: tp.List[tp.Optional[float]], np: tp.Any) -> tp.Optional[float]:
    """
    Description:
        The best FastSAM confidence among the masks that overlap this component, or
        None when no scored FastSAM mask overlaps it (a component the background cue
        alone found). A component is a fused blob, not a FastSAM instance, so it has
        no score of its own; this reports the strongest segmenter evidence for it.

        The overlap is tested inside the component's bounding box only: the component's mask
        is empty outside it, so the answer is the same and every mask is compared on a small
        window instead of the whole frame.

    Args:
        (1) comp_mask [Matrix<bool> HxW]: The component's mask.
        (2) bbox [Vector<int> 1x4]: The component's bounding box as (x, y, w, h).
        (3) masks [Vector<Matrix<bool> HxW>]: The FastSAM instance masks.
        (4) scores [Vector<float or None>]: Per-mask FastSAM confidence, aligned.
        (5) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [float]: The best overlapping score, or None.
    """

    x, y, w, h = bbox
    window = comp_mask[y:y + h, x:x + w]
    best = None
    for mask, score in zip(masks, scores):
        if score is None:
            continue
        if np.any(window & mask[y:y + h, x:x + w]):
            best = score if best is None else max(best, score)
    return best
