#!/usr/bin/env python3.11
"""GATE M -- what IS the A3 clean/OD imbalance, per band and per drive?

Session 105.  No render: every number is a re-read of a report already on disk.  Imports
`level_law_gate` (GATE K) -- and through it `matrix_grade` -- rather than re-deriving the absolute
reconstruction, so the two cannot drift.

WHY THIS EXISTS
---------------
A3 is the head backlog item and session 103 re-promoted it on GATE K7, which measures the clean/OD
balance DIRECTLY at the mixing network's two exact-zero endpoints (BLEND = 0 -> clean with
coefficient 1; BLEND = 1 AND LEVEL = 1 -> OD with coefficient 1).  That endpoint construction is
sound and is not in question here -- it is the only A3 instrument that involves no fit, no gain
match and no model form.

What IS in question is what was then read off it.  K7 reports ONE number per stimulus level: the
mean of `r_model - r_pedal` over the 25 non-HF graded bands, pooled over its pairs.  Two claims
were carried forward from that single number, and both are checked here for the first time:

  (1) "the model's clean bleed runs 3.1-4.9 dB hot" -- quoted as A3's size.
  (2) "K7 says the defect is a LEVEL one.  Do not re-run those [frequency-shaping] searches."
      (CLAUDE.md item 5, session 103's scope note, which retired sessions 50/52/53's search space.)

Claim (2) is a statement about frequency.  K7 never resolves frequency: it takes a mean over the
band before anything is compared.  A mean cannot distinguish a flat 4 dB offset from a curve that
is +10 at 320 Hz and -5 at 6.5 kHz.  So the scope note that tells the next session NOT to look for
frequency shaping was inferred from a statistic that is blind to frequency by construction --
`difference-statistics-hide-common-mode`, in the one line that selects the whole A3 workplan.

GATES (all computed, exits non-zero on failure)
-----------------------------------------------
M1  KNOWN ANSWER -- this tool's own pooled read must reproduce GATE K7's shipped numbers to 1e-9
    through its own code path.  Without this, any disagreement below is my membership, not a
    finding.  Mutation control: dropping a band must move it.
M2  MEMBERSHIP, asserted rather than assumed (the s104 L2 lesson).  Exact pair count, the drive x
    attack spread printed, and `gain-n12` -- the pair recorded 12.071 dB down the compression curve
    from the other four -- identified BY NAME rather than by hoping it is absent.
M3  OPERATING-POINT PURITY.  `gain-n12` is one of K7's five pairs, i.e. 20% of the shipped
    headline, and it sits 12.071 dB further down the compression curve than the other four.
    Reports the headline with and without it.  ⚠ s111: this is no longer
    `defective-rows-must-not-vote` (GATE N healed the group) -- it is s108 P4, do not pool over an
    operating point the pedal itself sets.  See DEFECT_TOKEN.
M4  THE DECOMPOSITION, and the load-bearing one: offset vs shape per band, over four band
    selections, with the floor guard and a band-edge robustness column.  The verdict on "is A3 a
    level error?" is COMPUTED from shape/offset, not narrated.
M5  IS THE SHAPE REAL?  Leave-one-out correlation of each pair's de-meaned curve against the mean
    of the others.  A shape carried by one pair is not a finding; a shape all four pairs agree on
    is.  This is what separates "structure" from "noise in a 4-row mean".
M6  DOES THE SHAPE MOVE WITH DRIVE?  A static gain error cannot produce a peak that migrates in
    frequency with stimulus level.  Inherits K7's own known answer (both sides' r must rise
    monotonically with stimulus, because the OD path compresses and the clean tap does not).

WHAT THIS GATE DOES NOT CLAIM
-----------------------------
It does not re-open sessions 50/52/53's conclusions.  Those ruled out single elements and all
post-clipper LINEAR elements of any order; a drive-DEPENDENT shape is outside what either search
covered, so nothing here contradicts them.  What falls is only the s103 scope note that said a
frequency-shaping fix need not be looked for at all.

It also does not propose a fix.  It sizes and localises the defect so that the timeboxed A3
attempt (item 5) starts pointed at the right quantity.
"""
import argparse
import json
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import matrix_grade as MG          # noqa: E402
import level_law_gate as K         # noqa: E402

