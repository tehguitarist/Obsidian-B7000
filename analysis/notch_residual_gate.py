#!/usr/bin/env python3.11
"""GATE AR — what carries GATE AQ4's residual metric gap, and is AQ4's own statistic PAIRED?

WHY THIS EXISTS
---------------
GATE AQ (s153) freed the section's Q, found the point-vs-area metric gap went 2.69 -> 2.16 dB
(-20 %), printed **SURVIVED**, and concluded that AP6's "shape mismatch" is refuted as *the*
explanation.  Its `NEXT` #4 then named the successor: *"the residual is a SKIRT/centre defect, not a
Q defect; anyone re-opening it should free the CENTRE frequency"*.

⚠⚠ THAT SUCCESSOR IS A CLAIM, NOT A TASK (`a-backlog-item's-proposed-REPAIR-is-a-claim`, s142), and
so is the -20 % that motivates it.  This gate audits both before anything is freed, because the
cheap reads come first:

  (1) ⛔⛔ **AQ4's gap is a DIFFERENCE OF MEANS OVER AN AXIS ON WHICH THE QUANTITY CHANGES SIGN.**
      AQ3/AP3 average the solved gain over the three stimulus sweeps SEPARATELY per metric and only
      then difference the two columns.  If the per-sweep gap changes sign across sweeps — and it
      does — the mean cancels it, and it cancels the two arms by DIFFERENT amounts, so the ratio
      AQ4 reports is not a property of shape-matching at all.  The paired form (difference per
      sweep, then average) uses the same numbers and asks the same question with the axis intact.
      `a-pooled-statistic-cannot-answer-about-its-own-axis` (s105), `difference-statistics-hide-
      common-mode`.
      ⚠ A SECOND, smaller instance of the same thing rides along: AQ3 drops unreachable cells PER
      METRIC, so a cell's gap can pair a mean over sweeps {a,b} against a mean over {a} alone.
      Measured below — it is one cell of eight, and it is named rather than estimated.

  (2) The residual is decomposed rather than attributed.  On ANY curve, exactly,

          depth_point - depth_area  ==  S - B
          S = min(lsh, rsh)_cell - min(band(lsh_f), band(rsh_f))     [the SHOULDER term]
          B = bottom_cell         - band(bottom_f)                   [the BOTTOM   term]

      so the disagreement between the two metrics is the sum of two named parts, and asking which
      one carries it is arithmetic rather than judgement.  AR1a asserts the identity.

  (3) The three candidates s153 and s152 named — the CENTRE offset, the null's ASYMMETRY, and the
      censoring — are screened directly.  Two of them cost nothing: the centre is already returned
      per cell by the reader, and the censoring margin is already returned by `curves(meta=True)`.
      Screening a named carrier before building the solve that would chase it is this project's
      cheapest repeated win (s134, s139, s140, s145).

⭐ ASYMMETRY NEEDS ONE NEW READING AND IT IS ADDITIVE.  `q`/`q_interp` are WIDTHS, and a width
cannot express asymmetry.  An RBJ peaking section is symmetric in log-f BY CONSTRUCTION, so if the
pedal's null is not, that is a shape coordinate the (f0, Q, gain) family cannot span at ANY setting
— a structural statement, not a tuning one.  `notch_geometry` now also returns the two interpolated
half-depth crossings (`xlo_f`, `xhi_f`) separately; nothing existing reads them, and GATE AP's and
GATE AQ's stored reports are byte-identical after the change (the s153 `q_interp` pattern).

⚠ WHAT THIS GATE DOES NOT DO.  It ships nothing, proposes no constant, and does not re-open the
USER DECISION s153 closed (`kNotchGainDb` stays as shipped — that decision rested on the
shipped-vs-area-solved *table* trade, which nothing here touches).  What it can change is which
mechanism the residual is attributed to, and therefore what a future session would build.

    /opt/homebrew/bin/python3.11 analysis/notch_residual_gate.py
"""
import json
import os
import sys
from math import comb

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import feature_locus_gate as W          # noqa: E402
import notch_shape_gate as AQ           # noqa: E402  — the 2-D solve, imported not copied
import null_depth_censor_gate as AP     # noqa: E402  — the 1-D solve, imported not copied
import od_tone_restore_fit as F         # noqa: E402

REAL = AP.REAL
ROWS = AP.ROWS
FIT_RESIDUAL_DB = AP.FIT_RESIDUAL_DB     # s151's own converged residual, ±0.83 dB

# AQ4's own three-way scale, imported so this gate's verdict is comparable to AQ4's BY CONSTRUCTION
# rather than by my reading it off its source.  (AQ4: COLLAPSED if <= the fit residual, SHRANK if it
# more than halves, SURVIVED otherwise.)
SHRANK_FACTOR = 0.5

# The reader's own resolution, derived from the grid rather than chosen: GATE W's grid is 1/48 oct,
# so a centre can only be located to one cell and any offset below that is not a measurement.
CELL_FRAC = 2.0 ** (1.0 / 48.0) - 1.0

REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports",
                      "s154_notch_residual.json")
AQ_REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports",
                         "s153_notch_shape.json")
AP_REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports",
                         "s152_null_depth_censor.json")

FAIL = []


def fail(tag, msg):
    FAIL.append(tag)
    print(f"  ❌ {tag}: {msg}")


# ================================================================================================
# The two named parts of the metric difference, and the asymmetry
# ================================================================================================
def terms(g, d, geo=None):
    """-> (geometry, S, B) with `depth_point - depth_area == S - B` asserted at machine precision.

    This is not a model of the difference — it IS the difference, regrouped.  `depth_point` reads
    the bottom and the shallower shoulder as single grid CELLS; `depth_area` reads both as 1/6-oct
    power BANDS.  Grouping cell-minus-band per operand is therefore exact, and it splits the
    disagreement into the only two places it can live."""
    r = geo if geo is not None else F.notch_geometry(g, d)
    S = (min(r["lsh"], r["rsh"])
         - min(F.band_db_grid(g, d, r["lsh_f"]), F.band_db_grid(g, d, r["rsh_f"])))
    B = r["bottom"] - F.band_db_grid(g, d, r["f0"])
    resid = abs((r["depth_point"] - r["depth_area"]) - (S - B))
    return r, S, B, resid


