#pragma once

#include <cmath>
#include "../utils/TaperUtils.h"

// =============================================================================
// Stage 7/8 — LEVEL (VR2) + BLEND (VR1) — OD volume + clean/OD crossfade
// =============================================================================
// circuit.md "LEVEL, BLEND (crossfade mix)":
//   LEVEL (VR2) | 100k A taper | OD volume divider: pin3=IC4_A out, pin1=VD,
//                                  wiper=leveled OD → BLEND pin3
//   BLEND (VR1) | 100k B taper | crossfade: pin3=leveled OD, pin1=clean
//                                  (IC1_A out), wiper=mix → IC5_A(+)
//
// ---- Resistive network (AC-referenced to VD) --------------------------------
// Both inputs (clean and OD) sit on the same DC bias VD = 4.5 V, so the DC
// component cancels in the crossfade — only the AC signal matters.
//
//   Vo(OD) ── Rup ── Vw ── Rdn ── GND(VD)
//                     │
//                ┌────┴────┐
//                │  BLEND   │  100k B-taper
//                │          │
//          pin3 ◄┤ R_od     ├─ wiper ── Vout ──▶ IC5_A(+)
//                │          │
//          pin1 ◄┤ R_cl     │
//                └────┬─────┘
//   Vc(clean) ────────┘
//
// LEVEL pot (100k A) split: Rup = (1-L)*100k, Rdn = L*100k
// BLEND pot (100k B) split: R_od = (1-B)*100k, R_cl = B*100k
// where L = levelTaper(x_level, ...) ∈ [0,1]  — a 4-segment PWL since s163;
//         ⛔ NOT a power law any more, see the constants block below
//       B = x_blend (linear — B-taper)
//
// KCL at Vw (LEVEL wiper):
//   (Vo - Vw)/Rup = Vw/Rdn + (Vw - Vc)/100k
//
// Solved for Vw:
//   Vw = (Vo/(1-L) + Vc) / (1/(1-L) + 1/L + 1)
//
// Output (BLEND wiper):
//   Vout = (1-B)*Vc + B*Vw
//
// ---- Loading effect ---------------------------------------------------------
// The BLEND pot loads the LEVEL divider because BLEND's OD-side segment
// (R_od = (1-B)*100k) connects the LEVEL wiper to the BLEND wiper. Since the
// BLEND wiper output goes to a high-Z op-amp input (IC5_A+), the entire BLEND
// pot conducts I = (Vw-Vc)/100k, which flows through R_od AND R_cl.
//
// This current through R_od (= (1-B)*100k from LEVEL wiper to BLEND wiper) and
// R_cl (= B*100k from BLEND wiper to clean input) creates the asymmetric OD-vs-
// clean loading effect. At LEVEL=noon/BLEND=noon the OD path gain is ~3.3 dB
// below the ideal unloaded divider prediction (matching the pedal's real
// behaviour — confirmed by the blend-0700/1200 captures at Phase 7).
//
// The clean side has source impedance ~0 Ω (IC1_A op-amp output); the OD side
// has source impedance ~0 Ω (IC4_A op-amp output) but the LEVEL wiper's
// equivalent Thevenin impedance is Rup||Rdn = L*(1-L)*100k, maximal (~25k) at
// mid-rotation. This is why the crossfade law is asymmetric.
//
// ---- dist_engage override ---------------------------------------------------
// When dist_engage = false, the output is forced to 100% clean (Vc), ignoring
// the BLEND knob. This implements the [ENG] DIST footswitch behaviour per
// circuit.md "Footswitches". The ~5ms crossfade smoothing for this override is
// deferred to Phase 6 (the BLEND crossfade itself must not be wired before
// Phase 6's delay-compensation line exists — build-plan risk #8).
//
// ---- Polarity ---------------------------------------------------------------
// Both paths are non-inverting (resistive dividers). The polarity concern at
// the BLEND summing node (J201 unconfirmed sign + clipper's known −48.5 gain)
// will be resolved with an end-to-end DC-step test at Phase 6.
// =============================================================================
class LevelBlend
{
public:
    LevelBlend() = default;

