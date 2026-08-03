#pragma once

#include <cmath>

// =============================================================================
// Stage 5 — CD4049UBE CMOS-inverter clipper (IC3) + GRUNT bank  [THE distortion]
// =============================================================================
// circuit.md "CLIPPER" + "GRUNT switch". The audible overdrive of the pedal.
// A single unbuffered-CD4049 inverter section wired as a shunt-feedback inverting
// amp, self-biased to its own transition point, clipping softly against its own
// (R19-dropped) CMOS rails. NOT a diode clipper — D1/D2 are rail clamps at node W
// that never conduct in normal operation.
// ⚠ That last clause was FALSE for the shipped build from session 44 to 117: the
// clamp window was derived from the FITTED satLo and duly fired on up to 7.6 % of
// samples. Fixed in session 118 by anchoring it on the physical trip point — see
// kTripPointV below for the measurement, the cost, and why the per-stage test did
// not catch it (it exercises the NOMINAL constants, not the shipped fit).
//
//   GRUNT bank : C11(4n7) always + C12(47n)/C13(220n) switched in parallel -->
//                the "coupling cap" Cg feeding R16 (three bass-content levels).
//   R16 = 6k8  : clipper input resistor (Cg + R16 in series into node W).
//   IC3        : one CD4049UBE inverter section (pin3 = W in, pin2 = Y out).
//   R18 = 330k : shunt feedback (Y -> W).
//   C14 = 220pF: || R18, HF rolloff of the feedback.
//   D1 = 1N4148: anode W, cathode +9V  -> clamps W <= ~+9.6 V  (rarely conducts)
//   D2 = 1N4148: anode GND, cathode W  -> clamps W >= ~-0.6 V  (rarely conducts)
//
// ---- Model: finite-gain coupled VTC (nonlinear-component-modeling.md §1) -----
// The doc's RECOMMENDED approach: a static asymmetric-sigmoid inverter VTC inside
// the shunt-feedback loop, solved with the 4049's FINITE open-loop gain A0 (~20-30
// on real CMOS B7K/B3K stages) rather than an ideal virtual ground. Finite gain is
// NOT a refinement here — it is load-bearing voicing:
//   * The GRUNT high-pass corner is 1/(2*pi*Cg*(R16 + R18/(1+A0))). The input-node
//     impedance R18/(1+A0) dominates the RC, dragging the corner FAR below the
//     ideal-virtual-ground 1/(2*pi*Cg*R16): with A0=25, ~900/144/36 Hz (-3 dB)
//     vs the ideal 4980/453/104 Hz (circuit.md GRUNT note — ideal-vg is audibly
//     wrong). So R16 + Cg-bank + the finite-gain VTC + R18||C14 are ONE coupled
//     stage, not "HPF then waveshaper".
//   * Finite gain also lowers the closed-loop mid-band gain below the ideal
//     -R18/R16 = -48.5 (with A0=25, HF plateau ~ -16). circuit.md's -48.5 is the
//     ideal-A0 upper bound.
//
// Per-sample this is an implicit equation (W depends on Y = VTC(W) and vice versa
// through the feedback), so it is solved by BRACKETED Newton with a bisection
// fallback on node W — cheap (F is nearly linear except in saturation; warm-started
// from the previous sample, mean 2.7-3.0 iterations measured across the whole OS x
// drive plane). ⚠ It was a PLAIN Newton loop until session 120, and plain Newton is
// not globally convergent on a sigmoid however monotone F is; see kNewtonIters for
// the measured defect that cost. Both reactive elements (Cg, C14) are trapezoidal companion caps,
// same convention as every other stage (JfetStage/DriveStage/MasterOut).
//
// ---- Node-W KCL (VD-referenced internally: 0 = the inverter trip point Vm) ----
// Both ports are AC-coupled (Cg on the input, C15 on the output belongs to the
// recovery stage), so we work in a frame where quiescent W = Y = 0 (the self-bias
// trip point). The inverter input draws no current:
//   i_in + i_fb = 0
//   i_in = G_in*(x - W) - Ic          (series Cg+R16 branch, Norton-reduced; the
//                                       intermediate node between Cg and R16 is
//                                       eliminated algebraically)
//   i_fb = g_fb*(VTC(W) - W) - ieq14  (R18 || C14)
//   F(W)  = G_in*(x - W) - Ic + g_fb*(VTC(W) - W) - ieq14  = 0
//   F'(W) = -G_in + g_fb*(VTC'(W) - 1)
//
// ---- Polarity (dsp.md "Dry/wet phase alignment ... Polarity") ---------------
// A CMOS inverter INVERTS: +in edge -> W rises -> Y = VTC(W) falls. This is the
// confirmed inversion the OD path carries into the BLEND node ALONGSIDE the J201
// stage's inversion (JfetStage). DC-step test confirms +in -> -out on the AC edge
// (AC-coupled both ends -> decays to 0). The end-to-end DC-step at BLEND runs in
// Phase 6; the clipper's own sign is not an open unknown.
//
// ---- Why NO RailClamp -------------------------------------------------------
// RailClamp models a TL07x OP-AMP output hitting its rails. IC3 is NOT an op-amp —
// its VTC IS the soft limiting (the whole point of the stage). The R19-dropped
// effective rail is folded into the VTC saturation levels (kSatLo/kSatHi).
//
// ---- ** NOMINAL amplitude params — FIT TO CAPTURE AT PHASE 7 ** -------------
// Trustworthy pre-capture: the R/C corner SHAPES, the finite-gain COUPLING form,
// and the INVERTING polarity. Everything amplitude-related is nominal:
//   kA0     open-loop gain (governs BOTH gain and the GRUNT corners) — the primary
//           capture-fit param; community-measured ~20-30. Fit from the GRUNT-corner
//           voicing + the drive-sweep level.
//   kSatLo/kSatHi  per-side VTC saturation (VD_eff-referenced volts of output swing
//           toward the GND / +VDD rail). Asymmetric by design (n-ch vT~1.57 vs
//           |p-ch|~0.48 -> the even harmonics the doc requires). Their sum is the
//           R19-dropped effective rail (nominal ~7 V, below the 8.6 V op-amp rail).
//           Fit to the drive-sweep Farina THD(f) + low-freq-tone H2/H3 asymmetry.
//   kHardness  VTC knee hardness `k` (session-11 addition): decouples how ABRUPT
//           the transition-region knee is from the small-signal gain a0 — see
//           the vtc() note. Fit to the drive-sweep harmonic-to-harmonic ratios.
// The stage is structured so refitting these is a constants-only change that never
// disturbs the (correct) linear corner shapes or the polarity. Oversampling + ADAA
// wrap this stage in Phase 6 (it is the chain's hardest aliaser); the per-side
// k=2 sigmoid has a closed-form antiderivative ((sat^2/a0)*(sqrt(1+u^2)-1) per
// side, replacing the old tanh's sat^2/a0 * ln cosh) for cheap ADAA.
// =============================================================================
class Clipper
{
public:
    // ---- Component values (circuit.md CLIPPER + GRUNT tables) ---------------
    static constexpr double kR16 = 6.8e3;    // clipper input resistor
    static constexpr double kR18 = 330.0e3;  // shunt feedback
    static constexpr double kC14 = 220.0e-12; // feedback HF rolloff
    static constexpr double kC11 = 4.7e-9;   // GRUNT: always present
    static constexpr double kC12 = 47.0e-9;  // GRUNT: added in the "medium" pos
    static constexpr double kC13 = 220.0e-9; // GRUNT: added in the "most" pos

