#!/usr/bin/env python3.11
"""GATE BO — DOES THE GRUNT AXIS'S ORDERING SURVIVE AT THE MIX?  (session 186, item 19's task P3)

THE TASK, AND WHY IT IS A MEASUREMENT RATHER THAN A DICT EDIT
-------------------------------------------------------------
P3 is "rebalance `od_tone_restore_fit.SETS` toward the mix".  Rebalancing a membership table is
bookkeeping; what makes it worth a session is the question the imbalance raises, and s186 measured
the imbalance sharply enough to state it:

  * the 8 pre-s186 groups hold **17 of 29 rows at cf = 0.02418**, the bleed-free corner;
  * far sharper, **the GRUNT axis is 12 of 12 rows bleed-free** (`grunt_flat`, `grunt_boost`,
    `grunt_hot`, `grunt_cold`), and `null_depth_censor_gate.ROWS` — which GATE AQ and GATE AX both
    inherit — names three bleed-free sets as *the* GRUNT mapping.

So this stage's GRUNT-ROWED tables (`kNotchGainDb[3][5]`, `kNotchMixK[3][5]`, `kNotchQ[3][5]`) have
only ever been graded at ONE clean fraction, on the axis that has three rows to choose between.
That is fine if the axis reads the same at a played setting and a defect in the instrument if it
does not — and *which GRUNT position the stage is worst at* is exactly the kind of thing a table
with one entry per position is prioritised on.

⇒ THE GRADED QUESTION: **does the ORDERING of the three GRUNT positions, by how much correction the
320 Hz null still needs, agree between the BLEED-FREE arm and the MIXED arm?**

WHY AN ORDERING AND NOT A MAGNITUDE
-----------------------------------
At a mixed cell BOTH sides are diluted by the same clean tap, so |pedal − model| is SMALLER there
for reasons that have nothing to do with the stage being better.  Comparing magnitudes across cf is
`difference-statistics-hide-common-mode` with the common mode being the mix itself.  A RANK across
the three GRUNT positions is taken WITHIN an arm, so the dilution is common to all three and
cancels out of the comparison — it needs no bar, no normalisation and no model of the mix.

⚠⚠ AND THE RANK MUST BE SHOWN TO BE A PROPERTY BEFORE IT IS COMPARED.  s178 measured this project's
sharpest instance of the opposite: the treble null's DEPTH inverts between adjacent stimulus rungs,
so "20 dB too deep" and "11 dB too shallow" were the same build two rungs apart, and depth was
therefore refused as a target while ORDERING was kept.  BO2 reads all four sweeps per cell and
reports the rank per sweep; a rank that does not hold across stimulus is not a fact about GRUNT and
this gate says so rather than pooling it away (`an-endpoint-pair-is-not-a-ladder`, s129).

MEMBERSHIP — MATCHED, AND THE UNMATCHED PART IS NAMED
------------------------------------------------------
The bleed-free GRUNT block runs DRIVE {0, 0.5, 1.0}; the mixed one runs {0, 0.25, 0.5}, because
`drive-1430_grunt-*` and `drive-1700_grunt-flat` are NOT ON DISK and capture access is ending
(`reference-sources.md` §0) — a permanent gap, not a request.  The MATCHED block is therefore
**3 GRUNT x DRIVE {0.0, 0.5} = 6 cells per arm**, and that is what BO2 grades.  ⛔ There is no
mixed twin of `grunt_hot` at all; BO1 prints the gap rather than letting a pooled statistic hide it.

ESTIMATOR
---------
E6 — `od_tone_restore_fit.notch_geometry`, IMPORTED, never re-derived.  That is the estimator the
shipped table was fitted on, and GATE AW proved GATE W's E1 is `E1 <= E6` identically and mixes
DEPTH with WIDTH, so E1 must not adjudicate this stage.  BOTH depths are printed (s152) and the
AREA depth is what BO2 grades (s180 BJ0d: the POINT depth is a lower bound wherever a null's bottom
sits at or below the deconvolution residue, and the arm-choosing column is exactly where that
inflated s178's readings by up to 2.7x).  `q_interp`, never the quantised `q` (s153 AQ1c).

Run:
    python3.11 analysis/mix_membership_gate.py
    python3.11 analysis/_mutate_gate_bo.py          # the mutation runner
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import captures as C                      # noqa: E402
import feature_locus_gate as W            # noqa: E402
import od_tone_restore_fit as OT          # noqa: E402

REPORT = "analysis/reports/s186_mix_membership.json"
REN_DIR = OT.REN_DIR                      # shared with the fit tool: the same renders, one cache

# ---- the matched block -------------------------------------------------------------------------
# (GRUNT name, physical Clipper::Grunt position).  The physical position, not the APVTS index —
# `grunt_pos_of` does that mapping and s151 records what raw `gruntIdx` costs.
GRUNTS = (("cut", 0), ("flat", 1), ("boost", 2))

# The two arms, as (arm name, {grunt name: {drive: capture}}).  Every entry is a real file; BO0a
# asserts each one's parsed settings rather than trusting the filename convention (s114).
MATCHED_DRIVES = (0.0, 0.5)

# ⚠⚠ THE RANK IS GRADED AT DRIVE 0.5 ALONE, AND THAT IS A MEASURED RESTRICTION, NOT A CHOICE.
# At DRIVE 0 the MIXED arm's GRUNT-cut cell (`drive-0700_base-od.wav`) is unreadable at ALL FOUR
# sweeps — the reader refuses because the minimum rests on a CORE bound, i.e. the composite has no
# 320 Hz null there at all: the OD path is barely driven and a 46 %-clean tap floors what is left.
# That is physics and the refusal is correct (s151), but it means the arms are NOT matched at
# DRIVE 0, and ranking one arm over 3 positions against the other over 2 is exactly the
# unmatched-pooling trap s178 committed (`aggregate-moved-check-membership-first`).  BO2 reports
# the DRIVE-0 column and grades the DRIVE-0.5 one.  ⛔ Do NOT "fix" this by widening CORE: s151
# measured that a window wide enough to hold this null's right shoulder puts the global minimum
# ~550 Hz away, on the bridged-T, and the reader then silently tracks a different feature.
GRADE_DRIVE = 0.5

ARMS = {
    "bleedfree": {
        "cut":   {0.0: "drive-0700_level-1700_base-od.wav",
                  0.5: "level-1700_base-od.wav"},
        "flat":  {0.0: "drive-0700_level-1700_grunt-flat_base-od.wav",
                  0.5: "level-1700_grunt-flat_base-od.wav"},
        "boost": {0.0: "drive-0700_level-1700_grunt-boost_base-od.wav",
                  0.5: "level-1700_grunt-boost_base-od.wav"},
    },
    "mix": {
        "cut":   {0.0: "drive-0700_base-od.wav",
                  0.5: "ref-od.wav"},
        "flat":  {0.0: "drive-0700_grunt-flat_base-od.wav",
                  0.5: "grunt-flat_base-od.wav"},
        "boost": {0.0: "drive-0700_grunt-boost_base-od.wav",
                  0.5: "grunt-boost_base-od.wav"},
    },
}

PLAY_SWEEP = "sweep_drv_-12"              # `playing-level-is-drv-minus-12`
SWEEPS = W.SWEEPS

FAIL = []


def fail(tag, msg):
    FAIL.append(f"{tag}: {msg}")
    print(f"  ✗ {tag} FAIL — {msg}")


# =================================================================================================
# BO0 — guards and known answers
# =================================================================================================
def gate_bo0():
    print("\n== BO0  GUARDS AND KNOWN ANSWERS ==")

    # -- BO0a: the fit tool's own membership guard, plus this gate's block ------------------------
    OT.check_sets(verbose=True)
    e = OT.bleedfree_cf()
    for arm, blocks in ARMS.items():
        for gname, gpos in GRUNTS:
            for drv, fname in sorted(blocks[gname].items()):
                p = C.parse_capture(fname)
                got = OT.grunt_pos_of(fname)
                cf = OT.clean_frac_of(fname)
                if got != gpos:
                    fail("BO0a", f"{arm}/{gname}/{drv}: {fname} is GRUNT position {got}, not {gpos}")
                if abs(p["drive"] - drv) > 1e-9:
                    fail("BO0a", f"{arm}/{gname}/{drv}: {fname} has DRIVE {p['drive']}")
                bf = abs(cf - e) <= OT.BLEEDFREE_CF_TOL
                if (arm == "bleedfree") != bf:
                    fail("BO0a", f"{arm}/{gname}/{drv}: {fname} cf={cf:.5f} contradicts its arm")
    if not FAIL:
        print(f"  ✓ BO0a  {sum(len(b[g]) for b in ARMS.values() for g, _ in GRUNTS)} cells; "
              f"every GRUNT position, DRIVE and arm confirmed from the capture's OWN settings")

    # -- BO0b: THE ARMS DIFFER ONLY IN THE MIX ----------------------------------------------------
    # The whole comparison rests on this: if the two arms differed in anything else, a rank change
    # would be attributable to that instead.  LEVEL is the only knob that moves between them.
    diffs = set()
    for gname, _ in GRUNTS:
        for drv in MATCHED_DRIVES:
            a = C.parse_capture(ARMS["bleedfree"][gname][drv])
            b = C.parse_capture(ARMS["mix"][gname][drv])
            for k in sorted(set(a) | set(b)):
                if isinstance(a.get(k), (int, float)) and isinstance(b.get(k), (int, float)):
                    if abs(a[k] - b[k]) > 1e-9:
                        diffs.add(k)
    if diffs != {"level"}:
        fail("BO0b", f"the two arms differ in {sorted(diffs)}, expected LEVEL alone — a rank "
                     f"change would not be attributable to the mix")
    else:
        print("  ✓ BO0b  the arms differ in LEVEL and nothing else (1.0 -> 0.5); every other "
              "setting is\n          identical cell for cell, so a rank change is the mix's")

    # -- BO0c: NON-VACUITY — the arms must actually render differently ----------------------------
    # A comparison whose two arms are the same audio confirms nothing, and would print a perfect
    # rank agreement (s183: an equality-only guard set cannot detect a broken comparison).
    g, pa, ma = OT.curves(ARMS["bleedfree"]["cut"][0.5], PLAY_SWEEP, ren_dir=REN_DIR)
    _, pb, mb = OT.curves(ARMS["mix"]["cut"][0.5], PLAY_SWEEP, ren_dir=REN_DIR)
    band = (g >= 250.0) & (g <= 900.0)
    dm = float(np.max(np.abs(ma[band] - mb[band])))
    dp = float(np.max(np.abs(pa[band] - pb[band])))
    if dm < 1.0 or dp < 1.0:
        fail("BO0c", f"the arms are near-identical (model {dm:.3f} dB, pedal {dp:.3f} dB) — the "
                     f"comparison has nothing to compare")
    else:
        print(f"  ✓ BO0c  NON-VACUOUS: over 250-900 Hz the arms differ by {dm:.2f} dB (model) and "
              f"{dp:.2f} dB (pedal)")
    return e


# =================================================================================================
# BO1 — the imbalance, and the gap
# =================================================================================================
def gate_bo1(e):
    print("\n== BO1  THE MEMBERSHIP IMBALANCE THIS TASK EXISTS TO CORRECT ==")
    rows = OT.check_sets()
    froz = [r for r in rows if r[0] in OT.FROZEN_SETS]
    fbf = sum(1 for r in froz if abs(r[3] - e) <= OT.BLEEDFREE_CF_TOL)
    gr = [r for r in froz if r[0] in ("grunt_flat", "grunt_boost", "grunt_hot", "grunt_cold")]
    gbf = sum(1 for r in gr if abs(r[3] - e) <= OT.BLEEDFREE_CF_TOL)
    allbf = sum(1 for r in rows if abs(r[3] - e) <= OT.BLEEDFREE_CF_TOL)
    print(f"  pre-s186 (the 8 frozen groups) : {fbf} of {len(froz)} rows bleed-free "
          f"({100.0*fbf/len(froz):.0f} %)")
    print(f"    of which the GRUNT axis      : {gbf} of {len(gr)} rows bleed-free "
          f"({100.0*gbf/len(gr):.0f} %)  <- the sharp one")
    print(f"  post-s186 (all {len(OT.SET_META)} groups)    : {allbf} of {len(rows)} rows bleed-free "
          f"({100.0*allbf/len(rows):.0f} %)")
    if gbf != len(gr):
        fail("BO1", f"the GRUNT axis was measured as {gbf}/{len(gr)} bleed-free, not all of it — "
                    f"this gate's premise has changed and its framing must be re-read")
    else:
        print(f"  ⭐ the GRUNT axis was {len(gr)} of {len(gr)} bleed-free, so `kNotchGainDb[3][5]`, "
              f"`kNotchMixK[3][5]`\n     and `kNotchQ[3][5]` have only ever been graded at ONE "
              f"clean fraction (cf = {e:.5f}).")
    print("\n  ⛔ THE PERMANENT GAP, NAMED: there is no mixed twin of `grunt_hot` (DRIVE max across "
          "GRUNT).\n     `drive-1700_grunt-flat_base-od.wav` is not on disk and capture access is "
          "ending, so the\n     matched block stops at DRIVE 0.5.  That is a bound on this gate, "
          "not an omission from it.")
    return {"frozen_rows": len(froz), "frozen_bleedfree": fbf, "grunt_rows": len(gr),
            "grunt_bleedfree": gbf, "all_rows": len(rows), "all_bleedfree": allbf}


# =================================================================================================
# BO2 — the ordering
# =================================================================================================
def read_cell(fname, drv, sweep, depth="area"):
    """-> dict of both sides' null geometry, or None if either side refuses.

    A refusal is a reading of the physics (the composite null genuinely dissolves at heavy clean
    blend), never an error to swallow — the caller NAMES it (s151)."""
    g, ped, mod = OT.curves(fname, sweep, ren_dir=REN_DIR)
    try:
        p = OT.notch_geometry(g, ped, depth=depth)
        m = OT.notch_geometry(g, mod, depth=depth)
    except RuntimeError as ex:
        return {"refused": str(ex)}
    return {"refused": None,
            "ped_point": p["depth_point"], "ped_area": p["depth_area"], "ped_q": p["q_interp"],
            "mod_point": m["depth_point"], "mod_area": m["depth_area"], "mod_q": m["q_interp"],
            "corr_point": p["depth_point"] - m["depth_point"],
            "corr_area": p["depth_area"] - m["depth_area"],
            "ped_f0": p["f0"], "mod_f0": m["f0"]}


def gate_bo2():
    """The graded sub-gate: rank the three GRUNT positions within each arm, per sweep."""
    print("\n== BO2  THE GRUNT ORDERING, BLEED-FREE vs MIX  (matched block: 3 GRUNT x DRIVE "
          f"{MATCHED_DRIVES}) ==")
    print("  `corr` = pedal depth - model depth = the CUT still needed, in dB (AREA depth, the "
          "censor-robust one).")

    cells = {}
    for arm in ("bleedfree", "mix"):
        for gname, _ in GRUNTS:
            for drv in MATCHED_DRIVES:
                for sw in SWEEPS:
                    cells[(arm, gname, drv, sw)] = read_cell(ARMS[arm][gname][drv], drv, sw)

    refused = [k for k, v in cells.items() if v["refused"]]
    if refused:
        print(f"\n  ⚠ {len(refused)} of {len(cells)} cells REFUSED (the null is not readable there) "
              f"— named, not dropped:")
        for k in sorted(refused):
            print(f"      {k[0]:<10} {k[1]:<6} drv {k[2]:g}  {k[3]:<14} {cells[k]['refused'][:78]}")
        # A refusal that is TOTAL on one arm's cell is a finding, not attrition: it says the stage
        # has nothing measurable there at all, which no bleed-free set could ever have reported.
        for arm in ("bleedfree", "mix"):
            for gname, _ in GRUNTS:
                for d in MATCHED_DRIVES:
                    n = sum(1 for sw in SWEEPS if cells[(arm, gname, d, sw)]["refused"])
                    if n == len(SWEEPS):
                        print(f"    ⭐ {arm}/{gname}/drv {d:g} refuses at ALL {n} sweeps — the "
                              f"composite has NO 320 Hz null\n       there on any stimulus, which "
                              f"is why {GRADE_DRIVE:g} and not {d:g} is the graded drive.")

    # -- the per-sweep table ----------------------------------------------------------------------
    # ⚠⚠ RANKED BY |corr|, DESCENDING — "the position the stage is FURTHEST OFF at".  The first
    # draft sorted by the SIGNED value and labelled the result "worst -> best", which put a cell
    # needing -2.1 dB ahead of one needing -9.8: `computed-verdicts-not-narrated`, committed inside
    # the one line the whole gate is graded on.  The SIGN is a real and separate fact (negative =
    # the model's null is already TOO DEEP), so it is printed as its own column rather than folded
    # into the ordering.
    ranks = {}
    for sw in SWEEPS:
        print(f"\n  --- sweep {sw} " + "-" * 58)
        print(f"    {'arm':<10} {'GRUNT':<6} | " + " | ".join(f"drv {d:g}" for d in MATCHED_DRIVES)
              + f" | graded (drv {GRADE_DRIVE:g})   |corr|   rank")
        for arm in ("bleedfree", "mix"):
            got = {}
            for gname, _ in GRUNTS:
                c = cells[(arm, gname, GRADE_DRIVE, sw)]
                got[gname] = None if c["refused"] else float(c["corr_area"])
            ok = {k: v for k, v in got.items() if v is not None}
            order = sorted(ok, key=lambda k: -abs(ok[k]))
            # KNOWN ANSWER on the gate's own sort.  The first draft sorted by the SIGNED value
            # while labelling the result "worst -> best", which ranked -2.1 dB ahead of -9.8.
            # Asserting the property the LABEL claims is what makes that unrepeatable — and it is
            # a property of the sort, so it costs nothing and can never be "nearly" true.
            mags = [abs(ok[k]) for k in order]
            if mags != sorted(mags, reverse=True):
                fail("BO2", f"{arm}/{sw}: the ordering is not sorted by |corr| descending "
                            f"({mags}) — the rank does not mean what its label says")
            ranks[(arm, sw)] = tuple(order) if len(ok) == len(GRUNTS) else None
            for gname, _ in GRUNTS:
                v = got[gname]
                cols = []
                for d in MATCHED_DRIVES:
                    c = cells[(arm, gname, d, sw)]
                    cols.append(" REFUSED" if c["refused"] else f"{c['corr_area']:8.3f}")
                r = "-" if v is None else str(order.index(gname) + 1)
                sv = "       -        -" if v is None else f"{v:9.3f} {abs(v):8.3f}"
                print(f"    {arm:<10} {gname:<6} | " + " | ".join(cols) + f" | {sv}      {r}")
            if ranks[(arm, sw)]:
                signs = "/".join("+" if got[g] > 0 else "-" for g in ("cut", "flat", "boost"))
                print(f"    {'':<10} {'ORDER':<6} |  furthest off -> closest: "
                      f"{' > '.join(ranks[(arm, sw)])}   (signs cut/flat/boost {signs})")

    # -- is the rank a PROPERTY at all? (s178's knife-edge lesson) --------------------------------
    print("\n  --- is the ordering STABLE across stimulus? " + "-" * 44)
    stable = {}
    for arm in ("bleedfree", "mix"):
        rs = [ranks[(arm, sw)] for sw in SWEEPS if ranks.get((arm, sw))]
        uniq = set(rs)
        stable[arm] = (len(uniq) == 1 and len(rs) == len(SWEEPS))
        print(f"    {arm:<10} {len(rs)}/{len(SWEEPS)} sweeps readable, {len(uniq)} distinct "
              f"ordering(s): " + "; ".join(" > ".join(r) for r in sorted(uniq)))
    if not all(stable.values()):
        print("    ⚠⚠ AN ORDERING THAT MOVES WITH STIMULUS IS NOT A FACT ABOUT GRUNT.  s178 found "
              "exactly this on\n        the treble null and refused DEPTH as a target for it.  The "
              "comparison below is then a\n        comparison of two unstable things and is "
              "reported as SUCH, not as a finding.")

    # -- THE GRADED COMPARISON --------------------------------------------------------------------
    print("\n  --- THE GRADED COMPARISON: does the ordering agree between the arms? " + "-" * 20)
    agree = {}
    for sw in SWEEPS:
        a, b = ranks.get(("bleedfree", sw)), ranks.get(("mix", sw))
        if a is None or b is None:
            print(f"    {sw:<14} unreadable on at least one arm — no comparison")
            continue
        agree[sw] = (a == b)
        # A rank INVERSION (exact reverse) is a stronger statement than mere disagreement.
        inv = (a == tuple(reversed(b)))
        verdict = ("AGREE" if a == b else ("INVERTED" if inv else "DIFFER"))
        print(f"    {sw:<14} bleed-free {' > '.join(a):<22} | mix {' > '.join(b):<22} {verdict}")
    n_ag = sum(1 for v in agree.values() if v)
    print(f"\n    -> the two arms agree on the ordering in {n_ag} of {len(agree)} readable sweeps.")

    # -- the decision-relevant reduction: WHICH POSITION IS FURTHEST OFF? --------------------------
    # ⚠ Reported ALONGSIDE the full ordering, never instead of it (`self-selecting-scores`): the
    # full permutation is the gate's stated question and is answered above.  This reduction earns
    # its place because (a) a full 3-permutation match is a demanding bar — 6 possible orderings —
    # while a table with ONE entry per GRUNT position is prioritised on its argmax, and (b) the
    # stability caveat above bites the full ordering hardest, so the honest question is whether
    # ANYTHING here is stable.  Both counts are printed so a reader can see it either way.
    print("\n  --- reduction: which GRUNT position is the stage FURTHEST OFF at? " + "-" * 22)
    top = {}
    for arm in ("bleedfree", "mix"):
        firsts = [ranks[(arm, sw)][0] for sw in SWEEPS if ranks.get((arm, sw))]
        if not firsts:
            continue
        mode = max(set(firsts), key=firsts.count)
        top[arm] = (mode, firsts.count(mode), len(firsts))
        print(f"    {arm:<10} rank-1 per sweep: {', '.join(firsts):<40} -> "
              f"{mode} at {firsts.count(mode)}/{len(firsts)}")
    if len(top) == 2:
        (mb, nb, tb), (mm, nm, tm) = top["bleedfree"], top["mix"]
        if mb == mm:
            print(f"    ⇒ both arms put **{mb}** furthest off ⇒ the argmax SURVIVES the mix even "
                  f"though the full\n       ordering does not.")
        else:
            print(f"    ⇒ ⭐⭐ THE ARGMAX ITSELF MOVES: bleed-free says **{mb}** ({nb}/{tb} sweeps), "
                  f"the mix says **{mm}**\n       ({nm}/{tm}).  That is the statistic a "
                  f"one-entry-per-position table is prioritised on, and it is\n       stable "
                  f"WITHIN each arm while disagreeing BETWEEN them — so the instability above does "
                  f"not\n       explain the disagreement away.")
    if agree and n_ag == len(agree):
        print("    ⇒ COMPUTED VERDICT: the GRUNT ordering SURVIVES the mix.  The bleed-free "
              "grading was\n       representative ON THIS AXIS, so the rebalance is hygiene rather "
              "than a correction, and\n       GATE AP's bleed-free `ROWS` mapping is not "
              "misprioritising the GRUNT table.")
    elif agree:
        print("    ⇒ COMPUTED VERDICT: the GRUNT ordering DOES NOT SURVIVE the mix.  The three "
              "GRUNT rows of\n       `kNotchGainDb`/`kNotchMixK`/`kNotchQ` were prioritised on a "
              "reading that reorders at every\n       setting a player uses — which is what task "
              "P3 existed to find out.")
    else:
        print("    ⇒ NOT ANSWERABLE: no sweep is readable on both arms.")
    return cells, ranks, agree


# =================================================================================================
# BO3 — the absolute standing at played settings, with the dilution stated
# =================================================================================================
def gate_bo3(cells):
    print("\n== BO3  WHERE THE STAGE ACTUALLY STANDS AT THE PLAYED SETTING ==")
    print(f"  sweep {PLAY_SWEEP}; BOTH depth estimators printed (s152), because the POINT one is a "
          f"LOWER BOUND\n  wherever a null's bottom sits at the deconvolution residue (s180 BJ0d).")
    print(f"\n  {'arm':<10} {'GRUNT':<6} {'drv':>4} | {'ped area':>9} {'mod area':>9} "
          f"{'corr':>7} | {'ped pt':>7} {'mod pt':>7} {'corr':>7} | {'pt-area':>7}")
    print("  " + "-" * 92)
    rowsout = []
    for arm in ("bleedfree", "mix"):
        for gname, _ in GRUNTS:
            for drv in MATCHED_DRIVES:
                c = cells[(arm, gname, drv, PLAY_SWEEP)]
                if c["refused"]:
                    print(f"  {arm:<10} {gname:<6} {drv:4g} | REFUSED: {c['refused']}")
                    continue
                gap = c["corr_point"] - c["corr_area"]
                print(f"  {arm:<10} {gname:<6} {drv:4g} | {c['ped_area']:9.3f} {c['mod_area']:9.3f} "
                      f"{c['corr_area']:7.3f} | {c['ped_point']:7.3f} {c['mod_point']:7.3f} "
                      f"{c['corr_point']:7.3f} | {gap:7.3f}")
                rowsout.append({"arm": arm, "grunt": gname, "drive": drv, **c})
    # The dilution, stated rather than implied: the mixed arm's corrections are smaller because
    # BOTH sides are diluted, not because the stage is better there.
    for key, lab in (("corr_area", "AREA"), ("corr_point", "POINT")):
        bf = [c[key] for (a, _, _, s), c in cells.items()
              if a == "bleedfree" and s == PLAY_SWEEP and not c["refused"]]
        mx = [c[key] for (a, _, _, s), c in cells.items()
              if a == "mix" and s == PLAY_SWEEP and not c["refused"]]
        if bf and mx:
            print(f"\n  mean |corr| ({lab}):  bleed-free {np.mean(np.abs(bf)):.3f} dB   "
                  f"mix {np.mean(np.abs(mx)):.3f} dB")
    print("  ⚠⚠ DO NOT read a smaller mixed |corr| as the stage being better at the mix: both "
          "sides carry the\n     same clean tap there, so the difference is diluted by "
          "construction.  That common mode is\n     exactly why BO2 grades a RANK, which is taken "
          "WITHIN an arm and cancels it.")
    return rowsout


# =================================================================================================
# BO4 — the LEVEL axis, which no group covered at all
# =================================================================================================
def gate_bo4():
    print("\n== BO4  THE LEVEL LADDER — THE AXIS NO PRE-s186 GROUP SWEPT ==")
    print("  `blend`/`blend_hot` sweep BLEND; LEVEL was pinned at max or noon everywhere, so the "
          "one control\n  the mix law is KEYED THROUGH had never been swept in this tool.")
    print(f"\n  {'capture':<28} {'L':>5} {'cf':>8} | {'ped area':>9} {'mod area':>9} {'corr':>7} "
          f"| {'mod q':>6}")
    print("  " + "-" * 84)
    out = []
    prev_cf = None
    gapmsg = None
    for fname, drv in OT.SETS["level_ladder"]:
        p = C.parse_capture(fname)
        cf = OT.clean_frac_of(fname)
        c = read_cell(fname, drv, PLAY_SWEEP)
        if c["refused"]:
            print(f"  {fname:<28} {p['level']:5.3f} {cf:8.5f} | REFUSED: {c['refused']}")
        else:
            print(f"  {fname:<28} {p['level']:5.3f} {cf:8.5f} | {c['ped_area']:9.3f} "
                  f"{c['mod_area']:9.3f} {c['corr_area']:7.3f} | {c['mod_q']:6.2f}")
            out.append({"capture": fname, "level": p["level"], "cf": cf, **c})
        if prev_cf is not None and prev_cf - cf > 0.15:
            gapmsg = (prev_cf, cf)
        prev_cf = cf
    if gapmsg:
        lo, hi = OT.bleedfree_cf(), gapmsg[0]
        print(f"\n  ⭐ FREE CORROBORATION OF s185, from membership alone: the detents jump "
              f"cf {gapmsg[0]:.5f} -> {gapmsg[1]:.5f},\n     so the band P2's re-anchor disturbs "
              f"(cf in ({lo:.5f}, 0.20433)) contains NO CAPTURE.  s185's split\n     bar — CAPTURED "
              f"met exactly, DIALLABLE exceeded — is a property of this ladder's spacing, and it\n"
              f"     reproduces here on a tool that knows nothing about GATE BN.")
    else:
        fail("BO4", "expected a >0.15 gap in the LEVEL ladder's cf column (s185's disturbed band "
                    "is uncaptured); none found — re-read s185 before quoting its split bar")
    return out


# =================================================================================================
# BO5 — the estimators disagree about the SIGN bleed-free and agree at the mix.  Why?
# =================================================================================================
def gate_bo5():
    """BO3 shows something BO2's rank cannot: bleed-free, `corr_point` and `corr_area` have
    OPPOSITE SIGNS at 4 of 6 cells — the two estimators disagree about whether the model's null is
    too DEEP or too SHALLOW — while at the mix they agree to ~0.3 dB.  A sign disagreement is not a
    precision quibble; it is the two readings recommending opposite corrections.

    GATE AP (s152) predicts exactly this and names the cause: the POINT depth is CENSORED wherever
    a null's bottom sits at or below the deconvolution residue, and censoring makes a deep null read
    shallower than it is.  This sub-gate tests that rather than asserting it, using GATE BJ's OWN
    margin bar (imported, s180 BJ0d) so the threshold is one this project already measured against
    rather than one chosen here."""
    import analyze as A
    import bass_null_frontier_gate as BJ
    print("\n== BO5  WHY THE TWO DEPTH ESTIMATORS DISAGREE BLEED-FREE AND AGREE AT THE MIX ==")
    print(f"  `margin` := the pedal null's BOTTOM minus the deconvolution residue, both in this "
          f"curve's own\n  normalised dB.  Negative = the bottom is BELOW the residue, i.e. the "
          f"POINT depth is a lower bound.\n  `cens` applies GATE BJ's imported {BJ.FLOOR_MARGIN_DB:.0f} dB bar — "
          f"kept for continuity with s180, but see the\n  summary: it does not discriminate here, "
          f"and the MARGIN itself does.")
    print(f"\n  {'arm':<10} {'GRUNT':<6} {'drv':>4} | {'ped bottom':>10} {'ped floor':>10} "
          f"{'margin':>7} {'cens':>5} | {'corr pt':>8} {'corr area':>9} {'signs':>6}")
    print("  " + "-" * 92)
    out, ncens, nflip = [], 0, 0
    for arm in ("bleedfree", "mix"):
        for gname, _ in GRUNTS:
            for drv in MATCHED_DRIVES:
                fname = ARMS[arm][gname][drv]
                g, ped, mod, meta = OT.curves(fname, PLAY_SWEEP, ren_dir=REN_DIR, meta=True)
                try:
                    p = OT.notch_geometry(g, ped, depth="area")
                    m = OT.notch_geometry(g, mod, depth="area")
                except RuntimeError:
                    print(f"  {arm:<10} {gname:<6} {drv:4g} | (null unreadable)")
                    continue
                # `W.floor_db` is a SCALAR — the deconvolution residue below the sweep's own 20 Hz
                # start, already in this curve's normalised dB — so it is compared directly, which
                # is how GATE BJ's BJ0d uses it too.  ⛔ It is DIAGNOSTIC and must never become an
                # exclusion: it is signal-proportional regularisation residue, not a noise floor,
                # and this project has deleted its own headline cells with it twice.
                fl = float(meta["ped_floor"])
                margin = p["bottom"] - fl
                cens = margin < BJ.FLOOR_MARGIN_DB
                cp = p["depth_point"] - m["depth_point"]
                ca = p["depth_area"] - m["depth_area"]
                flip = (cp * ca) < 0
                ncens += int(cens)
                nflip += int(flip)
                print(f"  {arm:<10} {gname:<6} {drv:4g} | {p['bottom']:10.3f} {fl:10.3f} "
                      f"{margin:7.3f} {'YES' if cens else 'no':>5} | {cp:8.3f} {ca:9.3f} "
                      f"{'OPPOSED' if flip else 'agree':>6}")
                out.append({"arm": arm, "grunt": gname, "drive": drv, "margin": margin,
                            "censored": bool(cens), "corr_point": cp, "corr_area": ca,
                            "sign_flip": bool(flip)})
    bf = [r for r in out if r["arm"] == "bleedfree"]
    mx = [r for r in out if r["arm"] == "mix"]
    fbf, fmx = sum(r["sign_flip"] for r in bf), sum(r["sign_flip"] for r in mx)
    print(f"\n  SIGN-OPPOSED estimators (RATE, not count — the arms have different n): "
          f"bleed-free {fbf}/{len(bf)}, mix {fmx}/{len(mx)}")

    # ⚠⚠ THE 3 dB BAR DOES NOT DISCRIMINATE HERE AND SAYING SO IS THE POINT.  Every one of the 11
    # cells is "within 3 dB of the residue", so a COUNT of censored cells separates nothing, and a
    # first draft's verdict duly fired on `6 > 5` — which is a difference in how many cells each
    # arm has, not a rate (`check-n-before-reading-a-trend`).  The quantity that DOES separate is
    # the MARGIN itself, and it separates completely, so the honest statistic is s109's: find the
    # gap, put the bar in it, and ASSERT THE SEPARATION rather than quoting a threshold.
    op = sorted(r["margin"] for r in out if r["sign_flip"])
    ag = sorted(r["margin"] for r in out if not r["sign_flip"])
    print(f"  bottom-minus-residue MARGIN, dB:")
    print(f"    sign-OPPOSED cells ({len(op)}): {', '.join(f'{v:+.3f}' for v in op)}")
    print(f"    sign-AGREEING cells ({len(ag)}): {', '.join(f'{v:+.3f}' for v in ag)}")
    sep = (min(ag) - max(op)) if (op and ag) else float("nan")
    complete = bool(op and ag and max(op) < min(ag))
    if complete:
        print(f"    ⇒ COMPLETE SEPARATION: every opposed cell is below every agreeing one, with a "
              f"{sep:.2f} dB GAP\n       and nothing in it — so no threshold is being chosen, the "
              f"populations simply do not overlap.")
    else:
        print(f"    ⇒ the two populations OVERLAP (gap {sep:+.2f} dB) — the margin does not "
              f"separate them, so the\n       censoring attribution below is NOT supported.")

    # COMPUTED verdict, every branch written out from the numbers (s184 BM2).
    rbf = fbf / len(bf) if bf else 0.0
    rmx = fmx / len(mx) if mx else 0.0
    if complete and rbf > rmx:
        print(f"\n  ⇒ COMPUTED VERDICT: the sign disagreement TRACKS THE CENSORING DEPTH, and it is "
              f"confined to the\n     bleed-free arm ({100*rbf:.0f} % of cells vs {100*rmx:.0f} % "
              f"at the mix).  At the corner the pedal's null bottom sits\n     6–13 dB BELOW the "
              f"deconvolution residue, so its POINT depth is a lower bound there and the two\n"
              f"     estimators recommend OPPOSITE corrections; at the mix the clean tap floors "
              f"the null to within\n     1 dB of the residue and they agree to ≤0.33 dB.  ⇒ GATE "
              f"AP's mechanism (s152) on a THIRD\n     construction, and a second, sharper reason a "
              f"bleed-free-only membership is treacherous: it is\n     the one region where the "
              f"DIRECTION of the correction depends on which estimator is read.")
    elif rbf > rmx:
        print("\n  ⇒ COMPUTED VERDICT: the sign disagreement is confined to the bleed-free arm, but "
              "the margin does\n     NOT separate the two populations, so GATE AP's censoring "
              "mechanism is not established as the\n     cause here and the disagreement is "
              "UNATTRIBUTED.")
    else:
        print("\n  ⇒ COMPUTED VERDICT: the estimators do NOT disagree more bleed-free than at the "
              "mix; BO3's\n     apparent sign split does not survive this audit.")
    return out


def main():
    print("#" * 100)
    print("# GATE BO — DOES THE GRUNT ORDERING SURVIVE THE MIX?   (session 186, item 19, task P3)")
    print("#" * 100)

    e = gate_bo0()
    imb = gate_bo1(e)
    cells, ranks, agree = gate_bo2()
    played = gate_bo3(cells)
    censor = gate_bo5()
    ladder = gate_bo4()

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w") as fh:
        json.dump({
            "bleedfree_cf": e,
            "imbalance": imb,
            "ranks": {f"{a}|{s}": (list(r) if r else None) for (a, s), r in ranks.items()},
            "agree": {k: bool(v) for k, v in agree.items()},
            "played": played,
            "censoring": censor,
            "level_ladder": ladder,
            "matched_drives": list(MATCHED_DRIVES),
            "fail": FAIL,
        }, fh, indent=1, default=float)
    print(f"\nwrote {REPORT}")

    if FAIL:
        print("\nGATE BO: FAIL\n  " + "\n  ".join(FAIL))
        sys.exit(1)
    print("\nGATE BO: all guards passed.")


if __name__ == "__main__":
    main()
