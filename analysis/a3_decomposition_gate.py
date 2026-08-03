#!/usr/bin/env python3.11
"""GATE O -- is A3 a two-sided BALANCE error, or is the OD path quiet on its own?

Session 107.  No render: every number is a re-read of a report already on disk.  Imports
`a3_balance_gate` (GATE M) -- and through it `level_law_gate` (GATE K) and `matrix_grade` -- rather
than re-deriving the absolute reconstruction or the pair selection, so the tools cannot drift.

WHY THIS EXISTS
---------------
Session 106 measured a decomposition of GATE M's A3 excess and recorded it as
"MEASURED, NOT YET GATED, DO NOT QUOTE AS FACT".  This gate is that check.  Nothing here is a new
hypothesis; what is new is that each step now has to survive a known answer before it can be
quoted, and one of them does not survive in the form it was written.

The arithmetic is a regrouping, and that is the whole idea.  GATE M's excess is

    excess = (mc - mo) - (qc - qo)          [m = model, q = pedal(reference), c = clean, o = OD]

which reads as "the model's clean/OD ratio minus the reference's" -- a BALANCE, in which either
path could be at fault.  Regrouped,

    excess = (mc - qc) - (mo - qo)

it reads as "the clean path's absolute error minus the OD path's".  Same number; a completely
different question.  If the clean path's absolute error can be shown to be ~0, then A3 stops being
a balance nobody can attribute and becomes a one-sided statement: THE OD PATH IS QUIET, BY THE FULL
EXCESS.  That is a far sharper target for the timeboxed A3 attempt (CLAUDE.md item 5) than a
two-sided ratio, and it is worth exactly as much as the exoneration behind it -- hence this file.

⚠ THE EXONERATION IS NOT FREE, AND IT IS NOT ZERO.  Three things sit between "the clean tap has no
gain element by topology" and "the clean path's absolute error is 0", and all three are measured
here rather than assumed:
  (a) the render-vs-capture absolute scale itself (O3, the bypass anchor);
  (b) the MASTER pot's own law, which is DOWNSTREAM of BLEND and therefore common to both paths --
      it cancels in the excess but NOT in either path's absolute error (O5/O6);
  (c) the two capture routes to "pure clean" do not agree, and session 106 left that dangling as a
      one-line loose end.  O7 resolves it, and it turns out to set the error bar.

GATES (all computed, exits non-zero on failure)
-----------------------------------------------
O1  KNOWN ANSWER -- the regrouping must reproduce GATE M's excess ELEMENTWISE per band, at every
    stimulus.  This is an identity, so it must hold to machine precision; if it does not, the two
    tools disagree about membership and nothing below is readable.  Mutation control included,
    because an identity check passes for any band set.
O2  MEMBERSHIP, asserted rather than assumed (the s104 L2 lesson).  Pair count, `gain-n12` named
    and asserted FOUND before being excluded, MASTER asserted matched within every pair (if it
    were not, (b) would not cancel in the excess and GATE M itself would be contaminated), and the
    master ladder's one-capture-per-detent asserted.
O3  THE BYPASS ANCHOR.  Rules out a common render-vs-capture offset that would otherwise be free
    to absorb any of the terms below.  Must be small AND stimulus-invariant.
O4  KNOWN ANSWER -- the clean path is LINEAR, so its absolute error is forbidden to depend on
    stimulus level.  Recovered separately at four levels on every base-clean capture; the floor
    guard that excludes the muted MASTER-min row must be asserted to BIND (s106 N5).
O5  PROVENANCE, measured PER BAND and with its own known answer.  The master ladder's upper half
    is `gain-n12` and its lower half is not.  The clean path is linear, so the MODEL side of an
    n12 capture must be its twin shifted by EXACTLY the harness pad, at every band -- asserted.
    Whatever is left is the REFERENCE's, and it is not the flat 0.107 dB session 106 recorded.
O6  THE MASTER LAW, and the topology's own known answer.  MASTER is a post-EQ, attenuation-only
    divider (C36 corners at 0.72 Hz), so a law error is a PURE GAIN and must be flat in frequency.
    Measured SAME-SESSION it must be flat to a tight bar -- asserted.  Measured cross-session it
    is not, and the difference is exactly O5's residue, which is what makes O5 load-bearing rather
    than cosmetic.
O7  THE ROUTE CHECK -- session 106's loose end, resolved.  Two captures reach pure clean by
    different means (DIST disengaged vs BLEND at minimum).  The model MUST render them
    identically, because at BLEND 0 the clean coefficient is exactly 1 by GATE K2; that is
    asserted.  Whatever the REFERENCE does between the two routes is then a property of the
    reference, and it is part of the error bar on the exoneration.
O8  THE LEDGER, and the verdict.  Every term above, summed, must REPRODUCE the measured clean-side
    reading of the A3 pairs -- an internal known answer, asserted, so a mis-signed or
    double-counted term cannot pass.  The verdict is COMPUTED from the ratio of the
    clean-branch bound to the OD deficit, and the bound is taken CONSERVATIVELY.

WHAT THIS GATE DOES NOT CLAIM
-----------------------------
It does not propose a fix, and it does not touch A3's SIZE: MASTER is matched within every pair,
so it is common-mode and GATE M's 5.1-5.5 dB over 100-400 Hz is unchanged by anything here.  What
changes is the ATTRIBUTION -- which side of the mix the deficit is on.

It says nothing about the MASTER law itself beyond sizing it.  That is a post-EQ, attenuation-only
divider with nothing nonlinear downstream, filed to Phase 10 C by the session-106 priority
decision; a law error there is a volume-knob calibration error, not a tone error.  ⚠ Do not merge
it with the LEVEL law (GATE K/L), which sits BEFORE the mix and therefore sets tone.
"""
import argparse
import re
import json
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import matrix_grade as MG          # noqa: E402
import level_law_gate as K         # noqa: E402
import a3_balance_gate as M        # noqa: E402
import captures as CAP             # noqa: E402  -- the harness pad, READ not retyped
import master_anchor_gate as T     # noqa: E402  -- the ladder correction, IMPORTED not transcribed

SWEEPS = M.SWEEPS

# The two capture routes to a pure-clean output.  A: the DIST footswitch disengaged (which forces
# the crossfade fully clean regardless of the BLEND knob).  B: the BLEND knob itself at minimum.
# B is the route the A3 pairs use; A is the route the MASTER ladder and the makeup calibration use,
# so the two have to be reconciled before they can appear in one accounting.
ROUTE_A = "ref-clean.wav"
ROUTE_A_N12 = "ref-clean_gain-n12.wav"
ROUTE_B = "blend-0700_base-od.wav"
BYPASS = "bypass.wav"

# A3's own band, as recorded in reference-sources.md §1 and confirmed per band by GATE M.
A3_BAND = M.A3_BAND

