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
    // clipSatLo/clipSatHi are the per-side VTC ceilings; their SUM is bounded ABOVE
    // by the R19-dropped effective rail and their DIFFERENCE is the even-harmonic
    // asymmetry. Fit to the drive-sweep Farina THD(f) + low-frequency-tone H2/H3
    // balance.
    // ⚠ SESSION 142: this line used to read "their SUM **is** the R19-dropped effective
    // rail (nominal ~7 V, below the 8.6 V op-amp rail)". TWO errors in one clause.
    // (a) "~7 V" is exactly the round figure session 42 called out as "a rail no
    //     calculation ever produced" -- the DERIVED, self-consistent value is
    //     **VDD = 5.636 V** (circuit.md; analysis/clipper_rail_selfconsistent.py), and
    //     the crowbar current is self-limiting, which a fixed-drop prior cannot express.
    // (b) "is the rail" states an EQUALITY where the physics gives a one-sided bound:
    //     a CMOS inverter cannot swing PAST its rail, so the sum is bounded from ABOVE
    //     only. A sum below the rail is not a supply violation -- which is the whole
    //     reason the 18 % flag below is SOFT. The equality reading is what made the
    //     session-118 clamp bug possible in the first place.
    // ** SESSION 44 (Phase 9 / A5 step 2): RE-FITTED under the clean path's supply bound. **
    // The session-17 family was fitted with kInputRef FROZEN at 3.377 — a value session 41 then
    // proved IMPOSSIBLE (IC5_B's fixed -2.2x would need 5.26 V of swing on a +/-4.325 V supply).
    // Session 43 showed the OD harmonic objective does not identify K AT ALL (unfenced it rests on
    // whatever bound the box provides), so the clean path is not a competing constraint but the
    // MISSING EQUATION. Re-fit with K fenced to <= 1.509 (analysis/clean_headroom_bound.py) and the
    // clipper ceilings freed: cost 649.6 (shipped, on today's model) -> 34.1, ALL step-4 acceptance
    // checks green and NO parameter resting on a bound. See analysis/fit_logs/step7_a5_sq2.log.
    // clipA0 = 24.87 is INTERIOR in [20, 30] and independently corroborated: the same DAFx-2020
    // device model that gives the 5.636 V rail also gives A0 = 22.0 at its own lambda
    // (clipper_rail_selfconsistent.py section 4). Note circuit.md's "20-30" is a COMMUNITY
    // measurement, not a datasheet spec — the TI datasheet carries no small-signal gain figure.
    // ⚠ clipSatLo+Hi = 1.036 V is only 18 % of the 5.636 V rail — a SOFT flag, deliberately not a
    // rejection: the rail bounds the sum from ABOVE only, and rejecting on the floor alone is the
    // half-of-a-degenerate-pair error session 16 caught. It is structural to the fenced K (the
    // clipper's drive scales with K, so a 2.7x lower K pulls the fitted ceiling down with it).
    // A fit forcing satsum back into session-15's [1.5, 4]/side fence costs 34.1 -> 201.8 and pins
    // THREE parameters at once (step7_a5_sqphys.log) — that region is jointly infeasible.
    //
    // ⛔⛔⛔ SESSION 142 — DO NOT RE-FIT THIS FAMILY AGAINST A PHYSICAL CEILING. OPEN-WORK ITEM 5
    // PROPOSED EXACTLY THAT FOR ~24 SESSIONS AND **THE PEDAL'S OWN 9 V SUPPLY FORBIDS IT.** Closed
    // form, no fit, no render, no threshold — every input is schematic-derived or shipped:
    //   * the VTC is HOMOGENEOUS (vtc_{L*s}(L*w) = L*vtc_s(w)), so raising the ceilings by L
    //     preserves the clipper's operating point ONLY if the drive at node W also rises by L;
    //   * L = VDD/satsum = 5.636/1.0356 = **5.442x (+14.72 dB)**  (per side: satLo x6.07, satHi x4.98);
    //   * everything from the jack to node W is schematic-FIXED — IC1_A unity, the J201 stage, the
    //     treble/ATTACK ladder, IC2_A = 1 + R15/(R17+DRIVE+R32), R16 — so the ONLY free scalar is
    //     kInputRef, and it would have to become 0.90 x 5.442 = **4.898 V/FS**;
    //   * against that: TL07x knee (the binding clean-THD fence) **1.509**, TL07x hard limit 1.734,
    //     and the ABSOLUTE supply ceiling **2.777** — "no op-amp on this rail can beat it", since it
    //     is just VD/(2.2 x 10^(-3/20)) from the 8.65 V rail and IC5_B's fixed -2.2.
    //   => the requirement exceeds even the ABSOLUTE supply ceiling by **1.76x (+4.93 dB)**. Taking
    //      K to that absolute ceiling supplies only **56.7 %** of the needed scale (30.8 % to the
    //      binding fence). ** A physical clipSat is not merely expensive to fit; it is unreachable
    //      on this supply. ** (analysis/clean_headroom_bound.py section 1 for the ceilings.)
    // ⭐ This refutes the route on the AXIS THE PARAMETER LIVES ON (supply arithmetic), which is
    //   strictly stronger than session 44's fit-cost argument above: a cost of 201.8 invites "try a
    //   better optimiser", whereas a supply bound cannot be argued down.
    // ⚠ AND THE DIRECTION HAS MOVED THE WRONG WAY SINCE ITEM 5 WAS WRITTEN: session 44 fitted this
    //   family at kInputRef = 1.2596; session 109 shipped **0.90** (1.40x lower) WITHOUT re-fitting
    //   clipSat. By the co-scaling above that puts the pair further from physical, not closer.
    // ⇒ what remains open is NOT a fit but a PHYSICAL question: either the clipper's ceiling really
    //   is ~5.4x low, or ~14.7 dB of gain ahead of node W is missing from the model. The second
    //   branch is UNTESTED. Do not spend a fit before deciding which.
    double clipA0 = 24.871;      // session-44 A5 re-fit (was 26.142, session-17)
    double clipSatLo = 0.4377;   // session-44 A5 re-fit (was 2.0067, session-17)
    double clipSatHi = 0.59791;  // session-44 A5 re-fit (was 2.9321, session-17)
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
    // ⛔⛔ SESSION 123: THE JUSTIFICATION IN THE THREE LINES ABOVE IS REFUTED —
    // memoryless ADAA DOES apply to this stage (PedalChain.h's anti-aliasing block
    // and Clipper.h::setADAA carry the argument and the measurement), so "the
    // closed-form antiderivative is never used" is no longer a safe assumption and
    // this non-anchor k had a COST: it is what made ADAA inert. Measured value of the
    // ADAA it blocked: 12.6-19.8 dB of median alias-floor improvement over 19 tones
    // at OS 1x/2x (GATE X, analysis/clip_adaa_gate.py).
    // ✅ SESSION 124 RE-ANCHORS k TO 2.0, ON THE USER'S DECISION, AND THE PRICE WAS
    // MEASURED FIRST, NOT ARGUED. `s123_k2.json` vs `s123_kship_control.json` (162
    // captures, identical membership, n identical on all 14 gated rows, both at
    // os_factor 8 with ADAA off so the arms isolate k alone): k=2 is better on 8 rows,
    // worse on 3, and bit-unmoved on all four CLEAN rows — the last of which is a free
    // SCOPE check, since the clipper is OD-only and a CLEAN move would have meant the
    // constant reached further than intended. Both headline OD rows improve (band-RMS
    // 1.959 -> 1.947, p99 10.348 -> 10.278); the only cost above 0.01 dB is THD
    // full-send +0.038 dB on a row already over its bar by 0.52. SIX ROWS OVER SHIP
    // EITHER WAY — no verdict changes.
    // ⚠⚠ DO NOT RECORD THIS AS "k=2 FITS BETTER". The movements are far inside the
    // spread this project treats as significant; the honest statement is
    // *indistinguishable, with a rounding preference*. The reasons to prefer 2.0 are
    // (a) it makes ADAA exact and therefore usable, and (b) it restores the k==2 sqrt
    // fast path — NOT the ledger. Anyone re-opening this should re-read that sentence
    // before quoting the 1.947 as evidence of accuracy.
    // The k != 2 forward path (Clipper.h vtc()/vtcDeriv()) is a plain pow(), exact
    // for any k; only the k==2 sqrt fast-path is skipped.
    // ⚠⚠ SESSION 127 CORRECTION — THE LINE ABOVE USED TO END "(a little more
    // CPU/sample)", AND THAT UNDERSTATED IT BY TWO ORDERS OF MAGNITUDE OF IMPORTANCE.
    // Measured (tests/PerfBenchmark.cpp, ctest #18): the k==2 fast path is worth
    // **-56 to -59 % of the WHOLE PLUGIN's CPU at every OS factor** (chain, ns per base
    // sample: 1x 437.8 -> 183.7, 8x 3151.8 -> 1297.7), i.e. off the anchor the plugin
    // is ~2x slower. Clipper alone at 384 kHz: 314.6 -> 110.1 ns/sample, -65 %. The
    // arithmetic closes independently at 3 %: 11.97 ns per pow() on that machine x ~17.6
    // pow calls/sample (4 initial + 4 x ~2.9 Newton iterations + 2 for the emitted y).
    // ⇒ ** THIS CONSTANT IS A PERF PARAMETER AS WELL AS A SHAPE ONE, AND NO FIT
    // OBJECTIVE IN THIS PROJECT SCORES EITHER OF ITS TWO NON-SHAPE COSTS. ** Before
    // shipping any re-fitted k (open-work item 5's K/clipSat re-fit against the physical
    // rail is the live candidate), require BOTH:
    //   (a) is the winner distinguishable from k = 2.0 on accuracy? A fitter reports the
    //       argmin, never the set of points indistinguishable from it, so this is a
    //       SEPARATE question and s124's answer was "no" (162 captures) after 80 sessions
    //       of carrying 2.4653. Break an accuracy tie toward the anchor.
    //   (b) is the 2x CPU and the SILENT DEATH OF ADAA (adaaExact() gates on
    //       hardness == 2.0 — no error, no log line, the feature just stops) worth
    //       whatever the non-anchor k buys? Say the price out loud in the handover.
    // measurement-discipline.md §4 carries this as a general rule. **
    double clipK = 2.0;          // session-124 re-anchor (was 2.4653 session-44 A5, 2.8462 session-17)
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
    double clipC11 = 3.69e-9;    // session-44 A5 re-fit (was 5.7207e-9; schematic 4.7 nF, user-authorised to move)
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
    // clipR16 = the clipper INPUT resistor. Schematic 6k8, pixel-zoom verified and
    // BOM-reconciled; settable only so the A3 crossover sub-gate can scan it
    // (session 45). It is the one GRUNT-branch element that moves all three corners
    // TOGETHER — 1/(2*pi*Cg*(R16 + R18/(1+A0))) — leaving the cap ratios, and hence
    // the span shelf's height, alone; C11/C12/C13 each move height and frequency at
    // once. ⚠ But it is NOT a free frequency knob: it also sets the closed-loop gain
    // -R18/R16, so lowering it to raise the corners raises the OD level with them.
    // Measured session 45 — see the note at the top of §4 "A3 crossover sub-gate".
    double clipR16 = 6.8e3;      // ohms; schematic 6k8 — DIAGNOSTIC, ships at nominal

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
    double jfetSatPos = 0.4559;  // s: square-law knee (gate volts) — session-44 A5 re-fit (was 0.20072)
    double jfetSatNeg = 1.9;     // a: even strength (signed) — session-91 (was 0.76054, session-44
                            // A5; 3.1769 before that). THE LOW-DRIVE EVEN-ORDER MOVE, located
                            // session 80 and matrix-judged 81/82/84; shipped on the user's
                            // weighting decision, session 91.
                            //
                            // WHY. `reference-sources.md` §4: hardware is strongly even-dominant
                            // at LOW drive (H2-H3 ~ +18.5 dB) where ND has essentially no
                            // even-order mechanism. Session 79 measured our model on ND's OWN
                            // device (not the demoted chart) and found we sat at +1.4 against
                            // ND's +10.1 — i.e. on the FAR side of ND, ~-104 %, not the +2 %
                            // session 72 believed. So the first ~7.9 dB of this move goes toward
                            // BOTH references at once. In the 129-capture matrix's own output
                            // domain the low-drive H2 deficit is 6.5 dB, spent at a ~= 1.77-1.81
                            // (measured crossing 1.77, bracketed 1.30->1.90), so 1.9 sits at the
                            // EDGE of the free region and lands low-drive H2 on ND at +0.53.
                            //
                            // WHAT IT COSTS (session 84, paired medians vs shipped, per order per
                            // regime — never pooled, the two regimes have OPPOSITE signs and the
                            // pooled bootstrap ranks nothing):
                            //   LOW  H2 +7.92 (ND carries NO authority here, §1) | H3 -0.10
                            //   MID  H2 +2.28 (no authority)                     | H3 -0.66, H5 -0.75
                            // The cost lands on the odd orders, which ARE authoritative — but at
                            // <=0.75 dB, against a 7.92 dB gain on the column hardware cares about.
                            //
                            // ⚠ IT BREAKS THE SQUARE-LAW IDENTITY 2*a*cn = 1, DELIBERATELY. That
                            // identity held EXACTLY at the old point (2*0.76054*0.65743 = 1.000);
                            // here it reads 2.498. Session 84 rendered the identity-honouring
                            // alternative (SQ a=1.9 s=0.40) on the full matrix: it buys +0.23 dB
                            // on the no-authority column and pays -1.45 dB on the authoritative
                            // one at the low anchor (+0.30/-0.42 at mid), because forcing cn down
                            // 2.5x moves the compression knee 4.6x closer to the origin — the
                            // extra even content and the odd suppression are ONE mechanism. So
                            // the identity is affordable but NOT free, and the free move wins.
                            // Do not "restore" the identity without re-reading session 84.
                            //
                            // MONOTONICITY GATED, session 91, against the REAL header (not a
                            // transcription): |a|*s = 0.866. Shipped point passes as the
                            // known-answer, a=6.5 folds back as the mutation check, and the true
                            // fold-back threshold measures **a = 5.333** (|a|*s = 2.431) — BELOW
                            // the 2.598 even-bump bound quoted in JfetStage.h, because that bound
                            // is for the bump in isolation and the asymmetric core tightens it.
                            // 1.9 has 2.81x headroom. ⚠ Session 73's rejected a ~= 5.7 was past
                            // the real threshold, i.e. not merely worse but non-monotone.
                            //
                            // ⚠⚠ KNOWN COST THE 129-CAPTURE MATRIX CANNOT SEE — ALIASING.
                            // `OSValidationTest`'s 8x alias/signal floor moves **-23.6 -> -17.3 dB**
                            // (amp 0.35) when this constant goes 0.76054 -> 1.9. Attribution is
                            // clean and was measured by reverting THIS constant alone: at 0.76054
                            // with c21R already at 130k the test reproduces the 45-session record
                            // to the digit (2x -25.6 / 4x -32.1 / 8x -23.6), so c21R contributes
                            // nothing and this constant owns all of it. The matrix renders at OS=8
                            // and grades FR/THD/harmonics AT BANDS — it never measures inharmonic
                            // energy, so no amount of matrix work would have caught this.
                            // ⚠ NOT established as genuine aliasing. The 8x column is non-monotone
                            // in amplitude both before and after, and at a=1.9 it spikes 7 dB at
                            // amp 0.35 with clean values either side (-40.5 at 0.20, -38.1 at
                            // 0.70) — the signature of one harmonic folding onto a bin, not a
                            // broadband rise. The test's metric also counts every FFT bin further
                            // than ±3 bins from a harmonic as "alias", so a shape with MORE
                            // harmonic content inflates it through window leakage alone. But
                            // `instrument-defect-is-a-hypothesis` (s90) applies: that is an
                            // argument, not a measurement. Settling it needs a bin-exact f0,
                            // mainlobe-POWER summation (`peak-bin-amplitude-scallops`) and a
                            // convergence check against a much higher OS factor.
                            // ⇒ carried to PHASE 10 B (perf/HQ pass), where the OSValidationTest
                            // decision already lives. Shipped with the user's explicit agreement,
                            // session 91, with this cost on the table.
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
    double jfetCeilPos = 2.0111;   // session-44 A5 re-fit (was 2.3428, session-17)
    double jfetCeilNeg = 0.65743;  // session-44 A5 re-fit (was 0.27408) — 2*a*ceilNeg = 1.000, the square-law identity
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
    double jfetExpandBeta = 0.46279; // session-44 A5 re-fit — EXPANSIVE cubic (was 2.1354, session-17)

    // ---- Pot taper shapes (power-law exponent p, R = Rmax * x^p) ------------
    // dsp.md §tapers: fit the SHAPE, don't assume convex, and constrain p with at
    // least TWO knob points across the range (a wrong shape can match one
    // position and flip sign at another). The capture matrix provides 4 points
    // per pot for exactly this.
    double driveTaperExp = 1.98;  // VR3 100k C-taper, in (1-x) — 0 ohm at full CW. session-17
                                  // measured (bleed-free taper, drive_taper_curve.log; was 1.5/2.5)
    // ⭐⭐ SESSION 163 (task D(b)) — THE LEVEL POWER LAW IS RETIRED. `levelTaperExp` NO LONGER
    // EXISTS; a stale `--fit levelTaperExp=` now fails loudly in offline_render rather than being
    // silently ignored (the s115 `masterTaperExp` pattern). VR2 100k A-taper is a FOUR-SEGMENT
    // PWL — full derivation and the shape/containment/cost checks in `LevelBlend.h`'s constants
    // block, GATE AY (`analysis/level_taper_reshape.py`) and GATE AZ (`analysis/level_taper_fit.py`).
    //
    // The one-line reason: against the pedal's own LEVEL ladder the shipped exponent 2.25 was
    // 2.844 dB rms out (worst 7.638); this curve reaches 0.340, which is the architectural floor
    // (a free per-detent curve gets 0.344) and is inside the target's OWN across-stimulus
    // ambiguity of 0.755 dB. ⛔ Do NOT "simplify" it back to an exponent: the best single exponent
    // over this ladder is p = 2.002 at 2.106 dB rms, still OUTSIDE that ambiguity by 2.79x.
    //
    // ⚠⚠ THIS CHANGES `LevelBlend::cleanFraction()`, which `OdToneRestore`'s s156 mix law READS —
    // worst |Δcf| = 0.1292 at LEVEL 0.875 (GATE AZ5). The notch fit is therefore stale by
    // construction after any change here; re-run its acceptance table across all five `--set`
    // conditions (open work item 10).
    double levelTaperBreak1 = 0.219415;   // rotation at which the wiper reaches levelTaperFrac1
    double levelTaperFrac1 = 0.038146;    // fraction of full resistance at that rotation
    double levelTaperBreak2 = 0.529680;
    double levelTaperFrac2 = 0.166340;
    double levelTaperBreak3 = 0.857645;
    double levelTaperFrac3 = 0.425688;
    // VR8 100k A-taper [ENG]. ** SESSION-41: 2.25 -> 1.998. ** Session 17 set 2.25 by borrowing
    // LEVEL's exponent, on the grounds that the master captures "bracket it: 2.06/2.37". They no
    // longer do — `master-1700_gain-n12_base-clean.wav` was found to be a BAD TAKE and re-recorded
    // in session 24 (its sweep_clean RMS moved -16.62 -> -18.20 dBFS), and it is the DENOMINATOR of
    // both bracket estimates, which now read 1.93 (m=0.25) and 1.73 (m=0.75). Nothing re-ran the
    // calibration afterwards, so a stale reference capture stayed baked into two shipped constants.
    // ⚠ A THIRD interior knob point was also missing: `ref-clean.wav` IS master=0.50 of this same
    // series (_REF_OD with base=clean is every pot at noon), it just carries no `master-` filename
    // token, so the fit never saw the middle of the knob's travel — the exact place the shipped
    // value was worst (2.5 dB). With it, the per-point exponents are 1.929 / 2.322 / 1.734 at
    // m = 0.25 / 0.50 / 0.75 — NON-MONOTONE, so no power law of any exponent fits all three. Same
    // finding as the DRIVE C-taper (session 16): a real pot taper is not a power law, and a
    // one-parameter family fitted to ONE point looks exact and is wrong everywhere else.
    // 1.998 is the LEAST-SQUARES value over all three, chosen on WHOLE-TRAVEL error:
    //   worst |err| vs the captures — 2.25 (shipped) 3.87 dB | 1.734 (m=0.75) 3.54 |
    //   2.322 (m=0.50) 4.73 | 1.929 (m=0.25) 2.37 | **1.998 (LS) 1.95**
    // That is master_taper_makeup.py's own untargeted consistency check, which session 17 recorded
    // as FAILING at 3.71 dB and shipped anyway. analysis/fit_logs/step7_master_taper_makeup.log.
    // The residual 1.95 dB sits at m=0.50 and is the power law's own limit, not a fit error; it is
    // also within reach of knob-pointer error on a ±28 dB control (A2c). Fixing it properly means
    // replacing the power law with a real taper curve, as session 16 concluded for DRIVE.
    // ⭐⭐ SESSION 115 (Phase 10 C) — THE POWER LAW IS RETIRED. `masterTaperExp` NO LONGER EXISTS;
    // a stale `--fit masterTaperExp=` now fails loudly in offline_render rather than being
    // silently ignored, which is the failure mode this project keeps paying for.
    //
    // WHY THE FORM CHANGED, NOT THE VALUE. Session 41 fitted p over three points, all of them
    // referred to `master-1700_gain-n12_base-clean.wav`. GATE T (analysis/master_anchor_gate.py)
    // shows that file is a DUPLICATE of the 1545 capture at a knob position that is neither
    // detent — 4.447 dB below a true master-1700 — so it corrupted the taper AND the makeup.
    // (Session 112 read the same files as CLIPPED; that is refuted — the pinning is confined to
    // one segment, and the two files' offset is a pure gain across a 33 dB span of level, which
    // clipping cannot be.)
    //
    // On the corrected 9-detent ladder no power law fits at all: the per-point exponent runs
    // 1.795 / 2.343 / 2.652 / 3.073 / 3.489 / 3.513 / 1.742. A real audio ("A") taper is
    // MANUFACTURED as two linear resistive segments, and this pot measures like one.
    //
    //   fitted   : rms 1.28 dB, worst 1.96 dB   over the 7 interior detents
    //   shipped p=1.998 : rms 4.71 dB, worst 6.47 dB
    //   knob-repositioning noise floor, MEASURED from duplicate detents: 0.847 dB rms
    // ⇒ the old form sat at 5.6x the noise floor (a real, resolvable misfit); the new one sits
    //   at 1.5x it, i.e. as close as this ladder can resolve. Do NOT chase the residual — it is
    //   the knob, not the model. Derivation + all guards: analysis/master_taper_makeup.py.
    //
    // ⚠ Free corroboration nothing in the objective knew: the fitted curve passes 9.6% of full
    // resistance at HALF rotation, and a textbook audio taper is specified at 10-15%. circuit.md
    // calls VR8 a "100k A".
    //
    // ⚠ divRatio(0) is EXACTLY 0 by construction. The reference does NOT mute at master=0 (it
    // floors at -39.0 dB re full CW). That is deliberately not reproduced — MASTER is an [ENG]
    // stage absent from our schematic, our drawn divider really does go to zero, and a volume
    // control that cannot mute is a usability regression. Recorded as a departure, not an
    // oversight (reference-sources.md §1 makes the captures authoritative for pot laws, so this
    // is a knowing exception on one point).
    // ⭐⭐⭐ SESSION 146 — THE TWO-SEGMENT FORM IS RETIRED IN TURN; THIS IS NOW THREE SEGMENTS,
    // AND `masterTaperBreak` HAS CHANGED MEANING (first of two breaks, 0.5927 -> 0.3318).
    // ⛔ Do NOT read the s115 numbers above as current: rms 1.28 / floor 0.847 / 9.6% at half
    // rotation all belong to the retired two-segment fit. What survives from s115 is the FORM
    // argument (a real A taper is linear segments, not a power law) and the retirement of the
    // power law itself.
    //
    // WHAT CHANGED THE ANSWER: session 120 captured a COMPLETE second MASTER ladder at the
    // `gain-n18` send (s115 had it only at the top two detents), and the user stated which
    // knob positions are trustworthy: "0700, 1200, and 1700 are 100% trustworthy, all other
    // positions are best estimations."  Those three are exactly the positions where the pot has
    // a physical reference (both hard stops + the centre detent) — and the captures say so
    // without being told: across two sessions 12+ days apart the spread is 0.0000 dB at 0700
    // and 0.0000 dB at 1200, against 0.33-1.77 dB everywhere else. The files are confirmed
    // INDEPENDENT recordings, not digital copies (scalar-nulled they read -84..-86 dB, the same
    // floor as detents whose levels DISAGREE by 1.19 dB). Two separate sources, same answer.
    //
    // ⇒ THE FIT IS NOW A CONSTRAINT, NOT A LEAST-SQUARES OVER NINE EQUAL POINTS. Six of the
    // seven interior detents are ESTIMATES of a rotation, so their error is in x, not in y (the
    // LEVEL of every capture is exact — the pure-gain check reads 0.0002 dB band-span across
    // all nine). Averaging them in let six estimates outvote the one position that is known.
    //
    // THE DEFECT THAT FOUND, AND IT NEEDS NO FIT TO STATE: at MASTER noon the s115 taper is
    // 1.86 dB QUIET — 186x the pin's own uncertainty (0.010 dB, s112 recording repeatability,
    // reference-sources.md §0). Equivalently, in the units a pot taper is actually specified in:
    //     reference at half rotation  11.89 %   <- inside the textbook A-taper 10-15% band
    //     s115 model at half rotation   9.59 %   <- below it
    // circuit.md calls VR8 a "100k A". Nothing in any objective knew that.
    // ⭐ Independently corroborated by the s120 listening test ("MASTER: plugin needs ~0.61 to
    // match the pedal's loudness"): an ear said turn it UP at noon, and the captures say the
    // model is 1.86 dB short there. ⚠ That ear figure does NOT resolve the old flagged
    // coincidence with masterTaperBreak=0.5927 — the level-match rotation (0.5951) and the old
    // break sit 0.0024 apart, far below an ear's resolution of a knob position, so the
    // coincidence DISSOLVES (two indistinguishable explanations) rather than being decided.
    //
    // WHY THREE SEGMENTS AND NOT TWO PINNED. Pinning noon inside the two-segment family gives
    // xb 0.6115 / fb 0.1454 and puts the BOTTOM of the travel 1.4-3.4 dB hot, because segment 1
    // runs from the origin and a straight line cannot be convex. Measured, over the six
    // estimated positions (+ = model louder than capture):
    //     m          0.125  0.250  0.375  0.625  0.750  0.875     rms    bias
    //     s115      +0.45  +1.49  -0.47  +0.13  +1.52  -0.74    0.960  +0.399
    //     2-seg pin +2.31  +3.36  +1.39  -0.30  +1.41  -0.77    1.881  +1.232
    //     3-seg pin -0.52  +0.52  -0.36  -0.82  +0.31  -1.10    0.665  -0.329
    // The BIAS column is the diagnostic, not the rms: hand jitter has no preferred sign, so a
    // one-signed residual means the FAMILY is inadequate. Three segments absorbs it.
    //
    // ⚠⚠ THREE PARAMETERS AGAINST SIX ESTIMATED POINTS IS WHERE OVERFITTING LIVES, so the
    // candidate is NOT justified by its rms (extra freedom always buys rms). It ships because
    // THREE things hold at once and only the third is a fit statistic:
    //   (i)   EXACT at the one trusted interior position — a constraint, not a fitted target;
    //   (ii)  segment slopes RISE monotonically, 0.172 -> 0.368 -> 2.413, i.e. a convex,
    //         physically-buildable resistive track; the tool FAILS if convexity is lost;
    //   (iii) it fits the estimated positions better than the incumbent (0.665 vs 0.960 rms)
    //         while CARRYING a constraint the incumbent does not.
    // ⛔ Do NOT "improve" this by adding a fourth segment — (iii) is already below the 1.075 dB
    // knob floor, so any further rms gain is fitting the hand that turned the knob.
    //
    // ⚠ The knob-repositioning floor is 1.075 dB rms / 1.770 worst over FREE positions (n=5),
    // NOT s115's 0.847: that figure pooled the free positions with the 0700 hard stop reading
    // exactly 0.000, which deflates an rms. The two populations are split on a PHYSICAL
    // property (does the pot have a reference here?), established by GATE S3 (s113) before any
    // spread here was read — not on the spreads themselves.
    //
    // ⚠ divRatio(0) is still EXACTLY 0, unchanged and still a knowing departure — see the note
    // above. Derivation + all guards: analysis/master_taper_makeup.py, report
    // analysis/reports/s146_master_recal.json.
    double masterTaperBreak = 0.331781;   // rotation at which the wiper reaches masterTaperFrac
    double masterTaperFrac = 0.056905;    // fraction of full resistance at that rotation
    double masterTaperBreak2 = 0.659183;  // rotation at which the wiper reaches masterTaperFrac2
    double masterTaperFrac2 = 0.177468;   // fraction of full resistance at the second break

    // ---- C21 (100n) inter-stage coupling into the tone stack ----------------
    // The 100n cap is schematic-verified; the resistance it works against is the
    // tone stack's effective INPUT impedance, which is a nominal ~10k estimate,
    // not a single schematic part. It sets a ~159 Hz highpass that audibly shapes
    // bass, so it is a real fit knob (fit alongside the tone stack).
    double c21R = 130.0e3;  // session-91: RE-AIMED AT HARDWARE (was 220k, session-28 A2d; 100k
                            // session-18; nominal 10k). Corner ~12.2 Hz (was 7.2).
                            //
                            // ⭐ THE REFERENCE CHANGED, NOT THE MEASUREMENT. Everything below this
                            // paragraph is the session-28 fit against the ND captures, and it is
                            // still correct AS A FIT TO ND — 220k really is where the ND captures
                            // put this corner. What changed is that `analysis/captures/` was
                            // confirmed (session 71) to be a recording of the Neural DSP plugin,
                            // and `.claude/rules/reference-sources.md` §1 makes HARDWARE the
                            // authority for "broadband linear tilt, LF and HF corners". §2's
                            // hardware column is 1.1 dB below ND at 20 Hz where 220k had us
                            // matched to ND at -0.4. So this is a deliberate, priced departure
                            // from the captures toward hardware — a PASS under §5 rule 2, NOT a
                            // correction of session 28.
                            //
                            // DERIVED, NOT TRANSCRIBED: `analysis/c21_hw_anchor.py` (6 known-answer
                            // gates) fits the corner over every §2 LF anchor. ⚠ The target is
                            // `HW - MODEL`, not §2's published `HW - ND`: measured over the 168
                            // CLEAN rows of s90_baseline129_h1.json the model was ALREADY 0.40 dB
                            // below ND at 20 Hz and 0.16 at 30 Hz, so a third of the move was
                            // already made by other constants. Fitting the raw §2 delta gives
                            // 121k and OVERSHOOTS; fitting the remainder gives 133.1k / 11.96 Hz,
                            // nearest E24 130k. (The session-71 handover's flagged "130-150k"
                            // brackets this while being derived from ONE frequency and the raw
                            // delta — agreeing with a recorded range is not evidence the
                            // derivation was sound.)
                            //
                            // MEASURED at 130k, 129 captures, 504 rows, membership identical:
                            //   * hardware: worst remaining error vs §2 0.70 -> **0.17 dB**
                            //   * OD IMPROVES on every gate row (the OD path's LF ran hot vs ND —
                            //     the A3/GAP #3 symptom — and this pulls it down): band-RMS
                            //     2.697 -> 2.652, OD 25-100 Hz median 1.13 -> 1.03, OD
                            //     100 Hz-8 kHz p90 5.27 -> 5.05, THD level 6.20 -> 6.16, OD tilt
                            //     1.97 -> 1.46.  219/320 OD rows improve; worst OD row +0.07 dB.
                            //   * CLEAN pays: median 0.23 -> 0.26, p90 0.77 -> 0.82 (over its 0.80
                            //     bar), band-RMS 0.432 -> 0.453.  Confined to 25-100 Hz (that
                            //     region's p90 0.67 -> 0.84); 100 Hz-8 kHz IMPROVES 0.73 -> 0.72
                            //     and 8-16.3 kHz is unchanged.  No row worse by >0.5 dB.
                            //   * bypass.wav is bit-identical in all 4 sweeps — inert BY
                            //     CONSTRUCTION (chain out of circuit), the known-answer control.
                            // 150k was also rendered (s91_c21_150k.json): it keeps CLEAN p90 at
                            // exactly 0.80 but takes only 55 % of the hardware move (0.32 dB) and
                            // is OUTSIDE what either individual §2 anchor asks for (139k @20 Hz,
                            // 116k @30 Hz) — chosen to protect a gate row, not supported by the
                            // reference. Rejected with the user, session 91.
                            //
                            // ---- the session-28 ND fit, retained as the record of record ----
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
    // ⭐ SHIPPED SESSION 100 at 15372.9 (was 30k). Session 62 predicted this constant would
    // stop being one shared value and become the switched pole B, and that is what landed:
    // it now sets only the FLAT throw, with attackDampBoost/attackDampCut overriding the
    // other two (7055.36 / 118.022). See the session-100 block under the ATTACK tap below.
    double trebleLadderDampR = 15372.9;  // ohms; s99. Session-19 Phase-9 A/B fit was 30k (was implicit 0).
                            // Fit on the clean OD captures (notch region 127-640 Hz):
                            // low-mid RMS 3.64 -> 1.96 dB across 6 flat-EQ OD captures, HF
                            // (1-6 kHz) cost only +0.11 dB (the knee; 40k trades +0.12 HF for
                            // -0.09 more low-mid). Shallows the 322 Hz notch from ~28 dB to a
                            // capture-like depth. ⚠ 30k is LARGE for literal cap ESR — the
                            // physical origin (why the ideal notch is far too deep; tolerance
                            // ruled out) is a schematic-checker follow-up, but dsp.md makes the
                            // capture authoritative on the notch depth (like c21R's 10x corner).
                            // ⭐ UPDATE (session 62): this constant is what GAP #2 and ATTACK have
                            // in common. 30k destroys the notch (session 46), and the ATTACK
                            // proposal wants it to STOP being one constant and become the switched
                            // pole B — 6.14k flat / 478 boost / 6.04k cut. It still sets ALL THREE
                            // throws (setNotchDamp); attackDampBoost/attackDampCut override one.

    // ---- The TWO-POLE ATTACK topology (TrebleAttack.h, Phase 9 / A3 step 19-20)
    // ⚠ ATTACK is [ENG] — the 3-way switch is not on our schematic, so these
    // PROPOSE a topology rather than correcting a drawn one. EVERY DEFAULT BELOW
    // REPRODUCES THE DRAWN NETWORK EXACTLY, so leaving them alone is a true no-op:
    // the tap collapses onto node P and the notch leg is position-independent.
    //
    // WHY (docs/phase9-validation.md §4 "A3 step 17/19"): measured bleed-free at
    // LEVEL max / drive min, ATTACK does TWO things at once — a broadband gain of
    // +8.65 / -2.39 dB (boost/cut re flat, flat to ~1 dB over 80 Hz-1.6 kHz) AND a
    // cancellation null that moves 316.4 / 328.1 / 334.0 Hz with depth >= 14.9 /
    // 32.7 / 16.0 dB. Session 61 refuted every family in which the switch changes
    // one element VALUE on a SIGN (0 of 782 random draws reproduce the pattern; in
    // that topology the cut throw can only move the null UPWARD), and session 62
    // showed the two halves are carried by three provably NON-INTERACTING groups —
    // the tap divider owns the gain (d f0 0.01-0.02 Hz), Rd owns the depth (d h
    // 0.00 dB), the ladder RC owns the frequency (d h 0.00 dB). Hence two poles.
    //
    // Session 62's proposed point, for reference (NOT the defaults — the matrix is
    // the arbiter, as it was for btC17 and clipC15):
    //   attackTapRa/Rb/Rc/R11 = 470k / 506k / 78.5k / 212k
    //   trebleC5 = 19.7n, attackC5TrimBoost = +1.1n, attackC5TrimCut = +2.7n
    //   trebleLadderDampR = 6.14k (flat), attackDampBoost = 478, attackDampCut = 6.04k
    //
    // ⚠ ONLY RATIOS ARE IDENTIFIED. `h` is a ratio between switch positions, so any
    // element common to all three throws cancels out of the measurement BY
    // CONSTRUCTION — Ra duly parked on whichever bound it started nearest (100 ohm
    // and 10 Mohm scored identically) until it was pinned to the drawn R8. The
    // proposal also wants the tap-to-ground resistance to sum to ~797k against the
    // drawn R11 = 470k; since the switch is [ENG] the surrounding rail is a proposal
    // too, but state that rather than bury it.
    // ⭐⭐ SHIPPED SESSION 100 — the whole 17-value ATTACK/treble-ladder block below is
    // the session-99 fitted candidate, landed on the user's explicit re-authorisation to
    // break from the schematic where the reference requires it (the session-51 standing
    // authorisation, reaffirmed at the top of session 100). READ THIS BEFORE READING ANY
    // "the drawn X" COMMENT BELOW — those describe the PRIOR defaults, not what ships.
    //
    // ⚠⚠ WHAT THIS IS, AND WHAT IT IS NOT. It is an **OD-path ABSOLUTE-LEVEL fix that
    // happens to live in the ATTACK ladder**. It is NOT a 320 Hz notch fix, and it does
    // NOT close GAP #2 — measured, the 320 Hz band moves only 9.54 -> 9.21 dB mean |Δ|
    // over the same 320 OD rows, and the notch requirement it was built for is still
    // UNMET (width 1.28/1.46/1.38x, depth +4 dB). Do not book it against GAP #2.
    // What it actually fixes: the prior default sat **9-12 dB light at every sub-band on
    // the ATTACK BOOST throw** (cut was already right and stays so; flat improves):
    //     pedal - render, boost throw, bleed-free:  LF +10.90  LM +11.68  M +10.69  HM +9.19
    //     after:                                       +0.53      +1.36     +0.50     +0.64
    //
    // THE 129-CAPTURE MATRIX ACCEPTS IT — the first ATTACK candidate in the project's
    // history it has not refused, beating the s91 baseline on 8 of the 9 gated OD/THD
    // statistics (504 shared rows, membership identical, CLEAN **bit-identical**):
    //     OD band-RMS ex gain-n12   2.664 -> 2.409     THD (OD) level  4.279 -> 3.663
    //     OD 25-100 Hz  med/p90     1.024/6.065 -> 0.860/4.971
    //     OD 100 Hz-8k  med/p90     0.742/5.089 -> 0.568/4.458
    //     OD 8-16.3 kHz med/p90     0.662/8.076 -> 0.566/8.058
    //     OD p99  14.408 -> 14.661  ⚠ the ONLY gated statistic that got worse
    //     rows better >0.5 dB / worse:  111 / 36
    //
    // ⭐ It is also the cleanest candidate the project has produced on the identifiability
    // axes: **0 of 17 values rest on a bound**, realisable, worst shared re-scale x15.8 —
    // and `C7` comes back to x1.11, i.e. essentially its prior value, from the s97 point's
    // x0.244 (the element session 94 attributed about half its matrix regression to).
    //
    // ⚠ HOW IT WAS FOUND, AND WHY THE EARLIER "REACHABLE" RESULTS ARE CORRECTED, NOT
    // BEATEN. Sessions 94 and 97 both reported the corrected ATTACK requirement REACHED
    // (width rms 0.34 and 0.41). Both were scored by objectives that could not see the OD
    // path's absolute low-end level, and both had quietly PAID for the notch shape with
    // it — measured per sub-band, their LF residual is **-42 dB** and **-22 dB**. Give the
    // objective an LF-visible term (session 99's per-sub-band `g`) and the same search
    // reaches LF to -1.4 dB while width collapses 0.41 -> 4.25, in ALL TEN rows of a sweep
    // spanning 100x in f0 weight and 3x in box. That is saturation, not a weight choice:
    // **the notch width/depth and the absolute OD level are in genuine CONFLICT in this
    // topology.** If the notch itself is wanted, it is now a TOPOLOGY question (a missing
    // degree of freedom), not a fitting one — do not point another search at it.
    //
    // Provenance: analysis/attack_shape_screen.py --best (per-sub-band `g`, GATE F1-F5) ->
    // analysis/attack_d_extrapolation_gate.py (GATE H, REQUIRED: `g` is an extrapolation
    // at 1.20 decades against F4's tested 0.23) -> analysis/attack_stepped_gate.py
    // --fits-json -> the 129-capture matrix. Reports: s99_attack_best_subband.json,
    // s99_d_extrapolation.json, s99_attack_stepped_cand.json, s99_attack_cand.json.
    double attackTapRa = 392663.0;   // ohms; M -> T1 (boost tap).  s99 (was 470k = the drawn R8)
    double attackTapRb = 420440.0;   // ohms; T1 -> T2 (flat tap).  s99 (was 0 = taps collapsed)
    double attackTapRc = 77481.0;    // ohms; T2 -> T3 (cut tap).   s99 (was 0 = taps collapsed)
    double attackTapR11 = 163933.0;  // ohms; T3 -> GND.            s99 (was 470k = the drawn R11)

    // Pole B, the notch leg. `trebleC5` is the base cap (all positions); the two
    // trims are ADDITIVE, i.e. a small parallel cap selected by the same pole —
    // which is how a +-7 % move should be realised, not as three graded caps.
    // ⚠ THE TRIMS MUST BOTH BE >= 0 AND FLAT MUST BE THE SMALLEST OF THE THREE THROWS —
    // there is no `attackC5TrimFlat`, so a fitted point whose flat C5 is not the smallest
    // CANNOT BE EXPRESSED HERE. The screen printed that warning for 35 sessions without
    // ranking on it and duly selected an unrealisable point the moment an unrelated
    // ranking fix changed the winner (session 97); `realisable()` is now the FIRST term of
    // its key. The s99 point below is realisable — cut 8.277n / boost 8.058n / flat 7.957n.
    double trebleC5 = 7.95747e-9;         // farads; s99 (was 22n, the drawn C5) = flat throw
    double attackC5TrimBoost = 1.00053e-10;  // farads added to trebleC5 in the BOOST throw; s99 (was 0)
    double attackC5TrimCut = 3.19622e-10;    // farads added to trebleC5 in the CUT throw;   s99 (was 0)

    // Per-throw damping. NEGATIVE = "inherit trebleLadderDampR" (the sentinel keeps
    // every existing `--fit trebleLadderDampR=` tool behaving exactly as before —
    // it still sets all three throws). A negative resistance is physically
    // meaningless, so the sentinel is unambiguous.
    double attackDampBoost = 7055.36;  // ohms, or < 0 to inherit trebleLadderDampR; s99 (was -1)
    double attackDampCut = 118.022;    // ohms, or < 0 to inherit trebleLadderDampR; s99 (was -1)

    // C8 — the 220 pF cap the DRAWN switch reroutes. Fittable ONLY so that the
    // two-pole proposal, which does not use C8 at all, can actually be rendered:
    // attack_tap_screen.py screened it at C8 = 0, so a render that leaves 220 pF in
    // is NOT the thing that was screened. kC8 (220p) = the drawn stage.
    // ⚠ SHIPPED AT 0 IN SESSION 100. The two-pole ATTACK topology does not use C8 at all,
    // and every screen that produced the shipped point ran at C8 = 0 — a render leaving
    // 220 pF in is NOT the thing that was screened, measured or accepted by the matrix.
    double trebleC8 = 0.0;           // farads; s99 (was 220p = the drawn C8). kC8 = the drawn stage.

    // ---- The SHARED treble ladder (TrebleAttack.h::setLadder) ----------------
    // Session 50's next-step (a), open from session 50 to 63: R7 and the C9/C6 +
    // R12/R14 ladder were `static constexpr` and reachable from NO analysis tool, so
    // no A3 screen could render a candidate that moved them.
    //
    // WHY THEY ARE REACHABLE NOW (session 64). Session 63's two-pole ATTACK topology
    // matches the null's (f0, depth) to the BIN at all three throws while every null
    // is ~2x too BROAD — half-depth width 150.6 / 59.6 / 138.6 Hz against the pedal's
    // 77.9 / 27.1 / 71.9 (cut/boost/flat). A ~2x error that is nearly UNIFORM across
    // three throws cannot be per-throw (the throws differ only in pole B), so the
    // width lever must be SHARED — and these five values are the shared set.
    //
    // ⚠ ALL FIVE ARE SCHEMATIC-VERIFIED (circuit.md; covered by the R1-R54 / C1-C39
    // BOM reconciliation), so moving one is a capture-vs-document disagreement of the
    // same class as trebleC7 (147x), c21R (10x) and trebleWiperR (1.4x) — not a bug
    // fix.
    // ⚠ CORRECTED SESSION 100: this paragraph used to end "Defaults are the drawn values
    // and a default render is BIT-IDENTICAL to the pre-session-64 stage (TrebleAttackTest
    // Test 10)." THE FIRST CLAUSE IS NO LONGER TRUE — all five ship moved (below). The
    // second clause was never about FitParams: Test 10 compares the TrebleAttack STAGE's
    // own internal defaults (kR7/kR12/kR14/kC9/kC6) against explicit drawn values, so it
    // still passes and is still meaningful, but it does NOT certify the shipped constants.
    //
    // ⚠ AND THE SENSITIVITY CENSUS SAYS DO NOT EXPECT A FREE LUNCH (session 64,
    // `analysis/attack_shape_screen.py --census`): every one of these moves the null's
    // WIDTH and its FREQUENCY together, at ~0.5-1.5 Hz of width per Hz of f0, and f0
    // currently matches to the bin. Only C7 is width-selective (11.4 Hz of width per
    // Hz of f0) and its authority is small. The tap divider (attackTapRa/Rb/Rc/R11) is
    // width-NEUTRAL to <=0.5 Hz, which extends session 62's pole-independence result
    // to the width statistic.
    // ⚠⚠ ALL FIVE MOVED IN SESSION 100 (the s99 point) AND ALL FIVE ARE SCHEMATIC-VERIFIED,
    // so this is the largest single departure-from-the-drawn-network in the project — five
    // BOM-reconciled values at once, C6 by a factor of 16. It is a deliberate, authorised,
    // priced departure, NOT a bug fix, and it is what carries the OD-level repair above.
    // The multipliers are against the drawn values, and the worst of them (x8.23) is the
    // MILDEST shared re-scale of any ATTACK winner the project has produced.
    double trebleR7 = 1.64563e6;        // ohms; s99, x8.23 (drawn R7 = 200k;   G -> M on the top rail)
    double trebleLadderR12 = 27131.0;   // ohms; s99, x3.99 (drawn R12 = 6.8k;  L1 -> GND)
    double trebleLadderR14 = 48500.9;   // ohms; s99, x2.20 (drawn R14 = 22k;   L2 -> GND)
    double trebleC9 = 1.28153e-8;       // farads; s99, x0.583 (drawn C9 = 22n; L1 -> L2)
    double trebleC6 = 1.39228e-9;       // farads; s99, x0.0633 (drawn C6 = 22n; L2 -> M)

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
    // ⭐ SESSION 100 moved it only x1.11, to 755.764p, as part of the s99 ATTACK/ladder
    // point. That mildness is a RESULT, not an accident: session 94's rejected candidate
    // wanted C7 x0.1 and session 97's x0.244, and session 94 attributed about HALF its
    // +27 dB matrix regression to that element alone. The candidate the matrix finally
    // accepted leaves C7 essentially where session 35 put it. Everything above still
    // stands — the 147x-vs-schematic story, and the owed schematic-checker pass.
    double trebleC7 = 755.764e-12;  // farads; s99, x1.11 of the s35 680p. Schematic/BOM is 100n (see above)

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

    // ---- clipAdaa: 1st-order ADAA on the CD4049 VTC (session 123; SHIPPED s124) ---
    // 0 = Off      (the pre-session-124 default; bit-identical to the s122 build)
    // 1 = Full     (average the whole VTC) ** SHIPPED **
    // 2 = Residue  (average only its nonlinear part) ⛔ REFUTED — see below
    // ⛔⛔ MODE 2's OWN DESCRIPTION IN THIS FILE USED TO READ "the one to prefer".
    // THAT IS REFUTED (session 123) AND THE LINE OUTLIVED ITS OWN REFUTATION BY A
    // SESSION — a `verify-the-PREMISE` occurrence inside the file that defines the
    // constant. Clipper.h::setADAA carries the one-line algebra: averaging only the
    // nonlinear part evaluates the two halves of ONE map half a sample apart, which
    // injects a first difference of gain a0/2, and |0.5*a0*(1 - z^-1)| reaches the
    // FULL loop gain at Nyquist at every sample rate. Measured: H1 +13.4 dB hot, alias
    // floor 14.4 dB WORSE than Full — whose own 2-point-average cost, the thing
    // Residue exists to avoid, is 0.01 dB of harmonic power and 0.2 dB of H2/H1.
    // ⇒ mode 2 is kept SELECTABLE only so that refutation stays reproducible; it is
    // not a better Full. Do not "upgrade" to it on the strength of its name.
    // ⚠ SILENTLY INERT UNLESS clipK == 2.0. Clipper::adaaExact() gates on it because
    // sigma_k's primitive is elementary only at k = 2 (and k = 1) — so a k != 2 build
    // gets NO ADAA whatever this is set to, deliberately: a stale flag can never
    // produce a WRONG antiderivative, only no antialiasing. That guard is now belt and
    // braces rather than the operative one, because session 124 ships clipK = 2.0.
    int clipAdaa = 1;

    // ---- clipAdaaMaxOs: the OS-FACTOR GATE on the above (session 124) ------------
    // ADAA applies only where the OD region's oversampling factor is <= this. The
    // shipped 2 means ON at 1x/2x, OFF at 4x/8x. This is a MEASURED policy, not a
    // taste. GATE X X6, Full vs its OWN k=2 baseline, 19 usable bin-exact tones per
    // cell (2 degenerate tones excluded — a tone dividing fs puts every fold on a
    // harmonic bin, so inharmonic content is impossible BY CONSTRUCTION and its
    // spectacular reading means nothing), alias-floor change in dB, negative = better:
    //        OS    median(amp .35 / .70)   WORST tone      improved
    //        1x      -19.50 / -18.74       +1.96 / +2.53   95 % / 95 %
    //        2x      -12.57 / -19.75       +3.33 / +3.23   84 % / 89 %
    //        4x       -2.38 /  -8.71       +9.88 / +2.81   68 % / 89 %
    //        8x       -4.62 /  -0.50       +0.73 / +17.33  89 % / 63 %
    // ⇒ at 1x/2x the median is a large win and the WORST case is bounded at +3.3 dB;
    // at 4x/8x the median collapses AND the worst tone costs +9.9 / +17.3 dB. ADAA1
    // carries its own first-order residual, so once oversampling has already taken the
    // floor low there is nothing left to win and the residual is all that is left to
    // pay. The gate buys the top two rows and declines the bottom two.
    // ⚠ Read the WORST column, not only the median — that is what makes this a policy
    // rather than an average. And note it is NOT monotone in OS (8x beats 4x at amp
    // .35, loses badly at .70): the honest statement is "1x/2x win, 4x/8x are a
    // coin-toss with a bad tail", not "benefit decreases with rate".
    // ⛔ Do NOT enable it flat across all factors on the strength of the 2x number —
    // that is the specific error session 123 pre-registered against.
    // ⚠ Corroborated by an instrument sharing nothing with the alias metric: node W's
    // mean step/knee ratio falls 5.76 -> 2.84 -> 1.42 over 2x/4x/8x (Clipper.h
    // setADAA's in-chain table). Crossing the whole knee in one sample is ADAA1's best
    // case and oversampling's worst, so the two orderings agreeing is not a
    // coincidence — it is the mechanism showing up twice.
    // ⭐⭐ THE GATE LANDS ON THE PLUGIN'S OWN DEFAULTS, WHICH IS WHY IT IS WORTH HAVING
    // AT ALL RATHER THAN BEING A CORNER CASE. PluginProcessor's `oversampling` choice
    // defaults to index 1 = **2x** (the realtime path) and `render_oversampling` to
    // index 3 = **8x** (offline bounce). So out of the box the realtime path GETS ADAA
    // — exactly where the alias floor is worst and CPU is scarcest — and the offline
    // render does not, because at 8x oversampling has already taken the floor to
    // -63 dB and ADAA1's residual is all that is left to pay. ⇒ this is not "a feature
    // that happens to be on at some settings"; it is on at the setting nearly every
    // user runs. ⚠ If either default ever moves, re-read this: the policy's value is
    // tied to them, and moving the realtime default to 4x would silently switch ADAA
    // off for everyone.
    // ⭐ SET IT TO 8 TO FORCE ADAA AT EVERY FACTOR — which is exactly what GATE X's
    // 4x/8x arms need, and why this is a knob rather than a hardcoded `if`. 0 disables
    // ADAA everywhere without disturbing clipAdaa's recorded mode.
    // ⚠ The matrix renders at os_factor 8, where this gate turns ADAA OFF. So the
    // shipped build's matrix grade is `s123_k2.json` (k=2, ADAA off) and NOT a new
    // number — asserted as a known answer in session 124, not assumed.
    int clipAdaaMaxOs = 2;

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
