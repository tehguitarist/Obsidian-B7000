// blend_null_probe — session 19 (Phase 9): is the plugin's grunt-boost 254 Hz
// null an OD-vs-clean-bleed CANCELLATION at the BLEND node, and if so is it a
// polarity bug or expected frequency-dependent phase?
//
// LevelBlend is linear in its two inputs, so the output decomposes exactly:
//   full  = processPostBlend(clean, od)
//   odC   = processPostBlend(0,     od)   // OD contribution alone
//   clC   = processPostBlend(clean, 0)    // clean-bleed contribution alone
// A cancellation null => |full| << |odC|,|clC| with phase(odC)-phase(clC) ~ 180.
// Polarity check: at LOW freq the two SHOULD be ~in-phase (OD = clipper-inv +
// JFET-inv = net non-inverting; clean = non-inverting -> they ADD). If they are
// ~180 apart at low freq, the OD/clean sign relationship is wrong (dsp.md).
//
// Build: see analysis/README or the one-off c++ line in the session log.
#include "../src/dsp/PedalChain.h"
#include "../src/dsp/FitParams.h"
#include "../src/dsp/GainStaging.h"
#include <cstdio>
#include <cmath>
#include <complex>
#include <vector>

static constexpr double kPi = 3.14159265358979323846;

struct Bin { double mag; double phaseDeg; };

// Single-frequency DFT (complex) of y[n] over an integer number of cycles.
static std::complex<double> goertzel(const std::vector<double>& y, double f, double fs)
{
    std::complex<double> acc {0.0, 0.0};
    const double w = 2.0 * kPi * f / fs;
    for (size_t n = 0; n < y.size(); ++n)
        acc += y[n] * std::exp(std::complex<double>(0.0, -w * (double) n));
    return acc * (2.0 / (double) y.size());
}

// Run one pass; mode: 0 full, 1 od-only, 2 clean-only. Returns steady-state y.
static std::vector<double> runPass(PedalChain& ch, double f, double fs, double amp,
                                   int nWarm, int nMeas, int mode)
{
    ch.reset();
    std::vector<double> y;
    y.reserve((size_t) nMeas);
    const double w = 2.0 * kPi * f / fs;
    for (int n = 0; n < nWarm + nMeas; ++n)
    {
        const double x = amp * std::sin(w * (double) n);
        const double clean = ch.runInputBuffer(x);
        const double od = ch.runOdSample(clean);
        double yy;
        if (mode == 0) yy = ch.processPostBlend(clean, od);
        else if (mode == 1) yy = ch.processPostBlend(0.0, od);
        else yy = ch.processPostBlend(clean, 0.0);
        if (n >= nWarm) y.push_back(yy);
    }
    return y;
}

int main(int argc, char** argv)
{
    const int gruntArg = (argc > 1) ? std::atoi(argv[1]) : 0; // 0=Boost 1=Cut 2=Flat
    const double c13nF = (argc > 2) ? std::atof(argv[2]) : 0.0; // 0 => shipped default
    const double c12nF = (argc > 3) ? std::atof(argv[3]) : 0.0; // 0 => shipped default
    const double fs = 48000.0;
    const double kInputRef = GainStaging::kInputRefNominal; // 3.377
    const double dbfs = -36.0;                              // ~ sweep_clean level
    const double amp = kInputRef * std::pow(10.0, dbfs / 20.0);

    PedalChain ch;
    ch.prepare(fs, fs); // 1x: no OS latency, clean tap already aligned
    FitParams fp {}; // shipped defaults (C12=47n, C13=220n)
    if (c13nF > 0.0) fp.clipC13 = c13nF * 1e-9;
    if (c12nF > 0.0) fp.clipC12 = c12nF * 1e-9;
    ch.setFitParams(fp);

    PedalChain::Params p;
    p.drive = 0.0;      // drive-min = most linear
    p.blend = 1.0;      // full OD (base-od)
    p.level = 0.5;
    p.master = 0.5;
    p.lo = p.loMid = p.hiMid = p.hi = 0.5; // flat EQ (DSP-space)
    p.attackIdx = 1;    // Boost centre (ref-od baseline)
    p.gruntIdx = gruntArg; // 0=Boost 1=Cut 2=Flat
    p.distEngage = true;
    ch.applyParams(p);

    // Warmup for slow post-BLEND caps (C21 16 Hz, master 0.7 Hz) to settle.
    const int nWarm = (int) (fs * 2.0);
    const int nMeas = (int) (fs * 0.5);

    const double freqs[] = {40, 50, 63, 80, 100, 110, 127, 140, 160, 180, 202, 227,
                            254, 290, 320, 400, 508, 640};
    const char* gname = gruntArg == 0 ? "BOOST" : gruntArg == 1 ? "CUT" : "FLAT";
    std::printf("grunt=%s drive=min blend=max  c13=%s c12=%s  amp=%.5f V\n",
                gname, c13nF > 0 ? (std::to_string(c13nF) + "n").c_str() : "default",
                c12nF > 0 ? (std::to_string(c12nF) + "n").c_str() : "default", amp);
    std::printf("%6s %10s %10s %10s %12s\n", "f", "|full|dB", "|od|dB", "|clean|dB", "ph(od-cl)");
    double peakF = 0, peakOd = -1e9;
    for (double f : freqs)
    {
        auto full = runPass(ch, f, fs, amp, nWarm, nMeas, 0);
        auto odC = runPass(ch, f, fs, amp, nWarm, nMeas, 1);
        auto clC = runPass(ch, f, fs, amp, nWarm, nMeas, 2);
        auto F = goertzel(full, f, fs);
        auto O = goertzel(odC, f, fs);
        auto C = goertzel(clC, f, fs);
        auto todb = [](double m) { return 20.0 * std::log10(std::max(m, 1e-12)); };
        double dph = (std::arg(O) - std::arg(C)) * 180.0 / kPi;
        while (dph > 180.0) dph -= 360.0;
        while (dph < -180.0) dph += 360.0;
        if (todb(std::abs(O)) > peakOd) { peakOd = todb(std::abs(O)); peakF = f; }
        std::printf("%6.0f %10.2f %10.2f %10.2f %12.1f\n",
                    f, todb(std::abs(F)), todb(std::abs(O)), todb(std::abs(C)), dph);
    }
    std::printf(">> OD-only contribution peaks at %.0f Hz (%.2f dB)  [pedal target ~180 Hz]\n",
                peakF, peakOd);
    return 0;
}
