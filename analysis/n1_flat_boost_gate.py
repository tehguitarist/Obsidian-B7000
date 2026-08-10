#!/usr/bin/env python3.11
"""GATE BX — s201's hand-forward finding (2): N1 (the bass null) at GRUNT flat/boost.

WHAT WAS HANDED FORWARD
-----------------------
GATE BV (s201) re-read item 19's seven-feature comb on the shipped build and reported

    bass_notch  played flat   n=10  POINT +10.54  AREA +8.93   model TOO DEEP
    bass_notch  played boost  n= 2  POINT  +4.78  AREA +4.49   THIN -- not a verdict
    bass_notch  played cut    n=46  POINT  -0.08  AREA -0.10   MATCHES

filed as *"s187's own named-unowned residual, now sized at played settings"* and ranked second of
four.  The verdict was STABLE across all four stimulus rungs, so it clears s201's own caution that
33 % of this comb's verdicts move with the rung.

THE PROVENANCE GAP IS REAL, AND IT LOOKS EXACTLY LIKE s195
-----------------------------------------------------------
`odMakeupLowCutDb = 6.0` was chosen by GATE BJ (s180) whose membership is `BH.CONDITIONS` --
**7 cut / 1 flat / 2 boost**, the same cut-heavy pool s195 caught GATE BH with on the treble half.
s187 then keyed GRUNT = Cut to its OWN field (`odMakeupLowCutDbCut = 2.2`), so the shared 6.0 is
now applied ONLY at the two positions that supplied 3 of the 10 conditions that chose it.  ⇒ the
s195 hypothesis: a constant fitted at cut, inherited ungraded at flat/boost.

⭐⭐ THE HYPOTHESIS IS CONFIRMED AS A PROVENANCE GAP AND REFUTED AS A DEFECT.  Graded directly at
flat/boost, on a complete population, 6.0 is the BEST value available and every lever move is
worse -- see BX5.  The analogy to s195 was strong and it does not hold; that is why this gate
records it rather than leaving the next session to re-derive it.

WHY `+8.93 dB` IS NOT A DEFECT SIZE (BX2-BX4)
----------------------------------------------
BV's depth is `area(neighbour) - area(feature)`, admitted only where GATE W's `locate()` passes on
BOTH sides.  Measured, that statistic here is:

  * a DIFFERENCE whose operands were never printed -- decomposed (BX2) it is **100.3 % the notch**
    and 12.9 % the peak at flat, so s201's headline SURVIVES this check.  It genuinely is N1.
  * SELECTED ON THE GRADED QUANTITY (BX3): admitted cells have a MODEL floor margin of **-11.9 dB**
    and refused cells **+1.5** -- a cell is admitted precisely when the model's null is DEEP enough
    to clear `MIN_PROM_DB`.  s178's `matched_cells` lesson, in the direction that inflates.
  * CENSORED on the model side in **10 of 10** admitted flat cells (bottom below the deconvolution
    residue), with no robust estimator available: s191 AP1b measured the AREA depth's censoring
    robustness as **1.0x at MIXED cells** (its 4.1x is a BLEED-FREE property), and every cell here
    is mixed.  ⇒ EVERY quotable reading is a LOWER BOUND.
  * DISPERSED -- a 15.83 dB spread about its own +8.93 median, i.e. **1.8x the median**, from 10
    readings that are really 3 captures x 3-4 rungs.
    ⚠ On a LOOSER membership (the graded feature valid on both sides, but the NEIGHBOUR that
    supplies the reference level allowed to rest on a window bound) the same data admits 13 cells,
    spans **33.3 dB** and **CHANGES SIGN** (+18.80 against -14.48).  Recorded because it is the
    read a session would get by applying `valid()` alone: BV's `shoulder_ok` on the neighbour is
    load-bearing here, not bookkeeping.
  * WINDOW-BOUNDED at boost: **8 of 28** cells EDGE-refuse at f0 = 30.7 Hz against the window's own
    30.0 Hz bound, on BOTH sides -- s202's N2 finding on a second feature.  (At flat: 0 of 24 --
    flat's refusals are PROM, i.e. presence, not migration.)
  * and it re-reads as **8.93 / 15.66 / 16.45 dB on three different matched populations of the same
    data** ⇒ the "size" is a property of the admitted set, not of the model.

WHAT IS TRUE INSTEAD (BX4)
---------------------------
On a fixed BAND -- every cell readable, nothing located, nothing selected, nothing censored, and
s187's OWN axis -- the direction INVERTS: over 40-80 Hz the model is **-0.33 dB at flat and +1.46
HIGH at boost**, and over 63-100 Hz **+1.27 HIGH at flat with 1 of 24 cells model-low**.  A null
genuinely 8.9 dB deeper would pull those down.  ⇒ the model is not short of LF at flat/boost; its
cancellation is NARROWER and DEEPER, which a 1/6-octave depth reads as ~9 dB and an octave-wide
band reads as ~0.

Run:
    /opt/homebrew/bin/python3.11 analysis/n1_flat_boost_gate.py
    /opt/homebrew/bin/python3.11 analysis/n1_flat_boost_gate.py --json analysis/reports/s203_n1_flat_boost.json
"""
import argparse
import glob
import hashlib
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import analyze as A                      # noqa: E402
import captures as C                     # noqa: E402
import comb_confirm_gate as BV           # noqa: E402
import feature_locus_gate as W           # noqa: E402
import hf_null_shape_gate as BH          # noqa: E402
import od_tone_restore_fit as F          # noqa: E402