# The `gain-n12` group.  Named, not inferred: a substring test that silently matches nothing is
# `empty-gate-must-fail` wearing a disguise, so M2 asserts it IS found.
#
# ⚠⚠ SESSION 111 — THE REASON THIS IS EXCLUDED HAS CHANGED, THE EXCLUSION HAS NOT.  Session 105
# excluded it as "the session-48 capture defect", and that premise is RETIRED: GATE N (s106) re-ran
# session 48's own THD-turnover instrument and healed the group, and session 111 put those rows back
# into the graded matrix on the user's decision (`matrix_grade.EXCLUDE_GAIN_N12`).  Leaving a
# justification standing after its premise expires is the exact trap this project has paid for seven
# times, so it is corrected here rather than left to mislead.
#
# ⭐ THE EXCLUSION SURVIVES ON A DIFFERENT AND STILL-VALID GROUND: these captures sit 12.071 dB
# further down the OD path's compression curve than K7's other four pairs, and GATE M *pools* its
# pairs.  Session 108's P4 measured what pooling over an operating point the pedal itself sets costs
# — a headline quoted with a 0.47 dB stimulus spread that really carried +-1.10 dB — so mixing one
# 12 dB-quieter pair into a four-pair mean is the same defect, not a de-contamination.  M3 keeps
# printing the headline BOTH ways, which is what makes that checkable rather than asserted:
# re-including the pair returns A3 to K7's shipped 3.15 / 4.12 / 4.60 / 4.85 dB from 3.36 / 4.39 /
# 4.80 / 5.05, i.e. it SHRINKS the headline, so nothing here is chosen to flatter it.
DEFECT_TOKEN = "gain-n12"

# The settings a clean/OD pair must agree on for the endpoint difference to be the mix ratio.
PAIR_KEYS = ("drive", "gruntIdx", "attackIdx", "master")

SWEEPS = ["sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6"]

# A3 as recorded in reference-sources.md §1: "~5-7 dB over 100-400 Hz".
A3_BAND = (100.0, 400.0)

# Above this ratio of (rms shape about the mean) / |mean|, calling the residual "a level error"
# is not defensible.  0.25 is generous -- GATE K5 used 0.24 to justify exactly that phrase for
# the LEVEL law, so the same bar is applied here rather than a new one chosen to suit the answer.
LEVEL_ERROR_MAX_RATIO = 0.25


# --------------------------------------------------------------------------------------------
# shared machinery
# --------------------------------------------------------------------------------------------
def endpoints(caps, exclude_defect):
    """-> (clean_files, od_files).  The two exact-zero endpoints of the shipped mixing network."""
    cl = [f for f, c in caps.items()
          if c.get("settings", {}).get("blend") == 0.0 and MG.is_od(f)]
    od = [f for f, c in caps.items()
          if c.get("settings", {}).get("blend") == 1.0
          and c.get("settings", {}).get("level") == 1.0 and MG.is_od(f)]
    if exclude_defect:
        od = [f for f in od if DEFECT_TOKEN not in f]
    return sorted(cl), sorted(od)


def pair_up(caps, cl, od):
    """-> [(clean_file, od_file, drive, attackIdx, gruntIdx)] for every settings-matched pair."""
    out = []
    for fc in cl:
        sc = caps[fc]["settings"]
        for fo in od:
            so = caps[fo]["settings"]
            if all(sc[k] == so[k] for k in PAIR_KEYS):
                out.append((fc, fo, sc["drive"], sc["attackIdx"], sc["gruntIdx"]))
    return out


