# Phase 7 CALIBRATION PROPER — session handover (2026-07-22)

> Resume point for Phase-7 calibration. Supersedes `phase7-handoff.md` as the live
> state (that file documents the now-complete PRE-work). Read this first.

## TL;DR

- **Step 1 (kInputRef) ✅ DONE** — anchored at 0.87 V/FS, documented, no ctest impact.
- **Step 2 (CD4049 + J201 fits) 🔄 IN PROGRESS** — big finding: the **J201 waveshaper
  was structurally wrong** (tanh → can't make pure-even harmonics). It has been
  **reshaped to a square-law** (code done, shape verified). The **re-fit has NOT been
  run yet** — that is the immediate next action.
- **⚠ WORKING TREE IS UNCOMMITTED and ctest is currently BROKEN** — `JfetStageTest.cpp`
  still asserts the OLD tanh behaviour and will fail. See "State of the tree" below.
- Steps 3–6 (bridged-T, tapers incl. `masterTaperExp`, makeup, rails) untouched.

## Immediate next action (start here)

1. **Run the re-fit** (the 30-min job that was about to launch, now with the square-law
   J201 + corrected param semantics):
   ```
   /opt/homebrew/bin/python3.11 analysis/fit_nonlinear.py > /tmp/fit3.log 2>&1
   ```
   It fits `{jfetG0, jfetSatPos(=knee s), jfetSatNeg(=even strength a), clipA0,
   clipSatLo, clipSatHi, driveTaperExp}` to the tone_220 harmonic profile across the
   drive sweep. Best OLD-shape cost was 1090; the new shape should beat it substantially
   at low drive (the tanh's structural wall is gone).
2. **Inspect the fitted profile** it prints (capture vs plug, per drive setting). Expect
   drive-min to now be even-dominant. If good, **commit the fitted constants** by editing
   the nominals in `src/dsp/JfetStage.h` (`kG0`, `kSatPos`, `kSatNeg`) and
   `src/dsp/Clipper.h` (`kA0`, `kSatLo`, `kSatHi`) and `driveTaperExp` — plus the matching
   defaults in `src/dsp/FitParams.h`. (These are the "commit a fitted value = one-line
   edit" nominals.)
3. **Rewrite `tests/JfetStageTest.cpp`** for the square-law shape (see "Broken test").
4. **`ctest`** back to green, then **run the `dsp-validator` agent** on JfetStage +
   Clipper (project policy: DSP correctness = validate high).
5. **Re-run `analysis/render_smoke_check.py`** (processBlock/DSP mapping guard) — the
   chain changed. It should still PASS (it doesn't assert absolute harmonics).

## State of the tree (all UNCOMMITTED)

`git status`: modified `CLAUDE.md`, `src/dsp/FitParams.h`, `src/dsp/GainStaging.h`,
`src/dsp/JfetStage.h`; new untracked `analysis/fit_nonlinear.py`. Nothing committed this
session — decide whether to commit after the fit + test-fix land ctest green.

### Step 1 — committed to files (not git), no behaviour change
- `src/dsp/GainStaging.h` — `kInputRefNominal = 0.87` now documented as ANCHORED (was
  "⚠ NOMINAL"). Value unchanged.
- `CLAUDE.md` — Current-step block updated (step 1 done, step 2 next, master-taper note).
- Memory: `phase7-kinputref-anchor.md` (+ MEMORY.md index line).

### Step 2 — J201 square-law reshape (code done, NOT fitted, test BROKEN)
- **`src/dsp/JfetStage.h`** — `waveshape()` + antiderivative REPLACED. Was per-polarity
  `sat*tanh(w/sat)`; now `g(w) = w + a*s^2*(1 - sech(w/s))` (linear + EVEN → pure H2, zero
  intrinsic H3). Antiderivative `F(w)=w^2/2 + a*s^2*(w - s*gd(w/s))`, `gd=2*atan(tanh(x/2))`
  (for ADAA). **Param slots reused/reinterpreted** (no rename, to avoid churn): `sPos` = knee
  `s`, `sNeg` = even strength `a` (SIGNED). Nominal `kSatNeg` changed 2.6 → **0.3** (old value
  = a is non-monotonic; 0.3 is mild/monotonic, |a|*s=0.9). `kSatPos=3.0` kept as `s`.
- **`src/dsp/FitParams.h`** — `jfetSatNeg` default 2.6 → 0.3; both jfet-sat fields
  re-documented as (knee s / even strength a). No signature change.
- **`analysis/fit_nonlinear.py`** (NEW) — the fitter. Bounds/nominal/starts updated for
  the new semantics (`jfetSatNeg` ∈ [0,1] is now `a`, not a sat level). Short-tone
  objective (renders ~20× faster than the full file; verified to reproduce the full-file
  harmonics exactly).
- **`OfflineRender` REBUILT** with the new shape (`cmake --build build --target OfflineRender`).
- **NOT done:** re-fit not run; fitted constants not committed; `Clipper.h` unchanged
  (its shape is CORRECT — see findings); `dsp.md`/`circuit.md` J201 notes still say "tanh".

### ⚠ Broken test — `tests/JfetStageTest.cpp`
Asserts the old tanh: output peaks bounded by `[kSatNeg, kSatPos]` (Test's `ceil` logic
~line 167) and asymmetry via `satPos!=satNeg`. The square-law shape does NOT saturate the
fundamental (odd part is linear) and is not bounded by the sat levels, so those asserts are
now wrong. **Rewrite** to assert: (a) small-signal ≈ identity·(−g0) [unchanged];
(b) even-dominant harmonics (H2 present, H3 ≈ 0) when `a`>0 — the whole point;
(c) slope-at-0 = 1; (d) monotonic for the nominal params. Until then **ctest is not 16/16**.

## Key findings (evidence, so they aren't re-derived)

### kInputRef degeneracy (step 1)
`bypass.wav` cal_1k returns at −0.012 dB vs the test signal → **unity round-trip** rig; the
capture domain == DAW domain 1:1. `kInputRef` is **degenerate with the clip ceiling** under
audio-only captures (proven: ref-clean DIST-off render is −3.894 dB under the capture at
EVERY level step −36..−3 dBFS, **std = 0.000** → K cancels in the linear path). So K is SET,
not measured; 0.87 is the test-signal design anchor. User decision 2026-07-22.

### The clean deficit is Master-taper-dependent (feeds steps 4/5)
`ref-clean` (DIST off, pure linear) plug−capture = **−3.894 dB, flat across all levels**.
But across the MASTER sweep the real round-trip gain runs (gain-n12 corrected):
`master 0/¼/½/¾/max → −19.6 / −8.2 / +0.95 / +10.7 / +12.3 dB`. So the −3.9 dB at noon is
NOT pure flat makeup — **fit `masterTaperExp` (step 4) BEFORE committing makeup (step 5)**.
(Master min renders as a full mute in the plugin — taper x=0 → 0; real is ~−40 dB floor.
Check the master taper floor when fitting.)

### Step 2 — the two errors, both pinned
1. **`jfetG0=15` far too high** — slams the clipper even at drive-min. At `jfetG0≈4–8` the
   drive-MAX harmonic profile matches the capture well (THD 6.7–9.7% vs 7.2%; H2/H4 ~1 dB).
2. **J201 tanh → square-law (structural).** Real low-drive OD is even-dominant
   (H2 −36, H3 −59 @ drive-min: +23 dB even/odd separation) — a JFET square-law fingerprint.
   `tanh` is odd; its w³ term forces H3 whenever it makes H2 (proven: no scalar combo got
   drive-min H3 below −50 while the capture is −59). The new square-law shape produces
   H2−H3 separations of **+48…+60 dB** (verified) — the wall is gone.
3. **CD4049 clipper shape is FINE** (user asked to check). Isolated with moderate gain it is
   correctly near-silent at drive-min (THD −78) and H3-dominant at max; its earlier
   over-activity was purely the `jfetG0` gain error. The J201's (now correct) even H2
   balances the clipper's odd H3 to the real "balanced at max" (H2≈H3). Leave Clipper.h.

### Capture harmonic TARGETS (tone_220, dB re fundamental) — the fit objective
```
drive  THD    H2     H3     H4     H5
min   -36.0  -36.0  -59.2  -69.9  -86.4
9:30  -34.4  -34.4  -55.3  -71.6  -83.5
noon  -31.0  -31.4  -42.0  -51.1  -56.8
2:30  -25.9  -31.9  -30.7  -38.4  -32.7
max   -22.9  -30.0  -29.0  -35.8  -28.8
```

## Tooling notes / gotchas (cost real time)
- Python: **`/opt/homebrew/bin/python3.11`** (plain `python3` = 3.13, no numpy/scipy).
- **`analyze.py::align(render, orig)` returns a TUPLE `(render, lag)`** — unpack it.
- `captures.py::load_capture()` resamples rate-mislabeled files via the cal tone; use it
  (not `analyze.load`) for captures. Warns on non-`data` WAV chunks — harmless.
- **gain-n12 captures need +12.071 dB** to reach the base-gain frame (exact on the
  ref-clean anchor pair; `captures.py::gain_correction_db`). Direction: ADD to the capture.
- Render CLI: `OfflineRender <in> <out> --os 8 <render_args...> [--fit key=val ...]`.
  EQ pots are KNOB-space in `render_args`; OfflineRender applies the `1-x` inversion.
- Isolating one nonlinearity by setting the OTHER's sat huge is UNRELIABLE (the linearized
  clipper's ~×48 loop gain re-saturates even at sat=50). Reason about shapes analytically
  or drive the real stage; don't trust "linearize by huge-sat" renders.

## Remaining calibration steps (order fixed by calibration-and-gain-staging.md)
3. Bridged-T reshape to the measured notch (compare `drive-0700` OD path vs `ref-clean`).
4. Taper shapes (≥2 knob points/pot; matrix has 4). **Includes `masterTaperExp`** — do
   before makeup (see finding above). `driveTaperExp` is already being fit in step 2
   (coupled); it may want a light re-touch here.
5. Output makeup = level-match to captures (may exceed 1.0; no headroom pad). Decompose the
   deficit per validation-and-capture.md §4 first.
6. Rail clamps LAST — enable only after kInputRef anchored (done) so stages don't clip
   against an arbitrary reference and corrupt the fits above.
