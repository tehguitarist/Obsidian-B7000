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
`dsp.md`), which is exactly what the `analysis/` harness is built for.

### Setup rules (from `validation-and-capture.md` §3)
- `python3 analysis/gen_test_signal.py` → play `analysis/test_signal_48k.wav`, one take per row.
- **Fix interface gain for the whole session; never touch it.** Reamp at a fixed bass-representative
  level (this sets `kInputRef`). 48 kHz / 32-bit float, no interface clipping, full-length files.
- **Bypass pass FIRST** (level anchor). One control at a time; hold all others at baseline.
- **Name each file EXACTLY per the grammar below — no free-text notes, no spaces, no shorthand.**
  `analysis/captures.py::parse_capture()` implements this grammar and will reject (loudly, with a
  specific reason) anything that doesn't match — run `python3 analysis/captures.py` (no captures on
  disk yet → it self-validates the matrix below) before and after recording to catch a typo early
  rather than discovering it mid-fit.

### Two baselines
- **REF-OD** = `Master noon · Blend FULL OD (CW) · Level noon · Drive noon · Bass/Treble/LoMid/HiMid
  noon · Attack FLAT (physical up) · Grunt physical-MID (= electrical Cut) · Lo-Mid-freq 500 Hz
  (physical up) · Hi-Mid-freq 1.5 kHz (physical up) · DIST ON`.
- **REF-CLEAN** = REF-OD but **DIST OFF** (forces 100% clean path → EQ sees an undistorted signal).
  Used for all EQ / mid-freq / Master reads.

### Capture filename grammar (exact — matches `analysis/captures.py::parse_capture()` 1:1)

Every filename is either one of **three reserved baseline names**, or an **underscore-joined list
of `key-value` deviation tokens** ending in a **required trailing `base-od` / `base-clean` token**
that states — explicitly, every time, no exceptions — which baseline every *unlisted* control sits
at. There is deliberately no separate "dist-off" token: DIST state is fully determined by
`base-od`/`base-clean` (REF-CLEAN differs from REF-OD by DIST alone, so the base token already says
it). If a control matters for a given capture, it gets a token; nothing is implied by context or a
parenthetical note.

**Reserved (zero-deviation) filenames:** `bypass.wav`, `ref-od.wav`, `ref-clean.wav`, plus their
gain-session variants `ref-od_gain-<tok>.wav` / `ref-clean_gain-<tok>.wav` (see the `gain` key
below) — still zero *other* deviation, so no trailing `base-*` token.

**Pot keys** (value = 4-digit clock code, `0700`=min … `1200`=noon … `1700`=max, linear between —
`captures.py::_clock_to_x`, same convention as `analyze.py::clock_to_x`):

| Filename key | PedalChain::Params field | Real control |
|---|---|---|
| `drive` | `drive` | DRIVE |
| `blend` | `blend` | BLEND |
| `level` | `level` | LEVEL |
| `master` | `master` | MASTER |
| `bass` | `lo` | BASS (Baxandall) |
| `treble` | `hi` | TREBLE (Baxandall) |
| `lomid` | `loMid` | LO-MID gain |
| `himid` | `hiMid` | HI-MID gain |

**Switch keys** (value = the literal enum label — matches the APVTS `juce::StringArray` order in
`PluginProcessor.cpp::createParameterLayout()` exactly, so `parse_capture()`'s index maps need no
translation layer):

| Filename key | Values (index 0/1/2) | Real control |
|---|---|---|
| `attack` | `flat` / `boost` / `cut` | ATTACK [ENG] |
| `grunt` | `boost` / `cut` / `flat` | GRUNT |
| `lomidfreq` | `250` / `500` / `1k` | LO-MID freq selector [ENG-caps] |
| `himidfreq` | `750` / `1p5k` / `3k` | HI-MID freq selector [ENG-caps] |

> ⚠ **GRUNT naming correction (this pass):** an earlier draft of this matrix used `grunt-lo`/
> `grunt-hi`, which named captures by a vague bass-amount adjective instead of the switch's actual
> electrical position — and doesn't even correspond to a real position (the three GRUNT positions
> are `boost`/`cut`/`flat` per `circuit.md`'s UI map). Since REF-OD's baseline already sits at the
> physical-MID/electrical-Cut position, the two non-baseline captures needed are `boost` and `flat`
> — that's what the matrix below uses. This is exactly the class of ambiguity this explicit grammar
> exists to prevent.
>
> **Frequency-selector captures also need the matching gain pot pushed to an extreme** (so the peak
> is visible/measurable) — e.g. `lomidfreq-250_lomid-1700_base-clean.wav`. An earlier draft left
> this as a prose parenthetical ("Lo-Mid gain MAX"); it's now an explicit `lomid-1700` token like
> any other deviation, not implied text.

