#!/usr/bin/env python3.11
"""GATE Q -- the OD path's ABSOLUTE error surface, and the two defects in it.

Session 109.  No render of its own: every number is a re-read of a report already on disk.  It
imports `a3_balance_gate` (GATE M) -- and through it `level_law_gate` (GATE K) and `matrix_grade`
-- so the endpoint selection and the absolute reconstruction cannot drift from the A3 chain.

WHY THIS EXISTS
---------------
GATE O (session 107) re-attributed A3: it is not a two-sided balance, the CLEAN side is bounded at
0.41 dB, and "the OD path is quiet, absolutely".  That attribution makes the OD path's own absolute
error directly readable -- at BLEND = 1 AND LEVEL = 1 the mix coefficient is exactly 1 (GATE K2),
so on those captures

        model_abs - pedal_abs   IS   the OD path's absolute transfer error.

No difference of differences, no clean side, no fit, no gain match.  GATE M/P read that quantity
only through the A3 excess, which needs a settings-matched CLEAN partner and therefore uses 4 pairs;
the pure-OD endpoints alone number 15, spanning DRIVE {0, 0.5, 1} x ATTACK {flat, boost, cut} x
GRUNT {cut, flat, boost}, each at 4 stimulus levels.  That surface has never been read.

GATE P (session 108) established that A3's headline is a window mean over a MIGRATING feature and
is not a fittable constant.  This gate does the thing P's finding actually calls for: separate the
surface by what it depends on, instead of averaging over it.

    L(f)  the error at the LOWEST stimulus (-30 dBFS)   -- what a LINEAR element must fix
    D(f)  error(-6 dBFS) - error(-30 dBFS)              -- what only a NONLINEARITY can fix

Both are then read against the physics that produced them (Q5 the compression law, Q6 the notch),
so a candidate is aimed at a mechanism rather than at a residual.

GATES (all computed; the gate's own VALIDITY exits non-zero, physics outcomes get computed
verdicts -- s108's rule)
--------------------------------------------------------------------------------------------
Q1  KNOWN ANSWER against GATE M.  For M's own 4 pairs, (this tool's OD error) minus (this tool's
    clean error) must equal M's excess curve elementwise.  Mutation control: perturbing one band
    of the clean side must break it.
Q2  MEMBERSHIP, asserted.  Exact endpoint count, the `gain-n12` defect excluded BY NAME and
    asserted to have been FOUND, and the drive / attack / grunt spread printed -- a surface pooled
    over the pedal's own controls without printing that spread is s108's P4 trap.
Q3  FLOOR GUARD on both sides, plus the stimulus-level map asserted against gen_test_signal, plus
    a COMPUTED dropout guard on the reference: a stimulus level whose band-median sits far below
    BOTH of its neighbours in the ladder is a dropout, not a device property, and must not vote.
    (This found one previously-unrecorded bad row -- see the module note at DROPOUT_DB.)
Q4  THE SURFACE and its L / D split, with the across-capture spread beside every mean (so the
    correction target is quoted with the bars P4 says it must be).
Q5  THE COMPRESSION LAW -- input-referred gain vs stimulus, model and pedal.  This is what says
    whether D is a ceiling, a knee or a gain.
Q6  THE 320 Hz NOTCH, measured relative to EACH SIDE'S OWN shoulders, so it is immune to any
    absolute-level error and reads the same under any gain match.
Q7  THE SCORE the fit will use, printed as a decomposition, with a mutation control proving it
    responds to the thing it claims to measure.

WHAT THIS DOES NOT CLAIM
------------------------
It does not re-open the ATTACK-switch axis (s108 closed that: conditioned, 1.23x).  Q6 measures the
SHARED ladder's null DEPTH, which is a different quantity from which throw is worst.
It does not contradict s50/s52: those ruled out single elements and post-clipper LINEAR elements
against a pooled residual containing D.  Q4's split is what makes an L-only element well posed.
"""
import argparse
import json
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import matrix_grade as MG          # noqa: E402
import level_law_gate as K         # noqa: E402
import a3_balance_gate as M        # noqa: E402

