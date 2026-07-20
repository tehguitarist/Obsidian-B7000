#pragma once

#include "RailClamp.h"
#include "../utils/TaperUtils.h"

// =============================================================================
// Stage 4 — DRIVE gain stage (IC2_A, R15/C10 feedback, R17/VR3/R32 gain leg)
// =============================================================================
// circuit.md "DRIVE gain stage (IC2_A)": a NON-INVERTING op-amp gain stage.
//   R15 = 330k   feedback (out -> -)
//   C10 = 47pF   || R15, HF rolloff of the feedback impedance
//   R17 = 3k3    gain-leg series (- -> DRIVE)
//   VR3 = 100k C-taper rheostat (in the gain leg; the DRIVE control)
//   R32 = 1k     gain-leg series (DRIVE -> VD / AC ground)
//   Gain = 1 + R15 / (R17 + Rdrive + R32) ~= 4x (Rdrive=100k) .. 78x (Rdrive=0)
//
// ---- Ideal-op-amp decomposition (dsp.md "the workhorse pattern") ------------
// For an ideal op-amp the (-) node sits at V(+) = Vin and draws no current, so:
//   gain-set leg Zg = R17 + Rdrive + R32  (- -> AC ground). PURELY resistive, so
//     the current it draws is Ig = Vin / Zg, frequency-independent.
//   feedback leg Zf = R15 || C10  (- -> output). The SAME current Ig flows
//     through it (op-amp draws none), developing Vf = Ig * Zf across it.
//   Vout = Vin + Vf                       (non-inverting; gain = 1 + Zf/Zg)
// Only C10 makes the stage frequency-dependent (feedback HF rolloff, corner
// 1/(2*pi*R15*C10) ~= 10.3 kHz). It is discretised with the SAME trapezoidal
// (bilinear) companion rule as chowdsp's CapacitorT and TrebleAttack — so the
// stage maps 1:1 onto the analytic oracle (analysis/eq_reference.py
// :: drive_stage_tf) with identical bilinear warp near Nyquist (resolved by the
// Phase 6 oversampled region, exactly as for TrebleAttack).
//
// Companion node: Vf across R15||C10, driven by the current source Ig.
//   KCL:  Ig = Vf/R15 + (gc10*Vf - ieq)   ->  Vf = (Ig + ieq) / (1/R15 + gc10)
//   cap update: ieq_new = 2*gc10*Vf - ieq
//
// ---- Polarity ---------------------------------------------------------------
// Non-inverting: a positive DC input gives a positive output = Vin*gain. No
// PolarityInverterT (verified by the DC-step test, dsp.md "confirm output
// polarity ... NOT reflexively"). The J201 stage upstream and the CD4049 clipper
// downstream carry the inversions that matter at the BLEND node (circuit.md).
//
// ---- Rail clamp (calibration §6, build-plan Phase 4 GATE item) --------------
// IC2_A at max DRIVE is ~×78 and hits its own op-amp rails BEFORE the clipper —
// so the output carries a RailClamp. Disabled by default (a linear FR test then
// validates against the oracle unchanged); the processor enables it for audio.
//
// ---- DRIVE taper (INTERIM — fit from captures at Phase 7) -------------------
// VR3 is a 100k C-taper (reverse-audio) rheostat: knob up = LESS resistance =
// MORE gain. The knob->resistance CURVE must be fit from THD-vs-drive captures
// (calibration §6b; the reference build's drive pot landed ~Rmax*x^2.2). Until
// then we use a power law in (1-x) anchored to EXACTLY 0 at full drive to dodge
// the audio-taper FLOOR trap (calibration §3: a 1% floor on this 100k pot would
// leave ~1k in the gain leg at max drive, cutting max gain 78x->63x). FR
// validation is decoupled from the taper (the oracle takes Rdrive directly), so
// refitting the curve later never invalidates the stage's linear correctness.
// =============================================================================
class DriveStage
{
public:
    // Component values (circuit.md "DRIVE gain stage (IC2_A)").
    static constexpr double kR15 = 330.0e3; // feedback
    static constexpr double kC10 = 47.0e-12; // feedback HF rolloff
    static constexpr double kR17 = 3.3e3;   // gain-leg series (fixed, top)
    static constexpr double kR32 = 1.0e3;   // gain-leg series (fixed, bottom)
    static constexpr double kDrivePot = 100.0e3; // VR3 max resistance
    static constexpr double kTaperExp = 1.5; // INTERIM C-taper shape (fit later)

    DriveStage() = default;

    void prepare(double sampleRate)
    {
        gc10 = kC10 * 2.0 * sampleRate; // trapezoidal companion conductance
        gFB = 1.0 / kR15 + gc10;        // node conductance seen by Ig
        reset();
    }

    void reset() noexcept { ieqC10 = 0.0; }

    // Map the DRIVE knob (0..1) through the C-taper to the gain-leg resistance.
    // Static so tests/oracle can share the exact curve. Anchored to 0 at x=1.
    static double driveResistance(double x) noexcept
    {
        // Power law in (1-x): x=0 -> 100k (min gain), x=1 -> 0 (max gain).
        return pedal::taper::powerLawTaper(1.0 - x, kDrivePot, kTaperExp);
    }

    void setDrive(double x) noexcept { setDriveResistance(driveResistance(x)); }

    // Set the DRIVE rheostat's ELECTRICAL resistance directly (used by the FR
    // test to drive oracle-matched values, decoupled from the taper curve).
    void setDriveResistance(double rDrive) noexcept
    {
        gZg = 1.0 / (kR17 + rDrive + kR32);
    }

    // Rail-clamp passthroughs (calibration §6).
    void setRailClampEnabled(bool e) noexcept { rail.setEnabled(e); }
    void setRailVoltages(double vNeg, double vPos) noexcept { rail.setRailVoltages(vNeg, vPos); }

    // Process one sample (real volts in/out, VD-referenced). Non-inverting.
    inline double process(double x) noexcept
    {
        const double ig = x * gZg;              // gain-leg current (resistive)
        const double vf = (ig + ieqC10) / gFB;  // voltage across R15||C10
        ieqC10 = 2.0 * gc10 * vf - ieqC10;      // trapezoidal cap-state update
        return rail.process(x + vf);            // Vout = Vin + Vf, then rails
    }

private:
    double gc10 = 0.0;   // C10 companion conductance (set in prepare)
    double gFB = 0.0;    // 1/R15 + gc10
    double ieqC10 = 0.0; // C10 history current
    double gZg = 1.0 / (kR17 + kDrivePot + kR32); // gain-leg conductance (min gain default)
    RailClamp rail;

    DriveStage(const DriveStage&) = delete;
    DriveStage& operator=(const DriveStage&) = delete;
};
