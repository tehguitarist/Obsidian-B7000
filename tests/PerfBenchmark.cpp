// PerfBenchmark — the Phase-10 CPU probe, and the instrument that closes open-work
// item 3 ("the pow() fast path is UNBLOCKED but NOT MEASURED", session 124).
//
// WHY IT EXISTS. `build.md` has specified a `PerfBenchmark` since the template, and
// `README.md` still carries a placeholder for its table, but it was never built: the
// only per-sample cost this project has ever recorded — **356.59 ns/sample for the
// clipper stage at 384 kHz, best-of-5 over 4 M samples** (session 120) — came from a
// scratch probe that no longer exists on disk. Session 124 then shipped three
// constants whose perf effect is genuinely two-signed and was explicitly NOT measured:
//
//   • `clipK` 2.4653 -> 2.0 RESTORES `sig()`/`sigDeriv()`'s `k == 2.0` fast path,
//     removing two `std::pow` per F evaluation at EVERY oversampling factor. That
//     was the entire perf argument for the re-anchor (session 120 found `pow`, not
//     the iteration count, to be the dominant per-sample cost).
//   • `clipAdaa` Off -> Full ADDS work — a second VTC evaluation and an
//     antiderivative per F evaluation — but only at 1x/2x, where `clipAdaaMaxOs`
//     gates it on.
//
// So the two changes pull opposite ways exactly where the plugin runs in realtime,
// and CLAUDE.md's item 3 says in as many words: "measure it, do not reason about it".
// This file measures it.
//
// ⛔ IT IS NOT A PERFORMANCE GATE, AND MUST NOT BECOME ONE. Per `build.md`
// ("register them with add_test() as **finite-only** probes ... do NOT gate on
// absolute CPU %, CI speed varies"), every pass/fail assertion below is either a
// finiteness check or a CHECKSUM identity. Timing is printed, never asserted. A
// green run says "the arms are real and the arithmetic is sound", not "fast enough".
//
// WHAT IS ASSERTED (and why each one is not vacuous):
//
//   1. Finiteness + non-zero checksum on every arm — `empty-gate-must-fail` in a
//      probe is still `empty-gate-must-fail`; a probe that reports a NUMBER is a
//      gate whatever it is called (measurement-discipline.md §5, session 118).
//   2. **`k = 2.4653` + ADAA=Full is BIT-IDENTICAL to `k = 2.4653` + ADAA=Off.**
//      `Clipper::adaaExact()` gates the substitution on `hardness == 2.0`, so ADAA
//      is *silently inert* off the anchor (FitParams.h::clipAdaa says so). That
//      makes it a free known answer with no threshold to argue about — and it is
//      the one arm pairing that proves the gating claim rather than restating it.
//   3. **`k = 2.0` differs from `k = 2.4653`, and ADAA=Full differs from ADAA=Off
//      AT the anchor.** These are the non-vacuity controls. Without them a
//      constant that never reaches the stage makes two arms equal and the timing
//      table reads "free" for the very defect it exists to catch (session 100's
//      mutation-control lesson, and session 118's `--os 3` probe that reported a
//      clean 0.0000 % on nine renders that processed nothing).
//   4. **In the full chain, the shipped build is bit-identical to an ADAA-off
//      control at 4x/8x and differs at 1x/2x.** That is the OS-factor gate's scope,
//      re-derived here through a code path that shares nothing with
//      `OSValidationTest`'s version of the same assertion — and it is what proves
//      my chain arms actually reach `Clipper` rather than being three renders of
//      one configuration.
//
// METHOD, AND ITS ONE HONEST LIMIT. Best-of-N over a fixed sample count, one
// warm-up rep discarded, stimulus PRECOMPUTED outside the timed region (three
// `std::sin` per sample would be ~17 % of the clipper's own cost and would make the
// absolute ns/sample incomparable to session 120's figure). Best-of-N rather than a
// mean because the contaminant here is one-sided — scheduler preemption, thermal
// throttling, and a laptop that has been known to clamshell-sleep mid-run
// (`wallclock-is-not-runtime`) can only ever make a rep SLOWER.
//   ⚠ The absolute ns/sample is a property of THIS MACHINE on THIS RUN. Session
// 120's 356.59 is printed beside the arm that reproduces its configuration as a
// cross-session sanity read, NOT as a bar: a laptop three sessions later is not a
// controlled instrument. **The measurement is the RATIO between arms in one run**,
// which shares the machine, the binary and the thermal state.
//
// STIMULUS. The stage bench is driven by an inharmonic three-tone sum, not a smooth
// LF sine, because this is a warm-started iterative solve: session 120 established
// that its work depends on how far the argument moves BETWEEN SAMPLES, so a slow
// sine makes the previous sample a good warm start and understates the iteration
// count by a lot (two independent synthetic sweeps both understated the same defect
// that way). The dominant tone is 2499 Hz — the frequency session 120's in-chain
// measurement found the real signal carrying at the clipper.
//
// #include "../src/dsp/PedalDSP.h" pulls in PedalChain -> Clipper, so both the
// stage-level and chain-level benches read the SHIPPED headers, not a transcription.

