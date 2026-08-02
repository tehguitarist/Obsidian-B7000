#!/usr/bin/env python3.11
"""GATE I — what the OD 8-16.3 kHz error IS, settled by measurement rather than assertion.

Session 101. Sessions 89/90 left this as the one open measurement-side question in Phase 9:

    "Session 89's step (b) is now the whole question: is the residual ND's artefact or our
     Sallen-Keys? Do not spend another session on the FR instrument."
    "DO NOT dismiss this as 'ND aliasing' -- that is not established and it is not a reason to
     skip the band." (the user, session 89)

It matters because the region is not a corner case: 16255 Hz and 12901.6 Hz together own **38 % of
the OD band-RMS**, and the region carries two of the eight gate rows still over SHIP.

WHAT THIS TOOL SETTLES, and how each branch dies
------------------------------------------------
G1  CLEAN CONTROL / probe-alive.  On the clean path (BLEND 0, OD out of circuit) the model must
    already agree with the pedal at HF, at EVERY stimulus level. If it does not, the whole question
    is moot -- our HF linear response is simply wrong and there is nothing subtle to explain. This
    runs FIRST and refuses, because every later verdict is conditioned on it.

G2  THE ROLLOFF *RATE*, over the 8127.5 -> 16255 Hz octave, pedal vs model, per drive condition.
    This is the headline, and the choice of statistic is the point: a RATE is immune to the
    report's per-row gain match, to the choice of anchor band, and to how hard the clipper is
    working. The load-bearing property is that **no chain of fixed lowpass elements can GAIN with
    frequency**, whatever its HF switches are set to. Measured, at the hottest stimulus every one
    of the 15 pedal conditions gains and every one of ours rolls off -- a complete separation with
    no threshold in it -- and the gap GROWS monotonically with drive, which a fixed filter
    difference cannot do and a drive-generated artefact must.

    ⚠⚠ SESSION 114 REWROTE G2 AND ITS MEMBERSHIP. The original asked whether the MODEL holds one
    rate at the drawn Sallen-Key value (-18.25 dB/oct). That premise is wrong: the OD path also
    contains the treble/ATTACK ladder, C7, C10, C14 and the recovery bridged-T, and ATTACK is
    literally an HF control (C8 220 pF), so the path's rate spans ~19 dB/oct across the pedal's own
    switches. That guard -- not the model -- is why GATE I read FAIL from session 109 to 113.
    Rebuilt, the gate passes on EVERY report from s91 to s113, so session 111's recorded
    "session 109's kInputRef broke GATE I" does not survive. See classify() for the three
    membership defects fixed at the same time.

G3  THE FOLD-LOCUS TEST.  Session 90's h1_fr_gate KA-5 identified the one aliasing mechanism that
    defeats a Farina H1 read: the N-th harmonic's alias lands back ON the fundamental at exactly
        f = fs / (N + 1)   ->   16000 (H2), 12000 (H3), 9600 (H4), 8000 (H5) Hz
    coincident in BOTH time and frequency, so no gating can reject it. Those frequencies come from
    fs alone -- no free parameter, no relationship to any circuit corner -- so LOCALISED features on
    them would be dispositive FOR that mechanism, and a smooth curve through them dispositive
    AGAINST. Read at the deconvolution's own resolution, pedal only, no render.

G4  THE POOL-RESTRICTION CONSEQUENCE.  If the region is contaminated, the question "should the gate
    still grade it?" follows immediately -- so the cost is computed here rather than guessed, on the
    CANDIDATE **and** on the baseline, with the currently-PASSING rows re-checked too. Session 91:
    excluding a region can make a gate HARDER, because the excluded bands may have been diluting a
    percentile downward. That is exactly what happens here, and it would be invisible if only the
    failing rows were recomputed.

WHAT IT DOES NOT CLAIM
----------------------
"Contaminated" is not "entirely artefact". G2 prints the LOW-drive column precisely so the residual
linear disagreement stays visible, and G4 breaks the region into top-1 / top-2 / top-4 options
because the 8127.5 Hz band's error is drive-INDEPENDENT -- a different, real, and probably fixable
defect that a blanket exclusion would excuse. Read the per-option table, not the headline.

Run:
    python3.11 analysis/hf_artefact_gate.py analysis/reports/s99_attack_cand.json
    python3.11 analysis/hf_artefact_gate.py CAND.json --baseline analysis/reports/s91_shipped.json
    python3.11 analysis/hf_artefact_gate.py CAND.json --skip-fine      # G3 needs the capture wavs
"""
import argparse
import collections
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A                                    # noqa: E402
import release_gate as RG                              # noqa: E402

FS = 48000.0
CAPDIR = "analysis/captures"

# The octave G2 measures over. The two bands are exactly 2:1 (asserted below, not assumed).
OCT_LO, OCT_HI = 8127.5, 16255.0
# RATE_TOL (session 101) is RETIRED -- see G2a. It required the whole OD path to hold the rate of
# two of its elements, which nothing requires, and it is why GATE I failed from s109 to s113.

