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
- **ctest 17/17** as of session 124. ⚠ Two tests were REPAIRED in session 124 and neither was a code
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
| the THD "level term"'s direction | **The gated term is UNSIGNED (rms).** Signed mean is **positive** — the model **over**-distorts, not under. | 109 | Any candidate reasoned about as "we need more distortion" is backwards. | `FitParams.h`, `analysis/shape_gate.py` |
| `s114_baseline.json` for absolute-ledger gates (K/M/O/P/Q) | **STALE** | 118/119 | Predates session 115's shipped `kOutputMakeup`/PWL-taper constants. GATE O refuses it by name. | `analysis/a3_decomposition_gate.py` |
| The six user-flagged peak/notch centre-frequency mismatches, **as CORNER (element-value) targets** | **CLOSED — none is a corner error.** ⚠ NOT "closed as a defect" — see the row below, added s125 | 122 | Two are the OD/clean mix (= A3, not a filter); three are not a fixed feature on at least one side; the 320 Hz null's centre is **right to 0.7%** — GAP #2 is a depth/width defect only, its centre was never wrong. ⛔ Do not point an optimiser at a capacitor for any of them. | `analysis/feature_locus_gate.py` (GATE W) |
| "the bass notch/peak are A3 seen as a frequency, so they need no separate work" | ⚠ **HALF TRUE — the bass PEAK is NOT A3, s125** | 125 | **Notch: consistent with A3** (both sides MIX, both vanish bleed-free, LEVEL loci **overlap** — model 53.2–64.2, pedal 38.1–54.4 Hz — so some mix balance reconciles them). **Peak: ranges are DISJOINT** — model 154.6–**165.5**, pedal **195.7**–208.9 Hz, the pedal's *lowest* **18.2 % above** the model's *highest*. LEVEL is the mix lever A3 acts through and its FULL travel moves the feature 6.6 % against a ~20–26 % gap ⇒ the lever is 3× too small, **and points the wrong way** (more OD ⇒ model 165.5 → 154.6 Hz, *away* from the pedal). ⇒ correcting A3 makes the bass peak **worse**. Same shape as s38's C12 locus argument. | `analysis/reports/s122_feature_locus.json` W4 |
| "…and therefore there is nothing to fix at those centres" | ⛔ **DOES NOT FOLLOW — REOPENED s125 as open-work item 6** | 125 | GATE W's verdict (c) *"not a fixed feature on at least one side"* is a **diagnosis, not an exoneration**: it says the pedal has a drive-dependent mechanism the model lacks. W6, measured: the model's treble peak is **FIXED to 0.2%** across the 24 dB ladder while the pedal's walks **2696 → 2498 Hz (7.9%)** ⇒ we are **281 Hz off at clean and 485 Hz (19.4%) off at `drv_-6`** — wrong at *every* drive setting. Same shape at the bridged-T (ours fixed 716 Hz, pedal 696 → 745 Hz). ⚠ The reassuring `1.022×` in s122's summary is `sweep_clean` on the LEVEL ladder only; the same feature reads `1.152×` on the pure-OD endpoints. | `analysis/feature_locus_gate.py` W6/W5/W5b |
| "the bass peak can be walked onto the pedal's by an OD-path LF constant" (the natural next move after s125 opened it) | ⛔ **REFUTED — no SINGLE constant does it, s126** | 126 | Every LF-shaping OD-path constant is a weak NEGATIVE lever (`\|S\| ≤ 0.178`, next 0.144/0.131, rest ≤ 0.058), against a required **+18.2 % to touch / +25.2 % to match** ⇒ a 4.8–5.6× move on an already-fitted constant. Two **do** reach when rendered (`trebleR7 ×0.21` → 205.9 Hz, `trebleC5 ×0.179` → 214.4) — and both **DISSOLVE the 320 Hz null (GAP #2) and the mid peak entirely** (prom 7.27 → 0.00 dB, 0 interior extrema in a 1.6×-widened window), i.e. they flatten the one centre GATE W says is right to 0.7 % and the one feature whose drive dependence already tracks. ⇒ compensating error, not a fix. ⚠ NOT refuted: a mechanism that is not one of these constants. | `analysis/bass_peak_locus.py` (GATE Y) Y3/Y5/Y7 |
| "the bass-peak gap is ~20–26 %" (s125, and every earlier statement of it) | ⚠ **THAT IS A `sweep_clean` NUMBER — the gap COLLAPSES with stimulus, s126** | 126 | Both sides from one capture: **+25.7 % (clean) → +24.0 → +18.1 → +6.4 % (`drv_-6`)**. So the defect is far more a quiet-stimulus phenomenon than a broadband one, and a lever must be quoted per rung: `trebleR7 ×0.21` closes it at `clean` and leaves **+21.6 %** at `drv_-12` (its own effect spans 2.1–25.6 % across the ladder). ⭐ Also the FIRST measurement of the model's own bass peak on this axis — **163.9 → 151.1 Hz, −7.8 %**, i.e. **DRIVE-DEPENDENT** by W6's own 5 % bar. GATE W6 reports it `UNRESOLVED` for a **membership** reason (W6 reads bleed-free endpoints; a mix cancellation has no reading there), never a physical one. | `analysis/bass_peak_locus.py` (GATE Y) Y6 |
| "memoryless ADAA does not apply to the CD4049 VTC — it lives inside an implicit solve, so state-space ADAA would be needed" (asserted in `PedalChain.h`, `FitParams.h`, `dsp.md` from session 6) | **REFUTED** | 123 | Conflates the STAGE (has memory) with the NONLINEARITY (`vtc` is memoryless in node W). ADAA1 needs a memoryless map with a ~linear argument; nothing requires that argument to be the stage input. Built and measured: **12.6–19.8 dB** median alias-floor gain at OS 1×/2×. Ships OFF (exact only at `clipK == 2`). | `analysis/clip_adaa_gate.py` (GATE X) |
| "ADAA only the NONLINEAR residue, keeping the linear part pointwise, to dodge ADAA1's 2-point-average cost in the feedback loop" | **REFUTED — do not re-invent** | 123 | Evaluates two halves of ONE map half a sample apart ⇒ injects a first difference of gain `a0/2`, reaching the **full loop gain at Nyquist**. H1 +13.4 dB hot, alias floor 14.4 dB worse than plain ADAA, whose own cost is 0.01 dB. | `Clipper.h::setADAA`, `ClipperTest` Test 8(e) |
| "ADAA1 imposes its own ≈ −48 dB alias floor (win above it, loss below)" | **REFUTED — my own s123 hypothesis** | 123 | Read off the worst-3-tones table; the ADAA arm's full spread is 51–84 dB, as wide as the baseline's. What survives: `corr(baseline, benefit) = −0.540`, and every costing cell had a baseline already better than −43.9 dB. | `docs/session-log.md` SESSION 123 |
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

Current ordering per session 124's own `▶ NEXT` (see `docs/session-log.md` for the superseded
orderings and why each item moved).

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
2. **THD level term** — one of 6 rows over SHIP (3.523 vs ≤3.0, full-send). Model **over**-distorts
   (signed mean positive) — do not reason about candidates as "add more distortion".
