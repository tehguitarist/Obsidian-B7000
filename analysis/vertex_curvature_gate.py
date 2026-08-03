#!/usr/bin/env python3.11
"""GATE AH — THE TREBLE PEAK'S VERTEX CURVATURE, MEASURED ON BOTH SIDES.

WHY THIS EXISTS (session 137, executing session 135's `NEXT` #2 verbatim):

    "Measure the pedal's own vertex CURVATURE on GATE W's 1/48-oct locator, converting AG6's
     implied -17.66 dB/oct^2 into a measurement.  It decides how much of the available tilt a
     candidate may spend, and it is the one number between AG6's constraint and a usable gate."

THE CHAIN THIS SITS IN, AND WHERE THE HOLE IS.
  AB4/AF6 established that the treble peak is a **VERTEX** — the bridged-T's rise meeting three
  rolloffs — so it moves under a drive-dependent SLOPE change with no corner moving anywhere:

      dx (octaves) = -T / C          T = tilt (dB/oct),  C = curvature (dB/oct^2)

  AF6 SIZED the requirement with that law (-1.185 dB/oct at 2935 Hz).  AG5 then measured that the
  reference CARRIES a drive-tilt of -1.944 dB/oct there, 1.72x the requirement.  AG6 put the two
  together and found the law OVER-PREDICTS: the pedal's own tilt through the MODEL's curvature
  predicts a -11.4 % peak walk against GATE W6's measured -7.3 %, so

      "the pedal's peak is ~1.6x SHARPER than ours -- C_pedal ~ -17.66 dB/oct^2"

  ⚠ and AG6 flagged that number as an IMPLICATION, not a measurement: it is a division of two
  ratios, and **the pedal's vertex has never been fitted at all**.  Everything downstream of it —
  in particular item 6's gate 2, *"a candidate must be gated on position AND shape"* — rests on a
  quantity nobody has measured.  This gate measures it.

⛔ AND IT CHECKS THE OTHER OPERAND TOO, WHICH AG6 COULD NOT.  AG6's C_model is **AF1c's
CLOSED-FORM cascade curvature** (-11.124 dB/oct^2, GATE AB's bridged-T x SK x SK x clipper-loop),
while its measured walk is a property of the **RENDERED** model.  Those are two different objects:
the closed form is the post-clipper linear cascade alone, the render is the whole chain including
the pre-clipper path and the mix.  If they disagree at this feature then AG6's 1.55x is partly an
object mismatch rather than a device difference — so AH4 measures the model's curvature on the SAME
estimator as the pedal's, and AH5 reports what that does to AG6.

WHAT THIS GATE DOES **NOT** CLAIM.
  * It does not identify any mechanism.  It measures a shape parameter of two curves.
  * A vertex on a non-parabolic background has a **window-dependent** curvature.  That is a
    property of the quantity, not a defect, so AH2 sweeps the fit half-width and prints the
    dependence rather than quoting one number as if it had none.
  * It does not re-measure the drive-TILT as its headline — AG5 owns that.  AH6 re-reads it on
    THIS instrument only as a cross-instrument corroboration, and says so.
  * No constant, no `src/` edit.  Renders are GATE W's own, at GATE W's own settings.

  AH1  KNOWN ANSWERS  (a) injected-parabola recovery: adding 0.5*C*log2(f/f0)^2 to ANY curve must
                      raise the fitted curvature by exactly C -- exact algebra, so the bar is
                      1e-9 and not a guess, with C = 0 as the arm's own built-in control (s133);
                      (b) the estimator on GATE AB's CLOSED-FORM cascade must reproduce AF1c's
                      stored curvature, READ from the s135 report rather than transcribed -- this
                      is what makes AH4's model column comparable to the number AG6 used.
  AH2  WINDOW SWEEP   curvature vs fit half-width, both sides.  Printed, not hidden.
  AH3  MEMBERSHIP     GATE Q's pure-OD endpoints, `gain-n12` excluded, edge/prominence guards
                      imported from GATE W.  A partial ladder is SPLIT BY ITS REASON (GATE AG2's
                      test, and s133's correction to s129's rule): a cell lost to PROMINENCE has
                      an independently-measured physical reason and is excluded + named; a cell
                      lost to the window EDGE is a validity failure and REFUSES.
  AH3b WINDOW CONTAINMENT, asserted after locating and BEFORE any curvature is read (AG1c's rule).
                      ⚠ It CANNOT be asserted from GATE W's windows alone, and the first draft of
                      this gate tried to and duly refused itself: `treble_peak` ends at 4200 Hz and
                      `treble_notch` STARTS at 4200 Hz, so a window-bounds test fails for any fit
                      half-width whatsoever.  The bound that means something is over the vertices
                      actually LOCATED -- which is still before any curvature is read, because
                      locating a vertex is not measuring one.
  AH4  THE MEASUREMENT   C_model and C_pedal per stimulus rung, and the ratio.
  AH5  AG6 RE-CLOSED  with C measured on both sides: does the vertex law reproduce each side's OWN
                      measured peak walk from its OWN measured tilt?  That is a known answer about
                      the PHYSICS (if the peak is a vertex of this construction, it must), and it
                      is the first time it can be asked of the pedal at all.
  AH6  CROSS-INSTRUMENT  AG3/AG5's drive-tilt, re-read on this 1/48-oct transfer instead of GATE
                      Q's 1/3-octave band surface.  AG6 mixed the two instruments; this says
                      whether that was safe.
  AH7  THE BUDGET     how much tilt a candidate may spend before it OVERSHOOTS the position
                      target -- item 6's gate 2, stated as a number for the first time.
  AH8  VERDICT        computed, as a comparison against the stored implication.

Usage:
  python3.11 analysis/vertex_curvature_gate.py
  python3.11 analysis/vertex_curvature_gate.py --json analysis/reports/s137_vertex_curvature.json
"""
import argparse
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import analyze as A                # noqa: E402
import bt_pair_shape_gate as AB    # noqa: E402  the closed-form cascade, imported not re-derived
import captures as C               # noqa: E402
import feature_locus_gate as W     # noqa: E402  the locator, the grid, the windows, the renders
import matrix_grade as MG          # noqa: E402
import null_locus_gate as R        # noqa: E402  EXPECT_ENDPOINTS -- ONE definition
import od_absolute_gate as Q       # noqa: E402
from parallel import pmap          # noqa: E402

REPORT = "analysis/reports/s124_ship.json"
AG_REPORT = "analysis/reports/s135_drive_tilt.json"
W_REPORT = "analysis/reports/s122_feature_locus.json"
OUT_JSON = "analysis/reports/s137_vertex_curvature.json"
REN_DIR = W.REN_DIR                 # GATE W's own renders, at GATE W's own settings

FEATURE = "treble_peak"

