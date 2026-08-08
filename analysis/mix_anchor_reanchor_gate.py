#!/usr/bin/env python3
"""GATE BN — RE-ANCHORING `OdToneRestore`'s DEAD `kMixS[0]` NODE (session 185, item 19 task P2).

WHY THIS EXISTS
---------------
s181 gave `LevelBlend` a BLEND wiper end stop (`blendEndStop = 0.02418`).  The clean coefficient at
LEVEL = BLEND = max therefore went `0 -> e`, so `LevelBlend::cleanFraction()` — which is the
independent variable of `OdToneRestore`'s mix law —

    cut(grunt, drive, cf) = kNotchGainDb[g][d] + kNotchMixK[g][d] * S(cf) + odNotchDepthDb

can no longer reach 0.  `kMixS[0] = 0.951` sits at the node `kMixCf[0] = 0.000`, which is now
UNREACHABLE, and `kNotchMixK`'s own definition point (`cut(cf = 0) - cut(kMixCfRef)`) went with it.

⭐⭐ THE NODE IS DEAD; THE SEGMENT IS NOT.  That distinction is the whole gate.  `mixShape` is
piecewise-linear, so `kMixS[0]` still reaches every cell on the FIRST SEGMENT `[0, 0.21]` through
interpolation — and the corner, at `cf = e = 0.02418`, is on that segment.  So "the node is
unreachable" does NOT mean "the constant is inert": the shipped law evaluates `S(e) = 0.781`
where the measurement that produced the table says `0.951`.

⇒ P2 IS A RE-ANCHOR, NOT A RE-FIT (s183 §10, s184 BM5 — both measured; do not re-derive).  The
0.951 was measured AT the bleed-free corner, and that corner's clean fraction is now `e` rather
than 0.  Re-expressing one measurement in the coordinate the model now uses is a change of
labelling; re-measuring the required cut would be a fit, and s184 measured that no fit is owed
(the applied cut moves 3.1x more at the corner than at the worst played cell, opposite in sign).

THE BAR (USER-AGREED, s183 §10): <= 0.05 dB at every REACHABLE MIXED cell.  Not bit-identical —
the corner is MEANT to move, and it is the one cell exempted by name.

WHAT THIS GATE MEASURES, AND THE ONE THING IT FINDS THAT NOBODY ASKED FOR
------------------------------------------------------------------------
The applied cut is ARITHMETIC (`base + K*S(cf) + offset`), so the primary measurement needs no
render at all and is exact.  BN4 then renders a handful of cells to check the one thing arithmetic
cannot: s184's own headline, that the applied CUT and the RENDERED RESPONSE are different
quantities and a bound on one is not automatically a bound on the other.

⚠⚠ BN1 IS THE LOAD-BEARING SUB-GATE AND IT SPLITS THE VERDICT IN TWO.  The bar is met on every
agreed verification set — but it is met for a MEMBERSHIP reason, not because the disturbance is
small, and reporting the pass without that is `aggregate-moved-check-membership-first` in its most
flattering form.  The re-anchor moves `S` only where `cf` is in the first segment above the corner;
the capture matrix has NO cell there at all (its LEVEL detents jump from knob 0.875 at cf 0.244 to
knob 1.0 at cf 0.024), so "0 of 20 cells move" is a statement about the grid.  On the CONTROL
SURFACE the same band is the top few per cent of the LEVEL knob at high BLEND, and it moves by up
to the full corner excursion.  Both numbers are printed, always, side by side.

⭐ AND THE BAND IS AN ARGUMENT FOR THE RE-ANCHOR RATHER THAN AGAINST IT, WHICH IS WORTH STATING
BECAUSE IT INVERTS THE OBVIOUS READING: the shipped segment `[0, 0.21]` has a LEFT ENDPOINT THAT NO
LONGER CORRESPONDS TO ANY PHYSICAL SETTING, so every value the shipped law returns in that band is
an extrapolation off a dead node.  The re-anchored segment `[e, 0.21]` has both endpoints on
reachable settings.  The re-anchor does not disturb an anchored region; it anchors an unanchored
one.  ⛔ That is an argument, not a measurement — it is labelled as such in BN5 and does not enter
any verdict.

WHAT IS DELIBERATELY NOT DONE HERE
----------------------------------
⛔ The OTHER seven nodes' abscissae are stale by the same mechanism (every capture's clean fraction
moved under s181, not just the corner's), and this gate does NOT re-map them.  Two reasons, and the
second is the real one: (1) s184 measured the law's error off the corner at <= 0.508 dB worst and
-0.144 dB at the listening condition, so there is no defect there to chase; (2) a full re-map is
NOT a coordinate change — the required cut genuinely changes when `e` adds clean bleed to the
composite null, so re-mapping every node would be a RE-FIT wearing a re-anchor's name, which is
exactly what item 10's standing note forbids.  BN1c prints the size of the other nodes' shift so
the decision is visible rather than assumed.

Usage:
    python3.11 analysis/mix_anchor_reanchor_gate.py [--no-render] [--json PATH]
"""

import argparse
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import analyze as A                       # noqa: E402
import captures as C                      # noqa: E402
import level_law_gate as K                # noqa: E402
import od_tone_restore_fit as F           # noqa: E402
import feature_locus_gate as W            # noqa: E402
import bleedfree_anchor_gate as BL        # noqa: E402
import mix_grid_anchor_gate as BM         # noqa: E402
import comprehensive_report as CR         # noqa: E402

HDR_ODT = "src/dsp/OdToneRestore.h"
HDR_FIT = "src/dsp/FitParams.h"

CURVE_DIR = "build/s185_reanchor_curves"
OS_FACTOR = BL.OS_FACTOR
SWEEPS = BL.SWEEPS
# ⚠ GATE BL stores these as (capture-token, value) PAIRS.  Unpacked here rather than re-typed, so
# the two gates cannot drift apart on which conditions they mean.
DRIVES_R = BL.DRIVES                      # (token, DRIVE knob) — the RENDERED conditions
GRUNTS = tuple(v for _t, v in BL.GRUNTS)  # APVTS grunt indices

