#!/usr/bin/env python3.11
"""A3 / ATTACK: what TRANSFER FUNCTION must a proposed ATTACK topology realise?

Session 57 established what the pedal's ATTACK does (a low-mid peak of ~+9 / -3 dB that the
drawn [ENG] ladder cannot make at any setting of any of its 11 elements) and left the live
question as "what topology to PROPOSE".  A proposal cannot be judged until the measurement is
turned into a SPECIFICATION: how many corners does the ratio need, where are they, and does it
need a resonance (a complex pole/zero pair) or only cascaded real ones?  That is what this tool
answers.  It does NOT propose or fit a circuit -- deliberately, because session 57's own
next-step (a) says "do not fit a new topology against the drive-noon target alone", and the
target here is still a describing-function ratio (sec SCOPE).

WHAT IT DOES
  1. Rebuilds the pedal's bleed-free ATTACK ratio LIVE from the captures (never transcribed),
     at every stimulus level, via attack_topology_probe.pedal_ratios.
  2. Fits minimum-phase rational families of increasing order to |ratio| per throw and reports
     where the residual reaches the floor -- the ORDER the data actually demands.
  3. Reports corner STABILITY ACROSS LEVEL.  A linear pre-clipper element has corners that do
     not move with stimulus level; a describing-function artefact's do.  This is the same test
     that made the ~30 Hz OD coupling corner credible in session 35 (fc = 30.3/31.4/28.4 Hz,
     +/-5%, across three levels) and it is the strongest evidence available short of the
     drive-min captures.

GUARDS (each has a specific failure it exists to catch)
  * SELF-TEST: every family must recover its own synthesised parameters to << the floor.  A
    family that cannot fit data it generated cannot be read as "this shape is unreachable".
  * DEGENERACY: a raised order that lands a zero on top of a pole has not found more structure,
    it has found none -- that is the signature that the data wants FEWER corners (session 35
    item 9).  Reported explicitly, never silently.
  * OFF-BAND: a corner outside the measured span is NOT identified by this data.  Reported as
    such rather than quoted as a value (the session-47 item-11 lesson: state identifiability).
  * FLOOR: the target is a ratio of two SOLVED quantities from the same instrument, so its
    floor is sqrt(2) x the 0.144 dB take-to-take floor = 0.204 dB, not 0.144 (session 56 sec 2).

SCOPE -- read before quoting any number here
  * The pedal side is a DESCRIBING-function ratio at drive noon.  sweep_clean (-30 dBFS) is the
    most linear condition in the matrix but is NOT the linear limit -- session 57 sec 2 showed
    the level trend has not plateaued there.  So the corner LOCATIONS are properties of the
    most-linear available measurement, and the overall GAIN k is a lower bound on the linear
    limit's gain, not the value of it.
  * ATTACK is [ENG].  There is no schematic to defer to and nothing corroborates any topology,
    which is exactly why the specification has to come from the measurement.
  * Magnitude only.  This axis measures |G|; it has no phase, so these are MINIMUM-PHASE fits.
    A non-minimum-phase realisation of the same magnitude exists and is not excluded.

Usage:  python3.11 analysis/attack_tf_spec.py [--selftest] [--quick]
"""
import argparse
import math
import os
import sys

import numpy as np
from scipy.optimize import differential_evolution, least_squares

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import attack_topology_probe as P        # noqa: E402  (rebuilds the target from captures)

TAKE_FLOOR_DB = 0.144                    # pedal take-to-take repeatability (session 24)
RATIO_FLOOR_DB = math.sqrt(2.0) * TAKE_FLOOR_DB   # ratio of two solved quantities
LEVELS = ["sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6"]
LEVEL_DBFS = {"sweep_clean": -30, "sweep_drv_-18": -18, "sweep_drv_-12": -12, "sweep_drv_-6": -6}
LINEAR_LEVEL = "sweep_clean"             # most linear condition in the matrix
OFFBAND_MARGIN = 3.0                     # a corner this far outside the span is not identified
DEGEN_RATIO = 1.25                       # a zero within this factor of a pole has cancelled


# ------------------------------------------------------------------ families
# Each family: (name, n_params, param names, builder taking (f, params) -> dB)
def _shelf(f, fz, fp):
    return 20.0 * np.log10(np.abs(1 + 1j * f / fz) / np.abs(1 + 1j * f / fp))


def _biquad(f, fz, Qz, fp, Qp):
    x, y = f / fz, f / fp
    num = np.abs(1 + 1j * x / Qz - x ** 2)
    den = np.abs(1 + 1j * y / Qp - y ** 2)
    return 20.0 * np.log10(num / den)


def fam_G(f, p):        # order 0 -- a pure frequency-flat gain (the null hypothesis)
    return np.full_like(f, p[0])


def fam_S1(f, p):       # order 1 -- one real zero + one real pole (a shelf)
    return p[0] + _shelf(f, 10 ** p[1], 10 ** p[2])


def fam_S2(f, p):       # order 2 -- two cascaded real shelves
    return p[0] + _shelf(f, 10 ** p[1], 10 ** p[2]) + _shelf(f, 10 ** p[3], 10 ** p[4])


