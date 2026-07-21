#pragma once

#include "RailClamp.h"

// =============================================================================
// EQ block — pre-gain: IC5_A unity buffer + IC5_B inverting −2.2× — circuit.md
//            "EQ path — buffer, gain ..." (IC5_A row, R28/R29 + IC5_B row).
// =============================================================================
// The post-BLEND EQ input conditioning, ahead of the Baxandall tone stack:
//   IC5_A — TL074 unity buffer (isolates the BLEND wiper's varying source Z).
//   IC5_B — TL074 inverting gain, −R29/R28 = −22k/10k = −2.2× (flat, broadband;
//           no feedback cap on this stage per circuit.md).
// Both are frequency-flat, so this stage is a pure scalar gain with two op-amp
// output rail clamps — no WDF/MNA network, no oracle beyond the constant −2.2.
//
// C21(100n) couples IC5_B → the Baxandall stack input; per the stage-boundary
// convention it lives at the EqPreGain→Baxandall boundary (a ~150 Hz HP into the
// ~10k stack input) and is added in Phase-6 integration, NOT inside this stage —
// same treatment as the other inter-stage coupling caps. See Baxandall.h.
//
// ---- Rail clamps (calibration §6, GATE item) --------------------------------
// One clamp per op-amp output: the buffer output (rarely rails — unity, but kept
// for the GATE) and the −2.2× output (can rail on a hot post-BLEND signal at
// extreme drive). Disabled by default so the linear test sees exactly −2.2.
//
// ---- Polarity ---------------------------------------------------------------
// INVERTING (−2.2). This is one of the EQ block's four inversions (IC5_B,
// Baxandall, LO-MID, HI-MID → net non-inverting through the whole EQ); confirmed
// by the DC-step test.
// =============================================================================
class EqPreGain
{
public:
    static constexpr double kR28 = 10.0e3; // IC5_B input resistor
    static constexpr double kR29 = 22.0e3; // IC5_B feedback resistor
    static constexpr double kGain = -kR29 / kR28; // −2.2 (inverting)

    EqPreGain() = default;

    void prepare(double /*sampleRate*/) noexcept {} // frequency-flat, no state

    void reset() noexcept {}

    // Rail-clamp passthroughs (calibration §6). Applied to each op-amp output.
    void setRailClampEnabled(bool e) noexcept
    {
        railBuf.setEnabled(e);
        railGain.setEnabled(e);
    }
    void setRailVoltages(double vNeg, double vPos) noexcept
    {
        railBuf.setRailVoltages(vNeg, vPos);
        railGain.setRailVoltages(vNeg, vPos);
    }

    inline double process(double vin) noexcept
    {
        const double buf = railBuf.process(vin);       // IC5_A unity buffer
        return railGain.process(kGain * buf);          // IC5_B inverting −2.2×
    }

private:
    RailClamp railBuf;  // IC5_A output
    RailClamp railGain; // IC5_B output

    EqPreGain(const EqPreGain&) = delete;
    EqPreGain& operator=(const EqPreGain&) = delete;
};
