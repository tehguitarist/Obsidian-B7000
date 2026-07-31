#!/usr/bin/env python3.11
"""
even_low_screen.py -- screen even-order candidates on the CORRECTION-FREE 1 kHz axis,
at BOTH drive anchors SEPARATELY.

WHY THIS EXISTS (session 80).  Session 79 put our own model on `nd_tone_ladder.py`'s
1 kHz axis and found the thing that unblocks the even-order item:

    d(H2-H3) = model - ND      low-drive anchor  -7.93 dB      mid-drive anchor  +10.94 dB

i.e. our model sits BELOW ND at low drive and ABOVE it at mid drive, and the pooled number
(-2.9 dB) is a MIXTURE that cancels ~7.9 dB of real error.  Two consequences, both of which
this tool is built around:

 (1) ⭐⭐ THE STANDING "AN EVEN-ORDER CORRECTION MUST REGRESS THE ND MATRIX" RULE IS ONLY
     TRUE AT MID DRIVE.  It was written (reference-sources.md section 1(0), repeated as
     sessions 72(a)/73(6)/76(7)) on session 72's reading that we already sit AT ND at low
     drive -- which used the CHART's ND column (0.0).  Measured, ND's own low-drive H2-H3 is
     +10.1 and ours is +1.4, so at low drive the first ~7.9 dB of an even-order correction
     moves toward BOTH references at once.  That is the reason the item has been parked
     since session 76, and it is gone.

 (2) ⛔ SO THE GATE MUST BE THE TWO ANCHORS SEPARATELY, NEVER A POOLED SCORE.  A candidate
     that fixes low drive and wrecks mid drive scores WELL on any pooled statistic, because
     the two errors have opposite sign.  This tool refuses to print a combined number.

WHAT IT DOES.  Reads the REFERENCE side once, then for each candidate renders our own chain
at every capture's own condition (`captures.render_args`, never hand-written -- the
session-65 `--grunt` defect) and reports d(H2-H3) at each anchor, plus the per-order
absolutes beside it (`difference-statistics-hide-common-mode`).

  python3.11 analysis/even_low_screen.py [--candidate 'label:key=val,key=val'] ...

⚠ WHAT THIS IS NOT.  It is a SCREEN on a model-vs-ND statistic, not a ship decision.  ND's
even orders sit ~27 dB below hardware's, so "reaching ND" is not the target -- what makes
the low-drive move defensible is that ND lies BETWEEN us and hardware there, so the first
~7.9 dB is monotone toward both.  Anything past ND is a departure from the column the
129-capture matrix encodes and must be judged there, not here.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ONE definition of the extractor, the gates, the anchor rule and the correction sign --
# imported, never re-typed (the session-62 anti-divergence rule; session 33's transcription
# trap).  Every number below therefore comes from the identical code path that produced the
# session-79 record.
import nd_tone_ladder as N                                          # noqa: E402
import captures as C                                                # noqa: E402

# The session-79 record, for the SHIPPED point on this identical axis.  The screen REFUSES
# to rank if the baseline does not reproduce it: a cross-candidate table is only meaningful
# if the point every candidate is measured against is the one that was recorded
# (`verify-the-baseline-not-its-label`; the pattern is joint_even_fit.py's SHIP_RECORD).
SHIP_RECORD = {"low": -7.93, "mid": +10.94}
SHIP_TOL_DB = 0.35


def read_reference(files, jobs):
    """The ND side.  Independent of every candidate, so it is read exactly once."""
    with ProcessPoolExecutor(max_workers=max(1, jobs), initializer=N._init) as ex:
        results = list(ex.map(N.read_one, [f for f, _ in files]))
    data = {fn: cells for fn, cells, err in results if not err}
    bad = [(fn, err) for fn, cells, err in results if err]
    return data, bad


def read_candidate(files, fit, jobs):
    """Our own chain at every capture's own condition, under one FitParams override."""
    with ProcessPoolExecutor(max_workers=max(1, jobs), initializer=N._init_model,
                             initargs=(tuple(fit),)) as ex:
        res = list(ex.map(N.read_model, [f for f, _ in files]))
    data = {fn: cells for fn, cells, err in res if not err}
    bad = [(fn, err) for fn, cells, err in res if err]
    return data, bad


