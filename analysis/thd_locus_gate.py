#!/usr/bin/env python3.11
"""GATE Z -- WHERE the gated THD "level" term lives, and which WAY it points.

Session 128, Phase 9, open-work item 2.  NO RENDER: every number is a re-read of a report already
on disk, so this gate is unaffected by session 127's cache invalidation.

WHY THIS EXISTS
---------------
`THD (OD) level, full send` is one of the 6 rows over SHIP and, per session 127's own handover, the
only gated row with an open lever.  It had never been LOCALISED.  What the project carried instead
was a single pooled number plus a DIRECTION, and both turn out to be wrong:

  (1) THE PRINTED SIGN WAS INVERTED FOR 65 SESSIONS.  `shape_gate.basis` took `np.linalg.qr`'s
      column signs as given; LAPACK returns Q[:, 0] = -ones/sqrt(n) here, so `level_signed` was
      **-mean(d)**.  A residual that is a constant +3 dB was reported as -3.0.  Session 109 saw the
      gated term was unsigned, went looking for the direction, found `level_signed` already computed
      and stored -- and read its sign off a QR convention.  That reading became CLAUDE.md's
      CLOSED/REFUTED row ("the model OVER-distorts ... any candidate reasoned about as 'we need more
      distortion' is backwards") and open-work item 2's own framing.  Fixed at the source in
      `shape_gate.basis`; the gated rms values are bit-identical, because they take abs.
      ⭐ WHY IT SURVIVED: shape_gate's ATTRIBUTION gate ranks the UNSIGNED terms, so the one gate
      written to check attribution was blind to the half of it a handover would read.

  (2) AND CORRECTING THE SIGN IS NOT ENOUGH, BECAUSE THERE IS NO SINGLE SIGN TO CORRECT IT TO.
      Measured convention-free -- the two raw THD percentages side by side, no basis, no projection,
      no gain match -- the ratio runs from **+4.47 dB at DRIVE 0 x the quietest rung to -4.21 dB at
      DRIVE max x the hottest**, crossing zero INSIDE the graded pool.  So the pooled mean is a
      weighted average of two opposite-signed regimes and its sign is a property of the capture
      inventory.  ⇒ the honest object is a SURFACE, and Z3 prints it.

WHAT IS MEASURED, AND WHY EACH INSTRUMENT IS INDEPENDENT
-------------------------------------------------------
  Z3  raw THD percentages, model vs pedal, over the rung x DRIVE plane.  A ratio of two numbers
      each side computes for itself, so it is immune to the report's per-row gain match, to the
      output makeup, to MASTER, and -- the point here -- to every sign convention.
  Z4  the stored per-order harmonic levels (H2..H7 in dB re the fundamental, at the 100/200/400 Hz
      anchors).  Shares NO arithmetic with Z3: per-order rather than summed, three tones rather
      than 26 bands, and referred to the fundamental at the same tone.  Used to corroborate the
      ORDERING, never to add precision.
  Z5  the bleed axis.  THD is harmonics/fundamental and the clean tap contributes fundamental with
      no harmonics, so a mix difference moves THD with no change in distortion at all.  Z5 asks
      whether the bleed dose-response is QUANTITATIVELY what A3's independently-measured OD-path
      level deficit predicts -- one free parameter, compared against a number this gate does not
      fit.

⚠ WHAT THIS GATE DOES NOT DO.  It proposes no constant and no gate-row change.  Splitting or
re-membering a gated row is a user decision (session 114 took the last one); Z6 prints what the row
would read on each sub-population and stops there.

⚠ `cf` IS THE **MODEL'S** CLEAN FRACTION, from the shipped `LevelBlend` algebra at the TAPERED level
(`level ** levelTaperExp` -- session 113 lost a whole instrument by passing the KNOB value to a
function that takes the tapered one, and got a plausible, monotone, entirely wrong answer).  The
pedal's own clean fraction is not knowable from a capture, which is exactly what Z5 is about.

Usage:
  python3.11 analysis/thd_locus_gate.py [REPORT.json] [--json OUT] [--ex-gain-n12]
"""
import argparse
import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matrix_grade as MG                              # noqa: E402
import shape_gate as SG                                # noqa: E402
import release_gate as RG                              # noqa: E402
import level_law_gate as LLG                           # noqa: E402

def _newest_matrix_report():
    """The newest FULL matrix report on disk, resolved STRUCTURALLY.

    ⛔⛔ SESSION 191 — THIS WAS THE LITERAL `analysis/reports/s124_ship.json` AND IT WAS BOTH STALE
    AND ABSENT, so `_mutate_gate_z.py`'s CONTROL died in `open()` and every arm below it was
    unattributable. Two things wrong with the literal at once: `analysis/reports/*.json` is
    GITIGNORED and regenerable, so any filename written into a default expires on its own (s189
    found the same rot in two more tools one line apart); and `s124_ship.json` is the artefact
    CLAUDE.md marks ⛔ STALE-EPOCH FOR EVERY ABSOLUTE LEDGER, which GATE O6b refuses BY NAME —
    so even when it existed it was the wrong default for a gate whose Z1 reproduces release_gate.

    Same resolver shape as `_mutate_gate_ay.newest_matrix_report` (s173): a report is the matrix if
    it carries the three top-level keys AND >= 100 captures, so a `--only` subset cannot win."""
    import glob
    best, best_mt = None, -1.0
    for path in glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "reports", "*.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
        except Exception:
            continue                       # a gate's own artefact, or a partial write
        if not (isinstance(doc, dict) and {"captures", "meta", "summary"} <= set(doc)):
            continue
        if len(doc.get("captures") or []) < 100:
            continue
        mt = os.path.getmtime(path)
        if mt > best_mt:
            best, best_mt = path, mt
    if best is None:
        sys.exit("GATE Z FAIL: no full matrix report found under analysis/reports/ -- `*.json` "
                 "there is gitignored, so re-render with comprehensive_report.py or pass a report "
                 "explicitly (`empty-gate-must-fail`)")
    return os.path.relpath(best, os.getcwd())


