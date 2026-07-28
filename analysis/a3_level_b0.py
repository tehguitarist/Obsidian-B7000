#!/usr/bin/env python3.11
"""a3_level_b0 -- measure the CLEAN-BLEED LEVEL b0 from the LEVEL pot law, instead of taking it from
the model (session 54, Phase 9 / A3; Set D).

WHY THIS IS THE LAST SOFT SPOT
------------------------------
`a3_blend_axis` is provably DEGENERATE in b0: three unknowns (c, P, Q) map onto two quadratic
coefficients, so every bleed level fits equally well and the tool takes b0 from the model
(0.14239, -16.93 dB). Every number that instrument has produced -- including session 52's
impossibility proof and session 51's mutual validation -- therefore INHERITS the model's own bleed.
Session 52 tried to break it by scanning b0 and found the cost saturates as b0 -> 0 with no interior
optimum ("make it see less"), i.e. the blend axis cannot settle it from inside. It needs a different
axis, and LEVEL is one.

THE LAW, WHICH HAS NO FREE PARAMETER EXCEPT THE TAPER
-----------------------------------------------------
At BLEND max the wiper sits on the LEVEL wiper node, which is a three-way Thevenin node: the OD
source through the pot's upper section Rp(1-L), VD (signal ground) through the lower section Rp.L,
and -- because the BLEND track still bridges it to the clean source -- the clean source through the
whole 100k. With Rp normalised out:

    V(L) = [ Vod/(1-L) + Vclean ] / D(L),     D(L) = 1/(1-L) + 1/L + 1

so the OD leg scales as 1/(1-L) while the bleed leg does not scale at all, and the bleed
coefficient at any LEVEL is exactly b0(L) = 1/D(L). That IS `a3_blend_axis.model_b0()` -- the same
formula -- so this measures the identical quantity the blend axis assumes.

Ratios against the LEVEL-noon capture cancel the absolute scale AND every post-BLEND stage:

    T(L) = V(L)/V(L0) = ( |g/(1-L) + 1| / D(L) ) / ( |g/(1-L0) + 1| / D(L0) ),   g = Vod/Vclean

Unknowns: a COMPLEX g per band (2 per band) and the taper exponent p (ONE, shared across every
band). Four LEVEL positions give three independent ratios per band, so N bands give 3N equations
against 2N+1 unknowns -- over-determined by N-1, and it is the SHARED p that makes it so. b0 then
follows as 1/D(0.5^p) with no further assumption.

⚠ WHY DRIVE MIN. At drive min the OD path is ~linear, so `g` is a genuine constant across the LEVEL
sweep. At any hotter drive the LEVEL pot would change the level into nothing (LEVEL is AFTER the
clipper) -- but the OD path's own compression is set upstream, so g would still be constant. The
real reason for drive-min is different and worth keeping: at drive min the OD contribution is small,
which makes `1` (the bleed) the DOMINANT term in `g/(1-L) + 1`, and the bleed is what is being
measured. Measuring a term where it dominates is the whole point.

⚠ WHAT THIS DOES NOT DO. It does not re-open the blend axis's theta. It returns b0 (and p). If b0
lands on the model's 0.14239 the inheritance was harmless and session 52 stands unqualified; if it
does not, every s_blend and every H_req needs recomputing at the measured value.

Run:
    python3.11 analysis/a3_level_b0.py --selftest
    python3.11 analysis/a3_level_b0.py
"""
import argparse
import json
import math
import os
import sys

import numpy as np
from scipy.optimize import least_squares

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import a3_blend_axis as AX

REPORT = "analysis/reports/s54_matrix85.json"
SWEEP = "sweep_drv_-18"
FIT_HI_HZ = AX.FIT_HI_HZ
FIT_LO_HZ = 40.0

# (LEVEL knob, capture). captures.py::_clock_to_x. LEVEL noon is the reference (drive-0700_base-od
# IS level noon at drive min); level-0700 is the silent L=0 null and is deliberately absent.
LEVELS = [
    (0.25, "drive-0700_level-0930_base-od.wav"),
    (0.50, "drive-0700_base-od.wav"),
    (0.75, "drive-0700_level-1430_base-od.wav"),
    (1.00, "drive-0700_level-1700_base-od.wav"),
]
REF_I = 1                                    # index of the LEVEL-noon normaliser


