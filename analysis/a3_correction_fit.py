#!/usr/bin/env python3.11
"""a3_correction_fit -- fit a POST-CLIPPER LINEAR CORRECTION NETWORK to A3's
MEASURED complex target (session 52, Phase 9 / A3 step 8).

WHY A NETWORK AND NOT A COMPONENT
---------------------------------
Session 50 closed the C2 carrier search space over every reachable element and
found it EMPTY, and showed that fixing any ONE component perfectly still leaves
3.5-4.8 dB of the 5.82 shape score. Session 51 then measured the pedal's own
OD-path transfer directly on the BLEND axis, so for the first time A3 has a
MEASURED COMPLEX TARGET rather than a target inverted out of the model's own
drive response. The remaining move is therefore not "which component" but "what
transfer function", fitted to whatever order the data demands -- the same move
that added `OdCoupling` in session 36, one order up. The user has authorised
departing from the schematic for this element.

THE TARGET
----------
    H_req(f) = G_ped(f) / G_mdl(f)

  * G_ped: the PEDAL's measured OD contribution, from `a3_blend_axis` (r and
    |theta| per band). Its magnitude is unambiguous; its PHASE SIGN is not --
    the blend-axis solve returns |theta| because a magnitude-only observation
    cannot see the sign (`unpack` uses acos).
  * G_mdl: the MODEL's EXACT phasor from `a3_blend_decompose`'s superposition
    taps -- no solve, and SIGNED. Used in preference to the blend axis's own
    solved model column, which agrees with it to 0.075 dB mean below 1.7 kHz
    (session 51's `--validate`) but carries solve error and a folded phase.

⭐ THE PHASE SIGN IS RESOLVED BY THE DATA, NOT ASSUMED -- and that resolution is
this tool's main claim to trustworthiness. A minimum-phase network's phase is
determined by its MAGNITUDE, and the magnitude has no sign ambiguity, so the two
branches are not equally realisable. Two tests, of unequal strength:

  (a) WEAK INDICATOR -- fit |H| ALONE (min-phase by construction: all zeros and
      poles in the left half plane) and compare the network's own phase against
      both branches. ⚠ This can only RANK them, because a magnitude-only fit over
      a handful of discrete bands can be phase-DEGENERATE: several
      (wz, Qz, wp, Qp) combinations pass through the same magnitude samples with
      different phase. (An earlier draft of `--selftest` measured 12.7 deg of that
      degeneracy on noise-free data -- but only because its synthetic target was
      not exactly representable; with the observation structure modelled properly
      it recovers the phase to 0.00 deg. Treat the size of the degeneracy as
      unknown per data set, hence "indicator".) Never read this row's absolute
      number as "how minimum-phase the target is".

  (b) THE DECISIVE TEST -- fit magnitude AND phase JOINTLY on each branch and
      compare. A min-phase cascade has no freedom left once both are in the cost,
      so if one branch is fitted to the capture floor in magnitude AND to a few
      degrees in phase while the other cannot be, the branch is SELECTED and --
      the stronger statement -- the required correction IS approximately
      minimum-phase, i.e. realisable by an ordinary causal network.

If NEITHER branch can be fitted jointly at any order, no causal correction can do
this and the search would have to move to a two-path cancellation (session 32's
question, left open because its Bode ceiling turned out to be an artefact of
unmeasured tails -- here the phase is MEASURED, so no ceiling is needed).

SCOPE AND ITS LIMITS
--------------------
  * Bands above **1700 Hz are NOT fitted**: `a3_blend_axis --validate` diverges
    there (+11.8 dB at 4064) because the swept-sine band average carries
    harmonic/aliasing power the single-tone tap does not.
  * ⚠ **Bands below 40 Hz are not fitted either, and that is the sharper limit.**
    Read PER BAND rather than as its recorded "mean 0.075 dB over 40-1700 Hz"
    summary, the same `--validate` says the solve is +2.77 dB and 20.0 deg wrong
    at 20 Hz, -0.96 dB / 13.9 deg at 32 Hz with theta RAILED at 180, against
    <=0.32 dB / <=2.7 deg at every band from 40 Hz to 1.6 kHz. That summary
    STARTS at 40 Hz, so it excluded the tool's own three worst bands -- which are
    exactly the ones carrying session 51's "C3 is the dominant A3 term" claim.
    See `--lo-hz`.
  * The shelf/biquad sections asymptote to 1 at HF, so for those families H(inf)
    is exactly k and the whole reach above the top corner is ONE number, printed
    as the predicted SIDE change for the 63-capture matrix to arbitrate. The
    `+TAIL` families deliberately break that (see FAMILIES) and their
    out-of-band lift is printed per family at 10 kHz.
  * **320 Hz is excluded**, as in every A3 tool: it is the TrebleAttack-notch
    band (GAP #2). The pedal's notch there is DEEPER relative to its neighbours
    than the model's, so a smooth correction cannot supply it and must not try.
  * This is a GRUNT-cut / BLEND-max / drive-noon / -18 dBFS measurement. It is a
    LINEAR element being fitted to a linear observation, but the element then
    lands in a chain whose upstream is nonlinear, so the gates that decide it are
    `a3_lead_fit` (the null, across five drives), `a3_shape_gate` (CORE + SIDE)
    and the full matrix -- never this tool's own residual.

RESULT (session 52): the target is NOT realisable. Magnitude alone fits to
0.103 dB; the magnitude-vs-phase Pareto frontier runs 0.23 dB @ 40.3 deg ...
5.66 dB @ 2.6 deg with nothing in between, and the measurement wants MORE LEAD
than the min-phase realisation of its own magnitude (~-38 deg flat over five
octaves). Since min-phase is the maximum-lead realisation, no causal linear
element of any order can supply it. Escapes closed: a delay mismatch (excluded --
the shortfall is flat, not proportional to f), the harmonic-power bias on theta
(needs impossible H/P at 8 of 15 bands), and a wrong bleed level (degenerate,
saturating, and independently excluded below -18.5 dB by session 34 item 2).
=> the difference is upstream of, or inside, the nonlinearity, where no Bode
relation applies. Full write-up: docs/phase9-validation.md §4 "A3 step 8".

Usage:
    python3.11 analysis/a3_correction_fit.py --selftest
    python3.11 analysis/a3_correction_fit.py [--sweep sweep_drv_-18] [--lo-hz 20]
"""
import argparse
import cmath
import math
import os
import sys

