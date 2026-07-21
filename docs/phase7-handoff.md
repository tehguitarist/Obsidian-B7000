# Phase 7 — pre-work status & resume point (2026-07-22)

> Scratch handoff for resuming the Phase-7 (capture + calibration) pre-work.
> Delete once Phase 7 proper is underway and `docs/build-plan.md` carries the state.

## TL;DR

**Phase-7 PRE-WORK IS COMPLETE (2026-07-22).** The capture session is done (55
files on disk, all parse), and all four pre-work items are green. Nothing blocks
calibration proper now — start at "Then — Phase 7 proper" below, in that order.

| # | Pre-work item | Status |
|---|---|---|
| 1 | Gain-session fix (`captures.py` + doc) | ✅ committed `ff5fc5f` |
| 2 | Make fit constants runtime-settable (`FitParams`) | ✅ committed `697339f`, ctest 16/16 |
| 3 | Build `OfflineRender` console exe | ✅ done — `analysis/offline_render.cpp` |
| 4 | Implement `captures.py::render_args()` | ✅ done — against that CLI |

## What's already done

### 1. Capture session + the gain-session fix (`ff5fc5f`)

All **55** capture files are in `analysis/captures/` (gitignored — `*.wav`):
31 Tier-1 + 20 Tier-2 matrix takes + 4 secondary. `python3 analysis/captures.py`
(via `/opt/homebrew/bin/python3.11` — plain `python3` is 3.13 with no numpy)
parses 51/51 matrix filenames, and disk-vs-matrix is an exact set match, zero
missing / zero extra.

**The catch that made this non-trivial:** 14 MASTER/EQ-boost-max takes were all
pinned at the same peak (0.98850) with hundreds–thousands of flat-topped samples
regardless of which knob was under test — one shared ceiling (the interface's own
input headroom), not 14 coincidences. Interface gain was dropped −12 dB and those
14 re-captured, which is why the `gain-n12` filename token and
`gain_correction_db()` now exist. The measured delta comes from the **ref-CLEAN**
anchor pair (−12.071 dB), **not ref-OD** — REF-OD routes `cal_1k` through the
CD4049, whose compression made the same nominal −12 read as only −2.857 dB.

Full reasoning is in `docs/nonlinear-component-modeling.md` §4 (the `gain` key
note) and the commit message. **Read that before touching absolute levels.**

### 2. `FitParams` (`697339f`)

`src/dsp/FitParams.h` + `PedalChain::setFitParams()`. Every capture-fit constant
is now runtime-settable instead of `static constexpr`, because a fit needs
hundreds of candidate evaluations and each one used to cost a rebuild.

**Nothing was re-tuned** — each stage keeps its `static constexpr kXxx` as the
nominal and initialises the member from it, so defaults reproduce the previous
build exactly. ctest 16/16 PASS confirms it.

Fit knobs: `clipA0/clipSatLo/clipSatHi`, `jfetG0/jfetGmR6/jfetSatPos/jfetSatNeg`,
`driveTaperExp/levelTaperExp/masterTaperExp`, `c21R`,
`btR22/btR23/btC16/btC17`, `railEnabled/railNeg/railPos`.

`kInputRef` / `kOutputMakeup` are deliberately **not** in `FitParams` — they're
DAW-domain processor scalars and calibration §1 depends on `kInputRef`
cancelling in the linear path. They get their own `OfflineRender` CLI flags
(`--input-ref` / `--output-makeup`), defaulting to `src/dsp/GainStaging.h`.

### 3. `OfflineRender` (2026-07-22)

`analysis/offline_render.cpp` + CMake target `OfflineRender`
(`juce_add_console_app`, links `juce_audio_formats` + `juce_dsp` + chowdsp_wdf).
Build with `cmake --build build --target OfflineRender`; the binary lands at
`build/OfflineRender_artefacts/Release/OfflineRender`, which is what
`captures.py::RENDER_BIN` already pointed at.

It mirrors `PluginProcessor::processBlock` step for step (each step is annotated
in the source with the processBlock line it copies) — **if processBlock's gain
staging changes, change this too**, or every measurement is of a chain the plugin
doesn't run. The two shared scalars now live in `src/dsp/GainStaging.h`
(`kInputRefNominal` / `kOutputMakeupNominal`) and are included by BOTH
`PluginProcessor.h` and OfflineRender, so committing a fitted `kInputRef` is a
one-line edit that cannot land in only one of the two. `PedalDSP` gained a
`setFitParams()` / `getFitParams()` passthrough (its `chain` is private).

