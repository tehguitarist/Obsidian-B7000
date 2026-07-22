# Phase 7 CALIBRATION PROPER — session handover (2026-07-22)

> Resume point for Phase-7 calibration. Supersedes `phase7-handoff.md` as the live
> state (that file documents the now-complete PRE-work). Read this first.

## TL;DR

- **Step 1 (kInputRef) ✅ DONE** — anchored at 0.87 V/FS, documented, no ctest impact.
- **Step 2 (CD4049 + J201 fits) ⏸ DEFERRED — the reshape is VALIDATED, the fitted
  CONSTANTS ARE DELIBERATELY NOT COMMITTED.** The J201 square-law reshape is confirmed
  correct (fit cost 3374.8 → 149.4; drive-min finally even-dominant). But the fit
  converges on a physically implausible clipper that no available capture can
  contradict, AND its absolute scale is confounded with step 4's LEVEL taper — so the
  constants stay at nominal until steps 3–4 land. **User decision 2026-07-22.** Full
  evidence in "Step 2 — why the constants are NOT committed" below.
- **ctest 16/16 ✅ GREEN**, working tree committed. `JfetStageTest.cpp` rewritten for the
  square-law shape.
- **GRUNT position→cap map ✅ VERIFIED against capture** (was circuit.md's longest-standing
  ASSUMED carry-forward) — see "GRUNT map" below. Not a bug; map is correct.
- Steps 3–6 (bridged-T, tapers incl. `masterTaperExp`, makeup, rails) next.

## Immediate next action (start here)

**Step 3 — bridged-T reshape**, then **step 4 — tapers** (`levelTaperExp`,
`masterTaperExp`, re-touch `driveTaperExp`). THEN return to step 2 and re-fit the
nonlinear constants jointly, now that the tapers make the **OD-vs-clean level** a valid
constraint (see below — that is the missing constraint the harmonic-only objective
lacks). Only then commit step-2 constants, then step 5 (makeup), step 6 (rails).

## Step 2 — why the constants are NOT committed (2026-07-22)

The reshape works. The **values it produces do not survive a physics check**, and four
separate attempts to break the ambiguity all failed. Do not re-derive these:

### The fit result (best cost 149.4, from nominal 3374.8)
```
jfetG0 4.583 | jfetSatPos(s) 10.585 | jfetSatNeg(a) 0.232
clipA0 7.275 | clipSatLo 0.773 | clipSatHi 1.012 | driveTaperExp 1.598
```
Harmonic match is good (drive-min H2 −35.6 vs capture −36.0; H3 −64.8 vs −59.2) and
**drive-min is genuinely even-dominant now** — the structural win the reshape was for.

### Why these values are not trustworthy
1. **`clipA0` = 7.3 vs circuit.md's community-measured 20–30**, and **`clipSatLo+Hi` =
   1.79 V vs the ~7 V R19-dropped 4049 rail** (hard-bounded above by the 8.6 V supply).
   `jfetG0` 4.58 vs nominal 15.
2. **NOT a bounds artefact.** Run 1 pinned `jfetSatPos` at exactly its 6.0 ceiling;
   bounds were widened (now in `fit_nonlinear.py` with the reasoning) and run 2 moved
   FURTHER out, not back.
3. **NOT a flat degeneracy** — this was the obvious hypothesis and it is WRONG. Scaling
   `g0·k, a/k, clipSat·k` (which preserves both the clipper drive ratio and J201's
   H2/H1 ∝ a·g0) gives a REAL minimum at k=1:
   `k=0.6→288.7, 0.8→168.3, 1.0→149.4, 1.5→186.5, 2.5→293.5, 4.0→447.7`.
   The objective actively REJECTS the physically-nominal combination (k=4 → 448).
4. **The doc-mandated second constraint on `clipA0` is INERT.** `FitParams.h` says A0
   must be fit against the GRUNT voicing AND the drive sweep, "not either alone",
   because A0 sets the clipper input impedance `R18/(1+A0)` and hence the GRUNT corners.
   Built that check (`analysis/grunt_a0_check.py`). **Result: the boost−flat separation
   is A0-INDEPENDENT** (−0.13 → −0.27 dB across A0 = 7.3…90) — clipper compression
   washes the corners out. RMS only weakly prefers A0≈25 (1.43) over 7.3 (1.74). So A0
   has **no independent physical anchor in these captures**.
