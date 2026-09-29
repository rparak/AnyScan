# Design decisions

The reasoning behind the non-obvious choices in the vision port, so the next person does
not undo them. Each entry states the decision, the reason, and what would justify
revisiting it. This is the counterpart to [`KNOWN_ISSUES.md`](../KNOWN_ISSUES.md), which
records open behaviours, and to README > Limitations, which records the two limitations that
affect decisions; this file records deliberate choices whose motivation is not visible in the
code. A change that contradicts one of these should cite
why the reason no longer holds.

## The label mask is black ground, tinted fill, verdict contour

The exported mask paints a black ground, fills each object with a **tint of its own box
colour**, and outlines it in that box colour. Black ground keeps every silhouette edge sharp.
The fill was white until a tint replaced it, because white made the silhouette and its coloured
box read as two things. A tint of the box's own hue makes them read as **one object**.

**The first tint was a token on paper only.** It mixed the box with 80% white in sRGB and landed
on near-white: the neutral fill `#F1F2F4` was ΔE 4.7 from white — the white it replaced — with
the outline only ΔE 19.5 away; the OK fill was ΔE 13.2 from white at a sixth of the box's
chroma; and sRGB mixing drifted NOK's hue 22°.

**Why they stayed near-white for so long: a test enforced a constraint that was never real.**
`test_theme` asserted `_lum(fill) > 0.75` "so a dark numeral reads on it". But the index numeral
sits on its chip, which is filled with the box colour, and never touches the fill. The test pinned
the fills pale, every later check passed against it, and the near-white looked like a settled
decision rather than a side effect. The change below is therefore a correction, not a change of
taste: the false constraint is removed and replaced by floors that describe what a fill actually
has to do. The fills are now built in LCh with the box's hue held:

| | box | fill | ΔE box↔fill | ΔE fill↔white | vs black ground |
|---|---|---|---|---|---|
| OK | `#6C63B5` | `#E2E0F0` → **`#B4AADB`** | 59.4 → 33.6 | 13.2 → 39.0 | 9.7:1 |
| NOK | `#ff005c` | `#FFCCDE` → **`#FC929C`** | 74.7 → 46.8 | 24.6 → 51.1 | 9.7:1 |
| neutral | `#B8BECA` → mask outline **`#767C87`** | `#F1F2F4` → **`#C0C6D2`** (derived pair) | 19.5 → 27.9 | 4.7 → 21.3 | 12.2:1 |

OK and NOK share L\* 72 at about half their box's chroma, so only hue separates them, as with
the boxes; their mask outlines are their boxes (L\* 46 and 54, darker than the fills), so they
never had the neutral's convergence problem and were checked and left as they are.

**The neutral mask has its own derived pair — a light fill and a darker outline.** The first
correction kept the frame's box (`#B8BECA`, L\* 76.85) as the mask outline; the ΔE 25 outline/fill
floor then forced the fill down to a dark grey (L\* ~50), which read too dark. The box needs its
lightness on the frame, over the green table and the parts, but on the mask the outline only ever
meets the fill and the black ground. So the mask gets its own neutral outline, darker, which frees
the fill to go light (`Theme.Neutral_Mask_Colors`, `Detection_Mask_Outline`); the annotated frame
keeps `#B8BECA`. The pair is derived in the box's own hue and chroma and no longer depends on the
box's lightness:

- the **fill** is as light as the fill/white floor allows. For a near-neutral of chroma C\*,
  ΔE to white is √((100 − L\*)² + C\*²), so ΔE ≥ 21 needs L\* ≤ 100 − √(21² − C\*²) = 80.12
  here; less the 0.5 margin (and hex rounding), the fill is `#C0C6D2` at L\* 79.75;
- the **outline** sits at the midpoint of its window [48.88 (4.5:1 against black), fill − 25] =
  [48.88, 54.62]: `#767C87`, L\* 51.86. ΔE(outline, fill) 27.9, fill 12.2:1 and outline 5.0:1 on
  black.

**The fill/white floor is 21, and why.** It exists for one failure: a mask fill that reads as
white — which `#F1F2F4` did at ΔE 4.7. It was set to 25 for one round, and 25 capped the neutral
fill at L\* ~75 (the outline/fill floor was never the constraint: with the outline near L\* 50 it
stays at 28–30). Previews at L\* 80 and 85 settled it: L\* 80 (ΔE ~21 from white) still reads
clearly as grey, including at full size on the previous test set's `Image_001` (`f5cd075^`; a visual
check, not re-done on `All/`); L\* 85 (ΔE ~16) starts drifting back toward
the white that was removed. So 21 is a chosen margin with L\* 85 as the point where it starts to fail
visually, not a measurement limit — `Theme.CONST_MASK_FILL_MIN_WHITE_DELTA_E` carries this note so it
is not rounded back up. Every point above 21 costs neutral fill lightness. The pair re-derives from
the floor; the outline's window is now 5.74 L\* wide and closes only if the floors change.
the floors change (not the box), and then Theme raises at import naming the window.

The floors
(`Theme.CONST_MASK_FILL_*`, in the parameters layer because Theme derives with them) are stricter
than the general ΔE 12 because a thin outline must
stand out against the fill it crosses: ΔE box↔fill ≥ 25, ΔE fill↔white ≥ 21, ≥ 4.5:1 against the
black ground, and a chromatic fill within 5° of its box's hue at ≥ 40% of its chroma. The OK/NOK
box↔fill ΔE went *down*: that is the cost of a fill that is actually a colour, and both stay well
above the floor. When classification is off the fill is the neutral one, implying no verdict
nobody made.
**Revisit if** the operator-facing mask needs to encode something other than verdict (e.g.
per-class colour), in which case add a mode rather than overloading the default.
Tests `test/Parameters/test_theme.py::test_label_mask_fill_is_a_visible_tint_of_its_box` (fails
on the old values: "OK: fill #E2E0F0 reads as white"),
`::test_neutral_mask_pair_is_derived_light_fill_and_darker_outline` (the bounds and the pair's
margins), `::test_neutral_mask_pair_ignores_box_lightness_and_fails_loudly_on_floors`,
`::test_white_floor_rejects_what_reads_as_white_and_admits_the_l80_fill`,
`test/Vision/Utilities/test_annotate.py::test_label_mask_fills_each_object_with_a_tint_of_its_box_colour`,
`::test_detect_only_label_mask_fills_with_the_neutral_tint`, `test/UI/test_harness_parity.py`.

## `#ff005c` is the fail marker and must stay the NOK colour

The EDIH-DIGIMAT brand magenta `#ff005c` reads as a fail marker at a glance, so it is the
**NOK** verdict colour — exactly what that quality makes it good for. **Revisit only** if
the verdict scheme itself changes; do not repurpose the magenta as a decorative object
colour or swap it for a calmer red, because its fail-lookalike quality is the point.
Commit `3494ba3`; test `test/Parameters/test_theme.py::test_verdict_colour_comes_from_the_one_constant`.

## The colour-name saturation cutoff is 120, and was not tuned for the red block

The model-free describer calls a pixel "coloured" only above HSV saturation 120
(`Describe_Fallback.CONST_COLOR_SAT_MIN`); below it the object reads as grey/metal. 120
sits in a real gap. It was set on the previous test set (`f5cd075^`: metal up to S=98,
saturated colours from S=184, a pink-red block at S=121) and re-measured on
`Data/Images/Test/All` (2026-09-28, median saturation per object): metal, plastic and white
parts 2–78 (the dark plates 17–41), the blue parts 168–189, and the red block 124 and 143 —
still the one tight case, now 4 points above the line in `All/Image_006`. The field is decided
by a per-pixel majority vote, not the median, which is more robust than any median-based
cutoff, and lowering the line to "protect" the red block would only move the tightness toward
the metals. So it stays at 120. **Revisit
if** new captures show real coloured parts clustering in the 98–184 band; the honest fix
then is a better colour feature, not a nudged threshold.
Commit `62c5097`; tests `test/Vision/test_describe_fallback.py::test_weak_metallic_cast_reads_grey_not_blue`, `::test_red_straddling_the_hue_wrap_votes_red_not_blue`.

## Objects are not all routed through FastSAM to complete the confidence metric

The `Confidence (mean)` status field only has a score for objects FastSAM found; a
background-cue-only object carries none, so the field shows the mean over exactly the
scored objects **with its coverage** (`87% over 5 of 9`) and `—` when none are scored, rather
than averaging over a partial set. It is tempting to force every object through FastSAM so
the metric is complete, but the fusion exists precisely because neither cue is sufficient:
forcing them through means lowering thresholds until FastSAM sees them (which admits false
detections) or a second region-prompted pass (which roughly doubles the slowest stage) —
changing *detection* to populate a *status* field. **Revisit by** giving the
background-subtraction cue its own confidence (normalised change magnitude or mask-edge
sharpness) so every object scores from whichever cue found it; until then the coverage
fraction is the honest disclosure.
Commit `4407c87`; [`KNOWN_ISSUES.md`](../KNOWN_ISSUES.md) "confidence status metric is partial"; tests `test/UI/test_status_metrics.py::test_confidence_denominator_is_the_scored_count_not_the_total`, `::test_confidence_is_no_value_when_no_object_has_a_score`.

## The fusion needs both cues — the previous test set's `Image_001` proved it in both directions

Detection fuses FastSAM instance masks with OpenCV background subtraction: an object
survives on **either** cue. This is not redundancy. On `Image_001`, objects 2 and 9 came
back with background-subtraction coverage `cov=0.00` — the background cue missed them
entirely and FastSAM carried them — while the `cue = background` objects (four of nine)
had no FastSAM mask at all and were carried only by background subtraction. Dropping either
cue loses real objects. **Revisit only** if a single cue is shown to cover every object
across a representative set of frames, which today's evidence contradicts.

*Re-measured 2026-09-25:* only one direction still shows on the repository frames. With the
current pipeline `Image_001`'s nine objects are 4 `both` + 5 `fastsam`: FastSAM still carries
objects the background cue misses, but no object is background-only, on `Image_001` or on the
other six frames (one `both` object each). The "four of nine" above is that run's figure, not
today's. This does not meet the revisit clause: seven frames, six with one object, are not a
representative set, and the tests hold the background-only path. The entry stands. The
background-only direction now rests on the original run, not on a frame in the repository.

*Re-measured 2026-09-28 on the current test set* (`Data/Images/Test/All`; the frames above are the
previous set, removed in `f5cd075`, recoverable from `f5cd075^` — names there do not match `All/`): 44
objects, 41 `both` and 3 `fastsam` (one each in `All/Image_001`, `007` and `013`), none background-only.
The FastSAM-only direction is sharper than before — the dark rusted plate in `All/Image_013` is 2 % seen
by the background cue — and the background-only direction still rests on the original run. The entry
stands.

*Re-measured 2026-09-28 on the eight frames left after `2d163a6`* removed `All/Image_009`–`013`
(recoverable from `2d163a6^`): 37 objects, 35 `both` and 2 `fastsam` (the blue double triangle in
`All/Image_001`, the lattice bracket in `007`), none background-only. The 2 % plate was in `013` and is
no longer in the set; the FastSAM-only direction rests on the triangle and the bracket. The entry stands.
Commit `fe4f10c`; tests `test/Vision/Utilities/test_fusion.py::test_object_seen_only_by_fastsam_survives`, `::test_object_seen_only_by_background_survives`.

## The closing never joins two components

Stage 3 splits the fused cues into connected components FIRST and closes each one on its own
(`Vision.Utilities.Fusion.__Close_Within_Components`): the closing still fills gaps and notches inside
a component, but a pixel it adds reaching two components goes to neither, and two components that
were separate before the closing are never one object after it. `Segmentation.Fusion.Close_Kernel`
stays 15.

