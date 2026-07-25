// =============================================================================
// Baxandall BASS+TREBLE (IC5_C) — validation
// =============================================================================
// Validates the coupled Baxandall network against the analytic oracle
// (analysis/eq_reference.py :: baxandall_tf). Rail clamp OFF → pure linear TF.
//
//   Test 1 — FR vs oracle at 48 kHz, bass/treble boost/flat/cut + both-boost:
//            tight ≤2 kHz; above 2 kHz allowed to droop from bilinear warp.
//   Test 2 — HF (5 k, 10 k) deviation shrinks 48k→96k (warp, not model error).
//   Test 3 — DC-step polarity: INVERTING; flat DC gain ≈ −0.926 (oracle value).
// =============================================================================

#include "../src/dsp/Baxandall.h"

#include <cmath>
#include <cstdio>
#include <vector>

static constexpr double PI = 3.14159265358979323846;

static const double kFreqs[] = { 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000 };
static constexpr int kNF = 9;

struct Cfg { const char* name; double ab, at; double db[kNF]; };

static const std::vector<Cfg> kCfgs = {
    { "both flat",     0.5, 0.5,
      { -0.64159, -0.53845, -0.38065, -0.25468, -0.19532, -0.18489, -0.18251, -0.18464, -0.19498 } },
    { "bass boost",    0.0, 0.5,
      { +18.13420, +15.25982, +11.28714, +7.15332, +3.01290, +1.04114, +0.17361, -0.13086, -0.18714 } },
    { "bass cut",      1.0, 0.5,
      { -19.75803, -16.21767, -11.86423, -7.57650, -3.37519, -1.39535, -0.52851, -0.23035, -0.19508 } },
    { "treble boost",  0.5, 0.0,
      { -0.73894, -0.95396, -0.96884, -0.06124, +2.39946, +5.47542, +9.89948, +15.74545, +18.39545 } },
    { "treble cut",    0.5, 1.0,
      { -0.54452, -0.12804, +0.19399, -0.45080, -2.75589, -5.78257, -10.18154, -16.01076, -18.66700 } },
    { "bass+treble boost", 0.0, 0.0,
      { +18.02554, +15.00051, +11.16363, +7.38405, +3.93953, +5.29887, +9.76572, +15.73895, +18.39102 } },
};