#  ⚠⚠ NUMERICALLY STABLE FORM -- and it fixes a real error in the first draft.
#
#  The node equation is  V = (g/(1-L) + 1) / (1/(1-L) + 1/L + 1)  in units of Vclean. Multiplying
#  numerator and denominator by (1-L) removes the L -> 1 singularity entirely:
#
#      V(L) = (g + (1-L)) / (1 + (1-L)/L + (1-L))
#
#  At L = 1 that is exactly `g`, which is also what the circuit says: at LEVEL max the wiper sits ON
#  pin3, shorted to the OD source (a low-impedance op-amp output), so the output IS Vod and NO clean
#  bleed reaches the wiper -- b0(1) = 0.
#
#  The first draft instead special-cased L >= 1 as `|0.5g + 0.5|` with `bleed(1) = 0.5`, i.e. it
#  asserted the bleed is at its MAXIMUM exactly where it is actually ZERO. Because knob 1.0 gives
#  L = 1 for EVERY p, that one wrong point was present in every candidate fit and dragged the shared
#  taper from ~2.25 down to 1.33 while inflating the residual to ~2.3 dB. The measured t(0.25)
#  column had been pointing at p ~ 2.25 all along.
def _denom(L):
    return 1.0 + (1.0 - L) / L + (1.0 - L)


def bleed(L):
    """Coefficient on Vclean at the wiper. 0 at L=1 (shorted to the OD source), 0 at L=0."""
    if L <= 0.0:
        return 0.0
    return (1.0 - L) / _denom(L)


def predict(g, Ls):
    """|V(L)| in units of |Vclean|, for a complex g = Vod/Vclean."""
    return np.asarray([abs(g + (1.0 - L)) / _denom(L) for L in Ls])


def band_cost(g_re, g_im, t_obs, Ls):
    """⚠ LOG residual, not linear. A linear residual is dominated by whichever LEVEL point is
    loudest and effectively ignores the quiet ones -- and the quiet ones are where the bleed (the
    thing being measured) matters most. Guarded against a zero prediction so a null cannot produce
    an infinity that the optimiser then chases."""
    p = predict(complex(g_re, g_im), Ls)
    p = p / max(p[REF_I], 1e-12)
    return np.log(np.maximum(p, 1e-9)) - np.log(np.maximum(t_obs, 1e-9))


def solve_p(t_by_band, bands, p_init=2.25, fix_p=None):
    """Joint fit: one complex g per band + ONE shared taper exponent p."""
    knobs = [k for k, _ in LEVELS]

    def unpack(v):
        p = fix_p if fix_p is not None else v[0]
        gs = v[(0 if fix_p is not None else 1):].reshape(-1, 2)
        return p, gs

    def resid(v):
        p, gs = unpack(v)
        Ls = [k ** p for k in knobs]
        out = []
        for i, b in enumerate(bands):
            out.extend(band_cost(gs[i, 0], gs[i, 1], np.asarray(t_by_band[b]), Ls))
        return np.asarray(out)

    g0 = []
    for b in bands:
        g0.extend([0.3, 0.1])
    v0 = (list([] if fix_p is not None else [p_init])) + g0
    lo = ([] if fix_p is not None else [0.05]) + [-50.0] * len(g0)
    hi = ([] if fix_p is not None else [8.0]) + [50.0] * len(g0)
    sol = least_squares(resid, v0, bounds=(lo, hi), xtol=1e-14, ftol=1e-14)
    p, gs = unpack(sol.x)
    rms = float(np.sqrt(np.mean(np.square(sol.fun))))
    return p, gs, rms


def load(report):
    if not os.path.exists(report):
        sys.exit("missing %s" % report)
    d = json.load(open(report))
    bands = d["meta"]["bands"]
    caps = {c["file"]: c for c in d["captures"]}
    cols = []
    for _, f in LEVELS:
        if f not in caps:
            sys.exit("report has no %s" % f)
        cols.append(np.asarray(caps[f]["fr"][SWEEP]["pedal_db"], dtype=float))
    ref = cols[REF_I]
    return {b: [10.0 ** ((c[i] - ref[i]) / 20.0) for c in cols]
            for i, b in enumerate(bands) if all(np.isfinite(c[i]) for c in cols)}


