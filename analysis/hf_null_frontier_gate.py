#!/usr/bin/env python3.11
"""GATE BS — item 17's TREBLE half: the joint frontier, measured ACROSS SETTINGS.  Session 195.

WHY A NEW GATE RATHER THAN MORE ARMS ON GATE BH
-----------------------------------------------
GATE BH (s178, repaired s195) establishes the two axes and that its SIX discrete arms are in
tension.  "Six arms are in tension" is not "the family cannot do it" — s126's rule is that a
dose-response LOCUS refutes a lever, and BH never swept one.  This gate sweeps the family.

⛔⛔ AND IT CORRECTS BH4's STATISTIC, WHICH IS WHY THE FRONTIER LOOKS DIFFERENT FROM BH5's.
BH4 grades the centre as the MEDIAN of the signed ratio `f0_model / f0_pedal`.  Measured per
condition on the current epoch that ratio CHANGES SIGN ACROSS GRUNT:

    GRUNT cut   0.853 .. 0.958   (the model's null is BELOW ND's)
    GRUNT flat  1.044            (ABOVE)
    GRUNT boost 1.091 .. 1.106   (ABOVE)

so a median over the pool cancels one against the other and reads 0.958 — a number no condition
has.  `unsigned-aggregates-have-no-sign` in its other direction: here the SIGNED aggregate is the
flattering one.  This gate grades **median |1 - ratio|**, prints the signed column beside it, and
splits BOTH by GRUNT.  ⇒ never quote a centre "ratio" for this feature without its GRUNT split.

WHAT THE SWEEP IS AGAINST, AND WHY THE ANSWER IS NOT A TUNING
-------------------------------------------------------------
Measured at the playing rung, the MODEL's null centre is 5393 / 5393 / 5393 / 5472 / 5472 / 5472 /
5881 / 5393 / 5165 Hz over the nine readable conditions — a 13.9 % span that is almost entirely one
outlier — while ND's runs 4946 .. 6414 Hz and MOVES with both GRUNT (5881 cut / 5165 flat / 4946
boost at DRIVE 0.5) and DRIVE (5714 -> 5881 -> 6414 at cut).  ⇒ the model's HF null is PINNED and
ND's is not: open item 6's signature, on a fourth axis after position, depth and slope.

A pinned feature cannot be put on a moving target by any fixed correction, so the honest question
this gate asks is not "which candidate lands on 1.000" but **"what is the best the family can do on
both axes at once, and is any point DOMINATING?"**

Run:
    /opt/homebrew/bin/python3.11 analysis/hf_null_frontier_gate.py
    /opt/homebrew/bin/python3.11 analysis/hf_null_frontier_gate.py --json analysis/reports/s195_hf_frontier.json
"""
import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import captures as C                      # noqa: E402
import hf_null_shape_gate as BH           # noqa: E402
import od_tone_restore_fit as F           # noqa: E402

BH.REN_DIR = "build/s195_hf_frontier"     # PRIVATE — never GATE W's read-only s122 cache

RUNGS = BH.RUNGS
PLAY = BH.PLAYING_RUNG
FEAT = BH.ORDER_GRADED                    # treble_notch

# ⛔⛔ `SHIP` IS AN EXPLICIT `--fit`, NOT THE COMPILED DEFAULTS, AND THAT IS LOAD-BEARING.
# This gate's baseline is the PRE-s195 build, where the mix-keyed HF peak node was SHARED across
# GRUNT.  s195 shipped `odMakeupHfPeakDbNonCut = 0.0`, so compiled defaults ARE this gate's own
# winning candidate — leaving the baseline as `()` would silently re-point it and every row would
# then be measured against the thing being proposed (`verify-the-BASELINE-not-its-LABEL`, s37).
# Setting the non-Cut node back to the Cut value reproduces the pre-s195 stage exactly.
SHIP = ("--fit", "odMakeupHfPeakDbNonCut=3.3")
SHIPPED_NOW = ()                          # what the plugin currently runs — printed, not baseline
NOHF = BH.HF_OFF                          # the family's own far endpoint

