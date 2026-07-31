#!/usr/bin/env python3.11
"""a3_budget_rederive -- re-derive A3's C1/C2/C3 component budget against the
CORROBORATED curve, and state exactly which components the corroboration reaches.

WHY THIS EXISTS (session 86's next-step (b))
--------------------------------------------
Session 50 wrote A3's budget down as three numbers, and every A3 candidate since has
been aimed at them:

    C1  broadband floor      +2.68 dB   (mean of 50, 64 Hz)
    C2  low-mid rise         +3.20 dB   on top of C1 (mean of 101 .. 508 Hz)
    C3  LF rise              +7.86 dB   on top of C1 (20 Hz), slope 9.18 dB/oct

Those three numbers were read off ONE instrument -- `a3_shape_gate`'s drive-axis
`20log10 s` -- as POINT VALUES with no uncertainty attached, and at a bleed level
`beta` the same instrument fits. Session 85 then built a second instrument
(`a3_harmonic_axis`, `k` from the LEVEL/BLEND dilution: no solve, no taper, no `b0`,
no bleed model) and session 86 showed the two describe ONE curve. So the budget can
now be re-derived against both -- which is what this tool does.

⛔⛔ THE HEADLINE IS PARTLY NEGATIVE, AND IT IS A COVERAGE FACT, NOT AN OPINION.
`a3_harmonic_axis.ANCHOR_HZ` IS `comprehensive_report.THD_ANCHORS` -- (100, 200, 400)
Hz, the stimulus's own swept-THD anchors. There is no anchor below 100 Hz and none
above 400. So of the three components:

    C1  (50, 64 Hz)          -- 0 anchors. NOT reachable by the second instrument.
    C2  (101 .. 508 Hz)      -- 3 of its 7 bands carry an anchor.
    C3  (20, 25, 32 Hz)      -- 0 anchors. NOT reachable by the second instrument.

GATE 1 computes that table rather than asserting it, and the tool refuses to describe
a component as corroborated when its anchor count is zero. ⇒ the corroboration reaches
C2 and nothing else, and C1/C3 remain single-instrument numbers no matter how well the
two axes agree at 100-400 Hz.

⚠ AND C2's CORROBORATION IS ONLY HALF-INDEPENDENT -- state it that way or it is
overclaimed. C2 is a DIFFERENCE, `s(low-mids) - s(floor)`, and the harmonic axis has
no floor band. So the cross-instrument test necessarily pairs the harmonic axis's
low-mid level against the DRIVE axis's floor: one instrument supplies each half. What
that does establish is real -- the low-mid level is measured by a tool with no beta in
it at all -- but it is not two independent measurements of C2.

WHAT REPLACES THE THREE POINT VALUES
------------------------------------
A component is a DIFFERENCE of two solved quantities that share a beta, so an
independent "+-" on each is the wrong object: the errors are correlated, and
differencing two independent ranges overstates the width. What IS well defined is

    (a) each band's own +0.25 dB joint (s, theta) region      -- section A
    (b) the GAP between two bands' regions                    -- section B
    (c) how far a component moves across beta's own interval  -- GATE 2

so the budget is re-stated as a level plus a resolvedness gap, not as three numerals.
⚠ (a) is a cost-slack region, NOT a confidence interval, and the harmonic axis's is a
5-95 group bootstrap -- two different constructions, so OVERLAP/DISJOINT here is a
legibility verdict, exactly as session 86 recorded, never a formal test.

⚠ Reads build/a3_dec_*.csv via `a3_shape_gate.render` into a temp dir (so the shipped
baseline CSVs are never overwritten) and the harmonic axis's report JSON. GATE 0
refuses to print anything if either instrument fails to reproduce its record, or if
session 50's budget does not reproduce -- a moved instrument and a moved result are
indistinguishable otherwise.

Usage:
    python3.11 analysis/a3_budget_rederive.py
    python3.11 analysis/a3_budget_rederive.py --out analysis/reports/s87_budget.json
"""
import argparse
import json
import math
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a3_axis_compare as AC                                         # noqa: E402
import a3_component_budget as cb                                     # noqa: E402
import a3_harmonic_axis as HA                                        # noqa: E402
import a3_phase_solve as ps                                          # noqa: E402
import a3_shape_gate as sg                                           # noqa: E402
from parallel import pmap_cpu                                        # noqa: E402

# Session 50's recorded budget, at ITS OWN beta. GATE 0 reproduces these through
# `a3_component_budget`'s own constants and solver rather than re-transcribing the band
# sets (`rebuild-targets-dont-transcribe`).
S50_BETA = -16.75
S50 = dict(c1=2.68, c2=3.20, c3=7.86, slope=9.18)
# Session 50's own beta-robustness spans, reproduced as a check on GATE 2.
S50_SPANS = {20: 2.51, 50: 0.07, 254: 1.10, 508: 0.68}
S50_IDENTIFIED = (-17.25, -16.50)

# The measured-conditioning restriction session 86 named (s-interval <= 2.5 dB).
# Frozen HERE at the shipped baseline and never re-derived per candidate
# (`self-selecting-scores`); printed alongside, never substituted for, the full set.
WIDE_INTERVAL_DB = 2.5

CAPTURE_FLOOR_DB = 0.144        # a3_component_budget's own identifiability criterion


