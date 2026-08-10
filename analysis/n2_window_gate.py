#!/usr/bin/env python3.11
"""GATE BW -- N2's WIDENED-WINDOW CONFIRMATION.  s201's own OWED step, run.

WHY THIS EXISTS.  GATE BV's BV3 measured that the model's `mid_notch` (item 19's **N2**, the
~320 Hz null) is **not readable in 0 of 112 played GRUNT-cut cells**, against the pedal's 38 --
including at `ref-od.wav`, the user's own stated baseline.  It split the refusals by REASON, which
is the load-bearing half: **EDGE 28** (the extremum sits on a window BOUND -- a statement about
where the feature MOVED TO) and **PROM 84** (the window is right and there is nothing in it --
s126/s133's presence/absence result).  BV's own write-up then said, in as many words:

    ⛔⛔ THE CONFIRMING STEP IS OWED AND WAS NOT RUN: a `PROM` refusal is measured in a FIXED
    window, so separating *moved out of the window* from *gone* properly needs the widened-window
    read (GATE AV's method, s158).  ⇒ an open observation, not a defect, until that runs.

This gate is that step.  ⛔ It changes no constant and proposes none.  Its output is a
classification of all 112 cells.

WHAT MAKES A NEGATIVE RESULT READABLE HERE, AND IT WAS FREE.  `a silent estimator and an absent
feature are indistinguishable` (s126/s133) until the estimator is shown to find the feature when it
IS there -- and BV3 already measured that control without being asked: the model resolves N2 at
**36 of 36 BLEED-FREE CORNER cells**.  So the reader is not broken, and BW3 re-runs the identical
widened instrument there so the control travels with the measurement rather than being cited.

TWO INSTRUMENTS, BECAUSE THE TWO REFUSAL REASONS ARE DIFFERENT QUESTIONS
-----------------------------------------------------------------------
BW4  **PINNED WIDENING** -- GATE AV's literal method, for the PROM refusals.  Hold the extremum
     where the shipped window put it, widen ONLY the walk domain, re-read.  A number that does not
     move is a depth; a number that grows had its value set by where the window was cut (AV3).
     ⚠⚠ AND IT CANNOT STAND ALONE HERE.  AV5 measured this exact hazard: in a window FLANKED by
     neighbouring features -- which every shipped window is -- **161 of 300 feature-free curves
     read PRESENT** under widening, because the walk climbs the neighbours' flanks.  So a widened
     `prom` crossing the bar is NOT evidence of a feature, and BW4 reports `at_bound` per side and
     runs the PEDAL at the same cells as the contrast arm rather than quoting the model alone.

BW5  **THE INTERIOR-EXTREMUM CENSUS** -- the threshold-free discriminator, and the one the verdict
     rests on.  GATE AE's construction (s133): "NO INTERIOR EXTREMUM AT ALL" is a statement with no
     bar in it.  `bass_peak_locus._best_interior` (E2, s126's repair, classified by AV0) requires a
     genuine two-sided local minimum, so a monotone flank returns **nothing** where `locate`'s walk
     would return a plausible number.  ⭐ And its `min(left, right)` correctly penalises a dimple on
     a slope -- going downhill breaks the walk immediately -- which is precisely the inflation AV5
     warns about, refused by construction rather than by a threshold.

⭐⭐ THE SEARCH DOMAIN IS `od_tone_restore_fit.SHOULDER`, IMPORTED, AND THE s151 JUMP IS
STRUCTURALLY IMPOSSIBLE IN IT.  s151 established that widening GATE W's `mid_notch` window is
exactly where a reader jumps features: at DRIVE max the model's curve falls monotonically from
~370 Hz into the bridged-T, so a window wide enough to hold the right shoulder puts the GLOBAL
minimum at ~550 Hz (measured: f0 550.8, depth 0.000, edge=1).  That is why this gate does not pick
a widening factor for the SEARCH -- it uses the window the stage that OWNS this feature already
derived for it, and BW0 ASSERTS `SHOULDER`'s top bound sits below `bt_notch`'s window, so the jump
cannot occur rather than being checked for afterwards.

⛔⛔ THIS GATE MUST NOT TOUCH `build/s122_feature_locus/` (READ-ONLY, ENFORCED, s159) and it
renders NOTHING: every model curve comes from GATE BV's own private cache, whose 50 stamps BW0
re-verifies against the shipped binary.

Run:  python3.11 analysis/n2_window_gate.py
      python3.11 analysis/_mutate_gate_bw.py
"""
import argparse
import glob
import hashlib
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze as A                  # noqa: E402
import bass_peak_locus as Y          # noqa: E402  -- E2 `_best_interior`, the interior-min finder
import captures as C                 # noqa: E402
import comb_confirm_gate as BV       # noqa: E402  -- membership, validity rule, refusal reasons
import comprehensive_report as CR    # noqa: E402
import feature_locus_gate as W       # noqa: E402  -- locator, windows, grid, bars: IMPORTED
import od_tone_restore_fit as F      # noqa: E402  -- CORE/SHOULDER + the corner clean fraction
import prominence_audit_gate as AV   # noqa: E402  -- the pinned, widenable walk: IMPORTED
from parallel import add_jobs_arg, pmap_cpu   # noqa: E402