# Fit half-widths in OCTAVES.  The primary is 1/12, which is AF1c's own window (+-40 cells on a
# 480-points-per-octave grid) -- chosen so AH1b compares like with like rather than so it flatters.
# At GATE W's 1/48-oct grid that is +-4 cells, i.e. 9 points for a 3-parameter fit.
HALFWIDTHS = (1.0 / 24, 1.0 / 16, 1.0 / 12, 1.0 / 8, 1.0 / 6)
PRIMARY_HALF = 1.0 / 12
MIN_PTS = 5                         # a quadratic needs 3; fewer than 5 is not a fit

KA_INJECT_TOL = 1e-9                # AH1a is exact algebra
KA_CLOSED_TOL = 0.05                # AH1b: two grids, two centring conventions, one analytic curve

# The fit's own vertex must land in the MIDDLE HALF of its own fit window, i.e. within half the
# half-width.  ⚠ DERIVED FROM THE ESTIMATOR'S GEOMETRY, NOT CHOSEN -- and the first draft used a
# flat 0.02 oct at every half-width, which is a tolerance a correct implementation cannot meet
# (s123): on a non-parabolic background a WIDER fit's vertex legitimately drifts further, so a
# constant bar fails correct code at the wide end while passing it at the narrow end.  Scaling the
# bar with the window turns the sweep into a statement about which half-widths are USABLE.
VERTEX_OFFSET_FRAC = 0.5


def _die(msg):
    """Refuse.  Exit 2, so a runner tells a fired guard from an uncaught crash (s133)."""
    print("\n" + "=" * 96)
    print(f"GATE AH: REFUSED — {msg}")
    print("=" * 96)
    sys.exit(2)


# ---------------------------------------------------------------------------
# THE ESTIMATOR
# ---------------------------------------------------------------------------
def curvature(grid, db, f0, half_oct):
    """Quadratic fit in u = log2(f/f0) over |u| <= half_oct.

    -> dict(curv_db_oct2, slope_db_oct, vertex_off_oct, n)  or None if under-sampled.

    `curv` is 2*a for d ~ d0 + b*u + a*u^2, i.e. d''(u) -- the SAME convention AF1c uses
    (`2.0 * np.polyfit(...)[0]`), so AH1b can compare against its stored value directly.

    `vertex_off_oct` = -b/(2a) is where the FIT thinks the vertex is, in octaves from f0.  It is
    not used in any verdict; it is a free self-check that the fit is describing the feature the
    locator found and not a shoulder (`a-positional-index-is-a-shape-claim`).
    """
    u = np.log2(np.asarray(grid, dtype=float) / f0)
    m = np.abs(u) <= half_oct + 1e-12
    n = int(m.sum())
    if n < MIN_PTS:
        return None
    a, b, _ = np.polyfit(u[m], np.asarray(db)[m], 2)
    if a == 0.0:
        return None
    return {"curv_db_oct2": float(2.0 * a), "slope_db_oct": float(b),
            "vertex_off_oct": float(-b / (2.0 * a)), "n": n}


def tilt_at(grid, db, f0, half_oct):
    """The LINEAR coefficient of the same quadratic -- the slope AT f0 (AG's own estimator).

    AG fits a quadratic in log2(f/F0) over GATE Q's 1/3-octave bands and takes b; this does the
    identical thing on the 1/48-oct transfer, which is what makes AH6 a cross-INSTRUMENT check
    rather than a re-run of AG.
    """
    r = curvature(grid, db, f0, half_oct)
    return None if r is None else r["slope_db_oct"]


# ---------------------------------------------------------------------------
# One capture: render (GATE W's stamp), align, smooth both sides onto GATE W's grid.
# ---------------------------------------------------------------------------
def _cell(fname):
    orig, ref = W._load_orig()
    parsed = C.parse_capture(fname)
    tag = fname.replace(".wav", "")
    out = os.path.join(REN_DIR, tag + "_plugin.wav")
    W.render(out, C.render_args(parsed))
    cap_al, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, fname)), orig)
    ren_al, _ = A.align(A.load(out), orig)
    rec = {"file": fname, "model": {}, "pedal": {}}
    for side, al in (("model", ren_al), ("pedal", cap_al)):
        for sw in W.SWEEPS:
            f, m = A.transfer_h1(A.seg_of(al, sw), ref)
            d = W.smooth(f, m)
            loc = W.locate(d, W.FEAT_BY_NAME[FEATURE][2], W.FEAT_BY_NAME[FEATURE][1])
            rec[side][sw] = {"db": [float(x) for x in d], "loc": loc}
    return rec


# ===========================================================================
def gate_ah1(out, ag, closed_db):
    """KNOWN ANSWERS, all three, before any measurement is read."""
    print("\n" + "-" * 96)
    print("AH1  KNOWN ANSWERS")
    print("-" * 96)
    fail = []

    # (a) injected parabola -- exact algebra, so the bar is not a guess.
    base_f0, _ = 2934.0, None
    rows = []
    worst = 0.0
    for inj in (0.0, -3.0, -11.124, +7.5):
        d = closed_db + 0.5 * inj * np.log2(W.GRID / base_f0) ** 2
        c0 = curvature(W.GRID, closed_db, base_f0, PRIMARY_HALF)["curv_db_oct2"]
        c1 = curvature(W.GRID, d, base_f0, PRIMARY_HALF)["curv_db_oct2"]
        err = abs((c1 - c0) - inj)
        worst = max(worst, err)
        rows.append([inj, c1 - c0, err])
        print(f"  (a) inject {inj:+8.3f} dB/oct^2  ->  recovered {c1 - c0:+9.6f}   "
              f"|err| = {err:.2e}")
    ok_a = worst < KA_INJECT_TOL
    print(f"      worst |err| = {worst:.2e} against an EXACT requirement  "
          f"{'PASS' if ok_a else 'FAIL'}")
    print("      (the inject-ZERO row is this arm's own mutation control: it must recover 0.)")
    if not ok_a:
        fail.append("AH1a")

    # (b) the closed-form cascade must reproduce AF1c's stored curvature.
    af1c = ag.get("af1c_curv")
    vertex_hz = ag.get("vertex_hz")
    if af1c is None or vertex_hz is None:
        _die(f"AH1b — {os.path.basename(AG_REPORT)} carries no af1c_curv/vertex_hz; this gate "
             f"will not transcribe AF1c's number from a handover.")
    loc_c = W.locate(closed_db, W.FEAT_BY_NAME[FEATURE][2], "max")
    r = curvature(W.GRID, closed_db, loc_c["f0"], PRIMARY_HALF)
    if r is None:
        _die("AH1b — the closed-form cascade is under-sampled at the primary half-width.")
    rel = abs(r["curv_db_oct2"] / af1c - 1.0)
    ok_b = rel < KA_CLOSED_TOL
    print(f"\n  (b) closed-form cascade, this estimator : {r['curv_db_oct2']:+8.3f} dB/oct^2 "
          f"({r['n']} pts)")
    print(f"      AF1c's stored value (s135 report)    : {af1c:+8.3f} dB/oct^2")
    print(f"      peak {loc_c['f0']:.1f} Hz vs AF1c's vertex {vertex_hz:.1f} Hz;  "
          f"relative |d| = {100*rel:.2f} %   {'PASS' if ok_b else 'FAIL'}")
    print("      ⇒ without this, AH4's MODEL column is not comparable to the C_model AG6 used.")
    if not ok_b:
        fail.append("AH1b")

    out["ah1"] = {"inject": rows, "inject_worst": worst,
                  "closed_curv": r["curv_db_oct2"], "af1c_curv": af1c, "closed_rel": rel}
    if fail:
        _die(f"{', '.join(fail)} — a known answer did not reproduce; nothing below is quotable.")