**Baseline key** (required, always the last token): `base-od` / `base-clean`.

**Gain-session key** (optional; omit entirely if the whole session used one fixed interface gain —
see `validation-and-capture.md` §3 rule 1, "fix interface gain for the whole session and never touch
it"). Value = signed dB from the session's original gain, `[np]<digits>` (`n12` = −12 dB, `p6` =
+6 dB):

| Filename key | `captures.py` field | Meaning |
|---|---|---|
| `gain` | `gainSessionDb` | interface-gain deviation from the original session, dB |

> ⚠ **Added 2026-07-22, mid-session.** MASTER-max and several EQ-boost-max clean captures
> (`master-1700`, `bass-1430/1700`, `treble-1430/1700`, `lomid-1430/1700` + its freq variants,
> `himid-1430/1700` + its freq variants) were pinned against the same hard ceiling (peak 0.98850,
> hundreds–thousands of flat-topped samples) regardless of which knob was under test — the signature
> of the recording interface's own input headroom being hit, not 14 independent coincidences. Fix:
> dropped interface gain −12 dB partway through the session and re-captured just those 14 takes
> (protocol rule 1 says fix gain for "the whole session," so a mid-session change is deliberately
> made loud/explicit here rather than silently reusing the same bare filenames). The `gain` key
> exists so a re-captured-at-different-gain file can never silently look identical to a normal
> capture — same principle as every other key in this grammar ("if a control matters, it gets a
> token").
>
> **A `gain`-tagged file needs a matching gain-session anchor pair before it can be trusted for
> ABSOLUTE level** (not needed for shape-only comparisons — `analyze.py::normalize_gain` already
> handles an arbitrary scalar mismatch there). The anchor is the REF-OD/REF-CLEAN baseline
> re-captured at the new gain: `ref-od_gain-n12.wav` / `ref-clean_gain-n12.wav` (reserved-name
> variant — still zero *other* deviation, so no trailing `base-*` token, same as the un-tagged
> `ref-od.wav`/`ref-clean.wav`). `captures.py::gain_correction_db()`/`gain_correction_linear()`
> apply the MEASURED delta from that pair's `cal_1k` tone (not the nominal dial value — same
> "fit to capture, don't trust the control" principle used everywhere else in this project). **Use
> the ref-CLEAN pair to measure this, not ref-OD**: REF-CLEAN's audible path is pure linear stages
> (BLEND's clean tap is pre-JFET), so `cal_1k`'s level there is an uncontaminated scalar of
> interface gain (measured 2026-07-22: −12.071 dB, within 0.07 dB of the −12 dial). REF-OD routes
> `cal_1k` through the CD4049 clipper, whose compression makes a lowered send level produce a
> smaller apparent output drop (measured only −2.857 dB for the same nominal −12) — not usable as a
> linear calibration anchor. All 14 re-captured files are `base-clean`, so this is exactly the pair
> that matters; only re-derive an OD-side delta if a gain-tagged `base-od` capture is ever added.

### Tier 1 — Essential (31 takes)

```
bypass.wav
ref-od.wav
ref-clean.wav
ref-od_gain-n12.wav
ref-clean_gain-n12.wav
drive-0700_base-od.wav
drive-0930_base-od.wav
drive-1430_base-od.wav
drive-1700_base-od.wav
grunt-boost_base-od.wav
grunt-flat_base-od.wav
attack-boost_base-od.wav
attack-cut_base-od.wav
bass-0700_base-clean.wav
bass-1700_gain-n12_base-clean.wav
treble-0700_base-clean.wav
treble-1700_gain-n12_base-clean.wav
lomid-0700_base-clean.wav
lomid-1700_gain-n12_base-clean.wav
himid-0700_base-clean.wav
himid-1700_gain-n12_base-clean.wav
lomidfreq-250_lomid-1700_gain-n12_base-clean.wav
lomidfreq-1k_lomid-1700_gain-n12_base-clean.wav
himidfreq-750_himid-1700_gain-n12_base-clean.wav
himidfreq-3k_himid-1700_gain-n12_base-clean.wav
blend-0700_base-od.wav
blend-1200_base-od.wav
level-0700_gain-n12_base-od.wav
level-1700_gain-n12_base-od.wav
master-0700_base-clean.wav
master-1700_gain-n12_base-clean.wav
```

| Group | Pins |
|---|---|
| `bypass` | **level anchor (kInputRef)** — record first |
| `ref-od` / `ref-clean` | OD & clean references + DIST-footswitch check (compare the two directly) |
| `ref-od_gain-n12` / `ref-clean_gain-n12` | **gain-session anchor pair** — measures the real dB delta for every `*_gain-n12_*` capture below |
| `drive-*` | **CD4049 clipper** amount + harmonics (4 points; drive's own noon baseline is the implicit 5th) |
| `grunt-*` | pre-clip bass content (baseline already covers electrical Cut) |
| `attack-*` | **3-way Attack [ENG]** + treble net (baseline already covers Flat) |
| `bass-*` / `treble-*` / `lomid-*` / `himid-*` | EQ band tapers, read from the clean sweep only |
| `lomidfreq-*` / `himidfreq-*` | **switchable mid centers [ENG-caps]** — gain pinned to MAX so the peak is measurable |
| `blend-*` | crossfade taper (full-OD is the baseline; these two are the other two points) |
| `level-*` | LEVEL taper |
| `master-*` | **Master taper/placement [ENG]** |

### Tier 2 — Extended (20 takes, if time)

```
bass-0930_base-clean.wav
bass-1430_gain-n12_base-clean.wav
treble-0930_base-clean.wav
treble-1430_gain-n12_base-clean.wav
lomid-0930_base-clean.wav
lomid-1430_gain-n12_base-clean.wav
himid-0930_base-clean.wav
himid-1430_gain-n12_base-clean.wav
blend-0930_base-od.wav
blend-1430_base-od.wav
level-0930_gain-n12_base-od.wav
level-1430_gain-n12_base-od.wav
master-0930_base-clean.wav
master-1430_gain-n12_base-clean.wav
lomidfreq-250_lomid-0700_base-clean.wav
lomidfreq-1k_lomid-0700_base-clean.wav
himidfreq-750_himid-0700_base-clean.wav
himidfreq-3k_himid-0700_base-clean.wav
drive-1700_grunt-boost_base-od.wav
drive-1700_attack-boost_base-od.wav
```

- First 14: fill EQ bands / Blend / Level / Master to 5 sweep points each (Drive already has 5 via
  its Tier-1 4 points + its own noon baseline, so it's not repeated here).
- Next 4: mid-freq selectors captured at the gain-MIN extreme too (two-sided → tighter center fit;
  the gain-MAX side is already in Tier 1).
- Last 2: Drive×switch cross-terms at max Drive.
- (The baseline already covers: Grunt physical-mid/electrical-Cut, Attack Flat, and both mid-freq
  selectors' "up" position — no need to re-capture those as their own zero-deviation takes.)

`analysis/captures.py::CAPTURE_MATRIX_TIER1` / `CAPTURE_MATRIX_TIER2` are these exact lists,
byte-for-byte — `python3 analysis/captures.py` parses every one and reports PASS/FAIL, so the doc
and the parser cannot silently drift apart.

> **Secondary/diagnostic captures (not in the matrix): the full LEVEL sweep at its ORIGINAL
> (untagged, `gainSessionDb=0`) interface gain** — `level-0700/0930/1430/1700_base-od.wav`, kept
> alongside the primary `gain-n12` LEVEL sweep above rather than archived. LEVEL is `base-od`
> (DIST-engaged), so — unlike the `base-clean` captures the `gain-n12` fix already covers — its
> original-gain files can't be corrected into the same absolute-level frame as the `gain-n12`
> primary sweep (the CD4049 clipper's compression makes any base-od session-to-session delta
> unreliable, the same reason REF-OD's own `cal_1k` gave a contaminated −2.857 dB instead of
> REF-CLEAN's clean −12.071 dB — see the `gain` key note above). They repeatably show what looks
> like genuine output-stage compression at high LEVEL settings (non-monotonic level, poor
> waveform-shape null vs. neighboring settings) that the `gain-n12` sweep does not — worth keeping
> for future characterization, but **never treat them as equivalent to, or splice-able with, the
> `gain-n12` primary sweep.** Listed in `captures.py::CAPTURE_MATRIX_SECONDARY`, not
> `CAPTURE_MATRIX` — `find_captures()` will still surface them (nothing hides a file from a
> directory scan), but no primary fit should read from that list.

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