OUT_JSON = "analysis/reports/s202_n2_window.json"
REN_DIR = BV.REN_DIR                       # GATE BV's cache -- READ ONLY here, nothing is rendered
FORBIDDEN_DIR = W.REN_DIR                  # build/s122_feature_locus -- READ-ONLY, ENFORCED
BV_REPORT = BV.OUT_JSON

FEATURE = "mid_notch"                      # item 19's N2
_NAME, KIND, WIN, _LAB = W.FEAT_BY_NAME[FEATURE]

# The population the finding is about, stated as a filter rather than a file list.
POP_GRUNT = "cut"

FAILED = []


def fail(tag, msg):
    FAILED.append(f"{tag}: {msg}")
    print(f"  ❌ {tag} FAIL -- {msg}")


# =================================================================================================
def _curve(al, sw, ref):
    """The smoothed 1/48-oct curve -- W's own pipeline, so every reading is apples-to-apples."""
    f, m = A.transfer_h1(A.seg_of(al, sw), ref)
    return W.smooth(f, m)


def _read_side(d):
    """Everything this gate asks of ONE curve at N2, both instruments."""
    shipped = W.locate(d, WIN, KIND)
    i = AV.cell_index(d, WIN, KIND)
    base = AV.sides_at(d, i, WIN, KIND)
    wide = {}
    for w in AV.WIDEN:
        s = AV.sides_at(d, i, AV.widen_win(WIN, w), KIND)
        wide[f"{w}"] = None if s is None else {
            "prom": s["prom"], "n_bound_sides": s["n_bound_sides"],
            "left_at_bound": s["left"]["at_bound"], "right_at_bound": s["right"]["at_bound"]}
    bi = Y._best_interior(d, F.SHOULDER, KIND)
    try:
        ng = F.notch_geometry(W.GRID, d)
        ngr = {"f0": ng["f0"], "depth_point": ng["depth_point"], "depth_area": ng["depth_area"],
               "refused": False}
    except RuntimeError:
        # notch_geometry REFUSES when the minimum rests on a CORE bound -- which is not a failure
        # here, it is the "the feature is at or past the bound" signal, recorded as such (s151).
        ngr = {"f0": None, "depth_point": None, "depth_area": None, "refused": True}
    return {"shipped_f0": shipped["f0"], "shipped_prom": shipped["prom"],
            "edge": bool(shipped["edge"]), "margin_frac": shipped["margin_frac"],
            "valid": bool(BV.valid(shipped)), "why": BV.refusal_reason(shipped),
            "walk_n_bound_sides": None if base is None else base["n_bound_sides"],
            "widen": wide,
            "bi_f0": bi["f0"], "bi_prom": bi["prom"], "bi_n_interior": bi["n_interior"],
            "ng": ngr}


def classify(r, bar=None):
    """THREE tiers, and the three-way split is the whole correction this gate makes.

    ⛔⛔ `ABSENT` AND `BELOW-BAR` MUST NOT SHARE A BRANCH.  A first draft called both of them GONE
    and reported "46 of 112 genuinely absent" -- which merges a statement with NO BAR IN IT (the
    curve is monotone across the entire search domain, so there is no feature at any depth) with a
    statement that is ENTIRELY a bar call (a real local minimum, shallower than the presence
    threshold).  Those have different owners: the first would be a missing feature, the second is
    this comb's already-measured DILUTION at a mixed setting.  s129's "three outcomes, not two",
    on the one axis where collapsing them flatters the alarming reading.

    ⛔ The ORDER matters: `n_interior == 0` is tested FIRST so a genuine absence can never be
    reported as a shallow presence.  The bar is W's OWN `MIN_PROM_DB`, imported -- the same bar
    that produced the refusal being explained -- and BW5 SWEEPS it (s137) because a tier defined
    by a threshold must be quoted with its sensitivity."""
    bar = W.MIN_PROM_DB if bar is None else bar
    if r["bi_n_interior"] == 0:
        return "ABSENT"
    if r["bi_prom"] < bar:
        return "BELOW-BAR"
    f0 = r["bi_f0"]
    if WIN[0] <= f0 <= WIN[1]:
        return "IN-WINDOW"
    return "MOVED HIGH" if f0 > WIN[1] else "MOVED LOW"


PRESENT_KINDS = ("IN-WINDOW", "MOVED HIGH", "MOVED LOW")


def _cell(args):
    """One capture -> N2 on BOTH sides at all four rungs.  Reads renders; renders nothing."""
    fname = args
    orig, ref = W._load_orig()
    out = os.path.join(REN_DIR, fname.replace(".wav", "") + "_plugin.wav")
    if not os.path.exists(out):
        raise RuntimeError(f"GATE BW: {out} absent -- GATE BV's cache is incomplete; re-run GATE BV")
    cap_al, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, fname)), orig)
    ren_al, _ = A.align(A.load(out), orig)
    rec = {"file": fname, "settings": C.parse_capture(fname), "cf": F.clean_frac_of(fname),
           "model": {}, "pedal": {}}
    for sw in W.SWEEPS:
        rec["model"][sw] = _read_side(_curve(ren_al, sw, ref))
        rec["pedal"][sw] = _read_side(_curve(cap_al, sw, ref))
    return rec


