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
clearly as grey, including at full size on the previous test set's `Image_001` (`eb00508^`; a visual
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
*Corrected 2026-10-14, the JIC Smart Factory palette (*The palette is the JIC Smart Factory brand's, one purple,
measured on the frames*):* the boxes are now light (but OK), so each fill is built in the box's hue BELOW it, at
L\* 56–72, against the same floors; a fill lighter than a light box would read as white.

| | box | fill | ΔE box↔fill | ΔE fill↔white | vs black ground |
|---|---|---|---|---|---|
| OK | `#640ABA` | **`#CC9EF1`** | 63.5 | 55.4 | 9.7:1 |
| NOK | `#FF6540` | **`#CD7157`** | 30.8 | 62.2 | 6.1:1 |
| Warning | `#FFC226` | **`#B28508`** | 28.3 | 75.3 | 6.3:1 |
| neutral | `#E1DCE6` → mask outline **`#7E7982`** | **`#C7C2CC`** (derived pair, L\* 79.09; bound 79.74) | 27.6 | 21.7 | 12.0:1 |

**Revisit if** the operator-facing mask needs to encode something other than verdict (e.g.
per-class colour), in which case add a mode rather than overloading the default.
Tests `test/Parameters/test_theme.py::test_label_mask_fill_is_a_visible_tint_of_its_box` (fails
on the old values: "OK: fill #E2E0F0 reads as white"),
`::test_neutral_mask_pair_is_derived_light_fill_and_darker_outline` (the bounds and the pair's
margins), `::test_neutral_mask_pair_ignores_box_lightness_and_fails_loudly_on_floors`,
`::test_white_floor_rejects_what_reads_as_white_and_admits_the_l80_fill`,
`test/Vision/Utilities/test_annotate.py::test_label_mask_fills_each_object_with_a_tint_of_its_box_colour`,
`::test_detect_only_label_mask_fills_with_the_neutral_tint`, `test/UI/test_harness_parity.py`.

## The fail marker is the JIC orange-red `#FF6540`

The NOK verdict colour is the JIC orange-red `#FF6540`, the colour the AnyScan poster marks a defect in, for the
object's box and chip, a failed feature's marks and the stain tint. Its text twin `#BA260B` and, for words on its
ground, the poster's defect-tag tint `#FFD9D0` carry it into the UI.

*Corrected 2026-10-14:* until the JIC Smart Factory palette this entry was "`#ff005c` is the fail marker and must
stay the NOK colour": the EDIH-DIGIMAT magenta, kept because it read as a fail marker at a glance. The owner moved the
application to the JIC Smart Factory brand, whose poster gives the defect its orange-red; it still reads as a fail
marker and stays apart from every other state (ΔE ≥ 58) and from the Log's error pink (ΔE 55), so a defect and an
application fault never share a colour. Do not swap it for a calmer red.

**Revisit if** the verdict scheme or the brand changes.
Commit `ab7df30` (the magenta); test `test/Parameters/test_theme.py::test_verdict_colour_comes_from_the_one_constant`.

## The colour-name saturation cutoff is 120, and was not tuned for the red block

The model-free describer calls a pixel "coloured" only above HSV saturation 120
(`Describe_Fallback.CONST_COLOR_SAT_MIN`); below it the object reads as grey/metal. 120
sits in a real gap. It was set on the previous test set (`eb00508^`: metal up to S=98,
saturated colours from S=184, a pink-red block at S=121) and re-measured on
`Data/Images/Test/All` (2026-09-28, median saturation per object; no longer in the repository, recoverable from `1061966`, not re-measured
on the current set): metal, plastic and white
parts 2–78 (the dark plates 17–41), the blue parts 168–189, and the red block 124 and 143 —
still the one tight case, now 4 points above the line in `All/Image_006`. The field is decided
by a per-pixel majority vote, not the median, which is more robust than any median-based
cutoff, and lowering the line to "protect" the red block would only move the tightness toward
the metals. So it stays at 120. **Revisit
if** new captures show real coloured parts clustering in the 98–184 band; the honest fix
then is a better colour feature, not a nudged threshold.
Commit `2fe808e`; tests `test/Vision/test_describe_fallback.py::test_weak_metallic_cast_reads_grey_not_blue`, `::test_red_straddling_the_hue_wrap_votes_red_not_blue`.

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
Commit `5def2d0`; [`KNOWN_ISSUES.md`](../KNOWN_ISSUES.md) "confidence status metric is partial"; tests `test/UI/test_status_metrics.py::test_status_confidence_denominator_is_the_scored_count_not_the_total`, `::test_status_confidence_is_no_value_when_no_object_has_a_score` (*Corrected 2026-10-08:* renamed from `test_confidence_…`).

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

*Re-measured 2026-09-28 on the test set of that time* (`Data/Images/Test/All`, no longer in the repository, recoverable from `1061966`; the frames above are the
previous set, removed in `eb00508`, recoverable from `eb00508^` — names there do not match `All/`): 44
objects, 41 `both` and 3 `fastsam` (one each in `All/Image_001`, `007` and `013`), none background-only.
The FastSAM-only direction is sharper than before — the dark rusted plate in `All/Image_013` is 2 % seen
by the background cue — and the background-only direction still rests on the original run. The entry
stands.

*Re-measured 2026-09-28 on the eight frames left after `b5ca788`* removed `All/Image_009`–`013`
(recoverable from `b5ca788^`; the eight are gone too, recoverable from `1061966`, and the current set is not
re-measured): 37 objects, 35 `both` and 2 `fastsam` (the blue double triangle in
`All/Image_001`, the lattice bracket in `007`), none background-only. The 2 % plate was in `013` and is
no longer in the set; the FastSAM-only direction rests on the triangle and the bracket. The entry stands.
Commit `feca088`; tests `test/Vision/Utilities/test_fusion.py::test_object_seen_only_by_fastsam_survives`, `::test_object_seen_only_by_background_survives`.

## The closing never joins two components

Stage 3 splits the fused cues into connected components FIRST and closes each one on its own
(`Vision.Utilities.Fusion.__Close_Within_Components`): the closing still fills gaps and notches inside
a component, but a pixel it adds reaching two components goes to neither, and two components that
were separate before the closing are never one object after it. `Segmentation.Fusion.Close_Kernel`
stays 15.

**Why.** Closing the fused mask as a whole joined any two parts less than the kernel apart: in the
test set as it then was, `All/Image_010` and `013` (removed in `b5ca788`, recoverable from `b5ca788^`),
two plates 10.8 and 9.8 px apart came back as one object. That was a bridge with no reason behind it,
and a smaller kernel would only have moved the distance at which it happens. Across all twenty real
frames then available (the thirteen of `b5ca788^` and the previous seven) the closing
healed nothing — every count was the same with no closing at all — and with the new rule every other
object's mask is identical pixel for pixel, the lattice bracket and the milled square plate included. 010 and
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
`test/integration/test_pipeline.py::test_counts_match_the_inventory` (slow; the 41 frames of
`Data/Images/Test`, whose nearest parts are the plates of the 2×2 grids `Image_093`–`095`, set close
together but not touching, each counted four).

## The annotated view is the exported render, not live Qt painting

The Camera View shows the same image the harness exports (`Draw_Annotated` /
`Draw_Label_Mask` rendered off the result and handed to the viewport), rather than boxes
painted live in Qt. The old live painter cycled base palette colours and so disagreed with
the mask's colours object-for-object, which defeats a toggle meant for comparison; sharing
one renderer makes the on-screen annotation byte-identical to the export and keys each
object to the same colour in both views. **Revisit if** the UI needs interaction the raster
cannot give (hover, per-object selection, live zoom overlays), in which case reintroduce Qt
painting but drive its colours from the same `Theme` tokens so the two cannot drift.
Commit `94b74fa`; test `test/UI/test_camera_view.py::test_switching_view_does_not_invoke_the_pipeline`.

## Staleness clears the result rather than marking it

When the frame changes (a new scan, a disconnect, Clear), the held analysis renders are
dropped and the annotated/mask toggle is hidden, rather than kept and marked as belonging
to an earlier frame. Showing a previous frame's annotations over a new scene is the one
genuinely misleading failure here — the outlines would not line up and nothing on screen
would say so — and clearing is unambiguous where a "stale" badge invites the operator to
keep reading a mismatched overlay. **Revisit if** a use case needs to compare an old
analysis against a new frame side by side, which would call for an explicit two-pane
compare, not a marked-stale single view.
Commit `94b74fa`; tests `test/UI/test_camera_view.py::test_a_new_scan_makes_the_result_stale_and_hides_the_toggle`, `test/UI/test_threading.py`.

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
Commit `dfbb3b2`; test `test/Reporting/test_core.py::test_strip_background_noun_binding`.

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
Commit `1b208df`; tests `test/UI/test_logging_coverage.py::test_mid_analysis_failure_tags_the_error_and_writes_a_partial_set`, `test/UI/test_capture.py::test_a_write_failure_raises`.

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
Commit `1b208df`; tests `test/Reporting/test_core.py::test_yolo_lines_are_normalised_and_indexed_from_the_object_list`, `test/UI/test_capture.py::test_yolo_file_holds_the_given_lines_and_classes_has_a_header`.

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
*Corrected 2026-10-08:* since `d14a130` the third scope is the **run** (since the start or the last
Clear), labelled "Inference (run median)" and "Confidence (run mean)", and its accumulator is
`Reporting.Trends` (`AnyScan_Window_Cls.__trends.Run_Mean()`), not `__session_scores`. It weights
each object equally over the raw scores and rounds once, and Trends' frame mean is `Frame_Confidence`'s,
so the Trends tooltip, the Live panel and History show the same frame mean. Until 2026-10-08 Trends
rounded each object first and could read a point lower (scores 0.569 and 0.802: 68 % in Trends, 69 %
everywhere else); `test/Reporting/test_trends.py::test_the_means_round_once_from_the_raw_scores` pins it.
Commit `8c48a73`; tests `test/UI/test_status_metrics.py::test_frame_mean_and_session_mean_are_over_their_own_scopes`, `::test_session_mean_weights_each_object_equally_not_each_frame`, `test/UI/test_reading_view.py::test_object_blocks_carry_the_shared_label_and_description`.

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
Commit `61bb651`; tests `test/Vision/Utilities/test_annotate.py::test_seg_keeps_only_the_outer_contour_for_a_holed_object`, `test/UI/test_history_data.py::test_metadata_round_trips_and_matches_the_detection_list`.

## Classification is a per-configuration switch that exposes the verdict UI, not one that creates it

*Corrected 2026-10-11: the switch is removed. A configuration classifies exactly when it is a catalogue
mode (`Configuration_Str.Classifies`), so the dormant "on, but every object OK" state below cannot occur
any more; a file that still holds `General.Classification` loads with a warning that it is no longer
read. What this entry says about the verdict UI (the filter absent when not classifying, the neutral
colour, History following each set's recorded flag) still holds, with the catalogue mode as the switch.
See [*A catalogue mode identifies by similarity…*](#a-catalogue-mode-identifies-by-similarity-and-an-object-of-the-parts-shape-that-does-not-look-like-it-is-nok).*

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
Commit `1fbbd7b`; tests `test/Configuration/test_core.py`, `test/UI/test_history.py::test_the_two_empty_nok_states_are_distinguishable`, `test/Vision/Utilities/test_annotate.py::test_verdict_colored_false_draws_one_neutral_colour_not_verdicts`.

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
count **camera connections**. *Corrected 2026-10-07:* `total_session_time` no longer does. It is now the
summed cycles, each from a scan to the end of its analysis (*A cycle is a scan to the end of its analysis,
not a camera connection*). The column keeps its name because the name is the data contract. In the UI a connection
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
*(corrected 2026-10-11: the switch is removed; `analyze.py` reads `Configuration_Str.Classifies`, true in a
catalogue mode, from the same loaded configuration the application uses)*
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
warning (`Configuration.Core.__Read_Calibration`) says so. *Corrected 2026-10-08:* the leniency has
ended. The multi-view recalibration in force since 2026-09-28 records its window, so an absent window
now fails the load, naming the camera's window and `calibrate.py`
(`test_a_calibration_without_its_window_fails_the_load`).

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
made by the tool in force (checklist item 2). *Corrected 2026-10-08:* both reasons have expired (the
recalibration and `Image_Background_001` with its sidecar, both in force since 2026-09-28), and both
paths are load failures now (`test_a_reference_without_a_sidecar_fails_the_load_naming_what_is_unknown`,
`test_a_calibration_without_its_window_fails_the_load`).

**`scan.py` goes through the application's camera path.** It undistorted frames without the
application's processing step, so its frames were not what the pipeline sees — and it is the harness
someone would reach for to shoot a reference or grab a test frame. The same class of defect as
`analyze.py`'s `verdict_colored`, made required so a harness could not render differently from the app.
`scan.py` now captures with `Camera.Core.Basler_Camera_Cls` (window, processing, undistortion), and
says in its docstring and output that its frame carries no provenance and is not a reference.
`calibrate.py --capture` keeps its own path on purpose — it needs frames before undistortion — and
applies the application's processing profile to them.

*Corrected 2026-10-13:* a reference is no longer made from a capture set. `make_reference.py` shoots it
itself, through the same camera path, and its sidecar records what the camera reported: see *A new reference
is the mean of 8 frames…* below. The provenance and the load's checks are unchanged; the sidecar gains
`frames`, `station` and `compared_with`, which the load does not check.

**Revisit if** lighting becomes measurable (a reading from the lamp or a light meter could replace the
typed `Camera.Lighting` and close the gap above); or references are shared between cameras (the checks
would then need the hardware id as well as the window).
Tests `test/Configuration/test_core.py` (the sidecar checks), `test/Camera/test_reference_harnesses.py`
(the tool against a stand-in camera; `scan.py` against a stand-in).

## A new reference is the mean of 8 frames, shot by the tool, and refused if the application finds anything on it

`Example/Camera/make_reference.py`, run from the command line with the table empty and the application
disconnected, connects through `Camera.Core.Basler_Camera_Cls` with the station's camera settings and window,
grabs 8 frames (processed and undistorted with the station's calibration, as every analysed frame is), and
writes their rounded mean as the next free `Data/Images/Background/Image_Background_NNN.png` with its sidecar
(`source: camera`, `frames: 8`, the station, the read-back window, the lens model's fingerprint, the hardware,
and `compared_with`). Each file is created exclusively, and the next number is above every image or sidecar
already there, so nothing is written over. The station file is not edited: the tool prints its
`Background.Reference` line by number, as `calibrate.py` prints the calibration line. `--from` (a capture
set), `--accept-objects` and `--output` are removed and refuse, naming what replaced them.

**Before it writes, the application must find nothing on it.** The mean and each of the 8 frames go through
the application's own stages 1 to 3 (`Background_Difference`, `Foreground_Mask`, FastSAM, `Fuse_Objects`)
with the mode's parameters, against the reference in force; any object the fusion keeps (above
`Min_Area_Fraction`) refuses the reference and is listed by box, share of the frame and region. Each frame is
checked, not only the mean: a hand in one frame is an eighth as strong in the mean (130 grey levels become 16,
under the floor of 28).

**Why FastSAM, not the background difference alone.** On the 41 test frames the difference alone does not see
38 of the 150 objects, among them the 60 × 40 mm plate in `Image_062`. FastSAM sees all 150, and on the empty
table (rig, 2026-10-13, 16 frames, both modes) it returns no mask and the fusion finds nothing; the fresh
frames differed from `Image_Background_001` by at most 23 grey levels.

**When the reference in force no longer matches the camera** — a new calibration or window makes the load fail
until a new reference is shot — comparing with it would mean nothing. `Load_Configuration_For_Reference`
returns its problems instead of failing (nothing else is relaxed); the check then runs FastSAM alone, the
sidecar records `compared_with: null` and `not_compared` (the reason), and the tool prints a warning. On
`Image_062` FastSAM alone finds the same objects as the application (boxes within a pixel or two).

**Why 8 frames.** Measured on the rig on 2026-10-13: an empty table, 16 frames through the application's
camera path, then the 41 test frames analysed in the catalogue mode against each candidate, with the
describer off.
- Temporal noise is 5.9 grey levels per pixel. Against held-out empty frames, the difference's 99th
  percentile is 11 with one frame, 9 with 4 and 8 with 8.
- No candidate changed a count, a side or a verdict: OK 17, Warning 128, NOK 5 for every reference.
- Sizes moved as follows:

  | References compared | Sizes moved, mean | p95 | Max | Displayed sizes changed |
  |---|---|---|---|---|
  | Two single frames | 0.011 mm | 0.063 mm | 0.20 mm | 54 / 150 |
  | Two independent 8-frame means | 0.005 mm | 0.036 mm | 0.16 mm | 36 / 150 |
  | `Image_Background_001` against a new 8-frame mean | 0.014 mm | 0.069 mm | 0.25 mm | 57 / 150 |

- 16 frames added little over 8, and 8 frames take about 2.6 s (0.32 s per grab).

Averaging is not "more correct": it makes the reference, and so the sizes, depend half as much on which frame
was grabbed. Not measured: Gemma's background sentence from an averaged reference; another light or table;
flat objects FastSAM misses, which the test set does not contain.

**Camera in use.** With the application connected, pylon lists the camera but `IsDeviceAccessible` is false,
and opening it fails with *The device is controlled by another application* (rig, 2026-10-13, with a second
process holding it). `Basler_Cls` now raises `Basler_In_Use_Error_Cls` at once instead of retrying ten times
a second apart, and the camera layer reports `Camera_In_Use_Error_Cls` (a `Camera_Error_Cls`) naming the camera
and saying to press DISCONNECT, in the application and in the scripts, where it used to say "No Basler camera
was detected".

**Revisit if** a part FastSAM misses on the empty-table check is ever left on the table (the check would then
need its own, lower difference threshold); the light changes enough that a fresh empty frame differs from the
reference in force by more than the floor (the tool would refuse an empty table; FastSAM alone is then the
check, as for an out-of-date reference); or the camera's noise or frame time changes the 8-frame trade-off.
Tests `test/Camera/test_reference_harnesses.py` (the mean, the refusals, the stale reference, the station
file, the camera in use, the removed flags; `test_the_check_finds_what_the_application_finds` with the real
FastSAM), `test/Camera/test_basler.py` (the in-use refusal and its report),
`test/Configuration/test_core.py` (`Load_Configuration_For_Reference`, `Reference_Line` inside a block).

## A replaced image never keeps its name

The failure mode, recorded because it has now happened four times: **when an image is replaced
rather than added, everything keyed to its filename silently re-points at the new image.** A test, a
note, a measured number or a capture record that names `Image_004.png` does not know the bytes
changed; it goes on citing, asserting or loading whatever now carries the name.

1. **The first renumbering.** The frame committed as `Data/Image_006.png` became `Data/Camera/Image_001.png`
   and later `Data/Images/Test/Image_001.png` (one blob, three names); notes written against the old
   numbers pointed at different images. A clone at the old commit still has them under the old names.
2. **`eb00508` deleted the seven test frames and added thirteen others under the same names.**
   `All/Image_001` is not the old `Image_001`. The tests' pins (`Image_001` → nine objects, `Image_004`
   → one plate) looked for the old names in the old folder, found nothing and *skipped* — two tests
   tested nothing from then on, and nothing said so. Measured evidence citing `Image_002–005` cited
   frames that no longer existed.
3. **`eb00508` overwrote `Data/Images/Background/Image_Background_001.png`** with a new reference
   shot under the new calibration. Capture sets record the reference by path
   (`_objects.json` `background_reference`), so every set made before then names an image it was
   not differenced against.
4. **`b5ca788` removed `All/Image_009`–`013` and left their pins in place:** the five inventory counts
   and the strict xfails on 009, 011 and 012. The xfails expected an `AssertionError`, and a missing
   frame raises one, so three of the five read as expected failures; only 010 and 013 failed, and only
   under `--runslow` with the weights. Not a replacement, but the same failure: the name outlived the
   frame, and the pins did not follow the set.
5. **On 2026-10-11 the set was replaced whole, and the names were not reused.** Forty-one frames of a
   2026-10-09 session took the place of `All/` and its raw-capture neighbours, directly in
   `Data/Images/Test`. They arrived as `Image_001`–`041`; none matched any committed image by bytes or
   by pixels. The names `Image_001`–`013` were still cited for the previous set's evidence, so the new
   frames were numbered `Image_014`–`054`, the inventory was recounted by eye and confirmed by the owner,
   and every citation of `All/` says in place that its frame is gone (recoverable from `1061966`).
6. **Those 41 were the wrong file of each capture set, and their replacements took new names too.** They
   were the sets' `_distorted.png` files, the frame before undistortion, not `_raw.png`, the frame the
   application analyses. Against the reference, which went through the undistortion, nine of them
   counted one object too many, in the bottom-right corner where the undistortion leaves a dark border
   the frames lacked (the reference's border has 5,271 px in the outer 40 px ring; the 41 frames had 151
   in common). The same scenes' `_raw.png` files are different images, so they are `Image_055`–`095`, not
   014–054. Each was paired with the frame it replaces by content — it equals, pixel for pixel, the
   application's undistortion of that frame with the calibration in force (the set ids of the
   `_distorted.png` files were not kept) — and took its confirmed count. All 41 match their counts, so
   the strict xfails on the nine were removed with their KNOWN_ISSUES entry. **A test frame is a capture
   set's `_raw.png`**: the name says unannotated, not unprocessed; `.gitkeep`, the README and the capture
   checklist say so.

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
Tests `test/Logger/test_core.py::test_csv_filename_follows_the_hardware_of_the_loaded_configuration` (*Corrected 2026-10-08:* renamed from `…follows_the_loaded_configuration`),
`::test_logger_requires_the_configuration_to_be_stated`.

