#!/usr/bin/env python3.11
"""GATE BR — WHERE, INSIDE THE OD 8-16.3 kHz REGION, DOES A MATRIX COST ACTUALLY LIVE?

Session 191, step 2 of the s190 prioritised action list ("run the two matrix-cost diagnostics,
specifically the OD 8-16.3 kHz per-band breakdown FIRST"). The s190 LEVEL taper moved that region's
p90 5.210 -> 5.333 dB (+0.123) and NOTHING had ever localised WHERE in the band the movement sits.
That matters for sequencing, not just for tidiness: the treble notch (item 17's live half) has its
own window at 4200-12000 Hz and its measured centres run 6150-10708 Hz, which STRADDLES the gated
region's bottom band (8127.5 Hz) and misses its top two entirely. So:

  - if the cost is concentrated at 8127.5 Hz  -> it is inside the treble notch's own territory and
    is evidence to fold INTO that investigation;
  - if it is at 12901.6 / 16255 Hz            -> it is outside, the two stay independent, and item
    17 proceeds without that shadow.

⛔ THIS IS A DIAGNOSTIC, NOT A NEW BAR. No threshold is invented here and nothing is graded; the
release gate remains the criterion. Everything printed is either an order statistic recomputed from
`release_gate`'s OWN pool (imported, never re-derived) or a membership count.

WHAT IT DOES
------------
BR0  MEMBERSHIP. Both reports are loaded through `release_gate.deltas`/`subsets`, so the graded OD
     set, the by-name exclusions and the detected reference dropouts are the gate's, not this
     tool's. The two sets are then MATCHED (intersected) and the tool REFUSES if the match loses
     more than nothing without saying so -- `aggregate-moved-check-membership-first`, which has
     fired twelve times in this project and once (s159) inside an epoch comparison exactly like
     this one, where the conditions are identical by construction and the ADMISSION rule moved.

BR1  KNOWN ANSWER. The pooled region statistics recomputed here must reproduce `release_gate`'s
     own stored cells EXACTLY (0.0e+00) on the unmatched membership. If they do not, this tool is
     measuring a different pool than the number it claims to be decomposing.

BR2  PER-BAND DECOMPOSITION. Median / p90 / mean of |delta| per band, both reports, matched rows.

BR3  ATTRIBUTION, BY SUBSTITUTION. The pooled p90 recomputed on the AFTER data with one band's
     values REVERTED to their BEFORE values. That is a counterfactual on the actual statistic and
     it changes nothing else -- same rows, same band count, same quantile position.
     ⚠ The obvious alternative, LEAVE-ONE-BAND-OUT, is printed as a control and must NOT be read as
     the attribution: dropping a band changes the population SIZE, so it moves where the 90th
     percentile falls as well as which values are there, mixing two effects. On the s187->s190
     comparison the two disagree completely (LOO names one band by a 0.3 pp margin -- a knife-edge
     verdict; substitution says the move is DISTRIBUTED over three).
     ⚠ Substitution shares do NOT sum to 100 %: an order statistic is not additive over disjoint
     sub-populations. They are read as "how much of the move does this band carry on its own", and
     the tool says so rather than normalising them into a fake decomposition.

BR4  TOP-DECILE MEMBERSHIP -- and its IDENTITY, not merely its counts. Of the values above each
     report's own p90 threshold, how many come from each band, AND how many are literally the same
     (row, band) cells in both. Equal counts are cheap; a high cell-level overlap is the statement
     that the move is the same worst cells shifting rather than a different population arriving.

BR5  ROW ATTRIBUTION. The rows that moved most in the region, with their settings, so a movement
     concentrated at one operating point cannot read as broadband.

Run:
    python3.11 analysis/hf_region_breakdown.py                       # s187 -> s190, OD, 8-16.3 kHz
    python3.11 analysis/hf_region_breakdown.py --region "100 Hz-8 kHz"
    python3.11 analysis/hf_region_breakdown.py --before X.json --after Y.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matrix_grade as MG        # noqa: E402
import release_gate as RG        # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPORTS = os.path.join(HERE, "reports")

# The two epochs the s190 cost is quoted between. Named rather than derived: this tool exists to
# decompose ONE published delta, and deriving "the newest two reports" would silently re-point it
# at a different comparison the moment anything else is rendered.
DEF_BEFORE = os.path.join(REPORTS, "s187_grunt_lf.json")
DEF_AFTER = os.path.join(REPORTS, "s190_leveltaper.json")

# GATE W's own window for `treble_notch`, and the measured centre range item 19's N4 records.
# Imported as FACTS to compare band membership against, not as a bar.
TREBLE_NOTCH_WINDOW = (4200.0, 12000.0)
TREBLE_NOTCH_MEASURED = (6150.0, 10708.0)


def p90(v):
    return float(np.percentile(v, 90)) if len(v) else float("nan")


def load_matched(before, after, region, subset, method=None):
    """-> (bands, idx, sel, rowsA, rowsB, caps, unmatched_counts).

    Both sides go through the gate's own membership resolution; the returned row dicts are
    restricted to the INTERSECTION and are keyed identically, so every later statistic is paired."""
    out = []
    for path in (before, after):
        if not os.path.exists(path):
            sys.exit(f"GATE BR: {path} not found. `analysis/reports/*.json` is gitignored -- "
                     f"re-render with comprehensive_report.py or pass --before/--after.")
        bands, idx, rows, used = RG.deltas(path, method)
        caps = MG.load(path)[1]
        drops, _sags, _gap = MG.find_dropouts(bands, caps, method)
        subs = RG.subsets(rows, drops)
        if subset not in subs:
            sys.exit(f"GATE BR: subset {subset!r} not one of {sorted(subs)}")
        out.append((bands, idx, subs[subset], caps, used))

    (bandsB, idxB, subB, capsB, usedB), (bandsA, idxA, subA, capsA, usedA) = out
    if bandsB != bandsA:
        sys.exit("GATE BR: the two reports do not share a band grid -- they cannot be differenced")
    if idxB != idxA:
        sys.exit("GATE BR: the two reports grade different bands -- membership is not comparable")
    if usedB != usedA:
        sys.exit(f"GATE BR: FR method differs ({usedB!r} vs {usedA!r}); `the instrument is part of "
                 f"the number` (s90) -- re-grade both with --method")

    shared = sorted(set(subB) & set(subA))
    if not shared:
        sys.exit("GATE BR: the two reports share no graded row (`empty-gate-must-fail`)")
    sel = RG.region_sel(bandsA, idxA, region)
    if not sel:
        sys.exit(f"GATE BR: region {region!r} selects no graded band")
    return (bandsA, idxA, sel,
            {k: subB[k][0] for k in shared}, {k: subA[k][0] for k in shared},
            capsA, (len(subB) - len(shared), len(subA) - len(shared)), usedA)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--before", default=DEF_BEFORE)
    ap.add_argument("--after", default=DEF_AFTER)
    ap.add_argument("--region", default="8-16.3 kHz")
    ap.add_argument("--subset", default="OD")
    ap.add_argument("--method", default=None)
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    print("=" * 100)
    print("GATE BR — per-band decomposition of an OD region's matrix cost")
    print("=" * 100)
    print(f"  before : {os.path.basename(a.before)}")
    print(f"  after  : {os.path.basename(a.after)}")
    print(f"  subset : {a.subset}     region: {a.region}")

    bands, idx, sel, rB, rA, caps, unmatched, method = load_matched(
        a.before, a.after, a.region, a.subset, a.method)
    fsel = [bands[idx[j]] for j in sel]
    print(f"  FR read: {method}     region bands: {', '.join(f'{f:g}' for f in fsel)}")

    # ---------------------------------------------------------------- BR0 membership
    print("\n" + "-" * 100)
    print("BR0  MEMBERSHIP — matched rows only")
    print("-" * 100)
    print(f"  graded {a.subset} rows: before {len(rB) + unmatched[0]}, "
          f"after {len(rA) + unmatched[1]}, MATCHED {len(rA)}")
    if unmatched != (0, 0):
        print(f"  ⚠ {unmatched[0]} before-only and {unmatched[1]} after-only rows are EXCLUDED "
              f"from every number below. A delta over an unmatched pool is "
              f"`aggregate-moved-check-membership-first`.")
    else:
        print("  ✅ membership is IDENTICAL — nothing dropped by the match, so the matched and "
              "pooled readings are the same population.")

    # ---------------------------------------------------------------- BR1 known answer
    print("\n" + "-" * 100)
    print("BR1  KNOWN ANSWER — reproduce release_gate's own cells from its own pool")
    print("-" * 100)
    ka_fail = False
    for lbl, path in (("before", a.before), ("after", a.after)):
        m = RG.measure(path, a.method)
        cell = m["cells"].get((a.subset, a.region))
        if cell is None:
            sys.exit(f"GATE BR: release_gate has no cell for ({a.subset}, {a.region})")
        # Recompute from the SAME pool the gate uses, on the gate's own (unmatched) membership.
        bandsX, idxX, rowsX, _u = RG.deltas(path, a.method)
        capsX = MG.load(path)[1]
        dropsX, _s, _g = MG.find_dropouts(bandsX, capsX, a.method)
        subX = RG.subsets(rowsX, dropsX)[a.subset]
        vals, _nb = RG.pool(subX, bandsX, idxX, a.region)
        for stat, mine in (("median", float(np.median(vals))), ("p90", p90(vals))):
            theirs = float(cell[stat])
            d = abs(mine - theirs)
            ok = d == 0.0
            ka_fail |= not ok
            print(f"  {lbl:6s} {stat:6s}  mine {mine:8.4f}  release_gate {theirs:8.4f}  "
                  f"|Δ| {d:.3e}  {'OK' if ok else '❌ MISMATCH'}")
    if ka_fail:
        sys.exit("GATE BR: the recomputed pool does not reproduce release_gate's own numbers -- "
                 "this tool is decomposing a different statistic than the one it names")

    # ---------------------------------------------------------------- BR2 per band
    print("\n" + "-" * 100)
    print("BR2  PER-BAND — |delta| distribution within the region, matched rows")
    print("-" * 100)
    B = np.array([rB[k] for k in sorted(rB)])   # (rows, graded bands)
    A = np.array([rA[k] for k in sorted(rA)])
    print(f"  {'band':>10s} {'n':>5s} | {'median before':>13s} {'after':>8s} {'Δ':>8s} "
          f"| {'p90 before':>10s} {'after':>8s} {'Δ':>8s} | {'mean Δ':>8s}")
    per_band = {}
    for j in sel:
        vb, va = B[:, j], A[:, j]
        rec = dict(f=bands[idx[j]], n=len(vb),
                   med_b=float(np.median(vb)), med_a=float(np.median(va)),
                   p90_b=p90(vb), p90_a=p90(va),
                   mean_b=float(np.mean(vb)), mean_a=float(np.mean(va)))
        per_band[bands[idx[j]]] = rec
        print(f"  {rec['f']:10.1f} {rec['n']:5d} | {rec['med_b']:13.3f} {rec['med_a']:8.3f} "
              f"{rec['med_a'] - rec['med_b']:+8.3f} | {rec['p90_b']:10.3f} {rec['p90_a']:8.3f} "
              f"{rec['p90_a'] - rec['p90_b']:+8.3f} | {rec['mean_a'] - rec['mean_b']:+8.3f}")

    pooled_b, pooled_a = B[:, sel].ravel(), A[:, sel].ravel()
    dp90 = p90(pooled_a) - p90(pooled_b)
    print(f"  {'POOLED':>10s} {len(pooled_b):5d} | {np.median(pooled_b):13.3f} "
          f"{np.median(pooled_a):8.3f} {np.median(pooled_a) - np.median(pooled_b):+8.3f} "
          f"| {p90(pooled_b):10.3f} {p90(pooled_a):8.3f} {dp90:+8.3f} "
          f"| {np.mean(pooled_a) - np.mean(pooled_b):+8.3f}")

    # ---------------------------------------------------------------- BR3 attribution
    print("\n" + "-" * 100)
    print("BR3  ATTRIBUTION — the pooled p90 with ONE band's values reverted to `before`")
    print("-" * 100)
    print("  Same rows, same band count, same quantile position — only the band under test moves.")
    print(f"  {'reverted':>10s} | {'p90':>8s} {'Δ remaining':>12s} {'Δ carried':>10s} "
          f"{'share':>8s} | window")
    print(f"  {'(none)':>10s} | {p90(pooled_a):8.3f} {dp90:+12.3f} {0.0:+10.3f} "
          f"{'—':>8s} |")
    sub = {}
    for j in sel:
        M = A.copy()
        M[:, j] = B[:, j]
        q = p90(M[:, sel].ravel())
        rem = q - p90(pooled_b)
        carried = dp90 - rem
        share = (carried / dp90 * 100.0) if dp90 != 0 else float("nan")
        f = bands[idx[j]]
        inside = (TREBLE_NOTCH_WINDOW[0] <= f < TREBLE_NOTCH_WINDOW[1]
                  or TREBLE_NOTCH_MEASURED[0] <= f <= TREBLE_NOTCH_MEASURED[1])
        sub[f] = dict(p90=q, remaining=rem, carried=carried, share_pct=share, in_notch=inside)
        print(f"  {f:10.1f} | {q:8.3f} {rem:+12.3f} {carried:+10.3f} {share:7.1f} % "
              f"| {'INSIDE treble_notch' if inside else 'outside'}")

    # Leave-one-out, printed as a CONTROL only — see the docstring. It answers a different question
    # (what would the region read if this band were not graded at all) and its verdict here is a
    # knife-edge, which is precisely why it must not be the attribution.
    loo = {}
    print(f"\n  [control] LEAVE-ONE-BAND-OUT — NOT the attribution (changes the population size, "
          f"so it moves the quantile position too)")
    for j in sel:
        keep = [t for t in sel if t != j]
        vb, va = B[:, keep].ravel(), A[:, keep].ravel()
        d = p90(va) - p90(vb)
        loo[bands[idx[j]]] = dict(p90_b=p90(vb), p90_a=p90(va), delta=d,
                                  retained_pct=(d / dp90 * 100.0) if dp90 else float("nan"))
        print(f"  [control] {bands[idx[j]]:10.1f} | p90 {p90(vb):7.3f} -> {p90(va):7.3f}  "
              f"Δ {d:+7.3f}  ({loo[bands[idx[j]]]['retained_pct']:6.1f} % retained)")

    # Computed verdict, not narrated. A single carrier is only named when one band carries the
    # majority AND the runner-up is clearly behind; otherwise the honest answer is DISTRIBUTED.
    carrier = None
    if dp90 == 0:
        print("\n  ⇒ NO VERDICT: the pooled Δ is exactly zero, so no band carries it")
    else:
        # ⛔ VACUITY. A non-zero pooled Δ with every band's substitution share at ~0 is not a
        # finding, it is a broken counterfactual: the delta exists, so SOMETHING must move when the
        # values that produce it are reverted. s185 shipped a sub-gate whose arms all had zero
        # intervention and it printed a confident `BAR: MET` while comparing 0 to 0.
        if max(abs(v["share_pct"]) for v in sub.values()) < 1.0:
            sys.exit(f"GATE BR3 FAIL [vacuous]: the pooled Δ is {dp90:+.4f} dB but reverting any "
                     f"single band moves it by under 1 % -- the substitution is not intervening, "
                     f"so the attribution below would be measuring nothing")
        order = sorted(sub, key=lambda f: -sub[f]["share_pct"])
        top, runner = order[0], (order[1] if len(order) > 1 else None)
        dominant = (sub[top]["share_pct"] > 50.0
                    and (runner is None or sub[top]["share_pct"] - sub[runner]["share_pct"] > 20.0))
        if dominant:
            carrier = top
            print(f"\n  ⇒ CARRIER: {top:g} Hz carries {sub[top]['share_pct']:.1f} % of the pooled "
                  f"Δ of {dp90:+.3f} dB on its own")
        else:
            print(f"\n  ⇒ DISTRIBUTED: no single band carries the pooled Δ of {dp90:+.3f} dB — "
                  f"top {top:g} Hz {sub[top]['share_pct']:.1f} %, next "
                  f"{runner:g} Hz {sub[runner]['share_pct']:.1f} %")
        carried_in = sum(v["carried"] for v in sub.values() if v["in_notch"])
        carried_out = sum(v["carried"] for v in sub.values() if not v["in_notch"])
        print(f"  ⇒ carried by bands INSIDE the treble notch's territory "
              f"({TREBLE_NOTCH_WINDOW[0]:g}-{TREBLE_NOTCH_WINDOW[1]:g} Hz window / "
              f"{TREBLE_NOTCH_MEASURED[0]:g}-{TREBLE_NOTCH_MEASURED[1]:g} Hz measured): "
              f"{carried_in:+.3f} dB;  OUTSIDE: {carried_out:+.3f} dB")
        if abs(carried_in) > abs(carried_out):
            print("  ⇒ the matrix cost is carried MOSTLY by bands inside item 17's treble-notch "
                  "territory — evidence to fold into that investigation, not a separate problem.")
        else:
            print("  ⇒ the matrix cost is carried MOSTLY by bands outside the treble notch's "
                  "territory — the two are independent, and item 17 proceeds without this shadow.")
        print("  ⚠ OVERLAP IN FREQUENCY IS NOT IDENTITY OF MECHANISM. This is a band-membership "
              "statement; nothing here measures a shared carrier.")

    # ---------------------------------------------------------------- BR4 top decile
    print("\n" + "-" * 100)
    print("BR4  TOP-DECILE MEMBERSHIP — what the pooled p90 is made of, and whether it is the "
          "same cells")
    print("-" * 100)
    cellset = {}
    for lbl, M in (("before", B), ("after", A)):
        vals = M[:, sel].ravel()
        thr = p90(vals)
        counts = {bands[idx[j]]: int(np.sum(M[:, j] > thr)) for j in sel}
        cellset[lbl] = {(i, j) for i in range(M.shape[0]) for j in sel if M[i, j] > thr}
        tot = sum(counts.values())
        cols = "  ".join(f"{f:g} Hz: {c:3d} ({c / tot * 100:4.1f} %)"
                         for f, c in sorted(counts.items()))
        print(f"  {lbl:6s} thr {thr:6.3f} dB  above: {tot:3d}   {cols}")
    inter = cellset["before"] & cellset["after"]
    union = cellset["before"] | cellset["after"]
    jac = len(inter) / len(union) if union else float("nan")
    print(f"  IDENTITY: {len(inter)} of {len(cellset['before'])} / {len(cellset['after'])} "
          f"top-decile CELLS are the same (Jaccard {jac:.3f})")
    print("  ⇒ equal per-band COUNTS alone would be cheap; the cell-level overlap is what says "
          "whether the same worst cells shifted or a different population arrived.")

    # How dense is the distribution where the threshold sits? A p90 in a dense neighbourhood moves
    # easily, which bounds how much any single dB of movement there is worth reading into.
    order_a = np.sort(pooled_a)
    k = int(0.90 * len(order_a))
    lo_i, hi_i = max(0, k - 9), min(len(order_a) - 1, k + 9)
    span = order_a[hi_i] - order_a[lo_i]
    print(f"  DENSITY at the threshold: the 19 values straddling the 90th percentile span "
          f"{span:.3f} dB (after) — a Δ of {dp90:+.3f} dB is "
          f"{abs(dp90) / span if span else float('nan'):.2f}× that local spread")

    # ---------------------------------------------------------------- BR5 rows
    print("\n" + "-" * 100)
    print(f"BR5  ROW ATTRIBUTION — the {a.top} rows that moved most in the region (mean |delta|)")
    print("-" * 100)
    keys = sorted(rA)
    movers = []
    for i, k in enumerate(keys):
        movers.append((float(np.mean(A[i, sel]) - np.mean(B[i, sel])), k))
    movers.sort(key=lambda t: -abs(t[0]))
    print(f"  {'Δ mean':>8s}  {'level':>5s} {'blend':>5s} {'drive':>5s} {'gr':>3s}  row")
    for d, (f, sw) in movers[:a.top]:
        s = caps[f]["settings"]
        print(f"  {d:+8.3f}  {s.get('level', float('nan')):5.3f} "
              f"{s.get('blend', float('nan')):5.3f} {s.get('drive', float('nan')):5.3f} "
              f"{s.get('gruntIdx', -1):3d}  {f} @ {sw}")
    n_up = sum(1 for d, _ in movers if d > 0)
    print(f"\n  {n_up} of {len(movers)} matched rows moved UP in this region "
          f"({n_up / len(movers) * 100:.1f} %); mean over rows "
          f"{np.mean([d for d, _ in movers]):+.4f} dB")

    # ---------------------------------------------------------------- BR6 the notch window
    print("\n" + "-" * 100)
    print("BR6  THE TREBLE-NOTCH WINDOW, ACROSS THE GATED REGION BOUNDARY")
    print("-" * 100)
    print("  GATE W's `treble_notch` window is 4200-12000 Hz; the release gate's region boundary "
          "cuts it")
    print("  at 8 kHz. So a movement that is ONE feature reads as two gated regions moving "
          "oppositely.")
    print("  Printed here on one axis, one band either side, so the shape is visible rather than "
          "inferred.")
    wsel = [j for j in range(len(idx))
            if TREBLE_NOTCH_WINDOW[0] * 0.9 <= bands[idx[j]] <= TREBLE_NOTCH_WINDOW[1] * 1.1]
    print(f"  {'band':>10s} {'region':>13s} | {'median before':>13s} {'after':>8s} {'Δ':>8s} "
          f"| {'mean before':>11s} {'after':>8s} {'Δ':>8s}")
    win = {}
    for j in wsel:
        f = bands[idx[j]]
        reg = next(n for n, lo, hi in RG.REGIONS if lo <= f < hi)
        vb, va = B[:, j], A[:, j]
        win[f] = dict(region=reg, med_b=float(np.median(vb)), med_a=float(np.median(va)),
                      mean_b=float(np.mean(vb)), mean_a=float(np.mean(va)))
        mark = "  <— region boundary" if f >= 8000.0 and bands[idx[j - 1]] < 8000.0 else ""
        print(f"  {f:10.1f} {reg:>13s} | {np.median(vb):13.3f} {np.median(va):8.3f} "
              f"{np.median(va) - np.median(vb):+8.3f} | {np.mean(vb):11.3f} {np.mean(va):8.3f} "
              f"{np.mean(va) - np.mean(vb):+8.3f}{mark}")
    signs = [np.sign(v["mean_a"] - v["mean_b"]) for v in win.values()]
    if len(set(signs)) > 1:
        neg = [f"{f:g}" for f, v in win.items() if v["mean_a"] < v["mean_b"]]
        pos = [f"{f:g}" for f, v in win.items() if v["mean_a"] > v["mean_b"]]
        print(f"\n  ⇒ THE SIGN CHANGES INSIDE THE WINDOW: better at {', '.join(neg)} Hz, "
              f"worse at {', '.join(pos)} Hz")
        print("  ⇒ that is the signature of a FEATURE MOVING within the band, not of a broadband "
              "level change — and it is the same mechanism GATE BH's BH1a describes for this "
              "null (an OD-branch gain change slides the |OD| = |clean| crossing).")
        print("  ⚠ SIGNATURE, NOT MEASUREMENT: this is a per-band error table, not a located "
              "centre. Use GATE W's locator (or GATE BF/BH) to measure where the null actually "
              "sat before and after.")
    else:
        print("\n  ⇒ the window moves ONE WAY throughout — no in-band sign change to explain")

    if a.json:
        blob = dict(before=os.path.basename(a.before), after=os.path.basename(a.after),
                    subset=a.subset, region=a.region, method=method,
                    n_matched=len(rA), unmatched=list(unmatched),
                    pooled=dict(p90_b=p90(pooled_b), p90_a=p90(pooled_a), delta=dp90,
                                med_b=float(np.median(pooled_b)),
                                med_a=float(np.median(pooled_a))),
                    per_band={f"{f:g}": v for f, v in per_band.items()},
                    substitution={f"{f:g}": v for f, v in sub.items()},
                    leave_one_out={f"{f:g}": v for f, v in loo.items()},
                    top_decile_jaccard=jac,
                    notch_window={f"{f:g}": v for f, v in win.items()},
                    carrier=(None if carrier is None else float(carrier)))
        with open(a.json, "w") as fh:
            json.dump(blob, fh, indent=2)
        print(f"\n  wrote {a.json}")


if __name__ == "__main__":
    main()