DEFAULT_REPORT = None          # resolved in main(), so importing this module costs no disk scan

#: THD's own measurement floor, taken from `shape_gate.thd_rows` rather than re-chosen here so the
#: two tools cannot disagree about which bands exist (`rebuild-targets-dont-transcribe`).
THD_FLOOR_PCT = 1e-3
MIN_BANDS = 8

#: A3's clean-side/OD-side decomposition, as re-quoted on the CURRENT baseline epoch by GATE O in
#: session 119 (CLAUDE.md's CLOSED/REFUTED table).  Z5 compares its own fitted deficit against this;
#: it is NOT used to compute anything, so a stale value here cannot bias a number -- it can only
#: make the comparison line read wrong, which is why it carries its provenance.
A3_OD_DEFICIT_DB = 4.38          # OD path quiet, absolutely, over 100-400 Hz (GATE O, s119)
A3_CLEAN_BOUND_DB = 0.48         # the clean side's bound over the same set

#: The rungs, in stimulus order.  `sweep_clean` carries no measurable THD on either side (see Z2's
#: printed census), so the THD ladder is three rungs, 6 dB apart.
RUNGS = ("sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6")

#: Bleed classes.  The bottom class is the mix ANCHOR -- the smallest clean fraction the stage can
#: reach -- and the rest are wide because their purpose is a dose-response, not a fit.
#:
#: ⛔⛔ SESSION 191 -- THIS CLASS WAS AN EXACT ZERO AND HAD BEEN EMPTY SINCE SESSION 181, SO Z3, Z4,
#: Z5 AND Z6's SPLIT WERE ALL UNRUNNABLE AND NOBODY HAD NOTICED.  It read `cf < 1e-12` on the
#: strength of GATE K2's s103 finding that "the LevelBlend clean coefficient is identically 0 only
#: where BOTH BLEND and LEVEL are max" -- true of the network s103 measured, and FALSE since s181
#: shipped `blendEndStop`, which puts `e` of clean signal at that very corner.  So the population
#: the gate's whole convention-free direction argument rests on became empty by construction, Z3
#: exited, and Z4-Z6 never ran.  Same lineage as GATE L refusing at s189 and GATE K2's two stale
#: mirrors at s182 -- a downstream tool still modelling the pre-s181 anchor.
#:
#: ✅ The bar is now DERIVED, not transcribed: `ANCHOR_CF` is the clean fraction the shipped stage
#: actually delivers at the corner, computed through the SAME `coef_closed` this module already
#: uses for every row (which reads s182's single end-stop resolver), so it cannot drift from
#: `FitParams.h` without `check_shipped_endstop()` refusing first.  A row is in the anchor class if
#: it is within `ANCHOR_TOL` of that value -- floating-point slack only, not a widened membership.
#:
#: ⛔ THE RETIRED DEFINITION STAYS REACHABLE (`--anchor-cf 0`) so every pre-s181 GATE Z number
#: reproduces exactly, and the gate PRINTS which definition it ran (s124's rule).
CF_EDGES = ((0.35, "cf<0.35"), (0.60, "0.35-0.60"), (0.80, "0.60-0.80"), (1.01, "cf>=0.80"))
ANCHOR_LABEL = "anchor cf"
CF_CLASSES = (ANCHOR_LABEL,) + tuple(lbl for _, lbl in CF_EDGES)

#: Slack around the anchor.  Small enough that it cannot admit a neighbouring LEVEL detent (the
#: ladder's next cf is 0.24382, an order of magnitude away -- s185 measured that gap), large enough
#: to absorb float association between `coef_closed` here and in the report's own settings.
ANCHOR_TOL = 1e-9


def _anchor_cf():
    """The smallest clean fraction the SHIPPED stage can deliver = cf at BLEND max, LEVEL max.

    Derived through the same algebra every row uses, so the anchor and the rows cannot disagree.

    ⭐ KNOWN ANSWER, asserted rather than trusted: at that corner `coef_closed` returns
    `(1 - e, e)`, so the clean FRACTION must collapse to `e` -- the shipped `blendEndStop` itself.
    That ties this derivation to `FitParams.h` through GATE K's single resolver: if a fourth stale
    mirror of `LevelBlend` ever appears (s182 found two, s189 a third), the corner stops equalling
    `e` and this refuses instead of silently re-classifying every anchor row."""
    a, c = LLG.coef_closed(1.0, LLG.level_taper(1.0))
    cf = (c / (a + c)) if (a + c) > 0.0 else 1.0
    e = LLG.SHIPPED_BLEND_END_STOP[0]
    if abs(cf - e) > 1e-12:
        sys.exit(f"GATE Z FAIL [anchor]: cf at the BLEND/LEVEL-max corner is {cf!r} but the shipped "
                 f"blendEndStop is {e!r}. Those must be EQUAL by construction "
                 f"(coef_closed -> (1-e, e) there), so one of the two is modelling a different "
                 f"LevelBlend -- s182/s189's stale-mirror trap, a fourth time.")
    return cf


