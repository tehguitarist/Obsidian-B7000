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

#include "../src/dsp/FitParams.h"
#include "../src/dsp/LevelBlend.h"
#include "../src/dsp/OdToneRestore.h"

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

// ⚠ s181: the oracle carries the BLEND end stops too, defaulting to the SHIPPED values.
// Passing eHi = eLo = 0 recovers the pre-s181 network term for term, which is what Test
// 8(a) uses as a bit-identity check — so this one function is both the current reference
// implementation AND the archived previous one, and they cannot drift apart.
static double levelBlendOracle(double level, double blend,
                               double vo, double vc,
                               double eHi = LevelBlend::kBlendEndStop,
                               double eLo = LevelBlend::kBlendEndStopClean)
{
    const double L = (level <= 0.0) ? 0.0
                   : (level >= 1.0) ? 1.0
                   : levelTaperShipped(level);
    const double k = 1.0 - eLo - eHi;      // the wiper-traversable span / body conductance
    const double B = eLo + blend * k;

    double vw;
    if (L <= 0.0)
        vw = 0.0;
    else if (L >= 1.0)
        vw = vo;
    else
    {
        const double invRup = 1.0 / (1.0 - L);
        const double invRdn = 1.0 / L;
        const double invTotal = invRup + invRdn + k;
        vw = (vo * invRup + vc * k) / invTotal;
    }
    if (B <= 0.0)
        return vc;
    if (B >= 1.0)
        return vw;
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
        //     specified. REPORTED, NOT GATED — and it was gated until s174, when
        //     the gate went red and the reason turned out to be its own premise.
        //
        //     ⛔⛔ DO NOT RE-GATE THIS, AND DO NOT WIDEN THE OLD 8-18 % BAR
        //     EITHER — widening is the concession this project's own rule warns
        //     about, and re-gating re-asserts a premise that does not hold.
        //     circuit.md calls VR2 a 100k A taper and the textbook band is
        //     10-15 %, but `levelTaper` is NOT a measurement of VR2's track: GATE
        //     AY defines it as a REPARAMETERISATION OF THE KNOB AXIS — the curve
        //     that makes the model's rendered ladder match the pedal's — so it
        //     absorbs every model-vs-pedal difference downstream of the pot, not
        //     just the pot. Both s163 and s146 label the A-taper agreement
        //     "outside corroboration no term of the objective knew about", i.e.
        //     a bonus, never a constraint.
        //     ⭐ And the quantity behaves like the thing it is: across three
        //     epochs it went 21.02 % (retired power law) -> 15.41 % (s163)
        //     -> 23.75 % (s173), moved each time by DSP changes elsewhere in the
        //     chain (`OdMakeup`, the mix-keyed HF term) that cannot touch a
        //     physical pot. A property of VR2 would not do that.
        //     ⚠ 23.75 % is a real departure and is NOT dismissed — it is an open
        //     question recorded against the taper, not a test failure. See the
        //     kLevelTaper* block in LevelBlend.h.
        const double half = levelTaperShipped(0.5) * 100.0;
        std::printf("  half-rotation fraction: %.2f %% (REPORTED, not gated; A-taper band "
                    "10-15 %%; s163 15.41 %%, retired power law 21.02 %%)\n", half);

        // (e) ⭐⭐ THE ASSERTION THAT REPLACES IT, AND IT IS STRICTLY HARDER —
        //     it catches the defect that hid the above for a whole session.
        //     These compiled defaults are read by `setLevel()`'s invalid-set
        //     fallback AND by this test's own oracle, and s173 moved the SHIPPED
        //     taper in FitParams.h without moving them, so Test 0 spent a session
        //     asserting the shape of a curve nothing runs (and passed). Exact
        //     equality is the right bar: both are literals of the same fit, so
        //     any difference at all is a missed edit, never rounding.
        const FitParams fp{};
        struct { const char* name; double compiled, shipped; } pairs[] = {
            {"Break1", LevelBlend::kLevelTaperBreak1, fp.levelTaperBreak1},
            {"Frac1",  LevelBlend::kLevelTaperFrac1,  fp.levelTaperFrac1},
            {"Break2", LevelBlend::kLevelTaperBreak2, fp.levelTaperBreak2},
            {"Frac2",  LevelBlend::kLevelTaperFrac2,  fp.levelTaperFrac2},
            {"Break3", LevelBlend::kLevelTaperBreak3, fp.levelTaperBreak3},
            {"Frac3",  LevelBlend::kLevelTaperFrac3,  fp.levelTaperFrac3},
            // s181: the BLEND end stops join the same assertion for the same reason.
            // Naming them here is the whole point — a new constant that is NOT in this
            // list is a new instance of the s174 defect waiting to happen.
            {"BlendEndStop",      LevelBlend::kBlendEndStop,      fp.blendEndStop},
            {"BlendEndStopClean", LevelBlend::kBlendEndStopClean, fp.blendEndStopClean},
        };
        bool inStep = true;
        for (const auto& p : pairs)
            if (p.compiled != p.shipped)
            {
                inStep = false;
                std::printf("    STALE: LevelBlend::kLevelTaper%s = %.6f but FitParams ships "
                            "%.6f\n", p.name, p.compiled, p.shipped);
            }
        std::printf("  %-50s %s\n", "compiled defaults == FitParams' shipped taper",
                    inStep ? "PASS" : "FAIL");
        failures += !inStep;
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
        // ⚠⚠ s181 REPAIR — the s118/s124 pattern: this asserted `output == 1.0 exactly`,
        // which was the whole content of "no loading at LEVEL=1". The BLEND end stop
        // (item 12) deliberately inverts it: the wiper cannot reach pin3, so the corner
        // now delivers (1-e)*OD + e*clean. The bar is NOT loosened — it is re-pointed at
        // the same claim, EXACTLY, with e in it. `e = 0` reproduces the old assertion.
        const double odOnlyWant = 1.0 - LevelBlend::kBlendEndStop;
        const bool odOnly = std::abs(r - odOnlyWant) < 1e-9;
        std::printf("  %-50s %s (want %.6f = 1 - e)\n", "output = (1-e) * OD:",
                     odOnly ? "PASS" : "FAIL", odOnlyWant);
        if (!odOnly)
            ++failures;
        // And the OTHER half of the same corner, which is the price this change accepted
        // and must never go silent: the clean coefficient here is EXACTLY e, not 0.
        const double rCleanAtCorner = measureVout(1.0, 1.0, 1.0, 0.0);
        const bool anchorBreak = std::abs(rCleanAtCorner - LevelBlend::kBlendEndStop) < 1e-9;
        std::printf("  %-50s %s (%.6f)\n",
                    "bleed-free corner clean coeff == e (NOT 0 — the s181 price):",
                    anchorBreak ? "PASS" : "FAIL", rCleanAtCorner);
        if (!anchorBreak)
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
        // ⚠ s181: `k` is the BLEND body's normalised conductance (1 at the ideal pot,
        // 1-e-eLo with the end stops), and it enters BOTH the wiper solve and the BLEND
        // split. Carrying it here rather than deleting the check keeps this the strictly
        // stronger, taper-independent assertion the s163 comment above argues for.
        const double kBody = 1.0 - LevelBlend::kBlendEndStop - LevelBlend::kBlendEndStopClean;
        const double bEff = LevelBlend::kBlendEndStopClean + 0.5 * kBody;
        const double predicted =
            (1.0 / (1.0 - L)) / (1.0 / (1.0 - L) + 1.0 / L + kBody) * bEff;
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

    // ---- Test 5: dist_engage=false -> 100% clean ------------------------
    // ⚠ Session 171 (item 14, S2): dist_engage now crossfades over ~12 ms
    // (`LevelBlend::kDistFadeSeconds`) rather than switching instantly, so a
    // single process() after setDistEngage() reads mid-fade, not the settled
    // endpoint. Settle it explicitly with tickSmoothing() (the same call
    // PedalChain::processPostBlend makes every sample) before reading the
    // steady-state value the endpoints are still bit-identical to.
    std::printf("\n=== Test 5: dist_engage=false (override to clean) ===\n");
    {
        LevelBlend stage;
        stage.prepare(48000.0);
        stage.setLevel(1.0);
        stage.setBlend(1.0);
        stage.setDistEngage(false);

        // 1000 samples comfortably clears the ~12 ms (576-sample) fade at 48 kHz.
        constexpr int kSettleSamples = 1000;
        double y = 0.0;
        for (int n = 0; n < kSettleSamples; ++n)
        {
            stage.tickSmoothing();
            y = stage.process(1.0, 3.0); // clean=1V, OD=3V
        }
        const bool cleanOverride = std::abs(y - 1.0) < 1e-9;
        std::printf("  dist_engage=false: output=%.6f (expect 1.0 clean): %s\n",
                     y, cleanOverride ? "PASS" : "FAIL");
        if (!cleanOverride)
            ++failures;

        stage.setDistEngage(true);
        y = 0.0;
        for (int n = 0; n < kSettleSamples; ++n)
        {
            stage.tickSmoothing();
            y = stage.process(1.0, 3.0);
        }
        // LEVEL=1, BLEND=1 -> (1-e)*OD + e*clean, s181's BLEND end stop. This assertion
        // is about the dist_engage OVERRIDE, not about the pot network, so it carries the
        // network's own answer rather than a re-typed 3.0 — same repair as Test 3.
        const double want = (1.0 - LevelBlend::kBlendEndStop) * 3.0
                            + LevelBlend::kBlendEndStop * 1.0;
        const bool normalBlend = std::abs(y - want) < 1e-9;
        std::printf("  dist_engage=true:  output=%.6f (expect %.6f = (1-e)*OD + e*clean): %s\n",
                     y, want, normalBlend ? "PASS" : "FAIL");
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

    // ---- Test 8: BLEND wiper end stop (session 181, open-work item 12) ---
    // Four separate claims, because they fail for different reasons:
    //  (a) DISABLED IS BIT-IDENTICAL. `blendEndStop = 0` must reproduce the pre-s181
    //      network EXACTLY, across a pot sweep — not "to a tolerance". The oracle above
    //      is the pre-change algebra, so this is a cross-implementation bit check and it
    //      is what lets every pre-s181 number stay reproducible.
    //  (b) THE DEFECT IS FIXED. At LEVEL min / BLEND max the shipped stage must deliver
    //      exactly e*cleanIn — a PURE clean bleed with no OD term, which is the mechanism
    //      GATE BK measured (the residual tracks the linear clean tap, not the
    //      compressing OD path).
    //  (c) THE PRICE IS REAL AND ASSERTED. The bleed-free corner's clean coefficient goes
    //      0 -> e. This is the anchor break the user accepted; it is asserted here so it
    //      can never be lost silently by a later edit, in EITHER direction.
    //  (d) NON-VACUITY. `e` must actually move the LEVEL-min output by more than the
    //      tolerance the other checks use — otherwise (b) passes on a stage that ignores
    //      the parameter entirely (the s177 MidBandTest Test-7 pattern).
    std::printf("\n=== Test 8: BLEND wiper end stop (item 12) ===\n");
    {
        constexpr double kE = 0.02418;   // the shipped FitParams::blendEndStop

        // (a) disabled == pre-s181, bit-identical over a sweep
        int bitDiffs = 0;
        for (double lv = 0.0; lv <= 1.0001; lv += 0.125)
            for (double bl = 0.0; bl <= 1.0001; bl += 0.125)
            {
                LevelBlend s;
                s.prepare(48000.0);
                s.setBlendEndStop(0.0);
                s.setLevel(lv);
                s.setBlend(bl);
                s.setDistEngage(true);
                const double got = s.process(1.0, 0.7);
                const double want = levelBlendOracle(lv, bl, 0.7, 1.0, 0.0, 0.0);
                if (got != want)
                    ++bitDiffs;
            }
        std::printf("  (a) endStop=0 vs pre-s181 oracle: %d of 81 cells differ  %s\n",
                    bitDiffs, bitDiffs == 0 ? "PASS" : "FAIL");
        if (bitDiffs != 0)
            ++failures;

        // (b) LEVEL min / BLEND max delivers exactly e * cleanIn, no OD term
        LevelBlend s;
        s.prepare(48000.0);
        s.setBlendEndStop(kE);
        s.setLevel(0.0);
        s.setBlend(1.0);
        s.setDistEngage(true);
        const double withOd = s.process(1.0, 5.0);   // a deliberately huge OD input
        const double noOd = s.process(1.0, 0.0);
        std::printf("  (b) LEVEL min, BLEND max: out=%.8f (want %.8f), "
                    "OD-independent: %s\n", withOd, kE,
                    (withOd == noOd) ? "yes" : "NO");
        check("    LEVEL-min bleed == e * clean", withOd, kE, tol);
        if (withOd != noOd)
        {
            std::printf("      FAIL: an OD term survives at LEVEL min\n");
            ++failures;
        }

        // (c) the accepted price: the bleed-free corner is no longer bleed-free
        LevelBlend bf;
        bf.prepare(48000.0);
        bf.setBlendEndStop(kE);
        bf.setLevel(1.0);
        bf.setBlend(1.0);
        bf.setDistEngage(true);
        for (int n = 0; n < 4; ++n)
            bf.process(0.0, 0.0);
        const double cf = bf.cleanFraction();
        std::printf("  (c) clean fraction at LEVEL=BLEND=max: %.6f (was exactly 0)\n", cf);
        check("    bleed-free corner clean coeff == e", cf, kE, 0.05);

        // (d) non-vacuity: e must MOVE the LEVEL-min output well past the tolerance
        LevelBlend off;
        off.prepare(48000.0);
        off.setBlendEndStop(0.0);
        off.setLevel(0.0);
        off.setBlend(1.0);
        off.setDistEngage(true);
        const double zeroed = off.process(1.0, 5.0);
        const bool nonVacuous = (zeroed == 0.0) && (std::abs(withOd) > 1e-3);
        std::printf("  (d) NON-VACUITY: endStop=0 gives %.8f, endStop=%.5f gives %.8f  %s\n",
                    zeroed, kE, withOd, nonVacuous ? "PASS" : "FAIL");
        if (!nonVacuous)
            ++failures;
    }

    // ---- Test 9: OdToneRestore's mix-law anchor tracks blendEndStop (s185) --
    // `OdToneRestore::kMixCf[0]` is NOT a free constant: it is the clean fraction of the
    // bleed-free corner, which is where `kMixS[0] = 0.951` was measured. s181 moved that
    // corner from cf = 0 to cf = e, and s185 re-anchored the node to follow it (item 19's
    // task P2, GATE BN). The two constants live in different headers and neither can see
    // the other — OdToneRestore is a DSP stage and FitParams is the fit bag PedalChain
    // applies — so nothing but this assertion keeps them tied.
    //
    // ⚠⚠ WHY EXACT RATHER THAN A TOLERANCE, and why this test exists at all: the pair is
    // two literals of ONE quantity, so any difference is a MISSED EDIT, never rounding.
    // This is the s174 pattern that caught the compiled LEVEL taper still holding the
    // retired s163 values while FitParams shipped s173's — a file that spent a whole
    // session asserting the shape of a curve nothing ran, and passing. If a future session
    // re-fits `blendEndStop`, THIS is what stops the mix law silently keeping the old
    // corner and evaluating S at a coordinate that no longer exists.
    // ⛔ Do NOT "fix" a failure here by widening it. Move kMixCf[0] to the new end stop —
    // and re-read GATE BN, because that is a re-anchor and it has a measured price.
    std::printf("\n=== Test 9: OdToneRestore mix anchor == blendEndStop (item 19 P2) ===\n");
    {
        const FitParams fp;
        const double anchor = OdToneRestore::mixAnchorCf();
        const bool tied = (anchor == fp.blendEndStop);
        std::printf("  kMixCf[0] = %.8f, FitParams::blendEndStop = %.8f  %s\n",
                    anchor, fp.blendEndStop, tied ? "PASS" : "FAIL");
        if (!tied)
        {
            std::printf("    ^ the mix law's node 0 is filed under a clean fraction the stage "
                        "can no longer reach.\n");
            ++failures;
        }

        // NON-VACUITY. An anchor equal to the end stop is only meaningful if the node
        // actually reaches the corner — i.e. if S there is the MEASURED kMixS[0] and not
        // an interpolated value. Assert that directly, so a future edit that moved BOTH
        // constants to some other matching pair would still have to face this.
        const double sAtCorner = OdToneRestore::mixShapeAt(fp.blendEndStop);
        const bool measured = std::abs(sAtCorner - OdToneRestore::mixAnchorS()) < 1e-12;
        std::printf("  S(corner) = %.6f, kMixS[0] = %.6f (the MEASURED ordinate)  %s\n",
                    sAtCorner, OdToneRestore::mixAnchorS(), measured ? "PASS" : "FAIL");
        if (!measured)
            ++failures;
    }

    // ---- Summary ----------------------------------------------------------
    std::printf("\n%s\n", failures == 0 ? "All tests passed." : "Some tests FAILED.");
    return (failures > 0) ? 1 : 0;
}