5. **The absolute-level constraint is confounded with STEP 4.** OD-vs-clean level is
   makeup-independent (both paths share the output chain) and would pin the scale — but
   the fitted point runs **+3.7…+5.2 dB hot**, and that is mostly a FLAT offset at a
   fixed LEVEL=noon, i.e. the un-fit `levelTaperExp`. Only the ~1.5 dB drive-dependent
   part belongs to step 2.
   ```
   drive   min    9:30   noon   2:30   max
   err   +4.08  +4.14  +3.65  +5.13  +5.16   (render OD−clean minus capture OD−clean)
   ```

### Therefore
**Do steps 3–4 first, then re-fit step 2 jointly with an added OD-vs-clean level term.**
That term is the missing constraint; it only becomes valid once `levelTaperExp` is known.

## GRUNT map — ✅ VERIFIED against capture (resolves a circuit.md carry-forward)

circuit.md/Clipper.h carried "GRUNT position→cap map is the ASSUMED UI map — VERIFY at
capture" since Phase 5. **It is correct.** Measured, 50–300 Hz, matched-pair vs the cut
baseline: **cut 0 dB (4n7) < flat +5.43 dB (4n7∥47n) < boost +6.81 dB (4n7∥220n)**,
monotone bin-by-bin (63 Hz +9.77/+14.83; 100 Hz +8.11/+10.39; 160 Hz +5.17/+6.03).
Index mapping is right end-to-end too: `PedalChain::gruntEnum()` deliberately does NOT
pass the index through to `Clipper::Grunt` (whose declaration order is Cut/Flat/Boost =
0/1/2), so the off-by-one trap is already handled; `offline_render.cpp` parses
`--grunt {boost,cut,flat}` = 0/1/2 to match.

The uneven spacing (+5.43 then only +1.38) is physically expected, not suspicious: at
A0=25 the cut corner is ~1.7 kHz (above the band → heavily rolled off in-band), flat
~158 Hz (in band), boost ~36 Hz (already below the band). Once a corner drops under the
band, extra capacitance buys almost nothing.

⚠ **Open carry-forward (belongs to step 2, not the cap map):** the model reproduces the
cut→flat step but **flattens the flat→boost step to ~0 dB vs the capture's +1.38 dB**, at
EVERY A0 (7.3…90) and at BOTH the fitted and the physically-nominal clipper ceilings
(sat 3.15/3.85 gave +0.14, and made RMS worse: 2.74 vs 1.43). So it is not the sat
ceiling and not A0 — the model's clipper compresses away a level difference the real
pedal preserves. Revisit with the step-2 joint re-fit.
Suggestive: the ANALYTIC pre-clipper separation at A0=7.28 is **+1.41 dB**, nearly
exactly the captured +1.38 — consistent with the real clipper barely compressing here,
while the model's compresses it to zero regardless of parameters.

⚠ **Measurement trap (cost real time, now guarded in the script):** below ~40 Hz the
driven-sweep captures are noise (the matched-pair diff swings −5…−11 dB
non-monotonically). Averaging a "LF plateau" from 20 Hz reads that noise as
"flat gives LESS bass than cut" and looks exactly like a wrong cap map. Use 50–300 Hz.

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

## ⚠⚠ Step 3 attempt found a BIGGER problem: the OD path has ~+25 dB of excess HF

Attempting the bridged-T reshape surfaced a much larger issue that **blocks step 3 and
probably corrupted the step-2 fit**. Evidence, in the order it was established:

### 1. The error is confined to the OD chain (bisection)
Measured shape re 200 Hz, `sweep_clean_-36` segment, drive-MIN capture vs render:
```
                 100    300    700   1200   2000   3000   5000   8000 Hz
ref-clean  cap  -0.12  +0.04  +0.10  +0.14  +0.19  +0.21  +0.17  +0.11   <- FLAT (+-0.2 dB)
ref-clean  mdl  -3.14  +1.11  +1.98  +2.14  +2.19  +2.20  +2.21  +2.21   RMS err 1.90 dB  OK
drive-0700 cap  -2.41  -2.63  -2.19  +0.53  +6.03  +6.54  -4.59  -5.52
drive-0700 mdl  -2.05  -7.80  +4.01 +21.90 +29.23 +31.00 +27.70 +19.98   RMS err 19.7 dB  ✗
```
The clean path matches within ~2 dB, and the clean CAPTURE is flat to +-0.2 dB — so the
EQ, output stage, and the whole `transfer()` measurement pipeline are all validated. The
error is **entirely inside the OD chain**.

