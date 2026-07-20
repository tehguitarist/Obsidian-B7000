# Analysis Harness — Guitar Pedal Plugin Template

This directory contains a **pedal-agnostic** A/B validation harness for comparing
a circuit-emulation plugin against real-pedal captures. Every tool here was
extracted from a production pedal project and stripped of pedal-specific
dependencies (those live in `captures.py`, which you fill in).

## Quick Start

```bash
# 1. Generate the reference test signal
python3 analysis/gen_test_signal.py
# → writes analysis/test_signal_48k.wav

# 2. Implement captures.py (see "First-time Setup" below)
# 3. Build your OfflineRender binary (a CLI that mirrors processBlock)
cmake --build build --target OfflineRender

# 4. Run the comprehensive A/B (once captures exist in analysis/captures/)
python3 analysis/comprehensive_report.py --os 8
# → writes analysis/reports/comprehensive_data.json

# 5. Generate the dashboard
python3 analysis/dashboard_gen.py
# → writes analysis/reports/dashboard.html  (open in browser)

# 6. Audit against acceptance targets
python3 analysis/report_audit.py --write
# → writes analysis/reports/executive_summary.txt
```

## File Reference

### Core Library

| File | Lines | What It Does |
|------|-------|-------------|
| `analyze.py` | 297 | **Pedal-agnostic analysis library.** Load/align WAVs, frequency response (CSD/Welch), discrete-tone THD (harmonic binning), **Farina continuous THD(f)** with order-limiting (eliminates the spurious-edge-spike artefact), sub-sample fractional alignment, gain-matched null depth, linear-removed (coherence-based) null floor, generic capture-filename parser (clock HHMM or 0-10 scale). Everything else imports this. |
| `gen_test_signal.py` | 173 | **Reference signal generator.** Exponential sine sweeps (Farina ESS) at clean + 3 driven levels, discrete harmonic tones, 1 kHz level steps for compression knee, SMPTE IMD (60 Hz + 7 kHz, 4:1), guitar-band IMD (220 Hz + 660 Hz), plucked decay notes. **Append-only** — inserting segments in the middle invalidates all existing captures. |
| `captures.py` | — | **Pedal-specific interface (you implement).** Provides `find_captures()`, `load_capture()`, `render_args()`, and `RENDER_BIN`. The template scripts import from here. See "First-time Setup" below. |

### Dashboard & Visualisation

| File | Lines | What It Does |
|------|-------|-------------|
| `dashboard_gen.py` | 457 | Reads `comprehensive_data.json` and generates a **self-contained HTML dashboard** with: FR shape heatmap (capture × band, diverging colour scale), FR line charts per revision (pure SVG, no JS, no CDN), THD dumbbell charts vs. drive level, harmonic magnitude (H2–H7) heatmap, per-revision summary tiles. Supports dark mode via `prefers-color-scheme`. |

### Report & Audit Tools

| File | Lines | What It Does |
|------|-------|-------------|
| `report_audit.py` | 225 | Audits `comprehensive_data.json` against acceptance targets. **Generates `executive_summary.txt`**. Covers: (1) FR vs. target grading (per-band RMS, count exceeding tolerance), (2) THD data coverage — which bands have measurable THD vs. Nyquist-limited, (3) THD vs. drive level — is error clip-onset (level-dependent) or static (wrong fault type)?, (4) Harmonic magnitude deltas — correct per-order levels, not just RSS (THD). |
| `gap_audit.py` | 174 | Grades every FR band + THD point against configurable thresholds (HUGE >3 dB / target >1.5 dB / good ≤1 dB). Reports **mean and spread** per band: large spread = setting-dependent error (taper/drive-tracking); consistent mean = fixed shape error (component value). |
| `cascade_analysis.py` | 115 | Separates FR gaps by **which circuit stage** can cause them. Uses blend, drive, and frequency-region discriminators to prevent fitting a downstream stage to compensate for an upstream error. Runs on JSON only — no re-rendering. **Replace the `REGIONS` tuple with your pedal's frequency bands of interest.** |
| `capture_outlier_scan.py` | 263 | Flags captures that disagree with all siblings. Separates **capture-intrinsic** physics violations (corrupt file — quarantine) from **plugin-vs-capture** disagreement (real gap — investigate). Never says "wrong"; hands you the question. Runs on JSON only. |