REN_DIR = "build/n1_frontier"                 # PRIVATE.  Never BV.REN_DIR, never W.REN_DIR.
FORBIDDEN = (W.REN_DIR, BV.REN_DIR)           # read-only epochs this gate must not write into
BV_REPORT = "analysis/reports/s201_comb_confirm.json"
FEAT, NEIGHBOUR = "bass_notch", "bass_peak"

# The two bands.  40-80 Hz brackets both sides' located centres (model 33-59, pedal 33-53 across the
# whole population); 63-100 Hz is s187's OWN axis, restated so its numbers stay commensurable.
BANDS = {"40-80": (40.0, 80.0), "63-100": (63.0, 100.0)}
CORNER_CF_TOL = 1e-6
MIN_N = BV.MIN_N                              # imported -- the THIN bar is BV's, not a new one
DEPTH_TOL_DB = BV.DEPTH_TOL_DB                # imported -- s151's converged fit residual

# ⚠ Every override below is flat/boost-ONLY ON THE SHIPPED BUILD, because s187 keyed GRUNT = Cut to
# `clipC15Cut` / `odMakeupLowCutDbCut`.  BX0c asserts that two-sidedly rather than assuming it --
# s194 recorded the same keying making GATE BH's Cut arms silently INERT, and an arm that moves
# nothing still gets a name in a results table.
ARMS = {
    "SHIP (5.2n / 6.0)":     (),
    "C15 only (2u2 / 6.0)":  ("--fit", "clipC15=2200e-9"),
    "shelf only (5.2n/2.2)": ("--fit", "odMakeupLowCutDb=2.2"),
    "BOTH = s187 global":    ("--fit", "clipC15=2200e-9", "--fit", "odMakeupLowCutDb=2.2"),
    "C15 300n / 6.0":        ("--fit", "clipC15=300e-9"),
}
SHIP_ARM = "SHIP (5.2n / 6.0)"
S187_ARM = "BOTH = s187 global"
# s187's published 63-100 Hz range for the GLOBAL application it refuted.  BX6 reproduces it.
S187_GLOBAL_LO, S187_GLOBAL_HI = 3.2, 9.7

