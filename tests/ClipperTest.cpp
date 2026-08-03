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

    std::printf("\n%s\n", failures == 0 ? "All tests passed." : "Some tests FAILED.");
    return (failures > 0) ? 1 : 0;
}
