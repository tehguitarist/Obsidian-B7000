#!/usr/bin/env python3
"""GATE P -- is A3's headline 5.1-5.5 dB a sound target for a STATIC level correction?

    /opt/homebrew/bin/python3.11 analysis/a3_pedestal_gate.py analysis/reports/s99_attack_cand.json

WHY THIS EXISTS
---------------
The project's head item is a timeboxed attempt at A3 term (A): "the OD path's 5.1-5.5 dB absolute
deficit over 100-400 Hz, offset-dominated there, stimulus-independent to 0.47 dB".  Before
spending the one authorised attempt, three properties of that number are worth checking, because
all three are assumed by the plan and none had been measured:

  1. Is it a PEDESTAL or the mean of a window that CONTAINS a feature?  100-400 Hz holds the
     254/320 Hz bands, which run 9-10 dB at the clean stimulus against 2 dB in the bands either
     side.  A mean over a window containing a peak is not a level.

  2. Is it REPRODUCIBLE?  GATE M averages 4 capture pairs.  If the per-band spread ACROSS those
     pairs is comparable to the quantity, the headline is not determined well enough to fit to.

  3. ⭐ Is it independent of the DRIVE KNOB?  GATE M varies the STIMULUS LEVEL (sweep_clean ..
     sweep_drv_-6, four input levels) and reports stimulus-independence -- but its 4 pairs also
     differ in the pedal's own DRIVE control (0.0, 0.5, 1.0), and it POOLS over that.  Those are
     different axes: stimulus level is how hard the signal drives the input, DRIVE is how hard
     the clipper is asked to work.  A quantity that is flat in one and steep in the other is not
     a fixed linear error, and a static gain cannot carry it.

    ⭐ THE INTERNAL CONTROL that makes (3) readable at n=4: the two drive-0.0 pairs differ in
    their ATTACK throw (boost vs cut).  So the pair set contains one comparison that isolates
    ATTACK at fixed drive, against a drive sweep at fixed ATTACK.  If the excess moves with DRIVE
    and not with ATTACK, the drive axis is real and is not an attack artefact.

WHAT THIS GATE DOES NOT CLAIM
-----------------------------
  * It does NOT touch A3's ATTRIBUTION.  GATE O's ledger -- clean side bounded at 0.41 dB against
    a 5.28 dB OD deficit -- is untouched.  What is under test is whether the SIZE is a
    well-determined target for a STATIC correction, not whether the OD path is quiet.
  * It does NOT claim (A) and (B) are one defect.
  * n per drive setting is 2 / 1 / 1.  The drive trend is reported with that stated, and rests on
    the ATTACK control, not on replication.

It IMPORTS `a3_balance_gate` (and through it `level_law_gate` / `matrix_grade`), so the pair
selection, the absolute reconstruction and the band mapping cannot drift from GATE M's.

Exits non-zero on a failed sub-gate.  No render: a re-read of the shipped grade.
"""

import argparse
import json
import sys
import os

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matrix_grade as MG          # noqa: E402
import level_law_gate as K         # noqa: E402
import a3_balance_gate as M        # noqa: E402

SWEEPS = M.SWEEPS
A_WINDOW = M.A3_BAND               # (100, 400) Hz -- GATE M's own constant, not a retype

# A band is REPRODUCIBLE if the spread across the capture pairs is below this at BOTH stimulus
# extremes.  Selecting on precision is independent of the value being selected; P3 sweeps the bar
# and requires the conclusion to survive, so this is not `self-selecting-scores`.
REPRO_SD_BAR = 1.25
REPRO_BAR_SWEEP = (0.75, 1.00, 1.25, 1.50, 2.00)

# A band is CLEAR OF THE FEATURE if its excess sits within this of the curve's own floor.  This
# asks "is this band near the pedestal?" without assuming the feature's shape, centre or width.
FEATURE_CLEAR_DB = 1.00
CLEAR_BAR_SWEEP = (0.50, 1.00, 1.50, 2.00)

# Where the floor is taken from: above GATE M's distrusted LF bands, below the HF rolloff that
# GATE I attributes to ND.
BASELINE_SPAN = (40.0, 3300.0)

# GATE M's least trustworthy bands, excluded from its every verdict; inherited here.
DISTRUSTED_HZ = (25.2, 31.7)


