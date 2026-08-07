# Release cleanup plan

> Goal: turn this repo from a **history store** into a **shipping product**. Three jobs:
> (1) absolute dilution of the accumulated learnings/logs, (2) total removal of every reference to
> the emulation used as the capture source, (3) generic learnings extracted to the template.
>
> ✅ **Job 3 is DONE** (see §0). Everything below is the plan for jobs 1 and 2. Nothing in §1–§8 has
> been executed.

---

## 0. Already done — template extraction

Landed in `../Guitar-Pedal-Plugin-Template`, uncommitted there:

| File | Change |
|---|---|
| `docs/nonlinear-component-modeling.md` | **NEW.** Generic: CMOS-inverter clippers, JFET/MOSFET gain stages, op-amp rails; sources, recommended models, the structural traps, and cross-cutting solver/ADAA/fitting rules. Verified free of project references. |
| `docs/measurement-discipline.md` | **NEW.** The generic core of this project's 3,218-line rules file, distilled to 680 (**D1, approved**): instruments & known answers, mutation-testing guards, thresholds, aggregates & membership, gates & verdicts, fits & degeneracy, mechanism screening, reading measurements, staleness, process. No session tags, no gate letters, no project numbers — verified. |
| `docs/refs/*.pdf` | **NEW.** 4 datasheets/papers the nonlinear doc cites (6.6 MB). |
| `.claude/rules/dsp.md` | Pointer at the top of "Nonlinear elements"; 4 new ADAA bullets + pointer. |
| `CLAUDE.md` | Both docs added to Essential Reading; parts-triage added to build-sequence step 1. |
| `README.md` | Both docs + `refs/` in the file map; triage added to "How to use it"; two entries added to "the things that bit us before". |

What was extracted (generic, no project mention): the current-source-not-voltage-source structure of
a degenerated common-source stage; finite CMOS open-loop gain as voicing; the supply-dropper
self-consistent rail solve; tanh-cannot-be-even-dominant; the cubic-sign/expansive-core finding;
monotonicity bounds must be scanned on the combined function; ADAA1 inside an implicit solve;
residue-splitting and quadrature refutations; `rtsafe` two-condition safeguarding; in-chain vs
synthetic convergence; one-step vs trajectory error; the "make the nonlinearity see less" degeneracy;
parameter-meaning-change hazard; anchoring a fitted exponent on a special-case value.

⚠ **Needs a commit in the template repo.** Suggested message: *"Add generic non-WDF-native component
modelling reference (CMOS clippers, JFETs, op-amp rails) + cited refs"*.

---

## Decisions needed before execution

| # | Question | Recommendation |
|---|---|---|
| **D1** | ~~The ~3,200 lines of generic measurement discipline — delete outright, or distil to the template first?~~ | ✅ **DECIDED AND DONE.** Distilled to `../Guitar-Pedal-Plugin-Template/docs/measurement-discipline.md` (3,218 → 680 lines). §3's row for this file is now an unconditional **delete**. |
| **D2** | Several shipped DSP constants were *deliberately* moved away from the captures toward third-party hardware trend data (`c21R`, `jfetSatNeg`, the `OdToneRestore` depth targets). Removing all reference-source discussion removes the *reason* they are what they are. | Keep a one-line neutral justification at each constant ("fitted/anchored to reference measurements") and delete the comparison framing entirely. No constant changes value. |
| **D3** | 206 scripts in `analysis/`, ~190 of which are one-shot session gates. | Keep the ~12-module reusable harness, delete the rest (§5). They are recoverable from git history if ever needed. |
| **D4** | Rewrite git history to purge the removed content, or just delete going forward? | **Just delete.** History rewrite breaks the audit trail and any clone; the working tree is what "not a history store" is about. Tag the pre-cleanup commit so the record is retrievable. |
| **D5** | `analysis/captures/` is 3.3 GB of the reference recordings, untracked and gitignored. | Out of scope for the repo (already ignored), but **move or delete locally** if the goal is that the material is gone. Your call — no repo impact either way. |

---

## 1. Pre-flight

1. Commit the current tree (CLAUDE.md, session-log.md, two analysis scripts are dirty).
2. `git tag pre-release-cleanup` — the one-line insurance policy that makes every deletion below
   reversible without keeping anything in the working tree.
3. Confirm baseline for the end-state verification: `ctest --test-dir build --output-on-failure -j 12`
   (expect 22/22) and an AU build + `auval`.

---

## 2. Delete outright — the history stores

These are session narrative, superseded handovers, and capture-request paperwork. Nothing downstream
reads them except CLAUDE.md's pointers (which §4 rewrites).

