#pragma once

// =============================================================================
// FitParams — every Phase-7 CAPTURE-FIT constant, in one place
// =============================================================================
// The circuit's schematic-verified R/C values are NOT here — those are fixed
// facts (circuit.md is their source of truth) and stay `static constexpr` in
// their stages. What lives here is the much smaller set of constants that the
// build deliberately left NOMINAL because they cannot be read off a schematic:
// device-spread amplitude params (J201 ~5:1 part spread), the CD4049's finite
// open-loop gain and R19-dropped rail, pot taper SHAPES, the tolerance-sensitive
// bridged-T, and the op-amp rail ceilings. Each was flagged in-code as a
// "Phase-7 capture carry-forward"; this struct is where they all converge.
//
// **Why runtime instead of constexpr.** Every field below started life as a
// `static constexpr` in its stage. Fitting them that way costs a full rebuild
// per candidate value, which is fine for a one-line sanity tweak and hopeless
// for an actual fit: kA0 x kSatLo x kSatHi alone is a 3-D search, and the doc's
// extraction plan (nonlinear-component-modeling.md §4) asks for several such
// fits cross-checked against multiple captures. Making them settable lets
// OfflineRender sweep hundreds of candidates per minute from Python.
//
// **These defaults are now the SHIPPED session-17 calibration, NOT the stage
// nominals.** Through session 16 the defaults here mirrored each stage's
// `static constexpr kXxx` so a default-constructed FitParams reproduced the
// pre-fit build exactly. Session 17 froze the full-chain fit and wrote it here:
// every field above whose comment says "session-17 fit" is now the measured
// value, and PluginProcessor applies a default-constructed FitParams in
// prepareToPlay (it did not before — the plugin used to silently ignore this
// struct), so THIS file is the single source the shipped plugin AND OfflineRender
// both start from. The stage `kXxx` constexprs are retained UNCHANGED as the
// documented pre-fit nominal and as the per-stage tests' oracle (those tests
// construct stages directly, without a FitParams, so they still test the nominal
// path). To re-baseline OfflineRender to nominal, pass the `kXxx` values via --fit.
//
// **Scope boundary.** These are all CHAIN-domain (real volts, inside
// PedalChain). The two DAW-domain scalars — `kInputRef` (volts per full scale)
// and `kOutputMakeup` — are processor-domain and deliberately NOT here; they
// live in PluginProcessor and are set on OfflineRender's command line
// separately. Keeping the two domains apart is the calibration doc's §1 rule
// (kInputRef must cancel in the linear path); folding them into the chain would
// blur exactly the boundary that rule depends on.
// =============================================================================
struct FitParams
{
    // ---- CD4049UBE clipper (Clipper.h) --------------------------------------
    // clipA0 is the PRIMARY fit param: it sets BOTH the closed-loop gain AND the
    // three GRUNT corner frequencies (the input-node impedance is R18/(1+A0)), so
    // it is constrained by two independent measurements at once — fit it against
    // the GRUNT voicing and the drive-sweep level together, not either alone.
    // clipSatLo/clipSatHi are the per-side VTC ceilings; their SUM is the
    // R19-dropped effective rail (nominal ~7 V, below the 8.6 V op-amp rail) and
    // their DIFFERENCE is the even-harmonic asymmetry. Fit to the drive-sweep
    // Farina THD(f) + low-frequency-tone H2/H3 balance.
    double clipA0 = 26.142;      // session-17 fenced fit (was nominal 25)
    double clipSatLo = 2.0067;   // session-17 fenced fit (was nominal 3.15)
    double clipSatHi = 2.9321;   // session-17 fenced fit (was nominal 3.85)
    // clipK = the VTC knee HARDNESS (session-11 reshape 2026-07-23, Clipper.h
    // vtc()): the per-side sigmoid is u/(1+u^k)^(1/k). A single tanh could not
    // decouple knee hardness from the small-signal gain a0 — the step-3/4 fits
    // pinned clipA0 on its ceiling and still fell ~8 dB short of the capture's
    // H3-H2 at DRIVE-noon (handover §3h-3j). tanh behaved like k~=2.5-3; the
    // capture wants softer. k = 2 is the shipped anchor (elementary ADAA
    // antiderivative sqrt(1+u^2); k=1 also closed-form) — do NOT commit an
    // arbitrary fitted k as the default without checking its antiderivative
    // stays closed-form (same trap class as the JfetStage sech->tanh reshape).
    // ** Session 17 ships the fitted k = 2.846, a NON-anchor value. Safe here
    // because the clipper carries NO ADAA (its VTC lives inside the implicit
    // RC-coupled Newton solve — memoryless-ADAA does not apply; oversampling
    // does the antialiasing), so the closed-form antiderivative is never used.
    // The k != 2 forward path (Clipper.h vtc()/vtcDeriv()) is a plain pow(), exact
    // for any k; only the k==2 sqrt fast-path is skipped (a little more CPU/sample). **
    double clipK = 2.8462;       // session-17 fenced fit (was anchor 2.0 — see closed-form note below)
    // clipC11 = the ALWAYS-PRESENT GRUNT coupling cap (schematic 4n7, Clipper.h
    // kC11). Made fittable in session 17 (user-authorised 2026-07-24: "ATTACK and
    // GRUNT are somewhat estimated; I trust the captures more than the schematics").
    // It sets the GRUNT=Cut high-pass corner 1/(2*pi*C11*(R16 + R18/(1+A0))) that
    // gates how much bass reaches the clipper. The re-diagnosis (handover §3v.4) is
    // that the model is STRUCTURALLY flat across drive-min..noon at Cut (+1.1 dB)
    // while the capture ramps +12.6 dB — the signature of the Cut corner being too
    // HIGH (bass strangled -> clipper never turns on with DRIVE). C11 is the ISOLATED
    // lever for it: bigger C11 lowers ONLY the Cut corner (Boost/Flat corners are
    // already sub-band), whereas R16 would also cut the clipper gain and A0 is ruled
    // out (analysis/clipa0_grunt_corner_probe.py: the gain drop cancels the corner
    // shift). Fit it JOINTLY with the K/clipSat/clipA0 family; a pin at its bound is
    // diagnostic (the corner wants a value no 4n7-labelled cap explains -> look past
    // C11). Only the Cut position depends on it alone; Boost = C11||220n is ~immune.
    double clipC11 = 5.7207e-9;  // session-17 fenced fit (schematic 4.7 nF; user-authorised to move)
    // clipC12/clipC13 = the SWITCHED GRUNT caps (schematic 47 nF / 220 nF, added in
    // Flat / Boost respectively). Only Flat depends on C12, only Boost on C13; Cut is
    // C11 alone (unaffected). Made fittable in session 19 to chase the GRUNT sub-bass
    // excess; **session 23 (2026-07-25) CLOSED that line — they are the WRONG LEVER
    // and both stay at their schematic values. DO NOT FIT THEM.** The mechanism is
    // upstream: the OD path carries ~13-15 dB too much 40-50 Hz relative to the clean
    // blend, which C12/C13 can only mask by subtracting bass downstream of it.
    // Four independent strands (docs/phase9-validation.md §4 "3b CLOSED"):
    //   1. The excess is FULLY present at GRUNT **Cut** — C12 and C13 out of circuit
    //      entirely — at +12.8 dB (40 Hz) / +14.8 dB (50 Hz) vs the pedal.
    //   2. The plugin-vs-pedal LF error tracks the BLEND knob, not GRUNT: -0.47 dB at
    //      pure clean -> +9.51 dB at full OD, monotone; the clean path matches to 0.32 dB.
    //   3. A 1-D scan of clipC13 is MONOTONE with no interior minimum down to 0.5 nF
    //      (grunt-boost band-RMS 11.25 -> 5.09): the best "fit" is to delete the boost
    //      cap. Same "make the clipper see less" degeneracy that killed the session-5/6
    //      clipper fits and the rail-voltage fit — a degenerate objective, not a value.
    //   4. At 22n the model's boost-minus-flat span INVERTS (-3.8 dB at 100 Hz vs the
    //      pedal's consistent +5.6..+6.1 dB), destroying the switch's differentiation —
    //      the exact failure mode that got GAP #4's joint mid-cap fit rejected.
    // C13's provenance is also settled: circuit.md's re-zoom trigger was executed and
    // the primary p.4 symbol + BOM both read 220n unambiguously (though they are ONE CAD
    // source, not two independent ones — and neither schematic describes the Ultra we
    // captured; see circuit.md "GRUNT cap C13"). The backup's 22n is a genuine 2021
    // revision difference. Left fittable ONLY so a future probe can sweep them
    // diagnostically — a shipped value other than the schematic's needs the A3 gap
    // (the OD/clean LF balance) closed first, or it is just re-fitting this degeneracy.
    double clipC12 = 47.0e-9;    // GRUNT Flat  add-cap (schematic 47 nF — do NOT fit, see above)
    double clipC13 = 220.0e-9;   // GRUNT Boost add-cap (schematic 220 nF — do NOT fit, see above)