def fam_R2(f, p):       # order 2 -- one complex zero pair + one complex pole pair (resonant)
    return p[0] + _biquad(f, 10 ** p[1], p[2], 10 ** p[3], p[4])


def fam_S1R2(f, p):     # order 3 -- a shelf on top of a resonance
    return p[0] + _shelf(f, 10 ** p[1], 10 ** p[2]) + _biquad(f, 10 ** p[3], p[4], 10 ** p[5], p[6])


FZ = (-0.3, 5.3)        # log10 Hz: 0.5 Hz .. 200 kHz -- wide enough that "off band" is visible
FQ = (0.2, 10.0)
FG = (-40.0, 40.0)
FAMILIES = [
    ("G     (order 0, flat gain)", fam_G,    [FG],                              ["k dB"]),
    ("S1    (order 1, shelf)",     fam_S1,   [FG, FZ, FZ],                      ["k dB", "fz", "fp"]),
    ("S2    (order 2, 2 shelves)", fam_S2,   [FG, FZ, FZ, FZ, FZ],              ["k dB", "fz1", "fp1", "fz2", "fp2"]),
    ("R2    (order 2, resonant)",  fam_R2,   [FG, FZ, FQ, FZ, FQ],              ["k dB", "fz", "Qz", "fp", "Qp"]),
    ("S1R2  (order 3)",            fam_S1R2, [FG, FZ, FZ, FZ, FQ, FZ, FQ],      ["k dB", "fz1", "fp1", "fz", "Qz", "fp", "Qp"]),
]


def fit(fn, box, f, tgt, quick, seed=1):
    """Global search + multi-start local refinement.

    DE alone is not enough here: at order 3 it converged to a 0.36 dB local minimum on a target
    the family had GENERATED, deterministically, at both budgets.  A family that cannot recover
    its own parameters makes a large residual on the real data unreadable, so the local restarts
    below are a correctness requirement, not a speed tweak.
    """
    lo = np.array([b[0] for b in box])
    hi = np.array([b[1] for b in box])

    def resid(p):
        try:
            r = fn(f, np.clip(p, lo, hi)) - tgt
        except (FloatingPointError, ValueError):
            return np.full_like(tgt, 1e3)
        return np.where(np.isfinite(r), r, 1e3)

    def cost(p):
        return math.sqrt(float(np.mean(resid(p) ** 2)))

    # ** DELIBERATELY SERIAL -- see the same note in attack_topology_probe.opt(). ** workers=-1
    # forces updating="deferred" and moves the search trajectory, and this tool's recorded result
    # is a SATURATION claim (boost saturates at 0.31-0.35 dB across rising orders, session 58)
    # that is only readable if the orders are comparable run-to-run. `cost` is also a closure, so
    # it is unpicklable, and the objective is cheap numpy -- there is no render in this loop.
    r = differential_evolution(cost, box, seed=seed, tol=1e-10, init='sobol',
                               maxiter=150 if quick else 500,
                               popsize=15 if quick else 30, polish=True)
    best_f, best_x = r.fun, r.x

    rng = np.random.default_rng(seed)
    starts = [r.x] + [lo + (hi - lo) * rng.random(len(box))
                      for _ in range(20 if quick else 60)]
    for x0 in starts:
        try:
            ls = least_squares(resid, np.clip(x0, lo, hi), bounds=(lo, hi),
                               xtol=1e-14, ftol=1e-14, gtol=1e-14, max_nfev=4000)
        except (ValueError, np.linalg.LinAlgError):
            continue
        c = cost(ls.x)
        if c < best_f:
            best_f, best_x = c, ls.x
    return best_f, best_x


def annotate(names, p, f_lo, f_hi):
    """Turn a parameter vector into readable text + the identifiability flags."""
    cells, flags = [], []
    corners = []
    for nm, v in zip(names, p):
        if nm.startswith("f"):
            hz = 10.0 ** v
            corners.append((nm, hz))
            tag = ""
            if hz < f_lo / OFFBAND_MARGIN or hz > f_hi * OFFBAND_MARGIN:
                tag = "!"
                flags.append("%s = %.3g Hz is OFF-BAND (not identified by this data)" % (nm, hz))
            cells.append("%s %.4g%s" % (nm, hz, tag))
        elif nm.startswith("Q"):
            cells.append("%s %.2f" % (nm, v))
        else:
            cells.append("%s %+.2f" % (nm, v))
    for i, (n1, h1) in enumerate(corners):
        for n2, h2 in corners[i + 1:]:
            if n1[1] != n2[1] and max(h1, h2) / max(min(h1, h2), 1e-12) < DEGEN_RATIO:
                flags.append("%s and %s coincide (%.3g / %.3g Hz) -- DEGENERATE, this order "
                             "adds nothing" % (n1, n2, h1, h2))
    return "  ".join(cells), flags