def selftest():
    """Synthesise the ladder through the law from a KNOWN p and known per-band g, then check the
    joint fit recovers p (and hence b0). ⭐ Also checks the fit is not degenerate: a WRONG fixed p
    must cost visibly more, otherwise `p` is unidentified and the returned b0 is meaningless -- the
    exact failure mode (a flat objective read as a measurement) that session 52's b0 scan hit."""
    true_p = 2.25
    bands = [40.0, 101.0, 254.0, 640.0, 1613.0]
    truth = {f: complex(0.15 + f / 4000.0, -0.08 + f / 9000.0) for f in bands}
    Ls = [k ** true_p for k, _ in LEVELS]
    t = {}
    for f in bands:
        p = predict(truth[f], Ls)
        t[f] = list(p / p[REF_I])
    p_fit, _, rms = solve_p(t, bands)
    ok_p = abs(p_fit - true_p) < 1e-4 and rms < 1e-9
    b_true, b_fit = bleed(0.5 ** true_p), bleed(0.5 ** p_fit)
    print("  recovery: p = %.6f (true %.4f), rms %.2e  ->  b0 = %.6f (true %.6f)  %s"
          % (p_fit, true_p, rms, b_fit, b_true, "PASS" if ok_p else "FAIL"))
    off = [(pp, solve_p(t, bands, fix_p=pp)[2]) for pp in (1.5, 2.0, 2.25, 2.5, 3.0)]
    print("  identifiability -- rms at fixed p: %s"
          % "  ".join("p=%.2f %.2e" % x for x in off))
    ok_id = min(x[1] for x in off if abs(x[0] - true_p) > 0.2) > 100 * rms
    print("  a wrong p must cost visibly more -> %s" % ("PASS" if ok_id else "FAIL (p is flat!)"))
    return ok_p and ok_id


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--report", default=REPORT)
    args = ap.parse_args()

    if args.selftest:
        print("=== SELFTEST ===")
        sys.exit(0 if selftest() else 1)

    t = load(args.report)
    # ⚠ EXCLUDE null-dominated bands. At drive min / BLEND max the OD path SUBTRACTS at LF, so some
    # bands sit in a deep cancellation; there |g| is barely constrained and the band contributes a
    # huge, meaningless residual that the shared p then bends itself to fit. (64 Hz came back at
    # +24.7 dB before this guard.)
    NULLG = 0.15
    bands = [b for b in sorted(t) if FIT_LO_HZ <= b <= FIT_HI_HZ and min(t[b]) >= NULLG]
    dropped = [b for b in sorted(t) if FIT_LO_HZ <= b <= FIT_HI_HZ and min(t[b]) < NULLG]
    print("=== SET D -- b0 FROM THE LEVEL POT LAW (drive min, BLEND max) ===")
    print("  %d bands %.0f-%.0f Hz, 4 LEVEL positions, normalised at LEVEL noon."
          % (len(bands), bands[0], bands[-1]))
    if dropped:
        print("  dropped %d null-dominated band(s): %s"
              % (len(dropped), ", ".join("%.0f" % b for b in dropped)))
    print("  unknowns: complex g per band (%d) + ONE shared taper p  =>  over-determined by %d\n"
          % (2 * len(bands), len(bands) - 1))

    p_fit, gs, rms = solve_p(t, bands)
    b0 = bleed(0.5 ** p_fit)
    b0_mdl = AX.model_b0()
    print("  fitted LEVEL taper p = %.4f   (FitParams::levelTaperExp ships %.2f)"
          % (p_fit, AX.LEVEL_TAPER_EXP))
    print("  joint residual rms = %.4f (linear ratio units)" % rms)
    print("  => b0 = %.5f (%+.2f dB)   vs the model's %.5f (%+.2f dB)   DIFF %+.2f dB"
          % (b0, 20 * math.log10(b0), b0_mdl, 20 * math.log10(b0_mdl),
             20 * math.log10(b0 / b0_mdl)))

    print("\n  identifiability -- rms with p FIXED (a flat row means b0 is NOT measured):")
    for pp in (1.0, 1.5, 2.0, 2.25, 2.5, 3.0, 4.0):
        _, _, r = solve_p(t, bands, fix_p=pp)
        print("    p = %.2f -> b0 %.5f (%+.2f dB), rms %.5f%s"
              % (pp, bleed(0.5 ** pp), 20 * math.log10(bleed(0.5 ** pp)), r,
                 "   <- interior optimum" if abs(pp - p_fit) < 0.13 else ""))

    print("\n  per-band |g| = |Vod/Vclean| at drive min (the OD path where it is nearly linear):")
    for i, b in enumerate(bands):
        g = complex(gs[i, 0], gs[i, 1])
        print("    %5.0f Hz  |g| %+7.2f dB   arg %+7.1f deg" % (b, 20 * math.log10(abs(g)),
                                                                math.degrees(np.angle(g))))


if __name__ == "__main__":
    main()