# The two POST-clipper Sallen-Key LPFs, unity gain, schematic-verified values (circuit.md
# "Recovery + bandlimiting"). IC4_B ~10.7 kHz, IC4_A ~3.3 kHz.
#   H(s) = 1 / (1 + s*Cgnd*(R1+R2) + s^2*R1*R2*Cfb*Cgnd)
SK_STAGES = (
    dict(name="IC4_B", R1=10e3, R2=22e3, Cfb=1.0e-9, Cgnd=1.0e-9),
    dict(name="IC4_A", R1=22e3, R2=47e3, Cfb=2.2e-9, Cgnd=1.0e-9),
)


def sk_mag_db(f):
    """|H| of the post-clipper SK pair, dB."""
    s = 2j * np.pi * f
    h = 1.0 + 0j
    for d in SK_STAGES:
        h *= 1.0 / (1 + s * d["Cgnd"] * (d["R1"] + d["R2"])
                    + s * s * d["R1"] * d["R2"] * d["Cfb"] * d["Cgnd"])
    return 20 * np.log10(abs(h))


def drawn_rate():
    """The drawn network's OWN rate over G2's octave, DERIVED from the schematic values.

    ⚠ This replaces an asserted -24 dB/oct, which was wrong and would have failed a correct model.
    -24 is the ASYMPTOTIC 4th-order slope; at 8127.5 Hz the pair is not yet fully past the 10.7 kHz
    corner, so the rate measured across this particular octave is **-18.25 dB/oct**. Asserting the
    textbook asymptote instead of computing the actual network cost G2a a false FAIL on its first
    run (`rebuild-targets-dont-transcribe`, applied to a number that looked too obvious to check)."""
    return sk_mag_db(OCT_HI) - sk_mag_db(OCT_LO)

# G1's bars. The clean path has no OD stage at all, so agreement here is a statement about our
# linear HF response only -- and it must not depend on stimulus level (nothing nonlinear is engaged).
G1_LEVEL_TOL = 1.5              # dB, |model - pedal| at 16255 re the mid anchor
G1_INVARIANCE_TOL = 0.5         # dB, spread of that difference across stimulus levels

MID_ANCHOR = (900.0, 1100.0)    # flat, far from the 320 Hz notch and from the HF region
PLATEAU = (13500.0, 19500.0)

SWEEPS = ("sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6")


def ok(flag):
    return "OK" if flag else "**FAIL**"


# ---------------------------------------------------------------- report-side helpers

def band_octave(path):
    """-> (bands, lo_i, hi_i, rows) with the octave indices asserted, not assumed."""
    d = json.load(open(path))
    bands = np.array(d["meta"]["bands"])
    lo = int(np.argmin(np.abs(bands - OCT_LO)))
    hi = int(np.argmin(np.abs(bands - OCT_HI)))
    ratio = bands[hi] / bands[lo]
    if abs(ratio - 2.0) > 0.02:
        sys.exit(f"hf_artefact_gate: {bands[lo]:.1f} -> {bands[hi]:.1f} Hz is {ratio:.3f}x, not an "
                 f"octave -- G2's dB/octave scaling would be wrong")
    return d, bands, lo, hi


EQ_POTS = ("lo", "loMid", "hiMid", "hi")

# The OD classes, keyed off the DRIVE setting itself rather than a filename token.
CLASSES = ("CLEAN path (DIST off, EQ flat)", "OD, bleed-free, DRIVE min",
           "OD, bleed-free, DRIVE noon", "OD, bleed-free, DRIVE max")


