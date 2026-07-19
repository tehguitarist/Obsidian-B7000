# Non-linear / non-WDF-native component modeling — sources & plan

> Compiled 2026-07-19 (pre-build research pass). Purpose: for every component in the B7K Ultra
> signal path that **chowdsp_wdf cannot model natively**, gather the datasheets / papers / SPICE /
> implementations we need *before* writing DSP, so we fit to real data instead of guessing later.
> Local copies of the load-bearing PDFs live in `docs/refs/`.

## What needs external modeling data (and what doesn't)

| Component | WDF-native? | Notes |
|-----------|-------------|-------|
| All R, C, bridged-T, Sallen-Keys, EQ networks | ✅ yes | plain R/C — `ResistorT`/`CapacitorT` |
| TL072ACP / TL074ACN op-amps | ✅ (ideal op-amp + rail clamp) | only external datum = single-9V output swing (see §3) |
| D1/D2 1N4148 | ✅ `DiodePairT` | params already in `circuit.md` (Is=2.52e-9, Vt=25.85e-3, n=1.752) |
| **IC3 CD4049UBE** (clipper) | ❌ **NO native model** | **the** distortion nonlinearity — see §1 |
| **Q1/Q2 J201** (JFET gain stage) | ❌ **NO native model** | active gain stage — see §2 |
| D3 1N5817, D4 LED | n/a | supply/status, not in signal path |

Only **two** component types genuinely need us to supply a model: the **CD4049UBE clipper** and the
**J201 JFET stage**. Both are addressed below with sources + a recommended approach + what to capture.

---

## 1. CD4049UBE CMOS-inverter clipper (IC3)

The single inverter section, wired as a shunt-feedback inverting amp (R16 6k8 in, R18 330k∥C14 220pF
fb, self-biased ~VDD/2, +9V rail ≈8.6V). It clips against its own 0…VDD rails (soft). **This is the
audible distortion source** — model its transfer curve, not the D1/D2 clamps.

### Load-bearing resources
- **★ DAFx-2020 "Taming the Red Llama" (Köper & Holters)** — models *exactly* this device (one
  unbuffered CD4049 section as a 9V shunt-feedback overdrive). Local: `docs/refs/DAFx2020_Taming-the-Red-Llama_CD4049-overdrive-model.pdf`.
  Code: https://lkoeper.gitlab.io/dafx-2020-cmos-llama/ · model merged into ACME.jl: https://github.com/HSU-ANT/ACME.jl
  - Provides a **measured 9V VTC** (their Fig 13 — the curve the datasheet lacks) and a fitted
    two-MOSFET Shichman-Hodges model. **Simple-model params (VDD=9V, per section):**
    - n-ch: α≈5.1021e-3, vT(VTO)≈1.5702 V
    - p-ch: α≈8.2246e-4, |vT|≈0.48476 V, λ(LAMBDA)≈0.06 V⁻¹
  - **Extended model** (their real contribution): α and vT made functions of vGS (Table 3) + p-ch
    channel-length modulation — matches the real pedal in a MUSHRA test. Use this as the
    **ground-truth curve generator** to fit our smooth waveshaper against.
  - Solver is DK-method state-space (NOT WDF, NO ADAA) — the *model* is gold, the numerics we redo.
- **TI CD4049UB datasheet SCHS046L** — local: `docs/refs/TI_CD4049UB_datasheet_SCHS046L.pdf`.
  - **Fig 5-1** = min/max VTC (Vo vs Vi) but **only at VCC=5V** and as tolerance envelopes (trip at
    ~1V and ~4V bracket the *spread*, not a typical curve — typical trip ≈ VCC/2).
  - **Figs 5-3…5-6** = the N/P MOSFET I-V families (what DAFx fit).
  - Rails: VOH≈VCC−0.05, VOL≈0.05 → clip window ≈ 0…8.6V (≈±4.3V around the self-bias). CIN≈15pF.
  - No 9V VTC, no small-signal gain spec in the datasheet → get those from DAFx / capture.
- **No usable off-the-shelf analog SPICE subckt.** The common SparkFun `CD4000_v.lib` `CD4049B` is a
  *behavioural digital* macromodel (switching only, no soft clip) — do NOT use for distortion. TI's
  PSpice model is likewise digital/timing. Correct SPICE route = build the inverter from 2 generic
  MOSFETs and use the DAFx params above.