def excess_curve(absfr, pairs, nonhf, sweep):
    """-> per-band mean of (r_model - r_pedal) over the pairs, where r = clean - OD, in dB.

    No gain match enters anywhere: `absfr` has already undone the per-row broadband null gain, and
    both endpoints traverse the same downstream chain, so their difference IS the mixed ratio."""
    acc = []
    for fc, fo, *_ in pairs:
        if (fc, sweep) not in absfr or (fo, sweep) not in absfr:
            continue
        mc, qc = absfr[(fc, sweep)]
        mo, qo = absfr[(fo, sweep)]
        acc.append((mc[nonhf] - mo[nonhf]) - (qc[nonhf] - qo[nonhf]))
    if not acc:
        sys.exit(f"GATE M FAIL: no pairs survive at {sweep} -- an empty mean is not a measurement")
    return np.mean(acc, axis=0), len(acc)


# --------------------------------------------------------------------------------------------
# M1 -- known answer against GATE K7 itself
# --------------------------------------------------------------------------------------------
def gate_m1(absfr, caps, nonhf, out):
    print("-- M1: known answer -- reproduce GATE K7's pooled headline through this code path --")
    cl, od = endpoints(caps, exclude_defect=False)      # K7 ships WITHOUT the exclusion
    pairs = pair_up(caps, cl, od)
    mine, ref = {}, {}
    for sw in SWEEPS:
        curve, n = excess_curve(absfr, pairs, nonhf, sw)
        mine[sw] = float(curve.mean())
        # K7's own arithmetic, recomputed inline: mean over pairs of the band-mean, rather than
        # band-mean of the mean over pairs.  Both are means over the same rectangle, so they must
        # agree exactly -- and if they ever did not, one of the two is subsetting silently.
        rows = []
        for fc, fo, *_ in pairs:
            mc, qc = absfr[(fc, sw)]
            mo, qo = absfr[(fo, sw)]
            rows.append(float(np.mean(mc[nonhf] - mo[nonhf]) - np.mean(qc[nonhf] - qo[nonhf])))
        ref[sw] = float(np.mean(rows))
    worst = max(abs(mine[s] - ref[s]) for s in SWEEPS)
    if worst > 1e-9:
        sys.exit(f"GATE M1 FAIL: this tool's pooled excess does not reproduce K7's arithmetic "
                 f"(worst {worst:.3e}) -- membership or band selection differs, fix that first")
    print(f"   {'stimulus':<12}{'K7 arithmetic':>15}{'this tool':>12}")
    for sw in SWEEPS:
        print(f"   {sw.replace('sweep_', ''):<12}{ref[sw]:>15.2f}{mine[sw]:>12.2f}")

    # Mutation control: the check above compares two orderings of one mean, so it would pass for
    # ANY band set.  Dropping a band must move the number, or M1 is certifying nothing.
    drop = np.arange(1, len(nonhf))
    mutated = float(excess_curve(absfr, pairs, nonhf, SWEEPS[0])[0][drop].mean())
    if abs(mutated - mine[SWEEPS[0]]) < 1e-6:
        sys.exit("GATE M1 FAIL: dropping a band did not move the pooled excess -- the band "
                 "selection is not reaching the statistic, so M1 is vacuous")
    print(f"   M1 OK   reproduces to {worst:.1e}; mutation (drop 1 band) moves it "
          f"{mine[SWEEPS[0]]:.2f} -> {mutated:.2f}, so the check is not vacuous")
    out["m1"] = {"worst": worst, "pooled": mine, "mutation": mutated}
    return pairs


