# Documentation consolidation plan (written session 121, 2026-08-03)

> **Who this is for:** a Sonnet-tier session executing a *text-editing and archiving* task. It is
> deliberately mechanical. **No measurement, no render, no gate run, no `src/` change is authorised
> by this plan** — see "Hard constraints" below. If you find yourself wanting to verify a number,
> stop: that is out of scope and it is the expensive path.

---

## 0. The problem, in numbers

`wc -l`, measured 2026-08-03:

| file | lines | auto-loaded every session? |
|---|---|---|
| **CLAUDE.md** | **5,788** | ✅ yes |
| `.claude/rules/measurement-discipline.md` | 1,806 | ✅ (via `@`) |
| `.claude/rules/circuit.md` | 863 | ✅ |
| `.claude/rules/reference-sources.md` | 523 | ✅ |
| `.claude/rules/dsp.md` | 365 | ✅ |
| `.claude/rules/build.md` | 267 | ✅ |
| `.claude/rules/ui.md` | 209 | ✅ |
| `.claude/rules/architecture.md` | 164 | ✅ |
| **auto-loaded subtotal** | **≈9,985** | |
| `docs/phase9-gap-log.md` | 9,932 | ❌ archive |
| `docs/session-log.md` | 7,309 | ❌ archive |
| `docs/phase7-calibration-handover.md` | 2,621 | ❌ |
| 12 other `docs/*.md` | ≈3,559 | ❌ |
| **total** | **33,406** | |

**≈10,000 lines are read into context before a single session's work begins.** That is the cost
this plan is aimed at. The 17,000 lines of archive (`session-log`, `phase9-gap-log`) are **not** the
problem — they are already out of the loaded path and must be left alone.

### Why it regrew

Session 89 already did this exercise: it archived a 6,914-line "Current step" block to
`docs/session-log.md` and rewrote it with an explicit instruction — *"Keep this block SHORT — if it
grows past ~120 lines again, archive it and rewrite the summary."* **Thirty-two sessions later it is
5,788 lines.** So a one-off trim is not the deliverable. The deliverable is a trim **plus a
structural rule that makes the growth land somewhere other than CLAUDE.md**, because the growth
itself is legitimate — each session genuinely produces a finding worth keeping.

