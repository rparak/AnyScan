# Known issues

Open behaviours of the pipeline that show up in its text or its numbers, recorded so they are
recognised when they appear. Nobody decides anything on them. **The three limitations that do affect
decisions are in the README, under [Limitations](../../README.md#limitations).**

Each entry states the behaviour, what it affects, and why it is not fixed. An entry is removed when
the behaviour is fixed, and the resolution is recorded in `design-decisions.md`.

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
  (design-decisions.md, *The configuration sets the camera's sensor window*). So is a camera
  another program holds: it raises `Basler_In_Use_Error_Cls` at once, not retried, reported as in use
  (design-decisions.md, *A new reference is the mean of 8 frames…*).
- **Not fixed here:** the style pass gave `Basler_Cls` types, docstrings and
  `CONST_*` naming but deliberately did not restructure the connection's control flow —
  rewriting it changes behaviour on a hardware path with little automated coverage. Narrow
  the remaining `except Exception` clauses in `__Connect`, `Capture`, `__Set_Optional` and
  `__Close` together with a real camera run.

## Basler's grab retries print to the console and never reach the session log

`Basler_Cls.Capture` (`Camera/Basler.py`) retries a failed or incomplete grab up to `max_attempts`
times (3) and prints each failed attempt to the console (`[WARNING] Attempt n/m ...`). Nothing passes
the count back to `Basler_Camera_Cls`, so a frame that needed retries and then arrived leaves no line
in the session log: a run's log cannot show how often grabs were dropped. A grab that fails on every
attempt is not affected: `Capture` returns None, `_Grab` raises a `Camera_Error_Cls` ("The camera
returned an empty frame..."), and the failed scan is logged.

- **Impact:** low today. Only retried-then-successful grabs are invisible in the log. A cable or
  camera that starts dropping frames shows on the console alone, which an operator who starts the
  application from a launcher does not see, and the station event files never record it.
- **Not fixed here:** reporting it means `Basler_Cls.Capture` returning its attempt count and the
  camera emitting it through its log sink: a new line the operator reads, so a change of its own,
  checked with a real camera (the retry path has no automated coverage).

## The fusion's parameters are validated on one table under one light

What decides detection is set in the configuration:

- `Segmentation.Background.*` — the background difference: the Otsu floor, and the opening and
  dilation kernels.
- `Segmentation.Fusion.*` — the closing kernel, the minimum component area, and the
  background-rejection fractions and border count.

Two constants in `Vision/Utilities/Fusion.py` also decide: the 0.10 cue-attribution overlap, which
only labels which cue found an object, and the row band / object cap, which order and limit the
objects.

They are validated on real captures, every frame's count pinned against a by-eye inventory
(`test/integration/test_pipeline.py::test_counts_match_the_inventory`): the 41 frames of the
2026-10-09 session (`Evaluation.Frames`, `Data/Images/Test`, `Image_055`–`095`, counted by eye and
confirmed by the owner 2026-10-11), all matching against the shipped reference
(`Image_Background_001`). The three 2×2 grids of plates set close together (`Image_093`–`095`) come
back as four objects each. The earlier sets of `1061966` and `eb00508^` matched too; the misses below were
on `b5ca788^` and `e2b87bd`. 41 frames of one table, under one light, is a narrow base.

- **Seen on earlier sets:** parts that touch or nearly touch, and a dark rusted plate the background cue
  barely sees (2 % of it), carried by FastSAM alone (`b5ca788^`); an extra object in the bottom-right
  corner on frames that skipped the undistortion the reference went through (`e2b87bd`; design-decisions,
  *A replaced image never keeps its name*, case 6).
- **Not yet seen on real data:** parts close to the table's colour, and any other lighting.
- **The failure signatures to watch:**
  - a real part missing from the count (a cue failed and the other did not carry it)
  - one part split into two components — the closing fills gaps inside a component but no longer
    joins two separate ones, so a part the cues see in two pieces stays two (not seen yet)
  - two neighbours merged into one (they touch; see *Touching parts merge before the closing*)
  - a part's outline running into its shadow (see the harsh-shadow entry below)
- **Until more real frames are analysed,** the parameters are trusted on these frames only.
  When a failure signature appears, look at which stage causes it before changing a parameter: the
  touching-plate merge looked like a closing-kernel problem and three of five were not.

## Touching parts merge before the closing

Two touching parts read as one object: the count is one low and the size is the pair's. Seen on the
five two-plate frames `All/Image_009`–`013` (recoverable from `b5ca788^`): three came back as one object
(009, 011, 012). The current set has plates set close together in its 2×2 grids (`Image_093`–`095`), none
touching, and counts them right, so it does not re-measure this entry.

**Two causes, independent.** FastSAM returns a hierarchy, and nothing structural tells which level holds
the division: two touching plates and one machined plate's two halves measure the same (both children
cover 0.99 of their parent, overlap 0.000, 1.9 px apart). And a bridge remains when FastSAM's both-plates
mask is removed: the background cue's in 009 and 011, FastSAM's own in 012. A segmenter that got the
level right would fix 012 only.

**Five routes were measured (2026-09-28) and all fail:**

1. Lowering FastSAM's NMS `IoU` (shipped 0.9) to 0.7, 0.5 or 0.3: the three still count one; NMS chooses
   levels by score, and the score favours the wrong level as often as the right one.
2. A larger `Segmentation.Image_Size` (1280–1920): the both-plates mask weakens, but the plates' own masks
   grow into the seam and touch, and frames that counted right fail (on the eight frames of `1061966`:
   003 and 004 from 1280, 005 too at 1920, where one FastSAM mask covers 0.495 of the frame, just under
   `Background_Area_Fraction`'s 0.50). Time is not the reason (at most a quarter of a second more per
   frame); the counts are, so `Image_Size` stays 1024.
3. Splitting by the seam's darkness: touching plates 0.36–0.46, a plate's halves 0.73–0.88, but the
   robot's printed joints 0.44–0.61, so any threshold that splits the plates splits the robot.
4. Dropping a parent mask that covers two disjoint children: it fires on every plate, the robot and the
   terminal strip; with a coverage cut it still splits a single plate (010) and leaves 009 and 011 joined.
5. Splitting along FastSAM's leaf masks: the leaves are hole rings, smudges and limbs, not plates.

The full measurements, per frame and per route, are in this file at `d9305b2`.

- **Not fixed here:** left open deliberately. Two plates butted against each other is not a realistic
  inspection case.
- **What would work** (out of scope), both needed: something that picks out the middle level (a segmenter
  returning flat instances, or another cue: depth, a second view), and a separate answer for the
  background bridge.
- **Pinned by:** nothing; restoring the frames from `b5ca788^` with their inventory entries brings the
  strict xfails back.

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
- **Detection route:** the object **count** against expectation is the only one
  (a merge lowers the count by one; the status bar's OBJECTS DETECTED and the Trends
  chart both show it).
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

On real captures a soft cast shadow is stripped by the background-subtraction opening
(`Segmentation.Background.Open_Kernel`) and the part comes back as a tight silhouette; no frame of the
current set over-counts.

The open failure is narrower, and only off real data: when a
shadow is far darker and larger than any real capture — a 40%-darkening ellipse too
big for the opening to erase — its absdiff clears the Otsu floor (`Segmentation.Background.Otsu_Floor`), and the
fusion **absorbs** it into the object's component rather than rejecting it, so the
mask extends past the part into the shadow band. This does not over-count (it stays
one object), but the silhouette is no longer tight, and the enhanced crop fed to the
describer would then contain a strip of table.

- **Fixed case, pinned by:** `test/integration/test_pipeline.py::test_plates_come_back_as_compact_silhouettes_on_a_real_capture`
  (slow; `Image_072` → six objects, the machined plate's and the red block's rectangularity ≥ 0.80,
  measured 0.968 and 0.949 on 2026-10-11) and, for every frame's count, `::test_counts_match_the_inventory`.
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

The test frames do not exercise this path: on the sets measured (2026-09-25 and 2026-09-28; the current
set not re-measured) every object was scored, by FastSAM alone or with the background cue. A rig frame
with a part FastSAM misses would.

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

Seen on the set removed in `eb00508` (recoverable from `eb00508^`); not looked for since. On its `Image_002` plate, whose two through-holes have dark rims, Gemma describes "two circular
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
the set removed in `eb00508`, recoverable from `eb00508^`; not looked for since; sizes shown to one
decimal then):

- **Hex nuts** (`Image_001` objects 7 and 8): Gemma calls them "a small, roughly octagonal metal
  washer or flange" and "a circular metal washer or ring". The
  measurement identifies them correctly: the across-flats detection finds the silhouette's 60°
  periodicity and reports `A/F 11.7 mm` / `A/F 11.5 mm`, not `Ø`. The geometry knows it is a hex
  nut; the text says washer.
- **The square plate in `Image_007`**: Gemma calls it "a rectangular, flat plate"; the measurement
  is 48.1 × 46.9 mm, i.e. square. (It calls the other square plate, `Image_006`'s milled square plate,
  47.8 × 47.0 mm, "square".)

This is a limitation of describing a small crop, not something prompt wording will fix.

- **Impact:** the object's text can misname its shape or kind while its size line is correct.
  Trust the numbers.
- **The likely fix, not built:** give the describer what the measurement already knows — e.g. the
  measured shape class and dimensions in the prompt ("this part measures A/F 11.7 mm, hexagonal") —
  rather than letting the model guess shape from pixels.

## A killed run never gets its run-summary CSV row

The run-summary CSV (`log_<Hardware>.csv`) gets its row from `Session_Logger_Cls.Close`, so a run that
never closes (killed with SIGKILL, a power loss, a hard crash) has a complete `.txt` log but no row, and
nothing adds one later. The daily station event file had the same gap and closes it with an export ledger
(design-decisions.md, *The daily station event file is exported from the session log at close*):
every log the ledger does not name is exported at the next start.

- **Impact:** the CSV under-counts runs and their time after an abnormal exit. The `.txt` log of that run
  still records every event, so the time can be reconstructed by hand.
- **Not fixed here:** out of scope for the station event change. The same ledger mechanism could cover
  it: a run-summary row computed from a finished log, written at the next start for a log without one.

## One full test run died with a fatal error, and nothing named it

On 2026-10-08 one run of the whole suite (`pytest -q`) ended without its summary: the last line of its
output was a fatal-error dump's list of loaded native modules, *Extension modules: numpy._core...,
pypylon._genicam, pypylon._pylon, PyQt5.QtCore, PyQt5.QtGui, PyQt5.QtWidgets, PyQt5.QtSvg, PyQt5.QtTest,
..., fontTools.misc.bezierTools, fontTools.varLib.iup (total: 22)*. Only that line was kept, so the
test that was running, the thread and the kind of error (an abort such as PyQt5's qFatal on an exception
escaping a slot, or a segfault) are unknown. pytest's faulthandler prints that dump to stderr only between
its configure and unconfigure, so it happened during the session, not at interpreter exit. The tree was
`ea13c6a` with the Trends change of `5f7825a` uncommitted in it, pure-Python arithmetic in
`Reporting/Trends.py`. The same tree then passed 13 full runs in a row, as had about 20 full runs and a
30-run stress loop of `test/UI` earlier that day. It has not recurred: the two records kept since
(2026-10-11) hold no fatal-error dump (one run exited with failures, one was cut off mid-run).

- **Impact:** one run in 14 or fewer on that tree, cause unknown. Not called a flake: it is unnamed.
- **What would answer it:** the next one. `test/conftest.py` now keeps a crash record,
  `test/crash_records/crash_record.txt` (git-ignored): each test's node id as it starts, and
  faulthandler's dump of every thread on a fatal error, during the session or at exit. A run that did not
  exit cleanly has its record kept by the next run as `crash_record_<time>.txt` (the newest ten), so
  running the suite again never deletes one (`test/integration/test_crash_record.py`). A crash in the
  interpreter's own finalisation, after the record's last line is written, is not kept.

## A hole drilled where the catalogue puts none is not reported

The hole check counts a positioned group's holes only near the positions the catalogue gives (within √2 ×
tolerance + 0.5 mm, mirrored to all four corners), which keeps a round mark of a hole's size elsewhere on the part
out of the count. A hole of the right size anywhere else on the part is not counted, and nothing says it is there.
Accepted by the owner, 2026-10-11, for phase C.

