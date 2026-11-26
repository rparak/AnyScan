# Features

The tracker: what is open, and what each revision delivered with its owner's acceptance. Format:
project-style-rpx `references/markdown.md` > *FEATURES.md*. A revision's long record lives here while it is open;
once accepted it collapses to its row in *Done*, and what is still true moves to the SPEC, design-decisions or
KNOWN_ISSUES.

## Open

- **C - The v1.1 media** (owner, Phase C, 2026-11-26), on branch `c-media`: main repaired after the README web edits
  (the three limitations moved to SPEC > *Known limitations*, every citation repointed, Figure 4 a screen recording);
  `Example/UI/readme_diagrams.py` and its test (the pipeline and the models, light and dark, through `<picture>`);
  the README's media (the video poster, the History animation, both diagrams, the figures renumbered). The 70 s video,
  the LinkedIn cut and the four thumbnails are built outside the repository (`~/Desktop/AnyScan-Video/`) and never
  committed (design-decisions, *The README's media come from the station's own recordings*). Awaiting the owner's
  acceptance.
- **README v11** (owner, 2026-11-26, before Phase D), on branch `readme-v11`: the README restructured (headline,
  poster, what AnyScan does, architecture, catalogue mode, the station, quick start, requirements and platforms,
  configuration, records, development, documentation, authors, licence, citation, funding; 250 visible lines), every
  figure a still (no animation), Figure 1 in the station's order with Public Sans embedded and without the funding
  band, the headline, the catalogue item card and the models table generated, the recorded stills built outside the
  repository; the headings renamed with every citation (design-decisions, *The README shows stills only, each
  explaining one thing*). Phase D adds the `docs/` links, the limitations included. Awaiting the owner's acceptance.
- **Figure 5's link** (owner, 2026-11-26): the video poster links to the owner's YouTube channel
  (`https://www.youtube.com/@RomanParak/videos`) until the video is published; then a small commit changes it to the
  video's own URL.
- **R6 - The poster dropped, history rewritten** (owner, 2026-11-03): the poster's PDFs embedded the GT fonts, and
  JIC Smart Factory's Desktop EULA does not expressly grant publishing a PDF with them embedded (6.4). The poster is
  dropped, and every version left history on 2026-11-03 (`images/anyscan-poster.pdf`, `images/AnyScan_poster.pdf`,
  `images/anyscan-poster-image.png`; git-filter-repo 2.47.0: 503 commits to 493, 10 empty ones dropped). Every
  commit hash the records cite is mapped to its new one, and `v1.0` is re-created on the release commit, in a fresh
  clone. The owner deletes and re-creates the GitHub repository, pushes it and makes it public (design-decisions,
  *The poster is dropped and every version removed from history*). The logo, the screenshots, the animation and the
  photo stay (the EULA's 3.1 and 3.5). The README gains a *Workflow* section, from a fresh clone to the first
  analysis.
- **Root-layout check on station SF4** (owner, 2026-11-03): `test/integration/test_root_layout.py`'s allowlist of
  ignored root entries and its untracked-entry check ran on macOS only. SF4 is not checked before the release. It is
  answered by `.venv/bin/python -m pytest test/integration/test_root_layout.py` on SF4.

## Done

| Revision | Delivered | Commits | Accepted |
|---|---|---|---|
| R1 | Skills in the repository: six skills in `.claude/skills/` with generic `SKILL.md` files and AnyScan's `references/project.md` layers, their LICENSE, the rewritten skills test, the records and the third-party inventory; the personal copies excluded by sparse checkout (design-decisions, *The skills ship in the repository*). Full record, with the owner's answers Q1-Q9 of 2026-10-29: `git show 8947abe:.claude/project-docs/FEATURES.md` | `06a57e9`…`8947abe`, closed by the commit that adds this row | accepted by the owner 2026-10-29 |
| R2 | The support-chat brief: support-brief's project layer, `.claude/project-docs/SUPPORT_CHAT.md` (its first run, checked against `739beab`) and `test/integration/test_support_chat.py`; the records of the use at station SF4 on 2026-10-29 and its offline v1.0 replay. The owner's statements of 2026-10-29: design-decisions, *The owner's statements of 2026-10-29*. Full record: `git show 94af1e8:.claude/project-docs/FEATURES.md` | `e0f429d`, `94af1e8`, closed by the commit that adds this row | accepted by the owner 2026-10-29 |
| R3 | Cleanup: the root-layout test (untracked and ignored root entries, case-only paths, all six records), `transformers` and `fonttools` declared, every file a test opens closed and a leak made an error (`pytest.ini`), the owner's statements of 2026-10-29 in design-decisions, the brief refreshed. Full record: `git show 62b603c:.claude/project-docs/FEATURES.md` | `c4d7854`…`62b603c`, closed by the commit that adds this row | accepted by the owner 2026-11-03 |
| R4 | README, licences, media: the README held to its sources with a *Validation* section, defect detection split in SPEC (a catalogued item's defined defects built, open-set not), the licence note and the third-party table, the station photo, the analysis animation (`Example/UI/analysis_animation.py`) and two Live screenshots, one command spelling `.venv/bin/python`, the brief refreshed. Full record: `git show e942ff3:.claude/project-docs/FEATURES.md` | `5f9c9dc`…`e942ff3`, closed by the commit that adds this row | accepted by the owner 2026-11-03 |
| R5 | Release v1.0: the corrected poster linked, the publication sweep (camera addresses in `192.0.2.x`, the station's path reworded), `CITATION.cff` and its test, the README's gallery and rollback block, the brief refreshed. The tag move and the GitHub page were the owner's. Full record: `git show ea534a5:.claude/project-docs/FEATURES.md` | `a4e958b`…`ea534a5`, closed by the commit that adds this row | accepted by the owner 2026-11-03 |