def gate_ah3b(rows, files, out):
    """WINDOW CONTAINMENT — asserted over the LOCATED vertices, before any curvature is read.

    ⚠ This is deliberately NOT a test on GATE W's window bounds.  `treble_peak` ends at 4200 Hz
    and `treble_notch` begins at 4200 Hz, so a bounds-based containment test fails for every fit
    half-width including zero -- the first draft of this gate wrote one and refused itself with a
    -514 Hz margin.  A window-bounds test that cannot pass is not a strict guard, it is a broken
    one (`a-tolerance-a-correct-implementation-cannot-meet`, s123).  What is meaningful is whether
    the fit windows around the vertices this gate ACTUALLY located reach a neighbouring feature.
    """
    print("\n" + "-" * 96)
    print("AH3b WINDOW CONTAINMENT — over the located vertices, before any curvature is read")
    print("-" * 96)
    bt_hi = W.FEAT_BY_NAME["bt_notch"][2][1]
    tn_lo = W.FEAT_BY_NAME["treble_notch"][2][0]
    wide = max(HALFWIDTHS)
    by_file = {r["file"]: r for r in rows}
    f0s = [by_file[f][side][sw]["loc"]["f0"]
           for f in files for side in ("model", "pedal") for sw in W.SWEEPS]
    lo_edge = min(f0s) * 2.0 ** -wide
    hi_edge = max(f0s) * 2.0 ** +wide
    print(f"  located vertices span {min(f0s):.1f} - {max(f0s):.1f} Hz over "
          f"{len(f0s)} (capture, side, rung) cells")
    print(f"  at the WIDEST half-width (+-{wide:.4f} oct) the fit windows span "
          f"{lo_edge:.1f} - {hi_edge:.1f} Hz")
    print(f"      lowest  reached {lo_edge:8.1f} Hz  >  bt_notch window top    {bt_hi:8.1f} Hz"
          f"   margin {lo_edge - bt_hi:+8.1f} Hz")
    print(f"      highest reached {hi_edge:8.1f} Hz  <  treble_notch window lo {tn_lo:8.1f} Hz"
          f"   margin {tn_lo - hi_edge:+8.1f} Hz")
    ok = lo_edge > bt_hi and hi_edge < tn_lo
    print(f"      {'PASS' if ok else 'FAIL'}   (both neighbour bounds imported from GATE W's "
          f"FEATURES table, not chosen here)")
    out["ah3b"] = {"f0_lo": min(f0s), "f0_hi": max(f0s), "win_lo": lo_edge, "win_hi": hi_edge,
                   "bt_hi": bt_hi, "tn_lo": tn_lo, "widest_half_oct": wide}
    if not ok:
        _die("AH3b — a fit window reaches a neighbouring migrating feature; the curvature would "
             "be a property of two features, not one.")


