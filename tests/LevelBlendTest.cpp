// =============================================================================
// LevelBlend (VR2 LEVEL + VR1 BLEND) — passive pot network validation
// =============================================================================
// Validates the loaded resistive network against the analytic oracle
// (analysis/eq_reference.py :: level_blend_tf). Since the stage is purely
// resistive, FR is flat — validate DC gain at key knob positions:
//   1. LEVEL=0 (CCW) — OD fully off, output = (1-B)*clean
//   2. LEVEL=1 (CW), BLEND=0 — 100% clean
//   3. LEVEL=1 (CW), BLEND=1 — 100% OD (no loading)
//   4. Noon/noon — loading effect (OD below ideal unloaded divider)
//   5. dist_engage=false — output = clean regardless of BLEND
//   6. DC-step polarity — both paths non-inverting
// =============================================================================

#include "../src/dsp/LevelBlend.h"

#include <cmath>
#include <cstdio>

// -----------------------------------------------------------------------------
// Analytic oracle: level_blend_tf(level, blend, vo, vc, taperExp)
// Returns Vout given Vo (OD input) and Vc (clean input), using the same
// power-law taper for LEVEL as the C++ stage.
// -----------------------------------------------------------------------------
static double levelBlendOracle(double level, double blend,
                               double vo, double vc, double taperExp)
{
    const double L = (level <= 0.0) ? 0.0
                   : (level >= 1.0) ? 1.0
                   : std::pow(level, taperExp);
    const double B = blend;

    double vw;
    if (L <= 0.0)
        vw = 0.0;
    else if (L >= 1.0)
        vw = vo;
    else
    {
        const double invRup = 1.0 / (1.0 - L);
        const double invRdn = 1.0 / L;
        const double invTotal = invRup + invRdn + 1.0;
        vw = (vo * invRup + vc) / invTotal;
    }
    return (1.0 - B) * vc + B * vw;
}

// -----------------------------------------------------------------------------
// Helper: measure DC output at a given (level, blend) for the C++ stage.
// measureVout(level, blend, cleanAmp, odAmp) — note the clean/od order.
// -----------------------------------------------------------------------------
static double measureVout(double level, double blend,
                          double cleanAmp, double odAmp)
{
    LevelBlend stage;
    stage.prepare(48000.0);
    stage.setLevel(level);
    stage.setBlend(blend);
    stage.setDistEngage(true);
    for (int n = 0; n < 10; ++n)
        stage.process(cleanAmp, odAmp);
    return stage.process(cleanAmp, odAmp);
}

// -----------------------------------------------------------------------------
// Test helpers
// -----------------------------------------------------------------------------
static int failures = 0;

static void check(const char* label, double measured, double expected,
                  double toleranceDb)
{
    const bool zero = (measured == 0.0 && expected == 0.0);
    const double errDb = zero ? 0.0
        : std::abs(20.0 * std::log10(std::abs(measured) / std::abs(expected)));
    const bool pass = errDb <= toleranceDb || zero;
    std::printf("  %-50s meas=%+.6f  oracle=%+.6f  err=%.4f dB  %s\n",
                label, measured, expected, errDb, pass ? "PASS" : "FAIL");
    if (!pass)
        ++failures;
}

