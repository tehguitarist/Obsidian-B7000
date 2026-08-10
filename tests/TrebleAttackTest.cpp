// =============================================================================
// TrebleAttack (treble net + ATTACK switch) — frequency-response validation
// =============================================================================
// Validates the MNA stage against the continuous-time analytic oracle
// (analysis/eq_reference.py :: treble_attack_tf, CORRECTED 2026-07-20 topology)
// for all three ATTACK positions (Boost / Flat / Cut).
//
// The stage discretises its caps with the trapezoidal (bilinear) rule, so near
// Nyquist it warps vs the continuous oracle. We therefore:
//   * assert tight agreement (<=0.25 dB) where warp is negligible (<= 2 kHz),
//   * at 5 k / 10 kHz, assert the error SHRINKS from 48 k to 96 k (proving the
//     deviation is bilinear warp, not a model error) and is small at 96 k.
// In the full plugin this stage runs inside the oversampled region (dsp.md), so
// the top-octave warp is resolved there; this isolated test documents it.
//
// Also checks: (a) NO position mutes (a regression guard for the switch-pole
// bug that grounded node M), and (b) all three positions share the same low end
// (they differ only in treble).
// =============================================================================

#include "../src/dsp/TrebleAttack.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <vector>

static constexpr double PI = 3.14159265358979323846;

// Oracle reference from analysis/eq_reference.py :: treble_attack_transimpedance
// at these frequencies, in dB re 1 ohm — the stage takes the J201 drain's NORTON
// CURRENT now, so its transfer is a TRANSIMPEDANCE V(Q)/I, not a voltage gain
// (TrebleAttack.h "Stage boundary", 2026-07-22). The oracle is evaluated at
// JfetStage's NOMINAL gm/ro/Rq2, which is what a default-constructed stage uses.
// Regenerate if component values or those nominals change (single source of
// truth = the oracle).
struct Ref { double f; double boost, flat, cut; };
static const std::vector<Ref> kRef = {
    //  f Hz     boost       flat        cut
    {     50.0,   85.6449,   85.6596,   85.6498 },
    {    100.0,   77.3194,   77.3275,   77.3132 },
    {    200.0,   65.5089,   65.4789,   65.4522 },
    {    500.0,   60.5204,   60.2031,   60.1079 },
    {   1000.0,   65.9664,   64.7786,   64.4641 },
    {   2000.0,   68.9722,   65.7957,   64.7078 },
    {   5000.0,   72.2762,   66.0806,   61.6870 },
    {  10000.0,   73.4138,   66.1214,   57.0993 },
};

// Damped golden set (session-19): treble_attack_tf(..., RdampC5 = kTestDampR),
// same Zs recipe as kRef. Validates the lossy-C5 notch-damping code path against
// the independent Python oracle. Regenerate alongside kRef if anything changes.
static constexpr double kTestDampR = 30000.0;
static const std::vector<Ref> kRefDamped = {
    //  f Hz     boost       flat        cut
    {      50.0,   85.2483,   85.2633,   85.2534 },
    {     100.0,   77.0918,   77.1006,   77.0860 },
    {     200.0,   67.7351,   67.7059,   67.6789 },
    {     500.0,   63.0893,   62.7722,   62.6769 },
    {    1000.0,   65.5173,   64.3293,   64.0149 },
    {    2000.0,   67.9486,   64.7717,   63.6840 },
    {    5000.0,   71.0821,   64.8864,   60.4928 },
    {   10000.0,   72.1943,   64.9021,   55.8799 },
};

static double refFor(const Ref& r, TrebleAttack::Attack a)
{
    switch (a)
    {
        case TrebleAttack::Attack::Boost: return r.boost;
        case TrebleAttack::Attack::Flat:  return r.flat;
        case TrebleAttack::Attack::Cut:   return r.cut;
    }
    return 0.0;
}