# The bar, agreed with the user at s183 §10.  A MIXED cell is any reachable (LEVEL, BLEND) whose
# clean fraction is strictly above the corner's; the corner itself is exempt BY NAME (never by a
# predicate on its clean fraction — s105 M2/M3: what is special about it is not in its settings,
# it is that it is the one cell the re-anchor exists to move).
BAR_DB = 0.05
CORNER_LB = (1.0, 1.0)                    # (LEVEL knob, BLEND knob) — the bleed-free corner

# The band the graded features live in, for BN4's rendered check.  Imported from GATE W's own
# `mid_notch` window rather than chosen here: the stage's notch is at 323 Hz and that window is
# what every depth reading in this project uses.
NOTCH_F = (285.0, 358.0)


# =================================================================================================
# the mix law, as a function of the S table — one implementation, used by every arm
# =================================================================================================
def clean_frac(level_knob, blend_knob, endstop=None):
    """The clean fraction the SHIPPED stage reports, from GATE K's imported mirrors.

    `coef_closed` takes the TAPERED level (s113: a shipped stage's closed form takes the STAGE's
    input, not the knob) and the RAW blend knob (the end stops are applied inside it)."""
    od, cl = K.coef_closed(blend_knob, K.level_taper(level_knob), endstop=endstop)
    return (cl / (od + cl)) if (od + cl) > 0 else 1.0


def mix_shape(cf, cfs, ss):
    """S(cf) — MUST mirror `OdToneRestore::mixShape()`: piecewise-linear, FLAT outside the nodes.

    Taken as (nodes, values) rather than off the header, so a candidate re-anchor is expressed as
    a different node list and shares this one interpolation rule with the shipped arm.  A second
    copy of the rule per arm is how an arm-to-arm difference becomes an implementation difference."""
    if cf <= cfs[0]:
        return float(ss[0])
    if cf >= cfs[-1]:
        return float(ss[-1])
    return float(np.interp(cf, cfs, ss))


def drive_knots(T):
    """The DRIVE values the arithmetic is evaluated at: the TABLE'S OWN KNOTS.

    `kNotchMixK` is piecewise-linear in DRIVE, and the extremum of a PWL function is attained at a
    knot — so evaluating at the knots is not a sample of the DRIVE axis, it is exhaustive over it.
    (The RENDERED sub-gate uses GATE BL's three captured rungs instead; those are conditions that
    exist on disk, which is a different requirement.)"""
    return tuple(T["kX"])


def applied_cut(cf, grunt_enum, drive, T, cfs, ss, depth_off):
    """The dB of cut `OdToneRestore` applies at one condition — the quantity the bar is on."""
    return (F.lerp5(T["kNotchGainDb"][grunt_enum], drive, T["kX"])
            + F.lerp5(T["kNotchMixK"][grunt_enum], drive, T["kX"]) * mix_shape(cf, cfs, ss)
            + depth_off)


RETIRED_MIX_CF0 = 0.0     # the pre-s185 abscissa of node 0 — kept reachable (s124)


def anchor_state(T, e_hi):
    """Which of the two states the header currently SHIPS, and both node lists.

    ⭐⭐ THIS GATE HAS TO SURVIVE ITS OWN RESULT.  Before s185 shipped the re-anchor, the
    `abscissa` candidate differed from the header and BN0f's non-vacuity guard was satisfied;
    afterwards it IS the header, the guard fires, and the gate would refuse — reporting "the
    candidate is inert" about a change that had already landed.  So the comparison is always
    stated in one fixed direction, **RE-ANCHORED minus RETIRED**, and which one is shipped is
    DETECTED and printed.  That keeps every published number's sign valid across the shipping
    boundary and keeps the retired form reproducible, which is s124's rule."""
    cf0 = T["kMixCf"][0]
    reanchored = ([e_hi] + list(T["kMixCf"][1:]), list(T["kMixS"]))
    retired = ([RETIRED_MIX_CF0] + list(T["kMixCf"][1:]), list(T["kMixS"]))
    if abs(cf0 - e_hi) < 1e-12:
        return "reanchored", reanchored, retired
    if abs(cf0 - RETIRED_MIX_CF0) < 1e-12:
        return "retired", reanchored, retired
    sys.exit(f"GATE BN: kMixCf[0] = {cf0} is neither the retired {RETIRED_MIX_CF0} nor the "
             f"re-anchored {e_hi} (= blendEndStop).  This gate only knows those two states; if a "
             "third has been introduced, it needs its own provenance before anything below means "
             "anything.")


def reanchor_nodes(T, e_hi, mode, nodes=None):
    """The candidate node lists.

    `abscissa`  — move the dead node's ABSCISSA to the corner's new clean fraction, keeping its
                  measured ordinate.  This is the re-anchor as item 10 states it.
    `ordinate`  — leave the abscissa at 0 and solve `kMixS[0]` so the SAME line passes through
                  (e, 0.951).  A different edit to the same header producing the same law.
    `noop`      — the shipped table, unchanged.  BN0g's inert control.

    ⭐ `abscissa` and `ordinate` are two spellings of one line, so they MUST agree at every
    reachable cf.  BN0e asserts that; it is the gate's own known answer and it is what says the
    'which constant do we edit?' question is cosmetic rather than a second candidate."""
    cfs, ss = (list(T["kMixCf"]), list(T["kMixS"])) if nodes is None \
        else (list(nodes[0]), list(nodes[1]))
    if mode == "noop":
        return cfs, ss
    if mode == "abscissa":
        return [e_hi] + cfs[1:], list(ss)
    if mode == "ordinate":
        # Solve S0' so the segment (0, S0') -> (cf1, S1) passes through (e, S0_measured).
        t = (e_hi - cfs[0]) / (cfs[1] - cfs[0])
        s0_new = (ss[0] - t * ss[1]) / (1.0 - t)
        return list(cfs), [s0_new] + ss[1:]
    raise ValueError(mode)