def gate_ah3(rows, out):
    """MEMBERSHIP, asserted — and a partial ladder SPLIT BY ITS REASON.

    ⚠⚠ s129's three-outcome rule says a row that LOSES a rung is a malformed read and must
    REFUSE rather than be excluded.  The first draft of this gate applied that unconditionally and
    refused on 7 of 16 pedal captures -- which is s133's own correction to the rule: **ask whether
    the partiality your guard imagines is structurally possible, and on which axis.**  Here a cell
    can drop out for two completely different reasons and only one of them is a validity failure:

      PROMINENCE below GATE W's own bar  -> the feature is not RESOLVED at that operating point.
                                            That is a PHYSICS outcome (GATE AD measured the
                                            pedal's feature DEPTHS moving with drive), it has an
                                            independently-recorded reason, and it is excluded and
                                            named -- exactly GATE AG2's test, which refuses only a
                                            partial row whose missing cells are UNFLAGGED.
      EDGE of the named window           -> the window did not CONTAIN a feature that is there.
                                            That is a validity failure and it refuses.

    Collapsing the two would either refuse on ordinary physics (draft 1) or silently swallow a
    window that no longer contains a migrating feature (the failure s122's W1b paid for).
    """
    print("\n" + "-" * 96)
    print("AH3  MEMBERSHIP — asserted, and partial ladders split by REASON")
    print("-" * 96)
    print(f"  bar: GATE W's own MIN_PROM_DB = {W.MIN_PROM_DB} dB, imported not chosen\n")
    good, faint, edged, absent, proms = {}, [], [], {}, []
    for side in ("model", "pedal"):
        g, a = [], []
        for r in rows:
            ok = []
            for sw in W.SWEEPS:
                loc = r[side][sw]["loc"]
                proms.append(loc["prom"])
                if loc["edge"]:
                    edged.append((side, r["file"], sw, loc["f0"], loc["prom"]))
                elif loc["prom"] < W.MIN_PROM_DB:
                    faint.append((side, r["file"], sw, loc["f0"], loc["prom"]))
                else:
                    ok.append(sw)
            (g if len(ok) == len(W.SWEEPS) else a).append((r["file"], ok))
        good[side], absent[side] = g, a
        print(f"  {side:<6s} complete {len(g):3d}   incomplete {len(a):3d}   (of {len(rows)})")

    if faint:
        print(f"\n  NOT RESOLVED (prominence < {W.MIN_PROM_DB} dB) — a physics outcome, excluded "
              f"and named:")
        for side, f, sw, f0, p in faint:
            print(f"      {side:<6s} {f[:52]:52s} {sw.replace('sweep_',''):>8s}  "
                  f"prom {p:5.2f} dB at {f0:7.1f} Hz")
        # COMPUTED, not narrated: which side loses cells and at which rungs is exactly the kind
        # of sentence that outlives its data (`computed-verdicts-not-narrated`).  The first draft
        # asserted "every unresolved cell is on the PEDAL side" in prose.
        sides = sorted({s for s, _, _, _, _ in faint})
        rungs = sorted({sw for _, _, sw, _, _ in faint}, key=lambda s: W.SWEEPS.index(s))
        hot = [sw for sw in rungs
               if sum(1 for _, _, x, _, _ in faint if x == sw) >= 0.5 * len(faint) / len(rungs)]
        print(f"      ⇒ unresolved cells appear on {sides} at rung(s) "
              f"{[r.replace('sweep_', '') for r in rungs]}, concentrated at "
              f"{[r.replace('sweep_', '') for r in hot]}.")
        if sides == ["pedal"]:
            print(f"        ONE-SIDED, on the pedal: its treble peak FLATTENS as it is driven — "
                  f"item 6's DEPTH\n        axis (GATE AD5) showing up in a membership guard, "
                  f"not a defect here.")
        else:
            print(f"        ⚠ NOT one-sided — the MODEL loses cells too, so this is not a "
                  f"statement about the\n        pedal's feature depth and must not be read as "
                  f"one.")
    if edged:
        for side, f, sw, f0, p in edged:
            print(f"      EDGE {side} {f} {sw}: f0 {f0:.1f} Hz")
        _die(f"AH3 — {len(edged)} cell(s) locate the peak ON its window bound.  A bound is not a "
             f"measurement, and a window that no longer contains a migrating feature is a "
             f"validity failure, not an exclusion.")

    # The bar is swept and the surviving count asserted to MOVE (s106 N5: a robustness sweep
    # whose knob never turns is a constant printed N times), and the distribution is printed so
    # the bar can be checked for the gap it sits in.
    proms = np.array(proms)
    pct = {q: float(np.percentile(proms, q)) for q in (0, 5, 25, 50, 75, 100)}
    print(f"\n  prominence distribution over all {len(proms)} cells (dB): "
          + " ".join(f"p{q}={v:.2f}" for q, v in pct.items()))
    counts = [(b, int((proms >= b).sum())) for b in W.PROM_SWEEP]
    print("  bar sweep: " + "   ".join(f"{b:.1f} dB -> {n}" for b, n in counts))
    if len({n for _, n in counts}) == 1:
        _die("AH3 — the prominence bar never changes the surviving count; the knob is not turning "
             "and the sweep is a constant printed N times (s106 N5).")
    # ⚠⚠ SAY WHERE THE BAR SITS, BECAUSE IT DOES NOT SIT IN A GAP.  s109's rule is: measure the
    # distribution and place the bar in its gap, THEN assert the separation -- and if the
    # population is not bimodal, no threshold is defensible and the gate must say so rather than
    # trim a tail.  Here p5 = 0.88 and p25 = 1.27, so the 1.0 dB bar cuts through a dense region.
    # Its PROVENANCE is still the right one (GATE W's own constant, imported), but provenance is
    # not separation -- so the membership it produces is bar-SENSITIVE, and AH4b measures what
    # that does to the headline instead of leaving the reader to wonder.
    near = float(((proms > 0.75 * W.MIN_PROM_DB) & (proms < 1.25 * W.MIN_PROM_DB)).mean())
    print(f"  ⚠ {100*near:.0f} % of cells lie within +-25 % of the bar — this population is NOT")
    print(f"    bimodal, so the bar SELECTS rather than separates.  AH4b sweeps it.")

    common = sorted({f for f, _ in good["model"]} & {f for f, _ in good["pedal"]})
    dropped = sorted({r["file"] for r in rows} - set(common))
    print(f"\n  AH3-MEMBERSHIP n={len(common)} scored (both sides, all {len(W.SWEEPS)} rungs)")
    for f in common:
        print(f"      + {f}")
    for f in dropped:
        print(f"      - {f}  (excluded: not resolved on both sides at every rung)")
    if len(common) < 4:
        _die(f"AH3 — only {len(common)} captures resolve the peak on BOTH sides at all four "
             f"rungs; a curvature median over that is not a measurement.")
    out["ah3"] = {"n": len(common), "files": common, "dropped": dropped,
                  "faint": [[s, f, sw, f0, p] for s, f, sw, f0, p in faint],
                  "prom_sweep": counts}
    return common


def gate_ah2(rows, files, out):
    """WINDOW SWEEP — curvature vs fit half-width.  Printed because it is real."""
    print("\n" + "-" * 96)
    print("AH2  FIT-WINDOW DEPENDENCE — a vertex on a non-parabolic background has one")
    print("-" * 96)
    print("  A curvature is only defined against the interval it is fitted over.  This is swept")
    print("  and printed rather than reduced, so no later reader quotes one number as if the")
    print("  quantity had no window at all.\n")
    by_file = {r["file"]: r for r in rows}
    tab = {}
    print(f"  {'half (oct)':>11s} {'pts':>5s} {'C_model':>10s} {'C_pedal':>10s} "
          f"{'ratio':>8s} {'worst |off|':>12s} {'bar':>7s}   usable")
    for half in HALFWIDTHS:
        cell = {}
        offs, npts = [], []
        for side in ("model", "pedal"):
            vals = []
            for sw in W.SWEEPS:
                per = []
                for f in files:
                    rec = by_file[f][side][sw]
                    r = curvature(W.GRID, np.array(rec["db"]), rec["loc"]["f0"], half)
                    if r is not None:
                        per.append(r["curv_db_oct2"])
                        offs.append(abs(r["vertex_off_oct"]))
                        npts.append(r["n"])
                if per:
                    vals.append(float(np.median(per)))
            # Median of the PER-RUNG medians, so this row is the same statistic AH4 quotes and
            # the primary row must equal AH4 exactly (asserted there).
            cell[side] = float(np.median(vals)) if vals else float("nan")
            cell[side + "_rungs"] = len(vals)
        ratio = cell["pedal"] / cell["model"] if np.isfinite(cell["model"]) else float("nan")
        cell["ratio"] = ratio
        # The fit-point count is MEASURED, not predicted from the half-width: the log grid is not
        # aligned to any vertex, so the same half-width admits 8 or 9 cells depending on where the
        # feature sits.  Printing a computed guess here would misreport the fit by one point.
        cell["pts_min"], cell["pts_max"] = (min(npts), max(npts)) if npts else (0, 0)
        cell["worst_vertex_off"] = max(offs) if offs else float("nan")
        bar = VERTEX_OFFSET_FRAC * half
        cell["bar"] = bar
        # ⚠ isfinite FIRST and explicitly. `nan > bar` is False, so an under-sampled row would
        # otherwise sail through as "usable" and then poison every max()/span below it -- the
        # exact fail-OPEN shape of s106's N3, committed here in draft 1 by the +-1/24 row.
        cell["usable"] = bool(npts) and np.isfinite(cell["worst_vertex_off"]) \
            and cell["worst_vertex_off"] <= bar
        tab[f"{half:.6f}"] = cell
        mark = "  <- PRIMARY (AF1c's own window)" if abs(half - PRIMARY_HALF) < 1e-9 else ""
        if not npts:
            print(f"  {half:11.5f} {'0':>5s} {'-':>10s} {'-':>10s} {'-':>8s} {'-':>12s} "
                  f"{bar:7.4f}   UNDER-SAMPLED (< {MIN_PTS} pts on a {W.GRID_FRAC}/oct grid){mark}")
        else:
            pts = "{}-{}".format(cell["pts_min"], cell["pts_max"])
            note = "yes" if cell["usable"] else "NO — fit vertex leaves the middle half"
            print(f"  {half:11.5f} {pts:>5s} {cell['model']:10.3f} {cell['pedal']:10.3f} "
                  f"{ratio:8.3f} {cell['worst_vertex_off']:12.4f} {bar:7.4f}   {note}{mark}")

    prim = tab[f"{PRIMARY_HALF:.6f}"]
    print(f"\n  The bar is HALF THE FIT HALF-WIDTH: the quadratic's own vertex must sit in the")
    print(f"  middle half of the interval it was fitted over, or it is describing a shoulder.")
    print(f"  Derived from the estimator's geometry — a CONSTANT bar here fails correct code at")
    print(f"  the wide end (s123), and a nan one fails open at the narrow end (s106 N3).")
    if not prim["usable"]:
        _die(f"AH2 — the PRIMARY half-width ({PRIMARY_HALF:.5f} oct) is not usable "
             f"(worst offset {prim['worst_vertex_off']:.4f} vs bar {prim['bar']:.4f}); the number "
             f"AH4 quotes would not be describing the feature.")
    ok = {k: v for k, v in tab.items() if v["usable"]}
    span_m = max(v["model"] for v in ok.values()) / min(v["model"] for v in ok.values())
    span_p = max(v["pedal"] for v in ok.values()) / min(v["pedal"] for v in ok.values())
    rat = [v["ratio"] for v in ok.values()]
    print(f"\n  over the {len(ok)} USABLE half-widths: C_model spans {span_m:.3f}x, "
          f"C_pedal {span_p:.3f}x, ratio {min(rat):.3f}-{max(rat):.3f}x")
    print(f"  ⇒ the RATIO is the quotable quantity, and the pedal's curvature is the "
          f"window-sensitive half.")
    out["ah2"] = {"table": tab, "n_usable": len(ok), "span_model": span_m, "span_pedal": span_p,
                  "ratio_lo": min(rat), "ratio_hi": max(rat)}
    return tab


