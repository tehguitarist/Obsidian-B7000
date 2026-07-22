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
| 2. CD4049 + J201 fits | ⚠ three fits rejected. **Session 7 (2026-07-23) found WHY: `fit_nonlinear.py`'s "harmonic ratios are level-independent" premise is FALSE — BLEND's clean bleed dilutes every harmonic by the OD-vs-clean level, so the fitter bought harmonic score with level and drove `jfetGm` 25× low.** The even-harmonic "ladder" was that artefact; the shaper shape is FINE and must NOT be reshaped. Fix the OBJECTIVE, then re-fit. Constants NOT committed. |
| 1b. **Mixer (BLEND/LEVEL)** | ✅ **DONE 2026-07-23 (session 8).** Topology verified at pixel zoom; crossfade law confirmed; clean bleed measured REAL and larger than modelled, by TWO independent routes that now agree to 1.4–3.9 dB; LEVEL taper measured at **p ≈ 2.25** (36/36 estimates agree, shipped is 1.43). Two bad captures found+fixed along the way (see "STEP 1 — THE MIXER"). Prerequisite for step 2. |
| 2b. **Re-anchor `jfetGm`** | ✅ **DONE 2026-07-23 (session 9).** Bleed-aware OD/clean fundamental ratio through the corrected mixer → **gm ≈ 0.10 mS**, corroborates the old 0.090 bleed-FREE. `analysis/reanchor_gm.py`. Surfaced an OD-path LF-excess lead (→ `clipA0`/GRUNT coupling, step 3). |
| 3. **Fix objective + fit shaper** | ◀ **NEXT.** Harmonic-TO-harmonic ratios in `fit_nonlinear.py`; hold gm=0.10 mS. NOT started. |
| 3′. Bridged-T reshape | not started (was blocked; **now unblocked**) |
| 4. Tapers (`level`/`master`/`drive`) | not started — but `levelTaperExp ≈ 2.25` is already measured (session 8, 36 agreeing estimates), commit it here not there |
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
4. ✅ **DONE — asymmetric soft ceiling on the J201 drain current** (`JfetStage.h`;
   `jfetCeilPos`/`jfetCeilNeg` in `FitParams` + the `--fit` map; `JfetStageTest`
   Test 6; numeric monotonicity gate in `fit_nonlinear.py`). ctest 16/16,
   dsp-validator run. The even bump also changed shape (`1-sech` → `tanh^2`) so its
   tail matches the ceiling's — see `JfetStage.h waveshape()`; that is what makes the
   monotone region 2× wider, and it moves the ceiling-off `|a|*s` bound to 2.598.
5. ✅ **RUN — step-2 re-fit WITH the ceiling** (`analysis/fit_logs/step2_ceiling.log`).
   **The ceiling worked and the fit is still rejected — but the binding constraint has
   MOVED to the clipper.** See "STEP 2 RE-FIT #2" below before doing anything else.
6. ✅ **DONE — rail clamps tested as the suspect, and ELIMINATED.** See "RAILS ARE NOT
   THE ANSWER" below. Enabling them is **inert** at the fitted point (cost 428.6 →
   428.6, identical) and worth −0.1 % at nominal. A **real latent bug** was found and
   fixed on the way (`railNeg` was signed → an enabled clamp emitted DC; commit
   `926c0cc`), so this had to be done regardless — but it does not unblock step 2.
7. ✅ **DONE (session 7, 2026-07-23) — the blocker is DIAGNOSED and it is the FIT
   OBJECTIVE, not the shaper and not the clipper.** BLEND's clean bleed makes the
   harmonic ratios level-dependent, so the fit traded level for harmonics. See
   "THE EVEN-HARMONIC LADDER WAS AN ARTEFACT" below — read it before anything else.
   **No code was changed; the shipped shape is correct and must not be reshaped.**
8. ✅ **DONE (session 8, 2026-07-23) — PLAN STEP 1, THE MIXER, IS SETTLED.** Topology
   verified at 600-dpi pixel zoom; the crossfade law confirmed (harmonics affine in the
   BLEND knob to 1.6 %/4.0 %); the LEVEL taper measured bleed-free at **p ≈ 2.25, not the
   shipped 1.43** (36/36 tone×harmonic×knob estimates agree); and **the clean bleed is
   REAL and at least as large as modelled**, confirmed by TWO independent routes now
   agreeing to 1.4–3.9 dB (clean within a couple of dB of OD at "100 % OD"). See "STEP 1
   DONE — THE MIXER IS SETTLED" below. **The recorded prediction resolved in favour of
   "the bleed matches"**, so `jfetGm ≈ 0.090 mS` is not obviously a bleed artefact. Found
   and fixed two bad takes of `level-1430_base-od.wav` along the way (odd-harmonic
   contamination, then a BLEND-at-noon capture mistake) — both confirmed fixed by the data
   converging, not just by the explanation being plausible. Nothing committed to the DSP.
9. **THE J201 PLAN, steps 2-4 (agreed with the user 2026-07-23). See
   "THE PATH FORWARD FOR THE J201" below for the full rationale; status:**
   1. ✅ **Settle the MIXER first** — DONE (session 8), see above.
   2. ✅ **Re-anchor `jfetGm`** — DONE (session 9). **gm ≈ 0.10 mS** (bleed-free, corroborates
      0.090). See "✅ STEP 2 DONE — `jfetGm` RE-ANCHORED". `analysis/reanchor_gm.py`.
   3. **▶ NEXT — Fix the harmonic objective** (harmonic-TO-HARMONIC ratios in
      `fit_nonlinear.py`), hold gm=0.10 mS, then fit the shaper. NOT started.
   4. **Accept only on corroboration the objective could not see.**
   Steps 1-2 are what make 3 falsifiable; do not skip their results when running it.
10. Then step 3′ (bridged-T), step 4 (tapers), step 5 (makeup), step 6 (rails proper).

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

---

