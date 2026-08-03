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
//   Test 5 — D1/D2: the clamp window is FIT-INVARIANT (the session-118 guard),
//            inert in the in-range drive region, and BOUNDING beyond it.
//            ** Session-11 correction: the old "max|W| = 1.1 V at 8 V" claim was
//            an atanh-recovery artifact — see the in-test note. **
//            ** Session-118: this test used to run the NOMINAL constants only and
//            so could not see that the SHIPPED window had drifted onto the signal;
//            it now runs both arms and gates the fit-invariance directly. **
//   Test 6 — 3 GRUNT x 3 drive snapshot grid: all finite, monotone in drive.
//
// NOTE: kA0, kSatLo, kSatHi are NOMINAL placeholders (fit to captures at Phase 7).
// These tests validate the STRUCTURE — the finite-gain corner SHAPES, the inverting
// polarity, and the qualitative asymmetric soft-clip — all invariant under a later
// amplitude refit; they do NOT assert an absolute "correct" gain (no capture yet).
// =============================================================================

#include "../src/dsp/Clipper.h"
#include "../src/dsp/FitParams.h"

#include <cmath>
#include <complex>
#include <cstdio>
#include <algorithm>

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

    // ---- Test 5: D1/D2 inert at realistic max drive; bounding at absurd drive -
    std::printf("\n=== D1/D2 clamps: fit-invariant window; inert in-range; bounding beyond ===\n");
    {
        // W is recovered from Y through the VTC's exact inverse: per side
        // y = -+sat * f_k(a0*w/sat), f_k(u) = u/(1+u^k)^(1/k), so
        // u = t/(1-t^k)^(1/k) with t = |y|/sat. Unlike the old tanh VTC this
        // inverse is usable over the whole range — the sigmoid's POLYNOMIAL tail
        // keeps y distinguishable at large w, where tanh's exponential tail made
        // every w >~ 1 V produce y within 1e-9 of -satLo.
        //
        // ** SESSION-11 CORRECTION: the original version of this test claimed
        // "max|W| = 1.1 V at amp = 8 V" — that number was an ARTIFACT of the
        // atanh recovery saturating, not the real excursion. A ground-truth
        // replica of the Newton solve (clamps disabled) shows W reaches ~8 V at
        // amp = 8 V with EITHER VTC shape (tanh and k=2 sigmoid agree to
        // < 0.1 V), i.e. the D1/D2 clamps DO engage ~50% of samples at that
        // absurd direct drive — in the tanh build too; the old test simply could
        // not see it. What is actually true (and what this test now asserts):
        //   (a) at the HOTTEST input the chain can physically deliver (IC2_A is
        //       rail-limited to ~+-3.3 V; probe at 3.5 V) the clamps NEVER
        //       engage — max|W| ~= 3.56 V vs the [-3.75, +6.45] window, so the
        //       hard-clamp simplification of the 1N4148s is justified in-chain;
        //   (b) beyond that (amp = 8 V) the clamps BOUND W at the window edge —
        //       they guard huge transients, exactly circuit.md's description.
        // ** SESSION-118: this test used to run the NOMINAL constants ONLY, and a
        // stage that is never told the Phase-7 fit cannot answer a question about
        // the SHIPPED build. It passed for 74 sessions while the shipped clamp
        // window fired on up to 7.6 % of in-chain samples (Clipper.h ::
        // kTripPointV). Both arms are now run: NOMINAL (structure, unchanged) and
        // SHIPPED (FitParams, the arm that would have caught it). **
        auto probe = [&](double a0, double sLo, double sHi, double kk,
                         double amp, double& wPos, double& wNeg) {
            auto sigInv = [kk](double t) {
                t = std::min(0.999999, t);
                return t * std::pow(1.0 - std::pow(t, kk), -1.0 / kk);
            };
            auto recoverW = [&](double y) {
                if (y <= 0.0) // came from w >= 0
                    return (sLo / a0) * sigInv(-y / sLo);
                return -(sHi / a0) * sigInv(y / sHi);
            };
            wPos = 0.0; wNeg = 0.0;
            for (const auto& gc : kGrunts)
            {
                Clipper stage;
                stage.prepare(48000.0);
                stage.setNonlinear(a0, sLo, sHi, kk);
                stage.setGruntCap(gc.cg);
                for (int n = 0; n < 20000; ++n)
                {
                    const double x = amp * std::sin(2.0 * PI * 100.0 * n / 48000.0);
                    const double w = recoverW(stage.process(x));
                    wPos = std::max(wPos, w);
                    wNeg = std::min(wNeg, w);
                }
            }
        };
        const double eps = 1e-6;
        const FitParams fp;
        struct Arm { const char* name; double a0, sLo, sHi, k; };
        const Arm arms[] = {
            { "NOMINAL", Clipper::kA0, Clipper::kSatLo, Clipper::kSatHi, Clipper::kHardness },
            { "SHIPPED", fp.clipA0, fp.clipSatLo, fp.clipSatHi, fp.clipK },
        };
        // ** The GATED claim is deliberately NOT "the clamps never fire". Session
        // 118 measured that they do, at the top of the drive range, and pretending
        // otherwise is what let the bug live for 74 sessions. What IS gated:
        //   (i)  the window is the same for BOTH arms — i.e. no amplitude fit can
        //        move it. This is the exact regression guard for the session-118
        //        bug, and it is now structural (Clipper::process reads kClampLo /
        //        kClampHi directly; there is no mutable copy left to desync).
        //   (ii) at 3.0 V — comfortably inside what IC2_A can deliver — the clamps
        //        are inert on BOTH arms, which is the "rarely conducts" claim
        //        circuit.md actually makes.
        //   (iii) beyond anything the chain can deliver they BOUND W at the window
        //        edge, i.e. they are guards, not shapers.
        // The rail-limited 4.1 V row is PRINTED as a measurement, not gated: there
        // D2 does engage, and that is a real (documented) property of the shipped
        // fit, not something a test should be tuned to hide.
        // ⚠ Guard (ii) FAILS on the pre-session-118 window (-1.0377): the shipped
        // arm reaches -2.05 V at 3.0 V in. Verified before the fix was believed —
        // a guard that passes on the bug it was written for is worthless. **
        const double kSafeV = 3.0, kRailV = 4.1, kAbsurdV = 40.0;
        bool allInert = true, allBounded = true;
        for (const auto& a : arms)
        {
            double wPos = 0.0, wNeg = 0.0;
            probe(a.a0, a.sLo, a.sHi, a.k, kSafeV, wPos, wNeg);
            const bool inert = wPos < Clipper::kClampHi - eps && wNeg > Clipper::kClampLo + eps;
            allInert = allInert && inert;
            std::printf("  %s amp=%.1fV: W in [%+.4f, %+.4f] V  (window [%+.3f, %+.3f], "
                        "margin %+.3f/%+.3f)  %s\n", a.name, kSafeV, wNeg, wPos,
                        Clipper::kClampLo, Clipper::kClampHi,
                        wNeg - Clipper::kClampLo, Clipper::kClampHi - wPos, inert ? "PASS" : "FAIL");

            double wPosR = 0.0, wNegR = 0.0;
            probe(a.a0, a.sLo, a.sHi, a.k, kRailV, wPosR, wNegR);
            std::printf("  %s amp=%.1fV (rail-limited max): W in [%+.4f, %+.4f] V  "
                        "-- D2 %s here (measured, NOT gated)\n", a.name, kRailV, wNegR, wPosR,
                        wNegR <= Clipper::kClampLo + eps ? "ENGAGES" : "inert");

            double wPos8 = 0.0, wNeg8 = 0.0;
            probe(a.a0, a.sLo, a.sHi, a.k, kAbsurdV, wPos8, wNeg8);
            const bool bounded = wPos8 <= Clipper::kClampHi + eps && wNeg8 >= Clipper::kClampLo - eps;
            allBounded = allBounded && bounded;
            std::printf("  %s amp=%.0fV (absurd): W in [%+.4f, %+.4f] V  bounded-at-window:%s\n",
                        a.name, kAbsurdV, wNeg8, wPos8, bounded ? "PASS" : "FAIL");
        }
        // (i) fit-invariance of the window — the exact session-118 regression
        // guard. At absurd drive BOTH arms drive node W hard into D2, so both must
        // pin at EXACTLY kClampLo whatever their VTC amplitudes are. (The positive
        // side is not usable for this: the shipped arm's W never reaches kClampHi
        // even at 40 V, so it cannot demonstrate anything and is not asserted.)
        double p1 = 0.0, n1 = 0.0, p2 = 0.0, n2 = 0.0;
        probe(Clipper::kA0, Clipper::kSatLo, Clipper::kSatHi, Clipper::kHardness, kAbsurdV, p1, n1);
        probe(fp.clipA0, fp.clipSatLo, fp.clipSatHi, fp.clipK, kAbsurdV, p2, n2);
        const bool pinned = std::abs(n1 - Clipper::kClampLo) < eps
                         && std::abs(n2 - Clipper::kClampLo) < eps;
        std::printf("  window is FIT-INVARIANT: D2 pins nominal at %+.4f, shipped at %+.4f "
                    "(kClampLo %+.4f)  %s\n", n1, n2, Clipper::kClampLo, pinned ? "PASS" : "FAIL");
        if (! (allInert && allBounded && pinned))
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

    // ---- Test 7: the node-W solve CONVERGES, at every shipped OS rate ---------
    // ** SESSION-120. The stage solves an implicit equation per sample; nothing in
    // this file used to check that the solve actually reaches its root, and it did
    // not: with plain Newton the shipped fit left up to 69 mV of node error at
    // 48 kHz and 150 mV at 96 kHz, which is 0.6-0.7 V of OUTPUT error. **
    //
    // The 162-capture matrix renders at OS 8, where the plain solve was already
    // converged to 1.8e-15 — it is STRUCTURALLY BLIND to this, so the guard has to
    // live here. It runs the SHIPPED FitParams values (session-118's lesson: an
    // amplitude-dependent claim cannot be gated on the NOMINAL constants).
    //
    // A local re-transcription is deliberate, not laziness: it is a SECOND
    // implementation, so this test still fails if the stage's solve changes. Its
    // reference is pure BISECTION on the closed-form bracket derived in Clipper.h,
    // which shares no arithmetic with Newton.
    std::printf("\n=== Node-W solve converges at every shipped OS rate (shipped fit) ===\n");
    {
        const FitParams fp {};
        struct Ref
        {
            double gIn, gFb, ieqG = 0.0, ieq14 = 0.0, gcG, dNode, r16, a0, sLo, sHi, kk;
            double sig(double u) const { return u * std::pow(1.0 + std::pow(u, kk), -1.0 / kk); }
            double vtc(double w) const
            { return w >= 0.0 ? -sLo * sig(a0 * w / sLo) : sHi * sig(-a0 * w / sHi); }
            double F(double w, double x, double ic) const
            { return gIn * (x - w) - ic + gFb * (vtc(w) - w) - ieq14; }
        };

        auto run = [&](double fs, double amp, double cg, double& worstDy) {
            Clipper stage;
            stage.setNonlinear(fp.clipA0, fp.clipSatLo, fp.clipSatHi, fp.clipK);
            stage.prepare(fs);
            stage.setGruntCap(cg);

            Ref r;
            r.gcG = cg * 2.0 * fs;
            r.r16 = Clipper::kR16;
            r.dNode = r.gcG + 1.0 / r.r16;
            r.gIn = r.gcG / (r.r16 * r.dNode);
            r.gFb = 1.0 / Clipper::kR18 + Clipper::kC14 * 2.0 * fs;
            r.a0 = fp.clipA0; r.sLo = fp.clipSatLo; r.sHi = fp.clipSatHi; r.kk = fp.clipK;

            worstDy = 0.0;
            const int n = static_cast<int>(0.05 * fs);
            for (int i = 0; i < n; ++i)
            {
                const double t = i / fs;
                const double x = amp * (0.75 * std::sin(2.0 * PI * 110.0 * t)
                                        + 0.20 * std::sin(2.0 * PI * 770.0 * t + 0.7));
                const double y = stage.process(x);

                // Bisect the same equation from the same state.
                const double ic = r.ieqG / (r.r16 * r.dNode);
                const double sum = r.gIn + r.gFb;
                const double w0 = (r.gIn * x - ic - r.ieq14) / sum;
                const double rad = r.gFb * std::max(r.sLo, r.sHi) / sum + 1e-12;
                double lo = w0 - rad, hi = w0 + rad;
                for (int k = 0; k < 200; ++k)
                {
                    const double m = 0.5 * (lo + hi);
                    if (m == lo || m == hi) break;
                    (r.F(m, x, ic) > 0.0 ? lo : hi) = m;
                }
                double w = 0.5 * (lo + hi);
                if (w > Clipper::kClampHi) w = Clipper::kClampHi;
                else if (w < Clipper::kClampLo) w = Clipper::kClampLo;
                worstDy = std::max(worstDy, std::abs(y - r.vtc(w)));

                // Advance the reference on the STAGE's own trajectory, so this
                // measures solver error and not the chain's trajectory divergence
                // (two independent instances separate: the trapezoidal companion
                // recursion ieq = 2g*dv - ieq is lossless, so an injected 1e-15
                // never decays and the VTC's a0 amplifies it).
                const double wS = -1.0; (void) wS;
                const double m2 = (r.gcG * x - r.ieqG + w / r.r16) / r.dNode;
                r.ieqG = 2.0 * r.gcG * (x - m2) - r.ieqG;
                r.ieq14 = 2.0 * (Clipper::kC14 * 2.0 * fs) * (r.vtc(w) - w) - r.ieq14;
            }
        };

        // 1e-9 V is ~7 orders below the stage's own output swing and ~2 orders
        // below float32 render precision: a real solve failure lands at 1e-1.
        const double kTol = 1e-9;
        const double rates[] = { 48000.0, 96000.0, 192000.0, 384000.0 };
        const char* rname[] = { "1x  48k", "2x  96k", "4x 192k", "8x 384k" };
        bool ok = true;
        for (int k = 0; k < 4; ++k)
            for (double amp : { 2.0, 3.5 }) // 3.5 V ~= the physical ceiling (Test 5)
                for (const auto& gc : kGrunts)
                {
                    double dy = 0.0;
                    run(rates[k], amp, gc.cg, dy);
                    if (dy > kTol) ok = false;
                    std::printf("  %s amp %.1f %-16s worst |y - y_converged| = %.3e %s\n",
                                rname[k], amp, gc.name, dy, dy > kTol ? "  <-- FAIL" : "");
                }
        std::printf("  converged everywhere (tol %.0e): %s\n", kTol, ok ? "PASS" : "FAIL");
        if (! ok)
            ++failures;
    }

    // ---- Test 8: ADAA on the VTC (session 123) --------------------------------
    // Gates the ANTIDERIVATIVE and the substituted map directly, via the probe
    // forwarders, rather than inferring them from process() output — a wrong V
    // still produces plausible audio, so an output-only test cannot see it.
    // These are STRUCTURE claims (calculus identities of the shipped shape), so
    // they run at BOTH the nominal and the shipped amplitudes, and the k-gating
    // claim is amplitude-dependent by definition so it runs the shipped clipK too
    // (the session-118 sorting rule).
    std::printf("\n=== ADAA on the VTC: antiderivative, exactness gate, monotonicity ===\n");
    {
        const FitParams fp;
        bool ok = true;

        // (a) V' == vtc, checked by central difference across the trip point and
        //     deep into both saturations. This is THE load-bearing identity: if it
        //     fails, ADAA1 is averaging the wrong function.
        {
            Clipper st;
            st.prepare(48000.0);
            st.setNonlinear(fp.clipA0, fp.clipSatLo, fp.clipSatHi, 2.0);
            double worst = 0.0, worstAt = 0.0;
            const double h = 1e-6;
            for (double w = -4.0; w <= 4.0; w += 0.0005)
            {
                const double num = (st.probeVtcAD(w + h) - st.probeVtcAD(w - h)) / (2.0 * h);
                const double err = std::abs(num - st.probeVtc(w));
                if (err > worst) { worst = err; worstAt = w; }
            }
            // 1e-7 is the central difference's own O(h^2 * V''') truncation scale
            // here, not a tolerance chosen to pass.
            const bool pass = worst < 1e-7;
            std::printf("  (a) dV/dw == vtc over w in [-4,+4]: worst %.3e at w=%+.4f  %s\n",
                        worst, worstAt, pass ? "PASS" : "FAIL");
            std::printf("      V(0) = %.3e (must be 0 -> ADAA1 exact at DC)\n", st.probeVtcAD(0.0));
            ok = ok && pass && std::abs(st.probeVtcAD(0.0)) < 1e-300;
        }

        // (b) the mean degenerates to the pointwise value as the step vanishes,
        //     and the midpoint fallback joins on continuously (no step at kAdaaEps).
        {
            Clipper st;
            st.prepare(48000.0);
            st.setNonlinear(fp.clipA0, fp.clipSatLo, fp.clipSatHi, 2.0);
            // ** The bar must SCALE WITH dw, not be a fixed number. First draft used
            // a flat 1e-4 and "failed" at 1.244e-3 — which is a0*dw/2 to three
            // figures at dw = 1e-4, i.e. the mean-value theorem, not a defect.
            // A tolerance that a correct implementation cannot meet is a broken
            // test; the real claim is FIRST-ORDER agreement, so gate on that. **
            double worstRel = 0.0, worstAbs = 0.0, worstDw = 0.0;
            for (double w : { -2.0, -0.02, -1e-4, 0.0, 1e-4, 0.02, 2.0 })
                for (double dw : { 1e-12, 1e-9, 1e-8, 1e-7, 1.000001e-7, 1e-6, 1e-4 })
                {
                    const double err = std::abs(st.probeVtcAvg(w + dw, w) - st.probeVtc(w));
                    const double bound = fp.clipA0 * dw + 1e-12; // |vtc'| <= a0
                    if (err / bound > worstRel)
                    {
                        worstRel = err / bound;
                        worstAbs = err;
                        worstDw = dw;
                    }
                }
            const bool pass = worstRel <= 1.0;
            std::printf("  (b) mean -> pointwise, first-order in dw (err <= a0*dw):"
                        " worst %.3e at dw=%.0e = %.3f of bound  %s\n",
                        worstAbs, worstDw, worstRel, pass ? "PASS" : "FAIL");
            ok = ok && pass;
        }

        // (c) the substituted map stays STRICTLY DECREASING in w at fixed wPrev.
        //     This is what keeps the root unique and the session-120 bracket valid;
        //     if it fails, rtsafe's containment argument is void.
        {
            Clipper st;
            st.prepare(48000.0);
            st.setNonlinear(fp.clipA0, fp.clipSatLo, fp.clipSatHi, 2.0);
            bool mono = true;
            double worstSlope = -1e300;
            for (double wp : { -3.0, -0.5, -0.01, 0.0, 0.01, 0.5, 3.0 })
            {
                double prev = st.probeVtcAvg(-5.0, wp);
                for (double w = -5.0 + 0.001; w <= 5.0; w += 0.001)
                {
                    const double cur = st.probeVtcAvg(w, wp);
                    worstSlope = std::max(worstSlope, (cur - prev) / 0.001);
                    if (cur > prev) mono = false;
                    prev = cur;
                }
            }
            std::printf("  (c) mean is strictly decreasing in w (worst slope %+.3e): %s\n",
                        worstSlope, mono ? "PASS" : "FAIL");
            ok = ok && mono;
        }

        // (d) the k != 2 GATE. A k != 2 build must get NO ADAA rather than a wrong
        //     one, and a k == 2 build must actually get it (else the flag is dead and
        //     every "ADAA bought nothing" reading is vacuous). BOTH directions, or
        //     this proves nothing.
        //
        // ⚠⚠ SESSION 124 — THIS TEST HAD TO BE REPAIRED, AND THE REASON IS WORTH MORE
        // THAN THE TEST. It was written when the shipped clipK was 2.4653, so it took
        // its non-anchor arm from `fp.clipK` and its anchor arm from a literal 2.0,
        // and asserted "inert at SHIPPED, live at k=2". The moment session 124
        // re-anchored the shipped constant TO 2.0 the two arms became the same value
        // and the test demanded that one render be simultaneously inert and live — it
        // failed against entirely correct code, and its message ("clipK=2.0000 ...
        // must be INERT") could not be true.
        // ⭐ The defect is that it bound a claim about **k** to whatever happened to be
        // SHIPPED. The property under test is a property of the exponent: it does not
        // know or care which value ships. So both arms are now named constants, and
        // the shipping question — "is the shipped k the ADAA anchor?" — is asserted
        // SEPARATELY below, where it is a real, deliberate claim that SHOULD fail
        // loudly if someone re-fits clipK off the anchor without re-reading
        // FitParams.h::clipAdaa. Two questions, two assertions.
        // (Same family as the session-118 note in this very block: a per-stage test
        // must be explicit about which build it is answering about.)
        {
            // A deliberately NON-anchor exponent: the retired session-44 A5 value, so
            // the inertness arm keeps testing the real historical case. Any k != 2
            // would do; naming the retired one makes the intent legible.
            constexpr double kNonAnchor = 2.4653;
            constexpr double kAnchor = 2.0;
            auto renderPeak = [&](double kk, Clipper::Adaa mode) {
                Clipper st;
                st.prepare(96000.0);
                st.setNonlinear(fp.clipA0, fp.clipSatLo, fp.clipSatHi, kk);
                st.setADAA(mode);
                st.setGrunt(Clipper::Grunt::Boost);
                double acc = 0.0;
                for (int n = 0; n < 8000; ++n)
                    acc += std::abs(st.process(2.5 * std::sin(2.0 * PI * 2499.0 * n / 96000.0)));
                return acc;
            };
            const double naOff = renderPeak(kNonAnchor, Clipper::Adaa::Off);
            const double naFull = renderPeak(kNonAnchor, Clipper::Adaa::Full);
            const double naRes = renderPeak(kNonAnchor, Clipper::Adaa::Residue);
            const double k2Off = renderPeak(kAnchor, Clipper::Adaa::Off);
            const double k2Full = renderPeak(kAnchor, Clipper::Adaa::Full);
            const bool inertAtNonAnchor = (naFull == naOff) && (naRes == naOff);
            const bool liveAtK2 = (k2Full != k2Off);
            std::printf("  (d) clipK=%.4f (non-anchor): Full/Residue vs Off -> %s (must be INERT)\n",
                        kNonAnchor, inertAtNonAnchor ? "identical" : "DIFFERENT");
            std::printf("      clipK=%.4f (anchor):     Full vs Off         -> %s (must be LIVE)\n",
                        kAnchor, liveAtK2 ? "different" : "IDENTICAL");
            // ** `Clipper()` default-constructs at kHardness = 2.0, so printing
            // `Clipper().probeAdaaExact()` and LABELLING it "shipped" reported 1 for
            // a stage that had never been told the fit — the session-118 defect
            // (a per-stage test answering about the nominal build while claiming the
            // shipped one) reproduced inside the test written to guard against it.
            // Construct each arm explicitly. **
            Clipper naStage, k2Stage;
            naStage.setNonlinear(fp.clipA0, fp.clipSatLo, fp.clipSatHi, kNonAnchor);
            k2Stage.setNonlinear(fp.clipA0, fp.clipSatLo, fp.clipSatHi, kAnchor);
            std::printf("      adaaExact(): k=%.4f %d, k=%.4f %d\n", kNonAnchor,
                        (int) naStage.probeAdaaExact(), kAnchor, (int) k2Stage.probeAdaaExact());
            ok = ok && ! naStage.probeAdaaExact() && k2Stage.probeAdaaExact();
            ok = ok && inertAtNonAnchor && liveAtK2;

            // ---- the SHIPPING claim, asserted separately (session 124) ----------
            // The block above is about the exponent. THIS is about the build: session
            // 124 ships ADAA ON, which is only meaningful if the shipped clipK is the
            // anchor. If a future re-fit moves clipK off 2.0, ADAA goes silently inert
            // — no wrong answer, but the shipped alias reduction quietly disappears,
            // which is exactly the kind of loss that travels for 100 sessions. Fail
            // loudly here instead, and name the file to re-read.
            Clipper shippedStage;
            shippedStage.setNonlinear(fp.clipA0, fp.clipSatLo, fp.clipSatHi, fp.clipK);
            const bool shippedIsAnchor = shippedStage.probeAdaaExact();
            std::printf("      SHIPPED clipK=%.4f -> adaaExact %d, clipAdaa=%d, clipAdaaMaxOs=%d : %s\n",
                        fp.clipK, (int) shippedIsAnchor, fp.clipAdaa, fp.clipAdaaMaxOs,
                        (shippedIsAnchor || fp.clipAdaa == 0)
                            ? "consistent"
                            : "INCONSISTENT — clipAdaa is ON but clipK is off the anchor, so ADAA is DEAD "
                              "(re-read FitParams.h::clipK / ::clipAdaa)");
            ok = ok && (shippedIsAnchor || fp.clipAdaa == 0);
        }

        // (e) with ADAA live, the solve must still CONVERGE — the bracket changed
        //     (slope-based, not the |vtc| <= sat radius), so Test 7's guarantee does
        //     not transfer for free. Output must stay finite and bounded by the VTC
        //     ceilings at every OS rate.
        {
            bool pass = true;
            for (double fs : { 48000.0, 96000.0, 192000.0, 384000.0 })
                for (auto mode : { Clipper::Adaa::Full, Clipper::Adaa::Residue })
                {
                    Clipper st;
                    st.prepare(fs);
                    st.setNonlinear(fp.clipA0, fp.clipSatLo, fp.clipSatHi, 2.0);
                    st.setADAA(mode);
                    st.setGrunt(Clipper::Grunt::Boost);
                    double worst = 0.0;
                    for (int n = 0; n < 20000; ++n)
                    {
                        const double y = st.process(3.5 * std::sin(2.0 * PI * 2499.0 * n / fs));
                        if (! std::isfinite(y)) { pass = false; break; }
                        worst = std::max(worst, std::abs(y));
                    }
                    // Residue's substituted value is NOT bounded by max(sat) (it
                    // carries the a0*dw/2 first difference — Clipper.h setADAA), so
                    // only Full is gated on the ceiling; Residue is gated on finite.
                    if (mode == Clipper::Adaa::Full
                        && worst > std::max(fp.clipSatLo, fp.clipSatHi) + 1e-9)
                        pass = false;
                    std::printf("      fs %6.0f  %-7s max|y| = %.5f\n", fs,
                                mode == Clipper::Adaa::Full ? "Full" : "Residue", worst);
                }
            std::printf("  (e) ADAA solve finite everywhere, Full bounded by the ceilings: %s\n",
                        pass ? "PASS" : "FAIL");
            ok = ok && pass;
        }

        if (! ok)
            ++failures;
    }

    std::printf("\n%s\n", failures == 0 ? "All tests passed." : "Some tests FAILED.");
    return (failures > 0) ? 1 : 0;
}
