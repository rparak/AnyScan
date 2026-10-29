# Markdown - the records

Each file records one kind of thing; put a finding in the one it belongs to. All 📄 documentation
only. Where the files live and their overall shape: references/structure.md > `.claude/project-docs/`.

| File | Records | Read by |
|---|---|---|
| `.claude/project-docs/SPEC.md` | The approved specification, as it is now: goal, scope, measured facts, layout, formats, configuration, tests, risks | Whoever implements or reviews |
| `.claude/project-docs/design-decisions.md` | Deliberate choices whose reason is not visible in the code | Whoever is about to undo one |
| `.claude/project-docs/KNOWN_ISSUES.md` | Open limitations and accepted risks of the output | Whoever uses the output |
| `.claude/project-docs/FEATURES.md` (optional) | The feature tracker, when the owner wants one | Whoever plans the next change |
| `README.md` | The public page; written and maintained with the readme-writer skill | Everyone |

## `SPEC.md`

- **Current truth.** It says what is, not how it got there; history is in git. A changed decision
  is changed in its section, in the same commit as the code.
- **Stable section numbers.** Other files and code comments cite `SPEC §n`; a number is never
  reused. A removed section keeps its heading with a one-line note; new sections are appended.
- Measured facts carry their method, date and source; an estimate says so.
- A change that contradicts SPEC either updates it, with the owner's agreement, or does not happen.

## `design-decisions.md` entries

```markdown
## <The decision, stated as a sentence>

**Decision.** <What was decided, concretely: the rule, the value, the code it lives in.>

**Why.** <The reason - the evidence, with measured numbers where there are any, and the source
(a manual page, a measurement, a SPEC section).>

**Alternatives.** <Each option rejected, and why.>

**Revisit if** <the condition under which the decision should be reopened>.

Pinned by `test/<path>::<test>`.
```

- The title states the decision, not the topic: *Every configuration field is required*, not
  *Configuration*.
- **Revisit if** is required for every entry. An entry without one is a decision with no expiry.
- **Alternatives** names what was weighed, so the next person does not re-propose a rejected option
  without its counter-argument.
- The pinning tests (or, when nothing can be tested, the reason) close the entry, so a change that
  contradicts it can be traced to what it would break.
- A correction to an entry says so in place (*Corrected YYYY-MM-DD: …*) with what was wrong, so a
  re-check does not mistake the correction for the error.
- Every implemented decision SPEC records has an entry.

## `KNOWN_ISSUES.md` items

A `##` title naming the limitation; a paragraph saying what is true and what it means for whoever
uses the output; then bullets as they apply - **Impact:** (in the reader's terms: what to check
before relying on the output), **Evidence:** (the measured numbers, the SPEC section), **Pinned by:**
(the test that holds the behaviour, if any), **What would close it:** (the measurement or feature).

- **Open items only.** When an issue is fixed the item is removed and the resolution goes to
  `design-decisions.md`.
- Only what has been decided or measured; nothing is added that was not decided.
- Say plainly whether a statement is verified (*measured on the reference input only*, *unverified
  on Linux*). No promise that later work will resolve it.
- When the output drives a physical system, the file opens with the project's safety sentence
  (the project reference gives it): a result verified only in simulation or tests is a proposal.

## `FEATURES.md` (optional)

A project that wants a tracker keeps one, and its project reference says so. It holds:

- **Open**: one line per open item, with the owner's note and date where it came from.
- **Done**: a table, one row per feature - its number, one line on what it delivered, its commits
  (first…last), and *accepted by the owner YYYY-MM-DD*.

A feature's long record (its design report, the measurements, the sub-items) lives in the tracker
while the feature is open. Once it is accepted, what is still true moves to SPEC, design-decisions or
KNOWN_ISSUES (whatever code or configuration cites goes first), the record collapses to its row, and
the row points to the commit that last held the full record (`git show <hash>:<path>`).
