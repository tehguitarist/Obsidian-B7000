#!/usr/bin/env python3.11
"""Aggregate grade for a comprehensive_report.py JSON — the numbers §4 of
docs/phase9-validation.md quotes, and an A-vs-B row comparison.

Per row (= one capture x one sweep level) it computes the band-RMS of
|plugin_db - pedal_db| over the graded band (25 Hz - 16.3 kHz), plus the GAP #3
tilt (see od_tilt_metric.py). Deltas are already gain-matched by the report, so
these are SHAPE errors, not level errors.

⚠ THE TOP OF THAT RANGE MOVED IN SESSION 90, 12901.6 -> 16255 Hz. The old ceiling
was justified by a comment claiming the 16 kHz band "sits in the sweep/cab noise
floor" -- there is no cab in this pedal (leftover template text) and it had never
been measured. Measured: CLEAN at 16255 Hz reads median 0.62 / p90 1.70 / max
3.14 dB, i.e. perfectly readable, and the sweep is 20 Hz - 20 kHz so the stimulus
supports it. gap_audit.py / cascade_analysis.py still carry the old 12.9 kHz
ceiling; they are separate, older instruments and their numbers are not
comparable to these.

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

GRADE_LO, GRADE_HI = 25.0, 16255.0    # session 90: was 12901.6 — see the module docstring
SILENT_DB = -60.0
MOVE_DB = 0.5


def load(path):
    d = json.load(open(path))
    return d["meta"]["bands"], {c["file"]: c for c in d["captures"]}


def band_idx(bands, lo, hi):
    return [i for i, b in enumerate(bands) if lo <= b <= hi]


def is_od(fname):
    return "base-od" in fname or fname.startswith("ref-od")


# ---- THE `gain-n12` EXCLUSION -- RETIRED, SESSION 111, ON THE USER'S DECISION -------------------
# Session 48 found that the `gain-n12` session had been recorded with the interface SEND 12.071 dB
# down while the harness rendered the model at full level, so every NONLINEAR comparison on those
# files was invalid, and their 16 OD rows were broken out of every project headline.  BOTH halves of
# the fix have since landed: `captures.render_args` emits `--input-trim` whenever `gainSessionDb` is
# non-zero (captures.py, using the MEASURED delta), and the four exposed files were re-captured
# 2026-07-29.  Session 106's GATE N (`analysis/gain_session_gate.py`) re-ran session 48's OWN
# instrument -- THD turnover, which no record or output gain can move -- and got 12.376 / 11.412 /
# 12.016 / 12.012 dB against the harness's 12.071, i.e. 4 of 4 discriminating pairs HEALED, with the
# inversion calibrated at 0 / 6 / 12.071 on known answers.  Session 48's "implied pad 3-9 dB" does
# not reproduce.
#
# ⛔ WHAT GATE N DOES NOT SHOW, stated because retiring an exclusion is exactly where an overclaim
# would go unchallenged: it certifies the CURRENT files (the defective ones were overwritten by the
# re-capture) and it certifies them on a NONLINEAR statistic.  On the absolute/linear axis GATE O5
# bounds the residual provenance offset at a 0.334 dB SPAN across bands (mean removed by the
# report's per-row gain match, tilt not), and that residue is the REFERENCE's -- our model side is a
# pure 12.0710 dB shift to 1.8e-08.  So these rows are CHEAP, not clean.
#
# MEASURED COST at s110_baseline (131 captures): OD band-RMS 2.265 -> 2.327 over n 322 -> 342.
# ⚠ That is NOT session 106's +0.020 dB / n 320 -> 336, which was measured on the s109 report:
# s110 added a re-captured `drive-1700_level-1700_grunt-boost_gain-n12` twin, so the group is 20
# rows now, not 16, and that twin is the worst of it (band-RMS 3.41-8.95).  It is also the ONLY
# healthy capture of DRIVE max x LEVEL max x GRUNT boost at the `drv_-12` rung -- both full-send
# captures of that condition are reference dropouts there (see LADDER below) -- so retiring the
# exclusion RESTORES coverage the dropout exclusion had removed.
#
# The switch survives so every pre-s111 quote stays reproducible: set it True (or pass
# `--ex-gain-n12` to matrix_grade / release_gate) to get the old membership back, byte for byte.
EXCLUDE_GAIN_N12 = False
N12_TOKEN = "gain-n12"


def is_gain_n12(fname):
    return N12_TOKEN in fname


def n12_split(rows, key_file=lambda k: k[0], is_od_of=lambda v: v[2]):
    """-> (od_all, od_ex_n12, od_n12) for a {(file, sweep): value} mapping.

    ⚠ ASSERTS the `gain-n12` group is non-empty (`empty-gate-must-fail`): a substring filter that
    silently matches nothing would make the retirement look free and the control vacuous."""
    od = {k: v for k, v in rows.items() if is_od_of(v)}
    n12 = {k: v for k, v in od.items() if is_gain_n12(key_file(k))}
    ex = {k: v for k, v in od.items() if not is_gain_n12(key_file(k))}
    if od and not n12:
        raise SystemExit(f"matrix_grade: no OD row matched {N12_TOKEN!r} -- the control subset is "
                         f"empty, so neither the exclusion nor its retirement can be checked")
    return od, ex, n12


# ---- Reference-side ladder dropouts (session 109 found the first; session 110 made it dynamic) --
# The four sweeps ARE the same sweep at -30/-18/-12/-6 dBFS, so the REFERENCE's band-median must
# rise monotonically: a compressive path compresses, it does not lose 25 dB in the middle of the
# ladder and get it back.  A middle rung sitting far below BOTH neighbours is therefore a capture /
# deconvolution dropout, not a device property, and must not vote (`defective-rows-must-not-vote`).
#
# ⭐ DETECTED, NEVER NAMED.  Session 109 found exactly one such cell and recorded it by filename.
# Session 110 re-captured that file (same rung, same ~14 dB hole) and a NEW capture of the same
# condition at a different MASTER setting turned out to have it too -- which a hardcoded (file,
# sweep) pair would have missed entirely.  So the test is a property of the LADDER and is recomputed
# per report.  ⚠ Only the twin recorded with the send 12 dB down is clean, so this looks like a
# reproducible LEVEL-dependent behaviour of the reference at DRIVE max x LEVEL max x GRUNT boost,
# not a bad take.  It is excluded here, not explained.
#
# The threshold sits in a MEASURED bimodal gap, not a guess: over the 258 interior rungs of the
# s109 baseline the worst healthy sag was -0.35 dB and the defect +11.59, an 11.94 dB gap with
# nothing between.  `check_dropout_separation` asserts the population is STILL bimodal rather than
# asserting a count -- if it ever stops being, no threshold is defensible and the caller is told.
# ⚠ A first draft of the s109 guard used "12 dB, deliberately generous" and MISSED the defect by
# 0.41 dB while printing a clean pass.  `measure-the-distribution-before-placing-a-threshold`.
LADDER = ("sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6")
DROPOUT_DB = 5.0
MIN_SEPARATION_DB = 3.0


def _median(xs):
    v = sorted(xs)
    n = len(v)
    return 0.5 * (v[(n - 1) // 2] + v[n // 2])


def find_dropouts(bands, caps, method=None):
    """-> (drops, sags, gap): reference-side ladder dropouts, computed from the ladder itself.

    `drops` is a set of (file, sweep); `sags` is every interior rung's (sag, file, sweep) sorted
    worst-first; `gap` is the separation between the worst kept rung and the mildest dropped one
    (inf when either side is empty), which is what makes the threshold defensible."""
    idx = band_idx(bands, GRADE_LO, GRADE_HI)
    sags = []
    for f, c in caps.items():
        fr = c.get("fr", {})
        if any(s not in fr for s in LADDER):
            continue
        med = {}
        for s in LADDER:
            src = fr[s]
            if method is not None and "methods" in src and method in src["methods"]:
                src = src["methods"][method]
            q = src["pedal_db"]
            med[s] = _median([q[i] for i in idx])
        for i in (1, 2):
            floor = min(med[LADDER[i - 1]], med[LADDER[i + 1]])
            sags.append((floor - med[LADDER[i]], f, LADDER[i]))
    sags.sort(reverse=True)
    drops = {(f, s) for sag, f, s in sags if sag > DROPOUT_DB}
    kept = [sag for sag, _, _ in sags if sag <= DROPOUT_DB]
    dropped = [sag for sag, _, _ in sags if sag > DROPOUT_DB]
    gap = (min(dropped) - max(kept)) if (dropped and kept) else float("inf")
    return drops, sags, gap


def check_dropout_separation(gap, drops):
    """-> None or a warning string.  A threshold is only defensible while the population is
    bimodal; if a rung ever lands NEAR the bar, say so instead of trimming a tail."""
    if drops and gap < MIN_SEPARATION_DB:
        return (f"dropout threshold {DROPOUT_DB:.1f} dB is NOT in a clear gap "
                f"(separation {gap:.2f} dB < {MIN_SEPARATION_DB:.1f}): the sag population has "
                f"stopped being bimodal, so no threshold here is defensible -- inspect the ladder "
                f"by hand rather than trusting this exclusion")
    return None


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


def aggregate(rows, label, ex_n12=None):
    """The headline aggregate.  `ex_n12` defaults to EXCLUDE_GAIN_N12 (False since session 111 --
    see the provenance block above); True restores the pre-s111 membership as a control."""
    ex_n12 = EXCLUDE_GAIN_N12 if ex_n12 is None else ex_n12
    od_all, od_ex, od_n12 = n12_split(rows)
    cl = {k: v for k, v in rows.items() if not v[2]}
    # ⭐ SESSION 111: the graded OD set is now od_all -- the `gain-n12` group is IN.  The two
    # sub-reads stay printed, always: the group is the control that says how much of the headline
    # rests on the retirement, and an exclusion (or its retirement) that is not printed is the
    # session-40 trap in either direction.
    od = od_ex if ex_n12 else od_all
    al = {k: v for k, v in rows.items() if not (ex_n12 and v[2] and is_gain_n12(k[0]))}

    def m(v, i):
        return sum(x[i] for x in v.values()) / len(v) if v else float("nan")

    tag = "[EXCLUDED, pre-s111]" if ex_n12 else "[graded, s111]"
    print(f"\n### {label}" + ("   (--ex-gain-n12: PRE-s111 MEMBERSHIP)" if ex_n12 else ""))
    print(f"{'subset':<36}{'rows':>6}{'band-RMS dB':>13}{'tilt dB':>10}")
    for name, v in (("OD", od), ("CLEAN", cl), ("ALL", al),
                    ("  OD ex gain-n12  [pre-s111 control]", od_ex),
                    (f"  OD gain-n12  {tag}", od_n12)):
        print(f"{name:<36}{len(v):6d}{m(v, 0):13.3f}{m(v, 1):10.2f}")
    return {"OD": m(od, 0), "CLEAN": m(cl, 0), "ALL": m(al, 0), "tilt_od": m(od, 1),
            "OD_ex_n12": m(od_ex, 0), "OD_n12": m(od_n12, 0),
            "n_od": len(od), "ex_n12": ex_n12}


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
    ap.add_argument("--ex-gain-n12", action="store_true",
                    help="restore the PRE-SESSION-111 membership (gain-n12 OD rows excluded), so a "
                         "pre-s111 quote can be reproduced byte for byte")
    args = ap.parse_args()

    loaded = [(p, rows_of(p)) for p in args.reports]
    labels = [args.label_a, args.label_b] + [None] * len(loaded)
    for i, (p, r) in enumerate(loaded):
        aggregate(r, labels[i] or p, ex_n12=args.ex_gain_n12 or None)
    for i in range(1, len(loaded)):
        compare(loaded[0][1], loaded[i][1],
                labels[0] or loaded[0][0], labels[i] or loaded[i][0], args.rows)


if __name__ == "__main__":
    main()
