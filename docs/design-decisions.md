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
| neutral | `#B8BECA` | `#F1F2F4` → **`#737883`** (derived) | 19.5 → 26.5 | 4.7 → 50.1 | 4.7:1 |

OK and NOK share L\* 72 at about half their box's chroma, so only hue separates them, as with
the boxes. The neutral box is nearly achromatic and already light, so lightening it can only
reach white; its fill goes the **other way**, to a mid grey in the box's cool hue — the outline is
the lighter of that pair.

**The neutral fill is derived from its box, not hand-set** (`Theme.Neutral_Mask_Fill`). Its valid
window is only 2.97 L\* wide: the lower bound, L\* 48.88, is where the fill would drop under 4.5:1
against the black ground (fixed, independent of the box); the upper bound, L\* 51.85, is the box's
L\* 76.85 minus the ΔE 25 floor, and it moves with the box. A hand-picked fill would silently fall
out of that window the moment someone adjusted `#B8BECA`, so the fill is computed at the window's
midpoint in the box's own hue and chroma (`#737883`, L\* 50.35, 1.5 L\* inside each bound against a
required 0.5). Adjust the box and the fill follows; darken it below L\* 74.88 and the window
closes — there is then no valid darker fill, and Theme raises at import naming the window, because
a different neutral needs a design decision, not a silently broken mask. The floors
(`Theme.CONST_MASK_FILL_*`, in the parameters layer because Theme derives with them) are stricter
than the general ΔE 12 because a thin outline must
stand out against the fill it crosses: ΔE box↔fill ≥ 25, ΔE fill↔white ≥ 25, ≥ 4.5:1 against the
black ground, and a chromatic fill within 5° of its box's hue at ≥ 40% of its chroma. The OK/NOK
box↔fill ΔE went *down*: that is the cost of a fill that is actually a colour, and both stay well
above the floor. When classification is off the fill is the neutral one, implying no verdict
nobody made.
**Revisit if** the operator-facing mask needs to encode something other than verdict (e.g.
per-class colour), in which case add a mode rather than overloading the default.
Tests `test/Parameters/test_theme.py::test_label_mask_fill_is_a_visible_tint_of_its_box` (fails
on the old values: "OK: fill #E2E0F0 reads as white"),
`::test_neutral_fill_is_derived_from_its_box_inside_the_valid_window` (the window bounds and the
fill's margin inside both), `::test_neutral_fill_follows_the_box_and_fails_loudly_when_no_fill_fits`,
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
capture directory names (`<timestamp>_s<N>`) and the run-summary CSV's `sessions_count`,
`total_session_time` and `session_details` all count **camera connections**. In the UI a connection
is called a **Connection** — the History grid headers, the Info panel, and the Log view's prose
lines ("Camera connected. Connection 1 started.", "Connection 1 ended after …", "Created the
capture directory for connection …"). The Log is UI and speaks the UI's words. The CSV is a file
format: its `session*` column names are a data contract that existing rows carry, so they stay.

**Three spans, named precisely** — they differ on purpose, and each is labelled for what it is:

- **Status-bar aggregates and the Trends charts: since the application started or the last
  Clear.** The UI calls this the **run** ("Inference (run median)", "Confidence (run mean)", the
  charts' "Run mean" line); Clear resets these figures and both charts together, because they read
  one accumulator.
- **History: the application run**, identified by the run id in each set's `_objects.json`. Clear
  does not hide sets; History shows every set written since the application started.
- **The run-summary CSV: one row per application run**, whole-run, ignoring Clear;
  `clears_count` records the Clear presses, so a row that differs from the status bar's last
  reading is explained rather than looking like a bug.

So after a Clear, the status bar and Trends restart while History and the CSV do not. That is the
intended behaviour, not a counting bug.
**Revisit if** the capture directories are renamed, at which point "session" can leave the code
too; the CSV columns keep their names regardless.

## Trends: one accumulator, a hand-drawn chart base, and no failed image on the x axis

The Trends view (Live · Trends · History · Log — named for what it shows: both charts are
running values over the run's images, not summary statistics) draws two charts: cumulative
detected objects (Total, plus OK/NOK when the run classifies), and confidence (one dot per scored
object, the frame mean, the running run mean, dashed 80%/60% lines at the §5 thresholds).

- **One accumulator** (`Reporting.Trends.Trends_Accumulator_Cls`, Qt-free) feeds both charts
  *and* the status bar's IMAGES ANALYSED, OBJECTS DETECTED and run-mean confidence, so the last
  point of each series is the status figure by construction, not by two paths agreeing. It spans
  **since the application started or the last Clear** (Clear resets it), not the whole application
  run — History and the run-summary CSV cover that (see the vocabulary entry).
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

## Run-summary CSV columns are appended, never renamed, and old files are extended in place

The CSV gained `run_id, classification_enabled, failed_analyses, scored_objects, nok_objects,
mean_confidence, median_inference_ms, clears_count` after `error_details`. Columns are only ever
**appended** — never renamed or reordered — so an older file's header is a strict prefix of the
current list. On the first run that closes onto such a file the logger extends the header line
once (`Logger.Core.Extend_Csv_Header`): the new header is written to a temporary file and
atomically replaces the CSV under the file lock, every existing row stays byte-identical, and a
reader treats an old row's missing trailing cells as empty. Any other mismatch (reordered, renamed,
or a header from a newer version) keeps the align-and-warn path rather than guessing. A row appends
through a handle re-checked after the lock is taken, so a run that waited while another extended
the file does not write into the replaced one.

Every figure is **whole-run**: one row per application run, and Clear — which resets only what the
UI shows — does not reset the CSV. `clears_count` records the Clear presses so a row that differs
from the status bar's last reading is explained, not mistaken for a bug. `run_id` is the id every
capture set's `_objects.json` carries, joining a row to its sets. `mean_confidence` and
`median_inference_ms` are blank, never 0, when nothing was scored / no analysis completed.
`nok_objects` is 0 until a classifier exists, and `classification_enabled` in the same row says
whether that 0 means "none failed" or "nothing was judged".
Tests `test/Logger/test_csv_extension.py`, `test/UI/test_run_summary.py`.

## `session_details` and `error_details` are JSON; older rows keep the colon encoding

Both breakdown cells used to pack entries as `index:HH:MM:SS-HH:MM:SS:HH:MM:SS` (and
`…:message` for errors), joined by ` | ` — colons separating timestamps that themselves contain
colons. That is readable only by a positional regex that assumes every time is exactly
`HH:MM:SS`; it breaks once a duration reaches 100 hours (`Format_HMS` widens the hour field),
drops the date (a session crossing midnight is ambiguous), and required sanitising `|` and
newlines out of error messages. Both cells are now compact JSON arrays with full datetimes at
millisecond precision —
`[{"index":1,"start":"2026-09-22 20:18:38.412","end":"2026-09-22 20:18:39.998","duration":"00:00:01.586"}]`,
errors adding `"id"` and a verbatim `"message"` — parsed with any JSON reader.

**Every row checks out arithmetically.** The old cells printed whole-second start/end but rounded
the duration from the exact times, so an entry could read 20:18:38 → 20:18:39 with a duration of
00:00:02 — internally inconsistent, and the kind of thing that makes someone doubt the totals.
Now each entry's timestamps are cut to whole milliseconds and its duration is derived from exactly
those two values, so `start + duration == end` holds for every entry. The whole-second columns
keep their `HH:MM:SS` format (a contract) but are derived from the values the row prints:
`cycle_time` is the printed stop minus the printed start, `total_session_time` and
`total_error_time` are the detail durations rounded to seconds, and `idle_time` is the cycle minus
that session total, so `cycle_time == total_session_time + idle_time` exactly.

**Where the change starts.** Old rows are not rewritten. The encoding is self-identifying: a JSON
cell begins with `[`, a legacy cell with a digit, and an empty breakdown is an empty cell in both.
It takes effect from the commit "Run-summary CSV: encode session_details and error_details as JSON" (the one after `fdc6edd`); the first real run after it writes the first JSON row,
and that row also carries a `run_id`, the first run id in the file. **Millisecond timestamps and
the self-consistent arithmetic** start one commit later ("Run-summary CSV: millisecond detail
timestamps; every row adds up"): a JSON timestamp with a `.mmm` fraction is the new behaviour. No
row was written in between — the real file had no JSON cells when this landed — so in practice
every JSON row is millisecond-precise, and every legacy row keeps its original rounding. To read a legacy cell, split on
` | ` and match each entry with
`^(\d+):(\d{2}:\d{2}:\d{2})-(\d{2}:\d{2}:\d{2}):(\d{2,}:\d{2}:\d{2})$` (sessions) or the same
followed by `:(.*)$` (errors: id, start, end, duration, message) — verified against every legacy
entry in `logger/log_a2A1920_51gcPRO_Computar_M1228_MPW3.csv`.
Tests `test/Logger/test_core.py::test_reference_run_row_values`,
`::test_details_round_trip_with_commas_and_quotes`.

