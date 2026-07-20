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
> **CURRENT: Step 4 (stage-by-stage linear DSP) — IN PROGRESS (2026-07-20).**
> Phase completion tracking in `docs/build-plan.md` §"Where we are" — update both files.
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
> **⚠ ATTACK-SWITCH TOPOLOGY CORRECTED THIS SESSION** (found while building the oracle): circuit.md's
>    "triple-checked" node graph had the switch **pole** wrong (named node M as common → implied a Cut
>    MUTE). Verified from primary+backup schematics + schematic-checker: **pole = C8 bottom plate**;
>    Boost→C8 bridges R8, Cut→C8 shunts P→GND (treble cut, no mute), Flat→open. circuit.md + this file's
>    UI-map carry-forward corrected; `treble_attack_tf` in `eq_reference.py` implements the fix.
> **STILL TODO in Step 4:** SallenKey ×2 → LevelBlend → EQ block → MasterOut, THEN the J201 nonlinear
>    stage. RailClamp now exists — apply it to each remaining op-amp stage as built (calibration §6,
>    GATE item). (Build-plan Phase 4.)
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
> **NEXT: SallenKey ×2** (IC4_B ~10.7 kHz → IC4_A ~3.3 kHz), build-plan Phase 4 item 5. Two
> instances of a textbook 2nd-order unity-gain Sallen-Key LPF, different values:
>   • IC4_B: R24 10k / R25 22k, C27 1n (→GND) / C18 1n (feedback) → fc ≈ 10.7 kHz.
>   • IC4_A: R26 22k / R27 47k, C20 1n (→GND) / C19 2n2 (feedback) → fc ≈ 3.3 kHz (final OD bandlimit).
> These are the last stage of the OD chain before LEVEL/BLEND. No oracle exists yet — add a
> `sallen_key_tf(f, R1, R2, C1, C2)` to `eq_reference.py` (standard SK transfer fn) and validate FR
> +2nd-order rolloff/Q vs it (same 48k/96k bilinear-warp split as the other stages; the SK corners
> are lower than the bridged-T so top-octave warp will show — assert tight ≤2 kHz, shrink 48k→96k
> above). Build via MNA + trapezoidal companion caps (consistent with TrebleAttack/RecoveryBridgedT;
> a unity-gain SK is a clean 2-node solve) OR chowdsp WDF — pick MNA for oracle 1:1. Apply `RailClamp`
> to EACH SK op-amp output (GATE item, disabled by default). ⚠ Both SKs sit INSIDE the Phase-6
> oversampled region (dsp.md OS-region rule) — their bilinear warp is resolved there, so don't
> prewarp-fight it in the base-rate test. After both SKs: LevelBlend (build-plan item 6 — the
> asymmetric-crossfade + dual phase-alignment risks; do NOT wire the crossfade before Phase 6's
> delay-comp), then the EQ block, MasterOut, then the J201 nonlinear front-end.

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
  (~29 essential takes, deviation-from-REF-OD-baseline filenames) = `docs/nonlinear-component-modeling.md`
  §4. Parser `parse_capture()` added to `analysis/analyze.py` (8 pots + 4 three-way switches + DIST,
  tested against the whole matrix). Missing DC/rail values → take nominal from datasheets, calibrate
  the clip ceiling to the bypass+drive captures.
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