def classify(c):
    """The row classes G1/G2 need, resolved from SETTINGS, never from a filename substring.

    ⚠⚠ SESSION 114 REWROTE THIS, AND THE OLD VERSION IS WHY GATE I HAD BEEN FAILING SINCE
    SESSION 109. It read `"level-1700" in fname` and called the result "LEVEL max, where the
    clean bleed is exactly ZERO by topology". Three separate defects, each one arriving with a
    capture batch written AFTER the gate:

      (1) **GATE K2 (session 103) refuted the premise.** The bleed vanishes only where BOTH
          BLEND and LEVEL are at max -- the BLEND pot's body bridges the LEVEL wiper to the
          clean source at every intermediate BLEND. Session 112's `level-1700_blend-0930/1200/
          1430` captures therefore joined the "bleed-free OD" classes carrying 25-75 % CLEAN
          signal, and duly read a rate of ~0 dB/oct: they ARE the clean path.
      (2) **`gain-n12` twins were pooled with full-send captures** in the same rate cell --
          a second operating point 12 dB down the compression curve (session 108's P4).
      (3) **`master-1100_grunt-boost` is a MODEL-SIDE DUPLICATE** of `grunt-boost`. MASTER is a
          post-EQ pure gain and a RATE is a contrast, so a gain cancels exactly: measured, the
          two agree to 1.2e-07 dB/oct. Pooling them double-weighted one condition -- exactly the
          trap session 110 (GATE R7) found and fixed in GATE R, never propagated here.

    Membership is asserted downstream, so a future capture batch cannot silently re-contaminate
    these classes the way s110/s112/s113's did."""
    s = c.get("settings", {})
    if s.get("distEngage") is False:
        # ⚠ this is DIST-OFF, NOT "BLEND 0" as the old label claimed. GATE O7 measured that the
        # two are not the same thing in ND (0.11-0.46 dB apart). EQ must be flat or the class is
        # a median over the EQ sweep, which is what it had silently become (36 of 44 rows).
        #
        # ⭐ gain-session captures ARE admitted HERE and nowhere else, and the asymmetry is
        # physical rather than pragmatic: this path is LINEAR (GATE O5 measured our side of a
        # send change as a pure 12.0710 dB shift to 1.8e-08), and G1's statistic is a CONTRAST
        # (16255 Hz re a mid anchor), so a send change cancels exactly. There is no "operating
        # point" on a path with no nonlinearity in it. Excluding them would leave n=1.
        if all(abs(s.get(k, 0.5) - 0.5) < 1e-9 for k in EQ_POTS):
            return CLASSES[0]
        return None
    if s.get("gainSessionDb"):                  # (2) a different operating point -- never pooled
        return None
    if s.get("blend") != 1.0 or s.get("level") != 1.0:    # (1) bleed-free BY GATE K2, not by name
        return None
    drv = s.get("drive")
    if drv == 0.0:
        return CLASSES[1]
    if drv == 1.0:
        return CLASSES[3]
    return CLASSES[2]


def condition_key(c):
    """Every setting EXCEPT master. MASTER is a post-EQ, attenuation-only divider into a unity
    buffer (circuit.md), i.e. a PURE GAIN -- and both statistics here are contrasts (a rate is a
    difference of two dB values; the G1 level is referred to a mid anchor), so master cancels
    exactly. Two captures sharing this key are ONE condition and must vote once."""
    return tuple(sorted((k, v) for k, v in c.get("settings", {}).items() if k != "master"))


DUP_TOL = 0.01          # dB/oct -- MASTER is a pure gain, so duplicates must agree to ~0


def collect(d, bands, lo, hi):
    """-> ({class: {sweep: (pedal_rates, model_rates, pedal_lvl, model_lvl, files)}}, dropped).

    MASTER-only duplicates are collapsed to ONE vote per condition (session 110 R7). Two traps,
    both paid for in session 114:

      * **Do NOT pick the representative alphabetically.** The first draft did, and in the
        MASTER-ladder group that selects `master-0700_gain-n12`, where the MODEL MUTES (max
        plugin -640 dB -- GATE L7's LEVEL/MASTER-min finding on the second [ENG] divider). The
        silent-row guard then dropped all four sweeps and the entire condition vanished from G1,
        leaving n=1 and no sign that anything had been lost. Which capture represents a condition
        is a real choice (s112's `PREFER_FULL_SEND_NOON`), so it is made on USABLE DATA.
      * **Assert the duplicates agree instead of discarding them.** They must: MASTER is a
        post-EQ pure gain and both statistics here are contrasts. That turns the dedup from an
        arbitrary pick into a free known answer -- and it is the 4th independent confirmation of
        circuit.md's pure-gain claim (after GATE O6, s110 R7 and s114's G0)."""
    mid = int(np.argmin(np.abs(bands - 1015.9)))
    acc = collections.defaultdict(
        lambda: collections.defaultdict(lambda: ([], [], [], [], [])))
    by_cond, dropped = {}, []
    for c in d["captures"]:
        if classify(c) is None:
            continue
        by_cond.setdefault(condition_key(c), []).append(c)

    for key in sorted(by_cond, key=lambda kk: min(c["file"] for c in by_cond[kk])):
        cs = sorted(by_cond[key], key=lambda c: c["file"])
        k = classify(cs[0])
        for sw in SWEEPS:
            vals = []
            for c in cs:
                fr = c["fr"].get(sw)
                if not fr:
                    continue
                p, q = np.array(fr["plugin_db"]), np.array(fr["pedal_db"])
                if max(p) < -300 or max(q) < -300:      # silent row, same guard as matrix_grade
                    continue                            # e.g. the model mutes at MASTER/LEVEL min
                vals.append((c["file"], q[hi] - q[lo], p[hi] - p[lo],
                             q[hi] - q[mid], p[hi] - p[mid]))
            if not vals:
                continue
            if len(vals) > 1:
                worst = max(abs(v[2] - vals[0][2]) for v in vals)
                if worst > DUP_TOL:
                    sys.exit(f"hf_artefact_gate: MASTER-only duplicates DISAGREE by {worst:.4f} "
                             f"dB/oct at {sw} ({[v[0] for v in vals]}) -- MASTER is asserted to be "
                             f"a pure gain, and a rate is a contrast, so this cannot happen. Either "
                             f"condition_key() is missing a setting or circuit.md is wrong.")
                for v in vals[1:]:
                    dropped.append((v[0], vals[0][0], sw, worst))
            f, pr, mr, pl, ml = vals[0]
            cell = acc[k][sw]
            for i, x in enumerate((pr, mr, pl, ml, f)):
                cell[i].append(x)
    return acc, dropped


