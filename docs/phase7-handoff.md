# Phase 7 — pre-work status & resume point (2026-07-22)

> Scratch handoff for resuming the Phase-7 (capture + calibration) pre-work.
> Delete once Phase 7 proper is underway and `docs/build-plan.md` carries the state.

## TL;DR

The **capture session is done** (55 files on disk, all parse). Two of the four
pre-work items are **committed and green**; the remaining blocker is that
**`OfflineRender` does not exist yet** — nothing can be fitted without it.

| # | Pre-work item | Status |
|---|---|---|
| 1 | Gain-session fix (`captures.py` + doc) | ✅ committed `ff5fc5f` |
| 2 | Make fit constants runtime-settable (`FitParams`) | ✅ committed `697339f`, ctest 16/16 |
| 3 | **Build `OfflineRender` console exe** | ❌ **NOT STARTED — the blocker** |
| 4 | Implement `captures.py::render_args()` | ❌ blocked on #3 (needs its CLI) |

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
cancelling in the linear path. They get their own `OfflineRender` CLI flags.

## What's next — item 3, `OfflineRender`

A `juce_add_console_app` (needs `juce::dsp::Oversampling` + WAV I/O) that mirrors
`PluginProcessor::processBlock` exactly. Design already worked out:

**CLI shape**
```
--in <wav> --out <wav>
--master --blend --level --drive --lo --lo-mid --hi-mid --hi   (0..1 KNOB space)
--attack --grunt --lo-mid-freq --hi-mid-freq                    (APVTS choice idx)
--dist-engage 0|1   --bypass 0|1
--input-trim <dB>   --output-trim <dB>
--os 1|2|4|8
--input-ref <V>     --output-makeup <g>
--fit name=value    (repeatable, any FitParams field)
--print-fit         (dump what the render actually used)
```

**Four traps to honour when writing it** (each is a real, silent-wrong-answer
failure mode, not a nicety):

1. **EQ pot inversion.** `PluginProcessor::readParams()` does
   `p.lo = 1.0f - pLo->load()` for `lo/loMid/hiMid/hi` — the DSP stages are
   boost-at-0 while the knob/APVTS is CW-is-boost. `captures.py` returns
   **knob-space** values (matching APVTS). So `OfflineRender` must take
   knob-space on the CLI and apply the same `1.0 -` inversion internally,
   mirroring `readParams()`. Passing the parsed dict straight into
   `PedalChain::Params` inverts every EQ fit, and it will look plausible.
   ⚠ Note `captures.py`'s docstring claims its dict uses "PedalChain::Params
   field names" — the NAMES match but the EQ VALUES are knob-space, not
   DSP-space. Worth a clarifying comment there when writing `render_args()`.
2. **Smoothing ramps.** `inputGain`/`outputGain` (20 ms) and `bypassMix` (5 ms)
   ramp from the plugin's `prepareToPlay` defaults. For a static offline render
   that's a start-of-file artifact — use `setCurrentAndTargetValue()` so the
   render begins at its final gain.
3. **Latency.** `analysis/analyze.py::align()` already cross-correlates and
   removes lag (returns `lag`), so do **not** also trim `getLatencySamples()` by
   default or the two compensations fight. Prefer leaving the render
   uncompensated and letting `align()` do it; if a trim flag is added, make it
   opt-in and document the interaction.
4. **Bypass captures.** `parse_capture("bypass.wav")` returns `{"bypass": True}`
   and *nothing else* — no pot/switch keys. `render_args()` must special-case it
   rather than indexing the usual fields.

Then **item 4**: implement `render_args(parsed, extra_args=None)` in
`analysis/captures.py` (currently `raise NotImplementedError` at ~line 316)
against that CLI, and point `RENDER_BIN` at the built binary
(`build/OfflineRender_artefacts/Release/OfflineRender`).

## Then — Phase 7 proper (do NOT start before 3 & 4)

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