# ---- the condition set, BALANCED ON GRUNT ------------------------------------------------------
# ⛔⛔ GATE BH's ten conditions are 7 cut / 1 flat / 2 boost, and the centre error CHANGES SIGN
# across GRUNT — so any pooled centre statistic on that set is 70 % a GRUNT-cut statistic wearing a
# pooled name.  That is `aggregate-moved-check-membership-first` on the axis this item turns out to
# live on.  ⭐ The captures to fix it were already on disk and unread (`check-for-unread-data-first`,
# 8th occurrence): the SAME (DRIVE x BLEND x LEVEL) shapes exist at all three GRUNT positions.
#
# Each row is one SHAPE, given at all three positions.  `None` = that (shape, GRUNT) capture does
# not exist, and it is NAMED rather than silently dropped — capture access is ending (s111), so it
# is a permanent bound, not a to-do.
SHAPES = [
    # (shape label,           cut,                              flat,                                   boost)
    ("drv0.0 lvl.5 bl1",  "drive-0700_base-od.wav",         "drive-0700_grunt-flat_base-od.wav",       "drive-0700_grunt-boost_base-od.wav"),
    ("drv0.25 lvl.5 bl1", "drive-0930_base-od.wav",         "drive-0930_grunt-flat_base-od.wav",       "drive-0930_grunt-boost_base-od.wav"),
    ("drv0.5 lvl.5 bl1",  "ref-od.wav",                     "grunt-flat_base-od.wav",                  "grunt-boost_base-od.wav"),
    ("drv1.0 lvl.5 bl1",  "drive-1700_base-od.wav",         None,                                      "drive-1700_grunt-boost_base-od.wav"),
    ("drv0.5 lvl.5 bl.75", "blend-1430_base-od.wav",        "grunt-flat_blend-1430_base-od.wav",       "grunt-boost_blend-1430_base-od.wav"),
    ("drv0.5 lvl.5 bl.5", "blend-1200_base-od.wav",         "grunt-flat_blend-1200_base-od.wav",       "grunt-boost_blend-1200_base-od.wav"),
    ("drv0.5 lvl.5 bl.25", "blend-0930_base-od.wav",        "grunt-flat_blend-0930_base-od.wav",       "grunt-boost_blend-0930_base-od.wav"),
    ("drv0.5 lvl1 bl1",   "level-1700_base-od.wav",         "level-1700_grunt-flat_base-od.wav",       "level-1700_grunt-boost_base-od.wav"),
    ("drv0.0 lvl1 bl1",   "drive-0700_level-1700_base-od.wav", "drive-0700_level-1700_grunt-flat_base-od.wav", "drive-0700_level-1700_grunt-boost_base-od.wav"),
    ("drv1.0 lvl1 bl1",   "drive-1700_level-1700_base-od.wav", "drive-1700_level-1700_grunt-flat_base-od.wav", "drive-1700_level-1700_grunt-boost_base-od.wav"),
]
GRUNTS = ("cut", "flat", "boost")


def conditions():
    out = []
    for i, (shape, *caps) in enumerate(SHAPES):
        for gr, cap in zip(GRUNTS, caps):
            if cap is not None:
                out.append((f"{shape} | {gr}", cap, gr, shape))
    return out


def die(tag, msg):
    print(f"\n⛔ {tag}: {msg}")
    sys.exit(1)


# ---- the family ---------------------------------------------------------------------------------
def hf(scale=1.0, hz=None, q=None, peak=None, at_od=None, at_clean=None):
    """One point of the mix-keyed HF peak's own family.

    `scale` multiplies ALL THREE mix nodes together, which is the only way to move the term's size
    without also re-shaping its cf law — the two are different questions and conflating them is
    how a 'gain sweep' silently becomes a re-fit.

    ⛔⛔ THE PEAK NODE IS SET UNDER **BOTH** NAMES.  Since s195 `odMakeupHfPeakDb` reaches the DSP
    at GRUNT = Cut only, so an arm that sets it alone would be INERT at flat and boost — the exact
    s194 defect (`--fit odMakeupLowCutDb` silently a no-op at Cut for seven sessions), re-armed on
    the constant this gate exists to study.  A GRUNT-keyed candidate is expressed through
    `armfor()` instead, by giving each position its own arm."""
    p = BH.shipped_makeup("cut")
    a = []
    for name, key, override in (("odMakeupHfAtOdDb", "hfAtOdDb", at_od),
                                ("odMakeupHfPeakDb", "hfPeakDb", peak),
                                ("odMakeupHfPeakDbNonCut", "hfPeakDb", peak),
                                ("odMakeupHfAtCleanDb", "hfAtCleanDb", at_clean)):
        v = p[key] * scale if override is None else override
        a += ["--fit", f"{name}={v:.6g}"]
    if hz is not None:
        a += ["--fit", f"odMakeupHfHz={hz:.6g}"]
    if q is not None:
        a += ["--fit", f"odMakeupHfQ={q:.6g}"]
    return tuple(a)


def shelf(hz=None, cut=None):
    a = []
    if hz is not None:
        a += ["--fit", f"odMakeupHighHz={hz:.6g}"]
    if cut is not None:
        a += ["--fit", f"odMakeupHighCutDb={cut:.6g}"]
    return tuple(a)


# ================================================================================================
def armfor(arm, grunt):
    """A candidate is either ONE `--fit` tuple or a {grunt: tuple} map.

    ⭐ A GRUNT-KEYED candidate needs no `src/` change to EVALUATE: the conditions are already
    partitioned by switch position, so rendering each position with its own arm reproduces exactly
    what `PedalChain::syncGruntKeyedOd()` would do — the s187 pattern, measured before it is built."""
    # tuple() so a candidate that has been round-tripped through JSON (dict of LISTS) is still
    # hashable for the curve cache — the crash this gate hit on its first keyed run.
    return tuple(arm[grunt] if isinstance(arm, dict) else arm)