## Run-summary CSV: six time-account columns; an older format is archived, never appended to

The CSV is cut to `log_file, application_start, application_stop, cycle_time, total_session_time,
idle_time` — the run's time account: when the application ran, for how long, how much of that a
camera was connected (*corrected 2026-10-07:* how much of it the station worked, scan to the end of
analysis, under format version 2), and how much it was idle (`cycle_time == total_session_time + idle_time`
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
(`Vision.Utilities.Measure`), converted through the calibration file's `Calibration.Conversion_Factor`
(*Corrected 2026-10-08:* this named `Camera.Calibration.Conversion_Factor`, which is not a key path).

- **The factor is millimetres per pixel.** The YAML labels it `[mm/px]`, and the calibration
  derives it as `square_size_mm / mean corner spacing in px`
  (`Calibration.Core.__Get_Pixel_To_MM_Factor`; *Corrected 2026-10-08:* now `__Solve_Factor` and
  `__Solve_Scale`) — so `mm = px × factor`, per axis. Two physical
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
  (`b5ca788^`; that folder is no longer in the repository, recoverable from `1061966`, and the figures are not re-measured on the
  current set) put round parts at 1.002–1.016 and the least elongated non-square part at 1.468 (the
  robot in 005; the plates 1.49–1.60). Re-measured on the eight left after `b5ca788`, every figure
  holds except the plates, 1.49–1.54. **A square is the exception:** it is as un-elongated as a
  disc (1.013, the milled square plate in `All/Image_008`) but its sides are real edges that `minAreaRect`
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
  `Data/Images/Test/All` (2026-09-28, no longer in the repository, recoverable from `1061966`; 9 round and 6 hexagonal instances of 4 washer/bushing and 2
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
  set, `eb00508^`) the two nuts moved from Ø 12.0 to A/F 11.7 mm and from Ø 11.6 to A/F 11.5 mm — much
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

*Evidence from the previous test set* — the seven frames removed in `eb00508` (recoverable from `eb00508^`; their names do not match `Data/Images/Test`). *Not re-run on the current set: it needs the describer run and its text read. The `Image_NNN` names below refer to that set.*

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

*Evidence from the previous test set* — the seven frames removed in `eb00508` (recoverable from `eb00508^`; their names do not match `Data/Images/Test`). *Not re-run on the current set: it needs the describer run and its text read. The `Image_NNN` names below refer to that set.*

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
`::test_object_description_detail_reading_and_fallback` (*Corrected 2026-10-08:* renamed from `test_describe_…`),
`test/integration/test_pipeline.py::test_pipeline_camera_to_reporting`.


## The label distiller peels Gemma's opener — and the label is still weak

*Evidence from the previous test set* — the seven frames removed in `eb00508` (recoverable from `eb00508^`; their names do not match `Data/Images/Test`). *Not re-run on the current set: it needs the describer run and its text read. The `Image_NNN` names below refer to that set.*

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

*Evidence from the previous test set* — the seven frames removed in `eb00508` (recoverable from `eb00508^`; their names do not match `Data/Images/Test`). *Not re-run on the current set: it needs the describer run and its text read. The `Image_NNN` names below refer to that set.*

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

*Evidence from the previous test set* — the seven frames removed in `eb00508` (recoverable from `eb00508^`; their names do not match `Data/Images/Test`). *Not re-run on the current set: it needs the describer run and its text read. The `Image_NNN` names below refer to that set.*

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

*Evidence from the previous test set* — the seven frames removed in `eb00508` (recoverable from `eb00508^`; their names do not match `Data/Images/Test`). *Not re-run on the current set: it needs the describer run and its text read. The `Image_NNN` names below refer to that set.*

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
  `Data/Images/Test` frames: time per object, peak memory, word-for-word stability.
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
bare literals in a commit about the Annotated/Mask toggle (`94b74fa`), with no comment or reason,
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

*Corrected 2026-10-14, the JIC Smart Factory palette:* the controls are outlined in the one purple `#640ABA`, as the
brand's buttons are: a plain button and an unselected segment in a 1 px purple rule (neighbouring segments share
one), ANALYZE in a 2 px one, all on the white card with a purple label (9.15:1). A hovered plain button fills
grey-lilac (6.79:1), a pressed one periwinkle (5.71:1); a selected segment, and a hovered or pressed ANALYZE, fill
purple under a white label (9.15:1). With one purple there is no darker hover fill, so a selected segment's hover
keeps the selected look: clicking it does nothing. The harness's self-check that every hover changes pixels exempts
the selected segments by name and still holds every other control to it. Disabled labels are `#B4A6BE` (2.30:1,
exempt), their rule the divider grey-lilac.

## One configuration file per mode, one calibration per camera, decided before the first CONNECT