int main()
{
    constexpr double p = LevelBlend::kLevelTaperExp;
    constexpr double tol = 0.001; // ±0.001 dB (purely resistive, no freq-dep error)

    // ---- Test 1: LEVEL=0 → OD fully off --------------------------------
    // When LEVEL=0, LEVEL wiper is at VD — no OD contribution.
    // At any BLEND position, output should be (1-B)*clean.
    // ---------------------------------------------------------------------
    std::printf("=== Test 1: LEVEL=0 (OD fully off) ===\n");
    for (double b = 0.0; b <= 1.0; b += 0.5)
    {
        const double r = measureVout(0.0, b, 1.0, 1.0);
        // Both inputs 1V: clean=1, OD=1. Oracle: vo=1, vc=1.
        const double exp = levelBlendOracle(0.0, b, 1.0, 1.0, p);
        char label[64];
        std::snprintf(label, sizeof(label), "LEVEL=0 BLEND=%.1f (both 1V)", b);
        check(label, r, exp, tol);
    }

    // ---- Test 2: LEVEL=1, BLEND=0 → 100% clean -------------------------
    std::printf("\n=== Test 2: LEVEL=1, BLEND=0 (100%% clean) ===\n");
    {
        const double r = measureVout(1.0, 0.0, 1.0, 1.0);
        const double exp = levelBlendOracle(1.0, 0.0, 1.0, 1.0, p);
        check("LEVEL=1 BLEND=0 (both 1V)", r, exp, tol);
        // At LEVEL=1/BLEND=0 the output should be pure clean (1.0).
        const bool cleanOnly = std::abs(r - 1.0) < 1e-9;
        std::printf("  %-50s %s\n", "output = clean (1.0):",
                     cleanOnly ? "PASS" : "FAIL");
        if (!cleanOnly)
            ++failures;
    }

    // ---- Test 3: LEVEL=1, BLEND=1 → 100% OD (no loading) --------------
    // When LEVEL=1, the LEVEL wiper is at the OD input (Rup=0), so no
    // loading from the BLEND pot. Output = OD directly.
    // ---------------------------------------------------------------------
    std::printf("\n=== Test 3: LEVEL=1, BLEND=1 (100%% OD, no loading) ===\n");
    {
        // clean=0, OD=1 → output should be OD=1 (no loading at LEVEL=1).
        const double r = measureVout(1.0, 1.0, 0.0, 1.0);
        const double exp = levelBlendOracle(1.0, 1.0, 1.0, 0.0, p);
        check("LEVEL=1 BLEND=1 (OD only)", r, exp, tol);
        const bool odOnly = std::abs(r - 1.0) < 1e-9;
        std::printf("  %-50s %s\n", "output = OD (1.0):",
                     odOnly ? "PASS" : "FAIL");
        if (!odOnly)
            ++failures;
    }

    // ---- Test 4: Loading effect at noon/noon ---------------------------
    // At LEVEL=0.5 (audio-tapered to L≈0.371), BLEND=0.5, the OD path
    // gain is loaded by the BLEND pot drawing current through the LEVEL
    // divider. The loading deficit is ~1.8 dB at the power-law taper's
    // noon (not ~3.5 dB, which was computed for an ideal linear L=0.5).
    // ---------------------------------------------------------------------
    std::printf("\n=== Test 4: Loading at noon/noon ===\n");
    {
        // OD only: clean=0, OD=1.
        const double r = measureVout(0.5, 0.5, 0.0, 1.0);
        const double exp = levelBlendOracle(0.5, 0.5, 1.0, 0.0, p);

        const double L = std::pow(0.5, p);
        const double idealOdGain = L * 0.5;
        const double loadingDb = 20.0 * std::log10(r / idealOdGain);
        std::printf("  L=%.4f, B=0.5\n", L);
        std::printf("  loaded OD gain:  %.6f  (%.3f dB)\n", r, 20.0*std::log10(r));
        std::printf("  ideal OD gain:   %.6f  (%.3f dB)\n", idealOdGain, 20.0*std::log10(idealOdGain));
        std::printf("  loading deficit: %.2f dB (expect ~ −2.0 to −1.5 dB for p=1.43)\n", loadingDb);

        check("LEVEL=0.5 BLEND=0.5 (OD only)", r, exp, tol);

        // Verify loading deficit is in the ~1-3 dB range (less than ideal L=0.5
        // because the power-law taper at noon gives L≈0.371 → lower wiper Z).
        const bool loadingPresent = loadingDb < -1.0 && loadingDb > -3.0;
        std::printf("  %-50s %s\n", "loading deficit ~1-3 dB range:",
                     loadingPresent ? "PASS" : "FAIL");
        if (!loadingPresent)
            ++failures;

        // Clean path gain is also affected (loaded up by the BLEND network).
        const double rClean = measureVout(0.5, 0.5, 1.0, 0.0);
        const double idealCleanGain = 0.5;
        const double cleanLoadingDb = 20.0 * std::log10(rClean / idealCleanGain);
        std::printf("  clean path loaded gain: %.4f (ideal %.4f, offset %.2f dB)\n",
                     rClean, idealCleanGain, cleanLoadingDb);
    }

    // ---- Test 5: dist_engage=false → 100% clean ------------------------
    std::printf("\n=== Test 5: dist_engage=false (override to clean) ===\n");
    {
        LevelBlend stage;
        stage.prepare(48000.0);
        stage.setLevel(1.0);
        stage.setBlend(1.0);
        stage.setDistEngage(false);

        double y = 0.0;
        for (int n = 0; n < 10; ++n)
            y = stage.process(1.0, 3.0); // clean=1V, OD=3V
        const bool cleanOverride = std::abs(y - 1.0) < 1e-9;
        std::printf("  dist_engage=false: output=%.6f (expect 1.0 clean): %s\n",
                     y, cleanOverride ? "PASS" : "FAIL");
        if (!cleanOverride)
            ++failures;

        stage.setDistEngage(true);
        y = 0.0;
        for (int n = 0; n < 10; ++n)
            y = stage.process(1.0, 3.0);
        // LEVEL=1, BLEND=1 → output = OD = 3.0
        const bool normalBlend = std::abs(y - 3.0) < 1e-9;
        std::printf("  dist_engage=true:  output=%.6f (expect 3.0 OD): %s\n",
                     y, normalBlend ? "PASS" : "FAIL");
        if (!normalBlend)
            ++failures;
    }

    // ---- Test 6: DC-step polarity (non-inverting both paths) ------------
    std::printf("\n=== Test 6: DC-step polarity (non-inverting) ===\n");
    {
        const double rClean = measureVout(0.5, 0.5, 1.0, 0.0);
        const bool cleanPos = rClean > 0.0;
        std::printf("  clean path: Vout=%.6f (positive -> positive): %s\n",
                     rClean, cleanPos ? "PASS" : "FAIL");
        if (!cleanPos)
            ++failures;

        const double rOd = measureVout(0.5, 0.5, 0.0, 1.0);
        const bool odPos = rOd > 0.0;
        std::printf("  OD path:   Vout=%.6f (positive -> positive): %s\n",
                     rOd, odPos ? "PASS" : "FAIL");
        if (!odPos)
            ++failures;

        const double rBoth = measureVout(0.5, 0.5, 1.0, 1.0);
        const bool bothPos = rBoth > 0.0;
        std::printf("  both:      Vout=%.6f (both positive -> positive): %s\n",
                     rBoth, bothPos ? "PASS" : "FAIL");
        if (!bothPos)
            ++failures;
    }

    // ---- Test 7: Sweep across knob space --------------------------------
    std::printf("\n=== Test 7: Sweep across knob space ===\n");
    const struct { double level; double blend; double vc; double vo; } kPoints[] = {
        { 0.0, 0.0, 1.0, 0.0 },
        { 0.0, 1.0, 1.0, 0.0 },
        { 0.25, 0.75, 1.0, 1.0 },
        { 0.75, 0.25, 1.0, 1.0 },
        { 1.0, 0.5, 1.0, 0.0 },
        { 0.5, 0.0, 1.0, 1.0 },
        { 0.5, 1.0, 1.0, 1.0 },
    };
    for (const auto& pt : kPoints)
    {
        // measureVout takes (cleanAmp, odAmp) = (vc, vo).
        // Oracle takes (vo, vc).
        const double r = measureVout(pt.level, pt.blend, pt.vc, pt.vo);
        const double exp = levelBlendOracle(pt.level, pt.blend, pt.vo, pt.vc, p);
        char label[64];
        std::snprintf(label, sizeof(label), "L=%.2f B=%.2f", pt.level, pt.blend);
        check(label, r, exp, tol);
    }

    // ---- Summary ----------------------------------------------------------
    std::printf("\n%s\n", failures == 0 ? "All tests passed." : "Some tests FAILED.");
    return (failures > 0) ? 1 : 0;
}
