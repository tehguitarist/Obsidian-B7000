#pragma once

#include <array>
#include <cmath>
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
// ---- Stage boundary / source convention (build-plan Phase 4, user-confirmed) -
//   Input node G (J201 drain) = IDEAL voltage source (source Z = 0) for Phase 4;
//   revisit with an explicit J201 output impedance at Phase 7 capture. Output =
//   V(Q), the voltage at IC2_A(+), which draws no current (unloaded) — a clean
//   stage boundary; the DRIVE stage multiplies V(Q).
//
// ---- Why MNA rather than a WDF tree --------------------------------------
// R7 and the C5/C9/C6 ladder BOTH connect G to node M (a loop), and there are
// several ground-referenced shunts — so this is not a series/parallel WDF tree;
// it would need a hand-derived R-type scattering matrix. For a LINEAR passive
// block with an ideal source in and an unloaded output, nodal analysis (MNA)
// with trapezoidal-companion capacitors is exact, uses the SAME bilinear cap
// discretisation as chowdsp's CapacitorT (identical warp), maps 1:1 onto the
// analytic oracle in analysis/eq_reference.py (so it validates directly), and
// handles the 3 switch positions by precomputing one nodal matrix inverse per
// position (dsp.md "precompute per topology" — here a plain matrix swap).
//
// Node indices for the 5 unknowns: M=0, P=1, L1=2, L2=3, Q=4. G is the known
// source; GND = 0.
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

    static constexpr int N = 5;             // node count
    static constexpr int M = 0, P = 1, L1 = 2, L2 = 3, Q = 4;

    TrebleAttack() = default;

    void prepare(double sampleRate)
    {
        // Trapezoidal companion conductances: gc = 2*C / T.
        const double twoOverT = 2.0 * sampleRate;
        gc5 = kC5 * twoOverT;
        gc9 = kC9 * twoOverT;
        gc6 = kC6 * twoOverT;
        gc7 = kC7 * twoOverT;
        gc8 = kC8 * twoOverT;

        for (int pos = 0; pos < 3; ++pos)
            invert(buildY(static_cast<Attack>(pos)), yInv[pos]);

        reset();
    }

    void reset()
    {
        ieqC5 = ieqC9 = ieqC6 = ieqC7 = ieqC8 = 0.0;
    }

    void setAttack(Attack a) noexcept
    {
        // C8 changes topological role between positions (M<->P bridge, P->GND
        // shunt, or open), so its carried history is meaningless across a swap —
        // zero it to avoid injecting a spurious transient. (The other four caps'
        // connections are position-invariant, so their state is safe to keep.)
        // Phase 5 adds the glitch-free crossfade on top of this.
        if (a != attack)
            ieqC8 = 0.0;
        attack = a;
    }

    // Process one sample (real volts in at G, real volts out at Q).
    inline double process(double x) noexcept
    {
        // ---- Build RHS: source (x) contributions + capacitor history (Ieq) ----
        std::array<double, N> b {};
        b[M] = kG7 * x - ieqC6;      // R7 from source; C6 (a=L2,b=M) -> RHS[M] -= Ieq
        b[P] = ieqC7;                // C7 (a=P,b=Q) -> RHS[P] += Ieq
        b[L1] = gc5 * x - ieqC5 + ieqC9; // C5 (a=G,b=L1): +gc5*x - Ieq ; C9 (a=L1,b=L2): +Ieq
        b[L2] = -ieqC9 + ieqC6;      // C9 -> RHS[L2] -= Ieq ; C6 -> RHS[L2] += Ieq
        b[Q] = -ieqC7;               // C7 -> RHS[Q] -= Ieq

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
        const auto& A = yInv[static_cast<int>(attack)];
        std::array<double, N> v {};
        for (int i = 0; i < N; ++i)
        {
            double acc = 0.0;
            for (int j = 0; j < N; ++j)
                acc += A[i][j] * b[j];
            v[i] = acc;
        }

        // ---- Update capacitor states: Ieq_new = 2*gc*v_ab - Ieq_old ----
        ieqC5 = 2.0 * gc5 * (x - v[L1]) - ieqC5;
        ieqC9 = 2.0 * gc9 * (v[L1] - v[L2]) - ieqC9;
        ieqC6 = 2.0 * gc6 * (v[L2] - v[M]) - ieqC6;
        ieqC7 = 2.0 * gc7 * (v[P] - v[Q]) - ieqC7;
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

    // Build the nodal conductance matrix Y for one ATTACK position.
    Mat buildY(Attack pos) const
    {
        Mat Y {};
        // Resistors.
        Y[M][M] += kG7;                                   // R7 (G-M), source side -> RHS
        Y[M][M] += kG8; Y[M][P] -= kG8; Y[P][M] -= kG8; Y[P][P] += kG8; // R8 (M-P)
        Y[P][P] += kG11;                                  // R11 (P-GND)
        Y[L1][L1] += kG12;                                // R12 (L1-GND)
        Y[Q][Q] += kG13;                                  // R13 (Q-GND)
        Y[L2][L2] += kG14;                                // R14 (L2-GND)
        // Capacitor companion conductances.
        Y[L1][L1] += gc5;                                 // C5 (G-L1), source side -> RHS
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

    // Gauss-Jordan inverse with partial pivoting (N=5, runs once per position).
    static void invert(Mat src, Mat& dst)
    {
        Mat a = src;
        for (int i = 0; i < N; ++i)
            for (int j = 0; j < N; ++j)
                dst[i][j] = (i == j) ? 1.0 : 0.0;

        for (int col = 0; col < N; ++col)
        {
            int piv = col;
            double best = std::abs(a[col][col]);
            for (int r = col + 1; r < N; ++r)
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
            for (int j = 0; j < N; ++j) { a[col][j] /= d; dst[col][j] /= d; }
            for (int r = 0; r < N; ++r)
            {
                if (r == col) continue;
                const double f = a[r][col];
                if (f == 0.0) continue;
                for (int j = 0; j < N; ++j) { a[r][j] -= f * a[col][j]; dst[r][j] -= f * dst[col][j]; }
            }
        }
    }

    // Companion conductances (set in prepare()).
    double gc5 = 0.0, gc9 = 0.0, gc6 = 0.0, gc7 = 0.0, gc8 = 0.0;
    // Capacitor history (equivalent-source) currents.
    double ieqC5 = 0.0, ieqC9 = 0.0, ieqC6 = 0.0, ieqC7 = 0.0, ieqC8 = 0.0;
    // One precomputed nodal-matrix inverse per ATTACK position (Boost/Flat/Cut).
    std::array<Mat, 3> yInv {};
    Attack attack = Attack::Flat;

    TrebleAttack(const TrebleAttack&) = delete;
    TrebleAttack& operator=(const TrebleAttack&) = delete;
};
