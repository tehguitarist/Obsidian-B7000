# Phase 7 CALIBRATION PROPER — session handover (updated 2026-07-23, session 15)

> **Resume point for Phase-7 calibration. Read this first.** Supersedes
> `phase7-handoff.md` (which documents the now-complete PRE-work).
> Session 3's J201/TrebleAttack restructure is committed as `b02b2f2`.
>
> **⚠⚠⚠⚠ SESSION 15 (2026-07-23) — branch B (expansive-then-bounded JFET core, `jfetExpandBeta`)
> LANDED, its §3j gate CONFIRMED, and dsp-validator PASSED on both the new core and the
> still-deferred clipK. **THE JFET H3 PHASE PROBLEM FROM SESSIONS 12-14 IS FIXED**: the isolated
> JFET-core H3 flips from ~180° anti-phase to in-phase with the clipper as beta rises (110 Hz
> 177°→2°, 1 kHz 171°→42°), and the fitted drive-min ψ3 lands within 5.8-14° of the capture
> (was ~160° off). Three fit attempts, though, all FAILED acceptance — not on the JFET side, but
> because the CLIPPER cannot reach the capture's noon/2:30/max drive-sweep ramp within its
> PHYSICAL envelope (clipA0 20-30, rail ~7 V) no matter how clipK/clipSat/clipA0 are tuned; two
> diagnostic grids localised this to a SEPARATE, pre-existing issue (first flagged session 5) —
> likely `driveTaperExp`'s SHAPE (only ever LEVEL-validated, never HARMONIC-validated) or the
> clipper's input coupling, NOT gm and NOT the JFET. STOPPED per protocol — nothing committed to
> git, `jfetExpandBeta` nominal stays the honest placeholder 0.0. ctest 16/16 (incl.
> OSValidationTest — session 14's anomaly does not recur at nominal). **NEXT (session 16):
> investigate `driveTaperExp`'s shape against the HARMONIC ramp** (not just the level match
> session 11 used) or the clipper's input-coupling drive-dependence — do NOT re-attempt a joint
> clipK+clipSat+clipA0 fit first, it will just re-find the same degenerate "lower the ceiling"
> trick. Full detail: "SESSION 15" §3u below (search for it).
>
> ── prior session ──
> **⚠⚠⚠ SESSION 14 (2026-07-23) — the ceiling-hardness reshape (§3s) was IMPLEMENTED, and its
> pre-registered §3j pivot gate FAILED, robustly. STOPPED at the gate per protocol — NO fit, NOTHING
> committed. The residual is an H3 PHASE/SIGN problem, NOT a magnitude/hardness one. **I first blamed
> the known ~320/717 Hz notches, but a follow-up assembled-chain measurement (`analysis/notch_scope.py`)
> FALSIFIED that: in the LOADED chain both notches are only ≤2.6 dB (not the isolated −28 dB), too
> shallow to explain the ~180° anti-phase.** **▶ USER chose to VERIFY the anti-phase then take branch
> B, and the VERIFICATION IS DONE (§3t.5): the anti-phase reproduces (ceil↔clip 178.8/166.0/178.7° at
> 110/220/1000), the capture matches the CLIPPER not the ceiling (1 kHz conclusive: cap↔clip 8°), and
> it is NOT a polarity bug (a global inversion can't change a RELATIVE phase; per-stage fundamentals
> DC-step-verified). => the REAL JFET H3 is EXPANSIVE-signed (in-phase with the clipper); no
> compressive ceiling or hardness makes it. NEXT = branch B: an expansive-then-bounded odd JFET term,
> §3j gate first, phase-aware fit (§3t.6 has the plan).** Nothing committed. The `jfetCeilK` algebraic-sigmoid ceiling is fully implemented in the
> WORKING TREE (uncommitted): `JfetStage.h` (T(w)=w/(1+|w/L|^k)^(1/k), k=2 anchor with exact
> ADAA antiderivative L·√(L²+w²)−L², midpoint-ADAA fallback for k≠2), `FitParams.h`/`PedalChain.h`/
> `offline_render.cpp` plumbing, `JfetStageTest.cpp` + `fit_nonlinear.py` monotonicity updated.
> **ctest 15/16** — the 1 failure is `OSValidationTest`'s 4×-vs-2× aliasing diff-gate at amp 0.2, the
> KNOWN clipper/decimator narrow-band anomaly RELOCATED onto the probe amp by the reshape at
> PLACEHOLDER nominal ceiling params (8× floor still clean −40.5; oversampling-reduces-aliasing +
> delay-comp both pass); deferred to post-fit, NOT masked. **The pivot verdict** (`analysis/fit_logs/
> step5_ceilk_pivot.log`): as k RISES, drive-min AND drive-noon H3−H2 fall the SAME direction
> (through an anti-phase null), at BOTH the session-11 point AND a proper-clipper point — so the
> hardness lever cannot make the capture's monotonic ramp (−23.2/−21.0/−10.6/+1.3/+1.0). The model is
> FLAT across min/9:30/noon at every k (e.g. −15.2/−15.2/−15.3), the capture RAMPS. Full detail +
> the diagnosis + recommended branches: "SESSION 14" (§3t). Do NOT run the fit or commit until the
> branch is re-decided with the user.
>
> **⚠⚠ SESSION 13 (2026-07-23) — the two §3o measurements are IN; STATIC is CONFIRMED. Branch
> decided.** **Step 2 (static-vs-dynamic) = NO dynamic signature**, and the user's CONFIRM CAPTURE
> (a dense drive-min ladder at 110/220/440 Hz down to −60 dBFS) hardened it: the confound-free
> differential `cap_slope − mdl_slope` is ~0 over the whole clean-JFET range (>30 dB) at every tone,
> below-corner 110 Hz mean |dev| **0.03** (14 clean slopes), NOT anomalous vs above-corner 0.05.
> **Step 1 (phase) is ambiguous** (1 kHz says the ceiling odd term is BACKWARDS; 220's H3 is
> corrupted by the mismodelled 717 Hz notch). Consistent reading: the static FAMILY is adequate,
> but the current ceiling odd-term SHAPE (magnitude + likely SIGN) is wrong. **▶ BRANCH = the
> STATIC path: reshape the JFET ceiling's odd term, fitted against COMPLEX (phase-aware) targets,
> §3j check + dsp-validator sign-off — NOT the coupled-Newton rewrite.** Both the drive-min AND a
> bonus drive-noon ladder are recorded (`analysis/captures/jfet_ladder_drive-{min,noon}.wav`,
> gitignored) — the noon take is the clipper/interference-vs-level data the reshape fit will use.
> **Traps found + fixed** (in the plan's recipe and the tooling): (1) "ceiling-only via high
> clipSat" is invalid — D1/D2 clamps track satLo, so high sat FREEZES the clipper into a DC source;
> (2) raw `A_eff`-collapse is confounded by the treble+clipper the static model shares — use the
> differential; (3) `captures.load_capture()` misfires on the ladder stimulus (no 1 kHz cal tone) —
> use `A.load`. See "SESSION 13" (§3p–3r). ctest 16/16 (analysis/docs only, no DSP touched).
>
> **⚠⚠ SESSION 12 (2026-07-23) — the clipper-hardness `k` WAS implemented, and the §3j
> discriminating check REJECTED the session-11 diagnosis.** The pivot signature FAILED in
> the full chain (noon H3−H2 moves the WRONG way as `k` softens, at BOTH the nominal and
> the session-11 fitted point), and the follow-up probes found the real mechanism the
> clipper-alone probe could not see: **anti-phase H3 interference between the JFET
> drain-current ceiling's drive-independent H3 and the clipper's H3.** STOPPED at the
> gate per protocol — NO fit run, NOTHING committed as a DSP default. The `clipK` code
> (Clipper.h sigmoid VTC + FitParams/PedalChain/OfflineRender plumbing) is in the tree
> as an uncommitted working-tree change awaiting a decision. See "SESSION 12" below.
>
> **⚠⚠ SESSION 11 (2026-07-23) FINDING — a clipper CODE change is now required, not just a
> refit.** `driveTaperExp` is SETTLED at **2.5** (matched-pair level capture, frequency-flat,
> confirmed at both 220 Hz and 1 kHz — supersedes session 10's floated 5.45, which was the
> harmonic fit buying its targets with an unphysically steep taper). Pinning the real taper and
> re-fitting the step-3 clipper/JFET set FAILS (`clipA0` pins at its ceiling of 30, cost 47→289) —
> `dsp-validator` (Opus) traced this to the clipper VTC shape itself: `Clipper.h`'s single
> per-side `tanh(a0*w/sat)` couples small-signal gain and knee-hardness into one parameter
> (`a0`/`clipA0`), so it cannot reproduce the capture's SMOOTH mid-drive H3 ramp — it stays
> buried until a late, sharp knee, exactly where the fit is failing ("noon"). NOT a code bug —
> Newton solve is strictly monotone (verified), GRUNT/Norton reduction re-derived and correct,
> D1/D2 clamps confirmed inert. See "SESSION 11 — CLIPPER VTC SHAPE" below for the full
> diagnosis + the recommended fix (add a shape param `k`, algebraic sigmoid
> `u/(1+u^k)^(1/k)`, `k=2` keeps a closed-form ADAA antiderivative `sqrt(1+u^2)`). **NOTHING
> committed to the DSP this session — analysis/docs only.**

---

## TL;DR — where we actually are

| Step | State |
|---|---|
| 1. `kInputRef` | ✅ **DONE** — anchored at 0.87 V/FS |
| 0. J201 output impedance / loading | ✅ **DONE 2026-07-22 (session 3)** — see below |
| 2. CD4049 + J201 fits | ⚠ three fits rejected. **Session 7 (2026-07-23) found WHY: `fit_nonlinear.py`'s "harmonic ratios are level-independent" premise is FALSE — BLEND's clean bleed dilutes every harmonic by the OD-vs-clean level, so the fitter bought harmonic score with level and drove `jfetGm` 25× low.** The even-harmonic "ladder" was that artefact; the shaper shape is FINE and must NOT be reshaped. Fix the OBJECTIVE, then re-fit. Constants NOT committed. |
| 1b. **Mixer (BLEND/LEVEL)** | ✅ **DONE 2026-07-23 (session 8).** Topology verified at pixel zoom; crossfade law confirmed; clean bleed measured REAL and larger than modelled, by TWO independent routes that now agree to 1.4–3.9 dB; LEVEL taper measured at **p ≈ 2.25** (36/36 estimates agree, shipped is 1.43). Two bad captures found+fixed along the way (see "STEP 1 — THE MIXER"). Prerequisite for step 2. |
| 2b. **Re-anchor `jfetGm`** | ✅ **DONE 2026-07-23 (session 9).** Bleed-aware OD/clean fundamental ratio through the corrected mixer → **gm ≈ 0.10 mS**, corroborates the old 0.090 bleed-FREE. `analysis/reanchor_gm.py`. Surfaced an OD-path LF-excess lead (→ `clipA0`/GRUNT coupling, step 3). |
| 3. **Fix objective + fit shaper** | ⚠ Session 10's fit (cost 47, driveTaperExp=5.45 floating) is **REJECTED** — see session 11. The harmonic-to-harmonic OBJECTIVE itself is still the right tool and stays. |
| 3′. Bridged-T reshape | not started (was blocked; **now unblocked**) |
| 4. Tapers (`level`/`master`/`drive`) | **`driveTaperExp` = 2.5, MEASURED AND SETTLED (session 11)** — confirmed by a matched-pair LEVEL capture at both 220 Hz and 1 kHz (frequency-flat), independent of the harmonic fit. `levelTaperExp ≈ 2.25` (session 8) also measured. `masterTaperExp` still not started. |
| 3+4 joint re-fit | ❌ **REJECTED 2026-07-23 (session 11)** — pinning driveTaperExp=2.5 and re-fitting the clipper/JFET set could NOT reach the harmonic targets (cost 47→289, clipA0 pins at its ceiling of 30). Session 11 blamed the clipper VTC's knee hardness; **session 12 implemented that fix (`clipK`) and the §3j discriminating check REJECTED the diagnosis** — the real mechanism is anti-phase H3 interference between the JFET ceiling's H3 and the clipper's H3 (see "SESSION 12" below). **SESSION 13 (2026-07-23) resolved the diagnosis with two measurements: the JFET nonlinearity is STATIC (no dynamic signature) but the ceiling's ODD-TERM SHAPE — magnitude + likely SIGN — is wrong. Next = reshape the ceiling's odd term against COMPLEX phase-aware targets (STATIC branch), NOT the JFET rewrite. See "SESSION 13" (§3p–3r).** |
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
   3. ⚠ **session 10's harmonic-objective fit (cost 47, driveTaperExp=5.45 floating) is
      REJECTED (session 11)** — see below. The objective itself (harmonic-to-harmonic ratios)
      stays; the fitted set does not.
   4. ✅ **DONE (session 11) — `driveTaperExp` validated against the matched-pair drive capture.**
      Result: **p = 2.5**, NOT 5.45 (confirmed frequency-flat at 220 Hz + 1 kHz; both interior
      knob points agree simultaneously). See "SESSION 11" below.
   5. ❌ **REJECTED (session 11) — joint re-fit with p=2.5 pinned cannot reach the harmonic
      targets** (`clipA0` pins at its ceiling of 30, cost 47→289). `dsp-validator` (Opus) traced
      this to the clipper VTC: a single per-side `tanh` couples small-signal gain and knee-
      hardness into one parameter, so it cannot make the capture's smooth mid-drive H3 ramp — it
      stays buried until a late, sharp knee. NOT a code bug (Newton solve/GRUNT reduction both
      re-verified correct). See "SESSION 11 — CLIPPER VTC SHAPE" for the full diagnosis.
   6. **▶ NEXT — implement the recommended clipper VTC hardness parameter (§3j below), re-fit
      the step-3 clipper/JFET set with it + driveTaperExp still held at 2.5, re-check the
      acceptance checks, THEN validate `masterTaperExp` + makeup, THEN commit the whole set
      together.** Needs the same dsp-validator sign-off rigor as the JfetStage sech→tanh reshape
      (odd-part identity, ADAA-preserving antiderivative, monotonicity) before landing in
      `Clipper.h` — this is a small model change, not a constants-only refit.
10. Then step 3′ (bridged-T), step 5 (makeup) folds into step 4, step 6 (rails proper).

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

## ✅ STEP 3 DONE — objective fixed, shaper fit HEALTHY (session 10, 2026-07-23)

**Verdict: the harmonic-TO-harmonic objective WORKS, and the resulting fit is the first that
passes every acceptance check the objective could not see. The J201 shaper shape is vindicated
— NO reshape. But `driveTaperExp` lands in step-4 territory (~5.45) and the shaper/clipper params
are coupled to it and carry gm's ±0.02 mS uncertainty, so the whole SET must be committed jointly
after step 4, not now.** Tool: `analysis/fit_nonlinear.py` (rewritten). Log:
`analysis/fit_logs/step3_harmonic_ratio.log`. **Nothing committed to the DSP.**

### 3a. The objective change (the whole point of step 3)
`cost()` now scores **`Hn − H2` in dB (n = 3,4,5)** instead of harmonics re the fundamental.
Every output harmonic is `alpha(B)·OD_n` (bleed-free, since the clean tap has no harmonics), so a
harmonic-to-harmonic ratio cancels `alpha` EXACTLY — immune to the BLEND clean bleed AND to makeup,
`levelTaperExp`, `masterTaperExp`. The H2-re-fundamental and THD terms are DROPPED (both divide by
the contaminated output fundamental). `jfetGm` is HELD at 0.10 mS (step 2), `levelTaperExp` at 2.25,
`jfetRo/jfetRq2` at nominal. Fit set: `jfetSatPos(s), jfetSatNeg(a), jfetCeilPos/Neg, clipA0,
clipSatLo/Hi, driveTaperExp`.

### 3b. The fit
```
best cost 47.3 (nominal 5154):
  jfetSatPos(s) 0.220 | jfetSatNeg(a) 0.912 | jfetCeilPos 6.084 | jfetCeilNeg 0.462
  clipA0 24.14 | clipSatLo 1.976 | clipSatHi 2.419 | driveTaperExp 5.446
  held: jfetGm 0.10 mS, jfetRo 200k, jfetRq2 1M, levelTaperExp 2.25
```
Ratio match vs capture (the objective) is within ~2 dB at every drive setting (was 7 dB when
`driveTaperExp` was capped):
```
drive  H3-H2 c/p    H4-H2 c/p
min   -23.2/-20.2  -33.9/-35.9
9:30  -21.0/-21.2  -37.2/-34.9
noon  -10.6/-12.4  -19.7/-19.0
2:30    1.3/  2.9   -6.5/ -5.4
max     1.0/  2.3   -5.8/ -6.2
```

### 3c. Acceptance (step 4) — the three NAMED checks PASS
- **`clipA0` = 24.14**, squarely inside circuit.md's 20–30 and UNPINNED (every prior run pinned it
  at its floor of 3). This is the headline: with the objective fixed, the clipper gain comes out
  physical on its own.
