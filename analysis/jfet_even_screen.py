#!/usr/bin/env python3.11
"""jfet_even_screen — the PIVOT GATE for the low-drive even-order item, before any fit.

WHY THIS EXISTS, AND WHY IT RUNS BEFORE A FIT
---------------------------------------------
Session 72 (`docs/phase9-validation.md` §4 "HARMONIC LADDER") measured our H2..H5 ladder against
both reference columns and found the even-order deficit is **low-drive-specific**:

        even-minus-adjacent-odd, corrected      OURS      ND        HW
        mid drive  H2-H3   (997 / 800 Hz)     -1.7/-1.5  -27.0     0.0    => 94 % of the way to HW
        low drive  H2-H3   (997 / 800 Hz)     +0.4/+2.3    0.0    +18.5   =>  2-12 %

So the target is: raise LOW-drive H2-H3 by ~16-18 dB while LEAVING MID DRIVE ALONE. Session 72
named the J201 as the natural carrier (the clipper is near-linear at low drive; the J201 sits
UPSTREAM of the DRIVE pot and never idles -- session 59 item 3).

** This project has twice built a reshape and then failed its own pre-registered pivot gate
(session 12's `clipk_pivot_check.py`, session 14's `ceilk_pivot_check.py`), each time after the
code was written. ** So the gate runs first, on parameters that ALREADY EXIST -- nothing in `src/`
is touched to run it.

THE STRUCTURAL PREDICTION BEING TESTED (derived from the shape in JfetStage.h, not guessed)
------------------------------------------------------------------------------------------
The shipped J201 map is

        g(w) = T(w) + (a*s^2/2)*tanh^2(w/s),     a = jfetSatNeg, s = jfetSatPos
        T(w) = w*(1+c*w^2)/(1+(w/L)^2)^1.5,      L = jfetCeilPos (w>=0) / jfetCeilNeg (w<0)

For |w| << s the bump is (a/2)*w^2, so the stage's SMALL-SIGNAL even (quadratic) coefficient is
**a/2, independent of s and of both ceilings**. And the low-drive anchor lands at input levels
-42..-54 dBFS => vgs of order 1-10 mV, which is 2-3 orders of magnitude below s (0.456) and below
either L (0.657 / 2.011). Therefore:

    * `jfetSatNeg` (a)              -- MUST move low-drive H2-H3        (the LIVENESS arm)
    * `jfetSatPos` (s) alone        -- must NOT move it   (it only sets where the bump saturates)
    * `jfetCeilNeg`/`Pos` asymmetry -- must NOT move it   (acts only at |w| ~ L)

Both arms matter. A gate that only shows `a` is live cannot distinguish "the small-signal quadratic
is the mechanism" from "anything I touch in this stage moves that number"; the two inert controls
are what make the liveness reading mean something (memory: `known-feature-validates-an-instrument`,
and session 63's own "a control that passes even when the claim is false is not the gate").

AND THE THIRD ARM, WHICH IS THE ONE THAT CAN KILL IT: mid drive must stay put. That is NOT
arranged -- it is predicted, because at the mid anchor the clipper's own H2 dominates (raw -14.9 dB)
while the J201's small-signal even contribution sits far below it. If mid drive moves as much as
low drive, `a` is not a low-drive-selective lever and the item needs a different carrier.

FEASIBILITY IS PART OF THE GATE, NOT A FOOTNOTE
-----------------------------------------------
The even bump folds back (non-monotone => a rectifier, not a JFET) once |a|*s exceeds
3*sqrt(3)/2 = 2.598. With a finite ceiling the constraint couples s, a and the ceilings, so it is
SCANNED NUMERICALLY via `fit_nonlinear.min_slope` -- imported, not re-derived, because that replica
is already gated against the shipped C++ map by JfetStageTest (one oracle; memory:
`verify-extremum-derived-bounds`). Every candidate prints its own min slope and is REFUSED if it
folds back, so a "win" bought by an unphysical shape cannot be quoted.

Run:
  /opt/homebrew/bin/python3.11 analysis/jfet_even_screen.py --selftest
  /opt/homebrew/bin/python3.11 analysis/jfet_even_screen.py --jobs 6
"""
import sys, os, json, argparse, io, contextlib
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
import numpy as np