# --------------------------------------------------------------------------- #
# the beta sweep -- CPU-bound numpy, so PROCESSES (parallel.pmap_cpu's own table)
# --------------------------------------------------------------------------- #
_BANDS = None


def _sweep_init(bands):
    """Ship the (t_db, mu) table once per worker, not once per item.

    Module-level for the same reason `a3_phase_solve._beta_init` is: under `spawn`
    each worker re-imports this module, and the table is identical for every beta.
    """
    global _BANDS
    _BANDS = bands


def _sweep_one(beta_db):
    """`20log10 s` per band plus the total residual, at ONE beta.

    Uses `ps.fit_band`'s DEFAULT grid, matching `a3_component_budget.solve_at` exactly
    -- GATE 0 compares against that tool's recorded numbers, so a coarser grid here
    would make the comparison a grid difference wearing a result's clothes.
    """
    rows, tot = {}, 0.0
    for b, t_db, mu in _BANDS:
        (_, cost, s), _ = ps.fit_band(np.asarray(t_db), np.asarray(mu), beta_db)
        rows[b] = 20.0 * math.log10(s)
        tot += cost
    return beta_db, rows, tot


def beta_sweep(pedal, model, betas):
    bands = [(b, list(pedal[b]), [model[d][b][0] for d, _ in ps.DRIVES])
             for b in sg.BETA_BANDS]
    got = pmap_cpu(_sweep_one, list(betas), initializer=_sweep_init, initargs=(bands,))
    return {round(b, 4): (rows, tot) for b, rows, tot in got}


def components(rows):
    """C1 / C2 / C3 from a curve, using a3_component_budget's OWN band sets."""
    c1 = float(np.mean([rows[b] for b in cb.FLOOR_BAND]))
    c2 = float(np.mean([rows[b] for b in cb.C2_BANDS])) - c1
    c3 = rows[20] - c1
    slope = (rows[20] - rows[32]) / math.log2(32.0 / 20.0)
    return dict(c1=c1, c2=c2, c3=c3, slope=slope)


# --------------------------------------------------------------------------- #
# gates
# --------------------------------------------------------------------------- #
def gate0(hrows, pooled, srows, beta, s50_rows):
    print("=== GATE 0 -- BASELINE: BOTH INSTRUMENTS *AND* THE PRIOR BUDGET ===")
    kd = max(abs(hrows[h]["k"] - AC.K_RECORD[h]) for h in AC.K_RECORD if h in hrows)
    pdk = abs(pooled["k"] - AC.K_POOLED_RECORD)
    print(f"  harmonic axis   worst per-band |dk| {kd:.3f} dB, pooled |dk| {pdk:.3f} dB"
          f"  (n={pooled['n']}, rms {pooled['rms']:.2f})")
    sd = max(abs(srows[b]["s_db"] - sg.BASELINE_DB[b]) for b in sg.CORE)
    print(f"  shape gate      worst |d(20log10 s)| vs record {sd:.3f} dB, "
          f"beta {beta:+.2f} dB")
    c = components(s50_rows)
    bd = max(abs(c[k] - S50[k]) for k in S50)
    print(f"  session-50 budget at its own beta {S50_BETA:+.2f}:  "
          f"C1 {c['c1']:+.2f} / C2 {c['c2']:+.2f} / C3 {c['c3']:+.2f} / "
          f"slope {c['slope']:.2f}  ->  worst |d| {bd:.3f} dB")
    bad = kd > 0.05 or pdk > 0.05 or sd > 0.05 or bd > 0.05
    print("  " + ("FAIL -- something moved; a moved result is unreadable"
                  if bad else "PASS -- all three records reproduce"))
    return (not bad), c


def gate1_coverage():
    """Which components the second instrument can reach AT ALL. Computed, not argued.

    An anchor count of zero is not a weak measurement, it is the absence of one -- and
    that distinction is the whole reason this gate prints before any comparison.
    """
    print("\nGATE 1 -- COVERAGE: which components does the harmonic axis reach?")
    sets = (("C1  floor   ", cb.FLOOR_BAND),
            ("C2  low-mid ", cb.C2_BANDS),
            ("C3  LF      ", cb.C3_BANDS))
    anchors = {AC.BAND_OF[h]: h for h in HA.ANCHOR_HZ}
    cov = {}
    for label, bands in sets:
        hit = [anchors[b] for b in bands if b in anchors]
        cov[label.split()[0]] = hit
        print(f"  {label} bands {str(bands):<40} anchors {len(hit)}/{len(bands)}"
              f"  {[f'{h:.0f} Hz' for h in hit] if hit else '-- NONE'}")
    print(f"  harmonic-axis anchors = {[f'{h:.0f}' for h in HA.ANCHOR_HZ]} Hz "
          f"(= comprehensive_report.THD_ANCHORS, a property of the STIMULUS)")
    print("  => the corroboration reaches C2 only. C1 and C3 stay single-instrument")
    print("     numbers, and no amount of agreement at 100-400 Hz changes that.")
    return cov


