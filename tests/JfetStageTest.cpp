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
//   Test 4 — Nonlinearity: the SQUARE-LAW EVEN shaper (Phase-7 reshape, see
//            JfetStage.h waveshape()). g(w) = w + a*s^2*(1 - sech(w/s)) is
//            LINEAR + EVEN, so a driven tone must come out EVEN-DOMINANT:
//            H2 well above the noise, H3 at the numerical floor (the odd part is
//            purely linear -> ZERO intrinsic H3). Also: +/- output peaks differ
//            (the even bump lands on one polarity), and the static curve is
//            monotonic at the nominal params. This is the whole point of the
//            reshape — a tanh could not separate H2 from H3 (captured drive-min
//            is H2 -36 / H3 -59 dB), so THIS assert is the structural guard.
//   Test 5 — Small-signal limit: at tiny drive the waveshaper is ~identity, so the
//            1 kHz gain matches -G0*shelf (the mid/HF small-signal gain). Since
//            g(w) ~ g'(0)*w for small w, this IS the "slope at 0 == 1" assert:
//            any g'(0) != 1 would scale the measured gain off the oracle.
//
// NOTE: kG0, kGmR6, kSatPos (= knee s), kSatNeg (= even strength a) are NOMINAL
// placeholders (fit to captures at Phase 7). These tests validate the STRUCTURE —
// filter shape, polarity, and the qualitative even-dominant nonlinearity — all of
// which are invariant under a later amplitude refit; they do NOT assert an
// absolute "correct" gain or harmonic level.
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

// Harmonic magnitudes of a steady tone driven through the stage, via an
// exact-bin DFT: freq/fs is chosen so an INTEGER number of periods fills the
// window, so a rectangular window leaks nothing and a genuinely-absent harmonic
// reads at the numerical floor (~-150 dB) instead of a leakage-limited ~-60.
// magOut[k] = magnitude of harmonic (k+1); magOut[0] = the fundamental.
static void harmonics(double freq, double fs, double amp, int nHarm, double* magOut)
{
    JfetStage stage;
    stage.prepare(fs);

    const int perSamples = static_cast<int>(std::lround(fs / freq)); // exact by construction
    const int periods = 20;
    const int nWin = perSamples * periods;
    const int settle = static_cast<int>(0.2 * fs); // >> the 145 Hz input-HP tau (1.1 ms)

    for (int k = 0; k < nHarm; ++k)
        magOut[k] = 0.0;

    double re[16] = { 0.0 };
    double im[16] = { 0.0 };

    for (int n = 0; n < settle + nWin; ++n)
    {
        const double x = amp * std::sin(2.0 * PI * freq * static_cast<double>(n) / fs);
        const double y = stage.process(x);
        if (n < settle)
            continue;
        const int m = n - settle;
        for (int k = 0; k < nHarm; ++k)
        {
            const double w = 2.0 * PI * static_cast<double>((k + 1) * periods) * m / nWin;
            re[k] += y * std::cos(w);
            im[k] -= y * std::sin(w);
        }
    }
    for (int k = 0; k < nHarm; ++k)
        magOut[k] = 2.0 * std::hypot(re[k], im[k]) / nWin;
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

    // ---- Test 4: SQUARE-LAW even shaper — H2 >> H3, asymmetric, monotonic -----
    std::printf("\n=== Nonlinearity: square-law EVEN shaper (H2 dominant, H3 ~ absent) ===\n");
    {
        // 200 Hz (well above the 145 Hz input HP; 48000/200 = 240 samples/period
        // exactly, so the DFT bins line up). Amplitude picked so the waveshaper
        // input peak lands near the knee s: |H(200 Hz)| ~ 15.8x, so 0.2 V -> ~3.2 V
        // against s = 3.0 — the shaper is genuinely engaged, not a small-signal probe.
        const double fs = 48000.0, freq = 200.0, amp = 0.2;

        double mag[6] = { 0.0 };
        harmonics(freq, fs, amp, 6, mag);
        double hDb[6];
        for (int k = 0; k < 6; ++k)
            hDb[k] = 20.0 * std::log10(mag[k] / (mag[0] + 1e-300) + 1e-300);

        std::printf("  drive %.2f V: H2 %+.1f  H3 %+.1f  H4 %+.1f  H5 %+.1f dB re fundamental\n",
                    amp, hDb[1], hDb[2], hDb[3], hDb[4]);

        // (a) H2 must be a real, audible-scale even harmonic (the warmth this shape exists for).
        const bool h2Present = hDb[1] > -40.0;
        // (b) H3 must be ~absent: the odd part of g is PURELY LINEAR, so H3 comes only
        //     from arithmetic noise. The captured pedal separates them by ~23 dB at
        //     drive-min; the shape itself must do far better than that on its own.
        const bool evenDominant = (hDb[1] - hDb[2]) > 40.0;
        // (c) H4 (even) must likewise outrun H5 (odd).
        const bool h4OverH5 = (hDb[3] - hDb[4]) > 20.0;
        std::printf("  H2 present: %s | H2-H3 = %+.1f dB (even-dominant): %s | H4-H5 = %+.1f dB: %s\n",
                    h2Present ? "PASS" : "FAIL", hDb[1] - hDb[2], evenDominant ? "PASS" : "FAIL",
                    hDb[3] - hDb[4], h4OverH5 ? "PASS" : "FAIL");
        if (! (h2Present && evenDominant && h4OverH5))
            ++failures;

        // Asymmetry: the even bump a*s^2*(1-sech) is >= 0 on BOTH half-cycles, and the
        // stage inverts, so |negative output peak| > positive output peak.
        JfetStage stage;
        stage.prepare(fs);
        double peakPos = 0.0, peakNeg = 0.0;
        const int settle = static_cast<int>(0.2 * fs);
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
        const bool asymmetric = std::abs(peakPos - std::abs(peakNeg)) > 1e-3 * peakPos;
        std::printf("  out peaks [%+.4f, %+.4f] V -> asymmetric (even bump): %s\n",
                    peakNeg, peakPos, asymmetric ? "PASS" : "FAIL");
        if (! asymmetric)
            ++failures;

        // Monotonic static map at the nominal params. Inline replica of
        // JfetStage::waveshape() from the PUBLIC constants (same no-drift convention
        // as oracleDb above): g'(w) = 1 + a*s*sech(w/s)*tanh(w/s), and
        // max|sech*tanh| = 1/2 (at tanh^2 = 1/2), so monotonicity <=> |a|*s < 2.
        // (This said 2.598 until 2026-07-22 — that is 1/max(sech^2*tanh), the wrong
        // extremum. The assert below is numeric so it was never actually wrong, but the
        // stated bound was 30% too permissive; see JfetStage.h waveshape().)
        const double s = JfetStage::kSatPos, a = JfetStage::kSatNeg;
        bool mono = true;
        double worstSlope = 1.0;
        for (double w = -10.0 * s; w <= 10.0 * s; w += 0.01 * s)
        {
            const double t = std::tanh(w / s);
            const double slope = 1.0 + a * s * (1.0 / std::cosh(w / s)) * t;
            worstSlope = std::min(worstSlope, slope);
            if (slope <= 0.0)
                mono = false;
        }
        std::printf("  static map monotonic (min slope %.4f, |a|*s = %.2f < 2): %s\n",
                    worstSlope, std::abs(a) * s, mono ? "PASS" : "FAIL");
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
