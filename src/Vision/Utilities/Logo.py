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
# File Name: ../Vision/Utilities/Logo.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — the logo structures, the catalogue's logo check, and the reference crop
#   ../Parameters/Vision
from Parameters.Vision import Logo_Result_Str, Logo_Letter_Str
#   ../Parameters/Catalogue
from Parameters.Catalogue import Catalogue_Logo_Str, Catalogue_Logo_Reference_Str
#   ../Vision/Utilities/Classify
from Vision.Utilities.Classify import Reference_Crop

"""
Description:
    Initialization of constants.

    The catalogue's logo check on a judged part's side (Checks.Logo.<side>). Each reference is one plate of a logo
    variant: its image turned to read upright and cut by its box, with each letter's box. A part's crop is registered
    to each reference by SIFT features (a similarity transform, RANSAC); none reaching Min_Matches means no
    inscription. Each letter is compared with that letter in every reference it registered to — the normalised
    correlation of their edge images (CLAHE first), the best kept — and is there at Letter_Min_Similarity and
    Letter_Min_Contrast (its edges against the part's own plate). Qt-free, OpenCV and NumPy injected.

    Measured on the test set's 16 labyrinth backs (2026-10-11), four references (filled letters; outline letters
    on two plates, since each plate's light leaves other letters dim; filled letters on a dark, glare-lit plate):
    the 4 blank plates register with at most 12 matches, every logo with at least 54; the 12 complete logos read
    complete, the 11 that are not that dark plate with least letter 0.77 (contrast 3.24); each of those 11 logos'
    165 letters erased in turn (synthetic, inpainted) at most 0.47, except two J at 0.58-0.59 whose inpainted seam
    keeps the J's shape at contrast 0.18-0.19. About 65-105 ms per back on the CPU (M-series), the references
    prepared once per configuration. Correlation alignment without features failed even on the
    reference frame; OCR cannot read the stylised JIC.
"""

# CLAHE before every comparison, clip 2 on 8 x 8 tiles. Measured with the check as built (complete letters' least
# similarity / the erased J seams' / the blank plates' most matches): off 0.73 / 0.74 / 6 — shape alone cannot
# tell them apart; clip 1 0.81 / 0.58 / 23; clip 2 0.77 / 0.59 / 12; clip 4 0.60 / 0.61 / 4. Clip 2 keeps the
# blanks far under Min_Matches with the letters apart.
#   Unit [float] / [int]
CONST_LOGO_CLAHE_CLIP = 2.0
CONST_LOGO_CLAHE_TILES = 8
# Lowe's ratio for a feature match, and the RANSAC reprojection threshold of the registration.
#   Unit [float] / [float] (px)
CONST_LOGO_MATCH_RATIO = 0.75
CONST_LOGO_RANSAC_PX = 4.0
# The edge image's smoothing. A letter is compared where the registration puts it: searching ±4 px around that
# was measured (2026-10-11) and moved no complete letter's and no erased letter's score by 0.01.
#   Unit [float] (px)
CONST_LOGO_EDGE_SIGMA = 1.5
# A letter's contrast: its edges where the reference's are above this fraction of their strongest (its strokes),
# against the mean edge of the part's plate — the crop's middle, this fraction cut from each edge, the letters'
# boxes grown by this many pixels left out.
#   Unit [float] / [float] / [int] (px)
CONST_LOGO_STROKE_FRACTION = 0.5
CONST_LOGO_PLATE_MARGIN = 0.12
CONST_LOGO_LETTER_MARGIN_PX = 6