# The bypass anchor is the whole plugin bypassed: it measures nothing but the render-vs-capture
# scale.  Anything above this and there IS a common offset, which would make every absolute
# statement below arguable.
ANCHOR_MAX_DB = 0.20

# The clean path contains no nonlinear element, so its absolute error must not move with stimulus.
# This is a property of the MEASUREMENT, not of the pedal, so it is tight.
LINEARITY_MAX_SPREAD_DB = 0.05

# MASTER is a post-EQ, attenuation-only divider into a unity buffer, with nothing nonlinear
# downstream and C36 cornering at 0.72 Hz (circuit.md).  A law error there is therefore a PURE
# GAIN, and must be flat in frequency.  This is a property of the TOPOLOGY, so the bar is tight --
# it is a known answer on the instrument, not a tolerance on the pedal.
MASTER_FLAT_MAX_DB = 0.001

# The ledger's terms must reconstruct the measurement they decompose.  This is arithmetic, so the
# bar is numerical, not physical.
LEDGER_TOL_DB = 1e-3

# Above this ratio of (clean-branch bound) / (OD-path deficit) the word "exonerated" is not
# defensible and the finding stays a two-sided balance.
EXONERATION_MAX_RATIO = 0.15

# The two duplicated MASTER detents (GATE T3) carry the SAME signal, so their pedal sides cancel
# in (model - pedal) and the difference must equal the MODEL's OWN taper step -- computable from
# the shipped PWL constants with no free parameter.
#
# ⚠ A "is it a pure gain?" span test does NOT work here and was tried first: O6 already asserts
# that ANY two MASTER detents differ by a pure gain (that is the topology), so a span check cannot
# tell a duplicated pair from an ordinary one.  Mutation-tested -- it passed against master-1200.
# The taper-step check below is the discriminating one, because only a duplicate makes the pedal
# term vanish.  Both bars are numerical: these are known answers, not tolerances on the pedal.
DUP_PURE_GAIN_MAX_SPAN_DB = 0.01
DUP_TAPER_STEP_MAX_DB = 0.05

# The MASTER taper exponent session 115 RETIRED.  Deliberately transcribed -- it no longer exists
# in FitParams.h, so it cannot be read from the header, and it is used for DIAGNOSIS ONLY (naming
# a pre-s115 report as such) and never to gate anything.
RETIRED_MASTER_TAPER_EXP = 1.998


# --------------------------------------------------------------------------------------------
# shared machinery
# --------------------------------------------------------------------------------------------
def band_sel(fb, lo, hi):
    return np.array([j for j, f in enumerate(fb) if lo <= f <= hi])


def err_curve(absfr, f, sweep):
    """-> per-band (model - pedal) in dB, NO gain match on either side."""
    m, q = absfr[(f, sweep)]
    return m - q


def err(absfr, f, sweep, sel):
    return float(np.mean(err_curve(absfr, f, sweep)[sel]))


def is_silent(caps, f, sweep):
    fr = caps[f]["fr"][sweep]
    return (max(fr["plugin_db"]) < MG.SILENT_DB) or (max(fr["pedal_db"]) < MG.SILENT_DB)


def shipped_master_taper():
    """The two-segment PWL MASTER taper constants, READ from src/dsp/FitParams.h.

    Read rather than transcribed: this gate's known answer is only a known answer if it uses the
    constants the plugin actually ships (`verify-the-CONSTANT-not-the-prose`, s35).  Session 115
    RETIRED `masterTaperExp`, so a stale power-law reader would silently find nothing -- hence the
    hard failure rather than a default.
    """
    src = open(K.FITPARAMS, encoding="utf-8").read()
    vals = {}
    for name in ("masterTaperBreak", "masterTaperFrac"):
        m = re.search(rf"\b{name}\s*=\s*([0-9.eE+-]+)\s*;", src)
        if not m:
            sys.exit(f"GATE O6b FAIL: {name} not found in {K.FITPARAMS}.  The shipped MASTER taper "
                     f"has changed shape; re-derive this known answer rather than adjusting it")
        vals[name] = float(m.group(1))
    return vals["masterTaperBreak"], vals["masterTaperFrac"]


def master_div(x, brk, frac):
    """MasterOut::setMaster's divRatio -- deliberately a re-derivation, not a call into the stage,
    so the check can still fail if the shipped curve moves."""
    return (frac * x / brk) if x <= brk else (frac + (1.0 - frac) * (x - brk) / (1.0 - brk))


def master_of(caps, f):
    return caps[f].get("settings", {}).get("master")


# ⚠⚠ SESSION 112 -- WHICH CAPTURE SUPPLIES MASTER NOON IS NOW A CHOICE, AND IT MOVES THIS GATE'S
# LEDGER, SO IT IS A NAMED CONSTANT RATHER THAN AN ACCIDENT OF WHICHEVER FILE A DICT KEPT.
# Until session 111 the noon detent had exactly one capture -- ROUTE_A (`ref-clean.wav`, full send)
# -- because no `master-1200` file existed.  Session 111's batch added `master-1200_gain-n12`, so
# noon now has TWO captures at two different sends and O2's duplicate check fired (correctly: that
# check is session 104's L2 lesson, a dict build silently keeping one of two detents).
#
# The two options are NOT equivalent and neither is obviously right:
#   PREFER_FULL_SEND_NOON = True   keeps ROUTE_A, i.e. EXACTLY the pre-s112 behaviour, so every
#                                  recorded O5/O6/O7/O8 number stays reproducible -- but the ladder
#                                  is then 8 `gain-n12` detents plus one full-send noon, i.e. still
#                                  provenance-split, which is the very thing O6 measures at 0.33 dB.
#   PREFER_FULL_SEND_NOON = False  uses `master-1200_gain-n12`, making the ladder same-provenance
#                                  for the first time -- but it CHANGES the ledger, so no pre-s112
#                                  A3 figure would be comparable without re-deriving it.
# ⛔ Left at True deliberately: this is a membership decision of the session-106/110/111 class, the
# user is re-capturing a clean 9-point ladder anyway, and it should be taken THEN, with the fresh
# ladder in hand, not silently here as a side effect of a re-render.
PREFER_FULL_SEND_NOON = True