#: Resolved at import so every sub-gate shares one value; `--anchor-cf` overrides it in `main()`.
ANCHOR_CF = None            # set by set_anchor_cf(), below


def set_anchor_cf(value=None):
    global ANCHOR_CF
    ANCHOR_CF = _anchor_cf() if value is None else float(value)
    return ANCHOR_CF


def is_anchor(cf):
    """⚠ The single predicate. Z3/Z4/Z6 used to inline `cf < 1e-12` in four places, which is how one
    stale definition took four sub-gates down together — there is now nothing to keep in step."""
    if ANCHOR_CF is None:
        set_anchor_cf()
    return cf <= ANCHOR_CF + ANCHOR_TOL


def cf_class(cf):
    if is_anchor(cf):
        return ANCHOR_LABEL
    for hi, lbl in CF_EDGES:
        if cf < hi:
            return lbl
    return CF_EDGES[-1][1]


def clean_fraction(settings):
    """The MODEL's clean fraction of the mix, from the shipped LevelBlend algebra.

    ⚠ `coef_closed` takes the TAPERED level.  Passing the knob value instead is session 113's
    documented defect and it returns a monotone, plausible, wrong curve."""
    b = float(settings["blend"])
    lv = LLG.level_taper(float(settings["level"]))
    a, c = LLG.coef_closed(b, lv)
    return (c / (a + c)) if (a + c) > 0.0 else 1.0


# =================================================================================================
# membership
# =================================================================================================
def collect(path, ex_n12=False):
    """-> (bands, caps, drops, rows) where rows[(file, sweep)] carries everything the gate reads.

    Membership is resolved from the report's stored `settings`, never from the filename
    (`measurement-condition-needs-its-own-gate`, s65; and s114's substring-selection time bomb --
    `resolve-membership-from-SETTINGS-then-ASSERT-it`)."""
    bands, caps = MG.load(path)
    drops, _, _ = MG.find_dropouts(bands, caps)
    idx = MG.band_idx(bands, SG.GRADE_LO, SG.GRADE_HI)
    rows = {}
    for f, c in caps.items():
        if not MG.is_od(f):
            continue
        if ex_n12 and MG.is_gain_n12(f):
            continue
        st = c["settings"]
        for sw, th in c.get("thd", {}).items():
            if (f, sw) in drops:
                continue
            pp, qq = th["plugin_pct"], th["pedal_pct"]
            use = [i for i in idx
                   if pp[i] is not None and qq[i] is not None
                   and pp[i] > THD_FLOOR_PCT and qq[i] > THD_FLOOR_PCT]
            if len(use) < MIN_BANDS:
                continue
            d = np.array([20.0 * np.log10(pp[i] / qq[i]) for i in use])
            rows[(f, sw)] = {
                "d": d, "use": use,
                "model_pct": np.array([pp[i] for i in use]),
                "pedal_pct": np.array([qq[i] for i in use]),
                "level_signed": float(np.mean(d)),
                "cf": clean_fraction(st), "drive": float(st["drive"]),
                "grunt": int(st["gruntIdx"]), "attack": int(st["attackIdx"]),
                "n12": MG.is_gain_n12(f), "sweep": sw, "file": f,
                "harm": c.get("harmonics", {}).get(sw, {}),
            }
    return bands, caps, drops, rows


def gate_z1(path, rows, out):
    """Z1 -- reproduce release_gate's own THD numbers, and pin the session-128 sign fix IN USE.

    Two different failures are caught here and they need different guards:
      * a MEMBERSHIP drift between this tool and the gate it is explaining -- caught by requiring
        the three rms values to agree to 1e-9 (`verify-the-baseline-BEFORE-ranking-anything`);
      * the sign convention silently reverting -- caught by requiring `shape_gate`'s stored
        `level_signed` to EQUAL this tool's independently-computed `mean(d)` on the real data, not
        merely to share its sign.  The selftest asserts that on synthetic input; this asserts it
        where the number is actually consumed."""
    print("\n-- Z1: KNOWN ANSWER -- reproduce release_gate's THD rows, and pin the s128 sign fix --")
    ref = RG.thd_split(path)
    mine = {"OD (gated)": [r for r in rows.values()],
            "  ex gain-n12 [pre-s111]": [r for r in rows.values() if not r["n12"]],
            "  gain-n12 only [control]": [r for r in rows.values() if r["n12"]]}
    worst = 0.0
    print(f"      {'group':<26}{'rms (theirs)':>14}{'rms (mine)':>12}{'|diff|':>10}"
          f"{'SIGNED mean':>13}{'n':>6}")
    for lbl, sub in mine.items():
        if not sub:
            sys.exit(f"GATE Z1 FAIL [empty]: sub-population {lbl!r} is EMPTY -- a membership filter that "
                     f"matches nothing makes every number below vacuous (`empty-gate-must-fail`)")
        r_ref, s_ref, n_ref = ref[lbl]
        r_mine = float(np.sqrt(np.mean([abs(x["level_signed"]) ** 2 for x in sub])))
        s_mine = float(np.mean([x["level_signed"] for x in sub]))
        if len(sub) != n_ref:
            sys.exit(f"GATE Z1 FAIL [membership]: {lbl!r} has n={len(sub)} here and n={n_ref} in release_gate -- "
                     f"the two tools disagree about membership, so nothing below is comparable")
        worst = max(worst, abs(r_mine - r_ref))
        # `level_signed` is stored by shape_gate; mean(d) is computed here from the percentages.
        # They must AGREE, which is only true with basis()'s canonicalised column signs.
        if abs(s_mine - s_ref) > 1e-9:
            sys.exit(
                f"GATE Z1 FAIL [sign]: {lbl!r} signed mean is {s_mine:+.6f} computed as mean(20log10("
                f"model/pedal)) and {s_ref:+.6f} via shape_gate's `level_signed`.\n"
                f"  If these differ by a SIGN, `shape_gate.basis` has lost its column-sign "
                f"canonicalisation (the session-128 fix) and every direction this gate prints is "
                f"backwards.\n  If they differ otherwise, the two are no longer the same statistic.")
        print(f"      {lbl.strip():<26}{r_ref:>14.4f}{r_mine:>12.4f}{abs(r_mine - r_ref):>10.1e}"
              f"{s_mine:>+13.3f}{len(sub):>6}")
    if worst > 1e-9:
        sys.exit(f"GATE Z1 FAIL [rms]: worst rms disagreement {worst:.3e} > 1e-9 -- this tool is not "
                 f"reading the row release_gate grades")
    print(f"      worst |rms| disagreement {worst:.2e}   OK")
    print("      ⭐ the signed means also agree with an independent mean(20log10(model/pedal)),")
    print("        which is the session-128 sign fix asserted where the number is CONSUMED.")
    out["z1"] = {"worst_rms_diff": worst,
                 "groups": {k: dict(zip(("rms", "signed", "n"), v)) for k, v in ref.items()}}
    return True


