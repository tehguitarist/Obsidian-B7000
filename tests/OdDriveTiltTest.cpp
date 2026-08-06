// =============================================================================
// OdDriveTilt — [ENG] level-dependent treble tilt (session 166)
// =============================================================================
// ⛔⛔ TEST 3 IS THE ONE THAT MATTERS AND IT IS NOT A NUMERICAL CHECK.
// Two ARCHITECTURES for this correction were refuted by measurement before this
// stage was built (GATE BA s164, GATE BB s165), and BOTH refutations say the same
// thing: a correction whose coefficients do NOT move with signal level contributes
// EXACTLY ZERO to the target, because the target is a DIFFERENCE between stimulus
// levels and anything fixed cancels from it identically.  The obvious future
// "simplification" of this stage — replace the envelope with a DRIVE-knob table,
// like `OdToneRestore` — would compile, sound plausible, and measure as zero.
// Test 3 asserts the property that makes the stage work at all.
//
//   0. the RBJ high-shelf matches an INDEPENDENT implementation of the Audio EQ
//      Cookbook formulae (the s156 pattern: certify a hand-transcribed biquad)
//   1. the law — flat at/below the reference, progressive CUT above it, clamped
//   2. disabled is EXACTLY a bypass (bit-identical), so the `--fit` gate every
//      measurement gate uses is trustworthy
//   3. ⭐ LEVEL DEPENDENCE — the stage's own transfer must DIFFER between two
//      input levels, by the amount the law asks for
//   4. the shelf only acts ABOVE its corner: a low-frequency tone is unaffected
//      even at full cut, so the correction is confined to the treble
// =============================================================================

#include "../src/dsp/OdDriveTilt.h"

#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <functional>
#include <random>
#include <vector>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static int failures = 0;

static void check(bool ok, const char* what, double got, double want, double tol)
{
    std::printf("  %-58s got %12.6g  want %12.6g  %s\n", what, got, want,
                ok ? "OK" : "** FAIL **");
    if (! ok)
        ++failures;
    (void) tol;
}

static void near(const char* what, double got, double want, double tol)
{
    check(std::fabs(got - want) <= tol, what, got, want, tol);
}

// Independent transcription of the RBJ high-shelf, straight from the Audio EQ
// Cookbook — deliberately NOT sharing code with the stage.
static double refShelfDb(double fs, double f0, double S, double gainDb, double f)
{
    const double A = std::pow(10.0, gainDb / 40.0);
    const double w0 = 2.0 * M_PI * f0 / fs;
    const double alpha = std::sin(w0) / 2.0 * std::sqrt((A + 1.0 / A) * (1.0 / S - 1.0) + 2.0);
    const double c = std::cos(w0), sq = 2.0 * std::sqrt(A) * alpha;
    const double b0 = A * ((A + 1) + (A - 1) * c + sq), b1 = -2 * A * ((A - 1) + (A + 1) * c);
    const double b2 = A * ((A + 1) + (A - 1) * c - sq), a0 = (A + 1) - (A - 1) * c + sq;
    const double a1 = 2 * ((A - 1) - (A + 1) * c), a2 = (A + 1) - (A - 1) * c - sq;
    const double w = 2.0 * M_PI * f / fs;
    const double cr = std::cos(w), sr = -std::sin(w);
    const double c2 = std::cos(2 * w), s2 = -std::sin(2 * w);
    const double nr = b0 + b1 * cr + b2 * c2, ni = b1 * sr + b2 * s2;
    const double dr = a0 + a1 * cr + a2 * c2, di = a1 * sr + a2 * s2;
    return 10.0 * std::log10((nr * nr + ni * ni) / (dr * dr + di * di));
}

