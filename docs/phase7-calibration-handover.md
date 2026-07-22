# Phase 7 CALIBRATION PROPER — session handover (updated 2026-07-22, session 3)

> **Resume point for Phase-7 calibration. Read this first.** Supersedes
> `phase7-handoff.md` (which documents the now-complete PRE-work).
> `ctest` is 16/16 green and the tree is clean. Session 3's J201/TrebleAttack
> restructure is committed as `b02b2f2`.

---

## TL;DR — where we actually are

| Step | State |
|---|---|
| 1. `kInputRef` | ✅ **DONE** — anchored at 0.87 V/FS |
| 0. J201 output impedance / loading | ✅ **DONE 2026-07-22 (session 3)** — see below |
| 2. CD4049 + J201 fits | ⚠ reshape validated, fit set now correct, re-run DONE — **rejected: the J201 shaper has no ceiling** (see below). Constants NOT committed. |
| 3. Bridged-T reshape | not started (was blocked; **now unblocked**) |
| 4. Tapers (`level`/`master`/`drive`) | not started |
| 5. Output makeup | not started |
| 6. Rail clamps | not started (must stay LAST) |

**Session 3 closed the blocker.** The OD path's ~+23 dB of excess HF was a
STRUCTURAL error in how the J201/treble boundary was modelled, and it is fixed.
Measured OD-path shape error vs the capture (drive-min, mean-removed RMS over
50 Hz–8 kHz, `sweep_clean_-36`):

```
   before (ideal-source boundary, nominal params) : 14.2 dB
   after  (Norton boundary, nominal params)       :  6.9 dB
   after  (Norton boundary, coarse gm scan)       :  1.4 dB
```

ctest 16/16. The remaining calibration steps can now proceed in the documented
order — but see "Still open" for two things that must not be forgotten.

---

## ▶ IMMEDIATE NEXT ACTION

1. ✅ **DONE — `jfetGm`/`jfetRo`/`jfetRq2` fitted** (`analysis/fit_jfet_boundary.py`,
   new). Shape error **7.53 → 1.56 dB** at **`jfetGm` ≈ 0.09 mS**; `jfetRo`/`jfetRq2`
   are **NOT identifiable** from this data and stay at nominal. See the section below
   before using the number — the level cross-check is what makes it credible.
2. ✅ **DONE — `FIT_KEYS` updated** in `analysis/fit_nonlinear.py`: `jfetG0` →
   `jfetGm`, with `jfetRo`/`jfetRq2` moved to a new `HELD` dict (they are inert in a
   harmonic objective and would only add flat directions). `NOMINAL`/`BOUNDS`/the
   restart points were rescaled too — the old `jfetSat*` ranges were on the
   pre-restructure voltage scale and are meaningless now that the shaper sees vgs.
   `analysis/grunt_a0_check.py` was also passing the dead `jfetG0` key, so **every
   run of it has been dying in the arg parser** — reset to nominal.
3. ✅ **RUN — step-2 nonlinear re-fit** (`analysis/fit_logs/step2_refit.log`).
   **It FAILS both acceptance tests, and the failure identifies a STRUCTURAL gap, not
   a bad parameter value.** Do not re-run it as-is. See "Step 2 re-fit — the result"
   below; the short version is that the J201 shaper has **no ceiling**, the fitter
   tried to manufacture one and was stopped dead at the monotonicity gate.
4. **▶ NEXT: add the asymmetric soft ceiling to the J201 drain current** (the
   carry-forward already flagged in `JfetStage.h` and by dsp-validator). This is a
   CODE change, not a fit — the first one Phase 7 has needed. Then re-run step 2.
5. Then step 3 (bridged-T), step 4 (tapers), step 5 (makeup), step 6 (rails).

---

## ✅ THE BLOCKER, RESOLVED — the J201 drain is a CURRENT source

### What was wrong
`JfetStage` was a VOLTAGE stage (HP → shelf → ×(−G0) → waveshaper) feeding
`TrebleAttack` as an IDEAL source (source Z = 0, the Phase-4 deferral at
`TrebleAttack.h:24`). For a common-source stage with degeneration `Zs = R6||C3`:

```
    k(s)    = 1 + gm*Zs(s)      degeneration factor: 1+gm*R6 at DC -> 1 at HF
    Gm(s)   = gm / k(s)         transconductance RISES with frequency
    Rout(s) = ro * k(s)         drain output resistance FALLS with frequency
    => open-circuit gain Gm*Rout = gm*ro is FLAT, independent of degeneration
```

So **C3's "+10.3 dB HF lift" is not a gain at all** — it is a falling output
impedance that only becomes a lift once something loads it. And the treble
ladder's input impedance falls across the same band (~35 kΩ at 200 Hz → ~6.5 kΩ
at 2 kHz), which cancels most of it. The old model applied the shelf
unconditionally AND drove the ladder from 0 Ω: the boost was counted twice.

### What changed (code)
- **`JfetStage`** now outputs the drain **Norton current** and exposes
  `getSourceZ()`. Its shaper argument is the effective **vgs** (real gate volts,
  order |Vp|) — so the knee `s` is physically scaled. Nominal `kSatPos` 3.0 → **0.5**,
  `kSatNeg` 0.3 → **1.0**.
- **`TrebleAttack`** grew node G and node H (N = 5 → 7) and stamps
  `Zout(s) = [ro + Rp||Cp] || Rq2` (exactly `ro*k(s)||Rq2`, with `Rp = ro*gm*R6`,
  `Rp*Cp = R6*C3`). Its transfer is now a **transimpedance** V(Q)/I.