# =================================================================================================
# the condition sets
# =================================================================================================
def verification_cells():
    """Every (LEVEL knob, BLEND knob) the agreed verification sets contain, deduplicated.

    Two sources, both IMPORTED: GATE BM's 20 mix cells (P1's own grid) and every capture in
    `od_tone_restore_fit.SETS` resolved through `captures.parse_capture` — settings, never
    filenames (s65)."""
    cells = {}
    for lt, lv, bt, bv in BM.MIX_CELLS:
        cells.setdefault((lv, bv), set()).add(f"BM:L{lt}/B{bt}")
    for name, rows in sorted(F.SETS.items()):
        for fname, _drv in rows:
            p = C.parse_capture(fname)
            cells.setdefault((p["level"], p["blend"]), set()).add(f"set:{name}")
    return cells


def control_surface(n_level=4001, n_blend=41):
    """A dense sweep of the reachable (LEVEL knob, BLEND knob) surface.

    ⚠⚠ THIS IS THE POINT OF THE SUB-GATE IT FEEDS.  The verification sets are DETENTS; the knobs
    are continuous, so `cf` takes every value between the detents' and a bar met at the detents is
    not a bar met on the control the player turns."""
    return np.linspace(0.0, 1.0, n_level), np.linspace(0.0, 1.0, n_blend)


# =================================================================================================
# BN0 — guards and known answers
# =================================================================================================
def gate_bn0(T, e_hi, depth_off, state, cand, base, out):
    print("=" * 100)
    print("BN0  GUARDS AND KNOWN ANSWERS")
    print("=" * 100)
    print(f"  (0) STATE        src/dsp/OdToneRestore.h currently ships the **{state.upper()}** "
          f"node (kMixCf[0] = {T['kMixCf'][0]:.5f})")
    print("                   every number below is RE-ANCHORED minus RETIRED, in that fixed "
          "direction, whichever is shipped")

    # (a) EPOCH.  Both constants this gate is a statement about, read from the source.
    K.check_shipped_endstop()
    print(f"  (a) EPOCH        blendEndStop = {e_hi:.6g}   [GATE K's single resolver, s182]")
    print(f"                   odNotchDepthDb = {depth_off:.6g}   [parsed from {HDR_FIT}]")

    # (b) CROSS-GATE KNOWN ANSWER.  This gate PARSES the tables (s149: read the value set the
    # plugin runs, never a transcription); GATE BM TRANSCRIBES them behind a drift guard.  They
    # must agree, and if they ever do not, one of the two gates is stale — which is a defect
    # report about the pair, not about either alone.
    worst_k = max(abs(T["kNotchMixK"][g][d] - BM.NOTCH_MIX_K[g][d])
                  for g in range(3) for d in range(5))
    worst_base = max(abs(T["kNotchGainDb"][g][0] - BM.NOTCH_BASE_DRIVE0[g]) for g in range(3))
    if worst_k > 1e-12 or worst_base > 1e-12:
        sys.exit(f"GATE BN: the tables PARSED out of {HDR_ODT} disagree with GATE BM's "
                 f"transcribed copies (kNotchMixK by {worst_k:.3g}, kNotchGainDb@DRIVE0 by "
                 f"{worst_base:.3g}).  One of the two gates is stale; fix the pair, do not "
                 "tolerate the drift.")
    if abs(T["kMixCfRef"] - BM.MIX_CF_REF) > 1e-12:
        sys.exit(f"GATE BN: kMixCfRef parsed {T['kMixCfRef']} vs GATE BM's {BM.MIX_CF_REF}.")
    print(f"  (b) CROSS-GATE   parsed tables == GATE BM's transcribed copies "
          f"(kNotchMixK worst {worst_k:.1e}, kNotchGainDb worst {worst_base:.1e})")

    # (c) THE PIN.  S is defined as pinned to 0 at kMixCfRef; if it is not, the table has moved
    # under this gate and every K in it means something else.
    cfs, ss = T["kMixCf"], T["kMixS"]
    pin = mix_shape(T["kMixCfRef"], cfs, ss)
    if abs(pin) > 2e-3:
        sys.exit(f"GATE BN: S(kMixCfRef = {T['kMixCfRef']}) = {pin:.6f}, expected 0.  The mix "
                 "table has moved; kNotchGainDb no longer means 'the cut at the reference mix'.")
    print(f"  (c) PIN          S(kMixCfRef = {T['kMixCfRef']}) = {pin:+.6f}   (pinned to 0)")

    # (d) THE MINIMUM REACHABLE CLEAN FRACTION, swept over the whole control surface rather than
    # asserted at the corner — the claim is that NOTHING reaches below it, which is a statement
    # about the surface.  ⭐ Free known answer riding along: the corner's OD coefficient is
    # (1 - e), so its level is 20log10(1-e) — s183's flat term, reproduced from the network.
    lv, bv = control_surface()
    cf_surf = np.array([[clean_frac(x, b) for b in bv] for x in lv])
    cf_min = float(cf_surf.min())
    if abs(cf_min - e_hi) > 1e-9:
        sys.exit(f"GATE BN: the minimum clean fraction over the control surface is {cf_min:.8f}, "
                 f"not blendEndStop = {e_hi:.8f}.  The corner is not where this gate thinks it "
                 "is and every 'reachable' statement below is wrong.")
    i, j = np.unravel_index(np.argmin(cf_surf), cf_surf.shape)
    if abs(lv[i] - CORNER_LB[0]) > 1e-9 or abs(bv[j] - CORNER_LB[1]) > 1e-9:
        sys.exit(f"GATE BN: the minimum clean fraction is attained at LEVEL {lv[i]:.4f} / BLEND "
                 f"{bv[j]:.4f}, not at the corner {CORNER_LB}.")
    od_corner = K.coef_closed(1.0, K.level_taper(1.0))[0]
    flat_db = 20.0 * np.log10(od_corner)
    print(f"  (d) MIN cf       {cf_min:.8f} over {cf_surf.size} surface points == blendEndStop, "
          f"attained only at LEVEL/BLEND max")
    print(f"                   corner OD coefficient {od_corner:.6f} -> {flat_db:+.4f} dB  "
          "[s183's flat term, from the network]")

    # (e) THE GATE'S OWN KNOWN ANSWER — the two spellings of the re-anchor are ONE law.
    # ⭐ BOTH spellings are constructed from the RETIRED nodes, never from whatever is shipped —
    # otherwise this known answer goes vacuous the moment the re-anchor lands (post-ship the
    # ordinate solve would be handed a table already at `e`, return 0.951 unchanged, and "they
    # agree" would mean nothing).  A known answer that dies on success is not a known answer.
    ab = reanchor_nodes(T, e_hi, "abscissa", nodes=base)
    od_ = reanchor_nodes(T, e_hi, "ordinate", nodes=base)
    probe = np.linspace(e_hi, 1.0, 20001)
    worst_spell = max(abs(mix_shape(c, *ab) - mix_shape(c, *od_)) for c in probe)
    if worst_spell > 1e-12:
        sys.exit(f"GATE BN: the abscissa and ordinate spellings of the re-anchor differ by "
                 f"{worst_spell:.3g} in S on the reachable range.  They are meant to be the same "
                 "line; one of the two constructions is wrong.")
    print(f"  (e) SPELLINGS    abscissa-move == ordinate-solve over cf in [e, 1]  "
          f"(worst |dS| {worst_spell:.1e}, n = {len(probe)})"
          + "   [both built from the RETIRED nodes, so this cannot go vacuous]")
    print(f"                   RETIRED -> RE-ANCHORED:  kMixCf[0] {base[0][0]:.5f} -> "
          f"{ab[0][0]:.5f}   OR   kMixS[0] {base[1][0]:.6f} -> {od_[1][0]:.6f}")

    # (f) NON-VACUITY.  A re-anchor that moved nothing would pass every bar below trivially.
    ge = BM.GRUNT_ENUM[1]                      # APVTS 1 = GRUNT cut = the steepest K row
    d_corner = (applied_cut(e_hi, ge, 0.5, T, *ab, depth_off)
                - applied_cut(e_hi, ge, 0.5, T, *base, depth_off))
    if abs(d_corner) < 1.0:
        sys.exit(f"GATE BN: the re-anchor moves the corner's cut by only {d_corner:+.4f} dB.  "
                 "Every bar below would pass vacuously; the candidate is inert.")
    print(f"  (f) NON-VACUITY  corner cut moves {d_corner:+.4f} dB at GRUNT cut / DRIVE noon")

    # (g) INERT CONTROL.  The `noop` arm must be exactly zero everywhere, or the arm machinery
    # itself is introducing a difference and every number below is that difference.
    nn = reanchor_nodes(T, e_hi, "noop")
    worst_noop = 0.0
    for c in np.linspace(0.0, 1.0, 5001):
        for g in range(3):
            for d in drive_knots(T):
                worst_noop = max(worst_noop,
                                 abs(applied_cut(c, g, d, T, *nn, depth_off)
                                     - applied_cut(c, g, d, T, T["kMixCf"], T["kMixS"], depth_off)))
    if worst_noop != 0.0:
        sys.exit(f"GATE BN: the inert control moves the cut by {worst_noop:.3g} dB.  The arm "
                 "machinery is not neutral and no arm-to-arm number below is attributable.")
    print(f"  (g) INERT        noop arm moves the cut by exactly {worst_noop:.1f} dB everywhere")

    out["bn0"] = {"state": state, "blendEndStop": e_hi, "odNotchDepthDb": depth_off, "pin": pin,
                  "cf_min": cf_min, "corner_od_db": flat_db,
                  "kMixCf0_new": ab[0][0], "kMixS0_new": od_[1][0],
                  "corner_cut_move_db": d_corner, "spelling_worst_dS": worst_spell}


