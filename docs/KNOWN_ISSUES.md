# Known issues

Open behaviours that show up in AnyScan's text or numbers but decide nothing, recorded so they are recognised when
they appear. The limitations that do affect a decision built on the output are in
[SPEC > Known limitations](SPEC.md#known-limitations).

Each entry states the behaviour, what it means for whoever uses the output, and why it is not fixed. A fixed issue
leaves this file.

## Basler's grab retries print to the console and never reach the session log

`Basler_Cls.Capture` (`Camera/Basler.py`) retries a failed or incomplete grab up to three times and prints each failed
attempt to the console only. A frame that arrived after retries leaves no line in the session log, so the log cannot
show how often grabs were dropped; a grab that fails on every attempt is reported and logged as a failed scan. A cable
or camera that starts dropping frames therefore shows only on the console. Reporting it needs the attempt count passed
back to the camera and logged, a change checked with a real camera.

## The fusion's parameters are validated on one table under one light

What decides detection is set in the configuration: `Segmentation.Background.*` (the Otsu floor, the opening and
dilation kernels) and `Segmentation.Fusion.*` (the closing kernel, the minimum component area, the background-rejection
fractions and border count). Two constants in `Vision/Utilities/Fusion.py` only label which cue found an object (the
0.10 overlap) and order and limit the objects (the row band and object cap).

They are validated on the 41 test frames (`Data/Images/Test`, `Image_055`–`095`, shot 2026-10-09), each frame's count
pinned against a by-eye inventory, all matching against the shipped reference `Image_Background_001`. The three 2×2
grids of plates set close together (`Image_093`–`095`) come back as four objects each. Earlier test sets, no longer in
the repository, matched too, apart from the misses below. 41 frames of one table under one light is a narrow base.

- **Seen on earlier sets:** parts that touch or nearly touch, and a dark rusted plate the background cue barely saw
  (2 % of it), carried by FastSAM alone (`b5ca788^`); an extra object in the bottom-right corner on frames that skipped
  the undistortion the reference went through (`e2b87bd`).
- **Not yet seen on real data:** parts close to the table's colour, and any other lighting.
- **The failure signatures to watch:** a real part missing from the count; one part split into two components (the
  closing does not join two separate ones; not seen yet); two neighbours merged into one (*Touching parts merge before
  the closing*); a part's outline running into its shadow (the harsh-shadow entry below).
- **Impact:** the parameters are trusted on these frames only. When a signature appears, find the stage that causes
  it before changing a parameter.
- **Pinned by:** `test/integration/test_pipeline.py::test_counts_match_the_inventory`.

## Touching parts merge before the closing

Two touching parts read as one object: the count is one low and the size is the pair's. Seen on five two-plate frames
of an earlier set (recoverable from `b5ca788^`), three of which came back as one object. The current set has plates set
close together but none touching, and counts them right.

There are two independent causes. FastSAM returns a hierarchy, and nothing structural tells which level holds the
division: two touching plates and one machined plate's two halves measure the same. And a bridge remains in the
background cue or in FastSAM's own masks when the both-plates mask is removed. Five routes were measured (2026-09-28)
and all fail: a lower FastSAM NMS `IoU` (0.7, 0.5, 0.3); a larger `Segmentation.Image_Size` (1280–1920, which breaks
frames that counted right, so it stays 1024); splitting by the seam's darkness (it would split the printed robot too);
dropping a parent mask over two disjoint children; splitting along FastSAM's leaf masks. The measurements per frame and
route are in this file's history at `d9305b2`.

- **Impact:** a part count one low, with one object sized as two parts, when parts touch.
- **Not fixed here:** two plates butted against each other is not a realistic inspection case. A fix would need both a
  segmenter that picks the middle level (flat instances, depth, a second view) and a separate answer for the
  background bridge.
- **Pinned by:** nothing; restoring the frames from `b5ca788^` with their inventory entries brings the strict xfails
  back.

## The label mask reveals near-but-distinct objects, not merged touching ones

The exported label mask (`Vision.Utilities.Annotate.Draw_Label_Mask`) fills each object with a light tint of its box
colour and outlines it from its own component mask. Two parts close together but not touching are separate components,
so the mask shows two shapes. Two parts that touch are already one component before anything is drawn
(`Vision.Utilities.Fusion.Fuse_Objects`), so they render as one shape (*Touching parts merge before the closing*).

- **Impact:** a genuine merge is invisible in the mask. The object count against expectation is the only way to see it
  (OBJECTS DETECTED in the status bar, and the Trends chart).
- **Pinned by:** `test/Vision/Utilities/test_annotate.py::test_mask_separates_near_but_distinct_objects`.

## Open question: FastSAM's reliability on low-contrast shapes

FastSAM dropped low-contrast objects twice during development, in independent synthetic scenes: no mask for a flat
mid-grey box (BGR ~105) on the green reference, and a near-black plate (BGR ~25) dropped in one layout after being
segmented cleanly in another, although the change mask found it. So objects close to the surface's colour, or dark and
featureless, are the ones FastSAM's everything mode is least dependable on, and its output is not fully deterministic
across scenes. This is an open question, not a confirmed limitation: real metal parts carry highlights and texture a
flat synthetic fill does not.

- **Impact:** grey, metallic and dark parts are what AnyScan inspects, so the answer cannot be assumed either way. The
  fusion carries a part FastSAM misses if the background difference sees it, so the risk is highest for parts close to
  the table's colour.
- **What would answer it:** real low-contrast parts on the reference background, analysed with
  `Example/Vision/analyze.py`, each checked to come back as an object. If real parts are missed, lower
  `Segmentation.Confidence` or revisit the segmenter.

## A very harsh cast shadow can be absorbed into a part's component

On real captures a soft cast shadow is removed by the background opening (`Segmentation.Background.Open_Kernel`) and
the part comes back as a tight silhouette; no frame of the current set over-counts. The open case is synthetic: a
shadow far darker and larger than any captured (a 40 %-darkening ellipse) clears the Otsu floor and is absorbed into the
object's component. It stays one object, but the outline runs into the shadow and the describer's crop holds a strip of
table.

- **Impact:** a looser outline and size for a part under a very harsh shadow; the count is unaffected.
- **Fixed case, pinned by:** `test/integration/test_pipeline.py::test_plates_come_back_as_compact_silhouettes_on_a_real_capture`
  (slow; `Image_072`, rectangularity ≥ 0.80) and `::test_counts_match_the_inventory`.
- **Open case, pinned by:** `test/integration/test_pipeline.py::test_synthetic_harsh_shadow_not_absorbed_xfail` (slow,
  strict xfail: when the shadow stops being absorbed it passes and the suite fails, the signal to make it a plain test
  and close this entry).
- **Not fixed here:** the thresholds are set against real captures; tuning them to a scene darker than any real one
  would move the failure. A real harsh shadow, analysed against a reference shot under the same light, would tell.

## The confidence status metric is partial — only the FastSAM cue is scored

The status strip's `Confidence (run mean)` averages `Detection_Str.Segmenter_Score`, which only the FastSAM cue
supplies. An object found by background subtraction alone carries no score. The run mean is therefore over the scored
objects only, and reads `—` when none has a score; the frame's own confidence shows the coverage (e.g.
`87% over 5 of 9`). On the sets measured each object was scored, so the test frames do not exercise the partial case.

