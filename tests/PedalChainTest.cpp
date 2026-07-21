// PedalChainTest — integration smoke test for the assembled per-channel chain.
// Not a reference-accuracy test (that's Phase 7, vs captures): this asserts the
// full chain is STABLE and WELL-FORMED once wired together — finite & bounded
// output across every switch position and knob extreme, AC-coupled DC handling,
// and the net input→output polarity on the AC edge. The per-stage FR/oracle
// tests already validate each block; this guards the assembly + param mapping.
#include "../src/dsp/PedalChain.h"

#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

static int failures = 0;
static void check(bool cond, const std::string& msg)
{
    if (!cond)
    {
        std::printf("  FAIL: %s\n", msg.c_str());
        ++failures;
    }
}

static bool finite(double v) { return std::isfinite(v); }

int main()
{
    constexpr double fs = 48000.0;
    PedalChain chain;
    chain.prepare(fs, fs); // 1× (base-rate) run

    // ---- 1. Finite & bounded across every switch position + knob extreme -----
    // Rails are disabled (Phase-7 calibration), so DRIVE at ×78 into the clipper
    // can produce large internal volts — the bound is generous, we're catching
    // NaN/Inf/blow-up, not calibrating level.
    const std::vector<double> knobExtremes = {0.0, 0.5, 1.0};
    double globalPeak = 0.0;
    for (int atk = 0; atk < 3; ++atk)
        for (int gru = 0; gru < 3; ++gru)
            for (int lmf = 0; lmf < 3; ++lmf)
                for (int hmf = 0; hmf < 3; ++hmf)
                    for (double drv : knobExtremes)
                        for (double bl : knobExtremes)
                        {
                            PedalChain::Params p;
                            p.attackIdx = atk;
                            p.gruntIdx = gru;
                            p.loMidFreq = lmf;
                            p.hiMidFreq = hmf;
                            p.drive = drv;
                            p.blend = bl;
                            p.master = 1.0;
                            chain.reset();
                            chain.applyParams(p);

                            bool ok = true;
                            // 0.25 s of a 110 Hz bass tone at ~0.5 V.
                            for (int n = 0; n < (int) (0.25 * fs); ++n)
                            {
                                const double x = 0.5 * std::sin(2.0 * M_PI * 110.0 * n / fs);
                                const double y = chain.processSample(x);
                                if (!finite(y)) { ok = false; break; }
                                globalPeak = std::max(globalPeak, std::abs(y));
                            }
                            char buf[128];
                            std::snprintf(buf, sizeof buf,
                                          "finite output @ atk=%d grunt=%d lmf=%d hmf=%d drive=%.1f blend=%.1f",
                                          atk, gru, lmf, hmf, drv, bl);
                            check(ok, buf);
                        }
    check(globalPeak < 1.0e4, "global peak stays bounded (<1e4 V)");
    std::printf("  [info] global peak across sweep = %.3f V\n", globalPeak);

    // ---- 2. DC-block: a sustained DC input decays toward ~0 (AC-coupled) ------
    {
        PedalChain::Params p;
        p.blend = 1.0;   // full OD path
        p.drive = 0.3;
        p.master = 1.0;
        chain.reset();
        chain.applyParams(p);
        double y = 0.0;
        for (int n = 0; n < (int) (2.0 * fs); ++n) // 2 s of +1 V DC
            y = chain.processSample(1.0);
        check(std::abs(y) < 1.0e-2, "DC input decays to near-zero output (AC-coupled chain)");
    }

    // ---- 3. Net polarity on the AC edge (input→output through OD path) --------
    // Whole chain is net non-inverting (JFET− ∘ Clipper− = +, EQ 4 inversions =
    // +). A positive step's first AC transient at the output should be positive.
    // Use full OD (blend=1) so the clean tap doesn't dominate, and read the very
    // first non-trivial sample after a rising step from steady state.
    {
        PedalChain::Params p;
        p.blend = 1.0;
        p.drive = 0.2;
        p.master = 1.0;
        chain.reset();
        chain.applyParams(p);
        for (int n = 0; n < (int) (0.2 * fs); ++n) // settle at 0
            chain.processSample(0.0);
        double firstEdge = 0.0;
        for (int n = 0; n < 8; ++n) // first few samples of a +step
        {
            const double y = chain.processSample(0.2);
            if (std::abs(y) > 1.0e-6) { firstEdge = y; break; }
        }
        check(firstEdge > 0.0, "net non-inverting: +step → +going output edge");
        std::printf("  [info] first output edge for +step = %.5f V\n", firstEdge);
    }

    // ---- 4. dist_engage=false forces the clean tap (bounded, buffer-only) -----
    {
        PedalChain::Params p;
        p.distEngage = false;
        p.drive = 1.0; // would be huge if OD leaked through
        p.blend = 1.0;
        p.master = 1.0;
        chain.reset();
        chain.applyParams(p);
        double peak = 0.0;
        for (int n = 0; n < (int) (0.1 * fs); ++n)
        {
            const double x = 0.5 * std::sin(2.0 * M_PI * 220.0 * n / fs);
            peak = std::max(peak, std::abs(chain.processSample(x)));
        }
        check(finite(peak) && peak < 5.0,
              "dist_engage=false routes clean tap only (no OD blow-up)");
    }

    if (failures == 0)
        std::printf("PedalChainTest: PASS\n");
    else
        std::printf("PedalChainTest: %d FAILURE(S)\n", failures);
    return failures == 0 ? 0 : 1;
}
