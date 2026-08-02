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

    // ---- EXPANSIVE-THEN-BOUNDED core (session-15 branch B, 2026-07-23) -------
    // SUPERSEDES the session-13/14 `jfetCeilK` hardness reshape, which was PROVEN
    // the wrong lever: its pre-registered pivot gate failed robustly (handover §3t.2
    // — hardness only rescales the ceiling's H3 magnitude, and the ceiling's H3 is
    // structurally ANTI-PHASE to the clipper's, ~180 deg apart, so no k drove the
    // capture's monotonic drive-min->noon H3-H2 ramp; it just walked both through a
    // shared anti-phase null). A follow-up phase-aware measurement (§3t.5,
    // analysis/phase_harmonics.py) then showed the anti-phase is GENUINE (not a
    // notch confound, not a polarity bug — a global inversion cannot change a
    // RELATIVE phase, and per-stage fundamentals are DC-step-verified): the capture
    // matches the model's CLIPPER phase at the one conclusive tone (1 kHz, 8 deg
    // apart) and opposes the ceiling (160 deg). **The real JFET's H3 is
    // EXPANSIVE-signed** (in-phase with the clipper) — no compressive shape, however
    // hard its knee, can produce that sign. This core replaces the compressive
    // sigmoid with a shape whose small-signal cubic term has the OPPOSITE sign.
    //
    //     T(w) = w*(1 + c*w^2) / (1 + (w/L)^2)^(3/2),   c = beta + 3/(2*L^2)
    //
    // reparameterised so the small-signal series is EXACT or DESIGN, not incidental:
    //     T(w) = w + beta*w^3 + O(w^5)                   (verified via sympy.series)
    // `beta` (kExpandBeta / eBeta) is the expansive cubic coefficient directly —
    // beta > 0 gives in-phase (expansive) H3 at the tone level; beta = 0 is neutral
    // (cubic-free) though the shape still saturates via the 3/(2L^2) baseline; beta
    // < 0 recovers a compressive shape (the OLD ceiling's regime, as a special case
    // of the SAME family, useful as an A/B against session 14's finding). T is still
    // BOUNDED for loud input: as w -> +-inf, T(w) -> +-(beta*L^3 + 1.5*L) (finite —
    // verified via sympy.limit), i.e. L still sets the ceiling's SCALE (its old,
    // pre-14 job) while beta ALSO now contributes to where the asymptote lands. Per
    // side (Lp = kCeilPos load-line side, Ln = kCeilNeg cutoff side, unchanged
    // meanings/values from the original 2026-07-22 ceiling), sharing ONE beta —
    // asymmetry is an H2 (even) lever (session 14 §3t.4 "reject" note), so it stays
    // on cPos/cNeg + the untouched even bump, not duplicated onto beta.
    //
    // ** WHY NOT literally reuse jfetCeilK's `w/(1+|w/L|^k)^(1/k)` sigmoid composed
    // with an inner w+beta*w^3 pre-warp (i.e. T(w) = Sigmoid(w+beta*w^3))? ** Tried
    // first, REJECTED: composing two nonlinear maps does not have an elementary
    // antiderivative in general (confirmed: at k=2 the composed integral reduces to
    // an elliptic-type integral of a degree-6 polynomial under a square root, not a
    // closed form) — it would have broken the mandatory closed-form ADAA. The
    // rational-function form above is NOT that composition; it is a single elementary
    // map engineered so its OWN series matches w+beta*w^3 near 0 while its OWN tail
    // saturates — same qualitative goal (expansive-then-bounded), different
    // construction, one that keeps a real antiderivative (see coreLimitAD()).
    //
    // ** MONOTONICITY — proven analytically, not just scanned (a first for this file's
    // reshapes; every prior shape here needed only a numeric scan because no closed
    // bound existed). T'(w) = L^3*(L^2 + w^2*(3*L^2*beta + 2.5)) /
    // (sqrt(L^2+w^2)*(L^2+w^2)^2). The denominator is always positive; the numerator's
    // sign is that of L^2 + w^2*(3*L^2*beta+2.5). For beta >= 0 the bracket
    // (3*L^2*beta+2.5) is >= 2.5 > 0, so the WHOLE bracket is a sum of two strictly
    // positive terms for ANY w, L>0 — T'(w) > 0 EVERYWHERE, unconditionally. (For
    // beta < -2.5/(3*L^2) the bracket can go negative at large |w| and the map folds
    // back — verified numerically the threshold is exact to float precision — but
    // beta must stay >= 0 for this branch's whole purpose, so that region is simply
    // out of scope, not a constraint the fitter needs to track.) Still gated
    // numerically in JfetStageTest AND fit_nonlinear.py per this file's standing
    // rule (memory: derive bounds from the shape in the file, then verify — an
    // analytic derivation has been wrong here before).
    static constexpr double kExpandBeta = 0.0; // PLACEHOLDER — session-15 fit target

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
                      double ceilPos, double ceilNeg, double expandBeta = kExpandBeta) noexcept
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
        // Expansive-cubic strength (branch-B core, see kExpandBeta). No floor needed
        // — beta=0 is a perfectly valid (neutral) value, and the shape is provably
        // monotone for all beta >= 0 (see the class-level note), so there is no
        // divide-by-zero or fold-back risk to guard against here.
        eBeta = expandBeta;
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
    // ---- THE ASYMMETRIC DRAIN-CURRENT CORE (added 2026-07-22; RESHAPED 2026-07-23,
    // session 15, branch B — see kExpandBeta for the full derivation/rejected
    // alternatives). The LINEAR term of the core is replaced by a per-side
    // EXPANSIVE-THEN-BOUNDED rational map (NOT a compressive sigmoid — that family
    // was proven the wrong lever by the session-14 pivot gate):
    //     T(w)  = w*(1 + c*w^2) / (1 + (w/Lp)^2)^(3/2),  c = beta + 3/(2*Lp^2)   w >= 0
    //             w*(1 + c*w^2) / (1 + (w/Ln)^2)^(3/2),  c = beta + 3/(2*Ln^2)   w <  0
    //     g(w)  = T(w) + (a*s^2/2)*tanh^2(w/s)
    // Lp = kCeilPos (load-line side), Ln = kCeilNeg (cutoff side) — same names/values/
    // physical meanings as the original 2026-07-22 ceiling (see their doc comments
    // above); only the SHAPE bolted onto them changed. The even bump is UNCHANGED —
    // only the core's limiter shape changed (again).
    //
    // ** WHY THIS RESHAPE (handover §3t, session 14-15). ** Session 14 gave the
    // ceiling a hardness knob `k` (T(w)=w/(1+|w/L|^k)^(1/k)) and its own pre-registered
    // pivot gate FAILED: as k rose, drive-min AND drive-noon H3-H2 fell the SAME
    // direction (through an anti-phase null) instead of separating — hardness only
    // rescales the ceiling's H3 magnitude, and a COMPRESSIVE shape's H3 is
    // intrinsically ~180 deg from the clipper's H3 at the chain's output, so no k
    // could flip it in-phase. A follow-up phase-aware measurement (§3t.5) confirmed
    // this is genuine (not a notch confound, not a polarity bug): the real JFET's H3
    // is EXPANSIVE-signed. This core's cubic term is +beta (not the old shape's
    // implicit -something), so the SIGN itself is now a first-class fit lever.
    //
    // WHY it stays inert at low drive and preserves the structure the reshape depends on:
    //   * T(0) = 0 and T'(0) = 1 EXACTLY on both sides (independent of beta and L), so
    //     gm remains the small-signal transconductance and the linear oracle/FR/corner
    //     tests are UNTOUCHED.
    //   * T is C1 at the seam (T'(0+) = T'(0-) = 1 for any Lp, Ln, beta), so the
    //     piecewise join makes no spurious first-order harmonic.
    //   * With Lp,Ln >= kCeilOff it reduces EXACTLY to g(w) = w + bump (beta is
    //     ignored in the bypass branch — see coreLimit()).
    // Near the origin T(w) = w + beta*w^3 + O(w^5) BY CONSTRUCTION (beta is not an
    // incidental coefficient of some other shape parameter, it IS the cubic term) —
    // beta > 0 is what makes drive-min H3 rise in-phase with the clipper.
    //
    // ** MONOTONICITY — proven analytically for the region this branch actually
    // needs (beta >= 0), then still gated numerically per this file's standing rule. **
    //     T'(w) = L^3*(L^2 + w^2*(3*L^2*beta + 2.5)) / (sqrt(L^2+w^2)*(L^2+w^2)^2)
    // Denominator always > 0. Numerator's sign = sign of L^2 + w^2*(3*L^2*beta+2.5).
    // For beta >= 0, (3*L^2*beta+2.5) >= 2.5 > 0, so the bracket is a SUM OF TWO
    // STRICTLY POSITIVE TERMS for every w, L>0 — T'(w) > 0 unconditionally, no
    // coupling with s/a/L to track (unlike every prior reshape in this file — the
    // even bump's OWN bound, |a|*s < 2.598, is unaffected and still applies
    // separately).
    // ⚠ BUT |a|*s < 2.598 IS THE BUMP IN ISOLATION, AND THE COMBINED SHAPE IS
    // TIGHTER (measured session 91, scanning THIS function on a 3 uV grid at the
    // shipped s/cPos/cNeg/beta): g folds back at **a = 5.333, |a|*s = 2.431**, not
    // at 5.699/2.598. The bump's bound ignores the core's own negative curvature
    // near the cutoff-side knee, which subtracts from the bump's slope before the
    // bump alone would turn over. Quote 2.598 as an upper bound on the admissible
    // region, never as the region — and scan the real function before shipping any
    // (a, s, cNeg) triple. Session 73's rejected a ~= 5.7 sits PAST this threshold,
    // so it was non-monotone, not merely worse-scoring.
    // The fold-back region only exists for beta < -2.5/(3*L^2), i.e.
    // strictly outside this branch's beta >= 0 regime. Still scanned numerically in
    // JfetStageTest AND fit_nonlinear.py (memory: verify-extremum-derived-bounds —
    // an analytic derivation has been wrong here before; this one was additionally
    // checked against a numeric finite-difference sweep before being trusted, see
    // session-15 log).
    inline double waveshape(double w) const noexcept
    {
        const double th = std::tanh(w / sPos);
        return coreLimit(w) + 0.5 * sNeg * sPos * sPos * th * th;
    }

    // Per-side expansive-then-bounded core (see waveshape() and the class-level note
    // above kExpandBeta for the full derivation). T(w) = w*(1+c*w^2)/(1+(w/L)^2)^1.5,
    // c = beta + 1.5/L^2, reparameterised so the small-signal series is EXACTLY
    // w + beta*w^3 + O(w^5). T(0)=0, T'(0)=1 exactly, and (per side) odd in w — so the
    // even bump keeps its exact-zero-H3 property. Computed via s = sqrt(1+(w/L)^2) and
    // s^3 rather than std::pow(x, 1.5) (cheaper, and avoids a general fractional-power
    // codepath for a fixed exponent).
    inline double coreLimit(double w) const noexcept
    {
        const double L = (w >= 0.0) ? cPos : cNeg;
        if (L >= kCeilOff)
            return w; // exact bypass — the pre-shape model (ignores beta too)
        const double c = eBeta + 1.5 / (L * L);
        const double r2 = (w / L) * (w / L);
        const double s = std::sqrt(1.0 + r2);
        return w * (1.0 + c * w * w) / (s * s * s);
    }

    // Antiderivative of coreLimit (elementary for ANY beta, L — verified via
    // sympy.integrate + a direct d/dw check, session-15 log):
    //   F(w) = c*L^3*sqrt(L^2+w^2) + (c*L^5 - L^3)/sqrt(L^2+w^2),  c = beta + 1.5/L^2
    //   G(w) = F(w) - F(0),   F(0) = 2*c*L^4 - L^2      (G(0)=0, G'=T, C1 at the seam)
    //   bypass: G(w) = w^2/2
    inline double coreLimitAD(double w) const noexcept
    {
        const double L = (w >= 0.0) ? cPos : cNeg;
        if (L >= kCeilOff)
            return 0.5 * w * w;
        const double c = eBeta + 1.5 / (L * L);
        const double L2 = L * L, L3 = L2 * L, L4 = L2 * L2, L5 = L4 * L;
        const double hyp = std::sqrt(L2 + w * w);
        const double F0 = 2.0 * c * L4 - L2;
        return c * L3 * hyp + (c * L5 - L3) / hyp - F0;
    }

    // Antiderivative of waveshape (for 1st-order ADAA):
    //   F(w) = FT(w) + (a*s^2/2) * (w - s*tanh(w/s)),
    //   since d/dw[w - s*tanh(w/s)] = 1 - sech^2(w/s) = tanh^2(w/s).
    //   FT = coreLimitAD. F(0) = 0 and F is C1, so 1st-order ADAA is well-posed (exact
    // at DC). Stays finite for any w (the core saturates, tanh saturates).
    inline double waveshapeAD(double w) const noexcept
    {
        const double s = sPos, a = sNeg;
        return coreLimitAD(w) + 0.5 * a * s * s * (w - s * std::tanh(w / s));
    }

    // coreLimitAD is elementary for every (beta, L) — unlike the session-14 shape,
    // there is no non-exact regime to fall back from. Kept as a named predicate
    // (rather than deleting the branch in adaaShape) so a future reshape that
    // reintroduces a non-elementary case has an obvious place to wire the fallback
    // back in, and so the "exact at DC" contract stays a documented invariant, not
    // an implicit assumption.
    inline bool adaaExact() const noexcept { return true; }

    // 1st-order ADAA: y = (F(u) - F(uPrev)) / (u - uPrev); midpoint fallback only when
    // the two samples are too close (avoids 0/0, keeps it exact at DC). The previous
    // sample is a PARAMETER, not the `uPrev` member, so the caller controls
    // the pairing — named `prev` so it doesn't shadow that member.
    inline double adaaShape(double u, double prev) const noexcept
    {
        const double du = u - prev;
        if (! adaaExact() || std::abs(du) < 1.0e-9)
            return waveshape(0.5 * (u + prev));
        return (waveshapeAD(u) - waveshapeAD(prev)) / du;
    }

private:
    // Phase-7 capture-fit amplitude params (FitParams.h), nominal-initialised.
    double gm = kGm, ro = kRo, rq2 = kRq2, sPos = kSatPos, sNeg = kSatNeg;
    double cPos = kCeilPos, cNeg = kCeilNeg, eBeta = kExpandBeta;

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
