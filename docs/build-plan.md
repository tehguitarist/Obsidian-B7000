# Obsidian-B7000 — Detailed Build Plan (written 2026-07-19)

> Step-by-step plan from here (Step 1 complete) to a shipped plugin. Each phase ends with a
> **GATE** — do not start the next phase until the gate passes. Phase numbering continues the
> CLAUDE.md build sequence. Source of truth for values/topology = `.claude/rules/circuit.md`
> (fully verified, BOM reconciled R1–R54); DSP rules = `.claude/rules/dsp.md`; the hard-won
> calibration lessons = `docs/calibration-and-gain-staging.md`.

## Where we are

Schematic analysis is **complete and closed**: full chain traced and verified, tone-stack node
graphs redrawn, R19 located (4049 supply dropper), [ENG] mid caps sim-validated, C36 verified,
IC2_B unity-buffer correction locked in. No schematic questions block any build phase.
`analysis/eq_reference.py` computes analytic reference curves for the tone stack (mid peaking
stages, Baxandall, bridged-T) — use it as the expected-response oracle in Phase 4.

**Capture-blocked items** (need the real B7K Ultra, audio-only session per
`docs/nonlinear-component-modeling.md` §4): bridged-T actual shape, 4049 VTC + effective rail
(R19 sag), J201 fit, mid boost ranges, `kInputRef`, output level match. **None of these block
Phases 2–6** — build with nominal/datasheet fits and swap in capture fits at Phase 7. Schedule
the capture session any time before Phase 7; one matched session, ~29 essential takes.

## The signal chain as DSP objects (per channel, `PedalDSP`)

| # | Stage | Type | Model |
|---|-------|------|-------|
| 1 | Input buffer + bias (R1/C1/R2/R3, IC1_A) | linear | trivial HP + unity buffer; clean tap here |
| 2 | J201 stage (Q1/Q2, R4–R6, C2–C4) | **nonlinear** | fitted gain + soft waveshaper (nominal SPICE → capture fit) |
| 3 | Treble net + ATTACK (R7/R8, C5/C6/C9, R12/R14, C8, R11/C7/R13) | linear, 3-topology switch | WDF / analytic biquad-equivalent; positions: C8-bridges-R8 / open / node-to-GND |
| 4 | DRIVE stage (IC2_A, R15/C10, R17/VR3/R32) | linear, pot-coupled | ideal-op-amp decomposition; C-taper 100k rheostat |
| 5 | GRUNT bank + clipper (C11–C13, R16, IC3+R18/C14, D1/D2, R19 rail) | **nonlinear**, 3-pos switch | coupled: cap bank + R16 into finite-gain asymmetric-tanh VTC; D1/D2 clamps; ceiling calibrated to capture (R19!) — oversampled + ADAA |
| 6 | Recovery buffer + bridged-T (C15/R20/R21, IC2_B, R22/R23/C16/C17) | linear | passive bridged-T (live ImpedanceCalculator); ~717 Hz notch ideal — reshape to capture |
| 7 | SK LPF ×2 (IC4_B ~10.7k, IC4_A ~3.3k) | linear | standard Sallen-Key, unity |
| 8 | LEVEL (VR2 100k A) | linear | divider, audio taper (power-law fit, see dsp.md §tapers) |
| 9 | BLEND (VR1 100k B) | linear | clean/OD crossfade; **DIST footswitch = override to 100% clean** |
| 10 | EQ: IC5_A buf, IC5_B −2.2, Baxandall (IC5_C), LO-MID (IC5_D), HI-MID (IC6_A) | linear, coupled pots + 2×3-pos cap switches | verified node graphs in circuit.md; reference curves in `analysis/eq_reference.py` |
| 11 | MASTER (VR8 100k A) [ENG] + IC6_B + C37/R47/R46 | linear | post-EQ divider → unity buffer → output HP |

Volume/trim/metering/bypass live in the processor, not the WDF tree (architecture.md).

---

## Phase 2 — Repo + CMake scaffold (routine work; cheap model fine)

