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

> Update this at the start/end of each session so progress doesn't rely on conversation history.
> **⚠ RESUME POINT = `docs/phase7-calibration-handover.md` (READ IT FIRST). Latest below.**
> **CURRENT (session 15, 2026-07-23): branch B LANDED, its §3j gate CONFIRMED, dsp-validator PASS on
> both the new JFET core AND the deferred clipK — THE JFET H3 PHASE PROBLEM (sessions 12-14) IS
> FIXED. Full joint fit STOPPED per protocol — a SEPARATE, pre-existing clipper-level issue blocks
> acceptance. NOTHING committed to git; branch is OPEN and needs the user for the next lever.**
> `jfetExpandBeta` — the new odd core `T(w)=w(1+c·w²)/(1+(w/L)²)^1.5`, `c=beta+1.5/L²`, small-signal
> `w+beta·w³+O(w^5)` (beta IS the cubic coefficient), bounded `±(beta·L³+1.5·L)`, **provably monotone
> for beta≥0 with NO parameter coupling** (a first for this file — every prior reshape needed a
> numeric-only scan; sympy-verified: `T'(w)=L³(L²+w²(3L²beta+2.5))/(...)`, sum of positive terms),
> elementary ADAA for ANY (beta,L). Replaces `jfetCeilK` entirely (that hardness knob is gone —
> proven the wrong lever). Fully plumbed: `JfetStage.h`/`FitParams.h`/`PedalChain.h`/
> `offline_render.cpp`/`JfetStageTest.cpp`, new gate `analysis/expandbeta_gate.py`. **ctest 16/16**
> (incl. `OSValidationTest` — session 14's anomaly does NOT recur at nominal beta=0.0).
> **The §3j gate CONFIRMED, cleanly inverting session 14's failure:** full-chain drive-min H3−H2
> rises MONOTONICALLY −57.3→−6.1 dB as beta sweeps 0→16 (crosses the capture's −23.2 at beta≈1.8, no
> interior null at ANY drive setting), and the isolated JFET-core H3 flips from ~180° ANTI-phase to
> IN-phase with the clipper (110 Hz 177°→2°, 1 kHz 171°→42°) — exactly the sign flip session 14
> proved a compressive shape could never produce. **dsp-validator (Opus, high) PASSED both shapes**
> (every closed-form claim sympy-verified exact, including re-auditing the even-bump's `2.598` bound
> for a repeat of the wrong-extremum bug — none found) and cleared clipK's session-11/12
> still-deferred sign-off in the same sitting.
> **Three fit attempts, all REJECTED at acceptance — but NOT because of the JFET.** (1) beta-only
> (clipK held at 2.0): beta=1.42 (expansive ✓), drive-min ψ3 err 14.2° (was ~160° off pre-branch-B),
> clipA0=20.1 (inside 20-30), no bound-resting param — but noon H3−H2 landed 6.7 dB short (the
> persistent session-10/11 "noon-specific" shortfall, previously untestable because the anti-phase
> JFET masked it). (2) A targeted probe confirmed clipK's discriminating signature RETURNS now that
> the JFET is in-phase (softening clipK unmasks noon, unlike session 12) — added it to the fit: noon
> error dropped to 3.6 dB and ψ3 err to 8.6°, but landed in a DEGENERATE corner (clipK pinned at its
> floor, clipSat collapsed to 1.58 V vs the ~7 V rail, `2·a·ceilNeg`=12.7, gm-scan not flat) —
> REJECTED. (3) Physically-constrained clipper bounds (clipSat≥1.5 V/side, clipK≥1.2): the optimiser
> just found a DIFFERENT unphysical knob (clipA0 dropped to 8.2, outside circuit.md's 20-30) to fake
> the same thing — REJECTED, noon still 4.6 dB short.
> **Localised (two diagnostic grids, not fits): the residual gap is a SEPARATE, pre-existing problem
> — NOT branch B.** At a FULLY physical clipper (A0 20-30, sat 3.15/3.85 V, clipK 1.0-2.0) noon
> caps out ~9-10 dB short REGARDLESS of clipper shape; sweeping `jfetGm` across its
> ALREADY-ESTABLISHED 0.09-0.15 mS band closes 2:30/max (max −3.2→+15.9 dB) but noon stays stuck at
> −18…−21 dB REGARDLESS of gm — a drive-POSITION-specific signature, not a uniform level error, so a
> NON-uniform level change (the DRIVE taper SHAPE) is the remaining lever. **KEY INSIGHT: VR3 is a
> C-TAPER (reverse-log) but `DriveStage.h` models it as a single POWER LAW `R=100k·(1-x)^2.5` — a
> C-taper is NOT a power law, and session 11 only ever pinned p=2.5 to a 2-POINT level match.** A
> new probe `analysis/drive_taper_shape.py` measured the real gain-vs-knob from the ladders: it has
> a BLEED confound at low/mid drive (base-OD fundamental carries the drive-independent clean bleed),
> but the ONE bleed-free step (2:30→max) shows the real pedal gains **+2.4 dB more at the top** than
> `(1-x)^2.5` — real evidence the taper shape is wrong. **NEXT (session 16), IN ORDER: (1) a
> BLEED-AWARE drive-taper measurement (subtract the drive-independent bleed) to get the clean shape
> at noon; (2) replace `(1-x)^p` with a proper C-taper curve in `DriveStage.h`; (3) re-run THIS
> session's branch-B fit (JFET core DONE — keep beta/jfetSat*/jfetCeil* + the phase-aware ψ3
> objective; only the clipper-input side changes). Do NOT re-attempt a joint clipK+clipSat+clipA0
> fit first — it re-finds the degenerate "lower the ceiling" trick. If a correct C-taper still
> doesn't close noon, look at the clipper INPUT coupling (GRUNT + R16).** Full detail: handover
> "SESSION 15" §3u.6. HELD: jfetGm 0.10 mS (0.09-0.15 band), levelTaperExp 2.25 — driveTaperExp is
> now ACTIVE, no longer held.
> ── prior session ──
> **CURRENT (session 14, 2026-07-23): the §3s ceiling-hardness reshape was IMPLEMENTED and its
> pre-registered §3j pivot gate FAILED — STOPPED per protocol. NO fit, NOTHING committed. Branch is
> OPEN and needs the user.** `jfetCeilK` algebraic-sigmoid ceiling `T(w)=w/(1+|w/L|^k)^(1/k)` (k=2
> anchor, exact ADAA `F_T=L·√(L²+w²)−L²`, midpoint-ADAA fallback for k≠2) is fully implemented in
> the WORKING TREE, uncommitted: `JfetStage.h` + `FitParams.h`/`PedalChain.h`/`offline_render.cpp`
> plumbing + `JfetStageTest.cpp`/`fit_nonlinear.py::min_slope` monotonicity updated for the power-law
> tail. **ctest 15/16** — the 1 fail is `OSValidationTest`'s 4×-vs-2× aliasing diff-gate at amp 0.2
> (the KNOWN clipper/decimator narrow-band anomaly relocated onto the probe amp by the shape change,
> at PLACEHOLDER nominal ceiling; 8× floor −40.5 clean, oversampling+delay-comp both pass — deferred
> to post-fit, NOT masked). **The pivot verdict** (`analysis/fit_logs/step5_ceilk_pivot.log`): as k
> rises, drive-min AND drive-noon H3−H2 fall the SAME direction through an anti-phase null, at BOTH
> the session-11 point and a proper-clipper point — hardness cannot make the capture's ramp
> (−23.2/−21.0/−10.6/+1.3/+1.0); the model is FLAT across min/9:30/noon at every k. **Diagnosis: an
> H3 PHASE/SIGN problem, not magnitude — the JFET's drive-min H3 must be IN-PHASE with the clipper's
> (they're anti-phase now). I first blamed the ~320/717 Hz notches, but `analysis/notch_scope.py`
> FALSIFIED that: in the ASSEMBLED/loaded chain both notches are only ≤2.6 dB (not the isolated
> −28 dB), too shallow to explain ~180° — so the anti-phase H3 is very likely REAL nonlinear
> structure and the leading fix is the JFET odd-term IN-PHASE H3 (branch B), NOT resolving the
> notch.** **▶ USER chose verify-then-B; VERIFICATION DONE (handover §3t.5): the anti-phase
> reproduces (ceil↔clip 178.8/166.0/178.7° at 110/220/1000), the CAPTURE matches the CLIPPER not the
> ceiling (1 kHz conclusive, cap↔clip 8°), and it is NOT a polarity bug (a global inversion cannot
> change a RELATIVE phase; per-stage fundamentals DC-step-verified). => the REAL JFET H3 is
> EXPANSIVE-signed (in-phase with the clipper); no compressive ceiling or hardness makes it.**
> **NEXT (session 15) = branch B: design an expansive-near-origin-then-BOUNDED odd JFET term (reuse
> jfetCeilK's sigmoid for the loud-input bound), §3j complex gate BEFORE fitting, phase-aware ψ3/ψ2
> fit, dsp-validator, accept, master taper + makeup, commit. KEY SIMPLIFIER: DRIVE is downstream of
> the JFET so the J201 sees a FIXED level — it only needs the right H3 at ONE operating point
> (H3−H2=−23.2, the drive-min capture). §3t.6 has the full plan.** Probes:
> `analysis/phase_harmonics.py`, `analysis/scratch_ceilk_clipk_probe.py`, `analysis/notch_scope.py`.
> HELD unchanged: driveTaperExp 2.5, jfetGm 0.10 mS, levelTaperExp 2.25.
> ── prior session ──
> **CURRENT (session 13, 2026-07-23): the two §3o measurements are IN — result LEANS STATIC.
> Analysis-only (no DSP code, no new captures). New tools `analysis/phase_harmonics.py`,
> `analysis/static_vs_dynamic.py`; logs `analysis/fit_logs/step5_phase_harmonics.log`,
> `..._static_vs_dynamic.log`. ctest untouched (16/16 — standalone analysis scripts only).**
> (1) **Step 1 — phase-aware harmonics: AMBIGUOUS (frequency-dependent).** ψn = φn − n·φ1
> shift-invariance is EXACT (self-test, incl. session-8's 26-sample lag). The model's ceiling-H3
> and clipper-H3 come out ~180° apart (coherent complex subtraction), re-deriving session-12's
> interference from PHASE. Verdict on the ceiling SIGN is frequency-dependent: the one clean tone
> (1 kHz, capSNR 47, notch-free) says the ceiling odd term is BACKWARDS (capture matches the
> clipper 8°, opposes the ceiling 161°), but 220/440 lean the other way and 220's H3 (660 Hz)
> sits on the mismodelled 717 Hz notch (KNOWN linear error). Mandate regardless: COMPLEX
> (phase-aware) fit targets.
> (2) **⚠ TRAP #1 (in the plan's own §3o step 1): "ceiling-only via high clipSat" is INVALID.**
> The D1/D2 clamp window TRACKS satLo (`Clipper.h`: clampHi = 9.6 − satLo), so clipSat ≳ 10
> FREEZES node W into a DC source and the residual output is just the harmonic-free clean BLEND
> bleed. You cannot linearise this clipper via sat. Used coherent complex subtraction of valid
> renders instead.
> (3) **Step 2 — static-vs-dynamic: NO DYNAMIC SIGNATURE → STATIC CONFIRMED (dense).** The
> confound-free DIFFERENTIAL `cap_slope − mdl_slope` (per frequency, same chain → Gpost/treble/
> clipper cancel) is ~0 at every tone. **The user then RECORDED a FULL DRIVE-SWEEP of dense ladders**
> (`analysis/gen_jfet_ladder.py` stimulus + `read_jfet_ladder.py`, captures
> `analysis/captures/jfet_ladder_drive-{min,0930,noon,1430,max}.wav`, gitignored, 110/220/440 Hz,
> −6…−60 dBFS): at drive-min, over the whole clean-JFET range (>30 dB) `cap−mdl` slope ~0,
> below-corner 110 Hz mean |dev| **0.03** (14 clean slopes), NOT anomalous vs above-corner 0.05 —
> thinness caveat GONE. At 0930/noon/1430/max the mean `|cap−mdl|` grows with drive (0.02→0.17→0.36)
> = the clipper/ceiling-interference error vs level/freq/drive, i.e. the reshape's TARGET data.
> (Reader tooling note: use `A.load`, NOT `captures.load_capture()`, on ladder captures — its
> rate-mislabel guard assumes a 1 kHz cal tone this stimulus lacks; and align on the sweep anchor
> before fixed-offset segment reads.)
> (4) **⚠ TRAP #2: raw A_eff-collapse (Gpre only) is CONFOUNDED** — the treble net + clipper
> after the JFET make effective drive frequency-dependent too, and the STATIC model shares them;
> raw non-collapse is not a dynamic signature. The differential-vs-static-model is the real test.
> (5) **Steps 1 & 2 are CONSISTENT: the static FAMILY is adequate, but the current ceiling
> ODD-TERM SHAPE (magnitude + likely SIGN) is wrong.** A static real nonlinearity's H3 is
> intrinsic 0/180° × downstream linear phase, so the capture being ~180° off at 1 kHz = a STATIC
> sign fix; step 1's cross-frequency inconsistency is linear-model (717 notch) error, not genuine
> frequency-dependence.
> **▶ NEXT — BRANCH DECIDED + RECIPE WRITTEN (handover §3s): reshape the JFET ceiling with its own
> HARDNESS param `jfetCeilK` (nominal 2), algebraic sigmoid `T(w)=w/(1+|w/L|^k)^(1/k)` replacing
> `L*tanh(w/L)` in `JfetStage.h::coreLimit` — EXACTLY parallel to the validated `clipK` reshape.**
> `T'(0)=1` (gm/linear untouched), bounded (still a ceiling), odd-per-side (even-bump zero-H3 kept);
> harder knee (higher k) cuts the drive-min ceiling-H3 excess AND unmasks the clipper ramp in one
> lever; ADAA anchor k=2 has elementary antiderivative `L*sqrt(L^2+w^2)-L^2`. **SEQUENCE (do in
> order, all in §3s):** (a) implement the shape in JfetStage.h + FitParams/PedalChain/offline_render
> plumbing; (b) **run `analysis/ceilk_pivot_check.py`** (stub written this session, detects the
> not-yet-implemented case) — the §3j gate: as k RISES, drive-min H3−H2 must FALL toward −23.2 AND
> noon RISE toward −10.6 *together*; if not, STOP; (c) add COMPLEX ψ3/ψ2 targets to
> `fit_nonlinear.py` (use `phase_harmonics.py`'s LS extractor on all 5 ladders + drive-sweep tones,
> down-weight 220's notch-corrupted H3); (d) dsp-validator (Opus, high) sign-off on JfetStage.h
> (T'(0)=1, numeric monotonicity, ADAA F'=T C1 seam, even-bump zero-H3, DC-step, k==2 fast path) —
> AND clear clipK's still-deferred dsp-validator pass in the same sitting; (e) accept only on
> `2*a*ceilNeg≈1` unconstrained + clipA0∈20-30 + no bound-resting param + gm-scan flat + small phase
> residual at 110/440; (f) then masterTaperExp (from existing master-* captures) + makeup, commit
> the whole set. HELD: driveTaperExp 2.5, jfetGm 0.10 mS, levelTaperExp 2.25. Do NOT take the
> coupled-Newton JFET rewrite. Full detail: handover "SESSION 13" §3p–3s + "✅ RECORDED + ANALYSED".
> ── prior history ──
> **CURRENT (session 12, 2026-07-23): the session-11 `clipK` fix WAS implemented and its own
> §3j discriminating check REJECTED the session-11 diagnosis — STOPPED at the gate, NO fit run,
> NOTHING committed. The real mechanism is ANTI-PHASE H3 INTERFERENCE between the JFET
> drain-current ceiling's drive-independent H3 and the clipper's H3.**
> (1) **Implemented (working tree, ctest 16/16, NOT committed):** `Clipper.h` `vtc()` per-side
> `tanh(u)` → algebraic sigmoid `u/(1+u^k)^(1/k)` with `kHardness = 2.0` nominal (ADAA anchor,
> antiderivative `sqrt(1+u^2)`, k==2 fast path), plumbed as `FitParams::clipK` →
> `PedalChain::setFitParams` → `--fit clipK=` in OfflineRender. `f_k'(0)=1` exactly, so a0 keeps
> its small-signal/GRUNT-corner meaning — FR/corner/polarity tests unchanged.
> (2) **Two honest test corrections found en route (keep regardless of clipK's fate):**
> `ClipperTest` Test 5's documented "max|W| = 1.1 V at 8 V drive" was an ARTIFACT of the atanh
> W-recovery saturating — ground truth (Newton-solve replica, clamps off) shows W hits ~8 V and
> the D1/D2 clamps DO engage ~50% of samples at that drive with EITHER VTC shape (test now
> asserts: clamps inert at the rail-limited realistic max ~3.5 V, and bounding at 8 V);
> `OSValidationTest`'s 4×-vs-2× diff gate widened 0.5 → 1.0 dB (the reshape IMPROVED both
> floors, −21.3/−21.2 → −22.1/−21.6, but 2× improved more — a strict improvement failed a
> diff-gate).
> (3) **§3j pivot check FAILED at BOTH the nominal and the session-11 fitted point**
> (`analysis/clipk_pivot_check.py`, logs `analysis/fit_logs/step4b_clipk_pivot*.log`): noon
> H3−H2 FALLS as k softens (−17.8 → −26.3 at the fitted point; capture wants −10.6) and 2:30
> explodes (+0.8 → +21.1; capture +1.3). Per protocol: STOP, no fit.
> (4) **Mechanism (log `step4b_clipk_interference.log`):** at noon the JFET ceiling's
> drive-independent H3 (`L*tanh(w/L)`, ~−49.8 re fund) dominates and is ~180° ANTI-PHASE to the
> clipper's H3 — softening k grows clipper H3 toward parity and the coherent sum CANCELS
> (predicted −57.2 vs measured −56.0 dB at k=1.25). Ceiling disabled (`cp=cn=1e6`): noon H3
> rises +31 dB monotonically as k drops — clipper-alone behaviour restored exactly. This also
> explains the model's FLAT H3−H2 across min/9:30/noon (−17.7/−17.7/−17.8) vs the capture's
> ramp (−23.2/−21.0/−10.6): the ceiling H3 floor is 5.4 dB too HIGH at min AND masks the
> clipper's ramp at noon.
> **▶ NEXT (AGREED with user 2026-07-23, handover §3o): measure FIRST, decide the path with
> data — no third shape-family guess.** The sessions-7–12 meta-pattern is amplitude-only fits
> killed by measurements the objective couldn't see; two measurements from EXISTING captures
> (no code, no new captures) decide everything: **(1) phase-aware harmonic analysis** of the
> drive-min tones via the shift-invariant relative phase `φn − n·φ1` (alignment-lag-immune) —
> does the real pedal's low-drive H3 phase OPPOSE the clipper's (ceiling too big) or MATCH it
> (ceiling BACKWARDS)? Then fold complex targets into `fit_nonlinear.py` so interference nulls
> become fitted, not hidden. **(2) static-vs-dynamic test** — C3's degeneration bypass corner
> is 219 Hz, IN the measurement band (every fit so far sat at 220 Hz, ON it): if drive-min
> H2-vs-level curves at different tone frequencies don't collapse onto one static curve, NO
> static W-H shaper of any family can fit. **Branch:** static holds + phase blames ceiling →
> reshape ceiling's odd term (or data-driven monotone-spline static map from the level ladder)
> fitted against COMPLEX targets with a §3j-style check first; static fails → give the JFET
> the clipper treatment (Q1/Q2 Shichman-Hodges + R6∥C3 companion INSIDE a per-sample Newton
> loop; phases emerge from topology; Idss/Vp physically bounded; DAFx-2024 paper in docs/refs)
> and skip further static families. Do NOT fit black-box shapers on the full drive sweep, do
> NOT capture anything new before the phase dimension of existing data is read. dsp-validator
> sign-off on the clipK vtc reshape still deferred — run before any commit that RELIES on it.
> Full detail: handover "SESSION 12" §3k–3o. ctest 16/16, committed 47c7e35.
> (1) **`driveTaperExp` validated against the matched-pair drive capture** (`analysis/
> drive_taper_validate.py`, `analysis/fit_logs/step4_drive_taper.log`) per dsp.md's "fit the taper
> SHAPE against a matched-pair capture" — session 10's floated 5.45 is REJECTED (it ran the
> model's noon-knob small-signal gain +8.5 dB hotter than the real pedal). The real value is
> **p = 2.5**, confirmed two ways: (a) BOTH interior knob points (9:30 +1.1 dB, noon +4.8 dB
> capture) match ONE `p` simultaneously (0.18 dB clean-taper error) — the two-point test dsp.md
> requires to rule out a wrong-shape false match; (b) frequency-flat — the same rise measured
> directly at 220 Hz agrees with the 1 kHz number to ~0.4 dB, so it isn't a frequency artefact.
> (2) **Re-ran the step-3 harmonic fit with `driveTaperExp` HELD at 2.5 (moved out of `FIT_KEYS`)
> — REJECTED.** Cost 47.3 → 289.0; `clipA0` pins at its physical ceiling of 30 and still can't
> reach the harmonic targets (`analysis/fit_logs/step4_joint_refit.log`). Failure is
> **noon-specific**: capture H3−H2 −10.6 dB vs model −18.6 dB (min/9:30 sit at a roughly constant
> ~5–6 dB offset instead; 2:30/max already fit). Ruled out as fixes: the whole anchored `jfetGm`
> band 0.09–0.15 mS (gm-scan doesn't close the noon gap, sometimes widens it); `RailClamp` on the
> DRIVE stage (`--fit railEnabled=1` renders BIT-IDENTICAL to disabled at this operating point —
> confirmed inert, signal never nears ±3.3 V at gm=0.10 mS).
> (3) **Root cause (dsp-validator, Opus, full re-derivation + its own probes): `Clipper.h`'s
> topology/Newton-solve/GRUNT-reduction are ALL faithful and correct — this is NOT a code bug in
> that sense.** The Newton solve is provably strictly monotone (`F'(W)` is a sum of strictly
> negative terms) → globally convergent, no amplitude-dependent convergence artefact (verified by
> probe: smooth monotone H1/H2/H3 across 42 dB of input swing). D1/D2 clamps confirmed inert
> in-band. **The actual cause is `vtc()`'s SHAPE** (`Clipper.h:227-232`) — a single per-side
> `tanh(a0*w/sat)` couples small-signal gain and knee-hardness into ONE parameter (`a0`), so its
> H3 stays buried until a late, sharp knee (a 20 dB jump packed into ~1 octave of drive, right
> where "noon" sits) instead of the capture's smooth ramp — and raising `clipA0` moves gain AND
> hardness together, which is why the fit pins it at 30 and still falls short. Full evidence table
> + diagnosis in `docs/phase7-calibration-handover.md` "SESSION 11 — CLIPPER VTC SHAPE" (§3i).
> **▶ NEXT (agreed with user, NOT implemented — planning only): add a hardness parameter `k` to
> `vtc()`** — replace `tanh(u)` with the algebraic sigmoid `u/(1+u^k)^(1/k)`, keeping `a0`/
> `satLo`/`satHi` unchanged. **Use `k=2` as the default/anchor — `f_2(u)=u/sqrt(1+u^2)` has the
> elementary antiderivative `sqrt(1+u^2)`, preserving the stage's required closed-form ADAA**
> (`k=1` also works: `u−ln(1+u)`); do not ship an arbitrary `k` without checking it keeps a closed
> form (same trap class as the JfetStage sech→tanh reshape). Needs the same
> dsp-validator-sign-off rigor as that reshape (odd-part identity if relevant, ADAA-preserving
> antiderivative, monotonicity) before landing in `Clipper.h` — this is a small MODEL change, not
> a constants-only refit. Discriminating check before re-committing: sweep `k` through the FULL
> chain and confirm the "pivot" signature (min/max stay put, noon rises as `k` drops) survives
> past the clipper-alone probe. Then re-run `fit_nonlinear.py` with `k` added to `FIT_KEYS`,
> `driveTaperExp` still held at 2.5, re-check all step-3 acceptance checks, THEN validate
> `masterTaperExp` + makeup, THEN commit the whole set together. §3j has the full plan.
> Full detail in `docs/phase7-calibration-handover.md`. ctest untouched (analysis/docs only this
> session — no DSP code changed yet).
> ── prior history ──
> **session 10, 2026-07-23: J201 PLAN step 3 (FIX OBJECTIVE + FIT SHAPER) ✅ DONE — and
> it WORKED (at the time). SUPERSEDED by session 11 above — the fitted set is now rejected.** `analysis/fit_nonlinear.py` rewritten to score
> **harmonic-TO-HARMONIC ratios `Hn − H2` (n=3,4,5)** (every output harmonic is `alpha·OD_n` → the
> ratio cancels `alpha` EXACTLY, bleed/makeup/taper-immune); `jfetGm` HELD 0.10 mS, `levelTaperExp`
> 2.25, ro/rq2 nominal; H2-re-fund + THD dropped. **Result (cost 5154→47.3,
> `analysis/fit_logs/step3_harmonic_ratio.log`): clipA0 = 24.1 (inside circuit.md's 20–30, UNPINNED
> — every prior run pinned it at 3), `2·a·ceilNeg` = 0.84 ≈ the square-law identity 1.0
> UNCONSTRAINED, `a` = 0.91 single-digit, NO param resting on a bound.** All three named acceptance
> checks PASS; the shaper SHAPE is vindicated (no reshape). **Two coupling caveats → commit the whole
> SET jointly in step 4, NOT now:** (1) `driveTaperExp` landed at **5.45** (its old [0.4,3.0] box
> PINNED it; widening to 8.0 found a robust interior min, cost 334→47) — a STEP-4 taper param the
> shaper/clipper are coupled to (a 1.78→0.91, clipA0 28.6→24.1 as it freed), so validate it against a
> matched-pair drive capture first per dsp.md. (2) The gm-sensitivity table is FLAT at low drive
> (bleed confound GONE, as designed) but swings at HIGH drive = real clipper physics (gm drives a
> hard-clipping stage), so clipSat/driveTaperExp inherit gm's ±0.02 mS. **clipA0 does NOT explain the
> step-2 LF excess** (base captures are GRUNT=cut, HP corner ~1.7 kHz ≫ 82–110 Hz; clipA0 24 vs 25
> moves LF only +0.19 dB, wrong way) — LF excess stays a front-end lead. Full data: handover
> "✅ STEP 3 DONE". ctest untouched (analysis/docs only this session).
> **▶ NEXT = step 4: validate `driveTaperExp` vs a matched-pair drive capture, fit `masterTaperExp`
> + makeup, re-check gm/clipA0 jointly, THEN commit the step-3 SET (s,a,ceilPos,ceilNeg,clipA0,
> clipSatLo/Hi,driveTaperExp) together. NOT started.**
> ── prior history ──
> Phase 7 CALIBRATION PROPER — step 1 ✅; OD-path loading blocker ✅ RESOLVED
> (session 3); J201 boundary params ✅ FITTED (session 4, 2026-07-22): `jfetGm ≈ 0.09 mS`,
> shape error 7.53 → 1.56 dB, corroborated by an independent level check (+12.1 → −1.7 dB);
> `jfetRo`/`jfetRq2` proved NOT identifiable (cost flat to ≤0.01 dB over 16×) → held nominal.
> ctest 16/16 ✅ (session 4 touched analysis/docs only).
> ⚠ RESUME POINT = `docs/phase7-calibration-handover.md` (READ IT FIRST).
> **J201 DRAIN-CURRENT CEILING ✅ ADDED (2026-07-22, session 5) and step 2 RE-FIT #2 RUN.
> The ceiling was the right diagnosis; the fit is still rejected; THE BINDING CONSTRAINT
> HAS MOVED TO THE CLIPPER — that is the next suspect, not the J201.**
> Code: `JfetStage.h` gained an asymmetric per-side soft limit on the drain current,
> `T(w) = L*tanh(w/L)` with `L = kCeilPos` (load-line side, 1.0) / `kCeilNeg` (cutoff side,
> 0.5), gate-volt equivalent (×gm → amps); `kCeilOff = 1e6` disables a side EXACTLY.
> `FitParams::jfetCeilPos/jfetCeilNeg` + the `--fit` map + `PedalChain` plumbing; new
> `JfetStageTest` Test 6 (bounded/asymmetric/monotone/`F'==g`/ADAA-zero-H3/off-is-exact);
> `waveshape()`/`waveshapeAD()` are now PUBLIC so tests probe the SHIPPED map.
> **The even bump ALSO changed shape — `a*s^2*(1-sech(w/s))` → `(a*s^2/2)*tanh^2(w/s)` —
> and this is load-bearing, not cosmetic:** its slope tail now decays at the same
> `exp(-2|w|/s)` rate as the ceiling's `sech^2`, so the monotone region is `ceilNeg > s`
> instead of `> 2s`. Same leading term `a*w^2/2`, still exactly even (zero H3 from the
> bump), elementary antiderivative (the Gudermannian is gone). `kSatPos` 0.5 → **0.3** so
> the nominal set sits INSIDE the feasible region rather than on its edge.
> **⚠ THE `|a|*s` BOUND MOVED AGAIN — 2.598 is now CORRECT** (`max|tanh*sech^2| =
> 2/(3√3)`), and the "corrected to 2.0 / do not write 2.598" note from earlier the same
> day applied ONLY to the sech bump. Both handover mentions are marked VOID. With a finite
> ceiling NEITHER closed form is sufficient — it couples `s`, `a` and `ceilNeg` (as tight
> as `|a|*s < 1` when `ceilNeg = s`), so `fit_nonlinear.py::monotonic` and the test both
> scan the slope NUMERICALLY. **Lesson: derive the bound from the extremum of the shape
> in the file; never carry a numeral across a reshape — the same numeral has been both
> wrong and right within one day.**
> **Fit result (`analysis/fit_logs/step2_ceiling.log`), cost 6910 → 428.6 (prev best 677):
> H2 growth 21.9 → 10.1 dB (capture 6.0), `clipA0` 3.017-pinned → 17.2 free, `|a|*s`
> 1.9997-pinned → 1.077 free, H3 undisturbed.** Still rejected: `clipSatLo` rests on its
> 0.4 floor, `clipSatLo+Hi = 0.80 V` vs the ~7 V R19-dropped rail (WORSE than the last
> run), `driveTaperExp` 2.9938 against a 3.0 ceiling, `ceilNeg/s = 1.01` on the
> monotonicity boundary, and `jfetGm` 0.0274 mS vs the shape fit's 0.090 (was 6.1× above,
> now 3.3× below — the two objectives now bracket it). Every one of those is a "make the
> clipper see less" lever at its limit → something upstream is STILL too hot.
> **RAILS ELIMINATED (session 6, 2026-07-22) — they were suspect #1 and they are NOT it.**
> Enabling them is worth −0.1% at nominal and is EXACTLY inert at the fitted point (cost
> 428.6 → 428.6): `jfetGm` is low enough there that nothing reaches ±3.3 V. Verified
> plumbed (it does move the cost at nominal), so the null is by operating point, not
> mis-wiring. **A REAL BUG was found doing it (`926c0cc`): `RailClamp` uses `railNeg` as a
> MAGNITUDE but `FitParams` shipped `-3.3`, so an ENABLED clamp returned a constant +3.3 V
> for every sample below +2.95 V — it emitted DC, not audio.** Invisible since Phase 4
> because rails default off and **no test exercises the enabled path** (that gap is the
> root cause and is still open — a `RailClampTest` is still missing).
> **✅✅ SESSION 7 (2026-07-23) — THE EVEN-HARMONIC LADDER WAS AN ARTEFACT. NO CODE
> CHANGED; DO NOT RESHAPE THE SHAPER.** The blocker is the FIT OBJECTIVE.
> `fit_nonlinear.py`'s premise — "harmonic RATIOS are level-independent, so this is
> valid before makeup" — is **FALSE in this chain**. `LevelBlend::process()` at
> `B >= 1.0` returns `vw`, and `vw` still contains `cleanIn` (BLEND's 100k track runs
> pin1-clean ↔ pin3-LEVEL-wiper, so at full-CW OD the clean source still feeds the node
> through 100k against the wiper's ~23.3k Thevenin): at LEVEL=noon the mix is
> `0.3009*od + 0.1892*clean`, i.e. clean only **4.0 dB** below OD. The clean tap has NO
> harmonics, so it inflates H1 and suppresses every measured harmonic by however far the
> OD path sits below the clean tap — **+20.9 dB of dilution at the fitted
> `jfetGm = 0.0274 mS`**, +12.9 at 0.090, +5.9 at nominal 0.69. So the fitter bought
> harmonic score with LEVEL: it drove gm 25× below nominal, then cranked `a` to claw H2
> back, hit the monotonicity constraint, and the bump's own saturation manufactured the
> H4. Every session-6 symptom is downstream of that one confound.
> **The shipped `(a*s^2/2)*tanh^2(w/s)` shape is FINE**: rendered drive-min at `s=0.3`
> with NOMINAL ceilings/clipper, `a = 4` gives H2 **−35.5** dB (capture −36.0) at
> gm 0.69 mS, and **−36.6** at gm 0.090 mS — both with `a*A < 1` and `|a|*s < 2.598`,
> and H4 4–9 dB BELOW target (safe direction; the clipper supplies the balance).
> **The recommended reshape `g(w) = T(w) + (a/2)w^2` MUST NOT BE BUILT** — as written it
> is unbounded AND non-monotone (slope `1 + a*w` < 0 for `w < -1/a`); a correct monotone
> variant (`ln(cosh(a*w))/a`) buys only ~2 dB, and a hard-cutoff square law scores only
> by degenerating into a half-wave rectifier (H3 −14 dB). **Keep this general bound:**
> for ANY monotone map with a clean quadratic even part, `H2/H1 = a*A/4` and
> monotonicity needs `a*A <= 1`, so `H2/H1 <= 1/4 = −12.04 dB` scale-invariantly — real,
> but nowhere near binding once the bleed is accounted for.
> **⚠ AND THE SHAPE FIT'S `jfetGm` = 0.090 mS IS CONTAMINATED BY THE SAME TERM — it is
> NOT a safe anchor** (this supersedes an earlier session-7 note that said the gm
> disagreement was "resolved in favour of the shape fit"). At 0.090 mS the drive-min
> render is `0.3009*0.0321 = 0.0097` OD vs `0.1892*0.1733 = 0.0328` clean — the
> "OD-path shape" `fit_jfet_boundary.py` matched is **~77% CLEAN by amplitude**, and its
> gm sensitivity comes from the OD/clean MIX RATIO moving, not the OD path's shape. Its
> absolute-level cross-check is contaminated too (total output FLOORS on the clean bleed
> as gm falls, so level under-responds and the fit must go lower still).
> **So all three gm estimates — 0.551 / 0.090 / 0.0274 mS — are really measurements of
> the OD/clean MIX RATIO and inherit any error in the BLEND model.**
> **✅ PLAN STEP 1 (THE MIXER) IS DONE — session 8, 2026-07-23. `analysis/mixer_law.py`,
> log `analysis/fit_logs/mixer_law_session8.log`. NOTHING COMMITTED TO THE DSP.**
> (1) **Topology VERIFIED at 600-dpi pixel zoom** — LEVEL pin3=IC4_A/pin1=VD/wiper→BLEND
> pin3; BLEND pin1=clean straight off IC1_A, wiper→IC5_A(+) unloaded; BOTH long rails
> scanned pixel-by-pixel end to end: bare wire, no series R, no junction dot, no shunt.
> `LevelBlend.h` is FAITHFUL — the bleed is the drawn circuit, not a model bug.
> (2) **The law is confirmed**: BLEND is linear-taper so every harmonic must be affine in
> the knob with ZERO free shape params — measured residual/|G| = **0.016 (H1) / 0.040
> (H2)** at 220 Hz over 5 points. (H3/H4 degrade only because they sit 20–40 dB lower.)
> (3) **⚠ A PLAN PREMISE WAS WRONG: the LEVEL sweep is NOT an independent route.** With
> the wiper unloaded, `alpha(L)=L/(1+L(1-L))`, `beta(L)=L(1-L)/(1+L(1-L))`, so
> `beta/alpha = (1-L)` EXACTLY — LEVEL moves the clean bleed too. That makes it a
> SHARPER test (no free param left but the taper), not a useless one.
> (4) **THE LEVEL TAPER: p ≈ 2.25, not the shipped 1.43** → `L(noon)` 0.371 → **0.210**.
> Measured BLEED-FREE (harmonics carry no clean, so `|Hn(L)|/|Hn(max)|` IS `alpha(L)`;
> invert it for L) over **36 quasi-independent estimates** (3 tones × 4 harmonics × 3
> knobs, ALL AGREE — mean 2.222, median 2.253, sd 0.359). Commit it in step 4, jointly.
> (5) **HEADLINE — the bleed is REAL and BIGGER than modelled, confirmed by TWO
> independent routes that now agree.** At BLEND max-OD / LEVEL noon / DRIVE noon the
> clean-vs-OD amplitude ratio is **−1.0 dB (220 Hz) / −2.3 dB (110 Hz)** by the
> well-conditioned 5-point BLEND route, and the 4-point LEVEL route agrees to within
> 1.4–3.9 dB at every tone — i.e. roughly HALF the "100 % OD" output is undistorted
> clean. The corrected taper makes it WORSE (smaller L → bigger `1-L`). **The recorded
> prediction resolved in favour of "the bleed MATCHES", so `jfetGm ≈ 0.090 mS` is NOT
> obviously a bleed artefact** — the confound that killed three step-2 fits is confirmed
> real, and step 3's harmonic-TO-harmonic objective is REQUIRED.
> ⚠ Scope: the `(1-L)` law and the taper are drive-independent; `CLEAN_1/OD_1` is a
> DRIVE-NOON number — the J201 re-anchor needs `OD_1` at DRIVE-MIN.
> (6) **TWO BAD TAKES OF `level-1430_base-od.wav`, BOTH FOUND AND FIXED BY THE USER —
> both confirmed fixed by the DATA CONVERGING, not just by the explanation being
> plausible.** Round 1: odd-dominant spectrum (H3 −45.4/H5 −52.4 vs H2 −59.9/H4 −83.8)
> where every other take is even-dominant; a passive divider cannot make odd harmonics;
> its own `gain-n12` twin was harmonic-free (61 dB less H3 for a 9 dB level drop) —
> re-captured, fixed. Round 2: the round-1 fix introduced a NEW anomaly (implied taper
> p ≈ 4.4–6.2 at knob=0.75 vs 0.25/0.50's 2.0–2.5) that turned out to be BLEND left at
> noon instead of the required max-OD for that one file — re-captured with BLEND
> confirmed at max, and the anomaly resolved: **36/36 tone×harmonic×knob estimates now
> agree under one exponent, where 12/36 disagreed sharply before.** `level-0700` stays
> excluded on principle (L=0 null). Also: 440 Hz is the least trustworthy tone (its
> H2 = 880 Hz sits near the IC2_B bridged-T notch, 12 dB below H3) — prefer 110/220, or
> pool across harmonics rather than trusting H2 alone at 440.
> (7) **Two traps not to re-trip:** never estimate a noise floor by projecting at
> half-harmonic frequencies (that measures the WINDOW's sidelobe rejection, ~−170 dB, not
> the capture — the first version of the script reported 100+ dB SNR on buried harmonics);
> and draw conclusions from ratios WITHIN one capture (alignment lags across this set span
> 0–26 samples = up to 43° of phase error at 220 Hz).
>
> **▶ NEXT — THE J201 PLAN, STEPS 2-4 (agreed with the user 2026-07-23; full rationale in
> `docs/phase7-calibration-handover.md` "THE PATH FORWARD FOR THE J201"). Step 1 is DONE
> (above) and is what makes 2 and 3 falsifiable — do not run them without its result:**
> **(1) SETTLE THE MIXER FIRST** — needs no new captures. The clean tap is linear and
> harmonic-free and everything post-BLEND is linear, so at the output
> `fundamental = alpha(b)*OD_1 + beta(b)*CLEAN_1` (contaminated) but
> `H2,H3,H4 = alpha(b)*OD_n` (**bleed-free**). So absolute H2 vs blend measures
> `alpha(b)` directly, and the fundamental then gives `beta(b)`. Use the 5 BLEND points
> (`blend-0700/0930/1200/1430` + `ref-od`) AND, as an INDEPENDENT second route, the 5
> LEVEL points (`level-0700/0930/1430/1700` + `ref-od`, since LEVEL moves OD only) —
> they must agree. In parallel run `schematic-checker` on BLEND's pin1/pin3/wiper
> mapping: `LevelBlend`'s arithmetic is self-consistent with the topology circuit.md
> states, so a capture disagreement means the TOPOLOGY is wrong.
> **(2) RE-ANCHOR `jfetGm`** from the corrected OD-vs-clean ratio (bleed-free by
> construction), then re-run the drive-min shape fit with the fixed mixer. Prediction to
> score: if the real bleed is much SMALLER than 4 dB, gm was pushed ~7× low to cancel a
> spurious clean floor and the "0.090 is 2× below the J201 spread's low corner"
> awkwardness resolves itself; if the bleed MATCHES, 0.090 mS survives.
> **(3) FIX THE OBJECTIVE — use harmonic-TO-HARMONIC ratios (H3/H2, H4/H2, H5/H2)**:
> `alpha` cancels EXACTLY, so they are immune to the bleed AND to makeup/`levelTaperExp`/
> `masterTaperExp` — genuinely level-independent as the old objective only claimed to be.
> Hold gm from (2), then fit `s`, `a`, ceilings, `clipA0`, `clipSat`. Expect `a` in
> single digits (a≈4 at s=0.3 already lands H2 within 0.5 dB), not the 5.5–20 of the
> rejected runs.
> **(4) ACCEPT only on corroboration the objective could not see:** the deliberately
> unconstrained square-law identity `2*a*jfetCeilNeg = 1`, absolute OD-vs-clean level,
> `clipA0` inside circuit.md's 20–30, and no param resting on a bound.
> **Localisation technique to re-use:** `PedalChain::runInputBuffer()/runOdSample()/
> processPostBlend()` are PUBLIC, so a console probe can split the chain and measure
> H2/H1 per boundary — that is what separated "8 dB lost in the OD region" from "18.4 dB
> lost after BLEND". Cross-checks: JfetStage in isolation at the chain's own conditions
> (384 kHz, ADAA on) gives exactly `H2 = a*A/4`; a 220+440 two-tone through the whole
> chain gives 440/220 = **+1.71 dB** (so the linear path does NOT eat the harmonic —
> the loss had to be H1 dilution); and the `s`-sweep KNEE independently measures the
> shaper's drive (it depends only on A/s), confirming vgs = 126 mV.
> **The `jfetGm` "over-determination disagreement" is RESOLVED in favour of the shape
> fit** — the harmonic objective's gm was measuring the bleed, not the device. Stop
> treating 0.551/0.0274 as bracketing 0.090.
>
> **~~▶ NEXT — THE EVEN-HARMONIC LADDER, not the clipper and not level.~~ SUPERSEDED —
> see above; measurements reproduce, diagnosis was wrong.** DRIVE sits AFTER
> the JFET/treble net, so the J201 sees the same signal at every drive setting → its
> harmonics are CONSTANT across the sweep (which is why the capture's H2 moves only 6 dB
> while H3 moves 30). So drive-min H2 is a near-direct J201 measurement, and the model is
> 7.3 dB short. It IS reachable — `s=0.1, a=20, ceilNeg=0.2` gives drive-min −37.4/−58.9/
> −36.7 vs the capture's −36.0/−59.2/−36.0 — but the full cost goes 428.6 → 1279.5 and
> **920 of that is three H4 terms**. Measured H2−H4 separation: capture **33.9 dB**, model
> at a=20 **8.9 dB**. A TRUE quadratic makes H2 and nothing else (a real JFET's
> `Id ∝ (Vgs−Vt)²`); the shipped `(a*s²/2)*tanh²(w/s)` is quadratic only for `|w| ≪ s` and
> **its own saturation manufactures the H4** — so killing H4 wants large `s`, making H2
> wants large `a`, and monotonicity caps `|a|*s`. Structurally the same finding as the
> original tanh→square-law reshape, one harmonic up. ~~**Recommended (NOT done, needs
> sign-off): make the even term a true quadratic and let the already-fitted ceiling bound
> it.**~~ **← REJECTED 2026-07-23 (session 7): unbounded + non-monotone as written, and
> the premise was an artefact. See the session-7 block above.**
> NO CONSTANTS COMMITTED; the ceilings ship at their physically-argued nominals.
> **THE BLOCKER IS FIXED — it was structural, not a fit problem.** `JfetStage` was a VOLTAGE
> stage feeding `TrebleAttack` as an IDEAL source. For a degenerated common-source stage
> `Gm(s)=gm/k(s)` RISES while `Rout(s)=ro*k(s)` FALLS, so open-circuit gain `Gm*Rout = gm*ro`
> is FLAT: **C3's "+10.3 dB HF lift" is not a gain at all**, it is a falling output impedance
> that only becomes a lift once loaded — and the treble ladder's input Z falls over the same
> band (35k@200Hz → 6.5k@2kHz), cancelling most of it. The old model applied the shelf
> unconditionally AND drove the ladder from 0 Ω: the boost was counted TWICE.
> **Fix (all in tree):** `JfetStage` now outputs the drain **Norton current** + `getSourceZ()`;
> `TrebleAttack` grew nodes G and H (N=5→7) and stamps `Zout(s)=[ro+Rp||Cp]||Rq2` (= `ro*k(s)||Rq2`,
> `Rp=ro*gm*R6`, `Rp*Cp=R6*C3`), so its transfer is a **transimpedance**. `FitParams`: `jfetG0`
> and `jfetGmR6` **REMOVED** (not renamed — `gmR6` was never independent of `gm`, R6 is a fixed
> 3k3) → **`jfetGm` / `jfetRo` / `jfetRq2`**; a stale `--fit jfetG0=` now fails loudly. Oracle:
> `treble_attack_tf(..., Zs=)`, `jfet_source_z()`, `treble_attack_transimpedance()`;
> `jfet_stage_lin_tf` returns siemens; `Zs=None` still reproduces the old numbers.
> **Result — OD-path shape error vs capture (mean-removed RMS, 50 Hz–8 kHz, drive-min):
> 14.2 dB → 6.9 dB at nominal → 1.4 dB on a coarse gm scan.** Also the model is now
> LEVEL-INDEPENDENT like the pedal (it used to swing 30 dB across sweep levels).
> **NEXT: fit `jfetGm`/`jfetRo`/`jfetRq2` properly** (the coarse scan sat at its grid EDGE on
> all three — extend it; `gm=0.06 mS` is ~11× below datasheet, justify or bound it), **update
> `FIT_KEYS`** (drop `jfetG0`, add the three; the old "add `jfetGmR6`" note is VOID — that param
> is gone), then RE-RUN the step-2 nonlinear fit on the corrected chain, then steps 3–6.
> **Key measurement technique to re-use (cheap, no new captures):** the capture's OD-path shape
> is IDENTICAL across the −36/−18 dBFS sweeps (±0.15 dB) → the pedal is LINEAR at drive-min, so
> that shape is a hard small-signal target. Comparing a model's level-dependence to the pedal's
> is the fastest way to separate "wrong filter" from "wrong operating point". Cross-checked
> against the harmonic-immune fixed-tone segments (agree ~1 dB), so the swept-sine FR is sound
> here — though the GRUNT cut matched pair may still be contaminated (still open).
> **⚠ TWO OPEN ITEMS (both in the handover doc):** (1) the treble ladder's ~322 Hz two-path
> cancellation notch is −28 dB in BOTH schematics but −3.4 dB in the capture; topology
> re-verified at pixel zoom, and Monte Carlo (400 draws, ±20% caps/±5% R) never gets shallower
> than −23 dB, so tolerance cannot explain it — PARKED by user decision, revisit after the gm/ro
> fit (it is much shallower in the assembled chain, ~−5.6 dB, than in isolation). (2) an 8×
> oversampling anomaly at one clipper drive where 8× is WORSE than 2× — **pre-existing, NOT
> caused by the restructure** (the old build has it too, at a different input amp, because it ran
> ~22 dB hotter; both break at the same clipper drive). The OD region itself is clean at 384 kHz
> and improves with rate; `OSValidationTest` now gates at amp 0.2 and prints the whole amp×order
> sweep so the bad zone stays visible.
> Step-2 finding: the J201 waveshaper was reshaped tanh → SQUARE-LAW (JfetStage.h) because tanh
> structurally can't make the real pedal's pure-even low-drive H2. The reshape is CONFIRMED (fit cost
> 3374.8 → 149.4, drive-min finally even-dominant; dsp-validator verified the math exactly — odd part
> ≡ w to 3.6e-15, H3 at the FP floor, exact antiderivative, ADAA preserves zero-H3). But the fitted
> VALUES are rejected for THREE independent reasons: physically implausible (`clipA0` 7.3 vs 20–30;
> clipper rail 1.79 V vs ~7 V); NOT a bounds artefact and NOT a flat degeneracy (scaling test has a
> real minimum) yet not contradictable by any capture (the GRUNT A0 cross-check is inert); and the
> run-2 point is a **non-monotone FOLD-BACK** (|a|·s = 2.456). **ORDER AMENDED with the user
> 2026-07-22: fix the loading/level blocker FIRST, then re-fit step 2, then steps 3–6.** Otherwise
> `docs/calibration-and-gain-staging.md` sets the fixed ORDER.
> **⚠ BUG FIXED 2026-07-22:** the shaper's monotonicity bound was documented as `|a|·s < 2.598` —
> that is `1/max(sech²·tanh)`, the WRONG extremum. `max(sech·tanh) = 1/2`, so the bound is
> **`|a|·s < 2`**. Corrected in `JfetStage.h` + `JfetStageTest.cpp`, and `fit_nonlinear.py` now has an
> explicit `monotonic()` feasibility gate (a PRODUCT constraint, which box bounds cannot express).
> **⚠ Two more dsp-validator carry-forwards:** (1) because the shaper's odd part is exactly linear,
> ADAA1 degenerates to a 2-point average over the WHOLE linear region → −2.0 dB @10 kHz at OS=1×
> (negligible at the 4× default) — fold into the Phase-8 low-OS shelf, consider gating ADAA off at
> order 0. (2) Do NOT fit `clipA0` from the GRUNT **cut** corner — C14's 2.19 kHz pole contaminates
> it and biases A0 low by ~2×; use flat/boost only.
> Also resolved this session: **GRUNT position→cap map VERIFIED against capture** (see below).
> **Step 1 result (see `src/dsp/GainStaging.h` + memory `phase7-kinputref-anchor`):** kInputRef
> stays **0.87 V/FS**, now ANCHORED (not nominal). `bypass.wav` is unity round-trip (−0.012 dB), so
> the capture domain == DAW domain 1:1. K is DEGENERATE with the clip ceiling under audio-only
> captures (proven: ref-clean DIST-off render is −3.894 dB under the capture at every level step
> −36..−3 dBFS, std=0.000 → K cancels in the linear path), so K is SET to the test-signal design
> level (0.87), and the clip ceiling (step 2) is fit relative to it — user decision 2026-07-22.
> ⚠ Also found: the clean deficit is Master-taper-dependent (real round-trip −19.6/−8.2/+0.95/
> +10.7/+12.3 dB across master 0/¼/½/¾/max), so fit `masterTaperExp` (step 4) BEFORE makeup (step 5).
> **`OfflineRender` ✅ DONE (the ex-blocker):** `analysis/offline_render.cpp` + CMake target
> `OfflineRender` (`juce_add_console_app`; juce_audio_formats + juce_dsp). Mirrors
> `PluginProcessor::processBlock` step for step — **if that changes, change this too.** Takes
> **knob-space** pots and applies `readParams()`'s `1-x` EQ inversion internally; renders
> UNCOMPENSATED (analyze.py::align() removes the lag — don't double-compensate); seeds every
> smoother with `setCurrentAndTargetValue()`; writes 32-bit FLOAT WAV; `--fit name=value` sets any
> FitParams field and `--print-fit` dumps what a render actually used. Positional `<in> <out>` is
> supported because the existing analysis/ orchestrators call it that way. New
> **`src/dsp/GainStaging.h`** holds `kInputRefNominal`/`kOutputMakeupNominal` so the plugin and the
> renderer can't diverge — committing a fitted `kInputRef` is a ONE-LINE edit there.
> `PedalDSP` gained `setFitParams()`/`getFitParams()` passthroughs.
> **`captures.py::render_args()` ✅ DONE** (all 55 filenames map; `bypass.wav` special-cased), and
> **`analysis/render_smoke_check.py`** PROVES the CLI→DSP mapping rather than assuming it: EQ knob
> direction monotonic CW=boost on all 4 bands (the check that catches a missing inversion), all 6
> mid-freq switch positions peak at their labelled centre, bypass = input delayed by the reported
> latency, and `align()` recovers exactly the reported 64-sample OS latency. All PASS; **ctest stays
> 16/16**; it is a tool, not a ctest gate — re-run it after any `processBlock`/`readParams()`/APVTS-
> order/CLI change. FYI the nominal ref-clean render sits ~5.3 dB below the capture (−37.47 vs
> −32.18 dB RMS on `sweep_clean`) — EXPECTED with un-anchored constants; decompose per
> `validation-and-capture.md` §4 before changing anything.
>
> **Pre-work history (2026-07-22):**
> Capture session ✅ DONE: 55 files in `analysis/captures/` (gitignored — back them up, they are NOT
> in the repo), 51/51 matrix filenames parse, disk↔matrix an exact set match. Mid-session the
> interface's own input headroom clipped 14 MASTER/EQ-boost-max takes (all pinned at peak 0.98850) →
> gain dropped −12 dB, those 14 re-captured, new `gain-n12` filename token + `gain_correction_db()`
> measuring the delta from the **ref-CLEAN** anchor pair (−12.071 dB), NOT ref-OD (the CD4049's
> compression made the same nominal −12 read as −2.857 dB there). Commit `ff5fc5f`.
> **`FitParams` ✅ DONE (`697339f`, ctest 16/16):** `src/dsp/FitParams.h` + `PedalChain::setFitParams()`
> make every capture-fit constant runtime-settable (was `static constexpr` → a rebuild per candidate,
> hopeless for a 3-D search like clipA0×satLo×satHi). Nothing re-tuned — each stage keeps its `kXxx`
> constexpr as the nominal and initialises the member from it. `kInputRef`/`kOutputMakeup` are
> deliberately NOT in FitParams (DAW-domain; calibration §1 needs kInputRef to cancel in the linear path).
> Python on this machine: **`/opt/homebrew/bin/python3.11`** (plain `python3` is 3.13, no numpy).
>
> **Phase 6 (oversampling + ADAA + FULL-CHAIN ASSEMBLY) ✅ DONE (2026-07-21).**
> The chain is now assembled and audible end-to-end for the first time. `src/dsp/PedalChain.h`
> (JUCE-free) wires all 14 stages in verified order (InputBuffer → [OS region: JFET → Treble/ATTACK
> → DRIVE → Clipper/GRUNT → Recovery → SK×2] → LevelBlend → C21 100n HP → EqPreGain → Baxandall →
> LO-MID → HI-MID → MasterOut); split base/OS-rate prepare so an OS-factor switch re-preps only the
> OD region. `src/dsp/PedalDSP.h` wraps it: `juce::dsp::Oversampling<double>` FIR half-band over the
> OD region (one instance per 2×/4×/8×, alloc-free switch; 1× = base-rate per-sample), clean-tap
> `DelayLine` compensating the OS FIR latency (49/60/64 base samples), realtime-vs-`render_oversampling`
> factor pick, host `setLatencySamples()` on change. `PluginProcessor::processBlock` now does real
> DSP (input trim → dry copy → kInputRef → chain → outputGain makeup → bypass crossfade → meters),
> replacing the old passthrough. JFET waveshaper got 1st-order ADAA (ln-cosh antiderivative). **ctest
> 16/16 PASS** (added `PedalChainTest` stability/polarity + `OSValidationTest` = GATE 6: LF BLEND=50%
> magnitude factor-independent ≤0.04 dB → delay comp exact; aliasing 2×−28→8×−34 dB). **AU auval PASS.**
> **KEY DEVIATIONS (deliberate, in-code + build-plan Phase 6 note):** (1) **AccurateOmega is N/A** —
> no chowdsp DiodePairT/omega in the path (D1/D2 = never-conducting hard clamps; both shapers are
> std::tanh). (2) **Clipper gets NO ADAA** — its VTC is inside an implicit RC-coupled Newton solve
> (not memoryless) → Esqueda ADAA doesn't apply; oversampling carries its antialiasing (state-space
> ADAA deferred unless low-OS listening demands it). (3) **Base-rate tone/master cap PREWARP not yet
> added** + OSFidelity low-OS top-octave restore → deferred to Phase 8 polish. (4) **RESOLVED
> 2026-07-21 (pre-capture check):** bypass dry copy is now delay-compensated the same way as
> BLEND's clean tap — a per-channel `DelayLine<float>` in `PluginProcessor` (sized via the new
> `PedalDSP::getMaxLatencySamples()`), retuned on any `reportedLatency` change (`PluginProcessor.h`/
> `.cpp`). ctest 16/16 still PASS. (5) **RailClamps still disabled** (need kInputRef
> from capture). **NEXT: Phase 7 — capture session + calibration** (kInputRef anchor, nonlinear-param
> fits, rail enable, bridged-T reshape, taper fits, OfflineRender exe). Phase-5 clipper structure
> notes retained below.
> Phase 4b (functional UI) ✅ DONE (commit 40451af). All linear stages (Step 4) ✅ COMPLETE incl.
> MasterOut. J201 JFET stage (nonlinear #1) STRUCTURE ✅ DONE. `processBlock` is still passthrough
> (metering only, `dsp` member unused) — no audible DSP until Phase 7 full-chain integration; UI
> controls correctly write params but don't yet affect sound (expected, not a bug). Phase completion
> tracking in `docs/build-plan.md` §"Where we are" — update both files.
> **PHASE 5 — CD4049UBE CLIPPER STRUCTURE DONE (2026-07-21):** `src/dsp/Clipper.h`. The audible
> overdrive. Modelled per `docs/nonlinear-component-modeling.md` §1's RECOMMENDED path: a static
> asymmetric-sigmoid inverter VTC inside the shunt-feedback loop, solved with the 4049's FINITE
> open-loop gain (kA0, nominal 25) — NOT ideal virtual ground (circuit.md GRUNT note: ideal-vg is
> audibly wrong). GRUNT cap bank (C11 4n7 always + C12 47n / C13 220n switched → Cut/Flat/Boost) in
> series with R16 feeds node W; R18∥C14 shunt feedback; both caps are trapezoidal companions (same
> convention as DriveStage/JfetStage/MasterOut). Node W is an implicit fn of Y=VTC(W), so it's a
> per-sample **Newton solve** (warm-started, 6 iters, F & F' derived in-header). VTC = inverting
> per-side tanh (kSatLo/kSatHi asymmetric → the doc's required even harmonics; R19-dropped effective
> rail folded into the sat levels; closed-form antiderivative for Phase-6 ADAA). **D1/D2 = hard
> clamps at node W** — Test 5 proves max|W|=1.1 V ≪ the ±3.75 V clamp window even at 8 V drive, so
> they never conduct in normal operation → no chowdsp DiodeT/AccurateOmega needed for them (that
> machinery lands in Phase 6 only if residual waveshaper aliasing demands it). **NO RailClamp** (the
> VTC IS the soft limiting; IC3 is not an op-amp). **NET INVERTING confirmed by the DC-step test** —
> the OD path carries THIS inversion + the J201's into BLEND (dsp.md polarity note; end-to-end BLEND
> DC-step still runs in Phase 6). **FINITE-GAIN COUPLING is the load-bearing result:** the GRUNT
> high-pass corners land at 896/144/36 Hz (Cut/Flat/Boost) — the input-node impedance R18/(1+A0)
> drags them 5.5×/3.1×/2.9× BELOW the ideal-virtual-ground 4980/453/104 Hz, and finite gain also
> lowers closed-loop gain below circuit.md's ideal −48.5 (HF plateau ~−16). Small-signal FR matches
> the oracle ≤0.012 dB <2 kHz; >2 kHz deviation (≤1.0 dB) is bilinear warp of the C14 corner
> (resolved by the Phase-6 OS region — the stage sits INSIDE it, it's the chain's hardest aliaser).
> **⚠ Phase-7 capture carry-forwards (all flagged in-code, constants-only refit):** kA0 (open-loop
> gain — fits BOTH the GRUNT-corner voicing AND the drive-sweep level, primary param), kSatLo/kSatHi
> (per-side clip ceilings / H2-H3 asymmetry, fit to drive-sweep Farina THD + low-freq H2/H3). GRUNT
> position→cap map (Cut=4n7/Flat=4n7∥47n/Boost=4n7∥220n) ✅ **VERIFIED at capture 2026-07-22**
> (cut 0 < flat +5.43 < boost +6.81 dB, 50–300 Hz matched-pair; `analysis/grunt_a0_check.py`).
> **⚠ GRUNT glitch-free swap deferred to Phase 6** (setGruntCap recomputes coefficients but keeps
> the cap history → a bounded click on a live swap; crossfade alongside the BLEND work, like
> TrebleAttack's deferred ATTACK crossfade). ATTACK + mid-freq switch topologies were already done
> in Phase 4 (TrebleAttack / MidBand) — Phase 5's switch-topology work was the GRUNT bank.
> **PHASE 4b — FUNCTIONAL UI DONE (2026-07-21):** `src/ui/PedalFace.{h,cpp}` composites the
> data-driven face from `ui/b7k_texture_base.png` + `ui/component_positions.csv`; all 8 knobs +
> 2 footswitches + 2 LEDs + 4 three-way switches (ATTACK/GRUNT/LO-MID/HI-MID) bound to APVTS via
> attachments. Two bugs found+fixed this session: (1) LO-MID/HI-MID pos→val read map
> (`updateLEDs`'s `midMap`) didn't match the write map (`onChange`), so the bottom lever position
> snapped back to middle on the next 33 Hz timer tick — both now share `{1,2,0}`. (2) LO-MID/HI-MID
> text labels (`SwitchLabelText`) and ATTACK/GRUNT icon glyphs (`AttackGruntIcons`) were
> click-through only via the paired `SwitchToggle`; added `onSelect` + `mouseDown` to both so
> clicking a label/icon row is equivalent to dragging the lever there. Toggle init positions
> aligned to each param's actual default index (was causing an open-time flicker). **⚠ Known
> duplication carry-forward:** the mid pos↔val map now lives in two places (`onChange` handlers +
> `midMap`) that must be kept in sync by hand — flagged, not yet collapsed into one shared table.
> **J201 JFET STAGE — STRUCTURE DONE (2026-07-21):** `src/dsp/JfetStage.h` + `tests/JfetStageTest.cpp`
> + `jfet_stage_lin_tf` in `eq_reference.py`. Path-B (docs/nonlinear-component-modeling.md §2)
> Wiener-Hammerstein cascade: input HP (C2 1n into R4+R5=1.1M, fc 144.7 Hz — J201 gate draws no
> current so R5/(R4+R5) gate divider folds into G0) → HF-lift shelf (C3 220n bypassing R6 3k3: zero
> 219 Hz / pole 719 Hz / +10.3 dB lift = 1+gmR6) → **inverting** mid-band gain (−G0) → per-polarity
> tanh soft waveshaper (satPos/satNeg asymmetric → the required even harmonics; ADAA-ready
> antiderivative). HP = physical trapezoidal cap (MasterOut convention); shelf = 1st-order bilinear
> IIR (== trapezoidal). ALL corners sub-kHz → NO audible-band bilinear warp → matches oracle ≤0.015
> dB across the whole band 48/96k (like MasterOut/InputBuffer; sits outside the OS region for LINEAR
> purposes, but its WAVESHAPER is the aliaser → oversampled+ADAA'd in the full chain, Phase 5/6).
> **NET INVERTING confirmed by the DC-step test → resolves circuit.md's "JFET output sign
> unconfirmed" carry-forward.** The OD path carries THIS inversion + the CD4049's into BLEND (dsp.md
> polarity note); end-to-end BLEND DC-step still runs in Phase 6. **NO RailClamp** (JFET drain, not a
> TL07x op-amp output — the soft waveshaper IS its limiting, unlike the "every op-amp stage" GATE
> item). ctest 13/13 PASS. **⚠ Phase-7 capture carry-forwards (all flagged in-code, one-line refit):**
> kG0 (mid-band |gain|, nominal 15), kGmR6 (shelf strength, nominal 2.277 from Shichman-Hodges
> self-bias Id≈0.12 mA / gm≈0.69 mS), kSatPos/kSatNeg (soft-sat levels / H2-H3 balance, nominal
> 3.0/2.6) — FIT all to the drive-min OD-path captures (§4 "J201 stage"; ~5:1 J201 spread → nominal
> SPICE can't match a specific unit). C4 bootstrap + R7 loading fold into G0 (Phase-4 boundary: node
> G is an ideal source per TrebleAttack.h; revisit output Z at Phase 7).
> **STEP-4 STAGES DONE SO FAR (each: FR test vs oracle in ctest + dsp-validator PASS):**
> ✅ **InputBuffer (IC1_A)** — `src/dsp/InputBuffer.h` + `tests/InputBufferTest.cpp`. ~1.59 Hz HP
>    (C1/R2), unity, non-inverting; matches analytic oracle ~0 dB at 44.1/48/96k. R1/R3 omitted from
>    isolated TF (justified). ✅ **TrebleAttack (treble net + ATTACK, stage #3)** — `src/dsp/TrebleAttack.h`
>    + `tests/TrebleAttackTest.cpp`. Built as **MNA (nodal + trapezoidal-companion caps, precomputed
>    inverse per position)** — NOT a WDF tree, because R7∥ladder→M is a loop (dsp-validator endorsed
>    this for a linear passive block; same bilinear discretisation as chowdsp caps). Matches oracle
>    ≤0.05 dB <2 kHz for all 3 positions; HF deviation is bilinear warp (shrinks 48k→96k, resolved by
>    the OS region). setAttack() zeros C8 state on swap; glitch-free crossfade is a Phase-5 add.
> ✅ **DriveStage (IC2_A, stage #4)** — `src/dsp/DriveStage.h` + `tests/DriveStageTest.cpp` +
>    `drive_stage_tf` in `eq_reference.py` (dsp-validator PASS 2026-07-20). Non-inverting op-amp
>    gain via ideal-op-amp decomposition (`Ig=Vin/Zg`, `Vf` across R15∥C10, `Vout=Vin+Vf`);
>    trapezoidal companion for C10 (like TrebleAttack's MNA, maps 1:1 to oracle — NOT a WDF tree).
>    DC gains EXACT: 4.164× (Rd=100k, min) … 77.744× (Rd=0, max); FR ≤0.06 dB through 2 kHz all four
>    DRIVE settings; top octave = pure bilinear warp (C10 corner ~10.3 kHz, resolved by the OS region).
>    Non-inverting confirmed by DC-step. DRIVE taper reaches EXACTLY 0 Ω at full drive (dodges §3 floor
>    trap). **⚠ Two Phase-7 capture-fit carry-forwards (flagged in-code): DRIVE taper SHAPE
>    (`kTaperExp=1.5` interim `100k·(1-x)^1.5` — confirm direction + p vs a matched-pair drive capture)
>    and the symmetric ±3.3 V rail estimate (real TL07x asymmetric around VD, positive may clip first).**
> ✅ **RailClamp (shared, `src/dsp/RailClamp.h`)** — op-amp output-rail saturation (calibration §6:
>    dead-linear→parabolic knee→hard clamp; C1-continuous; disabled by default so linear stage tests
>    stay valid). The per-stage rail-clamp GATE item — landed with DriveStage (IC2_A at ×78 rails first);
>    **apply it to EVERY subsequent op-amp stage** (SK×2, EQ block, MasterOut).
> ✅ **RecoveryBridgedT (IC2_B, stage #5)** — `src/dsp/RecoveryBridgedT.h` +
>    `tests/RecoveryBridgedTTest.cpp` (dsp-validator PASS 2026-07-20, full KCL re-derivation).
>    Unity-gain buffer + passive bridged-T (R22 100k/R23 33k/C16 680pF/C17 22n), NOT a +12 dB shelf
>    (no recovery make-up gain). Built as 2-node MNA + trapezoidal companion caps (same conventions
>    as TrebleAttack), precomputed 2×2 inverse; output = V(Nout). FR matches the UNLOADED oracle
>    (`bridged_t_tf`) to <0.02 dB through the notch (717 Hz ≪ Nyquist so warp negligible there); HF
>    shoulders warp bilinear-expected, →0 at 96k. Notch dead-on 716 Hz/−28 dB; test asserts
>    freq-tight (±3%) + depth-loose (≤−20 dB) per the Phase-4 caveat. RailClamp on the buffer op-amp
>    output (GATE, disabled by default). DC-step = unity/non-inverting. **⚠ Phase-7 carry-forward:
>    real notch DEPTH is loaded (R24→SK, deferred) + tolerance-sensitive → capture-validate (risk #1);
>    the isolated stage is unloaded by design, matching the unloaded oracle 1:1.**
> ✅ **SallenKeyLPF (IC4_B + IC4_A, stage #6)** — `src/dsp/SallenKeyLPF.h` + `tests/SallenKeyLPFTest.cpp`
>    (2026-07-20). Two instances of a 2nd-order unity-gain Sallen-Key LPF: IC4_B ≈10.7 kHz (R24 10k/
>    R25 22k, C18 1n feedback/C27 1n to GND) and IC4_A ≈3.3 kHz (R26 22k/R27 47k, C19 2n2 feedback/
>    C20 1n to GND). Built as MNA + trapezoidal companion caps (precomputed 2×2 inverse, consistent
>    with TrebleAttack/RecoveryBridgedT), NOT a WDF tree. Validated against `eq_reference.py ::
>    sallen_key_lpf_tf`: FR ≤0.25 dB through 2 kHz at 48k (both instances), HF deviation = bilinear
>    warp (shrinks 48k→96k for all frequencies). 2nd-order asymptotic rolloff ~−12 dB/oct at 768 kHz
>    (avoids warp in the measurement). DC-step unity non-inverting. RailClamp on each SK op-amp output
>    (GATE item, disabled by default). Both SKs sit inside the Phase-6 oversampled region — bilinear
>    warp resolved there, no prewarp needed. ctest PASS (1/1).
> ✅ **LevelBlend (VR2 LEVEL + VR1 BLEND)** — `src/dsp/LevelBlend.h` + `tests/LevelBlendTest.cpp`
>    (2026-07-20). Passive resistive network (LEVEL 100k A-taper OD volume divider + BLEND 100k
>    B-taper clean/OD crossfade) with exact loading interaction between the two pots. Solves the
>    1-node KCL equation for the LEVEL wiper voltage (loaded by the BLEND pot), then applies the
>    BLEND linear crossfade. Taper: `powerLawTaper(x, 1.0, 1.43)` for LEVEL (interim, fits at Phase 7),
>    linear for BLEND. `dist_engage` bool forces 100% clean output (the DIST footswitch override).
>    Validated against `eq_reference.py :: level_blend_tf`: DC gain matches oracle to ±0.001 dB across
>    7 knob position pairs; loading deficit of −1.82 dB at noon/noon confirmed (lower than the ideal-
>    taper ≈3.5 dB because power-law taper at noon gives L≈0.371). No RailClamp (passive stage —
>    no op-amp output). ctest PASS (1/1). ⚠ BLEND crossfade wiring + dist_engage smoothing deferred
>    to Phase 6 (needs delay-comp + end-to-end DC-step per build-plan risk #8).
> ✅ **EQ BLOCK (IC5_A/B/C/D + IC6_A, stage #7) — DONE (2026-07-21, dsp-validator PASS all 3 stages).**
>    Built as three headers sharing a new `src/dsp/MnaSolve.h` (templated NxN Gauss-Jordan inverse +
>    matvec; the peaking stages' MNA matrix depends on pot splits, so it re-inverts ONLY on a dirty
>    flag when a pot/switch moves — never per sample, allocation-free, RT-safe):
>    • **EqPreGain (IC5_A buffer + IC5_B −2.2)** — `src/dsp/EqPreGain.h` + `tests/EqPreGainTest.cpp`.
>      Frequency-flat scalar gain −R29/R28 = −2.2 (inverting), two RailClamps (IC5_A + IC5_B outputs).
>    • **Baxandall BASS+TREBLE (IC5_C)** — `src/dsp/Baxandall.h` + `tests/BaxandallTest.cpp`. ONE coupled
>      7-node MNA network (both wipers sum into the IC5_C virtual ground); 5 caps incl. C30 47p feedback.
>      FR ≤0.095 dB through 2 kHz vs `baxandall_tf` (all boost/flat/cut); HF warp shrinks 48k→96k; DC
>      gain −0.925926 (inverting, matches oracle exactly — the sub-unity magnitude is the bass-shelf DC
>      droop, not a bug).
>    • **MidBand (LO-MID IC5_D / HI-MID IC6_A)** — `src/dsp/MidBand.h` + `tests/MidBandTest.cpp`. ONE
>      reusable 4-node MNA peaking stage, switchable series cap (C33/C35) via live matrix recompute (dsp.md
>      "Fixed circuit variants" — cap VALUE changes, not shape, so NO setSMatrixData swap). Validated the
>      FULL switch matrix: both bands × min/centre/max × all 3 caps (18 configs) vs `mid_stage_tf`, worst
>      0.12 dB on a steep peak (shrinks with OS); DC gain −1 (inverting) at every position.
>    Key stamping subtlety (dsp-validator confirmed correct): caps bridging to the op-amp virtual-ground
>    node (MidBand C33, Baxandall C30) stamp the Vout-determining row with the oracle's sign-flipped
>    "currents INTO node" convention → the cap history current lands as +ieq in BOTH the natural node row
>    AND that row. RailClamp on every op-amp output (GATE item, disabled by default). 4-INVERSION NET
>    POLARITY CONFIRMED by the per-stage DC-step tests: IC5_B(−2.2) + Baxandall(−) + LO-MID(−) +
>    HI-MID(−) = 4 inversions → net non-inverting through the EQ. ctest 11/11 PASS.
>    **⚠ Two Phase-6 carry-forwards (both flagged in-code):** (1) the EQ's audible-band HF caps (TREBLE
>    ~5 kHz peak, HI-MID to 3 kHz) warp at base rate (~0.3 dB @10 kHz/48k) — must be covered by the
>    Phase-6 oversampled-region span or prewarped; (2) **C21 (100n) + C31 (2u2) inter-stage coupling
>    caps** are EXCLUDED from these stages (oracle boundary) — C21 into the ~10k stack input is a
>    ~150 Hz HP that shapes bass audibly, so place it at the EqPreGain→Baxandall boundary during
>    integration (don't forget it in the full chain).
>    **↳ Oracle fix (2026-07-21):** `eq_reference.py`'s mid peak-scan PRINT loop was calling HI-MID with
>    the default C32=22n instead of the real C34=6n8 → printed wrong peak centres (405 vs 728 Hz). Fixed
>    (per-band across-lug cap); the print now reproduces circuit.md's validated HI-MID table
>    (728/1552/3116 Hz) exactly. The `mid_stage_tf` FUNCTION was always correct (C32 is a param); only
>    the diagnostic print was wrong. The C++ stage uses 6n8 for HI-MID throughout.
> **⚠ ATTACK-SWITCH TOPOLOGY CORRECTED THIS SESSION** (found while building the oracle): circuit.md's
>    "triple-checked" node graph had the switch **pole** wrong (named node M as common → implied a Cut
>    MUTE). Verified from primary+backup schematics + schematic-checker: **pole = C8 bottom plate**;
>    Boost→C8 bridges R8, Cut→C8 shunts P→GND (treble cut, no mute), Flat→open. circuit.md + this file's
>    UI-map carry-forward corrected; `treble_attack_tf` in `eq_reference.py` implements the fix.
> ✅ **MasterOut (VR8 MASTER divider + IC6_B buffer + output HP, stage #9) — DONE (2026-07-21,
>    dsp-validator PASS all 7 checks).** `src/dsp/MasterOut.h` + `tests/MasterOutTest.cpp` +
>    `master_out_tf` in `eq_reference.py`. The LAST linear stage. [ENG] MASTER (100k A) post-EQ
>    divider: top = IC6_A out via C36(2u2), bottom = VD, wiper → IC6_B(+); IC6_B unity buffer;
>    C37(2u2) → R47(1k series) → OUT, R46(100k) pulldown. The wiper feeds high-Z IC6_B so it is
>    UNLOADED → the pot is a pure resistive tap: `divRatio = Rbot/Rp = master^p` (A-taper). Built as
>    two single-node MNA HPFs (C36→100k pot-to-VD; C37→R46) with a unity buffer + RailClamp between
>    them (same trapezoidal cap conventions as RecoveryBridgedT). **The ONLY caps are two ~0.72 Hz
>    sub-audio HPFs — NO audible-band caps → NO bilinear warp**, so the stage matches the analytic
>    oracle to ≤0.00024 dB across the WHOLE band (20 Hz–20 kHz, 48/96k) at master 1.0/0.5/0.25, and
>    sits OUTSIDE the Phase-6 oversampled region (like InputBuffer's ~1.6 Hz HP). Unity at full CW
>    (0 dB); non-inverting, AC-coupled (DC gain 0) — step jumps to +divRatio·Vin then decays to ~0,
>    closing the EQ→MASTER polarity chain (EQ net non-inv + MASTER adds none). RailClamp on IC6_B
>    output (GATE, disabled by default). ctest registered. **⚠ Phase-7 carry-forward:** MASTER A-taper
>    SHAPE (`kMasterTaperExp=1.43` interim `master^1.43`) — fit p to the master-sweep captures alongside
>    the LEVEL taper (same power-law method). RailClamp now applied to every op-amp stage as built
>    (calibration §6, GATE item). (Build-plan Phase 4.)
> **LAST COMPLETED: Step 3 (chowdsp_wdf smoke test) — COMPLETE (2026-07-20).**
> All three phases done: schematic ✓ → scaffold (20 params, AU+VST3, auval PASS) ✓ → WDF smoke test ✓.
> `circuit.md` is fully verified: full chain traced IN→OUT, node-by-node + value-by-value cross-check
> against primary p.4, backup, and both BOM pages, PLUS (session 3): ✅ Baxandall + LO-MID/HI-MID
> tone-stack per-node redraw (verified node graphs now in circuit.md — R35/R36 wiper→(−) roles,
> R40/R41 + R44/R45 flat-unity legs, C25/C26 lug→wiper, C36 2u2 real); ✅ R19 located (= the 4049's
> +9V supply dropper → clipper rail is LOWER/softer than the op-amp rail — real modeling consequence);
> ✅ [ENG] mid-cap table validated by nodal sim (all 6 positions within ±8.5%; per-position boost
> range varies ±14.5–28 dB — capture-validate); ✅ Master gain-staging sim-checked (0.72 Hz corner,
> flat, unity CW; the pot also fixes the stock board's missing IC6_B bias); ✅ GRUNT corners shown to
> depend on the 4049's finite open-loop gain (model coupled, not HPF→waveshaper); BOM fully
> reconciled R1–R54.
> Full chain: input buffer → J201 JFET gain → treble/ATTACK → DRIVE (IC2_A) → GRUNT → CD4049UBE
> clipper (R19-dropped rail; D1/D2 = rail clamps) → IC2_B unity buffer + bridged-T (~717 Hz notch,
> capture-validate) → 2× Sallen-Key LPF → LEVEL → BLEND(clean crossfade) → EQ (4-band, switchable
> mids) → MASTER[ENG] → output buffer. XLR DI + power beyond VD skipped. Ultra features are [ENG].
> **TRIPLE-CHECK PASS also done (same session):** BOM↔circuit.md 100% diff-clean; 11 load-bearing
> topology claims independently re-verified against the p.4 image (fresh-eyes agent, all CONFIRMED);
> backup schematic corroborates the tone-stack/output redraws; p.3 measured tables ↔ nodal sim agree
> ~3%/±2.5 dB; info.txt + dsp.md cross-checked. See circuit.md Validation notes ("TRIPLE-CHECK PASS").
> **J201 JFET stage (nonlinear #1) STRUCTURE ✅ DONE this session** (see the J201 block above) — sign
> CONFIRMED inverting by its DC-step test (circuit.md carry-forward resolved). One of only TWO
> non-WDF-native parts. **NEXT: CD4049UBE clipper (nonlinear #2) + GRUNT bank + switch topologies**
> (build-plan Phase 5). The clipper is the heart of the distortion: model the unbuffered-inverter VTC
> as a fitted asymmetric-tanh waveshaper inside the R16/R18∥C14 shunt-feedback decomposition, D1/D2 as
> hard rail clamps at node W, R19-dropped/soft rail (ceiling fit to captures), and the GRUNT cap bank
> + finite-4049-gain coupling for the three GRUNT corners — see `docs/nonlinear-component-modeling.md`
> §1 (DAFx "Red Llama" params as the prior) + §4 capture plan. Then Phase 4b functional UI. NOTE: all
> J201 amplitude constants are NOMINAL pending the Phase-7 capture session (same session fits the
> clipper); only its filter corners + inverting polarity are final.

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
