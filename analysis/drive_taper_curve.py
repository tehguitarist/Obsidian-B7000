#!/usr/bin/env python3.11
"""Phase-7 SESSION 17 — turn session 16's MEASURED DRIVE taper into a shippable curve.

INPUT (session 16, `analysis/drive_taper_bleedfree.py`, handover §3v.1). The VR3 resistance was
measured BLEED-FREE — the clean-BLEND bleed is cancelled ALGEBRAICALLY, not estimated — and
validated three ways (an L-006 self-test recovering a KNOWN taper to 0.00%, two estimators that
fail differently agreeing to <=2.3%, flat per-rung stability):

        knob 0.25 (9:30) -> 65.13k      knob 0.50 (noon) -> 25.36k      knob 0.75 (2:30) -> 6.27k

The two ENDPOINTS are taper-shape-INDEPENDENT circuit facts (R = 100k at knob 0, R = 0 at knob 1),
so any candidate curve must pin them exactly and is judged only on the three interior points.

⚠ WHAT THIS SCRIPT FOUND, AND WHY IT CONTRADICTS THE SESSION BRIEF. The session-16 handover and the
session-17 brief both prescribe "replace the power law with a proper C-taper (reverse-log) curve",
on the reasoning that the per-knob effective exponents (1.49/1.98/2.00) are not one constant, so the
SHAPE FAMILY must be wrong. That reasoning does not survive contact with the numbers: the spread is
driven almost entirely by the 9:30 point, and when the candidate families are actually scored
against all three measured points, **the reverse-log families fit WORSE than a plain power law** —
2.8x-3.4x worse in max error. The shipped p = 2.5 is a wrong EXPONENT, not a wrong family.

So this script does NOT hand-pick a family; it scores them and reports. Everything it prints is
reproducible from the three measured resistances and closed-form curves — no renders, no captures.

Both errors are reported, and the SECOND one is the one that matters:
  * resistance error  — what the taper curve itself gets wrong;
  * STAGE-GAIN error  — what that becomes audibly, through 1 + R15/(R17 + Rd + R32). The gain leg
    is dominated by R15 = 330k, so a large fractional error in a small Rd compresses a lot. Judging
    a taper on resistance error alone systematically overstates the damage.

Run:  /opt/homebrew/bin/python3.11 analysis/drive_taper_curve.py
Log:  analysis/fit_logs/step7_drive_taper_curve.log
"""
import os
import numpy as np
from scipy.optimize import brentq, minimize, minimize_scalar

LOG = "analysis/fit_logs/step7_drive_taper_curve.log"

# Measured (session 16). x = knob (0..1); u = 1 - x is rotation from the max-resistance end, which
# is the variable every taper family below is naturally written in. g = R / Rmax.
X = np.array([0.25, 0.50, 0.75])
U = 1.0 - X
R_MEAS = np.array([65.13e3, 25.36e3, 6.27e3])
RMAX = 100.0e3
G = R_MEAS / RMAX
KNOB = ["9:30", "noon", "2:30"]

# DriveStage.h gain leg: gain = 1 + R15 / (R17 + Rd + R32).
R15, R17, R32 = 330.0e3, 3.3e3, 1.0e3
SHIPPED_P = 2.5


def gain_db(rd):
    return 20.0 * np.log10(1.0 + R15 / (R17 + np.asarray(rd, float) + R32))


def errs(g_pred):
    """(resistance error dB, stage-gain error dB) of a predicted g vs the measurement."""
    return (20.0 * np.log10(g_pred / G), gain_db(g_pred * RMAX) - gain_db(R_MEAS))


