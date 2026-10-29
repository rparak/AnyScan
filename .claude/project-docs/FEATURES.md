# Features

The tracker: what is open, and what each revision delivered with its owner's acceptance. Format:
project-style-rpx `references/markdown.md` > *FEATURES.md*. A revision's long record lives here while it is open;
once accepted it collapses to its row in *Done*, and what is still true moves to the SPEC, design-decisions or
KNOWN_ISSUES.

## Open

- **R2 - The support-chat brief** (owner, 2026-10-29): support-brief's project layer (now a stub) and
  `.claude/project-docs/SUPPORT_CHAT.md`, its first run. The owner's statements of 2026-10-29:
  - Both sessions in the AnyScan-Media archive (captures/20261029-142803_s2 and captures/20261029-143904_s1) are real
    use at JIC Smart Factory on 2026-10-29.
  - The three folders deleted from the archive held irrelevant data, not test sessions.
  - Every object in the captures and screenshots is the property of JIC Smart Factory. No partner or customer parts.
  - Gemma 4 E4B is Apache-2.0, per the base card google/gemma-4-E4B-it (for R4, nothing changed for it in R2).
  - Station SF4 is the Linux machine with the RTX 5070 Ti verified on 2026-09-29. Both 2026-10-29 sessions and the
    11 UI screenshots in the archive come from it.
  - Development and the R2 replay ran on macOS (Apple M2 Pro).
  - The repository is private. It becomes public at R5 with JIC Smart Factory's and EDIH-DIGIMAT's approval, which
    R4 records in KNOWN_ISSUES. The v1.0 tag moves to the release commit at R5.
- **R3 - Cleanup: one entry point, layout test, dependencies** (owner, 2026-10-29). Includes, found in R1:
  - **Defect: `transformers` is not declared.** `src/Vision/Identifier.py` imports it to load DINOv2, but
    `requirements.txt` does not list it; it arrives only transitively, through `mlx-vlm` (`transformers>=5.14.0`;
    5.17.0 installed, 2026-10-29). A change to mlx-vlm's requirements would break the catalogue modes' install.
  - `fontTools` is imported by `Example/UI/build_fonts.py` (a maintenance script) and not declared; it arrives
    through ultralytics' matplotlib (4.65.0 installed).
  - `models/gemma-4-12B-it-4bit` (6.3 GB, git-ignored) is on the development Mac and referenced by nothing.
  - The decision on the old local branches (owner, 2026-10-29).
- **R4 - README** (owner, 2026-10-29), written with readme-writer: among other things a third-party section from the
  inventory in `.claude/skills/readme-writer/references/project.md` > *Third-party components*. Carries the owner's
  statement of 2026-10-29 that Gemma 4 E4B is Apache-2.0 (R2 above). Also (owner, 2026-10-29): the README media
  (two screenshots, a screen recording, a station photo, and removing `images/anyscan-poster-image.png`), the Gemma
  row of the inventory, `CITATION.cff`, and the record of JIC Smart Factory's and EDIH-DIGIMAT's approval to
  publish, in KNOWN_ISSUES.
- **R5 - Release v1.0** (owner, 2026-10-29): the v1.0 tag moved to the release commit (owner-approved), the
  publication of the repository, and a rollback procedure for the station.

## Done

| Revision | Delivered | Commits | Accepted |
|---|---|---|---|
| R1 | Skills in the repository: six skills in `.claude/skills/` with generic `SKILL.md` files and AnyScan's `references/project.md` layers, their LICENSE, the rewritten skills test, the records and the third-party inventory; the personal copies excluded by sparse checkout (design-decisions, *The skills ship in the repository*). Full record, with the owner's answers Q1-Q9 of 2026-10-29: `git show c454237:.claude/project-docs/FEATURES.md` | `6820f20`…`c454237`, closed by the commit that adds this row | accepted by the owner 2026-10-29 |