- **Impact:** a part with its catalogue holes right and one more in an unexpected place reads OK.
- **Not fixed here:** reporting candidates outside every position needs round marks told apart from holes by
  something other than position; no part with a misplaced hole is in the test set to measure it on.
- **Pinned by:** `test/Vision/Utilities/test_holes.py::test_a_hole_at_every_corner_is_counted_and_a_round_mark_beside_one_is_not`
  (a mark 5 mm along an edge is not counted).

## The stain check's colour band is this light's

The band (hue 5–30, saturation from 50, value from 40) was measured on the test set's fronts under the rig's
light and the station file's fixed exposure, gain and white balance (the ratios read back and checked on every
connect, since 2026-10-13). A warmer light, another white balance or a surface reflecting the table's green
differently moves the plate's colours; nothing checks that the band still fits.

- **Impact:** under another light a clean part could show band pixels (a false NOK) or a stain could fall
  outside the band (a stain passed: the error that matters).
- **Not fixed here:** a check of the band needs frames under another light (capture checklist); the camera's
  settings are fixed and read back since `cd28bb2`.
- **Pinned by:** `test/Vision/Utilities/test_stain.py` (the band as shipped), the pipeline's verdicts on the
  test set (slow).

## The describer guard reads words, so a paraphrase can pass and a right sentence can go

