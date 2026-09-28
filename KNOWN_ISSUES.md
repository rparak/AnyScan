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

## The fusion's parameters are validated on thirteen real frames only

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

Unlike the old gate, these have run on real captures: the thirteen frames of the pinned test set
(`Evaluation.Frames`, `Data/Images/Test/All`), shot under the calibration and reference in force, with
every frame's count pinned against a by-eye inventory
(`test/integration/test_pipeline.py::test_counts_match_the_inventory`). Ten frames match; three do not —
touching plates, in the entry below. The seven frames of the previous test set (removed in `f5cd075`,
recoverable from `f5cd075^`, shot under the previous calibration) give the same counts as before the
closing changed, object masks unchanged pixel for pixel. Thirteen frames of one table, under one light,
is still a narrow base.

- **Seen since:** parts that touch or nearly touch (`All/Image_009`–`013`), and a dark rusted plate the
  background cue barely sees (2 % of it in `All/Image_013`), carried by FastSAM alone.
- **Not yet seen on real data:** parts close to the table's colour, and any other lighting.
- **The failure signatures to watch:**
  - a real part missing from the count (a cue failed and the other did not carry it)
  - one part split into two components — the closing fills gaps inside a component but no longer
    joins two separate ones, so a part the cues see in two pieces stays two (not seen on any of the
    twenty frames: every count there was the same with no closing at all)
  - two neighbours merged into one (they touch; see *Touching parts merge before the closing*)
  - a part's outline running into its shadow (see the harsh-shadow entry below)
- **Until more real frames are analysed,** the parameters are trusted on these frames only.
  When a failure signature appears, look at which stage causes it before changing a parameter: the
  touching-plate merge looked like a closing-kernel problem and three of five were not.

## Touching parts merge before the closing

Of the five two-plate frames in the test set, three still come back as ONE object: `All/Image_009`,
`011` and `012`. **FastSAM offers the right answer and the wrong one at once, and the union takes
both:** each plate is its own mask, and FastSAM also returns a mask covering both plates — in 011 and
012 it outscores a single plate (0.94 against 0.87 / 0.91 in 011, 0.94 against 0.82 / 0.94 in 012;
0.81 against 0.97 / 0.97 in 009). The union keeps every mask, so the both-plates mask joins them before
the closing runs. A second, small bridge in each frame means removing that mask alone separates none:

| Measured per row (2026-09-28) | 009 | 011 | 012 |
|---|---|---|---|
| Dark seam between the plates | 1 px, absent in 207 of 543 rows | 10 px, every row | 6 px, every row |
| Seam brightness / plates' | 0.58 | 0.38 | 0.47 |
| FastSAM's two plate masks | 23 px apart, never touching | 2 px apart, never touching | 4 px apart; touching in 35 of 361 rows (y 615–658) |
| The background cue joins them | rows 621–867 | rows 316–320 only (the seam's top end, where it opens into a V) | nowhere |

- **The background cue holds 011 and 012 apart — it does not bridge them.** Counterintuitive, so
  stated plainly: background subtraction asks whether a pixel differs from the *green table*, not from
  the plate. A dark seam is far closer to the dark-green table than a bright plate is: its difference
  from the table (~40–44) sits at those frames' Otsu threshold (42–43), and after the blur it falls
  below — so the cue reads the seam as table in every row of 012 and all but five rows of 011. The
  more visible the seam, the more the cue separates. 009 is the exception: dark plates and a faint
  seam, the threshold drops to its floor (28), and plates and gap all clear it.
- **012's second bridge is FastSAM's own:** its plate edges each bleed ~3 px into a 6 px seam and meet
  mid-seam over 35 rows. At the 1024 px inference size the seam is ~3 px wide.

`010` and `013` (plates 10.8 and 9.8 px apart) used to merge in the closing; the closing no longer
joins components that were separate before it, and they now count two (design-decisions, *The closing
never joins two components*).

- **Impact:** two touching parts read as one object: the count is one low and the size is the pair's.
- **No configuration reaches it:** the merge happens before the closing and the area filter. Lowering
  FastSAM's NMS `IoU` could drop the both-plates mask in 009, but in 011 and 012 that mask outscores a
  plate, so the plate would be suppressed instead — and the background bridge would remain.
- **Tried and rejected — a larger FastSAM inference size (`Segmentation.Image_Size`).** At 1024 the
  6–10 px seam is ~3 px wide, so running closer to the frame's 1920 px looked like a configuration fix.
  Measured 2026-09-28 on all thirteen frames (1024 / 1280 / 1536 / 1920):
  - **It fixes the cause and creates a worse one.** The both-plates mask weakens as the size grows —
    011 0.94 → 0.96 → 0.79 → **0.48**, 012 0.94 → 0.91 → 0.81 → **0.43** — but the plates' own masks
    grow into the seam (they take in the dark edge and the side wall, which is the seam) and touch: at
    1920 in all five two-plate frames, 86–3,132 px of contact, 011 included (923 px), which does not touch
    at 1024. 009, 011 and 012 stay merged at every size.
  - **It costs frames that count correctly.** Off the inventory: 1024 — 009, 011, 012; 1280 and 1536 —
    those plus 010, 013 (their plate masks now touch), 003, 004; 1920 — 009, 011, 012, 013, 003, 004,
    005. At 1920 in `All/Image_003` one FastSAM mask covers **0.495** of the frame — the right half of the
    table — just under the 0.50 `Background_Area_Fraction` that would reject it as the table plane, so it
    stays in the union and joins the robot and the dark plate. That threshold sits at the edge of where it
    matters; this is the number beside it.
  - **Time is not the reason.** FastSAM per frame (median / max): 171 / 237 ms at 1024, 231 / 292 at
    1280, 299 / 398 at 1536, 435 / 495 at 1920 — at most a quarter of a second more, against Gemma's
    seconds per object. The counts are the reason: `Image_Size` stays 1024.
- **Tried and rejected — splitting a merged component by its FastSAM masks with a seam test.** FastSAM
  returns a hierarchy: both plates, each plate, each machined plate's two halves, the hole rings. "Both
  plates = two plates" has the same shape in mask space as "one plate = two halves", so a split needs
  evidence that a boundary is a physical gap. The darkness of the seam between two masks (its 10th
  percentile over the parts' median) was measured on every candidate pair in all twenty frames:
  touching plates 0.36–0.46, one plate's halves 0.73–0.88 — but **the robot's body against its arms,
  legs and head 0.44–0.61**. The robot is separately printed pieces pinned together, so its joints are
  real seams, and the darkest (0.44) is darker than the lightest plate seam (0.46). Any threshold that
  splits the plates splits the robot. Do not retry this test without a new kind of evidence: at the
  seam, two parts touching and one assembled part look the same.
- **Pinned by:** `test/integration/test_pipeline.py::test_counts_match_the_inventory` — 009, 011 and 012
  are strict xfails, so the day one separates the suite fails and this entry is revisited.

## The label mask reveals near-but-distinct objects, not merged touching ones

The exported label mask (`Vision.Utilities.Annotate.Draw_Label_Mask`) fills each
object with a light tint of its box colour and outlines it in that box colour from
that object's **own** component mask. Two parts that
sit close together but do not touch are separate components, so they render as
two tinted shapes with two outlines and black ground between them — the mask reads
as two objects. Two parts that **touch**, however, are already a single component
by the time they reach the renderer: `Vision.Utilities.Fusion.Fuse_Objects`
unions and connected-components the fused cues *before* anything is drawn, so a
merge collapses into one blob upstream (see *Touching parts merge before the closing*). The mask draws one shape with one
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
**real captures the defect is gone**: the soft cast shadow of the previous test set's
`Image_004` (a single two-hole plate; the set was removed in `f5cd075`, recoverable from
`f5cd075^`) is stripped by the background-subtraction opening
(`Segmentation.Background.Open_Kernel` in the configuration) and the plate comes back as a
single, tight silhouette (rectangularity ~0.88, no shadow tail). No frame of the current set
over-counts either: the three wrong counts are all merges (*Touching parts merge before the
closing*).

What remains is the **opposite, narrower** failure, and only off real data: when a
shadow is far darker and larger than any real capture — a 40%-darkening ellipse too
big for the opening to erase — its absdiff clears the Otsu floor (`Segmentation.Background.Otsu_Floor`), and the
fusion **absorbs** it into the object's component rather than rejecting it, so the
mask extends past the part into the shadow band. This does not over-count (it stays
one object), but the silhouette is no longer tight, and the enhanced crop fed to the
describer would then contain a strip of table.

- **Fixed case, pinned by:** `test/integration/test_pipeline.py::test_plates_come_back_as_compact_silhouettes_on_a_real_capture`
  (slow; `All/Image_003` → three objects, each plate's rectangularity ≥ 0.80) and, for every frame's
  count, `::test_counts_match_the_inventory`. The current set has no single shadowed plate like the
  old `Image_004`, so that exact case is no longer pinned.
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

The limitation stands; its example is stale. When it was written, four of the previous
test set's `Image_001`'s nine objects were background-only; re-measured 2026-09-25, none of
that set's objects were. On the current set (`All/`, 2026-09-28) none are either: 41 `both`
and 3 `fastsam` (one each in `Image_001`, `Image_007` and `Image_013` — the dark plate the
background cue sees 2 % of), every object scored 0.82–0.98. So the test frames score fully and
do not exercise this path; a rig frame with a part FastSAM misses would.

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

Seen on the previous test set (removed in `f5cd075`, recoverable from `f5cd075^`; the describer
has not been re-run on the current set). On its `Image_002` plate, whose two through-holes have dark rims, Gemma describes "two circular
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
mask. Where they disagree, the measurement is right, and the panel shows both side by side (seen on
the previous test set, `f5cd075^`; the describer has not been re-run on the current set, and the sizes
below were shown to one decimal then):

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