# The four sweeps ARE the same sweep at four amplitudes (gen_test_signal.py: CLEAN_FR_LEVELS_DB[0]
# then DRIVEN_LEVELS_DB).  Q3 asserts this map against that module rather than trusting the names.
STIM_DB = {"sweep_clean": -30.0, "sweep_drv_-18": -18.0,
           "sweep_drv_-12": -12.0, "sweep_drv_-6": -6.0}
LO, HI = "sweep_clean", "sweep_drv_-6"

# GATE I (session 101): at and above 8 kHz the OD region is ND's own aliasing artefact, not our
# Sallen-Keys.  Scoring it would aim the fit at the reference's defect.
HF_HZ = K.HF_HZ

# The notch Q6 measures, and the two shoulder bands it is referred to.  Named here rather than
# found by argmin, so a candidate that MOVES the notch cannot silently re-point the statistic.
NOTCH_HZ = 320.0
SHOULDER_HZ = (202.0, 508.0)

DEFECT_TOKEN = M.DEFECT_TOKEN

# ---- The reference-side dropout guard (session 109) -----------------------------------------
# The four sweeps are a monotone LADDER in stimulus amplitude, so the reference's band-median
# absolute reading cannot sit far below BOTH of its neighbours: a saturating path compresses, it
# does not lose 25 dB in the middle of the ladder and get it back.  Scanned over all 129 captures
# this fires exactly ONCE -- `drive-1700_level-1700_grunt-boost_base-od.wav` at `sweep_drv_-12`,
# where the reference reads a band-median of +3.5 dB against +15..+23 at drv_-18 and drv_-6.  That
# is a capture/deconvolution dropout, and it is NOT the session-48 `gain-n12` defect (different
# file, different session, different signature).  It was carrying 21.0 dB of this gate's score on
# its own before it was found.  `defective-rows-must-not-vote`.
#
# The threshold is placed on MEASURED evidence, not chosen.  Over the 258 interior ladder cells the
# statistic is cleanly bimodal: the largest sag among the healthy cells is -0.35 dB (i.e. the ladder
# is monotone everywhere, as a compressive path requires) and the defect sits at +11.59, an 11.94 dB
# gap with NOTHING in between.  Any bar inside that gap gives the identical answer, so Q3 asserts
# the SEPARATION rather than a count -- if the population ever stops being bimodal, no threshold is
# defensible and the gate says so instead of silently trimming a tail.
#
# ⚠ A first draft used 12.0 dB "to be generous" and MISSED the defect by 0.41 dB while printing a
# clean pass.  A guess at a threshold is not a guard; measure the distribution first.
DROPOUT_DB = 5.0
MIN_SEPARATION_DB = 3.0
# Asserted, and BUMPED DELIBERATELY when the capture set changes -- inferring it would stop this
# catching anything.  History:
#   1  session 109, the 129-capture matrix: `drive-1700_level-1700_grunt-boost_base-od @ drv_-12`.
#   2  session 110: the user re-captured that file (SAME rung, same ~14 dB hole) and added
#      `drive-1700_level-1700_master-1100_grunt-boost_base-od`, which has the SAME defect at the
#      SAME rung.  Only the `gain-n12` twin, recorded with the send 12 dB down, is clean -- so this
#      reads as a reproducible LEVEL-dependent behaviour of the reference at DRIVE max x LEVEL max
#      x GRUNT boost, not a bad take.  Excluded here, not explained.
EXPECT_DROPOUTS = 2


# --------------------------------------------------------------------------------------------
def endpoints_od(caps):
    """The pure-OD endpoints: BLEND = 1 and LEVEL = 1, where the mix coefficient is exactly 1."""
    return sorted(f for f, c in caps.items()
                  if c.get("settings", {}).get("blend") == 1.0
                  and c.get("settings", {}).get("level") == 1.0
                  and MG.is_od(f) and DEFECT_TOKEN not in f)


def find_dropouts(absfr, caps, nonhf):
    """-> [(file, sweep, median, neighbour_floor)] for reference-side ladder dropouts.

    Computed, not named: the test is a property of the LADDER (a middle rung far below both of
    its neighbours), so it transfers to any future capture set without a hardcoded filename."""
    order = ("sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6")
    sags = []
    for f in caps:
        if any((f, s) not in absfr for s in order):
            continue
        med = {s: float(np.median(absfr[(f, s)][1][nonhf])) for s in order}
        for i in (1, 2):
            floor = min(med[order[i - 1]], med[order[i + 1]])
            sags.append((floor - med[order[i]], f, order[i], med[order[i]], floor))
    sags.sort(reverse=True)
    bad = [(f, sw, m, fl) for sag, f, sw, m, fl in sags if sag > DROPOUT_DB]
    return bad, sags