def master_ladder(caps):
    """-> [(master_value, file, is_n12)] for the base-clean MASTER sweep, plus route A at noon.

    The ladder's own captures are named master-*; the noon detent was historically not among them
    because it is the matrix default, and ROUTE_A carries it.  Session 111 added a `master-1200`
    capture, so noon can now be served by either -- see PREFER_FULL_SEND_NOON above.  Every detent
    that a capture is DISCARDED at is printed by O2; nothing here is dropped silently (session 40)."""
    rows = [(master_of(caps, f), f, "gain-n12" in f)
            for f in caps if f.startswith("master-") and "base-clean" in f]
    if ROUTE_A in caps:
        rows.append((master_of(caps, ROUTE_A), ROUTE_A, "gain-n12" in ROUTE_A))
    rows.sort(key=lambda r: r[0])

    kept, dropped = [], []
    for mv in sorted({r[0] for r in rows}):
        at = [r for r in rows if r[0] == mv]
        if len(at) == 1:
            kept.append(at[0])
            continue
        full = [r for r in at if not r[2]]
        n12 = [r for r in at if r[2]]
        if len({r[2] for r in at}) == 1:
            # Same detent AND same send twice -- a genuine duplicate condition, not a choice.
            sys.exit(f"GATE O2 FAIL: {len(at)} captures at master={mv} with the SAME send "
                     f"({', '.join(sorted(r[1] for r in at))}) -- a dict build would silently keep "
                     f"one.  Resolve the membership before reading the ladder")
        pick = (full or n12)[0] if PREFER_FULL_SEND_NOON else (n12 or full)[0]
        kept.append(pick)
        dropped += [r for r in at if r[1] != pick[1]]
    return sorted(kept, key=lambda r: r[0]), dropped


# --------------------------------------------------------------------------------------------
# O1 -- known answer: the regrouping is an identity
# --------------------------------------------------------------------------------------------
def gate_o1(absfr, caps, nonhf, out):
    print("-- O1: known answer -- the regrouping must reproduce GATE M's excess elementwise --")
    cl, od = M.endpoints(caps, exclude_defect=True)
    pairs = M.pair_up(caps, cl, od)
    worst = 0.0
    for sw in SWEEPS:
        ref, _n = M.excess_curve(absfr, pairs, nonhf, sw)
        # the regrouping: mean over pairs of (clean absolute error) - (OD absolute error)
        mine = np.mean([err_curve(absfr, fc, sw)[nonhf] - err_curve(absfr, fo, sw)[nonhf]
                        for fc, fo, *_ in pairs], axis=0)
        worst = max(worst, float(np.max(np.abs(mine - ref))))
    if worst > 1e-12:
        sys.exit(f"GATE O1 FAIL: the regrouped split does not reproduce GATE M's excess "
                 f"(worst {worst:.3e} dB).  This is an algebraic identity, so a nonzero residual "
                 f"means the two tools are not selecting the same pairs or the same bands -- fix "
                 f"that before reading anything below")
    print(f"   {len(pairs)} pairs (gain-n12 excluded), {len(nonhf)} non-HF bands, "
          f"{len(SWEEPS)} stimulus levels")
    print(f"   worst elementwise |regrouped - GATE M| = {worst:.2e} dB")

    # An identity holds for ANY band set, so the check above certifies nothing on its own about
    # membership.  Perturbing ONE side must move the result, or O1 is vacuous.
    sw = SWEEPS[0]
    ref, _ = M.excess_curve(absfr, pairs, nonhf, sw)
    bad = np.mean([err_curve(absfr, fc, sw)[nonhf] - 0.5 * err_curve(absfr, fo, sw)[nonhf]
                   for fc, fo, *_ in pairs], axis=0)
    moved = float(np.max(np.abs(bad - ref)))
    if moved < 1e-3:
        sys.exit("GATE O1 FAIL: halving the OD side did not move the split -- the OD term is not "
                 "reaching the statistic, so the identity above is vacuous")
    print(f"   O1 OK   identity to {worst:.1e}; mutation (halve the OD term) moves it "
          f"{moved:.2f} dB, so the check is not vacuous")
    out["o1"] = {"worst": worst, "n_pairs": len(pairs), "mutation": moved}
    return pairs


# --------------------------------------------------------------------------------------------
# O2 -- membership, asserted
# --------------------------------------------------------------------------------------------
def gate_o2(caps, pairs, out):
    print("\n-- O2: membership, asserted rather than assumed --")
    all_pairs = M.pair_up(caps, *M.endpoints(caps, exclude_defect=False))
    defect = [p for p in all_pairs if M.DEFECT_TOKEN in p[1]]
    if not defect:
        sys.exit(f"GATE O2 FAIL: '{M.DEFECT_TOKEN}' matched no pair.  A substring filter that "
                 f"silently matches nothing is `empty-gate-must-fail` in a costume -- if the "
                 f"capture set has changed, re-derive the exclusion rather than assuming it")
    print(f"   {len(all_pairs)} settings-matched pairs; {len(defect)} carry {M.DEFECT_TOKEN} "
          f"(the session-48 capture defect) and are EXCLUDED -> {len(pairs)} used")

    # MASTER matched within every pair is what makes the master law common-mode.  If it were not,
    # GATE M's excess would carry a taper difference and A3's SIZE would be wrong, not just its
    # attribution.  Assert it rather than trusting PAIR_KEYS to still contain it.
    if "master" not in M.PAIR_KEYS:
        sys.exit("GATE O2 FAIL: GATE M no longer matches pairs on `master`, so the MASTER law is "
                 "not common-mode in the excess and this decomposition does not apply")
    bad = [(fc, fo) for fc, fo, *_ in pairs if master_of(caps, fc) != master_of(caps, fo)]
    if bad:
        sys.exit(f"GATE O2 FAIL: {len(bad)} pairs differ in MASTER, e.g. {bad[0]}")
    mvals = sorted({master_of(caps, fc) for fc, fo, *_ in pairs})
    print(f"   MASTER matched within every pair (asserted); pairs sit at master {mvals} "
          f"=> the master law is common-mode and cancels in the excess")

    lad, dropped = master_ladder(caps)
    seen = {}
    for mv, f, _n12 in lad:
        if mv in seen:
            sys.exit(f"GATE O2 FAIL: two captures at master={mv} ({seen[mv]}, {f}) -- a dict build "
                     f"would silently keep one.  Resolve before reading the ladder")
        seen[mv] = f
    # Never silent (session 40): if a detent had a second capture at the other send, say so, say
    # which one is in use, and say what the alternative would cost.
    for mv, f, is_n in dropped:
        used = seen[mv]
        print(f"   ⚠ master={mv} has TWO captures at different sends -- using {used}, "
              f"NOT {f}.  PREFER_FULL_SEND_NOON={PREFER_FULL_SEND_NOON} keeps every pre-s112 "
              f"A3 figure reproducible; flipping it makes the ladder same-provenance but "
              f"re-bases the ledger.  Decide it with the fresh MASTER ladder, not here.")
    print(f"   MASTER ladder: {len(lad)} detents, exactly one capture each "
          f"({min(seen)} .. {max(seen)})")
    n12 = [mv for mv, _f, is_n in lad if is_n]
    print(f"   ⚠ provenance splits INSIDE the ladder: master {n12} are {M.DEFECT_TOKEN}, the rest "
          f"are not -- O5 sizes that before the ladder is read")
    out["o2"] = {"n_pairs_all": len(all_pairs), "n_pairs_used": len(pairs),
                 "n_defect": len(defect), "master_of_pairs": mvals,
                 "ladder_detents": sorted(seen), "ladder_n12": n12}
    print(f"   O2 OK")
    return lad