def skew(r):
    """Log-f asymmetry of the null about its own bottom, in [-1, +1]; 0 = symmetric.

    ⚠ Uses the INTERPOLATED crossings.  On the snapped ones this would be quantised to whole cells
    in both directions, i.e. the s153 disease on a third statistic."""
    lo, hi, f0 = r.get("xlo_f"), r.get("xhi_f"), r["f0"]
    if lo is None or hi is None or not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return float("nan")
    right, left = np.log(hi / f0), np.log(f0 / lo)
    tot = right + left
    return float((right - left) / tot) if tot > 1e-12 else float("nan")


# ================================================================================================
# ONE computation pass — every sub-gate below reads these records
# ================================================================================================
def build():
    """-> list of per-(GRUNT, DRIVE, sweep) records.

    ⚠ Computed ONCE and shared, so that every statistic below — the paired gap, the pooled gap, the
    decomposition and all three candidate screens — is provably a re-aggregation of ONE set of
    numbers rather than four measurements that happen to agree."""
    T = F.shipped_tables()
    fs = 48000.0 * W.OS_FACTOR
    recs, ident = [], 0.0
    for gname, gpos, sname in ROWS:
        for fname, drv in F.SETS[sname]:
            for sw in REAL:
                g, ped, mod, meta = F.curves(fname, sw, meta=True)
                mod_off = mod - F.current_response(g, drv, fs, T, gpos, F.clean_frac_of(fname))
                try:
                    pg, Sp, Bp, e1 = terms(g, ped)
                except RuntimeError:
                    continue                     # only the PEDAL side can cost a cell here
                ident = max(ident, e1)
                one = {m: AP.solve_gain(g, mod_off, pg, drv, gpos, T, fs, m)
                       for m in ("point", "area")}
                two = {m: AQ.solve_gain_q(g, mod_off, pg, drv, T, fs, m)
                       for m in ("point", "area")}
                # The composite at the POINT-matched 1-D solve: depth_point then agrees with the
                # pedal's BY CONSTRUCTION, so every remaining difference between the two curves'
                # metric readings is shape and nothing else.
                cg = Sc = Bc = None
                if one["point"] is not None:
                    q = F.lerp5(T["kNotchQ"][gpos], drv, T["kX"])
                    comp = (mod_off
                            + F.rbj_peak_db(g, fs, T["kNotchFreq"], q, -one["point"])
                            + F.rbj_peak_db(g, fs, T["kPeakFreq"], T["kPeakQ"],
                                            F.lerp5(T["kPeakGainDb"], drv, T["kX"])))
                    try:
                        cg, Sc, Bc, e2 = terms(g, comp)
                        ident = max(ident, e2)
                    except RuntimeError:
                        cg = None
                recs.append({
                    "grunt": gname, "gpos": gpos, "drv": drv, "sweep": sw, "file": fname,
                    "ped": pg, "S_p": Sp, "B_p": Bp, "skew_p": skew(pg),
                    "comp": cg, "S_c": Sc, "B_c": Bc,
                    "skew_c": skew(cg) if cg else float("nan"),
                    "D": ((Sp - Bp) - (Sc - Bc)) if cg else float("nan"),
                    "g1_pt": one["point"], "g1_ar": one["area"],
                    "t2_pt": two["point"], "t2_ar": two["area"],
                    "q_ship": F.lerp5(T["kNotchQ"][gpos], drv, T["kX"]),
                    "margin": pg["bottom"] - float(meta["ped_floor"]),
                })
    return recs, ident


def _paired(recs, which):
    """-> array of per-sweep (area gain − point gain), for the 1-D ('g1') or 2-D ('t2') design."""
    out = []
    for r in recs:
        if which == "g1":
            a, b = r["g1_pt"], r["g1_ar"]
            if a is None or b is None:
                continue
            out.append((r, b - a))
        else:
            a, b = r["t2_pt"], r["t2_ar"]
            if a is None or b is None or a[3] != "ok" or b[3] != "ok":
                continue
            out.append((r, b[0] - a[0]))
    return out


def _cellmeans(recs, which):
    """Re-aggregate per (GRUNT, DRIVE) exactly as AP3/AQ3 do: mean per METRIC over the sweeps that
    solved for THAT metric, unreachable excluded per metric."""
    cells = {}
    for r in recs:
        key = (r["grunt"], r["drv"])
        c = cells.setdefault(key, {"pt": [], "ar": []})
        if which == "g1":
            if r["g1_pt"] is not None:
                c["pt"].append(r["g1_pt"])
            if r["g1_ar"] is not None:
                c["ar"].append(r["g1_ar"])
        else:
            for tag, t in (("pt", r["t2_pt"]), ("ar", r["t2_ar"])):
                if t is not None and t[3] == "ok":
                    c[tag].append(t[0])
    return cells


# ================================================================================================
# AR1 — known answers
# ================================================================================================
def ar1a(ident, recs):
    """THE IDENTITY.  depth_point − depth_area == S − B, on every curve this gate reads.

    ⭐ No threshold to argue about: this is algebra, and if it does not hold at machine precision
    the decomposition below is not a decomposition of anything."""
    print("\nAR1a  KNOWN ANSWER — the metric difference IS S − B (algebra, not a model)")
    n = sum(1 for r in recs if r["comp"] is not None)
    print(f"  worst |(depth_point − depth_area) − (S − B)| = {ident:.2e} dB "
          f"over {2 * len(recs) - n} curve readings")
    if not recs:
        fail("AR1a", "no curve was read at all (`empty-gate-must-fail`)")
    elif ident > 1e-9:
        fail("AR1a", f"the identity does not hold ({ident:.2e} dB) — AR4's decomposition is not a "
                     f"decomposition; nothing below it is readable")
    else:
        print("  ✅ exact ⇒ the shoulder term and the bottom term are the ONLY two places the")
        print("     point-vs-area disagreement can live, and AR4 measures which.")