static double measureDb(double ab, double at, double freq, double fs, double r36 = -1.0)
{
    Baxandall stage;
    stage.prepare(fs);
    stage.setBass(ab);
    stage.setTreble(at);
    if (r36 > 0.0)
        stage.setTrebleWiperR(r36);

    const double period = fs / freq;
    const int settle = static_cast<int>(std::max(0.25 * fs, 8.0 * period));
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

    // ---- Test 1: FR vs oracle @ 48 kHz --------------------------------------
    std::printf("=== FR vs analytic oracle @ 48 kHz ===\n");
    for (const auto& c : kCfgs)
    {
        double worstLo = 0.0; // <= 2 kHz (tight)
        for (int i = 0; i < kNF; ++i)
        {
            if (kFreqs[i] > 2000.0) continue;
            const double meas = measureDb(c.ab, c.at, kFreqs[i], 48000.0);
            worstLo = std::max(worstLo, std::abs(meas - c.db[i]));
        }
        const bool pass = worstLo <= 0.15;
        std::printf("  %-18s worst err (<=2 kHz) %.4f dB  %s\n", c.name, worstLo, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    // ---- Test 2: HF (5 k, 10 k) deviation is bilinear warp (shrinks 48k→96k) -
    std::printf("\n=== HF: 5k/10k error shrinks 48k → 96k (warp) ===\n");
    for (const auto& c : { kCfgs[3], kCfgs[5] }) // treble boost, bass+treble boost
    {
        for (int i = 0; i < kNF; ++i)
        {
            if (kFreqs[i] < 5000.0) continue;
            const double e48 = std::abs(measureDb(c.ab, c.at, kFreqs[i], 48000.0) - c.db[i]);
            const double e96 = std::abs(measureDb(c.ab, c.at, kFreqs[i], 96000.0) - c.db[i]);
            const bool pass = e96 < e48 + 1e-9;
            std::printf("  %-18s f=%6.0f  err48=%.4f  err96=%.4f  %s\n",
                        c.name, kFreqs[i], e48, e96, pass ? "PASS" : "FAIL");
            if (! pass)
                ++failures;
        }
    }

    // ---- Test 4: setTrebleWiperR — fitted point vs oracle, and R36=nominal is exact
    // (Phase 9 A2c, session 24-25: R36 3.3k -> 4.7k fits the captured TREBLE span).
    std::printf("\n=== setTrebleWiperR @ 48 kHz ===\n");
    {
        // R36 = 4.7k (fitted), oracle: eq_reference.baxandall_tf(f, 0.5, at, R36=4.7e3).
        struct FitCfg { const char* name; double at; double db[kNF]; };
        static const std::vector<FitCfg> kFitCfgs = {
            { "treble boost (R36=4.7k)", 0.0,
              { -0.73859, -0.94982, -0.95087, -0.02094, 2.47944, 5.55938, 9.77493, 14.62264, 16.33774 } },
            { "treble cut (R36=4.7k)",   1.0,
              { -0.54449, -0.13128, 0.17533, -0.49446, -2.84076, -5.87327, -10.06648, -14.90593, -16.63924 } },
        };
        for (const auto& c : kFitCfgs)
        {
            double worstLo = 0.0;
            for (int i = 0; i < kNF; ++i)
            {
                if (kFreqs[i] > 2000.0) continue;
                const double meas = measureDb(0.5, c.at, kFreqs[i], 48000.0, 4700.0);
                worstLo = std::max(worstLo, std::abs(meas - c.db[i]));
            }
            const bool pass = worstLo <= 0.15;
            std::printf("  %-24s worst err (<=2 kHz) %.4f dB  %s\n", c.name, worstLo, pass ? "PASS" : "FAIL");
            if (! pass)
                ++failures;
        }

        // setTrebleWiperR(3.3k) (== the compile-time nominal kR36) reproduces the
        // UNMODIFIED stage's own output bit-exactly — the setter is not a parallel
        // code path, it feeds the same rebuild(). Compare against the C++ stage
        // itself (not the analytic oracle table, which already carries Test 1's
        // small bilinear-warp deviation from the continuous-time model).
        for (const auto& c : { kCfgs[3], kCfgs[4] })
        {
            double worst = 0.0;
            for (int i = 0; i < kNF; ++i)
            {
                const double baseline = measureDb(0.5, c.at, kFreqs[i], 48000.0);
                const double withSetter = measureDb(0.5, c.at, kFreqs[i], 48000.0, 3300.0);
                worst = std::max(worst, std::abs(withSetter - baseline));
            }
            const bool pass = worst <= 1e-9;
            std::printf("  %-24s setTrebleWiperR(3.3k) == unmodified stage, worst %.2e  %s\n",
                        c.name, worst, pass ? "PASS" : "FAIL");
            if (! pass)
                ++failures;
        }
    }

    // ---- Test 3: DC-step polarity — inverting, flat DC gain ≈ −0.926 --------
    std::printf("\n=== DC-step polarity: inverting; flat DC gain ~ -0.926 ===\n");
    {
        Baxandall stage;
        stage.prepare(48000.0);
        stage.setBass(0.5);
        stage.setTreble(0.5);
        const double vin = 1.0e-3;
        double y = 0.0;
        for (int n = 0; n < 200000; ++n) // settle the 2u2-scale... (largest here 22n) history
            y = stage.process(vin);
        const double gain = y / vin;
        const double kOracleDc = -0.925926;
        const bool ok = (y < 0.0) && std::abs(gain - kOracleDc) < 3e-3;
        std::printf("  Vout/Vin=%.6f (oracle %.6f)  sign %s  %s\n",
                    gain, kOracleDc, y < 0.0 ? "-" : "+", ok ? "PASS" : "FAIL");
        if (! ok)
            ++failures;
    }

    std::printf("\n%s\n", failures == 0 ? "All tests passed." : "Some tests FAILED.");
    return (failures > 0) ? 1 : 0;
}