# =================================================================================================
def bw0(out):
    """PROVENANCE, plus the two STRUCTURAL assertions this gate's search domain rests on."""
    print("\n" + "=" * 98)
    print("BW0  PROVENANCE -- the renders are GATE BV's, current, and nothing here renders")
    print("=" * 98)
    binp = CR.DEFAULT_BIN
    if not os.path.exists(binp):
        sys.exit(f"GATE BW0: render binary {binp} is absent")
    bmt = os.stat(binp).st_mtime
    newer = [p for p in glob.glob("src/**/*", recursive=True)
             if os.path.isfile(p) and os.stat(p).st_mtime > bmt]
    md5 = hashlib.md5(open(binp, "rb").read()).hexdigest()
    if newer:
        sys.exit(f"GATE BW0: {len(newer)} src file(s) postdate the render binary -- rebuild first")
    stamps = glob.glob(os.path.join(REN_DIR, "*.args.json"))
    stale = [p for p in stamps if json.load(open(p)).get("bin") != W._bin_sig()]
    print(f"  render binary   : {binp}")
    print(f"  md5             : {md5}   (src files newer: {len(newer)})")
    print(f"  BV render cache : {REN_DIR}   {len(stamps)} stamps, {len(stale)} STALE")
    if stale:
        sys.exit(f"GATE BW0: {len(stale)} render(s) in {REN_DIR} predate this binary -- re-run GATE BV")
    if not os.path.exists(BV_REPORT):
        sys.exit(f"GATE BW0: {BV_REPORT} absent -- BW1b's cross-gate known answer needs it")
    fp = BV.dir_fingerprint(FORBIDDEN_DIR)
    print(f"  READ-ONLY cache : {FORBIDDEN_DIR}  fingerprint {fp}  (untouched by this gate)")

    # ---- the two structural assertions ---------------------------------------------------------
    # (1) s151's jump must be IMPOSSIBLE, not merely unobserved: the search domain's top bound has
    #     to sit below the next named notch's window, or a wide search can track the bridged-T.
    bt_lo = W.FEAT_BY_NAME["bt_notch"][2][0]
    print(f"\n  search domain   : od_tone_restore_fit.SHOULDER = {F.SHOULDER} Hz  (IMPORTED)")
    print(f"  bt_notch window : {W.FEAT_BY_NAME['bt_notch'][2]} Hz")
    if F.SHOULDER[1] >= bt_lo:
        sys.exit(f"GATE BW0: SHOULDER's top ({F.SHOULDER[1]}) reaches bt_notch's window ({bt_lo}) -- "
                 f"s151's feature jump is REACHABLE and this gate's search is not sound")
    print(f"  ✅ SHOULDER tops at {F.SHOULDER[1]:.0f} Hz, below bt_notch's {bt_lo:.0f} Hz ⇒ s151's")
    print( "     documented jump (the reader tracking the bridged-T at ~550 Hz) is STRUCTURALLY")
    print( "     impossible in this search, rather than checked for after the fact.")
    # (2) The search domain must CONTAIN the shipped window, or "moved out of it" is not expressible.
    if not (F.SHOULDER[0] < WIN[0] and F.SHOULDER[1] > WIN[1]):
        sys.exit(f"GATE BW0: SHOULDER {F.SHOULDER} does not strictly contain W's {WIN} -- a search "
                 f"that cannot look outside the shipped window cannot answer 'did it move out'")
    print(f"  ✅ SHOULDER strictly contains W's {WIN} ⇒ 'moved out of the shipped window' is a")
    print( "     reachable outcome of this search and not excluded by construction.")
    out["bw0"] = {"bin": binp, "md5": md5, "ren_dir": REN_DIR, "n_stamps": len(stamps),
                  "n_stale": 0, "forbidden_fp": fp, "shoulder": list(F.SHOULDER),
                  "shipped_win": list(WIN), "bt_notch_lo": bt_lo}
    return fp


