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
> ⛔⛔ **SESSIONS 150-151 ARE AN UNCOMMITTED, USER-DIRECTED, NON-SCHEMATIC FIX — READ
> `docs/session-log.md` SESSION 151 BEFORE TOUCHING `src/dsp/OdToneRestore.h` OR `PedalChain.h`.**
> User-authorised explicitly, overriding the usual schematic-fidelity preference, and scoped to this
> one tone complex: a drive- AND GRUNT-keyed restore of the OD-path 320 Hz null's DEPTH and Q (the
> ~800 Hz bridged-T notch is already close — **do not touch it**).
> ✅ s151 re-fitted it: null depth now within **±0.83 dB at all three GRUNT positions across the drive
> ladder**, from a starting point of 10-25 dB short at GRUNT flat/boost. s150's stall had two causes
> and it had named only the smaller one — see the CLOSED/REFUTED rows.
> ⚠ **Its five open items are listed at the END of `docs/session-log.md` SESSION 151** — the head one
> is the Cut row's Q (1.35-1.51 too broad at low/mid drive, structural: needs a shoulder-shaping
> section, not another gain iteration). `kPeakGainDb` is still all zeros by design.
> ⛔ **Fit BLEED-FREE (LEVEL = BLEND = max) and never at LEVEL noon** — that set is ~44 % clean and
> silently prices in one mix ratio; it is what made s150's table 3-5x too small. Instrument:
> `analysis/od_tone_restore_fit.py`.
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

- ⚠⚠ **`analysis/reports/s151_odtone.json` (s151) EXISTS AND IS NOT THE BASELINE — it is the
  `OdToneRestore` state, which is UNCOMMITTED.** 162 captures, membership identical to s146, 636
  shared (file, sweep) cells. **Release gate: 6 rows over SHIP on BOTH, so the stage changes no gate
  verdict.** ✅ CLEAN bit-identical (0.451 → 0.451) — a free known answer that the stage is OD-only.
  OD band-RMS 1.947 → **1.987**, and it is attributable: **GRUNT cut +0.010 over 364 of 448 cells
  (neutral), flat +0.194, boost +0.148**, every worst cell at `sweep_clean`/`sweep_drv_-18` — i.e.
  the whole cost is the quiet stimulus levels the knob-keyed compromise deliberately excluded.
  Derivation and the unresolved-target caveat: `docs/session-log.md` SESSION 151 §6b/§7.
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
- ⚠ **SESSIONS 152, 153, 154 AND 155 LIKEWISE CHANGED NO BASELINE AND NO CONSTANT** — GATES **AP**,
  **AQ** and **AR** on the `OdToneRestore` stage, each with its own mutation runner (9/9, 10/10,
  **11/11**), each adding only **additive** keys to `od_tone_restore_fit.notch_geometry` with the
  neighbouring gates' stored reports verified unchanged; then **GATE AS** (s155,
  `analysis/ladder_zin_tilt_gate.py` + `_mutate_gate_as.py`, **12/12 arms**, five computed-verdict),
  which is **read-only** — it touches no `src/` file, writes only its own new report
  `s155_ladder_zin_tilt.json`, and did **not** rebuild, so the render-cache bill is not re-armed a
  fourth time. **ctest 19/19** (68.8 s at -j 12). Their results are CLOSED/REFUTED rows below; the
  narrative is `docs/session-log.md` SESSION 152–155.
- ✅ **SESSION 158 IS READ-ONLY AND IS THE CLEANEST KIND: NO `src/` FILE, NO BUILD, NO RENDER** —
  `analysis/prominence_audit_gate.py` (GATE AV) + `_mutate_gate_av.py` (**14/14 arms**, six
  computed-verdict) + one new report, `s158_prominence_audit.json`. It runs on **captures and
  closed-form synthetics only**, so it does not re-arm the render-cache bill (still owed once from
  s156) and its numbers are **binary-independent** — they do not expire when a constant ships.
  **ctest 19/19** (68.6 s at -j 12). Three CLOSED/REFUTED rows carry it; narrative in
  `docs/session-log.md` SESSION 158. ✅ **Its one outstanding item — the MODEL side — is DONE at
  s159** (row below).
- ✅ **SESSION 159 CHANGED NO `src/` FILE, NO CONSTANT AND NO BASELINE, AND DID NOT BUILD** —
  `analysis/model_prominence_gate.py` (GATE AW) + `_mutate_gate_aw.py` (**14/14 arms**, five
  computed-verdict) + one new report, `s159_model_prominence.json`. **ctest 19/19** (68.1 s at
  -j 12). Four CLOSED/REFUTED rows carry it; narrative in `docs/session-log.md` SESSION 159.
  ⚠ It **did render** — 24 conditions into the PRIVATE `build/s159_model_prom/`, per s158's own
  instruction — but that is **not** a cache event: no binary was relinked, so the matrix
  render-cache bill is unchanged and the ~25 min still stands owed once from s156.
  ⛔⛔ **GATE W's own cache `build/s122_feature_locus/` is READ-ONLY to this gate and that is
  enforced, not intended**: it is fingerprinted `(size, mtime_ns)` before and after every run and
  the gate REFUSES on any change, because `W.render` re-renders anything whose binary stamp is
  stale — so one run pointed at that directory would destroy the artefacts GATE W published from
  and AW1b could never detect it again. **Do not point any tool's `ren_dir` at it.**
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
- ✅ **SESSION 160 IS A USER-DIRECTED REVIEW AND RE-PRIORITISATION, NOT A NEW MEASUREMENT SESSION —
  read this before the Open Work list below, it changes what several items now mean.** The user
  reviewed all open work across 150+ sessions and made four scoping decisions, recorded at each
  item rather than only here: **item 5 CLOSED** (branch (a) accepted — the clipper's low ceiling is
  a standing fact, not a lever; no further work); **item 6's physical-carrier search CLOSED**
  (exhaustive per GATE AM/AS — nothing left to screen), **converted to a capped [ENG] artificial
  correction** on the one sized sub-target (the treble-peak slope), same architecture as
  `OdToneRestore`, **hard-capped at 3 sessions**; **item 9 redirected from a topology-discriminating
  investigation to a direct artificial correction** of the measured LEVEL-sensitivity gap, with the
  explicit caveat that it cannot move any release-gate row (the matrix's per-row gain match is
  structurally blind to this class of error — same reason item 5 is closed rather than fixed);
  **item 10's Cut-row Q given a 2-iteration stop condition** rather than open-ended fitting.
  ✅ **B (hygiene) DONE THIS SESSION** — the three unchecked consumers of the corrupted MASTER anchor
  capture are re-pointed/annotated (item 4); two further stale constants found in passing
  (`clean_headroom_probe.py`'s `kInputRef` literal was the session-17 value, 3.75× the current
  0.90; GATE T's `SHIPPED_MAKEUP`/`SHIPPED_TAPER_EXP` were pre-s115/pre-s146 relics still labelled
  "shipped"). Zero `src/` change, so **no rebuild and no re-render owed.** Verified: GATE T's stored
  report is numerically identical (8/8 values, only two key names moved), `detent_corrections()`
  unchanged, all matrix filenames still parse. Full narrative: `docs/session-log.md` SESSION 160.

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
| `OdToneRestore` stage | *(new)* → one RBJ peaking biquad at 323 Hz, gain+Q on a GRUNT×DRIVE table | 150/151 | ⚠ **[ENG], NON-SCHEMATIC, user-authorised and scoped to this one tone complex** — restores the 320 Hz null's DEPTH and Q, which the model loses with drive at GRUNT cut and loses almost entirely at flat/boost. Depth now within ±0.83 dB at all 3 GRUNT positions across the ladder — ⚠⚠ **SUPERSEDED s156, row below** | `OdToneRestore.h`, `PedalChain.h` |
| `OdToneRestore` stage | bleed-free-fitted table → **MIX-KEYED**: `cut = kNotchGainDb[g][d] + kNotchMixK[g][d]*S(cleanFrac)` | 156 | ⚠⚠ **kNotchGainDb CHANGED MEANING** — it is now the cut at `kMixCfRef` (LEVEL noon/BLEND max), not the bleed-free cut. The stage sits upstream of LEVEL/BLEND and cannot see the mix directly, so `LevelBlend::cleanFraction()` (new, superposition on the shipped `process()`) is read into it every `applyParams()`/`applyFitParams()` via `PedalChain::syncOdToneMix()`. One scalar is provably sufficient — captures reaching the same clean fraction by different LEVEL/BLEND routes agree to 0.05 dB (GATE AT's AT2). Listening-condition depth error down from ~+8 dB to +1.0…+1.5 dB; DRIVE-0 sign corrected (was boosting where a cut was needed). ⚠ A measured DEPTH CEILING (~1.5–2 dB composite at the listening mix, a 40 dB probe gives 0.47 dB — shallower than the shipped 12.34 dB cut's 1.60) means the residual is not closable from this stage; the lever is A3 | `OdToneRestore.h`, `LevelBlend.h`, `PedalChain.h`; `analysis/od_notch_mix_law.py` (GATE AT) |

#### CLOSED / REFUTED — do not re-open without reading the pointer

One row per claim a future session might otherwise re-measure or re-open. This is the load-bearing
table in this file.