```
docs/session-log.md                    (1.7 MB, 21,567 lines)
docs/phase9-gap-log.md                 (728 KB, 9,932 lines)
docs/phase7-calibration-handover.md    (182 KB)
docs/doc-consolidation-plan.md
docs/clean-gate-split-handover.md
docs/final-capture-window.md
docs/phase7-handoff.md
docs/build-plan.md
docs/phase9-validation.md
docs/session53-capture-request.md
docs/session58-capture-request.md
docs/session59-capture-request.md
docs/session67-capture-request.md
.claude/rules/reference-sources.md     ← this file IS the capture-source doc; must go entirely
analysis/fit_logs/                     (73 tracked logs)
analysis/reports/                      (regenerable; keep only committed *.example.* if any)
image.png                              (3 MB stray screenshot at repo root)
.kilo/                                 (stale tool dir)
.DS_Store
```

**Survivors in `docs/`:** `calibration-and-gain-staging.md`, `validation-and-capture.md`,
`nonlinear-component-modeling.md`, `ui-peripheral-spec.md`, `refs/`, and this plan (delete this file
too once executed).

**Ripple:** `CLAUDE.md` has `@.claude/rules/reference-sources.md` in its import block; every rules
file and several source headers cite `reference-sources.md` by name. §3/§4/§6 clear those.

---

## 3. Dilute the rules files

Target: each file states **what to do**, not what was learned, when, or why-with-evidence. No session
numbers, no gate letters, no measured-value justifications, no ⛔/⚠/⭐ escalation ladders, no
refutation history.

| File | Now | Target | Action |
|---|---|---|---|
| `measurement-discipline.md` | 3,218 | **0** | **Delete** — the generic core is already in the template (D1, done). Nothing in the shipping product needs it. |
| `circuit.md` | 898 | ~350 | **Keep the component tables and node graphs verbatim** — that is the product's source of truth. Strip: every "session N verified/corrected" block, the capture-vs-document dissent narratives, the rail-solve derivation history, the correction-of-a-correction passages. Keep each `[ENG]` tag and one line of what it means. |
| `dsp.md` | 415 | ~250 | Keep the rules. Strip the session attributions, the measured-in-this-project numbers, the refuted-alternative narratives. Replace the CD4049/J201 pointers with a pointer to `docs/nonlinear-component-modeling.md`. |
| `build.md` | 267 | ~180 | Keep toolchain/layout/CI/test-parallelism rules. Strip session references and the "this cost us N minutes" framing. |
| `architecture.md` | 164 | ~150 | Nearly clean already. One capture-source reference to remove. |
| `ui.md` | 209 | ~200 | Nearly clean. Minor. |
| `reference-sources.md` | 323 | **0** | Delete (§2). |

Also: `.claude/agents/schematic-checker.md` and `dsp-validator.md` — check for pointers to deleted
files and to the capture source; repoint or trim.

---

## 4. Rewrite `CLAUDE.md` — 1,175 lines → ~120

This is the biggest single win and the file that most defines "history store". Delete wholesale:

- The **CLOSED / REFUTED** table (~90 rows) — the entire refutation archive.
- The **STATUS** block, every `SESSION N =` entry, every baseline/report reference.
- The **release gate** section (`analysis/release_gate.py`, bar tables, "9 rows over SHIP",
  the fallback trigger, the membership-weighting warnings) — this is a validation apparatus keyed
  entirely to the capture source.
- **Documentation discipline / re-archive** rules, the doc-size trigger, the read-order block.
- **Open work items 1–15**, including item 15 (blocked on more captures — removed per your
  instruction) and every reference to capture access, the capture inventory, and scarcity.
- The **SHIPPED CONSTANTS** table's *justification* column and provenance narrative.
- Cache/rebuild-state, uncommitted-work, and delegation-history blocks.

Keep, rewritten neutral (target shape):

```
# Obsidian-B7000 — Project Memory
  what it is (circuit-level B7K Ultra emulation, JUCE 8 + chowdsp_wdf) · author
## Quick reference          build / AU / test / format commands
## Schematics               pointer to circuit.md + the two agents
  @.claude/rules/{circuit,dsp,architecture,ui,build}.md
## Essential reading        the 4 surviving docs, one line each
## Architecture             the shipped signal chain, stage by stage, one line each
## Fitted constants         a plain table: constant | value | file  (no history, no why-not)
## Testing                  ctest 22/22, what each suite covers, the analysis harness
## Known limitations        2–4 neutral customer-facing lines (mirrors CHANGELOG)
## Open items               only genuinely-open, capture-free work (items 12 and 14's remainder)
```

⚠ **Item 14 carry-forward is real and should survive the cull**: `dist_engage` shipped with a 12 ms
crossfade, but the four selector switches (attack / grunt / loMidFreq / hiMidFreq) change topology
mid-block with no smoothing and are **reported, not gated**, in `SwitchTransitionTest`. That is a
product statement, not a session note — keep it in "Known limitations".

⚠ Also carry forward: the bit-identical-matrix check for the item-14 commit was set up and never
run. Either run it or drop the claim from `CHANGELOG.md`/commit message.

---

## 5. Cull `analysis/` — 206 scripts → ~15

**Keep** (the reusable harness + what tests/CMake reference):

```
README.md  gen_test_signal.py  analyze.py  captures.py  parallel.py
eq_reference.py  comprehensive_report.py  matrix_grade.py  shape_gate.py
fit_nonlinear.py  offline_render.cpp
```