def ar1b(recs):
    """CROSS-GATE KNOWN ANSWER — re-aggregating these records per cell must reproduce the STORED
    GATE AP and GATE AQ reports.

    ⭐ This is what makes AR2's re-pairing a RE-AGGREGATION rather than a second measurement: if my
    per-sweep solves aggregate to AP3's and AQ3's published per-cell numbers, then the paired
    statistic below is built from the very numbers AQ4 averaged, and any difference between the two
    is the ORDER OF OPERATIONS and nothing else.
    ⚠ WHAT IT IS BLIND TO (s145/s149, stated rather than discovered later): both sides run the same
    solvers on the same curves — it validates the aggregation, not the solve.  The solve is
    certified by AP1a/AP1c and AQ1a/AQ1d, which is why this gate re-uses them rather than
    re-implementing anything.
    ⚠ A failure here is at least as likely to be a STALE stored report as a defect in this gate;
    the message says so, because a guard that names an epoch must diagnose it (s146)."""
    print("\nAR1b  CROSS-GATE KNOWN ANSWER — do these records re-aggregate to AP3 and AQ3?")
    worst = {"1-D vs GATE AP": 0.0, "2-D vs GATE AQ": 0.0}
    n = {"1-D vs GATE AP": 0, "2-D vs GATE AQ": 0}
    if os.path.exists(AP_REPORT):
        tab = json.load(open(AP_REPORT)).get("table", {})
        for (gname, drv), c in _cellmeans(recs, "g1").items():
            row = tab.get(f"{gname}_{drv:.2f}")
            if not row or not c["pt"] or not c["ar"]:
                continue
            n["1-D vs GATE AP"] += 1
            worst["1-D vs GATE AP"] = max(
                worst["1-D vs GATE AP"],
                abs(float(np.mean(c["pt"])) - row["solve_point"]),
                abs(float(np.mean(c["ar"])) - row["solve_area"]))
    else:
        fail("AR1b", f"{os.path.basename(AP_REPORT)} is missing — the 1-D known answer cannot run")
    if os.path.exists(AQ_REPORT):
        aq3 = json.load(open(AQ_REPORT)).get("aq3", {})
        for (gname, drv), c in _cellmeans(recs, "t2").items():
            row = aq3.get(f"{gname}|{drv}")
            if not row or row.get("pt_g") is None or not c["pt"] or not c["ar"]:
                continue
            n["2-D vs GATE AQ"] += 1
            worst["2-D vs GATE AQ"] = max(worst["2-D vs GATE AQ"],
                                          abs(float(np.mean(c["pt"])) - row["pt_g"]),
                                          abs(float(np.mean(c["ar"])) - row["ar_g"]))
    else:
        fail("AR1b", f"{os.path.basename(AQ_REPORT)} is missing — the 2-D known answer cannot run")
    for k in worst:
        print(f"  {k:<16}  worst |mine − stored| = {worst[k]:.2e} dB over n={n[k]} cells")
    if min(n.values()) == 0:
        fail("AR1b", "one of the two comparisons ran over ZERO cells (`empty-gate-must-fail`)")
    elif max(worst.values()) > 1e-6:
        fail("AR1b", f"re-aggregation does not reproduce the stored reports "
                     f"({max(worst.values()):.2e} dB).  EITHER these records are not the ones AQ4 "
                     f"averaged — in which case AR2/AR3 below are a different measurement and are "
                     f"NOT a correction to AQ4 — OR the stored report predates a change to the "
                     f"solve/curves.  Re-run GATE AP and GATE AQ before reading on.")
    else:
        print("  ✅ identical ⇒ AR2's paired statistic is built from the SAME numbers AQ4 averaged,")
        print("     so any difference between them is the order of operations and nothing else.")
    return worst, n


def ar1c():
    """SYNTHETIC CONTROL — when the pedal's null IS the composite's, every statistic here must be 0.

    ⭐ This is the arm that can fail in BOTH directions, which is what a decomposition needs: on a
    synthetic pedal built as `composite(G*, Q*)` on a flat background the two curves are identical
    at the solved point, so D must vanish, the paired gap must vanish under both designs, and the
    two skews must agree.  A non-zero anywhere is this gate's own arithmetic, not the device's."""
    print("\nAR1c  SYNTHETIC CONTROL — pedal := composite(G*, Q*) ⇒ every residual must be 0")
    T = F.shipped_tables()
    fs = 48000.0 * W.OS_FACTOR
    g = W.GRID
    flat = np.zeros_like(g)
    print(f"  {'G*':>6} {'Q*':>6} | {'D':>10} {'1-D gap':>9} {'2-D gap':>9} | "
          f"{'skew ped':>9} {'skew comp':>9}")
    worst = 0.0
    for gstar, qstar in ((10.0, 6.0), (18.0, 12.0), (24.0, 18.0)):
        ped = flat + F.rbj_peak_db(g, fs, T["kNotchFreq"], qstar, -gstar)
        pgeo, Sp, Bp, _ = terms(g, ped)
        # Solve against the synthetic pedal with the SECTION's own Q, i.e. Q is matched by
        # construction — the 1-D and 2-D designs then differ only in whether they say so.
        one = {m: AQ.solve_gain_at_q(g, flat, pgeo["depth_area" if m == "area" else "depth_point"],
                                     qstar, 0.5, T, fs, m) for m in ("point", "area")}
        two = {m: AQ.solve_gain_q(g, flat, pgeo, 0.5, T, fs, m) for m in ("point", "area")}
        if any(v is None for v in one.values()) or any(v is None or v[3] != "ok"
                                                       for v in two.values()):
            fail("AR1c", f"no solution for the synthetic (G*={gstar}, Q*={qstar}) — the control "
                         f"cannot run, so AR3/AR4 are ungated")
            continue
        comp = flat + F.rbj_peak_db(g, fs, T["kNotchFreq"], qstar, -one["point"])
        cgeo, Sc, Bc, _ = terms(g, comp)
        D = (Sp - Bp) - (Sc - Bc)
        g1, g2 = one["area"] - one["point"], two["area"][0] - two["point"][0]
        ds = abs(skew(pgeo) - skew(cgeo))
        worst = max(worst, abs(D), abs(g1), abs(g2), ds)
        print(f"  {gstar:6.1f} {qstar:6.1f} | {D:10.2e} {g1:9.2e} {g2:9.2e} | "
              f"{skew(pgeo):9.4f} {skew(cgeo):9.4f}")
    # The bar is the solvers' own tolerance (both brentq calls run xtol=1e-3), not a chosen number.
    if worst > 5e-3:
        fail("AR1c", f"the synthetic control does not return zero ({worst:.2e}) — the residual "
                     f"measured below is at least partly this gate's own arithmetic")
    else:
        print(f"  ✅ all zero to {worst:.1e} (the solvers' own xtol is 1e-3) ⇒ a non-zero residual")
        print("     on real data is the pedal's shape and not this gate's.")
    return worst


