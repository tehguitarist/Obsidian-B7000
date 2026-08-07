#pragma once

#include <algorithm>
#include <cmath>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// =============================================================================
// OdMakeup — engineered (NON-SCHEMATIC) OD:CLEAN RATIO correction
// =============================================================================
// Session 172, open work item 10 / A3.  Sits on the OD branch AT the LevelBlend
// summing node, base rate.  ✅ SHIPPED (FitParams: +6.0 dB, low 130 Hz / -3.5,
// high 2800 Hz / -6.0), USER DECISION 2026-08-07, priced first.  Setting gainDb
// and both cuts to 0 reproduces every pre-s172 build BIT-IDENTICALLY — that is
// the control every number below was measured against, and it still works.
//
// ---------------------------------------------------------------------------
// WHAT IT FIXES, AND WHY IT IS A RATIO AND NOT A FILTER
// ---------------------------------------------------------------------------
// User report: the 320 Hz null, the ~450 Hz recovery peak and the ~800 Hz
// bridged-T notch are ALL under-contrasted at most settings.  Measured, that is
// ONE defect with a signature no filter can produce:
//
//   * BLEED-FREE (LEVEL max AND BLEND max — the only bleed-free corner, GATE K2)
//     the model is RIGHT.  The 320 Hz null sits within +-0.41 dB of the pedal at
//     all three drive rungs, and the notch-peak-notch excursion reads 14.07 dB
//     against the pedal's 13.92.
//   * At EVERY mixed setting it collapses, on BOTH mix axes independently, and
//     worst at MODERATE mix (LEVEL 0.875: pedal 7.14 dB vs model 2.48; BLEND
//     1430 at LEVEL max: 6.32 vs 3.67).
//
// Zero error bleed-free, peaking mid-mix, is the DILUTION signature: the
// composite carries too much clean relative to OD, so every feature flattens at
// once.  ⛔ A deeper notch cannot fix it — s156 measured the DEPTH CEILING (a
// deliberate 40 dB OD-path cut buys 0.47 dB of composite null at the listening
// mix, SHALLOWER than the shipped 12.34 dB cut's 1.60).  The lever is the ratio.
//
// The ratio, measured with each side differenced against ITSELF so every
// per-side capture-chain scalar cancels exactly (pure OD minus pure CLEAN, dB):
// the model's OD path is quiet re its own clean path by -4.97 / -5.00 / -5.74 dB
// over 250-900 Hz at the three stimulus rungs — stable to 0.77 dB over a 12 dB
// span, and an independent third reading of GATE O's A3 deficit (4.40 dB).
//
// ---------------------------------------------------------------------------
// ⭐ WHY RAISING THE OD PATH DEEPENS A NOTCH (the non-obvious half)
// ---------------------------------------------------------------------------
// At a composite notch's BOTTOM the OD path is already nulled, so the floor is
// set by the clean tap and boosting the OD path there does almost nothing.  What
// moves is the SHOULDERS.  The ~450 Hz recovery peak IS the shoulder between the
// two notches — so ONE correction raises the peak and deepens both notches
// together, which is exactly the three-part defect reported.
//
// ---------------------------------------------------------------------------
// ⚠⚠ THE FLAT TERM CANNOT CHANGE ANY BLEED-FREE CONTRAST — AND THAT IS THE
// REASON THE CORRECTION IS SHAPED THE WAY IT IS
// ---------------------------------------------------------------------------
// Bleed-free the composite IS the OD branch, so a constant cancels from every
// difference taken within that curve.  Measured across a 0 -> 7.5 dB sweep, the
// bleed-free excursion moves 0.0000 dB.  The one condition that is already
// correct is therefore protected BY CONSTRUCTION, not by tuning — a free known
// answer, and the reason a plain BELL was rejected: a Q~0.6 bell at 500 Hz moves
// that excursion ~1.5 dB and would overshoot the one cell that is already right.
//
// The two SHELVES exist because the deficit is NOT flat outside the midrange
// (-1.4 dB at 101 Hz, -0.8 at 4 kHz, and POSITIVE above 5 kHz), so a bare flat
// gain over-boosts the OD path's extremes.  ⛔ Their corners are placed OUTSIDE
// the feature span (mid_notch 285-358, mid_peak 358-620, bt_notch 620-905 Hz) on
// purpose: a shelf whose transition reached a feature would re-introduce exactly
// the bleed-free contrast change the flat form was chosen to avoid.  Keep
// lowHz well below 285 and highHz well above 905, and re-assert the bleed-free
// invariance after ANY corner change — it is one render and it is the guard.
//
// ---------------------------------------------------------------------------
// ⚠ WHAT THIS STAGE DOES NOT DO
// ---------------------------------------------------------------------------
//  * It does NOT re-key OdToneRestore.  It is applied OUTSIDE
//    LevelBlend::process(), so LevelBlend::cleanFraction() still reports the
//    POT-LAW clean fraction and the s156 mix law behaves exactly as today.  That
//    is deliberate (one change at a time — folding it in would re-key the notch
//    stage in the same edit and make the two effects unattributable), and its
//    consequence is that the notch stage keeps applying its old, LARGER dilution
//    correction, so residual error lands on the TOO-DEEP side.  Re-fitting item
//    10's acceptance table on top of a shipped makeup is owed, separately.
//  * It does NOT touch CLEAN.  At BLEND = 0 the OD branch is out of circuit;
//    asserted bit-identical (0.000e+00) between 0 and +6 dB.
//  * ⚠⚠ IT OBSOLETES TWO FITS, and both re-fits are OWED, not optional.  The s163
//    LEVEL taper and s156's OdToneRestore mix law were each fitted while the OD
//    path was ~5 dB quiet, so both were partly compensating for the deficit this
//    stage now corrects.  Measured on a 100 Hz-4 kHz proxy, the delivered LEVEL
//    law read RELATIVE TO LEVEL MAX (which is how GATE AY/AZ defines it) degrades
//    from 0.4-1.4 dB to ~3.5 dB at the interior detents.  ⛔ Do not read that as a
//    regression in the taper — it is the taper being handed back a job it should
//    never have had.  Re-fit order: taper first (GATE AZ), then the mix law
//    (item 10's acceptance table), then re-baseline the matrix.
//  * It is NOT the item-6 drive-tilt stage and must not absorb it.  This one is
//    a fixed linear section on a MIX ratio; OdDriveTilt is level-dependent and
//    sits inside the oversampled region for reasons GATE BA/BB measured.
// =============================================================================
class OdMakeup
{
public:
    void prepare(double sampleRate) noexcept
    {
        fs = sampleRate;
        rebuild();
        reset();
    }

