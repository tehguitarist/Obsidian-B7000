// =============================================================================
// JfetStage (J201 Q1 CS + Q2 active load) — validation
// =============================================================================
// The first NONLINEAR stage. Validated against the analytic small-signal oracle
// (analysis/eq_reference.py :: jfet_stage_lin_tf), computed here inline as the
// complex Laplace TF from the header constants (no hardcoded table -> the
// trapezoidal/bilinear implementation is cross-checked directly).
//
//   Test 1 — Linear FR vs oracle across the FULL band (20 Hz..20 kHz) @ 48/96 kHz.
//            Tiny amplitude => the waveshaper is ~identity => pure linear TF. Tight
//            EVERYWHERE (<=0.05 dB): all corners (HP 145 Hz, shelf 219/719 Hz) are
//            sub-kHz, so there is NO audible-band bilinear warp (like MasterOut).
//   Test 2 — HF-lift shelf: HF plateau sits ~+10.3 dB (1+gmR6) above the ~200 Hz
//            shoulder; corners at 219 Hz (zero) / ~719 Hz (pole).
//   Test 3 — DC-step polarity: INVERTING (+in -> -out on the AC edge), AC-coupled
//            (C2 HP) so it decays to ~0. Resolves circuit.md's JFET-sign carry-fwd.
//   Test 4 — Nonlinearity: mild ASYMMETRIC soft saturation. A hot tone compresses
//            (peak gain < small-signal gain) and the +/- output peaks differ
//            (satPos != satNeg -> even harmonics); the static curve is monotonic.
//   Test 5 — Small-signal limit: at tiny drive the waveshaper is ~identity, so the
//            1 kHz gain matches -G0*shelf (the mid/HF small-signal gain).
//
// NOTE: kG0, kGmR6, kSatPos, kSatNeg are NOMINAL placeholders (fit to captures at
// Phase 7). These tests validate the STRUCTURE — filter shape, polarity, and the
// qualitative nonlinearity — all of which are invariant under a later amplitude
// refit; they do NOT assert an absolute "correct" gain (there is no capture yet).
// =============================================================================

#include "../src/dsp/JfetStage.h"

#include <cmath>
#include <complex>
#include <cstdio>

static constexpr double PI = 3.14159265358979323846;

// Analytic small-signal oracle: H(f) = -G0 * HP(s) * shelf(s).
static double oracleDb(double freq)
{
    const std::complex<double> s(0.0, 2.0 * PI * freq);
    const double tauHp = (JfetStage::kR4 + JfetStage::kR5) * JfetStage::kC2;
    const std::complex<double> hp = s * tauHp / (1.0 + s * tauHp);
    const double tauZ = JfetStage::kR6 * JfetStage::kC3;
    const double tauP = tauZ / (1.0 + JfetStage::kGmR6);
    const std::complex<double> shelf = (1.0 + s * tauZ) / (1.0 + s * tauP);
    const double mag = JfetStage::kG0 * std::abs(hp * shelf);
    return (mag > 0.0) ? 20.0 * std::log10(mag) : -300.0;
}

