// =============================================================================
// TrebleAttack (treble net + ATTACK switch) — frequency-response validation
// =============================================================================
// Validates the MNA stage against the continuous-time analytic oracle
// (analysis/eq_reference.py :: treble_attack_tf, CORRECTED 2026-07-20 topology)
// for all three ATTACK positions (Boost / Flat / Cut).
//
// The stage discretises its caps with the trapezoidal (bilinear) rule, so near
// Nyquist it warps vs the continuous oracle. We therefore:
//   * assert tight agreement (<=0.25 dB) where warp is negligible (<= 2 kHz),
//   * at 5 k / 10 kHz, assert the error SHRINKS from 48 k to 96 k (proving the
//     deviation is bilinear warp, not a model error) and is small at 96 k.
// In the full plugin this stage runs inside the oversampled region (dsp.md), so
// the top-octave warp is resolved there; this isolated test documents it.
//
// Also checks: (a) NO position mutes (a regression guard for the switch-pole
// bug that grounded node M), and (b) all three positions share the same low end
// (they differ only in treble).
// =============================================================================

#include "../src/dsp/TrebleAttack.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <vector>

static constexpr double PI = 3.14159265358979323846;

// Oracle reference (dB) from analysis/eq_reference.py at these frequencies.
// Regenerate if component values change (single source of truth = the oracle).
struct Ref { double f; double boost, flat, cut; };
static const std::vector<Ref> kRef = {
    //  f Hz     boost       flat        cut
    {    50.0, -13.7468,  -13.7352,  -13.7436 },
    {   100.0, -17.8995,  -17.8916,  -17.9058 },
    {   200.0, -24.8881,  -24.9179,  -24.9447 },
    {   500.0, -23.2228,  -23.5393,  -23.6349 },
    {  1000.0, -13.1894,  -14.3695,  -14.6876 },
    {  2000.0,  -7.0329,  -10.1982,  -11.2912 },
    {  5000.0,  -2.0760,   -8.3017,  -12.6813 },
    { 10000.0,  -0.6145,   -7.9694,  -16.9625 },
};

static double refFor(const Ref& r, TrebleAttack::Attack a)
{
    switch (a)
    {
        case TrebleAttack::Attack::Boost: return r.boost;
        case TrebleAttack::Attack::Flat:  return r.flat;
        case TrebleAttack::Attack::Cut:   return r.cut;
    }
    return 0.0;
}

// Steady-state peak magnitude (dB). Settles then measures the peak over 2 periods.
static double measureDb(double freq, double fs, TrebleAttack::Attack a)
{
    TrebleAttack stage;
    stage.prepare(fs);
    stage.setAttack(a);

    const double period = fs / freq;
    const int settle = static_cast<int>(std::max(0.25 * fs, 8.0 * period));
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
    int failures = 0;
    const char* names[3] = { "Boost", "Flat", "Cut" };
    const TrebleAttack::Attack positions[3] = {
        TrebleAttack::Attack::Boost, TrebleAttack::Attack::Flat, TrebleAttack::Attack::Cut
    };

    // ---- Test 1: FR vs oracle at 48 kHz (tight <= 2 kHz) --------------------
    std::printf("=== FR vs analytic oracle @ 48 kHz ===\n");
    for (int pi = 0; pi < 3; ++pi)
    {
        std::printf("--- ATTACK = %s ---\n", names[pi]);
        for (const auto& r : kRef)
        {
            const double meas = measureDb(r.f, 48000.0, positions[pi]);
            const double ref = refFor(r, positions[pi]);
            const double err = std::abs(meas - ref);
            const double tol = (r.f <= 2000.0) ? 0.25 : 100.0; // HF handled by Test 2
            const bool checked = (r.f <= 2000.0);
            const bool pass = err <= tol;
            std::printf("  f=%8.1f  meas=%8.3f  ref=%8.3f  err=%.3f dB  %s\n",
                        r.f, meas, ref, err, checked ? (pass ? "PASS" : "FAIL") : "(HF: see Test 2)");
            if (checked && ! pass)
                ++failures;
        }
    }

    // ---- Test 2: HF deviation is bilinear warp (shrinks 48k -> 96k) ---------
    std::printf("\n=== HF: error must shrink from 48k to 96k (warp), and be small at 96k ===\n");
    for (int pi = 0; pi < 3; ++pi)
    {
        for (const auto& r : kRef)
        {
            if (r.f < 5000.0) continue;
            const double ref = refFor(r, positions[pi]);
            const double e48 = std::abs(measureDb(r.f, 48000.0, positions[pi]) - ref);
            const double e96 = std::abs(measureDb(r.f, 96000.0, positions[pi]) - ref);
            const bool shrinks = e96 < e48 + 1e-9;
            const bool small96 = e96 <= 0.30;
            const bool pass = shrinks && small96;
            std::printf("  %-5s f=%8.1f  err48=%.3f  err96=%.3f  %s\n",
                        names[pi], r.f, e48, e96,
                        pass ? "PASS" : (! shrinks ? "FAIL (not warp!)" : "FAIL (96k too big)"));
            if (! pass)
                ++failures;
        }
    }

    // ---- Test 3: NO position mutes (switch-pole-bug regression guard) -------
    std::printf("\n=== No position mutes (regression guard for the M->GND mute bug) ===\n");
    for (int pi = 0; pi < 3; ++pi)
    {
        const double meas = measureDb(1000.0, 48000.0, positions[pi]);
        const bool pass = meas > -60.0; // real level is ~ -13..-15 dB; mute would be < -200
        std::printf("  %-5s @1kHz = %.2f dB  %s\n", names[pi], meas,
                    pass ? "PASS (signal present)" : "FAIL (MUTED!)");
        if (! pass)
            ++failures;
    }

    // ---- Test 4: all positions share the low end (differ only in treble) ---
    std::printf("\n=== Low-end consistency across positions (@100 Hz) ===\n");
    {
        const double b = measureDb(100.0, 48000.0, TrebleAttack::Attack::Boost);
        const double f = measureDb(100.0, 48000.0, TrebleAttack::Attack::Flat);
        const double c = measureDb(100.0, 48000.0, TrebleAttack::Attack::Cut);
        const double spread = std::max({ b, f, c }) - std::min({ b, f, c });
        const bool pass = spread < 0.10;
        std::printf("  boost=%.3f flat=%.3f cut=%.3f  spread=%.3f dB  %s\n",
                    b, f, c, spread, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    // ---- Test 5: treble ordering Boost > Flat > Cut at 5 kHz ----------------
    std::printf("\n=== Treble ordering Boost > Flat > Cut (@5 kHz) ===\n");
    {
        const double b = measureDb(5000.0, 48000.0, TrebleAttack::Attack::Boost);
        const double f = measureDb(5000.0, 48000.0, TrebleAttack::Attack::Flat);
        const double c = measureDb(5000.0, 48000.0, TrebleAttack::Attack::Cut);
        const bool pass = (b > f + 1.0) && (f > c + 1.0);
        std::printf("  boost=%.3f > flat=%.3f > cut=%.3f  %s\n", b, f, c, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    std::printf("\n%s\n", failures == 0 ? "All tests passed." : "Some tests FAILED.");
    return (failures > 0) ? 1 : 0;
}