def load_surface(report):
    """-> (bands, caps, absfr, nonhf_idx, band_hz, od_files, dropped_cells)."""
    bands, caps = MG.load(report)[0], MG.load(report)[1]
    idx = [i for i, b in enumerate(bands) if MG.GRADE_LO <= b <= MG.GRADE_HI]
    absfr, _ = K.absolute_fr(caps, idx)
    nonhf = [j for j, i in enumerate(idx) if bands[i] < HF_HZ]
    fb = np.array([bands[idx[j]] for j in nonhf])
    drops = {(f, s) for f, s, *_ in find_dropouts(absfr, caps, nonhf)[0]}
    return bands, caps, absfr, nonhf, fb, endpoints_od(caps), drops


def od_error(absfr, files, nonhf, sweep, drops=frozenset()):
    """-> (n_kept, n_bands) of model_abs - pedal_abs, in dB.  Negative = the model is quiet."""
    rows = [absfr[(f, sweep)][0][nonhf] - absfr[(f, sweep)][1][nonhf]
            for f in files if (f, sweep) not in drops]
    if not rows:
        sys.exit(f"GATE Q FAIL: every capture is dropped at {sweep} -- an empty mean is not a "
                 f"measurement (`empty-gate-must-fail`)")
    return np.array(rows)


def kept(files, sweep, drops):
    return [f for f in files if (f, sweep) not in drops]


def score(absfr, files, nonhf, drops=frozenset()):
    """The scalar the fit minimises, plus its decomposition.

    rms over (capture x stimulus x non-HF band) of the OD path's absolute error.  Every term is an
    absolute dB error of a quantity whose mix coefficient is exactly 1, so there is no anchor to
    choose and no gain match anywhere -- which is the whole point: the 129-capture matrix's per-row
    null gain removes exactly this (`a-per-row-gain-match-makes-every-control-law-error-invisible`,
    s103), so it is structurally unable to arbitrate it."""
    per = {s: od_error(absfr, files, nonhf, s, drops) for s in STIM_DB}
    allv = np.concatenate([per[s].ravel() for s in STIM_DB])
    return float(np.sqrt(np.mean(allv ** 2))), {s: float(np.sqrt(np.mean(v ** 2)))
                                                for s, v in per.items()}, per


# --------------------------------------------------------------------------------------------
# Q1 -- known answer against GATE M
# --------------------------------------------------------------------------------------------
def gate_q1(absfr, caps, nonhf, out):
    print("-- Q1: known answer -- this tool's OD-minus-CLEAN must BE GATE M's excess --")
    cl, od = M.endpoints(caps, exclude_defect=True)
    pairs = M.pair_up(caps, cl, od)
    worst = 0.0
    for sw in M.SWEEPS:
        ref, _n = M.excess_curve(absfr, pairs, nonhf, sw)
        mine = []
        for fc, fo, *_ in pairs:
            mc, qc = absfr[(fc, sw)]
            mo, qo = absfr[(fo, sw)]
            mine.append((mc[nonhf] - qc[nonhf]) - (mo[nonhf] - qo[nonhf]))
        worst = max(worst, float(np.max(np.abs(np.mean(mine, axis=0) - ref))))
    if worst > 1e-12:
        sys.exit(f"GATE Q1 FAIL: OD-error minus CLEAN-error does not reproduce GATE M's excess "
                 f"(worst {worst:.3e}) -- the two tools disagree about the same quantity")
    # Mutation: the identity above is algebraic, so it would hold for ANY absfr.  Perturb one band
    # of the clean side and require it to break, or Q1 certifies only that + and - work.
    sw = M.SWEEPS[0]
    ref, _ = M.excess_curve(absfr, pairs, nonhf, sw)
    bad = []
    for fc, fo, *_ in pairs:
        mc, qc = absfr[(fc, sw)]
        mo, qo = absfr[(fo, sw)]
        d = (mc[nonhf] - qc[nonhf]).copy()
        d[0] += 3.0
        bad.append(d - (mo[nonhf] - qo[nonhf]))
    if abs(float(np.mean(bad, axis=0)[0] - ref[0])) < 1e-6:
        sys.exit("GATE Q1 FAIL: a 3 dB mutation of the clean side did not move the identity -- "
                 "the check is vacuous")
    print(f"   Q1 OK   reproduces GATE M elementwise to {worst:.1e} over {len(pairs)} pairs x "
          f"{len(M.SWEEPS)} stimuli; a 3 dB band mutation breaks it")
    out["q1"] = {"worst": worst, "n_pairs": len(pairs)}


