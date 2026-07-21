# Obsidian-B7000 — Detailed Build Plan (written 2026-07-19)

> Step-by-step plan from here (Step 1 complete) to a shipped plugin. Each phase ends with a
> **GATE** — do not start the next phase until the gate passes. Phase numbering continues the
> CLAUDE.md build sequence. Source of truth for values/topology = `.claude/rules/circuit.md`
> (fully verified, BOM reconciled R1–R54); DSP rules = `.claude/rules/dsp.md`; the hard-won
> calibration lessons = `docs/calibration-and-gain-staging.md`.

## Where we are

| Phase | Status | Completed | Gate |
|-------|--------|-----------|------|
| 1 — Schematic analysis | Complete | 2026-07-19 | — |
| 2 — CMake scaffold | Complete | 2026-07-20 | auval PASSED, ctest 2/2 |
| 3 — chowdsp_wdf smoke test | Complete | 2026-07-20 | −3 dB ±0.02 dB at 44.1/48/96k |
| 4 — Stage-by-stage linear DSP | **✅ COMPLETE (2026-07-21)** | InputBuffer ✓, TrebleAttack ✓, DriveStage ✓ + RailClamp util ✓, RecoveryBridgedT ✓, SallenKeyLPF ✓, LevelBlend ✓ (2026-07-20), EQ block ✓ (EqPreGain + Baxandall + MidBand, 2026-07-21), **MasterOut ✓ (2026-07-21, last linear stage)** | per-stage FR + dsp-validator |
| 4 (nonlinear #1) — J201 JFET stage | **✅ STRUCTURE DONE (2026-07-21)** | JfetStage ✓: linear shape (HP + HF-lift shelf) + inverting polarity + asym soft waveshaper. All amplitude constants (G0/gmR6/sat) NOMINAL → fit at Phase 7 capture. | linear FR vs oracle + DC-step polarity + nonlinearity sanity (ctest 13/13) + dsp-validator |
| 4b — Functional UI pass | **✅ DONE (2026-07-21)** | data-driven pedal face bound to APVTS (commit 40451af) | interactive testability |
| 5 — Nonlinear clipper + GRUNT + switch topologies | **✅ STRUCTURE DONE (2026-07-21)** | Clipper ✓: GRUNT bank + R16 + finite-gain 4049 VTC + R18∥C14 + D1/D2 as ONE coupled stage (Newton solve). GRUNT corners finite-gain (896/144/36 Hz ≪ ideal-vg). All amplitude params (A0/satLo/satHi) NOMINAL → Phase-7 capture fit. Oversample+ADAA = Phase 6. | small-signal FR vs oracle + GRUNT corners + DC-step polarity + asymmetry + D1/D2-never-conduct (ctest 14/14) + **dsp-validator PASS (all 6 checks, 2026-07-21)** |
| 6 — Oversampling wiring + delay compensation | **✅ DONE (2026-07-21)** | Full chain assembled (`PedalChain`/`PedalDSP`), wired into `processBlock`; OS region JFET→SK (FIR, 1×/2×/4×/8× + render factor); clean-tap `DelayLine` compensation; host `setLatencySamples`; JFET ADAA. AU auval PASS. | ctest 16/16 (+ PedalChainTest, OSValidationTest); delay comp factor-independent <0.1 dB LF; aliasing 2×−28→8×−34 dB |
| 7 — Full-chain integration + level calibration | **Pre-work ✅ COMPLETE (2026-07-22); calibration not started** — see `docs/phase7-handoff.md` | chain assembled + wired (Phase 6); **capture session DONE** (55 files, all parse) + gain-session correction (`ff5fc5f`); **`FitParams` runtime fit constants DONE** (`697339f`); **`OfflineRender` + `render_args()` DONE** (the ex-blocker) with `render_smoke_check.py` proving the CLI→DSP mapping. REMAINING = calibration proper, in the doc's order: `kInputRef` anchor, nonlinear fits, bridged-T reshape, taper fits, output makeup, rail-clamp enable | ctest 16/16; `render_smoke_check.py` all PASS (EQ knob direction, mid-freq mapping, bypass, align lag == reported latency) |
| 8 — Full UI (polish, VU gate, headless) | Not started | — | — |
| 9 — HQ/Eco + final sweep | Not started | — | — |

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

## UI timing — functional pass pulled forward (decision 2026-07-20)

The UI is split into two passes instead of one Phase-8 block:

- **Functional UI (Phase 4b, end of Phase 4 — before Phase 5's clipper):** build the data-driven
  centre pedal face (base image + CSV, `ui.md`) with all controls **bound to APVTS** — knobs,
  switches, footswitches, LEDs. Goal is *interactive testability*, not final polish: from Phase 5
  onward every "turn DRIVE/GRUNT/BLEND up and check X" request is done on real controls instead of
  the DAW's generic slider editor. **Safe to build here** because the APVTS set is frozen at Phase 2
  and the UI is DSP-decoupled (`architecture.md`) — no param churn, no DSP entanglement, and the
  assets + switch-position mappings are all confirmed (`ui.md`, `circuit.md`).
- **Why not earlier:** at Phase 2 the plugin is pass-through — nothing to audition. End of Phase 4
  (linear chain + J201 audible) is the first useful point.
- **Not a blocker either way:** JUCE exposes every APVTS param to the host's generic editor, so
  interactive testing is *possible* without any custom UI — the functional pass is a
  quality-of-life upgrade for the human-in-the-loop checks, not a prerequisite for them.

**What stays at Phase 8** (needs finished DSP/calibration, so a second UI touch is expected, not
rework): the VU idle-noise-gate threshold (moves with the final Phase 7 output makeup), final
label-opacity tuning against the base image, peripheral-chrome polish, and the headless
scale-verification GATE. Phase 8 below is the authoritative full UI spec; Phase 4b is the subset of
it that's worth having early.

---

## Phase 2 — Repo + CMake scaffold (routine work; cheap model fine)

1. Add submodules: `libs/JUCE`, `libs/chowdsp_wdf`, `libs/xsimd` (build.md commands).
2. Instantiate `CMakeLists.txt` from `CMakeLists.txt.template`: plugin name **Obsidian-B7000**,
   company Leigh Pierce, codes (pick 4-char codes, e.g. `Ob7k`/`LPrc`), AU+VST3,
   `COPY_PLUGIN_AFTER_BUILD TRUE`, SYSTEM-include chowdsp_wdf, `PEDAL_WARNING_FLAGS` gate.
3. Minimal `PluginProcessor`/`PluginEditor` (pass-through audio, empty black editor). Decide bus
   layouts here: mono + stereo (the pedal is a mono circuit — stereo = two independent `PedalDSP`
   instances per architecture.md, never a summed path). Add `juce::ScopedNoDenormals` to
   `processBlock` from day one (decaying WDF cap states denormal and quietly eat CPU), and
   override `getBypassParameter()` to return the `bypass` param so hosts wire their own bypass
   control to it.
4. **Full APVTS parameter set now** (IDs are forever — architecture.md):
   - Pots (`AudioParameterFloat` 0..1, taper in DSP): `master`, `blend`, `level`, `drive`,
     `lo`, `lo_mid`, `hi_mid`, `hi`.
   - Switches (`AudioParameterChoice`): `attack` (Boost/Flat/Cut), `grunt` (three bass-boost
     levels per info.txt — no official position names; note the physical On-Off-On CENTRE is the
     minimum-bass position (4n7 only), throws add 47n or 220n — order the UI/param to mirror the
     hardware), `lo_mid_freq` (250/500/1k), `hi_mid_freq` (750/1.5k/3k).
   - Bools: `bypass`, `dist_engage` (default **true**; overrides BLEND to 100% clean when false,
     own ~5ms crossfade — circuit.md "Footswitches"), `trim_link` (default false), `hq` (whether
     the toggle is *justified* is a Phase 9 decision, but the PARAMETER must be handled now — an
     APVTS ID cannot be "reserved" by omission, and adding one later can shift AU integer parameter
     IDs and silently break session recall in Logic-family hosts unless params carry
     `juce::ParameterID` version hints. **No audio/CPU impact either way — this is purely session
     compatibility.** Do BOTH of the following in THIS phase, not at Phase 9:
       - Construct every parameter with a versioned `ParameterID{"id", 1}` — the JUCE-idiomatic
         default that future-proofs *any* later addition (bump the hint to `2`, `3`, … for params
         added in future versions so existing AU IDs stay put).
       - Also add `hq` now as a **default-true no-op** the DSP ignores until Phase 9. Since we
         already know it's coming, materialising it removes it as a special case: Phase 9 just
         wires up an existing param with no layout change and no version-hint arithmetic to
         remember (a forgotten hint bump would reintroduce the recall bug). Only cost is a
         host-visible parameter that does nothing until Phase 9 — trivial.)
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
bilinear-warp deviation above; prewarp HF caps per dsp.md where corners are fixed). Pick an
interim `kInputRef` now (a nominal bass-DI level, ~1–3 V/FS — the template's 0.87 is a guitar-rig
number) and use it consistently through Phases 4–6 so the nonlinear tests exercise realistic drive
levels; the capture anchor replaces it at Phase 7:

1. ✅ **InputBuffer** (R1/C1/R2/R3): ~1.6 Hz HP, unity. Clean tap point. **DONE 2026-07-20**
   (`src/dsp/InputBuffer.h`, `tests/InputBufferTest.cpp`; WDF C1/R2 HP, dsp-validator PASS).
2. ✅ **TrebleAttack** (stage 3): three switch positions validated against the nodal oracle
   (`treble_attack_tf` added to `eq_reference.py`). **DONE 2026-07-20** (`src/dsp/TrebleAttack.h`,
   `tests/TrebleAttackTest.cpp`, dsp-validator PASS). Realised as **MNA** (nodal + trapezoidal
   companion caps, one precomputed matrix inverse per position — equivalent to the dsp.md
   "precompute per topology, swap the matrix" rule) rather than a WDF tree, because R7∥ladder→M is
   a genuine loop, not a series/parallel tree. **⚠ TOPOLOGY CORRECTION during this step:** the
   ATTACK switch **pole = C8's bottom plate** (throws M / GND), NOT common=M — the old circuit.md
   reading grounded M and implied a Cut-position MUTE; corrected in circuit.md (see
   "ATTACK-SWITCH CORRECTION") after re-reading both schematics + a schematic-checker pass. Stage
   BOUNDARY (as decided, user-confirmed): the J201 drain (node G) is an **ideal voltage source**
   for Phase 4 (source Z = 0), loading absorbed into the J201 fit at Phase 7 capture; same
   convention in `eq_reference.py` and the stage. Positions differ topologically (cap bridge / cap
   shunt / open); `setAttack()` zeros C8's state on swap, glitch-free crossfade deferred to Phase 5.
3. ✅ **DriveStage** (IC2_A): ideal-op-amp decomposition; gain 4×–78× vs VR3; C-taper (fit per
   dsp.md; beware taper floor on the 100k). DC-step polarity test (non-inverting). **DONE
   2026-07-20** (`src/dsp/DriveStage.h`, `tests/DriveStageTest.cpp`, `drive_stage_tf` in
   `eq_reference.py`, dsp-validator PASS). Companion-model (trapezoidal C10 in the feedback leg,
   like TrebleAttack's MNA — maps 1:1 to the oracle), NOT a WDF tree. DC gains 4.164×/77.744×
   exact; FR ≤0.06 dB through 2 kHz all four DRIVE settings; top-octave deviation confirmed pure
   bilinear warp (shrinks 48k→96k, resolved by the Phase-6 OS region — C10 corner ~10.3 kHz is
   knob-INDEPENDENT so it's a clean prewarp candidate IF this stage ever runs base-rate, but it's
   inside the OS region so leave it). Taper reaches EXACTLY 0 Ω at full drive (dodges the §3 floor
   trap). **Shared `RailClamp` utility (`src/dsp/RailClamp.h`) landed here** (calibration §6:
   dead-linear→parabolic knee→hard clamp; disabled by default so linear tests stay valid) —
   this is the per-stage rail-clamp GATE item; apply it to every subsequent op-amp stage.
   ⚠ Two Phase-7 capture-fit carry-forwards (both flagged in-code, non-blocking): DRIVE taper
   SHAPE (`kTaperExp=1.5` interim — confirm direction + p vs a matched-pair drive capture) and the
   symmetric ±3.3 V rail estimate (real TL07x is asymmetric around VD, positive may clip first).
4. ✅ **RecoveryBridgedT**: unity buffer + passive bridged-T; notch validated at ~717 Hz vs
   `eq_reference.py`. **DONE 2026-07-20** (`src/dsp/RecoveryBridgedT.h`,
   `tests/RecoveryBridgedTTest.cpp`, dsp-validator PASS w/ full KCL re-derivation). Realised as
   **2-node MNA + trapezoidal companion caps** (same conventions as TrebleAttack; precomputed 2×2
   inverse) rather than a WDF ImpedanceCalculator — a bridge network isn't a series/parallel tree,
   and MNA maps 1:1 onto the oracle. Values kept as `constexpr` (tolerance-sensitive → capture-
   reshape at Phase 7). Test honoured BOTH caveats: (a) validated the ISOLATED stage against the
   UNLOADED oracle (`bridged_t_tf()` default; the R24→SK load is light + bootstrapped, deferred to
   the Phase-7 bridged-T→SK pair test — the oracle's Rload arg models Nout→GND, NOT the real
   series-into-high-Z topology, so it's only a sensitivity bound); (b) split assertions — notch
   FREQUENCY tight (±3%, landed 716 Hz), DEPTH loose (≤−20 dB, landed −28), ±0.25 dB only on the
   gentle shoulders, steep flanks + HF treated as bilinear warp (verified by 48k→96k shrink). FR
   matched oracle <0.02 dB through the notch. RailClamp on the buffer output (GATE), disabled by
   default. DC-step = unity/non-inverting. **⚠ real notch DEPTH still capture-validate — risk #1.**
5. ✅ **SallenKeyLPF (IC4_B + IC4_A, stage #6)**: two instances of a 2nd-order unity-gain Sallen-Key
   LPF. **DONE 2026-07-20** (`src/dsp/SallenKeyLPF.h`, `tests/SallenKeyLPFTest.cpp`). Built as MNA +
   trapezoidal companion caps (precomputed 2×2 inverse, consistent with TrebleAttack/RecoveryBridgedT).
   Validated against `analysis/eq_reference.py :: sallen_key_lpf_tf`: FR ≤0.25 dB through 2 kHz at
   48k (both instances), HF deviation = bilinear warp (shrinks 48k→96k for all frequencies).
   2nd-order asymptotic rolloff ~−12 dB/oct at 768 kHz (avoids warp in the measurement; the original
   4×/8× fc test at 192 kHz hit Nyquist-induced warp for IC4_B at 85.8 kHz, fixed by raising SR to
   768 kHz). DC-step unity non-inverting. RailClamp on each SK op-amp output (GATE, disabled by
   default). Both SKs sit inside the Phase-6 oversampled region — bilinear warp resolved there, no
   prewarp needed. ctest PASS (1/1).
6. ✅ **LevelBlend (VR2 LEVEL + VR1 BLEND, stage #7/8)**: passive resistive network with exact
   loading interaction between the two pots. **DONE 2026-07-20** (`src/dsp/LevelBlend.h`,
   `tests/LevelBlendTest.cpp`). Solved as a 1-node KCL: `Vw = (Vo/(1-L) + Vc) / (1/(1-L) + 1/L + 1)`
   for the LEVEL wiper, then `Vout = (1-B)*Vc + B*Vw` for the BLEND crossfade. LEVEL uses
   `powerLawTaper(x, 1.0, 1.43)` (interim power-law fit, p captured at Phase 7; note the real
   loading deficit at noon/noon is −1.82 dB with p=1.43, not the ideal-linear ≈3.5 dB cited in the
   old spec). BLEND is linear B-taper. `dist_engage` bool forces 100% clean output (the DIST
   footswitch override, crossfade smoothing deferred to Phase 6). No RailClamp needed (passive
   stage — no op-amp output). Validated against `analysis/eq_reference.py :: level_blend_tf`: DC
   gain matches oracle to ±0.001 dB across 7 knob-position pairs. ctest PASS (1/1).
   ⚠ **Two alignment risks at this summing node** deferred to Phase 6 (risk #8 below): (a) delay-
   mismatch crossfade comb-filters without the Phase 6 latency line; (b) aggregate polarity at the
   BLEND node depends on J201's unconfirmed sign + clipper's known inversion — an end-to-end DC-step
   test from input to BLEND is required before trusting the crossfade. Do NOT wire the BLEND
   crossfade until Phase 6.
7. ✅ **EQ block**: Baxandall (coupled BASS+TREBLE — ONE nodal network), LO-MID, HI-MID (each an
   inverting-unity + pot network stage; series cap switchable via live matrix recompute). **DONE
   2026-07-21** (dsp-validator PASS all 3 stages): `src/dsp/EqPreGain.h` (IC5_A buffer + IC5_B −2.2),
   `src/dsp/Baxandall.h` (IC5_C, 7-node MNA), `src/dsp/MidBand.h` (reusable IC5_D/IC6_A, 4-node MNA,
   switchable cap), sharing `src/dsp/MnaSolve.h` (templated NxN inverse, re-inverted only on a pot/
   switch dirty flag — never per sample, allocation-free). Validated every band at min/centre/max +
   both mid switches at all 3 caps (18 mid configs) against `analysis/eq_reference.py`: Baxandall
   ≤0.095 dB / MidBand ≤0.12 dB through 2 kHz; HF warp shrinks 48k→96k. 4-inversion net polarity
   confirmed by per-stage DC-step (IC5_B −2.2, Baxandall −0.926, LO/HI-MID −1 → net non-inverting).
   RailClamp on every op-amp output (GATE, disabled by default). ctest 11/11. ⚠ Phase-6 carry-forwards:
   (a) EQ HF caps (TREBLE ~5 kHz, HI-MID to 3 kHz) warp at base rate → cover with the oversampled-
   region span or prewarp; (b) C21(100n)/C31(2u2) inter-stage coupling caps excluded from the stages
   (oracle boundary) — place C21 (~150 Hz HP into the 10k stack, shapes bass) at the EqPreGain→
   Baxandall boundary at integration. Also fixed an `eq_reference.py` diagnostic-print bug (HI-MID
   peak scan used C32=22n not C34=6n8 → printed 405 not 728 Hz; the oracle function was always correct).
8. ✅ **MasterOut** (LAST linear stage — DONE 2026-07-21, dsp-validator PASS): [ENG] MASTER divider
   (VR8 100k A) + IC6_B unity buffer + C37/R47/R46 output HP; A-taper (`master^1.43` interim, Phase-7
   fit). `src/dsp/MasterOut.h` + `tests/MasterOutTest.cpp` + `master_out_tf`. Unloaded wiper (high-Z
   IC6_B) → pure resistive tap; two single-node MNA HPFs (C36→100k-to-VD, C37→R46), both ~0.72 Hz —
   NO audible-band caps, so ≤0.00024 dB vs oracle across the whole band and OUTSIDE the OS region.
   Unity at full CW; non-inverting, AC-coupled. RailClamp on IC6_B output (GATE, disabled by default).

**J201 stage (nonlinear #1)** comes after the linear chain around it works: implement as fitted
gain + soft waveshaper (nominal from Fairchild datasheet SPICE params; structure per
`docs/nonlinear-component-modeling.md` §2), with the C3/R6 source-bypass HF-gain rise and C4
bootstrap behaviour captured by the fit. Sine + DC-step polarity test; expect mild asymmetric
soft compression, NOT hard clipping.

> ✅ **DONE — STRUCTURE (2026-07-21):** `src/dsp/JfetStage.h` + `tests/JfetStageTest.cpp` +
> `jfet_stage_lin_tf` in `eq_reference.py` (dsp-validator run). Path-B Wiener-Hammerstein cascade:
> input HP (C2 into R4+R5=1.1M, fc 144.7 Hz — the gate draws no current so R5/(R4+R5) folds into
> G0) → HF-lift shelf (C3 bypassing R6: zero 219 Hz, pole 719 Hz, +10.3 dB lift = 1+gmR6) →
> **inverting** mid-band gain (−G0) → per-polarity tanh soft waveshaper (satPos/satNeg asymmetric →
> even harmonics; ADAA-ready antiderivative satN²·ln cosh). HP is a physical trapezoidal cap (same
> convention as MasterOut); the shelf is a first-order bilinear IIR (== trapezoidal). All corners
> sub-kHz → NO audible-band warp, matches the oracle ≤0.015 dB across the whole band 48/96k. **NET
> INVERTING confirmed by the DC-step test** — resolves circuit.md's "JFET sign unconfirmed"
> carry-forward (the OD path carries this inversion + the CD4049's into the BLEND node; end-to-end
> BLEND DC-step still runs in Phase 6). **NO RailClamp** (JFET, not an op-amp output — the waveshaper
> IS its soft limiting). **⚠ Phase-7 capture carry-forwards (all flagged in-code):** kG0 (mid-band
> gain), kGmR6 (shelf strength / HF lift), and kSatPos/kSatNeg (saturation levels / H2-H3 balance)
> are NOMINAL placeholders from the datasheet Shichman-Hodges self-bias point (Id≈0.12 mA, gm≈0.69
> mS) — FIT all to the drive-min OD-path captures (§4 "J201 stage" extraction; ~5:1 J201 part spread
> means nominal SPICE cannot match a specific unit). C4 bootstrap + R7 treble-net loading fold into
> G0 (Phase-4 boundary: node G is an ideal source per TrebleAttack.h; revisit output Z at Phase 7).

**Op-amp output-rail saturation (ALL op-amp stages — easy to forget because every stage above is
labelled "linear"):** calibration doc §6 requires an asymmetric output clamp (~[1.2, 7.8] V on the
8.6 V rail; dead-linear → short parabolic knee → HARD clamp, `setRailVoltages()`) on EVERY op-amp
output, and it is genuinely part of this pedal's sound: IC2_A at max DRIVE is ×78 and hits its own
rails BEFORE the 4049 does, and the mid stages can boost up to +28 dB. Implement the clamp as one
shared utility in this phase and apply it per stage as each is built; measure the worst-case node
per stage (calibration §6 "compounding gain"). Stages inside the Phase 6 OS region (IC2_A through
the SK filters) get their clamps oversampled + ADAA'd along with everything else; the EQ stages
(IC5_B/C/D, IC6_A) run at base rate — keep their clamps anyway (post-LEVEL signal usually sits
below the rails, but extreme boost settings do clip in the real unit) and give them the same
piecewise-antiderivative ADAA (≈0 CPU, dsp.md) rather than leaving a base-rate hard clamp to alias.

**GATE 4:** every linear stage's FR test in ctest and green; dsp-validator run per stage;
polarity verified per stage; rail clamp present on every op-amp output (a missing clamp is a gate
failure, not a refinement); J201 stage behaves plausibly (gain ~×10–30 region, soft).

### Phase 4b — Functional UI pass (routine; after GATE 4, before Phase 5)

Build the APVTS-bound centre pedal face now so Phase 5+ checks are interactive (see "UI timing"
above). Scope = the *functional* subset of Phase 8, not the polish:
- Data-driven face from `ui/b7k_texture_base.png` + `ui/component positions.csv` (base-texture px
  space, centre-anchored, blank-height = scale-to-width — `ui.md`). Composite the component PNGs
  (`T_Knob`, `switch_up/_Mid/_down`, `Footswitch_up/_down`, `blue_led_on/_off`) per the asset map.
- Bind every control to its APVTS param (`SliderParameterAttachment` etc.); switches use the
  confirmed position→value maps (`circuit.md`). ATTACK/GRUNT icon glyphs rendered procedurally
  (`juce::Path`); LO-/HI-MID text labels in Lexend Exa (embed the .ttf now).
- LEDs + bypass/DIST read the APVTS bools directly (`ui.md` metering note).
- Enough peripheral chrome to be usable (trims, OS strip) is fine but optional here.

**No formal gate** — this pass is a testing convenience. Its correctness is verified for real at
GATE 8 (headless scale renders, VU gate vs final makeup, label states). Don't spend Phase 8's
polish budget here; just get controls on screen and wired.

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

> **✅ DONE 2026-07-21.** Full chain assembled first (`src/dsp/PedalChain.h`, JUCE-free — all 14
> stages in verified order incl. the C21 100n inter-stage HP; `PedalChainTest` = 4 stability/
> polarity checks) then wrapped in `src/dsp/PedalDSP.h`: `juce::dsp::Oversampling<double>` FIR
> half-band over the OD region (JFET→SK), one instance per 2×/4×/8× (alloc-free switching), 1× =
> per-sample base rate. Clean-tap `juce::dsp::DelayLine` compensates the OS FIR latency (integer:
> 49/60/64 base samples at 2×/4×/8×), re-sized on factor change. `processBlock` picks realtime vs
> `render_oversampling` factor via `isNonRealtime()`, reports host latency via `setLatencySamples()`
> on change. JFET waveshaper gets 1st-order ADAA (ln-cosh antiderivative). AU auval PASS.
> **`OSValidationTest` (JUCE FFT console exe) is GATE 6:** BLEND=50% magnitude is factor-independent
> at LF (≤0.04 dB @ 80/200 Hz → delay comp exact — a delay bug would comb here); the 600/1500 Hz
> spread (≤0.43 dB) is the WANTED bilinear-warp accuracy gain (OD caps re-discretised at OS rate),
> not a delay error; aliasing floor drops 2×=−28 → 4×=−32 → 8×=−34 dB (oversampling working).
> **Deviations from the original plan below, all deliberate & documented in-code:**
> - **Item 2 — AccurateOmega N/A.** There are no chowdsp DiodePairT/omega solves in the path (D1/D2
>   are hard clamps that never conduct; both shapers are `std::tanh`). The omega4 gotcha / HQ lever
>   it implies simply doesn't arise here. ADAA applied to the J201 (memoryless, clean antiderivative)
>   only; the **CD4049 clipper VTC is inside an implicit RC-coupled Newton solve** → not a memoryless
>   map, so Esqueda 1st-order ADAA doesn't apply (state-space ADAA is out of scope) — its
>   antialiasing is carried by oversampling. See `PedalChain.h` "Anti-aliasing strategy".
> - **Item 1 — prewarp not yet added** to the base-rate tone/master caps (their audible-HF warp is a
>   flagged Phase-6/8 carry-forward from the EQ stages). Deferred with the low-OS top-octave restore
>   (item 3 OSFidelity) to the Phase-8 UI/polish pass; base default is 2× where warp is already small.
> - **Bypass delay-comp:** the processor bypass crossfade currently sums the pre-DSP dry copy against
>   the wet chain WITHOUT delay-comp — acceptable only because bypass is a hard A/B (the ~5 ms
>   crossfade is brief). If a click/comb shows on bypass toggle at high OS, route the dry copy through
>   the same latency (reuse `PedalDSP`'s delay line or add one in the processor). Flagged, not done.
> - **Items 3/5 partial:** aliasing measurement ✅ (OSValidationTest); PerfBenchmark CPU table,
>   full-random-automation NaN soak, and the explicit bypass-transition null are NOT yet written —
>   fold into the Phase 8/9 probe pass.
>
> **Original plan (for reference):**

1. OS region = J201 → clipper → recovery/bridged-T → SK filters (nonlinear + downstream HF caps);
   `postFn` pattern; base-rate stages get prewarp on fixed HF corners.
2. AccurateOmega provider everywhere (not omega4); ADAA (ln-cosh antiderivative) on the tanh VTC
   and the rail clamps; 1×/2×/4×/8× runtime factors + separate `render_oversampling`,
   glitch-free switching per dsp.md.
3. Aliasing measurement test (JUCE FFT console exe): sweep at high drive, assert aliasing
   components at 4× are below the harmonic floor by a documented margin; OSFidelity probe
   (build.md) for the low-OS top-octave restore decision.
4. **Wire up the BLEND (and bypass) delay-compensation line now** (dsp.md "Dry/wet phase
   alignment across the oversampled region"): a base-rate `DelayLine` on the clean tap sized to
   `getLatencyInSamples()`, updated in lockstep with OS-factor reinit; same line (or a second
   instance) compensates the bypass dry copy. This is the natural point to add it — the
   oversampler and its latency reporting now exist for the first time. Also report latency to the
   HOST: `setLatencySamples()` in `prepareToPlay` AND again whenever the runtime OS factor
   changes mid-session — host PDC and the internal dry-path delay are different problems (dsp.md
   "do NOT over-correct"); do both, conflate neither.
5. **Null/impulse test at BLEND=50%, swept across 1×/2×/4×/8×** — read the failure signature,
   don't just check "is there a notch": comb-filter notches that SHIFT with OS factor mean the
   delay line is missing/stale (fix per step 4); a broadband/mostly-flat cancellation or a null at
   the wrong BLEND setting that does NOT shift with OS factor means a sign/polarity mismatch in
   the OD chain instead (re-run the end-to-end DC-step test from Phase 4's LevelBlend note,
   starting with the J201 stage) — dsp.md gives both signatures explicitly. Repeat both checks for
   the bypass crossfade transition.

**GATE 6:** aliasing test green; 1× vs 8× FR delta documented; CPU per OS factor measured
(PerfBenchmark); BLEND and bypass null/impulse tests show neither OS-factor-dependent comb-filtering
NOR an unexplained broadband/sign-mismatch null; no NaN/Inf anywhere in a full-random-automation soak.

## Phase 7 — CAPTURE SESSION + full-chain integration + calibration

**Do the hardware capture session now if not already done** (`docs/nonlinear-component-modeling.md`
§4: two baselines + ~29 takes, `gen_test_signal.py` signal, `parse_capture()` filenames).
Then:

1. ✅ **DONE (2026-07-22)** — `OfflineRender` console exe mirroring `processBlock` exactly
   (`analysis/offline_render.cpp`, CMake target `OfflineRender`), plus `captures.py::render_args()`
   against its CLI and `analysis/render_smoke_check.py` proving the CLI→DSP mapping (EQ knob
   direction, mid-freq switch mapping, bypass, render/capture alignment).
2. Calibrate in the documented order (calibration doc): `kInputRef` from the capture rig anchor;
   THEN fit the 4049 VTC/rail + J201 shaper to the driven captures (control-isolation +
   matched-pair diffs); reshape the bridged-T to the measured notch (or lack of one — it's
   tolerance-sensitive); confirm mid-band boost ranges + GRUNT corners + taper shapes
   (two-point minimum per pot, matched-pair method for coupled ones); output makeup =
   level-match to captures (may exceed 1.0 — no headroom pad). Also confirm the TL07x rail-clamp
   levels against any capture that drives a stage into its rails (nonlinear doc §3 — the
   [~1.2, ~7.8] V estimates are ±0.5 V placeholders until then).
3. Decompose any residual level deficit per calibration doc §4 before touching constants.

**GATE 7:** A/B harness (`analyze.py`): 1/3-oct FR within target tolerance on the essential
matrix, swept-THD tracks, null depth documented, knob-tracking pass/fail table green for all
8 pots + 4 switches + DIST at the captured points.

## Phase 8 — UI

> **Note (2026-07-20):** the *functional* pedal-face UI is built earlier in **Phase 4b** (see "UI
> timing"). By the time Phase 8 opens, items 1–2 below are likely already done and bound — treat
> this phase as **finishing + verifying** them (calibration-dependent bits, gate) plus the
> peripheral chrome in item 3, not building the face from scratch. If Phase 4b was skipped or
> deferred, Phase 8 builds the whole thing as originally written.

1. **Centre pedal face from the provided base image + CSV** (positions/sizes; layout is
   data-driven, not hand-placed — see `ui.md` "Centre pedal face"). Confirm the CSV schema when it
   arrives before building the layout parser. No bypass label needed (already on the base image).
   Element set (8 knobs — MASTER/LEVEL/BLEND/DRIVE top, LO/LO-MID/HI-MID/HI bottom; 2 footswitches
   bypass+DIST; ATTACK/GRUNT 3-pos toggles; 2 mid-freq selectors; LED per footswitch) follows
   `ui/ui-replacements.md` prep rules (2× res, crop-don't-stretch, alpha-safe rotation) for any
   individual component PNGs composited against the base image. **If the base image + CSV haven't
   arrived when Phase 8 opens, don't stall the build:** do items 2–4's peripheral/chrome work
   first (asset-independent) and leave the centre face as a placeholder — Phase 9 doesn't depend
   on the face layout.
2. **Switch-label text** (`ThreePositionSwitch`, the only pedal-face element that renders text):
   embed **Lexend Exa** as binary data and load via `Typeface::createSystemTypefaceFor()`; update
   `cSWLabelActive`/`cSWLabelInactive` to opaque-white/semi-opaque-white (replacing the current
   light-/dark-blue constants) — see `ui.md` for the exact spec. Do not apply Lexend Exa to
   peripheral chrome text (OS strip, trims, tooltips) — that stays on the existing default font.
3. Peripheral chrome from `src/ui/` (PedalLookAndFeel, VUMeter, trims + Trim Link, OS strip,
   scale) per `docs/ui-peripheral-spec.md` + ui.md (tooltips 2-dp, trim readout labels,
   selector visual language, resize persistence with debounced default-save). Apply the VU
   idle-noise gate and re-check its threshold against the FINAL Phase 7 makeup value
   (calibration §7 — the idle floor moves with makeup, so re-verify if Phase 9 changes it).
4. Headless editor render test (build.md) at 0.5×/1×/2.5×; VU/trim bounds check at extremes;
   verify the embedded Lexend Exa renders (not silently falling back to a system font).

**GATE 8:** headless renders correct at all scales; params bind; bypass/DIST LEDs track APVTS
directly; no drawing outside LookAndFeel; switch labels render in Lexend Exa with correct
opaque/semi-opaque selected/unselected states.

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
8. **BLEND/bypass phase cancellation — TWO distinct causes, don't fix one and assume it's solved:**
   (a) *delay*: the clean tap (BLEND) and dry copy (bypass) both split off before the oversampled
   region; without a delay line matched to `getLatencyInSamples()`, the crossfade comb-filters at
   every BLEND position, not just visibly in an FR plot but audibly (this exact bug cost a past
   project real debugging time). (b) *polarity*: independent of delay, the OD path reaching BLEND
   already carries one confirmed inversion (the clipper) plus an unconfirmed one (the J201 stage's
   sign) — a per-stage-only DC-step regime can miss an aggregate sign error at the BLEND node
   itself. Phase 6 now builds and null-tests both explicitly, with distinct failure signatures
   (dsp.md) — do not let Phase 4's LevelBlend stage get marked done without both checks (see that
   stage's note).
9. **Op-amp rail clipping is unscheduled by default** — every stage in the Phase 4 table is
   labelled "linear", which made it easy for the original plan to omit TL07x output clamps
   entirely (it did — fixed in the 2026-07-20 review). IC2_A at ×78 rails BEFORE the clipper;
   the mids can boost +28 dB. Phase 4's rail-clamp paragraph schedules it; a missing clamp is a
   gate-4 failure.
10. **LEVEL→BLEND loading** — the two pots are NOT independent ideal dividers (finite LEVEL-wiper
    source impedance → −1.82 dB crossfade imbalance at noon/noon with the interim power-law taper
    p=1.43; ≈3.5 dB if the taper were linear at L=0.5); model the resistive network exactly (Phase
    4 item 6 — DONE), validate against the blend captures at Phase 7.
11. **Phase 8 asset dependency** — the centre-face base image + CSV come from the user; chrome
    work proceeds without them (Phase 8 item 1 note) so the build never blocks on an external
    deliverable.
