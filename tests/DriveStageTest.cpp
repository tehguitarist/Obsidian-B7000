// =============================================================================
// DriveStage (IC2_A non-inverting DRIVE gain) — validation
// =============================================================================
// Validates against the continuous-time analytic oracle
// (analysis/eq_reference.py :: drive_stage_tf) at four DRIVE-rheostat resistances
// spanning the gain range (min 4x .. max 78x), plus:
//   * DC-step polarity (non-inverting: +in -> +out, magnitude = DC gain),
//   * taper sanity (endpoints reach exactly 0 / 100k -> the full 78x / 4x span,
//     dodging the calibration §3 floor trap),
//   * rail clamp shape + that IC2_A at ×78 rails (calibration §6 GATE item).
//
// Like TrebleAttack, the caps discretise with the trapezoidal rule, so near
// Nyquist the stage warps vs the continuous oracle. We assert tight agreement
// (<=0.25 dB) up to 2 kHz and, at 5k/10k, that the error SHRINKS 48k->96k
// (proving it is bilinear warp, resolved by the Phase 6 oversampled region).
// =============================================================================

#include "../src/dsp/DriveStage.h"

#include <cmath>
#include <cstdio>
#include <vector>

static constexpr double PI = 3.14159265358979323846;

// Oracle reference (dB) from analysis/eq_reference.py :: drive_stage_tf, per Rdrive.
// Regenerate if component values change (single source of truth = the oracle).
struct Row { double rDrive; std::vector<double> db; };
static const std::vector<double> kFreqs = { 50, 100, 200, 500, 1000, 2000, 5000, 10000, 15000, 20000 };
static const std::vector<Row> kRef = {
    { 100000.0, {  12.3900, 12.3897, 12.3886, 12.3804, 12.3514, 12.2377, 11.5240,  9.7220,  7.9300,  6.4392 } },
    {  35355.3, {  19.3898, 19.3895, 19.3883, 19.3797, 19.3493, 19.2299, 18.4766, 16.5375, 14.5305, 12.7644 } },
    {  12500.0, {  26.2953, 26.2950, 26.2938, 26.2851, 26.2544, 26.1339, 25.3726, 23.4054, 21.3522, 19.5226 } },
    {      0.0, {  37.8133, 37.8129, 37.8117, 37.8031, 37.7723, 37.6515, 36.8883, 34.9144, 32.8500, 31.0048 } },
};

