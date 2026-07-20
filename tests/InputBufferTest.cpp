// =============================================================================
// InputBuffer (IC1_A) stage — frequency-response validation
// =============================================================================
// Validates the isolated linear transfer function of the input buffer stage:
//   a first-order high-pass (C1 into R2) at fc = 1/(2 pi R2 C1) ~= 1.5915 Hz,
//   unity passband, non-inverting.
//
// Analytic reference (continuous-time):  |H(f)| = r / sqrt(1 + r^2), r = f/fc.
// Bilinear (trapezoidal-cap) warp is < 1e-3 dB at these frequencies (all far
// below Nyquist), so the analytic value is a tight oracle.
// =============================================================================

#include "../src/dsp/InputBuffer.h"

#include <cmath>
#include <cstdio>
#include <vector>

static constexpr double PI = 3.14159265358979323846;

// Reference the stage's own constants (single source of truth — no local re-decl).
static constexpr double kR2 = InputBuffer::kR2;
static constexpr double kC1 = InputBuffer::kC1;
static const double kFc = 1.0 / (2.0 * PI * kR2 * kC1); // ~1.5915 Hz

// Analytic magnitude of the C1/R2 high-pass, in dB.
static double analyticDb(double f)
{
    const double r = f / kFc;
    const double mag = r / std::sqrt(1.0 + r * r);
    return 20.0 * std::log10(mag);
}

// Steady-state peak magnitude (dB) of the stage at a given frequency.
// Settles for >= 10 time-constants (tau = R2*C1 = 0.1 s) AND >= 2 periods, then
// measures the peak over 2 full periods — accurate to well under 0.01 dB.
static double measureDb(double freq, double fs)
{
    InputBuffer stage;
    stage.prepare(fs);

    const double period = fs / freq;
    const int settle = static_cast<int>(std::max(1.0 * fs, 2.0 * period));
    const int measure = static_cast<int>(std::ceil(2.0 * period)) + 1;

    double peak = 0.0;
    for (int n = 0; n < settle + measure; ++n)
    {
        const double x = std::sin(2.0 * PI * freq * static_cast<double>(n) / fs);
        const double y = stage.process(x);
        if (n >= settle)
            peak = std::max(peak, std::abs(y));
    }
    return (peak > 0.0) ? 20.0 * std::log10(peak) : -300.0;
}

int main()
{
    std::printf("InputBuffer (IC1_A): C1=%.3g F, R2=%.3g ohm, fc=%.4f Hz\n\n", kC1, kR2, kFc);

    int failures = 0;

    // ---- Test 1: frequency response vs analytic C1/R2 high-pass -------------
    // (freq Hz, tolerance dB). The corner + slope points get a slightly looser
    // tolerance than the flat passband to absorb any residual settling.
    struct Point { double f, tol; };
    const std::vector<Point> points = {
        { 0.5, 0.20 },   // on the -20 dB/decade slope (expect ~ -10.46 dB)
        { kFc, 0.10 },   // corner: expect -3.0103 dB
        { 20.0, 0.05 },  // low audio edge: expect ~ -0.027 dB
        { 100.0, 0.05 }, // expect ~ -0.001 dB
        { 1000.0, 0.05 } // passband: expect ~ 0 dB
    };

    const std::vector<double> sampleRates = { 44100.0, 48000.0, 96000.0 };

    for (double fs : sampleRates)
    {
        std::printf("--- fs = %.0f Hz ---\n", fs);
        for (const auto& p : points)
        {
            const double meas = measureDb(p.f, fs);
            const double ref = analyticDb(p.f);
            const double err = std::abs(meas - ref);
            const bool pass = err <= p.tol;
            std::printf("  f=%9.4f Hz  meas=%8.4f dB  ref=%8.4f dB  err=%.4f dB  %s\n",
                        p.f, meas, ref, err, pass ? "PASS" : "FAIL");
            if (! pass)
                ++failures;
        }
        std::printf("\n");
    }

    // ---- Test 2: non-inverting passband polarity ---------------------------
    // In the passband the high-pass phase shift is ~0 (arctan(fc/f) = 0.09 deg
    // at 1 kHz), so the output must be in phase with the input: a positive input
    // half-cycle produces a positive output. Sample the input's positive peak in
    // steady state and confirm the output there is positive.
    {
        std::printf("--- polarity (non-inverting) ---\n");
        const double fs = 48000.0;
        const double freq = 1000.0;
        InputBuffer stage;
        stage.prepare(fs);

        const int settle = static_cast<int>(1.0 * fs);
        double outAtInputPeak = 0.0;
        double bestInput = -1.0;
        for (int n = 0; n < settle + static_cast<int>(fs); ++n)
        {
            const double x = std::sin(2.0 * PI * freq * static_cast<double>(n) / fs);
            const double y = stage.process(x);
            if (n >= settle && x > bestInput) // track the most-positive input sample
            {
                bestInput = x;
                outAtInputPeak = y;
            }
        }
        const bool pass = outAtInputPeak > 0.0;
        std::printf("  input peak ~ +1.0, output there = %+.4f  %s\n",
                    outAtInputPeak, pass ? "PASS (non-inverting)" : "FAIL (inverted!)");
        if (! pass)
            ++failures;
        std::printf("\n");
    }

    std::printf("%s\n", failures == 0 ? "All tests passed." : "Some tests FAILED.");
    return (failures > 0) ? 1 : 0;
}
