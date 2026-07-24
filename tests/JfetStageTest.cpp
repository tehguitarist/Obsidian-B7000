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
//   Test 4 — Nonlinearity: the SQUARE-LAW EVEN core (Phase-7 reshape, see
//            JfetStage.h waveshape()). g(w) = T(w) + (a*s^2/2)*tanh^2(w/s) has an
//            odd part of exactly T, so with the CEILING DISABLED (T(w) = w) it is
//            LINEAR + EVEN and a driven tone must come out EVEN-DOMINANT: H2 well
//            above the noise, H3 at the numerical floor. Run with the ceiling off
//            ON PURPOSE — that is what isolates the core's zero-H3 property, which
//            is the structural guard the reshape exists for (a tanh could not
//            separate H2 from H3, and the capture's drive-min is H2 -36 / H3 -59).
//            Any H3 the shipped stage makes therefore comes from the ceiling, by
//            construction, and Test 6 is where that is measured.
//   Test 5 — Small-signal limit: at tiny drive the waveshaper is ~identity, so the
//            1 kHz gain matches -G0*shelf (the mid/HF small-signal gain). Since
//            g(w) ~ g'(0)*w for small w, this IS the "slope at 0 == 1" assert:
//            any g'(0) != 1 would scale the measured gain off the oracle.
//   Test 6 — The ASYMMETRIC DRAIN-CURRENT CEILING (added 2026-07-22). Asserts the
//            four things the ceiling has to be right about, by exercising the
//            SHIPPED map (waveshape/waveshapeAD are public for exactly this — a
//            replica of a piecewise map in a test only tests the replica):
//            (a) BOUNDED and asymmetric — g -> +(beta*cp^3+1.5*cp) + a*s^2/2 and the
//                mirror on the cutoff side, so a 100x hotter drive barely raises the
//                output. This is the whole point: before it, the J201 fed the CD4049
//                37.9 V at 0 dBFS. (Asymptote is c*L^3, NOT +-L — the session-15
//                rational core, see JfetStage.h coreLimit().)
//            (b) MONOTONE — no NEGATIVE slope anywhere. Note slope -> 0 in the far
//                tail is CORRECT (that is saturation/cutoff), so the assert is
//                slope >= 0, not > 0. The core is provably monotone for beta >= 0
//                (JfetStage.h), the bump has its own |a|*s < 2.598 bound; this is a
//                numeric scan of the summed real map per the standing verify rule.
//            (c) F' == g — the ADAA antiderivative, now piecewise, still integrates
//                the shipped shape. A wrong branch here is silent: it would only
//                show up as excess aliasing at low OS.
//            (d) DISABLING the ceiling (>= kCeilOff) reproduces the plain linear
//                core EXACTLY, so Test 4's isolation is real and an A/B against the
//                pre-ceiling model is available to the fitter.
//
// NOTE (2026-07-22 restructure): the stage now outputs the drain NORTON CURRENT
// (amps), not a voltage, and its output impedance is stamped into TrebleAttack —
// see JfetStage.h "THIS STAGE IS A CURRENT SOURCE". So every level below is in
// dB re 1 siemens, and the shaper's argument is the effective vgs (real gate
// volts), which is why Test 4's drive amplitude is much larger than it used to be.
//
// NOTE: kGm, kRo, kRq2, kSatPos (= knee s), kSatNeg (= even strength a), kCeilPos
// and kCeilNeg are NOMINAL placeholders (fit to captures at Phase 7). These tests
// validate the STRUCTURE —
// filter shape, polarity, and the qualitative even-dominant nonlinearity — all of
// which are invariant under a later amplitude refit; they do NOT assert an
// absolute "correct" gain or harmonic level.
// =============================================================================

#include "../src/dsp/JfetStage.h"

#include <algorithm>
#include <cmath>
#include <complex>
#include <cstdio>

static constexpr double PI = 3.14159265358979323846;

