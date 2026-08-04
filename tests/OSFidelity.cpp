// OSFidelity — the second of Phase 10's three specified probes (`build.md`,
// "Performance & fidelity probes"), and the last one still unbuilt after
// PerfBenchmark landed in session 127.
//
// THE QUESTION IT ANSWERS, which nothing else in the suite asks:
// **how close are 1x / 2x / 4x to 8x, and WHICH PART of the gap is which?**
// The plugin ships a 2x realtime default and exposes 1x, so most users never hear
// the 8x path at all; `build.md` specifies this probe as "the common DAW low-OS
// case ... separates the wanted distortion (faithful at low OS) from aliasing +
// top-octave droop (the OS-only fixes)". Those three components have completely
// different remedies — a droop is a discretisation artefact fixed by a filter,
// aliasing is what the OS factor and ADAA exist for, and a harmonic-ladder error
// at low OS would mean the low-OS user is hearing a different distortion, not
// merely a dirtier one. A single "alias floor" number cannot tell them apart.
//   ⛔ AND ON THE DROOP'S REMEDY, BECAUSE THIS IS WHERE SOMEONE WILL REACH FOR IT:
// `src/utils/Prewarp.h` ships and is referenced by NOTHING outside its own header,
// which makes it the obvious candidate. IT IS THE WRONG TOOL HERE. `dsp.md` states
// that a cap inside the OVERSAMPLED region is already discretised at the high rate
// and must not be prewarped — and every cap this block measures is inside it (the
// OD region is what PedalDSP oversamples). Prewarp pins ONE corner at ONE rate; the
// deficit below is a function of the OS FACTOR. The option in `dsp.md` that matches
// is its third one: a fixed high-shelf whose gain is set PER OS FACTOR (~0 at 4x/8x,
// so transparent at the default). Unbuilt, and NOT proposed by this probe — it is a
// DSP change and would owe its own gate and a re-baseline.
//
// ⛔ WHAT IT DELIBERATELY DOES NOT DUPLICATE. `OSValidationTest` already gates
// (a) delay-comp factor-independence, (b) the ADAA OS-factor gate's liveness and
// scope, (c) the alias floor vs factor at 2499 Hz, and (d) ADAA's benefit on that
// floor at 2x. Every one of those is an ABSOLUTE property of one factor. This
// file measures a RELATIVE one — distance from the 8x reference — decomposed, and
// it re-derives (b) as a by-product through a third code path (see check 5).
//
// ⚠⚠ THE CONFOUND THIS PROBE HAD TO BE DESIGNED AROUND, AND IT IS NEW SINCE
// SESSION 124. The shipped build gates ADAA by OS factor (`clipAdaaMaxOs = 2`:
// on at 1x/2x, off at 4x/8x), so the low-OS arms are NOT "the same chain with
// less oversampling" — they run a different approximation of the nonlinearity.
// A naive 1x-vs-8x difference therefore mixes the discretisation question with
// the ADAA question and can attribute neither. So the two are measured
// SEPARATELY, and both are reported:
//   • Blocks 1 and 2 hold ADAA OFF at every factor (`clipAdaaMaxOs = 0`), which
//     is the only way to isolate what the OS factor itself does. Same move, and
//     the same reason, as OSValidationTest's delay-comp block (session 124).
//   • Block 3 then asks the question that isolation makes askable, and which
//     NOTHING in this project has asked: the shipped policy reduces alias energy
//     (measured twice — GATE X and OSValidationTest's own benefit column), but
//     ADAA1 is a *different approximation*, not merely a cleaner one — it is a
//     2-point average over the sample interval. So does it move 1x/2x TOWARD the
//     8x truth, or merely make them quieter in the alias bucket while displacing
//     the WANTED harmonics? Reducing alias energy and improving fidelity are two
//     claims, and only the first has ever been measured.
//
// WHAT IS ASSERTED, AND WHY EACH IS NOT VACUOUS (`build.md`: these probes are
// FINITE-ONLY — nothing here gates on the size of a fidelity number, because
// that would be a threshold nobody has derived):
//
//   1. Finiteness + non-zero on every arm. A probe that reports a NUMBER is a
//      gate whatever it is called (measurement-discipline.md §5, session 118's
//      `--os 3` probe that reported a clean 0.0000 % on nine renders that
//      processed nothing).
//   2. DETERMINISM: two fresh PedalDSP instances at identical settings are
//      BIT-IDENTICAL. Free known answer, no threshold, and it is what licenses
//      reading any cross-factor difference as a factor effect rather than as
//      state leaking between renders.
//   3. **THE CLEAN PATH IS FACTOR-INVARIANT.** The BLEND clean tap splits at the
//      InputBuffer, runs at base rate, and is only DELAYED by the oversampler's
//      latency (PedalDSP.h) — and Goertzel magnitude is phase-invariant. So at
//      BLEND = 0 the measured magnitude is *forbidden* to depend on the OS
//      factor, and the residual is the FR instrument's own noise floor. This is
//      the constructive known answer of measurement-discipline.md §1 ("look down
//      the chain for a stage whose physics forbids some structure, and measure
//      that structure"), and it certifies the render + Goertzel + bin-exact grid
//      before a single OD number is read.
//   4. NON-VACUITY, gated on that measured floor rather than on a guessed bar:
//      the OD path's 1x-vs-8x FR difference must exceed the clean control's
//      residual by a wide margin. Without it, a probe in which the factor never
//      reached the DSP would print a beautiful table of zeros and read as
//      "1x is perfect" (session 100's mutation-control lesson).
//   5. The ADAA policy's SCOPE, re-derived here: shipped is bit-identical to an
//      ADAA-off control at 4x/8x and differs at 1x/2x. Third independent code
//      path for the same invariant (OSValidationTest 1b, PerfBenchmark check 4).
//
// METHOD NOTES, all inherited rather than re-invented:
//   • Every probe frequency is BIN-EXACT (f = k·fs/N over exactly N samples), so
//      the Goertzel/FFT read is leakage-free by construction and no window or
//      mask width exists to get wrong. Session 92 found a −40.5 dB "floor" that
//      was nothing but a third of a bin of misalignment.
//   • The driven blocks settle 4 s (18 τ of MasterOut's two ~0.72 Hz high-passes)
//      and report the sub-200 Hz bucket SEPARATELY rather than summing a decaying
//      DC ramp into "alias". Session 92, OSValidationTest header note (b).
//   • The harmonic ladder is rms'd only over orders the 8x REFERENCE resolves
//      above a floor re its own H1, and the surviving count is printed — an rms
//      over numerical noise is not a fidelity measurement.
//
// ⚠ HONEST LIMIT. Every number here is model-vs-model: it says how far the
// shipped plugin at one OS factor sits from the SAME plugin at 8x. It says
// nothing about how far 8x sits from the pedal — that is the capture matrix's
// job, and the matrix renders at 8x precisely so this axis is excluded from it.

