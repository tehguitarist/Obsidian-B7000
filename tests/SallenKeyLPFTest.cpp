// =============================================================================
// SallenKeyLPF ×2 (IC4_B ≈ 10.7 kHz, IC4_A ≈ 3.3 kHz) — validation
// =============================================================================
// Validates each instance against the continuous-time analytic oracle
// (analysis/eq_reference.py :: sallen_key_lpf_tf), which is derived from the
// SAME 2-node nodal formulation the stage implements (so the match is exact bar
// bilinear warp). Both corners are low enough that trapezoidal-cap warping shows
// in the top octave at base rate — resolved by the Phase-6 oversampled region —
// so we assert tight (<=0.25 dB) up to 2 kHz and, above, that the error SHRINKS
// 48k->96k (proving warp, not a model error). Plus:
//   * −12 dB/oct asymptotic 2nd-order rolloff (an octave above the corner),
//   * DC unity + non-inverting (DC-step),
//   * rail clamp shape + linear-when-disabled.
// =============================================================================

#include "../src/dsp/SallenKeyLPF.h"

#include <cmath>
#include <cstdio>
#include <vector>

static constexpr double PI = 3.14159265358979323846;

struct Pt { double f; double db; };
struct Case { const char* name; SallenKeyLPF::Values v; double fc; std::vector<Pt> ref; };

// Oracle reference (dB) from analysis/eq_reference.py :: sallen_key_lpf_tf.
// Regenerate if component values change (single source of truth = the oracle).
static const std::vector<Case> kCases = {
    { "IC4_B (~10.7k)", SallenKeyLPF::kIC4B, 10730.2, {
        {    50.0, -0.00025 }, {  100.0, -0.00100 }, {  200.0, -0.00400 }, {  500.0, -0.02498 },
        {  1000.0, -0.09931 }, { 2000.0, -0.38790 }, { 3000.0, -0.84079 }, { 5000.0, -2.10461 },
        {  7000.0, -3.63768 }, {10000.0, -6.08513 }, {15000.0,-10.00273 }, {20000.0,-13.48140 } } },
    { "IC4_A (~3.3k)", SallenKeyLPF::kIC4A, 3336.9, {
        {    50.0, -0.00009 }, {  100.0, -0.00037 }, {  200.0, -0.00151 }, {  500.0, -0.01124 },
        {  1000.0, -0.07069 }, { 2000.0, -0.65364 }, { 3000.0, -2.37639 }, { 5000.0, -7.95830 },
        {  7000.0,-13.17501 }, {10000.0,-19.16374 }, {15000.0,-26.14021 }, {20000.0,-31.12184 } } },
};

