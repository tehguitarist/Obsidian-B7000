// clean_rail_probe — Phase 9 item A5, session 41: WHICH op-amp on the DIST-off
// clean path actually reaches its rail, and by how much?
//
// Session 39 confirmed the defect (the clean chain breaks up between -12 and -9 dBFS
// where the pedal is at its floor at every rung down to -3) and A/B-confirmed the
// cause as the RailClamp, but never localised it: "EqPreGain first suspect" was an
// arithmetic guess, not a measurement. This probe measures it.
//
// Method — the whole point is that with the clamps DISABLED the clean path is
// exactly LINEAR (LevelBlend returns cleanIn unmodified when distEngage=false;
// C21/Baxandall/mids/MasterOut are linear networks; EqPreGain is a flat -2.2), so
// every tap is the voltage that op-amp WOULD have to swing. Then:
//
//   onset(node) = probe level x min(railPos/peakPos, railNeg/peakNeg)
//
// is the exact input level at which that node first touches its rail — one render
// at ONE level gives the onset for every node at once, and the node with the
// LOWEST onset is the offender. Measured at a level far below any clamp so the
// linearity the formula assumes actually holds (asserted below, not assumed).
//
// Rails are asymmetric (railPos 2.7 / railNeg 2.9, session 21) and the chain has an
// odd number of inversions at some nodes, so the two polarities are tracked
// separately rather than using |peak|.
//
// Build (NOT a CMake target — like a3_blend_decompose, so `cmake --build` will NOT
// rebuild it when FitParams.h changes; rebuild it by hand after any such edit,
// session-37 trap):
//   c++ -std=c++17 -O2 -o build/clean_rail_probe analysis/clean_rail_probe.cpp
//
// Usage: build/clean_rail_probe [freqHz]        (default 1000 — the lvl_ ladder tone)
#include "../src/dsp/PedalChain.h"
#include "../src/dsp/FitParams.h"
#include "../src/dsp/GainStaging.h"
#include <cstdio>
#include <cmath>
#include <cstring>
#include <string>
#include <vector>

static constexpr double kPi = 3.14159265358979323846;

struct Case
{
    const char* name;
    double lo, loMid, hiMid, hi, master; // knob space (0..1), 0.5 = flat/centre
};

// The clean captures session 39 confirmed the defect on: flat EQ plus each single
// band at full boost, plus MASTER max (least downstream attenuation).
static const Case kCases[] = {
    {"flat EQ (ref-clean)", 0.5, 0.5, 0.5, 0.5, 1.0},
    {"BASS max",            1.0, 0.5, 0.5, 0.5, 1.0},
    {"TREBLE max",          0.5, 0.5, 0.5, 1.0, 1.0},
    {"LO-MID max",          0.5, 1.0, 0.5, 0.5, 1.0},
    {"HI-MID max",          0.5, 0.5, 1.0, 0.5, 1.0},
    {"ALL EQ max",          1.0, 1.0, 1.0, 1.0, 1.0},
};

struct NodePeaks
{
    double pos = 0.0, neg = 0.0; // most-positive and most-negative excursion (volts re VD)
};

static const char* kNodeNames[] = {
    "BLEND wiper", "C21 out", "IC5_B (EqPreGain -2.2)", "IC5_C (Baxandall)",
    "IC5_D (LO-MID)", "IC6_A (HI-MID)", "OUT (post-C37)"
};
static constexpr int kNumNodes = 7;
// Which taps are actual OP-AMP OUTPUTS carrying a RailClamp (the others are passive
// nodes — BLEND is a resistive wiper, C21 a coupling cap, OUT is post-C37).
static const bool kIsOpAmpOut[kNumNodes] = {false, false, true, true, true, true, false};