#include "../src/dsp/PedalDSP.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

static int failures = 0;
static void check(bool cond, const char* msg)
{
    if (! cond)
    {
        std::printf("  FAIL: %s\n", msg);
        ++failures;
    }
}

static constexpr double kFs = 48000.0;
static constexpr int kRefOrder = 3; // 8x is the reference everything is measured against

// FR block: N samples, so bin width = fs/N. Every probe frequency is k·fs/N.
static constexpr int kFrOrder = 15;
static constexpr int kFrN = 1 << kFrOrder; // 32768 -> 1.4648 Hz bins

// Driven block: FFT length + settle, both inherited from OSValidationTest.
static constexpr int kFftOrder = 14;
static constexpr int kFftN = 1 << kFftOrder; // 16384
static constexpr double kLfHz = 200.0;       // below this = settling residue, reported apart

// ⚠⚠ THE SETTLE IS LOAD-BEARING FOR THE **FR** BLOCKS TOO, WHICH IS NOT OBVIOUS AND
// COST THIS FILE ITS FIRST RUN. OSValidationTest settles its FR/delay-comp block for
// 0.3 s and only its DRIVEN block for 4 s, so 0.3 s was the natural inheritance here.
// It fails the clean-path known answer: MasterOut is two ~0.72 Hz high-passes
// (tau = 0.22 s), so 0.3 s is 1.4 tau and leaves ~26 % of the transient alive in the
// analysis window — and because each OS factor delays the clean tap by a DIFFERENT
// number of samples, each factor's window starts at a different point on that decaying
// ramp. The residue is therefore factor-dependent, which is precisely the thing the
// known answer forbids. Measured, it read 4.4e-07 dB at 200 Hz falling to 1.1e-10 at
// 16 kHz — frequency-ordered, i.e. wearing its own diagnosis (a decaying-DC contaminant,
// not a broadband floor). It also put a spurious constant +0.005 dB on the droop table's
// 100-400 Hz rows, where discretisation must contribute ~0.
// ⭐ The tempting repair was to widen the 1e-9 bar to 1e-6 and move on. That is the
// concession this project keeps paying for: the bar was right and the SETTLE was wrong,
// and widening it would have kept a contaminated FR table while deleting the only guard
// that can see the contamination. One settle constant is now used everywhere.
static constexpr double kSettleSec = 4.0; // 18 tau — the same figure session 92 derived

