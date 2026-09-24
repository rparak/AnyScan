# UI design — how the interface looks

`pyqt.md` covers how the UI code is written; this page covers how the interface looks. Each rule
states the practice, what enforces it (✅ a test, 📄 documentation only), and where the reasoning
lives in `docs/design-decisions.md` (DD). Everything here is something the code already does;
practices followed inconsistently are under **Unsettled**.

## Colour comes from the theme, never from a literal ✅

- Every colour is a token in `src/Parameters/Theme.py` — Qt-free, so the application and the vision
  renderer (the exported annotated image and label mask) share one palette. UI code reaches the
  tokens through `UI/Utilities/Style.py` and never names a colour by value: not a hex string (in a
  stylesheet or elsewhere), not a `QColor` built from numbers.
- A token at an opacity is `Style.Token_Color(token, alpha)`, with the alpha a named theme constant
  (`CONST_BUSY_SCRIM_ALPHA`) — never the token's value copied into a `QColor(r, g, b, a)`. That copy
  is how drift starts: the busy overlay once filled with `QColor(43, 36, 85, 158)`, the ink token's
  value at another opacity, which nothing would have kept in step with the ink.
- A new colour is a new token, commented with what it is for.
- ✅ `test/UI/test_colour_tokens.py` scans every UI module (except `Style.py`) with the Python tokenizer
  for a hex colour in a string or a numeric `QColor(`.

## A verdict colour never changes; its foreground carries legibility ✅

- The verdict colours are fixed tokens: OK `#6C63B5`, NOK `#ff005c` — the brand magenta, kept as the
  fail marker because it reads as one at a glance (DD *`#ff005c` is the fail marker*). A
  detect-only run draws one neutral colour, distinct in hue from OK (DD *Classification is a
  per-configuration switch*).
- The box, the chip and the mask outline are drawn in the verdict colour itself, unshifted, on any
  background. A colour is never lightened, darkened or rotated to gain contrast against a frame.
- Legibility comes from the foreground: the chip's numeral takes whichever theme foreground (white or
  ink) contrasts with the chip. There is no casing or outline around the chip — a chip in one colour
  with a contrasting numeral reads as one thing; an added casing read as two (`Vision/Utilities/
  Annotate.py`, `__Draw_Index_Chip`).
- The label-mask fill is a tint that keeps its box's hue (within 5°, at ≥ 40 % of its chroma), so the
  silhouette and its outline read as one object (DD *The label mask is black ground, tinted fill,
  verdict contour*).
- ✅ `test/Vision/Utilities/test_annotate.py::test_annotated_is_box_and_numeral_only_in_the_unshifted_verdict_colour`,
  `test/Parameters/test_theme.py::test_label_mask_fill_is_a_visible_tint_of_its_box`,
  `::test_verdict_colour_comes_from_the_one_constant`.

## Severity is never carried by colour alone ✅

- A severity level has a word and a weight as well as a colour: the Log's level field reads INFO /
  WARNING / ERROR, and its weight ramps INFO < WARNING < ERROR from one shared ramp
  (`Style.Log_Level_Weight`), which the confidence numbers at that severity use too — so a reader who
  cannot tell the colours apart still reads the level. It matters in practice: the WARNING amber and
  ERROR red collapse to nearly one colour under deuteranopia (ΔE ~8, measured; `Style.py`).
- Detect-only versus classified is carried by wording as well as colour: a detect-only run shows no
  OK / NOK words at all, only detected objects.
- ✅ `test/UI/test_log_view.py::test_level_field_weight_ramps_with_severity`,
  `test/Vision/Utilities/test_annotate.py::test_verdict_colored_false_draws_one_neutral_colour_not_verdicts`.

## Controls: every state clears 4.5:1, measured; disabled speaks through its fill ✅

- Every enabled state of every control — rest, hover, pressed, selected, focus — keeps its label at
  ≥ 4.5:1 against its fill, and a stylesheet rule for a state names both its fill and its label
  (DD *Control stylesheets: every state rule names its fill and its label*).