    // ---- LEVEL audio-taper shape — FOUR-SEGMENT PIECEWISE LINEAR -------------
    // ⭐⭐ SESSION 163 — THE POWER LAW IS RETIRED (`kLevelTaperExp = 1.43`, then
    // `FitParams::levelTaperExp = 2.25` from session 8). The wiper reaches
    // `Frac_i` of full resistance at rotation `Break_i`; linear in between and
    // either side. Both endpoints are EXACT by construction and no parameter can
    // move them, which the topology requires:
    //   x = 0 → 0 (wiper on VD, no OD)   x = 1 → 1 (the bleed-free anchor).
    //
    // ⚠⚠ THAT SECOND ENDPOINT IS LOAD-BEARING FAR BEYOND THIS STAGE. L(1) = 1
    // makes the clean coefficient EXACTLY zero at LEVEL = BLEND = max, and that
    // exact zero is the bleed-free corner every absolute instrument in the
    // project anchors on (GATE K7's ratio, GATE O's A3 ledger, GATE L's |rho|,
    // `OdToneRestore`'s base row, GATE W/AE's bleed-free membership). GATE AZ6
    // asserts it is bit-identical across this change.
    //
    // WHY IT MOVED, in one line: measured against the pedal's own LEVEL ladder,
    // the shipped power law is 2.844 dB rms out (worst 7.638) where a free
    // monotone curve reaches 0.344 — and 0.344 is inside the target's OWN
    // across-stimulus ambiguity of 0.755 dB. GATE K's closure (s103, "THE TAPER
    // CANNOT FIX IT") was measured on the single-EXPONENT family, and "no single
    // exponent reaches" is a different claim from "no monotone taper reaches" —
    // the distinction s115/s146 were already forced to draw on the MASTER pot.
    // Full derivation: GATE AY (`analysis/level_taper_reshape.py`, s162) and
    // GATE AZ (`analysis/level_taper_fit.py`, s163).
    //
    // ⭐⭐ WHY FOUR SEGMENTS AND NOT THREE (s146's MASTER precedent is a FAMILY,
    // not a number): 3 segments reaches only 0.480 dB rms and misplaces the
    // 0.875 detent by 0.19 in L, with a sign-alternating residual; 4 reaches
    // 0.340 — the architectural floor — and a 5-segment control returns the
    // 4-segment answer to the digit, so the family SATURATES at 4. That is the
    // stopping proof, not a parameter-count argument. And the fitted curve sits
    // INSIDE the requirement's own per-detent spread at EVERY detent (worst
    // 0.085 of it), which is the overfitting test in the constant's own units.
    //
    // ⭐ Outside corroboration no term of the objective knew about: the segment
    // slopes RISE monotonically (0.174 → 0.413 → 0.791 → 4.034, i.e. convex — a
    // physically buildable resistive track), and the half-rotation fraction goes
    // 21.02 % → 15.41 %, TOWARD the textbook A-taper 10–15 % band that
    // circuit.md specifies for VR2 (100k A). `LevelBlendTest` Test 0 asserts the
    // shape and FAILS if convexity, monotonicity or an endpoint is lost.
    //
    // ⚠ The last segment is a LOWER bound on its own steepness: GATE AY3 reports
    // the LEVEL-max requirement as `above` (the pedal wants more than L = 1 can
    // deliver), so it is clamped by the anchor rather than met.
    static constexpr double kLevelTaperBreak1 = 0.219415;
    static constexpr double kLevelTaperFrac1 = 0.038146;
    static constexpr double kLevelTaperBreak2 = 0.529680;
    static constexpr double kLevelTaperFrac2 = 0.166340;
    static constexpr double kLevelTaperBreak3 = 0.857645;
    static constexpr double kLevelTaperFrac3 = 0.425688;

    // The taper itself, as a free function so tests, the oracle and any future
    // consumer read ONE implementation rather than rebuilding the curve from the
    // constants — the s146 `masterTaperBreak` trap, where four consumers would
    // each have silently rebuilt a two-segment curve from a renamed parameter.
    static constexpr double levelTaper(double x, double b1, double f1, double b2, double f2,
                                       double b3, double f3) noexcept
    {
        return (x <= 0.0)  ? 0.0
             : (x >= 1.0)  ? 1.0
             : (x <= b1)   ? (f1 * x / b1)
             : (x <= b2)   ? (f1 + (f2 - f1) * (x - b1) / (b2 - b1))
             : (x <= b3)   ? (f2 + (f3 - f2) * (x - b2) / (b3 - b2))
                           : (f3 + (1.0 - f3) * (x - b3) / (1.0 - b3));
    }

    void prepare(double /*sampleRate*/) noexcept {}

    void reset() noexcept {}

    void setLevel(double x) noexcept
    {
        // x ∈ [0,1]. L = 0 → wiper at VD (min OD), L = 1 → wiper at OD input.
        knob = x;
        // Fall back to the compiled defaults unless the WHOLE set is ordered and
        // in range — a partially-valid set would silently produce a curve that is
        // not monotone, i.e. not a pot law at all (MasterOut::setMaster's guard,
        // which exists for the same reason).
        const bool ok = tb1 > 1.0e-9 && tb1 < tb2 && tb2 < tb3 && tb3 < 1.0
                        && tf1 > 0.0 && tf1 < tf2 && tf2 < tf3 && tf3 < 1.0;
        L = ok ? levelTaper(x, tb1, tf1, tb2, tf2, tb3, tf3)
               : levelTaper(x, kLevelTaperBreak1, kLevelTaperFrac1, kLevelTaperBreak2,
                            kLevelTaperFrac2, kLevelTaperBreak3, kLevelTaperFrac3);
    }