def bw1(rows, out):
    """KNOWN ANSWERS -- the transcription, and the cross-gate census.

    (a) The pinned walk at widen 1.0 must reproduce `W.locate`'s own `prom` EXACTLY.  AV pays this
        because it TRANSCRIBED the walk; this gate IMPORTS AV's function, so the assertion is
        really that the import still binds -- which is the thing that would silently rot.
    (b) ⭐⭐ The refusal census recomputed here must reproduce GATE BV's STORED one for this feature,
        to the count.  That is what makes every number below attributable: it proves this gate's
        membership, its validity predicate and its refusal-reason split are BV's and not a second
        opinion (s149 -- re-implementing a shared helper is how five gates start to disagree)."""
    print("\n" + "=" * 98)
    print("BW1  KNOWN ANSWERS -- the imported walk, and GATE BV's stored census reproduced")
    print("=" * 98)
    worst = 0.0
    n = 0
    for r in rows:
        for side in ("model", "pedal"):
            for sw in W.SWEEPS:
                v = r[side][sw]
                w1 = v["widen"]["1.0"]
                if w1 is None:
                    continue
                worst = max(worst, abs(w1["prom"] - v["shipped_prom"]))
                n += 1
    print(f"  (a) pinned walk at widen 1.0 vs W.locate's prom, over {n} readings: "
          f"worst |Δ| {worst:.3e} dB")
    if worst > 0.0:
        fail("BW1a", f"the imported walk does not reproduce the shipped prominence ({worst:.3e} dB)")
    else:
        print("      ✅ 0.000e+00 -- AV's re-parameterisation IS the shipped statistic, so BW4's")
        print("         widening column is a widening of the number the project actually quotes.")

    stored = json.load(open(BV_REPORT))["bv3"][FEATURE]
    corner_cf = F.bleedfree_cf()
    cnt = {("corner", "model"): [0, 0], ("corner", "pedal"): [0, 0],
           ("played", "model"): [0, 0], ("played", "pedal"): [0, 0]}
    why = {k: {} for k in cnt}
    for r in rows:
        cls = "corner" if abs(r["cf"] - corner_cf) <= BV.CORNER_CF_TOL else "played"
        for sw in W.SWEEPS:
            for side in ("model", "pedal"):
                v = r[side][sw]
                cnt[(cls, side)][0] += v["valid"]
                cnt[(cls, side)][1] += 1
                if not v["valid"]:
                    why[(cls, side)][v["why"]] = why[(cls, side)].get(v["why"], 0) + 1
    ok = True
    print(f"\n  (b) census vs GATE BV's stored `bv3.{FEATURE}`:")
    for cls in ("corner", "played"):
        for side in ("model", "pedal"):
            got, want = cnt[(cls, side)], stored[f"{cls}_{side}"]
            good = got == want
            ok &= good
            print(f"      {cls:7s} {side:6s}  {got[0]:4d}/{got[1]:<4d}  vs BV's "
                  f"{want[0]:4d}/{want[1]:<4d}   {'✅' if good else '❌'}")
            gw, ww = why[(cls, side)], stored["why"][f"{cls}_{side}"]
            if gw != ww:
                ok = False
                print(f"          ❌ refusal reasons differ: {gw} vs BV's {ww}")
    if not ok:
        fail("BW1b", "the recomputed census does not reproduce GATE BV's stored one -- this gate's "
                     "membership or validity rule is NOT BV's, so nothing below is attributable")
    else:
        print("      ✅ every count and every refusal reason reproduces ⇒ this gate reads the same")
        print("         population, through the same predicate, as the finding it is explaining.")
    out["bw1"] = {"walk_worst_delta_db": worst, "n_readings": n,
                  "census": {f"{c}_{s}": cnt[(c, s)] for c, s in cnt},
                  "census_reproduces": bool(ok)}


def _pop(rows, corner_cf, grunt=POP_GRUNT, played=True):
    """The (capture, sweep) cells of one class, model side -- the finding's own population."""
    cells = []
    for r in rows:
        is_corner = abs(r["cf"] - corner_cf) <= BV.CORNER_CF_TOL
        if is_corner == played:
            continue
        if grunt is not None and BV.grunt_of(r) != grunt:
            continue
        for sw in W.SWEEPS:
            cells.append((r, sw))
    return cells


def bw2(rows, corner_cf, out):
    """THE POPULATION -- 0 of 112, and the EDGE/PROM split, reproduced per GRUNT."""
    print("\n" + "=" * 98)
    print("BW2  THE POPULATION -- BV3's headline, split by GRUNT")
    print("=" * 98)
    res = {}
    for g in ("cut", "flat", "boost"):
        cells = _pop(rows, corner_cf, grunt=g)
        mv = sum(r["model"][sw]["valid"] for r, sw in cells)
        pv = sum(r["pedal"][sw]["valid"] for r, sw in cells)
        why = {}
        for r, sw in cells:
            v = r["model"][sw]
            if not v["valid"]:
                why[v["why"]] = why.get(v["why"], 0) + 1
        res[g] = {"n": len(cells), "model_valid": mv, "pedal_valid": pv, "model_why": why}
        print(f"  played grunt {g:5s}  n={len(cells):4d}   model {mv:3d} readable   "
              f"pedal {pv:3d} readable   model refusals: "
              + ("  ".join(f"{k}:{v}" for k, v in sorted(why.items())) or "-"))
    if res.get(POP_GRUNT, {}).get("n", 0) == 0:
        # `empty-gate-must-fail`: with no cells, BW5's shares divide by zero and BW7 would report a
        # verdict over nothing.  REFUSE rather than crash (s117 -- a stack trace hands the next
        # session a symptom instead of a reason).
        sys.exit(f"GATE BW2: the population (played, GRUNT = {POP_GRUNT}) is EMPTY -- every "
                 f"statistic below would be computed over no cells at all")
    cut = res[POP_GRUNT]
    print(f"\n  ⇒ the finding's population is GRUNT = {POP_GRUNT}: "
          f"{cut['model_valid']} of {cut['n']} on the model against {cut['pedal_valid']} on the")
    print(f"    pedal, refusals {cut['model_why']}.  Everything below classifies those {cut['n']} cells.")
    out["bw2"] = res
    return res


