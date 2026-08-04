#!/usr/bin/env python3.11
"""GATE AL — THE DEFICIT'S FREQUENCY EXPONENT, AUDITED ON A 14x FINER SURFACE, WITH A REAL n;
            AND WHAT CLASS OF STRUCTURE CAN PRODUCE WHATEVER IT TURNS OUT TO BE.

WHY THIS EXISTS (session 141, executing session 140's `NEXT` #2 before its #1).

Session 139 introduced the sharpest screen open work item 6 has:

    for a single real pole whose corner moves, d ln|dT| / d ln f = 2/(1+u) <= 2 EXACTLY, for
    every pole frequency and every f.  The deficit steepens as f^2.84.  => the whole "a
    capacitance grows with drive" class is refuted on SHAPE, at any size, with no threshold.

Session 140 (AK3b) then leaned on the same exponent a second time, and added a POSITIVE
specification built on it (*"the carrier's own frequency dependence must RISE near the vertex"*).
Three conclusions now rest on one number -- and that number is a regression through **three**
points (AG4's uncontaminated centres, 1612.7 / 2031.9 / 2560.0 Hz), which s140 flagged in as many
words:

    "⚠ The exponent is still n = 3 centres.  Both AJ2c and now AK3b rest on it, so it is carrying
     more weight each session.  Widening it needs a finer surface, not a wider window."

⇒ **This gate makes that measurement.**  It is the premise audit, not another candidate screen.
It can INVALIDATE two whole-class refutations, which is worth more than adding a third.

⚠⚠ WHY THE PREMISE AND NOT THE NEXT CANDIDATE.  `measurement-discipline.md` §1 carries EIGHT
occurrences of `verify-the-PREMISE-not-the-prior-session's-framing-of-it`, and the shape here is
the textbook one: a number measured once, for one purpose, quoted forward by later sessions for
purposes it was never sized for, each of which strengthens the appearance that it is settled.  If
f^2.84 is an artefact of three points on a coarse grid, then AJ2c refuted the largest candidate
class in the project wrongly, and item 6's search space is much bigger than the handover says.

THE INSTRUMENT, and why it is not a new one.  AG4 reads slopes off GATE Q's **1/3-octave band**
surface, so a +-0.5 oct window holds 3 bands and only three centres have a window wholly inside
GATE W's feature-free band (1000-4200 Hz).  That is a property of the GRID, not of the physics.
GATE AH already built the finer instrument for a different question and CROSS-VALIDATED it against
AG at this very feature (AH6: P-M drive-tilt -2.290 here against AG5's -2.038, same sign,
difference <= 1/2|AG5| => "CORROBORATED ... safe at this feature").  So this gate imports AH's
loader and AH's estimator verbatim rather than writing a third one:

    * surface : GATE W's 1/48-oct smoothed `transfer_h1` (462 points), GATE W's own renders
    * estimator: AH.tilt_at -- the linear coefficient of a quadratic in log2(f/f0), i.e. AG's
    * captures : GATE Q's pure-OD endpoints, ex `gain-n12` -- AH's own membership

At the primary half-width (1/12 oct, AH's own PRIMARY, imported not chosen) a fit window holds 9
points and **12 NON-OVERLAPPING centres** fit inside the feature-free band, against AG4's 3.

⚠⚠ THE n THAT IS QUOTED IS THE INDEPENDENT ONE.  A dense scan over every grid cell gives ~131
centres whose windows overlap almost completely; that is one curve sampled finely, NOT 131
measurements, and quoting it as an n would be a worse error than the n=3 this gate exists to fix.
AL4 reports the dense curve for SHAPE and takes every verdict from the non-overlapping set.

GATES (validity exits non-zero; every physics OUTCOME is a computed verdict and execution
continues -- s108's rule)
------------------------------------------------------------------------------------------------
AL1  KNOWN ANSWERS  (a) the estimator recovers an INJECTED TILT exactly, swept including ZERO
                        (the arm's own mutation control).
                    (b) ⭐ the estimator recovers an INJECTED KNOWN EXPONENT.  This is the
                        decision-relevant arm and it is the reason this gate can be believed: it
                        is not enough that the estimator works, it must be shown to DISCRIMINATE
                        p = 2.000 (the class bound) from p = 2.84 (the measurement).  An estimator
                        that returned 2.84 for an injected 2.0 would have manufactured AJ2c.
                    (c) the class bound itself, recomputed by FINITE DIFFERENCE over the same
                        spacing the measurement uses -- sharing no algebra with AJ2c's analytic
                        2/(1+u).  It must come back 2.000.
AL2  MEMBERSHIP     three-outcome (s129), imported from AH; and WINDOW CONTAINMENT asserted for
                    every centre against GATE W's own feature bounds BEFORE any exponent is read.
AL3  THE OPERANDS   s117: a deficit is a difference, so print the MODEL's and the PEDAL's own
                    drive-tilt per centre, and scan for a SIGN CHANGE -- log|D| is not defined
                    across one, and a power law through a zero crossing has a divergent local
                    exponent (which is exactly how a coarse grid manufactures a large one).
AL4  THE EXPONENT   the headline.  Non-overlapping centres, half-width swept, fitted on the
                    monotone limb (COMPUTED, not chosen).  ⚠ The gated statistic is the
                    ENDPOINT-to-endpoint exponent, not AJ2c's weakest adjacent pair -- integrating
                    the pointwise bound `<= 2` gives `endpoint exponent <= 2` EXACTLY for the whole
                    class, so the endpoint reading is what the bound implies, needs no fit, and
                    cannot be rescued by a favourable interior.  The per-pair column is printed
                    beside it because AJ2c's PHRASING ("every adjacent pair") is what fails here,
                    separately from its conclusion.  Cross-checked against AG4's stored n=3 value,
                    imported not transcribed.
AL5  THE CLASS      what structure CAN produce the measured exponent.  Real pole: 2.000 (AL1c).
                    Complex pole pair (Q-change and f0-move) evaluated at the SHIPPED Sallen-Key
                    operating points, and the admissible f0 band derived.  A positive
                    specification, which is what s140 `NEXT` #1(c) asked for.
AL6  VERDICT        computed, with a machine-checkable membership line (s130).

WHAT THIS DOES **NOT** CLAIM
  * It does not identify a mechanism, and AL5 is a SHAPE screen only -- admissible in shape is
    necessary, never sufficient (s140 AK5 is the standing example: a carrier can pass every sign
    and shape gate and still die on size).
  * It says nothing about hardware.  Both sides are the ND captures (`reference-sources.md` §0).
  * AL5's Sallen-Key arithmetic is a MECHANISM SIZE on the shipped linear cascade, not a priced
    render (AC's own caveat, inherited).

Usage:
  python3.11 analysis/deficit_exponent_gate.py
  python3.11 analysis/deficit_exponent_gate.py --json analysis/reports/s141_deficit_exponent.json
"""
import argparse
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import feature_locus_gate as W          # noqa: E402  the grid, the windows, the renders
import matrix_grade as MG               # noqa: E402
import null_locus_gate as R             # noqa: E402  EXPECT_ENDPOINTS -- ONE definition
import od_absolute_gate as Q            # noqa: E402  the endpoint selection
import vertex_curvature_gate as AH      # noqa: E402  the loader AND the estimator, imported
from parallel import pmap               # noqa: E402

REPORT = "analysis/reports/s124_ship.json"
AG_REPORT = "analysis/reports/s135_drive_tilt.json"      # AG4's n=3 exponent, read not transcribed
AJ_REPORT = "analysis/reports/s139_pre_clipper_tilt.json"  # AJ2c's bound + its own exponent
OUT_JSON = "analysis/reports/s141_deficit_exponent.json"

# The two rungs the drive-tilt is taken between -- AG's own endpoints of the 24 dB ladder.
RUNG_LO, RUNG_HI = "sweep_clean", "sweep_drv_-6"