def Reference_Logo_Crop(image_bgr: tp.Any, Catalogue_Logo_Reference_Str: Catalogue_Logo_Reference_Str, cv2: tp.Any,
                        np: tp.Any) -> tp.Any:
    """
    Description:
        A logo reference's part: its image turned Rotation_Deg about the part's YOLO box centre, so the logo reads
        upright and level, then cut by the box (Vision.Utilities.Classify.Reference_Crop). Its letters' boxes are in
        this crop's pixels; Example/Catalogue/logo_letters.py draws them on the same crop. The box, not the outline:
        the background difference finds only half of the outline-letter plate (FastSAM finds it in the pipeline),
        and the registration's similarity transform takes up the box's margin.

    Args:
        (1) image_bgr [Matrix<uint8> HxWx3]: The reference image.
        (2) Catalogue_Logo_Reference_Str [Catalogue_Logo_Reference_Str(object)]: The reference.
        (3) cv2 [module]: The OpenCV module, injected by the caller.
        (4) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Matrix<uint8> hxwx3]: The crop.
    """

    reference = Catalogue_Logo_Reference_Str
    height, width = image_bgr.shape[:2]
    centre = (reference.Box[0] * width, reference.Box[1] * height)
    turned = cv2.warpAffine(image_bgr, cv2.getRotationMatrix2D(centre, reference.Rotation_Deg, 1.0), (width, height),
                            flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return np.ascontiguousarray(Reference_Crop(turned, reference.Box))


def __Gray(image_bgr: tp.Any, cv2: tp.Any) -> tp.Any:
    """
    Description:
        The image as CLAHE-equalised grey: what features are found on and letters are compared in.

    Args:
        (1) image_bgr [Matrix<uint8> hxwx3]: The image.
        (2) cv2 [module]: The OpenCV module.

    Returns:
        (1) parameter [Matrix<uint8> hxw]: The grey image.
    """

    clahe = cv2.createCLAHE(CONST_LOGO_CLAHE_CLIP, (CONST_LOGO_CLAHE_TILES, CONST_LOGO_CLAHE_TILES))
    return clahe.apply(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY))


def __Edges(gray: tp.Any, cv2: tp.Any, np: tp.Any) -> tp.Any:
    """
    Description:
        The gradient magnitude of a smoothed grey image: the engraving's outlines, whichever way the light falls.

    Args:
        (1) gray [Matrix<uint8> hxw]: The grey image.
        (2) cv2 [module]: The OpenCV module.
        (3) np [module]: The NumPy module.

    Returns:
        (1) parameter [Matrix<float32> hxw]: The edges.
    """

    smooth = cv2.GaussianBlur(gray.astype(np.float32), (0, 0), CONST_LOGO_EDGE_SIGMA)
    return cv2.magnitude(cv2.Sobel(smooth, cv2.CV_32F, 1, 0), cv2.Sobel(smooth, cv2.CV_32F, 0, 1))


def __Correlation(a: tp.Any, b: tp.Any, np: tp.Any) -> float:
    """
    Description:
        The normalised correlation of two equal-sized images, 0 when either is flat.

    Args:
        (1) a [Matrix<float>]: One image.
        (2) b [Matrix<float>]: The other.
        (3) np [module]: The NumPy module.

    Returns:
        (1) parameter [float]: -1 to 1.
    """

    a, b = a - a.mean(), b - b.mean()
    denominator = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum()) / denominator if denominator > 0.0 else 0.0


def __Plate(shape: tp.Tuple[int, int], letters: tp.List[tp.Tuple[str, int, int, int, int]], np: tp.Any) -> tp.Any:
    """
    Description:
        Where a registered part's own plate is measured for a letter's contrast: the reference crop's middle
        (CONST_LOGO_PLATE_MARGIN cut from each edge: the plate's rim and the table beyond), every letter's box
        grown by CONST_LOGO_LETTER_MARGIN_PX left out.

    Args:
        (1) shape [Tuple<int> 1x2]: The reference crop's (height, width).
        (2) letters [Vector<Tuple>]: The reference's letters.
        (3) np [module]: The NumPy module.

    Returns:
        (1) parameter [Matrix<bool> hxw]: The plate's pixels.
    """

    height, width = shape
    plate = np.zeros((height, width), dtype=bool)
    margin = int(CONST_LOGO_PLATE_MARGIN * min(height, width))
    plate[margin:height - margin, margin:width - margin] = True
    grow = CONST_LOGO_LETTER_MARGIN_PX
    for _letter, x, y, w, h in letters:
        plate[max(0, y - grow):y + h + grow, max(0, x - grow):x + w + grow] = False
    return plate


