# Known issues

Behaviour-preserving migration notes: latent quirks discovered during the
RoLE-style refactor and deliberately left unchanged, so the migration's
characterization baseline stays green. Fix them as separate, intentional changes
after the migration — each is pinned by a test so a fix is a visible diff.

## `Synth_Eye` stale project name (fixed)

`calibrate.py` located the project folder by splitting `os.getcwd()` on the string
`'Synth_Eye'` — a previous project's name — which produced a wrong output path in
this repo (`scan.py` correctly used `'anyscan-pyqt'`). Fixed in the style pass
(commit "Style: bring Example/Camera/scan.py and calibrate.py to house style").
Recorded here in case the same `Synth_Eye` copy-paste appears in other inherited
files pulled in later; a repo-wide `git grep 'Synth_Eye'` is currently clean.

## `Basler_Cls` uses bare `Exception`, not the RP error pattern

`Camera/Basler.py` raises and catches bare `Exception` throughout — e.g.
`raise Exception('[ERROR] No Basler cameras detected...')` and `except Exception`
in `__Connect`, `Capture`, `__Set_Optional`, `__Close`. This is the inherited
driver's style, not the RP assert-inside-try-then-report pattern, and a bare
`except Exception` can mask an unexpected error as a routine one.

- **Impact:** low in practice. The facade `Basler_Camera_Cls._Open`/`_Grab` catches
  whatever `Basler_Cls` raises and re-wraps it into a `Camera_Error_Cls` with an
  actionable sentence, so the operator never sees a bare traceback. The roughness
  is internal to the driver.
- **Not fixed here:** the style pass gave `Basler_Cls` types, docstrings and
  `CONST_*` naming but deliberately did not restructure its control flow —
  rewriting the error handling changes behaviour on a hardware path that has no
  automated coverage. Do it together with a real camera run, narrowing the
  `except Exception` clauses and replacing the bare `raise` with `Camera_Error_Cls`.

## `Verdict`'s confidence branch is dormant by design

`Reporting.Core.Verdict` degrades the operator badge to `'Low confidence' / 'warn'`
when any detection's `Confidence` is below its threshold (0.35). The describer (Gemma,
like Florence-2 before it) emits no score, so `Confidence` is `None` and that branch never
fires. The FastSAM
pipeline does not wire it up either: the segmenter's score is stored in the
**separate** `Detection_Str.Segmenter_Score`, and `Confidence` stays `None`.

- **Why kept apart:** a segmenter's mask confidence and a detector's / classifier's
  confidence are different quantities. Feeding FastSAM's mask score into `Confidence`
  would silently activate a dormant, operator-visible verdict path — a busy frame
  with one lower-scoring mask would flip the badge to amber for a reason that has
  nothing to do with recognition quality. That is a behaviour change dressed up as
  wiring, so it was declined.
- **If a real detection/classification confidence ever exists** (a model that scores
  *what* an object is, not merely how sharp its mask is), populate `Confidence` with
  it deliberately, and re-check the 0.35 threshold against that model's score
  distribution. Do not point `Confidence` at `Segmenter_Score` as a shortcut.

## FastSAM dilation and coverage gate are validated only on synthetic scenes

Two stage-tunables were set and checked against synthetic frames (solid shapes on
the flat green reference), never against hardware captures:

- `Segmentation.CONST_SEG_MASK_DILATE_KERNEL = 5` — how much the stage-1 change mask
  is grown before stage 3 scores coverage against it.
- `Mask_Filter.CONST_FILTER_CHANGE_COVERAGE = 0.35` — the fraction of a FastSAM mask
  that must overlap the change mask for it to count as an object.

- **What the synthetic evidence showed:** the coverage distribution was degenerate —
  real objects at ~1.0, a cast shadow at 0.0, with the 0.35 gate in a wide empty gap.
  That validates *separation* but says nothing about where real parts land, because
  solid shapes on flat green give artificially perfect masks.
