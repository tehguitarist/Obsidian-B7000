#pragma once

#include "RailClamp.h"

// =============================================================================
// Stage 6 — Sallen-Key low-pass ×2 (IC4_B ≈ 10.7 kHz, IC4_A ≈ 3.3 kHz) —
//           circuit.md "Recovery + bandlimiting (IC2_B, IC4_B, IC4_A)".
// =============================================================================
// The final OD-path bandlimiting: two cascaded 2nd-order UNITY-GAIN (voltage-
// follower) Sallen-Key low-pass filters. One reusable class, configured per
// instance with its own R1/R2/C1/C2 (see the two kIC4* value sets below):
//   IC4_B: R24 10k / R25 22k, C18 1n (feedback) / C27 1n (→GND)  → fc ≈ 10.7 kHz
//   IC4_A: R26 22k / R27 47k, C19 2n2 (feedback) / C20 1n (→GND) → fc ≈  3.3 kHz
//
// ---- Topology & node solve (MNA, matching the oracle) -----------------------
//   Vin --R1--> X --R2--> Y(=op-amp + input) ;  Y --C2--> GND
//   C1 (feedback) from X to Vout ;  op-amp = unity follower → Vout = V(Y).
// Unknowns [X, Y]; the op-amp OUTPUT node O = Y is DRIVEN (low-Z), so C1's
// current couples node X to Y (via O=Y) but injects NOTHING into node Y's own
// KCL — that one-sided coupling is what makes an active SK non-reciprocal (the
// Y matrix is asymmetric: X↔Y ≠ Y↔X). Continuous transfer function:
//   H(s) = 1 / (1 + s*C2*(R1+R2) + s^2*R1*R2*C1*C2)
// w0 and the damping term are symmetric in R1↔R2 (assignment irrelevant), but
// Q depends on C2 (the to-GND cap) alone → the C1/C2 role assignment matters.
//
// Built as MNA + trapezoidal-companion caps (same conventions as TrebleAttack /
// RecoveryBridgedT — gc = 2C/T, RHS[a]+=Ieq, ieq_new = 2*gc*v_ab − ieq_old),
// precomputed 2×2 inverse (fixed topology). Maps 1:1 onto eq_reference.py ::
// sallen_key_lpf_tf, so the FR test validates directly. C1 spans X↔O(=Y); its
// companion stamps ONLY node X (self +gc1) and couples −gc1 to Y, with its
// history at node X — the O-side current is absorbed by the driven op-amp
// output and never enters node Y (consistent with the KCL above).
//
// ---- Oversampling / warp ----------------------------------------------------
// Both corners (esp. IC4_A at 3.3 kHz) sit low enough that bilinear warp shows
// in the top octave at base rate; both SKs live INSIDE the Phase-6 oversampled
// region (dsp.md OS-region rule) which resolves it — so the base-rate FR test
// asserts tight ≤2 kHz and warp-shrink (48k→96k) above, NOT a prewarp fight.
//
// ---- Rail clamp / polarity --------------------------------------------------
// Op-amp output → RailClamp on Vout (GATE item; disabled by default so the
// linear FR test matches the oracle). Unity, non-inverting at DC (H(0)=1).
// =============================================================================
class SallenKeyLPF
{
public:
    // Component value sets (circuit.md). {R1, R2, C1_feedback, C2_toGND}.
    struct Values { double r1, r2, c1, c2; };
    static constexpr Values kIC4B { 10.0e3, 22.0e3, 1.0e-9, 1.0e-9 };   // ≈ 10.7 kHz
    static constexpr Values kIC4A { 22.0e3, 47.0e3, 2.2e-9, 1.0e-9 };   // ≈  3.3 kHz

    SallenKeyLPF() = default;

    // Choose which filter this instance is (call before prepare()).
    void configure(const Values& v) noexcept { val = v; }

    void prepare(double sampleRate)
    {
        const double twoOverT = 2.0 * sampleRate;
        gc1 = val.c1 * twoOverT; // trapezoidal companion conductances
        gc2 = val.c2 * twoOverT;

        // Nodal matrix Y (unknowns [X, Y]); Vin is the source. See header KCL:
        //   X: (1/R1 + 1/R2 + gc1) X − (1/R2 + gc1) Y = Vin/R1 + ieqC1
        //   Y: (−1/R2) X + (1/R2 + gc2) Y             = ieqC2
        const double a = 1.0 / val.r1 + 1.0 / val.r2 + gc1;
        const double b = -(1.0 / val.r2 + gc1);
        const double c = -1.0 / val.r2;
        const double d = 1.0 / val.r2 + gc2;
        const double det = a * d - b * c;
        yi00 = d / det;
        yi01 = -b / det;
        yi10 = -c / det;
        yi11 = a / det;

        reset();
    }

    void reset() noexcept { ieqC1 = ieqC2 = 0.0; }

    // Rail-clamp passthroughs (calibration §6) — applied to Vout (op-amp output).
    void setRailClampEnabled(bool e) noexcept { rail.setEnabled(e); }
    void setRailVoltages(double vNeg, double vPos) noexcept { rail.setRailVoltages(vNeg, vPos); }

    // Process one sample (real volts). Vout = V(Y).
    inline double process(double x) noexcept
    {
        // RHS: source (R1 from Vin) + capacitor history.
        //   C1 (a=X, b=O=Y): source? no — RHS[X] += ieqC1 (O-side absorbed by op-amp).
        //   C2 (a=Y, b=GND): RHS[Y] += ieqC2.
        const double rhs0 = x / val.r1 + ieqC1;
        const double rhs1 = ieqC2;

        const double vx = yi00 * rhs0 + yi01 * rhs1;
        const double vy = yi10 * rhs0 + yi11 * rhs1;

        // Capacitor state update: Ieq_new = 2*gc*v_ab − Ieq_old.
        ieqC1 = 2.0 * gc1 * (vx - vy) - ieqC1; // v_ab = X − O(=Y)
        ieqC2 = 2.0 * gc2 * vy - ieqC2;        // v_ab = Y − GND

        return rail.process(vy); // Vout = V(Y), then op-amp rails
    }

private:
    Values val = kIC4B;                     // default; set via configure()
    double gc1 = 0.0, gc2 = 0.0;            // companion conductances (set in prepare)
    double yi00 = 0.0, yi01 = 0.0, yi10 = 0.0, yi11 = 0.0; // precomputed Y^-1
    double ieqC1 = 0.0, ieqC2 = 0.0;        // capacitor history currents
    RailClamp rail;

    SallenKeyLPF(const SallenKeyLPF&) = delete;
    SallenKeyLPF& operator=(const SallenKeyLPF&) = delete;
};
