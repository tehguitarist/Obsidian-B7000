// od_phase_probe — session 31 (Phase 9 / A3 step 1): localise WHICH OD stage owes
// the missing LF phase lead.
//
// Session 29 established the root cause of A3: below ~80 Hz the real pedal's OD
// path is ANTI-PHASE with the clean BLEND bleed, so the two cancel (a null near
// 40 Hz at drive 2:30 that migrates to ~22 Hz by max drive). The model has them
// nearly IN phase everywhere — measured OD-vs-bleed phase +104° @20, +58° @40,
// +24° @64, +8° @80, −7° @101, −37° @202 — so it can only ever ADD. The target is
// ~140-180° at 40 Hz decaying to ~0 by 200 Hz, i.e. **90-120° MORE LF lead**.
//
// This probe answers "where does the OD path's LF phase currently come from, and
// which stage could plausibly supply the missing lead?" BEFORE any element is
// proposed — sessions 19/20 both mis-attributed a gap by reasoning from a stage
// transfer instead of measuring one.
//
// WHY THE CLEAN TAP IS THE RIGHT REFERENCE: `LevelBlend` is a purely resistive
// network (no caps — `LevelBlend::prepare` is empty), and everything after it is
// shared by both paths, so the OD-vs-bleed phase AT THE BLEND NODE is exactly
//     arg(skA tap) − arg(input-buffer output)
// with no post-BLEND correction needed. The skA row of table A is therefore
// directly comparable to a3_blend_decompose's OD-vs-bleed column — it is printed
// as a self-check, and if the two ever disagree one of them is wrong.
//
// ⚠ At drive noon the clipper is NONLINEAR, so every number here is a
// describing-function (fundamental-only) response, not a transfer function — it
// is amplitude-dependent, hence the dBFS argument. Run at drive-min too for the
// small-signal (genuinely linear) picture.
//
// ⚠ Settings match analysis/captures.py::_REF_OD (ATTACK **Flat** = idx 0). Do
// NOT copy blend_null_probe.cpp's `attackIdx = 1` — see a3_blend_decompose.
//
// Usage: od_phase_probe [grunt 0=Boost 1=Cut 2=Flat] [drive 0..1] [dBFS] [key=value ...]
//   trailing key=value pairs override FitParams (jfetGm/jfetRo/jfetRq2/
//   trebleLadderDampR/clipC11/clipA0) so a lever's phase authority can be scanned
//   without a rebuild — the same idea as OfflineRender's --fit.
// Build: c++ -std=c++17 -O2 -I libs/chowdsp_wdf/include \
//            analysis/od_phase_probe.cpp -o build/od_phase_probe
#include "../src/dsp/PedalChain.h"
#include "../src/dsp/FitParams.h"
#include "../src/dsp/GainStaging.h"
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <complex>
#include <vector>
#include <string>

static constexpr double kPi = 3.14159265358979323846;
static constexpr int kNTaps = 7;
static const char* kTapName[kNTaps] = {"jfet", "treble", "drive", "clipper", "recov", "skB", "skA"};
// Stages that INVERT. The two cancel by skA (chain comment: "JFET(−) + Clipper(−)
// = OD reaches BLEND net non-inverting"), but an intermediate tap carrying an odd
// number of them would read ~±180° and swamp the shape we are after — so the
// tables below report phase with the inversions removed, and say so.
static const bool kTapInverts[kNTaps] = {true, false, false, true, false, false, false};

static std::complex<double> goertzel(const std::vector<double>& y, double f, double fs)
{
    std::complex<double> acc {0.0, 0.0};
    const double w = 2.0 * kPi * f / fs;
    for (size_t n = 0; n < y.size(); ++n)
        acc += y[n] * std::exp(std::complex<double>(0.0, -w * (double) n));
    return acc * (2.0 / (double) y.size());
}

static double wrapDeg(double d)
{
    while (d > 180.0) d -= 360.0;
    while (d <= -180.0) d += 360.0;
    return d;
}