### 2. With the step-2 FITTED constants, 100-700 Hz matches within ~1 dB
Error vs capture: 100 Hz −0.10, 300 Hz −0.96, 500 Hz −0.92, **700 Hz −0.00**, then
900 Hz +6.22, 1200 +13.72, 2000 +17.11, 3000 +18.82. So the divergence is sharply
confined to **>900 Hz**, and the fitted constants fix the low end (nominal RMS 19.71 →
fitted 13.98 dB).

### 3. It is NOT a C++ bug — the analytic oracle reproduces it
Cascading `eq_reference.py`'s per-stage TFs (independent of the C++), dB re each stage's
own 200 Hz value:
```
  Hz  |    J201  treble   drive clipper bridgedT  SK10k7  SK3k3 | TOTAL
 2000 |   +9.39  +14.62   -0.15   +9.17    -2.40   -0.39  -0.67 | +29.56
 3000 |   +9.65  +15.77   -0.33   +9.29    +1.31   -0.84  -2.39 | +32.46
```
The analytic TOTAL (+29.6 dB @ 2 kHz) tracks the rendered model (+23.1 dB; the ~6 dB gap
is the clipper's nonlinear compression). **So the model faithfully implements the spec —
the SPEC disagrees with the real pedal**, which shows only +6.03 dB at 2 kHz.

### 4. Prime suspect: the deferred inter-stage LOADING carry-forwards
Three stages contribute ~+33 dB of HF boost between them (treble net +14.6, J201 shelf
+9.4, clipper +9.2 @ 2 kHz). Each is modelled with **ideal-source-in / unloaded-out**
boundaries — and those are explicitly flagged Phase-7 deferrals:
- `TrebleAttack.h:24` — "Input node G (J201 drain) = IDEAL voltage source (source Z = 0)
  for Phase 4; **revisit with an explicit J201 output impedance at Phase 7 capture**."
  This is the big one: the treble ladder's HF path is C5/C9/C6 in series (22n each →
  7.33n ≈ **7.2 kΩ at 3 kHz**). A real J201 drain / active-load output impedance of tens
  of kΩ would form a divider against that and largely CANCEL the HF bypass of R7.
- `RecoveryBridgedT` is modelled UNLOADED by design (circuit.md risk #1, R24→SK deferred).
- `JfetStage` folds C4 bootstrap + R7 loading into `kG0` — a flat approximation of what
  is really a frequency-dependent interaction.

### 5. This probably BIASED the step-2 harmonic fit
The tone_220 objective reads H2..H5 at **440/660/880/1100 Hz** — i.e. H3/H4/H5 sit right
where the excess HF begins. The fit could only match the captured harmonic ratios by
distorting the clipper, which is a plausible mechanism for the implausible `clipA0`=7.3 /
rail=1.79 V it converged on. **Re-fit step 2 only after the loading is fixed.**

### 6. The bridged-T notch itself is real and CLOSE (the actual step-3 target)
Fine detail, fitted constants, shape re 200 Hz: **capture dip 334 Hz @ −3.36 dB**, model
dip **375 Hz @ −6.46 dB**. So the real notch exists, is ~12% lower in frequency and about
half as deep — exactly what circuit.md risk #1 predicted ("much shallower than ideal").
Tractable, but do NOT fit it until the HF/loading issue is resolved: fitting a notch on
top of a known +20 dB neighbouring error bakes in a compensating error (the calibration
doc's "decompose the deficit before changing constants" rule).
⚠ Also note the analytic treble net shows **−16.69 dB at 300 Hz** on its own — so part of
the ~334 Hz dip may be the TREBLE network, not the bridged-T. Decompose before fitting.

### Recommended next action
Model the **J201 output impedance** into the TrebleAttack boundary (and the bridged-T
load), re-check the OD FR, then re-fit step 2, then step 3/4. `jfetGmR6` should also join
the fit set — it was NOT in `FIT_KEYS` and accounts for ~5 dB of the excess on its own
(sweep: gmR6 2.277→0 moves the 3 kHz error 18.82→13.30 dB).

## Remaining calibration steps (order fixed by calibration-and-gain-staging.md)
3. Bridged-T reshape to the measured notch (compare `drive-0700` OD path vs `ref-clean`).
4. Taper shapes (≥2 knob points/pot; matrix has 4). **Includes `masterTaperExp`** — do
   before makeup (see finding above). `driveTaperExp` is already being fit in step 2
   (coupled); it may want a light re-touch here.
5. Output makeup = level-match to captures (may exceed 1.0; no headroom pad). Decompose the
   deficit per validation-and-capture.md §4 first.
6. Rail clamps LAST — enable only after kInputRef anchored (done) so stages don't clip
   against an arbitrary reference and corrupt the fits above.