    // ---- J201 JFET stage (JfetStage.h) --------------------------------------
    // The ~5:1 J201 part spread means nominal SPICE cannot match a specific unit;
    // all of these are capture-fit by definition (nonlinear doc §2/§4). Fit to
    // the drive-MIN OD captures, where the CD4049 downstream contributes least.
    //
    // ** RESTRUCTURED 2026-07-22.** `jfetG0` (a lumped voltage gain that absorbed
    // the gate divider, the active-load impedance AND the R7 treble-net loading)
    // and `jfetGmR6` are both GONE. The stage is now a transconductance whose
    // output impedance is stamped into TrebleAttack, so:
    //   * jfetGm  replaces jfetG0 — the actual device gm. It also SETS the
    //     degeneration factor via gm*R6 (R6 is a fixed 3k3), which is why the old
    //     separate jfetGmR6 was redundant and is removed rather than renamed.
    //   * jfetRo / jfetRq2 are the loading that used to be folded into jfetG0.
    //     Together with gm they decide how much of the C3 shelf survives into the
    //     treble net — the single biggest lever on the OD path's HF balance.
    // Removing (not renaming) the old fields is deliberate: a stale
    // `--fit jfetG0=...` now fails loudly in OfflineRender instead of silently
    // setting something with different physical meaning.
    double jfetGm = 0.10e-3;   // S   session-4 anchor / session-17 HELD (was nominal 0.69e-3; gm*R6 = 0.33)
    double jfetRo = 200.0e3;   // ohm  Q1 drain output resistance (1/gos)
    double jfetRq2 = 1.0e6;    // ohm  Q2 C4-bootstrapped active-load impedance
    // jfetSatPos/Neg feed JfetStage's SQUARE-LAW even-shaper (JfetStage.h, Phase-7
    // reshape 2026-07-22), NOT the old tanh sat levels: jfetSatPos = knee `s` (volts),
    // jfetSatNeg = even-harmonic strength `a` (SIGNED). Names kept to avoid a rename
    // churn across PedalChain/OfflineRender/fit_nonlinear.py; semantics documented here
    // and at JfetStage::waveshape(). A clean rename is deferred polish.
    // ** The SCALE of `s` changed with the 2026-07-22 restructure: the shaper now sees
    // the effective vgs (real gate volts, order |Vp|), not a post-gain voltage. Any
    // s/a fitted before that date is meaningless — refit. **
    // ** The even bump's SHAPE also changed when the ceiling landed (same date):
    // a*s^2*(1-sech(w/s)) -> (a*s^2/2)*tanh^2(w/s), so its tail matches the ceiling's
    // and monotonicity has an interior (JfetStage.h waveshape()). `a` keeps its meaning
    // (the square-law quadratic, a = 1/Vov); its asymptote halved, and the ceiling-off
    // product bound moved from |a|*s < 2 to |a|*s < 2.598 — a DIFFERENT extremum of a
    // DIFFERENT function, not a revert of the 2026-07-22 bug fix. With a finite ceiling
    // NEITHER closed form is sufficient: the constraint couples s, a and jfetCeilNeg, so
    // a fitter must scan the slope NUMERICALLY (fit_nonlinear.py does). **
    double jfetSatPos = 0.20072; // s: square-law knee (gate volts) — session-17 fit (was 0.3)
    double jfetSatNeg = 3.1769;  // a: even strength (signed) — session-17 fit (was 1.0)
    // ---- Asymmetric drain-current CEILING (added 2026-07-22) ----------------
    // The step-2 re-fit REJECTED its own result and diagnosed why: the capture's
    // H2 grows +6 dB across the drive sweep and the unbounded model's grew
    // +21.9 dB, so the fitter pinned |a|*s to the 2.0 monotonicity gate trying to
    // manufacture a ceiling out of a shape that has none, and pushed clipA0 to its
    // floor to weaken everything downstream (phase7-calibration-handover.md,
    // "STEP 2 RE-FIT"). These two give the J201 its own explicit limit.
    // Units: gate-volt equivalent — multiply by jfetGm for AMPS. Deliberately NOT
    // in amps: the cutoff headroom is Idq/gm = Vov/2, a pinch-off-voltage property
    // that should NOT move when the fitter moves gm.
    //   jfetCeilNeg = the negative-swing (drain rising) side. Q1 CUTOFF puts a hard
    //     device floor there at Idq/gm = Vov/2, and the same Vov sets the even
    //     strength (a = 1/Vov), so IF cutoff is what binds, 2*jfetCeilNeg*jfetSatNeg
    //     = 1 — the nominal 0.5 is exactly that identity at the nominal a = 1.
    //     ** Treat that as a WEAK check, not a requirement. ** Q2's own compliance
    //     limits the same swing at ~3 V/(gm*Zload) = 0.15 V at LF at nominal gm,
    //     i.e. TIGHTER than cutoff, so the identity only holds in the low-gm regime
    //     where cutoff wins. A fit that misses it is not automatically suspect; a
    //     fit that hits it is corroborated. (It also assumes a = 1/Vov, which is
    //     only the small-signal reading of `a` — see JfetStage.h waveshape().)
    //   jfetCeilPos = LOAD-LINE side (drain swinging down), circuit-set and
    //     band-dependent (~0.2 V at LF, ~0.9 V at 2 kHz into the node-G load at
    //     NOMINAL gm, and ~7.7x looser again at the gm the drive-min shape fit
    //     prefers) — a single memoryless number lumps that on purpose. Nominal
    //     1.0 V. Which side BINDS depends on gm and so is still open: at nominal gm
    //     the estimate above makes jfetCeilPos (0.2 V at LF) the tighter of the two;
    //     only under the low-gm hypothesis does the cutoff side bind.
    // The asymmetry between them is a SECOND source of even harmonics alongside
    // jfetSatNeg, and reinforces it in the same direction; expect the fit to trade
    // the two off. Passing >= 1e6 disables a side exactly (pre-ceiling model).
    double jfetCeilPos = 2.3428;   // session-17 fit (was nominal 1.0)
    double jfetCeilNeg = 0.27408;  // session-17 fit (was nominal 0.5)
    // jfetExpandBeta = the EXPANSIVE cubic coefficient of the core shape (session-15
    // branch B, 2026-07-23, JfetStage.h coreLimit()). SUPERSEDES the session-13/14
    // `jfetCeilK` hardness knob, which was proven the wrong lever (its pivot gate
    // failed: a COMPRESSIVE ceiling's H3 is intrinsically ~180 deg from the
    // clipper's, and no knee hardness flips that sign — handover §3t.2). The core
    // is now the expansive-then-bounded rational map
    //   T(w) = w*(1+c*w^2)/(1+(w/L)^2)^(3/2),  c = beta + 1.5/L^2
    // whose small-signal series is EXACTLY w + beta*w^3 + O(w^5). beta is thus the
    // cubic coefficient DIRECTLY: beta > 0 gives EXPANSIVE H3 (in-phase with the
    // clipper), which the phase-aware measurement (§3t.5) showed the real JFET has;
    // beta = 0 is cubic-neutral; beta < 0 recovers a compressive shape (the old
    // ceiling's regime, kept only as an A/B). Shared by both sides (asymmetry is an
    // H2 lever on jfetCeilPos/Neg, not an H3 one). The antiderivative is elementary
    // for ANY beta, L (unlike jfetCeilK's k != 2 case), so the closed-form 1st-order
    // ADAA is preserved unconditionally. Provably monotone for beta >= 0 (see
    // JfetStage.h), which is the only regime this branch uses; still scanned
    // numerically in fit_nonlinear.py + JfetStageTest per the standing bound-verify
    // rule. Nominal 0.0 is a PLACEHOLDER — this is the session-15 primary fit target.
    double jfetExpandBeta = 2.1354;  // session-17 fit — EXPANSIVE cubic (was placeholder 0.0)