# ---------------------------------------------------------------- G1

def gate_membership(acc, dropped):
    """G0 -- ASSERTED membership. Session 114: three capture batches silently re-populated G1/G2's
    classes (see classify()'s note), and every one of them was invisible because the classes were
    resolved by filename substring. Nothing below is readable if this is wrong, so it runs first
    and it EXITS rather than warning."""
    print("=== G0  MEMBERSHIP — asserted, not inferred (session 114) ===")
    for k in CLASSES:
        n = len(acc[k][SWEEPS[0]][4]) if k in acc else 0
        print(f"  {k:<34} n = {n}")
    if dropped:
        names = sorted({(e, k) for e, k, _, _ in dropped})
        worst = max(w for _, _, _, w in dropped)
        print(f"\n  MASTER-only duplicates collapsed to one vote per condition (session 110 R7):")
        for e, k in names:
            print(f"    {e}  ->  {k}")
        print(f"  ⭐ and they AGREE to {worst:.2e} dB/oct (bar {DUP_TOL}) — MASTER is a pure gain and")
        print(f"     a rate is a contrast, so this is a free known answer, not a discard.")

    od = [k for k in CLASSES if k.startswith("OD")]
    if not all(k in acc and acc[k][SWEEPS[0]][4] for k in od):
        sys.exit("hf_artefact_gate: an OD class is EMPTY -- G2 cannot run (`empty-gate-must-fail`)")
    if CLASSES[0] not in acc or not acc[CLASSES[0]][SWEEPS[0]][4]:
        sys.exit("hf_artefact_gate: no DIST-off EQ-flat rows -- G1 cannot run, and no later "
                 "verdict is readable without it")
    # every OD row must actually be bleed-free and full-send, by GATE K2's criterion
    bad = [f for k in od for sw in SWEEPS for f in acc[k][sw][4]
           if "gain-n12" in f or "gain-n18" in f or "blend-" in f]
    if bad:
        sys.exit(f"hf_artefact_gate: these are NOT bleed-free full-send OD rows: {sorted(set(bad))}")
    print(f"\n  every OD row is BLEND max AND LEVEL max (bleed-free by GATE K2) at full send ... OK")
    return True


def gate_clean_control(acc):
    print("\n=== G1  CLEAN CONTROL — is our HF linear response already right? (probe-alive) ===")
    k = CLASSES[0]
    diffs, rates = [], []
    print(f"  {'stimulus':<12}{'n':>4}{'pedal dB':>10}{'model dB':>10}{'diff':>8}"
          f"{'pedal d/oct':>13}{'model d/oct':>13}")
    for sw in SWEEPS:
        pr, mr, pl, ml, _ = acc[k][sw]
        if not pl:
            continue
        dp, dm = float(np.median(pl)), float(np.median(ml))
        diffs.append(dm - dp)
        rates.append((float(np.median(pr)), float(np.median(mr))))
        print(f"  {sw.replace('sweep_',''):<12}{len(pl):>4}{dp:>10.2f}{dm:>10.2f}{dm-dp:>8.2f}"
              f"{np.median(pr):>13.2f}{np.median(mr):>13.2f}")
    worst = max(abs(x) for x in diffs)
    spread = max(diffs) - min(diffs)
    a = worst <= G1_LEVEL_TOL
    b = spread <= G1_INVARIANCE_TOL
    print(f"\n  G1a  |model - pedal| at {OCT_HI:.0f} Hz re mid: worst {worst:.2f} dB "
          f"(<= {G1_LEVEL_TOL}) .......... {ok(a)}")
    print(f"  G1b  and INVARIANT across stimulus level: spread {spread:.2f} dB "
          f"(<= {G1_INVARIANCE_TOL}) ..... {ok(b)}")
    print("       (nothing nonlinear is engaged on this path, so any level dependence here would")
    print("        mean the instrument itself is level-dependent and G2 would be unreadable)")
    if not (a and b):
        print("\n  ⛔ G1 FAILED: our HF linear response disagrees with the pedal on the CLEAN path.")
        print("     Everything below is moot -- fix the linear response first. G2's drive-")
        print("     dependence argument only isolates a NONLINEAR cause once the linear one is out.")
    return a and b


# ---------------------------------------------------------------- G2