def prerender(arms, conditions):
    """Render every (condition, arm) pair CONCURRENTLY.  `build.md`: parallel by default, and the
    items are independent OfflineRender subprocesses with distinct output paths."""
    jobs = sorted({(f, armfor(a, g)) for _, f, g, _ in conditions for a in arms})
    with ThreadPoolExecutor(max_workers=min(8, (os.cpu_count() or 4))) as ex:
        list(ex.map(lambda j: BH.render_of(j[0], j[1]), jobs))


def read(fname, arm):
    """-> {rung: geom or None} for one (condition, arm)."""
    out = {}
    for r in RUNGS:
        g, ped, mod = BH.curves(fname, r, arm)
        out[r] = (BH.geom(g, ped, FEAT), BH.geom(g, mod, FEAT))
    return out


def score(conds, arm, membership, side="model"):
    """Both axes for one arm, computed PER GRUNT and then aggregated with EQUAL WEIGHT per switch
    position.

    ⚠⚠ THE EQUAL-WEIGHT AGGREGATE IS A DESIGN CHOICE AND IT IS STATED, NOT SNUCK IN.  A plain pool
    over conditions weights GRUNT by how many captures each position happens to have, and the
    centre error changes SIGN across GRUNT — so a pooled median cancels cut against flat/boost and
    reports a number no condition has.  The pooled figure is printed beside the balanced one every
    run so the two can never be confused.

    ⚠ MEMBERSHIP IS FIXED BY THE BASELINE PAIR, not by the candidate.  A candidate that cannot read
    a fixed cell is PENALISED (dropped from its `n`, counted as a refusal) — never rewarded, which
    is the s178 trap: a null too shallow to READ is exactly the outcome being scored."""
    idx = 0 if side == "pedal" else 1
    per = {}
    kk = {g: [0, 0] for g in GRUNTS}
    errs = {g: [] for g in GRUNTS}
    sgn = {g: [] for g in GRUNTS}
    refused = 0
    for label, fname, gr, shape in conds:
        if label not in membership:
            continue
        rows = read(fname, armfor(arm, gr))
        vals = [rows[r][idx] for r in RUNGS]
        if any(v is None for v in vals):
            refused += 1
        else:
            d = [v["depth_point"] for v in vals]
            kk[gr][0] += all(d[i] > d[i + 1] for i in range(len(d) - 1))
            kk[gr][1] += 1
        # The CENTRE axis is a model/pedal ratio, so it is defined only on the model side; the
        # `pedal` side of this function exists to score ND's own ORDERING and nothing else.
        ped, mod = rows[PLAY]
        if side == "model" and ped and mod:
            r = mod["f0"] / ped["f0"]
            errs[gr].append(abs(1.0 - r))
            sgn[gr].append(r)
            per[label] = (gr, shape, r)
    k = sum(v[0] for v in kk.values())
    n = sum(v[1] for v in kk.values())
    live = [g for g in GRUNTS if errs[g]]
    bal = float(np.mean([np.median(errs[g]) for g in live])) if live else float("nan")
    pooled = float(np.median([x for g in GRUNTS for x in errs[g]])) if live else float("nan")
    # Ordering, also equal-weighted per position, so a cut-heavy pool cannot carry it either.
    olive = [g for g in GRUNTS if kk[g][1]]
    obal = float(np.mean([kk[g][0] / kk[g][1] for g in olive])) if olive else float("nan")
    return {"k": k, "n": n, "refused": refused, "k_by_grunt": {g: list(v) for g, v in kk.items()},
            "order_bal": obal, "abs_err_bal": bal, "abs_err_pooled": pooled,
            "err_by_grunt": {g: float(np.median(errs[g])) for g in live},
            "signed_by_grunt": {g: float(np.median(sgn[g])) for g in live},
            "per": per}


# ================================================================================================
def bs0(out, conds):
    print("-- BS0: membership, BALANCED ON GRUNT, and the settings axes spelled out --------------")
    print("    ⚠ every capture without a `grunt-` token is GRUNT = Cut (s151), so the switch axis")
    print("      is named per condition rather than inferred.")
    missing = [c for _, c, _, _ in conds if not os.path.exists(os.path.join(C.CAPTURE_DIR, c))]
    if missing:
        die("BS0", f"missing captures: {missing}")
    by = {}
    for _, _, gr, _ in conds:
        by[gr] = by.get(gr, 0) + 1
    gaps = [(s, g) for s, *cs in SHAPES for g, c in zip(GRUNTS, cs) if c is None]
    print(f"    {len(conds)} conditions from {len(SHAPES)} shapes x 3 GRUNT positions: {by}")
    print(f"    shapes with no capture at a position (a CAPTURE fact, permanent — s111): {gaps}")
    if min(by.values()) < 8:
        die("BS0", "a GRUNT position has fewer than 8 conditions — the balance this gate rests on "
                   "does not exist and a pooled statistic would be that position's statistic")
    p = BH.shipped_makeup("cut")
    cfs = [F.clean_frac_of(c) for _, c, _, _ in conds]
    hg = [BH.hf_gain_at(p, x) for x in cfs]
    print(f"    cleanFrac spans {min(cfs):.3f} .. {max(cfs):.3f}; the MIX-KEYED HF term's own gain")
    print(f"    spans {min(hg):+.2f} .. {max(hg):+.2f} dB across it ⇒ 'the HF term' is a DIFFERENT")
    print(f"    correction at every setting, which is why a bleed-free-only read is meaningless.")
    out["bs0"] = {"n": len(conds), "by_grunt": by, "gaps": gaps,
                  "cf_min": min(cfs), "cf_max": max(cfs)}