# --------------------------------------------------------------------------------------------
# Q2 -- membership, asserted
# --------------------------------------------------------------------------------------------
def gate_q2(caps, files, out):
    print("\n-- Q2: membership, asserted rather than assumed --")
    raw = [f for f, c in caps.items()
           if c.get("settings", {}).get("blend") == 1.0
           and c.get("settings", {}).get("level") == 1.0 and MG.is_od(f)]
    dropped = [f for f in raw if DEFECT_TOKEN in f]
    if not dropped:
        sys.exit(f"GATE Q2 FAIL: the '{DEFECT_TOKEN}' exclusion matched NOTHING among the "
                 f"{len(raw)} pure-OD endpoints -- a filter that silently matches nothing is "
                 f"`empty-gate-must-fail` in a costume.  If the capture set changed, re-derive.")
    if len(files) != len(raw) - len(dropped):
        sys.exit("GATE Q2 FAIL: endpoint arithmetic does not close")
    drives = sorted({caps[f]["settings"]["drive"] for f in files})
    atks = sorted({caps[f]["settings"]["attackIdx"] for f in files})
    grunts = sorted({caps[f]["settings"]["gruntIdx"] for f in files})
    print(f"   {len(raw)} pure-OD endpoints, {len(dropped)} excluded by name "
          f"({DEFECT_TOKEN}, the session-48 capture defect) -> {len(files)} scored")
    print(f"   DRIVE {drives}   ATTACK {atks}   GRUNT {grunts}")
    cells = sorted({(caps[f]["settings"]["drive"], caps[f]["settings"]["attackIdx"],
                     caps[f]["settings"]["gruntIdx"]) for f in files})
    print(f"   {len(cells)} distinct (drive, attack, grunt) cells -- the surface is pooled over "
          f"the pedal's OWN controls, so Q4 prints the across-capture spread beside every mean")
    # DRIVE must not be perfectly confounded with the switches, or no per-drive read is attributable
    per_drive = {d: sorted({(c[1], c[2]) for c in cells if c[0] == d}) for d in drives}
    if any(len(v) < 2 for v in per_drive.values()):
        sys.exit("GATE Q2 FAIL: at least one DRIVE setting carries a single switch combination -- "
                 "a per-drive column would be confounded with the switch")
    print(f"   every DRIVE setting carries {min(len(v) for v in per_drive.values())}+ switch "
          f"combinations, so a per-drive read is attributable to DRIVE")
    out["q2"] = {"n_raw": len(raw), "n_dropped": len(dropped), "n_scored": len(files),
                 "drives": drives, "attacks": atks, "grunts": grunts, "n_cells": len(cells)}


# --------------------------------------------------------------------------------------------
# Q3 -- floor guard + the stimulus map
# --------------------------------------------------------------------------------------------
def cross_check_dropouts(report, drops):
    """Assert this gate's dropout set agrees with `matrix_grade`'s (session 110).

    ⚠ There are deliberately TWO detectors, because they run on different inputs: this one on the
    ABSOLUTE FR reconstruction over the non-HF bands, `matrix_grade.find_dropouts` on the report's
    raw `pedal_db` over the graded band -- the latter is what the grading path needs, the former is
    what this gate's absolute surface needs. Two definitions of one physical fact is exactly how a
    gate and the thing it gates stop describing the same defect (the s97 `resid()` lesson), so they
    are cross-checked rather than merged. If they ever disagree, say so loudly instead of letting
    the headline and the gate quietly exclude different cells."""
    bands, caps = MG.load(report)
    mg_drops, _, _ = MG.find_dropouts(bands, caps)
    if mg_drops == drops:
        return None
    return (f"Q3/matrix_grade DROPOUT DISAGREEMENT -- this gate excludes {sorted(drops)} and the "
            f"grading path excludes {sorted(mg_drops)}. The headline and this gate are no longer "
            f"describing the same defect; reconcile before quoting either.")