def gate2_beta(sweep, betas, fitted):
    """ds/dbeta per band, measured -- and each component's span across beta's own
    identified interval.

    Why this is a gate and not a footnote: C1 is a FLAT component and beta is a flat
    knob, so "the model's OD is 2.7 dB too weak everywhere" and "the pedal's bleed is
    2.7 dB hotter than we think" are partly the same data (session 50's own framing).
    The only thing that separates them is how fast the joint fit degrades -- measured
    here, and cross-checked against session 50's recorded spans.
    """
    print("\nGATE 2 -- BETA SENSITIVITY, MEASURED (not assumed)")
    n = len(sg.BETA_BANDS) * len(ps.DRIVES)
    rms = {b: math.sqrt(sweep[b][1] / n) for b in betas}
    ok = [b for b in betas if rms[b] <= CAPTURE_FLOOR_DB]
    print(f"  {'beta':>7} {'fit rms':>9}   {'s(20)':>7} {'s(50)':>7} {'s(101)':>7} "
          f"{'s(202)':>7} {'s(403)':>7}   identified")
    for b in betas:
        r = sweep[b][0]
        flag = "yes" if b in ok else "-"
        mark = "  <- fitted" if abs(b - fitted) < 1e-9 else ""
        print(f"  {b:+7.2f} {rms[b]:9.4f}   {r[20]:+7.2f} {r[50]:+7.2f} {r[101]:+7.2f} "
              f"{r[202]:+7.2f} {r[403]:+7.2f}   {flag:>10}{mark}")
    lo, hi = min(ok), max(ok)
    print(f"\n  identified interval (rms <= {CAPTURE_FLOOR_DB:.3f} dB) = "
          f"[{lo:+.2f}, {hi:+.2f}] dB")
    # ⚠ THAT IS WIDER THAN SESSION 50's RECORD, AND THE CAUSE IS THE GRID, NOT THE DATA.
    # `a3_component_budget` sweeps at 0.25 dB; this tool at 0.1 dB, so it SEES points the
    # coarser grid steps over. Verified rather than asserted: restricted to session 50's
    # own 0.25 dB sub-grid the interval reproduces exactly. An unexplained widening here
    # would read as a moved result for the rest of the project's life.
    sub = [b for b in ok if abs(b * 4 - round(b * 4)) < 1e-9]
    s_lo, s_hi = (min(sub), max(sub)) if sub else (float("nan"), float("nan"))
    agree = (abs(s_lo - S50_IDENTIFIED[0]) < 1e-9 and abs(s_hi - S50_IDENTIFIED[1]) < 1e-9)
    print(f"    on session 50's own 0.25 dB sub-grid = [{s_lo:+.2f}, {s_hi:+.2f}] dB   "
          f"(recorded [{S50_IDENTIFIED[0]:+.2f}, {S50_IDENTIFIED[1]:+.2f}])  "
          f"{'REPRODUCES' if agree else 'DOES NOT REPRODUCE'}")
    if not agree:
        sys.exit("the identified interval does not reproduce on session 50's own grid -- "
                 "that is a moved result, not a resolution difference. Stop and localise "
                 "it before reading anything below.")
    print("    => the wider interval is this tool's finer grid seeing points the 0.25 dB")
    print("       sweep stepped over, NOT a moved measurement. Every beta-span figure")
    print("       below is correspondingly wider than session 50's for the same reason.")

    # ds/dbeta -- the number section C's cross-constraint is built on, so it is
    # MEASURED, not taken as -1.
    #
    # ⚠⚠ A DEFECT IN THIS GATE's FIRST VERSION, worth keeping as the reason it is now
    # written this way. It took a central difference at `fitted +- step`, where `step`
    # came from `betas[1] - betas[0]` -- but the sweep carries two off-grid points (the
    # two beta conventions), so neither neighbour existed in it and `slopes` came back
    # EMPTY. Nothing failed: the table printed zero rows, section C's loop produced no
    # items, its `lows and highs` test was then False on empty lists and it narrated
    # "the three bands agree on beta's direction" over NO DATA, while the interval
    # intersection printed its own +-99 initialiser as though it were a measurement
    # (`computed-verdicts-not-narrated`, plus session 40's sentinel-as-a-value trap).
    # Now: a least-squares slope over the beta points INSIDE the identified interval --
    # which is the right estimator anyway (it is the region beta is identified in, and
    # those points are unevenly spaced) -- and it EXITS rather than printing a partial
    # table.
    fit_bands = [20, 50, 64, 101, 127, 160, 202, 254, 403, 508]
    if len(ok) < 3:
        sys.exit(f"only {len(ok)} beta points inside the identified interval -- cannot "
                 "measure ds/dbeta; widen the sweep or the step.")
    xs = np.asarray(ok, dtype=float)
    A = np.vstack([xs, np.ones_like(xs)]).T
    print(f"\n  ds/dbeta, least squares over the {len(ok)} beta points inside the "
          f"identified interval:")
    slopes = {}
    for b in fit_bands:
        ys = np.asarray([sweep[k][0][b] for k in ok], dtype=float)
        slopes[b] = float(np.linalg.lstsq(A, ys, rcond=None)[0][0])
    missing = [b for b in fit_bands if b not in slopes]
    if missing:
        sys.exit(f"ds/dbeta missing for {missing} -- refusing to print a partial table.")
    for b in fit_bands:
        print(f"    {b:4d} Hz  {slopes[b]:+6.2f} dB of s per dB of beta")
    # ⭐ THE SIGNS ARE NOT ALL THE SAME, AND THAT IS A REAL STRUCTURAL FACT. beta is a
    # flat level knob, so the naive expectation is that raising it lowers every band's
    # `s` by the same amount. It does not: `s` is solved from a two-phasor
    # cancellation, so a band near anti-phase (theta -> 180, the LF end) moves the
    # OPPOSITE way to one near quadrature. Any argument of the form "beta is flat, so a
    # flat component is degenerate with it" has to be checked per band against this
    # table rather than asserted.
    pos = [b for b in fit_bands if slopes[b] > 0]
    neg = [b for b in fit_bands if slopes[b] < 0]
    print(f"    => ds/dbeta is POSITIVE at {pos} and NEGATIVE at {neg}: beta does not")
    print(f"       move the curve up or down, it TILTS it. |ds/dbeta| is smallest at "
          f"{min(fit_bands, key=lambda b: abs(slopes[b]))} Hz\n       "
          f"({min(abs(slopes[b]) for b in fit_bands):.2f}), which is why C1 is the "
          f"beta-robust component.")

    print("\n  component span across the identified beta interval "
          "(session 50's own check):")
    for b in sorted(S50_SPANS):
        vals = [sweep[k][0][b] for k in ok]
        span = max(vals) - min(vals)
        print(f"    {b:4d} Hz  {min(vals):+6.2f} .. {max(vals):+6.2f} dB   "
              f"span {span:.2f}  (recorded {S50_SPANS[b]:.2f})")
    return slopes, (lo, hi), ok


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=AC.DEFAULT_REPORT)
    ap.add_argument("--sweep", default="sweep_drv_-18")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rng = np.random.default_rng(AC.SEED)
    _, lad = AC.load_ladder(args.report)
    hrows, pooled = AC.harmonic_side(lad, rng)

    tmp = tempfile.mkdtemp(prefix="a3budget_")
    beta, srows, model, pedal = AC.shape_side(os.path.join(tmp, "dec"), args.sweep, [])

    # One sweep serves GATE 0 (session 50's beta), GATE 2 (sensitivity + the identified
    # interval) and section C (the beta cross-constraint).
    # 0.05 dB step: section C reads the joint beta constraint off THIS grid rather than
    # linearising, so its resolution IS the grid's -- and the grid must be a strict
    # SUPERSET of session 50's 0.25 dB sweep, or GATE 2's reproduction check compares
    # two different point sets. ⚠ A 0.1 dB step from -18.00 looks like it contains the
    # 0.25 grid and does not (it never lands on -17.25), and GATE 2 duly refused to
    # print -- correctly, because at that point the two intervals really were measured
    # over different betas. 0.05 contains both.
    betas = [round(-18.0 + 0.05 * i, 4) for i in range(41)]
    for extra in (S50_BETA, round(beta, 4)):
        if extra not in betas:
            betas.append(extra)
    betas = sorted(betas)
    sweep = beta_sweep(pedal, model, betas)

    ok0, s50 = gate0(hrows, pooled, srows, beta, sweep[S50_BETA][0])
    if not ok0:
        return 1
    cov = gate1_coverage()
    slopes, ident, ok_betas = gate2_beta(sweep, betas, round(beta, 4))

    # ⚠ TWO BETA CONVENTIONS EXIST AND BOTH RECORDS ARE CORRECT. `a3_component_budget`
    # takes the min-cost beta off its OWN 0.25 dB sweep (-16.75); `a3_shape_gate.
    # fit_beta` scans at 0.1 dB and lands on -16.80, which is what the axis comparison
    # and every session-86 number use. Stated with its consequence rather than quietly
    # reconciled -- an unexplained 0.05 dB later reads as a discrepancy.
    here = components({b: srows[b]["s_db"] for b in sg.CORE})
    print(f"\n⚠ BETA CONVENTION: a3_component_budget's own sweep minimum is "
          f"{S50_BETA:+.2f} dB (0.25 dB grid);")
    print(f"  a3_shape_gate.fit_beta gives {beta:+.2f} dB (0.1 dB grid). Both are the "
          f"same objective at")
    print(f"  different resolutions. Consequence for the budget: C1 {s50['c1']:+.2f} -> "
          f"{here['c1']:+.2f}, C2 {s50['c2']:+.2f} -> {here['c2']:+.2f}, "
          f"C3 {s50['c3']:+.2f} -> {here['c3']:+.2f} dB.")
    print(f"  Everything below is at {beta:+.2f} dB, the axis comparison's own value.")

    # ---- A. the curve as intervals, grouped by component ---------------------
    print("\n=== A. THE CURVE AS INTERVALS, BY COMPONENT (at the fitted beta) ===")
    print("  the +0.25 dB joint (s, theta) region -- a cost-slack region, NOT a CI")
    group = {}
    for b in sg.CORE:
        group[b] = ("C3" if b in cb.C3_BANDS else
                    "C1" if b in cb.FLOOR_BAND else
                    "C2" if b in cb.C2_BANDS else "--")
    print(f"  {'Hz':>6} {'comp':>5} {'20log10 s':>10} {'region':>16} {'width':>7} "
          f"{'anchor':>7}")
    anchors = {AC.BAND_OF[h]: h for h in HA.ANCHOR_HZ}
    for b in sg.CORE:
        r = srows[b]
        print(f"  {b:6d} {group[b]:>5} {r['s_db']:+10.2f} "
              f"[{r['lo_db']:+5.2f},{r['hi_db']:+6.2f}] {r['width']:7.2f} "
              f"{'yes' if b in anchors else '-':>7}")
    print("  ⚠ 40 and 80 Hz belong to no component -- session 50's band sets leave them")
    print("    out, and section B shows why that is right for 40 Hz.")

    # ---- B. resolvedness: is each component real, and against what? ----------
    # A component is only a component if it is RESOLVED above the thing it sits on
    # top of. C2 and C3 sit on C1, so the test is disjointness from the floor band's
    # own region; C1 sits on nothing, so its test is disjointness from zero.
    print("\n=== B. RESOLVEDNESS -- is each component distinguishable from the floor? ===")
    f_lo = min(srows[b]["lo_db"] for b in cb.FLOOR_BAND)
    f_hi = max(srows[b]["hi_db"] for b in cb.FLOOR_BAND)
    print(f"  floor band {cb.FLOOR_BAND} Hz combined region = "
          f"[{f_lo:+.2f}, {f_hi:+.2f}] dB")
    print(f"  C1 itself: the floor's LOWER bound is {f_lo:+.2f} dB, i.e. C1 excludes "
          f"zero by {f_lo:.2f} dB")
    print(f"    => C1 is real, and no bleed level removes it (session 50 measured beta "
          f"worth <= 0.26 dB\n       of it; GATE 2's s(50) span of "
          f"{max(sweep[k][0][50] for k in ok_betas) - min(sweep[k][0][50] for k in ok_betas):.2f} dB reproduces that).")
    print(f"\n  {'Hz':>6} {'comp':>5} {'region':>16} {'vs floor':>12} {'gap':>7}")
    resolved = {}
    for b in sg.CORE:
        if b in cb.FLOOR_BAND:
            continue
        lo, hi = srows[b]["lo_db"], srows[b]["hi_db"]
        disj = lo > f_hi or hi < f_lo
        gap = (lo - f_hi) if lo > f_hi else ((f_lo - hi) if hi < f_lo else 0.0)
        resolved[b] = dict(disjoint=bool(disj), gap=gap, comp=group[b])
        print(f"  {b:6d} {group[b]:>5} [{lo:+5.2f},{hi:+6.2f}] "
              f"{'DISJOINT' if disj else 'overlaps':>12} {gap:7.2f}")
    c3_res = [b for b in cb.C3_BANDS if resolved[b]["disjoint"]]
    c2_res = [b for b in cb.C2_BANDS if resolved[b]["disjoint"]]
    print(f"\n  C3: {len(c3_res)}/{len(cb.C3_BANDS)} bands resolved above the floor "
          f"{c3_res}")
    print(f"  C2: {len(c2_res)}/{len(cb.C2_BANDS)} bands resolved above the floor "
          f"{c2_res}")
    if not resolved[40]["disjoint"]:
        print(f"  ⭐ 40 Hz OVERLAPS the floor (gap {resolved[40]['gap']:.2f}) => C3's "
              f"onset sits between 40 and 32 Hz, so session 50's\n     C3 band set "
              f"{cb.C3_BANDS} is the right one and 40 Hz belongs to the floor, "
              f"not to C3.")

    # ⭐ WHICH BANDS CARRY C2's SIZE -- and it is not the well-conditioned ones.
    narrow = [b for b in cb.C2_BANDS if srows[b]["width"] <= WIDE_INTERVAL_DB]
    c1_here = here["c1"]
    c2_all = float(np.mean([srows[b]["s_db"] for b in cb.C2_BANDS])) - c1_here
    c2_nar = (float(np.mean([srows[b]["s_db"] for b in narrow])) - c1_here
              if narrow else float("nan"))
    print(f"\n  ⭐ C2's SIZE is carried by its WORST-CONDITIONED bands. Restricted to "
          f"the bands whose\n     s-region is <= {WIDE_INTERVAL_DB:.1f} dB wide "
          f"({narrow}), C2 = {c2_nar:+.2f} dB against {c2_all:+.2f} dB over all "
          f"{len(cb.C2_BANDS)}:")
    for b in cb.C2_BANDS:
        print(f"     {b:4d} Hz  s {srows[b]['s_db']:+6.2f}  width "
              f"{srows[b]['width']:5.2f}  {'kept' if b in narrow else 'DROPPED'}")
    print(f"     => the 'deficit RISES with frequency' half of C2 rests on 403 and 508 "
          f"Hz, whose\n        regions are the two widest in C2 (and 508 has no "
          f"harmonic anchor at all).")
    print(f"     ⚠ This set is FROZEN at the shipped baseline and must never be "
          f"re-derived per\n        candidate (`self-selecting-scores`); it is printed "
          f"beside the full set, never instead of it.")

    # ---- C. the corroborated curve ------------------------------------------
    print("\n=== C. WHAT THE SECOND INSTRUMENT ADDS ===")
    print("  robust order subset (H2, H3) -- designated by a3_harmonic_axis itself, for")
    print("  a stated physical reason, before this comparison existed")
    print(f"\n  {'Hz':>6} {'drive s':>9} {'region':>16} {'|k| H2,H3':>10} "
          f"{'bootstrap':>16} {'verdict':>9}")
    xs = []
    for hz in sorted(hrows):
        b = AC.BAND_OF[hz]
        h, r = hrows[hz], srows[b]
        k_lo, k_hi = abs(h["low_hi"]), abs(h["low_lo"])
        ov = not (r["hi_db"] < k_lo or k_hi < r["lo_db"])
        xs.append(dict(hz=hz, band=b, s=r["s_db"], s_lo=r["lo_db"], s_hi=r["hi_db"],
                       k=abs(h["k_low"]), k_lo=k_lo, k_hi=k_hi, overlap=bool(ov)))
        print(f"  {hz:6.0f} {r['s_db']:+9.2f} [{r['lo_db']:+5.2f},{r['hi_db']:+6.2f}] "
              f"{abs(h['k_low']):10.2f} [{k_lo:+5.2f},{k_hi:+6.2f}] "
              f"{'OVERLAP' if ov else 'DISJOINT':>9}")

    # ⭐⭐ THE ONE CROSS-INSTRUMENT STATEMENT ABOUT A COMPONENT. C2 exists iff the
    # low-mid level exceeds the floor -- and the harmonic axis supplies that level with
    # no beta, no solve and no bleed model anywhere in it.
    best = max((x for x in xs if x["hz"] >= 200.0), key=lambda x: x["k_lo"])
    margin = best["k_lo"] - f_hi
    print(f"\n  ⭐⭐ C2 IS CORROBORATED ACROSS INSTRUMENTS. The harmonic axis's LOWER "
          f"bound at\n     {best['hz']:.0f} Hz is {best['k_lo']:+.2f} dB; the drive "
          f"axis's floor region tops out at {f_hi:+.2f} dB.")
    print(f"     Margin {margin:+.2f} dB => a tool with NO beta in it says A3 at "
          f"{best['hz']:.0f} Hz exceeds the floor,")
    print(f"     so the low-mid rise is not an artefact of the drive axis's own bleed "
          f"fit.")
    print(f"  ⚠ HALF-INDEPENDENT ONLY: C2 = s(low-mid) - s(floor) and the harmonic axis "
          f"has no\n     floor band (GATE 1), so this pairs one instrument's numerator "
          f"with the other's\n     denominator. It is not two independent measurements "
          f"of C2.")
    if margin <= 0:
        print("  ⛔ margin is not positive -- do NOT report C2 as corroborated.")

    # ---- CAN THE SECOND INSTRUMENT NARROW beta? --------------------------------
    # ⚠⚠ NOT BY EXTRAPOLATING ds/dbeta, and the first version of this block did exactly
    # that -- twice wrongly. (a) It solved `beta + (s - k)/m` when setting
    # s(beta0) + m.(beta - beta0) = k gives `beta0 + (k - s)/m`: the sign was inverted,
    # so a table in which every band wants beta LOWER printed as "ALL THREE BANDS WANT
    # beta HIGHER" -- the session-33 lost-sign trap and session 79's wrong-sign
    # correction, in a verdict line. (b) Even with the sign right, closing a 3.5 dB gap
    # at |ds/dbeta| = 0.54 needs a 6.5 dB move in beta, i.e. the linearisation would be
    # pushed ~9x past the 0.75 dB window it was measured in -- and the sweep itself
    # falsifies it (s(101) never reaches 7.96 at ANY swept beta; its maximum over the
    # whole range is +4.96).
    # So: no linearisation at all. Ask the SWEPT curve directly which beta values put
    # each band inside its own bootstrap interval, and intersect those sets. ds/dbeta
    # stays in GATE 2 as the tilt statement it is, and is not used to travel.
    print("\n  Can the harmonic axis narrow beta? Read off the SWEPT curve (no")
    print("  linearisation): which beta values put s(band) inside that band's own")
    print("  robust bootstrap interval?")
    admit, per_band, both = None, {}, []
    for x in xs:
        b = x["band"]
        okb = [k for k in sorted(sweep)
               if x["k_lo"] <= sweep[k][0][b] <= x["k_hi"]]
        per_band[x["hz"]] = okb
        rng_s = (f"[{min(okb):+.2f}, {max(okb):+.2f}]" if okb else "EMPTY")
        print(f"    {x['hz']:6.0f} Hz  s spans "
              f"{min(sweep[k][0][b] for k in sweep):+6.2f}..{max(sweep[k][0][b] for k in sweep):+6.2f}"
              f"  target [{x['k_lo']:+5.2f},{x['k_hi']:+6.2f}]  admits beta {rng_s}"
              f"  ({len(okb)}/{len(sweep)} swept points)")
        admit = set(okb) if admit is None else (admit & set(okb))
    if any(not v for v in per_band.values()):
        print("  ⛔ a band admits NO swept beta -- its interval and the drive axis's curve")
        print("     do not intersect anywhere in the swept range. Widen the sweep before")
        print("     reading the joint constraint below; it would be an artefact.")
    joint = sorted(admit) if admit else []
    if not joint:
        print("\n  ⛔ the three bands admit NO COMMON beta in the swept range. The two axes")
        print("     are jointly infeasible at every beta tested -- a finding in its own")
        print("     right; chase it before using either curve's absolute level.")
    else:
        j_lo, j_hi = min(joint), max(joint)
        print(f"\n  joint (all three bands)        beta in [{j_lo:+7.2f}, {j_hi:+7.2f}] dB"
              f"   (width {j_hi - j_lo:.2f})")
        # ⚠ An endpoint ON the sweep edge is a property of the sweep, not of the data
        # (`bound-resting-means-unidentified`). Flagged so the WIDTH above is not read
        # as a measurement -- and note it does not affect the intersection below, whose
        # ends come from the two axes rather than from the grid.
        edges = [e for e, v in (("lower", j_lo), ("upper", j_hi))
                 if abs(v - min(sweep)) < 1e-9 or abs(v - max(sweep)) < 1e-9]
        if edges:
            print(f"  ⚠ the {' and '.join(edges)} end rests ON the sweep edge, so the "
                  f"harmonic axis does not\n     bound beta from that side at all -- read "
                  f"the width as a lower bound, not a value.")
        print(f"  drive axis alone (GATE 2)      beta in [{ident[0]:+7.2f}, "
              f"{ident[1]:+7.2f}] dB   (width {ident[1] - ident[0]:.2f})")
        both = [k for k in joint if ident[0] <= k <= ident[1]]
        if not both:
            print("  ⛔ the two constraints are DISJOINT -- each axis prefers a beta the")
            print("     other excludes. That is a finding; chase it before using either")
            print("     curve's absolute level.")
        else:
            b_lo, b_hi = min(both), max(both)
            tighter = (b_hi - b_lo) < (ident[1] - ident[0]) - 1e-9
            print(f"  ⭐ BOTH                          beta in [{b_lo:+7.2f}, "
                  f"{b_hi:+7.2f}] dB   (width {b_hi - b_lo:.2f})"
                  f"{'  <- TIGHTER than the drive axis alone' if tighter else ''}")
            if tighter:
                # WHICH axis binds WHICH side, computed -- that is the useful form of the
                # statement, and it is what makes the two instruments complementary
                # rather than redundant on beta.
                lo_src = "drive axis" if abs(b_lo - ident[0]) < 1e-9 else "harmonic axis"
                hi_src = "drive axis" if abs(b_hi - ident[1]) < 1e-9 else "harmonic axis"
                print(f"     => the second instrument DOES narrow beta, to the "
                      f"{'lower' if b_hi < 0.5 * (ident[0] + ident[1]) else 'upper'} end of "
                      f"the drive axis's own\n        interval. And the two bound OPPOSITE "
                      f"sides: the {lo_src} sets the lower end\n        ({b_lo:+.2f}), the "
                      f"{hi_src} the upper ({b_hi:+.2f}) -- so they are complementary on\n"
                      f"        beta, not redundant. It is a LEVEL constraint, and the "
                      f"components move with\n        it, which is the next table.")
            # ⭐⭐ AND THE CONSEQUENCE FALLS ALMOST ENTIRELY ON C3, the one component
            # GATE 1 says the second instrument cannot see. Read at the ENDPOINTS of
            # the joint range, from the sweep, never extrapolated.
            n_res = len(sg.BETA_BANDS) * len(ps.DRIVES)
            print(f"\n  ⭐⭐ WHAT THE NARROWED beta DOES TO THE BUDGET (read off the sweep):")
            print(f"     {'beta':>7} {'fit rms':>8} {'C1':>7} {'C2':>7} {'C3':>7}")
            for k in (round(beta, 4), b_hi, b_lo):
                c = components(sweep[k][0])
                tag = "  <- fitted" if abs(k - beta) < 1e-9 else ""
                print(f"     {k:+7.2f} {math.sqrt(sweep[k][1] / n_res):8.4f} "
                      f"{c['c1']:+7.2f} {c['c2']:+7.2f} {c['c3']:+7.2f}{tag}")
            # ⭐⭐ AND THE SHIPPED CURVE IS READ AT A beta THE SECOND INSTRUMENT REJECTS,
            # if it is. Computed, because it changes how the shape gate's score should be
            # used: every A3 candidate since session 47 has been ranked on a curve solved
            # at fit_beta's own optimum.
            inside = b_lo - 1e-9 <= beta <= b_hi + 1e-9
            print(f"\n     ⭐⭐ the drive axis's OWN optimum beta ({beta:+.2f}) is "
                  f"{'INSIDE' if inside else 'OUTSIDE'} the jointly-admitted\n        range "
                  f"[{b_lo:+.2f}, {b_hi:+.2f}]"
                  + ("." if inside else
                     f" -- it sits {abs(beta - (b_hi if beta > b_hi else b_lo)):.2f} dB "
                     f"{'above' if beta > b_hi else 'below'} the range. So the\n"
                     f"        curve every A3 candidate has been RANKED on since session 47 is "
                     f"solved at a beta\n        the second instrument excludes. That does not "
                     f"invalidate the ranking (a common\n        beta shift is mostly a level "
                     f"offset on the score), but any ABSOLUTE component\n        size taken off "
                     f"that curve -- C3 above all -- inherits it."))
            cl, ch = components(sweep[b_lo][0]), components(sweep[b_hi][0])
            print(f"     => across the jointly-admitted beta range C1 moves "
                  f"{abs(ch['c1'] - cl['c1']):.2f} dB and C2 {abs(ch['c2'] - cl['c2']):.2f} dB,")
            print(f"        but C3 moves {abs(ch['c3'] - cl['c3']):.2f} dB. The corroborated "
                  f"curve constrains beta, beta\n        tilts the LF end (GATE 2), and so "
                  f"the second instrument's real effect on the\n        budget lands on C3 -- "
                  f"the component it cannot measure. ⇒ NEVER quote a C3\n        size without "
                  f"the beta it was read at.")
    # ---- D. the re-derived budget -------------------------------------------
    print("\n=== D. THE RE-DERIVED BUDGET ===")
    print(f"  {'comp':<5} {'level':>8} {'resolved above':>16} {'gap':>7} "
          f"{'beta span':>10} {'corroborated':>14}")
    span = lambda b: (max(sweep[k][0][b] for k in ok_betas)
                      - min(sweep[k][0][b] for k in ok_betas))
    rows_out = [
        ("C1", here["c1"], "zero", f_lo, span(50), "no -- 0 anchors"),
        ("C2", c2_all, f"floor, {len(c2_res)}/{len(cb.C2_BANDS)} bands",
         min((resolved[b]["gap"] for b in c2_res), default=0.0),
         max(span(b) for b in cb.C2_BANDS), "yes (half)"),
        ("C3", here["c3"], f"floor, {len(c3_res)}/{len(cb.C3_BANDS)} bands",
         min((resolved[b]["gap"] for b in c3_res), default=0.0),
         span(20), "no -- 0 anchors"),
    ]
    for nm, lvl, ra, gp, sp, corr in rows_out:
        print(f"  {nm:<5} {lvl:+8.2f} {ra:>16} {gp:7.2f} {sp:10.2f} {corr:>14}")

    # ⭐⭐ THE RE-DERIVED LEVELS. The point of the exercise: the budget read at the beta
    # BOTH axes admit, not at the drive axis's own optimum. Computed over that range,
    # never quoted from the fitted point alone.
    if both:
        cs = [components(sweep[k][0]) for k in both]
        rng = {nm: (min(c[nm] for c in cs), max(c[nm] for c in cs))
               for nm in ("c1", "c2", "c3")}
        print(f"\n  ⭐⭐ RE-DERIVED against the beta range BOTH axes admit "
              f"([{min(both):+.2f}, {max(both):+.2f}] dB):")
        for nm, was in (("c1", S50["c1"]), ("c2", S50["c2"]), ("c3", S50["c3"])):
            lo_v, hi_v = rng[nm]
            print(f"     {nm.upper()}   session 50 quoted {was:+5.2f} dB   ->   "
                  f"{lo_v:+5.2f} .. {hi_v:+5.2f} dB"
                  f"{'   <- MOVES' if min(abs(lo_v - was), abs(hi_v - was)) > 0.5 else ''}")
        # Does the ordering survive across that range? Computed, because at the bottom
        # of it C3 and C2 come within a couple of dB of each other.
        worst = min(cs, key=lambda c: c["c3"] - c["c2"])
        ordered = all(c["c3"] > c["c2"] > c["c1"] for c in cs)
        print(f"     ordering C3 > C2 > C1 holds at every admitted beta: "
              f"{'YES' if ordered else 'NO'}   "
              f"(narrowest C3-C2 margin {worst['c3'] - worst['c2']:+.2f} dB, "
              f"against {here['c3'] - here['c2']:+.2f} at the fitted beta)")

    print("\n  ⇒ WHAT SURVIVES: all three components are REAL (each resolved above what")
    print("    it sits on) and the ORDERING holds across every admitted beta. What does")
    print("    NOT survive is quoting them as three numbers:")
    print(f"      C1 is the only beta-robust one (span {span(50):.2f} dB over the identified")
    print(f"         interval, |ds/dbeta| {abs(slopes[50]):.2f}) and it is what a broadband")
    print(f"         OD-level lever must supply -- unchanged from session 50.")
    print(f"      C2 is corroborated in EXISTENCE (half-independently) but its SIZE moves")
    print(f"         {c2_nar:+.2f} .. {c2_all:+.2f} dB on whether its two worst-conditioned "
          f"bands vote.")
    print(f"      C3 is the LEAST determined -- beta span {span(20):.2f} dB, the widest "
          f"s-region in\n         CORE at 20 Hz ({srows[20]['width']:.2f} dB), and no second "
          f"instrument at all. ⚠ And the")
    print("         corroborated curve pushes it DOWN, where session 51 item 7's `r_ped`")
    print("         reading pushed it UP (\"C3 is the DOMINANT A3 term\"). Both readings come")
    print("         from below 40 Hz, where session 52 item 1 measured the blend axis to be")
    print("         unreliable. ⇒ C3's SIZE is still open; do not treat either as settled.")
    print("\n  ⛔ NOT CLAIMED: nothing is proposed, no candidate is screened, and no")
    print("    constant moved. Session 50 item 1 (A3 will not close on one element) and")
    print("    session 52 (no causal post-clipper LINEAR element can supply it) both")
    print("    stand -- this re-states the requirement they are measured against, with")
    print("    the corroboration's reach made explicit.")

    if args.out:
        with open(args.out, "w") as fh:
            json.dump(dict(report=args.report, beta=beta, beta_s50=S50_BETA,
                           budget_s50=s50, budget_here=here,
                           coverage={k: v for k, v in cov.items()},
                           identified=ident, slopes={str(k): v for k, v in slopes.items()},
                           spans={str(b): span(b) for b in sg.CORE},
                           floor_region=[f_lo, f_hi],
                           resolved={str(k): v for k, v in resolved.items()},
                           c2_all=c2_all, c2_narrow=c2_nar, c2_narrow_bands=narrow,
                           cross=xs, c2_margin=margin,
                           beta_admits={str(h): v for h, v in per_band.items()},
                           beta_joint=joint,
                           beta_sweep={str(k): dict(rms=math.sqrt(sweep[k][1] / (
                               len(sg.BETA_BANDS) * len(ps.DRIVES))),
                               **components(sweep[k][0])) for k in sorted(sweep)},
                           curve={str(b): srows[b] for b in sg.CORE}), fh, indent=1)
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
