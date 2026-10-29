---
name: support-brief
description: >-
  Creates or refreshes the support-chat brief, .claude/project-docs/SUPPORT_CHAT.md: the one file
  the owner pastes as the first message into a new Claude chat, so that chat can act as the
  project's senior technical support (reviews, prompts for Claude Code, debugging, consistent
  decisions). CREATE surveys the whole repository and
  drafts the brief; REFRESH reads the brief, surveys what changed since the commit it names and lists
  every statement that is outdated, wrong or missing. Only facts from the repository, each traceable
  to a file. It reports first and stops for approval, unless the owner says no review. Use it only
  when the owner asks to create, write, refresh, update, check or review the support-chat brief, the
  support brief or SUPPORT_CHAT.md, or names /support-brief. Not for the README, the specification
  or other docs, a session handover, or feature work, even when that work changes what the brief
  states (the project's change workflow says when the brief is updated).
---

# support-brief

Creates or refreshes the support-chat brief of the repository it runs in.

**Assumes** (deliberate): a git repository with its internal docs in one folder, and an owner who
approves before anything is written. Nothing here names a project: the skill is copied into another
repository unchanged, and that repository's own decisions go in its `references/project.md` when it
has one.

**Task.** Create or refresh the support-chat brief for THIS repository -
`.claude/project-docs/SUPPORT_CHAT.md` (or the place where this project keeps its internal docs). The
owner pastes it as the first message into a new Claude chat; that chat then acts as the project's
senior technical support: it reviews Claude Code's output, writes prompts for Claude Code, helps
debug, and keeps decisions consistent. The file must describe the CURRENT state and stay current.

**When the brief is updated** is the project's rule, kept in one place in its change workflow
(section 5 proposes where); this skill only says how.

**Option "no review".** If the owner says "no review" when invoking the skill, do the survey and write
the file (CREATE) or apply the changes (REFRESH) directly, run the project's checks, and report
afterwards instead of stopping: the mode, what was written or changed, the activated modules and the
open questions. It commits locally (section 6's message) and never pushes: the push follows the owner's
acceptance.

## 0. Mode (decide first and state it)

- **CREATE** - the file does not exist: do the full survey (section 1) and write a new draft
  (sections 2-4).
- **REFRESH** - the file exists: read it, then survey the repository since the commit named in its
  section 9 (git log and the changed files). Report every statement that is outdated, wrong or
  missing (section, before -> after, source file), keep the owner's edits that are still true, and
  keep the structure. Add or remove domain modules only if the survey shows a change.

In both modes: report first and stop for the owner's approval; write nothing before it (unless the
owner said "no review").

## 1. Survey (read-only)

Read `CLAUDE.md`, the README, every docs folder (specs, decisions, known issues, trackers), the
configuration files, the source layout, the tests and how they run, the scripts/CLI, CI, the
licence(s), dependencies and their licences, the release/tag state, and the git log (what was built,
what failed, how it was fixed). Determine:

- what the project is, for whom, its domain, and who owns it;
- its current state and key results/metrics - only those recorded in the repository, each with its
  source file;
- the architecture (configuration, code areas, entry points, outputs, data and models);
- the rules and lessons that must not break (from specs, decisions, known issues, the commit
  history);
- how work is done (skills/conventions in `.claude/`, the design-first/approval flow, check tiers,
  git and release rules, the handover to a new Claude Code session);
- the open items and risks;
- the real-world impact: can the output move hardware, drive a machine, make or inform decisions
  about people, money, health, safety or security? This decides the deployment advisor role and
  modules D/E;
- which domain modules (section 3) apply.

## 2. The file

These sections, in this order, adapted to this project.

0. **Header**: how to use it (paste it whole into a new chat, together with the latest Claude Code
   report); who maintains it (Claude Code, in every accepted change that affects it); "the
   repository wins on any disagreement", naming the source-of-truth files; "state as of commit
   <hash>, <date>".
1. **The project in brief**: what, why, for whom, the repository, licence, release state,
   owner/authors, and any disclaimer the project already states (e.g. "simulation only", "research
   prototype"). The essential components or process as a short table or numbered list.
2. **Current state**: what exists; the key results/metrics with units, their variance where
   recorded, and their source; what is in progress and next.
3. **Architecture** (short): configuration, code areas and their roles, data and models, entry
   points (exact commands stay in `CLAUDE.md`), the agent docs, how correctness is verified.
4. **Lessons and rules that must not break**: one imperative line each, from the records.
5. **How work is done**: skills/conventions, the design-first and approval flow, check tiers, git and
   release rules, the session handover.
6. **Open items and risks** (summarized), and where the details live.
7. **The assistant's role** - a senior technical partner for this domain and for working with Claude
   Code:
   1. Reviewer: does the output meet the task and the acceptance criteria; are verified results
      kept; are claims backed by measurements or tests that fail on the old code; ask for missing
      numbers; flag unsupported claims, skipped steps, risky or unnecessary changes, and
      contradictions with recorded decisions.
   2. Work planner: small verifiable steps with measurable acceptance criteria; order and
      dependencies; the time and compute cost of heavy runs.
   3. Debugger: hypothesis -> measurement -> targeted fix; no cause without data.
   4. Guardian of consistency: new requests against earlier decisions and lessons; the owner decides.
   5. Evaluation designer (when results are measured): benchmarks, baselines, ablations, acceptance
      metrics, the operating point.
   6. Risk reviewer: failure modes, edge cases, red-team questions before a change is accepted.
   7. Deployment advisor (only with real-world impact): what a change means outside the
      simulation/lab (safety, limits, interlocks, rollback, compliance), and what remains
      unvalidated.
   8. Compute steward (when runs are heavy): what to cache, parallelize or skip; GPU/CPU hours.
   9. Communication on request: e-mails, texts, README wording - factual, without overstating
      results.

   Do not: invent numbers, sources or standards; loosen a limit, bound or test to make it pass;
   present unvalidated results (simulation, single runs, lab data) as validated; certify safety or
   compliance; decide for the owner anything that changes behaviour, data, models, safety or the
   public record.
8. **How to answer**:
   - Start-of-chat ritual: the first reply is a summary of the understanding in at most five lines,
     plus the open questions; no advice before that.
   - The reply language is chosen by the owner at the start (ask once if not stated, then keep it).
     Every generated deliverable is in English (prompts for Claude Code, docs, README text, code
     comments, commit messages, release notes), unless the owner asks for another language for a
     specific text.
   - Conclusion first (fine / problem / decision needed), then details; recommendations marked, each
     with a one-sentence reason.
   - Prompts for Claude Code in a separate code block, ready to copy: context (1-2 sentences, plus a
     handover preamble for a new session); the task in numbered items; the files/areas; constraints
     (what must not change); measurable acceptance criteria; whether to report first and stop; what
     to print at the end (commands and results, checks, commits, remote state).
   - Code changes as prompts for Claude Code, not finished code, unless the owner asks for code.
   - Uncertainty: ask, or say what to verify; check facts about tools, libraries and standards when
     in doubt.
9. **Updates**: the last-updated date and commit; when to update (every accepted change that alters
   the state, numbers, commands, rules, roles, modules or open items); what must stay exact and where
   it comes from; "if this file disagrees with the repository, fix this file".

**The commit it names** (sections 0 and 9) is the commit the brief was checked against: a commit
cannot name its own hash, so it is the last commit before the one that writes the brief. A REFRESH
surveys from there.

## 3. Domain modules

Include a short section for each one that applies (state in the report which apply and why; omit the
rest).

- **A. ML lifecycle**: dataset versions and splits (leakage checks); training reproducibility (seeds,
  hardware nondeterminism); experiment tracking and the model registry; a model card (intended use,
  limits, failure modes); the evaluation protocol (held-out/OOD sets, the operating point and
  thresholds); drift monitoring after deployment.
- **B. Statistical rigour**: metrics with variance over seeds/runs and confidence intervals where
  possible; sensitivity analyses and ablations; no comparison claimed from a single run.
- **C. Sim-to-real**: calibration (camera intrinsics/extrinsics, hand-eye, robot base/TCP); sensor
  noise and latency models; domain randomization; the measured reality gap; the hardware-in-the-loop
  / real validation plan and its order (reduced speed, one moving object at a time).
- **D. Safety and compliance**: a register of standards and regulations that may apply to the domain
  (e.g. industrial robots ISO 10218, collaborative operation ISO/TS 15066, safety-related control
  ISO 13849 / IEC 62061, in the EU the Machinery Regulation and the AI Act where ML is part of a
  safety function), each marked "verify the current version and applicability"; the risk-assessment
  status; when to escalate to a qualified safety engineer or legal advisor.
- **E. Real-time and deployment**: latency/throughput budgets; target hardware (edge, GPU, PLC, robot
  controller); interfaces (e.g. ROS 2, OPC UA, fieldbus); firmware/driver versions; rollback.
- **F. Machine vision**: calibration and lighting assumptions; labelling QA; metrics at the operating
  point (precision/recall; the cost of a false reject vs a false accept); data protection for people
  in images.
- **G. Traceability**: a requirement -> test -> result map for the key requirements; a change log of
  safety-relevant parameters.
- **H. Data, models and licences**: dataset and pretrained-model/weights licences, third-party code,
  data protection, export-control flags if relevant.

## 4. Rules for the draft

- Only facts from the repository, each traceable to a file; anything unknown becomes an open
  question, never a guess.
- No secrets, credentials or personal data beyond what the repository already states publicly.
- Concise: at most about 2,500 words, counted by `wc -w` on the whole file (tables, code and markup
  included): the one measure, so counts compare between runs; no other count is reported. The
  project reference may set another limit. Details by reference to the repository files; no history
  that git already holds.
- English.

## 5. Placement and maintenance (propose; do after approval)

- The location next to the internal docs; not mentioned in the public README unless the owner says
  so.
- The maintenance rule in one place, in the project's change workflow (e.g. the feature-manager
  skill or `CLAUDE.md`), referenced from `CLAUDE.md`.
- If the project has layout tests or doc file lists, allow the new file.
- A light test: the file exists, section 0 and section 9 name a commit and a date, and the key
  numbers it states match their source files (propose which numbers; break the test once).

## 6. Report, then build

**Report**: the mode, the survey summary with its source files, the activated modules and why, the
full draft (CREATE) or the list of changes (REFRESH), the word count by `wc -w` (before and after for
REFRESH), the questions for the owner, and the proposed location, maintenance rule and test. Then
stop.

**After the owner's approval**: write the file (CREATE) or apply the listed changes (REFRESH), plus
the maintenance rule and the test if they do not exist yet; run the project's checks; commit
"SUPPORT_CHAT.md: create the support-chat brief" or "SUPPORT_CHAT.md: refresh to <commit>"; push only
as the project's rules allow after acceptance.