// Where the harmonic ladder is split into a GENERATION reading and a DROOP reading.
// ⚠ Not a round number picked for tidiness: block 1 of this same run measures the 1x
// FR deficit at −0.485 dB at 5.0 kHz and −2.348 dB at 8.0 kHz, so 5 kHz is the last
// probe point at which the droop is small against the ladder errors being reported.
// If block 1's numbers move on a future build, MOVE THIS TOO — it is derived from
// them, not independent of them.
static constexpr double kLadderSplitHz = 5000.0;

// ---------------------------------------------------------------------------------
// Render helper — one steady sine through a fresh PedalDSP, transient discarded.
// Same shape as OSValidationTest::renderSine (deliberately: the two probes must
// agree about what "a render" is), duplicated rather than shared because these are
// standalone console apps with no common translation unit.
// ---------------------------------------------------------------------------------
static std::vector<double> renderSine(PedalChain::Params p, int order, double freq, double amp,
                                      int nOut, double settleSec, FitParams fit)
{
    PedalDSP dsp;
    const int block = 256;
    dsp.prepare(kFs, block);
    dsp.setFitParams(fit);
    dsp.setFactorOrder(order);
    dsp.setParams(p);

    const int settle = (int) (settleSec * kFs);
    const int total = settle + nOut;
    std::vector<double> out;
    out.reserve((size_t) nOut);

    std::vector<double> buf((size_t) block);
    int phase = 0;
    for (int n = 0; n < total; n += block)
    {
        const int m = std::min(block, total - n);
        for (int i = 0; i < m; ++i)
            buf[(size_t) i] = amp * std::sin(2.0 * M_PI * freq * (phase + i) / kFs);
        phase += m;
        dsp.processBlock(buf.data(), m);
        for (int i = 0; i < m; ++i)
            if (n + i >= settle)
                out.push_back(buf[(size_t) i]);
    }
    return out;
}

// Goertzel magnitude at f (phase-invariant -> immune to the per-factor clean delay).
static double goertzelMag(const std::vector<double>& x, double f)
{
    const double w = 2.0 * M_PI * f / kFs;
    const double coeff = 2.0 * std::cos(w);
    double s0 = 0.0, s1 = 0.0, s2 = 0.0;
    for (double v : x)
    {
        s0 = v + coeff * s1 - s2;
        s2 = s1;
        s1 = s0;
    }
    const double real = s1 - s2 * std::cos(w);
    const double imag = s2 * std::sin(w);
    return std::sqrt(real * real + imag * imag) * 2.0 / (double) x.size();
}

static double db(double lin) { return 20.0 * std::log10(lin + 1e-300); }

// ---------------------------------------------------------------------------------
// Driven-spectrum decomposition at a bin-exact f0 = kBin·fs/kFftN.
// Rectangular window is CORRECT here and not a shortcut: the settled output of a
// time-invariant chain driven by a tone periodic in kFftN samples is itself
// periodic in kFftN, so every harmonic AND every fold of a harmonic lands dead on
// a bin and leakage is zero (session 92).
// ---------------------------------------------------------------------------------
struct Spectrum
{
    std::vector<double> harmonicDb; // index n = order n (1-based); -inf where absent
    double aliasToSigDb = 0.0;
    double lfToSigDb = 0.0;
    double h1Db = 0.0;
    long long nonFinite = 0;
    int maxOrder = 0;
};

static Spectrum analyseDriven(PedalChain::Params p, int order, int kBin, double amp, FitParams fit)
{
    const double f0 = kBin * kFs / kFftN;
    auto y = renderSine(p, order, f0, amp, kFftN, kSettleSec, fit);

    Spectrum s;
    for (double v : y)
        if (! std::isfinite(v))
            ++s.nonFinite;

    juce::dsp::FFT fft(kFftOrder);
    std::vector<float> fd((size_t) kFftN * 2, 0.0f);
    for (int i = 0; i < kFftN; ++i)
        fd[(size_t) i] = (float) y[(size_t) i];
    fft.performFrequencyOnlyForwardTransform(fd.data());

    s.maxOrder = (kFftN / 2 - 1) / kBin;
    s.harmonicDb.assign((size_t) s.maxOrder + 1, -1e300);

    double sig = 0.0, alias = 0.0, lf = 0.0;
    for (int b = 1; b < kFftN / 2; ++b)
    {
        const double mag = (double) fd[(size_t) b];
        const double e = mag * mag;
        if (b % kBin == 0)
        {
            sig += e;
            const int n = b / kBin;
            if (n <= s.maxOrder)
                s.harmonicDb[(size_t) n] = db(mag);
        }
        else if (b * kFs / kFftN < kLfHz)
            lf += e;
        else
            alias += e;
    }
    s.h1Db = s.harmonicDb.size() > 1 ? s.harmonicDb[1] : -1e300;
    s.aliasToSigDb = 10.0 * std::log10((alias + 1e-30) / (sig + 1e-30));
    s.lfToSigDb = 10.0 * std::log10((lf + 1e-30) / (sig + 1e-30));
    return s;
}