def anchored(mdata, mcontam, mnoisy, settings, mc23, mc45):
    """Anchor the model side by the IDENTICAL first-upward-crossing rule as the reference."""
    hits, nonmono = N.anchor_hits(mdata, mcontam, mnoisy, settings, mc23, mc45)
    return {lbl: {x["file"]: x for x in hits[lbl] if x["ok23"]} for lbl in N.ANCHOR_H3}, nonmono


def gate_membership(per_cand):
    """The FIXED common set, per anchor, across every candidate AND the reference.

    ⚠⚠ `aggregate-moved-check-membership-first` (seventh appearance in this project).  A
    candidate that raises H2 lifts cells over the measurability margin and can also change
    which cells GATE 2 rejects, so each candidate's own `n_common` differs -- and an rms or
    median over differently-populated sets is not a ranking.  Every cross-candidate number
    in the table below is therefore computed on the INTERSECTION over all candidates, with
    the per-candidate native set printed beside it so the difference is visible, never
    silent.
    """
    fixed = {}
    for lbl in N.ANCHOR_H3:
        sets = [set(c["msub"][lbl]) for c in per_cand]
        fixed[lbl] = sorted(set.intersection(*sets)) if sets else []
    return fixed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default="analysis/reports/s74_baseline129.json")
    ap.add_argument("--jobs", type=int, default=min(8, (os.cpu_count() or 4) - 2))
    ap.add_argument("--json", default=None)
    ap.add_argument("--candidate", action="append", default=[],
                    help="'label:key=value[,key=value]' -- repeatable.  The shipped point is "
                         "always screened first and is not a candidate.")
    ap.add_argument("--no-ship-gate", action="store_true",
                    help="report even if the shipped point does not reproduce SHIP_RECORD "
                         "(for use only when the record itself is being re-derived)")
    args = ap.parse_args()

    if not N.selftest():
        print("⛔ GATE 0 FAILED -- refusing to screen candidates on an unvalidated extractor.")
        return 1

    # ---- the capture set: identical CONDITION-based rule as nd_tone_ladder --------------
    files = []
    for fn in sorted(os.listdir(N.CAPDIR)):
        if not fn.endswith(".wav"):
            continue
        if "base-od" not in fn and not fn.startswith("ref-od"):
            continue
        if "gain-n12" in fn:
            continue
        try:
            s = C.parse_capture(fn)
        except Exception:                                            # noqa: BLE001
            continue
        if s.get("blend") == 0.0 or s.get("level") == 0.0:
            continue
        files.append((fn, s))
    settings = dict(files)

    print("=" * 90)
    print("EVEN-ORDER CANDIDATE SCREEN -- the 1 kHz axis, BOTH anchors, reported SEPARATELY")
    print("=" * 90)
    print(f"  captures            : {len(files)}")
    print(f"  renderer            : {N.RENDER_BIN}  (OS {N.RENDER_OS}, --trim-latency)")
    print(f"  condition           : DERIVED per file via captures.render_args(parse_capture())")
    print()

    # ---- reference side, once -----------------------------------------------------------
    data, bad = read_reference(files, args.jobs)
    if bad:
        print(f"  ⚠ {len(bad)} capture(s) unreadable")
    contam, noisy, _, _ = N.side_gates(data, "REFERENCE (ND captures)", 1.0)

    N.gate_corr_sign()
    fb, _ = N.filter_bridge(args.report)
    c23 = float(np.median([r["g3"] - r["g2"] for r in fb]))
    c45 = float(np.median([r["g5"] - r["g4"] for r in fb]))
    mfb, _ = N.filter_bridge(args.report, which="plugin_db")
    mc23 = float(np.median([r["g3"] - r["g2"] for r in mfb]))
    mc45 = float(np.median([r["g5"] - r["g4"] for r in mfb]))
    print("=" * 90)
    print("FILTER CORRECTIONS (GATE 3) -- measured on the BLEED-FREE captures/renders")
    print("=" * 90)
    print(f"  ND    H2-H3 correction {c23:+.2f} dB      model {mc23:+.2f} dB   "
          f"⇒ net {mc23 - c23:+.2f} dB")
    print(f"  ⚠ the model correction is the SHIPPED chain's LINEAR FR, and every candidate")
    print(f"    here moves an EVEN term whose leading part is a*w^2/2, so T'(0) -- and with it")
    print(f"    the small-signal transfer -- is unchanged.  That is an argument, so it is also")
    print(f"    CHECKED below: an even-only lever must leave the ODD orders alone (H3 CONTROL).")
    print()

    nhits, _ = N.anchor_hits(data, contam, noisy, settings, c23, c45)
    nsub = {lbl: {x["file"]: x for x in nhits[lbl] if x["ok23"]} for lbl in N.ANCHOR_H3}
    for lbl in ("low", "mid"):
        print(f"  reference reaches the {lbl}-drive anchor in {len(nsub[lbl])} captures, "
              f"median H2-H3 = {np.median([x['h23c'] for x in nsub[lbl].values()]):+.2f} dB")
    print()

    # ---- candidates ---------------------------------------------------------------------
    cands = [("shipped", ())]
    for spec in args.candidate:
        label, _, kvs = spec.partition(":")
        cands.append((label, tuple(k for k in kvs.split(",") if k)))

    per_cand = []
    for label, fit in cands:
        print("=" * 90)
        print(f"CANDIDATE  {label}   fit = {list(fit) if fit else '(shipped defaults)'}")
        print("=" * 90)
        mdata, mbad = read_candidate(files, fit, args.jobs)
        if mbad:
            print(f"  ⚠ {len(mbad)} render(s) unusable: {mbad[:3]}")
        mcontam, mnoisy, worst, nnoisy = N.side_gates(mdata, f"MODEL [{label}]", 1.0)
        msub, mnonmono = anchored(mdata, mcontam, mnoisy, settings, mc23, mc45)
        per_cand.append(dict(label=label, fit=fit, mdata=mdata, msub=msub,
                             gate1_worst=worst, gate2_noisy=nnoisy, nonmono=mnonmono))

    # ---- GATE L: liveness + the discriminating controls ---------------------------------
    print("=" * 90)
    print("GATE L -- the override must REACH the binary, and only the intended lever may move")
    print("=" * 90)
    base = per_cand[0]
    live = []
    print(f"  {'candidate':<22} {'max|dH2| whole ladder':>22} {'|dH2| AT the low anchor':>25}")
    for c in per_cand[1:]:
        common = sorted(set(base["mdata"]) & set(c["mdata"]))
        dmax = 0.0
        for fn in common:
            for db in sorted(set(base["mdata"][fn]) & set(c["mdata"][fn])):
                dmax = max(dmax, abs(base["mdata"][fn][db]["hd"][2] -
                                     c["mdata"][fn][db]["hd"][2]))
        # ⚠⚠ THE DISCRIMINATING NUMBER IS THE ANCHOR ONE, NOT THE LADDER MAX, and the first
        # version of this gate printed only the ladder max while narrating an inertness
        # claim about the anchor -- a `computed-verdicts-not-narrated` violation in a gate
        # written to catch exactly that.  The two differ a lot and the difference is the
        # FINDING: the J201 knee and ceiling have several dB of H2 authority at the HOT end
        # of the ladder (so they are live levers, and a globally-inert control would prove
        # nothing) while contributing ~0 at the low anchor, which is what the small-signal
        # algebra requires (the even coefficient there is a/2, independent of s and of both
        # ceilings -- session 73).  Session 73 measured them EXACTLY inert because its
        # anchor sat at -42..-54 dBFS; this anchor reaches -11 dBFS, so it had to be
        # measured here rather than inherited.
        anch_lo = float("nan")
        fs = [f for f in c["msub"]["low"] if f in base["msub"]["low"]]
        if fs:
            anch_lo = abs(float(np.median([c["msub"]["low"][f]["hd"][2] for f in fs]))
                          - float(np.median([base["msub"]["low"][f]["hd"][2] for f in fs])))
        live.append((c["label"], dmax, anch_lo))
        print(f"  {c['label']:<22} {dmax:>19.3f} dB {anch_lo:>22.3f} dB")
    if live and max(d for _, d, _ in live) < 0.5:
        print("  ⛔ NO candidate moves H2 -- the --fit overrides are not reaching the renderer.")
        return 1
    print("  ⇒ LIVENESS is the ladder column; the CONTROL claim is the anchor column.  A lever")
    print("    that is large on the ladder and ~0 at the anchor is inert WHERE THE STATISTIC IS")
    print("    READ, which is a far sharper discriminator than a globally-dead control.")
    print()

    # ---- the fixed membership -----------------------------------------------------------
    fixed = gate_membership(per_cand)
    for lbl in ("low", "mid"):
        fixed[lbl] = [f for f in fixed[lbl] if f in nsub[lbl]]
    print("=" * 90)
    print("MEMBERSHIP -- the FIXED common set every candidate is scored on")
    print("=" * 90)
    for lbl in ("low", "mid"):
        native = [len(c["msub"][lbl]) for c in per_cand]
        print(f"  {lbl:>4}-drive anchor: reference {len(nsub[lbl])}, per-candidate "
              f"{native}, FIXED intersection {len(fixed[lbl])}")
    print("  ⚠ the fixed set is what the table below uses.  A candidate's own set differs")
    print("    because raising H2 lifts cells over the measurability margin -- scoring on")
    print("    those would compare differently-populated sets")
    print("    (`aggregate-moved-check-membership-first`).")
    print()

    # ---- the table ----------------------------------------------------------------------
    print("=" * 90)
    print("d(H2-H3) = model - ND, AT EACH ANCHOR SEPARATELY.  There is no combined column.")
    print("=" * 90)
    print(f"  {'candidate':<22} {'d(low)':>9} {'p10..p90':>17} {'d(mid)':>9} {'p10..p90':>17}"
          f" {'sel':>7}")
    rows = {}
    for c in per_cand:
        cells = {}
        for lbl in ("low", "mid"):
            fs = fixed[lbl]
            if len(fs) < 3:
                cells[lbl] = None
                continue
            d = np.array([c["msub"][lbl][f]["h23c"] - nsub[lbl][f]["h23c"] for f in fs])
            cells[lbl] = dict(n=len(fs), med=float(np.median(d)),
                              p10=float(np.percentile(d, 10)),
                              p90=float(np.percentile(d, 90)),
                              model=float(np.median([c["msub"][lbl][f]["h23c"] for f in fs])),
                              nd=float(np.median([nsub[lbl][f]["h23c"] for f in fs])))
        lo, mi = cells["low"], cells["mid"]
        # SELECTIVITY, defined against the SHIPPED point: how much low-drive movement the
        # candidate buys per dB of mid-drive movement it spends.  Mid drive is where the
        # model already sits ~11 dB above ND and ~at hardware, so movement there is a COST.
        sel = ""
        if c["label"] != "shipped" and rows.get("shipped"):
            b = rows["shipped"]
            dl = lo["med"] - b["low"]["med"] if lo and b["low"] else float("nan")
            dm = mi["med"] - b["mid"]["med"] if mi and b["mid"] else float("nan")
            sel = f"{dl / dm:6.2f}x" if abs(dm) > 0.05 else "   inf"
            cells["d_low_vs_ship"], cells["d_mid_vs_ship"] = float(dl), float(dm)
        rows[c["label"]] = cells
        f_lo = (f"{lo['med']:>+9.2f} {lo['p10']:>+7.2f}..{lo['p90']:>+7.2f}"
                if lo else f"{'--':>9} {'--':>17}")
        f_mi = (f"{mi['med']:>+9.2f} {mi['p10']:>+7.2f}..{mi['p90']:>+7.2f}"
                if mi else f"{'--':>9} {'--':>17}")
        print(f"  {c['label']:<22} {f_lo} {f_mi} {sel:>7}")
    print()
    print(f"  reference (ND) at the fixed set: low {rows['shipped']['low']['nd']:+.2f}   "
          f"mid {rows['shipped']['mid']['nd']:+.2f} dB")
    print("  ⇒ d(low) should move toward 0 (ND lies BETWEEN us and hardware there, so the")
    print("    first ~8 dB is monotone toward both); d(mid) should NOT move (the model is")
    print("    already ~at hardware there -- session 72's 94 %, 88 % against measured ND).")
    print()

    # ---- GATE B: the shipped point must reproduce the record -----------------------------
    print("=" * 90)
    print("GATE B -- the SHIPPED point must reproduce the session-79 record")
    print("=" * 90)
    okB = True
    for lbl in ("low", "mid"):
        got = rows["shipped"][lbl]["med"] if rows["shipped"][lbl] else float("nan")
        want = SHIP_RECORD[lbl]
        ok = abs(got - want) <= SHIP_TOL_DB
        okB &= ok
        print(f"  {lbl:>4}-drive d(H2-H3): got {got:+.2f}   recorded {want:+.2f}   "
              f"|d| {abs(got - want):.2f} dB   {'PASS' if ok else '⛔ FAIL'}")
    print(f"  ⚠ the recorded figures are on each side's NATIVE set; this table is on the")
    print(f"    FIXED intersection, so a small offset is expected and is bounded by the")
    print(f"    tolerance, not explained away.")
    if not okB and not args.no_ship_gate:
        print("  ⛔ REFUSING to rank candidates against a baseline that does not reproduce.")
        return 1
    print()

    # ---- per-order absolutes -------------------------------------------------------------
    print("=" * 90)
    print("PER-ORDER ABSOLUTES at each anchor (model), beside ND -- a pair statistic cancels")
    print("common-mode error exactly, so these are printed too")
    print("=" * 90)
    for lbl in ("low", "mid"):
        fs = fixed[lbl]
        if len(fs) < 3:
            continue
        print(f"  --- {lbl}-drive anchor, {len(fs)} captures ---")
        print(f"      {'candidate':<22} " + " ".join(f"{'H'+str(n):>7}" for n in N.ORDERS))
        print(f"      {'ND (reference)':<22} " +
              " ".join(f"{np.median([nsub[lbl][f]['hd'][n] for f in fs]):>+7.1f}"
                       for n in N.ORDERS))
        for c in per_cand:
            print(f"      {c['label']:<22} " +
                  " ".join(f"{np.median([c['msub'][lbl][f]['hd'][n] for f in fs]):>+7.1f}"
                           for n in N.ORDERS))
        print()

    # ---- the H3 control -------------------------------------------------------------------
    print("=" * 90)
    print("ODD-ORDER CONTROL -- an EVEN-only lever must leave the ODD orders alone")
    print("=" * 90)
    print("  ⚠⚠ IT MUST BE H5, NOT H3.  The first version of this gate scored H3 and could")
    print("  only ever return 0.00 dB: every side is ANCHORED on its own H3/H1 crossing, so")
    print("  H3 is pinned to the anchor value BY CONSTRUCTION.  A control whose answer is")
    print("  fixed by the construction of the measurement tests nothing, however reassuring")
    print("  a table of zeros looks.  H5 is odd and NOT pinned, so it can actually fail.")
    print("  If an odd order moves as much as H2, the candidate is not an even-order")
    print("  correction at all -- it is a drive/level change, and the model's linear filter")
    print("  correction (held fixed across candidates) would no longer be valid either.")
    for lbl in ("low", "mid"):
        fs = fixed[lbl]
        if len(fs) < 3:
            continue
        b = {n: np.median([per_cand[0]["msub"][lbl][f]["hd"][n] for f in fs]) for n in N.ORDERS}
        print(f"  --- {lbl}-drive ---")
        for c in per_cand[1:]:
            m = {n: np.median([c["msub"][lbl][f]["hd"][n] for f in fs]) for n in N.ORDERS}
            d2, d3, d5 = m[2] - b[2], m[3] - b[3], m[5] - b[5]
            # `ratio-statistics-need-a-denominator-guard`.  The question this control asks is
            # "does an odd order move as much as H2?", and it is only ASKABLE of a candidate
            # that moves H2 at all.  The two CTL rows are inert BY DESIGN at this anchor
            # (dH2 ~ 0.1 dB), so a ratio there divides one noise-level number by another and
            # fired the warning at 1.45 on a control that moved H5 by 0.19 dB.  The bar is set
            # well under the smallest REAL candidate (a=1.2 moves H2 by 3.3 dB) and well over
            # the controls, so it excludes only rows where the ratio is meaningless -- and the
            # raw dH5 is still printed, so nothing is hidden by the guard.
            LIVE_DH2_DB = 1.0
            live = abs(d2) >= LIVE_DH2_DB
            ratio = abs(d5) / abs(d2) if live else float("nan")
            note = ("   ⚠ an ODD order moves comparably -- NOT an even-only lever"
                    if live and ratio > 0.5 else
                    "" if live else
                    f"   (dH2 < {LIVE_DH2_DB:.1f} dB -- inert here, ratio not meaningful)")
            print(f"      {c['label']:<22} dH2 {d2:>+6.2f}   dH5 {d5:>+6.2f}   "
                  f"|dH5/dH2| {ratio:5.2f}   (dH3 {d3:>+5.2f} = pinned by the anchor)" + note)
    print()

    # ---- the cost the PAIR statistic cannot see -------------------------------------------
    print("=" * 90)
    print("H4 -- THE COST d(H2-H3) CANNOT SEE")
    print("=" * 90)
    print("  d(H2-H3) is blind to H4 by construction, and H4 is not a free ride: at the low")
    print("  anchor the model already sits ABOVE ND on H4 while sitting BELOW it on H2, so a")
    print("  lever that raises both improves one and worsens the other")
    print("  (`difference-statistics-hide-common-mode`).")
    print()
    print("  ⚠⚠ BUT THIS ROW HAS NEVER BEEN GUARDED, AND THE ANCHOR SUBSET DOES NOT GUARD IT")
    print("  (session 83).  `msub`/`nsub` select on `ok23` -- H2 AND H3 measurable -- because")
    print("  the headline statistic is the H2-H3 pair.  `ok45` is computed per hit and is")
    print("  simply never consulted here, so every H4 number printed since session 80 is a")
    print("  median over cells selected for H2/H3 reliability and NOT for H4's.  That matters")
    print("  because a floored Hn is not a measurement: the LS fit returns whatever noise")
    print("  projects onto that basis vector, bounded BELOW by roughly the cell's residual, so")
    print("  a floored value reads too HIGH.  On the MODEL side that biases (model - ND)")
    print("  UPWARD -- which is exactly the direction of the claim being made.  The support")
    print("  and the reference-guarded read are therefore printed below, and the guard is on")
    print("  the REFERENCE (`floor-guard-belongs-on-the-reference`, session 74 item 6 --")
    print("  guarding on the model selects away the cells where the model under-produces).")
    h4_support = {}
    for lbl in ("low", "mid"):
        fs = fixed[lbl]
        if len(fs) < 3:
            continue
        nd4 = np.median([nsub[lbl][f]["hd"][4] for f in fs])
        # Support, per side, on the SAME fixed set the row is scored on.
        ref_ok = [f for f in fs if nsub[lbl][f]["meas"][4]]
        ref_h2 = [f for f in fs if nsub[lbl][f]["meas"][2]]
        print(f"  --- {lbl}-drive, ND H4 = {nd4:+.1f} dB, {len(fs)} cells in the fixed set ---")
        print(f"      SUPPORT: reference H4 measurable (H4 > residual + "
              f"{N.ORDER_MARGIN_DB:.0f} dB) in {len(ref_ok)} of {len(fs)} cells; "
              f"reference H2 in {len(ref_h2)} of {len(fs)} (the control -- the headline "
              f"statistic's own order)")
        # ⚠ TWO DIFFERENT STATISTICS, AND THE FIRST VERSION OF THIS BLOCK PRINTED THEM SIDE
        # BY SIDE UNLABELLED.  `median(model) - median(ND)` (session 80's convention, kept for
        # continuity) is NOT `median(model - ND)`; the cells are PAIRED, so the second is the
        # correct one and they differ by 0.15-0.6 dB here.  Both are printed, each named.
        print(f"      {'candidate':<22} {'unpaired  med(m)-med(ND)':>26} "
              f"{'PAIRED med(m-ND)':>18} {'PAIRED, guarded':>17}")
        for c in per_cand:
            m4 = float(np.median([c["msub"][lbl][f]["hd"][4] for f in fs]))
            unpaired = m4 - nd4
            paired = float(np.median(
                [c["msub"][lbl][f]["hd"][4] - nsub[lbl][f]["hd"][4] for f in fs]))
            mdl_ok = sum(1 for f in fs if c["msub"][lbl][f]["meas"][4])
            g = (float(np.median([c["msub"][lbl][f]["hd"][4] - nsub[lbl][f]["hd"][4]
                                  for f in ref_ok])) if len(ref_ok) >= 3 else float("nan"))
            print(f"      {c['label']:<22} {unpaired:>+21.2f} dB {paired:>+15.2f} dB "
                  f"{g:>+14.2f} dB   (model H4 measurable {mdl_ok}/{len(fs)})")
            if c["label"] == "shipped":
                d4 = np.array([c["msub"][lbl][f]["hd"][4] - nsub[lbl][f]["hd"][4] for f in fs])
                h4_support[lbl] = dict(
                    n_fixed=len(fs), n_ref_meas=len(ref_ok), n_ref_meas_h2=len(ref_h2),
                    n_model_meas=int(sum(1 for f in fs if c["msub"][lbl][f]["meas"][4])),
                    unguarded_median=float(np.median(d4)),
                    spread_p10_p90=[float(np.percentile(d4, 10)),
                                    float(np.percentile(d4, 90))],
                    spread_min_max=[float(d4.min()), float(d4.max())],
                    guarded_median=(float(np.median(
                        [c["msub"][lbl][f]["hd"][4] - nsub[lbl][f]["hd"][4] for f in ref_ok]))
                        if len(ref_ok) >= 3 else None))
                print(f"      {'':<22} ⚠ per-cell d(H4) spread over the {len(fs)} cells: "
                      f"p10 {np.percentile(d4, 10):+.1f} .. p90 {np.percentile(d4, 90):+.1f}, "
                      f"full {d4.min():+.1f} .. {d4.max():+.1f} dB "
                      f"({d4.max() - d4.min():.1f} dB WIDE) -- the median is a summary of THAT")
                dropped = [f for f in fs if f not in ref_ok]
                for f in dropped:
                    dv = (c["msub"][lbl][f]["hd"][4] - nsub[lbl][f]["hd"][4])
                    print(f"      {'':<22} dropped by the guard: {f}  d(H4) {dv:+.1f} dB "
                          f"(ND H4 {nsub[lbl][f]['hd'][4]:+.1f} vs its residual "
                          f"{nsub[lbl][f]['inharm']:+.1f})")
        print()
    # The verdict on whether this row may be quoted at all -- COMPUTED, not narrated.
    for lbl, s in h4_support.items():
        if s["n_ref_meas"] < 5:
            print(f"  ⛔ {lbl}-drive: the reference's OWN H4 clears its residual in only "
                  f"{s['n_ref_meas']} of {s['n_fixed']} cells, against {s['n_ref_meas_h2']} for "
                  f"H2.  This row is NOT a measurement of H4 and must not be quoted as one; "
                  f"the H2-H3 headline is unaffected.")
        else:
            w = s["spread_min_max"][1] - s["spread_min_max"][0]
            print(f"  ⇒ {lbl}-drive: H4 IS supported -- {s['n_ref_meas']}/{s['n_fixed']} "
                  f"reference-measurable cells (H2 control {s['n_ref_meas_h2']}/{s['n_fixed']}). "
                  f"PAIRED median {s['unguarded_median']:+.2f} dB, guarded "
                  f"{s['guarded_median']:+.2f} dB.")
            print(f"     ⚠⚠ BUT the per-cell spread is {w:.1f} dB WIDE, so this median is a "
                  f"weak summary however many cells back it: dropping the "
                  f"{s['n_fixed'] - s['n_ref_meas']} unmeasurable cell(s) moves it "
                  f"{abs(s['unguarded_median'] - s['guarded_median']):.2f} dB.  Quote the")
            print(f"     TREND in `a` (robust to the guard), never the absolute level.")
    print()

    # ---- the verdict, COMPUTED -------------------------------------------------------------
    print("=" * 90)
    print("VERDICT (computed from the table, not narrated)")
    print("=" * 90)
    ship = rows["shipped"]
    best, bestscore = None, None
    for c in per_cand[1:]:
        r = rows[c["label"]]
        if not (r["low"] and r["mid"]):
            continue
        # A candidate is admissible only if it does not spend more at mid drive than it
        # buys at low drive.  Reported per anchor; NEVER summed into one score.
        gain = abs(ship["low"]["med"]) - abs(r["low"]["med"])
        cost = abs(r["mid"]["med"]) - abs(ship["mid"]["med"])
        print(f"  {c['label']:<22} low-drive |error| {abs(ship['low']['med']):.2f} -> "
              f"{abs(r['low']['med']):.2f} (gain {gain:+.2f})   "
              f"mid-drive |error| {abs(ship['mid']['med']):.2f} -> "
              f"{abs(r['mid']['med']):.2f} (cost {cost:+.2f})")
        if gain > 0 and (bestscore is None or gain - max(cost, 0.0) > bestscore):
            best, bestscore = c["label"], gain - max(cost, 0.0)
    # ⭐ Where d(low) actually CROSSES ZERO, interpolated across the swept values -- more
    # useful than "which grid point won", because the grid is mine and the crossing is the
    # data's.  Only meaningful for the single-parameter jfetSatNeg sweep.
    sweep = [(float(c["fit"][0].split("=")[1]), rows[c["label"]]["low"]["med"])
             for c in per_cand
             if len(c["fit"]) == 1 and c["fit"][0].startswith("jfetSatNeg=")
             and rows[c["label"]]["low"]]
    sweep.append((0.76054, rows["shipped"]["low"]["med"]))       # the shipped value
    sweep.sort()
    xs = [a for a, _ in sweep]
    ys = [d for _, d in sweep]
    cross = None
    for i in range(len(xs) - 1):
        if ys[i] <= 0.0 <= ys[i + 1] and ys[i + 1] > ys[i]:
            f = (0.0 - ys[i]) / (ys[i + 1] - ys[i])
            cross = xs[i] + f * (xs[i + 1] - xs[i])
            break
    if cross is not None:
        print(f"  ⭐ d(low) crosses ZERO at jfetSatNeg ~ {cross:.2f} "
              f"(swept {xs[0]:.2f}..{xs[-1]:.2f}); |d(low)| is worse on BOTH sides of it, "
              f"which is the non-degeneracy signature.")
        print(f"     ⚠ 'crosses zero' means 'equals ND', NOT 'equals hardware'.  ND lies")
        print(f"     BETWEEN us and hardware at this anchor, so this is the far edge of the")
        print(f"     move that is free against the 129-capture matrix, not the target.")
        print()
    if best is None:
        print("  ⛔ NO candidate reduces the low-drive error.  Nothing located.")
    else:
        print(f"  ⇒ best low-drive movement net of mid-drive cost: {best}")
        print(f"  ⚠ LOCATED, NOT PROPOSED.  The 129-capture matrix has not judged this, and")
        print(f"    per reference-sources.md section 1(0) the MID-drive regime must be expected")
        print(f"    to regress there while the LOW-drive regime should improve -- report BOTH.")
    print()

    if args.json:
        blob = {"ship_record": SHIP_RECORD,
                "fixed_membership": {k: v for k, v in fixed.items()},
                "h4_support": h4_support,
                "corrections": {"nd_h2h3": c23, "model_h2h3": mc23, "net": mc23 - c23},
                "candidates": {c["label"]: {"fit": list(c["fit"]),
                                            "gate1_worst_db": c["gate1_worst"],
                                            "gate2_noisy_cells": c["gate2_noisy"],
                                            "anchors": rows[c["label"]]}
                               for c in per_cand}}
        json.dump(blob, open(args.json, "w"), indent=1, default=float)
        print(f"  wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