- **`FitParams`**: `jfetG0` and `jfetGmR6` are **REMOVED** (not renamed) →
  `jfetGm`, `jfetRo`, `jfetRq2`. `gmR6` was never independent of `gm` (R6 is a
  fixed 3k3), so the old pair was redundant. A stale `--fit jfetG0=...` now fails
  loudly in OfflineRender instead of silently setting something else.
- **Oracle**: `treble_attack_tf(..., Zs=...)`, new `jfet_source_z()` and
  `treble_attack_transimpedance()`; `jfet_stage_lin_tf` returns siemens.
  `Zs=None` still reproduces the old ideal-source numbers.

### Evidence it is right
- Oracle open-circuit gain is flat (+40.12 dB @1 kHz → +40.39 @20 kHz), confirming
  `Gm*Rout = gm*ro` in the implementation, not just on paper.
- C++ stages match the oracle: JfetStage worst 0.015 dB full band; TrebleAttack
  ≤0.005 dB below 1 kHz, all three ATTACK positions.
- **The model is now level-independent like the pedal is** (see below) — the old
  one swung 30 dB across the sweep levels.

### ⚠ Two test gotchas this introduced (both fixed, don't re-trip them)
- **Settling.** Node G now floats on ~396 kΩ against the 22 nF ladder, adding a
  time constant slow enough that TrebleAttackTest's old 0.25 s settle left a
  ~0.4 dB error at 200 Hz that looks exactly like a model error. Settle is now
  2 s (agreement ≤0.005 dB).
- **The "HF error must shrink 48k→96k" assert** now also passes when the 48 k
  error is ALREADY negligible — there is no warp left to shrink, and the
  rate-to-rate difference is measurement noise.

---

## ✅ J201 BOUNDARY FIT — `analysis/fit_jfet_boundary.py` (2026-07-22, session 4)

Objective: the drive-min OD-path SHAPE (`drive-0700_base-od.wav`, segment
`sweep_clean_-36`), mean-removed dB on a 1/12-oct log grid, 50 Hz–8 kHz. Shape-only
is legitimate *now* because the pedal is provably linear at drive-min, and
mean-removal makes the cost blind to makeup and to every unfit taper. Renders are
trimmed to the first 22.6 s (both sweeps, identical segment offsets) → **1.4 s/eval**.

```
nominal (gm 0.69 mS)                        7.53 dB RMS
coarse grid best (210 evals)                1.86
Nelder-Mead refine                          1.58   gm 0.0911 mS
1-D refit, ro/rq2 held at nominal           1.56   gm 0.090  mS   <- USE THIS
```

### What is and is NOT measured here

- **`jfetGm` IS identified** — a clean interior minimum (0.05 mS → 2.16, 0.09 → 1.56,
  0.20 → 3.73, 0.30 → 5.01 dB).
- **`jfetRo` and `jfetRq2` are NOT.** The free fit ran both to their upper bounds
  (10 MΩ / 94 MΩ) and the 1-D scans move the cost by **≤0.01 dB over a 16× range** —
  that is the ideal-current-source limit, i.e. "large enough not to matter", not a
  measurement. Holding them at nominal 200 k / 1 M costs 0.02 dB. **Do not commit
  10 MΩ/94 MΩ as a finding**; they are a fit artefact of an inert direction. The full
  grid does show a weak preference for ro ≳ 600 k (0.15 dB), which is the only real
  content in them.

### The cross-check that makes gm credible — ABSOLUTE LEVEL

The objective is mean-removed, so it **cannot see level at all**. Level therefore
tests the fit rather than being fitted by it, and it agrees:

```
                          drive-min sweep RMS vs capture
  nominal gm 0.690 mS            +12.12 dB   (hot)
  fitted  gm 0.091 mS             -1.73 dB
  fitted gm, nominal ro/rq2       -1.91 dB
```

A 14 dB level error collapsing to ~2 dB — with makeup and both tapers still unfit —
under a parameter chosen by a level-blind objective is strong corroboration. It also
retro-explains the dsp-validator finding that the chain ran **3–10× too hot into the
clipper**: same direction, same order of magnitude, one cause.

### ⚠ The degeneracy you must know about before committing `kGm`

**Shape alone cannot distinguish a 7.6× lower `gm` from a ~10× larger `C3`.** Checked
analytically on the front-end oracle (`jfet_stage_lin_tf` × `jfet_source_z` ×
`treble_attack_tf`, both of which take `C3` as a keyword):

```
  A  gm 0.069 mS, C3 220n     shape reference        level @1k  -19.4 dB
  B  gm 0.690 mS, C3 2u2      0.63 dB from A                    +0.7 dB
  C  gm 0.690 mS, C3 220n     2.99 dB from A (nominal)          -0.9 dB
```

A and B are 0.63 dB apart in SHAPE — inside this fit's own 1.56 dB residual — and
**20 dB apart in LEVEL**. Both kill the C3 shelf; A does it by removing the
degeneration (`k0 = 1+gm*R6 → 1`), B by moving the shelf zero below the audio band so
it is a flat gain. Since `k0` is the only in-model handle on that shelf, a shape-only
fit *had* to express it as gm. **It is the level column that chooses A** — B leaves
the chain +12 dB hot. Worth knowing because a large-`C3` revision difference is
exactly the kind of thing this schematic has already sprung twice (C33 22n vs 2200pF,
C13 220n vs 22n), and if a later measurement ever contradicts the low gm, C3 is the
first place to look — it would need `jfetC3` adding to `FitParams` to test in the
full chain.

### Is `gm = 0.09 mS` physically defensible?