    // Capture fit (FitParams.h): re-applies the CURRENT knob position through the
    // new curve, so a taper refit doesn't leave a stale L behind.
    void setTaper(double b1, double f1, double b2, double f2, double b3, double f3) noexcept
    {
        tb1 = b1; tf1 = f1;
        tb2 = b2; tf2 = f2;
        tb3 = b3; tf3 = f3;
        setLevel(knob);
    }

    void setBlend(double x) noexcept
    {
        // x ∈ [0,1], B-taper = linear.
        // B = 0 → output = clean, B = 1 → output = leveled OD.
        B = x;
    }

    void setDistEngage(bool engage) noexcept { distEngage = engage; }

    // Fraction of the OUTPUT that is clean-tap signal, in [0,1].
    //
    // ⭐ Derived by EVALUATING `process` itself with unit inputs rather than by re-deriving the
    // divider algebra.  `process` is linear in (cleanIn, odIn) — it is a weighted sum — so
    // superposition gives its two coefficients exactly, and this accessor therefore CANNOT drift
    // from what the stage actually does, including at the analytic endpoints and under
    // dist-disengage (which correctly reports 1.0, i.e. all clean).  Re-deriving it instead
    // would be the s113 trap (a shipped stage's closed form takes the STAGE's input, not the
    // knob) plus a second copy of the network to keep in sync.
    //
    // `OdToneRestore` reads this: it sits in the OD path, upstream of here, so how much cut its
    // 320 Hz notch must apply to land the COMPOSITE null on the pedal's depends entirely on how
    // much clean signal is about to be summed on top of it.  GATE AT measured that dependence
    // and showed it collapses onto this single scalar (many LEVEL/BLEND routes to the same value
    // agree to 0.03-0.05 dB), which is what makes one number sufficient here.
    double cleanFraction() const noexcept
    {
        const double od = process(0.0, 1.0);
        const double cl = process(1.0, 0.0);
        const double sum = od + cl;
        return sum > 0.0 ? cl / sum : 1.0;
    }

    // Process one sample: return mixed output.
    // cleanIn = signal from IC1_A clean tap (VD-referenced AC voltage).
    // odIn    = signal from IC4_A Sallen-Key output (VD-referenced AC voltage).
    inline double process(double cleanIn, double odIn) const noexcept
    {
        // dist_engage override: 100% clean.
        if (!distEngage)
            return cleanIn;

        // LEVEL divider wiper voltage (loaded by BLEND pot).
        // Handle endpoints analytically to avoid division by zero.
        double vw;
        if (L <= 0.0)
        {
            vw = 0.0; // wiper at GND (VD)
        }
        else if (L >= 1.0)
        {
            vw = odIn; // wiper at OD input (no drop)
        }
        else
        {
            const double invRup = 1.0 / (1.0 - L);
            const double invRdn = 1.0 / L;
            const double invTotal = invRup + invRdn + 1.0;
            // Vw = (odIn/(1-L) + cleanIn) / (1/(1-L) + 1/L + 1)
            vw = (odIn * invRup + cleanIn) / invTotal;
        }

        // BLEND wiper voltage = linear crossfade. Branch at the extremes instead of
        // relying on (1-B)*cleanIn / B*vw to reach zero — 0.0*NaN/Inf is NOT zero
        // under IEEE 754, so a non-finite sample on the side being "zeroed out"
        // (e.g. odIn destabilising while BLEND is fully clean) would otherwise leak
        // straight through the crossfade.
        if (B <= 0.0)
            return cleanIn;
        if (B >= 1.0)
            return vw;
        return (1.0 - B) * cleanIn + B * vw;
    }

private:
    double L = 1.0; // LEVEL taper-mapped position [0,1] (default = max OD)
    double B = 0.0; // BLEND position [0,1] (default = 100% clean)
    bool distEngage = true; // true = normal BLEND behaviour
    // Capture-fit taper shape + the knob position it was applied to. Defaults are
    // the fitted s163 values, so a default-constructed LevelBlend matches the
    // shipped FitParams.
    double tb1 = kLevelTaperBreak1, tf1 = kLevelTaperFrac1;
    double tb2 = kLevelTaperBreak2, tf2 = kLevelTaperFrac2;
    double tb3 = kLevelTaperBreak3, tf3 = kLevelTaperFrac3;
    double knob = 1.0;

    LevelBlend(const LevelBlend&) = delete;
    LevelBlend& operator=(const LevelBlend&) = delete;
};
