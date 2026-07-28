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
#include <string>

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
    double inputRef = GainStaging::kInputRefNominal;

    // ATTACK position, session 55. Like kInputRef this is NOT a FitParams member —
    // it is a PedalChain::Params switch index (0=Flat, 1=Boost, 2=Cut, matching
    // analysis/captures.py::_ATTACK_IDX) — so it is special-cased rather than added
    // to kFitKeys, which is a table of `double FitParams::*`.
    // Why it exists: session 54's condition axis measured the PEDAL's OD transfer at
    // both ATTACK positions but could print no `H_req` for them, because this tool
    // hardcoded `p.attackIdx = 0` and there was therefore no model side at all — the
    // ATTACK half of that localiser could only ever run pedal-vs-pedal. GRUNT was
    // already reachable (argv[1]); ATTACK was the one condition in the matrix that
    // was not.
    int attackIdx = 0;                        // Flat (_REF_OD) — the shipped default

    // Trailing key=value pairs override FitParams, so a candidate element can be
    // swept across the whole DRIVE axis without a rebuild (session 34, A3 step 3a:
    // the gate is a drive SWEEP, so every candidate needs all five CSVs).
    // kInputRef is GainStaging-domain, not a FitParams member (see FitParams.h
    // "Scope boundary"), so it is special-cased here rather than added to
    // kFitKeys — session 39: the -12/-6 dBFS clipper item needs kInputRef swept
    // JOINTLY with clipSatLo/Hi (its session-16/17 degenerate partner), and
    // until now this tool had no way to move it off the shipped default at all.
    FitParams fp {};
    const struct { const char* name; double FitParams::* member; } kFitKeys[] = {
        {"trebleC7", &FitParams::trebleC7},
        {"clipC15", &FitParams::clipC15},
        {"trebleLadderDampR", &FitParams::trebleLadderDampR},
        {"attackTapRa", &FitParams::attackTapRa},
        {"attackTapRb", &FitParams::attackTapRb},
        {"attackTapRc", &FitParams::attackTapRc},
        {"attackTapR11", &FitParams::attackTapR11},
        {"trebleC5", &FitParams::trebleC5},
        {"attackC5TrimBoost", &FitParams::attackC5TrimBoost},
        {"attackC5TrimCut", &FitParams::attackC5TrimCut},
        {"attackDampBoost", &FitParams::attackDampBoost},
        {"attackDampCut", &FitParams::attackDampCut},
        {"trebleC8", &FitParams::trebleC8},
        // The SHARED ladder (session 64; session 50's next-step (a)). These were
        // static constexpr in TrebleAttack.h and reachable from NO tool until now.
        {"trebleR7", &FitParams::trebleR7},
        {"trebleLadderR12", &FitParams::trebleLadderR12},
        {"trebleLadderR14", &FitParams::trebleLadderR14},
        {"trebleC9", &FitParams::trebleC9},
        {"trebleC6", &FitParams::trebleC6},
        {"clipC11", &FitParams::clipC11}, {"clipA0", &FitParams::clipA0},
        // The switched GRUNT caps, added session 38 so the GRUNT SPAN can be scanned
        // at the shipped state. Session 23's "no interior minimum" scan predates
        // trebleC7/clipC15, so it had to be re-run rather than carried forward.
        {"clipC12", &FitParams::clipC12}, {"clipC13", &FitParams::clipC13},
        {"clipR16", &FitParams::clipR16},
        // The IC2_B bridged-T (risk register #1). FitParams already declares all four
        // as FIT parameters ("to be reshaped to whatever the capture actually shows,
        // including much shallower than ideal"); they were never reachable from this
        // probe. Added session 47 because the whole-band s(f) solve puts the model's
        // OD path 4-9 dB too weak from 127 Hz up, and this stage is the single
        // largest roller-off across exactly that span (-11.3 dB from 127 to 400 Hz).
        // ⚠ GAP #1b closed this stage TWICE on OUTPUT dips — a band where the OD sits
        // 6-19 dB under the bleed, so the output is bleed-dominated and cannot see the
        // OD path's own shape. That is the GAP #2 category error, one gap over.
        {"btR22", &FitParams::btR22}, {"btR23", &FitParams::btR23},
        {"btC16", &FitParams::btC16}, {"btC17", &FitParams::btC17},
        {"railNeg", &FitParams::railNeg}, {"railPos", &FitParams::railPos},
        {"jfetGm", &FitParams::jfetGm},
        // The clipper VTC + JFET shaper, added session 37 so the LEVEL axis can be
        // swept: the -12/-6 dBFS residual is level-dependent, so only a
        // nonlinearity can move it and these are the parameters that shape one.
        {"clipSatLo", &FitParams::clipSatLo}, {"clipSatHi", &FitParams::clipSatHi},
        {"clipK", &FitParams::clipK},
        {"jfetSatPos", &FitParams::jfetSatPos}, {"jfetSatNeg", &FitParams::jfetSatNeg},
        {"jfetCeilPos", &FitParams::jfetCeilPos}, {"jfetCeilNeg", &FitParams::jfetCeilNeg},
        {"jfetExpandBeta", &FitParams::jfetExpandBeta},
        {"driveTaperExp", &FitParams::driveTaperExp},
    };
    for (int i = 4; i < argc; ++i)
    {
        const std::string a = argv[i];
        const auto eq = a.find('=');
        if (eq == std::string::npos) { std::fprintf(stderr, "expected key=value, got '%s'\n", argv[i]); return 1; }
        const std::string k = a.substr(0, eq);
        bool hit = false;
        if (k == "kInputRef") { inputRef = std::atof(a.c_str() + eq + 1); hit = true; }
        if (k == "attackIdx")
        {
            attackIdx = std::atoi(a.c_str() + eq + 1);
            if (attackIdx < 0 || attackIdx > 2)
            {
                std::fprintf(stderr, "attackIdx must be 0=Flat, 1=Boost or 2=Cut, got '%s'\n",
                             a.c_str() + eq + 1);
                return 1;
            }
            hit = true;
        }
        for (const auto& fk : kFitKeys)
            if (k == fk.name) { fp.*(fk.member) = std::atof(a.c_str() + eq + 1); hit = true; }
        if (! hit) { std::fprintf(stderr, "unknown fit key '%s'\n", k.c_str()); return 1; }
    }
    const double amp = inputRef * std::pow(10.0, dbfs / 20.0);

    PedalChain ch;
    ch.prepare(fs, fs);   // 1x: no OS latency, clean tap already aligned
    ch.setFitParams(fp);

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
    // ⚠ Overridable since session 55 (`attackIdx=` above); the DEFAULT is unchanged
    // at Flat, so every existing CSV/tool is bit-identical unless it asks otherwise.
    p.attackIdx = attackIdx;                  // Flat  (_REF_OD) unless overridden
    p.gruntIdx = gruntArg;                    // _REF_OD = cut (1)
    p.loMidFreq = 1;                          // 500 Hz  (_REF_OD)
    p.hiMidFreq = 1;                          // 1.5 kHz (_REF_OD)
    p.distEngage = true;

    // Warmup for the slow post-BLEND caps (C21 ~7 Hz at c21R=220k, master 0.7 Hz).
    // C21's corner moved down in session 28, so this is deliberately longer than
    // blend_null_probe's 2 s — a short warmup shows up as an LF magnitude error.
    const int nWarm = (int) (fs * 4.0);
    const int nMeas = (int) (fs * 0.5);

    // The A3 target table's own band centres, extended to 806 Hz (session 33).
    // The upper bands are NOT decoration: with the required extra phase corrected
    // for the model's SIGN it runs ~+120 deg all the way out to 254 Hz, and
    // whether that is minimum-phase-realisable is decided by what |G| does ABOVE
    // the band. Session 32's lesson was that an unmeasured tail decides the
    // answer at the band edge — so measure this one instead of declaring it.
    //
    // ⭐ EXTENDED AGAIN TO 10 kHz (session 49) — same argument, one range up, and
    // this time it had already cost a wrong decision. Every A3 instrument stopped
    // at 806 Hz, so a candidate's SIDE EFFECTS above 1 kHz were unmeasurable by
    // construction: session 47 preferred `btC17=10n + btC16=1.496n` (the
    // f0-preserving pair) on a score computed over bands <=806 Hz, and the full
    // 63-capture matrix then rejected it because that form adds +3.7 dB of OD lift
    // at 3-5 kHz and +1.6 dB at 6.5-13 kHz -- entirely outside what the gate could
    // see. A gate whose domain is narrower than its candidate's reach cannot
    // discriminate; widen the domain rather than trusting the candidate.
    //
    // ⚠ The 1-10 kHz bands are spaced 2/3 octave, NOT the report's full 1/3-oct
    // grid: they exist to catch a BROADBAND multi-dB side effect, which is what
    // the bridged-T family produces. Do NOT read a NARROW feature (a notch depth
    // or centre) off this grid -- that is the standing session-46 / A2c-2 error.
    const double freqs[] = {20, 25, 32, 40, 50, 64, 80, 101, 127, 160, 202, 254,
                            320, 403, 508, 640, 806,
                            1016, 1613, 2560, 4064, 6451, 10240};

    const char* gname = gruntArg == 0 ? "BOOST" : gruntArg == 1 ? "CUT" : "FLAT";
    const char* aname = attackIdx == 1 ? "BOOST" : attackIdx == 2 ? "CUT" : "FLAT";
    // ATTACK is in the header so a CSV states its own operating point: these files are
    // read by name from a dozen tools, and a condition that lives only in the filename
    // is the stale-artefact trap (session 45 item 7a, session 37 item 12).
    std::printf("# a3_blend_decompose grunt=%s attack=%s drive=%.3f dBFS=%.1f amp=%.6f V fs=%.0f\n",
                gname, aname, drive, dbfs, amp, fs);
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