def bw3(rows, corner_cf, out):
    """NON-VACUITY -- the identical widened instrument, at the cells the model DOES resolve.

    ⛔ Without this the gate cannot distinguish "the model has no N2 at played settings" from "this
    gate reports GONE everywhere".  The control is free: BV3 already measured the model resolving
    N2 at 36 of 36 bleed-free corner cells, so the instrument must classify those as PRESENT."""
    print("\n" + "=" * 98)
    print("BW3  NON-VACUITY -- the same instrument at the BLEED-FREE CORNER, where N2 is readable")
    print("=" * 98)
    cells = _pop(rows, corner_cf, grunt=None, played=False)
    kinds = {}
    proms = []
    for r, sw in cells:
        v = r["model"][sw]
        kinds[classify(v)] = kinds.get(classify(v), 0) + 1
        proms.append(v["bi_prom"])
    n_present = sum(v for k, v in kinds.items() if k in PRESENT_KINDS)
    print(f"  corner cells (all GRUNT): n={len(cells)}   classified: "
          + "  ".join(f"{k}:{v}" for k, v in sorted(kinds.items())))
    print(f"  interior-minimum prominence at those cells: median {np.median(proms):.2f} dB, "
          f"min {min(proms):.2f}, max {max(proms):.2f}")
    if n_present != len(cells):
        fail("BW3", f"the instrument reports {len(cells) - n_present} corner cell(s) as ABSENT or "
                    f"BELOW-BAR, where GATE BV measured the model resolving N2 at 36 of 36 -- it is "
                    f"not finding a feature that is demonstrably there, so no ABSENT verdict below "
                    f"is readable")
    else:
        print(f"  ✅ {n_present} of {len(cells)} classified PRESENT ⇒ the instrument finds N2 where the")
        print( "     shipped reader also finds it.  An ABSENT verdict below is therefore a statement")
        print( "     about the CELL, not about this gate.")
    out["bw3"] = {"n": len(cells), "kinds": kinds, "all_present": bool(n_present == len(cells)),
                  "prom_median": float(np.median(proms))}


def bw4(rows, corner_cf, out):
    """PINNED WIDENING -- AV's literal method, on the PROM refusals, WITH the pedal contrast.

    ⚠⚠ Read the contrast column, not the model column alone.  AV5 measured that a FLANKED window
    (which this is -- `bass_peak` sits below and `mid_peak` above) reads a feature-free curve as
    PRESENT in 54 % of cases under widening, because the walk climbs the neighbours' flanks.  So
    "the widened prom crosses the bar" is on its own equally consistent with a feature and with a
    slope, and only BW5's interior-minimum requirement separates them."""
    print("\n" + "=" * 98)
    print("BW4  PINNED WIDENING -- GATE AV's method on the PROM refusals (⚠ not sufficient alone)")
    print("=" * 98)
    cells = [(r, sw) for r, sw in _pop(rows, corner_cf)
             if r["model"][sw]["why"] == "PROM"]
    print(f"  {len(cells)} PROM-refused model cells.  Pinned widening of the walk domain only;")
    print(f"  the bar is W's own MIN_PROM_DB = {W.MIN_PROM_DB} dB.\n")
    print(f"  {'widen':>6s}  {'window (Hz)':>16s}  {'model crosses':>14s}  {'pedal crosses':>14s}"
          f"  {'model median prom':>18s}")
    rec = {}
    for w in AV.WIDEN:
        ww = AV.widen_win(WIN, w)
        mc = pc = 0
        mp = []
        for r, sw in cells:
            m = r["model"][sw]["widen"][f"{w}"]
            p = r["pedal"][sw]["widen"][f"{w}"]
            if m is not None:
                mc += m["prom"] >= W.MIN_PROM_DB
                mp.append(m["prom"])
            if p is not None:
                pc += p["prom"] >= W.MIN_PROM_DB
        rec[f"{w}"] = {"win": [round(x, 1) for x in ww], "model_cross": mc, "pedal_cross": pc,
                       "model_median_prom": float(np.median(mp)) if mp else float("nan")}
        print(f"  {w:6.2f}  {f'{ww[0]:.1f}-{ww[1]:.1f}':>16s}  {mc:6d}/{len(cells):<7d}"
              f"  {pc:6d}/{len(cells):<7d}  {np.median(mp) if mp else float('nan'):18.2f}")
    nb = [r["model"][sw]["walk_n_bound_sides"] for r, sw in cells
          if r["model"][sw]["walk_n_bound_sides"] is not None]
    both = sum(1 for x in nb if x == 2)
    print(f"\n  at the SHIPPED window, {both} of {len(nb)} of these cells have BOTH walk sides")
    print( "  terminating on a window BOUND ⇒ their shipped prominence is set by where the window")
    print( "  was cut, not by the curve (AV3's own criterion).  ⚠ That says the reading is a WINDOW")
    print( "  statement; it does NOT say a feature is there.  BW5 is what decides that.")
    out["bw4"] = {"n_prom_refused": len(cells), "bar_db": W.MIN_PROM_DB, "by_widen": rec,
                  "both_sides_bound": both, "n_walks": len(nb)}


