#pragma once

#include "MnaSolve.h"
#include "RailClamp.h"

// =============================================================================
// EQ block — Baxandall BASS + TREBLE (IC5_C) — circuit.md "Baxandall BASS/TREBLE
//            (IC5_C) — NODES VERIFIED (2026-07-19 pixel-zoom redraw)".
// =============================================================================
// BASS and TREBLE are ONE coupled active Baxandall network: both pots' wipers
// sum into the SAME IC5_C virtual-ground (−) node, so they must be solved as a
// single 7-node network, not two independent filters (circuit.md "Interactive /
// coupled controls"). Ideal op-amp: (+) = VD = 0, (−) held at 0, feedback
// R37(1M) ∥ C30(47p); Vout is the unknown that satisfies the (−)-node KCL (no
// KCL at the driven op-amp output — same active-filter treatment as MidBand).
//
// Node graph (signal ground = VD = 0; verified 2026-07-19):
//   Vin --R33--> A ;  B --R34--> Vout                  (bass end legs)
//   bass pot Rp: A --Rba--> Wb --Rbb--> B  (ab = fraction A→Wb ; ab→0 = BASS BOOST)
//   C25 A↔Wb ;  C26 Wb↔B ;  Wb --R35--> (−)            (caps run lug→WIPER)
//   Vin --C28--> T3 ;  T1 --C29--> Vout                (treble end legs, cap-coupled)
//   treble pot Rp: T3 --Rta--> Wt --Rtb--> T1 (at→0 = TREBLE BOOST)
//   Wt --R36--> (−)
//   feedback: (−) --R37--> Vout ;  (−) --C30--> Vout
// Unknowns [A, B, Wb, T3, T1, Wt, Vout].
//
// ---- MNA + companion caps (matches eq_reference.py :: baxandall_tf) ----------
// Trapezoidal companion caps (gc=2C/T; ieq_new = 2·gc·v_ab − ieq_old) make the
// 7×7 conductance matrix REAL and constant for fixed pot positions; the
// frequency dependence rides in the per-sample RHS history currents, exactly as
// for the 2-node stages and MidBand. Five caps: C25(A↔Wb), C26(B↔Wb) in the bass
// network; C28(Vin↔T3) source-coupled; C29(T1↔Vout); C30(Vout↔(−)) the feedback
// cap. Rows A/B/Wb/T3/T1/Wt use the natural "sum leaving = 0" convention; the
// (−)/Vout row uses the oracle's "currents INTO the node = 0" (a sign flip) — so
// the C30 history current lands as +ieqC30 in that row, mirroring MidBand's C33.
// The matrix depends on both pot splits, so it re-inverts whenever EITHER pot
// moves (dirty flag), never per sample. Maps 1:1 onto baxandall_tf.
//
// ---- Coupling caps C21/C31 (stage boundary — deferred) ----------------------
// C21(100n) couples IC5_B → this stage's Vin, and C31(2u2) couples this stage's
// Vout → LO-MID. Both are inter-stage HP couplers (like C2/C15/C36 elsewhere);
// the oracle (and this stage) are defined at the Baxandall network boundary and
// EXCLUDE them. C21 into the ~10k stack input is a ~150 Hz HP that DOES shape the
// bass, so it must be placed at the IC5_B→Baxandall boundary during Phase-6
// integration (flagged as a carry-forward — do not forget it in the full chain).
//
// ---- Rail clamp / polarity --------------------------------------------------
// Op-amp output → RailClamp on Vout (GATE item; disabled by default so the
// linear FR test matches the oracle). INVERTING: DC gain ≈ −0.926 at flat (the
// summing amp inverts; the slight <1 magnitude is the bass shelf's DC droop, not
// a bug — matches the oracle's −0.925926). This is one of the EQ block's four
// inversions (IC5_B, Baxandall, LO-MID, HI-MID → net non-inverting); confirmed by
// the DC-step test.
// =============================================================================
class Baxandall
{
public:
    // Component values (circuit.md "Baxandall BASS/TREBLE" + BASS/TREBLE rows).
    static constexpr double kRp = 100.0e3;  // both pots (100k B-taper)
    static constexpr double kR33 = 10.0e3;  // Vin → A
    static constexpr double kR34 = 10.0e3;  // B → Vout
    static constexpr double kR35 = 10.0e3;  // Wb → (−)
    static constexpr double kR36 = 3.3e3;   // Wt → (−)
    static constexpr double kR37 = 1.0e6;   // feedback (−) → Vout ("1m" on schematic)
    static constexpr double kC25 = 22.0e-9; // A ↔ Wb
    static constexpr double kC26 = 22.0e-9; // Wb ↔ B
    static constexpr double kC28 = 10.0e-9; // Vin ↔ T3
    static constexpr double kC29 = 10.0e-9; // T1 ↔ Vout
    static constexpr double kC30 = 47.0e-12; // feedback cap (−) ↔ Vout

    Baxandall() = default;

    void prepare(double sampleRate)
    {
        const double twoOverT = 2.0 * sampleRate;
        gc25 = kC25 * twoOverT;
        gc26 = kC26 * twoOverT;
        gc28 = kC28 * twoOverT;
        gc29 = kC29 * twoOverT;
        gc30 = kC30 * twoOverT;
        dirty = true;
        rebuild();
        reset();
    }

    void reset() noexcept { ieq25 = ieq26 = ieq28 = ieq29 = ieq30 = 0.0; }