The mechanism of regrowth is visible in the file: each session appends a full narrative block, and
when a later session refutes it, the convention has been to **keep the original verbatim and add the
refutation above it**. That convention is *correct* (see Hard constraint #2) and it is also
quadratic. The fix is to keep the refutation and drop the narrative, not to drop the refutation.

---

## Hard constraints (read before touching anything)

1. **Archive verbatim before deleting anything.** Every line removed from CLAUDE.md must first exist,
   word-for-word, in a file under `docs/`. Session 89 set this precedent and it is why nothing was
   lost then. Do not paraphrase on the way into the archive.

2. ⛔ **A refutation is worth more than the finding it refutes. Never drop a ⛔/⚠ "do not quote this"
   marker.** This project's dominant failure mode is a session re-opening an item that was closed
   measurements ago (`verify-the-PREMISE`, eight recorded occurrences). If you must choose between
   keeping a 40-line finding and keeping the one line that says it was refuted, **keep the
   refutation**. Where possible keep both, compressed to one line each.

3. **No numbers may be invented, recomputed, rounded, or "tidied".** Every figure in these docs was
   paid for by a session. Copy them exactly, including the units and the qualifier they travel with
   ("quote the SIGN, not the size", "±1.10 dB of operating-point spread", "n = 5", etc.). A number
   without its caveat is worse than no number — that is `pooled-statistic-cannot-answer-about-its-
   own-axis` in a new costume.

4. **No `src/`, `tests/`, or `analysis/` changes.** This is a docs task. Do not fix a stale constant
   you notice; **record it in the "found in passing" list** (§6) and leave it.

5. **Do not run the gates, the matrix, or ctest.** Nothing here changes behaviour, so there is
   nothing to verify by running. The verification is textual (§5).

6. **`docs/session-log.md` and `docs/phase9-gap-log.md` are append-only archives — do not compress
   them.** They are not loaded into context, so they cost nothing per session, and they are the
   safety net that makes everything below safe.

---

## 1. CLAUDE.md — the main job (5,788 → target ≤700 lines)

### 1.1 Current structure, by line range

| lines | section | verdict |
|---|---|---|
| 1–129 | header, Quick reference, Schematics, Delegation & model tiering, Essential reading, Build sequence | **KEEP essentially as-is** (~130 lines). Stable, non-narrative, all still true. |
| 130–2,700 | `### Where we are` — stacked per-session blocks, sessions 100–121 | **THE BIG ONE, ~2,570 lines.** Compress to ≤200. See §1.2. |
| 2,701–2,852 | `### THE RELEASE GATE` | Compress to ~40. See §1.3. |
| 2,853–3,455 | `### Open work, in order` | Compress to ~80. See §1.4. |
| 3,456–4,395 | `### Standing rules that must not be lost` | Compress to ~90. See §1.5. |
| 4,396–5,467 | 28 × `### Uncommitted at session N` blocks | **DELETE from CLAUDE.md entirely, ~1,070 lines.** See §1.6. |
| 5,468–5,788 | `## Project-specific carry-forwards` | Compress to ~120. See §1.7. |

### 1.2 `Where we are` (2,570 → ≤200)

**Step 1 — archive.** Append lines 130–2,700 verbatim to `docs/session-log.md` under a new heading
`## SESSIONS 100–121 — full per-session narrative, archived from CLAUDE.md session 121`. The archive
file already contains sessions 1–93 + 100 in exactly this style, so it is the right home. Keep the
session blocks in the order they appear.

**Step 2 — replace with three short sub-sections:**

**(a) STATUS — ~20 lines.** Present tense, no history:
- Phases 1–8 complete; Phase 9 (reference validation) in progress; Phase 10 not started.
- Current baseline: `analysis/reports/s120_newton.json` (162 captures). *Every OD number is quoted
  against this.* `s118_clampfix.json` is the diff-against control (identical membership).
- ctest **17/17** as of session 120 (first clean suite since session 44).
- Release gate: **6 rows over SHIP** — run `analysis/release_gate.py` for the live numbers; do not
  transcribe them (§1.3).
- Absolute-ledger gates (K/M/O/P/Q) must be read against `s118_clampfix.json` or later — GATE O
  refuses anything earlier by design.

**(b) SHIPPED CONSTANTS — one table, ~25 lines.** One row per constant that has moved since the last
reset, with only: constant, old → new, session, one-clause reason, and where the full provenance
lives (which is `FitParams.h` / `GainStaging.h` / `Clipper.h` comment blocks — **those are already
the fullest record and must not be duplicated here**). The known set to cover:
`c21R`, `jfetSatNeg` (s91) · the 17 ATTACK/treble-ladder constants (s100 — one row, pointing at
`FitParams.h`'s session-100 block) · `kInputRef` (s109) · `_GAIN_SESSION_MEASURED_DB[-12]` +
the THD row split (s114) · `kOutputMakeup` + the MASTER PWL taper replacing `masterTaperExp`
(s115) · the D1/D2 clamp window / `kTripPointV` (s118) · the bracketed-Newton `rtsafe` solve (s120).

**(c) CLOSED / REFUTED — one table, ~60 lines, and this is the load-bearing part.** One row per
item that a future session might otherwise re-open. Columns: *claim · status · session · one-line
reason · pointer*. Extract these from the ⛔/⚠ markers currently scattered through the narrative.
The known set, at minimum — **verify against the file, do not trust this list to be complete**:

| claim | must record |
|---|---|
| GATE J9's conditioned table (`level`, `gruntIdx`, `attackIdx`, `drive` as OD-residual levers) | **RETIRED as a localisation, all four.** `gruntIdx` s108, `level` s116 (it is dilution), `attackIdx` 1.23× = not a lever, `drive` weak/non-monotone. ⇒ the remaining OD error is **not localised on any control axis**. Do not re-open. |
| "GRUNT off-flat, 1.68–1.85×, GAP #3b" | CLOSED s108. GAP #3b dissolved s38; no GRUNT cap reaches the target (C12 locus right-and-down vs pedal right-and-up); the 1.68–1.85× is confounded with bleed. |
| "`blend = 1.0` is bleed-free" | REFUTED s103 (GATE K2). Bleed vanishes only where BOTH BLEND and LEVEL are max. |
| A3 = 5.1–5.5 dB as a **fit target** | REFUTED s108 (GATE P): window mean over a migrating feature, ±1.10 dB operating-point spread, pedestal unmeasured. **A3's SIZE and GATE O's attribution stand** — the OD path is quiet, clean side bounded at 0.48 dB (s119 re-quote), deficit 4.38 dB. |
| "the clean side is exonerated to 0.007 dB" | OVERCLAIM. Quote **0.48 dB** (s119) — earlier 0.41 (s107) was on the s99 baseline. |
| "session 109's `kInputRef` broke GATE I" | REFUTED s114. The guard was wrong, not the model; GATE I passes on every report s91–s113. |
| "ND's clean path is not level-invariant" (GATE O5 attribution) | REFUTED s112. It is 12.000 dB flat to 0.0003 across four fresh twins; the tilt is one contaminated pair (`ref-clean.wav`). |
| "even n12 clips at the top two MASTER detents" | REFUTED s115 (GATE T3). Duplicated/mis-dialled capture, not a ceiling. `kOutputMakeup` was knob-corrupted by 4.447 dB. |
| session 106's "`kOutputMakeup` is CONFIRMED RIGHT" | REFUTED s115 — circular (re-confirmed against the capture it was fitted to). |
| "a null whose depth grows with level, at DRIVE MAX" (the head item for 7 sessions) | **MIS-STATED, stood down s117 (GATE V).** It names the end of the ladder where the pedal is flat. Successor target: DRIVE max × **QUIET**, 3 of 5 switch conditions, 8.68 dB — but V5 says the error changes sign across the ladder, so no depth correction closes both ends. Recommendation on record: treat as a symptom of GATE Q's "the OD path saturates too early". |
| session 92's attribution of `OSValidationTest` to the un-ADAA'd VTC | **SUBSTANTIALLY REFUTED s120** — it was the solver. ADAA remains open; s92's alias/aperiodicity table is unquotable until re-measured. ✅ s121 re-measured it: aperiodic regime **CLOSED, 0/21**; genuine fold-down survives. |
| the THD "level term" direction | The gated term is an **UNSIGNED** rms. Signed mean is **positive** — the model **over**-distorts. Any candidate reasoned about as "we need more distortion" is backwards. |
| `s114_baseline.json` for absolute ledgers | STALE — predates session 115's shipped constants. GATE O refuses it by name. |

⚠ **The two "kept as the record" superseded blocks** (session 102's LEVEL structural-impossibility
argument, and session 110's null-depth sentence) can be reduced to their one-line refutation in this
table — the full superseded text goes to the archive with everything else.

### 1.3 `THE RELEASE GATE` (152 → ~40)

The section already says of its own table: *"THE TABLE BELOW IS STALE AS OF SESSION 120 — run the
script."* Act on that.

**Keep:** the bar definitions (SHIP / stretch columns are the *agreement*, not a measurement — they
live in `release_gate.py`'s `GATE` constant and must stay documented), the command, the
`--method`/`--compare`/`--ex-gain-n12` flags, the pre-registered HF-split fallback and its trigger
("everything else closed"), and the standing warnings that the OD headline is membership-weighted
and that CLEAN rows are split by region.

**Delete:** the entire multi-column `now / s112 / s110 / s100` history table, the per-session
movement commentary, and the s96 CLEAN-split narrative. Replace the whole table with one line:

```bash
/opt/homebrew/bin/python3.11 analysis/release_gate.py analysis/reports/s120_newton.json
```

plus a single sentence naming the current count (6 rows over SHIP) and the six rows by name.
`rebuild-targets-dont-transcribe` — the script is the definition.

### 1.4 `Open work, in order` (603 → ~80)

Items 0, 1, 2, 6 and 7 are marked **DONE**; item 3's premise is **REFUTED**; item 4 contains a
~400-line sessions-93-to-99 ATTACK narrative that is pure history; item 5 (A3) has been re-scoped
five times, each re-scope stacked on the last.

**Rewrite as a flat numbered list, one item = 2–5 lines**, taking the CURRENT ordering from the
**session-121 `▶ NEXT` list** (the most recent one — near the end of the SESSION 121 block), not
from this section, which is stale. That list is:

1. ✅ done s121 (alias gate re-run).
2. ADAA the CD4049 VTC — Phase 10 B head item, re-scoped to the 2×/4× realtime floor.
3. THD level term (over its 3.0 bar; model over-distorts).
4. Perf: the `pow()` path, not the solver (`clipK = 2.4653` misses the `k == 2.0` fast path).
5. Re-point the other consumers of the corrupted MASTER anchor (4 named files).
6. VTC-amplitude-vs-physical-rail inconsistency (a K/clipSat re-fit).
7. The peak/notch centre-frequency audit (s119 items 8–9) — **largest open MODEL item.**
8. Capture question + missing `_GAIN_SESSION_MEASURED_DB[-18]` entry.

For each: what it is, why it is not done, and the **one** pointer to where the detail now lives
(archive section or gate script). Every ✅ DONE item collapses to a single line or disappears — its
detail is in the archive.

⚠ **Item 5 (A3) is the one to be careful with.** Its exclusions compose into a statement worth
preserving in full, because it is what stops five different searches being re-run:
*no single element (s50), no post-clipper linear element of ANY order (s52), no GRUNT-side cap
(s38), its level is not a fittable constant (s108), and its shape MIGRATES with stimulus so no fixed
linear network can produce it (s108 synthesis).* **Keep that sentence intact.**

### 1.5 `Standing rules that must not be lost` (940 → ~90)

Most of this section is the session-89-to-101 HF/GATE-I investigation written out longhand, and it
now ends in a settled answer. Compress to the settled answers only:

- The captures are the ND plugin, not hardware → `reference-sources.md` is the authority rule.
  (1 line + pointer.)
- The generalisable traps live in `measurement-discipline.md`. (1 line.)
- Never quote a matrix total without its capture count. (1 line, keep the occurrence count.)
- **The matrix is blind to any pure level error, and one was 9.3 dB** — with the consequence:
  a control-LAW question must use a matched-pair, no-gain-match instrument, and the matrix must not
  be quoted as arbiter. (Keep ~6 lines; this is heavily load-bearing.)
- The HF region is ND's artefact, quotable from a **passing** GATE I since s114 (G2b: zero overlap,
  gap +17.44 dB/oct; G2c monotone dose-response). Keep ~6 lines. Delete the s89–s101 narrative of
  how it was established — that is archive material.
- The pre-registered HF-split fallback and its trigger. (Already in the gate section; cross-ref, do
  not duplicate.)
- "STOP AIMING MODEL WORK AT 8–16.3 kHz" with its ~38 % figure. (2 lines.)

### 1.6 The 28 × `Uncommitted at session N` blocks (1,070 lines → **0**)

**Delete all 28 from CLAUDE.md.** Justification, in order of strength:

1. **They are a transcription of `git status`, and `git status` is the source of truth.**
   `rebuild-targets-dont-transcribe`. The blocks are already partly stale — the session-120 one says
   *"`git diff --stat -- src tests` is no longer session 118's eight files' content… Any future
   session quoting that phrase must re-derive it."* The file is telling you to delete it.
2. Sessions 89–114 **are committed** (`df81360`). Their "uncommitted at" blocks describe a state
   that no longer exists. Only sessions 115–121 are genuinely uncommitted (22 paths, per
   `git status --porcelain`).
3. The genuinely useful content — *why* a constant moved, what a gate does, what an artefact is —
   is duplicated in the session narrative (going to the archive) and in the source comments.

**Replace with ~15 lines:** a single `### Uncommitted work` section stating that sessions 115–121
are uncommitted, listing the changed paths from a live `git status --porcelain` at execution time,
and naming the regenerable artefacts (`analysis/reports/*.json`, `analysis/fit_logs/*.log`,
`build/**`) as gitignored. **Archive all 28 blocks verbatim** to `docs/session-log.md` first — the
per-session "what changed and why" detail in them is genuinely useful history.

▶ **Flag to the user, do not act:** 7 sessions of work including 3 shipped-constant changes are
uncommitted. Committing them would make this section trivially maintainable in future. That is the
user's call, not this task's.

### 1.7 `Project-specific carry-forwards` (320 → ~120)

Keep, compressed:
- **Capture access status** — ⛔ this is live and urgent. Access is ending; the scarce framing is
  re-instated; ask the user immediately if a capture is needed. Keep the full inventory of what
  landed in sessions 111/112/113/120, but as a compact list, not a narrative.
- The MASTER `gain-n18` ladder captured s120, with the user's own accuracy caveat **verbatim**
  (*"the positions are best estimates… 0700, 1200, 1700, 0930, and 1430 are somewhat the most
  accurate"*) — that quote is a measurement qualifier and must survive intact.
- The two ear-matched listening findings (MASTER ≈0.61, DRIVE ≈0.8) as leads, with their "not
  measured, not gated" status attached.
- The two shipped bug fixes (bypass-engage click, knob-turn zipper) — compress each to ~4 lines:
  symptom, root cause, fix, file. The full diagnosis is in git history.
- The circuit facts (target = B7K Ultra, `[ENG]` list, supply/VD, clipper is CMOS not diodes,
  non-WDF-native parts) — these are **duplicated from `circuit.md`**. Replace with a pointer.
- Delete the settled 2026-07-19/20/21 verification narrative (BOM reconciliation, node-graph
  triple-check, UI asset landing) — all of it is in `circuit.md` / `ui.md` already, which are the
  files that own those facts.

---

## 2. `.claude/rules/measurement-discipline.md` (1,806 → target ≤750)

**This is the second-most valuable file in the repo and the second-most bloated.** 191 top-level
entries across 7 sections, many with nested sub-entries that are *the same trap found again*.

**Do NOT delete entries. Merge them.** The rule for merging:

- Entries that share a root cause become **one entry with the occurrence count and the single
  clearest worked example**. The others' distinguishing detail becomes one clause. E.g.
  `aggregate-moved-check-membership-first` currently has eleven occurrences written out
  individually — that becomes one entry, the count, the two most instructive cases (s112's
  flattering direction, s113's "knowing the trap does not immunise you"), and one line for the rest.
- **Keep every entry's NAME.** The names are referenced by ID from CLAUDE.md, the memory files and
  the gate source comments (`empty-gate-must-fail`, `bound-resting-means-unidentified`,
  `rebuild-targets-dont-transcribe`, …). A renamed or dropped name breaks a cross-reference.
- **Keep the session attributions** `(sNN)` — they are how a reader finds the full story.
- Where an entry has a ⭐ GENERAL clause, **that clause is the entry**; the worked example can be
  cut to one sentence.
- **Do not merge two entries that have different remedies**, however similar the symptom. E.g.
  "recording repeatability 0.010 dB" vs "re-dialling repeatability ≤1.6 dB" are explicitly *not
  interchangeable* — merging them would destroy the distinction the entry exists to make.

Suggested per-section targets: §1 ≈180, §2 ≈120, §3 ≈130, §4 ≈70, §5 ≈90, §6 ≈120, §7 ≈40.

⚠ Add a one-line header note: **"Merged in session 122; occurrence counts are cumulative and the
full per-incident narrative is in `docs/session-log.md`."** Otherwise a later session reads a
count of 11 with two examples and adds a twelfth as if it were new.

---

## 3. `.claude/rules/reference-sources.md` (523 → target ≤250)

The authority split in §1 is the operative content and is excellent. The problem is that **§1's
table cells have become session logs**: the "OD-vs-clean mixing balance (A3)" row is a *single
markdown line* containing eight stacked session updates (s105, s107, s108, s109, s112, s114 …), each
prefixed with its own ⛔/⭐ and each partly superseding the one below.

**Restructure:** keep §1's table to **one or two sentences per cell — the current verdict only** —
and move the stacked history out into a short `## 1a. How the A3 row got its current wording` list
below the table, one line per session, in date order, refutations preserved. Same treatment for the
§0 "0.144 dB take-to-take floor" row.

Then:
- §2 (the clean-path anchor) — **keep in full.** It is the only section precise enough to fit
  against and it says so.
- §3 (driven-condition divergences) — keep the table, compress the s110 GATE R inline block to
  3 lines (its detail belongs in the archive).
- §4 (the harmonic finding) — **the finding itself is the biggest thing in the file and stays.** The
  nested `>` quote-block chain of sessions 72→84 updates (about 100 lines) compresses to a table:
  session · what it established · status. Preserve every ⛔ (*the chart's numbers are DEMOTED, do not
  score a candidate against them*; *`2·a·cn = 1` is affordable but NOT free*; *gate the two drive
  regimes separately and expect opposite matrix signs*).
- §5 (rules of engagement) and §6 (what is NOT claimed) — **keep verbatim.** Both are short and both
  are pure operative rule.

---

## 4. `docs/` — retire what is fulfilled

⚠ **This section is the lowest-value part of the plan and should be done LAST.** None of `docs/` is
auto-loaded, so archiving it saves **zero** per-session context — the entire benefit is that a future
session searching `docs/` is not misled by a fulfilled one-shot request. Weigh that against the
broken-link risk below, and skip anything that looks marginal.

Create `docs/archive/` and **move** (`git mv`, do not copy-and-delete) these. ⚠⚠ **Every one of them
has inbound references, several from `analysis/*.py` — measured 2026-08-03, table below. Update
every inbound path in the same commit as the move, or the moves are a broken-link generator.**

| file | lines | inbound refs (excl. `session-log` / `phase9-gap-log`, which are archives and may keep stale paths) | why archive |
|---|---|---|---|
| `session53-capture-request.md` | 191 | none live | one-shot request, fulfilled |
| `session67-capture-request.md` | 90 | none live | fulfilled |
| `session59-capture-request.md` | 110 | none live | fulfilled |
| `session58-capture-request.md` | 86 | `docs/session59-capture-request.md`, **`analysis/attack_drive_axis.py`** | fulfilled |
| `phase7-handoff.md` | 172 | `docs/build-plan.md`, `docs/phase7-calibration-handover.md` | Phase 7 complete |
| `clean-gate-split-handover.md` | 172 | `CLAUDE.md`, `.claude/rules/measurement-discipline.md`, `docs/phase9-validation.md`, **`analysis/release_gate.py`** | marked EXECUTED (s96) |
| `phase7-calibration-handover.md` | 2,621 | `CLAUDE.md`, `.claude/rules/reference-sources.md`, **`analysis/reanchor_gm.py`, `fit_nonlinear.py`, `fit_jfet_boundary.py`, `mixer_law.py`** (+ ~20 `analysis/fit_logs/*.log`) | Phase 7 complete |

⚠ **`phase7-calibration-handover.md` is the one to think about rather than move reflexively.** Four
live analysis tools cite it as their derivation of record, and `reference-sources.md` cites it in the
standing "what the captures are" warning. Two acceptable outcomes — pick one and say which:
**(a)** move it and update the six live citations (the `fit_logs/*.log` are historical output and are
left alone); or **(b)** leave it in `docs/` and add a two-line header marking it as a completed-phase
reference. **(b) is the lower-risk option** and the 2,621 lines cost nothing per session — it is not
auto-loaded. Only its *citations* matter, and they are already correct.

⚠ Editing a `.py` file to fix a docstring path is the one exception to Hard constraint #4. It is a
comment change only — **do not touch any code on the same line or in the same function.**

**Leave in place, unchanged:** `build-plan.md`, `calibration-and-gain-staging.md`,
`nonlinear-component-modeling.md`, `ui-peripheral-spec.md`, `validation-and-capture.md` — all are
referenced as live "essential reading" from CLAUDE.md and are reference material, not narrative.

**Check, then decide:** `final-capture-window.md` (501 lines). Its premise was voided
(2026-07-29, captures unlimited) and then **re-instated** (s111, access ending). It is cited from
`.claude/rules/reference-sources.md` §0 and from two live tools (`analysis/gen_notch_sweep.py`,
`analysis/verify_new_captures.py`). Read the first 40 lines and either mark it live at the top or
archive it — **do not guess, and given capture access is currently ending, the default is to leave
it live.**

**`phase9-validation.md` (431 lines) stays live** — it is the current phase's own record and is
cross-referenced heavily. Do not touch it in this pass.

---

## 5. Verification (do this before reporting done)

Textual only. Run each and report the output:

1. **Line counts.** `wc -l CLAUDE.md .claude/rules/*.md` — confirm the auto-loaded subtotal is
   ≈2,600 or below, from ≈9,985.

2. **Nothing was lost.** For CLAUDE.md and each rules file, confirm the pre-edit version exists in
   the archive:
   ```bash
   git stash list; git diff --stat HEAD -- CLAUDE.md .claude/rules/ docs/
   ```
   and grep the archive for three distinctive strings from each deleted region.

3. **Every refutation survives.** This is the critical check. Before editing, capture the baseline:
   ```bash
   grep -o 'REFUTED\|SUPERSEDED\|DO NOT QUOTE\|Do not re-open\|must not be quoted' CLAUDE.md | sort | uniq -c
   ```
   After editing, every *distinct claim* behind those 36 markers must appear in the new CLOSED /
   REFUTED table (§1.2c) or in the compressed rules files. **The marker count will legitimately drop
   — the count of distinct refuted claims must not.** List them and tick them off by hand.

4. **Cross-references still resolve.** Every `docs/…` and `.claude/rules/…` path mentioned in the
   rewritten files must exist:
   ```bash
   grep -oE '(docs|\.claude/rules|analysis|src|tests)/[A-Za-z0-9_./-]+\.(md|py|h|cpp|json)' \
     CLAUDE.md .claude/rules/*.md | cut -d: -f2 | sort -u | while read f; do [ -e "$f" ] || echo "MISSING: $f"; done
   ```
   Expect hits for the files moved in §4 — fix those pointers, don't delete them.

5. **Discipline-file entry names are all still present.** Diff the list of entry names before and
   after; any name that disappears must be confirmed as a deliberate merge into a named survivor.

6. **`git status`** — confirm only `.md` files changed. If anything under `src/`, `tests/` or
   `analysis/` appears, back it out (Hard constraint #4).

---

## 6. Deliverables

1. Rewritten `CLAUDE.md` (≤700 lines).
2. Rewritten `.claude/rules/measurement-discipline.md` (≤750) and
   `.claude/rules/reference-sources.md` (≤250).
3. `docs/session-log.md` extended with the archived material (it will roughly double; that is fine
   and intended).
4. `docs/archive/` populated per §4.
5. **A "found in passing" list** in the final report — anything noticed that looks wrong but was NOT
   touched (stale constants in tools, broken cross-references, contradictions between two docs).
   Per Hard constraint #4 these are reported, never fixed in this pass. Known candidates already on
   record: `clean_headroom_bound.py` prints `kInputRef = 3.377` and `kOutputMakeup = 3.684`, neither
   shipped since s109/s115, and on that basis prints an "IMPOSSIBLE on this supply" verdict.
6. A one-paragraph note at the top of the new CLAUDE.md "Current step" recording that this
   consolidation happened, the date, and that the full narrative is in `docs/session-log.md` —
   exactly as session 89's reset did.

---

## 7. The structural rule that stops it regrowing

Session 89's instruction ("keep it short") failed because it gave no home for the material a session
legitimately produces. Add this to CLAUDE.md's own header, as a rule with a mechanism:

> **Per-session narrative goes to `docs/session-log.md`, NOT to CLAUDE.md.** A session may add to
> CLAUDE.md only: (a) a row in the SHIPPED CONSTANTS table, (b) a row in the CLOSED / REFUTED table,
> (c) an edit to the NEXT list, (d) an edit to STATUS. **All four are tables or lists with a fixed
> shape, and all four are edits rather than appends.** Everything else — the derivation, the gate's
> sub-gates, the defects found in the session's own instrument, the numbers that did not change a
> decision — goes to `docs/session-log.md` under a `## SESSION N` heading.
>
> If CLAUDE.md exceeds **800 lines**, the next session's first job is to re-archive before doing
> anything else.

That converts the growth from *append to a 5,000-line file* into *one row in a table*, which is the
actual fix. Consider also adding the 800-line check to a hook so it is enforced rather than
remembered.

---

## 8. Suggested execution order

Small, checkable steps; commit or checkpoint after each.

1. §1.6 — delete the 28 `Uncommitted at` blocks (archive first). **Biggest win per unit of risk**:
   −1,070 lines, and the content is provably reconstructible from `git`.
2. §1.2 — archive and rewrite `Where we are`. −2,370 lines. The CLOSED/REFUTED table is the careful
   part; budget most of the effort here.
3. §1.3, §1.4, §1.5, §1.7 — the remaining CLAUDE.md sections. −1,600 lines.
4. §7 — add the structural rule to the new header.
5. §2 — `measurement-discipline.md`. −1,050 lines.
6. §3 — `reference-sources.md`. −270 lines.
7. §4 — move the fulfilled `docs/`.
8. §5 — verification, then report with the §6 deliverables.

Steps 1–4 alone take the per-session load from ≈9,985 to ≈5,000. Steps 5–6 take it to ≈2,600.