def bs1_membership(out, conds):
    """The fixed cell set: readable by ND AND both endpoints of the family, at all rungs."""
    print("\n-- BS1: the FIXED membership (ND + both family endpoints), all rungs -----------------")
    prerender([SHIP, NOHF], conds)
    keep, drop = [], []
    for label, fname, _, _ in conds:
        ok = True
        for arm in (SHIP, NOHF):
            rows = read(fname, arm)
            for r in RUNGS:
                if rows[r][0] is None or rows[r][1] is None:
                    ok = False
        (keep if ok else drop).append(label)
    by = {}
    for label, _, gr, _ in conds:
        if label in keep:
            by[gr] = by.get(gr, 0) + 1
    print(f"    kept {len(keep)}/{len(conds)}, by GRUNT {by}")
    print(f"    dropped and NAMED: {drop if drop else 'none'}")
    if min(by.get(g, 0) for g in GRUNTS) < 3:
        die("BS1", f"a GRUNT position keeps fewer than 3 conditions ({by}) — the balanced "
                   f"aggregate would rest on a position that is barely measured")
    out["bs1"] = {"kept": keep, "dropped": drop, "by_grunt": by}
    return keep


def _line(name, s):
    return (f"    {name:18s}{f'{s[chr(107)]}/{s[chr(110)]}':>9s}{s['order_bal']:>8.2f}"
            f"{s['refused']:>6d}{s['abs_err_bal']:>10.3f}{s['abs_err_pooled']:>10.3f}"
            + "".join(f"{s['signed_by_grunt'].get(g, float('nan')):9.3f}" for g in GRUNTS))


HDR = (f"    {'candidate':18s}{'order':>9s}{'ordbal':>8s}{'ref':>6s}{'|1-r|bal':>10s}"
       f"{'pooled':>10s}" + "".join(f"{g:>9s}" for g in GRUNTS))


def bs2_baseline(out, conds, membership):
    print("\n-- BS2: the current-epoch baseline, on BOTH axes, SPLIT BY GRUNT ---------------------")
    nd = score(conds, SHIP, membership, side="pedal")
    print(f"    ND ordering (monotone-falling depth): {nd['k']}/{nd['n']}, "
          f"per GRUNT {nd['k_by_grunt']}, equal-weighted {nd['order_bal']:.2f}")
    print(HDR)
    res = {}
    for name, arm in (("pre-s195 (shared)", SHIP), ("SHIPPED s195", SHIPPED_NOW), ("no-HF", NOHF)):
        s = score(conds, arm, membership)
        res[name] = s
        print(_line(name, s))
    a = res["pre-s195 (shared)"]
    signs = {np.sign(r - 1.0) for _, _, r in a["per"].values()}
    print()
    print(f"    per-GRUNT |1-r| (shipped): "
          + "  ".join(f"{g} {a['err_by_grunt'].get(g, float('nan')):.3f}" for g in GRUNTS))
    if len(signs) > 1:
        print(f"    ⇒ THE CENTRE ERROR CHANGES SIGN across GRUNT, so BH4's median of the SIGNED")
        print(f"      ratio is a cancellation, not a centre accuracy: the shipped build reads")
        print(f"      |1-r| = {a['abs_err_bal']:.3f} balanced, against a signed median that looks")
        print(f"      far better.  ⇒ a single GRUNT-INDEPENDENT term is being asked to push the")
        print(f"      centre UP at one switch position and DOWN at the other two.")
    else:
        print(f"    ⇒ the centre error is one-signed across GRUNT; the signed median is readable.")
    out["bs2"] = {"nd": {k: v for k, v in nd.items() if k != "per"},
                  **{k: {kk: vv for kk, vv in v.items() if kk != "per"} for k, v in res.items()},
                  "per_condition": {k: {l: [t[0], t[1], t[2]] for l, t in v["per"].items()}
                                    for k, v in res.items()}}
    return nd, res