# --------------------------------------------------------------------------------------------
# O3 -- the bypass anchor
# --------------------------------------------------------------------------------------------
def gate_o3(absfr, caps, nonhf, a3sel, out):
    print("\n-- O3: the bypass anchor -- is there a common render-vs-capture offset? --")
    if (BYPASS, SWEEPS[0]) not in absfr:
        sys.exit(f"GATE O3 FAIL: {BYPASS} absent.  Without it every absolute statement below is "
                 f"free to be a scale error instead of a path error")
    vals_n = [err(absfr, BYPASS, sw, nonhf) for sw in SWEEPS]
    vals_a = [err(absfr, BYPASS, sw, a3sel) for sw in SWEEPS]
    print(f"   {'stimulus':<12}{'non-HF':>10}{'100-400 Hz':>13}")
    for sw, vn, va in zip(SWEEPS, vals_n, vals_a):
        print(f"   {sw.replace('sweep_', ''):<12}{vn:>10.4f}{va:>13.4f}")
    spread = max(vals_n) - min(vals_n)
    worst = max(abs(v) for v in vals_n + vals_a)
    if worst > ANCHOR_MAX_DB:
        sys.exit(f"GATE O3 FAIL: bypass reads {worst:.3f} dB against a {ANCHOR_MAX_DB} dB bar -- "
                 f"there IS a common offset, and it is free to absorb any term in O7")
    if spread > 1e-6:
        sys.exit(f"GATE O3 FAIL: the bypass path is linear, so its error cannot depend on "
                 f"stimulus; spread {spread:.3e} dB says the reconstruction is not stimulus-clean")
    print(f"   O3 OK   worst {worst:.4f} dB (bar {ANCHOR_MAX_DB}), identical at all "
          f"{len(SWEEPS)} stimulus levels (spread {spread:.1e})")
    print( "           => the render-vs-capture absolute scale is sound; there is no common offset")
    print( "              available to absorb the terms below.")
    out["o3"] = {"nonhf": vals_n, "a3band": vals_a, "worst": worst, "spread": spread}


# --------------------------------------------------------------------------------------------
# O4 -- known answer: the clean path is linear
# --------------------------------------------------------------------------------------------
def gate_o4(absfr, caps, nonhf, out):
    print("\n-- O4: known answer -- the clean path is LINEAR, so its error cannot move with "
          "stimulus --")
    cleans = sorted(f for f in caps if "base-clean" in f or f == ROUTE_A)
    kept, dropped = [], []
    for f in cleans:
        if any(is_silent(caps, f, sw) for sw in SWEEPS):
            dropped.append(f)
            continue
        vals = [err(absfr, f, sw, nonhf) for sw in SWEEPS]
        kept.append((f, max(vals) - min(vals), vals[0]))
    if not dropped:
        sys.exit("GATE O4 FAIL: the floor guard excluded nothing.  The MASTER-min capture mutes in "
                 "the model (GATE L7) and reads ~-220 dB, so it MUST be caught here -- a guard "
                 "that never binds is not a guard (s106 N5)")
    if not kept:
        sys.exit("GATE O4 FAIL: no clean capture survived the floor guard -- an empty known answer "
                 "is not a known answer")
    worst_f, worst_s, _ = max(kept, key=lambda r: r[1])
    print(f"   {len(kept)} clean captures checked, {len(dropped)} excluded by the floor guard "
          f"(asserted to bind): {[f.split('_')[0] for f in dropped]}")
    print(f"   worst stimulus spread over the four sweeps: {worst_s:.2e} dB  ({worst_f})")
    if worst_s > LINEARITY_MAX_SPREAD_DB:
        sys.exit(f"GATE O4 FAIL: a clean capture's absolute error moves {worst_s:.3f} dB with "
                 f"stimulus, against a {LINEARITY_MAX_SPREAD_DB} dB bar.  Either the clean path is "
                 f"not linear or the absolute reconstruction is contaminated; both invalidate O7")
    print(f"   O4 OK   every clean capture is stimulus-invariant to {worst_s:.1e} dB")
    print( "           => this is a free known answer on the INSTRUMENT, not on the pedal: it")
    print( "              would break if the reconstruction, the band selection or the sweep")
    print( "              mapping were wrong, and it does not.")
    out["o4"] = {"n_kept": len(kept), "n_dropped": len(dropped), "dropped": dropped,
                 "worst_spread": worst_s, "worst_file": worst_f}