# --------------------------------------------------------------------------------------------
# M2 -- membership, asserted
# --------------------------------------------------------------------------------------------
def gate_m2(caps, pairs, out):
    print("\n-- M2: membership, asserted rather than assumed --")
    cl, od = endpoints(caps, exclude_defect=False)
    defect_pairs = [p for p in pairs if DEFECT_TOKEN in p[1]]
    if not defect_pairs:
        sys.exit(f"GATE M2 FAIL: no '{DEFECT_TOKEN}' row found among K7's pairs.  This gate exists "
                 f"partly to quantify that row's contribution; if the capture set has changed, "
                 f"re-derive M3's conclusion rather than assuming it still holds")
    print(f"   {len(cl)} pure-clean, {len(od)} pure-OD captures -> {len(pairs)} settings-matched "
          f"pairs on {PAIR_KEYS}")
    print(f"   {'drive':>6}{'atk':>5}{'grunt':>7}  OD capture")
    for fc, fo, dr, atk, gr in sorted(pairs, key=lambda r: (r[2], r[3])):
        tag = (f"   <-- {DEFECT_TOKEN} (12 dB lower operating point; excluded to keep the pool at "
               f"ONE operating point -- s111, see DEFECT_TOKEN)" if DEFECT_TOKEN in fo else "")
        print(f"   {dr:>6}{atk:>5}{gr:>7}  {fo.replace('_base-od.wav', '')}{tag}")

    drives = sorted({p[2] for p in pairs})
    print(f"\n   drive spread: {drives}  ({len(drives)} settings) -- a real axis, so the excess "
          f"CAN be read against drive")
    # State the confound rather than letting a later reader infer independence that is not there.
    by_drive = {d: sorted({p[3] for p in pairs if p[2] == d}) for d in drives}
    print(f"   ⚠ drive x attack are PARTIALLY CONFOUNDED across these pairs: "
          + ", ".join(f"drive {d} -> attackIdx {by_drive[d]}" for d in drives))
    print( "     so a per-drive column is suggestive of drive, not clean of attack.  M6 reads the "
           "stimulus axis instead, which is within-pair and carries no such confound.")
    out["m2"] = {"n_clean": len(cl), "n_od": len(od), "n_pairs": len(pairs),
                 "n_defect_pairs": len(defect_pairs), "drives": drives,
                 "attack_by_drive": {str(k): v for k, v in by_drive.items()}}
    print(f"   M2 OK   {len(pairs)} pairs, {len(defect_pairs)} of them carrying {DEFECT_TOKEN}")


# --------------------------------------------------------------------------------------------
# M3 -- de-contamination
# --------------------------------------------------------------------------------------------
def gate_m3(absfr, caps, nonhf, out):
    print(f"\n-- M3: what does the '{DEFECT_TOKEN}' row do to K7's headline? --")
    res = {}
    for label, excl in (("as K7 ships (incl. defect)", False), ("defect EXCLUDED", True)):
        cl, od = endpoints(caps, exclude_defect=excl)
        pairs = pair_up(caps, cl, od)
        vals = [float(excess_curve(absfr, pairs, nonhf, sw)[0].mean()) for sw in SWEEPS]
        res[label] = {"n_pairs": len(pairs), "excess": vals}
        print(f"   {label:<28}n={len(pairs)}  " + "".join(f"{v:>9.2f}" for v in vals))
    a = res["as K7 ships (incl. defect)"]["excess"]
    b = res["defect EXCLUDED"]["excess"]
    d = [y - x for x, y in zip(a, b)]
    print(f"   {'delta (excluded - shipped)':<28}      " + "".join(f"{v:>9.2f}" for v in d))
    print(f"\n   => the defect row is {res['as K7 ships (incl. defect)']['n_pairs'] - res['defect EXCLUDED']['n_pairs']}"
          f" of {res['as K7 ships (incl. defect)']['n_pairs']} pairs and pulls the headline DOWN by "
          f"{min(d):.2f}-{max(d):.2f} dB at every stimulus level.")
    print( "      The sign matters: excluding it makes A3 LARGER, so the promotion in s103 is not")
    print( "      at risk -- but the quoted size should be the excluded one.")
    out["m3"] = res
    return b


# --------------------------------------------------------------------------------------------
# M4 -- the decomposition
# --------------------------------------------------------------------------------------------
def selections(fb):
    return {
        "all non-HF": np.arange(len(fb)),
        "drop lowest band": np.array([j for j, f in enumerate(fb) if f > fb[0] + 0.5]),
        "drop lowest + >5k": np.array([j for j, f in enumerate(fb)
                                       if f > fb[0] + 0.5 and f < 5000.0]),
        "100-400 Hz (§1's band)": np.array([j for j, f in enumerate(fb)
                                            if A3_BAND[0] <= f <= A3_BAND[1]]),
    }