# Fit half-widths in OCTAVES.  PRIMARY is AH's own PRIMARY_HALF, imported rather than chosen, so
# this gate's windows are the ones AH6 cross-validated against AG at this feature.
HALF_SWEEP = (1.0 / 24, 1.0 / 16, 1.0 / 12, 1.0 / 8, 1.0 / 6)
PRIMARY_HALF = AH.PRIMARY_HALF                            # 1/12 oct -> 9 points on a 1/48 grid

# AG4's interpretable band, both bounds imported from GATE W's FEATURES table (AG4's own rule).
SMOOTH_LO = W.FEAT_BY_NAME["bt_notch"][2][1]              # 1000.0 Hz
SMOOTH_HI = W.FEAT_BY_NAME["treble_notch"][2][0]          # 4200.0 Hz

INJECT_TOL = 1e-9        # AL1a is exact algebra, so the bar is machine precision, not a guess
EXPO_REF_HZ = 2000.0     # the injection's reference frequency; any value works, it cancels
EXPO_INJECT_AMP = -40.0  # large enough that the REAL deficit is negligible beside the injected one
BOUND_TOL = 2e-3         # AL1c: a finite-difference reconstruction of an exact 2.000

SINGLE_POLE_BOUND = 2.0  # the exact class bound; AL1c must RECOVER it, never assume it

# The fixed spacing the PAIR exponent is taken over, in octaves.  1/3 oct is AG4's own centre
# spacing, so AJ2c's pair statistic is reproduced at its own scale rather than at whichever scale
# this gate's half-width sweep happens to be on.  See `exponent()` for why a fixed spacing is
# required at all.
PAIR_SPACING_OCT = 1.0 / 3.0

# Shipped Sallen-Key values, from `circuit.md`'s verified node graphs (unity-gain SK: C1 is the
# feedback cap, C2 the shunt to ground).  Named with their designators so a future value change is
# greppable.  AL5 uses these ONLY as operating points for a shape screen.
SK_STAGES = (
    ("IC4_B  R24/R25/C18/C27", 10e3, 22e3, 1.0e-9, 1.0e-9),
    ("IC4_A  R26/R27/C19/C20", 22e3, 47e3, 2.2e-9, 1.0e-9),
)
# AL5's size floor: a mechanism whose exponent is high only where it delivers nothing is useless
# -- that is AK3b's own argument ("strongest where the deficit is weakest"), reused as a screen.
AL5_SIZE_FRAC = 0.25


def _die(msg):
    """Refuse.  Exit 2, so a runner tells a fired guard from an uncaught crash (s133)."""
    print("\n" + "=" * 96)
    print(f"GATE AL: REFUSED — {msg}")
    print("=" * 96)
    sys.exit(2)


# ---------------------------------------------------------------------------
# The measured quantity
# ---------------------------------------------------------------------------
def drive_tilt(db_lo, db_hi, f0, half):
    """The change in slope at f0 between the quiet and hot rungs, on GATE W's grid.

    Both operands come from AH.tilt_at, which is AG's estimator -- the linear coefficient of a
    quadratic in log2(f/f0).  Returns None if either window is under-sampled.
    """
    a = AH.tilt_at(W.GRID, db_lo, f0, half)
    b = AH.tilt_at(W.GRID, db_hi, f0, half)
    return None if (a is None or b is None) else b - a


def deficit_at(by_file, files, f0, half, inject=None):
    """(pedal drive-tilt) - (model drive-tilt) at f0, reduced over captures.

    `inject` is a callable f(Hz)->dB added to the MODEL's quiet rung, or None.  It is passed as an
    ARGUMENT and never as module state: AH's loader runs under `parallel.pmap`, which is a
    THREAD pool, and s133 cost a session to a module-level injection flag leaking across workers.
    Nothing here is threaded, and keeping the perturbation functional is what guarantees it.

    -> dict(model, pedal, deficit, n) using the MEAN (AG4's reducer, so AL4's cross-check compares
       like with like) and the MEDIAN alongside it as the robustness column.
    """
    add = None if inject is None else np.asarray(inject(W.GRID), dtype=float)
    mt, pt = [], []
    for f in files:
        rec = by_file[f]
        m_lo = np.array(rec["model"][RUNG_LO]["db"], dtype=float)
        if add is not None:
            m_lo = m_lo + add
        m = drive_tilt(m_lo, np.array(rec["model"][RUNG_HI]["db"], dtype=float), f0, half)
        p = drive_tilt(np.array(rec["pedal"][RUNG_LO]["db"], dtype=float),
                       np.array(rec["pedal"][RUNG_HI]["db"], dtype=float), f0, half)
        if m is None or p is None:
            continue
        mt.append(m)
        pt.append(p)
    if not mt:
        return None
    mt, pt = np.array(mt), np.array(pt)
    return {"model": float(mt.mean()), "pedal": float(pt.mean()),
            "deficit": float(pt.mean() - mt.mean()),
            "deficit_median": float(np.median(pt) - np.median(mt)),
            "n": len(mt)}


def centres(half, independent):
    """Admissible fit centres whose WHOLE +-half window sits inside the feature-free band.

    `independent=True` returns a NON-OVERLAPPING set -- the only set whose count may be quoted as
    an n.  `False` returns every qualifying grid cell, which is one curve sampled finely and is
    used for SHAPE only.

    ⚠ CENTRES ARE SNAPPED TO GRID CELLS, and that is not cosmetic.  The first draft placed them at
    exact 2*half spacing from the band edge, i.e. at arbitrary frequencies, so a +-half window
    captured 4 or 5 cells depending on where each centre happened to fall between them -- the fit's
    point count, and therefore its bias, varied from centre to centre inside one sweep.  Snapping
    makes every window on a given half-width hold the same number of points by construction.
    """
    lo, hi = SMOOTH_LO * 2.0 ** half, SMOOTH_HI * 2.0 ** -half
    g = np.asarray(W.GRID, dtype=float)
    g = g[(g >= lo) & (g <= hi)]
    if len(g) == 0 or not independent:
        return g
    # Walk the grid taking the first cell at least 2*half above the last kept one, so consecutive
    # fit windows touch but never overlap.  Non-overlap is asserted by AL2, not assumed here.
    out = [float(g[0])]
    for f in g[1:]:
        if f >= out[-1] * 2.0 ** (2.0 * half) - 1e-9:
            out.append(float(f))
    return np.array(out)


def monotone_run(fs, d):
    """The maximal trailing run over which |d| is strictly increasing, and the split index.

    ⚠ COMPUTED, NOT CHOSEN.  A power law is a statement about a monotone quantity; fitting one
    across an interior extremum measures where the centres happened to fall, not a shape.  The
    split is the argmin of |d|, so a future capture set that moves the minimum moves the analysis
    with it and this stays a measurement rather than a hardcoded band.
    """
    a = np.abs(np.asarray(d, dtype=float))
    i = int(a.argmin())
    rising = bool(np.all(np.diff(a[i:]) > 0)) if len(a) - i >= 2 else False
    return i, rising