- **Impact:** the confidence figures describe the FastSAM-scored objects, not all of them; the coverage says how many.
- **Not fixed here:** routing each object through FastSAM would change detection to fill a status field (lower
  thresholds admit false detections; a second pass doubles the slowest stage). A later fix would give the background
  cue its own confidence.
- **Pinned by:** `test/UI/test_status_metrics.py::test_status_confidence_is_the_session_mean_over_scored_objects`,
  `::test_status_confidence_denominator_is_the_scored_count_not_the_total`,
  `::test_status_confidence_is_no_value_when_no_object_has_a_score`,
  `::test_frame_confidence_shows_coverage_when_partial_and_dash_when_none`.

## Gemma reads some through-holes as "a central green element"

Seen on the set removed in `eb00508` (recoverable from `eb00508^`); not looked for since. On a plate whose two
through-holes have dark rims, Gemma described "two circular cutouts each containing a central green element": the
table showing through the hole. The object prompt's sentence on green seen through a hole fixed the same misreading on
another part but not on this plate, and a sharper wording made it worse.

- **Impact:** a false detail in one object's text on dark-rimmed through-holes; the rest of the description was right.
- **Not fixed by tuning:** a prompt adjusted until one frame reads right is not a fix. Revisit with a different input,
  such as a crop whose table is masked to a neutral colour.

