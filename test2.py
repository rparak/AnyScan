"""
test2.py
========

Object detection + natural-language description pipeline for the
parts-on-green-background images.

Compared with ``test.py`` this script adds two things the previous version did
not have, and drops the hand-crafted ``material_phrase`` heuristic entirely:

  1. **Background-subtracted segmentation.** ``Image_Background_001.png`` is a
     photo of the empty green table (no parts on it). The absolute difference
     between each input image and this background gives a clean, illumination
     robust foreground mask that is fused with the FastSAM part-masks. This
     makes the object separation far more reliable than the border/area
     heuristics alone (it no longer depends on FastSAM correctly guessing which
     mask is "the table").

  2. **Histogram-clipping image enhancement.** Each detected object is cropped
     and its contrast/brightness are stretched with
     ``Get_Alpha_Beta_Parameters`` (a robust min/max histogram clip) before it
     is handed to Florence-2. The stretched crop exposes surface detail, edges
     and true colour, so Florence-2 produces a noticeably better grounded
     description of the object instead of guessing about a washed-out blob.

For every input image the script:

  1. Detects one mask per physical object (FastSAM âˆª background subtraction).
  2. Enhances each object crop with the alpha/beta histogram clip.
  3. Runs Florence-2 ``<MORE_DETAILED_CAPTION>`` on the enhanced crop.
  4. Saves the annotated image to ``results/Image_XXX_detected.png``.
  5. Saves the enhanced-crops montage to ``results/Image_XXX_enhanced.png``.
  6. Writes one description per object to
     ``results/Image_XXX_descriptions.txt`` followed by a single global line
     describing the (green) background of the scene::

         Obj. 1 - <detailed description, no background mention>
         Obj. 2 - <detailed description, no background mention>
         ...
         Background - <one global description of the empty table>

     Each object caption has any background/table sentence removed; the
     background is instead described once, globally, on the last line.
"""

from pathlib import Path
import re
import typing as tp

import cv2
import numpy as np
import torch
from PIL import Image
from ultralytics import FastSAM
from transformers import AutoModelForImageTextToText, AutoProcessor

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
MODEL_PATH = "FastSAM-x.pt"          # largest / most accurate FastSAM weights
# Local Florence-2 weights. The first existing candidate is used, so the same
# script works whether the model lives next to this file or one level up.
FLORENCE_CANDIDATES = ["florence2-large-ft", "../florence2-large-ft"]
FLORENCE_TASK = "<MORE_DETAILED_CAPTION>"   # richest description prompt

IMAGES = [f"Image_{i:03d}.png" for i in range(1, 8)]
BACKGROUND_PATH = "Image_Background_001.png"   # empty table (no parts)
OUT_DIR = Path("results")

# ---- Model inference parameters (tuned for precision) --------------------- #
IMGSZ = 1024          # higher inference resolution -> tighter, more precise masks
CONF = 0.40           # keep confident part-masks (high recall on real parts)
IOU = 0.90            # high NMS IoU: keep overlapping part-masks (we merge later)
RETINA_MASKS = True   # full-resolution masks instead of down-sampled prototypes
MAX_DET = 300         # allow many part-masks before consolidation

# ---- Post-processing parameters ------------------------------------------- #
BG_AREA_FRAC = 0.50   # a mask covering more than this fraction ...
BG_BORDERS = 3        # ... and touching at least this many image borders = background
HARD_BG_FRAC = 0.85   # any mask this large is background regardless of borders
CLOSE_KERNEL = 15     # morphological closing to merge parts of the same object
MIN_AREA_FRAC = 5e-4  # drop components smaller than this fraction of the image

# ---- Background-subtraction parameters ------------------------------------ #
# Foreground = |image - empty_table_background|.  A blur removes sensor noise,
# an Otsu threshold (floored so faint shadows are ignored) marks object pixels,
# and an opening removes the thin shadow halo around each part.
BG_BLUR = 5           # Gaussian blur kernel applied to the difference image
BG_DIFF_FLOOR = 28    # min grayscale difference to count as foreground
BG_OPEN_KERNEL = 5    # opening kernel to erase shadow halo / speckle
BG_DILATE = 3         # small dilation so object edges are not clipped

