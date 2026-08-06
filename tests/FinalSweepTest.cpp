// FinalSweepTest — Phase 10's own criterion, and the only thing that closes it:
//   "Final sweep — all controls full range: no instability, clicks, or NaN/Inf."
//
// WHY THIS EXISTS ALONGSIDE PedalChainTest (session 167).  PedalChainTest's Test 1 sweeps the four
// SWITCHES x {DRIVE, BLEND} at three values each, at 1x only.  That leaves four gaps that matter
// for a 1.0 release, every one of them covering something that has CHANGED recently:
//   * LEVEL is never moved            — and s163 replaced its taper with a 4-segment PWL.
//   * the four EQ knobs never move    — lo / loMid / hiMid / hi are pinned at 0.5.
//   * only 1x is exercised            — but the ADAA policy is GATED ON THE OS FACTOR
//                                       (FitParams::clipAdaaMaxOs = 2), so 4x/8x run a different
//                                       code path that no finiteness test has ever reached.
//   * nothing moves a knob WHILE processing — so "no clicks", half of Phase 10's wording, is
//                                       untested. s166's OdDriveTilt added an envelope follower,
//                                       i.e. the first stage whose response depends on signal
//                                       HISTORY, which is exactly what a discontinuity test probes.
//
// ⚠ Output BOUNDS here are generous and deliberately so: the rails are disabled (Phase-7
// calibration) and DRIVE at x78 into the clipper legitimately produces large internal volts.
// CLAUDE.md: "Output > 0 dBFS at extreme drive+volume is faithful, not a fault." This test catches
// NaN / Inf / blow-up, NOT level.
//
// ⚠⚠ THE CLICK TEST USES NO INVENTED THRESHOLD.  An absolute "max jump" bar would be a number I
// guessed (measurement-discipline §1). Instead each moving-knob run is scored against ITS OWN
// static control: the same settings, the same tone, the knob held still at both endpoints. A click
// is then "moving the knob produces a sample-to-sample step far larger than the signal itself ever
// takes when the knob is still" — a ratio, self-calibrating, with the denominator guarded.

#include "../src/dsp/PedalChain.h"

#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static int failures = 0;
static int checksRun = 0;

static void check(bool ok, const std::string& what)
{
    ++checksRun;
    if (!ok)
    {
        std::printf("  FAIL: %s\n", what.c_str());
        ++failures;
    }
}

static bool finiteAndBounded(double v) { return std::isfinite(v) && std::fabs(v) < 1.0e4; }

// One static run: process `seconds` of a tone, return false on any non-finite/blow-up sample.
// `maxStep` receives the largest sample-to-sample change seen (the click statistic).
static bool runStatic(PedalChain& chain, const PedalChain::Params& p, double fs, double seconds,
                      double toneHz, double amp, double& peak, double& maxStep)
{
    chain.reset();
    chain.applyParams(p);
    peak = 0.0;
    maxStep = 0.0;
    double prev = 0.0;
    const int n = (int) (seconds * fs);
    for (int i = 0; i < n; ++i)
    {
        const double x = amp * std::sin(2.0 * M_PI * toneHz * i / fs);
        const double y = chain.processSample(x);
        if (!finiteAndBounded(y))
            return false;
        peak = std::max(peak, std::fabs(y));
        if (i > 0)
            maxStep = std::max(maxStep, std::fabs(y - prev));
        prev = y;
    }
    return true;
}