# ONE oracle for the measurement: the anchor logic, the stimulus, the pair statistic and the
# repeatability gate all come from the tool that produced the session-72 record.
import harmonic_ladder as HL
with contextlib.redirect_stdout(io.StringIO()):
    from fit_nonlinear import min_slope

# Shipped values (FitParams.h, session-44 A5 re-fit). Kept here ONLY so a candidate's implied
# monotonicity can be scanned; the RENDER always takes the shipped defaults unless a candidate
# overrides them, so these cannot silently become the source of truth for the audio.
SHIP = dict(jfetSatPos=0.4559, jfetSatNeg=0.76054,
            jfetCeilPos=2.0111, jfetCeilNeg=0.65743, jfetExpandBeta=0.46279)

# The gate's targets, from reference-sources.md §4 via session 72's anchored measurement.
LOW_TARGET_DB = 18.5      # HW's low-drive H2-H3
MID_HOLD_DB = 3.0         # mid drive must not move by more than this to count as "left alone"

# --- the candidates ---------------------------------------------------------------------------
# `a*s` is printed for each so the feasibility edge (2.598) is visible in the table itself.
CANDS = [
    ("ship",       {},                                             "shipped defaults (reference row)"),
    # LIVENESS ARM: the small-signal even coefficient a/2, swept to its feasibility ceiling at
    # the shipped knee (a < 2.598/s = 5.70).
    ("a=2.0",      dict(jfetSatNeg=2.0),                           "a x2.6   (a*s 0.91)"),
    ("a=4.0",      dict(jfetSatNeg=4.0),                           "a x5.3   (a*s 1.82)"),
    ("a=5.6",      dict(jfetSatNeg=5.6),                           "a x7.4   (a*s 2.55, at the edge)"),
    # Beyond the edge at fixed s only by SHRINKING s -- the small-signal quadratic is a/2 and does
    # not care about s, so a*s = const trades the saturation knee for more even content.
    ("a=11 s=0.20", dict(jfetSatNeg=11.0, jfetSatPos=0.20),        "a x14.5  (a*s 2.20)"),
    ("a=22 s=0.10", dict(jfetSatNeg=22.0, jfetSatPos=0.10),        "a x28.9  (a*s 2.20)"),
    # SQUARE-LAW-LINKED FAMILY -- the PHYSICALLY COHERENT form of the same lever. `a` = 1/Vov and
    # the cutoff ceiling cn = Vov/2 both derive from the SAME overdrive voltage, so a real device
    # moving to a smaller Vov moves BOTH: 2*a*cn = 1. That identity holds EXACTLY at the shipped
    # point (2 x 0.76054 x 0.65743 = 1.0000) and was session 44's one independent corroboration, so
    # raising `a` alone BREAKS it. These rows ask whether honouring it changes the selectivity --
    # cn tightening pulls the ceiling into play, which is a mid-drive effect, so it might well make
    # the trade worse rather than better. (s is shrunk only where a*s would otherwise fold back.)
    ("SQ Vov=0.60", dict(jfetSatNeg=1.667, jfetCeilNeg=0.300),     "a=1.67 cn=0.30, 2*a*cn=1"),
    ("SQ Vov=0.30", dict(jfetSatNeg=3.333, jfetCeilNeg=0.150),     "a=3.33 cn=0.15, 2*a*cn=1"),
    ("SQ Vov=0.18", dict(jfetSatNeg=5.556, jfetCeilNeg=0.090),     "a=5.56 cn=0.09, 2*a*cn=1"),
    ("SQ Vov=0.09", dict(jfetSatNeg=11.11, jfetCeilNeg=0.045,
                         jfetSatPos=0.20),                          "a=11.1 cn=0.045, 2*a*cn=1"),
    # DISCRIMINATING CONTROLS: predicted INERT at low drive. If either moves it, the small-signal
    # reading above is wrong and the mechanism is not what this gate assumes.
    ("CTL s=0.20", dict(jfetSatPos=0.20),                          "knee only, a unchanged"),
    ("CTL cn=0.33", dict(jfetCeilNeg=0.33),                        "ceiling asymmetry x2, a unchanged"),
]


