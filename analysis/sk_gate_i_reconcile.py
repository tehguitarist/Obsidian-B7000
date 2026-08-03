#!/usr/bin/env python3.11
"""GATE AC — does item 6's Sallen-Key sub-target REFUTE GATE I, or is it a separate mechanism?

Session 131.  Session 130's `NEXT` #3, which explicitly GATES its own #1:

    "Re-examine whether the 8-16.3 kHz gated rows are the same finding.  A drive-dependent fall
     in the model's effective HF bandwidth is the *opposite* sign to GATE I's measurement (the
     pedal GAINS with frequency under drive where our path rolls off).  Those two must be
     reconciled before an SK-bandwidth candidate is built -- they may be the same mechanism seen
     from two ends, or they may refute each other.  This is a cheap read against a passing gate."

THE TENSION, STATED PRECISELY
-----------------------------
GATE AB6 sized item 6's treble-peak half as **Sallen-Key time constants x 1.1113** (SK corners
-10.01 %), applied ACROSS THE DRIVE LADDER -- i.e. the model needs a drive-dependent mechanism
that rolls its HF off HARDER as drive rises, so the 2935 Hz peak walks DOWN with the pedal's.

GATE I measures, on the same quantity class, that over 8127.5 -> 16255 Hz the PEDAL gains with
frequency at the hottest stimulus while OUR path rolls off, the gap growing monotonically with
drive -- i.e. the model needs MORE HF as drive rises, not less.

Both are read off the FUNDAMENTAL transfer.  GATE W/AB locate centres on `transfer_h1`;
`comprehensive_report`'s default FR method is `h1band` (H1, power-averaged per band), which is
what GATE I's rates are computed from.  So this is not two different quantities talking past each
other -- it is one axis with two demands on it, and their signs must be compared.

WHAT THIS TOOL SETTLES
----------------------
AC1  KNOWN ANSWERS, two, and both are cross-implementation rather than self-referential.
     (a) `hf_artefact_gate.sk_mag_db` and `bt_pair_shape_gate.sallen_key` are two independently
         written transcriptions of the same two schematic-verified stages; they must agree on the
         octave rate.  Agreement certifies BOTH before either is used.
     (b) the cascade at sk_scale = 1 must reproduce s125's closed-form peak (GATE AB's AB1).

AC2  SEPARABILITY -- the claim that makes AC3 assumption-light.  Transfers cascade
     multiplicatively, so in dB every unchanged stage CANCELS in a delta.  The perturbation
     touches only the SK pair, so the collateral in GATE I's octave is EXACTLY the SK-only delta,
     independent of the treble ladder, C7, the GRUNT bank, the bridged-T, the EQ and the pots.
     That is asserted numerically (full cascade vs SK alone), not argued.

AC3  THE COLLATERAL, SIZED.  What AB6's SK move does to the model's octave rate and to its
     16255 Hz level, quoted against GATE I's own measured gap on the current baseline.

AC4  DIRECTION, as a COMPARISON against the target and not as a property of the candidate
     (AB5's defect, s130: a classifier whose predicate does not contain the target is narration).

AC5  THE REACHABILITY BOUND.  Can ANY sk_scale close GATE I's gap?  The SK pair's whole
     contribution to this octave is bounded, so deleting it outright is the best this axis can
     ever do -- and that bound is computed and compared against the requirement, per cell.

AC6  THE OTHER AXIS.  AB6 asks for a bridged-T move too; its collateral in the same octave is
     computed rather than assumed negligible.

WHAT IT DOES NOT CLAIM
----------------------
* It is CLOSED-FORM on the post-clipper cascade.  No render, no capture, no constant.  A dB
  delta on the linear post-clipper path is NOT a prediction of the matrix's graded change --
  the graded rows sit downstream of a per-row null gain and of a nonlinearity.  AC3 sizes a
  mechanism, it does not price a render.
* It says nothing about whether the 8-16.3 kHz bands SHOULD be graded.  GATE I calls that a
  USER DECISION and this tool does not reopen it.
* "The pedal gains with frequency" is GATE I's measurement, carried here.  The MECHANISM noun
  for it is still unnamed (s125: G3 refutes the fs/(N+1) fold, and "aliasing" was never
  measured).  Nothing below supplies one.

Run:
    python3.11 analysis/sk_gate_i_reconcile.py analysis/reports/s124_ship.json
    python3.11 analysis/sk_gate_i_reconcile.py REPORT.json --json analysis/reports/s131_ac.json
"""
import argparse
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bt_pair_shape_gate as AB                        # noqa: E402
import hf_artefact_gate as HI                          # noqa: E402