def gate_rate(acc):
    drawn = drawn_rate()
    print(f"\n=== G2  HF ROLLOFF *RATE* over {OCT_LO:.0f} -> {OCT_HI:.0f} Hz, dB/octave ===")
    print(f"    the drawn POST-clipper network gives {drawn:.2f} dB/oct across this octave —")
    print( "    DERIVED from the two schematic-verified Sallen-Keys (IC4_B 10.7 kHz, IC4_A 3.3 kHz),")
    print( "    not the -24 asymptote: at 8127.5 Hz the pair is not yet fully past the 10.7 kHz corner")
    print(f"    ⚠ that is the rate of TWO elements (IC4_B, IC4_A), not of the OD PATH, which also")
    print(f"      contains the treble/ATTACK ladder, C7, C10, C14 and the recovery bridged-T. It is")
    print(f"      printed as a REFERENCE. Session 114 deleted the guard that required the model to")
    print(f"      MATCH it -- see the note below G2a.")
    print(f"\n  {'condition':<28}{'n':>4} |" + "".join(f"{s.replace('sweep_',''):>19}" for s in SWEEPS))
    print(f"  {'':<28}{'':>4} |" + "".join(f"{'pedal      model':>19}" for _ in SWEEPS))
    ped, mod = {}, {}
    for k in CLASSES:
        if k not in acc:
            continue
        n, cells = 0, []
        for sw in SWEEPS:
            pr, mr, _, _, _ = acc[k][sw]
            if not pr:
                cells.append(f"{'--':>19}")
                continue
            n = len(pr)
            ped[(k, sw)], mod[(k, sw)] = list(pr), list(mr)
            cells.append(f"{np.median(pr):9.1f}{np.median(mr):10.1f}")
        print(f"  {k:<28}{n:>4} |" + "".join(cells))

    od = [k for k in CLASSES if k.startswith("OD")]
    # s108 P4: these cells pool over the pedal's OWN switches (ATTACK is literally an HF control,
    # C8 220 pF), so the SPREAD is printed beside every median rather than averaged away.
    print(f"\n  per-cell spread [min,max] over the {len(ped[(od[0], SWEEPS[0])])} conditions in each class:")
    for k in od:
        print(f"    {k:<28}" + "".join(
            f"  {sw.replace('sweep_',''):<8} P[{min(ped[(k,sw)]):6.1f},{max(ped[(k,sw)]):6.1f}] "
            f"M[{min(mod[(k,sw)]):6.1f},{max(mod[(k,sw)]):6.1f}]\n{'':>34}" for sw in SWEEPS).rstrip())
    print(f"    ⇒ the MODEL's own rate spans up to {max(max(mod[(k,sw)])-min(mod[(k,sw)]) for k in od for sw in SWEEPS):.1f}"
          f" dB/oct WITHIN one cell, because ATTACK and GRUNT")
    print( "      are HF controls. 'Does the model hold ONE rate?' is not a question this path can")
    print( "      answer, which is what the retired G2a was asking.")

    m_all = [x for k in od for sw in SWEEPS for x in mod[(k, sw)]]
    hot_p = [x for k in od for x in ped[(k, "sweep_drv_-6")]]
    hot_m = [x for k in od for x in mod[(k, "sweep_drv_-6")]]
    gaps = [min(x for k in od for x in ped[(k, sw)]) - max(x for k in od for x in mod[(k, sw)])
            for sw in SWEEPS]

    a = max(m_all) <= 0.0
    print(f"\n  G2a  the MODEL never GAINS with frequency across this octave, at any condition or")
    print(f"       stimulus — a chain of fixed lowpass elements cannot, whatever the HF switches do:")
    print(f"       worst model rate = {max(m_all):+.2f} dB/oct over {len(m_all)} cells (<= 0) ..... {ok(a)}")
    print( "       ⚠ REPLACES session 101's 'worst |model - drawn| <= 6 dB/oct'. That guard compared")
    print( "         the WHOLE OD path against the rate of two of its elements, and it is the reason")
    print( "         GATE I read FAIL from session 109 to 113. It is not a threshold that needed")
    print( "         loosening — the quantity it constrained is not required to hold.")

    b = min(hot_p) > max(hot_m)
    print(f"\n  G2b  at the hottest stimulus every PEDAL condition GAINS and every MODEL condition")
    print(f"       ROLLS OFF — a complete separation, so there is no threshold to argue about:")
    print(f"       pedal n={len(hot_p)} [{min(hot_p):+.2f},{max(hot_p):+.2f}]   "
          f"model n={len(hot_m)} [{min(hot_m):+.2f},{max(hot_m):+.2f}]")
    print(f"       gap = min(pedal) - max(model) = {min(hot_p)-max(hot_m):+.2f} dB/oct "
          f"(> 0) ....... {ok(b)}")
    print( "       ⚠ this is a MIN-vs-MAX over every condition, i.e. STRICTER than the median")
    print( "         comparison it replaces — the repair does not buy the pass by weakening the test.")

    c = all(gaps[i] < gaps[i + 1] for i in range(len(gaps) - 1))
    print(f"\n  G2c  and the separation GROWS with stimulus — a drive-generated artefact must,")
    print(f"       a fixed filter difference cannot (free dose-response check, no parameter):")
    print( "       " + "  ".join(f"{sw.replace('sweep_',''):>8}" for sw in SWEEPS))
    print( "       " + "  ".join(f"{g:>+8.2f}" for g in gaps) + f"   monotone ..... {ok(c)}")

    verdict = a and b and c
    print("\n  ⇒ " + ("THE PEDAL GAINS TOP-OCTAVE CONTENT WHERE OUR OD PATH CANNOT. No Sallen-Key "
                      "value\n    produces gain across this octave, and the effect grows with drive, "
                      "so the region's\n    error is NOT our linear HF response -- it is drive-"
                      "generated content in ND that\n    survives Farina H1 gating."
                      if verdict else
                      "INCONCLUSIVE on the rate axis -- read the table, do not quote a verdict."))
    return verdict


