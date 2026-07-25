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
    double c21R = 100.0e3;  // session-18 Phase-9 A/B fit (was nominal 10k). The clean-sweep
                            // capture shows the tone-stack coupling corner is ~16 Hz, NOT the
                            // 159 Hz the 10k estimate gave: the plugin was 6-15 dB bass-light
                            // below ~100 Hz (identical clean & driven -> shared post-BLEND HP).
                            // Fit on ref-clean (flat EQ) + validated across 34 EQ/blend captures:
                            // low-band RMS deficit 9.8 -> 0.69 dB, no overshoot. Implies C21's
                            // effective RC is ~10x nominal (C21 > 100n OR stack input Z > 10k) —
                            // ⚠ C21's schematic value/placement is worth a schematic-checker pass;
                            // the capture is authoritative on the corner (dsp.md fit-the-corner).

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
    double midWiperRLo = 33.0e3;   // LO-MID (IC5_D) wiper leg; fit 53.7k, E12-rounded
    double midWiperRHi = 22.0e3;   // HI-MID (IC6_A) wiper leg; fit 22.1k

    // LO-MID "250 Hz" switch position. The [ENG] table computed 47n (-> a 229 Hz
    // centre); the capture peaks at the 320 Hz band, and 22n — which is the STOCK
    // board's C33, schematic- and BOM-verified — puts the modelled centre exactly
    // there. Two independent lines of evidence agree, so this is the one cap value
    // in the table the captures actually contradict. The other five stay [ENG].
    // (A joint fit that refits ALL six caps scores better on paper but collapses this
    // position onto ~10n, i.e. onto the 500 Hz position's cap — it destroys the
    // switch's frequency differentiation, so it was rejected. §4 GAP #4.)
    double midLoCap250 = 22.0e-9;

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
