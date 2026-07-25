// =============================================================================
// RailClamp — op-amp output-rail saturation — validation (clamp ENABLED)
// =============================================================================
// This is the ONLY test that turns the clamp ON. Every stage test validates its
// analytic oracle with rails OFF (the default), which is exactly why the
// FitParams railNeg = -3.3 sign bug (fixed 926c0cc) survived from Phase 4: with
// a SIGNED railNeg the negative branch fires for every sample below +(3.3-knee)
// and returns a constant +3.3 V, i.e. an enabled clamp emitted DC instead of
// audio, and nothing exercised the enabled path.
//
//   Test 1 — Dead-linear region: process(x) == x EXACTLY for |x| < rail - knee.
//   Test 2 — Symmetry with matched rails: process(-x) == -process(x) exactly
//            (the two branches are mirror images, same FP ops, so exact).
//   Test 3 — Bounded: |process(x)| <= max(railNeg, railPos) for large |x|, both
//            signs — including absurd inputs (1e6 V) and non-finite-adjacent mag.
//   Test 4 — The parabolic knee is C1-continuous at BOTH boundaries
//            (x = ±(rail-knee), ±(rail+knee)): no value jump, and the one-sided
//            slopes agree (1 at the inner edge, 0 at the outer edge). Plus the
//            whole transition is MONOTONE non-decreasing (slope >= 0; slope -> 0
//            at the clamp is correct saturation, so the assert is >=, not >).
//   Test 5 — Hard clamp: process(x) == railPos exactly for x >= railPos + knee,
//            and == -railNeg exactly for x <= -(railNeg + knee).
//   Test 6 — Asymmetric rails act independently: setRailVoltages(2.0, 4.0)
//            saturates into [-2.0, +4.0], each side with its own knee position.
//   Test 7 — REGRESSION GUARD for 926c0cc: setRailVoltages(-3.3, 3.3) must be
//            bit-identical to setRailVoltages(3.3, 3.3) across the whole range
//            (the |v| guard in setRailVoltages), and in particular
//            process(-1.0) == -1.0, NOT +3.3. `railNeg` is a --fit key, so a
//            signed value can still arrive from a sweep — this asserts the guard,
//            not just the current FitParams value.
// =============================================================================

#include "../src/dsp/RailClamp.h"

#include <cmath>
#include <cstdio>

static constexpr double kRail = 3.3;
static constexpr double kKnee = 0.35;

// A clamp at the nominal symmetric rails, enabled.
static RailClamp makeClamp(double vNeg = kRail, double vPos = kRail, double knee = kKnee)
{
    RailClamp rc;
    rc.setRailVoltages(vNeg, vPos);
    rc.setKnee(knee);
    rc.setEnabled(true);
    return rc;
}