# =================================================================================================
# BN1 — the reachable domain, and the membership caveat
# =================================================================================================
def gate_bn1(T, e_hi, depth_off, cand, base, out):
    print()
    print("=" * 100)
    print("BN1  THE REACHABLE DOMAIN — WHERE THE RE-ANCHOR CAN MOVE ANYTHING AT ALL")
    print("=" * 100)

    ship = base
    kmax = max(abs(v) for row in T["kNotchMixK"] for v in row)

    # The band is defined by the LAW, not by a chosen cf: it is exactly where S differs between
    # the two node lists, and it ends where the two lines meet again (the second node).
    grid = np.linspace(e_hi, T["kMixCf"][1], 200001)
    dS = np.array([mix_shape(c, *cand) - mix_shape(c, *ship) for c in grid])
    over = np.where(np.abs(dS) * kmax > BAR_DB)[0]
    cf_bar = float(grid[over[-1]]) if len(over) else e_hi
    print(f"  (a) THE BAND     S differs only on cf in [{e_hi:.5f}, {T['kMixCf'][1]:.5f}] "
          f"(the first segment); |dS| falls linearly to 0 at its right node")
    print(f"                   worst |dcut| = |dS|max x max|K| = {abs(dS).max():.5f} x {kmax:.2f} "
          f"= {abs(dS).max() * kmax:.4f} dB, at the corner")
    print(f"                   the {BAR_DB} dB bar is exceeded for cf < {cf_bar:.5f}")

    # (b) MEMBERSHIP — the verification sets.
    cells = verification_cells()
    inband, rows = [], []
    for (lv, bv), tags in sorted(cells.items()):
        cf = clean_frac(lv, bv)
        corner = abs(lv - CORNER_LB[0]) < 1e-12 and abs(bv - CORNER_LB[1]) < 1e-12
        hit = (not corner) and (cf < cf_bar)
        if hit:
            inband.append((lv, bv, cf))
        rows.append({"level": lv, "blend": bv, "cf": cf, "corner": corner, "over_bar": hit,
                     "tags": sorted(tags)})
    n_mixed = sum(1 for r in rows if not r["corner"])
    print(f"  (b) VERIFICATION {len(rows)} distinct (LEVEL, BLEND) cells "
          f"({len(BM.MIX_CELLS)} from GATE BM + {len(F.SETS)} --set groups), "
          f"{n_mixed} of them MIXED")
    lo_mixed = min(r["cf"] for r in rows if not r["corner"])
    print(f"                   lowest MIXED clean fraction = {lo_mixed:.5f}, against a band "
          f"ending at {cf_bar:.5f}")
    print(f"                   -> {len(inband)} of {n_mixed} mixed cells inside the band")

    # (c) THE CONTINUUM.  ⚠⚠ This is the half the verification sets cannot see.
    lv_s, bv_s = control_surface()
    worst_frac, worst_b = 0.0, None
    per_blend = []
    for b in bv_s:
        cf_col = np.array([clean_frac(x, b) for x in lv_s])
        mixed = cf_col > e_hi + 1e-12
        hit = mixed & (cf_col < cf_bar)
        frac = float(hit.sum()) / float(len(lv_s))
        per_blend.append({"blend": float(b), "frac_level_travel": frac,
                          "lo": float(lv_s[hit].min()) if hit.any() else None,
                          "hi": float(lv_s[hit].max()) if hit.any() else None})
        if frac > worst_frac:
            worst_frac, worst_b = frac, float(b)
    print(f"  (c) CONTINUUM    dense sweep {len(lv_s)} LEVEL x {len(bv_s)} BLEND knob positions")
    print(f"                   worst BLEND = {worst_b:.3f}: {100 * worst_frac:.2f} % of the LEVEL "
          f"knob's travel is over the bar")
    for pb in per_blend:
        if pb["blend"] in (0.25, 0.5, 0.75, 1.0):
            if pb["lo"] is None:
                print(f"                   BLEND {pb['blend']:.2f}: no LEVEL position over the bar")
            else:
                print(f"                   BLEND {pb['blend']:.2f}: LEVEL knob "
                      f"[{pb['lo']:.4f}, {pb['hi']:.4f}] = {100 * pb['frac_level_travel']:.2f} % "
                      "of travel")

    # ⭐ COMPUTED VERDICT, both directions — the two halves disagree and the gate says so rather
    # than reporting whichever is convenient.
    if len(inband) == 0 and worst_frac > 0.0:
        print()
        print(f"  ⚠⚠ THE TWO HALVES DISAGREE, AND BOTH ARE RIGHT.  The bar is met at "
              f"{n_mixed} of {n_mixed} mixed VERIFICATION cells and violated on "
              f"{100 * worst_frac:.2f} % of the LEVEL knob's travel.  The disturbed band is a "
              "GAP IN THE CAPTURE MATRIX, not a region the law is quiet in — the detents jump "
              f"from cf {lo_mixed:.3f} straight to the corner's {e_hi:.5f}.")
        print("     ⇒ quote the pass WITH its membership, never alone.")
    elif len(inband) == 0:
        print("  ⇒ the bar is met at every mixed verification cell AND on the whole continuum.")
    else:
        print(f"  ⇒ {len(inband)} mixed verification cells are over the bar: "
              + ", ".join(f"L{lv:.3f}/B{bv:.3f} (cf {cf:.4f})" for lv, bv, cf in inband))

    # (d) THE OTHER NODES' STALENESS — printed so the decision not to re-map them is visible.
    print()
    print("  (d) THE OTHER SEVEN NODES are stale by the same mechanism and are NOT re-mapped "
          "here (see the docstring).  Size of the shift, for the record:")
    for name, (lv0, bv0) in (("corner  L1.000/B1.000", (1.0, 1.0)),
                             ("listen  L0.500/B1.000", (0.5, 1.0)),
                             ("blend   L1.000/B0.500", (1.0, 0.5))):
        c0 = clean_frac(lv0, bv0, endstop=(0.0, 0.0))
        c1 = clean_frac(lv0, bv0)
        print(f"      {name}:  cf  {c0:.5f} (pre-s181)  ->  {c1:.5f} (shipped)   "
              f"delta {c1 - c0:+.5f}")

    out["bn1"] = {"cf_bar": cf_bar, "band": [e_hi, T["kMixCf"][1]],
                  "worst_dcut_db": float(abs(dS).max() * kmax), "max_abs_K": kmax,
                  "cells": rows, "n_mixed": n_mixed, "n_inband": len(inband),
                  "lowest_mixed_cf": lo_mixed,
                  "continuum_worst_frac": worst_frac, "continuum_worst_blend": worst_b,
                  "per_blend": per_blend}
    return cf_bar, rows


