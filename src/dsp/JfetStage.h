#pragma once

#include <cmath>

// =============================================================================
// Stage 2 — J201 JFET gain stage (Q1 common-source + Q2 active load)
// =============================================================================
// The FIRST nonlinear stage. circuit.md "JFET gain stage (Q1/Q2)". Sits between
// the InputBuffer (IC1_A) and the TrebleAttack treble net.
//
//   C2 = 1n    coupling from IC1_A into the drive path
//   R4 = 100k  gate-stopper into Q1 gate      | gate draws ~no current, so the
//   R5 = 1M    gate-leak bias to GND          | input HP sees C2 into R4+R5 = 1.1M
//   Q1 = J201  common-source gain JFET (INVERTING)
//   R6 = 3k3   Q1 source degeneration to GND
//   C3 = 220n  || R6, bypasses the degeneration above ~219 Hz
//   Q2 = J201  active load (gate @ VD via R9/R10, drain @ +9V, source = output)
//   C4 = 22n   Q2 gate->source(output) bootstrap -> raises the active-load Z
//
// ---- THIS STAGE IS A CURRENT SOURCE, NOT A VOLTAGE SOURCE -------------------
// ** RESTRUCTURED 2026-07-22 (Phase-7 calibration). ** It used to be a voltage
// stage — HP -> HF-lift shelf -> *(-G0) -> waveshaper — feeding TrebleAttack as
// an IDEAL source. That was structurally wrong in a way that cost ~+23 dB of
// excess HF in the OD path (docs/phase7-calibration-handover.md). Why:
//
//   For a common-source stage with degeneration Zs = R6||C3 and an active load,
//       k(s)    = 1 + gm*Zs(s)            degeneration factor: 1+gm*R6 at DC -> 1 at HF
//       Gm(s)   = gm / k(s)               transconductance RISES with frequency
//       Rout(s) = ro * k(s)               drain output R FALLS with frequency
//   so the OPEN-CIRCUIT voltage gain is Gm*Rout = gm*ro — **flat, independent of
//   the degeneration**. The old "+10.3 dB HF-lift shelf" is therefore NOT an
//   unconditional gain lift; it only appears to the extent the stage is LOADED.
//   And the load — the treble ladder — has an input impedance that FALLS across
//   the same band (~35 kOhm at 200 Hz -> ~6.5 kOhm at 2 kHz), which cancels most
//   of it. Applying the shelf unconditionally AND then driving the ladder from an
//   ideal source double-counts the boost.
//
// So the stage now outputs the drain NORTON CURRENT, and its output impedance is
// stamped into TrebleAttack's nodal matrix (getSourceZ() / TrebleAttack::
// setSourceZ) — that is the "revisit with an explicit J201 output impedance at
// Phase 7" deferral, discharged. The shelf survives only as the shared k(s) that
// shapes Gm and Rout in OPPOSITE directions, exactly as the device does.
//
//   x --[input HP]--[gate div]--[1/k(s)]--[square-law shaper]--*(-gm)--> i_drain
//        (C2,R4/R5)  R5/(R4+R5)  (C3/R6)     (vgs nonlinearity
//                                             + asymmetric drain-current ceiling)
//
//   * The 1/k(s) filter is the SAME first-order shelf IIR as before, rescaled so
//     its output is the effective vgs (DC gain 1/(1+gm*R6), HF gain 1). Driving
//     the shaper with a true vgs means the knee `s` is in REAL gate volts (order
//     |Vp| ~ 0.3-1.5 V for a J201), not an arbitrary post-gain scale.
//   * Small-signal current is exactly -gm*vgs, so `gm` alone sets the gain and
//     the shaper only adds curvature (its slope at 0 is exactly 1).
//   * This is still a Wiener-Hammerstein approximation: the true degeneration is
//     nonlinear feedback (vgs = vg - i_d*Zs, an implicit solve). Linearising the
//     degeneration and putting the nonlinearity on vgs is the same modelling
//     choice the stage always made, just applied at the physically right node.
//
// ** kGm/kRo/kRq2 and the shaper params are ALL capture-fit (J201 spread ~5:1);
//    only the filter corners (from R/C) and the INVERTING polarity are
//    trustworthy pre-capture. **
//
// ---- Linear transfer (small signal), for the oracle -------------------------
//   i_drain(s)/Vin(s) = -gm/(1+gm*R6) * HP(s) * shelf(s) * R5/(R4+R5)
//   HP(s)    = s(R4+R5)C2 / (1 + s(R4+R5)C2)              fc = 144.7 Hz
//   shelf(s) = (1 + s R6 C3) / (1 + s R6 C3/(1+gm R6))    zero 219 Hz, pole ~719 Hz
//   Zout(s)  = [ro * k(s)] || Rq2,  ro*k(s) = ro + (Rp || Cp),
//              Rp = ro*gm*R6, Cp = R6*C3/Rp               (see getSourceZ)
// All corners are sub-kHz, so there is NO audible-band bilinear warp here; the
// stage matches the analytic oracle across the whole band. Its SHAPER is the
// aliasing source, so the full chain oversamples + ADAA's it (Phase 5/6).
//
// ---- Polarity ---------------------------------------------------------------
// A common-source stage INVERTS. The Norton current is -gm*shape(vgs), i.e. a
// positive input pulls current OUT of the drain node, so V(G) falls: NET
// INVERTING, unchanged by the restructure (DC-step asserted in JfetStageTest).
// This is the sign the OD path carries into BLEND alongside the CD4049's
// inversion (dsp.md "Dry/wet phase alignment ... Polarity").
//
// ---- Why NO RailClamp here --------------------------------------------------
// RailClamp models a TL07x OP-AMP output hitting its supply rails. The J201
// drain is not an op-amp output — its limiting is the device's own, and as of
// 2026-07-22 it is modelled explicitly by the asymmetric drain-current ceiling
// in waveshape() (see there). Before that the shaper was UNBOUNDED and, with
// railEnabled = false, nothing between the input jack and the CD4049 limited
// anything at all.
// =============================================================================
class JfetStage
{
public:
    // Component values (circuit.md "JFET gain stage (Q1/Q2)"). Public = single
    // source of truth for the test's inline oracle (no drift).
    static constexpr double kR4 = 100.0e3;   // gate stopper
    static constexpr double kR5 = 1.0e6;     // gate-leak bias to GND
    static constexpr double kC2 = 1.0e-9;    // input coupling
    static constexpr double kR6 = 3.3e3;     // source degeneration
    static constexpr double kC3 = 220.0e-9;  // source-bypass (HF lift)

