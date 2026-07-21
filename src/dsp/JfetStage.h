#pragma once

#include <cmath>

// =============================================================================
// Stage 2 — J201 JFET gain stage (Q1 common-source + Q2 active load)
// =============================================================================
// The FIRST nonlinear stage. circuit.md "JFET gain stage (Q1/Q2)". Sits between
// the InputBuffer (IC1_A) and the TrebleAttack treble net: its output IS node G
// (the J201 drain), which TrebleAttack takes as an ideal voltage source for
// Phase 4 (revisit output Z at Phase 7 capture).
//
//   C2 = 1n    coupling from IC1_A into the drive path
//   R4 = 100k  gate-stopper into Q1 gate      | gate draws ~no current, so the
//   R5 = 1M    gate-leak bias to GND          | input HP sees C2 into R4+R5 = 1.1M
//   Q1 = J201  common-source gain JFET (INVERTING)
//   R6 = 3k3   Q1 source degeneration to GND
//   C3 = 220n  || R6, bypasses the degeneration above ~219 Hz -> HF gain lift
//   Q2 = J201  active load (gate @ VD via R9/R10, drain @ +9V, source = output)
//   C4 = 22n   Q2 gate->source(output) bootstrap -> raises the active-load Z
//
// ---- Model: Path B (docs/nonlinear-component-modeling.md §2, recommended) ----
// The J201 is spread ~5:1 part-to-part (Vgs(off) -0.3..-1.5 V, IDSS 0.2..1.0 mA)
// so a nominal SPICE device will NOT match a specific unit — we fit the whole
// Q1/Q2 block to captures. The block is a Wiener-Hammerstein cascade:
//
//   x --[input HP]--[HF-lift shelf]--[ * -G0 ]--[asym soft waveshaper]--> out
//        (C2,R4/R5)   (C3 / R6)      inverting    (JFET/active-load soft sat)
//
//   * Linear filters carry the exact R/C SHAPE (corner frequencies).
//   * -G0 carries the inverting mid-band small-signal gain magnitude.
//   * the waveshaper carries the mild asymmetric soft saturation (even harmonics).
//
// ** ONLY the filter corners (from R/C) and the INVERTING polarity are trustworthy
//    pre-capture. ** Everything amplitude-related below (kG0, kGmR6, the waveshaper
//    saturation levels) is a NOMINAL placeholder from the datasheet Shichman-Hodges
//    operating point — see the "Phase-7 capture carry-forwards" note. The stage is
//    structured so refitting them later is a one-line change and never disturbs the
//    (already-correct) linear filter shape or the polarity.
//
// ---- Linear transfer function (small signal) --------------------------------
//   H(s) = -G0 * HP(s) * shelf(s)
//   HP(s)    = s(R4+R5)C2 / (1 + s(R4+R5)C2)              fc = 144.7 Hz, passband 1
//              (the fixed R5/(R4+R5) gate divider folds into G0)
//   shelf(s) = (1 + s R6 C3) / (1 + s R6 C3/(1+gmR6))     zero 219 Hz, pole ~719 Hz
//              low-freq gain 1, high-freq gain (1+gmR6) = shelfRatio (~3.28)
// All three corners are well below 1 kHz, so — like MasterOut and InputBuffer —
// there is NO audible-band bilinear top-octave warp here (unlike the EQ stages):
// the trapezoidal/bilinear discretisation matches the analytic oracle tightly
// across the WHOLE band. This stage therefore sits OUTSIDE the Phase-6 oversampled
// region for LINEAR purposes, BUT its WAVESHAPER is the aliasing source, so in the
// full chain the stage is oversampled + ADAA'd (build-plan Phase 5/6; the per-side
// tanh has a closed-form antiderivative satN^2 * ln cosh(w/satN) for cheap ADAA).
//
// ---- Discretisation ---------------------------------------------------------
//   Input HP: one physical trapezoidal-companion cap (C2) at a single node
//     (identical convention to MasterOut's HPFs / RecoveryBridgedT).
//   HF shelf: a first-order bilinear IIR from the analog shelf prototype. Bilinear
//     == trapezoidal, so this is the SAME discretisation family as the caps and
//     maps 1:1 onto the oracle's shelf(s) with the (negligible, sub-kHz) warp.
//
// ---- Polarity (circuit.md JFET carry-forward — RESOLVED to inverting) -------
// A common-source stage INVERTS (drain falls as gate rises); Q2 is only an active
// load, so the stage is net INVERTING. circuit.md flagged the sign "unconfirmed"
// and asked for a DC-step test — done here (JfetStageTest: +in -> -out on the AC
// edge). This is the sign the OD path carries into the BLEND node ALONGSIDE the
// CD4049 clipper's inversion (dsp.md "Dry/wet phase alignment ... Polarity"); the
// end-to-end DC-step at BLEND still gets run in Phase 6, but the JFET's own sign
// is no longer an open unknown. (No PolarityInverterT games — the -G0 is the sign.)
//
// ---- Why NO RailClamp here --------------------------------------------------
// RailClamp models a TL07x OP-AMP output hitting its supply rails (calibration §6,
// the "every op-amp stage" GATE item). The J201 drain is NOT an op-amp output —
// its soft limiting against the active load / +9V rail IS the waveshaper below, a
// gentle asymmetric saturation, not the op-amp's dead-linear-then-hard-clamp knee.
// So this stage carries the waveshaper, not a RailClamp.
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
    // kGmR6 = gm*R6, the source-bypass shelf strength (HF lift = 1+gmR6). From the
    //   datasheet Shichman-Hodges self-bias point (Id~=0.12 mA, gm~=0.69 mS).
    // kG0   = inverting mid-band small-signal gain magnitude. The R5/(R4+R5) gate
    //   divider, the C4-bootstrapped active-load impedance, and R7 treble-net
    //   loading all fold in here — genuinely capture-dependent (~5:1 part spread),
    //   so this nominal is only a plausible starting value.
    static constexpr double kGmR6 = 2.277;   // -> shelfRatio 3.277 (+10.3 dB)
    static constexpr double kG0 = 15.0;      // mid-band |gain| (INVERTING via -G0)

    // Waveshaper: per-polarity soft-saturation levels (VD-referenced volts of drain
    // swing). Asymmetric by design (n-/p-side + active-load asymmetry -> the even
    // harmonics the doc requires). Mild nominal (soft, not a hard clip) — the
    // CD4049 downstream does the heavy distorting. FIT satPos/satNeg (and hence the
    // H2/H3 balance) to the drive-min low-frequency-tone captures at Phase 7.
    static constexpr double kSatPos = 3.0;   // positive-drain-swing soft ceiling
    static constexpr double kSatNeg = 2.6;   // negative-swing soft ceiling (asym)

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

    // Phase-7 capture fit (FitParams.h). gmR6 sets the shelf POLE, so changing it
    // must re-derive the shelf coefficients — hence the stored fs and the
    // updateShelf() call (calling this before prepare() is fine; prepare()
    // recomputes from the stored values).
    void setNonlinear(double G0, double GmR6, double satPos, double satNeg) noexcept
    {
        g0 = G0;
        gmR6 = GmR6;
        sPos = satPos;
        sNeg = satNeg;
        updateShelf();
    }

    void reset() noexcept
    {
        ieqC2 = 0.0;
        shelfX1 = shelfY1 = 0.0;
        uPrev = 0.0;
    }

    // 1st-order ADAA on the waveshaper (dsp.md "ADAA"). Off by default so the
    // per-stage FR/DC-step oracle (JfetStageTest) validates the raw memoryless
    // map; PedalChain turns it ON inside the oversampled region (ADAA is IN
    // ADDITION to oversampling, not instead of it). Glitch-free to toggle —
    // uPrev updates every sample regardless.
    void setADAA(bool e) noexcept { adaa = e; }

    // Process one sample (real volts in/out, VD-referenced). NET INVERTING.
    inline double process(double x) noexcept
    {
        // ---- Input HP node (C2 source-side, R4+R5 to GND) -------------------
        // (gc2 + gRin)*vx = gc2*x - ieqC2
        const double vx = (gc2 * x - ieqC2) / (gc2 + gRin);
        ieqC2 = 2.0 * gc2 * (x - vx) - ieqC2; // v_ab = x - vx

        // ---- HF-lift shelf (first-order bilinear IIR) -----------------------
        const double vs = sb0 * vx + sb1 * shelfX1 - sa1 * shelfY1;
        shelfX1 = vx;
        shelfY1 = vs;

        // ---- Inverting gain + asymmetric soft saturation --------------------
        const double u = g0 * vs;
        const double y = adaa ? adaaShape(u, uPrev) : waveshape(u);
        uPrev = u;
        return -y;
    }