# ================================================================================================
# AR2 — THE ORDER OF OPERATIONS
# ================================================================================================
def ar2(recs):
    """Is AQ4's gap a PAIRED statistic?  It is not, and this measures what that costs.

    AQ4 computes  |mean_sweeps(gain_area) − mean_sweeps(gain_point)|  per cell.  If the per-sweep
    gap changes sign across sweeps, the two means cancel it — and there is no reason for the two
    designs to cancel by the same amount, so the RATIO between them (which is AQ4's whole verdict)
    is not a property of shape-matching.

    ⚠ Two separate defects are measured here and they must not be conflated:
      (a) the ORDER (mean-then-difference vs difference-then-mean), which touches every cell;
      (b) the MEMBERSHIP (AQ3 drops unreachable cells per METRIC, so a cell's two means can be over
          different sweep sets), which is named per cell rather than estimated."""
    print("\nAR2  ORDER OF OPERATIONS — is AQ4's gap paired?")
    print("  (a) MEMBERSHIP: cells whose point-mean and area-mean are over DIFFERENT sweep sets")
    bad = []
    for which, label in (("g1", "1-D"), ("t2", "2-D")):
        for (gname, drv), c in sorted(_cellmeans(recs, which).items()):
            if len(c["pt"]) != len(c["ar"]) and c["pt"] and c["ar"]:
                bad.append((label, gname, drv, len(c["pt"]), len(c["ar"])))
    if bad:
        for label, gname, drv, a, b in bad:
            print(f"      ⛔ {label} {gname:<6} {drv:4.2f}: point mean over {a} sweep(s), "
                  f"area mean over {b} — the 'gap' pairs different data")
    else:
        print("      ✅ none — every cell's two means are over the same sweeps")

    print("\n  (b) THE SIGN STRUCTURE that makes the order matter, per stimulus rung:")
    print("      ⚠ computed on the PAIRED set (cells solving under BOTH designs), so the two rows")
    print("        are over identical membership and the comparison is not itself unpaired.")
    print(f"      {'design':<6} | " + " ".join(f"{s[-3:]:>14}" for s in REAL) + f" | {'pooled':>14}")
    stat = {}
    keep = {k for k, _ in [((r["grunt"], r["drv"], r["sweep"]), d) for r, d in _paired(recs, "g1")]}
    keep &= {(r["grunt"], r["drv"], r["sweep"]) for r, _ in _paired(recs, "t2")}
    for which, label in (("g1", "1-D"), ("t2", "2-D")):
        pr = [(r, d) for r, d in _paired(recs, which)
              if (r["grunt"], r["drv"], r["sweep"]) in keep]
        cells = []
        for sw in REAL:
            v = np.array([d for r, d in pr if r["sweep"] == sw])
            cells.append(f"{v.mean():+7.2f} ({int((v < 0).sum())}/{len(v)})" if len(v)
                         else f"{'—':>14}")
        allv = np.array([d for _, d in pr])
        stat[label] = {"per_sweep": {sw: [float(np.mean([d for r, d in pr if r["sweep"] == sw])),
                                          int(len([1 for r, _ in pr if r["sweep"] == sw]))]
                                     for sw in REAL},
                       "signed_mean": float(allv.mean()), "abs_mean": float(np.abs(allv).mean()),
                       "n": len(allv), "n_negative": int((allv < 0).sum())}
        print(f"      {label:<6} | " + " ".join(cells)
              + f" | {allv.mean():+7.2f} ({int((allv < 0).sum())}/{len(allv)})")
    print("      cells are: signed mean gap (area − point), and (# negative / n)")
    # The verdict has to be computable and to have a negation: does the per-sweep gap change sign
    # across the stimulus axis in the 1-D design?  That is the precondition for the cancellation.
    pr1 = _paired(recs, "g1")
    means1 = [float(np.mean([d for r, d in pr1 if r["sweep"] == sw])) for sw in REAL
              if any(r["sweep"] == sw for r, _ in pr1)]
    flips = len(set(np.sign(means1))) > 1
    if flips:
        print("\n  ⛔ THE 1-D PER-SWEEP GAP CHANGES SIGN ACROSS THE STIMULUS AXIS ⇒ averaging over")
        print("     sweeps before differencing CANCELS it, and there is no reason for the 2-D arm")
        print("     to cancel by the same amount.  AQ4's ratio is therefore not readable as a")
        print("     property of shape-matching; AR3 re-computes it paired.")
    else:
        print("\n  ✅ the 1-D per-sweep gap is one-signed across the stimulus axis ⇒ averaging")
        print("     before differencing cannot cancel it, and AQ4's pooled ratio is safe as it")
        print("     stands.  AR3 is then a corroboration rather than a correction.")
    return stat, bad, flips


