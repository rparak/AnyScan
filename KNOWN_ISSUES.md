# Known issues

Open behaviours of the pipeline that show up in its text or its numbers, recorded so they are
recognised when they appear. Nobody decides anything on them. **The two limitations that do affect
decisions — sizes are repeatable, not absolute; the describer is not a defect detector — are in the
README, under [Limitations](README.md#limitations).**

Each entry states the behaviour, what it affects, and why it is not fixed. An entry is removed when
the behaviour is fixed, and the resolution is recorded in `docs/design-decisions.md`.

## `Basler_Cls` connection code raises and catches bare `Exception`

`Camera/Basler.py`'s connection code raises and catches bare `Exception` — e.g.
`raise Exception('[ERROR] No Basler cameras detected...')` and `except Exception`
in `__Connect`, `Capture`, `__Set_Optional`, `__Close`. This is the inherited
driver's style, not this codebase's (a `*_Error_Cls` whose message is an operator
sentence), and a bare `except Exception` can mask an unexpected error as a routine one.

- **Impact:** low in practice. The facade `Basler_Camera_Cls._Open`/`_Grab` catches
  whatever `Basler_Cls` raises and re-wraps it into a `Camera_Error_Cls` with an
  actionable sentence, so the operator never sees a bare traceback. The roughness
  is internal to the driver. One path is already narrowed: a setting the camera refuses or
  does not keep (the sensor window) raises `Basler_Settings_Error_Cls`, reported as it stands
  rather than as "no camera", and a failed configure closes the device before raising
  (docs/design-decisions.md, *The configuration sets the camera's sensor window*).
- **Not fixed here:** the style pass gave `Basler_Cls` types, docstrings and
  `CONST_*` naming but deliberately did not restructure the connection's control flow —
  rewriting it changes behaviour on a hardware path with little automated coverage. Narrow
  the remaining `except Exception` clauses in `__Connect`, `Capture`, `__Set_Optional` and
  `__Close` together with a real camera run.

## The fusion's parameters are validated on seven real frames only

This entry used to describe a coverage gate and a mask dilation (`CONST_FILTER_CHANGE_COVERAGE`,
`CONST_SEG_MASK_DILATE_KERNEL`) tuned on synthetic scenes. **Neither exists any more.** The gate
was replaced by fusion: an object survives on *either* cue, FastSAM or background subtraction, so no
coverage threshold decides whether a FastSAM mask counts (docs/design-decisions.md, *The fusion
needs both cues*).

What decides detection now is set in the configuration:

- `Segmentation.Background.*` — the background difference: the Otsu floor, and the opening and
  dilation kernels.
- `Segmentation.Fusion.*` — the closing kernel, the minimum component area, and the
  background-rejection fractions and border count.

Two constants in `Vision/Utilities/Fusion.py` also remain: the 0.10 cue-attribution overlap, which
only labels which cue found an object, and the row band / object cap, which order and limit the
objects.

Unlike the old gate, these have run on real captures: the seven `Data/Images/Test` frames, with object
counts pinned by tests (`Image_001` → nine objects, `Image_004` → one plate with its soft shadow
rejected). But seven frames of one table, under one light, with mostly isolated parts, is a narrow
base.

- **Not yet seen on real data:** parts close to the table's colour or dark and featureless, parts
  that touch, and any other lighting.
- **The failure signatures to watch:**
  - a real part missing from the count (a cue failed and the other did not carry it)
  - one part split into two components (the closing kernel too small for its gaps)
  - two neighbours merged into one (the closing kernel too large, or they touch)
  - a part's outline running into its shadow (see the harsh-shadow entry below)
- **Until more real frames are analysed,** the parameters are trusted on these seven frames only.
  When a failure signature appears, change the parameter in the configuration, not in code.

## The label mask reveals near-but-distinct objects, not merged touching ones

The exported label mask (`Vision.Utilities.Annotate.Draw_Label_Mask`) fills each
object with a light tint of its box colour and outlines it in that box colour from
that object's **own** component mask. Two parts that
sit close together but do not touch are separate components, so they render as
two tinted shapes with two outlines and black ground between them — the mask reads
as two objects. Two parts that **touch**, however, are already a single component
by the time they reach the renderer: `Vision.Utilities.Fusion.Fuse_Objects`
closes and connected-components the fused cues *before* anything is drawn, so a
merge collapses into one blob upstream. The mask draws one shape with one
contour and cannot reveal that it was two parts — the merge is not a rendering
question.

- **Impact:** a genuine merge (two touching parts read as one object) is invisible
  in the default mask; the per-object contour only distinguishes objects that were
  already separate components.
- **Detection route:** the object **count** against expectation is now the only route
  (a merge lowers the count by one; the status bar's OBJECTS DETECTED and the Trends
  chart both show it). The per-object diagnostic mask fill that used to reveal a merge
  in the mask itself (`CONST_ANNOTATE_MASK_FILL = 'index'`, filling each object in its
  own colour) was removed — its only consumer was that diagnostic, and it carried a
  whole coordinated-stroke palette with it, so the count against expectation stands
  alone.
- **Pinned by:** `test/Vision/Utilities/test_annotate.py::test_mask_separates_near_but_distinct_objects`.

## Open question: FastSAM's reliability on low-contrast shapes

FastSAM dropped low-contrast objects **twice** during development, in independent
synthetic scenes:

- In a synthetic comparison, it returned **no mask for a flat mid-grey box** (BGR ~105)
  on the green reference.
- While building the `analyze.py` synthetic scene, `'everything'` mode **dropped a
  near-black plate** (BGR ~25) it had segmented cleanly in a different layout — the
  stage-1 change mask found all four regions, but FastSAM returned a mask for only
  three.

So this is not a one-off grey quirk but a **low-contrast reliability question in
general**: objects whose colour sits close to the surface, or which are dark and
featureless, are the ones FastSAM everything-mode is least dependable on, and its
output is not fully deterministic across scenes. It is recorded as an **open
question, not a confirmed limitation** — a flat synthetic fill is a plausible
worst case (no internal texture or edges to latch onto), and real metal parts
carry specular highlights and surface texture FastSAM may segment well.

- **Why it matters here:** grey / metallic and dark parts are exactly what this
  application inspects, so the answer cannot be assumed either way.
- **What would answer it:** real low-contrast parts (grey/metallic and dark) on the
  reference background, analysed with `Example/Vision/analyze.py`, checking that each
  comes back as an object. Fusion carries a part FastSAM misses if the background
  difference sees it, so the risk is highest for parts close to the table's colour. If
  real parts are missed, lower the segmenter confidence (`Segmentation.Confidence`) or
  revisit the segmenter choice.

## A very harsh cast shadow can be absorbed into a part's component

The over-segmentation this entry used to describe — a cast shadow's boundary
surviving stage 3 as an extra sliver, so N parts reported as more than N — was a
property of the old coverage-gate + mask-NMS filter. The fusion pipeline replaced
that filter (see git history: the FastSAM-∪-background-subtraction port), and on
**real captures the defect is gone**: `Image_004`'s soft cast shadow is stripped
by the background-subtraction opening (`Segmentation.Background.Open_Kernel` in the configuration) and the
plate comes back as a single, tight silhouette (rectangularity ~0.88, no shadow
tail). Measured across all seven `Data/Images/Test` frames, the counts are exactly the
inventory (15 objects, no over-count).

What remains is the **opposite, narrower** failure, and only off real data: when a
shadow is far darker and larger than any real capture — a 40%-darkening ellipse too
big for the opening to erase — its absdiff clears the Otsu floor (`Segmentation.Background.Otsu_Floor`), and the
fusion **absorbs** it into the object's component rather than rejecting it, so the
mask extends past the part into the shadow band. This does not over-count (it stays
one object), but the silhouette is no longer tight, and the enhanced crop fed to the
describer would then contain a strip of table.

- **Fixed case, pinned by:** `test/integration/test_pipeline.py::test_shadow_rejected_on_real_capture`
  (slow; `Image_004` → one object, rectangularity ≥ 0.80 — the real-capture case that now passes).
- **Open case, pinned by:** `test/integration/test_pipeline.py::test_synthetic_harsh_shadow_not_absorbed_xfail`
  (slow; `xfail(strict=True)`. It asserts the desired behaviour — no object reaches into
  the shadow band — which currently fails. When the pipeline stops absorbing the harsh
  shadow the test XPASSes and the suite fails: the signal to promote it to a plain pass
  and delete this entry.)
- **Not fixed here:** rejecting a shadow this harsh is a threshold problem, and the
  background-subtraction thresholds are set against real captures, not a synthetic
  scene darker than any real one. Tuning them against this scene would just move the
  failure. Only a real harsh shadow, analysed against a reference shot under the same light,
  would say whether it happens on real data.

## The confidence status metric is partial — only the FastSAM cue is scored

The status strip's `Confidence (run mean)` averages `Detection_Str.Segmenter_Score`,
which only the FastSAM cue supplies. An object found by background subtraction
alone (`Cue == 'background'`) carries `Segmenter_Score is None` and no confidence
of its own. The run mean is therefore over **exactly** the scored objects, never
averaging over the partial set silently, and reads `—` when no object has a score; the
frame's own confidence shows the coverage (e.g. `87% over 5 of 9`).

The limitation stands; its example is stale. When it was written, four of `Image_001`'s
nine objects were background-only. Re-measured 2026-09-25 with the current pipeline, no
object in the seven repository frames is: `Image_001` is 4 `both` + 5 `fastsam`, and the
other six frames' single objects are `both`. So the repository frames score fully (run
mean 93–95%) and do not exercise this path; a rig frame with a part FastSAM misses would.

- **Why not route every object through FastSAM:** the fusion exists because neither
  cue is sufficient, and a single run proved it in both directions (the run this entry
  was written from; see design-decisions, *The fusion needs both cues*) — objects the
  background cue missed were carried by FastSAM (`cov=0.00`), and the `Cue ==
  'background'` objects had no FastSAM mask at all. Forcing them through means
  either lowering thresholds until FastSAM sees them (which admits false
  detections) or a second region-prompted pass (which roughly doubles time on the
  slowest stage). Either changes *detection* behaviour to populate a *status*
  field — not worth it.
- **Honest fix later (do not build now):** give the background-subtraction cue its
  own confidence — a normalised change magnitude or a mask-edge sharpness — so every
  object carries a score from whichever cue found it, and the mean covers the whole
  set. Until then the coverage fraction is the honest disclosure that it does not.
- **Pinned by:** `test/UI/test_status_metrics.py::test_status_confidence_is_the_session_mean_over_scored_objects`,
  `::test_status_confidence_denominator_is_the_scored_count_not_the_total`,
  `::test_status_confidence_is_no_value_when_no_object_has_a_score` and
  `::test_frame_confidence_shows_coverage_when_partial_and_dash_when_none`.

## Gemma reads some through-holes as "a central green element"

On the `Image_002` plate, whose two through-holes have dark rims, Gemma describes "two circular
cutouts each containing a central green element" — the green is the table showing through the
hole. The object prompt says "A hole may show the green surface through it; that green is not part
of the part", which fixed the same misreading on `Image_001`'s red block ("a passage allowing a view
of a bright green surface through them") but not on this plate. A sharper wording ("Any green you
see inside a hole … is the surface below showing through it") made it worse — the holes became
"indentations" — so the prompt was not tuned further.

- **Impact:** a false detail in one object's text on dark-rimmed through-holes; the object, its
  holes and its condition are otherwise described correctly (the rust on the same plate is found).
- **Not fixed by tuning:** a prompt adjusted until one frame reads right is the thing the
  comparison must not do. Revisit with a different input (e.g. a crop whose table is masked to a
  neutral colour) rather than more wording.

## The description and the measurement can disagree in the same panel — and the numbers are right

The describer guesses shape from the pixels of one small crop; the measurement computes it from the
mask. Where they disagree, the measurement is right, and the panel shows both side by side:

- **Hex nuts** (`Image_001` objects 7 and 8): Gemma calls them "a small, roughly octagonal metal
  washer or flange" and "a circular metal washer or ring" (Florence-2 called them rings too). The
  measurement identifies them correctly: the across-flats detection finds the silhouette's 60°
  periodicity and reports `A/F 11.7 mm` / `A/F 11.5 mm`, not `Ø`. The geometry knows it is a hex
  nut; the text says washer.
- **The square plate in `Image_007`**: Gemma calls it "a rectangular, flat plate"; the measurement
  is 48.1 × 46.9 mm, i.e. square. (It calls the other square plate, `Image_006`'s maze plate,
  47.8 × 47.0 mm, "square".)

Both models miss the nuts, so this is a limitation of describing a small crop, not something prompt
wording will fix.

- **Impact:** the object's text can misname its shape or kind while its size line is correct.
  Trust the numbers.
- **The likely fix, not built:** give the describer what the measurement already knows — e.g. the
  measured shape class and dimensions in the prompt ("this part measures A/F 11.7 mm, hexagonal") —
  rather than letting the model guess shape from pixels.