- The contrast is measured from rendered pixels — the widget rendered at 2×, the label's highest-
  contrast pixel against the fill — not read back from the stylesheet, because Qt resolved one
  correct-looking stylesheet to 1.08:1 on screen.
- A disabled control signals through its fill (and outline), not by making its label vanish. It is
  exempt from the 4.5:1 floor — its lower contrast is what says "not available" — but it must stay
  distinguishable from its enabled state, and disabled-hover must look like disabled.
- ✅ `test/UI/test_control_contrast.py` (`test_no_enabled_state_falls_below_the_text_contrast_floor`,
  `test_disabled_states_are_exempt_but_distinguishable_from_enabled`, `test_disabled_hover_looks_like_disabled`,
  `test_every_state_of_every_control_was_measured`, and a self-check that hover really rendered).

## Content type comes from the scale; one content, one size ✅ (content) 📄 (chrome)

- **Content typography** — text the analysis produces, read as the result: the Scene Understanding
  reading (background paragraph, object labels, confidences, descriptions), History's info panel, the
  Log's rows — is sized by named tokens on the modular scale (`CONST_TYPE_SCALE` in `Style.py`;
  `CONST_TYPE_OBJECT_LABEL`, `CONST_TYPE_INFO_BODY`, `CONST_TYPE_LOG` …), never a literal size. A size
  change moves a token to another step.
- **Within a view, one content has one size**: the background paragraph and the object descriptions
  share one, and the hierarchy runs heading > label > body > meta. Across views it deliberately does
  not: Live (glanced at across a workbench) and History (read up close) have separate token sets, so a
  description is 12.5 pt in one and 10.5 pt in the other, and tuning one cannot move the other.
- **Chrome** — the frame around the content: button and pill labels, status-strip labels and values,
  card metadata, captions, empty-state and status messages, overlays — is sized per widget (literal
  sizes, or raw steps of the scale). It is not held to the scale; see Unsettled.
- **Which side a new widget falls on:** if the text is part of what the analysis says (a reading, a
  record, a description), it is content and takes a named token; if it labels, frames or operates
  the UI, it is chrome.
- The reasoning: DD *Type: a scale for content, chosen sizes for chrome*.
- ✅ `test/UI/test_history.py::test_info_panel_type_hierarchy_heading_is_largest`.

## A colour relationship is held by code or a test, never by a comment ✅

- Where two colours must keep a relationship — a mask fill against its box, against white, against
  the black ground — the relationship is enforced, not merely noted:
  - **by derivation**, failing loudly: the neutral mask pair is computed from the neutral box at
    import (`Theme.Neutral_Mask_Colors`), and raises a `ValueError` naming the violated floors when no
    valid pair exists or rounding breaks one;
  - **or by a test on the floors**, for colours tuned by eye: the verdict fills are fixed tokens,
    and `test_theme.py` holds them to the same floors (ΔE from the box and from white, 4.5:1 on the
    ground, the hue within 5°).
- ✅ `test/Parameters/test_theme.py::test_neutral_mask_pair_ignores_box_lightness_and_fails_loudly_on_floors`,
  `::test_label_mask_fill_is_a_visible_tint_of_its_box`.

## Unsettled

- **Chrome type sizes.** 32 chrome `Font(...)` calls use literal sizes, most of them off the scale
  (7.5, 8, 8.5, 9, 10, 11, 12, 13.5). The rule above covers content only.
- **One content label outside the scale:** the Scene Understanding card's note (`UI/Core.py`,
  `__reading_note`, the composer's note under the objects) is content set at a literal 11.5 (a scale
  step, but not a named token).
- **Derivation or test.** Both hold colour relationships today (the neutral pair derived, the verdict
  fills tested); there is no rule for which a new pair should use.
- **The label mask's black ground** is `Annotate.CONST_ANNOTATE_MASK_GROUND` — by a documented choice
  not a theme surface colour — while `Theme.Ground_Contrast` separately assumes `'#000000'`: one colour
  with two sources.