#include "../src/dsp/PedalDSP.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

static int failures = 0;
static void check(bool cond, const char* msg)
{
    if (! cond)
    {
        std::printf("  FAIL: %s\n", msg);
        ++failures;
    }
}

// Session 120's recorded figure for the clipper stage at 384 kHz, ADAA absent,
// clipK = 2.4653. Printed for context; NOT a threshold (see the header note).
static constexpr double kS120ClipperNsPerSample = 356.59;
static constexpr double kS120ClipperRate = 384000.0;

// clipK before session 124's re-anchor — the value that MISSES the k == 2 fast path.
static constexpr double kPreS124ClipK = 2.4653;

static constexpr int kReps = 5; // best-of, after one discarded warm-up

// ---------------------------------------------------------------------------------
// Timing helper. Runs `fn` once un-timed (warm the caches / let the branch
// predictor settle), then kReps times, returning the BEST ns per sample.
// ---------------------------------------------------------------------------------
template <typename F>
static double bestNsPerSample(F&& fn, long long nSamples)
{
    fn(); // warm-up, discarded
    double best = 1e300;
    for (int r = 0; r < kReps; ++r)
    {
        const auto t0 = std::chrono::steady_clock::now();
        fn();
        const auto t1 = std::chrono::steady_clock::now();
        const double ns = std::chrono::duration<double, std::nano>(t1 - t0).count() / (double) nSamples;
        best = std::min(best, ns);
    }
    return best;
}

// ---------------------------------------------------------------------------------
// 1. STAGE-LEVEL: the clipper alone, at one rate, four (clipK, ADAA) arms.
//    This is the arm set directly comparable to session 120's 356.59 ns/sample.
// ---------------------------------------------------------------------------------
struct Arm
{
    const char* label;
    double k;
    Clipper::Adaa adaa;
    double ns = 0.0;
    double checksum = 0.0;
    long long nonFinite = 0;
};

static void benchClipperArm(Arm& a, const std::vector<double>& stim, double rate)
{
    const FitParams fit{}; // the SHIPPED calibration; only k and the ADAA mode vary
    const long long n = (long long) stim.size();

    auto run = [&]() {
        Clipper c;
        c.prepare(rate); // must precede the cap setters — prepare() sets fs
        c.setNonlinear(fit.clipA0, fit.clipSatLo, fit.clipSatHi, a.k);
        c.setC11(fit.clipC11);
        c.setC12(fit.clipC12);
        c.setC13(fit.clipC13);
        c.setR16(fit.clipR16);
        c.setGrunt(Clipper::Grunt::Cut); // REF-OD baseline = the On-Off-On centre
        c.setADAA(a.adaa);

        double sum = 0.0;
        long long bad = 0;
        for (long long i = 0; i < n; ++i)
        {
            const double y = c.process(stim[(size_t) i]);
            sum += y;
            if (! std::isfinite(y))
                ++bad;
        }
        a.checksum = sum;
        a.nonFinite = bad;
    };

    a.ns = bestNsPerSample(run, n);
}

// ---------------------------------------------------------------------------------
// 2. CHAIN-LEVEL: the real PedalDSP, per OS factor, three FitParams arms.
//    This is the number the user actually feels — and the one item 3 calls unknown,
//    because ADAA adds work only at 1x/2x while the fast path removes it everywhere.
// ---------------------------------------------------------------------------------
struct ChainResult
{
    double ns = 0.0;      // per BASE-rate sample
    double checksum = 0.0;
    long long nonFinite = 0;
    int latency = 0;
};

static ChainResult benchChain(const std::vector<double>& stim, int order, double fs, FitParams fit)
{
    ChainResult r;
    const int block = 256;
    const long long n = (long long) stim.size();

    auto run = [&]() {
        PedalDSP dsp;
        dsp.prepare(fs, block);
        dsp.setFitParams(fit);
        dsp.setFactorOrder(order);

        PedalChain::Params p;
        p.blend = 1.0;  // pure OD — the clipper's worst case, which is what a perf
        p.level = 1.0;  // table wants; a blended setting is cheaper, not different.
        p.drive = 0.85; // sessions 118/120's operating point
        p.master = 1.0;
        dsp.setParams(p);

        r.latency = dsp.getLatencySamples();

        std::vector<double> buf((size_t) block);
        double sum = 0.0;
        long long bad = 0;
        for (long long i = 0; i < n; i += block)
        {
            const int m = (int) std::min<long long>(block, n - i);
            std::copy(stim.begin() + (size_t) i, stim.begin() + (size_t) (i + m), buf.begin());
            dsp.processBlock(buf.data(), m);
            for (int j = 0; j < m; ++j)
            {
                sum += buf[(size_t) j];
                if (! std::isfinite(buf[(size_t) j]))
                    ++bad;
            }
        }
        r.checksum = sum;
        r.nonFinite = bad;
    };

    r.ns = bestNsPerSample(run, n);
    return r;
}

