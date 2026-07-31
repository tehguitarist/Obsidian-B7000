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

### Where we are

**Phases 1–8 are COMPLETE.** The plugin builds, loads in a DAW, is fully playable, and the UI is
done. **Phase 9 (reference validation) is the only phase in progress**, and Phase 10 (perf pass +
release) has not started. ctest **16/17** — the single failure is the pre-existing session-44
`OSValidationTest` (`amp 0.35: 2x −25.6 / 4x −32.1 / 8x −23.6`), unchanged to the digit for 45
sessions and tracked as its own decision below.

⚠⚠ **The last constant SHIPPED was session 44.** Sessions 45–88 changed nothing audible — they were
measurement and instrument-building (sessions 63/64 touched `src/`, but every new parameter defaults
to the drawn network, i.e. a proven no-op). `git diff HEAD -- src/ tests/` is clean. That is the
context for the reset: the analysis has been sound and the corrections real, but the *decision* steps
kept being deferred to more measurement, so nothing converged on a shipped change.

**Current grade** — 129 captures, shipped defaults, `analysis/reports/s74_baseline129.json`
(`matrix_grade.py` + `shape_gate.py`; distribution measured session 89). ⚠ **These are at the OLD
25 Hz – 12.9 kHz range and WILL move when item 0 below widens it to 16.3 kHz and repairs the FR
instrument — re-baseline them before comparing anything against them.**

| subset | rows | band-RMS | median \|Δ\| | p90 | max | decomposition (level/tilt/curv/LOCAL) |
|---|---|---|---|---|---|---|
| **OD** ex gain-n12 | 320 | **2.743** | 0.85 | 5.87 | 36.2 | 1.767 / 1.659 / 1.347 / **2.607** |
| **CLEAN** | 168 | **0.408** | 0.21 | 0.66 | 1.99 | 0.179 / 0.303 / 0.151 / 0.258 |
| **THD** (OD) | 228 | 9.292 | — | — | — | **6.202** / 4.281 / 3.257 / 5.147 |
| OD gain-n12 [bad] | 16 | 3.621 | — | — | — | capture defect, session 48 — do not fit to it |

⭐⭐ **CLEAN IS FINISHED — 97.1 % of its band values are within ±1 dB, max 1.99 dB.** A2c closed it
and nothing since has moved it. **Regression-guard it; do not fit it further.**

⭐ **The largest single number in the project is the THD `level` term, 6.2 dB** — the model's
distortion *amount* is systematically wrong. It has sat in this table since session 63 while
attention went to FR shape. It has never had a dedicated session.

### THE RELEASE GATE (agreed with the user, session 89)

Phase 9 closes and Phase 10 begins when the SHIP column is met. Percentiles are over band values,
OD ex gain-n12.

⚠ **The graded range is now 25 Hz – 16.3 kHz, widened from 12.9 kHz in session 89.** `matrix_grade`'s
`GRADE_HI = 12901.6` was justified by a comment claiming the 16 kHz band "sits in the sweep/cab noise
floor" — there is no cab in this pedal (leftover template text) and it had never been measured.
Measured: **CLEAN at 16255 Hz reads median 0.62 / p90 1.70 / max 3.14 dB.** It is perfectly readable.
The sweep is 20 Hz – 20 kHz, so the stimulus supports it.

| subset | region | statistic | **SHIP** | stretch | now |
|---|---|---|---|---|---|
| CLEAN | 25 Hz – 16.3 k | median / p90 | ≤0.3 / ≤0.8 | — | 0.21 / ~0.7 ✅ **MET** |
| **OD** | 100 Hz – 8 kHz | median / p90 | **≤0.5 / ≤2.0** | ≤0.5 / ≤1.0 | ~0.6 / ~5.6 |
| **OD** | 25 – 100 Hz | median / p90 | **≤0.7 / ≤2.5** | ≤0.5 / ≤1.5 | 1.25 / 5.66 |
| **OD** | 8 – 16.3 kHz | median / p90 | **≤0.7 / ≤2.5** | ≤0.5 / ≤1.5 | 0.67 / **16.6** |
| **OD** | any region | p99 ("extremes") | **≤4.0** | ≤3.0 | ~14 |
| **THD** | OD | level term | **≤3.0 dB** | ≤2.0 | 6.20 |
| headline | OD ex gain-n12 | band-RMS | **≤2.0 dB** | ≤1.5 | 2.743 |
| notches (320 Hz &c.) | — | best effort, reported per band, not gated | — | — | +26 dB |