# ---- Florence-2 description parameters ------------------------------------ #
CROP_PAD = 12         # padding (px) around each object crop for extra context
MAX_NEW_TOKENS = 256  # description length cap
NUM_BEAMS = 3         # beam search for higher quality captions

# ---- Image-enhancement parameters ----------------------------------------- #
CLIP_LIMIT = 1.0     # histogram clip in percent for the alpha/beta stretch

# Florence-2 occasionally reads the concentric machining marks on the metal
# plates as "wood"/"cardboard"; these parts are always machined metal/plastic,
# so we neutralise those impossible substance guesses in the final caption.
WOOD_WORDS = re.compile(r"\b(wood|woods|wooden|cardboard|paper)\b", re.IGNORECASE)

# The (green) table is described once, globally, as the last line of every
# ``*.txt``. Individual object captions therefore have any background/table
# sentence removed so each object is described on its own. A sentence is treated
# as "about the background" when it mentions one of these words.
BG_WORDS = re.compile(
    r"\b(background|backdrop|surface|table|tablecloth|green|greenish|"
    r"turquoise|teal)\b", re.IGNORECASE)
# Prompt used for the one-off background description.
BG_CROP_MARGIN = 0.12   # centre-crop the reference to skip the dark vignette


# --------------------------------------------------------------------------- #
# Image enhancement (histogram clipping -> contrast/brightness)
# --------------------------------------------------------------------------- #
def Get_Alpha_Beta_Parameters(image: tp.List[tp.List[int]],
                              clip_limit: float) -> tp.Tuple[float, float]:
    """
    Description:
        Function to adjust the contrast and brightness parameters of the input image by clipping the histogram.

        The main core of the function is to obtain the alpha and beta parameters
        to determine the equation:
            g(i, j) = alpha * f(i, j) + beta,

            where g(i, j) are the input (source) pixels of the image, f(i, j) are the output pixels
            of the image, and alpha, beta are the contrast and brightness parameters.

    Args:
        (1) image [Vector<float> Image Shape {Resolution<x, y>}]: Input raw image.
        (2) clip_limit [float]: Parameter for histogram clipping in percentage.

    Returns:
        (1) parameter [float]: A gain (contrast) parameter called alpha.
        (2) parameter [float]: A bias (brightness) parameter called beta.
    """

    image_copy = image.copy()

    # Calculate the grayscale histogram of the image.
    image_hist = cv2.calcHist([image_copy], [0], None, [256], [0, 256])

    # Get the cumulative sum of the elements (histogram).
    c_hist = np.cumsum(image_hist)

    # Modify the percentage to clip the histogram.
    c_hist_max = c_hist[-1]
    clip_limit_mod = clip_limit * (c_hist_max / float(100.0 * 2.0))

    # Clip the histogram if the values are outside the limit.
    min_value = 0; max_value = c_hist.size - 1
    for _, c_hist_i in enumerate(c_hist):
        if c_hist_i < clip_limit_mod:
            min_value += 1

        if c_hist_i >= (c_hist_max - clip_limit_mod):
            max_value -= 1

    # Guard against a degenerate (flat) histogram.
    if max_value <= min_value:
        return 1.0, 0.0

    # Express the alpha and beta parameters.
    #   Gain (contrast) parameter.
    alpha = 255 / (max_value - min_value)
    #   Bias (brightness) parameter.
    beta = (-1) * (min_value * alpha)

    return (alpha, beta)