# --------------------------------------------------------------------------------------------
# O5 -- provenance, per band, with its own known answer
# --------------------------------------------------------------------------------------------
def gate_o5(absfr, caps, fb, nonhf, a3sel, out):
    print(f"\n-- O5: provenance -- what does the {M.DEFECT_TOKEN} capture session do to a CLEAN "
          f"capture? --")
    if ROUTE_A not in caps or ROUTE_A_N12 not in caps:
        sys.exit(f"GATE O5 FAIL: need both {ROUTE_A} and {ROUTE_A_N12} at identical settings to "
                 f"size the provenance offset; the master ladder spans the two sessions and "
                 f"cannot be read without it")
    sa, sb = caps[ROUTE_A]["settings"], caps[ROUTE_A_N12]["settings"]
    diff = {k for k in sa if k != "gainSessionDb" and sa[k] != sb.get(k)}
    if diff:
        sys.exit(f"GATE O5 FAIL: the provenance pair differs in {sorted(diff)} as well as the "
                 f"capture session, so their difference is not the provenance offset")

    # KNOWN ANSWER.  The clean path has no nonlinear element, so on the MODEL side an n12 capture
    # must be its twin shifted by EXACTLY the harness pad -- at every band, not on average.  This
    # exercises the whole chain: the pad plumbing, the render, the band mapping and the absolute
    # reconstruction.  If it holds, anything left over is the REFERENCE's, by elimination.
    mA = absfr[(ROUTE_A, SWEEPS[0])][0]
    mB = absfr[(ROUTE_A_N12, SWEEPS[0])][0]
    qA = absfr[(ROUTE_A, SWEEPS[0])][1]
    qB = absfr[(ROUTE_A_N12, SWEEPS[0])][1]
    dm, dq = (mB - mA)[nonhf], (qB - qA)[nonhf]
    pad = CAP.gain_correction_db(caps[ROUTE_A_N12]["settings"])
    span_m = float(dm.max() - dm.min())
    if span_m > 1e-6:
        sys.exit(f"GATE O5 FAIL: the MODEL's n12 clean capture is not a pure level shift of its "
                 f"twin (span {span_m:.3e} dB).  The clean path is linear, so this must be exact; "
                 f"a frequency-dependent model side means the pad is not being applied cleanly "
                 f"and the residue below cannot be attributed to the reference")
    if abs(float(dm.mean()) + pad) > 1e-6:
        sys.exit(f"GATE O5 FAIL: the model shift is {float(dm.mean()):+.4f} dB but the harness pad "
                 f"is {pad:.4f} dB -- the render and the bookkeeping disagree")
    print(f"   KNOWN ANSWER (model side, clean path is linear):")
    print(f"      MODEL  n12 - twin = {float(dm.mean()):+.4f} dB, span {span_m:.1e} -- EXACTLY the "
          f"harness pad ({-pad:+.4f}), at every band")
    print(f"      PEDAL  n12 - twin = {float(dq.mean()):+.4f} dB, span "
          f"{float(dq.max() - dq.min()):.4f}")
    print( "      => our side is exact, so the residue is the REFERENCE's: ND's clean path is not")
    print( "         perfectly level-invariant across a 12 dB input change.")

    prov = (mB - mA) - (qB - qA)      # the residue, per band, on the error (model - pedal)
    pn, pa = float(prov[nonhf].mean()), float(prov[a3sel].mean())
    lo = float(prov[band_sel(fb, 25.0, 100.0)].mean())
    hi = float(prov[band_sel(fb, 1000.0, 8000.0)].mean())
    span = float(prov[nonhf].max() - prov[nonhf].min())
    print(f"\n   the provenance residue, PER BAND (not the scalar session 106 recorded):")
    print(f"      non-HF mean {pn:+.3f}    100-400 Hz {pa:+.3f}")
    print(f"      below 100 Hz {lo:+.3f}  ->  1-8 kHz {hi:+.3f}   (span {span:.3f} dB)")
    if span < 3.0 * abs(pn):
        print( "      (flat enough that the scalar would have done)")
    else:
        print(f"   ⚠ session 106 recorded this as 'agree to 0.107 dB', which is the BROADBAND MEAN")
        print(f"     and understates the low end by {abs(lo / pn):.1f}x.  It is a TILT, not an")
        print( "     offset, so a scalar correction leaves most of it behind.  Corrected per band")
        print( "     from here on.")
    out["o5"] = {"pad": pad, "model_shift": float(dm.mean()), "model_span": span_m,
                 "pedal_shift": float(dq.mean()), "resid_nonhf": pn, "resid_a3": pa,
                 "resid_lf": lo, "resid_hf": hi, "resid_span": span}
    print(f"   O5 OK   model side exact to {span_m:.1e} dB; reference residue is a {span:.2f} dB "
          f"tilt, carried per band")
    return prov


# --------------------------------------------------------------------------------------------
# O6 -- the MASTER law, and the topology's own known answer
# --------------------------------------------------------------------------------------------
def gate_o6(absfr, caps, fb, nonhf, a3sel, prov, lad, out):
    print("\n-- O6: the MASTER law -- and the known answer the topology supplies for free --")
    live = [(mv, f, n12) for mv, f, n12 in lad
            if not any(is_silent(caps, f, sw) for sw in SWEEPS)]
    muted = [mv for mv, f, _ in lad if (mv, f, _) not in live]
    unity = max(mv for mv, _f, _n in live)
    if unity != 1.0:
        sys.exit(f"GATE O6 FAIL: the ladder's top live detent is master={unity}, not 1.0.  The "
                 f"accounting rests on a detent where the divider is unity by topology")
    u_file = [f for mv, f, _ in live if mv == unity][0]
    u_n12 = [n for mv, _f, n in live if mv == unity][0]
    if not u_n12:
        sys.exit("GATE O6 FAIL: the master-unity capture is no longer a gain-n12 file; the "
                 "same-session pairing below assumed it was.  Re-derive rather than adjust")

    # KNOWN ANSWER.  MASTER is a post-EQ, attenuation-only divider feeding a unity buffer, with
    # nothing nonlinear downstream and C36 cornering at 0.72 Hz (circuit.md).  So a law error is a
    # PURE GAIN and MUST be flat in frequency.  Measured between two captures from the SAME
    # session, that is exactly what it is -- which simultaneously validates the reconstruction,
    # the band mapping, and O5's attribution of the tilt to provenance.
    same = err_curve(absfr, ROUTE_A_N12, SWEEPS[0]) - err_curve(absfr, u_file, SWEEPS[0])
    cross = err_curve(absfr, ROUTE_A, SWEEPS[0]) - err_curve(absfr, u_file, SWEEPS[0])
    s_span = float(same[nonhf].max() - same[nonhf].min())
    c_span = float(cross[nonhf].max() - cross[nonhf].min())
    print(f"   MASTER noon -> unity, model - pedal, over {len(nonhf)} non-HF bands:")
    print(f"      SAME session  ({ROUTE_A_N12} vs {u_file.split('_')[0]}...)")
    print(f"         mean {float(same[nonhf].mean()):+.4f} dB, span {s_span:.4f}")
    print(f"      CROSS session ({ROUTE_A} vs the same n12 capture)")
    print(f"         mean {float(cross[nonhf].mean()):+.4f} dB, span {c_span:.4f}")
    if s_span > MASTER_FLAT_MAX_DB:
        sys.exit(f"GATE O6 FAIL: the same-session MASTER law spans {s_span:.4f} dB against a "
                 f"{MASTER_FLAT_MAX_DB} dB bar.  MASTER is an attenuation-only divider, so a law "
                 f"error is a pure gain and must be flat -- a tilt means either the topology note "
                 f"in circuit.md is wrong or this reconstruction is not measuring what it claims")
    if c_span < 5.0 * s_span:
        sys.exit("GATE O6 FAIL: the cross-session read is as flat as the same-session one, so O5's "
                 "residue is not what breaks the flatness and the two gates disagree")
    print(f"\n   => SAME-session it is FLAT to {s_span:.4f} dB -- the pure gain the topology")
    print( "      demands.  Cross-session it tilts, and the tilt IS O5's provenance residue")
    print(f"      ({c_span:.3f} dB against {s_span:.4f}), which is what makes O5 load-bearing.")
    print( "   ⭐ This is a free known answer on the whole instrument: it would break if the")
    print( "      absolute reconstruction, the band mapping or the provenance handling were wrong.")

    law_n = float(same[nonhf].mean())
    law_a = float(same[a3sel].mean())
    if muted:
        print(f"\n   ⚠ master {muted} MUTES in the model (GATE L7) and is below SILENT_DB, so the "
              f"matrix has never graded it; excluded here and not diagnosed.")
    out["o6"] = {"same_mean": law_n, "same_span": s_span, "cross_span": c_span,
                 "law_a3": law_a, "unity_file": u_file, "muted": muted}
    print(f"   O6 OK   MASTER law = {law_n:+.4f} dB (non-HF) / {law_a:+.4f} dB (100-400), a pure "
          f"gain, common-mode across the mix")
    return law_n, law_a, u_file