    // ---- NOMINAL amplitude placeholders — FIT TO CAPTURE AT PHASE 7 ---------
    // kGm  = Q1 transconductance. Datasheet Shichman-Hodges self-bias point
    //        (Id ~= 0.12 mA -> gm ~= 0.69 mS). Sets BOTH the small-signal current
    //        AND, through gm*R6, the degeneration factor k(s) — one parameter,
    //        physically coupled. (The old separate `kGmR6` is GONE: R6 is a fixed
    //        3k3, so gm*R6 was never independent of gm. Removing the redundancy
    //        also resolves the "jfetGmR6 missing from FIT_KEYS" carry-forward —
    //        it is no longer a free parameter at all.)
    // kRo   = Q1 drain output resistance (1/gos). J201 gos is a few uS at this
    //         bias, hence a few hundred kOhm — but it is spread like everything
    //         else on this part, and it is now the main thing setting how much of
    //         the C3 shelf survives into the treble net. FIT IT.
    // kRq2  = Q2 active-load impedance at the drain, C4-bootstrapped (the
    //         bootstrap corner is ~14.5 Hz into R9||R10 = 500k, so it is fully
    //         active across the audio band -> this is high, not 1/gm). FIT IT.
    static constexpr double kGm = 0.69e-3;   // S   (gm*R6 = 2.277 at nominal)
    static constexpr double kRo = 200.0e3;   // ohm
    static constexpr double kRq2 = 1.0e6;    // ohm