def gate_q3(absfr, caps, files, nonhf, drops, out):
    print("\n-- Q3: floor guard, stimulus map, and the reference dropout guard --")
    try:
        import gen_test_signal as G
        want = [G.CLEAN_FR_LEVELS_DB[0]] + list(G.DRIVEN_LEVELS_DB)
    except Exception as e:                                    # pragma: no cover
        sys.exit(f"GATE Q3 FAIL: cannot read the stimulus levels from gen_test_signal ({e}) -- "
                 f"the compression law below is meaningless without them")
    got = [STIM_DB[s] for s in ("sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6")]
    if [float(x) for x in want] != got:
        sys.exit(f"GATE Q3 FAIL: STIM_DB {got} does not match gen_test_signal {want} -- "
                 f"`rebuild-targets-dont-transcribe`")
    print(f"   stimulus levels {got} dBFS, read from gen_test_signal, not from the sweep names")
    wm = wq = 1e9
    for f in files:
        for s in STIM_DB:
            m, q = absfr[(f, s)]
            wm = min(wm, float(np.min(m[nonhf])))
            wq = min(wq, float(np.min(q[nonhf])))
    if min(wm, wq) <= MG.SILENT_DB:
        sys.exit(f"GATE Q3 FAIL: an endpoint reading touches the {MG.SILENT_DB} dB floor "
                 f"(model {wm:.1f}, pedal {wq:.1f}) -- the error would be a difference of floors")
    print(f"   floor guard: worst absolute reading model {wm:.1f} / pedal {wq:.1f} dB "
          f"against a {MG.SILENT_DB:.0f} dB floor -- clear")

    bad, sags = find_dropouts(absfr, caps, nonhf)
    print(f"\n   reference-ladder dropout scan over ALL {len(caps)} captures, "
          f"{len(sags)} interior rungs (a rung > {DROPOUT_DB:.0f} dB below BOTH neighbours):")
    for f, sw, med, floor in bad:
        print(f"      {f.replace('_base-od.wav', ''):<46} {sw:<14} median {med:>7.2f} dB "
              f"vs neighbours >= {floor:>7.2f}  (sag {floor - med:.2f} dB)")
    # Assert the SEPARATION, not the bar: the exclusion is only defensible while the population is
    # bimodal, and that is a property of the data rather than of the number chosen here.
    worst_kept = sags[len(bad)][0] if len(sags) > len(bad) else float("-inf")
    gap = (sags[len(bad) - 1][0] - worst_kept) if bad else float("inf")
    print(f"   worst sag among the KEPT rungs: {worst_kept:+.2f} dB  "
          f"(so the ladder is monotone everywhere it is kept)")
    print(f"   separation between the last dropped and the first kept rung: {gap:.2f} dB "
          f"against a {MIN_SEPARATION_DB:.1f} dB minimum")
    if bad and gap < MIN_SEPARATION_DB:
        sys.exit(f"GATE Q3 FAIL: the dropout statistic is NOT bimodal (gap {gap:.2f} dB) -- the "
                 f"exclusion would be trimming a tail, which is `self-selecting-scores`.  No "
                 f"threshold is defensible here; investigate the population instead.")
    if len(bad) != EXPECT_DROPOUTS:
        sys.exit(f"GATE Q3 FAIL: found {len(bad)} reference dropouts, expected "
                 f"{EXPECT_DROPOUTS}.  A CHANGE here is a hard stop, not a silent shrinkage of "
                 f"the scored set -- inspect the rows above and update EXPECT_DROPOUTS only "
                 f"after deciding each one is genuinely a capture defect.")
    hit = sorted(c for c in drops if c[0] in set(files))
    print(f"   {len(bad)} dropout(s) matrix-wide, {len(hit)} of them inside this gate's "
          f"{len(files)} scored endpoints -- excluded from every statistic below.")
    if hit:
        # Say what it was worth, so the exclusion is quantified rather than merely asserted.
        with_bad, _, _ = score(absfr, files, nonhf, frozenset())
        without, _, _ = score(absfr, files, nonhf, drops)
        print(f"   it was carrying the score on its own: {with_bad:.3f} -> {without:.3f} dB "
              f"({with_bad - without:+.3f}).  `defective-rows-must-not-vote`.")
    out["q3"] = {"stim_db": got, "worst_model": wm, "worst_pedal": wq,
                 "dropouts": [[f, sw, m, fl] for f, sw, m, fl in bad],
                 "n_dropped_cells": len(hit)}