Partly, and it should NOT be committed on this evidence alone. Datasheet-nominal is
0.69 mS. Working the J201 self-bias at the LOW corner of the part spread
(IDSS 0.2 mA, |Vp| 1.5 V, R6 = 3k3) gives Id ≈ 0.11 mA and **gm ≈ 0.20 mS** — so the
fit sits ~2× below the plausible low corner, not the ~11× the earlier coarse scan
suggested. Combined with the level corroboration this is far stronger than any of the
three rejected step-2 fits, but the honest position is: **hold it in the analysis
scripts, let step 2 vote on gm independently from the harmonics, and commit
`JfetStage::kGm` only if the two objectives agree.** They constrain gm in genuinely
different directions — lowering gm cuts the drain current (less clipper drive) while
*raising* vgs by `k0` (more J201 curvature), so the harmonic profile is not just a
restatement of the level.

---

## ❌ STEP 2 RE-FIT — the result (2026-07-22 session 4). READ BEFORE RE-RUNNING IT.

Full log: **`analysis/fit_logs/step2_refit.log`**. Cost 7553.9 → 677.3 (3 starts, best of
677/940/984 — badly non-convex). Fitted point:

```
jfetGm 0.00055076 | jfetSatPos(s) 0.43262 | jfetSatNeg(a) 4.6223
clipA0 3.0171 | clipSatLo 0.64385 | clipSatHi 1.8783 | driveTaperExp 1.6575
held: jfetRo 200k, jfetRq2 1M
```

### Both acceptance tests FAIL

- **A — `jfetGm` disagrees with the shape fit by 6.1×** (0.551 mS here vs 0.090 mS from
  the drive-min shape). The over-determination test fired, exactly as it was set up to.
- **B — the clipper is *less* physical than the last rejected run.** `clipA0` = **3.02**
  vs circuit.md's 20–30 (the previous rejected fit said 7.3), and `clipSatLo+Hi` =
  **2.52 V** vs the ~7 V R19-dropped rail.

### THREE parameters are resting on constraints — so this is a box artefact

```
clipA0     3.0171   <- its LOWER BOUND is 3        (pinned)
clipSatLo  0.64385  <- floor 0.4                   (near-pinned)
|a| * s  = 1.99970  <- monotonicity gate is 2.0    (pinned to 4 decimals)
```

A param resting on a bound means the optimum is outside the box, so the value reported is
a property of the box, not of the pedal. **Do NOT respond by widening the bounds** — that
was tried at the last run and the fit simply walked further out. The gate is doing its job.

### What the failure actually diagnoses — the J201 shaper has NO CEILING

Compare how the harmonics GROW across the drive sweep, capture vs fitted model:

| | drive-min | drive-max | growth |
|---|---|---|---|
| capture H2 | −36.0 | −30.0 | **+6.0 dB** |
| model H2 | −37.8 | −15.9 | **+21.9 dB** |
| capture H3 | −59.2 | −29.0 | +30.2 dB |
| model H3 | −61.2 | −29.6 | +31.6 dB |

**H3 tracks almost perfectly; H2 grows nearly 4× too fast in dB.** The real pedal's H2
*saturates* — it is nearly flat across the whole drive sweep — while the model's grows
without limit. That is precisely the signature of the flagged carry-forward: the
square-law shaper is **unbounded** (`g(w) → w + a*s²`, slope 1, no ceiling) and
`railEnabled = false`, so **nothing anywhere between the input jack and the CD4049 limits
the J201's own output**. A real J201 drain on a 9 V rail swings at most ≈ ±4 V.

The pinned `|a|*s = 1.9997` is the fitter *confessing this*: raising `|a|*s` is the only
lever the current shape offers for bending the even term over, so the optimiser drove it
straight into the monotonicity boundary trying to build a ceiling out of a shape that
does not have one. It then dropped `clipA0` to its floor and the clip ceilings toward
theirs — all three constraints binding at once — because the only other way to stop the
runaway H2 is to make everything downstream weaker. **The fit is not wrong about the
data; the model is missing a limiter.** This also explains the `gm` disagreement:
harmonics-vs-drive is being distorted by the missing ceiling, so its `gm` is not
trustworthy, and the shape fit's 0.09 mS (which is corroborated by absolute level) is
still the better estimate.

### ▶ What to do next (the fix, in order)

1. **Add an explicit asymmetric soft ceiling on the J201 drain current** in
   `JfetStage.h`, keeping `g` a clean linear+even core — do **NOT** try to get the bound
   by raising `|a|*s` (breaks monotonicity, and re-introduces H3 which currently matches
   almost perfectly and must not be disturbed). Asymmetric because the real drain clips
   hard toward the rail one way and toward cutoff the other; that asymmetry is also where
   the residual even content should come from once the shaper's own `a` stops carrying it.
   New fit params + `FitParams` entries + `offline_render.cpp` map entry; update
   `JfetStageTest` (the even/odd and monotonicity asserts still apply below the ceiling).
2. **Then re-run step 2.** Expect `|a|*s` to come off the gate and `clipA0` to rise; if
   `clipA0` still pins at 3, the clipper itself is the next suspect, not the J201.
3. Only then judge `jfetGm` again — with the ceiling in place the two objectives are
   finally measuring the same thing.

**Do not commit any constant from this run.** Nothing from it is committed; the analysis
scripts hold `jfetGm` at nominal and `jfetRo`/`jfetRq2` at nominal.

---

## 🔬 The measurement work that established all of this

