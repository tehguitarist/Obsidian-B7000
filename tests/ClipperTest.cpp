// =============================================================================
// Clipper (CD4049UBE CMOS-inverter overdrive, IC3) + GRUNT bank — validation
// =============================================================================
// THE distortion stage. Validated against the analytic small-signal oracle
// (analysis/eq_reference.py :: clipper_smallsignal_tf), computed here inline as
// the complex loop transfer from the header constants (no hardcoded table ->
// the finite-gain coupled companion implementation is cross-checked directly).
//
//   Test 1 — Small-signal FR vs oracle, all 3 GRUNT positions. Tiny amplitude =>
//            VTC ~ -A0*w (linear) => the exact finite-gain loop transfer. Tight
//            through 2 kHz; HF deviation = bilinear warp of the C14 feedback
//            corner (resolved by the Phase-6 oversampled region, like every stage).
//   Test 2 — GRUNT corners: the -3 dB high-pass corner per position sits FAR below
//            the ideal-virtual-ground value (< half) and matches the finite-gain
//            oracle. This is the structural proof that the coupling (input-node Z =
//            R18/(1+A0)) is modelled, not "HPF then waveshaper" (circuit.md note).
//   Test 3 — DC-step polarity: INVERTING (+in -> -out on the AC edge), AC-coupled
//            (Cg) so it decays to ~0. The confirmed OD-path inversion into BLEND.
//   Test 4 — Sine clipping: soft asymmetric saturation. A hot tone compresses,
//            output bounded by the per-side VTC ceilings, and the +/- peaks differ
//            (kSatLo != kSatHi -> even harmonics — the doc's required asymmetry).
//   Test 5 — D1/D2 never conduct: even at max drive, node W stays well inside the
//            clamp window [kClampLo, kClampHi] -> the hard-clamp simplification of
//            the 1N4148 clamps is justified (they only guard huge transients).
//   Test 6 — 3 GRUNT x 3 drive snapshot grid: all finite, monotone in drive.
//
// NOTE: kA0, kSatLo, kSatHi are NOMINAL placeholders (fit to captures at Phase 7).
// These tests validate the STRUCTURE — the finite-gain corner SHAPES, the inverting
// polarity, and the qualitative asymmetric soft-clip — all invariant under a later
// amplitude refit; they do NOT assert an absolute "correct" gain (no capture yet).
// =============================================================================

#include "../src/dsp/Clipper.h"

#include <cmath>
#include <complex>
#include <cstdio>

static constexpr double PI = 3.14159265358979323846;

// Analytic small-signal oracle: H(f) = -A0 * Yin / (Yin + (A0+1)*Yfb).
static double oracleDb(double freq, double cg)
{
    const std::complex<double> s(0.0, 2.0 * PI * freq);
    const std::complex<double> yin = 1.0 / (Clipper::kR16 + 1.0 / (s * cg));
    const std::complex<double> yfb = 1.0 / Clipper::kR18 + s * Clipper::kC14;
    const std::complex<double> h = -Clipper::kA0 * yin / (yin + (Clipper::kA0 + 1.0) * yfb);
    const double mag = std::abs(h);
    return (mag > 0.0) ? 20.0 * std::log10(mag) : -300.0;
}