def gate_m4(absfr, caps, nonhf, fb, out):
    print("\n-- M4: is the excess an OFFSET or does it carry SHAPE? --")
    cl, od = endpoints(caps, exclude_defect=True)
    pairs = pair_up(caps, cl, od)
    C = {sw: excess_curve(absfr, pairs, nonhf, sw)[0] for sw in SWEEPS}

    # Floor guard first.  A dB difference built on a near-floor absolute reading is not a
    # measurement (`ratio-statistics-need-a-denominator-guard`).
    worst_m = worst_q = 1e9
    for sw in SWEEPS:
        for fc, fo, *_ in pairs:
            for fn in (fc, fo):
                m, q = absfr[(fn, sw)]
                worst_m = min(worst_m, float(np.min(m[nonhf])))
                worst_q = min(worst_q, float(np.min(q[nonhf])))
    if min(worst_m, worst_q) <= MG.SILENT_DB:
        sys.exit(f"GATE M4 FAIL: an endpoint reading touches the {MG.SILENT_DB} dB floor "
                 f"(model {worst_m:.1f}, pedal {worst_q:.1f}) -- the excess would be a difference "
                 f"of floor values, not a ratio")
    print(f"   floor guard: worst absolute reading model {worst_m:.1f} dB / pedal {worst_q:.1f} dB "
          f"against a {MG.SILENT_DB:.0f} dB floor -- clear")

    print(f"\n   per-band excess (model r - pedal r), mean over {len(pairs)} pairs")
    print(f"   {'Hz':>8}" + "".join(f"{s.replace('sweep_', ''):>10}" for s in SWEEPS))
    for j, f in enumerate(fb):
        print(f"   {f:>8.0f}" + "".join(f"{C[s][j]:>10.2f}" for s in SWEEPS))

    sels = selections(fb)
    if len(sels["drop lowest band"]) != len(fb) - 1:
        sys.exit(f"GATE M4 FAIL: the 'drop lowest band' selection holds "
                 f"{len(sels['drop lowest band'])} of {len(fb)} bands -- it is not dropping "
                 f"exactly one, so the robustness column is measuring something else")

    print(f"\n   {'selection':<24}{'n':>4}" + "".join(f"{s.replace('sweep_', ''):>10}" for s in SWEEPS))
    tab = {}
    for nm, s in sels.items():
        row = [float(C[sw][s].mean()) for sw in SWEEPS]
        tab[nm] = {"n": int(len(s)), "offset": row,
                   "shape_rms": [float(np.std(C[sw][s])) for sw in SWEEPS]}
        print(f"   {nm:<24}{len(s):>4}" + "".join(f"{v:>10.2f}" for v in row))

    print(f"\n   {'selection':<24}{'stimulus':>9}{'offset':>9}{'shape rms':>11}{'shape/offset':>14}")
    verdict = {}
    for nm, s in sels.items():
        for sw in ("sweep_clean", "sweep_drv_-6"):
            v = C[sw][s]
            r = float(np.std(v) / abs(v.mean()))
            verdict[(nm, sw)] = r
            print(f"   {nm:<24}{sw.replace('sweep_', ''):>9}{v.mean():>9.2f}"
                  f"{np.std(v):>11.2f}{r:>14.2f}")

    # COMPUTED verdict.  The claim under test is "the defect is a level one", broadband.
    broad = [verdict[(nm, sw)] for nm in sels if nm != "100-400 Hz (§1's band)"
             for sw in ("sweep_clean", "sweep_drv_-6")]
    band = [verdict[("100-400 Hz (§1's band)", sw)] for sw in ("sweep_clean", "sweep_drv_-6")]
    print(f"\n   bar: shape/offset <= {LEVEL_ERROR_MAX_RATIO:.2f} for 'a level error, not a "
          f"frequency-response error'\n       (GATE K5's own bar -- 0.24 justified exactly that "
          f"phrase for the LEVEL law)")
    if min(broad) <= LEVEL_ERROR_MAX_RATIO:
        print(f"   => BROADBAND: shape/offset reaches {min(broad):.2f} on some selection -- the "
              f"'level error' reading SURVIVES.")
    else:
        print(f"   => BROADBAND: shape/offset is {min(broad):.2f}-{max(broad):.2f} on EVERY "
              f"selection, all over the {LEVEL_ERROR_MAX_RATIO:.2f} bar.")
        print( "      ⛔ 'K7 says the defect is a LEVEL one' is NOT supported by K7.  The pooled")
        print( "         mean it was read from is blind to frequency by construction.")
    if max(band) <= LEVEL_ERROR_MAX_RATIO:
        print(f"   => WITHIN 100-400 Hz the ratio falls to {max(band):.2f}, so reference-sources §1's")
        print( "      '~5-7 dB over 100-400 Hz' IS a level statement -- and correct there.  What")
        print( "      does not survive is extending it to the broadband statistic.")
    else:
        print(f"   => WITHIN 100-400 Hz the ratio is still {min(band):.2f}-{max(band):.2f}; even §1's")
        print( "      own band is not offset-dominated at every stimulus level.")
    out["m4"] = {"floor": {"model": worst_m, "pedal": worst_q},
                 "bands": [float(x) for x in fb],
                 "curves": {s: [float(x) for x in C[s]] for s in SWEEPS},
                 "table": tab,
                 "ratio": {f"{nm}|{sw}": v for (nm, sw), v in verdict.items()},
                 "bar": LEVEL_ERROR_MAX_RATIO}
    return pairs, C