### 1. The capture is LEVEL-INDEPENDENT — so the pedal is linear at drive-min
`drive-0700_base-od.wav` shape re 200 Hz, across the four sweep levels:
```
                   50     82    110    200    300    500   1000   2000   3000   5000   8000
sweep_clean_-36  -4.73  -3.73  -2.19  +0.00  -2.66  -1.56  -1.40  +6.04  +6.54  -4.61  -5.52
sweep_drv_-18    -4.74  -3.74  -2.20  +0.00  -2.82  -1.60  -1.51  +5.03  +5.11  -5.77  -5.14
sweep_drv_-6     -5.19  -4.14  -2.43  +0.00  -3.63  -2.42  -2.58  +0.24  -0.34  -5.09  -3.95
```
Identical to ±0.15 dB from −36 to −18 dBFS. **So that shape IS the pedal's true
small-signal OD transfer** — it is a hard target, not a compressed artefact. The
OLD model swung 30 dB over the same range (+29.26 → +0.75 at 2 kHz), which is the
independent confirmation that it ran far too hot into the clipper.
**Re-use this test** — it is the cheapest way to tell "wrong filter" from "wrong
operating point", and it needs no new captures.

### 2. The sweep FR is trustworthy — checked against harmonic-immune fixed tones
The handover previously suspected harmonic contamination of the swept-sine
transfer. For THIS measurement it does not apply: the test signal's fixed-tone
segments (82.41/110/220/440/1k/2k/4k/8k) measured by exact-bin projection of the
FUNDAMENTAL ONLY agree with the sweep-derived shape to ~1 dB (82 Hz −3.78 vs
−3.73, 110 Hz −2.23 vs −2.19). Tone script: `scratchpad/tone_fr.py` pattern —
worth re-creating in `analysis/` if it is needed again.
⚠ The suspicion may still hold for the GRUNT cut matched pair, which is a much
more marginal measurement — that item is still open.

---

## ⚠ STILL OPEN — the ~320 Hz treble-net notch (schematic vs hardware)

**Parked by user decision 2026-07-22** in favour of doing the J201 boundary first.
Do not lose it: it is the largest remaining structural discrepancy.

The C5/C9/C6 ladder and R7 form a two-path cancellation into node M. The drawn
network puts a **~28 dB notch at ~322 Hz**. The capture has a dip at the right
frequency (**334 Hz**) but only **−3.4 dB** deep. What was ruled out:

- **Mis-read topology** — re-verified at pixel zoom on BOTH schematics. The ladder
  really does tie back to node M, and the ATTACK pole really is C8's bottom plate.
- **Component tolerance** — Monte Carlo, 400 draws at ±20 % caps / ±5 % resistors:
  the frequency moves 287–362 Hz (the measured 334 Hz sits comfortably inside),
  but the **shallowest notch of 400 draws is −23 dB**. Depth is NOT tolerance-
  sensitive, unlike the bridged-T.
- **A single plausible value change** — scanning ladder cap scale × shunt-R scale
  never got below ~4.5 dB cost, and its best point (440 pF caps, 68k/220k shunts)
  is a redesign, not a correction.
- R7 = 200 k sits almost exactly at the worst-case balance point (−32.7 dB); you
  need R7 off by ~5× to get a mild dip.

Note the notch is much shallower in the ASSEMBLED chain than in the isolated
analytic stage (rendered chain at nominal shows ~−5.6 dB at 300 Hz vs the capture's
−2.66), so this may matter less than the isolated numbers suggest — **re-measure it
after the gm/ro fit before spending more on it.**

Most likely explanation on the evidence: our schematic is the **original-B7K clone**
and the captured unit is a real **B7K Ultra** (circuit.md says exactly this in its
header). If so the front end genuinely differs and the ladder values become fit
parameters — but that is a decision, not a conclusion.

---

## ⚠ STILL OPEN — 8× oversampling anomaly at one clipper drive

Found while re-validating `OSValidationTest`. There is a narrow band of clipper
drive where **8× is WORSE than 2×** — oversampling locally goes backwards.

**It is NOT caused by the restructure.** The pre-restructure build has the same
anomaly at a different INPUT amplitude, because it ran ~22 dB hotter into the
clipper. 8× alias/sig (dB) vs input amp:
```
  pre-restructure : 0.05 **-21.8** | 0.20 -35.1 | 0.35 -34.1 | 0.50 -37.3 | 0.70 -37.3
  post-restructure: 0.05  -40.5    | 0.20 -40.5 | 0.35 -40.5 | 0.50 **-17.4** | 0.70 -23.1
```
and `0.05 * 10^(22/20) ~= 0.63` — **both break at the same clipper drive.** The
test's fixed probe simply slid onto the bad zone. Also note the post-restructure
build is at the −40.5 dB measurement floor across most of the range, i.e. BETTER
than the old build everywhere except that zone.

Localisation done so far: the OD region driven directly at 384 kHz is provably
clean (non-harmonic content ~1e-4 relative, and it IMPROVES with rate:
1e-2 at 192 kHz → 1e-4 at 384 kHz, measured stage-by-stage through
JFET → treble → drive → clipper → recovery → both SKs). There is no
self-oscillation (silence in → exactly 0.0 out). So the anomaly is in the
**clipper/decimator interaction at that operating point**, not in any one stage.

`OSValidationTest` now gates at amp = 0.2 and prints the full amp × order sweep
unconditionally, flagging the bad zone, so it cannot hide behind a green test.
**Root-causing it is an open item.**

---

## Step 2 — reshape VALIDATED, constants NOT committed

### What changed (committed, `f9d41d0` + `ccfc931`)
`src/dsp/JfetStage.h` — the waveshaper was **structurally wrong** and has been replaced.
Was per-polarity `sat*tanh(w/sat)`; now a **square-law even-shaper**:
```
g(w)  = w + a*s^2*(1 - sech(w/s))                      <- linear + EVEN
F(w)  = w^2/2 + a*s^2*(w - s*gd(w/s)),  gd(x)=2*atan(tanh(x/2))   <- antiderivative, for ADAA
```
The odd part is **purely linear → ZERO intrinsic H3**; the even bump makes H2/H4 only.
Slope at 0 is exactly 1 (so `-G0` remains the linear gain); monotonic while
`|a|*s < 2.598` (max |sech·tanh| = 0.3849).