def exponent(fs, d, pair_spacing=None):
    """(regression exponent, pair exponents) of |d| against f, or None on a sign change.

    Refuses rather than taking a log across a zero -- AJ2c's own rule, kept because a power law
    fitted through a sign change has a DIVERGENT local exponent, which is precisely how a coarse
    grid manufactures a large one.

    ⚠⚠ THE PAIR STATISTIC IS TAKEN OVER A FIXED FREQUENCY SPACING, NOT BETWEEN "ADJACENT" CENTRES,
    AND THAT IS A CORRECTION TO AJ2c's CONSTRUCTION RATHER THAN A LOOSENING OF IT.  A pair exponent
    is log(|D_j/D_i|) / log(f_j/f_i): its DENOMINATOR is the centre spacing, so as the half-width
    sweep narrows and centres crowd together the same measurement noise is divided by a smaller
    number and the statistic blows up.  Measured here, the raw adjacent-pair minimum runs -10.3 at
    1/24 oct and +2.02 at 1/6 oct on ONE dataset whose regression exponent barely moves (2.53-2.90)
    -- i.e. the spread is the estimator's, not the deficit's.  AJ2c's version was sound because its
    centres were a fixed 1/3 oct apart; it simply is not scale-free, and a sweep is exactly what
    exposes that.  Fixing the spacing makes rows comparable ACROSS the sweep and matches the
    construction AL1c and AL5 use for the closed-form bound, so the measurement and the bound it is
    gated against are computed the same way.  The raw adjacent column is still returned and printed.
    """
    fs, d = np.asarray(fs, dtype=float), np.asarray(d, dtype=float)
    if len(fs) < 3 or np.any(d == 0) or len(set(np.sign(d))) != 1:
        return None
    lg = np.log(np.abs(d))
    reg = float(np.polyfit(np.log(fs), lg, 1)[0])
    adj = [float((lg[i + 1] - lg[i]) / math.log(fs[i + 1] / fs[i])) for i in range(len(fs) - 1)]
    if pair_spacing is None:
        return reg, adj, adj
    # Pairs separated by at least `pair_spacing` octaves, using MEASURED values only (no
    # interpolation): for each i take the first j whose separation clears the spacing.
    need = math.log(2.0 ** pair_spacing)
    fixed = []
    for i in range(len(fs)):
        for j in range(i + 1, len(fs)):
            if math.log(fs[j] / fs[i]) >= need - 1e-9:
                fixed.append(float((lg[j] - lg[i]) / math.log(fs[j] / fs[i])))
                break
    return reg, (fixed if fixed else adj), adj


# ---------------------------------------------------------------------------
# AL5's closed forms -- a shape screen on structures, not on parts
# ---------------------------------------------------------------------------
def sk_params(r1, r2, c1, c2):
    """Unity-gain Sallen-Key low-pass: (f0 Hz, Q) from the four shipped components."""
    t = math.sqrt(r1 * r2 * c1 * c2)
    return 1.0 / (2.0 * math.pi * t), t / (c2 * (r1 + r2))


def _biquad_tilt(wgrid, q, scale):
    """Slope in dB/oct of a 2nd-order LP with quality `q`, corner scaled by `scale`."""
    w = np.asarray(wgrid, dtype=float) / scale
    d = (1.0 - w ** 2) ** 2 + (w / q) ** 2
    return np.gradient(-10.0 / math.log(10.0) * np.log(d), np.log2(wgrid))


def pair_mechanism(wgrid, q, kind, eps=1e-4):
    """d(tilt)/d(parameter) for a complex pole pair: `kind` in {"Q", "f0"}.

    A one-sided difference on the parameter, which is the same construction AL1c uses for the real
    pole -- so AL5's two rows are computed the same way and their comparison is not an artefact of
    two different derivations.
    """
    base = _biquad_tilt(wgrid, q, 1.0)
    if kind == "Q":
        return (_biquad_tilt(wgrid, q * (1.0 + eps), 1.0) - base) / eps
    return (_biquad_tilt(wgrid, q, 1.0 + eps) - base) / eps


def real_pole_mechanism(wgrid, kind):
    """The refuted class, both of its sub-cases, in dB/oct of tilt change.

    "appear" is AJ2c's own form (the pole's contribution itself, -6.0206*u/(1+u)); "move" is the
    derivative of that with respect to ln(pole frequency).  Both must come back bounded by 2.
    """
    k = 20.0 * math.log(2.0) / math.log(10.0)
    u = np.asarray(wgrid, dtype=float) ** 2
    return -k * u / (1.0 + u) if kind == "appear" else 2.0 * k * u / (1.0 + u) ** 2


def fd_exponent(wgrid, g, w_at, spacing_oct):
    """Exponent read the way the MEASUREMENT reads it: a ratio over a fixed log spacing."""
    r = 2.0 ** spacing_oct
    a = float(np.interp(w_at, wgrid, g))
    b = float(np.interp(w_at * r, wgrid, g))
    if a == 0.0 or np.sign(a) != np.sign(b):
        return None
    return math.log(abs(b / a)) / math.log(r)


def max_fd_exponent(wgrid, g, spacing_oct, size_frac=0.0, w_max=1.3):
    """Largest finite-difference exponent anywhere, optionally where the mechanism has usable size.

    -> (exponent, w) or (None, None).  `size_frac` implements AK3b's screen: a mechanism whose
    exponent is high only where it delivers nothing cannot carry anything.
    """
    g = np.asarray(g, dtype=float)
    gmax = float(np.abs(g[np.asarray(wgrid) <= w_max]).max())
    best, at = None, None
    for i, wi in enumerate(wgrid):
        if abs(g[i]) < size_frac * gmax:
            continue
        e = fd_exponent(wgrid, g, wi, spacing_oct)
        if e is not None and (best is None or e > best):
            best, at = e, float(wi)
    return best, at