*Corrected 2026-10-11: the camera block and the background reference are no longer in the mode file. They
are the station's, in `Station_<Hardware>.yaml` beside it, shared by every mode and never overridden by one
([*The station file holds the camera and the reference…*](#the-station-file-holds-the-camera-and-the-reference-and-a-mode-file-never-overrides-it)).
The rest of this entry stands.*

*Corrected 2026-10-13: the calibration is no longer found by the hardware beside the mode file, and is no
longer optional. The station file names it (`Calibration`), the mode file names the station (`Station`),
each kind in its own folder; nothing loads uncalibrated, and `calibrate.py` reads the station's camera alone,
so a new camera can still be calibrated. `Write_Calibration` now refuses any existing file
([*The configuration is a chain of references…*](#the-configuration-is-a-chain-of-references-mode--station--calibration-each-kind-in-its-own-folder)).
"Calibration lives once per camera, and is optional as a whole" below is superseded by that entry; the
rest stands.*

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

*Evidence from the previous test set* — the seven frames removed in `eb00508` (recoverable from `eb00508^`; their names do not match `Data/Images/Test`). *Not re-run on the current set: it needs the describer run and its text read. The `Image_NNN` names below refer to that set.*

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

**Why.** Until commit `58bed68` a second detector, `CONST_DETECTOR == 'florence'`, ran Florence-2's
`<REGION_PROPOSAL>` on the whole frame with no reference — the only path that could analyse an
arbitrary image. No code set it (the default was `'fastsam'`), no test exercised it, and it was slower
than FastSAM: an untested branch carrying a capability nothing used. The application, `analyze.py` and
the tests all supply a reference, so nothing regressed. The capability lost is analysing a one-off
image from a camera with no reference capture. (Moved here from KNOWN_ISSUES on 2026-09-24.)

**Revisit if** the application has to analyse images from a camera with no empty-surface reference.
Restoring it means a whole-frame detector ahead of stage 1, the describe-each-box loop and its crop
helper (all recoverable from `58bed68`'s parent) — and the test the original never had.
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
put its heading below the text it headed until it got its own tokens (commit `3c908b1`). Live and
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
- **The logos are copied inline, not referenced.** An SVG loaded through `<img>` never fetches
  another file, so a referenced logo would draw nothing. The AnyScan logo and the JIC Smart Factory logo are inlined
  as SVG (between `logo:` and `jic:` marker comments, which the token test leaves out: they are brand artwork in their
  own colour), and the funding band's marks are embedded as base64 PNG for the same reason; the generator reads them
  from `images/` and `App/assets/`, so a changed mark makes the committed SVG stale and the whole-file test fails.
  There are three copies of the AnyScan logo: `images/`, `App/assets/` and the one the generator inlines. A test holds
  all three equal. After a new logo run `Example/UI/build_logo.py`, then regenerate.
- **The card icons are pixel icons.** *Updated 2026-10-14, the owner's choice from renders:* the stroked line icons
  (24-unit grid, round caps) are replaced by icons in the JIC Smart Factory guide's pixel style, each a 12 × 12 grid
  drawn as one path of 3 px squares (`CONST_ICONS`, `CONST_ICON_SIZE` 36). At the line icons' 28 px a cell would be
  2.33 px and the grid smeared; at 3 px a cell they stay legible at README width. A test holds every grid to
  12 × 12 at whole-pixel cells (`test_the_diagram_icons_are_twelve_by_twelve_pixel_grids`).
- **The logo's colour is its own.** *Corrected 2026-10-14:* the delivered logo is one purple, `#640ABA`, the JIC
  Smart Factory primary; until then the logo kept a palette that predated the theme (indigo and the magenta
  `#D6006E`). The diagram draws it as delivered whatever the theme is.

**Revisit if** the logo is redesigned (rebuild it with `Example/UI/build_logo.py`, regenerate), or
if the code changes what the diagram shows. The generator holds the colours; the content is
still written by hand in the generator, and the README link is what keeps it in view.
Tests `test/UI/test_brand_figures.py` (`test_the_three_logo_copies_are_identical`,
`test_the_diagram_is_the_generators_output`, `test_the_diagram_draws_only_theme_tokens`,
`test_the_readme_shows_the_diagram`).

## The logo's text is outlined, so the logo has the same width in every font setup

`images/anyscan-logo.svg` is the AnyScan logo as the JIC Smart Factory designer delivered it (2026-10-14), committed
byte for byte: one purple, `#640ABA`, the mark's brackets and object as strokes and fills, and the wordmark and
tagline as three outlined paths, so it carries no `<text>`. Its viewBox is 609.8 × 140 units; the mark's brackets
reach the top and the bottom, and the ink ends 5.9 units inside the right edge. The previous logo (indigo and magenta,
outlined from `images/source/anyscan-logo-text.svg` in Inter by Inkscape) and its text source are removed.

The application's copies are derived, never edited: `python Example/UI/build_logo.py` copies the logo to
`App/assets/anyscan-logo.svg` and writes `App/assets/anyscan-logo-wordmark.svg` (the logo without its tagline, which
the top bar draws), `App/assets/anyscan-mark.svg` (the mark alone: the empty viewport, the icon's source) and
`App/assets/anyscan-mark.ico` (the mark on a white square, rendered at each of 16-256 px). The derivation is string
surgery on the delivered file, so every byte it keeps is the designer's: the text is the three top-level paths after
the mark's groups, the tagline the one starting below y 107.5. No font and no Inkscape are involved, so it reproduces
on any machine. **Reproduced:** the derived mark is byte for byte the mark file delivered with the logo
(`AnyScan_mark_PURPLE.svg`), and a rebuild into an empty directory reproduces the committed SVGs.

The JIC mark beside it is the JIC Smart Factory horizontal logo in purple (`App/assets/jic-smart-factory.svg`, the
designer's file), at 26 px, about half the AnyScan logo's height as on the poster. The grey variant is for dark
grounds; nothing in the application or the diagram has one, so it is not shipped.

**Why.** PyQt5's QtSvg 5.15 ignores every CSS `font-*` property (measured 2026-09-28: a CSS `fill` changed 2,500 px,
a CSS `font-family`, `font-weight` or `font-size` changed 0), so a logo with `<text>` was drawn in the application's
default font, which clipped the old tagline on Linux. Outlined, the logo renders identically under any application
font. The delivered file is outlined already, so the project no longer outlines anything; what it needs is its own
copies (the logo without its tagline, the mark), and deriving them from the one delivered file keeps them in step.

In the top bar the logo, the divider and the JIC mark are spaced `AnyScan_Window_Cls.CONST_BRAND_GAP`
= `Style.CONST_MARK_GAP` (32 px) apart, measured from ink: `Style.Ink_Insets` takes each image's transparent margin
off the spacing. The architecture diagram follows the same rule (`Header_Positions` in
`Example/UI/architecture_diagram.py`), scaled from the lockup to the diagram's logo.

`Style.Load_Svg` takes an SVG's aspect ratio from its viewBox, read as real numbers (*Corrected 2026-10-14:* it read
Qt's `defaultSize()`, which truncates to whole units, so the delivered logo's 609.8 units were drawn as 609 and the
logo was squeezed 0.13 % across; the test comparing the mark with the logo's mark found it).

**Revisit if** the logo is redesigned: commit the new delivered file as `images/anyscan-logo.svg`, run
`Example/UI/build_logo.py` (it stops if the file is no longer three text paths after the mark), then regenerate the
diagram; the tagline's live position (*The header draws the delivered logo and sets its tagline as live text*) must
follow it.
Tests `test/UI/test_brand_figures.py` (`test_the_logo_renders_the_same_in_any_default_font`,
`test_the_three_logo_copies_are_identical`, `test_the_derived_logo_files_rebuild_byte_identically`,
`test_the_wordmark_and_the_mark_are_the_logos_own`, `test_the_diagram_is_the_generators_output`),
`test/UI/test_header.py`.

## Gemma 4 12B was measured against E4B and is not better; E4B stays the describer

*Evidence from the previous test set* — the seven frames removed in `eb00508` (recoverable from `eb00508^`; their names do not match `Data/Images/Test`). *Not re-run on the current set: it needs the describer run and its text read. The `Image_NNN` names below refer to that set.*

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
flag is given. *Corrected 2026-10-08:* `--model` was removed on 2026-09-29 and the 12B is no longer
supported (*No longer supported (2026-09-29)*, under *E4B stays the describer on both machines*);
`test/Install/test_install.py` now pins `--model` as an unknown option.
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

  These are estimates: nothing has run on Linux. *Corrected 2026-10-08:* the 2026-09-29 Linux run
  measured a 9.5 GB whole-application peak, which the 11 GiB floor clears (*The installer on Linux:
  detection and the Gemma download ran, the rest did not*); the `--model 12b` bullets here and below
  describe an option removed that day.
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

*Evidence from the previous test set* — the seven frames removed in `eb00508` (recoverable from `eb00508^`; their names do not match `Data/Images/Test`). *Not re-run on the current set: it needs the timing run again. The `Image_NNN` names below refer to that set.*

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
as painted); commit `aae4fd1`. The load and warm-up log lines:
`test/UI/test_timing_log.py::test_a_configuration_load_logs_each_model_and_the_warm_up`,
`::test_a_warm_up_that_stops_early_is_a_warning`, `::test_the_first_analysis_after_each_load_is_marked`.

## The logo is taller on a low-density display, so its tagline is 9 pt

Below a device pixel ratio of 1.5 the top bar draws the AnyScan lockup as tall as it must be for the logo's tagline,
24.55 of its 140 units, to be 9 pt (`Style.CONST_TYPE_FLOOR_LOW_DENSITY`) in the widget's logical DPI, rounded up to a
whole pixel: 69 px at 96 dpi, 72 px in the offscreen tests (100 dpi). At 1.5 and above it is 54 px
(`Style.CONST_LOGO_HEIGHT`). `Style.Logo_Height(widget)` chooses, through `Style.Is_Low_Density(widget)`, the one
density check. The JIC Smart Factory logo beside it scales with it (26 px beside 54 px, 35 px beside 72 px; the
owner's decision of 2026-10-14), so the pair keeps its proportions at both densities. The spacing to the divider is
measured from ink (`Style.Ink_Insets`), so the 32 px gap holds at both.

How the ratio is read, and its limit: Qt 5.15 gives a widget the ratio of its top-level window's screen once that
window has a native handle. The header is built before the window is shown, so it reads the application's ratio, the
highest of all screens: a machine with a Retina and a 1x screen gets the 54 px logo on both. The height is read once;
nothing re-reads it when the window moves to a screen of another ratio.

**Why.** The delivered logo sets its tagline at 7 pt when the lockup is 54 px. At DPR 1, at that size, the outlined
tagline has 0.009 of its ink at full contrast and live text 0.011 (measured 2026-10-14, offscreen at 100 dpi): neither
is sharp, so setting it live only helps at a larger size. At 9 pt the live tagline is 0.179 (and the outlined one at
the same height 0.147). The owner chose, from renders at 1x, to grow the whole lockup on a low-density display rather
than set the tagline beside the wordmark at 9 pt or keep it outlined at 7 pt; the logo keeps its proportions. The mark
and the wordmark are sharp at every height tried (0.57-0.76 of the mark's ink and 0.62-0.72 of the wordmark's at full
contrast from 48 to 66 px), so the height is set by the tagline alone.

*Corrected 2026-10-14:* until the delivered logo, this entry was "The logo is 59 px on a low-density display": 59 px
put the previous logo's 4-unit brackets on whole pixels. That reason went with that logo.

**Revisit if** the logo is redesigned (its tagline's share of the height sets the 1x size), if the type floor
changes, or when the window re-reads its screen's ratio on a screen change.
Tests `test/UI/test_header.py::test_the_logo_puts_its_tagline_at_9_pt_on_a_low_density_display`,
`::test_the_logo_is_54_px_on_a_high_density_display`, `::test_the_jic_logo_keeps_its_share_of_the_lockup`,
`::test_the_tagline_is_crisp_on_a_low_density_display` and
`::test_the_header_is_measured_again_at_dpr_2` (the module run again at `QT_SCALE_FACTOR=2`), with
`::test_the_brand_marks_are_spaced_by_the_brand_gap_from_ink` at both ratios.

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
(then `brand-jic-mute.png`) was artwork tinted with the old value and was not re-tinted.
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

*Corrected 2026-10-14, the JIC Smart Factory palette:* the muted ink is `#6F5783` (the purple's hue at L\* 41,
chroma 28: 6.24:1 on white, 4.63:1 on the grey-lilac); the status words are the JIC green's and amber's hues at L\* 41
(`#00711B`, `#7C5B00`, 6.2:1), their dots at L\* 60.5 (3.1:1, the graphic floor). The viewport is no longer dark:
it is the grey-lilac `#E1DCE6`, its text the purple (6.79:1), and a failed set's thumbnail says so in the Log's
error colour `#BE0362` (4.61:1), so `CONST_ERROR_ON_DARK` is removed.

## The UI fonts are bundled: static Public Sans and JetBrains Mono at the four weights the UI requests

`App/assets/fonts/` ships Public Sans and JetBrains Mono, each as four static files (Regular 400, Medium 500,
SemiBold 600, Bold 700: the QFont Normal, Medium, DemiBold and Bold the UI requests), with each family's SIL Open Font
License text (`PublicSans-OFL.txt`, `JetBrainsMono-OFL.txt`). `Style.Load_Fonts` registers every .ttf there, and its
candidate lists pick Public Sans and JetBrains Mono first; the system faces after them are only the fallback for a
missing directory. Inter and Inter Display, the UI face and the previous header's wordmark cut until 2026-10-14, are
removed with the logo they were outlined from.

They are built, never edited: `python Example/UI/build_fonts.py` downloads the variable fonts and their licences from
google/fonts commit `e1d6480102fed30739fead0faee463101f892c8f`, stops unless each SHA-256 is the pinned one
(`PublicSans[wght].ttf` `d75a7dc1…`), and instances every weight with fontTools (4.66.0; another version builds with a
WARNING). The name table and `usWeightClass` are set so Qt lists each family with its styles. The source's
timestamps are kept, so the output does not depend on the clock. **Reproduced:** a build into a temporary directory
gave the same ten files, byte for byte, as the committed ones (2026-10-14).

**Why.** None of `Load_Fonts`' candidates was installed on the Linux test machine, so the UI was drawn in fontconfig's
substitute (Noto Sans, Regular and Bold only: the UI's 500 drew Regular and its 600 Bold), and on macOS in Helvetica
Neue, which has no SemiBold. Static files, not the variable ones: Qt 5.15 exposes only a variable font's default
instance and synthesises every other weight (a button label's full-contrast share fell from 0.42 to 0.20 with a
variable face, measured 2026-09-29). Committed, not fetched by `install.sh`: an installer fetch would add a network
step and a fontTools dependency, and an offline install would silently fall back. Subsetting to Latin was not done: a
model sentence with a character outside the subset would switch faces mid-line.

**Revisit if** the UI requests a weight outside the four (the test reads the weights from the source and fails), or
Qt is upgraded to one that uses variable-font axes.
Tests `test/UI/test_fonts.py::test_the_ui_and_monospace_families_resolve_to_the_bundled_fonts`,
`::test_every_requested_weight_draws_its_own_face` (ui, mono), `::test_each_bundled_family_ships_its_licence`.

## The UI is set in Public Sans, the open font closest to the brand's GT America

The JIC Smart Factory guide sets its type in GT America Standard and GT Super Display, commercial faces that cannot be
distributed with the application. The UI is set in Public Sans (SIL OFL 1.1), the open font that came closest to GT
America Standard; no serif is used in the application.

**Why.** Each candidate was set at GT's cap height on the same English lines and measured against it (2026-10-14):
x-height over cap height, the width of one line, the mean pixel overlap (IoU) of 18 glyphs centred at equal cap
height, and the ink of "n".

| Face | x/cap | width vs GT | glyph overlap | weight vs GT |
|---|---|---|---|---|
| GT America Standard | 0.709 | (reference) | (reference) | (reference) |
| **Public Sans** | 0.713 | +0.9 % | **0.773** | +5 % |
| Libre Franklin | 0.713 | −2.2 % | 0.712 | −5 % |
| Inter (the previous UI face) | 0.750 | +3.2 % | 0.712 | +13 % |

For GT Super Display, Newsreader at opsz 72 was closest (x/cap 0.713 against 0.722, width −0.9 %, overlap 0.551),
ahead of Playfair Display (0.563 overlap, but much finer hairlines) and Fraunces (−13.7 % wide). The owner chose to
leave the serif out of the application: its largest heading is a 15.5 pt card title. Words are set in Public Sans and the
monospace face (JetBrains Mono) only for machine values, times, sizes, the resolution and the Log's columns, where
fixed-width digits keep a column still. *Corrected 2026-10-14:* the badge's chips ('No frame', 'Idle', the verdicts),
the empty Camera View's instruction, the busy overlay's status and History's empty-pane message were monospace with no
recorded reason; they are set in Public Sans
(`test/UI/test_fonts.py::test_chips_and_the_empty_camera_view_are_set_in_the_ui_face`). The GT files were only read for
the comparison, from the owner's `design/` folder, which stays out of git.

**Revisit if** the brand's typefaces change, or GT America becomes distributable with the application.
Tests `test/UI/test_fonts.py::test_the_ui_and_monospace_families_resolve_to_the_bundled_fonts`.

## A 9 pt type floor on a low-density display

Below a device pixel ratio of 1.5 (`Style.Is_Low_Density`) no text is set below 9 pt
(`Style.CONST_TYPE_FLOOR_LOW_DENSITY`): `Style.Font`, which builds every font in the UI (painted text
included), raises a smaller size to 9 pt there. At DPR 1.5 and above every size is as written. The ratio is
the application's, read when the font is built: the value a widget reads before its window is shown, with
the same limit as the logo (a screen change does not rebuild fonts; *The logo is taller on a low-density
display, so its tagline is 9 pt*). It raises ten chrome styles, all 7.5-8.5 pt: the frame and stage badges (`Widgets.py`
`Badge_Cls`), the status-strip labels (`Stat_Cell_Cls`), the funding note (`Funding_Row_Cls`), History's
card time, card count and failed thumbnail (`History.py` `Thumb_Card_Cls`), and in `History_View_Cls`
its rolling-window note, image captions and connection group label and count. (*Corrected 2026-10-08:*
these were cited by line number, which had drifted.) Content sizes
(`CONST_TYPE_SCALE`, smallest 9.5 pt) are not touched.

**Why.** On a 1x monitor a regular-weight 7.5-8.5 pt text is 10-11 px, and at that size 0.02-0.05 of its
ink reaches full contrast, in Noto Sans and in the then bundled Inter alike; at 9 pt (12 px) it is 0.12-0.19
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

## The header draws the delivered logo and sets its tagline as live text

The top bar's lockup is `Widgets.Logo_Lockup_Cls`: the delivered logo without its tagline
(`App/assets/anyscan-logo-wordmark.svg`, *The logo's text is outlined*) as an SVG pixmap at `Style.Logo_Height`, and
the tagline drawn as live text where the logo outlines it, in the bundled Public Sans Regular, in the logo's colour
`Theme.CONST_LOGO_INK` (`#640ABA`, the logo's fill). The mark and the wordmark stay the designer's outlines: they are
large enough to be sharp at every density (*The logo is taller on a low-density display*).

- **Place and size:** `Style.CONST_LOGO_TAGLINE_ORIGIN` (166.69, 128.0) and `CONST_LOGO_TAGLINE_SIZE` 24.55, in logo
  units. The outlined tagline's "T" starts at x 167.25, its cap top is at 110.25 and its baseline at 128.0, a cap
  height of 17.75 units; Public Sans's cap height is 0.723 em and its "T" starts 0.023 em right of the pen, so the
  size is 17.75 / 0.723 and the pen 0.56 units left of the ink. The size is converted to points through the widget's
  DPI and built with `Style.Font`; Qt draws it at a whole pixel (13 px in the offscreen tests, 1.03 × the logo's).
- **Measured** against the outlined logo rendered at the same height, every offset within 1 device px at DPR 1 and 2:
  mark to wordmark, wordmark to tagline (left edges and baselines), both cap heights (the tagline's at the size Qt
  draws) and the wordmark's width.
- **Unchanged:** `images/anyscan-logo.svg`, its copy in `App/assets/` and the diagram's inline copy are the whole
  outlined logo; the diagram is a vector figure, read at its full size.

**Why.** The owner asked for the delivered logo, and for its tagline as live text if the outlines are soft at 1x.
They are (0.009 of the tagline's ink at full contrast at 54 px). Live text is hinted by FreeType at 9 pt and above,
where the lockup puts it at DPR 1. Public Sans, the UI face, is the open font closest to the logo's GT America
(*The UI is set in Public Sans*), so the live tagline is within a pixel of the outlined one.
*Corrected 2026-10-14:* until the delivered logo this entry was "The header's wordmark and tagline are live text":
the previous logo's wordmark and tagline were both live, in Inter Display and Inter, over its mark.

**Revisit if** the logo is redesigned (the tagline's origin and size follow the new outlines; the header test holds
them), or when Qt 6 is adopted (it draws fractional sizes).
Tests `test/UI/test_header.py::test_the_lockup_matches_the_outlined_logo` (both densities),
`::test_the_tagline_is_crisp_on_a_low_density_display`, `::test_the_lockup_tagline_is_the_bundled_public_sans`,
`test/UI/test_brand_figures.py::test_the_live_tagline_is_the_logos`, `::test_the_wordmark_and_the_mark_are_the_logos_own`.

## E4B stays the describer on both machines: the owner's choice, one wrong statement ahead of the 12B

**Decided by the owner, 2026-09-29: keep Gemma 4 E4B.** The shipped configuration names it, and one
configuration is shared by both machines, so History and Trends compare like with like.

The comparison rests on an answer key, `Data/Images/Test/All/answer_key.json` (the key and its eight frames
are no longer in the repository, recoverable from `1061966`; the current set has no key yet). It names, for each of the 37
objects the shipped pipeline finds in the eight frames (numbered in the pipeline's order), its part type,
material and colour, each with its source (`CONST_INVENTORY`, judged from the crop, or the owner from the
physical part). The owner confirmed every entry on 2026-09-29. The scoring rules, the synonym patterns, the
naming cues and the other materials are data in the key. `Vision.Utilities.Evaluation` is its only reader
and scorer, and `Example/Vision/evaluate_describer.py` runs the configured describer through the
application's path and scores it (`--describer-model` swapped the model in memory, not in the file, for
these comparisons; removed on 2026-09-29).

Both models ran the same crops (identical pixel for pixel) with the shipped prompts. Totals over all 37
objects, as the scorer gives them and as checked by hand (every "not stated" was read; the scorer agrees
with the hand check on every one). Every object counts, by the owner's choice: the two small hex nuts
(5.3, 6.2), whose crop hides their corners, carry a `note` in the key saying so, not an exclusion.

| Attribute (correct / wrong / not stated) | E4B 4-bit | 12B |
|---|---|---|
| Part type | 15 / 6 / 16 | 25 / 2 / 10 |
| Material | 26 / 1 / 10 | 26 / 6 / 5 |
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
  wrong ("felt or fabric"), and synonyms count in the plural ("strips"); (4) material hedges score as
  type hedges do: the right material beside any other is not stated ("plastic or composite", "metallic or
  ceramic": E4B's comb and robot, the 12B's washer and robot, 28 -> 26 correct for each). Scoring on the
  app's short label (`Condense_Label`) was tried and rejected: it dropped names the text gives.

**The 8-bit E4B is not better: don't switch.** `mlx-community/gemma-4-e4b-it-8bit` at revision
`4255b21bd9a9d3fc807ef7abd80373f5e3a52a73` (8.91 GB, every file checked against its published hash) ran
through the same script, twice, with identical text. On the same 37 objects:

| Attribute (correct / wrong / not stated) | E4B 4-bit | E4B 8-bit |
|---|---|---|
| Part type | 15 / 6 / 16 | 16 / 5 / 16 |
| Material | 26 / 1 / 10 | 26 / 3 / 8 |
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

**Why.** On all 37 objects, with the hand-checked scorer, E4B makes 7 wrong statements and the 12B 8, so the
count alone barely separates them (a first reading, 4 against 8, rested on 35 objects and a scorer that
missed invented names). The owner chose E4B on the kind of error and the cost: the 12B names ten more part
types but calls six plastic parts metal, while E4B hedges, and its errors are part names; E4B is 1.7x
faster (0.65 against 1.10 s per object here; 2.2 against 5.5 s on the Mac) with 2.1 GB less GPU memory;
the prompts were tuned on it; and keeping it leaves every stored description comparable.

**Revisit if** a 12B-specific prompt is tried (score both again), the prompts are rewritten
(re-run both models), a new describer or E4B conversion is proposed (score it with the script against the
same key; the 8-bit is not worth measuring on the Mac unless it beats the 4-bit here), or the segmentation
changes: the script stops when a frame's object count differs from the key's, and the key must be
re-confirmed.
Tests `test/Vision/Utilities/test_evaluation.py` (on this key, kept byte for byte as
`test/Vision/Utilities/data/answer_key_1061966.json` since its frames left the repository: it records the
owner's answers, and each scoring rule, including `::test_a_wrong_name_after_the_first_sentence_counts`,
`::test_a_material_outside_metal_and_plastic_is_wrong_alone`, `::test_a_plural_synonym_counts`); the run
itself needs the weights and is the script, not a test.

**No longer supported (2026-09-29):** Gemma 4 12B and E4B 8-bit. `gemma-4-e4b-it-4bit` is the only describer;
`./install.sh --model` and `evaluate_describer.py --describer-model` were removed. The comparisons above remain
the evidence for the choice.

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

**Why.** In the real window (`docs/evidence/label-2026-09-29/` at commit `2607804`: grabs of Image_003 and
Image_005 and their log lines; *Corrected 2026-10-14:* the folder was removed from the tree, and this cited
it as present, so it is read from history, `git show 2607804:docs/evidence/label-2026-09-29/`) the label
only reaches the log; History stores the full description and no label. There it
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

## The installer on Linux: detection and the Gemma download ran, the rest did not

Recorded 2026-09-29 from that day's Linux run (commit `3cec51a`, README > Platform; the machine's
measurements are in *E4B stays the describer on both machines*). Nothing was re-run for this entry.
It keeps "tested" and "ran for real" apart for each installer path, as the Mac's runs are kept apart
in `test/Install/test_install.py`'s docstring.

- **Ran for real on Linux** (Ubuntu, RTX 5070 Ti 16 GB, driver 595.91.07, Python 3.11.16):
  - detection, as `./install.sh --detect-only`: the CUDA 13 branch, `mlx[cuda13]` and the `cu130`
    PyTorch build, 15.9 GB read on GPU 0;
  - the Gemma step (`Ensure_Gemma`): the real `hf download` of E4B at the pinned revision, and the
    verification of every file against the manifest.
- **Not run on Linux:** the full install. The machine's environment was set up by hand with
  `opencv-python-headless`, and the requirements install would add `opencv-python` beside it. So
  `.venv` creation, the pip resolves on the PyTorch index and the `mlx` extra, the import check, the
  FastSAM step and the configuration check have not run there.
- **Not run on any machine:** the CUDA 12 path (`mlx[cuda12]`, `cu126`), the CPU path (`--cpu`,
  `mlx[cpu]`), and every refusal (no driver, an old driver, low compute capability, too little
  memory). Stubbed tests cover them.
- **The 11 GiB floor stands.** It was set from an estimate (~8.5 GB, *Linux: MLX's CUDA backend…*);
  the measured whole-application peak is 9.5 GB of GPU memory, 6.99 GB of it MLX, which it clears.
  The installer's comment and refusal message now give the measured peak.

**Revisit if** a machine runs the full Linux install, the CUDA 12 path or the CPU path: record it
here, then update README > Setup and the docstring of `test/Install/test_install.py`.
Tests `test/Install/test_install.py` (the stubbed branches); commit `3cec51a` for the run.

## The daily station event file is exported from the session log at close, not written live

Decided 2026-10-03. An external system tracks the station's uptime from one CSV per day,
`<General.Station_Events.Directory>/YYYY-MM-DD.csv`: `station_id,event_type,ts`, with `SF4`,
`STATION_ON` / `STATION_OFF` (application start and stop) and `CYCLE_START` / `CYCLE_DONE` (one camera
connection, CONNECT to its end), and `ts` in UTC to the second. `Logger/Station_Events.py` is the one
module that writes it. The run-summary CSV (`log_<Hardware>.csv`) is unchanged.

*Corrected 2026-10-07:* a cycle is no longer a connection but a scan, or a re-analysis, to the end of its
analysis. The connection markers are gone, and the scan and analysis markers replace them. The cycles are
`Logger.Core.Cycles`, the one computation behind this file and the run-summary CSV's `total_session_time`.
See *A cycle is a scan to the end of its analysis, not a camera connection*. The bullets on markers and
connection ends below describe the file until that date.

- **Exported, not live.** The file is generated from a finished session log (`log_*.txt`), read through
  the logger's own `Parse_Line`: the run-summary CSV's mechanism with a different structure. The logger's
  `Set_Close_Callback` runs the export after `Close` has written `Application stopped` and closed the
  file, so every close path exports: the window, the launcher's try/finally, atexit and SIGINT/SIGTERM.
  `STATION_ON` takes its time from the log's start line, which the logger now writes itself at its start
  time (it was `App/run.py`'s), so the log, the `.txt` name and the CSV's `application_start` agree.
- **Matched on markers, not wording.** The five lines that open or close the run or a connection end in
  a fixed token (`#run-start`, `#run-stop`, `#connection-start`, `#connection-end`; `Logger.Core`'s
  `CONST_MARKER_*`). The markers name the log's own events; the mapping to the four station events is
  `Station_Events`'. A line can be reworded freely; one that loses its marker fails
  `test_every_way_a_connection_ends_closes_its_cycle_and_closing_ends_it_before_station_off`.
- **Every way a connection ends closes its cycle**, because each one writes `#connection-end` in the log:
  DISCONNECT; a lost connection (`Log_Camera_Connection_Lost`); a CONNECT while a connection is still
  open (the logger closes the old one); closing the application while connected (`CYCLE_DONE` before
  `STATION_OFF`). A failed CONNECT opens no connection in the logger, so it writes nothing. The export
  can only see a loss the log records: *A lost connection is detected by the camera, not only by
  DISCONNECT* is what makes the application record one.
- **Crashed runs, and runs whose export failed, are exported at the next start.** The ledger
  `logger/station_events_exported.txt` names every exported log. At startup every `log_*.txt` it does not
  name is exported, oldest first, except this run's own log and a log another running instance still
  holds (the logger keeps an exclusive `flock` on its live log). A crashed log has no `#run-stop` and may
  have an open connection: it exports `STATION_ON` / `CYCLE_START` with no pair, and nothing is invented to
  close them. That unpaired row is what the YAML comment tells the external system an abnormal exit looks
  like.
- **The ledger line is written only after the rows.** An export that fails (a share unmounted, a full
  disk) is therefore simply not marked, and the next start retries it through the same path as a crashed
  run. At close the log is already shut, so the failure is printed to the console; at startup it goes to
  the new run's log as an ERROR and is counted in the status strip's System cell (`Report_Error`).
- **The duplicate window is accepted.** A crash between writing a log's rows and its ledger line exports
  that log twice on the next start. That window is two fsynced writes. So is the case of a run crossing
  midnight whose second file fails after the first was written: every file is opened before any row is
  written, so a missing or unwritable directory fails before any row, but a disk filling between the two
  files would leave the first file's rows to be written again.
- **No ledger yet means start here.** On the first start, every log already in `logger/` is recorded as
  handled without being exported. The logs older than the markers carry no events, and backfilling by
  sentence wording is what the markers exist to avoid.
- **The directory is required and fixed for the run.** `General.Station_Events.Directory` must exist and
  take a file at load (a probe file is created and removed; permission bits mislead on shares), and it is
  never created, so a missing share surfaces before a shift. The startup configuration's directory is the
  one the close export uses, so the Configuration dialog refuses a mode that names another.
- **`SF4` is a constant** (`CONST_STATION_ID`): it is the installation's identity in the external contract,
  and there is one station. A second station would make it a configuration field.

**The file is named by the LOCAL date, as the contract specifies, while `ts` is UTC.** They disagree near
midnight: an event at 00:30 local in summer has `ts` 22:30Z of the previous date, and a reader that finds
an event by its `ts` date looks in the wrong file. Naming by the UTC date would keep every file's `ts` on
one date and needs no zone knowledge to read. That was recommended, but the format is the external owner's
contract, not this project's, so the local date stands and the question has been raised with the system's
owner. The local date is the log line's own date field, so naming needs no conversion. A run or a cycle
crossing midnight therefore starts in one file and ends in the next, and an unpaired row at a file's start
or end is normal. Only an unpaired `STATION_ON` / `CYCLE_START` with no match in a later file means an
abnormal exit.

**The log stores local time without a zone**, converted with the machine's rules. In the hour that repeats
when summer time ends (02:00–03:00 twice), a log time is read as its first, summer-time pass (`fold=0`).
An event in the second pass gets a `ts` one hour early, so a cycle spanning that hour can read an hour
short or negative. This is recorded rather than engineered around, because the log cannot tell the passes
apart.

The live-log lock is `fcntl` only: Windows is not a target (the installer stops on it, README > Platform).

**Revisit if** the external system's owner agrees to UTC file names, or a second station joins (station
id into the configuration).
Tests `test/Logger/test_station_events.py` (format, order, UTC, midnight, the repeated hour, crashes, the
ledger, failure and retry, the baseline), `test/UI/test_station_event_paths.py` (a failed CONNECT, a startup
failure on the strip),
`test/Configuration/test_core.py` (the required, existing, writable directory),
`test/UI/test_configuration_dialog.py::test_a_mode_naming_another_station_event_directory_is_refused`.

## A lost connection is detected by the camera, not only by DISCONNECT

Decided 2026-10-03. Before this, nothing made the camera's `Connected` false except DISCONNECT. A Basler
grab failure left the camera "connected", so the scan handler's lost-connection branch could not run
outside tests, whose fake cameras disconnected themselves. That was the Camera cell's old fault: a state
updated by the button, not by what happened. The station event file (the entry above) can only close a
cycle the log records ending, so a loss nobody detects would keep counting a dead connection as a
working cycle. *Corrected 2026-10-07:* a connection no longer defines a cycle, so a loss closes none by
itself. The detection still matters for cycles. A Scan on a removed device fails its capture and ends that
scan's cycle as a lost connection, not as a stale frame on a camera still marked connected.

- **The backend reports a removed device.** `Camera_Backend_Cls._Device_Removed` is part of the per-device
  SPI (always False for a saved frame; for Basler, pylon's `InstantCamera.IsCameraDeviceRemoved`, where a
  failing SDK call is not taken as a removal).
- **A grab that fails on a removed device disconnects** in the base `Capture` before the error goes on, so
  the Scan reports a lost connection. The same failure on a device still present stays a transient
  capture error.
- **The window checks once a second while connected** (`CONST_CONNECTION_CHECK_MS`, `Check_Connection`),
  so a loss while nobody scans is closed when it is detected, about pylon's heartbeat timeout plus up to
  one interval after the link went down, not at the next Scan. Both paths go through one
  `__Record_Connection_Lost`, which stops the check and logs the loss.
- **The fakes that disconnected themselves are retired.** The tests now make the device report removed
  and let the backend do the disconnecting, so they exercise the code the real camera goes through.

**Unverified on the hardware.** Whether pylon reports the removal on this GigE camera, and how fast, has
not been tried: `docs/capture-checklist.md` item 4 is the cable-pull check. This entry is one commit so it
can be reverted on its own if that check fails.

**Revisit if** the cable pull shows pylon does not report the removal, or reports it too slowly to count
as detection.
Tests `test/Camera/test_core.py` (the removal check, the grab, `Check_Connection`, the Basler check),
`test/UI/test_station_event_paths.py` (a loss found by the check and at a Scan),
`test/UI/test_system_status.py::test_a_lost_connection_reads_disconnected_in_the_camera_cell_too`,
`test/UI/test_logging_coverage.py::test_mid_session_connection_loss_is_an_error`.

## A cycle is a scan to the end of its analysis, not a camera connection

Decided 2026-10-07. A cycle used to run from CONNECT to its end, and a camera left connected all shift
counted as a shift of work. A cycle now brackets the station's real work. It runs from SCAN (or a
re-analysis) to the end of that scan's analysis. It is defined once, in `Logger.Core.Cycles`, over the
log's event markers. The same definition produces the run-summary CSV's `total_session_time` and the daily
station file's `CYCLE_START` / `CYCLE_DONE`. `cycle_time` (application start to stop) and
`idle_time = cycle_time − total_session_time` keep their meaning.

The cases, read from the window's code paths:

- **The analysis ends the cycle, whether it finished or failed.** A failure still ends the cycle at the
  failure time, because the station was working.
- **A scan never analysed ends at the end of its capture, not at the next event.** Only the latest frame
  is analysed, so each scan before it is captured and discarded. Its cycle is closed at its capture end
  once a later SCAN, or the stop, shows that no analysis came. The log supports this through
  *Frame scan finished*. Counting up to the next event would add the time an operator walks away. DISCONNECT,
  Clear and a lost connection end nothing by themselves.
- **A failed capture ends its cycle at the failure.** This includes a cable pulled during the grab, which
  is how a lost connection ends a cycle. The frame held before it is kept.
- **A re-analysis opens a cycle at its own start.** This covers the same frame analysed again, or a kept
  frame analysed after a failed capture. It is real work with no SCAN, so a `CYCLE_START` means a scan or
  a re-analysis.
- **A loss does not cut a cycle.** An analysis keeps running when the camera goes, and ends its cycle when
  it finishes. A frame scanned before a loss is kept, and analysing it later closes its scan's cycle as
  usual.
- **Closing cuts a running analysis's cycle at the close.** `CYCLE_DONE` comes before `STATION_OFF`. The
  analysis's own end line is never written.
- **No overlap.** SCAN and DISCONNECT are disabled while an analysis runs, so cycles never overlap and
  no second is counted twice.
- **Scanning without a camera** has no path. SCAN is enabled only while connected.
- **A crash leaves the last cycle unpaired, whatever its state.** That includes a scan whose capture end
  is in the log. Nothing after the log's end can show the analysis never came, and an unpaired
  `CYCLE_START` stays the sign of an abnormal exit.

**Markers.** These lines end in a fixed token:

| Marker | Line |
|---|---|
| `#scan-start` | *Frame scan started* |
| `#scan-end` | *Frame scan finished* |
| `#scan-failed` | new *Frame scan failed*, before the capture's ERROR |
| `#analysis-start` | *Analysis N started* |
| `#analysis-end` | *Analysis N finished*, and the new *Analysis N failed* before the analysis's ERROR |

`#connection-start` and `#connection-end` are removed. Nothing reads a connection as an event any more.
The connection sentences and their durations stay in the log.

**One computation, so the two files agree.** The logger keeps each marker it writes, at the line's
whole-second time, recognised by the same `Event_Marker` that `Station_Events` applies to the file.
`Compute_Summary` runs `Cycles` over those markers, and the export runs it over the parsed file. The
CSV's `total_session_time` therefore equals the daily file's summed `CYCLE_DONE − CYCLE_START` to the
second. The cycles come from the whole-second times the log shows, not the exact clock. The one known
disagreement is a cycle in the repeated summer-time hour, which the daily file reads an hour off (see the
entry above).

**The change is marked in the files where it can be.**

- **Run-summary CSV: an explicit format version, kept beside the file.** The CSV has no place for a
  version. A line before the header, or a constant column, would break every reader. So
  `log_<Hardware>.csv.version` holds the number (`CONST_CSV_FORMAT_VERSION`), and a CSV with none is
  version 1:
  - 1: `total_session_time` was connection time.
  - 2: from 2026-10-07, the summed cycles.
- **The existing archive mechanism keys on it.** A CSV whose header or version is not current is renamed
  aside unchanged, to `_until_<date>`, with its version file beside it. The first run after this change
  therefore archives every existing CSV, so connection-time rows and cycle rows never share a file. A fresh
  CSV gets its version file before its header.
  - A CSV copied without its version file is read as version 1 and archived. That is the safe direction:
    rows are never mixed.
- **Daily station files: no mark in the file.** `station_id,event_type,ts` is the external system's
  contract, so the change date is recorded here and in the mode file's comment. Old files are not
  rewritten. Rows before 2026-10-07 bracket connections, and rows after bracket scan-to-analysis. The
  file for 2026-10-07 itself may hold both kinds, if a run before the update and one after share the
  date.

**Revisit if** an analysis can run alongside a SCAN (cycles would overlap and need a union), the UI gains
a second way to start a scan, or the external system's owner wants the definition change marked inside
its files.
Tests `test/Logger/test_station_events.py` (several scans summed, a failed analysis, a scan never analysed
closed by the next SCAN, DISCONNECT, a loss and close, a failed capture, a re-analysis, a loss not
cutting, close during an analysis, connections as no cycle, and
`::test_the_daily_files_cycles_sum_to_the_run_summarys_total_session_time`),
`test/Logger/test_core.py` (the CSV row, whole-second cycles),
`test/Logger/test_csv_archive.py::test_a_current_header_of_another_format_version_is_archived_with_its_version`,
`test/UI/test_station_event_paths.py` (an analysis finished and failed through the window, a scan closed by
the window's close, a loss at a Scan and by the check).

## A worker's thread is joined before the slot that takes its result lets the worker go

Decided 2026-10-07. Each result slot calls `UI.Workers.Join_Worker_Thread` (quit, then wait) before it
drops its references to the worker and the thread. This covers both ends of CONNECT and of an analysis in
`UI/Core.py`, and both ends of a configuration load in `UI/Configuration_Dialog.py`. The module's own
docstring already described this ("quits and waits on the thread once a worker's terminal signal fires").
The slots did not do it.

**Why.** The UI suite hung or crashed in about 4 of 53 runs. One hang was sampled live (`sample`) in
`test_timing_log.py::test_a_configuration_load_logs_each_model_and_the_warm_up`:

- **Worker thread:** inside `QThread::exec`, a deferred delete was destroying the load worker. `~QObject`
  called PyQt's `QThread.disconnectNotify` under a Qt signal-slot lock, and that waited for the GIL.
- **GUI thread:** it held the GIL. It was inside the dialog's load slot, which emits `Configuration_Loaded`
  into the window's `setStyleSheet`, and it waited in `QObject::connect` for that same lock.

The deferred delete is PyQt's: when the last Python reference to a QObject living in another, still
running, thread goes, PyQt calls `deleteLater` and the object is destroyed on that thread. A probe showed
it destroyed on the worker thread. The slot dropped that reference while the thread's `quit` was still
queued behind it.

`QThread.wait` releases the GIL. With the join, the thread finishes its own clean-up while the GUI thread
is parked and holds no Qt lock, and afterwards nothing is destroyed off the GUI thread. The wait is only
the worker returning from `Run`, because the terminal signal is the worker's last act.

**What is not shown.** The other failures, a segfault while building a later test's window and a
`QThread: Destroyed while thread is still running` abort, left no stack that names this cause. After the
fix, 30 of 30 UI runs passed (213 tests each). At the old rate, about 1 run in 13, that is evidence, not
proof, that they shared it.

**Revisit if** a worker is ever reused after its result, or the UI suite crashes or hangs again. The loop
that found this was 30 runs of `test/UI` under a 300 s per-run alarm, with `faulthandler` on and a
native `sample` of any hung run, because pytest's capture keeps `faulthandler_timeout` dumps.
Tests `test/UI/test_threading.py::test_a_workers_thread_has_ended_when_the_window_has_taken_its_result`,
`test/UI/test_configuration_dialog.py::test_the_load_thread_has_ended_when_the_dialog_has_taken_its_result`.
Removing any single join fails exactly its own case.

## Closing waits for a running worker, stops an analysis before its next object, and has an escape

Decided 2026-10-07. `closeEvent` used to `wait(5000)` on a worker's thread and then close regardless. An
analysis takes 2.20 s per object on the Mac and 0.65 s on the station, so nine objects run longer than
that. Reproduced with an eight-second analysis:

- the window froze for 5.0 s;
- it then closed with the thread still running;
- at interpreter exit the window destroyed its `QThread`: `QThread: Destroyed while thread is still
  running`, exit status 134. The log, CSV row and export had already been written, inside `closeEvent`.

That abort is not the one in the old test runs: no test analysis runs past 0.3 s.

Now a close never blocks and never destroys a running thread:

- **While a worker runs, the close is refused and deferred.** An analysis is asked to stop: the worker's
  progress hook, which runs before each object, raises `Analysis_Stopped_Error_Cls` once
  `Request_Stop` is set. `Analyze` lets it through, and the worker emits `Analysis_Stopped`. The object
  being described, or the segmentation before the first object, finishes first, because neither can be
  interrupted. A CONNECT cannot be interrupted at all, so it is waited for. The busy line says which, and
  that a second close quits at once.
- **A stopped analysis** logs *Analysis N stopped at close after k of n objects*, ending its cycle with
  `#analysis-end`, and writes a partial capture set (the raw frame and a note), as a failed one does.
- **Every slot that ends a worker** joins the thread and then finishes the pending close. The close then
  runs the logger's: CSV row, `Application stopped`, export.

**Stopping, not waiting, for an analysis.** The operator asked to close, and the result would never be
shown, so waiting up to about 20 s on the Mac for it looks like a hang. The stop is bounded by one step,
and the raw frame is kept.

**The escape.** A worker that never ends would make the application impossible to close. A Basler
handshake can hang with the network down, and an analysis can stick in one call. So a second close
request, or `CONST_CLOSE_ESCAPE_MS` (30 s) after the first, calls `__Exit_Now`:

- It logs a WARNING naming what it abandons, closes the logger (CSV row and export, all synced), and ends
  the process with `os._exit(0)`.
- Normal exit would destroy the window, and with it the running thread, and abort. `os._exit` runs no
  destructors, so nothing is destroyed.
- What is skipped is the camera SDK's own shutdown: the OS closes the socket, and the camera may hold its
  control channel until its heartbeat expires, so a reconnect right away can be refused once.
- A normal handshake takes seconds and an analysis stops within one object, so the 30 s bound is reached
  only by a hang.

**Revisit if** a worker ever needs a clean shutdown of its own (then the escape must wait for it), or
the camera is found refusing reconnects after an escape (then add a pylon shutdown to the escape, bounded).
Tests `test/UI/test_threading.py`: `::test_closing_during_an_analysis_stops_it_before_its_next_object_then_closes`,
`::test_a_close_arriving_as_the_analysis_finishes_closes_once_with_the_whole_result`,
`::test_closing_while_connecting_waits_for_the_camera_then_closes`,
`::test_a_workers_thread_has_ended_when_the_window_has_taken_its_result[analysis stopped]` (the
stopped slot joins its thread as the others do), and
`::test_closing_never_destroys_a_running_thread_and_exits_cleanly`. That last one runs in its own
interpreter, for the analysis case and the CONNECT escape (second close, and the bound). Without the
deferral, the suite itself aborts with Qt's message.

## The Camera View's heatmap: the background difference, fixed 0–128 scale, cividis, screen only

Decided 2026-10-07. The Camera View has a third view beside Annotated and Mask: **Heatmap**. For each
pixel it shows how much the frame differs from the reference, the background cue before thresholding. It
is the diagnostic for why an object was or was not found: shadows, glare, low-contrast parts, where two
parts merge.

- **The image is the one stage 1 thresholds, not a recomputed one.** `Background_Foreground` is split
  into `Background_Difference` (the per-channel absolute difference, blurred 5×5, as grey, 0–255) and
  `Foreground_Mask` (floored Otsu, opening, dilation). The function returns the threshold it applied and
  Otsu's own. `Analyze` calls the two halves and puts that very array on `Analysis_Str.Heatmap`, so the
  legend's threshold mark applies to exactly the pixels shown. `Background_Foreground` stays as their
  composition for the callers that want only the mask.
- **A fixed scale, not normalised per frame.** It runs linearly from 0 to 128 grey levels, and a value
  above 128 takes the top colour (the legend says "≥ 128"). Per-frame normalisation would paint an empty
  frame's noise as hot as a part.
  - The scale's basis, the 8 frames of `Data/Images/Test/All` (no longer in the repository, recoverable from `1061966`) under the lighting
    of 2026-10-07, not re-measured on the current set: background
    median 6–7, the busiest frames' 90th percentile 56–75, Otsu 30–65 (the floor of 28 never bound),
    objects up to 156–172.
  - At 128, the band that decides found or missed gets the lower half of the lightness range, and
    everything above it is at least twice the highest threshold seen.
  - `CONST_DIFFERENCE_SCALE_MAX`'s comment records the basis, and that it must be re-checked at the
    side-light session.
- **The legend marks the threshold applied, named by what set it:** "Otsu 51", or "floor 28" when the
  floor wins.
- **Cividis, defined in `Parameters/Theme.py`.** It is held to ΔE ≥ 12 (`CONST_ANNOTATE_MIN_DELTA_E`)
  against the OK and NOK verdict colours (box, ink and fill), the status colours and their text twins, and
  the log and on-dark error colours. Viridis fails that: ΔE 4.2 from the OK ink and 12.0 from `CONST_OK`.
  Inferno and plasma pass near the reserved amber and red. Cividis's closest is 12.5, the OK ink.
  - It is defined as 17 anchors from matplotlib's map, expanded to 256 colours in L*a*b*. Lightness rises
    from L* 13.8 to 91.3.
  - Uniformity is held as rising lightness, not even CIE76 steps. Both viridis and cividis are uneven in
    CIE76 (coefficient of variation 0.33), because they are uniform in CAM02-UCS.
- **The difference image alone:** no boxes or outlines.
- **Screen only.** The heatmap is rendered in the window, never handed to the capture writer, not shown in
  History, not in the validation harness.
- **The view toggle:** the Heatmap segment is disabled for a reading with no heatmap, and the chosen view
  is kept for the next one.

**A second source later.** A future mode will show DINOv2 similarity to a reference part. The heatmap's
data and legend are a Qt-free `Heatmap_Str` (values, scale, title, unit, marks), filled by the stage that
computes it. The view only renders a `Heatmap_Str`, so a second source changes no UI code. There is **no
configuration field for the source**: with one source it would have one legal value. When a second
exists, **the source should follow what the mode can actually compute, not the `Classification` flag**.
A catalogue mode may identify parts by geometry alone, with no similarity model, while a classifying
mode might not have a reference part to compare against.

**Revisit if** the side-light session moves the background or object ranges (re-derive the 0–128 scale),
or a second heatmap source is added (then decide the source by the mode's capability, as above).
Tests `test/Parameters/test_theme.py` (lightness rises, distinct from the reserved colours),
`test/Vision/Utilities/test_heatmap.py` (the fixed scale, one value one colour across frames),
`test/Vision/Utilities/test_segmentation.py::test_the_threshold_applied_is_returned_with_which_one_set_it`,
`test/Vision/test_core.py::test_the_heatmap_is_the_difference_the_mask_was_thresholded_from`,
`test/UI/test_camera_view.py` (the painted colours on the fixed scale, the legend's mark and where it
shows, no boxes, the segment and the remembered choice),
`test/UI/test_logging_coverage.py::test_the_heatmap_is_never_written_to_the_capture_set`. Each was proven
by breaking what it names, 14 mutations in all.

## The capabilities document is a map, and a test holds it to the code

Decided 2026-10-08. `docs/capabilities.md` says what the application does: the pipeline stages, the
modes, the views, what each configuration section controls, calibration, the records it writes, and
what has been verified on hardware. It explains nothing twice. A reason links here, an open behaviour
links to `KNOWN_ISSUES.md`, and setup links to the README. The README's list of what each mode-file
section holds moved into it, so there is one copy. The README keeps the file names, the loader's checks
and how a station keeps its own copy.

**Why.** A capability document that is wrong is worse than none, because a reader trusts it instead
of the code. So everything in it that the code names is checked in both directions:
`test/integration/test_capabilities_doc.py` compares its tables with the mode and calibration files'
sections, the mode files, the view switch, the Camera View renders, the Live card and Trends chart
titles, the capture-set suffixes, the run-summary columns and the station event types. Every
configuration key path it writes must exist in a file, and every link and anchor must resolve. Fields
below a section are left to the files' own comments, which a test already holds to the code's
defaults. Proven by 17 mutations, each failing the test it targets: a row or heading removed from the
document, and a section, key, view label, chart title or CSV column changed in the code.

**A review is required and recorded** (added 2026-10-08, the same day). Names going out of step are
caught, but a behaviour changed under an unchanged name is not. So the document carries a *Last reviewed
against the code at commit* line, and every later commit that changes `src/`, `App/`, `Configuration/` or
`Example/` must change the document too: its content, or, when no capability changed, that line, with
*Capabilities: no change* and the reason in the message. A review that is skipped then fails a test; a
careless one does not, and stays the reviewer's responsibility. Tests and docs alone are exempt, since
they describe no capability. A commit message alone was rejected as the record, because nothing can
check it reliably; a file change in the commit can be checked. Proven in a scratch clone: a code-only
commit and a harness-only commit fail, a code commit with a doc change or a moved line passes, a
tests-only commit passes, a line naming a commit not in the history fails, and a copy without git
history skips with its reason.

**Revisit if** the test fails on wording rather than on a capability (then it checks the wrong thing),
a capability that matters has no name in the code for the test to read, or the review line is moved
by habit without the review (then the record says nothing, and a per-section review would be needed).
Tests `test/integration/test_capabilities_doc.py`.

## A catalogue mode is a Catalogue block naming an item folder, and the configuration picks checks, never their order

Decided 2026-10-11, from the owner's catalogue-mode request (in Czech) and the owner's answers to its
*Before building* points. Phase A of five is built: the item, the mode files, the outline
check. The rest is the agreed design, recorded here so the later phases build to it.

- **The item is a folder.** `Data/Catalogue/<item>/<item>.yaml` holds the part's thickness, tolerance and
  checks; its reference images will sit beside it in `reference_image/` (phase B). The file is named after
  its folder and the load refuses one that is not, so a copied folder is never inspected under the old
  name. `Configuration.Core` reads it (`Load_Catalogue`, and through `Load_Configuration`), by the mode
  file's rules: REQUIRED fields, documented defaults, invalid values fail, unknown keys warn.
- **A `Catalogue` block selects the mode.** A mode file with `Catalogue.Item` is a catalogue mode; one
  without is Segment Anything, unchanged. One mode file per item
  (`Config_<Hardware>_Mode_Mounting_Plate.yaml`). The request coupled the mode
  to `General.Classification.Enabled`; that switch already exposes the verdict UI with nothing behind it,
  so the owner chose to let the block select the mode and to remove the switch. Removed with the states in
  phase B (2026-10-11).
- **The configuration picks checks and sets their parameters; it never describes an algorithm.** Each
  block under `Checks` selects one ready-made check module (`Outline`, `Holes`, `Stain`, the last two built
  in phases C and D) with the parameters it reads. No OpenCV call sequence, and **no order**: the checks are
  independent and the verdict will require all of them, so an order field could not change a result
  (structure.md: no field that cannot take effect). A defect check is optional per item: an item may
  define none yet, and one is added later with no code change.
- **One home per value.** The Gemma prompt for an item lives in the item file only (`Describer.Prompt`, phase
  D); the request's override in the mode file would give the same text two homes.
- **The agreed split for the later phases.** FastSAM and the fusion keep finding the objects and their
  outlines (41 of 41 frames counted correctly); DINOv2 base, run locally, will identify which object is
  the item and which side is up, since its 14 px patches cannot give an outline to measure. Deterministic
  checks decide (dimensions, hole counts, a stain by colour); Gemma confirms, and a disagreement is logged, never decisive. The four states are OK, NOK,
  Unspecified (area ≥ 1.7× the item's) and Warning (not the item); Warning takes the amber, Unspecified the
  neutral detection colour.
- **Expected verdicts are labelled for the frames that exist.** `test/integration/test_pipeline.py`
  `CONST_EXPECTED_VERDICTS` gives each object of the 41 frames its state, on the owner's rulings. No frame
  shows a defect the later checks look for (a hole out of place, two parts touching), and the owner chose
  no placeholder tests for frames that do not exist. The two frames that are the item's reference images
  (055, 056) are reported apart: the harness finds them by content.

**Why.** The request asked for configuration-only changes for new parts; a configuration that sequences
OpenCV calls is a program without tests. Recording the split now keeps phase B from building localisation
into DINOv2, where the request first put it.

**Revisit if** a check turns out to depend on another's result (then the dependency is code, still not
an order field), or a part needs a check no module provides (a new module, not a new YAML construct).
Tests `test/Configuration/test_core.py` (the item's loading rules, the block, the shipped files' comments),
`test/integration/test_pipeline.py::test_the_expected_verdicts_label_every_object_of_every_frame` and the
two label tests beside it, `test/Vision/test_analyze_harness.py::test_a_catalogue_run_finds_the_items_reference_frames_by_content`.

## A catalogue mode measures at its part's top face

Decided 2026-10-11. The calibration's factor is exact in the plane of its flat boards,
`Calibration.Solved.Board_Height_Mm` (4.22 mm above the table). A catalogue mode moves it to the item's
top face, `Thickness_Mm` above the table: `Configuration.Core.Scale_At_Height`, per axis
`s' = s − (t − h_board) / f`, the pinhole model with K's focal lengths. The loaded `Configuration_Str.Scale`
is the moved one and says so (`Height_Mm`), so the pipeline, the harness and every size shown use it with
no other change. A catalogue mode whose calibration has no factor or no board height fails its load.
Segment Anything is unchanged: its scale stays the calibration's.

**Why.** Measured before the change on the current test set (the harness's own path, the model-free
describer, every instance of each part): the 22 mounting plates read 60.33–61.40 × 39.64–41.15 mm, a bias
of +0.89 mm on the 60 mm side and a worst case 0.10 mm from the ±1.5 mm limit. The bias is the thickness: a
face 3.78 mm above the boards reads 1.06 % large (predicted +0.64 mm on 60). It did not grow towards the frame
edge on these plates (correlation with distance from the centre 0.25, out to 46 mm). Corrected, the plates
read −0.77 to +0.76 mm off nominal: a margin of 0.73 mm, every one of the 22 within tolerance, and no other
object on the 41 frames the item's size.

- **K's focal lengths, not the undistorted space's.** The factor is in the pixel space
  `getOptimalNewCameraMatrix` (alpha 1) gives, whose focal lengths differ from K's by 0.23 % (x) and
  0.06 % (y). Using K moves the correction by that fraction of itself: 0.0015 mm on 60 mm. Computing the
  new matrix in the loader would take OpenCV and the camera layer's alpha into the configuration layer,
  which sits below both.
- **Every object is measured at the item's face**, not only the item: which object is the item is not
  decided until phase B, and a size shown must be the size checked. Other objects' sizes are off by the
  difference between their height and the item's, about 0.28 % per millimetre.
- **The parts are not calipered.** The owner's ruling: treat them as nominal, so a part within tolerance
  reads within. "Within tolerance" here means consistent with nominal, not a verified size; README >
  Limitations says what that leaves open.

**Revisit if** a part's measured sizes drift with its position (the side wall: see README > Limitations),
the parts are calipered (then compare against the true sizes, not the nominal), or the calibration is
re-solved at another board height (the correction follows it, but re-check the margins).
Tests `test/Configuration/test_core.py::test_the_scale_at_a_height_follows_the_pinhole_model`,
`::test_a_catalogue_mode_measures_at_the_parts_top_face`, `::test_a_catalogue_mode_needs_a_scale_it_can_move_to_the_top_face`,
`::test_a_mode_without_a_catalogue_block_is_not_a_catalogue_mode`,
`test/Vision/Utilities/test_dimensions.py`,
`test/Vision/test_core.py::test_a_catalogue_mode_checks_each_measured_object_and_segment_anything_does_not`,
`test/integration/test_pipeline.py::test_the_outline_passes_exactly_the_catalogue_parts` (slow, 82 cases).


## A catalogue mode identifies by similarity, and an object of the part's shape that does not look like it is NOK

Decided 2026-10-11 (catalogue phase B), on the owner's rulings. Every object FastSAM and the fusion find is
compared with the catalogue item's two reference images by DINOv2 base and judged by
`Vision.Utilities.Classify.Classify`, in this order:

1. **Unspecified** — its area is at least `Catalogue.Unspecified_Area_Ratio` (1.7) times the part's nominal
   area: probably several parts together. Not judged; it says to separate them.
2. **The part, by its look** — similarity at least `Catalogue.Identify_Similarity` (0.75), whatever its size:
   **OK** when its outline is within tolerance, **NOK** when not. A wrong-sized part is therefore NOK, not a
   Warning.
3. **The part, by its shape** — below 0.75, but its outline within the part's tolerance: **NOK**, "it has
   the part's outline but does not look like the part".
4. **Warning** — anything else: not the part, found and described, not supposed to be there.

**Why 0.75.** Measured on the 41 frames (fallback describer, the class token's cosine, the best of four
quarter turns and both sides): every mounting plate 0.79–1.00, the fingerprint-stained fronts lowest; every
other object at most 0.673 (the red block against the plate's back), the 50 × 50 square plates 0.23–0.43
(re-checked 2026-10-13). 0.75 sits in that gap. The side is the reference that scored highest: right on all 22
plates, the smallest margin at least 0.08.

**Why step 3 has no lower bound.** Objects that are not the part reach 0.673 against it, close under the
plates' 0.79. The owner chose no floor: an object of the part's size that does not look like it
reads NOK rather than Warning, **the safer error in quality control** (a foreign plate the size of the part
is flagged as a failed part, never passed or ignored), and the thin threshold is gone.

- **Compared whole and upright.** Each object's measured rectangle is warped upright (long side vertical, as
  the references show the parts) and compared in four quarter turns; a round object by its box. The image is
  resized whole to 224 × 224, not centre-cropped as the model card's processor does — a centre crop of a 2:3
  plate cuts its holes off. The normalisation is the processor's own.
- **The size checks' verified zone.** Every judged mounting plate on the test set lies within 46.32 mm of the
  frame centre (Image_072, measured the way the check measures). Beyond `CONST_VERIFIED_RADIUS_MM` (46.4) an OK
  or NOK judged on its size carries the note "the size check is not verified here", with its distance. The
  verdict stands: a NOK stays NOK, the note explains it (the owner's ruling). *Corrected 2026-10-13:* it was
  74.3 mm, measured on more parts than the mounting plates (*The catalogue holds only the mounting plate*).
  Plates captured farther out, in the corners of the view, would widen it (capture checklist).
- **Where the verdict shows.** The frame and the mask (Warning in the status amber — the one place amber marks
  an object, `Parameters/Theme.py` — Unspecified in the neutral colour, with the mask's darker neutral
  outline), the Scene Understanding panel and file (`Reporting.Verdict_Lines`: the state, its evidence, each
  reason it is not OK with measured and expected values), and the log (one line per object, Warning and
  Unspecified at WARNING). Trends counts only OK as OK: a Warning did not pass. The status badge and History's
  filter still speak OK/NOK only (KNOWN_ISSUES).
  *Corrected 2026-10-11 (phase B.1), the owner's wording:* Scene Understanding shows `State: <state>.` and a
  `Reason:` line per reason (a Warning: "The object should not be on the surface."; an Unspecified object: why
  it could not be judged and what to do; a NOK: each failed dimension with measured and expected values, or
  "It has the part's outline but does not look like the part."), then the size note; no similarity there —
  it stays in the log, with the side. An OK or NOK part's description says which side is up. The badge states
  the worst verdict (NOK in the NOK ink on its tint, the 'fail' level; Unspecified, then Warning, in amber;
  all OK in green), and Trends charts OK, NOK, Warning and Unspecified. Only History's filter is left
  (KNOWN_ISSUES). *Corrected 2026-10-11 (phase E):* a NOK has one `Reason:` sentence and its values are in the
  log (*A NOK reads as one sentence…*); History filters by the four states (*History filters by the four
  states…*).
- **What it does not judge yet.** The stain and the holes. The five stained-plate frames read OK until the
  stain check (phase D); their expected NOK is a strict xfail naming it. *Corrected 2026-10-11:* the holes are
  judged since phase C, the stain since phase D (*A judged part's stains are a colour band…*); the stained
  plates read NOK and their marks are lifted.
- **Confidence stays a mask score.** The similarity is shown as "similarity", never as Confidence
  ([*`Verdict`'s confidence branch stays dormant…*](#verdicts-confidence-branch-stays-dormant-a-mask-score-is-not-a-confidence)).

**Revisit if** a new item or a new lighting puts an item below 0.75 or another object above it (re-measure
with the harness, which reports the states per frame), a part is placed farther than 46.4 mm from the centre
on purpose (measure there, then move the radius), or a real foreign part of the item's size turns up and
should be a Warning (then a floor needs data, not a guess).
Tests `test/Vision/Utilities/test_classify.py` (each branch, no floor, the crop upright, the best match),
`test/Reporting/test_core.py` (the lines, the note, the log levels),
`test/integration/test_pipeline.py::test_each_frame_gets_its_expected_verdicts` (slow, 41 cases), `test/Vision/test_core.py` (the identifier loaded, kept and released; the rule applied to every
object), `test/Parameters/test_theme.py::test_every_catalogue_state_has_its_colour`,
`test/UI/test_timing_log.py::test_a_catalogue_analysis_logs_each_verdict_and_its_identification_time`,
`test/UI/test_reading_view.py::test_a_judged_object_shows_its_verdict_between_label_and_description`.

## DINOv2 base is the catalogue identifier, pinned and verified by the installer

Decided 2026-10-11. `facebook/dinov2-base` at revision `f9e44c8` (Apache 2.0, unchanged on the Hub since
2024-01-17), in `models/dinov2-base`: the weights as safetensors (346 MB, not the duplicate
`pytorch_model.bin`), its configuration, image processor and model card. `install.sh` downloads and verifies
it like Gemma — the same step, `Ensure_Hub_Model`: the LFS SHA-256 of the weights and the git blob SHA-1 of
each small file, a mismatched file fetched again with `--force-download` — and checks that every catalogue
mode's `Catalogue.Identifier` points at it. It loads with `local_files_only`, so nothing touches the network at
run time, on `Segmentation.Device` (one device setting for the two torch models), and is released when a
configuration without a catalogue is loaded.

**Why base.** The owner's choice; the measurements above were made with it, so the thresholds are its.

**Revisit if** the identifier is swapped (re-measure the 0.75 and the side margins on the same frames and
crops) or the Hub revision stops serving a pinned file (the installer says so and stops).
Tests `test/Install/test_install.py` (the DINOv2 download at its revision, the skip when verified, a failed
verification, the plan line, the configuration check), `test/Vision/test_identifier.py` (no heavy import, the
missing-weights sentence; slow: unit rows, repeatable, the two sides apart).


## The station file holds the camera and the reference, and a mode file never overrides it

*Corrected 2026-10-13: the station is no longer found by the mode file's `Hardware`: the mode file names it
(`Station`), and it lives in `Configuration/Station/`. It now also names the calibration in force, which a mode
file cannot override either. A local copy of a mode file no longer keeps the station beside it
([*The configuration is a chain of references…*](#the-configuration-is-a-chain-of-references-mode--station--calibration-each-kind-in-its-own-folder)).
The no-overrides rule stands.*

Decided 2026-10-11 (catalogue phase B.1), on the owner's rulings. What belongs to the camera, the light and
the table moved out of the mode files into one station file per hardware,
`Configuration/Station_<Hardware>.yaml`: the camera, lens and lighting as a person names them, the
acquisition settings (`Camera.Custom_Cfg`), the sensor window, and the empty-surface reference
(`Background.Reference`, until now `Segmentation.Background.Reference` in each mode). `Load_Configuration`
finds it by the mode file's `Hardware`, as it finds `Calibration_<Hardware>.yaml` — no second name to keep in
step — and checks that the station file names the same hardware. It is REQUIRED.

- **No overrides.** A mode file that holds `Camera` or a background reference fails to load and names the
  station file, even when the value equals the station's. The window, the calibration and the reference's
  provenance are all checked against the camera settings; with one source they cannot disagree, and two
  modes on one camera cannot shoot at different exposures against one reference without anyone noticing.
  The alternative — overrides merged over the station — would have made every one of those checks read
  the merged value, and a per-mode exposure would have made the shared reference wrong for that mode.
- **The reference is the station's** because it was shot from this camera, under this light, on this
  table, and every mode differences against it. The mode keeps the difference's parameters (Otsu floor,
  opening, dilation): those are processing, not the scene.
- **Machine-specific values stay out of the repository.** The station file is committed, so it holds
  nothing true of one machine only; the station-event directory stays in the local copy of the mode file
  (README > Configuration), which now keeps the station file beside it as it keeps the calibration.

**Revisit if** a second camera arrives (its own `Station_<Hardware>.yaml`, nothing else changes), a mode
genuinely needs other acquisition settings (that is another station, or a measured case for overrides,
not a quiet exception), or a second table or light shares the camera (then the reference may need to be
per table, and the station split).
Tests `test/Configuration/test_core.py` (`test_a_mode_file_never_overrides_the_station`, the missing and
mismatched station file, its unknown keys, every mode reading the one station, its documented defaults),
`test/integration/test_capabilities_doc.py::test_the_station_table_names_every_section_of_the_station_file`.


## A catalogue item is the single tracked source for its part, and its descriptions wait for the describer

Decided 2026-10-11 (catalogue phase B.1), on the owner's rulings. Each item file holds what the request
said about the part, in a schema phases C and D extend rather than reshape:

- `Name` (REQUIRED) — the item as a person names it; the configuration-loaded line names it.
- `Description`, `Measurement_Rules` (optional, default empty) — the part as a whole, and how a dimension
  is read on it beyond its nominal value (the plate's symmetry).
- `Sides` (REQUIRED: exactly `front` and `back`, the reference images' names) — each a `Name` (REQUIRED)
  and a `Description`. The `Name` is read now: a judged part's description gains "It lies with its <Name>
  up.", from DINOv2's side, never the describer's.
- `Defects` (optional, default none: a part whose defective examples may not exist yet) — each a `Name`,
  the `Side` it is looked for on, what it `Looks_Like` and what is `Not_A_Defect`.
- `Checks` — what the code measures (`Outline`, `Holes`, `Stain`), kept apart from what a person or
  the describer looks for.

**A dated exception to "a field must be read".** `Description`, `Measurement_Rules`, each side's
`Description` and `Defects` are loaded and validated now (a wrong side, a missing name, an unknown key in a
side or a defect fails the item) and read by nothing until the describer uses them in phase D. The owner
chose this over keeping them as comments: validated fields cannot drift unnoticed, comments would have had
to become fields anyway, and the item file is then the one place the part is described. The exception ends
when phase D reads them; until then the item files' headers say so.

*Corrected 2026-10-11 (phase D):* each side's `Description` and the `Defects` are read: they fill the
describer's prompt (*The describer is told what the checks found, never a number…*), and they may hold no
number. `Description` and `Measurement_Rules` are still read by nothing: they hold the dimensions, which the
owner ruled the describer may not get. The exception continues for those two, for people reading the file,
until the owner decides whether they stay.

**Revisit if** phase D does not read a field (remove it, the rule applies again), or a part has a side
without a reference image (then `Sides` follows the references, not a fixed pair).
Tests `test/Configuration/test_core.py` (`test_the_item_carries_its_description_sides_and_defects`,
`test_an_invalid_description_fails_the_item`, `test_an_item_with_no_defects_described_loads`, the documented
defaults), `test/Reporting/test_core.py::test_a_judged_part_says_which_side_is_up_in_the_catalogues_words`,
`test/Vision/Utilities/test_classify.py::test_the_side_is_named_in_the_catalogues_words`,
`test/Vision/test_core.py::test_a_catalogue_mode_judges_every_object_by_the_rule`.


## A judged part's holes are counted where the catalogue puts them, by FastSAM on its upright crop

Decided 2026-10-11 (catalogue phase C), on the owner's rulings. Each part judged OK or NOK has its holes checked
on the side DINOv2 found up (`Vision.Utilities.Holes`): FastSAM runs again, through the loaded segmenter, on the
part's upright crop; a round mask inside the crop is a hole candidate; each catalogue group (`Checks.Holes.<side>`)
counts the candidates of its diameter and, when it has positions, near one; each counted hole's diameter, edge
distances and pitch are checked against the tolerance. A hole missing, extra or out of tolerance makes the part
NOK, one `Reason:` per finding. (*Corrected 2026-10-11, phase E:* one sentence for all findings, the values in
the log.)

**Why FastSAM on the crop.** Measured on the 22 mounting plates of the 41 frames (re-checked 2026-10-13): every
hole (12 fronts, 2 countersinks and 2 through-holes each; 10 backs, 2 through-holes each, 68 in all), and no
other round mask of a group's size. About 134 ms per judged part on Apple silicon (Metal), 739 ms on the CPU. A
classical detector was not needed at these scores.

- **Counting.** A hole counts in a group when its diameter is within twice the tolerance of the group's — wider
  than the check, so a hole of the wrong size is reported as the wrong size, not as missing; the load refuses two
  groups of one side that would capture the same diameter. A positioned group counts a hole within √2 × tolerance
  + 0.5 mm of an expected position (2.62 mm for the through-holes), mirrored to all four corners since the part lies
  either way round; every through-hole lies within 1.23 mm of its position. A hole anywhere else is not counted
  and not reported (KNOWN_ISSUES).
- **Roundness 0.83.** Every real hole's mask is 0.881-0.914 round, and no mask of a hole's size lies between
  0.70 and 0.83; a square is π/4 = 0.785.
- **The diameters read large, and it is the hole, not the mask.** Countersinks 12.07-12.33, through-holes
  6.14-6.25 on the front and 6.46-6.73 on the back. The mask follows the visible edge
  (within 0.1-0.4 mm of the strongest radial change); through a mounting-plate hole the table shows 5.67-5.99 mm
  from the front and 6.05-6.26 from the back, so the back's opening is wider than its bore — by the look a chamfer
  or deburring. Not measured with a pin gauge. The catalogue's tolerances are unchanged (the owner's ruling):
  every hole is within them, the narrowest margin 0.77 mm (a back through-hole's diameter).
- **Not checked:** the countersink's centering on its through-hole (0.12-1.05 mm apart in the image, the bore seen
  at an angle; the catalogue gives no tolerance).

**Revisit if** a part with a hole in the wrong place turns up (then report candidates outside every position), a
plate's holes are measured with a pin gauge (then the bias has its number), the lighting changes (re-measure the
roundness), or the crop pass's 134 ms per part matters (then one FastSAM pass could serve
both).
Tests `test/Vision/Utilities/test_holes.py`, `test/Configuration/test_core.py` (the groups, their validation),
`test/Reporting/test_core.py::test_a_nok_names_its_missing_extra_and_wrong_holes`,
`test/Vision/test_core.py` (the crop segmented once per judged part, a part without its holes NOK),
`test/integration/test_pipeline.py::test_every_mounting_plate_shows_all_its_holes_within_tolerance` (slow).


## Exposure, gain and white balance are fixed: the automatic modes are switched off and read back

Decided 2026-10-11, on the owner's instruction. On connect `Camera.Basler` switches off `ExposureAuto`,
`GainAuto` and `BalanceWhiteAuto`, sets the station file's exposure (10 000 µs), gain (10) and white-balance
ratios (red 0.95, green 0.90, blue 1.20), then reads the three modes back; a camera that keeps one on is
refused, naming it, and every connect logs them. Until now exposure and white balance were switched off but not
read back, and gain auto was never set — the camera's power-up default (Off on this model) was trusted.

**Why.** The background difference, the colour names and the stain check (a hue and saturation band, measured
under these settings) all assume the camera does not adjust itself between frames.

**Not controlled:** gamma and the colour preset (`LightSourcePreset`) are not set; they come from the camera's
power-up user set. They are not automatic, but a changed user set would change the colours without a word.
*Corrected 2026-10-11, on the owner's instruction:* both are read and logged on every connect, and the station
file may pin them (`Camera.Custom_Cfg.Gamma`, `Light_Source_Preset`): a camera that reads otherwise, or lacks the
node, is refused, naming both values. They are read, never written, so the pin checks the user set rather than
overriding it. *Pinned 2026-10-13, from the rig's connect log:* Gamma 1. `Light_Source_Preset` stays unpinned:
the a2A1920-51gcPRO has no `LightSourcePreset` node, so it reads "not available", which is logged and is not an
error while unpinned (a pin could never match it). The rig confirmed the three automatic modes Off the same day.
*Added 2026-10-13, on the owner's instruction:* the white-balance ratios are read back too, one colour at a time,
and logged with the tolerance used; a ratio more than half the `BalanceRatio` node's step from the station file's
is refused, naming the colour. The camera rounds each ratio to that step, so an exact match would refuse a
correctly set camera; a node reporting no step is checked to 1/128 (half of an assumed 1/64 step).
*Confirmed on the rig 2026-10-13:* this camera reports no step for `BalanceRatio`, so the 1/128 fallback applies,
and it reads the ratios back as 0.949951, 0.899902 and 1.19995 (within about 0.00005 of 0.95, 0.90, 1.20).

**Revisit if** the camera's user set is changed, the camera is replaced by a model with a colour-preset node (then
pin it), the rig's connect line shows a ratio step coarser than expected, or a stain or colour measurement drifts
with no change in the station file (then set gamma and the preset too).
Tests `test/Camera/test_basler.py::test_a_camera_that_keeps_an_automatic_mode_is_refused`,
`::test_a_factory_default_camera_is_set_to_the_configured_window`, `::test_the_camera_layer_logs_the_window_it_read_back`,
`::test_gamma_and_the_colour_preset_are_read_and_logged_never_set`, `::test_a_camera_that_does_not_match_a_pin_is_refused`,
`::test_a_node_the_camera_lacks_is_logged_and_refuses_a_pin`,
`::test_the_white_balance_ratios_are_read_back_within_half_the_camera_step`,
`::test_a_ratio_node_without_a_step_uses_the_fallback_tolerance`,
`::test_a_camera_that_does_not_keep_the_white_balance_is_refused`,
`test/Configuration/test_core.py::test_gamma_and_the_colour_preset_may_be_pinned_and_are_checked`.

## A judged part's stains are a colour band on its upright crop, from 1 mm²

Decided 2026-10-11 (catalogue phase D), the threshold the owner's. `Checks.Stain.<side>` lists a colour band
(OpenCV HSV: hue 5–30, saturation from 50, value from 40), the least area (1 mm²) and an edge band left out
(1 mm). `Vision.Utilities.Stain` takes the judged part's upright crop, leaves out the edge band and every hole
the hole check found (its diameter with 0.5 mm more), opens the band's pixels (3 × 3: lines and specks go), and
each connected area of 1 mm² or more is a stain; one makes the part NOK, the reason giving the count, the
largest and the total ("7 stains on the machined front, the largest 152.22 mm², 201.55 mm² in all.").

**Measured on the 12 mounting-plate fronts of the test set** (the crops the check gets): the five
fingerprinted plates' largest stain 144–157 mm²; every clean front has no band pixel left after the opening,
at any size. No false acceptance, no false rejection; the threshold sits over 100 times under the smallest
stain found. The papillary lines are not used (about 5 px apart at this scale): colour alone separates them
here.

*Corrected 2026-10-11 (phase E), on the owner's instruction:* a fingerprint's ridges broke it into fragments, so
Image_059's two fingerprints read as seven stains. Fragments within `Merge_Mm` (3 mm) are now one stain region,
counted, boxed and reported as one; a region is a stain only when it holds a fragment of 1 mm² or more, so what
makes a part NOK is unchanged. Measured on the five fingerprinted fronts (two fingerprints each by eye): 2–4 mm
gives exactly two regions on every one, 1 mm three or four, 5 mm joins the two across the hole on 074 and 076;
3 mm is the middle. The regions' largest 149–158 mm². The reason now reads "There are two stains on the
machined front." (*A NOK reads as one sentence…*).

**Why colour, not the describer.** A describer is not a detector (README > Limitations), and the stain is a
texture with no boundary FastSAM would give.

**Revisit if** the light, the camera's settings or the table change (the band is this light's: KNOWN_ISSUES),
a stain of another colour must be caught, or a clean part shows band pixels.
Tests `test/Vision/Utilities/test_stain.py` (synthetic: the least area, the edge band and the holes left out,
hairlines, colours outside the band, the order, the rule), `test/integration/test_pipeline.py::test_each_frame_gets_its_expected_verdicts`
(the five stained plates NOK, the clean ones OK), `::test_each_stained_front_shows_its_two_fingerprints_as_two_stains`,
`test/Configuration/test_core.py::test_an_invalid_stain_check_fails_the_item`.

## The describer is told what the checks found, never a number, and its contradictions are dropped and logged

Decided 2026-10-11 (catalogue phase D), on the owner's rulings: the describer may only confirm and describe,
never decide or contradict the verdict, and gets the appearance and the defects as context but no dimension
or number. In a catalogue mode the objects are now judged before they are described (the judgement's time is
still left out of the latency). A judged part (OK, NOK) is described with the item's `Describer.Prompt`, filled
by `Reporting.Describer_Prompt` with the side up (DINOv2's), that side's description and defects, and what the
checks found in words (`Reporting.Findings`: "found yellow-brown stains on its machined front; describe them
and where they are", "found fewer through-holes than the part has"). A Warning or an Unspecified object gets the
mode's own prompt. The loader refuses a digit or a number word (two to twelve, pair, half…) in a side's
description, a defect or the prompt. `Reporting.Guard_Description` then drops, sentence by sentence, one with
a digit and one contradicting a check that ran (a stain claimed on a clean side or denied on a stained one; a
count of holes, or holes "in each corner", when the hole count failed); each drop is an audit warning in the log with the describer's
full text. The verdict, State and Reasons come from the checks only.

**Measured with Gemma 4 E4B on 24 judged parts of 15 frames** (2026-10-11: 7 mounting-plate fronts, 4 of them
stained, and 17 parts of an item since removed, 5 of them NOK for missing holes — *The catalogue holds only the
mounting plate*):
- **First run**, the catalogue's sides still counting ("Four small blind holes…"): on all five parts missing
  holes Gemma wrote "four small blind holes in each corner"; the first guard let it through, and dropped one
  correct sentence ("clean of any staining").
- **After** the number words were taken out of what it is given and the guard extended: it still wrote
  "small blind holes in each corner" on the five — the guard dropped all five; no other drop; no contradiction
  left in the text shown; no digit. The stains were described and placed ("concentrated on the left side").
  1.9–3.7 s per judged part on the M-series GPU.
- **Before phase D** (the side description and defects without the findings, then with them, on the 12
  fronts): 0 contradictions, but 11–12 of 12 recited the catalogue's sizes as seen, among them the 8 mm
  thickness, invisible from above — why no number reaches it.

**The guard is words, not understanding.** It catches the sentences measured and their kind; a paraphrase it
has not seen can pass, and a correct sentence using a pattern's words can be dropped (logged either way:
KNOWN_ISSUES).

**Revisit if** the describer model or the prompt changes (measure again: contradictions shown, drops, false
drops), a check is added (its claims join `CONST_GUARD_CLAIMS`), or the drops show a sentence the operator
needed.
Tests `test/Reporting/test_core.py` (`::test_the_guard_drops_numbers_and_what_contradicts_a_check`, with
Gemma's own sentences; `::test_the_findings_say_what_the_checks_found_in_words_without_numbers`;
`::test_the_describer_prompt_is_the_items_filled_for_the_part`),
`test/Vision/test_core.py::test_a_judged_part_is_described_with_its_findings_and_guarded`,
`test/Vision/test_describers.py::test_gemma_sends_a_given_prompt_instead_of_the_purposes`,
`test/Configuration/test_core.py::test_what_the_describer_is_given_holds_no_number`.

## A NOK reads as one sentence, and its values go to the log part by part

Decided 2026-10-11 (catalogue phase E), on the owner's instruction. Scene Understanding gives a NOK exactly one
`Reason:` line (`Reporting.Reason_Sentence`): each kind of finding a clause, in a fixed order — the outline's size,
its look, the holes per group, the stains — joined into one sentence, counts in words up to ten and digits above
("One of two through-holes is missing and one is out of tolerance."; "There are two stains on the machined
front."). The measured and expected values move to the log (`Reporting.Part_Lines`), below the object's verdict
line: the outline's checks, each hole group's count, and one line per part, numbered as the frame numbers its
failing parts ("Part 2.4 · through-hole: not found at its expected position."). The request's explainability —
measured value, expected value and tolerance for each NOK part — is met in the log.

**Why one sentence.** The panel lists every object of a frame; a NOK with a line per finding (eight hole checks on
one part were seen in phase D) pushed the others out of sight. The sentence says what is wrong; the log says by how
much.

**Revisit if** a check is added (its clause joins the order), or an operator needs a value on screen.
Tests `test/Reporting/test_core.py` (`::test_a_nok_has_one_reason_sentence_for_its_outline_and_look`,
`::test_a_nok_names_its_holes_in_one_sentence`, `::test_a_nok_names_its_stains_in_one_sentence`,
`::test_the_log_lists_each_part_with_its_measured_and_expected_values`),
`test/UI/test_timing_log.py::test_a_catalogue_analysis_logs_each_verdict_and_its_identification_time`.

## A judged part's features are marked on the frame, pass or fail, numbered as the log's parts, and saved as its parts

Decided 2026-10-11 (catalogue phase E), as the request asks and the owner approved. Each judged part's features
(`Parameters.Vision.Feature_Str`) are built where its checks run — each hole found and each hole expected and not
found (`Vision.Utilities.Holes.Hole_Features`) and each stain region (`Check_Stain`) — on the upright crop, then taken to the frame through the inverse of the crop's warp (`Classify.Crop_To_Frame`) and
numbered as the object's parts. `Annotate.Draw_Annotated` draws them on the annotated frame (Live, the saved
`_annotated.png`, the harness), each in ONE colour — the pass colour (the OK verdict's indigo) or the fail colour
(the NOK verdict's magenta), the colours that already mark the objects, so a feature's colour means what an
object's does — at one line weight, 2 px on a 1920 px frame, half the object's box:

Every feature has a box along the part's axes — its edges are the upright crop's, taken to the frame — so it turns
with the part:

- **A hole found:** its box solid, tight round its outline, and its outline solid: the FastSAM mask's contour,
  simplified under a pixel, so it follows the hole's real shape.
- **A hole expected and not found:** in magenta at its expected position, its box (tight round the catalogue's
  circle) and a circle of the catalogue's diameter, both DASHED — the only dashed feature marks — so a missing hole
  never reads as a found hole out of tolerance (solid).
- **A stain:** its box along the part's axes, round all its pixels (`Check_Stain`), solid, and its pixels under a
  35 % tint of the fail colour, so its shape shows.
- **Its number:** every feature carries its part number (`3.1`, `3.2` for object 3) on a chip like the object's,
  at 0.6 of its font — the number the log's `Part` lines print, from the same `Feature_Str.Part`. The chip belongs
  to the feature's box as the object's chip to the object's: on the corner of the box nearest the object's chip
  (the top-left of the object's axis-aligned box), so all of an object's chips sit toward its own chip at any
  rotation; outside the box, along that corner's edge closer to horizontal, turned with it, its numeral reading
  left to right, so it is never more than 45° off level. Two rules keep it from jumping between frames: corners
  within 3 px (at the 1000 px reference, about 6 px on the frame) of the nearest are equally near and the higher one
  is taken; edges within 5° of each other are equally level and the one running right from the corner is taken
  (both running right: the one rising). A chip may lie over a neighbouring outline (a through-hole's over its
  countersink's ring), never over another chip: one that would come within 2 px of an earlier chip of its object
  slides along its edge, away from the corner, until it does not. Numbering stays group by group (countersinks 1.1,
  1.2, then through-holes 1.3, 1.4), as the log lists them.

*Corrected 2026-10-13, the owner's rulings (second revision):* the first version (`32418bc`) drew a found hole's
box dashed and axis-aligned on the frame, a stain's box along the stain's own slant, and moved a chip up and left to
free space off its box. Every found feature's box is now solid and along the part, and a chip stays on its box. Two
corner rules were tried first and dropped: the top-left of the part's upright crop (which corner that is flips with
the crop's 180° ambiguity: across nine turns of two real plates it landed on one corner or the opposite one), and
that corner fixed by the identifier's turn (right on all 18 synthetic turns, but 180° off on 2 of the test set's 22
plates, Image_076 and Image_079). The corner nearest the object's chip needs no orientation at all. A chip sliding
along its edge is for the tolerance limits: at nominal sizes the through-hole's chip sits 29.7 px below the
countersink's (22 px of chip and the gap), at a 10.5 mm countersink round a 7.5 mm through-hole 14.9 px, and on the
test set's front (Image_055) it slides 6 px to keep the gap.

*Corrected 2026-10-13, the owner's ruling, reversing the one of 2026-10-11:* the frame now numbers the parts. On
2026-10-11 failing parts were numbered on the frame, then every part, and the outline's measured sides were tagged
L and W; the owner ruled that both cluttered the frame, and they were removed. The numbers are back as smaller chips
on their features' boxes, never over each other; the L and W tags stay removed. *Corrected 2026-10-13, same ruling:*
until then a hole was marked by a solid square of its diameter plus 0.5 mm, a missing hole by a dashed square, and
every mark stood on a 2 px light halo (the theme's card colour); the square is now only the box recorded in
`_objects.json` (`CONST_HOLE_MARK_MARGIN_MM`), and the halo is gone.

*Reconsidered 2026-10-14 with the JIC Smart Factory palette, and kept:* the marks are now the purple (pass) and the
orange-red (fail). The poster lays a thin dark outline under each defect box, so an outline under every mark was
measured on the test frames: the orange-red is 1.2:1 against bright aluminium and rust-stained metal (median), and a
2 px outline lifts every mark there to 3.5:1 in `#640ABA` (6.4:1 in the darker `#2D0557`, which the owner then
dropped from the palette). The owner compared renders of Image_074 and Image_076 with and without the outline and
chose none, by eye, despite the 1.2:1: the ruling below stands (*The palette is the JIC Smart Factory brand's*).

**No halo: the marks stand out by hue, not brightness — the owner's decision (2026-10-13).** Measured on the plate
surface 3–8 px outside each hole (Image_055 front, Image_056 dark back, Image_080 stained front), the indigo's CIE76
ΔE against the ground is 49.5, 53.7 and 48.8 (10th percentile 44.1, 49.2, 44.4) and the magenta's 84.8, 91.0 and
84.1, four times the renderer's 12 floor (`CONST_ANNOTATE_MIN_DELTA_E`) on the dark back as on the light front; the
luminance contrast is only about 2:1 on every ground (indigo 2.1, 2.2, 1.9), below the 3:1 usually asked of a
graphic. The owner accepted that, and that it is weaker for a colour-blind viewer, over a halo, which is a second
colour beside every mark. In the Camera View at the default window (1720 x 1020, the frame shown at 0.45 scale) the
2 px lines draw about 1 px wide and stay unbroken on the dark back, a dashed outline still reads dashed, and a
feature chip's numeral is about 6 px tall; 1 px lines were rejected as likely to fade there.

The label mask has none of it: it shows the segmentation. The parts are saved in `_objects.json` as each object's
`parts`, an additive field (owner's ruling): an older set loads with none, the CSVs are unchanged. A hole's outline
is drawn, not saved: History shows the saved `_annotated.png`.

- **Where a missing hole goes.** At its catalogue position: every mirrored position for a group that fills them
  all; for the plate's through-holes, mirrored either way, the pair that holds the holes found and best fits the pitch (none placed with
  none found); a countersink around a through-hole without one (KNOWN_ISSUES).
- **Rendered and looked at** (2026-10-13, second revision): Image_055 (front), Image_056 (dark back), Image_080
  (the two fingerprints as two tinted boxes along the plate, chips 1.5 and 1.6); SYNTHETIC frames: Image_055 with
  one through-hole painted out (inpainted; `Part 1.4 · through-hole: not found at its expected position`, a dashed
  magenta box and circle inside the found countersink 1.1), the Image_055 and Image_056 plates turned 135°, 215° and
  260° and pasted on the background reference (all judged OK, every chip level within 45°), and Image_055's
  concentric pair redrawn at the tolerance limits (chip 1.3 slides 20 px along its own top edge). In the Camera View
  widget, rendered offscreen at the default window (0.45 scale), the lines draw about 1 px and stay unbroken, a
  level chip's numeral is about 6 px tall, and a chip turned near 45° reads but softer. No mounting plate of the test
  set misses a hole, so only the synthetic frame shows one.

**Revisit if** a mark or a number is misread on the rig's screen (a chip turned near 45° first), an operator cannot
tell indigo from the dark back (the halo's case), a chip slides off its box on a crowded part, or a feature kind is
added.
Tests `test/Vision/Utilities/test_annotate.py::test_a_found_holes_box_and_outline_are_solid_in_one_colour_thinner_than_the_object_without_a_halo`,
`::test_a_missing_hole_is_a_dashed_box_and_circle_where_a_found_one_is_solid`,
`::test_a_stains_box_along_the_part_is_solid_and_its_pixels_tinted`,
`::test_a_chip_sits_outside_its_box_on_the_corner_nearest_the_objects_chip_and_reads_near_level` (0°, 30°, 135°, 200°),
`::test_a_near_tie_takes_the_higher_corner_and_the_edge_running_right`,
`::test_a_concentric_pair_at_the_tolerance_limits_has_its_chips_apart_each_on_its_own_box`,
`test/Vision/Utilities/test_stain.py::test_a_stains_box_is_along_the_crops_axes_round_all_its_pixels`,
`test/Vision/Utilities/test_holes.py` (the missing-hole placements;
`::test_a_holes_outline_is_its_masks_contour_in_mm_and_the_frame_marks_it`,
`::test_a_missing_holes_outline_is_a_circle_of_its_groups_diameter_at_its_position`),
`test/Vision/Utilities/test_classify.py::test_a_point_on_the_upright_crop_goes_back_to_where_it_is_on_the_frame`,
`test/Vision/test_core.py::test_a_judged_parts_features_and_similarity_are_on_the_frame`,
`test/UI/test_history_data.py::test_a_judged_parts_parts_round_trip_and_an_older_record_has_none`,
`test/UI/test_history.py::test_a_set_recorded_in_a_mode_that_no_longer_ships_loads_and_shows`.

## The similarity overlay shows where a part looks unlike its reference, and decides nothing

Decided 2026-10-11 (catalogue phase E): the request's DINOv2 similarity heatmap, as a separate diagnostic tab
(owner's ruling). For each judged part, each patch of its best-matched rotation's crop is compared with every patch
of the matched reference; 1 minus the highest cosine is laid on the part's pixels (`Classify.Similarity_Grid`,
`Vision.Core`), and the Camera View's **Similarity** segment (catalogue modes only, on screen only) shows it over
the frame (`Heatmap.Render_Overlay`, 55 % opaque) under the legend "Unlike the reference (DINOv2 patches) — not a
defect map", on a fixed 0–0.5 scale. The patch tokens come from the identification's own pass at 224 px (16 × 16
patches), so it costs no model time.

**Measured** (2026-10-11, at 448 px then 224 px, on Image_059): the fingerprints on 059 stand out at both, so
224 px was kept (owner's condition). Re-measured at 224 px on the 22 mounting plates (2026-10-13): a clean
plate's patches' mean 0.01–0.16 unlike, a stained one's 0.19–0.25, the fingerprints up to 0.63. Missing holes do
not show; glare shows as unlike. It is therefore not a defect
map, and no verdict reads it.

**Revisit if** a defect is seen only in it (then it is a check to build, not a reading of the overlay).
Tests `test/Vision/Utilities/test_classify.py::test_the_similarity_grid_is_the_best_turn_turned_back_upright`,
`test/Vision/Utilities/test_heatmap.py::test_an_overlay_colours_only_the_pixels_it_covers`,
`test/UI/test_camera_view.py::test_the_similarity_view_overlays_the_frame_and_needs_a_catalogue_reading`,
`test/Vision/test_core.py::test_a_judged_parts_features_and_similarity_are_on_the_frame`.

## History filters by the four states, and the Trends threshold line is neutral

Decided 2026-10-11 (catalogue phase E), resolving the two KNOWN_ISSUES entries left for it. History's filter has a
segment per state — All, OK, NOK, Warning, Unspecified, each with its count — and lists a set under every state
its objects took; a card is outlined in its worst state's colour (the status badge's order: NOK, Unspecified,
Warning, OK). The confidence chart's warning-threshold line is drawn in the neutral mid ink instead of the amber
a Warning object's dot takes; the error line keeps its deep red, which no verdict uses.

**Revisit if** a fifth state is added, or the threshold lines need telling apart by more than their dash.
Tests `test/UI/test_history.py::test_each_state_filter_lists_every_set_holding_that_state`,
`::test_a_set_is_outlined_in_its_worst_state`,
`test/UI/test_trends_view.py::test_the_warning_threshold_line_is_not_the_warning_verdicts_amber`.


## The catalogue holds only the mounting plate

Decided 2026-10-13, on the owner's instruction: the labyrinth was removed — its catalogue item, reference images
and mode file, and the code only it used (the logo check, `Checks.Logo`, its frame marks and report lines, and
`Example/Catalogue/logo_letters.py`). A catalogue mode is now the mounting-plate mode. Git history keeps the
removed code (its last commit is `4865eee`).

- **Its plates in the test frames are Warnings.** The 41 frames stay the pinned set, used in Segment Anything and
  the mounting-plate mode. In the latter its 37 plates read Warning (similarity 0.23–0.43 against the plate's
  0.75), as they were labelled before; no verdict on any frame changed.
- **The verified zone dropped to 46.4 mm**, from 74.3, because only mounting plates remain as evidence: the
  farthest judged plate's centre is 46.32 mm from the frame centre (Image_072). A size checked beyond it carries
  the note; the verdict stands.
- **Older capture sets still load.** A set recorded in the removed mode names its configuration and keeps its
  parts; the reader ignores the text fields this version no longer writes, and History shows it.

**Revisit if** another catalogue item is added (then its checks, its mode and its share of the verified zone
are measured afresh), or mounting plates are captured farther from the centre (then the zone widens).
Tests `test/integration/test_pipeline.py::test_each_frame_gets_its_expected_verdicts` (slow),
`test/Vision/Utilities/test_classify.py`,
`test/UI/test_history.py::test_a_set_recorded_in_a_mode_that_no_longer_ships_loads_and_shows`.


## Only OpenCV's headless build is installed: the installer removes the GUI build, and the application refuses it

Decided 2026-10-13, from a fault on the station: after `install.sh`, `App/run.py` aborted with "Could not load
the Qt platform plugin xcb in .venv/lib/python3.11/site-packages/cv2/qt/plugins". Both `opencv-python` and
`opencv-python-headless` 5.0.0.93 were installed. They share the `cv2` folder, the GUI build adds its own Qt
plugins there, and the window then loads OpenCV's xcb plugin. Uninstalling the GUI build alone deletes the
files the two share ("No module named cv2").

**Where it comes from.** `requirements.txt` itself asked for `opencv-python>=4.10`, and two dependencies require
it too: `ultralytics` 8.4.163 (`opencv-python>=4.7.0,!=4.13.0.90`) and `mlx-vlm` 0.7.2
(`opencv-python>=4.12.0.88`). The application needs the headless build only: the window is PyQt5's, and
nothing calls OpenCV's own GUI.

- **`requirements.txt` pins `opencv-python-headless==5.0.0.93`**, its one home; it no longer names the GUI build.
  The two dependencies still pull the GUI build in on every install, since pip cannot substitute one package
  for another.
- **`install.sh` swaps after every requirements install** (`Ensure_Headless_Opencv`, inside `.venv`): the GUI
  build uninstalled when present, the headless build reinstalled at its pin with `--force-reinstall --no-deps`
  (whole, its shared files restored, nothing else touched), then cv2 must import and `cv2/qt/plugins` must not
  exist, or the install stops naming the two commands. It runs before `pip freeze` compares, so a re-run in which
  pip brought the GUI build back and the swap removed it reports nothing changed. With only the pinned headless
  build and cv2 intact it installs nothing. The pip cache is used (the hand fix's `--no-cache-dir` is not needed
  for a whole reinstall).
- **`App/run.py` checks first** (`UI.Utilities.Opencv_Check`, before anything imports cv2): the GUI build's
  distribution, or `cv2/qt/plugins`, stops it with exit status 1 and a message naming
  `python -m pip uninstall -y opencv-python` and `python -m pip install --force-reinstall --no-deps
  opencv-python-headless==<pin>` (or re-running `./install.sh`), instead of Qt's core dump.
- **`pip check` reports** that `ultralytics` and `mlx-vlm` require `opencv-python`, which is not installed. That
  is this decision; their imports of `cv2` are served by the headless build.

**Measured** (2026-10-13, the development Linux machine, Python 3.11, a scratch environment with both builds
installed from PyPI): `cv2/qt/plugins` present; the startup check names both; `Ensure_Headless_Opencv` removed
the GUI build, reinstalled the headless one, and cv2 5.0.0 imported with no `qt` folder; a second run installed
nothing; after uninstalling the GUI build alone cv2 did not import, and the step reinstalled it. Not run on the
station, nor the whole `install.sh`.

**Revisit if** ultralytics and mlx-vlm accept the headless build (then drop the swap), OpenCV's GUI build stops
shipping Qt plugins, or the application starts using OpenCV's own windows.
Tests `test/Install/test_install.py` (the swap, idempotence, the stops, the check's own Python, its place after
the requirements install), `test/UI/test_opencv_check.py` (`App/run.py` stopping before cv2 and Qt).


## The configuration is a chain of references, mode → station → calibration, each kind in its own folder

Decided 2026-10-13, on the owner's request and rulings. `Configuration/` holds three folders, one per kind:
`Mode/` (`Config_<Hardware>_Mode_<Mode>.yaml`), `Station/` (`Station_*.yaml`) and `Calibration/`
(`Calibration_*.yaml`). A mode file names its station (`Station`, REQUIRED); the station file names its
calibration (`Calibration`, REQUIRED). Nothing is found by convention any more: the loader no longer builds
`Station_<Hardware>.yaml` and `Calibration_<Hardware>.yaml` beside the mode file
(`Configuration.Core.__Read_Reference`, `Load_Configuration`).

- **A reference is a file name, never a path**, of its kind (`Station_*.yaml`, `Calibration_*.yaml`), resolved
  in its kind's folder of the repository (`Station_Directory`, `Calibration_Directory`) wherever the file
  holding it is. A local copy of a mode file kept outside the repository — a station's, for its own
  station-event directory — reads the shipped station and calibration with nothing beside it. Until now that
  copy needed both files symlinked beside it; a path in a reference would make a copy read something else.
- **Each link is checked, and a failure names both files**: the station's `Hardware` must be the mode's; the
  calibration's `Hardware`, `Resolution` and `Offset` must be the station's. A missing reference fails the load
  with the line to add, where, and the files of that kind for the hardware.
- **Nothing loads uncalibrated.** A station that names no calibration fails, in the application and every
  harness. Until now a hardware without a calibration file loaded with a warning, not undistorted and not
  measured, so that `calibrate.py` could run on a new camera. That one case now has its own reader,
  `Load_Station_Camera`: the mode's Hardware and Station, and the station's camera — names, acquisition
  settings, window — validated as `Load_Configuration` validates them; no reference image, no calibration.
- **The calibration stays a file of its own, never inside the station file**: the station file is written by
  hand, with comments, and the calibration is written by a tool; and separate files keep every older
  calibration available to switch back to, by one line.
- **A calibration is never written over.** `calibrate.py --images` always writes a new
  `Calibration_<Hardware>_<YYYYMMDD-HHMMSS>.yaml` into `Configuration/Calibration/`, copying the header of the
  one in force, and prints the station file's `Calibration` line by number with the text to set (or, on a
  station with none, the line to add below `Hardware`). It never edits the station file. `Write_Calibration`
  refuses any file that exists, so the protection is in the writer, not in the tool's naming;
  `--write-calibration` (overwrite the one in force) is removed and says so. Adopting a calibration is that
  one deliberate edit, as adopting a reference is (`make_reference.py` prints the line too).
- **A mode file cannot override the station**: `Calibration` joins `Camera` and the background reference among
  the keys a mode file holding fails on, naming the station file.

**Migration.** The four files moved with `git mv`. The calibration in force was renamed after its solve,
`Calibration_a2A1920_51gcPRO_Computar_M1228_MPW3_20260928-110755.yaml`, so every calibration is named the way the
tool names them; its content is unchanged. Each mode file gained `Station:`, the station `Calibration:`. Older
records are untouched and still read: a capture set records the mode file's *name*, the reference, the hardware,
window and factor, and nothing resolves a recorded name back to a file. The reference sidecar's
`calibration.file` (`Calibration_<Hardware>.yaml`) is history; its check compares the lens model's fingerprint,
which the rename does not change. From 2026-10-13 a capture set also records the file names of its station and its
calibration (`_objects.json` `station`, `calibration`): calibrations are switched by one line, so the conversion
factor alone no longer says which one measured a set. A set written before reads both as empty
(`test/UI/test_configuration_dialog.py::test_each_capture_set_records_its_station_and_calibration`).

**Revisit if** two stations must share a station file with different references or lights (then the station
splits further), a reference must point outside the repository (a station's own calibration not committed),
or a second tool needs to write the station file (then it is no longer hand-written, and the calibration could
move into it).
Tests `test/Configuration/test_core.py` (`test_a_mode_file_without_a_station_fails_naming_the_line_to_add`,
`test_a_reference_must_be_a_file_name_of_its_kind`, `test_the_station_file_must_be_the_modes_hardware`,
`test_the_calibration_must_be_the_stations_hardware`, `test_a_calibration_solved_at_another_window_fails_the_load`,
`test_a_station_without_a_calibration_fails_naming_the_line_to_add`, `test_the_station_camera_reads_without_a_calibration`,
`test_switching_the_calibration_is_one_changed_line`,
`test_a_local_copy_of_a_mode_file_reads_the_shipped_station_and_calibration`,
`test_every_configuration_file_lives_in_its_kind_folder`, `test_the_calibration_writer_never_writes_over_a_file`,
`test_a_mode_file_never_overrides_the_station`), `test/Calibration/test_core.py`
(`test_images_harness_writes_a_new_calibration_and_prints_the_station_line`,
`test_a_first_calibration_is_a_new_file_and_the_harness_says_the_line_to_add`, `test_a_removed_flag_says_what_replaced_it`).

## Corners are square, as the brand draws them

No UI element and no rectangle in the architecture diagram has a rounded corner: cards, buttons, segmented controls,
pills, badges, the viewport, History's thumbnails and image panes, the Log's new-lines pill, Trends' read-out box,
the Configuration dialog's list and progress bar, scroll areas and their handles, and the camera and reading icons.
The radius tokens (`Style.CONST_RADIUS_CARD` 18, `CONST_RADIUS_BTN` 11) and every literal radius (3–15 px) are
removed, not set to 0, so no rule is left to re-round a corner.

**Why.** The JIC Smart Factory guide draws every block, tag and button square, with thin rules (the formats, the
banner and the poster), and the owner asked for square corners. Removing the radii rather than zeroing them keeps one
reading of the stylesheets: a radius anywhere is a regression, which a source scan can find.

**Revisit if** the brand guide changes its shapes.
Tests `test/UI/test_square_corners.py::test_no_ui_corner_is_rounded`, `::test_no_diagram_rectangle_is_rounded`.

## The palette is the JIC Smart Factory brand's, one purple, measured on the frames

The console, the frame's marks and the architecture diagram take their colours from the JIC Smart Factory guide
(`Parameters/Theme.py`): the purple `#640ABA` for all text, outlines, the selected segment and the OK verdict; the
grey-lilac `#E1DCE6` for rules, the control hover, the viewport and the neutral (Unspecified, detect-only); the
periwinkle `#C2C9FF` for a pressed button, the scroll handle and the OK verdict's word ground; and from the wider
JIC palette in the same guide the orange-red `#FF6540` (NOK), the amber `#FFC226` (Warning) and the green
`#3DBE4C` (system health only). One purple: the owner dropped the poster's dark purple `#2D0557` everywhere, the
hover fills, the text on chips and badges, an outline under the marks and the diagram's band. Text twins too light
for words are derived in each colour's hue at L\* 41 (6.2:1 on white, 4.6:1 on the grey-lilac). The guide's yellow
`#FFEF85` is decoration and is no token.

- **On the frame.** OK is the purple, as the poster marks a detected part; NOK the orange-red, as it marks a defect;
  Warning the amber; Unspecified the grey-lilac. A chip is filled with its box's colour, as on the poster, with a
  white numeral on OK (9.15:1) and NOK (2.92:1: **the owner's one deliberate exception** for these short bold
  numerals, pinned at that value) and a purple one on Warning (5.66:1) and Unspecified (6.79:1). The box stays the
  dashed axis-aligned box around the solid rotated outline of a measured part; corner brackets (the AnyScan mark's
  motif) were rendered and not chosen.
- **Words on a verdict.** The badge and the diagram's verdict labels set the purple on the verdict's ground where it
  reads at ≥ 4.5:1 (Warning's amber, the grey-lilac) and on the poster's tint of it otherwise: the part tag's
  periwinkle for OK (5.71:1) and the defect tag's `#FFD9D0` for NOK (7.01:1; the purple on the solid orange-red is
  3.13:1). Trends draws each verdict's series in its text twin (the boxes are under 3:1 as lines on white) and the
  total in the muted purple-grey, since OK is the purple.

**Why, measured.** Per-pixel WCAG ratio on the test frames (055, 062, 063, 065, 072, 074, 076, 080; 60,000 pixels
per surface; plate interiors from each object's own mask, eroded 7 px; the table outside the dilated masks). Median
surfaces: the table `#1A6651` (L\* 38), bright aluminium `#A49FA7` (66), the dark rusted plate `#3A3A3A` (25),
rust-stained metal `#999298` (61), a stain `#786354` (44).

| Colour | table | aluminium | dark plate | rust-stained | stain |
|---|---|---|---|---|---|
| OK `#640ABA` | 1.3 | 3.5 | 1.3 | 3.0 | 1.6 |
| NOK `#FF6540` | 2.4 | 1.2 | 3.9 | 1.2 | 1.9 |
| Warning `#FFC226` | 4.3 | 1.6 | 7.0 | 1.9 | 3.5 |
| Unspecified `#E1DCE6` | 5.1 | 1.9 | 8.4 | 2.2 | 4.2 |
| green `#3DBE4C` (not chosen for OK) | 2.8 | 1.2 | 4.7 | 1.3 | 2.3 |

- No single colour can reach 3:1 against both the dark plate and the aluminium (relative luminance ≥ 0.227 and
  ≤ 0.085 at once), so a "stronger" fail colour only trades one plate for the other: `#D03C1D` reached 1.9:1 on
  aluminium and lost the table (1.4:1) and the stains (1.2:1). An outline under the marks lifts them on bright metal;
  the owner chose none, by eye (*A judged part's features are marked on the frame*).
- The OK purple is 1.3:1 against the table and the dark plate; it reads there by hue (ΔE 119 and 96). The owner
  judged it acceptable as it is (2026-10-14), at the shipped weights, from 1:1 renders of Image_056 (the dark back)
  and Image_077, over thicker lines or a lighter purple for the frame's marks.
- Green was not chosen for OK although it does not vanish on the table (2.8:1, ΔE 60): its hue is 28° from the
  table's teal, against 119° for the periwinkle that was first proposed, and the poster marks a detection purple.
- The four boxes are ≥ ΔE 44 apart; NOK and Warning are ΔE 27 under deuteranopia, where the words and the weights
  carry them as before.
- Every enabled text clears 4.5:1 on its ground and every control state does, measured from rendered pixels
  (`test_text_contrast.py`, `test_control_contrast.py`).

**Revisit if** the brand guide changes, the work surface or the parts change (the table above is one table under one
light), or the owner wants the frame's marks to clear 3:1 on bright metal (the outline is the measured lever).
Tests `test/Parameters/test_theme.py::test_verdict_colour_comes_from_the_one_constant`,
`::test_chip_numerals_clear_4_5_but_the_one_nok_exception`, `::test_the_palette_keeps_the_brands_rules`,
`::test_label_mask_fill_is_a_visible_tint_of_its_box`, `::test_every_catalogue_state_has_its_colour`,
`test/Vision/Utilities/test_annotate.py::test_each_chip_is_its_box_colour_with_its_numeral_colour`,
`test/UI/test_reading_view.py::test_the_badge_paints_each_verdict_level_legibly`, `test/UI/test_text_contrast.py`,
`test/UI/test_control_contrast.py`.

## The funding band is the poster's: the project's, the Ministry's and the EU's logos in white on the purple

The band at the foot of the window (`Widgets.Funding_Row_Cls`) and the architecture diagram's are one band, as on the
AnyScan poster's footer: on the solid purple `#640ABA`, the EDIH-DIGIMAT wordmark, a white rule, the Ministry of
Industry and Trade's logo and the EU emblem with "Funded by the European Union", then a white rule and the EU
disclaimer, all in white (9.15:1). The diagram reads the window's list (`Funding_Row_Cls.LOGOS`).

The logos are their white (reverse) versions, `App/assets/*-white.png`, the ones the band has carried since
2026-09-17. The EDIH-DIGIMAT wordmark and the EU emblem are all white. **The Ministry's logo has no all-white version
in the repository's history:** its white file keeps the coat of arms as a white field with the black Czech lion (8 %
of its ink is dark), beside white text, as the earlier colour file kept the red-and-white shield. The earlier colour EU
file (deleted 2026-09-17) read "Co-funded by the European Union"; the white one and the disclaimer read "Funded by".

*Corrected 2026-10-14:* earlier the same day this entry was "The application shows the EU emblem alone; the diagram's
band keeps the project's logos": the window showed the white EU emblem and the disclaimer in one slim row, and a light
band was to follow with the colour emblem. On the station's screen the owner chose the poster's footer instead.

**Revisit if** the funding or its publicity rules change, or vector (SVG) versions of the three logos are supplied:
they are the window's only raster logos, drawn scaled down 8–26 times from their PNGs.
Tests `test/UI/test_funding_band.py::test_the_band_carries_the_three_logos_and_the_disclaimer_in_white`,
`test/UI/test_brand_figures.py::test_the_diagram_is_self_contained_and_carries_every_logo`.

## Logos are rendered as vectors at paint time

Every SVG logo the window shows is rendered by a `QSvgRenderer` into the widget's painter whenever it paints: the
AnyScan lockup's mark and wordmark (`Widgets.Logo_Lockup_Cls`), the JIC Smart Factory logo (`Widgets.Svg_Image_Cls`)
and the mark in the empty Camera View (`Viewport_Cls`). The vectors land on the device pixels they are drawn on, at
any device pixel ratio, and no logo is a pixmap scaled to fit. A pixmap of a logo is rendered only to measure its ink
(`Style.Ink_Insets`), never drawn. The funding band's three logos exist only as PNG and stay pixmaps.

**Why.** On the station's 1x display the logos looked blurred. Measured offscreen (the share of a logo's ink pixels at
full contrast, as the window draws it, against the same SVG rendered directly at the drawn device size):

| Logo | DPR 1 before → after (direct) | DPR 2 before → after (direct) |
|---|---|---|
| AnyScan mark and wordmark | 0.697 → 0.699 (0.699), up to 76 levels apart → identical | 0.808 → 0.805 (0.805), 80 → identical |
| JIC Smart Factory | 0.628 → 0.625 (0.625), 229 → identical | 0.729 → 0.729 (0.729), 102 → identical |
| Camera View mark | **0.818 → 0.894** (0.894), 70 → identical | **0.896 → 0.990** (0.990), 71 → identical |

The Camera View's mark was the real blur: a 256 px raster scaled down to about 210 px. The header logos were rendered
into pixmaps at the application's ratio and rounded to whole-pixel widths, which stretched them slightly (hence the
pixel differences); where the application's ratio differs from the window's screen, Qt then scales such a pixmap when
drawing it, which offscreen could not reproduce. Rendering at paint time removes both. What remains at 1x is the
logos' own geometry: their edges fall between pixels at these sizes (the AnyScan mark and wordmark 0.70, the JIC logo
0.63 of their ink at full contrast). *Followed up 2026-10-14:* on a 1x display the two header logos' marks are now
grid-fitted (*The header logos are grid-fitted on a 1x display*).

**Revisit if** a logo is added (render it through `Svg_Image_Cls`), or the band's logos become available as SVG.
Tests `test/UI/test_logo_rendering.py` (each SVG logo against a direct render, at DPR 1 and again at DPR 2; the
previous pixmap code fails every one), `test/UI/test_header.py`.

## The header logos are grid-fitted on a 1x display

On a display of device pixel ratio 1 the AnyScan lockup and the JIC Smart Factory logo are drawn with their mark's
straight edges on whole pixels (`UI.Utilities.Grid_Fit.Fit_Svg`, through `Widgets.Svg_Renderer_For`): the AnyScan mark
(every shape left of 152 units, `Style.CONST_LOGO_MARK_RIGHT`) and the J-I-C bars (left of 452, `CONST_JIC_MARK_RIGHT`).
The SVG is fitted for the exact drawn height, once, and rendered as vectors. Rectangles, polygons and straight paths are
fitted, filled ones through one map per axis (an edge shared by two shapes stays shared; a stroke under 10 px keeps its
rounded width, so equal strokes stay equal), stroked ones with a whole-pixel stroke centred so both its edges land on
pixels. Each edge moves by under a pixel. The lettering (curves, and everything right of the mark) and the mark's
numeral are drawn exactly as delivered, and at any other ratio the whole logo is.

**Why.** On the station's 1x screen the header logos still looked soft after they were rendered as vectors at their
drawn size: their edges fall between pixels. The owner asked first for drawn sizes whose main edges land on whole
pixels; measured, no size does it, because the edges are not on a regular grid (the AnyScan mark's edges at 9, 18, 19,
23, 32 … 131, 140 of its 140 units): the best heights near the header put 52 % (63 px) or 50 % (77 px) of the mark's
edge length within 0.1 px of a pixel against 23 % at 69 px, and 37 % of the J-I-C bars' (34 px) against 8 %. The owner
chose grid-fitting at the drawn sizes. Measured on direct renders (the share of the mark's ink pixels fully covered,
and partly covered):

| Logo | before | after |
|---|---|---|
| AnyScan mark, 69 px (96 dpi) | 0.68 full, 0.33 partial | 1.00 full, 0.00 partial |
| AnyScan mark, 72 px (100 dpi) | 0.66, 0.39 | 1.00, 0.00 |
| J-I-C bars, 33 px (96 dpi) | 0.72, 0.28 | 1.00, 0.00 |
| J-I-C bars, 35 px (100 dpi) | 0.75, 0.28 | 1.00, 0.00 |

At 69 px the brackets are a 4 px stroke (4.43 delivered), the mark's three bars 3 px each (3.45), its frame 2 px
(2.46); at 33 px each J-I-C bar is 6 px (6.47) and the C's and J's feet are level with the I's.

**Revisit if** the logos are redesigned (the mark's right edge, and whether its shapes are still straight), or the
station moves to a display of another ratio, where the logos are drawn as delivered.
Tests `test/UI/test_grid_fit.py` (equal strokes stay equal where rounding each edge alone would not; a translated
relative path; curves and the lettering left as delivered; both logos' marks on whole pixels at 69, 72, 33 and 35 px),
`test/UI/test_logo_rendering.py::test_at_1x_the_header_marks_have_no_half_covered_pixel` and the DPR 1 and DPR 2
vector-identity tests, `test/UI/test_header.py` (the fitted lockup still within 1 device px of the outlined logo).
