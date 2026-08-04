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
// ✅ RESOLVED session 115 (Phase 10 C): the taper is no longer a power law. It is a
//   TWO-SEGMENT PIECEWISE LINEAR curve fitted to the corrected 9-detent master ladder —
//   see setMaster() and FitParams::masterTaperBreak. The old carry-forward asked for a
//   power-law exponent fit; the answer is that no exponent exists (per-point p spans
//   1.74…3.51), which is why the FORM changed rather than the value.
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

    // MASTER audio-taper shape — THREE-SEGMENT PIECEWISE LINEAR (session 146; was two-segment
    // s115, a power law before that). The wiper reaches `Frac` of full resistance at rotation
    // `Break`, and `Frac2` at `Break2`; linear in between and either side.
    // (The retired power-law exponent `kMasterTaperExp = 1.43` lived here until session 115.)
    // Defaults are the fitted session-146 values, so a default-constructed MasterOut matches
    // the shipped FitParams. Both endpoints stay exact regardless of these numbers.
    //
    // ⚠⚠ `kMasterTaperBreak` CHANGED MEANING at session 146: it is now the FIRST of two breaks,
    // not THE break, and its VALUE moved 0.5927 -> 0.3318 accordingly. Anything that reads it
    // and reconstructs a two-segment curve is now silently wrong — the s118 lesson
    // (`when a parameter carries two meanings and a fit consumes one of them`). The known
    // consumers were re-pointed in the same session: PedalChain::applyFitParams,
    // tests/MasterOutTest.cpp::taperRatio, analysis/offline_render.cpp's --fit map, and
    // analysis/a3_decomposition_gate.py::master_div. Grep before adding another.
    static constexpr double kMasterTaperBreak = 0.331781;
    static constexpr double kMasterTaperFrac = 0.056905;
    static constexpr double kMasterTaperBreak2 = 0.659183;
    static constexpr double kMasterTaperFrac2 = 0.177468;

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
        // x ∈ [0,1]. divRatio = Rbot/Rp (wiper→GND tap):
        // x=1 (full CW) → 1.0 → unity; x=0 → 0.0 (wiper at VD, silent).
        //
        // ⭐⭐ SESSION 146 — THREE-SEGMENT PIECEWISE LINEAR, replacing session 115's two.
        // A real audio ("A") taper is MANUFACTURED as linear resistive segments; the question
        // is only how many. TWO cannot describe this pot, and the reason is structural rather
        // than a matter of fit quality: with the first segment running from the ORIGIN, the
        // curve below the break is a straight line and therefore cannot be CONVEX there — so
        // forcing it through the one knob position the captures actually pin (MASTER noon, the
        // centre detent, where the pot has no freedom and two capture sessions agree to
        // 0.0000 dB) drives the bottom of the travel 1.4–3.4 dB hot. A third segment removes
        // that constraint. See FitParams::masterTaperBreak for the full provenance.
        //
        // The shipped segment slopes RISE monotonically (0.172 → 0.368 → 2.413 ratio per
        // rotation), i.e. the curve is convex — what a real audio track looks like, and a
        // property no term of the objective asked for.
        //
        // Both endpoints are EXACT by construction, which the topology requires:
        //   x=0 → 0 (the wiper is on VD)   x=1 → 1 (unity at full CW, circuit.md MASTER).
        knob = x;
        // Fall back to the compiled defaults unless the whole set is ordered and in range —
        // a partially-valid set would silently produce a non-monotone "taper".
        const bool ok = masterTaperBreak > 1.0e-9 && masterTaperBreak < masterTaperBreak2
                        && masterTaperBreak2 < 1.0 && masterTaperFrac > 0.0
                        && masterTaperFrac < masterTaperFrac2 && masterTaperFrac2 < 1.0;
        const double b1 = ok ? masterTaperBreak : kMasterTaperBreak;
        const double f1 = ok ? masterTaperFrac : kMasterTaperFrac;
        const double b2 = ok ? masterTaperBreak2 : kMasterTaperBreak2;
        const double f2 = ok ? masterTaperFrac2 : kMasterTaperFrac2;
        divRatio = (x <= b1) ? (f1 * x / b1)
                 : (x <= b2) ? (f1 + (f2 - f1) * (x - b1) / (b2 - b1))
                             : (f2 + (1.0 - f2) * (x - b2) / (1.0 - b2));
    }

    // Phase-7/10C capture fit (FitParams.h): re-applies the CURRENT knob position through the
    // new curve, so a taper refit doesn't leave a stale divRatio.
    void setTaper(double brk, double frac, double brk2, double frac2) noexcept
    {
        masterTaperBreak = brk;
        masterTaperFrac = frac;
        masterTaperBreak2 = brk2;
        masterTaperFrac2 = frac2;
        setMaster(knob);
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
    // Phase-7 capture-fit taper shape + the knob position it was applied to.
    double masterTaperBreak = kMasterTaperBreak;
    double masterTaperFrac = kMasterTaperFrac;
    double masterTaperBreak2 = kMasterTaperBreak2;
    double masterTaperFrac2 = kMasterTaperFrac2;
    double knob = 1.0;
    RailClamp rail;

    MasterOut(const MasterOut&) = delete;
    MasterOut& operator=(const MasterOut&) = delete;
};