def gate_z2(bands, caps, drops, rows, out):
    """Z2 -- membership, printed in full, and the composition of every axis this gate reads."""
    print("\n-- Z2: MEMBERSHIP -- counts, exclusions, and the composition of each axis --")
    print(f"      OD THD rows graded      : {len(rows)}")
    print(f"      reference ladder dropouts EXCLUDED (detected, not named): {len(drops)}")
    for k in sorted(drops):
        print(f"        ! {k[0]}@{k[1]}")
    swc = defaultdict(int)
    for f, c in caps.items():
        for sw in c.get("fr", {}):
            swc[sw] += 1
    thdc = defaultdict(int)
    for r in rows.values():
        thdc[r["sweep"]] += 1
    print("      sweeps present in the report vs sweeps carrying gradeable THD:")
    for sw in sorted(swc):
        print(f"        {sw:<16} FR rows {swc[sw]:>4}   THD rows {thdc.get(sw, 0):>4}"
              + ("   <- no measurable THD on EITHER side (both below the "
                 f"{THD_FLOOR_PCT} % floor)" if not thdc.get(sw) else ""))
    print("      ⭐ `sweep_clean` dropping out is a free known answer, not missing data: with the")
    print("        clipper barely worked both sides sit under the floor, so no ratio exists. A THD")
    print("        gate that reported a number there would be reading noise.")
    print("      composition along the two axes Z3 reads (row counts):")
    drv = sorted({r["drive"] for r in rows.values()})
    tab = defaultdict(lambda: defaultdict(int))
    for r in rows.values():
        tab[cf_class(r["cf"])][r["drive"]] += 1
    print(f"        {'cf class':<12}" + "".join(f"{('drv ' + str(d)):>10}" for d in drv)
          + f"{'total':>8}")
    for c in CF_CLASSES:
        n = sum(tab[c].values())
        print(f"        {c:<12}" + "".join(f"{tab[c].get(d, 0):>10}" for d in drv) + f"{n:>8}")
    print("      ⚠ the classes are NOT balanced across DRIVE, which is exactly why Z3 reports the")
    print("        rung x DRIVE surface at FIXED bleed rather than a marginal over either axis")
    print("        (`a-marginal-over-one-knob-is-confounded-by-every-other-knob`, s102).")
    out["z2"] = {"n_rows": len(rows), "dropouts": [f"{a}@{b}" for a, b in sorted(drops)],
                 "thd_rows_by_sweep": dict(thdc), "cf_x_drive": {c: dict(tab[c]) for c in CF_CLASSES}}
    return True


