#!/usr/bin/env python3.11
"""
matrix_harmonics.py -- per-ORDER harmonic structure across the capture matrix.

WHY THIS EXISTS (session 74).  Every harmonic instrument this project built after
session 71 scores a DIFFERENCE between adjacent orders -- `harmonic_ladder.py` and
`jfet_even_screen.py` both report H2-H3 and H4-H5.  That was the right call for its
own purpose (it cancels this chain's own linear shape, which is large and known
wrong -- session 72 item 2).  But a difference is BLIND BY CONSTRUCTION to a
COMMON-MODE error: if every order is 10 dB low, H2-H3 is perfect and the model is
badly wrong.  This tool scores the ABSOLUTE per-order error instead, over the whole
matrix, so that blind spot is covered.

It reads `comprehensive_report.py` JSONs only -- no rendering, no capture reads, no
solve, no taper, no bleed estimate.  `plugin_db`/`pedal_db` are taken as the report
computed them.

  python3.11 analysis/matrix_harmonics.py A.json B.json [C.json ...] [--labels a,b,c]

⚠⚠ THE FLOOR GUARD MUST BE ON THE REFERENCE ONLY, AND THIS IS NOT A DETAIL.
A harmonic sitting at the numerical floor carries no information, so cells have to be
excluded -- but excluding on the MODEL's value selects away exactly the cells where
the model under-produces, which is the defect under test.  Session 74 made that
mistake first: guarding on `plugin_db > floor` reported the evens as already correct
and the odds as the problem, and the corrected guard INVERTED both halves of that
reading.  Guard on `pedal_db` (the reference) and on finiteness, never on the model.
Same family as `ratio-statistics-need-a-denominator-guard`.

⚠⚠ AND THE SILENT CAPTURES MUST BE EXCLUDED -- SESSION 74 DID NOT, AND IT COST 4-7 dB.
`matrix_grade.rows_of` has dropped zero-knob captures since session 18 (the -640 dB
trap); this tool did not, so `level-0700_base-od.wav` (LEVEL = 0, no OD path at all)
contributed 47 of the 67 band values where the model's Hn sits at the extractor's
floor, and those cells alone carried **4.3-6.8 dB of the per-order "deficit"**
(H2 -9.94 -> -4.18, H3 -12.44 -> -6.14, ...).  A guard on the REFERENCE cannot catch
this: at LEVEL=0 the reference's own Hn/H1 divides one floor-level number by another
and comes out as high as -1.7 dB, so it passes the -60 dB reference floor easily.
⇒ silent rows are excluded by default (printed, never silently), and the **MEDIAN is
the headline statistic** with the mean beside it, because a mean over a distribution
with a -400 dB tail is set by how many such cells exist and by the extractor's epsilon,
not by the physics.  `--no-silence-guard` reproduces the session-74 numbers exactly.

⚠ MEMBERSHIP.  Every statistic is computed over the (file, sweep, order, band) cells
present in ALL reports with ONE shared mask, so a candidate cannot look better by
being scored on a different set (`aggregate-moved-check-membership-first`).  The
tool prints the cell count and refuses reports whose capture sets differ.

⚠ SCOPE.  `pedal_db` is the NEURAL DSP capture, not hardware -- see
`.claude/rules/reference-sources.md`.  Per §1 that gives ND FULL authority over the
ODD orders (ND and hardware agree there to the dB) and NO authority over the EVENS
(ND runs ~27 dB below hardware).  So read an even-order regression here as expected
and possibly desirable, and an odd-order regression as a real cost.  The tool prints
that split rather than one total, because one total would silently average an
authoritative column with a non-authoritative one.
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np

ORDERS = ["H2", "H3", "H4", "H5", "H6", "H7"]
EVEN = ["H2", "H4", "H6"]
ODD = ["H3", "H5", "H7"]
DEFAULT_FLOOR = -60.0
SILENT_DB = -60.0        # matrix_grade.SILENT_DB -- one definition, not a new threshold
NOTMEAS_DB = -100.0      # below this the model's Hn/H1 is the extractor's floor, not a value

# Bin edges for the drive-regime split, in dB of the REFERENCE's H3/H1 -- the coordinate
# `nd_tone_ladder.py` defines both of its anchors on (low drive = H3/H1 -42, mid = -12), so
# the outermost bins ARE those anchors' neighbourhoods and the interior ones are the region
# between them, which is where most of this matrix actually sits.  Measured on the
# BLEED-FREE subset the split is forced onto (n=130 H3 band values above the -60 dB floor):
# p25 -33.5, median -26.0, p75 -18.2, max -7.1, and only 13% at or below -42.  Edges are
# quartile-ish on THAT population so no bin is starved.
ANCHOR_BIN_EDGES = [-42.0, -34.0, -26.0, -18.0, -12.0]


def is_od(fname: str) -> bool:
    """Match matrix_grade.is_od (session 24 fix: ref-od_gain-n12 is OD, not CLEAN)."""
    return ("base-od" in fname) or fname.startswith("ref-od")


def silent_rows(report: dict) -> set:
    """(file, sweep) rows `matrix_grade.rows_of` has excluded since session 18.

    A LEVEL=0 capture has no OD path, so the model's harmonics are numerically ZERO
    while the reference's Hn/H1 divides a floor-level harmonic by a floor-level
    fundamental and returns anything at all -- as high as -1.7 dB, so a REFERENCE-side
    floor cannot catch it.  Those cells are not measurements of the model.  Judged on
    the FR block with matrix_grade's own criterion so there is ONE definition of
    "silent" in the project, not two.
    """
    out = set()
    for c in report["captures"]:
        for sw, fr in (c.get("fr") or {}).items():
            if max(fr["plugin_db"]) < SILENT_DB or max(fr["pedal_db"]) < SILENT_DB:
                out.add((c["file"], sw))
    return out


def diluted_rows(report: dict) -> set:
    """Captures where the clean BLEND bleed is NOT zero, decided from the settings.

    ⚠⚠ THIS IS THE ONE THAT MATTERS.  Hn/H1 is measured at the OUTPUT, and the clean
    bleed adds FUNDAMENTAL and no harmonics, so it lowers Hn/H1 -- on both sides, but
    by DIFFERENT amounts whenever the model's OD-vs-clean balance is wrong, which is
    exactly A3.  So a mixed-BLEND harmonic statistic reports A3 as a distortion error.
    Sessions 59/60 established the bleed is EXACTLY zero at LEVEL max AND BLEND max
    (the LEVEL wiper shorts to the OD source), so that is the only condition at which
    Hn/H1 is a clean statement about the nonlinearity.

    Measured (session 75): pooled over all BLEND positions the per-order deficit reads
    -1.1 .. -3.7 dB; on the bleed-free subset it is **+2.6 / -0.5 / +3.2 / -0.7 / +3.4
    / +0.3 dB**, i.e. there is no deficit at all.  Same mechanism as session 60 item 7
    (`dilution-fakes-a-resonance`).
    """
    out = set()
    for c in report["captures"]:
        s = c.get("settings") or {}
        if not (s.get("blend") == 1.0 and s.get("level") == 1.0):
            for sw in (c.get("harmonics") or {}):
                out.add((c["file"], sw))
    return out


def no_od_path_rows(report: dict) -> set:
    """Captures whose OD path is out of circuit, decided from the KNOB SETTINGS.

    BLEND = 0 is 100 % clean: not silent (so `silent_rows` cannot see it) but the OD
    path contributes nothing, so the model's Hn is numerically zero and the reference's
    Hn/H1 is a ratio of two floor-level numbers.  Measured: those 14 band values carry
    a MEDIAN "deficit" of -119 dB.  LEVEL = 0 is included for the same reason and as a
    belt-and-braces duplicate of `silent_rows`.

    ⚠ This is an exclusion on the CONDITION, decidable before any number is read -- NOT
    on the measured value, which is the session-74 item-6 mistake.
    """
    out = set()
    for c in report["captures"]:
        s = c.get("settings") or {}
        if s.get("blend") == 0.0 or s.get("level") == 0.0:
            for sw in (c.get("harmonics") or {}):
                out.add((c["file"], sw))
    return out


def cells(report: dict, skip_gain_n12: bool = True, exclude: set | None = None) -> dict:
    exclude = exclude or set()
    out = {}
    for c in report["captures"]:
        f = c["file"]
        if not is_od(f):
            continue
        if skip_gain_n12 and "gain-n12" in f:
            continue
        for sw, rec in (c.get("harmonics") or {}).items():
            if (f, sw) in exclude:
                continue
            for o in ORDERS:
                if o not in rec:
                    continue
                out[(f, sw, o)] = (
                    np.asarray(rec[o]["plugin_db"], dtype=float),
                    np.asarray(rec[o]["pedal_db"], dtype=float),
                )
    return out


def build_masks(C: dict, keys, ref_label: str, floor: float) -> dict:
    """ONE mask per cell, shared by every candidate.  Reference-side floor only."""
    masks = {}
    for k in keys:
        pe = C[ref_label][k][1]
        m = np.isfinite(pe) & (pe > floor)
        for lab in C:
            m = m & np.isfinite(C[lab][k][0])
        masks[k] = m
    return masks


def per_order(C, masks, keys, label, order, reducer):
    """Reduce WITHIN each cell, then mean ACROSS cells.  This is the session-74
    statistic and is kept so `--no-silence-guard` reproduces that record exactly.
    ⚠ It is NOT robust: one degenerate CELL survives the inner reducer intact and
    then enters the outer mean at full weight (selftest GATE 4)."""
    vals = []
    for k in keys:
        if k[2] != order:
            continue
        m = masks[k]
        if not m.any():
            continue
        pl, pe = C[label][k]
        vals.append(reducer(pl[m] - pe[m]))
    return float(np.mean(vals)) if vals else float("nan")


def pooled(C, masks, keys, label, order, reducer):
    """Reduce over ALL surviving band values at once.  Required for the median to
    actually be robust -- a per-cell median averaged across cells is not."""
    vals = []
    for k in keys:
        if k[2] != order:
            continue
        m = masks[k]
        if not m.any():
            continue
        pl, pe = C[label][k]
        vals.extend(list(pl[m] - pe[m]))
    return float(reducer(np.asarray(vals))) if vals else float("nan")


def selftest() -> bool:
    """Two properties the conclusions rest on, both checked against a known answer."""
    ok = True
    rng = np.random.default_rng(0)
    base = {}
    for i in range(12):
        for o in ORDERS:
            pe = rng.uniform(-55, -10, size=5)
            base[(f"f{i}_base-od.wav", "sweep_drv_-12", o)] = (pe.copy(), pe.copy())
    C = {"ref": base}
    # (1) identity: a report compared with itself must give exactly zero.
    keys = sorted(base)
    masks = build_masks(C, keys, "ref", DEFAULT_FLOOR)
    worst = max(abs(per_order(C, masks, keys, "ref", o, np.mean)) for o in ORDERS)
    print(f"  GATE 1 identity (self vs self)            worst |mean| = {worst:.3e}   "
          f"{'PASS' if worst < 1e-12 else 'FAIL'}")
    ok &= worst < 1e-12

    # (2) a KNOWN uniform common-mode offset must be recovered exactly -- this is the
    #     quantity every difference-based instrument cancels, so it is the one that
    #     matters most here.
    OFF = -7.5
    shifted = {k: (v[0] + OFF, v[1]) for k, v in base.items()}
    C2 = {"ref": base, "cand": shifted}
    masks2 = build_masks(C2, keys, "ref", DEFAULT_FLOOR)
    errs = [per_order(C2, masks2, keys, "cand", o, np.mean) - OFF for o in ORDERS]
    worst2 = max(abs(e) for e in errs)
    print(f"  GATE 2 common-mode offset ({OFF:+.1f} dB) recovered to {worst2:.3e}   "
          f"{'PASS' if worst2 < 1e-12 else 'FAIL'}")
    ok &= worst2 < 1e-12

    # (3) LIVENESS of the guard: show the model-side guard really does bias, so the
    #     docstring warning is demonstrated rather than asserted.
    sunk = {}
    for k, (pl, pe) in base.items():
        pl2 = pl.copy()
        pl2[:2] -= 40.0          # two cells where the model badly under-produces
        sunk[k] = (pl2, pe)
    C3 = {"ref": base, "cand": sunk}
    keys3 = sorted(sunk)
    m_ref = build_masks(C3, keys3, "ref", DEFAULT_FLOOR)
    true_err = np.mean([per_order(C3, m_ref, keys3, "cand", o, np.mean) for o in ORDERS])
    # the WRONG guard: additionally require the model above the floor
    m_bad = {}
    for k in keys3:
        pl, pe = sunk[k]
        m_bad[k] = m_ref[k] & (pl > DEFAULT_FLOOR)
    bad_err = np.mean([per_order(C3, m_bad, keys3, "cand", o, np.mean) for o in ORDERS])
    print(f"  GATE 3 model-side guard bias: true {true_err:+.2f} dB vs model-guarded "
          f"{bad_err:+.2f} dB  (understates by {abs(true_err - bad_err):.2f})   "
          f"{'PASS' if abs(true_err - bad_err) > 1.0 else 'FAIL'}")
    ok &= abs(true_err - bad_err) > 1.0

    # (4) the session-75 defect, DEMONSTRATED: one degenerate capture whose model Hn
    #     sits at the extractor floor moves the MEAN by several dB and the MEDIAN by
    #     ~nothing.  This is why the median is the headline and why silent rows are
    #     excluded by the same criterion matrix_grade has used since session 18.
    DEG = ("level-0700_base-od.wav", "sweep_drv_-12")
    cand = {k: (v[0] - 3.0, v[1].copy()) for k, v in base.items()}   # a real -3 dB deficit
    for o in ORDERS:                     # plus ONE degenerate capture, all orders
        pe = rng.uniform(-40, -5, size=5)
        cand[(DEG[0], DEG[1], o)] = (np.full(5, -400.0), pe)
    C4 = {"cand": cand}
    k_all = sorted(cand)
    k_ok = [k for k in k_all if (k[0], k[1]) != DEG]
    m_all = build_masks(C4, k_all, "cand", DEFAULT_FLOOR)
    m_ok = build_masks(C4, k_ok, "cand", DEFAULT_FLOOR)
    mean_in = np.mean([per_order(C4, m_all, k_all, "cand", o, np.mean) for o in ORDERS])
    mean_ex = np.mean([per_order(C4, m_ok, k_ok, "cand", o, np.mean) for o in ORDERS])
    med_in = np.mean([pooled(C4, m_all, k_all, "cand", o, np.median) for o in ORDERS])
    med_ex = np.mean([pooled(C4, m_ok, k_ok, "cand", o, np.median) for o in ORDERS])
    shift_mean, shift_med = abs(mean_in - mean_ex), abs(med_in - med_ex)
    print(f"  GATE 4 one silent capture moves the MEAN {shift_mean:.2f} dB "
          f"({mean_in:+.2f} -> {mean_ex:+.2f}) and the MEDIAN {shift_med:.2f} dB "
          f"({med_in:+.2f} -> {med_ex:+.2f})   "
          f"{'PASS' if shift_mean > 10.0 * max(shift_med, 1e-3) else 'FAIL'}")
    ok &= shift_mean > 10.0 * max(shift_med, 1e-3)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("reports", nargs="*")
    ap.add_argument("--labels", default=None, help="comma-separated, defaults to filenames")
    ap.add_argument("--floor", type=float, default=DEFAULT_FLOOR,
                    help="reference-side floor in dB (default -60)")
    ap.add_argument("--json", default=None)
    ap.add_argument("--bleed-free", action="store_true",
                    help="score ONLY the LEVEL=max/BLEND=max cells, where the clean bleed "
                         "is exactly zero -- the only condition at which Hn/H1 is a "
                         "statement about the nonlinearity rather than about A3")
    ap.add_argument("--no-silence-guard", action="store_true",
                    help="keep zero-knob captures in (reproduces the session-74 numbers; "
                         "NOT a valid measurement -- see the docstring)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        print("SELFTEST")
        ok = selftest()
        print("  ->", "PASS" if ok else "FAIL")
        return 0 if ok else 1

    if len(args.reports) < 2:
        ap.error("need at least two reports (the first is the reference/baseline)")

    labels = (args.labels.split(",") if args.labels
              else [r.split("/")[-1].replace(".json", "") for r in args.reports])
    if len(labels) != len(args.reports):
        ap.error("--labels count must match reports")

    D = {lab: json.load(open(p)) for lab, p in zip(labels, args.reports)}
    ncap = {lab: d["meta"]["num_captures"] for lab, d in D.items()}
    ovr = {lab: d["meta"]["fit_overrides"] for lab, d in D.items()}
    if len(set(ncap.values())) != 1:
        print("⛔ CAPTURE-SET MISMATCH -- refusing to compare:", ncap)
        print("   Re-render the baseline at the same capture set "
              "(`aggregate-moved-check-membership-first`).")
        return 2

    # -- silent-row exclusion, UNIONed so every report is scored on one membership ---
    sil = set()
    if not args.no_silence_guard:
        for d in D.values():
            sil |= silent_rows(d) | no_od_path_rows(d)
    if args.bleed_free:
        for d in D.values():
            sil |= diluted_rows(d)
    C = {lab: cells(d, exclude=sil) for lab, d in D.items()}
    keys = sorted(set.intersection(*[set(v) for v in C.values()]))
    ref = labels[0]
    masks = build_masks(C, keys, ref, args.floor)
    ncells = sum(int(masks[k].sum()) for k in keys)

    print("=" * 92)
    print("PER-ORDER HARMONIC STRUCTURE vs the capture matrix")
    print("=" * 92)
    for lab in labels:
        print(f"  {lab:>22} : {ncap[lab]} captures, overrides {ovr[lab]}")
    print(f"  reference (row 0)      : {ref}")
    print(f"  cells                  : {len(keys)} (file,sweep,order) -> {ncells} band values "
          f"| reference floor {args.floor:+.0f} dB")
    if args.no_silence_guard:
        print("  ⚠⚠ SILENCE GUARD OFF -- zero-knob captures are IN. This reproduces the")
        print("     session-74 numbers and is NOT a valid measurement of the model (docstring).")
    else:
        drop = sorted({f for f, _ in sil if is_od(f) and "gain-n12" not in f})
        nrow = sum(1 for f, _ in sil if is_od(f) and "gain-n12" not in f)
        if args.bleed_free:
            print(f"  ⭐ BLEED-FREE ONLY      : {len(keys)} cells at LEVEL=max/BLEND=max, "
                  f"where the clean bleed is exactly ZERO")
        else:
            print(f"  no-OD-path rows dropped: {nrow} (file,sweep) OD rows, "
                  f"{len(drop)} file(s) -- LEVEL=0 / BLEND=0, or FR below "
                  f"SILENT_DB {SILENT_DB:+.0f} dB")
            for f in drop:
                print(f"                           {f}")
            print("  ⚠ mixed BLEND/LEVEL: Hn/H1 is DILUTED by the clean bleed, so this "
                  "read carries A3.")
            print("    Use --bleed-free for a statement about the nonlinearity alone.")
    nm = sum(int((C[ref][k][0][masks[k]] < NOTMEAS_DB).sum()) for k in keys)
    print(f"  model Hn below {NOTMEAS_DB:+.0f} dB   : {nm} of {ncells} band values in `{ref}` "
          f"(extractor floor, not a value -> read the MEDIAN)")
    print("  ⚠ `pedal_db` is the NEURAL DSP capture. Per reference-sources.md §1 the ODD")
    print("    orders are authoritative (ND == hardware) and the EVENS are NOT (ND runs")
    print("    ~27 dB below hardware), so the two groups are reported separately.")
    print()

    hdr = f"{'order':>6} " + "".join(f"{lab:>10}" for lab in labels) + "   parity"
    print("SIGNED MEDIAN over pooled band values, dB   -- HEADLINE; negative = model LOW")
    print(hdr)
    print("-" * len(hdr))
    med = {}
    for o in ORDERS:
        med[o] = [pooled(C, masks, keys, lab, o, np.median) for lab in labels]
        print(f"{o:>6} " + "".join(f"{v:>+10.2f}" for v in med[o]) +
              f"   {'EVEN' if o in EVEN else 'odd'}")
    print()
    print("SIGNED mean (plugin - pedal), dB   -- tail-sensitive, read beside the median")
    print(hdr)
    print("-" * len(hdr))
    signed = {}
    for o in ORDERS:
        signed[o] = [per_order(C, masks, keys, lab, o, np.mean) for lab in labels]
        print(f"{o:>6} " + "".join(f"{v:>+10.2f}" for v in signed[o]) +
              f"   {'EVEN' if o in EVEN else 'odd'}")
    print()
    print("mean |error|, dB")
    print(hdr)
    print("-" * len(hdr))
    absd = {}
    for o in ORDERS:
        absd[o] = [per_order(C, masks, keys, lab, o, lambda e: np.abs(e).mean()) for lab in labels]
        print(f"{o:>6} " + "".join(f"{v:>10.2f}" for v in absd[o]) +
              f"   {'EVEN' if o in EVEN else 'odd'}")
    print()
    groups = {}
    for nm, grp in (("EVEN (not authoritative)", EVEN), ("odd  (AUTHORITATIVE)", ODD),
                    ("ALL  (mixed -- see ⚠)", ORDERS)):
        row = [float(np.mean([absd[o][i] for o in grp])) for i in range(len(labels))]
        groups[nm] = row
        d = row[0]
        print(f"  {nm:>24} mean|e|: " + "".join(f"{v:>10.2f}" for v in row) +
              "   Δ " + " ".join(f"{v - d:+.2f}" for v in row[1:]))
    print()

    # -- IS THE RANKING REAL?  The cell-level sd is ~11 dB, so an UNPAIRED reading of a
    #    0.3-1.5 dB mean|e| difference would be noise.  The candidates share cells, so
    #    the right test is paired -- printed unconditionally, because a check you have
    #    to remember to run is a check that will not be run.
    print("PAIRED bootstrap of Δmean|e| vs the reference (10k resamples over cells)")
    print(f"{'group':>6} {'cand':>10} {'mean|e|':>9} {'Δ':>8}   95% CI of Δ")
    pairs = {}
    for gname, grp in (("EVEN", EVEN), ("odd", ODD), ("ALL", ORDERS)):
        per = {lab: [] for lab in labels}
        for k in keys:
            if k[2] not in grp:
                continue
            m = masks[k]
            if not m.any():
                continue
            pe = C[ref][k][1]
            for lab in labels:
                per[lab].append(float(np.abs(C[lab][k][0][m] - pe[m]).mean()))
        base = np.asarray(per[ref])
        rng = np.random.default_rng(0)
        idx = rng.integers(0, len(base), size=(10000, len(base)))
        for lab in labels:
            dif = np.asarray(per[lab]) - base
            bs = dif[idx].mean(axis=1)
            lo, hi = (float(x) for x in np.percentile(bs, [2.5, 97.5]))
            sig = "" if lo <= 0.0 <= hi else "  SIGNIFICANT"
            pairs[f"{gname}/{lab}"] = {"mean_abs": float(np.asarray(per[lab]).mean()),
                                       "delta": float(dif.mean()), "ci": [lo, hi],
                                       "significant": bool(sig)}
            print(f"{gname:>6} {lab:>10} {np.asarray(per[lab]).mean():>9.2f} "
                  f"{dif.mean():>+8.2f}   [{lo:>+7.2f}, {hi:>+7.2f}]{sig}")
        print()

    # -- DRIVE-REGIME SPLIT -------------------------------------------------------
    # Session 79 measured d(H2-H3) = model - ND as +10.94 dB at the mid-drive anchor and
    # -7.93 dB at the low-drive one -- OPPOSITE SIGNS -- and showed the pooled figure
    # (-2.9 dB) cancels ~7.9 dB of real error and reads as "we are nearly on ND".  So a
    # single matrix total CANNOT judge an even-order candidate, and every total printed
    # above this line is subject to that caveat.
    #
    # The split coordinate is the REFERENCE's OWN H3/H1, which is exactly the quantity
    # both anchors are defined on, so the matrix is read on the same axis as the screen
    # rather than on a drive-knob proxy.  It is candidate-independent BY CONSTRUCTION --
    # `pedal_db` is the capture side and no `--fit` can move it -- which is asserted
    # below rather than assumed (`floor-guard-belongs-on-the-reference`: a bin edge that
    # moved with the candidate would be self-selecting in exactly the same way).
    #
    # ⚠⚠ AND IT IS FORCED BLEED-FREE, whatever mode the rest of the table is in.  The
    # anchors are DEFINED on bleed-free renders (nd_tone_ladder runs at BLEND=LEVEL=max),
    # and the clean bleed adds fundamental and no harmonics, so it pushes every Hn/H1
    # DOWN: measured on this matrix the reference's H3/H1 has median -34.8 dB over the
    # mixed set against -26.0 dB bleed-free, an 8.8 dB shift.  Binned on the mixed set a
    # genuinely hot cell can therefore land in a "low-drive" bin purely because A3
    # diluted it -- i.e. the bin coordinate would be contaminated by the very quantity
    # this statistic exists to avoid.  Restricting here (rather than requiring the user
    # to pass --bleed-free) keeps the split on the anchors' axis by construction.
    dil = set()
    for d in D.values():
        dil |= diluted_rows(d)
    bkeys = [k for k in keys if (k[0], k[1]) not in dil]
    print("DRIVE-REGIME SPLIT -- binned on the REFERENCE's own H3/H1 (the anchors' own axis)")
    print(f"  BLEED-FREE subset only: {len(bkeys)} of {len(keys)} cells "
          f"(LEVEL=max AND BLEND=max) -- see the comment in-file for why this is forced")
    h3ref = {}
    for k in bkeys:
        if k[2] != "H3":
            continue
        for lab in labels:                      # the gate: capture side must not move
            if not np.allclose(C[lab][k][1], C[ref][k][1], equal_nan=True):
                print(f"  ⛔ pedal_db differs between `{lab}` and `{ref}` at {k} -- the bin "
                      f"edges would move with the candidate.  Refusing to split.")
                return 3
        h3ref[(k[0], k[1])] = C[ref][k][1]
    nbin = {}
    byanchor = {}
    for i, (lo, hi) in enumerate(zip([-1e9] + ANCHOR_BIN_EDGES, ANCHOR_BIN_EDGES + [1e9])):
        sel = {}                                # (key -> boolean mask) within this bin
        tot = 0
        for k in bkeys:
            h3 = h3ref.get((k[0], k[1]))
            if h3 is None:
                continue
            m = masks[k] & np.isfinite(h3) & (h3 > lo) & (h3 <= hi)
            if m.any():
                sel[k] = m
                if k[2] == "H2":
                    tot += int(m.sum())
        name = (f"H3/H1 <= {hi:+.0f}" if i == 0 else
                f"H3/H1 >  {lo:+.0f}" if hi > 1e8 else f"{lo:+.0f} .. {hi:+.0f}")
        nbin[name] = tot
        if not sel:
            continue
        row, nper = {}, {}
        for o in ORDERS:
            # ⚠⚠ PER-ORDER SUPPORT, PRINTED ON EVERY ROW (session 83).  The bin header counts
            # H2 band values ONLY, and session 82 found by throwaway probe that the orders
            # are NOT equally populated -- in the LOW bin H2 has 22 and H4 has FIVE, so an
            # H4 row read as if it had the header's n is over-trusted by 4x.  That is
            # `check-n-before-reading-a-trend`, and the fix belongs in the tool rather than
            # in a session's prose, because the prose is what goes stale.
            nper[o] = int(sum(int(sel[k].sum()) for k in sel if k[2] == o))
            for lab in labels:
                v = [C[lab][k][0][sel[k]] - C[lab][k][1][sel[k]]
                     for k in sel if k[2] == o]
                row[(o, lab)] = (float(np.median(np.concatenate(v))) if v else float("nan"))
        anch = ("  <- LOW-drive anchor" if i == 0 else
                "  <- MID-drive anchor" if hi > 1e8 else "")
        print(f"  --- {name} dB, {tot} H2 band values{anch} ---")
        print(f"    {'order':>6} {'n':>5} " + "".join(f"{lab:>10}" for lab in labels))
        for o in ORDERS:
            flag = "   ⚠ THIN" if nper[o] < 10 else ""
            print(f"    {o:>6} {nper[o]:>5} "
                  + "".join(f"{row[(o, lab)]:>+10.2f}" for lab in labels) + flag)
        thin = [o for o in ORDERS if nper[o] < 10]
        if thin:
            print(f"    ⚠ {', '.join(thin)} rest on <10 band values in this bin -- the header's "
                  f"{tot} is the H2 count and does NOT apply to them.")
        byanchor[name] = {"n_h2_band_values": tot,
                          "n_per_order": nper,
                          "per_order": {o: {lab: row[(o, lab)] for lab in labels}
                                        for o in ORDERS}}
        d23 = {lab: row[("H2", lab)] - row[("H3", lab)] for lab in labels}
        byanchor[name]["H2_minus_H3"] = d23
        print(f"    {'H2-H3':>6} " + "".join(f"{d23[lab]:>+10.2f}" for lab in labels) +
              "   <- the session-79 statistic")

        # ⚠⚠ THE TABLE ABOVE IS A TABLE OF LEVELS, AND DIFFERENCING TWO OF ITS COLUMNS
        # BY EYE IS NOT THE PAIRED STATISTIC.  Session 84 nearly published -5.46 dB for
        # the identity candidate's H3 cost by doing exactly that; the cells are PAIRED
        # (one shared mask), so the correct figure is median(cand - other) = -1.45 dB,
        # 4 dB smaller.  Session 83 fixed this same class one level down in
        # `even_low_screen.py` (it printed median(m) - median(ND) beside median(m - ND)
        # unlabelled); the trap survived here because this table has no paired column at
        # all.  So: print the paired median vs the reference, and COMPUTE the worst
        # disagreement with the difference-of-medians so the warning cannot go stale.
        paired, worst_gap, worst_at = {}, 0.0, None
        for o in ORDERS:
            for lab in labels:
                dv = [(C[lab][k][0][sel[k]] - C[lab][k][1][sel[k]])
                      - (C[ref][k][0][sel[k]] - C[ref][k][1][sel[k]])
                      for k in sel if k[2] == o]
                pm = float(np.median(np.concatenate(dv))) if dv else float("nan")
                paired[(o, lab)] = pm
                naive = row[(o, lab)] - row[(o, ref)]
                if np.isfinite(pm) and np.isfinite(naive) and abs(naive - pm) > worst_gap:
                    worst_gap, worst_at = abs(naive - pm), (o, lab)
        byanchor[name]["paired_vs_ref"] = {o: {lab: paired[(o, lab)] for lab in labels}
                                           for o in ORDERS}
        print(f"    PAIRED median of (cand - {ref}) per cell -- the correct statistic for "
              f"comparing candidates:")
        for o in ORDERS:
            flag = "   ⚠ THIN" if nper[o] < 10 else ""
            print(f"    {o:>6} {nper[o]:>5} "
                  + "".join(f"{paired[(o, lab)]:>+10.2f}" for lab in labels) + flag)
        if worst_at is not None and worst_gap > 0.5:
            print(f"    ⚠ differencing the LEVELS table by eye disagrees with the paired "
                  f"statistic by up to {worst_gap:.2f} dB (worst: {worst_at[0]} "
                  f"{worst_at[1]}).  Quote the PAIRED row.")
    print("  ⚠ MOST OF THE MATRIX LIES BETWEEN THE TWO ANCHORS, so this is a continuum,")
    print("    not a binary split -- and d(H2-H3) changes SIGN somewhere inside it.  Read")
    print("    the trend across bins; do not collapse it to one number.")
    print()

    # -- WHAT THE REFERENCE ITSELF DOES -------------------------------------------
    # Sessions 72-74 compared this model against a third-party CHART's ND column and
    # never measured ND's own parity off the captures, which ARE the ND reference.
    print("THE REFERENCE'S OWN STRUCTURE (median Hn/H1, dB) -- ND measured, not the chart")
    print(f"{'sweep':>16} " + "".join(f"{o:>8}" for o in ORDERS) + f"{'H2-H3':>9}{'H4-H5':>8}")
    sweeps = sorted({k[1] for k in keys})
    refstruct = {}
    for sw in sweeps:
        row = {}
        for o in ORDERS:
            v = [C[ref][k][1][masks[k]] for k in keys if k[1] == sw and k[2] == o and masks[k].any()]
            row[o] = float(np.median(np.concatenate(v))) if v else float("nan")
        refstruct[sw] = row
        print(f"{sw:>16} " + "".join(f"{row[o]:>+8.1f}" for o in ORDERS) +
              f"{row['H2'] - row['H3']:>+9.1f}{row['H4'] - row['H5']:>+8.1f}")
    # ⚠⚠ THIS BLOCK USED TO PRINT A HARDCODED CLAIM AND THE CLAIM WAS FALSE (session 78).
    # It said "nothing in this matrix is hotter than H3 ~ -35 dB, so the matrix cannot speak
    # to that condition", and session 75 section 5 wrote the same conclusion off a per-sweep
    # MEDIAN ("never above ~ -25 dB").  Both are medians; the question -- does any condition
    # reach the chart's -12 dB? -- is about the MAXIMUM, and the maximum is far hotter.
    # Session 78 measured -7.1 dB on these very swept anchors and -2.5 dB on the 1 kHz tone
    # ladder, with 153 clean tone cells at or above -12 dB.  The number is now COMPUTED and
    # the verdict follows from it (`computed-verdicts-not-narrated`,
    # `split-the-aggregate-check-reachability`).
    h3max, h3max_where = -1e9, None
    for k in keys:
        if k[2] != "H3" or not masks[k].any():
            continue
        v = C[ref][k][1][masks[k]]
        if v.max() > h3max:
            h3max, h3max_where = float(v.max()), (k[0], k[1])
    chart_mid_h3 = -12.0
    nhot = sum(int((C[ref][k][1][masks[k]] >= chart_mid_h3).sum())
               for k in keys if k[2] == "H3" and masks[k].any())
    med_hot = max(refstruct[sw]["H3"] for sw in sweeps)
    print(f"  the chart's ND column has H3 = {chart_mid_h3:+.0f} dB at 'mid drive'.  Measured on")
    print(f"  these anchors: MAX H3/H1 = {h3max:+.1f} dB ({h3max_where[0]} / {h3max_where[1]}), "
          f"hottest per-sweep MEDIAN {med_hot:+.1f} dB,")
    print(f"  and {nhot} band value(s) sit at or above {chart_mid_h3:+.0f} dB.")
    if nhot > 0:
        print(f"  ⇒ that operating point IS present in the matrix -- do NOT repeat the retired")
        print(f"    claim that it is not.  What the SWEPT anchors cannot do is match the chart's")
        print(f"    CONVENTION: they sample 100/200/400 Hz, so a 100 Hz anchor's H3 lands at")
        print(f"    300 Hz beside ND's own ~320 Hz notch, and the bridge to the chart's 800 Hz")
        print(f"    tone is -9..-24 dB and capture-dependent.  Use `nd_tone_ladder.py` (the 1 kHz")
        print(f"    `lvl_` ladder, pair correction -0.02 dB) for any chart comparison.")
    else:
        print(f"  ⇒ not reached on these anchors at this floor/membership.")
    print()

    # -- the decomposition a difference-based screen cannot show -------------------
    print("WHERE d(H2-H3) COMES FROM  (the statistic harmonic_ladder/jfet_even_screen score)")
    print(f"{'cand':>10} {'d(H2)':>8} {'d(H3)':>8} {'d(H2-H3)':>10} {'from H3 sag':>13}  stat")
    decomp = {}
    for stat_name, src in (("median", med), ("mean", signed)):
        base_h = {o: src[o][0] for o in ("H2", "H3")}
        for i, lab in enumerate(labels):
            d2 = src["H2"][i] - base_h["H2"]
            d3 = src["H3"][i] - base_h["H3"]
            tot = d2 - d3
            share = (-d3 / tot * 100.0) if abs(tot) > 1e-9 else 0.0
            decomp[f"{lab}/{stat_name}"] = {"d_H2": d2, "d_H3": d3, "d_H2_minus_H3": tot,
                                            "share_from_H3_sag_pct": share}
            print(f"{lab:>10} {d2:>+8.2f} {d3:>+8.2f} {tot:>+10.2f} {share:>12.0f}%  {stat_name}")
    print("  ⭐ a difference statistic cannot separate 'H2 rose' from 'H3 fell'. A positive")
    print("     share here is improvement bought by degrading the AUTHORITATIVE column.")
    print()

    # -- deficit by stimulus level (NOT "common-mode" -- see the parity split above) -
    print("Deficit by stimulus level (over H2..H7)   median | mean")
    print(f"{'sweep':>16} " + "".join(f"{lab:>9}" for lab in labels) + "  |" +
          "".join(f"{lab:>9}" for lab in labels))
    bylevel = {}
    for sw in sweeps:
        sub = [k for k in keys if k[1] == sw]
        rmed, rmean = [], []
        for lab in labels:
            pool = []
            for k in sub:
                m = masks[k]
                if not m.any():
                    continue
                pl, pe = C[lab][k]
                pool.extend(list(pl[m] - pe[m]))
            rmed.append(float(np.median(pool)) if pool else float("nan"))
            rmean.append(float(np.mean(pool)) if pool else float("nan"))
        bylevel[sw] = {"median": rmed, "mean": rmean}
        print(f"{sw:>16} " + "".join(f"{v:>+9.2f}" for v in rmed) + "  |" +
              "".join(f"{v:>+9.2f}" for v in rmean))

    if args.json:
        json.dump({
            "reports": dict(zip(labels, args.reports)),
            "num_captures": ncap, "fit_overrides": ovr, "reference": ref,
            "floor_db": args.floor, "n_cells": len(keys), "n_band_values": ncells,
            "silence_guard": not args.no_silence_guard,
            "n_silent_od_rows": sum(1 for f, _ in sil if is_od(f) and "gain-n12" not in f),
            "n_model_below_notmeas": nm,
            "median": med, "signed": signed, "abs": absd, "groups": groups,
            "paired_bootstrap": pairs,
            "reference_structure": refstruct,
            "h2_h3_decomposition": decomp, "by_level": bylevel,
            # The drive-regime split is the HEADLINE statistic for an even-order
            # candidate (session 79: a pooled total cancels ~8 dB of real error), so it
            # is machine-readable rather than stdout-only -- a load-bearing table that
            # exists only in a log gets re-transcribed by hand, and a sign gets lost
            # (`rebuild-targets-dont-transcribe`).
            "by_anchor": byanchor, "anchor_bin_edges": ANCHOR_BIN_EDGES,
            "n_bleed_free_cells": len(bkeys),
        }, open(args.json, "w"), indent=1)
        print(f"\n  wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