# AB6's solved multipliers.  Read from GATE AB's stored result when it is present, and
# RECOMPUTED from AB's own sensitivities otherwise -- never transcribed
# (`rebuild-targets-dont-transcribe`).
AB_REPORT = "analysis/reports/s130_bt_pair.json"

# The one band in GATE I's octave whose error is drive-INDEPENDENT, i.e. a separate real defect
# that GATE I explicitly refuses to fold into the artefact story.
DRIVE_INDEP_BAND = HI.OCT_LO

SEP_TOL = 1e-9          # dB -- AC2, two ways of computing one delta
KA_TOL = 1e-9           # dB/oct -- AC1a, two transcriptions of one network


def ok(flag):
    return "OK" if flag else "**FAIL**"


def ab6_multipliers():
    """-> (bt_mult, sk_mult, source).  Stored if available, else recomputed from AB's own
    sensitivity solve.  Either way the numbers come from GATE AB, not from this file."""
    if os.path.exists(AB_REPORT):
        d = json.load(open(AB_REPORT))
        dec = d.get("decomposition")
        if dec and "sk_mult" in dec and "bt_mult" in dec:
            return dec["bt_mult"], dec["sk_mult"], f"stored ({AB_REPORT})"
    bt = AB.sens(AB._all_bt, 1.10)
    sk = AB.sens(lambda k: dict(sk_scale=k), 1.10)
    if bt is None or sk is None:
        sys.exit("GATE AC REFUSED: GATE AB's sensitivity solve lost a feature, so AB6's "
                 "multipliers cannot be recovered and there is no candidate to reconcile.")
    A = np.array([[bt["notch"], sk["notch"]], [bt["peak"], sk["peak"]]])
    rhs = np.array([math.log1p(AB.PEDAL_DNOTCH), math.log1p(AB.PEDAL_DPEAK)])
    x = np.linalg.solve(A, rhs)
    return math.exp(x[0]), math.exp(x[1]), "recomputed from AB sensitivities"


def sk_pair_db(f, scale=1.0):
    """|H| of the post-clipper SK pair alone, dB, at time-constant multiplier `scale`."""
    h = AB.sallen_key(np.atleast_1d(np.asarray(f, dtype=float)), scale=scale, **AB.SK_B) \
        * AB.sallen_key(np.atleast_1d(np.asarray(f, dtype=float)), scale=scale, **AB.SK_A)
    return 20.0 * np.log10(np.abs(h))


def sk_octave_rate(scale=1.0):
    return float(sk_pair_db(HI.OCT_HI, scale)[0] - sk_pair_db(HI.OCT_LO, scale)[0])