    // ---- NOMINAL amplitude placeholders — FIT TO CAPTURE AT PHASE 7 ---------
    // These stay as the documented NOMINAL values (and are what the per-stage
    // test uses as its oracle); the live values are the settable members below,
    // initialised from these. See FitParams.h for why they are runtime-settable.
    static constexpr double kA0 = 25.0;      // 4049 open-loop gain (voicing-critical)
    static constexpr double kSatLo = 3.15;   // output swing toward GND rail (= Vm)
    static constexpr double kSatHi = 3.85;   // output swing toward +VDD rail (asym)
    // VTC knee hardness `k` (session-11 reshape — see vtc() below). k=2 is the
    // ANCHOR: f_2(u) = u/sqrt(1+u^2) has the elementary antiderivative
    // sqrt(1+u^2), preserving the stage's closed-form ADAA option (k=1 also
    // works: u - ln(1+u)). Do NOT ship an arbitrary fitted k as this default
    // without checking its antiderivative stays closed-form (dsp.md trap class).
    static constexpr double kHardness = 2.0;

    // ** SESSION-118: the inverter TRIP POINT, decoupled from the fitted VTC
    // amplitude. This is a PHYSICAL constant and must NOT track a fit. **
    // Node W is worked in a frame where 0 = the self-bias trip point Vm, so the
    // absolute node voltage is W_abs = w + Vm and the 1N4148 rail clamps are
    //   D1: W_abs <= +9.6  ->  w <=  9.6 - Vm
    //   D2: W_abs >= -0.6  ->  w >= -0.6 - Vm
    // Vm comes from circuit.md's self-consistent R19-dropped supply solve
    // (session 42, analysis/clipper_rail_selfconsistent.py): the CD4049's own
    // crowbar current through R19 settles at VDD = 5.636 V with the shunt-feedback
    // self-bias point at Vm = 2.657 V. It is a property of the DEVICE and its
    // supply dropper, not of how the VTC's knee was fitted.
    //
    // ⛔⛔ WHY THIS IS NOT `kSatLo` ANY MORE — SESSION-118 BUG FIX, and the old
    // comment right here ("these essentially never fire (the test asserts it)")
    // WAS FALSE FOR THE SHIPPED BUILD FOR 74 SESSIONS. The window used to be
    // derived as `±rail - satLo`, on the reasoning that for a CMOS inverter
    // swinging rail-to-rail the output swing toward GND *is* the trip point. That
    // identification is sound for the NOMINAL values (kSatLo = 3.15 = 7.0/2) and
    // it broke the moment satLo stopped being an output swing: session 44's A5
    // re-fit made satLo a fitted KNEE SCALE and moved it 3.15 -> 0.4377 V (their
    // sum, 1.036 V, is only 18 % of the 5.636 V rail — FitParams.h already flags
    // that as a soft-low). The clamp window silently followed it from
    // [-3.750, +6.450] to [-1.038, +9.162], i.e. the D2 floor moved 2.71 V IN
    // TOWARD the region node W actually occupies.
    // MEASURED (session 118, temporary in-chain instrumentation over 10 matrix
    // conditions x OS 2 and 8, ~32 M clipper samples each): D1 never fires
    // anywhere, and D2 fires on 0.39 % (ref-od, DRIVE noon) to 7.61 % of samples,
    // rising monotonically with how hard the clipper is pushed —
    //   DRIVE min 0.00 | DRIVE noon 0.39 | 1430 1.66 | DRIVE max 3.48 |
    //   attack-boost 5.32 | grunt-flat 6.53 | grunt-boost 7.01   (OS 8)
    // ⚠⚠ AND THE FIRST VERSION OF THIS NOTE OVERCLAIMED, BECAUSE THE ENVELOPE WAS
    // MEASURED THROUGH THE LIMITER UNDER TEST. With the old clamp ACTIVE the node
    // reads [-2.458, +5.417] V, which sits inside [-3.257, +6.943] and looks
    // comfortably inert. It is not: the old clamp was itself holding the negative
    // excursions down. Re-measured with the corrected window in place, the true
    // envelope is [-3.927, +5.127] V, so D2 still fires — on 0.05-0.25 % of
    // samples (OS 8) against the old 0.39-7.61 %, i.e. a 30-70x reduction, not
    // elimination. **An excursion envelope measured with a limiter engaged
    // understates the envelope that limiter would see if removed.**
    // ⛔ The residual is NOT a reason to widen this number further. It is the
    // known soft-low clipSat showing through: the fitted VTC saturates at
    // |w| ~ satLo/a0 ~ 0.018 V, so past that the node runs away almost linearly
    // and reaches excursions a physically-scaled ceiling (VDD 5.636 V) would never
    // permit. Fixing THAT is a re-fit of the whole K/clipSat family, not a clamp
    // edit — and it is already flagged in FitParams.h. What this change buys is
    // that the window is anchored on physics instead of on a fit.
    // COST OF THE OLD WINDOW, measured on an independent transcription of this
    // solve (bit-identical to it, gated): at 384 kHz the clamp is the ENTIRE
    // error — 6 Newton iterations with the clamp removed reproduce the converged
    // solve to 7e-14 V, while the clamped version errs by up to 1.034 V, i.e. the
    // whole satLo+satHi = 1.036 V output swing. The damage is not to y directly
    // (vtc is already saturated out there, so y moves ~1e-4 V) but to wPrev and to
    // the C14 companion-cap state, which is updated from the CLAMPED w: at 384 kHz
    // that is a 4.8e-4 A error in a branch carrying ~1e-4 A.
    // ⚠ Do NOT "fix" this by widening the number until it stops firing — the point
    // is that the reference is physical and the fit must not reach it. If a future
    // re-fit of the K/clipSat family restores a physical satLo, this constant and
    // that one will agree again on their own.
    static constexpr double kTripPointV = 2.657; // circuit.md / session-42 solve
    static constexpr double kClampHi = 9.6 - kTripPointV;  // +6.943 V
    static constexpr double kClampLo = -0.6 - kTripPointV; // -3.257 V

