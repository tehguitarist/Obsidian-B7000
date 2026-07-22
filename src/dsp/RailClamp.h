#pragma once

#include <algorithm>
#include <cmath> // std::abs (floating-point overload) in setRailVoltages

// =============================================================================
// RailClamp — op-amp output-rail saturation (shared across every op-amp stage)
// =============================================================================
// calibration-and-gain-staging.md §6: a non-rail-to-rail op-amp (TL07x here) on
// a single 9 V supply swings only to within ~1-2 V of each rail. The correct
// shape is NOT a gentle tanh — a real output transistor is "dead-linear until
// ~0.35 V before the rail, a short parabolic knee, then a HARD clamp". This
// utility implements exactly that so every stage can apply it to its output.
//
// The DSP chain runs bipolar with signal ground = VD (~4.5 V) mapped to 0, so
// the clamp limits are given RELATIVE to VD: the output saturates into
// [-vNeg, +vPos]. Defaults come from circuit.md's op-amp model (absolute
// [~1.2, ~7.8] V on the ~8.6 V rail, i.e. ~±3.3 V around VD) — ESTIMATES to
// refine from a scope/SPICE or captures (calibration §6: absolute values ±0.5 V
// unless measured; positive rail may clip first as VD sits ~mid-supply).
//
// This is a real, audible part of the sound, not a safety net: IC2_A at max
// DRIVE is ~×78 and hits ITS rails BEFORE the CD4049 clipper does (build-plan
// Phase 4 rail paragraph; §6 "compounding gain" — clamp every op-amp output and
// measure the worst-case node). Inside the Phase 6 oversampled region this clamp
// gets oversampled + ADAA'd along with the stage; the piecewise-quadratic knee
// has a closed-form antiderivative, so ADAA is cheap (dsp.md).
//
// Disabled by default so a freshly-built LINEAR stage validates against its
// analytic oracle unchanged; the processor/stage enables it for the audio path.
// =============================================================================
class RailClamp
{
public:
    RailClamp() = default;

    // Clamp MAGNITUDES relative to VD (signal ground = 0) — the output saturates
    // into [-vNeg, +vPos], so both are positive. |v| is taken defensively: a
    // signed vNeg makes the negative branch below fire for every sample under
    // +(|vNeg| - knee) and return a constant +|vNeg|, i.e. the clamp emits DC
    // instead of audio. That is exactly what FitParams shipped (railNeg = -3.3)
    // until 2026-07-22, undetected because railEnabled defaulted to false — and
    // `railNeg` is a --fit key, so a signed value can still arrive from a sweep.
    void setRailVoltages(double vNeg, double vPos) noexcept
    {
        railNeg = std::abs(vNeg);
        railPos = std::abs(vPos);
    }

    void setKnee(double kneeVolts) noexcept { knee = kneeVolts; }
    void setEnabled(bool e) noexcept { enabled = e; }
    bool isEnabled() const noexcept { return enabled; }

    // Saturate one sample (real volts, VD-referenced).
    inline double process(double x) const noexcept
    {
        if (! enabled)
            return x;

        const double h = knee;
        // ---- Positive rail: linear -> parabolic knee -> hard clamp ----
        if (x > railPos - h)
        {
            if (x >= railPos + h)
                return railPos;
            const double d = x - railPos - h; // in [-2h, 0)
            return railPos - (d * d) / (4.0 * h);
        }
        // ---- Negative rail (mirror image) ----
        if (x < -(railNeg - h))
        {
            if (x <= -(railNeg + h))
                return -railNeg;
            const double d = x + railNeg + h; // in (0, 2h]
            return -railNeg + (d * d) / (4.0 * h);
        }
        return x; // dead-linear between the knees
    }

private:
    double railNeg = 3.3, railPos = 3.3; // relative to VD; estimates (calibration §6)
    double knee = 0.35;                  // parabolic-knee half-width (V)
    bool enabled = false;                // linear until a stage/processor turns it on
};