// Steady-state peak magnitude (dB re 1 ohm, i.e. volts out per amp in — the stage
// is driven by the J201's Norton current). Settles then measures over 2 periods.
static double measureDb(double freq, double fs, TrebleAttack::Attack a, double dampR = 0.0)
{
    TrebleAttack stage;
    stage.prepare(fs);
    stage.setAttack(a);
    stage.setNotchDamp(dampR); // session-19: lossy-C5 notch damping (0 = ideal)

    const double period = fs / freq;
    // 2 s, not the old 0.25 s: with the J201 source network stamped in (2026-07-22),
    // node G floats on ~396 kOhm against the 22 nF ladder, adding a time constant slow
    // enough that 0.25 s left a ~0.4 dB settling error at 200 Hz — which looks exactly
    // like a model error but is not (at 2 s the agreement is <= 0.005 dB below 1 kHz).
    const int settle = static_cast<int>(std::max(2.0 * fs, 8.0 * period));
    const int measure = static_cast<int>(std::ceil(2.0 * period)) + 1;

    double peak = 0.0;
    for (int n = 0; n < settle + measure; ++n)
    {
        const double x = std::sin(2.0 * PI * freq * static_cast<double>(n) / fs);
        const double y = stage.process(x);
        if (n >= settle)
            peak = std::max(peak, std::abs(y));
    }
    return (peak > 0.0) ? 20.0 * std::log10(peak) : -300.0;
}

// ---- Test 8's reference: the TWO-POLE ATTACK topology ----
// Fixed reference values for the per-throw series collapse of the split top rail.
// Cross-checked once against an independent uncollapsed 8-node solve (worst 2.1e-14 dB
// at the split point) rather than derived from the same algebra being tested here.
static constexpr double kTapRa = 470.0e3, kTapRb = 506.0e3, kTapRc = 78.5e3, kTapR11 = 212.0e3;
static constexpr double kC5Base = 19.7e-9, kC5TrimBoost = 1.1e-9, kC5TrimCut = 2.7e-9;
static constexpr double kRdFlat = 6.14e3, kRdBoost = 478.0, kRdCut = 6.04e3;
static constexpr double kPropC7 = 680.0e-12;   // the shipped trebleC7
static const std::vector<Ref> kRefTwoPole = {
    //  f Hz     boost       flat        cut
    {     50.0,   76.1844,   67.6804,   64.3507 },
    {    100.0,   73.0341,   64.6679,   61.1442 },
    {    200.0,   65.0816,   57.1044,   53.1630 },
    {    320.0,   38.7566,   41.5400,   37.9129 },
    {    500.0,   60.9209,   52.4546,   50.6858 },
    {   1000.0,   66.1470,   57.6584,   55.3804 },
    {   2000.0,   67.3080,   58.7961,   56.4347 },
};

// Configure a stage at the two-pole proposal (C8 REMOVED — that is what session 62
// actually screened, so leaving 220 pF in would not be the same proposal).
static void configureTwoPole(TrebleAttack& stage)
{
    stage.setC7(kPropC7);
    stage.setC8(0.0);
    stage.setAttackTap(kTapRa, kTapRb, kTapRc, kTapR11);
    // ⚠ setNotchDamp() writes ALL THREE throws by design, so per-throw values must
    // come after it — the same ordering constraint PedalChain::applyParams obeys.
    stage.setNotchDamp(kRdFlat);
    stage.setNotchLeg(TrebleAttack::Attack::Flat, kC5Base, kRdFlat);
    stage.setNotchLeg(TrebleAttack::Attack::Boost, kC5Base + kC5TrimBoost, kRdBoost);
    stage.setNotchLeg(TrebleAttack::Attack::Cut, kC5Base + kC5TrimCut, kRdCut);
}

static double measureTwoPoleDb(double freq, double fs, TrebleAttack::Attack a)
{
    TrebleAttack stage;
    stage.prepare(fs);
    configureTwoPole(stage);
    stage.setAttack(a);

    const double period = fs / freq;
    const int settle = static_cast<int>(std::max(2.0 * fs, 8.0 * period));
    const int measure = static_cast<int>(std::ceil(2.0 * period)) + 1;
    double peak = 0.0;
    for (int n = 0; n < settle + measure; ++n)
    {
        const double x = std::sin(2.0 * PI * freq * static_cast<double>(n) / fs);
        const double y = stage.process(x);
        if (n >= settle)
            peak = std::max(peak, std::abs(y));
    }
    return (peak > 0.0) ? 20.0 * std::log10(peak) : -300.0;
}

