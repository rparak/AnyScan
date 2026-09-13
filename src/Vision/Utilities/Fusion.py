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
# File Name: ../Vision/Utilities/Fusion.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — the detection structure the objects become
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str

"""
Description:
    Initialization of constants.

    Stage 3 of the pipeline: fuse the two segmentation cues into the objects. The
    foreground the objects are split from is the union of the FastSAM part-masks
    (stage 2) and the background-subtracted mask (stage 1), so an object survives if
    EITHER cue sees it — a part FastSAM misses is kept by the difference, and a dark
    part the difference barely sees is kept by FastSAM. The fused foreground is closed
    to merge the parts of one object, split into connected components, filtered by
    area and ordered left to right in row bands (the operator index contract). Each
    component becomes one Detection_Str carrying which cue(s) located it.

    Note:
        OpenCV (cv2) and NumPy (np) are passed in to every function rather than
        imported here, the same contract the rest of the Qt-free vision domain uses:
        the module imports at load time but the heavy runtime does not.
"""
# Background-like FastSAM-mask rejection, before the union. FastSAM in everything-mode
# returns the table itself as a mask; a mask this large is the background regardless
# of where it sits ...
CONST_FUSE_HARD_BG_FRAC = 0.85
# ... and a mask merely large (this fraction of the frame) that also touches at least
# CONST_FUSE_BG_BORDERS of the four image borders is the background plane too.
CONST_FUSE_BG_AREA_FRAC = 0.50
CONST_FUSE_BG_BORDERS = 3
# Morphological closing kernel applied to the fused foreground, to bridge the small
# gaps between the parts of one object (e.g. FastSAM and the difference each seeing a
# different half) before the components are counted.
CONST_FUSE_CLOSE_KERNEL = 15
# Drop a connected component smaller than this fraction of the frame (a speck).
CONST_FUSE_MIN_AREA_FRAC = 5e-4
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


def Foreground_Union(masks: tp.List, h: int, w: int, np: tp.Any) -> tp.List[tp.List[int]]:
    """
    Description:
        The union of the FastSAM masks, excluding the background-like ones. A mask
        covering at least CONST_FUSE_HARD_BG_FRAC of the frame is the background
        outright; a mask covering at least CONST_FUSE_BG_AREA_FRAC that also touches
        at least CONST_FUSE_BG_BORDERS image borders is the background plane. Every
        other mask contributes to the union — this is the FastSAM cue that stage 3
        fuses with the background-subtracted mask.

    Args:
        (1) masks [Vector<Matrix<bool> HxW>]: The FastSAM instance masks.
        (2) h [int]: The frame height.
        (3) w [int]: The frame width.
        (4) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Matrix<uint8> HxW]: The union mask (0 or 1).
    """

    union = np.zeros((h, w), np.uint8)
    for mask in masks:
        frac = float(np.count_nonzero(mask)) / float(h * w)
        if frac >= CONST_FUSE_HARD_BG_FRAC:
            continue
        if frac >= CONST_FUSE_BG_AREA_FRAC and __Border_Count(mask, np) >= CONST_FUSE_BG_BORDERS:
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
                 background_fg: tp.List[tp.List[int]], cv2: tp.Any, np: tp.Any) -> tp.List[Detection_Str]:
    """
    Description:
        Fuse the FastSAM masks and the background-subtracted mask into the objects.
        The FastSAM union (background-like masks removed) is OR-ed with the
        background foreground, so an object survives on either cue; the result is
        closed to merge the parts of one object, split with connectedComponentsWithStats,
        filtered by area and ordered left to right in row bands. Each surviving
        component becomes a Detection_Str carrying its Mask, tight Bbox, the cue(s)
        that located it, the fraction the background cue covered (Change_Coverage) and
        the best overlapping FastSAM score. Label and Detail are left for stage 4.

    Args:
        (1) masks [Vector<Matrix<bool> HxW>]: The FastSAM instance masks (stage 2).
        (2) scores [Vector<float or None>]: Per-mask FastSAM confidence, aligned.
        (3) background_fg [Matrix<uint8> HxW]: The background-subtracted mask (stage 1).
        (4) cv2 [module]: The OpenCV module, injected by the caller.
        (5) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Vector<Detection_Str(object)>]: The objects, left to right.
    """

    h, w = background_fg.shape[:2]
    sam_fg = Foreground_Union(masks, h, w, np)
    bg_bool = background_fg > 0
    fused = (sam_fg.astype(bool) | bg_bool).astype(np.uint8)
    if int(fused.max()) == 0:
        return []

    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (CONST_FUSE_CLOSE_KERNEL, CONST_FUSE_CLOSE_KERNEL))
    closed = cv2.morphologyEx(fused * 255, cv2.MORPH_CLOSE, kernel)

    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(closed, connectivity=8)
    min_area = CONST_FUSE_MIN_AREA_FRAC * h * w
    components = [i for i in range(1, n_labels)
                 if stats[i, cv2.CC_STAT_AREA] >= min_area]

    # Order left to right within row bands (the operator index contract), applied
    # explicitly here and never inherited from the label numbering.
    components.sort(key=lambda i: (stats[i, cv2.CC_STAT_TOP] // CONST_FUSE_ROW_BAND,
                                   stats[i, cv2.CC_STAT_LEFT]))
    components = components[:CONST_FUSE_MAX_OBJECTS]

    sam_bool = sam_fg > 0
    objects = []
    for i in components:
        comp_mask = labels == i
        x = int(stats[i, cv2.CC_STAT_LEFT]); y = int(stats[i, cv2.CC_STAT_TOP])
        bw = int(stats[i, cv2.CC_STAT_WIDTH]); bh = int(stats[i, cv2.CC_STAT_HEIGHT])
        area = float(stats[i, cv2.CC_STAT_AREA])

        bg_overlap = float(np.count_nonzero(comp_mask & bg_bool)) / area
        sam_overlap = float(np.count_nonzero(comp_mask & sam_bool)) / area
        objects.append(Detection_Str(
            Label='object', Bbox=(x, y, bw, bh), Confidence=None, Mask=comp_mask,
            Change_Coverage=bg_overlap, Segmenter_Score=__Component_Score(comp_mask, masks, scores, np),
            Cue=__Cue(sam_overlap, bg_overlap)))
    return objects


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


def __Component_Score(comp_mask: tp.List[tp.List[int]], masks: tp.List,
                      scores: tp.List[tp.Optional[float]], np: tp.Any) -> tp.Optional[float]:
    """
    Description:
        The best FastSAM confidence among the masks that overlap this component, or
        None when no scored FastSAM mask overlaps it (a component the background cue
        alone found). A component is a fused blob, not a FastSAM instance, so it has
        no score of its own; this reports the strongest segmenter evidence for it.

    Args:
        (1) comp_mask [Matrix<bool> HxW]: The component's mask.
        (2) masks [Vector<Matrix<bool> HxW>]: The FastSAM instance masks.
        (3) scores [Vector<float or None>]: Per-mask FastSAM confidence, aligned.
        (4) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [float]: The best overlapping score, or None.
    """

    best = None
    for mask, score in zip(masks, scores):
        if score is None:
            continue
        if np.any(comp_mask & mask):
            best = score if best is None else max(best, score)
    return best