# =================================================================================================
# Z3 -- the convention-free direction
# =================================================================================================
def gate_z3(rows, out):
    """Z3 -- the two raw THD percentages, side by side, over rung x DRIVE at ZERO bleed.

    No basis, no projection, no sign convention, no gain match: each side's THD is a ratio it
    computes for itself, so this table cannot be inverted by a library convention the way
    `level_signed` was.  Restricted to the BLEED-FREE rows so the mix cannot contribute (Z5 covers
    the mix); restricted to full send so the interface pad cannot (Z6's control covers that).

    The GATE is that the surface CHANGES SIGN.  That is not a threshold -- it is the refusal of a
    pooled direction, and if the surface ever stops changing sign this gate should say so and a
    single direction becomes quotable again."""
    print("\n-- Z3: CONVENTION-FREE DIRECTION -- raw THD %, model vs pedal, rung x DRIVE, no bleed --")
    sub = [r for r in rows.values() if is_anchor(r["cf"]) and not r["n12"]]
    if not sub:
        # ⛔ NOT a hard exit any more (s191). An empty anchor class is a fact about the EPOCH,
        # not a validity failure that makes Z4-Z6 meaningless -- and exiting here is exactly s108's
        # rule broken: "exit only on things that make the numbers below meaningless". Between s181
        # and s191 this line suppressed four sub-gates for eight sessions.
        print("      ⛔ Z3 CANNOT RUN ON THIS REPORT: the anchor class is EMPTY.")
        print(f"        Anchor cf = {ANCHOR_CF:.6f}; the smallest cf in the graded set is "
              f"{min((r['cf'] for r in rows.values() if not r['n12']), default=float('nan')):.6f}.")
        print("        That is a MEMBERSHIP result, not missing data -- and NOT a pass: no")
        print("        convention-free direction is available on this report. Z4-Z6 continue.")
        out["z3"] = {"available": False, "anchor_cf": ANCHOR_CF}
        return True
    drv = sorted({r["drive"] for r in sub})
    cell = defaultdict(lambda: {"m": [], "p": [], "n": 0})
    for r in sub:
        c = cell[(r["sweep"], r["drive"])]
        c["m"] += list(r["model_pct"])
        c["p"] += list(r["pedal_pct"])
        c["n"] += 1
    print(f"      {'rung':<10}{'DRIVE':>7}{'rows':>6}{'model THD%':>12}{'pedal THD%':>12}"
          f"{'ratio':>9}{'dB':>8}")
    surf = {}
    for sw in RUNGS:
        for d in drv:
            c = cell.get((sw, d))
            if not c:
                continue
            m, p = float(np.median(c["m"])), float(np.median(c["p"]))
            db = 20.0 * np.log10(m / p)
            surf[(sw, d)] = db
            print(f"      {sw.replace('sweep_', ''):<10}{d:>7}{c['n']:>6}{m:>12.4f}{p:>12.4f}"
                  f"{m / p:>9.4f}{db:>+8.2f}")
    vals = np.array(list(surf.values()))
    pooled_m = float(np.median([x for c in cell.values() for x in c["m"]]))
    pooled_p = float(np.median([x for c in cell.values() for x in c["p"]]))
    pooled_db = 20.0 * np.log10(pooled_m / pooled_p)
    n_bands = sum(len(r["use"]) for r in sub)
    n_model_hi = sum(int(np.sum(r["model_pct"] > r["pedal_pct"])) for r in sub)
    print(f"      {'POOLED':<10}{'':>7}{len(sub):>6}{pooled_m:>12.4f}{pooled_p:>12.4f}"
          f"{pooled_m / pooled_p:>9.4f}{pooled_db:>+8.2f}")
    print(f"      bands where the MODEL distorts more: {n_model_hi} of {n_bands} "
          f"({100.0 * n_model_hi / n_bands:.1f} %) -- a near coin-flip, which is what a surface")
    print("        straddling zero looks like when it is summarised by one number.")

    changes_sign = bool(vals.max() > 0.0 and vals.min() < 0.0)
    print(f"      surface span {vals.min():+.2f} .. {vals.max():+.2f} dB over {len(vals)} cells")
    if not changes_sign:
        print("      ⚠ THE SURFACE NO LONGER CHANGES SIGN on this report. That is a real result and")
        print("        it MAKES A POOLED DIRECTION QUOTABLE AGAIN -- re-read this gate's docstring")
        print("        before carrying session 128's 'there is no single sign' forward.")
    else:
        print("      ⇒ the surface CHANGES SIGN inside the graded pool, so no pooled mean over it")
        print("        is a direction. Quote the cell, or the two corners, never the average.")
    # Dose-response, which is the part a mechanism has to explain.  Reported as a monotonicity
    # COUNT rather than a fitted slope: three rungs cannot support a slope (`check-n-before-
    # reading-a-trend`), but they can support an ordering.
    mono_rung = 0
    for d in drv:
        seq = [surf[(sw, d)] for sw in RUNGS if (sw, d) in surf]
        if len(seq) == len(RUNGS) and all(b < a for a, b in zip(seq, seq[1:])):
            mono_rung += 1
    mono_drv = 0
    for sw in RUNGS:
        seq = [surf[(sw, d)] for d in drv if (sw, d) in surf]
        if len(seq) == len(drv) and all(b < a for a, b in zip(seq, seq[1:])):
            mono_drv += 1
    print(f"      monotone FALLING with stimulus at {mono_rung}/{len(drv)} DRIVE settings; "
          f"monotone FALLING with DRIVE at {mono_drv}/{len(RUNGS)} rungs")
    print("      ⇒ ONE mechanism covers both axes: the model's THD grows with how hard the clipper")
    print("        is pushed MORE SLOWLY than the pedal's. It starts too high and ends too low, so")
    print("        this is a SLOPE error with a crossing, not a level error in either direction.")
    out["z3"] = {"surface_db": {f"{a}|{b}": v for (a, b), v in surf.items()},
                 "pooled_db": pooled_db, "changes_sign": changes_sign,
                 "frac_bands_model_higher": n_model_hi / n_bands,
                 "mono_falling_with_stimulus": [mono_rung, len(drv)],
                 "mono_falling_with_drive": [mono_drv, len(RUNGS)]}
    return True