def enhance_bgr(image_bgr: np.ndarray,
                mask: tp.Optional[np.ndarray] = None,
                clip_limit: float = CLIP_LIMIT) -> np.ndarray:
    """Contrast/brightness-stretch a BGR image via the alpha/beta histogram clip.

    The gain/bias are estimated with ``Get_Alpha_Beta_Parameters`` and then
    applied to every colour channel with ``g = alpha * f + beta``.

    If ``mask`` is given, only the object pixels feed the histogram, so the
    uniform green table around the part does not bias the stretch. The stretch
    itself is still applied to the *whole* crop, so the object keeps its natural
    green surroundings for Florence-2 -- only the alpha/beta estimate changes.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    if mask is not None and int(mask.sum()) > 0:
        sample = gray[mask > 0].reshape(-1, 1)   # object pixels only
    else:
        sample = gray
    alpha, beta = Get_Alpha_Beta_Parameters(sample, clip_limit)
    return cv2.convertScaleAbs(image_bgr, alpha=alpha, beta=beta)


# --------------------------------------------------------------------------- #
# FastSAM detection + background subtraction
# --------------------------------------------------------------------------- #
def load_detector() -> FastSAM:
    model = FastSAM(MODEL_PATH)
    model.info()
    return model


def load_background(h: int, w: int) -> tp.Optional[np.ndarray]:
    """Load the empty-table background, resized to the working resolution."""
    if not Path(BACKGROUND_PATH).exists():
        print(f"[warn] background '{BACKGROUND_PATH}' not found -> "
              f"segmentation falls back to FastSAM only")
        return None
    bg = cv2.imread(BACKGROUND_PATH)
    if bg is None:
        return None
    if bg.shape[:2] != (h, w):
        bg = cv2.resize(bg, (w, h), interpolation=cv2.INTER_AREA)
    return bg


def background_foreground(image_bgr: np.ndarray,
                          background_bgr: np.ndarray) -> np.ndarray:
    """Binary foreground mask from |image - empty_table_background|.

    Returns a uint8 {0,1} mask where 1 = pixel differs from the empty table
    (i.e. belongs to an object / its shadow-free silhouette).
    """
    diff = cv2.absdiff(image_bgr, background_bgr)
    diff = cv2.GaussianBlur(diff, (BG_BLUR, BG_BLUR), 0)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

    # Otsu picks the split automatically; the floor keeps faint shadows out.
    otsu, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thresh = max(float(otsu), float(BG_DIFF_FLOOR))
    fg = (gray >= thresh).astype(np.uint8)

    # Remove the thin shadow halo / speckle, then grow slightly to recover edges.
    open_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (BG_OPEN_KERNEL, BG_OPEN_KERNEL))
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, open_k)
    if BG_DILATE > 0:
        dil_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (BG_DILATE, BG_DILATE))
        fg = cv2.dilate(fg, dil_k)
    return fg


def touches_borders(mask: np.ndarray) -> int:
    """Number of image borders the mask touches (0..4)."""
    return int(mask[0, :].any()) + int(mask[-1, :].any()) \
        + int(mask[:, 0].any()) + int(mask[:, -1].any())


def foreground_union(masks: np.ndarray, h: int, w: int) -> np.ndarray:
    """Union of all object masks, excluding background-like masks."""
    union = np.zeros((h, w), np.uint8)
    for m in masks:
        frac = float(m.mean())
        if frac >= HARD_BG_FRAC:
            continue
        if frac >= BG_AREA_FRAC and touches_borders(m) >= BG_BORDERS:
            continue
        union |= m
    return union


def detect_objects(model: FastSAM, image_path: str,
                   background_bgr: tp.Optional[np.ndarray]):
    """Return (image_bgr, list_of_component_indices, (labels, stats), raw_n).

    The foreground used for connected-component splitting is the union of the
    FastSAM part-masks and the background-subtracted mask, so an object is kept
    if *either* cue sees it.
    """
    result = model(
        image_path,
        imgsz=IMGSZ,
        retina_masks=RETINA_MASKS,
        conf=CONF,
        iou=IOU,
        max_det=MAX_DET,
        verbose=False,
    )[0]

    image = result.orig_img.copy()
    h, w = result.orig_shape

    # FastSAM foreground (may be empty if nothing was segmented).
    if result.masks is not None:
        masks = result.masks.data.cpu().numpy().astype(np.uint8)  # (N, H, W)
        raw_n = masks.shape[0]
        sam_fg = foreground_union(masks, h, w)
    else:
        raw_n = 0
        sam_fg = np.zeros((h, w), np.uint8)

    # Background-subtraction foreground (independent of FastSAM).
    if background_bgr is not None:
        bg_fg = background_foreground(image, background_bgr)
    else:
        bg_fg = np.zeros((h, w), np.uint8)

    union = (sam_fg | bg_fg).astype(np.uint8)
    if union.max() == 0:
        return image, [], None, raw_n

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (CLOSE_KERNEL, CLOSE_KERNEL))
    closed = cv2.morphologyEx(union * 255, cv2.MORPH_CLOSE, kernel)

    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(closed, connectivity=8)
    min_area = MIN_AREA_FRAC * h * w
    objects = [i for i in range(1, n_labels)
               if stats[i, cv2.CC_STAT_AREA] >= min_area]

    # Order objects left-to-right, top-to-bottom for stable numbering.
    objects.sort(key=lambda i: (stats[i, cv2.CC_STAT_TOP] // 100,
                                stats[i, cv2.CC_STAT_LEFT]))

    return image, objects, (labels, stats), raw_n


def annotate(image, objects, labels, stats):
    """Draw a filled translucent mask, contour and box + index per object."""
    overlay = image.copy()
    rng = np.random.default_rng(0)
    for idx, comp in enumerate(objects, start=1):
        color = tuple(int(c) for c in rng.integers(60, 255, size=3))
        comp_mask = (labels == comp).astype(np.uint8)

        overlay[comp_mask.astype(bool)] = color
        contours, _ = cv2.findContours(comp_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(image, contours, -1, color, 3)

        x, y, w, h, _ = stats[comp]
        cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
        cv2.putText(image, f"{idx}", (x, max(0, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3, cv2.LINE_AA)

    return cv2.addWeighted(overlay, 0.4, image, 0.6, 0)


# --------------------------------------------------------------------------- #
# Florence-2 description
# --------------------------------------------------------------------------- #
def resolve_florence_dir() -> str:
    for candidate in FLORENCE_CANDIDATES:
        if Path(candidate).is_dir():
            return candidate
    raise FileNotFoundError(
        f"Florence-2 model not found in any of: {FLORENCE_CANDIDATES}")


def load_florence():
    """Load the local Florence-2 model + processor onto the best device."""
    model_dir = resolve_florence_dir()
    device = "mps" if torch.backends.mps.is_available() else \
             ("cuda" if torch.cuda.is_available() else "cpu")
    processor = AutoProcessor.from_pretrained(model_dir)
    model = AutoModelForImageTextToText.from_pretrained(
        model_dir, dtype=torch.float32).to(device).eval()
    print(f"Florence-2 loaded from '{model_dir}' on {device}")
    return model, processor, device


def describe_crop(model, processor, device, pil_crop: Image.Image) -> str:
    """Run Florence-2 on one object crop and return a cleaned description."""
    inputs = processor(text=FLORENCE_TASK, images=pil_crop,
                       return_tensors="pt").to(device)
    with torch.no_grad():
        generated = model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=MAX_NEW_TOKENS,
            num_beams=NUM_BEAMS,
            do_sample=False,
        )
    decoded = processor.batch_decode(generated, skip_special_tokens=False)[0]
    parsed = processor.post_process_generation(
        decoded, task=FLORENCE_TASK, image_size=pil_crop.size)
    text = parsed.get(FLORENCE_TASK, "").strip()
    return " ".join(text.split())  # collapse whitespace / newlines


def crop_box(stats, comp, H: int, W: int) -> tp.Tuple[int, int, int, int]:
    """Padded (x0, y0, x1, y1) bounding box around one object.

    The crop keeps the object's natural (green-table) surroundings: Florence-2
    grounds its description more accurately when the object is shown in context
    rather than cut out onto a blank canvas. The box is also used to slice the
    object mask so the alpha/beta stretch can be estimated from object pixels.
    """
    x, y, w, h, _ = stats[comp]
    x0, y0 = max(0, x - CROP_PAD), max(0, y - CROP_PAD)
    x1, y1 = min(W, x + w + CROP_PAD), min(H, y + h + CROP_PAD)
    return x0, y0, x1, y1


def clean_caption(text: str) -> str:
    """Replace Florence-2's impossible substance guesses (wood, cardboard...)."""
    return WOOD_WORDS.sub("metal", text)