- **The failure signature to watch on real captures:** genuine objects coming back
  with coverage sitting **just above 0.35** (say 0.4-0.6) rather than near 1.0. That
  means the FastSAM mask spills past the change mask at textured/shiny/anti-aliased
  edges the stage-1 subtraction missed — i.e. `CONST_SEG_MASK_DILATE_KERNEL` is too
  small and is starving those edges. The fix is to grow the dilation until real
  objects clear the gate comfortably, not to lower the gate.
- **Revisit both** with a real parts run (the `Example/Vision` FastSAM script, once
  it exists, is the vehicle), and record the observed real-object coverage range so
  the gate and dilation can be set from data rather than from synthetic 1.0s.

## Touching-object separation depends on the FastSAM prompt mode

`Segmenter.CONST_SEGMENTER_PROMPT_MODE` defaults to `'everything'`, and it must
stay there for the pipeline to earn its keep. `'box'` is kept only as a config
alternative for scenes whose objects are already well separated.

The task file's Stage 2 said "prefer box-prompting with the stage-1 candidate
regions." **That wording was superseded by evidence — do not switch the default
back to `'box'` on the strength of the spec.** The reason is concrete:

- Stage 1 merges touching parts into a **single** candidate region (connected
  components, plus the dilation). A box prompt returns one mask per box, so
  `'box'` inherits that merge — two touching parts come back as one object, exactly
  the failure FastSAM was added to fix. Measured: two dark rectangles 15px apart →
  one merged region → `'box'` returns 1 mask; `'everything'` returns 2.
- Under `'box'`, Stage 3's part/whole NMS is near-dead code (one mask per region
  cannot contain a part/whole pair), so the 144 MB model and the torch dependency
  would be reproducing what background subtraction already gave us.

`'everything'` segments the frame independently (separating touching parts) and
leans on the Stage 3 filter to discard the table, the fixture and the part/whole
duplicates — which is what that filter was built for.

## Open question: FastSAM's reliability on low-contrast shapes

FastSAM dropped low-contrast objects **twice** during development, in independent
synthetic scenes:

- In the prompt-mode comparison, it returned **no mask for a flat mid-grey box**
  (BGR ~105) on the green reference, in both `'box'` and `'everything'` modes.
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

- **This is why the `analyze.py` synthetic demo uses four saturated colours.** The
  dark shapes were unreliable, so the demo was built from shapes FastSAM segments
  dependably. That makes the demo a clean end-to-end illustration — **not evidence
  that the pipeline handles all parts**. A passing demo run says the
  wiring works, not that a grey or black part would be found.
- **Why it matters here:** grey / metallic and dark parts are exactly what this
  application inspects, so the answer cannot be assumed either way.
- **The specific check before trusting it:** photograph real low-contrast parts
  (grey/metallic and dark) on the reference background, run `Example/Vision/
  analyze.py`, and confirm each segments (a mask survives Stage 3). If real parts
  are missed, lower the segmenter confidence (`Segmentation.Confidence` in the configuration), try `'box'`
  mode for those, or revisit the segmenter choice; if they segment, close this note.

## A very harsh cast shadow can be absorbed into a part's component

The over-segmentation this entry used to describe — a cast shadow's boundary
surviving stage 3 as an extra sliver, so N parts reported as more than N — was a
property of the old coverage-gate + mask-NMS filter. The fusion pipeline replaced
that filter (see git history: the FastSAM-∪-background-subtraction port), and on
**real captures the defect is gone**: `Image_004`'s soft cast shadow is stripped
by the background-subtraction opening (`Segmentation.Background.Open_Kernel` in the configuration) and the
plate comes back as a single, tight silhouette (rectangularity ~0.88, no shadow
tail). Measured across all seven `Data/Camera` frames, the counts are exactly the
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
  failure. It stays on the real-capture list.

## The no-reference-background detection path was removed