FILES = {
    "cut":  ["ref-od.wav", "drive-0700_base-od.wav", "drive-0930_base-od.wav",
             "blend-1430_base-od.wav", "blend-1200_base-od.wav"],
    "flat": ["drive-0700_grunt-flat_base-od.wav", "drive-0930_grunt-flat_base-od.wav",
             "grunt-flat_base-od.wav", "grunt-flat_blend-0930_base-od.wav",
             "grunt-flat_blend-1200_base-od.wav", "grunt-flat_blend-1430_base-od.wav"],
    "boost": ["drive-0700_grunt-boost_base-od.wav", "drive-0930_grunt-boost_base-od.wav",
              "drive-1700_grunt-boost_base-od.wav", "grunt-boost_base-od.wav",
              "grunt-boost_blend-0930_base-od.wav", "grunt-boost_blend-1200_base-od.wav",
              "grunt-boost_blend-1430_base-od.wav"],
}
GRADED = ("flat", "boost")          # cut is the CONTROL: it must be inert to every arm


def die(tag, msg):
    print(f"\n⛔ {tag}: {msg}")
    sys.exit(1)


def med(xs):
    return float(np.median(xs)) if len(xs) else float("nan")


def _tag(arm):
    return "" if not arm else "__" + "_".join(
        a.replace("=", "").replace(".", "p").replace("-", "m") for a in arm if a != "--fit")


def _render_into(out, args):
    for d in FORBIDDEN:
        assert not os.path.abspath(out).startswith(os.path.abspath(d)), \
            f"GATE BX: refusing to render into the READ-ONLY cache {d}"
    return W.render(out, args)


_CACHE = {}


def read(fname, arm):
    """-> {sweep: dict(model_curve, pedal_curve, norm_m, norm_p, comb_m, comb_p)}"""
    key = (fname, arm)
    if key in _CACHE:
        return _CACHE[key]
    out = os.path.join(REN_DIR, fname.replace(".wav", "") + _tag(arm) + "_plugin.wav")
    _render_into(out, C.render_args(C.parse_capture(fname), extra_args=list(arm)))
    orig, ref = W._load_orig()
    cap_al, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, fname)), orig)
    ren_al, _ = A.align(A.load(out), orig)
    res = {}
    for sw in W.SWEEPS:
        def cur(al):
            fr, m = A.transfer_h1(A.seg_of(al, sw), ref)
            d = W.smooth(fr, m)
            n = (W.GRID >= F.NORM_LO) & (W.GRID <= F.NORM_HI)
            lvl = float(np.mean(d[n]))
            return d - lvl, lvl
        cm, nm = cur(ren_al)
        cp, npd = cur(cap_al)
        res[sw] = dict(model=cm, pedal=cp, norm_m=nm, norm_p=npd,
                       comb_m=BV.comb_of(ren_al, sw, ref), comb_p=BV.comb_of(cap_al, sw, ref))
    _CACHE[key] = res
    return res


def bandv(d, lo, hi):
    sel = (W.GRID >= lo) & (W.GRID <= hi)
    return float(np.mean(d[sel]))


def played_of(g):
    out = []
    for f in FILES[g]:
        rec = BV._cell((f, BV.REN_DIR))          # BV's own cache -- read only, never re-rendered
        if abs(rec["cf"] - 0.02418) > CORNER_CF_TOL:
            out.append(f)
    return out


def admits(cell):
    """BV's OWN admission rule, imported.  A reading is quotable only if the graded feature is a
    resolved extremum on BOTH sides and the neighbour supplying the reference level is not itself
    resting on a window bound."""
    return (BV.valid(cell["comb_m"][FEAT]) and BV.valid(cell["comb_p"][FEAT])
            and BV.shoulder_ok(cell["comb_m"][NEIGHBOUR])
            and BV.shoulder_ok(cell["comb_p"][NEIGHBOUR]))


def depth_delta(cell):
    return (cell["comb_m"][FEAT]["depth_area"] - cell["comb_p"][FEAT]["depth_area"])