| claim | status | session | reason | pointer |
|---|---|---|---|---|
| "clamp the mix-shape `S(cleanFrac)` flat below its peak, so the raw fall toward the bleed-free corner (which is the most censored reading in the set) doesn't ship" — three independent reasons argued for it (user's stated preference, censoring, hardware authority) | ⛔⛔ **BUILT AND REVERSED, s156 — the raw non-monotone shape is PHYSICALLY EXPECTED, not an artefact** | 156 | Measured against the acceptance table, the clamp made the composite null **9.6–11.6 dB too deep** at LEVEL/BLEND max while every other mix landed within 1–3 dB. Re-examined: the required cut peaks at INTERMEDIATE mix because that's where the model's own null is diluted hardest while the pedal's target is still deep; at cleanFrac→0 the model's own null is already close, at →1 both wash out together. A middle peak follows from that with nothing to correct. | `analysis/od_notch_mix_law.py::S_CLAMP_CF` block |
| "the model's composite 320 Hz null can be made as deep as the pedal's by cutting harder in the OD path" | ⛔⛔ **REFUTED — THERE IS A DEPTH CEILING, s156** | 156 | A deliberate 40 dB OD-path cut at the listening condition (LEVEL noon, GRUNT cut, DRIVE 0.5) produced a **0.47 dB** composite null — SHALLOWER than the shipped 12.34 dB cut's **1.60 dB** — because at that depth the RBJ section is narrower than the 1/48-oct analysis (and the ear) resolves, so extra depth is averaged away. Confirmed independently: +1.20 dB on the whole Cut row moved the listening-condition depth 0.03 dB while costing 1.11 dB bleed-free. ⇒ the ~1.0–1.5 dB residual at the listening mix is not reachable from this stage; the lever is A3 (the model's OD path is ~4.4 dB quiet), not this notch's gain. | `OdToneRestore.h::setCleanFraction()`'s block |
| "the ~800 Hz bridged-T region is shallow the same way the 320 Hz null is, and needs a matching notch" (user's initial report this session) | ⛔ **NOT A NOTCH DEFECT, s156** | 156 | A biquad fitted there (jointly with the 320 Hz term, so it can't leak) buys a median **0.058 dB** of fit — at the grid's own scatter — against the 320 Hz term's **1.56 dB** (27x). What's there is a broad ~1.5-octave bowl (A3 seen as a shape), and its **sign flips with GRUNT** (+1.26 dB at cut, −1.8…−3.5 at flat/boost) — a fixed correction would be wrong at 2 of 3 switch positions. | `analysis/od_notch_mix_law.py` docstring §(2) |
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
| session 150's own suspicion that `OdToneRestore` might carry a **structural** bug (bad biquad coefficients, or the wrong sample rate reaching `prepare()`) rather than a tuning miss | ⛔ **REFUTED, s151 — the filter was always correct** | 151 | Standalone probe (no JUCE, no WDF): impulse → DFT through the shipped C++ stage's own `prepare()`/`setDrive()` path, against an **independent** RBJ implementation written from the Audio EQ Cookbook. Worst disagreement over 200–1000 Hz: **4.0e−6 dB**. ⇒ the coefficients, the direct-form I recursion and the oversampled rate are all right and the entire shortfall was the TARGET. ⚠ Free by-product, and it mattered: the binary on disk was **older than `OdToneRestore.h`**, so s150's final "revert the 10 dB debug probe" edit had never been compiled and anything read off that binary was reading the probe. **Check mtimes before trusting a rendered artefact.** | `scratchpad/odprobe.cpp`; `docs/session-log.md` SESSION 151 §1 |
| GATE W `locate()`'s PROMINENCE as the objective to tune this stage against (session 150 used it for every iteration) | ⛔⛔ **REFUTED — IT IS A DETECTOR, NOT AN OBJECTIVE, AND WIDENING ITS WINDOW DOES NOT RESCUE IT** | 151 | `mid_notch`'s window is a fixed **[285, 358] Hz** band and its prominence is `min(rise-to-left-edge, rise-to-right-edge)`; where the model's curve declines across the whole window the argmin sits ON the right edge, the right-hand walk is empty, and the statistic reads **~0 for ANY notch depth** — `measurement-discipline.md`'s s126 entry exactly. Chasing it drove s150's Q to **32** (a ~10 Hz needle) and its centre to **310 Hz**, against a pedal whose centre is **322.8 Hz** and whose Q is 5–12. ⛔ **And the obvious repair fails too:** at DRIVE max the model's curve falls monotonically from ~370 Hz into the bridged-T notch, so a window wide enough to hold the null's right shoulder puts the GLOBAL minimum at **~550 Hz** and the reader silently tracks a different feature (measured: f0 550.8, depth 0.000, edge=1). ⇒ **decouple the two searches** — a CORE window bounding where the null sits, a SHOULDER window bounding where its flanks recover, and a REFUSAL when the minimum rests on a CORE bound. | `analysis/od_tone_restore_fit.py::notch_geometry` |
| the `drive-*_base-od.wav` / `ref-od.wav` DRIVE ladder as the fit set for an **OD-path** correction | ⛔⛔ **REFUTED — IT IS ~44 % CLEAN, AND THIS IS THE LARGER HALF OF WHY s150 STALLED** | 151 | That ladder sits at **LEVEL = 0.5**. GATE K2: bleed vanishes only where BOTH LEVEL and BLEND are max; s113 measured LEVEL-noon/BLEND-max output at **~44 % clean signal**. A stage in the OD path therefore has ~half of what it does diluted away before the analysis reads it — measured, the deficits come out **3–5× too small** (s150's DRIVE-max entry was 3.05 dB against a true 16.3), *and* a fit there silently prices in one LEVEL setting. ⇒ **fit bleed-free (`drive-0700_level-1700` / `level-1700` / `drive-1700_level-1700`), then CHECK across LEVEL and BLEND.** ⭐ The check is what proves it: after fitting bleed-free the OD path is right to ±0.3 dB while LEVEL noon is still 1.1–1.75 dB short — and propagating GATE O's independently measured **4.38 dB** A3 deficit through the LEVEL-noon clean fraction predicts **1.61 dB** against **1.75** measured. ⚠ Sufficiency, not identification (the coherent-sum model gets the difference to 0.14 dB but not the absolute depths, which need phase). | `analysis/od_tone_restore_fit.py` `--set bleedfree\|listen\|blend` |
| "just exaggerate whatever already creates the 320 Hz null, tracking the same elements" (the user's own question, s151 — and the right one to ask) | ⛔ **REFUTED WITH NO RENDER — THE CORRECTION CHANGES SIGN** | 151 | Measured bleed-free with the stage subtracted out, the model's null is **5.74 dB TOO DEEP at DRIVE 0** and **17.10 dB TOO SHALLOW at DRIVE max** (pedal 8.59 → 19.08 dB, rising monotonically; model 14.32 → 1.97, washing out). The null is a cancellation in the **linear** pre-clipper treble/ATTACK ladder (GATE R's R2: it moves 329.7 → 164.2 Hz with the ladder caps and ignores the bridged-T), so any static element change adds the SAME amount at every rung and **cannot be −5.7 at one end and +17.1 at the other**. Making such an element drive-dependent IS open item 6, where every named carrier is refuted. ⭐ And GATE Y (s126) independently priced the collateral: the ladder constants that DO move this region **dissolve the 320 Hz null and the mid peak outright** (prominence 7.27 → 0.00). ⚠ The pedal also SHARPENS as it deepens (Q 5.21 → 8.65 → 11.54), which the user identified by ear before it was measured. | `docs/session-log.md` SESSION 151 §4 |
| ⭐⭐ which axis this defect actually lives on — every prior look, including all of session 150, read it at **GRUNT = cut** | ⭐⭐⭐ **GRUNT IS THE LARGEST AXIS, NOT A REFINEMENT — AND THE ONE-ROW STAGE WAS A REGRESSION AT TWO OF THREE POSITIONS** | 151 | **Every capture without a `grunt-` token is GRUNT = CUT** (`captures.py` defaults `gruntIdx=_GRUNT_IDX["cut"]`), so the whole search sat at one switch position. Measured bleed-free with the stage subtracted, correction needed (mean over the realistic sweeps): **Cut −5.74 / +2.12 / +17.10** against **Flat +13.99 / +16.56 / +21.88** and **Boost +11.79 / +12.58 / +9.65** — i.e. at Cut the model's null is roughly the right size and at Flat/Boost it is **10–25 dB short**, with **no null at all** in several DRIVE-max cells. ⛔⛔ Worse, the Cut-fitted DRIVE-0 entry is a 6.4 dB **BOOST**, applied unchanged where the null was already 15–19 dB too shallow: it made those positions **4.5 dB WORSE than leaving the stage out**. Found only by subtracting the stage's own response analytically — "the model never had a null here" and "our correction filled it in" are identical in the rendered curve. ✅ Fixed by GRUNT-rowing the tables (`[3][5]`) keyed on the PHYSICAL position via `gruntEnum()` (APVTS order is {Boost, Cut, Flat}, NOT the enum's — raw `p.gruntIdx` would silently permute the rows), then iterating twice: depth now within **±0.83 dB everywhere**. ⭐ `reference-sources.md` §1 makes **HARDWARE** the authority for this null's depth and §3 records it deeper than ND by **+1.6 dB at cut rising to ~26 dB at boost** ⇒ the ND-matched answer is a **lower bound**. ⛔ §3 is a PNG read — sign and rough size only, never a fit target. | `analysis/od_tone_restore_fit.py --stage-off --set grunt_flat\|grunt_boost` |
| s151 §6b's direction — *"the pedal depths are LOWER BOUNDS ⇒ the shipped corrections are UNDER-estimates, i.e. **conservative**"* (s151's own head open item, ranked above every tuning item) | ⛔⛔ **THE CENSORING IS REAL AND THE CONCLUSION IS NOT SAFE — ON THE CENSOR-ROBUST METRIC 7 OF 9 ENTRIES WANT *LESS* GAIN, s152** | 152 | Built the estimator s151 named as the remedy (GATE R's own 1/6-oct POWER-INTEGRATED depth, s110 R4 — `band_db` **imported**, not re-derived) and converted BOTH readings into the shipped table's own unit, a biquad centre gain, by solving per cell for the gain at which the composite's depth equals the pedal's. ⚠⚠ **That conversion is the whole design**: a point depth and a 1/6-oct area depth are **different quantities, not two measurements of one** (a deep narrow null has a small area deficit whatever the residue does), so comparing the two depths directly is `difference-statistics-hide-common-mode` in two different units. ✅ **The censoring is confirmed: 16 of 26** bleed-free pedal readings bottom at/below the residue, `corr(margin, point−area gap) = −0.668`, and the area depth is **4.1× less sensitive** to censoring (point slope **−1.000 dB per dB**, area **−0.242**; **−0.001** at the worst-censored cell). ⛔ But re-solved, **8 of 9 entries move by more than the fit's own ±0.83 dB residual and 7 move DOWN, to −4.92 dB**. ⇒ within the point metric §6b's logic still holds; what fails is the conclusion, because the point metric is exactly the one whose unreliability motivated the item. ⭐ Certified by a known answer that already existed: the **POINT** solve reproduces the shipped table to **0.57 dB rms** (that table came from a different rebuild-and-re-measure loop). ⚠⚠ **NOTHING SHIPPED — the trade is a WASH** (pooled mean \|err\|: shipped 4.03 point / 2.06 area, area-solved 4.54 / 1.54), i.e. entries move up to 4.92 dB while achieved error moves 0.5 dB ⇒ **the table entry is weakly identified**, s151 §6's stimulus-level limit priced in the constant's own units. **USER DECISION**, and note §1/§3 make HARDWARE the authority and record it DEEPER than ND, so the smaller table moves *away* from hardware. | `analysis/null_depth_censor_gate.py` (GATE AP) AP1–AP5 |
| "…and therefore the metric disagreement IS the censoring" (the attribution a reader reaches for) | ⛔ **NOT SUPPORTED — IT IS A *SHAPE* MISMATCH, AND THE CONTROL WAS FREE** | 152 | Tested rather than assumed: `corr(mean floor margin, area−point gap) = **+0.196**` — nothing, and the wrong sign for a censoring story; `corr(pedal/composite Q ratio, gap) = −0.314`. ⭐⭐ The decisive control is AP1c's own synthetic round trip: with the pedal's null shaped **exactly** like the shipped biquad, the two metrics recover the same injected gain to **2e-4 dB**. ⇒ **the censoring is what makes the POINT reading untrustworthy; the shape mismatch between the pedal's null and the shipped (f0, Q) is what makes the two columns differ** — two separate facts the item conflated. ⭐ This is **open item 1 (the Cut row's Q, 1.35–1.51 too broad) on a second instrument**, and it is now the head technical item on this stage. | `analysis/null_depth_censor_gate.py` AP6/AP1c |
| s151's header note *"Boost's DRIVE-max entry is a mean over **TWO** valid cells, not three"* | ⚠ **IT IS ONE — AND *FLAT*'s DRIVE-max is also one, and is flagged nowhere** | 152 | Counted against the shipped build with the stage subtracted, on the difference method's own membership (BOTH sides readable): Flat × DRIVE max reads model **NO NULL** at `sweep_drv_-18` AND `-12`; Boost × DRIVE max reads model NO NULL at −18 and **both** sides NO NULL at −12. ⇒ **1/3 each.** ⭐ AP3's analytic solve does better and this is the reusable part: it needs only the **PEDAL** side, because it *creates* the composite's null with the candidate gain — so it recovers those cells (Flat n=3, Boost n=2). **A model-side refusal is not missing data about the target; it is the model having no feature**, which a solve handles and a depth-difference cannot. ⚠ The header amendment is a `src/` edit and was deliberately NOT made — the render cache already owes ~25 min; batch it (`build.md`). | `analysis/null_depth_censor_gate.py` AP4 |
| GATE AP's *"match the notch by its BOTTOM or by its AREA?"* — the USER DECISION carried from s152 | ✅ **TAKEN, s153 — THE TABLE STAYS AS SHIPPED; the area-solved alternative is DECLINED** | 153 | Put to the user with the trade priced. Three grounds: **(1)** the trade is a **wash** — pooled mean \|error\| **4.03 point / 2.06 area** for the shipped table against **4.54 / 1.54** for the area-solved one, i.e. entries move up to **4.92 dB** while achieved error moves ~**0.5 dB** ⇒ the constant is **weakly identified** (s151 §6's stimulus-level limit, in the constant's own units); **(2)** `reference-sources.md` §1/§3 make **HARDWARE** the authority for this null's depth and record it **DEEPER than ND**, so the smaller area-solved table moves **away** from the governing reference; **(3)** which metric the **ear** follows is established by nothing measured. ⚠ **NOT refuted by this:** the censoring is real (**16 of 26** readings) and the area estimator is **4.1x** less sensitive to it — the decision is about which target to fit, not about whether the censoring exists. ⛔ Recorded at `kNotchGainDb` itself, not only in the log (`a-refutation-has-to-land-where-the-thing-is-CHOSEN`). ⛔ Do not re-open it as *"the shape was wrong"* — GATE AQ tested that, and ⚠ **s154 CORRECTS THE SIZE: matching Q closes 69 % of the gap paired, not 20 %** (the −20 % is an unpaired statistic — see AR3's row). ⭐⭐ **The DECISION is untouched by that correction and here is why, because the distinction is the whole point:** the shipped table has ONE entry per (GRUNT, DRIVE), so a mean over sweeps is exactly what *would* be shipped ⇒ AQ4's pooled gap is the **right statistic for the SHIPPING question this decision turned on**. What moved is the MECHANISM inference, not the number. And the paired residual (**2.13 dB**) still exceeds the ±0.83 dB bar. | `OdToneRestore.h` `kNotchGainDb` block; `docs/session-log.md` SESSION 153 §9 / SESSION 154 §3 |
| `notch_geometry`'s `q` — the instrument EVERY Q number on this stage was measured with, including the shipped `kNotchQ` table | ⛔⛔ **QUANTISED TO THE SIZE OF THE DEFECT IT WAS MEASURING, s153 — 8 distinct values over 16 true Qs, worst error −42 %** | 153 | It snaps BOTH half-depth crossings to whole 1/48-oct grid cells, so the width is an integer number of cells and `q` can only return **`1/(2^(m/48) − 2^(−n/48))` for integer (m, n)** — asserted in closed form, and every reading came back an exact symmetric pair. Above Q≈8 the attainable values are **{8.65, 11.54, 17.31}** and nothing between: true Q of **8, 10 and 11 ALL read 8.651**, and 18/20/24/30 all read 17.310. ⇒ ⛔ `OdToneRestore.h`'s *"the Cut row stalls at 1.35–1.51 too broad"* is **ONE TO TWO STEPS of the reader**, and its *"EXACTLY on the pedal's 11.54 at DRIVE max"* is a **quantisation coincidence**. ✅ Fixed additively: **`q_interp`** interpolates each crossing in log-f, is strictly monotone with no plateaus, and recovers an injected Q to **±0.003 %**; `q` is UNTOUCHED and **GATE AP's stored report is byte-identical** after the change. ⚠ Neither reader is unbiased at low Q (the SHOULDER window truncates a broad notch — same effect AP1c documents on the depth); the bias **cancels** in every pedal-vs-composite comparison, which is why the gate tests monotonicity and round-trip recovery, never absolute accuracy. ⭐⭐ This is `a-statistic-can-be-a-fine-DETECTOR-and-a-catastrophic-OBJECTIVE` (s151) **a second time on this same stage** — s151 caught it on the depth axis and the Q axis had the same disease. | `analysis/notch_shape_gate.py` (GATE AQ) AQ1c |
| `OdToneRestore.h`'s *"that Cut residual is STRUCTURAL … a single peaking section cannot narrow it … do not spend more gain iterations on it"* — asserted on the evidence of an iteration that stalled | ⭐⭐ **SURVIVES, AND IS NOW A MEASURED LIMIT RATHER THAN A STALL — BUT IT IS SCOPED TO *CUT*, s153** | 153 | A stall is not a bound (`a-backlog-item's-proposed-REPAIR-is-a-claim`, s142). Re-posed as a **containment** question with no threshold in it: sweep the section's Q to 120 with the DEPTH re-solved at every rung (so a high-Q section cannot "narrow" the composite by simply doing less) and ask whether the pedal's Q is inside the attained set. **Reachable in 21 of 26 cells, and all 5 failures are in the CUT row** — Cut × DRIVE 0.50 fails at **all three** sweeps (pedal Q 13.91 against an attainable 3.50–9.46), so that entry has **no shape-matched solution at any Q**. ⇒ the second, shoulder-shaping section is owed **at CUT ONLY**; ⛔ **Flat and Boost reach at every cell — do not generalise the structural claim to them.** | `analysis/notch_shape_gate.py` (GATE AQ) AQ2 |
| GATE AP's AP6 — *"the censoring is what makes the POINT reading untrustworthy; the SHAPE mismatch between the pedal's null and the shipped (f0, Q) is what makes the two columns differ"*, and s152's hope that fixing the shape would dissolve the user decision | ⛔⛔ **REFUTED AS *THE* EXPLANATION, s153 — matching Q removes only 20 % of the gap** | 153 | AP6 reached its attribution by ELIMINATION plus a synthetic control, with both of its correlations weak (**+0.196** with the floor margin, **−0.314** with the Q ratio). Tested directly on real data by freeing Q so the composite's shape matches the pedal's: the mean \|area − point\| solved gain goes **2.69 → 2.16 dB (−20 %)** against a bar of **±0.83 dB** (the fit's own residual, imported) ⇒ **SURVIVED**. AP1c/AQ1d are untouched (with the shape matched *exactly* the two metrics agree to **2e-4 dB**). ⚠⚠ ⇒ **GATE AP's USER DECISION IS NOT DISSOLVED** — still a real open choice. ⛔⛔ **BUT THE −20 % IS UNPAIRED AND THE INFERENCE FROM IT IS REFUTED, s154 — see AR3's own row.** Paired, the SAME numbers read **6.83 → 2.13 dB (−69 %)**, so the shape mismatch is the LARGER part of the disagreement rather than a fifth of it ⇒ **AP6's attribution is largely REHABILITATED**, not refuted. ⛔ And this row's closing advice — *"anyone re-opening this should free the **centre**, not the Q"* — **is REFUTED**: AR5a measures the two centres agreeing to within the reader's own resolution in **21 of 26** cells. | `analysis/notch_shape_gate.py` (GATE AQ) AQ4; `analysis/notch_residual_gate.py` (GATE AR) AR3/AR5a |
| "the pedal's null Q at a given (GRUNT, DRIVE) entry" — the premise behind quoting the Q defect as one figure per entry, and behind `kNotchQ` being a DRIVE-keyed table at all | ⛔⛔ **IT IS NOT ONE NUMBER — it spans 1.29x–2.93x across stimulus at FIXED (GRUNT, DRIVE), s153** | 153 | Every rung printed rather than summarised (`an-endpoint-pair-is-not-a-ladder`, s129): the pedal's own Q runs e.g. **19.60 / 15.64 / 7.70 at Flat × DRIVE 0** and **18.83 / 24.13 / 8.24 at Boost × DRIVE 0**, non-monotone in 3 of 9 cells. ⇒ the spread is **as large as the defect being chased and larger in 8 of 9 cells**, so a DRIVE-keyed Q entry is fitting a mean over a quantity that moves further than the thing it is correcting. ⭐ This is **s151 §6's architectural limit** (a knob-keyed stage cannot track a stimulus-dependent feature) **measured for the first time on the Q axis**, and it bounds what any (gain, Q) table here can achieve. ⚠ Read as an argument for leaving `kNotchQ` ALONE, not for refining it. | `analysis/notch_shape_gate.py` (GATE AQ) AQ2b |
| "the pedal's null MIGRATES to ~242 Hz at GRUNT boost × DRIVE max, so the centre must track (grunt, drive)" — written up mid-session as a finding | ⛔ **REFUTED BY MY OWN NEXT READ — IT WAS ONE CELL OF FOUR** | 151 | Across the four stimulus levels that cell reads **322.8 / 327.5 / 238.3 / 322.8 Hz**; only `sweep_drv_-12` gives 238.3. **322.8 Hz serves every GRUNT position** and the centre needs no tracking at all, which is what made the GRUNT fix tractable rather than a re-architecture. ⇒ `an-endpoint-pair-is-not-a-ladder` on the SWEEP axis: read every rung before calling anything a migration — a single-cell reading is exactly what a wide search window returns when the feature it wants is absent. | `docs/session-log.md` SESSION 151 §5 |
| GATE AQ4's headline statistic — *"the mean \|area − point\| solved gain goes 2.69 → 2.16 dB (−20 %)"* — read as a measurement of what SHAPE-MATCHING buys | ⛔⛔ **IT IS A DIFFERENCE OF MEANS OVER AN AXIS ON WHICH THE QUANTITY CHANGES SIGN, s154. PAIRED, THE SAME NUMBERS READ 6.83 → 2.13 dB (−69 %)** | 154 | AQ3/AP3 average each metric's solved gain over the three stimulus sweeps SEPARATELY and only then difference the two columns. Per sweep the **1-D (shipped-Q) gap changes sign** — **−6.85 / −6.56 / +5.94** dB, 7/7 and 6/7 and **0/7** negative — while the **2-D (Q-free) gap does not** (−2.26 / −3.30 / −0.58, 18/21 one-signed). So the mean cancels the 1-D arm heavily and the 2-D arm barely, and the RATIO between them is not readable as a property of shape-matching. ⭐⭐ **The two forms agree on the AFTER value (2.13 vs 2.16 dB) and disagree entirely on the BEFORE one (6.83 vs 2.69)** ⇒ what the pooled form mis-states is its **BASELINE**. ⇒ **AP6's shape attribution is largely REHABILITATED** — the shape mismatch is the larger part of the disagreement — and **GATE AP's user decision still stands**, 2.13 dB being over the imported ±0.83 dB bar. ⚠⚠ **NOT "AQ4 was wrong": the shipped table has ONE entry per (GRUNT, DRIVE), so a mean over sweeps is exactly what WOULD be shipped ⇒ the pooled form is the right statistic for the SHIPPING question and the wrong one for a MECHANISM claim.** The correction is to the inference, not the number. ⭐ Guaranteed to be the same numbers by AR1b, which reproduces AP's and AQ's **stored** per-cell values at **0.00e+00 dB**. ⚠ A second, smaller instance is named rather than estimated: 1 cell of 8 pairs means over different sweep sets. | `analysis/notch_residual_gate.py` (GATE AR) AR2/AR3 |
| the three candidates s152/s153 named for the residual that survives shape-matching — the CENTRE offset, the CENSORING, the ASYMMETRY | ⛔⛔ **ONE REFUTED, ONE REFUTED ON A REPAIRED BAR, ONE *INVERTED* — s154, all three screened before anything was built** | 154 | **(a) CENTRE — REFUTED, and it was s153's own `NEXT` #4.** In the reader's own resolution the two centres agree to **≤ 1 cell in 21 of 26** cells (mean −0.09 cells; all five exceptions in the Cut row) ⇒ freeing f0 has almost nothing to move. **(b) CENSORING — REFUTED as the carrier.** ⛔ The first draft gated this on **\|r\| < 0.3, a number I invented**, and at the measured **r = −0.437** the whole verdict rested on it. Replaced by a **permutation test** (20 000 shuffles; **p = 0.0523**) and **r² = 0.191** ⇒ censoring accounts for **19 %** of the residual's variance. ⚠⚠ p sits ON the 0.05 convention and the gate says so rather than quoting the branch label — **both branches conclude "not the carrier"**, and r² is the bar-free half. Corroborates AP6 from a second quantity. **(c) ASYMMETRY — the candidate is INVERTED.** s153 named it as *"the PEDAL's null is asymmetric"*; measured, pedal skew **+0.028** vs composite **+0.152** ⇒ ⭐⭐ **the more asymmetric side is the COMPOSITE, i.e. the MODEL's own null** (an RBJ peaking section is symmetric in log-f BY CONSTRUCTION, so the correction cannot be the source). Direction is real (**20/26, exact sign test p = 0.0094**); SIZE is **at the reader's resolution** (over the bar at 0.5× the 1/48-oct cell, under at 1.0× and 2.0× — swept, s137's BAR-SENSITIVE pattern, after the first draft's verdict flipped on **1.4 %**: 0.208 vs 0.211). ⇒ **neither a licence to build nor a refutation** — it needs a better skew estimator, not a DSP change. | `analysis/notch_residual_gate.py` (GATE AR) AR5 |
| "the residual that survives shape-matching is a SHAPE coordinate the (f0, Q, gain) family does not span" (AQ4's conclusion, and the premise behind every proposed successor) | ⛔⛔ **IT IS NOT A SHAPE DEFECT AT ALL — IT CHANGES SIGN ACROSS THE STIMULUS LADDER, s154** | 154 | Per rung the residual reads **+2.63 (9/9) / +2.20 (7/8) / −1.65 (1/9)** ⇒ **no single (gain, Q) entry can be right at all three rungs, WHATEVER shape coordinate is freed** — which retires the whole "free one more coordinate" programme rather than any single candidate. ⭐ And the shipped Q's own error crosses zero on the same axis (pedal−composite **+5.02 / +3.07 / −3.57**), so no single Q entry is "closer" either: a **slope error with a crossing**, not an offset. ⇒ this is **s151 §6's architectural limit** (a knob-keyed stage cannot track a stimulus-dependent feature) measured on a **THIRD axis** — depth (s151), Q (AQ2b), and now the metric residual itself. ⭐ Free by-product of the same table: **freeing Q makes the metric disagreement one-signed across stimulus where the shipped Q's is not**, which is why AR3's paired baseline is 2.5× AQ4's pooled one. | `analysis/notch_residual_gate.py` (GATE AR) AR6/AR2 |
| ⭐⭐ item 6's **LAST unscreened pre-clipper lever** — a **drive-dependent treble-ladder `Zin`** (AO4's specification: the LOAD side of the drain-node divider, 4.97× the source side, the one parameter `drain_db` accepts and never moved) | ⛔⛔ **SCREENED AND REFUTED, s155 — AND IT IS DECIDED ON A THIRD AXIS THAT DID NOT EXIST IN THE FIRST DRAFT** | 155 | **AO4 was RIGHT about the lever and that is the first thing to record: this is the FIRST pre-clipper class not refuted on size** — a validated, sign-admissible perturbation reaches **477 %** of AH7's budget against **AK 2.46 / AJ 0.17 / AN 1.33 %** at their limits (S_zin 0.836 vs S_zout 0.166, recomputed = 5.03×). ⚠⚠ **Quote the second number with it: at a 1 % drift of the best element the reach is 0.3932 %** — the geometric lever is real, a PHYSICAL drift lands in the same order as the classes already refuted. ⭐ **And it is NOT shape-refuted the way its predecessors were:** a multi-element perturbation moves every pole and zero at once, so ⛔ **gate 5's `≤2` single-pole bound DOES NOT APPLY to this class** and the validated set does contain exponents to **+3.667**. What decides it is the **SIZE OF THE ELEMENT CHANGE**, graded as a FOLD change: the joint (exponent AND reach) points ask for `cut/C5+R14` at **×0.1 ×0.001** — R14 from 48.5 k to **48.5 Ω**, a different circuit, not a drift. Held to a fold ≤ **1.5×** (X7R's 50 %, deliberately generous; film 0.1 %, resistor self-heating ~1 %) **0 of 241** validated sign-admissible probes clear even the 2.0 bar. ⭐⭐ **THE THRESHOLD-FREE FORM, WHICH IS THE ONE TO QUOTE: of the 1050 probes at fold ≤ 1.5×, ZERO have a tilt change that even RISES across the limb**, against the deficit's 9/9. ⭐ Root cause, measured: **\|Zin\| falls at only −0.312 dB/oct at the vertex and −0.028 by 10 kHz** — asymptotically CONSTANT, so a perturbation of it is a pure GAIN there, which has zero tilt; the Jacobian's **σ₂/σ₁ = 5.64e−03** ⇒ to 99.9968 % of its energy EVERY small perturbation of this ladder makes ONE shape, exponent **−1.5915**. ⇒ **AK's root cause in a THIRD guise**, and item 6's gate 6 stated positively. ⭐⭐ Methodological, for the SECOND time: it **PASSES gate 4 at 3/3** (upstream of GRUNT, asserted 2.5e−13) **and is still refuted** — sign-admissibility is necessary, not sufficient. ⚠ A SEARCH over 7140 probes, not a theorem; AS4 covers small combinations, AS6 covers added elements. | `analysis/ladder_zin_tilt_gate.py` (GATE AS) AS2–AS6 |
| the ADDED-ELEMENT half of that class — a perturbation of a network need not be a drift of one of its parts (nothing had screened it; AJ screened a stray capacitance at the J201 GATE node only) | ⛔ **REFUTED, s155, and it closes ANALYTICALLY so the sweep is a check rather than the argument** | 155 | `trebleC8` ships at **0** (s99/s100 took C8 out of circuit), so it is an element **APPEARING**, and the ATTACK switch supplies two topologies free — a shunt at node P (`cut`) and a bridge across R8 (`boost`). Swept over **eight decades**, no rung survives the validity columns with the right sign. ⭐ The analytic branch is general: for ANY passive RC block added to this network, corners **BELOW** the band ⇒ asymptotically constant there ⇒ its tilt-change contribution decays (exponent < 0); corners **ABOVE** ⇒ `log\|H\| = c0 + c1 f² + O(f⁴)` ⇒ the tilt change is ∝ f² and the exponent approaches **2 FROM BELOW**, which is gate 5. Either way bounded by **2.000** against the deficit's **+2.779**. | `analysis/ladder_zin_tilt_gate.py` AS6 |
| ⭐⭐ AL3's single-signedness guard — built to stop the DEFICIT's exponent being a zero-crossing artefact, and never pointed at a MECHANISM | ⛔⛔ **AND THE FIRST DRAFT OF GATE AS DULY PUBLISHED THE ARTEFACT, s155 — 4 OF THE TOP 5 EXPONENTS ARE INVALID** | 155 | Read on the endpoint exponent alone the table tops out at **+5.335 / +4.140 / +3.962 / +3.813**, which would have been published as *"the class is SHAPE-ADMISSIBLE"*. `cut/R7 ×0.5` reads **+0.00017** at 1348 Hz and is negative everywhere above — its tilt change **crosses zero inside the limb**, so the endpoint ratio is divided by a number passing through zero. ⭐ **Two validity columns are therefore mandatory on any mechanism exponent from now on: SINGLE-SIGNEDNESS (AL3's guard) and MONOTONICITY of \|dT\| across the limb** — AL4 grades the deficit's RISING limb by construction (9/9), so a mechanism that turns over inside it is not tracking it whatever its endpoints say. **241 of 7140** probes carry both. | `analysis/ladder_zin_tilt_gate.py` AS3 |
| where the point-vs-area disagreement physically LIVES — never asked; AP6 and AQ4 both treat it as one lump | ⭐⭐ **DECOMPOSED BY AN IDENTITY, s154: THE BOTTOM TERM CARRIES 0.84 OF IT (corr −0.99), THE SHOULDERS 0.16 (corr +0.32)** | 154 | On ANY curve, exactly, `depth_point − depth_area == S − B` with `S` the shoulder term and `B` the bottom term — **asserted at 3.55e-15 dB over 26 curve readings**, so the two are the ONLY places the disagreement can live and the split is arithmetic rather than judgement. ⇒ the disagreement is **how much the 1/6-octave band averages the notch BOTTOM away — a sharpness difference INSIDE the half-depth width**, which is a coordinate neither the depth nor the Q pins. ⚠ Share AND correlation are both printed because a term can carry the MEAN without carrying the VARIATION. ⚠ This localises the residual; it does **not** license chasing it — AR6 (row above) says the remainder is stimulus-dependent, not a fixed shape. | `analysis/notch_residual_gate.py` (GATE AR) AR1a/AR4 |
| ⭐ s157's own `NEXT` #1 — *"the `locate()` finding is project-wide; `prom` is used as a presence/validity bar in GATE W, AA, AD, AE and in `od_tone_restore_fit`, and whether any of them leans on it as a HEIGHT has not been audited"* | ⭐⭐⭐ **AUDITED, s158 — AND THE ANSWER IS THE REASSURING ONE: THE PROJECT HAS EIGHT PROMINENCE ESTIMATORS AND ONLY ONE HAS AU's DEFECT** | 158 | An AST census of all 21 modules that define, call or subscript a prominence, each classified by ESTIMATOR and by ROLE. **E1** (`feature_locus_gate.locate`, the walk from the window ARGMIN) is read as a **HEIGHT by exactly ONE module — `od_tone_restore_fit.prom_table` — whose one published claim GATE AU already refuted (s157)**. Every OTHER quantitative depth in the project is on an estimator that **never walks** and therefore cannot have the defect: **E3** `null_locus_gate.notch` (named-shoulder 1/6-oct area depth — GATE R **and** GATE V's wash-out plane), **E4** `hw_trend_gate`'s fixed 3-band shoulder depth (**AD5/AD5b's depth-axis dose-responses**), **E6** `notch_geometry` (GATE AP/AQ/AR), **E7** `hf_artefact_gate.prominence` (GATE I's G3), **E8** `compression_law_gate.prom` (GATE S7). ⇒ **no depth finding in this table is exposed.** ⭐⭐ **E2** (`bass_peak_locus._best_interior`, s126's repair) genuinely CAN break — but its winner is the window argmin in **22.6 %** of curves and there it cannot, so the repair removes s126's identically-zero-at-an-edge pathology and does NOT make every reading topographic; ⭐ GATE AE **already says so itself** (*"a LOWER bound by construction"*), recorded rather than discovered. ✅ The census **REFUSES** on any unclassified or vanished site — the durable half, since E1's defect survived 35 sessions precisely because no site had been classified; it fired on its own first run, against this gate itself. ⚠ A mutation can prove the table's COVERAGE, never that `hw_trend_gate` really is E4 — that came from reading the source. | `analysis/prominence_audit_gate.py` (GATE AV) AV0/AV2 |
| AU1's SCOPE sentence — *"as a DETECTOR the statistic is unharmed; a real feature descends both sides"* | ⚠⚠ **TRUE ONLY IN AN UNFLANKED WINDOW, AND EVERY SHIPPED WINDOW IS FLANKED BY CONSTRUCTION, s158** | 158 | Measured as a dose-response against an INJECTED feature of known depth, in two arms. **ALONE on a bare tilt E1 invents nothing — 0 of 300 feature-free curves read PRESENT — and responds monotonically to depth.** Put the SAME window between two neighbouring features and **161 of 300 (54 %) of feature-free windows read PRESENT**, because the walk is climbing the neighbours' flanks; injecting a feature *at* the 1.0 dB bar adds only **+16 points** over that baseline. ⇒ the failure is **CONTEXTUAL, not intrinsic** — and GATE W's seven windows tile the band between consecutive named features, so all seven are flanked. ⭐ Corroborated on real data: pinning the extremum and widening ONLY the walk domain, **0 of 7 features give a window-free depth** (3 are WINDOW-DOMINATED — the cut moves the number by more than its own median) and **25.4 % of W3-valid readings change presence verdict at the shipped bar** when the window's log width doubles. ⛔ **A flip is NOT a rejected feature** — the wide window admits the neighbours' flanks too; this measures that a presence verdict is only as firm as the window. ⚠ False-negative direction is real and bounded: on a ±8 dB tilt a 4 dB feature can stay under the bar (the estimator being conservative, not wrong). ⭐ The widening is certified by a **theorem, not a tolerance**: `prom` is non-decreasing in window width (a max over a superset), so flips OUT must be exactly 0 — measured 0 at every bar, which is what proves the extremum is genuinely pinned and AV3 is not measuring s151's feature-jump. | `analysis/prominence_audit_gate.py` (GATE AV) AV3–AV5 |
| what E1's window-dependence COSTS the conclusions that rest on it | ⭐⭐⭐ **PRICED, s158: THE CLASSIFICATIONS SURVIVE, THE PERCENTAGES DO NOT — 0 of 7 W6 VERDICTS FLIP, AND THE SIZES MOVE BY UP TO 28.40 %** | 158 | A defect found is not a defect priced (s149). The E1 DETECTOR consumers publish **CENTRES**, so GATE W6's OWN statistic was re-graded on **W6's OWN membership rule** with the bar applied to the widened reading. ⚠⚠ **The first draft priced the WRONG statistic** — it invented "captures resolving at all 4 rungs, first-vs-last" and reported 3.48 % movement in a quantity W6 does not compute; W6's rule (read out of `gate_w6`, not guessed) is ENDPOINT captures only, per-CELL exclusion, the MEDIAN f0 per sweep, `span = max/min − 1`. ⭐⭐ Certified by a **cross-gate known answer: it reproduces GATE W's STORED w6 pedal spans to 0.000e+00 at all seven features** — available only because the pedal side is binary-independent. Result: **0 of 7 FIXED / DRIVE-DEPENDENT verdicts flip**, so open item 6's whole frame, AA6 and AD **stand**. ⛔ But the sizes move: bass_peak **7.82 → 36.21 %**, treble_peak **7.92 → 9.76**, mid_peak **7.95 → 9.62**, bt_notch **7.15 → 7.81**, against a locator resolution of **0.48 %** (W's own `GRID_STEP_FRAC/3`, imported). ⇒ **quote them as "~7–10 %, DRIVE-DEPENDENT", never to two decimals.** ⚠ `bt_notch` is the sharpest membership instance even though its span barely moves — its admitted cell count goes **17 → 64**, i.e. W6's bridged-T row rests on a quarter of the readings a wider window admits and lands on nearly the same number anyway. | `analysis/prominence_audit_gate.py` (GATE AV) AV6/AV6b |
| GATE W's `locate()` `prom` is a topographic PROMINENCE (a rise out of the extremum until the curve turns back) — assumed by every gate that reads it since s122 | ⛔⛔ **REFUTED STRUCTURALLY, s157 — THE TURN-BACK TEST IS UNREACHABLE CODE, FOR EVERY FEATURE AND EVERY CURVE** | 157 | `locate` sets `dd = d[m]` (min) or `-d[m]` (max), takes **`j = argmin(dd)`**, then breaks each walk on `dd[k] < dd[j]` — but `j` IS that argmin, so `dd[k] >= dd[j]` for every `k` and **the break can never fire** (asserted on 20 000 adversarial random windows, 0 breaks — not merely argued). ⇒ `prom` is `min(left max-descent, right max-descent)` **inside a FIXED window**, so a wider window can only enlarge it for the identical feature. Measured on `mid_peak`: **48 of 48** walks bound-terminated, and the curves are monotone to both bounds (max-descent minus drop-to-bound worst **0.000e+00 dB**), so it reduces EXACTLY to `min(d[peak]−d[358], d[peak]−d[620])` — a two-point read of the window's own bounds, i.e. of the NEIGHBOURING notches' flanks. ⚠ `locate`'s `edge` flag does NOT catch this: it fires on the EXTREMUM, interior in 24 of 24 rows. ⚠⚠ **SCOPE: as a DETECTOR it is unharmed** — a real feature descends both sides, and GATE AE's *"no interior extremum in 9 of 9"* is threshold-free and untouched. What it cannot be is a **HEIGHT**, or a comparison between two sides whose extrema sit at different places in the window. s126/s151's finding with the **mechanism proven** rather than observed. ⚠⚠ **THAT SCOPE SENTENCE IS QUALIFIED, s158: it holds only in an UNFLANKED window, and all seven shipped windows are flanked** — measured, 54 % of feature-free FLANKED windows read PRESENT against 0 % unflanked. See its own row above; do not re-quote "as a detector it is unharmed" unqualified. ✅ **And the audit it hands forward is DONE (s158, GATE AV)** — three rows above. | `analysis/peak_identifiability_gate.py` (GATE AU) AU1 |
| s151's stated reason for `kPeakGainDb = 0` — *"bleed-free, the model's peak is MORE prominent than the pedal's in 8 of 9 (GRUNT × DRIVE) cells, so boosting here would OVERSHOOT"* | ⛔⛔ **THE REASON IS REFUTED, s157 — IT IS BLEED-FREE-ONLY, THE EXACT DISEASE s156 FIXED FOR THE NOTCH.** ⚠ The VALUE is unchanged and now rests on the row below | 157 | Measured **bound-free** (the joint notch+peak+discarded-trend fit's own peak gain, which is what would set the constant), restricted to fits resting on no bound: **+1.44 dB mean at the listening condition (n=7, +1.00…+1.94) against −4.30 dB bleed-free (n=2, −5.60…−2.99)** ⇒ **the requested gain CHANGES SIGN with the mix**, so a bleed-free reading cannot carry the decision. s156 §1's finding on a second feature of the same stage. ⛔ Do not re-quote the 8-of-9 figure. ⚠ And the prominence deficit s156's `NEXT` #1 reported also changes sign across DRIVE (**+1.083 … −0.854 dB** at the listening condition, 10 positive / 5 negative of 15) — so it names no direction either, on top of being read from a statistic the row above shows cannot see the peak's height. | `analysis/peak_identifiability_gate.py` (GATE AU) AU2/AU3 |
| s156's own `NEXT` #1 — *"`kPeakGainDb` may now be worth revisiting; the ~450 Hz peak is 0.3–1.1 dB less prominent at the listening condition"* — i.e. give the peak the mix-keyed treatment the notch got | ⛔⛔ **REFUTED, s157, ON THE ONE AXIS THAT DECIDES IT: THE PEAK TERM IS NOT SEPARABLE FROM A3.** `kPeakGainDb` STAYS ZERO — and this, not s151's bleed-free argument, is the reason | 157 | `od_tone_restore_fit`'s own `FIT_BAND` block states that the quadratic-in-log-f trend the fit discards **IS A3**, so a peak term that trend can already reproduce is A3 wearing a biquad. Measured as `keep` (fraction of a term's own norm surviving projection onto that trend basis over 250–850 Hz): the **shipped peak at Q = 2.20 keeps 0.313**, against the **notch term's 0.848 median** over all 15 cells — the notch, the term this stage has already accepted as identified (s156: it buys **1.56 dB** of fit against the 800 Hz candidate's 0.058), is **2.71× more separable**. ⇒ a fitted **+1.3 dB** delivers only **+0.41 dB** of shape the trend could not already explain; the rest is `one-knob-two-jobs-is-compensating` — s156 §3's own reason for rejecting the 800 Hz candidate (*"A3 seen as a shape"*), on a second term. ⭐⭐ **AND IT IS STRUCTURAL: separability is MONOTONE in Q** (0.011/0.087/0.187/**0.313**/0.423/0.594/0.721/0.803/0.877 at Q = 0.5/1/1.5/**2.2**/3/5/8/12/20), reaching the notch's 85 % only above **Q ≈ 20**, while this feature is BROAD by nature (it is the recovery BETWEEN two notches) ⇒ **the shape that would be identifiable is not the shape the feature has, so no (gain, Q) choice fixes it.** ⚠ Corroborating only: **15 of 24** fits rest a parameter on a bound, and the request spans **15.25 dB** across stimulus at one fixed cell — s151 §6's architectural limit on a **third** axis after AQ2b's Q and AR6's metric residual. ⚠ NOT claimed: that the device has no peak there, or that we match it — the **CENTRE** is still 1.093× high (22 of 24 readings), which is item 6's territory. | `analysis/peak_identifiability_gate.py` (GATE AU) AU4/AU1b |
| s158's own `NEXT` #1 — the **MODEL side** of the prominence audit, left owed because AV4 found 25 % membership instability on the pedal side | ⭐⭐⭐ **DONE, s159 — AND IT IS THE REASSURING ANSWER: 0 OF 4 RESOLVED MODEL VERDICTS FLIP, SO OPEN ITEM 6's CONTRAST SURVIVES AT *BOTH* ENDS** | 159 | The model side is the half that could have been manufactured: W6's pedal rows are **DRIVE-DEPENDENT** (a POSITIVE result a window-limited estimator can only UNDER-report) and its model rows are **FIXED** (a NEGATIVE result, exactly what a window-bounded estimator CAN invent). Re-graded on W6's own membership with the bar applied to the pinned-widened reading: **mid_notch 0.59 → 0.59, bt_notch 0.15 → 0.43, treble_peak 0.21 → 0.21, mid_peak 8.98 → 17.70 %** — all four classifications unchanged. ⇒ **the model's pinnedness is not an artefact of where GATE W cut its windows**, so item 6's frame, AA6 and AD stand at both ends (pedal side: s158, 0 of 7). ⭐⭐⭐ **AND IT COST NO RENDER — s158's estimate was wrong about that**: `build/s122_feature_locus/` still holds the artefacts GATE W published from, and AW1b proves it by reproducing the STORED w6 MODEL medians AND spans to **0.000e+00**. ⚠⚠ That known answer is load-bearing rather than bookkeeping — **16 of 24 renders carry a BINARY STAMP that POSTDATES the stored report**, so on the stamps alone the cache is a different epoch wearing the right filenames. ⛔ Sizes still move up to **8.72 %** against a 0.48 % resolution ⇒ s158's *"quote ~7–10 %, never two decimals"* now applies to the model column too. ⭐ `bass_peak` UNRESOLVED → **DRIVE-DEP (5.49 %)** is a MEMBERSHIP recovery, not an inversion, and it **independently corroborates GATE Y's Y6** (s126 measured the model's bass peak walking −7.8 % from a different construction); ⛔ not a licence to quote 5.49 % as a measurement. | `analysis/model_prominence_gate.py` (GATE AW) AW1b/AW4 |
| "the shipped chain may have moved GATE W's model rows since s122" — never asked; three DSP changes have landed and one of them is a biquad inside `mid_notch`'s own window | ⭐⭐ **MEASURED, s159 — 3 OF 4 RESOLVED ROWS ARE UNMOVED AND NO W6 VERDICT IS STALE; ONE PROMINENCE IS** | 159 | Same 24 conditions re-rendered with the current binary into a **PRIVATE** directory (never GATE W's cache — the gate fingerprints it before/after and refuses on any change), non-vacuity asserted first. Matched-membership Δf0: **mid_notch −1.52 %, mid_peak −0.35 %, bt_notch −0.14 %, treble_peak +0.03 %** against a 0.48 % resolution ⇒ only `mid_notch` moved, and it is attributable **by construction** (`OdToneRestore`'s centre is 323 Hz, inside that window). ⭐ It moved the right way on an axis it was never fitted against (DEPTH was): model **328.31 → 323.23 Hz** against the pedal's **327.21 → 322.19**, closing ~+1.7 % → ~+0.1 %. ⛔ **What IS stale: the model-side PROMINENCE at `mid_notch`, 4.48 → 19.91 dB.** Nothing quotes it (AV0's census puts E1's only HEIGHT consumer in `prom_table`, already refuted by GATE AU), so it is a doc correction, not a re-baseline — but do not read that row moving as a regression. ⚠⚠ **`aggregate-moved-check-membership-first`, TWELFTH occurrence, committed by s159's own first draft**: POOLED, `mid_peak`'s centre moves **−6.66 %** and would have been published as *"the stage moved the 450 Hz peak"*. It did not — deepening the neighbouring null pushes `mid_peak` past the 1.0 dB bar and **admits 20 cells that were refused at s122**. Matched: **−0.35 %**. | `analysis/model_prominence_gate.py` (GATE AW) AW5 |
| "the model's bleed-free 320 Hz null now OVERSHOOTS the pedal by ~6 dB" (read off GATE W's E1 prominence, pooled over the endpoint set) | ⛔⛔ **REFUTED, s159 — A SECOND MEMBERSHIP ARTEFACT, AND THE E1-vs-E6 GAP IS A *WIDTH* STATISTIC** | 159 | The 6.2 dB was a median over **16 endpoints × 4 sweeps** (mixed DRIVE/ATTACK/GRUNT/MASTER) read as though it were the three bleed-free rungs. On the stage's OWN estimator (E6, `notch_geometry`) the shipped bleed-free null is within **0.41 dB** of the pedal at all three, reproducing s151's fit residual. ⭐⭐ And the residual E1-vs-E6 disagreement (up to **3.78 dB** on identical curves) is attributed by a **THEOREM, not a correlation** — a first draft published `corr = −0.975` **at n = 3**, where any three points give a large \|r\| and two of them are ordered the wrong way. E1's shoulders are the FIXED window edges (285, 358) Hz; E6's are the curve's own local maxima inside (210, 520) Hz, a **SUPERSET** ⇒ **`E1 ≤ E6` IDENTICALLY** (asserted, 0 violations of 6), so the deficit `E6 − E1` is exactly *how far the curve is still rising at 285/358 Hz* — a **WIDTH** statistic. Measured: model **5.41 / 6.49 / 1.32** vs pedal **4.29 / 2.70 / 0.33** ⇒ **the model's null is BROADER at 3 of 3 rungs**, which is this stage's already-known Q defect. ⇒ **GATE AV's point on a second pair of estimators: E1 mixes DEPTH with WIDTH.** ⛔ Never read an E1 prominence as a depth, and never adjudicate `OdToneRestore` on one. | `analysis/model_prominence_gate.py` (GATE AW) AW6 |
| GATE AV's widening THEOREM — *"`prom` is a max over a cell set and widening only ADDS cells, so it is non-decreasing in window width"*, stated unqualified in AV's docstring and relied on by AV4 | ⚠ **IT HAS A PRECONDITION, s159 — and asserting it without one REFUSES CORRECT DATA (177 decreases, worst 0.516 dB)** | 159 | Each side's rise is a max over that side's cells and widening only adds cells — **provided the side is non-empty**. When the extremum rests ON a window bound one side has NO cells and the walk reports its rise as the CONVENTION **0.0**, which is not the max over an empty set; widening replaces that floor with a real maximum and, the curve still falling outside the old window, the value legitimately goes **NEGATIVE**. Those readings are exactly the ones GATE W3 refuses. Restated with the precondition: **0 decreases over 1416 adjacent widen pairs on INTERIOR readings.** ⭐ And the exception is a finding, not noise — **177 of the 200 excluded readings go negative under widening**, i.e. **s126's edge-resting pathology with a SIGN on it**: a shipped `prom` of 0.0 was a floor, not a measured rise, which is a sharper statement than `locate`'s own `edge` flag. ⚠ AV4 is untouched: it measured the CONSEQUENCE (0 flips OUT) on the W3-valid population, where the precondition holds. | `analysis/model_prominence_gate.py` (GATE AW) AW1c |

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
   ✅ **DONE, SESSION 160 — the other three consumers are re-pointed.** `clean_headroom_probe.py` and
   `clean_thd_check.py` had the bad capture **removed** from their candidate lists (annotated in
   place with both defects — the 4.447 dB mis-dial AND the `lvl_-3` rung s142 found PINNED, which
   matters more for a THD/headroom probe than the level error does); `captures.py`'s Tier-1 list
   keeps the filename (it is the canonical inventory, consumed only by the filename-parse
   self-test, not by graded membership) but is annotated not to be read for level. ⭐ Found in
   passing: `clean_headroom_probe.py`'s `K_INPUT_REF_SHIPPED` literal was still **3.377** — the
   session-17 value, 3.75× the current `kInputRef = 0.90` — corrected. **This item is CLOSED; no
   further consumer of this capture exists in `analysis/`.**
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
   ✅✅ **CLOSED, USER DECISION SESSION 160 — BRANCH (a) ACCEPTED, BRANCH (b) NOT PURSUED.** The
   clipper's ceiling really is ~5.4× below the derived physical rail; it is a standing property of
   the fit, not a fixable defect (the supply arithmetic above proves no lever reaches it). Branch
   (b) — hunting for ~14.7 dB of missing pre-clipper gain — is deliberately NOT started: it would be
   a fresh, unscoped carrier search of the same shape as item 6's, with no candidate identified and
   no measured connection to A3 (the 14.7 dB and A3's 4.38 dB are different quantities, per the
   paragraph above). ⛔ Do not re-open this item without a specific candidate for branch (b) in hand.
6. ⭐⭐ **THE MODEL LACKS A DRIVE-DEPENDENT MECHANISM ABOVE ~2 kHz — RESTORED s125, having been
   DROPPED in the s122→s124 handover chain.** ⛔ This is **not** a centre-frequency item: GATE W
   settled that none of the six flagged centres is a *corner* error, and that stands — do not point
   an optimiser at a capacitor. What it is: the pedal's HF features **move with drive** and ours are
   pinned, so we are wrong at every drive setting and the error grows with it.
   ✅✅ **USER DECISION, SESSION 160 — THE PHYSICAL-CARRIER SEARCH IS CLOSED. Everything below this
   line is HISTORICAL RECORD (why nothing physical works), not an open search.** GATE AM's
   exhaustive resonance census (0 resonances anywhere at/upstream of the clipper, for ANY component
   values) and GATE AS's class-level ladder screen (0 of 1050 physically-bounded `Zin` perturbations
   even rise the right way) leave no remaining candidate to name — this is not a stall, it is a
   closed search space. ⇒ **converting to a scoped, non-schematic [ENG] correction — task E —
   same architecture as `OdToneRestore` (item 10): a drive-keyed tilt/shelf section fitted directly
   to the sized target below (AF6/AH7: ~1.2 dB/oct at 2935 Hz, growing with drive), not derived from
   a component.** It does NOT need to satisfy the six carrier gates below (gates 1–6 test whether a
   REAL component could cause this; an engineered correction only needs to match the measured
   curve). ⛔⛔ **SCOPE: target the treble-peak slope ONLY.** The bridged-T notch depth collapse, the
   bass-peak walk, and the missing 4.5–6 kHz null (three tables below) are separate, independently-
   sized symptoms of the same gap — do not bundle them into E; decide on each separately, after E
   lands, if still wanted. ⛔ **HARD CAP: 3 sessions.** If the fit will not hold across the drive
   ladder by then, ship the best compromise and close this item permanently — no further physical
   search, no further artificial-fix iteration beyond the cap.
   **Historical record — why every physical carrier failed (`feature_locus_gate.py` W6, 24 dB
   stimulus ladder):**
   ⛔⛔ **QUOTE THE CLASSIFICATION, NOT THE PERCENTAGE (GATE AV, s158; GATE AW, s159).** Every
   `FIXED` / `DRIVE-DEPENDENT` verdict in the two tables below is **window-STABLE on BOTH sides —
   0 of 7 pedal rows flip (s158) and 0 of 4 resolved MODEL rows flip (s159)** when the selecting bar
   is re-applied to a widened reading, so every argument this item builds on them stands. ⭐ The
   model half is the one that mattered: a `FIXED` verdict is a NEGATIVE result and a window-bounded
   estimator is exactly what could have manufactured it. ✅ **And s159 re-rendered the same
   conditions with the CURRENT binary: 3 of 4 resolved model rows are unmoved by everything shipped
   since s122, and 0 of 4 classifications change** — so this item's frame is safe against both the
   estimator and the epoch. The **percentages are not**: re-graded on W6's own membership they move
   **7.92 → 9.76 %** (treble peak), **7.95 → 9.62** (mid peak), **7.15 → 7.81** (bt notch) and
   **7.82 → 36.21** (bass peak) on the pedal side and up to **8.72 %** on the model side, against a
   locator resolution of 0.48 %. ⇒ **say "~7–10 %, DRIVE-DEPENDENT", never two decimals.** Their
   own CLOSED/REFUTED rows carry the derivation.
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
   | ⭐⭐⭐ a **DRIVE-DEPENDENT TREBLE-LADDER `Zin`** — AO4's specification, the LOAD side of the drain-node divider (4.97× the source side), i.e. the whole class the spent-divider argument does NOT reach | ⛔⛔ **Decided on the SIZE OF THE ELEMENT CHANGE, s155, because the other two axes do NOT refute it.** The lever is real (**477 %** of budget at a limit — the first pre-clipper class that reaches) and gate 5's `≤2` bound **does not apply** to a multi-element perturbation (exponents to **+3.667** exist). But the joint points ask for **×1000** element moves; held to a fold ≤ **1.5×**, **0 of 241** validated probes clear even 2.0, and threshold-free, **0 of 1050** physically-bounded probes have a tilt change that even RISES. ⭐ Root cause: `\|Zin\|` slope **−0.312 dB/oct at the vertex**, asymptotically constant ⇒ a perturbation is a pure GAIN there; σ₂/σ₁ = **5.64e−03** ⇒ ONE reachable shape, exponent **−1.59**. ⛔ ADDED elements fall too, analytically (≤ 2.000). ⚠ A search over 7140 probes, not a theorem | 155 |
   | ⭐⭐ the **J201 drain node's OUTPUT RESISTANCE** (`ro`/`rq2`) sagging with the operating-point current — the carrier s139/s140's exhaustiveness claim MISSED | **Three interlocking refutations, so no choice of direction rescues it:** ⚠ **numbers RE-QUOTED s149 on the corrected ladder:** the sign-admissible direction (`L→∞`) reaches **1.334 %** of budget; the direction that reaches is now only **23.0 %** (`L→0`) and has the **wrong sign at 10/10** of AL4's limb centres; and **both** fall with frequency (**f^−1.78**) where the deficit rises (**f^+2.78**). ⇒ **NEITHER direction reaches**, so the physical direction of the Id shift cannot change the verdict and the shaper-rectification measurement is NOT owed. ⭐ Root cause AN3b, weakened but standing: `Zout/Zin = **4.97:1**` at the vertex (⛔ **not** the 27:1 s148 published) and `\|Zin_ladder\|` falls at **−0.455 dB/oct** (not −1.75) ⇒ a drain-node source-impedance perturbation is still largely spent there — AK's route 2 (f^−1.87), AJ's moving-pole class and this still share a falling exponent | 148 |
   ⭐⭐⭐ **⇒ EVERY NAMED CARRIER ON BOTH SIDES OF THE CLIPPER IS REFUTED — INCLUDING THE J201's
   OWN NONLINEARITY (s140) AND ITS DRAIN OUTPUT RESISTANCE (s148) — AND SINCE s155 THE PRE-CLIPPER
   SIDE IS ALSO CLOSED BY *CLASS* RATHER THAN BY NAME (GATE AS screens every perturbation of the
   treble ladder, not a component list), WHICH IS THE FIRST TIME THAT DISTINCTION HAS BEEN EARNED.**
   ⚠⚠⚠ **BUT THE "every named carrier" SENTENCE HAS BEEN FALSE TWICE, SO READ IT AS "every carrier
   that has been NAMED" AND NOTHING MORE.** It was
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
   CLOSED/REFUTED rows carry it.
   ✅✅ **SCREENED s155 (GATE AS), AND THE ANSWER IS NULL — SO THE PRE-CLIPPER SIDE IS NOW CLOSED BY
   CLASS, WHICH IS THE STRONGER RESULT s149 SAID IT WOULD BE.** AO4 was right about the lever (5.03×,
   and it reaches **477 %** of budget at a limit — the first pre-clipper class not refuted on size),
   and ⛔ **the paragraph above is WRONG that gate 5's `≤2` bound "still applies to any SINGLE element
   drift"**: a perturbation of a multi-element network moves every pole and zero at once, cancellation
   is available, and exponents to **+3.667** exist. What refutes the class is the **SIZE OF THE ELEMENT
   CHANGE** — fold ≤ 1.5× ⇒ **0 of 241** validated probes clear even 2.0, and threshold-free **0 of
   1050** even RISE across the limb — plus the added-element branch closing analytically at ≤ 2.000.
   ⛔ **Do NOT re-screen this ladder from a component list**; a new candidate must clear GATE AS's
   fold-change frontier, entry price a mechanism supplying a **>2× element change with drive**.
   ⚠ The deficit is untouched
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
   ✅✅ **USER DECISION, SESSION 160 — SKIP THE DISCRIMINATION, APPLY AN ARTIFICIAL CORRECTION
   INSTEAD (task D).** Rather than spend a session designing a new measurement to tell topology
   mismatch (a) from a missing downstream stage (b) apart, reshape the LEVEL taper/mix law directly
   against the measured sensitivity gap (the matched-pair GATE K instrument above), targeting the
   ~2–3× LEVEL-sensitivity ratio rather than a component. ⛔⛔ **STATE THIS UP FRONT, NOT AFTER: this
   correction WILL NOT MOVE ANY RELEASE-GATE ROW.** `comprehensive_report`'s per-row gain match
   deletes this exact class of error by construction — the same property that let GATE K's 9.3 dB
   absolute-level defect sit invisible in the main matrix for ~100 sessions means fixing it can't be
   scored by that matrix either. This closes a real knob-behaviour defect (audible on a LEVEL
   sweep), not a ship-blocker. ⛔ Do not re-open the topology-vs-downstream question unless D's fit
   itself fails to converge — a fit failing is evidence the symptom isn't a simple sensitivity
   mismatch, which would be the first real reason to go back and discriminate.
10. ⭐⭐ **`OdToneRestore` — the user-authorised, NON-SCHEMATIC 320 Hz null restore (s150 built,
    s151 re-fitted and made GRUNT-aware). SHIPPED and converged; five things remain open.** Depth is
    now within **±0.83 dB at all three GRUNT positions across the drive ladder**, against a starting
    point of 10–25 dB short at flat/boost. ⛔ This item is **not** an item-6 mechanism hunt — the
    user explicitly authorised an artificial correction here, overriding the usual schematic
    preference, and scoped that authorisation to this one tone complex. Do not generalise it.
    **The open items are listed at the end of `docs/session-log.md` SESSION 151, as amended by
    SESSION 152.**
    ⭐⭐⭐ **s151's TABLE WAS STILL BLEED-FREE-ONLY, AND THAT WAS THE HEAD DEFECT — RE-FITTED s156 AS
    A MIX-KEYED LAW.** The user checked `ref-od.wav` (LEVEL noon, the actual listening condition)
    directly against captures and found both notches shallow, worse at low drive; measured, the
    bleed-free table was **6–13 dB short** at LEVEL noon and had the **wrong sign** at DRIVE 0 (a
    6.5 dB BOOST where a 1.2 dB cut was needed). ⛔ **The "Fit BLEED-FREE and re-measure" instruction
    two paragraphs below is SUPERSEDED** — the stage now reads `LevelBlend::cleanFraction()` every
    `applyParams()` and its cut is `base[g][d] + K[g][d]*S(cleanFrac)`, provably sufficient because
    captures reaching the same clean fraction by different LEVEL/BLEND routes agree to 0.05 dB
    (GATE AT's AT2, `analysis/od_notch_mix_law.py`). Still fit/measure the base row bleed-free (it is
    the cleaner corner), but a bleed-free-only table is no longer what ships. Listening-condition
    depth error now **+1.0…+1.5 dB** (was ~+8), floored by a measured **DEPTH CEILING**: a 40 dB
    OD-path cut at the listening mix gives only a 0.47 dB composite null, shallower than the shipped
    12.34 dB cut's 1.60 — the residual is A3 (the OD path's own quietness), not reachable from this
    stage's gain. ⭐ Two things checked and cleared this session that a future one should not re-open
    for this stage: the ~450 Hz peak between the two notches (worst change −0.145 dB from the deeper
    null, most cells near zero or positive) and the ~800 Hz region (NOT a notch defect — a biquad
    there buys 0.058 dB of fit against the 320 Hz term's 1.56, and its sign flips with GRUNT).
    Three new CLOSED/REFUTED rows and `docs/session-log.md` SESSION 156 carry the detail.
    ✅✅ **ITEM 0 (the censored flat/boost targets) IS ANSWERED, s152 — and it split into three
    facts, two of which contradict how it was written.** Three CLOSED/REFUTED rows carry it. Short
    version: the censoring is **real** (16 of 26 readings), the area estimator is **4.1× less
    sensitive** to it — and re-solved in the table's own unit **7 of 9 entries want LESS gain, not
    more**, so ⛔ *"the shipped corrections are conservative"* is not a safe reading. ⭐⭐ And the
    residual disagreement between the two metrics is **NOT the censoring** — it is a **shape**
    mismatch — which s153 then **refuted as the explanation** (matching Q closes only 20 % of it).
    ⛔⛔ **THAT LAST CLAUSE IS ITSELF CORRECTED, s154: the 20 % is UNPAIRED. Paired, matching Q
    closes 69 %, so AP6's shape attribution is largely REHABILITATED** — see AR3's CLOSED/REFUTED
    row, and note the user decision above is untouched (the pooled form is the right statistic for
    the SHIPPING question; only the mechanism inference moved).
    ✅✅ **AND THE USER DECISION IT RAISED IS TAKEN, s153: THE TABLE STAYS AS SHIPPED.** The
    area-solved alternative is **declined** — the trade is a wash (entries move up to 4.92 dB while
    achieved error moves ~0.5 dB, so the entry is weakly identified), `reference-sources.md` §1/§3
    make **HARDWARE** the authority here and record it **DEEPER** than ND so the smaller table moves
    *away* from it, and which metric the **ear** follows is established by nothing measured.
    ⛔ Recorded at `kNotchGainDb` itself, not only in the log; its own CLOSED/REFUTED row carries the
    numbers. ⚠ This settles **which target to fit**, and does NOT retire the censoring finding
    (16 of 26 readings; the area estimator is 4.1× less sensitive to it).
    ✅✅ **THE (gain, Q) 2-D SOLVE WAS BUILT, s153 (GATE AQ) — AND IT ANSWERED THE HEAD ITEM IN THE
    NEGATIVE THREE TIMES OVER.** Four CLOSED/REFUTED rows carry it; short version:
    **(a)** the Q reader every Q number on this stage was measured with is **quantised to 8 distinct
    values** (worst error −42 %), so *"1.35–1.51 too broad"* is one to two steps of the instrument.
    Fixed additively with **`q_interp`**; GATE AP is byte-identical after the change.
    **(b)** the *"structural"* claim **SURVIVES as a measured limit, but only at CUT** — one section
    reaches the pedal's Q in **21 of 26** cells and all 5 failures are Cut, with Cut × DRIVE 0.50
    unreachable at all three sweeps. ⛔ Do NOT generalise it to Flat/Boost, which reach everywhere.
    **(c)** ⛔⛔ matching the shape **does NOT dissolve GATE AP's user decision** — the metric gap
    goes **2.69 → 2.16 dB** against a ±0.83 dB bar. ⚠⚠ **But the −20 % and the successor drawn from
    it are BOTH corrected by s154 (GATE AR), which is the head reading for this item now:** the
    statistic is unpaired and the paired form reads **6.83 → 2.13 dB (−69 %)** ⇒ **AP6 is largely
    REHABILITATED**; the residual does **NOT** live in the centre (**≤ 1 cell in 21 of 26**); the
    asymmetry candidate is **inverted** (it is the MODEL's null that is skewed, and only at the
    reader's resolution); and — the one that retires the programme — **the remainder CHANGES SIGN
    across stimulus, so it is not a shape coordinate at all.** Four CLOSED/REFUTED rows carry it.
    ⛔ ⇒ **do not free the centre, and do not build the 3-D solve.**
    ⚠⚠ **AND THE ITEM MAY NOT BE WORTH WORKING AT ALL: the pedal's own Q spans 1.29x–2.93x across
    stimulus at FIXED (GRUNT, DRIVE)** — larger than the defect in 8 of 9 cells — which is s151 §6's
    architectural limit measured on the Q axis. ⇒ read that as an argument for leaving `kNotchQ`
    **alone**; if the row is worked anyway, the shoulder-shaping section is owed at **CUT ONLY**.
    ✅✅ **USER DECISION, SESSION 160 — WORK IT, WITH A STOP CONDITION (task A).** Add the
    shoulder-shaping section at GRUNT-Cut only (Flat/Boost already reach everywhere — do not touch
    them). Acceptance: depth stays within the shipped ±0.83 dB everywhere, Cut's Q error drops
    below the reader's own resolution, CLEAN stays bit-identical, release gate no worse. ⛔ **HARD
    CAP: 2 fit iterations.** If Cut isn't reachable after two, ship the better of the two and close
    this sub-item — the architectural Q-span ceiling two sentences up means there is a real limit
    to what any knob-keyed table can do here. ⛔ Out of scope for this task: freeing the notch
    centre, the 3-D solve, re-opening `kNotchGainDb`'s point-vs-area decision, `kPeakGainDb`.
    ⚠ `kPeakGainDb` is still all zeros **by measurement, not by default** (s151 item 3: the model's
    peak is MORE prominent than the pedal's in 8 of 9 cells, so boosting would overshoot).
    ⛔ Fit BLEED-FREE and re-measure after ANY upstream OD-path change — this stage is calibrated
    against the model's own null, so it goes stale when that null moves. ⚠ As of s156 this means
    re-running the ACCEPTANCE table across all five `--set` conditions (bleedfree/listen/blend/
    grunt_flat/grunt_boost), not just bleedfree — the mix-keyed law is only as good as the shape
    node it was solved from.
    Instruments: `analysis/od_tone_restore_fit.py` (`--stage-off` [now honoured by `--matrix` too,
    s156], `--depth point|area`, `q_interp`), `analysis/od_notch_mix_law.py` (GATE AT, s156 —
    `--collapse` for AT2's falsification test, `--law` to re-emit the tables),
    `analysis/null_depth_censor_gate.py` (GATE AP) + `analysis/_mutate_gate_ap.py` (9/9 arms),
    `analysis/notch_shape_gate.py` (GATE AQ) + `analysis/_mutate_gate_aq.py` (10/10 arms), and
    `analysis/notch_residual_gate.py` (GATE AR) + `analysis/_mutate_gate_ar.py` (**11/11 arms**,
    four of them computed-verdict). ⚠ AP/AQ/AR's own stored reports and mutation arms were fitted
    against the PRE-s156 bleed-free-only law — re-verify before trusting their numbers forward.
11. ⭐ **ADDED, SESSION 160 (task F) — is the session-120 DRIVE/distortion ear-lead still true on
    the current build, or already closed?** *"plugin needs ≈0.8 to match the [ND capture]'s
    distortion at DRIVE max; tracks closely at DRIVE≈0.5"* — recorded under "Project-specific
    carry-forwards" and never resolved. ⛔⛔ **IT CITED "open work item 11" AS THE THING TO CHECK,
    AND THAT WAS A DEAD POINTER** — into a session-60/61/63/66 numbering scheme this project
    abandoned ~90 sessions ago; the lead sat unresolved because its own follow-up pointed nowhere.
    This item reclaims the number for real. **Goal:** render the current build at DRIVE 0.8 and
    1.0, compare against ND's DRIVE-max capture, and check whether the 0.8≈1.0 relationship still
    holds. Read-only, no DSP change. ⚠ **A tension to test rather than assume away:** the *later*,
    corrected GATE Z finding (s128) has the model **under**-distorting at DRIVE-max/hot-stimulus —
    the opposite direction from "needs less drive to match". Either the two are measuring different
    things (perceived saturation character vs. THD%) or the ear-lead is stale; do not assume either
    without rendering. **Stop condition: one measurement.** It answers yes/still-open/no either way.

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
  regression **twelve** times (`aggregate-moved-check-membership-first`). ⚠ The twelfth (s159) is
  the first inside an **epoch** comparison, where the conditions are identical by construction and
  it is the admission BAR that moves the population — **difference two epochs only on the cells
  admitted in both.**
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

⛔⛔ **SESSION 152 REBUILT, AND FOR A REASON WORTH KEEPING: THE SHIPPED HEADER WAS UNCOMPILED.**
`OfflineRender` was built at 18:37 on 2026-08-04; `src/dsp/OdToneRestore.h` was last edited at
**19:10**; s151's matrix report was written at **19:23** — so every s151 artefact came from a binary
predating the header it ships. That is the trap s151 itself caught one session earlier, re-armed by
its own closing documentation pass. ✅ **Settled by measurement: 4 cells re-rendered after the
rebuild are BIT-IDENTICAL** (both GRUNT extremes × both DRIVE ends) ⇒ the edit was comment-only and
**every s151 number stands**. ⭐ GENERAL: *a comment-only pass at the end of a session re-arms the
staleness that session just documented* — rebuild after the last `src/` edit even when it is prose.
⚠ s152 changed **no** `src/` file and **no** constant; it added `analysis/null_depth_censor_gate.py`
(GATE AP), its mutation runner, and a second depth estimator in `od_tone_restore_fit.py`.
**ctest 19/19** (69.2 s).

⚠ **SESSION 153 touched `src/` in COMMENTS ONLY (`OdToneRestore.h`), changed NO constant, and
REBUILT — once, after its last `src/` edit, with `pgrep` run first** (s124's check; s152's lesson
that a closing prose pass re-arms the staleness it just documented). ✅ **Verified bit-identical:**
GATE AQ's full output before and after the rebuild differs only by the harness's own *"rendered at a
DIFFERENT BINARY — re-rendering"* notices, every measured number unchanged. It added
`analysis/notch_shape_gate.py` (GATE AQ) + `analysis/_mutate_gate_aq.py` (**10/10 arms**), and an
**additive** `q_interp` key in `od_tone_restore_fit.notch_geometry` (GATE AP's stored report is
byte-identical after it). **ctest 19/19** (67.5 s at -j 12).
⭐⭐ It also fixed a defect in **BOTH** mutation runners: a mutant runs `main()`, so it was writing
the gate's **own report path** and leaving the last arm's output on disk wearing the real gate's
name. Mutant reports are now PID-redirected (the redirect REFUSES if it cannot apply) and cleaned
up. ⚠ That defect cost s153 a false *"the rebuild changed the numbers"* alarm — the artefact being
compared against was a mutant's.

⚠ **SESSION 154 touched `src/` in COMMENTS ONLY (`OdToneRestore.h`'s `kNotchGainDb` block), changed
NO constant, and REBUILT — once, after its last `src/` edit, with `pgrep` run first.** ✅ **Verified
bit-identical by the stronger test s153's alarm argues for: GATE AR's stored report is BYTE-IDENTICAL
across the rebuild** (`json.dumps(sort_keys=True)` equality, plus a per-leaf scan). **ctest 19/19**
(72.6 s at -j 12). It added `analysis/notch_residual_gate.py` (GATE AR) + `analysis/_mutate_gate_ar.py`
(**11/11 arms**, four computed-verdict), and two **additive** keys in
`od_tone_restore_fit.notch_geometry` — the interpolated half-depth crossings `xlo_f` / `xhi_f`, which
nothing existing reads and which are what makes an ASYMMETRY reading possible at all (GATE AP's and
GATE AQ's stored reports are unchanged across the addition — the s153 `q_interp` pattern, twice).
⭐ It also replaced a transcribed `2.69 → 2.16` inside GATE AR with a read of GATE AQ's **stored**
report (`rebuild-targets-dont-transcribe`); it reproduces the transcription exactly, which is a free
known answer that the import reads the right field.

✅ **SESSION 155 TOUCHED NO `src/` FILE AT ALL AND DID NOT BUILD** — so it is the first session since
s152 that does **not** re-arm the render-cache bill, and the ~25 min stays owed from s154 rather than
being owed again. It added `analysis/ladder_zin_tilt_gate.py` (GATE AS) + `analysis/_mutate_gate_as.py`
(**12/12 arms**, five computed-verdict) and one new report, `analysis/reports/s155_ladder_zin_tilt.json`.
✅ The four stored reports it reads (`s135` / `s137` / `s141` / `s149`) are **unmodified** — verified by
mtime, and the gate opens them read-only. **ctest 19/19** (68.8 s at -j 12), unaffected because no
binary changed.

⛔⛔ **SESSION 156 CHANGED DSP BEHAVIOUR AGAIN — the `OdToneRestore` bleed-free table became a
MIX-KEYED law.** Touched `OdToneRestore.h` (new `setCleanFraction()`, `kNotchMixK`/`kMixCf`/`kMixS`
tables, `kNotchGainDb`'s meaning changed), `LevelBlend.h` (new `cleanFraction()` accessor), and
`PedalChain.h` (new `syncOdToneMix()`, called from both `applyParams()` and `applyFitParams()` —
the mix depends on inputs both set, in caller-dependent order, s124's two-setter trap). Rebuilt
**several times** during iteration (the shape-clamp attempt, the 40 dB saturation probe, the K-table
correction, each `pgrep`-checked first with no render in flight) and once more after reverting to
the final tables — `OfflineRender`'s binary postdates every edited header. **ctest 19/19** (~69 s).
✅ **Transcription certified TWICE, standalone impulse→DFT probe (no JUCE/WDF) against the Python
mirror (`od_tone_restore_fit.current_response`/`mix_shape`)**: 600 combinations of (grunt, drive,
cleanFrac, frequency), worst disagreement **5.0e-09 dB**, both before and after the final table edit.
⚠ **NO comprehensive_report/matrix run this session** — every acceptance number came from
`od_tone_restore_fit.py --geom`, which reads renders directly and is unaffected by the matrix cache.
So the matrix cache's staleness is **unchanged in kind** from s154 but the bill has **grown**: this
session's several rebuilds each re-armed it, so the next matrix run pays the full ~25 min (not more —
relinking again doesn't compound the cost, it just confirms the cache is cold).
⚠ Two pre-existing instrument defects fixed in passing (not DSP, not gated on): `do_matrix`'s
`--stage-off` flag was parsed but silently never applied (every quantitative table this session used
the explicit subtraction path instead, so nothing already reported was affected); and every
`current_response()` call site across the notch gates now passes the capture's own clean fraction
rather than an implicit default.

⚠⚠ **BUDGET ~25 MIN FOR THE NEXT MATRIX RUN** (owed since s152/s153/s154, RE-ARMED s156's several
rebuilds) — any relink moves the `(size, mtime_ns)` that `_cache_key` hashes, so warm entries go
unreachable. This is the documented price of compiling (`build.md`'s batching rule; s127's lesson,
repeated by s124/s144/s146/s156), a **speed** cost only, and nothing is corrupted. Arithmetic: the
CLOSED/REFUTED row + `docs/session-log.md` SESSION 142 §5.4 / 144. ⛔ Do NOT "fix" it by touching the
cache key — the key is right.

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
    question whether the listening test predates or postdates that fix. ⛔ **Was cited as "open work
    item 11" — a DEAD POINTER into a retired 90-session-old numbering scheme. Tracked for real now
    as item 11 in the numbered Open Work list above (task F, session 160).**
- **Two shipped bug fixes, pre-Phase-9 (2026-07-23), both in `src/PluginProcessor.{h,cpp}`** — the
  **bypass-engage click** (each channel stepped a throwaway *copy* of the smoothers, so the members'
  state never advanced) and the **knob-turn zipper, worst on DRIVE** (`applyParams()` runs once per
  block, so a fast sweep jumped the raw APVTS value uninterpolated; fixed with `SmoothedValue::skip`
  at knob-value level, ~20 ms). Full diagnosis: `docs/session-log.md`.
  ⚠ **Still open, and NOT covered by either fix:** switches (ATTACK/GRUNT/mid-freq/bypass/
  `dist_engage`) are unsmoothed — the harder glitch-free-crossfade problem (`circuit.md`,
  `TrebleAttack.h`).