# ---------------------------------------------------------------- G3

def _pedal_curve(orig, inp, name, sw):
    x = A.load(os.path.join(CAPDIR, name))
    cap = x[0] if isinstance(x, tuple) else x
    cap_al, _ = A.align(cap, orig)
    g, G = A.transfer_h1(A.seg_of(cap_al, sw), inp)
    m = (g >= MID_ANCHOR[0]) & (g <= MID_ANCHOR[1])
    return g, G - G[m].mean()


def gate_fold_locus(name="level-1700_base-od.wav", step=250.0):
    print(f"\n=== G3  FOLD-LOCUS TEST — is the excess ON f = fs/(N+1)? ({name}, pedal only) ===")
    loci = {FS / (n + 1): n for n in range(2, 8)}
    print("    loci: " + ", ".join(f"H{n} -> {f:.0f} Hz" for f, n in sorted(loci.items())))
    x = A.load(A.ORIG)
    orig = x[0] if isinstance(x, tuple) else x
    inp = A.seg_of(orig, "sweep_clean")
    g, base = _pedal_curve(orig, inp, name, "sweep_clean")
    edges = np.arange(5000.0, 20001.0, step)

    def binned(Gn):
        return np.array([10 * np.log10(np.mean(10 ** (Gn[(g >= a) & (g < b)] / 10)))
                         if ((g >= a) & (g < b)).any() else np.nan
                         for a, b in zip(edges[:-1], edges[1:])])

    b0 = binned(base)
    cols = {sw: binned(_pedal_curve(orig, inp, name, sw)[1]) - b0 for sw in SWEEPS[1:]}
    ctr = 0.5 * (edges[:-1] + edges[1:])
    hot = cols["sweep_drv_-6"]

    print(f"\n  DRIVE-INDUCED EXCESS = H1(level) - H1(clean), dB, {step:.0f} Hz bins")
    print(f"  {'centre':>8} |" + "".join(f"{s.replace('sweep_drv_','drv'):>9}" for s in SWEEPS[1:]))
    for i, c in enumerate(ctr):
        mark = next((f"   <== H{n} locus ({f:.0f} Hz)" for f, n in loci.items()
                     if edges[i] <= f < edges[i + 1]), "")
        if mark or i % 4 == 0:
            print(f"  {c:8.0f} |" + "".join(f"{cols[s][i]:9.2f}" for s in SWEEPS[1:]) + mark)

    # A fold deposits a LOCAL PEAK at the locus. The statistic is prominence: the excess AT the
    # locus minus the mean of the excess in a surrounding annulus. A fold gives a positive
    # prominence; a smooth shelf -- of any steepness -- gives ~0.
    #
    # ⚠ THE FIRST DRAFT USED RAW CURVATURE AND FAILED FOR ITS OWN REASON, which is recorded because
    # it is a general trap: |2nd difference| is large wherever a SIGMOID turns over, and this excess
    # IS a sigmoid. It duly fired 27x at the H6 locus (6857 Hz) -- which is simply where the dip
    # bottoms out -- and printed "the fold mechanism is live here" over a curve that is flat to
    # 0.73 dB across the 6 kHz containing the H2 locus. With six loci scattered over the band, some
    # locus will always sit near a smooth feature's inflection. Prominence cannot make that mistake.
    #
    # Restricted to N = 2..4. Those are the orders with meaningful amplitude AND the ones whose loci
    # fall inside the region under investigation; H6/H7 sit below 8 kHz and carry little energy, so
    # a null result there would be uninformative either way. The weak loci are still PRINTED.
    STRONG = {n: FS / (n + 1) for n in (2, 3, 4)}
    ann = 1500.0

    def prominence(f):
        i = int(np.argmin(np.abs(ctr - f)))
        near = np.abs(ctr - f) <= 0.5 * step * 1.5
        out = (np.abs(ctr - f) > ann * 0.5) & (np.abs(ctr - f) <= ann)
        if not near.any() or not out.any():
            return np.nan
        return float(np.nanmean(hot[near]) - np.nanmean(hot[out]))

    print(f"\n  G3a  LOCAL PROMINENCE at each locus (excess at the locus minus its ±{ann:.0f} Hz")
    print( "       annulus). A fold deposits a positive peak; a smooth shelf gives ~0.")
    proms = {}
    for n in sorted(loci.values()):
        f = FS / (n + 1)
        p = prominence(f)
        proms[n] = p
    # ⚠ A BARE PROMINENCE THRESHOLD IS NOT A VALID TEST HERE, and the second draft failed on it:
    # this excess is a sigmoid, and a symmetric annulus straddling a curved flank returns a nonzero
    # prominence from the CURVATURE alone. H4 (9600 Hz) sits on the steepest part of the rise and
    # duly scored +2.09 dB with no peak present. Tuning the threshold until it passes would be
    # fitting the gate to the answer.
    #
    # The valid form is a NULL: compute the same statistic at every non-locus frequency on the same
    # curve, and ask whether the loci are outliers in THAT distribution. A real fold puts its locus
    # in the top few percent; sigmoid curvature puts it wherever the flank happens to be, which the
    # controls sample too. Parameter-free, and immune to the curve's shape.
    grid = ctr[(ctr >= 8000.0) & (ctr <= 19000.0)]
    null = np.array([prominence(f) for f in grid
                     if all(abs(f - FS / (n + 1)) > ann for n in loci.values())])
    null = null[np.isfinite(null)]
    pct = {n: float((null < proms[n]).mean() * 100.0) for n in STRONG if np.isfinite(proms[n])}
    # ⚠ THE HEADLINE VERDICT IS SCORED ON H2 ALONE, and that is a scope limit, not a cherry-pick.
    # H2 is (a) the strongest order, so the largest fold, and (b) the only locus lying inside
    # 16255 Hz -- the band that owns 25.7 % of the OD band-RMS and is the whole reason this gate
    # exists. H3/H4 are printed and NOT scored because the null is thin (the ±1500 Hz exclusions
    # around six loci leave few controls) and because both sit on the sigmoid's steep flank, where
    # the statistic is curvature-biased. Underpowered is not the same as negative: this gate
    # REFUTES the fold at H2 and says nothing either way at H3/H4.
    worst = pct.get(2, float("nan"))
    smooth = bool(worst < 95.0)
    plat = hot[(ctr >= PLATEAU[0]) & (ctr <= PLATEAU[1])]
    flat = float(np.nanmax(plat) - np.nanmin(plat))
    for n in sorted(loci.values()):
        f = FS / (n + 1)
        if n == 2:
            tag = f"  pct vs {len(null)} controls {pct[n]:5.1f}%  <== SCORED (in 16255 Hz band)"
        elif n in pct:
            tag = f"  pct {pct[n]:5.1f}%  (NOT scored: thin null, on the sigmoid flank)"
        else:
            tag = "     (printed only — weak order, below the region)"
        print(f"       H{n} @ {f:7.0f} Hz : {proms[n]:+7.2f} dB{tag}")
    print(f"       H2 sits at the {worst:.1f}th percentile of the null "
          f"(< 95 = unremarkable) ..... {ok(smooth)}")
    print(f"\n  G3b  {PLATEAU[0]/1000:.1f}-{PLATEAU[1]/1000:.1f} kHz at drv_-6: mean "
          f"{np.nanmean(plat):+.2f} dB, spread {flat:.2f} dB over {PLATEAU[1]-PLATEAU[0]:.0f} Hz")
    print(f"       the H2 locus (16000 Hz) is INSIDE that span, so a fold there would have to")
    print(f"       show up in this spread .................................... {ok(flat < 2.0)}")
    verdict = smooth and flat < 2.0
    print("\n  ⇒ " + ("THE KA-5 FOLD MECHANISM IS REFUTED AT H2 — the excess passes through\n"
                      "    16000 Hz as a smooth plateau, so it cannot be what fills the 16255 Hz\n"
                      "    band. Session 90's mechanism is real; it is not what this is.\n"
                      "    ⚠ NOT tested at H3/H4: thin null, curvature-biased. Open, not negative."
                      if verdict else
                      "A LOCALISED FEATURE SITS ON THE H2 LOCUS -- the fold mechanism is live."))
    return verdict