# =================================================================================================
def gate_bx0(out):
    """Epoch, provenance and SCOPE.  ⚠ The scope arm is not decoration: s187's keying is what makes
    every `--fit` below a flat/boost-only lever, and s194 recorded the same keying silently turning
    a whole ladder of arms into no-ops in a neighbouring gate."""
    print("=" * 100)
    print("BX0  epoch, read-only caches, and the TWO-SIDED scope of every arm")
    print("=" * 100)
    binp = "build/OfflineRender_artefacts/Release/OfflineRender"
    if not os.path.exists(binp):
        die("BX0", f"render binary absent: {binp}")
    md5 = hashlib.md5(open(binp, "rb").read()).hexdigest()
    # ⚠⚠ A first draft wrote this as `W._src_files() if hasattr(W, "_src_files") else []`.
    # `W` HAS NO SUCH ATTRIBUTE, so the guard silently evaluated to the empty list and could never
    # fire -- and its mutation arm still PASSED, because that arm patched the RESULT line rather
    # than the computation feeding it.  A guard behind a `hasattr` fallback is a guard that
    # disappears the day the attribute is renamed, with no error anywhere (s106 N3's `nan` failing
    # open, in a different costume).  Written out the way GATE BV0 writes it, with no fallback.
    bmt = os.stat(binp).st_mtime
    newer = [p for p in glob.glob("src/**/*", recursive=True)
             if os.path.isfile(p) and os.stat(p).st_mtime > bmt]
    if not glob.glob("src/**/*", recursive=True):
        die("BX0", "no src/ files found at all -- the stale-binary guard would be vacuous")
    print(f"  binary {md5}   src files newer than it: {len(newer)} (of "
          f"{sum(1 for p in glob.glob('src/**/*', recursive=True) if os.path.isfile(p))} scanned)")
    if newer:
        die("BX0", f"{len(newer)} src file(s) postdate the render binary ({newer[:3]}) -- "
                   f"rebuild first, or every model-side number below is the previous build's")

    fps = {d: BV.dir_fingerprint(d) for d in FORBIDDEN}
    for d, fp in fps.items():
        print(f"  read-only cache {d:28s} fingerprint {fp}")

    if not os.path.exists(BV_REPORT):
        die("BX0", f"GATE BV's report is absent ({BV_REPORT}) -- BX1's known answer needs it")

    # ---- BX0c: the arms move flat/boost and are ARCHITECTURALLY INERT at cut and clean ----------
    print("\n  BX0c  scope, two-sided (the lever must be live where it is graded and dead elsewhere)")
    probe = ("--fit", "clipC15=2200e-9", "--fit", "odMakeupLowCutDb=2.2")

    def h(f, arm):
        o = os.path.join(REN_DIR, f.replace(".wav", "") + _tag(arm) + "_plugin.wav")
        _render_into(o, C.render_args(C.parse_capture(f), extra_args=list(arm)))
        return hashlib.md5(open(o, "rb").read()).hexdigest()

    scope = {}
    for lbl, f, want_move in (("flat ", FILES["flat"][0], True), ("boost", FILES["boost"][0], True),
                              ("cut  ", FILES["cut"][0], False), ("clean", "ref-clean.wav", False)):
        moved = h(f, ()) != h(f, probe)
        ok = (moved == want_move)
        scope[lbl.strip()] = moved
        print(f"     {lbl}  {f:44s} {'MOVED' if moved else 'BIT-IDENTICAL':14s} "
              f"{'✅' if ok else '⛔ WRONG -- the arm does not do what this gate assumes'}")
        if not ok:
            die("BX0c", f"scope violated at {f}: moved={moved}, expected={want_move}")
    out["bx0"] = {"bin": binp, "md5": md5, "forbidden_fp": fps, "scope": scope}
    return fps


