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
> **CURRENT: Phase 6 (oversampling + ADAA + FULL-CHAIN ASSEMBLY) ✅ DONE (2026-07-21).**
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
> position→cap map is the ASSUMED UI map (Cut=4n7/Flat=4n7∥47n/Boost=4n7∥220n) — VERIFY at capture.
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
  documented filenames with no captures on disk yet: 49/49 PASS. `render_args()` (maps parsed
  settings → `OfflineRender` CLI flags) is still NOT implemented — blocked on `OfflineRender` itself
  not existing yet (see "NEXT: Phase 7"). Missing DC/rail values → take nominal from datasheets,
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
  down=250Hz(47n); **HI-MID** up=1.5k(3n3)/mid=3k(820pF)/down=750Hz(15n); **GRUNT** ⚠assumed, VERIFY
  at capture: up/Boost=4n7∥220n(most)/mid/Cut=4n7 alone(least)/down/Flat=4n7∥47n(medium). That text: **font = Lexend Exa** (embed as binary data, this pedal's face text
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
