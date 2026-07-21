// =============================================================================
// MidBand (LO-MID IC5_D / HI-MID IC6_A) — validation
// =============================================================================
// Validates the reusable mid peaking stage against the analytic oracle
// (analysis/eq_reference.py :: mid_stage_tf) for the full switch matrix the
// build-plan gate requires: every band at min/centre/max pot × all 3 switch
// caps. Signal ground = VD = 0; rail clamp OFF → pure linear TF.
//
//   Test 1 — FR vs oracle at 48 kHz, all 6 cap configs × {boost, flat, cut}:
//            ≤2 kHz tight (peaks up to ±27 dB, warp negligible far below Nyquist).
//   Test 2 — flat at B-taper centre (a=0.5 → 0 dB) and boost/cut mirror symmetry.
//   Test 3 — HF deviation shrinks 48k→96k (bilinear warp, not a model error).
//   Test 4 — DC-step polarity: inverting-unity (Vout/Vin = −1) at every position
//            (one of the EQ block's four inversions).
// =============================================================================

#include "../src/dsp/MidBand.h"

#include <cmath>
#include <cstdio>
#include <vector>

static constexpr double PI = 3.14159265358979323846;

static const double kFreqs[] = { 20, 50, 100, 200, 300, 500, 1000, 2000 };
static constexpr int kNF = 8;

// One config = a band's fixed values + one switchable series cap + a pot position,
// with the oracle dB at kFreqs. Regenerate from eq_reference.py if values change.
struct Cfg
{
    const char* name;
    const MidBand::Values& vals;
    double cSeries;
    double a;              // pot position (0 boost, 0.5 flat, 1 cut)
    double db[kNF];
};

static const std::vector<Cfg> kCfgs = {
    // LO-MID 47n
    { "LO-MID 47n boost", MidBand::kLoMid, MidBand::kLoMid47n, 0.0,
      { +4.31232, +10.91871, +17.72029, +27.16000, +25.28458, +18.24408, +11.31251, +5.94742 } },
    { "LO-MID 47n flat",  MidBand::kLoMid, MidBand::kLoMid47n, 0.5,
      { 0, 0, 0, 0, 0, 0, 0, 0 } },
    { "LO-MID 47n cut",   MidBand::kLoMid, MidBand::kLoMid47n, 1.0,
      { -4.31232, -10.91871, -17.72029, -27.16000, -25.28458, -18.24408, -11.31251, -5.94742 } },
    // LO-MID 10n
    { "LO-MID 10n boost", MidBand::kLoMid, MidBand::kLoMid10n, 0.0,
      { +0.33843, +1.80176, +5.01226, +10.75303, +15.77914, +22.99175, +13.09254, +6.44200 } },
    { "LO-MID 10n flat",  MidBand::kLoMid, MidBand::kLoMid10n, 0.5,
      { 0, 0, 0, 0, 0, 0, 0, 0 } },
    { "LO-MID 10n cut",   MidBand::kLoMid, MidBand::kLoMid10n, 1.0,
      { -0.33843, -1.80176, -5.01226, -10.75303, -15.77914, -22.99175, -13.09254, -6.44200 } },
    // LO-MID 2n2
    { "LO-MID 2n2 boost", MidBand::kLoMid, MidBand::kLoMid2n2, 0.0,
      { +0.02154, +0.13329, +0.51509, +1.83066, +3.54362, +7.26895, +14.39544, +8.36388 } },
    { "LO-MID 2n2 flat",  MidBand::kLoMid, MidBand::kLoMid2n2, 0.5,
      { 0, 0, 0, 0, 0, 0, 0, 0 } },
    { "LO-MID 2n2 cut",   MidBand::kLoMid, MidBand::kLoMid2n2, 1.0,
      { -0.02154, -0.13329, -0.51509, -1.83066, -3.54362, -7.26895, -14.39544, -8.36388 } },
    // HI-MID 15n  (across-lug cap C34 = 6n8, not the oracle's 22n default)
    { "HI-MID 15n boost", MidBand::kHiMid, MidBand::kHiMid15n, 0.0,
      { +0.68564, +3.17196, +7.32802, +13.09020, +17.18062, +23.79361, +24.68605, +15.86027 } },
    { "HI-MID 15n flat",  MidBand::kHiMid, MidBand::kHiMid15n, 0.5,
      { 0, 0, 0, 0, 0, 0, 0, 0 } },
    { "HI-MID 15n cut",   MidBand::kHiMid, MidBand::kHiMid15n, 1.0,
      { -0.68564, -3.17196, -7.32802, -13.09020, -17.18062, -23.79361, -24.68605, -15.86027 } },
    // HI-MID 3n3
    { "HI-MID 3n3 boost", MidBand::kHiMid, MidBand::kHiMid3n3, 0.0,
      { +0.03788, +0.23185, +0.86555, +2.79156, +4.92103, +8.80935, +17.00343, +20.19009 } },
    { "HI-MID 3n3 flat",  MidBand::kHiMid, MidBand::kHiMid3n3, 0.5,
      { 0, 0, 0, 0, 0, 0, 0, 0 } },
    { "HI-MID 3n3 cut",   MidBand::kHiMid, MidBand::kHiMid3n3, 1.0,
      { -0.03788, -0.23185, -0.86555, -2.79156, -4.92103, -8.80935, -17.00343, -20.19009 } },
    // HI-MID 820p
    { "HI-MID 820p boost", MidBand::kHiMid, MidBand::kHiMid820p, 0.0,
      { +0.00286, +0.01784, +0.07100, +0.27860, +0.60799, +1.54811, +4.67537, +11.27482 } },
    { "HI-MID 820p flat",  MidBand::kHiMid, MidBand::kHiMid820p, 0.5,
      { 0, 0, 0, 0, 0, 0, 0, 0 } },
    { "HI-MID 820p cut",   MidBand::kHiMid, MidBand::kHiMid820p, 1.0,
      { -0.00286, -0.01784, -0.07100, -0.27860, -0.60799, -1.54811, -4.67537, -11.27482 } },
};