    // Waveshaper params for the SQUARE-LAW even-shaper (see waveshape()).
    // kSatPos = s, the knee; kSatNeg = a, the even (H2/H4) strength, SIGNED.
    // ** SCALE CHANGED with the 2026-07-22 restructure: the shaper now sees the
    //    effective vgs (real gate volts, order |Vp|), NOT a post-gain voltage, so
    //    any previously fitted s/a values are meaningless here — refit. **
    // Nominal is deliberately mild; the CD4049 downstream does the heavy
    // distorting. ** kSatPos 0.5 -> 0.3 on 2026-07-22 with the ceiling: the
    // nominal set must sit INSIDE the feasible region, not on its edge. The
    // ceiling makes monotonicity couple s to kCeilNeg (roughly ceilNeg >~ s, see
    // waveshape()), and the square law ties ceilNeg = 1/(2a); at a = 1 that is
    // ceilNeg = 0.5, so s = 0.3 leaves a 1.67x margin where s = 0.5 sat exactly
    // on the boundary with zero margin in the tail. Parking a nominal on a
    // constraint is how this calibration has already produced two uncommittable
    // fits. **
    static constexpr double kSatPos = 0.3;   // s: square-law knee (gate volts)
    static constexpr double kSatNeg = 1.0;   // a: even-harmonic strength (signed)

    // ---- Asymmetric drain-current CEILING (added 2026-07-22, Phase-7 step 2) -
    // Units are the shaper's own — gate-volt equivalent; multiply by gm for AMPS.
    // That is the physically right parameterisation: the cutoff-side headroom is
    // Idq/gm = Vov/2, a property of the pinch-off voltage, NOT of the operating
    // current, so it does not move when the fitter moves gm (an amps-domain
    // ceiling would be coupled to gm and make the fit worse-conditioned).
    //
    // kCeilNeg — the negative-swing (drain rising) side. TWO things limit it:
    //   * Q1 CUTOFF, a hard device floor — drain current cannot go below zero, so
    //     the downward AC swing is bounded by the quiescent current, Idq/gm = Vov/2.
    //     Expanding the square law about the bias point, the SAME Vov sets the even
    //     strength: Id/gm = vgs + vgs^2/(2*Vov), i.e. a = 1/Vov. So IF cutoff binds,
    //         ** kCeilNeg = 1/(2*a) = Vov/2 **
    //     and the nominal 0.5 V is exactly that identity at the nominal a = 1.0.
    //   * Q2's own COMPLIANCE — the active load only holds saturation over roughly
    //     (9 - Vd_q - Vds_sat2) ~ 3 V, i.e. 3/(gm*Zload) = ~0.15 V at LF at the
    //     nominal gm, which is TIGHTER than the cutoff floor. So the identity above
    //     only applies in the low-gm regime, and a fit that misses it is not
    //     automatically wrong (dsp-validator 2026-07-22). Use it as corroboration
    //     when it holds, not as a requirement.
    //   The documented gm bias point (Id 0.12 mA, gm 0.69 mS -> Vov = 2*Idq/gm =
    //   0.35 V) implies a ~= 2.9 and ceilNeg ~= 0.17; that set is feasible only with
    //   a much smaller knee s (s, a and ceilNeg are coupled — see waveshape()), so
    //   it is NOT imposed as the nominal, only offered as a target to hit or refute.
    // kCeilPos — the side that swings the drain DOWN toward the load line, so it
    //   is CIRCUIT-set, not device-set: (Vd_q - Vds_sat)/(gm*Zload). With ~4 V of
    //   drain headroom and the node-G load (ro||Rq2||treble ladder, 28.9k at 200 Hz
    //   and 6.3k at 2 kHz) that is 0.20 V at LF and 0.93 V at 2 kHz **at the nominal
    //   gm** — band-dependent, which a single memoryless number deliberately LUMPS.
    //   It also scales as 1/gm, so at the gm ~= 0.09 mS the drive-min shape fit
    //   prefers it is ~7.7x looser again (1.5-7 V). Nominal 1.0 V.
    // WHICH SIDE BINDS IS STILL OPEN and turns on gm: at the NOMINAL gm the estimates
    // above make kCeilPos (0.20 V) the tighter of the two, and only under the low-gm
    // hypothesis does the cutoff side bind. Do not assume either ordering.
    // The asymmetry between them is what "the real drain clips toward the rail one
    // way and toward cutoff the other" means, and is a second source of even
    // harmonics alongside `a`, reinforcing it in the same direction.
    // Both are FIT params. Passing >= kCeilOff DISABLES that side exactly (the
    // pre-ceiling model, for A/B and for the core's structural test); anything
    // <= 0 is clamped to a tiny positive value, not treated as "off".
    static constexpr double kCeilPos = 1.0;  // V-equiv (x gm -> A), load-line side
    static constexpr double kCeilNeg = 0.5;  // V-equiv (x gm -> A), cutoff side
    static constexpr double kCeilOff = 1.0e6; // >= this == "no ceiling" (exact bypass)

