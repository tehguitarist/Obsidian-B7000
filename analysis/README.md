# Analysis Harness

This directory holds the A/B validation harness used to check the plugin against
real-pedal reference captures: FR shape, THD/harmonic structure, and null-depth
tracking across the control surface.

## Quick Start

```bash
# 1. Generate the reference test signal
python3 analysis/gen_test_signal.py
# → writes analysis/test_signal_48k.wav

# 2. Populate analysis/captures/ with real-pedal recordings (see captures.py)
# 3. Build the OfflineRender binary
cmake --build build --target OfflineRender

# 4. Run the comprehensive A/B (once captures exist in analysis/captures/)
python3 analysis/comprehensive_report.py --os 8
# → writes analysis/reports/comprehensive_data.json

# 5. Grade the report
python3 analysis/matrix_grade.py analysis/reports/comprehensive_data.json
```

## File Reference

| File | What It Does |
|------|-------------|
| `analyze.py` | **Analysis library.** Load/align WAVs, frequency response (CSD/Welch), discrete-tone THD (harmonic binning), **Farina continuous THD(f)** with order-limiting (eliminates the spurious-edge-spike artefact), sub-sample fractional alignment, gain-matched null depth, linear-removed (coherence-based) null floor, capture-filename parser. Everything else imports this. |
| `gen_test_signal.py` | **Reference signal generator.** Exponential sine sweeps (Farina ESS) at clean + 3 driven levels, discrete harmonic tones, 1 kHz level steps for compression knee, SMPTE IMD (60 Hz + 7 kHz, 4:1), guitar-band IMD (220 Hz + 660 Hz), plucked decay notes. **Append-only** — inserting segments in the middle invalidates all existing captures. |
| `captures.py` | **Capture interface.** Provides `find_captures()`, `load_capture()`, `render_args()`, and `RENDER_BIN`. Everything else imports from here. |
| `parallel.py` | Shared parallel-map helper — every heavy tool loops over independent items (captures, candidate values, bands), which is embarrassingly parallel; this module gives that to a new tool for free. |
| `eq_reference.py` | Closed-form analytic transfer functions for each linear WDF stage (treble/ATTACK ladder, Sallen-Key filters, Baxandall, mid bands, bridged-T, drive stage). The oracle every per-stage `ctest` target checks against. |
| `comprehensive_report.py` | Reads every capture in `analysis/captures/`, renders the plugin at matching settings, and writes a JSON report (FR, THD, H2–H7 harmonics) to `analysis/reports/comprehensive_data.json`. Parallel by default (`--jobs N`). |
| `matrix_grade.py` | Aggregate grade for a `comprehensive_report.py` JSON: per-row band-RMS of `|plugin_db - pedal_db|` over the graded band, plus the FR tilt. |
| `shape_gate.py` | Decomposes every FR/THD residual into LEVEL + TILT + CURVATURE + LOCAL components instead of a single band-RMS — catches narrow features (nulls, peaks) that an aggregate statistic averages away. |
| `fit_nonlinear.py` | Fits the clipper + gain-stage nonlinear parameters to captures, scoring on harmonic-to-harmonic ratios (not harmonic-to-fundamental, which is contaminated by any clean/wet mix in the signal path). |
| `phase_harmonics.py` | Extracts complex (magnitude + phase) harmonics from a steady tone and reports the shift-invariant relative phase `psi_n = phi_n - n*phi_1`. Used by `fit_nonlinear.py`. |
| `offline_render.cpp` | CLI renderer (built as the `OfflineRender` CMake target) that mirrors `processBlock()` gain staging outside the plugin host — every fit and every report above needs it. |

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

## Capture File Naming

`captures.py`'s filename parser recognises knob settings as either clock notation
(`level-1200`, `blend-1330` — 0700=min, 1200=noon, 1700=max) or a 0–10 dial scale
(`grunt-3`), plus named tokens for the switches (`grunt-flat`, `attack-boost`, …).
`analysis/captures/` itself is not tracked in this repository (it holds the raw
reference recordings); populate it locally before running `comprehensive_report.py`.

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
- The `OfflineRender` binary (`cmake --build build --target OfflineRender`)
