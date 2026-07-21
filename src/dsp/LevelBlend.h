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
// where L = powerLawTaper(x_level, 1.0, kLevelTaperExp) ∈ [0,1]
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

    // Taper exponent for LEVEL's audio taper (power law, per dsp.md §tapers).
    // p ≈ 1.43 is a reasonable starting guess for a real audio pot. Fit to
    // captures at Phase 7.
    static constexpr double kLevelTaperExp = 1.43;

    void prepare(double /*sampleRate*/) noexcept {}

    void reset() noexcept {}

    void setLevel(double x) noexcept
    {
        // x ∈ [0,1], audio taper via power law: L = x^p.
        // L = 0 → wiper at VD (min OD), L = 1 → wiper at OD input (max OD).
        knob = x;
        L = pedal::taper::powerLawTaper(x, 1.0, levelTaperExp);
    }

    // Phase-7 capture fit (FitParams.h): re-applies the CURRENT knob position
    // through the new curve, so a taper refit doesn't leave a stale L behind.
    void setTaperExp(double p) noexcept
    {
        levelTaperExp = p;
        setLevel(knob);
    }

    void setBlend(double x) noexcept
    {
        // x ∈ [0,1], B-taper = linear.
        // B = 0 → output = clean, B = 1 → output = leveled OD.
        B = x;
    }

    void setDistEngage(bool engage) noexcept { distEngage = engage; }

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
    // Phase-7 capture-fit taper shape + the knob position it was applied to.
    double levelTaperExp = kLevelTaperExp;
    double knob = 1.0;

    LevelBlend(const LevelBlend&) = delete;
    LevelBlend& operator=(const LevelBlend&) = delete;
};