Analysis now **requires a reference background**. Every path through
`Vision_Pipeline_Cls.Analyze` runs stage 1 (background subtraction against
`CONST_BACKGROUND_REF`), so with no reference capture the analysis raises rather
than running.

Until this change there was a second detector, `CONST_DETECTOR == 'florence'`,
which ran Florence-2's own `<REGION_PROPOSAL>` on the whole frame with no
background subtraction — the only path that could analyze an arbitrary image with
no reference. It was removed deliberately: it was slower than FastSAM, no code
set it (default was `'fastsam'`), and no test exercised it, so it was an untested
branch carrying a capability nothing used.

- **Capability lost:** analyzing an image when no reference-background capture
  exists (e.g. a one-off photo from a different camera). The app, the example
  script and the tests all supply a background, so none of them regressed.
- **What it would take to restore:** re-add the whole-frame detector — a method
  running the `<REGION_PROPOSAL>` task (task token, max-tokens and min-area
  constants), a describe-the-boxes loop cropping each detection (the old
  `Crop_With_Pad` helper, also removed), and a `CONST_DETECTOR` toggle selecting
  it ahead of stage 1. The removed code is recoverable from git history (the
  commit that removed the `<REGION_PROPOSAL>` path); restoring it should come with
  the test the original never had.

## The characterization baseline is pinned to the toolchain

`Example/Vision/characterize.py` records the `python` / `numpy` / `opencv` versions
in `characterize_baseline.log`, and the segmentation section pins exact box pixel
coordinates. Those coordinates depend on the OpenCV build, so a `numpy`/`opencv`
upgrade can change the committed `.log` — flipping the "empty diff" regression gate
for a reason that has nothing to do with the application code.

- **Impact:** the gate is a genuine behaviour net, but it couples "did the code
  change behaviour?" to "did the toolchain change?" On a dependency bump someone
  must re-run the harness and re-commit the baseline, and confirm by eye that only
  the version header (not the composed sentences) moved.
- **Options if it becomes annoying:** drop the version header and the exact box
  coordinates from the pinned output (assert box *count* and ordering instead of
  pixels), or split the log into a version-independent "behaviour" section that
  gates and a separate informational "environment" section that does not.

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

## The confidence status metric is partial — only the FastSAM cue is scored

The status strip's `Confidence (mean)` averages `Detection_Str.Segmenter_Score`,
which only the FastSAM cue supplies. An object found by background subtraction
alone (`Cue == 'background'`) carries `Segmenter_Score is None` and no confidence
of its own — on `Image_001` that was four of nine objects. The field therefore
reports the mean over **exactly** the scored objects and shows the coverage
(`87% (5/9)`), never averaging over the partial set silently, and reads `—` when
no object has a score.

- **Why not route every object through FastSAM:** the fusion exists because neither
  cue is sufficient, and a single run proves it in both directions — objects the
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
- **Pinned by:** `test/UI/test_status_metrics.py::test_confidence_is_the_mean_over_scored_objects_with_coverage`,
  `::test_confidence_denominator_is_the_scored_count_not_the_total` and
  `::test_confidence_is_no_value_when_no_object_has_a_score`.

## Measured sizes may carry a systematic error of unknown magnitude — not for acceptance decisions

**Do not use the object sizes for acceptance decisions yet.** They may be wrong by a systematic
error whose size nobody has measured. They are shown to 0.1 mm because that is one pixel at
0.098 mm/px, not because they are accurate to 0.1 mm.

They are **repeatable** — the same plate in `Image_002`–`005`, placed differently, measures
57.7–58.5 × 37.9–39.1 mm — but repeatability says nothing about correctness: a systematic error
(a wrong scale, or a scale that varies across the frame) is the same in every frame and hides
inside exactly that stability. The calibration in force gives specific reasons to expect one:

