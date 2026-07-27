#!/usr/bin/env python3.11
"""Aggregate grade for a comprehensive_report.py JSON — the numbers §4 of
docs/phase9-validation.md quotes, and an A-vs-B row comparison.

Per row (= one capture x one sweep level) it computes the band-RMS of
|plugin_db - pedal_db| over the graded band (25 Hz - 12.9 kHz, matching
gap_audit.py; the 16 kHz and 20 Hz bands sit in the sweep/cab noise floor), plus
the GAP #3 tilt (see od_tilt_metric.py). Deltas are already gain-matched by the
report, so these are SHAPE errors, not level errors.

Rows are split OD vs CLEAN by the capture's `base-od`/`base-clean` filename
token (ref-od.wav / ref-clean.wav special-cased), because the two halves grade
very differently and a single mean hides which one a candidate moved.

SILENT captures are excluded (max level < -60 dB on either side): the
zero-knob rows (master-0700, level-0700) are -640 dB garbage and would swamp any
aggregate — see docs/phase9-validation.md §3 on gap_audit's raw mean.

Usage:
    python3.11 analysis/matrix_grade.py reports/comprehensive_data.json
    python3.11 analysis/matrix_grade.py BASE.json CAND.json [--label-a X --label-b Y]
    python3.11 analysis/matrix_grade.py BASE.json CAND.json --rows 12   # worst/best N rows

With two reports it prints the aggregate for each plus the row-level movement
(how many rows better/worse by >0.5 dB), which is the acceptance evidence the
gap log records alongside the aggregate — an aggregate win built out of a few
big improvements and many small regressions is not the same result.
"""
import argparse
import json

GRADE_LO, GRADE_HI = 25.0, 12901.6
SILENT_DB = -60.0
MOVE_DB = 0.5


def load(path):
    d = json.load(open(path))
    return d["meta"]["bands"], {c["file"]: c for c in d["captures"]}


def band_idx(bands, lo, hi):
    return [i for i, b in enumerate(bands) if lo <= b <= hi]


def is_od(fname):
    return "base-od" in fname or fname.startswith("ref-od")


def rows_of(path):
    """-> {(file, sweep): (band_rms, tilt, is_od)} over non-silent rows."""
    bands, caps = load(path)
    GRADE = band_idx(bands, GRADE_LO, GRADE_HI)
    LOW = band_idx(bands, 20, 50)
    MID = band_idx(bands, 202, 1613)
    out = {}
    for f, c in caps.items():
        for sw, fr in c["fr"].items():
            p, q = fr["plugin_db"], fr["pedal_db"]
            if max(p) < SILENT_DB or max(q) < SILENT_DB:
                continue
            dl = [a - b for a, b in zip(p, q)]
            rms = (sum(dl[i] ** 2 for i in GRADE) / len(GRADE)) ** 0.5
            tilt = sum(dl[i] for i in LOW) / len(LOW) - sum(dl[i] for i in MID) / len(MID)
            out[(f, sw)] = (rms, tilt, is_od(f))
    return out


def aggregate(rows, label):
    od = [v for v in rows.values() if v[2]]
    cl = [v for v in rows.values() if not v[2]]
    al = list(rows.values())
    # The 16 gain-n12 OD rows are a CAPTURE defect, localised session 48 by
    # analysis/gain_n12_localise.py: their THD turnover -- which no input or
    # output gain can move -- differs from their own normal-gain twins' by up to
    # 15.6 dB, and the input pad their turnover POSITION implies is 3-9 dB, not
    # the 12.07 the harness renders them at.  So they are not -12 dB re-takes of
    # the same measurement and `--input-trim` cannot repair them.
    #
    # They are broken out, NOT dropped.  An exclusion that is not printed is the
    # session-40 trap ("exclude explicitly, with the evidence recorded, never
    # silently"), and the honest form is to show the headline aggregate AND the
    # clean read side by side so a reader can see how much rests on the split.
    n12 = [v for k, v in rows.items() if v[2] and "gain-n12" in k[0]]
    od_ok = [v for k, v in rows.items() if v[2] and "gain-n12" not in k[0]]

    def m(v, i):
        return sum(x[i] for x in v) / len(v) if v else float("nan")

    print(f"\n### {label}")
    print(f"{'subset':<22}{'rows':>6}{'band-RMS dB':>13}{'tilt dB':>10}")
    for name, v in (("OD", od), ("CLEAN", cl), ("ALL", al),
                    ("  OD ex gain-n12", od_ok), ("  OD gain-n12 [bad]", n12)):
        print(f"{name:<22}{len(v):6d}{m(v, 0):13.3f}{m(v, 1):10.2f}")
    return {"OD": m(od, 0), "CLEAN": m(cl, 0), "ALL": m(al, 0), "tilt_od": m(od, 1)}


def compare(a, b, la, lb, nrows):
    shared = sorted(set(a) & set(b))
    only_a, only_b = set(a) - set(b), set(b) - set(a)
    print(f"\n### row movement  ({lb} vs {la}),  {len(shared)} shared rows")
    if only_a or only_b:
        print(f"  ! {len(only_a)} rows only in {la}, {len(only_b)} only in {lb} (excluded)")
    moves = sorted(((b[k][0] - a[k][0], k) for k in shared), key=lambda t: t[0])
    better = [m for m in moves if m[0] < -MOVE_DB]
    worse = [m for m in moves if m[0] > MOVE_DB]
    bit_id = sum(1 for m in moves if m[0] == 0.0)
    print(f"  better by >{MOVE_DB} dB: {len(better)}    worse by >{MOVE_DB} dB: {len(worse)}"
          f"    bit-identical: {bit_id}")
    if better:
        print(f"  biggest improvement: {better[0][0]:+.2f} dB  {better[0][1][0]} {better[0][1][1]}")
    if worse:
        print(f"  worst regression:    {worse[-1][0]:+.2f} dB  {worse[-1][1][0]} {worse[-1][1][1]}")
    if nrows:
        print(f"\n  top {nrows} improvements:")
        for d, k in moves[:nrows]:
            print(f"    {d:+8.2f}  {a[k][0]:6.2f} -> {b[k][0]:6.2f}   {k[0]:<44}{k[1]}")
        if worse:
            print(f"  top {nrows} regressions:")
            for d, k in list(reversed(moves))[:nrows]:
                if d <= 0:
                    break
                print(f"    {d:+8.2f}  {a[k][0]:6.2f} -> {b[k][0]:6.2f}   {k[0]:<44}{k[1]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reports", nargs="+")
    ap.add_argument("--label-a")
    ap.add_argument("--label-b")
    ap.add_argument("--rows", type=int, default=0, help="also list the N biggest movers")
    args = ap.parse_args()

    loaded = [(p, rows_of(p)) for p in args.reports]
    labels = [args.label_a, args.label_b] + [None] * len(loaded)
    for i, (p, r) in enumerate(loaded):
        aggregate(r, labels[i] or p)
    for i in range(1, len(loaded)):
        compare(loaded[0][1], loaded[i][1],
                labels[0] or loaded[0][0], labels[i] or loaded[i][0], args.rows)


if __name__ == "__main__":
    main()
