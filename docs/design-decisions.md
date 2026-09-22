# Design decisions

The reasoning behind the non-obvious choices in the vision port, so the next person does
not undo them. Each entry states the decision, the reason, and what would justify
revisiting it. This is the counterpart to [`KNOWN_ISSUES.md`](../KNOWN_ISSUES.md): that
file records latent quirks left unchanged; this file records deliberate choices whose
motivation is not visible in the code. A change that contradicts one of these should cite
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
clearly as grey, including at full size on `Image_001`; L\* 85 (ΔE ~16) starts drifting back toward
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

## The colour-name saturation cutoff is 120, and was not tuned for object 4

The model-free describer calls a pixel "coloured" only above HSV saturation 120
(`Describe_Fallback.CONST_COLOR_SAT_MIN`); below it the object reads as grey/metal. 120
sits in a real gap measured across all seven frames: metal parts top out near S=98, truly
saturated colours start near S=184, and the dark plates in `Image_003`/`005` sit at 35–40,
far from the line. Object 4 (a pink block) lands at S=121, one point above — but the field
is decided by a per-pixel majority vote, not the median, which is more robust than any
median-based cutoff, and lowering the line to 110 to "protect" object 4 would only move
the tightness toward the metals at 98 and close the gap. So it was left at 120. **Revisit
if** new captures show real coloured parts clustering in the 98–184 band; the honest fix
then is a better colour feature, not a nudged threshold.
Commit `62c5097`; tests `test/Vision/test_describe_fallback.py::test_weak_metallic_cast_reads_grey_not_blue`, `::test_red_straddling_the_hue_wrap_votes_red_not_blue`.

## Objects are not all routed through FastSAM to complete the confidence metric

The `Confidence (mean)` status field only has a score for objects FastSAM found; a
background-cue-only object carries none, so the field shows the mean over exactly the
scored objects **with its coverage** (`87% (5/9)`) and `—` when none are scored, rather
than averaging over a partial set. It is tempting to force every object through FastSAM so
the metric is complete, but the fusion exists precisely because neither cue is sufficient:
forcing them through means lowering thresholds until FastSAM sees them (which admits false
detections) or a second region-prompted pass (which roughly doubles the slowest stage) —
changing *detection* to populate a *status* field. **Revisit by** giving the
background-subtraction cue its own confidence (normalised change magnitude or mask-edge
sharpness) so every object scores from whichever cue found it; until then the coverage
fraction is the honest disclosure.
Commit `4407c87`; [`KNOWN_ISSUES.md`](../KNOWN_ISSUES.md) "confidence status metric is partial"; tests `test/UI/test_status_metrics.py::test_confidence_denominator_is_the_scored_count_not_the_total`, `::test_confidence_is_no_value_when_no_object_has_a_score`.

## The fusion needs both cues — `Image_001` proved it in both directions

