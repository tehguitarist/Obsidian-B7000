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

- **Current baseline: `analysis/reports/s120_newton.json`** (162 captures). Quote every OD number
  against this report. `s118_clampfix.json` is the diff-against control (identical membership).
  ⛔ The absolute-ledger gates (K/M/O/P/Q) must be read against `s118_clampfix.json` or later — GATE O
  deliberately refuses any earlier report by name (session 119).
- **ctest 17/17** as of session 120 — the first clean suite since session 44 (the bracketed-Newton
  `rtsafe` solve fixed the standing `OSValidationTest` failure; see SHIPPED CONSTANTS).
- **Release gate: 6 rows over SHIP.** Run the script for the live numbers — do not transcribe them:
  ```bash
  /opt/homebrew/bin/python3.11 analysis/release_gate.py analysis/reports/s120_newton.json
  ```
  The six, as of s120: OD 100 Hz–8 kHz p90, OD 25–100 Hz median/p90, OD 8–16.3 kHz p90, OD p99,
  THD level (full-send). See §"THE RELEASE GATE" below for the bar definitions and fallback.
- Session 118's D1/D2 clamp-window fix and session 120's `rtsafe` solve are both **KEPT** (user
  decisions, taken at the top of session 120).
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
| The six user-flagged peak/notch centre-frequency mismatches (bass notch/peak, mid peak, treble peak/notch, clean HF rolloff) | **CLOSED — none is a corner error** | 122 | Two are the OD/clean mix (= A3, not a filter); three are not a fixed feature on at least one side (ND's own peaks move with drive, a fixed network cannot); the 320 Hz null's centre is **right to 0.7%** — GAP #2 is a depth/width defect only, its centre was never wrong. | `analysis/feature_locus_gate.py` (GATE W) |
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
drive-independent defect vs an ND-artefact-dominated tail) rather than loosening either bar. Trigger
is "everything else closed", not "this row is annoying" — re-run GATE I and reproduce its numbers
before acting. ⛔ **Do not aim model work at 8–16.3 kHz otherwise** — ~38% of the OD headline sits
there and it is ND's own aliasing artefact (GATE I, `analysis/hf_artefact_gate.py`, passing since
session 114), not our Sallen-Keys; p99 is 10.28 dB even with all four HF bands dropped, so the
remaining OD error is genuinely broadband.

### Open work, in order

Current ordering per session 122's own `▶ NEXT` (which supersedes every earlier list — see
`docs/session-log.md` for the superseded orderings and why each item moved):

1. **ADAA the CD4049 VTC** — Phase 10 B's head item, re-scoped session 121 to the 2×/4× realtime
   alias floor (−30…−32 dB at amp 0.35–0.70; the 8× render floor is already −61 dB post-`rtsafe`
   and is not what a realtime user hears). The J201 already has closed-form ADAA (`PedalChain.h`);
   this is 1st-order ADAA on `railClip`/the CD4049 VTC transfer per `dsp.md`'s ADAA section.
2. **THD level term** — one of 6 rows over SHIP (3.523 vs ≤3.0, full-send). Model **over**-distorts
   (signed mean positive) — do not reason about candidates as "add more distortion".
3. **Perf: the `pow()` path, not the solver.** Shipped `clipK = 2.4653` misses `sig()`/`sigDeriv()`'s
   `k == 2.0` fast path — two `pow()` calls per Newton F-evaluation dominate the clipper's
   356 ns/sample. A cheap `pow` approximation or an anchor back at k=2 is the lever.
4. **Re-point the other consumers of the corrupted MASTER anchor** — `clean_headroom_bound.py`,
   `clean_headroom_probe.py`, `clean_thd_check.py`, `captures.py`'s Tier-1 matrix list all still name
   `master-1700_gain-n12_base-clean.wav` (the capture GATE T proved 4.447 dB low). None currently
   carries a quoted number that matters (checked session 119), but any future use needs the
   correction from `master_anchor_gate.py`'s `detent_corrections()`.
5. **VTC-amplitude-vs-physical-rail inconsistency** — the model's VTC amplitude is fitted 5.4×
   below the physical rail (everything around it — TL07x rails, D1/D2 references, R19 — is
   physical). That is why the corrected D1/D2 window still fires on 0.05–0.25% of samples. A
   K/`clipSat` re-fit against a physical ceiling is the real repair (same job as item 4).
6. ⛔ **Do NOT open a centre-frequency item** (CLOSED session 122 — see CLOSED/REFUTED table).
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

⚠ **A3 (item on this list since session 89) is compressed here but its exclusions must travel
together — this sentence is load-bearing, do not lose it:** *no single element closes A3 (s50), no
post-clipper linear element of ANY order does (s52), no GRUNT-side cap does (s38), its level is not
a fittable constant (s108), and its shape MIGRATES with stimulus so no fixed linear network can
produce it (s108 synthesis).* A3's SIZE and GATE O's attribution stand (see CLOSED/REFUTED table);
what is retired is only the idea of fitting a static correction to it. Full derivation:
`docs/session-log.md` SESSION 105–108 blocks.

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
- ⭐⭐ **THE HF REGION (8–16.3 kHz) IS ND'S OWN ARTEFACT, AND THIS IS NOW QUOTABLE FROM A PASSING
  GATE, NOT A NARRATIVE.** `analysis/hf_artefact_gate.py` (GATE I, rebuilt session 114) passes on
  every report from s91 to s113 (and beyond): at the hottest stimulus every one of the 15 pedal
  conditions **gains** with frequency across the octave and every one of the model's **rolls off** —
  complete separation, gap +17.44 dB/oct, with a monotone dose-response (a drive-generated artefact
  must grow with stimulus; a fixed filter difference cannot). ⛔ **STOP AIMING MODEL WORK AT
  8–16.3 kHz** — ~38% of the OD headline sits there and is not ours to fix (see THE RELEASE GATE's
  fallback note above for the one condition under which this changes).

### Uncommitted work

⚠ **As of session 122, sessions 115–122 are uncommitted.** Run `git status --porcelain` for the
live, authoritative list — do not transcribe it here (`rebuild-targets-dont-transcribe`; the old
per-session "Uncommitted at session N" blocks were exactly this mistake, repeated 28 times, and are
now archived verbatim in `docs/session-log.md`). Sessions 89–114 **are committed** (`df81360`).

Regenerable/gitignored, not part of any commit decision: `analysis/reports/*.json`,
`analysis/fit_logs/*.log`, `build/**`.

▶ **Flag to the user, do not act unilaterally:** several sessions of work including multiple
shipped-constant changes (`kOutputMakeup`, the MASTER PWL taper, the D1/D2 clamp window, the
`rtsafe` solver) are uncommitted. Committing them would make this section — and the SHIPPED
CONSTANTS table above — trivially maintainable going forward. That is the user's call.

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