# --------------------------------------------------------------------------------------------
# O6b -- the ladder anchor (session 119).  SESSION 115 CORRECTED THE LADDER AND NOBODY RE-POINTED
#        THIS GATE AT IT, so O6/O8 were reading a capture GATE T proved is 4.447 dB low.
# --------------------------------------------------------------------------------------------
def gate_o6b(absfr, caps, nonhf, u_file, out):
    print("\n-- O6b: the master-unity ANCHOR -- is the capture the ledger rests on sound? --")

    det = [d for d in T.DUP_DETENTS if f"master-{d}_" in u_file]
    print(f"   the ledger's master-unity capture is {u_file}")

    if not det:
        # A future capture set may put a CLEAN file at unity.  Then the correction must be zero,
        # and saying so explicitly is what stops it being applied where it does not belong.
        print("   it is NOT one of GATE T's duplicated detents "
              f"({', '.join(T.DUP_DETENTS)}) => correction 0.000 dB, ledger read as measured")
        out["o6b"] = {"file": u_file, "corrected": False, "correction_db": 0.0}
        print("   O6b OK   no correction applies")
        return 0.0

    corr = T.detent_corrections()[det[0]]
    if not np.isfinite(corr) or corr <= 0.0:
        sys.exit(f"GATE O6b FAIL: GATE T returned a correction of {corr} dB for detent {det[0]}; "
                 f"a corrupted detent reads LOW, so the correction must be finite and positive")

    # KNOWN ANSWER, inside THIS gate's own data and sharing no arithmetic with GATE T's WAV-level
    # derivation.  T3 says the two top n12 files carry ONE signal.  If so their pedal sides cancel
    # in (model - pedal), and what is left is the MODEL's own MASTER taper step -- which the
    # shipped PWL constants predict with NO free parameter.  Only a duplicate makes the pedal term
    # vanish, so this discriminates; a span test does not (see the constant's comment).
    other = [f for f in caps
             if any(f"master-{d}_" in f for d in T.DUP_DETENTS) and f != u_file]
    if not other:
        sys.exit(f"GATE O6b FAIL: the report has no second duplicated detent to check {u_file} "
                 f"against, so the duplication cannot be confirmed in this gate's own domain")
    d = err_curve(absfr, other[0], SWEEPS[0]) - err_curve(absfr, u_file, SWEEPS[0])
    span = float(d[nonhf].max() - d[nonhf].min())
    meas = float(d[nonhf].mean())
    brk, frac = shipped_master_taper()
    pred = 20.0 * np.log10(master_div(master_of(caps, other[0]), brk, frac)
                           / master_div(master_of(caps, u_file), brk, frac))
    print(f"   known answer: {other[0].split('_')[0]} vs {u_file.split('_')[0]} (model-pedal)")
    print(f"      measured  {meas:+.4f} dB, span {span:.6f} dB")
    print(f"      predicted {pred:+.4f} dB  = the shipped PWL taper step (brk {brk}, frac {frac}),")
    print( "                  which is what remains IF AND ONLY IF the pedal sides cancel")
    if span > DUP_PURE_GAIN_MAX_SPAN_DB:
        sys.exit(f"GATE O6b FAIL: the two detents differ by {span:.4f} dB across frequency, not a "
                 f"pure gain (bar {DUP_PURE_GAIN_MAX_SPAN_DB}) -- MASTER is attenuation-only, so "
                 f"either this reconstruction or circuit.md's topology note is wrong")
    if abs(meas - pred) > DUP_TAPER_STEP_MAX_DB:
        # Before blaming the captures, check the likeliest cause: a report rendered BEFORE session
        # 115 replaced the power law.  This makes the gate a real baseline-EPOCH guard -- the thing
        # session 118 discovered the hard way, that "invisible to the matrix" is not "invisible".
        old = 20.0 * np.log10(master_of(caps, other[0]) ** RETIRED_MASTER_TAPER_EXP
                              / master_of(caps, u_file) ** RETIRED_MASTER_TAPER_EXP)
        if abs(meas - old) <= DUP_TAPER_STEP_MAX_DB:
            sys.exit(f"GATE O6b FAIL: measured {meas:+.4f} dB matches the RETIRED power-law taper "
                     f"(exp {RETIRED_MASTER_TAPER_EXP}, predicts {old:+.4f}), not the shipped PWL "
                     f"({pred:+.4f}).  ⇒ THIS REPORT PREDATES SESSION 115 and was rendered from a "
                     f"different src/.  Re-render before reading any ABSOLUTE ledger off it: the "
                     f"matrix's per-row gain match hides s115's constants, this gate does not")
        sys.exit(f"GATE O6b FAIL: measured {meas:+.4f} dB vs the shipped taper's {pred:+.4f} dB "
                 f"(bar {DUP_TAPER_STEP_MAX_DB}), and it does not match the retired power law "
                 f"either ({old:+.4f}).  Either these two captures are not the duplicate GATE T3 "
                 f"reports, or the shipped MASTER taper is not rendering as specified")
    print(f"      agree to {abs(meas - pred):.4f} dB  => the pedal sides DO cancel: the")
    print( "         duplication is confirmed here, independently of GATE T's WAV-level read.")
    print( "      ⭐ Free second result: this validates the session-115 PWL taper on the render,")
    print( "         through a path sharing nothing with s115's own acceptance check.")

    print(f"\n   CORRECTION (imported from GATE T, not transcribed): +{corr:.3f} dB on the PEDAL")
    print( "      provenance: the fresh gain-n18 capture of this detent, promoted through the")
    print( "      directly measured 6.000 dB n12->n18 pad (GATE T2, derived WITHOUT the")
    print( "      contaminated ref-clean.wav), against what the corrupted n12 file reads.")
    print( "   ⚠ Sessions 107-118 read this gate WITHOUT it.  Pre-s119 quotes of O6/O8 are on the")
    print( "      uncorrected anchor and are reproduced below as a labelled CONTROL.")
    out["o6b"] = {"file": u_file, "corrected": True, "correction_db": corr,
                  "dup_span_db": span, "dup_gain_db": float(d[nonhf].mean())}
    print(f"   O6b OK   anchor corrected by +{corr:.3f} dB")
    return corr