# --------------------------------------------------------------------------------------------
# M5 -- is the shape real?
# --------------------------------------------------------------------------------------------
def gate_m5(absfr, pairs, nonhf, out):
    print("\n-- M5: is that shape carried by all the pairs, or by one of them? --")
    res = {}
    for sw in ("sweep_clean", "sweep_drv_-6"):
        S = []
        for fc, fo, *_ in pairs:
            mc, qc = absfr[(fc, sw)]
            mo, qo = absfr[(fo, sw)]
            v = (mc[nonhf] - mo[nonhf]) - (qc[nonhf] - qo[nonhf])
            S.append(v - v.mean())                    # de-mean: shape only, offset removed
        S = np.array(S)
        cors = []
        for k in range(len(S)):
            others = np.mean([S[m] for m in range(len(S)) if m != k], axis=0)
            cors.append(float(np.corrcoef(S[k], others)[0, 1]))
        res[sw] = {"loo_corr": cors,
                   "per_pair_rms": [float(np.std(s)) for s in S],
                   "mean_rms": float(np.std(S.mean(axis=0)))}
        lbl = [f"d{p[2]}/a{p[3]}" for p in pairs]
        print(f"   {sw.replace('sweep_', ''):>9}  leave-one-out corr vs mean of the others: "
              + "  ".join(f"{l} {c:+.2f}" for l, c in zip(lbl, cors)))
        if min(cors) <= 0.0:
            sys.exit(f"GATE M5 FAIL: at {sw} a pair's shape is uncorrelated or anti-correlated "
                     f"with the rest ({min(cors):+.2f}) -- the mean curve is then an average of "
                     f"disagreeing curves and must not be read as a structure")
    lo = min(min(r["loo_corr"]) for r in res.values())
    print(f"\n   M5 OK   every pair's shape agrees with the others (worst r = {lo:+.2f}), so the")
    print( "           curve is a coherent structure, not noise in a 4-row mean.")
    out["m5"] = res