def main():
    os.makedirs("analysis/fit_logs", exist_ok=True)
    log = open(LOG, "w")

    def emit(s=""):
        print(s)
        log.write(s + "\n")

    emit("=" * 100)
    emit("SESSION-17 — DRIVE taper: scoring candidate curves against the session-16 measurement")
    emit("=" * 100)
    emit(f"  measured:  " + "   ".join(f"{k} (x={x:.2f}) R={r/1e3:.2f}k"
                                       for k, x, r in zip(KNOB, X, R_MEAS)))
    emit(f"  endpoints PINNED by construction: R(0) = {RMAX/1e3:.0f}k, R(1) = 0")
    emit(f"  per-knob effective exponent ln(g)/ln(u): "
         f"{np.round(np.log(G) / np.log(U), 3)}   <- the spread that prompted 'wrong family'")
    emit("")

    cands = []

    # --- the shipped curve, for reference ---
    cands.append((f"power law u^p  [SHIPPED p={SHIPPED_P}]", U ** SHIPPED_P))

    # --- 1-dof families, each given its best single parameter ---
    p_ls = minimize_scalar(lambda p: np.sum((20 * np.log10(U ** p / G)) ** 2),
                           bounds=(0.5, 5.0), method="bounded").x
    cands.append((f"power law u^p  [LS p={p_ls:.3f}]", U ** p_ls))

    # exponential reverse-log, the textbook "C taper": g = (b^u - 1)/(b - 1)
    b = brentq(lambda b: (b ** 0.5 - 1) / (b - 1) - G[1], 1.0001, 1e9)
    cands.append((f"exp C-taper (b^u-1)/(b-1)  [b={b:.2f}]", (b ** U - 1) / (b - 1)))

    # Mobius / "linearity factor" taper: g = u / (u + k(1-u))
    k = 1.0 / G[1] - 1.0
    cands.append((f"Mobius u/(u+k(1-u))  [k={k:.3f}]", U / (U + k * (1 - U))))

    # --- 2-dof: what a real log/reverse-log pot physically IS (a 2-segment conductive track) ---
    def pw(u, ub, gb):
        u = np.asarray(u, float)
        return np.where(u <= ub, gb * u / ub, gb + (1 - gb) * (u - ub) / (1 - ub))

    r = minimize(lambda t: np.sum((20 * np.log10(pw(U, t[0], t[1]) / G)) ** 2), [0.5, 0.25],
                 bounds=[(0.05, 0.95), (0.01, 0.99)])
    cands.append((f"2-seg PWL [break u={r.x[0]:.3f}, g={r.x[1]:.3f}]", pw(U, *r.x)))

    emit("-" * 100)
    emit("CANDIDATES — error at the three measured knob points")
    emit("-" * 100)
    emit(f"  {'curve':44s} | {'resistance err dB':>26s} | {'STAGE-GAIN err dB':>26s} | {'max|gain|':>9s}")
    emit(f"  {'':44s} | " + " ".join(f"{k:>8s}" for k in KNOB) + " | "
         + " ".join(f"{k:>8s}" for k in KNOB) + " |")
    for name, gp in cands:
        er, eg = errs(gp)
        emit(f"  {name:44s} | " + " ".join(f"{v:>+8.2f}" for v in er) + " | "
             + " ".join(f"{v:>+8.2f}" for v in eg) + f" | {np.abs(eg).max():>9.2f}")

    emit("")
    emit("-" * 100)
    emit("READING")
    emit("-" * 100)
    emit("  * The two REVERSE-LOG families — the ones the session-16 plan called for — are the WORST")
    emit("    fits of any candidate here, worse than the plain power law they were meant to replace.")
    emit("    The 'wrong shape family' inference does not hold: the measured curve is not less")
    emit("    power-law-like than a C-taper, it is MORE so.")
    emit("  * The shipped p = 2.5 is a wrong EXPONENT. Re-deriving it from the measurement gives")
    emit(f"    p = {p_ls:.2f}, which cuts the worst stage-gain error from "
         f"{np.abs(errs(U**SHIPPED_P)[1]).max():.2f} dB to {np.abs(errs(U**p_ls)[1]).max():.2f} dB.")
    emit("  * The 2-segment piecewise-linear track — which is what a real log/reverse-log pot")
    emit("    physically is — fits best, but it buys under a dB over the re-derived power law and")
    emit("    costs a new curve shape in DriveStage.h. Not worth it unless a later measurement")
    emit("    disagrees with the power law by more than that.")
    emit("")
    emit(f"  ** RECOMMENDATION: driveTaperExp 2.5 -> {p_ls:.2f}, keeping the existing power-law")
    emit("     curve. This is a one-constant change re-derived from a measurement, NOT a new fit")
    emit("     against harmonic data — the exponent is read off the measured resistances only. **")
    emit("")
    emit("  ⚠ ADOPT ONLY AS PART OF A RE-FIT. Session 16's drive_taper_gate.py showed the corrected")
    emit("    taper delivers LESS level at noon and therefore moves the noon H3-H2 metric the WRONG")
    emit("    way on its own. It is right as circuit modelling and wrong as a standalone change.")
    log.close()
    print(f"\n[log] {LOG}")


if __name__ == "__main__":
    main()
