// OSValidationTest — Phase-6 gate for the oversampling + clean-tap delay work.
//
// Two independent checks on the assembled PedalDSP (per-channel chain + JUCE
// oversampler + clean-tap DelayLine):
//
//   1. DELAY-COMP consistency (dsp.md "Dry/wet phase alignment"). At BLEND=50%
//      the clean tap and the OD path SUM. Because the clean tap is delay-
//      compensated to the oversampler's FIR latency, the audible-band magnitude
//      response must be (nearly) OS-FACTOR-INDEPENDENT — the OS factor only
//      touches HF aliasing, never the clean/OD balance. If the delay line were
//      missing or stale, the clean+OD comb pattern would SHIFT with factor and
//      these magnitudes would diverge (dsp.md's stated failure signature). We
//      assert cross-factor agreement at several audible frequencies.
//
//   2. ALIASING reduction. Drive a single high tone hard through the OD path
//      (BLEND=100% OD) and measure inharmonic (alias) energy via FFT. More
//      oversampling ⇒ less aliasing, so the alias floor at 8× must sit clearly
//      below 2×. Absolute levels are calibration-dependent (nominal params,
//      rails off) so we gate on the RELATIVE reduction + print the numbers,
//      per build.md's "finite/relative probes, don't gate on absolute" rule.
//
//      ⚠⚠ THE MEASUREMENT WAS REBUILT IN SESSION 92 (2026-07-31). Read this
//      before comparing any number below with a pre-session-92 record: the
//      figures moved because the INSTRUMENT changed, and two of the three
//      things it used to report were artefacts of the instrument, not of the
//      chain. Full derivation + known-answer gates: `analysis/alias_gate.py`
//      (`--selftest` proves each claim below against a signal whose alias
//      content is known by construction).
//
//        (a) f0 was 2500 Hz against a 2.9297 Hz bin — 853.33 bins, i.e. OFF
//            GRID. Every harmonic whose order is not a multiple of 3 then sat a
//            third of a bin off-centre and its Hann skirt escaped the ±3-bin
//            "signal" mask, so the metric had a −40.5 dB LEAKAGE PEDESTAL. That
//            is the exact value the old table printed as a "floor" at low
//            drive; the true floor there is −86 dB. f0 is now bin-exact
//            (kBin·fs/N), so the stimulus is periodic in exactly N samples, the
//            window is RECTANGULAR, and leakage is zero by construction — no
//            mask width is needed and none is used.
//        (b) 0.3 s of settling is not settled. MasterOut is two ~0.72 Hz
//            high-passes (τ = 0.22 s) and an asymmetric clipper steps them, so
//            the window still held a decaying DC ramp — energy at bins 1..50,
//            which `round(f/f0) == 0` classified as alias. The settle is now
//            4 s (18 τ) and the sub-200 Hz bucket is reported separately
//            instead of being summed into "alias".
//        (c) what is left IS real aliasing, and it is now attributed exactly:
//            the dominant inharmonic bins land on |n·f0 − m·(factor·fs)| for a
//            handful of consecutive harmonic orders near the OS rate (H152–156
//            at 8×), matching the arithmetic TO THE BIN at three different f0.
//            A 192 kHz-base reference (1.536 MHz internal) reads −65.9 dB where
//            48 kHz/8× reads −17.1, so it is fold-down, not circuit behaviour.
//            Rails are not the carrier (railEnabled=0 moves it 1.5 dB) and the
//            J201 already carries closed-form ADAA — the un-ADAA'd CD4049 VTC
//            is what generates the far ladder (FitParams.h clipSat notes).
//
//      ⚠ The gate below therefore still FAILS at amp 0.35, and that failure is
//      now known to be a REAL DEFECT rather than a measurement artefact. It is
//      strongly f0-dependent: at 8× the alias floor is −85…−115 dB for
//      fundamentals under 1.5 kHz (i.e. everywhere a bass guitar's fundamental
//      lives) and collapses to −17…−26 dB above ~2.3 kHz. Do not "fix" it by
//      moving the probe amplitude — the full amp × order sweep is printed
//      unconditionally so the bad zone stays visible instead of hiding behind a
//      green test. Owned by Phase 10 B (perf/HQ pass).
//
// This is the risky new code (delay bookkeeping + block-based OS around a
// per-sample WDF chain); the per-stage oracles don't cover it.

#include "../src/dsp/PedalDSP.h"

#include <cmath>
#include <cstdio>
#include <vector>