static double measureDb(const MidBand::Values& v, double cSeries, double a, double freq, double fs)
{
    MidBand stage;
    stage.configure(v, cSeries);
    stage.prepare(fs);
    stage.setPosition(a);

    const double period = fs / freq;
    const int settle = static_cast<int>(std::max(0.25 * fs, 8.0 * period));
    const int measure = static_cast<int>(std::ceil(2.0 * period)) + 1;

    const double amp = 1.0e-3; // tiny → pure linear TF (rails off anyway)
    double peak = 0.0;
    for (int n = 0; n < settle + measure; ++n)
    {
        const double x = amp * std::sin(2.0 * PI * freq * static_cast<double>(n) / fs);
        const double y = stage.process(x);
        if (n >= settle)
            peak = std::max(peak, std::abs(y));
    }
    return (peak > 0.0) ? 20.0 * std::log10(peak / amp) : -300.0;
}

int main()
{
    int failures = 0;

    // ---- Test 1: FR vs oracle at 48 kHz (full switch matrix) ----------------
    std::printf("=== FR vs analytic oracle @ 48 kHz (all caps × boost/flat/cut) ===\n");
    for (const auto& c : kCfgs)
    {
        double worst = 0.0;
        for (int i = 0; i < kNF; ++i)
        {
            const double meas = measureDb(c.vals, c.cSeries, c.a, kFreqs[i], 48000.0);
            worst = std::max(worst, std::abs(meas - c.db[i]));
        }
        // Peaks reach ±27 dB; below 2 kHz at 48 kHz the warp is tiny, so a tight
        // bar holds even on the steep flanks.
        const bool pass = worst <= 0.15;
        std::printf("  %-18s worst err %.4f dB  %s\n", c.name, worst, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    // ---- Test 2: flat at centre + boost/cut mirror symmetry -----------------
    std::printf("\n=== Flat at a=0.5, and boost/cut mirror symmetry ===\n");
    {
        // Centre = 0 dB everywhere (already asserted in Test 1's "flat" rows via
        // the zero reference); here confirm the mirror: boost(f) == −cut(f).
        double worstMirror = 0.0;
        for (double f : { 100.0, 300.0, 1000.0 })
        {
            const double b = measureDb(MidBand::kLoMid, MidBand::kLoMid10n, 0.0, f, 48000.0);
            const double cutv = measureDb(MidBand::kLoMid, MidBand::kLoMid10n, 1.0, f, 48000.0);
            worstMirror = std::max(worstMirror, std::abs(b + cutv));
        }
        const bool pass = worstMirror <= 1e-3;
        std::printf("  boost(f) + cut(f) max |sum| = %.6f dB (expect ~0)  %s\n",
                    worstMirror, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    // ---- Test 3: HF deviation is bilinear warp (shrinks 48k → 96k) ----------
    std::printf("\n=== HF: 2 kHz error must shrink 48k → 96k (warp) ===\n");
    {
        // Use the steepest config (LO-MID 47n boost, ~27 dB peak) at 2 kHz.
        const double ref2k = 5.94742;
        const double e48 = std::abs(measureDb(MidBand::kLoMid, MidBand::kLoMid47n, 0.0, 2000.0, 48000.0) - ref2k);
        const double e96 = std::abs(measureDb(MidBand::kLoMid, MidBand::kLoMid47n, 0.0, 2000.0, 96000.0) - ref2k);
        const bool pass = e96 < e48 + 1e-9;
        std::printf("  err48=%.4f  err96=%.4f  %s\n", e48, e96, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    // ---- Test 4: DC-step polarity — inverting-unity at every position -------
    std::printf("\n=== DC-step polarity: inverting-unity (Vout/Vin = -1) ===\n");
    for (double a : { 0.0, 0.5, 1.0 })
    {
        MidBand stage;
        stage.configure(MidBand::kLoMid, MidBand::kLoMid10n);
        stage.prepare(48000.0);
        stage.setPosition(a);
        const double vin = 1.0e-3;
        double y = 0.0;
        for (int n = 0; n < 20000; ++n) // settle the large-cap history fully
            y = stage.process(vin);
        const double gain = y / vin;
        const bool ok = (y < 0.0) && std::abs(gain + 1.0) < 2e-3;
        std::printf("  a=%.1f  Vout/Vin=%.6f (expect -1.0)  %s\n", a, gain, ok ? "PASS" : "FAIL");
        if (! ok)
            ++failures;
    }

    std::printf("\n%s\n", failures == 0 ? "All tests passed." : "Some tests FAILED.");
    return (failures > 0) ? 1 : 0;
}
