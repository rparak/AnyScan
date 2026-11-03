# Features

The tracker: what is open, and what each revision delivered with its owner's acceptance. Format:
project-style-rpx `references/markdown.md` > *FEATURES.md*. A revision's long record lives here while it is open;
once accepted it collapses to its row in *Done*, and what is still true moves to the SPEC, design-decisions or
KNOWN_ISSUES.

## Open

- **R4 - README, licences, media** (owner, 2026-10-29), written with readme-writer: the README's third-party section
  from the inventory in `.claude/skills/readme-writer/references/project.md` > *Third-party components*, the media,
  the commands in the one spelling `.venv/bin/python`, and `preview_check.py` in the layout. The owner's answers to
  Part A (2026-11-03):
  - The README is held to its sources: every finding of the claims audit is fixed (README:294 among them), and a
    *Validation* section states what ran on real hardware and what did not.
  - Defect detection is split in SPEC: a catalogued item's defined defects are built, open-set defect detection on
    any part is not. The project poster is linked only if every claim on it holds against SPEC.
  - Media: a station photo (cropped), the analysis animation (`Example/UI/analysis_animation.py`, regenerated, never
    edited), two Live screenshots collapsed; `images/anyscan-poster-image.png` removed.
  - One command spelling: no `activate` step, the tests as `.venv/bin/python -m pytest`.
  - The approval to publish stays in one place, design-decisions (*The owner's statements of 2026-10-29*); there is no
    KNOWN_ISSUES entry. `CITATION.cff` moves to R5.
- **R5 - Release v1.0** (owner, 2026-10-29): the v1.0 tag moved to the release commit (owner-approved), the
  publication of the repository, and a rollback procedure for the station. Also `CITATION.cff` (owner, 2026-11-03):
  title, the authors as in README > Authors, JIC Smart Factory, MIT, the repository URL, the version and release
  date, with a test; whether the three contributors are listed as authors, their affiliations and any ORCID or
  e-mail are the owner's to give. `transformers` and `fonttools` keep their `>=` floors, as `requirements.txt` does
  throughout: an `==` pin changes what installs on Linux and needs a Linux check first (project-style-rpx
  `project.md` > *Installer*, open item) (owner, 2026-11-03).
- **Root-layout check on station SF4** (owner, 2026-11-03): `test/integration/test_root_layout.py`'s allowlist of
  ignored root entries and its untracked-entry check ran on macOS only. SF4 is not checked before the release. It is
  answered by `.venv/bin/python -m pytest test/integration/test_root_layout.py` on SF4.

## Done

| Revision | Delivered | Commits | Accepted |
|---|---|---|---|
| R1 | Skills in the repository: six skills in `.claude/skills/` with generic `SKILL.md` files and AnyScan's `references/project.md` layers, their LICENSE, the rewritten skills test, the records and the third-party inventory; the personal copies excluded by sparse checkout (design-decisions, *The skills ship in the repository*). Full record, with the owner's answers Q1-Q9 of 2026-10-29: `git show c454237:.claude/project-docs/FEATURES.md` | `6820f20`…`c454237`, closed by the commit that adds this row | accepted by the owner 2026-10-29 |
| R2 | The support-chat brief: support-brief's project layer, `.claude/project-docs/SUPPORT_CHAT.md` (its first run, checked against `1c9aade`) and `test/integration/test_support_chat.py`; the records of the use at station SF4 on 2026-10-29 and its offline v1.0 replay. The owner's statements of 2026-10-29: design-decisions, *The owner's statements of 2026-10-29*. Full record: `git show 6d6f068:.claude/project-docs/FEATURES.md` | `a62ed77`, `6d6f068`, closed by the commit that adds this row | accepted by the owner 2026-10-29 |
| R3 | Cleanup: the root-layout test (untracked and ignored root entries, case-only paths, all six records), `transformers` and `fonttools` declared, every file a test opens closed and a leak made an error (`pytest.ini`), the owner's statements of 2026-10-29 in design-decisions, the brief refreshed. Full record: `git show 85e8840:.claude/project-docs/FEATURES.md` | `f9ae320`…`85e8840`, closed by the commit that adds this row | accepted by the owner 2026-11-03 |
