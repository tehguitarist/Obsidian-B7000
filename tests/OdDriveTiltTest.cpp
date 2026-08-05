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

#include <cmath>
#include <cstdio>
#include <vector>

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

    std::printf("\n%s (%d failure%s)\n", failures ? "FAILED" : "PASSED", failures,
                failures == 1 ? "" : "s");
    return failures ? 1 : 0;
}