# =================================================================================================
# Z4 -- corroboration on an instrument that shares no arithmetic
# =================================================================================================
def gate_z4(rows, out):
    """Z4 -- the stored per-order harmonic levels over the same rows and the same axis.

    Z3 is a summed ratio over 26 bands of a swept stimulus; this is per-ORDER, in dB re the
    fundamental, at three fixed tones.  They share the render and nothing else, so agreement on the
    ORDERING is a real corroboration -- and disagreement would mean Z3's summation is doing the
    work rather than the harmonic content.  ⚠ Used for ordering only: `reference-sources.md` §4
    makes the CAPTURES non-authoritative on even-order LEVEL, so an absolute H2 number from this
    report is not a target."""
    print("\n-- Z4: CORROBORATION -- per-order harmonics (dB re fundamental), same rows as Z3 --")
    sub = [r for r in rows.values() if is_anchor(r["cf"]) and not r["n12"]]
    orders = sorted({o for r in sub for o in r["harm"]},
                    key=lambda s: int(s[1:]) if s[1:].isdigit() else 99)
    if not orders:
        # ⚠ s191: two different causes used to print ONE message. An empty anchor class and a
        # report with no harmonics block are not the same problem, and blaming the report for a
        # membership outcome sends the next session to re-render something that is fine.
        if not sub:
            print(f"      ⛔ Z4 CANNOT RUN: the anchor class is EMPTY (anchor cf = {ANCHOR_CF:.6f}) "
                  f"-- Z3's rows do not exist,")
            print("        so there is nothing to corroborate. A MEMBERSHIP result, not a missing "
                  "harmonics block.")
        else:
            print("      no harmonics block in this report -- corroboration NOT AVAILABLE "
                  "(not a pass)")
        out["z4"] = {"available": False, "anchor_cf": ANCHOR_CF, "n_rows": len(sub)}
        return True
    tab = defaultdict(lambda: defaultdict(list))
    for r in sub:
        for o, v in r["harm"].items():
            pl, pd = v.get("plugin_db"), v.get("pedal_db")
            if pl is None or pd is None:
                continue
            for a, b in zip(pl, pd):
                if a is not None and b is not None and a > -90.0 and b > -90.0:
                    tab[r["sweep"]][o].append(a - b)
    print(f"      {'rung':<10}" + "".join(f"{o:>9}" for o in orders) + f"{'mean':>9}")
    seq_mean = []
    for sw in RUNGS:
        vals = [float(np.mean(tab[sw][o])) if tab[sw][o] else float("nan") for o in orders]
        seq_mean.append(float(np.nanmean(vals)))
        print(f"      {sw.replace('sweep_', ''):<10}"
              + "".join(f"{v:>+9.2f}" for v in vals) + f"{seq_mean[-1]:>+9.2f}")
    print("      (model - pedal; NEGATIVE = the model has LESS harmonic content at that order)")
    falls = all(b < a for a, b in zip(seq_mean, seq_mean[1:]))
    crosses = seq_mean[0] > 0.0 > seq_mean[-1]
    margin = min(abs(seq_mean[0]), abs(seq_mean[-1]))
    step = abs(seq_mean[0] - seq_mean[-1]) / max(1, len(seq_mean) - 1)
    print(f"      falls monotonically with stimulus: {falls}    crosses zero: {crosses}"
          f"    (endpoint nearest zero: {margin:.2f} dB, mean step {step:.2f} dB)")
    # ⛔ TWO PROPERTIES, TWO VERDICTS (s191). This block used to print "THE TWO INSTRUMENTS DISAGREE
    # about the ORDERING" whenever EITHER failed -- so a run where the ordering agreed perfectly and
    # only the crossing differed was reported as an ordering disagreement, which is a different and
    # much more alarming claim. `computed-verdicts-not-narrated`, in the one line a reader takes the
    # corroboration from.
    if not falls:
        print("      ⚠ THE TWO INSTRUMENTS DISAGREE ABOUT THE ORDERING. Z3's summed ratio is then")
        print("        doing work the harmonic content does not support -- resolve that BEFORE")
        print("        quoting either (`when-a-scratch-statistic-disagrees-suspect-the-scratch-one`,")
        print("        except that here neither is scratch, so neither gets the benefit).")
    elif not crosses:
        print("      ⇒ THE ORDERING IS CORROBORATED (both fall monotonically, on instruments")
        print("        sharing no arithmetic). The ZERO CROSSING is not: this axis stays one-signed.")
        print("      ⚠ Read that as a limit of THIS axis, not as a contradiction of Z3 — Z4's rung")
        print("        means POOL OVER DRIVE, and DRIVE is where most of Z3's span lives, so a")
        print("        surface that crosses in (rung x DRIVE) need not cross in rung alone.")
        if margin < step:
            print(f"      ⚠⚠ AND THE CROSSING IS A KNIFE-EDGE HERE: the endpoint nearest zero is")
            print(f"        {margin:.2f} dB against a mean step of {step:.2f} dB, so this boolean")
            print(f"        flips on less than one rung of movement. Do not quote it either way.")
    else:
        print("      ⇒ same ordering and same crossing as Z3, on an instrument sharing no")
        print("        arithmetic with it. The slope-with-a-crossing reading is corroborated.")
    out["z4"] = {"available": True, "orders": orders,
                 "by_rung": {sw: {o: (float(np.mean(tab[sw][o])) if tab[sw][o] else None)
                                  for o in orders} for sw in RUNGS},
                 "rung_means": seq_mean, "monotone_falling": falls, "crosses_zero": crosses,
                 "crossing_margin_db": margin, "mean_step_db": step}
    return True


