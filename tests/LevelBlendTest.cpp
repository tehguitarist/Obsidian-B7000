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
// Analytic oracle: level_blend_tf(level, blend, vo, vc)
// Returns Vout given Vo (OD input) and Vc (clean input).
//
// ⚠ s163: the LEVEL taper is a FOUR-SEGMENT PWL, not a power law. The oracle
// calls `LevelBlend::levelTaper` rather than rebuilding the curve from the
// constants — deliberately. Re-deriving it here would make this test able to
// pass while the stage and the oracle disagree about the SHAPE, which is exactly
// the s146 `masterTaperBreak` failure (four consumers each rebuilding a curve
// from a renamed parameter). What the oracle independently checks is the
// NETWORK, which is what it was written for; the taper's own shape is asserted
// on its own terms by Test 0 below.
// -----------------------------------------------------------------------------
static double levelTaperShipped(double x)
{
    return LevelBlend::levelTaper(x, LevelBlend::kLevelTaperBreak1, LevelBlend::kLevelTaperFrac1,
                                  LevelBlend::kLevelTaperBreak2, LevelBlend::kLevelTaperFrac2,
                                  LevelBlend::kLevelTaperBreak3, LevelBlend::kLevelTaperFrac3);
}

static double levelBlendOracle(double level, double blend,
                               double vo, double vc)
{
    const double L = (level <= 0.0) ? 0.0
                   : (level >= 1.0) ? 1.0
                   : levelTaperShipped(level);
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
    constexpr double tol = 0.001; // ±0.001 dB (purely resistive, no freq-dep error)

    // ---- Test 0: the TAPER's own shape (session 163) --------------------
    // The MasterOutTest Test-0 pattern, for the same reason: the taper is now a
    // multi-segment PWL, so the properties that make it a POT LAW at all are
    // separate claims from the network the oracle checks, and none of them is
    // implied by a good residual. A segment-boundary off-by-one, a lost
    // ordering, or a re-fit that quietly breaks convexity shows up here and
    // NOWHERE else in the suite.
    // ---------------------------------------------------------------------
    std::printf("=== Test 0: LEVEL taper shape (4-segment PWL) ===\n");
    {
        // (a) endpoints EXACT — L(1) = 1 is the bleed-free anchor every absolute
        //     instrument in the project reads at (GATE AZ6).
        const bool e0 = levelTaperShipped(0.0) == 0.0;
        const bool e1 = levelTaperShipped(1.0) == 1.0;
        std::printf("  %-50s %s\n", "L(0) == 0 exactly", e0 ? "PASS" : "FAIL");
        std::printf("  %-50s %s\n", "L(1) == 1 exactly", e1 ? "PASS" : "FAIL");
        failures += (!e0) + (!e1);

        // (b) strictly monotone in the knob — a non-monotone curve is not a pot
        //     taper whatever its residual.
        bool mono = true;
        double prev = -1.0;
        for (int i = 0; i <= 2000; ++i)
        {
            const double v = levelTaperShipped(i / 2000.0);
            if (v < prev - 1e-15)
                mono = false;
            prev = v;
        }
        std::printf("  %-50s %s\n", "strictly monotone over [0,1]", mono ? "PASS" : "FAIL");
        failures += !mono;

        // (c) segment slopes must RISE (convex) — what a real audio track is, and
        //     a property no term of the fit objective asked for.
        const double bs[5] = {0.0, LevelBlend::kLevelTaperBreak1, LevelBlend::kLevelTaperBreak2,
                              LevelBlend::kLevelTaperBreak3, 1.0};
        const double fs[5] = {0.0, LevelBlend::kLevelTaperFrac1, LevelBlend::kLevelTaperFrac2,
                              LevelBlend::kLevelTaperFrac3, 1.0};
        bool convex = true, ordered = true;
        double lastSlope = -1.0;
        for (int i = 0; i < 4; ++i)
        {
            if (!(bs[i] < bs[i + 1]) || !(fs[i] < fs[i + 1]))
                ordered = false;
            const double s = (fs[i + 1] - fs[i]) / (bs[i + 1] - bs[i]);
            std::printf("    segment %d: x %.4f->%.4f  L %.4f->%.4f  slope %.4f\n",
                        i + 1, bs[i], bs[i + 1], fs[i], fs[i + 1], s);
            if (s < lastSlope - 1e-12)
                convex = false;
            lastSlope = s;
        }
        std::printf("  %-50s %s\n", "breaks and fracs strictly ordered", ordered ? "PASS" : "FAIL");
        std::printf("  %-50s %s\n", "segment slopes rise (convex)", convex ? "PASS" : "FAIL");
        failures += (!ordered) + (!convex);

        // (d) the half-rotation fraction, the way a pot taper is actually
        //     specified. circuit.md calls VR2 a 100k A taper; the textbook band
        //     is 10-15 %. This is the OUTSIDE corroboration (s146's for MASTER)
        //     and is asserted only as a loose sanity bound — the fitted value is
        //     15.41 %, just above the band, and the point is that it moved
        //     TOWARD it from the retired power law's 21.02 %.
        const double half = levelTaperShipped(0.5) * 100.0;
        const bool sane = half > 8.0 && half < 18.0;
        std::printf("  half-rotation fraction: %.2f %% (A-taper band 10-15 %%; "
                    "retired power law: 21.02 %%)\n", half);
        std::printf("  %-50s %s\n", "half rotation within 8-18 %", sane ? "PASS" : "FAIL");
        failures += !sane;
    }

    // ---- Test 1: LEVEL=0 → OD fully off --------------------------------
    // When LEVEL=0, LEVEL wiper is at VD — no OD contribution.
    // At any BLEND position, output should be (1-B)*clean.
    // ---------------------------------------------------------------------
    std::printf("=== Test 1: LEVEL=0 (OD fully off) ===\n");
    for (double b = 0.0; b <= 1.0; b += 0.5)
    {
        const double r = measureVout(0.0, b, 1.0, 1.0);
        // Both inputs 1V: clean=1, OD=1. Oracle: vo=1, vc=1.
        const double exp = levelBlendOracle(0.0, b, 1.0, 1.0);
        char label[64];
        std::snprintf(label, sizeof(label), "LEVEL=0 BLEND=%.1f (both 1V)", b);
        check(label, r, exp, tol);
    }

    // ---- Test 2: LEVEL=1, BLEND=0 → 100% clean -------------------------
    std::printf("\n=== Test 2: LEVEL=1, BLEND=0 (100%% clean) ===\n");
    {
        const double r = measureVout(1.0, 0.0, 1.0, 1.0);
        const double exp = levelBlendOracle(1.0, 0.0, 1.0, 1.0);
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
        const double exp = levelBlendOracle(1.0, 1.0, 1.0, 0.0);
        check("LEVEL=1 BLEND=1 (OD only)", r, exp, tol);
        const bool odOnly = std::abs(r - 1.0) < 1e-9;
        std::printf("  %-50s %s\n", "output = OD (1.0):",
                     odOnly ? "PASS" : "FAIL");
        if (!odOnly)
            ++failures;
    }

    // ---- Test 4: Loading effect at noon/noon ---------------------------
    // At LEVEL=0.5 (tapered to L≈0.154 since s163), BLEND=0.5, the OD path
    // gain is loaded by the BLEND pot drawing current through the LEVEL
    // divider. The deficit is smaller than the ~3.5 dB an ideal linear L=0.5
    // would give, because a lower L means a lower wiper impedance.
    // ---------------------------------------------------------------------
    std::printf("\n=== Test 4: Loading at noon/noon ===\n");
    {
        // OD only: clean=0, OD=1.
        const double r = measureVout(0.5, 0.5, 0.0, 1.0);
        const double exp = levelBlendOracle(0.5, 0.5, 1.0, 0.0);

        const double L = levelTaperShipped(0.5);
        const double idealOdGain = L * 0.5;
        const double loadingDb = 20.0 * std::log10(r / idealOdGain);
        std::printf("  L=%.4f, B=0.5\n", L);
        std::printf("  loaded OD gain:  %.6f  (%.3f dB)\n", r, 20.0*std::log10(r));
        std::printf("  ideal OD gain:   %.6f  (%.3f dB)\n", idealOdGain, 20.0*std::log10(idealOdGain));
        std::printf("  loading deficit: %.2f dB (an ideal linear L=0.5 would give ~ −3.5)\n", loadingDb);

        check("LEVEL=0.5 BLEND=0.5 (OD only)", r, exp, tol);

        // ⚠ s163 REPAIR, and it is the s124 pattern: this assertion used to be a
        // WINDOW (`-3 dB < deficit < -1 dB`) chosen for the taper that shipped at
        // the time. The new taper puts noon at L≈0.154 instead of 0.210, which
        // LOWERS the wiper impedance and therefore legitimately shrinks the
        // deficit to −1.06 dB — inside the old window by 0.06 dB, i.e. the test
        // would have passed by luck and would fail the next time the taper moves,
        // against correct code. The window was never the claim.
        //
        // What IS the claim, and it is taper-INDEPENDENT: the BLEND pot loads the
        // LEVEL divider, so the delivered OD gain must be strictly BELOW the
        // unloaded divider by exactly the amount the network predicts. Asserting
        // the closed form is strictly stronger than any window and cannot go
        // stale — it is a property of the topology, not of the pot law.
        // vw = (1/(1-L)) / (1/(1-L) + 1/L + 1) with the clean input grounded, and
        // the BLEND wiper then delivers B = 0.5 of it.
        const double predicted = (1.0 / (1.0 - L)) / (1.0 / (1.0 - L) + 1.0 / L + 1.0) * 0.5;
        const double predErr = std::abs(20.0 * std::log10(r / predicted));
        const bool loadingPresent = loadingDb < 0.0 && loadingDb > -3.5;
        const bool matchesForm = predErr < 1e-9;
        std::printf("  %-50s %s\n", "loading present and bounded (0 to -3.5 dB):",
                     loadingPresent ? "PASS" : "FAIL");
        std::printf("  %-50s %s (err %.2e dB)\n", "matches the closed-form loaded divider:",
                     matchesForm ? "PASS" : "FAIL", predErr);
        failures += (!loadingPresent) + (!matchesForm);

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
        const double exp = levelBlendOracle(pt.level, pt.blend, pt.vo, pt.vc);
        char label[64];
        std::snprintf(label, sizeof(label), "L=%.2f B=%.2f", pt.level, pt.blend);
        check(label, r, exp, tol);
    }

    // ---- Summary ----------------------------------------------------------
    std::printf("\n%s\n", failures == 0 ? "All tests passed." : "Some tests FAILED.");
    return (failures > 0) ? 1 : 0;
}
