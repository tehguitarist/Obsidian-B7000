# Obsidian-B7000 — Project Memory  (from the pedal-plugin template)

> Obsidian-B7000 is a circuit-level emulation of the **Darkglass B7K Ultra** bass overdrive/DI preamp,
> built as an AU/VST3 plugin using JUCE 8+ and chowdsp_wdf. The schematic we have ("Black Mirror VII"
> by PCB Guitar Mania, rev 1.1v) is the ORIGINAL B7K clone; the Ultra-only features (Master volume,
> 3-way Attack, switchable mid frequencies) are **engineered on top of it** — see circuit.md [ENG] tags.
> Author/Company: Leigh Pierce

This project was scaffolded from a reusable template. The generic, hard-won engineering lives in
the rules + docs below — read them before writing DSP or UI. Replace every `<...>` placeholder.

## Quick reference

```
Build:  cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build
AU:     cmake --build build --target <Pedal>_AU     (auto-installs; bump VERSION to force Logic rescan)
Format: clang-format -i src/**/*.{cpp,h}
```

## Schematics

Put the schematic images in `schematics/` and load them whenever verifying a circuit detail.
`.claude/rules/circuit.md` is the source of truth for values/topology — fill it in first.

**Use the `schematic-checker` agent any time a circuit value or topology is in doubt; use
`dsp-validator` after any DSP stage change.** Both read `.claude/rules/circuit.md`/`dsp.md` —
keep those current and the agents stay useful with no extra setup.

> ⚠⚠ **BEFORE READING ANY CAPTURE-DERIVED NUMBER IN THIS FILE OR ANY DOC: `analysis/captures/` is a
> recording of the NEURAL DSP Darkglass plugin, NOT of a hardware B7K Ultra** (confirmed 2026-07-29).
> Every "the pedal" / "the real pedal" / "the captured unit" below and in `docs/phase9-validation.md`,
> `docs/phase7-calibration-handover.md`, `circuit.md` and the memory files means **the ND emulation**.
> ND is very close on the linear path (≤1.4 dB) and **~27 dB low on even-order harmonics**.
> **`.claude/rules/reference-sources.md` is the authority rule — read it before treating a capture as
> ground truth, and before calling a move away from the captures a regression.**

@.claude/rules/reference-sources.md
@.claude/rules/measurement-discipline.md
@.claude/rules/circuit.md
@.claude/rules/dsp.md
@.claude/rules/architecture.md
@.claude/rules/ui.md
@.claude/rules/build.md

## Delegation & model tiering

Plan with a high-end model, delegate execution down to cheaper ones — reserve the expensive
reasoning for the step that's actually hard to get right. As of July 2026 that means:

- **Planning** (build-sequence ordering, schematic-topology judgement calls, deciding what a
  session should tackle next) — a top-tier model at high effort (e.g. **Fable 5**, high effort).
- **Important thinking work** (circuit/DSP correctness: the `schematic-checker` and
  `dsp-validator` agents, anything cross-checking values/topology/taper against `circuit.md` or
  `dsp.md`) — a strong reasoning model at high effort (e.g. **Opus 4.8**, high effort). Both
  agents' frontmatter (`.claude/agents/schematic-checker.md`, `.claude/agents/dsp-validator.md`)
  are pinned to this tier — don't downgrade them to save cost, they're exactly the "important"
  category this policy protects.
- **Routine work** (mechanical edits, boilerplate scaffolding, formatting, running builds/tests)
  — a fast mid-tier model at medium effort (e.g. **Sonnet 5**, medium effort).

Re-evaluate the concrete model names as new ones ship; the tiering principle (plan high, validate
high, execute routine work cheap) is what should persist.

## Essential reading (template learnings — do not skip)

- **`docs/nonlinear-component-modeling.md`** — the ONLY two non-WDF-native parts are the **CD4049UBE
  clipper** and the **J201 JFET stage**; this doc has the datasheets/papers/SPICE + recommended
  modeling approach + the pre-DSP capture list for both (source PDFs in `docs/refs/`). Read before
  the nonlinear-stage build steps.

- **`docs/calibration-and-gain-staging.md`** — input-load (`kInputRef`) calibration, output-makeup
  calibration (level-match to captures — NOT a ~0.9 headroom pad; see §2), the DRIVE taper-floor
  bug, output-load (negligible), internal-vs-output clipping, op-amp rails, VU idle gate. This is
  where the non-obvious time-sinks are documented.
- **`docs/validation-and-capture.md`** — how to measure how close the plugin is to the real pedal
  (1/3-oct FR, continuous Farina swept-THD, sub-sample null, knob-tracking pass/fail) and how to
  CAPTURE the pedal so the measurement is trustworthy (bypass anchor, one-knob-at-a-time, sweep
  Volume, no truncation). The capture MATRIX, not the signal, is the usual limitation.
- **`analysis/`** — the reusable harness: `gen_test_signal.py` (comprehensive A/B signal) +
  `analyze.py` (load/align, FR, THD, Farina swept-THD, sub-sample null, filename parser).
- **`docs/ui-peripheral-spec.md`** — full visual spec for the reusable UI elements.
- **`src/ui/`** — drop-in `PedalLookAndFeel`, `VUMeter`, `ThreePositionSwitch`, `LEDIndicator`.
- **`src/utils/TaperUtils.h`** — taper helpers (note `audioTaperR0` for large gain pots).

## Build sequence (validate each step before the next — do not skip ahead)

1. **Schematic analysis** → fill `circuit.md`. Heed the schematic-reading gotchas there. Use the
   `schematic-checker` agent to cross-check any value/topology question against what's already
   captured, rather than re-reading the schematic image from scratch each time.
2. **CMake scaffold** — APVTS + AU/VST3 targets loading in a DAW.
3. **chowdsp_wdf smoke test** — trivial RC lowpass, confirm −3 dB point within 1% (offline/unit
   test, not a visual guess).
4. **Stage-by-stage DSP**, validated at each step:
   - Linear stages: frequency response vs expected transfer function.
   - Nonlinear stage: sine-clipping behaviour; confirm output polarity with a DC-step test.
   - Run the `dsp-validator` agent against each stage before moving to the next — it cross-checks
     component values, taper curves, and WDF topology against `circuit.md`/`dsp.md` for you.
5. **Switch topologies** — verify each position independently (precomputed scattering matrices).
   `dsp-validator` covers this too (topology + `setSMatrixData()` usage).
6. **Oversampling + ADAA** on the nonlinear stage — verify aliasing reduction. Use AccurateOmega
   (not chowdsp's default omega4). Add a separate render-time OS factor.
7. **Full-chain integration + level calibration** — anchor `kInputRef` from a real measurement;
   **calibrate output makeup to the reference captures** (may exceed 1.0; don't pad for headroom —
   calibration doc §2). Build an `OfflineRender` console exe mirroring `processBlock` for A/B.
8. **UI** — reuse the peripheral elements; design the centre pedal face per this pedal.
9. **Reference validation** — generate the comprehensive signal (`analysis/gen_test_signal.py`),
   capture the pedal per `docs/validation-and-capture.md`, and A/B with the harness: FR (1/3-oct),
   continuous swept-THD, null depth, knob-tracking pass/fail. Decompose any level deficit (§4)
   before changing constants.
10. **Final sweep** — all controls full range: no instability, clicks, or NaN/Inf. (Output > 0 dBFS
    at extreme drive+volume is faithful, not a fault — the output trim manages it.)

## Current step

> **RESET at session 89 (2026-07-31), at the user's request.** The previous version of this section
> was 6,914 lines of stacked per-session handovers; it is archived verbatim in
> **`docs/session-log.md`** and nothing was deleted. Keep this block SHORT — if it grows past ~120
> lines again, archive it and rewrite the summary.
>
> **Read order for a fresh session:** this block → `.claude/rules/reference-sources.md` (what the
> captures actually are) → `.claude/rules/measurement-discipline.md` (the hard-won traps) →
> `docs/phase9-validation.md` §0 (backlog). Per-session detail: `docs/session-log.md` and
> `docs/phase9-gap-log.md`.
>
> ⛔⛔ **CAPTURE ACCESS IS ENDING (session 111, 2026-08-02) — READ `reference-sources.md` §0's
> re-instated row AND "Project-specific carry-forwards" → "Capture access status" BEFORE assuming
> any capture not already on disk is obtainable.** If this session needs one, ask the user
> immediately, not "when convenient".

### Documentation discipline (added session 122, doc-consolidation pass)

> **Per-session narrative goes to `docs/session-log.md`, NOT to CLAUDE.md.** A session may add to
> CLAUDE.md only: (a) a row in the SHIPPED CONSTANTS table below, (b) a row in the CLOSED / REFUTED
> table below, (c) an edit to the NEXT list, (d) an edit to STATUS. All four are tables or lists with
> a fixed shape, and all four are **edits**, not appends. Everything else — the derivation, a gate's
> sub-gates, defects found in a session's own instrument, numbers that did not change a decision —
> goes to `docs/session-log.md` under a `## SESSION N` heading.
>
> If CLAUDE.md exceeds **800 lines**, the next session's first job is to re-archive before doing
> anything else. (Session 89's "keep it short, archive at 120 lines" instruction failed for 32
> sessions because it gave no fixed home for legitimate per-session output; this rule gives one.)
>
> **Session 122 consolidation (2026-08-03):** this file was 5,980 lines; the auto-loaded rules files
> totalled ≈10,000 lines read into every session before work begins. Compressed per
> `docs/doc-consolidation-plan.md`. The full per-session narrative for sessions 1–122 (and every
> "Uncommitted at session N" git-state snapshot) is now in `docs/session-log.md`, verbatim, nothing
> paraphrased or deleted. Every ⛔/⚠ refutation marker was preserved either in the CLOSED / REFUTED
> table below or in the compressed rules files.

### Where we are

**Phases 1–8 are COMPLETE.** The plugin builds, loads in a DAW, is fully playable, and the UI is
done. **Phase 9 (reference validation) is the only phase in progress**; Phase 10 (perf pass +
release) has not started.

#### STATUS

- **Current baseline: `analysis/reports/s124_ship.json`** (162 captures) — session 124 shipped three
  DSP constants (`clipK`, `clipAdaa`, `clipAdaaMaxOs`), so the baseline moved with them. Quote every
  OD number against this report. `s123_kship_control.json` is the diff-against control at the
  PREVIOUS constants (identical membership), and `s123_k2.json` is the known answer this baseline
  must reproduce (see below). `s120_newton.json` is the session-118→123 baseline, now superseded.
  ✅ **The baseline move carries a KNOWN ANSWER, and it PASSED: `s124_ship.json` reproduces
  `s123_k2.json` BIT-IDENTICALLY — 0 differing across 202,001 numeric leaves.** The matrix renders at
  `--os 8`, where the OS gate turns ADAA **off**, so the only shipped constant reaching an 8× render
  is `clipK = 2.0`; `s123_k2.json` was rendered with an explicit `--fit clipK=2.0` and `s124_ship.json`
  with none, so this simultaneously certifies that the constant reaches the DSP as a default and that
  no ADAA leaks into an 8× render. ⚠ This also means
  **the matrix cannot see the ADAA change at all**, by construction — do not quote a matrix number as
  evidence for or against ADAA. Its evidence is GATE X plus `OSValidationTest`'s in-chain benefit
  block, both at 1×/2×.
  ⚠ `comprehensive_report` now reports **172 attempted / 162 graded** — the 10-capture gap is the
  `_gain-n18` set failing on the missing `_GAIN_SESSION_MEASURED_DB[-18]` entry (open work item 8),
  NOT a membership change. A render log counts what it tried; only the report's capture list counts
  what it graded.
  ⛔ The absolute-ledger gates (K/M/O/P/Q) must be read against `s118_clampfix.json` or later — GATE O
  deliberately refuses any earlier report by name (session 119).
- ⚠ **Session 129 changed NO baseline, NO constant and NO `src/` file** — it read stored data only
  (`analysis/drive_locus_gate.py`, GATE AA, + its 7/7 mutation runner). `s124_ship.json` stands and
  the gate is still 6 rows over SHIP. Its two results are in the CLOSED/REFUTED table and both bear
  on open item 6. ⚠ It also flags an **unexplained `CMakeLists.txt` VERSION bump 0.5.0 → 0.5.1** that
  it did not make and deliberately did not revert — see `docs/session-log.md` SESSION 129.
- ⚠ **Session 130 likewise changed NO baseline, NO constant and NO `src/` file** — closed-form
  arithmetic on shipped constants only (`analysis/bt_pair_shape_gate.py`, GATE AB, + its 7/7 mutation
  runner). Its three results are in the CLOSED/REFUTED table and all bear on open item 6, which now
  has **two sized sub-targets** rather than one. ✅ **The session-129 `CMakeLists.txt` VERSION flag is
  DISCHARGED** — put to the user at the top of session 130, who confirmed 0.5.1 is intended; committed
  as-is. Nothing is owed there.
- ⚠ **Session 131 likewise changed NO baseline, NO constant and NO `src/` file** — it read
  `s124_ship.json` only (`analysis/hw_trend_gate.py`, **GATE AD**, + its 8/8 mutation runner).
  ⭐⭐ **It is the project's FIRST hardware-referenced gate.** `release_gate.py` is 100 % ND-referenced,
  so until now nothing mechanically distinguished "moved toward ND" from "moved away from hardware"
  — `reference-sources.md` §5 rule 2 said to make that distinction and only a human reading a rules
  file could apply it. GATE AD reports the LEAN per hardware trend and grades **sign and ordering
  only** (§5 rule 3: §3/§4 are PNG reads). Its four results are in the CLOSED/REFUTED table.
  ⛔ It covers the three FR trends and **NOT** §4's harmonic finding (hardware's evens ~27 dB above
  ND's), which is the largest hardware gap in the project and needs a harmonic instrument.
  ⚠ **An untracked `analysis/sk_gate_i_reconcile.py` claiming GATE AC was on disk at session start
  and is not session 131's** — it has no session-log entry. Flagged, not touched, not run.
  ✅ **This IS session 132's own tool** (a naming collision — two sessions ran in this repo at
  once; session 131 claimed that number first, so this work is filed as 132). See below.
