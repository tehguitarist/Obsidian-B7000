#!/usr/bin/env python3.11
"""GATE AZ -- task D(b): fit the SHIPPABLE LEVEL taper to GATE AY's solved requirement.

Session 163.  No render of its own: a re-read of the same matrix report GATE AY used, plus GATE
AY's own objective, imported rather than re-derived.

WHAT THIS IS AND WHAT IT IS NOT
-------------------------------
GATE AY (s162) established the two halves separately:

  * task D **as specified** -- closing item 9's ~2-3x LEVEL-SENSITIVITY gap -- is REFUTED on a
    bound over the whole taper family (sup fold 1.368x against a required 1.744x/2.670x).  ⛔ This
    gate does not re-open that and ships nothing aimed at it.
  * GATE K's closure *"THE TAPER CANNOT FIX IT"* is REFUTED **for the segmented family**: a free
    monotone curve closes the LEVEL LAW to 0.344 dB rms against the target's own 0.755 dB
    ambiguity, where no single exponent gets within 2.79x.

The user's decision at the end of s162 was to ship the second.  That is what this gate is for: it
turns AY3's `required_taper` into a piecewise-linear pot law of the family the MASTER pot already
ships (s146), and it decides the SEGMENT COUNT by measurement rather than by the precedent's
number.

⭐ THE OBJECTIVE IS AY3's, IMPORTED, AND THE KNOWN ANSWER IS THAT IT REPRODUCES AY3's OWN NUMBERS.
AY3's scorer is a closure, so the five lines are rebuilt here -- and AZ1 then requires them to
return AY3's **stored** rms and worst for all three of its families, to 0.  If that fails, this
gate is scoring something else and nothing below it means anything (s154: replace a transcribed
number with a read of the stored report, and the reproduction is the check).

⭐⭐ WHY THE SEGMENT COUNT IS MEASURED, NOT INHERITED.  s162's own hand-over said "the s146 MASTER
precedent: 3-segment PWL".  Measured on this requirement, 3 segments does NOT reach: it misplaces
the 0.875 detent by 0.19 in L and leaves a structured, sign-alternating residual.  4 reaches the
architectural floor, and a 5-segment control returns the 4-segment answer to the digit -- the
family SATURATES, which is the stopping proof s146 wanted for MASTER and could not have here by
assumption.  ⚠ The precedent is a family, not a number.

⭐⭐⭐ AND THE OVERFITTING QUESTION IS ANSWERED IN THE REQUIREMENT'S OWN UNITS, not by parameter
counting.  AY3 publishes a per-detent across-stimulus SPREAD -- how well each required L is
determined at all.  A candidate that lands inside that spread AT EVERY DETENT is not fitting
noise; it is reproducing a curve measured better than it is being fitted.  AZ3 grades exactly
that, and it is the one test that distinguishes "6 parameters against 8 points" from "a curve
inside its own error bars".

GATES (all computed; exits non-zero on failure)
-----------------------------------------------
AZ1  the imports and the KNOWN ANSWER: the rebuilt objective must reproduce GATE AY3's stored
     shipped / best-exponent / free-curve rms and worst, exactly.  Mutation: perturb the scorer.
AZ2  the FAMILY SWEEP, 2..5 segments on that objective, with the saturation control.  Verdict is
     computed against AY3's own ambiguity bar and against the free curve's floor.
AZ3  CONTAINMENT: is the chosen curve inside the requirement's own per-detent spread everywhere?
     This is the overfitting test, in the constant's units.
AZ4  the curve's own SHAPE properties, none of which any term of the objective asked for:
     monotone in the knob, endpoints exact, segment slopes RISING (convex -- a physically
     buildable resistive track), and the half-rotation fraction against the textbook A-taper
     10-15 % band that `circuit.md` specifies for VR2.  s146's outside corroboration, re-used.
AZ5  the COST, priced before it ships: the clean-fraction shift at every detent, which is what
     `OdToneRestore`'s s156 mix law reads -- so this taper re-stales that fit by construction and
     the size of the re-fit owed is a number, not a worry.
AZ6  what must NOT move: L(1) = 1 exactly, so the ANCHOR every absolute instrument in
     the project reads at is bit-identical.  Asserted, not assumed.

Run:
    python3.11 analysis/level_taper_fit.py analysis/reports/s162_shipped.json
    python3.11 analysis/level_taper_fit.py REPORT.json --ay analysis/reports/s162_level_taper.json \
        --json analysis/reports/s163_level_taper_fit.json
"""
import glob
import os
import argparse
import json
import math
import sys