def gate_ah4(rows, files, tab, out):
    """THE MEASUREMENT — C per stimulus rung, both sides, at the primary half-width."""
    print("\n" + "-" * 96)
    print("AH4  THE MEASUREMENT — vertex curvature per stimulus rung")
    print("-" * 96)
    by_file = {r["file"]: r for r in rows}
    res = {}
    print(f"  {'side':<6s} " + " ".join(f"{s.replace('sweep_', ''):>11s}" for s in W.SWEEPS)
          + f"{'median':>11s}{'span':>9s}")
    for side in ("model", "pedal"):
        meds, cells = [], []
        for sw in W.SWEEPS:
            vals = []
            for f in files:
                rec = by_file[f][side][sw]
                r = curvature(W.GRID, np.array(rec["db"]), rec["loc"]["f0"], PRIMARY_HALF)
                if r is not None:
                    vals.append(r["curv_db_oct2"])
            meds.append(float(np.median(vals)))
            cells.append(f"{meds[-1]:11.3f}")
        span = max(meds) / min(meds)
        res[side] = {"per_rung": meds, "median": float(np.median(meds)), "span": span}
        print(f"  {side:<6s} " + " ".join(cells) + f"{np.median(meds):11.3f}{span:9.2f}x")

    cm, cp = res["model"]["median"], res["pedal"]["median"]
    ratio = cp / cm
    print(f"\n  ⭐ C_model = {cm:+.3f}   C_pedal = {cp:+.3f}   RATIO = {ratio:.3f}x")
    print(f"     (n = {len(files)} captures x 4 rungs per side, one estimator, one grid.)")

    # FREE KNOWN ANSWER: AH2's primary row and this table are the same statistic computed by two
    # separate code paths, so they must agree EXACTLY.  Cheap, and it is the only thing standing
    # between "the sweep describes the quoted number" and "the sweep is a decorative table".
    prim = tab[f"{PRIMARY_HALF:.6f}"]
    worst = max(abs(prim["model"] - cm), abs(prim["pedal"] - cp))
    print(f"  known answer: AH2's primary row reproduces this table to {worst:.2e} dB/oct^2 "
          f"{'PASS' if worst < 1e-9 else 'FAIL'}")
    if worst >= 1e-9:
        _die(f"AH4 — AH2's primary row ({prim['model']:.6f}/{prim['pedal']:.6f}) and AH4's "
             f"({cm:.6f}/{cp:.6f}) are the same statistic and disagree by {worst:.2e}.")
    res["ratio"] = ratio
    out["ah4"] = res
    return res


def gate_ah4b(rows, out):
    """MEMBERSHIP ROBUSTNESS — the headline against the prominence bar that SELECTS it.

    AH3 establishes that the prominence population is not bimodal at this feature, so the 1.0 dB
    bar chooses a membership rather than separating two groups.  The project's most-repeated trap
    is a headline that moved with membership (`aggregate-moved-check-membership-first`, eleven
    occurrences), so the bar is swept and the headline re-computed at each setting.  A ratio that
    holds across the sweep is a measurement; one that tracks the bar is a selection.
    """
    print("\n" + "-" * 96)
    print("AH4b MEMBERSHIP ROBUSTNESS — is the ratio a measurement, or the bar's choice?")
    print("-" * 96)
    print(f"  {'bar (dB)':>9s} {'n caps':>7s} {'C_model':>10s} {'C_pedal':>10s} {'ratio':>8s}")
    tabb = {}
    for bar in W.PROM_SWEEP:
        keep = {}
        for side in ("model", "pedal"):
            keep[side] = {r["file"] for r in rows
                          if all((not r[side][sw]["loc"]["edge"])
                                 and r[side][sw]["loc"]["prom"] >= bar for sw in W.SWEEPS)}
        common = sorted(keep["model"] & keep["pedal"])
        if len(common) < 4:
            print(f"  {bar:9.1f} {len(common):7d}   n < 4 — not scored")
            tabb[f"{bar:.1f}"] = {"n": len(common)}
            continue
        by_file = {r["file"]: r for r in rows}
        med = {}
        for side in ("model", "pedal"):
            per_rung = []
            for sw in W.SWEEPS:
                v = [curvature(W.GRID, np.array(by_file[f][side][sw]["db"]),
                               by_file[f][side][sw]["loc"]["f0"], PRIMARY_HALF)["curv_db_oct2"]
                     for f in common]
                per_rung.append(float(np.median(v)))
            med[side] = float(np.median(per_rung))
        rr = med["pedal"] / med["model"]
        tabb[f"{bar:.1f}"] = {"n": len(common), "model": med["model"], "pedal": med["pedal"],
                              "ratio": rr}
        mark = "  <- GATE W's bar, used above" if abs(bar - W.MIN_PROM_DB) < 1e-9 else ""
        print(f"  {bar:9.1f} {len(common):7d} {med['model']:10.3f} {med['pedal']:10.3f} "
              f"{rr:8.3f}{mark}")
    scored = [v for v in tabb.values() if "ratio" in v]
    lo, hi = min(v["ratio"] for v in scored), max(v["ratio"] for v in scored)
    ns = sorted(v["n"] for v in scored)
    print(f"\n  ratio over {len(scored)} bar settings spanning n = {ns[0]}-{ns[-1]} captures: "
          f"{lo:.3f}-{hi:.3f}x")
    stable = (hi / lo - 1.0) < 0.10 and all(v["ratio"] > 1.0 for v in scored)
    v = ("ROBUST — the pedal is sharper at every bar, and the ratio moves less than 10 % while "
         "the membership changes by a factor of two" if stable else
         "BAR-SENSITIVE — the headline tracks the membership; quote it with its bar and n")
    print(f"  AH4b-VERDICT: {v}")
    out["ah4b"] = {"table": tabb, "ratio_lo": lo, "ratio_hi": hi, "verdict": v}
    return v