    // Phase-7 capture fit (FitParams.h). ** Does NOT touch the clamp window — see
    // kTripPointV above: the window is anchored on the physical trip point and a
    // VTC-amplitude fit is not allowed to move it (session-118 bug fix). **
    void setNonlinear(double A0, double sLo, double sHi, double k = kHardness) noexcept
    {
        a0 = A0;
        satLo = sLo;
        satHi = sHi;
        hardness = k;
    }

    // GRUNT position -> coupling cap. ** UI map VERIFIED against capture 2026-07-22
    // (was ASSUMED since Phase 5): up/Boost = 4n7||220n (MOST low end), mid/Cut = 4n7
    // alone (LEAST), down/Flat = 4n7||47n (MEDIUM). Semantics Cut < Flat < Boost. **
    // Evidence (analysis/grunt_a0_check.py, matched-pair vs the cut baseline, 50-300 Hz
    // of the driven sweep): cut 0 dB < flat +5.43 dB < boost +6.81 dB, monotone
    // bin-by-bin. NOTE the enum's declaration order (Cut/Flat/Boost = 0/1/2) is NOT the
    // APVTS index order (0=Boost, 1=Cut, 2=Flat) -- PedalChain::gruntEnum() does that
    // remap deliberately; do not "simplify" it to a cast.
    enum class Grunt
    {
        Cut,   // 4n7 only            (least bass)
        Flat,  // 4n7 || 47n          (medium)
        Boost, // 4n7 || 220n         (most bass)
    };