private:
    // HF-lift shelf: bilinear (== trapezoidal) first-order IIR.
    // Analog:  shelf(s) = (1 + s*tauZ) / (1 + s*tauP),  tauZ=R6C3, tauP=tauZ/(1+gmR6)
    // Bilinear s = c*(1 - z^-1)/(1 + z^-1),  c = 2*fs :
    //   H(z) = ((1+c*tauZ) + (1-c*tauZ)z^-1) / ((1+c*tauP) + (1-c*tauP)z^-1)
    void updateShelf() noexcept
    {
        const double c = 2.0 * fs;
        const double tauZ = kR6 * kC3;
        const double tauP = tauZ / (1.0 + gmR6);
        const double a0 = 1.0 + c * tauP;
        sb0 = (1.0 + c * tauZ) / a0;
        sb1 = (1.0 - c * tauZ) / a0;
        sa1 = (1.0 - c * tauP) / a0;
    }

    // Per-polarity tanh soft-clip: g(w) = sat * tanh(w/sat). C1-continuous at 0
    // (both sides -> slope 1), asymmetric sat levels -> even harmonics. Reduces to
    // ~identity for |w| << sat (mild).
    inline double waveshape(double w) const noexcept
    {
        const double sat = (w >= 0.0) ? sPos : sNeg;
        return sat * std::tanh(w / sat);
    }

    // Numerically-stable ln(cosh(x)) = |x| + log1p(exp(-2|x|)) - ln2.
    static inline double lncosh(double x) noexcept
    {
        const double a = std::abs(x);
        return a + std::log1p(std::exp(-2.0 * a)) - 0.6931471805599453;
    }

    // Antiderivative of waveshape: F(w) = sat^2 * ln cosh(w/sat) (per polarity).
    // C1-continuous at 0 (both branches -> 0), so 1st-order ADAA is well-posed.
    inline double waveshapeAD(double w) const noexcept
    {
        const double sat = (w >= 0.0) ? sPos : sNeg;
        return sat * sat * lncosh(w / sat);
    }

    // 1st-order ADAA: y = (F(u) - F(uPrev)) / (u - uPrev); midpoint fallback when
    // the two are too close (avoids 0/0), which also keeps it exact at DC.
    inline double adaaShape(double u, double uPrev) const noexcept
    {
        const double du = u - uPrev;
        if (std::abs(du) < 1.0e-7)
            return waveshape(0.5 * (u + uPrev));
        return (waveshapeAD(u) - waveshapeAD(uPrev)) / du;
    }

    // Phase-7 capture-fit amplitude params (FitParams.h), nominal-initialised.
    double g0 = kG0, gmR6 = kGmR6, sPos = kSatPos, sNeg = kSatNeg;

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