def gate_ah5(ah4, ah2tab, ag, wrep, out):
    """AG6 RE-CLOSED — the vertex law, now with BOTH curvatures measured."""
    print("\n" + "-" * 96)
    print("AH5  AG6 RE-CLOSED — does each side's own tilt predict its own walk?")
    print("-" * 96)
    ag6 = ag.get("ag6", {})
    ag3 = ag.get("ag3", {})
    for k, src in (("pedal_tilt_change", ag6), ("implied_pedal_curv", ag6),
                   ("measured_pct", ag6), ("model", ag3)):
        if k not in src:
            _die(f"AH5 — {os.path.basename(AG_REPORT)} has no `{k}`; refusing to transcribe "
                 f"AG's operands from a handover.")
    T_pedal = ag6["pedal_tilt_change"]
    T_model = ag3["model"][-1] - ag3["model"][0]
    implied = ag6["implied_pedal_curv"]

    w6 = wrep.get("w6", {}).get(FEATURE, {})
    walk = {}
    for side in ("model", "pedal"):
        meds = w6.get(side, {}).get("medians")
        if not meds or len(meds) < 4:
            _die(f"AH5 — GATE W's stored W6 has no 4-rung {side} median list for {FEATURE}; the "
                 f"measured walk is what this sub-gate compares against and it will not be "
                 f"reconstructed here.")
        walk[side] = meds[-1] / meds[0] - 1.0

    print("  The law (AB4/AF6):  dx[oct] = -T / C ,  then d(f)/f = 2^dx - 1.")
    print("  Each side is now asked about ITSELF — its own measured tilt, its own measured")
    print("  curvature, against its own measured walk.  Nothing crosses between the two.\n")
    # ⚠⚠ THE MODEL ROW IS NOT ANSWERABLE, AND ITS RATIO MUST NOT BE PRINTED AS ONE.
    # Both of its operands sit below the locator's own resolution -- the grid is 1/48 oct, i.e.
    # GRID_STEP_FRAC per cell, and the model's walk is 0.19 % against a 1.45 % cell.  A ratio of
    # two unresolvable numbers is arithmetic, not a measurement
    # (`ratio-statistics-need-a-denominator-guard`, and s116's U7: check there IS an effect before
    # reading anything off it).  It is reported as UNRESOLVED with both operands printed, which is
    # the honest form -- deleting the row would hide that the law is only testable on one side.
    res_frac = W.GRID_STEP_FRAC
    print(f"  {'side':<6s} {'T (dB/oct)':>11s} {'C (dB/oct^2)':>13s} {'predicted':>11s} "
          f"{'measured':>10s} {'ratio':>10s}")
    rowsout = {}
    for side, T in (("model", T_model), ("pedal", T_pedal)):
        Cs = ah4[side]["median"]
        pred = 2.0 ** (-T / Cs) - 1.0
        meas = walk[side]
        resolved = abs(meas) > res_frac and abs(pred) > res_frac
        rat = (pred / meas) if (resolved and meas) else float("nan")
        rowsout[side] = {"T": T, "C": Cs, "pred_frac": pred, "meas_frac": meas,
                         "ratio": rat, "resolved": bool(resolved)}
        shown = f"{rat:9.2f}x" if resolved else "UNRESOLVED"
        print(f"  {side:<6s} {T:11.3f} {Cs:13.3f} {100*pred:10.2f}% {100*meas:9.2f}% "
              f"{shown:>10s}")
    print(f"\n  UNRESOLVED = at least one operand is under the locator's own cell "
          f"({100*res_frac:.2f} %).")
    print(f"  The model's row is exactly that case and it is a CONSEQUENCE, not a gap: W6 already")
    print(f"  reads the model's peak FIXED, so its walk is unmeasurable BECAUSE the mechanism is")
    print(f"  missing.  ⇒ the vertex law is testable on the PEDAL only, and that is the side that")
    print(f"  matters — but it means this sub-gate has no model-side control.")

    cp = ah4["pedal"]["median"]
    cm = ah4["model"]["median"]
    # The verdict is gated on the range over the USABLE half-widths, not on the primary point
    # alone: AH2 measures C_pedal moving with the fit window, so a verdict read off one window
    # would be a property of that window (`a-lever-measured-at-one-rung-is-a-claim-about-that-rung`,
    # applied to the estimator's own free parameter rather than to the stimulus).
    ok = [v for v in ah2tab.values() if v["usable"]]
    cp_lo, cp_hi = min(v["pedal"] for v in ok), max(v["pedal"] for v in ok)
    rel = sorted(abs(c / implied - 1.0) for c in (cp_lo, cp_hi))
    sharper_always = all(abs(v["pedal"]) > abs(v["model"]) for v in ok)
    print(f"\n  ⭐⭐ AG6's IMPLICATION vs THIS MEASUREMENT:")
    print(f"      implied (s135, a division of two ratios) : {implied:+.3f} dB/oct^2")
    print(f"      MEASURED here, primary half-width        : {cp:+.3f} dB/oct^2")
    print(f"      MEASURED, over the usable window range   : {cp_hi:+.3f} to {cp_lo:+.3f}")
    print(f"      distance from the implication            : {100*rel[0]:.1f} - {100*rel[1]:.1f} %")
    print(f"      pedal sharper than model at EVERY usable window: {sharper_always}")
    if sharper_always and rel[1] < 0.20:
        verdict = ("CONFIRMED — the pedal's vertex is sharper at every usable window and AG6's "
                   "implied value survives being measured")
    elif sharper_always:
        verdict = (f"DIRECTION CONFIRMED, SIZE REDUCED — the pedal's vertex IS sharper than ours "
                   f"at every usable window ({ah4['ratio']:.2f}x at the primary), but it is "
                   f"{100*rel[0]:.0f}-{100*rel[1]:.0f} % short of AG6's implied "
                   f"{implied:+.2f}; quote the measurement, not the implication")
    else:
        verdict = ("REFUTED — the pedal's vertex is NOT reliably sharper than ours, so AG6's "
                   "over-prediction is not a curvature difference and must be re-attributed")
    print(f"\n  AH5-VERDICT: {verdict}")

    # ⭐ CLOSE THE DECOMPOSITION FROM BOTH ENDS (s117).  AG6 got its implied curvature by ASSUMING
    # the vertex law is exact on the pedal and solving for C.  Measured, the law is NOT exact --
    # the pedal's own T and C over-predict its own walk by the `pedal` row's ratio.  So AG6's
    # single over-prediction factor should decompose into (a genuine curvature difference) x (the
    # law's own residual), and if it does not, one of the three measurements is wrong.
    over_ag6 = ag6.get("over_predict")
    if over_ag6 is not None:
        # AG6 used the CLOSED-FORM C_model; rescale to the rendered one this gate measures.
        af1c = ag.get("af1c_curv")
        scale = (af1c / cm) if (af1c and cm) else 1.0
        recon = (cp / cm) * rowsout["pedal"]["ratio"]
        pred = over_ag6 * scale
        agree = abs(recon / pred - 1.0)
        print(f"\n  ⭐ AND THE DECOMPOSITION CLOSES FROM BOTH ENDS:")
        print(f"      AG6's over-prediction   {over_ag6:.4f}x  (on the CLOSED-FORM C_model "
              f"{af1c:+.3f}); rescaled to this gate's rendered C_model {cm:+.3f} -> {pred:.4f}x")
        print(f"      = (curvature ratio {cp/cm:.4f}x) x (the vertex law's own residual on the "
              f"pedal {rowsout['pedal']['ratio']:.4f}x) = {recon:.4f}x")
        print(f"      agreement {100*agree:.1f} %   {'PASS' if agree < 0.05 else 'CHECK'}")
        print(f"      ⇒ AG6's 1.55x was TWO effects, not one: the pedal's vertex really is "
              f"{cp/cm:.2f}x sharper,")
        print(f"        and the vertex law itself over-predicts by a further "
              f"{rowsout['pedal']['ratio']:.2f}x — which AG4 already predicts, because the law is a")
        print(f"        LOCAL linearisation and the pedal's tilt is not uniform.")
        out.setdefault("ah5_decomp", {}).update(
            {"ag6_over": over_ag6, "rescaled": pred, "reconstructed": recon, "agree": agree,
             "curv_ratio": cp / cm, "law_residual": rowsout["pedal"]["ratio"]})

    out["ah5"] = {"rows": rowsout, "implied_pedal_curv": implied, "measured_pedal_curv": cp,
                  "measured_range": [cp_hi, cp_lo], "rel_lo": rel[0], "rel_hi": rel[1],
                  "sharper_always": bool(sharper_always), "verdict": verdict}
    return rowsout, verdict