# ===========================================================================
# AL1 -- known answers
# ===========================================================================
def gate_al1(by_file, files, ag4_rows, out):
    print("\n" + "-" * 96)
    print("AL1  KNOWN ANSWERS — all three, before any measurement is read")
    print("-" * 96)
    fail = []
    base = np.array(by_file[files[0]]["model"][RUNG_LO]["db"], dtype=float)
    f0 = 2000.0

    # (a) injected TILT -- exact algebra (AG1b's arm, on this grid).
    worst = 0.0
    rows_a = []
    for t in (0.0, -1.185, +2.5, -7.0):
        pert = base + t * np.log2(np.asarray(W.GRID, dtype=float) / f0)
        # A gate should REFUSE where it would otherwise crash: a stack trace hands the next
        # session a symptom instead of a reason (s117).  `tilt_at` returns None when the window is
        # under-sampled, and `None - None` is a TypeError three frames from anything meaningful.
        v1 = AH.tilt_at(W.GRID, pert, f0, PRIMARY_HALF)
        v0 = AH.tilt_at(W.GRID, base, f0, PRIMARY_HALF)
        if v1 is None or v0 is None:
            _die(f"AL1a — the estimator is under-sampled at the PRIMARY half-width "
                 f"({PRIMARY_HALF:.5f} oct needs {AH.MIN_PTS} points on a {W.GRID_FRAC}/oct grid). "
                 f"No known answer can be evaluated, so nothing below is quotable.")
        got = v1 - v0
        worst = max(worst, abs(got - t))
        rows_a.append([t, float(got)])
        tag = "   <- ZERO: this arm's own mutation control, must recover nothing" if t == 0 else ""
        print(f"  (a) inject tilt {t:+7.3f} dB/oct -> recovered {got:+8.5f}  "
              f"|err| {abs(got - t):.2e}{tag}")
    ok_a = worst < INJECT_TOL
    print(f"      worst |err| = {worst:.2e} against an EXACT requirement   "
          f"{'PASS' if ok_a else 'FAIL'}")
    if not ok_a:
        fail.append("AL1a")

    # (b) ⭐ injected KNOWN EXPONENT -- the arm this gate's credibility rests on.
    #
    # Add to the MODEL's quiet rung a function whose local slope is exactly A*(f/fref)^p.  Then the
    # model's drive-tilt falls by A*(f/fref)^p at every centre, so the DEFICIT becomes a power law
    # of exponent p, and the measured exponent must come back p.  It will not come back exactly:
    # a quadratic fitted over a finite window of an exponential carries a bias, and that bias is
    # the quantity this arm exists to MEASURE rather than to assume away.
    print(f"\n  (b) injected known EXPONENT (amp {EXPO_INJECT_AMP:+.0f} dB/oct at "
          f"{EXPO_REF_HZ:.0f} Hz, so the real deficit is negligible beside it)")
    fs = centres(PRIMARY_HALF, independent=True)

    def make(p):
        def g(hz):
            u = np.log2(np.asarray(hz, dtype=float) / EXPO_REF_HZ)
            if p == 0.0:
                return EXPO_INJECT_AMP * u
            return EXPO_INJECT_AMP * (2.0 ** (p * u)) / (p * math.log(2.0))
        return g

    rows_b, biases = [], []
    for p in (0.0, SINGLE_POLE_BOUND, 2.84, 4.0):
        d = [deficit_at(by_file, files, f, PRIMARY_HALF, inject=make(p)) for f in fs]
        e = exponent(fs, [x["deficit"] for x in d], PAIR_SPACING_OCT)
        if e is None:
            _die(f"AL1b — the injected p={p} deficit changes sign across the centres, so the arm "
                 f"cannot report an exponent.  Raise |EXPO_INJECT_AMP| so the injection dominates.")
        rows_b.append([p, e[0]])
        biases.append(e[0] - p)
        print(f"      injected p = {p:5.3f}  ->  recovered {e[0]:6.3f}   bias {e[0] - p:+.4f}"
              + ("   <- ZERO: a CONSTANT deficit must read exponent 0" if p == 0.0 else ""))
    bias = max(abs(b) for b in biases)
    print(f"      worst |bias| over the sweep = {bias:.4f}")
    # THE DECISION-RELEVANT REQUIREMENT.  It is not enough that the estimator works; it must be
    # shown to separate the class bound from the measurement, because that separation IS the
    # conclusion AJ2c/AK3b draw.  An estimator biased by +0.84 would have manufactured both.
    got2 = [r[1] for r in rows_b if r[0] == SINGLE_POLE_BOUND][0]
    got284 = [r[1] for r in rows_b if r[0] == 2.84][0]
    ok_b = (got2 < 2.84) and (got284 > SINGLE_POLE_BOUND) and (got284 > got2)
    print(f"      ⭐ DISCRIMINATION: an injected {SINGLE_POLE_BOUND:.3f} reads {got2:.3f} "
          f"(< 2.840) and an injected 2.840 reads {got284:.3f} (> {SINGLE_POLE_BOUND:.3f})")
    print(f"         => the estimator can tell the class BOUND from the MEASUREMENT   "
          f"{'PASS' if ok_b else 'FAIL'}")
    if not ok_b:
        fail.append("AL1b")

    # (c) the class bound, recomputed by FINITE DIFFERENCE -- shares no algebra with AJ2c.
    print(f"\n  (c) the refuted class's bound, recomputed by finite difference over the same"
          f" spacing\n      the measurement uses (AJ2c derives it analytically as 2/(1+u); this "
          f"shares none of\n      that algebra, so agreement is a real cross-check)")
    wg = np.logspace(-2.5, 0.9, 20001)
    ok_c = True
    rows_c = []
    for kind in ("appear", "move"):
        g = real_pole_mechanism(wg, kind)
        e, at = max_fd_exponent(wg, g, 2.0 * PRIMARY_HALF)
        rows_c.append([kind, e, at])
        good = e is not None and e <= SINGLE_POLE_BOUND + BOUND_TOL
        ok_c &= good
        print(f"      single real pole, {kind:6s}: max exponent anywhere = {e:.4f} "
              f"(at w={at:.3f})   {'PASS' if good else 'FAIL'}")
    print(f"      both <= {SINGLE_POLE_BOUND:.3f} + {BOUND_TOL:g}   "
          f"{'PASS' if ok_c else 'FAIL'}")
    if not ok_c:
        fail.append("AL1c")

    # A free cross-check while AG4's rows are in hand: this gate must reproduce AG4's own n=3
    # exponent from AG4's own stored columns (not from this gate's surface) -- if it cannot, the
    # two are not computing the same statistic and AL4's comparison would be meaningless.
    ag_fs = [r[0] for r in ag4_rows]
    ag_d = [r[2] - r[1] for r in ag4_rows]
    ag_e = exponent(ag_fs, ag_d, PAIR_SPACING_OCT)
    if ag_e is None:
        _die("AL1 — AG4's own stored deficits change sign, so the number this gate is auditing "
             "cannot be reconstructed from the report that produced it.")
    print(f"\n  (d) AG4's n=3 exponent, recomputed from ITS OWN stored columns: {ag_e[0]:.3f}  "
          f"(pairs at {PAIR_SPACING_OCT:.4f} oct: "
          f"{', '.join('%.3f' % p for p in ag_e[1])})")
    print(f"      => the statistic this gate audits is reproduced from the source report, not "
          f"transcribed")

    out["al1"] = {"inject_tilt": rows_a, "inject_tilt_worst": float(worst),
                  "inject_expo": rows_b, "inject_expo_bias": float(bias),
                  "discriminates": bool(ok_b), "real_pole_bound": rows_c,
                  "ag4_exponent_recomputed": ag_e[0], "ag4_pairs_recomputed": ag_e[1]}
    if fail:
        _die(f"{', '.join(fail)} — a known answer did not reproduce; nothing below is quotable.")
    return ag_e


# ===========================================================================
# AL2 -- membership and window containment
# ===========================================================================
def gate_al2(by_file, files, out):
    print("\n" + "-" * 96)
    print("AL2  MEMBERSHIP and WINDOW CONTAINMENT — asserted before any exponent is read")
    print("-" * 96)
    print(f"  captures: {len(files)} (GATE AH's own membership, imported)")
    complete, partial = [], []
    for f in files:
        have = [s for s in (RUNG_LO, RUNG_HI) if s in by_file[f]["model"]
                and s in by_file[f]["pedal"]]
        (complete if len(have) == 2 else partial).append(f)
    if partial:
        _die(f"AL2 — {len(partial)} captures are missing a rung of the pair this gate differences "
             f"({partial[:3]}).  Data that existed and went missing is a MALFORMED read (s129).")
    print(f"  all {len(complete)} carry both {RUNG_LO} and {RUNG_HI}")

    print(f"\n  feature-free band {SMOOTH_LO:.0f}-{SMOOTH_HI:.0f} Hz, BOTH bounds imported from "
          f"GATE W's\n  FEATURES table (above the bridged-T's window, below the treble notch's) "
          f"— AG4's own rule.\n")
    print(f"  {'half (oct)':>11s} {'pts/fit':>8s} {'centre range (Hz)':>21s} "
          f"{'independent n':>14s} {'dense n':>8s}  usable")
    tab = {}
    ref = np.array(by_file[complete[0]]["model"][RUNG_LO]["db"])
    for half in HALF_SWEEP:
        ind, dense = centres(half, True), centres(half, False)
        if len(ind) == 0 or len(dense) == 0:
            _die(f"AL2 — no admissible centre at half-width {half:.4f} oct")
        # The point count must be the SAME at every centre, or the sweep's rows are not
        # comparable.  Asserted rather than sampled at one centre.
        counts = {(AH.curvature(W.GRID, ref, float(f), half) or {}).get("n", 0) for f in ind}
        npts = min(counts)
        # ⚠ UNDER-SAMPLED IS AN EXCLUSION WITH A REASON, NOT A HARD EXIT (s108).  A half-width too
        # narrow for a 3-parameter fit on this grid is an outcome of the grid, not a malformed
        # read -- the first draft exited here and killed the whole sweep on its narrowest row.
        usable = npts >= AH.MIN_PTS and len(counts) == 1
        lo_edge, hi_edge = float(ind[0]) * 2.0 ** -half, float(ind[-1]) * 2.0 ** half
        if lo_edge < SMOOTH_LO - 1e-6 or hi_edge > SMOOTH_HI + 1e-6:
            _die(f"AL2 — at half {half:.4f} a fit window spans {lo_edge:.1f}-{hi_edge:.1f} Hz and "
                 f"reaches outside the feature-free band; a slope there is a MIGRATING FEATURE "
                 f"sliding through the window, not a tilt (AG1c's rule).")
        # Non-overlap, asserted rather than assumed of the construction.
        if len(ind) > 1:
            gaps = np.diff(np.log2(ind))
            if gaps.min() < 2.0 * half - 1e-9:
                _die(f"AL2 — at half {half:.4f} two independent centres are {gaps.min():.5f} oct "
                     f"apart, closer than the {2 * half:.5f} oct their windows occupy, so they "
                     f"are NOT independent and their count must not be quoted as an n.")
        why = ("" if usable else
               f"  UNDER-SAMPLED ({npts} pts < {AH.MIN_PTS} on a {W.GRID_FRAC}/oct grid)")
        star = "   <- PRIMARY (AH's own, imported)" if half == PRIMARY_HALF else ""
        print(f"  {half:11.5f} {npts:8d} {float(ind[0]):9.1f} -{float(ind[-1]):9.1f} "
              f"{len(ind):14d} {len(dense):8d}  {str(usable):5s}{why}{star}")
        tab[half] = {"n_ind": len(ind), "n_dense": len(dense), "pts": npts,
                     "usable": bool(usable), "lo": float(ind[0]), "hi": float(ind[-1])}
    # ⚠ STRUCTURAL INVARIANT, NOT A TESTED GUARD (s133).  AL1a already evaluates the estimator AT
    # the primary half-width, so any grid coarse enough to under-sample the primary refuses there
    # first and this branch is unreachable -- its mutation arm was caught by AL1a, which is the
    # gate being better than the test's model of it (s119).  Kept against a future refactor that
    # moves AL1a off the primary; explicitly NOT claimed as something this gate's runner verifies.
    if not tab[PRIMARY_HALF]["usable"]:
        _die(f"AL2 — the PRIMARY half-width {PRIMARY_HALF:.5f} is itself under-sampled; this gate "
             f"has no readable headline.")
    n_prim = tab[PRIMARY_HALF]["n_ind"]
    print(f"\n  ⇒ at the primary half-width the INDEPENDENT n is {n_prim}, against AG4's 3 "
          f"({n_prim / 3.0:.1f}x).")
    print(f"    The dense column is ONE CURVE sampled finely, not {tab[PRIMARY_HALF]['n_dense']} "
          f"measurements; it is\n    used for SHAPE and never as an n.")
    out["al2"] = {"n_captures": len(complete), "by_half": {str(k): v for k, v in tab.items()},
                  "n_independent_primary": n_prim}
    return complete, tab


