// =============================================================================
// MasterOut — MASTER [ENG] divider + IC6_B buffer + output HP — validation
// =============================================================================
// Validates the stage against the analytic oracle (analysis/eq_reference.py ::
// master_out_tf), evaluated here in C++ as the complex Laplace TF so the
// trapezoidal implementation is cross-checked directly, no hardcoded tables.
// Rail clamp OFF → pure linear TF.
//
//   Test 0 — The taper's own SHAPE: convex (segment slopes rise), monotone, exact
//            endpoints, and inside the A-taper 10-15% half-rotation band (s146).
//   Test 1 — FR vs oracle across the FULL band (20 Hz .. 20 kHz) at 48/96 kHz, at
//            six masters covering all three segments AND both breaks. Tight
//            EVERYWHERE (≤0.05 dB): the only
//            caps are two ~0.72 Hz HPFs, so there is no audible-band bilinear
//            warp — unlike every prior EQ-block stage, the top octave matches too.
//   Test 2 — Unity at full CW: plateau (≥5 Hz) gain ≈ 0 dB.
//   Test 3 — Step-response polarity: first sample ≈ +divRatio·Vin (NON-inverting,
//            correct gain), long settle → ~0 (AC-coupled: both HPFs block DC).
// =============================================================================

#include "../src/dsp/MasterOut.h"

#include <cmath>
#include <complex>
#include <cstdio>

static constexpr double PI = 3.14159265358979323846;

// THREE-segment piecewise-linear MASTER taper (session 146; two segments s115) -- the oracle's
// copy of MasterOut::setMaster. Deliberately re-derived here rather than calling the stage, so
// the test can still fail if the stage's curve changes underneath it.
static double taperRatio(double m)
{
    const double b1 = MasterOut::kMasterTaperBreak;
    const double f1 = MasterOut::kMasterTaperFrac;
    const double b2 = MasterOut::kMasterTaperBreak2;
    const double f2 = MasterOut::kMasterTaperFrac2;
    if (m <= 0.0)
        return 0.0;
    if (m >= 1.0)
        return 1.0;
    if (m <= b1)
        return f1 * m / b1;
    if (m <= b2)
        return f1 + (f2 - f1) * (m - b1) / (b2 - b1);
    return f2 + (1.0 - f2) * (m - b2) / (1.0 - b2);
}

// ⭐ Session 146 — the taper's own SHAPE properties, asserted here because they are what make
// the 3-segment form defensible rather than merely better-fitting (FitParams::masterTaperBreak).
// A non-convex or non-monotone "taper" is the signature of the extra freedom having gone into
// fitting knob noise, and neither the FR test nor the step test below would notice.
static bool checkTaperShape()
{
    bool ok = true;
    const double s1 = MasterOut::kMasterTaperFrac / MasterOut::kMasterTaperBreak;
    const double s2 = (MasterOut::kMasterTaperFrac2 - MasterOut::kMasterTaperFrac)
                      / (MasterOut::kMasterTaperBreak2 - MasterOut::kMasterTaperBreak);
    const double s3 = (1.0 - MasterOut::kMasterTaperFrac2) / (1.0 - MasterOut::kMasterTaperBreak2);
    std::printf("  segment slopes: %.4f -> %.4f -> %.4f (must RISE: convex track)\n", s1, s2, s3);
    if (!(s1 < s2 && s2 < s3))
    {
        std::printf("  ** FAIL: taper is not convex\n");
        ok = false;
    }
    // Monotone over the whole travel, sampled finely enough to catch a segment inversion.
    double prev = -1.0;
    for (int i = 0; i <= 1000; ++i)
    {
        const double r = taperRatio(static_cast<double>(i) / 1000.0);
        if (r < prev)
        {
            std::printf("  ** FAIL: taper is not monotone at m=%.3f\n", i / 1000.0);
            ok = false;
            break;
        }
        prev = r;
    }
    // The half-rotation fraction is how a pot taper is SPECIFIED; circuit.md calls VR8 a 100k A,
    // and the reference measures 11.89% there. A textbook A taper is 10-15%.
    const double half = taperRatio(0.5);
    std::printf("  half-rotation fraction: %.2f %% (A-taper spec 10-15%%)\n", 100.0 * half);
    if (!(half >= 0.10 && half <= 0.15))
    {
        std::printf("  ** FAIL: half-rotation fraction is outside the A-taper band\n");
        ok = false;
    }
    // Endpoints are required EXACTLY by the topology (wiper on VD / unity at full CW).
    if (taperRatio(0.0) != 0.0 || taperRatio(1.0) != 1.0)
    {
        std::printf("  ** FAIL: endpoints are not exact\n");
        ok = false;
    }
    return ok;
}