**Param slots are REUSED, not renamed** (to avoid plumbing churn across
PedalChain/OfflineRender/fit_nonlinear.py): `kSatPos`/`jfetSatPos` = knee **`s`**;
`kSatNeg`/`jfetSatNeg` = even strength **`a`** (SIGNED). Nominal `kSatNeg` 2.6 → **0.3**.
A clean rename is deferred polish. Documented at `JfetStage::waveshape()` and in
`FitParams.h`.

**Why:** the real pedal's low-drive OD is even-dominant (captured H2 −36 / H3 −59 dB at
drive-min = 23 dB separation) — a JFET square-law fingerprint. `tanh` is an odd map whose
w³ term forces H3 whenever it makes H2, so it structurally cannot reach that separation
(proven by fit: no parameter combination got drive-min H3 below −50 dB). The new shape
measures H2 −15.9 / **H3 −308 dB** in the unit test — the wall is gone.

### The fit result (best cost 149.4, from nominal 3374.8)
```
jfetG0 4.583 | jfetSatPos(s) 10.585 | jfetSatNeg(a) 0.232
clipA0 7.275 | clipSatLo 0.773 | clipSatHi 1.012 | driveTaperExp 1.598
```
Harmonic match is good (drive-min H2 −35.6 vs capture −36.0) and **drive-min is finally
even-dominant** — the structural win the reshape was for.

### Why the values are NOT trustworthy (four checks, do not re-derive)
1. **Physically implausible.** `clipA0` 7.3 vs circuit.md's community-measured **20–30**;
   `clipSatLo+Hi` = **1.79 V** vs the ~7 V R19-dropped 4049 rail (hard-bounded above by
   the 8.6 V supply); `jfetG0` 4.58 vs nominal 15.
2. **NOT a bounds artefact.** Run 1 pinned `jfetSatPos` at exactly its 6.0 ceiling; the
   bounds were widened (reasoning recorded in `fit_nonlinear.py`) and run 2 moved
   **further out**, not back.
3. **NOT a flat degeneracy** — the obvious hypothesis, and it is WRONG. Scaling
   `g0·k, a/k, clipSat·k` (which preserves both the clipper drive ratio and J201's
   H2/H1 ∝ a·g0) gives a REAL minimum at k=1:
   `k=0.6→288.7, 0.8→168.3, 1.0→149.4, 1.5→186.5, 2.5→293.5, 4.0→447.7`.
   The objective actively REJECTS the physically-nominal combination (k=4 → 448).
4. **The doc-mandated second constraint on `clipA0` is INERT.** `FitParams.h` requires A0
   to be fit against the GRUNT voicing AND the drive sweep "not either alone", because A0
   sets the clipper input impedance `R18/(1+A0)` and hence the GRUNT corners. Built that
   check (`analysis/grunt_a0_check.py`). **Result: the boost−flat separation is
   A0-INDEPENDENT** (−0.13 → −0.27 dB across A0 = 7.3…90) — clipper compression washes
   the corners out. RMS only weakly prefers A0≈25 (1.43) over 7.3 (1.74). So **A0 has no
   independent physical anchor in these captures.**

### Plus: the absolute-level constraint is confounded with STEP 4
OD-vs-clean level is makeup-independent (both paths share the output chain) and would pin
the nonlinear scale — but the fitted point runs **+3.7…+5.2 dB hot**:
```
drive   min    9:30   noon   2:30   max
err   +4.08  +4.14  +3.65  +5.13  +5.16    (render OD-clean minus capture OD-clean)
```
That is mostly a FLAT offset at a fixed LEVEL=noon, i.e. the un-fit `levelTaperExp`. Only
the ~1.5 dB drive-dependent part belongs to step 2. **So this constraint only becomes
usable after step 4** — add an OD-vs-clean level term to the objective then.

**User decision 2026-07-22:** defer the step-2 commit. (Since amended — the HF blocker
above now takes priority over steps 3–4 as well.)

---

## 🔬 dsp-validator report (2026-07-22) — JfetStage FAIL (fixed), Clipper PASS

Run per project policy after the reshape. It found a **real bug** plus several results
that corroborate and sharpen the blocker above. All numbers below were verified by the
agent with compiled probes against the real headers, and the headline math was
independently re-checked before acting.

### ❗ BUG FOUND AND FIXED — the monotonicity bound was wrong
`JfetStage.h` and `JfetStageTest.cpp` documented "monotonic while `|a|*s < 2.598`,
because max `sech*tanh` ≈ 0.385". **That conflates two different extrema:**
```
max sech(x)tanh(x)  = 0.5000   -> correct bound |a|*s < 2
max sech^2(x)tanh(x)= 0.3849   -> 1/0.3849 = 2.598   (what was written — WRONG)
```
**Consequence, not academic:** the step-2 run-2 fit point `s=10.585, a=0.232` gives
`|a|*s = 2.456`, **min slope −0.21** → the waveshaper FOLDS BACK inside the signal range.
That is a **third independent reason** those constants must not be committed, and it
plausibly explains part of why the fit drifted somewhere strange (a fold-back can score
well on H2 alone).

**Fixed 2026-07-22:** constant corrected to 2.0 in both files with a "do not write 2.598"
note, and `fit_nonlinear.py` now has an explicit `monotonic()` feasibility gate
(`|a|*s < 2` → cost 1e6). The gate is necessary because this is a **PRODUCT** constraint,
which box bounds cannot express. ctest still 16/16.

### JfetStage — everything else about the reshape verified correct
- Even/odd split is **exact**: odd part ≡ `w` to 3.6e-15 over w ∈ [−30, 30]. Raw-map
  harmonics at 8 V drive: H2 −18.1, **H3 −121.9** (FP floor), H4 −28.0, H5 −128.1 dB.