# --------------------------------------------------------------------------------------------
# M6 -- does the shape move with drive?
# --------------------------------------------------------------------------------------------
def gate_m6(C, fb, out):
    print("\n-- M6: does the shape MOVE with stimulus level? --")
    print( "   A static gain error in the OD path is one number.  It cannot put a peak at one")
    print( "   frequency at low stimulus and a different frequency at high stimulus.")
    print(f"   {'stimulus':<12}{'peak of shape':>16}{'value dB':>10}{'@100-400':>10}{'@508-1016':>11}")
    res = {}
    for sw in SWEEPS:
        v = C[sw] - C[sw].mean()
        # ignore the lowest band: M4 shows it is the largest and most pair-variable term, and a
        # band-edge maximum would decide this gate on the least trustworthy point.
        interior = np.array([j for j, f in enumerate(fb) if f > fb[0] + 0.5])
        k = interior[int(np.argmax(v[interior]))]
        lo = float(np.mean([x for x, f in zip(C[sw], fb) if A3_BAND[0] <= f <= A3_BAND[1]]))
        mid = float(np.mean([x for x, f in zip(C[sw], fb) if 500.0 <= f <= 1100.0]))
        res[sw] = {"peak_hz": float(fb[k]), "peak_db": float(v[k]), "a3band": lo, "mid": mid}
        print(f"   {sw.replace('sweep_', ''):<12}{fb[k]:>13.0f} Hz{v[k]:>10.2f}{lo:>10.2f}{mid:>11.2f}")
    peaks = [res[s]["peak_hz"] for s in SWEEPS]
    lo_t = [res[s]["a3band"] for s in SWEEPS]
    mid_t = [res[s]["mid"] for s in SWEEPS]
    print(f"\n   100-400 Hz across stimulus: {lo_t[0]:.2f} -> {lo_t[-1]:.2f} dB "
          f"(spread {max(lo_t) - min(lo_t):.2f})")
    print(f"   508-1016 Hz across stimulus: {mid_t[0]:.2f} -> {mid_t[-1]:.2f} dB "
          f"(spread {max(mid_t) - min(mid_t):.2f})")
    if max(peaks) / min(peaks) > 1.5 or (max(mid_t) - min(mid_t)) > 2.0:
        print(f"\n   => the structure MOVES: the shape's peak runs {min(peaks):.0f} -> "
              f"{max(peaks):.0f} Hz across stimulus, and the 508-1016 Hz term swings "
              f"{max(mid_t) - min(mid_t):.2f} dB while §1's 100-400 Hz band holds to "
              f"{max(lo_t) - min(lo_t):.2f} dB.")
        print( "      A drive-DEPENDENT frequency structure is not a level error and not a fixed")
        print( "      linear network -- which is outside what sessions 50/52/53 searched, so it")
        print( "      does not contradict them; it is a region neither ruled out.")
    else:
        print("\n   => the structure does NOT move materially with stimulus; a static reading is "
              "defensible.")
    out["m6"] = res


# --------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    bands, caps = MG.load(a.report)[0], MG.load(a.report)[1]
    idx = [i for i, b in enumerate(bands) if MG.GRADE_LO <= b <= MG.GRADE_HI]
    absfr, _silent = K.absolute_fr(caps, idx)
    nonhf = [j for j, i in enumerate(idx) if bands[i] < K.HF_HZ]
    fb = np.array([bands[idx[j]] for j in nonhf])

    print(f"GATE M -- the A3 clean/OD imbalance, per band and per drive   [{a.report}]")
    print(f"  {len(caps)} captures, {len(idx)} graded bands, {len(nonhf)} non-HF "
          f"(< {K.HF_HZ:.0f} Hz, HF excluded per GATE I)")
    print( "  No render, no gain match, no fit: both endpoints traverse the same downstream chain.\n")

    out = {"report": a.report}
    gate_m1(absfr, caps, nonhf, out)
    pairs_all = pair_up(caps, *endpoints(caps, exclude_defect=False))
    gate_m2(caps, pairs_all, out)
    gate_m3(absfr, caps, nonhf, out)
    pairs, C = gate_m4(absfr, caps, nonhf, fb, out)
    gate_m5(absfr, pairs, nonhf, out)
    gate_m6(C, fb, out)

    print("\n== GATE M: all sub-gates passed ==")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, default=float)
        print(f"   wrote {a.json}")


if __name__ == "__main__":
    main()