**CLI as built** (`--help` prints it):
```
OfflineRender <in.wav> <out.wav> [options]      # positional — what the analysis/ scripts use
OfflineRender --in <wav> --out <wav> [options]  # equivalent
OfflineRender --print-fit                       # no render; dump the resolved config

--master --blend --level --drive --lo|--bass --lo-mid --hi-mid --hi|--treble  (0..1 KNOB space)
--attack --grunt --lo-mid-freq --hi-mid-freq    (APVTS choice index OR label, e.g. `boost`, `1p5k`)
--dist-engage 0|1   --bypass 0|1
--input-trim <dB>   --output-trim <dB>
--os 1|2|4|8        --block <samples>
--input-ref <V>     --output-makeup <g>
--fit name=value    (repeatable, any FitParams field, case-insensitive)
--print-fit         (dump fit params + the knob→DSP mapping actually used)
--trim-latency      (opt-in only — see trap 3)
```
Deviations from the sketch above, all deliberate: **positional in/out** is
supported because the existing orchestrators (`comprehensive_report.py`,
`farina_validate.py`, `hf_thd_flatness_check.py`) already call
`[BIN, in, out, "--os", N] + render_args(...)`; switch flags accept labels as
well as indices; `--bass`/`--treble` alias `--lo`/`--hi`. Output is always
**32-bit float WAV** (validation-and-capture.md §2). A non-finite sample in the
output is an exit-1 failure, so a parameter sweep records a blown-up candidate as
rejected instead of scoring a file of NaNs.

**The four traps, and how each is handled:**

1. **EQ pot inversion.** `readParams()` does `p.lo = 1.0f - pLo->load()` for
   `lo/loMid/hiMid/hi` — stages are boost-at-0, the knob is CW-is-boost.
   `captures.py` returns **knob-space** values. OfflineRender takes knob space and
   applies the same `1.0 -` inversion internally (`toChainParams()`), and
   `--print-fit` prints `knob_space -> dsp_space` for all eight pots so the
   mapping is checkable. `render_args()` must NOT pre-invert. `captures.py`'s
   docstring now says this explicitly (the names match `PedalChain::Params`; the
   EQ **values** are knob-space, not DSP-space).
2. **Smoothing ramps** — every smoother seeded with `setCurrentAndTargetValue()`.
3. **Latency** — renders UNCOMPENSATED by default; `analyze.py::align()` removes
   the lag. `--trim-latency` exists but is opt-in. Verified: `align()` recovers
   exactly the latency the render reports (64 samples at 8×).
4. **`bypass.wav`** — `render_args()` special-cases `{"bypass": True}` to a bare
   `--bypass 1`; every other flag is optional on the CLI. Note a bypassed render
   is the input **delayed by the OS latency**, not a bit-copy — the dry path is
   delay-compensated to match the latency the plugin reports for PDC.

### 4. `render_args()` + the mapping proof (2026-07-22)

`captures.py::render_args(parsed, extra_args=None)` emits every control
explicitly (never leaning on the binary's defaults matching the capture
baseline), skips `--in/--out/--os` (the orchestrators supply those), and appends
`extra_args` verbatim — which is how a sweep varies one `--fit` value across a
whole batch. All 55 matrix + secondary filenames map cleanly.

**`analysis/render_smoke_check.py`** (run with `/opt/homebrew/bin/python3.11`) is
the guard against the real risk here — a render that runs and produces finite
audio while silently mis-mapping a knob, which no downstream fit can detect
because it would just absorb the error into a constant. Four checks, all PASS:

1. **EQ knob direction** — multitone through each band at knob 0.0/0.5/1.0;
   asserts band gain rises monotonically with the knob (CW = boost) for all four,
   span ≈ 29–36 dB. This is the check that would catch a missing inversion.
2. **Mid-frequency switch mapping** — each selector position's boost peaks at its
   labelled centre (250/500/1k, 750/1.5k/3k), all six exact.
3. **Bypass** — reproduces the input exactly, delayed by the reported latency.
4. **Alignment vs a real capture** — a full ref-clean render is finite,
   length-matched, and `align()` recovers lag == the reported 64-sample latency.

It is a tool, not a ctest gate (ctest stays 16/16). Re-run it after any change to
`processBlock`, `readParams()`, the APVTS choice order, or the CLI.

For context, that ref-clean render sits at −37.47 dB RMS on `sweep_clean` vs the
capture's −32.18 dB. That ~5.3 dB deficit is **expected** — every constant is
still nominal and `kInputRef`/`kOutputMakeup` are un-anchored. Decompose it per
`validation-and-capture.md` §4 before changing anything.

## Phase 7 proper — START HERE (pre-work 1–4 are all done)

Calibration order is fixed by `docs/calibration-and-gain-staging.md`; don't
reorder it:

1. `kInputRef` from the `bypass.wav` anchor (§1).
2. 4049 VTC/rail + J201 shaper fits from the driven captures (control-isolation
   + matched-pair diffs, §6b).
3. Bridged-T reshape to the measured notch — or lack of one (risk #1).
4. Taper shapes, ≥2 knob points per pot (§3b); the matrix has 4.
5. Output makeup = level-match to captures, **may exceed 1.0**, no headroom pad
   (§2). Decompose any deficit (`validation-and-capture.md` §4) *before*
   touching constants.
6. Rail-clamp levels last — enable only **after** `kInputRef` is anchored, else
   every stage clips against an arbitrary reference and corrupts the fits above.

## Environment gotchas

- Python: **`/opt/homebrew/bin/python3.11`**. Plain `python3` is 3.13 and has no
  numpy/scipy.
- Captures are gitignored (`*.wav`) — they exist only on this machine. Back them
  up; they are not recoverable from the repo.