# ===========================================================================
# AL3 -- the two operands, dense, and the sign scan
# ===========================================================================
def gate_al3(by_file, files, out):
    print("\n" + "-" * 96)
    print("AL3  THE TWO OPERANDS across the band, and the SIGN scan (s117)")
    print("-" * 96)
    print("  A deficit is a difference, and a difference cannot say which end moved.  A power law")
    print("  fitted across a SIGN CHANGE has a divergent local exponent, so where the deficit")
    print("  crosses zero is the first thing that has to be known.\n")
    fs = centres(PRIMARY_HALF, independent=True)
    rows = []
    print(f"  {'centre Hz':>10s} {'MODEL dTilt':>12s} {'PEDAL dTilt':>12s} {'deficit':>10s} "
          f"{'median':>9s} {'n':>4s}")
    for f0 in fs:
        d = deficit_at(by_file, files, float(f0), PRIMARY_HALF)
        if d is None:
            _die(f"AL3 — no readable slope at {f0:.1f} Hz")
        rows.append([float(f0), d["model"], d["pedal"], d["deficit"], d["deficit_median"], d["n"]])
        print(f"  {f0:10.1f} {d['model']:+12.3f} {d['pedal']:+12.3f} {d['deficit']:+10.3f} "
              f"{d['deficit_median']:+9.3f} {d['n']:4d}")
    dv = np.array([r[3] for r in rows])
    signs = set(np.sign(dv))
    n_neg = int((dv < 0).sum())

    # ⭐⭐ MONOTONICITY, printed before anything is fitted.  AG4 read three centres and described
    # the result as "the deficit STEEPENS with frequency"; that is a claim about a monotone
    # quantity, and on 12 centres it can be tested rather than assumed (s129: an endpoint pair is
    # not a ladder -- here the whole interior between 1000 Hz and AG4's lowest centre was unseen).
    i_min, rising = monotone_run([r[0] for r in rows], dv)
    a = np.abs(dv)
    mono_all = bool(np.all(np.diff(a) > 0))
    print(f"\n  |deficit| minimum at {rows[i_min][0]:.1f} Hz ({a[i_min]:.3f} dB/oct), "
          f"index {i_min}/{len(a) - 1}")
    print(f"  monotone increasing across ALL centres: {mono_all}   "
          f"strictly rising from the minimum onward: {rising}")
    if not mono_all:
        print(f"  ⚠⚠ THE DEFICIT IS NOT MONOTONE ACROSS THE INTERPRETABLE BAND.  It FALLS from")
        print(f"     {a[0]:.3f} dB/oct at {rows[0][0]:.0f} Hz to {a[i_min]:.3f} at "
              f"{rows[i_min][0]:.0f} Hz, then rises to {a[-1]:.3f} at {rows[-1][0]:.0f} Hz.")
        print(f"     AG4's three centres all sit ABOVE that minimum, on the rising limb, so its")
        print(f"     'steepens with frequency' describes ONE LIMB and was never able to see the")
        print(f"     other.  A single power law over the whole band is not defined; AL4 fits the")
        print(f"     rising limb and names the excluded one.")
    print(f"\n  deficit negative at {n_neg}/{len(dv)} centres; distinct signs = {len(signs)}")
    if len(signs) == 1:
        sv = ("SINGLE-SIGNED across the whole interpretable band — log|D| is well defined and "
              "AL4's exponent is not a zero-crossing artefact")
    else:
        xs = [f"{rows[i][0]:.0f}->{rows[i + 1][0]:.0f} Hz"
              for i in range(len(dv) - 1) if np.sign(dv[i]) != np.sign(dv[i + 1])]
        sv = ("⚠⚠ THE DEFICIT CHANGES SIGN inside the interpretable band (" + ", ".join(xs) +
              ") — a power law through a zero crossing has a DIVERGENT local exponent, so any "
              "exponent quoted across it is an artefact of where the centres happened to fall")
    print(f"  ⇒ {sv}")
    # The model's own operand, printed rather than assumed: item 6's whole premise is that ours is
    # pinned, and if it is not, the deficit is not "the pedal's mechanism" (s117's rule).
    mm = np.array([r[1] for r in rows])
    pp = np.array([r[2] for r in rows])
    print(f"\n  MODEL drive-tilt spans {mm.min():+.3f} .. {mm.max():+.3f} dB/oct "
          f"(range {mm.max() - mm.min():.3f})")
    print(f"  PEDAL drive-tilt spans {pp.min():+.3f} .. {pp.max():+.3f} dB/oct "
          f"(range {pp.max() - pp.min():.3f})")

    # ⭐⭐ THE MODEL'S OWN OPERAND CROSSES ZERO, AND WHERE IT DOES IS NOT A DETAIL.  AG3 reads the
    # model's drive-tilt AT the vertex and reports it "PINNED" (span 0.094 dB/oct across the 24 dB
    # ladder), which item 6 carries as a property of the model.  Across FREQUENCY it is nothing of
    # the kind -- it runs from strongly negative at 1 kHz to positive at 3.8 kHz.  Printed because
    # "pinned" and "passing through zero here" are different statements with different
    # consequences for a candidate, and only the second is what the data supports.
    zc = None
    for i in range(len(mm) - 1):
        if mm[i] <= 0.0 <= mm[i + 1] or mm[i] >= 0.0 >= mm[i + 1]:
            f_a, f_b = rows[i][0], rows[i + 1][0]
            t = (0.0 - mm[i]) / (mm[i + 1] - mm[i]) if mm[i + 1] != mm[i] else 0.0
            zc = float(f_a * (f_b / f_a) ** t)
            break
    if zc is not None:
        vtx = out.get("vertex_hz", 2934.8)
        print(f"\n  ⭐ the MODEL's own drive-tilt CROSSES ZERO at ~{zc:.0f} Hz "
              f"({100 * (zc / vtx - 1):+.1f} % from the {vtx:.0f} Hz vertex).")
        print(f"    ⇒ AG3's \"the model is PINNED at the vertex\" is a LOCAL reading at a zero")
        print(f"      crossing of the model's own drive-tilt, not a property of the model across")
        print(f"      this band — over 1070-3814 Hz it moves {mm.max() - mm.min():.3f} dB/oct,")
        print(f"      {(mm.max() - mm.min()) / (pp.max() - pp.min()):.2f}x the pedal's own range.")
        print(f"    ⚠ Recorded as measured.  Why the crossing sits near the vertex is NOT")
        print(f"      explained here and is not claimed to be more than a coincidence.")
    out["al3"] = {"rows": rows, "single_signed": len(signs) == 1, "n_negative": n_neg,
                  "sign_verdict": sv, "model_range": [float(mm.min()), float(mm.max())],
                  "pedal_range": [float(pp.min()), float(pp.max())],
                  "monotone_all": mono_all, "min_index": i_min, "min_hz": rows[i_min][0],
                  "rising_from_min": rising, "model_zero_cross_hz": zc}
    return rows, len(signs) == 1