// Analytic small-signal oracle (siemens): I/Vin = -[gm/(1+gm*R6)] * div * HP * shelf.
static double oracleDb(double freq)
{
    const std::complex<double> s(0.0, 2.0 * PI * freq);
    const double tauHp = (JfetStage::kR4 + JfetStage::kR5) * JfetStage::kC2;
    const std::complex<double> hp = s * tauHp / (1.0 + s * tauHp);
    const double tauZ = JfetStage::kR6 * JfetStage::kC3;
    const double gmR6 = JfetStage::kGm * JfetStage::kR6;
    const double tauP = tauZ / (1.0 + gmR6);
    const std::complex<double> shelf = (1.0 + s * tauZ) / (1.0 + s * tauP);
    const double div = JfetStage::kR5 / (JfetStage::kR4 + JfetStage::kR5);
    const double mag = (JfetStage::kGm / (1.0 + gmR6)) * div * std::abs(hp * shelf);
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

// Set the nominal fit params but with the drain-current ceiling at an explicit
// value — kCeilOff (or above) disables it exactly, which is how Test 4 isolates
// the linear+even CORE from the ceiling's own (deliberate) odd content.
static void setCeiling(JfetStage& stage, double ceilPos, double ceilNeg)
{
    stage.setNonlinear(JfetStage::kGm, JfetStage::kRo, JfetStage::kRq2,
                       JfetStage::kSatPos, JfetStage::kSatNeg, ceilPos, ceilNeg);
}

// Worst slope of the SHIPPED static map over |w| <= wMax, by central difference.
// A saturating map's slope legitimately decays to 0 in the tail, so callers assert
// "never NEGATIVE" — with a tolerance for the difference quotient's own roundoff
// (F/g values ~O(1) differenced over 2e-6 floors the resolution near 1e-10).
static double minSlope(const JfetStage& stage, double wMax)
{
    const double h = 1.0e-6;
    double worst = 1.0e9;
    for (double w = -wMax; w <= wMax; w += 5.0e-4)
        worst = std::min(worst, (stage.waveshape(w + h) - stage.waveshape(w - h)) / (2.0 * h));
    return worst;
}

// Harmonic magnitudes of a steady tone driven through the stage, via an
// exact-bin DFT: freq/fs is chosen so an INTEGER number of periods fills the
// window, so a rectangular window leaks nothing and a genuinely-absent harmonic
// reads at the numerical floor (~-150 dB) instead of a leakage-limited ~-60.
// magOut[k] = magnitude of harmonic (k+1); magOut[0] = the fundamental.
static void harmonics(double freq, double fs, double amp, int nHarm, double* magOut,
                      double ceilPos = JfetStage::kCeilOff, double ceilNeg = JfetStage::kCeilOff)
{
    JfetStage stage;
    stage.prepare(fs);
    setCeiling(stage, ceilPos, ceilNeg);

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
        const double expectMax =
            20.0 * std::log10(1.0 + JfetStage::kGm * JfetStage::kR6); // full shelf ratio
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

    // ---- Test 4: square-law even CORE — H2 >> H3, asymmetric (ceiling OFF) ----
    std::printf("\n=== Nonlinearity: square-law EVEN core, ceiling DISABLED "
                "(H2 dominant, H3 ~ absent) ===\n");
    {
        // 200 Hz (well above the 145 Hz input HP; 48000/200 = 240 samples/period
        // exactly, so the DFT bins line up). Amplitude picked so the waveshaper input
        // peak lands near the knee s. The shaper now sees the effective vgs, which is
        // ATTENUATED from the input (gate divider 0.909, shelf ~1.30 at 200 Hz, then
        // /(1+gm*R6) = /3.277) -> vgs ~ 0.29 * amp, so 1.5 V -> ~0.44 V against
        // s = 0.3. Hence the much larger drive than the pre-restructure 0.2 V.
        // ** Ceiling DISABLED here (kCeilOff): the zero-H3 property belongs to the
        // linear+even CORE, and the ceiling adds odd content by construction (any
        // bounded map must — bounding is an odd-order operation). Testing the core in
        // isolation is what keeps this a structural guard rather than a fit-dependent
        // one; Test 6 asserts the ceiling's own behaviour. **
        const double fs = 48000.0, freq = 200.0, amp = 1.5;

        double mag[6] = { 0.0 };
        harmonics(freq, fs, amp, 6, mag, JfetStage::kCeilOff, JfetStage::kCeilOff);
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

        // Asymmetry: the even bump (a*s^2/2)*tanh^2 is >= 0 on BOTH half-cycles, and
        // the stage inverts, so |negative output peak| > positive output peak.
        JfetStage stage;
        stage.prepare(fs);
        setCeiling(stage, JfetStage::kCeilOff, JfetStage::kCeilOff);
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

        // Monotonic CORE (ceiling off), where the closed-form product bound applies:
        // g'(w) = 1 + a*s*tanh(w/s)*sech^2(w/s), and max|tanh*sech^2| = 2/(3*sqrt(3))
        // = 0.38490 (at tanh^2 = 1/3), so monotonicity <=> |a|*s < 3*sqrt(3)/2 = 2.598.
        // ** 2.598 is the RIGHT number for THIS bump and the WRONG one for the old
        // sech bump (whose bound was 2, from max|sech*tanh| = 1/2, corrected here on
        // 2026-07-22). Check which shape the header has before trusting either. The
        // assert itself is numeric on the SHIPPED map, so it cannot be fooled by a
        // stale constant in a comment. **
        const double s = JfetStage::kSatPos, a = JfetStage::kSatNeg;
        const double coreSlope = minSlope(stage, 10.0 * s);
        const bool mono = coreSlope > 0.0;
        std::printf("  core map monotonic (min slope %.4f, |a|*s = %.2f < 2.598): %s\n",
                    coreSlope, std::abs(a) * s, mono ? "PASS" : "FAIL");
        if (! mono)
            ++failures;
    }

    // ---- Test 5: small-signal limit matches -gm*shelf at 1 kHz ----------------
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

    // ---- Test 6: the asymmetric drain-current ceiling -------------------------
    std::printf("\n=== Drain-current ceiling: bounded, asymmetric, monotone, F' == g ===\n");
    {
        const double s = JfetStage::kSatPos, a = JfetStage::kSatNeg;
        const double cp = JfetStage::kCeilPos, cn = JfetStage::kCeilNeg;
        const double beta = JfetStage::kExpandBeta;
        // Asymptotes: the expansive-then-bounded core (session-15 branch B) saturates
        // to c*L^3 = beta*L^3 + 1.5*L per side (verified via sympy.limit — NOT +-L any
        // more; the rational shape's ceiling scale is 1.5*L at beta=0). The even bump
        // saturates at a*s^2/2 on BOTH sides (a DC offset — rectification), so the swing
        // is bounded by the two core asymptotes about that bump offset.
        const double bump = 0.5 * a * s * s;
        auto coreAsym = [beta](double L) { return beta * L * L * L + 1.5 * L; };
        const double gTop = coreAsym(cp) + bump, gBot = -coreAsym(cn) + bump;

        JfetStage stage;
        stage.prepare(48000.0);

        // (a) BOUNDED + asymmetric. ** The rational core approaches its asymptote c*L^3
        // as a POWER LAW: T(w) - c*L^3 ~ -L^3*(1.25 + 1.5*beta*L^2)/w^2 (approach from
        // BELOW for beta >= 0, so the map NEVER exceeds the asymptote), still measurably
        // short at moderate w. Scan far enough (2000*max) that the shortfall (~1e-7 at
        // the nominal params) is well under the tolerance, and assert the map never
        // EXCEEDS the asymptote (a hard bound) and gets within tolerance of it. **
        // max(cp,cn) not cp — a later fit may produce cn >> cp, and scanning only to a
        // cp-multiple would never reach negative saturation and fail for the wrong reason.
        const double wBound = 2000.0 * std::max(cp, cn);
        double lo = 1.0e9, hi = -1.0e9;
        for (double w = -wBound; w <= wBound; w += 2.0e-2)
        {
            lo = std::min(lo, stage.waveshape(w));
            hi = std::max(hi, stage.waveshape(w));
        }
        // Never exceeds the asymptote (the sigmoid is < L strictly, the bump <= its
        // asymptote), and converges to it within the power-law shortfall at wBound.
        const bool bounded = hi <= gTop + 1.0e-9 && lo >= gBot - 1.0e-9
                             && (gTop - hi) < 1.0e-4 && (lo - gBot) < 1.0e-4;
        // Asymmetric about the bump offset: the two ceilings must genuinely differ,
        // which is the "clips toward the rail one way, toward cutoff the other" claim.
        const bool asym = std::abs((hi - bump) - (bump - lo)) > 0.01 * cp;
        std::printf("  g in [%+.4f, %+.4f]  (expect [%+.4f, %+.4f]): %s | asymmetric: %s\n",
                    lo, hi, gBot, gTop, bounded ? "PASS" : "FAIL", asym ? "PASS" : "FAIL");
        if (! (bounded && asym))
            ++failures;

        // ... and it actually BITES: 100x more drive must not give 100x more output.
        // (Before the ceiling the J201 handed the CD4049 37.9 V at 0 dBFS/1 kHz, and
        // the DriveStage 546 V against a +-3.3 V TL072 rail.) Measured against what
        // the UNBOUNDED core would have done over the same span, so the assert scales
        // with the params instead of hardcoding a tolerance. ** Tolerance 5e-3, looser
        // than the old tanh ceiling's 1e-3: the rational core has a SOFTER knee (it
        // approaches its asymptote ~1/w^2, not exp), so g(2*cp) is not yet fully
        // saturated and (y2-y1) is a larger — but still ~0.1% of unbounded — fraction. **
        const double y1 = stage.waveshape(2.0 * cp), y2 = stage.waveshape(200.0 * cp);
        const double unbounded = 198.0 * cp; // the old g(w) -> w
        const bool saturates = (y2 - y1) < 5.0e-3 * unbounded;
        std::printf("  g(2*cp) %+.4f -> g(200*cp) %+.4f  (100x drive: %+.4f, vs %+.1f "
                    "unbounded = %.2f%%): %s\n",
                    y1, y2, y2 - y1, unbounded, 100.0 * (y2 - y1) / unbounded,
                    saturates ? "PASS" : "FAIL");
        if (! saturates)
            ++failures;

        // (b) MONOTONE at the shipped params. Slope -> 0 in the tail is CORRECT
        // (saturation), so assert never-NEGATIVE, with a tolerance for the difference
        // quotient's own roundoff. ** The rational core is PROVABLY monotone for any
        // beta >= 0 (T'(w) = L^3*(L^2 + w^2*(3*L^2*beta+2.5))/(...) has a strictly
        // positive numerator — a sum of two positive terms — for beta >= 0; see
        // JfetStage.h). So unlike the session-14 sigmoid there is NO s/a/L/beta coupling
        // for the CORE to track; the only fold-back risk is the even bump's own
        // |a|*s < 2.598, which is a SEPARATE closed bound. This numeric scan still runs
        // per the standing rule (verify, don't trust the derivation) and covers the sum
        // g' = T' + bump'. ** The bump slope decays exponentially, so beyond ~10*s only
        // T' > 0 remains. Scan a generous multiple of max(s,cp,cn) to cover the knee.
        const double wSat = 60.0 * std::max(s, std::max(cp, cn));
        const double worst = minSlope(stage, wSat);
        const bool mono = worst > -1.0e-9;
        std::printf("  min slope %+.3e over |w| <= %.0f (>= 0 == no fold-back; cn/s = %.2f): %s\n",
                    worst, wSat, cn / s, mono ? "PASS" : "FAIL");
        if (! mono)
            ++failures;

        // (c) F' == g for the piecewise antiderivative (ADAA correctness). The core's
        // antiderivative is now elementary for ANY beta,L (session-15), so this must be
        // exact everywhere, not just at a special value. The floor is the central
        // difference's own roundoff, ~eps*|F|/h, not h^2.
        double worstF = 0.0, atW = 0.0;
        const double h = 1.0e-6;
        for (double w = -20.0; w <= 20.0; w += 1.0e-3)
        {
            const double e = std::abs((stage.waveshapeAD(w + h) - stage.waveshapeAD(w - h)) / (2 * h)
                                      - stage.waveshape(w));
            if (e > worstF) { worstF = e; atW = w; }
        }
        const bool adOk = worstF < 1.0e-6;
        std::printf("  max|F'(w) - g(w)| = %.2e @ w = %+.2f (roundoff floor): %s\n",
                    worstF, atW, adOk ? "PASS" : "FAIL");
        if (! adOk)
            ++failures;

        // Finite everywhere, including absurd drive (the sqrt/tanh must not produce NaN).
        bool finite = true;
        for (const double w : { 1.0e3, 1.0e12, -1.0e12 })
            finite = finite && std::isfinite(stage.waveshape(w)) && std::isfinite(stage.waveshapeAD(w));
        std::printf("  finite at |w| up to 1e12: %s\n", finite ? "PASS" : "FAIL");
        if (! finite)
            ++failures;

        // ADAA must not break the core's zero-H3 property. This was verified by hand
        // for the pre-ceiling shape; the antiderivative is now PIECEWISE, which is
        // new, so gate it. Ceiling off (H3 belongs to the core), ADAA on, and the
        // frequency is high enough that du is large — the regime where the difference
        // quotient does real work rather than degenerating to the midpoint fallback.
        {
            const double fs = 48000.0, freq = 2400.0, amp = 1.5;
            JfetStage ad;
            ad.prepare(fs);
            setCeiling(ad, JfetStage::kCeilOff, JfetStage::kCeilOff);
            ad.setADAA(true);
            const int per = static_cast<int>(std::lround(fs / freq)), nWin = per * 20;
            const int settle = static_cast<int>(0.2 * fs);
            double re[3] = { 0.0 }, im[3] = { 0.0 };
            for (int n = 0; n < settle + nWin; ++n)
            {
                const double y = ad.process(amp * std::sin(2.0 * PI * freq * n / fs));
                if (n < settle) continue;
                for (int k = 0; k < 3; ++k)
                {
                    const double ang = 2.0 * PI * (k + 1) * 20.0 * (n - settle) / nWin;
                    re[k] += y * std::cos(ang);
                    im[k] -= y * std::sin(ang);
                }
            }
            double m[3];
            for (int k = 0; k < 3; ++k)
                m[k] = std::hypot(re[k], im[k]);
            const double h2 = 20.0 * std::log10(m[1] / m[0] + 1e-300);
            const double h3 = 20.0 * std::log10(m[2] / m[0] + 1e-300);
            const bool adaaEven = (h2 - h3) > 40.0;
            std::printf("  ADAA on, ceiling off: H2 %+.1f  H3 %+.1f dB -> still even-dominant: %s\n",
                        h2, h3, adaaEven ? "PASS" : "FAIL");
            if (! adaaEven)
                ++failures;
        }

        // (d) Disabling the ceiling reproduces the plain linear core EXACTLY, so
        // Test 4's isolation is real and the fitter can A/B the pre-ceiling model.
        JfetStage off;
        off.prepare(48000.0);
        setCeiling(off, JfetStage::kCeilOff, JfetStage::kCeilOff);
        double worstOff = 0.0;
        for (double w = -5.0; w <= 5.0; w += 1.0e-3)
        {
            const double th = std::tanh(w / s);
            worstOff = std::max(worstOff, std::abs(off.waveshape(w) - (w + bump * th * th)));
        }
        const bool offOk = worstOff < 1.0e-12;
        std::printf("  ceiling OFF == w + (a*s^2/2)*tanh^2(w/s), worst %.2e: %s\n",
                    worstOff, offOk ? "PASS" : "FAIL");
        if (! offOk)
            ++failures;
    }

    std::printf("\n%s\n", failures == 0 ? "All tests passed." : "Some tests FAILED.");
    return (failures > 0) ? 1 : 0;
}