def strip_background(text: str) -> str:
    """Drop sentences that talk about the background/table from an object caption.

    The background is described once, globally (see ``describe_background``), so
    every per-object caption is stripped of any sentence mentioning the table /
    green surface. This keeps each object description about the object itself.
    If every sentence mentions the background (nothing else is left) the original
    caption is returned unchanged so the object is not left without a description.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    kept = [s for s in sentences if s and not BG_WORDS.search(s)]
    cleaned = " ".join(kept).strip()
    return cleaned if cleaned else text.strip()


def describe_background(model, processor, device) -> str:
    """Run Florence-2 once on the empty-table reference to describe the scene.

    The reference is centre-cropped first so the dark vignette at the frame edge
    does not leak into the description of the (green) table itself.
    """
    if not Path(BACKGROUND_PATH).exists():
        return ""
    bg = cv2.imread(BACKGROUND_PATH)
    if bg is None:
        return ""
    h, w = bg.shape[:2]
    m = BG_CROP_MARGIN
    bg = bg[int(h * m):int(h * (1 - m)), int(w * m):int(w * (1 - m))]
    pil = Image.fromarray(cv2.cvtColor(bg, cv2.COLOR_BGR2RGB))
    return clean_caption(describe_crop(model, processor, device, pil))


def montage(crops: tp.List[np.ndarray], cols: int = 3) -> tp.Optional[np.ndarray]:
    """Tile the enhanced object crops into a single inspection image."""
    if not crops:
        return None
    cell = 260
    tiles = []
    for c in crops:
        h, w = c.shape[:2]
        s = min(cell / w, cell / h)
        r = cv2.resize(c, (max(1, int(w * s)), max(1, int(h * s))))
        canvas = np.full((cell, cell, 3), 40, np.uint8)
        yh, xw = r.shape[:2]
        y0, x0 = (cell - yh) // 2, (cell - xw) // 2
        canvas[y0:y0 + yh, x0:x0 + xw] = r
        tiles.append(canvas)
    rows = []
    for i in range(0, len(tiles), cols):
        row = tiles[i:i + cols]
        while len(row) < cols:
            row.append(np.full((cell, cell, 3), 40, np.uint8))
        rows.append(np.hstack(row))
    return np.vstack(rows)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    OUT_DIR.mkdir(exist_ok=True)
    detector = load_detector()
    flo_model, flo_processor, device = load_florence()

    background = None  # loaded lazily once we know the image resolution

    # Describe the (green) table once; it is appended as the final, global line
    # of every descriptions file and stripped from the individual object captions.
    background_caption = describe_background(flo_model, flo_processor, device)
    if background_caption:
        print(f"[background] {background_caption}\n")

    total = 0
    for image_path in IMAGES:
        if not Path(image_path).exists():
            print(f"[skip] {image_path} not found")
            continue

        if background is None:
            probe = cv2.imread(image_path)
            background = load_background(probe.shape[0], probe.shape[1])

        image, objects, extra, raw_n = detect_objects(detector, image_path, background)
        n = len(objects)
        total += n
        stem = Path(image_path).stem

        # Save annotated image.
        if extra is not None:
            labels, stats = extra
            annotated = annotate(image.copy(), objects, labels, stats)
        else:
            labels = stats = None
            annotated = image
        cv2.imwrite(str(OUT_DIR / f"{stem}_detected.png"), annotated)

        # Enhance each object crop (natural background kept for Florence-2, but
        # alpha/beta estimated from the object's own pixels), describe it.
        H, W = image.shape[:2]
        txt_path = OUT_DIR / f"{stem}_descriptions.txt"
        lines, enhanced_crops = [], []
        for idx, comp in enumerate(objects, start=1):
            x0, y0, x1, y1 = crop_box(stats, comp, H, W)
            crop_bgr = image[y0:y1, x0:x1]
            obj_mask = (labels == comp).astype(np.uint8)[y0:y1, x0:x1]
            enhanced = enhance_bgr(crop_bgr, obj_mask, CLIP_LIMIT)
            enhanced_crops.append(enhanced)

            pil_crop = Image.fromarray(cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB))
            caption = strip_background(clean_caption(
                describe_crop(flo_model, flo_processor, device, pil_crop)))
            line = f"Obj. {idx} - {caption}"
            lines.append(line)
            print(f"[{image_path}] {line}")

        # Save the enhanced-crops montage for visual inspection.
        grid = montage(enhanced_crops)
        if grid is not None:
            cv2.imwrite(str(OUT_DIR / f"{stem}_enhanced.png"), grid)

        # Append the single, global background description as the last line.
        if background_caption:
            bg_line = f"Background - {background_caption}"
            lines.append(bg_line)
            print(f"[{image_path}] {bg_line}")

        txt_path.write_text("\n".join(lines) + ("\n" if lines else ""))
        print(f"{image_path}: {n} object(s) (raw masks: {raw_n}) -> {txt_path}\n")

    print(f"Total objects described across {len(IMAGES)} images: {total}")


if __name__ == "__main__":
    main()