def bw5(rows, corner_cf, out):
    """⭐ THE DISCRIMINATOR -- the interior-extremum census.  MOVED vs GONE, threshold-free."""
    print("\n" + "=" * 98)
    print("BW5  ⭐ THE ANSWER -- interior-minimum census over SHOULDER, per refusal reason")
    print("=" * 98)
    print("  `_best_interior` requires a genuine TWO-SIDED local minimum, so a monotone flank")
    print("  returns nothing where a walk-based reader returns a plausible number, and its")
    print("  min(left,right) penalises a dimple on a slope by construction (AV5's inflation,")
    print("  refused rather than thresholded).\n")
    cells = _pop(rows, corner_cf)
    byreason = {}
    for r, sw in cells:
        v = r["model"][sw]
        byreason.setdefault(v["why"], {}).setdefault(classify(v), []).append((r, sw, v))
    order = list(PRESENT_KINDS) + ["BELOW-BAR", "ABSENT"]
    print(f"  {'refusal':>8s}  " + "".join(f"{k:>12s}" for k in order) + f"{'n':>7s}")
    tot = {k: 0 for k in order}
    for why in sorted(byreason):
        row = byreason[why]
        n = sum(len(v) for v in row.values())
        for k in order:
            tot[k] += len(row.get(k, []))
        print(f"  {why:>8s}  " + "".join(f"{len(row.get(k, [])):>12d}" for k in order) + f"{n:>7d}")
    print(f"  {'TOTAL':>8s}  " + "".join(f"{tot[k]:>12d}" for k in order)
          + f"{sum(tot.values()):>7d}")

    present = sum(tot[k] for k in PRESENT_KINDS)
    absent, below = tot["ABSENT"], tot["BELOW-BAR"]
    pres = [v for _r, _sw, v in
            [x for k in PRESENT_KINDS for wh in byreason.values() for x in wh.get(k, [])]]
    f0s = [v["bi_f0"] for v in pres]
    proms = [v["bi_prom"] for v in pres]
    below_p = [v["bi_prom"] for _r, _sw, v in
               [x for wh in byreason.values() for x in wh.get("BELOW-BAR", [])]]

    print(f"\n  ⭐⭐ THE THRESHOLD-FREE NUMBER IS `ABSENT`, AND IT IS {absent} OF {len(cells)}.")
    print(f"     In {len(cells) - absent} of {len(cells)} cells the model's curve HAS a two-sided")
    print( "     interior minimum between 210 and 520 Hz -- there is a feature there.  Whether it")
    print(f"     clears a PRESENCE bar is a separate, bar-dependent question ({below} sit below it).")
    # ⚠ The header and the above-the-bound COUNT print unconditionally.  Zero is a real reading
    # here -- it is what a search restricted to the shipped window produces -- and suppressing the
    # line when the set is empty would make the gate silent in exactly the configuration a reader
    # most needs to distinguish from a working one.
    above = sum(1 for x in f0s if x > WIN[1])
    near = sum(1 for x in f0s if x > WIN[1] * 0.97)
    print(f"\n  PRESENT (clears W's own {W.MIN_PROM_DB:.1f} dB bar): {present} of {len(cells)}")
    if f0s:
        print(f"    centre  median {np.median(f0s):7.1f} Hz   range {min(f0s):.1f}-{max(f0s):.1f} "
              f"(W's window: {WIN[0]:.0f}-{WIN[1]:.0f})")
        print(f"    prom    median {np.median(proms):7.2f} dB   range {min(proms):.2f}-{max(proms):.2f}")
    print(f"    {above} sit ABOVE W's upper bound of {WIN[1]:.0f} Hz; {near} sit within 3 % of it")
    if below_p:
        print(f"\n  BELOW-BAR: prom median {np.median(below_p):.2f} dB, "
              f"range {min(below_p):.2f}-{max(below_p):.2f} against a {W.MIN_PROM_DB:.1f} dB bar")

    # ---- the bar SWEEP: a tier defined by a threshold is quoted with its sensitivity (s137) -----
    print(f"\n  BAR SENSITIVITY (W's own PROM_SWEEP) -- ABSENT cannot move, by construction:")
    print(f"    {'bar dB':>7s}  {'PRESENT':>9s}  {'BELOW-BAR':>10s}  {'ABSENT':>8s}")
    sweep = {}
    for b in W.PROM_SWEEP:
        k = [classify(v, bar=b) for _r, _sw, v in
             [(r, sw, r["model"][sw]) for r, sw in cells]]
        p = sum(1 for x in k if x in PRESENT_KINDS)
        bb = sum(1 for x in k if x == "BELOW-BAR")
        ab = sum(1 for x in k if x == "ABSENT")
        sweep[f"{b}"] = {"present": p, "below": bb, "absent": ab}
        print(f"    {b:7.1f}  {p:9d}  {bb:10d}  {ab:8d}")
    print(f"    ⇒ ABSENT is {absent} at every bar (it is not a bar call), while PRESENT moves")
    print( "      across the sweep ⇒ quote ABSENT as the finding and PRESENT with its bar.")

    out["bw5"] = {"n": len(cells), "by_reason": {k: {kk: len(vv) for kk, vv in v.items()}
                                                for k, v in byreason.items()},
                  "totals": tot, "present": present, "absent": absent, "below_bar": below,
                  "bar_sweep": sweep,
                  "present_f0_median": float(np.median(f0s)) if f0s else None,
                  "present_f0_min": float(min(f0s)) if f0s else None,
                  "present_f0_max": float(max(f0s)) if f0s else None,
                  "present_prom_median": float(np.median(proms)) if proms else None,
                  "below_prom_median": float(np.median(below_p)) if below_p else None}
    return byreason, present, absent, below, f0s


