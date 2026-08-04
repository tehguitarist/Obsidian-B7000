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
> If CLAUDE.md exceeds **1200 lines**, the next session's first job is to re-archive before doing
> anything else, compressing down to **under 800 lines**. (Session 89's "keep it short, archive at
> 120 lines" instruction failed for 32 sessions because it gave no fixed home for legitimate
> per-session output; this rule gives one. Trigger raised 800→1200, target held at 800, session 148 —
> the gap gives a session more room before compression is mandatory, without changing how compressed
> the file should be once it happens.)
>
> **Session 122 consolidation (2026-08-03):** this file was 5,980 lines and the auto-loaded rules
> files ≈10,000, read into every session before work begins. Compressed per
> `docs/doc-consolidation-plan.md`; the full sessions-1–122 narrative (and every "Uncommitted at
> session N" snapshot) is in `docs/session-log.md`, verbatim. Every ⛔/⚠ refutation marker was
> preserved, in the CLOSED / REFUTED table below or in the compressed rules files.

### Where we are

**Phases 1–8 are COMPLETE.** The plugin builds, loads in a DAW, is fully playable, and the UI is
done. **Phase 9 (reference validation) is the only phase in progress**; Phase 10 (perf pass +
release) has not started **as a phase**, though **2 of its 3 specified probes now exist** —
`PerfBenchmark` (s127) and `OSFidelity` (s144). ⛔ `FeatureProfile` is the third and s144 argues it
should NOT be built in its template form: its stated lever (accurate-omega vs `omega4`) **does not
exist in this pedal** — the omega provider belongs to chowdsp's diode models, and this chain's
nonlinearities are the CD4049 VTC and the J201 shaper — and its other candidate levers (the `pow`
fast path, ADAA's cost) were already priced at s127. If ever built it needs a new brief.

✅ **RE-ARCHIVED AT SESSIONS 136, 141, 143 AND 147**, every time on this file's own 800-line
trigger, and every time with each compressed passage verified present verbatim in
`docs/session-log.md` FIRST — which is the condition the discipline rule requires. What each pass
compressed: `docs/session-log.md` SESSION 136 / 141 / 143 / 147.
⛔ **The CLOSED/REFUTED and SHIPPED CONSTANTS tables have never been touched by any pass** — they
are the load-bearing content and compressing them is never the move. Compress narrative.
⚠⚠ **The structural cause is the one s136 named and s143/s147 hit again: open item 6 grows a
PARAGRAPH per session.** When that item gains a result, **add a row to its refuted table** (or edit
an existing gate), never a new paragraph to its body.

#### STATUS

- **Current baseline: `analysis/reports/s146_mastertaper.json`** (162 captures, identical membership
  to `s124_ship.json`). **Quote every OD number against this report.** Superseded, in order:
  `s124_ship.json` (s124's three clipper constants), `s123_kship_control.json` (the diff-against
  control at the PREVIOUS constants, identical membership), `s120_newton.json`.
  ✅✅ Both baseline moves passed a free known answer — s146 bit-identical to `s124_ship.json` on all
  14 gated cells, s124 bit-identical to `s123_k2.json` — **and s146's is only a result because its
  mutation control fired** (the fitted null gain moved −1.8621 dB on the 608 master=0.5 rows against
  a closed-form taper delta of +1.862, and 0.0000 at both endpoints); without that column, "the
  matrix did not move" is equally consistent with the constants never reaching the renderer.
  Derivations: `docs/session-log.md` SESSION 124 / 146.
  ⛔⛔ **`s124_ship.json` IS THEREFORE A STALE-EPOCH ARTEFACT FOR EVERY ABSOLUTE LEDGER** — 152 of its
  162 captures sit at master = 0.5, exactly where the taper moved 1.86 dB. The gain-matched matrix
  deletes a per-row scalar; **GATE K/M/O/P/Q do not.** ✅ GATE O6b's epoch guard refuses it by name
  and diagnoses it to 0.0002 dB, so the trap is guarded rather than merely documented. ⭐ A3 itself is
  untouched (MASTER is common-mode between clean and OD and cancels in its excess): GATE O re-reads
  **clean-branch bound 0.475 dB vs OD-path deficit 4.403 dB** against 0.48/4.38 on s118.
  ⚠⚠ **The matrix renders at `--os 8`, where the OS gate turns ADAA OFF, so it cannot see the ADAA
  change AT ALL** — never quote a matrix number as evidence for or against ADAA. Its evidence is GATE
  X plus `OSValidationTest`'s in-chain benefit block, both at 1×/2×.
  ⚠ `comprehensive_report` reports **172 attempted / 162 graded** — the gap is the `_gain-n18` set
  failing on the missing `_GAIN_SESSION_MEASURED_DB[-18]` entry (open item 8), NOT a membership
  change. A render log counts what it tried; only the report's capture list counts what it graded.
  ⛔ The absolute-ledger gates (K/M/O/P/Q) must be read against `s118_clampfix.json` or later — GATE O
  deliberately refuses any earlier report by name (session 119).
- ⚠⚠ **SESSIONS 129–145, 148 AND 149 CHANGED NO BASELINE AND NO CONSTANT, EXCEPT s144's NEW TEST.**
  Fourteen read-only gate sessions (GATES **AA**–**AN**, each a new gate over stored data or
  closed-form arithmetic on shipped constants, each with its own mutation runner — the tool file for
  each is the pointer column of its CLOSED/REFUTED row), plus s136/s143/s147 doc-only and s142 a
  premise audit.
  **Every result of all fourteen is a row in the CLOSED/REFUTED table below — that table, not this
  bullet, is where they are read.** Per-session narrative: `docs/session-log.md` SESSION 129–148.
  ⚠ **s148 also raised this file's own re-archive trigger 800 → 1200 lines** (target held at under
  800) at the user's request — see the Documentation-discipline block above; `docs/session-log.md`
  SESSION 147.4's "Headroom" paragraph is annotated STALE because of it.
  ⚠ s142 touched `src/` in **comments only** (`FitParams.h`, `Clipper.h`) and deliberately did not
  rebuild; **s144 BUILT** (see "Uncommitted work" for what that costs the render cache).
  ✅✅ **`know-when-to-stop-measuring` — flagged s141, fired s142, DISCHARGED s144** by the second of
  the two options it left open (*"land a `src/` change or take Phase 10's unbuilt probes"*):
  **`tests/OSFidelity.cpp` is built and is the 19th ctest.** No constant shipped — item 5's route is
  refuted on the pedal's own supply and every named carrier for item 6 is refuted, so there was none
  to ship. Its three results are CLOSED/REFUTED rows below.
  ⭐⭐ **AD is the project's ONLY hardware-referenced gate** — `release_gate.py` is 100 %
  ND-referenced, so until s131 nothing mechanically distinguished "moved toward ND" from "moved away
  from hardware"; AD grades **sign and ordering only** (`reference-sources.md` §5 rule 3). ⛔ It
  covers the three FR trends and **NOT** §4's harmonic finding (hardware's evens ~27 dB above ND's),
  still the largest hardware gap in the project and still needing an instrument nobody has built.
  ⚠ **Two carry-forwards from those sessions, both live:**
  - **Do not reuse s133's mutation machinery without reading `docs/session-log.md` SESSION 133** —
    seven defects were found in that session's own instrument, one a **thread race inside the
    mutation runner** (`parallel.pmap` is a `ThreadPoolExecutor`; a module-level injection flag
    leaked across workers). Now also in `measurement-discipline.md` §1.
  - ⭐ **Any pre-s120 reading of the drive-tilt axis was measuring the SOLVER, not the model** —
    AG's cross-baseline control found the model's drive-dependent HF slope span collapsing
    **0.830 → 0.100 dB/oct at s120**, i.e. `rtsafe` removed a spurious **non-monotone** slope of
    numerical origin worth **70 % of AF6's whole requirement**. The pedal side is bit-identical
    across all three baselines (same captures — a free known answer certifying the reference side).
- **ctest 19/19** as of session 146 (suite 70.2 s at `-j 12`). ⭐ s146 gave `MasterOutTest` a
  **Test 0** asserting the taper's own SHAPE — convexity (segment slopes must rise), monotonicity,
  exact endpoints, the A-taper 10–15 % half-rotation band — and widened its master set to six values
  covering all three segments AND both breaks (a segment-boundary off-by-one shows there and nowhere
  else). `OSFidelity` was added s144 (19th, 15.4 s, finite-only); `PerfBenchmark` s127 (18th, ~54 s).
  ⛔ `PerfBenchmark` is `RUN_SERIAL` because it times wall-clock per sample and a co-scheduled ctest
  job contends for the cores it measures — **do not copy that property to any other test as house
  style**; `build.md` names it the ONE exception to "run tests in parallel, always", and s144
  deliberately did not copy it to `OSFidelity`, which measures spectra.
  ⚠ Two tests were REPAIRED in session 124 and neither was a code defect — both asserted premises the
  ADAA change inverted, and both repairs kept their original bars. Read `docs/session-log.md`
  SESSION 124 before re-reading either as a regression.
- **Release gate: 6 rows over SHIP.** Run the script for the live numbers — do not transcribe them:
  ```bash
  /opt/homebrew/bin/python3.11 analysis/release_gate.py analysis/reports/s146_mastertaper.json
  ```
  The six, unchanged through the session-124 re-anchor: OD 100 Hz–8 kHz p90, OD 25–100 Hz
  median/p90, OD 8–16.3 kHz p90, OD p99, THD level (full-send). See §"THE RELEASE GATE" below for
  the bar definitions and fallback.
  ⚠ **Session 128 fixed an inverted sign inside `shape_gate` and NO gated value moved** (every graded
  rms takes `abs`; shape_gate selftest gate **2c** asserts that invariance) — so no re-baseline is
  owed; what changed is the *direction* the project quotes. CLOSED/REFUTED table + open item 2.
- Session 118's D1/D2 clamp-window fix and session 120's `rtsafe` solve are both **KEPT** (user
  decisions, taken at the top of session 120). Session 124's ADAA enable + `clipK` re-anchor is
  likewise a **user decision**, taken after the matrix price was measured.
- ⛔⛔ **Capture access is ending, and the read order for a fresh session** — both stated in full at
  the top of "Current step"; not repeated here.

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
| MASTER taper | 2-segment PWL → **3-segment** | 146 | the 2-seg family cannot be convex below its break, so pinning the one trusted knob position drove the bottom of the travel 1.4–3.4 dB hot | `FitParams.h`, `MasterOut.h` |
| `masterTaperBreak` | 0.5927 → 0.331781 | 146 | ⚠⚠ **CHANGED MEANING — now the FIRST of two breaks**; 4 consumers re-pointed, see CLOSED/REFUTED | `FitParams.h` |
| `masterTaperFrac` | 0.1137 → 0.056905 | 146 | fraction at the first break | `FitParams.h` |
| `masterTaperBreak2` / `masterTaperFrac2` | *(new)* → 0.659183 / 0.177468 | 146 | second break; segment slopes 0.172→0.368→2.413, convex, asserted by `MasterOutTest` Test 0 | `FitParams.h`, `MasterOut.h` |

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
| "a falling effective op-amp GBW under large signal is the obvious single physical cause of the SK half" (s130's named carrier for item 6's treble half, carried into two `NEXT` lists as the thing to build) | ⛔⛔ **REFUTED TWICE OVER, s134 — and the second half is immune to any datasheet number** | 134 | **(1) SIZE:** moving the peak −7.34 % needs a gain-bandwidth of **16.09 kHz**; TL07x ships **3.0 MHz typ / 2.5 MHz min**, so the requirement is **155× below the worst part TI sells**. At the real GBW the lever delivers **−0.025 %**. **(2) STRUCTURE, the stronger half:** gain-bandwidth is a **SMALL-SIGNAL** parameter — an op-amp in its linear region does not lose GBW as the signal grows; the large-signal limit is *slew*, a rate limit and not a bandwidth reduction. ⇒ there is **no amplitude at which this lever moves at all**, so the size arithmetic is moot. The sentence names a mechanism that does not exist. ⭐ Free by-product of the same sweep: the model's **ideal-op-amp assumption costs 0.025 %** at this feature, so nothing is owed to modelling finite SK bandwidth statically either. | `analysis/sk_mechanism_locus.py` (GATE AF) AF2 |
| "item 6's treble half is a Sallen-Key BANDWIDTH move" — AB6's `SK τ × 1.1113` read as a build instruction | ⛔⛔ **THE ARITHMETIC STANDS; THE MECHANISM IS REFUTED — 0 of 5 physical candidates reach, s134** | 134 | Screened in closed form on the shipped cascade, each quoted at the spread end WORST for the conclusion: falling GBW **0.0064** of what is needed, slew limiting **0.020** (worst \|dV/dt\| anywhere is **0.160 V/µs** against an 8 V/µs minimum-spec part — 50× margin, never engaged), output rail clamping **0.029**, op-amp input capacitance **0.023**, film-cap voltage coefficient **0.031**. ⭐⭐ The rail-clamp row is the sharpest and its answer was already on disk: `railEnabled = true` ships, so the model **already carries seven post-clipper amplitude nonlinearities**, two of them on the Sallen-Key outputs — and GATE W6 measured what all seven do to this peak across the 24 dB ladder: **0.21 %, verdict FIXED, 34× short**. A saturating clamp compresses the fundamental almost uniformly across frequency, and a uniform gain change **cannot move a vertex** (AB2's own control). ⇒ **the question was never "add a post-clipper nonlinearity".** ⛔ Do NOT build a drive-dependent Sallen-Key. ⚠ AB6 is unharmed: `SK τ × 1.1113` is a correct **SIZING** of how far the peak must move, not a claim that anything moves the SK corners. | `analysis/sk_mechanism_locus.py` (GATE AF) AF3–AF5, AF7 |
| item 6's treble half, stated in the right units | ⭐⭐ **IT IS A *SLOPE*, NOT A CORNER — SIZED, s134** | 134 | Every refutation above is about **corners**, and AB4 already established the peak is a **VERTEX** (the bridged-T's rise meeting three rolloffs). A vertex sits where the total slope crosses zero, so a drive-dependent **TILT** moves it with **no corner moving anywhere**. The vertex law `Δx = −T/C` turns AF1c's curvature (**−11.124 dB/oct²**) into a prediction with no fit in it: **predicted −1.223, measured −1.185 dB/oct, agreeing to 3.2 %**. ⇒ **a drive-dependent slope change of −1.185 dB/oct near 2935 Hz puts the peak exactly on target**, and it lives **at or UPSTREAM of the clipper**, not in the SK pair. ⚠⚠ **LOCAL number** — the curvature argument is strictly local; the broadband reading (**−7.49 dB over 100 Hz–8 kHz**, rms **2.16 dB**, i.e. **72 % of GATE Q's measured `D(f)` of 3.01 dB rms**) is an **assumption**, and an rms says nothing about whether `D(f)` is a monotone tilt at 2.9 kHz. ⭐ Cross-check: the same tilt moves the notch only **+0.83 %** against **+7.14 %**, so it is a **peak-only** lever — AB3's orthogonality reproduced from a third construction, and **the bridged-T half stays unowned**. | `analysis/sk_mechanism_locus.py` (GATE AF) AF6 |
| AF6's sized target — *"a drive-dependent −1.185 dB/oct slope change near 2935 Hz"* — is it actually CARRIED by the reference? (s134's own `NEXT` #1, the last thing separating item 6 from a build) | ⭐⭐ **YES — RIGHT SIGN, 1.72× THE REQUIRED SIZE, s135** | 135 | Measured as the two OPERANDS, not a delta (s117), at every rung (s129), on a quadratic-derivative estimator that recovers an injected tilt to **2.2e−14** (exact algebra, not a guessed bar). **MODEL slope pinned: span 0.094 dB/oct across the 24 dB ladder, and moving the WRONG way (+0.052/+0.021/+0.021). PEDAL: span 1.944, monotone falling 4/4 with ACCELERATING deltas (−0.210/−0.544/−1.190)**, monotone in 11/14 captures individually; the model's span is **0.048×** the pedal's. P−M = **−2.038 dB/oct**, same sign in **13/14**. ⇒ item 6's signature on a **THIRD axis** (position → depth → SLOPE), and the axis AF6 says the fix lives on. ⚠ The primary ±0.5 oct window (2075–4150 Hz) is the only one clearing BOTH neighbouring migrating features (GATE W's `bt_notch` tops at 1000, `treble_notch` starts at 4200) — asserted at AG1c before any slope is read, and true by only **50 Hz** at the top. | `analysis/drive_tilt_shape_gate.py` (GATE AG) AG3/AG5 |
| AF6's own flagged assumption — *"extrapolating it to a broadband tilt is an ASSUMPTION … whether the SHAPE matches is UNMEASURED"* | ⛔⛔ **MEASURED, AND THE ASSUMPTION IS WRONG — IT IS NOT A UNIFORM TILT, s135** | 135 | Over the only three centres whose whole window clears both features, PEDAL−MODEL drive-tilt runs **−0.39 / −0.78 / −1.44 dB/oct at 1613 / 2032 / 2560 Hz — monotone STEEPENING at −1.58 dB/oct per octave**, and the same difference continues −2.8/−5.5/−8.5 at 3225/4064/5120 Hz (same direction, but those windows reach ND's treble notch per GATE AE, so reported as a trend and **not counted**). ⇒ **a candidate delivering a CONSTANT drive-dependent tilt would land on target at one frequency and be wrong at the others by a growing amount — that whole class is refuted before it is built.** The mechanism must be frequency-dependent, not a tilt knob. ⚠ **n = 3 uncontaminated centres — a direction, not a broad measurement.** | `analysis/drive_tilt_shape_gate.py` (GATE AG) AG4 |
| "a drive-dependent tilt fixes the treble peak" — the move AF6 sized, read as sufficient | ⚠⚠ **NOT SUFFICIENT — POSITION AND SHAPE CANNOT BOTH BE FIXED BY A PURE TILT, s135** | 135 | AF6's vertex law applied to the pedal's OWN measured tilt (−1.944 dB/oct) with the model's curvature predicts a **−11.4 %** peak walk against GATE W6's measured **−7.3 %** — same sign, over-predicting **1.55×**. Reproducing the pedal's walk from its own tilt needs **C = −17.66 dB/oct² against our −11.12, i.e. the pedal's peak is ~1.6× SHARPER than ours.** ⇒ **giving the model the pedal's full measured tilt OVERSHOOTS the peak target**; a candidate must be gated on position AND shape, which is cheap. ⚠ The −17.66 is a division of two ratios and the pedal's vertex has never been fitted on a 1/48-oct grid — an implication, not a measurement (open item, s135 `NEXT` #2). | `analysis/drive_tilt_shape_gate.py` (GATE AG) AG6 |
| AG6's implied **`C_pedal` = −17.66 dB/oct²** — the number item 6's "position AND shape" gate rested on | ⭐⭐ **MEASURED, s137 — DIRECTION CONFIRMED, SIZE REDUCED, and AG6's 1.55× turns out to be TWO effects** | 137 | Both sides fitted on **one** estimator on GATE W's 1/48-oct locator (AG6 could not: its `C_model` was AF1c's **closed-form** cascade while its walk was a property of the **rendered** model — two different objects). Measured **`C_model` −10.903 / `C_pedal` −14.674, ratio 1.346×**; over the usable fit windows `C_pedal` runs −12.780…−14.674, i.e. **17–28 % short of −17.66**, and the pedal is sharper at **every** usable window. ⭐ The decomposition closes from both ends: AG6's **1.5533×** (rescaled to the rendered `C_model` → 1.5848×) = **(curvature ratio 1.3459) × (the vertex law's own residual on the pedal 1.1954) = 1.6089×, agreeing to 1.5 %** ⇒ **the pedal's vertex really is 1.35× sharper AND the vertex law itself over-predicts by a further 1.20×** — which **AG4 already predicts**, the law being a *local* linearisation against a tilt that is not uniform. Attributing all of it to curvature is exactly how −14.67 became −17.66. ⚠⚠ **Quote it with its bar and n**: the prominence bar sits in a **dense region, not a gap** (cells 127/115/6/0 at 0.5/1.0/2.0/4.0 dB), so no bar is assertable and AH4b re-measures at each — **0.5 dB → n=15, −12.845, 1.179×** vs **1.0 dB → n=8, −14.674, 1.346×**. Direction survives both. ⚠ The MODEL row is **UNRESOLVED by construction** (predicted +0.601 % vs measured +0.194 % walk, both under the locator's resolution) — the law cannot be tested on our side at all, which is item 6's own premise, not a defect. | `analysis/vertex_curvature_gate.py` (GATE AH) AH4/AH5/AH4b |
| item 6's carrier on the **pre/at-clipper** side, starting with the mechanism the model **already ships** — the CD4049's incremental gain `a0` sagging with drive | ⛔⛔ **REFUTED TWICE OVER, s138 — on SIGN CONSISTENCY (the stronger half) and independently on SIZE at a limit past any physical sag** | 138 | `a0` moves the response two ways at once: the closed-loop pole rises as `a0` falls (**brighter**) while the input impedance `Zf/(1+a0)` rises and drags the GRUNT coupling cap's high-pass corner down (**darker**) — so **which wins depends on the coupling cap, and the mechanism's SIGN FLIPS WITH THE GRUNT SWITCH**: at `a0 → 1` it delivers **cut −0.498 / flat +0.974 / boost +1.061** dB/oct. **The defect does not flip** — measured per capture on GATE Q's 16 endpoints with AG5's estimator, PEDAL−MODEL is **cut −2.407 (9/9 negative) / flat −1.913 (3/3) / boost −1.098 (3/4)**, i.e. the same sign at all three positions, **15/16 captures**. ⇒ right sign at **1 of 3**, and it pushes the defect FURTHER at the other two. ⭐ And where the sign IS right it reaches **20.7 %** of what that position needs — at `a0 = 1`, which is not an operating point but a limit (a shunt-feedback stage there has no gain left), so the ceiling holds for **any** excursion. ⭐⭐ Cheap because the tilt operator is **linear on log-magnitude**, so every `a0`-independent block — the treble/ATTACK ladder, IC2_A, the bridged-T, both SKs — **cancels EXACTLY from the tilt CHANGE** (asserted at 1.3e−15 dB/oct against a deliberately wild fixed block, not argued): **no render was needed**. ⚠ Session 17's `clipa0_grunt_corner_probe.py` "A0 is ruled out", quoted in `FitParams.h`, is about the **LF GRUNT corner and H3−H2 at ~220 Hz** — scoped, not inherited; this re-asks it at the vertex. ⚠⚠ **SCOPE: this refutes ONE class.** Still UNSCREENED on this side: the **J201's Miller/junction capacitance**, **IC2_A's GBW and slew**, the **GRUNT caps' voltage coefficient**. | `analysis/at_clipper_tilt_gate.py` (GATE AI) AI2–AI5 |
| "AG6 mixed two instruments (GATE Q's 1/3-oct band surface for the tilt, GATE W's 1/48-oct locator for the walk), so its arithmetic may not be safe" | ⭐ **CORROBORATED — the mixing is safe AT THIS FEATURE, s137** | 137 | The identical quadratic-derivative estimator on the 1/48-oct transfer (49 points, ~14× the sampling, a different H1 window) gives P−M drive-tilt **−2.290 dB/oct** against AG5's **−2.038** — same sign, difference 0.252 ≤ ½\|AG5\|. Free by-product: the model's **pinned** tilt (+0.021 span) and the pedal's **monotone 4/4 acceleration** (−1.807 → −4.077) both reproduce on an instrument sharing no bands with AG's. ⚠ Scoped to this feature; it licenses no general mixing of the two instruments. | `analysis/vertex_curvature_gate.py` (GATE AH) AH6 |
| GATE Q's `D(f)` rms = **3.01 dB** — quoted in this file, in `reference-sources.md`'s A3 chain, and imported by GATE AF as the denominator of its "72 %" | ⚠ **STALE (s109-era) — the current value is 2.64 dB, and the conclusion STRENGTHENS** | 135 | GATE Q on the three valid baselines reads **2.53 / 2.65 / 2.64 dB** (s118 / s120 / s124); 3.01 predates s115's constants and s118's clamp fix, and the absolute-ledger gates were never allowed to be read against s109 anyway. AF6's 2.16 dB is therefore **82 %**, not 72 %, of the measured drive-dependent term. ⛔ Do not re-quote 3.01. GATE AG prints the restatement every run. | `analysis/drive_tilt_shape_gate.py` AG7 |
| item 6's **three remaining pre/at-clipper carriers** — the J201's Miller/junction capacitance, IC2_A's GBW and slew, the GRUNT caps' voltage coefficient (AI's own printed UNSCREENED list) | ⛔⛔ **ALL THREE REFUTED, s139 — so EVERY NAMED CARRIER ON BOTH SIDES OF THE CLIPPER IS NOW REFUTED** | 139 | **J201 Miller:** ⛔⛔ **THIS ROW's STATED REASON WAS REFUTED s149 — the |A| < 1 clause is FALSE on the shipped ladder; the SIZE refutation and the shape bound below both stand.** It read *"\|A\| = 0.565 < 1, so the Miller factor is 1.565 and the candidate reduces to the bare junction capacitance"*, computed with `Zin_ladder` taken from the **DRAWN** treble values; on the shipped fit **\|A\| = 2.778 > 1** and the Miller factor is **3.778**, so there IS multiplication to modulate. Re-quote: the budget needs **388.3 pF** against **8.17 pF** at 2.5× the part's datasheet max = **47.5× short** (was quoted 80×), and the reach at that ceiling is **bit-identical at 0.17 %** — it is read at an absolute 10 pF ceiling, which never touched `zin`. ⭐⭐ **And it is refuted on SHAPE by an argument that generalises past it:** every "a capacitance grows with drive" mechanism is one real pole whose corner moves, for which `d ln\|dT\|/d ln f = 2/(1+u) ≤ **2 EXACTLY**`; AG4's deficit steepens as **f^2.84** (adjacent pairs 2.99 / 2.69, gated on the weaker). ⇒ **no single moving pole can carry this, at any size.** **IC2_A:** GBW is a **small-signal** parameter so no amplitude moves it (AF2, **inherited** — a fact about the part, not the stage; 11× short on size besides); slew carries a **12× margin AT THE VERTEX** on a full-rail square wave. **GRUNT V-coeff:** a falling cap moves the tilt **POSITIVE at all three positions** where the defect is negative ⇒ **0 of 3 on sign**, independent of film-vs-ceramic. ⚠ Refuted is a list of **named carriers**, not the existence of a mechanism; AG5's deficit is untouched (**1.72×** the requirement). ⚠ AJ2c is **n = 3 centres**. | `analysis/pre_clipper_tilt_gate.py` (GATE AJ) AJ2–AJ5 |
| item 6's LAST unscreened pre-clipper carrier — the **J201's SHAPER as a TILT mechanism** (s139's own `NEXT` #1(b); AJ refuted the J201's *capacitance*, a different carrier) | ⛔⛔ **REFUTED ON ALL THREE ROUTES, s140 — so the named-carrier search is exhausted INCLUDING the J201's nonlinearity** | 140 | `JfetStage.h` makes the stage a **current source** (`Gm = gm/k`, `Rout = ro·k`, open-circuit `Gm·Rout = gm·ro` FLAT), so the shelf acts only through LOADING — which splits the candidate into three. **(1) The shaper AS SHIPPED:** memoryless ⇒ its incremental gain is a **scalar**, log-magnitude gains a constant, tilt unchanged **below 1e−14 dB/oct at any compression to 40 dB** — AB2's control, no threshold. **(2) gm SAG through `k(s)`** (the nonlinear-degeneration coupling the Wiener-Hammerstein model omits, and says so): reaches **2.46 % of budget at `gm → 0`**, a limit at which a JFET has no transconductance left. ⭐⭐ And refuted far harder **on SHAPE, by an argument sharper than AJ2c's bound** — the deficit **RISES** with frequency (+2.989/+2.693 adjacent pairs) while the mechanism **FALLS** (**−1.884/−1.926**): not merely under the exact `≤+2` single-pole bound but **on the wrong side of ZERO**, strongest where the deficit is weakest. **(3) amplitude-dependent compression** (the shaper is driven *through* the shelf, so it sees a frequency-dependent level — route 2 does not model this): bounded **for ANY shaper shape** by the shelf's own variation across the window, `dG/dA ∈ [−1,0]` ⇒ **0.0274 dB/oct = 2.29 % of budget**, so no re-fit of `s`/`a`/ceiling can move it. ⭐⭐⭐ **COMMON ROOT CAUSE:** the shelf's corners are the **zero at 219.2 Hz** and the **pole at 291.6 Hz** — **both a decade below the 2935 Hz vertex** — which is why two routes computed completely differently agree to 0.2 pp. ⭐⭐ **AND THE METHODOLOGICAL RESULT: this carrier PASSES item 6's GRUNT-sign gate 3/3** (the J201 is upstream of the switch and tilt is linear, so its contribution is GRUNT-independent — asserted at **1.07e−14**) unlike `a0` (1 of 3) and the GRUNT V-coeff (0 of 3), **and is still refuted** ⇒ **sign-admissibility is NECESSARY, NOT SUFFICIENT**; a screen built on sign alone would have passed it. ⚠ SCOPE: this is the J201 as a **tilt** mechanism at the vertex — it says nothing about its **even-order harmonic** role (`reference-sources.md` §4, still live). | `analysis/j201_shaper_tilt_gate.py` (GATE AK) AK2–AK5 |
| GATE AI's flat/boost GRUNT caps | ⚠ **DEFECT FOUND AND FIXED, s139 — VERDICT UNCHANGED** | 139 | AI read `clipC12`/`clipC13` **raw** (47.00 / 220.0 nF) where `Clipper::gruntCap()` composes **ADD-caps** (`Flat = c11+c12`, `Boost = c11+c13` → 50.69 / 223.69 nF). Re-run at both cap sets and diffed: `cut` **bit-identical**, `flat`/`boost` move **≤0.009 dB/oct**, every reach and sign unchanged, and AI3's defect column **bit-identical** (caps do not enter it) — two free known answers, both held. Composed in one place (`grunt_caps()`) so the raw reading cannot return. ⇒ **AI's refutation stands.** | `analysis/at_clipper_tilt_gate.py::grunt_caps` |
| AJ2c/AK3b's load-bearing exponent — *"the deficit steepens as f^2.84"* — measured on **n = 3** centres and quoted forward by two later sessions (s140 `NEXT` #2 flagged it) | ⭐⭐ **CONFIRMED ON A 14× FINER SURFACE AND 4× THE n, s141 — the two whole-class refutations rest on a measurement** | 141 | Re-measured on GATE W's 1/48-oct transfer with AH's own estimator and membership, at **12 NON-OVERLAPPING centres** (overlapping ones are one curve sampled finely and are never quoted as an n). Limb regression **2.685** against AG4's **2.841**; across five half-widths it runs **2.53–2.90**. ⭐ Certified by an injected-KNOWN-EXPONENT known answer that does the one thing that matters: an injected **2.000 reads 1.977** and an injected **2.840 reads 2.779**, so the estimator **discriminates the class bound from the measurement** — a +0.84 bias would have *manufactured* AJ2c. ⭐ And the bias is **negative and grows with p**, i.e. the estimator UNDERSTATES the exponent, the conservative direction. ⚠ Free by-product: AL1c recomputes the class's own `≤2` bound by **finite difference**, sharing no algebra with AJ2c's analytic `2/(1+u)`, and gets **2.0000** for both the pole *appearing* and the pole *moving*. | `analysis/deficit_exponent_gate.py` (GATE AL) AL1/AL4 |
| AJ2c's **gating statistic and its phrasing** — *"EVERY adjacent pair exceeds the bound (weakest 2.693)"* | ⛔ **THE PHRASING IS REFUTED AND THE STATISTIC IS THE WRONG ONE — the CONCLUSION survives on better ground, s141** | 141 | **(1)** On the fine surface the weakest ⅓-oct pair is **−0.117** (weakest RAW adjacent pair **−10.349**), so the deficit does **NOT** beat the bound pointwise. **(2)** The per-pair statistic is **not scale-free**: it divides a log-ratio by the centre spacing, so as a half-width sweep narrows, the same noise is divided by a smaller number — measured, the raw adjacent minimum runs **−10.3 at 1/24 oct → +2.02 at 1/6 oct** on ONE dataset whose regression barely moves. AJ2c's version was sound only because its centres were a fixed ⅓ oct apart. ⭐⭐ **(3) The statistic the bound EXACTLY implies is the ENDPOINT one**: integrating `d ln\|g\|/d ln f ≤ 2` over `[a,b]` gives `endpoint exponent ≤ 2` for the whole class, whatever it does in between. That needs **no fit**, has the largest lever arm, and cannot be rescued by a favourable interior. Measured: **> 2 at 5/5 half-widths, smallest 2.530.** ⇒ **a single moving pole is refuted as the carrier of the WHOLE limb, and was never refuted pointwise. Quote the endpoint reading.** | `analysis/deficit_exponent_gate.py` AL4 |
| "the deficit steepens with frequency" — the shape, as a description of the band | ⚠⚠ **IT IS NOT MONOTONE — there is an interior MINIMUM at ~1348 Hz that AG4's three centres could never have seen, s141** | 141 | \|D\| **FALLS** 1.116 → 0.245 dB/oct over 1070 → 1348 Hz, then **RISES** to 4.410 at 3814 Hz. AG4's centres (1613/2032/2560) all sit **above** the minimum, so its wording describes **one limb**; a single power law over the whole band is not defined, and AL4 fits the rising limb with the split **computed as the argmin of \|D\|**, not chosen. ⭐ Nothing has looked below 1348 Hz because AG4's window rule never admitted it, and *a deficit that falls then rises is the natural signature of two contributions, not one corner*. ✅ Single-signed at **12/12**, so no log below is a zero-crossing artefact — the outcome most likely to sink the exponent programme, and it held. | `analysis/deficit_exponent_gate.py` AL3 |
| AG3's *"the MODEL's slope is PINNED (span 0.094 dB/oct) and moving the wrong way"* — quoted by item 6 as a property of the model | ⚠⚠ **IT IS A *LOCAL* READING AT A ZERO CROSSING OF THE MODEL'S OWN DRIVE-TILT, s141** | 141 | Across FREQUENCY the model's drive-tilt runs **−1.765 dB/oct at 1070 Hz to +0.389 at 3814 Hz — range 2.154, which is 0.73× the pedal's own 2.953** — and **crosses zero at ~2724 Hz, −7.2 % from the 2935 Hz vertex**, which is where AG3 reads it. ⇒ the model is **not** pinned across this band; it is passing through zero at the one frequency the statistic was taken. Those are different statements with different consequences for a candidate. ⚠ Recorded as measured: **why** the crossing sits near the vertex is NOT explained and is not claimed to be more than a coincidence. | `analysis/deficit_exponent_gate.py` AL3 |
| item 6's carrier as a **complex pole pair** (a resonance whose damping or corner moves) — the two-pole structure s140 `NEXT` #1(c) asked for, and the class AA6/AD5 independently narrowed to (DAMPING / LOADING) | ⭐⭐ **ADMISSIBLE IN SHAPE — but NO SHIPPED RESONANCE REACHES IT, and the admissible band is now a NUMBER, s141** | 141 | A complex pair **can** exceed the `2.000` real-pole bound where no number of real poles can (a sum of f² terms is f²). But at the **shipped** Sallen-Key operating points, against a target of **2.685 at the vertex**: **IC4_B** (f0 10730 Hz, Q 0.4635, w = 0.27) gives **1.200 / 1.477** — deep in its own f² regime; **IC4_A** (f0 3337 Hz, Q 0.6912, w = 0.88) sits essentially **AT** its resonance, where the Q-mechanism's own slope change passes through **zero**. ⇒ **0 of 2**, and it is **AK's root cause in a second guise: a carrier's corner must be PLACED right, not merely present.** ⭐⭐⭐ **THE POSITIVE SPEC (at ≥25 % of the mechanism's own max size): a Q/damping route needs a resonance at ~2.3–2.8 kHz with the vertex on its UPPER skirt (w ≈ 1.07–1.28); an f0-move route needs ~3.2–5.8 kHz (and NONE at Q = 0.4635).** ⚠ SHAPE ONLY — necessary, never sufficient (AK5). ⚠ Mechanism sizes on the shipped linear cascade, not priced renders. | `analysis/deficit_exponent_gate.py` (GATE AL) AL5 |
| open-work **item 5**'s proposed repair — *"a K/`clipSat` re-fit against a physical ceiling is the real repair"* (carried ~24 sessions) | ⛔⛔ **REFUTED ON THE PEDAL'S OWN SUPPLY, s142 — closed form, no fit, no render, no threshold** | 142 | The VTC is **homogeneous** (`vtc_{L·s}(L·w) = L·vtc_s(w)`), so raising the ceilings by `L` preserves the clipper's operating point **only if the drive at node W rises by `L` too**. `L = VDD/satsum = 5.636/1.0356 = ` **5.442× (+14.72 dB)** (per side: satLo ×6.07, satHi ×4.98). Every stage from the jack to node W is **schematic-fixed** (IC1_A unity, J201, treble/ATTACK ladder, IC2_A `= 1+R15/(R17+DRIVE+R32)`, R16), so the only free scalar is `kInputRef`, which would have to reach **4.898 V/FS**. Against it: TL07x knee **1.509** (the binding fence), TL07x hard 1.734, **ABSOLUTE supply ceiling 2.777** — the last being just `VD/(2.2·10^(−3/20))` off the 8.65 V rail and IC5_B's fixed −2.2, i.e. *"no op-amp on this rail can beat it"*. ⇒ the requirement **exceeds even the absolute supply ceiling by 1.76× (+4.93 dB)**; K at that ceiling supplies **56.7 %** of the needed scale (**30.8 %** to the binding fence). ⭐ This refutes on the **AXIS the parameter lives on** (supply arithmetic), strictly stronger than s44's fit-cost argument — a cost of 201.8 invites "try a better optimiser"; a supply bound cannot be argued down. ⚠ And the direction **moved the wrong way since item 5 was written**: s44 fitted the family at `kInputRef = 1.2596`, s109 shipped **0.90** (1.40× lower) without re-fitting `clipSat`. ⇒ what stays open is a **physical** question, not a fit: either the ceiling really is ~5.4× low, **or ~14.7 dB of gain ahead of node W is missing from the model** — and that second branch is **UNTESTED**. | `FitParams.h` clipSat block; `analysis/clean_headroom_bound.py` §1 |
| "session 44 already refuted the physical `clipSat` fence, so the 34.1 → 201.8 cost settles it" | ⭐ **VERIFIED CLEAN, s142 — the comparison is NOT confounded, and both logs were still on disk** | 142 | `step7_a5_sqphys.log` and `step7_a5_sq2.log` were read (`check-for-unread-data-first`, 7th occurrence). **Both** run with the square-law constraint ACTIVE and with identical `clipA0` [20,30] and `kInputRef` [0.4, 1.509] fences; the **only** difference is the `clipSat` floor ([1.5,4] vs [0.1,4]) ⇒ the 5.9× cost increase isolates exactly that floor. `sqphys` pinned **three** params as recorded — `clipSatLo` 1.5 (floor), `kInputRef` 1.5088 (**ceiling**), `clipA0` 20.052 (floor) — and even so reached satsum **3.239 V = 57.5 % of the rail, not 100 %**. ⚠ **Unexplained numerical coincidence, flagged and NOT used:** that 57.5 % sits beside the closed form's independent **56.7 %**. Two different constructions; the obvious co-scaling explanation does **not** reproduce it (drive-scaling from sq2 predicts satsum 1.241 V, not 3.239 — `sqphys` bought ceiling by driving `clipA0` to its floor and paying 5.9×). Treat as coincidence until explained; build nothing on it. | `analysis/fit_logs/step7_a5_sqphys.log` |
| "correcting item 4's corrupted MASTER anchor could relax the `kInputRef` fence and unlock item 5" (s142's own hypothesis, written down before it was tested) | ⛔ **REFUTED BY ARITHMETIC BEFORE ANY RENDER, s142** | 142 | The binding fence is `k_clean` from `clean_headroom_bound.py` **section (1)** = `(RAIL_POS−RAIL_KNEE)/(EQPREGAIN·10^(−3/20))` = `2.35/(2.2·0.70795)` = **1.5088**, and **every term is schematic-derived — no capture enters it.** The capture-derived bounds live in section (2) and read **4.375–5.493**, i.e. **2.9–3.6× looser; they never bind at all.** ⇒ the tool *is* correctly on item 4's list, but the corruption reaches **only a non-binding column**, so re-pointing it cannot move the fence. ⚠ Free by-product: that row is **doubly unusable** and must not be quoted — its −3 dBFS rung is the one segment s115 measured **PINNED** (peak 0.98850), so its `out@−3 dBFS` is a ceiling rather than a level, on top of the mis-dialled knob. ⇒ **item 4's scope SHRINKS**: it is hygiene, not a lever. | `analysis/clean_headroom_bound.py` §1 vs §2 |
| `circuit.md`'s *"the shipped `clipSat` sum 4.939 V is 88 % of that — physically consistent"*, and its *"impossible (183 % of the available swing)"* | ⛔⛔ **STALE FOR 98 SESSIONS — CORRECTED s142, in the file the project calls its source of truth** | 142 | 4.939 V is the **session-17** pair (2.0067+2.9321). s44's A5 re-fit changed satLo's *meaning* to a fitted knee scale and moved the pair to 0.4377/0.59791 — **sum 1.0356 V, 18.4 % of the rail**. So `circuit.md` certified as "physically consistent" a value the model has not carried since s44, while **`FitParams.h` and `Clipper.h` both flagged the real figure correctly the whole time** ⇒ `verify-the-CONSTANT-not-the-prose`. ⚠ **The correction costs a standing argument some of its force, so it is stated rather than patched:** the "2.70 V floating-spares collapse" case was ruled out *partly because* 4.94 V would be 183 % of 2.70 V; at the true 1.0356 V that is only **38 %** and the argument no longer bites. **The collapse case still falls — on the schematic evidence alone** (spare inputs tied to GND, verified 600 DPI on primary p.4 *and* the backup). ⛔ Quote the schematic, never the 183 %. ⚠ Same edit fixed `FitParams.h`'s *"their SUM **is** the R19-dropped effective rail (nominal ~7 V)"* — two errors: `~7 V` is the round figure s42 called out as *"a rail no calculation ever produced"* (derived **5.636 V**), and the physics gives a **one-sided** bound (a sum *below* the rail is no violation), which is why the 18 % flag is SOFT and is the reading whose loss enabled the s118 clamp bug. | `.claude/rules/circuit.md`; `src/dsp/FitParams.h` |
| CLAUDE.md's own *"the next matrix run re-renders from scratch (~25 min)"* (s127's cache bill) | ⚠ **THE BILL WAS ALREADY PAID — CORRECTED s142** | 142 | Measured against the binary's own `(size, mtime_ns)` signature, which is what `_cache_key` hashes: of **6663** entries, **6501 predate** the binary (unreachable — exactly s127's figure) and **162 postdate** it (reachable), and 162 is exactly the current matrix's capture count. ⇒ a full matrix render **did** happen after s127's relink, so the current matrix is **fully cached** and the next run is fast. **Do not budget 25 minutes**, and note the 6501 stale entries are ~reclaimable disk (138 MB total). ⛔ But the bill **re-arms on the next build**: s142 edited `FitParams.h`/`Clipper.h` comments and **deliberately did NOT rebuild**, so those 162 are still warm — whoever next builds pays ~25 min once, and should batch their `src/` edits into that one build (`build.md`'s rule). ⚠⚠ **THAT RE-ARM FIRED AT s144, WHICH BUILT — so the 162 are now STALE and the next matrix run DOES pay ~25 min.** Nothing is corrupted (no DSP behaviour changed in s142 or s144), so `s124_ship.json` still stands; this is a speed cost, not a correctness one. | `analysis/comprehensive_report.py::_cache_key` |
| `drive-1700_base-od @ sweep_drv_-6`, 50 Hz reading ~1400% THD | **RESOLVED — denominator artefact** | 122 | Model's 50 Hz fundamental collapses 41 dB below the pedal's (a cancellation-null read-point coincidence, same mechanism as the bass-notch/A3 row); numerator (harmonic energy) is ordinary on both sides. Not a distortion-generation defect; needs no separate work. | `analysis/feature_locus_gate.py` |
| "how close are 1x/2x/4x to 8x?" — `build.md`'s Phase-10 `OSFidelity` question, unbuilt since the template | ⭐⭐ **MEASURED AND DECOMPOSED, s144. The WANTED DISTORTION IS FAITHFUL AT LOW OS; WHAT LOW OS LOSES IS THE TOP OCTAVE AND THE ALIAS FLOOR** | 144 | Harmonic-ladder rms vs the 8x reference, restricted to harmonics **below 5 kHz** (above it the ladder just re-reads the droop — unbanded it came out 27.8 dB and would have double-counted one defect as two): **1x = 0.183 dB** at a bass-realistic f0 and **0.511 dB** at 2499 Hz, against an alias excess of **+45.6 / +40.8 dB** at the same factor — two orders of magnitude apart on the same renders. ⭐ **The droop, first measurement ever: 1x is −2.35 dB at 8 kHz and −20.65 at 16 kHz; the SHIPPED 2x default is −0.48 / −3.03; 4x is −0.09 / −0.56.** Below 3.2 kHz every factor agrees inside the block's floor ⇒ strictly a top-octave defect. ⭐ Corroborates `dsp.md`'s *template reference build* (1x ≈ −4 @8k / −21 @16k) on a different circuit, which is what a pure discretisation artefact should do. ⛔ **`src/utils/Prewarp.h` ships and is referenced by NOTHING — and it is the WRONG remedy**: `dsp.md` says a cap inside the oversampled region must not be prewarped, and these are. The matching option is `dsp.md`'s per-OS-factor high-shelf; **unbuilt and NOT proposed** (DSP change, owes a gate + re-baseline). ⚠ Membership: n=8 orders in the 506.84 Hz low band, **n=1 (H2 alone)** at 2499 Hz — printed every run. | `tests/OSFidelity.cpp` |
| the shipped ADAA policy, judged as **FIDELITY** rather than as alias energy — never asked; GATE X and `OSValidationTest` both score it on the alias floor ALONE | ⭐⭐⭐ **MEASURED, s144: IT IS A WIN AT THE SHIPPED 2x DEFAULT AT BOTH FUNDAMENTALS, AND IT COSTS LADDER ACCURACY IN 3 OF 4 CELLS** | 144 | ADAA1 is a *different approximation* (a 2-point average), not merely a cleaner one, so "reduces aliasing" and "is closer to the truth" are two claims and only the first was on record. Scoring both arms against the **same** 8x reference (which carries no ADAA either way), Δ alias / Δ ladder<5k: **506.84 Hz — 1x +1.91 dB (WORSE) / −0.008; 2x −5.70 / +0.023. 2499 Hz — 1x −20.27 / +0.527; 2x −15.08 / +0.209.** ⇒ **at 2x it wins at both fundamentals**, vindicating s124's decision on an axis s124 never measured; **at 1x it is a large win at 2.5 kHz and a small net LOSS at a bass-realistic f0**. ⭐ And in 3 of 4 cells it moves the wanted harmonics slightly AWAY from the 8x truth while moving the alias floor toward it — two axes, opposite directions. ⛔ **NOT a proposal to change `clipAdaaMaxOs`**: the 1x loss is +1.91 dB on a floor already at −44.3 dB (inaudible), and n = 2 fundamentals is not a frequency dependence. | `tests/OSFidelity.cpp` |
| open-work **item 7** — *"a clean same-session `gain-n18` MASTER ladder would let s115's taper be resolved below its 0.85 dB knob-noise floor"* | ⭐⭐⭐ **DONE, s146 — RESOLVED AND SHIPPED, BUT WHAT RESOLVED IT WAS A TRUST STATEMENT, NOT THE EXTRA DATA** | 146 | The s120 n18 ladder alone moves the ladder ≤0.593 dB against a 1.075 dB floor — **sub-floor, licensing nothing**. What licensed a change is the user's statement *"0700, 1200, and 1700 are 100% trustworthy, all other positions are best estimations"*, which makes six of seven interior points **estimates of a ROTATION** — error in **x**, not y (every capture's LEVEL is exact to 0.0002 dB). ⇒ the fit becomes a **CONSTRAINT through the one trusted interior point (m=0.5)**, not least-squares over seven equals. ⭐⭐ **And the statement is independently corroborated**: those three positions are exactly where the pot has a physical reference, and across two capture sessions 12+ days apart the spread is **0.0000 dB at 0700 and 0.0000 at 1200 vs 0.33–1.77 dB elsewhere** — with the files **confirmed independent recordings, not digital copies** (scalar-nulled −84…−86 dB, the same floor as detents whose levels DISAGREE by 1.19 dB). ⭐⭐ **THE DEFECT, FIT-FREE: the s115 taper was 1.86 dB QUIET at MASTER noon — 186× the pin's own uncertainty**, and in the units a pot is specified in, the reference is **11.89 % at half rotation (INSIDE the textbook A-taper 10–15 % band)** where the model was **9.59 % (BELOW it)**; `circuit.md` calls VR8 a 100k **A**. ⚠ **The s115 floor of 0.847 dB was overstated** — it pooled free positions with the 0700 hard stop reading exactly 0.000; split on the physical property it is **1.075 dB (n=5, worst 1.770)**. | `analysis/master_taper_makeup.py`, `analysis/reports/s146_master_recal.json` |
| "three segments is overfitting — 3 params against 6 points at a 1.08 dB floor" (the obvious objection, and it is the right instinct) | ⭐⭐ **ANSWERED, s146 — IT SHIPS ON THREE GROUNDS AND ONLY ONE IS A FIT STATISTIC** | 146 | The 2-segment family's first segment runs from the ORIGIN, so it **cannot be convex** below its break — pinning noon inside it drives the bottom of the travel **1.4–3.4 dB hot** with a **+1.232 dB one-signed bias**. ⭐ **The BIAS is the diagnostic, not the rms**: hand jitter has no preferred sign, so a one-signed residual means the FAMILY is inadequate; 3 segments takes it to −0.329. The candidate ships because **(i)** it is EXACT at the trusted point (a constraint, not a fitted target), **(ii)** its segment slopes RISE monotonically — **0.172 → 0.368 → 2.413**, a convex physically-buildable track, asserted by `MasterOutTest` Test 0 which FAILS if convexity is lost — and **(iii)** it fits the estimated positions better than the incumbent (**0.665 vs 0.960 rms**) *while carrying a constraint the incumbent does not*. ⛔ **Do NOT add a fourth segment**: (iii) is already **below** the 1.075 dB floor, so further rms gain is fitting the hand that turned the knob. | `docs/session-log.md` SESSION 146.4 |
| ⚠⚠ `masterTaperBreak` — the NAME survived a MEANING change at s146 (it is now the FIRST of two breaks, 0.5927 → 0.3318) | ⚠⚠ **FOUR CONSUMERS WOULD HAVE SILENTLY REBUILT A TWO-SEGMENT CURVE — ALL RE-POINTED s146** | 146 | Every consumer that rebuilds a 2-seg curve from that name **still runs, still produces plausible numbers, and is wrong** — s118's *"when a parameter carries two meanings and a fit consumes one of them"*. Re-pointed: `PedalChain::applyFitParams`, `tests/MasterOutTest.cpp::taperRatio`, `offline_render.cpp`'s `--fit` map, `a3_decomposition_gate.py::master_div` (now **requires** the two new names rather than defaulting, so divergence is loud). ⚠ It also caught the taper tool **twice**: it evaluated its own "SHIPPED" row through `pwl2` after the constants moved under it, and its pinned-2 diagnostic **seeded its optimiser from `SHIP_XB`** — which, once that value meant something else, landed outside the valid region so the "fit" silently returned its start. ⇒ **a candidate's own search must not depend on the incumbent's parameterisation.** | `MasterOut.h` constants block |
| the s120 listening-test lead — *"MASTER: plugin needs ≈0.61 to match"* — and its flagged coincidence with `masterTaperBreak = 0.5927` (`an-implausible-coincidence-is-a-bug-report`, unchecked for 26 sessions) | ⚠ **THE COINCIDENCE DISSOLVES; IT DOES NOT RESOLVE — and this session's own first write-up overclaimed that it did** | 146 | Two candidate explanations exist and they sit **0.0024 of rotation apart** — the old break (0.5927) and the rotation at which the s115 taper delivered the pedal's own noon level (0.5951) — which is far below an ear's resolution of a knob position. ⇒ **it cannot be decided this way, and there was never evidence of a bug**. ⭐ What survives is **directional corroboration**, and it is real: an ear said *turn it up at noon* and the captures independently say the model was **1.86 dB short there**. ⇒ open work item 10 closes on that basis, not on a resolution. | `docs/session-log.md` SESSION 146.3 |
| GATE O6b's baseline-EPOCH guard, which s119 built to name a pre-s115 report | ⚠ **FIRED CORRECTLY AND DIAGNOSED WRONGLY, s146 — EXTENDED** | 146 | It refused `s124_ship.json` (right — that report predates the taper change), but its fallback knew only the **power law**, so it reported *"either these captures are not the duplicate GATE T3 reports, or the shipped MASTER taper is not rendering as specified"* — two alarming and wrong diagnoses. Now a LIST of retired forms: it identifies the epoch to **0.0002 dB** (measured −2.7572 vs the retired 2-seg PWL's −2.7574) and says explicitly *"NOT a capture defect and NOT a rendering bug — do not go looking for one."* ⭐ GENERAL: **a guard that names epochs must be EXTENDED every time an epoch ends**, or it degrades into a puzzle exactly when it fires. | `analysis/a3_decomposition_gate.py::_retired_epoch_pred` |
| `_archive/master-1700_gain-n18_base-clean.wav` — the second n18 capture at the top hard stop | ⛔ **CONFIRMED BAD, s146, by a forbidden-structure test — excluded BY NAME** | 146 | It differs from the current n18 top **at the same hard stop** by a **frequency-dependent 11.27 dB span**. MASTER is a post-EQ attenuator, so a master-only difference is a PURE GAIN and this is physically impossible (GATE O6). ⇒ s112's *"the whole archived session was contaminated"* pinned to a specific file by evidence rather than by which directory it sits in. ⚠ The rest of the n18 ladder is clean: **no pinning anywhere** (all peaks ≤ −28 dBFS) and **pure-gain to 0.0002 dB across all nine detents**. | `analysis/master_taper_makeup.py::EXCLUDE` |
| A3's corollary block naming *"open-work item 6's **dynamic-sag candidate**"* as A3's most likely carrier — the sentence that ends the A3 exclusions list, carried since s125 | ⛔⛔ **THE CARRIER IS REFUTED TWICE OVER, AND BOTH REFUTATIONS WERE ALREADY ROWS IN THIS TABLE — s147** | 147 | Dynamic sag has fallen twice: **s125** (dynamic R19 supply sag shifting the `C14∥R18` corner — the closed-loop corner is **6.29 kHz, not the 2.19 kHz bare pole**, and it moves the peak **UP** as `a0` falls where the pedal walks **down**) and **s138** (the clipper's own `a0` sag — its sign **flips with the GRUNT switch** at 1 of 3 positions and the defect's does not, and it reaches only **20.7 %** at the `a0 → 1` limit). ⭐ **The block's CONCLUSION survives and is untouched** — item 6 *is* A3's dynamic half, on GATE W's `transfer_h1` argument — but a session reading that sentence would have inherited a **mechanism noun** that every named-carrier screen has since killed, which is the failure mode `a-refutation-has-to-land-where-the-thing-is-CHOSEN` (s124) describes: the refutation landed in the table and not in the prose citing it. ⇒ **item 6's carrier is an OPEN FRAME question — do not take a mechanism from that block.** ⚠ Same pass corrected two more stale claims in the same file: the block re-quoted `D(f)` as **3.01 dB** against its own ⛔ *"do not re-quote 3.01"* row (current **2.64**), and "Capture access status" still called the s120 `gain-n18` ladder *"not yet analysed"* 1 session after item 7 closed on it. | `docs/session-log.md` SESSION 147 |
| **"what in this chain could have a resonance near 2.5 kHz at all?"** — AL5's own buildable next question, carried as item 6's head brief since s141 and never asked | ⭐⭐⭐ **ANSWERED, s145, AND IT CLOSES THE RESONANCE ROUTE: NOTHING AT OR UPSTREAM OF THE CLIPPER CAN RESONATE, AT ANY FREQUENCY, FOR ANY COMPONENT VALUES** | 145 | A census of **all 24 stages** in signal order, natural frequencies read off the generalised eigenvalue pencil. The chain contains **EXACTLY ONE complex pole pair anywhere — Sallen-Key IC4_A (f0 3336.9 Hz, Q 0.6912)** — and it is **post-clipper** and reads **w = 0.8795** against its own-Q admissible bands (Q route [1.068, 1.209]; f0 route [0.504, 0.601]) ⇒ **does not reach**, reproducing AL5's 0-of-2 from a different construction. ⭐⭐ **The pre/at-clipper zero is EXHAUSTIVE, not a shipped-point reading**: every stage there is either **passive RC** — real poles by the RC theorem, **asserted on the actual stamps** (sym(G)=sym(C)=0, non-negative min eigenvalues) rather than cited, with a bootstrap-gain control that DOES produce a complex pair at g = 0.9/1.0 — or the **clipper's own shunt-feedback loop**, whose discriminant `b²−4ac ≥ 0` for **every** positive R16, R18, Cg, C14 and every a0 ≥ 0 by **AM-GM** (20 000-draw sweep: min normalised discriminant **5.23e-5**). ⇒ **no re-fit of `clipA0` or a GRUNT cap can create one.** ⚠⚠ **The linear-only census is NOT a gap**: both nonlinearities are **memoryless** (CD4049 VTC in node W, s123; J201 shaper, s140/AK2), and a memoryless map has no state ⇒ contributes no natural frequency, so every pole in the chain is in AM2's table. ⭐ Sharpens AL5's IC4_B row: **Q = 0.4635 < 0.5 ⇒ OVERDAMPED, not a resonance at all.** ⭐ AM6 prices the one omitted energy-returning structure — **C4's bootstrap corners at 14.47 Hz, 203× below the vertex**, and `JfetStage.h` already models it as static — so the omission cannot hide one; and a computed scan of `circuit.md` finds **0 inductors**, leaving controlled sources as the only route, all of which AM2 enumerates. ⚠ **NOT claimed: that the DEVICE has no resonance there** — only that the MODEL has none. Instrument: 20 netlists vs `eq_reference`'s oracle (worst **3.68e-12**), a two-sided synthetic control (RC ladder real / Butterworth Q recovered exactly), 12/12 mutation arms. | `analysis/resonance_census.py` (GATE AM) |
| ⭐⭐ *"EVERY named carrier on both sides of the clipper is now refuted"* (s139/s140's closing claim, carried into s145's frame question and into two CLOSED/REFUTED rows) | ⛔⛔ **IT WAS OVERSTATED, s148 — one live carrier was never screened, and the tell was inside the gate that closed the space** | 148 | The J201 drain node's **output resistance** (`ro`, `rq2`) sagging with the operating-point current is a shipped-fit-param mechanism that is **STATIC in the model** (AN1b brace-matches `JfetStage.h`: mutated only at lines 268/269 in `setNonlinear`, never in `process()`) and appears in **no** CLOSED/REFUTED row, nowhere in `docs/session-log.md`, and in no gate. ⭐⭐ **The tell was free and unread: GATE AK's OWN mechanism function is `drain_db(gm, ro, rq2, zin)` — it ACCEPTS both and swept `gm` only** (`GM_SAG_FRACS`). ⇒ the claim was about carriers that had been **NAMED**, and it read as a claim about the **space**. ⭐ **THE REPEATABLE AUDIT, which is the durable output: for every gate that screened a stage, diff the parameters its mechanism function ACCEPTS against the ones it actually SWEPT.** Worth running on AI (`a0`, GRUNT caps) and AJ. ⚠ The claim is **true again** as of s148 — but only because s148 refuted what it had missed. | `analysis/jfet_rout_tilt_gate.py` (GATE AN) |
| item 6's carrier as a **drain-node source-impedance** mechanism — the `ro`/`rq2` sag, and by AN3b the whole class | ⛔⛔ **REFUTED THREE WAYS THAT INTERLOCK, s148 — and the class falls with it** | 148 | `ro` does **not** enter `k(s)`, so unlike AK's route 2 it scales `Zout` **flat in frequency** and its shape comes purely from the divider against the multi-pole `Zin_ladder(f)` — which is why it was worth screening rather than assuming AK covered it. One-parameter by physics (Q2 is the active load carrying Q1's own Id ⇒ one Id scales both; `Zout` homogeneous degree 1 in L, asserted at **0.0**), so its two limits BRACKET every excursion. **⚠ RE-QUOTED s149 on the corrected ladder (GATE AO): sign-admissible reach **1.334 %** (was 0.694); the reaching direction now reaches only **23.0 %** (was 107) and is still wrong-signed **10/10**; both directions fall as f^−1.78 where the deficit rises as f^+2.78.** ⇒ refuted on **shape independently of sign and size**, and s149 **STRENGTHENS it — NEITHER direction reaches, so the verdict no longer leans on the sign argument at all.** ⭐⭐ **AN3b generalises it, but WEAKLY: `Zout/Zin` is `**4.97:1**` (NOT the 27:1 s148 published) and `\|Zin\|` slopes **−0.455** dB/oct (NOT −1.75) at the vertex, so a drain-node SOURCE-impedance perturbation is still largely spent there** — the three routes do share a falling exponent (AK f^−1.87, AN f^−1.78) against a rising deficit, but *"one geometric fact dominates all of them"* is a much weaker claim at 5:1 than at 27:1. ⛔ Do not re-quote 27:1 or −1.75. ⚠ Structural reading on the shipped cascade at ONE feature; **not** a proof about unnamed mechanisms. ⚠ 5 known answers all at **0.0**; 13/13 mutation arms, two of which caught defects in this gate's own instrument (see pointer). | `analysis/jfet_rout_tilt_gate.py` (GATE AN) AN1–AN5 |
| s148's own audit — *"for each gate that screened a stage, diff the parameters its mechanism function ACCEPTS against the ones it SWEPT"* — run for real | ⭐⭐⭐ **MECHANISED AND RUN, s149 — AND IT FOUND A DEFECT IN THE SHARED INPUT OF THREE GATES, NOT ANOTHER CARRIER** | 149 | Of GATE AK's `drain_db(gm, ro, rq2, zin)`, s148 covered `ro`/`rq2`; **`zin` is the fourth**, and tracing where it came from shows `AJ.ladder_zin` computed the treble/ATTACK ladder from **`eq_reference`'s DRAWN defaults** — `EQ.treble_attack_tf(f, position)`, no element values passed at all — while s99/s100 re-fitted **17** treble/ATTACK constants and changed the topology. Measured, **11 of 12 values differ**: R7 **×8.23**, C6 **×0.063**, C7 **×0.0076**, C8 **→ 0**, RdampC5 0 → 15.37 k. **GATE AJ, and through `ladder_zin` also GATE AK and GATE AN, all screened a network the plugin does not run.** ⭐⭐ GATE AM hit this exact trap at s145 and **guards** it (AM1a); these three had no guard. ⭐⭐⭐ **WHY NOTHING CAUGHT IT is the generalisable half: AJ *did* have a known answer on `ladder_zin` — AJ1d, probe-independence, passing at 3.9e−14 — and it validates the EXTRACTION, not the VALUE SET, because both sides share the element set as INPUT** (s145 AM1a's lesson in a second guise). ✅ Fixed: `ladder_kwargs` (imported from `resonance_census`, never transcribed) defaults to **shipped**, `drawn` stays reachable so pre-s149 numbers reproduce, and **AJ now carries the divergence guard itself (AJ1e)** — a correction is not complete until the gate that USES the value can refuse. | `analysis/ladder_epoch_gate.py` (GATE AO) AO2 |
| what the ladder-epoch defect COST the three gates' conclusions | ⭐⭐ **MEASURED BOTH WAYS, s149 — ALL THREE VERDICTS HOLD, AND THREE PUBLISHED NUMBERS ARE WRONG** | 149 | s139's discipline (re-run at both value sets and DIFF the stored reports, never assert the difference is small): AJ **8** leaves moved / 97 bit-identical, AK **26**/39, AN **75**/56, **verdict unchanged in all three**. ⭐⭐ **AJ's GRADED columns are BIT-IDENTICAL** (`reach` 0.00166351, `exponent` 2.84139, required 388.297 pF) because its reach is read at an **absolute 10 pF ceiling** and its exponent bound is **analytic** — neither ever touched `zin`. ⇒ **the defect reached the EXPLANATORY columns only, which is exactly why it survived ten sessions: nothing that was gated on moved.** ⛔ Wrong and now re-quoted: **\|A\| 0.565 → 2.778** (Miller factor 1.565 → **3.778**, so AJ2's *"no Miller multiplication to modulate"* is FALSE), **80× → 47.5×**, **`Zout/Zin` 27.2 → 4.97**, **`\|Zin\|` slope −1.755 → −0.455 dB/oct**, **`\|Zin\|` 6.14 k → 33.63 k**. ⭐⭐ And **GATE AN is STRENGTHENED** — its reaching direction falls 106.4 % → **23.0 %**, so neither direction reaches. ⚠ AO4 **imports** these from its own two AJ reports: a first draft recomputed `\|A\|` at the wrong probe frequency and got 0.595/2.811, plausible and mislabelled. | `analysis/reports/s149_ladder_epoch.json` AO3/AO4 |
| ⭐⭐ item 6's pre-clipper side, after AN3b — is the divider argument really exhaustive? | ⭐⭐⭐ **NO — ONE LEVER IS UNSCREENED, AND AN3b's OWN ARITHMETIC SAYS IT IS THE BIG ONE, s149** | 149 | AO1c asserts the exact identity `d ln Zd/d ln Zin + d ln Zd/d ln Zout = 1` (measured **3.3e−16**, plus a finite-difference cross-check — AB3's *"the columns must sum to −1"* in a second guise, no threshold to argue about). At the shipped ladder it reads **S_zin 0.836 / S_zout 0.168 ⇒ the LOAD side of the drain-node divider carries 4.97× the lever of the SOURCE side** — and **every carrier screened so far acts on the SOURCE side** (AK's gm-through-`Zout`, AJ's moving-pole class, AN's `ro`/`rq2`). ⇒ **AN3b, written as a refutation, read as a SPECIFICATION points at a drive-dependent treble-ladder `Zin`, and AO2 classifies `drain_db(zin)` KA-ONLY** — its only non-baseline expression is `inf`, inside AK's own known-answer sub-gate, so it was never moved as a mechanism. ⚠⚠ **NOT SCREENED — this establishes the lever exists, is unswept and is ~5× the source-side one; it names no physical carrier**, and gate 5's `≤ 2` bound still applies to any SINGLE element drift in a network AM2 established is all-real-pole. ⇒ start the screen from *"which perturbation of this network can rise as f^+2.8 at all"*, not from a component list. | `analysis/ladder_epoch_gate.py` AO1c/AO4 |

### THE RELEASE GATE

Phase 9 closes and Phase 10 begins when the SHIP column is met (agreed with the user, session 89).
Percentiles are over band values, OD ex `gain-n12` unless noted. **The gate is a script, not a
transcribed table — `analysis/release_gate.py`.** Run it; do not transcribe its output here:

```bash
/opt/homebrew/bin/python3.11 analysis/release_gate.py analysis/reports/s146_mastertaper.json
```

It exits non-zero while any gated row is over, prints `n` beside every statistic, breaks the
reference dropouts and the `gain-n12` group out as printed subsets (never hidden), and takes
`--method csd|h1|h1band` / `--compare` to re-grade from the same renders, plus `--ex-gain-n12` to
reproduce the pre-session-111 membership.

**6 rows over SHIP** — OD 100 Hz–8 kHz p90, OD 25–100 Hz median/p90, OD 8–16.3 kHz p90, OD p99,
THD level (full-send). OD band-RMS (the headline) and OD 100 Hz–8 kHz median both meet their bars.

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

⚠⚠ **CORRECTED SESSION 125 — this block used to call the 8–16.3 kHz region "ND's own ALIASING
artefact… not ours to fix" and carried a ⛔ prohibition on working it. GATE I does not say that, and
its G3 refutes the one aliasing mechanism it tested.** The full correction is the "HF region" entry
under "Standing rules that must not be lost" below — read it there, it is stated once. The short
version: **"drive-generated" ≠ "aliasing" ≠ "not ours to fix"**, whether the gate should still grade
these bands is a **USER DECISION**, and open-work item 6 carries the live hypothesis.

### Open work, in order

Current ordering per **session 139's** own `▶ NEXT` (see `docs/session-log.md` for the superseded
orderings and why each item moved). ⭐⭐⭐ **Session 139 closed the last of item 6's named carriers,
so its head item is now a FRAME question rather than another element screen** — the three
directions session 139 hands forward are in `docs/session-log.md` SESSION 139's `▶ NEXT` #1. ⚠ **The numbering below is historical and is NOT the priority
order any more** — session 128 demoted item 2 (it turned out to be items 6 and 9 seen on another
axis), so **item 6 is now the head item**. The numbers are kept because every rules file, gate
docstring and CLOSED/REFUTED row cites them.

0. ✅ **DONE, SESSION 126 — the bass peak is LOCALISED and the single-constant route is REFUTED**
   (`analysis/bass_peak_locus.py`, GATE Y; two CLOSED/REFUTED rows carry it).
   ⛔ Do NOT re-open "point an optimiser at trebleR7/trebleC5/trebleC7" — priced and refuted.
   ⭐⭐ **ITS SUCCESSOR IS FILED UNDER ITEM 6, NOT HERE** (per `closing-an-item-drops-its-successor`):
   the bass peak is a second instance of item 6's target, at the opposite end of the band, and is
   carried with its numbers in item 6's own table.

1. ✅ **DONE, SESSION 124 — the user enabled ADAA, gated by OS factor, with `clipK` re-anchored to
   2.0.** Three constants shipped (SHIPPED CONSTANTS table above); two open items closed on one
   decision, since the re-anchor is both what makes ADAA exact and what restores the `pow()` fast
   path. ⛔ Do NOT re-open "is the re-anchor affordable" — measured on 162 captures before shipping
   and free (⚠ *indistinguishable with a rounding preference*, NOT "a better fit"). ⛔ Do NOT
   "simplify" the OS gate to an unconditional on: 4×/8× were measured and they lose (worst tone
   +9.9/+17.3 dB). See `docs/session-log.md` SESSION 124.
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
3. ✅ **DONE, SESSION 127 — SESSION 124 IS THE LARGEST PERF WIN IN THE PROJECT: THE WHOLE CHAIN IS
   ~2× FASTER AT EVERY OS FACTOR** (`tests/PerfBenchmark.cpp`, finite-only per `build.md` — timing is
   REPORTED, never gated). The `pow` fast path is **−56…−59 % of the WHOLE CHAIN**; ADAA costs
   **+18…+22 %** at the two gated-ON factors and zero-to-noise at 4×/8×; the arithmetic closes from
   both ends (a `std::pow` microbenchmark × the per-sample pow count predicts it to **3 %**).
   ⚠ **Absolute ns/sample is machine- and run-specific — only within-run ratios are quotable.** Run
   it for numbers; the s127 table is in `docs/session-log.md` SESSION 127.
   ⛔ Do NOT re-open "is the re-anchor worth it on perf grounds" — priced, and negative by 2×.
   ⛔ **Keep one refutation from that work, because it applies to any future "just integrate the
   nonlinearity numerically" idea: NOT quadrature.** The in-chain step-vs-knee table in
   `Clipper.h::setADAA` rules it out — the argument steps further than the whole knee on 57 % of
   samples at 2×, so fixed nodes land in saturation and miss the feature entirely.
4. ⚠ **Re-point the other consumers of the corrupted MASTER anchor — SCOPE SHRANK, SESSION 142:
   this is HYGIENE, not a lever.** s142 measured the first name on the list and found the corrupted
   capture reaches **only a non-binding column** of `clean_headroom_bound.py`, so re-pointing it
   moves **no** bound and cannot unlock item 5 (CLOSED/REFUTED row). ⛔ That row must also **not be
   quoted** even as a loose bound — its −3 dBFS rung is a segment s115 measured **PINNED**, so it is
   a ceiling, not a level. ✅ Its stale display numbers are annotated in place.
   **The other three consumers are unchecked** — `clean_headroom_probe.py`, `clean_thd_check.py`,
   `captures.py`'s Tier-1 matrix list all still name `master-1700_gain-n12_base-clean.wav` (the
   capture GATE T proved 4.447 dB low). None currently carries a quoted number that matters (checked
   session 119), but any future use needs `master_anchor_gate.py`'s `detent_corrections()`.
5. ⛔⛔ **VTC-amplitude-vs-physical-rail — THE INCONSISTENCY IS REAL AND CONFIRMED; THE PROPOSED
   REPAIR IS REFUTED, SESSION 142.** The measurement stands: `clipSatLo+Hi = 1.0356 V` against the
   derived `VDD = 5.636 V` — **18.4 %, i.e. 5.442× low** — while everything around it (TL07x rails,
   D1/D2 references via `kTripPointV`, R19) is physical, and it is why the corrected D1/D2 window
   still fires on 0.05–0.25 % of samples.
   ⛔ **The sentence that used to end this item — *"a K/`clipSat` re-fit against a physical ceiling
   is the real repair (same job as item 4)"* — is refuted in both halves; do not attempt it.** Two
   CLOSED/REFUTED rows carry the arithmetic: the **supply forbids it** (a physical ceiling needs
   +14.72 dB more drive at node W, and `kInputRef` — the only free scalar — would have to exceed the
   **absolute supply ceiling by 1.76×**), and **"same job as item 4" is false** (the binding fence is
   capture-free). ⭐ s44's own attempt is verified a **clean** comparison and even forced reached only
   57.5 % of the rail at 5.9× the cost.
   ⇒ ⭐⭐ **WHAT REPLACES IT — A PHYSICAL QUESTION WITH TWO BRANCHES, AND THE SECOND IS UNTESTED:**
   either (a) the clipper's ceiling really is ~5.4× low and the OD path is structurally quiet at the
   clipper, **or (b) ~14.7 dB of gain ahead of node W is missing from the model.** Nothing has tested
   (b), and it is *not* obviously absurd: `trebleC7` ships **147× off schematic** as a ~183 Hz
   high-pass that *attenuates* the OD path, s100 re-fitted **17** treble/ATTACK constants explicitly
   as an *"OD-path absolute-level fix"*, and A3's whole finding is that the OD path is quiet,
   absolutely (GATE O: 4.38 dB over 100–400 Hz). ⛔ But that is **a hypothesis with a suggestive size,
   not a measurement** — the 14.7 dB and the 4.38 dB are not the same quantity and nothing has
   related them. Decide which branch before spending a fit.
   ⚠ `FitParams.h`'s clipSat block and `Clipper.h`'s `kTripPointV` block both carry this refutation
   where the constant would be **chosen**, not only where it was analysed. ⛔ The D1/D2 residual is
   therefore **expected to persist** — a standing, quantified marker of the soft-low ceiling, **not**
   a pending repair, and still not a reason to widen `kTripPointV`.
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
   ⛔⛔ **THE "MID PEAK TRACKS" CLUE IS WITHDRAWN (s129), AND WITH IT THIS ITEM'S "it is specific,
   not global" PREMISE** — the pair is **non-monotone** (interiors printed above), the error reaches
   **8.3 % mid-ladder against the 2.5 % that excused it**, and mid_peak is the least stable reading
   in the set. ⇒ the model has **no resolved drive-dependent feature anywhere**; the deficit is
   **GLOBAL**. ⛔ Do **not** gate a candidate on the mid peak in either direction. Two s129 rows.
   ⭐⭐ **A FOURTH FEATURE, s126, AT THE OTHER END OF THE BAND — THE BASS PEAK, WHERE *BOTH* SIDES
   WALK** (GATE Y's Y6, one capture, all four rungs — not W6, which reads it `UNRESOLVED` for a
   **membership** reason: it is a mix cancellation with no bleed-free reading):
   | feature | model | pedal | our error |
   |---|---|---|---|
   | bass peak (`ref-od`, s126) | 163.9 → **151.1** Hz (7.8%) | 206.0 → **160.8** Hz (28.1%) | **+25.7 % @ clean → +6.4 % @ `drv_-6`** |
   ⇒ unlike the treble peak this is **not** "ours is pinned and theirs walks" — ours walks too, just
   **3.6× less far**, so the error is a difference of *rates*, and it gives the item a **low-frequency
   anchor to gate candidates against**. ⚠ On the **bleed-free** endpoints W6 reads the pedal's bass
   peak at a 7.8 % span and non-monotone — a different capture set at a different mix, so the two
   readings are not interchangeable.
   ⭐⭐⭐ **WHY OUR 2980 Hz PEAK IS PINNED — LOCALISED s125, CLOSED-FORM, NO FIT.** It is the
   **recovery bridged-T's rise out of its own 716 Hz notch, rolled off by the two Sallen-Keys**:
   cascading the schematic values and vertex-interpolating in log-f gives **2934.8 Hz** against GATE
   W's measured **2977–2983 Hz — 1.5 %, with nothing fitted.** ⇒ it is a **pure POST-CLIPPER LINEAR**
   feature, downstream of every nonlinearity, so it *cannot* move with drive, by construction.
   ⭐⭐ **AND THAT UNIFIES THIS ITEM WITH A3.** GATE W reads centres off `transfer_h1` — the
   **fundamental** — so for the *pedal's* peak to walk, its fundamental transfer must itself be
   drive-dependent, i.e. its compression is **frequency-dependent** where ours is closer to uniform,
   which is **GATE Q's `D(f)` in the frequency domain**. ⇒ **the treble-peak walk and A3's untested
   dynamic half are the SAME finding on two instruments.**

   ⭐⭐⭐ **THE CURRENT TARGET, IN THE RIGHT UNITS (AF6, size-confirmed by AG3/AG5): a
   drive-dependent SLOPE change near 2935 Hz, worth −1.185 dB/oct, that STEEPENS with frequency, at
   or UPSTREAM of the clipper.** A vertex sits where the total slope crosses zero, so a tilt moves it
   with **no corner moving anywhere** — which is why every corner-based frame in the refuted table
   below failed. The reference carries it with margin (P−M = **−2.038 dB/oct = 1.72×** the
   requirement, same sign in **13/14** captures, monotone 4/4 across the ladder) while ours is
   **pinned at 0.094 dB/oct and moving the wrong way**. Size available: **82 %** of GATE Q's `D(f)`.
   ⭐ AF6's −1.185 came from the **closed-form** cascade curvature; AH7 re-derives **−1.199** from the
   **rendered** model's measured curvature — **1.2 % apart** (s137).
   **SIX gates a candidate must pass, all cheap, all pre-registered.** ⚠ When a session adds one,
   **add a ROW** — this list grew from three to six as paragraphs, and that is what forced two
   re-archives:
   | # | gate — what a candidate must satisfy | s |
   |---|---|---|
   | 1 | **Frequency-dependent, NOT a constant tilt.** The deficit steepens **−0.39 / −0.78 / −1.44 dB/oct at 1613 / 2032 / 2560 Hz** (AG4) ⇒ a constant-tilt class is ⛔ refuted before it is built: right at one frequency, wrong at the others by a growing amount | 135 |
   | 2 | **Position AND shape — a NUMBER, not an implication (AH7): AT MOST −1.199 dB/oct (range −1.193…−1.199) of drive-dependent tilt at the vertex before it OVERSHOOTS the position target**, against the −2.038 the reference carries ⇒ spending the reference's full tilt overshoots **1.70×**; the pedal's vertex is **1.35× sharper** (not AG6's implied ~1.6×). ⚠ Depends on **`C_model` only** — the stable half — so AH4b's BAR-SENSITIVE verdict on `C_pedal` does **not** reach it. ⚠ A **position ceiling, not a specification**: gate 1 already refutes delivering it uniformly | 137 |
   | 3 | **CLEAN stays bit-identical** — the clipper is OD-only | — |
   | 4 | ⭐ **GRUNT-SIGN CONSISTENCY** (free, threshold-free). The defect is the SAME sign at all three GRUNT positions (cut −2.407 / flat −1.913 / boost −1.098 dB/oct, 15/16 captures) ⇒ **a candidate whose own sign flips with that switch is refuted with no size argument at all.** Killed the `a0` candidate; costs one closed-form evaluation per GRUNT cap | 138 |
   | 5 | ⭐⭐ **POLE COUNT** (free, threshold-free). For a single real pole whose corner moves, `d ln\|dT\|/d ln f = 2/(1+u)`, **bounded above by 2 EXACTLY** ⇒ **one moving pole is refuted before it is sized**; what is needed is **two poles or a distributed mechanism**. ⛔ Do NOT say *"every adjacent pair exceeds the bound"* (that per-pair statistic is **not scale-free**, and the deficit is **not monotone** — interior minimum ~1348 Hz). ✅ Say: **the ENDPOINT exponent over the rising limb is > 2 at 5/5 half-widths, smallest 2.530** — what the pointwise bound exactly implies, needing no fit | 139/141 |
   | 6 | ⭐⭐ **THE CARRIER'S OWN FREQUENCY DEPENDENCE MUST *RISE* NEAR THE VERTEX — a POSITIVE SPECIFICATION, not another veto.** Mechanisms cornering *below* the vertex deliver a tilt change falling as ~**f^−1.9** where the deficit rises as **f^+2.8** — opposite sign, refuting with no threshold and *stronger* than gate 5's bound ⇒ **a viable carrier must have structure AT or ABOVE ~2.9 kHz** | 140 |
   ⭐⭐⭐ **GATE 6 SHARPENED INTO A BAND (AL5), AND THEN THE BAND WAS SEARCHED AND FOUND EMPTY
   (AM, s145) — THAT PAIR IS THE ITEM'S CURRENT BRIEF.** A **complex pole pair** is the one structure
   clearing gate 5's real-pole bound (a sum of f² terms is still f²), and only from a narrow
   position: a **Q/damping** route needs a resonance at **~2.3–2.8 kHz with the vertex on its UPPER
   skirt (w ≈ 1.07–1.28)**; an **f0-move** route needs **~3.2–5.8 kHz**. ⛔⛔ **GATE AM then censused
   all 24 stages and `resonances at or upstream of the clipper = 0`, exhaustively rather than at the
   shipped point** — the chain's only complex pair anywhere is IC4_A, post-clipper, failing at its
   own Q. ⇒ **item 6's carrier is either a structure the model OMITS, or it is not a resonance.**
   Both branches: the two refuted rows below, and `docs/session-log.md` SESSION 145 `▶ NEXT` #1.
   ⭐ Convergence worth noting: **AA6 and AD5 narrowed this item to a DAMPING / LOADING class from
   statistics sharing no arithmetic with AL5**, and the Q route is exactly that class.
   ⛔⛔ **THE "next screen belongs pre/at-clipper" INSTRUCTION IS SPENT (s139/s140): that side is
   screened to exhaustion and all five named carriers on it fell** (rows below). What is left is a
   **frame** question, not another element. ⚠ AF6's broadband extrapolation is an **assumption about
   shape** (gate 1 measures it); the −1.185 itself is **local**.

   ⛔⛔ **CANDIDATE CLASSES ALREADY REFUTED — each has a CLOSED/REFUTED row; do not re-derive any of
   them.** This list is the item's real value, and it is why the search space above is narrow:
   | refuted class | why, in one clause | s |
   |---|---|---|
   | dynamic R19 supply sag shifting the `C14∥R18` corner | the closed-loop corner is **6.29 kHz, not the 2.19 kHz bare pole**, and it moves the peak **UP** as `a0` falls — the pedal walks down | 125 |
   | every effective **element-value drift** (sag, junction capacitance, any R/C) | refuted on **DIRECTION** (drift moves both features the same way, the device moves them opposite) — ⛔ **not** on AA6's ratio-invariance argument, which our own baseline breaks by 44.5 % | 129/130 |
   | one single mechanism for the SK **and** bridged-T halves | the two axes are **~ORTHOGONAL** (AB3): notch ≈100 % bridged-T, peak ≈79 % Sallen-Keys | 130 |
   | the SK axis as a fix for GATE I's 8–16.3 kHz gap | different mechanism **classes** (filtering vs generative) and **36–46× too small**; deleting both SKs outright still falls 1.6–3.2 dB/oct short | 132 |
   | the SK-**bandwidth** frame as a MECHANISM (falling GBW, slew, rail clamp, input C, film-cap Vco) | **0 of 5 reach**; GBW is **small-signal**, so no amplitude moves it at all — and we already ship **seven** post-clipper amplitude nonlinearities that W6 measures moving this peak **0.21 %** | 134 |
   | a **constant** drive-dependent tilt | AG4, gate 1 above | 135 |
   | the clipper's own **`a0` sag** (the ONE drive-dependent mechanism the model already ships at/before the clipper) | its sign **flips with the GRUNT switch** and the defect's does not (1 of 3 positions), and it reaches **20.7 %** at `a0 → 1` | 138 |
   | the **J201's Miller / junction capacitance** | the stage has **\|A\| = 0.565 < 1**, so there is no Miller multiplication to modulate; **0.17 %** of budget at 2.5× the datasheet max | 139 |
   | **IC2_A's GBW and slew** | GBW is **small-signal** (AF2, inherited — no amplitude moves it); slew has a **12× margin at the vertex** | 139 |
   | the **GRUNT caps' voltage coefficient** | moves the tilt **POSITIVE at all three positions**; the defect is negative at all three ⇒ **0 of 3 on sign** | 139 |
   | ⭐⭐ **ANY single moving pole** — i.e. the whole "a capacitance grows with drive" class, whatever the element | `d ln\|dT\|/d ln f = 2/(1+u) ≤ **2 exactly**`; the deficit's **ENDPOINT exponent over the rising limb is > 2 at 5/5 half-widths (smallest 2.530)** ⇒ a candidate needs **two poles or a distributed mechanism**. ⚠ Re-measured s141 at 4× the n; quote the endpoint reading, **not** AJ2c's refuted "every adjacent pair" | 139/141 |
   | **both SHIPPED Sallen-Keys** as the complex-pair carrier | the pair is the one structure that clears the real-pole bound, and **neither is positioned to**: IC4_B at **w = 0.27** (own f² regime, 1.20/1.48), IC4_A at **w = 0.88** (essentially AT resonance, where the Q-mechanism crosses zero) ⇒ **0 of 2** against a 2.685 target. ⭐ s145 sharpens IC4_B: at **Q = 0.4635 < 0.5** it is **OVERDAMPED — not a mis-placed resonance, not a resonance at all** | 141/145 |
   | ⭐⭐⭐ **ANY resonance in the SHIPPED MODEL at or upstream of the clipper** — i.e. the whole complex-pair route on the side AF6 requires | the census finds **0**, and exhaustively: every pre/at-clipper stage is passive RC (real poles by the theorem, **asserted on the stamps**) or the clipper's own loop, whose discriminant is **≥ 0 for every R, C and a0** by AM-GM ⇒ **no re-fit can create one**. The chain's ONLY complex pair anywhere is IC4_A, post-clipper, and it fails at its own Q | 145 |
   | the **J201's SHAPER**, all three routes (as shipped / gm sag through `k(s)` / amplitude-dependent compression) | memoryless ⇒ a pure gain change (**<1e−14**); gm sag is **2.46 %** at `gm→0` AND falls as **f^−1.9** where the deficit rises as **f^+2.8**; compression bounded **for any shaper** by the shelf's 0.0274 dB/oct. Root cause: the shelf corners at **219/292 Hz**, a decade below the vertex | 140 |
   | ⭐⭐ the **J201 drain node's OUTPUT RESISTANCE** (`ro`/`rq2`) sagging with the operating-point current — the carrier s139/s140's exhaustiveness claim MISSED | **Three interlocking refutations, so no choice of direction rescues it:** ⚠ **numbers RE-QUOTED s149 on the corrected ladder:** the sign-admissible direction (`L→∞`) reaches **1.334 %** of budget; the direction that reaches is now only **23.0 %** (`L→0`) and has the **wrong sign at 10/10** of AL4's limb centres; and **both** fall with frequency (**f^−1.78**) where the deficit rises (**f^+2.78**). ⇒ **NEITHER direction reaches**, so the physical direction of the Id shift cannot change the verdict and the shaper-rectification measurement is NOT owed. ⭐ Root cause AN3b, weakened but standing: `Zout/Zin = **4.97:1**` at the vertex (⛔ **not** the 27:1 s148 published) and `\|Zin_ladder\|` falls at **−0.455 dB/oct** (not −1.75) ⇒ a drain-node source-impedance perturbation is still largely spent there — AK's route 2 (f^−1.87), AJ's moving-pole class and this still share a falling exponent | 148 |
   ⭐⭐⭐ **⇒ EVERY NAMED CARRIER ON BOTH SIDES OF THE CLIPPER IS REFUTED — INCLUDING THE J201's
   OWN NONLINEARITY (s140) AND ITS DRAIN OUTPUT RESISTANCE (s148).** ⚠⚠⚠ **BUT THE SENTENCE HAS NOW
   BEEN FALSE TWICE, SO READ IT AS "every carrier that has been NAMED" AND NOTHING MORE.** It was
   written at s139/s140 and was **false until s148** (which found `ro`/`rq2` live and refuted it),
   and s149's mechanised audit then found **(a)** that all three pre-clipper gates had been screening
   the **DRAWN** treble ladder rather than the shipped one, and **(b)** one genuinely unscreened
   lever:
   ⭐⭐⭐ **THE LIVE PRE-CLIPPER LEVER (s149): a DRIVE-DEPENDENT TREBLE-LADDER `Zin`.** AN3b's
   refutation of the drain-node **source** impedance is, by AO1c's exact sensitivity identity, an
   **amplification** of the **load** side: **S_zin 0.836 vs S_zout 0.168 ⇒ 4.97× the lever**, on the
   one parameter (`zin`) that AK's own mechanism function accepts and that AO2 classifies **KA-ONLY**
   (moved only inside a known-answer sub-gate). ⚠⚠ **This is a SPECIFICATION, not a candidate — no
   physical carrier is named, and gate 5's `≤ 2` bound still applies to any SINGLE element drift in a
   network AM2 established is all-real-pole.** ⇒ screen it by asking *"which perturbation of this
   network can rise as f^+2.8 at all"*, never from a component list; a null answer there closes the
   pre-clipper side properly and is a STRONGER result than another element refutation. Two
   CLOSED/REFUTED rows carry it. ⚠ The deficit is untouched
   by this: still measured, sized and twice-localised (AG5 **1.72×** the requirement, same sign
   13/14). ⚠ **AB6's arithmetic is likewise untouched** — a correct **SIZING** of how far each feature
   must move, never a claim that anything moves it (a sizing is not a mechanism —
   `measurement-discipline.md` §1, s134). Both sub-targets stand; **the bridged-T half is unowned**:
   | axis | required move across the ladder | carried by |
   |---|---|---|
   | treble peak | **SK time constants × 1.1113** (SK corners **−10.01 %**) | the two Sallen-Keys, 79 % |
   | bridged-T notch | **bridged-T time constants × 0.9337 (−6.63 %)** | the bridged-T, ~100 % |
   ⚠ AF6's tilt moves the notch only **+0.83 %** against the required **+7.14 %**, so it is
   **peak-only** — orthogonality reproduced from a third construction.
   ⭐⭐⭐ **TWO MORE INSTANCES JOINED IN s131, ON A NEW AXIS — *DEPTH*, NOT CENTRE FREQUENCY**
   (GATE AD; bleed-free, driven ladder, both sides, one estimator). Everything above is about where a
   feature SITS; these are about how DEEP it is:
   | feature | pedal (ND) depth vs drive | model | ⇒ |
   |---|---|---|---|
   | bridged-T dip (~640–716 Hz) | **FALLS monotonically, 3/3 GRUNT positions** (spans 1.30 / 2.20 / 1.49 dB) | **pinned: 0.02 / 0.19 / 0.04 dB** | item 6's signature on the depth axis |
   | **4.5–6 kHz null** | **RISES monotonically, 3/3** (spans 2.60 / 7.55 / 3.41 dB; GRUNT cut 0.92 → 2.19 → **8.47**) | **FROZEN: 0.01 dB span in all three, at 0.69–0.70 dB** | ⚠⚠ **we appear to have NO NULL THERE AT ALL** |
   ⭐ A notch whose DEPTH collapses with drive is a **DAMPING / LOADING** change — the class AA6
   narrowed to, corroborated from a statistic sharing no arithmetic with it. ⇒ **a candidate must
   compress a notch's depth with drive, not merely slide centres.**
   ✅✅ **THE 4.5–6 kHz ROW WAS THEN MEASURED (s133, GATE AE) — AD5b RIGHT, WITH ONE QUALIFIER THAT
   CHANGES WHAT A CANDIDATE MUST DO:** the model holds **NO interior extremum in 9 of 9** bleed-free
   driven cells (threshold-free — the curve is monotone) against ND's 6 of 9 deepening monotonically,
   **but is not featureless there** — on the LEVEL ladder it carries a **MIX cancellation** that dies
   with the clean tap. ⇒ **the target is ND's DRIVE-GENERATED null: ours is a balance, theirs is a
   balance PLUS something the OD path generates, so a candidate that only re-tunes filters cannot
   address this row.** ⛔ Do NOT re-open "is our prominence there really zero" — measured, with a
   synthetic known answer. ⛔ Nothing there is graded against hardware (`reference-sources.md` §1:
   **neither** reference). ⚠ Quote the MEASURED band, not the "4.5–6 kHz" label — CLOSED/REFUTED row.
7. ✅ **DONE, SESSION 146 — THE MASTER TAPER IS RESOLVED AND FOUR CONSTANTS SHIPPED**
   (`analysis/master_taper_makeup.py`; five CLOSED/REFUTED rows carry it). The s120 `gain-n18`
   ladder was necessary but **not sufficient** — on its own it moves the ladder ≤0.593 dB against a
   1.075 dB floor. What resolved it was the **user's trust statement**, which turned the fit into a
   CONSTRAINT through the one interior position that has no knob freedom.
   ⛔ Do NOT re-open "re-fit the MASTER taper to the ladder" — a pure re-fit is **inside the knob
   floor** and changes nothing real; the shipped curve now sits at **0.6× the floor** and is exact
   at the trusted point. ⛔ Do NOT add a fourth segment.
   ⚠ **No new capture was needed**, so this closes without spending capture access.
8. ⚠ **`captures._GAIN_SESSION_MEASURED_DB` has no −18 entry** — triply corroborated at 18.000 dB,
   deliberately NOT added (it would change graded membership; three `_gain-n18` captures currently
   fail `comprehensive_report`).
9. ⚠⚠ **STATUS AMBIGUOUS — flag to the user rather than assume closed (found s122).** *"The LEVEL law
   is a TOPOLOGY question — discriminate GATE L4's (a) [pedal's mix network differs structurally] vs
   (b) [something downstream of LEVEL in the pedal is level-dependent]"* was an explicit NEXT-list
   item from s104 to s111, then silently stopped appearing at s112 with **no ⛔/REFUTED/CLOSED marker
   anywhere**. It is **not** GATE U's "LEVEL is dilution" (s116, closed — that is the OD-residual
   axis); this is whether the LEVEL control's *own* absolute law (GATE K's 9.3 dB defect) is a
   structural mismatch or a level-dependent downstream stage. Neither branch is discriminated.
   `docs/session-log.md` SESSION 104–111; `analysis/level_taper_gate.py`.
   ⭐⭐ **THE DISCRIMINATOR IS MEASURED TWICE, ON TWO FEATURES, BOTH AGREEING — AND BOTH READS WERE
   FREE, ALREADY IN STORED REPORTS.** Two mixers summing the same two paths must respond to LEVEL the
   same way, so a difference in that sensitivity measures L4(a) vs (b) directly — and it is a *shape*
   question, which the gain-matched matrix is not blind to the way it is blind to L4's absolute
   9.3 dB. **Bass notch** (s125, 7 detents): the pedal is **~2×** more LEVEL-sensitive than us
   (30.0 % vs 17.2 %). **`treble_notch`** (s133, AE4, the 4 detents where both sides resolve it):
   **2.7×** (24.3 % vs 9.1 %). ⇒ the item has an instrument and two numbers, not just a question.
   ⚠⚠ **MATCHED DETENTS ONLY — the raw spans read 9.1 % vs 133.5 %, and comparing THOSE is a
   membership difference wearing a physics number** (we mute at LEVEL min and lose the feature above
   noon; ND keeps it nearly to the top). ⚠ Neither instance discriminates (a) from (b).

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
could carry it) and `D(f)` (*"only a nonlinearity can carry it"*).** So a nonlinear target has been
sized since session 109 and appears on no work list. ⛔ **Quote `D(f)` as 2.64 dB, NOT the s109-era
3.01** — see its own CLOSED/REFUTED row. `kInputRef` (s109) was the first move in that direction and
is the only constant ever to close an OD gate row. ⇒ **A3's honest status is "static excluded,
dynamic UNTESTED"**, and it is the same target as item 6 — which is stimulus-dependent by
construction and sits in the OD path only, where A3 lives.
⛔⛔ **CORRECTED s147: this block used to end *"its most likely carrier is item 6's dynamic-sag
candidate"*. That candidate is REFUTED — twice** (s125, the R19-sag/`C14∥R18` corner, which moves
the peak the wrong way; s138, the clipper's own `a0` sag, whose sign flips with GRUNT). Item 6 is
still A3's dynamic half, but **every named carrier for it is refuted** and the open question is the
frame — do not inherit a mechanism noun from this sentence.

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