import numpy as np
from scipy.optimize import least_squares

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a3_blend_axis as ba                                        # noqa: E402

FIT_HI_HZ = 1700.0        # a3_blend_axis's own validity limit (session 51 item 4)
EXCLUDE = {320}           # GAP #2's TrebleAttack notch band
PHASE_W = 0.10            # dB per degree in the joint cost: 10 deg ~ 1 dB
TAKE_FLOOR_DB = 0.144

# Families, in increasing order. Each entry is (label, n_first_order, n_biquad,
# n_tail).
#
# The shelf and biquad sections are (s+wz)/(s+wp) and
# (s^2+(wz/Qz)s+wz^2)/(s^2+(wp/Qp)s+wp^2): both -> 1 as f -> inf, so a network
# built only from them has HF asymptote exactly k and its whole reach above the
# measured band is ONE number (session 49's lesson -- a gate whose domain is
# narrower than its candidate's reach cannot discriminate). All of them also have
# FINITE DC gain (z/p, wz^2/wp^2), so no family here can run away subsonically.
#
# ⚠ BUT a bounded-tail parameterisation cannot settle the MINIMUM-PHASE question,
# and assuming it can is exactly session 32's error. The phase a min-phase network
# has at 400 Hz is bought partly from its magnitude slope OUTSIDE the measured
# band; truncating the tail destroys lead the real element might legitimately
# have. So the `n_tail` sections are PURE ZEROS (1 + s/wz) with no matching pole:
# they rise 6 dB/oct for ever, buy unlimited lead, and are included precisely so
# that a failure to fit the phase cannot be blamed on a missing tail. Their price
# is an explicit out-of-band lift, printed at the SIDE bands, which the matrix
# then arbitrates -- the cost is visible instead of assumed away.
FAMILIES = [
    ("flat gain only (k)",                 0, 0, 0),
    ("k + 1 real shelf",                   1, 0, 0),
    ("k + 2 real shelves",                 2, 0, 0),
    ("k + 1 biquad",                       0, 1, 0),
    ("k + 1 shelf + 1 biquad",             1, 1, 0),
    ("k + 2 biquads",                      0, 2, 0),
    ("k + 1 shelf + 2 biquads",            1, 2, 0),
    ("k + 2 shelves + 2 biquads",          2, 2, 0),
    ("+TAIL: k + 1 shelf + 1 zero",        1, 0, 1),
    ("+TAIL: k + 1 biquad + 1 zero",       0, 1, 1),
    ("+TAIL: k + 1 shelf + 1 bq + 1 zero", 1, 1, 1),
    ("+TAIL: k + 1 shelf + 2 bq + 2 zero", 1, 2, 2),
]


# ---------------------------------------------------------------- response ----
def response(f, k, first, biquad, tail=()):
    """H(2.pi.i.f) for a cascade of shelf / biquad / pure-zero sections. The shelf
    and biquad sections -> 1 at HF; each `tail` zero rises 6 dB/oct for ever."""
    s = 2j * math.pi * np.asarray(f, dtype=float)
    h = np.full(s.shape, complex(k))
    for wz, wp in first:
        h = h * (s + wz) / (s + wp)
    for wz, qz, wp, qp in biquad:
        h = h * ((s * s + (wz / qz) * s + wz * wz) /
                 (s * s + (wp / qp) * s + wp * wp))
    for wz in tail:
        h = h * (1.0 + s / wz)
    return h


def unpack(v, nf, nb, nt=0):
    """Parameter vector -> (k, first[], biquad[], tail[]).  All frequencies/Qs are
    exp() of the free variable, so they are positive by construction => every
    zero and pole is in the LEFT half plane => the network is stable AND
    minimum-phase, which is exactly the hypothesis being tested."""
    i = 0
    k = math.exp(v[i]); i += 1
    first = []
    for _ in range(nf):
        wz = 2 * math.pi * math.exp(v[i]); i += 1
        wp = 2 * math.pi * math.exp(v[i]); i += 1
        first.append((wz, wp))
    biquad = []
    for _ in range(nb):
        wz = 2 * math.pi * math.exp(v[i]); i += 1
        qz = math.exp(v[i]); i += 1
        wp = 2 * math.pi * math.exp(v[i]); i += 1
        qp = math.exp(v[i]); i += 1
        biquad.append((wz, qz, wp, qp))
    tail = []
    for _ in range(nt):
        tail.append(2 * math.pi * math.exp(v[i])); i += 1
    return k, first, biquad, tail


def npar(nf, nb, nt=0):
    return 1 + 2 * nf + 4 * nb + nt


def bounds(nf, nb, nt=0):
    lo = [math.log(0.05)]
    hi = [math.log(20.0)]
    for _ in range(nf):
        lo += [math.log(1.0)] * 2
        hi += [math.log(2.0e4)] * 2
    for _ in range(nb):
        lo += [math.log(1.0), math.log(0.15), math.log(1.0), math.log(0.15)]
        hi += [math.log(2.0e4), math.log(12.0), math.log(2.0e4), math.log(12.0)]
    for _ in range(nt):
        lo += [math.log(100.0)]        # a tail zero below the band is a shelf, not a tail
        hi += [math.log(1.0e6)]
    return np.array(lo), np.array(hi)


def seed(rng, nf, nb, nt=0):
    v = [rng.uniform(math.log(0.5), math.log(4.0))]
    for _ in range(nf):
        v += [math.log(10 ** rng.uniform(1.0, 3.2)), math.log(10 ** rng.uniform(1.0, 3.2))]
    for _ in range(nb):
        v += [math.log(10 ** rng.uniform(1.3, 3.2)), math.log(10 ** rng.uniform(-0.3, 0.5)),
              math.log(10 ** rng.uniform(1.3, 3.2)), math.log(10 ** rng.uniform(-0.3, 0.5))]
    for _ in range(nt):
        v += [math.log(10 ** rng.uniform(2.5, 5.0))]
    return np.array(v)