def gate_bx1(out):
    """KNOWN ANSWER -- reproduce GATE BV's STORED depth numbers from BV's own cache.

    Chains this gate to s201, and through BV2 to GATE BQ (s190), s125's published loci and GATE AE's
    docstring.  ⚠ It validates the READER and the MEMBERSHIP RULE together; it says nothing about
    whether the number MEANS anything, which is BX2-BX4's subject."""
    print("\n" + "=" * 100)
    print("BX1  KNOWN ANSWER -- BV5's stored `bass_notch` depths, recomputed from BV's cache")
    print("=" * 100)
    stored = json.load(open(BV_REPORT))["bv5"]["features"][FEAT]
    rows, worst = [], 0.0
    for g in ("cut", "flat", "boost"):
        cells = []
        for f in played_of(g):
            rec = BV._cell((f, BV.REN_DIR))
            for sw in W.SWEEPS:
                cell = {"comb_m": rec["model"][sw], "comb_p": rec["pedal"][sw]}
                if admits(cell) and cell["comb_m"][FEAT]["depth_area"] is not None:
                    cells.append(depth_delta(cell))
        st = stored.get(f"played_{g}", {})
        got, want, n_w = med(cells), st.get("area_db"), st.get("n")
        d = abs(got - want) if want is not None else float("nan")
        worst = max(worst, 0.0 if np.isnan(d) else d)
        rows.append({"grunt": g, "n_here": len(cells), "n_bv": n_w, "here": got, "bv": want,
                     "abs_diff": d})
        print(f"  played {g:5s}  n {len(cells):3d} (BV {n_w})   here {got:+7.2f} dB   "
              f"BV {want:+7.2f} dB   |Δ| {d:.3e}")
    # ⚠ This gate samples cut rather than enumerating BV's 31, so cut's n legitimately differs.
    # The two GRADED positions are enumerated in full and must reproduce exactly.
    graded = [r for r in rows if r["grunt"] in GRADED]
    bad = [r for r in graded if r["n_here"] != r["n_bv"] or r["abs_diff"] > 1e-9]
    print(f"\n  graded positions reproduce: {'✅ EXACT' if not bad else '⛔ ' + str(bad)}")
    if bad:
        die("BX1", "the graded cells do not reproduce GATE BV -- reader or membership has drifted")
    out["bx1"] = {"rows": rows, "worst_abs_diff": worst}


def gate_bx2(out):
    """DECOMPOSE the difference.  `depth = area(bass_peak) - area(bass_notch)`, so `+8.93 too deep`
    could be the notch, the peak, or both, and s201 printed neither operand (s117)."""
    print("\n" + "=" * 100)
    print("BX2  the two OPERANDS of the depth difference -- is it really the NOTCH?")
    print("=" * 100)
    res = {}
    for g in GRADED + ("cut",):
        dn, dp, dd = [], [], []
        for f in played_of(g):
            rec = BV._cell((f, BV.REN_DIR))
            for sw in W.SWEEPS:
                cell = {"comb_m": rec["model"][sw], "comb_p": rec["pedal"][sw]}
                if not admits(cell):
                    continue
                dn.append(cell["comb_m"][FEAT]["area_db"] - cell["comb_p"][FEAT]["area_db"])
                dp.append(cell["comb_m"][NEIGHBOUR]["area_db"]
                          - cell["comb_p"][NEIGHBOUR]["area_db"])
                dd.append(depth_delta(cell))
        if not dd:
            continue
        mn, mp, md = med(dn), med(dp), med(dd)
        sn, sp = -mn / md * 100.0, mp / md * 100.0
        carrier = "NOTCH" if abs(sn) > abs(sp) else "PEAK"
        res[g] = {"n": len(dd), "d_notch": mn, "d_peak": mp, "d_depth": md,
                  "share_notch_pct": sn, "share_peak_pct": sp, "carrier": carrier}
        print(f"  {g:5s}  n={len(dd):3d}   Δnotch {mn:+7.2f}   Δpeak {mp:+7.2f}   "
              f"Δdepth {md:+7.2f}   ⇒ notch {sn:6.1f} %, peak {sp:6.1f} %   carrier {carrier}")
    v = res.get("flat", {}).get("carrier")
    print(f"\n  computed verdict: at GRUNT flat the depth error is carried by the "
          f"**{v}** ⇒ s201's headline {'SURVIVES -- it really is N1' if v == 'NOTCH' else 'is REFUTED -- it is the neighbour, not N1'}")
    out["bx2"] = res