⛔ **DO NOT TRANSCRIBE GIT STATE HERE. Run `git status --porcelain` and `git log --oneline -5`** —
they are the live, authoritative answer (`rebuild-targets-dont-transcribe`; the old per-session
"Uncommitted at session N" blocks were exactly this mistake, repeated 28 times, and are archived
verbatim in `docs/session-log.md`). Every session up to and including the last one named in
`git log` is committed; nothing older is owed.

Regenerable/gitignored, not part of any commit decision: `analysis/reports/*.json`,
`analysis/fit_logs/*.log`, `build/**`.

**Cache / rebuild state.** ⛔⛔ **SESSION 146 CHANGED DSP BEHAVIOUR — the first since s124.** It
shipped the 3-segment MASTER taper (`MasterOut.h`, `FitParams.h`, `PedalChain.h`,
`offline_render.cpp`, `MasterOutTest.cpp`), built **once** with every `src/` edit batched into that
build (`build.md`'s rule; no matrix render in flight — checked with `pgrep` first, s124's lesson),
and re-baselined to `s146_mastertaper.json`. **ctest 19/19.** Since s128 only s142 (comments only,
deliberately NOT rebuilt), **s144** (BUILT, adding `OSFidelity`) and s146 touched `src/` at all.

⚠⚠ **BUDGET ~25 MIN FOR THE NEXT MATRIX RUN** — any relink moves the `(size, mtime_ns)` that
`_cache_key` hashes, so warm entries go unreachable. This is the documented price of compiling
(`build.md`'s batching rule; s127's lesson, repeated by s124/s144/s146), a **speed** cost only, and
nothing is corrupted. Arithmetic: the CLOSED/REFUTED row + `docs/session-log.md` SESSION 142 §5.4 /
144. ⛔ Do NOT "fix" it by touching the cache key — the key is right.

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
  - **The inventory itself is `analysis/captures/` — read the directory, not a transcription.** Four
    batches landed against the closing window: **s111** (26: DRIVE ladder, LEVEL×BLEND 3×3, MASTER
    `gain-n12`, EQ-0700 pairs), **s112** (`level × blend` grid + re-captured twins + two `gain-n18`
    MASTER that resolved the pinned top end), **s113** (the head-item blocker plus 8 EQ hedges the
    user added independently — unused so far, no claim about what they show), **s120** (the 9-detent
    `gain-n18` MASTER ladder). Per-batch purpose and analysis: `docs/session-log.md` SESSION
    111–113 / 120.
  - ⚠ **The s120 ladder carries the user's own accuracy caveat, verbatim — do not drop this
    qualifier:** *"the positions are best estimates, so some variance is expected. I would say the
    0700, 1200, 1700, 0930, and 1430 are somewhat the most accurate."* ✅ **ANALYSED AND SPENT at
    s146** (item 7, closed): the ladder alone moves ≤0.593 dB against a 1.075 dB knob floor, so what
    resolved the taper was the user's later **trust statement**, not this data.