def feasible(over):
    p = dict(SHIP, **over)
    ms = min_slope(p["jfetSatPos"], p["jfetSatNeg"], p["jfetCeilPos"], p["jfetCeilNeg"],
                   p["jfetExpandBeta"])
    return ms, ms > -1.0e-9, p["jfetSatNeg"] * p["jfetSatPos"]


def run_one(job):
    """Render + measure one candidate. Returns the pair rows plus the anchor bookkeeping.

    Runs in a worker process, so it must not print (interleaved output from 6 workers is
    unreadable) -- everything it learns comes back in the dict."""
    name, over, tag, bounds = job
    fit = tuple(f"{k}={v!r}" for k, v in over.items())
    # ** The stimulus is built ONCE by the parent and only READ here. ** Letting each worker call
    # build_stimulus() on the shared path had 8 processes writing one 13 MB WAV concurrently -- the
    # content is deterministic, so it would have looked fine most of the time and produced a torn
    # file for one candidate occasionally, which is the worst possible failure mode for an A/B.
    with contextlib.redirect_stdout(io.StringIO()):
        cells, fr = HL.measure_all(bounds, 8, fit, tag)
        repeat_ok = HL.gate_repeat(cells)
        verdicts, hits, gates = HL.measure_verdict(cells)
        rows = HL.pair_rows(verdicts, fr)
        lrows = HL.level_rows(verdicts, fr)
    pairs = {(r["tone"], r["drive"], r["pair"]): r["corr"] for r in rows}
    # ** The THIRD anchored degree of freedom (session 76). The pair statistics above span only two
    # of the three, so a candidate can move the late-harmonic LEVEL by any amount and score
    # identically on every number this screen used to print -- HL.gate_dof() demonstrates that
    # blindness explicitly. Carried per candidate so that cannot happen silently. **
    levels = {(r["tone"], r["drive"]): r["corr"] for r in lrows}
    level_vs_hw = {(r["tone"], r["drive"]): r["vs_hw"] for r in lrows}
    reach = {(f0, lbl): len(hits[(f0, lbl)]) for f0 in HL.TONES_HZ for lbl in ("low", "mid")}
    drv = {(f0, lbl): ([h["drive"] for h in hits[(f0, lbl)]] or [float("nan")])
           for f0 in HL.TONES_HZ for lbl in ("low", "mid")}
    return dict(name=name, fit=list(fit), pairs=pairs, levels=levels,
                level_vs_hw=level_vs_hw, reach=reach,
                drives={f"{k[0]:g}|{k[1]}": v for k, v in drv.items()},
                repeat_ok=bool(repeat_ok),
                anchor_spread={f"{f0:g}": gates[f0][1] for f0 in HL.TONES_HZ})