Detection fuses FastSAM instance masks with OpenCV background subtraction: an object
survives on **either** cue. This is not redundancy. On `Image_001`, objects 2 and 9 came
back with background-subtraction coverage `cov=0.00` — the background cue missed them
entirely and FastSAM carried them — while the `cue = background` objects (four of nine)
had no FastSAM mask at all and were carried only by background subtraction. Dropping either
cue loses real objects. **Revisit only** if a single cue is shown to cover every object
across a representative set of frames, which today's evidence contradicts.
Commit `fe4f10c`; tests `test/Vision/Utilities/test_fusion.py::test_object_seen_only_by_fastsam_survives`, `::test_object_seen_only_by_background_survives`.

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
Commit `c34983e`; tests `test/Camera/test_configuration.py`, `test/UI/test_history.py::test_the_two_empty_nok_states_are_distinguishable`, `test/Vision/Utilities/test_annotate.py::test_verdict_colored_false_draws_one_neutral_colour_not_verdicts`.

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
(`#E2E0F0`) on a detect-only run, and `Example/UI/screenshot.py` built its window detect-only but
rendered its `demo_*.png` beside it in verdict mode — two modes in one run. A default is a
rendering mode chosen on the caller's behalf; with none, a caller that has not decided fails at
the call site, and the keyword makes a bare `True`/`False` impossible to pass without naming it.
Both harnesses now read `General.Classification.Enabled` through the application's own
`Read_Classification_Enabled` and default config (`analyze.py --config` overrides it), because
`analyze.py` validates the logic the app uses — a harness rendering in another mode would make a
harness artefact look like a real difference. **Do not reintroduce a default.**
Tests `test/UI/test_harness_parity.py` (the harness mask equals the mask the window writes, for
both flag values; the harness uses the app's config reader; the renderers reject an unstated mode).

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
- **Precision from the scale.** Sizes are shown to one pixel's size: `floor(−log10(mm/px))`
  decimals — 0.098 mm/px → 0.1 mm. That is already the most the mask edge supports.
- **Rotationally symmetric parts report a diameter and no angle.** `minAreaRect` assigns a round
  part an orientation that changes on noise, so a drawn rectangle would appear to spin on a part
  that has not moved. The test is elongation — the square root of the mask's second-moment
  eigenvalue ratio — below **1.15**: the seven `Data/Camera` frames put round parts at 1.008–1.031
  and the least elongated real part at 1.498 (the plates in 002–005). **A square is the exception:**
  it is as un-elongated as a disc (1.02, the plate in 006/007) but its sides are real edges that
  `minAreaRect` finds reliably, so un-elongated parts are only called symmetric when also round —
  extent (contour area / rectangle area) below **0.92** (round parts 0.81–0.85, the square 0.98–0.99).
  A square keeps A × B and an angle folded to [0°, 90°), since its sides are interchangeable. A
  round part's diameter is the mean of the rectangle's sides; a hexagonal one reports across flats
  (next entry).
- **Camera View drawing.** A measured, elongated object is drawn twice in its one verdict colour:
  the rotated rectangle **solid** at the full box weight (the measurement) and the axis-aligned box
  as a **thin dashed** line (now only the reference that carries the number chip) — solid versus
  dashed reads as "measurement" versus "reference" where two weights alone could read as one
  confused shape. Symmetric and unmeasured objects keep the single solid axis box; the label mask
  is unchanged.

**Revisit if** a part family needs orientation modulo 60° (hex). See KNOWN_ISSUES: the sizes may
carry a systematic error of unknown magnitude and are not for acceptance decisions until checked
against references of known size.
Tests `test/Vision/Utilities/test_measure.py`, `test/integration/test_pipeline.py::test_symmetric_parts_measure_as_diameters_on_real_captures` (slow).

## Symmetric parts: round ones report Ø, hexagonal ones report across flats (A/F)

A hexagon's across-corners width is 2/√3 = 1.155 × its across-flats, so one hex nut has two
standard "diameters" 15 % apart, and the mean of the rotated rectangle's sides — the round-part
convention — lands between them and matches neither. A nut is specified by its across flats (the
wrench size), so a hexagonal symmetric part reports that, and the label names the convention:
`A/F 11.7 mm` beside a round part's `Ø 14.7 mm`. The two can never be read as the same kind of
number.

- **What counts as hexagonal.** The part's caliper (Feret) width is sampled over 180° from its
  convex hull; a hexagon's repeats every 60°, so its third harmonic is strong. *Hexagonality* is
  that harmonic's amplitude over the mean width, and **0.0075** is the threshold. Measured: the
  two washers in `Image_001` 0.0016 and 0.0026, the two nuts 0.0204 and 0.0254 (lower than an
  ideal hexagon's 0.038–0.057 because the masks round the corners), pixelated ideal discs ≤ 0.0021
  down to 24 px across. 0.0075 sits near the geometric mean of the closest washer and nut, about
  2.7× from each. The round parts are only in `Image_001`, so this rests on two parts of each
  kind; the synthetic cases (discs and hexagons at several sizes and rotations) are the wider net.
- **Only the 60° harmonic.** A general "polygonal" test (any harmonic 3–8) fails on this data:
  washer 1's own mask is a slightly squared circle with a 4-fold component of 0.012 — stronger
  than the threshold. Square parts never reach this branch anyway (their extent excludes them).
- **Across flats is the smallest caliper width**, converted through the factor along its own
  direction. It is also the robust choice here: the masks clip the nuts' corners (nut 7's widest
  caliper width is 1.13 × its across flats, not 1.155), which pulls a mean or an across-corners
  number but not the flats. On `Image_001` nut 7 moves from Ø 12.0 to A/F 11.7 mm and nut 8 from Ø 11.6 to
  A/F 11.5 mm — much less than the theoretical 7.5 %, for exactly that reason.
- **Stored.** `_objects.json` records `across_flats` and `hexagonality` (null when the part is not
  symmetric). A record written before this convention has no `across_flats` and reads back as a
  round Ø, which is what it was measured as.

**Revisit if** another polygonal family appears (an octagonal part would need its own harmonic and
its own evidence), or if the nuts' measured A/F disagrees with a caliper by more than the scale
check in KNOWN_ISSUES explains.
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

**Why now:** the reference check (known-size parts at the centre and in the corners) must stay
usable whichever calibration ends up in force, and the calibration is about to be redone.
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
  to the sensor. Capture 20+ views.
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