Plus any script `CMakeLists.txt`, `tests/`, or `README.md` names — verify with a grep before
deleting, not after.

**Delete:** all `_mutate_gate_*.py` (39), all `*_gate.py` session gates, all `a3_*`, `attack_*`,
`od_*`, `clip*`, `master_*`, `level_*`, `notch_*`, `jfet_*`, `sk_*`, `bt_*`, `hf_*`, `null_*`,
`drive_*`, `bass_*`, `deficit_*`, `resonance_*`, `prominence_*`, `ladder_*`, `preclip_*`,
`task_e_*`, `thd_*`, `vertex_*`, `hw_trend_*` probes, the `.cpp` one-shot probes, the `.sh` scan
scripts, and the stray `.wav` files.

⚠ **`release_gate.py` goes with them** — it is the capture-source-referenced grading apparatus, and
every mention of "rows over SHIP" leaves the project with it.

⚠ Check imports before deleting: `feature_locus_gate`, `level_law_gate`, `od_absolute_gate` and
`a3_phase_solve` are each imported by 11–20 other scripts. Once those importers are gone the
modules go too — but delete in dependency order and re-run `python3 -c "import analyze, captures"`
style smoke checks after.

---

## 6. Purge the capture source from code and remaining docs

Every occurrence of the emulation's name, the `ND`/`HW` split, the authority framing, and
`reference-sources.md` citations.

| Location | Hits | Action |
|---|---|---|
| `src/dsp/FitParams.h` | 13 | Rewrite the `jfetSatNeg`, `c21R`, `levelTaper`, `masterTaper` comment blocks. Per **D2**: keep one neutral line per constant, delete the comparison narrative and every session tag. |
| `src/dsp/OdToneRestore.h` | 6 | Same: the `[ENG]` correction stays and stays documented as an engineered correction; the authority-and-depth-comparison passages go. |
| `.claude/rules/circuit.md` | 18 | Covered by §3. |
| `.claude/rules/dsp.md` | 6 | Covered by §3. |
| `.claude/rules/build.md` | 4 | Covered by §3. |
| `.claude/rules/architecture.md`, `ui.md` | 3 | Trivial. |
| `docs/calibration-and-gain-staging.md` | 3 | Neutralise — say "reference captures", nothing more. |
| `docs/validation-and-capture.md` | 10 | Keep the *method* (FR, swept-THD, null, knob tracking, capture protocol); delete what was captured and the authority split. |
| `docs/nonlinear-component-modeling.md` | 9 | **Delete this file from THIS repo** — its generic content now lives in the template. Repoint `CLAUDE.md`/`dsp.md` at the template copy, or keep a trimmed project-specific stub. |
| `README.md` | 2 | Neutralise. |
| `analysis/*.py` (32 files) | — | Mostly resolved by the §5 cull; sweep the survivors. |

⚠ Also purge, in the same pass: the whole "hardware vs emulation" authority concept wherever it
appears unnamed — phrases like "which reference governs", "the captures are not ground truth",
"moving toward hardware is a PASS". These carry the same story without the name.

**Verification grep (must return nothing):**

```bash
grep -rniE 'neural ?dsp|\bND\b|reference-sources|hardware vs|which reference' \
  --include='*.md' --include='*.h' --include='*.cpp' --include='*.py' . \
  | grep -v '^./build/'
```

---

## 7. Release-facing polish

- **`README.md`** — currently 200 lines with development framing. Rewrite as a product README:
  what it is, install, controls, build-from-source, licence. No phases, no gates, no validation
  history.
- **`CHANGELOG.md`** — already customer-facing (52 lines). Re-read the limitation wording so it
  states the limitation without implying a comparison to another product.
- **`CMakeLists.txt.template`** — template leftover at the project root; delete.
- **`presets/`, `ui/`, `schematics/`, `installer/`, `.github/`** — no changes needed.
- **`docs/release-cleanup-plan.md`** — delete this file as the last step.

---

## 8. Verification

1. `ctest --test-dir build --output-on-failure -j 12` → 22/22.
2. `cmake --build build --target ObsidianB7000_AU` → `auval` VALIDATION SUCCEEDED.
3. `python3 -c "import analyze, captures, comprehensive_report"` from `analysis/` → clean import.
4. The §6 grep returns nothing.
5. `grep -rn "session-log\|phase9-gap-log\|reference-sources\|release_gate" --include='*.md' --include='*.h' .`
   → no dangling pointers to deleted files.
6. Fresh-eyes read of `CLAUDE.md`: does it describe a product, or a research programme?

---

## Expected end state

| | Before | After |
|---|---|---|
| `CLAUDE.md` | 1,175 lines | ~120 |
| `.claude/rules/` | 7 files, 5,468 lines | 5 files, ~1,100 |
| `docs/` | 19 files, ~10 MB | 4 files + `refs/` |
| `analysis/*.py` | 206 | ~11 |
| Tracked files | 428 | ~230 |
| Capture-source references | ~1,250 | 0 |