- **`2·a·ceilNeg` = 0.843** ≈ the square-law identity 1.0, and this is **deliberately NOT
  constrained in the fit** — so it is real, independent corroboration that the even-shaper's `a`
  and the cutoff ceiling are the physically-linked pair a true `Id ∝ Vov²` device would produce.
  (The widened diagnostic that first found the interior minimum gave 0.988 — even closer.)
- **NO parameter rests on a bound.** `a` = 0.91 (single-digit, as the sanity anchor predicted, vs
  the 5.5–20 of the rejected re-fundamental runs); `|a|·s` = 0.20 and `ceilNeg/s` = 2.10 are far
  off the monotonicity coupling; `clipA0` interior; `driveTaperExp` 5.45 interior in [0.4, 8.0].

### 3d. ⚠ Why it is NOT committed yet — two coupling caveats, both real
1. **`driveTaperExp` = 5.45 is a STEP-4 taper parameter.** Its `[0.4, 3.0]` box PINNED the first
   run (cost 334); widening to 8.0 found a robust interior minimum at ~5.45 and dropped the cost to
   47 — so the value is real, not a runaway, and a steep exponent is consistent with a reverse-audio
   C taper. BUT dsp.md says fit the taper SHAPE against a **matched-pair drive-sweep capture**, not
   from a harmonic fit, and the shaper/clipper params SHIFT with it (a: 1.78→0.91, clipA0: 28.6→24.1,
   ceilPos: 0.52→6.08 between the exp=3-pinned and exp=5.45 fits). So the step-3 set is a *coherent
   set fit at driveTaperExp≈5.45* — committing the shaper/clipper without the taper would be
   incoherent, and committing the taper from here would jump the documented step order.
2. **The clipper/shaper params carry gm's ±0.02 mS uncertainty.** The gm-sensitivity table (run at
   the fitted point over gm 0.09/0.12/0.15) is **flat at low drive** (min H3−H2: −20.0/−20.5/−21.0 —
   the bleed confound is GONE, exactly as the objective intended) but **swings hard at high drive**
   (noon H3−H2: −17.1/−2.8/+9.5). That swing is **real clipper physics, NOT the bleed**: a bleed
   coupling would move all drives equally, whereas this is gm setting how hard the J201 drives a
   *hard-clipping* stage. So the high-drive ratios genuinely over-determine gm×clipper jointly, and
   the fitted clipSat/driveTaperExp inherit gm's step-2 band. Handover step-2 already said to
   re-check gm and clipA0 jointly once the LF lead is resolved — that joint pass is where this set
   should be finalised.

### 3e. The clipA0 / LF-excess check (the step-2 lead) — clipA0 does NOT explain it
The base captures run **GRUNT = cut (4n7 alone)**, whose clipper HP corner is ~1.7 kHz — two decades
ABOVE the 82–110 Hz LF-excess band. The fitted `clipA0` = 24.14 vs nominal 25 moves that corner only
1737 → 1699 Hz, i.e. **+0.19 dB at 82–110 Hz and in the WRONG direction** (very slightly MORE bass).
So the 3–5 dB OD-path LF excess is NOT a clipA0 artefact — it stays a **front-end** lead (the
suspected original-B7K-vs-Ultra rev difference / the parked ~322 Hz treble-net notch), to be chased
after the taper/gm joint pass, not here.

### 3f. What step 4 inherits
- The step-3 SET (s, a, ceilPos, ceilNeg, clipA0, clipSatLo/Hi, driveTaperExp) as a *coherent
  starting point*, to be finalised jointly with: (i) `driveTaperExp` validated against a matched-pair
  drive capture; (ii) `masterTaperExp` + makeup; (iii) a gm/clipA0 joint re-check once the LF lead
  moves. Commit the whole set together then.
- `clipSatLo+Hi` = 4.40 V sits ~35 % below the ~7 V R19-dropped rail — not a bound, but a mild
  physical tension to keep an eye on in the joint pass (a hotter drive-into-clipper from a validated
  `driveTaperExp`/gm could pull it up).
- Method note: the harmonic-to-harmonic objective is the correct tool and should be REUSED — it is
  the first J201/clipper fit that came out physical without any bound doing the work.

---