# =================================================================================================
# BN2 — the applied cut, every verification cell x GRUNT x DRIVE
# =================================================================================================
def gate_bn2(T, e_hi, depth_off, cand, base, rows, out):
    print()
    print("=" * 100)
    print("BN2  APPLIED CUT — RE-ANCHORED minus RETIRED, AT EVERY VERIFICATION CELL")
    print("=" * 100)
    ship = base

    worst_mixed, worst_where, corner_moves, n = 0.0, None, [], 0
    for r in rows:
        for g_apvts in GRUNTS:
            ge = BM.GRUNT_ENUM[g_apvts]
            for d in drive_knots(T):
                a = applied_cut(r["cf"], ge, d, T, *cand, depth_off)
                b = applied_cut(r["cf"], ge, d, T, *ship, depth_off)
                n += 1
                if r["corner"]:
                    corner_moves.append(a - b)
                elif abs(a - b) > worst_mixed:
                    worst_mixed, worst_where = abs(a - b), (r["level"], r["blend"], g_apvts, d)

    print(f"  n = {n} (cell x GRUNT x DRIVE) readings, of which "
          f"{len(corner_moves)} are the corner")
    print(f"  worst |dcut| at a MIXED cell : {worst_mixed:.6f} dB"
          + (f"   at LEVEL {worst_where[0]:.3f} / BLEND {worst_where[1]:.3f} / "
             f"GRUNT {worst_where[2]} / DRIVE {worst_where[3]:.2f}" if worst_where else ""))
    print(f"  corner move                  : {min(corner_moves):+.4f} .. "
          f"{max(corner_moves):+.4f} dB  (exempt by name)")
    verdict = "MET" if worst_mixed <= BAR_DB else "EXCEEDED"
    print(f"  ⇒ BAR ({BAR_DB} dB at every mixed verification cell): {verdict}")

    out["bn2"] = {"n": n, "worst_mixed_db": worst_mixed,
                  "worst_where": list(worst_where) if worst_where else None,
                  "corner_min_db": min(corner_moves), "corner_max_db": max(corner_moves),
                  "verdict": verdict}
    return worst_mixed <= BAR_DB