⚠ **The OD p90 ≤2.0 dB bar depends on A3 closing.** If the timeboxed A3 attempt fails AND the
fallback correction network underdelivers, that number has to move to ~3.0 — flagged now rather than
discovered later. ⚠ Departures from the ND captures TOWARD a documented hardware trend are a **PASS**
(`reference-sources.md` §1), so the gate is a target, never a veto on a hardware-directed fix.

### Open work, in order

0. ⭐⭐ **FIRST: repair the FR INSTRUMENT, because the release gate is measured with it.**
   `analyze.transfer()` is a CSD estimate that only partially rejects harmonics, so every FR number
   taken at hot drive — including the gate above — carries unknown nonlinear contamination. Add an
   **H1-only Farina read** (the machinery already exists in `analyze.harmonic_thd_curve`), gate it
   with a known-answer self-test, and **re-baseline the gate numbers against it.** Extend
   `matrix_grade.GRADE_HI` 12901.6 → 16255. Expect this to move the HF tail a lot and possibly the
   whole OD headline; it is a measurement correction, not a model change, so nothing ships from it.
   ⚠ Per §1 of `measurement-discipline.md`: do not fit against an instrument you have not validated.
1. **`c21R` 220k → ~130–150k.** One constant. Hardware wants ~11–12 Hz where we sit at 7.2 Hz matched
   to ND (`reference-sources.md` §2). Flagged session 71, never done. Half a session.
2. **`jfetSatNeg` 0.76054 → ≈1.9** (low-drive even-order). Located session 80, matrix-judged sessions
   81/82: free move is `a` ≈ 1.8–2.0, crossing measured at 1.77. **Blocked only on a WEIGHTING
   JUDGEMENT** (mid-drive cost vs low-drive gain) — a decision to put to the user, not a measurement.
   ⛔ Do NOT re-render more `a` candidates; the matrix has said all it can (sessions 82/84).
3. **The THD `level` term (6.2 dB).** Largest number on the board, never had its own pass. Start from
   `shape_gate.py`'s THD decomposition and the drive/level axes, not from FR.
4. **Re-fit the two-pole ATTACK against session 70's CORRECTED spec, then ship-or-park.** The topology
   is already in `src/` (defaults to the drawn network). Session 70 corrected the requirement it was
   fitted against — null moves **7.13 Hz, not 17.58**; boost width **19.2 Hz, not 27.1** — and it has
   not been re-fitted in the 18 sessions since. Addresses the **+26 dB @ 320 Hz** band, the largest
   single-band error in the matrix. Gate: `attack_render_gate.py` then the 129-capture matrix.
5. **A3 — ONE timeboxed attempt (user decision, session 89).** ≈5–7 dB OD-vs-bleed imbalance over
   100–400 Hz, corroborated by two instruments sharing no machinery (sessions 85/86). Session 50
   proved no single element closes it; session 52 proved no *post-clipper linear* element of any order
   does; session 53 inverted the post-clipper restriction. **The only region not ruled out is
   inside/before the clipper** (`Clipper.h:309` — `a0` has no frequency dependence and the inverter no
   output impedance, both derivable from the DAFx-2020 two-MOSFET model). **Hard stop at one session**,
   then fall back to a fitted correction network (the user authorised breaking the schematic in
   session 51).
6. **A4 re-grade + the GATE-9 report**, then the `OSValidationTest` decision, then **Phase 10**:
   B (perf/HQ pass), C (carry-forwards incl. the VU idle gate vs makeup 2.599), D (release).

### Standing rules that must not be lost

- ⚠⚠ **`analysis/captures/` is a recording of the NEURAL DSP plugin, not hardware.**
  `.claude/rules/reference-sources.md` is the authority rule — read it before treating any capture
  number as ground truth, and before calling a move away from the captures a regression.
- ⭐ **The generalisable measurement traps are collected in
  `.claude/rules/measurement-discipline.md`.** ~40 of them, each one paid for by a real session.