// Steady-state peak magnitude (dB) at a given Rdrive (rail clamp OFF -> linear).
static double measureDb(double freq, double fs, double rDrive)
{
    DriveStage stage;
    stage.prepare(fs);
    stage.setDriveResistance(rDrive);

    const double period = fs / freq;
    const int settle = static_cast<int>(std::max(0.25 * fs, 8.0 * period));
    const int measure = static_cast<int>(std::ceil(2.0 * period)) + 1;

    // Small amplitude so even the ×78 setting stays well inside the (disabled)
    // rails and the measurement is purely the linear transfer function.
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
    for (const auto& row : kRef)
    {
        std::printf("--- Rdrive = %.0f ohm ---\n", row.rDrive);
        for (size_t i = 0; i < kFreqs.size(); ++i)
        {
            const double meas = measureDb(kFreqs[i], 48000.0, row.rDrive);
            const double ref = row.db[i];
            const double err = std::abs(meas - ref);
            const bool checked = kFreqs[i] <= 2000.0;
            const bool pass = err <= 0.25;
            std::printf("  f=%8.1f  meas=%8.3f  ref=%8.3f  err=%.3f dB  %s\n",
                        kFreqs[i], meas, ref, err,
                        checked ? (pass ? "PASS" : "FAIL") : "(HF: see Test 2)");
            if (checked && ! pass)
                ++failures;
        }
    }

    // ---- Test 2: HF deviation is bilinear warp (shrinks 48k -> 96k) --------
    // The ONLY frequency shaping here is the C10 feedback rolloff (fixed corner
    // ~10.3 kHz, knob-INDEPENDENT). Because that corner sits in the top octave,
    // its bilinear warp near Nyquist is larger than a gentle shelf's: at 15k/20k
    // even the 96k residual is ~0.5-1.2 dB. That is faithful warp (it keeps
    // shrinking with SR, and the stage runs OVERSAMPLED in production, dsp.md),
    // not a model error. So we require the error to SHRINK everywhere, with a
    // tight 96k bound through 10 kHz and a looser one in the warped top octave.
    std::printf("\n=== HF: error must shrink from 48k to 96k (warp) ===\n");
    for (const auto& row : kRef)
    {
        for (size_t i = 0; i < kFreqs.size(); ++i)
        {
            if (kFreqs[i] < 5000.0) continue;
            const double ref = row.db[i];
            const double e48 = std::abs(measureDb(kFreqs[i], 48000.0, row.rDrive) - ref);
            const double e96 = std::abs(measureDb(kFreqs[i], 96000.0, row.rDrive) - ref);
            const bool shrinks = e96 < e48 + 1e-9;
            const double bound = (kFreqs[i] <= 10000.0) ? 0.30 : 1.50; // top-octave warp looser
            const bool small96 = e96 <= bound;
            const bool pass = shrinks && small96;
            std::printf("  Rd=%8.0f f=%8.1f  err48=%.3f  err96=%.3f (<=%.2f)  %s\n",
                        row.rDrive, kFreqs[i], e48, e96, bound,
                        pass ? "PASS" : (! shrinks ? "FAIL (not warp!)" : "FAIL (96k too big)"));
            if (! pass)
                ++failures;
        }
    }

    // ---- Test 3: DC-step polarity (non-inverting) --------------------------
    std::printf("\n=== DC-step polarity: non-inverting, gain = 1 + R15/Zg ===\n");
    {
        struct DcCase { double rDrive; double expectGain; };
        const std::vector<DcCase> cases = {
            { 100000.0, 1.0 + 330e3 / (3.3e3 + 100e3 + 1e3) }, // ~4.16x
            {      0.0, 1.0 + 330e3 / (3.3e3 + 0.0 + 1e3) },   // ~77.7x
        };
        for (const auto& c : cases)
        {
            DriveStage stage;
            stage.prepare(48000.0);
            stage.setDriveResistance(c.rDrive);
            // Tiny DC so ×78 stays linear; settle the trapezoidal cap transient.
            const double vin = 1.0e-3;
            double y = 0.0;
            for (int n = 0; n < 200; ++n)
                y = stage.process(vin);
            const double gain = y / vin;
            const bool positive = (y > 0.0); // non-inverting: same sign as input
            const bool magOk = std::abs(gain - c.expectGain) / c.expectGain < 0.001;
            std::printf("  Rd=%8.0f  Vout/Vin=%8.4f (expect %8.4f)  sign %s  %s\n",
                        c.rDrive, gain, c.expectGain, positive ? "+" : "-",
                        (positive && magOk) ? "PASS" : "FAIL");
            if (! (positive && magOk))
                ++failures;
        }
    }

    // ---- Test 4: taper sanity (endpoints + no floor trap) ------------------
    std::printf("\n=== DRIVE taper: endpoints reach 0 / 100k (no floor trap) ===\n");
    {
        const double rMin = DriveStage::driveResistance(1.0); // full drive -> 0 ohm
        const double rMax = DriveStage::driveResistance(0.0); // min drive  -> 100k
        const double gMax = 1.0 + 330e3 / (3.3e3 + rMin + 1e3);
        const double gMin = 1.0 + 330e3 / (3.3e3 + rMax + 1e3);
        const bool zeroOk = rMin == 0.0;                       // exact 0 -> full 78x
        const bool maxOk = std::abs(rMax - 100e3) < 1.0;
        const bool spanOk = gMax > 77.0 && gMin < 4.3 && gMin > 4.0;
        std::printf("  x=1 -> Rd=%.3f ohm (gain %.2fx)   x=0 -> Rd=%.0f ohm (gain %.2fx)\n",
                    rMin, gMax, rMax, gMin);
        std::printf("  0-ohm min: %s | 100k max: %s | 4x..78x span: %s\n",
                    zeroOk ? "PASS" : "FAIL", maxOk ? "PASS" : "FAIL", spanOk ? "PASS" : "FAIL");
        // Monotonic increasing gain with knob (spot-check).
        double prev = -1.0; bool mono = true;
        for (double x = 0.0; x <= 1.0001; x += 0.1)
        {
            const double g = 1.0 + 330e3 / (3.3e3 + DriveStage::driveResistance(x) + 1e3);
            if (g < prev - 1e-9) mono = false;
            prev = g;
        }
        std::printf("  gain monotonic in knob: %s\n", mono ? "PASS" : "FAIL");
        if (! (zeroOk && maxOk && spanOk && mono))
            ++failures;
    }

    // ---- Test 5: rail clamp (IC2_A at ×78 rails; shape + ceiling) ----------
    std::printf("\n=== Rail clamp: ×78 drive hits the rail; clamp is bounded ===\n");
    {
        DriveStage stage;
        stage.prepare(48000.0);
        stage.setDriveResistance(0.0);   // max gain ~78x
        stage.setRailVoltages(3.3, 3.3); // ±3.3 V around VD (calibration §6 estimate)
        stage.setRailClampEnabled(true);

        // 0.2 V peak input * 78 -> ~15.5 V unclamped; must clamp to <= +3.3 V.
        double peakPos = 0.0, peakNeg = 0.0;
        const double freq = 200.0, fs = 48000.0;
        for (int n = 0; n < 4000; ++n)
        {
            const double x = 0.2 * std::sin(2.0 * PI * freq * n / fs);
            const double y = stage.process(x);
            peakPos = std::max(peakPos, y);
            peakNeg = std::min(peakNeg, y);
        }
        const bool clamped = peakPos <= 3.3 + 1e-9 && peakNeg >= -3.3 - 1e-9;
        const bool active = peakPos > 3.0 && peakNeg < -3.0; // genuinely reached the rail
        std::printf("  clamped output range [%.4f, %.4f] V (rails ±3.3)  %s\n",
                    peakNeg, peakPos, (clamped && active) ? "PASS" : "FAIL");
        if (! (clamped && active))
            ++failures;

        // Disabled clamp must be bit-identical linear (no phantom shaping).
        DriveStage lin;
        lin.prepare(48000.0);
        lin.setDriveResistance(100e3);
        lin.setRailClampEnabled(false);
        const double y = [&] { double v = 0; for (int n = 0; n < 200; ++n) v = lin.process(1e-3); return v; }();
        const bool linOk = std::abs(y / 1e-3 - (1.0 + 330e3 / 104.3e3)) / (1.0 + 330e3 / 104.3e3) < 1e-3;
        std::printf("  clamp-disabled stays linear (%.4fx): %s\n", y / 1e-3, linOk ? "PASS" : "FAIL");
        if (! linOk)
            ++failures;
    }

    std::printf("\n%s\n", failures == 0 ? "All tests passed." : "Some tests FAILED.");
    return (failures > 0) ? 1 : 0;
}