    Clipper() = default;

    void prepare(double sampleRate)
    {
        fs = sampleRate;
        gc14 = kC14 * 2.0 * sampleRate; // feedback cap companion
        gFb = 1.0 / kR18 + gc14;        // R18 || C14 conductance
        setGruntCap(gruntCapNow(grunt)); // (re)build the input-branch coefficients (uses fittable c11)
        reset();
    }

    void reset() noexcept
    {
        ieqG = 0.0;
        ieq14 = 0.0;
        wPrev = 0.0;
    }

    // Static so the test/oracle can share the exact SCHEMATIC cap value (the FR
    // test fits nothing, so it uses kC11 directly).
    static double gruntCap(Grunt g) noexcept
    {
        switch (g)
        {
            case Grunt::Cut:   return kC11;              // 4n7
            case Grunt::Flat:  return kC11 + kC12;       // 51.7n
            case Grunt::Boost: return kC11 + kC13;       // 224.7n
        }
        return kC11;
    }

    // Instance version — uses the FITTABLE c11/c12/c13 instead of kC11/kC12/kC13,
    // so a fitted clipC11 moves the Cut corner and fitted clipC12/clipC13 move the
    // Flat/Boost corners (session 19 — the capture shows GRUNT voiced backwards, a
    // too-low boost/flat corner; see FitParams::clipC12/clipC13).
    double gruntCapNow(Grunt g) const noexcept
    {
        switch (g)
        {
            case Grunt::Cut:   return c11;
            case Grunt::Flat:  return c11 + c12;
            case Grunt::Boost: return c11 + c13;
        }
        return c11;
    }