def gate_ah6(rows, files, ag, out):
    """CROSS-INSTRUMENT — AG's drive-tilt, re-read on the 1/48-oct transfer."""
    print("\n" + "-" * 96)
    print("AH6  CROSS-INSTRUMENT CHECK — AG5's tilt on a DIFFERENT instrument")
    print("-" * 96)
    ag5 = ag.get("ag5", {})
    ag3 = ag.get("ag3", {})
    if "primary_diff" not in ag5 or "half_oct" not in ag3:
        _die("AH6 — the s135 report has no ag5.primary_diff / ag3.half_oct.")
    half = ag3["half_oct"]
    F0 = ag["vertex_hz"]
    print(f"  AG reads the slope at {F0:.1f} Hz over +-{half} oct of GATE Q's 1/3-OCTAVE band")
    print(f"  surface (3 bands).  Here the identical quadratic-derivative estimator runs on GATE")
    print(f"  W's 1/48-oct transfer ({int(2*half*W.GRID_FRAC)+1} points).  Same quantity, ~14x the")
    print(f"  sampling, a different H1 window.  AG6 mixed these two instruments; this says whether")
    print(f"  that was safe.\n")
    by_file = {r["file"]: r for r in rows}
    res = {}
    print(f"  {'side':<6s} " + " ".join(f"{s.replace('sweep_', ''):>11s}" for s in W.SWEEPS)
          + f"{'change':>10s}")
    for side in ("model", "pedal"):
        meds, cells = [], []
        for sw in W.SWEEPS:
            vals = [tilt_at(W.GRID, np.array(by_file[f][side][sw]["db"]), F0, half) for f in files]
            vals = [v for v in vals if v is not None]
            if not vals:
                _die(f"AH6 — no readable slope for {side} at {sw}.")
            meds.append(float(np.median(vals)))
            cells.append(f"{meds[-1]:11.3f}")
        res[side] = {"per_rung": meds, "change": meds[-1] - meds[0]}
        print(f"  {side:<6s} " + " ".join(cells) + f"{meds[-1]-meds[0]:10.3f}")

    diff = res["pedal"]["change"] - res["model"]["change"]
    ag_diff = ag5["primary_diff"]
    agree = abs(diff - ag_diff)
    same_sign = (diff < 0) == (ag_diff < 0)
    print(f"\n  P-M drive-tilt, THIS instrument : {diff:+.3f} dB/oct")
    print(f"  P-M drive-tilt, AG5 (1/3-oct)   : {ag_diff:+.3f} dB/oct")
    print(f"  |difference| = {agree:.3f} dB/oct,  same sign = {same_sign}")
    if same_sign and agree <= 0.5 * abs(ag_diff):
        v = ("CORROBORATED — two instruments, same sign and comparable size, so AG6's mixing of "
             "the 1/3-oct surface with the 1/48-oct locator is safe at this feature")
    elif same_sign:
        v = ("SAME SIGN, DIFFERENT SIZE — the direction is instrument-independent and the "
             "magnitude is not; quote the instrument with any tilt number from here on")
    else:
        v = ("NOT CORROBORATED — the two instruments disagree in SIGN, which makes every "
             "cross-instrument step in AG6 unsafe and must be resolved before anything is built")
    print(f"\n  AH6-VERDICT: {v}")
    res["diff"] = diff
    res["ag_diff"] = ag_diff
    res["verdict"] = v
    out["ah6"] = res
    return res


