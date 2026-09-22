# Known issues

Behaviour-preserving migration notes: latent quirks discovered during the
RoLE-style refactor and deliberately left unchanged, so the migration's
characterization baseline stays green. Fix them as separate, intentional changes
after the migration — each is pinned by a test so a fix is a visible diff.

## Label distiller strands the `n` from `an`

`Vision.Utilities.Caption.Condense_Label` peels Florence caption lead-ins by
iterating `CONST_LABEL_LEADINS` and stripping the first match. `"this is a"`
appears before `"this is an"` in that tuple and is a prefix of it, so a caption
like `"This is an M6 stainless steel screw..."` matches `"this is a"` first,
leaving a stranded `"n"`: the label becomes `"n m6 stainless steel"`.

- **Impact:** cosmetic and low. Only the short `Label` is affected; the full
  caption is preserved in `Detection_Str.Detail` and is what the panel shows as
  the object's sentence.
- **Pinned by:** `test/Vision/Utilities/test_caption.py::test_condense_label_known_leadin_ordering_quirk`
  and the characterization baseline (`Example/Vision/characterize_baseline.log`).
- **Fix after migration:** either order `CONST_LABEL_LEADINS` longest-first (so
  `"this is an"` is tried before `"this is a"`), or match on word boundaries.
  Update the pinning test and re-baseline in the same change.

## `calibrate.py` custom camera config is silently ignored

`Example/Camera/calibrate.py` builds `custom_cfg` with lower-case keys:

```python
custom_cfg = {
    'exposure_time': 10000,
    'gain': 10,
    'balance_ratios': {'Red': 0.95, 'Green': 0.9, 'Blue': 1.2},
    'pixel_format': 'BayerRG8',
}
```

But `Camera.Basler.Basler_Cls.__Configure` reads the **capitalized** keys —
`self.config['Exposure_Time']`, `['Gain']`, `['Balance_Ratios']`,
`['Pixel_Format']` — the same form as `Camera.Core.CONST_BASLER_CONFIG`. The
lower-case keys therefore never match; `Basler_Cls` merges them in but reads none
of them, falling back to its own `default_config`. So `calibrate.py` runs the
camera at the wrapper's defaults, not the values it appears to set.

- **Impact:** the calibration is performed at unintended exposure/gain/white
  balance. Latent because `calibrate.py` needs a physical Basler camera and has
  never been run against hardware in this repo.
- **Should be:** `{'Exposure_Time': 10000, 'Gain': 10, 'Balance_Ratios': {...},
  'Pixel_Format': 'BayerRG8'}` (Capitalized), matching `CONST_BASLER_CONFIG`.
- **Not fixed here:** correcting the keys changes the capture behaviour, which is
  out of scope for a style pass and unverifiable without the camera. Fix it
  together with a hardware test run.

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
when any detection's `Confidence` is below its threshold (0.35). Florence-2 emits
no score, so `Confidence` is `None` and that branch never fires. The FastSAM
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
  are missed, lower the segmenter confidence (`CONST_SEGMENTER_CONF`), try `'box'`
  mode for those, or revisit the segmenter choice; if they segment, close this note.

## A very harsh cast shadow can be absorbed into a part's component

The over-segmentation this entry used to describe — a cast shadow's boundary
surviving stage 3 as an extra sliver, so N parts reported as more than N — was a
property of the old coverage-gate + mask-NMS filter. The fusion pipeline replaced
that filter (see git history: the FastSAM-∪-background-subtraction port), and on
**real captures the defect is gone**: `Image_004`'s soft cast shadow is stripped
by the background-subtraction opening (`Segmentation.CONST_BG_OPEN_KERNEL`) and the
plate comes back as a single, tight silhouette (rectangularity ~0.88, no shadow
tail). Measured across all seven `Data/Camera` frames, the counts are exactly the
inventory (15 objects, no over-count).

What remains is the **opposite, narrower** failure, and only off real data: when a
shadow is far darker and larger than any real capture — a 40%-darkening ellipse too
big for the opening to erase — its absdiff clears `CONST_BG_DIFF_FLOOR`, and the
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
`Florence_Vision_Cls.Analyze` runs stage 1 (background subtraction against
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
- **Detection route:** the object **count** against expectation is the first signal
  (a merge lowers the count by one). To see it in the mask, switch the one constant
  `CONST_ANNOTATE_MASK_FILL = 'index'`: the diagnostic mode fills each object in its
  own `Index_Color`, so a single blob carrying one colour where two were expected
  shows the merge, and one part in two colours shows an over-segmentation.
- **Pinned by:** `test/Vision/Utilities/test_annotate.py::test_mask_separates_near_but_distinct_objects`
  and `::test_index_fill_mask_mode_is_reachable_by_one_constant`.

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