# --------------------------------------------------------------------------------------------
# O7 -- the route check (session 106's loose end)
# --------------------------------------------------------------------------------------------
def gate_o7(absfr, caps, fb, nonhf, a3sel, out):
    print("\n-- O7: the two routes to pure clean -- session 106's unexplained 0.28 dB --")
    for f in (ROUTE_A, ROUTE_B):
        if f not in caps:
            sys.exit(f"GATE O7 FAIL: {f} absent; without the route reconciliation the ledger in "
                     f"O8 would mix two routes silently")
    sa, sb = caps[ROUTE_A]["settings"], caps[ROUTE_B]["settings"]
    same = {k for k in sa if k not in ("blend", "distEngage") and sa[k] == sb.get(k)}
    print(f"   A = {ROUTE_A:<24} blend={sa['blend']}, distEngage={sa['distEngage']}")
    print(f"   B = {ROUTE_B:<24} blend={sb['blend']}, distEngage={sb['distEngage']}")
    print(f"   identical on {len(same)} other settings incl. master={sa['master']}")
    print( "   Both are pure clean: GATE K2 gives the clean coefficient exactly 1 at BLEND 0, and")
    print( "   disengaging DIST forces the crossfade fully clean.  So the MODEL must render them")
    print( "   identically -- a topological requirement, not an expectation.\n")

    dm = float(np.max([np.max(np.abs(absfr[(ROUTE_A, sw)][0] - absfr[(ROUTE_B, sw)][0]))
                       for sw in SWEEPS]))
    if dm > 1e-9:
        sys.exit(f"GATE O7 FAIL: the MODEL renders the two pure-clean routes differently "
                 f"(worst {dm:.3e} dB).  Either GATE K2's coefficient is wrong or the DIST "
                 f"override is not what circuit.md describes -- that is a finding in itself and "
                 f"it invalidates the premise this decomposition rests on")
    dq = absfr[(ROUTE_A, SWEEPS[0])][1] - absfr[(ROUTE_B, SWEEPS[0])][1]
    if abs(float(dq[nonhf].mean())) < 1e-6:
        sys.exit("GATE O7 FAIL: the two routes agree on the REFERENCE side too, so the model check "
                 "above compared two effectively identical rows and is vacuous")
    gap_n, gap_a = -float(dq[nonhf].mean()), -float(dq[a3sel].mean())
    lo = -float(dq[band_sel(fb, 25.0, 100.0)].mean())
    hi = -float(dq[band_sel(fb, 1000.0, 8000.0)].mean())
    print(f"   MODEL  A - B : {dm:.2e} dB  -- BIT-IDENTICAL, as the topology requires")
    print(f"   PEDAL  A - B : {float(dq[nonhf].mean()):+.3f} dB non-HF, "
          f"{float(dq[a3sel].mean()):+.3f} dB over 100-400 Hz")
    print( "\n   => the whole disagreement is on the REFERENCE side.  In the reference, engaging")
    print( "      DIST at BLEND minimum is NOT transparent; in our model it is exactly so.")
    # One convention only.  Stating this as a signed "gap" invites a later quote with the sign
    # flipped, so it is written as what the reference actually does.
    print(f"      In the REFERENCE, route B (BLEND min) reads LOWER than route A (DIST off) by")
    print(f"      {abs(lo):.3f} dB below 100 Hz, rising to {abs(hi):.3f} dB over 1-8 kHz -- a")
    print( "      frequency-STRUCTURED loss, not an offset.")
    print( "   ⛔ NOT diagnosed here and NOT folded into A3: it is a reference-side property of a")
    print( "      control the matrix grades at one position.  What it IS, is part of the error bar")
    print( "      -- the A3 pairs use route B while the ladder and the makeup calibration use A.")
    out["o7"] = {"model_delta": dm, "gap_nonhf": gap_n, "gap_a3": gap_a, "lf": lo, "hf": hi}
    print(f"   O7 OK   model identical to {dm:.1e}; the routes differ by {abs(gap_a):.3f} dB over "
          f"100-400 Hz on the reference side")
    return gap_n, gap_a


