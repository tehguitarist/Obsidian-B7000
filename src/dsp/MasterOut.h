#pragma once

#include <cmath>
#include "RailClamp.h"
#include "../utils/TaperUtils.h"

// =============================================================================
// Stage 9 — MASTER volume [ENG] + IC6_B output buffer + output HP network
// =============================================================================
// The LAST linear stage before the J201 nonlinear front end. circuit.md
// "MASTER volume [ENG]" + "Output (¼\" jack) — IC6_B".
//
//   MASTER (VR8) 100k A-taper [ENG] — post-EQ output volume divider:
//       top lug = HI-MID (IC6_A) output via C36 (2u2), bottom lug = VD,
//       wiper → IC6_B(+). Unity at full CW; attenuation-only.
//   IC6_B (TL074) — unity output buffer.
//   C37 (2u2) → R47 (1k series) → OUT ; R46 (100k) output pulldown.
//
// ---- Topology (signal ground = VD = 0) --------------------------------------
//   Vin(IC6_A out) --C36--> Ntop --[MASTER pot Rp]--> GND
//                                     wiper W (unloaded, IC6_B is high-Z)
//   W --> IC6_B (unity) --> Vbuf --C37--> Nout --R47(1k)--> OUT
//                                          Nout --R46(100k)--> GND
//
// Two facts make this stage simple and exact in the audible band:
//   1. The MASTER wiper feeds IC6_B(+), a high-Z op-amp input that draws NO
//      current — so the wiper is UNLOADED. The pot presents its full Rp from
//      Ntop to ground, and the wiper is a pure resistive tap:
//          Ntop = Vin · sC36·Rp / (1 + sC36·Rp)          (input HPF, ~0.72 Hz)
//          W    = Ntop · (Rbot/Rp) = Ntop · divRatio      (frequency-flat tap)
//      divRatio = Rbot/Rp = the A-taper divider fraction (full CW → 1 → unity).
//   2. The output jack is unloaded (into a high-Z DAW/next stage), so no current
//      flows in R47 → OUT = Nout, and the output network is just:
//          Nout = Vbuf · sC37·R46 / (1 + sC37·R46)        (output HPF, ~0.72 Hz)
//
// ⚠ The ONLY caps in this stage are C36 and C37, BOTH forming ~0.72 Hz HPFs
//   (1/(2π·2u2·100k) — inaudible; circuit.md "MASTER" sim-checked). There are NO
//   audible-band HF caps here, so — unlike every prior EQ-block stage — there is
//   NO bilinear top-octave warp to worry about: the trapezoidal discretisation of
//   a 0.72 Hz corner is essentially exact at audio rates, and the stage matches
//   the analytic oracle (master_out_tf) tightly across the WHOLE spectrum. It sits
//   OUTSIDE the Phase-6 oversampled region for the same reason (no HF content to
//   protect — like the InputBuffer's ~1.6 Hz HP).
//
//   The C36 leg also supplies IC6_B(+)'s DC bias: the stock board floats that pin
//   (no bias R after C36 — verified), and the [ENG] MASTER pot's VD (bottom) leg
//   provides the missing DC path. Electrically cleaner than stock, no extra part.
//
// ---- Why MNA (consistent with the other linear stages) ----------------------
// The input and output HPFs are each a single-node MNA with one trapezoidal
// companion cap (same conventions as RecoveryBridgedT). The buffer decouples the
// two networks (IC6_B out = W, unity), so we solve the input node for W, apply
// the rail clamp on the buffer output, then solve the output node — no coupled
// matrix needed. Both nodes are 1×1 (scalar), so no inverse table: the pot move
// only rescales the resistive tap, never the cap-node conductance, so nothing
// here needs a dirty-flag re-inversion.
//
// ---- Rail clamp (calibration §6, build-plan Phase 4 GATE item) --------------
// IC6_B is an op-amp output → carries a RailClamp on its output (Vbuf), i.e. the
// source feeding C37. Disabled by default so the linear FR test validates against
// the oracle unchanged; the processor enables it.
//
// ---- Polarity ---------------------------------------------------------------
// NON-INVERTING: passive divider (non-inv) → unity buffer (non-inv) → passive
// output net (non-inv). AC-coupled, so the DC gain is 0; a step response jumps to
// +divRatio·Vin (non-inverting, correct gain) then decays to 0 (both HPFs) —
// confirmed by the step test. This closes the EQ→MASTER polarity chain: EQ block
// is net non-inverting (4 inversions) and MASTER adds none.
//
// ⚠ Phase-7 carry-forward: the MASTER A-taper SHAPE (kMasterTaperExp = 1.43
//   interim, divRatio = master^p) is a starting guess — fit p to the master-sweep
//   captures (same power-law-taper method as LEVEL; dsp.md §tapers).
// =============================================================================
class MasterOut
{
public:
    // Component values (circuit.md MASTER + Output tables).
    static constexpr double kRp = 100.0e3;   // MASTER pot VR8 (100k A)
    static constexpr double kC36 = 2.2e-6;   // EQ-out coupling into the divider top
    static constexpr double kC37 = 2.2e-6;   // output coupling
    static constexpr double kR46 = 100.0e3;  // output pulldown to GND
    static constexpr double kR47 = 1.0e3;    // series output resistor (spec 1k out Z; unloaded → no drop)