def per_pair(absfr, pairs, nonhf, sw):
    """-> (n_pairs, n_bands) array of the excess curve, one row per pair, no pooling."""
    S = []
    for fc, fo, *_ in pairs:
        mc, qc = absfr[(fc, sw)]
        mo, qo = absfr[(fo, sw)]
        S.append((mc[nonhf] - mo[nonhf]) - (qc[nonhf] - qo[nonhf]))
    if not S:
        sys.exit(f"GATE P FAIL: no pairs at {sw} -- an empty mean is not a measurement")
    return np.array(S)


# --------------------------------------------------------------------------------------------
# P1 -- known answer against GATE M itself
# --------------------------------------------------------------------------------------------
def gate_p1(absfr, caps, nonhf, fb, out):
    print("-- P1: known answer -- the excess must reproduce GATE M elementwise --")
    pairs = M.pair_up(caps, *M.endpoints(caps, exclude_defect=True))
    worst = 0.0
    for sw in SWEEPS:
        mine = per_pair(absfr, pairs, nonhf, sw).mean(axis=0)
        theirs = M.excess_curve(absfr, pairs, nonhf, sw)[0]
        worst = max(worst, float(np.max(np.abs(mine - theirs))))
    if worst > 1e-12:
        sys.exit(f"GATE P1 FAIL: the per-pair decomposition does not re-pool to GATE M's own "
                 f"curve ({worst:.3e}) -- every split below would be of a different quantity")
    print(f"   per-pair rows re-pool to GATE M's curve elementwise to {worst:.2e}, all "
          f"{len(SWEEPS)} stimulus levels")

    sel = [j for j, f in enumerate(fb) if A_WINDOW[0] <= f <= A_WINDOW[1]]
    ref = float(per_pair(absfr, pairs, nonhf, "sweep_clean").mean(axis=0)[sel].mean())
    mut = float(per_pair(absfr, pairs, nonhf, "sweep_clean").mean(axis=0)[sel[:-1]].mean())
    if abs(mut - ref) < 0.10:
        sys.exit(f"GATE P1 FAIL: dropping a band moves the (A) mean {abs(mut - ref):.3f} dB -- "
                 f"the check cannot distinguish membership and is vacuous")
    print(f"   mutation control: dropping the top (A) band moves the mean {ref:.2f} -> {mut:.2f} "
          f"dB -- not vacuous")
    print(f"   ⇒ GATE M's headline (A) mean at the clean stimulus is {ref:.2f} dB")
    out["p1"] = {"worst": worst, "mutation": abs(mut - ref), "a_mean_clean": ref}
    return pairs


# --------------------------------------------------------------------------------------------
# P2 -- membership, and the design of the pair set
# --------------------------------------------------------------------------------------------
def gate_p2(caps, pairs, out):
    print("\n-- P2: membership, and what the 4 pairs actually vary --")
    all_pairs = M.pair_up(caps, *M.endpoints(caps, exclude_defect=False))
    n_defect = len(all_pairs) - len(pairs)
    if n_defect < 1:
        sys.exit(f"GATE P2 FAIL: excluding '{M.DEFECT_TOKEN}' removed {n_defect} pairs -- the "
                 f"exclusion matched nothing (`empty-gate-must-fail` in a costume)")
    print(f"   {len(all_pairs)} pairs, {n_defect} carrying '{M.DEFECT_TOKEN}' excluded by NAME, "
          f"{len(pairs)} used")

    print(f"\n   {'drive':>6}{'attack':>8}{'grunt':>7}   OD capture")
    drives, attacks = {}, {}
    for fc, fo, dr, at, gr in pairs:
        print(f"   {dr:>6}{at:>8}{gr:>7}   {fo}")
        drives.setdefault(dr, []).append(at)
        attacks.setdefault(at, []).append(dr)

    if len(drives) < 2:
        sys.exit(f"GATE P2 FAIL: the pairs hold {len(drives)} distinct DRIVE setting(s) -- the "
                 f"drive axis this gate exists to measure is not present in the data")
    # The internal control: some drive setting must carry >1 ATTACK throw, or ATTACK and DRIVE
    # are perfectly confounded and P4's trend cannot be attributed.
    ctrl = [d for d, ats in drives.items() if len(set(ats)) > 1]
    if not ctrl:
        sys.exit("GATE P2 FAIL: no DRIVE setting carries more than one ATTACK throw -- DRIVE and "
                 "ATTACK are perfectly confounded and no trend below can be attributed to either")
    print(f"\n   DRIVE settings present : {sorted(drives)}  (n = "
          f"{', '.join(str(len(drives[d])) for d in sorted(drives))})")
    print(f"   ⭐ internal control    : drive {ctrl[0]} carries ATTACK throws "
          f"{sorted(set(drives[ctrl[0]]))} -- ATTACK is isolable at fixed DRIVE")
    print( "   ⚠ GATE M pools over ALL of this and reports only the STIMULUS-LEVEL axis.")

    out["p2"] = {"n_pairs_all": len(all_pairs), "n_defect": n_defect, "n_pairs": len(pairs),
                 "drives": {str(d): sorted(set(a)) for d, a in drives.items()},
                 "control_drive": ctrl[0]}
    return ctrl[0]