### Tooling Integrity Tests

These validate the estimators themselves before you trust any number they produce.

| File | Lines | What It Does |
|------|-------|-------------|
| `farina_validate.py` | 201 | Validates the **Farina continuous-THD curve** against the discrete-tone THD estimator via a **bracket test**: `THD(−18) ≤ THD_tone(−14) ≤ THD(−12)`. `--probe` mode dumps per-order magnitudes to identify which harmonic order spikes where. **Re-renders the plugin** for each capture (needs `captures.render_args()`). |
| `farina_regression_check.py` | 67 | Proves the order-limit fix is **bit-identical below 2714 Hz** on every capture. Run after any change to `harmonic_thd_curve()` in `analyze.py`. |
| `hf_thd_flatness_check.py` | 125 | Cross-validates swept THD against an **independent** discrete-tone estimator at 2 kHz and 4 kHz. Separates two questions usually conflated: (1) does the magnitude agree? (2) is it monotonic in level? **Re-renders the plugin** (needs `captures.render_args()`). |
| `tone_thd_nyquist_check.py` | 87 | Validates the discrete-tone THD estimator at HF. Unguarded `analyze.thd()` clamps out-of-band harmonics to the top FFT bin, inflating THD by up to √N of the near-Nyquist noise. Compares **guarded** (drop orders past Nyquist) vs. **unguarded**, quantifying the fabrication. |
| `base_rate_warp_measure.py` | ~105 | Measures the model's own **base-rate bilinear top-octave warp** by rendering the dry/linear path at 48 kHz vs. 96 kHz (near-analog reference) and differencing the FR. Droop = what a calibration high-shelf should invert. |

## Key Concepts

### The Test Signal

`test_signal_48k.wav` (48 kHz, 32-bit float) contains these segments in order:

| Segment | Content | Purpose |
|---------|---------|---------|
| `cal_1k` | 1 kHz tone @ -18 dBFS | Level calibration + sample-rate detection anchor |
| `sweep_clean` | Log sweep 20 Hz → 20 kHz @ -30 dBFS | Primary clean FR + alignment anchor |
| `sweep_clean_-36` | Same sweep @ -36 dBFS | Second clean-end FR point (rolled-off input) |
| `sweep_drv_-18` | Log sweep @ -18 dBFS | Driven FR + continuous THD(f) via Farina deconvolution |
| `sweep_drv_-12` | Log sweep @ -12 dBFS | Deeper drive; bracket-tests the -18 sweep |
| `sweep_drv_-6` | Log sweep @ -6 dBFS | Hot pickup level; heaviest clipping |
| `lvl_-36` … `lvl_-3` | 1 kHz tone steps, 3 dB apart | Compression knee vs. input level |
| `tone_82.41` … `tone_8000` | Discrete tones @ -14 dBFS | Harmonic spot-checks (anchor the swept THD) |
| `imd_smpte` | 60 Hz + 7 kHz (4:1) | SMPTE intermodulation distortion |
| `imd_guitar` | 220 Hz + 660 Hz (musical 5th) | Guitar-band intermod |
| `decay_220`, `decay_1k` | Plucked exp-decay notes | Touch / dynamic response |

**Never insert segments in the middle** — it shifts every later segment's offset
and invalidates all existing captures. Append new segments at the end only.

### The Farina THD Curve

`analyze.harmonic_thd_curve()` deconvolves a driven exponential sweep against
the clean reference sweep to extract time-separated harmonic impulse responses.
This yields a **continuous THD(f) curve** from a single capture.

**Order limiting** (on by default): the reference sweep has no energy above
`SWEEP_F1` (20 kHz), so order N is only measurable while `N·f ≤ SWEEP_F1`.
Without limiting, each order produces a large spurious spike at exactly
`SWEEP_F1/N` (e.g., H7 spikes at 2857 Hz). With limiting:
- Nothing below ~2714 Hz changes (all 7 orders in-band)
- Coverage extends to ~9.5 kHz (H2 only)
- Above 12 kHz, THD doesn't exist at 48 kHz (H2 past Nyquist)