static int failures = 0;
static void check(bool cond, const char* msg)
{
    if (!cond) { std::printf("  FAIL: %s\n", msg); ++failures; }
}

// Goertzel magnitude of `x` at frequency f (phase-invariant → latency-robust).
static double goertzelMag(const std::vector<double>& x, double f, double fs)
{
    const double w = 2.0 * M_PI * f / fs;
    const double coeff = 2.0 * std::cos(w);
    double s0 = 0.0, s1 = 0.0, s2 = 0.0;
    for (double v : x) { s0 = v + coeff * s1 - s2; s2 = s1; s1 = s0; }
    const double real = s1 - s2 * std::cos(w);
    const double imag = s2 * std::sin(w);
    return std::sqrt(real * real + imag * imag) * 2.0 / (double) x.size();
}

// Render a steady sine through a fresh PedalDSP at the given OS order; return the
// output tail (transient discarded).
static std::vector<double> renderSine(PedalChain::Params p, int order, double freq,
                                      double amp, double fs, int nOut, double settleSec = 0.3,
                                      FitParams fit = FitParams{})
{
    PedalDSP dsp;
    const int block = 256;
    dsp.prepare(fs, block);
    dsp.setFitParams(fit);           // defaults to the shipped calibration (matches PluginProcessor)
    dsp.setFactorOrder(order);
    dsp.setParams(p);

    const int settle = (int) (settleSec * fs);
    const int total = settle + nOut;
    std::vector<double> out;
    out.reserve((size_t) nOut);

    std::vector<double> buf((size_t) block);
    int phase = 0;
    for (int n = 0; n < total; n += block)
    {
        const int m = std::min(block, total - n);
        for (int i = 0; i < m; ++i)
            buf[(size_t) i] = amp * std::sin(2.0 * M_PI * freq * (phase + i) / fs);
        phase += m;
        dsp.processBlock(buf.data(), m);
        for (int i = 0; i < m; ++i)
            if (n + i >= settle)
                out.push_back(buf[(size_t) i]);
    }
    return out;
}