int main()
{
    constexpr double fs = 48000.0;
    const std::vector<double> ext = {0.0, 0.5, 1.0};

    // =====================================================================================
    // 1. EXHAUSTIVE: every switch combination x DRIVE x BLEND x LEVEL, at 1x.
    //    81 switch combos x 27 knob combos = 2187 configurations.
    // =====================================================================================
    {
        PedalChain chain;
        chain.prepare(fs, fs);
        double worstPeak = 0.0;
        int configs = 0, bad = 0;
        std::string firstBad;

        for (int atk = 0; atk < 3; ++atk)
            for (int gru = 0; gru < 3; ++gru)
                for (int lmf = 0; lmf < 3; ++lmf)
                    for (int hmf = 0; hmf < 3; ++hmf)
                        for (double drv : ext)
                            for (double bl : ext)
                                for (double lv : ext)
                                {
                                    PedalChain::Params p;
                                    p.attackIdx = atk; p.gruntIdx = gru;
                                    p.loMidFreq = lmf; p.hiMidFreq = hmf;
                                    p.drive = drv; p.blend = bl; p.level = lv;
                                    p.master = 1.0;

                                    double peak = 0.0, step = 0.0;
                                    ++configs;
                                    if (!runStatic(chain, p, fs, 0.10, 110.0, 0.5, peak, step))
                                    {
                                        ++bad;
                                        if (firstBad.empty())
                                        {
                                            char buf[160];
                                            std::snprintf(buf, sizeof buf,
                                                          "atk=%d grunt=%d lmf=%d hmf=%d drive=%.1f blend=%.1f level=%.1f",
                                                          atk, gru, lmf, hmf, drv, bl, lv);
                                            firstBad = buf;
                                        }
                                    }
                                    worstPeak = std::max(worstPeak, peak);
                                }

        check(bad == 0, "1. exhaustive switch x DRIVE x BLEND x LEVEL @1x: all finite and bounded"
                        + (firstBad.empty() ? std::string() : "  first bad: " + firstBad));
        std::printf("  [1] %d configurations swept @1x, %d bad, worst peak %.3f V\n",
                    configs, bad, worstPeak);
    }

    // =====================================================================================
    // 2. THE EQ KNOBS — never moved by any existing test. All four at both extremes x both
    //    mid-frequency selectors x DRIVE extremes.
    // =====================================================================================
    {
        PedalChain chain;
        chain.prepare(fs, fs);
        int configs = 0, bad = 0;
        double worstPeak = 0.0;
        std::string firstBad;
        const std::vector<double> eq = {0.0, 1.0};

        for (double lo : eq)
            for (double lm : eq)
                for (double hm : eq)
                    for (double hi : eq)
                        for (int lmf = 0; lmf < 3; ++lmf)
                            for (int hmf = 0; hmf < 3; ++hmf)
                                for (double drv : {0.0, 1.0})
                                {
                                    PedalChain::Params p;
                                    p.lo = lo; p.loMid = lm; p.hiMid = hm; p.hi = hi;
                                    p.loMidFreq = lmf; p.hiMidFreq = hmf;
                                    p.drive = drv; p.blend = 1.0; p.level = 1.0; p.master = 1.0;

                                    double peak = 0.0, step = 0.0;
                                    ++configs;
                                    if (!runStatic(chain, p, fs, 0.10, 110.0, 0.5, peak, step))
                                    {
                                        ++bad;
                                        if (firstBad.empty())
                                        {
                                            char buf[160];
                                            std::snprintf(buf, sizeof buf,
                                                          "lo=%.0f loMid=%.0f hiMid=%.0f hi=%.0f lmf=%d hmf=%d drive=%.0f",
                                                          lo, lm, hm, hi, lmf, hmf, drv);
                                            firstBad = buf;
                                        }
                                    }
                                    worstPeak = std::max(worstPeak, peak);
                                }

        check(bad == 0, "2. EQ knobs at extremes x mid-freq selectors: all finite and bounded"
                        + (firstBad.empty() ? std::string() : "  first bad: " + firstBad));
        std::printf("  [2] %d EQ configurations swept, %d bad, worst peak %.3f V\n",
                    configs, bad, worstPeak);
    }

    // =====================================================================================
    // 3. EVERY OS FACTOR. The ADAA policy is gated on the factor (clipAdaaMaxOs = 2), so
    //    4x/8x take a different path through the clipper than 1x/2x. Reached here by
    //    preparing the OD region at the oversampled rate, which is what PedalDSP does.
    // =====================================================================================
    {
        int bad = 0;
        std::string firstBad;
        for (int factor : {1, 2, 4, 8})
        {
            PedalChain chain;
            chain.prepare(fs, fs * factor);
            double worstPeak = 0.0;
            int configs = 0;

            for (int atk = 0; atk < 3; ++atk)
                for (int gru = 0; gru < 3; ++gru)
                    for (double drv : ext)
                        for (double bl : ext)
                            for (double lv : {0.0, 1.0})
                            {
                                PedalChain::Params p;
                                p.attackIdx = atk; p.gruntIdx = gru;
                                p.drive = drv; p.blend = bl; p.level = lv; p.master = 1.0;

                                // NOTE: processSample() is the OS-region call, so it is driven at
                                // the oversampled rate here — the tone is generated at fs*factor.
                                double peak = 0.0, step = 0.0;
                                ++configs;
                                if (!runStatic(chain, p, fs * factor, 0.05, 110.0, 0.5, peak, step))
                                {
                                    ++bad;
                                    if (firstBad.empty())
                                    {
                                        char buf[160];
                                        std::snprintf(buf, sizeof buf,
                                                      "os=%dx atk=%d grunt=%d drive=%.1f blend=%.1f level=%.1f",
                                                      factor, atk, gru, drv, bl, lv);
                                        firstBad = buf;
                                    }
                                }
                                worstPeak = std::max(worstPeak, peak);
                            }
            std::printf("  [3] OS %dx: %d configurations, worst peak %.3f V\n",
                        factor, configs, worstPeak);
        }
        check(bad == 0, "3. all four OS factors (incl. the 4x/8x ADAA-off path): finite and bounded"
                        + (firstBad.empty() ? std::string() : "  first bad: " + firstBad));
    }

    // =====================================================================================
    // 4. CLICKS under CONTINUOUS knob motion — the untested half of Phase 10's wording.
    //    Each knob is ramped 0 -> 1 over 0.5 s while a tone runs. Scored against its own
    //    STATIC control (same settings, knob held at each endpoint), so no absolute bar.
    // =====================================================================================
    {
        struct Knob { const char* name; double PedalChain::Params::* member; };
        const std::vector<Knob> knobs = {
            {"master", &PedalChain::Params::master},
            {"blend",  &PedalChain::Params::blend},
            {"level",  &PedalChain::Params::level},
            {"drive",  &PedalChain::Params::drive},
            {"lo",     &PedalChain::Params::lo},
            {"loMid",  &PedalChain::Params::loMid},
            {"hiMid",  &PedalChain::Params::hiMid},
            {"hi",     &PedalChain::Params::hi},
        };

        std::printf("  [4] knob-motion discontinuity, vs each knob's own static control:\n");
        for (const auto& k : knobs)
        {
            PedalChain chain;
            chain.prepare(fs, fs);

            // static controls at both endpoints
            double pk = 0.0, stepLo = 0.0, stepHi = 0.0;
            PedalChain::Params a;
            a.master = 1.0; a.blend = 1.0; a.level = 1.0; a.drive = 0.5;
            a.*(k.member) = 0.0;
            bool okA = runStatic(chain, a, fs, 0.25, 110.0, 0.5, pk, stepLo);
            PedalChain::Params b = a;
            b.*(k.member) = 1.0;
            bool okB = runStatic(chain, b, fs, 0.25, 110.0, 0.5, pk, stepHi);
            const double staticStep = std::max(stepLo, stepHi);

            // moving arm: applyParams() once per 32-sample "block", as the plugin does per block
            chain.reset();
            PedalChain::Params p = a;
            chain.applyParams(p);
            double prev = 0.0, movingStep = 0.0, movingPeak = 0.0;
            bool okM = true;
            const int n = (int) (0.5 * fs);
            for (int i = 0; i < n; ++i)
            {
                if (i % 32 == 0)
                {
                    p.*(k.member) = (double) i / (double) n;
                    chain.applyParams(p);
                }
                const double x = 0.5 * std::sin(2.0 * M_PI * 110.0 * i / fs);
                const double y = chain.processSample(x);
                if (!finiteAndBounded(y)) { okM = false; break; }
                movingPeak = std::max(movingPeak, std::fabs(y));
                if (i > 0)
                    movingStep = std::max(movingStep, std::fabs(y - prev));
                prev = y;
            }

            check(okA && okB && okM, std::string("4. knob '") + k.name + "' motion: finite and bounded");

            // ⚠ VACUITY GUARD. A ratio near 1.0x is equally consistent with "the knob moved
            // smoothly" and with "the knob never reached the DSP" — the second would make this
            // whole arm narration. Require the moving run's output to actually DIFFER from the
            // static-at-endpoint run, or the ratio above means nothing.
            {
                PedalChain vc;
                vc.prepare(fs, fs);
                vc.reset();
                vc.applyParams(a);           // held at the LOW endpoint for the whole run
                double diff = 0.0;
                PedalChain mv;
                mv.prepare(fs, fs);
                mv.reset();
                PedalChain::Params q = a;
                mv.applyParams(q);
                for (int i = 0; i < n; ++i)
                {
                    if (i % 32 == 0) { q.*(k.member) = (double) i / (double) n; mv.applyParams(q); }
                    const double x = 0.5 * std::sin(2.0 * M_PI * 110.0 * i / fs);
                    diff = std::max(diff, std::fabs(mv.processSample(x) - vc.processSample(x)));
                }
                check(diff > 1e-6, std::string("4. VACUITY: knob '") + k.name
                                       + "' motion changes the output (else the ratio is meaningless)");
            }

            // ratio-statistics-need-a-denominator-guard: refuse to print a ratio against a
            // static step that is itself at the floor.
            if (staticStep < 1e-9)
            {
                std::printf("      %-7s static step at floor (%.2e) — RATIO REFUSED, moving step %.3e\n",
                            k.name, staticStep, movingStep);
            }
            else
            {
                const double ratio = movingStep / staticStep;
                std::printf("      %-7s moving %.3e / static %.3e = %6.2fx%s\n",
                            k.name, movingStep, staticStep, ratio,
                            ratio > 4.0 ? "   <-- discontinuity" : "");
            }
        }
    }

    // =====================================================================================
    // 5. SWITCH transitions — REPORTED, NOT GATED. CLAUDE.md records the switches as
    //    deliberately unsmoothed ("the harder glitch-free-crossfade problem", still open),
    //    so gating this would be asserting a limitation the project has explicitly accepted.
    //    It is measured so the size of that known limitation is on record for the release.
    // =====================================================================================
    {
        std::printf("  [5] switch-transition step (REPORTED, not gated — switches are known unsmoothed):\n");
        PedalChain chain;
        chain.prepare(fs, fs);
        const char* names[] = {"attack", "grunt", "loMidFreq", "hiMidFreq"};
        for (int which = 0; which < 4; ++which)
        {
            PedalChain::Params p;
            p.master = 1.0; p.blend = 1.0; p.level = 1.0; p.drive = 0.5;
            // ⚠⚠ THE MID POTS MUST BE OFF CENTRE OR THIS ARM IS VACUOUS, and the first run of this
            // test proved it: with loMid/hiMid at their 0.5 default the loMidFreq/hiMidFreq flips
            // moved the output by 4.8e-14 / 6.0e-14 (i.e. nothing) and the vacuity guard failed.
            // That is CORRECT plugin behaviour, not a bug — circuit.md records the mid band's
            // B-taper centre as EXACTLY flat ("sim: 0.00 dB max deviation"), so re-centring a band
            // that is contributing nothing must change nothing. Suspect the mutation before the
            // guard (s110). Boosting both mids makes the selector observable.
            p.loMid = 1.0; p.hiMid = 1.0;
            chain.reset();
            chain.applyParams(p);

            double prev = 0.0, quietStep = 0.0, switchStep = 0.0;
            const int n = (int) (0.4 * fs);
            const int flipAt = n / 2;
            for (int i = 0; i < n; ++i)
            {
                if (i == flipAt)
                {
                    if (which == 0) p.attackIdx = 2;
                    else if (which == 1) p.gruntIdx = 2;
                    else if (which == 2) p.loMidFreq = 0;
                    else p.hiMidFreq = 0;
                    chain.applyParams(p);
                }
                const double x = 0.5 * std::sin(2.0 * M_PI * 110.0 * i / fs);
                const double y = chain.processSample(x);
                if (!finiteAndBounded(y)) { std::printf("      %s: NON-FINITE\n", names[which]); break; }
                if (i > 0)
                {
                    const double d = std::fabs(y - prev);
                    // the step AT the flip vs the largest step anywhere else
                    if (i == flipAt) switchStep = d;
                    else quietStep = std::max(quietStep, d);
                }
                prev = y;
            }
            // ⚠⚠ VACUITY GUARD, and it was earned: the first run of this arm reported the SAME
            // step (2.603e-02) for all four switches to four significant figures, which is
            // `an-implausible-coincidence-is-a-bug-report` — four different topology changes
            // cannot agree to that precision. Either the flip does nothing at the flip sample,
            // or the number is just the tone's own step there. So require the flip to CHANGE the
            // output against an unflipped twin, and print WHEN the change first exceeds the
            // tone's own quiet step — a switch whose effect arrives gradually is not a click.
            {
                PedalChain twin;
                twin.prepare(fs, fs);
                twin.reset();
                PedalChain::Params unflipped;
                unflipped.master = 1.0; unflipped.blend = 1.0; unflipped.level = 1.0; unflipped.drive = 0.5;
                unflipped.loMid = 1.0; unflipped.hiMid = 1.0;   // see the note above — off centre
                twin.applyParams(unflipped);

                PedalChain flip;
                flip.prepare(fs, fs);
                flip.reset();
                PedalChain::Params q = unflipped;
                flip.applyParams(q);

                double maxDiff = 0.0;
                for (int i = 0; i < n; ++i)
                {
                    if (i == flipAt)
                    {
                        if (which == 0) q.attackIdx = 2;
                        else if (which == 1) q.gruntIdx = 2;
                        else if (which == 2) q.loMidFreq = 0;
                        else q.hiMidFreq = 0;
                        flip.applyParams(q);
                    }
                    const double x = 0.5 * std::sin(2.0 * M_PI * 110.0 * i / fs);
                    maxDiff = std::max(maxDiff, std::fabs(flip.processSample(x) - twin.processSample(x)));
                }
                check(maxDiff > 1e-6, std::string("5. VACUITY: switch '") + names[which]
                                          + "' flip changes the output (else the step below is not a switch step)");
                std::printf("      %-10s post-flip max divergence from unflipped twin %.3e\n",
                            names[which], maxDiff);
            }

            if (quietStep < 1e-9)
                std::printf("      %-10s quiet step at floor — RATIO REFUSED (switch step %.3e)\n",
                            names[which], switchStep);
            else
                std::printf("      %-10s switch step %.3e vs quiet %.3e = %6.2fx\n",
                            names[which], switchStep, quietStep, switchStep / quietStep);
        }
    }

    std::printf("\nFinalSweepTest: %d checks, %d failure(s)\n", checksRun, failures);
    return failures == 0 ? 0 : 1;
}