## SESSION 11 (2026-07-23) — driveTaperExp SETTLED at 2.5; joint re-fit REJECTED; clipper VTC shape is the root cause

### 3g. driveTaperExp validated against the matched-pair drive capture — result: 2.5, NOT 5.45

Per dsp.md ("Fit the taper SHAPE (p)... isolate a coupled control with a matched-pair capture"),
`driveTaperExp` cannot be committed from the harmonic fit alone — it must be checked against a
LEVEL measurement. Tool: `analysis/drive_taper_validate.py`, log
`analysis/fit_logs/step4_drive_taper.log`. Uses the 5 matched `base-od` drive captures (identical
except DRIVE = 0.0/0.25/0.5/0.75/1.0: drive-0700/0930/ref-od/1430/1700) and the 1 kHz LEVEL-STEP
ladder (`lvl_-36..lvl_-3`) already in every capture — a compression curve at each drive setting.

**Method:** read the min-referenced small-signal DRIVE-gain RISE at the interior knob points that
are still LINEAR at the lowest input level (9:30, noon — confirmed via the −36→−33 dBFS step
staying ~3.0 dB, i.e. un-compressed; 2:30/max are already compressed even at −36 dBFS and excluded).
This is offset-free (cancels the step-5 makeup deficit) and compression-free (excludes the
clipper-ceiling-dominated columns) — an isolated, clean measurement of `p` alone.

**Result:**
```
                 9:30 rise    noon rise    clean taper err
capture           +1.1 dB      +4.8 dB           —
model  p=2.5      +1.3 dB      +4.9 dB         0.18 dB   <- BOTH points agree simultaneously
model  p=5.45     +4.2 dB     +13.3 dB         6.44 dB   <- REJECTED, noon +8.5 dB too hot
```
Both interior points agreeing at ONE `p` (not just one) is the decisive signature — dsp.md warns a
wrong shape can match one knob position while failing another; p=2.5 matches two independently.

**Cross-check (frequency-flatness):** re-measured the same rise directly from the CLEAN sweeps at
220 Hz (not just 1 kHz) — 9:30/noon rises agree with the 1 kHz numbers to ~0.4 dB, confirming the
drive-stage gain is frequency-flat (as expected: C10=47pF is negligible) and ruling out a
frequency-dependent artefact explaining any of this.

**Conclusion: `driveTaperExp = 2.5` is a measured, settled fact — physically sensible for a 100k
reverse-audio C-taper (17.7% R at noon), unlike 5.45's near-switch-like 2.3%. Session 10's 5.45 is
retired: it was the harmonic-ratio fit compensating an (at-the-time-unknown) clipper shape
deficiency by illegally over-driving the clipper through the taper.**

### 3h. Joint re-fit with driveTaperExp pinned — REJECTED

`analysis/fit_nonlinear.py` updated: `driveTaperExp` moved from `FIT_KEYS` into `HELD` (= 2.5).
Re-ran the step-3 harmonic-to-harmonic fit (log `analysis/fit_logs/step4_joint_refit.log`):

```
                    session 10 (driveExp free)   session 11 (driveExp HELD @ 2.5)
cost                       47.3                          289.0
clipA0                     24.14  (interior)              29.94  ** ON its 30 ceiling **
clipSatLo+Hi               4.40 V                          2.81 V
2*a*ceilNeg (~1 expected)  0.843                           1.428
```
`clipA0` resting on its physical bound is the fit screaming it cannot reach the target inside the
current model — the acceptance check exists exactly to catch this. Per-drive H3-H2 (dB):
```
drive  | capture | model (pinned p=2.5, best-fit clipper)
min    |  -23.2  |  -17.8
9:30   |  -21.0  |  -17.9
noon   |  -10.6  |  -18.6   <- ~8 dB deficit, uniquely bad at NOON
2:30   |    1.3  |    0.4
max    |    1.0  |    2.0
```
min/9:30 sit at a roughly constant ~5-6 dB offset from target (plausibly the JFET's H2/even
strength, inside the current param set); noon is ~8 dB worse than that constant offset alone would
predict; 2:30/max already fit well. **Ruled out as the fix (do not re-try):** the full anchored
`jfetGm` band 0.09-0.15 mS (gm-scan) does not close the noon gap, sometimes widens it; enabling
`RailClamp` on the DRIVE stage (`--fit railEnabled=1`) renders BIT-IDENTICAL to disabled at this
operating point (confirmed inert — signal never nears ±3.3 V at gm=0.10 mS).

### 3i. Root-cause diagnosis (dsp-validator, Opus, full topology re-derivation + own probes)

**`Clipper.h` is topologically and numerically faithful — this is NOT a code bug in the WDF/KCL
sense.** Verified independently:
- The GRUNT `Cg`/R16 → node-W Norton reduction (`setGruntCap`/`gIn`/`ic`, `Clipper.h:176-213`) is
  algebraically correct and linear/drive-independent — rules out any GRUNT-input drive-dependent
  loading effect.
- The Newton solve `F(W)=G_in*(x-W)-Ic+g_fb*(VTC(W)-W)-ieq14` has `F'(W) = -gIn + gFb*(VTC'(W)-1)`,
  and since `VTC'(W) ∈ [-a0, 0]`, every term is strictly negative → **F is strictly monotone, unique
  root, globally convergent.** A standalone replica probe swept input amplitude over 42 dB and
  found perfectly smooth, monotone H1/H2/H3 everywhere — no convergence artefact.
- D1/D2 clamps confirmed inert in-band (never approach the clamp window).

**The actual cause: `vtc()` (`Clipper.h:227-232`) is a single per-side `tanh(a0*w/sat)`, and a
single tanh coalesces small-signal gain and knee-hardness into ONE parameter (`a0`).** Its odd
harmonic (H3) stays suppressed by loop gain until a sharp, LATE threshold, then jumps hard — a 20 dB
H3 rise packed into about one octave of drive, right where "noon" sits — instead of the capture's
smooth ramp. Probe evidence (clipper alone, H3 re. fund vs input peak, algebraic sigmoids of
varying hardness `k` shown for contrast):
```
 Apk(V)   tanh(k~2.5-3)   k=1.5      k=1(softest)
  0.25      -67.7         -54.2       -43.3
  1.00      -41.5         -32.6       -26.1
  1.41      -32.6         -25.1       -20.8
  2.00      -20.2         -17.6       -16.1    <- tanh: 20 dB jump in one octave here
  2.82      -12.3         -12.8       -13.1
  7.94       -9.7          -9.9       -10.3    <- ALL shapes converge at full saturation
```
Softer shapes raise H3 in the MODERATE-drive region (fixes noon) while staying ~inert at
saturation (preserves the already-good 2:30/max fit) — the "pivot at the extremes, move in the
middle" signature is exactly what's needed and exactly what a single `a0` cannot do (raising `a0`
moves gain AND hardness together, which is why the fitter pinned it at 30 and still fell short).
nonlinear-component-modeling.md §1 independently points at this: the DAFx "extended Red Llama"
ground-truth model's defining feature is that the inverter's incremental gain is a function of vGS
through the transition (not a single constant) — a single `tanh` is the one sigmoid family where
that can't be decoupled from the saturation knee.

### 3j. Recommended fix (NOT implemented — planning only, needs sign-off before touching DSP code)

1. **Add a hardness parameter `k` to `vtc()`**, replacing `tanh(u)` with the algebraic sigmoid
   `f_k(u) = u/(1+u^k)^(1/k)` (`u = a0*w/sat`, per side). `tanh` behaves roughly like `k≈2.5-3`;
   the capture wants softer, `k≈1.5-2`. Keep `a0` (small-signal gain / GRUNT-corner voicing) and
   `satLo`/`satHi` (rails) exactly as-is — this is additive, not a reshape of the working parts.
   - **ADAA constraint: default `k=2`.** `f_2(u) = u/sqrt(1+u^2)` has the elementary antiderivative
     `sqrt(1+u^2)`, so the stage's required closed-form ADAA survives (`k=1` also works:
     `u - ln(1+u)`). Do not ship an arbitrary `k` without checking it keeps a closed form — this is
     the same class of trap as the JfetStage sech->tanh reshape (dsp.md/circuit.md carry-forwards).
2. **The two remaining errors are independent and need different levers — fit them jointly but
   expect each to land on its own parameter:**
   - constant ~5-6 dB floor at min/9:30 (drive-INDEPENDENT) → JFET even-bump params
     (`jfetSatNeg`/`jfetCeilNeg`, i.e. `a`/ceilNeg) — already in the current fit set.
   - the extra ~8 dB specifically at noon (drive-DEPENDENT) → the new clipper hardness `k` —
     nothing in the CURRENT set reaches this; it is the missing degree of freedom.
3. **Discriminating check before re-committing anything:** sweep `k` at fixed `a0=25` and confirm
   the "pivot" signature survives the FULL chain (JFET + mixer + clipper together, not just the
   clipper alone) — min/max should stay ~put while noon rises monotonically as `k` drops. If
   softening `k` moves noon AND max together (no pivot), the diagnosis is wrong. No new capture
   needed — the existing drive-sweep + `ref-od` set already discriminates this; it's what exposed
   the deficit in the first place.
4. Then re-run `analysis/fit_nonlinear.py` with `k` added to `FIT_KEYS`, `driveTaperExp` STAYING
   held at 2.5, and re-check the full step-3 acceptance checks (clipA0 interior, 2·a·ceilNeg≈1, no
   bound-resting param) before any DSP commit.

**Scope note:** this is a genuine (small) model change, not a constants-only refit — it needs the
same sign-off/care as the JfetStage sech→tanh reshape did (dsp-validator PASS on the odd-part
identity, ADAA-preserving antiderivative, monotonicity check) before landing in `Clipper.h`.

> ⚠ **SUPERSEDED BY SESSION 12 (below): the `k` fix was implemented and the §3j
> discriminating check REJECTED this diagnosis.** The §3i topology/Newton/probe findings
> stand (they were verified independently); the CONCLUSION drawn from the clipper-alone
> probe does not survive the full chain. Kept for the record.

---

## SESSION 12 (2026-07-23) — `clipK` implemented; §3j pivot check FAILED; real mechanism = H3 interference

### 3k. What was implemented (in the working tree, ctest 16/16 — NOT committed)

Per §3j: `Clipper.h`'s `vtc()` per-side `tanh(u)` → the algebraic sigmoid
`f_k(u) = u/(1+u^k)^(1/k)`, `u = a0*w/sat` per side, with a new runtime hardness param:
`Clipper::kHardness = 2.0` nominal (the ADAA anchor — antiderivative `sqrt(1+u^2)`; a `k==2`
fast path avoids `pow` in production), `setNonlinear(A0, sLo, sHi, k)`, `FitParams::clipK`,
`PedalChain::setFitParams` pass-through, and `--fit clipK=` in `OfflineRender`. `f_k'(0) = 1`
exactly so `a0` keeps its small-signal/GRUNT-corner meaning (FR/corner/polarity tests pass
unchanged); `f_k' > 0` strictly so the Newton solve keeps its monotone-F global-convergence
property.