    // Electrical pot fractions (B-taper linear; knob→fraction + direction applied
    // by the processor). ab→0 = BASS boost, at→0 = TREBLE boost, 0.5 = flat.
    void setBass(double ab) noexcept { setPos(posBass, ab); }
    void setTreble(double at) noexcept { setPos(posTreble, at); }

    // Rail-clamp passthroughs (calibration §6) — applied to Vout (op-amp output).
    void setRailClampEnabled(bool e) noexcept { rail.setEnabled(e); }
    void setRailVoltages(double vNeg, double vPos) noexcept { rail.setRailVoltages(vNeg, vPos); }

    inline double process(double vin) noexcept
    {
        if (dirty)
            rebuild();

        // RHS: sources (R33, C28) + capacitor history currents. See header.
        double rhs[7];
        rhs[0] = vin / kR33 + ieq25;      // A
        rhs[1] = ieq26;                   // B
        rhs[2] = -ieq25 - ieq26;          // Wb
        rhs[3] = gc28 * vin + ieq28;      // T3 (C28 source-coupled from Vin)
        rhs[4] = ieq29;                   // T1
        rhs[5] = 0.0;                     // Wt (no caps)
        rhs[6] = ieq30;                   // (−)/Vout (C30 feedback, flipped-sign row)

        double x[7];
        mna::matvec<7>(yinv, rhs, x);

        // Capacitor state update: Ieq_new = 2*gc*v_ab − Ieq_old.
        ieq25 = 2.0 * gc25 * (x[0] - x[2]) - ieq25; // A − Wb
        ieq26 = 2.0 * gc26 * (x[1] - x[2]) - ieq26; // B − Wb
        ieq28 = 2.0 * gc28 * (x[3] - vin) - ieq28;  // T3 − Vin
        ieq29 = 2.0 * gc29 * (x[4] - x[6]) - ieq29; // T1 − Vout
        ieq30 = 2.0 * gc30 * x[6] - ieq30;          // Vout − (−)=0

        return rail.process(x[6]); // Vout, then op-amp rails
    }

private:
    void setPos(double& slot, double v) noexcept
    {
        const double c = v < 1e-6 ? 1e-6 : (v > 1.0 - 1e-6 ? 1.0 - 1e-6 : v);
        if (c != slot) { slot = c; dirty = true; }
    }

    void rebuild() noexcept
    {
        const double Rba = posBass * kRp, Rbb = (1.0 - posBass) * kRp;   // A→Wb, Wb→B
        const double Rta = posTreble * kRp, Rtb = (1.0 - posTreble) * kRp; // T3→Wt, Wt→T1
        const double gRba = 1.0 / Rba, gRbb = 1.0 / Rbb, gRta = 1.0 / Rta, gRtb = 1.0 / Rtb;

        double Y[7][7] = {};
        // 0 A : (1/R33 + gc25 + 1/Rba) A − (gc25 + 1/Rba) Wb
        Y[0][0] = 1.0 / kR33 + gc25 + gRba; Y[0][2] = -(gc25 + gRba);
        // 1 B : (1/R34 + gc26 + 1/Rbb) B − (gc26 + 1/Rbb) Wb − (1/R34) Vout
        Y[1][1] = 1.0 / kR34 + gc26 + gRbb; Y[1][2] = -(gc26 + gRbb); Y[1][6] = -1.0 / kR34;
        // 2 Wb: −(gc25+1/Rba) A − (gc26+1/Rbb) B + (gc25+1/Rba + gc26+1/Rbb + 1/R35) Wb
        Y[2][0] = -(gc25 + gRba); Y[2][1] = -(gc26 + gRbb);
        Y[2][2] = gc25 + gRba + gc26 + gRbb + 1.0 / kR35;
        // 3 T3: (gc28 + 1/Rta) T3 − (1/Rta) Wt
        Y[3][3] = gc28 + gRta; Y[3][5] = -gRta;
        // 4 T1: (gc29 + 1/Rtb) T1 − (1/Rtb) Wt − gc29 Vout
        Y[4][4] = gc29 + gRtb; Y[4][5] = -gRtb; Y[4][6] = -gc29;
        // 5 Wt: −(1/Rta) T3 − (1/Rtb) T1 + (1/Rta + 1/Rtb + 1/R36) Wt
        Y[5][3] = -gRta; Y[5][4] = -gRtb; Y[5][5] = gRta + gRtb + 1.0 / kR36;
        // 6 (−)/Vout: (1/R35) Wb + (1/R36) Wt + (1/R37 + gc30) Vout   (into-node sign)
        Y[6][2] = 1.0 / kR35; Y[6][5] = 1.0 / kR36; Y[6][6] = 1.0 / kR37 + gc30;

        double tmp[7][7];
        if (mna::invert<7>(Y, tmp))
        {
            for (int i = 0; i < 7; ++i)
                for (int j = 0; j < 7; ++j)
                    yinv[i][j] = tmp[i][j];
        }
        // else keep the previous good inverse (degenerate pot endpoint).
        dirty = false;
    }

    double gc25 = 0.0, gc26 = 0.0, gc28 = 0.0, gc29 = 0.0, gc30 = 0.0;
    double posBass = 0.5, posTreble = 0.5; // electrical pot fractions (0.5 = flat)
    double yinv[7][7] = {};
    double ieq25 = 0.0, ieq26 = 0.0, ieq28 = 0.0, ieq29 = 0.0, ieq30 = 0.0;
    bool dirty = true;
    RailClamp rail;

    Baxandall(const Baxandall&) = delete;
    Baxandall& operator=(const Baxandall&) = delete;
};