# =================================================================================================
# BN3 — does the re-anchor RESTORE the pre-s181 law at the corner?
# =================================================================================================
def gate_bn3(T, e_hi, depth_off, cand, base, rows, out):
    print()
    print("=" * 100)
    print("BN3  AGAINST THE PRE-s181 LAW — WHAT THE RE-ANCHOR RESTORES, AND WHAT IT DOES NOT")
    print("=" * 100)
    ship = base
    print("  Pre-s181 = the RETIRED tables evaluated at the clean fraction the PRE-END-STOP network")
    print("  produced at that setting (`endstop=(0,0)`).  That is the law s156 shipped.")
    print()
    print(f"  {'cell':>22}  {'cf pre':>8} {'cf ship':>8}  {'ship-pre':>9} {'reanc-pre':>10}")

    recs = []
    for r in rows:
        cf0 = clean_frac(r["level"], r["blend"], endstop=(0.0, 0.0))
        for g_apvts in GRUNTS:
            ge = BM.GRUNT_ENUM[g_apvts]
            for d in drive_knots(T):
                pre = applied_cut(cf0, ge, d, T, *ship, depth_off)
                shp = applied_cut(r["cf"], ge, d, T, *ship, depth_off)
                rea = applied_cut(r["cf"], ge, d, T, *cand, depth_off)
                recs.append({"level": r["level"], "blend": r["blend"], "corner": r["corner"],
                             "grunt": g_apvts, "drive": d,
                             "ship_minus_pre": shp - pre, "reanc_minus_pre": rea - pre})

    corner = [x for x in recs if x["corner"]]
    mixed = [x for x in recs if not x["corner"]]
    for tag, sel in (("CORNER  L1.000/B1.000", corner),):
        sm = max(abs(x["ship_minus_pre"]) for x in sel)
        rm = max(abs(x["reanc_minus_pre"]) for x in sel)
        cf0 = clean_frac(1.0, 1.0, endstop=(0.0, 0.0))
        print(f"  {tag:>22}  {cf0:8.5f} {e_hi:8.5f}  {sm:+9.4f} {rm:+10.6f}   (worst |.|, n={len(sel)})")
    sm = max(abs(x["ship_minus_pre"]) for x in mixed)
    rm = max(abs(x["reanc_minus_pre"]) for x in mixed)
    print(f"  {'all MIXED cells':>22}  {'':>8} {'':>8}  {sm:+9.4f} {rm:+10.4f}   "
          f"(worst |.|, n={len(mixed)})")

    corner_restored = max(abs(x["reanc_minus_pre"]) for x in corner)
    print()
    if corner_restored < 1e-9:
        print(f"  ⭐⭐ THE CORNER IS RESTORED EXACTLY: worst |re-anchored - pre-s181| = "
              f"{corner_restored:.2e} dB over {len(corner)} (GRUNT x DRIVE) readings.")
        print("      That is not a fit landing well — it is an identity.  S(corner) is pinned to "
              "the measured 0.951 by construction, so the corner's cut is the pre-s181 cut.")
    else:
        print(f"  ⚠ the corner is NOT restored: worst residual {corner_restored:.4g} dB.")
    print(f"  ⚠ AND THE MIXED CELLS ARE NOT RESTORED, ON PURPOSE: worst {rm:.4f} dB remains "
          "against pre-s181.")
    print("      That residual is s184's measured `ship - e0` at played settings and it is a REAL "
          "consequence of the end stop changing the mix, not an artefact of the dead node.  A "
          "re-anchor must not remove it; removing it would be a re-fit.")

    out["bn3"] = {"corner_restored_db": corner_restored, "mixed_worst_vs_pre_db": rm,
                  "corner_ship_vs_pre_db": max(abs(x["ship_minus_pre"]) for x in corner)}


# =================================================================================================
# BN4 — the RENDERED check
# =================================================================================================
def render_cells(T, e_hi, depth_off, cand, cf_bar):
    """(tag, LEVEL, BLEND, why) for the rendered check.

    Chosen to span the three regimes the arithmetic distinguishes, and NAMED so the selection is
    not a search over outcomes (`self-selecting-scores`)."""
    cells = [("corner", 1.0, 1.0, "the cell the re-anchor exists to move"),
             ("listen", 0.5, 1.0, "the user's stated listening condition (mixed, far above the band)"),
             ("blendmid", 1.0, 0.5, "the other dilution axis, mixed"),
             ("ladder", 0.875, 1.0, "the LOWEST-cf mixed detent — the closest cell to the band")]
    # ⚠⚠ THE FOUR ABOVE CANNOT ANSWER THIS SUB-GATE'S OWN QUESTION, AND THAT IS THE POINT OF THE
    # THREE BELOW.  Every MIXED verification cell has `dcut` identically 0, so rendering them
    # confirms 0 -> 0 and says nothing about whether a SMALL cut change can be amplified by a
    # near-cancellation.  The only mixed cells where the cut moves at all are the uncaptured ones
    # INSIDE the band — which is also the region BN1's continuum finding is about.  Rendering them
    # is what turns BN4 from a tautology into a measurement.  ⛔ These are NOT captured settings, so
    # they are model-vs-model only; no reference number can be quoted at them.
    # A LADDER, not an endpoint pair (s129): the band runs continuously from where the bar starts
    # being exceeded up to the corner, so the rendered disturbance is a dose-response and is
    # reported as one.  `band999` is the closest reachable mixed cell to the corner sampled here.
    # ⚠ THE TAG MUST BE INJECTIVE IN THE SETTING.  A first draft used `int(lk*100)`, which maps
    # 0.99, 0.995 and 0.999 onto ONE tag — colliding the render cache (each re-rendered over the
    # last, saved only by `curves()`'s argv stamp) and mis-pairing three rows of the ratio table
    # against the first cell's cf and dcut.  Found by reading the printed table, not by any guard.
    for lk in (0.94, 0.96, 0.98, 0.99, 0.995, 0.999):
        cells.append((("band" + f"{lk:.4f}".replace(".", "p")), lk, 1.0,
                      "INSIDE the disturbed band — mixed, uncaptured, where the cut does move"))
    return cells


