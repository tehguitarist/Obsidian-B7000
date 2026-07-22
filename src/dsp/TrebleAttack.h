#pragma once

#include <array>
#include <cmath>
#include <cstring>
#include <cstddef>
#include <utility>

// =============================================================================
// Stage 3 — Treble network + ATTACK switch (R7/R8, C5/C9/C6, R12/R14, C8,
//           R11/C7/R13) — circuit.md "Treble network + ATTACK (SW1)"
// =============================================================================
// Linear, passive, switched. Sits between the J201 drain (node G) and the
// IC2_A DRIVE stage ((+) input = node Q). Shapes the treble content fed into
// the distortion; the 3-way ATTACK switch reroutes C8 (220pF):
//
//   circuit.md CORRECTED topology (2026-07-20 — the switch POLE is C8's bottom
//   plate; C8's top plate is fixed to node P; throws are node M and GND):
//     Boost : pole -> M   -> C8 bridges R8 (spans M<->P)  -> treble boost
//     Flat  : pole open    -> C8 inert                     -> flat  ([ENG] centre)
//     Cut   : pole -> GND  -> C8 shunts P to ground        -> treble cut
//   The forward path G-R7-M-R8-P-C7-Q is intact in ALL positions (no mute).
//
// ---- Stage boundary: the J201 drain is a CURRENT source ---------------------
// ** CHANGED 2026-07-22 (Phase-7 calibration), discharging the Phase-4 deferral
//    that used to read "Input node G (J201 drain) = IDEAL voltage source (source
//    Z = 0); revisit with an explicit J201 output impedance at Phase 7." **
//
// Node G is now a real unknown node driven by the J201's Norton current, with
// that device's output impedance stamped in alongside it:
//
//        i_drain (from JfetStage::process)  ->  node G
//        node G --[ro]-- node H --[Rp || Cp]-- GND        = ro*k(s), the
//        node G --[Rq2]-------------------- GND             degeneration-shaped
//                                                           drain resistance,
//                                                           in parallel with the
//                                                           C4-bootstrapped Q2
//                                                           active load.
//
// This matters a great deal, not marginally: the ladder's input impedance falls
// from ~35 kOhm at 200 Hz to ~6.5 kOhm at 2 kHz, so an ideal (0 ohm) source let
// the C5/C9/C6 HF bypass of R7 through at full strength AND let JfetStage apply
// its C3 shelf on top — double-counting, worth ~+23 dB of excess HF in the OD
// path (docs/phase7-calibration-handover.md). See JfetStage.h's header for the
// device algebra (Gm*Rout = gm*ro is flat; only the LOADED gain shelves).
//
// Output is still V(Q), the voltage at IC2_A(+), which draws no current — a
// clean stage boundary; the DRIVE stage multiplies V(Q).
//
// ---- Why MNA rather than a WDF tree --------------------------------------
// R7 and the C5/C9/C6 ladder BOTH connect G to node M (a loop), and there are
// several ground-referenced shunts — so this is not a series/parallel WDF tree;
// it would need a hand-derived R-type scattering matrix. For a LINEAR passive
// block with a current source in and an unloaded output, nodal analysis (MNA)
// with trapezoidal-companion capacitors is exact, uses the SAME bilinear cap
// discretisation as chowdsp's CapacitorT (identical warp), maps 1:1 onto the
// analytic oracle in analysis/eq_reference.py (so it validates directly), and
// handles the 3 switch positions by precomputing one nodal matrix inverse per
// position (dsp.md "precompute per topology" — here a plain matrix swap).
//
// Node indices for the 7 unknowns: G=0, H=1, M=2, P=3, L1=4, L2=5, Q=6.
// GND = 0 V. G is no longer a known source.
//
// ⚠ The matrix now depends on the FITTED source-Z values as well as on the
// switch position, so setSourceZ() re-inverts (three 7x7 Gauss-Jordans, stack
// only, no allocation). It is called from setFitParams(), i.e. at most once per
// block and never per sample — and it early-outs when nothing changed.
// =============================================================================
class TrebleAttack
{
public:
    enum class Attack
    {
        Boost = 0, // C8 bridges R8
        Flat,      // C8 open (centre) [ENG]
        Cut        // C8 shunts P->GND
    };

    // Component values (circuit.md "Treble / pre-clip network + ATTACK switch").
    static constexpr double kR7 = 200.0e3;
    static constexpr double kR8 = 470.0e3;
    static constexpr double kR11 = 470.0e3;
    static constexpr double kR12 = 6.8e3;
    static constexpr double kR13 = 1.0e6;
    static constexpr double kR14 = 22.0e3;
    static constexpr double kC5 = 22.0e-9;
    static constexpr double kC9 = 22.0e-9;
    static constexpr double kC6 = 22.0e-9;
    static constexpr double kC7 = 100.0e-9;
    static constexpr double kC8 = 220.0e-12;

    // size_t (not int) so every array subscript below is already the right
    // signedness — std::array::operator[] takes size_type, and an int index
    // would make each of the ~35 subscripts in this file an implicit signed->
    // unsigned conversion (-Wsign-conversion).
    static constexpr size_t N = 7;             // node count
    static constexpr size_t G = 0, H = 1, M = 2, P = 3, L1 = 4, L2 = 5, Q = 6;