def cascade_db(f, **kw):
    h = AB.cascade(np.atleast_1d(np.asarray(f, dtype=float)), **kw)
    return 20.0 * np.log10(np.abs(h))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report", help="a comprehensive_report JSON (GATE I's own input)")
    ap.add_argument("--json", default=None, help="write the full result set here")
    ap.add_argument("--sk-bound-decades", type=float, default=4.0,
                    help="how far AC5 sweeps sk_scale below 1 when bounding the axis")
    args = ap.parse_args()

    out = {"report": args.report}
    fail = []

    print(f"### GATE AC — item 6's Sallen-Key sub-target vs GATE I   [{args.report}]")

    # ------------------------------------------------------------------ AC0
    print("\n=== AC0  PROVENANCE — what is being reconciled, and where each side comes from ===")
    bt_mult, sk_mult, src = ab6_multipliers()
    print(f"  candidate (GATE AB6, {src}):")
    print(f"    Sallen-Key time constants   x {sk_mult:.4f}   "
          f"(SK corners {100 * math.expm1(-math.log(sk_mult)):+.2f} %)")
    print(f"    bridged-T time constants    x {bt_mult:.4f}   ({100 * (bt_mult - 1):+.2f} %)")
    print(f"  reference (GATE I): rate over {HI.OCT_LO:.1f} -> {HI.OCT_HI:.1f} Hz, "
          f"h1band, bleed-free full-send OD")
    print("  ⚠ CLOSED-FORM on the post-clipper cascade. No render, no capture, no constant.")
    out["candidate"] = dict(sk_mult=sk_mult, bt_mult=bt_mult, source=src)

    d, bands, lo_i, hi_i = HI.band_octave(args.report)
    acc, dropped = HI.collect(d, bands, lo_i, hi_i)
    ncap = len(d["captures"])
    print(f"\n  report carries {ncap} captures; GATE I's octave is bands "
          f"{bands[lo_i]:.1f} -> {bands[hi_i]:.1f} Hz")
    od_classes = [k for k in HI.CLASSES if k.startswith("OD")]
    for k in od_classes:
        n = len(acc[k][HI.SWEEPS[0]][4]) if k in acc else 0
        print(f"    {k:<34} n = {n}")
        if n == 0:
            fail.append("AC0")
    if "AC0" in fail:
        sys.exit("GATE AC REFUSED: an OD class is EMPTY -- there is no measured gap to reconcile "
                 "against (`empty-gate-must-fail`).")

    # ------------------------------------------------------------------ AC1
    print("\n=== AC1  KNOWN ANSWERS — cross-implementation, not self-referential ===")
    mine = sk_octave_rate(1.0)
    theirs = HI.drawn_rate()
    ka_a = abs(mine - theirs) <= KA_TOL
    print(f"  AC1a  the SK pair's own rate across this octave, computed twice from the same")
    print(f"        schematic values by two independently-written transcriptions:")
    print(f"          bt_pair_shape_gate.sallen_key  {mine:+.6f} dB/oct")
    print(f"          hf_artefact_gate.sk_mag_db     {theirs:+.6f} dB/oct")
    print(f"          |diff| {abs(mine - theirs):.2e} (<= {KA_TOL:g}) ... {ok(ka_a)}")
    if not ka_a:
        fail.append("AC1a")

    base = AB.features()
    ka_b = base is not None and abs(base["peak"] / AB.S125_PEAK_HZ - 1.0) < 0.02
    if base is None:
        print("  AC1b  the cascade lost a feature at sk_scale = 1 ... **FAIL**")
        fail.append("AC1b")
    else:
        print(f"\n  AC1b  cascade baseline (inherited from GATE AB's AB1):")
        print(f"          peak {base['peak']:.2f} Hz vs s125's closed form {AB.S125_PEAK_HZ:.1f} "
              f"({100 * (base['peak'] / AB.S125_PEAK_HZ - 1):+.2f} %) ... {ok(ka_b)}")
        if not ka_b:
            fail.append("AC1b")
    out["known_answers"] = dict(sk_rate_ab=mine, sk_rate_hi=theirs,
                                baseline_peak=None if base is None else base["peak"])

    if fail:
        print("\n" + "=" * 96)
        print(f"GATE AC: REFUSED — {', '.join(fail)} failed. Nothing below is quotable.")
        print("=" * 96)
        sys.exit(2)

    # ------------------------------------------------------------------ AC2
    print("\n=== AC2  SEPARABILITY — the collateral is EXACTLY the SK-only delta ===")
    print("  Transfers cascade multiplicatively, so in dB every unchanged stage cancels in a")
    print("  delta. Asserted numerically rather than argued: the same perturbation, differenced")
    print("  through the FULL cascade and through the SK pair alone, must agree.")
    d_full = float((cascade_db(HI.OCT_HI, sk_scale=sk_mult) - cascade_db(HI.OCT_LO, sk_scale=sk_mult))[0]
                   - (cascade_db(HI.OCT_HI) - cascade_db(HI.OCT_LO))[0])
    d_sk = sk_octave_rate(sk_mult) - sk_octave_rate(1.0)
    sep = abs(d_full - d_sk)
    print(f"\n    through the full cascade   {d_full:+.6f} dB/oct")
    print(f"    through the SK pair alone  {d_sk:+.6f} dB/oct")
    print(f"    |diff| {sep:.2e} (<= {SEP_TOL:g}) ... {ok(sep <= SEP_TOL)}")
    print("  ⇒ the number below does not depend on the treble ladder, C7, the GRUNT bank, the")
    print("    bridged-T, the EQ or any pot position. It is a property of the two SK stages.")
    if sep > SEP_TOL:
        fail.append("AC2")
        print("  ⚠ AC3 is NOT readable while this fails — the delta is not separable.")
    out["separability"] = dict(full=d_full, sk_only=d_sk, diff=sep)

    # ------------------------------------------------------------------ AC3
    print("\n=== AC3  THE COLLATERAL, SIZED — AB6's SK move inside GATE I's octave ===")
    lvl_hi = float(sk_pair_db(HI.OCT_HI, sk_mult)[0] - sk_pair_db(HI.OCT_HI, 1.0)[0])
    lvl_lo = float(sk_pair_db(HI.OCT_LO, sk_mult)[0] - sk_pair_db(HI.OCT_LO, 1.0)[0])
    print(f"  at SK tau x {sk_mult:.4f}, applied at the hottest rung (it is drive-dependent by")
    print(f"  construction, so it is INERT at the clean rung and full-size here):")
    print(f"    octave rate      {d_sk:+.3f} dB/oct")
    print(f"    level @ {HI.OCT_LO:7.1f} Hz  {lvl_lo:+.3f} dB")
    print(f"    level @ {HI.OCT_HI:7.1f} Hz  {lvl_hi:+.3f} dB")
    out["collateral"] = dict(d_rate=d_sk, d_lvl_lo=lvl_lo, d_lvl_hi=lvl_hi)

    # GATE I's measured gap, live, per class, at the hottest rung.
    hot = HI.SWEEPS[-1]
    gaps = {}
    print(f"\n  GATE I's measured gap at {hot} on this report (pedal - model, dB/oct):")
    for k in od_classes:
        pr, mr = acc[k][hot][0], acc[k][hot][1]
        if not pr:
            continue
        gaps[k] = dict(pedal=float(np.median(pr)), model=float(np.median(mr)),
                       gap=float(np.median(pr) - np.median(mr)),
                       worst_gap=float(max(p - m for p, m in zip(pr, mr))),
                       n=len(pr))
        g = gaps[k]
        print(f"    {k:<30} n={g['n']}  pedal {g['pedal']:+6.2f}  model {g['model']:+6.2f}"
              f"   gap {g['gap']:+6.2f}   (worst cell {g['worst_gap']:+6.2f})")
    out["gate_i_gap"] = gaps
    ref_gap = max(g["gap"] for g in gaps.values())
    print(f"\n    widest class gap at the hottest rung: {ref_gap:+.2f} dB/oct")
    print(f"    AB6's SK move is {100 * abs(d_sk) / ref_gap:.1f} % of that, and it adds to it.")

    # ------------------------------------------------------------------ AC4
    print("\n=== AC4  DIRECTION — a comparison against the TARGET, not a property of the candidate ===")
    print("  (AB5's own defect, s130: a classifier whose predicate does not contain the target")
    print("   gives the right answer only for the target it was written against.)")
    print()
    # Target for each axis: the signed change the MODEL must make to reach the pedal.
    tgt_rate = ref_gap                                   # model rate must RISE by this
    tgt_peak = AB.PEDAL_DPEAK                            # model peak must FALL by this fraction
    cand = AB.features(sk_scale=sk_mult)
    if cand is None:
        print("  NOT MEASURABLE — the candidate lost the peak. Direction is undefined.")
        fail.append("AC4")
        d_peak = float("nan")
    else:
        d_peak = cand["peak"] / base["peak"] - 1.0
    print(f"  ⚠ the candidate column is the SK axis ALONE (sk tau x {sk_mult:.4f}), which is the")
    print(f"    axis under reconciliation. AB6's combination reads a smaller peak move ({100 * (AB.features(**{**AB._all_bt(bt_mult), 'sk_scale': sk_mult})['peak'] / base['peak'] - 1):+.2f} %)")
    print(f"    because the bridged-T half pushes the peak back the other way. Do not diff them.")
    print()
    rows = (("treble peak position", d_peak, tgt_peak, "%"),
            ("8-16.3 kHz octave rate", d_sk, tgt_rate, "dB/oct"))
    print(f"    {'axis':<24} {'candidate':>12} {'target':>12}  {'sign product':>13}  verdict")
    agree = {}
    for name, c, t, unit in rows:
        sp = math.copysign(1.0, c) * math.copysign(1.0, t)
        a = sp > 0
        agree[name] = a
        cs = f"{100 * c:+.2f} %" if unit == "%" else f"{c:+.2f}"
        ts = f"{100 * t:+.2f} %" if unit == "%" else f"{t:+.2f}"
        print(f"    {name:<24} {cs:>12} {ts:>12}  {sp:>13.0f}  "
              f"{'TOWARD' if a else 'AWAY'}")
    out["direction"] = {k: bool(v) for k, v in agree.items()}
    print()
    both = all(agree.values())
    print(f"  ⇒ the SK axis moves the model {'TOWARD' if both else 'TOWARD one target and AWAY from the other'}.")
    if not both:
        print("    The two demands on this one knob are OPPOSITE-SIGNED: item 6 wants the SK")
        print("    corners DOWN (peak walks down with drive); GATE I wants more top-octave, which")
        print("    on this axis means the corners UP. A single SK mechanism cannot serve both.")

    # ------------------------------------------------------------------ AC5
    print("\n=== AC5  REACHABILITY BOUND — can ANY sk_scale close GATE I's gap? ===")
    print("  The SK pair's entire contribution to this octave is finite, so making it fully")
    print("  transparent is the most this axis can ever give back. That bound is computed, not")
    print("  assumed, by sweeping the multiplier down until the contribution stops moving.")
    sk1 = sk_octave_rate(1.0)
    scales = np.logspace(-args.sk_bound_decades, 0.0, 9)
    print(f"\n    {'sk tau x':>12}  {'SK rate':>10}  {'adds to path':>13}")
    for s in scales:
        r = sk_octave_rate(float(s))
        print(f"    {s:12.2e}  {r:+10.3f}  {r - sk1:+13.3f}")
    # The bound is the CHANGE in the SK pair's contribution, i.e. what the model's whole-path
    # rate gains -- NOT the contribution's endpoint value. Those differ by 18 dB/oct and the
    # first draft printed the endpoint under the bound's label, contradicting its own
    # parenthetical in the same breath (s122: a message that cannot be true is a defect even
    # when the guard around it is sound).
    resid = sk_octave_rate(float(scales[0]))
    bound = resid - sk1
    conv = abs(resid) <= 0.01
    print(f"\n    at the smallest multiplier the SK pair contributes {resid:+.4f} dB/oct, i.e. it")
    print(f"    has converged to transparent (|rate| <= 0.01) ... {ok(conv)}")
    if not conv:
        fail.append("AC5")
        print("    ⚠ the sweep has NOT converged, so `bound` is not a bound. Widen "
              "--sk-bound-decades.")
    print(f"    ⇒ upper bound on what this axis can add to the model's octave rate: "
          f"{bound:+.3f} dB/oct")
    print(f"      (= the SK pair's whole contribution, {sk1:+.3f} dB/oct, handed back)")

    # Per (class, rung), not per class at the hottest rung alone: a lever measured at one
    # stimulus rung is a claim about that rung (s126), and this gap has a dose-response.
    print(f"\n    required gap vs the bound, per class AND per rung (median of the class's cells):")
    print(f"    {'condition':<30} " + "".join(f"{sw.replace('sweep_', ''):>10}" for sw in HI.SWEEPS))
    reach, cells_ok, cells_n = {}, 0, 0
    for k in od_classes:
        row, per = [], {}
        for sw in HI.SWEEPS:
            pr, mr = acc[k][sw][0], acc[k][sw][1]
            if not pr:
                row.append("       —")
                continue
            need = float(np.median(pr) - np.median(mr))
            per[sw] = dict(required=need, reachable=bool(need <= bound))
            row.append(f"{need:+10.2f}")
            for p, m in zip(pr, mr):
                cells_n += 1
                cells_ok += 1 if (p - m) <= bound else 0
        reach[k] = per
        print(f"    {k:<30} " + "".join(row))
    print(f"    {'BOUND (SK deleted outright)':<30} " + "".join(f"{bound:+10.2f}" for _ in HI.SWEEPS))
    out["reachability"] = dict(bound=bound, per_class=reach,
                               cells_reachable=cells_ok, cells_total=cells_n)
    hot_reach = [k for k in od_classes if reach[k].get(hot, {}).get("reachable")]
    n_reach = len(hot_reach)
    print(f"\n  ⇒ at the hottest rung {n_reach} of {len(od_classes)} classes are reachable, and")
    print(f"    {cells_ok} of {cells_n} individual (condition, rung) cells across the whole ladder.")
    print(f"    Deleting the two Sallen-Keys ENTIRELY still leaves the hottest rung short by")
    print(f"    {min(reach[k][hot]['required'] for k in od_classes) - bound:+.2f} to "
          f"{max(reach[k][hot]['required'] for k in od_classes) - bound:+.2f} dB/oct.")
    print(f"    That is not a proposal — it removes the 2935 Hz peak and the OD path's whole")
    print(f"    bandlimit — it is the ceiling of the axis, and the gap is above it.")

    # ------------------------------------------------------------------ AC6
    print("\n=== AC6  THE OTHER AXIS — the bridged-T half's collateral in the same octave ===")
    bt_rate = float((cascade_db(HI.OCT_HI, **AB._all_bt(bt_mult))
                     - cascade_db(HI.OCT_LO, **AB._all_bt(bt_mult)))[0]
                    - (cascade_db(HI.OCT_HI) - cascade_db(HI.OCT_LO))[0])
    bt_lvl = float((cascade_db(HI.OCT_HI, **AB._all_bt(bt_mult)) - cascade_db(HI.OCT_HI))[0])
    print(f"  bridged-T tau x {bt_mult:.4f}:  octave rate {bt_rate:+.3f} dB/oct, "
          f"level @ {HI.OCT_HI:.1f} Hz {bt_lvl:+.3f} dB")
    ratio = abs(bt_rate) / abs(d_sk) if d_sk else float("inf")
    print(f"  ⇒ {ratio:.3f}x the SK half's rate collateral — the bridged-T is far above its own")
    print(f"    notch here and is nearly flat across this octave, so it carries almost none of")
    print(f"    the cost. AB6's two axes are as separable in THIS region as they are at the")
    print(f"    features (AB3), which is the same fact read at a third frequency.")
    out["bt_axis"] = dict(d_rate=bt_rate, d_lvl_hi=bt_lvl, ratio_of_sk=ratio)

    # ------------------------------------------------------------------ AC7
    print("\n" + "=" * 96)
    print("AC7  VERDICT — computed")
    print("=" * 96)
    same_mech = both
    print(f"\n  (a) ONE mechanism for both?  A single SK-axis mechanism would have to move both")
    print(f"      axes toward their targets. Measured: "
          f"{sum(agree.values())} of {len(agree)} axes move toward.")
    print(f"      => {'SAME MECHANISM — not refuted' if same_mech else 'REFUTED. The two findings demand OPPOSITE signs on this knob.'}")
    print(f"\n  (b) Is GATE I even reachable on this axis?  At the hottest rung, {n_reach} of")
    print(f"      {len(od_classes)} classes and {cells_ok} of {cells_n} cells over the whole ladder,")
    print(f"      at the axis's absolute ceiling (both Sallen-Keys deleted).")
    if n_reach == 0:
        print(f"      => NO at the hottest rung. GATE I's gap cannot be closed by ANY Sallen-Key")
        print(f"         setting there, so it needs a mechanism outside this axis whatever item 6")
        print(f"         does. ⚠ The bound is TIGHT, not comfortable — {bound:+.2f} dB/oct against a")
        print(f"         requirement of {min(reach[k][hot]['required'] for k in od_classes):+.2f}..."
              f"{max(reach[k][hot]['required'] for k in od_classes):+.2f} — so this refutes the AXIS,")
        print(f"         not the general idea that some of the region is a rolloff difference.")
        print(f"         The cells that ARE reachable are the quiet rungs, where the gap is small;")
        print(f"         that dose-response is GATE I's own G2c and is why a single rung cannot")
        print(f"         carry this verdict (s126).")
    print(f"\n  (c) ⇒ THE RECONCILIATION: the two findings do NOT refute each other, because they")
    print(f"      are not about the same mechanism CLASS. Item 6's SK sub-target is a FILTERING")
    print(f"      change; GATE I's gap needs a GENERATIVE one (the pedal gains where no filter")
    print(f"      can). What they DO share is one knob, with opposite signs on it — so the SK")
    print(f"      candidate carries a real, sized collateral cost in a region that is already")
    print(f"      over SHIP, and that cost must be quoted whenever it is proposed:")
    print(f"          {d_sk:+.3f} dB/oct and {lvl_hi:+.3f} dB at {HI.OCT_HI:.1f} Hz, at the hottest rung,")
    print(f"          against a measured gap of {ref_gap:+.2f} dB/oct ({100 * abs(d_sk) / ref_gap:.1f} %).")
    print(f"\n  ⚠ NOT priced: what that does to the GRADED rows. The matrix gain-matches per row")
    print(f"    and sits downstream of the clipper; a closed-form dB delta on the linear")
    print(f"    post-clipper path is a mechanism size, not a render result.")
    print(f"  ⚠ And the {DRIVE_INDEP_BAND:.1f} Hz band's error is drive-INDEPENDENT (GATE I's own")
    print(f"    caveat), while this candidate is drive-dependent BY CONSTRUCTION — so it can")
    print(f"    neither cause nor cure that part of the region.")
    out["verdict"] = dict(same_mechanism=bool(same_mech), n_reachable=n_reach,
                          n_conditions=len(reach), collateral_frac=abs(d_sk) / ref_gap)

    print("\n" + "=" * 96)
    if fail:
        print(f"GATE AC: REFUSED — {', '.join(fail)} did not pass. Nothing above them is quotable.")
    else:
        print("GATE AC: all guards passed. AC3-AC7 are readable.")
    print("=" * 96)

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(out, fh, indent=1)
        print(f"\nwrote {args.json}")
    sys.exit(2 if fail else 0)


if __name__ == "__main__":
    main()