    // Set the always-present GRUNT coupling cap (FitParams::clipC11) and re-derive
    // the current position's branch coefficients. Safe in any order vs setGrunt():
    // both re-run setGruntCap() off the live c11/grunt pair.
    void setC11(double v) noexcept
    {
        c11 = v;
        setGruntCap(gruntCapNow(grunt));
    }

    // Set the SWITCHED GRUNT caps (FitParams::clipC12/clipC13). Like setC11, each
    // re-derives the current position's branch coefficients; order-independent vs
    // setC11()/setGrunt() (all re-run setGruntCap() off the live c11/c12/c13/grunt).
    void setC12(double v) noexcept
    {
        c12 = v;
        setGruntCap(gruntCapNow(grunt));
    }

    void setC13(double v) noexcept
    {
        c13 = v;
        setGruntCap(gruntCapNow(grunt));
    }

    // Set the clipper input resistor (FitParams::clipR16). DIAGNOSTIC lever, added
    // session 45 for the A3 crossover sub-gate; the default IS the schematic 6k8, so
    // not calling this is bit-identical to the pre-session-45 build.
    //
    // ⚠ R16 is NOT a pure GRUNT-side element even though it sits in the GRUNT branch.
    // It does two things at once: (a) it scales ALL THREE GRUNT corners together via
    // 1/(2*pi*Cg*(R16 + R18/(1+A0))), leaving the cap RATIOS — and hence the span
    // shelf's height — untouched, which is the one thing C11/C12/C13 cannot do; and
    // (b) it sets the clipper's closed-loop gain -R18/R16, so it moves the OD level
    // too. Read any R16 result as that pair, never as a frequency translation alone.
    void setR16(double v) noexcept
    {
        r16 = v;
        setGruntCap(gruntCapNow(grunt));
    }

    void setGrunt(Grunt g) noexcept
    {
        grunt = g;
        setGruntCap(gruntCapNow(g));
    }

    // Set the input-branch coupling cap directly (used by the FR test to sweep Cg
    // against the oracle, decoupled from the GRUNT position enum).
    void setGruntCap(double cg) noexcept
    {
        gcG = cg * 2.0 * fs;          // grunt cap companion conductance
        dNode = gcG + 1.0 / r16;      // intermediate-node conductance sum
        gIn = gcG / (r16 * dNode);    // Norton conductance of the (Cg,R16) branch
    }