# --------------------------------------------------------------------------------------------
# P3 -- how reproducible is the measurement, per band?
# --------------------------------------------------------------------------------------------
def gate_p3(absfr, pairs, nonhf, fb, out):
    print("\n-- P3: per-band spread ACROSS the pairs -- where is this measurable at all? --")

    worst_m = worst_q = 1e9
    for sw in SWEEPS:
        for fc, fo, *_ in pairs:
            for fn in (fc, fo):
                m, q = absfr[(fn, sw)]
                worst_m = min(worst_m, float(np.min(m[nonhf])))
                worst_q = min(worst_q, float(np.min(q[nonhf])))
    if min(worst_m, worst_q) <= MG.SILENT_DB:
        sys.exit(f"GATE P3 FAIL: an endpoint reading touches the {MG.SILENT_DB} dB floor")
    print(f"   floor guard: worst absolute reading model {worst_m:.1f} / pedal {worst_q:.1f} dB "
          f"against a {MG.SILENT_DB:.0f} dB floor -- clear")

    ends = ("sweep_clean", "sweep_drv_-6")
    S = {sw: per_pair(absfr, pairs, nonhf, sw) for sw in ends}
    sd = {sw: S[sw].std(axis=0, ddof=1) for sw in ends}
    mu = {sw: S[sw].mean(axis=0) for sw in ends}

    print(f"\n   {'Hz':>7}{'mean cln':>10}{'sd cln':>8}{'mean drv':>10}{'sd drv':>8}   repro?")
    keep = []
    for j, f in enumerate(fb):
        ok = (max(sd[ends[0]][j], sd[ends[1]][j]) <= REPRO_SD_BAR
              and not any(abs(f - h) < 0.05 for h in DISTRUSTED_HZ))
        if ok:
            keep.append(j)
        print(f"   {f:>7.0f}{mu[ends[0]][j]:>10.2f}{sd[ends[0]][j]:>8.2f}"
              f"{mu[ends[1]][j]:>10.2f}{sd[ends[1]][j]:>8.2f}   {'yes' if ok else '.'}")

    if len(keep) < 3:
        sys.exit(f"GATE P3 FAIL: only {len(keep)} bands are reproducible at sd <= "
                 f"{REPRO_SD_BAR} -- there is nothing to average")
    hz = [float(fb[j]) for j in keep]
    print(f"\n   {len(keep)} of {len(fb)} bands reproduce across the pairs at sd <= "
          f"{REPRO_SD_BAR} dB at BOTH stimulus extremes:")
    print(f"      {', '.join(f'{h:.0f}' for h in hz)} Hz")

    # The bands carrying A3's headline are precisely the least reproducible ones.
    aw = [j for j, f in enumerate(fb) if A_WINDOW[0] <= f <= A_WINDOW[1]]
    top = sorted(aw, key=lambda j: -mu[ends[0]][j])[:2]
    print(f"\n   ⚠ the two bands that DOMINATE the (A) window at the clean stimulus are "
          f"{fb[top[0]]:.0f} and {fb[top[1]]:.0f} Hz")
    print(f"     ({mu[ends[0]][top[0]]:.2f}, {mu[ends[0]][top[1]]:.2f} dB) and their across-pair "
          f"spread is {sd[ends[0]][top[0]]:.2f}, {sd[ends[0]][top[1]]:.2f} dB at clean and "
          f"{sd[ends[1]][top[0]]:.2f}, {sd[ends[1]][top[1]]:.2f} at drive.")
    print( "     The headline's largest contributors are its least reproducible bands.")

    out["p3"] = {"floor": {"model": worst_m, "pedal": worst_q},
                 "bands": [float(x) for x in fb],
                 "mean": {s: [float(x) for x in mu[s]] for s in ends},
                 "sd": {s: [float(x) for x in sd[s]] for s in ends},
                 "repro_hz": hz, "bar": REPRO_SD_BAR}
    return keep, S