int main(int argc, char** argv)
{
    const int gruntArg = (argc > 1) ? std::atoi(argv[1]) : 1;    // _REF_OD = cut
    const double drive = (argc > 2) ? std::atof(argv[2]) : 0.5;  // noon
    const double dbfs  = (argc > 3) ? std::atof(argv[3]) : -36.0;

    const double fs = 48000.0;
    const double amp = GainStaging::kInputRefNominal * std::pow(10.0, dbfs / 20.0);

    FitParams fp {};
    const struct { const char* name; double FitParams::* member; } kFitKeys[] = {
        {"jfetGm", &FitParams::jfetGm}, {"jfetRo", &FitParams::jfetRo},
        {"jfetRq2", &FitParams::jfetRq2}, {"trebleLadderDampR", &FitParams::trebleLadderDampR},
        {"clipC11", &FitParams::clipC11}, {"clipA0", &FitParams::clipA0},
    };
    std::vector<std::string> overrides;
    for (int i = 4; i < argc; ++i)
    {
        const std::string a = argv[i];
        const auto eq = a.find('=');
        if (eq == std::string::npos) { std::fprintf(stderr, "expected key=value, got '%s'\n", argv[i]); return 1; }
        const std::string k = a.substr(0, eq);
        bool hit = false;
        for (const auto& fk : kFitKeys)
            if (k == fk.name) { fp.*(fk.member) = std::atof(a.c_str() + eq + 1); hit = true; }
        if (! hit) { std::fprintf(stderr, "unknown fit key '%s'\n", k.c_str()); return 1; }
        overrides.push_back(a);
    }

    PedalChain ch;
    ch.prepare(fs, fs);   // 1x: no OS latency, clean tap already aligned
    ch.setFitParams(fp);

    PedalChain::Params p;
    p.drive = drive;
    p.blend = 1.0;
    p.level = 0.5;
    p.master = 0.5;
    p.lo = p.loMid = p.hiMid = p.hi = 0.5;
    p.attackIdx = 0;            // Flat (_REF_OD)
    p.gruntIdx = gruntArg;      // _REF_OD = cut (1)
    p.loMidFreq = 1;
    p.hiMidFreq = 1;
    p.distEngage = true;
    ch.applyParams(p);

    // The OD region's slowest element is C15 (2u2) into R20+R21; 4 s of warmup
    // matches a3_blend_decompose. A short warmup shows up as an LF phase error,
    // which is exactly the quantity being measured here.
    const int nWarm = (int) (fs * 4.0);
    const int nMeas = (int) (fs * 0.5);

    // The A3 target table's own band centres, extended to 400 Hz so the decay back
    // toward 0° is visible (the target is ~0 by 200 Hz).
    const double freqs[] = {20, 25, 32, 40, 50, 64, 80, 101, 127, 160, 202, 254, 320, 400};

    const char* gname = gruntArg == 0 ? "BOOST" : gruntArg == 1 ? "CUT" : "FLAT";
    std::printf("# od_phase_probe grunt=%s drive=%.3f dBFS=%.1f amp=%.6f V fs=%.0f\n",
                gname, drive, dbfs, amp, fs);
    if (! overrides.empty())
    {
        std::printf("# fit overrides:");
        for (const auto& o : overrides) std::printf(" %s", o.c_str());
        std::printf("\n");
    }
    std::printf("# reference = clean tap (InputBuffer out). LevelBlend is resistive, so the\n");
    std::printf("# skA column IS the OD-vs-bleed phase at the BLEND node (cf. a3_blend_decompose).\n");
    std::printf("# Target for A3: skA must reach ~140-180 deg at 40 Hz, decaying to ~0 by 200 Hz.\n\n");

    std::vector<std::vector<double>> cumPhase(kNTaps), cumMag(kNTaps);

    for (double f : freqs)
    {
        ch.reset();
        std::vector<double> in;
        std::vector<std::vector<double>> tap(kNTaps);
        const double w = 2.0 * kPi * f / fs;
        for (int n = 0; n < nWarm + nMeas; ++n)
        {
            const double x = amp * std::sin(w * (double) n);
            const double buf = ch.runInputBuffer(x);
            const auto t = ch.runOdSampleTapped(buf);
            if (n >= nWarm)
            {
                in.push_back(buf);
                tap[0].push_back(t.jfet);   tap[1].push_back(t.treble);
                tap[2].push_back(t.drive);  tap[3].push_back(t.clipper);
                tap[4].push_back(t.recovery); tap[5].push_back(t.skB);
                tap[6].push_back(t.skA);
            }
        }

        const auto I = goertzel(in, f, fs);
        int nInv = 0;
        for (int i = 0; i < kNTaps; ++i)
        {
            const auto T = goertzel(tap[i], f, fs);
            if (kTapInverts[i]) ++nInv;
            cumPhase[i].push_back(wrapDeg((std::arg(T) - std::arg(I)) * 180.0 / kPi - 180.0 * nInv));
            cumMag[i].push_back(20.0 * std::log10(std::max(std::abs(T) / std::max(std::abs(I), 1e-15), 1e-12)));
        }
    }

    const int nF = (int) (sizeof(freqs) / sizeof(freqs[0]));

    std::printf("A. CUMULATIVE phase vs the clean tap, deg (+ = OD LEADS clean), inversions removed\n");
    std::printf("%6s", "f");
    for (int i = 0; i < kNTaps; ++i) std::printf(" %8s", kTapName[i]);
    std::printf("\n");
    for (int k = 0; k < nF; ++k)
    {
        std::printf("%6.0f", freqs[k]);
        for (int i = 0; i < kNTaps; ++i) std::printf(" %8.1f", cumPhase[i][k]);
        std::printf("\n");
    }

    std::printf("\nB. PER-STAGE phase increment, deg (sums to A's skA column), inversions removed\n");
    std::printf("%6s", "f");
    for (int i = 0; i < kNTaps; ++i) std::printf(" %8s", kTapName[i]);
    std::printf("\n");
    for (int k = 0; k < nF; ++k)
    {
        std::printf("%6.0f", freqs[k]);
        for (int i = 0; i < kNTaps; ++i)
            std::printf(" %8.1f", wrapDeg(cumPhase[i][k] - (i == 0 ? 0.0 : cumPhase[i - 1][k])));
        std::printf("\n");
    }

    std::printf("\nC. CUMULATIVE magnitude |tap/clean|, dB\n");
    std::printf("%6s", "f");
    for (int i = 0; i < kNTaps; ++i) std::printf(" %8s", kTapName[i]);
    std::printf("\n");
    for (int k = 0; k < nF; ++k)
    {
        std::printf("%6.0f", freqs[k]);
        for (int i = 0; i < kNTaps; ++i) std::printf(" %8.2f", cumMag[i][k]);
        std::printf("\n");
    }
    return 0;
}