def bs3_frontier(out, conds, membership, nd, base):
    print("\n-- BS3: the FRONTIER — sweep the family, grade BOTH axes ------------------------------")
    cands = [("pre-s195 (shared)", SHIP), ("SHIPPED s195", SHIPPED_NOW)]
    for s in (0.75, 0.5, 0.25, 0.0):
        cands.append((f"hf x{s:.2f}", hf(scale=s)))
    for hz in (4500.0, 7500.0, 10000.0):
        cands.append((f"hf @{hz:.0f}Hz", hf(hz=hz)))
    for q in (1.0, 4.0):
        cands.append((f"hf Q{q:g}", hf(q=q)))
    for hz in (7500.0, 10000.0):
        cands.append((f"hf @{hz:.0f} x0.5", hf(scale=0.5, hz=hz)))
    for cut in (4.5, 6.0):
        cands.append((f"shelf cut {cut:g}", shelf(cut=cut)))
    for shz in (2800.0, 4000.0):
        cands.append((f"shelf @{shz:.0f}", shelf(hz=shz)))
    cands.append(("no-HF", NOHF))

    prerender([a for _, a in cands], [c for c in conds if c[0] in membership])
    print(HDR)
    rows = []
    for name, arm in cands:
        s = score(conds, arm, membership)
        rows.append({"name": name, "arm": arm if isinstance(arm, dict) else list(arm),
                     **{k: v for k, v in s.items() if k != "per"}})
        print(_line(name, s))

    b = base["pre-s195 (shared)"]
    # ⚠ The bar on the centre is the LOCATOR's own resolution, not equality: GATE W's grid is
    # 1/48 oct = 1.45 %, and s129's rule is that a difference under the instrument's resolution is
    # FLAT, not small.  Requiring exact non-regression would refuse candidates that are
    # centre-identical to the shipped build within what the reader can see.
    tol = W_RES = 0.0145
    dom = [r for r in rows if r["order_bal"] >= nd["order_bal"] - 1e-9
           and r["abs_err_bal"] <= b["abs_err_bal"] + tol and r["refused"] <= b["refused"]]
    strict = [r for r in dom if r["abs_err_bal"] <= b["abs_err_bal"] + 1e-9]
    better = [r for r in rows if r["order_bal"] > b["order_bal"]
              and r["abs_err_bal"] <= b["abs_err_bal"] + 1e-9 and r["refused"] <= b["refused"]]
    print()
    print(f"    centre tolerance = the LOCATOR's own resolution, 1/48 oct = {tol * 100:.2f} % "
          f"(s129) — a\n    difference under it is FLAT, not small.")
    if strict:
        print(f"    ⇒ A STRICTLY DOMINATING CANDIDATE EXISTS: {[r['name'] for r in strict]}")
        print(f"      — matches ND's equal-weighted ordering AND improves the balanced centre.")
    elif dom:
        print(f"    ⇒ A DOMINATING CANDIDATE EXISTS within the reader's resolution: "
              f"{[r['name'] for r in dom]}")
        print(f"      — it matches ND's ordering ({nd['order_bal']:.2f}) and its centre is inside")
        print(f"      {tol * 100:.2f} % of the shipped build's, i.e. not resolvably worse.")
    elif better:
        print(f"    ⇒ NO candidate reaches ND's full ordering, but {[r['name'] for r in better]}")
        print(f"      improve it WITHOUT costing the centre — a partial win, not a trade.")
    else:
        print(f"    ⇒ NO DOMINATING CANDIDATE ANYWHERE IN THE FAMILY — the tension survives a")
        print(f"      SWEEP, not just s178's six discrete arms.")
    out["bs3"] = {"rows": rows, "tol": tol, "dominating": [r["name"] for r in dom],
                  "strict": [r["name"] for r in strict], "better_both": [r["name"] for r in better]}
    return rows


def bs4_pinning(out, conds, membership):
    """The finding neither axis states: the model's null does not MOVE with the settings."""
    print("\n-- BS4: the model's null is PINNED and ND's is not ------------------------------------")
    print(f"    {'condition':26s}{'ND f0':>10s}{'model f0':>10s}{'ratio':>8s}")
    nd, mo, by = [], [], {}
    for label, fname, gr, _ in conds:
        if label not in membership:
            continue
        rp, rm = read(fname, SHIP)[PLAY]
        if not (rp and rm):
            continue
        nd.append(rp["f0"])
        mo.append(rm["f0"])
        by.setdefault(gr, []).append((rp["f0"], rm["f0"]))
        print(f"    {label:26s}{rp['f0']:10.1f}{rm['f0']:10.1f}{rm['f0'] / rp['f0']:8.3f}")
    sp = lambda v: max(v) / min(v) - 1.0
    print(f"\n    span (max/min - 1) across the pool:  ND {sp(nd) * 100:5.1f} %   "
          f"MODEL {sp(mo) * 100:5.1f} %   ratio {sp(mo) / max(sp(nd), 1e-9):.2f}x")
    print(f"    the GRUNT axis alone (median f0 per position):")
    for g in GRUNTS:
        if g in by:
            print(f"      {g:6s} ND {np.median([a for a, _ in by[g]]):7.1f}   "
                  f"MODEL {np.median([b for _, b in by[g]]):7.1f}   n={len(by[g])}")
    ndg = [np.median([a for a, _ in by[g]]) for g in GRUNTS if g in by]
    mog = [np.median([b for _, b in by[g]]) for g in GRUNTS if g in by]
    print(f"      span across GRUNT:  ND {sp(ndg) * 100:5.1f} %   MODEL {sp(mog) * 100:5.1f} %")
    print("    ⚠ GATE W's locator resolves 1/48 oct = 1.45 %, so a span under ~1.5 % is FLAT, not")
    print("      small (s129: use the instrument's own resolution as the floor, never a spread).")
    if sp(mog) < sp(ndg):
        print("    ⇒ the model's null moves LESS with GRUNT than ND's — open item 6's pinning on a")
        print("      fourth axis (after position, depth and slope).  ⛔ A GRUNT-INDEPENDENT")
        print("      correction cannot put a pinned feature onto a target that moves with the")
        print("      switch, which BOUNDS what any point of BS3's family can achieve and is the")
        print("      structural reason the centre error changes sign across GRUNT.")
    else:
        print("    ⇒ the model's null moves at least as much as ND's across GRUNT — the pinning")
        print("      story does NOT hold on this axis and BS3's family is not bounded by it.")
    out["bs4"] = {"nd_span_pct": sp(nd) * 100, "model_span_pct": sp(mo) * 100,
                  "nd_grunt_span_pct": sp(ndg) * 100, "model_grunt_span_pct": sp(mog) * 100}