# ================================================================================================
# AR3 — the paired gap, and AQ4's verdict recomputed on it
# ================================================================================================
def ar3(recs, stat):
    """AQ4's question, asked with the stimulus axis intact.

    ⛔ The membership is PAIRED TWICE OVER: a cell votes only if BOTH metrics solve under BOTH
    designs, so the 1-D and 2-D columns are over an identical set of (GRUNT, DRIVE, sweep) cells.
    Without that the comparison is between two different populations, which is the defect AR2(a)
    finds in the pooled form and would be silly to re-commit here.
    ⚠ The scale is AQ4's own, IMPORTED (`FIT_RESIDUAL_DB`, and its 0.5x SHRANK threshold), so the
    two verdicts are comparable by construction rather than by my transcribing its thresholds."""
    print("\nAR3  THE PAIRED GAP — does shape-matching close it, with the axis intact?")
    p1 = {(r["grunt"], r["drv"], r["sweep"]): d for r, d in _paired(recs, "g1")}
    p2 = {(r["grunt"], r["drv"], r["sweep"]): d for r, d in _paired(recs, "t2")}
    keys = sorted(set(p1) & set(p2))
    dropped = sorted((set(p1) | set(p2)) - set(keys))
    if not keys:
        fail("AR3", "no cell solves under both designs (`empty-gate-must-fail`)")
        return None
    a = np.array([p1[k] for k in keys])
    b = np.array([p2[k] for k in keys])
    m1, m2 = float(np.abs(a).mean()), float(np.abs(b).mean())
    print(f"  n = {len(keys)} (GRUNT, DRIVE, sweep) cells solving under BOTH designs; "
          f"{len(dropped)} named-excluded:")
    for k in dropped:
        print(f"      excluded {k[0]:<6} {k[1]:4.2f} {k[2][-3:]:>4} — "
              f"{'no 1-D solve' if k not in p1 else 'unreachable at free Q'}")
    print(f"\n  |gap| mean: {m1:.2f} dB at the shipped Q → {m2:.2f} dB with Q free "
          f"({100 * (m2 - m1) / max(m1, 1e-9):+.0f} %)")
    print(f"  bar: the fit's own residual, ±{FIT_RESIDUAL_DB:.2f} dB (imported from GATE AP).")
    # ⛔ AQ4's own pair of numbers is READ FROM ITS STORED REPORT, never transcribed
    # (`rebuild-targets-dont-transcribe`).  A hardcoded "2.69 → 2.16" here would go stale the first
    # time GATE AQ is re-run, and it is the number this gate's entire headline is a comparison
    # against — the worst possible thing to keep a private copy of.
    try:
        a4 = json.load(open(AQ_REPORT))["aq4_gap_shipQ_freeQ"]
        q1, q2, qv = float(a4[0]), float(a4[1]), str(a4[2])
    except Exception as e:                                        # noqa: BLE001
        fail("AR3", f"cannot read AQ4's own gap from {os.path.basename(AQ_REPORT)} ({e}) — the "
                    f"comparison this gate exists to make has nothing to compare against")
        q1 = q2 = float("nan")
        qv = "?"
    print(f"  ⚠ AQ4 asks the SAME question of the SAME numbers (AR1b) and reads "
          f"{q1:.2f} → {q2:.2f} dB ({100 * (q2 - q1) / max(q1, 1e-9):+.0f} %): {qv},")
    print("    because it averages each metric over sweeps BEFORE differencing — see AR2.")
    print(f"  ⭐ THE TWO AGREE ON THE *AFTER* VALUE ({m2:.2f} vs {q2:.2f} dB) AND DISAGREE ON THE")
    print(f"     *BEFORE* ONE ({m1:.2f} vs {q1:.2f}) ⇒ what the pooled form mis-states is its")
    print("     BASELINE, not the shape-matched arm.  That is the sign change in AR2's 1-D row")
    print("     cancelling under the mean, and the 2-D row having almost none left to cancel.")
    print("  ⚠⚠ BOTH FORMS ARE REAL AND THEY ANSWER DIFFERENT QUESTIONS — do NOT read this as")
    print("     'AQ4 was wrong'.  The shipped table has ONE entry per (GRUNT, DRIVE), so a mean")
    print("     over sweeps is exactly what WOULD be shipped ⇒ AQ4's pooled gap is the right")
    print("     statistic for the SHIPPING question GATE AP's user decision turned on, and that")
    print("     decision is untouched here.  What a pooled form cannot support is a MECHANISM")
    print("     claim: 'does shape-matching close the disagreement' is about the two metrics as")
    print("     MEASUREMENTS, and there the stimulus axis has to stay intact.  ⇒ the correction is")
    print("     to the INFERENCE AQ4 drew, not to the number it shipped.")
    if m2 <= FIT_RESIDUAL_DB:
        verdict = "COLLAPSED"
        print("  ⭐⭐ COLLAPSED — with the shape matched the two metrics agree inside the fit's own")
        print("     residual ⇒ AP6's attribution is confirmed and the metric choice is not a")
        print("     decision at all.")
    elif m2 < SHRANK_FACTOR * m1:
        verdict = "SHRANK"
        print("  ⭐ SHRANK by more than half without clearing the fit's residual ⇒ the shape")
        print("     mismatch is the LARGER PART of the disagreement but not all of it.  AP6's")
        print("     attribution is largely rehabilitated; the user decision still stands, because")
        print("     what is left still exceeds the bar.")
    else:
        verdict = "SURVIVED"
        print("  ⛔ DID NOT COLLAPSE and did not halve ⇒ Q is not the shape coordinate that")
        print("     carries the disagreement, and AQ4's reading stands under pairing too.")
    return {"n": len(keys), "abs_1d": m1, "abs_2d": m2, "verdict": verdict,
            "aq4": [q1, q2, qv],
            "signed_1d": float(a.mean()), "signed_2d": float(b.mean()),
            "neg_1d": int((a < 0).sum()), "neg_2d": int((b < 0).sum()),
            "excluded": [list(k) for k in dropped]}


# ================================================================================================
# AR4 — the decomposition
# ================================================================================================
def ar4(recs):
    """WHICH of the two terms carries the metric difference: the SHOULDERS or the BOTTOM?

    Read at the POINT-matched 1-D solve, where the two curves' point depths agree by construction,
    so `D = (S − B)_pedal − (S − B)_composite` is exactly the residual depth disagreement that
    forces the two solves apart.
    ⭐ Both the share and the correlation are printed: a term can carry the MEAN without carrying
    the VARIATION, and a claim about a mechanism needs both."""
    print("\nAR4  DECOMPOSITION — shoulder term or bottom term?")
    ok = [r for r in recs if r["comp"] is not None and np.isfinite(r["D"])]
    if len(ok) < 5:
        fail("AR4", f"only {len(ok)} cells have both curves readable — too few to decompose")
        return None
    dS = np.array([r["S_p"] - r["S_c"] for r in ok])
    dB = np.array([r["B_p"] - r["B_c"] for r in ok])
    D = np.array([r["D"] for r in ok])
    print(f"  n = {len(ok)}   D := (S−B)_pedal − (S−B)_composite  "
          f"(D > 0 ⇔ the area solve wants LESS gain)")
    print(f"  {'term':<22} {'mean':>8} {'|mean|/|D|':>11} {'corr with D':>12} {'same-sign':>10}")
    out = {}
    for name, v, sgn in (("dS  (shoulders)", dS, +1.0), ("dB  (bottom)", dB, -1.0)):
        c = float(np.corrcoef(v, D)[0, 1])
        share = float(abs(v.mean()) / max(abs(D.mean()), 1e-9))
        same = int(np.sum(np.sign(v) == np.sign(v.mean())))
        print(f"  {name:<22} {v.mean():+8.3f} {share:11.2f} {c:+12.3f} {same:6d}/{len(v)}")
        out[name.split()[0]] = {"mean": float(v.mean()), "share": share, "corr": c,
                                "same_sign": same, "n": len(v)}
    print(f"  {'D = dS − dB':<22} {D.mean():+8.3f} {1.0:11.2f} {1.0:+12.3f} "
          f"{int(np.sum(np.sign(D) == np.sign(D.mean()))):6d}/{len(D)}")
    cS, cB = abs(out["dS"]["corr"]), abs(out["dB"]["corr"])
    if cB > cS and out["dB"]["share"] > out["dS"]["share"]:
        print("\n  ⇒ THE BOTTOM TERM CARRIES IT.  The disagreement is a difference in how much the")
        print("     1/6-octave band averages the notch BOTTOM away — a sharpness difference INSIDE")
        print("     the half-depth width, which is a shape coordinate neither the depth nor Q pins.")
    elif cS > cB and out["dS"]["share"] > out["dB"]["share"]:
        print("\n  ⇒ THE SHOULDER TERM CARRIES IT.  The disagreement is not at the null at all: it")
        print("     is the local curvature of the SHOULDERS the two metrics read differently, which")
        print("     no section centred at the null can address.")
    else:
        print("\n  ⇒ SPLIT — neither term dominates on both share and correlation; the two must be")
        print("     quoted together and no single-mechanism story is supported.")
    return out