int main(int argc, char** argv)
{
    const double freq = (argc > 1) ? std::atof(argv[1]) : 1000.0;
    const double fs = 48000.0;
    const double kInputRef = GainStaging::kInputRefNominal;

    FitParams fpOff {};
    fpOff.railEnabled = false; // <- the whole method: measure the UNCLAMPED swing
    const double railPos = fpOff.railPos, railNeg = fpOff.railNeg;

    // Probe level: far below any clamp so the linear scaling the onset formula uses
    // is real. -40 dBFS is 4 rungs under the ladder's own bottom.
    const double probeDb = -40.0;
    const double amp = kInputRef * std::pow(10.0, probeDb / 20.0);

    std::printf("clean_rail_probe — DIST OFF, %g Hz, rails DISABLED (unclamped swing)\n", freq);
    std::printf("kInputRef = %.4f V/FS   rail window = [-%.2f, +%.2f] V re VD   probe = %.0f dBFS\n\n",
                kInputRef, railNeg, railPos, probeDb);

    for (const auto& c : kCases)
    {
        PedalChain ch;
        ch.prepare(fs, fs);
        ch.setFitParams(fpOff);
        PedalChain::Params p;
        p.blend = 1.0; p.level = 0.5; p.drive = 0.5;
        p.master = c.master; p.lo = c.lo; p.loMid = c.loMid; p.hiMid = c.hiMid; p.hi = c.hi;
        p.attackIdx = 0; p.gruntIdx = 1;
        p.distEngage = false; // <- the clean (DIST-off) path under test
        ch.applyParams(p);

        const int nWarm = (int) (fs * 1.0), nMeas = (int) (fs * 0.25);
        NodePeaks pk[kNumNodes];
        for (int n = 0; n < nWarm + nMeas; ++n)
        {
            const double x = amp * std::sin(2.0 * kPi * freq * (double) n / fs);
            const double buf = ch.runInputBuffer(x);
            const double od = ch.runOdSample(buf); // still runs (discarded by LevelBlend)
            const auto t = ch.processPostBlendTapped(buf, od);
            if (n < nWarm)
                continue;
            const double v[kNumNodes] = {t.blend, t.c21, t.eqPre, t.baxandall, t.loMid, t.hiMid, t.master};
            for (int i = 0; i < kNumNodes; ++i)
            {
                if (v[i] > pk[i].pos) pk[i].pos = v[i];
                if (v[i] < pk[i].neg) pk[i].neg = v[i];
            }
        }

        std::printf("---- %s ----\n", c.name);
        std::printf("  %-24s %9s %9s %10s %12s %10s\n",
                    "node", "V+ pk", "V- pk", "gain(dB)", "onset dBFS", "verdict");
        double worstOnset = 1e9;
        std::string worstNode;
        for (int i = 0; i < kNumNodes; ++i)
        {
            // Cumulative gain of this node re the input, at the probe frequency.
            const double gainDb = 20.0 * std::log10(std::max(pk[i].pos, -pk[i].neg) / amp + 1e-30);
            if (!kIsOpAmpOut[i])
            {
                std::printf("  %-24s %9.4f %9.4f %10.2f %12s %10s\n",
                            kNodeNames[i], pk[i].pos, pk[i].neg, gainDb, "-", "(passive)");
                continue;
            }
            // Headroom: how much the probe level can rise before this node clips.
            const double hPos = railPos / (pk[i].pos + 1e-30);
            const double hNeg = railNeg / (-pk[i].neg + 1e-30);
            const double head = std::min(hPos, hNeg);
            const double onsetDb = probeDb + 20.0 * std::log10(head);
            const char* side = (hPos < hNeg) ? "+" : "-";
            if (onsetDb < worstOnset) { worstOnset = onsetDb; worstNode = kNodeNames[i]; }
            std::printf("  %-24s %9.4f %9.4f %10.2f %12.2f %10s\n",
                        kNodeNames[i], pk[i].pos, pk[i].neg, gainDb, onsetDb,
                        (onsetDb < -3.0) ? (std::string("RAILS ") + side).c_str() : "ok");
        }
        std::printf("  => first to rail: %s at %.2f dBFS", worstNode.c_str(), worstOnset);
        if (worstOnset < -3.0)
            std::printf("   [DEFECT: the pedal is clean at -3 dBFS, i.e. %.2f dB of missing headroom]",
                        -3.0 - worstOnset);
        std::printf("\n");
        // The kInputRef that would put this case's onset exactly at -3 dBFS.
        std::printf("     kInputRef bound from this case: %.3f V/FS (shipped %.3f)\n\n",
                    kInputRef * std::pow(10.0, (worstOnset - (-3.0)) / 20.0), kInputRef);
    }

    // ---- Linearity assertion: the onset formula above is only valid if the probe
    // level is genuinely in the linear region. Re-run flat EQ 12 dB lower and check
    // every node's gain is unchanged.
    {
        PedalChain ch;
        ch.prepare(fs, fs);
        ch.setFitParams(fpOff);
        PedalChain::Params p;
        p.blend = 1.0; p.level = 0.5; p.drive = 0.5; p.master = 1.0;
        p.lo = p.loMid = p.hiMid = p.hi = 0.5;
        p.attackIdx = 0; p.gruntIdx = 1; p.distEngage = false;
        ch.applyParams(p);
        const double amp2 = amp * std::pow(10.0, -12.0 / 20.0);
        const int nWarm = (int) (fs * 1.0), nMeas = (int) (fs * 0.25);
        NodePeaks pk[kNumNodes];
        for (int n = 0; n < nWarm + nMeas; ++n)
        {
            const double x = amp2 * std::sin(2.0 * kPi * freq * (double) n / fs);
            const double buf = ch.runInputBuffer(x);
            const auto t = ch.processPostBlendTapped(buf, ch.runOdSample(buf));
            if (n < nWarm) continue;
            const double v[kNumNodes] = {t.blend, t.c21, t.eqPre, t.baxandall, t.loMid, t.hiMid, t.master};
            for (int i = 0; i < kNumNodes; ++i)
            {
                if (v[i] > pk[i].pos) pk[i].pos = v[i];
                if (v[i] < pk[i].neg) pk[i].neg = v[i];
            }
        }
        double worst = 0.0;
        for (int i = 0; i < kNumNodes; ++i)
        {
            const double g = 20.0 * std::log10(std::max(pk[i].pos, -pk[i].neg) / amp2 + 1e-30);
            (void) g;
        }
        // Recompute flat-EQ gains at the probe level for the comparison.
        PedalChain ch2;
        ch2.prepare(fs, fs);
        ch2.setFitParams(fpOff);
        ch2.applyParams(p);
        NodePeaks pk1[kNumNodes];
        for (int n = 0; n < nWarm + nMeas; ++n)
        {
            const double x = amp * std::sin(2.0 * kPi * freq * (double) n / fs);
            const double buf = ch2.runInputBuffer(x);
            const auto t = ch2.processPostBlendTapped(buf, ch2.runOdSample(buf));
            if (n < nWarm) continue;
            const double v[kNumNodes] = {t.blend, t.c21, t.eqPre, t.baxandall, t.loMid, t.hiMid, t.master};
            for (int i = 0; i < kNumNodes; ++i)
            {
                if (v[i] > pk1[i].pos) pk1[i].pos = v[i];
                if (v[i] < pk1[i].neg) pk1[i].neg = v[i];
            }
        }
        for (int i = 0; i < kNumNodes; ++i)
        {
            const double g1 = 20.0 * std::log10(std::max(pk1[i].pos, -pk1[i].neg) / amp + 1e-30);
            const double g2 = 20.0 * std::log10(std::max(pk[i].pos, -pk[i].neg) / amp2 + 1e-30);
            worst = std::max(worst, std::fabs(g1 - g2));
        }
        std::printf("SELF-TEST (linearity of the unclamped path, probe vs probe-12 dB): worst node-gain\n"
                    "  difference %.6f dB  =>  %s\n", worst,
                    (worst < 1e-6) ? "PASS — the onset scaling is exact"
                                   : "FAIL — the clean path is not linear with rails off");
    }
    return 0;
}