    void reset() noexcept
    {
        lo.resetState();
        hi.resetState();
        hf.resetState();
    }

    // gainDb      flat boost of the OD branch (the A3 ratio correction)
    // lowCutDb    how much of that boost is REMOVED below lowHz  (>= 0)
    // highCutDb   how much of that boost is REMOVED above highHz (>= 0)
    // lowS/highS  RBJ shelf slope. 0.9 = the s172 shipped value, so the defaults are
    //             bit-identical to that build. See FitParams::odMakeupHighS for why the
    //             SLOPE is a parameter and not a constant: it sets how much TILT the
    //             shelf presents at the features above it, independently of how much
    //             LEVEL it removes -- and the level and the tilt have different jobs.
    void setLaw(double gainDb, double lowHzIn, double lowCutDb,
                double highHzIn, double highCutDb,
                double lowSIn = 0.9, double highSIn = 0.9) noexcept
    {
        g = gainDb;
        lowHz = lowHzIn;
        loCut = lowCutDb;
        highHz = highHzIn;
        hiCut = highCutDb;
        loS = lowSIn;
        hiS = highSIn;
        rebuild();
    }

    // The mix-keyed HF term's own shape.  `atOd` is its gain at cleanFrac = 0 (pure OD), `peak`
    // its gain at `peakCf`, `atClean` its gain as cleanFrac -> 1.  Two straight segments in
    // cleanFrac, which is what the measured requirement is: one sign change and one turnover.
    void setHfMix(double hz, double q, double atOd, double peak, double peakCf,
                  double atClean) noexcept
    {
        hfHz = hz;
        hfQ = q;
        hfAtOd = atOd;
        hfPeak = peak;
        hfPeakCf = (peakCf < 1e-3) ? 1e-3 : (peakCf > 1.0 - 1e-3 ? 1.0 - 1e-3 : peakCf);
        hfAtClean = atClean;
        rebuild();
    }

    // The law itself, exposed so the analysis side can score it without re-deriving it.
    double hfGainDb() const noexcept
    {
        return (cleanFrac <= hfPeakCf)
                   ? hfAtOd + (hfPeak - hfAtOd) * (cleanFrac / hfPeakCf)
                   : hfPeak + (hfAtClean - hfPeak) * ((cleanFrac - hfPeakCf) / (1.0 - hfPeakCf));
    }