1. Add submodules: `libs/JUCE`, `libs/chowdsp_wdf`, `libs/xsimd` (build.md commands).
2. Instantiate `CMakeLists.txt` from `CMakeLists.txt.template`: plugin name **Obsidian-B7000**,
   company Leigh Pierce, codes (pick 4-char codes, e.g. `Ob7k`/`LPrc`), AU+VST3,
   `COPY_PLUGIN_AFTER_BUILD TRUE`, SYSTEM-include chowdsp_wdf, `PEDAL_WARNING_FLAGS` gate.
3. Minimal `PluginProcessor`/`PluginEditor` (pass-through audio, empty black editor).
4. **Full APVTS parameter set now** (IDs are forever — architecture.md):
   - Pots (`AudioParameterFloat` 0..1, taper in DSP): `master`, `blend`, `level`, `drive`,
     `lo`, `lo_mid`, `hi_mid`, `hi`.
   - Switches (`AudioParameterChoice`): `attack` (Boost/Flat/Cut), `grunt` (three bass-boost
     levels per info.txt — no official position names; note the physical On-Off-On CENTRE is the
     minimum-bass position (4n7 only), throws add 47n or 220n — order the UI/param to mirror the
     hardware), `lo_mid_freq` (250/500/1k), `hi_mid_freq` (750/1.5k/3k).
   - Bools: `bypass`, `dist_engage` (default **true**; overrides BLEND to 100% clean when false,
     own ~5ms crossfade — circuit.md "Footswitches"), `trim_link` (default false), `hq` (defer —
     add only if FeatureProfile justifies; reserve the ID).
   - Trims/OS: `input_trim`, `output_trim` (dB), `oversampling`, `render_oversampling`.
5. CI: activate `.github/workflows/ci.yml` placeholders; `ctest` skeleton with one dummy test.

**GATE 2:** AU + VST3 build, pass `auval`/pluginval, load in Logic/a DAW, audio passes through,
all parameters visible + automatable + state round-trips. CI green on all three platforms.

## Phase 3 — chowdsp_wdf smoke test (routine)

Console test exe: RC lowpass (e.g. 10k/1n) in WDF (double, compile-time API), rendered offline;
assert −3 dB point within 1% of 1/(2πRC), and that a `CapacitorT` missing `.prepare()` is caught
(regression for the classic silence bug). Register with `add_test()`.

**GATE 3:** test passes at 44.1/48/96k.

## Phase 4 — Stage-by-stage DSP, linear first (validate each; dsp-validator after each)

Build order = signal order, each stage a header in `src/dsp/`, each with a console FR test
comparing against the analytic transfer function (tolerance ±0.25 dB 20 Hz–10 kHz, document any
bilinear-warp deviation above; prewarp HF caps per dsp.md where corners are fixed):

1. **InputBuffer** (R1/C1/R2/R3): ~1.6 Hz HP, unity. Clean tap point.
2. **TrebleAttack** (stage 3): three switch positions validated independently against nodal
   reference (add its TF to `eq_reference.py` first). Precomputed S-matrix per position OR live
   ImpedanceCalculator — positions differ topologically (node grounded vs cap bridge vs open), so
   follow dsp.md: precompute per topology, swap `setSMatrixData()`.
3. **DriveStage** (IC2_A): ideal-op-amp decomposition; gain 4×–78× vs VR3; C-taper (fit per
   dsp.md; beware taper floor on the 100k). DC-step polarity test (non-inverting).
4. **RecoveryBridgedT**: unity buffer + passive bridged-T; validate notch at 717 Hz/−28 dB vs
   `eq_reference.py` (ideal values for now; capture reshape in Phase 7). Live
   ImpedanceCalculator (linear network, tolerance-sensitive → keep values as variables).
5. **SallenKey2** (×2 instances, different values): FR vs textbook SK response.
6. **LevelBlend**: dividers/crossfade (plain gains, not WDF); audio-taper for LEVEL;
   `dist_engage` override hook here.
7. **EQ block**: Baxandall (coupled BASS+TREBLE — ONE WDF/nodal network), LO-MID, HI-MID (each
   an inverting-unity + pot network stage; series cap switchable via live ImpedanceCalculator).
   Validate every band at min/centre/max + both mid switches at all 3 positions against
   `analysis/eq_reference.py` (already checked against the schematic + p.3 tables). Check the
   4-inversion net polarity with a DC step through the whole EQ.
