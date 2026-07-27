#pragma once

#include <cmath>

// =============================================================================
// Stage 5 — CD4049UBE CMOS-inverter clipper (IC3) + GRUNT bank  [THE distortion]
// =============================================================================
// circuit.md "CLIPPER" + "GRUNT switch". The audible overdrive of the pedal.
// A single unbuffered-CD4049 inverter section wired as a shunt-feedback inverting
// amp, self-biased to its own transition point, clipping softly against its own
// (R19-dropped) CMOS rails. NOT a diode clipper — D1/D2 are rail clamps at node W
// that (as verified by the test) never conduct in normal operation.
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
// through the feedback), so it is solved by Newton iteration on node W — cheap
// (F is nearly linear except in saturation; warm-started from the previous sample,
// ~2-4 iters). Both reactive elements (Cg, C14) are trapezoidal companion caps,
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

    // D1/D2 clamp window on node W, VD_eff-referenced (0 = trip point Vm = satLo
    // above GND). D1: W_abs <= +9.6 -> w <= 9.6 - Vm ; D2: W_abs >= -0.6 -> w >=
    // -0.6 - Vm. Wide vs the ~+-0.3 V that the feedback-regulated node actually
    // reaches, so these essentially never fire (the test asserts it).
    // NOTE these TRACK satLo — the clamp window is referenced to the trip point,
    // so refitting the saturation levels moves the window with it (the absolute
    // +9.6 / -0.6 V rail references are what stay fixed).
    static constexpr double kClampHi = 9.6 - kSatLo;  // +6.45 V
    static constexpr double kClampLo = -0.6 - kSatLo; // -3.75 V

    // Phase-7 capture fit (FitParams.h). Recomputes the derived clamp window.
    void setNonlinear(double A0, double sLo, double sHi, double k = kHardness) noexcept
    {
        a0 = A0;
        satLo = sLo;
        satHi = sHi;
        hardness = k;
        clampHi = 9.6 - satLo;
        clampLo = -0.6 - satLo;
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

        // ---- Newton solve for node W ----------------------------------------
        double w = wPrev; // warm start
        for (int it = 0; it < kNewtonIters; ++it)
        {
            const double f = gIn * (x - w) - ic + gFb * (vtc(w) - w) - ieq14;
            const double fp = -gIn + gFb * (vtcDeriv(w) - 1.0);
            const double dw = f / fp;
            w -= dw;
            if (std::abs(dw) < 1e-12)
                break;
        }

        // ---- D1/D2 rail clamps at node W (normally inert) -------------------
        if (w > clampHi)
            w = clampHi;
        else if (w < clampLo)
            w = clampLo;

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
    static constexpr int kNewtonIters = 6;

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
    // monotone decreasing and the Newton solve keeps its global-convergence
    // property (F'(W) remains a sum of strictly negative terms).
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
    double clampHi = kClampHi, clampLo = kClampLo; // derived from satLo
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