    // Thevenin/Norton output network handed to TrebleAttack, which stamps it into
    // its nodal matrix: Zout(s) = [ro + (Rp || Cp)] || Rq2, the exact ro*k(s)||Rq2.
    struct SourceZ
    {
        double ro, rq2, rp, cp;
    };

    JfetStage() = default;

    void prepare(double sampleRate)
    {
        fs = sampleRate;

        // ---- Input HP: trapezoidal companion for C2 -------------------------
        gc2 = kC2 * 2.0 * sampleRate;
        gRin = 1.0 / (kR4 + kR5);

        updateShelf();
        reset();
    }

    // Phase-7 capture fit (FitParams.h). gm sets the shelf POLE (via gm*R6) as
    // well as the gain, so changing it must re-derive the shelf coefficients —
    // hence the stored fs and the updateShelf() call. Calling this before
    // prepare() is fine; prepare() recomputes from the stored values.
    void setNonlinear(double Gm, double Ro, double Rq2, double satPos, double satNeg,
                      double ceilPos, double ceilNeg) noexcept
    {
        gm = (Gm > 1.0e-9) ? Gm : 1.0e-9; // rp = ro*gm*R6 must stay non-degenerate
        ro = Ro;
        rq2 = Rq2;
        // sPos divides in waveshape(): --fit jfetSatPos=0 gives tanh(0/0) = NaN and
        // poisons the whole chain, so guard it like gm. (A NEGATIVE s is harmless —
        // the map is exactly even in s — so only the magnitude needs a floor.)
        sPos = (std::abs(satPos) > 1.0e-9) ? satPos : 1.0e-9;
        sNeg = satNeg;
        // A ceiling below ~1 uV-equivalent is not a pedal, it is a divide-by-zero;
        // clamp rather than let a stray fit value produce inf/NaN in the chain.
        cPos = (ceilPos > 1.0e-6) ? ceilPos : 1.0e-6;
        cNeg = (ceilNeg > 1.0e-6) ? ceilNeg : 1.0e-6;
        updateShelf();
    }

    // The drain-node output network (see SourceZ). TrebleAttack owns the actual
    // stamping — this stage only reports the impedance its device presents.
    SourceZ getSourceZ() const noexcept
    {
        const double gmR6 = gm * kR6;
        const double rp = ro * gmR6;
        return { ro, rq2, rp, (kR6 * kC3) / rp };
    }

    void reset() noexcept
    {
        ieqC2 = 0.0;
        shelfX1 = shelfY1 = 0.0;
        uPrev = 0.0;
    }

    // 1st-order ADAA on the waveshaper (dsp.md "ADAA"). Off by default so the
    // per-stage oracle test validates the raw memoryless map; PedalChain turns it
    // ON inside the oversampled region. Glitch-free to toggle — uPrev updates
    // every sample regardless.
    void setADAA(bool e) noexcept { adaa = e; }