// Drive the stage with a steady sine at `amp`, let the envelope settle, then
// measure its gain at `f` by correlation.  Returns dB.
static double measureDb(OdDriveTilt& s, double fs, double f, double amp, double envAmp)
{
    s.reset();
    const int settle = (int) (fs * 0.5), n = (int) (fs * 0.2);
    double re = 0.0, im = 0.0;
    for (int i = 0; i < settle + n; ++i)
    {
        const double t = i / fs;
        // The envelope is observed on the OD REGION'S INPUT, which in the plugin is a
        // different signal from this stage's own input — so the test drives them
        // separately, exactly as PedalChain does.
        s.observe(envAmp * std::sin(2.0 * M_PI * 220.0 * t));
        const double y = s.process(amp * std::sin(2.0 * M_PI * f * t));
        if (i >= settle)
        {
            const double p = 2.0 * M_PI * f * t;
            re += y * std::sin(p);
            im += y * std::cos(p);
        }
    }
    return 20.0 * std::log10(2.0 * std::hypot(re, im) / (n * amp) + 1e-300);
}

// =============================================================================
// Test 5 support: a faithful copy of OdDriveTilt's PRE-W3 recompute trigger --
// std::log10 called unconditionally every sample, no env2 window -- built
// standalone (shares no code with the header under test) so Test 5 can prove
// the W3 fast path is a decision-for-decision match, not merely argue it.
// =============================================================================
struct RefOdDriveTilt
{
    void prepare(double fs) noexcept
    {
        sampleRate = fs;
        smooth = coefFor(timeMs);
        shelf.reset();
        env2 = 0.0;
        lastGainDb = 1e9;
        recompute(0.0);
    }
    void resetState() noexcept
    {
        shelf.resetState();
        env2 = 0.0;
    }
    void setLaw(double f0Hz, double slopeS, double dbPerDb, double refDbv, double maxCutDb) noexcept
    {
        f0 = f0Hz; S = slopeS; k = dbPerDb; ref = refDbv; maxCut = maxCutDb;
        lastGainDb = 1e9;
        recompute(currentEnvDb());
    }
    void observe(double odRegionInput) noexcept
    {
        const double sq = odRegionInput * odRegionInput;
        env2 += smooth * (sq - env2);
    }
    double process(double x) noexcept
    {
        const double g = gainFor(currentEnvDb());
        if (std::fabs(g - lastGainDb) > kRecomputeDb)
            recompute(currentEnvDb());
        return shelf.process(x);
    }
    double currentGainDb() const noexcept { return gainFor(currentEnvDb()); }
    std::uint64_t recomputeCount() const noexcept { return recomputes; }

    static constexpr double kRecomputeDb = 0.02, kEnvFloor = 1e-20;
    double coefFor(double ms) const noexcept
    {
        if (sampleRate <= 0.0 || ms <= 0.0) return 1.0;
        return 1.0 - std::exp(-1.0 / (1e-3 * ms * sampleRate));
    }
    double currentEnvDb() const noexcept { return 10.0 * std::log10(env2 + kEnvFloor); }
    double gainFor(double envDb) const noexcept
    {
        return std::clamp(-k * (envDb - ref), -maxCut, 0.0);
    }
    void recompute(double envDb) noexcept
    {
        const double g = gainFor(envDb);
        lastGainDb = g;
        shelf.setHighShelf(sampleRate, f0, S, g);
        ++recomputes;
    }