`Reporting.Guard_Description` drops a describer's sentence that holds a number or contradicts the hole or the stain
check by reading words: each mention of a hole kind or a stain, in its own clause, and the words just before and after
it (a negation, a count, "missing", "would be"), and a sentence naming the checks ("automatic", "confirmed",
"verified", "detected"). On the mounting plate's 10 capture frames (2026-10-15, 15 judged parts) it changes exactly the
four stored descriptions that contradicted a check and the one naming the check; live, with the no-checks rule in the
prompt, it had nothing to do.

- **Impact:** a contradiction worded unlike those measured can reach the panel (a hole kind it has no word for:
  "openings", "bores"; a negation more than four words before its noun; a stain denied with a part-of-side word,
  "no stains on the front area", which it lets through); a right sentence using a pattern's words can be dropped
  ("detected" in "no scratches were detected"), and a dropped sentence takes its right clauses with it (the four 2026-10-15 drops each held "The
  plate has straight edges, with some evidence of a narrow chamfer"). Every intervention is in the log with the
  describer's full text. The verdict, State and Reasons never come from the describer.
- **Not fixed here:** the describer is not asked to decide, so a model judging its text would be one more
  model to trust; the words grow with what is measured.
- **Pinned by:** `test/Reporting/test_core.py::test_the_guard_drops_numbers_and_what_contradicts_a_check`,
  `::test_the_guard_holds_each_mention_to_its_check_in_both_directions`,
  `::test_the_guard_drops_a_sentence_referring_to_the_checks` (Gemma's own sentences).

## A missing hole is not marked when the part shows nothing to place it by

A hole expected and not found is marked dashed where a hole found puts it: at the pitch from a through-hole, under a
countersink, around a through-hole. The mounting plate's through-holes sit by one long edge, so with no hole of the
side found, which end of the part they belong at cannot be told from the outline, and none is marked. Seen on
capture `20261015-143622_s1`, object 3: a back with no holes, NOK, no hole mark.

- **Impact:** a plate missing all its holes shows no hole marks; its reason ("Both through-holes are missing.") and
  its log lines still say so, and its note says why the marks are absent.
- **Not fixed here:** DINOv2's best turn against the side's reference picked the wrong end on 3 of 21 plates (the test
  set and this capture's front) with every hole in view (margins up to 0.020, overlapping the right ones), and on object 3 its margin is 0.0022; a
  mark at a guessed end may be wrong (design-decisions.md, *A missing hole is placed only by a hole found*).
  A confidence gate on that margin (0.025) was measured on these 21 plates, where it would place 6, all correctly,
  and was not built (owner's ruling, 2026-10-15): one table, one light, and 0.003 between the worst wrong margin and
  the next right one. It can be revisited once more rig captures give the margins on more plates.
- **Pinned by:** `test/Vision/Utilities/test_holes.py::test_a_side_with_no_hole_found_places_none_since_its_end_cannot_be_told`,
  `test/Reporting/test_core.py::test_missing_holes_not_marked_are_named_in_the_note`.

## Sizes beyond 46.4 mm from the frame centre are unverified

The size checks were verified on real frames only out to 46.4 mm from the frame centre
(`Vision.Utilities.Classify.CONST_VERIFIED_RADIUS_MM`: the farthest judged mounting plate of the test set, 46.32 mm,
Image_072). Farther out the side-wall term predicts up to about 1 mm more (README > Limitations), beyond the plates'
0.73 mm margin to the tolerance. A part there is judged on its size exactly as one at the centre: this radius is
evidence for the log, not a branch of the rule. (Outside the station's inspection area a part is not judged at all:
*The inspection area's insets rest on plates measured mostly by the right edge*, below. The 2026-10-15 captures
measured plates 50–66.6 mm out at
59.97–61.27 × 39.89–41.31 mm, within tolerance, the side wall reaching about 1 mm on the edges facing the axis;
without calipers that is not a verification of the size.)

- **Evidence, at the station on 2026-10-29:** two plate judgements beyond 46.4 mm, their bounding-box centres 53.4 and
  57.3 mm from the frame centre, read 60.47 × 40.64 and 60.04 × 40.25 mm, within tolerance (AnyScan-Media archive,
  captures/20261029-143904_s1, frames 7 and 8). The plates were not calipered, so the radius is not widened.
- **Impact:** an OK or a NOK on size beyond 46.4 mm rests on a size not verified there, and Scene Understanding no
  says so (the owner's ruling: a note there stood under sizes that match the plate and misled the operator;
  design-decisions, *The size note is in the log only*). The session log's verdict line gives the distance and the
  radius.
- **Not fixed here:** only rig captures can verify it: mounting plates in the corners of the view and along its
  edges (capture-checklist.md, 3d). If they read within tolerance there, `CONST_VERIFIED_RADIUS_MM` widens to
  them.
- **Pinned by:** `test/Vision/Utilities/test_classify.py::test_the_verdict_does_not_depend_on_where_the_part_lies`,
  `test/Reporting/test_core.py::test_a_size_checked_outside_the_verified_zone_is_noted_in_the_log_only`.

## Four UI tests fail when the suite is run at DPR 2

Run with `QT_SCALE_FACTOR=2`, `test/UI/test_brand_figures.py::test_the_wordmark_and_the_mark_are_the_logos_own`
("the wordmark draws where the logo's tagline is") and the three cases of
`test/UI/test_funding_band.py::test_the_motif_is_faint_squares_at_both_ends_clear_of_every_logo` (a white pixel
where the motif's purple square is expected) fail; the default run is at DPR 1, where they pass, and the DPR 2
checks that exist run on 2×2 blocks. Measured on 2026-10-15, 2026-10-18 (with the new mark, which is not the cause)
and again on 2026-10-24: the same four, at the same assertions.

- **Impact:** none on the DPR 1 run or the station; a DPR 2 run of the whole suite is red.
- **Not fixed here:** recorded on the way, without its cause measured; the tests read pixels at fixed positions,
  which may be what does not scale.
- **Pinned by:** nothing yet.

## The inspection area's insets rest on plates measured mostly by the right edge

A catalogue mode judges only inside the station's inspection area: the frame inset by 10 mm from its top and bottom
edges and 13 mm from its left and right (`Inspection_Area` in the station file; design-decisions.md, *A catalogue
mode judges only inside the inspection area*). The insets were chosen from the 72 fully visible
mounting plates of the test set and the three capture sets on disk, as the smallest at which every size, hole-position
and hole-diameter error of the plates inside stays within half its tolerance. What that rests on:

- **The edges are unevenly covered.** Of the 40 plates inside the area, the closest to each of its edges came within
  0.1 mm of the top (3 plates within 4 mm), 0.7 mm of the right (3 within 4.2 mm), 2.4 mm of the left (3 within
  6.1 mm), but only 4.7 mm of the bottom, and only one plate (`20261016-070930_21`) lies within 9 mm of it. Most of
  the plates measured by the edges, and every one that set the short-edge inset, lay by the **right** edge.
- **At the station on 2026-10-29** (AnyScan-Media archive, captures/20261029-143904_s1, 20 plate judgements,
  measured by their bounding boxes): one plate came 2.3 mm inside the area's bottom edge (12.3 mm from the frame's,
  frame 7), against 4.7 mm before. The closest to the left edge stayed 39.4 mm inside the area (52.4 mm from the
  frame's). The left edge and the corners are still unmeasured, and these plates were not calipered.
- **The corners are not measured.** A plate wholly inside the area can lie up to about 67 mm from the frame centre
  (in a corner, its long side upright); the farthest judged inside lies 58.4 mm out. Between, nothing was measured.
- **One plate exceeds the criterion wherever the area lies.** `Image_083`'s plate, 14.2 mm from the centre, reads
  0.77 mm off its nominal size against the 0.75 mm half tolerance. No inset could change it, so it was set aside; the plates are not measured with calipers (README > Limitations), so part of
  that is the plate itself.
- **The plates past the area are not judged.** By the right edge, where the captures of 2026-10-15 and
  2026-10-16 put them on purpose, they lie over the area's edge and are Warnings, with no check run on them.
  Measured there, a stained front's stains and every hole were found to 80.9 mm out (`20261016-070736_10`), but
  the outlines read up to 1.17 mm off nominal from 57 mm out, more than half the tolerance.

- **The area is narrow upright.** It is about 101 mm high, so a plate standing with its long side vertical (60 mm)
  can move only about ±20 mm up or down from the frame's middle row and still be judged (±30 mm lying across).
  Such a plate 21-22 mm from the centre already reaches into the top band (`Image_062`, `20261015-170753_14`). The
  area shows on the empty view, the scanned frame and the live preview (PREVIEW), so the operator can place a part
  inside it before the scan.

- **Impact:** a part placed by the left or bottom edge of the area, or in its corners, is judged on errors measured
  mostly by the right edge and the top; the area may be larger, or need to be smaller, there. An upright plate a
  little off the middle row is a Warning, to be moved and scanned again.
- **Not fixed here:** only rig captures can tell (capture-checklist.md, 3d: plates along the area's left and
  bottom edges and in its four corners, clean and stained fronts and backs; plates cut by the frame's border and
  foreign objects cut by it, for the outside-area Warning). If the plates there measure within half of every
  tolerance, the insets stand, or shrink where they allow.
- **Pinned by:** `test/Vision/Utilities/test_classify.py::test_only_an_object_wholly_inside_the_inspection_area_is_judged`,
  `test/integration/test_edge_of_view.py`, `test/integration/test_pipeline.py::test_each_frame_gets_its_expected_verdicts`.

## The live preview runs at about 3.7 frames a second, set by the USB-C Ethernet adapter

PREVIEW shows the table at about 3.7 frames a second (3.67 measured in the window on 2026-10-16), so a hand placing a
part moves in visible steps. The limit is not the camera (51 fps) but the link: the camera's throughput is held to
10 MB/s (`Camera.Basler.CONST_THROUGHPUT_LIMIT`), the measured ceiling of the USB-C Ethernet adapter it is plugged
into, and a full 1920 × 1200 frame is 2.3 MB.

- **Impact:** the preview is usable for placing parts, not smooth; SCAN from the preview first waits for the frame
  in flight (0.786 s from the press to the frame, against 0.590 s without the preview). Nothing measured or judged
  depends on it.
- **Not fixed here:** a faster preview at this link would need a camera setting that differs between preview and scan
  (binning, a smaller window), which the owner ruled out, and would show something other than the frame the scan
  takes. A dedicated gigabit network card for the GigE camera would allow a much faster preview without changing any
  camera setting; revisit then (design-decisions.md, *The preview's frame rate is the GigE adapter's, not the
  camera's*, has what to raise and re-measure).
- **Pinned by:** nothing automated (a property of the network hardware); `Example/Camera/preview_check.py` measures it.

## A plate cut more than any measured could read as a foreign object

Outside the inspection area an object the verdict rule does not identify resembles the part only when its similarity
is at least 0.657, its mean saturation at most 76.3 and its visible extent at most 73.6 mm
(`Classify.Resembles_Part`; design-decisions.md, *A foreign object is told by what it is, not where it lies*).
The most cut plate measured, a stained front 88.5 mm out with a corner off the right border (`20261016-070632_8`),
scored 0.668, 0.011 above the threshold. A plate with less of it in view (only a corner) was never measured and may
score under it.

- **Impact:** such a plate would read `State: Warning – Foreign object.` and be told "It is not the part … remove it
  from the surface" instead of `Warning – Outside area.` and "move it fully inside the area", and be recorded with
  `warning_kind` `foreign`; it is drawn in the amber either way (one colour for every Warning), its
  verdict is a Warning either way, and the operator moves it either way.
- **Not fixed here:** only captures can tell: plates cut by each border with less and less of them in view
  (capture-checklist.md, 3d), and foreign objects of the plate's grey cut by it.
- **Pinned by:** `test/Vision/Utilities/test_classify.py::test_an_object_resembles_the_part_by_the_rule_or_outside_by_every_position_free_cue`
  (the cut-plate case).

## A stained front by the edge of the view reads "does not look like the part"

DINOv2's similarity of the fingerprinted front to the front reference falls with its distance from the frame centre:
0.81–0.89 within 30 mm, 0.67–0.78 at 50–67 mm, mostly below `Identify_Similarity` (0.75). There it is NOK for its stains, with
its side and holes right, and its reason adds "It has the part's outline but does not look like the part" (captures
`20261015-170251_s1` frames 12, 13, 15, 18, 19, 20 and `20261015-143622_s1`). The rule is deliberate (an object of the
part's shape that does not look like it is NOK, design-decisions.md).

The drop below 0.75 is the stains', not the position's (capture `20261015-180933_s1`, 2026-10-15): five clean fronts
58–62.5 mm out score 0.83–0.87 (0.92–1.00 near the centre) and read OK with no such clause; a stained front at the same
place scores 0.69. The position takes about 0.1 off a clean front; the stains take the rest.

Most of those plates lie outside the inspection area and are Warnings, whose reason does not carry the clause; inside
the area a stained front still scores down to 0.73 (`20261015-170602_4`, 52 mm out) and still gets it.

- **Impact:** the verdict is right; the clause says the stains make the front look unlike its clean reference, which is
  true, in words written for a foreign object. A clean front by the edge does not get it.
- **Not fixed here:** nothing to fix in the identification; a separate wording for a judged part whose stains were
  found could follow, if the owner wants one.
- **Pinned by:** nothing: the clean fronts that pinned the clause's absence lie outside the inspection area, where no
  reason carries it, and the stained fronts' clause is not pinned.

## The capture sets of 2026-10-29 are stamped one hour ahead

Every capture set of 2026-10-29 records a `timestamp`, and a set id, one hour later than its files' modification times
(3,599 to 3,601 s, all 28 sets of both sessions, AnyScan-Media archive, captures/20261029-142803_s2 and
captures/20261029-143904_s1). The station's screenshots of that day show the same clock. The likely cause is a
station still on summer time after 2026-10-25, in its time zone or in its clock. Which of the two is not known: the
station was not checked yet.

- **Impact:** read a set's time, its set id and the session log of that day one hour back before comparing them with
  any other record. If only the time zone is wrong, the daily station event export's UTC `ts` is still right. If the
  clock itself is wrong, `ts` is one hour off as well.
- **Not fixed here:** it is a setting of the station, not of the code. Checking the station's time zone and clock
  against a reference tells which, and a fix there leaves only the sets written before it affected.
- **Pinned by:** nothing: no test can see the station's clock.