    // Process one sample. IN: real volts from the input buffer.
    // OUT: the drain NORTON CURRENT in AMPS, signed for injection into node G
    // (TrebleAttack's source node). NET INVERTING: +v in -> negative current in.
    inline double process(double x) noexcept
    {
        // ---- Input HP node (C2 source-side, R4+R5 to GND) -------------------
        // (gc2 + gRin)*vx = gc2*x - ieqC2
        const double vx = (gc2 * x - ieqC2) / (gc2 + gRin);
        ieqC2 = 2.0 * gc2 * (x - vx) - ieqC2; // v_ab = x - vx

        // ---- Gate divider + degeneration -> effective vgs -------------------
        // shelf() has DC gain 1 / HF gain (1+gm*R6); dividing by (1+gm*R6) makes
        // this 1/k(s), i.e. the real gate-source voltage the device responds to.
        const double vg = kDiv * vx;
        const double vs = sb0 * vg + sb1 * shelfX1 - sa1 * shelfY1;
        shelfX1 = vg;
        shelfY1 = vs;
        const double vgs = vs / (1.0 + gm * kR6);

        // ---- Square-law drain current (INVERTING) ---------------------------
        const double y = adaa ? adaaShape(vgs, uPrev) : waveshape(vgs);
        uPrev = vgs;
        return -gm * y;
    }

private:
    static constexpr double kDiv = kR5 / (kR4 + kR5); // gate divider, folds in here now

    // HF-lift shelf: bilinear (== trapezoidal) first-order IIR.
    // Analog:  shelf(s) = (1 + s*tauZ) / (1 + s*tauP),  tauZ=R6C3, tauP=tauZ/(1+gmR6)
    // Bilinear s = c*(1 - z^-1)/(1 + z^-1),  c = 2*fs :
    //   H(z) = ((1+c*tauZ) + (1-c*tauZ)z^-1) / ((1+c*tauP) + (1-c*tauP)z^-1)
    void updateShelf() noexcept
    {
        const double c = 2.0 * fs;
        const double tauZ = kR6 * kC3;
        const double tauP = tauZ / (1.0 + gm * kR6);
        const double a0 = 1.0 + c * tauP;
        sb0 = (1.0 + c * tauZ) / a0;
        sb1 = (1.0 - c * tauZ) / a0;
        sa1 = (1.0 - c * tauP) / a0;
    }