    // MASTER audio-taper exponent (power law: divRatio = master^p). Interim
    // start per dsp.md §tapers; fit to captures at Phase 7.
    static constexpr double kMasterTaperExp = 1.43;

    MasterOut() = default;

    void prepare(double sampleRate)
    {
        const double twoFs = 2.0 * sampleRate;
        gc36 = kC36 * twoFs; // trapezoidal companion conductances
        gc37 = kC37 * twoFs;
        reset();
    }

    void reset() noexcept { ieqC36 = ieqC37 = 0.0; }

    void setMaster(double x) noexcept
    {
        // x ∈ [0,1], A-taper via power law. divRatio = Rbot/Rp (wiper→GND tap):
        // x=1 (full CW) → 1.0 → unity; x=0 → 0.0 (wiper at VD, silent).
        divRatio = pedal::taper::powerLawTaper(x, 1.0, kMasterTaperExp);
    }

    // Rail-clamp passthroughs (calibration §6) — applied to the IC6_B output.
    void setRailClampEnabled(bool e) noexcept { rail.setEnabled(e); }
    void setRailVoltages(double vNeg, double vPos) noexcept { rail.setRailVoltages(vNeg, vPos); }

    // Process one sample: Vin = IC6_A (EQ) output, VD-referenced volts; out = OUT.
    inline double process(double vin) noexcept
    {
        // ---- Input HPF node Ntop: C36 (a=Vin src, b=Ntop) + pot Rp to GND ----
        // (gc36 + 1/Rp)·Ntop = gc36·Vin - ieqC36
        const double ntop = (gc36 * vin - ieqC36) / (gc36 + 1.0 / kRp);
        ieqC36 = 2.0 * gc36 * (vin - ntop) - ieqC36; // v_ab = Vin - Ntop

        // ---- Unloaded resistive wiper tap → IC6_B unity buffer (rail-clamped) ----
        const double vbuf = rail.process(ntop * divRatio);

        // ---- Output HPF node Nout: C37 (a=Vbuf src, b=Nout) + R46 to GND ----
        // (gc37 + 1/R46)·Nout = gc37·Vbuf - ieqC37 ; OUT = Nout (R47 into open load)
        const double nout = (gc37 * vbuf - ieqC37) / (gc37 + 1.0 / kR46);
        ieqC37 = 2.0 * gc37 * (vbuf - nout) - ieqC37; // v_ab = Vbuf - Nout

        return nout;
    }

private:
    double gc36 = 0.0, gc37 = 0.0;    // companion conductances (set in prepare)
    double ieqC36 = 0.0, ieqC37 = 0.0; // capacitor history currents
    double divRatio = 1.0;             // MASTER wiper tap (default full CW = unity)
    RailClamp rail;

    MasterOut(const MasterOut&) = delete;
    MasterOut& operator=(const MasterOut&) = delete;
};