def Prepare_Reference(crop_bgr: tp.Any, cv2: tp.Any, np: tp.Any) -> tp.Dict[str, tp.Any]:
    """
    Description:
        What a reference's turned crop is compared through, computed once per configuration: its size, its SIFT
        keypoints' positions and descriptors, and its edge image.

    Args:
        (1) crop_bgr [Matrix<uint8> hxwx3]: The reference's turned crop (Reference_Logo_Crop).
        (2) cv2 [module]: The OpenCV module.
        (3) np [module]: The NumPy module.

    Returns:
        (1) parameter [Dict]: {'size': (w, h), 'points', 'descriptors', 'edges'}.
    """

    gray = __Gray(crop_bgr, cv2)
    keypoints, descriptors = cv2.SIFT_create().detectAndCompute(gray, None)
    return {'size': (gray.shape[1], gray.shape[0]), 'points': np.float32([k.pt for k in keypoints]),
            'descriptors': descriptors, 'edges': __Edges(gray, cv2, np)}


def Check_Logo(crop_bgr: tp.Any, Catalogue_Logo_Str: Catalogue_Logo_Str, prepared: tp.List[tp.Dict[str, tp.Any]],
               cv2: tp.Any, np: tp.Any) -> Logo_Result_Str:
    """
    Description:
        The logo on a judged part's upright crop. It is registered to each reference (resized to its size, SIFT
        matches under Lowe's ratio, a similarity transform by RANSAC); a reference with Min_Matches inliers or more
        registers, and none registering means no inscription. Each letter is compared with that letter in every
        reference that registered, edge image against edge image in its box, and the best is kept: references of one
        variant lit from different sides make up for each other's dim letters, while an erased letter is unlike the
        letter in all of them. With the best the letter's contrast is also taken: its edges along the reference's
        strokes against the part's own plate (its middle, letters left out). A letter is there at
        Letter_Min_Similarity and Letter_Min_Contrast or more: the shape alone is blind to how faint it is
        (correlation is contrast-free), and an erased letter's seam has the letter's shape.

    Args:
        (1) crop_bgr [Matrix<uint8> hxwx3]: The part's upright crop.
        (2) Catalogue_Logo_Str [Catalogue_Logo_Str(object)]: The side's logo check.
        (3) prepared [Vector<Dict>]: Each reference prepared (Prepare_Reference), in the check's order.
        (4) cv2 [module]: The OpenCV module, injected by the caller.
        (5) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Logo_Result_Str(object)]: The reference with the most matches, its matches, and each letter.
    """

    logo = Catalogue_Logo_Str
    sift, matcher = cv2.SIFT_create(), cv2.BFMatcher()
    words = [word for word in logo.Expected_Text for _letter in word.replace(' ', '')]
    scores = [(-1.0, 0.0)] * len(words)
    best, warps = ('', 0), {}
    for reference, features in zip(logo.References, prepared):
        image = cv2.resize(crop_bgr, features['size'], interpolation=cv2.INTER_AREA)
        keypoints, descriptors = sift.detectAndCompute(__Gray(image, cv2), None)
        if descriptors is None or features['descriptors'] is None or len(keypoints) < 4:
            continue
        pairs = [pair for pair in matcher.knnMatch(descriptors, features['descriptors'], k=2) if len(pair) == 2]
        good = [first for first, second in pairs if first.distance < CONST_LOGO_MATCH_RATIO * second.distance]
        if len(good) < 4:
            continue
        source = np.float32([keypoints[m.queryIdx].pt for m in good])
        target = features['points'][[m.trainIdx for m in good]]
        warp, inliers = cv2.estimateAffinePartial2D(source, target, method=cv2.RANSAC,
                                                    ransacReprojThreshold=CONST_LOGO_RANSAC_PX)
        matches = int(inliers.sum()) if inliers is not None else 0
        if warp is None:
            continue
        if matches > best[1]:
            best = (reference.Name, matches)
        warps[reference.Name] = (reference, features['size'], warp)
        if matches < logo.Min_Matches:
            continue
        edges = __Edges(__Gray(cv2.warpAffine(image, warp, features['size']), cv2), cv2, np)
        plate = __Plate(edges.shape, reference.Letters, np)
        base = float(edges[plate].mean()) if plate.any() else 0.0
        for index, (_letter, x, y, w, h) in enumerate(reference.Letters):
            target_edges, window = features['edges'][y:y + h, x:x + w], edges[y:y + h, x:x + w]
            score = __Correlation(target_edges, window, np)
            if score > scores[index][0]:
                strokes = target_edges > CONST_LOGO_STROKE_FRACTION * float(target_edges.max())
                scores[index] = (score, float(window[strokes].mean()) / base if base > 0.0 else 0.0)
    if best[1] < logo.Min_Matches:
        return Logo_Result_Str(Reference='', Matches=best[1])
    letters = [Logo_Letter_Str(Word=word, Letter=letter, Similarity=score, Contrast=contrast,
                               Present=score >= logo.Letter_Min_Similarity and contrast >= logo.Letter_Min_Contrast)
               for word, letter, (score, contrast) in zip(words, ''.join(logo.Expected_Text).replace(' ', ''), scores)]
    return Logo_Result_Str(Reference=best[0], Matches=best[1], Letters=letters,
                           Words=__Word_Boxes(logo, *warps[best[0]], crop_bgr.shape, cv2, np))