3. ⭐ **Perf: the `pow()` fast path is UNBLOCKED but NOT MEASURED.** `clipK = 2.0` restores
   `sig()`/`sigDeriv()`'s `k == 2.0` fast path — which was the entire perf argument for the
   re-anchor — but nobody has re-run `PerfBenchmark` against the clipper's recorded 356 ns/sample.
   That is a **measurement, not a change**, and it must be quoted before this item is called closed.
   ⚠ ADAA *adds* work at 1×/2× while the fast path removes it everywhere, so the net at the realtime
   factors is genuinely unknown — measure it, do not reason about it.
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
   | mid peak | 458 → 429 Hz (9.0%) | 447 → 419 Hz (8.0%) | ~2.5% — ✅ this one TRACKS |
   ⭐ **The mid peak tracking is the localising clue**: we already have a drive-dependent mechanism
   at ~450 Hz and none at ~2.9 kHz, so this is not a global missing dynamic — it is specific.
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
   nonlinearity, and must be gated on the mid peak NOT moving (it already tracks at ~2.5 %) and on
   CLEAN staying bit-identical (the clipper is OD-only).
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

✅ **Sessions 123–124 are COMMITTED** (one commit: session 123 built and measured ADAA, session 124
shipped it on the user's decision — they are one change and were committed together). Run
`git status --porcelain` for the live, authoritative state — do not transcribe it here
(`rebuild-targets-dont-transcribe`; the old per-session "Uncommitted at session N" blocks were
exactly this mistake, repeated 28 times, and are archived verbatim in `docs/session-log.md`).

Regenerable/gitignored, not part of any commit decision: `analysis/reports/*.json`,
`analysis/fit_logs/*.log`, `build/**`.

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
