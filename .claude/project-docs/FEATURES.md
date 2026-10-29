# Features

The tracker: what is open, and what each revision delivered with its owner's acceptance. Format:
project-style-rpx `references/markdown.md` > *FEATURES.md*. A revision's long record lives here while it is open;
once accepted it collapses to its row in *Done*, and what is still true moves to the SPEC, design-decisions or
KNOWN_ISSUES.

## Open

- **R1 - Skills in the repository** (owner, 2026-10-29; in progress on branch `skills-in-repo`). The six skills
  ship in `.claude/skills/` with generic `SKILL.md` files and AnyScan's `references/project.md` layers; the
  personal copies are excluded from `~/.claude/skills` by its sparse checkout (the owner runs the command). Design:
  design-decisions, *The skills ship in the repository*. The owner's answers of 2026-10-29: jic-sf-ui-style taken at
  `ec7af02` unchanged and allowed to name AnyScan and JIC (Q1); bootstrap mode dropped from the four SKILL.md files
  (Q2); the checker's and readme-writer's script tests in the suite, not jic-sf-ui-style's template tests (Q3);
  handovers pasted, never stored, in the generic text (Q4); a branch per revision, fast-forwarded into `main` by the
  owner after acceptance and pushed by the owner (Q5); AnyScan's own `check_readme.json` with the four avatars
  exempt (Q6); the dependency defects below go to R3 (Q7); a support-brief stub naming R2 (Q8); jic-sf-ui-style
  excluded from the personal skills on this machine and on the station (Q9). Awaiting acceptance.
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