    // ---- Pot taper shapes (power-law exponent p, R = Rmax * x^p) ------------
    // dsp.md §tapers: fit the SHAPE, don't assume convex, and constrain p with at
    // least TWO knob points across the range (a wrong shape can match one
    // position and flip sign at another). The capture matrix provides 4 points
    // per pot for exactly this.
    double driveTaperExp = 1.98;  // VR3 100k C-taper, in (1-x) — 0 ohm at full CW. session-17
                                  // measured (bleed-free taper, drive_taper_curve.log; was 1.5/2.5)
    double levelTaperExp = 2.25;  // VR2 100k A-taper — session-8 measured (36 estimates; was 1.43)
    double masterTaperExp = 2.25; // VR8 100k A-taper [ENG] — session-17; same pot as LEVEL, so
                                  // shares its 2.25 (master captures bracket it: 2.06/2.37; was 1.43)

    // ---- C21 (100n) inter-stage coupling into the tone stack ----------------
    // The 100n cap is schematic-verified; the resistance it works against is the
    // tone stack's effective INPUT impedance, which is a nominal ~10k estimate,
    // not a single schematic part. It sets a ~159 Hz highpass that audibly shapes
    // bass, so it is a real fit knob (fit alongside the tone stack).
    double c21R = 220.0e3;  // session-28 A2d (was 100k, session-18; nominal 10k). Corner ~7.2 Hz.
                            //
                            // Session 18 moved 10k -> 100k (159 -> 15.9 Hz) and closed most of a
                            // 6-15 dB bass deficit. Session 28 found the REST of it: over the 30
                            // clean captures the plugin was still uniformly bass-light below
                            // ~63 Hz — bypass-corrected flat-EQ residual -1.31 dB @20 Hz, -0.75
                            // @31.7, -0.38 @40, 0.00 @63.5. It is NOT the measurement chain:
                            // bypass.wav round-trips at -0.03 dB across every one of those bands.
                            // It is in the SHARED post-BLEND path (identical in all 30 captures),
                            // and C21 is the only audible-band highpass there — everything else in
                            // the clean path corners at <=1.6 Hz.
                            //
                            // NOT the "delete the element" degeneracy that killed the session-5/6
                            // clipper fits and the GAP #3b C13 candidate: the 8-capture clean scan
                            // has an INTERIOR minimum with pushback on both sides, on all three
                            // metrics (<=63 Hz RMS: 100k 0.849 / 150k 0.421 / 180k 0.319 /
                            // 220k 0.261 / 270k 0.248 / 330k 0.260 / 470k 0.287; 20 Hz-10 kHz mean
                            // minimises AT 220k, 0.471 -> 0.283). 220k lands 20 Hz dead on
                            // (-1.28 -> -0.02 dB) and is within 0.001 dB of optimum on the agreed
                            // 30 Hz-10 kHz band, where the curve is nearly flat from 150k-270k.
                            //
                            // ⚠ TWO CAVEATS, do not read this as "found the real circuit".
                            // (a) The implied corner is not perfectly constant across the LF bands
                            // (7-10 Hz over 20-40 Hz), so this is a corner APPROXIMATION; a purely
                            // first-order mismatch would give one number. The residual +0.20 dB
                            // low-mid tilt (see docs/phase9-validation.md A2d) contaminates the
                            // solve above ~50 Hz. (b) 220k is 22x the nominal stack input Z, so
                            // the physical story for C21 is thin — same posture as 10k -> 100k, and
                            // the same third branch as R36/C13/the [ENG] mid caps: our schematic is
                            // a clone of the ORIGINAL B7K, the captured unit is an Ultra. This is a
                            // behavioural match to the unit we recorded. C21's schematic
                            // value/placement is STILL worth a schematic-checker pass; the capture
                            // is authoritative on the corner (dsp.md fit-the-corner).
                            //
                            // ⚠ ONE CAPTURE REGRESSES, monotonically with c21R: bass-0930 (BASS
                            // cut) 0.424 -> 0.554 dB band-RMS. It is already +1.0 dB relative at
                            // 40 Hz before this change — the Baxandall bass CUT is ~1 dB too
                            // shallow there, a separate and smaller gap. Do not fix it with c21R.