## The description and the measurement can disagree in the same panel — and the numbers are right

The describer guesses shape from the pixels of one small crop; the measurement computes it from the mask. On the set
removed in `eb00508` (recoverable from `eb00508^`; not looked for since), Gemma called two hex nuts a washer while the
measurement reported them across flats (`A/F 11.7 mm`, `A/F 11.5 mm`), and called a 48.1 × 46.9 mm plate rectangular.

- **Impact:** an object's text can misname its shape or kind while its size line is right. Trust the numbers.
- **Not fixed here:** prompt wording will not fix a small crop. The likely fix, not built, is to give the describer the
  measured shape and size.

## A killed run never gets its run-summary CSV row

The run-summary CSV (`log_<Hardware>.csv`) gets its row when the session logger closes, so a run that never closes
(killed, a power loss, a hard crash) has a complete `.txt` log but no row, and nothing adds one later. The daily station
event file had the same gap and closes it with an export ledger.

- **Impact:** the CSV under-counts runs and their time after an abnormal exit. The run's `.txt` log still records each
  event, so the time can be reconstructed by hand.
- **Not fixed here:** the same ledger could cover it: a row computed from a finished log, written at the next start.

## One full test run died with a fatal error, and nothing named it

On 2026-10-08 one full run of the suite ended without its summary, with only the last line of a fatal-error dump kept,
so the test, the thread and the kind of error are not known. The same tree then passed 13 full runs in a row, and it has
not recurred. The cause is not known. The suite now keeps a crash record, `test/crash_records/crash_record.txt`
(git-ignored), naming each test as it starts and holding faulthandler's dump of each thread on a fatal error; the next
run keeps a record that did not end cleanly as `crash_record_<time>.txt` (the newest ten), so the next crash names
itself (`test/integration/test_crash_record.py`).

## A hole drilled where the catalogue puts none is not reported

The hole check counts a positioned group's holes only near the positions the catalogue gives (within √2 × tolerance +
0.5 mm, mirrored to the four corners), which keeps a round mark of a hole's size elsewhere on the part out of the count.
A hole of the right size anywhere else is not counted, and nothing says it is there. Accepted on 2026-10-11.

- **Impact:** a part with its catalogue holes right and one more in an unexpected place reads OK.
- **Not fixed here:** reporting holes outside the positions needs round marks told apart from holes by something other
  than position, and no part with a misplaced hole is in the test set.
- **Pinned by:** `test/Vision/Utilities/test_holes.py::test_a_hole_at_every_corner_is_counted_and_a_round_mark_beside_one_is_not`.

## The stain check's colour band is this light's

The band (hue 5–30, saturation from 50, value from 40) was measured on the test set's fronts under the station's light
and the station file's fixed exposure, gain and white balance (read back and checked on each connect since 2026-10-13).
A warmer light, another white balance or a surface reflecting the table's green differently moves the plate's colours,
and nothing checks that the band still fits.

- **Impact:** under another light a clean part could show band pixels (a false NOK), or a stain could fall outside the
  band (a stain passed, the error that matters).
- **Not fixed here:** checking the band needs frames under another light;
  the camera's settings are fixed and read back since `cd28bb2`.
- **Pinned by:** `test/Vision/Utilities/test_stain.py` (the band as shipped), and the pipeline's verdicts on the test set
  (slow).

## The describer guard reads words, so a paraphrase can pass and a right sentence can go

`Reporting.Guard_Description` drops a describer's sentence that holds a number or contradicts the hole or stain check, by
reading words: each mention of a hole kind or a stain in its own clause with the words around it (a negation, a count,
"missing", "would be"), and a sentence naming the checks ("automatic", "confirmed", "verified", "detected"). On the
mounting plate's 10 capture frames (2026-10-15, 15 judged parts) it changed exactly the four stored descriptions that
contradicted a check and the one naming the check; live, with the no-checks rule in the prompt, it had nothing to do.

- **Impact:** a contradiction worded unlike those measured can reach the panel (a hole kind it has no word for, such as
  "openings"; a negation more than four words before its noun; "no stains on the front area"), and a right sentence
  using a pattern's words can be dropped with its right clauses ("no scratches were detected"). Each intervention is in
  the log with the describer's full text. The verdict, the state and the reasons never come from the describer.