# ---------------------------------------------------------------- G4

POOL_OPTIONS = (
    ("current   25 Hz-16.3 kHz (all)", lambda f: True),
    ("drop 8-16.3 kHz   (top 4)", lambda f: f < 8000.0),
    ("drop 11-16.3 kHz  (top 2)", lambda f: f < 11000.0),
    ("drop 16.3 kHz     (top 1)", lambda f: f < 14500.0),
)


def gate_pool(paths):
    print("\n=== G4  POOL-RESTRICTION CONSEQUENCE — computed, on candidate AND baseline ===")
    print("    Session 91: an exclusion can make a gate HARDER, because the excluded bands may")
    print("    have been diluting a percentile downward. So the PASSING rows are recomputed too.")
    for path, label in paths:
        bands, idx, rows, used = RG.deltas(path)
        od = RG.subsets(rows)["OD"]
        f = np.array([bands[i] for i in idx])
        M = np.stack([v[0] for v in od.values()])
        print(f"\n  --- {label}  ({os.path.basename(path)}, {M.shape[0]} OD rows, {used}) ---")
        print(f"  {'pool':<34}{'bands':>6}{'band-RMS':>10}{'median':>9}{'p90':>8}{'p99':>8}")
        for name, keep in POOL_OPTIONS:
            sel = [j for j in range(len(f)) if keep(f[j])]
            sub, flat = M[:, sel], M[:, sel].ravel()
            print(f"  {name:<34}{len(sel):>6}"
                  f"{float(np.mean(np.sqrt((sub**2).mean(axis=1)))):>10.3f}"
                  f"{np.percentile(flat,50):>9.3f}{np.percentile(flat,90):>8.3f}"
                  f"{np.percentile(flat,99):>8.3f}")
        print("  SHIP: band-RMS <= 2.0,  p99 <= 4.0")
    print("\n  ⚠ Read the MEDIAN column: it gets WORSE under every exclusion. The HF bands were")
    print("    diluting it downward, exactly as the 25-100 Hz bands were diluting CLEAN's p90 in")
    print("    session 91. An exclusion here is not a free pass.")
    print("  ⚠ And p99 stays far over its 4.0 bar with ALL FOUR HF bands dropped -- so this region")
    print("    is NOT the p99 story, and excluding it closes ONE gate row, not Phase 9.")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report")
    ap.add_argument("--baseline", default="analysis/reports/s91_shipped.json",
                    help="second report for G4's control column (session 91's trap)")
    ap.add_argument("--capture", default="level-1700_base-od.wav", help="G3's row")
    ap.add_argument("--skip-fine", action="store_true", help="skip G3 (needs the capture wavs)")
    ap.add_argument("--json", default="", help="write the verdicts here")
    args = ap.parse_args()

    d, bands, lo, hi = band_octave(args.report)
    acc, dropped = collect(d, bands, lo, hi)

    print(f"### GATE I — the OD 8-16.3 kHz residual   [{os.path.basename(args.report)}]\n")
    gate_membership(acc, dropped)
    g1 = gate_clean_control(acc)
    g2 = gate_rate(acc)
    g3 = None if args.skip_fine else gate_fold_locus(args.capture)
    pool = [(args.report, "CANDIDATE")]
    if args.baseline and os.path.exists(args.baseline):
        pool.append((args.baseline, "BASELINE control"))
    gate_pool(pool)

    print("\n" + "=" * 78)
    print("VERDICT")
    print("=" * 78)
    print(f"  G1 clean control (our linear HF is right) ........ {ok(g1)}")
    print(f"  G2 pedal GAINS where our path cannot, growing with drive  {ok(g2)}")
    print(f"  G3 NOT the fs/(N+1) fold mechanism ............... "
          f"{'skipped' if g3 is None else ok(g3)}")
    if g1 and g2:
        print("\n  ⇒ SESSION 89's OPEN QUESTION IS ANSWERED: the residual is ND's, not our")
        print("    Sallen-Keys. Our OD path ROLLS OFF at every condition and stimulus while the")
        print("    pedal's GAINS at the hottest, with the gap growing monotonically with drive --")
        print("    the 'dense inharmonic content that reads as aliasing' already recorded in")
        print("    reference-sources.md §4, now measured on the FR axis.")
        print("  ⚠ NOT claimed: 'our OD path delivers the drawn 4th-order rolloff'. Session 114")
        print("    retired that sentence -- the OD path's rate spans ~19 dB/oct across ATTACK and")
        print("    GRUNT, which are HF controls, and nothing requires it to match the two")
        print("    Sallen-Keys alone. G1 is where our linear HF response is established.")
        print("\n  ⚠ NOT claimed: that the region is ENTIRELY artefact. G2's low-drive column")
        print("    still shows a real gap, and the 8127.5 Hz band's error is drive-INDEPENDENT,")
        print("    i.e. a separate genuine defect a blanket exclusion would excuse. Whether the")
        print("    gate should still grade these bands is a USER DECISION, not this tool's.")
    if args.json:
        json.dump({"report": args.report, "drawn_rate_db_oct": drawn_rate(),
                   "G1": bool(g1), "G2": bool(g2),
                   "G3": None if g3 is None else bool(g3)},
                  open(args.json, "w"), indent=1)
        print(f"\n  wrote {args.json}")
    return 0 if (g1 and g2) else 1


if __name__ == "__main__":
    sys.exit(main())