- **ADAA preserves the zero-H3 property** (this was worth confirming): `F` splits into an
  even part `w²/2` whose ADAA quotient is `(u+p)/2`, and an odd part invariant under
  `(u,p)→(−u,−p)`. Measured with ADAA on: H2 −18.1, **H3 −122.0** — identical.
- Antiderivative exact: `max|F'(w) − g(w)| = 1.0e-7`, precisely the `h²` truncation of the
  central difference at `h=1e-6`. `gd'(x) = 1/cosh(x)` confirmed analytically.
- `g'(0) = 1` exactly; `g(0) = 0`. Corners unchanged: HP **144.7 Hz**, shelf zero
  **219.2 Hz** / pole **718.4 Hz** — all match circuit.md.
- Numerics safe: `cosh` overflow → `sech→0` → degrades to `g(w)=w+a*s²`, no NaN; the
  Gudermannian form correctly avoids `atan(sinh)` overflow.

### ⚠ NEW: ADAA imposes a linear-region lowpass (matters for Phase 8)
Because the odd part is *exactly* linear, ADAA1 degenerates to a 2-point average
(`|H| = cos(pi f/fs)`) over the whole linear region — i.e. for essentially the entire
signal, not just where it distorts:

| OD-region rate | 5 kHz | 10 kHz | 20 kHz |
|---|---|---|---|
| 48 kHz (**OS = 1×**) | −0.49 dB | **−2.02 dB** | **−12.02 dB** |
| 96 kHz (2×) | −0.12 | −0.46 | −2.06 |
| 192 kHz (4×) | −0.03 | −0.12 | −0.47 |

`PedalChain::prepareOd` enables ADAA unconditionally and `PedalDSP` calls it at base rate
for order 0, so at **OS = 1× this droop is live and is LARGER than the bilinear warp** the
dsp.md "low-OS top-octave restore" is designed to fix. Harmless at the 4× default. Noted
in `PedalChain.h`. **Action for Phase 8: account for it in the low-OS shelf fit, and
consider gating ADAA off at order 0.**

### ⚠ NEW: the shaper is unbounded AND nothing limits before the clipper
`g(w) → w + a*s²` asymptotically — slope 1, no ceiling. Measured J201 output
(kInputRef 0.87, nominal G0=15, ATTACK flat):

| input | 100 Hz | 1 kHz |
|---|---|---|
| −20 dBFS | 0.90 V | **4.69 V** |
| −12 dBFS | 2.55 V | **11.25 V** |
| 0 dBFS | **10.41 V** | **37.88 V** |

A real J201 drain on a 9 V rail swings at most ≈ ±4 V, so the model leaves the physical
envelope from about **−20 dBFS at 1 kHz** — ordinary bass-player input, not an edge case.
And because `railEnabled = false`, there is currently **no limiter anywhere between the
input jack and the clipper**: measured DriveStage output **89.7 V @ 100 Hz** and **546 V
@ 1 kHz** at 0 dBFS/drive-max, against a TL072 ceiling of ±3.3 V. circuit.md and
build-plan risk #9 both say IC2_A rails *before* the 4049 at high drive — that behaviour
is entirely absent today.

Verdict: relying on the CD4049 for all limiting is defensible for *stability* (the output
is always bounded, no NaN) but **not for level calibration**, and **not for low-drive
character** — the regime the even-shaper was fit for, where the real pedal's dominant
nonlinearity may be the J201 hitting its own rails. **Fix by adding an explicit asymmetric
soft ceiling on the JFET output** (keeping `g` a clean linear+even core). **Do NOT try to
get a bound by raising `|a|*s`** — that breaks monotonicity and re-introduces H3.

### Clipper.h — PASS, no structural fault
Norton reduction of the (Cg+R16) branch re-derived by hand and **exact** (`i_in =
gIn(x−w) − ic`, `gIn = 1/(R16 + 1/gcG)`); trapezoidal companion convention consistent with
the other stages; `F'(w) = −gIn + gFb(vtc'(w) − 1)` is the exact derivative and is
strictly negative, so **Newton is globally convergent** from any warm start (no
divide-by-zero, no damping needed); VTC is C1 at `w=0`. `R18/(1+A0)` confirmed — measured
corners **899.1 / 144.4 / 35.8 Hz** reproduce CLAUDE.md's documented 896/144/36 exactly.
GRUNT mapping verified against `PluginProcessor.cpp`'s `{"Boost","Cut","Flat"}`.

### ⚠ NEW: do NOT fit A0 from the CUT-position corner
The cut (4n7) analytic corner is 1737 Hz but its measured −3 dB is 899 Hz, because
R18·C14's pole (2.19 kHz) is barely an octave above — the 4n7 response never reaches a
plateau, so "−3 dB from peak" is dragged down by C14, not the RC. **Inverting the
single-pole formula on the cut corner biases A0 low by ~2×.** Use flat/boost only.

### ⚠⚠ Root cause of the GRUNT flat→boost anomaly: EXCESS PRE-CLIPPER LEVEL
This independently corroborates the HF/loading blocker. The model *does* preserve the
step — but only below a clipper input level the chain currently exceeds. Separation vs
amplitude at the clipper, 100 Hz:

| Vin at clipper | A0=25, sat 3.15/3.85 | A0=7.28, sat 0.773/1.012 |
|---|---|---|
| ≤ 0.01 V | +4.93 dB | **+1.58 dB** |
| 0.1 V | +4.71 | +1.19 |
| 0.3 V | +2.94 | +0.22 |
| 1.0 V | **+0.07** | **+0.01** |