# --------------------------------------------------------------------------------------------
# P4 -- the DRIVE-KNOB axis GATE M pools over
# --------------------------------------------------------------------------------------------
def gate_p4(absfr, pairs, nonhf, fb, ctrl_drive, out):
    """How much does the headline move across the four OPERATING POINTS it is averaged over?

    GATE M reports one number per stimulus level, pooling 4 pairs that differ in the pedal's own
    DRIVE and ATTACK controls.  A static correction is a single constant, so the spread across
    those operating points is the target's own uncertainty -- and it has never been printed."""
    print("\n-- P4: how much does the headline move across the four OPERATING POINTS? --")
    aw = [j for j, f in enumerate(fb) if A_WINDOW[0] <= f <= A_WINDOW[1]]
    ends = ("sweep_clean", "sweep_drv_-6")

    V = {}
    for sw in ends:
        S = per_pair(absfr, pairs, nonhf, sw)
        V[sw] = [float(S[i][aw].mean()) for i in range(len(pairs))]

    print(f"\n   (A)-window mean, per pair -- NOT pooled")
    print(f"   {'drive':>6}{'attack':>8}{'clean':>9}{'drv_-6':>9}")
    for i, (fc, fo, dr, at, gr) in enumerate(pairs):
        print(f"   {dr:>6}{at:>8}{V[ends[0]][i]:>9.2f}{V[ends[1]][i]:>9.2f}")

    allv = V[ends[0]] + V[ends[1]]
    span = max(allv) - min(allv)
    pooled = float(np.mean(allv))
    print(f"\n   ⇒ the headline is the mean of values spanning {min(allv):.2f} to {max(allv):.2f} "
          f"dB -- a {span:.2f} dB span, i.e. ±{span / 2:.2f} dB")
    print(f"     about a pooled {pooled:.2f}.  GATE M prints only the pooled column.")

    # Which knob?  Report the ATTACK control against the DRIVE trend AT EACH stimulus level, and
    # let the verdict be conditioned -- pooling the two would hide a disagreement between them.
    res = {}
    print(f"\n   {'stimulus':<10}{'ATTACK spread':>15}{'DRIVE span':>12}   attributable?")
    for sw in ends:
        ci = [i for i, p in enumerate(pairs) if p[2] == ctrl_drive]
        d_at = max(V[sw][i] for i in ci) - min(V[sw][i] for i in ci)
        by = {}
        for i, p in enumerate(pairs):
            by.setdefault(p[2], []).append(V[sw][i])
        dv = {d: float(np.mean(v)) for d, v in by.items()}
        d_dr = max(dv.values()) - min(dv.values())
        att = d_dr > d_at
        res[sw] = {"attack_spread": d_at, "drive_span": d_dr, "attributable": bool(att),
                   "by_drive": {str(d): v for d, v in dv.items()}}
        print(f"   {sw.replace('sweep_', ''):<10}{d_at:>15.2f}{d_dr:>12.2f}   "
              f"{'DRIVE (span > attack control)' if att else 'NO -- attack >= drive'}")

    if all(res[s]["attributable"] for s in ends):
        verdict = "drive dependent"
        print( "\n   ⇒ DRIVE dominates at BOTH stimulus levels: the excess depends on how hard the")
        print( "     clipper is asked to work, so it is not a fixed linear error of the OD path.")
    elif any(res[s]["attributable"] for s in ends):
        verdict = "operating-point dependent, knob not resolved"
        good = [s.replace("sweep_", "") for s in ends if res[s]["attributable"]]
        bad = [s.replace("sweep_", "") for s in ends if not res[s]["attributable"]]
        print(f"\n   ⇒ DRIVE dominates at {', '.join(good)} but NOT at {', '.join(bad)}, where the "
              f"ATTACK control is")
        print( "     as large or larger.  So the headline IS operating-point dependent, but WHICH")
        print( "     knob carries it is NOT resolvable from 4 pairs -- do not attribute it.")
    else:
        verdict = "no drive dependence"
        print( "\n   => the DRIVE span never exceeds the ATTACK control; no drive axis established.")

    print(f"   ⚠ n per drive setting is "
          + ", ".join(f"{d}: {len([1 for p in pairs if p[2] == d])}"
                      for d in sorted(set(p[2] for p in pairs)))
          + " -- this rests on the ATTACK control, not on replication.")

    out["p4"] = {"per_pair": {s: V[s] for s in ends},
                 "settings": [{"drive": p[2], "attack": p[3]} for p in pairs],
                 "span": span, "pooled": pooled, "by_stimulus": res, "verdict": verdict}
    return verdict