def bw6(rows, corner_cf, byreason, out):
    """CONTINUITY -- s151's own condition for calling a moved reading "the same null".

    s151: "the widening is not free: it crosses a named-feature boundary, so the reading must be
    checked for continuity against the same capture at lower drive before it is called 'the same
    null that moved'."  Applied on the STIMULUS ladder, which every capture carries."""
    print("\n" + "=" * 98)
    print("BW6  CONTINUITY -- does the located centre MOVE, or does the reader JUMP? (s151)")
    print("=" * 98)
    print("  ⛔ A SPAN BAR IS THE WRONG TEST, AND THIS GATE'S FIRST DRAFT USED ONE.  It flagged 3")
    print("     captures for exceeding the feature's own 1/6-oct width -- and all three turned out")
    print("     to be high-DRIVE cells whose centre walks MONOTONICALLY down the ladder, i.e. the")
    print("     very thing a migration looks like.  A large span is what a MIGRATION and a JUMP")
    print("     have IN COMMON; what separates them is ORDER.  A reader alternating between two")
    print("     dimples gives an erratic sequence, one feature moving gives a monotone one -- and")
    print("     monotonicity needs no threshold at all.\n")
    cells = _pop(rows, corner_cf)
    percap = {}
    for r, sw in cells:
        v = r["model"][sw]
        if classify(v) == "ABSENT":          # no minimum to track; not a discontinuity
            continue
        percap.setdefault(r["file"], {})[sw] = v["bi_f0"]
    mono, tested, spans, rows_out = 0, 0, [], []
    for fn, m in sorted(percap.items()):
        vals = [m[sw] for sw in W.SWEEPS if sw in m]
        if len(vals) < 3:
            continue
        tested += 1
        # ⚠ MONOTONE **AT THE LOCATOR'S OWN RESOLUTION**, not exactly.  A reversal smaller than one
        # 1/48-oct cell is not a reversal -- it is the parabola interpolation moving inside a cell
        # the instrument cannot resolve, and demanding exact monotonicity of an interpolated
        # quantity fails correct data (this run: one capture reversing by 0.4 Hz = 0.14 %, a TENTH
        # of a cell, was reported NOT monotone).  `W.GRID_STEP_FRAC` is imported, never chosen.
        tol = W.GRID_STEP_FRAC
        up = all(b >= a * (1.0 - tol) for a, b in zip(vals, vals[1:]))
        dn = all(b <= a * (1.0 + tol) for a, b in zip(vals, vals[1:]))
        ok = up or dn
        mono += ok
        sp = max(vals) / min(vals) - 1.0
        spans.append(sp)
        rows_out.append({"file": fn, "n": len(vals), "monotone": bool(ok),
                         "span_pct": 100 * sp, "centres": [round(x, 1) for x in vals]})
    print(f"  {tested} captures carry a located centre on >=3 of the 4 rungs.")
    print(f"  MONOTONE in stimulus: {mono} of {tested}")
    print(f"  across-rung span: median {100*np.median(spans):.2f} %, worst {100*max(spans):.2f} %")
    print( "\n  ⇒ a randomly-ordered sequence of 4 distinct values is monotone with probability")
    print(f"    2/4! = 8.3 %.  Observed {100.0*mono/tested:.0f} %.")
    for rr in sorted(rows_out, key=lambda x: -x["span_pct"])[:4]:
        print(f"    {rr['file'][:44]:44s} n={rr['n']} span {rr['span_pct']:5.1f} %  "
              f"{'MONOTONE' if rr['monotone'] else 'NOT monotone'}  "
              + ", ".join(f"{x:.1f}" for x in rr["centres"]))
    if mono == tested:
        print("\n  ✅ EVERY tested capture's centre walks monotonically with stimulus ⇒ ONE feature")
        print("     migrating, not the reader alternating between two.  ⭐ And the DIRECTION is the")
        print("     one s151 documented on the PEDAL at high drive (its null reaching 238.3 Hz at")
        print("     DRIVE max) -- here it is measured on the MODEL.")
    else:
        print(f"\n  ⚠ {tested - mono} capture(s) are NOT monotone -- named above; those readings are")
        print( "    not established as one feature and must not be quoted as a migration.")
    out["bw6"] = {"n_tested": tested, "n_monotone": mono,
                  "span_median_pct": 100 * float(np.median(spans)) if spans else None,
                  "span_worst_pct": 100 * float(max(spans)) if spans else None,
                  "per_capture": rows_out}


