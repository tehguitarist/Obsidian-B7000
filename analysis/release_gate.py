#!/usr/bin/env python3.11
"""THE PHASE-9 RELEASE GATE, as a script instead of an ad-hoc read.

Session 90. The gate table agreed with the user in session 89 lives in `CLAUDE.md` "THE RELEASE
GATE"; until now its numbers were produced by one-off reads and transcribed into that table by
hand. That is the `rebuild-targets-dont-transcribe` trap waiting to happen on the single table that
decides when Phase 9 closes — so the thresholds live here, in `GATE`, and every number beside them
is computed from a report file.

WHAT IT MEASURES
----------------
Per ROW (= one capture x one sweep level) the report already stores a gain-matched
`plugin_db - pedal_db` at each 1/3-octave band, so these are SHAPE errors. The gate pools the
per-BAND |delta| values within a region and takes order statistics over that pool -- which is why
its numbers are not comparable to `matrix_grade.py`'s band-RMS (a per-row scalar, then averaged).
Both are printed, because the headline band-RMS row of the gate IS matrix_grade's number.

  region      25-100 Hz | 100 Hz-8 kHz | 8-16.3 kHz     (half-open, so every graded band is in
                                                         exactly one region, and the counts add up)
  subsets     OD | CLEAN | the gain-n12 group and the reference dropouts broken out, never silent
              ⚠ SESSION 111: the gain-n12 OD rows are GRADED again (user decision; GATE N healed
              them on session 48's own instrument). They keep a printed [control] line, which is a
              SUB-SET of OD. `--ex-gain-n12` restores the pre-s111 membership; provenance and the
              measured cost are in `matrix_grade.EXCLUDE_GAIN_N12`'s block.
  THD         the `level` term of shape_gate's decomposition over the OD rows

⚠ THE INSTRUMENT IS PART OF THE NUMBER (session 90, Phase 9 item 0). Every gate figure before this
session came from `analyze.transfer()`, a CSD estimate that does not separate a swept sine's
harmonics from its fundamental. `comprehensive_report.py` now stores all three FR reads per row, so
`--method` re-grades from the SAME renders with no re-render, and `--compare` prints two methods
side by side on membership that is identical by construction. The method that produced each column
is printed in the header; a report too old to carry `methods` is reported as such rather than
silently graded on whatever `plugin_db` happens to hold.

Run:
    python3.11 analysis/release_gate.py analysis/reports/s90_baseline129_h1.json
    python3.11 analysis/release_gate.py REPORT.json --compare csd h1band
    python3.11 analysis/release_gate.py REPORT.json --method csd
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matrix_grade as MG                              # noqa: E402
import shape_gate as SG                                # noqa: E402

# Regions, half-open [lo, hi) except the last, which closes on GRADE_HI. The union is exactly the
# graded band set, and `check_partition()` asserts that rather than trusting it.
REGIONS = (
    ("25-100 Hz", MG.GRADE_LO, 100.0),
    ("100 Hz-8 kHz", 100.0, 8000.0),
    ("8-16.3 kHz", 8000.0, MG.GRADE_HI + 1.0),
)

# Composite regions, for gating a subset over a union of REGIONS rather than one of them.
# `pool()` resolves these; `check_partition()` still validates REGIONS alone, so adding one here
# cannot silently change which bands are graded.
COMPOSITES = {
    # CLEAN's pool floor is 100 Hz, session 91. `reference-sources.md` §1 makes HARDWARE — not ND —
    # the authority for "broadband linear tilt, LF and HF corners", and session 91 shipped c21R
    # 220k -> 130k, a DELIBERATE departure from ND across 25-100 Hz toward the §2 hardware anchor.
    # Grading CLEAN against ND there would score a change the project's own rules class as a PASS
    # (§5 rule 2) as a failure. So CLEAN is graded from 100 Hz up.
    #
    # ⚠⚠ THAT EXCLUSION MADE THE GATE HARDER, NOT EASIER — READ THIS BEFORE CALLING IT A CARVE-OUT.
    # Measured on the SAME reports: CLEAN p90 pooled over ALL bands is 0.77 (s90 ship) and 0.82
    # (s91 130k); over this composite it is **0.802 and 0.808**. The 25-100 Hz bands carried
    # SMALLER errors than the midband, so including them was diluting the pooled p90 downward, and
    # the s90 baseline passed its 0.80 bar only because of that dilution.
    #
    # ⭐ THIS COMPOSITE IS NO LONGER GATED — SESSION 95/96 SPLIT IT IN TWO (see GATE below). It is
    # kept, and still printed by `print_report`, because it is the ONLY thing that makes the
    # session-91 pool change visible to a reader comparing against a pre-s91 quote. Do not delete
    # it and do not re-gate on it: the pooled p90 0.808 is an average of a fine 19-band midband
    # (0.719) and a bad 4-band tail (1.308), and neither is readable from it.
    "100 Hz-16.3 kHz": (100.0, MG.GRADE_HI + 1.0),
}

# The CLEAN regions that ARE gated. `check_clean_partition()` asserts these tile the composite
# above exactly — a silently dropped band would improve every CLEAN bar at once, which is
# `aggregate-moved-check-membership-first` in its most flattering form.
CLEAN_GATED_REGIONS = ("100 Hz-8 kHz", "8-16.3 kHz")
CLEAN_POOL_CONTROL = "100 Hz-16.3 kHz"

# The agreed table. (subset, region_or_None, statistic, SHIP, stretch); region None = pooled over
# every graded band. `stat` is resolved by `STATS`.
#
# ⭐ THE CLEAN ROW WAS SPLIT IN TWO (decided with the user, session 95; executed session 96;
# derivation of record: `docs/clean-gate-split-handover.md`). It was ONE pooled row over
# 100 Hz-16.3 kHz at median ≤0.30 / p90 ≤0.80, and it FAILED BOTH BASELINES (p90 0.802 on s90,
# 0.808 on s91) — a gate that fails the shipped baseline it exists to protect is a false alarm, not
# a regression detector. Session 91's two constants moved it by 0.006 dB, so the failure was never
# about them.
# ⭐⭐ The session-89 midband bars survive the split UNCHANGED at 0.30/0.80, which is the strongest
# evidence this is a correction rather than a concession: the originally agreed numbers pass once
# they are measured on the pool they were meant for (0.215 / 0.719 at s91).
# ⚠ The HF bars (0.40/1.40) are LOOSER than the midband's because CLEAN's top four bands genuinely
# ARE worse (0.340 / 1.308 vs 0.215 / 0.719) — the split makes that visible for the first time
# instead of averaging it away. Their headroom is set by the same rule as the midband's: ~1.5-2x
# the drift this statistic shows under unrelated shipped work (s90 -> s91 moved the midband p90
# 0.008 dB, the HF p90 0.001, the ungated pool 0.053), so every bar sits 0.06-0.09 dB clear of it.
# ⛔ 8-16.3 kHz is GATED, not excluded. §1's "HF corners" clause would arguably justify excluding it
# as 25-100 Hz was excluded, but nothing in sessions 91-95 touched HF, and bundling that in behind a
# justified change is the move that would make this file untrustworthy. This split is a READABILITY
# fix; it must not quietly become an AUTHORITY change.
GATE = [
    ("CLEAN", "100 Hz-8 kHz", "median", 0.30, None),
    ("CLEAN", "100 Hz-8 kHz", "p90", 0.80, None),
    ("CLEAN", "8-16.3 kHz", "median", 0.40, None),
    ("CLEAN", "8-16.3 kHz", "p90", 1.40, None),
    ("OD", "100 Hz-8 kHz", "median", 0.50, 0.50),
    ("OD", "100 Hz-8 kHz", "p90", 2.00, 1.00),
    ("OD", "25-100 Hz", "median", 0.70, 0.50),
    ("OD", "25-100 Hz", "p90", 2.50, 1.50),
    # ⚠⚠ THESE TWO ROWS ARE KNOWN TO BE ARTEFACT-CONTAMINATED, AND ARE DELIBERATELY LEFT GATED
    # ANYWAY (user decision, session 101). `analysis/hf_artefact_gate.py` (GATE I) establishes that
    # the pedal's OD-path rolloff RATE over 8127.5 -> 16255 Hz is drive-DEPENDENT (spans 18.5 dB/oct
    # and turns POSITIVE) where ours holds the drawn -18.25 dB/oct -- and a linear filter has exactly
    # one rate, so this is ND filling its top octave with drive-generated non-harmonic content, not a
    # Sallen-Key error of ours. The CLEAN-path control agrees to 0.57 dB and is level-invariant.
    #
    # NOT excluded, for two measured reasons and one judgement:
    #   - no exclusion closes the gate anyway: dropping all four HF bands moves band-RMS
    #     2.409 -> 2.005 (bar 2.00) and p99 14.661 -> 10.281 (bar 4.00). ONE row, not Phase 9.
    #   - the OD median gets WORSE under every exclusion (0.625 -> 0.636): the HF bands were
    #     diluting it downward, session 91's trap again.
    #   - and the 8127.5 Hz band's error is drive-INDEPENDENT, i.e. a separate REAL defect that a
    #     blanket 8-16.3 kHz exclusion would excuse.
    #
    # ▶ PRE-REGISTERED FALLBACK: if the other OD rows close and these two are the last blocker,
    #   split this region the way session 96 split CLEAN -- 8127.5 Hz (real) graded apart from
    #   12901.6/16255 Hz (artefact-dominated) -- rather than loosening either bar. Re-run GATE I
    #   first; do not act on the numbers above without reproducing them.
    ("OD", "8-16.3 kHz", "median", 0.70, 0.50),
    ("OD", "8-16.3 kHz", "p90", 2.50, 1.50),
    ("OD", "ALL", "p99", 4.00, 3.00),
    ("OD", "ALL", "band-RMS", 2.00, 1.50),
]
THD_LEVEL_SHIP, THD_LEVEL_STRETCH = 3.00, 2.00

STATS = {
    "median": lambda v: float(np.median(v)),
    "p90": lambda v: float(np.percentile(v, 90)),
    "p99": lambda v: float(np.percentile(v, 99)),
    "max": lambda v: float(np.max(v)),
}


def check_partition(bands, idx):
    """The regions must tile the graded bands exactly -- a band silently in no region would be
    invisible to the gate, and a band in two would be double-counted in the pooled p99."""
    counted = sum(len([i for i in idx if lo <= bands[i] < hi]) for _, lo, hi in REGIONS)
    if counted != len(idx):
        sys.exit(f"release_gate: regions cover {counted} of {len(idx)} graded bands -- fix REGIONS")


def deltas(path, method=None):
    """-> (bands, graded_idx, {(file, sweep): (|delta| per graded band, is_od)}, method_used).

    `method` selects one of comprehensive_report's stored FR reads. None keeps whatever the report
    itself graded on, and reports which that was."""
    bands, caps = MG.load(path)
    idx = MG.band_idx(bands, MG.GRADE_LO, MG.GRADE_HI)
    check_partition(bands, idx)
    check_clean_partition(bands, idx)
    rows, seen_methods = {}, set()
    for f, c in caps.items():
        for sw, fr in c["fr"].items():
            src = fr
            if method is not None:
                if "methods" not in fr:
                    sys.exit(f"release_gate: {os.path.basename(path)} predates stored FR methods "
                             f"(no fr['{sw}']['methods']) -- re-run comprehensive_report.py to use "
                             f"--method/--compare")
                if method not in fr["methods"]:
                    sys.exit(f"release_gate: method {method!r} not stored; have "
                             f"{sorted(fr['methods'])}")
                src = fr["methods"][method]
            p, q = src["plugin_db"], src["pedal_db"]
            if max(p) < MG.SILENT_DB or max(q) < MG.SILENT_DB:
                continue
            rows[(f, sw)] = (np.abs(np.array([p[i] - q[i] for i in idx])), MG.is_od(f))
            seen_methods.add(fr.get("fr_method", "unknown (pre-session-90 report)"))
    used = method if method is not None else (
        seen_methods.pop() if len(seen_methods) == 1 else f"MIXED {sorted(seen_methods)}")
    return bands, idx, rows, used


def subsets(rows, drops=frozenset(), ex_n12=None):
    """OD / CLEAN / the broken-out rows.

    Every exclusion here is PRINTED, never silent (session 40) — each one gets its own labelled
    subset rather than vanishing from the totals. The `gain-n12` group keeps its own line even now
    that it is IN the graded OD set, because it is the control that says how much of the headline
    rests on session 111's retirement.

    `drops` is the set of (file, sweep) reference-side ladder dropouts from
    `matrix_grade.find_dropouts` (session 110, on the user's decision: exclude the offending CELL,
    re-detected per render rather than named — the s109 cell moved rung when its file was
    re-captured). Passing nothing keeps the pre-s110 behaviour exactly, so older callers and older
    quotes stay reproducible.

    `ex_n12` defaults to `matrix_grade.EXCLUDE_GAIN_N12` — False since session 111, whose full
    provenance (GATE N's healing, what it does NOT certify, the measured cost) is the block above
    that constant. True restores the pre-s111 membership.

    ⚠ The `gain-n12` subset is a SUB-SET of OD when the exclusion is retired, not a disjoint one —
    it is labelled `[control]` for exactly that reason. Do not sum the subsets."""
    ex_n12 = MG.EXCLUDE_GAIN_N12 if ex_n12 is None else ex_n12
    n12_lbl = "OD gain-n12 [bad]" if ex_n12 else "OD gain-n12 [control]"
    od = {k: v for k, v in rows.items()
          if v[1] and k not in drops and not (ex_n12 and MG.is_gain_n12(k[0]))}
    n12 = {k: v for k, v in rows.items()
           if v[1] and MG.is_gain_n12(k[0]) and (ex_n12 or k not in drops)}
    if not n12:
        sys.exit("release_gate: no OD row matched 'gain-n12' — the control subset is empty, so "
                 "neither the exclusion nor its retirement can be checked (`empty-gate-must-fail`)")
    return {
        "OD": od,
        "CLEAN": {k: v for k, v in rows.items() if not v[1] and k not in drops},
        n12_lbl: n12,
        "ref dropout [bad]": {k: v for k, v in rows.items() if k in drops},
    }


def region_sel(bands, idx, region):
    """The positions WITHIN `idx` that a region name selects. The single resolver -- `pool()` and
    `check_clean_partition()` MUST share it, or the check could pass against logic the pool does
    not actually use."""
    if region == "ALL":
        return list(range(len(idx)))
    lo, hi = (COMPOSITES[region] if region in COMPOSITES
              else next((l, h) for n, l, h in REGIONS if n == region))
    return [j for j, i in enumerate(idx) if lo <= bands[i] < hi]


def check_clean_partition(bands, idx):
    """The gated CLEAN regions must tile the pooled composite EXACTLY -- no band dropped, none
    double-counted (session 96, the row split).

    Asserted rather than eyeballed because a dropped band would lower every CLEAN statistic at
    once, making the split look like an improvement it is not
    (`aggregate-moved-check-membership-first`)."""
    parts = [set(region_sel(bands, idx, r)) for r in CLEAN_GATED_REGIONS]
    union, whole = set().union(*parts), set(region_sel(bands, idx, CLEAN_POOL_CONTROL))
    total = sum(len(p) for p in parts)
    if total != len(union):
        sys.exit(f"release_gate: CLEAN gated regions overlap ({total} selections, {len(union)} "
                 f"distinct bands) -- fix CLEAN_GATED_REGIONS")
    if union != whole:
        sys.exit(f"release_gate: CLEAN gated regions cover {len(union)} bands but the pooled "
                 f"composite {CLEAN_POOL_CONTROL!r} covers {len(whole)} "
                 f"(missing {sorted(bands[idx[j]] for j in whole - union)}, "
                 f"extra {sorted(bands[idx[j]] for j in union - whole)}) -- fix the regions")


def pool(sub, bands, idx, region):
    """Every |delta| band value in the subset x region, as one flat array."""
    sel = region_sel(bands, idx, region)
    if not sel:
        return np.array([]), 0
    return np.concatenate([v[0][sel] for v in sub.values()]) if sub else np.array([]), len(sel)


def band_rms(sub, bands, idx):
    """matrix_grade's statistic: RMS over bands within a row, then the mean over rows."""
    if not sub:
        return float("nan")
    return float(np.mean([np.sqrt(np.mean(v[0] ** 2)) for v in sub.values()]))


def blend_composition(sub, caps, bands, idx):
    """The graded OD subset's BLEND composition -> [(blend, n_captures, n_rows, band_rms), ...].

    ⚠⚠ SESSION 112, ON THE USER'S DECISION, AND IT EXISTS TO STOP A MEMBERSHIP SHIFT READING AS
    PROGRESS. BLEND is by far the largest single axis in this matrix: GATE J measured the OD
    band-RMS spanning 0.200 -> 3.120 dB (15.6x, monotone) from pure clean to pure OD, because at
    low BLEND the clean bleed dilutes the OD path's error. So the pooled OD headline is a weighted
    average whose weights are nothing but *how many captures we happen to own at each blend*.

    That is not hypothetical. Session 112 added 12 level x blend captures at BLEND 0.25/0.5/0.75
    (band-RMS 0.798 against the existing set's 2.432) and the OD headline fell 2.327 -> 2.154 while
    the OD 100 Hz-8 kHz median flipped from `over` back to STRETCH -- with the model UNCHANGED,
    proven by every gated cell being byte-identical on the 127 shared captures. Printing this table
    is what makes that visible without re-deriving it.

    This is `aggregate-moved-check-membership-first` (eighth occurrence) crossed with session 108's
    P4 rule -- do not pool over an operating point the pedal itself sets -- applied to the headline
    gate rather than to a one-off instrument.

    ⛔ Reported, never gated: the bars are still on the pooled number. This says what the pool is
    made of; it does not change it."""
    per = {}
    for (f, _sw), v in sub.items():
        b = caps[f]["settings"].get("blend")
        if b is None:
            continue
        rec = per.setdefault(round(float(b), 4), {"caps": set(), "rms": []})
        rec["caps"].add(f)
        rec["rms"].append(float(np.sqrt(np.mean(v[0] ** 2))))
    out = [(b, len(r["caps"]), len(r["rms"]), float(np.mean(r["rms"])))
           for b, r in sorted(per.items())]
    # A composition that does not account for every graded row is worse than none -- it would
    # under-report exactly the bucket whose settings failed to parse, which is the flattering
    # direction (`empty-gate-must-fail`).
    covered = sum(n_rows for _, _, n_rows, _ in out)
    if covered != len(sub):
        sys.exit(f"release_gate: blend composition covers {covered} of {len(sub)} graded OD rows "
                 f"-- some capture has no 'blend' setting, so the table would be silently partial")
    return out


def measure(path, method=None, ex_n12=None):
    bands, idx, rows, used = deltas(path, method)
    caps = MG.load(path)[1]
    drops, sags, gap = MG.find_dropouts(bands, caps, method)
    warn = MG.check_dropout_separation(gap, drops)
    subs = subsets(rows, drops, ex_n12)
    out = {"method": used, "n_rows": {k: len(v) for k, v in subs.items()}, "cells": {},
           "ex_n12": MG.EXCLUDE_GAIN_N12 if ex_n12 is None else ex_n12,
           "blend_composition": blend_composition(subs["OD"], caps, bands, idx),
           "dropouts": sorted(f"{f}@{s}" for f, s in drops),
           "dropout_gap_db": (None if gap == float("inf") else round(gap, 3)),
           "dropout_warning": warn}
    for name, sub in subs.items():
        for region in ["ALL"] + [r[0] for r in REGIONS] + list(COMPOSITES):
            vals, nb = pool(sub, bands, idx, region)
            if not len(vals):
                continue
            cell = {s: fn(vals) for s, fn in STATS.items()}
            cell.update(n_values=int(len(vals)), n_bands=nb, n_rows=len(sub))
            cell["band-RMS"] = band_rms(sub, bands, idx) if region == "ALL" else float("nan")
            out["cells"][(name, region)] = cell
    return out


def thd_split(path):
    """-> {label: (rms, signed_mean, n)} for the gated OD THD rows and both sub-reads.

    Session 110: the reference ladder dropouts are excluded here TOO, on the same detected set the
    FR rows use. The s109 dropout cell is the SECOND-WORST THD row of the whole shipped
    decomposition, so leaving it in the THD gate row while removing it from the FR rows would make
    the two halves of the gate disagree about which data exists.

    ⚠ Session 111 the same way round: the `gain-n12` retirement applies HERE TOO, and it has to,
    because GATE N certified those rows on a THD statistic — excluding them from the THD gate row
    while grading them on FR would be quoting the certification and refusing its consequence.

    ⛔ AND THE SPLIT IS PRINTED BECAUSE THE POOLED ROW IS NOW A MIXTURE OF TWO OPPOSITE-SIGNED
    POPULATIONS. The gated term is `abs(c[0])/sqrt(n)` RMS'd over rows — a MAGNITUDE — and the two
    halves disagree about the DIRECTION: at full send the model over-distorts (signed +1.41 dB at
    s110) and at the 12.071 dB lower send it UNDER-distorts (−0.77). So an rms over the union is
    smaller than either population's own error, and the number falls for a membership reason rather
    than a model one. `unsigned-aggregates-have-no-sign` (s109) meeting
    `aggregate-moved-check-membership-first` — the signed means are printed beside every rms so the
    mixture cannot be read as an improvement."""
    _, rows, _ = SG.thd_rows(path)
    bands, caps = MG.load(path)
    drops, _, _ = MG.find_dropouts(bands, caps)
    od = {k: r for k, r in rows.items() if r["is_od"] and k not in drops}
    groups = {"OD (gated)": od,
              "  ex gain-n12 [pre-s111]": {k: r for k, r in od.items()
                                           if not MG.is_gain_n12(k[0])},
              "  gain-n12 only [control]": {k: r for k, r in od.items()
                                            if MG.is_gain_n12(k[0])}}
    return {lbl: ((float(np.sqrt(np.mean([r["level"] ** 2 for r in g.values()]))),
                   float(np.mean([r["level_signed"] for r in g.values()])), len(g))
                  if g else (float("nan"), float("nan"), 0))
            for lbl, g in groups.items()}


#: ⛔⛔ SESSION 114 SPLIT THE THD ROW BY OPERATING POINT, on the user's "keep pooling only if it is
#: getting us closer to accuracy" decision. It is not, and the split is the session-96 CLEAN move:
#: nothing is excluded, and the mixture stops hiding the defect.
#:
#: Measured on `s114_baseline.json`, the pooled row and its two halves:
#:      pooled          rms 2.974   SIGNED +1.380   n 322   -> SHIP
#:      full send       rms 3.084   SIGNED +1.534   n 289   -> over
#:      gain-n12        rms 1.748   SIGNED +0.032   n  33   -> SHIP
#: The pooled number is SMALLER THAN EITHER-ish and, decisively, it **flips the verdict on the
#: population the 3.0 bar was agreed against** (session 89, when `gain-n12` was excluded outright).
#:
#: ⭐ And the disagreement is SIGNAL, not noise. GATE S (s113) measured the model's distortion rising
#: with input FASTER than the reference's, so 12 dB down the send the model's excess distortion very
#: nearly vanishes (+1.53 -> +0.03). Averaging the two destroys exactly the second-operating-point
#: information that makes those rows worth grading at all (s111).
#: ⚠ s111 recorded the two as OPPOSITE-signed (-0.772 at n=15). That framing is STALE: at s114 the
#: group is n=33 and reads +0.032, i.e. near zero rather than negative. The split is justified by the
#: 1.5 dB DISAGREEMENT and the flipped verdict, not by a sign cancellation.
#:
#: Both rows carry the SAME 3.0 bar deliberately: it expresses how much THD level error is
#: acceptable, which is a property of the model, not of the send level. No new threshold was invented
#: -- inventing one is how a split quietly becomes a concession (s96).
THD_ROWS = (("full send", "  ex gain-n12 [pre-s111]"),
            ("gain-n12", "  gain-n12 only [control]"))


def thd_level(path, ex_n12=None):
    """The gate's THD rows: the `level` term of shape_gate's decomposition, OD rows, SPLIT BY
    OPERATING POINT (session 114 -- see THD_ROWS).

    -> [(label, rms, n), ...]. RMS over rows, matching how shape_gate reports every other term --
    a signed mean would let a row that is 6 dB hot cancel one that is 6 dB cold and report 0.

    `ex_n12` is kept so every pre-s114 quote stays reproducible: it collapses the pair back to the
    single pooled/excluded row the gate used to print."""
    s = thd_split(path)
    if ex_n12 is None:
        ex_n12 = MG.EXCLUDE_GAIN_N12
    if ex_n12:                                      # the pre-s111 single-row reading, verbatim
        rms, _sg, n = s["  ex gain-n12 [pre-s111]"]
        return [("ex gain-n12", rms, n)]
    out = []
    for label, key in THD_ROWS:
        rms, _sg, n = s[key]
        if not n:
            sys.exit(f"release_gate: THD sub-population '{label}' is EMPTY -- the split cannot be "
                     f"graded and a missing row must not read as a pass (`empty-gate-must-fail`)")
        out.append((label, rms, n))
    return out


def verdict(value, ship, stretch):
    if not np.isfinite(value) or ship is None:
        return "—"
    if stretch is not None and value <= stretch:
        return "STRETCH"
    return "SHIP" if value <= ship else "over"


def print_report(path, m, thd):
    print(f"\n=== RELEASE GATE — {os.path.basename(path)} ===")
    print(f"    FR read: {m['method']}   graded band {MG.GRADE_LO:g}–{MG.GRADE_HI:g} Hz   "
          f"rows: " + ", ".join(f"{k} {v}" for k, v in m["n_rows"].items()))
    print(f"\n{'subset':<20}{'region':<15}{'stat':>9}{'value':>9}{'SHIP':>8}{'stretch':>9}"
          f"{'n':>8}   verdict")
    n_over = 0
    for subset, region, stat, ship, stretch in GATE:
        cell = m["cells"].get((subset, region))
        if cell is None:
            print(f"{subset:<20}{region:<15}{stat:>9}{'—':>9}{ship:>8.2f}"
                  f"{'—' if stretch is None else f'{stretch:8.2f}':>9}{'0':>8}   NO DATA")
            n_over += 1                                # an empty cell FAILS, it does not pass
            continue
        v = cell[stat]
        mark = verdict(v, ship, stretch)
        n_over += mark == "over"
        print(f"{subset:<20}{region:<15}{stat:>9}{v:9.3f}{ship:>8.2f}"
              f"{'—' if stretch is None else f'{stretch:8.2f}':>9}{cell['n_values']:>8}   {mark}")
    for label, tv, tn in thd:
        tmark = verdict(tv, THD_LEVEL_SHIP, THD_LEVEL_STRETCH)
        n_over += tmark == "over"
        print(f"{'THD (OD)':<20}{('level, ' + label):<15}{'rms':>9}{tv:9.3f}{THD_LEVEL_SHIP:>8.2f}"
              f"{THD_LEVEL_STRETCH:>9.2f}{tn:>8}   {tmark}")
    if len(thd) > 1:
        print("     ⚠ SPLIT BY OPERATING POINT, session 114 (was one pooled row). Pooled it reads")
        print("       2.974 = SHIP while the full-send half — the population the 3.0 bar was agreed")
        print("       against — is over. The 1.5 dB disagreement is GATE S's compression-slope")
        print("       error, i.e. signal; averaging it away is what the pooled row was doing.")
    # ⛔ The THD sub-populations with their SIGNED means, ALWAYS printed — see thd_split's docstring.
    # The gated term is unsigned, so a reader must be able to see the direction and the disagreement
    # before quoting any verdict on it as a statement about the model.
    if m.get("thd_split"):
        print("     signed means (the gated term is an unsigned rms and never carried a direction):")
        for lbl, (r, s, n) in m["thd_split"].items():
            print(f"       {lbl.strip():<26}rms {r:6.3f}   SIGNED mean {s:+6.3f}   n {n:>4}")

    # SESSION 111: state the OD membership on every run. It changed, so a reader comparing against
    # any pre-s111 quote must be able to see which set produced this column without going to a doc
    # (`aggregate-moved-check-membership-first`, and it has faked a regression seven times).
    if m["ex_n12"]:
        print("\n  ⚠ MEMBERSHIP: --ex-gain-n12 — PRE-SESSION-111 control, the gain-n12 OD rows are "
              "EXCLUDED.\n    This is not the shipped definition; quote it only against a pre-s111 "
              "figure.")
    else:
        print("\n  MEMBERSHIP: the gain-n12 OD rows are GRADED (session 111, user decision — GATE N "
              "healed\n    them on session 48's own THD-turnover instrument). They keep a printed "
              "[control] line, which is\n    a SUB-SET of OD, not a disjoint one. Every pre-s111 "
              "number is on the old membership: re-run with\n    --ex-gain-n12 to compare like "
              "with like.")

    # SESSION 112, user decision: what the pooled OD number is MADE OF, on every run. BLEND spans
    # 15.6x in band-RMS (GATE J), so the headline is a weighted average of buckets that differ by
    # more than the defect being measured -- and the weights are just the capture inventory.
    comp = m.get("blend_composition")
    if comp:
        print("\n  OD BLEND COMPOSITION — reported, NOT gated. The bars are still on the pooled "
              "number; this says\n    what the pool is made of. BLEND spans ~15x in band-RMS "
              "(GATE J), so ADDING captures at low\n    BLEND lowers the OD headline with no model "
              "change. Check this before reading any movement:")
        print(f"    {'BLEND':>6}{'captures':>10}{'rows':>7}{'band-RMS':>10}")
        for b, ncap, nrow, rms in comp:
            print(f"    {b:6.2f}{ncap:10d}{nrow:7d}{rms:10.3f}")
        tot = sum(n for _, _, n, _ in comp)
        print(f"    {'pooled':>6}{sum(c for _, c, _, _ in comp):10d}{tot:7d}"
              f"{m['cells'][('OD', 'ALL')]['band-RMS']:10.3f}")

    print(f"\n  reported, NOT gated (the notch row of the gate table, and the excluded rows):")
    # The reference-side ladder dropouts, DETECTED per render rather than named (session 110).
    # Printed here for the same reason the gain-n12 split is: an exclusion that is not printed is
    # the session-40 trap.
    if m["dropouts"]:
        print(f"\n  reference ladder DROPOUTS excluded from OD/CLEAN, detected not named "
              f"({len(m['dropouts'])} cell(s), threshold {MG.DROPOUT_DB:.1f} dB in a measured "
              f"{m['dropout_gap_db']} dB gap):")
        for d in m["dropouts"]:
            print(f"    ! {d}")
    else:
        print("\n  reference ladder dropouts: none detected")
    if m["dropout_warning"]:
        print(f"    ⚠ {m['dropout_warning']}")
    for subset in list(m["n_rows"]):
        cell = m["cells"].get((subset, "ALL"))
        if cell:
            print(f"    {subset:<22}band-RMS {cell['band-RMS']:6.3f}   max |Δ| {cell['max']:6.2f} "
                  f"dB   over {cell['n_rows']} rows x {cell['n_bands']} bands")
    for subset in ("OD", "CLEAN"):
        for region in [r[0] for r in REGIONS]:
            cell = m["cells"].get((subset, region))
            if cell:
                print(f"    {subset:<8}{region:<15}median {cell['median']:5.2f}  p90 "
                      f"{cell['p90']:5.2f}  p99 {cell['p99']:6.2f}  max {cell['max']:6.2f}")

    # The CLEAN gate's definition has changed TWICE (pool floor in session 91, row split in 96).
    # Print both superseded statistics beside the current pair, always — a gate that quietly
    # redefines its own pool is exactly the `rebuild-targets-dont-transcribe` failure this file
    # exists to prevent, and a reader comparing against any older quote needs the old numbers on
    # the page. These are CONTROLS: they are computed, labelled superseded, and never gated.
    allb = m["cells"].get(("CLEAN", "ALL"))
    pooled = m["cells"].get(("CLEAN", CLEAN_POOL_CONTROL))
    mid = m["cells"].get(("CLEAN", CLEAN_GATED_REGIONS[0]))
    hf = m["cells"].get(("CLEAN", CLEAN_GATED_REGIONS[1]))
    if allb and pooled and mid and hf:
        print("\n  ⚠ CLEAN's gated definition has changed twice — both superseded pools, as "
              "CONTROLS:")
        print(f"      pooled 25-16255 Hz   [pre-s91: before the LF exclusion]  "
              f"median {allb['median']:.3f}  p90 {allb['p90']:.3f}   n={allb['n_values']}")
        print(f"      pooled 100-16255 Hz  [s91-95: one row, bar 0.30/0.80  ]  "
              f"median {pooled['median']:.3f}  p90 {pooled['p90']:.3f}   n={pooled['n_values']}")
        print(f"      SPLIT 100 Hz-8 kHz   [current, gated 0.30/0.80        ]  "
              f"median {mid['median']:.3f}  p90 {mid['p90']:.3f}   n={mid['n_values']}")
        print(f"      SPLIT 8-16.3 kHz     [current, gated 0.40/1.40        ]  "
              f"median {hf['median']:.3f}  p90 {hf['p90']:.3f}   n={hf['n_values']}")
        print(f"      s91 dropped 25-100 Hz because `reference-sources.md` §1 makes HARDWARE the "
              f"authority for LF corners.\n"
              f"      That made the gate HARDER (the LF bands carried smaller errors and were "
              f"diluting p90 down), and the\n"
              f"      surviving pooled row then failed BOTH baselines. Session 96 split it: "
              f"{pooled['p90']:.3f} is the average of a fine\n"
              f"      {mid['n_bands']}-band midband ({mid['p90']:.3f}) and a bad {hf['n_bands']}"
              f"-band tail ({hf['p90']:.3f}), and neither is readable from it. The\n"
              f"      session-89 midband bars are UNCHANGED at 0.30/0.80; the HF bars are looser "
              f"because that region is\n"
              f"      genuinely worse, not to make it pass. Derivation: "
              f"docs/clean-gate-split-handover.md.")

    print(f"\n  {'ALL GATED ROWS MET' if n_over == 0 else f'{n_over} ROW(S) OVER SHIP'}\n")
    return n_over


def print_compare(path, ms):
    """Two methods, one report -> identical membership by construction."""
    print(f"\n=== FR-METHOD COMPARISON — {os.path.basename(path)} ===")
    print("    Same renders, same rows, same bands: the only thing that differs is the FR read.\n")
    names = [m["method"] for m in ms]
    print(f"{'subset':<20}{'region':<15}{'stat':>9}" + "".join(f"{n:>12}" for n in names)
          + f"{'Δ':>9}")
    for subset, region, stat, _ship, _st in GATE:
        cells = [m["cells"].get((subset, region)) for m in ms]
        if any(c is None for c in cells):
            continue
        vals = [c[stat] for c in cells]
        print(f"{subset:<20}{region:<15}{stat:>9}" + "".join(f"{v:12.2f}" for v in vals)
              + f"{vals[-1] - vals[0]:9.2f}")
    print()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report")
    ap.add_argument("--method", default=None,
                    help="grade on a stored FR read (csd|h1|h1band) instead of the report's own")
    ap.add_argument("--compare", nargs="+", default=None, metavar="METHOD",
                    help="grade several stored FR reads side by side, identical membership")
    ap.add_argument("--json", default=None, help="also write the measured cells here")
    ap.add_argument("--ex-gain-n12", action="store_true",
                    help="PRE-SESSION-111 control: exclude the gain-n12 OD rows again, so any "
                         "figure quoted before session 111 can be reproduced exactly")
    a = ap.parse_args()
    ex = a.ex_gain_n12 or None                 # None -> the module default (currently: include)

    if a.compare:
        ms = [measure(a.report, mth, ex) for mth in a.compare]
        print_compare(a.report, ms)
        return

    m = measure(a.report, a.method, ex)
    m["thd_split"] = thd_split(a.report)
    n_over = print_report(a.report, m, thd_level(a.report, ex))
    if a.json:
        out = {"report": a.report, "method": m["method"], "n_rows": m["n_rows"],
               "ex_gain_n12": m["ex_n12"],
               "grade_lo": MG.GRADE_LO, "grade_hi": MG.GRADE_HI,
               "cells": {f"{k[0]}|{k[1]}": v for k, v in m["cells"].items()}}
        json.dump(out, open(a.json, "w"), indent=1)
        print(f"  wrote {a.json}")
    sys.exit(1 if n_over else 0)


if __name__ == "__main__":
    main()