def gate_bn4(T, e_hi, depth_off, cand, base, state, cf_bar, out, do_render):
    print()
    print("=" * 100)
    print("BN4  THE RENDERED CHECK — DOES A BOUND ON THE *CUT* BOUND THE *RESPONSE*?")
    print("=" * 100)
    print("  s184's headline is that the applied CUT and the RENDERED RESPONSE are different")
    print("  quantities.  A cut change is applied to the OD branch; at a mixed cell the composite")
    print("  is a SUM, so near a cancellation a small branch change can produce a larger one in")
    print("  the sum.  BN2 bounds the cut; only a render bounds the response.")
    if not do_render:
        print("  -- SKIPPED (--no-render) --")
        out["bn4"] = {"skipped": True}
        return
    # ⭐ RENDER PRIVATE (s159).  `BM.curves` is reused because it already carries the argv+BINARY
    # stamp this check depends on — but it caches into GATE BM's own directory, and pointing a new
    # tool at another gate's cache is exactly what s159's GATE W rule forbids.  Re-point it at this
    # gate's directory for the duration instead of copying the function.
    bm_dir = BM.CURVE_DIR
    BM.CURVE_DIR = CURVE_DIR
    # ⭐ The SHIPPED state renders with no `--fit`; the OTHER state is emulated through
    # `odNotchDepthDb`, which adds a uniform dB to the same `cutDb` (s184's `mixfroz` trick).  Which
    # of the two is which flips at the shipping boundary, so it is DERIVED from `state`.
    shipped_nodes = cand if state == "reanchored" else base
    other_nodes = base if state == "reanchored" else cand
    ship = base
    cells = render_cells(T, e_hi, depth_off, cand, cf_bar)
    tags = [c[0] for c in cells]
    if len(set(tags)) != len(tags):
        dup = sorted({t for t in tags if tags.count(t) > 1})
        sys.exit(f"GATE BN: render tags are not injective ({dup}).  Two conditions would share "
                 "one cache entry and the ratio table would mis-pair rows against the first.")
    grunt_apvts, drive = 1, 0.5              # GRUNT cut / DRIVE noon — the steepest K row
    ge = BM.GRUNT_ENUM[grunt_apvts]

    recs = []
    for tag, lv, bv, why in cells:
        cf = clean_frac(lv, bv)
        dcut = (applied_cut(cf, ge, drive, T, *cand, depth_off)
                - applied_cut(cf, ge, drive, T, *base, depth_off))
        # rendered offset that turns the SHIPPED build into the OTHER state
        d_other = (applied_cut(cf, ge, drive, T, *other_nodes, depth_off)
                   - applied_cut(cf, ge, drive, T, *shipped_nodes, depth_off))
        a_ship = BL.cond_args(drive, grunt_apvts, blend=bv, level=lv)
        a_rean = BL.cond_args(drive, grunt_apvts, blend=bv, level=lv,
                              extra=("--fit", f"odNotchDepthDb={depth_off + d_other:.9f}"))
        cs = BM.curves(f"BN_{tag}_{state}", a_ship)
        cr = BM.curves(f"BN_{tag}_other", a_rean)
        worst, worst_band = 0.0, None
        for sw in SWEEPS:
            d = cr[sw] - cs[sw]
            m = np.max(np.abs(d))
            if m > worst:
                worst, worst_band = float(m), sw
        recs.append({"tag": tag, "level": lv, "blend": bv, "cf": cf, "why": why,
                     "dcut_db": dcut, "rendered_worst_db": worst, "worst_sweep": worst_band})
        print(f"  {tag:>9}  L{lv:.3f}/B{bv:.3f}  cf {cf:.5f}   predicted dcut {dcut:+8.4f} dB"
              f"   rendered worst |d| {worst:7.4f} dB  ({worst_band})")
        print(f"            {why}")

    ver = [r for r in recs if not r["tag"].startswith("band") and r["tag"] != "corner"]
    band = [r for r in recs if r["tag"].startswith("band")]
    worst_mixed_rendered = max(r["rendered_worst_db"] for r in ver)
    print()
    print(f"  worst rendered |d| at a MIXED VERIFICATION cell: {worst_mixed_rendered:.5f} dB "
          f"(bar {BAR_DB}) over n = {len(ver)} cells x {len(SWEEPS)} sweeps")
    verdict = "MET" if worst_mixed_rendered <= BAR_DB else "EXCEEDED"
    print(f"  ⇒ RENDERED BAR (verification cells): {verdict}")

    # ⭐ THE AMPLIFICATION QUESTION, answered only by the cells where the cut actually moves.
    amp = [(r, r["rendered_worst_db"] / abs(r["dcut_db"]))
           for r in recs if abs(r["dcut_db"]) > 1e-9]
    print()
    if len(ver) and max(abs(r["dcut_db"]) for r in ver) < 1e-12:
        print(f"  ⚠⚠ THE {len(ver)} MIXED VERIFICATION CELLS CANNOT ANSWER THIS SUB-GATE'S OWN")
        print("     QUESTION: their predicted `dcut` is identically 0, so rendering them confirms")
        print("     0 -> 0 and bounds no amplification.  The cells below are the ones that can.")
    print(f"  rendered / predicted, at the {len(amp)} cells where the cut moves at all:")
    for r, a in amp:
        print(f"      {r['tag']:>12}  cf {r['cf']:.5f}   dcut {r['dcut_db']:+7.4f} -> rendered "
              f"{r['rendered_worst_db']:6.4f} dB   ratio {a:.3f}")
    if amp:
        lo_a, hi_a = min(a for _r, a in amp), max(a for _r, a in amp)
        if hi_a <= 1.0:
            print(f"  ⇒ the rendered response moves LESS than the cut at all {len(amp)} "
                  f"(ratio {lo_a:.3f} .. {hi_a:.3f}) — the cut bound is CONSERVATIVE here, so")
            print("     BN2's arithmetic bar is the stricter statement and BN2 may be quoted.")
        else:
            print(f"  ⛔ AMPLIFIED: ratio reaches {hi_a:.3f} > 1 — a cut bound does NOT bound the")
            print("     rendered response, and BN2's arithmetic must not be quoted on its own.")
    if band:
        print(f"  ⚠ the band cells are UNCAPTURED settings: model-vs-model only, no reference "
              f"number exists at them.  Worst rendered |d| there: "
              f"{max(r['rendered_worst_db'] for r in band):.4f} dB.")
    out["bn4"] = {"cells": recs, "worst_mixed_rendered_db": worst_mixed_rendered,
                  "verdict": verdict, "grunt": grunt_apvts, "drive": drive}
    BM.CURVE_DIR = bm_dir