# --------------------------------------------------------------------------------------------
# O8 -- the ledger, and the verdict
# --------------------------------------------------------------------------------------------
def gate_o8(absfr, caps, pairs, fb, nonhf, a3sel, prov, law, gap, u_file, corr, out):
    print("\n-- O8: the ledger -- what is left of the clean path's absolute error? --")
    if corr:
        print(f"   anchor corrected by +{corr:.3f} dB on the pedal side (O6b).  The correction")
        print( "   enters the MASTER law with +C and the residual with -C, so it CANCELS in the")
        print( "   sum -- the reconstruction check below is therefore blind to it, and is a real")
        print( "   guard that it has been threaded through BOTH places rather than one.")
    law_n, law_a = law
    gap_n, gap_a = gap
    res = {}
    for label, sel, lw, gp in (("100-400 Hz", a3sel, law_a, gap_a),
                               ("broadband non-HF", nonhf, law_n, gap_n)):
        measured = err(absfr, ROUTE_B, SWEEPS[0], sel)     # the clean side of every A3 pair
        pv = float(prov[sel].mean())
        raw_resid = err(absfr, u_file, SWEEPS[0], sel) - pv  # unity detent, onto the non-n12 basis
        # The corrupted detent reads LOW, so the true pedal level is higher and the model's error
        # against it is smaller by exactly the correction.  The MASTER law is a difference in which
        # this capture is the SUBTRAHEND, so it moves the other way.
        residual = raw_resid - corr
        lw = lw + corr
        terms = [("MASTER law (common-mode: cancels in A3's excess)", lw),
                 ("DIST-engage transparency gap, route B vs A (O7)", -gp),
                 ("clean SIGNAL-PATH residual (at master unity)", residual)]
        print(f"\n   [{label}]   contributions to the clean side's absolute error, dB")
        for name, v in terms:
            print(f"      {name:<52}{v:>9.3f}")
        total = sum(v for _n, v in terms)
        print(f"      {'-' * 52}{'':>9}")
        print(f"      {'= sum':<52}{total:>9.3f}")
        print(f"      {'measured, route B at master noon':<52}{measured:>9.3f}")
        # INTERNAL KNOWN ANSWER: the terms must reconstruct the measurement.  A mis-signed or
        # double-counted term cannot survive this, which is the whole reason it is here.
        if abs(total - measured) > LEDGER_TOL_DB:
            sys.exit(f"GATE O8 FAIL [{label}]: the ledger sums to {total:.4f} dB but the measured "
                     f"clean side is {measured:.4f} -- a term is mis-signed or double-counted")
        print(f"      reconstruction error {abs(total - measured):.2e} dB  (bar {LEDGER_TOL_DB})")

        deficit = [float(np.mean([err_curve(absfr, fc, sw)[sel] - err_curve(absfr, fo, sw)[sel]
                                  for fc, fo, *_ in pairs]).mean()) for sw in SWEEPS]
        print(f"      => OD PATH DEFICIT (the full excess): "
              + " / ".join(f"{-d:.2f}" for d in deficit) + " dB across stimulus")
        res[label] = {"measured": measured, "master_law": lw, "route_gap": -gp,
                      "residual": residual, "raw_residual": raw_resid, "correction": corr,
                      "provenance": pv, "deficit": deficit}

    # The verdict, computed, and the bound taken CONSERVATIVELY: the residual itself is small, but
    # it was obtained by subtracting a provenance correction of comparable size and it sits on the
    # other capture route, so neither of those can be claimed to better than its own magnitude.
    a = res["100-400 Hz"]
    bound = abs(a["residual"]) + abs(a["route_gap"]) + abs(a["provenance"])
    deficit = float(np.mean([abs(d) for d in a["deficit"]]))
    ratio = bound / deficit

    if corr:
        # CONTROL: the pre-s119 reading, on the uncorrupted-anchor-unaware ledger.  Printed so
        # every session-107..118 quote of this gate stays reproducible on demand, and so the size
        # of the repair is visible rather than asserted.
        c_bound = abs(a["raw_residual"]) + abs(a["route_gap"]) + abs(a["provenance"])
        print(f"\n   CONTROL (pre-s119, anchor UNcorrected -- what sessions 107-118 read):")
        print(f"      clean signal-path residual {abs(a['raw_residual']):.3f} dB "
              f"=> bound {c_bound:.3f}, ratio {c_bound / deficit:.3f}"
              f"  [{'over' if c_bound / deficit > EXONERATION_MAX_RATIO else 'within'} bar]")

    print(f"\n   VERDICT (computed, 100-400 Hz, conservative bound):")
    print(f"      clean signal-path residual        {abs(a['residual']):.3f} dB")
    print(f"      + route gap, B vs A (O7)          {abs(a['route_gap']):.3f} dB")
    print(f"      + provenance transfer (O5)        {abs(a['provenance']):.3f} dB")
    print(f"      = clean-branch bound              {bound:.3f} dB")
    print(f"        OD-path deficit                 {deficit:.3f} dB")
    print(f"        ratio {ratio:.3f}   against a bar of {EXONERATION_MAX_RATIO}")
    if ratio > EXONERATION_MAX_RATIO:
        out["o8"] = {"verdict": "NOT exonerated", "ratio": ratio, "bound": bound,
                     "deficit": deficit, "detail": res}
        print(f"\n   ⛔ NOT EXONERATED: the clean side could account for {ratio * 100:.0f}% of the "
              f"excess, so A3 remains a TWO-SIDED balance and the timeboxed attempt must not aim "
              f"a one-sided correction at the OD path.")
        sys.exit("GATE O8 FAIL: exoneration ratio over bar")
    print(f"\n   ✅ EXONERATED: the clean branch carries at most {bound:.2f} dB of a "
          f"{deficit:.2f} dB excess ({ratio * 100:.0f}%).")
    print( "      => A3 IS NOT A TWO-SIDED BALANCE ERROR.  THE OD PATH IS QUIET, ABSOLUTELY, BY")
    print(f"         {min(abs(d) for d in a['deficit']):.1f}-{max(abs(d) for d in a['deficit']):.1f}"
           " dB OVER 100-400 Hz, and the clean side is not a candidate cause.")
    print( "      ⚠ Quote the bound, not the residual.  Session 106 recorded this exoneration as")
    print(f"        '0.007 dB', which is the master-unity reading alone; honestly it is "
          f"{bound:.2f} dB,")
    print( "        because that reading sits on a different capture route AND a different capture")
    print(f"        session from the A3 pairs, and O7/O5 size both.  The deficit is still "
          f"{deficit / bound:.0f}x the")
    print( "        bound, so nothing about the conclusion changes -- only what may be quoted.")
    print( "      ⚠ A3's SIZE is untouched: MASTER is matched within every pair (O2), so it is")
    print( "        common-mode.  What changed is the ATTRIBUTION, not the number.")
    if corr:
        print( "      ⛔ DO NOT read the residual as independent evidence that the clean path is")
        print( "         transparent.  kOutputMakeup is a SINGLE-POINT calibration anchored on this")
        print( "         very detent, so the residual is near zero BY CONSTRUCTION on any baseline")
        print( "         -- pre-s115 it was ~0 against the corrupted capture with the model 4.43 dB")
        print( "         quiet, which is the circularity GATE T5 identified.  What it IS worth: a")
        print( "         cross-check that s115's RENDER-based makeup re-derivation and GATE T's")
        print( "         CAPTURE-side ladder algebra agree, and they do, to "
              f"{abs(a['residual']):.3f} dB.")
        print( "      ⭐ And a common-mode calibration error is invisible here yet HARMLESS to A3:")
        print( "         kOutputMakeup is a post-chain scalar, so it moves both branches equally")
        print( "         and cancels in the excess (s115 proved it a per-row pure gain).")
    out["o8"] = {"verdict": "exonerated", "ratio": ratio, "bound": bound, "deficit": deficit,
                 "detail": res}


# --------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    bands, caps = MG.load(a.report)
    idx = [i for i, b in enumerate(bands) if MG.GRADE_LO <= b <= MG.GRADE_HI]
    absfr, _silent = K.absolute_fr(caps, idx)
    fb = np.array([bands[i] for i in idx])
    nonhf = np.array([j for j, f in enumerate(fb) if f < K.HF_HZ])
    a3sel = band_sel(fb, *A3_BAND)

    print(f"GATE O -- is A3 the OD path alone, or a two-sided balance?   [{a.report}]")
    print(f"  {len(caps)} captures, {len(idx)} graded bands, {len(nonhf)} non-HF "
          f"(< {K.HF_HZ:.0f} Hz, excluded per GATE I), {len(a3sel)} in A3's own band")
    print( "  No render, no gain match, no fit.  Imports GATE M and GATE K so nothing can drift.\n")

    out = {"report": a.report, "n_captures": len(caps)}
    pairs = gate_o1(absfr, caps, nonhf, out)
    lad = gate_o2(caps, pairs, out)
    gate_o3(absfr, caps, nonhf, a3sel, out)
    gate_o4(absfr, caps, nonhf, out)
    prov = gate_o5(absfr, caps, fb, nonhf, a3sel, out)
    law_n, law_a, u_file = gate_o6(absfr, caps, fb, nonhf, a3sel, prov, lad, out)
    corr = gate_o6b(absfr, caps, nonhf, u_file, out)
    gap = gate_o7(absfr, caps, fb, nonhf, a3sel, out)
    gate_o8(absfr, caps, pairs, fb, nonhf, a3sel, prov, (law_n, law_a), gap, u_file, corr, out)

    print("\n== GATE O: all sub-gates passed ==")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, default=float)
        print(f"   wrote {a.json}")


if __name__ == "__main__":
    main()
