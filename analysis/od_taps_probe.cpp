// od_taps_probe — session 19 (Phase 9): localise WHICH OD stage scoops the
// low-mids (100-400 Hz). Measures the cumulative transfer |tap|/|input| in dB at
// each OD boundary (jfet, treble, drive, clipper, recovery, skB, skA) vs freq,
// at drive-min (near-linear). The pedal's OD has a low-mid bump ~180 Hz; the
// plugin peaks ~60 Hz. This shows the stage that flattens/notches the low-mids.
#include "../src/dsp/PedalChain.h"
#include "../src/dsp/FitParams.h"
#include "../src/dsp/GainStaging.h"
#include <cstdio>
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
    const int gruntArg = (argc > 1) ? std::atoi(argv[1]) : 0; // 0=Boost 1=Cut 2=Flat
    const double dampR = (argc > 2) ? std::atof(argv[2]) : 0.0; // trebleLadderDampR ohms
    const double fs = 48000.0;
    const double kInputRef = GainStaging::kInputRefNominal;
    const double amp = kInputRef * std::pow(10.0, -36.0 / 20.0);

    PedalChain ch;
    ch.prepare(fs, fs);
    FitParams fp {};
    fp.trebleLadderDampR = dampR;
    ch.setFitParams(fp);
    PedalChain::Params p;
    p.drive = 0.0; p.blend = 1.0; p.level = 0.5; p.master = 0.5;
    p.lo = p.loMid = p.hiMid = p.hi = 0.5;
    p.attackIdx = 1; p.gruntIdx = gruntArg; p.distEngage = true;
    ch.applyParams(p);

    const int nWarm = (int) (fs * 1.0), nMeas = (int) (fs * 0.5);
    const double freqs[] = {40, 63, 80, 100, 127, 160, 180, 202, 254, 290, 320, 360, 400, 508, 640, 1000};
    const char* gname = gruntArg == 0 ? "BOOST" : gruntArg == 1 ? "CUT" : "FLAT";
    std::printf("OD-stage cumulative transfer |tap/in| dB, grunt=%s drive=min\n", gname);
    std::printf("%6s %8s %8s %8s %8s %8s %8s %8s\n",
                "f", "jfet", "treble", "drive", "clipper", "recov", "skB", "skA");

    for (double f : freqs)
    {
        ch.reset();
        std::vector<double> in;
        std::vector<double> jf, tr, dr, cl, re, sb, sa;
        const double w = 2.0 * kPi * f / fs;
        for (int n = 0; n < nWarm + nMeas; ++n)
        {
            const double x = amp * std::sin(w * (double) n);
            const double buf = ch.runInputBuffer(x);
            auto t = ch.runOdSampleTapped(buf);
            if (n >= nWarm)
            {
                in.push_back(buf);
                jf.push_back(t.jfet); tr.push_back(t.treble); dr.push_back(t.drive);
                cl.push_back(t.clipper); re.push_back(t.recovery); sb.push_back(t.skB); sa.push_back(t.skA);
            }
        }
        double inMag = std::abs(goertzel(in, f, fs));
        auto rel = [&](const std::vector<double>& v) {
            return 20.0 * std::log10(std::max(std::abs(goertzel(v, f, fs)) / std::max(inMag, 1e-12), 1e-9));
        };
        std::printf("%6.0f %8.2f %8.2f %8.2f %8.2f %8.2f %8.2f %8.2f\n",
                    f, rel(jf), rel(tr), rel(dr), rel(cl), rel(re), rel(sb), rel(sa));
    }
    return 0;
}