def __Word_Boxes(logo: Catalogue_Logo_Str, reference: Catalogue_Logo_Reference_Str, size: tp.Tuple[int, int],
                 warp: tp.Any, shape: tp.Tuple[int, ...], cv2: tp.Any, np: tp.Any
                 ) -> tp.List[tp.Tuple[str, tp.List[tp.Tuple[float, float]]]]:
    """
    Description:
        Each expected word's box on the checked crop: the box around its letters in the reference, taken back
        through the registration (the crop resized to the reference's size, then warped onto it) to the crop's
        own pixels.

    Args:
        (1) logo [Catalogue_Logo_Str(object)]: The side's logo check.
        (2) reference [Catalogue_Logo_Reference_Str(object)]: The best-matched reference.
        (3) size [Tuple<int> 1x2]: The reference's (width, height).
        (4) warp [Matrix<float> 2x3]: The crop's registration onto it.
        (5) shape [Tuple<int>]: The crop's shape.
        (6) cv2 [module]: The OpenCV module.
        (7) np [module]: The NumPy module.

    Returns:
        (1) parameter [Vector<Tuple<string, Vector<Tuple<float> 1x2>>>]: (word, its four corners) in reading order.
    """

    back = cv2.invertAffineTransform(warp)
    scale_x, scale_y = shape[1] / float(size[0]), shape[0] / float(size[1])
    boxes, start = [], 0
    for word in logo.Expected_Text:
        letters = reference.Letters[start:start + len(word.replace(' ', ''))]
        start += len(letters)
        x0, y0 = min(b[1] for b in letters), min(b[2] for b in letters)
        x1, y1 = max(b[1] + b[3] for b in letters), max(b[2] + b[4] for b in letters)
        corners = cv2.transform(np.float32([[[x0, y0]], [[x1, y0]], [[x1, y1]], [[x0, y1]]]), back).reshape(-1, 2)
        boxes.append((word, [(float(x) * scale_x, float(y) * scale_y) for x, y in corners]))
    return boxes