- **Not fixed here:** a model judging the describer's text would be one more model to trust; the word lists grow with
  what is measured.
- **Pinned by:** `test/Reporting/test_core.py::test_the_guard_drops_numbers_and_what_contradicts_a_check`,
  `::test_the_guard_holds_each_mention_to_its_check_in_both_directions`,
  `::test_the_guard_drops_a_sentence_referring_to_the_checks`.

## A missing hole is not marked when the part shows nothing to place it by

A hole expected and not found is marked dashed where a hole found puts it: at the pitch from a through-hole, under a
countersink, around a through-hole. The mounting plate's through-holes sit by one long edge, so with no hole of the side
found, the outline cannot tell which end they belong at, and none is marked (seen on capture `20261015-143622_s1`,
object 3).

- **Impact:** a plate missing all its holes shows no hole marks; its reason ("Both through-holes are missing."), its log
  lines and its note still say so.
- **Not fixed here:** DINOv2's best turn picked the wrong end on 3 of 21 plates with each hole in view, so a mark at a
  guessed end may be wrong. A gate on its margin (0.025)
  would have placed 6 of the 21, all correctly, and was not built: one table, one light, and 0.003 between the worst
  wrong margin and the next right one.
- **Pinned by:** `test/Vision/Utilities/test_holes.py::test_a_side_with_no_hole_found_places_none_since_its_end_cannot_be_told`,
  `test/Reporting/test_core.py::test_missing_holes_not_marked_are_named_in_the_note`.

## Sizes beyond 46.4 mm from the frame centre are unverified

