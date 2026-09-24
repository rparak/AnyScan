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
# File Name: ../Vision/Utilities/Caption.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — report composer (the label vocabulary lives there)
#   ../Reporting/Core
from Reporting.Core import (CONST_LABEL_LEADINS, CONST_LABEL_OPENERS, CONST_LABEL_BOUNDARIES,
                            CONST_LABEL_MAX_WORDS)

"""
Description:
    Initialization of constants.

    Florence-2 captioning: run one caption pass on a single crop (Describe) and
    distil a caption into a short noun-phrase label (Condense_Label).

    Note:
        Describe injects the model, processor and the runtime (cv2, np, torch,
        PILImage) rather than importing them, so this module — and App/run.py,
        which imports it at load time — does not pull the heavy runtime until an
        analysis actually runs. Condense_Label is pure text and needs none of it.
"""
# The Florence-2 task token sent per crop. <CAPTION> is the default: on a single
# cropped object it returns a concise 'A bolt on a green surface.' that distils
# cleanly to a noun-phrase label, and it is faster. <DETAILED_CAPTION> and
# <MORE_DETAILED_CAPTION> also work — the distiller handles their verbose 'In this
# image we can see a ...' template — but add no identification accuracy on a single
# crop. The token passed to generate() and to post_process_generation() must be
# identical — they are, both read from here.
CONST_VISION_TASK = '<MORE_DETAILED_CAPTION>'

# Generation. do_sample stays False so the same crop reads the same twice. One
# beam is the fast, deterministic default (shared with the detection pass).
CONST_VISION_NUM_BEAMS = 1
CONST_VISION_MAX_NEW_TOKENS = 256

# Crops smaller than this (shorter side, in pixels) are upscaled before the model,
# because tiny crops upscale poorly through the processor's own resize.
CONST_MIN_CROP_SIDE = 224


def Describe(model: tp.Any, processor: tp.Any, device: tp.Any, dtype: tp.Any,
             crop_bgr: tp.List[tp.List[float]], cv2: tp.Any, np: tp.Any, torch: tp.Any,
             pil_image: tp.Any, task: str = CONST_VISION_TASK) -> str:
    """
    Description:
        One Florence-2 caption pass on a single crop; returns the raw caption.

        The model, processor, device/dtype and the runtime modules are injected by
        the caller (which has already loaded them), so this module imports no heavy
        runtime of its own. The task defaults to the detailed object caption; the
        caller passes the concise <CAPTION> for the one-off background description.

    Args:
        (1) model [object]: The loaded Florence-2 model.
        (2) processor [object]: The matching AutoProcessor.
        (3) device [object]: The torch device the model is on.
        (4) dtype [object]: The torch dtype the model runs in.
        (5) crop_bgr [Matrix<uint8> hxwx3]: The cropped object (BGR).
        (6) cv2 [module]: The OpenCV module, injected.
        (7) np [module]: The NumPy module, injected.
        (8) torch [module]: The torch module, injected.
        (9) pil_image [module]: PIL.Image, injected.
        (10) task [string]: The Florence task token (default CONST_VISION_TASK).

    Returns:
        (1) parameter [string]: The model's raw caption for the crop.
    """

    pil = pil_image.fromarray(cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB))

    # Tiny crops upscale poorly through the processor's own resize; give it
    # something reasonable to work with.
    if min(pil.size) < CONST_MIN_CROP_SIDE:
        scale = CONST_MIN_CROP_SIDE / min(pil.size)
        pil = pil.resize((int(pil.width * scale), int(pil.height * scale)),
                         pil_image.LANCZOS)

    inputs = processor(text=task, images=pil, return_tensors='pt')
    inputs = {k: (v.to(device, dtype) if v.is_floating_point() else v.to(device))
              for k, v in inputs.items()}

    with torch.inference_mode():
        ids = model.generate(**inputs, max_new_tokens=CONST_VISION_MAX_NEW_TOKENS,
                             num_beams=CONST_VISION_NUM_BEAMS, do_sample=False)
    # skip_special_tokens=False: post_process_generation needs the location and
    # task tokens that True would strip, or structured output silently vanishes.
    raw = processor.batch_decode(ids, skip_special_tokens=False)[0]
    parsed = processor.post_process_generation(
        raw, task=task, image_size=pil.size)[task]

    if isinstance(parsed, str):
        return parsed.strip()
    if isinstance(parsed, dict):                   # OD-style tasks return a dict
        labels = parsed.get('labels') or []
        return labels[0] if labels else ''
    return str(parsed)


def Condense_Label(caption: str) -> str:
    """
    Description:
        A two-to-three word noun phrase for the label, distilled from a caption.

        Describe_Object renders the label as 'A <label>.', so a paragraph there
        produces a line that is not a sentence. The front matter and any trailing
        clause are stripped and the phrase is capped; the full caption survives
        untouched in Detection_Str.Detail as the line's second sentence, so an
        imperfect distillation loses nothing.

    Args:
        (1) caption [string]: The model's raw caption.

    Returns:
        (1) parameter [string]: The distilled label, or 'object' if nothing remains.
    """

    text = ' '.join(caption.split()).strip().rstrip('.')
    # Florence stacks lead-ins ('The image shows a close-up of a hex bolt'), and Gemma opens
    # 'The object is a …', so strip both repeatedly until the front is the noun phrase itself.
    stripped = True
    while stripped:
        stripped = False
        low = text.lower()
        for lead in CONST_LABEL_OPENERS + CONST_LABEL_LEADINS:
            if low.startswith(lead):
                text = text[len(lead):].lstrip(' ,')
                stripped = True
                break

    low = text.lower()
    cut = len(text)
    for boundary in CONST_LABEL_BOUNDARIES:
        idx = low.find(boundary)
        if idx != -1:
            cut = min(cut, idx)
    text = text[:cut].strip(' ,')

    for article in ('a ', 'an ', 'the '):
        if text.lower().startswith(article):
            text = text[len(article):]
            break

    words = text.split()[:CONST_LABEL_MAX_WORDS]
    text = ' '.join(words).strip(' ,.')
    return text.lower() if text else 'object'