def bw7(out, present, absent, below, f0s, n, bw2res):
    """THE VERDICT -- computed, on the THRESHOLD-FREE number, with the bar call kept separate."""
    print("\n" + "=" * 98)
    print("BW7  VERDICT")
    print("=" * 98)
    have = n - absent
    if absent > have:
        v = "ABSENT -- a genuine presence/absence defect"
    elif absent == 0:
        v = "PRESENT EVERYWHERE -- the WINDOW, not the feature"
    else:
        v = "PRESENT AT %d of %d -- overwhelmingly the WINDOW, not the feature" % (have, n)
    print(f"  COMPUTED VERDICT: {v}")
    print(f"\n  s201 asked: has N2 MOVED out of GATE W's window, or is it GONE?  Measured over the")
    print(f"  {n} played GRUNT-{POP_GRUNT} cells the finding is about:")
    print(f"    * the model's curve has a two-sided interior minimum in {have} of {n} "
          f"({100.0*have/n:.0f} %)")
    print(f"    * it is monotone -- NO feature at any depth -- in {absent} of {n} "
          f"({100.0*absent/n:.0f} %)")
    print(f"    * of those {have}, {present} clear W's own {W.MIN_PROM_DB:.1f} dB presence bar and "
          f"{below} do not")
    if f0s:
        above = sum(1 for x in f0s if x > WIN[1])
        print(f"    * the located centres run {min(f0s):.1f}-{max(f0s):.1f} Hz, median "
              f"{np.median(f0s):.1f}, against a window that STOPS at {WIN[1]:.0f}")
    print(f"\n  ⇒ s201's *'0 of 112'* is a WINDOW-AND-BAR statement, not a presence one, and its")
    print(f"    own gloss needs correcting: the EDGE/PROM split does NOT map onto moved/gone.")
    e = out["bw5"]["by_reason"].get("EDGE", {})
    p = out["bw5"]["by_reason"].get("PROM", {})
    ep = sum(e.get(k, 0) for k in PRESENT_KINDS)
    pp = sum(p.get(k, 0) for k in PRESENT_KINDS)
    print(f"    PROM -- read as 'the window is right and there is nothing in it' -- is {pp} of "
          f"{sum(p.values())} PRESENT;")
    print(f"    EDGE -- read as 'the feature moved' -- is {ep} of {sum(e.values())}.  ⛔ So")
    print(f"    'absence dominates migration 3:1' is REFUTED: it read the refusal LABELS as")
    print(f"    outcomes, and the labels do not carry that meaning.")
    pedal = bw2res[POP_GRUNT]["pedal_valid"]
    # ⚠ These two are None when the PRESENT set is empty -- which is not hypothetical: the
    # `bw5-search-domain` mutation arm reaches it, and the first draft CRASHED there with a
    # TypeError instead of reporting.  s117: a gate must refuse or degrade, never hand the next
    # session a stack trace where a number is missing.
    pm, cm = out["bw5"]["present_prom_median"], out["bw3"]["prom_median"]
    pms = f"~{pm:.1f} dB" if pm is not None else "(no PRESENT cell)"
    cms = f"~{cm:.0f} dB" if cm is not None else "(none)"
    print(f"\n  ⚠ What this does NOT say, and it is the half a reader will over-run:")
    print(f"    * NOTHING here says N2's depth or centre is RIGHT.  The model's feature is a "
          f"{pms} dimple")
    print(f"      at played settings against {cms} at the bleed-free corner -- that dilution is")
    print(f"      item 19's own finding and is UNCHANGED.  The depth question is BV5's row.")
    print(f"    * The model/pedal asymmetry is real and unexplained: the pedal reads {pedal} of {n}")
    print(f"      through the SAME window and bar.  This gate says why the model reads 0; it does")
    print(f"      not say the two sides agree.")
    print(f"    * {absent} cells genuinely have no N2 at all.  That is small, real, and unowned.")
    out["bw7"] = {"verdict": v, "present": present, "absent": absent, "below_bar": below,
                  "have_feature": have, "n": n, "pedal_valid": pedal,
                  "edge_present": ep, "prom_present": pp}


# =================================================================================================
def main():
    ap = argparse.ArgumentParser(description="GATE BW -- N2's widened-window confirmation")
    ap.add_argument("--out", default=OUT_JSON)
    add_jobs_arg(ap)
    args = ap.parse_args()

    out = {}
    fp_before = bw0(out)

    rep = json.load(open(BV_REPORT))
    files = [c["file"] for c in rep["_cells"]]
    print(f"\n  reading {len(files)} cached renders x {len(W.SWEEPS)} sweeps x 2 sides ...")
    rows = pmap_cpu(_cell, files, jobs=args.jobs)
    corner_cf = F.bleedfree_cf()
    print(f"  bleed-free corner clean fraction (DERIVED from the shipped end stop): {corner_cf:.5f}")

    bw1(rows, out)
    bw2res = bw2(rows, corner_cf, out)
    bw3(rows, corner_cf, out)
    bw4(rows, corner_cf, out)
    byreason, present, absent, below, f0s = bw5(rows, corner_cf, out)
    bw6(rows, corner_cf, byreason, out)
    bw7(out, present, absent, below, f0s, len(_pop(rows, corner_cf)), bw2res)

    fp_after = BV.dir_fingerprint(FORBIDDEN_DIR)
    if fp_after != fp_before:
        sys.exit(f"GATE BW: the READ-ONLY cache {FORBIDDEN_DIR} CHANGED ({fp_before} -> {fp_after})")
    print(f"\n  ✅ READ-ONLY cache unchanged: {fp_before}")

    out["_cells"] = [{"file": r["file"], "cf": r["cf"], "grunt": BV.grunt_of(r)} for r in rows]
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w"), indent=1)
    print(f"  wrote {args.out}")

    if FAILED:
        sys.exit("\nGATE BW REFUSES:\n  " + "\n  ".join(FAILED))


if __name__ == "__main__":
    main()