int main()
{
    int failures = 0;

    // ---- Test 1: dead-linear region is EXACTLY the identity ------------------
    std::printf("=== Dead-linear region: process(x) == x exactly for |x| < rail-knee ===\n");
    {
        const RailClamp rc = makeClamp();
        const double edge = kRail - kKnee; // 2.95
        double worst = 0.0;
        bool exact = true;
        for (int i = -2000; i <= 2000; ++i)
        {
            // Sweep strictly inside the linear window (0.9999 keeps us off the edge).
            const double x = 0.9999 * edge * static_cast<double>(i) / 2000.0;
            const double y = rc.process(x);
            if (y != x)
            {
                exact = false;
                worst = std::max(worst, std::abs(y - x));
            }
        }
        std::printf("  |x| < %.4f V over 4001 points, worst deviation %.3e  %s\n",
                    edge, worst, exact ? "PASS" : "FAIL");
        if (! exact)
            ++failures;
    }

    // ---- Test 2: symmetry for equal magnitudes -------------------------------
    std::printf("\n=== Symmetry (matched rails): process(-x) == -process(x) ===\n");
    {
        const RailClamp rc = makeClamp();
        double worst = 0.0;
        bool exact = true;
        for (int i = 0; i <= 4000; ++i)
        {
            const double x = 5.0 * static_cast<double>(i) / 4000.0; // 0 .. 5 V, spans both knees
            const double yp = rc.process(x);
            const double yn = rc.process(-x);
            if (yn != -yp)
            {
                exact = false;
                worst = std::max(worst, std::abs(yn + yp));
            }
        }
        std::printf("  0..5 V over 4001 points, worst asymmetry %.3e  %s\n",
                    worst, exact ? "PASS" : "FAIL");
        if (! exact)
            ++failures;
    }

    // ---- Test 3: bounded for large |x|, both signs ---------------------------
    std::printf("\n=== Bounded: |process(x)| <= max(railNeg, railPos) ===\n");
    {
        const RailClamp rc = makeClamp(2.0, 4.0); // asymmetric on purpose
        const double bound = 4.0;
        static const double kBig[] = { 4.1, 10.0, 100.0, 1.0e3, 1.0e6, 1.0e12 };
        bool ok = true;
        for (const double m : kBig)
        {
            for (const double x : { m, -m })
            {
                const double y = rc.process(x);
                const bool fin = std::isfinite(y);
                if (! fin || std::abs(y) > bound)
                {
                    ok = false;
                    std::printf("    x=%+.3e -> %+.6f  OUT OF BOUNDS\n", x, y);
                }
            }
        }
        std::printf("  |x| up to 1e12 both signs, bound %.2f V  %s\n", bound, ok ? "PASS" : "FAIL");
        if (! ok)
            ++failures;
    }

    // ---- Test 4: knee is C1-continuous and monotone --------------------------
    std::printf("\n=== Parabolic knee: C1-continuous at both boundaries, monotone ===\n");
    {
        const RailClamp rc = makeClamp();
        const double eps = 1.0e-7;

        // (a) value + slope continuity at the four knee boundaries.
        struct Boundary { double x; double slope; const char* name; };
        const Boundary kBounds[] = {
            {  (kRail - kKnee), 1.0, "+inner (rail-knee)" },
            {  (kRail + kKnee), 0.0, "+outer (rail+knee)" },
            { -(kRail - kKnee), 1.0, "-inner" },
            { -(kRail + kKnee), 0.0, "-outer" },
        };
        for (const Boundary& b : kBounds)
        {
            const double yl = rc.process(b.x - eps);
            const double y0 = rc.process(b.x);
            const double yr = rc.process(b.x + eps);

            const double jumpL = std::abs(y0 - yl);
            const double jumpR = std::abs(yr - y0);
            const double slopeL = (y0 - yl) / eps;
            const double slopeR = (yr - y0) / eps;

            // Value continuity: any real JUMP would be >> the O(eps) change of a
            // continuous function; slope continuity: both one-sided slopes must
            // agree with each other and with the analytic value at the boundary.
            const bool valOk = (jumpL < 1.0e-5) && (jumpR < 1.0e-5);
            const bool slopeOk = std::abs(slopeL - slopeR) < 1.0e-3
                                 && std::abs(slopeL - b.slope) < 1.0e-3
                                 && std::abs(slopeR - b.slope) < 1.0e-3;
            const bool pass = valOk && slopeOk;
            std::printf("  %-20s x=%+.4f  jump %.2e/%.2e  slope %.6f/%.6f (want %.1f)  %s\n",
                        b.name, b.x, jumpL, jumpR, slopeL, slopeR, b.slope, pass ? "PASS" : "FAIL");
            if (! pass)
                ++failures;
        }

        // (b) monotone non-decreasing across the WHOLE range (slope >= 0; the
        //     slope legitimately reaches 0 in the clamped region).
        {
            const int N = 200000;
            double prev = rc.process(-6.0);
            double worstDrop = 0.0;
            for (int i = 1; i <= N; ++i)
            {
                const double x = -6.0 + 12.0 * static_cast<double>(i) / static_cast<double>(N);
                const double y = rc.process(x);
                if (y < prev)
                    worstDrop = std::max(worstDrop, prev - y);
                prev = y;
            }
            const bool pass = worstDrop == 0.0;
            std::printf("  monotone over -6..+6 V (%d pts), worst decrease %.3e  %s\n",
                        N, worstDrop, pass ? "PASS" : "FAIL");
            if (! pass)
                ++failures;
        }
    }

    // ---- Test 5: hard clamp is exact beyond the outer knee -------------------
    std::printf("\n=== Hard clamp: exact rail value beyond ±(rail+knee) ===\n");
    {
        const RailClamp rc = makeClamp();
        const double outer = kRail + kKnee; // 3.65
        bool ok = true;
        for (int i = 0; i <= 500; ++i)
        {
            const double x = outer + 20.0 * static_cast<double>(i) / 500.0;
            if (rc.process(x) != kRail)
            {
                ok = false;
                std::printf("    +side x=%.6f -> %.9f (want %.6f)\n", x, rc.process(x), kRail);
                break;
            }
            if (rc.process(-x) != -kRail)
            {
                ok = false;
                std::printf("    -side x=%.6f -> %.9f (want %.6f)\n", -x, rc.process(-x), -kRail);
                break;
            }
        }
        std::printf("  x >= %.2f -> +%.2f and x <= %.2f -> %.2f, exactly  %s\n",
                    outer, kRail, -outer, -kRail, ok ? "PASS" : "FAIL");
        if (! ok)
            ++failures;
    }

    // ---- Test 6: asymmetric rails act independently ---------------------------
    std::printf("\n=== Asymmetric rails: setRailVoltages(2.0, 4.0) -> [-2.0, +4.0] ===\n");
    {
        const double vNeg = 2.0, vPos = 4.0;
        const RailClamp rc = makeClamp(vNeg, vPos);

        // Linear where BOTH sides are still linear, clamped at each side's own rail.
        const bool linMid = (rc.process(1.0) == 1.0) && (rc.process(-1.0) == -1.0);
        // +3.0 V is past the NEGATIVE rail's magnitude but nowhere near the
        // positive knee (4.0-0.35 = 3.65) -> must still be dead-linear. This is
        // the assert that catches the two rails being conflated.
        const bool posStillLinear = (rc.process(3.0) == 3.0);
        // -3.0 V is past the negative outer knee (-2.35) -> hard-clamped at -2.0.
        const bool negClamped = (rc.process(-3.0) == -vNeg);
        const bool posClamped = (rc.process(10.0) == vPos);
        // Independent knee positions.
        const double yPosKnee = rc.process(vPos); // mid-knee on + side
        const double yNegKnee = rc.process(-vNeg);
        const bool kneesOk = (yPosKnee < vPos) && (yPosKnee > vPos - kKnee)
                             && (yNegKnee > -vNeg) && (yNegKnee < -vNeg + kKnee);

        const bool pass = linMid && posStillLinear && negClamped && posClamped && kneesOk;
        std::printf("  f(1)=%+.4f f(-1)=%+.4f f(3)=%+.4f f(-3)=%+.4f f(10)=%+.4f\n",
                    rc.process(1.0), rc.process(-1.0), rc.process(3.0), rc.process(-3.0), rc.process(10.0));
        std::printf("  knee mid-points f(%.1f)=%+.4f f(%.1f)=%+.4f  %s\n",
                    vPos, yPosKnee, -vNeg, yNegKnee, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    // ---- Test 7: REGRESSION GUARD — signed railNeg (commit 926c0cc) ----------
    std::printf("\n=== Regression guard: setRailVoltages(-3.3, 3.3) == (3.3, 3.3) ===\n");
    {
        const RailClamp signedRc = makeClamp(-kRail, kRail); // the bug's input
        const RailClamp magRc = makeClamp(kRail, kRail);     // the correct input

        // The specific symptom: with a signed railNeg, EVERY sample below
        // +(3.3-0.35) took the negative branch and came out at a constant +3.3.
        const double y = signedRc.process(-1.0);
        const bool dcBugGone = (y == -1.0);
        std::printf("  process(-1.0) = %+.6f  (bug returned %+.4f)  %s\n",
                    y, kRail, dcBugGone ? "PASS" : "FAIL");
        if (! dcBugGone)
            ++failures;

        double worst = 0.0;
        bool identical = true;
        for (int i = -4000; i <= 4000; ++i)
        {
            const double x = 6.0 * static_cast<double>(i) / 4000.0; // -6 .. +6 V
            const double a = signedRc.process(x);
            const double b = magRc.process(x);
            if (a != b)
            {
                identical = false;
                worst = std::max(worst, std::abs(a - b));
            }
        }
        std::printf("  bit-identical over -6..+6 V (8001 pts), worst delta %.3e  %s\n",
                    worst, identical ? "PASS" : "FAIL");
        if (! identical)
            ++failures;

        // Same guard on the positive side, for completeness.
        const RailClamp signedPos = makeClamp(kRail, -kRail);
        const bool posOk = (signedPos.process(1.0) == 1.0) && (signedPos.process(10.0) == kRail);
        std::printf("  signed railPos also normalised: f(1)=%+.4f f(10)=%+.4f  %s\n",
                    signedPos.process(1.0), signedPos.process(10.0), posOk ? "PASS" : "FAIL");
        if (! posOk)
            ++failures;
    }

    std::printf("\n%s\n", failures == 0 ? "All tests passed." : "Some tests FAILED.");
    return (failures > 0) ? 1 : 0;
}
