# Markdown — the three records

Three files record three different things; put a finding in the one it belongs to. All 📄
documentation only.

| File | Records | Read by |
|---|---|---|
| `docs/design-decisions.md` | Deliberate choices whose reason is not visible in the code | Whoever is about to undo one |
| `README.md` > *Limitations* | The limitations that affect a decision built on the output | Everyone using the output |
| `KNOWN_ISSUES.md` | Open behaviours that show up in the text or numbers but decide nothing | Whoever sees one and wonders |

## `docs/design-decisions.md` entries

```markdown
## <The decision, stated as a sentence>

<What was decided, concretely: the rule, the value, the code it lives in.>

**Why.** <The reason — the evidence, the alternative rejected and why. Measured numbers where
there are any.>

**Revisit if** <the condition under which the decision should be reopened>.
Tests `test/<path>::<test>` (…); commit `<hash>` where the change is one commit.
```

- The title states the decision, not the topic: *The object crop padding stays at 0.20 for Gemma*,
  not *Crop padding*.
- **Revisit if** is required for every new entry. An entry without one is a decision with no
  expiry — the way a lenient path outlives its reason. The existing entries are not backfilled:
  about half have one, and inventing conditions for them afterwards would be guessing at past reasoning.
- The pinning tests (or the commit, when nothing can be tested) close the entry, so a change that
  contradicts it can be traced to what it would break.
- A correction to an entry says so in place (*Corrected 2026-09-24: …*) with what was wrong, so a
  re-check does not mistake the correction for the error.
- The labels vary in the existing entries (a bold **Why.** is used in some, a plain paragraph in most);
  the parts above are what the shape needs, not the typography.

## `README.md` > *Limitations*

Only limitations that affect a decision built on the output. Each is a `###` heading stating the
limitation, then:

1. **The consequence first**, bold, in the reader's terms: *Don't build a tolerance on these numbers.*
2. The evidence after, as bullets, with the measured numbers.
3. Plainly whether it is verified. No promise that some capture or later work will resolve it.

The section links `KNOWN_ISSUES.md` for everything else.

## `KNOWN_ISSUES.md` entries

A `##` title naming the behaviour; a paragraph saying what happens and where it was seen; then bullets
as they apply — **Impact:**, **Pinned by:** (the test that holds the behaviour — sometimes an `xfail` that
fires when it is fixed), **Not fixed here:** (why), **What would answer it:** (for an open question).
No promise that a capture closes it. When the behaviour is fixed the entry is removed and the
resolution goes to `docs/design-decisions.md`.