def selftest():
    """Gates that need no render: the feasibility scan must be LIVE and must REFUSE a known
    fold-back, and the candidate list must be self-consistent with its own printed a*s."""
    print("=" * 92)
    print("SELFTEST -- feasibility scan (fit_nonlinear.min_slope, the JfetStage-gated replica)")
    print("=" * 92)
    ok = True
    # A known-BAD point must be refused, or the scan is decoration. a*s = 3.65 was measured
    # (session 73) to fold back at w = -0.312 with slope -0.380.
    ms_bad, good_bad, _ = feasible(dict(jfetSatNeg=8.0))
    if good_bad:
        ok = False
    print(f"  known fold-back  a=8.0  (a*s 3.65):  min slope {ms_bad:+.4f}  "
          f"{'** FAIL -- accepted an unphysical shape **' if good_bad else 'OK (refused)'}")
    ms_ship, good_ship, _ = feasible({})
    if not good_ship:
        ok = False
    print(f"  shipped point                      :  min slope {ms_ship:+.3e}  "
          f"{'OK (accepted)' if good_ship else '** FAIL **'}")
    print("  (the scan is flat in `a` until the bump can out-slope the core near the knee; that is")
    print("   a property of the shape, not a dead parameter -- the a=8.0 row above proves it bites.)")
    print()
    print("  candidate feasibility:")
    for name, over, why in CANDS:
        ms, good, asx = feasible(over)
        print(f"    {name:<12} a*s {asx:5.2f}  min slope {ms:+.4e}  "
              f"{'OK' if good else '** FOLDS BACK -- will be refused **'}   {why}")
    print()
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--json", default="analysis/reports/s73_jfet_even_screen.json")
    args = ap.parse_args()

    if not selftest():
        print("** SELFTEST FAILED -- not screening. **")
        return 1
    if args.selftest:
        print("SELFTEST PASS.")
        return 0

    with contextlib.redirect_stdout(io.StringIO()):
        bounds = HL.build_stimulus(f"{HL.WORK}/stimulus.wav")
    jobs = [(n, o, f"_scr{i}", bounds) for i, (n, o, _) in enumerate(CANDS)]
    print(f"screening {len(jobs)} candidates x {len(HL.DRIVES)} drives at OS 8, {args.jobs} workers ...\n")
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        res = list(ex.map(run_one, jobs))
    by = {r["name"]: r for r in res}

    # ---- the pivot table -----------------------------------------------------------------------
    print("=" * 92)
    print("PIVOT TABLE -- corrected H2-H3 at each anchor (dB). WANT: low -> +18.5, mid -> unchanged.")
    print("=" * 92)
    print(f"  {'candidate':<12} {'a*s':>5} {'feas':>5}   "
          f"{'low 997':>8} {'low 800':>8}   {'mid 997':>8} {'mid 800':>8}   "
          f"{'d(low)':>7} {'d(mid)':>7}   {'ratio':>6}")
    base = by["ship"]["pairs"]
    b_lo = np.mean([base[(997.0, "low", (2, 3))], base[(800.0, "low", (2, 3))]])
    b_mi = np.mean([base[(997.0, "mid", (2, 3))], base[(800.0, "mid", (2, 3))]])
    table = []
    for name, over, why in CANDS:
        r = by[name]
        ms, good, asx = feasible(over)
        p = r["pairs"]
        try:
            lo = [p[(997.0, "low", (2, 3))], p[(800.0, "low", (2, 3))]]
            mi = [p[(997.0, "mid", (2, 3))], p[(800.0, "mid", (2, 3))]]
        except KeyError:
            print(f"  {name:<12} {asx:5.2f} {'-':>5}   ** AN ANCHOR WAS NOT REACHED -- "
                  f"reach {r['reach']} -- excluded **")
            continue
        d_lo, d_mi = float(np.mean(lo)) - b_lo, float(np.mean(mi)) - b_mi
        ratio = abs(d_lo) / abs(d_mi) if abs(d_mi) > 1e-9 else float("inf")
        table.append((name, d_lo, d_mi, ratio, good, r))
        print(f"  {name:<12} {asx:5.2f} {'ok' if good else 'FOLD':>5}   "
              f"{lo[0]:+8.1f} {lo[1]:+8.1f}   {mi[0]:+8.1f} {mi[1]:+8.1f}   "
              f"{d_lo:+7.2f} {d_mi:+7.2f}   {ratio:6.1f}")
    print(f"\n  baseline (mean of both tones): low {b_lo:+.2f} dB, mid {b_mi:+.2f} dB")
    print(f"  HW wants low = {LOW_TARGET_DB:+.1f} dB, i.e. d(low) = {LOW_TARGET_DB - b_lo:+.1f} dB "
          f"of movement, with |d(mid)| <= {MID_HOLD_DB:.1f} dB.")
    print("  d(low)/d(mid) is the SELECTIVITY: >>1 means the lever is low-drive-specific, ~1 means")
    print("  it moves the whole ladder and cannot fix low drive without breaking mid.")

    # ---- H4-H5, the SECONDARY pair, reported so a win on H2-H3 cannot hide a loss here ----------
    print()
    print("=" * 92)
    print("SECONDARY -- corrected H4-H5 (dB). HW wants +15.0 at low drive and 0.0 at mid.")
    print("=" * 92)
    print("  ** Not a HW-vs-ND discriminator at low drive ** -- the two references sit 1 dB apart")
    print("  there (session 72 §5), so this is a shared-deficit reading, not a position between them.")
    print(f"  {'candidate':<12}   {'low 997':>8} {'low 800':>8}   {'mid 997':>8} {'mid 800':>8}")
    for name, over, why in CANDS:
        p = by[name]["pairs"]
        k = [(997.0, "low"), (800.0, "low"), (997.0, "mid"), (800.0, "mid")]
        if not all((f0, lbl, (4, 5)) in p for f0, lbl in k):
            continue
        print(f"  {name:<12}   " + " ".join(f"{p[(f0, lbl, (4, 5))]:+8.1f}" for f0, lbl in k))
    print("  (HW low +15.0 / ND low +14.0 | HW mid 0.0 / ND mid -28.0)")

    # ---- TERTIARY -- the third anchored dof, which the two blocks above cannot see ---------------
    print()
    print("=" * 92)
    print("TERTIARY -- LATE-HARMONIC LEVEL (H4+H5)/2 re the anchor, error vs HW (dB)")
    print("=" * 92)
    print("  ** Why this block exists: the anchor pins H3, so the anchored error vector has THREE")
    print("  degrees of freedom and the two blocks above span only TWO of them. A candidate can move")
    print("  this one by ANY amount and score identically on every number printed above --")
    print("  HL.gate_dof() demonstrates that with a pure-mode vector reading exactly 0.00 on both.")
    print("  Shipped baseline is +5.7 dB at low drive and -11.8 at mid (session 76), so a candidate")
    print("  that pushes mid drive further negative is lengthening an already-too-short series.")
    print(f"  {'candidate':<12}   {'low 997':>8} {'low 800':>8}   {'mid 997':>8} {'mid 800':>8}   "
          f"{'d vs ship':>10}")
    b_lv = by["ship"].get("level_vs_hw", {})
    for name, over, why in CANDS:
        lv = by[name].get("level_vs_hw", {})
        k = [(997.0, "low"), (800.0, "low"), (997.0, "mid"), (800.0, "mid")]
        if not all(key in lv for key in k):
            continue
        dmid = (np.mean([lv[(997.0, "mid")], lv[(800.0, "mid")]])
                - np.mean([b_lv[(997.0, "mid")], b_lv[(800.0, "mid")]])) if b_lv else float("nan")
        print(f"  {name:<12}   " + " ".join(f"{lv[key]:+8.1f}" for key in k) +
              f"   {dmid:+10.2f}")
    print("  ⚠ (H4+H5)/2 mixes H4 -- where HW and ND are 28 dB apart at mid drive, so")
    print("    reference-sources.md §1's authority split applies -- with H5, where the two columns")
    print("    AGREE. Read it as a liveness/size statistic; quote the authority-free per-order rows")
    print("    from harmonic_ladder.py for a claim.")

    # ---- the gate verdict, COMPUTED (memory: computed-verdicts-not-narrated) --------------------
    print()
    print("=" * 92)
    print("GATE VERDICT")
    print("=" * 92)
    lives = [t for t in table if t[0].startswith("a=")]
    ctls = [t for t in table if t[0].startswith("CTL")]
    repeat_bad = [r["name"] for r in res if not r["repeat_ok"]]

    live_best = max((t[1] for t in lives), default=0.0)
    arm_live = live_best > 1.0
    ctl_worst = max((abs(t[1]) for t in ctls), default=0.0)
    arm_ctl = ctl_worst < 1.0
    monot = all(lives[i][1] <= lives[i + 1][1] + 0.3 for i in range(len(lives) - 1))
    feasible_win = [t for t in lives if t[4] and t[1] > 1.0]
    arm_hold = any(abs(t[2]) <= MID_HOLD_DB for t in feasible_win)
    reach_ok = not repeat_bad

    print(f"  [{'PASS' if reach_ok else 'FAIL'}] GATE 4 repeatability held for every candidate"
          + ("" if reach_ok else f"  -- contaminated: {repeat_bad}"))
    print(f"  [{'PASS' if arm_live else 'FAIL'}] LIVENESS: `a` moves low-drive H2-H3 "
          f"(best d(low) = {live_best:+.2f} dB)")
    print(f"  [{'PASS' if monot else 'FAIL'}] MONOTONE in `a`: low-drive H2-H3 rises with the "
          f"even coefficient, no interior turnover")
    print(f"  [{'PASS' if arm_ctl else 'FAIL'}] CONTROLS INERT: knee/ceiling alone leave low drive "
          f"alone (worst |d(low)| = {ctl_worst:.2f} dB)")
    print(f"  [{'PASS' if arm_hold else 'FAIL'}] SELECTIVITY: a feasible candidate moves low drive "
          f">1 dB while |d(mid)| <= {MID_HOLD_DB:.1f} dB")
    allpass = reach_ok and arm_live and monot and arm_ctl and arm_hold
    print()
    if allpass:
        print("  ** GATE PASSES. ** The J201's small-signal even coefficient IS a low-drive-"
              "selective lever,")
        print("  and the two inert controls show the mechanism is specifically the SMALL-SIGNAL")
        print("  quadratic a/2 -- not the knee, not the ceiling asymmetry.")

        # ** THE HOLD CONSTRAINT IS PART OF THE ANSWER, NOT A FOOTNOTE. ** Picking the largest
        # d(low) over all feasible candidates reports a "target reached" on a point that moves mid
        # drive 7 dB -- the exact thing the gate was told to protect. Rank only inside the hold set,
        # and state the SELECTIVITY the target demands against the selectivity actually available.
        need = LOW_TARGET_DB - b_lo
        need_sel = abs(need) / MID_HOLD_DB
        best_sel = max((t[3] for t in feasible_win), default=0.0)
        hold_set = [t for t in feasible_win if abs(t[2]) <= MID_HOLD_DB]
        print(f"\n  REQUIRED movement d(low) = {need:+.1f} dB with |d(mid)| <= {MID_HOLD_DB:.1f} dB")
        print(f"  => required selectivity {need_sel:.2f}x;  best selectivity observed {best_sel:.2f}x"
              f"  ({'AVAILABLE' if best_sel >= need_sel else 'NOT AVAILABLE'})")
        print("  Selectivity DECLINES as `a` rises (the J201's even content becomes a bigger share")
        print("  of the mid-drive total too), so the best ratio sits at the smallest useful step.")
        # ** THE VERDICT HINGES ON A TOLERANCE I CHOSE, so show the trade instead of hiding it. **
        # MID_HOLD_DB = 3.0 is tied to reference-sources.md §5's own +-3 dB chart-read uncertainty,
        # but at 5 dB the required selectivity drops to ~3.4x and the answer flips. A
        # threshold-dependent conclusion must print its own sensitivity (memory:
        # flat-threshold-on-interval-identified-quantity).
        print(f"\n  SENSITIVITY OF THAT VERDICT to the mid-drive tolerance (which is a CHOICE):")
        for tol in (2.0, 3.0, 4.0, 5.0, 7.0):
            ns = abs(need) / tol
            okc = [t[0] for t in feasible_win if abs(t[2]) <= tol and t[1] >= need]
            print(f"    |d(mid)| <= {tol:.1f} dB -> need {ns:5.2f}x  "
                  f"{'reached by ' + ', '.join(okc) if okc else 'no feasible candidate reaches the target'}")

        if hold_set:
            bh = max(hold_set, key=lambda t: t[1])
            frac = (bh[1] / need * 100.0) if need else float("nan")
            print(f"\n  BEST CANDIDATE THAT HOLDS MID: {bh[0]}")
            print(f"    low {b_lo:+.1f} -> {b_lo + bh[1]:+.1f} dB  (target {LOW_TARGET_DB:+.1f}; "
                  f"closes {frac:.0f} % of the gap)")
            print(f"    mid {b_mi:+.1f} -> {b_mi + bh[2]:+.1f} dB  (moved {bh[2]:+.2f} dB, inside the "
                  f"{MID_HOLD_DB:.1f} dB hold)")
        else:
            print("\n  ** NO feasible candidate holds mid drive. **")
        # The square-law-linked family, reported separately: it is not part of the gate's arms
        # (those test the mechanism), it tests whether the PHYSICALLY LINKED move is any better.
        sq_all = [t for t in table if t[0].startswith("SQ")]
        sq = [t for t in sq_all if t[4]]
        sq_bad = [t[0] for t in sq_all if not t[4]]
        if sq_all:
            print("\n  SQUARE-LAW-LINKED family (2*a*cn = 1 honoured -- the physically coherent move):")
            for t in sq_all:
                tail = ("FOLDS BACK -- refused" if not t[4] else
                        ("holds mid" if abs(t[2]) <= MID_HOLD_DB else "BREAKS the mid hold"))
                print(f"    {t[0]:<12} d(low) {t[1]:+7.2f}  d(mid) {t[2]:+7.2f}  "
                      f"selectivity {t[3]:5.2f}x   {tail}")
            if sq_bad:
                print(f"    ** {len(sq_bad)} of {len(sq_all)} REFUSED as non-monotone: {', '.join(sq_bad)}. **")
                print("    Honouring the identity drives cn DOWN, which shrinks the core's cutoff-side")
                print("    slope exactly where the even bump's slope is most negative -> the map folds")
                print("    back (a rectifier, not a JFET). Note cn barely moves either anchor (the")
                print("    CTL cn row is inert, and SQ Vov=0.18 reads the same as a=5.6), so the")
                print("    identity buys NOTHING here and costs feasibility: ** the square law and the")
                print("    required even strength are JOINTLY INFEASIBLE in this shape. **")
            if sq:
                bsq = max(sq, key=lambda t: t[3])
                print(f"    best FEASIBLE linked selectivity {bsq[3]:.2f}x vs {need_sel:.2f}x required "
                      f"({'AVAILABLE' if bsq[3] >= need_sel else 'NOT AVAILABLE'})")

        reachers = [t for t in feasible_win if t[1] >= need]
        if reachers:
            r0 = min(reachers, key=lambda t: t[1])
            print(f"\n  TO REACH THE TARGET OUTRIGHT you need ~{r0[0]}, which moves mid drive "
                  f"{r0[2]:+.2f} dB")
            print(f"    => mid goes {b_mi:+.1f} -> {b_mi + r0[2]:+.1f} dB against HW's 0.0, i.e. from "
                  f"{abs(b_mi):.1f} dB UNDER to {abs(b_mi + r0[2]):.1f} dB OVER.")
            print("    That is a TRADE, not a free win -- read it against reference-sources.md §5")
            print("    (the reference numbers are chart reads; a +-3 dB error in either moves this).")
        else:
            print(f"\n  The target is NOT reached by any feasible candidate tested "
                  f"(best d(low) = {live_best:+.1f} vs {need:+.1f} required).")
    else:
        print("  ** GATE FAILS -- do NOT proceed to a fit on this lever. ** Per the session-12/14")
        print("  precedent, stop here and report, rather than fitting against a mechanism the")
        print("  discriminating check does not support.")

    out = dict(cands=[dict(name=n, over={k: v for k, v in o.items()}, why=w) for n, o, w in CANDS],
               baseline=dict(low=b_lo, mid=b_mi), target_low=LOW_TARGET_DB,
               results=[dict(name=r["name"], fit=r["fit"], repeat_ok=r["repeat_ok"],
                             reach={f"{k[0]:g}|{k[1]}": v for k, v in r["reach"].items()},
                             drives=r["drives"], anchor_spread=r["anchor_spread"],
                             pairs={f"{k[0]:g}|{k[1]}|H{k[2][0]}-H{k[2][1]}": v
                                    for k, v in r["pairs"].items()}) for r in res],
               verdict=dict(repeat=reach_ok, liveness=arm_live, monotone=monot,
                            controls_inert=arm_ctl, selectivity=arm_hold, pass_all=allpass))
    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