- `Conversion_Factor` is derived from chessboard corners in a **single, raw (distorted)** image,
  but it is applied to **undistorted** frames (the live camera and `Example/Camera/scan.py` both
  undistort), so any scale difference between the two pixel spaces is a systematic error. The
  undistortion itself rescales: `getOptimalNewCameraMatrix(alpha=1)` gives a focal length 0.17 %
  (x) and 0.97 % (y) shorter than K's.
- The calibration's own model, taken at face value, predicts sizes about +0.5 % (x) / +1.0 % (y)
  too large at the frame centre and within ±0.3 % near the corners — a position-dependent error.
  That prediction is **not** evidence either way: it comes from the same single-image fit, which
  puts K's principal point at (160.7, 355.5), about 800 px from the image centre (960, 600) — a
  sign the intrinsics are poorly constrained.
- A mean corner spacing over the whole board averages out any perspective tilt of the board, so
  a tilted calibration board biases the factor.
- The factor holds only in its **reference plane** — the calibration board's surface — at the
  calibrated distance; moving the camera or refocusing invalidates it altogether. A part with
  thickness is not in that plane — see the next entry, which is a separate effect that no factor
  can remove.

- **Impact:** every size (A × B, Ø and A/F) may carry a systematic error of unknown magnitude, either
  one scale factor or one that varies with position in the frame.
- **The check that closes it:** photograph references of known size — the calibration chessboard
  (its square size calipered) and caliper-measured flat parts — at the frame centre and in the
  corners, through the application's own undistortion, and compare measured against nominal in mm
  and percent. If the error is the same everywhere it is one correction to the factor; if it
  varies across the frame, the factor must be recomputed from undistorted corners and the
  calibration redone from several board poses before any size is relied on. Capture sets now keep
  each frame before undistortion too (`<set>_distorted.png`), so the same reference frames can be
  re-measured under any later calibration.
- **The tool to redo it exists; the result does not yet.** `Example/Camera/calibrate.py --capture`
  records distorted frames (flat and tilted boards, all kept) and `--images` solves them together,
  derives the factor from the flat boards' undistorted corners in the application's pixel space,
  and reports the principal point, the tilt spread and the factor's spread across the frame. It
  writes a NEW configuration file; the configuration in force is still the single-view one above
  until a new set is solved, compared against it, and adopted (App/run.py hardcodes its path).

## A part's measured size depends on where it lies in the frame, and on its thickness

**In practice: this setup measures repeatably, not absolutely.** Comparing like parts in like
positions works; deciding whether a part is within a stated tolerance does not, and won't without
a telecentric lens.