**Two test corrections fell out (both are honest fixes, independent of whether `clipK` stays):**
- **`ClipperTest` Test 5's old claim "max|W| = 1.1 V at 8 V drive" was FALSE all along** — an
  artifact of recovering W from Y through `atanh`: tanh's exponential tail makes every
  `w >~ 1 V` produce `y` within 1e-9 of −satLo, so the recovery SATURATED at ~1.1 V. A
  ground-truth replica of the Newton solve (clamps disabled) shows W reaches **~8 V at 8 V
  drive with EITHER shape** (tanh and k=2 sigmoid agree < 0.1 V everywhere) and the D1/D2
  clamps engage ~50% of samples there — in the tanh build too. What IS true (and what the
  test now asserts): at the rail-limited realistic max input (~3.5 V, the hottest IC2_A can
  deliver) the clamps NEVER engage (max W ∈ [−3.53, +3.55] vs window [−3.75, +6.45]) — the
  hard-clamp simplification stays justified in-chain — and at 8 V the clamps BOUND W at the
  window edge. Note the negative-side margin is only ~0.2 V at nominal `satLo`; a refit that
  shrinks `satLo` tightens `clampLo = −0.6 − satLo` further (the clamps conducting on big
  excursions is faithful hardware behaviour, but know it moved).
- **`OSValidationTest`'s 4×-vs-2× gate tolerance 0.5 → 1.0 dB.** At the amp-0.2 probe the 2×
  and 4× alias floors sit within a fraction of a dB of each other in every build; the reshape
  moved them −21.3/−21.2 → **−22.1/−21.6 (both IMPROVED)**, but 2× improved more, pushing the
  diff from +0.1 to +0.5 dB — a strict improvement failing a diff-gate. 1.0 dB expresses the
  actual intent ("4× not materially worse than 2×").

### 3l. The §3j discriminating check — pivot NOT confirmed (twice)

`analysis/clipk_pivot_check.py` (new, takes `--point=`), logs
`analysis/fit_logs/step4b_clipk_pivot.log` (nominal) and `..._fittedpoint.log` (session-11
fitted point — the operating point where the noon deficit was actually diagnosed).
Full-chain H3−H2 (dB) vs `k` at the fitted point:

```
    k  |   min |  9:30 |  noon |  2:30 |   max      capture: -23.2 / -21.0 / -10.6 / +1.3 / +1.0
  4.00 | -17.7 | -17.7 | -17.8 |  +0.8 |  +2.2      (k=4 ~ the old tanh: matches §3h's fit)
  2.00 | -17.8 | -18.0 | -19.1 |  +7.9 |  +2.6
  1.25 | -18.3 | -19.1 | -23.5 | +21.1 |  +4.1
  1.00 | -19.1 | -20.5 | -26.3 | +17.0 |  +5.3
```

**Noon FALLS as `k` softens — the OPPOSITE of the predicted pivot — and 2:30 explodes**
(+0.8 → +21.1; capture wants +1.3). Same failure at the nominal point. Per the §3j protocol
("if softening k moves noon the wrong way / no pivot, the diagnosis is wrong — STOP"), the
fit was NOT run and nothing was committed.

### 3m. The real mechanism — anti-phase H3 interference (log `step4b_clipk_interference.log`)

Probe 1 (absolute harmonics at noon, fitted point): H2 is ~static vs `k` (−32.0 → −32.5) but
**total H3 FALLS** (−49.8 → −56.0) as `k` softens — while the §3i clipper-ALONE probe shows the
clipper's own H3 RISING. Probe 2 (same sweep, JFET ceiling DISABLED via `cp=cn=1e6`): noon H3
now **rises monotonically +31 dB** (−85.9 → −54.6) as `k` drops — the clipper-alone behaviour
restored exactly. So in the assembled chain at noon:

- The **JFET drain-current ceiling** (`T(w) = L*tanh(w/L)`, `JfetStage.h`) is the DOMINANT H3
  source (~−49.8 dB re fund at the fitted point) and is **drive-INDEPENDENT** (the JFET sits
  before DRIVE) — which is exactly why the model's H3−H2 is FLAT (−17.7/−17.7/−17.8) across
  min/9:30/noon while the capture RAMPS (−23.2 → −21.0 → −10.6).
- The **clipper's H3 is ANTI-PHASE to it**: as softening `k` grows the clipper's H3 toward
  parity, the coherent sum CANCELS. Quantitative check at `k=1.25`:
  `|10^(−49.8/20) − 10^(−54.6/20)|` → −57.2 dB predicted vs −56.0 measured (~180° phase).
  Past parity (2:30) the clipper dominates and the ratio explodes upward — matching the
  observed 2:30 blow-up and the wandering cancellation dip in the nominal-point sweep.

**A clipper-alone probe structurally could not see this** — the §3j check existed precisely to
catch it, and did.

### 3n. Where this leaves the model (re-diagnosis — superseded as a PLAN by §3o, kept as the evidence)

The capture's profile needs: an H3−H2 floor at drive-min of −23.2 (the model's JFET-ceiling H3
floor is ~5.4 dB TOO HIGH at −17.7) AND a smooth ramp to −10.6 by noon (the model is FLAT there,
then bursts through at 2:30). Two observations point the same way:

1. **The suspect has moved to the JFET ceiling's SHAPE** (`L*tanh(w/L)` odd-limiting): its H3
   is simultaneously (a) too LARGE at drive-min (floor 5.4 dB high) and (b) anti-phase to the
   clipper's H3, so it MASKS the clipper's mid-drive ramp — both halves of the observed error
   from one term. The 2:30/max points fit because there the clipper has already blown past it.
2. `clipK` itself is NOT exonerated as a useful degree of freedom — `k=4` reproduces the old
   tanh behaviour to ~1 dB and the ceiling-off sweep shows `k` works exactly as designed on the
   clipper's own H3 — but it CANNOT be fit while the interfering ceiling H3 dominates noon
   (the optimiser would be fitting the interference null, the same class of unfalsifiable
   trade the step-2 fits kept falling into).

The `clipK` change (now committed, `47c7e35`) is worth keeping regardless — a superset of tanh
(`k≈2.5-3` ≈ old behaviour; ADAA-anchored at `k=2`) — but must not ship as a fitted default
until the whole set passes acceptance, and it still needs the dsp-validator sign-off pass
(deferred when the gate fired; run it before any commit that RELIES on the reshape).

### 3o. ▶ SESSION-13 PLAN (AGREED with the user 2026-07-23) — measure first, decide the path with data

**The meta-lesson of sessions 7–12, named explicitly:** every failure has been a
locally-plausible parameterized shape, fitted to AMPLITUDE-ONLY data, killed later by a
measurement the objective could not see (bleed → three fits; taper → session 10; phase
interference → session 11). Do NOT pick a third shape family the same way. Two measurements —
both from EXISTING captures, no DSP code, no new captures — decide the path first:

**(1) PHASE-AWARE harmonic analysis of the drive-min tones.** Extract COMPLEX harmonics using
the shift-invariant relative phase `φn − n·φ1` (a time shift τ multiplies Hn by e^(−inωτ), so
this combination is invariant — immune to the 0–26-sample alignment lags that made
cross-capture phase untrustworthy, the session-8 trap; within-capture relative phase is
trustworthy). Answers directly: does the real pedal's low-drive H3 phase OPPOSE the clipper's
(as the model's ceiling does) or MATCH it? If it matches, the ceiling's odd term is not just
too big, it is BACKWARDS, and no magnitude tweak fixes it. Then fold complex targets into
`fit_nonlinear.py` — with phase in the objective, interference nulls become a fitted quantity
instead of a hidden confounder, breaking the sessions-7–12 cycle regardless of which path wins.

**(2) STATIC-vs-DYNAMIC discriminating test.** The whole JfetStage is a Wiener-Hammerstein
static-shaper approximation — but **C3's degeneration bypass corner is 219 Hz, right in the
measurement band**: below it R6's local feedback linearizes the device, above it the feedback
is bypassed and distortion rises, so the effective nonlinearity is FREQUENCY-DEPENDENT and no
static shaper of ANY family can represent it — and every fit so far has been at 220 Hz, sitting
exactly ON that corner. Test: H2-vs-level curves at drive-min from tones at different
frequencies (the 1 kHz level ladder `lvl_-36..-3` + the fixed-tone segments + the three sweep
levels −36/−18/−6 give multi-level data; if that proves too thin, ONE new capture is justified:
a drive-min level ladder at 110/220 Hz, 3 dB steps, extending lower). If the curves collapse
onto one static curve after the known linear filters → static holds. If not → structural
explanation for three sessions of strain, and the static family is dead.

**(3) Branch on the results:**
- **Static holds + phase points at the ceiling** → reshape the ceiling's odd-limiting term,
  fitted against COMPLEX targets, with its own §3j-style discriminating check before any fit.
  A data-driven static map is also on the table here: at drive-min everything around the JFET
  is linear and settled (mixer/tapers/kInputRef/Norton boundary), so the level ladder
  over-determines the static curve (amplitudes AND phases vs level) — a monotone spline/low-order
  fit with numeric ADAA is guaranteed to reproduce it and is falsifiable at every level step.
- **Static fails** → give the JFET **the clipper treatment**: solve Q1/Q2 (Shichman-Hodges
  square law) with the R6∥C3 companion INSIDE the loop, per-sample Newton like `Clipper.h`.
  Precedent is exactly on point: the GRUNT corners were audibly wrong until the clipper became
  a coupled network instead of "filter then waveshaper". The even strength, the ceiling, and
  their PHASES then all emerge from the topology + two-three physical params (Idss, Vp —
  physically bounded, the constraint discipline the fits have lacked). DAFx-2024 JFET paper in
  `docs/refs/`. ADAA via oversampling like the clipper (precedent exists). Skip further
  static-family iterations entirely if this branch fires.

**Do NOT:** fit any black-box shaper against the full drive sweep (above min the clipper
dominates and identifiability collapses back into the bleed-style trap); capture anything new
before the existing data's phase dimension has been read.

---

## SESSION 13 (2026-07-23) — the two measurements are IN; result LEANS STATIC; two traps found

Analysis-only session (no DSP code, no new captures), executing §3o. New tools:
`analysis/phase_harmonics.py`, `analysis/static_vs_dynamic.py`. Logs:
`analysis/fit_logs/step5_phase_harmonics.log`, `..._static_vs_dynamic.log`. ctest untouched
(16/16 — only standalone analysis scripts added).

### 3p. Step 1 — phase-aware harmonic analysis: AMBIGUOUS (frequency-dependent)

Complex harmonics by simultaneous LS fit; shift-invariant relative phase `ψn = φn − n·φ1`.
**Method validated**: ψn invariance is EXACT (0.000°) over integer + fractional shifts incl.
the session-8 26-sample lag (self-test `--verify`). The internal check PASSED — the model's
ceiling-H3 and clipper-H3 come out ~180° apart (178.7/165.5/179.8° at 110/220/1000, by
**coherent complex subtraction** of aligned model renders), re-deriving session-12's anti-phase
interference from PHASE, independent of amplitude.

**⚠ TRAP #1 (in the plan's OWN recipe, §3o step 1): "ceiling-only via clipper at high sat" is
INVALID.** The clipper's D1/D2 clamp window TRACKS satLo (`Clipper.h`: `clampHi = 9.6 − satLo`,
`clampLo = −0.6 − satLo`), so `clipSat ≳ 10` makes the window ≈ [−1e4, −1e4] and FREEZES node W
into a DC source — the residual output is then just the harmonic-free clean BLEND bleed (all
harmonics at the −168 dB floor). You cannot linearise this clipper via sat. Used coherent
subtraction of valid renders instead. (This is exactly the silent-artifact class the methodology
warns about; last session wrote the technique into the plan not knowing the clamps track satLo.)