    // ---- THE MIX-KEYED HF TERM (s173) ------------------------------------------------------
    // ⛔⛔ WHY THIS EXISTS, AND WHY IT IS NOT A FIXED FILTER.  s172 fitted this whole stage at the
    // BLEED-FREE corner and s173 sized its corners there too.  Measured across the mix at the
    // user's stated playing level (`sweep_drv_-12`), the 4-8 kHz error CHANGES SIGN:
    //
    //     cleanFrac   0.000   0.335   0.397   0.431   0.458*  0.487   0.767   0.958
    //     4-8 kHz    +4.53   -1.49   -2.68   -3.27   -2.80   -2.01   -0.72   -0.95
    //                                                  * = ref-od, THE reference condition
    //
    // i.e. bleed-free says +4.5 dB TOO BRIGHT while every setting the instrument is actually
    // played at says 0.7-3.3 dB TOO DARK.  A fixed correction fitted at bleed-free therefore does
    // not merely miss elsewhere — IT PUSHES THE WRONG WAY.  That is the user's report, and it is
    // why this term is keyed on `LevelBlend::cleanFraction()` exactly as `OdToneRestore`'s s156
    // law is, rather than being another constant.
    // ⚠ The band is read as a MEDIAN, not a mean: 4-8 kHz contains the treble notch, and at one
    // capture (cleanFrac 0.335) the notch drags the band MEAN 4.35 dB away from the median. A
    // smooth law fitted to that mean would be fitting the notch's position, not the level.
    // ⚠ A PEAKING section, not a shelf — 8-16.3 kHz already measures right at every mixed setting
    // (+0.03…+0.71 at the ones that matter), so a shelf would break a band that is correct.
    void setCleanFraction(double cf) noexcept
    {
        cleanFrac = (cf < 0.0) ? 0.0 : (cf > 1.0 ? 1.0 : cf);
        rebuild();
    }

    inline double process(double x) noexcept
    {
        if (inert)
            return x;                      // exact identity — no state, no rounding
        return hf.process(hi.process(lo.process(x))) * flat;
    }

private:
    void rebuild() noexcept
    {
        flat = std::pow(10.0, g / 20.0);
        // A cut of 0 dB is an EXACT identity shelf, but running the biquad anyway
        // would still cost rounding; branch it out so "inert" means bit-identical.
        // ⚠ The HF term joins that condition: with all three of its gains at 0 the law returns 0
        // at EVERY cleanFrac, so the stage is inert as a whole and stays bit-identical to the
        // pre-s173 build — which is what makes the known answer below a real check.
        const bool hfOff = (hfAtOd == 0.0 && hfPeak == 0.0 && hfAtClean == 0.0);
        inert = (g == 0.0 && loCut == 0.0 && hiCut == 0.0 && hfOff);
        if (fs <= 0.0)
            return;
        lo.setShelf(fs, lowHz, clampS(loS, loCut), -std::abs(loCut), /*high=*/false);
        hi.setShelf(fs, highHz, clampS(hiS, hiCut), -std::abs(hiCut), /*high=*/true);
        hf.setPeaking(fs, hfHz, hfQ, hfOff ? 0.0 : hfGainDb());
    }

    // An RBJ shelf's `alpha` carries sqrt((A + 1/A)(1/S - 1) + 2), which goes imaginary once S
    // rises past 1/(1 - 2/(A + 1/A)) -- and the ceiling DEPENDS ON THE SHELF's own gain, so a
    // fixed upper bound is either wrong at some depth or needlessly tight at others. Solve it
    // instead, and keep a margin so the shelf stays a shelf rather than a resonance.
    // ⚠ S < 1 is the gentle side and is unconditionally valid; only the steep side can go
    // imaginary, which is why the floor is a plain positive number and the ceiling is derived.
    static double clampS(double s, double cutDb) noexcept
    {
        const double A = std::pow(10.0, -std::abs(cutDb) / 40.0);
        const double q = A + 1.0 / A;
        const double denom = 1.0 - 2.0 / q;
        // q <= 2 happens only at cutDb == 0 (A == 1), where the shelf is an exact identity and
        // S cannot matter; any finite value is then safe.
        const double hiLimit = (denom > 1e-12) ? (1.0 / denom) : 1e9;
        return std::min(std::max(s, 0.1), 0.98 * hiLimit);
    }