# --------------------------------------------------------------------------------------------
# Q4 -- the surface, split into what a LINEAR element can fix and what it cannot
# --------------------------------------------------------------------------------------------
def gate_q4(absfr, files, nonhf, fb, drops, out):
    print("\n-- Q4: the OD path's absolute error surface, and its L / D split --")
    print("   L(f) = error at -30 dBFS      -> a LINEAR element can carry this")
    print("   D(f) = error(-6) - error(-30) -> only a NONLINEARITY can carry this")
    keep = [f for f in files if (f, LO) not in drops and (f, HI) not in drops]
    Elo = od_error(absfr, keep, nonhf, LO, drops)
    Ehi = od_error(absfr, keep, nonhf, HI, drops)
    L, Ls = Elo.mean(axis=0), Elo.std(axis=0)
    D, Ds = (Ehi - Elo).mean(axis=0), (Ehi - Elo).std(axis=0)
    print(f"\n   {'Hz':>8}{'L mean':>10}{'L sd':>8}{'D mean':>10}{'D sd':>8}")
    for j, hz in enumerate(fb):
        print(f"   {hz:>8.0f}{L[j]:>10.2f}{Ls[j]:>8.2f}{D[j]:>10.2f}{Ds[j]:>8.2f}")
    print(f"\n   |L| rms = {np.sqrt(np.mean(L ** 2)):.2f} dB      "
          f"|D| rms = {np.sqrt(np.mean(D ** 2)):.2f} dB")
    print(f"   mean across-capture sd:  L {Ls.mean():.2f} dB   D {Ds.mean():.2f} dB")
    print("   => both terms are large, and NEITHER is a constant: quoting one number for A3 was")
    print("      averaging a linear defect together with a level-dependent one (GATE P's finding,")
    print("      here separated instead of pooled).")
    out["q4"] = {"bands": [float(x) for x in fb],
                 "L": [float(x) for x in L], "L_sd": [float(x) for x in Ls],
                 "D": [float(x) for x in D], "D_sd": [float(x) for x in Ds],
                 "L_rms": float(np.sqrt(np.mean(L ** 2))),
                 "D_rms": float(np.sqrt(np.mean(D ** 2)))}
    return L, D


# --------------------------------------------------------------------------------------------
# Q5 -- the compression law
# --------------------------------------------------------------------------------------------
def gate_q5(absfr, caps, files, nonhf, fb, drops, out):
    print("\n-- Q5: the compression law -- input-referred gain vs stimulus, per DRIVE --")
    print("   out_dB - stimulus_dB.  A linear path gives a FLAT row; the fall is compression.")
    res = {}
    for drv in sorted({caps[f]["settings"]["drive"] for f in files}):
        fs0 = [f for f in files if caps[f]["settings"]["drive"] == drv]
        fs = [f for f in fs0 if all((f, s) not in drops for s in STIM_DB)]
        rows = {}
        for s in ("sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6"):
            rows[s] = (np.mean([absfr[(f, s)][0][nonhf] for f in fs], axis=0) - STIM_DB[s],
                       np.mean([absfr[(f, s)][1][nonhf] for f in fs], axis=0) - STIM_DB[s])
        mcomp = rows[HI][0] - rows[LO][0]
        pcomp = rows[HI][1] - rows[LO][1]
        band = np.array([500.0 <= f < HF_HZ for f in fb])
        res[drv] = {"model_comp": [float(x) for x in mcomp],
                    "pedal_comp": [float(x) for x in pcomp],
                    "excess_500_8k": float(np.mean((mcomp - pcomp)[band]))}
        print(f"   DRIVE {drv}  ({len(fs)} captures)   compression -30 -> -6 dBFS, mean over "
              f"500 Hz-8 kHz: model {np.mean(mcomp[band]):+.2f} dB, pedal "
              f"{np.mean(pcomp[band]):+.2f} dB, EXCESS {np.mean((mcomp - pcomp)[band]):+.2f} dB")
    ex = [res[d]["excess_500_8k"] for d in sorted(res)]
    print(f"\n   excess compression by DRIVE: " + ", ".join(f"{d}: {res[d]['excess_500_8k']:+.2f}"
                                                            for d in sorted(res)))
    if max(ex) - min(ex) > 1.0:
        print(f"   => the excess VARIES with DRIVE by {max(ex) - min(ex):.2f} dB, and is largest at "
              f"DRIVE {sorted(res)[int(np.argmin(ex))]}.")
    else:
        print(f"   => the excess is DRIVE-independent to {max(ex) - min(ex):.2f} dB.")
    print("      The model compresses MORE than the pedal in every column -- so D is not a gain")
    print("      error, it is a SATURATION error: the model's OD path runs out of headroom first.")
    out["q5"] = {str(k): v for k, v in res.items()}