**Why.** Closing the fused mask as a whole joined any two parts less than the kernel apart: in the
test set as it then was, `All/Image_010` and `013` (removed in `2d163a6`, recoverable from `2d163a6^`),
two plates 10.8 and 9.8 px apart came back as one object. That was a bridge with no reason behind it,
and a smaller kernel would only have moved the distance at which it happens. Across all twenty real
frames then available (the thirteen of `2d163a6^` and the previous seven) the closing
healed nothing — every count was the same with no closing at all — and with the new rule every other
object's mask is identical pixel for pixel, the lattice bracket and the maze plate included. 010 and
013 then counted two. Cost: fusion ~25 ms slower per frame. The trade-off is stated: a part the cues see
as two separate pieces now stays two objects (KNOWN_ISSUES, the fusion entry's failure signatures) —
not seen on any frame.

The other three touching pairs (009, 011, 012) merge before the closing and are not fixed by this;
the five routes tried for them are recorded, with why they fail, in KNOWN_ISSUES (*Touching parts
merge before the closing*). With 010 and 013 out of the set, no frame in `All/` exercises the rule: it
is pinned by the synthetic test below alone.

**Revisit if** a real part comes back as two objects because its cues see it in pieces — then the
bridge it needs is evidence-specific (e.g. both pieces inside one FastSAM mask), not a kernel.
Tests `test/Vision/Utilities/test_fusion.py::test_the_closing_never_joins_components_that_were_separate`,
`::test_the_closing_still_fills_a_gap_inside_one_component`,
`test/integration/test_pipeline.py::test_counts_match_the_inventory` (slow; the eight frames, none of
them with near parts).

## The annotated view is the exported render, not live Qt painting

The Camera View shows the same image the harness exports (`Draw_Annotated` /
`Draw_Label_Mask` rendered off the result and handed to the viewport), rather than boxes
painted live in Qt. The old live painter cycled base palette colours and so disagreed with
the mask's colours object-for-object, which defeats a toggle meant for comparison; sharing
one renderer makes the on-screen annotation byte-identical to the export and keys each
object to the same colour in both views. **Revisit if** the UI needs interaction the raster
cannot give (hover, per-object selection, live zoom overlays), in which case reintroduce Qt
painting but drive its colours from the same `Theme` tokens so the two cannot drift.
Commit `5461678`; test `test/UI/test_camera_view.py::test_switching_view_does_not_invoke_the_pipeline`.

## Staleness clears the result rather than marking it

When the frame changes (a new scan, a disconnect, Clear), the held analysis renders are
dropped and the annotated/mask toggle is hidden, rather than kept and marked as belonging
to an earlier frame. Showing a previous frame's annotations over a new scene is the one
genuinely misleading failure here — the outlines would not line up and nothing on screen
would say so — and clearing is unambiguous where a "stale" badge invites the operator to
keep reading a mismatched overlay. **Revisit if** a use case needs to compare an old
analysis against a new frame side by side, which would call for an explicit two-pane
compare, not a marked-stale single view.
Commit `5461678`; tests `test/UI/test_camera_view.py::test_a_new_scan_makes_the_result_stale_and_hides_the_toggle`, `test/UI/test_threading.py`.

## `strip_background` binds `surface` to a background noun instead of matching the word

**Superseded — the strip is removed** (see "The background strip is removed, not retuned"). Kept
for the record of why it was built the way it was.

The background-stripping deletes a sentence only when it is *about* the background —
requiring a background noun (`background`, `backdrop`, `table`, `tablecloth`, `cloth`,
`felt`, `mat`, `desk`, `floor`, `sheet`) or a colour bound to one — rather than deleting
any sentence containing `surface` or a colour word, as the prototype did. The bare word
matched legitimate object description ("the surface of the plate is machined", "a green
plastic terminal block") and threw it away; `surface` in particular is a weak noun that
only strips when it is colour-bound or locative, so "the surface is shiny and reflective"
about a milled plate is kept while "a green surface" is stripped. Every strip and
substitution is logged to the audit, so over-stripping is visible, not silent. **Revisit
if** captions show a background noun the list misses (extend the list, with a kept/stripped
test pair) — never by widening back to bare word-matching.
Commit `47be425`; test `test/Reporting/test_core.py::test_strip_background_noun_binding`.

## A failed analysis writes a PARTIAL capture set, on purpose

On a completed analysis the capture set is the raw frame, the annotated image, the label
mask, the Scene-Understanding `.txt` and the YOLO `.txt`. When an analysis FAILS — the
segmenter raises, the weights are missing, the pipeline throws — the annotated image, the
mask and the YOLO records do not exist, because they are produced only *after* a
successful analysis. But the raw frame does exist, and it is the most useful artefact in a
failure (it is the frame that caused it). So a failure writes a **partial set**: the raw
frame plus an `_understanding.txt` note saying the analysis failed and only the raw frame
is present, and the failure is logged as an ERROR tagged with the set id that names the
directory. The missing annotated/mask/YOLO files are therefore expected for a partial set,
not an incomplete implementation — reading them as a bug is the mistake this note exists to
prevent. **Revisit if** a future pipeline renders the annotation before it can fail, in
which case a failed set could carry the annotation too.
Commit `44be4a6`; tests `test/UI/test_logging_coverage.py::test_mid_analysis_failure_tags_the_error_and_writes_a_partial_set`, `test/UI/test_capture.py::test_a_write_failure_raises`.

## The YOLO `<set>.txt` ids are per-frame indices, NOT classes — do not train on them

Each analysis writes a YOLO region file, `<set_id>.txt`, one line per object
(`<class_id> <x_center> <y_center> <width> <height>`, normalised 0–1). The boxes come from
the same ordered detection list that drives the numbering, the mask and the
Scene-Understanding text, so all artefacts describe the same objects in the same order. The
`class_id` is the object's **0-based index in that list** (object 1 in the text → id 0): a
per-frame **handle** for finding the object in the text and hand-correcting it, not a class.
This is the kind of file someone will point a training script at, so state it plainly:
**these files must not be used for training as-is.** The same id means a *different* part in
every frame, so a class built from them is an arbitrary mix; a `classes.txt` beside the
captures lists the ids in order (currently the per-frame object indices) and carries the
same warning in its own header, so the caution travels with the data. They become a real
dataset only once ids are reassigned by actual class. **Revisit when** classification
exists: the id then comes from the class, and this note is rewritten — the id stops being a
per-frame handle and becomes a real label.
Commit `44be4a6`; tests `test/Reporting/test_core.py::test_yolo_lines_are_normalised_and_indexed_from_the_object_list`, `test/UI/test_capture.py::test_yolo_file_holds_the_given_lines_and_classes_has_a_header`.

## The three confidence figures have one home each, at three different scopes

Confidence appears in three places, and they will show different numbers at the same time,
so each has exactly one home and one scope:

1. **Per object** — the object's own score (`Detection_Str.Segmenter_Score`), on its label
   in the Scene-Understanding panel (`Object 1 · Confidence 91%`) and in the descriptions
   `.txt` (both from the shared `Reporting.Object_Confidence`).
2. **Per frame** — the mean over *this frame's* scored objects, in the panel's foot table
   (`Confidence (mean)`), with coverage shown when the frame is only partly scored
   (`87% over 5 of 9`) so it reconciles against the object list directly below it
   (`AnyScan_Window_Cls.__Frame_Confidence_Text`).
3. **Per session** — the mean over *every scored object in every analysis* since the session
   began, in the status strip (`Confidence (session mean)`), beside the session-median
   inference time.

The status figure **accumulates individual object scores across analyses**
(`AnyScan_Window_Cls.__session_scores`) and divides by their count — it does **not**
recompute the current frame, and it is **not** the mean of the per-frame means. Per-object
weighting is deliberate: a nine-object frame and a one-object frame must not count equally,
which the mean of frame means would do. The status labels name both the scope and the
statistic (`session median`, `session mean`) precisely because these scopes differ — a
label that implied "session" while computing the frame is the class of bug where the UI
looks right and quietly says something false (it existed: the status confidence recomputed
the frame mean under a session label). Coverage stays out of the status bar (it lives in the
log and the frame table). **Revisit if** a fourth scope is wanted (e.g. a rolling window of
the last N analyses): add it as its own cell with its own scope in the label, never overload
an existing one.
Commit `5191b73`; tests `test/UI/test_status_metrics.py::test_frame_mean_and_session_mean_are_over_their_own_scopes`, `::test_session_mean_weights_each_object_equally_not_each_frame`, `test/UI/test_reading_view.py::test_object_blocks_carry_the_shared_label_and_description`.

## Segmentation polygons keep only the outer contour, and the set carries a JSON record

Each analysis writes `<set>_seg.txt` (YOLO segmentation) beside `<set>.txt` (YOLO boxes): one
line per object, `<class_id> x1 y1 …`, normalised 0–1, the class id the same per-frame object
index as the box file (the same not-a-class caveat applies — do not train on it as-is). The
polygon is the contour of the SAME per-object mask that fills the label mask, simplified with
`approxPolyDP` at an epsilon proportional to the contour's own perimeter (`CONST_SEG_APPROX_EPS_FRAC`),
so a raw 1920×1200 contour of thousands of points collapses to a few dozen — an unsimplified
file is unusable. **Only the OUTER contour is kept** (`cv2.RETR_EXTERNAL`, largest component):
an object with holes — a washer, the lattice bracket — is written as a single ring, its holes
dropped, because YOLO segmentation is one ring per instance and the downstream consumers assume
it. A maskless object (found by the background cue alone) falls back to its bounding box as a
four-point rectangle, so the seg file has one line per object in the same order as the boxes.
**Revisit if** a consumer needs holes (then emit multi-ring polygons and record the winding),
or if the fixed epsilon fraction proves too coarse for the smallest parts.

The set also carries `<set>_objects.json` — the one machine-readable record, built from the same
detection list as everything else: per object the index, pixel box, confidence, cue, verdict and
description; set-wide the session id, timestamp, frame size, task, inference time and frame mean
confidence. **No view parses `_understanding.txt`** — that file is prose for humans; History and
any other reader use the JSON. A `<set>_thumb.jpg` (~320 px long edge) is written once from the
annotated image so History never decodes full PNGs to fill its grid. **Revisit if** History needs
a field the JSON does not carry — add it to `Build_Set_Metadata`, the single builder, so the file
and the reader stay in step.
Commit `157eabe`; tests `test/Vision/Utilities/test_annotate.py::test_seg_keeps_only_the_outer_contour_for_a_holed_object`, `test/UI/test_history_data.py::test_metadata_round_trips_and_matches_the_detection_list`.

## Classification is a per-configuration switch that exposes the verdict UI, not one that creates it

`General.Classification.Enabled` in the configuration file says whether a configuration performs
OK/NOK classification or only detects objects. It defaults to **false**, because nothing
classifies today — no code assigns NOK; `Detection_Str.Verdict` defaults to OK and nothing sets
it otherwise. So enabling the switch does **not** make classification work: with it on, today's
behaviour is filters visible, every object OK, the NOK filter permanently empty. That is a
deliberate, shippable state — the config is ready for a classifier that does not exist yet.

**Enabled** shows verdict state: the Captures OK/NOK filter, verdict colours on annotations, and
the verdict per object wherever object detail is shown. **Disabled** removes all of it — the
filter is not there (removed, not disabled, so nothing on screen implies a feature this
configuration lacks), objects are annotated in a single neutral colour (`Theme.Detection_Color`,
a distinct token from the verdict colours — 'detected, not judged'), and the UI speaks only of
detected objects.

The flag is read **once**, through the one configuration layer
(`Camera.Utilities.Configuration.Read_Classification_Enabled`), with the single default living in
`Parameters.General`; the launcher passes it to the window and logs it on the configuration-loaded
line, which is the answer when someone asks why the UI has no OK/NOK. It governs what LIVE
produces (annotation colours, and the flag recorded on each new capture set) — **not** History.

History lists only the **current application run** (see the run-scope entry below), and the flag is
read once at startup, so every set in a run shares it — there is no mixed history. The Captures
filter appears when **the run classifies**, and each set's outline still follows its **own recorded
flag** (`_objects.json` keeps it as the record, so an earlier set shown by some future cross-run
view would still carry its own colours). Object rows always show the record — suppressing a
captured verdict would lie about what was captured. The earlier mixed-history handling (the filter
shown by scanning sets, and a "not classified" per-card marker) was removed with run scoping,
since it can no longer arise.

**Two empty-NOK states are kept distinguishable:** config disabled ⇒ the filter is absent (its
absence is the answer); config enabled with no classifier ⇒ the filter is present and says why it
is empty ("no classifier is running yet, so no object has been judged"), the reason being the
missing classifier, not the config.

**Revisit when** a classifier lands: it sets `Detection_Str.Verdict`, the empty-NOK message stops
being the normal state, and the switch starts gating a feature that actually runs.
Commit `c34983e`; tests `test/Configuration/test_core.py`, `test/UI/test_history.py::test_the_two_empty_nok_states_are_distinguishable`, `test/Vision/Utilities/test_annotate.py::test_verdict_colored_false_draws_one_neutral_colour_not_verdicts`.

## History shows only the current run, identified by a run id

The window generates one **run id** at startup (a UUID, stable across every camera connection in
that run) and writes it into each set's `_objects.json`. History lists only the sets whose run id
matches the current one; earlier runs' sets stay on disk and retention still manages them, they
simply are not shown. The run is identified by this **explicit id, not by comparing timestamps** —
a timestamp scheme breaks the moment the clock is adjusted, and a run can span several camera
connections (each its own on-disk `session`), which one id spans and a per-session scheme would
split. Before the first analysis the grid shows a short muted message ("No captures in this run
yet. Analyse an image to begin."), not a blank panel. See the next entry for what "session"
and "run" each mean.
Tests `test/UI/test_history.py::test_history_lists_only_the_current_run`, `::test_empty_run_shows_the_run_scoped_message`.

## Vocabulary: "session" is a camera connection; UI figures run since start or last Clear

**Session = camera connection = the UI's "Connection".** The logger's session bookkeeping, the
capture directory names (`<timestamp>_s<N>`) and the run-summary CSV's `total_session_time` all
count **camera connections**. In the UI a connection
is called a **Connection** — the History grid headers, the Info panel, and the Log view's prose
lines ("Camera connected. Connection 1 started.", "Connection 1 ended after …", "Created the
capture directory for connection …"). The Log is UI and speaks the UI's words. The CSV is a file
format: its `total_session_time` column name is a data contract that its rows carry, so it stays.

**Three spans, named precisely** — they differ on purpose, and each is labelled for what it is:

- **Status-bar aggregates and the Trends charts: since the application started or the last
  Clear.** The UI calls this the **run** ("Inference (run median)", "Confidence (run mean)", the
  charts' "Run mean" line); Clear resets these figures and both charts together, because they read
  one accumulator.
- **History: the application run**, identified by the run id in each set's `_objects.json`. Clear
  does not hide sets; History shows every set written since the application started.
- **The run-summary CSV: one row per application run** — its time account (cycle, connected
  and idle time), which Clear does not touch.

So after a Clear, the status bar and Trends restart while History and the CSV do not. That is the
intended behaviour, not a counting bug.
**Revisit if** the capture directories are renamed, at which point "session" can leave the code
too; the CSV column keeps its name regardless.

## Trends: one accumulator, a hand-drawn chart base, and no failed image on the x axis

The Trends view (Live · Trends · History · Log — named for what it shows: both charts are
running values over the run's images, not summary statistics) draws two charts: cumulative
detected objects (Total, plus OK/NOK when the run classifies), and confidence (one dot per scored
object, the frame mean, the running run mean, dashed 80%/60% lines at the §5 thresholds).

- **One accumulator** (`Reporting.Trends.Trends_Accumulator_Cls`, Qt-free) feeds both charts
  *and* the status bar's IMAGES ANALYSED, OBJECTS DETECTED and run-mean confidence, so the last
  point of each series is the status figure by construction, not by two paths agreeing. It spans
  **since the application started or the last Clear** (Clear resets it), not the whole application
  run — History covers that (see the vocabulary entry).
- **A failed analysis does not advance x.** It is not an analysed image, and the accumulator is
  only fed successful analyses, so the last x and IMAGES ANALYSED agree either way.
- **Unscored objects are not plotted.** A dot at 0% would be a false low-confidence reading; the
  hover shows how many objects in that image were left off.
- **Hand-drawn with QPainter, not matplotlib.** matplotlib is installed (via ultralytics), but a
  small Qt chart base matches how the rest of the UI is drawn, takes its colours and type sizes
  from the theme by construction, and keeps a plotting library out of the UI layer. Both charts
  share one base (`UI.Views.Trends.Chart_Base_Cls`) for axes, gridlines, legend and hover; the
  maths that such charts usually get wrong (1/2/5 × 10ⁿ ticks on **both** axes, value→pixel
  mapping, the hover hit-test, x-label thinning onto round numbers) is pure and unit-tested.
- Neutral confidence dots use the detection colour's **ink** twin (`#5C6270`): the box value
  `#B8BECA` is tuned for drawing on the green frame and nearly vanishes on the white card.

**Revisit if** a chart needs zoom/pan or thousands of series points, which is where adopting a
charting library starts to pay for itself.
Tests `test/Reporting/test_trends.py`, `test/UI/test_trends_view.py`.

## `verdict_colored` has no default, and the harnesses read the flag like the app

`Draw_Annotated` and `Draw_Label_Mask` take `verdict_colored` as a **required, keyword-only**
argument. It used to default to `True`, and two callers that never read the configuration fell
back to it silently: `Example/Vision/analyze.py` painted OK-verdict boxes and the OK tint
(`#E2E0F0`) on a detect-only run, and `Example/UI/screenshot.py` (since removed) built its window detect-only but
rendered its `demo_*.png` beside it in verdict mode — two modes in one run. A default is a
rendering mode chosen on the caller's behalf; with none, a caller that has not decided fails at
the call site, and the keyword makes a bare `True`/`False` impossible to pass without naming it.
Both harnesses now read `General.Classification.Enabled` through the application's own
`Read_Classification_Enabled` and default config (`analyze.py --config` overrides it), because
`analyze.py` validates the logic the app uses — a harness rendering in another mode would make a
harness artefact look like a real difference. **Do not reintroduce a default.**
Tests `test/UI/test_harness_parity.py` (the harness mask equals the mask the window writes, for
both flag values; the harness uses the app's config reader; the renderers reject an unstated mode).

## The configuration sets the camera's sensor window

`Camera.Resolution` (`x`, `y`) and `Camera.Offset` (`x`, `y`) — 1920 × 1200 centred at (8, 8) on the
a2A1920-51gcPRO's 1936 × 1216 sensor — are REQUIRED, and `Basler_Cls` sets them on every connect
(offsets to 0, then the size, then the offsets: the camera caps each by the other) and reads all four
back. The read-back window, exposure, gain and pixel format go into the session log on connect.

**Why.** `Camera.Resolution` already existed: it was loaded into the configuration and never read.
Only `Custom_Cfg` reached the camera, and no code had ever set `Width` / `Height`. The camera ran at
whatever it last remembered; the 1920 × 1200 frames came from a setting made outside the application
and never saved to a user set, and a power cycle returned the camera to its factory default, the full
1936 × 1216 sensor (found 2026-09-24, when a frame stopped matching the 1920 × 1200 reference). A
missing field is honest; **a field that looks authoritative and does nothing is how someone concludes
the sensor is pinned when it is not** — the same class of error as the hardware-id constant below that
duplicated the configuration's, and removed for the same reason. Giving the existing field the job,
rather than adding `Width` / `Height` beside it, keeps one source.

**The dependency runs one way.** Configuration → camera (set on connect) → data validated against the
configuration at load: a background reference of another size fails the load naming both sizes, and a
calibration solved at another window fails it too — K's principal point and the mm/px factor are in
that window's pixels. The camera never reads its size from the reference: that would make the hardware
follow a picture on disk, and swapping the reference would silently reconfigure the sensor. The check
at the grab (a delivered frame of another size) and the one at ANALYZE stay as safety nets, not the
first line of defence. `calibrate.py` records the read-back window in `capture.json` and in the
calibration it writes, refuses to extend a capture set taken at another window, and the writer refuses
a calibration that does not record its window.

**Centred, (8, 8).** Symmetric about the lens axis; trims the sensor's border evenly. The old frames'
window position is unrecoverable (the empty mat has no texture to register against), and both the
calibration and the background reference are being re-shot, so there was nothing to match back to.

**Temporary leniency.** The calibration in force predates recorded windows, so an absent window is a
WARNING that names the risk (measurements may be wrong by an unknown amount), not a load failure —
blocking live use over a calibration being replaced that week would gain nothing. **Once the
multi-view recalibration is in force, make an absent window a load failure**; the code beside the
warning (`Configuration.Core.__Read_Calibration`) says so.

**Revisit if** the camera changes (another sensor makes 1920 × 1200 at (8, 8) wrong — the window
belongs to the hardware, in its mode files); a measurement ever needs the 16 px per axis the window
trims; or the read-back ever catches the camera not keeping the window, in which case persist it in a
user set on the camera as well, instead of only setting it on connect.
Tests `test/Configuration/test_core.py` (the window's validation, the reference and calibration
checks, the writer's refusal), `test/Camera/test_basler.py` (the set order against a stand-in with the
camera's constraints, the read-back, the log line, the grab check), `test/Calibration/test_core.py`
(the window in `capture.json` and in the written calibration).

## The background reference carries its provenance; harnesses capture through the app's path

A reference is made by `Example/Camera/make_reference.py` from a capture set of the empty table: it
copies the set's `_raw.png` byte for byte and writes `Image_Background_NNN.json` from the set's own
records — the window the camera read back (capture sets now record it: the offset is not in the
pixels), the fingerprint of the lens model that undistorted the frame (from the set's undistortion
record, a SHA-256 over K and the coefficients), the configuration, the camera, lens and lighting,
the time and the source. Nothing in it is typed by a person. `Load_Configuration` checks the reference
against it: the image must match the sidecar's SHA-256, and the window, lens model and lighting must be
the configuration's; any mismatch fails the load.

**Why a sidecar, not the size check alone.** Size cannot tell two frames of one size apart: not the
window's position, not the lens model that undistorted it (a reference is an undistorted frame, so a
recalibration puts it out of date), not the light it was shot under. And provenance belongs with the
file: the configuration says which reference to use; only the file can say how it was made.

**The guarantees are not equal.** The window and calibration checks are structural — both sides are
recorded by the software. The lighting check compares `Camera.Lighting` with the lighting the
configuration named when the reference was made: two fields a person types. **It fires only when
someone updates `Camera.Lighting`; whoever changes the lamp and not the configuration gets no warning.**
That gap is real and stays until lighting is measured rather than named.

**Temporary leniency, twice.** A reference with no sidecar loads with a WARNING (the reference in force
predates sidecars), like a calibration with no recorded window. Both paths say beside them in the code
that they become load failures once their reason expires: the recalibration in force, and a reference
made by the tool in force (checklist item 2).

**`scan.py` goes through the application's camera path.** It undistorted frames without the
application's processing step, so its frames were not what the pipeline sees — and it is the harness
someone would reach for to shoot a reference or grab a test frame. The same class of defect as
`analyze.py`'s `verdict_colored`, made required so a harness could not render differently from the app.
`scan.py` now captures with `Camera.Core.Basler_Camera_Cls` (window, processing, undistortion), and
says in its docstring and output that its frame carries no provenance and is not a reference.
`calibrate.py --capture` keeps its own path on purpose — it needs frames before undistortion — and
applies the application's processing profile to them.

**Revisit if** lighting becomes measurable (a reading from the lamp or a light meter could replace the
typed `Camera.Lighting` and close the gap above); references are shared between cameras (the checks
would then need the hardware id as well as the window); or a reference ever has to come from
something other than a capture set.
Tests `test/Configuration/test_core.py` (the sidecar checks), `test/Camera/test_reference_harnesses.py`
(the tool against sets built with the application's record builders; `scan.py` against a stand-in).

## A replaced image never keeps its name

The failure mode, recorded because it has now happened four times: **when an image is replaced
rather than added, everything keyed to its filename silently re-points at the new image.** A test, a
note, a measured number or a capture record that names `Image_004.png` does not know the bytes
changed; it goes on citing, asserting or loading whatever now carries the name.

1. **The first renumbering.** The frame committed as `Data/Image_006.png` became `Data/Camera/Image_001.png`
   and later `Data/Images/Test/Image_001.png` (one blob, three names); notes written against the old
   numbers pointed at different images. A clone at the old commit still has them under the old names.
2. **`f5cd075` deleted the seven test frames and added thirteen others under the same names.**
   `All/Image_001` is not the old `Image_001`. The tests' pins (`Image_001` → nine objects, `Image_004`
   → one plate) looked for the old names in the old folder, found nothing and *skipped* — two tests
   tested nothing from then on, and nothing said so. Measured evidence citing `Image_002–005` cited
   frames that no longer existed.
3. **`f5cd075` overwrote `Data/Images/Background/Image_Background_001.png`** with a new reference
   shot under the new calibration. Capture sets record the reference by path
   (`_objects.json` `background_reference`), so every set made before then names an image it was
   not differenced against.
4. **`2d163a6` removed `All/Image_009`–`013` and left their pins in place:** the five inventory counts
   and the strict xfails on 009, 011 and 012. The xfails expected an `AssertionError`, and a missing
   frame raises one, so three of the five read as expected failures; only 010 and 013 failed, and only
   under `--runslow` with the weights. Not a replacement, but the same failure: the name outlived the
   frame, and the pins did not follow the set.

**What held.** The reference's sidecar records the image's SHA-256 and the fingerprint of the lens
model that undistorted it, and `Load_Configuration` checks both: a reference swapped under an old
sidecar fails the load, and one shot under another lens model is refused. The overwrite in (3) came
with a new sidecar, so it loaded — correctly — but no other image in the project carries its content
identity, which is why (1) and (2) went unnoticed.

**So:** a replacement image is added under a **new name** (`Image_Background_002`, the next frame
number, a new folder) and the old one is removed only with everything that cites it updated in the
same change. Where a name must identify content, record the content (a SHA, as the sidecar does), not
only the path. A pinned frame that is missing fails its test; it never skips. **When a test set changes,
its inventory and its pins are part of the same change** — the default run now fails when the inventory
and the frames in `Evaluation.Frames` disagree, without the weights. An expected failure must not expect
the error a missing frame raises.

**Revisit if** frames or references get a content-addressed store or a manifest with hashes — then the
name stops being the identity and this becomes a property of the store.
Tests `test/Configuration/test_core.py::test_a_reference_replaced_under_its_sidecar_fails_the_load`,
`test/integration/test_pipeline.py::test_counts_match_the_inventory` (slow; a missing frame fails),
`::test_the_inventory_names_every_frame_of_the_test_set` (the inventory against the folder).

## The run-summary CSV is named after the loaded configuration

`logger/log_<id>.csv` takes `<id>` from the configuration file the run loaded
(`Config_<id>.yaml` → `log_<id>.csv`, `Logger.Core.Csv_Filename_For_Config`). It used to come from
a hardware-id constant in `Logger/Core.py` that duplicated the id already in the config filename
— two sources of truth, and loading a different YAML would have appended that camera's runs into
the other camera's summary: silent, and corrupting the data rather than failing. `App/run.py`
now holds one `config_path` and passes it to the logger, the classification reader and the
config-loaded log line. `config_path` is required on `Session_Logger_Cls` (keyword-only, no
default), for the same reason `verdict_colored` is; `None` is an explicit "no configuration"
and writes to `log_unconfigured.csv`, which belongs to no hardware. **A configuration change
therefore starts a new CSV** — different hardware, different summary, which is the intent. The
shipped config produces the existing name, so current files continue unchanged.
Tests `test/Logger/test_core.py::test_csv_filename_follows_the_loaded_configuration`,
`::test_logger_requires_the_configuration_to_be_stated`.

## Run-summary CSV: six time-account columns; an older format is archived, never appended to

The CSV is cut to `log_file, application_start, application_stop, cycle_time, total_session_time,
idle_time` — the run's time account: when the application ran, for how long, how much of that a
camera was connected, and how much it was idle (`cycle_time == total_session_time + idle_time`
exactly, every duration derived from the whole-second values the row prints). Counts, errors,
confidence and inference figures, the run id, the Clear count and the JSON detail cells are gone;
the `.txt` log beside each row still records every event, and the capture sets carry the per-image
figures.

**An older file is renamed aside, not appended to.** Every file written before the cut carries the
22-column header, which is not a prefix of the six, so the old header-extension path cannot apply.
Appending six values under the 22-column header (the extra cells empty) would make one file whose
rows mean different things depending on when they were written. Instead, when the file at the
canonical name has any header other than the current columns, the logger renames it — byte-for-byte
unchanged — to `log_<id>_until_<date>.csv`, the date its last row was written (`_2`, `_3` if that
name is taken), and the canonical `log_<id>.csv` starts afresh. A reader looking for "the log"
finds the live one; history sits beside it under a name that says what it is. The `.txt` log of
the run that archived it says so. The check and the rename run under the file lock, and a run
that waited while another archived the file re-checks the file now at the path, so two runs
closing together cannot both archive or write into the archived file.

This one rule replaced the header-extension path (rewrite the header in place when it is a prefix)
and the align-and-warn path (realign a row to a mismatched header) — the most intricate code in
the logger, which existed to solve the problem this rule removes. Any future change of columns
archives the same way.

**Reading an archived file.** Its rows are the old 22 columns. Their `session_details` and
`error_details` cells are compact JSON arrays (`[{"index":1,"start":"2026-09-22 20:18:38.412",…}]`)
from the commit "Run-summary CSV: encode session_details and error_details as JSON" onward, and
legacy colon-joined entries before it — a JSON cell begins with `[`, a legacy one with a digit. A
legacy cell splits on ` | `, each entry matching
`^(\d+):(\d{2}:\d{2}:\d{2})-(\d{2}:\d{2}:\d{2}):(\d{2,}:\d{2}:\d{2})$` (sessions) or the same
followed by `:(.*)$` (errors: id, start, end, duration, message).
Tests `test/Logger/test_csv_archive.py` (an older file archived unchanged and a new one started, for
22- and 14-column files; a current file appended with either delimiter; an earlier archive never
overwritten; the row is the time account), `test/Logger/test_core.py`.

## Object measurement: mm per pixel, our own angle convention, and a symmetric case with a square exception

Each masked object is measured from the minimum-area rotated rectangle of its mask
(`Vision.Utilities.Measure`), converted through `Camera.Calibration.Conversion_Factor`.

- **The factor is millimetres per pixel.** The YAML labels it `[mm/px]`, and the calibration
  derives it as `square_size_mm / mean corner spacing in px`
  (`Calibration.Core.__Get_Pixel_To_MM_Factor`) — so `mm = px × factor`, per axis. Two physical
  cross-checks agree: 1920 px × 0.098 ≈ 188 mm field width, and K's focal length 3886 px × 0.098
  mm/px ≈ 381 mm working distance. Nothing applied the factor before this; it is read once through
  `Read_Conversion_Factor`, passed as a `Scale_Str` (required, keyword-only, like the classification
  flag) to the vision backend, and recorded with its units at capture-set level. **No factor means
  no measurement**, with a WARNING on the configuration-loaded line — never a size from a default.
- **Per-axis conversion, pixel-centre correction.** Each side's pixel vector is converted with its
  own axis factor before its length is taken. Contour points sit on pixel centres, so a filled
  200 px block spans 199 px between its boundary pixels; one pixel is added to each side, or every
  size would read ~0.1 mm short.
- **The angle convention is ours, not OpenCV's:** the long side's direction from the image +x axis,
  counter-clockwise *as seen on screen*, in [0°, 180°) — computed from the rectangle's corners, not
  from `minAreaRect`'s angle, whose convention changed between OpenCV versions. A test pins
  +30° → 30, −30° → 150, 181° → 1.
- **Precision from the scale.** *Superseded 2026-09-28 (next entry):* sizes were rounded to one
  pixel's size, `floor(−log10(mm/px))` decimals — 0.098 mm/px → 0.1 mm — when measured, so the stored
  value was rounded too. The recalibration to 0.10208 mm/px tipped that to 0 decimals, and sizes were
  stored and shown in whole millimetres with nothing to flag it.
- **Rotationally symmetric parts report a diameter and no angle.** `minAreaRect` assigns a round
  part an orientation that changes on noise, so a drawn rectangle would appear to spin on a part
  that has not moved. The test is elongation — the square root of the mask's second-moment
  eigenvalue ratio — below **1.15**: the thirteen frames `Data/Images/Test/All` held on 2026-09-28
  (`2d163a6^`) put round parts at 1.002–1.016 and the least elongated non-square part at 1.468 (the
  robot in 005; the plates 1.49–1.60). Re-measured on the eight left after `2d163a6`, every figure
  holds except the plates, 1.49–1.54. **A square is the exception:** it is as un-elongated as a
  disc (1.013, the maze plate in `All/Image_008`) but its sides are real edges that `minAreaRect`
  finds reliably, so un-elongated parts are only called symmetric when also round — extent (contour
  area / rectangle area) below **0.92** (round parts 0.777–0.809, the square 0.983). The set has one
  square part, in one frame.
  A square keeps A × B and an angle folded to [0°, 90°), since its sides are interchangeable. A
  round part's diameter is the mean of the rectangle's sides; a hexagonal one reports across flats
  (next entry).
- **Camera View drawing.** A measured, elongated object is drawn twice in its one verdict colour:
  the rotated rectangle **solid** at the full box weight (the measurement) and the axis-aligned box
  as a **thin dashed** line (now only the reference that carries the number chip) — solid versus
  dashed reads as "measurement" versus "reference" where two weights alone could read as one
  confused shape. Symmetric and unmeasured objects keep the single solid axis box; the label mask
  is unchanged.

**Revisit if** a part family needs orientation modulo 60° (hex). See README > Limitations: the
sizes are repeatable, not absolute, and stand unverified against parts of known size.
Tests `test/Vision/Utilities/test_measure.py`, `test/integration/test_pipeline.py::test_symmetric_parts_measure_as_diameters_on_real_captures` (slow).

## Sizes keep full precision; only the display rounds, to a fixed two decimals

`Vision.Utilities.Measure` stores `Width_Mm`, `Height_Mm` and `Diameter_Mm` as computed, and the
`_objects.json` record carries them unrounded (no `decimals` key; an older record's key is ignored).
One function rounds, for display only: `Reporting.Core.Object_Size`, to `CONST_SIZE_DECIMALS = 2`
(`X.XX mm`, `Ø X.XX mm`, `A/F X.XX mm`) — the Live and History labels, the `.txt` lines and the
harness all go through it. Nothing that computes, stores or compares a size sees the rounding.

**Why.** The decimal count used to be derived from the scale, applied at measurement. The
recalibration moved the factor from 0.098 to 0.10208 mm/px, `floor(−log10(…))` went from 1 to 0,
and every size became whole millimetres — coarser at the moment the lens model got better, with no
warning. A value whose meaning changes when the calibration moves is worse than a fixed constant.
**Displayed precision is now finer than measured precision:** the second digit is below one pixel
(0.10 mm) at the current factor, and a size already carries a position-dependent error of up to
about 1.5 mm near the frame edge (README > Limitations). Two decimals are a formatting choice — not
improved resolution, and not a reason to go back to a derived count.

**Revisit if** a size is ever compared or tolerance-checked as text, or the display needs to state
its own uncertainty (then show it, rather than trimming digits to imply it).
Tests `test/Vision/Utilities/test_measure.py::test_stored_size_keeps_full_precision_while_the_displayed_text_is_rounded`.

## Symmetric parts: round ones report Ø, hexagonal ones report across flats (A/F)

A hexagon's across-corners width is 2/√3 = 1.155 × its across-flats, so one hex nut has two
standard "diameters" 15 % apart, and the mean of the rotated rectangle's sides — the round-part
convention — lands between them and matches neither. A nut is specified by its across flats (the
wrench size), so a hexagonal symmetric part reports that, and the label names the convention:
`A/F 11.7 mm` beside a round part's `Ø 14.7 mm`. The two can never be read as the same kind of
number.

- **What counts as hexagonal.** The part's caliper (Feret) width is sampled over 180° from its
  convex hull; a hexagon's repeats every 60°, so its third harmonic is strong. *Hexagonality* is
  that harmonic's amplitude over the mean width, and **0.0075** is the threshold. Measured on
  `Data/Images/Test/All` (2026-09-28; 9 round and 6 hexagonal instances of 4 washer/bushing and 2
  nut parts): round 0.0010–0.0028, nuts 0.0114–0.0290 (lower than an ideal hexagon's 0.038–0.057
  because the masks round the corners), pixelated ideal discs ≤ 0.0021 down to 24 px across. 0.0075
  sits between the closest washer (0.0028) and nut (0.0114) — 2.7× and 1.5× from each; the small nut
  in `All/Image_005` is the tightest case. The synthetic cases (discs and hexagons at several sizes
  and rotations) are the wider net.
- **Only the 60° harmonic.** A general "polygonal" test (any harmonic 3–8) fails on this data:
  the washers' own masks are slightly squared circles, with 4-fold components up to 0.0121 (the
  white washer in `All/Image_008`) — stronger than the threshold. Square parts never reach this branch anyway (their extent excludes them).
- **Across flats is the smallest caliper width**, converted through the factor along its own
  direction. It is also the robust choice here: the masks clip the nuts' corners (their widest
  caliper width is 1.055–1.121 × their across flats on `All/`, not 1.155), which pulls a mean or an
  across-corners number but not the flats. When the convention was introduced (on the previous test
  set, `f5cd075^`) the two nuts moved from Ø 12.0 to A/F 11.7 mm and from Ø 11.6 to A/F 11.5 mm — much
  less than the theoretical 7.5 %, for exactly that reason.
- **Stored.** `_objects.json` records `across_flats` and `hexagonality` (null when the part is not
  symmetric). A record written before this convention has no `across_flats` and reads back as a
  round Ø, which is what it was measured as.

**Revisit if** another polygonal family appears (an octagonal part would need its own harmonic and
its own evidence), or if the nuts' measured A/F disagrees with a caliper by more than the position
and thickness effect in README > Limitations explains.
Tests `test/Vision/Utilities/test_measure.py` (`test_hexagonal_part_reports_across_flats`,
`test_a_disc_of_any_size_is_round_not_across_flats`, label and stored-record tests),
`test/integration/test_pipeline.py::test_symmetric_parts_measure_as_diameters_on_real_captures` (slow).


## Capture sets keep the frame before undistortion, marked as distorted

Every capture set's `<set>_raw.png` is the frame **after** undistortion with the calibration in
force when it was taken ("raw" means unannotated, not undistorted). A frame undistorted with one
calibration cannot be cleanly re-measured under another: it would have to be re-distorted and
re-undistorted, resampling twice. So a set now also keeps `<set>_distorted.png` — the same frame,
processed identically (the same blur and colour step), before undistortion — whenever the camera
undistorts, together with a `<set>_distorted.json` sidecar that:

- says `"distorted": true` and, in words, that the lens distortion is not removed, so the two
  files cannot be mistaken for each other;
- names its undistorted counterpart;
- records the exact undistortion that produced `<set>_raw.png`: the configuration file, the frame
  size, K, the coefficients, `alpha` (1) and the new camera matrix.

The PNG and its sidecar are written together or not at all. A saved-frame camera (`--frame`) does
not undistort, so it provides no original and nothing distorted is written — never the undistorted
frame under the distorted name. The camera clears the original before every grab, so a failed grab
cannot pair a new frame with the previous frame's original. `keep_raw` governs both frames; the
retention estimate rises from ~8 to ~12 MB per set (~600 MB at 50 sets).

**Why now:** the calibration is about to be redone, and a frame kept only undistorted is tied to the
lens model that undistorted it; the original can be re-undistorted under whichever calibration ends up
in force.
Tests `test/UI/test_capture.py` (`test_distorted_frame_is_kept_with_a_sidecar_saying_so`,
`test_no_distorted_frame_without_one_and_it_is_evicted_with_its_set`),
`test/UI/test_logging_coverage.py::test_the_scanned_frames_distorted_original_reaches_the_capture_set`,
`test/Camera/test_core.py::test_distorted_original_belongs_to_one_frame_only`.

## Calibration captures: distorted, all kept, flat and tilted named apart

`Example/Camera/calibrate.py --capture DIR` captures calibration frames one key press at a time:
`f` for a board lying **flat on the table**, `t` for a **tilted** (or raised) board, `q` to stop.

- **Distorted, and said so.** Each frame is the camera image after the application's own
  processing step and before undistortion — a lens model can only be solved from distorted frames.
  A `capture.json` manifest beside them states `"distorted": true`, how they were produced (the
  processing profile, the configuration, the camera settings), and one record per frame, so no
  reader mistakes them for the application's undistorted `<set>_raw.png`.
- **Every frame is kept.** A frame where no board is found is reported and recorded with the
  reason, never deleted: a discarded pose cannot be re-examined, which is exactly what went missing
  when the image behind the original single-view calibration was not kept.
- **Kind in the name, one running number.** `flat_NNN.png` feeds the lens model and the mm/px
  factor; `view_NNN.png` feeds the lens model only. Numbers run across both kinds and continue after
  whatever the directory holds, so a second session never overwrites the first.
- **Partial boards are detected.** `findChessboardCornersSBWithMeta` with `CALIB_CB_LARGER` returns
  the visible part of a board that overhangs the frame (at least 4 × 3 inner corners); the classic
  detector the old calibration used needs the whole board. The sub-pixel refinement is the
  detector's own `CALIB_CB_ACCURACY`: on six noisy, perspective-warped synthetic boards it gave a
  mean corner error of 0.031 px, against 0.041 px without it; running `cornerSubPix` afterwards made
  it worse (0.051–0.079 px), and `CALIB_CB_NORMALIZE_IMAGE` cost 0.22 px, so neither is used.

Tests `test/Calibration/test_core.py`.

## Calibration: many views solved together, the factor from flat boards' undistorted corners

The calibration in force came from **one** chessboard image. A single, near-frontal view cannot
separate the principal point from the board's position (a shifted principal point and a translated
board give the same image), and the optimiser put it ~800 px from the image centre. The factor was
then taken from that image's raw, distorted corners and applied to undistorted frames.
`Calibration.Core` now solves over a set, and `Example/Camera/calibrate.py` is only its harness:
`--capture DIR` records frames, `--images DIR` solves them.

- **All views feed the lens model; only flat views feed the factor.** Every detected image goes into
  one `cv2.calibrateCamera`. The factor comes only from `flat_*` images (boards lying on the table),
  from their corners **undistorted into the application's own pixel space**
  (`getOptimalNewCameraMatrix` with the camera's `CONST_BASLER_UNDISTORT_ALPHA`) — the space every
  measurement happens in. Each adjacent-corner pair gives square² = (dx·sx)² + (dy·sy)², linear in
  (sx², sy²), so a board at any rotation on the table fixes both axes. **No flat view detected is an
  error**, never a fallback to tilted boards; the report counts the views of each kind.
- **Failures are per image.** An unreadable file, a frame with no board, or a grid larger than the
  board is named with its reason and skipped. A view that reprojects at more than 2× the set's
  median is named as a bad capture to retake or exclude.
- **What is reported,** because this is where single-view calibration goes wrong: per image the
  kind, the visible grid and corner count, the reprojection error and the tilt; the overall RMS; the
  **principal point** with its offset from the image centre in pixels and as a fraction of the
  frame; the tilt range and the count of views tilted ≥ 10°; the distortion coefficients and how far
  they move the frame's corners and edge midpoints; the undistortion's rescale of the focal length;
  and the factor with its spread across the flat views and over a 3 × 3 map of the frame.
- **The tilt warning is set from a recovery curve, not picked.** `Example/Camera/calibration_tilt_study.py`
  solves synthetic sets (a camera close to ours, 0.03–0.2 px corner noise). With 12 views at 0.1 px:
  all flat 45 / 100 px principal-point error (median / 90th percentile; at 0.2 px noise 94 / 614 px —
  the stored calibration's failure) and 18 % focal error; tilts spread up to 2° 4.8 px, 3° 3.1 px, 5°
  2.1 px, 8–45° 1.5–1.6 px. By count, with the rest flat: one view tilted 10° 22 / 49 px, two
  2.8 / 6.8 px, three 2.3 / 4.4 px, six 1.4 / 2.5 px. So the warning fires below **three views
  tilted ≥ 10°**, the first point on the plateau in both sweeps. More flat views do not help: the
  all-flat row is the same however many there are.
- **What tilt does not buy.** The factor's uniformity across the frame is set by corner noise and view
  count, not tilt: 0.149 % at 6 views, 0.085 % at 12, 0.057 % at 24, 0.039 % at 40 (0.1 px noise).
  A spread above **0.1 %** (one pixel on a ~1000 px, 100 mm part) is reported as position-dependent
  rather than averaged away, with the map — a gradient across it suggests the table is not parallel
  to the sensor. Capture 40+ views. *Corrected 2026-09-25: this said 20+, read from the medians
  alone; at 24 views the 90th percentile is 0.103 %, over the limit on noise alone, and at 40 it is
  0.065 % (see "The printed calibration board stays 11 × 8" below).*
- **Sub-pixel.** The detector's own `CALIB_CB_ACCURACY` refinement; `cornerSubPix` afterwards
  measured worse (previous entry).
- **Square size and reference plane are stated, not assumed.** `--board-squares`, `--square-mm` and
  `--board-height-mm` are required with no defaults, and every result repeats that a printed board
  must be calipered (0.5–1 % printer scaling is the same order as the errors being removed). The
  board's height above the table is recorded with the result: the factor is exact in that plane only.
- **Nothing switches over by itself.** The result is written to a new
  `<config>_calib-<date>.yaml` — the source's header, the new K, coefficients and factor, and a
  `Solved` record (date, image directory, views by kind, RMS, square size, board height). The
  configuration in force is overwritten only with `--write-config`, and the harness says that
  `App/run.py` hardcodes its path, so adoption is a separate, deliberate step after comparing old
  against new.

The old `Checkerboard_Calibration_Cls` is gone, and with it the parameter named `inner_corners`
that actually received the square counts; the board is now given as `--board-squares 11x8`, named
for what it holds.

Tests `test/Calibration/test_core.py` — rendered boards through a known lens: the intrinsics
recovered (principal point within 1 px, focal within 0.5 %); failing images named and skipped; the
tilt warning on an all-frontal set; the factor from undistorted corners within 0.1 % of the truth
where the raw-corner value is off by more than 0.5 % (−1.1 % here); no flat view fails loudly; the new
file written with the source untouched.

## File headers carry JIC Smart Factory; the style's origin credit stays

Every file header now reads `Copyright (c) <year> JIC Smart Factory` (each file keeps its own year:
2023 ×6, 2024 ×1, 2025 ×79) and `Author   : JIC Smart Factory`, aligned with `File Name:`; the
`Email` and `Github` lines are gone. The sweep covered every tracked file — `src/`, tests, examples,
`App/run.py` — and the style skill's header templates (`assets/header.txt` in both forms,
`module_template.py`, `script_template.py`, and the skeleton in `SKILL.md`), because files written
from them are ours. Every `File Name:` line already matched its file's path. There is no root
`LICENSE`, and the style checker's header rule checks only for the MIT block and the `File Name:`
basename, so no author string is encoded anywhere that would fail.
*Corrected 2026-09-26:* there is a root `LICENSE` now — the one the GitHub repository was created
with, carried over when the two histories were joined — and it reads `Copyright (c) 2026 JIC Smart
Factory` like the headers; as created it named Roman Parak, which the sweep above never saw.

**Deliberately unchanged:** the skill's `SKILL.md` and `README.md` lines saying the style is derived
from `rparak/RoLE`, "MIT License, © 2023 Roman Parak". They credit where the style came from, in
another repository; rewriting them would misstate that origin.

## The describer is Gemma 4 E4B, prompted, behind a describer seam

*Evidence from the previous test set* — the seven frames removed in `f5cd075` (recoverable from `f5cd075^`; their names do not match `Data/Images/Test/All`). *Not re-run on the current set: it needs the describer run and its text read. The `Image_NNN` names below refer to that set.*

Stage 4 (the per-object description and the one background sentence) moves from Florence-2 to
**Gemma 4 E4B-it**, the local `models/gemma-4-e4b-it-4bit`. Segmentation stays on FastSAM.

- **What the weights are.** `config.json` says `gemma4` / `Gemma4ForConditionalGeneration`; the
  README names `google/gemma-4-E4B-it` (revision `fee6332`), converted to MLX by
  `mlx-community`. The language model is 4-bit affine (group 64, 3.7 GB packed); the vision tower
  (0.33 GB) and an unused audio tower (0.61 GB) stay bf16. It runs through **MLX on the Metal GPU**
  (`mlx` 0.32.2, `mlx-vlm` 0.7.2, pinned exactly in `requirements.txt` for Apple-silicon macOS —
  the machine that drives the camera), not PyTorch MPS. Measured on the M2 Pro: load ~3.3 s, peak
  5.15 GB loaded and 5.9 GB while generating, 2.1–2.7 s per object crop.
- **The seam.** `Vision.Describers`: every describer answers `Describe(crop, purpose)` with
  purpose `object` or `background` and maps it to its own input — Florence to a task token
  (`<MORE_DETAILED_CAPTION>` / `<CAPTION>`), Gemma to a prompt. The pipeline never sees a token or
  a prompt. `Vision.Core.CONST_DESCRIBER` selects `gemma` (default), `florence` (kept reachable so
  both run over the same frames; `Example/Vision/analyze.py --describer`) or the model-free
  `fallback`, which the weight-free tests use. Each describer loads its runtime lazily.
- **The prompts are data.** `Configuration/Describer_Prompts.yaml` holds the `Object` and
  `Background` prompts, read through `Read_Describer_Prompts`; a missing or empty prompt stops the
  load before the weights are touched — there is no built-in wording.
- **Deterministic.** The weights' own generation config samples (temperature 1.0, top-k 64,
  top-p 0.95). The describer decodes greedily (`temperature=0.0`) with thinking off, so the same
  crop and prompt give the same text: repeated runs, and runs on other threads, were identical.
  A model loaded on one worker thread describes on later ones (measured), which is how the app
  uses it.
- **The Task field names the producer.** The Live Task row and each capture set's `task` record
  what produced the reading: `part inspection` (Gemma), `detailed caption` (Florence),
  `model-free description` (fallback). History shows each set's own value, so older sets keep
  `detailed caption`. `Analysis_Str`'s *default* Task (a reading nothing produced) is still
  `detailed caption`, pinned by `test_vision` and the characterization baseline; left for a
  deliberate decision.

**How the object prompt was chosen** (measured, temperature 0, on the `Image_002` rust-stained
plate, the `Image_007` clean plate and four plastic parts of `Image_001`): the starting prompt
("…explicitly noting any discolouration, stains, rust…") found the rust and did not invent staining
on the clean plate. A softer rewording ("if you can see …") **missed the rust entirely**, and naming
"threads" as a feature made the model report threads that are not there. The shipped wording keeps
the firm "look carefully … name any you find and where", makes "the surface looks clean" an
acceptable answer, asks only for features "you can actually see", asks for the "apparent" material
(the plastic parts come back as plastic, with no machining marks), and says a hole may show the
green surface through it. The background prompt asks for one short sentence naming the surface's
colour and finish ("A deep teal surface presents a uniform, matte finish."); the one-sentence /
20-word validator stays as a safety net.

**Licence: not MIT, not covered by this repository's licence.** The Gemma 4 weights are licensed
under the Apache License 2.0 (https://ai.google.dev/gemma/docs/gemma_4_license). The repository's
code is MIT; the weights are not, and are not redistributed with it: `models/` is gitignored, so
they sit in the working tree but are not in the repository. Anyone shipping them does so under
Apache 2.0's conditions. (Florence-2, while it remains, is MIT.) *Corrected 2026-09-24:* this
entry first said the Gemma Terms of Use, taken from the `license: gemma` tag on the mlx-community
conversion; that tag looks like converter boilerplate — upstream `google/gemma-4-E4B-it` is
`apache-2.0`, and the Gemma Terms of Use state they do not govern Gemma 4 (README > Licence note).

**Revisit if** the comparison over all seven frames (Phase 2) shows the new model worse somewhere;
the Florence path went in Phase 3, and the pipeline class, then `Florence_Vision_Cls`, was
renamed `Vision_Pipeline_Cls`.
Tests `test/Vision/test_describers.py` (with a stand-in `mlx_vlm`: the data-file prompts, greedy
decoding, thinking off, RGB input, loud failures, Florence's token mapping, the Task labels),
`test/UI/test_history.py::test_each_set_shows_the_task_that_produced_it`,
`test/integration/test_pipeline.py::test_pipeline_real_describer_smoke` (both describers, when their
weights exist).

## The background strip is removed, not retuned

*Evidence from the previous test set* — the seven frames removed in `f5cd075` (recoverable from `f5cd075^`; their names do not match `Data/Images/Test/All`). *Not re-run on the current set: it needs the describer run and its text read. The `Image_NNN` names below refer to that set.*

`Reporting.Strip_Background` deleted any object sentence that was *about* the background and
trimmed trailing phrases like "on a green surface". It existed because Florence-2 wrote table
sentences into object captions. Gemma, told to "describe only the part, not the surface it lies
on", wrote **none** in the prompt trials. Its one mention of the surface was part of the object's
own description — the red block's "two circular holes … each appearing to have a passage allowing
a view of a bright green surface through them" — and the strip deleted that whole sentence,
taking the holes with it. A safeguard with no job left and a real cost is removed, not retuned:
the function, its noun lists, its patterns and its test are gone, and `Object_Description` now
only peels a template lead-in and applies the substance substitution.

- **Kept at the time:** the substance substitution (wood / paper / cardboard → metal). The
  seven-frame comparison then confirmed it never fires on Gemma's text, and it was removed too
  (see "The substance substitution is removed"). The background-sentence validator (one sentence, ≤ 20
  words, else the neutral sentence) also stays.
- **Consequence while Florence is reachable:** Florence's captions keep their table phrases
  ("A hex bolt on a green surface."), which is what the comparison should see.
Tests `test/Reporting/test_core.py::test_a_sentence_naming_the_surface_is_kept_whole`,
`::test_describe_object_detail_reading_and_fallback`,
`test/integration/test_pipeline.py::test_pipeline_camera_to_reporting`.


## The label distiller peels Gemma's opener — and the label is still weak

*Evidence from the previous test set* — the seven frames removed in `f5cd075` (recoverable from `f5cd075^`; their names do not match `Data/Images/Test/All`). *Not re-run on the current set: it needs the describer run and its text read. The `Image_NNN` names below refer to that set.*

Gemma opens every description "The object is a …" (all 15 objects of the seven frames), which the
Florence lead-ins do not cover; the distiller cut at " is " and every label — which feeds `type=`
in the log — read `object`. `Reporting.CONST_LABEL_OPENERS` ("the object is", "the part is",
"the object appears to be", …) is now peeled **for the label only**; the object line keeps the
model's full sentence ("The object is a rectangular metallic plate, …").

**The result is still poor, and is reported rather than patched per phrase.** Across the fifteen
objects: usable 5 (circular ring, metallic bolt or screw, rectangular metallic plate, rectangular
plate, and the two washers, cut at "… washer or"); a single adjective 8 (rectangular ×4, small ×3,
flat); wrong 1 (dark blue). The cause is structural: the distiller cuts at the first comma, which
suited Florence's phrasing, and Gemma lists adjectives with commas ("a rectangular, flat plate").
Fixing that by more boundary rules would be tuning a heuristic to one model's style.
**Open:** ask the model for the name directly — a third, short prompt ("name the part in at most
three words") in `Describer_Prompts.yaml`, one more short generation per object — instead of
distilling it from the description.
Test `test/Vision/Utilities/test_caption.py::test_condense_label_peels_gemmas_opener_but_the_line_keeps_it`.

## The label runs up to the head noun (supersedes the comma cut)

*Evidence from the previous test set* — the seven frames removed in `f5cd075` (recoverable from `f5cd075^`; their names do not match `Data/Images/Test/All`). *Not re-run on the current set: it needs the describer run and its text read. The `Image_NNN` names below refer to that set.*

The first opener fix left 8 of 15 labels a single adjective, because the distiller cut at the
first comma and Gemma lists adjectives with commas ("a rectangular, flat plate"). The problem was
the extraction rule, not missing information, so the fix is the rule — not a second generation per
object to ask for a name the sentence already contains. The label is now the noun phrase **up to
its head noun**, which ends an English noun phrase:

- a comma **continues** the adjective run, and **ends** the phrase only when the next word opens a
  clause — an "-ing" participle ("ring, appearing …") or a hedge (`CONST_LABEL_HEDGES`: likely,
  possibly, …);
- " of " is a boundary ("plate of a bright metal"); one word after " or " is an alternative noun
  and goes ("washer or spacer" → "washer"), more words mean " or " joined modifiers and only
  "or <modifier>" goes ("plastic or ceramic component" → "plastic component");
- a trailing past participle of five letters or more goes ("part rendered in …"), but never an
  "-ing" word — many part names end in it (ring, bearing, bushing, housing, fitting, spring; an
  "-ing" rule first turned "circular ring" into "circular") — nor a short "-ed" word ("red");
- the **last** four words are kept, where the noun is.

All fifteen objects of the seven frames: circular ring; somewhat amorphous plastic part (was "dark
blue" — the colour is gone); circular metallic washer; rectangular flat part; white rectangular
plastic component; metallic bolt; roughly octagonal metal washer; circular metal washer; flat
elongated piece; rectangular metallic plate ×2; rectangular plate; rectangular flat piece; small
square metallic plate; rectangular flat plate. Every label ends in a part noun. The vague ones
("part", "piece") are Gemma's own words, and objects 7 and 8 — hex nuts — are "washer" because
Gemma calls them washers: the label is faithful to the text, and the text is wrong there. Known
limit, not special-cased: a bare " in " is not a boundary ("a threaded rod coated in oil" keeps
"coated in oil"). The Florence captions distil as before ("hex bolt", "washer", "two brass
fittings"); the long M6 example now reads "m6 stainless steel screw", and the stranded-"n" quirk
is pinned on a short caption where it still shows.
Test `test/Vision/Utilities/test_caption.py::test_condense_label_takes_the_phrase_up_to_its_head_noun`.

## The substance substitution is removed

*Evidence from the previous test set* — the seven frames removed in `f5cd075` (recoverable from `f5cd075^`; their names do not match `Data/Images/Test/All`). *Not re-run on the current set: it needs the describer run and its text read. The `Image_NNN` names below refer to that set.*

`Reporting.Substitute_Substance` rewrote "wood", "paper" and "cardboard" to "metal" in object
descriptions, because Florence-2 read the concentric machining marks as wood grain. Over the seven
frames it fired once, on Florence ("artwork … a light wood grain pattern", `Image_002`), and never
on Gemma, which names the concentric machining marks for what they are (`Image_004`). A rewrite
rule that never fires leaves a later reader wondering what it is for and whether it is still
needed, so it goes with the model it existed for.

With it gone, the composer rewrites nothing the describer wrote: `Object_Description` returns only
the line (lead-in peeled, capitalisation and stop applied), and `Compose` returns `(objects, note)`
— there is no per-object audit left to return. The analysis audit keeps the background-sentence
records. The characterization baseline does not move.
Test `test/Reporting/test_core.py::test_the_models_words_are_not_rewritten`.


## Florence-2 is removed; Gemma is the only describer

*Evidence from the previous test set* — the seven frames removed in `f5cd075` (recoverable from `f5cd075^`; their names do not match `Data/Images/Test/All`). *Not re-run on the current set: it needs the describer run and its text read. The `Image_NNN` names below refer to that set.*

After the seven-frame comparison (both models on the same crops, the same pipeline, each in its own
process) Gemma was kept: warm, after load, 2.22 s per object against Florence's 1.12 s — the
nine-object `Image_001` 20.6 s against 11.1 s (the 18 s once quoted for Florence included its
load) — for descriptions that do not invent "green lights", "black screws" or "artwork", never
mention the table, and read machining marks as machining marks. Both models were deterministic
word for word (same process, across processes, and with both resident at a 12.9 GB peak). Both miss
the hex nuts (KNOWN_ISSUES).

Removed with it: `Florence_Describer_Cls` and its constants, the Florence caption pass
(`Caption.Describe` — `Vision/Utilities/Caption.py` now holds only the label distiller), the
`florence` choice of `CONST_DESCRIBER` and of `analyze.py --describer` (the flag is gone; `--device`
now sets FastSAM's device only), the Florence smoke test, and `transformers` / `einops` / `timm`
from `requirements.txt` (nothing of ours imports them; `mlx-vlm` declares its own `transformers`;
`torch` stays, declared under FastSAM, whose segmenter imports it). The README, `models/.gitkeep`,
`.gitignore`, `pytest.ini` and the architecture diagram now name Gemma, with its fetch command and
its licence. `models/florence2-large-ft/` on disk is unused and can be deleted.

**Kept on purpose:** capture sets written by Florence keep `task: detailed caption` (History shows
each set's own value); the caption lead-ins (`CONST_LABEL_LEADINS`, Florence's template phrasing),
which Gemma's text never triggers but the label distiller and the characterization baseline still
exercise. The object crop padding, set when Florence described a cut-out part poorly, has since
been measured for Gemma (see *The object crop padding stays at 0.20 for Gemma*). The
characterization baseline does not move.

## Consequence of Gemma via MLX: the application is supported on Apple-silicon macOS only

Choosing Gemma 4 E4B as a 4-bit MLX conversion pins the platform. The describer was run and
measured only on macOS on Apple silicon (Metal): ≈2.2 s per object, ≈9.4 GB peak for the whole
application, word-for-word identical text across runs. Those are the only figures that exist, so
that is the only platform the application is supported on. The README's "Packaging for Windows"
section (a PyInstaller recipe) described a capability that no longer holds and is replaced by a
"Platform" section.

**A correction to the record:** during Phase 1 this was stated as "MLX exists only for macOS on
Apple silicon". That was wrong: `mlx` 0.32.2 publishes Linux (x86_64, aarch64) and Windows (amd64,
arm64) wheels with `cpu` and `cuda` extras. The constraint is therefore *unverified*, not
*impossible*: whether the 4-bit model and `mlx-vlm`'s Gemma 4 code run on those backends, how fast
(a CPU backend would be far slower) and whether the text stays deterministic are unknown.
`requirements.txt` keeps installing `mlx` / `mlx-vlm` only on Apple-silicon macOS, so an install
elsewhere does not pretend to be supported; the describer then stops with a message.

To run elsewhere: MLX's CUDA/CPU backend on that platform, verified and re-measured on the seven
frames; or a PyTorch build of the same model (`google/gemma-4-E4B-it` through `transformers`)
behind `Describer_Backend_Cls`, likewise re-measured; or a different describer. The rest of the
application (Qt, OpenCV, FastSAM/PyTorch, pypylon) is portable. No macOS packaging recipe has been
verified; the application runs from source.

## The caption lead-ins are removed

`CONST_LABEL_LEADINS` held Florence-2's caption template ("In this image we can see …", "The image
shows a close-up of …") and was peeled from the front of every description (`Caption_Sentence`)
and every label. Gemma never writes those phrases, so — like the substance substitution — it was a
rule that never fires, and it goes. Without the peel, `Caption_Sentence` did exactly what
`Clean_Detail` does (tidy whitespace, capitalise, one terminal stop), so it goes too; the object
line and the background sentence are the model's own words, tidied. The label distiller peels only
Gemma's own openers (`CONST_LABEL_OPENERS`). The "stranded n" known issue lived in the lead-ins'
ordering and is gone with them.

**The characterization baseline moved, visibly:** the composer's Florence-style fixture lines keep
their template ("In this image we can see a hex bolt …", "A close-up of a screw …"), and the label
distiller's four Florence-style fixture captions now distil to nonsense ("image shows a
close-up", "can see a washer", "photograph", "this"). That is the correct result of the rule
change; it also shows the harness's fixture captions are Florence's phrasing, which the
application no longer produces.
Tests `test/Reporting/test_core.py::test_the_description_is_kept_as_written_and_only_tidied`,
`test/Vision/Utilities/test_caption.py`.

## Platform: three states — measured, target, not a target

"Supported" and "verified" are kept apart, because "chosen not to support" and "not yet
verified" are different things. The previous entry treated every platform but Apple silicon as
one unverified state; the platforms are now scoped separately:

- **macOS on Apple silicon — supported, measured.** MLX on the Apple GPU (Metal): 2.22 s per
  object warm, 9.41 GB peak for the whole application, output identical word for word across
  runs, processes and memory pressure.
- **Linux — a supported target, unmeasured.** MLX runs there on a different backend (CUDA or
  CPU), and nothing has been run on it: speed, memory and whether the text comes out identical
  are unknown. On Linux `mlx` installs no compute backend by itself — the backend is an extra
  (`mlx[cuda12]`, `[cuda13]` or `[cpu]`) chosen for the machine — so `requirements.txt` keeps
  its macOS-only line, and the Linux line is added with the first measured Linux machine. The
  README gives the install command meanwhile. Becoming *measured* means the same run over the
  `Data/Images/Test/All` frames: time per object, peak memory, word-for-word stability.
- **Windows — not a target, untested.** Nothing known prevents it (`mlx` publishes Windows
  wheels), but it is not supported and has never been tried.

**Determinism is measured, not guaranteed.** Greedy decoding makes the sampler deterministic;
it does not make the arithmetic identical across backends. A different backend can produce
different text through floating-point differences inside the model, so word-for-word identical
output is a measured property of the Apple-silicon build. On any new platform, everything pinned
to exact description text — tests and the characterization baseline — must be re-verified
before it is trusted there.

## Control stylesheets: every state rule names its fill and its label

**Qt resolves stylesheet rules by specificity, not by order.** Specificity counts pseudo-states,
so `QPushButton:hover:enabled` (two) beats `QPushButton:checked` (one) wherever both apply, even
if `:checked` is written later. A rule wins only for the properties it names. Properties it
leaves out still come from whichever rule is next in line.

This broke every segmented control. The shared segment stylesheet had a hover rule that set
only the background (`#f6f5fa`) and a `:checked` rule that set the fill to ink and the label to
white. On a selected segment under the cursor, the hover rule won the background and `:checked`
still supplied the label: **white on `#f6f5fa`, 1.08:1.** Pressing counts as hovering, so a press
on a selected segment failed in the same way. The rules looked correct in the file. The failure
only showed in what Qt painted, and only when someone hovered.

**The rule adopted:** a state rule sets the background *and* the label together, and a hover
rule is scoped to `:checked` or `:!checked`. Then no state can pick up a label colour chosen for
a different fill, whichever rule Qt ranks first. `Tool_Button_Cls` follows the same rule.

**How far it reached:** one rule, in one class (`Segmented_Control_Cls`). It showed up in four
places (view switch, Log filter, Annotated/Mask toggle, Captures filter) only because they share
the class. ANALYZE was the obvious suspect, since it is filled like a selected segment and its
hover rule also set only the background. It measured **11.23:1**. Nothing else on an enabled
button set a competing label colour, so there was nothing to leak. The pattern was a trap that
had gone off in one place, not a bug in every stylesheet. The tool buttons were rewritten as
pairs anyway, so adding a label colour to some state later cannot set it off.

**Measured, not read.** `test/UI/test_control_contrast.py` builds the real window and drives
every control through rest, hover, pressed, focus, disabled, and disabled with the cursor on it.
Segmented controls are measured with a segment selected and one unselected. It renders each state
at 2× and measures the label area's pixels. Two traps for anyone writing such a test:

- In Qt 5.15, `QPushButton` reports hover only after a `MouseMove` while `WA_UnderMouse` is set.
  Setting the attribute alone renders the resting state, and the test passes without testing
  anything.
- A control the app keeps hidden, such as the view toggle before an analysis, can render stale
  the first time. The test shows it first.

Every enabled state is held to **4.5:1**. The lowest is 10.08:1, a focused selected segment.

**Disabled states are exempt from 4.5:1, by decision.** Low contrast is how a disabled control
says it is unavailable. Holding it to 4.5:1 would make it look active. It is held instead to
looking different from its enabled self: ΔE76 ≥ 12 in label or fill, the project's distinctness
floor. It must also look the same whether or not the cursor is on it, so a CONNECT that disables
itself under the pointer stays visibly disabled. The exemption is a named constant in the test
(`CONST_EXEMPT_STATES`) with its reason. Measured disabled values:

| disabled | label on fill | contrast | ΔE to enabled (label / fill) |
|---|---|---|---|
| unselected segment, plain button | `#b6b2ca` on `#ffffff` | 2.06:1 | 59.7 / 0.0 |
| selected segment | `#b6b2ca` on `#2b2455` | 6.87:1 | 29.5 / 0.0 |
| ANALYZE (primary) | `#8983a6` (`CONST_INK_MUTE`) on `#cbc8db` | 2.19:1 | 48.1 / 68.0 |

**Exempt means the fill signals, not that the label disappears.** Disabled ANALYZE first shipped
with a `#f2f1f6` label on its `#cbc8db` fill: 1.46:1, ΔE 5.3 from the enabled label. It was nearly
invisible instead of looking greyed out. It was not a deliberate pairing. Both values arrived as
bare literals in a commit about the Annotated/Mask toggle (`5461678`), with no comment or reason,
apparently each lightened on its own to "fade" the button. The fill already carries the disabled
signal (ΔE 68 from enabled), so the label is now the existing `CONST_INK_MUTE`: 2.19:1, clearly
muted and still readable. The more legible `#6b6590` (3.30:1) was turned down because it would
add a colour to the palette for one state, for little gain. A disabled label should read as
greyed. It should not be the fill's own colour.

Revisit this if a disabled control has no fill change to carry the signal, since then the label
has to do it alone. Also revisit it if the console moves to a different Qt version. The hover
simulation was checked against Qt 5.15's `QPushButton` only, so on another version, confirm the
hovered renders still differ from the resting ones first. The test's self-check fails if they
don't.

## One configuration file per mode, one calibration per camera, decided before the first CONNECT

**The layout.** A configuration is one file per mode on one camera:
`Config_<Hardware>_Mode_<Mode>.yaml`. The hardware comes first so camera-specific data still
separates by camera, and the mode comes after so it stays visible. It holds everything a user
may change without touching code:

- segmentation, fusion and the background reference
- the describer's model, prompts and limits
- the configuration's display name, model set and Task
- the confidence thresholds
- the camera block: acquisition settings, and the camera, lens and lighting as a person names them

Every value that moved into the file from a module constant kept its value. The shipped file sets
each one explicitly, and `test/Configuration` pins them.

**One reader, the whole file.** `Configuration.Core.Load_Configuration` is the **only** reader. It
supersedes the readers named in earlier entries (`Read_Classification_Enabled`,
`Read_Conversion_Factor`, `Read_Describer_Prompts`) and `Describer_Prompts.yaml`. It validates the
whole file and raises once with every problem listed, so a file wrong halfway through is never
applied halfway.

- A **required** field has no default: its absence fails the load, naming it. The required fields
  are the hardware, both model paths, both prompts, the display name and model set, the camera's
  acquisition settings and the background reference.
- An **optional** field takes its documented default and says so in the log.
- A value that is **present but invalid** fails the load. **This strictness is deliberate.** The old
  readers read a non-boolean `Classification.Enabled` as false, and a negative conversion factor as
  "no measurement". Both were silent wrong answers, not tolerance. Do not restore the lenient
  parsing as a bug fix.
- An **unrecognised key** is a warning, because a misspelt optional field would otherwise default
  in silence.

**Calibration lives once per camera, and is optional as a whole.**
- It is in `Calibration_<Hardware>.yaml`, and every mode naming that hardware reads it. With a copy
  inside each mode file, recalibrating one mode would leave the other measuring with a stale scale,
  silently. That is the failure the measurement work exists to prevent.
- A hardware **without** a calibration file loads with a warning to run `calibrate.py`. Frames are
  not undistorted, because the camera passes them through when there is no K. Objects are not
  measured. This is the honest degraded state. It is also what lets `calibrate.py --capture` run for
  a new camera: otherwise the tool that produces calibration would refuse to run without one.
- A calibration file that **exists** must be complete.
- `calibrate.py` writes the calibration file and nothing else. `Write_Calibration` refuses to
  overwrite keys it doesn't own; its predecessor assumed its block was last in the file and rewrote
  everything below it.

**The background reference is stated, never discovered.** `Segmentation.Background.Reference` is
required, and its file must exist. It is the one path checked at load, because the repository
tracks it; models are only checked when they load. The reference decides every
background-subtraction result, and without it the pipeline loses one of its two fusion cues.

The glob (`Image_Background_*.png`) and its highest-index selection rule were **removed**, along
with `--background` on `run.py` and `analyze.py`. They existed to resolve an ambiguity — several
references, which one? — that the field now ends. Two ways of choosing the reference would bring
the ambiguity back, so **do not reintroduce discovery as a convenience**. The reference is logged
beside the calibration on every load and recorded in every capture set.

**Keyed by hardware.** The run-summary CSV is `log_<Hardware>.csv`, which keeps the existing file
name, and two modes share it. That is safe because the row is a time account. The CSV path is fixed
when the logger starts, so the dialog greys out configurations for other hardware; changing camera
means restarting with `--config`.

**Configuration is decided before the first CONNECT, and fixed for the run.**
- CONNECT is disabled until a configuration is loaded: the camera settings, the calibration and the
  models all come from it. ANALYZE requires it too, structurally, not only through the frame it
  needs.
- The application starts with its configuration named but not loaded. The dialog is always used
  once, which makes the choice explicit and means a launch to browse History costs no ~9 s and no
  ~9.4 GB.
- After the first CONNECT, CONFIGURATION is disabled for the rest of the run, including after
  DISCONNECT; changing configuration means restarting. A run's measurements can therefore never span
  two configurations, and nothing ever needs resetting on a load.
- Both disabled buttons carry a one-line tooltip, and a press on either is logged as a refusal.
- The UI speaks of **loading a configuration**. The models are how a configuration is loaded, not
  something the operator chooses. The dialog says what was loaded in a sentence built from the
  configuration's own fields (model set, camera, lens, lighting). Model files, load time and task go
  to the log.

**Lighting is data.** `Camera.Lighting` sits beside `Camera.Model` and `Camera.Lens`, and each
capture set records all three. The describer's colour readings, the background subtraction and the
surface-condition descriptions depend on the lighting, so a capture set that couldn't say what lit
it would be missing something a future comparison needs.

**Models are released before a replacement loads.** A mode that keeps the same weights reuses them
(measured at 0.00 s). A model that changes is released **before** its replacement loads: two
describers would need ~19 GB on a 17 GB machine. The cost is that a failed load must reload the
previous configuration's models to keep it in force, and the failure message says whether it is
loaded. Measured on the real weights:

| Measurement | Result |
|---|---|
| Load on a worker thread | 6.8 s (*Corrected 2026-09-26:* 9.4–10.0 s since the load also warms up the models — see *The first analysis's one-time costs are paid at configuration load*; 6.8 s was the load without it) |
| Analyse on another thread | 5.8 s, with no load stage |
| GPU memory after a failed swap and reload | back at 5.15 GB |

**Past sets are coloured by today's thresholds.** A capture set in History has its confidence
numbers coloured by the thresholds in force **now**, not those in force when it was captured. That
is defensible because the thresholds are a viewing preference. The numbers themselves are stored
unchanged, and each set names its configuration.

Revisit the startup-only rule if a configuration ever has to change mid-run (it would need
per-configuration run data). Revisit the hardware greying if the CSV path is ever resolved at
shutdown rather than at startup.

## The object crop padding stays at 0.20 for Gemma

*Evidence from the previous test set* — the seven frames removed in `f5cd075` (recoverable from `f5cd075^`; their names do not match `Data/Images/Test/All`). *Not re-run on the current set: it needs the describer run and its text read. The `Image_NNN` names below refer to that set.*

**What it is.** `Description.Object_Crop_Padding` pads each object's crop outward by a fraction of
its longer side before the crop is enhanced and described. It was set to 0.20 for Florence-2, which
described a part cut out onto a blank canvas poorly. Padding pulls neighbouring objects into the
crop, which is why the crop is isolated (neighbours replaced by the reference).

It is **not** `Description.Background_Crop_Margin` (0.12). That one crops the empty reference
*inward* for the one background sentence and never touches an object crop. The two were once
conflated, and the Florence history belongs to the padding alone.

**The measurement (2026-09-24).** All seven `Data/Images/Test` frames were run at paddings 0.00, 0.04,
0.08, 0.12, 0.20, 0.28 and 0.36, through the application's pipeline. Each run used a copy of the
shipped configuration with only this field changed, the same loaded models, greedy decoding and 15
objects per padding. A warm re-run of 0.00 and 0.20 reproduced all 45 descriptions word for word,
so every difference between paddings is caused by the padding, not noise.

**The comparison was not neutral.** The describer's prompt was tuned on Image_002 — the rust-stained
plate, the deciding frame below — with crops padded at 0.20. The test therefore favours the
incumbent value. Anyone re-running it, or tuning the prompt again, should read "0.20 wins on the
rust" with that in mind.

**Padding costs no time; there was never a trade-off.** Crop size varied from 119×117 px (a nut at
0.00) to 1617×709 px (the lattice bracket at 0.36), yet the mean time per object stayed at
2.28–2.45 s at every padding. Gemma scales each crop to a fixed input size, so crop pixels never
reach the model's cost. The padding was assumed to have a speed cost it does not have; the only
costs are neighbours in the crop and what the framing does to the description.

- **Surface condition: the rust is named only at 0.20 and 0.36.** Image_002's brown staining is
  plainly visible in every crop. Gemma names it at **0.20** ("brown, earthy-toned stains … in the
  upper section") and at **0.36** ("significant brown discoloration or staining across the top
  edge"). It misses it at 0.00–0.12 ("unevenness", "patina", "signs of handling") and again at
  **0.28** ("slight discoloration … upper section"). The result is deterministic but not
  monotonic: whether the most important condition in the set is reported depends on the framing,
  not on how much context there is (README > Limitations, *The describer is not a defect detector*).
- **Shape.** The hex nut #7 reads as a circular washer or ring at 0.00 and 0.04, and as polygonal
  from 0.08 ("outer hexagonal profile" at 0.12). That is the Florence failure mode in milder form.
  The other hex nut, #8, reads as circular at **every** padding. This is the limitation already in
  KNOWN_ISSUES (*The description and the measurement can disagree*), and the measurement confirms
  padding is not its cause.
- **Naming and material:**
  - At 0.00 the bolt (#6) is "a metallic shaft", the washer (#3) is "light-coloured, possibly
    metallic", and #2's label degrades to "at a central point".
  - At the larger paddings, the terminal strip (#5) turns "metallic … silver" at 0.28 (it is white
    plastic).
  - #7 describes the green table through its hole as "greenish-tinged patina/oxidation" at 0.28 and
    0.36.
  - Image_005 gains "light corrosion" at 0.36.
- **Neighbours in the crop grow; they never reach the text.** Only Image_001 has more than one
  object:

  | padding | lattice bracket #9 | bolt #6 | others |
  |---|---|---|---|
  | 0.04–0.12 | 0.2–2.7% | — | — |
  | 0.20 | 4.7% | 0.7% | — |
  | 0.28 | 8.2% | 2.7% | — |
  | 0.36 | 11.4% | 4.7% | #3 and #4 begin |

  For #9, the pixels left near a neighbour after isolation grow from 211 at 0.20 to 1,061 at 0.36.
  No description at any padding mentions a neighbouring object.

**Decision: keep 0.20.** Smaller paddings save no time, lose the rust and misread a hexagon. Of the
larger ones, 0.28 loses the rust and 0.36 only ties 0.20 on it, with more than twice the neighbour
material in the lattice bracket's crop and new misreadings. Nothing measured beats 0.20. Given how
the rust flips between neighbouring values, choosing between 0.20 and 0.36 on that one frame would
be fitting to noise in the framing, not to an effect.

**Isolation stays, and it leaves ghosts.** At 0.20 it has neighbours to remove (#9, #6). The evidence
cannot retire it even at 0.00: six of the seven frames hold one object, so Image_001 is the only
frame that tests it, and a part whose box is mostly table (the diagonal bracket) can take in a
neighbour at any padding.

The replacement is not invisible. Faint ghost outlines of the neighbouring nuts and the terminal
strip remain where the reference patch meets the real table, because the table in the frame is
lit or shadowed slightly differently from the reference. No description has mentioned one, but a
future prompt or model might. The fix identified — feathering the patch edge into the surrounding
table — is **not built**.

## `Verdict`'s confidence branch stays dormant: a mask score is not a confidence

`Reporting.Core.Verdict` degrades the operator badge to `'Low confidence' / 'warn'` when any
detection's `Confidence` is below 0.35. Nothing sets `Confidence`: the describer (Gemma, like
Florence-2 before it) emits no score, and the FastSAM mask score is stored in the separate
`Detection_Str.Segmenter_Score`. So the branch never fires, and that is deliberate.

**Why.** A segmenter's mask confidence and a detector's or classifier's confidence are different
quantities. Feeding FastSAM's mask score into `Confidence` would silently activate an
operator-visible verdict path: a busy frame with one lower-scoring mask would turn the badge amber
for a reason that has nothing to do with recognising the part. That is a behaviour change dressed up
as wiring. (Moved here from KNOWN_ISSUES on 2026-09-24: it is a decision, not an open problem.)

**Revisit if** a model that scores *what* an object is — a real detection or classification
confidence — joins the pipeline. Populate `Confidence` with that score deliberately and re-check the
0.35 threshold against its distribution; do not point `Confidence` at `Segmenter_Score` as a shortcut.
Tests `test/Reporting/test_core.py::test_verdict_levels` (the branch itself, fed a score directly).

## Analysis requires a background reference; the whole-frame detector was removed

Every path through `Vision_Pipeline_Cls.Analyze` runs stage 1, background subtraction against the
configured `Segmentation.Background.Reference`, which the configuration requires. There is no analysis
without a reference.

**Why.** Until commit `7b1559c` a second detector, `CONST_DETECTOR == 'florence'`, ran Florence-2's
`<REGION_PROPOSAL>` on the whole frame with no reference — the only path that could analyse an
arbitrary image. No code set it (the default was `'fastsam'`), no test exercised it, and it was slower
than FastSAM: an untested branch carrying a capability nothing used. The application, `analyze.py` and
the tests all supply a reference, so nothing regressed. The capability lost is analysing a one-off
image from a camera with no reference capture. (Moved here from KNOWN_ISSUES on 2026-09-24.)

**Revisit if** the application has to analyse images from a camera with no empty-surface reference.
Restoring it means a whole-frame detector ahead of stage 1, the describe-each-box loop and its crop
helper (all recoverable from `7b1559c`'s parent) — and the test the original never had.
Tests `test/Vision/test_analyze_harness.py::test_missing_reference_fails_before_writing_anything`.

## Type: a scale for content, chosen sizes for chrome

Text the analysis produces — the Scene Understanding reading, History's info panel, the Log's rows —
is sized by named tokens on one modular scale (`CONST_TYPE_SCALE` in `UI/Utilities/Style.py`:
`CONST_TYPE_OBJECT_LABEL`, `CONST_TYPE_INFO_BODY`, `CONST_TYPE_LOG` …). Within a view the same content
has one size (the background paragraph and the descriptions share one), and the hierarchy is strict:
heading > label > body > meta. The chrome around it — buttons, pills, status cells, captions, card
metadata, overlays — is sized per widget and is not held to the scale.

**Why.** The content is what a person reads to decide something, and its hierarchy is what makes it
readable: a size is chosen as a step on the scale ("one step down from the label"), so a change
moves a token, and the relative order cannot invert unnoticed. It did once: History's info panel
put its heading below the text it headed until it got its own tokens (commit `9fd3b5c`). Live and
History use **separate** token sets on purpose — Live is glanced at across a workbench and runs large
(descriptions 12.5 pt), History is read up close while comparing two images (10.5 pt) — so the same
description is deliberately a different size in the two views, and tuning one distance cannot move
the other. Chrome was never put on the scale (32 of its `Font()` calls use literal sizes, most off the
scale); holding it to one now would be a restyle of every widget, with no reading hierarchy at stake.

**Revisit if** a chrome element starts carrying content (it then takes a named token), if the
chrome's literal sizes start drifting into visible inconsistency between widgets of one kind (a case
for putting chrome on the scale too), or if Live and History need to show the same text at the same
size (the two token sets would then merge).
Tests `test/UI/test_history.py::test_info_panel_type_hierarchy_heading_is_largest`.

## models/ is out of reach of the installer tests, and the suite fails if it changes

On 2026-09-24 the repository's `models/` was emptied during a working session: the Gemma weights
(5.1 GB) and FastSAM, both git-ignored and so beyond git's reach. On 2026-09-25 it was emptied
again, the 12B included. **Both times it was manual, confirmed by the user:** they deleted `models/`
by hand and put it back themselves. It was not a code problem either time. `logger/` went the
first afternoon, in circumstances consistent with the same manual tidying, but that is not
confirmed. The logs are not recoverable.

The suite was ruled out both times. The second time it was the `models_untouched` fixture below: it
takes the inventory of `models/` before the first test and compares it after the last, so every green
run that session was itself the evidence that the suite had not touched the weights. The first time,
before the fixture existed, it took an investigation: `git worktree remove --force` does not follow a
symlinked `models/`; nothing in the suite, the harnesses or the installer deletes a directory (the
installer's only destructive operations are `rm -f` of its own temporary and `.part` files, replacing
the FastSAM file, and `hf --force-download` over single Gemma files).
Both restores were checked file by file against the manifests in `install.sh`.

**What the investigation did find** is one real exposure, now closed: the installer tests sourced the
real `install.sh`, so `CONST_ROOT` pointed at the real repository until each test overrode it. Every
test did — but by convention only, and a test that forgot would have run the installer's writes
against the real `models/`. That was not the cause, but it is removed by construction rather than by
discipline.

Two measures make `models/` structurally out of reach of the suite, instead of a note asking to be
careful. Neither can stop a manual deletion; the second answers, on the run itself, whether the suite
made one:

- **The installer tests source a copy of `install.sh` inside their sandbox.** `CONST_ROOT` is resolved
  from the script's own location, so the copy's root *is* the sandbox from its first line. Before, the
  tests sourced the real script — `CONST_ROOT` was the real repository — and every snippet had to
  override it; one that forgot would have run the installer's writes against the real `models/`.
- **The suite fails if `models/` changes.** A session fixture in `test/conftest.py` takes the inventory
  (every file and its size) before the first test and compares it after the last; a removed, added or
  resized file fails the run, naming it. The rest of the suite only reads `models/` (the model loads,
  when the weights are present), so there is nothing further to prevent — but a repeat is now attributed
  to the run that caused it, immediately.

**Revisit if** the guard ever fails (it then names the run and the files), or if a test ever needs to
write under `models/` (it must use its own `tmp_path`, and the guard would fail it otherwise).
Tests `test/Install/test_install.py::test_the_sandboxed_script_resolves_its_root_to_the_sandbox`; the
`models_untouched` fixture in `test/conftest.py` runs with every session.


## The architecture diagram is generated from the theme, carries the real logo, and is linked from the README

`images/anyscan-architecture.svg` went 111 commits without an update, because nothing linked to
it. It still showed the old "AnyScan-VLM" wordmark, the stages as a chain, a mask-filter stage
that no longer exists, and the Summary field retired in the very commit that added it. The new
diagram draws only what the code does: the two cues side by side into the fusion, what each
stage hands on (the cue attribution, the Enhanced_Crop, the background sentence), where each
configuration section enters, the shared formatter and renderer, and the import layers with the
Qt-free boundary. It now sits at the top of the README, where a stale diagram gets noticed.

*Updated 2026-09-27: redesigned as a top-level overview.* The aim is that a reader sees in a
few seconds what AnyScan is and how it works; the detailed version (class names, configuration
sections, import layers) repeated what README > Detection logic and Source layout already say. It now shows six blocks only: capture, find objects
(the two cues fused), describe and measure per object, the desktop app with its four views,
and the configuration under the stages it sets. It carries the JIC mark (as in the top bar) and
the EDIH-DIGIMAT mark on the funding band, both embedded from `App/assets/` as base64 PNG, so
the SVG stays self-contained. The wording is held to the real limits: the describer describes
objects (no defect or pass/fail claim), and the measurement is "in mm, when the camera is
calibrated" with no accuracy adjective (README > Limitations).

*Updated 2026-09-28: what sets the stages up, and what a run leaves behind.* The single
"Configuration" block said one YAML file per camera and mode sets up every stage. That stopped
being true when the calibration moved to its own file per camera, and it never showed the
reference background, without which no analysis runs. The row under the flow is now a "set up
by" group of three cards. Configuration. Calibration: optional, and it gives the undistortion
and the mm/px. Reference: required. That split is the loader's. A missing calibration file is a
warning (`__Read_Calibration`), and the frame is then not undistorted and nothing is measured. A
missing reference fails the load. Capture says the frame is undistorted "when calibrated", in
the passive: the software does it after the grab (`Basler_Camera_Cls._Grab`), not the camera. A
Records card under the app shows the capture sets, the run CSV and the session log, because
History and Log are views of those records. The flow itself is unchanged.

"Optional" is the code's rule, not the rig's. The reference's sidecar records the calibration it
was undistorted with, and the load refuses a mismatch. With the committed reference, removing
the calibration therefore fails the load. The card states the general rule. This entry states
the coupling.

**Revisit if** the calibration becomes required (the card says "optional"), or if a stage, an
input or a record is added or removed: the diagram draws each one.

- **It is generated, not drawn: regenerating is the way to change it.**
  `Example/UI/architecture_diagram.py` writes it. The colours come from `Parameters/Theme.py`, and
  the type scale and font fallbacks from `UI/Utilities/Style.py`. The generator is what ties the
  figure to the palette. A hand-edited SVG would drift the moment the theme moved, the same
  failure as the hand-copied ink value and the duplicated hardware id. The font fallback lists
  were moved out of `Load_Fonts` into `Style.CONST_FONT_UI_CANDIDATES` /
  `CONST_FONT_MONO_CANDIDATES` for the same reason: otherwise the generator would have carried its
  own copy of the font stack.
- **Two tests guard the SVG, and each does a different job. Keep both.**
  - `test_the_diagram_is_the_generators_output` compares the whole committed file with the
    generator's output (`--check` does the same from the command line). It is the stronger guard:
    it catches any hand edit (a colour, text, layout) and a theme change nobody regenerated for.
  - `test_the_diagram_draws_only_theme_tokens` catches only a colour that is not a token. It
    overlaps the first test but is not redundant. Its failure names the offending colour, whereas
    the whole-file test only says "stale or hand-edited". That clearer message is its remaining
    value.
- **The layout is checked against fallback font metrics, not Inter.** The README shows the SVG
  through `<img>`, which cannot load web fonts, so most readers see Helvetica/Arial and Courier.
  The spacing was set and reviewed with those faces, at README width (900 px since the
  2026-09-27 redesign, rendered with `rsvg-convert`) on white and on GitHub dark (`#0d1117`). Do not tighten it on a machine that has Inter or JetBrains Mono installed: it
  would fit there and overflow for everyone else. The logo itself no longer depends on fonts: its
  text is outlined (see *The logo's text is outlined*), so it has the same ink in every
  renderer and the old `overflow: visible` on the logo slot is gone.
- **The logo is copied inline, not referenced.** An SVG loaded through `<img>` never fetches
  another file, so a referenced logo would draw nothing. The JIC and EDIH-DIGIMAT marks are
  embedded as base64 data for the same reason; the generator reads them from `App/assets/`, so
  a changed mark makes the committed SVG stale and the whole-file test fails. There are now three copies: `images/`,
  `App/assets/` (the topbar) and the one the generator inlines. A test holds all three equal.
  Rebuild the logo with `Example/UI/build_logo.py` (it writes both files), then regenerate.
- **The logo's palette predates the theme and is deliberately not reconciled with it.** Slate
  `#0F172A` and magenta `#D6006E` are not `CONST_INK` or `CONST_BRAND`. The topbar already shows
  the logo this way beside the indigo UI, and the diagram mirrors that on an opaque `CONST_BG`
  card, which reads like a screenshot on a light or a dark README. Do not "fix" the logo to the
  tokens: it is the brand lockup, not a UI surface.

**Revisit if** the logo is redesigned (rebuild it with `Example/UI/build_logo.py`, regenerate), or
if the code changes what the diagram shows. The generator holds the colours; the content is
still written by hand in the generator, and the README link is what keeps it in view.
Tests `test/UI/test_brand_figures.py` (`test_the_three_logo_copies_are_identical`,
`test_the_diagram_is_the_generators_output`, `test_the_diagram_draws_only_theme_tokens`,
`test_the_readme_shows_the_diagram`).

## The logo's text is outlined, so the logo has the same width in every font setup

`images/anyscan-logo.svg` (and its byte-identical copy `App/assets/anyscan-logo.svg`) carries no
`<text>`: the wordmark, the tagline and the index "1" are paths, set in Inter 400. It has no
`<style>`, no `marker` (the arrowhead is not drawn, as the app always showed it), and no C2PA
metadata. The viewBox is the ink bounds plus 5 units on every side, which keeps the height at 174
so the top bar's `Style.CONST_LOGO_HEIGHT` (54 px) lockup keeps its scale. (59 px on a low-density display since 2026-09-29: *The logo is 59 px on a low-density display*.)

It is built, never edited: `python Example/UI/build_logo.py` outlines the text source
`images/source/anyscan-logo-text.svg` and writes both copies (`--output PATH` writes one file,
`--font PATH` uses a local copy of the font). Then regenerate the diagram.
- **Font:** Inter 4.001, SIL OFL 1.1 (outlined glyphs in a logo are artwork made with the font; the
  OFL governs the font software, and Inter has no Reserved Font Name). It is not in the repository:
  the script downloads `ofl/inter/Inter[opsz,wght].ttf` from google/fonts commit
  `e1d6480102fed30739fead0faee463101f892c8f` and stops unless its SHA-256 is
  `29160a80ff49ddcab2c97711247e08b1fab27a484a329ce8b813d820dc559031`.
- **Outliner:** Inkscape 1.2.2 (`--export-text-to-path --export-plain-svg`), shaping with
  Pango/HarfBuzz (kerning included), through a private fontconfig file that shows it only that font.
  Another Inkscape version builds with a WARNING; compare before committing.
- **Optical size, pinned in the source:** Inter's `opsz` axis runs 14–32 and Pango picks it from the
  size on its own (measured: 32 for the 87-unit wordmark). The source pins it on every `<text>` with
  `font-variation-settings`: `'opsz' 32` for the wordmark (87) and the tagline (36), `'opsz' 14` for
  the index (13), which is what a browser chooses at those sizes.
- **Reproduced:** from a clean export of the committed tree into a temporary path, the script's
  output is byte-identical to `App/assets/anyscan-logo.svg`. That holds on the macOS build it was made
  with. On Linux the Inkscape 1.2.2 AppImage does not reproduce it (measured 2026-09-29): its bundled
  Pango ignores `font-variation-settings`, so the wordmark and tagline are outlined at the default opsz
  14 (viewBox 886.48 wide, not 844.15), and it writes path data in another form (other start points,
  three decimals) even from static instances of the font. The mark (`--mark-only`) reproduces anywhere.
  The full-rebuild test is therefore `slow` and macOS-only; its skip reason names this cause.

**Why.** PyQt5's QtSvg 5.15 ignores every CSS `font-*` property (measured 2026-09-28: a CSS `fill`
changed 2,500 px, a CSS `font-family`, `font-weight` or `font-size` changed 0), so it drew the
text in the application's default font at regular weight. On macOS that is the narrow system face,
which fitted; on Linux it is usually DejaVu Sans or similar, which ran the tagline 116 units past
the old 858-unit viewBox and clipped it in the header. Widening the viewBox instead (the 1060-unit
version) fixed the clip but left up to 77 px of empty image between the tagline and the divider
in the topbar, and the width still depended on the machine's font. Outlined, the logo renders
identically under any application font (pixel-identical pixmaps under the macOS system font and
DejaVu Sans) and matches rsvg-convert and WebKit to anti-aliasing (identical ink boxes, no pixel
more than 128 levels apart). Look (b), the file's CSS intent (bold wordmark, JetBrains Mono
tagline, arrowhead), was the alternative; (a) was chosen because it is what the app has shown.

In the top bar the logo, the divider and the JIC mark are spaced `AnyScan_Window_Cls.CONST_BRAND_GAP`
= `Style.CONST_MARK_GAP` (32 px, the funding band's own gap around its divider, now named and used
by both) apart, measured from ink: `Style.Ink_Insets` takes each image's transparent margin off the
spacing, so the logo's 5-unit margin (1.6 px at 54 px) does not widen the gap. A margin wider than
the gap is not absorbed (the spacing never goes negative), so it shows and `test/UI/test_header.py`
fails; a smaller one is absorbed by design (at 32 px, even 100 extra units, 31 px, is). Before this,
77.5 of the 93.5 px between the tagline and the divider were empty image. 12 (the Live button bar)
and 16 (`Style.CONST_GAP`) were rendered as the alternatives. The architecture diagram follows the
same rule (`Header_Positions` in `Example/UI/architecture_diagram.py`): the gap scaled from the
54 px lockup to the diagram's logo, 41.24 units, measured 41.0 in an rsvg render.

**Revisit if** the logo is redesigned: change the text source (or replace it with an outlined
export), rebuild with `Example/UI/build_logo.py`, then regenerate the diagram; or if google/fonts
drops the pinned commit (pin another, update the SHA-256, and compare the rebuilt logo).
Tests `test/UI/test_brand_figures.py` (`test_the_logo_renders_the_same_in_any_default_font`,
`test_the_three_logo_copies_are_identical`, `test_the_diagram_is_the_generators_output`),
`test/UI/test_header.py`.

## Gemma 4 12B was measured against E4B and is not better; E4B stays the describer

*Evidence from the previous test set* — the seven frames removed in `f5cd075` (recoverable from `f5cd075^`; their names do not match `Data/Images/Test/All`). *Not re-run on the current set: it needs the describer run and its text read. The `Image_NNN` names below refer to that set.*

The obvious intuition is that a bigger model describes better. It was measured on 2026-09-25,
and it does not hold here. `mlx-community/gemma-4-12B-it-4bit` @ `73bcf09` (6.77 GB, the same
4-bit MLX format; the pinned `mlx-vlm` 0.7.2 loads its `gemma4_unified` architecture) ran the
seven frames on the M2 Pro. It had the same pipeline, the same crops and the same prompts as
E4B; only `Description.Model` differed. E4B was re-run in the same session and reproduced its
recorded baseline (2.20 s per object against 2.22; `Image_001` 20.7 s against 20.6), so the
comparison is like for like.

| | E4B | 12B |
|---|---|---|
| Warm time per object | 2.20 s | **5.46 s** (2.5×) |
| `Image_001` (9 objects) | 20.7 s | 50.4 s |
| Pipeline peak footprint | 9.35 GB | 10.45 GB |
| Load | 7.2 s | 7.5 s |
| Word-for-word identical, within and across processes | yes | yes |

- **What the 12B fixed:**
  - It names the rust on `Image_002` as rust ("brown and orange discoloration, appearing as rust
    or tarnish"); E4B said "brown, earthy-toned stains or deposits".
  - No invented "particulate matter" on the dark plates `Image_003` / `Image_005`, E4B's likely
    glint artefacts.
  - It calls `Image_001` object 7 a hexagonal nut, one of the two hex nuts E4B misses (object 8
    is still a "ring").
  - It reports a small real mark on `Image_006`'s corner, checked on the frame.
- **What it broke:**
  - **Three of `Image_001`'s four plastic parts read as metal.** Object 5, the white plastic
    part, becomes "a small, rectangular metallic component with a silver-colored finish";
    object 9 has "a blueish-green metallic appearance"; object 4 "a metallic, slightly textured
    surface"; object 2 gets no material at all. That is the property the prompts were measured
    against, and E4B reads those parts as plastic.
  - It calls the square `Image_006` (47.8 × 47.0 mm) "rectangular"; E4B said square.
  - It misses the concentric machining marks that dominate `Image_004`.
  - It repeats the prompt's condition checklist back in about ten of fifteen lines ("free of
    any visible rust, stains, or significant scratches").
- **The cost:** 2.5× the time per object, and +1.1 GB.

**Model or wording?**
- **The checklist echo is the wording.** The 12B follows "look carefully for discolouration,
  stains, rust, tarnish …" more literally than E4B does.
- **The plastics failure is, in our judgement, mostly the model.** Both models received the same
  crops and the same prompt, which asks for "apparent material" without suggesting one, and E4B
  reads those parts correctly from it.
- **The wording may still contribute.** The prompt's condition list is metal vocabulary (rust,
  tarnish), and it was tuned on E4B, so it may prime a model that follows lists more literally.
  **Only a prompt experiment separates the two:** a 12B-specific wording, measured on the same
  four plastic parts and the Image_002 / Image_007 plates. The 12B weights stay in
  `models/gemma-4-12B-it-4bit/` for that.

**Its provenance is a weaker link, not an equivalent choice.**
- E4B's card names its source, `google/gemma-4-E4B-it` at revision `fee6332`, where the licence
  was checked.
- The 12B's card names no base model, revision or licence. Its `tokenizer.json` is byte-identical
  to `google/gemma-4-12B-it`'s and its text configuration matches field for field (its chat
  template and processor configuration differ). That is plausible, not proven.

**Decision:** E4B stays the describer on macOS and is the default on Linux. The 12B is available
only as `./install.sh --model 12b`, which prints the provenance gap and these results when the
flag is given.
**Revisit if** a 12B-specific prompt fixes the plastics without losing the rust and the clean
plate. Then it is an argument for the 12B on macOS too, at 2.5× the time per object.

## Linux: MLX's CUDA backend, E4B on every card with ≥ 11 GB, refusal instead of a silent CPU fallback

A request to move Linux to PyTorch with a separate 12B build was checked against the repository
first. Linux already runs on **MLX's CUDA backend** (see *Platform: three states*), and the 12B
exists as a 4-bit MLX conversion the pinned `mlx-vlm` loads. So both platforms share one
describer and one weight format, and nothing new is written.

The PyTorch alternative would have needed:
- a second describer behind `Describe(crop, purpose)`;
- a way for the configuration to select it;
- and, for the best 16 GB fit, a 23.9 GB download (`google/gemma-4-12B-it-qat-q4_0-unquantized`,
  quantised to NF4 at load).

Google's own 4-bit `…-qat-w4a16-ct` looks smaller, but its safetensors header shows a 6.13 GB
4-bit decoder plus bf16 token embeddings and a *separate* bf16 `lm_head`, 2 GB each: 10.26 GB of
weights, built for vLLM. A file-size estimate would have missed that.

- **E4B on every Linux card, the 12B only on request.** The first Linux run should change one
  variable, Metal to CUDA, with the model measured on the Mac. The 12B would add a second
  variable, with a known regression (*Gemma 4 12B was measured against E4B*).
- **The card is read, not just the driver.** `nvidia-smi --query-gpu=memory.total,memory.used`
  on GPU 0, the device MLX and PyTorch use:
  - **the minimum is 11 GiB** (11,264 MiB): E4B plus FastSAM is estimated at ~8.5 GB, and 12 GB
    cards report ~12,280 MiB;
  - **`--model 12b` needs 15 GiB**: it is estimated at ~10.5 GB (6.77 GB of weights, ~0.25 GB of
    KV cache at the ≤ 280 image tokens every crop is resized to, plus the generation working
    set, two CUDA contexts and FastSAM), and 16 GB cards report ~16,300 MiB;
  - **a card already using more than 1.5 GB** (a display, another process) gets a warning.

  These are estimates: nothing has run on Linux.
- **No silent CPU fallback.** A machine without a usable NVIDIA GPU (no driver, a failing
  `nvidia-smi`, an old driver, compute capability below 7.5, too little memory) now stops. The
  message names the reason and the 11 GB minimum, and suggests `--cpu`. A silent fallback
  installs successfully and then leaves the operator with inference too slow to use, not knowing
  why. `--cpu` takes the CPU path with that warning; with a usable GPU it is not needed, and the
  GPU builds are installed.
- **The installer never edits a configuration.** After `--model 12b` a configuration still naming
  E4B keeps loading. The installer names the file, the field (`Description.Model`) and the value
  that would use the 12B.
- **Both manifests are pinned and verified.** Each file's published size and hash (LFS SHA-256,
  or git blob SHA-1) at the pinned revision. The 12B manifest was checked against the 12B
  downloaded for the measurement.

**Revisit when** a Linux machine runs it: replace the estimates with measured peaks, re-derive
the thresholds from them, and re-verify every exact-text pin on the CUDA backend.
Tests `test/Install/test_install.py` (the refusal and `--cpu` for every no-GPU case, the memory
floors, the busy-card warning, `--model` parsing, the 12B notice, its download directory, and the
configuration message).


## The Log view holds the newest 1,000 lines, because each row made every later one slower

The Log view rendered every line of the session as its own row (a widget, a layout and three
labels) and never dropped one. A new row costs more the more rows the layout already holds, so the
view did not just grow — it slowed the application down as the shift went on. Measured offscreen
on the development Mac, appending a realistic object line 1,000 at a time:

| Rows in the view | Time for the next 1,000 lines | Per line | Memory added |
|---|---|---|---|
| 1,000 | 1.1 s | ~1 ms | +46 MB |
| 5,000 | 5.3 s | ~5 ms | +229 MB |
| 10,000 | 13.4 s | ~13 ms | +455 MB |
| 20,000 | 39.1 s | ~39 ms | +909 MB |

All of that runs on the GUI thread. At 12–15 lines per analysis, a 1,000-analysis shift reaches
~15,000 rows: about 0.7 GB and ~27 ms of work for every new log line — the application getting
sluggish in the afternoon with nothing to connect it to the log.

- **The view keeps the newest `CONST_MAX_ROWS` = 1,000 lines** (`UI/Views/Log.py`); past it the
  oldest row is dropped as each new one arrives. With the cap the cost stays flat: ~1.5 ms a line
  and ~115 MB (peak RSS) whether the shift has written 2,000 lines or 20,000.
- **The file keeps every line.** The count says so once lines have been dropped ("the last 1000
  kept here, all in the log file"), so a short view never reads as a short log.
- **Seeding from the file renders only its last 1,000 lines**, instead of building every row of a
  long file only to drop it again.
- **A scrolled-up reader is not moved.** When a row above the viewport is dropped, the scroll
  position moves up by its height, so the line at the top of the viewport stays the same.
- **1,000 is the knee, not a limit of the design.** It keeps a new line near 1 ms and the view
  near 50 MB of rows. A first measurement showed memory still climbing after the fix; that was the
  measurement, not a leak — dropped rows are freed by `deleteLater`, which only runs when the event
  loop does, and the script never started one. Processing the deferred deletes (as the application's
  own loop does) the memory levels off.

**Revisit if** someone wants more lines on screen: re-run the measurement above first and raise
the cap only as far as the per-line time stays acceptable — or render the log with a model/view
(`QListView` over the records) instead of one widget per line, which would remove the curve.
Tests `test/UI/test_log_view.py::test_the_view_keeps_the_newest_lines_and_says_the_rest_are_in_the_file`,
`::test_seeding_from_a_long_file_renders_only_its_last_lines`,
`::test_dropping_old_lines_does_not_move_what_a_scrolled_up_reader_sees`.


## Two calibrations of the same images agree only to the last digits — read a small difference as noise

`cv2.calibrateCamera` runs on OpenCV's thread pool (12 threads on the development Mac by default),
and the order in which the threads' partial sums combine changes from run to run. The same images,
solved twice by the same code, give reports that differ in the last digits. This was found while
checking that the `Calibrate` split changed nothing: the unchanged code first disagreed with itself.
With `cv2.setNumThreads(1)` repeated runs are identical to the last bit, which is how old and new
code were compared.

How large the difference is depends on how well the image set pins the solve down. On the test
suite's synthetic boards:

| Image set | Distortion coefficients | mm/px factor | RMS |
|---|---|---|---|
| Realistic: 3 flat boards + 8 tilted 15–25° (plus an unreadable file and a board-less frame) | ≤ 2e-9 | ~1e-11 | ~2e-15 px |
| All frontal: the 3 flat boards only | k3 −1.750 vs −1.758 | ~2e-8 | ~7e-11 px |

- **Comparing an old calibration with a new one:** a difference at the level of the first row is
  the solver, not the lens, the board or the rig. Only differences far above it mean anything.
- **A visible run-to-run difference is a second sign of an ill-conditioned set.** The all-frontal
  set, where k3 moves in its third significant digit, is exactly the set `Calibrate` already warns
  about ("near-frontal views cannot separate the principal point from the board's position"). If
  re-running the same images moves a coefficient visibly, the images do not determine it; add
  tilted views rather than trusting either value.
- **Nothing pins the thread count in the application or the harness.** Reproducibility to the last
  bit is not needed there, and forcing one thread would slow every solve for no benefit. Pin it
  (`cv2.setNumThreads(1)`) only when comparing two runs of the same code, as the equivalence check
  did.

**Revisit if** a calibration comparison is ever automated (a regression check on the rig's
calibration, say): it must compare with a tolerance at the scale above, or pin the thread count on
both sides.
Tests `test/Calibration/test_core.py` (the synthetic solves the table was measured on).


## The printed calibration board stays 11 × 8 at 12 mm; a board larger than the field needs ChArUco

The board is generated by `Example/Camera/generate_checkerboard.py` into
`docs/Checkerboard_11x8_12mm_A4.pdf` (under `docs/` because it is printed and read, never input data),
and the calibration set is 40+ views, not a larger board.

**Why.** A larger board looked better and is not usable with this detector.

- On the synthetic study's model, which assumes every visible corner is detected, a 20 × 13 board
  (240 × 156 mm, overhanging the ~188 × 118 mm field) cut the factor's spread about fourfold:
  0.015 / 0.028 % (median / 90th percentile) at 12 views against 11 × 8's 0.085 / 0.138 %.
- The real detector does not read it. `Detect_Board` calls `findChessboardCornersSBWithMeta` with the
  minimum grid (4 × 3) and `CALIB_CB_LARGER`, and that growth stops beyond ~15 columns and where the
  board leaves the frame. On 12 rendered camera views (122 px squares, flat and tilted 10–35°) 11 × 8
  was read whole every time; 20 × 13 came back as grids from 3 × 5 to 17 × 3, 17 × 11 likewise.
  Passing the full grid finds a large board only when all of it is in view, which a board larger
  than the field never is.
- Views buy what the board cannot: 11 × 8 spreads 0.057 / 0.103 % at 24 views, 0.039 / 0.065 % at 40,
  0.028 / 0.056 % at 60 — under the 0.1 % limit from 40.
- Even 11 × 8 was not always read whole while the detector grew from its minimum grid: over a sweep
  of rendered views tilted 0–45°, 86 of 100 whole, the rest partial grids of ~30 corners instead of 70.
  *Corrected 2026-09-25: this said 83; that count came from an earlier version of the test's camera
  view.* The detector is now told the board (next entry) and reads all 100 whole.
- The page carries a scale ruler on **each** axis, 10 squares long, and says not to use a board where
  either is not 120.0 mm. Printers can scale the feed and head directions differently, and the solver
  takes the x and y factors from one `--square-mm`, so a one-axis error would go into one factor
  unflagged. The printed command leaves `--square-mm` as a `<CALIPERED mm>` placeholder.
- The PDF is written with the standard library (no reportlab): rectangles, lines and built-in
  Helvetica in exact millimetre geometry, byte-reproducible.
- The board with its one-square white border is 120 mm tall against a ~118 mm field; the detector
  was measured not to mind, so the border is not shrunk to fit.

**Revisit if** a board larger than the field is wanted: that means ChArUco (`cv2.aruco.CharucoDetector`,
in the installed OpenCV), whose marker IDs make a partial, overhanging view detect completely —
replacing the detection in `Calibration.Core` and its tests, and checked on rendered views of the
printed board before anyone prints it.
Tests `test/Camera/test_generate_checkerboard.py` (the page rendered and read by `Detect_Board` across
a tilt sweep; nothing in the quiet zone; both rulers exactly ten squares; the calipered placeholder;
the committed PDF reproduced), `test/Camera/test_reference_harnesses.py::test_each_camera_script_imports_from_any_working_directory`.


## The calibration detector is told the board and asks for all of it first

`Calibration.Core.Detect_Board(image, board_squares)` asks `findChessboardCornersSBWithMeta` for the
board's whole inner grid first and only then for `CONST_CALIB_MIN_GRID` (4 × 3) with `CALIB_CB_LARGER`,
the fallback for a board overhanging the frame; a grid larger than the board is refused inside it.
`calibrate.py --capture` requires `--board-squares` (each frame is checked as the solve will read
it, whole or partial, and says which), records it in `capture.json` as `board_squares`, refuses to
extend a set taken with another board, and `--images` refuses to solve a set as a board other than
the one it records.

**Why.** Growing from the minimum grid is not reliable, and every partial view costs the solve
corners. On 100 rendered camera views of the printed 11 × 8 board (tilted 0–45°, 10 noise seeds) the
minimum grid read 86 whole and the rest as partial grids down to 3 × 5 — ~30 corners where the board
has 70. Asking for the whole grid read all 100 whole, and all 100 of the same views turned 90°, in the
same time (~240 ms a view). Accuracy is unchanged: mean corner error against ground truth 0.032 px
with the whole grid, 0.033 px with the minimum grid (40 rendered views through the test suite's lens,
tilted up to 40°). A board turned on its side needs no second pattern: the detector finds the
whole grid in either orientation and reports it in the board's own (columns × rows).
The board became a required argument, not an optional one: a detection without it is exactly the
unreliable path, and every caller knows the board — `--images` always did, `--capture` now does.

**Revisit if** the calibration moves to a board the detector cannot find whole in one call (a board
larger than the field — ChArUco, previous entry), or if a set's frames regularly report "part of the
board": the fallback is then carrying the solve, and the views should be retaken.
Tests `test/Camera/test_generate_checkerboard.py::test_the_calibration_detector_reads_the_printed_board_whole`
(every view of a 30-view tilt sweep read whole; red with the minimum grid alone),
`test/Calibration/test_core.py::test_detector_reads_a_board_turned_on_its_side_whole`,
`::test_detector_refuses_a_grid_larger_than_the_board`, `::test_detector_finds_the_visible_part_of_an_overhanging_board`
(the fallback), `::test_capture_harness_keeps_every_frame_and_marks_them_distorted`,
`::test_a_set_captured_with_another_board_is_not_solved`,
`test/Camera/test_reference_harnesses.py::test_calibrate_refuses_capture_without_the_board_and_says_why`.

## The first analysis's one-time costs are paid at configuration load ("Warming up…")

*Evidence from the previous test set* — the seven frames removed in `f5cd075` (recoverable from `f5cd075^`; their names do not match `Data/Images/Test/All`). *Not re-run on the current set: it needs the timing run again. The `Image_NNN` names below refer to that set.*

`Vision_Pipeline_Cls.Configure`, once the configuration is in force, reads the reference, runs
FastSAM on it (it has the frame's size) and describes the background sentence — which is also
Gemma's first generation — under the dialog's stage label **Warming up…**. Configure clears the
previous reference and sentence first, so a reconfiguration describes its own reference. The
sentence's audit record is held and carried by the first analysis, as before. The warm-up is best
effort: a failure there is not a failed load; the first analysis meets it and reports it. When a
failed load reloads the previous configuration, the reload is warmed up the same way (a reloaded
Gemma describes the sentence again as its first generation; a Gemma that was kept is still warm and
keeps its sentence), so a slow first analysis does not read as a second fault after the failure.

**Why.** The first ANALYZE after a load took **2.6–2.9 s** longer than the second on the same frame
(2026-09-26: `Image_001`, 9 objects, the shipped configuration, real weights; the load on one thread
and each ANALYZE on its own, as the application runs them), all of it in three places:

| Stage | First analysis | Second | Extra |
|---|---|---|---|
| Background sentence (one Gemma call on the reference) | 1.08 s | 0 (kept) | +1.08 s |
| Gemma per-object — the first call only (3.10 s against ~2.2 s) | 21.0 s | 20.2 s | +0.84–1.14 s |
| FastSAM (predictor set-up and first device pass) | 1.02–1.06 s | 0.39–0.41 s | +0.64 s |
| Reading the reference | 0.03 s | 0 | +0.03 s |
| Background subtraction, fusion, crop enhancement, compose, measure | — | — | ≤ 0.02 s each |

`mlx_vlm` and `ultralytics` were already imported by the load. On the UI side the annotation render
(+0.02 s) and the undistortion maps (~0.01 s, built on the first SCAN capture) are too small to move.
The load is where the operator already waits, watching a stage label; the first scan of a run is not.

| | Before | After |
|---|---|---|
| Configuration load | 6.9–7.6 s | 9.4–10.0 s |
| First analysis (`Image_001`) | 23.4–23.7 s | 20.9–21.7 s |
| Second analysis | 20.7–20.8 s | 20.8–21.1 s |

The load is ~2.5 s slower, and the first analysis now takes as long as any other. The readings are
identical word for word before and after (`Image_002`, the background sentence and every object).

Rejected (reasoned, not measured): **warming up on a blank image** — it costs the same time, and the
reference is the one image that is certainly the frame's size and whose description the first
analysis needs anyway; **naming the cost on the analysis's busy line instead** — it would explain
the wait, not move it out of the scan; **warming up after the dialog reports the load done** — an
ANALYZE could then start while the warm-up still holds the models, which would need a lock between
the two for a saving of seconds.

*Updated 2026-09-27:* the load now logs where its time went, after the unchanged `Models loaded … (x s)`
line: one line per model (`Model FastSAM-x.pt loaded in 1.11 s.`, or `… kept, not reloaded.` for a model
the configuration shares with the previous one) and one for the warm-up's parts (`Warm-up took 3.24 s:
reference 0.04 s, first FastSAM pass 1.17 s, background sentence 2.03 s.`). A warm-up that stops early is
no longer silent at the load: that line becomes a WARNING naming the reason and saying the first analysis
pays the rest. Each analysis's timing line marks the first one after a load (`(first after load)`), so
whether the warm-up worked can be read from the log. In 12 processes on 2026-09-27 (`Image_001`, window
path) the first analysis was not slower than the second: the difference ranged from −711 to +127 ms.

**The harness is not warmed up, on purpose.** `Example/Vision/analyze.py` never calls Configure —
its first Analyze loads the models — so its first frame still pays these ~2.6 s. A slow first frame
is invisible in a command-line run. **Measure the fix through Configure** (the dialog, or a script
that calls it), not with the harness: timing the harness's first frame shows the old cost and says
nothing about this change.

**Revisit if** the load time starts to matter more than the first analysis (a load on every
startup, or a configuration switched often), or if a model change moves its one-time cost somewhere
the warm-up does not reach — a crop size or input shape Gemma or FastSAM compile separately, which
would show again as a slow first analysis in the table above.
Tests `test/Vision/test_core.py::test_a_configuration_load_warms_up_what_the_first_analysis_would_pay`,
`::test_the_background_is_described_once_per_configuration` (at the load, from the new reference),
`::test_the_background_audit_reaches_the_first_analysis_after_a_load`,
`::test_a_failed_warm_up_is_not_a_failed_load`,
`::test_the_reload_after_a_failed_load_is_warmed_up_like_a_load`,
`test/UI/test_configuration_dialog.py::test_the_loading_line_follows_the_loaders_phases` ("Warming up…"
as painted); commit `fd369e4`. The load and warm-up log lines:
`test/UI/test_timing_log.py::test_a_configuration_load_logs_each_model_and_the_warm_up`,
`::test_a_warm_up_that_stops_early_is_a_warning`, `::test_the_first_analysis_after_each_load_is_marked`.

## The logo is 59 px on a low-density display

Below a device pixel ratio of 1.5 the top bar draws the AnyScan lockup 59 px tall
(`Style.CONST_LOGO_HEIGHT_LOW_DENSITY`); at 1.5 and above it stays 54 px (`Style.CONST_LOGO_HEIGHT`).
`Style.Logo_Height(widget)` chooses, through `Style.Is_Low_Density(widget)`, the one density check: the
widget's `devicePixelRatioF()` below `Style.CONST_LOW_DENSITY_DPR` (1.5). The spacing to the divider is
still measured from ink (`Style.Ink_Insets`), so the 32 px gap holds at both heights.

How the ratio is read, and its limit: Qt 5.15 gives a widget the ratio of its top-level window's screen
once that window has a native handle. The header is built before the window is shown, so what it reads
is the application's ratio, which Qt 5 takes as the highest of all screens: a machine with a Retina and
a 1x screen gets the 54 px logo on both. The height is read once, when the header is built; nothing
re-reads it when the window moves to a screen of another ratio. That belongs to mixed-DPR support,
which this does not add.

**Why.** At 54 px (0.310 px per unit) the corner brackets are 1.24 px wide and the connector 0.93 px, and
neither covers a whole pixel: their brightest pixels reach 0.66 and 0.53 coverage, so on a 1x monitor
the mark reads soft. Across 48–64 px, 59 is the smallest height where both land on a whole pixel
(peak 1.00 and 0.99); the share of the mark's ink at full contrast rises from 0.38 to 0.52 and its edge
width falls from 2.9 to 1.6 px. The wordmark stems are 2.2 px at 54 and were never the problem. The
tagline stays soft at every height in range (its 15 stems sit at 15 sub-pixel phases; best full-contrast
share 0.17 at 64). 57 and 62 were rendered as the alternatives: 57 leaves the brackets at 0.95, 62
drops the connector to 0.60. A grid-fitted 1x logo file was estimated at 1–1.5 days plus upkeep for a
gain 59 px gives without it. At DPR 2 every stroke already spans two device pixels or more, so the Mac
header is unchanged (the logo pixmap is `Load_Svg` at 54 px, identical pixels; since the lockup's text is
live, *The header's wordmark and tagline are live text*, only the mark is an image). The top bar is 5 px
taller at 1x (92 → 97 px); the minimum window width does not change (1406 px). Measured 2026-09-29 on
a 27" 1920 × 1080 monitor (81 ppi), offscreen renders checked pixel-identical against the xcb platform.

**Revisit if** the logo is redesigned (its stroke widths change what lands on a pixel), if
`CONST_LOGO_HEIGHT` changes, or when the window re-reads its screen's ratio on a screen change: then
the height must follow it, not the ratio at build time.
Tests `test/UI/test_header.py::test_the_logo_is_59_px_on_a_low_density_display`,
`::test_the_logo_is_54_px_on_a_high_density_display` and `::test_the_header_is_measured_again_at_dpr_2`
(the module run again at `QT_SCALE_FACTOR=2`), with `::test_the_brand_marks_are_spaced_by_the_brand_gap_from_ink`
at both ratios. At DPR 1 the gap test's ±1 px cannot see a missing ink inset (1.7 px at 59 px); the DPR 2
run does (measured 33.5 px).

## Text clears 4.5:1 on its ground: the muted ink, status words and error text on the viewport

Every enabled text in the console is at least 4.5:1 (WCAG AA) against the ground it is drawn on, at any
density. Three changes, all in `Parameters/Theme.py`:

- `CONST_INK_MUTE` is `#706a8c` (was `#8983a6`): the same LCh hue and chroma at L* 46.6 instead of
  56.4. 5.09:1 on the card, 4.69:1 on the control hover, 4.60:1 on the page (was 3.58, 3.29, 3.24).
- A status word is drawn in its colour's text twin: `Theme.Status_Text_Color` maps `CONST_OK` to
  `CONST_OK_INK` and `CONST_WARN` to `CONST_WARN_INK` (`CONST_STATUS_TEXT_COLORS`), 5.02:1 each (was
  3.30 and 3.19). The two widgets that put a status colour on words read it: `Stat_Cell_Cls.Set_Value`
  and the header pill's `__Pill_Style`. The status cell's dot keeps the bright colour (a graphic, held
  to 3:1). The call sites still pass the status colour.
- `CONST_ERROR_ON_DARK` (`#fc5e4c`, `CONST_LOG_ERROR`'s hue lightened) for red text on the indigo
  viewport, the failed set's History thumbnail: 4.61:1 (was 2.18:1 with `CONST_LOG_ERROR`).

`CONST_PRIMARY_DISABLED_TEXT` keeps the old muted value `#8983a6` as its own literal, so the disabled
ANALYZE label looks as it did. Disabled controls stay exempt (see *Control stylesheets*). The JIC mark
(`brand-jic-mute.png`) is artwork tinted with the old value and is not re-tinted.
`images/anyscan-architecture.svg` takes `CONST_INK_MUTE` from the theme and was regenerated.

**Why.** The 2026-09-29 audit of every text style found 38 flagged on a 1x monitor; 23 of them were
`CONST_INK_MUTE` as a text colour (status-strip labels, the "Configuration not loaded." chip, empty
states, timestamps, History's notes and captions), and the status words were in the bright verdict
colours. Contrast is defined on colour values, so it applies at every density; a 1x screen makes it
worse, because anti-aliasing leaves small text below its token's contrast (a 10 px label in the old muted
ink rendered at 3.40:1 at DPR 1, 3.58:1 at DPR 2). A density-dependent palette was rejected: the theme
is the one Qt-free palette the vision renderer and the diagram share. The Mac look changes: muted text is
darker. The failed-set thumbnail cannot be reached in the application today (found 2026-09-29, not
fixed here): a partial set's metadata carries no run id, and History lists only the current run's sets;
the test renders the thumbnail widget itself.

**Revisit if** a text colour or a ground changes, or a new surface carries text: the test measures what
is drawn, so a new pair below 4.5:1 fails it.
Tests `test/UI/test_text_contrast.py::test_every_enabled_text_clears_the_floor`,
`::test_every_text_ground_is_a_theme_token`, `::test_every_flagged_text_was_measured` (one text of every
flagged style reached); buttons in every state are measured by `test/UI/test_control_contrast.py`.

## The UI fonts are bundled: static Inter and JetBrains Mono at the four weights the UI requests

`App/assets/fonts/` ships Inter and JetBrains Mono, each as four static files (Regular 400, Medium 500,
SemiBold 600, Bold 700: the QFont Normal, Medium, DemiBold and Bold the UI requests), with each family's
SIL Open Font License text (`Inter-OFL.txt`, `JetBrainsMono-OFL.txt`). Since the header's wordmark became
live text it also ships Inter Display Regular (`InterDisplay-Regular.ttf`, Inter at opsz 32, under its own
family name so it is never taken for the text cut; *The header's wordmark and tagline are live text*). `Style.Load_Fonts` registers every
.ttf there, and its candidate lists pick Inter and JetBrains Mono first; the system faces after them are
only the fallback for a missing directory. 2.17 MB in all (1.83 MB before Inter Display).

They are built, never edited: `python Example/UI/build_fonts.py` downloads the variable fonts and their
licences from google/fonts commit `e1d6480102fed30739fead0faee463101f892c8f` (Inter is the file
`build_logo.py` outlines the logo with), stops unless each SHA-256 is the pinned one, and instances every
weight with fontTools (4.66.0; another version builds with a WARNING): Inter at `opsz` 14, the text optical
size (Inter Display at opsz 32). The name table and `usWeightClass` are set so Qt lists each family with
its styles. The source's
timestamps are kept, so the output does not depend on the clock. **Reproduced:** three builds, the last into
a temporary directory, gave the same SHA-256 for all ten files as the committed ones (2026-09-29). After
Inter Display was added, two more builds into temporary directories reproduced those ten files unchanged
and gave the same `InterDisplay-Regular.ttf` both times (SHA-256 `1d1fb6b7…`, 339,200 bytes).

**Why.** None of `Load_Fonts`' candidates was installed on the Linux test machine, so `FONT_UI` kept the bare
name "Inter" and fontconfig drew Noto Sans; the monospace text was DejaVu Sans Mono. Noto Sans there has
only Regular and Bold, so the UI's 500 drew Regular and its 600 drew Bold. On macOS the candidates give, by
the code and the faces macOS ships (not verified on the Mac), Helvetica Neue, which has no SemiBold (600
draws Medium), and Courier New. The same style therefore had a different weight on each platform. Static
files, not the variable ones: Qt 5.15 exposes only a variable font's default instance and synthesises every
other weight (the button label's full-contrast share fell from 0.42 to 0.20 with the variable Inter,
measured 2026-09-29). Committed, not fetched by `install.sh`, the way the outlined logo is committed: an
installer fetch would add a network step and a fontTools dependency to a script tested only with stubs, and
an offline install would silently fall back. Subsetting to Latin was measured at 0.80 MB and not done: a
model sentence with a character outside the subset would switch faces mid-line. Inter does not make
10–11 px regular text crisper at DPR 1 than Noto Sans did (full-contrast share 0.02–0.05 in both), so it
is not a density fix. The Mac look changes: Inter replaces Helvetica Neue, JetBrains Mono replaces Courier New.

**Revisit if** the UI requests a weight outside the four (the test reads the weights from the source and
fails), Qt is upgraded to one that uses variable-font axes, or the logo's Inter pin moves (keep the two on
one commit).
Tests `test/UI/test_fonts.py::test_the_ui_and_monospace_families_resolve_to_the_bundled_fonts`,
`::test_every_requested_weight_draws_its_own_face` (ui, mono), `::test_the_display_cut_is_its_own_bundled_face`,
`::test_each_bundled_family_ships_its_licence`.

## A 9 pt type floor on a low-density display

Below a device pixel ratio of 1.5 (`Style.Is_Low_Density`) no text is set below 9 pt
(`Style.CONST_TYPE_FLOOR_LOW_DENSITY`): `Style.Font`, which builds every font in the UI (painted text
included), raises a smaller size to 9 pt there. At DPR 1.5 and above every size is as written. The ratio is
the application's, read when the font is built: the value a widget reads before its window is shown, with
the same limit as the logo (a screen change does not rebuild fonts; *The logo is 59 px on a low-density
display*). It raises ten chrome styles, all 7.5-8.5 pt: the frame and stage badges (`Widgets.py:217`), the
status-strip labels (`Widgets.py:1066`), the funding note (`Widgets.py:1249`), History's card time, card
count and failed thumbnail (`History.py:245, 250, 298`), its rolling-window note (`History.py:419`), image
captions (`History.py:550`) and connection group label and count (`History.py:796, 801`). Content sizes
(`CONST_TYPE_SCALE`, smallest 9.5 pt) are not touched.

**Why.** On a 1x monitor a regular-weight 7.5-8.5 pt text is 10-11 px, and at that size 0.02-0.05 of its
ink reaches full contrast, in Noto Sans and in the bundled Inter alike; at 9 pt (12 px) it is 0.12-0.19
(measured 2026-09-29, offscreen renders pixel-identical to xcb). Bundling Inter did not change that, so the
floor is independent of the face. A 2x display draws these sizes with 15-17 device px per em and keeps them;
there the window is pixel-identical to the window without the floor. The cost at DPR 1: the minimum window
size grows from 1454 x 1034 to 1511 x 1036 px (96 dpi); no label is clipped at it. Applying the floor only
to regular weights was considered (the two bold uppercase labels gain little, 0.36 to 0.40) and not done:
one rule is easier to hold than two.

**Revisit if** a chrome size is changed or added below 9 pt (the floor hides it at DPR 1 but not on a
Retina display), or when the window re-reads its screen's ratio on a screen change.
Tests `test/UI/test_text_contrast.py::test_every_text_is_at_least_9_pt_on_a_low_density_display`,
`::test_a_high_density_display_draws_what_it_drew_without_the_floor` (at DPR 2),
`::test_the_text_checks_run_again_at_dpr_2`.

## The header's wordmark and tagline are live text

The top bar's lockup is `Widgets.Logo_Lockup_Cls`: the mark as an SVG pixmap at `Style.Logo_Height`, and
"Any" + "Scan" and the tagline drawn as live text. The wordmark is set in the bundled display cut, Inter
Display Regular (`Style.CONST_FONT_DISPLAY`: Inter at opsz 32, the optical size the logo outlines it at),
the tagline in the bundled text cut, Inter Regular (opsz 14). One code path at every density; only the
height differs (59 px below DPR 1.5, 54 px above).

- **Mark:** `App/assets/anyscan-logo-mark.svg`, a second output of `Example/UI/build_logo.py`, derived in
  Python from the outlined logo: the logo with its two top-level outlined texts removed, in the logo's own
  viewBox, so the text lands at the text source's coordinates unchanged. The index "1" stays in the mark.
  Deriving needs neither Inkscape nor the font, so `build_logo.py --mark-only` rebuilds it byte for byte
  from the committed logo on any machine; a full build derives it from the logo it has just outlined.
- **Text:** `Style.CONST_LOGO_TEXT` holds each line as the source sets it, in logo units: the pen origin
  (268, 132) and (270, 184), the sizes 87 and 36, whether the line takes the display cut, and the spans.
  The colours are the tokens `CONST_LOGO_INK` `#0f172a`, `CONST_LOGO_MAGENTA` `#d6006e` and
  `CONST_LOGO_TAGLINE` `#475569`, the source's fills exactly (the logo's own palette, see *The logo's
  palette predates the theme*). "Scan" starts where it starts in the whole word as shaped, so the kerning
  across the colour change is kept. The sizes are the logo's (29.5 and 12.2 px at 59 px; 27.0 and 11.2 at
  54), converted to points through the widget's DPI and built with `Style.Font`, so the 9 pt floor applies.
- **Whole-pixel sizes:** Qt 5 draws a face at a whole-pixel size (FreeType through fontconfig, measured:
  29.5 px draws at 30, 12.2 at 12). The wordmark would be 1.7 % wide (+2.3 px at DPR 1), so its letter
  spacing takes the rounding up: the run advances as far as it would at the requested size (−0.27 px per
  glyph at DPR 1, none at DPR 2, where 27 px is 54 device px). The tagline is left as drawn: 12 px at
  96 dpi, and 13 px in the offscreen tests (100 dpi), where the floor asks 12.5.
- **Spacing:** the 32 px gap to the divider is still measured from ink: `Style.Ink_Insets` on
  `Logo_Lockup_Cls.Render()`, whose right ink is the tagline's.
- **Unchanged:** `images/anyscan-logo.svg`, its copy in `App/assets/` and the architecture diagram's
  inline copy stay the outlined logo. Nothing else in the UI shows the full logo: the window icon
  (`anyscan-mark-white.ico`) and the empty-viewport art (`anyscan-mark.png`) are the mark alone, and the
  window title carries the tagline as text already.

The layout reproduces the outlined logo's to within 0.74 device px. Measured on the shown header against
the outlined logo rendered at the same height (device px, live minus outlined, 96 dpi):

| Offset | DPR 1 (59 px) | DPR 2 (54 px) |
|---|---|---|
| mark → wordmark left edge | −0.26 | −0.32 |
| mark top → wordmark baseline | −0.17 | −0.24 |
| wordmark → tagline left edge | +0.43 | +0.66 |
| wordmark baseline → tagline baseline | +0.40 | +0.71 |
| wordmark cap height | +0.54 (22.00 vs 21.46) | +0.04 |
| tagline cap height | +0.27 (8.67 vs 8.40) | −0.27 |
| wordmark width | +0.47 (112.91 vs 112.43) | +0.32 (206.42 vs 206.11) |

The tagline is wider than its outlines by design: the text cut sets 9.7 % wider than opsz 32 (right ink
+16 px at DPR 1, +30 device px at DPR 2), and at 11–12 px it is the cut Inter draws for. The brand group
is 16 px wider than with the outlined logo (450 → 466 px at DPR 1); the minimum window size does not
change (1511 × 1036 at DPR 1, 1454 × 1029 at DPR 2).

**Why.** Outlined text is a picture: at DPR 1 its stems, cap line and baseline fall between pixels, and
nothing can hint them, so the tagline had 0.08 of its ink at full contrast (the low-density report's
measure: of the ink samples, each colour channel of each pixel at coverage ≥ 0.10, the share at ≥ 0.90).
Live text goes through FreeType's hinting (hintslight here), which puts the cap line and baseline on
whole pixels: 0.18 at 96 dpi on this display, and the wordmark's cap height snaps to 22 px. At DPR 2
(Qt does not hint there) the tagline goes from 0.37 to 0.40. Measured 2026-09-29 on the 27" 1920 × 1080
monitor (xcb and offscreen at 96 dpi pixel-identical). The wordmark was first set in the text cut, 7.5 %
wider than the logo (+11 px at DPR 1); the display cut, one bundled Regular face, matches it. Tracking
the text cut down to the width was not done: it would change the letterforms' spacing, not their cut.

**Revisit if** the logo is redesigned (rebuild with `build_logo.py`; `CONST_LOGO_TEXT` must follow the
text source, which a test enforces, and the display cut's optical size must follow the wordmark's), or
when Qt 6 is adopted (it draws fractional sizes and can select a variable font's optical size, so the
spacing correction and the separate cut could go).
Tests `test/UI/test_header.py::test_the_lockup_matches_the_outlined_logo` (both densities, the wordmark's
width included), `::test_the_tagline_is_crisp_on_a_low_density_display`,
`::test_the_lockup_text_is_the_bundled_inter`, `test/UI/test_fonts.py::test_the_display_cut_is_its_own_bundled_face`,
`test/UI/test_brand_figures.py::test_the_mark_rebuilds_byte_identically_from_the_logo`,
`::test_the_mark_is_the_logos_own`, `::test_the_live_text_is_the_logo_sources_text`, and the `slow`,
macOS-only `::test_the_logo_and_the_mark_rebuild_byte_identically_from_the_source` (needs Inkscape 1.2.2).
`test/UI/test_text_contrast.py` measures the lockup's text too (magenta 4.65:1 on `CONST_BG`).

## The Linux describer choice is open: on the confirmed key E4B and the 12B are one wrong statement apart

**Status: open, pending the owner's choice (2026-09-29).** The shipped configuration keeps Gemma 4 E4B until
then; one configuration is shared by both machines, so History and Trends compare like with like.

The comparison rests on an answer key, `Data/Images/Test/All/answer_key.json`. It names, for each of the 37
objects the shipped pipeline finds in the eight frames (numbered in the pipeline's order), its part type,
material and colour, each with its source (`CONST_INVENTORY`, judged from the crop, or the owner from the
physical part). The owner confirmed every entry on 2026-09-29. The scoring rules, the synonym patterns, the
naming cues and the other materials are data in the key. `Vision.Utilities.Evaluation` is its only reader
and scorer, and `Example/Vision/evaluate_describer.py` runs the configured describer through the
application's path and scores it (`--describer-model` swaps the model in memory, not in the file).

Both models ran the same crops (identical pixel for pixel) with the shipped prompts. Totals over all 37
objects, as the scorer gives them and as checked by hand (every "not stated" was read; the scorer now
agrees with the hand check on every one). The key still marks the two small hex nuts (5.3, 6.2),
whose crop hides their corners, as `exclude_from_totals`, and the script prints the totals both
without and with them; the numbers here include them.

| Attribute (correct / wrong / not stated) | E4B 4-bit | 12B |
|---|---|---|
| Part type | 15 / 6 / 16 | 25 / 2 / 10 |
| Material | 28 / 1 / 8 | 28 / 6 / 3 |
| Colour | 37 / 0 / 0 | 36 / 0 / 1 |
| Wrong statements, type + material | **7** | **8** |
| Per object (warm, mean) | 0.65 s | 1.10 s |
| Peak GPU memory, whole application | 9.5 GB | 11.6 GB |

- **What each gets wrong.** E4B's six wrong types: the two larger hex nuts as "octagonal metal washer (or
  cap)" (5.5, 6.5), the small nut 5.3 as "a cap or fitting", the terminal strip as "metal die or mold"
  (7.4), and the comb twice as a "mold insert" or a "jig or mold component" (1.3, 8.3); its one wrong
  material is the terminal strip, "metal". The 12B's six wrong materials are all plastic parts called
  metal: the comb twice (1.3, 8.3, once as "a rectangular metal plate", also its wrong type), the double
  triangle twice (1.4, 7.6), the lattice bracket (7.7) and the terminal strip (7.4); its other wrong type is
  the white washer as "ring-shaped object" (2.4).
- **Where they differ in kind.** The 12B names ten more part types (the six large washers E4B hedges as
  "washer or cap / flange / ring", the two larger hex nuts, the red block twice), ties on correct materials,
  and misreads plastic as metal; E4B hedges more, misnames parts rather than materials, and is 1.7× faster
  with 2.1 GB less GPU memory.
- **Stable:** both gave identical text in two separate processes. The Mac comparison (*Gemma 4 12B was
  measured against E4B and is not better*) found the same plastic-as-metal pattern on the previous test set.
- **The prompts were tuned on E4B.** The object prompt's condition list is metal vocabulary (rust,
  tarnish), which may prime a model that follows lists literally. A 12B-specific prompt could narrow the
  material gap; that is untested.
- **How the scorer got here (2026-09-29).** Three corrections, each changing only scores a hand check had
  already found wrong: (1) feature words are no type claim ("the outer white ring", "a concentric ring
  design"); (2) conflicting names are a hedge, not stated ("washer or cap": E4B's six large washers,
  21 -> 15 correct); (3) a type counts as claimed wherever a naming cue introduces it ("suggesting it is a
  component or mold insert", in a second sentence), a material outside metal and plastic named alone is
  wrong ("felt or fabric"), and synonyms count in the plural ("strips"). Scoring on the app's short label
  (`Condense_Label`) was tried and rejected: it dropped names the text gives.

**The 8-bit E4B is not better: don't switch.** `mlx-community/gemma-4-e4b-it-8bit` at revision
`4255b21bd9a9d3fc807ef7abd80373f5e3a52a73` (8.91 GB, every file checked against its published hash) ran
through the same script, twice, with identical text. On the same 37 objects:

| Attribute (correct / wrong / not stated) | E4B 4-bit | E4B 8-bit |
|---|---|---|
| Part type | 15 / 6 / 16 | 16 / 5 / 16 |
| Material | 28 / 1 / 8 | 26 / 3 / 8 |
| Colour | 37 / 0 / 0 | 37 / 0 / 0 |
| Wrong statements, type + material | 7 | 8 |
| Per object (warm, mean) | 0.647 s | 0.883 s (+36 %) |
| Model load | 3.9-5.4 s | 4.4-4.9 s (warm-up sentence 12.8 s on the first load) |
| MLX peak | 6.99 GB | 10.72 GB (+3.73 GB) |
| Peak GPU memory, whole application | 9.5 GB | 13.1 GB |

- It calls five of the six large washers "circular disc" (wrong; the 4-bit hedges) and the sixth a "metal
  component"; it drops "plate" on two plates; it calls a 3D-printed robot "felt or fabric" and an aluminium
  washer "plastic or composite". It names the red block, the comb and the lattice bracket, which the 4-bit
  does not, and one hex nut "hexagonal", but never says "nut".
- **On the 16 GB Mac, an estimate, not a measurement:** the 4-bit application peaks at 9.41 GB there; adding
  the 3.73 GB the 8-bit needed on Linux gives about 13.1 GB, leaving roughly 3 GB for macOS, and the model's
  10.7 GB alone is about the share of a 16 GB machine's memory macOS normally lets the GPU use. Metal's
  figures can differ from CUDA's; it would have to be measured on the Mac before any switch, and it is not
  worth measuring while it scores worse here.

**Why open.** The first reading (E4B 4 wrong statements, the 12B 8) rested on 35 objects and a scorer that
missed invented names; with all 37 and the hand-checked scorer they are 7 and 8. What is left to choose
between is a kind of error, not a count: the 12B names parts better and misreads plastic as metal; E4B
hedges and misnames parts. That is an operator's priority, the owner's to set.

**Revisit if** the owner chooses (then record the choice and its reason here), the prompts are rewritten
(re-run both models), a new describer or E4B conversion is proposed (score it with the script against the
same key; the 8-bit is not worth measuring on the Mac unless it beats the 4-bit here), or the segmentation
changes: the script stops when a frame's object count differs from the key's, and the key must be
re-confirmed.
Tests `test/Vision/Utilities/test_evaluation.py` (the key covers `CONST_INVENTORY`, records the owner's
answers, and each scoring rule, including `::test_a_wrong_name_after_the_first_sentence_counts`,
`::test_a_material_outside_metal_and_plastic_is_wrong_alone`, `::test_a_plural_synonym_counts`); the run
itself needs the weights and is the script, not a test.

## The object label keeps the model's alternatives, and reads the phrasings that broke it

`Condense_Label` (`src/Vision/Utilities/Caption.py`), the short label the session log writes as
`Object detected: type=...` (and the panel shows only when a description is empty), now:
- keeps an alternative after "or" ("circular metallic washer or cap"), with
  `CONST_LABEL_ALTERNATIVE_WORDS` (2) more words than `CONST_LABEL_MAX_WORDS`, instead of dropping it and
  stating the first name as certain;
- peels "This is a", "It is a", "The part consists of" and "The part is shaped like" as openers, longest
  first (`CONST_LABEL_OPENERS`, `src/Reporting/Core.py`);
- ends the phrase at a bare " in " and at a participle after the noun (" rendered", " pointing",
  " appearing", " featuring"; `CONST_LABEL_BOUNDARIES`);
- does not end the adjective run at a hyphenated "-ing" word ("metallic-looking object").

**Why.** In the real window (`docs/evidence/label-2026-09-29/`: grabs of Image_003 and Image_005 and their
log lines) the label only reaches the log; History stores the full description and no label. There it
read `type=this` for "This is a small, stylized robot figure", and `type=circular metallic washer` for
"washer or cap". On the 111 descriptions of three describers (E4B 4-bit and 8-bit, the 12B) the old rules
left 6 / 12 / 1 labels that name no part; these leave 3 / 4 / 0. Scored against the answer key (37
objects) the E4B 4-bit label goes from 17 / 3 / 17 to 14 / 3 / 20 (correct / wrong / not stated): the six
kept hedges ("washer or cap") are not stated by design, as in the description scores, and every other
"not stated" is a generic word ("circular", "part"), checked by hand. Asking the model for a "Name:" line
instead (a prompt change) was measured and rejected: 10 of its 37 names were wrong ("Dental impression
tray", "Electronic Connector"), and it changes every stored description.

**Revisit if** the describer's phrasing changes (a new model or prompt), or something other than the log
starts to show the label.
Tests `test/Vision/Utilities/test_caption.py::test_condense_label_names_the_part_in_the_phrasings_that_broke_it`,
`::test_condense_label_keeps_the_models_alternative`, and the characterization baseline
`test/Vision/test_characterize.py` (its four label lines now keep the alternative).