def fit(f, mag_db, ph_deg, nf, nb, ntry=60, seed_n=7, w=None, nt=0):
    """Least-squares fit. `ph_deg` None => MAGNITUDE-ONLY (the min-phase test)."""
    rng = np.random.default_rng(seed_n)
    lo, hi = bounds(nf, nb, nt)
    F = np.asarray(f, dtype=float)
    W = np.ones(len(F)) if w is None else np.asarray(w, dtype=float)

    def resid(v):
        k, first, biquad, tail = unpack(v, nf, nb, nt)
        h = response(F, k, first, biquad, tail)
        e = list(W * (20.0 * np.log10(np.abs(h)) - mag_db))
        if ph_deg is not None:
            dphi = np.degrees(np.angle(h)) - ph_deg
            dphi = (dphi + 180.0) % 360.0 - 180.0
            e += list(W * PHASE_W * dphi)
        return np.asarray(e)

    best = (float("inf"), None)
    for _ in range(ntry):
        v0 = np.clip(seed(rng, nf, nb, nt), lo + 1e-9, hi - 1e-9)
        try:
            sol = least_squares(resid, v0, bounds=(lo, hi), xtol=1e-14, ftol=1e-14,
                                max_nfev=20000)
        except Exception:                                          # noqa: BLE001
            continue
        c = float(np.sqrt(np.mean(sol.fun ** 2)))
        if c < best[0]:
            best = (c, sol.x)
    return best


def describe(k, first, biquad, tail=()):
    out = ["k=%.4f (%+.2f dB)" % (k, 20 * math.log10(k))]
    for wz, wp in first:
        out.append("shelf: z %.1f Hz / p %.1f Hz" % (wz / 2 / math.pi, wp / 2 / math.pi))
    for wz, qz, wp, qp in biquad:
        out.append("biquad: z %.1f Hz Q%.2f / p %.1f Hz Q%.2f"
                   % (wz / 2 / math.pi, qz, wp / 2 / math.pi, qp))
    for wz in tail:
        out.append("TAIL zero: %.1f Hz (rises 6 dB/oct above it, unbounded)"
                   % (wz / 2 / math.pi))
    return "  |  ".join(out)


# ------------------------------------------------------------------ target ----
def wrap(x):
    return (x + math.pi) % (2 * math.pi) - math.pi


def load_target(sweep):
    """(bands, |H| dB, theta_ped_deg (unsigned), theta_mdl_deg (signed), r_ped, r_mdl).

    Model side from a3_blend_decompose's EXACT taps (signed phase, no solve);
    pedal side from a3_blend_axis's CSV (measured, phase magnitude only).
    """
    csv = "build/a3_blend_axis_%s.csv" % sweep
    if not os.path.exists(csv):
        sys.exit("missing %s -- run: python3.11 analysis/a3_blend_axis.py --sweep %s"
                 % (csv, sweep))
    dec = ba.load_decompose()
    if dec is None:
        sys.exit("missing %s" % ba.DECOMPOSE_CSV)

    rows = []
    for line in open(csv):
        if line.startswith("#") or not line.strip():
            continue
        p = line.strip().split(",")
        f, r_ped, th_ped, ident = float(p[0]), float(p[1]), float(p[2]), int(p[5])
        m = min(dec, key=lambda x: abs(x - f))
        if abs(m - f) > 0.03 * f:
            continue
        r_mdl, th_mdl = dec[m][0], math.degrees(wrap(dec[m][1]))
        rows.append(dict(f=f, r_ped=r_ped, r_mdl=r_mdl, th_ped=th_ped, th_mdl=th_mdl,
                         mag=20.0 * math.log10(r_ped / r_mdl), ident=bool(ident)))
    return rows


# ---------------------------------------------------------------- selftest ----
def selftest():
    """Synthesise the ACTUAL observation structure -- a known correction network on
    top of a known model phasor, with the pedal's phase then FOLDED the way
    `a3_blend_axis`'s acos folds it -- and confirm (1) exact recovery from the
    unfolded truth, (2) that the branch tests pick the right sign."""
    print("SELF-TEST: recover a known network through the real observation structure.\n")
    F = np.array([20, 25, 32, 40, 50, 64, 80, 101, 127, 160, 202, 254, 403, 508,
                  640, 806, 1016, 1613], dtype=float)
    tk, tf, tb = 1.90, [(2 * math.pi * 22.0, 2 * math.pi * 95.0)], \
        [(2 * math.pi * 700.0, 1.6, 2 * math.pi * 700.0, 4.0)]
    h = response(F, tk, tf, tb)
    mag, argH = 20 * np.log10(np.abs(h)), np.degrees(np.angle(h))

    # A smooth pedal phase kept inside (25, 155) deg, i.e. away from 0 and 180 --
    # the condition under which a per-band sign ambiguity collapses to ONE global
    # sign (see the GLOBAL SIGN note in main()). theta_mdl is then whatever makes
    # the arithmetic consistent, and is treated as exactly known, as it is in
    # practice (a3_blend_decompose's taps).
    th_ped = 90.0 + 40.0 * np.sin(2 * math.pi * np.log10(F / 20.0) / np.log10(1613 / 20.0))
    th_mdl = th_ped - argH
    brA = (+th_ped - th_mdl + 180) % 360 - 180        # == argH, the truth
    brB = (-th_ped - th_mdl + 180) % 360 - 180

    c, v = fit(F, mag, brA, 1, 1, ntry=40)
    k, f1, b1, t1 = unpack(v, 1, 1)
    hg = response(F, k, f1, b1, t1)
    dm = float(np.max(np.abs(20 * np.log10(np.abs(hg / h)))))
    dp = float(np.max(np.abs(np.degrees(np.angle(hg / h)))))
    print("  truth : %s" % describe(tk, tf, tb))
    print("  fitted: %s" % describe(k, f1, b1, t1))
    print("  worst |dH| %.5f dB / %.4f deg   (joint cost %.6f)" % (dm, dp, c))
    ok1 = dm < 0.02 and dp < 0.5

    # --- (a) the WEAK indicator: magnitude-only fit, its phase vs each branch
    cm, vm = fit(F, mag, None, 1, 1, ntry=40)
    fitted = np.degrees(np.angle(response(F, *unpack(vm, 1, 1))))
    a = float(np.sqrt(np.mean(((fitted - brA + 180) % 360 - 180) ** 2)))
    b = float(np.sqrt(np.mean(((fitted - brB + 180) % 360 - 180) ** 2)))
    print("\n  (a) WEAK indicator -- magnitude-only fit (mag rms %.4f dB), phase vs branch:"
          % cm)
    print("      +branch (true) %.2f deg   -branch %.2f deg   ratio %.1fx"
          % (a, b, b / max(a, 1e-9)))
    print("      %s"
          % ("no phase degeneracy on this (representable) target -- the magnitude alone "
             "pinned it." if a < 1.0 else
             "%.2f deg of that is the magnitude-only fit's own phase degeneracy, not a "
             "property of the target." % a))
    print("      Either way this test only RANKS the branches; it cannot certify min-phase.")
    ok2 = b > 3.0 * max(a, 1e-9)

    # --- (b) the DECISIVE test: joint magnitude+phase fit on each branch
    def joint(target):
        cc, vv = fit(F, mag, target, 1, 1, ntry=40)
        hh = response(F, *unpack(vv, 1, 1))
        m = float(np.sqrt(np.mean((20 * np.log10(np.abs(hh)) - mag) ** 2)))
        p = float(np.sqrt(np.mean(((np.degrees(np.angle(hh)) - target + 180) % 360 - 180) ** 2)))
        return cc, m, p

    ca, ma, pa = joint(brA)
    cb, mb, pb = joint(brB)
    print("\n  (b) DECISIVE -- joint magnitude+phase fit, per branch:")
    print("      +branch (true): mag %.4f dB   phase %.3f deg   cost %.4f" % (ma, pa, ca))
    print("      -branch       : mag %.4f dB   phase %.3f deg   cost %.4f" % (mb, pb, cb))
    print("      the true branch is fitted jointly to %.4f dB / %.3f deg; the wrong one"
          % (ma, pa))
    print("      cannot get below %.3f dB / %.1f deg => joint cost discriminates %.0fx."
          % (mb, pb, cb / max(ca, 1e-9)))
    ok3 = pa < 0.5 and cb > 10.0 * max(ca, 1e-9)
    print("\n  %s\n" % ("PASS" if (ok1 and ok2 and ok3) else "FAIL -- do not read a fit"))
    return ok1 and ok2 and ok3