- Community corroboration (asymmetric clipping + open-loop gain ≈25–30 measured on real B3K/B7K
  CMOS stages): freestompboxes.org threads t=25589, t=31600. AionFX clone traces:
  maelstrom_documentation.pdf, yacana_documentation.pdf.

### Recommended approach (WDF-compatible)
Model IC3 as a **static asymmetric-sigmoid VTC waveshaper inside the ideal-op-amp shunt-feedback
decomposition** we already use (R16 input, R18∥C14 fb, D1/D2 as hard clamps at node W).
- Fit the VTC with an **asymmetric tanh/logistic** (different slope/saturation per side to get the
  N/P asymmetry) — closed-form, and **∫tanh = ln cosh** gives a clean 1st-order ADAA antiderivative.
  Fit it against the DAFx extended model's swept VTC (or our own 2-MOSFET SPICE sweep), then against
  the real-unit capture (§4).
- **Asymmetry → even harmonics is intrinsic and required** (n-ch vT≈1.57 vs |p-ch vT|≈0.48; α differs
  ~6×). Fit it from a capture — don't just bolt on a token mismatch `m`.
- Scale the curve to the clipper's ACTUAL rail, which is **below 8.6V**: R19 (1k, located 2026-07-19)
  sits in series between the +9V rail and IC3's VDD pin — the only IC with a supply dropper. The
  unbuffered 4049's class-A linear-region current (mA-scale) drops ~0.5–3V across it, so the clip
  ceiling is lower AND softer than the op-amp rail, with signal-dependent sag (compression), exactly
  the Red Llama trick. **Calibrate the ceiling to the bypass+drive captures** (the static drop is
  absorbed by the fit); dynamic sag is an optional refinement — try static first, add a simple
  supply-sag state (VDD_eff = 8.6 − I_DD(Vout)·1k, one-pole smoothed) only if captured feel demands it.
- The 4049's **finite open-loop gain (~20–30) is part of the voicing**: the GRUNT HPF corners depend
  on the input node's impedance R18/(1+A0) (sim 2026-07-19: ideal-virtual-ground corners 4.98k/453/104
  Hz vs ~1.5–1.9k/137–177/32–41 Hz at A0≈20–30). Model R16 + GRUNT bank + the fitted finite-gain VTC
  as one coupled stage, and verify the three GRUNT corners against captures after fitting A0.
- Oversample (hardest nonlinearity in the chain) + ADAA per `dsp.md`. Keep C14∥R18 and the GRUNT cap
  bank in the linear WDF part.