    // ---- Bridged-T recovery network (RecoveryBridgedT.h) -------------------
    // Risk register #1. The ideal-value response is a ~-28 dB notch at ~717 Hz,
    // which is surprisingly deep for this pedal, and the depth is highly
    // tolerance-sensitive — so all four values are fit parameters rather than
    // fixed, to be reshaped to whatever the capture actually shows (including
    // "much shallower than ideal"). The NOTCH FREQUENCY is far more trustworthy
    // than its depth; weight the fit accordingly.
    // ---- Treble-ladder notch damping (TrebleAttack.h) -----------------------
    // The R7-vs-(C5/C9/C6) two-path cancellation notch at ~322 Hz is ~28 dB deep
    // in the ideal model but only -3.4 dB in the capture, and tolerance cannot
    // explain the gap (circuit.md risk #1; Monte Carlo never got shallower than
    // -23 dB). The over-deep notch scoops the OD low-mids (100-500 Hz), which is
    // the session-19 root cause of the "backwards GRUNT" + the 254 Hz BLEND null.
    // trebleLadderDampR = a series loss on the C5 ladder cap (real ESR / PCB /
    // unmodelled damping R) that shallows the cancellation. 0 = ideal deep notch;
    // fit to the capture's -3.4 dB DEPTH (dsp.md "fit the corner/depth to capture";
    // the notch FREQUENCY moves little with it). See analysis/od_taps_probe.cpp.
    double trebleLadderDampR = 30.0e3;  // ohms; session-19 Phase-9 A/B fit (was implicit 0).
                            // Fit on the clean OD captures (notch region 127-640 Hz):
                            // low-mid RMS 3.64 -> 1.96 dB across 6 flat-EQ OD captures, HF
                            // (1-6 kHz) cost only +0.11 dB (the knee; 40k trades +0.12 HF for
                            // -0.09 more low-mid). Shallows the 322 Hz notch from ~28 dB to a
                            // capture-like depth. ⚠ 30k is LARGE for literal cap ESR — the
                            // physical origin (why the ideal notch is far too deep; tolerance
                            // ruled out) is a schematic-checker follow-up, but dsp.md makes the
                            // capture authoritative on the notch depth (like c21R's 10x corner).

    // ---- C7, the coupling cap into IC2_A (TrebleAttack.h::setC7) ------------
    // Phase 9 / A3 step 3a (session 34, SHIPPED session 35). At the schematic 100n
    // this cap corners at ~1.2 Hz (R_src+R_load ~= 1.28M) and is inert everywhere in band,
    // which leaves the OD path's response into IC2_A peaking at 32-40 Hz and
    // falling 12 dB by 320 Hz. IC2_A then rails at LF first, so at 40-101 Hz the
    // model's |OD| turns over at drive 2:30 and FALLS by max where the pedal's
    // grows +5..6 dB (analysis/a3_drive_axis.py — the A3 step-3a gate).
    // 680p puts a 1st-order HP at ~183 Hz ahead of IC2_A and restores that headroom.
    //
    // WHAT THE GATE ACTUALLY SAYS (read this, not "the drive axis is fixed"):
    //   G1 monotone |OD| in drive at 40-101 Hz: FAIL at 5/5 bands -> PASS.
    //   G2 the 2:30->max step: 50 Hz model -2.33 -> +7.30 against a pedal
    //      +5.56..+6.31, i.e. 7.89 dB SHORT -> 1.75 dB OVER; 64 Hz 6.82 short ->
    //      0.98 over. So G2 still fails CONTAINMENT, in the opposite direction.
    // The value was selected on the step-profile RMS over 50-254 Hz (4.72 -> 0.647
    // dB), with an interior minimum verified both sides (4.62 at 220p) — NOT the
    // "make the clipper see less" degeneracy. The residual overshoot is what the
    // step-3b lead network is fitted against, jointly with beta.
    //
    // ⚠ 680p against a schematic-AND-BOM-verified 100n is a factor of 147 — by far
    // the weakest physical story of any fit in this file (trebleWiperR is 1.4x,
    // c21R 10x). Same third branch as those (our schematic is a clone of the
    // ORIGINAL B7K; the captured unit is an Ultra), but do NOT read this as having
    // found the real circuit. What is established is that a 1st-order HP at ~183 Hz
    // is REQUIRED somewhere in the OD path ahead of IC2_A; C7 is the cheapest
    // placement, not a proven one.
    // ▶ A schematic-checker pass on C7 / R11 / R13 / the node-P network is OWED.
    double trebleC7 = 680.0e-12;  // farads; schematic/BOM value is 100n (see above)