int main()
{
    constexpr double fs = 48000.0;

    // Report the integer latency each factor compensates the clean tap by.
    {
        PedalDSP probe;
        probe.prepare(fs, 256);
        std::printf("  [latency] clean-tap delay (base samples): ");
        for (int order = 0; order < 4; ++order)
        {
            probe.setFactorOrder(order);
            std::printf("%dx=%d  ", 1 << order, probe.getLatencySamples());
        }
        std::printf("\n");
    }

    // ---- 1. Delay-comp: BLEND=50% magnitude is OS-factor-independent ---------
    {
        PedalChain::Params p;
        p.blend = 0.5;
        p.level = 1.0;
        p.drive = 0.3;
        p.master = 1.0;

        // Freqs split into two bands with DIFFERENT expectations:
        //  • LF (≤200 Hz): bilinear warp of the OD tone caps is negligible, so a
        //    correct delay comp makes the clean+OD sum FACTOR-INDEPENDENT. Strict
        //    (<0.1 dB) — this is the actual delay-comp proof. A missing/stale
        //    delay would comb here and the spread would blow up.
        //  • HF (600/1500 Hz): the OD caps (SK ~3.3k, etc.) re-discretise at the
        //    OS rate, so higher OS = less top-octave warp = a slightly different
        //    OD magnitude (dsp.md "Top-octave accuracy" — a WANTED accuracy gain,
        //    not a delay error). Informational; bounded, not factor-independent.
        // ⚠⚠ SESSION 124 — THIS BLOCK RUNS WITH ADAA HELD UNIFORM ACROSS THE FOUR
        // ARMS, AND THAT IS A CORRECTION, NOT A CONCESSION. The shipped build gates
        // ADAA by OS factor (on at 1x/2x, off at 4x/8x — FitParams.h::clipAdaaMaxOs),
        // which makes the OD path DELIBERATELY factor-dependent. This check asserts
        // the opposite, so on the shipped defaults it fails: measured, the 200 Hz
        // spread goes 0.078 -> 0.112 against a 0.1 bar, with 1x moving -0.033 dB, 2x
        // -0.017, and 4x/8x BIT-UNMOVED — i.e. exactly the two gated factors moved.
        // ⭐ The tempting repair is to widen the bar to 0.15. That is wrong: this bar
        // is the ONLY delay-compensation proof in the suite, a stale delay line combs
        // here, and a widened bar would silently absorb it. Instead, hold the
        // INTENDED effect constant so the check measures only what it is for — the
        // original 0.1 bar then survives untouched, which is the tell that this is a
        // correction rather than a concession: a rebuilt test that is harder than the
        // one it replaces and still passes is a correction; one that is easier is not.
        // The ADAA policy gets its OWN assertion, below.
        FitParams delayFit;
        delayFit.clipAdaaMaxOs = 0; // ADAA off at EVERY factor => the only thing
                                    // differing between arms is the OS/delay path.

        struct FreqCheck { double f; bool strict; };
        const FreqCheck freqs[] = {{80.0, true}, {200.0, true}, {600.0, false}, {1500.0, false}};
        std::printf("  [delay-comp] BLEND=50%% magnitude (dB) across OS factors"
                    " (ADAA held OFF at all factors — see note):\n");
        std::printf("     freq      1x        2x        4x        8x     spread  (band)\n");
        for (auto fc : freqs)
        {
            double mag[4];
            for (int order = 0; order < 4; ++order)
            {
                auto y = renderSine(p, order, fc.f, 0.3, fs, 1 << 15, 0.3, delayFit);
                mag[order] = 20.0 * std::log10(goertzelMag(y, fc.f, fs) + 1e-30);
            }
            double lo = mag[0], hi = mag[0];
            for (int o = 1; o < 4; ++o) { lo = std::min(lo, mag[o]); hi = std::max(hi, mag[o]); }
            const double spread = hi - lo;
            std::printf("  %7.0f  %8.3f  %8.3f  %8.3f  %8.3f   %5.3f  (%s)\n",
                        fc.f, mag[0], mag[1], mag[2], mag[3], spread,
                        fc.strict ? "delay" : "warp");
            if (fc.strict)
                check(spread < 0.1,
                      "LF BLEND=50% magnitude factor-independent (<0.1 dB → delay comp OK)");
            else
                check(spread < 1.0, "HF spread stays bounded (<1 dB warp-accuracy gain)");
        }
    }

    // ---- 1b. The ADAA OS-factor gate is LIVE, and reaches ONLY 1x/2x ---------
    // Session 124. The gate is a shipped POLICY (FitParams.h::clipAdaaMaxOs = 2), and
    // a policy that silently stops applying is the expensive kind of regression: the
    // build keeps working, nothing fails, and the realtime alias reduction the user
    // decided to enable just quietly disappears. So assert both halves against a
    // control with ADAA disabled everywhere:
    //   • 1x and 2x MUST differ from the control  (the gate is doing something)
    //   • 4x and 8x MUST be BIT-IDENTICAL to it   (it is doing it only where intended)
    // ⭐ The second half is the more valuable one — it is a free SCOPE check, and it
    // is what distinguishes "ADAA is on at 1x/2x" from "ADAA is on and also leaking
    // somewhere I did not look". Both are parameter-free: no threshold to argue about.
    {
        PedalChain::Params p;
        p.blend = 1.0;   // pure OD — the clean tap would dilute the very difference
        p.level = 1.0;   //           being measured (bleed-free, GATE K2's rule)
        p.drive = 0.6;
        p.master = 1.0;

        FitParams shipped;             // clipAdaa = 1, clipAdaaMaxOs = 2
        FitParams noAdaa = shipped;
        noAdaa.clipAdaaMaxOs = 0;      // same build, gate disabled

        std::printf("  [adaa-gate] shipped vs ADAA-off control, per factor"
                    " (clipAdaa=%d, clipAdaaMaxOs=%d):\n",
                    shipped.clipAdaa, shipped.clipAdaaMaxOs);
        for (int order = 0; order < 4; ++order)
        {
            const int factor = 1 << order;
            auto a = renderSine(p, order, 2499.0, 0.35, fs, 1 << 14, 0.3, shipped);
            auto b = renderSine(p, order, 2499.0, 0.35, fs, 1 << 14, 0.3, noAdaa);

            double worst = 0.0;
            for (size_t i = 0; i < a.size() && i < b.size(); ++i)
                worst = std::max(worst, std::abs(a[i] - b[i]));

            const bool wantLive = (factor <= shipped.clipAdaaMaxOs);
            const bool live = (worst != 0.0);
            std::printf("     %dx  worst |shipped - control| = %.3e  -> %-9s (want %s)\n",
                        factor, worst, live ? "ADAA ON" : "identical",
                        wantLive ? "ADAA ON" : "identical");
            check(live == wantLive,
                  wantLive ? "ADAA gate is LIVE at this factor (1x/2x)"
                           : "ADAA gate is INERT at this factor (4x/8x) — bit-identical to control");
        }
    }

    // ---- 2. Aliasing reduction with OS factor --------------------------------
    {
        PedalChain::Params p;
        p.blend = 1.0;    // full OD
        p.level = 1.0;
        p.drive = 0.85;   // hard into the clipper
        p.master = 1.0;

        // amp 0.35: hard into the clipper for the SESSION-17 fitted gain staging
        // (kInputRef 3.377). ** The probe amp MUST track the gain staging** — it
        // was 0.2 through session 16, but the fitted kInputRef (0.87 -> 3.377)
        // raised the clipper-onset input level, so at 0.2 the chain sits BELOW
        // onset and every factor is at the measurement floor.
        // ⚠ kInputRef has since moved TWICE — 3.377 -> 1.2596 (s44) -> 0.90 (s109) — and this
        // probe is deliberately UNAFFECTED by either: it feeds PedalDSP directly, in CHAIN-DOMAIN
        // VOLTS, so K (a DAW-domain scalar, GainStaging.h) never enters. Verified at s109: the
        // whole amp x factor table is unchanged across the 1.2596 -> 0.90 move. What HAS drifted is
        // only what DAW level 0.35 V corresponds to (-19.7 dBFS at K = 3.377, -8.2 dBFS at
        // K = 0.90), so read "hard into the clipper" as a statement about the CHAIN, which is what
        // this test measures, not about a plugin input level.
        //
        // f0 is bin-exact: kBin cycles in exactly fftN samples (header note (a)),
        // so the settled output is periodic in fftN, the rectangular window is
        // leakage-free, and every harmonic — and every FOLD of a harmonic — lands
        // dead on a bin. 2499.02 Hz, one bin off the 2500 the old test used.
        const int fftOrder = 14;         // 16384
        const int fftN = 1 << fftOrder;
        const int kBin = 853;
        const double f0 = kBin * fs / fftN;
        const double gateAmp = 0.35;
        const double lfHz = 200.0;       // below this = settling residue, reported separately
        const double settleSec = 4.0;    // 18 tau of the 0.72 Hz output high-passes

        // Returns { alias/signal dB, LF-bucket/signal dB }.
        auto aliasFloorDb = [&](int order, double amp, FitParams fit = FitParams{}) {
            auto y = renderSine(p, order, f0, amp, fs, fftN, settleSec, fit);
            juce::dsp::FFT fft(fftOrder);
            std::vector<float> fd((size_t) fftN * 2, 0.0f);
            for (int i = 0; i < fftN; ++i)
                fd[(size_t) i] = (float) y[(size_t) i];   // rectangular — see above
            fft.performFrequencyOnlyForwardTransform(fd.data());

            double sig = 0.0, alias = 0.0, lf = 0.0;
            for (int b = 1; b < fftN / 2; ++b)
            {
                const double e = (double) fd[(size_t) b] * (double) fd[(size_t) b];
                if (b % kBin == 0)                       // exact harmonic bin
                    sig += e;
                else if (b * fs / fftN < lfHz)           // settling / DC residue
                    lf += e;
                else
                    alias += e;
            }
            return std::pair<double, double>{ 10.0 * std::log10((alias + 1e-30) / (sig + 1e-30)),
                                              10.0 * std::log10((lf + 1e-30) / (sig + 1e-30)) };
        };

        // Full sweep, printed unconditionally — see this file's header: there is a
        // drive band where 8x goes backwards, and it must stay visible.
        std::printf("  [aliasing] f0 = %.2f Hz (bin-exact), rect window, %.0f s settle\n",
                    f0, settleSec);
        std::printf("  [aliasing] alias/signal (dB) vs input amp — 8x SHOULD be lowest"
                    " (lf = settling bucket, excluded):\n");
        for (double a : { 0.05, 0.1, 0.2, 0.35, 0.5, 0.7 })
        {
            const auto r2 = aliasFloorDb(1, a), r4 = aliasFloorDb(2, a), r8 = aliasFloorDb(3, a);
            // Flag a REAL inversion: 8x failing to beat 2x while still well clear of
            // where there is nothing left to improve.
            const bool bad = (r8.first > r2.first - 3.0) && (r8.first > -60.0);
            std::printf("      amp %.2f :  2x %+6.1f   4x %+6.1f   8x %+6.1f   (lf %+6.1f)%s\n",
                        a, r2.first, r4.first, r8.first, r8.second,
                        bad ? "   <-- REAL FOLD-DOWN, see header (c)" : "");
        }

        const double a2 = aliasFloorDb(1, gateAmp).first; // 2x
        const double a4 = aliasFloorDb(2, gateAmp).first; // 4x
        const double a8 = aliasFloorDb(3, gateAmp).first; // 8x
        std::printf("  [aliasing] alias/signal floor: 2x=%.1f dB  4x=%.1f dB  8x=%.1f dB\n",
                    a2, a4, a8);
        check(a8 < a2 - 3.0, "8x aliasing floor >=3 dB below 2x (oversampling works)");
        // Tolerance 1.0 dB (was 0.5): at the amp-0.2 probe 2x and 4x sit within a
        // fraction of a dB of EACH OTHER in every build, so gating their DIFFERENCE
        // at 0.5 dB is brittle. The session-11 clipper VTC reshape (tanh -> k=2
        // sigmoid) tripped exactly that: 2x/4x floors moved -21.3/-21.2 ->
        // -22.1/-21.6 — BOTH improved, but 2x improved more, pushing the diff from
        // +0.1 to +0.5 dB. The intent of this check is "4x is not MATERIALLY worse
        // than 2x", and 1.0 dB expresses that without flagging a strict improvement.
        check(a4 <= a2 + 1.0, "4x aliasing floor no worse than 2x (1 dB tol)");

        // ---- what the shipped ADAA policy actually BUYS, in-chain (session 124) --
        // Test 1b proves the gate is live and correctly scoped; it says nothing about
        // whether the thing it enables is worth enabling. This does, on the FULL
        // PedalDSP chain — an instrument sharing no machinery with the calibration
        // fit's own ADAA gate, which is what makes the agreement below evidence
        // rather than a restatement.
        //
        // ⚠ Assert the SIGN, print the SIZE. A "must improve by >= N dB" bar would be
        // a guessed number, and the benefit is legitimately amplitude-dependent — so the
        // guard is "the shipped policy is not WORSE than not having it", which is
        // parameter-free and still catches a regression that inverts the policy's
        // value. The column is printed so the size stays visible and quotable.
        //
        // ⭐ The DOSE-RESPONSE is the real validity check, and it is free: ADAA1's
        // benefit should GROW with drive, because a harder-driven node W steps further
        // between samples and so crosses more of the knee per sample (Clipper.h
        // setADAA's in-chain dw/knee table). A fixed filter difference could not do
        // that. Measured at session 124, amp -> benefit:
        //     0.05 -2.2 | 0.10 +0.6 | 0.20 -4.2 | 0.35 -15.1 | 0.50 -20.3 | 0.70 -20.1
        // ⚠ Quote that as a TREND, not a monotone law — amp 0.10 costs +0.6 dB and
        // 0.70 is fractionally behind 0.50, so it is neither monotone nor uniformly a
        // win, and saying "rises monotonically" (as this comment first did, before the
        // table was read back) would be an overclaim of exactly the kind this project
        // keeps paying for. What IS supported: the benefit is small-to-negative at low
        // drive and 15-20 dB at the drive levels that matter.
        // ⭐ Corroboration worth more than the trend: GATE X's independent harness read
        // -12.6 / -19.8 dB at amps 0.35 / 0.70 against this instrument's -15.1 / -20.1
        // — two instruments sharing no machinery, agreeing to ~2.5 dB.
        {
            FitParams noAdaa;
            noAdaa.clipAdaaMaxOs = 0;
            std::printf("  [adaa-benefit] 2x alias/signal, shipped vs ADAA-off control"
                        " (negative = ADAA better):\n");
            for (double a : { 0.05, 0.1, 0.2, 0.35, 0.5, 0.7 })
            {
                const double on = aliasFloorDb(1, a).first;
                const double off = aliasFloorDb(1, a, noAdaa).first;
                std::printf("      amp %.2f :  off %+6.1f   on %+6.1f   benefit %+6.1f dB\n",
                            a, off, on, on - off);
            }
            const double onGate = aliasFloorDb(1, gateAmp).first;
            const double offGate = aliasFloorDb(1, gateAmp, noAdaa).first;
            std::printf("  [adaa-benefit] at gate amp %.2f: %+.1f -> %+.1f dB (%+.1f)\n",
                        gateAmp, offGate, onGate, onGate - offGate);
            check(onGate <= offGate,
                  "shipped ADAA policy does not worsen the 2x alias floor");
        }
    }

    if (failures == 0) std::printf("OSValidationTest: PASS\n");
    else std::printf("OSValidationTest: %d FAILURE(S)\n", failures);
    return failures == 0 ? 0 : 1;
}