    // Same RBJ direct-form-I biquad as the header (an independent copy, not a
    // shared include, so this really is a second implementation).
    struct ShelfBiquad
    {
        void setHighShelf(double fsIn, double cornerHz, double slopeS, double gainDb) noexcept
        {
            if (fsIn <= 0.0 || cornerHz <= 0.0 || cornerHz >= 0.5 * fsIn) return;
            const double A = std::pow(10.0, gainDb / 40.0);
            const double w0 = 2.0 * M_PI * cornerHz / fsIn;
            const double cosw0 = std::cos(w0), sinw0 = std::sin(w0);
            const double Ss = std::max(slopeS, 1e-3);
            const double alpha = 0.5 * sinw0 * std::sqrt((A + 1.0 / A) * (1.0 / Ss - 1.0) + 2.0);
            const double sq = 2.0 * std::sqrt(A) * alpha;
            const double b0 = A * ((A + 1.0) + (A - 1.0) * cosw0 + sq);
            const double b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cosw0);
            const double b2 = A * ((A + 1.0) + (A - 1.0) * cosw0 - sq);
            const double a0 = (A + 1.0) - (A - 1.0) * cosw0 + sq;
            const double a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cosw0);
            const double a2 = (A + 1.0) - (A - 1.0) * cosw0 - sq;
            B0 = b0 / a0; B1 = b1 / a0; B2 = b2 / a0; A1 = a1 / a0; A2 = a2 / a0;
        }
        double process(double x) noexcept
        {
            const double y = B0 * x + z1;
            z1 = B1 * x - A1 * y + z2;
            z2 = B2 * x - A2 * y;
            return y;
        }
        void reset() noexcept { resetState(); B0 = 1.0; B1 = B2 = A1 = A2 = 0.0; }
        void resetState() noexcept { z1 = z2 = 0.0; }
        double B0 = 1.0, B1 = 0.0, B2 = 0.0, A1 = 0.0, A2 = 0.0;
        double z1 = 0.0, z2 = 0.0;
    };
    ShelfBiquad shelf;
    double sampleRate = 48000.0, env2 = 0.0, smooth = 1.0, timeMs = 50.0, lastGainDb = 1e9;
    std::uint64_t recomputes = 0;
    double f0 = 5388.0, S = 0.85, k = 0.203, ref = -33.9, maxCut = 6.0;
};