- ⭐⭐ **NEW, session 89 — the HF OD error is REAL, LOCALISED and TRACTABLE, and our FR instrument
  cannot currently tell us whose it is.** All twelve worst OD rows are the same band (12901.6 Hz,
  26–36 dB), all on `level-1700` rows where the clean bleed is exactly zero by topology, so the
  measurement IS the raw OD path. There ND's OD path *gains* 24 dB at 12.9 kHz as drive rises
  (−15.3 clean → +9.0 at `sweep_drv_-6`) while ours rolls off — which is what the two
  schematic-verified Sallen-Key LPFs (10.7 kHz, 3.3 kHz) must do. On `ref-od` (bleed present) the two
  sides agree to **0.4 dB**, because the bleed masks it on both sides.
  ⛔ **DO NOT dismiss this as "ND aliasing" — that is not established and it is not a reason to skip
  the band** (user, session 89). Two things must be measured before anything is concluded:
  **(a)** `analyze.transfer()` is a **cross-spectral-density estimate** (`|Pxy|/Pxx`), not a Farina H1
  separation, so it only PARTIALLY rejects harmonic and aliasing content — at hot drive both sides'
  HF bands carry nonlinear content, and "ND aliases" and "our FR instrument is contaminated" are
  currently **indistinguishable**. We already have proper Farina order-separation in
  `analyze.harmonic_thd_curve`; the FR path just does not use it. **Build an H1-only FR read and
  re-measure.** **(b)** Only then ask whether the residual is ND's artefact or our Sallen-Keys —
  and if it IS ND's artefact, compensate for it in the MEASUREMENT rather than excluding the band.
  ⭐ The OD **median** at 8–16 kHz is 0.56–0.75 dB, i.e. fine — it is the TAIL that explodes, so this
  is a subset of rows failing badly, not a noise floor. It is gated (see the release gate above).
- ⚠ Never quote a matrix total without its capture count; membership changes have faked a regression
  seven times (`aggregate-moved-check-membership-first`).

### Uncommitted at session 89

Sessions 55–88 are uncommitted: `CLAUDE.md`, `docs/phase9-validation.md`, the new
`.claude/rules/reference-sources.md`, ~15 new `analysis/*.py` tools, and this session's
`docs/session-log.md` / `docs/phase9-gap-log.md` / `.claude/rules/measurement-discipline.md`.
**Nothing in `src/`, `tests/` or `analysis/captures/`.** Gitignored but regenerable:
`analysis/reports/*.json`, `analysis/fit_logs/*.log`, `build/**`.

## Project-specific carry-forwards

> Record decisions, measured constants (kInputRef, rail voltages, makeup), and open questions here
> as you go, so the next session resumes cleanly.

- **BUG FIXED 2026-07-23: bypass-engage produced a constant click train, louder with more DRIVE.**
  Root cause in `PluginProcessor::processBlock` (nothing DSP/circuit-related — a plugin-level
  smoothing bug): `bypassMix`/`inputGain`/`outputGain` were copied into a per-channel local, and
  only that **copy** ever called `.getNextValue()`; the processor's own member `currentValue` never
  advanced. `SmoothedValue::setTargetValue()` no-ops once the target stops changing (true for every
  block after the first following a bypass press, since the target then just sits at 0 or 1), so
  the member stayed frozen at whatever `currentValue` it had when the target last changed — and
  every following block re-ramped from that same stale point instead of continuing. That produced a
  periodic partial wet/dry blend-in at every block boundary forever after the first bypass toggle
  (not just during the ~5 ms transition) — the click, louder at higher DRIVE because the "wet" side
  briefly blended in is the gain-boosted/distorted signal. **Fix:** step each smoother exactly once
  per sample into a shared per-block ramp buffer (`inGainRamp`/`outGainRamp`/`bypassMixRamp`, sized
  in `prepareToPlay`) and have both channels read that same array, instead of each channel owning
  and advancing a throwaway copy. Preserves "both channels step identically"; the member's real
  state now persists correctly across blocks. `src/PluginProcessor.{h,cpp}`; ctest still 16/16 (no
  console test exercises the plugin-level `AudioProcessor::processBlock` path, which is why this
  didn't trip a gate — worth keeping in mind for any future `SmoothedValue` usage in this file:
  never let a per-channel/per-voice **copy** be the only thing that calls `getNextValue()`).