// Inharmonic three-tone sum — see the header note on why not a slow sine.
static std::vector<double> makeStim(long long n, double rate, double amp)
{
    std::vector<double> s((size_t) n);
    for (long long i = 0; i < n; ++i)
    {
        const double t = (double) i / rate;
        s[(size_t) i] = amp * (0.55 * std::sin(2.0 * M_PI * 2499.0 * t)
                               + 0.30 * std::sin(2.0 * M_PI * 617.3 * t)
                               + 0.15 * std::sin(2.0 * M_PI * 97.7 * t));
    }
    return s;
}

int main()
{
    std::printf("PerfBenchmark — Phase 10 CPU probe (open-work item 3)\n");
    std::printf("  best-of-%d, one warm-up discarded, stimulus precomputed.\n", kReps);
    std::printf("  ⚠ ABSOLUTE ns/sample IS MACHINE- AND RUN-SPECIFIC. The measurement is the\n");
    std::printf("    RATIO between arms of one run; nothing below is a threshold.\n\n");

    // =============================================================================
    // 1. Clipper stage, 384 kHz (= 48 kHz x 8, session 120's rate) and 96 kHz (x2,
    //    where the shipped policy has ADAA ON).
    // =============================================================================
    const long long kStageN = 2'000'000;

    for (const double rate : { 384000.0, 96000.0 })
    {
        for (const double amp : { 2.9, 0.9 })
        {
            const auto stim = makeStim(kStageN, rate, amp);

            Arm arms[] = {
                { "k=2.4653  ADAA Off   (pre-s124 shipped)", kPreS124ClipK, Clipper::Adaa::Off },
                { "k=2.0     ADAA Off   (pow fast path)   ", 2.0, Clipper::Adaa::Off },
                { "k=2.0     ADAA Full  (s124 SHIPPED <=2x)", 2.0, Clipper::Adaa::Full },
                { "k=2.4653  ADAA Full  [CONTROL: inert]  ", kPreS124ClipK, Clipper::Adaa::Full },
            };
            for (auto& a : arms)
                benchClipperArm(a, stim, rate);

            std::printf("  [stage] Clipper alone @ %.0f kHz, amp %.1f V, %lld samples\n",
                        rate / 1000.0, amp, kStageN);
            const double ref = arms[0].ns;
            for (const auto& a : arms)
                std::printf("     %s  %8.2f ns/sample  %+7.2f %%   checksum %+.9e\n",
                            a.label, a.ns, 100.0 * (a.ns - ref) / ref, a.checksum);

            // --- what the arms MEAN, computed not narrated ---
            const double powSaving = 100.0 * (arms[1].ns - arms[0].ns) / arms[0].ns;
            const double adaaCost = 100.0 * (arms[2].ns - arms[1].ns) / arms[1].ns;
            const double net = 100.0 * (arms[2].ns - arms[0].ns) / arms[0].ns;
            std::printf("     => pow fast path %+.2f %% | ADAA on top %+.2f %% | s124 NET %+.2f %%\n",
                        powSaving, adaaCost, net);

            if (rate == kS120ClipperRate && amp == 2.9)
                std::printf("     [context, NOT a bar] session 120 recorded %.2f ns/sample for arm 1;\n"
                            "       this run reads %.2f (%+.1f %%). A different machine/thermal state is\n"
                            "       expected to move it — only the within-run ratios above are quotable.\n",
                            kS120ClipperNsPerSample, arms[0].ns,
                            100.0 * (arms[0].ns - kS120ClipperNsPerSample) / kS120ClipperNsPerSample);

            // --- assertions: finiteness, the ADAA-gating known answer, non-vacuity ---
            for (const auto& a : arms)
            {
                check(a.nonFinite == 0, (std::string("stage arm produced non-finite output: ") + a.label).c_str());
                check(std::isfinite(a.checksum) && a.checksum != 0.0,
                      (std::string("stage arm checksum not finite/non-zero: ") + a.label).c_str());
                check(a.ns > 0.0, (std::string("stage arm timed at zero — did it run? ") + a.label).c_str());
            }
            // (2) adaaExact() gates on hardness == 2.0, so ADAA off the anchor is INERT.
            check(arms[3].checksum == arms[0].checksum,
                  "ADAA=Full at k != 2 is NOT bit-identical to ADAA=Off — adaaExact() gating broke");
            // (3) non-vacuity: both levers must actually change the output.
            check(arms[1].checksum != arms[0].checksum,
                  "clipK made no difference to the output — the constant is not reaching the stage");
            check(arms[2].checksum != arms[1].checksum,
                  "ADAA=Full made no difference AT the anchor — the mode is not reaching the stage");
            std::printf("\n");
        }
    }

    // =============================================================================
    // 2. Full chain, per OS factor. THE HEADLINE: what session 124 cost or bought
    //    at the factors the plugin actually runs at.
    // =============================================================================
    constexpr double fs = 48000.0;
    const long long kChainN = 96'000; // 2 s of audio at the base rate
    const auto chainStim = makeStim(kChainN, fs, 0.30);

    FitParams shipped{}; // k=2.0, clipAdaa=1, clipAdaaMaxOs=2

    FitParams fastPathOnly{};
    fastPathOnly.clipAdaa = 0; // k stays 2.0; ADAA off everywhere

    FitParams preS124{};
    preS124.clipK = kPreS124ClipK;
    preS124.clipAdaa = 0;

    std::printf("  [chain] full PedalDSP, BLEND=100%% OD, DRIVE=0.85, %lld base samples @ 48 kHz\n",
                kChainN);
    std::printf("     %-6s %-10s %10s %10s %10s   %8s %8s %8s\n",
                "factor", "latency", "shipped", "fastpath", "pre-s124", "pow%", "adaa%", "NET%");

    for (int order = 0; order < 4; ++order)
    {
        const int factor = 1 << order;
        const auto rShip = benchChain(chainStim, order, fs, shipped);
        const auto rFast = benchChain(chainStim, order, fs, fastPathOnly);
        const auto rPre = benchChain(chainStim, order, fs, preS124);

        const double powSaving = 100.0 * (rFast.ns - rPre.ns) / rPre.ns;
        const double adaaCost = 100.0 * (rShip.ns - rFast.ns) / rFast.ns;
        const double net = 100.0 * (rShip.ns - rPre.ns) / rPre.ns;

        std::printf("     %-6s %-10d %9.1f  %9.1f  %9.1f   %+7.2f %+7.2f %+7.2f\n",
                    (std::to_string(factor) + "x").c_str(), rShip.latency,
                    rShip.ns, rFast.ns, rPre.ns, powSaving, adaaCost, net);

        // x realtime — the number that answers "does it still run live?"
        const double nsPerSampleBudget = 1e9 / fs;
        std::printf("            x realtime: shipped %.1f | fastpath %.1f | pre-s124 %.1f  "
                    "(CPU %% of one core: %.2f / %.2f / %.2f)\n",
                    nsPerSampleBudget / rShip.ns, nsPerSampleBudget / rFast.ns, nsPerSampleBudget / rPre.ns,
                    100.0 * rShip.ns / nsPerSampleBudget, 100.0 * rFast.ns / nsPerSampleBudget,
                    100.0 * rPre.ns / nsPerSampleBudget);

        for (const auto* r : { &rShip, &rFast, &rPre })
        {
            check(r->nonFinite == 0, "chain arm produced non-finite output");
            check(std::isfinite(r->checksum) && r->checksum != 0.0, "chain arm checksum not finite/non-zero");
            check(r->ns > 0.0, "chain arm timed at zero — did it run?");
        }

        // (4) THE OS-FACTOR GATE'S SCOPE, re-derived through a path that shares nothing
        //     with OSValidationTest: ADAA is ON at 1x/2x (so shipped != ADAA-off control)
        //     and OFF at 4x/8x (so shipped IS bit-identical to it). This is simultaneously
        //     the policy assertion and the proof that these three arms reach the DSP.
        if (factor <= shipped.clipAdaaMaxOs)
            check(rShip.checksum != rFast.checksum,
                  "shipped == ADAA-off control at a GATED-ON factor — the ADAA policy is not applying");
        else
            check(rShip.checksum == rFast.checksum,
                  "shipped != ADAA-off control at a GATED-OFF factor — ADAA is leaking past clipAdaaMaxOs");

        // The pow fast path is factor-independent by construction (it is inside every F
        // evaluation), so preS124 must differ from the other two at EVERY factor.
        check(rPre.checksum != rFast.checksum, "clipK is not reaching the chain at this factor");
    }

    std::printf("\n");
    if (failures == 0)
        std::printf("PerfBenchmark: all structural checks PASSED (%d failures). Timing is REPORTED, not gated.\n", failures);
    else
        std::printf("PerfBenchmark: %d FAILURE(S).\n", failures);
    return failures == 0 ? 0 : 1;
}
