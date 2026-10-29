# Features

The tracker: what is open, and what each revision delivered with its owner's acceptance. Format:
project-style-rpx `references/markdown.md` > *FEATURES.md*. A revision's long record lives here while it is open;
once accepted it collapses to its row in *Done*, and what is still true moves to the SPEC, design-decisions or
KNOWN_ISSUES.

## Open

- **R3 - Cleanup: one entry point, layout test, dependencies** (owner, 2026-10-29). Found in R1: `transformers`
  (`src/Vision/Identifier.py`, DINOv2) and `fontTools` (`Example/UI/build_fonts.py`) are imported but not declared;
  they arrive only through mlx-vlm and through ultralytics' matplotlib. `models/gemma-4-12B-it-4bit` (6.3 GB,
  git-ignored) is referenced by nothing. The old local branches wait for a decision. The owner's answers to Part A
  (2026-10-29):
  - The application starts one way, `.venv/bin/python App/run.py`; SPEC says so now, the README in R4. The `win32`
    branch in `App/run.py` stays.
  - `test/integration/test_root_layout.py` also refuses untracked root entries, ignored root entries outside a
    written allowlist and case-only duplicate paths, and holds `FEATURES.md` and `SUPPORT_CHAT.md` as records.
  - `requirements.txt` declares `transformers>=5.14.0` and `fonttools>=4.22.0` (maintenance only), in its `>=` style.
    Exact pins wait for R5.
  - The 139 ResourceWarnings that the default run hides (all opened in tests) are fixed, and `pytest.ini` makes a
    leak an error.
  - project-optimize's timing table points to `CLAUDE.md` for the two check tiers.
  - The owner's statements of 2026-10-29 move to design-decisions (*The owner's statements of 2026-10-29*), and the
    brief is refreshed in R3.
  - `models/gemma-4-12B-it-4bit` is deleted by the owner after R3's final runs. The old local branches
    (`archive/github-original`, `main-pre-rebuild`, `warm-up-at-configuration-load`) are backed up as a bundle and
    deleted by the owner; a session does neither.
- **R4 - README** (owner, 2026-10-29), written with readme-writer: among other things a third-party section from the
  inventory in `.claude/skills/readme-writer/references/project.md` > *Third-party components*. Carries the owner's
  statement of 2026-10-29 that Gemma 4 E4B is Apache-2.0 (design-decisions, *The owner's statements of 2026-10-29*).
  Also (owner, 2026-10-29): the README media (two screenshots, a screen recording, a station photo, and removing
  `images/anyscan-poster-image.png`), the Gemma row of the inventory, `CITATION.cff`, and the record of JIC Smart
  Factory's and EDIH-DIGIMAT's approval to publish, in KNOWN_ISSUES. From R3 (owner, 2026-10-29): the README's
  commands in the one spelling `.venv/bin/python` (README lines 103, 113 to 115, 339 and 340, R3's numbering), and
  `preview_check.py` in the repository layout's list of `Example/` scripts (lines 316 and 317).
- **R5 - Release v1.0** (owner, 2026-10-29): the v1.0 tag moved to the release commit (owner-approved), the
  publication of the repository, and a rollback procedure for the station. From R3 (owner, 2026-10-29): exact
  `==` pins for `transformers` and `fonttools`, once the versions installed on SF4 have been checked.

## Done

| Revision | Delivered | Commits | Accepted |
|---|---|---|---|
| R1 | Skills in the repository: six skills in `.claude/skills/` with generic `SKILL.md` files and AnyScan's `references/project.md` layers, their LICENSE, the rewritten skills test, the records and the third-party inventory; the personal copies excluded by sparse checkout (design-decisions, *The skills ship in the repository*). Full record, with the owner's answers Q1-Q9 of 2026-10-29: `git show c454237:.claude/project-docs/FEATURES.md` | `6820f20`…`c454237`, closed by the commit that adds this row | accepted by the owner 2026-10-29 |
| R2 | The support-chat brief: support-brief's project layer, `.claude/project-docs/SUPPORT_CHAT.md` (its first run, checked against `1c9aade`) and `test/integration/test_support_chat.py`; the records of the use at station SF4 on 2026-10-29 and its offline v1.0 replay. The owner's statements of 2026-10-29: design-decisions, *The owner's statements of 2026-10-29*. Full record: `git show 6d6f068:.claude/project-docs/FEATURES.md` | `a62ed77`, `6d6f068`, closed by the commit that adds this row | accepted by the owner 2026-10-29 |