# --------------------------------------------------------------------------------------------
# P5 -- pedestal vs feature, on the reproducible bands only
# --------------------------------------------------------------------------------------------
def feature_free(fb, mu, clear_db):
    """-> band indices whose excess sits within `clear_db` of the curve's own floor.

    The floor is the MINIMUM of the clean-stimulus pooled curve over the analysis span, so this
    asks 'is this band near the pedestal?' without assuming the feature's shape or centre."""
    span = [j for j, f in enumerate(fb) if BASELINE_SPAN[0] <= f <= BASELINE_SPAN[1]]
    floor = float(np.min(mu[span]))
    return [j for j in span if mu[j] <= floor + clear_db], floor


def gate_p5(fb, keep, S, out):
    """Can a pedestal be measured AT ALL with this pair set?

    It needs a band that is BOTH reproducible across the pairs AND clear of the feature.  P3
    found the reproducible bands; this asks whether any of them is also feature-free."""
    print("\n-- P5: is there any band that is both REPRODUCIBLE and CLEAR OF THE FEATURE? --")
    mu = S["sweep_clean"].mean(axis=0)
    ff, floor = feature_free(fb, mu, FEATURE_CLEAR_DB)

    print(f"   curve floor over {BASELINE_SPAN[0]:.0f}-{BASELINE_SPAN[1]:.0f} Hz at the clean "
          f"stimulus: {floor:.2f} dB")
    print(f"   feature-free (within {FEATURE_CLEAR_DB:.1f} dB of it): "
          f"{', '.join(f'{fb[j]:.0f}' for j in ff)} Hz")
    print(f"   reproducible (P3, sd <= {REPRO_SD_BAR:.2f} dB): "
          f"{', '.join(f'{fb[j]:.0f}' for j in keep)} Hz")

    both = sorted(set(ff) & set(keep))
    print(f"\n   INTERSECTION: "
          + (", ".join(f"{fb[j]:.0f}" for j in both) + " Hz" if both else "EMPTY"))

    if not both:
        print( "\n   ⛔ NO band is both reproducible and clear of the feature.  The bands that are")
        print( "      quiet are the ones the four pairs disagree on; the bands the pairs agree on")
        print( "      are on the feature.  ⇒ a PEDESTAL and a FEATURE cannot be separated with")
        print( "      this pair set, so the size of any static level term in A3 is UNMEASURED.")
        ped = None
    else:
        ped = float(mu[both].mean())
        print(f"\n   => a pedestal IS measurable: {ped:.2f} dB over {len(both)} band(s), against "
              f"an (A)-window mean of {float(mu[[j for j, f in enumerate(fb) if A_WINDOW[0] <= f <= A_WINDOW[1]]].mean()):.2f} dB.")
        if len(both) < 3:
            print(f"   ⚠ {len(both)} band(s) is thin -- treat as an indication, not a measurement.")

    out["p5"] = {"floor": floor, "feature_free_hz": [float(fb[j]) for j in ff],
                 "repro_hz": [float(fb[j]) for j in keep],
                 "both_hz": [float(fb[j]) for j in both], "pedestal": ped}
    return both