# =================================================================================================
def gate_bn5(out):
    print()
    print("=" * 100)
    print("BN5  VERDICT")
    print("=" * 100)
    b1, b2 = out["bn1"], out["bn2"]
    ok_cut = b2["verdict"] == "MET"
    ok_ren = out.get("bn4", {}).get("verdict", "MET") == "MET"
    print(f"  the re-anchor      kMixCf[0]  0.000000 -> {out['bn0']['kMixCf0_new']:.5f}")
    print(f"       (equivalently kMixS[0]   {0.951:.6f} -> {out['bn0']['kMixS0_new']:.6f})")
    print(f"  corner            : cut {out['bn0']['corner_cut_move_db']:+.4f} dB, restoring the "
          f"pre-s181 law to {out['bn3']['corner_restored_db']:.1e} dB")
    print(f"  verification cells: worst mixed |dcut| {b2['worst_mixed_db']:.6f} dB  "
          f"-> BAR {b2['verdict']}")
    if "worst_mixed_rendered_db" in out.get("bn4", {}):
        print(f"  rendered          : worst mixed |d| {out['bn4']['worst_mixed_rendered_db']:.5f}"
              f" dB  -> BAR {out['bn4']['verdict']}")
    print(f"  continuum         : {100 * b1['continuum_worst_frac']:.2f} % of LEVEL travel at "
          f"BLEND {b1['continuum_worst_blend']:.2f} is over the bar (worst "
          f"{b1['worst_dcut_db']:.3f} dB)")
    print()
    if ok_cut and ok_ren and b1["continuum_worst_frac"] > 0.0:
        print("  ⇒⇒ THE WORD `REACHABLE` HAS TWO READINGS HERE AND THEY DISAGREE.  That is the")
        print("     result; neither reading is a mistake, and the gate will not pick one.")
        print()
        print("     (i)  REACHABLE = CAPTURED.  Every mixed cell in GATE BM's grid and in every")
        print(f"          --set group clears the bar EXACTLY: worst |dcut| {b2['worst_mixed_db']:.6f} dB,")
        print("          and the three rendered mixed cells are bit-identical.  BAR MET.")
        print("     (ii) REACHABLE = DIALLABLE.  A LEVEL knob between the top two captured detents")
        print(f"          is reachable and uncaptured, and {100 * b1['continuum_worst_frac']:.1f} % of the knob's travel at")
        print(f"          BLEND max is over the bar (worst {b1['worst_dcut_db']:.2f} dB of cut).  BAR EXCEEDED.")
        print()
        print("     The two differ because the disturbed band is a GAP IN THE CAPTURE MATRIX: the")
        print("     LEVEL detents jump from cf 0.244 straight to the corner's 0.024, so nothing")
        print("     was ever captured in between.  ⛔ Reading (i) alone is the flattering one and")
        print("     must never be quoted without (ii).")
        print("     ⇒ SHIPPING THIS IS A USER DECISION, not a gate pass.")
    elif ok_cut and ok_ren:
        print("  ⇒ THE BAR IS MET EVERYWHERE, INCLUDING THE CONTINUUM.")
    else:
        print("  ⇒ THE BAR IS EXCEEDED.  The plain re-anchor is not shippable as it stands.")
    print()
    print("  ⛔ NOT MEASURED HERE, and not claimed: whether the re-anchored law is CLOSER to the")
    print("     pedal in that band.  Nothing was captured there, so nothing can say.  What the")
    print("     re-anchor does is put both endpoints of the segment on reachable settings; the")
    print("     shipped segment's left endpoint is a dead node.  That is an argument, not a")
    print("     measurement, and it decides nothing on its own.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-render", action="store_true", help="skip BN4 (arithmetic only)")
    ap.add_argument("--json", default="analysis/reports/s185_reanchor.json")
    args = ap.parse_args()

    T = F.shipped_tables()
    e_hi, _e_lo, _k = K._endstop(None)
    src = open(HDR_FIT).read()
    m = re.search(r"double\s+odNotchDepthDb\s*=\s*([-\d.eE+]+)", src)
    if not m:
        sys.exit(f"GATE BN: cannot find odNotchDepthDb in {HDR_FIT}")
    depth_off = float(m.group(1))

    print("GATE BN — re-anchoring OdToneRestore's dead kMixS[0] node (item 19 task P2)")
    state, cand, base = anchor_state(T, e_hi)
    out = {"state": state}
    gate_bn0(T, e_hi, depth_off, state, cand, base, out)
    cf_bar, rows = gate_bn1(T, e_hi, depth_off, cand, base, out)
    gate_bn2(T, e_hi, depth_off, cand, base, rows, out)
    gate_bn3(T, e_hi, depth_off, cand, base, rows, out)
    gate_bn4(T, e_hi, depth_off, cand, base, state, cf_bar, out, not args.no_render)
    gate_bn5(out)

    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print(f"\n  report -> {args.json}")


if __name__ == "__main__":
    main()
