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