// Analytic oracle: H(f) = divRatio · [sC36·Rp/(1+sC36·Rp)] · [sC37·R46/(1+sC37·R46)]
static double oracleDb(double master, double freq)
{
    // Session 146: the taper is a THREE-SEGMENT PIECEWISE LINEAR curve (two until s115,
    // a power law before that). Mirrors MasterOut::setMaster exactly (endpoints exact).
    const double ratio = taperRatio(master);
    const std::complex<double> s(0.0, 2.0 * PI * freq);
    const std::complex<double> hpIn = s * MasterOut::kC36 * MasterOut::kRp
                                       / (1.0 + s * MasterOut::kC36 * MasterOut::kRp);
    const std::complex<double> hpOut = s * MasterOut::kC37 * MasterOut::kR46
                                        / (1.0 + s * MasterOut::kC37 * MasterOut::kR46);
    const double mag = ratio * std::abs(hpIn * hpOut);
    return (mag > 0.0) ? 20.0 * std::log10(mag) : -300.0;
}

static double measureDb(double master, double freq, double fs)
{
    MasterOut stage;
    stage.prepare(fs);
    stage.setMaster(master);

    const double period = fs / freq;
    // Slowest pole is the ~0.72 Hz HPF (tau ≈ 0.22 s) — settle well past it so the
    // startup transient doesn't corrupt the peak read.
    const int settle = static_cast<int>(std::max(2.0 * fs, 12.0 * period));
    const int measure = static_cast<int>(std::ceil(2.0 * period)) + 1;

    const double amp = 1.0e-3;
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

    static const double kFreqs[] = { 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000 };
    static const int kNF = 10;
    // ⚠ Session 146: with THREE segments the old { 1.0, 0.5, 0.25 } set never touched the top
    // segment at all (b2 = 0.659), so a bug above the second break would have gone unmeasured.
    // Both breaks are included explicitly — a segment-boundary off-by-one shows exactly there
    // and nowhere else.
    static const double kMasters[] = { 1.0, 0.85, MasterOut::kMasterTaperBreak2, 0.5,
                                       MasterOut::kMasterTaperBreak, 0.25 };
    static const int kNM = static_cast<int>(sizeof(kMasters) / sizeof(kMasters[0]));

    // ---- Test 0: the taper's own shape (session 146) ------------------------
    std::printf("=== MASTER taper shape (3-segment PWL) ===\n");
    if (! checkTaperShape())
        ++failures;
    std::printf("\n");

    // ---- Test 1: FR vs oracle across the full band (tight everywhere) -------
    std::printf("=== FR vs analytic oracle (full band, tight — no audible-band caps) ===\n");
    for (const double fs : { 48000.0, 96000.0 })
    {
        for (int mi = 0; mi < kNM; ++mi)
        {
            const double m = kMasters[mi];
            double worst = 0.0;
            for (int i = 0; i < kNF; ++i)
            {
                if (kFreqs[i] > fs * 0.45) continue; // stay clear of Nyquist
                const double meas = measureDb(m, kFreqs[i], fs);
                worst = std::max(worst, std::abs(meas - oracleDb(m, kFreqs[i])));
            }
            const bool pass = worst <= 0.05;
            std::printf("  fs=%6.0f  master=%.2f  worst err %.5f dB  %s\n",
                        fs, m, worst, pass ? "PASS" : "FAIL");
            if (! pass)
                ++failures;
        }
    }

    // ---- Test 2: unity at full CW (plateau ≈ 0 dB) --------------------------
    std::printf("\n=== Unity at full CW (master=1.0) ===\n");
    {
        const double g1k = measureDb(1.0, 1000.0, 48000.0);
        const bool pass = std::abs(g1k) <= 0.02;
        std::printf("  1 kHz gain %+.5f dB  %s\n", g1k, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    // ---- Test 3: step-response polarity (non-inverting; AC-coupled) ---------
    std::printf("\n=== Step response: non-inverting first sample; decays to ~0 ===\n");
    for (int mi = 0; mi < kNM; ++mi)
    {
        const double m = kMasters[mi];
        MasterOut stage;
        stage.prepare(48000.0);
        stage.setMaster(m);

        const double vin = 1.0e-3;
        const double divRatio = taperRatio(m);
        const double first = stage.process(vin);       // caps ≈ short at the edge
        double y = first;
        for (int n = 1; n < 400000; ++n)                // settle >> 0.22 s tau
            y = stage.process(vin);

        const double firstGain = first / vin;
        const bool jumpOk = (first > 0.0) && std::abs(firstGain - divRatio) < 5e-3; // non-inv + gain
        const bool decayOk = std::abs(y) < 1e-6 * std::abs(vin) + 1e-9;             // AC-coupled → 0
        const bool pass = jumpOk && decayOk;
        std::printf("  master=%.2f  first %+.6f (divRatio %.6f)  settled %+.3e  %s\n",
                    m, firstGain, divRatio, y, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    std::printf("\n%s\n", failures == 0 ? "All tests passed." : "Some tests FAILED.");
    return (failures > 0) ? 1 : 0;
}
