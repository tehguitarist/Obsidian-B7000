#pragma once

#include <cmath>

// =============================================================================
// MnaSolve — tiny fixed-size dense linear-algebra helper for the EQ block
// =============================================================================
// The linear stages built so far (TrebleAttack, RecoveryBridgedT, SallenKeyLPF)
// all have a FIXED nodal matrix, so their 2×2 inverse is precomputed once in
// prepare(). The EQ peaking stages don't: BASS/TREBLE/LO-MID/HI-MID pots move
// the pot-split resistances (Ra, Rb), so the real MNA conductance matrix Y
// changes whenever a pot (or a mid-switch series cap) moves — the inverse must
// be recomputed then. It is NOT recomputed per sample: with trapezoidal
// companion caps the matrix is entirely REAL and constant for a given pot/cap
// setting (the frequency dependence lives in the per-sample RHS history
// currents, exactly as in the fixed 2-node stages), so a stage only re-inverts
// on a "dirty" flag set by a pot/switch change — at most once per block off the
// smoothed parameter, no allocation, real-time safe.
//
// invert<N>() is Gauss-Jordan with partial pivoting on a local copy (N is 4 for
// MidBand, 7 for Baxandall). Returns false on a singular matrix (degenerate pot
// endpoint) so the caller can fall back to the previous good inverse rather than
// emit NaNs. Per-sample the stage just does an N×N matrix–vector multiply with
// the stored inverse.
// =============================================================================
namespace mna {

// Bit-exact "has this value moved?" test for the stages' dirty flags.
//
// A dirty flag wants EXACT inequality: any change at all, however small, must
// trigger a re-inversion, and an epsilon would silently ignore small pot moves.
// But a literal `a != b` on doubles trips -Wfloat-equal, which exists to catch
// approximate-comparison bugs this deliberately is not. Spelling it as two
// relational tests says "ordering differs" instead of "floats are equal",
// keeping the exact semantics (identical for all non-NaN inputs) without
// suppressing the warning globally and going blind to a real misuse elsewhere.
inline bool differs(double a, double b) noexcept { return (a < b) || (b < a); }


template <int N>
inline bool invert(const double src[N][N], double inv[N][N]) noexcept
{
    double a[N][2 * N];
    for (int i = 0; i < N; ++i)
    {
        for (int j = 0; j < N; ++j)
        {
            a[i][j] = src[i][j];
            a[i][N + j] = (i == j) ? 1.0 : 0.0;
        }
    }

    for (int col = 0; col < N; ++col)
    {
        // Partial pivot: pick the largest-magnitude entry in this column.
        int piv = col;
        double best = std::abs(a[col][col]);
        for (int r = col + 1; r < N; ++r)
        {
            const double m = std::abs(a[r][col]);
            if (m > best) { best = m; piv = r; }
        }
        if (best < 1e-300)
            return false; // singular

        if (piv != col)
            for (int j = 0; j < 2 * N; ++j)
            {
                const double t = a[col][j];
                a[col][j] = a[piv][j];
                a[piv][j] = t;
            }

        const double inv_p = 1.0 / a[col][col];
        for (int j = 0; j < 2 * N; ++j)
            a[col][j] *= inv_p;

        for (int r = 0; r < N; ++r)
        {
            if (r == col) continue;
            const double f = a[r][col];
            if (f == 0.0) continue;
            for (int j = 0; j < 2 * N; ++j)
                a[r][j] -= f * a[col][j];
        }
    }

    for (int i = 0; i < N; ++i)
        for (int j = 0; j < N; ++j)
            inv[i][j] = a[i][N + j];
    return true;
}

// y = M * x  (N×N times N-vector).
template <int N>
inline void matvec(const double m[N][N], const double x[N], double y[N]) noexcept
{
    for (int i = 0; i < N; ++i)
    {
        double acc = 0.0;
        for (int j = 0; j < N; ++j)
            acc += m[i][j] * x[j];
        y[i] = acc;
    }
}

} // namespace mna