    // ---- The static map, PUBLIC on purpose ----------------------------------
    // waveshape()/waveshapeAD() are exposed so JfetStageTest (and throwaway
    // probes, and dsp-validator) can validate the SHIPPED map directly —
    // monotonicity by finite-differencing g, and F' == g — instead of
    // re-implementing a now-piecewise shape in the test and testing the replica.
    // They are pure functions of the fit params; nothing here touches state.
public:
    // J201 SQUARE-LAW soft-shaper (Phase-7 capture finding, 2026-07-22): replaces the
    // former per-polarity tanh. The real B7K's low-drive OD character is even-dominant
    // (captured H2 ~= -36 dB, H3 ~= -59 dB @ drive-min: a ~23 dB even/odd separation) —
    // the fingerprint of a JFET common-source SQUARE-LAW transfer (Id ~ (Vgs-Vt)^2 ->
    // pure H2). A tanh is an ODD map: its w^3 term forces H3 whenever it makes H2, so it
    // structurally cannot reach that separation (proven by fit — the tanh floored H3 at
    // ~-50 dB while the capture sits at -59). This shape is LINEAR-CORE + EVEN:
    //     g(w) = T(w) + (a*s^2/2) * tanh^2(w/s)
    // where T is the linear core, soft-limited per side by the ceiling below (T(w) = w
    // exactly with the ceiling disabled). The bump is EXACTLY EVEN, so it contributes
    // ZERO odd content — and hence zero H3 — at any drive; ALL of g's odd part is T.
    // (T itself is only an odd function when Lp == Ln; with the ceilings asymmetric,
    // odd(g) = odd(T) != T. Do not read "the odd part is T" as "the odd part is
    // linear" once a ceiling is on — that is only true with it off.) The bump's
    // small-signal expansion is a*w^2/2, the square law's own quadratic, so `a` =
    // 1/Vov *in the small-signal limit* — note it saturates by |w| ~ 2s, so at the
    // cutoff distance |w| = Vov the model holds a*s^2/2 of quadratic content where a
    // true square law would hold a*Vov^2/2. This is a FITTED shape that is square-law
    // near the origin, not a square law in the large; the `a = 1/Vov` identity below
    // inherits that caveat. Slope at 0 is exactly 1 (so `gm` alone remains the
    // small-signal transconductance).
    // NOTE the argument is the effective vgs (real gate volts) — see the header note on
    // the 2026-07-22 restructure; old fitted s/a values do not carry over. The even
    // bump's SHAPE also changed on 2026-07-22 (see the ceiling note below for why), so
    // s/a fitted against the sech form do not carry over either — but `a`'s meaning
    // (the square-law quadratic coefficient) is unchanged, and its asymptote halved.
    //
    // ---- THE ASYMMETRIC DRAIN-CURRENT CEILING (added 2026-07-22) -------------
    // The LINEAR term of the core is replaced by a per-side soft limit:
    //     T(w)  = Lp*tanh(w/Lp)   w >= 0      (Lp = kCeilPos, load-line side)
    //             Ln*tanh(w/Ln)   w <  0      (Ln = kCeilNeg, cutoff side)
    //     g(w)  = T(w) + (a*s^2/2)*tanh^2(w/s)
    // so the whole map is now BOUNDED: g -> +Lp + a*s^2/2 and -Ln + a*s^2/2. (The
    // even bump's own asymptote is the SAME constant on both sides, i.e. a
    // saturating DC offset — rectification — so the peak-to-peak AC swing is
    // bounded by gm*(Lp+Ln), which is the physical statement wanted.)
    //
    // ** THE EVEN BUMP CHANGED SHAPE WITH THIS COMMIT: a*s^2*(1-sech(w/s)) ->
    // (a*s^2/2)*tanh^2(w/s). Both forms are exactly even with the same leading term
    // a*w^2/2 (so `a` keeps its meaning and the bump still adds no odd content),
    // but their TAILS decay at different rates, and the tail is what decides
    // monotonicity once a ceiling is present:
    //     ceiling slope  sech^2(w/L)          ~ 4*exp(-2|w|/L)
    //     old bump slope a*s*sech*tanh (w/s)  ~ 2*a*s*exp(-|w|/s)   <- 2x SLOWER
    //     new bump slope a*s*tanh*sech^2(w/s) ~ 4*a*s*exp(-2|w|/s)  <- MATCHED RATE
    // With the OLD bump the ceiling's slope dies off faster than the bump's, so deep
    // in cutoff the bump always wins eventually and g FOLDS BACK unless Ln > 2s.
    // With the matched rate that relaxes to **Ln > s** — a 2x wider feasible region,
    // which is the honest size of the win. It is NOT "makes a ceiling possible at
    // all": both regions have plenty of interior, and both have zero margin ON their
    // own boundary, where the min slope decays to zero (measured: new shape at
    // Ln/s = 1.0 gives +5e-174, old shape at Ln/2s = 1.0 the same). So a fit that
    // parks at Ln ~= s is still resting on a constraint and must be read that way.
    // At exactly Ln = s the slope FACTORISES on the negative side, which pins the
    // condition down without any asymptotics (x = |w|/s, w < 0):
    //     g'(w) = sech^2(x) * (1 - a*s*tanh(x))   ->   feasible iff **|a|*s < 1**
    // (NOT the (4 - 2*a*s) => |a|*s < 2 first written here; dsp-validator caught it,
    // counterexample on the shipped map: s=0.3, a=5.0, cn=0.3 gives min slope
    // -0.0765.) That is much tighter than the ceiling-OFF bound of 2.598 below, and
    // it is why the gate must be numeric.
    // Measured at the nominal set (s=0.3, a=1, cp=1, cn=0.5): min slope +0.0013 over
    // |w| <= 2 and +2.4e-104 globally (i.e. saturating, not folding). The old bump at
    // the same nominal gives -3e-6 — marginally infeasible. **
    //
    // WHY, and why this shape specifically (phase7-calibration-handover.md,
    // "STEP 2 RE-FIT"): the capture's H2 grows only +6 dB across the drive sweep
    // while the unbounded model's grew +21.9 dB — the real drain saturates and the
    // model did not. The step-2 fitter, having no ceiling to reach for, drove
    // |a|*s into the 2.0 monotonicity gate (1.9997) trying to bend the even term
    // over, and pushed clipA0 to its floor to weaken everything downstream. So the
    // ceiling has to be its OWN structure, and it must be inert at low drive:
    //   * T(0) = 0 and T'(0) = 1 EXACTLY on both sides, so gm remains the
    //     small-signal transconductance and the linear oracle is untouched.
    //   * T is C2 at the seam (T'' = 0 from both sides; the branches first differ
    //     in T''' = -2/L^2), so the piecewise join makes no spurious harmonics.
    //   * With Lp,Ln >= kCeilOff it reduces EXACTLY to the previous g(w) = w + ...
    // Below the knee T(w) ~ w - w^3/(3L^2), so the ceiling's own H3 goes as
    // (A/L)^2 while the core's H2 goes as a*A: H2/H3 ~ 3*a*L^2/A. The core's
    // intrinsic H3 is still EXACTLY zero — all H3 here now comes from the ceiling,
    // by construction, and vanishes as the ceiling is raised. That is deliberate:
    // H3 currently tracks the capture to ~1.4 dB and must not be disturbed at low
    // drive, and a bounded map cannot have an exactly-linear odd part (bounding
    // IS an odd-order operation), so the only safe place to put it is a knee the
    // fit can push out of the way.
    // ** Do NOT get the bound by raising |a|*s instead — that breaks monotonicity
    // (see the gate below; the applicable limit depends on the ceiling and is as
    // tight as |a|*s < 1 when Ln = s) and re-introduces H3 everywhere, not just
    // above a knee. **
    //
    // ** MONOTONICITY — READ THIS, THE BOUND MOVED AND IT IS A TRAP **
    //     g'(w) = sech^2(w/L) + a*s*tanh(w/s)*sech^2(w/s),    L = Lp or Ln
    // With the ceilings OFF (sech^2(w/L) == 1) the bound is set by
    // max|tanh*sech^2| = 2/(3*sqrt(3)) = 0.38490, i.e. **|a|*s < 3*sqrt(3)/2 =
    // 2.598** for the NEW bump — where the OLD (sech) bump's bound was |a|*s < 2
    // from max|sech*tanh| = 1/2.
    // ** So 2.598 is now CORRECT here, and it is the same numeral that was WRONG
    // in this file until 2026-07-22 (it was 1/max(sech^2*tanh), quoted against a
    // shape whose extremum was max(sech*tanh) = 1/2). Do not "fix" it back to 2,
    // and do not carry the old 2.0 forward: check which bump shape is in the file
    // before trusting either number. Both are now derived above from their own
    // extremum so the derivation, not the numeral, is the source of truth. **
    // With a FINITE ceiling neither closed-form bound is sufficient — the
    // condition couples s, a and L (the tail argument above adds L >~ s). A fitter
    // must scan g'(w) NUMERICALLY: fit_nonlinear.py does, and JfetStageTest
    // finite-differences the shipped map rather than a replica.
    inline double waveshape(double w) const noexcept
    {
        const double th = std::tanh(w / sPos);
        return coreLimit(w) + 0.5 * sNeg * sPos * sPos * th * th;
    }