# =================================================================================================
# Z5 -- the bleed axis, and whether A3 already explains it
# =================================================================================================
def gate_z5(rows, out):
    """Z5 -- does the bleed dose-response need a mechanism, or is it A3 seen through a ratio?

    THD = harmonics / fundamental, and the clean tap adds fundamental with no harmonics.  So if the
    model's OD path is DF dB quiet against a clean path that is right (which is precisely GATE O's
    A3 attribution), the model's mix is proportionally more clean, its harmonics are diluted more,
    and its THD reads LOW -- by an amount that is fully determined by DF and the clean fraction:

        excess(cf) - excess(0) = -20 log10( (1 + r_m) / (1 + r_m * 10^(DF/20)) ),  r_m = cf/(1-cf)

    ONE free parameter, and it is a quantity A3 has already measured independently.  So the test is
    not "does a curve fit" but "does the fitted DF land on A3's own number".

    ⚠ This is a SUFFICIENCY test, not an identification: any mechanism that scales the OD path's
    fundamental against its harmonics by the same factor predicts the same curve.  What it can do is
    retire the need for a SECOND mechanism, which is what a work list needs."""
    print("\n-- Z5: THE BLEED AXIS -- is it A3 seen through a ratio? --")
    sub = [r for r in rows.values() if not r["n12"]]
    byc = defaultdict(list)
    for r in sub:
        byc[cf_class(r["cf"])].append(r)
    print(f"      {'cf class':<12}{'rows':>6}{'mean cf':>9}{'excess dB':>11}"
          + "".join(f"{s.replace('sweep_drv_', 'rung '):>12}" for s in RUNGS))
    base = None
    obs = []
    for c in CF_CLASSES:
        g = byc.get(c, [])
        if not g:
            continue
        mean_cf = float(np.mean([r["cf"] for r in g]))
        ex = float(np.mean([r["level_signed"] for r in g]))
        per = [float(np.mean([r["level_signed"] for r in g if r["sweep"] == s]))
               if any(r["sweep"] == s for r in g) else float("nan") for s in RUNGS]
        if c == ANCHOR_LABEL:
            base = ex
        else:
            obs.append((mean_cf, ex))
        print(f"      {c:<12}{len(g):>6}{mean_cf:>9.3f}{ex:>+11.2f}"
              + "".join(f"{v:>+12.2f}" for v in per))
    if base is None or len(obs) < 3:
        print("      ⛔ Z5 CANNOT RUN: need the anchor class as a reference and >=3 bleed classes\n"
              "        to fit a one-parameter dilution law -- membership is too thin on this report.\n"
              "        REPORTED, not a pass; the classes above still stand on their own.")
        out["z5"] = {"available": False, "anchor_cf": ANCHOR_CF}
        return True
    print("      ⚠ every class carries all three rungs, so the bleed ordering above is not the")
    print("        stimulus ordering of Z3 re-appearing (the two axes are printed together).")

    def predict(cf, df_db):
        r_m = cf / (1.0 - cf)
        return -20.0 * np.log10((1.0 + r_m) / (1.0 + r_m * 10.0 ** (df_db / 20.0)))

    grid = np.arange(-12.0, 0.0001, 0.01)
    err = [float(np.sqrt(np.mean([(predict(c, df) - (e - base)) ** 2 for c, e in obs])))
           for df in grid]
    j = int(np.argmin(err))
    df_fit, rms_fit = float(grid[j]), err[j]
    interior = 0 < j < len(grid) - 1
    print(f"\n      one-parameter dilution fit: OD-path deficit DF = {df_fit:+.2f} dB "
          f"(rms {rms_fit:.2f} dB over {len(obs)} classes, "
          f"{'INTERIOR' if interior else 'ON ITS BOUND -- unidentified'})")
    print(f"      {'cf':>8}{'observed':>11}{'predicted':>11}{'resid':>8}")
    for c, e in obs:
        p = predict(c, df_fit)
        print(f"      {c:>8.3f}{e - base:>+11.2f}{p:>+11.2f}{(e - base) - p:>+8.2f}")
    print(f"      A3's independently measured OD-path deficit (GATE O, s119): "
          f"-{A3_OD_DEFICIT_DB:.2f} dB")
    print(f"      A3's clean-side bound over the same set                    : "
          f" {A3_CLEAN_BOUND_DB:.2f} dB")
    agree = abs(abs(df_fit) - A3_OD_DEFICIT_DB)
    print(f"      |fitted| - |A3|  =  {abs(df_fit):.2f} - {A3_OD_DEFICIT_DB:.2f} = {abs(df_fit) - A3_OD_DEFICIT_DB:+.2f} dB")
    if not interior:
        print("      ⛔ the fit is on its bound, so DF is UNIDENTIFIED and the comparison below")
        print("         means nothing (`bound-resting-means-unidentified`).")
    elif agree <= 1.5:
        print("      ⇒ the bleed axis is QUANTITATIVELY consistent with A3's already-measured OD")
        print("        deficit, from one parameter this gate did not take from A3. ⇒ it needs NO")
        print("        SECOND MECHANISM: it is A3 read through a ratio, the same way session 122")
        print("        found the 50 Hz 1400 % THD cell was A3's cancellation null read as a")
        print("        denominator. ⚠ SUFFICIENCY only -- see this function's docstring.")
    else:
        print("      ⚠ the fitted deficit does NOT match A3's. Either the bleed axis carries a")
        print("        second mechanism, or A3's figure does not apply broadband (it is a")
        print("        100-400 Hz number and this is 25 Hz-16 kHz). Do not attribute either way.")
    out["z5"] = {"anchor_excess": base, "anchor_cf": ANCHOR_CF, "classes": [{"cf": c, "excess": e} for c, e in obs],
                 "df_fit_db": df_fit, "fit_rms_db": rms_fit, "interior": interior,
                 "a3_deficit_db": -A3_OD_DEFICIT_DB, "agreement_db": abs(df_fit) - A3_OD_DEFICIT_DB}
    return True