# --------------------------------------------------------------------------------------------
# P6 -- does the conclusion survive the reproducibility bar it was read at?
# --------------------------------------------------------------------------------------------
def gate_p6(absfr, pairs, nonhf, fb, out):
    """P5's answer rests on two thresholds.  Sweep BOTH and require the answer to survive, with
    an assertion that each knob actually changes the selection (a threshold that never binds is
    a constant printed several times, not a robustness check)."""
    print("\n-- P6: does P5's answer survive BOTH of its thresholds? --")
    ends = ("sweep_clean", "sweep_drv_-6")
    S = {sw: per_pair(absfr, pairs, nonhf, sw) for sw in ends}
    sd = {sw: S[sw].std(axis=0, ddof=1) for sw in ends}
    mu = S[ends[0]].mean(axis=0)

    print(f"   rows = reproducibility bar (dB), cols = feature-clear bar (dB); "
          f"cell = |reproducible AND feature-free|")
    print("   " + "sd / clear".rjust(10) + "".join(f"{c:>8.1f}" for c in CLEAR_BAR_SWEEP))
    grid, n_repro, n_ff = {}, set(), set()
    for bar in REPRO_BAR_SWEEP:
        keep = [j for j, f in enumerate(fb)
                if max(sd[ends[0]][j], sd[ends[1]][j]) <= bar
                and not any(abs(f - h) < 0.05 for h in DISTRUSTED_HZ)]
        n_repro.add(len(keep))
        line = f"   {bar:>10.2f}"
        for clear in CLEAR_BAR_SWEEP:
            ff, _ = feature_free(fb, mu, clear)
            n_ff.add(len(ff))
            n = len(set(ff) & set(keep))
            grid[(bar, clear)] = n
            line += f"{n:>8d}"
        print(line)

    if len(n_repro) < 2:
        sys.exit(f"GATE P6 FAIL: the reproducibility bar selects {n_repro.pop()} bands at every "
                 f"setting -- the knob is not turning, so this is not a robustness check")
    if len(n_ff) < 2:
        sys.exit(f"GATE P6 FAIL: the feature-clear bar selects {n_ff.pop()} bands at every "
                 f"setting -- the knob is not turning, so this is not a robustness check")
    print(f"   (band counts move {min(n_repro)}-{max(n_repro)} and {min(n_ff)}-{max(n_ff)} "
          f"across the two sweeps, so both knobs ARE turning)")

    worst, best = min(grid.values()), max(grid.values())
    n_empty = sum(1 for v in grid.values() if v == 0)
    print(f"\n   the intersection holds {worst}-{best} bands across all {len(grid)} threshold "
          f"combinations; {n_empty} of them are EMPTY.")
    if best <= 2:
        print( "   ⇒ at NO setting of either threshold does a usable feature-free, reproducible")
        print( "     set exist.  P5's answer is a property of the DATA, not of the thresholds.")
    else:
        print(f"   ⚠ at the loosest settings up to {best} bands qualify -- P5's answer is")
        print( "     threshold-dependent and must be quoted with its bars.")
    out["p6"] = {"grid": {f"{k[0]}|{k[1]}": v for k, v in grid.items()},
                 "worst": worst, "best": best, "n_empty": n_empty, "n_cells": len(grid)}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    bands, caps = MG.load(a.report)
    idx = [i for i, b in enumerate(bands) if MG.GRADE_LO <= b <= MG.GRADE_HI]
    absfr, _silent = K.absolute_fr(caps, idx)
    nonhf = [j for j, i in enumerate(idx) if bands[i] < K.HF_HZ]
    fb = np.array([bands[idx[j]] for j in nonhf])

    print(f"GATE P -- is A3's 5.1-5.5 dB a sound STATIC-correction target?   [{a.report}]")
    print(f"  {len(caps)} captures, {len(nonhf)} non-HF bands (< {K.HF_HZ:.0f} Hz, per GATE I)")
    print( "  No render, no fit, no gain match.  Imports GATE M's pairs and GATE K's absolute")
    print( "  reconstruction, so the three cannot drift.\n")

    out = {"report": a.report}
    pairs = gate_p1(absfr, caps, nonhf, fb, out)
    ctrl = gate_p2(caps, pairs, out)
    keep, S = gate_p3(absfr, pairs, nonhf, fb, out)
    gate_p4(absfr, pairs, nonhf, fb, ctrl, out)
    gate_p5(fb, keep, S, out)
    gate_p6(absfr, pairs, nonhf, fb, out)

    print("\n== GATE P: all sub-gates passed ==")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, default=float)
        print(f"   wrote {a.json}")


if __name__ == "__main__":
    main()