# s173's OWN sub-bands, transcribed from its SHIPPED CONSTANTS row so the third axis is the one
# that change was actually fitted against — not a band set chosen by this gate.
S173_BANDS = [(250.0, 900.0), (900.0, 2800.0), (2800.0, 4000.0), (4000.0, 8000.0),
              (8000.0, 16300.0)]


def bs5_band_error(out, conds, _unused_membership, rows):
    """⛔⛔ THE AXIS BS3 IS STRUCTURALLY BLIND TO, AND IT IS THE ONE s173 WAS FITTED ON.

    BS3 grades a null's ORDERING and CENTRE.  s173's HF term was not shipped for either: it was
    shipped for a USER-REPORTED broadband error — 'at the stated playing level the 4-8 kHz error
    CHANGES SIGN across the mix', rms|err| 3.30 -> 0.98 dB over that band.  A candidate that
    improves BS3's two axes while giving that back is a THREE-WAY trade wearing a two-axis win,
    which is `gate-domain-must-cover-candidate-reach` (s49) exactly.

    ⛔⛔ READ AS A **MEDIAN OVER THE BAND'S POINTS**, NOT AN rms — AND THAT IS NOT A STYLE CHOICE.
    s173's own row says so in as many words: *'Band read as a MEDIAN — the notch drags the 4-8 kHz
    MEAN 4.35 dB off it at one capture.'*  The treble null LIVES in the 4-8 kHz band and is 17 dB
    deep in the shipped build, so an rms (or a mean) over that band is dominated by the null's own
    depth — i.e. a third axis computed that way is BS3's first axis wearing a different name, and
    a candidate that shallows the null scores a 'broadband' win it has not earned.  A first draft
    of this sub-gate did exactly that and reported the opposite ranking.  Both are printed."""
    print("\n-- BS5: the THIRD axis — s173's own sub-band magnitude error --------------------------")
    print("    ⚠ BS3 cannot see this: it grades a null's position and its depth ORDER, and s173's")
    print("      HF term was shipped for a broadband 4-8 kHz error at the playing mix.  A candidate")
    print("      that wins BS3 and loses here is a trade, not a fix.")
    print("    ⛔ MEDIAN over the band's points (s173's own convention) — an rms there is dominated")
    print("       by the null itself and is not an independent axis at all.  rms shown for contrast.")
    print("    ⛔⛔ AND IT RUNS ON **ALL** CONDITIONS, NOT BS1's MEMBERSHIP.  BS1 keeps only cells")
    print("       where BOTH sides resolve a NULL; a band error needs no null, and the 9 cells BS1")
    print("       drops are every LEVEL = max condition — exactly where the mix-keyed term is a CUT")
    print("       rather than a boost.  Scored on BS1's membership this sub-gate reported the")
    print("       OPPOSITE ranking.  ⇒ a null-readability membership must not travel to a")
    print("       magnitude statistic (`aggregate-moved-check-membership-first`).")
    print(f"    {'candidate':18s}" + "".join(f"{f'{lo:.0f}-{hi:.0f}':>12s}" for lo, hi in S173_BANDS)
          + f"{'4-8k bal':>10s}{'4-8k rms':>10s}")
    res = {}
    for r in rows:
        arm = r["arm"] if isinstance(r["arm"], dict) else tuple(r["arm"])
        per_band, per_band_rms = {}, {}
        band_by_grunt = {g: [] for g in GRUNTS}
        for lo, hi in S173_BANDS:
            acc, acc_rms = [], []
            for label, fname, gr, _ in conds:
                for rung in RUNGS:
                    g, ped, mod = BH.curves(fname, rung, armfor(arm, gr))
                    sel = (g >= lo) & (g < hi)
                    d = np.abs(mod[sel] - ped[sel])
                    e = float(np.median(d))
                    acc.append(e)
                    acc_rms.append(float(np.sqrt(np.mean(d ** 2))))
                    if (lo, hi) == (4000.0, 8000.0):
                        band_by_grunt[gr].append(e)
            per_band[f"{lo:.0f}-{hi:.0f}"] = float(np.mean(acc))
            per_band_rms[f"{lo:.0f}-{hi:.0f}"] = float(np.mean(acc_rms))
        live = [g for g in GRUNTS if band_by_grunt[g]]
        bal = float(np.mean([np.mean(band_by_grunt[g]) for g in live]))
        res[r["name"]] = {"per_band": per_band, "per_band_rms": per_band_rms,
                          "hf_band_balanced": bal,
                          "by_grunt_4_8k": {g: float(np.mean(band_by_grunt[g])) for g in live}}
        print(f"    {r['name']:18s}" + "".join(f"{v:12.3f}" for v in per_band.values())
              + f"{bal:10.3f}{per_band_rms['4000-8000']:10.3f}")

    b = res["pre-s195 (shared)"]
    # A candidate is shippable on THREE axes only if it does not regress any of them beyond the
    # relevant instrument's own resolution.  For a band rms the honest floor is the across-rung
    # spread of the shipped build's own reading in that band, computed rather than guessed.
    verdict = {}
    for name, v in res.items():
        worse = {k: v["per_band"][k] - b["per_band"][k] for k in v["per_band"]
                 if v["per_band"][k] > b["per_band"][k] + 0.02}
        verdict[name] = worse
    out["bs5"] = {"per_arm": res, "regressions_vs_ship": verdict}
    print()
    print("    ⇒ bands where a candidate is WORSE than the shipped build by > 0.02 dB:")
    for name in verdict:
        if name == "pre-s195 (shared)":
            continue
        w = verdict[name]
        print(f"      {name:18s} {'none' if not w else ', '.join(f'{k} {d:+.3f}' for k, d in w.items())}")

    # ⭐ THE PER-CONDITION TABLE IS THE DELIVERABLE, not the pooled row: the user's own report is
    # that this feature is "better and worse at various captures", and it is — with a STRUCTURE.
    print("\n    per condition, 4-8 kHz median|err|, HF term ON vs OFF (+ = the term HURTS there):")
    print(f"    {'condition':28s}{'cf':>6s}{'HF dB':>7s}{'ON':>8s}{'OFF':>8s}{'delta':>8s}")
    p = BH.shipped_makeup("cut")
    per_cond = {}
    for label, fname, gr, _ in conds:
        cf = F.clean_frac_of(fname)
        v = []
        for arm in (SHIP, NOHF):
            a = []
            for rung in RUNGS:
                g, ped, mod = BH.curves(fname, rung, arm)
                sel = (g >= 4000.0) & (g < 8000.0)
                a.append(float(np.median(np.abs(mod[sel] - ped[sel]))))
            v.append(float(np.mean(a)))
        per_cond[label] = {"cf": cf, "on": v[0], "off": v[1], "delta": v[0] - v[1], "grunt": gr}
        print(f"    {label:28s}{cf:6.2f}{BH.hf_gain_at(p, cf):+7.1f}{v[0]:8.2f}{v[1]:8.2f}"
              f"{v[0] - v[1]:+8.2f}")
    out["bs5"]["per_condition_4_8k"] = per_cond
    lvlmax = [x for x in per_cond.values() if x["cf"] < 0.1]
    cutmix = [x for x in per_cond.values() if x["cf"] >= 0.4 and x["cf"] < 0.6 and x["grunt"] == "cut"]
    fbmix = [x for x in per_cond.values() if x["cf"] >= 0.4 and x["cf"] < 0.6 and x["grunt"] != "cut"]
    print(f"\n    ⇒ COMPUTED STRUCTURE (counts, not narration):")
    for nm, grp in (("LEVEL max (cf<0.1, the term is a CUT)", lvlmax),
                    ("LEVEL noon x BLEND max, GRUNT=cut  (a BOOST)", cutmix),
                    ("LEVEL noon x BLEND max, GRUNT=flat/boost (a BOOST)", fbmix)):
        h = sum(1 for x in grp if x["delta"] < 0)
        print(f"      {nm:52s} HF term helps {h}/{len(grp)}  "
              f"median delta {np.median([x['delta'] for x in grp]):+.2f} dB")
    out["bs5"]["structure"] = {
        "level_max_helps": [sum(1 for x in lvlmax if x["delta"] < 0), len(lvlmax)],
        "cut_mix_helps": [sum(1 for x in cutmix if x["delta"] < 0), len(cutmix)],
        "flatboost_mix_helps": [sum(1 for x in fbmix if x["delta"] < 0), len(fbmix)]}
    return res


