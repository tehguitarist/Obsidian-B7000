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

// Oracle reference from analysis/eq_reference.py :: treble_attack_transimpedance
// at these frequencies, in dB re 1 ohm — the stage takes the J201 drain's NORTON
// CURRENT now, so its transfer is a TRANSIMPEDANCE V(Q)/I, not a voltage gain
// (TrebleAttack.h "Stage boundary", 2026-07-22). The oracle is evaluated at
// JfetStage's NOMINAL gm/ro/Rq2, which is what a default-constructed stage uses.
// Regenerate if component values or those nominals change (single source of
// truth = the oracle).
struct Ref { double f; double boost, flat, cut; };
static const std::vector<Ref> kRef = {
    //  f Hz     boost       flat        cut
    {     50.0,   85.6449,   85.6596,   85.6498 },
    {    100.0,   77.3194,   77.3275,   77.3132 },
    {    200.0,   65.5089,   65.4789,   65.4522 },
    {    500.0,   60.5204,   60.2031,   60.1079 },
    {   1000.0,   65.9664,   64.7786,   64.4641 },
    {   2000.0,   68.9722,   65.7957,   64.7078 },
    {   5000.0,   72.2762,   66.0806,   61.6870 },
    {  10000.0,   73.4138,   66.1214,   57.0993 },
};

// Damped golden set (session-19): treble_attack_tf(..., RdampC5 = kTestDampR),
// same Zs recipe as kRef. Validates the lossy-C5 notch-damping code path against
// the independent Python oracle. Regenerate alongside kRef if anything changes.
static constexpr double kTestDampR = 30000.0;
static const std::vector<Ref> kRefDamped = {
    //  f Hz     boost       flat        cut
    {      50.0,   85.2483,   85.2633,   85.2534 },
    {     100.0,   77.0918,   77.1006,   77.0860 },
    {     200.0,   67.7351,   67.7059,   67.6789 },
    {     500.0,   63.0893,   62.7722,   62.6769 },
    {    1000.0,   65.5173,   64.3293,   64.0149 },
    {    2000.0,   67.9486,   64.7717,   63.6840 },
    {    5000.0,   71.0821,   64.8864,   60.4928 },
    {   10000.0,   72.1943,   64.9021,   55.8799 },
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

// Steady-state peak magnitude (dB re 1 ohm, i.e. volts out per amp in — the stage
// is driven by the J201's Norton current). Settles then measures over 2 periods.
static double measureDb(double freq, double fs, TrebleAttack::Attack a, double dampR = 0.0)
{
    TrebleAttack stage;
    stage.prepare(fs);
    stage.setAttack(a);
    stage.setNotchDamp(dampR); // session-19: lossy-C5 notch damping (0 = ideal)

    const double period = fs / freq;
    // 2 s, not the old 0.25 s: with the J201 source network stamped in (2026-07-22),
    // node G floats on ~396 kOhm against the 22 nF ladder, adding a time constant slow
    // enough that 0.25 s left a ~0.4 dB settling error at 200 Hz — which looks exactly
    // like a model error but is not (at 2 s the agreement is <= 0.005 dB below 1 kHz).
    const int settle = static_cast<int>(std::max(2.0 * fs, 8.0 * period));
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
            // "Shrinks with rate" is the signature of bilinear warp. But when the 48 k
            // error is ALREADY negligible there is no warp to shrink, and the
            // rate-to-rate difference is just measurement noise — so an already-tiny
            // e96 passes on its own. (Flat sits at ~0.005 dB at both rates: that is a
            // stronger result than "shrinks", not a weaker one.)
            const bool shrinks = e96 < e48 + 1e-9 || e96 <= 0.05;
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
        // Real transimpedance here is ~ +64..+66 dB re 1 ohm; a mute reads < -200.
        const bool pass = meas > 0.0;
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

    // ---- Test 6: notch damping (lossy C5) matches the oracle at Rd>0 --------
    // Validates the session-19 trebleLadderDampR code path (setNotchDamp): the C++
    // lossy-cap Norton reduction must track the independent Python oracle's series
    // Rd+C5 admittance. Same tight <=2 kHz tolerance as Test 1 (HF is warp, Test 2).
    std::printf("\n=== Notch damping (Rd=%.0f) vs oracle @ 48 kHz ===\n", kTestDampR);
    for (int pi = 0; pi < 3; ++pi)
    {
        std::printf("--- ATTACK = %s ---\n", names[pi]);
        for (const auto& r : kRefDamped)
        {
            if (r.f > 2000.0) continue; // HF warp not re-checked here (Test 2 covers it)
            const double meas = measureDb(r.f, 48000.0, positions[pi], kTestDampR);
            const double ref = refFor(r, positions[pi]);
            const double err = std::abs(meas - ref);
            const bool pass = err <= 0.25;
            std::printf("  f=%8.1f  meas=%8.3f  ref=%8.3f  err=%.3f dB  %s\n",
                        r.f, meas, ref, err, pass ? "PASS" : "FAIL");
            if (! pass)
                ++failures;
        }
    }

    // ---- Test 7: notch damping shallows the ~322 Hz two-path cancellation ---
    // The whole point of Rd: the ideal notch (~28 dB) is far deeper than the
    // capture (-3.4 dB). Damping must raise the ~320 Hz null relative to Rd=0.
    std::printf("\n=== Notch damping shallows the 320 Hz null (Boost) ===\n");
    {
        const double ideal = measureDb(320.0, 48000.0, TrebleAttack::Attack::Boost, 0.0);
        const double damped = measureDb(320.0, 48000.0, TrebleAttack::Attack::Boost, kTestDampR);
        const bool pass = damped > ideal + 3.0; // meaningfully shallower
        std::printf("  320 Hz: ideal=%.2f  damped=%.2f  lift=%.2f dB  %s\n",
                    ideal, damped, damped - ideal, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    std::printf("\n%s\n", failures == 0 ? "All tests passed." : "Some tests FAILED.");
    return (failures > 0) ? 1 : 0;
}
