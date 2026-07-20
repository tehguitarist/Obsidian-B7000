#pragma once

#include "RailClamp.h"

// =============================================================================
// Stage 5 — Recovery buffer + passive bridged-T (IC2_B) — circuit.md
//           "Recovery + bandlimiting (IC2_B ...)" + the IC2_B CORRECTION note.
// =============================================================================
// IC2_B is a UNITY-GAIN VOLTAGE FOLLOWER (pin6- tied to pin7-out, verified on
// BOTH schematics) — NOT the +12 dB active shelf an earlier reading assumed.
// There is NO recovery make-up gain here; do not budget one into gain-staging.
//
// The R22/R23/C16/C17 parts form a PASSIVE bridged-T network hanging off the
// buffer output (circuit.md node graph):
//     buf-out --C16(680pF)--> Nout                       (bridge cap)
//     buf-out --R22(100k)--> Nmid --R23(33k)--> Nout     (the "T")
//     Nmid --C17(22n)--> GND                             (shunt leg)
// Stage output = V(Nout) (→ R24 → IC4_B Sallen-Key). Ideal-component response
// is a deep midrange notch (~717 Hz / −28 dB UNLOADED, tolerance-sensitive) —
// surprising for this pedal, so the DEPTH must be capture-validated at Phase 7;
// the TOPOLOGY (unity buffer + bridged-T) is firmly verified.
//
// ---- Why MNA rather than a WDF tree (same reasoning as TrebleAttack) --------
// A bridged-T is a bridge (C16 spans buf-out↔Nout in parallel with the R22-R23
// path) — not a series/parallel WDF tree; it would need a hand-derived R-type
// scattering matrix. For a LINEAR passive block with an ideal source in
// (the unity buffer output) and a high-Z output, 2-node nodal analysis with
// trapezoidal-companion caps is exact, uses the SAME bilinear cap discretisation
// as chowdsp's CapacitorT (identical warp), and maps 1:1 onto the analytic
// oracle (analysis/eq_reference.py :: bridged_t_tf, default UNLOADED). The
// matrix is fixed (no switch), so its 2×2 inverse is precomputed once in
// prepare(). Cap-stamp / history conventions match TrebleAttack exactly.
//
// ---- Loading (build-plan Phase 4 test caveat) -------------------------------
// The oracle default is UNLOADED, and so is this stage: Nout feeds R24(10k) in
// SERIES into the IC4_B SK non-inverting input, which is high-Z and bootstrapped
// in the SK passband — a light load well approximated as open at/around the
// 717 Hz notch (717 Hz ≪ the 10.7 kHz SK corner). The bridged-T→SK PAIR is
// validated together (and against captures) at Phase 7; here the isolated stage
// validates 1:1 against the unloaded oracle, decoupled from the SK load.
// (The oracle's Rload arg models Nout→GND through R, which is NOT the real
// topology — R24 does not go to ground — so it is only a crude sensitivity
// bound, never the reference for this stage.)
//
// ---- Rail clamp (calibration §6, build-plan Phase 4 GATE item) --------------
// The unity buffer is an op-amp output → carries a RailClamp (apply to EVERY
// op-amp stage). The clamp sits on the BUFFER output (the op-amp node), i.e. the
// source feeding the passive bridged-T. Disabled by default so the linear FR
// test validates against the oracle unchanged; the processor enables it.
//
// ---- Polarity ---------------------------------------------------------------
// Unity, non-inverting at DC (caps open → Nout follows buf-out through R22/R23
// with no drop into the open output → gain 1). Confirmed by the DC-step test.
// =============================================================================
class RecoveryBridgedT
{
public:
    // Component values (circuit.md "Recovery + bandlimiting" table).
    static constexpr double kR22 = 100.0e3; // "T" upper leg (buf-out -> Nmid)
    static constexpr double kR23 = 33.0e3;  // "T" lower leg (Nmid -> Nout)
    static constexpr double kC16 = 680.0e-12; // bridge cap (buf-out -> Nout)
    static constexpr double kC17 = 22.0e-9;   // shunt leg (Nmid -> GND)

    RecoveryBridgedT() = default;

    void prepare(double sampleRate)
    {
        const double twoOverT = 2.0 * sampleRate;
        gc16 = kC16 * twoOverT; // trapezoidal companion conductances
        gc17 = kC17 * twoOverT;

        // Nodal matrix Y (unknowns [Nmid, Nout]); Vin (=buffer out) is the source.
        //   Nmid: (1/R22 + 1/R23 + gc17) Nmid + (-1/R23) Nout = Vin/R22 + ieqC17
        //   Nout: (-1/R23) Nmid + (1/R23 + gc16) Nout       = gc16*Vin - ieqC16
        const double a = 1.0 / kR22 + 1.0 / kR23 + gc17;
        const double b = -1.0 / kR23;
        const double c = -1.0 / kR23;
        const double d = 1.0 / kR23 + gc16;
        const double det = a * d - b * c;
        // Precomputed inverse of [[a,b],[c,d]].
        yi00 = d / det;
        yi01 = -b / det;
        yi10 = -c / det;
        yi11 = a / det;

        reset();
    }

    void reset() noexcept { ieqC16 = ieqC17 = 0.0; }

    // Rail-clamp passthroughs (calibration §6) — applied to the BUFFER output.
    void setRailClampEnabled(bool e) noexcept { rail.setEnabled(e); }
    void setRailVoltages(double vNeg, double vPos) noexcept { rail.setRailVoltages(vNeg, vPos); }

    // Process one sample (real volts in from the clipper-recovery path, out at Nout).
    inline double process(double x) noexcept
    {
        const double vin = rail.process(x); // unity buffer (op-amp output, clamped)

        // RHS: source contributions + capacitor history (Ieq).
        //   C17 (a=Nmid, b=GND): RHS[Nmid] += ieqC17
        //   C16 (a=Vin src, b=Nout): source -> RHS[Nout] += gc16*Vin ; RHS[Nout] -= ieqC16
        const double rhs0 = vin / kR22 + ieqC17;
        const double rhs1 = gc16 * vin - ieqC16;

        const double nmid = yi00 * rhs0 + yi01 * rhs1;
        const double nout = yi10 * rhs0 + yi11 * rhs1;

        // Capacitor state update: Ieq_new = 2*gc*v_ab - Ieq_old.
        ieqC17 = 2.0 * gc17 * nmid - ieqC17;         // v_ab = Nmid - GND
        ieqC16 = 2.0 * gc16 * (vin - nout) - ieqC16; // v_ab = Vin - Nout

        return nout;
    }

private:
    double gc16 = 0.0, gc17 = 0.0;          // companion conductances (set in prepare)
    double yi00 = 0.0, yi01 = 0.0, yi10 = 0.0, yi11 = 0.0; // precomputed Y^-1
    double ieqC16 = 0.0, ieqC17 = 0.0;      // capacitor history currents
    RailClamp rail;

    RecoveryBridgedT(const RecoveryBridgedT&) = delete;
    RecoveryBridgedT& operator=(const RecoveryBridgedT&) = delete;
};