// Steady-state peak magnitude (dB) at a given frequency, small-signal (linear).
static double measureDb(double freq, double fs, double amp)
{
    JfetStage stage;
    stage.prepare(fs);

    const double period = fs / freq;
    // Slowest pole is the ~145 Hz input HP (tau = 1.1 ms) — settle is dominated by
    // the low-frequency measurement window, not the filter transient.
    const int settle = static_cast<int>(std::max(0.1 * fs, 12.0 * period));
    const int measure = static_cast<int>(std::ceil(2.0 * period)) + 1;

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
    const double kSmall = 1.0e-6; // << sat => waveshaper ~ identity

    // ---- Test 1: linear FR vs oracle across the full band (tight everywhere) --
    std::printf("=== FR vs analytic oracle (full band, tight — no audible-band caps) ===\n");
    for (const double fs : { 48000.0, 96000.0 })
    {
        double worst = 0.0;
        double worstF = 0.0;
        for (int i = 0; i < kNF; ++i)
        {
            if (kFreqs[i] > fs * 0.45) continue; // stay clear of Nyquist
            const double err = std::abs(measureDb(kFreqs[i], fs, kSmall) - oracleDb(kFreqs[i]));
            if (err > worst) { worst = err; worstF = kFreqs[i]; }
        }
        const bool pass = worst <= 0.05;
        std::printf("  fs=%6.0f  worst err %.5f dB @ %.0f Hz  %s\n",
                    fs, worst, worstF, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    // ---- Test 2: HF-lift shelf (+10.3 dB, corners 219/719 Hz) -----------------
    std::printf("\n=== HF-lift shelf: HF plateau ~+10.3 dB above the ~200 Hz shoulder ===\n");
    {
        const double gLo = measureDb(220.0, 48000.0, kSmall);  // just above HP, at the shelf zero
        const double gHi = measureDb(8000.0, 48000.0, kSmall); // HF plateau
        const double lift = gHi - gLo;
        const double expectMax = 20.0 * std::log10(1.0 + JfetStage::kGmR6); // full shelf ratio
        // gLo is measured AT the zero corner (already part-way up), so the measured
        // lift is a fraction of the full ratio — just assert it's a real HF boost
        // in the right ballpark and below the analytic ceiling.
        const bool pass = lift > 4.0 && lift < expectMax + 0.1;
        std::printf("  220 Hz %+.2f dB, 8 kHz %+.2f dB -> lift %+.2f dB (ratio ceiling %+.2f)  %s\n",
                    gLo, gHi, lift, expectMax, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    // ---- Test 3: DC-step polarity (INVERTING; AC-coupled) ---------------------
    std::printf("\n=== Step response: INVERTING first sample; decays to ~0 (AC-coupled) ===\n");
    {
        JfetStage stage;
        stage.prepare(48000.0);
        const double vin = 1.0e-4; // small: stays in the linear region
        const double first = stage.process(vin);
        double y = first;
        for (int n = 1; n < 200000; ++n) // settle >> HP tau (1.1 ms)
            y = stage.process(vin);

        const bool invert = first < 0.0; // +in -> -out (common-source)
        const bool decay = std::abs(y) < 1e-6 * std::abs(vin) + 1e-9;
        const bool pass = invert && decay;
        std::printf("  +in=%.1e  first out %+.4e (INVERTING) settled %+.3e (->0)  %s\n",
                    vin, first, y, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    // ---- Test 4: nonlinearity — compression + asymmetry + monotonic -----------
    std::printf("\n=== Nonlinearity: mild asymmetric soft saturation ===\n");
    {
        // Hot 200 Hz tone (well above the input HP) driven hard into the shelf/gain
        // so the waveshaper compresses. Small-signal gain reference from the oracle.
        const double fs = 48000.0, freq = 200.0;
        const double gSmallDb = measureDb(freq, fs, kSmall);
        const double gSmall = std::pow(10.0, gSmallDb / 20.0);

        JfetStage stage;
        stage.prepare(fs);
        const double amp = 1.0; // hot: kG0*shelf*1V ~ tens of volts >> sat
        double peakPos = 0.0, peakNeg = 0.0;
        const int settle = static_cast<int>(0.1 * fs);
        for (int n = 0; n < settle + static_cast<int>(4.0 * fs / freq); ++n)
        {
            const double x = amp * std::sin(2.0 * PI * freq * n / fs);
            const double y = stage.process(x);
            if (n >= settle)
            {
                peakPos = std::max(peakPos, y);
                peakNeg = std::min(peakNeg, y);
            }
        }
        const double bigGainPos = peakPos / amp;
        const bool compresses = bigGainPos < 0.5 * gSmall; // heavy compression at 1 V drive
        const bool asymmetric = std::abs(peakPos - std::abs(peakNeg)) > 1e-3 * peakPos; // satPos!=satNeg
        // Bounded by the soft ceilings (inverting: +in-peak -> -out clips against
        // satPos, -in-peak -> +out clips against satNeg). Assert both output peaks
        // are inside [satNeg, satPos] + eps.
        const double ceil = std::max(JfetStage::kSatPos, JfetStage::kSatNeg) + 1e-6;
        const bool bounded = peakPos <= ceil && -peakNeg <= ceil;
        std::printf("  1 V drive: out peaks [%+.4f, %+.4f] V; small-sig gain %.1fx -> big %.2fx\n",
                    peakNeg, peakPos, gSmall, bigGainPos);
        std::printf("  compresses: %s | asymmetric (satPos!=satNeg): %s | bounded by sat: %s\n",
                    compresses ? "PASS" : "FAIL", asymmetric ? "PASS" : "FAIL",
                    bounded ? "PASS" : "FAIL");
        if (! (compresses && asymmetric && bounded))
            ++failures;

        // Static transfer must be monotonic (a valid waveshaper).
        JfetStage s2;
        s2.prepare(fs);
        // DC won't pass the HP; probe the memoryless waveshaper via the exposed
        // shape by feeding a slow ramp is unnecessary — instead verify monotonicity
        // of tanh directly through the stage at HF where the HP passes (use a
        // rising set of amplitudes and confirm the peak output is non-decreasing).
        double prevPeak = -1.0; bool mono = true;
        for (double a = 0.01; a <= 2.0; a *= 1.5)
        {
            JfetStage sm;
            sm.prepare(fs);
            double pk = 0.0;
            const int st = static_cast<int>(0.05 * fs);
            for (int n = 0; n < st + static_cast<int>(4.0 * fs / freq); ++n)
            {
                const double x = a * std::sin(2.0 * PI * freq * n / fs);
                const double y = sm.process(x);
                if (n >= st) pk = std::max(pk, y);
            }
            if (pk < prevPeak - 1e-9) mono = false;
            prevPeak = pk;
        }
        std::printf("  output peak monotonic in drive: %s\n", mono ? "PASS" : "FAIL");
        if (! mono)
            ++failures;
    }

    // ---- Test 5: small-signal limit matches -G0*shelf at 1 kHz ----------------
    std::printf("\n=== Small-signal 1 kHz gain matches the linear oracle ===\n");
    {
        const double meas = measureDb(1000.0, 48000.0, kSmall);
        const double ref = oracleDb(1000.0);
        const bool pass = std::abs(meas - ref) <= 0.02;
        std::printf("  1 kHz meas %+.4f dB  oracle %+.4f dB  %s\n",
                    meas, ref, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    std::printf("\n%s\n", failures == 0 ? "All tests passed." : "Some tests FAILED.");
    return (failures > 0) ? 1 : 0;
}