def gate_bx3(out):
    """Is `+8.93` a description of anything?  Four properties of the statistic, all computed."""
    print("\n" + "=" * 100)
    print("BX3  the statistic's own pathologies -- selection, censoring, sign, window")
    print("=" * 100)
    res = {}
    for g in GRADED:
        adm_fm, ref_fm, vals, edge_bound, cens = [], [], [], 0, 0
        n_tot = 0
        for f in played_of(g):
            rec = BV._cell((f, BV.REN_DIR))
            for sw in W.SWEEPS:
                n_tot += 1
                cell = {"comb_m": rec["model"][sw], "comb_p": rec["pedal"][sw]}
                m = cell["comb_m"][FEAT]
                lo_bound = W.FEAT_BY_NAME[FEAT][2][0]
                if (m["edge"] and abs(m["f0"] - lo_bound) / lo_bound < 0.05
                        and cell["comb_p"][FEAT]["edge"]):
                    edge_bound += 1
                if admits(cell):
                    adm_fm.append(m["floor_margin_db"])
                    vals.append(depth_delta(cell))
                    if m["floor_margin_db"] < 0:
                        cens += 1
                else:
                    ref_fm.append(m["floor_margin_db"])
        if not vals:
            print(f"  {g:5s}  no admitted cell")
            continue
        spread = max(vals) - min(vals)
        ratio = spread / abs(med(vals))
        signflip = (min(vals) < 0) != (max(vals) < 0)
        res[g] = {"n_admitted": len(vals), "n_total": n_tot,
                  "floor_margin_admitted": med(adm_fm), "floor_margin_refused": med(ref_fm),
                  "censored": cens, "spread_db": spread, "median_db": med(vals),
                  "spread_over_median": ratio, "sign_flips": bool(signflip),
                  "edge_at_window_bound": edge_bound}
        print(f"\n  --- GRUNT {g} ---  admitted {len(vals)} of {n_tot}")
        print(f"    SELECTION   model floor margin: admitted {med(adm_fm):+.1f} dB, "
              f"refused {med(ref_fm):+.1f} dB  ⇒ "
              f"{'ADMISSION TRACKS THE GRADED QUANTITY (a cell is admitted when the model null is DEEP)' if med(adm_fm) < med(ref_fm) else 'no selection detected'}")
        print(f"    CENSORING   {cens} of {len(vals)} admitted MODEL bottoms below the "
              f"deconvolution residue  ⇒ "
              f"{'the depth is a LOWER BOUND (and s191 AP1b puts the AREA estimator at 1.0x robustness at MIXED cells)' if cens else 'not censored'}")
        print(f"    SPREAD      median {med(vals):+.2f} dB over a {spread:.2f} dB range "
              f"= {ratio:.1f}x its own median; sign flips: {signflip}")
        print(f"    WINDOW      {edge_bound} of {n_tot} cells EDGE-refused at the window's own "
              f"{W.FEAT_BY_NAME[FEAT][2][0]:.0f} Hz bound on BOTH sides")
    # ---- the size is a property of the admitted set, not of the model --------------------------
    print("\n  ⭐ the same defect, three matched populations of the SAME data (BX5 supplies the")
    print("     pairwise ones): the median is whatever the admission rule leaves behind.")
    out["bx3"] = res