# ===========================================================================
# AL4 -- the exponent, the headline
# ===========================================================================
def gate_al4(by_file, files, tab, ag_e, aj, out):
    print("\n" + "-" * 96)
    print("AL4  THE EXPONENT — non-overlapping centres, half-width swept")
    print("-" * 96)
    bound = aj.get("aj2", {}).get("exponent_bound", SINGLE_POLE_BOUND)
    ag_stored = aj.get("aj2", {}).get("exponent")
    ag_pairs = aj.get("aj2", {}).get("exponent_pairs", [])
    print(f"  AJ2c's stored reading (imported from the s139 report, not transcribed):")
    print(f"     exponent {ag_stored:.3f} over n = {aj.get('aj2', {}).get('n_centres')} centres, "
          f"weakest adjacent pair {min(ag_pairs):.3f}, class bound {bound:.3f}\n")
    print(f"  Fitted on the RISING LIMB only — the sub-range over which |D| is monotone, whose")
    print(f"  start is COMPUTED as the argmin of |D| at each half-width (AL3).  A power law is a")
    print(f"  statement about a monotone quantity; the falling limb is printed and excluded.\n")
    print(f"  {'half':>8s} {'n_all':>6s} {'n_limb':>7s} {'limb from':>10s} {'exponent':>9s} "
          f"{'weakest pair':>13s} {'strongest':>10s} {'> bound':>8s} {'raw adj min':>11s}")
    res = {}
    for half in HALF_SWEEP:
        if not tab[half]["usable"]:
            print(f"  {half:8.5f}    -- UNDER-SAMPLED at this grid, excluded (AL2)")
            res[half] = {"n": None, "exponent": None, "usable": False}
            continue
        fs = centres(half, independent=True)
        d = [deficit_at(by_file, files, float(f), half) for f in fs]
        if any(x is None for x in d):
            _die(f"AL4 — unreadable slope at half {half} despite AL2 calling it usable; the two "
                 f"disagree, which is a defect in this gate rather than in the data.")
        dv = [x["deficit"] for x in d]
        i0, _rise = monotone_run(fs, dv)
        fl, dl = fs[i0:], dv[i0:]
        e = exponent(fl, dl, PAIR_SPACING_OCT)
        if e is None:
            print(f"  {half:8.5f} {len(fs):6d} {len(fl):7d} {'--':>10s}    SIGN CHANGE or n<3 — "
                  f"refused (log|D| undefined)")
            res[half] = {"n": len(fs), "n_limb": len(fl), "exponent": None, "usable": True}
            continue
        reg, pair, adj = e
        res[half] = {"n": len(fs), "n_limb": len(fl), "limb_from_hz": float(fl[0]),
                     "exponent": reg, "pairs": pair, "adjacent_pairs": adj, "usable": True,
                     "weakest": min(pair), "strongest": max(pair),
                     "weakest_adjacent": min(adj),
                     "centres": [float(x) for x in fl], "deficits": dl}
        star = "   <- PRIMARY" if half == PRIMARY_HALF else ""
        print(f"  {half:8.5f} {len(fs):6d} {len(fl):7d} {float(fl[0]):10.1f} {reg:9.3f} "
              f"{min(pair):13.3f} {max(pair):10.3f} {str(min(pair) > bound):>8s}"
              f" {min(adj):11.3f}{star}")

    prim = res[PRIMARY_HALF]
    if prim["exponent"] is None:
        verdict = ("NOT MEASURABLE — the deficit changes sign at the primary half-width, so no "
                   "exponent is defined and AJ2c's screen cannot be evaluated on this surface")
        # ⚠ This early return must populate EVERY key `main` reads, or a branch that fires only on
        # unusual data crashes with a KeyError three frames away from the reason (s117: a gate
        # should refuse where it would otherwise crash).  Found by this gate's own sign-scan
        # mutation arm, which is the only thing that ever executes this path.
        v_unif = ("not evaluated — the uniformity clause is a statement about an exponent, and no "
                  "exponent is defined here")
        print(f"\n  ⇒ {verdict}")
        print(f"  ⇒ {v_unif}")
        out["al4"] = {"by_half": {str(k): v for k, v in res.items()}, "verdict": verdict,
                      "uniform_verdict": v_unif, "bound": bound, "aj_stored": ag_stored,
                      "weakest_any_half": float("nan"), "primary": prim,
                      "survives": None, "uniform": None}
        return res, verdict, None

    usable = [v for v in res.values() if v.get("exponent") is not None]
    if not usable:
        _die("AL4 — no half-width yields a defined exponent; `empty-gate-must-fail`.")
    w_all = min(v["weakest"] for v in usable)

    # ⭐⭐ THE GATED STATISTIC IS THE ENDPOINT-TO-ENDPOINT EXPONENT OVER THE LIMB, AND IT IS THE
    # ONLY ONE THE CLASS BOUND EXACTLY IMPLIES.  AJ2c gated on the weakest adjacent pair, reasoning
    # that the reading most favourable to the candidate is the honest bar.  That instinct is right
    # for a claim of the form "the deficit beats the bound EVERYWHERE" -- but that is not the claim
    # the refutation needs, and it is not what the bound gives you.  Integrate the pointwise bound:
    #
    #     d ln|g| / d ln f <= 2  on [a,b]   =>   ln|g(b)| - ln|g(a)| <= 2 ln(b/a)
    #     i.e.  ENDPOINT exponent  ln|g(b)/g(a)| / ln(b/a)  <=  2,  EXACTLY, for the whole class.
    #
    # So a single moving pole cannot produce a limb whose ENDPOINT exponent exceeds 2, whatever it
    # does in between -- which makes the endpoint reading a sufficient refutation, mathematically
    # implied rather than fitted, and simultaneously the most robust statistic available (two
    # values, the largest possible lever arm, no per-pair noise amplification and no regression).
    # It is also STRICTER than the regression in the sense that matters: it cannot be rescued by a
    # favourable interior.
    print(f"\n  {'half':>8s} {'limb (Hz)':>19s} {'|D| ends':>17s} {'ENDPOINT expo':>14s} "
          f"{'> bound':>8s}")
    ends = {}
    for half, v in res.items():
        if v.get("exponent") is None:
            continue
        fl, dl = v["centres"], v["deficits"]
        e_end = math.log(abs(dl[-1] / dl[0])) / math.log(fl[-1] / fl[0])
        ends[half] = e_end
        v["endpoint_exponent"] = e_end
        star = "   <- PRIMARY" if half == PRIMARY_HALF else ""
        print(f"  {half:8.5f} {fl[0]:8.1f} -{fl[-1]:9.1f} {abs(dl[0]):7.3f} ->{abs(dl[-1]):7.3f} "
              f"{e_end:14.3f} {str(e_end > bound):>8s}{star}")
    e_min = min(ends.values())
    print(f"\n  The ENDPOINT exponent is > {bound:.3f} at {sum(1 for x in ends.values() if x > bound)}"
          f"/{len(ends)} half-widths; the smallest is {e_min:.3f}.")
    print(f"  Regression over the limb, for comparison: "
          + " / ".join(f"{v['exponent']:.3f}" for v in usable)
          + f"   (AG4's n=3: {ag_stored:.3f})")
    print(f"  Weakest {PAIR_SPACING_OCT:.3f}-oct PAIR anywhere: {w_all:.3f} — reported, NOT gated "
          f"on;\n  see the note in `exponent()` and AL4's own verdict for why AJ2c's per-pair "
          f"phrasing\n  does not survive a sweep even though its conclusion does.\n")

    # The dense curve, for SHAPE only.  Explicitly not an n.
    fs_d = centres(PRIMARY_HALF, independent=False)
    dd = [deficit_at(by_file, files, float(f), PRIMARY_HALF) for f in fs_d]
    fsd = [f for f, x in zip(fs_d, dd) if x is not None]
    dvd = [x["deficit"] for x in dd if x is not None]
    j0, _r = monotone_run(fsd, dvd)
    ed = exponent(fsd[j0:], dvd[j0:], PAIR_SPACING_OCT)
    print(f"  dense scan, rising limb ({len(dvd) - j0} OVERLAPPING centres from "
          f"{fsd[j0]:.0f} Hz — shape only, NOT an n): "
          + ("exponent %.3f" % ed[0] if ed else "sign change — refused"))

    # Computed verdict.  The target appears as a VARIABLE (s130 AB5): delete `bound` and this
    # classification cannot run, which is the test that it is a measurement and not narration.
    survives = all(x > bound for x in ends.values())
    agrees = abs(prim["exponent"] - ag_stored) <= 0.5 * abs(ag_stored - bound)
    uniform = w_all > bound
    if survives and agrees:
        verdict = (f"CONFIRMED — the endpoint exponent exceeds the class bound {bound:.3f} at "
                   f"ALL {len(ends)} usable half-widths (smallest {e_min:.3f}), on "
                   f"{prim['n_limb']} independent centres at the primary "
                   f"({prim['n_limb'] / 3.0:.1f}x AG4's n), and the limb regression "
                   f"{prim['exponent']:.3f} reproduces AG4's n=3 reading {ag_stored:.3f}.  "
                   f"AJ2c's and AK3b's shape refutations REST ON A MEASUREMENT, not on three points")
    elif survives:
        verdict = (f"CONFIRMED IN DIRECTION, MOVED IN SIZE — the endpoint exponent clears "
                   f"{bound:.3f} at all {len(ends)} half-widths (smallest {e_min:.3f}), so AJ2c's "
                   f"refutation stands; but the limb regression reads {prim['exponent']:.3f} "
                   f"against AG4's {ag_stored:.3f}, so 'f^{ag_stored:.2f}' must be re-quoted")
    else:
        verdict = (f"⛔⛔ AJ2c's SHAPE REFUTATION DOES NOT SURVIVE — the endpoint exponent falls to "
                   f"{e_min:.3f}, INSIDE the class bound {bound:.3f}, at "
                   f"{sum(1 for x in ends.values() if x <= bound)}/{len(ends)} half-widths.  A "
                   f"single moving pole is NOT excluded by shape, the whole 'a capacitance grows "
                   f"with drive' class re-opens, and AK3b's positive specification loses its basis")
    print(f"  ⇒ {verdict}")
    # The SECOND verdict, separate because it corrects a PHRASING rather than a conclusion.
    if uniform:
        v_unif = (f"and the deficit beats the bound UNIFORMLY too — the weakest "
                  f"{PAIR_SPACING_OCT:.3f}-oct pair anywhere is {w_all:.3f}")
    else:
        v_unif = (f"⚠ BUT NOT UNIFORMLY, AND AJ2c SAID IT WAS: its wording is \"EVERY adjacent "
                  f"pair exceeds the bound\", and on this surface the weakest "
                  f"{PAIR_SPACING_OCT:.3f}-oct pair is {w_all:.3f}, INSIDE {bound:.3f}.  The "
                  f"deficit steepens faster than f^{bound:.0f} ACROSS the limb while containing "
                  f"sub-ranges where it does not, so a single pole is refuted as the carrier of "
                  f"the WHOLE limb and was never refuted pointwise.  Quote the endpoint reading, "
                  f"not the per-pair one")
    print(f"  ⇒ {v_unif}")
    out["al4"] = {"by_half": {str(k): v for k, v in res.items()}, "verdict": verdict,
                  "uniform_verdict": v_unif, "bound": bound, "aj_stored": ag_stored,
                  "weakest_any_half": w_all, "endpoint_by_half": {str(k): v for k, v in
                                                                  ends.items()},
                  "endpoint_min": e_min, "uniform": bool(uniform),
                  "dense_exponent": (ed[0] if ed else None), "dense_n": len(dvd),
                  "primary": prim, "survives": bool(survives), "agrees_with_ag4": bool(agrees)}
    return res, verdict, e_min


