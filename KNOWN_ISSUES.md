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