int main()
{
    const double fs = 384000.0;   // the OD region runs oversampled
    const double f0 = 5388.0, S = 0.85, k = 0.203, ref = -33.9, maxCut = 6.0;

    std::printf("\n=== Test 0: RBJ high-shelf vs an INDEPENDENT transcription ===\n");
    {
        double worst = 0.0;
        for (double g : { -1.0, -3.0, -4.87, -6.0 })
            for (double f : { 500.0, 2000.0, 2934.8, 5388.0, 12000.0 })
            {
                OdDriveTilt s;
                s.prepare(fs);
                s.setEnabled(true);
                // k = 1 dB/dB, so an envelope |g| dB above `ref` asks for exactly `g`.
                s.setLaw(f0, S, 1.0, ref, std::fabs(g));
                const double got = measureDb(s, fs, f, 0.1,
                                             std::pow(10.0, (ref + std::fabs(g)) / 20.0) * std::sqrt(2.0));
                const double want = refShelfDb(fs, f0, S, g, f);
                worst = std::max(worst, std::fabs(got - want));
            }
        near("worst |stage - independent RBJ| over 20 (gain, f) cells", worst, 0.0, 0.05);
    }

    std::printf("\n=== Test 1: the gain law — flat at/below ref, progressive cut above ===\n");
    {
        OdDriveTilt s;
        s.prepare(fs);
        s.setEnabled(true);
        s.setLaw(f0, S, k, ref, maxCut);
        struct Row { double envDb, want; };
        // rms amplitude -> envelope dB; the law is clamp(-k*(env-ref), -maxCut, 0)
        for (Row r : { Row{ ref - 12.0, 0.0 }, Row{ ref, 0.0 },
                       Row{ ref + 12.0, -k * 12.0 }, Row{ ref + 24.0, -k * 24.0 },
                       Row{ ref + 100.0, -maxCut } })
        {
            s.reset();
            const double amp = std::pow(10.0, r.envDb / 20.0) * std::sqrt(2.0);
            for (int i = 0; i < (int) (fs * 0.5); ++i)
                s.observe(amp * std::sin(2.0 * M_PI * 220.0 * i / fs));
            char buf[96];
            std::snprintf(buf, sizeof buf, "gain at env = ref %+.0f dB", r.envDb - ref);
            near(buf, s.currentGainDb(), r.want, 0.05);
        }
    }

    std::printf("\n=== Test 2: disabled is EXACTLY a bypass ===\n");
    {
        OdDriveTilt s;
        s.prepare(fs);
        s.setEnabled(false);
        s.setLaw(f0, S, k, ref, maxCut);
        double worst = 0.0;
        for (int i = 0; i < 4096; ++i)
        {
            const double x = std::sin(0.017 * i) + 0.3 * std::sin(0.31 * i);
            s.observe(10.0 * x);              // a large envelope it must ignore
            worst = std::max(worst, std::fabs(s.process(x) - x));
        }
        check(worst == 0.0, "max |disabled output - input| (must be EXACTLY 0)", worst, 0.0, 0.0);
    }

    std::printf("\n=== Test 3: ⭐ LEVEL DEPENDENCE — the property both refutations demand ===\n");
    {
        OdDriveTilt s;
        s.prepare(fs);
        s.setEnabled(true);
        s.setLaw(f0, S, k, ref, maxCut);
        const double quiet = std::pow(10.0, ref / 20.0) * std::sqrt(2.0);
        const double loud = std::pow(10.0, (ref + 24.0) / 20.0) * std::sqrt(2.0);
        const double gQuiet = measureDb(s, fs, 2934.8, 0.05, quiet);
        const double gLoud = measureDb(s, fs, 2934.8, 0.05, loud);
        const double delta = gLoud - gQuiet;
        // The stage must deliver the shelf's own response to a -k*24 dB gain change.
        const double want = refShelfDb(fs, f0, S, -k * 24.0, 2934.8) - refShelfDb(fs, f0, S, 0.0, 2934.8);
        near("transfer CHANGE at the vertex across a 24 dB envelope step", delta, want, 0.10);
        check(std::fabs(delta) > 0.5,
              "the change is LARGE (a fixed stage would give EXACTLY 0)", std::fabs(delta), 1.0, 0.0);
    }

    std::printf("\n=== Test 4: the correction is confined to the treble ===\n");
    {
        OdDriveTilt s;
        s.prepare(fs);
        s.setEnabled(true);
        s.setLaw(f0, S, k, ref, maxCut);
        const double loud = std::pow(10.0, (ref + 24.0) / 20.0) * std::sqrt(2.0);
        for (double f : { 60.0, 200.0, 500.0 })
        {
            char buf[96];
            std::snprintf(buf, sizeof buf, "|gain| at %.0f Hz at full envelope (must be ~0)", f);
            near(buf, measureDb(s, fs, f, 0.05, loud), 0.0, 0.25);
        }
    }

    std::printf("\n=== Test 5: W3 (session 168) -- the env2-window fast path is a "
                "decision-for-decision match ===\n");
    {
        // Drives the SHIPPED (windowed) stage and the RefOdDriveTilt (pre-W3,
        // unconditional log10) reimplementation with an IDENTICAL input stream
        // and asserts every sample's output is bit-identical -- covering:
        //  (a) a slow ramp through the whole envelope range, crossing `ref`
        //      and the maxCut clamp boundary many times over;
        //  (b) a step from silence to loud and back (worst case for a burst
        //      of consecutive recomputes);
        //  (c) a random walk in envelope space (no designed structure to
        //      accidentally dodge a boundary case).
        // A single ULP-level mismatch at a threshold crossing would show up
        // as a nonzero `worst` below; the design argument (CLAUDE.md W3) is
        // that even such a mismatch is inaudible (it can only shift a
        // recompute by one sample, inside the hysteresis band already
        // budgeted), but this test asks for the stronger bar and expects to
        // meet it: EXACTLY zero.
        auto stress = [&](const char* label, std::function<double(int)> envAt, int n)
        {
            OdDriveTilt fast;
            RefOdDriveTilt slow;
            fast.prepare(fs);
            slow.prepare(fs);
            fast.setEnabled(true);
            fast.setLaw(f0, S, k, ref, maxCut);
            slow.setLaw(f0, S, k, ref, maxCut);

            double worst = 0.0;
            for (int i = 0; i < n; ++i)
            {
                const double t = i / fs;
                const double envAmp = envAt(i);
                const double sig = envAmp * std::sin(2.0 * M_PI * 220.0 * t)
                                  + 0.3 * envAmp * std::sin(2.0 * M_PI * 3000.0 * t);
                fast.observe(sig);
                slow.observe(sig);
                const double stimulus = 0.05 * std::sin(2.0 * M_PI * 2934.8 * t);
                const double yFast = fast.process(stimulus);
                const double ySlow = slow.process(stimulus);
                worst = std::max(worst, std::fabs(yFast - ySlow));
            }
            char buf[128];
            std::snprintf(buf, sizeof buf, "worst |fast - slow| output, %s", label);
            check(worst == 0.0, buf, worst, 0.0, 0.0);
            return worst;
        };

        // (a) slow ramp: envDb sweeps roughly -60 -> +20 dBV and back over 2 s,
        //     crossing `ref` (-33.9) and the clamp boundary (ref + maxCut/k,
        //     here about -4.3 dBV) on both the way up and the way down.
        stress("slow ramp crossing ref and the clamp boundary",
               [&](int i)
               {
                   const double frac = std::fmod(i / (fs * 2.0), 1.0);
                   const double envDb = -60.0 + 80.0 * (frac < 0.5 ? 2.0 * frac : 2.0 * (1.0 - frac));
                   return std::pow(10.0, envDb / 20.0) * std::sqrt(2.0);
               },
               (int) (fs * 2.0));

        // (b) instantaneous silence -> loud -> silence step (bursts of
        //     consecutive recomputes as the envelope races through the
        //     hysteresis band).
        stress("silence -> loud -> silence step",
               [&](int i)
               {
                   const int n = (int) (fs * 0.3);
                   const double envDb = (i > n / 3 && i < 2 * n / 3) ? 20.0 : -80.0;
                   return std::pow(10.0, envDb / 20.0) * std::sqrt(2.0);
               },
               (int) (fs * 0.3));

        // (c) a random walk in envDb space -- no designed structure, so any
        //     boundary-adjacent case the ramp/step happen to miss is still
        //     covered probabilistically.
        {
            std::mt19937 rng(12345);
            std::normal_distribution<double> step(0.0, 0.8);
            std::vector<double> envDbPath;
            double envDb = -20.0;
            const int n = (int) (fs * 0.5);
            envDbPath.reserve((size_t) n);
            for (int i = 0; i < n; ++i)
            {
                envDb = std::clamp(envDb + step(rng), -90.0, 30.0);
                envDbPath.push_back(envDb);
            }
            stress("random walk in envDb space",
                   [&](int i) { return std::pow(10.0, envDbPath[(size_t) i] / 20.0) * std::sqrt(2.0); },
                   n);
        }

        // The optimisation must actually BE a fast path, not merely a
        // correct no-op.  `recomputeCount()` -- how many times the biquad
        // (and, for `fast`, std::log10) actually ran -- must be IDENTICAL
        // between the two (same decisions, the correctness claim above
        // stated a second way with no output involved), AND small relative
        // to the sample count: the OLD stage called std::log10 once per
        // SAMPLE regardless (N calls) plus once more per recompute; the NEW
        // stage calls it only on a recompute (recomputeCount() calls) --
        // so recomputeCount() << N is the whole saving, made concrete.
        {
            OdDriveTilt fast;
            RefOdDriveTilt slow;
            fast.prepare(fs);
            slow.prepare(fs);
            fast.setEnabled(true);
            fast.setLaw(f0, S, k, ref, maxCut);
            slow.setLaw(f0, S, k, ref, maxCut);
            const int n = (int) (fs * 2.0);
            for (int i = 0; i < n; ++i)
            {
                const double t = i / fs;
                const double frac = std::fmod(i / (fs * 2.0), 1.0);
                const double envDb = -60.0 + 80.0 * (frac < 0.5 ? 2.0 * frac : 2.0 * (1.0 - frac));
                const double envAmp = std::pow(10.0, envDb / 20.0) * std::sqrt(2.0);
                const double sig = envAmp * std::sin(2.0 * M_PI * 220.0 * t);
                fast.observe(sig);
                slow.observe(sig);
                fast.process(0.05 * std::sin(2.0 * M_PI * 2934.8 * t));
                slow.process(0.05 * std::sin(2.0 * M_PI * 2934.8 * t));
            }
            std::printf("  recomputes over %d samples: fast=%llu  slow(reference)=%llu  "
                        "(old std::log10 calls ~= %d + %llu, new ~= %llu)\n",
                        n, (unsigned long long) fast.recomputeCount(),
                        (unsigned long long) slow.recomputeCount(), n,
                        (unsigned long long) slow.recomputeCount(),
                        (unsigned long long) fast.recomputeCount());
            check(fast.recomputeCount() == slow.recomputeCount(),
                  "recompute counts match exactly (identical decisions)",
                  (double) fast.recomputeCount(), (double) slow.recomputeCount(), 0.0);
            check(fast.recomputeCount() < (std::uint64_t) n / 100,
                  "std::log10 calls (== recomputes) are << N samples -- the actual saving",
                  (double) fast.recomputeCount(), (double) n, 0.0);
        }

        // Timing, REPORTED not gated (build.md: absolute ns/sample is machine-
        // and run-specific; only the within-run ratio is quotable, and ctest
        // parallelism can add noise -- this is context, not a bar).
        {
            OdDriveTilt fast;
            RefOdDriveTilt slow;
            fast.prepare(fs);
            slow.prepare(fs);
            fast.setEnabled(true);
            fast.setLaw(f0, S, k, ref, maxCut);
            slow.setLaw(f0, S, k, ref, maxCut);
            const int n = 4'000'000;
            std::vector<double> sig(n), stim(n);
            std::mt19937 rng(999);
            std::normal_distribution<double> walkStep(0.0, 0.5);
            double envDb = -20.0;
            for (int i = 0; i < n; ++i)
            {
                envDb = std::clamp(envDb + walkStep(rng), -80.0, 20.0);
                sig[(size_t) i] = std::pow(10.0, envDb / 20.0) * std::sqrt(2.0)
                                * std::sin(2.0 * M_PI * 220.0 * i / fs);
                stim[(size_t) i] = 0.05 * std::sin(2.0 * M_PI * 2934.8 * i / fs);
            }
            double sinkFast = 0.0, sinkSlow = 0.0;
            const auto t0 = std::chrono::steady_clock::now();
            for (int i = 0; i < n; ++i) { fast.observe(sig[(size_t) i]); sinkFast += fast.process(stim[(size_t) i]); }
            const auto t1 = std::chrono::steady_clock::now();
            for (int i = 0; i < n; ++i) { slow.observe(sig[(size_t) i]); sinkSlow += slow.process(stim[(size_t) i]); }
            const auto t2 = std::chrono::steady_clock::now();
            const double nsFast = std::chrono::duration<double, std::nano>(t1 - t0).count() / n;
            const double nsSlow = std::chrono::duration<double, std::nano>(t2 - t1).count() / n;
            std::printf("  timing (REPORTED, not gated): fast=%.2f ns/sample  slow(ref)=%.2f ns/sample  "
                        "(%.1f %% of the reference cost)  [sinks: %.6g %.6g]  "
                        "[recomputes over %d: fast=%llu slow=%llu]\n",
                        nsFast, nsSlow, 100.0 * nsFast / nsSlow, sinkFast, sinkSlow, n,
                        (unsigned long long) fast.recomputeCount(), (unsigned long long) slow.recomputeCount());
        }
    }

    std::printf("\n%s (%d failure%s)\n", failures ? "FAILED" : "PASSED", failures,
                failures == 1 ? "" : "s");
    return failures ? 1 : 0;
}