    // Process one sample (real volts in/out; input VD-ref, output trip-point-ref
    // but AC — the downstream C15 re-biases). NET INVERTING.
    inline double process(double x) noexcept
    {
        // Per-sample constant part of the input-branch current source.
        const double ic = ieqG / (r16 * dNode);

        // ---- Rigorous closed-form bracket for the root (session 120) ---------
        // Rearranged, F(w) = (gIn+gFb)*(w0 - w) + gFb*vtc(w), so the root satisfies
        //     w = w0 + (gFb/(gIn+gFb)) * vtc(w),  w0 = (gIn*x - ic - ieq14)/(gIn+gFb)
        // and |vtc| <= max(satLo,satHi) confines it to w0 +/- rad. F is strictly
        // decreasing, so F(lo) >= 0 >= F(hi) and the root is unique: this bracket
        // cannot fail, costs no iteration, and needs no tuning.
        const double sum = gIn + gFb;
        const double w0 = (gIn * x - ic - ieq14) / sum;
        const double rad = gFb * (satLo > satHi ? satLo : satHi) / sum + 1e-12;
        double lo = w0 - rad, hi = w0 + rad;

        // ---- Bracketed Newton with bisection fallback (Numerical Recipes
        //      `rtsafe`) — session 120. See kNewtonIters for the measurement. ---
        // ⚠ BOTH conditions are load-bearing and neither may be dropped:
        //   (a) the RANGE test rejects a step that leaves [lo,hi] — a sigmoid VTC
        //       is nearly flat in saturation, so plain Newton launched from out
        //       there overshoots to the far side and can cycle;
        //   (b) the SUFFICIENT-DECREASE test |2f| > |dwOld*fp| ("Newton is not at
        //       least halving") is what breaks a 2-CYCLE in which Newton at a
        //       proposes exactly b and at b proposes exactly a. A hand-rolled
        //       guard with only (a) was measured cycling for 16 iterations with
        //       the step still at half the bracket width.
        double w = wPrev; // warm start
        if (w < lo) w = lo;
        else if (w > hi) w = hi;
        double dwOld = hi - lo, dw = dwOld;
        double f = solveF(w, x, ic);
        double fp = solveFp(w);
        for (int it = 0; it < kNewtonIters; ++it)
        {
            if ((((w - hi) * fp - f) * ((w - lo) * fp - f) > 0.0)
                || (std::abs(2.0 * f) > std::abs(dwOld * fp)))
            {
                dwOld = dw;
                dw = 0.5 * (hi - lo);
                w = lo + dw;
            }
            else
            {
                dwOld = dw;
                dw = f / fp;
                w -= dw;
            }
            if (std::abs(dw) < 1e-12)
                break;
            f = solveF(w, x, ic);
            fp = solveFp(w);
            if (f > 0.0) lo = w; else hi = w; // F strictly decreasing
        }

        // ---- D1/D2 rail clamps at node W (normally inert) -------------------
        // Read the CONSTANTS directly: there is deliberately no mutable copy of
        // the window any more, so no fit can reach it (session-118 bug fix).
        if (w > kClampHi)
            w = kClampHi;
        else if (w < kClampLo)
            w = kClampLo;

        wPrev = w;
        const double y = vtc(w);

        // ---- Update companion cap states ------------------------------------
        // Intermediate node m between Cg and R16 (eliminated in the solve).
        const double m = (gcG * x - ieqG + w / r16) / dNode;
        ieqG = 2.0 * gcG * (x - m) - ieqG;
        ieq14 = 2.0 * gc14 * (y - w) - ieq14;

        return y;
    }

private:
    // ** SESSION-120: 6 -> 12, and it is a CAP on the tail, not a per-sample cost. **
    // The loop early-exits, and the MEAN iteration count is 2.69-2.98 across the whole
    // OS ladder x drive plane — LOWER than the plain-Newton build's 2.90-3.07, because
    // rtsafe's bisection fallback stops the wasted overshoot-and-return steps. So
    // doubling the cap costs essentially nothing on the ~99 % of samples that converge
    // in 2-4 iterations; it only buys the tail that used to be left unconverged.
    //
    // WHY 12 AND NOT 6 — measured IN-CHAIN, which is the only figure to quote.
    // Temporary instrumentation in this function, driven by OSValidationTest (the real
    // PedalDSP, 23,251,712 clipper samples spanning OS 2/4/8), added, measured and
    // REVERTED:
    //                              plain Newton      rtsafe, cap 12
    //   max clipper input |x|         2.900 V          2.900 V
    //   max solve residual            0.556 V          6.8e-16 V
    //   unconverged samples        606314 (2.608 %)    0 (0.0000 %)
    // rtsafe at cap 6 fixes most of it; only cap >= 8 reaches machine precision at
    // every rate on the synthetic sweep, and 12 is 8 plus margin and is free.
    //
    // ⚠⚠ THE DEFECT IS **NOT** "1x ONLY", AND BOTH SYNTHETIC CHARACTERISATIONS OF IT
    // UNDERSTATED IT — session 118's and this session's first pass alike. A smooth
    // 110 Hz + 770 Hz probe stimulus says "absent at 4x/8x"; the real chain, feeding a
    // 2499 Hz tone through the treble/ATTACK ladder and the GRUNT bank, is unconverged
    // on 2.6 % of samples at only 2.9 V of clipper drive, at 4x AND 8x.
    // ** A solver-convergence claim is a claim about the STIMULUS as much as about the
    // sample rate: a slow, smooth test signal makes wPrev a good warm start and hides
    // the overshoot entirely. Quote the in-chain number. **
    //
    // ⚠ The 162-capture matrix renders at OS 8 and is nonetheless nearly blind to this,
    // because it grades gain-matched band statistics and this error is broadband and
    // signal-correlated — which is exactly why the defect survived to session 120. The
    // instrument that DOES see it is OSValidationTest; see the note below.
    static constexpr int kNewtonIters = 12;