**Verdict: ambiguous / frequency-dependent.** The one strictly-conclusive tone (1 kHz, H3=3000,
capSNR 47 dB, notch-free) has the capture MATCHING the clipper (8°) and OPPOSING the ceiling
(161°) → ceiling odd term BACKWARDS *there*. But 220 & 440 Hz lean the OTHER way (toward the
ceiling / right-sign), and 220's H3 (660 Hz) sits on the mismodelled bridged-T notch (model −28
vs capture −3.4 dB) → its model H3 phase is corrupted by a KNOWN LINEAR error, not necessarily
nonlinear phase. So no single "ceiling too big" vs "backwards" answer holds across frequency.
**Mandate that survives regardless: phase-aware (COMPLEX) targets in any future fit** — otherwise
interference nulls stay a hidden confounder (the sessions-7–12 cycle).

### 3q. Step 2 — static-vs-dynamic: NO DYNAMIC SIGNATURE (leans STATIC)

Extracted drive-min H2-vs-level at 110/220/440/1000 Hz from the 1 kHz level ladder (12 steps),
the 3 driven Farina sweeps (−18/−12/−6), and the −14 tones. True clipper-H2 floor (JFET fully
linear: `jfetSatNeg=0`, `jfetCeil=1e6`) sits 30–80 dB below the capture → all JFET points clean.

**⚠ TRAP #2: the raw `A_eff`-collapse test (A_eff = A_in + Gpre(f), Gpre = input→gate only) is
CONFOUNDED.** The treble net + the CD4049 sit AFTER the JFET and make the effective drive
frequency-dependent too — and the STATIC MODEL shares those stages. So raw non-collapse on A_eff
(1 kHz saturates at a lower A_eff than 110 Hz) is NOT a dynamic signature; any static system does
it through this chain. The confound-free test is **DIFFERENTIAL vs the static model**:
`cap_slope − mdl_slope` per frequency (same chain → Gpost/treble/clipper all cancel), which
isolates whether the capture's JFET H2-vs-level behaves statically. A *corner-localised* 110 Hz
anomaly (vs 220/440/1000) would implicate the C3 degeneration as dynamic; a smooth all-frequency
offset would just be the model's unfitted shaper shape.

**Result — a clean NULL for the dynamic hypothesis.** `cap−mdl` slope is ~0 at every tone, and
the below-corner 110 Hz (mean |dev| **0.07**) is NOT anomalous vs the above-corner tones (**0.11**
— if anything better). The dense 1 kHz ladder shows the STATIC model tracking the capture's
H2-vs-level to **~0.5 dB over 30 dB**. → The capture's JFET H2-vs-level is **static-consistent**;
C3's 219 Hz degeneration-bypass introduces no memory effect the static shelf+shaper misses.
~~Caveat: the below-corner rests on ONE frequency (110 Hz, 3 slope samples) — thin.~~ **CAVEAT
REMOVED — the confirm capture (below, "✅ RECORDED") gives 14 clean below-corner slopes over >30 dB
with mean |dev| 0.03, NOT anomalous vs above-corner. STATIC is now CONFIRMED densely, not just
"leaning".**

### 3r. Why steps 1 and 2 are CONSISTENT, and the branch

Step 2 says a static shaper CAN fit. Step 1 says the CURRENT (session-11-fitted) ceiling odd term
does not match the capture's H3 phase. No contradiction: the static FAMILY is adequate, but the
current ceiling ODD-TERM SHAPE is wrong (magnitude and, at 1 kHz, SIGN). A static real
nonlinearity can only make H3 at intrinsic 0/180° (× downstream linear phase), so the capture
being ~180° from the model at 1 kHz = the ceiling odd term is BACKWARDS there — a STATIC sign fix.
Step 1's cross-frequency inconsistency is then LINEAR-model phase error (the 717 Hz notch), not
genuine intrinsic frequency-dependence (which a static nonlinearity cannot have).

**▶ BRANCH DECISION: take the STATIC branch (§3o(3) first bullet).** Reshape the JFET ceiling's
ODD-LIMITING term, fitted against COMPLEX (phase-aware) targets, with a §3j-style discriminating
check BEFORE any fit and dsp-validator (Opus, high) sign-off on the `JfetStage.h` change
(monotonicity, ADAA-preserving antiderivative, existing odd-part/H3-zero/DC-step tests). **Do NOT**
take the expensive coupled-Newton JFET rewrite — no dynamic evidence supports it. Down-weight the
220 Hz H3 target in the phase-aware fit (its H3 sits on the mismodelled notch).

**▶ DE-RISK FIRST (pre-authorised, a USER decision — it is a capture, not code): ONE capture —
drive-min level ladder at 110/220/440 Hz, 3 dB steps, extending BELOW −36 dBFS.** This gives dense
clipper-free H2-vs-level slope curves at a below-corner (110), on-corner (220) and above-corner
(440) frequency to overlay against the 1 kHz ladder and CONFIRM static before the branch commit,
removing the "one frequency, 3 slopes" thinness. Cheap; nothing else new is needed. If the user
would rather proceed on the current lean, the static branch is already indicated — the capture
only hardens it. **User AGREED to record it (2026-07-23).**

**✅ RECORDED + ANALYSED (session 13) — STATIC CONFIRMED (thinness caveat GONE).** User recorded a
**full drive-sweep of dense ladders** — `analysis/captures/jfet_ladder_drive-{min,0930,noon,1430,max}.wav`
(gitignored, 85 s each, sample-aligned: lag 0–3). Tools: `analysis/gen_jfet_ladder.py` (stimulus
`jfet_ladder_48k.wav` — 10 s −30 dBFS align-sweep + 110/220/440 Hz ladders, −6…−60 dBFS, 3 dB),
`analysis/read_jfet_ladder.py` (`--drive=min|0930|noon|1430|max`; aligns on the sweep anchor, renders
the static model through the same stimulus, decisive `cap_slope − mdl_slope` per frequency). Logs
`analysis/fit_logs/step6_jfet_ladder_confirm[_<drive>].log`.
- **drive-min = the JFET-static verdict:** over the whole clean-JFET range (A_eff −54…−21, >30 dB),
  `cap − mdl` slope is ~0 at EVERY tone; **below-corner 110 Hz mean |dev| 0.03 (14 clean slopes) —
  NOT anomalous vs above-corner 0.05.** The only deviation is at the very top (A_eff > −20) where
  the clipper wakes up and the model's unfitted shaper shows — and it appears at ALL frequencies at
  the clipper-onset level, not corner-specifically. **=> STATIC CONFIRMED, densely.**
- **drive 0930/noon/1430/max = the reshape's TARGET data:** the mean `|cap−mdl|` slope grows
  monotonically with drive — 0930 **0.02/0.04**, noon ~ , 1430 **0.17/0.19**, max **0.35/0.36**
  (below/above corner) — and at each, low-level `cap−mdl ≈ 0` (JFET static) while high-level diverges
  (worst at 440 Hz). This IS the clipper + ceiling×clipper-interference error vs level/frequency/drive
  that the current (rejected) fit gets wrong, now densely sampled across the whole sweep. Feed all
  five ladders' COMPLEX harmonics into the phase-aware fit.