# -------------------------------------------------------------------- main ----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", default="sweep_drv_-18")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--ntry", type=int, default=60)
    ap.add_argument("--lo-hz", type=float, default=40.0,
                    help="low edge of the FITTED band. Default 40 Hz, because that is "
                         "where a3_blend_axis's own --validate stops being trustworthy: "
                         "on the MODEL, where the exact answer is known, the solve is "
                         "+2.77 dB / 20 deg wrong at 20 Hz, -0.96 dB / 13.9 deg at 32 Hz "
                         "(and theta RAILS at 180 there), against <=0.32 dB / <=2 deg "
                         "everywhere from 40 Hz to 1.6 kHz. Pass 20 to include them and "
                         "see what they do to the fit.")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return

    rows = load_target(args.sweep)
    use = [r for r in rows if r["ident"] and args.lo_hz <= r["f"] <= FIT_HI_HZ
           and r["f"] not in EXCLUDE]
    dropped = [r["f"] for r in rows if r["ident"] and r["f"] < args.lo_hz]
    F = np.array([r["f"] for r in use])
    MAG = np.array([r["mag"] for r in use])
    THP = np.array([r["th_ped"] for r in use])       # unsigned (acos)
    THM = np.array([r["th_mdl"] for r in use])       # signed, exact

    print("A3 correction network -- fitted to the MEASURED complex OD-path target.")
    print("sweep=%s   fitted bands: %d (identified, %.0f-%.0f Hz, 320 Hz excluded)"
          % (args.sweep, len(use), args.lo_hz, FIT_HI_HZ))
    if dropped:
        print("⚠ EXCLUDED as UNRELIABLE, not as inconvenient: %s Hz."
              % ", ".join("%.0f" % f for f in dropped))
        print("  `a3_blend_axis --validate` solves the MODEL's own totals, where the exact")
        print("  answer is known from the superposition taps. Read PER BAND instead of as")
        print("  its 40-1700 Hz mean, it says: 20 Hz +2.77 dB / theta 20.0 deg wrong;")
        print("  25 Hz -0.16 dB / 16.5 deg; 32 Hz -0.96 dB / 13.9 deg AND theta RAILED at")
        print("  180.0; then <=0.32 dB and <=2.0 deg at every band from 40 Hz to 1.6 kHz.")
        print("  ⚠ The published summary starts at 40 Hz, so it EXCLUDES the tool's own")
        print("  three worst bands -- and those three are exactly the ones carrying")
        print("  session 51's 'C3 is the dominant A3 term' claim. Re-run with --lo-hz 20")
        print("  to see them fight the fit.\n")

    # ⚠ THE SIGN AMBIGUITY IS PER BAND, NOT GLOBAL -- acos() folds each band
    # independently, so strictly there are 2^N sign patterns, not 2. Treating it as
    # ONE global sign is an assumption, and it is only legitimate while theta_ped(f)
    # stays away from 0 and 180 deg: the sign of a continuous phase can only change
    # where it passes through one of those, so on any interval bounded away from
    # both, the sign is constant. That condition is CHECKED here rather than
    # assumed, and the check is reported -- if theta_ped ever approaches an
    # endpoint the two-branch treatment collapses and the fit below is meaningless.
    lo_ang = min(min(r["th_ped"], 180.0 - r["th_ped"]) for r in use)
    print("=== 1. THE TARGET  H_req = G_ped / G_mdl ===")
    print("  |H| is unambiguous. The phase has TWO branches because the blend-axis solve")
    print("  returns |theta_ped| only (acos); theta_mdl is exact and signed.")
    print("  ⚠ That fold is PER BAND, so strictly there are 2^%d sign patterns. Treating it"
          % len(use))
    print("  as ONE global sign is legitimate only while theta_ped stays clear of 0 and 180")
    print("  deg (a continuous phase can only change sign through one of those).")
    print("  CHECK: closest approach of theta_ped to either endpoint = %.1f deg at %.0f Hz"
          % (lo_ang, min(use, key=lambda r: min(r["th_ped"], 180 - r["th_ped"]))["f"]))
    print("  => %s" % ("OK, the global-sign treatment holds." if lo_ang > 20.0 else
                       "⚠ TOO CLOSE -- a sign flip is possible inside the band; do not "
                       "read the branch test as decisive."))
    print("%6s %9s %9s %9s %9s %9s %9s" % ("f", "r_ped dB", "r_mdl dB", "|H| dB",
                                           "th_mdl", "+branch", "-branch"))
    brA, brB = [], []
    for r in use:
        a = wrap(math.radians(+r["th_ped"] - r["th_mdl"]))
        b = wrap(math.radians(-r["th_ped"] - r["th_mdl"]))
        brA.append(math.degrees(a))
        brB.append(math.degrees(b))
        print("%6.0f %9.2f %9.2f %+9.2f %9.1f %+9.1f %+9.1f"
              % (r["f"], 20 * math.log10(r["r_ped"]), 20 * math.log10(r["r_mdl"]),
                 r["mag"], r["th_mdl"], brA[-1], brB[-1]))
    brA, brB = np.array(brA), np.array(brB)

    # ---- 2. the branch test -------------------------------------------------
    print("\n=== 2a. WEAK INDICATOR -- magnitude-only fit, its own phase vs each branch ===")
    print("  ⚠ RANKS the branches only: a magnitude-only fit over %d discrete bands can be"
          % len(F))
    print("  phase-degenerate, so its absolute phase error is not a property of the target.")
    print("%-30s %8s %11s %11s" % ("family", "mag rms", "+branch rms", "-branch rms"))
    for label, nf, nb, nt in FAMILIES:
        if npar(nf, nb, nt) > len(F) - 2:
            continue
        c, v = fit(F, MAG, None, nf, nb, ntry=args.ntry, nt=nt)
        fp = np.degrees(np.angle(response(F, *unpack(v, nf, nb, nt))))
        ea = float(np.sqrt(np.mean(((fp - brA + 180) % 360 - 180) ** 2)))
        eb = float(np.sqrt(np.mean(((fp - brB + 180) % 360 - 180) ** 2)))
        print("%-30s %8.3f %11.1f %11.1f" % (label, c, ea, eb))

    print("\n=== 2b. DECISIVE -- joint magnitude+phase fit on EACH branch ===")
    print("  A min-phase cascade has no freedom left once both magnitude and phase are in")
    print("  the cost. If one branch is fitted to the capture floor in magnitude AND to a")
    print("  few degrees in phase while the other cannot be, the branch is SELECTED by the")
    print("  data and the required correction IS approximately minimum-phase => realisable.")
    print("%-30s %5s   %-22s   %-22s" % ("family", "npar", "+branch (mag/phase)",
                                         "-branch (mag/phase)"))
    per_branch = []
    for label, nf, nb, nt in FAMILIES:
        if npar(nf, nb, nt) > 2 * len(F) - 2:
            continue
        row = {}
        for name, tgt in (("+", brA), ("-", brB)):
            c, v = fit(F, MAG, tgt, nf, nb, ntry=args.ntry, nt=nt)
            k, f1, b1, t1 = unpack(v, nf, nb, nt)
            h = response(F, k, f1, b1, t1)
            row[name] = dict(
                cost=c, v=v, k=k, first=f1, biquad=b1, tail=t1,
                mag=float(np.sqrt(np.mean((20 * np.log10(np.abs(h)) - MAG) ** 2))),
                ph=float(np.sqrt(np.mean(((np.degrees(np.angle(h)) - tgt + 180) % 360 - 180) ** 2))))
        row["label"], row["nf"], row["nb"], row["nt"] = label, nf, nb, nt
        per_branch.append(row)
        print("%-34s %5d   %8.3f dB / %6.1f deg   %8.3f dB / %6.1f deg"
              % (label, npar(nf, nb, nt), row["+"]["mag"], row["+"]["ph"],
                 row["-"]["mag"], row["-"]["ph"]))

    bestA = min(per_branch, key=lambda r: r["+"]["cost"])
    bestB = min(per_branch, key=lambda r: r["-"]["cost"])
    plus_wins = bestA["+"]["cost"] < bestB["-"]["cost"]
    sel = brA if plus_wins else brB
    win = bestA["+"] if plus_wins else bestB["-"]
    lose = bestB["-"] if plus_wins else bestA["+"]
    print("\n  best +branch: cost %.3f (%s)   best -branch: cost %.3f (%s)"
          % (bestA["+"]["cost"], bestA["label"], bestB["-"]["cost"], bestB["label"]))
    print("  => the data selects the %s branch, by %.1fx in joint cost."
          % ("+" if plus_wins else "-", lose["cost"] / max(win["cost"], 1e-9)))
    if win["mag"] <= 3 * TAKE_FLOOR_DB and win["ph"] < 12.0:
        print("  ✅ REALISABLE: the selected branch is fitted jointly to %.3f dB and %.1f deg"
              % (win["mag"], win["ph"]))
        print("  by a cascade of ordinary LHP sections => the required correction is")
        print("  approximately MINIMUM-PHASE. First time A3's realisability has been tested")
        print("  against a MEASURED phase instead of an inferred one (session 32's Bode")
        print("  ceiling was decided by unmeasured tails; nothing here extrapolates).")
    else:
        print("  ⚠ NEITHER branch is fitted jointly (best %.3f dB / %.1f deg). Either the"
              % (win["mag"], win["ph"]))
        print("  phase measurement is untrustworthy at these bands, or the correction is")
        print("  NON-minimum-phase (a two-path cancellation), which no cascade of ordinary")
        print("  sections can supply. Do NOT ship a network from section 3 without")
        print("  resolving this -- the magnitude alone would then be a coincidence.")

    # ---- 2c. the PARETO FRONTIER: magnitude vs phase -----------------------
    # A single joint-cost number cannot say "unrealisable" -- it depends on the
    # weighting. The honest statement is the TRADE-OFF: how much magnitude error
    # must be accepted to reach a given phase error. Same form as session 49's
    # bridged-T Pareto scan, which is what turned "this element is insufficient"
    # into "no setting of this element can separate the two effects".
    print("\n=== 2c. PARETO FRONTIER -- magnitude error vs phase error (selected branch) ===")
    print("  Richest family (%s), which INCLUDES unbounded" % FAMILIES[-1][0])
    print("  rising tails, so a shortfall here cannot be blamed on a truncated tail.")
    print("  %10s %10s %10s" % ("phase wt", "mag rms", "ph rms"))
    nf_t, nb_t, nt_t = FAMILIES[-1][1], FAMILIES[-1][2], FAMILIES[-1][3]
    global PHASE_W
    saved_w, frontier = PHASE_W, []
    for wt in (0.0, 0.02, 0.05, 0.1, 0.3, 1.0, 3.0):
        PHASE_W = wt
        _, vv = fit(F, MAG, sel, nf_t, nb_t, ntry=max(12, args.ntry // 2), nt=nt_t)
        hh = response(F, *unpack(vv, nf_t, nb_t, nt_t))
        m = float(np.sqrt(np.mean((20 * np.log10(np.abs(hh)) - MAG) ** 2)))
        pp = float(np.sqrt(np.mean(((np.degrees(np.angle(hh)) - sel + 180) % 360 - 180) ** 2)))
        frontier.append((wt, m, pp))
        print("  %10.2f %10.3f %10.1f" % (wt, m, pp))
    PHASE_W = saved_w
    best_m = min(f[1] for f in frontier)
    best_p = min(f[2] for f in frontier)
    print("  best magnitude anywhere on the frontier: %.3f dB" % best_m)
    print("  best phase     anywhere on the frontier: %.1f deg" % best_p)
    print("\n  ⭐ READ THIS AS THE RESULT. Minimum phase is the MAXIMUM-LEAD realisation of")
    print("  a given magnitude (any other causal realisation is min-phase x an all-pass,")
    print("  and an all-pass only ADDS lag). So if the measured phase cannot be reached by")
    print("  a min-phase cascade that also matches the magnitude, NO causal linear element")
    print("  of ANY order can supply this target -- which is a stronger statement than")
    print("  session 50's reachability result (that ruled out the elements the model")
    print("  contains; this rules out the whole CLASS).")

    # ---- 2d. could the phase measurement's own BIAS explain the shortfall? --
    # It has one, and it was never quoted: from the law's own algebra the quadratic
    # returns k1 = 2(Re(g1) - c) and k2 = |g1|^2 + H - 2c.Re(g1) + c^2, where H is
    # the OD path's HARMONIC power in the band. So `unpack` reports
    # r = sqrt(|g1|^2 + H) -- INFLATED -- while Q = Re(g1) is exact and
    # harmonic-free. cos(theta) = Q/r is therefore biased TOWARDS 90 deg, and
    # r is an UPPER BOUND on the fundamental. (a3_blend_axis's docstring notes P
    # "absorbs the harmonic power" and then reports r as |G| and theta from it.)
    # Direction matters: correcting the bias moves theta AWAY from 90 deg, which
    # REDUCES the required lead over 127-640 Hz -- exactly where the shortfall is
    # worst. So it is a live alternative explanation and has to be sized, not
    # waved off. The size is the implied THD: if the min-phase fit's phase is
    # right, the needed inflation is r/|g1| = cos(theta_fit_implied)/cos(theta_meas)
    # and the implied harmonic-to-fundamental POWER ratio is (r/|g1|)^2 - 1.
    print("\n=== 2d. CAN THE PHASE MEASUREMENT'S KNOWN BIAS EXPLAIN THE SHORTFALL? ===")
    print("  The blend-axis quadratic gives Q = Re(g1) EXACTLY but r = sqrt(|g1|^2 + H)")
    print("  with H the band's harmonic power, so cos(theta) = Q/r is biased TOWARDS 90 deg")
    print("  and r is an UPPER BOUND on the fundamental. Correcting it moves theta away")
    print("  from 90 deg, which REDUCES the required lead over 127-640 Hz -- so it is a")
    print("  live explanation. Sizing it as the implied harmonic-to-fundamental power:")
    cm2, vm2 = fit(F, MAG, None, nf_t, nb_t, ntry=max(12, args.ntry // 2), nt=nt_t)
    ph_mp = np.degrees(np.angle(response(F, *unpack(vm2, nf_t, nb_t, nt_t))))
    print("  %6s %9s %9s %9s %12s" % ("f", "th_ped", "th needed", "d deg", "implied H/P"))
    worst_hp = 0.0
    for i, r in enumerate(use):
        th_need = r["th_mdl"] + ph_mp[i]          # theta_ped implied by the min-phase fit
        ca, cb2 = math.cos(math.radians(th_need)), math.cos(math.radians(r["th_ped"]))
        if abs(cb2) < 1e-6 or ca * cb2 <= 0:
            hp = float("inf")                    # needs a SIGN change, not an inflation
        else:
            ratio = ca / cb2
            hp = ratio * ratio - 1.0 if ratio >= 1.0 else -1.0   # <1 => needs DEFLATION
        worst_hp = max(worst_hp, hp if np.isfinite(hp) else 1e9)
        print("  %6.0f %9.1f %9.1f %+9.1f %12s"
              % (r["f"], r["th_ped"], th_need, th_need - r["th_ped"],
                 ("sign flip" if not np.isfinite(hp) else
                  "impossible" if hp < 0 else "%.1f" % hp)))
    print("\n  'implied H/P' is the harmonic-to-fundamental POWER ratio the bias would need")
    print("  in order to reconcile the measurement with the min-phase fit. H/P = 0.1 is")
    print("  ~32%% THD; H/P = 1 is more harmonic power than fundamental. 'impossible' means")
    print("  the bias would have to act in the WRONG DIRECTION (deflate r), which harmonic")
    print("  power cannot do; 'sign flip' means no inflation of any size suffices.")
    # ⭐ AND EXCLUDE THE BORING BUG WHILE WE ARE HERE. The most mundane explanation
    # for "the pedal's OD leads the model's" is a residual DELAY on the model's OD
    # path -- e.g. an oversampling FIR latency compensated to the nearest whole base
    # sample, leaving a fractional-sample mismatch (dsp.md's own standing warning
    # about the BLEND summing node). A delay is trivially distinguishable: its phase
    # error grows LINEARLY with frequency, so over the 40 Hz - 1.6 kHz span (a factor
    # of 40) it cannot look flat.
    short = np.array([ (r["th_mdl"] + ph_mp[i]) - r["th_ped"] for i, r in enumerate(use) ])
    tau = float(np.sum(short * F) / np.sum(F * F) / 360.0)      # LS delay, seconds
    dl_res = float(np.sqrt(np.mean((short - 360.0 * tau * F) ** 2)))
    fl_res = float(np.sqrt(np.mean((short - np.mean(short)) ** 2)))
    print("\n  DELAY CHECK: best-fit pure delay %+.3f ms leaves %.1f deg rms; a FLAT offset"
          % (tau * 1e3, dl_res))
    print("  of %+.1f deg leaves %.1f deg rms. Shortfall span %.1f to %.1f deg over a 40x"
          % (float(np.mean(short)), fl_res, float(short.min()), float(short.max())))
    print("  frequency range => %s"
          % ("FLAT, not proportional to f: a delay-compensation mismatch on the OD path "
             "is\n     EXCLUDED as the cause." if fl_res < dl_res else
             "consistent with a DELAY -- chase the OD path's latency compensation first."))

    print("  => %s" % ("the bias CANNOT explain the shortfall at the bands that carry it."
                       if worst_hp > 2.0 else
                       "⚠ the required H/P is small enough to be REAL -- the phase target "
                       "must be corrected for harmonic power before any conclusion."))

    # ---- 2e. FREE THE BLEED LEVEL: causality breaks the b0 degeneracy -------
    # a3_blend_axis is degenerate in b0 BAND BY BAND: three unknowns (c, P, Q) map
    # onto two quadratic coefficients, so it fixes b0 from the model and states it
    # cannot challenge beta. That is true one band at a time -- but NOT across
    # bands once the correction is required to be CAUSAL, because b0 enters
    # Q = k1/2 + (1-b0) identically at every band while a min-phase network's phase
    # is tied to its own magnitude. One scalar against 2 x 15 equations.
    #
    # ⭐ And the shortfall's SHAPE is what suggests it: 2d's 'd deg' column is a
    # near-constant ~-40 deg from 40 Hz to 1.6 kHz, five octaves. No causal filter
    # and no delay does that; a single wrong scalar in Q does exactly that.
    #
    # The (k1, k2) pair is recovered exactly from the published (r, theta) and the
    # b0 they were written at, then re-unpacked at each trial b0 -- so this is a
    # re-solve of the SAME measurement, not a new one.
    print("\n=== 2e. FREE THE BLEED LEVEL -- does causality identify b0? ===")
    b0_csv = ba.model_b0()
    c0 = 1.0 - b0_csv
    kk = []
    for r in use:
        Q = r["r_ped"] * math.cos(math.radians(r["th_ped"]))
        P = r["r_ped"] ** 2
        kk.append((2.0 * (Q - c0), P - c0 * (2.0 * (Q - c0)) - c0 * c0))

    def retarget(b0):
        """(mag_db, phase_deg_+branch, ok) for the whole band set at a trial b0."""
        c = 1.0 - b0
        mag, ph, ok = [], [], True
        for (k1, k2), r in zip(kk, use):
            Q = k1 / 2.0 + c
            P = k2 + c * k1 + c * c
            if P <= 0:
                return None, None, False
            rp = math.sqrt(P)
            cs = Q / rp
            if abs(cs) > 1.0:
                ok = False                      # infeasible: |cos| > 1 at this b0
                cs = max(-1.0, min(1.0, cs))
            mag.append(20.0 * math.log10(rp / r["r_mdl"]))
            ph.append(math.degrees(wrap(math.acos(cs) * (1.0 if plus_wins else -1.0)
                                        - math.radians(r["th_mdl"]))))
        return np.array(mag), np.array(ph), ok

    nf_s, nb_s, nt_s = 1, 1, 0                  # one mid-order family for the scan
    print("  scan: one family (k + 1 shelf + 1 biquad, %d par) at each trial beta."
          % npar(nf_s, nb_s, nt_s))
    print("  %8s %8s %10s %10s %8s" % ("beta dB", "b0", "mag rms", "ph rms", "feasible"))
    scan = []
    for beta_db in list(np.arange(-45.0, -11.9, 3.0)) + [-18.5, -17.25, -16.75, -16.5]:
        b0 = 10.0 ** (beta_db / 20.0)
        m, ph2, ok = retarget(b0)
        if m is None:
            print("  %8.1f %8.4f %10s %10s %8s" % (beta_db, b0, "-", "-", "P<=0"))
            continue
        c2, v2 = fit(F, m, ph2, nf_s, nb_s, ntry=max(8, args.ntry // 2), nt=nt_s)
        hh = response(F, *unpack(v2, nf_s, nb_s, nt_s))
        mr = float(np.sqrt(np.mean((20 * np.log10(np.abs(hh)) - m) ** 2)))
        pr = float(np.sqrt(np.mean(((np.degrees(np.angle(hh)) - ph2 + 180) % 360 - 180) ** 2)))
        scan.append((beta_db, mr, pr, c2, ok))
        print("  %8.1f %8.4f %10.3f %10.1f %8s"
              % (beta_db, b0, mr, pr, "Y" if ok else "n"))
    if scan:
        scan.sort()
        best = min(scan, key=lambda x: x[3])
        lo_edge, hi_edge = scan[0][0], scan[-1][0]
        interior = lo_edge < best[0] < hi_edge
        print("\n  best joint cost at beta = %+.2f dB (mag %.3f dB, phase %.1f deg)"
              % (best[0], best[1], best[2]))
        print("  optimum is %s"
              % ("INTERIOR to the scan" if interior else
                 "⚠ ON THE SCAN EDGE (%+.1f dB) -- a bound-resting optimum is not an "
                 "identification (the session-50 rule)" % best[0]))
        # As b0 -> 0 the target CONVERGES (c -> 1, so Q -> k1/2 + 1 and P -> k2+k1+1),
        # so a monotone improvement toward low beta must SATURATE. Saturating without
        # an interior minimum is the signature of a degeneracy, not a measurement.
        tail_span = max(x[3] for x in scan[:3]) - min(x[3] for x in scan[:3])
        print("  cost spread over the three LOWEST beta points: %.4f" % tail_span)
        print("  => %s" % ("SATURATED. As b0 -> 0 the target converges (c -> 1), so this "
                           "direction\n     is a DEGENERACY, not an identification: the fit "
                           "improves toward a limit\n     and never reaches realisability."
                           if tail_span < 0.15 else
                           "still moving -- widen the scan further before concluding."))
        # ⭐ AND THE ADMISSIBLE WINDOW IS SET FROM OUTSIDE THIS TOOL.
        # session 34 item 2 REFUTED beta <= -18.5 dB from magnitudes alone (below the
        # pedal's own drive-min total no monotone |OD| ladder exists at any theta);
        # session 50 puts it at -16.75 in [-17.25, -16.50]; and LevelBlend's own
        # resistor arithmetic gives -16.93 at the measured LEVEL taper. So the low-beta
        # region this scan drifts into is independently excluded.
        adm = [x for x in scan if -18.5 <= x[0] <= -16.5]
        if adm:
            ba_ = min(adm, key=lambda x: x[3])
            print("\n  WITHIN the independently ADMISSIBLE window beta in [-18.5, -16.5]")
            print("  (session 34 item 2 refutes beta <= -18.5 from magnitudes alone; session")
            print("  50 measures -16.75 [-17.25, -16.50]; LevelBlend's resistor arithmetic")
            print("  gives -16.93): best is beta %+.2f dB at mag %.3f dB / phase %.1f deg."
                  % (ba_[0], ba_[1], ba_[2]))
            print("  ⇒ the bleed level CANNOT rescue realisability: inside the admissible")
            print("  window the fit is still %.1f deg out, and the direction that would help"
                  % ba_[2])
            print("  is both degenerate AND excluded from outside.")

    # ---- 3. the joint complex fit -------------------------------------------
    print("\n=== 3. JOINT COMPLEX FIT on the selected branch (phase weighted %.2f dB/deg) ==="
          % PHASE_W)
    print("%-34s %5s %8s %9s %9s %9s %9s"
          % ("family", "npar", "cost", "mag rms", "ph rms", "k dB", "10kHz dB"))
    fits = []
    for label, nf, nb, nt in FAMILIES:
        if npar(nf, nb, nt) > 2 * len(F) - 2:
            continue
        c, v = fit(F, MAG, sel, nf, nb, ntry=args.ntry, nt=nt)
        k, f1, b1, t1 = unpack(v, nf, nb, nt)
        h = response(F, k, f1, b1, t1)
        mr = float(np.sqrt(np.mean((20 * np.log10(np.abs(h)) - MAG) ** 2)))
        pr = float(np.sqrt(np.mean(((np.degrees(np.angle(h)) - sel + 180) % 360 - 180) ** 2)))
        fits.append(dict(label=label, nf=nf, nb=nb, nt=nt, cost=c, mag=mr, ph=pr,
                         v=v, k=k, first=f1, biquad=b1, tail=t1))
        hf = 20 * math.log10(abs(response([10000.0], k, f1, b1, t1)[0]))
        print("%-34s %5d %8.3f %9.3f %9.1f %+9.2f %+9.2f"
              % (label, npar(nf, nb, nt), c, mr, pr, 20 * math.log10(k), hf))

    print("\n  Order selection: take the SIMPLEST family whose magnitude residual is at")
    print("  the capture floor (%.3f dB); extra sections beyond that are fitting noise."
          % TAKE_FLOOR_DB)
    for r in fits:
        print("    %-30s mag %.3f dB %s" % (r["label"], r["mag"],
              "<= floor" if r["mag"] <= TAKE_FLOOR_DB else ""))

    at_floor = [r for r in fits if r["mag"] <= TAKE_FLOOR_DB]
    chosen = at_floor[0] if at_floor else min(fits, key=lambda r: r["cost"])
    if at_floor:
        print("\n  CHOSEN: %s" % chosen["label"])
    else:
        print("\n  ⛔ NO FAMILY REACHES THE CAPTURE FLOOR IN MAGNITUDE while matching the")
        print("  phase (best %.3f dB at %s). The row below is the" % (chosen["mag"], chosen["label"]))
        print("  lowest-JOINT-COST fit and is printed for diagnosis ONLY -- it is NOT a")
        print("  candidate and must not be shipped. Read section 2c's frontier instead.")
    print("    %s" % describe(chosen["k"], chosen["first"], chosen["biquad"],
                              chosen["tail"]))

    h = response(F, chosen["k"], chosen["first"], chosen["biquad"])
    print("\n%6s %9s %9s %9s %9s %9s %9s" % ("f", "|H| tgt", "|H| fit", "d dB",
                                             "ph tgt", "ph fit", "d deg"))
    for i, r in enumerate(use):
        dp = (math.degrees(np.angle(h[i])) - sel[i] + 180) % 360 - 180
        print("%6.0f %+9.2f %+9.2f %+9.2f %+9.1f %+9.1f %+9.1f"
              % (r["f"], MAG[i], 20 * math.log10(abs(h[i])), 20 * math.log10(abs(h[i])) - MAG[i],
                 sel[i], math.degrees(np.angle(h[i])), dp))

    # ---- 4. what the network does OUTSIDE the fitted band -------------------
    print("\n=== 4. REACH OUTSIDE THE FITTED BAND (the session-49 check) ===")
    print("  Every section -> 1 at HF, so above the highest corner the network is exactly")
    print("  the flat gain k. Predicted SIDE-monitor change and DC behaviour:")
    hi = np.array([1016.0, 1613.0, 2560.0, 4064.0, 6451.0, 10240.0, 16000.0])
    hh = response(hi, chosen["k"], chosen["first"], chosen["biquad"])
    print("    " + "  ".join("%.0f:%+.2f" % (f, 20 * math.log10(abs(v)))
                             for f, v in zip(hi, hh)))
    lo = np.array([5.0, 10.0, 20.0])
    hl = response(lo, chosen["k"], chosen["first"], chosen["biquad"])
    print("    " + "  ".join("%.0f:%+.2f" % (f, 20 * math.log10(abs(v)))
                             for f, v in zip(lo, hl)))
    print("  ⚠ The LF numbers below 20 Hz are EXTRAPOLATION -- no capture measures them.")
    print("  A section whose gain keeps climbing below the measurement floor is a")
    print("  subsonic-headroom risk in the plugin even if it is invisible in the matrix.")

    # ---- 5. the FitParams line ---------------------------------------------
    print("\n=== 5. IMPLEMENTATION (post-clipper, OS rate, after OdCoupling) ===")
    args_list = ["odCorrEnabled=1", "odCorrK=%.6g" % chosen["k"]]
    for i, (wz, wp) in enumerate(chosen["first"][:1]):
        args_list += ["odCorrShelfZ=%.6g" % (wz / 2 / math.pi),
                      "odCorrShelfP=%.6g" % (wp / 2 / math.pi)]
    for i, (wz, qz, wp, qp) in enumerate(chosen["biquad"][:2]):
        n = i + 1
        args_list += ["odCorrZ%df=%.6g" % (n, wz / 2 / math.pi),
                      "odCorrZ%dq=%.6g" % (n, qz),
                      "odCorrP%df=%.6g" % (n, wp / 2 / math.pi),
                      "odCorrP%dq=%.6g" % (n, qp)]
    print("  " + " ".join("--fit " + a for a in args_list))

    out = "build/a3_correction_target_%s.csv" % args.sweep
    with open(out, "w") as fh:
        fh.write("# A3 correction target: H_req = G_ped/G_mdl. branch=%s\n"
                 "# f,mag_db,phase_deg,fit_mag_db,fit_phase_deg,identified\n"
                 % ("+" if plus_wins else "-"))
        for i, r in enumerate(use):
            fh.write("%.0f,%.4f,%.3f,%.4f,%.3f,1\n"
                     % (r["f"], MAG[i], sel[i], 20 * math.log10(abs(h[i])),
                        math.degrees(np.angle(h[i]))))
    print("\n  wrote %s" % out)


if __name__ == "__main__":
    main()