- Escalate to a full 2-MOSFET Newton solve at the WDF root **only if** the static fit fails to match
  captured harmonics across drive settings (no one has done this CMOS stage in WDF — it'd be new).

---

## 2. J201 JFET gain stage (Q1 common-source + Q2 active load)

Mildly-nonlinear active gain front-end. chowdsp has no JFET element. **The J201 is spread ~5:1
part-to-part** (Vgs(off) −0.3…−1.5V, IDSS 0.2…1.0mA) — nominal SPICE will not match a specific unit,
so **fit to the captured unit**.

### Load-bearing resources
- **Fairchild/onsemi J201 datasheet** — local: `docs/refs/Fairchild_J201_datasheet.pdf`. Vgs(off)
  −0.3…−1.5V, IDSS 0.2…1.0mA (both ~5:1 spread — this is why VTO must be fitted, not assumed).
- **SPICE `.MODEL` sets** (short factual data — quoted so we have them offline):
  - *Datasheet-derived "classic" (nominal starting point):*
    `.MODEL J201 NJF(VTO=-0.718 BETA=1.031M LAMBDA=2M IS=114.5F RD=1 RS=1 CGD=4.667P CGS=2.992P M=.2271 PB=.5 FC=.5 VTOTC=-2.5M BETATCE=-.5 KF=604.2E-18)`
    (PedalPCB/DIYstompbox community, datasheet-fit).
  - *LTspice factory pair (useful A/B for the spread):*
    `J201-GEN: VTO=-0.6 BETA=1.6m LAMBDA=2.2m RD=1 RS=1 CGS=3p CGD=4.7p`
    `J201-LS : VTO=-0.93 BETA=1.1m LAMBDA=6.8m RD=10 RS=12 CGS=1p CGD=1p`
    (LTwiki Standard.jft).
  - Consensus: BETA≈1.0–1.6mA/V², LAMBDA≈2m, RD/RS≈1, CGD≈4.7p/CGS≈3p. **VTO is the disagreement**
    (−0.6…−0.93 quoted; datasheet allows −0.3…−1.5) → **fit it**.
  - Curve-fit tool (method reference): dvhx/jfet-model-maker (level=2 model, not hand-eval-ready).
- **WDF modeling papers:**
  - **★ Bernardini et al., "WD Modeling of Nonlinear 3-terminal Devices" (CSSP 2019)** — WD models
    for JFET/MOSFET/BJT; JFET drain current as a **3rd-order polynomial → explicit closed-form wave
    scattering** (no per-sample Newton for the device). *The* reference for a JFET one-port in WDF.
    URL: https://re.public.polimi.it/bitstream/11311/1156955/1/WD3Terminal_Bernardini_RG.pdf
    (Springer: https://link.springer.com/article/10.1007/s00034-019-01331-7) — not saved locally
    (mirror 404'd); grab from Springer/ResearchGate if we go the coupled-solve route.
  - FPGA JFET WDF (Hernández/Hsieh) — CS-amp + JFET preamp case studies validated vs SPICE:
    https://www.semanticscholar.org/paper/402c083a0263e09d64fe40b97b5e19263dd8c2f4
  - **DAFx-2024 MXR Phase 90 (JFET as time-varying resistor)** — local:
    `docs/refs/DAFx2024_MXR-Phase90_JFET-timevarying-resistor-WDF.pdf`. Note: models JFETs in the
    *voltage-controlled-resistor* regime (not a driven CS amp) — a cheap-approximation reference,
    less directly applicable to our overdriven gain stage.
  - RT-WDF (Werner, DAFx 2016) — placing a nonlinear 3-terminal device at an R-type root (triode
    case study = analogue of our CS stage).
- No drop-in open-source J201 CS-overdrive WDF exists. Prototyping: pywdf (Python), Faust wdmodels.

### Recommended approach (WDF-compatible)
**Path B — fit the whole Q1/Q2 block to captures (recommended):** input HP (C2/R4+bias) → a
**frequency-dependent gain** (capture the C3-bypass HF lift) → a **static asymmetric soft-waveshaper**
fit to the measured transfer curve → downstream treble net. Memoryless-ADAA-friendly, cheap,
per-unit-calibratable. Matches `dsp.md`'s "fitted gain + soft-waveshaper" option and our
capture-before-model discipline. The J201 spread means even a perfect topology needs a per-unit fit
anyway, so start here.
**Path A — full coupled 2-device WDF solve (fallback):** Bernardini cubic-JFET one-ports + a chowdsp
R-type root resolving Q1 (CS nonlinearity) loaded by Q2 (active load, gate AC-bootstrapped via C4).
Higher CPU + a genuine multi-nonlinearity Newton solve. Only escalate here if capture A/B shows the
static model misses audible dynamics (bias-shift/blocking distortion) — unlikely to dominate since
the CD4049 clipper downstream does most of the distorting.

---

## 3. TL072ACP / TL074ACN op-amp rails (minor)

WDF-native (ideal op-amp + output saturation clamp). Only external datum: **single-9V output swing**.
TL07x is **not** rail-to-rail — output swings to within ~1.2–1.5V of each rail, asymmetric (worse
toward the negative rail). `circuit.md`'s [~1.2V, ~7.8V] estimate is reasonable. **Confirm the exact
clip level by capturing a stage driven into its rails** (calibration doc §6) rather than trusting the
nominal — no SPICE model needed, it's just a clamp.

---

## 4. Capture plan — real B7K **Ultra**, audio-only (¼" in → ¼" out)

**Target unit = a real Darkglass B7K Ultra; captures are audio in→out only (no internal probing /
no DC values).** Two consequences: (a) we can **capture & validate the [ENG] features directly** —
Master taper/placement, 3-way Attack, DIST footswitch, and the switchable mid frequencies
(including the extrapolated 750 Hz Hi-Mid); (b) both nonlinear models and the IC2_B notch are
**inferred from composite in→out captures** (control-setting isolation + matched-pair differencing,
`dsp.md`), which is exactly what the `analysis/` harness is built for. Filenames use the parser
`parse_capture()` in `analyze.py` (deviation-from-baseline naming).

### Setup rules (from `validation-and-capture.md` §3)
- `python3 analysis/gen_test_signal.py` → play `analysis/test_signal_48k.wav`, one take per row.
- **Fix interface gain for the whole session; never touch it.** Reamp at a fixed bass-representative
  level (this sets `kInputRef`). 48 kHz / 32-bit float, no interface clipping, full-length files.
- **Bypass pass FIRST** (level anchor). One control at a time; hold all others at baseline.

### Two baselines (filenames state only the DEVIATION from these)
- **REF-OD** = `Master noon · Blend FULL OD (CW) · Level noon · Drive noon · Bass/Treble/LoMid/HiMid
  noon · Attack FLAT · Grunt MID · Lo-Mid-freq 500 · Hi-Mid-freq 1.5k · DIST ON`.
- **REF-CLEAN** = REF-OD but **DIST OFF** (forces 100% clean path → EQ sees an undistorted signal).
  Used for all EQ / mid-freq / Master reads.

### Tier 1 — Essential (~29 takes)
| Filename | Deviation | Pins |
|----------|-----------|------|
| `bypass.wav` | true bypass | **level anchor (kInputRef)** — first |
| `ref-od.wav` / `ref-clean.wav` | — / DIST off | OD & clean references + DIST-footswitch check |
| `drive-0700/0930/1430/1700.wav` | Drive | **CD4049 clipper** amount + harmonics |
| `grunt-lo/hi.wav` | Grunt | pre-clip bass content |
| `attack-boost/cut.wav` | Attack | **3-way Attack [ENG]** + treble net |
| `bass-0700/1700`, `treble-0700/1700`, `lomid-0700/1700`, `himid-0700/1700` (+`dist-off`) | one EQ band cut/boost, clean | EQ tapers |
| `lomidfreq-250/1k.wav` (Lo-Mid gain MAX, `dist-off`) | Lo-Mid freq selector | **switchable Lo-Mid centers [ENG-caps]** |
| `himidfreq-750/3k.wav` (Hi-Mid gain MAX, `dist-off`) | Hi-Mid freq selector | **Hi-Mid centers — validates the 750 Hz guess** |
| `blend-0700/1200.wav` | Blend | crossfade taper |
| `level-0700/1700.wav` | Level | LEVEL taper |
| `master-0700/1700.wav` (`dist-off`) | Master | **Master taper/placement [ENG]** |

### Tier 2 — Extended (if time)
- Fill each sweep to 5 points (add `0930`/`1430`) for Drive, EQ bands, Blend, Level, Master.
- Mid-freq selectors at **cut** as well as boost (two-sided → tighter center fit).
- Drive×switch cross-terms: `drive-1700 grunt-hi.wav`, `drive-1700 attack-boost.wav`.
- (The middle of every 3-way — grunt-mid, attack-flat, both mid-freqs — is already `ref`.)

### How each model / the notch is extracted (audio-only)
- **CD4049 clipper waveshaper** ← Drive sweep + the signal's driven Farina sweeps (continuous
  THD(f)) + low-freq tones (H2/H3/H4 asymmetry). Fit the asymmetric-tanh VTC to this, DAFx model as
  the prior shape.
- **J201 stage** ← at Drive-min the clipper barely clips, so the OD path's mild nonlinearity ≈ the
  JFET stage; the level-step segments (input sweep) at low drive show its compression onset.
- **IC2_B ~720 Hz notch** ← compare the clean sweep through `drive-0700` (DIST on, OD path) vs
  `ref-clean` (DIST off, OD path bypassed), EQ flat in both; the difference is the OD-path-only
  linear shaping. **No probing required.**

### The electrical-values gap & workaround
Without probing we can't measure DC bias or exact rail-clip voltages. Take them as **nominal** from
the datasheets (rail ≈8.6 V, TL07x swing ≈[1.5, 7.5] V, CD4049 VTC from DAFx), then **calibrate the
effective clip ceiling to the `bypass`+`drive` captures** — the model's rail/clip level is fit to the
measured onset-of-clipping and output level (what actually matters audibly), recovering the missing
electrical values indirectly from audio.

---

## Local reference files (`docs/refs/`)
- `TI_CD4049UB_datasheet_SCHS046L.pdf` — VTC (Fig 5-1, 5V), MOSFET I-V (5-3…5-6), rails.
- `DAFx2020_Taming-the-Red-Llama_CD4049-overdrive-model.pdf` — the CD4049 overdrive model + params.
- `Fairchild_J201_datasheet.pdf` — J201 DC params + spread.
- `DAFx2024_MXR-Phase90_JFET-timevarying-resistor-WDF.pdf` — JFET-in-WDF (VCR regime) reference.
- Bernardini 3-terminal WDF paper — **not** saved (fetch from Springer/ResearchGate if going Path A).