def selftest(quick):
    """Every family must recover a target it generated itself. Without this, a large residual
    is indistinguishable from a search that could not find the answer."""
    print("=== SELF-TEST: each family recovers its own synthesised parameters ===")
    f = np.array([80., 101., 127., 160., 202., 254., 403., 508., 640., 1613.])
    truths = {
        "G     (order 0, flat gain)": [6.0],
        "S1    (order 1, shelf)": [3.0, math.log10(120.0), math.log10(900.0)],
        "S2    (order 2, 2 shelves)": [2.0, math.log10(90.0), math.log10(400.0),
                                       math.log10(1500.0), math.log10(300.0)],
        "R2    (order 2, resonant)": [4.0, math.log10(600.0), 0.8, math.log10(180.0), 1.6],
        "S1R2  (order 3)": [1.0, math.log10(70.0), math.log10(250.0),
                            math.log10(900.0), 0.9, math.log10(200.0), 1.4],
    }
    ok = True
    for name, fn, box, names in FAMILIES:
        tp = truths[name]
        tgt = fn(f, tp)
        span = float(tgt.max() - tgt.min())
        rms, _ = fit(fn, box, f, tgt, quick)
        good = rms < 0.01
        ok &= good
        print("  %-28s span %5.2f dB -> recovered rms %.5f dB   %s"
              % (name, span, rms, "OK" if good else "FAIL"))
    print("  %s" % ("ALL FAMILIES RECOVER" if ok else
                    "GATE FAILS -- a poor fit below would measure the SEARCH, not the pedal"))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(0 if selftest(args.quick) else 1)
    gate_ok = selftest(args.quick)

    # ---- target, rebuilt live from the captures at every level -------------
    tgts = {}
    for lv in LEVELS:
        try:
            tgts[lv] = P.pedal_ratios(lv)
        except SystemExit:
            print("  (%s unavailable)" % lv)
    tgt0 = tgts[LINEAR_LEVEL]
    f = np.array(sorted(tgt0))
    f_lo, f_hi = f[0], f[-1]
    print("\n=== TARGET: pedal ATTACK ratio, bleed-free, %s (%d dBFS = most linear) ==="
          % (LINEAR_LEVEL, LEVEL_DBFS[LINEAR_LEVEL]))
    print("  %d bands identified in all three conditions, %.0f - %.0f Hz" % (len(f), f_lo, f_hi))
    print("  %6s %9s %9s" % ("f Hz", "boost dB", "cut dB"))
    for i, ff in enumerate(f):
        print("  %6.0f %+9.2f %+9.2f" % (ff, tgt0[ff][0], tgt0[ff][1]))

    # ---- how much order does each throw need? ------------------------------
    print("\n=== 1. WHAT ORDER DOES THE DATA DEMAND?  (floor %.3f dB = sqrt(2) x %.3f) ==="
          % (RATIO_FLOOR_DB, TAKE_FLOOR_DB))
    best = {}
    for throw, idx in (("BOOST", 0), ("CUT", 1)):
        t = np.array([tgt0[ff][idx] for ff in f])
        print("\n  --- %s ---" % throw)
        for name, fn, box, names in FAMILIES:
            rms, p = fit(fn, box, f, t, args.quick)
            txt, flags = annotate(names, p, f_lo, f_hi)
            verdict = "REACHES FLOOR" if rms <= RATIO_FLOOR_DB else ""
            print("    %-28s rms %6.3f dB  %-12s %s" % (name, rms, verdict, txt))
            for fl in flags:
                print("        ! %s" % fl)
            if throw not in best and rms <= RATIO_FLOOR_DB and not flags:
                best[throw] = (name, p, names, fn)
        if throw not in best:
            print("    (no family reaches the floor cleanly -- see flags above)")

    # ---- do the corners move with level? -----------------------------------
    print("\n=== 2. CORNER STABILITY ACROSS LEVEL ===")
    print("  A LINEAR pre-clipper element's corners do not move with stimulus level.")
    print("  Fitted with the family the linear-limit row selected, per throw.")
    for throw, idx in (("BOOST", 0), ("CUT", 1)):
        if throw not in best:
            print("\n  --- %s: no clean family selected, skipping ---" % throw)
            continue
        name, _, names, fn = best[throw]
        box = {x[0]: x[2] for x in FAMILIES}[name]
        print("\n  --- %s, family %s ---" % (throw, name.split()[0]))
        print("    %-16s %8s  %s" % ("level", "rms dB", "parameters"))
        for lv in LEVELS:
            if lv not in tgts:
                continue
            common = [ff for ff in f if ff in tgts[lv]]
            if len(common) < len(names) + 2:
                print("    %-16s (too few common bands)" % lv)
                continue
            fa = np.array(common)
            ta = np.array([tgts[lv][ff][idx] for ff in common])
            rms, p = fit(fn, box, fa, ta, args.quick)
            txt, _ = annotate(names, p, f_lo, f_hi)
            print("    %-16s %8.3f  %s" % ("%s (%d dBFS)" % (lv.replace("sweep_", ""),
                                                            LEVEL_DBFS[lv]), rms, txt))

    if not gate_ok:
        print("\n  THE SELF-TEST GATE DID NOT PASS -- the fits above measure the search, "
              "not the pedal.")


if __name__ == "__main__":
    main()
