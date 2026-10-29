# Features

The tracker: what is open, and what each revision delivered with its owner's acceptance. Format:
project-style-rpx `references/markdown.md` > *FEATURES.md*. A revision's long record lives here while it is open;
once accepted it collapses to its row in *Done*, and what is still true moves to the SPEC, design-decisions or
KNOWN_ISSUES.

## Open

- **R2 - The support-chat brief** (owner, 2026-10-29): support-brief's project layer (now a stub) and
  `.claude/project-docs/SUPPORT_CHAT.md`, its first run.
- **R3 - Cleanup: one entry point, layout test, dependencies** (owner, 2026-10-29). Includes, found in R1:
  - **Defect: `transformers` is not declared.** `src/Vision/Identifier.py` imports it to load DINOv2, but
    `requirements.txt` does not list it; it arrives only transitively, through `mlx-vlm` (`transformers>=5.14.0`;
    5.17.0 installed, 2026-10-29). A change to mlx-vlm's requirements would break the catalogue modes' install.
  - `fontTools` is imported by `Example/UI/build_fonts.py` (a maintenance script) and not declared; it arrives
    through ultralytics' matplotlib (4.65.0 installed).
  - `models/gemma-4-12B-it-4bit` (6.3 GB, git-ignored) is on the development Mac and referenced by nothing.
- **R4 - README** (owner, 2026-10-29), written with readme-writer: among other things a third-party section from the
  inventory in `.claude/skills/readme-writer/references/project.md` > *Third-party components*.
- **R5 - Release v1.0** (owner, 2026-10-29).

## Done

| Revision | Delivered | Commits | Accepted |
|---|---|---|---|
| R1 | Skills in the repository: six skills in `.claude/skills/` with generic `SKILL.md` files and AnyScan's `references/project.md` layers, their LICENSE, the rewritten skills test, the records and the third-party inventory; the personal copies excluded by sparse checkout (design-decisions, *The skills ship in the repository*). Full record, with the owner's answers Q1-Q9 of 2026-10-29: `git show c454237:.claude/project-docs/FEATURES.md` | `6820f20`…`c454237`, closed by the commit that adds this row | accepted by the owner 2026-10-29 |