// Harmonic-ladder distance from the reference, in dB rms, over the orders the
// REFERENCE resolves above `floorDb` re its own H1 AND whose frequency lies in
// [fLo, fHi). Selecting membership on the reference (never on the arm under test) is
// what keeps this from being `self-selecting-scores`: the arm cannot shrink its own
// scoring set.
//
// ⚠⚠ THE BAND ARGUMENT IS NOT A CONVENIENCE — WITHOUT IT THIS METRIC MEASURES THE
// DROOP AGAIN AND CALLS IT DISTORTION ERROR. A harmonic is a signal at n·f0, so it is
// rolled off by exactly the top-octave deficit block 1 reports; unbanded, the 1x
// ladder rms came out at 27.8 dB driven almost entirely by orders above 10 kHz, where
// block 1 independently measures a −5…−21 dB FR deficit. Reporting that as "the wanted
// distortion is wrong at 1x" would be double-counting one defect as two — and it is the
// exact failure `build.md` commissions this probe to avoid ("separates the wanted
// distortion from ... top-octave droop"). So the ladder is reported in two bands, split
// at kLadderSplitHz, and only the LOW band answers the generation question.
struct LadderDist
{
    double rmsDb = 0.0;
    double worstDb = 0.0;
    int worstOrder = 0;
    int n = 0;
};

static LadderDist ladderDistance(const Spectrum& arm, const Spectrum& ref, double floorDb,
                                 double f0, double fLo, double fHi)
{
    LadderDist d;
    double acc = 0.0;
    const int hi = std::min(arm.maxOrder, ref.maxOrder);
    for (int n = 2; n <= hi; ++n)
    {
        const double fn = n * f0;
        if (fn < fLo || fn >= fHi)
            continue;
        const double r = ref.harmonicDb[(size_t) n];
        if (! std::isfinite(r) || r - ref.h1Db < floorDb)
            continue; // the reference does not resolve this order — nothing to compare to
        const double a = arm.harmonicDb[(size_t) n];
        if (! std::isfinite(a))
            continue;
        const double e = a - r;
        acc += e * e;
        ++d.n;
        if (std::abs(e) > std::abs(d.worstDb))
        {
            d.worstDb = e;
            d.worstOrder = n;
        }
    }
    d.rmsDb = d.n > 0 ? std::sqrt(acc / (double) d.n) : 0.0;
    return d;
}