- ⚠ **Two ear-matched (not measured) listening-test leads, volunteered session 120 ahead of losing
  physical pedal access — record as leads, not verdicts:**
  - ✅ **MASTER — CHECKED AND CLOSED, SESSION 146.** The lead ("plugin needs ≈0.61 to match")
    **corroborates the s146 taper defect directionally** — an ear said turn it up at noon, and the
    captures independently measured the model **1.86 dB quiet there**, now fixed. ⚠ But the flagged
    coincidence with `masterTaperBreak = 0.5927` **dissolves rather than resolving**: the two
    candidate explanations sit **0.0024 of rotation apart**, below an ear's resolution, so it was
    never evidence of a bug. See the CLOSED/REFUTED row.
  - **DRIVE/distortion**: plugin needs ≈0.8 to match the pedal's distortion at DRIVE max; tracks
    closely at DRIVE≈0.5. User-confirmed as saturation-based, not a separate gain-staging axis.
    Independently corroborates the standing head item (GATE Q/S: the model's OD path saturates
    differently, worst at DRIVE max) and is exactly what session 118's clamp fix targeted — open
    question whether the listening test predates or postdates that fix (open work item 11).
- **Two shipped bug fixes, pre-Phase-9 (2026-07-23), both in `src/PluginProcessor.{h,cpp}`** — the
  **bypass-engage click** (each channel stepped a throwaway *copy* of the smoothers, so the members'
  state never advanced) and the **knob-turn zipper, worst on DRIVE** (`applyParams()` runs once per
  block, so a fast sweep jumped the raw APVTS value uninterpolated; fixed with `SmoothedValue::skip`
  at knob-value level, ~20 ms). Full diagnosis: `docs/session-log.md`.
  ⚠ **Still open, and NOT covered by either fix:** switches (ATTACK/GRUNT/mid-freq/bypass/
  `dist_engage`) are unsmoothed — the harder glitch-free-crossfade problem (`circuit.md`,
  `TrebleAttack.h`).