- ⚠ **Session 132 likewise changed NO baseline, NO constant and NO `src/` file** — closed-form
  arithmetic on shipped constants, run against `s124_ship.json` only (`analysis/sk_gate_i_reconcile.py`,
  **GATE AC**, + its 7/7 mutation runner). It answers session 130's own `NEXT` #3, which explicitly
  gated its `NEXT` #1 (building an SK-bandwidth candidate) behind this reconciliation. Result in the
  CLOSED/REFUTED table. Also fixed a stale comment in `bt_pair_shape_gate.py` (`PEDAL_DPEAK`'s
  docstring said −7.92 %; the constant itself was always −7.34 %, the rung-1→rung-4 CHANGE, not
  AA6's max/min−1 SPAN — no number moved, only the comment was wrong).
- ⚠ **Session 133 likewise changed NO baseline, NO constant and NO `src/` file** — it read
  `s124_ship.json` plus 24 re-renders (`analysis/hf_null_presence_gate.py`, **GATE AE**, + its
  **10/10** mutation runner). It answers session 131's own `NEXT` #1. ⭐⭐ **It CONFIRMS AD5b's
  bleed-free reading and strengthens it past any threshold** — the model's window contains **NO
  interior extremum at all in 9 of 9 cells**, so the 0.69 dB was an inflection — **and it adds one
  qualifier that changes what kind of fix the item needs**: the model is not featureless there, it
  carries a MIX cancellation, so what we lack is ND's *drive-generated* null. Two rows in the
  CLOSED/REFUTED table; both bear on open item 6, and a third measurement lands on item 9.
  ⚠ Seven defects were found in the session's OWN instrument, one of them a **thread race inside the
  mutation runner** — see `docs/session-log.md` SESSION 133 before reusing any of that machinery.
- **ctest 18/18** as of session 127 (`PerfBenchmark` added — the 18th; ~54 s, `RUN_SERIAL`, and that
  serial property is load-bearing, not tidiness: it times wall-clock per sample, so a co-scheduled
  ctest job contends for the cores it is measuring. ⛔ Do not copy `RUN_SERIAL` to any other test as
  house style — `build.md` names this the ONE exception to "run tests in parallel, always".)
  ⚠ Two tests were REPAIRED in session 124 and neither was a code
  defect — both asserted premises the ADAA change inverted (`ClipperTest` (d) bound a claim about `k`
  to whatever shipped; `OSValidationTest`'s delay-comp check asserts factor-independence of a path
  the OS gate deliberately makes factor-dependent). Both repairs kept their original bars. See
  `docs/session-log.md` SESSION 124 before re-reading either as a regression.
- **Release gate: 6 rows over SHIP.** Run the script for the live numbers — do not transcribe them:
  ```bash
  /opt/homebrew/bin/python3.11 analysis/release_gate.py analysis/reports/s124_ship.json
  ```
  The six, unchanged through the session-124 re-anchor: OD 100 Hz–8 kHz p90, OD 25–100 Hz
  median/p90, OD 8–16.3 kHz p90, OD p99, THD level (full-send). See §"THE RELEASE GATE" below for
  the bar definitions and fallback.
  ⚠ **Session 128 fixed an inverted sign inside `shape_gate` and NO gated value moved** — the
  `SIGNED mean` lines the gate prints beside the THD rows flip sign, every graded rms is
  bit-identical (they take `abs`), and shape_gate selftest gate **2c** asserts exactly that
  invariance. So `s124_ship.json` remains the baseline and **no re-baseline is owed**; what changed
  is the *direction* the project quotes. See the CLOSED/REFUTED table and open item 2.
- Session 118's D1/D2 clamp-window fix and session 120's `rtsafe` solve are both **KEPT** (user
  decisions, taken at the top of session 120). Session 124's ADAA enable + `clipK` re-anchor is
  likewise a **user decision**, taken after the matrix price was measured.
- ⛔⛔ **CAPTURE ACCESS IS ENDING (session 111, 2026-08-02).** Read `reference-sources.md` §0's
  re-instated row and "Project-specific carry-forwards" → "Capture access status" before assuming
  any capture not already on disk is obtainable. If a session needs one, ask the user immediately.
- **Read order for a fresh session:** this file → `.claude/rules/reference-sources.md` (what the
  captures actually are) → `.claude/rules/measurement-discipline.md` (the traps) →
  `docs/phase9-validation.md` §0 (backlog). Full per-session narrative: `docs/session-log.md` and
  `docs/phase9-gap-log.md`.

#### SHIPPED CONSTANTS

One row per DSP constant/behaviour change since the session-89 reset. Full provenance for each
lives in the named source file's own comment block — **not duplicated here**.

| constant | was → now | session | why (one clause) | provenance |
|---|---|---|---|---|
| `c21R` | 220k → 130k | 91 | re-aimed at hardware LF anchor, not ND | `FitParams.h` |
| `jfetSatNeg` | 0.76054 → 1.9 | 91 | J201 low-drive even-order structure (hardware-authoritative) | `FitParams.h` |
| 17 treble/ATTACK-ladder constants | drawn values → fitted set | 100 | OD-path absolute-level fix (NOT a notch fix — GAP #2's notch is still unmet) | `FitParams.h` session-100 block |
| `kInputRef` | 1.2596 → 0.90 | 109 | degenerate-with-clip-ceiling lever; moves every nonlinear operating point at once; first change to close an OD gate row | `GainStaging.h` |
| `_GAIN_SESSION_MEASURED_DB[-12]` | 12.071 → 12.000 dB | 114 | four fresh linear twins + THD-turnover corroboration; corrects GATE K/M/O/Q absolute ledgers, invisible to the gain-matched matrix | `analysis/captures.py` |
| THD gate row | pooled → split by operating point (full-send / `gain-n12`) | 114 | pooling was flipping the verdict on the population the 3.0 bar was agreed against | `analysis/release_gate.py` |
| `kOutputMakeup` | 2.599 → 4.3297 | 115 | old anchor capture was 4.447 dB low (duplicated/mis-dialled, not clipped — GATE T) | `GainStaging.h` |
| MASTER taper | power law (`masterTaperExp`) → 2-segment PWL (`masterTaperBreak`/`masterTaperFrac`) | 115 | no single exponent fits the corrected ladder (span 1.74–3.51) | `FitParams.h`, `MasterOut.h` |
| D1/D2 clamp window | derived from fitted `satLo` (wrong meaning) → derived from `kTripPointV=2.657` (self-consistent rail) | 118 | fitted `satLo` is a knee scale, not the geometric trip point the window needs | `Clipper.h` |
| Clipper Newton solve | plain 6-iter Newton → bracketed Newton + bisection fallback (`rtsafe`), cap 12 | 120 | plain solve unconverged on 2.6% of in-chain samples at 4×/8×; closed the 8× alias floor by 36.6 dB and the headline OD gate row | `Clipper.h` |
| `clipK` | 2.4653 → 2.0 | 124 | the ADAA anchor (antiderivative elementary only at k=2) + restores the `pow()` fast path; matrix price measured FIRST and it is free — ⚠ "indistinguishable with a rounding preference", NOT "a better fit" | `FitParams.h` |
| `clipAdaa` | 0 (Off) → 1 (Full) | 124 | ADAA on the CD4049 VTC, enabled on the user's decision; ⛔ mode 2 (Residue) is REFUTED, not an upgrade | `FitParams.h`, `Clipper.h::setADAA` |
| `clipAdaaMaxOs` | *(new)* → 2 | 124 | OS-factor gate: ADAA on at 1×/2× (median −12.6…−19.8 dB, worst +3.3), off at 4×/8× (median collapses, worst +9.9/+17.3) | `FitParams.h`, `PedalChain::applyAdaaPolicy` |

#### CLOSED / REFUTED — do not re-open without reading the pointer

One row per claim a future session might otherwise re-measure or re-open. This is the load-bearing
table in this file.

| claim | status | session | reason | pointer |
|---|---|---|---|---|
| GATE J9's conditioned table (`level`, `gruntIdx`, `attackIdx`, `drive` as OD-residual levers) | **RETIRED, all four** | 108/116 | `gruntIdx` confounded with bleed (s108); `level` is dilution (s116); `attackIdx` 1.23× = not a lever; `drive` weak/non-monotone. ⇒ remaining OD error is **not localised on any control axis**. | `analysis/level_bleed_gate.py` (GATE U) |
| "GRUNT off-flat, 1.68–1.85×, GAP #3b" | **CLOSED** | 108 | GAP #3b dissolved s38 (no GRUNT cap reaches the target — C12 locus runs right-and-down, pedal sits right-and-up); the 1.68–1.85× is confounded with bleed via the refuted `blend=1.0` premise below. | `analysis/od_residual_localise.py` (GATE J) |
| "`blend = 1.0` is bleed-free" | **REFUTED** | 103 | Bleed vanishes only where BOTH BLEND and LEVEL are max (GATE K2). | `analysis/level_law_gate.py` (GATE K) |
| A3 = 5.1–5.5 dB over 100–400 Hz as a **fit target** | **REFUTED as a target; SIZE/attribution stand** | 108 | Window mean over a migrating feature; ±1.10 dB operating-point spread never printed; pedestal/feature split unmeasured. OD path is still quiet, absolutely — clean side bounded at 0.48 dB (re-quoted s119), deficit 4.38 dB. | `analysis/a3_pedestal_gate.py` (GATE P) |
| "the clean side is exonerated to 0.007 dB" | **OVERCLAIM — quote 0.48 dB** | 107/119 | 0.007 was the master-unity reading alone, on a different capture route/session; 0.41 (s107) was on the stale s99 baseline; re-quoted 0.48 on `s118_clampfix.json` (s119). | `analysis/a3_decomposition_gate.py` (GATE O) |
| "session 109's `kInputRef` broke GATE I" | **REFUTED** | 114 | The guard was wrong (asked the whole OD path to hold the rate of 2 of its elements), not the model. Rebuilt GATE I passes on every report s91–s113. | `analysis/hf_artefact_gate.py` (GATE I) |
| "ND's clean path is not level-invariant" (GATE O5's attribution) | **REFUTED** | 112 | 12.000 dB flat to 0.0003 dB across four fresh twins; the 0.334 dB tilt was one contaminated pair (`ref-clean.wav`). | `analysis/a3_decomposition_gate.py` |
| "even n12 clips at the top two MASTER detents" | **REFUTED** | 115 | Duplicated/mis-dialled capture (level constant across a 33 dB span of segment level, which clipping cannot produce), not a ceiling. `kOutputMakeup` was knob-corrupted by 4.447 dB. | `analysis/master_anchor_gate.py` (GATE T) |
| session 106's "`kOutputMakeup` is CONFIRMED RIGHT" | **REFUTED — circular** | 115 | Re-confirmed against the same capture it was fitted to. | `analysis/master_anchor_gate.py` |
| "a null whose depth grows with level, at DRIVE MAX" (head item for 7 sessions) | **MIS-STATED, stood down** | 117 | Names the end of the ladder where the pedal is flat (9.9 dB quiet-end collapse vs 3.1 dB driven-end deepening — opposite of what was claimed). Recommendation on record: treat as a symptom of GATE Q's "OD path saturates too early", not its own target. | `analysis/null_drive_plane_gate.py` (GATE V) |
| session 92's attribution of `OSValidationTest`'s failure to the un-ADAA'd CD4049 VTC | **SUBSTANTIALLY REFUTED** | 120 | It was the Newton solver's non-convergence, not (mainly) the VTC. ADAA remains open; session 92's alias/aperiodicity table was unquotable until re-measured — ✅ done s121: aperiodic regime **CLOSED (0/21 tones)**, genuine fold-down survives, smaller. | `analysis/alias_gate.py` |
| the THD "level term"'s direction, as recorded by session 109: *"signed mean is **positive** — the model **over**-distorts"* | ⛔⛔ **REFUTED TWICE OVER, s128 — the sign was a LIBRARY ARTEFACT, and there is no single sign to correct it to** | 128 | **(1)** `shape_gate.basis` took `np.linalg.qr`'s column signs as given; LAPACK returns `Q[:,0] = −ones/√n`, so `level_signed` was **−mean(d)** — a constant **+3 dB** residual was reported as **−3.0**. Every direction the project printed from s109 to s127 was **backwards** (`tilt_signed` happened to land right, `curv_signed` was also wrong — an inconsistency between three terms of one basis is the fingerprint of an unexamined convention). Fixed at the source; ⭐ **every gated rms is bit-identical** (they take `abs`), asserted by shape_gate selftest gate **2c**, so no baseline, report or verdict moved. **(2)** ⛔ And the corrected pooled sign is *still* not a direction: measured **convention-free** (the two raw THD percentages, no basis/projection/gain-match) the ratio runs **+4.47 dB at DRIVE 0 × the quietest rung → −4.21 dB at DRIVE max × the hottest**, crossing zero **inside** the graded pool, 3/3 monotone on each axis. ⇒ the model **over**-distorts when the clipper is pushed gently and **under**-distorts when it is pushed hard: a **slope error with a crossing**, not a level error either way. Quote the corner or the cell, never the mean. | `analysis/thd_locus_gate.py` (GATE Z) Z1/Z3, `analysis/shape_gate.py::basis` |
| "the gated THD row is a *distortion-generation* defect" | ⚠ **MOSTLY THE MIX, s128 — and the mix half needs NO new mechanism** | 128 | Split by the model's own clean fraction, the row reads **rms 2.201 = SHIP on the bleed-free rows** and **3.763 = over with bleed** (pooled 3.561). THD is harmonics/fundamental and the clean tap adds fundamental with no harmonics, so a mix difference moves it with **no change in distortion at all** — and the bleed dose-response is quantitatively what A3's already-measured OD-path deficit predicts: a one-parameter dilution law fits at **DF = −3.70 dB (interior, rms 0.56 dB over 4 classes)** against GATE O's independently measured **−4.38 dB**, i.e. **0.68 dB apart**. ⇒ same shape as s122's 1400 % THD cell (A3's cancellation read as a denominator). ⚠ **SUFFICIENCY, not identification** — any mechanism scaling the OD fundamental against its harmonics predicts the same curve. ⛔ **NOT a proposal to split the gate row** (Z6 prints and stops): bleed is continuous, the classes are unbalanced across DRIVE, and `cf` is the *model's* coefficient, not a measured property of the reference. | `analysis/thd_locus_gate.py` (GATE Z) Z5/Z6 |
| `s114_baseline.json` for absolute-ledger gates (K/M/O/P/Q) | **STALE** | 118/119 | Predates session 115's shipped `kOutputMakeup`/PWL-taper constants. GATE O refuses it by name. | `analysis/a3_decomposition_gate.py` |
| The six user-flagged peak/notch centre-frequency mismatches, **as CORNER (element-value) targets** | **CLOSED — none is a corner error.** ⚠ NOT "closed as a defect" — see the row below, added s125 | 122 | Two are the OD/clean mix (= A3, not a filter); three are not a fixed feature on at least one side; the 320 Hz null's centre is **right to 0.7%** — GAP #2 is a depth/width defect only, its centre was never wrong. ⛔ Do not point an optimiser at a capacitor for any of them. | `analysis/feature_locus_gate.py` (GATE W) |
| "the bass notch/peak are A3 seen as a frequency, so they need no separate work" | ⚠ **HALF TRUE — the bass PEAK is NOT A3, s125** | 125 | **Notch: consistent with A3** (both sides MIX, both vanish bleed-free, LEVEL loci **overlap** — model 53.2–64.2, pedal 38.1–54.4 Hz — so some mix balance reconciles them). **Peak: ranges are DISJOINT** — model 154.6–**165.5**, pedal **195.7**–208.9 Hz, the pedal's *lowest* **18.2 % above** the model's *highest*. LEVEL is the mix lever A3 acts through and its FULL travel moves the feature 6.6 % against a ~20–26 % gap ⇒ the lever is 3× too small, **and points the wrong way** (more OD ⇒ model 165.5 → 154.6 Hz, *away* from the pedal). ⇒ correcting A3 makes the bass peak **worse**. Same shape as s38's C12 locus argument. | `analysis/reports/s122_feature_locus.json` W4 |
| "…and therefore there is nothing to fix at those centres" | ⛔ **DOES NOT FOLLOW — REOPENED s125 as open-work item 6** | 125 | GATE W's verdict (c) *"not a fixed feature on at least one side"* is a **diagnosis, not an exoneration**: it says the pedal has a drive-dependent mechanism the model lacks. W6, measured: the model's treble peak is **FIXED to 0.2%** across the 24 dB ladder while the pedal's walks **2696 → 2498 Hz (7.9%)** ⇒ we are **281 Hz off at clean and 485 Hz (19.4%) off at `drv_-6`** — wrong at *every* drive setting. Same shape at the bridged-T (ours fixed 716 Hz, pedal 696 → 745 Hz). ⚠ The reassuring `1.022×` in s122's summary is `sweep_clean` on the LEVEL ladder only; the same feature reads `1.152×` on the pure-OD endpoints. | `analysis/feature_locus_gate.py` W6/W5/W5b |
| "the bass peak can be walked onto the pedal's by an OD-path LF constant" (the natural next move after s125 opened it) | ⛔ **REFUTED — no SINGLE constant does it, s126** | 126 | Every LF-shaping OD-path constant is a weak NEGATIVE lever (`\|S\| ≤ 0.178`, next 0.144/0.131, rest ≤ 0.058), against a required **+18.2 % to touch / +25.2 % to match** ⇒ a 4.8–5.6× move on an already-fitted constant. Two **do** reach when rendered (`trebleR7 ×0.21` → 205.9 Hz, `trebleC5 ×0.179` → 214.4) — and both **DISSOLVE the 320 Hz null (GAP #2) and the mid peak entirely** (prom 7.27 → 0.00 dB, 0 interior extrema in a 1.6×-widened window), i.e. they flatten the one centre GATE W says is right to 0.7 % and the one feature whose drive dependence already tracks. ⇒ compensating error, not a fix. ⚠ NOT refuted: a mechanism that is not one of these constants. | `analysis/bass_peak_locus.py` (GATE Y) Y3/Y5/Y7 |
| "the bass-peak gap is ~20–26 %" (s125, and every earlier statement of it) | ⚠ **THAT IS A `sweep_clean` NUMBER — the gap COLLAPSES with stimulus, s126** | 126 | Both sides from one capture: **+25.7 % (clean) → +24.0 → +18.1 → +6.4 % (`drv_-6`)**. So the defect is far more a quiet-stimulus phenomenon than a broadband one, and a lever must be quoted per rung: `trebleR7 ×0.21` closes it at `clean` and leaves **+21.6 %** at `drv_-12` (its own effect spans 2.1–25.6 % across the ladder). ⭐ Also the FIRST measurement of the model's own bass peak on this axis — **163.9 → 151.1 Hz, −7.8 %**, i.e. **DRIVE-DEPENDENT** by W6's own 5 % bar. GATE W6 reports it `UNRESOLVED` for a **membership** reason (W6 reads bleed-free endpoints; a mix cancellation has no reading there), never a physical one. | `analysis/bass_peak_locus.py` (GATE Y) Y6 |
| "memoryless ADAA does not apply to the CD4049 VTC — it lives inside an implicit solve, so state-space ADAA would be needed" (asserted in `PedalChain.h`, `FitParams.h`, `dsp.md` from session 6) | **REFUTED** | 123 | Conflates the STAGE (has memory) with the NONLINEARITY (`vtc` is memoryless in node W). ADAA1 needs a memoryless map with a ~linear argument; nothing requires that argument to be the stage input. Built and measured: **12.6–19.8 dB** median alias-floor gain at OS 1×/2×. Ships OFF (exact only at `clipK == 2`). | `analysis/clip_adaa_gate.py` (GATE X) |
| "ADAA only the NONLINEAR residue, keeping the linear part pointwise, to dodge ADAA1's 2-point-average cost in the feedback loop" | **REFUTED — do not re-invent** | 123 | Evaluates two halves of ONE map half a sample apart ⇒ injects a first difference of gain `a0/2`, reaching the **full loop gain at Nyquist**. H1 +13.4 dB hot, alias floor 14.4 dB worse than plain ADAA, whose own cost is 0.01 dB. | `Clipper.h::setADAA`, `ClipperTest` Test 8(e) |
| "ADAA1 imposes its own ≈ −48 dB alias floor (win above it, loss below)" | **REFUTED — my own s123 hypothesis** | 123 | Read off the worst-3-tones table; the ADAA arm's full spread is 51–84 dB, as wide as the baseline's. What survives: `corr(baseline, benefit) = −0.540`, and every costing cell had a baseline already better than −43.9 dB. | `docs/session-log.md` SESSION 123 |
| "the mid peak TRACKS (~2.5 %), so we already have a drive-dependent mechanism at ~450 Hz and none at ~2.9 kHz ⇒ the deficit is **specific**, not a global missing dynamic" (item 6's localising clue) | ⛔⛔ **NOT SUPPORTED — the clue is an ENDPOINT artefact of a NON-MONOTONE pair, s129** | 129 | `458 → 429` is rungs 1 and 4 of four; the interior goes **UP** first (467.4 at rung 2), making mid_peak the **only non-monotone model feature** in the resolved set — every other is flat to ≤0.6 %. **The pedal's is non-monotone too**, and elsewhere. Its GATE W5 across-condition range is **34.1 %, 11.4× the next widest** (3.0 / 2.4 / 0.8 %) — the least stable reading in the set. And "~2.5 %" is the endpoint error: per rung it is **+2.51 / +6.18 / +8.29 / +2.41 %**, so the feature excused as tracking is **8.3 % out mid-ladder, 3.3× the quoted figure**. ⇒ the model has **no resolved drive-dependent feature anywhere**; work item 6 as a **GLOBAL** deficit. ⚠ The 34.1 % is a RANGE (`max/min−1`), **not** an SD — no σ, no standard error, and the gate refuses to derive one. | `analysis/drive_locus_gate.py` (GATE AA) AA3/AA4 |
| "item 6's candidate is a frequency-dependent nonlinearity" — the class, unnarrowed | ⭐⭐ **NARROWED, s129: it must COMPRESS a feature pair, and every element-value-drift candidate is REFUTED on shape** | 129 | The two clean 4/4 dose-responses (pedal `bt_notch` **+7.15 % RISING**, `treble_peak` **−7.92 % FALLING**, model FLAT below the locator's resolution at both) are the notch and the recovery peak of **ONE network** (s125, closed form). They move **OPPOSITE** ways. Scaling every element of a linear network by `k` moves both by `1/k`, so their **ratio is invariant** — measured, it is **4/4 monotone falling, 3.876 → 3.352, −13.5 %**. ⇒ supply sag moving a corner, nonlinear junction capacitance, any effective-R/C drift: all predict an invariant ratio, all **refuted with no render and no threshold**. What remains is a **DAMPING / LOADING** mechanism. ⚠⚠ **PREMISE:** "one network" is proven for the MODEL and **ASSUMED for the pedal** — if its two features are different networks this weakens to an observation. Untested; the gate prints the caveat every run. | `analysis/drive_locus_gate.py` (GATE AA) AA6 |
| AA6's REASON — *"scaling every element by `k` moves both features by `1/k`, so their RATIO is invariant; it falls 13.5 % ⇒ element-value drift refuted"* | ⛔ **THE REASON IS REFUTED ON OUR OWN BASELINE, s130 — but the VERDICT survives on stronger ground** | 130 | The ratio is **not** invariant, because the peak is a **vertex** where the bridged-T's rise meets three rolloffs the drift does not touch (2 × SK + the clipper pole). Sized to deliver the pedal's own **+7.14 %** notch move, a pure bridged-T drift moves the ratio **−6.01 %** = **44.5 % of the pedal's −13.52 %**, where AA6 assumed 0.00. ⛔ ⇒ a screen written as *"the candidate must break the ratio invariance"* **would pass the refuted class**. ⭐ What DOES refute element drift needs no ratio and no threshold: the same drift moves the peak **+0.70 %, UP**, where the pedal's goes DOWN — refuted on **DIRECTION**. AB2's whole-cascade control shows the one configuration where AA6's premise holds (everything scales ⇒ both move by 1/k to 1e−7), and it is not any candidate mechanism. | `analysis/bt_pair_shape_gate.py` (GATE AB) AB2/AB4 |
| "the bt_notch and the treble_peak are two features of ONE network" (s125, carried into AA6 as its load-bearing premise) | ⚠⚠ **TRUE AS A CONSTRUCTION, FALSE ABOUT POSITION — the two axes are ~ORTHOGONAL, s130** | 130 | AB3 partitions every time constant in the s125 cascade, so each feature's sensitivity column must sum to **exactly −1** (a free known answer; measured **−1.0000** / **−0.9999**). It reads: **notch = −1.0031 bridged-T** and ~0 everything else; **peak = −0.7885 SALLEN-KEYS**, −0.1098 clipper pole, only **−0.1016 bridged-T**. ⇒ the peak's *position* is ~79 % the Sallen-Keys and ~10 % the bridged-T. The features share a construction and not a lever. ⛔ **Stop using "they are one network" as a step in an argument** — the model, where the construction is *proven*, already violates the conclusion drawn from it. (s129's separate caveat — that "one network" is only *assumed* for the pedal — is untouched and still open.) | `analysis/bt_pair_shape_gate.py` AB3 |
| "item 6's target is a single DAMPING / LOADING mechanism" (s129's narrowing) | ⚠ **TOO NARROW — it is TWO sized targets, s130** | 130 | Nothing in the cascade couples the two axes, so no single perturbation produces the signature: of the classes that carry the peak within a 4× knob move, the largest notch movement any drags along is **0.07 % against a required +7.14 %**. The 2×2 is well conditioned (**cond 1.30**) and the split is essentially unique: **bridged-T τ × 0.9337 (−6.63 %)** *and* **SK τ × 1.1113 (SK corners −10.01 %)**, verified by evaluating the combination (notch +7.15 vs +7.14, peak −7.21 vs −7.34). ⚠ Also `clipper a0` is admissible in sign AND reachable in size and is **still refuted**, on physical direction (sag *lowers* a0; s125 measured that walking the peak UP) — **sign-admissibility is necessary, not sufficient**. | `analysis/bt_pair_shape_gate.py` AB5/AB6 |
| "the hardware spectra show harmonics BELOW the fundamental — the pedal generates sub-fundamental content" (user observation on §4's three spectrum overlays, s131) | ⛔ **NOT A DEVICE MECHANISM — it is the recording's MAINS LADDER** | 131 | The hardware trace carries a ladder of bumps below its 997 Hz fundamental at **roughly CONSTANT absolute level across all three drive settings (~−100 / −96 / −95 dB)** while the fundamental itself climbs **−42 → −36 → −30 dB**. A drive-generated device mechanism must scale with drive; fixed additive noise does not. Spacing is a mains ladder (50 or 60 Hz base — a log-axis PNG cannot resolve which). The ND trace's own LF peaks sit ~120 dB below its fundamental, i.e. numerically irrelevant. ⇒ **do not model it, and do not re-open it from these PNGs.** ⚠ This is a PNG read and §3/§6's limits apply — it is "very likely rejected", not measured. The project has hit mains hum in a capture before (`docs/session-log.md` SESSION 39's hum-sensitivity de-gating). | `reference-sources.md` §4; `docs/session-log.md` SESSION 131 |
| "the model is drifting toward ND and away from hardware" (the risk §5 rule 2 exists to name, never measured until now) | ⭐ **MEASURED, s131 — and it is mostly NOT happening.** One inversion found, and it is NEW | 131 | GATE AD's first run: on the clean tilt (§2, the only section precise enough to fit against) **5 of 7 graded bands lean HARDWARE**, and **both hinges reproduce** (~65 Hz and ~2.7 kHz). ⚠ The LF bands are a **FRAME PIN, not evidence** — `c21R` was fitted to that anchor (s91), so they cannot certify the model (s119). The load-bearing result is the **one inversion: at 800 Hz–1 kHz hardware sits +0.32 dB ABOVE ND and we sit 0.21–0.27 BELOW it, so we are ~0.5–0.6 dB the wrong side.** Readable because the two independent clean routes agree on SHAPE to **0.148 dB** against GATE O's measured 0.30 dB route gap. **No open work item names this**; it is small and it is real. | `analysis/hw_trend_gate.py` (GATE AD) AD1/AD3 |
| "the model's OD low-mids are short of hardware by 5–9 dB, so §3's 150–250 Hz trend is a target of its own" | ⚠ **HALF OF IT IS ALREADY LEANING HARDWARE — the other half is A3, s131** | 131 | Split into a level-DEPENDENT and a level-INVARIANT half. **(a)** The absolute pedestal is 3.6–7.8 dB below ND at every GRUNT position ⇒ model→HW gap 5–9 dB, same direction everywhere, which quantifies §3's *"the two corrections compound, they do not fight"*. That half **is A3** and carries A3's whole caveat list. **(b)** The **GRUNT CONTRAST** (boost−cut; any common-mode gain cancels exactly) has the **SAME SIGN as hardware's in 6 of 6 driven cells** and a comparable size — ours +0.7…+2.3 dB wider than ND's against hardware's +2.8…+4.8. ⇒ **the GRUNT SPAN needs no work; the pedestal is the whole defect, and it closes when A3 does.** ⛔ Do not aim a GRUNT-side constant at this row (s38 already refuted the GRUNT caps for GAP #3b). | `analysis/hw_trend_gate.py` (GATE AD) AD4 |
| "the 4.5–6 kHz null is unresolved between references, so there is nothing to measure there" (§1's authority column reads *"Neither — unresolved"*) | ⭐⭐⭐ **THE AUTHORITY IS UNRESOLVED; THE DEFECT IS NOT. WE APPEAR TO HAVE NO NULL THERE AT ALL, s131** | 131 | Measured bleed-free across the driven ladder, both sides, same estimator: **ND's null depth RISES MONOTONICALLY with drive in 3 of 3 GRUNT positions** (spans **2.60 / 7.55 / 3.41 dB**; at GRUNT cut it runs 0.92 → 2.19 → **8.47 dB**), while **the model's is FROZEN — span 0.01 dB in all three, at 0.69–0.70 dB**. ⚠⚠ **Read that correctly: a prominence that is both tiny AND invariant to every control is the signature of NO FEATURE, not of a pinned one** (s126 — an extremum-finder always returns something). ⇒ this is **open item 6's sharpest instance anywhere in the project**, at the top of the band, and it is a presence/absence question rather than a centre-frequency one. ⚠ Grid limits: the report's bands are ~1/3 oct apart there, so the SHIFT the charts show is **not resolved** and the depths are LOWER BOUNDS — confirming "no feature" needs GATE W's locator, not this grid. ⛔ Nothing here is graded against hardware; §1 gives neither reference authority. | `analysis/hw_trend_gate.py` (GATE AD) AD5b |
| "item 6's SK sub-target (AB6: SK τ × 1.1113 across the drive ladder) and GATE I's 8–16.3 kHz gap are the same finding, or refute each other" (session 130's `NEXT` #3, gating its own #1) | ⭐⭐ **NEITHER — DIFFERENT MECHANISM CLASSES ON ONE SHARED KNOB, AND THE KNOB CANNOT CLOSE GATE I EVEN AT ITS LIMIT, s132** | 132 | The SK axis moves the treble-peak position **TOWARD** the pedal (−7.98 % vs a −7.34 % target) and the 8127.5→16255 Hz octave rate **AWAY** from it (−0.58 vs a required **+19.8…+21.5 dB/oct**, sign product −1) — **1 of 2 axes**, so a single SK mechanism cannot serve both; item 6's SK candidate is a *filtering* change, GATE I's gap needs a *generative* one (no lowpass chain can gain with frequency, which the pedal does). ⭐ **And the axis is bounded**: deleting both Sallen-Keys OUTRIGHT hands back only **+18.25 dB/oct**, still short of the hottest-rung requirement by **+1.57…+3.20 dB/oct** — 0 of 3 classes reachable at the hottest rung even at that limit (36 of 60 cells reachable across the whole ladder, all at the quiet end, per GATE I's own dose-response). ⇒ this **independently reproduces GATE I's own load-bearing property** (a fixed lowpass chain cannot gain with frequency) from a completely different construction. The bridged-T half of AB6 is nearly inert here (0.165× the SK half's collateral) — separable at this frequency exactly as AB3 found it separable at the features. ⚠ Collateral is a *mechanism size* on the closed-form linear cascade, not a priced render (the graded matrix sits downstream of a per-row null gain and the clipper). | `analysis/sk_gate_i_reconcile.py` (GATE AC) AC2–AC5 |
| "we appear to have NO 4.5–6 kHz null at all" (s131 AD5b, put at the head of its own NEXT list as the cheapest high-value read) | ⭐⭐ **CONFIRMED AND STRENGTHENED BLEED-FREE — AND IT NEEDS ONE QUALIFIER, s133** | 133 | On a grid **18× finer** the model's window (4200–12000 Hz, 1/48 oct) contains **NO INTERIOR EXTREMUM AT ALL in 9 of 9** bleed-free driven cells — its curve is strictly monotone there, which is a statement with **no bar in it** (AD5b's 0.69 dB was an inflection). ND has one in 6 of 9 over the 1 dB bar, deepening monotonically with drive in 3/3 GRUNT (spans **4.96 / 17.01 / 3.37 dB**). ⚠ **BUT the unconditional wording must be qualified**: on the LEVEL ladder the model DOES carry the feature (3 detents, prom 2.23/1.91/1.32 dB, verdict **MIX**), dying as the clean tap does — exactly s126's bass-peak membership situation. ⇒ **what we lack is ND's DRIVE-GENERATED null, not every feature there**; ours is a balance, theirs is a balance PLUS something the OD path generates. Presence/absence, not a centre or a depth. ⛔ Nothing graded against hardware (§1: authority = neither). | `analysis/hf_null_presence_gate.py` (GATE AE) AE3/AE4/AE5 |
| "the 4.5–6 kHz null" — the NAME | ⚠ **THE LABEL IS NOT THE WINDOW, s133** | 133 | Only **35 of 192** readings on either side fall inside 4.5–6 kHz; ND's centres run **6150 → 10708 Hz** across the LEVEL ladder. The name comes from `reference-sources.md` §3's PNG reads, whose exact conditions §6 says are unknown. ⇒ **quote the measured band, never the label** — and note GATE W has called this feature `treble_notch` with a 4200–12000 Hz window since s122. | `analysis/hf_null_presence_gate.py` (GATE AE) AE2 |
| `drive-1700_base-od @ sweep_drv_-6`, 50 Hz reading ~1400% THD | **RESOLVED — denominator artefact** | 122 | Model's 50 Hz fundamental collapses 41 dB below the pedal's (a cancellation-null read-point coincidence, same mechanism as the bass-notch/A3 row); numerator (harmonic energy) is ordinary on both sides. Not a distortion-generation defect; needs no separate work. | `analysis/feature_locus_gate.py` |

### THE RELEASE GATE

Phase 9 closes and Phase 10 begins when the SHIP column is met (agreed with the user, session 89).
Percentiles are over band values, OD ex `gain-n12` unless noted. **The gate is a script, not a
transcribed table — `analysis/release_gate.py`.** Run it; do not transcribe its output here:

```bash
/opt/homebrew/bin/python3.11 analysis/release_gate.py analysis/reports/s120_newton.json
```

It exits non-zero while any gated row is over, prints `n` beside every statistic, breaks the
reference dropouts and the `gain-n12` group out as printed subsets (never hidden), and takes
`--method csd|h1|h1band` / `--compare` to re-grade from the same renders, plus `--ex-gain-n12` to
reproduce the pre-session-111 membership.

**As of `s120_newton.json`: 6 rows over SHIP** — OD 100 Hz–8 kHz p90, OD 25–100 Hz median/p90,
OD 8–16.3 kHz p90, OD p99, THD level (full-send). OD band-RMS (the headline) and OD 100 Hz–8 kHz
median both meet their bars.

⚠ **The OD headline is membership-weighted** — it moves with the capture inventory's BLEND
composition, not only with the model (`release_gate.blend_composition()` prints this every run;
`aggregate-moved-check-membership-first`, session 112). Never diff two reports' OD numbers without
checking capture count and BLEND composition first.

⚠ **CLEAN is gated as two rows** (100 Hz–8 kHz and 8–16.3 kHz), not pooled — the pooled bar was
failing its own baseline on dilution (session 95/96). Both CLEAN rows currently SHIP.

▶ **Pre-registered fallback, not yet triggered:** if every other OD row closes and the two
8–16.3 kHz rows are the last blocker, split that region the way CLEAN was split (a real,
drive-independent defect vs a drive-generated tail) rather than loosening either bar. Trigger
is "everything else closed", not "this row is annoying" — re-run GATE I and reproduce its numbers
before acting. ⚠ p99 is 10.28 dB even with all four HF bands dropped, so the remaining OD error is
genuinely broadband and this region is not the p99 story.

⚠⚠ **CORRECTED SESSION 125 — THE PREVIOUS VERSION OF THIS BLOCK SAID "it is ND's own ALIASING
artefact… not ours to fix" AND CARRIED A ⛔ PROHIBITION ON WORKING THE REGION. GATE I DOES NOT SAY
THAT, AND ITS G3 REFUTES THE ONE ALIASING MECHANISM IT TESTED.** What GATE I actually establishes is
(G1) our clean-path linear HF is right, (G2) the pedal **gains** with frequency where our path rolls
off, with the gap growing monotonically with drive ⇒ **drive-generated, on the pedal's side**, and
(G3) it is **NOT** the `fs/(N+1)` fold mechanism — the excess passes through 16 kHz as a *smooth
plateau* (13.5–19.5 kHz mean +15.07 dB, spread 0.73 dB over 6 kHz), and a fold deposits a peak, not
a plateau. The gate's own printed verdict adds: *"NOT claimed: that the region is ENTIRELY artefact…
Whether the gate should still grade these bands is a **USER DECISION**, not this tool's."* The
gate's docstring also preserves the user's session-89 instruction verbatim: ⛔ *"DO NOT dismiss this
as 'ND aliasing' — that is not established and it is not a reason to skip the band."* The
prohibition inverted that instruction and converted a user decision into a standing rule.
⇒ **"drive-generated" ≠ "aliasing" ≠ "not ours to fix".** There is **no hardware data anywhere above
6 kHz under drive** (`reference-sources.md` §2 is clean-path only; §3's charts stop at the 5–6 kHz
null), so nothing adjudicates whether a real B7K also produces this. Treat the region as **open and
unattributed**, and see open-work item 6 — the model lacking a drive-dependent HF mechanism is a
live hypothesis for it, not a settled artefact.

### Open work, in order

Current ordering per session 128's own `▶ NEXT` (see `docs/session-log.md` for the superseded
orderings and why each item moved). ⚠ **The numbering below is historical and is NOT the priority
order any more** — session 128 demoted item 2 (it turned out to be items 6 and 9 seen on another
axis), so **item 6 is now the head item**. The numbers are kept because every rules file, gate
docstring and CLOSED/REFUTED row cites them.

0. ✅ **DONE, SESSION 126 — the bass peak is LOCALISED, and the single-constant route is REFUTED.**
   `analysis/bass_peak_locus.py` (GATE Y). Two CLOSED/REFUTED rows above carry the result; the
   short version is that every OD-path LF constant is a weak negative lever, the two that reach a
   +25.2 % move **dissolve GAP #2 and the mid peak**, and the gap being closed is itself a
   `sweep_clean` phenomenon that collapses to +6.4 % at `drv_-6`.
   ⭐⭐ **WHAT IT HANDS FORWARD, AND IT BELONGS TO ITEM 6, NOT HERE** (written as a numbered entry
   rather than a paragraph, per `closing-an-item-drops-its-successor`): **our bass peak is
   DRIVE-DEPENDENT too — 163.9 → 151.1 Hz, −7.8 %** — and so is the pedal's (7.8 %, W6). So the
   bass peak is *not* another "ours is pinned, theirs walks" case like the treble peak; **both
   walk, and they walk to different places.** That makes it a second instance of item 6's
   frequency-dependent-nonlinearity target, at the opposite end of the band from the treble peak,
   and it must be gated the same way: any candidate has to be checked at every stimulus rung, not
   at `sweep_clean` alone.
   ⛔ Do NOT re-open "point an optimiser at trebleR7/trebleC5/trebleC7" — priced and refuted.

1. ✅ **DONE, SESSION 124 — the user enabled ADAA, gated by OS factor, with `clipK` re-anchored to
   2.0.** Three constants shipped (SHIPPED CONSTANTS table above); two open items closed on one
   decision, since the re-anchor is both what makes ADAA exact and what restores the `pow()` fast
   path. ⛔ Do NOT re-open the "is the re-anchor affordable" question — it was measured on 162
   captures before shipping and is free (⚠ *indistinguishable with a rounding preference*, NOT "a
   better fit"). ⛔ Do NOT "simplify" the OS gate to an unconditional on: 4×/8× were measured and
   they lose (worst tone +9.9/+17.3 dB). See `docs/session-log.md` SESSION 124.
2. ⭐⭐ **THD level term — LOCALISED, SESSION 128 (`analysis/thd_locus_gate.py`, GATE Z), AND BOTH
   THINGS THIS ITEM SAID ARE NOW REFUTED.** Still one of 6 rows over SHIP (**3.561** vs ≤3.0,
   full-send, on `s124_ship.json`). Two CLOSED/REFUTED rows above carry the detail; what a session
   opening this item needs is:
   - ⛔ **Do NOT reason from a pooled sign in EITHER direction.** s109's *"the model over-distorts"*
     came from a QR-sign artefact and is fixed; and the corrected pool is still not a direction,
     because the **convention-free surface changes sign inside the graded pool**:
     | rung ↓ / DRIVE → | 0.0 | 0.5 | 1.0 |
     |---|---|---|---|
     | `drv_-18` | **+4.47** | +4.35 | −0.92 |
     | `drv_-12` | +2.83 | +1.43 | −2.95 |
     | `drv_-6`  | −1.36 | −2.64 | **−4.21** |
     (raw THD %, model vs pedal, bleed-free full send; 3/3 monotone falling on each axis;
     corroborated on the stored per-order harmonics, +2.88 → −0.32 dB, which shares no arithmetic
     with it.) ⇒ **the target is a SLOPE with a crossing, not an amount.**
   - ⭐ **The distortion-generation half already MEETS the bar** (bleed-free rms **2.201 = SHIP**);
     the over-bar reading lives in the rows carrying clean bleed (**3.763**), and that half is
     quantitatively A3's OD-path deficit seen through a ratio (DF −3.70 vs A3's −4.38 dB), so it
     needs **no second mechanism** — it closes when A3 does.
   - ⇒ **this item is now downstream of items 6/9, not independent of them.** The slope-with-a-
     crossing IS GATE Q's `D(f)`/GATE S's compression-slope error on a third instrument, and the
     bleed half is A3. ⚠ Whether that makes it worth *separate* work is a judgement for the next
     session; what is no longer true is that it is "the only gated row with an open lever of its
     own". ⛔ And do not aim a constant at the pooled 3.561 — no single offset can move a surface
     that changes sign.
3. ✅ **DONE, SESSION 127 — MEASURED, AND SESSION 124 IS THE LARGEST PERF WIN IN THE PROJECT: THE
   WHOLE CHAIN IS ~2× FASTER AT EVERY OS FACTOR.** `tests/PerfBenchmark.cpp` (new, registered with
   `add_test`, `RUN_SERIAL`, finite-only per `build.md` — timing is REPORTED, never gated). ⚠ Note
   `PerfBenchmark` **did not exist** until this session; session 120's 356 ns/sample came from a
   scratch probe long since deleted, so "re-run PerfBenchmark" meant "build it".
   **Full chain, ns per base sample, 48 kHz, BLEND=100 % OD, DRIVE=0.85 (run the test for live
   numbers — do not transcribe):**
   | factor | shipped | pre-s124 | pow fast path | ADAA on top | **s124 NET** | shipped × realtime |
   |---|---|---|---|---|---|---|
   | 1× | 225.0 | 437.8 | −58.0 % | +22.5 % | **−48.6 %** | 92.6× (1.08 % of a core) |
   | 2× | 475.8 | 911.1 | −55.7 % | +18.0 % | **−47.8 %** | 43.8× (2.28 %) |
   | 4× | 708.6 | 1653.9 | −57.2 % | **+0.08 %** | **−57.2 %** | 29.4× (3.40 %) |
   | 8× | 1297.4 | 3151.8 | −58.8 % | **−0.03 %** | **−58.8 %** | 16.1× (6.23 %) |
   ⇒ ADAA's cost is **+18…+22 % at the two gated-ON factors and ZERO to noise at 4×/8×** — the OS
   gate is doing exactly what it says, and that ±0.05 % is a free known answer (checksum-identical
   arms must also time identically). The fast path is **−56…−59 % of the WHOLE CHAIN**, so it dwarfs
   ADAA's cost everywhere and the net is a ~2× speed-up at every factor. Stage-level (clipper alone,
   384 kHz, comparable to s120's arm): **314.6 → 110.1 ns/sample, −65.0 %**.
   ⭐⭐ **AND THE ARITHMETIC CLOSES FROM BOTH ENDS, so the −65 % is the `pow` calls and nothing
   else:** a direct microbenchmark on this machine reads **11.97 ns per `std::pow`**, and the pow
   count per sample is 4 (initial `solveF`+`solveFp`) + 4 × ~2.9 iterations + 2 (final `vtcSub` for
   `y`) ≈ **17.6**, predicting **211 ns** against a measured **204.5 ns** — 3 %.
   ⚠ **Absolute ns/sample is machine- and run-specific** (this run reads arm 1 at 314.6 where s120
   recorded 356.59, −11.8 %, on a laptop three sessions later). **Only the within-run ratios are
   quotable**; the test says so in its own output.
   ⛔ Do NOT re-open "is the re-anchor worth it on perf grounds" — it is priced, and the price is
   negative by a factor of two.
   ⚠ (Historical, now moot: had `clipK` stayed at 2.4653, ADAA would have needed a general-k
   primitive — a Chebyshev fit of `psi(u) = Phi(u) − u` on `t = u/(1+u)`. ⛔ And NOT quadrature: the
   in-chain step-vs-knee table in `Clipper.h::setADAA` rules it out — the argument steps further than
   the whole knee on 57 % of samples at 2×, so fixed nodes land in saturation and miss the feature
   entirely. Keep that refutation: it applies to any future "just integrate it numerically" idea.)
4. **Re-point the other consumers of the corrupted MASTER anchor** — `clean_headroom_bound.py`,
   `clean_headroom_probe.py`, `clean_thd_check.py`, `captures.py`'s Tier-1 matrix list all still name
   `master-1700_gain-n12_base-clean.wav` (the capture GATE T proved 4.447 dB low). None currently
   carries a quoted number that matters (checked session 119), but any future use needs the
   correction from `master_anchor_gate.py`'s `detent_corrections()`.
5. **VTC-amplitude-vs-physical-rail inconsistency** — the model's VTC amplitude is fitted 5.4×
   below the physical rail (everything around it — TL07x rails, D1/D2 references, R19 — is
   physical). That is why the corrected D1/D2 window still fires on 0.05–0.25% of samples. A
   K/`clipSat` re-fit against a physical ceiling is the real repair (same job as item 4).
6. ⭐⭐ **THE MODEL LACKS A DRIVE-DEPENDENT MECHANISM ABOVE ~2 kHz — RESTORED s125, having been
   DROPPED in the s122→s124 handover chain.** ⛔ This is **not** a centre-frequency item: GATE W
   settled that none of the six flagged centres is a *corner* error, and that stands — do not point
   an optimiser at a capacitor. What it is: the pedal's HF features **move with drive** and ours are
   pinned, so we are wrong at every drive setting and the error grows with it.
   **Measured (`feature_locus_gate.py` W6, 24 dB stimulus ladder):**
   | feature | model | pedal | our error |
   |---|---|---|---|
   | treble peak | 2977 → 2983 Hz (**FIXED, 0.2%**) | 2696 → **2498** Hz (7.9%) | 281 Hz @ clean → **485 Hz (19.4%) @ `drv_-6`** |
   | bridged-T | 715.8 → 716.9 Hz (**FIXED, 0.2%**) | 695.7 → **745.4** Hz (7.2%) | crosses over |
   | mid peak | 458 → **467** → 448 → 429 Hz | 447 → 440 → 414 → **419** Hz | +2.51 / +6.18 / **+8.29** / +2.41 % |
   ⛔⛔ **THE "MID PEAK TRACKS" CLUE IS WITHDRAWN (s129) — AND WITH IT THIS ITEM'S "it is specific,
   not global" PREMISE.** The line here used to read *"458 → 429 (9.0%) | 447 → 419 (8.0%) | ~2.5% —
   ✅ this one TRACKS"* and concluded *"we already have a drive-dependent mechanism at ~450 Hz and
   none at ~2.9 kHz."* Both halves are endpoint artefacts of a **non-monotone** pair: the interiors
   are printed above, the model's goes **UP** before it comes down, and the error reaches **8.3 %
   mid-ladder — 3.3× the 2.5 % that excused it**. mid_peak is also the least stable reading in the
   set (across-condition range **34.1 %, 11.4×** the next widest). ⇒ the model has **no resolved
   drive-dependent feature anywhere**; treat the deficit as **GLOBAL**, and see the two
   CLOSED/REFUTED rows. ⛔ Do **not** gate a candidate on the mid peak in either direction — a
   candidate that "fixes" it is probably fitting noise.
   ⭐⭐ **AND A FOURTH FEATURE JOINED THIS ITEM IN s126, AT THE OTHER END OF THE BAND — THE BASS
   PEAK, WHERE *BOTH* SIDES WALK.** Measured on ONE capture, both sides, all four rungs (GATE Y's
   Y6 — not W6, which reads this feature `UNRESOLVED` on the model for a membership reason):
   | feature | model | pedal | our error |
   |---|---|---|---|
   | bass peak (`ref-od`, s126) | 163.9 → **151.1** Hz (7.8%) | 206.0 → **160.8** Hz (28.1%) | **+25.7 % @ clean → +6.4 % @ `drv_-6`** |
   ⇒ unlike the treble peak this is **not** "ours is pinned and theirs walks" — ours walks too, just
   **3.6× less far**, so the error is a difference of *rates*, not the presence-vs-absence of a
   mechanism. Same target class (a frequency-dependent nonlinearity), second location, and it gives
   the item a low-frequency anchor to gate candidates against.
   ⚠ Quote the condition: on the **bleed-free** endpoints W6 reads the pedal's bass peak at a 7.8 %
   span and non-monotone (195.7/199.0/186.7/201.3) — a different capture set at a different mix, so
   the two are not interchangeable.
   ⭐⭐⭐ **WHAT MAKES OUR 2980 Hz PEAK — LOCALISED s125, CLOSED-FORM, NO FIT.** It is the
   **recovery bridged-T's rise out of its own 716 Hz notch, rolled off by the two Sallen-Keys.**
   Cascading the schematic values (bridged-T nodal solve × SK 10.7k × SK 3.3k × the clipper's
   closed loop at the shipped `a0`) and vertex-interpolating in log-f gives **2934.8 Hz** against
   GATE W's measured **2977–2983 Hz — 1.5 %, with nothing fitted.**
   ⇒ **the treble peak is a pure POST-CLIPPER LINEAR feature, which is exactly why it is pinned to
   0.2 %** — it is downstream of every nonlinearity, so it *cannot* move with drive, by construction.
   ⛔⛔ **AND THAT REFUTES THIS ITEM'S OWN FIRST CANDIDATE, WITHIN THE SAME SESSION — dynamic R19
   supply sag acting through `a0`. IT MOVES THE PEAK THE WRONG WAY.** The claim written here first
   was that sag lowers `a0`, which walks the `C14 ∥ R18` corner *"at 1/(2π·330k·220p) = 2.19 kHz,
   i.e. exactly where the treble peak is"*. **Two errors, both caught by computing instead of
   reasoning:** (i) 2.19 kHz is the **bare** pole; the *closed-loop* corner is
   `[1/((1+a0)R16) + 1/R18] / 2πC14` = **6.29 kHz**, not 2.19, so it was never the peak's cause;
   (ii) that expression **rises** as `a0` falls, so sag moves the peak **UP** — measured
   `a0` 24.871 → 15 → 8 gives **2934.8 → 3025.8 → 3099.0 Hz**, while the pedal walks **down**.
   ⚠ Sag is not thereby dead as a mechanism for the *nonlinear* deficit; what is dead is the
   corner-shifting route and the 2.19 kHz coincidence. Do not re-derive either.
   ⭐⭐ **WHAT SURVIVES, AND IT UNIFIES THIS ITEM WITH A3.** GATE W reads centres off `transfer_h1`
   — the **fundamental**, harmonics rejected. So for the *pedal's* peak to walk with drive, the
   pedal's **fundamental transfer must itself be drive-dependent**, i.e. its compression is
   **frequency-dependent** where ours is closer to uniform. That is not a new defect: it is
   **GATE Q's `D(f)` (rms 3.01 dB, "only a nonlinearity can carry it") seen in the frequency
   domain.** ⇒ **the treble-peak walk and A3's untested dynamic half are the SAME finding on two
   instruments**, which is why they share this item. Any candidate must be a *frequency-dependent*
   nonlinearity, and must be gated on CLEAN staying bit-identical (the clipper is OD-only).
   ⛔ The old third gate — *"and on the mid peak NOT moving (it already tracks at ~2.5 %)"* — is
   **retired, s129**: the mid peak is unresolved, not tracking (see the table above).
   ⭐⭐ **THE GATE THAT REPLACES IT IS SHARPER, AND IT IS A SHAPE TEST (s129, GATE AA6): the
   candidate must COMPRESS the bridged-T's notch-to-recovery span by ~13.5 % across the ladder, not
   SLIDE it.** The pedal's `bt_notch` rises **+7.15 %** while its `treble_peak` falls **−7.92 %** —
   opposite ways, ratio 4/4 monotone **3.876 → 3.352**. A linear network scaled by `k` moves both by
   `1/k` and holds that ratio fixed, so **every effective-element-value candidate is already refuted**
   (sag moving a corner, nonlinear junction capacitance, any R/C drift). ⚠ Rests on "one network",
   proven for the model and assumed for the pedal.
   ⛔⛔ **AA6's ARGUMENT IS CORRECTED, AND ITS "look for a damping/loading mechanism" CONCLUSION IS
   SUPERSEDED (s130, GATE AB) — see the three CLOSED/REFUTED rows.** In one line: **the ratio is not
   invariant** (our own baseline breaks it by 44.5 % of the effect AA6 refuted on, because the peak is
   a vertex against rolloffs the drift does not touch), element drift is refuted on **DIRECTION**
   instead, and the two features turn out **~ORTHOGONAL** — the notch is ~100 % the bridged-T, the
   peak ~79 % the **Sallen-Keys**.
   ⭐⭐ **SO THIS ITEM'S TARGET IS TWO SIZED SUB-TARGETS, NOT ONE MECHANISM** (AB6, cond 1.30,
   verified by evaluating the combination):
   | axis | required move across the ladder | carried by |
   |---|---|---|
   | treble peak | **SK time constants × 1.1113** (SK corners **−10.01 %**) | the two Sallen-Keys, 79 % |
   | bridged-T notch | **bridged-T time constants × 0.9337 (−6.63 %)** | the bridged-T, ~100 % |
   ⭐⭐ **RECONCILED AGAINST GATE I, SESSION 132 (GATE AC) — NEITHER SAME MECHANISM NOR MUTUAL
   REFUTATION.** The SK axis moves the treble peak TOWARD the pedal and the 8–16.3 kHz octave rate
   AWAY from it (1 of 2 axes) — a filtering change can't be a generative one — AND the axis is
   bounded: deleting both Sallen-Keys outright hands back only +18.25 dB/oct against a
   +19.8…+21.5 dB/oct requirement at the hottest rung, short by 1.6–3.2 dB/oct even at that limit.
   See the CLOSED/REFUTED table (GATE AC). ⇒ **Work the Sallen-Key axis for the treble-peak walk
   as planned** — it still carries 79% of that feature and reconciliation found no conflict, only
   a bounded, quotable collateral cost in the (already-open, already-over-SHIP) HF region. Quote it
   whenever the candidate is built: −0.58 dB/oct and −3.10 dB at 16255 Hz at the hottest rung
   (2.7% of GATE I's own gap there). ⛔ Do NOT aim a single mechanism at the SK/bridged-T pair
   (AB3: orthogonal in this cascade). ⛔ Do NOT expect this candidate to move GATE I's gap — it
   is 36–46× too small on this axis and the two findings are different mechanism classes.
   ⭐⭐⭐ **TWO MORE INSTANCES JOINED THIS ITEM IN s131, ON A NEW AXIS — *DEPTH*, NOT CENTRE
   FREQUENCY** (`analysis/hw_trend_gate.py`, GATE AD; bleed-free, driven ladder, both sides, one
   estimator). Everything above is about where a feature SITS; these are about how DEEP it is, which
   no instrument on this item had looked at:
   | feature | pedal (ND) depth vs drive | model | ⇒ |
   |---|---|---|---|
   | bridged-T dip (~640–716 Hz) | **FALLS monotonically, 3/3 GRUNT positions** (spans 1.30 / 2.20 / 1.49 dB) | **pinned: 0.02 / 0.19 / 0.04 dB** | item 6's signature on the depth axis |
   | **4.5–6 kHz null** | **RISES monotonically, 3/3** (spans 2.60 / 7.55 / 3.41 dB; GRUNT cut 0.92 → 2.19 → **8.47**) | **FROZEN: 0.01 dB span in all three, at 0.69–0.70 dB** | ⚠⚠ **we appear to have NO NULL THERE AT ALL** |
   ⭐ A notch whose DEPTH collapses with drive is a **DAMPING / LOADING** change — the class AA6
   narrowed to, now corroborated from a statistic sharing no arithmetic with it. ⇒ **a candidate
   must compress a notch's depth with drive, not merely slide centres.**
   ✅✅ **THE 4.5–6 kHz ROW IS NOW MEASURED, SESSION 133 (GATE AE) — AD5b WAS RIGHT, AND THE
   CONCLUSION NEEDS ONE QUALIFIER THAT CHANGES WHAT A CANDIDATE MUST DO.** On GATE W's 1/48-octave
   locator the model's window holds **NO interior extremum at all in 9 of 9** bleed-free driven
   cells (threshold-free — the curve is monotone), against ND's 6 of 9 deepening monotonically with
   drive. ⚠ **But the model is NOT featureless there**: on the LEVEL ladder it carries a **MIX
   cancellation** (3 detents, verdict MIX) that dies with the clean tap, so AD5b read our side in
   the one condition where its feature cannot appear — s126's membership trap, again. ⇒ **the
   target is ND's DRIVE-GENERATED null: ours is a balance, theirs is a balance PLUS something the
   OD path generates.** A candidate that only re-tunes filters cannot address this row.
   ⛔ Do NOT re-open "is our prominence there really zero" — it is measured, with a synthetic
   known answer proving the estimator finds an injected notch at 1/3/9 dB and nothing at 0.
   ⛔ And nothing there is graded against hardware: `reference-sources.md` §1 gives the 5–6 kHz
   null to **neither** reference. ⚠ Also quote the MEASURED band, not the "4.5–6 kHz" label — see
   the CLOSED/REFUTED row.
7. ⚠ **Capture question, while access lasts:** a clean same-session `gain-n18` MASTER ladder would
   let session 115's taper be resolved below its 0.85 dB knob-noise floor (7 of 9 detents already
   captured session 120 — see "Capture access status" below for the accuracy caveat). Read
   `reference-sources.md` §0 first.
8. ⚠ **`captures._GAIN_SESSION_MEASURED_DB` has no −18 entry** — triply corroborated at 18.000 dB,
   deliberately NOT added (it would change graded membership; three `_gain-n18` captures currently
   fail `comprehensive_report`).
9. ⚠⚠ **FOUND DURING DOC CONSOLIDATION (session 122), STATUS AMBIGUOUS — flag to the user rather than
   assume closed.** *"The LEVEL law is a TOPOLOGY question — discriminate GATE L4's (a) [pedal's mix
   network differs structurally] vs (b) [something downstream of LEVEL in the pedal is
   level-dependent]"* was carried as an explicit open NEXT-list item from session 104 through
   session 111 (`docs/session-log.md` SESSION 104–111 blocks; `analysis/level_taper_gate.py`, GATE L)
   and then silently stopped appearing in the NEXT-list chain starting at session 112 — with no
   ⛔/REFUTED/CLOSED marker anywhere marking it resolved. It is **not** the same question as GATE
   U's "LEVEL is dilution, not a residual lever" (s116, closed) — that is about the OD-residual
   axis; this is about whether the LEVEL control's *own* absolute law (GATE K's 9.3 dB defect) is a
   structural mismatch or a level-dependent downstream stage. Neither GATE L4(a) nor (b) has been
   discriminated as far as this archive shows.
   ⭐⭐ **NEW EVIDENCE, s125, AND IT IS FREE — ALREADY IN `s122_feature_locus.json`.** Over the SAME
   7-detent LEVEL ladder the **pedal's bass notch is ~2× more LEVEL-sensitive than ours**: span
   **30.0 % (54.4 → 38.1 Hz) against our 17.2 % (64.2 → 53.2 Hz)**. Two mixers summing the same two
   paths must respond to LEVEL the same way, so a 2× difference in that sensitivity is a **direct
   measurement on L4(a) vs (b)** — and it is a *shape* question (how the cancellation locus moves),
   which the gain-matched matrix is not blind to in the way it is blind to L4's absolute 9.3 dB.
   ⇒ this item is now cheaper than it was: it has an instrument and a number, not just a question.
   ⭐⭐ **AND A SECOND, INDEPENDENT INSTANCE LANDED s133 (GATE AE, AE4) — OTHER END OF THE BAND,
   SAME SIZE.** Over the **4 LEVEL detents where both sides resolve it**, the `treble_notch`
   cancellation is **2.7× more LEVEL-sensitive on the pedal than on the model** (24.3 % vs 9.1 %) —
   the same shape and the same order as the bass notch's ~2×, on a different feature. ⇒ the
   L4(a)-vs-(b) discriminator is now measured **twice, on two features**, and both say the same
   thing. ⚠⚠ **MATCHED DETENTS ONLY — the raw spans read 9.1 % vs 133.5 %, and comparing THOSE is
   a membership difference wearing a physics number** (we mute at LEVEL min and lose the feature
   above LEVEL noon; ND keeps it nearly to the top). ⚠ Neither instance discriminates (a) from (b);
   what changed is that the item has two numbers on two features rather than one.

⚠ **A3 (item on this list since session 89) is compressed here but its exclusions must travel
together — this sentence is load-bearing, do not lose it:** *no single element closes A3 (s50), no
post-clipper linear element of ANY order does (s52), no GRUNT-side cap does (s38), its level is not
a fittable constant (s108), and its shape MIGRATES with stimulus so no fixed linear network can
produce it (s108 synthesis).* A3's SIZE and GATE O's attribution stand (see CLOSED/REFUTED table);
what is retired is only the idea of fitting a static correction to it. Full derivation:
`docs/session-log.md` SESSION 105–108 blocks.

⭐⭐⭐ **AND THE COROLLARY THAT WAS NEVER STATED, ADDED s125: EVERY ONE OF THOSE FIVE EXCLUSIONS IS A
*STATIC / LINEAR* EXCLUSION. A DYNAMIC MECHANISM HAS NEVER BEEN TESTED, AND THE EVIDENCE POINTS AT
ONE.** Read the list again — *element*, *linear element*, *cap*, *constant*, *fixed linear network*.
Nothing there rules out a stimulus-dependent mechanism, and *"its shape MIGRATES with stimulus"* is
the **signature** of one, not a reason to stop. The project has already measured this and then let
the summary line bury it: **GATE Q split A3's deficit into `L(f)` (rms 2.72 dB, a linear element
could carry it) and `D(f)` (rms 3.01 dB, of which its own source says *"only a nonlinearity can
carry it"*).** So a nonlinear target of **3.01 dB rms** has been sized since session 109 and appears
on no work list. `kInputRef` (s109) was the first move in that direction and is the only constant
ever to close an OD gate row. ⇒ **A3's honest status is "static excluded, dynamic UNTESTED"** — and
its most likely carrier is open-work item 6's dynamic-sag candidate, which is stimulus-dependent by
construction and sits in the OD path only, where A3 lives.

### Standing rules that must not be lost

- ⚠⚠ **`analysis/captures/` is a recording of the NEURAL DSP plugin, not hardware.**
  `.claude/rules/reference-sources.md` is the authority rule — read it before treating any capture
  number as ground truth, and before calling a move away from the captures a regression.
- ⭐ **The generalisable measurement traps are collected in
  `.claude/rules/measurement-discipline.md`.** ~190+ entries (merged/deduplicated session 122), each
  paid for by a real session.
- ⚠ Never quote a matrix total without its capture count; membership changes have faked a
  regression **eleven** times (`aggregate-moved-check-membership-first`).
- ⭐⭐ **THE 129/162-CAPTURE MATRIX IS BLIND TO ANY PURE LEVEL ERROR, AND ONE WAS 9.3 dB.**
  `comprehensive_report` fits a per-row broadband null gain before differencing anything, so
  band-RMS, every region median/p90, and the THD terms are all downstream of it. A control-LAW
  question (pot taper, divider end-stop, path-to-path balance) must be asked with a matched-pair,
  no-gain-match instrument (session 103's GATE K is the template) — the matrix must not be quoted
  as the arbiter of a level/law question, only of a shape/frequency one.
- ⭐⭐ **THE HF REGION (8–16.3 kHz) IS DRIVE-GENERATED AND ON THE PEDAL'S SIDE — WHICH IS QUOTABLE
  FROM A PASSING GATE. IT IS *NOT* ESTABLISHED AS ALIASING, AND IT IS *NOT* ESTABLISHED AS "not ours
  to fix".** `analysis/hf_artefact_gate.py` (GATE I, rebuilt session 114) passes on every report from
  s91 onward: at the hottest stimulus every one of the 15 pedal conditions **gains** with frequency
  across the octave and every one of the model's **rolls off** — complete separation, gap
  +17.44 dB/oct, with a monotone dose-response (a drive-generated mechanism must grow with stimulus;
  a fixed filter difference cannot). ⚠ **That is the whole of it.**
  ⛔⛔ **CORRECTED SESSION 125 — this entry previously read "IS ND'S OWN ARTEFACT" and ended "STOP
  AIMING MODEL WORK AT 8–16.3 kHz… not ours to fix". Both halves overstate the gate they cite.**
  GATE I's **G3 REFUTES** the `fs/(N+1)` fold mechanism at H2 (the excess is a smooth plateau —
  13.5–19.5 kHz mean +15.07 dB, spread 0.73 dB — where a fold deposits a localised peak), and the
  gate prints *"NOT claimed: that the region is ENTIRELY artefact"* and *"whether the gate should
  still grade these bands is a **USER DECISION**, not this tool's."* Its docstring carries the user's
  own session-89 instruction: ⛔ *"DO NOT dismiss this as 'ND aliasing' — that is not established and
  it is not a reason to skip the band."* The prohibition was the exact move that instruction forbade.
  ⇒ **Do not write "aliasing" for this region again without a measurement that names a mechanism.**
  A broadband HF plateau that grows with drive is equally the signature of *harmonic generation the
  model under-delivers* — and no hardware data exists above 6 kHz under drive to adjudicate. Open
  work item 6 carries the live hypothesis.

### Uncommitted work

✅ **Sessions 89–122 are ALL COMMITTED** — `df81360` (89–114), `9a0b255` (115–122) and `f927208`
(the doc-consolidation pass). Session 122's "sessions 115–122 are uncommitted" flag and its
"flag to the user" note are **discharged**; nothing is owed there.

✅ **Sessions 123–128 are COMMITTED.** Run
`git status --porcelain` for the live, authoritative state — do not transcribe it here
(`rebuild-targets-dont-transcribe`; the old per-session "Uncommitted at session N" blocks were
exactly this mistake, repeated 28 times, and are archived verbatim in `docs/session-log.md`).
Session 128 touched only `analysis/` and doc files (no `src/`), so it did not add to session 127's
cache-invalidation bill.

Regenerable/gitignored, not part of any commit decision: `analysis/reports/*.json`,
`analysis/fit_logs/*.log`, `build/**`.

⚠ **Session 127 relinked `OfflineRender` with a COMMENT-ONLY `FitParams.h` edit, so all 6501 entries
/ 133 MB of `analysis/reports/cache/` are unreachable and the next matrix run re-renders from scratch
(~25 min).** The DSP is bit-identical (verified: every changed line is a comment; ctest 18/18), so
`s124_ship.json` is still the correct baseline and **no re-baseline is owed** — budget the time, don't
go looking for a regression. `docs/session-log.md` SESSION 127 has the verification command.

## Project-specific carry-forwards

> Record decisions, measured constants, and open questions here as you go, so the next session
> resumes cleanly. Circuit facts ([ENG] list, supply/VD, clipper topology, non-WDF-native parts) are
> owned by `.claude/rules/circuit.md` — not duplicated here.

- ⛔⛔ **CAPTURE ACCESS STATUS, SESSION 111 (2026-08-02): THE USER IS LOSING ACCESS TO THE ND PLUGIN
  (the capture source).** `reference-sources.md` §0's "captures are unlimited, do not ration" claim
  is **re-instated to its pre-2026-07-29 scarce framing** until told otherwise. If a future session
  needs a capture not already on disk (`analysis/captures/`) or not in the inventory below, that is
  a **blocking question for the user, asked immediately** — not deferred, not assumed obtainable.
  ⭐ What IS decoupled and safe at any time: re-rendering `comprehensive_report.py`/any gate against
  WAV files already on disk. Only NEW captures need the plugin.
  - **Session 111 batch (26 new captures):** DRIVE ladder at `gain-n12` (5) · LEVEL×BLEND 3×3 matrix
    (9, fills GATE K6's matched-bleed gap) · MASTER ladder at `gain-n12`, remaining 5 of 9 detents ·
    EQ-0700 pairs at `gain-n12`, all four bands (4). Full detail + purpose: `docs/session-log.md`
    SESSION 111–113 blocks.
  - **Session 112 batch:** `level × blend` grid (12, intermediate BLEND) + a re-captured
    `grunt-boost_gain-n12` twin + the user's own `master-1100_grunt-boost` capture, plus two fresh
    `gain-n18` MASTER captures (`master-1545`/`-1700`) that resolved the ladder's pinned top end.
  - **Session 113 batch:** `drive-1700_level-1700_gain-n12_base-od.wav` (the head-item blocker,
    landed clean) + 8 unrelated EQ-hedge captures the user added independently against the closing
    window (bass/himid/lomid/treble at 9-o'clock/3-o'clock, `_base-od`) — unused so far, no claim
    about what they show.
  - **Session 120 batch:** the full 9-detent `gain-n18` MASTER ladder, 7 of 9 detents captured
    together (2026-08-03) plus 2 carried over from session 115/earlier. **User's own accuracy
    caveat, verbatim — do not drop this qualifier:** *"the positions are best estimates, so some
    variance is expected. I would say the 0700, 1200, 1700, 0930, and 1430 are somewhat the most
    accurate."* Not yet analysed — re-running `analysis/master_taper_makeup.py` against it is open
    work item 7 above.
- ⚠ **Two ear-matched (not measured) listening-test leads, volunteered session 120 ahead of losing
  physical pedal access — record as leads, not verdicts:**
  - **MASTER**: plugin needs ≈0.61 to match the pedal's loudness at whatever reference point was
    compared. Flagged, not concluded: 0.61 sits close to the shipped `masterTaperBreak = 0.5927`
    (~3% away) — worth checking per `an-implausible-coincidence-is-a-bug-report`, not yet checked.
    No new capture needed to quantify (open work item 10, `docs/session-log.md` SESSION 120).
  - **DRIVE/distortion**: plugin needs ≈0.8 to match the pedal's distortion at DRIVE max; tracks
    closely at DRIVE≈0.5. User-confirmed as saturation-based, not a separate gain-staging axis.
    Independently corroborates the standing head item (GATE Q/S: the model's OD path saturates
    differently, worst at DRIVE max) and is exactly what session 118's clamp fix targeted — open
    question whether the listening test predates or postdates that fix (open work item 11).
- **Two shipped bug fixes, pre-Phase-9 (2026-07-23):**
  - **Bypass-engage click** — `PluginProcessor::processBlock` had each channel step its own
    throwaway *copy* of `bypassMix`/`inputGain`/`outputGain` via `.getNextValue()`, so the member's
    real `SmoothedValue` state never advanced past the first block after a bypass toggle. Fixed by
    stepping each smoother once per sample into a shared per-block ramp buffer both channels read.
    `src/PluginProcessor.{h,cpp}`.
  - **Knob-turn zipper, worst on DRIVE** — `PedalChain::applyParams()` runs once per block (by
    design — its MNA stages only re-invert on a dirty flag); a fast knob sweep could jump the raw
    APVTS value a lot between blocks with zero interpolation. Fixed by smoothing the 8 continuous
    pots at knob-value level via `SmoothedValue::skip(numSamples)` on the member itself, ~20 ms.
    Switches (ATTACK/GRUNT/mid-freq/bypass/dist_engage) are unaffected — that's a separate,
    already-flagged, harder glitch-free-crossfade problem, still open (see `circuit.md`/
    `TrebleAttack.h`). `src/PluginProcessor.{h,cpp}`.