int main()
{
    int failures = 0;
    const char* names[3] = { "Boost", "Flat", "Cut" };
    const TrebleAttack::Attack positions[3] = {
        TrebleAttack::Attack::Boost, TrebleAttack::Attack::Flat, TrebleAttack::Attack::Cut
    };

    // ---- Test 1: FR vs oracle at 48 kHz (tight <= 2 kHz) --------------------
    std::printf("=== FR vs analytic oracle @ 48 kHz ===\n");
    for (int pi = 0; pi < 3; ++pi)
    {
        std::printf("--- ATTACK = %s ---\n", names[pi]);
        for (const auto& r : kRef)
        {
            const double meas = measureDb(r.f, 48000.0, positions[pi]);
            const double ref = refFor(r, positions[pi]);
            const double err = std::abs(meas - ref);
            const double tol = (r.f <= 2000.0) ? 0.25 : 100.0; // HF handled by Test 2
            const bool checked = (r.f <= 2000.0);
            const bool pass = err <= tol;
            std::printf("  f=%8.1f  meas=%8.3f  ref=%8.3f  err=%.3f dB  %s\n",
                        r.f, meas, ref, err, checked ? (pass ? "PASS" : "FAIL") : "(HF: see Test 2)");
            if (checked && ! pass)
                ++failures;
        }
    }

    // ---- Test 2: HF deviation is bilinear warp (shrinks 48k -> 96k) ---------
    std::printf("\n=== HF: error must shrink from 48k to 96k (warp), and be small at 96k ===\n");
    for (int pi = 0; pi < 3; ++pi)
    {
        for (const auto& r : kRef)
        {
            if (r.f < 5000.0) continue;
            const double ref = refFor(r, positions[pi]);
            const double e48 = std::abs(measureDb(r.f, 48000.0, positions[pi]) - ref);
            const double e96 = std::abs(measureDb(r.f, 96000.0, positions[pi]) - ref);
            // "Shrinks with rate" is the signature of bilinear warp. But when the 48 k
            // error is ALREADY negligible there is no warp to shrink, and the
            // rate-to-rate difference is just measurement noise — so an already-tiny
            // e96 passes on its own. (Flat sits at ~0.005 dB at both rates: that is a
            // stronger result than "shrinks", not a weaker one.)
            const bool shrinks = e96 < e48 + 1e-9 || e96 <= 0.05;
            const bool small96 = e96 <= 0.30;
            const bool pass = shrinks && small96;
            std::printf("  %-5s f=%8.1f  err48=%.3f  err96=%.3f  %s\n",
                        names[pi], r.f, e48, e96,
                        pass ? "PASS" : (! shrinks ? "FAIL (not warp!)" : "FAIL (96k too big)"));
            if (! pass)
                ++failures;
        }
    }

    // ---- Test 3: NO position mutes (switch-pole-bug regression guard) -------
    std::printf("\n=== No position mutes (regression guard for the M->GND mute bug) ===\n");
    for (int pi = 0; pi < 3; ++pi)
    {
        const double meas = measureDb(1000.0, 48000.0, positions[pi]);
        // Real transimpedance here is ~ +64..+66 dB re 1 ohm; a mute reads < -200.
        const bool pass = meas > 0.0;
        std::printf("  %-5s @1kHz = %.2f dB  %s\n", names[pi], meas,
                    pass ? "PASS (signal present)" : "FAIL (MUTED!)");
        if (! pass)
            ++failures;
    }

    // ---- Test 4: all positions share the low end (differ only in treble) ---
    std::printf("\n=== Low-end consistency across positions (@100 Hz) ===\n");
    {
        const double b = measureDb(100.0, 48000.0, TrebleAttack::Attack::Boost);
        const double f = measureDb(100.0, 48000.0, TrebleAttack::Attack::Flat);
        const double c = measureDb(100.0, 48000.0, TrebleAttack::Attack::Cut);
        const double spread = std::max({ b, f, c }) - std::min({ b, f, c });
        const bool pass = spread < 0.10;
        std::printf("  boost=%.3f flat=%.3f cut=%.3f  spread=%.3f dB  %s\n",
                    b, f, c, spread, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    // ---- Test 5: treble ordering Boost > Flat > Cut at 5 kHz ----------------
    std::printf("\n=== Treble ordering Boost > Flat > Cut (@5 kHz) ===\n");
    {
        const double b = measureDb(5000.0, 48000.0, TrebleAttack::Attack::Boost);
        const double f = measureDb(5000.0, 48000.0, TrebleAttack::Attack::Flat);
        const double c = measureDb(5000.0, 48000.0, TrebleAttack::Attack::Cut);
        const bool pass = (b > f + 1.0) && (f > c + 1.0);
        std::printf("  boost=%.3f > flat=%.3f > cut=%.3f  %s\n", b, f, c, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    // ---- Test 6: notch damping (lossy C5) matches the oracle at Rd>0 --------
    // Validates the session-19 trebleLadderDampR code path (setNotchDamp): the C++
    // lossy-cap Norton reduction must track the independent Python oracle's series
    // Rd+C5 admittance. Same tight <=2 kHz tolerance as Test 1 (HF is warp, Test 2).
    std::printf("\n=== Notch damping (Rd=%.0f) vs oracle @ 48 kHz ===\n", kTestDampR);
    for (int pi = 0; pi < 3; ++pi)
    {
        std::printf("--- ATTACK = %s ---\n", names[pi]);
        for (const auto& r : kRefDamped)
        {
            if (r.f > 2000.0) continue; // HF warp not re-checked here (Test 2 covers it)
            const double meas = measureDb(r.f, 48000.0, positions[pi], kTestDampR);
            const double ref = refFor(r, positions[pi]);
            const double err = std::abs(meas - ref);
            const bool pass = err <= 0.25;
            std::printf("  f=%8.1f  meas=%8.3f  ref=%8.3f  err=%.3f dB  %s\n",
                        r.f, meas, ref, err, pass ? "PASS" : "FAIL");
            if (! pass)
                ++failures;
        }
    }

    // ---- Test 7: notch damping shallows the ~322 Hz two-path cancellation ---
    // The whole point of Rd: the ideal notch (~28 dB) is far deeper than the
    // capture (-3.4 dB). Damping must raise the ~320 Hz null relative to Rd=0.
    std::printf("\n=== Notch damping shallows the 320 Hz null (Boost) ===\n");
    {
        const double ideal = measureDb(320.0, 48000.0, TrebleAttack::Attack::Boost, 0.0);
        const double damped = measureDb(320.0, 48000.0, TrebleAttack::Attack::Boost, kTestDampR);
        const bool pass = damped > ideal + 3.0; // meaningfully shallower
        std::printf("  320 Hz: ideal=%.2f  damped=%.2f  lift=%.2f dB  %s\n",
                    ideal, damped, damped - ideal, pass ? "PASS" : "FAIL");
        if (! pass)
            ++failures;
    }

    // ---- Test 8: the TWO-POLE ATTACK topology vs the oracle -----------------
    // Validates both poles at once: the moving tap on the split top rail (pole A)
    // and the per-throw C5/Rd notch leg (pole B). The reference table above was
    // cross-checked against an independent 8-node solve before being fixed here.
    std::printf("\n=== TWO-POLE ATTACK topology vs oracle @ 48 kHz ===\n");
    for (int pi = 0; pi < 3; ++pi)
    {
        std::printf("--- ATTACK = %s ---\n", names[pi]);
        for (const auto& r : kRefTwoPole)
        {
            if (r.f > 2000.0)
                continue; // HF is bilinear warp; Test 2 covers that mechanism
            const double meas = measureTwoPoleDb(r.f, 48000.0, positions[pi]);
            const double ref = refFor(r, positions[pi]);
            const double err = std::abs(meas - ref);
            // ⚠ 320 Hz sits ON the cancellation null, and a first draft of this test
            // pre-loosened it to 1.5 dB on the reasoning that a null's depth is a
            // difference of near-equal terms and so must discretise badly. MEASURED,
            // it does not: the error there is 0.002-0.042 dB, the same order as every
            // smooth band. The loosened tolerance was therefore removed — a gate
            // slacker than the data needs is a gate that will not catch a regression.
            const double tol = 0.25;
            const bool pass = err <= tol;
            std::printf("  f=%8.1f  meas=%8.3f  ref=%8.3f  err=%.3f dB (tol %.2f)  %s\n",
                        r.f, meas, ref, err, tol, pass ? "PASS" : "FAIL");
            if (! pass)
                ++failures;
        }
    }

    // ---- Test 9: the two poles do the two jobs, and do them SEPARATELY ------
    // This is the structural claim, not a value check: session 62's whole case for a
    // TWO-pole switch is that the broadband gain and the notch are carried by
    // non-interacting groups. Assert exactly that, so a future refactor that
    // accidentally couples them fails here rather than silently degrading a fit.
    std::printf("\n=== Two poles, two jobs, no cross-talk ===\n");
    {
        // (a) POLE A ALONE (tap split, notch leg shared): must move the broadband
        //     level a lot and the ~320 Hz null essentially not at all.
        auto measure = [](double freq, TrebleAttack::Attack a, bool tap, bool leg) {
            TrebleAttack stage;
            stage.prepare(48000.0);
            stage.setC7(kPropC7);
            stage.setC8(0.0);
            if (tap)
                stage.setAttackTap(kTapRa, kTapRb, kTapRc, kTapR11);
            stage.setNotchDamp(kRdFlat);
            if (leg)
            {
                stage.setNotchLeg(TrebleAttack::Attack::Boost, kC5Base + kC5TrimBoost, kRdBoost);
                stage.setNotchLeg(TrebleAttack::Attack::Cut, kC5Base + kC5TrimCut, kRdCut);
                stage.setNotchLeg(TrebleAttack::Attack::Flat, kC5Base, kRdFlat);
            }
            stage.setAttack(a);
            const double period = 48000.0 / freq;
            const int settle = static_cast<int>(std::max(2.0 * 48000.0, 8.0 * period));
            const int meas = static_cast<int>(std::ceil(2.0 * period)) + 1;
            double peak = 0.0;
            for (int n = 0; n < settle + meas; ++n)
            {
                const double x = std::sin(2.0 * PI * freq * static_cast<double>(n) / 48000.0);
                const double y = stage.process(x);
                if (n >= settle)
                    peak = std::max(peak, std::abs(y));
            }
            return (peak > 0.0) ? 20.0 * std::log10(peak) : -300.0;
        };
        // Broadband probe at 1 kHz (well clear of the null); notch depth as the
        // 320 Hz level relative to the 254 Hz shoulder, the probe's own convention.
        const double tapBoost = measure(1000.0, TrebleAttack::Attack::Boost, true, false)
                                - measure(1000.0, TrebleAttack::Attack::Flat, true, false);
        const double legBoost = measure(1000.0, TrebleAttack::Attack::Boost, false, true)
                                - measure(1000.0, TrebleAttack::Attack::Flat, false, true);
        const bool aGain = tapBoost > 6.0;    // pole A carries the broadband gain
        const bool bFlat = std::abs(legBoost) < 0.5; // pole B is broadband-NEUTRAL
        std::printf("  pole A alone, boost-vs-flat @1 kHz: %+7.2f dB  (want > +6)   %s\n",
                    tapBoost, aGain ? "PASS" : "FAIL");
        std::printf("  pole B alone, boost-vs-flat @1 kHz: %+7.2f dB  (want ~0)     %s\n",
                    legBoost, bFlat ? "PASS" : "FAIL");
        if (! aGain)
            ++failures;
        if (! bFlat)
            ++failures;

        // Pole B must be what deepens boost's null. Depth measured against the
        // 254 Hz shoulder so a broadband level change cannot masquerade as depth.
        const double depthTapOnly = measure(254.0, TrebleAttack::Attack::Boost, true, false)
                                    - measure(320.0, TrebleAttack::Attack::Boost, true, false);
        const double depthBoth = measure(254.0, TrebleAttack::Attack::Boost, true, true)
                                 - measure(320.0, TrebleAttack::Attack::Boost, true, true);
        const bool deepens = depthBoth > depthTapOnly + 5.0;
        std::printf("  boost null depth re 254 Hz: pole A only %.2f -> both %.2f dB   %s\n",
                    depthTapOnly, depthBoth, deepens ? "PASS" : "FAIL");
        if (! deepens)
            ++failures;
    }

    // ---- Test 10: the SHARED ladder is plumbed, BOTH WAYS -------------------
    // Session 64. R7/R12/R14/C9/C6 were `static constexpr` and reachable from no
    // tool (session 50's next-step (a)); they are now setLadder(). The standing rule
    // for this kind of change is session 37 item 12 / session 45 item 7a: verify
    // plumbing in BOTH directions, because "default == explicit nominal" passes on
    // its own even when NOTHING was actually rebuilt — that is the trap, not the test.
    {
        std::printf("\n-- Test 10: setLadder plumbing, both directions ---------------\n");
        constexpr double kR7 = 200.0e3, kR12 = 6.8e3, kR14 = 22.0e3;
        constexpr double kC9 = 22.0e-9, kC6 = 22.0e-9;

        // A short frequency-response fingerprint, taken through the real stage.
        const auto fingerprint = [](bool call, double r7, double r12, double r14,
                                    double c9, double c6) {
            TrebleAttack stage;
            stage.prepare(48000.0);
            if (call)
                stage.setLadder(r7, r12, r14, c9, c6);
            stage.setAttack(TrebleAttack::Attack::Flat);
            std::vector<double> out;
            for (double freq : { 101.0, 202.0, 320.0, 640.0, 2000.0 })
            {
                stage.reset();
                const int settle = 24000, n_ = 48000;
                double peak = 0.0;
                for (int n = 0; n < n_; ++n)
                {
                    const double y = stage.process(
                        std::sin(2.0 * PI * freq * static_cast<double>(n) / 48000.0));
                    if (n >= settle)
                        peak = std::max(peak, std::abs(y));
                }
                out.push_back(peak);
            }
            return out;
        };
        const auto same = [](const std::vector<double>& a, const std::vector<double>& b) {
            if (a.size() != b.size())
                return false;
            for (size_t i = 0; i < a.size(); ++i)
                if (std::memcmp(&a[i], &b[i], sizeof(double)) != 0)
                    return false;
            return true;
        };

        const auto base = fingerprint(false, 0, 0, 0, 0, 0);              // never call setLadder
        const auto nominal = fingerprint(true, kR7, kR12, kR14, kC9, kC6); // explicit drawn values
        const bool noop = same(base, nominal);
        std::printf("  default vs explicit-nominal setLadder: %s   %s\n",
                    noop ? "BIT-IDENTICAL" : "DIFFER",
                    noop ? "PASS" : "FAIL (the default is not the drawn network)");
        if (! noop)
            ++failures;

        // ...and every one of the five must be INDIVIDUALLY live, or a --fit key is
        // silently inert (the session-20 `--input-trim` defect: a value that parses,
        // is accepted, and never reaches the DSP).
        struct { const char* name; double r7, r12, r14, c9, c6; } probes[] = {
            { "R7  x1.3", kR7 * 1.3, kR12, kR14, kC9, kC6 },
            { "R12 x1.3", kR7, kR12 * 1.3, kR14, kC9, kC6 },
            { "R14 x1.3", kR7, kR12, kR14 * 1.3, kC9, kC6 },
            { "C9  x1.3", kR7, kR12, kR14, kC9 * 1.3, kC6 },
            { "C6  x1.3", kR7, kR12, kR14, kC9, kC6 * 1.3 },
        };
        for (const auto& p : probes)
        {
            const auto got = fingerprint(true, p.r7, p.r12, p.r14, p.c9, p.c6);
            const bool live = ! same(base, got);
            double worst = 0.0;
            for (size_t i = 0; i < got.size(); ++i)
                worst = std::max(worst, std::abs(20.0 * std::log10(got[i] / base[i])));
            std::printf("  %s: %s (worst %.3f dB)   %s\n", p.name,
                        live ? "LIVE" : "INERT", worst, live ? "PASS" : "FAIL");
            if (! live)
                ++failures;
        }
    }

    std::printf("\n%s\n", failures == 0 ? "All tests passed." : "Some tests FAILED.");
    return (failures > 0) ? 1 : 0;
}