    // Per-side soft ceiling on the linear core (see waveshape()).
    inline double coreLimit(double w) const noexcept
    {
        const double L = (w >= 0.0) ? cPos : cNeg;
        if (L >= kCeilOff)
            return w; // exact bypass — the pre-ceiling model
        return L * std::tanh(w / L);
    }

    // Antiderivative of coreLimit: L^2 * ln(cosh(w/L)), zero at w = 0 on BOTH
    // sides, so F stays continuous and C1 across the seam.
    inline double coreLimitAD(double w) const noexcept
    {
        const double L = (w >= 0.0) ? cPos : cNeg;
        if (L >= kCeilOff)
            return 0.5 * w * w;
        return L * L * lnCosh(w / L);
    }

    // ln(cosh x), numerically safe at BOTH ends. The textbook form
    // |x| + log1p(exp(-2|x|)) - ln2 overflows nothing but catastrophically
    // cancels as x -> 0 (it subtracts two ~ln2 quantities to get ~x^2/2), which
    // matters here because a large ceiling drives x = w/L towards zero — exactly
    // the "ceiling nearly disabled" region a fitter sweeps through.
    // ** Crossover 3e-3, NOT 1e-4. ** It has to be picked from BOTH error curves,
    // not just the series truncation: measured relative error vs mpmath is
    //     x      series      closed form
    //     1e-4   1.1e-16     4.4e-9      <- the closed form is 1e7 x worse here
    //     1e-3   4.5e-14     5.1e-11
    //     3e-3   3.6e-12     2.8e-12     <- the curves cross HERE
    // so a 1e-4 crossover hands x in [1e-4, 1e-3] to the branch this function
    // exists to avoid. Not academic: dsp-validator measured ADAA returning 10.1
    // instead of ~1 at L = 1e4, w = 1, du = 1e-9 (just above the midpoint guard).
    // At 3e-3 both branches are <= 3e-12.
    static inline double lnCosh(double x) noexcept
    {
        const double ax = std::abs(x);
        if (ax < 3.0e-3)
            return 0.5 * x * x * (1.0 - x * x / 6.0); // x^2/2 - x^4/12
        return ax + std::log1p(std::exp(-2.0 * ax)) - 0.69314718055994531;
    }