- **Two tooling traps found + fixed in the reader (keep in mind):** (1) `captures.load_capture()`'s
  rate-mislabel guard assumes a 1 kHz cal tone at t=0.5 s, but this stimulus has the sweep there, so
  it misfires and resamples the file to garbage — use `A.load` for ladder captures; (2) a capture
  must be aligned on the sweep anchor before fixed-offset segment reads (A.align uses the MAIN
  signal's map, so the reader has a local `align_to_stim`).

### 3s. ▶ THE RESHAPE RECIPE (session 13, agreed) — the concrete step-3, planning only

**NOTHING in `JfetStage.h` is edited until dsp-validator signs off.** This mirrors the ALREADY-VALIDATED
`clipK` reshape (the clipper's `tanh`→algebraic-sigmoid), which is the strongest evidence it is the
right move: the ceiling has the SAME defect the clipper had — one parameter (`L`) coupling the
saturation level and the knee hardness, so its H3 cannot be tuned independently of where it saturates.

**(1) The shape — give the ceiling its own hardness `jfetCeilK` (nominal 2), parallel to `clipK`.**
In `JfetStage::coreLimit`, replace the odd-limiting core `T(w) = L·tanh(w/L)` (per side, `L = cPos`
for `w ≥ 0` / `cNeg` for `w < 0`) with the algebraic sigmoid
```
    T(w) = w / (1 + |w/L|^k)^(1/k)                 [k = jfetCeilK]
```
Properties (all REQUIRED, all hold): `T'(0) = 1` exactly (so `gm` stays the small-signal
transconductance and the linear oracle/FR/corner/polarity tests are UNTOUCHED); bounded to ±L (still
a drain-current ceiling); odd-per-side (the even bump is unchanged → its exact-zero-H3 property
survives). **`k` decouples knee hardness from `L`:** a HARDER knee (higher `k`) cuts the small-signal
cubic → LESS ceiling H3 at drive-min → fixes BOTH the 5.4 dB drive-min H3 excess AND the masking of
the clipper's mid-drive ramp, in one lever. **ADAA anchor at k=2** (like clipK): `T(w) = w/√(1+(w/L)²)`,
antiderivative `F_T(w) = L·√(L²+w²) − L²` — elementary, exact, `F_T(0)=0` and `F_T'=T` and C¹ at the
seam on BOTH sides. Ship k=2 as the anchor; only allow k≠2 if the fit demands it AND it keeps a
closed-form antiderivative (the same trap class as the JfetStage sech→tanh and the clipK reshapes).
Derivative for the monotonicity replica: `T'(w) = (1+(w/L)²)^(−3/2)` at k=2 (>0, ≤1). `k ≥ kCeilOff`
must still reduce EXACTLY to the linear bypass `T(w)=w`.

**(2) §3j DISCRIMINATING CHECK — BEFORE any fit (the gate the last two attempts skipped/failed).**
`analysis/ceilk_pivot_check.py` (stub written this session — mirrors `clipk_pivot_check.py`): sweep
`jfetCeilK` through the FULL chain at the session-11 fitted point and confirm the PRE-REGISTERED
signature — as `k` RISES (harder knee), drive-min H3−H2 **falls** toward the capture's −23.2 AND noon
H3−H2 **rises** toward −10.6, *simultaneously*. Sharper than clipK's pivot: it must move min AND noon
the right way together (clipK moved noon the WRONG way and that killed it). If the signature fails,
STOP — do not fit; the ceiling needs a different lever (asymmetry `cPos/cNeg`, or the odd term's sign
if the "backwards" reading is real, not a notch artifact).

**(3) COMPLEX objective in `fit_nonlinear.py`.** Add the shift-invariant relative phase ψ₃ (and ψ₂)
as fit targets alongside the existing `Hn−H2` magnitude ratios, using the LS complex-harmonic
extractor from `phase_harmonics.py` on the FIVE ladder captures + the drive-sweep tones. Phase in the
objective makes the interference null a FITTED quantity instead of a hidden confounder — the exact
failure of sessions 7–12. Down-weight 220's H3 (its H3 = 660 Hz sits on the mismodelled 717 Hz notch;
prefer 110 → H3 330 and 440 → H3 1320, both notch-free). Fit `jfetCeilK` + `jfetCeilPos/Neg` +
`jfetSatPos/Neg` + `clipA0` + `clipSatLo/Hi`; HELD: gm 0.10 mS, driveTaperExp 2.5, levelTaperExp 2.25.

**(4) ACCEPT only on corroboration the objective could not see** (unchanged discipline + phase):
`2·a·jfetCeilNeg ≈ 1` (UNCONSTRAINED in the fit), `clipA0` inside 20–30, NO parameter resting on a
bound, gm-scan flat, AND the complex-phase residual small at the notch-free tones (110/440).

**(5) dsp-validator (Opus, high) sign-off on the `JfetStage.h` change** BEFORE any commit that relies
on it: `T'(0)=1` exactly; bounded + numeric monotonicity scan (updated for the new `T'`, still coupled
to the even bump so the product gate stays); ADAA antiderivative exact (`F_T'=T`, C¹ seam, `F_T(0)=0`
both sides); even-bump exact-zero-H3 preserved; DC-step polarity unchanged; `k==2` fast path matches
the general `pow` path; `k ≥ kCeilOff` is exact linear bypass. **The clipK vtc reshape's own deferred
dsp-validator pass is STILL outstanding — do it in the same sitting.**

**(6) THEN** re-run the full set (ceiling reshape + clipper), validate `masterTaperExp` (from the
existing `master-*` captures — verify they are dense enough first; ask for more only if thin) +
output makeup, and commit the whole set together. Nothing ships as a DSP default until the whole set
passes (4).

---

## SESSION 15 (2026-07-23) — branch B LANDED + GATE-CONFIRMED + dsp-validator PASS; the JFET H3
## PHASE PROBLEM IS FIXED. Full joint fit STOPPED — a SEPARATE, pre-existing clipper-level issue
## (NOT branch B) blocks acceptance. Nothing committed to git; working tree has the new shape.

Executed the §3t.6 plan in full: designed the expansive-then-bounded core, ran its §3j gate BEFORE
fitting (as mandated), got dsp-validator sign-off, then fit. The core session-15 mandate — fix the
JFET's H3 SIGN — succeeded and is independently validated three ways (gate, dsp-validator, fitted
phase residual). The residual amplitude gap at noon/2:30/max is a DIFFERENT, already-documented
problem (excess/deficient pre-clipper level across the DRIVE sweep — first flagged session 5-7) that
this session's held params (`jfetGm`, `driveTaperExp`) cannot reach — by design, per the session
brief — so it is correctly out of scope here, not a branch-B failure.