# ================================================================================================
# AR5 — the three named candidates, screened
# ================================================================================================
def ar5(recs, paired2):
    """The candidates s152/s153 named for this residual, screened before any of them is built.

    (a) CENTRE OFFSET — s153's `NEXT` #4 ("free the centre, not the Q").  Bar is the reader's own
        resolution (one 1/48-oct cell), derived from the grid rather than chosen.
    (b) CENSORING — AP6's alternative, retested on the quantity that actually matters here (the
        residual AFTER shape matching) rather than on the 1-D gap AP6 used.
    (c) ASYMMETRY — s153's other named candidate, and the only one that is structural: an RBJ
        peaking section is symmetric in log-f, so a pedal null that is not cannot be matched at ANY
        (f0, Q, gain).
    ⚠ All three are screens on a NAMED carrier, which is necessary and never sufficient (s140): a
    null answer here does not say the residual has no cause, only that these three are not it."""
    print("\nAR5  THE NAMED CANDIDATES, screened")
    ok = [r for r in recs if r["comp"] is not None]
    res = {}

    # (a) CENTRE ------------------------------------------------------------------------------
    cells = np.array([(r["ped"]["f0"] - r["comp"]["f0"]) / (r["ped"]["f0"] * CELL_FRAC)
                      for r in ok])
    within = int(np.sum(np.abs(cells) <= 1.0))
    print(f"  (a) CENTRE   pedal f0 − composite f0, in 1/48-oct CELLS "
          f"(the reader's own resolution)")
    print(f"      mean {cells.mean():+.2f} cells, range {cells.min():+.2f}..{cells.max():+.2f}, "
          f"|offset| ≤ 1 cell in {within}/{len(cells)}")
    off = [r for r in ok if abs((r["ped"]["f0"] - r["comp"]["f0"])
                                / (r["ped"]["f0"] * CELL_FRAC)) > 1.0]
    for r in off:
        print(f"        > 1 cell: {r['grunt']:<6} {r['drv']:4.2f} {r['sweep'][-3:]:>4}  "
              f"pedal {r['ped']['f0']:.1f} Hz vs composite {r['comp']['f0']:.1f} Hz")
    if within >= 0.8 * len(cells):
        print("      ⛔ REFUTED as the carrier — the two centres already agree to within the")
        print("         reader's resolution in the large majority of cells, so freeing f0 has")
        print("         almost nothing to move.  Do NOT build the 3-D solve on this basis.")
    else:
        print("      ⭐ ADMISSIBLE — the centres differ by more than the reader can resolve in a")
        print("         substantial fraction of cells, so freeing f0 is worth a solve.")
    res["centre_cells"] = {"mean": float(cells.mean()), "min": float(cells.min()),
                           "max": float(cells.max()), "within_1cell": within, "n": len(cells)}

    # (b) CENSORING ---------------------------------------------------------------------------
    key = {(r["grunt"], r["drv"], r["sweep"]): d for r, d in paired2}
    m = np.array([r["margin"] for r in recs if (r["grunt"], r["drv"], r["sweep"]) in key])
    gp = np.array([key[(r["grunt"], r["drv"], r["sweep"])] for r in recs
                   if (r["grunt"], r["drv"], r["sweep"]) in key])
    print(f"\n  (b) CENSORING  pedal-bottom margin above its own deconvolution residue, vs the")
    print(f"      residual gap AFTER shape matching   (n = {len(m)})")
    if len(m) < 5:
        fail("AR5", f"only {len(m)} shape-matched cells — the censoring screen cannot run")
        res["censor_corr"] = None
    else:
        rc = float(np.corrcoef(m, np.abs(gp))[0, 1])
        rs = float(np.corrcoef(m, gp)[0, 1])
        cens = int(np.sum(m <= 0))
        print(f"      censored (margin ≤ 0) in {cens}/{len(m)} cells; margin range "
              f"{m.min():+.1f}..{m.max():+.1f} dB")
        print(f"      corr(margin, |residual gap|) = {rc:+.3f}   "
              f"corr(margin, signed) = {rs:+.3f}")
        print(f"      for scale: GATE AP measured corr(margin, point−area DEPTH gap) = −0.668 on")
        print(f"      these same margins — a DIFFERENT quantity, so it is a scale reference and")
        print(f"      NOT a bar.")
        # ⚠⚠ THE FIRST DRAFT GATED THIS ON |r| < 0.3, WHICH IS A NUMBER I INVENTED
        # (`a-threshold-you-guessed-is-not-a-guard`, s109) — and at r = −0.437 the whole verdict
        # rested on it.  Replaced by two statements that each answer a question the invented bar
        # was conflating:
        #   (i)  is it distinguishable from zero AT ALL?  permutation test, no distributional
        #        assumption, on the 21 cells themselves;
        #   (ii) can it BE the carrier?  r² is the share of the residual's variance the censoring
        #        can account for, and "the carrier" means more than everything else combined —
        #        so 0.5 is definitional, not chosen.
        rng = np.random.default_rng(20260805)
        a = np.abs(gp)
        null = np.array([abs(np.corrcoef(rng.permutation(m), a)[0, 1]) for _ in range(20000)])
        p = float((np.sum(null >= abs(rc)) + 1) / (len(null) + 1))
        r2 = float(rc * rc)
        print(f"      permutation test (20 000 shuffles of the margin against the same residuals):")
        print(f"        p = {p:.4f}   ⇒ {'distinguishable from zero' if p < 0.05 else 'NOT distinguishable from zero'}")
        print(f"      r² = {r2:.3f} ⇒ censoring accounts for {100 * r2:.0f} % of the residual's")
        print(f"        variance; {100 * (1 - r2):.0f} % is something else.")
        # ⚠⚠ p LANDS ON THE 0.05 CONVENTION (0.0523 as measured), so say out loud what does NOT
        # depend on it: BOTH the p >= 0.05 branch and the r² < 0.5 branch conclude "not the
        # carrier", and only the wording differs.  Replacing one invented bar with a conventional
        # one that the data sits on top of would have been the same mistake in a lab coat — the
        # load-bearing number here is r², which is a SHARE and needs no threshold to read.
        if 0.02 <= p <= 0.10:
            print(f"      ⚠ p sits ON the 0.05 convention, so do NOT quote the branch label as the")
            print(f"        finding.  What is bar-free: r² = {r2:.3f} ⇒ censoring cannot be the")
            print(f"        carrier under EITHER branch, because it leaves {100 * (1 - r2):.0f} % "
                  f"unexplained.")
        if p >= 0.05:
            print("      ⛔ REFUTED as the carrier — the association is not distinguishable from")
            print("         zero at this n.  Corroborates AP6 from a second quantity.")
        elif r2 < 0.5:
            print("      ⚠ REAL BUT PARTIAL — the association survives the permutation test, so it")
            print("         is not noise, and it accounts for a MINORITY of the residual, so it")
            print("         cannot be the carrier.  ⇒ AP6's elimination is too strong as stated")
            print("         (censoring is not absent) and its CONCLUSION stands (censoring is not")
            print("         what the residual is).  Quote both halves; neither alone is honest.")
        else:
            print("      ⭐ ADMISSIBLE AS THE CARRIER — the association is real and accounts for the")
            print("         majority of the residual, so AP6's elimination needs re-opening.")
        res["censor_corr"] = {"abs": rc, "signed": rs, "n": len(m), "censored": cens,
                              "perm_p": p, "r2": r2}

    # (c) ASYMMETRY ---------------------------------------------------------------------------
    sp = np.array([r["skew_p"] for r in ok if np.isfinite(r["skew_p"])])
    sc = np.array([r["skew_c"] for r in ok if np.isfinite(r["skew_c"])])
    pair = [(r["skew_p"], r["skew_c"]) for r in ok
            if np.isfinite(r["skew_p"]) and np.isfinite(r["skew_c"])]
    print(f"\n  (c) ASYMMETRY  log-f skew about the null's own bottom, 0 = symmetric "
          f"(n = {len(pair)})")
    if len(pair) < 5:
        fail("AR5", f"only {len(pair)} cells have both skews — the asymmetry screen cannot run")
        res["skew"] = None
    else:
        d = np.array([a - b for a, b in pair])
        print(f"      pedal      mean {sp.mean():+.3f}  range {sp.min():+.3f}..{sp.max():+.3f}")
        print(f"      composite  mean {sc.mean():+.3f}  range {sc.min():+.3f}..{sc.max():+.3f}")
        npos, nneg = int(np.sum(d > 0)), int(np.sum(d < 0))
        print(f"      pedal − composite: mean {d.mean():+.3f}, |mean| {np.abs(d).mean():.3f}, "
              f"{npos} positive / {nneg} negative")
        # ⭐⭐ READ THE DIRECTION BEFORE THE SIZE — s153 named this candidate as "the PEDAL's null
        # is asymmetric and a symmetric section cannot match it", and the measurement says the
        # opposite side is the skewed one.  The section is symmetric in log-f BY CONSTRUCTION, so
        # any composite asymmetry is the MODEL's own underlying null, not the correction.  AR1c is
        # the control that licenses the comparison: with pedal := composite the two skews agree
        # EXACTLY, so the reader has no side-preference of its own.
        who = ("the COMPOSITE (⇒ the MODEL's own null)" if sc.mean() > sp.mean()
               else "the PEDAL")
        print(f"      ⇒ the more asymmetric side is {who}: "
              f"|skew| {abs(sp.mean()):.3f} pedal vs {abs(sc.mean()):.3f} composite")
        # Exact two-sided sign test — threshold-free, and it separates DIRECTION (is the difference
        # one-signed?) from SIZE (is it bigger than the reader can resolve?), which the first draft
        # conflated into one knife-edge verdict.
        k, n = max(npos, nneg), npos + nneg
        pk = 2.0 * sum(comb(n, i) for i in range(k, n + 1)) / (2.0 ** n) if n else 1.0
        pk = min(1.0, pk)
        print(f"      sign test on the difference: {k}/{n} one way, exact two-sided p = {pk:.4f}")
        # The size bar is the reader's own resolution, expressed as skew: one grid cell of asymmetry
        # on a null whose half-width is the measured median, derived per run.  ⚠⚠ THE FIRST DRAFT
        # PUT THE ENTIRE VERDICT ON THIS ONE NUMBER AND IT LANDED 1.4 % INSIDE IT (0.208 vs 0.211).
        # A verdict that flips on 1.4 % of a derived bar is not a verdict — so the bar is now SWEPT
        # and the verdict is computed as BAR-SENSITIVE where it is (s137's GATE AH4b pattern).
        hw = float(np.median([np.log(r["ped"]["xhi_f"] / r["ped"]["xlo_f"])
                              for r in ok if np.isfinite(r["ped"].get("xhi_f", np.nan))]))
        cell = float(np.log(1.0 + CELL_FRAC) / max(hw, 1e-9))
        print(f"      size bar: one 1/48-oct cell of asymmetry on the median null width = "
              f"{cell:.3f}")
        sweep = {}
        for mult in (0.5, 1.0, 2.0):
            v = "OVER" if np.abs(d).mean() > cell * mult else "under"
            sweep[mult] = v
            print(f"        at {mult:>3}x the cell ({cell * mult:.3f}): |mean| "
                  f"{np.abs(d).mean():.3f} is {v}")
        flips = len(set(sweep.values())) > 1
        if pk < 0.05 and not flips and sweep[1.0] == "OVER":
            print("      ⭐ ADMISSIBLE — one-signed AND above the reader's resolution at every bar")
            print("         swept.  STRUCTURAL: no (f0, Q, gain) can span it.")
        elif pk < 0.05:
            print("      ⚠ ONE-SIGNED, AT THE READER'S RESOLUTION — two separate findings, and the")
            print("         first draft's single verdict could express neither.  The difference is")
            print("         NOT noise (sign test), so an asymmetry difference genuinely exists and")
            print("         it is the MODEL's null that carries it; but its SIZE is within a factor")
            print("         of ~2 of one grid cell, so this reader cannot say it is worth chasing.")
            print("         ⇒ NOT a licence to build, and NOT a refutation: it needs an estimator")
            print("         that resolves skew better than the 1/48-oct locator does.")
        else:
            print("      ⛔ REFUTED as the carrier — the difference is not even one-signed, so there")
            print("         is no asymmetry mismatch to chase at any size.")
        res["skew"] = {"ped_mean": float(sp.mean()), "comp_mean": float(sc.mean()),
                       "diff_mean": float(d.mean()), "diff_absmean": float(np.abs(d).mean()),
                       "cell": cell, "sign_p": pk, "npos": npos, "nneg": nneg,
                       "bar_sweep": {str(k2): v for k2, v in sweep.items()}, "n": len(pair)}
    return res


