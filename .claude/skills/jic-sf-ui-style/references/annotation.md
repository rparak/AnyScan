# Image annotation

Source: `templates/JIC_SF_UI/Annotate.py` (Qt-free; OpenCV and NumPy are passed in) and `templates/annotate_demo.py`,
generalised from AnyScan's `src/Vision/Utilities/Annotate.py`. The reasoning is in AnyScan's design decisions *Every
chip carries a white numeral*, *A judged part's marks each carry their own check*, *A judged part's features are
marked on the frame*, *The label mask is black ground, tinted fill, verdict contour*, *Three states for the operator, a
Warning with its kind* and *A catalogue mode judges only inside the inspection area*.

## Principles

- **One renderer, Qt-free.** The window, a saved image and a headless harness all draw through the same functions, so
  what is validated is what is shown. The window shows the rendered image; it does not repaint marks in Qt.
- **The state's colour, unshifted, on any background.** Boxes, chips and mask outlines are drawn in
  `Theme.Verdict_Color(state)[0]` and never lightened, darkened or hue-rotated to gain contrast on a frame. No
  halo, casing, outline, rim or second colour is added around a mark, a chip or a numeral. The owner measured an
  outline and a numeral rim and ruled both out. No single colour reaches 3:1 on both a dark and a bright metal, so
  the marks read by hue.
- **Every weight scales with the image:** `scale = max(0.6, max(h, w) / 1000)` (`Annotate.Scale`), so a stroke tuned
  for a preview is not a hairline on a 1920 × 1200 export.

## Objects (`Draw_Object`)

| Case | Drawing |
|---|---|
| Plain object | A **solid** axis-aligned box, 2 px × scale, in its state's colour |
| Measured, non-symmetric object | Its **rotated outline SOLID** at the full weight (the measurement), inside the axis-aligned box **DASHED** at half weight (10 / 7 px dash/gap × scale): the reference that carries the chip |
| Judged part (OK/NOK) with its own checks | The dashed outer box and the chip carry the **verdict**; the solid rotated outline carries **only the size check** (the orange-red only when out of tolerance, otherwise the purple), so the frame says which check failed |
| Warning (every kind) | Outline, dashed outer box and chip all in the amber; **no feature marks** |
| Detect-only mode (no verdict) | Every object in `CONST_DETECTION_BOX` (the purple); nothing reads as a pass |

**The chip** is the object's 1-based number, a small tab **filled with its box's colour**, with the numeral in **plain
white** (`CONST_CHIP_NUMERAL`) in every state and mode. It uses OpenCV `FONT_HERSHEY_SIMPLEX`, with the font scale
`0.5 × scale` clamped to 0.6–1.1 so the tab stays small, and padding 6 × the font scale. Its bottom sits on the box's
top edge at the **top-left corner**; when the box is too near the image's top, it flips inside the box. White on the
orange-red is 2.92:1 and on the amber 1.62:1: these are the owner's accepted exceptions for short bold numerals.

## Features (`Draw_Feature`): holes, stains, any checked detail

- **Only for a judged part (OK or NOK).** A Warning shows no feature marks, though its features stay in the record.
- Each feature is a **box along the part's axes**, so it turns with the part, tight round its outline (a found hole's
  contour, a missing hole's expected circle), at **half the object's weight** (1 px × scale).
- **Its own check's colour**: the purple if it passed, the orange-red if it failed. A stain and a missing hole are
  always the orange-red.
- **Solid when found; DASHED (4 px × scale) when expected and not found.** These are the only dashed feature marks,
  so a missing hole never reads as a hole found out of tolerance. A closed path is dashed as one line round its
  vertices (`Draw_Dashed_Path`), so a many-sided circle reads dashed.
- **A stain's pixels** are tinted with the fail colour at 35 % (`Tint_Regions`), so its shape shows.
- **The feature chip** is the object's number and the feature's (`2.3`, matching the log's part numbering), at 0.6 of
  the object chip's font (never below 0.4), filled with the feature's colour, with a white numeral. It is **placed by
  the nearest-corner rule**:
  1. on the feature box's **corner nearest the object's chip** (the object box's top-left); corners within 3 px × scale
     count as equally near, and the **higher** one is taken, so the chip does not jump between frames;
  2. along that corner's edge **closer to horizontal**; edges within 5° count as equal, and the one running **to the
     right** is taken (if both run right, the rising one);
  3. **outside** the box, **turned with the edge**, its numeral reading left to right;
  4. if it would come within 2 px × scale of an earlier chip of the same object, it **slides along its edge** away
     from the corner, a pixel at a time, until it does not. It may lie over a neighbouring feature's outline.
- Whether to show feature chips is the project's choice. AnyScan has, at different times, shown and hidden them; the
  boxes and colours carry the check either way.

## Inspection area

The inspection area is drawn on screen only (`Widgets.Paint_Inspection_Area`), never into a saved image. It is 1 px,
solid, square-cornered, unfilled and on whole pixels: the light amber `#FFD880` over a camera image (told apart from a
Warning by its 1 px against a frame's 2 px) and the purple over the empty grey-lilac view. Only an object wholly
inside it is judged; one reaching outside is a Warning of kind *Outside area*, whose reason names the action.

## Label mask (a diagnostic image)

A **black** ground, each object's own pixels filled with its state's **tint** (`Fill_Mask`): OK `#CC9EF1`, NOK
`#CD7157`, Warning `#B28508`. Each fill keeps its box's hue within 5° at ≥ 40 % of its chroma, is ≥ 4.5:1 on black,
ΔE ≥ 25 from its box and ≥ 21 from white. The **same boxes and chips** go on top in the same places and colours, so
the mask view is the annotated view with the image replaced by the segmentation. A test holds these relationships;
a comment alone does not.

## Colour rules, summarised

- The state's box colour comes from `Verdict_Color`; never write a colour literal at a call site.
- Purple means pass or OK, orange-red fail or NOK, amber Warning. Green never marks an object. The log's error red
  never marks an object either: it is a software fault, not a faulty part.
- A Warning's kind is told in words (`wording.md`), never in a colour. If an operator ever needs it at a glance,
  add a letter on the chip, never a colour.
- A heatmap or similarity overlay uses a perceptual map with no green, red or magenta (AnyScan uses cividis), kept
  ΔE ≥ 12 from every state, status and log colour. It is diagnostic and decides nothing.
