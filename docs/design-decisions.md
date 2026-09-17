# Design decisions

The reasoning behind the non-obvious choices in the vision port, so the next person does
not undo them. Each entry states the decision, the reason, and what would justify
revisiting it. This is the counterpart to [`KNOWN_ISSUES.md`](../KNOWN_ISSUES.md): that
file records latent quirks left unchanged; this file records deliberate choices whose
motivation is not visible in the code. A change that contradicts one of these should cite
why the reason no longer holds.

## The label mask is black ground, white fill, verdict contour

The exported mask paints a black ground, fills each object white, and outlines it in its
verdict colour with a dark numeral on the fill. Black ground keeps every silhouette edge
sharp (nothing bleeds into a coloured background); white fill plus a verdict-coloured
contour reads the pass/fail at a glance without staining the whole shape, and a dark
numeral stays legible on the white. The per-object colour that used to fill the mask is
not gone — it is the **`index` diagnostic mode** (`Annotate.CONST_ANNOTATE_MASK_FILL =
'index'`), the one switch that fills each object in its own `Index_Color` to reveal a
merge or an over-segmentation. **Revisit if** the operator-facing mask needs to encode
something other than verdict (e.g. per-class colour), in which case add a mode rather than
overloading the default.
Commit `78311b4`; tests `test/Vision/Utilities/test_annotate.py::test_label_mask_is_white_fill_verdict_contour_dark_numeral`, `::test_index_fill_mask_mode_is_reachable_by_one_constant`.

## `#ff005c` is the fail marker and must not return to the object palette

The EDIH-DIGIMAT brand magenta `#ff005c` reads as a fail marker at a glance, so it was
removed from the object palette (an object numbered in it would silently look "bad") and
is now the **NOK** verdict colour, which is exactly what that quality makes it good for.
The object palette (`CONST_INDEX_COLORS`) and every generated variant are guarded against
the whole red-through-magenta wedge at load time. **Revisit only** if the verdict scheme
itself changes; do not "restore" the magenta to the object palette or swap it for a calmer
red, because its fail-lookalike quality is the point.
Commits `78311b4`, `3494ba3`; tests `test/Parameters/test_theme.py::test_verdict_colour_comes_from_the_one_constant`, `::test_no_index_colour_is_a_reserved_verdict_hue`.

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