    // Antiderivative of waveshape (for 1st-order ADAA):
    //   F(w) = FT(w) + (a*s^2/2) * (w - s*tanh(w/s)),
    //   since d/dw[w - s*tanh(w/s)] = 1 - sech^2(w/s) = tanh^2(w/s).
    //   FT = coreLimitAD (w^2/2 with the ceiling disabled).
    // F(0) = 0 and F is C1, so 1st-order ADAA is well-posed (exact at DC). The
    // Gudermannian the old sech bump needed is gone — this one integrates in
    // elementary terms, and stays finite for any w (tanh saturates, so F grows
    // linearly rather than overflowing).
    inline double waveshapeAD(double w) const noexcept
    {
        const double s = sPos, a = sNeg;
        return coreLimitAD(w) + 0.5 * a * s * s * (w - s * std::tanh(w / s));
    }

    // 1st-order ADAA: y = (F(u) - F(uPrev)) / (u - uPrev); midpoint fallback when
    // the two are too close (avoids 0/0), which also keeps it exact at DC.
    // The previous sample is a PARAMETER, not the `uPrev` member, so the caller
    // controls the pairing — named `prev` so it doesn't shadow that member.
    inline double adaaShape(double u, double prev) const noexcept
    {
        const double du = u - prev;
        if (std::abs(du) < 1.0e-9)
            return waveshape(0.5 * (u + prev));
        return (waveshapeAD(u) - waveshapeAD(prev)) / du;
    }

private:
    // Phase-7 capture-fit amplitude params (FitParams.h), nominal-initialised.
    double gm = kGm, ro = kRo, rq2 = kRq2, sPos = kSatPos, sNeg = kSatNeg;
    double cPos = kCeilPos, cNeg = kCeilNeg;

    // Input-HP companion (set in prepare()).
    double fs = 48000.0;
    double gc2 = 0.0;
    double gRin = 1.0 / (kR4 + kR5);
    double ieqC2 = 0.0;
    // Shelf IIR coefficients (a0-normalised) + state.
    double sb0 = 1.0, sb1 = 0.0, sa1 = 0.0;
    double shelfX1 = 0.0, shelfY1 = 0.0;
    // ADAA state.
    bool adaa = false;
    double uPrev = 0.0;

    // JUCE-free (compiled into pure console tests).
    JfetStage(const JfetStage&) = delete;
    JfetStage& operator=(const JfetStage&) = delete;
};
