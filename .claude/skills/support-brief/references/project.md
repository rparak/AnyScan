# support-brief: project reference for AnyScan

AnyScan's part of **support-brief** (`SKILL.md`, beside this folder). It overrides that skill where they differ.

## Where the brief lives

`.claude/project-docs/SUPPORT_CHAT.md`, beside the records. The public README does not mention it.

## Length

**At most 2,500 words**, counted by `wc -w` on the whole file. Trim the architecture (section 3) and the assistant's
role (section 7) first. The bound is never raised to make a draft fit.

## When it is refreshed

The rule is in feature-manager `references/project.md` > *Docs*: an accepted change that alters what the brief states
refreshes it with this skill.

## What holds it

`test/integration/test_support_chat.py`: the word limit, the commit and date in sections 0 and 9 (the commit must exist
and be an ancestor of HEAD), and the test count and times read from `CLAUDE.md` > Commands.

## What it may cite

- The evidence archive only as "AnyScan-Media archive, captures/<session>", never by a path.
- No hostname, IP address, user name or path from the station or a development machine. The hardware description is
  enough.
- No scratchpad or other uncommitted file. A result reproduced outside the repository cites the commit message that
  records its method.
