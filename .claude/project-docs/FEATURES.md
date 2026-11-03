# Features

The tracker: what is open, and what each revision delivered with its owner's acceptance. Format:
project-style-rpx `references/markdown.md` > *FEATURES.md*. A revision's long record lives here while it is open;
once accepted it collapses to its row in *Done*, and what is still true moves to the SPEC, design-decisions or
KNOWN_ISSUES.

## Open

- **R5 - Release v1.0** (owner, 2026-10-29): the v1.0 tag moved to the release commit (owner-approved), the
  publication of the repository, and a rollback procedure for the station. `transformers` and `fonttools` keep their
  `>=` floors, as `requirements.txt` does throughout: an `==` pin changes what installs on Linux and needs a Linux
  check first (project-style-rpx `project.md` > *Installer*, open item) (owner, 2026-11-03). The owner's answers to
  Part A (2026-11-03):
  - The poster is the owner's re-export with the six corrections and "AI models"; every claim on it holds against
    SPEC, its metadata is stripped and the README links it again. A raster export and the gap above its NOK box are
    accepted; its EU disclaimer is not changed.
  - The publication sweep over the tree and every blob in history (gitleaks 8.30.1 and a sweep of all 3,227 blobs)
    found no secret, no image metadata and no person. In the tree: the station's path in project-style-rpx
    `project.md`, reworded, and two private camera addresses, now in the documentation range `192.0.2.x`. In history
    only: two poster versions with the GT fonts embedded and the station's path; history is not rewritten in R5, and
    the owner decides on the GT licence before publication.
  - `CITATION.cff`: the four people of README > Authors as authors, each of JIC Smart Factory, no ORCID or e-mail,
    version 1.0 and the release commit's date, held by `test/integration/test_citation.py`.
  - The README: a gallery in *Run* (Trends, History and a NOK plate beside an OK one visible, four more collapsed),
    "Back to an earlier release" in *Setup*, the shared stages' table and the rig's validation collapsed, within 250
    visible lines.
  - The release notes, the GitHub description and the topics are drafted outside the repository, for the owner.
- **Root-layout check on station SF4** (owner, 2026-11-03): `test/integration/test_root_layout.py`'s allowlist of
  ignored root entries and its untracked-entry check ran on macOS only. SF4 is not checked before the release. It is
  answered by `.venv/bin/python -m pytest test/integration/test_root_layout.py` on SF4.

## Done

| Revision | Delivered | Commits | Accepted |
|---|---|---|---|
| R1 | Skills in the repository: six skills in `.claude/skills/` with generic `SKILL.md` files and AnyScan's `references/project.md` layers, their LICENSE, the rewritten skills test, the records and the third-party inventory; the personal copies excluded by sparse checkout (design-decisions, *The skills ship in the repository*). Full record, with the owner's answers Q1-Q9 of 2026-10-29: `git show c454237:.claude/project-docs/FEATURES.md` | `6820f20`…`c454237`, closed by the commit that adds this row | accepted by the owner 2026-10-29 |
| R2 | The support-chat brief: support-brief's project layer, `.claude/project-docs/SUPPORT_CHAT.md` (its first run, checked against `1c9aade`) and `test/integration/test_support_chat.py`; the records of the use at station SF4 on 2026-10-29 and its offline v1.0 replay. The owner's statements of 2026-10-29: design-decisions, *The owner's statements of 2026-10-29*. Full record: `git show 6d6f068:.claude/project-docs/FEATURES.md` | `a62ed77`, `6d6f068`, closed by the commit that adds this row | accepted by the owner 2026-10-29 |
| R3 | Cleanup: the root-layout test (untracked and ignored root entries, case-only paths, all six records), `transformers` and `fonttools` declared, every file a test opens closed and a leak made an error (`pytest.ini`), the owner's statements of 2026-10-29 in design-decisions, the brief refreshed. Full record: `git show 85e8840:.claude/project-docs/FEATURES.md` | `f9ae320`…`85e8840`, closed by the commit that adds this row | accepted by the owner 2026-11-03 |
| R4 | README, licences, media: the README held to its sources with a *Validation* section, defect detection split in SPEC (a catalogued item's defined defects built, open-set not), the licence note and the third-party table, the station photo, the analysis animation (`Example/UI/analysis_animation.py`) and two Live screenshots, one command spelling `.venv/bin/python`, the brief refreshed. Full record: `git show c8f90a3:.claude/project-docs/FEATURES.md` | `61b9cb4`…`c8f90a3`, closed by the commit that adds this row | accepted by the owner 2026-11-03 |