# ================================================================================================
# AR6 — the stimulus axis
# ================================================================================================
def ar6(recs):
    """Is the residual a fixed shape defect, or does it MOVE with stimulus?

    ⭐ This is s151 §6's architectural limit — a knob-keyed stage cannot track a stimulus-dependent
    feature — asked on a third axis, after the DEPTH (s151) and the Q (AQ2b).  If the residual
    changes sign across the stimulus ladder then no single (gain, Q) entry can be right at all
    three rungs whatever shape coordinate is freed, and the residual is not a shape defect to
    chase but a bound on what a DRIVE-keyed table can do."""
    print("\nAR6  THE STIMULUS AXIS — does the residual hold still?")
    ok = [r for r in recs if r["comp"] is not None and np.isfinite(r["D"])]
    if not ok:
        fail("AR6", "no cell has both curves readable (`empty-gate-must-fail`)")
        return None
    print(f"  {'rung':<16} {'n':>3} {'mean D':>8} {'D > 0':>8} | "
          f"{'ped Q':>7} {'comp Q':>7} {'ped−comp':>9}")
    out = {}
    for sw in REAL:
        v = [r for r in ok if r["sweep"] == sw]
        if not v:
            continue
        D = np.array([r["D"] for r in v])
        pq = np.array([r["ped"]["q_interp"] for r in v])
        cq = np.array([r["comp"]["q_interp"] for r in v])
        out[sw] = {"n": len(v), "meanD": float(D.mean()), "pos": int((D > 0).sum()),
                   "ped_q": float(pq.mean()), "comp_q": float(cq.mean())}
        print(f"  {sw:<16} {len(v):3d} {D.mean():+8.2f} {int((D > 0).sum()):5d}/{len(v):<2d} | "
              f"{pq.mean():7.2f} {cq.mean():7.2f} {pq.mean() - cq.mean():+9.2f}")
    signs = [np.sign(o["meanD"]) for o in out.values()]
    qsigns = [np.sign(o["ped_q"] - o["comp_q"]) for o in out.values()]
    flipD, flipQ = len(set(signs)) > 1, len(set(qsigns)) > 1
    if flipD:
        print("\n  ⛔ THE RESIDUAL CHANGES SIGN ACROSS THE STIMULUS LADDER.  No single (gain, Q)")
        print("     entry can be right at all three rungs, whatever shape coordinate is freed ⇒")
        print("     what is left after shape matching is not one shape defect but s151 §6's")
        print("     architectural limit, on a third axis (depth s151, Q AQ2b, and now this).")
    else:
        print("\n  ✅ the residual is one-signed across the stimulus ladder ⇒ it is a fixed shape")
        print("     defect that a better section could in principle address at every rung.")
    if flipQ:
        print("  ⛔ AND THE SHIPPED Q's OWN ERROR CROSSES ZERO on the same axis (too broad at one")
        print("     end of the ladder, too narrow at the other) — a slope error with a crossing,")
        print("     not an offset, so no single Q entry is 'closer'.")
    else:
        print("  ✅ the shipped Q's error is one-signed across the ladder, so a single Q entry")
        print("     could at least be moved in a consistent direction.")
    return {"per_sweep": out, "D_changes_sign": bool(flipD), "Qerr_changes_sign": bool(flipQ)}