**The same part measures differently depending on where it lies in the frame.** A 6 mm thick nut
of about 12 mm reads ≈ 0.2 mm large at the frame centre and ≈ 1.5 mm large near the frame edge.
That is not a precision caveat: **any acceptance threshold built on these sizes would have to
depend on position (and on the part's thickness)** — a fixed tolerance would pass a part at the
centre and reject the same part near the edge. If that is unacceptable for the intended use, the
answer is a **telecentric lens**, which sees every part at the same scale regardless of position
and height; better to know that before anyone builds tolerances on these numbers.

It is a property of measuring with one camera and an ordinary (entocentric) lens from above, not
a bug: **even a perfect conversion factor gives a size that depends on how thick the part is and
where it lies.** The factor is exact in one plane only — the **reference plane**, the surface of
the chessboard it was calibrated on (the table itself only if the board lay flat on it; a mounted
board puts the plane at the board's height h above the table). A part's outline is formed partly
above or below that plane.

Take a flat part of footprint width W and thickness t, the lens at height Z above the table
(~340–380 mm; 360 below), the reference plane at height h, and X the distance, on the table, from
the optical axis to the part's edge farther from it:

- **Centred on the optical axis**, both outline edges are top edges, and the top face is at height
  t, so it reads W · (Z − h) / (Z − t) — with a board flat on the table (h = 0), about **+0.28 %
  per millimetre of thickness**: a 58 mm plate 3 mm thick reads ≈ 58.5 mm (+0.8 %).
- **Off the axis**, the outline is the union of the top and bottom faces' projections: the edge
  away from the axis is the top edge, the edge toward it is the bottom edge, and the side wall
  between them is visible. Along the direction away from the axis the size reads (for h = 0)
  **W + X · t / (Z − t)** — the excess grows with the distance from the axis, **not** with the
  part's size. The same 3 mm plate with its far edge 100 mm off-axis gains ≈ 0.8 mm that way; the
  6 mm nut near the frame edge (X ≈ 90 mm) gains ≈ 1.5 mm (~13 %). The size across that direction
  gains only the top-face term, so an across-flats width (the smallest width) is largely spared,
  while a round Ø (the mean of two sides) takes about half the excess.
- **A central measuring zone does not rescue fixed tolerances.** The smallest excess, with the
  part centred on the axis, is W · t / (Z − t) — 0.2 mm for the 12 mm, 6 mm thick nut — so a 0.1 mm
  tolerance cannot be held for that nut **anywhere** in the frame. Holding 0.5 mm needs its far
  edge within ~30 mm of the axis: a central zone about 6 cm across on a 188 × 118 mm field.

- **Why it is not corrected:** the correction needs each part's thickness, the reference plane's
  height, and the true optical axis. The thickness is not in the image, and the calibration's
  principal point (160.7, 355.5) is itself suspect. In software it could only be corrected per
  part family once its thickness is known and the axis is calibrated from several board poses.
- **What a size means, then:** the extent of the part's silhouette from above, converted in the
  reference plane. For thin parts near the frame centre that is within the pixel resolution of
  the footprint; for thick or off-centre parts it is not.
- **Measured by** the reference check in the previous entry: the calipered parts at the centre and
  in two corners, with their thicknesses and the board's height, give the parallax term directly,
  alongside the chessboard's own scale in its own plane.

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

## The describer is not a defect detector: whether a stain is reported depends on the framing

**Read this before building any acceptance decision on the text.** The describer is not a reliable
defect detector. A description that does not mention a stain, scratch or corrosion is **not
evidence that there is none**. Nothing in the output marks a miss: a clean-sounding description of
a stained part looks exactly like a correct description of a clean one. For an application meant to
flag defects, this is the most serious limitation recorded here.

**The evidence.** The rust on `Image_002`'s plate is the stain the describer's prompt was written to
catch. It is named at object-crop paddings 0.20 and 0.36, and missed at 0.00–0.12 and at 0.28. The
result is deterministic (identical text on every run at a given padding), so this is not sampling
noise. It is a step, not a slope: the same stain, equally visible in every crop, is reported or not
depending on how the part is framed. At the shipped padding (0.20) it happens to be reported. The
whole finding rests on one stain on one frame — which is a reason for more caution, not less.

**Why, and the route that would work.** This is the same conclusion reached earlier from a
different direction (in discussion, not previously written down here). A stain is a *texture on a
surface*, not an object with a boundary. Describing a part in a sentence is not the same task as
detecting a defect on it, and no amount of prompt wording turns the one into the other. The route
for defects is **anomaly detection inside the part's mask**: compare the part's surface against
what a good part looks like, and localise what differs. Its verdict feeds the classification that is
already wired and waiting for a rule (`General.Classification.Enabled`, the OK/NOK verdict UI; see
docs/design-decisions.md, *Classification is a per-configuration switch …*). Until that exists,
treat surface condition in the text as a hint that may be absent, never as a finding.

- **Not fixed by picking the padding that catches it:** that would fit one stain on one frame — the
  frame the prompt was also tuned on. docs/design-decisions.md (*The object crop padding stays at
  0.20*) records the full measurement.
- **What would test it:** more stained parts, photographed and labelled (a real-capture task, on the
  capture list), so detection can be measured across defects rather than inferred from one.

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