### Calibration Workflow (the proven order)

1. **Validate STRUCTURE before AMOUNT** — get FR shape and per-harmonic structure
   (which orders, where placed) right first. THD magnitude is downstream.
2. **FR shape** — gain-match, compare linear FR. Fix EQ/tapers.
3. **Per-harmonic structure** — compare H2–H7 re fundamental. A correct THD can
   hide wrong individual magnitudes (same RSS, different timbre).
4. **Input reference calibration** (volts/FS from clip onset).
5. **Clip character** — asymmetry, knee softness, junction capacitance.
6. **Output level** — per-revision makeup gain.
7. **Re-run** full A/B; decompose residuals with `linear_removed_null()` before
   changing more constants.

## First-time Setup

### 1. Implement `captures.py`

This is the only file you need to write. It provides four things:

```python
RENDER_BIN = "build/OfflineRender_artefacts/Release/OfflineRender"  # your renderer path

def find_captures(directory="analysis/captures"):
    """Return [(path, parsed_dict), ...] for each .wav."""

def load_capture(path, expect_fs=48000):
    """Return float64 mono audio, auto-correcting rate-mislabeled headers."""

def render_args(parsed, extra_args=None):
    """Parsed settings -> flat CLI args list for your OfflineRender."""
```

A skeleton is already in `captures.py` with `load_capture` pre-implemented
(including the rate-mislabel fix). You only need to fill in `parse_capture()`
and `render_args()`.

### 2. Create your OfflineRender binary

Your plugin must provide a console-mode executable (e.g. a JUCE `ConsoleApplication`)
that mirrors `processBlock()` gain staging. Its CLI should accept:

- Input WAV path
- Output WAV path  
- Knob/switch positions (whatever your pedal has)
- `--os <factor>` for oversampling override
- Calibration overrides (for parameter sweeps)

### 3. Write your `comprehensive_report.py`

Model it after this pattern (it's what ties everything together):

```python
# comprehensive_report.py — you write this
import captures as C
import analyze as A
import json

for path, parsed in C.find_captures():
    cap = C.load_capture(path)
    ren = render_plugin(C.render_args(parsed))  # call your CLI
    # run A.transfer(), A.harmonic_thd_curve(), ...
    # collect into a JSON structure matching the dashboard schema
```

The NoAmp project's production version is available as a reference in the
`reports/example_dashboard.html` output format — study it to understand the
expected JSON schema.

## Naming Conventions for Capture Files

The `analyze.parse_filename()` helper auto-detects two notations:
- **Clock HHMM**: `V1200 B1330 T1200` — 0700=min, 1200=noon(0.5), 1700=max
- **0–10 scale**: `G3 V4 B6 T4` — plain dial position / 10

If your pedal uses different knob labels, write your own `parse_capture()` in
`captures.py` instead.

## Known Gotchas

- **Rate-mislabeled captures**: Some NAM modelers export 44.1 kHz audio inside
  a 48 kHz WAV header. Reading naively plays 8.8% fast and decorrelates the
  entire upper band. The `captures.load_capture()` skeleton includes detection
  via the 1 kHz cal tone — keep this logic.
- **Write 32-bit float renders**: Fixed-point output (16/24-bit int) hard-clips
  at ±1.0 FS. Driven sweeps routinely exceed 0 dBFS after makeup gain — this
  injects a spurious, input-level-independent THD floor that silently corrupts
  every measurement.
- **Judge wet path on full-wet captures**: At partial blend, the pedal's dry+wet
  paths can phase-cancel in the top octave (20 dB at 14 kHz on a BL=0.50
  capture). The plugin typically won't reproduce that cancellation, so a
  partial-blend FR read shows a false "plugin too bright" error.
- **Always write analysis scripts as files**, never as inline commands. Renders
  take seconds each; Farina harmonic analysis takes seconds per segment.

## Dependencies

- Python ≥ 3.9
- `numpy`
- `scipy` (for `scipy.io.wavfile`, `scipy.signal`)
- Your pedal's `OfflineRender` binary (C++ or otherwise)