def main():
    print("=" * 96)
    print("GATE AR — what carries AQ4's residual, and is AQ4's own statistic paired?")
    print("=" * 96)
    recs, ident = build()
    ar1a(ident, recs)
    kn = ar1b(recs)
    syn = ar1c()
    stat, memb, flips = ar2(recs)
    gap = ar3(recs, stat)
    dec = ar4(recs)
    cand = ar5(recs, _paired(recs, "t2"))
    stim = ar6(recs)

    print("\n" + "=" * 96)
    print("VERDICT")
    print("=" * 96)
    if gap:
        print(f"  AR3   paired |gap| {gap['abs_1d']:.2f} → {gap['abs_2d']:.2f} dB "
              f"({100 * (gap['abs_2d'] - gap['abs_1d']) / max(gap['abs_1d'], 1e-9):+.0f} %): "
              f"{gap['verdict']}  — AQ4's pooled form read {gap['aq4'][0]:.2f} → "
              f"{gap['aq4'][1]:.2f} ({100 * (gap['aq4'][1] - gap['aq4'][0]) / max(gap['aq4'][0], 1e-9):+.0f} %): "
              f"{gap['aq4'][2]}")
    if memb:
        print(f"  AR2   {len(memb)} cell(s) pair means over different sweep sets")
    if dec:
        print(f"  AR4   bottom term carries {dec['dB']['share']:.2f} of the mean "
              f"(corr {dec['dB']['corr']:+.2f}); shoulders {dec['dS']['share']:.2f} "
              f"(corr {dec['dS']['corr']:+.2f})")
    if cand.get("centre_cells"):
        c = cand["centre_cells"]
        print(f"  AR5a  centre offset ≤ 1 grid cell in {c['within_1cell']}/{c['n']} cells")
    if cand.get("censor_corr"):
        cc = cand["censor_corr"]
        print(f"  AR5b  corr(censoring margin, residual) = {cc['abs']:+.3f}, "
              f"permutation p = {cc['perm_p']:.4f}, r² = {cc['r2']:.3f}")
    if cand.get("skew"):
        s = cand["skew"]
        print(f"  AR5c  |skew(pedal) − skew(composite)| = {s['diff_absmean']:.3f} vs a one-cell "
              f"bar of {s['cell']:.3f}; sign test p = {s['sign_p']:.4f}, "
              f"more asymmetric side = {'composite' if s['comp_mean'] > s['ped_mean'] else 'pedal'}")
    if stim:
        print(f"  AR6   residual changes sign across stimulus: "
              f"{'YES' if stim['D_changes_sign'] else 'no'}; shipped-Q error crosses zero: "
              f"{'YES' if stim['Qerr_changes_sign'] else 'no'}")
    print(f"\n  {'❌ ' + ', '.join(sorted(set(FAIL))) if FAIL else '✅ all known answers hold'}")

    json.dump({"identity_worst": ident, "ar1b": kn, "ar1c_worst": syn, "ar2_stat": stat,
               "ar2_membership": [list(map(str, b)) for b in memb], "ar2_sign_flips": bool(flips),
               "ar3": gap, "ar4": dec, "ar5": cand, "ar6": stim,
               "fail": sorted(set(FAIL))}, open(REPORT, "w"), indent=1)
    print(f"  report -> {REPORT}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