def bs6_grunt_keyed(out, conds, membership, nd, base):
    """⭐⭐ THE CANDIDATE THE STRUCTURE POINTS AT, and it is s187's pattern on a second constant.

    BS5's per-condition table splits three ways and the split is the whole finding:
      * LEVEL max (cf ~ 0.02), where the mix law makes the term a CUT: it HELPS at all three GRUNT
        positions ⇒ `odMakeupHfAtOdDb` is right everywhere and must not be touched.
      * LEVEL noon x BLEND max (cf ~ 0.48), where the law makes it a BOOST: it HELPS at GRUNT=cut
        and HURTS at flat/boost.
    ⇒ the defect is confined to the POSITIVE peak node, at flat and boost only.  GRUNT switches the
    clipper's own input coupling bank (a ~47x swing in the OD branch's LF corner, and s170's BE1b
    measured flat/boost driving the clipper +7.6 dB harder), so a shared post-clipper term serving
    all three positions is exactly what s38/s187 say cannot work.

    ⚠ Evaluated by rendering each GRUNT position with its own arm — no `src/` change is needed to
    MEASURE a keyed candidate, only to ship one."""
    print("\n-- BS6: GRUNT-KEYED candidates — key `odMakeupHfPeakDb` at flat/boost only -----------")
    print("    ⚠ `odMakeupHfAtOdDb` is held at the shipped -4.5 at EVERY position: BS5 measures it")
    print("      helping at all three, and scaling it away is what costs the LEVEL-max conditions.")

    def keyed(peak_fb):
        return {"cut": SHIP,
                "flat": hf(peak=peak_fb), "boost": hf(peak=peak_fb)}

    cands = [("pre-s195 (shared)", SHIP), ("SHIPPED s195", SHIPPED_NOW), ("no-HF (global)", NOHF)]
    for pk in (2.0, 1.0, 0.0, -1.5, -3.0):
        cands.append((f"keyed peak {pk:+.1f}", keyed(pk)))
    # and the same, with a partial reduction at CUT too — where the axes genuinely trade
    for pk in (0.0,):
        for ck in (2.0, 1.0):
            cands.append((f"keyed {ck:+.1f}/{pk:+.1f}",
                          {"cut": hf(peak=ck), "flat": hf(peak=pk), "boost": hf(peak=pk)}))

    prerender([a for _, a in cands], conds)

    # ⛔⛔ NON-VACUITY, ASSERTED RATHER THAN ASSUMED — this is the s194 defect's own shape and the
    # constant under test is now GRUNT-keyed, so an arm that names the wrong field renders
    # BIT-IDENTICALLY to the baseline and still gets a row in the table.  Require every keyed arm
    # to MOVE flat/boost and to leave cut ALONE (it is `SHIP` there by construction).
    import hashlib

    def sha(fname, arm):
        return hashlib.sha256(open(BH.render_of(fname, armfor(arm, "flat")), "rb").read()).digest()

    probe = next(f for _, f, g, _ in conds if g == "flat")
    base_sha = sha(probe, SHIP)
    dead = [n for n, a in cands if n.startswith("keyed") and sha(probe, a) == base_sha]
    if dead:
        die("BS6", f"these keyed arms are BIT-IDENTICAL to the baseline at GRUNT=flat and are "
                   f"therefore measuring nothing: {dead}.  Since s195 `odMakeupHfPeakDb` reaches "
                   f"the DSP at Cut only — an arm must set `odMakeupHfPeakDbNonCut` to move "
                   f"flat/boost (s194's inert-`--fit` defect, on this gate's own constant).")
    print(f"    non-vacuity: all {sum(1 for n, _ in cands if n.startswith('keyed'))} keyed arms "
          f"move the flat render ✓")
    print(HDR)
    rows = []
    for name, arm in cands:
        s = score(conds, arm, membership)
        rows.append({"name": name, "arm": {k: list(v) for k, v in arm.items()}
                     if isinstance(arm, dict) else list(arm),
                     **{k: v for k, v in s.items() if k != "per"}})
        print(_line(name, s))
    out["bs6"] = {"rows": rows}
    return rows


def main():
    ap = argparse.ArgumentParser(description="GATE BS — item 17 treble half, joint frontier")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    print("=" * 100)
    print("GATE BS — item 17's TREBLE half: the joint frontier, across settings   (s195)")
    print("=" * 100)
    out = {}
    conds = conditions()
    bs0(out, conds)
    keep = bs1_membership(out, conds)
    nd, base = bs2_baseline(out, conds, keep)
    rows = bs3_frontier(out, conds, keep, nd, base)
    bs4_pinning(out, conds, keep)
    krows = bs6_grunt_keyed(out, conds, keep, nd, base)
    bs5_band_error(out, conds, keep, rows + [r for r in krows if r["name"].startswith("keyed")])
    if args.json:
        os.makedirs(os.path.dirname(args.json), exist_ok=True)
        json.dump(out, open(args.json, "w"), indent=1)
        print(f"\nwrote {args.json}")
    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()
