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
# File Name: ../Vision/Utilities/Segmentation.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp

"""
Description:
    Initialization of constants.

    Background-subtraction segmentation: find the foreground objects in a frame by
    differencing it against an empty-surface reference. Areas are fractions of the
    frame. This module holds the segmentation tunables; Vision.Core imports the
    caps it shares (max-area, max-objects) from here.

    Note:
        OpenCV (cv2) and NumPy (np) are passed in to every function rather than
        imported here. That is deliberate: App/run.py imports this module at load
        time, but the heavy runtime (OpenCV) is imported lazily so the window opens
        without it. The caller — which has already loaded cv2/np by the time an
        analysis runs — injects them.
"""
# Segmentation works in COLOUR distance, not brightness: on the green surface a
# grey screw is close to the green in luminance but far from it in colour, so a
# brightness threshold drops dark parts while a colour threshold keeps them.
# Distance is Euclidean over the three 0..255 channels, so it runs 0..441.
CONST_SEG_COLOR_DIST = 40           # min colour distance to count a pixel as foreground
CONST_SEG_STRONG_DIST = 90          # colour distance that is an object regardless of hue
CONST_SEG_SHADOW_TOLERANCE = 0.18   # min per-channel ratio spread; rejects hue-preserving shadow
CONST_SEG_BLUR = 5                  # Gaussian blur kernel before differencing
CONST_SEG_MORPH_KERNEL = 7          # ellipse kernel for open/close
CONST_SEG_OPEN_ITERS = 1
CONST_SEG_CLOSE_ITERS = 3
CONST_SEG_MIN_AREA_FRAC = 0.001     # ignore specks smaller than this
CONST_SEG_MAX_AREA_FRAC = 0.5       # ignore blobs larger than this (lighting drift)
CONST_SEG_MAX_OBJECTS = 12          # cap the number of crops per analysis (shared)
CONST_SEG_CROP_PAD_FRAC = 0.2       # crop margin as a fraction of object size (shared)


def Build_Mask(bg: tp.List[tp.List[float]], fg: tp.List[tp.List[float]],
               cv2: tp.Any, np: tp.Any) -> tp.List[tp.List[int]]:
    """
    Description:
        Foreground mask from the frame and the empty-surface reference.

        Colour distance, not brightness, is the primary test. On the green surface
        a grey or black screw sits close to the green in luminance — a brightness
        threshold silently drops it — yet far from the green in COLOUR, because the
        green channel alone falls sharply. A bright washer is far in every channel.
        Both therefore clear a colour-distance threshold.

        A large distance is an object outright. A moderate distance is an object
        only if the hue also changed (the per-channel ratio spread), which rejects
        the soft shadow a part casts on the surface: a shadow darkens the green but
        keeps its hue, so its channel ratios stay roughly constant.

    Args:
        (1) bg [Matrix<uint8> HxWx3]: The empty-surface background reference (BGR).
        (2) fg [Matrix<uint8> HxWx3]: The captured frame (BGR).
        (3) cv2 [module]: The OpenCV module, injected by the caller.
        (4) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Matrix<uint8> HxW]: The filled foreground mask (0 or 255).
    """

    blur = (CONST_SEG_BLUR, CONST_SEG_BLUR)
    bg_b = cv2.GaussianBlur(bg, blur, 0).astype(np.float32) + 1.0
    fg_b = cv2.GaussianBlur(fg, blur, 0).astype(np.float32) + 1.0

    diff = fg_b - bg_b
    dist = np.sqrt((diff * diff).sum(axis=2))       # Euclidean colour distance

    ratio = fg_b / bg_b
    spread = ratio.max(axis=2) - ratio.min(axis=2)  # hue change; ~0 under shadow

    strong = dist > CONST_SEG_STRONG_DIST           # unmistakable object, any hue
    subtle = (dist > CONST_SEG_COLOR_DIST) & (spread > CONST_SEG_SHADOW_TOLERANCE)
    mask = ((strong | subtle).astype(np.uint8)) * 255

    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                  (CONST_SEG_MORPH_KERNEL, CONST_SEG_MORPH_KERNEL))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=CONST_SEG_OPEN_ITERS)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=CONST_SEG_CLOSE_ITERS)

    # Fill interior holes: washers and nuts are rings whose centre shows
    # background and would otherwise split into two components.
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(mask)
    cv2.drawContours(filled, contours, -1, 255, thickness=cv2.FILLED)
    return filled


def Find_Objects(mask: tp.List[tp.List[int]], cv2: tp.Any, np: tp.Any) -> tp.List[tp.Tuple[int, int, int, int]]:
    """
    Description:
        Object boxes as (x1, y1, x2, y2) in frame pixels, ordered left to right.

        The largest N by area are kept; that selection is preserved, but the
        returned order is left-to-right — the order a person reads in and the
        contract the index draws on. The composer must see them already in this
        order and never reorder after.

    Args:
        (1) mask [Matrix<uint8> HxW]: The foreground mask.
        (2) cv2 [module]: The OpenCV module, injected by the caller.
        (3) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Vector<Tuple<int> 1x4>]: Boxes as (x1, y1, x2, y2).
    """

    h, w = mask.shape
    area_total = float(h * w)
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)

    boxes = []
    for i in range(1, n):  # 0 is background
        x, y, bw, bh, area = stats[i]
        frac = area / area_total
        if frac < CONST_SEG_MIN_AREA_FRAC or frac > CONST_SEG_MAX_AREA_FRAC:
            continue
        # Cast off numpy int32, which is not JSON-serialisable and prints noisily.
        boxes.append((int(x), int(y), int(x + bw), int(y + bh), int(area)))

    # Keep the largest N, then present them left to right.
    boxes.sort(key=lambda b: b[4], reverse=True)
    boxes = boxes[:CONST_SEG_MAX_OBJECTS]
    boxes.sort(key=lambda b: b[0])
    return [b[:4] for b in boxes]


def Crop_With_Pad(img: tp.List[tp.List[float]], box: tp.Tuple[int, int, int, int]) -> tp.List[tp.List[float]]:
    """
    Description:
        Crop from the ORIGINAL image with a margin, clamped to bounds. From the
        original, never the masked frame: Florence-2 is trained on natural images
        and an object floating on black is out of distribution.

    Args:
        (1) img [Matrix<uint8> HxWx3]: The original frame (BGR).
        (2) box [Vector<int> 1x4]: The box as (x1, y1, x2, y2).

    Returns:
        (1) parameter [Matrix<uint8> hxwx3]: The padded crop (BGR).
    """

    h, w = img.shape[:2]
    x1, y1, x2, y2 = box
    pad = int(CONST_SEG_CROP_PAD_FRAC * max(x2 - x1, y2 - y1))
    cx1, cy1 = max(0, x1 - pad), max(0, y1 - pad)
    cx2, cy2 = min(w, x2 + pad), min(h, y2 + pad)
    return img[cy1:cy2, cx1:cx2]