static double measureDb(const SallenKeyLPF::Values& v, double freq, double fs)
{
    SallenKeyLPF stage;
    stage.configure(v);
    stage.prepare(fs);

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

    // ---- Test 1: FR vs oracle @ 48 kHz (tight <= 2 kHz) --------------------
    std::printf("=== FR vs analytic oracle @ 48 kHz ===\n");
    for (const auto& cse : kCases)
    {
        std::printf("--- %s ---\n", cse.name);
        for (const auto& p : cse.ref)
        {
            const double meas = measureDb(cse.v, p.f, 48000.0);
            const double err = std::abs(meas - p.db);
            const bool checked = p.f <= 2000.0;
            const bool pass = err <= 0.25;
            std::printf("  f=%8.1f  meas=%9.4f  ref=%9.4f  err=%.3f dB  %s\n",
                        p.f, meas, p.db, err,
                        checked ? (pass ? "PASS" : "FAIL") : "(HF: see Test 2)");
            if (checked && ! pass)
                ++failures;
        }
    }

    // ---- Test 2: HF deviation is bilinear warp (shrinks 48k -> 96k) --------
    std::printf("\n=== HF: error must shrink from 48k to 96k (warp) ===\n");
    for (const auto& cse : kCases)
    {
        for (const auto& p : cse.ref)
        {
            if (p.f < 3000.0) continue;
            const double e48 = std::abs(measureDb(cse.v, p.f, 48000.0) - p.db);
            const double e96 = std::abs(measureDb(cse.v, p.f, 96000.0) - p.db);
            const bool shrinks = e96 < e48 + 1e-9;
            // Warp on a low-Q rolloff near Nyquist is sizeable in dB; require it
            // to keep shrinking with SR and stay bounded at 96k.
            const double bound = (p.f <= 7000.0) ? 0.60 : 3.0;
            const bool small96 = e96 <= bound;
            const bool pass = shrinks && small96;
            std::printf("  %-14s f=%8.1f  err48=%.3f  err96=%.3f (<=%.2f)  %s\n",
                        cse.name, p.f, e48, e96, bound,
                        pass ? "PASS" : (! shrinks ? "FAIL (not warp!)" : "FAIL (96k too big)"));
            if (! pass)
                ++failures;
        }
    }

    // ---- Test 3: 2nd-order asymptotic rolloff (~ -12 dB/oct well above fc) --
    std::printf("\n=== 2nd-order rolloff: ~-12 dB/octave above the corner ===\n");
    for (const auto& cse : kCases)
    {
        // Measure at 4*fc and 8*fc at 768 kHz (deep in the stopband, safely below
        // Nyquist even for IC4_B ≈10.7 kHz where 8*fc=85.8 kHz < 45% of 768k
        // Nyquist), so the bilinear warp is minimal and won't skew the slope.
        const double f1 = 4.0 * cse.fc, f2 = 8.0 * cse.fc;
        const double d1 = measureDb(cse.v, f1, 768000.0);
        const double d2 = measureDb(cse.v, f2, 768000.0);
        const double slope = d2 - d1; // dB per octave
        const bool pass = slope < -11.0 && slope > -13.0;
        std::printf("  %-14s %.0f->%.0f Hz: %.2f -> %.2f dB  slope %.2f dB/oct  %s\n",
                    cse.name, f1, f2, d1, d2, slope, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    // ---- Test 4: DC-step polarity (unity, non-inverting) --------------------
    std::printf("\n=== DC-step polarity: unity, non-inverting ===\n");
    for (const auto& cse : kCases)
    {
        SallenKeyLPF stage;
        stage.configure(cse.v);
        stage.prepare(48000.0);
        const double vin = 1.0e-3;
        double y = 0.0;
        for (int n = 0; n < 4000; ++n)
            y = stage.process(vin);
        const double gain = y / vin;
        const bool positive = (y > 0.0);
        const bool unity = std::abs(gain - 1.0) < 1e-3;
        std::printf("  %-14s Vout/Vin=%.6f  sign %s  %s\n",
                    cse.name, gain, positive ? "+" : "-", (positive && unity) ? "PASS" : "FAIL");
        if (! (positive && unity))
            ++failures;
    }

    // ---- Test 5: rail clamp (bounded; linear when disabled) -----------------
    std::printf("\n=== Rail clamp: bounded output; disabled == linear ===\n");
    {
        SallenKeyLPF stage;
        stage.configure(SallenKeyLPF::kIC4B);
        stage.prepare(48000.0);
        stage.setRailVoltages(3.3, 3.3);
        stage.setRailClampEnabled(true);
        // Big in-band drive (200 Hz passes ~0 dB) -> output must clamp to <= ±3.3.
        double peakPos = 0.0, peakNeg = 0.0;
        for (int n = 0; n < 4000; ++n)
        {
            const double x = 5.0 * std::sin(2.0 * PI * 200.0 * n / 48000.0);
            const double y = stage.process(x);
            peakPos = std::max(peakPos, y);
            peakNeg = std::min(peakNeg, y);
        }
        const bool clamped = peakPos <= 3.3 + 1e-9 && peakNeg >= -3.3 - 1e-9;
        const bool active = peakPos > 3.0 && peakNeg < -3.0;
        std::printf("  clamped range [%.4f, %.4f] V (rails ±3.3)  %s\n",
                    peakNeg, peakPos, (clamped && active) ? "PASS" : "FAIL");
        if (! (clamped && active))
            ++failures;

        SallenKeyLPF lin;
        lin.configure(SallenKeyLPF::kIC4B);
        lin.prepare(48000.0);
        lin.setRailClampEnabled(false);
        double y = 0.0;
        for (int n = 0; n < 4000; ++n)
            y = lin.process(1e-3);
        const bool linOk = std::abs(y / 1e-3 - 1.0) < 1e-3; // DC unity, unclamped
        std::printf("  clamp-disabled stays linear (%.6fx): %s\n", y / 1e-3, linOk ? "PASS" : "FAIL");
        if (! linOk)
            ++failures;
    }

    std::printf("\n%s\n", failures == 0 ? "All tests passed." : "Some tests FAILED.");
    return (failures > 0) ? 1 : 0;
}