The small-signal value at A0=7.28 (**+1.58 dB**) is essentially the capture's **+1.38 dB**
— *the coupling model is right, the operating point is not.* Measured actual clipper input
at the check's operating point: **0.342 / 0.396 / 0.305 / 0.100 V** at 50/100/200/300 Hz —
squarely in the collapse knee. **The model runs 3–10× too hot into the clipper in the
50–300 Hz band.** Why cut→flat survives while flat→boost dies: cut sits 15–19 dB below
flat, so cut stays under the knee while flat and boost are both pressed against the same
ceiling — the gap nearest the ceiling vanishes first.

Note this also means **enabling `railEnabled` alone will not fix it**: ±3.3 V into the
clipper still gives a 0.00 dB step; the needed input is ≲0.1 V, an order of magnitude
below the TL072 rail. The excess is in `kG0`/taper/loading.

### ⚠⚠ NEW, UNRESOLVED: the two GRUNT capture numbers may be mutually inconsistent
Capture cut→flat is **+5.43 dB**, but every small-signal prediction is **15.6 dB**
(A0=7.28) / **19.3 dB** (A0=25). No memoryless saturator at one operating point can
compress a 15.6 dB gap to 5.4 while leaving a 1.58 dB gap at 1.38 — **compression is
monotone in level, so the upper gap must shrink at least as much.** Something is lifting
the cut curve in the capture. `blend=1.0` is genuinely 100 % OD, so the clean path is not
it. Most likely **harmonic contamination of the swept-sine transfer**: in the cut position
the in-band fundamental is ~20 dB down, so H2/H3 from the 25–150 Hz part of the sweep
landing in the 50–300 Hz window is a proportionally much larger share of band energy than
for flat/boost. **Resolve this (Farina harmonic-window separation, or a fixed-tone matched
pair instead of a sweep) BEFORE spending more search on this objective.**

---

## ✅ GRUNT position→cap map — VERIFIED against capture

Resolves circuit.md / `Clipper.h`'s longest-standing ASSUMED carry-forward (since Phase 5).
**The map is correct.** Measured 50–300 Hz, matched-pair vs the cut baseline:

| position | cap | measured |
|---|---|---|
| cut (`ref-od`, idx 1) | 4n7 | 0 dB (baseline) |
| flat (`grunt-flat`, idx 2) | 4n7∥47n = 51.7n | **+5.43 dB** |
| boost (`grunt-boost`, idx 0) | 4n7∥220n = 224.7n | **+6.81 dB** |

Monotone bin-by-bin (63 Hz +9.77/+14.83; 100 Hz +8.11/+10.39; 160 Hz +5.17/+6.03;
200 Hz +3.84/+4.37). Index mapping is correct end-to-end: **`PedalChain::gruntEnum()`
deliberately does NOT cast the index to the enum** (whose declaration order is
Cut/Flat/Boost = 0/1/2) — it remaps 0=Boost, 1=Cut, 2=Flat; `offline_render.cpp` parses
`--grunt {boost,cut,flat}` to match. Do not "simplify" that remap.

The uneven spacing (+5.43 then only +1.38) is physically expected: at A0=25 the cut corner
is ~1.7 kHz (above the band → heavily rolled off), flat ~158 Hz (in band), boost ~36 Hz
(already below the band). Once a corner drops under the band, extra capacitance buys
almost nothing.

⚠ **Open sub-anomaly (belongs to step 2, not the cap map):** the model reproduces the
cut→flat step but **flattens the flat→boost step to ~0 dB vs the capture's +1.38 dB** — at
EVERY A0 (7.3…90) AND at both the fitted and physically-nominal clipper ceilings (sat
3.15/3.85 gave +0.14 and made RMS *worse*: 2.74 vs 1.43). So it is neither the sat ceiling
nor A0; the model's clipper compresses away a level difference the real pedal preserves.
Suggestive: the ANALYTIC pre-clipper separation at A0=7.28 is **+1.41 dB**, nearly exactly
the captured +1.38 — consistent with the real clipper barely compressing here. Plausibly
another symptom of the HF/loading blocker. Revisit at the step-2 re-fit.

⚠ **Measurement trap (cost real time; now guarded in the script):** below ~40 Hz the
driven-sweep captures are noise — the matched-pair diff swings −5…−11 dB
non-monotonically. Averaging an "LF plateau" from 20 Hz reads that noise as "flat gives
LESS bass than cut" and looks *exactly* like a wrong cap map. **Use 50–300 Hz.**

---

## ✅ Step 1 — `kInputRef` anchored (unchanged this session)

`kInputRef` stays **0.87 V/FS**, now ANCHORED rather than nominal (`src/dsp/GainStaging.h`).
`bypass.wav` cal_1k returns at −0.012 dB vs the test signal → **unity round-trip rig**, so
the capture domain == DAW domain 1:1.

`kInputRef` is **degenerate with the clip ceiling** under audio-only captures: the
ref-clean DIST-off render is −3.894 dB under the capture at EVERY level step −36…−3 dBFS,
**std = 0.000** → K cancels in the linear path. So K is **SET, not measured**; 0.87 is the
test-signal design anchor. User decision 2026-07-22. Memory: `phase7-kinputref-anchor`.

---

## Reference data (measured — don't re-derive)

### Capture harmonic targets (`tone_220`, dB re fundamental) — the step-2 fit objective
```
drive  THD    H2     H3     H4     H5
min   -36.0  -36.0  -59.2  -69.9  -86.4
9:30  -34.4  -34.4  -55.3  -71.6  -83.5
noon  -31.0  -31.4  -42.0  -51.1  -56.8
2:30  -25.9  -31.9  -30.7  -38.4  -32.7
max   -22.9  -30.0  -29.0  -35.8  -28.8
```