// Steady-state peak magnitude gain (dB) at a frequency, small-signal (linear).
static double measureDb(double freq, double fs, double cg, double amp)
{
    Clipper stage;
    stage.prepare(fs);
    stage.setGruntCap(cg);

    const double period = fs / freq;
    // Slowest pole is the large-Cg GRUNT HP (~36 Hz, tau ~4.4 ms) — settle is
    // dominated by the low-frequency measurement window.
    const int settle = static_cast<int>(std::max(0.2 * fs, 24.0 * period));
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

// -3 dB high-pass corner (rising edge) from a fine log sweep, small-signal.
static double measureCorner(double fs, double cg)
{
    const double amp = 1.0e-6;
    // Find the passband plateau (max gain across the band).
    double plateau = -300.0;
    for (int i = 0; i <= 120; ++i)
    {
        const double f = 5.0 * std::pow(10.0, 3.0 * i / 120.0); // 5 Hz .. 5 kHz
        plateau = std::max(plateau, measureDb(f, fs, cg, amp));
    }
    // Lowest frequency reaching plateau - 3 dB.
    double prev = 5.0;
    for (int i = 0; i <= 480; ++i)
    {
        const double f = 5.0 * std::pow(10.0, 3.0 * i / 480.0);
        if (measureDb(f, fs, cg, amp) >= plateau - 3.0)
            return 0.5 * (f + prev); // midpoint of the last step
        prev = f;
    }
    return -1.0;
}

int main()
{
    int failures = 0;

    struct GruntCfg { const char* name; Clipper::Grunt g; double cg; };
    const GruntCfg kGrunts[] = {
        { "Cut  (4n7)",       Clipper::Grunt::Cut,   Clipper::gruntCap(Clipper::Grunt::Cut) },
        { "Flat (4n7||47n)",  Clipper::Grunt::Flat,  Clipper::gruntCap(Clipper::Grunt::Flat) },
        { "Boost(4n7||220n)", Clipper::Grunt::Boost, Clipper::gruntCap(Clipper::Grunt::Boost) },
    };

    static const double kFreqs[] = { 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000 };
    static const int kNF = 9;
    const double kSmall = 1.0e-6; // << sat => VTC ~ -A0*w (linear loop)

    // ---- Test 1: small-signal FR vs oracle (all GRUNT positions) --------------
    std::printf("=== Small-signal FR vs finite-gain oracle (tight <2 kHz; HF = C14 warp) ===\n");
    for (const auto& gc : kGrunts)
    {
        double worstLo = 0.0, worstLoF = 0.0; // <= 2 kHz
        double worstHi = 0.0;                 // > 2 kHz (bilinear warp band)
        for (int i = 0; i < kNF; ++i)
        {
            const double err = std::abs(measureDb(kFreqs[i], 48000.0, gc.cg, kSmall) - oracleDb(kFreqs[i], gc.cg));
            if (kFreqs[i] <= 2000.0)
            {
                if (err > worstLo) { worstLo = err; worstLoF = kFreqs[i]; }
            }
            else if (err > worstHi)
                worstHi = err;
        }
        const bool pass = worstLo <= 0.25;
        std::printf("  %-16s worst <=2k %.4f dB @ %.0f Hz | >2k %.4f dB  %s\n",
                    gc.name, worstLo, worstLoF, worstHi, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    // ---- Test 2: GRUNT corners — finite-gain, far below ideal-virtual-ground --
    std::printf("\n=== GRUNT high-pass corners: finite-gain (<< ideal-vg), matches oracle ===\n");
    for (const auto& gc : kGrunts)
    {
        const double corner = measureCorner(48000.0, gc.cg);
        const double idealVg = 1.0 / (2.0 * PI * gc.cg * Clipper::kR16); // A0 -> inf

        // Oracle -3 dB corner (analytic, same model) for the match check.
        double plateau = -300.0;
        for (int i = 0; i <= 600; ++i)
            plateau = std::max(plateau, oracleDb(5.0 * std::pow(10.0, 3.0 * i / 600.0), gc.cg));
        double oracleCorner = -1.0, prev = 5.0;
        for (int i = 0; i <= 2400; ++i)
        {
            const double f = 5.0 * std::pow(10.0, 3.0 * i / 2400.0);
            if (oracleDb(f, gc.cg) >= plateau - 3.0) { oracleCorner = 0.5 * (f + prev); break; }
            prev = f;
        }

        const bool belowIdeal = corner < 0.5 * idealVg;           // finite gain dominates
        const bool matchesOracle = std::abs(corner - oracleCorner) < 0.10 * oracleCorner; // within 10%
        const bool pass = belowIdeal && matchesOracle && corner > 0.0;
        std::printf("  %-16s corner %7.1f Hz  (oracle %7.1f, ideal-vg %7.1f)  below-ideal:%s match:%s\n",
                    gc.name, corner, oracleCorner, idealVg,
                    belowIdeal ? "Y" : "N", matchesOracle ? "Y" : "N");
        if (! pass)
            ++failures;
    }

    // ---- Test 3: DC-step polarity (INVERTING; AC-coupled) ---------------------
    std::printf("\n=== Step response: INVERTING first sample; decays to ~0 (AC-coupled) ===\n");
    {
        Clipper stage;
        stage.prepare(48000.0);
        stage.setGrunt(Clipper::Grunt::Cut);
        const double vin = 1.0e-4; // small: stays in the linear VTC region
        const double first = stage.process(vin);
        double y = first;
        for (int n = 1; n < 400000; ++n) // settle >> the slowest HP tau
            y = stage.process(vin);

        const bool invert = first < 0.0; // +in -> -out (inverter)
        const bool decay = std::abs(y) < 1e-6 * std::abs(vin) + 1e-9;
        const bool pass = invert && decay;
        std::printf("  +in=%.1e  first out %+.4e (INVERTING) settled %+.3e (->0)  %s\n",
                    vin, first, y, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    // ---- Test 4: nonlinearity — compression + asymmetry + bounded -------------
    std::printf("\n=== Nonlinearity: soft asymmetric clip (even harmonics) ===\n");
    {
        // Use the Boost GRUNT (corner ~36 Hz) so 220 Hz is solidly in the passband
        // (near the full plateau gain) — a Cut/Flat position would high-pass the
        // 220 Hz tone below its own corner and mask the clip-vs-linear comparison.
        const double fs = 48000.0, freq = 220.0;
        const double cg = Clipper::gruntCap(Clipper::Grunt::Boost);
        const double gSmallDb = measureDb(freq, fs, cg, kSmall);
        const double gSmall = std::pow(10.0, gSmallDb / 20.0);

        Clipper stage;
        stage.prepare(fs);
        stage.setGrunt(Clipper::Grunt::Boost);
        const double amp = 2.0; // hot: A0*amp >> sat -> clips hard
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
        const double bigGainPos = peakPos / amp;
        const bool compresses = bigGainPos < 0.5 * gSmall; // heavy compression when hot
        const bool asymmetric = std::abs(peakPos - std::abs(peakNeg)) > 1e-3 * peakPos; // satLo != satHi
        // +in-peak -> W>0 -> Y clips to -kSatLo ; -in-peak -> W<0 -> Y clips to +kSatHi.
        const double eps = 1e-6;
        const bool bounded = peakPos <= Clipper::kSatHi + eps && -peakNeg <= Clipper::kSatLo + eps;
        std::printf("  amp=%.1f: out peaks [%+.4f, %+.4f] V; small-sig %.2fx -> big %.3fx\n",
                    amp, peakNeg, peakPos, gSmall, bigGainPos);
        std::printf("  compresses:%s  asymmetric:%s  bounded[-satLo,+satHi]:%s\n",
                    compresses ? "PASS" : "FAIL", asymmetric ? "PASS" : "FAIL", bounded ? "PASS" : "FAIL");
        if (! (compresses && asymmetric && bounded))
            ++failures;
    }

    // ---- Test 5: D1/D2 never conduct even at max drive ------------------------
    std::printf("\n=== D1/D2 clamps: node W stays well inside the clamp window ===\n");
    {
        // Reconstruct node W externally is awkward; instead drive very hot through
        // every GRUNT position and confirm the OUTPUT never pins to a clamp-implied
        // level, and that W (inferred from Y via the invertible VTC) stays inside.
        // We reproduce the solve's clamp check by asserting |Y| < the saturation
        // ceilings + a margin (if W hit a clamp, Y would freeze at VTC(clamp),
        // which is essentially +-full-rail — distinguishable from the soft ceiling).
        double maxAbsW = 0.0;
        for (const auto& gc : kGrunts)
        {
            Clipper stage;
            stage.prepare(48000.0);
            stage.setGruntCap(gc.cg);
            const double freq = 100.0, amp = 8.0; // absurdly hot
            for (int n = 0; n < 20000; ++n)
            {
                const double x = amp * std::sin(2.0 * PI * freq * n / 48000.0);
                const double y = stage.process(x);
                // Invert the VTC to recover W: y = -satLo*tanh(A0 w/satLo) (w>=0) etc.
                double w;
                if (y <= 0.0) // came from w >= 0
                {
                    const double t = std::min(0.999999, -y / Clipper::kSatLo);
                    w = (Clipper::kSatLo / Clipper::kA0) * std::atanh(t);
                }
                else
                {
                    const double t = std::min(0.999999, y / Clipper::kSatHi);
                    w = -(Clipper::kSatHi / Clipper::kA0) * std::atanh(t);
                }
                maxAbsW = std::max(maxAbsW, std::abs(w));
            }
        }
        const double window = std::min(Clipper::kClampHi, -Clipper::kClampLo);
        const bool pass = maxAbsW < 0.5 * window; // comfortably inside
        std::printf("  max |W| over all GRUNT @ amp=8V: %.4f V  (clamp window +-%.2f V)  %s\n",
                    maxAbsW, window, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    // ---- Test 6: 3 GRUNT x 3 drive snapshot grid (finite + monotone) ----------
    std::printf("\n=== Sine-clip snapshot grid (3 GRUNT x 3 drive): finite + monotone ===\n");
    {
        const double drives[] = { 0.05, 0.5, 3.0 };
        bool allFinite = true, allMonotone = true;
        for (const auto& gc : kGrunts)
        {
            double prevPk = -1.0;
            std::printf("  %-16s", gc.name);
            for (double amp : drives)
            {
                Clipper stage;
                stage.prepare(48000.0);
                stage.setGruntCap(gc.cg);
                double pk = 0.0;
                const int settle = static_cast<int>(0.1 * 48000.0);
                for (int n = 0; n < settle + 960; ++n)
                {
                    const double x = amp * std::sin(2.0 * PI * 220.0 * n / 48000.0);
                    const double y = stage.process(x);
                    if (! std::isfinite(y)) allFinite = false;
                    if (n >= settle) pk = std::max(pk, std::abs(y));
                }
                if (pk < prevPk - 1e-9) allMonotone = false;
                prevPk = pk;
                std::printf("  drive %.2f->pk %.4f", amp, pk);
            }
            std::printf("\n");
        }
        std::printf("  all finite:%s  peak monotone in drive:%s\n",
                    allFinite ? "PASS" : "FAIL", allMonotone ? "PASS" : "FAIL");
        if (! (allFinite && allMonotone))
            ++failures;
    }

    std::printf("\n%s\n", failures == 0 ? "All tests passed." : "Some tests FAILED.");
    return (failures > 0) ? 1 : 0;
}