The size checks were verified on real frames only out to 46.4 mm from the frame centre
(`Vision.Utilities.Classify.CONST_VERIFIED_RADIUS_MM`: the farthest judged mounting plate of the test set, 46.32 mm,
`Image_072`). Farther out the side-wall term predicts up to about 1 mm more ([SPEC > Known limitations](SPEC.md#known-limitations)),
beyond the plates' 0.73 mm margin to the tolerance. A part there is judged on its size exactly as one at the centre: the
radius is evidence for the log, not a branch of the rule. Plates 50–66.6 mm out read 59.97–61.27 × 39.89–41.31 mm on
2026-10-15, and two plate judgements 53.4 and 57.3 mm out read within tolerance at the station on 2026-10-29; none was
calipered, so the radius is not widened.

- **Impact:** an OK or a NOK on size beyond 46.4 mm rests on a size not verified there. Scene Understanding does not say
  so; the session log's verdict line
  gives the distance and the radius.
- **Not fixed here:** only captures on the station can verify it: mounting plates in the corners and along the edges of
  the view. If they read within tolerance there,
  `CONST_VERIFIED_RADIUS_MM` widens to them.
- **Pinned by:** `test/Vision/Utilities/test_classify.py::test_the_verdict_does_not_depend_on_where_the_part_lies`,
  `test/Reporting/test_core.py::test_a_size_checked_outside_the_verified_zone_is_noted_in_the_log_only`.

## The inspection area's insets rest on plates measured mostly by the right edge

A catalogue mode judges only inside the station's inspection area: the frame inset by 10 mm from its top and bottom and
13 mm from its left and right (`Inspection_Area` in the station file).
The insets were chosen from 72 fully visible mounting plates as the smallest at which each size,
hole-position and hole-diameter error of the plates inside stays within half its tolerance.

- **The edges are unevenly covered.** Of the 40 plates inside the area, the closest came within 0.1 mm of the top,
  0.7 mm of the right and 2.4 mm of the left, but only 4.7 mm of the bottom. Most plates by the edges, and each one that
  set the short-edge inset, lay by the right edge. At the station on 2026-10-29 one plate came 2.3 mm inside the bottom
  edge; the left edge and the corners are still unmeasured, and those plates were not calipered.
- **The corners are not measured.** A plate wholly inside the area can lie up to about 67 mm from the frame centre; the
  farthest judged inside lies 58.4 mm out.
- **One plate exceeds the criterion wherever the area lies:** `Image_083`'s plate, 14.2 mm from the centre, reads
  0.77 mm off its nominal size against the 0.75 mm half tolerance, so it was set aside; the plates are not calipered
  (SPEC > Known limitations), so part of that may be the plate itself.
- **Plates past the area are not judged.** By the right edge they are Warnings with no check run. Measured there, the
  stains and holes were found to 80.9 mm out, but the outlines read up to 1.17 mm off nominal from 57 mm out.
- **The area is narrow upright.** It is about 101 mm high, so a plate standing with its long side vertical can move only
  about ±20 mm from the frame's middle row and still be judged (±30 mm lying across). The area is drawn on the empty
  view, the scanned frame and the live preview, so the operator can place the part inside it first.
- **Impact:** a part by the left or bottom edge, or in a corner, is judged on errors measured mostly by the right edge and
  the top; the area may be larger, or need to be smaller, there. An upright plate a little off the middle row is a
  Warning, to be moved and scanned again.
- **Not fixed here:** only captures on the station can tell (plates along
  the left and bottom edges and in the four corners, and parts cut by the frame's border).
- **Pinned by:** `test/Vision/Utilities/test_classify.py::test_only_an_object_wholly_inside_the_inspection_area_is_judged`,
  `test/integration/test_edge_of_view.py`, `test/integration/test_pipeline.py::test_each_frame_gets_its_expected_verdicts`.

## The live preview runs at about 3.7 frames a second, set by the computer's Ethernet adapter

PREVIEW shows the table at about 3.7 frames a second (3.67 measured in the window on 2026-10-16), so a hand placing a
part moves in visible steps. The limit is the link, not the camera (51 fps): the camera's throughput is held to 10 MB/s
(`Camera.Basler.CONST_THROUGHPUT_LIMIT`), the measured ceiling of the Ethernet adapter it is plugged into, and a full
1920 × 1200 frame is 2.3 MB.

- **Impact:** the preview is usable for placing parts, not smooth; SCAN from the preview first waits for the frame in
  flight (0.786 s from the press to the frame, against 0.590 s without the preview). Nothing measured or judged depends
  on it.
- **Not fixed here:** a faster preview on this link would need a camera setting that differs between preview and scan
  (binning, a smaller window), which was ruled out: the preview would show something other than the frame the scan
  takes. A dedicated gigabit network card for the camera would allow a faster preview with no setting changed.
- **Pinned by:** nothing automated; `Example/Camera/preview_check.py` measures it.

## A plate cut more than any measured could read as a foreign object

Outside the inspection area, an object the verdict rule does not identify resembles the part only when its similarity
is at least 0.657, its mean saturation at most 76.3 and its visible extent at most 73.6 mm
(`Classify.Resembles_Part`). The most cut plate measured, a stained front
88.5 mm out with a corner off the right border, scored 0.668. A plate with less of it in view was never measured and may
score under the threshold.

- **Impact:** such a plate would read `Warning – Foreign object.` ("remove it from the surface") instead of
  `Warning – Outside area.` ("move it fully inside the area"), and be recorded with `warning_kind` `foreign`. It is a
  Warning, drawn in the same amber, either way, and the operator moves it either way.
- **Not fixed here:** only captures can tell: plates cut by each border with less and less of them in view, and foreign
  objects of the plate's grey.
- **Pinned by:** `test/Vision/Utilities/test_classify.py::test_an_object_resembles_the_part_by_the_rule_or_outside_by_every_position_free_cue`.

## A stained front by the edge of the view reads "does not look like the part"

DINOv2's similarity of the stained front to the front reference falls with its distance from the frame centre:
0.81–0.89 within 30 mm, 0.67–0.78 at 50–67 mm, mostly below `Identify_Similarity` (0.75). There the plate is NOK for its
stains, with its side and holes right, and its reason adds "It has the part's outline but does not look like the part".
The rule is deliberate: an object of the part's shape that does not look like it is NOK. The drop is the
stains', not the position's: clean fronts 58–62.5 mm out score 0.83–0.87 and read OK without the clause, while a stained
front at the same place scores 0.69. Most such plates lie outside the inspection area and are Warnings, whose reason
does not carry the clause; inside it a stained front still scores down to 0.73 (52 mm out) and gets it.

- **Impact:** the verdict is right. The clause, written for a foreign object, says the stains make the front look unlike
  its clean reference. A clean front by the edge does not get it.
- **Not fixed here:** nothing to fix in the identification; a separate wording for a judged part with stains found could
  follow.
- **Pinned by:** nothing.