    // ---- C15, the clipper-output coupling cap into IC2_B (PedalChain::OdCoupling)
    // Phase 9 / A3 step 3b (session 36). NOT MODELLED AT ALL until this session —
    // PedalChain fed the clipper output straight into RecoveryBridgedT with no
    // coupling stage in between; C15 (2u2) / R20 (10k) / R21 (1M) were simply
    // absent, not merely treated as inert. circuit.md: C15 -> R20 -> node X ->
    // IC2_B(+), R21 X->VD. R20 has no other branch at its near node, so R20+R21
    // combine into ONE effective series R for this first-order HP (same reduction
    // C21Highpass already uses), fixed at the schematic-verified 1.01 MΩ — the
    // step-3b pixel-zoom pass (docs/phase9-validation.md §4) closed off any
    // resistance-side explanation: even R21->0 leaves R20's 10k = 7.2 Hz, and
    // that would also tie the node to VD and kill the signal.
    //
    // ⚠⚠ SESSION 36 SHIPPED 1.5 nF AND SESSION 37 REVERTED IT TO 5.2 nF. Read this
    // before touching the value again — the 1.5 nF selection is instructive.
    // Session 36 chose 1.5 nF on the band-RMS aggregate over a 96-row matrix subset
    // (0.3/0.7/1.0/1.5/2.0/3.0/5.2/10 nF -> 4.734/4.048/3.698/3.475/3.490/3.568/
    // 3.839/4.187, off = 4.508), over the ~30 Hz that the single-condition fit gave.
    // That selection was wrong on TWO counts, both already-documented traps:
    //   (a) THE PER-ROW GAIN-MATCH REFRAME. The HF bands (320 Hz-12.9 kHz = 15 of
    //       the 26 graded bands) appeared to prefer 1.5 nF strongly, 2.794 -> 3.823
    //       dB across 1.5 -> 10 nF. But a first-order corner at 105 vs 30 Hz is
    //       indistinguishable above 320 Hz, and re-anchoring the gain match to those
    //       bands collapses it to FLAT 2.579-2.597 dB at EVERY value. It was the
    //       report's broadband scalar re-solving, and it dominated the aggregate.
    //   (b) THE REMAINDER IS ENTIRELY THE GRUNT flat/boost ROWS, WHICH CARRY A
    //       SEPARATE UNFIXED DEFECT (GAP #3b). LF 25-80 Hz band-RMS split by GRUNT:
    //       at CUT (68 rows) it bottoms at 4-5.2 nF (3.835/3.839) and 1.5 nF is the
    //       WORST tested (5.083, worse than off at 4.378); only flat/boost prefer
    //       1.5 nF. Session 23 measured the pedal's GRUNT span as a BUMP at
    //       127-202 Hz against the model's monotone SHELF maximal at DC, and
    //       recorded that a first-order coupling cap can never turn a shelf into a
    //       bump. So 1.5 nF was a COMPENSATING ERROR for GAP #3b, chosen by letting
    //       the defective row group vote.
    // THE GATES THAT ACTUALLY TARGET A3 ALL PREFER ~5.2 nF, and they agree:
    //   * raw-capture fit (a3_lead_fit, true H=1 after the fix_k bug fix below):
    //     4.0/4.7/5.2/6.0 nF -> 1.115/0.979/0.904/1.022 dB, interior minimum at 5.2,
    //     where the free-gain row also wants k = 0.995 (NO level correction). At
    //     1.5 nF the same metric reads 3.339 dB — worse than deleting the element —
    //     and asks for +5.6 dB of broadband OD gain to patch it.
    //   * the migrating NULL over 3 stimulus levels x 5 drives (a3_level_axis.py):
    //     5.2 nF 12/15 bands matched, 3.0 nF 12/15, 8.0 nF 5/15, 1.5 nF 0/15,
    //     off 0/15 — worse in BOTH directions from ~3-5 nF.
    //   * beta identifiability: -17.38 at 5.2 nF, 0.45 dB from the model's own
    //     -16.93; at 1.5 nF beta only resolves once a free gain absorbs the error.
    // FULL 63-CAPTURE COST OF THE REVERT, measured, and it splits on GRUNT exactly
    // as (b) predicts: GRUNT cut (76 rows) 2.478 -> 2.284, GRUNT cut gain-n12 (16)
    // 6.837 -> 5.843, GRUNT flat (12) 2.191 -> 4.055, GRUNT boost (16) 2.850 ->
    // 5.449, ALL OD 3.080 -> 3.357, CLEAN bit-identical, OD tilt -0.72 -> -0.11.
    // 92 of 120 OD rows improve; the aggregate regresses only because the 28
    // flat/boost rows vote. ⚠ DO NOT "FIX" THOSE 28 WITH C15 — they need GAP #3b.
    // (Same posture as session 28's c21R: "OD got worse and that is EXPECTED".)
    // User decision 2026-07-27: ship the mechanism-correct value now.
    // Full detail: docs/phase9-validation.md §4 "A3 step 3c".
    //
    // At schematic 2u2 the corner is 0.072 Hz (audibly inert); reaching ~30 Hz
    // needs C15 ~= 5.2 nF, a ~423x departure from 2u2 — far LARGER than trebleC7's
    // 147x, and WITHOUT trebleC7's structural argument (C7 sits ahead of IC2_A's
    // own rail-clip nonlinearity, so no downstream linear element can substitute
    // for it — the oracle-floor test proved that. C15 is AFTER the CD4049 clipper,
    // so a change here is a plain linear multiplier; several other post-clipper
    // positions could carry an identical transfer function, so this placement is a
    // convenient carrier, not a load-bearing physical claim).
    // ⚠ SHIPPED ON EXPLICIT USER AUTHORISATION (2026-07-26): "if changing the C15
    // change will make the plugin more accurate, lets do it, I don't care how off
    // it is" — same posture as clipK/clipC11's user-authorised departures from a
    // shared/schematic-plausible element (session 17 note, Clipper.h).
    double clipC15 = 5.2e-9;     // farads; schematic C15 = 2u2 (2.2e-6). fc ~30.3 Hz
                                  // into R20+R21=1.01M. Gated on the NULL + the raw
                                  // captures, NOT on matrix band-RMS (see above).