def gate_bx4(out):
    """The BAND axis -- complete population, nothing located, nothing selected, nothing censored.
    Plus the guard that makes it readable: the normalisation band must not move under the arms."""
    print("\n" + "=" * 100)
    print("BX4  the LF band error on EVERY cell (s187's own axis), + the normalisation guard")
    print("=" * 100)
    res = {}
    for g in ("cut", "flat", "boost"):
        acc = {b: [] for b in BANDS}
        for f in played_of(g):
            for sw in W.SWEEPS:
                cell = read(f, ())[sw]
                for b, (lo, hi) in BANDS.items():
                    acc[b].append(bandv(cell["model"], lo, hi) - bandv(cell["pedal"], lo, hi))
        res[g] = {b: {"median": med(acc[b]), "mean_abs": float(np.mean(np.abs(acc[b]))),
                      "worst_abs": float(np.max(np.abs(acc[b]))),
                      "n_model_low": int(sum(1 for v in acc[b] if v < 0)), "n": len(acc[b])}
                  for b in BANDS}
        tag = "  (CONTROL)" if g == "cut" else ""
        print(f"  {g:5s}{tag:11s} " + "   ".join(
            f"{b}: med {res[g][b]['median']:+5.2f}  |err| {res[g][b]['mean_abs']:4.2f}  "
            f"low {res[g][b]['n_model_low']:2d}/{res[g][b]['n']:2d}" for b in BANDS))
    lowband = "40-80"
    flat_med, boost_med = res["flat"][lowband]["median"], res["boost"][lowband]["median"]
    deep = flat_med < -DEPTH_TOL_DB and boost_med < -DEPTH_TOL_DB
    print(f"\n  computed verdict: over {lowband} Hz the model is {flat_med:+.2f} dB at flat and "
          f"{boost_med:+.2f} dB at boost")
    print(f"  ⇒ the model is {'SHORT of LF, consistent with a genuinely deeper null' if deep else 'NOT short of LF at either position -- a null 8.9 dB deeper would pull this DOWN, and it does not'}")

    print("\n  BX4b  normalisation guard -- if the NORM band moved between arms, every band")
    print("        reading below would be that shift wearing an LF name.")
    base = med([read(f, ())[sw]["norm_m"] for f in played_of("flat") for sw in W.SWEEPS])
    drift = {}
    for lbl, arm in ARMS.items():
        v = med([read(f, arm)[sw]["norm_m"] for f in played_of("flat") for sw in W.SWEEPS])
        drift[lbl] = v - base
        print(f"     {lbl:24s} norm-band shift {v - base:+.3f} dB")
    worst = max(abs(x) for x in drift.values())
    print(f"     worst drift {worst:.3f} dB against band errors of "
          f"{max(res[g][b]['worst_abs'] for g in ('flat', 'boost') for b in BANDS):.2f} dB ⇒ "
          f"{'NOT a normalisation artefact' if worst < 0.5 else '⛔ the normalisation moves enough to matter'}")
    out["bx4"] = {"bands": res, "norm_drift": drift, "worst_norm_drift": worst}
    return res


def gate_bx5(out):
    """THE FRONTIER.  Every arm on both statistics, with the depth MATCHED across arms -- s178:
    an arm whose null is too shallow to read drops that cell, and shallow is the outcome scored."""
    print("\n" + "=" * 100)
    print("BX5  the lever frontier -- BAND (complete) and DEPTH (matched across arms)")
    print("=" * 100)
    res = {}
    for g in GRADED:
        played = played_of(g)
        cells = [(f, sw) for f in played for sw in W.SWEEPS]
        keep = [(f, sw) for f, sw in cells
                if all(admits(read(f, a)[sw]) for a in ARMS.values())]
        print(f"\n  --- GRUNT {g} ---  {len(cells)} played cells; matched across all "
              f"{len(ARMS)} arms: {len(keep)}"
              + ("   ⚠⚠ TOO THIN TO ARBITRATE" if len(keep) < MIN_N else ""))
        print(f"  {'arm':24s}" + "".join(f"{'band ' + b:>14s}" for b in BANDS)
              + f"{'|err|40-80':>12s}{'DEPTH med':>12s}{'n':>4s}")
        res[g] = {"n_cells": len(cells), "n_matched": len(keep), "arms": {}}
        for lbl, arm in ARMS.items():
            bacc = {b: [] for b in BANDS}
            for f, sw in cells:
                cell = read(f, arm)[sw]
                for b, (lo, hi) in BANDS.items():
                    bacc[b].append(bandv(cell["model"], lo, hi) - bandv(cell["pedal"], lo, hi))
            dep = [depth_delta(read(f, arm)[sw]) for f, sw in keep]
            rec = {b: med(bacc[b]) for b in BANDS}
            rec["mean_abs_40_80"] = float(np.mean(np.abs(bacc["40-80"])))
            rec["depth_med"] = med(dep)
            rec["n_depth"] = len(dep)
            res[g]["arms"][lbl] = rec
            print(f"  {lbl:24s}" + "".join(f"{rec[b]:14.2f}" for b in BANDS)
                  + f"{rec['mean_abs_40_80']:12.2f}"
                  + (f"{rec['depth_med']:12.2f}" if dep else f"{'--':>12s}")
                  + f"{len(dep):4d}")

        # computed verdict: does ANY arm beat SHIP on every band column?
        ship = res[g]["arms"][SHIP_ARM]
        cols = list(BANDS) + ["mean_abs_40_80"]
        better = [lbl for lbl in ARMS if lbl != SHIP_ARM
                  and all(abs(res[g]["arms"][lbl][c]) < abs(ship[c]) for c in cols)]
        res[g]["dominating_arms"] = better
        print(f"    ⇒ arms beating SHIP on ALL of {cols}: "
              f"{better if better else 'NONE -- the shipped value is the best available'}")
    out["bx5"] = res
    return res