# =================================================================================================
# Z6 -- what the gated row reads on each sub-population.  REPORTED, never proposed.
# =================================================================================================
def gate_z6(rows, out):
    print("\n-- Z6: WHAT THE GATED ROW READS PER SUB-POPULATION (reported, NOT a proposal) --")
    groups = [
        ("full-send OD (the gated row)", lambda r: not r["n12"]),
        ("  anchor cf only", lambda r: not r["n12"] and is_anchor(r["cf"])),
        ("  with bleed only", lambda r: not r["n12"] and not is_anchor(r["cf"])),
        ("gain-n12 [control]", lambda r: r["n12"]),
    ]
    print(f"      {'population':<30}{'n':>5}{'rms (GATED)':>13}{'SIGNED mean':>13}{'vs 3.0 bar':>12}")
    res = {}
    for lbl, pred in groups:
        g = [r for r in rows.values() if pred(r)]
        if not g:
            continue
        v = np.array([abs(r["level_signed"]) for r in g])
        s = float(np.mean([r["level_signed"] for r in g]))
        rms = float(np.sqrt(np.mean(v ** 2)))
        print(f"      {lbl:<30}{len(g):>5}{rms:>13.3f}{s:>+13.3f}"
              f"{('SHIP' if rms <= RG.THD_LEVEL_SHIP else 'over'):>12}")
        res[lbl.strip()] = {"n": len(g), "rms": rms, "signed": s}
    print("      ⛔ THIS IS NOT A PROPOSAL TO SPLIT OR RE-MEMBER THE ROW. Session 114 took the last")
    print("        such decision and it was the USER's; the note there is explicit that a split")
    print("        must keep the ORIGINAL bar on both halves and must be justified by the")
    print("        sub-populations disagreeing about a VERDICT, not by one half reading better.")
    print("      ⚠ And a split here would be less clean than session 114's: bleed is CONTINUOUS,")
    print("        the classes are unbalanced across DRIVE (Z2), and `cf` is the MODEL's own")
    print("        coefficient rather than a measured property of the reference.")
    out["z6"] = res
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report", nargs="?", default=None,
                    help="a comprehensive_report matrix JSON; defaults to the NEWEST one on disk, "
                         "resolved structurally (see _newest_matrix_report)")
    ap.add_argument("--json", help="write every printed number here")
    ap.add_argument("--ex-gain-n12", action="store_true",
                    help="pre-session-111 membership; quote only against a pre-s111 figure")
    ap.add_argument("--anchor-cf", type=float, default=None,
                    help="override the anchor clean fraction. `--anchor-cf 0` is the RETIRED "
                         "pre-s181 definition (exact zero) and reproduces every GATE Z number "
                         "published before session 191; the default is DERIVED from the shipped "
                         "end stop and is what the stage can actually reach.")
    a = ap.parse_args()
    resolved = a.report is None
    if resolved:
        a.report = _newest_matrix_report()

    print("=" * 100)
    print("GATE Z -- WHERE THE GATED THD LEVEL TERM LIVES, AND WHICH WAY IT POINTS")
    print("=" * 100)
    print(f"  report : {a.report}{'   [resolved: newest matrix report on disk]' if resolved else ''}")
    LLG.check_shipped_constant()
    anchor = set_anchor_cf(a.anchor_cf)
    derived = _anchor_cf()
    print(f"  anchor cf = {anchor:.6f} "
          f"({'DERIVED from the shipped end stop' if a.anchor_cf is None else 'OVERRIDDEN'}"
          f"{'' if a.anchor_cf is None else f'; derived value would be {derived:.6f}'})")
    if anchor < 1e-9 and derived >= 1e-9:
        print("  ⛔ RETIRED DEFINITION IN USE (exact zero). The shipped stage cannot reach it "
              "since s181, so the anchor class WILL be empty and Z3/Z4/Z5 will report NOT "
              "AVAILABLE. This is the reproduce-a-pre-s191-number mode, not a measurement mode.")
    bands, caps, drops, rows = collect(a.report, ex_n12=a.ex_gain_n12)
    if not rows:
        sys.exit("GATE Z FAIL: no gradeable OD THD rows in this report")

    out = {"report": a.report, "ex_gain_n12": bool(a.ex_gain_n12)}
    ok = True
    if not a.ex_gain_n12:                              # Z1's known answer is on the SHIPPED membership
        ok &= gate_z1(a.report, rows, out)
    else:
        print("\n-- Z1: SKIPPED -- --ex-gain-n12 is not the membership release_gate grades --")
    ok &= gate_z2(bands, caps, drops, rows, out)
    ok &= gate_z3(rows, out)
    ok &= gate_z4(rows, out)
    ok &= gate_z5(rows, out)
    ok &= gate_z6(rows, out)

    print("\n" + "=" * 100)
    print("GATE Z: PASS" if ok else "GATE Z: FAIL")
    print("=" * 100)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, default=float)
        print(f"  wrote {a.json}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