# ===========================================================================
# AL5 -- what class of structure CAN produce it
# ===========================================================================
def gate_al5(measured, out):
    print("\n" + "-" * 96)
    print("AL5  WHAT CAN PRODUCE IT — a shape screen on STRUCTURES, not on parts")
    print("-" * 96)
    if measured is None:
        print("  AL4 reported no measurable exponent, so there is no target to screen against.")
        out["al5"] = {"skipped": "no measured exponent"}
        return None
    print(f"  target: a carrier must reach d ln|D|/d ln f >= {measured:.3f} AT THE VERTEX, and")
    print(f"  deliver usable SIZE there ( >= {AL5_SIZE_FRAC:.0%} of its own maximum ) — AK3b's own")
    print(f"  screen, since a mechanism strongest where the deficit is weakest carries nothing.\n")
    wg = np.logspace(-2.5, 0.9, 20001)
    sp = 2.0 * PRIMARY_HALF
    vertex = out.get("vertex_hz", 2934.8)

    print(f"  {'structure':34s} {'max exponent':>13s} {'at w':>7s}   note")
    rows = []
    for kind in ("appear", "move"):
        g = real_pole_mechanism(wg, kind)
        e, at = max_fd_exponent(wg, g, sp)
        rows.append(["real pole " + kind, e, at, None, None])
        print(f"  {'ONE real pole, ' + kind:34s} {e:13.3f} {at:7.3f}   the REFUTED class "
              f"(AL1c)")
    print(f"  {'N real poles, all below corner':34s} {'2.000':>13s} {'--':>7s}   a sum of f^2 "
          f"terms is f^2")

    print(f"\n  Complex pole pair, at the SHIPPED Sallen-Key operating points "
          f"(vertex {vertex:.0f} Hz):")
    print(f"  {'stage':26s} {'f0 Hz':>8s} {'Q':>7s} {'w@vtx':>7s} {'Q-change':>9s} "
          f"{'f0-move':>8s}  reaches?")
    sk_rows = []
    for name, r1, r2, c1, c2 in SK_STAGES:
        f0, q = sk_params(r1, r2, c1, c2)
        wv = vertex / f0
        vals = {}
        for kind in ("Q", "f0"):
            g = pair_mechanism(wg, q, kind)
            vals[kind] = fd_exponent(wg, g, wv, sp)
        fmt = {k: ("  sign chg" if v is None else f"{v:9.3f}") for k, v in vals.items()}
        reach = any(v is not None and v >= measured for v in vals.values())
        print(f"  {name:26s} {f0:8.1f} {q:7.4f} {wv:7.4f} {fmt['Q']:>9s} {fmt['f0']:>8s}  "
              f"{'YES' if reach else 'no'}")
        sk_rows.append([name, f0, q, wv, vals["Q"], vals["f0"], bool(reach)])

    # Where WOULD a resonance have to sit?  This is the positive specification s140 asked for.
    print(f"\n  ⭐ WHERE a resonance would have to sit to carry it (the positive specification):")
    print(f"  {'kind':6s} {'Q':>7s}   admissible w                required f0 (Hz)")
    band = []
    for kind in ("Q", "f0"):
        for q in (0.4635, 0.6912, 0.7071, 1.0, 2.0):
            g = pair_mechanism(wg, q, kind)
            gmax = float(np.abs(g[wg <= 1.3]).max())
            ok = []
            for i, wi in enumerate(wg):
                if abs(g[i]) < AL5_SIZE_FRAC * gmax:
                    continue
                e = fd_exponent(wg, g, float(wi), sp)
                if e is not None and e >= measured:
                    ok.append(float(wi))
            if ok:
                lo, hi = min(ok), max(ok)
                print(f"  {kind:6s} {q:7.4f}   w in [{lo:.3f}, {hi:.3f}]"
                      f"          f0 in [{vertex / hi:7.0f}, {vertex / lo:7.0f}]")
                band.append([kind, q, lo, hi, vertex / hi, vertex / lo])
            else:
                print(f"  {kind:6s} {q:7.4f}   NONE at usable size")
                band.append([kind, q, None, None, None, None])

    any_sk = any(r[6] for r in sk_rows)
    if any_sk:
        v5 = ("a SHIPPED Sallen-Key reaches the measured exponent at the vertex — the resonance "
              "class is admissible IN SHAPE and needs a size and a carrier screen next")
    else:
        v5 = ("NO shipped resonance reaches it at the vertex — both Sallen-Keys are mis-positioned "
              "relative to the feature (one sits essentially AT its own resonance where the "
              "mechanism's own slope change passes through zero, the other is deep in its f^2 "
              "regime), which is AK's root cause in a second guise: a carrier's corner has to be "
              "placed right, not merely present")
    print(f"\n  AL5-VERDICT: {v5}")
    print(f"  ⚠ SHAPE ONLY.  Admissible in shape is NECESSARY, never sufficient — s140's AK5 is "
          f"the\n    standing example of a carrier passing every sign gate and dying on size.")
    print(f"  ⚠ These are mechanism sizes on the shipped LINEAR cascade, not priced renders.")
    out["al5"] = {"target": measured, "real_pole": rows, "sk": sk_rows, "band": band,
                  "any_shipped_reaches": bool(any_sk), "verdict": v5,
                  "size_frac": AL5_SIZE_FRAC}
    return v5