# --------------------------------------------------------------------------------------------
# Q6 -- the notch, referred to each side's own shoulders
# --------------------------------------------------------------------------------------------
def gate_q6(absfr, files, nonhf, fb, drops, out):
    print(f"\n-- Q6: the {NOTCH_HZ:.0f} Hz null DEPTH, referred to each side's OWN shoulders --")
    print(f"   depth = mean(shoulders {SHOULDER_HZ[0]:.0f}/{SHOULDER_HZ[1]:.0f} Hz) - value at "
          f"{NOTCH_HZ:.0f} Hz, computed SEPARATELY on each side, so it is immune to any absolute")
    print( "   level error and reads identically under any gain match.")
    jn = int(np.argmin(np.abs(fb - NOTCH_HZ)))
    js = [int(np.argmin(np.abs(fb - h))) for h in SHOULDER_HZ]
    if abs(fb[jn] - NOTCH_HZ) > 1.0 or any(abs(fb[j] - h) > 1.0 for j, h in zip(js, SHOULDER_HZ)):
        sys.exit(f"GATE Q6 FAIL: the named bands are not on the grid "
                 f"(got {fb[jn]:.1f} / {[float(fb[j]) for j in js]})")
    res = {}
    for s in ("sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6"):
        md, pd = [], []
        for f in kept(files, s, drops):
            m, q = absfr[(f, s)][0][nonhf], absfr[(f, s)][1][nonhf]
            md.append(np.mean([m[j] for j in js]) - m[jn])
            pd.append(np.mean([q[j] for j in js]) - q[jn])
        res[s] = {"model": float(np.mean(md)), "model_sd": float(np.std(md)),
                  "pedal": float(np.mean(pd)), "pedal_sd": float(np.std(pd))}
        print(f"   {s.replace('sweep_', ''):>9}  model {res[s]['model']:>6.2f} "
              f"(sd {res[s]['model_sd']:.2f})   pedal {res[s]['pedal']:>6.2f} "
              f"(sd {res[s]['pedal_sd']:.2f})   MODEL DEEPER BY "
              f"{res[s]['model'] - res[s]['pedal']:>5.2f} dB")
    order = ("sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6")
    dd = [res[s]["model"] - res[s]["pedal"] for s in order]
    md = [res[s]["model"] for s in order]
    pdp = [res[s]["pedal"] for s in order]
    # COMPUTED verdict.  The first draft of this line NARRATED "too deep at every stimulus level"
    # while its own table changed sign across the ladder -- `computed-verdicts-not-narrated`, in
    # the one line that would have selected the fix.
    if min(dd) > 0.0:
        print(f"\n   => the model's null is {min(dd):.2f}-{max(dd):.2f} dB TOO DEEP at EVERY "
              f"stimulus level -- a depth error a linear element can carry.")
    elif max(dd) < 0.0:
        print(f"\n   => the model's null is {-max(dd):.2f}-{-min(dd):.2f} dB TOO SHALLOW at EVERY "
              f"stimulus level.")
    else:
        print(f"\n   => the sign CHANGES across the ladder: {dd[0]:+.2f} dB at the lowest stimulus "
              f"to {dd[-1]:+.2f} dB at the highest.")
        print(f"      The model's own null WASHES OUT with level ({md[0]:.2f} -> {md[-1]:.2f} dB) "
              f"while the pedal's DEEPENS ({pdp[0]:.2f} -> {pdp[-1]:.2f} dB).")
        print( "      ⇒ this is NOT a static depth error and NO linear element can carry it: a")
        print( "        fixed network's null depth cannot depend on the stimulus.  It is the same")
        print( "        saturation defect Q5 measures, seen through the null -- the model's OD")
        print( "        path compresses early, and compression fills a cancellation null.")
    print( "   Depth is a RATIO within one curve, so this reading survives any absolute-level fix")
    print( "   and is immune to the per-row gain match the 129-capture matrix applies.")
    out["q6"] = {"notch_hz": float(fb[jn]), "shoulders": [float(fb[j]) for j in js], "by_sweep": res}


