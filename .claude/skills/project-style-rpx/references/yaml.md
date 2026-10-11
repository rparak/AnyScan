# YAML — configuration, station, calibration and catalogue files

Three kinds under `Configuration/`: a mode file, `Config_<Hardware>_Mode_<Mode>.yaml` (one per mode); a
station file, `Station_<Hardware>.yaml` (one per camera: the camera, its acquisition settings and window,
and the background reference — shared by its modes, never overridden by one); and a calibration,
`Calibration_<Hardware>.yaml` (one per camera, shared by its modes). A catalogue mode also reads a catalogue
item, `Data/Catalogue/<item>/<item>.yaml`, by the same rules.
✅ = enforced by `Configuration.Core.Load_Configuration` / `Write_Calibration`; 📄 = documentation only.

## One reader, one writer ✅ (in practice) 📄 (as a rule)

`Configuration/Core.py` is the only code that parses these files (`Load_Configuration`), and the only
code that writes a calibration (`Write_Calibration`, called by `calibrate.py`). No module opens the
YAML for itself; every setting reaches its user through `Configuration_Str`. The writer refuses to
overwrite a file holding any key it does not own, so content someone added is never regenerated away.

## Shape 📄

- A header block between `## ===…=== ##` rules, in `#   Description:`-style sections: what the file
  is, who reads and writes it, the file-name convention, what REQUIRED means, the hardware setup.
- Keys are `Pascal_Snake_Case` (`Background_Reference`, `Exposure_Time`, `Balance_Ratios`), nested
  by stage or concern (`Segmentation.Background.*`, `Segmentation.Fusion.*`).
- Every top-level section is preceded by a comment saying what it covers ("Stages 1-3: FastSAM
  instance segmentation, the background difference, and their fusion.").
- Every field is preceded by a comment saying what it does and, where it matters, why its value is
  what it is. A comment may cover a group of consecutive fields.
- A required field says `REQUIRED.` (a group: `REQUIRED, both.`); an optional field states its
  default — `Default: 0.20`, or for a group `Defaults: 0.4 and 0.9`. Every field in the shipped mode
  file does one or the other, and a documented default must equal the code's — both enforced by
  `test/Configuration/test_core.py::test_every_documented_default_in_the_shipped_mode_file_is_the_code_default`.
- Units in brackets in the comment: `[px]`, `[us]`, `[%]`.
- Text the model receives (the prompts) lives here as data, with the reasoning behind the wording in
  the comment above it — iterated here, never in code.
- The mode file's section order is `Hardware, General, Identity, Confidence, Segmentation,
  Description, Evaluation`, with a catalogue mode's `Catalogue` block after `Identity`. The three mode
  files share it because the catalogue modes were copied from the first; it is their order, not a rule
  anything checks. The station file's is `Hardware, Camera, Background`.
  The calibration's order is fixed by its writer.

## Loading ✅

- A REQUIRED field that is missing fails the load, naming the field.
- A present value that is invalid fails the load; it never falls back to a default.
- An optional field that is absent takes its documented default (the `*_Str` field default), and
  the load notes it.
- Every problem is collected, then the load fails once, listing all of them.
- A key no setting reads is reported as a WARNING (`unrecognised key … is ignored (misspelt?)`).
- A **harness-only** field (the `Evaluation` block: `Evaluation.Frames`, read by `analyze.py`, never by
  the application) is optional, and the loader only resolves it: data the application never touches
  must not stop it loading. The harness that reads it checks it.
- What depends on the camera's sensor window is checked against it at load: the background
  reference's size and its provenance sidecar, and the window the calibration was solved at.

## A field must be read by something that can change behaviour 📄

A field that reads as configurable, is accepted, and cannot take effect is worse than a missing one:
someone concludes the setting is in force when it is not. So a field exists only if some code reads it
**and** a different value changes what that code does; otherwise it is removed with the code path.

**The loader cannot enforce this.** It catches unknown keys, not known ones that nothing uses. All
three instances so far were found by hand:

- A hardware-id constant in `Logger/Core.py` that looked like the setting for which camera's run
  summary is written, while the configuration's file name already said it — two sources that could
  disagree silently (docs/design-decisions.md, *The run-summary CSV is named after the loaded
  configuration*).
- `Camera.Resolution` — loaded into `Camera_Configuration_Str`, never read; the camera ran at whatever
  it last remembered (fixed: the window is now set on connect and read back).
- `Segmentation.Mode` — read, but its `box` value could not take effect (no region prompts were ever
  passed); removed, with the box path and the parameters that only served it.

**One dated exception** (2026-10-11): a catalogue item's descriptions (`Description`,
`Measurement_Rules`, each side's `Description`, `Defects`) are loaded and validated but read by nothing
until the describer uses them in phase D of the catalogue mode — the owner chose validated fields over
comments so the item file is the one tracked source for the part. The exception ends when phase D reads
them; a field phase D does not read is removed (docs/design-decisions.md, *A catalogue item is the single
tracked source…*). It is not a precedent for any other field.

See references/structure.md (*No parameter or field that cannot take effect*) for the same rule in code.

## Machine-specific values stay out of the repository 📄

A committed file holds values that are right on every machine that clones it: paths relative to the
repository root, the rig's hardware as a person names it. A value that is true on one machine only — a
station's absolute path, a host name, a mount point — lives in that machine's local copy of the mode
file, outside the repository, never in the shipped one. The shipped file keeps a repository-relative
value that works on a fresh clone.

Instance: `8d8a13c` put the station's `/home/sf4/sf4/events/` into the shipped
`General.Station_Events.Directory`. The loader requires that directory to exist, so everywhere else the
shipped configuration stopped loading and 17 test modules failed before any test ran. `9d44669` put back
`logger/Station_Events`; README > Configuration says how a station keeps its own copy (same file name,
the calibration symlinked beside it, started with `--config`).

Only a **required** path is caught, and only indirectly: the test suite loads the shipped file, so a path
that does not exist on the machine running the tests fails them. An optional or non-path value specific
to one machine passes every check.
