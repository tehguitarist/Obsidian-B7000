// =============================================================================
// EqPreGain (IC5_A buffer + IC5_B inverting −2.2×) — validation
// =============================================================================
// A frequency-flat scalar gain, so the checks are minimal:
//   Test 1 — flat −2.2× magnitude across the band (rail clamp OFF).
//   Test 2 — DC-step polarity: inverting, gain exactly −2.2.
//   Test 3 — rail clamp engages symmetrically once enabled (sanity on the GATE).
// =============================================================================

#include "../src/dsp/EqPreGain.h"

#include <cmath>
#include <cstdio>

static constexpr double PI = 3.14159265358979323846;

static double measureDb(double freq, double fs)
{
    EqPreGain stage;
    stage.prepare(fs);
    const double period = fs / freq;
    const int settle = static_cast<int>(std::max(0.1 * fs, 4.0 * period));
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
    return 20.0 * std::log10(peak / amp);
}

int main()
{
    int failures = 0;
    const double kExpectDb = 20.0 * std::log10(2.2);

    // ---- Test 1: flat −2.2× across the band ---------------------------------
    std::printf("=== Flat gain = 20*log10(2.2) = %.4f dB ===\n", kExpectDb);
    for (double f : { 20.0, 100.0, 1000.0, 10000.0, 20000.0 })
    {
        const double meas = measureDb(f, 48000.0);
        const bool pass = std::abs(meas - kExpectDb) < 1e-4;
        std::printf("  f=%8.1f  meas=%.4f dB  %s\n", f, meas, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    // ---- Test 2: DC-step polarity — inverting −2.2 --------------------------
    std::printf("\n=== DC-step polarity: inverting, gain -2.2 ===\n");
    {
        EqPreGain stage;
        stage.prepare(48000.0);
        const double vin = 1.0e-3;
        const double y = stage.process(vin);
        const double gain = y / vin;
        const bool ok = (y < 0.0) && std::abs(gain + 2.2) < 1e-9;
        std::printf("  Vout/Vin=%.6f (expect -2.2)  %s\n", gain, ok ? "PASS" : "FAIL");
        if (! ok)
            ++failures;
    }

    // ---- Test 3: rail clamp engages once enabled ----------------------------
    std::printf("\n=== Rail clamp engages symmetrically when enabled ===\n");
    {
        EqPreGain stage;
        stage.prepare(48000.0);
        stage.setRailVoltages(3.3, 3.3);
        stage.setRailClampEnabled(true);
        // −2.2 × (+2.0) = −4.4 → clamps to −3.3; −2.2 × (−2.0) = +4.4 → +3.3.
        const double yp = stage.process(2.0);
        const double yn = stage.process(-2.0);
        const bool ok = std::abs(yp + 3.3) < 1e-9 && std::abs(yn - 3.3) < 1e-9;
        std::printf("  in +2.0 -> %.4f (expect -3.3) ; in -2.0 -> %.4f (expect +3.3)  %s\n",
                    yp, yn, ok ? "PASS" : "FAIL");
        if (! ok)
            ++failures;
    }

    std::printf("\n%s\n", failures == 0 ? "All tests passed." : "Some tests FAILED.");
    return (failures > 0) ? 1 : 0;
}
