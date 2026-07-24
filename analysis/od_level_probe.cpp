// od_level_probe — session 20 (Phase 9, A3/GAP #3): does the plugin's OD path
// get BASS-HEAVIER as it is driven harder?
//
// The A3 signature (session 20): the plugin-vs-pedal low-vs-mid TILT is ~1 dB at
// drive-min/GRUNT-cut but 20-37 dB at high drive or GRUNT flat/boost — i.e. it is
// a CLIPPING-REGIME effect, not a linear-filter error. The suspected mechanism is
// the clipper's shunt-feedback input impedance: node W sees the GRUNT cap in
// series with R16 into R18/(1+A_eff). When the VTC saturates, A_eff collapses, so
// Zin rises toward the full R18 (330k vs 12.7k at A0=26) and the GRUNT high-pass
// corner falls by that same factor — admitting sub-bass that the small-signal
// corner would have blocked.
//
// This probe measures the OD chain's cumulative transfer at ONE tap (skA, the end
// of the OD path feeding LEVEL/BLEND) over an amplitude ladder, so the shape's
// level-dependence is directly visible. If the LF/mid balance shifts with level in
// the model, the mechanism is live; if it does not, the clipper Zin story is dead
// and A3 must be looked for elsewhere.
//
// usage: od_level_probe [gruntIdx 0=Boost 1=Cut 2=Flat] [drive 0..1] [dampR ohms] [railEnabled 0/1] [railV]
#include "../src/dsp/PedalChain.h"
#include "../src/dsp/FitParams.h"
#include "../src/dsp/GainStaging.h"
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <complex>
#include <vector>

static constexpr double kPi = 3.14159265358979323846;

static std::complex<double> goertzel(const std::vector<double>& y, double f, double fs)
{
    std::complex<double> acc {0.0, 0.0};
    const double w = 2.0 * kPi * f / fs;
    for (size_t n = 0; n < y.size(); ++n)
        acc += y[n] * std::exp(std::complex<double>(0.0, -w * (double) n));
    return acc * (2.0 / (double) y.size());
}

int main(int argc, char** argv)
{
    const int gruntArg = (argc > 1) ? std::atoi(argv[1]) : 1; // default CUT
    const double driveArg = (argc > 2) ? std::atof(argv[2]) : 0.5;
    const double dampR = (argc > 3) ? std::atof(argv[3]) : 30000.0;
    const bool railOn = (argc > 4) ? (std::atoi(argv[4]) != 0) : false;
    const double railV = (argc > 5) ? std::atof(argv[5]) : 3.3;
    const double fs = 48000.0;
    const double kInputRef = GainStaging::kInputRefNominal;

    const double levelsDbfs[] = {-60, -48, -36, -30, -24, -18, -12, -6};
    const double freqs[] = {25, 40, 63, 100, 160, 254, 400, 640, 1000, 1600};
    const char* gname = gruntArg == 0 ? "BOOST" : gruntArg == 1 ? "CUT" : "FLAT";

    std::printf("OD path (skA tap) transfer |skA/buf| dB — grunt=%s drive=%.2f dampR=%.0f rail=%s(%.2fV) kInputRef=%.3f\n",
                gname, driveArg, dampR, railOn ? "ON" : "off", railV, kInputRef);
    std::printf("%8s", "dBFS");
    for (double f : freqs)
        std::printf("%8.0f", f);
    std::printf("%10s\n", "LF-mid");

    const int nWarm = (int) (fs * 0.5), nMeas = (int) (fs * 0.5);

    for (double dbfs : levelsDbfs)
    {
        const double amp = kInputRef * std::pow(10.0, dbfs / 20.0);
        std::printf("%8.0f", dbfs);
        double lf = 0.0, mid = 0.0;
        int nlf = 0, nmid = 0;
        for (double f : freqs)
        {
            PedalChain ch;
            ch.prepare(fs, fs);
            FitParams fp {};
            fp.trebleLadderDampR = dampR;
            fp.railEnabled = railOn;
            fp.railNeg = fp.railPos = railV;
            ch.setFitParams(fp);
            PedalChain::Params p;
            p.drive = driveArg; p.blend = 1.0; p.level = 0.5; p.master = 0.5;
            p.lo = p.loMid = p.hiMid = p.hi = 0.5;
            p.attackIdx = 1; p.gruntIdx = gruntArg; p.distEngage = true;
            ch.applyParams(p);

            const double w = 2.0 * kPi * f / fs;
            std::vector<double> in, sa;
            for (int n = 0; n < nWarm + nMeas; ++n)
            {
                const double x = amp * std::sin(w * (double) n);
                const double buf = ch.runInputBuffer(x);
                auto t = ch.runOdSampleTapped(buf);
                if (n >= nWarm) { in.push_back(buf); sa.push_back(t.skA); }
            }
            const double inMag = std::abs(goertzel(in, f, fs));
            const double db = 20.0 * std::log10(std::max(std::abs(goertzel(sa, f, fs)) / std::max(inMag, 1e-12), 1e-9));
            std::printf("%8.2f", db);
            if (f <= 63.0) { lf += db; ++nlf; }
            if (f >= 254.0 && f <= 1600.0) { mid += db; ++nmid; }
        }
        std::printf("%10.2f\n", lf / nlf - mid / nmid);
    }
    return 0;
}