int main()
{
    std::printf("OSFidelity — Phase 10 probe: how far 1x/2x/4x sit from 8x, decomposed\n");
    std::printf("  reference = %dx.  All frequencies bin-exact; no window, no mask.\n", 1 << kRefOrder);
    std::printf("  ⚠ MODEL-vs-MODEL. Nothing here measures distance from the pedal.\n\n");

    // Params shared by the driven blocks: bleed-free OD, hard into the clipper.
    PedalChain::Params od;
    od.blend = 1.0; // pure OD — a clean tap would dilute the very difference being
    od.level = 1.0; //           measured, and it is not oversampled at all (GATE K2)
    od.drive = 0.85;
    od.master = 1.0;

    FitParams shipped{};        // clipAdaa = 1, clipAdaaMaxOs = 2
    FitParams noAdaa = shipped; // same build, gate disabled at every factor
    noAdaa.clipAdaaMaxOs = 0;

    // =============================================================================
    // 0. KNOWN ANSWERS. Neither is a fidelity number; both license the ones below.
    // =============================================================================
    std::printf("  [known-answer] determinism + clean-path factor invariance\n");

    // (a) Determinism — two fresh instances, identical settings, bit-identical out.
    {
        auto a = renderSine(od, 1, 1000.0, 0.3, 1 << 12, 0.3, shipped);
        auto b = renderSine(od, 1, 1000.0, 0.3, 1 << 12, 0.3, shipped);
        double worst = 0.0;
        for (size_t i = 0; i < a.size() && i < b.size(); ++i)
            worst = std::max(worst, std::abs(a[i] - b[i]));
        std::printf("     two fresh renders, same settings: worst |diff| = %.3e\n", worst);
        check(worst == 0.0, "renders are not deterministic — state is leaking between instances");
    }

    // (b) The clean path is base-rate and only DELAYED, so its magnitude is
    //     forbidden to depend on the OS factor. The residual IS the FR
    //     instrument's floor, and blocks 1/4 are gated against it, not a guess.
    double cleanFloorDb = 0.0;
    {
        PedalChain::Params clean = od;
        clean.blend = 0.0; // LevelBlend returns cleanIn exactly at B <= 0

        const int bins[] = { 137, 1092, 5461, 10923 }; // ~200 Hz / 1.6k / 8k / 16k
        std::printf("     BLEND=0 magnitude (dB) — must not move with factor:\n");
        std::printf("        freq        1x          2x          4x          8x      spread\n");
        for (int kb : bins)
        {
            const double f = kb * kFs / kFrN;
            double m[4];
            for (int o = 0; o < 4; ++o)
                m[o] = db(goertzelMag(renderSine(clean, o, f, 0.3, kFrN, kSettleSec, shipped), f));
            double lo = m[0], hi = m[0];
            for (int o = 1; o < 4; ++o)
            {
                lo = std::min(lo, m[o]);
                hi = std::max(hi, m[o]);
            }
            const double spread = hi - lo;
            cleanFloorDb = std::max(cleanFloorDb, spread);
            std::printf("     %8.1f  %10.5f  %10.5f  %10.5f  %10.5f  %9.2e\n",
                        f, m[0], m[1], m[2], m[3], spread);
        }
        std::printf("     => FR instrument floor (worst clean spread) = %.3e dB\n", cleanFloorDb);
        // The bar is one decade above the double-precision noise this path can
        // produce, NOT a tolerance on a physical quantity: the clean tap does not
        // pass through the oversampler at all, so anything above ~1e-9 dB means the
        // OS factor is reaching a stage it must not reach.
        check(cleanFloorDb < 1.0e-9,
              "clean-path magnitude moved with the OS factor — the clean tap is not factor-invariant");
    }
    std::printf("\n");

    // =============================================================================
    // 1. TOP-OCTAVE DROOP: the OD path's FR vs 8x, ADAA held OFF at every factor.
    //    ⛔ Its remedy is NOT Prewarp.h — see the header. These caps are inside the
    //    oversampled region, which dsp.md excludes from prewarping by name.
    // =============================================================================
    {
        // ⚠ THE LF PEDESTAL IS THIS BLOCK'S FLOOR, AND IT IS RECORDED AS UNEXPLAINED.
        // A constant +0.0055 dB where discretisation must give ~0 is a coincidence, and
        // this project's rule is to explain those rather than enjoy them — so it was
        // chased, and the obvious explanation was TESTED AGAINST ITS OWN PREDICTION AND
        // REFUTED, which is why no mechanism is named here:
        //   • NOT the settling residue that broke this file's first run. That is now
        //     2.4e-12 dB, measured by block 0(b) over the same settle; it cannot
        //     produce 0.0055.
        //   • NOT the oversampler's FIR passband ripple, which was the natural guess.
        //     JUCE's half-band FIR is applied once up and once down PER STAGE and the
        //     stage counts are 0/1/2/3 for 1x/2x/4x/8x, so ripple predicts the pedestal
        //     to GRADE 3:2:1 across 1x/2x/4x against the 8x reference. Measured at
        //     100-400 Hz it is ~1:1:1 (1x 0.0047-0.0068, 2x 0.0052-0.0055, 4x 0.0055
        //     flat). The signature is absent; the hypothesis is dead. Printing it as
        //     the explanation — which an earlier draft of this comment did — would be
        //     `an-attribution-is-not-a-measurement` committed inside the probe.
        //   • NOT the nonlinear solve converging with rate, which was the last cheap
        //     candidate and is what the [nl-probe] block below exists to test. A
        //     compressive stage solved at four rates need not deliver the same
        //     fundamental, but that predicts the pedestal to COLLAPSE as drive -> 0.
        //     Measured at 200.7 Hz, 4x re 8x: +0.00546 dB at DRIVE 0.15 and
        //     +0.00549 dB at DRIVE 0.01 — unchanged (fractionally LARGER), so the
        //     carrier is linear-side. The probe reprints this every run.
        // ⭐ WHAT THE STRUCTURE SAYS, since the mechanism does not: 1x/2x/4x form a
        // CLUSTER (2x and 4x agree to <0.0003 dB, 1x to ~0.002) and the 8x REFERENCE
        // sits ~0.0055 dB below all three. The odd arm is the reference, not the low
        // factors — so this is a property of the 3-stage/384 kHz path, not a droop that
        // grows as the factor falls. Anyone re-opening it should start there.
        // ⛔ AND THEN STOP. `know-when-to-stop-measuring`: this is 0.0055 dB = 0.06 %,
        // three orders of magnitude below every number this file quotes (the droop
        // findings are 2-21 dB), it moves no verdict, and three candidates have already
        // been excluded at the cost of one render pair each. It is recorded as a floor
        // with its exclusions, not as an open work item.
        PedalChain::Params lin = od;
        lin.drive = 0.15; // as linear as the OD path gets — this is a FILTER reading

        // Bin-exact, roughly log-spaced, 100 Hz .. 16 kHz over kFrN samples.
        const int bins[] = { 68, 137, 273, 546, 1092, 2185, 3413, 5461, 7509, 9557, 10923 };
        constexpr int nB = (int) (sizeof(bins) / sizeof(bins[0]));

        double magDb[4][nB];
        for (int i = 0; i < nB; ++i)
        {
            const double f = bins[i] * kFs / kFrN;
            for (int o = 0; o < 4; ++o)
                magDb[o][i] = db(goertzelMag(renderSine(lin, o, f, 0.3, kFrN, kSettleSec, noAdaa), f));
        }

        std::printf("  [droop] OD-path FR re %dx, DRIVE=0.15, ADAA OFF at all factors\n", 1 << kRefOrder);
        std::printf("          (ADAA held constant so this measures DISCRETISATION only)\n");
        std::printf("          ⚠ the few-thousandths-dB PEDESTAL on the LF rows is this block's\n");
        std::printf("            FLOOR, not droop, and it is UNEXPLAINED. It is not settling\n");
        std::printf("            residue (block 0(b) reads 2.4e-12 dB) and it is not FIR passband\n");
        std::printf("            ripple (that predicts a 3:2:1 grade across 1x/2x/4x; measured\n");
        std::printf("            ~1:1:1) and not the nonlinear solve (see [nl-probe]). 1x/2x/4x\n");
        std::printf("            CLUSTER and the 8x reference is the outlier. Nothing quoted\n");
        std::printf("            here depends on it — the droop findings are 2-21 dB.\n");
        std::printf("        freq         1x          2x          4x      (8x abs)\n");
        double worstDelta = 0.0;
        int worstIdx = 0;
        for (int i = 0; i < nB; ++i)
        {
            const double f = bins[i] * kFs / kFrN;
            const double d1 = magDb[0][i] - magDb[3][i];
            const double d2 = magDb[1][i] - magDb[3][i];
            const double d4 = magDb[2][i] - magDb[3][i];
            // 4 decimals, not 3: the passband-ripple pedestal discussed below is a
            // few thousandths of a dB and its GRADING BY STAGE COUNT is the evidence
            // that identifies it. At 3 decimals 2x and 4x tie and the grading vanishes.
            std::printf("     %8.1f  %+10.4f  %+10.4f  %+10.4f   %9.3f\n", f, d1, d2, d4, magDb[3][i]);
            if (std::abs(d1) > std::abs(worstDelta))
            {
                worstDelta = d1;
                worstIdx = i;
            }
            for (int o = 0; o < 4; ++o)
                check(std::isfinite(magDb[o][i]), "FR arm produced a non-finite magnitude");
        }
        std::printf("     => worst 1x deviation %+.3f dB at %.1f Hz"
                    "  (instrument floor %.1e dB, ratio %.2e)\n",
                    worstDelta, bins[worstIdx] * kFs / kFrN, cleanFloorDb,
                    std::abs(worstDelta) / (cleanFloorDb + 1e-300));

        // NON-VACUITY, gated on the MEASURED floor from block 0(b) rather than on a
        // number I picked. If the OS factor were not reaching the DSP this table
        // would be zeros and would read as "1x is already perfect".
        check(std::abs(worstDelta) > 1000.0 * cleanFloorDb,
              "1x OD FR is indistinguishable from 8x — the OS factor is not reaching the OD path");

        // --- [nl-probe] what the LF pedestal is, or at least what it is NOT ---------
        // The one remaining cheap candidate for a factor-dependent LF offset is the
        // NONLINEAR SOLVE converging with rate: at DRIVE 0.15 the OD path still
        // compresses, and a compressive stage evaluated at four different rates need
        // not deliver exactly the same fundamental. That predicts the pedestal to
        // COLLAPSE as drive -> 0, because a linear chain's LF response cannot depend
        // on the rate the nonlinearity is solved at. If it does NOT collapse, the
        // carrier is linear-side and this probe has excluded the nonlinearity too.
        // Either way the answer is printed rather than assumed — one render pair.
        {
            const double f = 200.68; // bin 137, the flattest row of the table above
            std::printf("     [nl-probe] LF pedestal vs DRIVE at %.1f Hz (4x re 8x)"
                        " — collapse => nonlinear solve:\n", f);
            for (const double dr : { 0.15, 0.01 })
            {
                PedalChain::Params q = lin;
                q.drive = dr;
                const double m4 = db(goertzelMag(renderSine(q, 2, f, 0.3, kFrN, kSettleSec, noAdaa), f));
                const double m8 = db(goertzelMag(renderSine(q, 3, f, 0.3, kFrN, kSettleSec, noAdaa), f));
                std::printf("        DRIVE %.2f :  4x-8x = %+.5f dB\n", dr, m4 - m8);
            }
        }
    }
    std::printf("\n");

    // =============================================================================
    // 2. WANTED DISTORTION vs ALIASING, driven. The separation build.md asks for.
    //    Again ADAA OFF everywhere, so this is the OS factor's own contribution.
    // =============================================================================
    // Two fundamentals, chosen for what each can show:
    //   • bin 173 -> 506.8 Hz: a bass-realistic fundamental with ~30 harmonics under
    //     Nyquist, so the LADDER is readable. OSValidationTest's own sweep says the
    //     alias floor is −85..−115 dB down here, i.e. this f0 is where the question
    //     "is the wanted distortion faithful?" is the whole question.
    //   • bin 853 -> 2499.0 Hz: OSValidationTest's f0, where that same sweep says
    //     the floor collapses to −17..−26 dB. Aliasing is the whole question here.
    // Quoting one without the other would be a statement about the chosen f0.
    struct Tone { int kBin; const char* what; };
    const Tone tones[] = { { 173, "bass-realistic (ladder-dominated)" },
                           { 853, "2499 Hz (alias-dominated)" } };
    constexpr double kLadderFloorDb = -100.0; // re the REFERENCE's own H1

    for (const auto& t : tones)
    {
        const double f0 = t.kBin * kFs / kFftN;
        Spectrum sp[4];
        for (int o = 0; o < 4; ++o)
            sp[o] = analyseDriven(od, o, t.kBin, 0.35, noAdaa);

        std::printf("  [separate] f0 = %.2f Hz — %s (ADAA OFF at all factors)\n", f0, t.what);
        std::printf("     ladder split at %.0f Hz: BELOW it block 1 measures the 1x FR deficit at\n"
                    "     <0.5 dB, so that column is a GENERATION reading; ABOVE it the droop\n"
                    "     reaches -21 dB and the column is the droop seen through the harmonics.\n",
                    kLadderSplitHz);
        std::printf("     factor   ladder<%.0fk   worst      ladder>%.0fk   worst      alias/sig  alias re 8x   lf\n",
                    kLadderSplitHz / 1000.0, kLadderSplitHz / 1000.0);
        for (int o = 0; o < 4; ++o)
        {
            const auto lo = ladderDistance(sp[o], sp[kRefOrder], kLadderFloorDb, f0, 0.0, kLadderSplitHz);
            const auto hi = ladderDistance(sp[o], sp[kRefOrder], kLadderFloorDb, f0, kLadderSplitHz, 1e9);
            std::printf("       %dx    %8.3f dB  %+6.2f(H%-2d)  %8.3f dB  %+7.2f(H%-2d)  %+8.1f dB  %+8.2f dB %+7.1f\n",
                        1 << o, lo.rmsDb, lo.worstDb, lo.worstOrder, hi.rmsDb, hi.worstDb, hi.worstOrder,
                        sp[o].aliasToSigDb, sp[o].aliasToSigDb - sp[kRefOrder].aliasToSigDb, sp[o].lfToSigDb);
            check(sp[o].nonFinite == 0, "driven arm produced non-finite output");
            check(std::isfinite(sp[o].h1Db), "driven arm H1 is not finite");
        }
        const auto rLo = ladderDistance(sp[kRefOrder], sp[kRefOrder], kLadderFloorDb, f0, 0.0, kLadderSplitHz);
        const auto rHi = ladderDistance(sp[kRefOrder], sp[kRefOrder], kLadderFloorDb, f0, kLadderSplitHz, 1e9);
        std::printf("     ladder membership: %d orders below / %d above, resolved by the %dx reference"
                    " above %.0f dB re its H1\n",
                    rLo.n, rHi.n, 1 << kRefOrder, kLadderFloorDb);
        // `empty-gate-must-fail`: an rms over zero orders is 0.000 and reads as perfect.
        // Both bands must be populated, or a column silently means "nothing measured".
        check(rLo.n > 0, "no harmonic orders below the split survived the reference floor — that rms is vacuous");
        check(rHi.n > 0, "no harmonic orders above the split survived the reference floor — that rms is vacuous");
        // The reference against itself must be exactly zero: an estimator that always
        // returns something cannot report agreement (session 126).
        check(rLo.rmsDb == 0.0 && rHi.rmsDb == 0.0,
              "reference-vs-itself ladder distance is non-zero — the metric cannot report agreement");
        std::printf("\n");
    }

    // =============================================================================
    // 3. THE SHIPPED ADAA POLICY, JUDGED AS FIDELITY RATHER THAN AS ALIAS ENERGY.
    //    Never asked before: both prior instruments (GATE X, OSValidationTest's
    //    benefit column) score ADAA on the alias floor ALONE. Here both arms are
    //    scored against the SAME 8x reference, which carries no ADAA either way,
    //    so "closer to 8x" is a like-for-like comparison.
    // =============================================================================
    {
        std::printf("  [policy] shipped (ADAA on at <=%dx) vs ADAA-off control, both re the %dx reference\n",
                    shipped.clipAdaaMaxOs, 1 << kRefOrder);
        std::printf("     negative 'delta' = the shipped policy is CLOSER to 8x on that axis\n");

        for (const auto& t : tones)
        {
            const double f0 = t.kBin * kFs / kFftN;
            const Spectrum ref = analyseDriven(od, kRefOrder, t.kBin, 0.35, noAdaa);

            std::printf("     f0 = %.2f Hz\n", f0);
            std::printf("        factor  arm       ladder<%.0fk    alias/sig     | delta ladder   delta alias\n",
                        kLadderSplitHz / 1000.0);
            for (int o = 0; o <= 1; o++) // 1x and 2x — the only factors the gate reaches
            {
                const Spectrum on = analyseDriven(od, o, t.kBin, 0.35, shipped);
                const Spectrum off = analyseDriven(od, o, t.kBin, 0.35, noAdaa);
                // LOW band only. The droop is identical in both arms (ADAA does not touch
                // the linear discretisation) but an rms is not linear, so differencing two
                // droop-dominated rms values would not cancel it — it would just bury the
                // ADAA effect under a common term ~20x larger.
                const auto dOn = ladderDistance(on, ref, kLadderFloorDb, f0, 0.0, kLadderSplitHz);
                const auto dOff = ladderDistance(off, ref, kLadderFloorDb, f0, 0.0, kLadderSplitHz);

                std::printf("          %dx    ADAA off  %8.3f dB  %+9.1f dB\n",
                            1 << o, dOff.rmsDb, off.aliasToSigDb);
                std::printf("          %dx    SHIPPED   %8.3f dB  %+9.1f dB  | %+9.3f dB  %+9.2f dB\n",
                            1 << o, dOn.rmsDb, on.aliasToSigDb,
                            dOn.rmsDb - dOff.rmsDb, on.aliasToSigDb - off.aliasToSigDb);

                // (5) SCOPE, third code path: the gate reaches 1x/2x and only those.
                check(on.aliasToSigDb != off.aliasToSigDb || on.h1Db != off.h1Db,
                      "shipped == ADAA-off control at a GATED-ON factor — the policy is not applying");
            }

            // The other half of the scope check: 4x/8x must be BIT-IDENTICAL.
            for (int o = 2; o <= 3; ++o)
            {
                auto a = renderSine(od, o, f0, 0.35, 1 << 12, 0.3, shipped);
                auto b = renderSine(od, o, f0, 0.35, 1 << 12, 0.3, noAdaa);
                double worst = 0.0;
                for (size_t i = 0; i < a.size() && i < b.size(); ++i)
                    worst = std::max(worst, std::abs(a[i] - b[i]));
                check(worst == 0.0,
                      "shipped != ADAA-off control at a GATED-OFF factor — ADAA is leaking past clipAdaaMaxOs");
            }
        }
    }

    std::printf("\n");
    if (failures == 0)
        std::printf("OSFidelity: all structural checks PASSED (%d failures). "
                    "Fidelity numbers are REPORTED, not gated.\n", failures);
    else
        std::printf("OSFidelity: %d FAILURE(S).\n", failures);
    return failures == 0 ? 0 : 1;
}