## ⚠ STEP 2 RE-FIT #2 — WITH the J201 ceiling (2026-07-22). Better, still not committable.

The ceiling landed (`JfetStage.h`, see "the fix" below — all four sub-items done, ctest
16/16, dsp-validator run). Re-fit log: **`analysis/fit_logs/step2_ceiling.log`**.
Cost **6910.4 → 428.6** (vs the previous run's best of 677.3 from nominal 7553.9).

```
jfetGm 2.7373e-05 | jfetSatPos(s) 0.19433 | jfetSatNeg(a) 5.5398
jfetCeilPos 0.25504 | jfetCeilNeg 0.1971
clipA0 17.222 | clipSatLo 0.4 | clipSatHi 0.40171 | driveTaperExp 2.9938
held: jfetRo 200k, jfetRq2 1M
```

### What the ceiling DID fix — it was the right diagnosis

| | before (no ceiling) | after | capture |
|---|---|---|---|
| H2 growth, drive-min → max | **+21.9 dB** | **+10.1 dB** | **+6.0 dB** |
| `clipA0` | 3.017 (**pinned** on its floor) | **17.222** (free, near circuit.md's 20–30) | — |
| `\|a\|*s` | 1.9997 (**pinned** on the gate) | 1.077 (free) | — |
| best cost | 677.3 | **428.6** | — |

Two of the three binding constraints from the last run are gone, and the H2-growth error
— the thing that identified the missing ceiling — closed by about two thirds. **The
structural gap was real and the fix addresses it.** H3 also still tracks (drive-min
−58.8 vs −59.2; max −26.3 vs −29.0), so the ceiling did not disturb it, which was the
main risk.

### Why it is STILL rejected — the constraints MOVED, they did not go away

```
clipSatLo    0.4      <- RESTING ON ITS FLOOR (0.4)
clipSatLo+Hi 0.802 V  <- vs the ~7 V R19-dropped 4049 rail. WORSE than the last run's 2.52 V.
driveTaperExp 2.9938  <- 0.2% off its 3.0 ceiling, i.e. pinned in all but name
ceilNeg/s    1.01     <- resting on the MONOTONICITY boundary (needs >~ 1)
jfetGm       0.0274 mS <- the shape fit + level cross-check say 0.090 mS
```

Read together these all point the same way: **every parameter that can make the signal
reaching or leaving the clipper weaker has gone to its limit.** Lower gm, maximum drive
taper exponent, minimum clip ceilings. That is the same signature as the last run, one
stage further downstream — the fitter is still starving the chain to compensate for
something upstream that is too hot, and it is now doing it through the clipper's rails
rather than through the J201's shaper.

Also note H2 is now ~7 dB LOW at drive-min (−43.3 vs −36.0) while nearly right at
drive-max — the fit bought its improved *slope* partly by dropping the whole curve.

### The gm disagreement narrowed but flipped sign

`jfetGm` 0.551 mS (6.1× ABOVE the shape fit's 0.090) → **0.0274 mS (3.3× BELOW it)**. The
over-determination test still fails, but by half as much and from the other side, so the
two objectives now bracket 0.090 mS rather than agreeing on nothing. **Do not average
them.** The shape fit's 0.090 mS remains the better-evidenced number (it is corroborated
by an independent absolute-level check that its own objective could not see).

### ▶ Verdict and next suspect

Per the acceptance rule set for this run: `clipA0` came off its floor, so **the J201 is no
longer the binding problem — the CLIPPER is.** Specifically `clipSatLo/clipSatHi`, which
the fit wants at 0.80 V total against a physical rail of ~7 V (hard-bounded above by the
8.6 V supply). A 9× discrepancy in a quantity that is bounded by a supply voltage is not a
fit result, it is a signal that the level arriving at the clipper is still far too high.

Candidates, in the order they should be checked:
1. **`railEnabled` is still false**, so `DriveStage` has no TL072 clamp at all
   (measured 546 V at 0 dBFS/drive-max pre-ceiling; the ceiling cuts the J201's
   contribution but IC2_A's own ±3.3 V rail is still absent). circuit.md and build-plan
   risk #9 both say IC2_A rails BEFORE the 4049 at high drive. Step 6 puts rails last for
   a good reason (they must not clip against an unanchored reference), but `kInputRef` IS
   anchored now — so the ordering constraint that deferred them is discharged, and
   enabling them may be a prerequisite for step 2 rather than a successor to it.
   ⚠ Note dsp-validator's earlier finding that rails ALONE will not fix the GRUNT
   flat→boost anomaly (±3.3 V into the clipper still gives a 0.00 dB step; that needs
   ≲0.1 V) — so treat this as necessary, not sufficient.
2. `driveTaperExp` pinned at 3.0 says the drive taper cannot get quiet enough at the low
   end either. That is a step-4 parameter being asked to do step-2 work.
3. Only then re-examine the J201 ceiling values themselves.

**Nothing from this run is committed.** `JfetStage::kCeilPos/kCeilNeg` ship at their
NOMINAL 1.0/0.5 (physically argued, not fitted); the analysis scripts hold everything else
at nominal.

---

### ▶ What to do next (the fix, in order) — ALL FOUR DONE 2026-07-22, see above

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

## ❌ RAILS ARE NOT THE ANSWER (2026-07-22, session 6) — suspect #1 eliminated

The handover named `railEnabled = false` as the first candidate for the clipper
starving itself. **Measured, and it is not.** Same objective, rails off vs on:

| point | rails off | rails ON | H2 growth off → on |
|---|---|---|---|
| nominal | 6910.4 | 6906.3 (**−0.1 %**) | 17.5 → 15.7 dB |
| step2_ceiling best | 428.6 | **428.6 (identical)** | 10.1 → 10.1 dB |

At the fitted point the rails are **exactly inert** — `jfetGm` is so low there that no
op-amp output gets near ±3.3 V, so a ±3.3 V clamp never engages. This is the
quantitative version of dsp-validator's earlier warning that rails are "necessary but
not sufficient": at the operating point the fitter actually chose, they are not even
*active*. The null is trustworthy — the flag is verified plumbed (`--print-fit` reports
`railEnabled=1`) and it **does** move the cost at nominal, so it is inert by operating
point, not by mis-wiring.

### ⚠ But a REAL BUG was found doing it — commit `926c0cc`
`RailClamp` uses `railNeg` as a **magnitude** (`x < -(railNeg - h)`), while `FitParams`
shipped `railNeg = -3.3`. Compiled probe against the real header:

```
   x     as-wired(-3.3)   intended(+3.3)
-5.00           3.3000          -3.3000
-1.00           3.3000          -1.0000     <- every sample below +2.95 V
 0.00           3.3000           0.0000        returned a CONSTANT +3.3 V
 1.00           3.3000           1.0000
```

**An enabled clamp emitted DC, not audio.** Invisible since Phase 4 because
`railEnabled` defaults to false and **no test exercises the enabled path** — every
stage test validates a linear oracle with rails off. It would have surfaced as a
garbage step-2 re-fit the moment rails were switched on, i.e. exactly the next thing
this handover told the next session to do. Fixed at the source (`railNeg = 3.3`) and
`setRailVoltages` now takes `|v|` because `railNeg` is a `--fit` key and a sweep can
still pass a signed value. **A `RailClampTest` covering the ENABLED path is still
missing — that gap is the actual root cause and it is not yet closed.**

---

## ✅✅ THE EVEN-HARMONIC LADDER WAS AN ARTEFACT — BLEND CLEAN-BLEED (session 7, 2026-07-23)

> **READ THIS BEFORE THE SECTION BELOW.** The "even-harmonic ladder" section that
> follows is **SUPERSEDED**. Its measurements are all reproducible, but its
> *diagnosis* — "the shaper structurally cannot make H2 without H4" — is WRONG, and
> the reshape it recommends (`g(w) = T(w) + (a/2)w²`) **must not be built**: as
> written it is unbounded AND non-monotone (a bare `+a w²/2` added to a bounded core
> has slope `1 + a*w`, which goes negative for `w < -1/a`), and even a correct
> monotone variant buys almost nothing (see "shapes that were scored" below).
>
> **The real cause: `fit_nonlinear.py`'s core premise is false.** Its docstring says
> "harmonic RATIOS are level-independent, so it is valid before makeup (step 5)".
> **They are not level-independent in this chain**, because at BLEND = max-OD the
> output still contains a large HARMONIC-FREE clean component, so every measured
> harmonic ratio is diluted by the OD-vs-clean LEVEL — which is exactly what the fit
> params move. The fitter could therefore buy harmonic score with level, and did.

### The mechanism, measured end to end
`LevelBlend::process()` at `B >= 1.0` returns `vw`, and `vw` **contains `cleanIn`**:
```
vw = (odIn * invRup + cleanIn) / invTotal        // LevelBlend.h, the KCL solution
```
That is NOT a bug — it is the drawn topology. BLEND's 100k track runs pin1(clean) ↔
pin3(LEVEL wiper), so with the wiper at pin3 the clean source still feeds the node
through the full 100k against the LEVEL wiper's Thevenin ~23.3k. At LEVEL = noon:
```
   Vout(BLEND max-OD) = 0.3009*od + 0.1892*clean      (clean only 4.0 dB below od)
```
The clean tap carries no harmonics, so it inflates H1 and suppresses every measured
harmonic by however far the OD path sits below the clean tap:

| `jfetGm` | OD vs clean tap | H1 inflated | H2: OD-region out → final |
|---|---|---|---|
| 0.0274 mS (the step2_ceiling fit) | −24.1 dB | **+20.9 dB** | −12.0 → **−30.4** |
| 0.090 mS (shape fit) | −14.6 dB | +12.9 dB | −13.0 → −22.4 |
| 0.690 mS (nominal) | −3.8 dB | +5.9 dB | −22.4 → −24.7 |

So the fitter drove `jfetGm` 25× below nominal (quiet OD → big dilution → all
harmonics suppressed), then cranked `a` to claw H2 back, hit the monotonicity
constraint, and the bump's own saturation manufactured the H4. **Every symptom the
section below reports is downstream of that one confound.**

### The blocker does not exist at a sane operating point
Rendered drive-min, `s = 0.3`, ceilings + clipper at NOMINAL (targets −36.0 / −59.2 / −69.9):

| gm (mS) | a | a·A | H2 | H3 | H4 | feasible |
|---|---|---|---|---|---|---|
| 0.690 | 4 | 0.17 | **−35.5** | −75.3 | **−78.5** | yes |
| 0.090 | 4 | 0.42 | **−36.6** | −68.0 | −65.6 | yes |
| 0.090 | 8 | 0.85 | −30.7 | −68.0 | −58.6 | yes |

H2 lands within 0.5 dB of the capture with a MODEST `a`, well inside both
`a·A < 1` and `|a|·s < 2.598`, and H4 comes out 4–9 dB BELOW target (the safe
direction — the clipper supplies the balance). The shipped
`(a*s²/2)*tanh²(w/s)` shape is fine.

### How this was localised (re-usable technique)
`PedalChain::runInputBuffer()` / `runOdSample()` / `processPostBlend()` are public, so
a console probe can split the chain and measure H2/H1 at each boundary. That is what
separated "8 dB lost in the OD region" from "18.4 dB lost after BLEND" and pointed
straight at the mixer. Cross-checks that made it airtight:
* JfetStage in isolation at the CHAIN's conditions (384 kHz, ADAA on) gives exactly
  `H2 = a*A/4` — the stage is correct.
* A two-tone (220+440) through the whole chain gives 440/220 = **+1.71 dB**, i.e. the
  linear path does NOT attenuate the harmonic — so the loss had to be dilution of H1.
* The `s`-sweep's KNEE position independently measures the shaper's drive amplitude
  (it depends only on A/s) and confirms vgs = 126 mV, matching the analytic front end.

### ⚠ Consequences — what must change before ANY step-2 re-fit
1. **The step-2 objective is confounded with step 4, worse than previously recorded.**
   The bleed coefficients depend on `L = powerLawTaper(level, 1, levelTaperExp)`, so
   `levelTaperExp` (a step-4 param) scales the dilution. The earlier note that only the
   OD-vs-clean LEVEL was confounded understated it: the **harmonic ratios** are
   confounded too.
2. Either fit gm from level/shape and HOLD it (the shape fit's 0.090 mS is corroborated
   by an independent absolute-level check), or add an OD-vs-clean level term so the
   objective can no longer buy harmonics with level. Do not let a harmonic-only
   objective choose gm.
3. **⚠ THE SHAPE FIT'S gm = 0.090 mS IS CONTAMINATED TOO — do NOT adopt it as the
   anchor.** (This corrects an earlier version of this very section, which said the
   disagreement was "resolved in favour of the shape fit".) At gm = 0.090 mS the
   drive-min render's output is `0.3009*0.0321 = 0.0097` of OD against
   `0.1892*0.1733 = 0.0328` of clean — the "OD-path shape" that `fit_jfet_boundary.py`
   matched is **~77 % CLEAN PATH by amplitude**. Its apparent gm sensitivity
   (0.05 → 2.16, 0.09 → 1.56, 0.20 → 3.73, 0.30 → 5.01 dB) comes from the OD/clean
   MIX RATIO moving, not from the OD path's own shape. Its absolute-level cross-check
   is contaminated by the same term (the total output floors on the clean bleed as gm
   falls, so level under-responds to gm and the fit must go LOWER to compensate).
   **Every gm estimate on the table — 0.551, 0.090, 0.0274 mS — is really a
   measurement of the OD/clean MIX RATIO, and therefore inherits any error in the
   BLEND model.** That is what makes settling the mixer a prerequisite rather than a
   side quest, and it is the whole reason for the plan below.

### ⚠ STILL TO VERIFY — is 4 dB of clean bleed at "100% OD" real?
The model is arithmetically consistent with circuit.md's stated pin mapping, but 4 dB
of clean at full distortion is a lot for a pedal sold on its blend, and the pot
pin1/pin3/wiper mapping is exactly the class of thing circuit.md's own gotcha list says
to re-verify. **There are `blend-*` captures — measure the real crossfade law against
this model before trusting the absolute dilution.** If the real pot suppresses clean
much harder at full CW, the topology is wrong and that is a second, independent bug.
(The finding above does not depend on the exact 4 dB: any substantial bleed produces
the same confound.)

---

## ✅ STEP 1 DONE — THE MIXER IS SETTLED (session 8, 2026-07-23)

**Verdict: the BLEND/LEVEL model is STRUCTURALLY CORRECT. The clean bleed is REAL, and the
shipped model UNDERSTATES it — confirmed by TWO independent routes that now agree to within
1.4–3.9 dB of each other. The step-2 confound is confirmed, not explained away.**

Along the way, two bad captures were found and fixed (both `level-1430_base-od.wav`, in two
separate rounds — see 1f) — worth reading as a caution about trusting a single anomalous data
point without a mechanism, and as a demonstration of how to tell a real finding from a capture
bug: the fix produced a measurable, predicted convergence (36/36 taper estimates agreeing where
12/36 disagreed before), not just "the number changed."

Tool: `analysis/mixer_law.py` (new). Log: `analysis/fit_logs/mixer_law_session8.log`.
No code changes; nothing committed to the DSP yet.

### 1a. Topology — VERIFIED AT PIXEL ZOOM, no longer an open question
Primary p.4 re-rasterised at **600 dpi** (`pdftoppm -r 600`, 7016×4961) and cropped hard.
Everything circuit.md claims is confirmed, and the two long rails were additionally scanned
**pixel-by-pixel along their whole length** (not eyeballed):

```
VR2 LEVEL : pin3 = IC4_A pin1 (OD in) | pin1 = VD, direct | wiper -> VR1 pin3
VR1 BLEND : pin3 = LEVEL wiper        | pin1 = clean rail straight off IC1_A pin1
            wiper -> IC5_A(+)  (unity buffer, high-Z => wiper is UNLOADED)
clean rail : x-frac 0.2255..0.8682 — bare wire, NO series R, NO junction dot, NO shunt
wiper rail : x-frac 0.1663..0.8848 — same
```

IC1_A pin1 carries a junction dot splitting to C2/R4 (drive path) and to the clean rail; IC1_A
pin2 ties to pin1 (unity buffer) as documented. **So `LevelBlend.h` is a faithful implementation
and the bleed is a property of the drawn circuit, not a modelling error.** The subagent route
could not do this (no Bash in that context) — the crops were run directly.

### 1b. ⚠ A PREMISE OF THE PLAN WAS WRONG — the two routes are NOT independent
The plan below says the LEVEL sweep is an independent second route "since LEVEL moves OD only".
**False.** With the wiper unloaded the closed form at BLEND full-CW is

```
alpha(L) = L / (1 + L(1-L))        beta(L) = L(1-L) / (1 + L(1-L))
beta/alpha = (1 - L)      <- clean-to-OD COEFFICIENT ratio, independent of the pot value
```

so LEVEL moves the clean bleed too, by exactly `(1-L)`. This makes the LEVEL sweep a *sharper*
test rather than a useless one: the law has no free parameter left except the taper `L(knob)`.

### 1c. The law itself — CONFIRMED
BLEND is a linear-taper pot, so the model makes every harmonic **affine in the knob with zero
free shape parameters**. Complex affine fit `Hn(B) = F_n + B*G_n` over all 5 BLEND points:

| | H1 | H2 | H3 | H4 |
|---|---|---|---|---|
| residual / \|G\| @220 Hz | **0.016** | **0.040** | 0.112 | 0.169 |

H1 and H2 confirm the law. H3/H4 degrade because they sit 20–40 dB lower and the constant-floor
term stops being a good model there — not evidence against the law.

### 1d. THE LEVEL TAPER — p ≈ 2.25, not the shipped 1.43 (a step-4 result, free)
**The round-2 recapture (1f) confirmed the hypothesis: the knob=0.75 anomaly was the
BLEND-at-noon capture bug, not a real taper irregularity.** With `level-1430_base-od.wav`
re-taken with BLEND confirmed at max-OD, its implied `p` moved from the earlier 4.4–6.2 cluster
into the SAME range as 0.25/0.50 — e.g. at 220 Hz, H2 gives p = 2.03 / 2.10 / **2.35** at knob
0.25/0.50/0.75 (was 2.35 before the fix too, at that harmonic — the outlier was concentrated in
lower-SNR harmonics that the earlier bad capture pushed further off). Over the full **36
quasi-independent estimates** (3 tones × 4 harmonics × 3 knob positions, `L = knob^p` inverted
bleed-free from `|Hn(L)|/|Hn(max)| = alpha(L)`):

```
p = 2.222 mean / 2.253 median / sd 0.359 / range 1.45-3.12   (all 3 knob positions agree)
=> L(noon) = 0.5^2.25 = 0.2098      vs the shipped 0.5^1.43 = 0.3711
```

No knob-position cluster stands apart from the others anymore — the single-exponent power-law
model is a good fit across the whole measured range. **`LevelBlend::kLevelTaperExp` should
become ≈2.2–2.3**, but do NOT commit it here: it is a step-4 parameter and the same captures
should fit it jointly with the other tapers.

### 1e. THE HEADLINE — the bleed is real and BIGGER than modelled, and the two routes now AGREE
Two estimators. The better-conditioned one uses the 5-point BLEND fit (all points far above the
noise floor, never touches any `level-*.wav` file): `F1 = CLEAN_1`,
`G1 = alpha_n*OD_1 + (beta_n-1)*CLEAN_1`, so `alpha_n*OD_1 = G1 + (1-beta_n)*F1` and
`bleed = |beta_n*F1| / |alpha_n*OD_1|`, summed as phasors, entirely within one sweep. The other
uses the (now-fixed) 4-point LEVEL sweep's `H1/H2` regressed on `(1-L)`.

```
clean-vs-OD amplitude ratio in the output at BLEND max-OD / LEVEL noon / DRIVE noon
   tone    LEVEL route    BLEND route
   110       +1.47 dB       -2.32 dB
   220       -2.45 dB       -1.03 dB
   440       +1.03 dB       +2.73 dB     (least reliable, see 1f)
```

**The two independent routes now agree to within 1.4–3.9 dB at every tone** (before the round-2
fix they disagreed by 5–13 dB) — that agreement is the cross-check the whole plan was built to
provide, and it passed. Fit quality improved too: the LEVEL route's affine-fit residual dropped
from 74–251 % of |A| (contaminated) to **18.6–53.6 %** (fixed). BLEND route remains the number
to carry forward — it never depends on the LEVEL taper at all.

**At "100 % OD" the clean tap is within a couple of dB of the OD path — i.e. roughly HALF the
output is undistorted clean signal.** Sensitivity to `L(noon)` (the log tabulates the full
curve): at the now-measured `L(noon) = 0.2098` the 220 Hz BLEND-route bleed is ≈−1.2 dB; at the
shipped `L = 0.3711` it would be +3.06 dB — i.e. **the corrected taper makes the bleed WORSE
(more negative L(noon) sensitivity aside, smaller L means larger `1-L`), not better.**

**▶ Consequence for the plan.** The handover recorded a prediction to score: *"if the real bleed
is much SMALLER than 4 dB, gm was pushed ~7× low to cancel a spurious clean floor; if the bleed
MATCHES, 0.090 mS survives."* **The bleed matches or exceeds the model, so the second branch
is the one that fired — and this is now confirmed by two agreeing, independent routes, not one.**
The confound that invalidated three step-2 fits is confirmed real, and `jfetGm ≈ 0.090 mS` is
NOT obviously an artefact of an over-modelled bleed. Step 2 (re-anchor gm) should proceed, and
step 3's harmonic-to-harmonic objective is *required*, not optional.
⚠ Scope: the `(1-L)` coefficient law and the taper are drive-independent (pure resistive
arithmetic); `CLEAN_1/OD_1` is an operating-point number measured at **DRIVE = noon**. The J201
re-anchor needs `OD_1` at **drive-min** — use the law from here plus the drive-min captures.

### 1f. `level-1430_base-od.wav` — TWO ROUNDS, BOTH FIXED, both confirmed by the data itself
**Round 1 (odd-harmonic contamination).** Originally excluded: its tone_220 spectrum was
**odd-dominant** (H3 −45.4, H5 −52.4 vs H2 −59.9, H4 −83.8) while every other capture in the
session is even-dominant — a passive divider cannot create odd harmonics, and its `gain-n12`
twin at the same knob was essentially harmonic-free (61 dB less H3 for a 9 dB level drop). Not
clipped, not misaligned — a take-specific artefact (scratchy pot / bad connection).

**Round 2 (BLEND left at noon instead of max-OD).** The round-1 recapture fixed the odd-harmonic
defect but introduced a new anomaly: its implied LEVEL taper (p ≈ 4.4–6.2) disagreed sharply
with the 0.25/0.50 cluster (p ≈ 2.0–2.5) — internally self-consistent across all its own
harmonics/tones, which is exactly the signature a wrong-BLEND-position capture would produce
(the whole file's alpha/beta mix shifts together). User caught and fixed this mid-write-up.

**Both rounds are now resolved and cross-validated by the data, not just by the explanation
being plausible:** with the round-2 take (BLEND confirmed at max), the taper estimate at
knob=0.75 rejoined the 0.25/0.50 cluster (1d) — 36/36 tone×harmonic×knob estimates now agree
under one exponent, where 12/36 disagreed sharply before. That is strong evidence the diagnosis
was right, not merely that the anomaly went away. `level-0700_base-od.wav` stays excluded on
principle regardless: `L = 0` is a deep null by construction, so ratios measured in it are
meaningless.

The BLEND-route bleed numbers (1e) were unaffected by either round — the BLEND sweep never uses
any `level-*.wav` file. Also note 440 Hz is the least trustworthy tone throughout: its H2 lands
at 880 Hz, near the IC2_B bridged-T notch, 12 dB below H3 (its H2-only implied p, 1.454 at knob
0.25, remains the single mild outlier in the 36-estimate pool) — prefer 110/220 Hz, or pool
across harmonics at 440 rather than trusting H2 alone.

### 1g. Two measurement traps worth not re-tripping
- **Do NOT estimate a noise floor by projecting at half-harmonic frequencies.** Against a
  near-pure tone that measures the analysis WINDOW's sidelobe rejection (~−170 dB), not the
  capture's noise, and every SNR derived from it is fiction. The first version of this script
  did exactly that and reported 100+ dB SNRs on buried harmonics. Use the median magnitude over
  spectrum bins that are not near any harmonic.
- **Draw conclusions from ratios WITHIN one capture** wherever possible. Cross-file phase
  reference costs ~1.65°/sample at 220 Hz and the alignment lags across this capture set span
  0–26 samples; the within-file `H1/Hn` and the within-sweep affine fits are immune to it.

---

## ✅ STEP 2 DONE — `jfetGm` RE-ANCHORED against the corrected mixer (session 9, 2026-07-23)

**Verdict: `gm ≈ 0.10 mS` survives.** The bleed-aware re-anchor corroborates the old 0.090 mS
via an independent, bleed-FREE route (the old shape fit was bleed-contaminated), nudges it
slightly toward the physical J201 low corner (0.20 mS), and scores step-1's recorded prediction
("bleed matches → 0.090 survives") as CONFIRMED. **No capture needs redoing** — the one real
problem surfaced (an OD-path LF frequency-response discrepancy) is consistent across every
capture and both tapers, i.e. a MODEL-structure issue, not a bad take.

Tool: **`analysis/reanchor_gm.py`** (new). Log: **`analysis/fit_logs/step2_reanchor_gm.log`**.
Nothing committed to the DSP; `gm` is held in the analysis scripts only.

### The measurement (bleed-aware, scale-free — this is the method to re-use)
The clean tap (IC1_A) is gm-INDEPENDENT and everything after BLEND is linear, so for one tone
at the OUTPUT: `|H1(drive OD cap)| / |H1(B=0 clean cap)| = |alpha(noon)*OD_1(gm)/CLEAN_1 + beta(noon)|`.
The right side is a pure RATIO — makeup, masterTaperExp, kInputRef and interface gain all cancel
because each side is normalised to ITS OWN B=0 clean reference. No cross-file complex subtraction:
the phase of `alpha*OD + beta*CLEAN` is computed by the DSP itself when we RENDER the chain at a
trial gm with the corrected taper (levelTaperExp=2.25, ro/rq2 nominal), and the B=0 clean render is
gm-independent (once). Speed: the model side renders a compact 6-tone input (82–2000 Hz, −14 dBFS),
NOT the full 84 s signal — a full OS-8 render is ~2 min, a tone render is <1 s. **⚠ Do not render the
full signal in a fit loop; trim or use a synthetic tone, as fit_nonlinear/fit_jfet_boundary do.**

### The data
Capture OD/clean fundamental ratio (dB) — the anchor target:
```
          82Hz   110Hz  220Hz  440Hz  1000Hz 2000Hz
  dmin   -17.4  -15.9  -13.9  -15.8  -15.9  -10.6
  dnoon  -15.3  -12.0   -9.7  -13.6  -15.2   -9.8
```
**The OD path sits 11–17 dB BELOW the clean bleed at drive-min** — so drive-min captures are
mostly clean bleed and the OD path is barely visible. That is the step-2 confound made concrete,
and it is why gm is only anchored to ~2×, not tighter.

Per-tone gm where the model OD/clean ratio matches the capture (corrected taper 2.25):
```
  dmin   82:none  110:none  220:0.53  440:0.17  1000:0.096  2000:0.067  mS
  dnoon  82:none  110:0.046 220:0.57  440:0.24  1000:0.060  2000:0.036  mS
```

### Why the tones disagree, and why gm is still ~0.1 mS
The per-tone gm spans 0.05–0.57 mS → the OD-path FREQUENCY SHAPE is wrong in the model. The
error at fixed gm (relative to its mean) is +4 dB at 82, +2 at 110, −4 at 220, −1.5 at 440,
~0 at 1000, +0.3 at 2000 — i.e. a **LOW-FREQUENCY EXCESS** (model OD rolls off ~3–5 dB LESS than
the real pedal at 82–110 Hz), plus a smaller mid dip. This is NOT the parked ~322 Hz notch alone
(that is only ~3 dB deep in the ASSEMBLED chain, not −28); the dominant feature is an LF
roll-off discrepancy, most likely the **GRUNT/clipper-coupling HPF corners, which depend on the
unfit `clipA0`** (circuit.md: 36–158 Hz at A0=25) — a step-3 parameter. So the low-freq anchor
tones (82–220 Hz) are corrupted and the high-freq tones (440–1000 Hz), above the LF issue and
both notches, are the trustworthy ones: **gm ≈ 0.06–0.24 mS, centre ~0.10–0.12 mS.**

`gm = 0.526 mS` at 220 Hz is a red herring: the model's spurious mid attenuation there pulls the
OD too quiet, so the fitter demands inflated gm to compensate. Correct the LF/notch shape and
that estimate drops toward the high-freq ~0.1 mS.

### Decision + what step 3 inherits
- **Hold `gm = 0.10 mS`** for step 3 (plausible band 0.09–0.15). Re-check step 3 for gm
  sensitivity within that band — harmonic-TO-harmonic ratios should be nearly gm-insensitive.
- The LF anchor tones will clean up once `clipA0`/coupling is fit in step 3, so gm and clipA0
  can be re-checked jointly afterward — the LF discrepancy is a step-3 lead, not a new blocker.
- `levelTaperExp ≈ 2.25` (step 1) is IRRELEVANT to the step-3 harmonic-to-harmonic objective
  (alpha cancels), but hold it anyway for a faithful render; commit it in step 4.

---

## ▶▶ THE PATH FORWARD FOR THE J201 (agreed with the user 2026-07-23) — START HERE

**Framing.** Three step-2 fits have now been rejected, and every one failed the same
way: an upstream error was absorbed by a downstream parameter, and no capture could
contradict the result. So the ordering principle is **do the measurement that cannot
be absorbed first.** Right now that is the mixer, and nothing else.

### Step 1 — SETTLE THE MIXER (prerequisite; needs NO new captures)

The lever that makes this tractable: **the clean tap is linear and harmonic-free, and
everything after BLEND (C21, EQ, MASTER) is linear too.** Therefore, at the output:

```
  fundamental  =  alpha(b) * OD_1  +  beta(b) * CLEAN_1     <- CONTAMINATED
  H2, H3, H4   =  alpha(b) * OD_n                            <- BLEED-FREE, OD only
```

So harmonic AMPLITUDES measure `alpha(b)` directly with zero clean contamination, and
the fundamental then yields `beta(b)`. Two independent equations, from captures that
already exist:

* `blend-0700 / -0930 / -1200 / -1430` + `ref-od` = **5 BLEND points**.
  - absolute H2 vs blend → `alpha(b)`
  - fundamental vs blend → `beta(b)`
  - `beta/alpha` at full-CW OD → the REAL clean-bleed figure, to test against the
    model's `0.3009*od + 0.1892*clean` (clean only 4.0 dB below OD).
* `level-0700 / -0930 / -1430 / -1700` + `ref-od` = **5 LEVEL points**, an INDEPENDENT
  second route (LEVEL moves the OD path only). The two routes must agree — that is a
  built-in cross-check, not a single unfalsifiable fit.

**In parallel, re-verify BLEND's pin1/pin3/wiper mapping on the schematic** (the
`schematic-checker` agent). `LevelBlend`'s arithmetic is self-consistent with the
topology circuit.md states, so if the captures disagree with the model, the error is in
the TOPOLOGY, and that is a pixel-zoom question. circuit.md's own gotcha list flags pot
lug mapping as exactly this class of error.

### Step 2 — RE-ANCHOR `jfetGm` from the corrected mix ✅ DONE (session 9)

See "✅ STEP 2 DONE — `jfetGm` RE-ANCHORED" above for the full result. Summary: the
bleed-aware OD-vs-clean fundamental ratio (rendered through the corrected mixer) gives
**gm ≈ 0.10 mS** from the trustworthy high-freq tones (440–1000 Hz), corroborating 0.090
via a bleed-FREE route. **The prediction fired as "bleed matches → 0.090 survives".** A
new lead surfaced: an OD-path LF response excess at 82–110 Hz, most likely `clipA0`/GRUNT
coupling — feeds into step 3. Hold `gm = 0.10 mS` for step 3.

### Step 3 — FIX THE OBJECTIVE, then fit the shaper ◀ NEXT (not started)

**The concrete fix: use harmonic-TO-HARMONIC ratios (H3/H2, H4/H2, H5/H2) instead of
ratios re the fundamental.** `alpha` cancels EXACTLY in those, so they are immune to
the clean bleed AND to makeup, `levelTaperExp` and `masterTaperExp` — genuinely
level-independent in the way the current objective only claimed to be. Keep an absolute
term separately if wanted, but do not let the shape params depend on it. Then hold `gm`
from step 2 and fit `s`, `a`, `jfetCeilPos/Neg`, `clipA0`, `clipSatLo/Hi`.

Sanity anchor for that re-fit: at `s = 0.3` with nominal ceilings/clipper, `a ~= 4`
puts drive-min H2 within ~0.5 dB of the capture at EITHER gm candidate — so the fitted
`a` should land near single digits, not the 5.5–20 the rejected runs produced.

### Step 4 — ACCEPT only on corroboration the objective could not see

The recurring failure mode has been a fit that scores well and cannot be contradicted.
Require at least: the square-law identity `2*a*jfetCeilNeg = 1` (deliberately NOT
constrained in the fit, so it stays a real check), absolute OD-vs-clean level, and
`clipA0` landing inside circuit.md's 20–30. No parameter resting on a bound.

---

### Shapes that were scored, so nobody re-does it
Requirement was intrinsic H2 with H4 ≥ 33.9 dB below it, at vgs peak 0.126 V:
`ln(cosh(a·w))/a` (monotone for ALL a, no constraint) tops out ~2 dB better than the
shipped shape; a hard-cutoff square law scores well on H2/H4 only by becoming a
half-wave rectifier (H3 −14 dB, fatal). **General bound worth keeping:** for any
monotone map whose even part is a clean quadratic, `H2/H1 = a·A/4` and monotonicity
needs `a·A ≤ 1`, so **H2/H1 ≤ 1/4 = −12.04 dB, scale-invariantly.** That wall is real
— it is just nowhere near binding once the bleed is accounted for.

---

## ▶▶ ~~THE NEXT STRUCTURAL GAP: the even-harmonic LADDER (H2 vs H4)~~ — SUPERSEDED

> ⚠ **SUPERSEDED 2026-07-23 — see the section immediately above.** The numbers here
> reproduce, but the diagnosis is wrong and the recommended reshape must NOT be built.
> Kept for the measurement record only.

This is the important finding of session 6 and it supersedes "the clipper is the next
suspect" as the lead. **The binding problem is not level anywhere — it is the SHAPE of
the J201's even-harmonic series.**

### Why drive-min H2 is a near-direct measurement of the J201
DRIVE (IC2_A) sits **after** the JFET/treble net, so **the J201 sees the same signal at
every drive setting** — its harmonic contribution is CONSTANT across the sweep. At
drive-min the capture's H3 is −59.2 (clipper barely working) while H2 is −36.0. So
drive-min H2 is essentially all J201, nearly uncontaminated. That also explains the
capture's whole profile: H2 moves only 6 dB across the sweep (a constant J201 floor)
while H3 moves 30 dB (the clipper switching on). **The architecture is right.**

### The J201 CAN reach the capture's H2 — but only by wrecking H4
Grid over the feasible (s, a, ceilNeg) region, rendering drive-min only:

```
best reachable drive-min H2 = -37.5 dB  at s=0.1, a=20, ceilNeg=0.2   (capture -36.0)
   and H3 there = -59.5                                               (capture -59.2)
```

Both harmonics land almost exactly — but `a = 20` is **outside `jfetSatNeg`'s (0, 10)
box**, and the full 5-point cost at that point is **1279.5 vs the fitted 428.6**. The
per-term breakdown shows the entire regression is H4:

| drive | H4 capture | H4 @ fitted | H4 @ a=20 | err² @ a=20 |
|---|---|---|---|---|
| min | −69.9 | −63.6 | **−46.3** | 278.5 |
| 9:30 | −71.6 | −57.8 | **−40.6** | 479.1 |
| noon | −51.1 | −49.6 | **−33.0** | 162.9 |

Those three terms alone are **920 of the 1279.5**. Every other term is equal or better —
drive-min becomes near-perfect on H2/H3/THD (−37.4/−58.9/−36.7 vs −36.0/−59.2/−36.0)
and drive-max lands within 1.8 dB on all three.

### The measured ladder, and why it is a WALL not a bad fit

| | H2 | H4 | **H2−H4** |
|---|---|---|---|
| capture (drive-min) | −36.0 | −69.9 | **33.9 dB** |
| model, fitted a=5.5 | −43.3 | −63.6 | 20.3 dB |
| model, a=20 | −37.4 | −46.3 | **8.9 dB** |

A **true quadratic makes H2 and NOTHING else** (`x = A cos → x² = A²/2·(1+cos 2ωt)`, H4
identically zero) — which is what a real JFET's `Id ∝ (Vgs−Vt)²` does. The shipped bump
`(a·s²/2)·tanh²(w/s)` is quadratic only for `|w| ≪ s`; **its own saturation is what
manufactures H4.** So suppressing H4 needs a LARGE knee `s`, while making H2 needs a
LARGE `a` — and monotonicity caps the product `|a|·s`:

```
   a     s at |a|s=2.598    A/s at A=0.05 V
  2.0            1.299             0.04      bump stays quadratic, but too little H2
 20.0            0.130             0.38      enough H2, knee now INSIDE the signal -> H4
 40.0            0.065             0.77      H4 worse still
```

**The two requirements are in direct conflict through the monotonicity constraint.** No
parameter choice inside the current shape can give the capture's 33.9 dB H2/H4
separation. This is the same class of finding as the original tanh→square-law reshape
(there: "an odd map cannot make H2 without H3"; here: "a self-saturating even bump
cannot make H2 without H4"), and it should be treated the same way — as a **shape**
problem, not a fit problem.

### ▶ Recommended next move (NOT yet done — needs sign-off, it is a DSP change)
Make the even term a **true quadratic over the operating range** and let the *ceiling*
provide the bound, instead of using a bump that saturates on its own:
`g(w) = T(w) + (a/2)·w²`, with `T` the ceiling-limited core. H4 is then zero by
construction and the ceiling — which is already fitted, already tested, and already has
an antiderivative — does all the limiting. Before building it, confirm on the static map
that the composite still passes the numeric monotonicity scan and that ADAA keeps its
zero-H3 property (both are existing `JfetStageTest` Test 6 checks).

**Do NOT re-run the step-2 fit before this is resolved** — every run so far has been the
optimiser trading a structural shape error against level, which is what produced three
successive uncommittable fits.

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

> ⚠ **SUPERSEDED 2026-07-22 (ceiling commit) — this whole subsection describes a shape
> that is no longer in the file, and its monotonicity numbers are now backwards.** The
> even bump is now `(a*s^2/2)*tanh^2(w/s)` and `F` is elementary (no Gudermannian); the
> `2.598` above was WRONG for the sech shape (the right bound was 2.0, see the
> dsp-validator section) and is RIGHT for the tanh² shape now in the file. **Do not
> follow the "constant corrected to 2.0 / do not write 2.598" instruction below** — it
> was correct for the sech bump only. And with a finite ceiling NEITHER closed form is
> sufficient: the constraint couples `s`, `a` and `ceilNeg` (as tight as `|a|*s < 1`
> when `ceilNeg = s`), so the gate is a numeric slope scan in both
> `fit_nonlinear.py::monotonic` and `JfetStageTest`. Derive the bound from the shape in
> the file; never carry either numeral across a reshape.

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

> ⚠ **The "2.0 / do not write 2.598" instruction is VOID as of the ceiling commit
> (later the same day).** It was correct for the `1-sech` bump, which is no longer the
> shape in the file. For the `tanh^2` bump now shipping, `max|tanh*sech^2| = 2/(3*sqrt(3))`
> → the ceiling-OFF bound genuinely is **2.598**, re-derived and re-verified numerically
> (|a|*s = 2.5 → min slope +0.038, 2.7 → −0.039). The transferable lesson is the one this
> bug taught in the first place: **derive the bound from the extremum of the shape
> actually in the file, and never carry a numeral across a reshape** — the same numeral
> has now been both wrong and right, for two different shapes, within one day. With a
> finite ceiling no closed form is sufficient anyway; both gates scan numerically.

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