- **FIXED 2026-07-23 (same session, user follow-up): rapid knob turns produced zipper clicks,
  worst on DRIVE.** Not a bug like the above — `PedalChain::applyParams()` is deliberately called
  once per block, not per sample (PedalChain.h: the MNA-based stages, Baxandall/MidBand, only
  re-invert their matrix on a dirty flag; doing that per sample would be a real CPU regression). So
  a fast knob sweep (or automation) could still jump the raw APVTS value a lot between one block and
  the next, and every stage recomputed its coefficients from whatever value it got with zero
  interpolation — audible as a step in signal amplitude at the block boundary, worst on DRIVE
  because its gain range is 4x-78x. **Fix:** smooth the 8 continuous pots (master/blend/level/drive/
  lo/loMid/hiMid/hi) at KNOB-VALUE level via `SmoothedValue::skip(numSamples)` called once per block
  directly on the member (not a per-channel copy — see the bypass fix above; the member itself is
  what advances this time, so the same bug class doesn't recur). This bounds how far a stage's
  coefficients can move in one block without adding any per-sample cost or touching the "recompute
  once per block" architecture — still exactly one MNA re-invert per block, just fed a value that
  can't jump arbitrarily far. `~20 ms` smoothing time (`kPotSmoothingSeconds`), matching the existing
  `inputGain`/`outputGain` constant. `readParams()` signature changed to take the 8 pre-smoothed pot
  values as params (switches — attack/grunt/mid-freq/bypass/dist_engage — still read raw; they're
  discrete topology swaps, not a smoothing gap). **Deliberately NOT fixed here:** clicks from
  flipping ATTACK/GRUNT/mid-freq switches — those are a separate, already-flagged, harder problem
  (glitch-free crossfade between two precomputed topologies, not a value-smoothing fix; see
  circuit.md/TrebleAttack.h "Phase 5 adds the glitch-free crossfade on top of this" and the GRUNT
  "deferred to Phase 6" note) — still open. `src/PluginProcessor.{h,cpp}`; ctest 16/16.
- **Target = Darkglass B7K Ultra** (schematic is the original-B7K "Black Mirror VII" clone; Ultra
  extras engineered on top). **8 pots**: MASTER[ENG], BLEND, LEVEL, DRIVE, LO, HI, LO-MID, HI-MID.
  Plus 3-way ATTACK[ENG] + 3-way GRUNT switches, and 3-position Lo-Mid/Hi-Mid freq selectors[ENG].
- **Engineered (not schematic-verified) parts** — flagged [ENG] in circuit.md: MASTER volume stage
  (post-EQ divider → IC6_B, also DI level); 3-way ATTACK (2-pos ULTRA-HI + centre Flat); switchable
  mid caps — Lo-Mid 47n/10n/2n2 (250/500/1k), Hi-Mid 15n/3n3/820pF (750/1.5k/3k). ✅ All six
  positions validated by nodal sim (±8.5% worst) AND the sim cross-checks against the p.3 measured
  tables (~3% / ±2.5 dB) — see circuit.md mid-band note. **Plus a 2nd DIST-engage
  footswitch** (real Ultra has 2 footswitches; ours only has 1 in the BOM) — model as a bool that
  overrides the BLEND crossfade to 100% clean, not a second bypass loop.
- **Web-confirmed 2026-07-19** (real Darkglass manual + reviews): Master/Attack wording and both
  mid-frequency sets match our `info.txt`/computed values exactly — high confidence. The DIST
  footswitch was new information, not previously in any doc.
- **Supply: single 9V, no charge pump.** 9V → D3 (1N5817) → +9V rail ≈ 8.6V. **VD = 4.5V**
  (R30/R31 10k/10k divider + 100µF, unbuffered). Op-amps TL072ACP/TL074ACN, clipper CD4049**UBE**.
- **Clipping = CMOS inverter (CD4049UBE) overdrive**, NOT diodes. D1/D2 (1N4148) are input rail
  clamps (~[−0.6, +9.6]V), rarely conduct. Model the 4049 transfer curve as the nonlinearity.
- **JFET stage (Q1/Q2 J201)** is an active gain stage (Q1 common-source + Q2 active load), not
  switches — needs a JFET device model or fitted gain+waveshaper. (See circuit.md / dsp.md.)
- **Non-WDF-native parts = ONLY the CD4049UBE clipper + the J201 JFET stage** (everything else is
  R/C/ideal-op-amp/diode). Modeling sources gathered 2026-07-19 → `docs/nonlinear-component-modeling.md`
  (+ 4 PDFs in `docs/refs/`: TI CD4049 datasheet, DAFx-2020 "Red Llama" CD4049-overdrive model,
  Fairchild J201 datasheet, DAFx-2024 JFET-WDF). Recommended: fit an asymmetric-tanh VTC waveshaper
  for the 4049 (DAFx params as ground-truth), and fit gain+soft-waveshaper for the J201 (part spread
  ~5:1 → must fit-to-capture, nominal SPICE won't match). **Pre-DSP capture plan is §4 of that doc**
  — do it in one matched session; it also resolves the IC2_B ~720 Hz bridged-T notch question.
- **Capture unit CONFIRMED = a real B7K Ultra, audio-only (¼" in→out, no internal probing).** Big
  win: we capture & VALIDATE all [ENG] features directly (Master, 3-way Attack, DIST footswitch,
  switchable mids incl. the 750 Hz Hi-Mid). Nonlinear models + the IC2_B notch are
  inferred from composite in→out (control-isolation + matched-pair diff). Finalized capture MATRIX
  (29 Tier-1 essential + 20 Tier-2 extended, explicit `key-value`-token filenames — no implicit
  state, see the grammar) = `docs/nonlinear-component-modeling.md` §4.
- **CORRECTED 2026-07-21 (pre-capture check):** the prior note here claiming `parse_capture()` was
  "added to `analysis/analyze.py`, tested against the whole matrix" was stale/wrong — that function
  didn't exist yet (still the template's `NotImplementedError` stub). **Now actually implemented in
  `analysis/captures.py`** (not `analyze.py`), against a fully explicit filename grammar (every
  filename = `key-value` tokens joined by `_`, ending in a required `base-od`/`base-clean` token;
  no parenthetical/implied state). Also fixed a real naming bug the old matrix had: `grunt-lo`/
  `grunt-hi` didn't correspond to any of GRUNT's actual three positions (`boost`/`cut`/`flat` per
  circuit.md's UI map) — corrected to `grunt-boost`/`grunt-flat` (baseline already covers `cut`).
  `python3 analysis/captures.py` (via `/opt/homebrew/bin/python3.11` — `python3` on this machine
  resolves to 3.13, which lacks numpy/scipy; pip installs against 3.11) self-validates all 49
  documented filenames with no captures on disk yet: 49/49 PASS. **`render_args()` ✅ IMPLEMENTED
  2026-07-22** against the now-existing `OfflineRender` CLI — emits every control explicitly (never
  leans on the binary's defaults), leaves `--in/--out/--os` to the orchestrators, special-cases
  `bypass.wav`, appends `extra_args` verbatim (how a `--fit` sweep varies one constant across a
  batch), and **does NOT pre-invert the EQ pots** (the dict is knob-space; OfflineRender applies
  `readParams()`'s `1-x` itself — inverting in both places mirrors every EQ fit while looking
  entirely plausible). Missing DC/rail values → take nominal from datasheets,
  calibrate the clip ceiling to the bypass+drive captures.
- **Value discrepancies resolved:** C33 = 22n (primary+BOM; backup's 2200pF is a different rev).
  GRUNT C13 = 220n (primary; backup 22n). Using primary values throughout. Both re-confirmed against
  BOM + schematic in the 2026-07-19 verification pass.
- **IC2_B recovery is a UNITY BUFFER, not a +12 dB active shelf** (verified in BOTH schematics —
  pin6 tied to pin7). The 100k/33k/680pF/22n parts are a passive bridged-T on the buffer output, not
  a feedback/gain leg. Consequence: **no recovery makeup gain exists** — do not budget +12 dB into
  gain-staging. Ideal sim of the bridged-T = deep ~720 Hz notch/scoop (tolerance-sensitive, surprising)
  → capture the real unit before finalising this section. Classic "same values ≠ same topology" trap.
- **C4 (JFET Q2)** connects gate→source(output) as a bootstrap, NOT gate→GND (was mis-stated).
- **R19 (1k)** is in the BOM but not yet located in the traced path — minor, non-critical, find it later.
- **Reusable crop tool** for the dense p.4 schematic: `schematics/crop.py` (see circuit.md crop index).
- **R19 (1k) RESOLVED (2026-07-19):** it's the CD4049's +9V supply dropper (only IC with one) —
  clipper clip-ceiling is BELOW the 8.6V op-amp rail and sags with signal. Calibrate the ceiling to
  captures, don't hardcode 8.6V. BOM fully reconciles (R1–R54 all located).
- **Tone stack fully node-verified (2026-07-19):** Baxandall (both wipers sum into IC5_C virtual gnd
  via R35/R36; C25/C26 run lug→wiper; R37 fb is 1 MΩ, schematic label "1m") and both mid stages
  (R41/R44 in→(−), R40/R45 (−)→out flat-unity legs; wiper→series-cap→(−)). Node graphs in circuit.md.
  Nodal sim validates all six [ENG] mid-cap positions (±8.5% worst) — per-position boost range varies
  (±14.5–28 dB), confirm against captures. GRUNT corners need the 4049's finite gain (~20–30) — model
  the clipper input as a coupled network, not ideal-virtual-ground.
- **C36 = 2u2 is schematic-verified** (EQ out coupling). Stock board has NO bias R on IC6_B(+) after
  C36; the [ENG] Master pot's VD leg supplies the DC path — cleaner than stock, no extra part.
- **UI assets ready in `ui/`** (knobs, footswitch, LEDs, switches, textures, VU trim — PNG with
  alpha, noon-position, rotation-safe) with prep guidelines in `ui/ui-replacements.md` (2x-resolution
  policy, crop-don't-stretch, resize-to-minimise). Use these for the Step 8 pedal face instead of
  procedural drawing where they fit; keep `src/ui/` LookAndFeel for the peripheral chrome.
- **UI assets + layout CSV LANDED (2026-07-20)** — base image `ui/b7k_texture_base.png` (1960×1540,
  no alpha), layout `ui/component positions.csv`, reference photo `ui/B7K ORIGINAL.jpg`. Full spec
  now in `ui.md` "Centre pedal face". Key facts: **CSV coords are base-texture pixel space** (origin
  top-left, X/Y = element centre, Width target, **blank Height = scale proportionally to Width**) —
  map every coord through one base-px→face-px scale. **Asset map:** knobs=`T_Knob.png`, footswitches
  =`Footswitch_up`/`footswitch_down`, LEDs=`blue_led_off`/`blue_led_on`, switches=`switch_up`/`_Mid`/
  `_down`, peripheral trims=`vol_trim.png` (NOT the old `Trim knob.png`). Two footswitches + two LEDs
  in the CSV (distortion + bypass) — confirms the [ENG] 2nd DIST footswitch. **ATTACK/GRUNT icon
  glyphs = render procedurally** (`juce::Path`, shelf lines/curves; CSV reserves 110×77 boxes) — I
  can draw these, no artwork needed from the user unless an exact match is wanted. LO-MID/HI-MID use
  text labels. **Switch-position→value mappings CONFIRMED by user 2026-07-20** (top/up→bottom/down),
  now in circuit.md: **ATTACK** up=Flat(C8 pole open)/mid=Boost(C8 bridges R8)/down=Cut(C8 shunts
  P→GND) — note centre=Boost, not the schematic's centre=Flat. ⚠ **CORRECTED 2026-07-20:** Cut is
  a C8→GND *shunt* (treble rolloff), NOT "R7-R8 junc→GND" (that earlier reading grounded node M and
  MUTED the path — wrong pole assignment; see circuit.md "ATTACK-SWITCH CORRECTION"). No position
  mutes; UI up/mid/down order unchanged. **LO-MID** up=500Hz(10n)/mid=1k(2n2)/
  down=250Hz(47n); **HI-MID** up=1.5k(3n3)/mid=3k(820pF)/down=750Hz(15n); **GRUNT** ✅VERIFIED at
  capture 2026-07-22: up/Boost=4n7∥220n(most)/mid/Cut=4n7 alone(least)/down/Flat=4n7∥47n(medium). That text: **font = Lexend Exa** (embed as binary data, this pedal's face text
  ONLY — peripheral chrome keeps its existing font), **colour = white**, opaque when selected,
  semi-opaque when not — replaces `PedalLookAndFeel`'s current `cSWLabelActive`/`cSWLabelInactive`
  light-/dark-blue constants. Full spec in `ui.md` "Centre pedal face"; plan updated in
  `docs/build-plan.md` Phase 8. Further pedal-face elements TBD until the assets land.
- **Full build plan: `docs/build-plan.md`** (2026-07-19) — step-by-step from submodules to release,
  with per-step validation gates and the capture-session checklist folded in.
- **UI pulled forward to Phase 4b (decided 2026-07-20 with user):** build a functional, APVTS-bound
  pedal face at the END of Phase 4 (before the Phase 5 clipper), so all Phase 5+ human-in-the-loop
  checks are done on real knobs/switches instead of the DAW's generic slider editor. Safe because
  APVTS is frozen at Phase 2 + UI is DSP-decoupled. Calibration-dependent polish (VU idle-gate
  threshold, final label opacity, headless scale gate) STAYS at Phase 8 — a second UI touch there is
  expected, not rework. Full rationale + scope in `docs/build-plan.md` "UI timing" + "Phase 4b".
- **Build-plan review pass (2026-07-20):** thorough gap analysis of the plan against calibration/
  validation/nonlinear docs + circuit.md; fixes applied to `docs/build-plan.md`. Biggest catch:
  **TL07x op-amp rail clamps were never scheduled anywhere** (calibration §6 requires them on every
  op-amp output; IC2_A at ×78 rails BEFORE the 4049 at max DRIVE; mids boost +28 dB) — now a Phase 4
  paragraph + gate item + risk #9. Also added: **LEVEL→BLEND pot loading** (not independent
  dividers; ≈3.5 dB crossfade imbalance at noon/noon — model the resistive network exactly, Phase 4
  item 6 + risk #10); bridged-T test-oracle caveats (oracle is unloaded; assert notch freq tight /
  depth loose, not ±0.25 dB at a notch bottom); treble/ATTACK stage-boundary decision (its input
  node is the JFET drain — pick one source-impedance convention for oracle AND WDF stage); `hq`
  APVTS-ID gotcha (can't "reserve" by omission — no audio/CPU impact, purely AU session-recall
  compatibility; **resolved: do BOTH** — version-hint every param `ParameterID{"id",1}` AND add
  `hq` now as a default-true no-op, decided with the user 2026-07-20); Phase 2 additions (bus
  layout, `ScopedNoDenormals`, `getBypassParameter()`); Phase 6 host
  `setLatencySamples()` on OS-factor change (distinct from the internal delay line); Phase 7 TL07x
  rail confirmation from captures; Phase 8 VU idle-gate recheck vs final makeup + don't-stall-on-
  assets fallback; interim `kInputRef` (~1–3 V/FS bass level) for Phases 4–6. `eq_reference.py`
  `bridged_t_tf` dead `Rload` param made functional (default None/unloaded — documented 717 Hz/
  −28.1 dB numbers unchanged, verified by re-run).
- **BLEND/bypass dry-wet phase-alignment gotcha added (2026-07-20, user's own hard-won lesson from
  another project) — covers BOTH delay and polarity, not delay alone:** (a) the clean BLEND tap
  splits off pre-JFET, i.e. before the oversampled region — an uncompensated crossfade against the
  OD path (which picks up the oversampler's FIR latency) comb-filters at every BLEND position; (b)
  independent of delay, the OD path reaching BLEND already carries one confirmed inversion (the
  clipper, ≈−48.5) plus an UNCONFIRMED one (the J201 stage's sign — needs its own DC-step test),
  so a per-stage-only test regime can miss an aggregate sign error at the BLEND node itself. Both
  fixes + null-test signatures (comb notches that shift with OS factor = delay bug; broadband/
  wrong-setting nulls that don't shift = polarity bug) now in `dsp.md` ("Dry/wet phase alignment
  across the oversampled region"), cross-referenced from `architecture.md` (Bypass), `circuit.md`
  (BLEND note), and `docs/build-plan.md` (Phase 4/6 + risk #8). Build the delay line AND run the
  end-to-end DC-step test in Phase 6; don't ship Phase 4's BLEND stage without both.
