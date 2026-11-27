# Changelog

All notable changes to AnyScan. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); each
version is a tag in this repository.

## [1.1] - Unreleased

AnyScan works as in 1.0: the application, its models, its configuration and its records are unchanged.

### Added

- `docs/`: the [specification](docs/SPEC.md) with its [known limitations](docs/SPEC.md#known-limitations) and the
  [known issues](docs/KNOWN_ISSUES.md), linked from README > Documentation.
- The AnyScan video: the station, each step and a plate judged NOK, linked from the README's first figure.
- This changelog.

### Changed

- The README rewritten: a headline with the AnyScan and JIC Smart Factory logos, a first screen that says what
  AnyScan does, and sections in the order a new user needs them.
- Every README figure is a still that explains one thing: analyses recorded at the station, the operator's reading,
  the station, and generated figures (the architecture, the pipeline, the catalogue item) in light and dark
  versions. The models are a table generated from `install.sh`.
- The architecture figure follows the station's order (find, measure, judge, describe, record) and embeds its
  font.
- Installer and error messages name the README's renamed sections.

### Removed

- The README's animations and screenshot gallery, and `Example/UI/analysis_animation.py`, which recorded them.
- The development tooling for the coding assistant (`.claude/`, `CLAUDE.md`) and the tests that checked it.

## [1.0] - 2026-11-03

First public release.

### Added

- Detect-only mode: the objects on the table found, measured in millimetres and described in words.
- Catalogue mode, shipped for a mounting plate: the part recognised and checked (outline, holes, stains), with a
  verdict of OK, NOK or Warning and its reason.
- Three local models: FastSAM-x (finding), Gemma 4 E4B on MLX (describing), DINOv2 base (recognising).
- The PyQt5 window with the Live, Trends, History and Log views, and the Configuration dialog.
- Records: capture sets, the session log, the run summary and the daily station events.
- `install.sh` for Apple-silicon macOS and Linux with an NVIDIA GPU; calibration and reference tools in
  `Example/`.
- `CITATION.cff`.

### Removed

- The project poster, from the files and from the repository's history: its PDFs embedded commercial fonts whose
  licence does not expressly allow public distribution. The history was rewritten and force-pushed on 2026-11-03,
  so every commit from 2026-10-03 on, when the poster was first committed, has a new hash. The repository was not
  deleted, and no GitHub Support request was made.

[1.1]: https://github.com/rparak/AnyScan/compare/v1.0...v1.1
[1.0]: https://github.com/rparak/AnyScan/releases/tag/v1.0