# ===========================================================================
def main():
    ap = argparse.ArgumentParser(description="GATE AL — the deficit's frequency exponent, audited")
    ap.add_argument("--report", default=REPORT)
    ap.add_argument("--ag", default=AG_REPORT)
    ap.add_argument("--aj", default=AJ_REPORT)
    ap.add_argument("--jobs", type=int, default=None)
    ap.add_argument("--json", default=OUT_JSON)
    a = ap.parse_args()

    for p in (a.report, a.ag, a.aj):
        if not os.path.exists(p):
            _die(f"{p} not found — this gate reads its operands from stored reports and will not "
                 f"reconstruct them.  Re-run the session that produced it.")
    rep = json.load(open(a.report))
    ag = json.load(open(a.ag))
    aj = json.load(open(a.aj))

    ag4 = ag.get("ag4", {})
    rows4 = [r for r in ag4.get("rows", []) if r[3]]
    if len(rows4) != 3:
        _die(f"AL — the s135 report carries {len(rows4)} uncontaminated AG4 centres, not the 3 "
             f"this gate exists to audit.  Check what moved before re-pointing it.")
    if "aj2" not in aj or "exponent" not in aj["aj2"]:
        _die("AL — the s139 report has no aj2.exponent; this gate will not transcribe AJ2c's "
             "number from a handover.")

    print("=" * 96)
    print("GATE AL — the deficit's frequency EXPONENT, audited on a 14x finer surface")
    print("=" * 96)
    print(f"  captures from : {a.report}")
    print(f"  AG4 operands  : {a.ag}   (the n=3 reading being audited)")
    print(f"  AJ2c bound    : {a.aj}   (the class bound and its stored exponent)")
    print(f"  surface       : GATE W's {W.GRID_FRAC}/oct transfer, {len(W.GRID)} points, "
          f"GATE W's renders")
    print(f"  estimator     : GATE AH's tilt_at (= AG's), imported not re-written")
    print(f"  drive-tilt    : {RUNG_HI} minus {RUNG_LO}")
    print("  ⚠ PREMISE, printed every run: overlapping windows are ONE CURVE, not many")
    print("    measurements.  Every verdict below is taken from NON-OVERLAPPING centres.")

    out = {"report": a.report, "ag_report": a.ag, "aj_report": a.aj,
           "grid_frac": W.GRID_FRAC, "primary_half_oct": PRIMARY_HALF,
           "vertex_hz": ag.get("vertex_hz", 2934.8)}

    caps = {c["file"]: c for c in rep["captures"]}
    eps = [e for e in Q.endpoints_od(caps) if not MG.is_gain_n12(e)]
    n_all = len(Q.endpoints_od(caps))
    if n_all != R.EXPECT_ENDPOINTS:
        _die(f"GATE Q's endpoint count moved ({n_all} vs {R.EXPECT_ENDPOINTS}) — bump it THERE "
             f"deliberately after checking what arrived.")
    print(f"\n  GATE Q pure-OD endpoints: {n_all}, {len(eps)} after excluding `gain-n12`")
    print(f"  rendering / reading {len(eps)} captures x {len(W.SWEEPS)} sweeps "
          f"(GATE W's cache) ...")
    rows = pmap(AH._cell, eps, jobs=a.jobs)
    by_file = {r["file"]: r for r in rows}
    files = sorted(by_file)

    ag_e = gate_al1(by_file, files, rows4, out)
    files, tab = gate_al2(by_file, files, out)
    _rows3, single = gate_al3(by_file, files, out)
    _res, v4, weakest = gate_al4(by_file, files, tab, ag_e, aj, out)
    prim = out["al4"].get("primary") or {}
    v5 = gate_al5(prim.get("exponent"), out)

    print("\n" + "-" * 96)
    print("AL6  VERDICT")
    print("-" * 96)
    print(f"  AL3  {out['al3']['sign_verdict']}")
    print(f"  AL4  {v4}")
    print(f"       {out['al4']['uniform_verdict']}")
    if v5:
        print(f"  AL5  {v5}")
    print(f"\n  AL6-MEMBERSHIP scored=[{','.join(sorted(f[:40] for f in files))}]")
    print(f"  AL6-EXPONENT n_independent={prim.get('n')} exponent="
          f"{prim.get('exponent') if prim.get('exponent') is None else round(prim['exponent'], 3)} "
          f"endpoint_min={weakest if weakest is None else round(weakest, 3)} "
          f"weakest_pair={round(out['al4']['weakest_any_half'], 3)} "
          f"bound={out['al4']['bound']} survives={out['al4'].get('survives')} "
          f"single_signed={single}")

    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
        with open(a.json, "w") as fh:
            json.dump(out, fh, indent=1, default=float)
        print(f"\n  -> {a.json}")
    print("\n" + "=" * 96)
    print("GATE AL: all guards passed.  AL3-AL5 are readable.")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