    TrebleAttack() = default;

    void prepare(double sampleRate)
    {
        // Trapezoidal companion conductances: gc = 2*C / T.
        twoOverT = 2.0 * sampleRate;
        gc5 = kC5 * twoOverT;
        gc9 = kC9 * twoOverT;
        gc6 = kC6 * twoOverT;
        gc7 = kC7 * twoOverT;
        gc8 = kC8 * twoOverT;

        prepared = true;
        rebuild();
        reset();
    }

    // The J201 drain network (JfetStage::getSourceZ): Zout(s) = [ro + Rp||Cp] || Rq2.
    void setSourceZ(double roOhm, double rq2Ohm, double rpOhm, double cpFarad) noexcept
    {
        // Bit-compare (not ==) so this is an exact "did anything move?" check without
        // tripping -Wfloat-equal: the point is to skip the three matrix inversions when
        // setFitParams() re-sends identical values every block, and any difference at
        // all — however tiny — legitimately needs a rebuild.
        const std::array<double, 4> next { roOhm, rq2Ohm, rpOhm, cpFarad };
        if (std::memcmp(next.data(), srcZ.data(), sizeof(srcZ)) == 0)
            return;
        srcZ = next;
        if (prepared)
            rebuild();
    }

    void reset()
    {
        ieqC5 = ieqC9 = ieqC6 = ieqC7 = ieqC8 = ieqCp = 0.0;
    }

    void setAttack(Attack a) noexcept
    {
        // C8 changes topological role between positions (M<->P bridge, P->GND
        // shunt, or open), so its carried history is meaningless across a swap —
        // zero it to avoid injecting a spurious transient. (The other caps'
        // connections are position-invariant, so their state is safe to keep.)
        // Phase 5 adds the glitch-free crossfade on top of this.
        if (a != attack)
            ieqC8 = 0.0;
        attack = a;
    }

    // Process one sample. IN: the J201 drain NORTON CURRENT in amps (signed for
    // injection into node G). OUT: real volts at Q.
    inline double process(double iIn) noexcept
    {
        // ---- Build RHS: source current + capacitor history (Ieq) ------------
        // Cap convention (unchanged): for a cap across (a,b) with
        // ieq = 2*gc*(va - vb) - ieq_old, contribute b[a] += ieq, b[b] -= ieq.
        std::array<double, N> b {};
        b[G] = iIn + ieqC5;          // Norton drive; C5 (a=G,b=L1)
        b[H] = ieqCp;                // Cp (a=H,b=GND)
        b[M] = -ieqC6;               // C6 (a=L2,b=M)
        b[P] = ieqC7;                // C7 (a=P,b=Q)
        b[L1] = -ieqC5 + ieqC9;      // C5 -> -Ieq ; C9 (a=L1,b=L2) -> +Ieq
        b[L2] = -ieqC9 + ieqC6;      // C9 -> -Ieq ; C6 -> +Ieq
        b[Q] = -ieqC7;               // C7 -> -Ieq

        if (attack == Attack::Boost) // C8 (a=M,b=P)
        {
            b[M] += ieqC8;
            b[P] -= ieqC8;
        }
        else if (attack == Attack::Cut) // C8 (a=P,b=GND)
        {
            b[P] += ieqC8;
        }

        // ---- Solve v = Yinv * b ----
        const auto& A = yInv[static_cast<size_t>(attack)];
        std::array<double, N> v {};
        for (size_t i = 0; i < N; ++i)
        {
            double acc = 0.0;
            for (size_t j = 0; j < N; ++j)
                acc += A[i][j] * b[j];
            v[i] = acc;
        }

        // ---- Update capacitor states: Ieq_new = 2*gc*v_ab - Ieq_old ----
        ieqC5 = 2.0 * gc5 * (v[G] - v[L1]) - ieqC5;
        ieqC9 = 2.0 * gc9 * (v[L1] - v[L2]) - ieqC9;
        ieqC6 = 2.0 * gc6 * (v[L2] - v[M]) - ieqC6;
        ieqC7 = 2.0 * gc7 * (v[P] - v[Q]) - ieqC7;
        ieqCp = 2.0 * gcp * (v[H]) - ieqCp;
        if (attack == Attack::Boost)
            ieqC8 = 2.0 * gc8 * (v[M] - v[P]) - ieqC8;
        else if (attack == Attack::Cut)
            ieqC8 = 2.0 * gc8 * (v[P]) - ieqC8;

        return v[Q];
    }

private:
    static constexpr double kG7 = 1.0 / kR7;
    static constexpr double kG8 = 1.0 / kR8;
    static constexpr double kG11 = 1.0 / kR11;
    static constexpr double kG12 = 1.0 / kR12;
    static constexpr double kG13 = 1.0 / kR13;
    static constexpr double kG14 = 1.0 / kR14;

    using Mat = std::array<std::array<double, N>, N>;

