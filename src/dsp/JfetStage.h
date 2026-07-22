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
//        (C2,R4/R5)  R5/(R4+R5)  (C3/R6)     (vgs nonlinearity)
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
// drain is not an op-amp output. NOTE (carry-forward): the square-law shaper is
// still UNBOUNDED (g(w) -> w + a*s^2 asymptotically), so nothing here limits a
// large drive; the explicit asymmetric drain-current ceiling is the next
// calibration step. The explicit loading above does now bound the VOLTAGE gain
// far more realistically than the old ideal-source boundary did.
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
    // Nominal is deliberately mild and monotonic (|a|*s = 0.5 << 2); the CD4049
    // downstream does the heavy distorting.
    static constexpr double kSatPos = 0.5;   // s: square-law knee (gate volts)
    static constexpr double kSatNeg = 1.0;   // a: even-harmonic strength (signed)

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
    void setNonlinear(double Gm, double Ro, double Rq2, double satPos, double satNeg) noexcept
    {
        gm = (Gm > 1.0e-9) ? Gm : 1.0e-9; // rp = ro*gm*R6 must stay non-degenerate
        ro = Ro;
        rq2 = Rq2;
        sPos = satPos;
        sNeg = satNeg;
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

    // J201 SQUARE-LAW soft-shaper (Phase-7 capture finding, 2026-07-22): replaces the
    // former per-polarity tanh. The real B7K's low-drive OD character is even-dominant
    // (captured H2 ~= -36 dB, H3 ~= -59 dB @ drive-min: a ~23 dB even/odd separation) —
    // the fingerprint of a JFET common-source SQUARE-LAW transfer (Id ~ (Vgs-Vt)^2 ->
    // pure H2). A tanh is an ODD map: its w^3 term forces H3 whenever it makes H2, so it
    // structurally cannot reach that separation (proven by fit — the tanh floored H3 at
    // ~-50 dB while the capture sits at -59). This shape is LINEAR + EVEN:
    //     g(w) = w + a * s^2 * (1 - sech(w/s))
    // The odd part is PURELY LINEAR (w) -> ZERO intrinsic H3; the even bump
    // a*s^2*(1 - sech(w/s)) generates H2/H4 only. Slope at 0 is exactly 1 (so `gm`
    // alone remains the small-signal transconductance); g'(w) = 1 + a*s*sech(w/s)*
    // tanh(w/s), and max|sech*tanh| = 1/2 (at tanh^2 = 1/2), so it is monotonic iff
    // **|a|*s < 2**. ** Do NOT write 2.598 here — that is 1/max(sech^2*tanh), a
    // DIFFERENT extremum, and it was wrong in this comment until 2026-07-22
    // (dsp-validator caught it). The error is not academic: the step-2 run-2 fit
    // candidate s=10.585/a=0.232 gives |a|*s = 2.456, min slope -0.21, i.e. a FOLD-BACK
    // inside the signal range. Any fitter must constrain |a|*s < 2. **
    // NOTE the argument is now the effective vgs (real gate volts) — see the header
    // note on the 2026-07-22 restructure; old fitted s/a values do not carry over.
    inline double waveshape(double w) const noexcept
    {
        const double sech = 1.0 / std::cosh(w / sPos);
        return w + sNeg * sPos * sPos * (1.0 - sech);
    }

    // Gudermannian gd(x) = integral of sech = 2*atan(tanh(x/2)) — a bounded/stable form
    // of atan(sinh(x)) (no sinh overflow). Odd, gd(0) = 0.
    static inline double gd(double x) noexcept
    {
        return 2.0 * std::atan(std::tanh(0.5 * x));
    }

    // Antiderivative of waveshape (for 1st-order ADAA):
    //   F(w) = w^2/2 + a*s^2 * (w - s*gd(w/s)),   d/dw[w - s*gd(w/s)] = 1 - sech(w/s).
    // F(0) = 0 and F is C1, so 1st-order ADAA is well-posed (exact at DC).
    inline double waveshapeAD(double w) const noexcept
    {
        const double s = sPos, a = sNeg;
        return 0.5 * w * w + a * s * s * (w - s * gd(w / s));
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

    // Phase-7 capture-fit amplitude params (FitParams.h), nominal-initialised.
    double gm = kGm, ro = kRo, rq2 = kRq2, sPos = kSatPos, sNeg = kSatNeg;

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