    double btR22 = 100.0e3;
    double btR23 = 33.0e3;
    double btC16 = 680.0e-12;
    double btC17 = 22.0e-9;

    // ---- TL07x op-amp output rails (RailClamp, shared by every op-amp stage) -
    // calibration §6. ** ENABLED 2026-07-25 (Phase 9 session 21) ** — the standing
    // GATE item, finally landed. Its precondition (kInputRef anchored, session 17)
    // has been met since 2026-07-22; what blocked it until now was a HARNESS bug
    // (the 20 gain-n12 captures were rendered ~12 dB hot because render_args()
    // never emitted --input-trim), which made the EQ-boost-max captures look like
    // rail-clamp regressions. On the level-honest matrix it is a clear win across
    // all 63 captures / 240 rows — phase9-validation.md GAP #3a.
    //
    // VOLTAGES ARE DERIVED, NOT FITTED. +9 V -> D3 (1N5817, ~0.35 V) -> rail
    // ~8.65 V; VD = rail/2 = 4.32 V; a TL07x swings to within ~1.5 V of each rail
    // (datasheet typ; worst-case min is ~3 V) => ~+-2.8 V around VD, with the
    // POSITIVE side clipping first. Hence 2.7 V positive / 2.9 V negative.
    // ** Do NOT "fit" these lower.** The capture scan is MONOTONE all the way down
    // (subset band-RMS 7.64 at 3.3 V -> 7.42 at 2.6 -> 7.22 at 2.0, no interior
    // minimum), i.e. the objective always wants more clipping — the same
    // "make the clipper see less" degeneracy that killed the session-5/6 fits.
    // Taking the physical typical value captures most of the gain (~-0.8 of the
    // -1.0 dB available at 2.0 V) without chasing an unphysical optimum; the
    // 0.2 V asymmetry is worth a further -0.12 dB at matched mean.
    // ** BOTH ARE MAGNITUDES (positive), not signed limits: RailClamp saturates
    // into [-railNeg, +railPos] and uses railNeg as a magnitude internally
    // (x < -(railNeg - knee)). railNeg was -3.3 here until 2026-07-22, which made
    // the negative branch fire for EVERY sample below +2.95 V and return a
    // constant +3.3 V — the clamp emitted DC, not audio. It never showed because
    // railEnabled has always been false; it would have surfaced as a garbage
    // step-2 re-fit the moment rails were enabled. RailClamp::setRailVoltages now
    // takes |v| defensively so a signed --fit railNeg cannot resurrect it. **
    bool railEnabled = true;
    double railNeg = 2.9;
    double railPos = 2.7;

    // ---- MID stages: range limiter + the LO-MID "250" cap (Phase 9 GAP #4) -------
    // The captures say the real pedal's mid boost/cut range is ~+-12 dB at EVERY switch
    // position; the modelled network's values imply +-14.5...+-28 dB (circuit.md's
    // [ENG-caps] table). `schematic-checker` (2026-07-25) returned TOPOLOGY CONFIRMED
    // FAITHFUL — MidBand.h matches circuit.md node for node and the full R1-R54 BOM
    // census leaves no spare resistor — so per the pre-registered decision tree in
    // docs/phase9-validation.md §4 GAP #4 these are FITTED to the capture, exactly as
    // c21R / trebleLadderDampR / the rail voltages were. The full derivation (why a
    // wiper-leg series R and not R38/R39, R40/R41, the across-lug cap, pot end-travel
    // or rail compression) is in MidBand.h::setWiperR and the §4 gap log.
    //
    // Measured effect over all six switch positions (boost-to-cut span, 160 Hz-4.1 kHz,
    // matched-pair differential so the rest of the chain cancels exactly):
    //   band-RMS vs the pedal  9.66 -> 4.68 dB
    //   4-point POT LAW RMS    5.31 -> 0.87 dB   <- the knob response a player feels
    // ONE resistor has to serve all three switch positions of a band, so the two
    // smallest caps (LO-MID 1k, HI-MID 3k) are slightly OVER-corrected (RMS 1.64->2.91
    // and 1.38->2.63). That is an accepted, inherent trade, not a fit artefact — the
    // net is decisive and the two large-cap positions improve by 10-11 dB RMS.
    //
    // ---- A2c-2 (session 26) RETUNE: both values REDUCED, jointly with the cap table
    // below. GAP #4 fitted Rw against the boost-to-cut SPAN, which is dominated by the
    // peak's HEIGHT and nearly blind to its WIDTH — and a series R in the wiper leg is
    // exactly the element that buys range by DAMPING, i.e. it pays for height with Q.
    // Measured against the pedal's full stage SHAPE it overshot: at LO-MID 250 the
    // shipped model matched the pedal's peak depth and centre exactly (-14.0 dB @
    // 320 Hz both) yet its skirts were 4.33 octaves wide at half-depth against the
    // pedal's 2.67. Re-fitting Rw and the switched caps TOGETHER against the shape
    // recovers the peak CENTRES that GAP #4 recorded as its open residual (see the
    // cap table below) at a lower Rw. Both are clean interior minima — LO-MID
    // 0k 2.00 / 15k 1.07 / 22k 0.97 / 33k 1.09 / 68k 1.83 dB; HI-MID 0k 2.04 /
    // 12k 1.13 / 18k 1.04 / 22k 1.06 / 68k 2.09 — so the objective pushes back from
    // both sides, unlike the "make it see less" degeneracies of sessions 5/6 + GAP #3b.
    // ⚠ SUPERSEDED BY A2c-3 (session 27, see midCapRatioLo below): once the across-lug
    // cap is switched as a scaled PAIR with the series cap, Rw no longer has to buy the
    // range on its own and both bands drop to the SAME, much smaller value. The scan at
    // the shipped A2c-3 cap set is a clean interior minimum and is now shared by both
    // bands: 0k 0.544 / 2.2k 0.511 / 4.7k 0.500 / 6.8k 0.509 / 15k 0.654 / 33k 1.117 dB
    // (0.584 / 0.539 / 0.509 / 0.500 / 0.587 / 0.997 over the wider 63 Hz-8 kHz window,
    // where 6.8k is the minimum). 4.7k and 6.8k are indistinguishable; 6.8k is taken as
    // the value the raw joint fit landed on (6.42k / 6.59k on the two windows).
    // The A2c-2 numbers quoted below applied to the shared-C32 network and no longer
    // describe the shipped one — kept because they are the record of why Rw exists.
    double midWiperRLo = 6.8e3;    // LO-MID (IC5_D) wiper leg; 33k (GAP #4) -> 22k (A2c-2)
    double midWiperRHi = 6.8e3;    // HI-MID (IC6_A) wiper leg; 22k (GAP #4) -> 18k (A2c-2)