8. **MasterOut**: divider + buffer + C37/R47/R46 HP; A-taper.

**J201 stage (nonlinear #1)** comes after the linear chain around it works: implement as fitted
gain + soft waveshaper (nominal from Fairchild datasheet SPICE params; structure per
`docs/nonlinear-component-modeling.md` §2), with the C3/R6 source-bypass HF-gain rise and C4
bootstrap behaviour captured by the fit. Sine + DC-step polarity test; expect mild asymmetric
soft compression, NOT hard clipping.

**GATE 4:** every linear stage's FR test in ctest and green; dsp-validator run per stage;
polarity verified per stage; J201 stage behaves plausibly (gain ~×10–30 region, soft).

## Phase 5 — The clipper (nonlinear #2, the heart) + switch topologies

1. Implement the **GRUNT bank + R16 + finite-gain 4049 + R18∥C14 + D1/D2** as ONE coupled stage
   (circuit.md GRUNT note: ideal-virtual-ground is audibly wrong).
2. 4049 VTC = asymmetric-tanh waveshaper, params seeded from the DAFx-2020 extended model /
   TI datasheet curve; **effective rail as a fit parameter** (R19 dropper — do NOT hardcode 8.6V).
   D1/D2 = hard clamps at node W referencing the full +9V rail (chowdsp `DiodeT` w/ 1N4148 params,
   `DiodeQuality::Good`, AccurateOmega — dsp.md).
3. Validate: sine-clipping snapshots at 3 GRUNT × 3 drive settings; DC-step polarity (inverting);
   GRUNT HPF corners measured and compared against the finite-gain prediction
   (~1.5–1.9k / 137–177 / 32–41 Hz at A0 20–30); asymmetry present (even harmonics).
4. Verify all switch positions of ATTACK/GRUNT/mid-freqs independently; parameter smoothing +
   glitch-free switch swaps.

**GATE 5:** clipper harmonics qualitatively match the DAFx reference curves; all 3×3×3×3 switch
combos render finite and stable; dsp-validator pass on the stage.

## Phase 6 — Oversampling + ADAA (dsp.md rules)

1. OS region = J201 → clipper → recovery/bridged-T → SK filters (nonlinear + downstream HF caps);
   `postFn` pattern; base-rate stages get prewarp on fixed HF corners.
2. AccurateOmega provider everywhere (not omega4); ADAA (ln-cosh antiderivative) on the tanh VTC
   and the rail clamps; 1×/2×/4×/8× runtime factors + separate `render_oversampling`,
   glitch-free switching per dsp.md.
3. Aliasing measurement test (JUCE FFT console exe): sweep at high drive, assert aliasing
   components at 4× are below the harmonic floor by a documented margin; OSFidelity probe
   (build.md) for the low-OS top-octave restore decision.

**GATE 6:** aliasing test green; 1× vs 8× FR delta documented; CPU per OS factor measured
(PerfBenchmark); no NaN/Inf anywhere in a full-random-automation soak.

## Phase 7 — CAPTURE SESSION + full-chain integration + calibration

**Do the hardware capture session now if not already done** (`docs/nonlinear-component-modeling.md`
§4: two baselines + ~29 takes, `gen_test_signal.py` signal, `parse_capture()` filenames).
Then:

1. `OfflineRender` console exe mirroring `processBlock` exactly (analysis/ + build.md).
2. Calibrate in the documented order (calibration doc): `kInputRef` from the capture rig anchor;
   THEN fit the 4049 VTC/rail + J201 shaper to the driven captures (control-isolation +
   matched-pair diffs); reshape the bridged-T to the measured notch (or lack of one — it's
   tolerance-sensitive); confirm mid-band boost ranges + GRUNT corners + taper shapes
   (two-point minimum per pot, matched-pair method for coupled ones); output makeup =
   level-match to captures (may exceed 1.0 — no headroom pad).
3. Decompose any residual level deficit per calibration doc §4 before touching constants.

**GATE 7:** A/B harness (`analyze.py`): 1/3-oct FR within target tolerance on the essential
matrix, swept-THD tracks, null depth documented, knob-tracking pass/fail table green for all
8 pots + 4 switches + DIST at the captured points.

## Phase 8 — UI

1. Centre pedal face from the **`ui/` assets** (per `ui/ui-replacements.md`: 2× res, crop-don't-
   stretch, alpha-safe rotation) — 8 knobs (B7K-Ultra layout: MASTER/LEVEL/BLEND/DRIVE top,
   LO/LO-MID/HI-MID/HI bottom), 2 footswitches (bypass + DIST), ATTACK/GRUNT 3-pos toggles,
   2 mid-freq selectors, LED per footswitch.
2. Peripheral chrome from `src/ui/` (PedalLookAndFeel, VUMeter, trims + Trim Link, OS strip,
   scale) per `docs/ui-peripheral-spec.md` + ui.md (tooltips 2-dp, trim readout labels,
   selector visual language, resize persistence with debounced default-save).
3. Headless editor render test (build.md) at 0.5×/1×/2.5×; VU/trim bounds check at extremes.

**GATE 8:** headless renders correct at all scales; params bind; bypass/DIST LEDs track APVTS
directly; no drawing outside LookAndFeel.

## Phase 9 — Reference validation + performance pass

1. Full `docs/validation-and-capture.md` A/B run against the whole capture matrix; fix by
   decomposition, not fudge factors.
2. PerfBenchmark / FeatureProfile / OSFidelity probes → decide `hq` toggle (omega4 vs
   AccurateOmega is usually the only real lever), README performance table.

**GATE 9:** validation report written into `docs/` (numbers, not adjectives); HQ decision made
and implemented or explicitly rejected.

## Phase 10 — Final sweep + release

1. Full control-sweep soak (all 8 pots × switches × OS × bypass/DIST transitions): no
   instability/clicks/NaN/Inf (output >0 dBFS at extremes is faithful — trim manages it).
2. Installers (installer/ scripts), release.yml dry-run, signing when certs exist.

**GATE 10:** ctest suite green in CI on macOS/Windows/Linux; release draft builds.

---

## Model tiering per phase (CLAUDE.md policy)

- Phases 2–3, boilerplate of 4, 8-layout, 10: **routine** → mid-tier (e.g. Sonnet), medium effort.
- Phase 4/5 stage correctness, all dsp-validator + schematic-checker runs, Phase 7 fitting
  decisions: **important thinking** → Opus-tier high effort (agents already pinned).
- Phase ordering decisions / plan revisions / capture-fit trade-offs: top-tier high effort.

## Risk register (things most likely to bite)

1. **Bridged-T notch** — ideal −28 dB @717 Hz is suspicious for this pedal; if the real unit shows
   a shallow scoop, component tolerances (C16/C17) are doing heavy lifting → make all four values
   fit parameters, reshape at Phase 7. (Capture take dedicated to this exists in §4 matrix.)
2. **4049 rail/sag (R19)** — static fit first; only add dynamic sag if captures demand it.
3. **J201 5:1 spread** — never trust nominal SPICE; the capture fit is the model.
4. **Mid boost-range variation** (±14.5–28 dB by position) — DE-RISKED (triple-check pass): the
   p.3 measured tables show the same monotonic trend on real hardware (26→18 dB lo-mid,
   23→12.6 dB hi-mid) and agree with the sim within ~3%/±2.5 dB, so this is faithful single-cap
   behaviour. Captures confirm absolute numbers only; the dual-cap fallback is very unlikely
   to be needed.
5. **GRUNT corners** — re-verify after the A0 fit; they moved 2–5× between ideal and A0=20.
6. **Taper shapes** — DRIVE is a 100k C-taper in a gain leg (floor trap + shape fit, dsp.md);
   constrain every fitted taper with ≥2 knob points.
7. **DIST footswitch semantics** — it must override BLEND *mix target* only (EQ/Master keep
   processing the clean signal), with its own crossfade; do not implement as a second bypass.
