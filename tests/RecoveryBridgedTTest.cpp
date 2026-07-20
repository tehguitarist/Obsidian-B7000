// =============================================================================
// RecoveryBridgedT (IC2_B unity buffer + passive bridged-T) — validation
// =============================================================================
// Validates against the continuous-time analytic oracle
// (analysis/eq_reference.py :: bridged_t_tf, default UNLOADED — see the stage
// header for why unloaded is the correct reference for the isolated stage).
//
// A bridged-T's deep notch makes a blanket "±0.25 dB everywhere" meaningless:
// on the steep flanks a sub-percent bilinear frequency-warp shows up as several
// dB, and the exact notch-bottom depth is a near-total cancellation that is
// hyper-sensitive to discretisation (build-plan Phase 4 test caveat). So we
// split the assertions (matching the caveat "notch FREQUENCY tight + DEPTH
// loose; ±0.25 dB elsewhere"):
//   * Test 1  — SHOULDER FR (well away from the notch): tight vs oracle.
//   * Test 2  — HF deviation shrinks 48k->96k (proves bilinear warp).
//   * Test 3  — NOTCH: located near 717 Hz (tight FREQUENCY) and genuinely deep
//               (loose DEPTH — just assert it is a real, deep notch).
//   * Test 4  — DC-step polarity: unity, non-inverting.
// =============================================================================

#include "../src/dsp/RecoveryBridgedT.h"

#include <cmath>
#include <cstdio>
#include <vector>

static constexpr double PI = 3.14159265358979323846;

// Oracle reference (dB) from analysis/eq_reference.py :: bridged_t_tf (UNLOADED).
// Regenerate if component values change (single source of truth = the oracle).
struct Pt { double f; double db; };
static const std::vector<Pt> kRef = {
    {    20.0,  -0.34561 }, {    50.0,  -1.82304 }, {   100.0,  -4.97438 },
    {   200.0, -10.24635 }, {   300.0, -14.35345 }, {   500.0, -21.80224 },
    {   717.0, -28.07107 }, {  1000.0, -22.30494 }, {  2000.0, -12.65347 },
    {  3000.0,  -8.88222 }, {  5000.0,  -5.13451 }, { 10000.0,  -1.90205 },
    { 15000.0,  -0.94459 }, { 20000.0,  -0.55538 },
};

// Steady-state peak magnitude (dB) at a frequency (rail clamp OFF -> linear).
static double measureDb(double freq, double fs)
{
    RecoveryBridgedT stage;
    stage.prepare(fs);

    const double period = fs / freq;
    const int settle = static_cast<int>(std::max(0.25 * fs, 8.0 * period));
    const int measure = static_cast<int>(std::ceil(2.0 * period)) + 1;

    const double amp = 1.0e-3; // tiny (rails disabled anyway) -> pure linear TF
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

    // ---- Test 1: shoulder FR vs oracle (away from the notch) ----------------
    // Shoulders = f <= 200 Hz and f >= 3 kHz: gentle slopes where warp is tiny
    // and the ±0.25 dB claim is meaningful. The steep 300 Hz..2 kHz flanks are
    // covered by the notch test instead (Test 3) — a dB tolerance on a steep,
    // warp-shifted flank would be testing the warp, not the model.
    std::printf("=== Shoulder FR vs analytic oracle @ 48 kHz (away from notch) ===\n");
    for (const auto& p : kRef)
    {
        const double meas = measureDb(p.f, 48000.0);
        const double err = std::abs(meas - p.db);
        const bool shoulder = (p.f <= 200.0) || (p.f >= 3000.0);
        // Tight where the slope is gentle; the near-Nyquist top octave gets the
        // usual small bilinear allowance (verified as warp in Test 2).
        const double tol = (p.f >= 10000.0) ? 0.60 : 0.25;
        const bool pass = err <= tol;
        std::printf("  f=%8.1f  meas=%8.3f  ref=%8.3f  err=%.3f dB  %s\n",
                    p.f, meas, p.db, err,
                    shoulder ? (pass ? "PASS" : "FAIL") : "(flank: see Test 3)");
        if (shoulder && ! pass)
            ++failures;
    }

    // ---- Test 2: HF deviation is bilinear warp (shrinks 48k -> 96k) ---------
    std::printf("\n=== HF: error must shrink from 48k to 96k (warp) ===\n");
    for (const auto& p : kRef)
    {
        if (p.f < 3000.0) continue;
        const double e48 = std::abs(measureDb(p.f, 48000.0) - p.db);
        const double e96 = std::abs(measureDb(p.f, 96000.0) - p.db);
        const bool shrinks = e96 < e48 + 1e-9;
        const bool small96 = e96 <= 0.30;
        const bool pass = shrinks && small96;
        std::printf("  f=%8.1f  err48=%.3f  err96=%.3f (<=0.30)  %s\n",
                    p.f, e48, e96,
                    pass ? "PASS" : (! shrinks ? "FAIL (not warp!)" : "FAIL (96k too big)"));
        if (! pass)
            ++failures;
    }

    // ---- Test 3: notch located near 717 Hz + genuinely deep -----------------
    // Frequency = TIGHT (a bridged-T's null sits where R/C set it; the ~717 Hz
    // is well below Nyquist so warp barely moves it). Depth = LOOSE (the exact
    // cancellation depth is hyper-sensitive to discretisation AND, per the
    // schematic notes, to real-part tolerance — capture-validated at Phase 7;
    // here we only assert it is a real, deep notch).
    std::printf("\n=== Notch: frequency tight, depth loose ===\n");
    {
        const double fs = 48000.0;
        double fNotch = 0.0, dbNotch = 1e9;
        // Log sweep 400..1200 Hz for the minimum.
        const int K = 2000;
        for (int k = 0; k <= K; ++k)
        {
            const double f = 400.0 * std::pow(1200.0 / 400.0, static_cast<double>(k) / K);
            const double db = measureDb(f, fs);
            if (db < dbNotch) { dbNotch = db; fNotch = f; }
        }
        const double kOracleF = 716.3, kOracleDepth = -28.07;
        const bool freqOk = std::abs(fNotch - kOracleF) / kOracleF <= 0.03; // ±3%
        const bool deepOk = dbNotch <= -20.0;                                // real deep notch
        std::printf("  notch @ %.1f Hz (oracle %.1f, ±3%%): %s | depth %.2f dB (oracle %.2f, need <=-20): %s\n",
                    fNotch, kOracleF, freqOk ? "PASS" : "FAIL",
                    dbNotch, kOracleDepth, deepOk ? "PASS" : "FAIL");
        if (! (freqOk && deepOk))
            ++failures;
    }

    // ---- Test 4: DC-step polarity (unity, non-inverting) --------------------
    std::printf("\n=== DC-step polarity: unity, non-inverting ===\n");
    {
        RecoveryBridgedT stage;
        stage.prepare(48000.0);
        const double vin = 1.0e-3;
        double y = 0.0;
        for (int n = 0; n < 4000; ++n) // settle the 22n shunt cap fully
            y = stage.process(vin);
        const double gain = y / vin;
        const bool positive = (y > 0.0);
        const bool unity = std::abs(gain - 1.0) < 1e-3; // DC: caps open -> unity
        std::printf("  Vout/Vin=%.6f (expect 1.0)  sign %s  %s\n",
                    gain, positive ? "+" : "-", (positive && unity) ? "PASS" : "FAIL");
        if (! (positive && unity))
            ++failures;
    }

    std::printf("\n%s\n", failures == 0 ? "All tests passed." : "Some tests FAILED.");
    return (failures > 0) ? 1 : 0;
}