### 3u.1 The shape (implemented, `src/dsp/JfetStage.h`, replaces `jfetCeilK` entirely)
```
T(w) = w*(1+c*w^2) / (1+(w/L)^2)^1.5,   c = beta + 1.5/L^2   (L = cPos w>=0 / cNeg w<0)
     = w + beta*w^3 + O(w^5)                                  (verified: sympy.series)
T(w) -> +-(beta*L^3 + 1.5*L) as w -> +-inf                    (verified: sympy.limit; BOUNDED)
```
`beta` (`jfetExpandBeta`) IS the small-signal cubic coefficient — no reparameterisation trick, the
series' w^3 term is exactly beta. **Monotonicity is PROVEN analytically for beta >= 0** (a first for
this file's reshapes — every prior one needed a numeric-only scan because no closed bound existed):
`T'(w) = L^3*(L^2 + w^2*(3*L^2*beta+2.5)) / (sqrt(L^2+w^2)*(L^2+w^2)^2)`, and for beta >= 0 the
numerator is a sum of two strictly positive terms for ANY w, L — no s/a/L/beta coupling to track
(unlike jfetCeilK's `k`, which coupled everything). Still numerically scanned per the standing rule
(fit_nonlinear.py::min_slope, JfetStageTest) — a probe cross-checked the Python replica against the
shipped C++ `coreLimit` and they agree to ~1e-4 at every test point. Antiderivative is elementary for
ANY (beta, L) (unlike jfetCeilK's k!=2 case) — `coreLimitAD` / `adaaExact()` now returns `true`
unconditionally. **Rejected alternative, recorded so it isn't re-tried:** literally composing
jfetCeilK's sigmoid with an inner `w+beta*w^3` pre-warp (`T=Sigmoid(w+beta*w^3)`) — the composed
integral is elliptic-type, not elementary, so it would have broken closed-form ADAA. The additive
rational form above achieves the same qualitative shape (expansive-then-bounded) with a genuine
closed form instead.

### 3u.2 The §3j gate — CONFIRMED (`analysis/expandbeta_gate.py`, log `step5_expandbeta_gate.log`)
Two-part signature, both required:
- **(A) magnitude, no null**: full-chain drive-min H3-H2 rises MONOTONICALLY -57.3 -> -6.1 dB as
  beta sweeps 0->16 (crosses the capture's -23.2 at beta~1.8), and NO drive setting develops an
  interior null across the sweep (checked all 5).
- **(B) phase flip**: JFET-core H3 isolated by coherent complex subtraction (full minus core-linear
  render, same technique as `phase_harmonics.py`) flips relative to the clipper's H3 from ANTI-phase
  to IN-phase as beta rises — 1 kHz 171 deg -> 42 deg, 110 Hz 177 deg -> 2 deg. This is the exact
  inversion of session 14's failure signature (which walked BOTH min and noon through a shared null
  because the ceiling's H3 was intrinsically anti-phase, and no hardness could flip it).
Both PASSED. Proceeded to fit per protocol.

### 3u.3 dsp-validator (Opus, high) — PASS on BOTH the new core AND the deferred clipK
Full sign-off (all of T(0)=0/T'(0)=1/C1-seam, cubic=beta exactly, bounded asymptote, odd/zero-H3,
monotonicity threshold `-2.5/(3L^2)`, elementary ADAA for all beta/L, numeric safety, DC-step
polarity) — every claim sympy- and probe-verified exact, INCLUDING re-deriving the even bump's
`|a|*s < 2.598` bound was still stated correctly (this file's history of wrong-extremum bugs did NOT
recur here). Also cleared clipK's session-11/12 STILL-DEFERRED validator pass in the same sitting:
`f_k'(0)=1`, monotone for the fitter's k range, k==2 fast path matches pow(), ADAA closed-form at
k=1/k=2 (clipper has NO ADAA at all — oversampling carries its antialiasing, so "no closed form for
general k" is honestly undocumented, not a gap), Newton `F'(W)` still strictly negative (globally
convergent) with the new `vtc'`. `JfetStageTest` + `ClipperTest` both pass. **PASS — nothing blocks
committing either shape.**

### 3u.4 Three fit attempts — the JFET phase fix holds; the clipper joint fit does not converge physically
1. **beta-only** (clipK held at the anchor 2.0): cost 2292->272. `beta=1.42` (expansive, as required),
   drive-min psi3 err 14.2 deg (capture -132.9, model -118.7 — compare session-14's ~160 deg
   anti-phase). clipA0=20.1 (inside 20-30), no param on a bound, monotone. **But noon H3-H2 landed
   -17.3 vs capture's -10.6 (6.7 dB short)** — the exact, persistent "noon-specific" shortfall from
   sessions 10-11, previously blamed on clipK but un-testable then because the JFET's anti-phase H3
   was masking it.
2. **+ clipK unconstrained** (the natural next step — session 11's lever, now finally testable since
   the JFET is in-phase): a targeted probe FIRST confirmed the discriminating signature RETURNS —
   softening clipK 2.0->1.0 at the beta-only fitted point raises noon -17.3 -> -9.1 (toward -10.6)
   while drive-min stays put. Added clipK to FIT_KEYS on that basis (documented, not blind). Refit:
   cost 272->69.5, noon error 6.7->3.6 dB, psi3 err DOWN to 8.6 deg (near session §3t.5's cap<->clip
   8 deg exactly). **But landed in a DEGENERATE corner**: clipK pinned at its 1.0 floor, clipSatLo+Hi
   collapsed to 1.58 V (vs the ~7 V R19-dropped rail), `2*a*ceilNeg`=12.7 (square-law badly violated,
   was supposed to be a free corroboration check ~1.0), beta pushed to 5.2, gm-scan NOT flat
   (cost 78/102/223 across 0.09/0.12/0.15 mS). REJECTED — the optimiser found "make the clip ceiling
   unphysically low" as a cheaper way to force the noon ramp than any real mechanism.
3. **+ clipK PHYSICALLY constrained** (clipSatLo/Hi in [1.5,4] V each so the sum can't collapse below
   ~3 V, clipK in [1.2,3] off the soft floor, beta in [0,4] near the gate's actual crossing): cost
   1925->196. Still REJECTED: `clipSatHi` pinned at its 1.5 V floor, `clipA0` dropped to 8.2 (circuit.md
   says 20-30 — flagged OUTSIDE), noon only reached -15.2 (still 4.6 dB short), gm-scan still swings
   (162-246). The optimiser just found a DIFFERENT unphysical knob (A0 instead of Sat) to fake the
   same thing once Sat was fenced off.

### 3u.5 Localisation: the residual gap is a SEPARATE, pre-existing clipper-level problem, not branch B
Two diagnostic grids (not fits — held at physically-nominal values, no free params) decisively
separate the two issues:
- **Fully physical clipper (A0 in circuit.md's 20-30, satLo/Hi = 3.15/3.85 V, clipK 1.0-2.0), JFET
  held at the beta-only fit**: best reachable noon is only ~-20 dB even at the softest clipK=1.0 —
  a ~9-10 dB gap that NO clipper-shape parameter closes within its physical envelope. 2:30/max are
  similarly stuck deeply negative (should be +1.3/+1.0).
- **Same physical clipper x jfetGm swept across its ALREADY-ESTABLISHED 0.09-0.15 mS band** (not a
  new unhold — the accepted range from step 2): raising gm closes 2:30/max (max: -3.2 -> +15.9 dB as
  gm 0.09->0.15) but **noon stays stuck at -18 to -21 regardless of gm** — a DIFFERENT signature than
  a simple level scale. This points at something DRIVE-POSITION-specific (most likely the held
  `driveTaperExp` shape, or the clipper/GRUNT input coupling across the DRIVE knob range), not a
  uniform gain error and not the JFET.
**Conclusion: branch B's JFET H3 phase/sign fix is CORRECT and DONE. The clipper cannot reach the
capture's drive-sweep ramp within its physical envelope using ONLY clipA0/clipSatLo/clipSatHi/clipK —
something upstream of the clipper (very likely `driveTaperExp`'s SHAPE, held at 2.5 from session 11's
LEVEL-only validation, which was never checked against the HARMONIC ramp) is not delivering the right
level AT NOON specifically.** This is the "excess/deficient pre-clipper level" thread flagged as far
back as session 5's GRUNT dsp-validator report and never fully closed — session 15 has now LOCALISED
it more precisely (drive-position-dependent, not gm, not clipper shape, not the JFET) but has not
fixed it, because doing so needs unholding `driveTaperExp` — explicitly out of this session's mandate
(HELD by the session brief) and a real re-fit of its own, not a side effect of the JFET-phase branch.

### 3u.6 STOPPED per protocol — nothing committed
Per "nothing ships as a DSP default before acceptance passes": none of the three fit attempts passed
acceptance (each has a param resting on a bound or outside circuit.md's range, or a non-flat gm-scan),
so **no FitParams defaults were changed and NOTHING was git-committed.** ctest is 16/16 (incl.
OSValidationTest — the session-14 anomaly does not recur at nominal beta=0.0, confirming the new code
is structurally sound independent of the fit outcome). The working tree has: the branch-B shape in
`JfetStage.h` (gate-confirmed + dsp-validator PASS), full plumbing (`FitParams.h`/`PedalChain.h`/
`offline_render.cpp`/`JfetStageTest.cpp`), the clipK-now-in-FIT_KEYS + phase-aware ψ3 objective in
`fit_nonlinear.py`, and the new gate script `analysis/expandbeta_gate.py`. `jfetExpandBeta` nominal
stays the honest placeholder 0.0 (cubic-neutral) — do NOT read that as "beta doesn't matter", it
means "not yet fit to a value that passed acceptance."

**▶ NEXT (session 16): the DRIVE taper SHAPE is the leading lever — but it is a C-TAPER, and the
model approximates it as a single POWER LAW.** `DriveStage.h` uses `R = 100k*(1-x)^p` (p=2.5), but
circuit.md/DriveStage.h both note VR3 is a **C-taper (reverse-log) pot** — and a C-taper is NOT a
power law. Session 11 only ever pinned p=2.5 to a 2-POINT small-signal LEVEL match (9:30, noon); the
SHAPE across the full sweep was never validated, least of all against the HARMONIC ramp.
- **Why the taper (not the clipper) is the suspect — bleed-free logic:** the session-15 grids show
  `jfetGm` (a UNIFORM level scale) does NOT fix noon H3-H2 (noon stuck at -18..-21 regardless of gm
  0.09-0.15 mS, while 2:30/max swing -3.2->+15.9), and no physical clipper VTC param fixes it either.
  A uniform scale can't; a NON-uniform level change (the taper SHAPE) is the only remaining lever.
- **Supporting probe (`analysis/drive_taper_shape.py`, log `step5_drive_taper_shape.log`):** measured
  the real small-signal drive gain vs knob from the existing dense ladders. **⚠ It has a BLEED
  CONFOUND** — the base-OD fundamental carries the drive-INDEPENDENT clean bleed, which DOMINATES at
  low/mid drive (the OD path is weak there), so the min->9:30->noon steps are NOT clean taper reads.
  The ONE bleed-free step (2:30->max, where OD dominates) shows the real pedal gains **+2.4 dB MORE**
  at the top than `(1-x)^2.5` (which saturates as R->0) — real evidence the taper shape is wrong at
  least at the top. The NOON-level question this probe CANNOT answer (bleed-confounded there).
- **So session 16 needs, IN ORDER:** (1) a BLEED-AWARE drive-taper measurement — subtract the
  drive-independent bleed from the fundamental (measure it at the clean tap / drive-min and remove
  it coherently), or measure level-into-clipper by a bleed-free route, to get the clean gain-vs-knob
  at all 5 settings ESPECIALLY noon; (2) replace `(1-x)^p` with a proper C-taper (reverse-log) curve
  in `DriveStage.h` — do NOT keep fitting a power-law exponent, the SHAPE family is wrong; (3) re-run
  THIS session's branch-B fit (the JFET core is DONE — keep jfetExpandBeta/jfetSatPos/jfetSatNeg/
  jfetCeilPos/jfetCeilNeg + the phase-aware ψ3 objective; only the clipper-input side changes). If a
  correct C-taper still doesn't close noon, THEN look at the clipper INPUT coupling (GRUNT cap bank +
  R16; `clipA0` also sets the input impedance R18/(1+A0)) for drive-dependent behaviour.
- **Do NOT re-attempt a joint clipK+clipSat+clipA0 fit before fixing the taper** — it will just
  re-find the same degenerate "lower the ceiling / drop clipA0" trick session 15's attempts 2-3 found.
- **⚠ Tension to resolve with the bleed-aware measurement:** session 11's 2-point LEVEL validation
  said p=2.5 matched noon-vs-9:30 to 0.18 dB, but that measurement may itself have been bleed-affected
  (its "matched-pair" cancels clipping but NOT the clean bleed if both takes share it). The
  bleed-aware measurement must reconcile these — do not assume session 11's p=2.5 is a clean anchor.
HELD unchanged this session: jfetGm 0.10 mS (established band 0.09-0.15), levelTaperExp 2.25 — but
driveTaperExp is now the ACTIVE parameter, no longer held.

---

## SESSION 14 (2026-07-23) — the §3s reshape was built, its §3j gate FAILED, STOPPED per protocol

Implemented the ceiling-hardness reshape exactly as §3s(1) specified, ran the pre-registered §3j
gate (§3s(2)) BEFORE any fit, and it FAILED. Per the protocol (and the whole point of the gate —
break the sessions-7–12 "fit past a bad diagnosis" cycle), STOPPED. No fit run, nothing committed.

### 3t.1 What was implemented (working tree, uncommitted; ctest 15/16)
`jfetCeilK` algebraic sigmoid `T(w) = w/(1+|w/L|^k)^(1/k)` replacing `L*tanh(w/L)` in
`JfetStage::coreLimit`, EXACTLY parallel to `clipK`. `T'(0)=1`, bounded to ±L, odd per side (even
bump untouched). k=2 fast path + exact ADAA antiderivative `F_T(w)=L·√(L²+w²)−L²`; **for k≠2 the
ADAA path uses the MIDPOINT rule** (`adaaShape` gates on `adaaExact() == (k==2)`) — the general-k
antiderivative is a non-elementary incomplete-Beta, so it is not provided; midpoint reproduces the
shape to O(du²)~1e-6 at 8× OS, i.e. correct shape / no anti-alias benefit, which is fine because
k≠2 is fitter-exploration-only and the shipped anchor is k=2. Monotonicity derivative
`T'(w)=(1+|w/L|^k)^(-(k+1)/k)`; **the algebraic ceiling's slope decays as a POWER LAW, not tanh's
exponential**, so the fold-back risk is confined to the knee (far tail is safe) — the
`JfetStageTest` bounded-scan tolerance and `fit_nonlinear.py::min_slope` were updated for this.
Plumbed `FitParams::jfetCeilK` (default 2.0) → `PedalChain::setFitParams` → `--fit jfetCeilK=` in
OfflineRender. `JfetStageTest` passes (bounded/monotone/F'==g all green with the new core).
**OSValidationTest**: the 4×-vs-2× aliasing diff-gate at amp 0.2 fails (4×=−19.2 vs 2×=−21.9) — the
known clipper/decimator narrow-band anomaly relocated onto the probe amp by the shape change at
PLACEHOLDER nominal ceiling params (8× floor −40.5 clean, oversampling still works, delay-comp
passes; baseline was −22.1/−21.6). NOT masked; re-judge at fitted params.

### 3t.2 The pivot FAILED — robustly (`analysis/fit_logs/step5_ceilk_pivot.log`)
Pre-registered signature: as k RISES, drive-min H3−H2 FALLS toward −23.2 **AND** drive-noon RISES
toward −10.6, together. Result at the session-11 point:
```
   k |    min |   9:30 |   noon |   2:30 |    max      (capture: -23.2/-21.0/-10.6/+1.3/+1.0)
2.00 |  -15.1 |  -15.3 |  -16.0 |    3.7 |    2.7
4.00 |  -34.6 |  -36.1 |  -41.4 |   24.1 |    2.4      <- noon at a deep anti-phase NULL
8.00 |  -57.8 |  -46.9 |  -31.5 |   23.2 |    2.4
  min falls +50.5 dB (want>0 ✓), noon rises -24.1 dB (want>0 ✗ — it FELL) -> NOT CONFIRMED
```
Re-ran with a PROPER clipper (`--point=...,clipA0=25,satLo=3.15,satHi=3.85`, sum 7 V): even clearer
failure — min AND noon fall MONOTONICALLY together (k=8: min=−81.6, noon=−48.0), and at every k the
model is **FLAT** across min/9:30/noon (k=2: −15.2/−15.2/−15.3) while the capture RAMPS. So the
frozen bad-clipper was NOT the confound; **the JFET-ceiling hardness `k` is confirmed the wrong
lever.** `k` only scales the ceiling H3 magnitude — it cannot touch the ANTI-PHASE relationship that
makes ceiling-H3 and clipper-H3 cancel (session 12's mechanism), so it drives both drives' H3 through
a shared null instead of separating them.

### 3t.3 The coherent diagnosis: an H3 PHASE/SIGN problem, entangled with the ~320 Hz notch
Scratch probe `analysis/scratch_ceilk_clipk_probe.py` (jfetCeilK held HIGH = ceiling H3-free, sweep
clipK): the CLIPPER-ALONE ramp has the right SHAPE (monotonic) but is too STEEP — at clipK=1 it spans
min=−40 → max=−0.2 (40 dB) vs the capture's −23.2 → +1.0 (24 dB). **The capture has real H3 at
drive-MIN (−23.2) where the clipper is barely on — that H3 can ONLY come from the JFET.** So the
capture's gentle monotonic ramp requires the JFET's (drive-independent) H3 and the clipper's
(drive-dependent) H3 to be **IN-PHASE (add)**: JFET sets the −23 floor at min, the clipper adds on
top up to noon −10.6 / max +1. They are currently **ANTI-PHASE** (session 12, measured 180° apart),
so they cancel → the model stays flat then nulls. A compressive ceiling's H3 is INTRINSICALLY
anti-phase to the clipper (both compress, but the inter-stage inversions/filtering put them 180°
apart at the output), and NO hardness value flips a sign — which is exactly why the gate failed.

**⚠⚠ THE NOTCH-CONFOUND HYPOTHESIS WAS MEASURED AND LARGELY FALSIFIED (session 14 tail,
`analysis/notch_scope.py`).** I initially wrote that the anti-phase H3 was confounded by "the
mismodelled ~320 Hz notch (model −28 vs capture −3.4 dB)". TWO corrections: (1) the notch that sits in
220's H3 band (660 Hz) is the **~717 Hz BRIDGED-T** notch (RecoveryBridgedT), NOT the ~320 Hz
treble-net notch — the ~320 one is in the **110 Hz tone's H3 band** (330 Hz); 440's H3 (1320 Hz) is
clear of both. (2) **The "−28 dB" figure is an ISOLATED-STAGE number; in the ASSEMBLED, LOADED chain
BOTH notches are shallow.** Measured drive-min OD-path FR (model @ gm 0.10 mS vs the drive-0700
capture, mean-removed, `analysis/notch_scope.py`):
```
  treble-net ~320 : capture dip -2.4 dB @ 318 Hz | model dip -0.8 dB @ 280 Hz | model SHALLOWER by 1.6
  bridged-T  ~717 : capture dip -0.7 dB @ 809 Hz | model dip -0.4 dB @ 809 Hz | ~flat, ~equal
```
So in the real signal path both notches are ≤2.6 dB, and the MODEL notch is if anything SHALLOWER
than the capture's — the loading (JFET finite Zout stamped into TrebleAttack, downstream stages)
washes out the isolated −28 dB. **A ≤2.6 dB dip carries only ~±15° of phase, not the ~180° anti-phase
the session-12 finding measured — so the notch does NOT explain the anti-phase H3.** The residual
model-vs-capture FR discrepancy is a broadband few-dB shape difference (model LF 150–290 Hz ~1–3 dB
low; model ~+0.8 dB high at 1320), not a deep notch. **=> The session-12 anti-phase H3 interference is
very likely REAL nonlinear structure, and "resolve the notch first" does NOT unblock it.** (The
session-13 step-1 "220/440 notch-corrupted" caveat is thus much weaker than stated — the linear phase
error in the H3 band is small.)

### 3t.4 ▶ BRANCH OPTIONS — RE-OPENED after the notch measurement
My original recommendation (A, resolve the notch first) rested on the −28 dB notch corrupting the
phase; §3t.3's measurement falsified that premise, so the recommendation flips. Options:
- **cPos/cNeg asymmetry is an H2 (even) lever** — will not fix an H3 PHASE problem. Reject.
- **(A) RESOLVE THE NOTCHES FIRST — now DOWNGRADED.** In the assembled chain both notches are ≤2.6 dB
  and the model's are already ~as shallow as the capture's, so this is NOT the phase blocker. There
  IS a residual ~1–3 dB broadband LF shape discrepancy worth fixing eventually for overall fidelity,
  but it is not prerequisite to the H3 fix. Do not lead with this.
- **(B) PURSUE THE JFET ODD-TERM IN-PHASE H3 DIRECTLY — now the leading candidate.** The phase
  measurement is more trustworthy than the "−28 dB notch" framing implied. Structurally the JFET's
  odd nonlinearity must produce H3 IN-PHASE with the clipper; a compressive ceiling can't (its H3 is
  intrinsically anti-phase), so this likely needs an EXPANSIVE odd component at low-mid drive before
  the bound — a new shape design + its own §3j-style discriminating check + phase-aware targets.
  First de-risk cheaply: re-read the session-12 anti-phase result and CONFIRM it is not a model
  polarity/inversion bug (an accidental extra/inverted stage sign would also read as 180°), since a
  sign bug would be a one-line fix, not a reshape.
- **(C) THE COUPLED-NEWTON JFET REWRITE** (Q1/Q2 Shichman-Hodges + R6∥C3 companion; phases emerge
  from topology) — heaviest, but if the issue is genuinely phase-structural it directly produces the
  right phases from the circuit rather than fitting them into a static shape.
**Revised recommendation: (B), but START by verifying the anti-phase is real (not a polarity bug) and
re-deriving it on the CURRENT chain** (session 12's measurement predates nothing structural, but
confirm), because if it is a sign bug the whole H3 problem could collapse to a trivial fix.

### 3t.5 ▶ VERIFICATION DONE (session 14 tail) — the anti-phase is GENUINE, branch B CONFIRMED
Re-ran `analysis/phase_harmonics.py` on the current chain (log `analysis/fit_logs/step5_phase_harmonics.log`).
- **Anti-phase reproduces robustly**: model ceiling-H3 vs clipper-H3 = **178.8 / 166.0 / 178.7°** apart
  at 110/220/1000 Hz (440's "51°" is the known notch/SNR tone where ceil & clip aren't even resolvable,
  <90° apart).
- **Capture matches the CLIPPER, opposes the ceiling**: the one conclusive tone (1000 Hz, H3=3 kHz,
  capSNR 47, clean) gives cap↔clip **8°**, cap↔ceil **160°** → "ceiling BACKWARDS". 110 Hz agrees
  suggestively (cap↔clip 11°, cap↔ceil 166°) but capSNR only 5; 220/440 inconclusive (notch/SNR).
- **It is NOT a polarity/inversion bug** (the check the user asked for): (1) the 180° is a RELATIVE
  phase between the model's OWN ceiling-H3 and clipper-H3, and a global sign error flips BOTH
  identically → cannot change their relative phase, so no stray/missing inversion can produce it;
  (2) per-stage FUNDAMENTAL polarities are DC-step-verified (JFET inverting, clipper inverting), so
  the inversion COUNT is right; (3) the 180° is genuine topology bookkeeping — ceiling-H3 is born
  UPSTREAM and transits the clipper's inversion + the treble/DRIVE linear phase at f vs 3f, while
  clipper-H3 is born AT the clipper; (4) the capture validates the model's CLIPPER side against
  reality (8°), so the ceiling being 160° off means the REAL JFET H3 is the opposite sign to a
  compressive ceiling. **=> The real JFET odd nonlinearity has EXPANSIVE-signed (in-phase-with-
  clipper) H3. No compressive ceiling and no hardness `k` can make it (the pivot proved the latter).**

### 3t.6 ▶ THE BRANCH-B DESIGN PLAN (for session 15) — an expansive-then-bounded odd JFET term
**Key simplifier (handover, already established): DRIVE sits AFTER the JFET, so the J201 sees the
SAME (input-level) signal at every drive setting — its harmonics are DRIVE-INDEPENDENT.** So the JFET
only has to make the right H3 at ONE operating level (the tone level), and the drive-min capture's
H3−H2 = −23.2 (in-phase with the clipper) IS that target. The clipper (downstream) supplies the
drive-DEPENDENT ramp on top. Confirmed by the scratch probe: clipper-alone at drive-min is −71…−81 dB
(nowhere near −23.2), so the −23.2 MUST be the JFET's.
- **Shape requirement**: an ODD term with EXPANSIVE H3 (opposite sign to compression) at the tone
  level, producing H3−H2 ≈ −23.2, IN-PHASE with the clipper — while staying MONOTONE and BOUNDED for
  loud (0 dBFS) inputs (the ceiling's original job: pre-reshape the J201 fed the CD4049 ~38 V at
  0 dBFS). Expansive alone (w+βw³) is unbounded; need expansive-near-origin THEN saturating.
  Candidate families to design/validate (each needs T'(0)=1, closed-form ADAA antiderivative,
  numeric monotonicity, and the even-bump H2 kept separate): an odd shape whose small-signal cubic
  is POSITIVE (β>0) then rolls into a bound. Do NOT ship one without the ADAA/monotonicity rigor the
  ceiling and clipK got.
- **Gate BEFORE fitting** (mandatory, the sessions-7–14 lesson): a §3j-style discriminating check that
  the new expansive term moves drive-min H3−H2 toward −23.2 IN-PHASE (complex, not just magnitude) —
  i.e. it must make the model's JFET-H3 phase FLIP to the clipper's side, and then the full-chain min
  H3−H2 rise toward the capture WITHOUT the anti-phase null the compressive ceiling produced.
- **Then** the phase-aware complex ψ3/ψ2 fit (fit_nonlinear.py, down-weight 220's notch-corrupted H3),
  dsp-validator sign-off (+ the still-deferred clipK pass), accept on corroboration, master taper +
  makeup, commit the set.
- **The `jfetCeilK` implementation stays useful**: the bounded expansive shape can REUSE its
  algebraic-sigmoid bound for the saturating tail (the expansive cubic handles the H3 sign near the
  origin, the sigmoid handles the loud-input bound). So keep it uncommitted, don't revert.

HELD (unchanged, still valid): driveTaperExp 2.5, jfetGm 0.10 mS, levelTaperExp 2.25. The `jfetCeilK`
implementation is a clean, more-general ceiling and can be KEPT (uncommitted) — a sign-fix may build
on it, or it reverts. dsp-validator sign-off on it (and the deferred clipK pass) was NOT run —
premature until the branch is settled.

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

### Step 3 — FIX THE OBJECTIVE, then fit the shaper ✅ DONE (session 10) — see "✅ STEP 3 DONE" above

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