    void rebuild()
    {
        gcp = srcZ[3] * twoOverT;
        for (size_t pos = 0; pos < 3; ++pos)
            invert(buildY(static_cast<Attack>((int) pos)), yInv[pos]);
    }

    // Build the nodal conductance matrix Y for one ATTACK position.
    Mat buildY(Attack pos) const
    {
        Mat Y {};
        // ---- J201 drain output network (see header) ----
        const double gro = 1.0 / srcZ[0], gRq2 = 1.0 / srcZ[1], gRp = 1.0 / srcZ[2];
        Y[G][G] += gro; Y[G][H] -= gro; Y[H][G] -= gro; Y[H][H] += gro; // ro (G-H)
        Y[G][G] += gRq2;                                  // Rq2 (G-GND)
        Y[H][H] += gRp;                                   // Rp  (H-GND)
        Y[H][H] += gcp;                                   // Cp  (H-GND)
        // ---- Resistors ----
        Y[G][G] += kG7; Y[G][M] -= kG7; Y[M][G] -= kG7; Y[M][M] += kG7; // R7 (G-M)
        Y[M][M] += kG8; Y[M][P] -= kG8; Y[P][M] -= kG8; Y[P][P] += kG8; // R8 (M-P)
        Y[P][P] += kG11;                                  // R11 (P-GND)
        Y[L1][L1] += kG12;                                // R12 (L1-GND)
        Y[Q][Q] += kG13;                                  // R13 (Q-GND)
        Y[L2][L2] += kG14;                                // R14 (L2-GND)
        // ---- Capacitor companion conductances ----
        Y[G][G] += gc5; Y[G][L1] -= gc5; Y[L1][G] -= gc5; Y[L1][L1] += gc5;     // C5 (G-L1)
        Y[L1][L1] += gc9; Y[L1][L2] -= gc9; Y[L2][L1] -= gc9; Y[L2][L2] += gc9; // C9 (L1-L2)
        Y[L2][L2] += gc6; Y[L2][M] -= gc6; Y[M][L2] -= gc6; Y[M][M] += gc6;     // C6 (L2-M)
        Y[P][P] += gc7; Y[P][Q] -= gc7; Y[Q][P] -= gc7; Y[Q][Q] += gc7;         // C7 (P-Q)
        if (pos == Attack::Boost) // C8 (M-P)
        {
            Y[M][M] += gc8; Y[M][P] -= gc8; Y[P][M] -= gc8; Y[P][P] += gc8;
        }
        else if (pos == Attack::Cut) // C8 (P-GND)
        {
            Y[P][P] += gc8;
        }
        return Y;
    }

    // Gauss-Jordan inverse with partial pivoting (N=7, runs once per position).
    static void invert(Mat src, Mat& dst)
    {
        Mat a = src;
        for (size_t i = 0; i < N; ++i)
            for (size_t j = 0; j < N; ++j)
                dst[i][j] = (i == j) ? 1.0 : 0.0;

        for (size_t col = 0; col < N; ++col)
        {
            size_t piv = col;
            double best = std::abs(a[col][col]);
            for (size_t r = col + 1; r < N; ++r)
            {
                const double v = std::abs(a[r][col]);
                if (v > best) { best = v; piv = r; }
            }
            if (piv != col)
            {
                std::swap(a[piv], a[col]);
                std::swap(dst[piv], dst[col]);
            }
            const double d = a[col][col];
            for (size_t j = 0; j < N; ++j) { a[col][j] /= d; dst[col][j] /= d; }
            for (size_t r = 0; r < N; ++r)
            {
                if (r == col) continue;
                const double f = a[r][col];
                if (f == 0.0) continue;
                for (size_t j = 0; j < N; ++j) { a[r][j] -= f * a[col][j]; dst[r][j] -= f * dst[col][j]; }
            }
        }
    }

    // Source-Z (J201 drain) as { ro, Rq2, Rp, Cp } — nominal-initialised from
    // JfetStage's nominals so a default-constructed stage is self-consistent
    // without an explicit setSourceZ() call.
    std::array<double, 4> srcZ { 200.0e3,
                                 1.0e6,
                                 200.0e3 * (0.69e-3 * 3.3e3),
                                 (3.3e3 * 220.0e-9) / (200.0e3 * (0.69e-3 * 3.3e3)) };

    bool prepared = false;
    double twoOverT = 2.0 * 48000.0;
    // Companion conductances (set in prepare()/rebuild()).
    double gc5 = 0.0, gc9 = 0.0, gc6 = 0.0, gc7 = 0.0, gc8 = 0.0, gcp = 0.0;
    // Capacitor history (equivalent-source) currents.
    double ieqC5 = 0.0, ieqC9 = 0.0, ieqC6 = 0.0, ieqC7 = 0.0, ieqC8 = 0.0, ieqCp = 0.0;
    // One precomputed nodal-matrix inverse per ATTACK position (Boost/Flat/Cut).
    std::array<Mat, 3> yInv {};
    Attack attack = Attack::Flat;

    TrebleAttack(const TrebleAttack&) = delete;
    TrebleAttack& operator=(const TrebleAttack&) = delete;
};