import numpy as np
from scipy.optimize import minimize

import matrix_grade as MG
import level_law_gate as K
import level_taper_reshape as AY

A_TAPER_LO, A_TAPER_HI = AY.A_TAPER_LO, AY.A_TAPER_HI
TOP = AY.TOP
# BREAKPOINT counts, so the families are (n + 1) segments: 2, 3, 4, 5, 6.
# ⚠ s173 added n = 1 (a 2-segment family).  It was absent, so the sweep could not report the
# simplest family the MASTER pot's own precedent uses -- and with the selection rule now taking
# the SMALLEST admissible family, a missing small family is a missing candidate, not just a
# missing row.  n = 5 remains the richest, i.e. the saturation control.
SEG_RANGE = (1, 2, 3, 4, 5)
N_STARTS = 60                     # multi-start, so a landed optimum is not an initialisation


# --------------------------------------------------------------------------------------------
# the PWL family -- the shape MASTER already ships (s146), generalised in segment count
# --------------------------------------------------------------------------------------------
def pwl(x, bs, fs):
    """L(x) for breakpoints bs (ascending in (0,1)) reaching fracs fs; L(0)=0 and L(1)=1 EXACTLY.

    Both endpoints are exact by construction and no parameter can move them -- which is what the
    topology requires (LEVEL min puts the wiper on VD; LEVEL max is the anchor -- ⛔ s189: NOT
    "bleed-free", s181's `blendEndStop` put e = 0.02418 of clean signal there)."""
    pts = [(0.0, 0.0)] + list(zip(bs, fs)) + [(1.0, 1.0)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return 1.0


def slopes_of(bs, fs):
    pts = [(0.0, 0.0)] + list(zip(bs, fs)) + [(1.0, 1.0)]
    return [(y1 - y0) / (x1 - x0) for (x0, y0), (x1, y1) in zip(pts, pts[1:])]


def valid(v, n):
    bs, fs = v[:n], v[n:]
    return (all(b > 1e-6 for b in bs) and all(a < b for a, b in zip(bs, bs[1:])) and bs[-1] < 1 - 1e-6
            and all(f > 1e-9 for f in fs) and all(a < b for a, b in zip(fs, fs[1:])) and fs[-1] < 1 - 1e-9)


# --------------------------------------------------------------------------------------------
# AZ1 -- the imported objective, and the known answer that it IS AY3's
# --------------------------------------------------------------------------------------------
def build_objective(report, ay, out):
    print("\n-- AZ1: the objective, imported from GATE AY, and the known answer that it is AY3's --")
    bands, caps = MG.load(report)[0], MG.load(report)[1]
    idx = [i for i, _b in enumerate(bands)]
    absfr, _silent = K.absolute_fr(caps, idx)
    groups = K.find_level_groups(caps)
    ladder = max(groups.values(), key=len)
    nonhf = [j for j, i in enumerate(idx) if bands[i] < K.HF_HZ]
    res = AY.ladder_re_top(absfr, ladder, nonhf)

    # ⭐⭐ THE detent -> L MAP MUST BE THE TAPER THE REPORT WAS **RENDERED** WITH, not the one
    # currently shipped, and the two are different the moment this gate's own output ships.  A
    # report's levels were produced by whatever curve was compiled in at render time; re-reading
    # them through a later curve silently mislabels every point on the horizontal axis.  So the
    # epoch is taken FROM GATE AY's stored report -- `taper_exp` if it predates s163, the stored
    # PWL otherwise -- which is what keeps this gate reproducible after the constants move.
    a1 = ay.get("ay1", {})
    if "taper_exp" in a1:
        p = K.power_taper(float(a1["taper_exp"]))
        print(f"    render epoch: the RETIRED power law, p = {float(a1['taper_exp'])} "
              f"(pre-s163 report)")
    elif "taper" in a1:
        params = tuple(float(v) for v in a1["taper"])
        p = lambda x, _q=params: K.level_taper(x, _q)
        print(f"    render epoch: segmented taper {tuple(round(v, 6) for v in params)}")
    else:
        sys.exit("GATE AZ1 FAIL: GATE AY's report records no taper, so the detent -> L map of the "
                 "epoch it was rendered in is unknown -- every point on this gate's horizontal "
                 "axis would be mislabelled")

    # Membership: the SAME usable-column rule AY3 applies, taken from AY's own helper so the two
    # cannot drift.  A column whose dB_model(L) is not monotone is not invertible and AY3 refuses
    # it; scoring it here would silently widen the objective.
    usable = [sw for sw in AY.SWEEPS
              if sw in res and np.all(np.diff(AY.build_dB_of_L(res, sw, ladder, p)[1]) > 0)]
    if not usable:
        sys.exit("GATE AZ1 FAIL: no stimulus column is invertible, so GATE AY's objective does "
                 "not exist on this report and nothing below can be scored")
    cache = {sw: AY.build_dB_of_L(res, sw, ladder, p) for sw in usable}

    # ⚠⚠ s189: MEMBERSHIP AND BASIS BOTH COME FROM AY, AND BOTH MOVED.  s181's end stop made the
    # L = 0 detent a real finite reading, so AY had to drop it from the log-L interpolation basis
    # (log 0 is not a number -- it was fabricating `required L = 0.0000` for the whole bottom
    # segment) and to score its three families over the detents the SOLVE could place.  This
    # scorer must use the same two, or AZ1's known answer -- "reproduce AY3's stored numbers" --
    # fails against two correct implementations of two different objectives.
    members = sorted(float(k) for k in ay["ay3"]["required_taper"])

    def score(curve, _cache=cache, _res=res, _members=members, _p=p):
        errs = []
        for sw in _cache:
            Ls, dB, _floor = _cache[sw]
            lo = np.log(Ls)
            for x in _members:
                if x <= 0.0 or x not in _res[sw]:
                    continue
                Lx = (_p(x) if curve is None else
                      (x ** curve) if np.isscalar(curve) else
                      curve(x) if callable(curve) else curve[x])
                errs.append(float(np.interp(math.log(max(Lx, 1e-12)), lo, dB)) - _res[sw][x][1])
        if not errs:
            sys.exit("GATE AZ1 FAIL: the objective scored ZERO errors (`empty-gate-must-fail`)")
        return (float(np.sqrt(np.mean(np.square(errs)))), float(np.max(np.abs(errs))), len(errs))

    xs = [x for x in members if x > 0.0]
    print(f"    ladder {len(ladder)} detents, {len(usable)} of {len(AY.SWEEPS)} stimulus columns "
          f"usable: {', '.join(s.replace('sweep_', '') for s in usable)}")
    return score, xs, p, out


def gate_az1(score, ay, out):
    """The known answer: this scorer must reproduce AY3's STORED numbers for all three families."""
    need = {float(k): v["mean"] for k, v in ay["ay3"]["required_taper"].items()}
    checks = [("taper as rendered", None, ay["ay3"]["shipped"]),
              ("best single exponent", ay["ay3"]["best_exp"]["exp"], ay["ay3"]["best_exp"]),
              ("free monotone curve", need, ay["ay3"]["free_curve"])]
    worst = 0.0
    print(f"    {'family':<24}{'rms here':>10}{'rms stored':>12}{'worst here':>12}{'worst stored':>14}")
    for label, arg, stored in checks:
        rms, wst, _n = score(arg)
        worst = max(worst, abs(rms - stored["rms"]), abs(wst - stored["worst"]))
        print(f"    {label:<24}{rms:10.4f}{stored['rms']:12.4f}{wst:12.4f}{stored['worst']:14.4f}")
    # A tolerance ABOVE float noise but far below anything that could change a verdict: these are
    # the same arithmetic on the same data, so they should agree to the last bit, and an
    # implementation difference shows up orders of magnitude above this.
    if not np.isfinite(worst) or worst > 1e-9:
        sys.exit(f"GATE AZ1 FAIL: the rebuilt objective does not reproduce GATE AY3's stored "
                 f"numbers (worst {worst:.3e}) -- it is scoring something else, so no family "
                 f"comparison below is licensed")
    print(f"    AZ1 OK  reproduces GATE AY3's three families to {worst:.2e} dB")
    out["az1"] = {"known_answer": worst, "ambiguity_rms_db": ay["ay3"]["ambiguity_rms_db"],
                  "free_curve_rms": ay["ay3"]["free_curve"]["rms"]}
    return need


# --------------------------------------------------------------------------------------------
# AZ2 -- the family sweep, with the saturation control
# --------------------------------------------------------------------------------------------
def fit_n(score, xs, n, need, seed=7):
    rng = np.random.default_rng(seed)

    def obj(v):
        if not valid(v, n):
            return 1e6
        bs, fs = list(v[:n]), list(v[n:])
        return score({x: pwl(x, bs, fs) for x in xs})[0]

    starts = []
    for _ in range(N_STARTS):
        starts.append(np.concatenate([np.sort(rng.uniform(0.10, 0.95, n)),
                                      np.sort(rng.uniform(0.01, 0.80, n))]))
    # plus starts seeded from the requirement itself, at evenly spaced detents
    ks = sorted(need)
    for off in range(3):
        pick = sorted({ks[min(len(ks) - 2, int(round((i + off * 0.3) * (len(ks) - 1) / (n + 1))))]
                       for i in range(1, n + 1)})
        if len(pick) == n:
            starts.append(np.array(pick + [need[b] for b in pick]))
    best, bestv = None, 1e9
    for x0 in starts:
        r = minimize(obj, x0, method="Nelder-Mead",
                     options={"xatol": 1e-12, "fatol": 1e-14, "maxiter": 40000, "maxfev": 40000})
        if float(r.fun) < bestv:
            bestv, best = float(r.fun), r.x
    if best is None or not np.isfinite(bestv):
        sys.exit(f"GATE AZ2 FAIL: the {n + 1}-segment fit did not converge from any of "
                 f"{len(starts)} starts -- a family that cannot be fitted cannot be compared")
    return list(best[:n]), list(best[n:]), bestv


def containment(fit, need, ay):
    """worst |fitted - required| / (that detent's own across-stimulus spread), anchor excluded.

    ⭐ s173: factored out of AZ3 so AZ2 can SELECT on it.  It was previously computed only for the
    family AZ2 had already chosen -- i.e. the one test this gate's own docstring calls "the
    overfitting test that matters, in the constant's own units" could describe the choice but
    never influence it.
    """
    spreads = {float(k): v["spread"] for k, v in ay["ay3"]["required_taper"].items()}
    worst = 0.0
    for x in sorted(need):
        sp = spreads.get(x, 0.0)
        if sp <= 0.0 or x >= TOP:        # the anchor is pinned on both sides: 0/0, not a violation
            continue
        worst = max(worst, abs(pwl(x, fit["breaks"], fit["fracs"]) - need[x]) / sp)
    return worst


def gate_az2(score, xs, need, ay, out):
    print("\n-- AZ2: the family sweep -- how many segments, decided by measurement --")
    amb = float(ay["ay3"]["ambiguity_rms_db"])
    floor = float(ay["ay3"]["free_curve"]["rms"])
    print(f"    Two imported bars, neither chosen here:")
    print(f"      the target's own across-stimulus ambiguity : {amb:.4f} dB rms  (AY2's spread)")
    print(f"      the free per-detent curve, i.e. the best ANY knob-keyed taper can do "
          f": {floor:.4f} dB rms")
    print(f"\n    {'family':<12}{'rms dB':>9}{'worst dB':>10}{'vs ambiguity':>16}{'vs floor':>10}"
          f"{'containment':>13}")
    fits = {}
    for n in SEG_RANGE:
        bs, fs, rms = fit_n(score, xs, n, need)
        wst = score({x: pwl(x, bs, fs) for x in xs})[1]
        fits[n + 1] = {"breaks": bs, "fracs": fs, "rms": rms, "worst": wst,
                       "slopes": slopes_of(bs, fs)}
        fits[n + 1]["containment"] = containment(fits[n + 1], need, ay)
        print(f"    {f'{n + 1}-segment':<12}{rms:9.4f}{wst:10.4f}"
              f"{('INSIDE' if rms <= amb else f'OUTSIDE {rms / amb:.2f}x'):>16}"
              f"{rms / floor:>9.2f}x{fits[n + 1]['containment']:>12.3f}"
              f"{'' if fits[n + 1]['containment'] <= 1.0 else ' !'}")

    # ---- the SATURATION control -----------------------------------------------------------
    # The stopping rule, and it is threshold-free: if the richest family returns the same
    # objective as the one below it, the family has saturated and the smaller one is not the
    # start of an overfitting slope -- it is the limit.  s146 could not run this on MASTER (its
    # richer family was a DIAGNOSTIC against a knob-noise floor); here the requirement is a
    # measured curve, so the control exists.
    ns = sorted(fits)
    gains = {b: fits[a]["rms"] - fits[b]["rms"] for a, b in zip(ns, ns[1:])}
    sat = [b for b, g in gains.items() if abs(g) < 1e-6]

    # ⛔⛔ s173 -- THE SELECTION RULE IS REBUILT, AND THE OLD ONE SHIPPED THE LARGEST FAMILY.
    # It was: saturate (|gain| < 1e-6) -> take the smallest family reaching that limit;
    # otherwise -> `max(n for n in ns if inside_ambiguity)`.  Two things wrong with that.
    #   (a) `1e-6 dB` is a GUESSED bar and it is at float-noise, not at any scale the requirement
    #       is measured on.  s163's 5-segment control happened to return EXACTLY 0.0000, so the
    #       test fired and nobody noticed it could not survive a merely-negligible gain.  On this
    #       epoch the marginal gains are +0.0012 and +0.0002 dB against a 1.213 dB ambiguity --
    #       obviously nothing, and comfortably above 1e-6.
    #   (b) and when it does not fire, the fallback ships the MOST COMPLEX family available.  A
    #       stopping rule whose failure mode is "pick the largest" is not a stopping rule; it is
    #       an overfitting rule with a guard in front of it.  It duly chose 6 segments (10
    #       constants) for +0.0014 dB over 4, on 7 measurable detents.
    # ⇒ the choice now uses only the TWO IMPORTED BARS, and takes the SMALLEST family that meets
    # both: inside the target's own across-stimulus ambiguity (AY2's spread, in dB of delivered
    # level) AND inside the requirement's own per-detent spread (AZ3's containment, in units of
    # L).  Saturation is REPORTED as a diagnostic and no longer decides anything, so no guessed
    # threshold sits in the decision path at all.
    inside = {n: bool(fits[n]["rms"] <= amb) for n in ns}
    contained = {n: bool(fits[n]["containment"] <= 1.0) for n in ns}
    print("\n    marginal gain per added segment (dB rms):")
    for b, g in gains.items():
        print(f"      -> {b}-segment : {g:+.4f}")
    if sat:
        print(f"    (the family saturates at {min(sat)} segments -- REPORTED, and it does not "
              f"decide\n      the choice: see the selection rule below.)")
    else:
        print("    (no exact saturation inside the swept range -- REPORTED, and it does not "
              "decide\n      the choice: see the selection rule below.)")

    print(f"\n    VERDICT, on the two imported bars:")
    print(f"      inside the ambiguity ({amb:.3f} dB rms) : "
          f"{', '.join(f'{n}-seg' for n in ns if inside[n]) or 'NONE'}")
    print(f"      inside the requirement's own spread     : "
          f"{', '.join(f'{n}-seg' for n in ns if contained[n]) or 'NONE'}")
    ok = [n for n in ns if inside[n] and contained[n]]
    if not ok:
        sys.exit(f"GATE AZ2 FAIL: NO family in the swept range is both inside the target's own "
                 f"ambiguity and inside its per-detent spread -- nothing here is shippable and "
                 f"GATE K's closure stands for this family too")
    chosen = min(ok)
    print(f"    ⇒ SHIP the SMALLEST family meeting BOTH: the {chosen}-SEGMENT curve -- "
          f"{fits[chosen]['rms']:.4f} dB rms,\n      {fits[chosen]['rms'] / floor:.2f}x the "
          f"free-curve reference, containment {fits[chosen]['containment']:.3f}.")
    richest = max(ok)
    if richest != chosen:
        print(f"      (the richest admissible family, {richest}-seg, buys "
              f"{fits[chosen]['rms'] - fits[richest]['rms']:+.4f} dB rms for "
              f"{2 * (richest - chosen)} more constants -- declined.)")
    out["az2"] = {"fits": {str(k): v for k, v in fits.items()}, "chosen": chosen,
                  "gains": {str(k): v for k, v in gains.items()},
                  "saturates_at": (min(sat) if sat else None), "inside_ambiguity": inside,
                  "contained": contained, "admissible": ok}
    return chosen, fits[chosen]


# --------------------------------------------------------------------------------------------
# AZ3 -- containment: the overfitting test, in the constant's own units
# --------------------------------------------------------------------------------------------
def gate_az3(fit, need, ay, out):
    print("\n-- AZ3: containment -- is the curve inside the REQUIREMENT's own per-detent spread? --")
    print("    This is the overfitting test that matters, and it is not a parameter count: AY3")
    print("    measured how well each required L is determined at all (its across-stimulus")
    print("    spread).  A curve inside that everywhere is reproducing a target measured better")
    print("    than it is being fitted.")
    spreads = {float(k): v["spread"] for k, v in ay["ay3"]["required_taper"].items()}
    print(f"    {'LEVEL':>7}{'required L':>12}{'fitted L':>10}{'|diff|':>9}{'spread':>9}{'':>6}")
    worst_ratio, rows = 0.0, {}
    for x in sorted(need):
        got = pwl(x, fit["breaks"], fit["fracs"])
        d = abs(got - need[x])
        sp = spreads.get(x, 0.0)
        # The anchor has spread 0 BY CONSTRUCTION (L(1) = 1 is pinned on both sides), so a ratio
        # there is 0/0 and is excluded rather than reported as an infinite violation.
        ratio = (d / sp) if (sp > 0.0 and x < TOP) else float("nan")
        if np.isfinite(ratio):
            worst_ratio = max(worst_ratio, ratio)
        rows[x] = {"required": need[x], "fitted": got, "diff": d, "spread": sp, "ratio": ratio}
        mark = "" if not np.isfinite(ratio) else ("  INSIDE" if ratio <= 1.0 else "  OUTSIDE")
        print(f"    {x:7.3f}{need[x]:12.4f}{got:10.4f}{d:9.4f}{sp:9.4f}{mark}")
    print(f"\n    worst |diff| / spread over the non-anchor detents: {worst_ratio:.3f}")
    if worst_ratio <= 1.0:
        print("    ⇒ INSIDE the requirement's own spread at EVERY detent — the curve is not")
        print("      fitting stimulus noise, it is reproducing the measured requirement.")
    else:
        print("    ⚠ OUTSIDE at one or more detents: the curve departs from the requirement by")
        print("      more than the requirement is determined, so the departure is the fit's, not")
        print("      the data's. Quote it with the detent.")
    out["az3"] = {"rows": {str(k): v for k, v in rows.items()}, "worst_ratio": worst_ratio,
                  "contained": bool(worst_ratio <= 1.0)}


# --------------------------------------------------------------------------------------------
# AZ4 -- the curve's own properties (nothing is fitted TO these)
# --------------------------------------------------------------------------------------------
def gate_az4(fit, p, out):
    print("\n-- AZ4: the curve's own shape -- none of it asked for by any term of the objective --")
    bs, fs, sl = fit["breaks"], fit["fracs"], fit["slopes"]
    xs = np.linspace(0.0, 1.0, 2001)
    Ls = np.array([pwl(float(x), bs, fs) for x in xs])
    mono = bool(np.all(np.diff(Ls) >= -1e-15))
    convex = all(a <= b + 1e-12 for a, b in zip(sl, sl[1:]))
    ends = (abs(pwl(0.0, bs, fs)) , abs(pwl(1.0, bs, fs) - 1.0))
    half, half_ship = pwl(0.5, bs, fs), p(0.5)
    print(f"    monotone in the knob            : {mono}")
    print(f"    endpoints exact                 : L(0) = {ends[0]:.1e}, |L(1) - 1| = {ends[1]:.1e}")
    print(f"    segment slopes (must RISE)      : {' -> '.join(f'{s:.3f}' for s in sl)}   "
          f"convex = {convex}")
    print(f"    half-rotation fraction          : {half * 100:.2f} %   "
          f"(shipped power law: {half_ship * 100:.2f} %)")
    band = f"{A_TAPER_LO * 100:.0f}-{A_TAPER_HI * 100:.0f} %"
    where = ("INSIDE" if A_TAPER_LO <= half <= A_TAPER_HI else
             ("BELOW" if half < A_TAPER_LO else "ABOVE"))
    print(f"    vs the textbook A-taper band ({band}) : {where}   "
          f"(shipped: {'INSIDE' if A_TAPER_LO <= half_ship <= A_TAPER_HI else 'ABOVE'})")
    moved = abs(half - 0.5 * (A_TAPER_LO + A_TAPER_HI)) < abs(half_ship - 0.5 * (A_TAPER_LO + A_TAPER_HI))
    print(f"    ⇒ the fitted curve moves the pot {'TOWARD' if moved else 'AWAY FROM'} the band "
          f"`circuit.md` specifies for VR2 (100k A).")
    print("      Nothing in the objective knows what an audio taper is, so this is outside")
    print("      corroboration — the same check s146 used for the MASTER pot.")
    if not mono:
        sys.exit("GATE AZ4 FAIL: the fitted curve is NOT monotone in the knob -- it is not a pot "
                 "taper at all, whatever its residual")
    if max(ends) > 1e-12:
        sys.exit(f"GATE AZ4 FAIL: an endpoint is not exact ({ends}) -- L(1) = 1 is the anchor "
                 f"anchor every absolute instrument in the project reads at")
    if not convex:
        print("    ⚠ NOT convex: the segment slopes do not rise monotonically, so this is not a")
        print("      physically-buildable resistive track shape. Reported, not fatal — the")
        print("      objective never asked for convexity and the requirement may not be convex.")
    out["az4"] = {"monotone": mono, "convex": convex, "endpoint_err": list(ends),
                  "half_rotation": half, "half_rotation_shipped": half_ship,
                  "in_band": bool(A_TAPER_LO <= half <= A_TAPER_HI), "moved_toward": bool(moved),
                  "slopes": sl}


# --------------------------------------------------------------------------------------------
# AZ5 -- the cost, priced before it ships
# --------------------------------------------------------------------------------------------
def gate_az5(fit, p, out):
    print("\n-- AZ5: the cost -- what this taper re-stales, as a number --")
    print("    `OdToneRestore`'s shipped mix law READS `LevelBlend::cleanFraction()` (s156), and")
    print("    that is a function of L. A taper change therefore moves the stage's own input, so")
    print("    the s156 fit goes stale BY CONSTRUCTION. AY5(a) priced the free curve at 0.1365;")
    print("    this is the same quantity for what actually ships.")
    rows, worst, worst_x = {}, 0.0, None
    print(f"    {'LEVEL':>7}{'L shipped':>11}{'L new':>9}{'cf shipped':>12}{'cf new':>9}{'Δcf':>9}")
    for x in [i / 8.0 for i in range(9)]:
        Lo = p(x)
        Ln = pwl(x, fit["breaks"], fit["fracs"])
        # BLEND = 1 (the OD-only knob position) is where the stage's own acceptance table is read.
        co, cn = K.coef_closed(1.0, Lo), K.coef_closed(1.0, Ln)
        cfo = co[1] / (co[0] + co[1]) if (co[0] + co[1]) > 0 else 1.0
        cfn = cn[1] / (cn[0] + cn[1]) if (cn[0] + cn[1]) > 0 else 1.0
        d = abs(cfn - cfo)
        if d > worst:
            worst, worst_x = d, x
        rows[x] = {"L_shipped": Lo, "L_new": Ln, "cf_shipped": cfo, "cf_new": cfn, "d": d}
        print(f"    {x:7.3f}{Lo:11.4f}{Ln:9.4f}{cfo:12.4f}{cfn:9.4f}{d:9.4f}")
    print(f"\n    worst |Δ cleanFraction| = {worst:.4f} at LEVEL {worst_x:.3f}")
    print("    ⇒ THE `OdToneRestore` MIX LAW MUST BE RE-CHECKED AFTER THIS SHIPS, across all five")
    print("      `--set` conditions. This is owed work, not a risk: it is what item 10 says.")
    out["az5"] = {"rows": {str(k): v for k, v in rows.items()}, "worst_dcf": worst,
                  "worst_at": worst_x}


# --------------------------------------------------------------------------------------------
# AZ6 -- what must NOT move
# --------------------------------------------------------------------------------------------
def gate_az6(fit, p, out):
    # ⛔ s189: "bleed-free" withdrawn throughout -- s181 put e = 0.02418 of clean at this corner.
    # The check itself is unchanged and still load-bearing: the anchor must be BIT-IDENTICAL,
    # because it is the detent every absolute instrument in the project reads at.
    print("\n-- AZ6: what must NOT move -- the ANCHOR corner (⛔ NOT bleed-free since s181) --")
    a_old, b_old = K.coef_closed(1.0, p(1.0))
    a_new, b_new = K.coef_closed(1.0, pwl(1.0, fit["breaks"], fit["fracs"]))
    print(f"    LEVEL = BLEND = max:  OD coef {a_old:.17g} -> {a_new:.17g}")
    print(f"                          clean   {b_old:.17g} -> {b_new:.17g}")
    if a_old != a_new or b_old != b_new:
        sys.exit("GATE AZ6 FAIL: the anchor corner MOVED. Every absolute instrument in the "
                 "project anchors there (GATE K7, GATE O's A3 ledger, GATE L's |rho|, "
                 "`OdToneRestore`'s base row, GATE W/AE's membership) -- a taper that moves it "
                 "invalidates all of them, and L(1) = 1 exists precisely to prevent this")
    print("    AZ6 OK  bit-identical, so every reading anchored at LEVEL max is untouched.")
    out["az6"] = {"od": a_new, "clean": b_new, "bit_identical": True}


def emit(fit, chosen, out):
    print("\n-- THE CONSTANTS, for src/dsp/FitParams.h + LevelBlend.h --")
    bs, fs = fit["breaks"], fit["fracs"]
    names = []
    for i, (b, f) in enumerate(zip(bs, fs), start=1):
        names.append((f"levelTaperBreak{i}", b))
        names.append((f"levelTaperFrac{i}", f))
    for n, v in names:
        print(f"    double {n} = {v:.6f};")
    print(f"    // {chosen}-segment PWL; L(0) = 0 and L(1) = 1 are EXACT by construction.")
    out["constants"] = {n: v for n, v in names}


def newest_ay_report():
    """Newest artefact on disk that is STRUCTURALLY a GATE AY report.  A structural test cannot go
    stale the way a filename does (s173's fix for the mutation runner, applied to this default)."""
    best, best_mt = None, -1.0
    for path in glob.glob("analysis/reports/*.json"):
        try:
            with open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
        except Exception:
            continue
        if isinstance(doc, dict) and {"ay1", "ay2", "ay3"} <= set(doc):
            mt = os.path.getmtime(path)
            if mt > best_mt:
                best, best_mt = path, mt
    # No fallback literal: a missing artefact must be a loud refusal in the gate's own reader, not
    # a default that silently names a file nobody rendered (`empty-gate-must-fail`).
    return best if best is not None else "analysis/reports/<no GATE AY report on disk>"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("report")
    # ⚠⚠ s189: this default was the transcribed literal `s162_level_taper.json`, four epochs
    # stale and no longer on disk -- the THIRD transcribed-filename rot in this tool family after
    # `_mutate_gate_ay.py`'s CURRENT (s173) and STALE (s189).  `analysis/reports/*.json` is
    # gitignored and regenerable, so ANY filename written into a default expires on its own.
    # Derived structurally instead: the newest artefact that IS a GATE AY report.
    ap.add_argument("--ay", default=newest_ay_report(),
                    help="GATE AY's stored report -- the source of the requirement AND of the "
                         "known answer this gate is licensed by (default: newest on disk)")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    out = {"report": args.report, "ay_report": args.ay}
    print(f"GATE AZ -- task D(b): fitting the shippable LEVEL taper   [{args.report}]")
    try:
        with open(args.ay, encoding="utf-8") as fh:
            ay = json.load(fh)
    except OSError as e:
        sys.exit(f"GATE AZ FAIL: cannot read GATE AY's report ({e}) -- the requirement and the "
                 f"known answer both live there; this gate does not re-derive either")
    for k in ("ay3",):
        if k not in ay:
            sys.exit(f"GATE AZ FAIL: {args.ay} has no {k!r} block -- it is not a GATE AY report")

    score, xs, p, out = build_objective(args.report, ay, out)
    need = gate_az1(score, ay, out)
    chosen, fit = gate_az2(score, xs, need, ay, out)
    gate_az3(fit, need, ay, out)
    gate_az4(fit, p, out)
    gate_az5(fit, p, out)
    gate_az6(fit, p, out)
    emit(fit, chosen, out)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, sort_keys=True, default=float)
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