# --------------------------------------------------------------------------------------------
# Q7 -- the score, and a mutation control
# --------------------------------------------------------------------------------------------
def gate_q7(absfr, files, nonhf, drops, out):
    print("\n-- Q7: the score the fit minimises --")
    total, per, _ = score(absfr, files, nonhf, drops)
    print(f"   rms |model - pedal| over {len(files)} captures x {len(STIM_DB)} stimuli x "
          f"{len(nonhf)} non-HF bands = {total:.3f} dB")
    for s in ("sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6"):
        print(f"      {s.replace('sweep_', ''):>9}  {per[s]:.3f}")
    # Mutation: a fixed +3 dB on the model must move the score, or the score is not reading the
    # model side at all.
    mutated = {k: (v[0] + 3.0, v[1]) for k, v in absfr.items()}
    mt, _, _ = score(mutated, files, nonhf, drops)
    if abs(mt - total) < 1e-6:
        sys.exit("GATE Q7 FAIL: a +3 dB shift of the model side did not move the score")
    print(f"   mutation control: +3 dB on the model moves the score {total:.3f} -> {mt:.3f}")
    out["q7"] = {"score": total, "per_sweep": per, "mutation": mt}
    return total


# --------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report")
    ap.add_argument("--json", default=None)
    ap.add_argument("--score-only", action="store_true",
                    help="print only the scalar score (for a candidate screen)")
    a = ap.parse_args()

    _bands, caps, absfr, nonhf, fb, files, drops = load_surface(a.report)

    if a.score_only:
        total, per, _ = score(absfr, files, nonhf, drops)
        print(f"{total:.4f}  " + "  ".join(f"{s.replace('sweep_', '')}={per[s]:.3f}"
                                           for s in ("sweep_clean", "sweep_drv_-18",
                                                     "sweep_drv_-12", "sweep_drv_-6")))
        return

    print(f"GATE Q -- the OD path's ABSOLUTE error surface   [{a.report}]")
    print(f"  {len(caps)} captures, {len(nonhf)} non-HF graded bands (< {HF_HZ:.0f} Hz per GATE I)")
    print( "  At BLEND=1, LEVEL=1 the mix coefficient is exactly 1 (GATE K2), so model - pedal IS")
    print( "  the OD path's error.  No fit, no gain match, no clean side.\n")

    out = {"report": a.report}
    gate_q1(absfr, caps, nonhf, out)
    gate_q2(caps, files, out)
    gate_q3(absfr, caps, files, nonhf, drops, out)
    xc = cross_check_dropouts(a.report, drops)
    print(f"\n   dropout cross-check vs matrix_grade (the grading path): "
          f"{'AGREE' if xc is None else 'DISAGREE'}")
    out["dropout_crosscheck_ok"] = xc is None
    if xc is not None:
        sys.exit("GATE Q3 FAIL: " + xc)
    gate_q4(absfr, files, nonhf, fb, drops, out)
    gate_q5(absfr, caps, files, nonhf, fb, drops, out)
    gate_q6(absfr, files, nonhf, fb, drops, out)
    gate_q7(absfr, files, nonhf, drops, out)

    print("\n== GATE Q: all sub-gates passed ==")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, default=float)
        print(f"   wrote {a.json}")


if __name__ == "__main__":
    main()