def gate_ah7(ah4, ah2tab, ah4b, ag, wrep, out):
    """THE BUDGET — how much tilt a candidate may spend.  Item 6's gate 2, as a number."""
    print("\n" + "-" * 96)
    print("AH7  THE SPEND BUDGET — item 6's 'position AND shape' gate, stated as a number")
    print("-" * 96)
    w6 = wrep["w6"][FEATURE]
    target = w6["pedal"]["medians"][-1] / w6["pedal"]["medians"][0] - 1.0
    Cm = ah4["model"]["median"]
    dx = math.log2(1.0 + target)
    T_max = -Cm * dx
    avail = ag["ag5"]["primary_diff"]
    over = avail / T_max
    print(f"  The model must acquire the pedal's own walk : {100*target:+.2f} %  "
          f"({dx:+.4f} oct)")
    print(f"  The model's MEASURED vertex curvature       : {Cm:+.3f} dB/oct^2")
    print(f"  ⇒ MAX drive-dependent tilt a candidate may deliver at {ag['vertex_hz']:.0f} Hz")
    print(f"    before it OVERSHOOTS the position target  : {T_max:+.3f} dB/oct")
    print(f"  The tilt the reference actually carries (AG5): {avail:+.3f} dB/oct")
    print(f"  ⇒ a candidate that reproduces the reference's FULL tilt overshoots by "
          f"{over:.2f}x")
    # ⭐ THE BUDGET USES C_MODEL ONLY, AND THAT IS THE STABLE HALF.  AH2 and AH4b both find
    # C_PEDAL moving with the estimator's fit window and with the membership bar; C_MODEL does
    # not move with either.  Saying so is what stops AH4b's "BAR-SENSITIVE" verdict being read as
    # a caveat on this number, which it is not -- the noisy quantity never enters it.
    ok = [v for v in ah2tab.values() if v["usable"]]
    cm_lo, cm_hi = min(v["model"] for v in ok), max(v["model"] for v in ok)
    bars = [v["model"] for v in ah4b["table"].values() if "model" in v]
    tb = sorted(-c * dx for c in (cm_lo, cm_hi))
    print(f"\n  ⭐ THE BUDGET DEPENDS ON C_MODEL ONLY — the stable half:")
    print(f"      C_model over the usable fit windows : {cm_hi:+.3f} to {cm_lo:+.3f} "
          f"({abs(cm_lo/cm_hi):.4f}x)")
    print(f"      C_model over the membership bars    : "
          + " / ".join(f"{c:+.3f}" for c in bars))
    print(f"      ⇒ budget {tb[0]:+.3f} to {tb[1]:+.3f} dB/oct.  AH4b's BAR-SENSITIVE verdict is")
    print(f"        about C_PEDAL and does NOT reach this number: the noisy quantity never")
    print(f"        enters the budget, only the pedal's WALK (a GATE W6 median) and C_model do.")
    print(f"\n  ⚠ THE BUDGET IS A POSITION CONSTRAINT ONLY.  AG4 already refuted the whole")
    print(f"    CONSTANT-tilt class on SHAPE (the deficit steepens -1.58 dB/oct per octave), so")
    print(f"    'deliver {T_max:+.3f} dB/oct uniformly' is NOT a specification — it is the ceiling")
    print(f"    the frequency-dependent candidate must respect AT THE VERTEX.")
    out["ah7"] = {"target_frac": target, "curv_model": Cm, "tilt_max_db_oct": T_max,
                  "tilt_max_range": tb, "curv_model_range": [cm_hi, cm_lo],
                  "curv_model_by_bar": bars, "tilt_available": avail, "overshoot": over}
    return T_max, over, tb


def main():
    ap = argparse.ArgumentParser(description="GATE AH — treble-peak vertex curvature, measured")
    ap.add_argument("--report", default=REPORT)
    ap.add_argument("--ag", default=AG_REPORT)
    ap.add_argument("--w", default=W_REPORT)
    ap.add_argument("--jobs", type=int, default=None)
    ap.add_argument("--json", default=OUT_JSON)
    a = ap.parse_args()

    for p in (a.report, a.ag, a.w):
        if not os.path.exists(p):
            _die(f"{p} not found — this gate reads its operands from stored reports and will not "
                 f"reconstruct them.")
    rep = json.load(open(a.report))
    ag = json.load(open(a.ag))
    wrep = json.load(open(a.w))

    print("=" * 96)
    print("GATE AH — the treble peak's VERTEX CURVATURE, measured on both sides")
    print("=" * 96)
    print(f"  captures from   : {a.report}")
    print(f"  AG operands from: {a.ag}   (AF6/AG5/AG6 read, never transcribed)")
    print(f"  W6 walk from    : {a.w}")
    print(f"  locator, grid, windows and renders: GATE W ({W.GRID_FRAC}/oct, "
          f"{len(W.GRID)} points)")
    print("  ⚠ PREMISE, printed every run: a curvature is defined against its FIT WINDOW.  AH2")
    print("    sweeps it.  The RATIO of the two sides is far more stable than either value.")

    out = {"report": a.report, "ag_report": a.ag, "w_report": a.w, "feature": FEATURE,
           "grid_frac": W.GRID_FRAC, "primary_half_oct": PRIMARY_HALF}

    closed_db = 20.0 * np.log10(np.abs(AB.cascade(W.GRID)) + 1e-300)
    gate_ah1(out, ag, closed_db)

    caps = {c["file"]: c for c in rep["captures"]}
    eps = [e for e in Q.endpoints_od(caps) if not MG.is_gain_n12(e)]
    n_all = len(Q.endpoints_od(caps))
    print(f"\n  GATE Q pure-OD endpoints: {n_all} (expected {R.EXPECT_ENDPOINTS}), "
          f"{len(eps)} after excluding `gain-n12`")
    if n_all != R.EXPECT_ENDPOINTS:
        _die(f"GATE Q's endpoint count moved ({n_all} vs {R.EXPECT_ENDPOINTS}) — bump it THERE "
             f"deliberately after checking what arrived.")

    print(f"  rendering / reading {len(eps)} captures x {len(W.SWEEPS)} sweeps ...")
    rows = pmap(_cell, eps, jobs=a.jobs)

    files = gate_ah3(rows, out)
    gate_ah3b(rows, files, out)
    tab = gate_ah2(rows, files, out)
    ah4 = gate_ah4(rows, files, tab, out)
    v4b = gate_ah4b(rows, out)
    _, v5 = gate_ah5(ah4, tab, ag, wrep, out)
    ah6 = gate_ah6(rows, files, ag, out)
    T_max, over, tb = gate_ah7(ah4, tab, out["ah4b"], ag, wrep, out)

    print("\n" + "-" * 96)
    print("AH8  VERDICT")
    print("-" * 96)
    print(f"  C_pedal / C_model = {ah4['ratio']:.3f}x   (measured, one estimator, one grid)")
    print(f"  AH4b {v4b}")
    print(f"  AH5  {v5}")
    print(f"  AH6  {ah6['verdict']}")
    print(f"\n  ⭐⭐ THE DELIVERABLE: item 6's gate 2 is now a NUMBER, not an implication —")
    print(f"     a candidate may deliver at most {T_max:+.3f} dB/oct ({tb[0]:+.3f} to {tb[1]:+.3f} over the")
    print(f"     usable fit windows) of drive-dependent tilt at the vertex before it overshoots")
    print(f"     the position target, against the "
          f"{ah6['ag_diff']:+.3f} dB/oct")
    print(f"     the reference carries ({over:.2f}x).  Position and shape cannot both be bought")
    print(f"     with a pure tilt, and now the ceiling is measured on both operands.")

    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
        with open(a.json, "w") as fh:
            json.dump(out, fh, indent=1, default=float)
        print(f"\n  -> {a.json}")
    print("\n" + "=" * 96)
    print("GATE AH: all guards passed.  AH2-AH7 are readable.")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
