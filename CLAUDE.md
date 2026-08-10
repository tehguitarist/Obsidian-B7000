# Obsidian-B7000 — Project Memory

> Obsidian-B7000 is a circuit-level emulation of the **Darkglass B7K Ultra** bass overdrive/DI
> preamp, built as an AU/VST3 plugin using JUCE 8+ and chowdsp_wdf. Author/Company: Leigh Pierce.

## Quick reference

```
Build:  cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build
AU:     cmake --build build --target ObsidianB7000_AU   (auto-installs; bump VERSION to force a Logic rescan)
Tests:  ctest --test-dir build --output-on-failure -j 12          # 22/22; never bare ctest
Format: clang-format -i src/**/*.{cpp,h}
```

## Schematics

The schematic images are in `schematics/`; `.claude/rules/circuit.md` is the source of truth for
component values and topology. Use the `schematic-checker` agent for any circuit value or topology
question, and `dsp-validator` after any DSP stage change.

@.claude/rules/circuit.md
@.claude/rules/dsp.md
@.claude/rules/architecture.md
@.claude/rules/ui.md
@.claude/rules/build.md

## Essential reading

- **`docs/nonlinear-component-modeling.md`** — the two non-WDF-native parts, the CD4049UBE clipper
  and the J201 JFET stage: datasheets/papers/SPICE and the modelling approach used for each.
- **`docs/calibration-and-gain-staging.md`** — `kInputRef` calibration, output-makeup calibration,
  pot-taper fitting, internal-vs-output clipping, op-amp rails, VU idle gate.
- **`docs/validation-and-capture.md`** — how the plugin is measured against a reference: FR, swept
  THD, per-order harmonics, null depth, and the capture protocol.
- **`analysis/`** — the reusable A/B validation harness (`gen_test_signal.py` + `analyze.py`, plus
  `comprehensive_report.py`, `matrix_grade.py`, `shape_gate.py`, `fit_nonlinear.py`). See
  `analysis/README.md`.
- **`docs/ui-peripheral-spec.md`** / **`src/ui/`** / **`src/utils/TaperUtils.h`** — UI spec, the
  reusable peripheral elements (side panels, knobs, VU meters, oversampling strip), taper helpers.

## Architecture

Single signal chain with a parallel clean tap for BLEND (full detail in `circuit.md`):

```
IN → input buffer → J201 JFET gain stage → treble/ATTACK ladder → DRIVE gain stage
   → GRUNT coupling bank → CD4049UBE clipper (the distortion source) → OD coupling
   → recovery buffer + bridged-T → two Sallen-Key lowpass sections → LEVEL → BLEND (mixes
   with the clean tap) → EQ (BASS/TREBLE Baxandall, switchable LO-MID/HI-MID) → MASTER → OUT
```

Per-stage implementations live in `src/dsp/` (one header per stage; `PedalChain.h` wires them
together, `PedalDSP.h` is the per-channel wrapper). `MASTER` volume, the 3-way `ATTACK` switch, and
the switchable mid-band frequencies are **engineered additions** (tagged `[ENG]` in `circuit.md`) —
the schematic on hand is the original B7K, and these behaviours are built to match the Ultra's
documented control surface rather than a verified Ultra schematic. Everything else is
schematic-verified.

Two footswitches: main true bypass, and a second `dist_engage` that mutes only the overdrive branch
(forces the BLEND crossfade to 100% clean) without disturbing the EQ/MASTER/output stage.

## Fitted constants

Component values follow the schematic except where a fit against the reference measurements
required otherwise. Current shipped values (see the named header for derivation and any per-switch
variants):

| Constant | Value | File |
|---|---|---|
| `c21R` | 130 kΩ | `FitParams.h` |
| `jfetSatNeg` | 1.9 | `FitParams.h` |
| Treble/ATTACK ladder (17 constants) | fitted set, not drawn values | `FitParams.h` |
| `kInputRef` | 0.90 | `FitParams.h` |
| `kOutputMakeup` | 4.3297 | `FitParams.h` |
| D1/D2 clamp window | derived from `kTripPointV` = 2.657 | `Clipper.h` |
| Clipper solve | bracketed Newton + bisection (`rtsafe`) | `Clipper.h` |
| `clipK` | 2.0 (ADAA anchor) | `FitParams.h` |
| `clipAdaa` / `clipAdaaMaxOs` | Full / OS ≤ 2 | `FitParams.h` |
| MASTER taper | 3-segment PWL (`masterTaperBreak`/`Frac`, `Break2`/`Frac2`) | `FitParams.h`, `MasterOut.h` |
| `OdToneRestore` | mix-keyed RBJ peaking biquad at 323 Hz, per-GRUNT gain/Q/mix tables | `OdToneRestore.h` |
| LEVEL taper | 4-segment PWL (`levelTaperBreak1..3`/`Frac1..3`) | `FitParams.h`, `LevelBlend.h` |
| `OdDriveTilt` | envelope-driven RBJ high-shelf, f0=5388 Hz S=0.85 dbPerDb=0.203 maxCut=6.0 dB | `OdDriveTilt.h` |
| `OdMakeup` | OD-branch makeup + low/high shelves + notch depth offset; low/high corners and Cut-side values differ by GRUNT position | `OdMakeup.h`, `FitParams.h` |
| `C31` (2.2 µF) | fifth MNA node in the LO-MID stage, enabled | `MidBand.h`, `FitParams.h` |
| `blendEndStop` | 0.02418 | `LevelBlend.h`, `FitParams.h` |
| Switch crossfade | 20 ms dual-instance shadow crossfade on ATTACK/GRUNT/LO-MID/HI-MID | `SwitchFade.h`, `PedalChain.h` |

## Testing

`ctest --test-dir build --output-on-failure -j 12` — 22/22. Per-stage tests validate each WDF stage
against the closed-form oracle in `analysis/eq_reference.py`; `ClipperTest`/`JfetStageTest` cover
the two nonlinear stages; `OSValidationTest`/`OSFidelity` cover oversampling and aliasing;
`SwitchTransitionTest` covers the switch crossfades; `FinalSweepTest` is a full control sweep (every
switch combination × DRIVE × BLEND × LEVEL × oversampling factor) asserting no NaN/Inf/instability;
`PerfBenchmark` measures CPU/latency per oversampling factor (`RUN_SERIAL` — the one exception to
running tests in parallel, since it measures wall-clock).

The `analysis/` harness (see `analysis/README.md`) runs a full A/B against reference captures: FR
shape, swept THD, per-order harmonics, and null depth.

## Known limitations

- The overdrive path reads quiet relative to the reference validation target, worst at GRUNT
  flat/boost. A clipper-headroom fix was investigated and found not to fit inside the pedal's own
  9 V supply rail — this is now understood to be a structural limit, not open work.
- 6 of 14 gated accuracy rows are over their agreed target (down from 9 at the 1.0.0 release).
- The XLR balanced DI output is not modelled.

## Open items

- The ~800 Hz bridged-T notch depth and the bass-peak frequency don't fully track the DRIVE knob.
  Lowest priority — both need a genuinely new mechanism candidate before further measurement is
  useful; the existing candidate search for each is exhausted.