### The clean deficit is MASTER-taper-dependent (feeds steps 4/5)
`ref-clean` (DIST off, pure linear) plug−capture = **−3.894 dB, flat across all levels**.
But across the MASTER sweep the real round-trip gain runs (gain-n12 corrected):
`master 0 / ¼ / ½ / ¾ / max → −19.6 / −8.2 / +0.95 / +10.7 / +12.3 dB`.
So the −3.9 dB at noon is NOT pure flat makeup — **fit `masterTaperExp` (step 4) BEFORE
committing makeup (step 5)**. Note master-min renders as a full mute in the plugin (taper
x=0 → 0) while the real floor is ~−40 dB — check the master taper floor when fitting.

---

## Tooling / gotchas (each of these cost real time)

- Python: **`/opt/homebrew/bin/python3.11`** (plain `python3` = 3.13, no numpy/scipy).
- **`analyze.py::align(render, orig)` returns a TUPLE `(render, lag)`** — unpack it.
- `captures.py::load_capture()` resamples rate-mislabeled files via the cal tone; use it
  (not `analyze.load`) for captures. Warns on non-`data` WAV chunks — harmless.
- **gain-n12 captures need +12.071 dB** to reach the base-gain frame (`gain_correction_db`;
  exact on the ref-clean anchor pair). Direction: ADD to the capture.
- Render CLI: `OfflineRender <in> <out> --os 8 <render_args...> [--fit key=val ...]`.
  EQ pots are KNOB-space in `render_args`; OfflineRender applies the `1-x` inversion —
  do NOT pre-invert.
- `--fit` accepts **any** `FitParams` field, so stages can be swept without a rebuild.
- A **full 84 s render is only ~6 s**, so full-signal A/B is cheap — don't assume it isn't.
- **Isolating one nonlinearity by setting the OTHER's sat huge is UNRELIABLE** (the
  linearised clipper's ~×48 loop gain re-saturates even at sat=50). Reason analytically or
  drive the real stage instead.
- **Setting `btC16` to ~0 does NOT "remove the notch"** — it turns the bridged-T into a
  72 Hz lowpass, so a nominal-vs-no-C16 difference is not a notch-depth measurement.
- When comparing FR, **normalise each curve to its own value at a reference frequency**
  (200 Hz here) and compare SHAPE. Median-normalising a curve with a deep notch shifts the
  whole thing and invents errors.

### How to reproduce the OD-path FR measurement
```python
orig = A.load('analysis/test_signal_48k.wav'); SEG = 'sweep_clean_-36'
f, m = A.transfer(A.seg_of(x, SEG), A.seg_of(orig, SEG))   # x = aligned capture or render
# normalise to 200 Hz, compare shapes; use drive-0700_base-od.wav (drive MIN => most linear)
```

---

## Analysis tooling added this session

- **`analysis/fit_nonlinear.py`** — the step-2 fitter. Objective = the `tone_220` harmonic
  profile (THD + H2..H5) across the drive sweep; harmonic RATIOS are level-independent, so
  it is valid before makeup. Renders a short synthetic tone per eval (~20× faster than the
  full file). Bounds widened after run 1 hit a ceiling; `--start=a,b,c,...` refines from an
  explicit point. ✅ `FIT_KEYS`/`NOMINAL`/`BOUNDS` updated for the restructure 2026-07-22
  (session 4) — `jfetG0` → `jfetGm`, `jfetRo`/`jfetRq2` in `HELD`, sat ranges rescaled to
  gate volts. (The old "add `jfetGmR6`" note here was VOID — that param no longer exists.)
- **`analysis/grunt_a0_check.py`** (NEW) — matched-pair GRUNT cross-check on `clipA0`.
  Guards the sub-40 Hz measurement trap. `key=value` args override any held param; bare
  numeric args are the A0 values to sweep.
- **`tests/JfetStageTest.cpp`** — rewritten for the square-law shape. Test 4 now uses an
  exact-bin DFT (200 Hz, 240 samples/period, 20 periods → zero leakage, so an absent
  harmonic reads at the numerical floor instead of a leakage-limited −60 dB) and asserts
  even-dominance; monotonicity is an analytic check on the static map; Test 5 is documented
  as the slope-at-0 == 1 assert.

---

## Remaining calibration steps

Order is set by `docs/calibration-and-gain-staging.md`, **amended twice** (both recorded
above): `masterTaperExp` before makeup, and now the **HF/loading fix before everything**.

0. ✅ **J201 output impedance → TrebleAttack boundary** — restructured AND fitted
   (`gm ≈ 0.09 mS`, held in the analysis scripts, `kGm` not yet committed).
1. ✅ `kInputRef` — done.
2. Nonlinear fits — reshape done, fit set correct, re-run DONE and **rejected**: the
   J201 shaper is unbounded, so H2 grows 22 dB across the drive sweep where the pedal's
   grows 6. **Add the J201 drain-current ceiling first (a CODE change), then re-fit.**
   Still wants an OD-vs-clean level term, which needs step 4 first.
3. Bridged-T reshape to the measured notch (334 Hz @ −3.36 dB). Decompose the treble net's
   own −16.69 dB @ 300 Hz contribution first.
4. Taper shapes (≥2 knob points/pot; the matrix has 4). Includes `masterTaperExp` and
   `levelTaperExp`; `driveTaperExp` is coupled into the step-2 fit and may want a re-touch.
5. Output makeup = level-match to captures (may exceed 1.0; no headroom pad). Decompose the
   deficit per `validation-and-capture.md` §4 first.
6. Rail clamps LAST — enable only after `kInputRef` is anchored (done) so stages don't clip
   against an arbitrary reference and corrupt the fits above.