    // ⭐⭐ CONSEQUENCE: `OSValidationTest` PASSES for the first time since session 44.
    // ctest goes 16/17 -> 17/17. At amp 0.35 the alias/signal floor moves
    //   2x -28.1 -> -32.4 | 4x -28.9 -> -50.5 | 8x -24.6 -> -61.2 dB   (36.6 dB at 8x)
    // and the test's own "REAL FOLD-DOWN" markers at amp 0.20/0.35 disappear.
    // Attributed by reverting ONLY this solver on an otherwise identical build.
    //
    // ⛔⛔ THIS SUBSTANTIALLY REFUTES SESSION 92's ATTRIBUTION of that failure to
    // "genuine fold-down from the un-ADAA'd CD4049 VTC". Session 92's evidence was
    // sound and could not have separated the two: a non-converged solve produces a
    // SIGNAL-DEPENDENT error, so it folds at exactly the same |N*f0 - m*fs_os| loci
    // that its bin-matching test used, and it also shrinks with rate, so its
    // 192 kHz-base control is equally consistent with either cause.
    // ⚠ NOT claimed: that the VTC needs no ADAA. ADAA remains open (Phase 10 B) and
    // some genuine fold-down surely remains — what falls is that THIS test's failure
    // was dominated by it. Re-measure before quoting session 92's alias figures.
    // ⚠ Also retired: session 92's "at 8x the chain is aperiodic at 4 of 21 tones",
    // which session 118 attributed to the clamp. With the clamp window fixed (s118)
    // AND the solve converged (s120), re-run `analysis/alias_gate.py` before quoting
    // any of that table — both of its named causes have now moved.

    // The node-W residual and its derivative, factored out so the solve, its bracket
    // and any gate can share ONE definition (see the KCL derivation in the header).
    inline double solveF(double w, double x, double ic) const noexcept
    {
        return gIn * (x - w) - ic + gFb * (vtc(w) - w) - ieq14;
    }
    inline double solveFp(double w) const noexcept
    {
        return -gIn + gFb * (vtcDeriv(w) - 1.0);
    }

