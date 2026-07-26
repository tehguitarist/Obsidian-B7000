// a3_blend_decompose — session 29 (Phase 9 / A3): decompose the BLEND node at the
// EXACT conditions the A3 target table was measured at (GRUNT cut / drive noon /
// BLEND max), referenced to the full-clean capture the way the table is.
//
// Why a new probe rather than blend_null_probe: that one is hardwired to
// drive=min (its question was the drive-min 254 Hz null) and has no full-clean
// reference pass, so its dB values are not comparable to the A3 table's rows.
// This one adds (a) a drive argument, (b) a BLEND=0 reference pass, (c) the
// table's own band centres, and (d) raw phasors on stdout so the geometry can be
// solved offline (a3_solve.py) instead of eyeballed.
//
// LevelBlend is linear in its two inputs, so at BLEND=max the output decomposes
// EXACTLY into an OD-path contribution and a clean-bleed contribution:
//   full  = processPostBlend(clean, od)
//   odC   = processPostBlend(0,     od)
//   clC   = processPostBlend(clean, 0)      (full == odC + clC, asserted below)
// The reference is a separate pass with BLEND=0 (= the blend-0700 capture).
//
// ⚠ At drive noon the OD path is NONLINEAR, so a single-tone measurement is a
// describing-function (fundamental-only) response. That is the right quantity to
// compare against a 1/3-octave band level dominated by its fundamental, but it is
// NOT a transfer function — it is amplitude-dependent, hence the amp argument.
//
// Usage: a3_blend_decompose [grunt 0=Boost 1=Cut 2=Flat] [drive 0..1] [dBFS]
// Build: c++ -std=c++17 -O2 -I libs/chowdsp_wdf/include \
//            analysis/a3_blend_decompose.cpp -o build/a3_blend_decompose
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

// mode: 0 full, 1 od-only, 2 clean-only. Params must already be applied.
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
        if (mode == 0)      yy = ch.processPostBlend(clean, od);
        else if (mode == 1) yy = ch.processPostBlend(0.0, od);
        else                yy = ch.processPostBlend(clean, 0.0);
        if (n >= nWarm) y.push_back(yy);
    }
    return y;
}

int main(int argc, char** argv)
{
    const int gruntArg  = (argc > 1) ? std::atoi(argv[1]) : 1;    // A3 condition = CUT
    const double drive  = (argc > 2) ? std::atof(argv[2]) : 0.5;  // A3 condition = noon
    const double dbfs   = (argc > 3) ? std::atof(argv[3]) : -36.0;

    const double fs = 48000.0;
    const double amp = GainStaging::kInputRefNominal * std::pow(10.0, dbfs / 20.0);

    PedalChain ch;
    ch.prepare(fs, fs);   // 1x: no OS latency, clean tap already aligned
    ch.setFitParams(FitParams {});

    PedalChain::Params p;
    p.drive = drive;
    p.level = 0.5;
    p.master = 0.5;
    p.lo = p.loMid = p.hiMid = p.hi = 0.5;   // flat EQ (DSP-space)
    // ⚠ These must match analysis/captures.py::_REF_OD exactly or the comparison
    // against the A3 table is against a different operating point. In particular
    // ref-od is ATTACK **Flat** (idx 0) — blend_null_probe.cpp used idx 1 and
    // labelled it "Boost centre (ref-od baseline)", which is wrong; at LF C8's
    // 220 pF makes it near-inert, but at drive noon it moves the clipper's
    // operating point, so do not inherit that setting.
    p.attackIdx = 0;                          // Flat  (_REF_OD)
    p.gruntIdx = gruntArg;                    // _REF_OD = cut (1)
    p.loMidFreq = 1;                          // 500 Hz  (_REF_OD)
    p.hiMidFreq = 1;                          // 1.5 kHz (_REF_OD)
    p.distEngage = true;

    // Warmup for the slow post-BLEND caps (C21 ~7 Hz at c21R=220k, master 0.7 Hz).
    // C21's corner moved down in session 28, so this is deliberately longer than
    // blend_null_probe's 2 s — a short warmup shows up as an LF magnitude error.
    const int nWarm = (int) (fs * 4.0);
    const int nMeas = (int) (fs * 0.5);

    // The A3 target table's own band centres.
    const double freqs[] = {20, 25, 32, 40, 50, 64, 80, 101, 127, 160, 202, 254};

    const char* gname = gruntArg == 0 ? "BOOST" : gruntArg == 1 ? "CUT" : "FLAT";
    std::printf("# a3_blend_decompose grunt=%s drive=%.3f dBFS=%.1f amp=%.6f V fs=%.0f\n",
                gname, drive, dbfs, amp, fs);
    std::printf("# ref = BLEND 0 (full clean, = blend-0700). full/od/clean at BLEND max.\n");
    std::printf("# f,ref_re,ref_im,full_re,full_im,od_re,od_im,cl_re,cl_im,resid_db\n");

    for (double f : freqs)
    {
        p.blend = 0.0;                       // full clean reference
        ch.applyParams(p);
        auto R = goertzel(runPass(ch, f, fs, amp, nWarm, nMeas, 0), f, fs);

        p.blend = 1.0;                       // full OD
        ch.applyParams(p);
        auto F = goertzel(runPass(ch, f, fs, amp, nWarm, nMeas, 0), f, fs);
        auto O = goertzel(runPass(ch, f, fs, amp, nWarm, nMeas, 1), f, fs);
        auto C = goertzel(runPass(ch, f, fs, amp, nWarm, nMeas, 2), f, fs);

        // Superposition self-check: full must equal od+clean to numeric precision.
        // If this ever grows, the decomposition is invalid and every number below
        // it is meaningless — so report it rather than trusting it silently.
        const double resid = std::abs(F - (O + C)) / std::max(std::abs(F), 1e-15);
        const double residDb = 20.0 * std::log10(std::max(resid, 1e-15));

        std::printf("%.0f,%.9e,%.9e,%.9e,%.9e,%.9e,%.9e,%.9e,%.9e,%.1f\n",
                    f, R.real(), R.imag(), F.real(), F.imag(),
                    O.real(), O.imag(), C.real(), C.imag(), residDb);
    }
    return 0;
}