    // ---- Mid across-lug cap ratio (Phase 9 A2c-3, session 27) -------------------
    // C32 (LO-MID) / C34 (HI-MID) is switched TOGETHER with the series cap, as a
    // SCALED PAIR: C32_position = midCapRatio * C33_position. MidBand::setAcrossCap.
    //
    // WHAT THIS RESOLVES. A2c-2 capped A2c with the peaks still ~1.31x too broad and
    // recorded the reason: with one wiper-leg R per band, range and width are set by
    // the same element, so you cannot have both. It also recorded what reopening would
    // take — "NEW evidence about the switch's real topology (is the mid-frequency
    // selector 2-pole, switching the across-lug cap too?), not another fit." That is
    // exactly what this is. The user authorised per-position fitting on 2026-07-26,
    // and the per-position optimum then turned out NOT to need per-position freedom:
    // fitting C32 freely at each of the six positions lands at a near-constant ratio
    //   LO-MID  53.3/6.91 = 7.7 ... 15.9/2.34 = 6.8   (joint refit: 10.4)
    //   HI-MID  22.7/3.31 = 6.9 ... 6.07/0.80 = 7.6   (joint refit:  9.4)
    // and pinning BOTH bands to exactly 10.0 costs 0.001 / 0.009 dB against the free
    // per-band values, and 0.007 / 0.006 dB against a fully unconstrained per-position
    // fit (C33 + C32 + Rw all free per position, the ceiling A2c-2 measured at
    // 0.17-0.44 dB). So the shipped model has ONE MORE free parameter per band than
    // A2c-2 did, not six, and it reaches the unconstrained ceiling.
    //
    // The ratio is a sharp interior minimum, scanned at the shipped cap set with Rw
    // held (this is the acceptance check, not the fit):
    //   ratio   1     2     4     6     8    10    12    15    20    30
    //   RMS  6.07  4.85  2.98  1.69  0.79  0.51  0.89  1.50  2.25  3.10  dB
    // and refitting Rw at each ratio gives the same answer (8: 0.316, 9: 0.301,
    // 10: 0.298, 11: 0.304, 12: 0.317) — it is not an artefact of holding Rw.
    //
    // ⭐ CORROBORATION THE OBJECTIVE COULD NOT SEE. At ratio 10 the HIGHEST-frequency
    // position of each band lands exactly on that band's DOCUMENTED pair:
    //   LO-MID 1 kHz  -> C33 2n2  / C32 22n    (C32 = 22n is schematic-verified;
    //                                           2n2 is the [ENG] table's own value)
    //   HI-MID 3 kHz  -> C35 680p / C34 6n8    (BOTH schematic-verified — they are the
    //                                           stock board's fixed HI-MID pair)
    // i.e. the model that came out of the fit is "the stock network is one switch
    // position, and the other two scale that same pair up" — and 6n8/680p is itself a
    // ratio of exactly 10. Nothing in the objective knew about those values. This is
    // the one piece of independent evidence in this whole gap, so weigh it: it is what
    // separates A2c-3 from A2c-2's rejected per-position fudge (C32 at 26.8n/31.9n/7.2n
    // with R40/R41 at 3.5-9.6x, which corresponded to nothing).
    //
    // ⚠ Still a FIT, not a documented circuit. The 3-way selectors are [ENG] — they do
    // not exist on our schematic — so nothing here contradicts a document; but neither
    // is there a document confirming the switch is 2-pole. Per-band fields (rather than
    // one shared) only so a future capture can differentiate them; both are 10.0 and a
    // free per-band fit (10.39 / 9.38) is not better.
    double midCapRatioLo = 10.0;   // C32 = midCapRatioLo * C33  (LO-MID, IC5_D)
    double midCapRatioHi = 10.0;   // C34 = midCapRatioHi * C35  (HI-MID, IC6_A)