    // Inverter VTC (VD_eff-referenced, 0 = trip point). Inverting asymmetric
    // sigmoid: slope -a0 at 0 (both sides -> C1-continuous), saturating to -satLo
    // (output -> GND rail) for w>0 and +satHi (output -> +VDD rail) for w<0. The
    // asymmetry (satLo != satHi) produces the required even harmonics.
    //
    // ** SESSION-11 RESHAPE (2026-07-23): per-side tanh(u) -> the algebraic
    // sigmoid f_k(u) = u / (1 + u^k)^(1/k), u = a0*w/sat (>= 0 per side). **
    // A single tanh coalesces small-signal gain and knee HARDNESS into ONE
    // parameter (a0): its H3 stays buried until a late, sharp knee (~20 dB of H3
    // packed into ~1 octave of drive, right where the capture's DRIVE-noon sits),
    // which is why the step-3/4 fits pinned clipA0 at its physical ceiling and
    // still fell ~8 dB short at noon (phase7-calibration-handover.md §3h-3j).
    // f_k keeps f_k'(0) = 1 EXACTLY (a0 keeps its small-signal / GRUNT-corner
    // meaning; the linear oracle and FR tests are untouched) and |f_k| -> 1
    // (satLo/satHi keep theirs), but knee hardness is now its own parameter:
    // tanh behaves like k ~= 2.5-3; the capture wants softer (k ~= 1.5-2).
    // f_k' = (1+u^k)^-((k+1)/k) is strictly positive, so the VTC stays strictly
    // monotone decreasing and F'(W) remains a sum of strictly negative terms.
    // ⛔ SESSION-120 CORRECTION: that gives the root UNIQUENESS, not "the Newton
    // solve keeps its global-convergence property", which is what this comment
    // used to claim and which is false. A strictly monotone F does not make plain
    // Newton globally convergent — a sigmoid is nearly FLAT in saturation, so a
    // step taken out there is huge and overshoots to the far side. That is exactly
    // the measured 1x/2x defect. Uniqueness is what makes the closed-form bracket
    // in process() valid; convergence is what rtsafe supplies.
    inline double vtc(double w) const noexcept
    {
        if (w >= 0.0)
            return -satLo * sig(a0 * w / satLo);
        return satHi * sig(-a0 * w / satHi);
    }

    inline double vtcDeriv(double w) const noexcept
    {
        const double u = (w >= 0.0) ? a0 * w / satLo : -a0 * w / satHi;
        return -a0 * sigDeriv(u); // both sides negative (inverting), |.| <= A0
    }

    // Per-side sigmoid core, u >= 0 (the two vtc branches fold the sign).
    //   f_k(u)  = u * (1 + u^k)^(-1/k)          f_k(0)=0, f_k'(0)=1, f_k -> 1
    //   f_k'(u) = (1 + u^k)^(-(k+1)/k)          in (0, 1] — strictly positive
    // k == 2.0 (the shipped anchor) takes an exact closed-form fast path — it is
    // also the value whose antiderivative keeps the stage's closed-form ADAA
    // (see the header note); the pow() path exists for the Phase-7 fitter.
    inline double sig(double u) const noexcept
    {
        if (hardness == 2.0)
            return u / std::sqrt(1.0 + u * u);
        const double b = 1.0 + std::pow(u, hardness);
        return u * std::pow(b, -1.0 / hardness);
    }

    inline double sigDeriv(double u) const noexcept
    {
        if (hardness == 2.0)
        {
            const double b = 1.0 + u * u;
            return 1.0 / (b * std::sqrt(b));
        }
        const double b = 1.0 + std::pow(u, hardness);
        return std::pow(b, -1.0 - 1.0 / hardness);
    }

    double fs = 48000.0;
    // Phase-7 capture-fit amplitude params (FitParams.h), nominal-initialised.
    double a0 = kA0, satLo = kSatLo, satHi = kSatHi, hardness = kHardness;
    // Feedback branch (R18 || C14).
    double gc14 = 0.0, gFb = 0.0, ieq14 = 0.0;
    // Input branch (Cg series R16), Norton-reduced.
    double c11 = kC11;   // fittable always-present GRUNT cap (FitParams::clipC11); schematic 4n7
    double c12 = kC12;   // fittable GRUNT Flat  add-cap (FitParams::clipC12); schematic 47n
    double c13 = kC13;   // fittable GRUNT Boost add-cap (FitParams::clipC13); schematic 220n
    double r16 = kR16;   // fittable clipper input R (FitParams::clipR16); schematic 6k8
    double gcG = 0.0, dNode = 0.0, gIn = 0.0, ieqG = 0.0;
    // Newton warm-start.
    double wPrev = 0.0;
    // REF-OD baseline = grunt "mid" = the physical On-Off-On CENTRE = 4n7 alone =
    // the LEAST-bass position (circuit.md GRUNT note), which is Grunt::Cut here.
    Grunt grunt = Grunt::Cut;

    Clipper(const Clipper&) = delete;
    Clipper& operator=(const Clipper&) = delete;
};
