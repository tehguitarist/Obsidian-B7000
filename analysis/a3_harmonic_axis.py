#!/usr/bin/env python3.11
"""a3_harmonic_axis -- A3's OD-vs-clean balance measured on the HARMONIC axis.

Owed since session 75's next-step (a), re-listed by 76(c), 77(c), 78(d), 79(c), 80(c),
81(b), 82(b), 83(c) and 84(a)(ii).  Nine sessions.  This is that instrument.

WHY IT EXISTS, AND WHY IT IS NOT A RE-RUN OF THE BLEND AXIS
-----------------------------------------------------------
Session 75 item 3 found that `Hn/H1` measured at the OUTPUT is DILUTED by the clean
BLEND bleed: the bleed adds FUNDAMENTAL and no harmonics, so it lowers every Hn/H1 --
by a different amount on each side whenever the model's OD-vs-clean balance is wrong,
which is A3.  That was recorded as a DEFECT to be excluded (`--bleed-free`).  It is
also a MEASUREMENT, and this tool reads it as one.

The algebra is the whole instrument.  Let O(c) and C(c) be the OD and clean
contributions to the output FUNDAMENTAL at capture c, and rn = (Hn/H1) of the OD path
itself.  BLEND and LEVEL both sit AFTER every nonlinearity (circuit.md:
`...-> IC4_A SK -> LEVEL -> BLEND`), so rn is IDENTICAL at every point of a LEVEL or
BLEND ladder -- session 59 item 6's enabling fact.  Then

    Hn_out(c) = |O(c)| . rn                (the bleed contributes no harmonics)
    H1_out(c) = |O(c) + C(c)|
    R_n(c) := 20log10(Hn/H1) at the output = rn_dB  -  20log10|1 + C(c)/O(c)|

Sessions 59/60 established the bleed is EXACTLY ZERO at BLEND max AND LEVEL max (the
LEVEL wiper shorts to the OD source), so at that anchor C = 0 and R_n(anchor) = rn_dB.
Subtracting:

    ⭐  d(c) := R_n(anchor) - R_n(c)  =  20log10|1 + C(c)/O(c)|   FOR EVERY ORDER n

`d` is the fundamental DILUTION in dB.  Three properties make it worth a tool:

  1. **rn cancels.** `d` contains no statement about the nonlinearity at all -- so a
     model with the wrong harmonic structure and the right OD/clean balance reads
     d_mdl = d_ped.  This is the mirror image of `--bleed-free`, which throws the
     dilution away to see the harmonics; here we throw the harmonics away to see the
     dilution.
  2. **The post-BLEND chain cancels EXACTLY.** Every EQ band, the master divider, the
     output makeup and the report's per-capture gain-match are shared by the anchor and
     the cell and are frequency-shaping MULTIPLIERS applied identically to Hn and to H1
     in both -- so they leave `d` untouched.  No gain-match un-applying is needed here
     (unlike `a3_blend_axis.load_totals`, and unlike session 23's `grunt_span_probe`).
  3. ⭐⭐ **It carries NO HARMONIC-POWER BIAS, which every prior blend-axis number does.**
     Session 52 item 3(b) derived that `a3_blend_axis`'s `r = sqrt(|g1|^2 + H)` is an
     UPPER BOUND on the fundamental inflated by the band's harmonic power, biasing its
     `theta` toward 90 degrees, and that caveat has ridden on `r_ped`/`s_blend` ever
     since (sessions 51 item 7, 52 item 3b, 54 item 8).  `d` is built from H1 and Hn as
     SEPARATE narrowband estimates, so the harmonic power is never summed into the
     fundamental.  This is the fundamental-only measurement that caveat asked for.

  ⇒ `Delta_d(c) = d_ped(c) - d_mdl(c)` is A3's OD-vs-clean balance error at knob
    position c, measured with NO solve, NO taper fit, NO b0 estimate, NO bleed model,
    and NO model of the nonlinearity.  Positive Delta_d = the pedal dilutes MORE than
    the model = the model's OD sits too HIGH relative to its own bleed.

⚠⚠ WHAT IT DOES *NOT* SEPARATE, AND THIS IS THE STANDING LIMITATION.
`d(c)` is indexed by KNOB POSITION, and the pedal's tapers are known to differ from the
model's: the BLEND taper is measurably non-linear (session 51 item 4: effective B =
0.212 / 0.482 / 0.739 at knob 0.25 / 0.50 / 0.75) and the LEVEL taper exponent measures
~1.90 against the shipped 2.25 (session 54 item 7).  So a per-cell `Delta_d` mixes
TAPER CONFORMITY with the OD/clean balance.  The two are distinguishable by SHAPE, not
by one number: a balance error is a roughly CONSTANT offset in `Delta_d` across a
ladder, a taper error is a term that vanishes at both ladder ends (at B = 1 the wiper
IS pin3 and at B = 0 the OD is out of circuit, so both endpoints are taper-immune --
session 51 item 4).  Both are printed; the endpoint-vs-interior split is the read.

⚠ AND THE ANCHOR IS A PREMISE, NOT A MEASUREMENT.  "Bleed is exactly zero at BLEND max
AND LEVEL max" comes from `LevelBlend`'s topology (an ideal pot).  Session 60 item 2
BOUNDED the real residual instead of trusting it: a real bleed cannot exceed the
deepest |G| in the set, which bounds worst-case dilution at the anchor at <= 0.87 dB,
and -- load-bearing -- a residual bleed at the anchor makes `d` an UNDER-estimate on
BOTH sides, so it cannot manufacture a `Delta_d`.

USAGE
    python3.11 analysis/a3_harmonic_axis.py --selftest
    python3.11 analysis/a3_harmonic_axis.py [REPORT.json] [--out reports/x.json]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# ⚠ `eq_reference` prints its whole ~80-line diagnostic report at MODULE level with no
# `if __name__ == "__main__"` guard (known wart, session 56 -- NOT fixed there because it is
# a shared oracle with 7+ importers).  Swallowed locally, as `attack_c8_screen.py` does.
_stdout = sys.stdout
try:
    sys.stdout = open(os.devnull, "w")
    import eq_reference as EQ  # noqa: E402  (level_blend_tf -- the model's own mixing law)
finally:
    sys.stdout.close()
    sys.stdout = _stdout

ORDERS = ["H2", "H3", "H4", "H5", "H6", "H7"]
EVEN = ["H2", "H4", "H6"]
ODD = ["H3", "H5", "H7"]
ANCHOR_HZ = (100.0, 200.0, 400.0)     # comprehensive_report.THD_ANCHORS -- one definition
# ⚠⚠ `ANCHOR_HZ` is used as a POSITIONAL INDEX into each record's `harmonics[sweep][order]
# [side][bi]` arrays (`for bi, hz in enumerate(ANCHOR_HZ)`).  So it is not a label -- it is a
# claim about the SHAPE of a JSON written by a different tool, on a different day, and nothing
# checked it.  The report already stores its own `thd_anchors` (comprehensive_report writes it),
# so the check is free; `assert_anchors_match` below spends it.  Session 88.
DEFAULT_REPORT = "analysis/reports/s74_baseline129.json"

REF_FLOOR_DB = -60.0        # matrix_harmonics.DEFAULT_FLOOR -- one definition, not a new threshold
TAKE_FLOOR_DB = 0.144       # measured pedal take-to-take (session 24)
# `d` is a DIFFERENCE of two dB ratios, each itself a difference of two dB numbers, so
# its floor is the take-to-take floor scaled by the propagation: sqrt(2) per difference.
D_FLOOR_DB = TAKE_FLOOR_DB * 2.0                     # 0.288 dB
SPREAD_GATE_DB = 3.0        # order-to-order spread above which a cell is NOT a measurement
MIN_ORDERS = 3              # a `d` from fewer orders has no usable order-independence check
LEVEL_TAPER_EXP = 2.25      # FitParams::levelTaperExp (shipped) -- a3_blend_axis.LEVEL_TAPER_EXP
LOW_ORDERS = ["H2", "H3"]   # last to reach the capture's own noise -- the robust subset
HIGH_ORDERS = ["H6", "H7"]  # first to floor, so the flooring signature lives in LOW - HIGH
INFEASIBLE = float("nan")

# Settings fields that define the OPERATING POINT of the OD path.  A ladder group holds
# these fixed and varies only `blend`/`level`, which sit after every nonlinearity.
GROUP_FIELDS = ("drive", "attackIdx", "gruntIdx", "master", "lo", "loMid", "hiMid", "hi",
                "loMidFreq", "hiMidFreq", "distEngage", "gainSessionDb")


# ----------------------------------------------------------------------------- loading
def is_od(fname: str) -> bool:
    """matrix_grade.is_od / matrix_harmonics.is_od -- one definition."""
    return ("base-od" in fname) or fname.startswith("ref-od")


def assert_anchors_match(report: dict):
    """Fail LOUDLY if the report's anchors are not the ones this tool indexes with.

    Why this is not paranoia.  Extending `comprehensive_report.THD_ANCHORS` to reach below
    100 Hz -- session 87's next-step (b), and measurable per `lf_anchor_gate` -- changes
    every record's `harmonics[...][bi]` arrays from 3 entries to N.  Read with a stale
    3-entry `ANCHOR_HZ` the tool would index bands 0,1,2 of a DIFFERENT list and report
    numbers for the wrong frequencies, with no exception and no shape error, because the
    arrays are merely longer.  The reverse (new constant, old report) IndexErrors, which is
    the lucky direction.

    ⚠ And the cache makes the silent direction the LIKELY one: `_cache_key` does not hash
    the anchors (measured, `lf_anchor_gate` GATE 0c), so a re-run without `--no-cache`
    returns OLD 3-anchor records under a NEW 5-anchor constant.  That is precisely the
    mixed state this guard exists to refuse.

    Returns the report's anchors so a caller can index by them rather than by the constant.
    """
    # ⚠ It lives under `meta`, not at the top level.  The first draft of this guard read
    # `report["thd_anchors"]`, got None on EVERY real report, and fell through to the
    # "cannot verify" branch below -- printing a warning that reads as diligence while
    # checking nothing.  Caught only by mutation-testing the guard (session 80 item 4a:
    # a control that cannot fail is not a control).  Both paths are probed in --selftest.
    got = (report.get("meta") or {}).get("thd_anchors", report.get("thd_anchors"))
    if got is None:
        # Reports written before the field existed: cannot verify, so say so rather than
        # assume agreement (an unverifiable check must not read as a pass).
        print("  ⚠ report has no `thd_anchors` field -- anchor alignment NOT verified; "
              f"proceeding on the module constant {ANCHOR_HZ}")
        return tuple(float(h) for h in ANCHOR_HZ)
    got_t = tuple(float(h) for h in got)
    if got_t != tuple(float(h) for h in ANCHOR_HZ):
        raise SystemExit(
            f"⛔ ANCHOR MISMATCH — this tool indexes {tuple(float(h) for h in ANCHOR_HZ)} "
            f"but the report was written with {got_t}.\n"
            "   `bi` is a positional index, so proceeding would silently report the wrong "
            "bands.\n"
            "   Fix: set a3_harmonic_axis.ANCHOR_HZ = comprehensive_report.THD_ANCHORS and "
            "re-render the report with --no-cache (the cache key does NOT hash the anchors).")
    return got_t


def load_groups(report: dict, skip_gain_n12: bool = True):
    """-> {group_key: {"anchor": rec, "cells": [rec, ...], "settings": {...}}}

    A `rec` is (file, settings, harmonics).  Groups without a BLEND-max/LEVEL-max anchor
    are returned too, flagged, so the count of what had to be dropped is printed rather
    than silently vanishing.
    """
    groups: dict[tuple, dict] = {}
    for c in report["captures"]:
        f = c["file"]
        if not is_od(f):
            continue
        if skip_gain_n12 and "gain-n12" in f:
            continue
        s = c.get("settings") or {}
        har = c.get("harmonics") or {}
        if not har:
            continue
        key = tuple(s.get(k) for k in GROUP_FIELDS)
        g = groups.setdefault(key, {"anchor": None, "cells": [], "no_od": [], "settings": s})
        rec = (f, s, har)
        if s.get("blend") == 1.0 and s.get("level") == 1.0:
            g["anchor"] = rec
        elif s.get("blend") == 0.0 or s.get("level") == 0.0:
            # ⚠⚠ THE OD PATH IS OUT OF CIRCUIT, so `d` is INFINITE by construction and the
            # model duly returns +141 .. +363 dB.  `matrix_harmonics.no_od_path_rows` has
            # excluded these since session 75 item 2 and this tool did not, first pass:
            # they dragged one group's median to -110 dB and the pooled MEAN to -11.05
            # against a median of -4.30.  Excluded on the CONDITION, decidable before any
            # number is read -- never on the measured value (session 74 item 6).
            g["no_od"].append(rec)
        else:
            g["cells"].append(rec)
    return groups


def group_label(key: tuple) -> str:
    d = dict(zip(GROUP_FIELDS, key))
    parts = [f"D{d['drive']:.2f}"]
    if d["attackIdx"]:
        parts.append(f"atk{d['attackIdx']}")
    if d["gruntIdx"]:
        parts.append(f"grn{d['gruntIdx']}")
    for k in ("master", "lo", "loMid", "hiMid", "hi"):
        if d[k] != 0.5:
            parts.append(f"{k}{d[k]:.2f}")
    return " ".join(parts)


# ------------------------------------------------------------------------ the statistic
def dilution_cell(anchor_har, cell_har, sweep, bi, side, ref_har=None,
                  floor=REF_FLOOR_DB, orders=ORDERS):
    """`d` at one (sweep, band) from all measurable orders.

    `side` is "pedal_db" or "plugin_db".  The floor guard reads `ref_har` (the REFERENCE
    side) when given, so BOTH sides are masked on the SAME cells -- otherwise the two
    `d` estimates are computed over different order sets and their difference is not a
    paired quantity (`aggregate-moved-check-membership-first`, one level down).

    Returns (d_median, spread, n, per_order dict).  `spread` = max - min over the
    surviving orders and is the instrument's own validity test: `d` is
    ORDER-INDEPENDENT by construction, so a large spread means the premise failed
    (rn moved along the ladder, or an Hn is floor-limited), not that `d` is large.
    """
    per = {}
    guard = ref_har if ref_har is not None else anchor_har
    for o in orders:
        if o not in anchor_har.get(sweep, {}) or o not in cell_har.get(sweep, {}):
            continue
        ga = guard[0][sweep][o]["pedal_db"][bi] if ref_har is not None else anchor_har[sweep][o][side][bi]
        gc = guard[1][sweep][o]["pedal_db"][bi] if ref_har is not None else cell_har[sweep][o][side][bi]
        if not (np.isfinite(ga) and np.isfinite(gc) and ga > floor and gc > floor):
            continue
        a = anchor_har[sweep][o][side][bi]
        c = cell_har[sweep][o][side][bi]
        if not (np.isfinite(a) and np.isfinite(c)):
            continue
        per[o] = float(a - c)
    if not per:
        return float("nan"), float("nan"), 0, per
    v = np.asarray(list(per.values()), dtype=float)
    return float(np.median(v)), float(v.max() - v.min()), len(v), per


def parity_split(per: dict):
    """(d_even, d_odd) medians -- a sharper order-independence test than the spread.

    The evens and odds are the two halves the authority split already separates
    (`reference-sources.md` §1), and they are produced by different terms of the
    nonlinearity.  If `d` really contains no statement about the nonlinearity, the two
    halves must agree; if they do not, `d` is contaminated by something order-dependent.
    """
    e = [per[o] for o in EVEN if o in per]
    d = [per[o] for o in ODD if o in per]
    return (float(np.median(e)) if e else float("nan"),
            float(np.median(d)) if d else float("nan"))


def magnitude_split(per: dict):
    """(d_low, d_high) from H2/H3 vs H6/H7 -- ⭐⭐ THE FLOORING DISCRIMINATOR.

    A harmonic near the capture's own noise reads too HIGH, so `Hn/H1` at the diluted
    cell reads too HIGH and that order's `d` reads too LOW.  The HIGH orders sit 20-40 dB
    below the low ones, so they reach the noise FIRST -- meaning a flooring artefact has a
    specific, checkable signature: `d(low) > d(high)`, growing with dilution.

    ⚠ This is an ORDER-based split, not a VALUE-based one, which is why it is the right
    test: guarding on the pedal's own `Hn/H1` at the cell would select away exactly the
    large-dilution cells under test (`self-selecting-scores`), whereas the order index is
    fixed in advance and cannot be chosen by the outcome.
    """
    lo = [per[o] for o in LOW_ORDERS if o in per]
    hi = [per[o] for o in HIGH_ORDERS if o in per]
    return (float(np.median(lo)) if lo else float("nan"),
            float(np.median(hi)) if hi else float("nan"))


def mix_ratio(d_db: float) -> float:
    """|C/O| from d = 20log10|1 + C/O|, under an IN-PHASE reduction (|1+z| -> 1+|z|).

    ⚠ STATED, NOT HIDDEN: C/O is complex, so this is exact only when its phase is small.
    It is used only to PARAMETERISE the balance error below; the fit is scored on `d`
    itself, so a bad reduction shows up as a residual over the 30 dB dilution range
    rather than as a silently wrong number.
    """
    return 10.0 ** (d_db / 20.0) - 1.0


def predict_from_balance(d_mdl_db: float, k_db: float) -> float:
    """The pedal's `d` if its OD/clean balance differs from the model's by a CONSTANT k dB.

    ⭐⭐ WHY THIS FUNCTION IS THE POINT.  `d` is a log-modulus, so a constant multiplicative
    balance error does NOT produce a constant Delta_d:

        small d:  d ~ 8.686 . |C/O|      =>  Delta_d ~ (k_lin - 1) . d_mdl   (PROPORTIONAL)
        large d:  d -> 20log10|C/O|      =>  Delta_d -> k_db                 (SATURATES)

    So Delta_d GROWING with dilution and then flattening is the SIGNATURE OF A CONSTANT
    BALANCE ERROR, not evidence of an artefact.  The first draft of this tool printed
    "a swing comparable to the effect means the effect is the artefact" above exactly that
    shape -- a narrated verdict contradicting the algebra of its own statistic
    (`computed-verdicts-not-narrated`).  Fitting ONE k across the whole 0-30 dB range and
    reporting the residual replaces the narration with a test: 4+ bins against 1 parameter.
    """
    m = mix_ratio(d_mdl_db) * (10.0 ** (k_db / 20.0))
    return 20.0 * math.log10(1.0 + m) if m > -1.0 else float("nan")


def fit_balance(pairs):
    """One k (dB) over (d_mdl, d_ped) pairs.  Returns (k_db, rms_dB, n).

    Median-of-absolute objective would be more robust but is not differentiable; a coarse
    grid plus bisection on a 1-D convex-in-practice cost is enough and has no branch to
    jump.  The residual is what makes this a TEST rather than a re-description.
    """
    pts = [(m, p) for m, p in pairs if np.isfinite(m) and np.isfinite(p) and m > 0.0]
    if len(pts) < 3:
        return float("nan"), float("nan"), len(pts)

    def cost(k):
        r = [predict_from_balance(m, k) - p for m, p in pts]
        r = [x for x in r if np.isfinite(x)]
        return float(np.median(np.abs(r))) if r else 1e9

    ks = np.linspace(-24.0, 24.0, 481)
    cs = [cost(k) for k in ks]
    k0 = float(ks[int(np.argmin(cs))])
    step = 0.1
    best = cost(k0)
    for _ in range(50):
        moved = False
        for dk in (step, -step):
            c = cost(k0 + dk)
            if c < best:
                best, k0, moved = c, k0 + dk, True
        if not moved:
            step *= 0.5
            if step < 1e-4:
                break
    res = [predict_from_balance(m, k0) - p for m, p in pts]
    res = np.asarray([x for x in res if np.isfinite(x)])
    return float(k0), float(np.sqrt(np.mean(res ** 2))), len(pts)


def floor_signature(per: dict, anchor_har, sweep, bi, side="pedal_db"):
    """Rank correlation of d(order) against that order's OWN level at the anchor.

    If flooring is operating, the orders with the least headroom give the smallest `d`,
    so d(order) correlates POSITIVELY with rn(order).  Returned as a Spearman rho over
    however many orders survived (nan under 3).  Computed, not asserted.
    """
    os_ = [o for o in per if o in anchor_har.get(sweep, {})]
    if len(os_) < 3:
        return float("nan")
    rn = np.asarray([anchor_har[sweep][o][side][bi] for o in os_], dtype=float)
    dd = np.asarray([per[o] for o in os_], dtype=float)
    if not (np.isfinite(rn).all() and np.isfinite(dd).all()):
        return float("nan")
    ra = np.argsort(np.argsort(rn)).astype(float)
    rb = np.argsort(np.argsort(dd)).astype(float)
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


# ------------------------------------------------------------------ the model's own law
def model_coeffs(level: float, blend: float, p: float = LEVEL_TAPER_EXP):
    """(a, b) = the model's OD and clean coefficients at this knob pair, EXACTLY.

    `level_blend_tf` is linear in (vo, vc), so superposition gives the two coefficients
    from two evaluations.  This is `LevelBlendTest`'s own analytic oracle -- not a fit.
    """
    a = EQ.level_blend_tf(level, blend, vo=1.0, vc=0.0, p=p)
    b = EQ.level_blend_tf(level, blend, vo=0.0, vc=1.0, p=p)
    return float(a), float(b)


def predict_d(rho: complex, level: float, blend: float, p: float = LEVEL_TAPER_EXP) -> float:
    """d = 20log10|1 + (b/a).rho|, rho = clean_1/OD_1 at the top of the LEVEL pot."""
    a, b = model_coeffs(level, blend, p)
    if a <= 0.0:
        return float("nan")
    return 20.0 * math.log10(abs(1.0 + (b / a) * rho))


def fit_rho(cells, p: float = LEVEL_TAPER_EXP):
    """Fit the ONE complex ratio rho that reproduces `d` at every ladder point.

    `b/a` is a known REAL positive number at each knob pair, so `1 + (b/a).rho` traces a
    straight line in the complex plane and `d` is its log-modulus -- the same geometry
    `a3_blend_axis` exploits, driven by harmonics instead of levels.  Two real unknowns
    against len(cells) equations, so >= 3 points leaves spare equations that TEST the
    mixing law rather than assume it.

    Returns (rho, rms_residual_dB, per_point_residuals).  Coarse grid then local polish,
    because a 2-D log-modulus objective is not convex near a cancellation (session 47
    item 11's lesson: global search first, refinement second).
    """
    pts = [(lv, bl, d) for (lv, bl, d) in cells if np.isfinite(d)]
    if len(pts) < 3:
        return None, float("nan"), []

    def cost(re, im):
        r = complex(re, im)
        s = 0.0
        for lv, bl, d in pts:
            q = predict_d(r, lv, bl, p)
            if not np.isfinite(q):
                return 1e9
            s += (q - d) ** 2
        return s / len(pts)

    best, bre, bim = 1e18, 0.0, 0.0
    for re in np.linspace(-8.0, 8.0, 161):
        for im in np.linspace(-8.0, 8.0, 161):
            c = cost(re, im)
            if c < best:
                best, bre, bim = c, re, im
    step = 0.1
    for _ in range(60):
        improved = False
        for dre, dim in ((step, 0), (-step, 0), (0, step), (0, -step),
                         (step, step), (-step, -step), (step, -step), (-step, step)):
            c = cost(bre + dre, bim + dim)
            if c < best:
                best, bre, bim, improved = c, bre + dre, bim + dim, True
        if not improved:
            step *= 0.5
            if step < 1e-7:
                break
    rho = complex(bre, bim)
    res = [predict_d(rho, lv, bl, p) - d for lv, bl, d in pts]
    # ⚠⚠ THE SEARCH SENTINEL MUST NOT BE RETURNED AS A RESIDUAL.  `cost` returns 1e9 for
    # an unrepresentable point, so a failed fit came back as sqrt(1e9) = 31622.777 dB and
    # the first run printed that as the p90 and max "law residual" -- a REFUSAL dressed as
    # a measurement (session 40 item 2's `need = +24.00` sentinel, one tool over).  Report
    # infeasibility as infeasibility and count it.
    rms = float(math.sqrt(best))
    if not np.isfinite(rms) or rms > 1e4:
        return None, INFEASIBLE, []
    return rho, rms, res


# ------------------------------------------------------------------------------- gates
def selftest() -> bool:
    ok = True
    print("SELFTEST")

    # GATE 1 -- RECOVERY.  Synthesise Hn/H1 from a known rn and a known dilution and
    # check `d` comes back exactly.  rn is deliberately WILD across orders (30 dB span)
    # so a tool that accidentally leaked rn into `d` cannot pass.
    rng = np.random.default_rng(7)
    rn = {o: float(rng.uniform(-70, -10)) for o in ORDERS}
    for true_d in (0.0, 0.5, 3.0, 12.0):
        anchor = {"s": {o: {"pedal_db": [rn[o]] * 3, "plugin_db": [rn[o]] * 3} for o in ORDERS}}
        cell = {"s": {o: {"pedal_db": [rn[o] - true_d] * 3, "plugin_db": [rn[o] - true_d] * 3}
                      for o in ORDERS}}
        d, sp, n, _ = dilution_cell(anchor, cell, "s", 0, "pedal_db", floor=-200.0)
        bad = abs(d - true_d) > 1e-12 or sp > 1e-12 or n != 6
        ok &= not bad
        print(f"  GATE 1 recovery  true d={true_d:6.2f}  ->  {d:8.5f}  spread {sp:.2e}  n={n}   "
              f"{'FAIL' if bad else 'PASS'}")

    # GATE 2 -- LIVENESS of the order-independence test.  A dilution that is NOT
    # order-independent (i.e. rn really did move along the ladder) must show up as
    # spread, and the parity split must separate a parity-dependent contamination.
    # Without this the spread gate could be vacuous.
    off = {"H2": 4.0, "H4": 4.0, "H6": 4.0, "H3": 0.0, "H5": 0.0, "H7": 0.0}
    anchor = {"s": {o: {"pedal_db": [rn[o]] * 3, "plugin_db": [rn[o]] * 3} for o in ORDERS}}
    cell = {"s": {o: {"pedal_db": [rn[o] - 2.0 - off[o]] * 3,
                      "plugin_db": [rn[o] - 2.0 - off[o]] * 3} for o in ORDERS}}
    d, sp, n, per = dilution_cell(anchor, cell, "s", 0, "pedal_db", floor=-200.0)
    de, do = parity_split(per)
    bad = not (sp > 3.9 and abs(de - do - 4.0) < 1e-9)
    ok &= not bad
    print(f"  GATE 2 liveness  parity-split contamination: spread {sp:.3f} dB, "
          f"even {de:+.3f} vs odd {do:+.3f}   {'FAIL' if bad else 'PASS'}")

    # GATE 3 -- THE MODEL'S OWN LAW, against a KNOWN answer.  Generate `d` at the real
    # ladder knob positions from a chosen rho through `level_blend_tf`, then recover rho.
    # This is the only gate that exercises `model_coeffs`/`fit_rho`, and it fails if the
    # superposition split, the taper, or the objective is wrong.
    for true_rho in (complex(0.9, 0.0), complex(2.5, -1.2)):
        knobs = [(0.125, 1.0), (0.25, 1.0), (0.375, 1.0), (0.5, 1.0), (0.625, 1.0),
                 (0.75, 1.0), (0.875, 1.0), (0.5, 0.25), (0.5, 0.5), (0.5, 0.75)]
        cells = [(lv, bl, predict_d(true_rho, lv, bl)) for lv, bl in knobs]
        rho, rms, _ = fit_rho(cells)
        err = abs(rho - true_rho) if rho is not None else 9e9
        bad = rms > 1e-3 or err > 1e-3
        ok &= not bad
        print(f"  GATE 3 law recovery  rho {true_rho} -> {rho}  |err| {err:.2e}  "
              f"rms {rms:.2e} dB   {'FAIL' if bad else 'PASS'}")

    # GATE 4 -- THE LAW IS DISCRIMINATING.  A wrong LEVEL taper must NOT fit `d` as well
    # as the right one, or the law test would pass for anything and the pedal-side
    # residual would mean nothing.
    knobs = [(lv, 1.0) for lv in (0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875)]
    cells = [(lv, bl, predict_d(complex(1.5, 0.0), lv, bl, p=2.25)) for lv, bl in knobs]
    _, rms_right, _ = fit_rho(cells, p=2.25)
    _, rms_wrong, _ = fit_rho(cells, p=1.20)
    bad = not (rms_wrong > 10.0 * max(rms_right, 1e-9) and rms_wrong > D_FLOOR_DB)
    ok &= not bad
    print(f"  GATE 4 law discriminates  correct taper rms {rms_right:.2e} dB vs "
          f"wrong taper {rms_wrong:.4f} dB   {'FAIL' if bad else 'PASS'}")

    # GATE 5 -- THE ANCHOR PREMISE'S SIGN.  A residual bleed at the anchor must make `d`
    # an UNDER-estimate on BOTH sides (session 60 item 2), i.e. it cannot manufacture a
    # Delta_d.  Checked numerically rather than argued: shrink the anchor's own
    # dilution-free assumption and confirm every `d` moves DOWN.
    rho = complex(1.5, 0.0)
    d_true = predict_d(rho, 0.5, 1.0)
    d_leaky = predict_d(rho, 0.5, 1.0) - predict_d(rho, 1.0, 0.999)
    bad = not (d_leaky < d_true)
    ok &= not bad
    print(f"  GATE 5 anchor leak is one-signed  clean {d_true:.4f} -> leaky "
          f"{d_leaky:.4f} dB (must fall)   {'FAIL' if bad else 'PASS'}")

    # GATE 6 -- THE BALANCE FIT MUST RECOVER ITS OWN k, AND MUST REFUSE A WRONG SHAPE.
    # Without the recovery half the residual is unreadable (session 77 item 1's lesson: a
    # family that cannot recover its own parameters makes a large residual meaningless).
    # Without the refusal half the fit would "explain" anything and k would mean nothing.
    for true_k in (-6.0, -2.0, +3.5):
        dm = [0.5, 1.0, 2.0, 3.5, 5.0, 8.0, 12.0, 20.0, 30.0, 40.0]
        pairs = [(m, predict_from_balance(m, true_k)) for m in dm]
        k, rms, n = fit_balance(pairs)
        bad = abs(k - true_k) > 0.05 or rms > 0.05
        ok &= not bad
        print(f"  GATE 6 balance recovery  true k={true_k:+5.1f} -> {k:+6.2f} dB  "
              f"rms {rms:.4f} dB (n={n})   {'FAIL' if bad else 'PASS'}")
    # A CONSTANT Delta (which is what an artefact-free naive reading assumes) is NOT of
    # this family, so the fit must leave a large residual on it rather than absorbing it.
    pairs = [(m, m - 6.0) for m in (0.5, 1.0, 2.0, 3.5, 5.0, 8.0, 12.0, 20.0, 30.0, 40.0)]
    _, rms_bad, _ = fit_balance(pairs)
    bad = not (np.isfinite(rms_bad) and rms_bad > 2.0)
    ok &= not bad
    print(f"  GATE 6b fit REFUSES a constant-Delta shape  rms {rms_bad:.2f} dB "
          f"(must be >> {D_FLOOR_DB:.2f})   {'FAIL' if bad else 'PASS'}")

    print("  ->", "PASS" if ok else "FAIL")
    return ok


# -------------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("report", nargs="?", default=DEFAULT_REPORT)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--sweep", default=None, help="restrict to one sweep level")
    ap.add_argument("--out", default=None)
    ap.add_argument("--floor", type=float, default=REF_FLOOR_DB)
    ap.add_argument("--spread-gate", type=float, default=SPREAD_GATE_DB)
    args = ap.parse_args()

    if args.selftest:
        return 0 if selftest() else 1

    if not selftest():
        print("\n⛔ SELFTEST FAILED -- refusing to report numbers.")
        return 1
    print()

    with open(args.report) as fh:
        rep = json.load(fh)
    assert_anchors_match(rep)          # `bi` is positional -- verify BEFORE reading any band
    groups = load_groups(rep)
    usable = {k: v for k, v in groups.items() if v["anchor"] and v["cells"]}
    dropped = {k: v for k, v in groups.items() if k not in usable}
    print(f"REPORT {args.report}   {len(rep['captures'])} captures")
    print(f"  groups with a BLEND-max/LEVEL-max anchor AND >=1 diluted cell: {len(usable)}")
    print(f"  groups dropped (no anchor, or anchor only): {len(dropped)}")
    for k, v in sorted(dropped.items(), key=lambda kv: group_label(kv[0])):
        why = "no bleed-free anchor" if not v["anchor"] else "anchor but no diluted cell"
        print(f"    - {group_label(k):28s} {why}  ({len(v['cells'])} cells)")

    sweeps = sorted({sw for v in usable.values() for sw in v["anchor"][2]})
    if args.sweep:
        sweeps = [s for s in sweeps if s == args.sweep]

    n_no_od = sum(len(v["no_od"]) for v in groups.values())
    print(f"  cells EXCLUDED because the OD path is out of circuit (BLEND=0 or LEVEL=0): "
          f"{n_no_od}")
    print("    -- `d` is infinite by construction there; the model returns +141 .. +363 dB.")

    rows, thin = [], 0
    for key, g in sorted(usable.items(), key=lambda kv: group_label(kv[0])):
        af, asx, ahar = g["anchor"]
        for cf, cs, char in sorted(g["cells"]):
            for sw in sweeps:
                if sw not in ahar or sw not in char:
                    continue
                for bi, hz in enumerate(ANCHOR_HZ):
                    ref = ({sw: ahar[sw]}, {sw: char[sw]})
                    dp, spp, np_, perp = dilution_cell(ahar, char, sw, bi, "pedal_db",
                                                       ref_har=ref, floor=args.floor)
                    dm, spm, nm, perm = dilution_cell(ahar, char, sw, bi, "plugin_db",
                                                      ref_har=ref, floor=args.floor)
                    # ⚠ A `d` from fewer than MIN_ORDERS orders has a spread of 0.00 over
                    # one value, which READS AS A PERFECT PASS on the order-independence
                    # gate while carrying no check at all -- the same construction that
                    # made session 80's odd-order control vacuous.  Such cells do not vote.
                    if np_ < MIN_ORDERS:
                        thin += 1
                        continue
                    pe, po = parity_split(perp)
                    me, mo = parity_split(perm)
                    plo, phi = magnitude_split(perp)
                    mlo, mhi = magnitude_split(perm)
                    rows.append(dict(
                        group=group_label(key), file=cf, sweep=sw, hz=hz,
                        level=cs.get("level"), blend=cs.get("blend"),
                        d_ped=dp, d_mdl=dm, delta=dp - dm,
                        spread_ped=spp, spread_mdl=spm, n=np_, n_mdl=nm,
                        ped_even=pe, ped_odd=po, mdl_even=me, mdl_odd=mo,
                        ped_lo=plo, ped_hi=phi, mdl_lo=mlo, mdl_hi=mhi,
                        delta_lo=(plo - mlo) if np.isfinite(plo) and np.isfinite(mlo) else float("nan"),
                        rho_s=floor_signature(perp, ahar, sw, bi),
                    ))

    if not rows:
        print("\n⛔ no measurable cells.")
        return 1

    print(f"  cells dropped for fewer than {MIN_ORDERS} measurable orders: {thin}")
    print(f"\n{len(rows)} (group, cell, sweep, band) measurements, "
          f"{len({(r['group'], r['file']) for r in rows})} distinct diluted captures\n")

    # ---- GATE A: ORDER-INDEPENDENCE.  The instrument's own validity test.
    sp = np.asarray([r["spread_ped"] for r in rows])
    spm = np.asarray([r["spread_mdl"] for r in rows])
    par = np.asarray([r["ped_even"] - r["ped_odd"] for r in rows
                      if np.isfinite(r["ped_even"]) and np.isfinite(r["ped_odd"])])
    good = sp <= args.spread_gate
    print("GATE A  ORDER-INDEPENDENCE (the premise: `d` must be the same at every order)")
    print(f"  pedal order-to-order spread   median {np.median(sp):5.2f}  p90 "
          f"{np.percentile(sp, 90):5.2f}  max {sp.max():5.2f} dB")
    print(f"  model order-to-order spread   median {np.median(spm):5.2f}  p90 "
          f"{np.percentile(spm, 90):5.2f}  max {spm.max():5.2f} dB")
    print(f"  pedal EVEN-minus-ODD `d`      median {np.median(par):+5.2f}  "
          f"10-90 {np.percentile(par, 10):+5.2f} .. {np.percentile(par, 90):+5.2f} dB")
    print(f"  cells within the {args.spread_gate:.1f} dB spread gate: {int(good.sum())} of "
          f"{len(rows)} ({100.0 * good.mean():.0f} %)")
    verdict_a = ("PASS -- `d` behaves as an order-independent quantity"
                 if np.median(sp) <= args.spread_gate and abs(np.median(par)) <= args.spread_gate
                 else "CHECK -- `d` is NOT order-independent; the premise does not hold here")
    print(f"  => {verdict_a}")
    print("  ⭐ the MODEL's spread is ~0 while the PEDAL's is not, so this is a property of "
          "the CAPTURES,")
    print("     not of the extraction -- which is what GATE A2 exists to identify.")

    # ---- GATE A2: THE FLOORING ARTEFACT.  Its direction is the SAME as the finding's, so
    # it has to be measured, not argued away.  A pedal harmonic near the capture's own
    # noise reads too HIGH => Hn/H1 at the cell too high => that order's `d` too LOW =>
    # Delta too NEGATIVE.  Every group's Delta below is negative, so this is not optional.
    lo = np.asarray([r["ped_lo"] for r in rows if np.isfinite(r["ped_lo"])])
    hi = np.asarray([r["ped_hi"] for r in rows if np.isfinite(r["ped_hi"])])
    both = np.asarray([r["ped_lo"] - r["ped_hi"] for r in rows
                       if np.isfinite(r["ped_lo"]) and np.isfinite(r["ped_hi"])])
    mboth = np.asarray([r["mdl_lo"] - r["mdl_hi"] for r in rows
                        if np.isfinite(r["mdl_lo"]) and np.isfinite(r["mdl_hi"])])
    rs = np.asarray([r["rho_s"] for r in rows if np.isfinite(r["rho_s"])])
    print("\nGATE A2  IS THE SPREAD THE PEDAL'S OWN NOISE FLOOR?  (H2/H3 vs H6/H7)")
    print(f"  pedal  d(H2,H3) median {np.median(lo):6.2f}   d(H6,H7) median "
          f"{np.median(hi):6.2f} dB")
    print(f"  pedal  d(low) - d(high)   median {np.median(both):+6.2f}  10-90 "
          f"{np.percentile(both, 10):+6.2f} .. {np.percentile(both, 90):+6.2f} dB   (n={len(both)})")
    print(f"  MODEL  d(low) - d(high)   median {np.median(mboth):+6.2f}  10-90 "
          f"{np.percentile(mboth, 10):+6.2f} .. {np.percentile(mboth, 90):+6.2f} dB   "
          f"(n={len(mboth)})  <- the CONTROL")
    print(f"  Spearman rho of d(order) vs that order's own anchor level: median "
          f"{np.median(rs):+.3f}  (n={len(rs)})")
    print("     positive => the orders with least headroom give the smallest `d` = the "
          "flooring signature")
    fl = bool(np.median(both) > args.spread_gate / 2.0 or np.median(rs) > 0.3)
    if fl:
        print("  => FLOORING IS OPERATING -- quote the LOW-ORDER (H2/H3) statistic, "
              "not the pooled one")
    else:
        print("  => no flooring signature; all six orders may be pooled")

    # ---- GATE B: MONOTONICITY.  More OD (higher B or L) must mean LESS dilution.
    viol, tot = 0, 0
    for grp in sorted({r["group"] for r in rows}):
        for sw in sweeps:
            for hz in ANCHOR_HZ:
                for axis, other in (("level", "blend"), ("blend", "level")):
                    sub = [r for r in rows if r["group"] == grp and r["sweep"] == sw
                           and r["hz"] == hz and r[other] == 1.0 and np.isfinite(r["d_ped"])]
                    sub.sort(key=lambda r: r[axis])
                    if len(sub) < 3:
                        continue
                    v = [r["d_ped"] for r in sub]
                    tot += 1
                    if any(v[i + 1] > v[i] + D_FLOOR_DB for i in range(len(v) - 1)):
                        viol += 1
    print("\nGATE B  MONOTONICITY (dilution must FALL as the knob adds OD)")
    if tot:
        print(f"  ladders with >=3 points: {tot}   violating by more than the "
              f"{D_FLOOR_DB:.3f} dB floor: {viol}")
        print(f"  => {'PASS' if viol == 0 else 'CHECK'}")
    else:
        print("  no ladder had >= 3 points on one axis -- not tested")

    # ---- THE RESULT.  Per group, endpoint-vs-interior split (the taper discriminator).
    print("\nTHE RESULT -- `d` = fundamental dilution in dB;  Delta = pedal - model")
    print("  (Delta > 0  =>  the pedal dilutes MORE  =>  the model's OD sits too HIGH "
          "vs its own bleed)\n")
    hdr = f"  {'group':22s} {'capture':46s} {'B':>5s} {'L':>5s} {'d_ped':>7s} {'d_mdl':>7s} {'Delta':>7s} {'spr':>5s}"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for grp in sorted({r["group"] for r in rows}):
        sub = [r for r in rows if r["group"] == grp and np.isfinite(r["delta"])]
        if not sub:
            continue
        byfile = {}
        for r in sub:
            byfile.setdefault(r["file"], []).append(r)
        for f in sorted(byfile):
            rr = byfile[f]
            dp = np.median([x["d_ped"] for x in rr])
            dm = np.median([x["d_mdl"] for x in rr])
            spx = np.median([x["spread_ped"] for x in rr])
            print(f"  {grp:22s} {f[:46]:46s} {rr[0]['blend']:5.2f} {rr[0]['level']:5.2f} "
                  f"{dp:7.2f} {dm:7.2f} {dp - dm:+7.2f} {spx:5.2f}")

    # ---- HEADLINE, split by whether the taper can contribute.
    print("\nHEADLINE -- Delta_d pooled, split by whether a TAPER error can contribute")
    fin = [r for r in rows if np.isfinite(r["delta"]) and r["spread_ped"] <= args.spread_gate]
    lad = [r for r in fin if not (r["blend"] == 1.0 and r["level"] == 1.0)]
    # A knob at an END of its own travel is taper-immune (session 51 item 4).  On these
    # ladders the only interior knob is the one being swept, so "endpoint" means the
    # swept knob is at 0 or 1 -- which for a diluted cell can only be BLEND = 0 (no OD
    # path) so there is no taper-immune diluted cell.  What IS available is the
    # DISTINCTION between the two ladders, whose tapers are different and independently
    # measured, so agreement between them is evidence the balance term dominates.
    for name, sel in (("LEVEL ladder (blend = 1)", lambda r: r["blend"] == 1.0),
                      ("BLEND ladder (level = 0.5)", lambda r: r["blend"] != 1.0)):
        s = [r["delta"] for r in lad if sel(r)]
        if not s:
            continue
        a = np.asarray(s)
        print(f"  {name:28s} n={len(a):4d}  median {np.median(a):+6.2f}  mean "
              f"{a.mean():+6.2f}  10-90 {np.percentile(a, 10):+6.2f} .. "
              f"{np.percentile(a, 90):+6.2f} dB")
    allx = np.asarray([r["delta"] for r in lad])
    print(f"  {'ALL diluted cells':28s} n={len(allx):4d}  median {np.median(allx):+6.2f}  "
          f"mean {allx.mean():+6.2f}  10-90 {np.percentile(allx, 10):+6.2f} .. "
          f"{np.percentile(allx, 90):+6.2f} dB")
    rob = np.asarray([r["delta_lo"] for r in lad if np.isfinite(r["delta_lo"])])
    print(f"  {'ROBUST: H2/H3 only':28s} n={len(rob):4d}  median {np.median(rob):+6.2f}  "
          f"mean {rob.mean():+6.2f}  10-90 {np.percentile(rob, 10):+6.2f} .. "
          f"{np.percentile(rob, 90):+6.2f} dB")

    # ---- ⭐⭐ THE CONDITIONING AXIS.  Binned on the MODEL's `d`, which is exact and
    # noise-free, so the binning coordinate cannot itself be chosen by the pedal's noise
    # (`self-selecting-scores`).  A flooring artefact GROWS with dilution; a genuine
    # balance error does not.  This is the read that decides whether Delta is a finding.
    print("\n⭐ Delta vs DILUTION -- binned on the MODEL's own exact `d`, so the binning")
    print("  coordinate carries none of the pedal's noise.  An ARTEFACT grows with "
          "dilution; a")
    print("  real balance error does not.")
    print(f"  {'model d bin':>16s} {'n':>4s} {'Delta(all)':>11s} {'Delta(H2/H3)':>13s} "
          f"{'spread_ped':>11s}")
    edges = [0.0, 5.0, 10.0, 20.0, 1e9]
    trend = []
    for i in range(len(edges) - 1):
        s = [r for r in lad if edges[i] <= r["d_mdl"] < edges[i + 1]]
        if not s:
            continue
        a = np.asarray([r["delta"] for r in s])
        b = np.asarray([r["delta_lo"] for r in s if np.isfinite(r["delta_lo"])])
        sx = np.asarray([r["spread_ped"] for r in s])
        hi_lbl = "inf" if edges[i + 1] > 1e8 else f"{edges[i + 1]:.0f}"
        print(f"  {f'{edges[i]:.0f}-{hi_lbl} dB':>16s} {len(a):4d} {np.median(a):+11.2f} "
              f"{(np.median(b) if len(b) else float('nan')):+13.2f} {np.median(sx):11.2f}")
        trend.append((np.median(a), np.median(b) if len(b) else float("nan")))
    if len(trend) >= 2:
        swing_all = max(t[0] for t in trend) - min(t[0] for t in trend)
        print(f"  observed swing across the bins: {swing_all:.2f} dB against an effect of "
              f"{np.median(allx):+.2f} dB")

    # ---- ⭐⭐ THE TEST THAT DECIDES IT: ONE constant balance error, over-determined.
    # `predict_from_balance`'s docstring has the algebra -- a CONSTANT multiplicative
    # balance error must make Delta_d proportional to d at small dilution and saturate at
    # the balance error itself at large dilution.  So the trend above is a PREDICTION to
    # be tested, not a confound to be excluded.  One parameter, 4 bins + 110 cells.
    pairs = [(r["d_mdl"], r["d_ped"]) for r in lad]
    k, rms, nk = fit_balance(pairs)
    print("\n⭐⭐ ONE CONSTANT BALANCE ERROR, FITTED ACROSS THE WHOLE DILUTION RANGE")
    print(f"  k = {k:+.2f} dB   rms residual {rms:.2f} dB   over n={nk} cells "
          f"spanning d_mdl {min(p[0] for p in pairs):.1f} .. "
          f"{max(p[0] for p in pairs):.1f} dB")
    print(f"  {'model d bin':>16s} {'n':>4s} {'observed':>9s} {'predicted':>10s} {'resid':>7s}")
    for i in range(len(edges) - 1):
        s = [r for r in lad if edges[i] <= r["d_mdl"] < edges[i + 1]]
        if not s:
            continue
        obs = float(np.median([r["delta"] for r in s]))
        pre = float(np.median([predict_from_balance(r["d_mdl"], k) - r["d_mdl"] for r in s]))
        hi_lbl = "inf" if edges[i + 1] > 1e8 else f"{edges[i + 1]:.0f}"
        print(f"  {f'{edges[i]:.0f}-{hi_lbl} dB':>16s} {len(s):4d} {obs:+9.2f} {pre:+10.2f} "
              f"{obs - pre:+7.2f}")
    ok_k = np.isfinite(rms) and rms < 2.0
    print(f"  => {'the trend IS a constant balance error' if ok_k else 'ONE k does NOT explain the trend'}"
          f" -- 1 parameter, 4 bins, {nk} cells, residual {rms:.2f} dB")

    sign = ("the pedal's OD sits LOWER vs its own bleed than the model's"
            if k > 0 else "the model's OD sits too LOW vs its own bleed, i.e. A3's known direction")
    if abs(k) <= D_FLOOR_DB:
        print(f"  => |k| {abs(k):.3f} dB is AT OR UNDER the {D_FLOOR_DB:.3f} dB propagated "
              f"take-to-take floor -- NO A3 error detectable on this axis")
    else:
        print(f"  => k = {k:+.2f} dB: {sign}")
    print(f"  ⚠ the POOLED Delta ({np.median(allx):+.2f} dB) is NOT this number and must not be "
          f"quoted as it --")
    print("    it is a mixture over dilution depths, so it UNDER-reads |k| by construction.")

    # ---- PER-BAND, since A3 is a curve and one number would hide its shape.
    print("\nPER BAND -- A3's CURVE on this axis (k, not the pooled Delta: see above)")
    band_k = {}
    for hz in ANCHOR_HZ:
        s = [r for r in lad if r["hz"] == hz]
        if len(s) < 3:
            continue
        kb, rb, nb = fit_balance([(r["d_mdl"], r["d_ped"]) for r in s])
        band_k[hz] = (kb, rb, nb)
        dd = np.asarray([r["delta"] for r in s])
        print(f"  {hz:6.0f} Hz   n={nb:4d}  k {kb:+6.2f} dB  rms {rb:5.2f}   "
              f"(pooled Delta median {np.median(dd):+6.2f})")

    # ---- PER DRIVE, because the OD/clean balance is drive-dependent by construction.
    print("\nPER GROUP (operating point)")
    for grp in sorted({r["group"] for r in lad}):
        s = [r for r in lad if r["group"] == grp]
        dd = np.asarray([r["delta"] for r in s])
        if len(s) >= 3:
            kg, rg, ng = fit_balance([(r["d_mdl"], r["d_ped"]) for r in s])
            print(f"  {grp:22s} n={ng:4d}  k {kg:+6.2f} dB  rms {rg:5.2f}   "
                  f"(pooled Delta median {np.median(dd):+6.2f})")
        else:
            print(f"  {grp:22s} n={len(s):4d}  -- too few cells to fit k   "
                  f"(pooled Delta median {np.median(dd):+6.2f})")

    # ---- ⭐ CROSS-CHECK: DOES THIS INSTRUMENT INDEPENDENTLY SEE THE KNOWN ATTACK GAP?
    # Sessions 57/60 established that the pedal's ATTACK-BOOST throw delivers a broadband
    # ~+8.6 dB into the OD path where the modelled ladder delivers ~0 (magnitude-inert to
    # <= 0.08 dB, session 56 item 2), and that the gap is LEVEL-DEPENDENT on boost and
    # level-INVARIANT on cut (session 57 item 3).  A hotter pedal OD dilutes LESS, so that
    # gap must appear here as EXTRA negative k on the atk1 groups, shrinking with drive as
    # the clipper compresses it.  Neither prediction was used in building this tool.
    print("\n⭐ CROSS-CHECK -- the known ATTACK gap, which this tool was not built to see")
    kk = {}
    for grp in sorted({r["group"] for r in lad}):
        s = [r for r in lad if r["group"] == grp]
        if len(s) >= 3:
            kk[grp] = fit_balance([(r["d_mdl"], r["d_ped"]) for r in s])[0]
    print(f"  {'drive':>7s} {'default k':>10s} {'atk BOOST k':>12s} {'excess':>8s} "
          f"{'atk CUT k':>10s} {'excess':>8s}")
    for dv in ("D0.00", "D0.50", "D1.00"):
        base = kk.get(f"{dv} grn1")
        b = kk.get(f"{dv} atk1 grn1")
        c = kk.get(f"{dv} atk2 grn1")
        def f2(x):
            return f"{x:+10.2f}" if x is not None else f"{'--':>10s}"
        eb = f"{b - base:+8.2f}" if (b is not None and base is not None) else f"{'--':>8s}"
        ec = f"{c - base:+8.2f}" if (c is not None and base is not None) else f"{'--':>8s}"
        print(f"  {dv:>7s} {f2(base)} {f2(b):>12s} {eb} {f2(c)} {ec}")
    print("  => a BOOST excess that is negative and shrinks with drive, with CUT much "
          "smaller, is the")
    print("     signature sessions 57/60 predict.  `--` = that group had < 3 usable cells "
          "(drive min is")
    print("     the thin end here: weak harmonics put most of its cells under the "
          "reference floor).")

    # ---- GATE C: THE MODEL'S OWN MIXING LAW, fitted to the model's own `d`.
    # This is a KNOWN-ANSWER check on the whole extraction: the model's law is exactly
    # `level_blend_tf`, so if `d_mdl` is being read correctly it must be reproducible by
    # ONE complex ratio per (group, sweep, band) with a residual at the numerical floor.
    print("\nGATE C  THE MODEL'S OWN MIXING LAW (known law, one free complex ratio)")
    law = []
    for grp in sorted({r["group"] for r in rows}):
        for sw in sweeps:
            for hz in ANCHOR_HZ:
                sub = [r for r in rows if r["group"] == grp and r["sweep"] == sw
                       and r["hz"] == hz and np.isfinite(r["d_mdl"])]
                if len(sub) < 3:
                    continue
                cells = [(r["level"], r["blend"], r["d_mdl"]) for r in sub]
                rho, rms, _ = fit_rho(cells)
                subp = [r for r in sub if np.isfinite(r["d_ped"])]
                rhop, rmsp, _ = (fit_rho([(r["level"], r["blend"], r["d_ped"]) for r in subp])
                                 if len(subp) >= 3 else (None, float("nan"), []))
                law.append(dict(group=grp, sweep=sw, hz=hz, n=len(sub),
                                rho_mdl=abs(rho) if rho else float("nan"), rms_mdl=rms,
                                rho_ped=abs(rhop) if rhop else float("nan"), rms_ped=rmsp))
    if law:
        rm = np.asarray([x["rms_mdl"] for x in law if np.isfinite(x["rms_mdl"])])
        rp = np.asarray([x["rms_ped"] for x in law if np.isfinite(x["rms_ped"])])
        print(f"  fits: {len(law)}  (>=3 ladder points each, so >=1 spare equation)   "
              f"INFEASIBLE: model {len(law) - len(rm)}, pedal {len(law) - len(rp)}")
        print(f"  MODEL law residual   median {np.median(rm):.3f}  p90 "
              f"{np.percentile(rm, 90):.3f}  max {rm.max():.3f} dB")
        if len(rp):
            print(f"  PEDAL law residual   median {np.median(rp):.3f}  p90 "
                  f"{np.percentile(rp, 90):.3f}  max {rp.max():.3f} dB")
        print(f"  => MODEL {'PASS' if np.median(rm) < D_FLOOR_DB else 'CHECK'} "
              f"(floor {D_FLOOR_DB:.3f} dB) -- this is a KNOWN-ANSWER check on the "
              f"extraction, not a result")
        print("  ⚠ the PEDAL residual is NOT the same kind of number: it is fitted with "
              "the MODEL's tapers,\n     which are measurably wrong (sessions 51/54), so a "
              "non-zero residual there is expected\n     and is a taper statement, not a "
              "balance statement.")
        print(f"\n  |rho| = |clean_1 / OD_1| at the top of the LEVEL pot, in dB "
              f"(-20log10|G| in `a3_blend_axis`'s notation):")
        print(f"  {'group':22s} {'sweep':16s} {'Hz':>5s} {'n':>3s} {'mdl':>8s} {'ped':>8s} {'ped-mdl':>8s}")
        for x in law:
            if not (np.isfinite(x["rho_mdl"]) and np.isfinite(x["rho_ped"])):
                continue
            m = 20.0 * math.log10(max(x["rho_mdl"], 1e-12))
            p = 20.0 * math.log10(max(x["rho_ped"], 1e-12))
            print(f"  {x['group']:22s} {x['sweep']:16s} {x['hz']:5.0f} {x['n']:3d} "
                  f"{m:8.2f} {p:8.2f} {p - m:+8.2f}")
    else:
        print("  no group had >= 3 ladder points -- law not tested")

    print("\n⚠ NOT CLAIMED")
    print("  * `pedal_db` is the NEURAL DSP capture, not hardware "
          "(`reference-sources.md`).  A3 is a")
    print("    LINEAR-path / mixing quantity, and per §1 ND tracks hardware to <= 1.4 dB "
          "there, so the")
    print("    captures DO have authority over this statistic -- unlike the even-order "
          "harmonic ones.")
    print("  * `d` is indexed by KNOB POSITION and the pedal's tapers differ from the "
          "model's, so a")
    print("    per-cell Delta mixes taper conformity with the OD/clean balance.  The "
          "two-ladder split")
    print("    above is the discriminator, not a single number.")
    print("  * The anchor's zero-bleed premise is TOPOLOGICAL, bounded at <= 0.87 dB "
          "(session 60 item 2)")
    print("    and one-signed (GATE 5), so it cannot manufacture a Delta.")

    if args.out:
        with open(args.out, "w") as fh:
            json.dump(dict(report=args.report, rows=rows, law=law,
                           floor=args.floor, spread_gate=args.spread_gate,
                           d_floor_db=D_FLOOR_DB), fh, indent=1)
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