    // ---- Switched mid-frequency cap table (Phase 9 A2c-2, session 26) -----------
    // circuit.md's [ENG-caps] table was COMPUTED (f ~ 1/sqrt(C_series)) and has never
    // been schematic-verified — the 3-way mid-frequency selectors do not exist on our
    // schematic at all, so unlike R36/C13 there is no document to defer to here. These
    // are fitted to the captured unit's measured stage shape (both knob extremes, all
    // three positions of a band at once, every parameter shared across the band — no
    // per-position fudge), jointly with midWiperR* above.
    //
    // What this fixes: GAP #4's Rw pulled every peak CENTRE down, which that gap
    // recorded as an accepted-but-open residual. Peak frequencies are compared at
    // SUB-BAND resolution (parabolic fit through the peak band and its neighbours on
    // the log-f axis, analysis/mid_shape_verify.py) — the 1/3-octave grid only locates
    // a peak to +-1/6 octave, and reading it off the raw grid says three of these
    // positions were already exact when in fact EVERY one was 9-20% low:
    //              pedal    was (GAP #4)      now
    //   LO-MID    349 Hz    294 Hz (-16%)   371 Hz (+6%)
    //             545 Hz    436 Hz (-20%)   548 Hz ( 0%)
    //            1090 Hz    929 Hz (-15%)  1064 Hz (-2%)
    //   HI-MID    784 Hz    665 Hz (-15%)   827 Hz (+5%)
    //            1613 Hz   1409 Hz (-13%)  1594 Hz (-1%)
    //            3026 Hz   2611 Hz (-14%)  3178 Hz (+5%)
    // Worst peak error 20.3% -> 6.1% (LO-MID) and 15.2% -> 5.4% (HI-MID); stage-shape
    // band-RMS 1.68 -> 0.97 and 1.44 -> 1.04 dB.
    //
    // The positions stay clearly differentiated (cap ratios 2.2x/3.8x and 3.7x/4.0x),
    // so this is NOT the session-22 joint fit that collapsed the "250" position onto
    // the 500 Hz cap and was rejected for destroying the switch's spread. Every one of
    // the eight values (6 caps + 2 Rw) sits at an interior minimum of the shape
    // objective with its E12 neighbours worse on both sides — e.g. LO-MID 250
    // 10n 1.24 / 12n 1.05 / 15n 0.97 / 18n 1.05 / 22n 1.24.
    //
    // ⚠ This RETIRES the GAP #4 argument that midLoCap250 = 22n was corroborated by
    // being the STOCK board's schematic-verified C33. That corroboration came from
    // circuit.md's nodal sim, which was run at Rw = 0; with the fitted wiper-leg R in
    // the model, 22n centres at 306 Hz against the pedal's measured 349 Hz. The value
    // was only ever a behavioural match, so it does not survive a change to the rest
    // of the network. (A2c-2 also noted its 3 kHz position landing on 0.68n = the stock
    // C35, and dismissed it as a coincidence of the same kind. A2c-3 below revives that
    // observation on stronger evidence — it lands the stock PAIR, C35 680p AND C34 6n8
    // together, and does the same thing at LO-MID 1 kHz — but a single value matching
    // remains weak evidence and A2c-2's dismissal was right on what it had.)
    //
    // ⚠ RE-FITTED BY A2c-3 (session 27) once the across-lug cap joined the switch as a
    // scaled pair (midCapRatioLo above) — the values below are A2c-3's, not A2c-2's.
    // Every one is an E12 value and a clean interior minimum of the shape objective
    // with its E12 neighbours worse on BOTH sides, scanned at ratio 10 / Rw 6.8k:
    //   LO-MID 250   4.7n 2.17 | 5.6n 1.05 | 6.8n 0.59 | 8.2n 1.67 | 10n  2.85
    //   LO-MID 500   2.7n 2.18 | 3.3n 1.18 | 3.9n 0.35 | 4.7n 0.73 | 5.6n 1.61
    //   LO-MID 1k    1.5n 2.11 | 1.8n 0.93 | 2.2n 0.57 | 2.7n 1.92 | 3.3n 3.21
    //   HI-MID 750   1.8n 3.14 | 2.2n 1.86 | 2.7n 0.47 | 3.3n 1.01 | 3.9n 2.16
    //   HI-MID 1.5k  1n   1.57 | 1.2n 0.77 | 1.5n 0.48 | 1.8n 1.35 | 2.2n 2.33
    //   HI-MID 3k    0.47n 2.25| 0.56n 1.51| 0.68n 0.62| 0.82n 0.77| 1n   1.83
    // (the HI-MID 3 kHz row is quoted over 63 Hz-8 kHz: at the narrower 100 Hz-4.1 kHz
    // window the position's upper skirt is truncated and 0.68n/0.82n tie at 0.56/0.56,
    // while 0.68n wins on every window that contains the whole skirt.)
    // Since C32 = 10 x C33 and a decade shift preserves the E12 series, the across-lug
    // values are E12 too: LO-MID 68n/39n/22n, HI-MID 27n/15n/6n8.
    double midLoCap250 = 6.8e-9;    // 250 Hz  ([ENG] 47n; GAP #4 22n; A2c-2 15n)
    double midLoCap500 = 3.9e-9;    // 500 Hz  ([ENG] 10n; A2c-2 6.8n)
    double midLoCap1k = 2.2e-9;     // 1 kHz   ([ENG] 2n2 — back onto the [ENG] value)
    double midHiCap750 = 2.7e-9;    // 750 Hz  ([ENG] 15n; A2c-2 10n)
    double midHiCap1500 = 1.5e-9;   // 1.5 kHz ([ENG] 3n3; A2c-2 2.7n)
    double midHiCap3k = 680.0e-12;  // 3 kHz   ([ENG] 820p — = the STOCK board's C35)

    // ---- Baxandall TREBLE range limiter (Phase 9 A2c-1, session 25) -------------
    // R36 (Wt -> IC5_C virtual ground) is schematic-verified at 3.3k, but the captured
    // unit's TREBLE boost-to-cut SPAN (matched-pair, so the rest of the chain cancels
    // exactly) is NARROWER than the modelled network delivers there: end to end over
    // 25 Hz-12.9 kHz the pedal tilts 33.6 dB, the network at 3.3k tilts 38.4 dB — and
    // at the fitted 4.7k it tilts 33.8 dB, i.e. straight onto the pedal. A 1-D
    // scan against that span has a clean INTERIOR minimum near 4.7-5.0k — 3.3k 2.44 /
    // 4.4k 0.89 / 4.7k 0.59 / 5.0k 0.54 / 6k 1.60 / 10k 5.86 dB band-RMS, i.e. the
    // objective pushes back from BOTH sides, NOT the one-sided "make it see less"
    // degeneracy that killed the session-5/6 clipper fits and the GAP #3b C13 fit.
    // The independent 4-point pot law (0.62 -> 0.27 dB) confirms it isn't just buying
    // the extremes at the cost of mid-travel.
    // BASS is unaffected: R36 carries only the treble leg's contribution to the shared
    // virtual-ground node, so at treble-flat the delta is <0.004 dB at every band —
    // measured, the four bass captures + both ref-clean takes move by <=0.024 dB.
    // Same posture as c21R (10k -> 100k): a plain VALUE fit on a schematic-verified
    // part, because the captured unit is a real Ultra while the primary schematic is a
    // clone of the ORIGINAL B7K — "the document is right AND the captured unit differs",
    // the same branch as C13 and the [ENG] mid caps.
    // ** NOT independently topology-checked: no schematic-checker pass was run (unlike
    // GAP #4, which hypothesised a NEW element and needed a BOM census). The evidence
    // the topology is right is indirect — a pure VALUE change flattens the span residual
    // across the whole band, where a wrong topology would leave a frequency-dependent
    // shape residual. See docs/phase9-validation.md §4 "A2c-1". **
    double trebleWiperR = 4.7e3;  // fit ~4.86k, E12-rounded (was nominal 3.3k)
};