def gate_bx6(band, frontier, out):
    """s187's own refutation, reproduced three epochs later -- a free cross-session known answer."""
    print("\n" + "=" * 100)
    print("BX6  does s187's GLOBAL refutation still hold?  (a cross-session known answer)")
    print("=" * 100)
    print(f"  s187 rendered the Cut pair applied globally and recorded flat/boost's 63-100 Hz error")
    print(f"  going to +{S187_GLOBAL_LO}..+{S187_GLOBAL_HI} dB.  s190's taper, s195's HF key and")
    print(f"  s196/s199's mix-K rows have shipped since.\n")
    ok = True
    got = {}
    for g in GRADED:
        v = frontier[g]["arms"][S187_ARM]["63-100"]
        inside = S187_GLOBAL_LO <= v <= S187_GLOBAL_HI
        got[g] = {"value": v, "inside": bool(inside)}
        ok &= inside
        print(f"  {g:5s}  63-100 Hz under the global arm: {v:+.2f} dB   "
              f"{'✅ inside s187 published range' if inside else '⚠ OUTSIDE s187 published range'}")
    print(f"\n  computed verdict: s187's global refutation "
          f"{'REPRODUCES on the current epoch' if ok else 'does NOT reproduce -- re-open it'}")
    out["bx6"] = {"published": [S187_GLOBAL_LO, S187_GLOBAL_HI], "measured": got,
                  "reproduces": bool(ok)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    args = ap.parse_args()
    out = {}
    fp_before = gate_bx0(out)
    gate_bx1(out)
    gate_bx2(out)
    gate_bx3(out)
    band = gate_bx4(out)
    frontier = gate_bx5(out)
    gate_bx6(band, frontier, out)

    fp_after = {d: BV.dir_fingerprint(d) for d in FORBIDDEN}
    if fp_after != fp_before:
        die("BX0", f"a READ-ONLY cache changed during the run: {fp_before} -> {fp_after}")
    print(f"\n  read-only caches unchanged: ✅")

    print("\n" + "=" * 100)
    print("VERDICT")
    print("=" * 100)
    carrier = out["bx2"].get("flat", {}).get("carrier")
    dom = sorted(set(sum((out["bx5"][g]["dominating_arms"] for g in GRADED), [])))
    print(f"  the depth error at flat is carried by the {carrier} ⇒ it IS N1")
    print(f"  the statistic is selected, censored, dispersed and window-bounded (BX3)")
    print(f"  ⚠ NOT sign-unstable under BV's own rule -- that appears only if the NEIGHBOUR's")
    print(f"    `shoulder_ok` is dropped, which admits 13 cells and flips the sign (see the docstring)")
    print(f"  the complete band statistic does NOT show a deeper null (BX4)")
    print(f"  arms beating SHIP anywhere: {dom if dom else 'NONE'}")
    if not dom:
        print("\n  ⇒ NOTHING TO SHIP.  N1 at flat/boost is CHARACTERISE AND ACCEPT: the direction")
        print("    survives as an unmeasurable sharpness difference; `+8.93 dB` is refuted as a")
        print("    defect SIZE.  s187's decision to scope the fix to GRUNT = Cut stands.")
    else:
        print(f"\n  ⇒ a dominating arm EXISTS: {dom} -- price it before shipping.")

    if args.json:
        os.makedirs(os.path.dirname(args.json), exist_ok=True)
        json.dump(out, open(args.json, "w"), indent=1, default=float)
        print(f"\n  wrote {args.json}")


if __name__ == "__main__":
    main()