    // RBJ shelving biquad (Audio EQ Cookbook), direct form I transposed.  Shared
    // low/high implementation so the two corners cannot drift apart in form.
    struct Shelf
    {
        void setShelf(double fsIn, double cornerHz, double slopeS, double gainDb,
                      bool high) noexcept
        {
            // ⚠ A 0 dB shelf is an EXACT identity in real arithmetic (b == a term for term at
            // A = 1) but NOT in floating point: b1 and a1 are built by different expression
            // trees, so b1/a0 and a1/a0 differ in the last bits and the filter leaks ~1e-10.
            // Measured, s172: the "inert" shaped stage was 1.164e-10 off the plain scalar.
            // Harmless (-199 dBFS) and still wrong to claim as inert, so branch it out and the
            // claim becomes true instead of nearly true.
            ident = (gainDb == 0.0);
            if (ident)
                return;
            const double A = std::pow(10.0, gainDb / 40.0);
            const double w0 = 2.0 * M_PI * std::max(1.0, cornerHz) / fsIn;
            const double cosw0 = std::cos(w0);
            const double sinw0 = std::sin(w0);
            const double alpha = sinw0 * 0.5 * std::sqrt((A + 1.0 / A) * (1.0 / slopeS - 1.0) + 2.0);
            const double sq = 2.0 * std::sqrt(A) * alpha;
            double b0, b1, b2, a0, a1, a2;
            if (high)
            {
                b0 = A * ((A + 1.0) + (A - 1.0) * cosw0 + sq);
                b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cosw0);
                b2 = A * ((A + 1.0) + (A - 1.0) * cosw0 - sq);
                a0 = (A + 1.0) - (A - 1.0) * cosw0 + sq;
                a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cosw0);
                a2 = (A + 1.0) - (A - 1.0) * cosw0 - sq;
            }
            else
            {
                b0 = A * ((A + 1.0) - (A - 1.0) * cosw0 + sq);
                b1 = 2.0 * A * ((A - 1.0) - (A + 1.0) * cosw0);
                b2 = A * ((A + 1.0) - (A - 1.0) * cosw0 - sq);
                a0 = (A + 1.0) + (A - 1.0) * cosw0 + sq;
                a1 = -2.0 * ((A - 1.0) + (A + 1.0) * cosw0);
                a2 = (A + 1.0) + (A - 1.0) * cosw0 - sq;
            }
            B0 = b0 / a0; B1 = b1 / a0; B2 = b2 / a0;
            A1 = a1 / a0; A2 = a2 / a0;
        }

        // RBJ peaking EQ (same cookbook, same direct-form-I-transposed recursion), used for the
        // mix-keyed HF term.  Kept inside `Shelf` so both sections share ONE state layout and one
        // `process()` — a second biquad class here is how the two would drift apart in form.
        void setPeaking(double fsIn, double centreHz, double q, double gainDb) noexcept
        {
            ident = (gainDb == 0.0);
            if (ident)
                return;
            const double A = std::pow(10.0, gainDb / 40.0);
            const double w0 = 2.0 * M_PI * std::max(1.0, centreHz) / fsIn;
            const double alpha = std::sin(w0) / (2.0 * std::max(0.05, q));
            const double cosw0 = std::cos(w0);
            const double b0 = 1.0 + alpha * A, b1 = -2.0 * cosw0, b2 = 1.0 - alpha * A;
            const double a0 = 1.0 + alpha / A, a1 = -2.0 * cosw0, a2 = 1.0 - alpha / A;
            B0 = b0 / a0; B1 = b1 / a0; B2 = b2 / a0;
            A1 = a1 / a0; A2 = a2 / a0;
        }

        inline double process(double x) noexcept
        {
            if (ident)
                return x;
            const double y = B0 * x + z1;
            z1 = B1 * x - A1 * y + z2;
            z2 = B2 * x - A2 * y;
            return y;
        }

        void resetState() noexcept { z1 = z2 = 0.0; }

        double B0 = 1.0, B1 = 0.0, B2 = 0.0, A1 = 0.0, A2 = 0.0;
        double z1 = 0.0, z2 = 0.0;
        bool ident = true;
    };

    Shelf lo, hi, hf;
    double fs = 48000.0;
    double g = 0.0, lowHz = 130.0, loCut = 0.0, highHz = 2600.0, hiCut = 0.0;
    double loS = 0.9, hiS = 0.9;
    double cleanFrac = 0.0;
    double hfHz = 5600.0, hfQ = 1.0;
    double hfAtOd = 0.0, hfPeak = 0.0, hfPeakCf = 0.43, hfAtClean = 0.0;
    double flat = 1.0;
    bool inert = true;
};
