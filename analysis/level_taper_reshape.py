#!/usr/bin/env python3.11
"""GATE AY -- task D: can a reshaped LEVEL TAPER deliver the pedal's LEVEL law, and what does it
cost everything else?

Session 162.  No render of its own: a re-read of a matrix report already on disk plus closed-form
evaluation of the shipped `LevelBlend` stage.  Imports `level_law_gate` (GATE K) and
`level_taper_gate` (GATE L) rather than re-deriving anything they established, so the three cannot
drift.

WHY THIS EXISTS, AND WHY IT IS NOT A RE-RUN OF GATE K's OWN TAPER QUESTION
-------------------------------------------------------------------------
Open work item 9 was redirected by the user at s160 from "discriminate GATE L4's (a) topology
mismatch vs (b) a level-dependent downstream stage" to "apply an artificial correction to the
measured LEVEL-sensitivity gap instead" (task D, 1 fit, no release-gate expectation).

Before reaching for an artificial correction this gate asks the cheaper question the project has
on record as CLOSED, because the premise behind that closure has expired
(`verify-the-PREMISE-not-the-prior-session's-framing-of-it`):

    GATE K (s103):  "THE TAPER CANNOT FIX IT ... the best exponent reaches only rms 1.85 dB and
                     lands 3.8 dB short at LEVEL max."
    GATE L (s104):  the network cannot produce the pedal's ladder under ANY taper and ANY bleed.

Both were measured on `s99_attack_cand.json`.  Since then the project has shipped `kInputRef`
(s109), `kOutputMakeup` + the MASTER PWL (s115), the D1/D2 clamp window (s118), the `rtsafe` solve
(s120), ADAA + `clipK` (s124), the 3-segment MASTER taper (s146) and the `OdToneRestore` stage
(s150/s151/s156).  Two of GATE K's three load-bearing numbers move with those: the LEVEL-max
shortfall was 3.8 dB and the above-noon stimulus dependence was the reason a taper was said to be
structurally incapable.

⭐ AND THE DISTINCTION GATE K's ARITHMETIC DID NOT DRAW.  GATE K fitted a single power-law
EXPONENT.  `FitParams.h`'s own MASTER block records what happened when that same family was
pressed on the neighbouring pot: "the per-point exponents are 1.929 / 2.322 / 1.734 ... NON-
MONOTONE, so no power law of any exponent fits all three", and s115/s146 replaced it with a
segmented PWL.  "No single exponent reaches" and "no monotone taper reaches" are different claims
and only the first was ever measured for LEVEL.

WHAT THIS GATE MEASURES, AND WHY IT IS A SOLVE RATHER THAN A FIT
---------------------------------------------------------------
A taper re-fit is a REPARAMETERISATION OF THE KNOB AXIS.  The stage's output depends on the knob
only through L, so the map

    L  ->  band-mean output level

is a property of the NETWORK plus everything downstream of it, and a taper change does not move it
at all -- it only changes which L each knob position selects.  So the required taper needs no fit
and no nuisance parameter:

    1. read the model's own rendered law at the 9 ladder detents.  Those detents sample
       dB_model(L) at L = x^2.25, nine points.
    2. interpolate dB_model(L) (monotone, in log L).
    3. INVERT it at the pedal's own measured levels.  The answer is the taper the pedal's ladder
       requires, L*(x).

⚠ Both sides are read RELATIVE TO LEVEL MAX, not relative to noon as GATE K3 prints them, and that
choice is forced rather than stylistic.  L(1) = 1 exactly is what makes `b(1) = 0` exactly, and
that exact zero is the bleed-free endpoint every absolute instrument in the project anchors on
(GATE K7's ratio, GATE O's A3 ledger, GATE L's |rho|, `OdToneRestore`'s base row, GATE W/AE's
bleed-free membership).  A taper is therefore not free at the top of its travel, so the top is the
anchor and everything else is measured from it.

⭐ THE KNOWN ANSWER IS FREE AND IT IS NOT A FIXED POINT.  Run the solve against the MODEL's own
levels and it must return the SHIPPED taper, L*(x) = x^2.25, to interpolation error.  Nothing is
seeded with the answer -- an inversion has no starting vector -- so unlike GATE L3's first draft
this cannot be a fixed point (`known-answer-must-not-start-at-its-answer`).

⭐⭐ AND THE ARCHITECTURAL FLOOR COMES OUT IN THE CONSTANT'S OWN UNITS.  The four stimulus levels
give four required tapers.  A taper cannot depend on the stimulus (GATE L6's refutation of the
model form), so a knob-keyed correction can deliver only their mean and the SPREAD is its residual
floor.  Reporting that spread beside the defect is what decides whether task D is well posed at
all -- the same test that closed task A one session ago, where the shipped error turned out to be
smaller than the target's own across-stimulus spread at 3 of 3 rungs.

GATES (all computed, exits non-zero on failure)
-----------------------------------------------
AY1   the imports and the invariant.  `L.a_of`/`L.b_of` must reproduce `K.coef_closed` (GATE L1's
      check, re-run here so this tool cannot be run against a drifted pair), the shipped
      `levelTaperExp` must match `FitParams.h` (K's own checker), and b(1) must be EXACTLY 0 --
      the invariant the whole anchor choice rests on.  Mutation: b must be non-zero at noon.
AY1b  EPOCH.  An absolute-ledger read is only valid against a report rendered from the current
      `src/`.  The report must postdate every `src/dsp/*.h` and the render binary, and no capture
      it reads may postdate the report (s110 R3b, the mirror direction).  REFUSES rather than
      warning: this gate's whole output is a per-detent level, and a stale epoch moves levels.
AY2   THE REQUIREMENT, per detent, referred to LEVEL max: the pedal's level, the model's, the
      defect, the across-stimulus SPREAD, and a computed per-detent verdict.  This is the screen
      that decides whether anything below is worth reading.
AY3   REACHABILITY, three families on the same objective: the shipped exponent, the best single
      exponent (GATE K's family, re-asked on this epoch), and a free monotone curve (the solve).
      Includes the known answer against the model's own levels.
AY4   the recovered curve's own properties -- monotone, endpoints exact, and the half-rotation
      fraction against the textbook A-taper 10-15 % band, which is the outside corroboration s146
      used for MASTER and which no term of this solve knows about.
AY5   CONSEQUENCES, priced before anything is built: the clean-fraction shift at every detent
      (which is what `OdToneRestore`'s shipped mix law reads, so a taper change re-stales it), and
      the mix-ratio span change against item 9's own ~2-3x LEVEL-sensitivity target.
AY6   what it must NOT move: the bleed-free corner must be bit-identical, asserted.

Run:
    python3.11 analysis/level_taper_reshape.py analysis/reports/s162_shipped.json
    python3.11 analysis/level_taper_reshape.py REPORT.json --json analysis/reports/s162_level_taper.json
"""
import argparse
import glob
import json
import math
import os
import sys

import numpy as np

import matrix_grade as MG
import level_law_gate as K
import level_taper_gate as L

NOON = K.NOON
TOP = 1.0                       # the anchor: L(1) = 1 exactly, so b(1) = 0 exactly
SWEEPS = L.SWEEPS

# ⚠ s163 made the shipped taper a CALLABLE (a segmented PWL), not an exponent, so it has no
# printable or JSON-serialisable value.  Three sites still carried an f-string that assumed a
# float: two printed `p = <function level_taper at 0x...>` into the verdict text, and the third
# put the function object into the report, where `json.dump` CRASHED -- so this gate has been
# unable to write its own artefact since s163, and the crash sits after every verdict has
# printed, which is exactly why nobody noticed.  One name, DERIVED from the shipped parameter
# list rather than transcribed, so it cannot go stale again when the segment count next moves.
P_LABEL = f"{len(K.LEVEL_TAPER_NAMES) // 2 + 1}-seg PWL"

# Textbook audio-taper band at half rotation, as used by s146 for the MASTER pot
# (`analysis/master_taper_makeup.py`).  A BAND, not a target: nothing here is fitted to it, which
# is exactly what makes it usable as outside corroboration.
A_TAPER_LO, A_TAPER_HI = 0.10, 0.15

# The MUTE threshold, in ONE place because two sub-gates disagreed about it.  A model level below
# this is digital silence, not a level: `LevelBlend` gives a = b = 0 exactly at LEVEL min with
# BLEND max, so the rendered detent is a numerical zero and any dB difference taken against it is
# `ratio-statistics-need-a-denominator-guard`.  AY3's `build_dB_of_L` excluded it from the start and
# AY2's first draft did not, so AY2 published a 214 dB "requirement" that AY3's own objective was
# already dropping -- the two sub-gates disagreeing on membership is the tell.
MUTE_DB = -100.0

SRC_GLOBS = ("src/dsp/*.h", "src/*.cpp", "analysis/offline_render.cpp")
RENDER_BIN = "build/OfflineRender_artefacts/Release/OfflineRender"


# --------------------------------------------------------------------------------------------
# AY1 -- imports and the invariant
# --------------------------------------------------------------------------------------------
def gate_ay1(out):
    print("-- AY1: imported coefficients, the shipped constant, and the anchor invariant --")
    K.check_shipped_constant()
    # ⚠ s163: the shipped taper is a 4-segment PWL, so `p` is a CALLABLE knob -> L, not an
    # exponent.  Everything below maps detents through it; a report from an earlier epoch must be
    # read with THAT epoch's curve instead (`K.power_taper`), which AY1b's guard enforces by
    # refusing a stale report outright.
    p = K.level_taper
    # ⚠ s173: and because it is a callable, it has no printable/serialisable VALUE.  Three sites
    # inherited an f-string that assumed a float and were emitting `p = <function level_taper at
    # 0x...>` into the report text -- and the JSON dump CRASHED on it, so this gate had not been
    # able to write its own artefact since s163 (the crash is at the very end, after every verdict
    # has printed, which is exactly why it went unnoticed).  One name, used everywhere.

    worst = 0.0
    for Lv in np.linspace(0.0, 1.0, 1001):
        a, b = K.coef_closed(1.0, float(Lv))
        worst = max(worst, abs(a - L.a_of(Lv)), abs(b - L.b_of(Lv)))
    if worst > 1e-15:
        sys.exit(f"GATE AY1 FAIL: level_taper_gate's reduction and level_law_gate's coef_closed "
                 f"disagree by {worst:.3e} -- one of the two imported modules has drifted, so "
                 f"nothing here may be quoted")
    print(f"  AY1 OK  L.a_of/L.b_of == K.coef_closed to {worst:.2e} over 1001 points (imported, "
          f"not retyped)")

    if L.b_of(1.0) != 0.0:
        sys.exit("GATE AY1 FAIL: the clean coefficient is not EXACTLY 0 at LEVEL max -- the "
                 "bleed-free anchor this gate measures everything against does not exist")
    if L.b_of(p(NOON)) <= 0.0:
        sys.exit("GATE AY1 FAIL: the clean coefficient is 0 at noon too, so there is no bleed "
                 "anywhere and this gate is testing nothing (empty-gate-must-fail)")
    print(f"  MUTATION OK  b(1) is exactly 0 and b(noon) = {L.b_of(p(NOON)):.4f}, so the anchor "
          f"is a real\n               exact zero and not a coincidence of the taper.")
    out["ay1"] = {"coef_agreement": worst, "taper": list(K.SHIPPED_LEVEL_TAPER),
                  "b_at_noon": L.b_of(p(NOON))}
    return p


# --------------------------------------------------------------------------------------------
# AY1b -- epoch
# --------------------------------------------------------------------------------------------
def gate_ay1b(path, caps, out):
    print("\n-- AY1b: epoch -- was this report rendered from the CURRENT src/? --")
    rep_m = os.path.getmtime(path)
    srcs = [f for g in SRC_GLOBS for f in glob.glob(g)]
    if not srcs:
        sys.exit("GATE AY1b FAIL: no src/ files found -- run from the repo root; this gate "
                 "cannot certify an epoch it cannot see")
    newer = [(f, os.path.getmtime(f)) for f in srcs if os.path.getmtime(f) > rep_m]
    binm = os.path.getmtime(RENDER_BIN) if os.path.exists(RENDER_BIN) else None
    if binm is not None and binm > rep_m:
        newer.append((RENDER_BIN, binm))
    if newer:
        names = ", ".join(os.path.basename(f) for f, _ in sorted(newer, key=lambda t: -t[1])[:4])
        sys.exit(f"GATE AY1b FAIL: {len(newer)} source/binary file(s) POSTDATE {path} ({names}) "
                 f"-- every number this gate prints is an absolute level, and a stale epoch moves "
                 f"levels.  Re-render the matrix before reading this.  This is a REFUSAL, not a "
                 f"warning: s118 retracted a whole synthesis built on a stale-epoch absolute read.")
    print(f"  AY1b OK report postdates all {len(srcs)} src/ files and the render binary")

    # The mirror direction (s110 R3b): a capture re-recorded after the report was written would be
    # read live here while the model column came from before it.
    stale = []
    for f in caps:
        for d in ("analysis/captures", "analysis/captures/_archive"):
            q = os.path.join(d, f)
            if os.path.exists(q) and os.path.getmtime(q) > rep_m:
                stale.append(f)
                break
    if stale:
        sys.exit(f"GATE AY1b FAIL: {len(stale)} capture(s) postdate the report, e.g. "
                 f"{stale[:3]} -- the pedal side and the model side are different epochs")
    print(f"  AY1b OK no capture postdates the report ({len(caps)} checked, both directions)")
    out["ay1b"] = {"report_mtime": rep_m, "n_src": len(srcs), "n_caps": len(caps)}


# --------------------------------------------------------------------------------------------
# the ladder, referred to LEVEL max
# --------------------------------------------------------------------------------------------
def read_ladder(path, out):
    """-> (detents, {sweep: {x: (model_dB_re_max, pedal_dB_re_max)}}, ladder settings)

    Membership comes from GATE K's own 13-key `find_level_groups` and GATE L's endpoint rules --
    never a filename substring (s114) -- and the pure-clean/pure-OD endpoint captures are located
    by GATE L2 so |rho| below is measured at the ladder's own operating point."""
    bands, caps = MG.load(path)[0], MG.load(path)[1]
    idx = MG.graded_band_idx(bands) if hasattr(MG, "graded_band_idx") else None
    return bands, caps, idx


def ladder_re_top(absfr, ladder, nonhf):
    res = {}
    for sw in SWEEPS:
        pts = {}
        for x, f in ladder:
            if (f, sw) not in absfr:
                continue
            m, q = absfr[(f, sw)]
            pts[x] = (float(np.mean(m[nonhf])), float(np.mean(q[nonhf])))
        if TOP in pts:
            m0, q0 = pts[TOP]
            res[sw] = {x: (m - m0, q - q0) for x, (m, q) in pts.items()}
    return res


def gate_ay2(res, ladder, out):
    print("\n-- AY2: THE REQUIREMENT, per detent, referred to LEVEL max (the anchor) --")
    print("    dB RELATIVE TO LEVEL MAX.  'need' = pedal - model = the gain the model is short by.")
    print(f"    {'LEVEL':>7} |{'  pedal (mean)':>15}{'  model (mean)':>15}{'   need':>9}"
          f"{'  spread':>9}{'   verdict':>14}")
    rows, ok, amb, mutes = {}, [], [], []
    for x, _f in ladder:
        pairs = [res[sw][x] for sw in SWEEPS if sw in res and x in res[sw]
                 and all(np.isfinite(res[sw][x]))]
        if not pairs:
            print(f"    {x:7.3f} |{'':>15}{'   -inf (mutes)':>15}{'':>9}{'':>9}"
                  f"{'NOT MEASURABLE':>14}")
            rows[x] = {"measurable": False}
            continue
        need = [q[1] - q[0] for q in pairs]
        ped = [q[1] for q in pairs]
        mod = [q[0] for q in pairs]
        # FOURTH outcome, and it is not a level requirement at all.  A model level below MUTE_DB is
        # digital silence, so 'need' there is a difference against a numerical zero: it scales with
        # nothing physical and it is NOT taper-reachable in either direction, because a pot's wiper
        # reaches its end stop and L(0) = 0 EXACTLY under every taper.  A solve asking for L(0) > 0
        # is asking for a pot that does not fully attenuate, which is a TOPOLOGY change (an end-stop
        # resistance, or GATE K2's BLEND-body bleed path), not a reparameterisation of the knob.
        if min(mod) < MUTE_DB:
            print(f"    {x:7.3f} |{np.mean(ped):15.2f}{min(mod):15.2f}{'':>9}{'':>9}"
                  f"{'MODEL MUTES':>14}")
            rows[x] = {"measurable": False, "mutes": True, "pedal": float(np.mean(ped)),
                       "model_min": float(min(mod))}
            mutes.append(x)
            continue
        mn, sp = float(np.mean(need)), float(max(need) - min(need))
        # Computed verdict.  A knob-keyed correction delivers the MEAN of the four stimulus
        # levels; the SPREAD is what it cannot deliver, so it is the residual floor in the
        # correction's own units.  Three outcomes, not two: a detent needing nothing is not
        # ambiguous, it is already right.
        if abs(mn) <= sp * 0.5:
            v = "NOTHING TO DO" if abs(mn) < 0.5 else "AMBIGUOUS"
        else:
            v = "WELL-DEFINED"
        (ok if v == "WELL-DEFINED" else amb).append(x)
        rows[x] = {"measurable": True, "pedal": float(np.mean(ped)), "model": float(np.mean(mod)),
                   "need_mean": mn, "need_spread": sp, "need_per_sweep": need, "verdict": v}
        print(f"    {x:7.3f} |{np.mean(ped):15.2f}{np.mean(mod):15.2f}{mn:9.2f}{sp:9.2f}{v:>14}")

    if not ok:
        sys.exit("GATE AY2 FAIL: no detent has a requirement larger than its own across-stimulus "
                 "spread -- a knob-keyed correction is inside the ambiguity of the thing it would "
                 "be fitting at EVERY detent, so task D is not well posed and nothing below is "
                 "worth reading (this is task A's closing argument, and it would apply here too)")
    print(f"\n    AY2: {len(ok)} of {len(ok) + len(amb)} measurable detents have a requirement "
          f"LARGER than their own\n         across-stimulus spread -- WELL-DEFINED at {sorted(ok)}.")
    worst = max((abs(rows[x]["need_mean"]) for x in ok), default=0.0)
    print(f"         Largest well-defined requirement: {worst:.2f} dB.")
    if mutes:
        print(f"\n    ⚠⚠ EXCLUDED, NAMED, NOT DROPPED -- the model MUTES at LEVEL {sorted(mutes)},")
        for x in sorted(mutes):
            print(f"       reading {rows[x]['model_min']:.1f} dB against a pedal that is only "
                  f"{rows[x]['pedal']:.2f} dB below its own max.")
        print("       That is a REAL defect and it is NOT this gate's subject: a taper cannot reach")
        print("       it (L(0) = 0 exactly at the end stop, under every taper), so it is excluded")
        print("       from the requirement above and from AY3's objective -- which is the SAME")
        print("       membership AY3 already used, and the first draft's disagreement between the")
        print("       two is what found it.  It needs a TOPOLOGY change (an end-stop resistance, or")
        print("       GATE K2's BLEND-body bleed path), and it is filed as its own finding.")
    out["ay2"] = {"rows": {str(k): v for k, v in rows.items()},
                  "well_defined": sorted(ok), "ambiguous": sorted(amb), "worst_need": worst,
                  "mutes": sorted(mutes)}
    return rows


# --------------------------------------------------------------------------------------------
# AY3 -- reachability: the solve, and the two power-law families
# --------------------------------------------------------------------------------------------
def build_dB_of_L(res, sw, ladder, p):
    """The model's own map L -> band-mean dB re LEVEL max, from the rendered detents.

    This is the whole reason a taper question needs no fit: the knob enters the stage ONLY through
    L, so this map belongs to the network and everything downstream of it, and a taper change
    cannot move it.  It is sampled at exactly the L values the shipped taper selects."""
    pts = []
    for x, _f in ladder:
        if x not in res[sw]:
            continue
        m, _q = res[sw][x]
        if not np.isfinite(m) or m < MUTE_DB:
            continue
        pts.append((p(x), m))
    pts.sort()
    Ls = np.array([t[0] for t in pts])
    dB = np.array([t[1] for t in pts])
    return Ls, dB


def invert_dB(Ls, dB, target):
    """L such that dB_model(L) = target, by monotone interpolation in log L.

    Returns (L, status) with status one of 'interp' / 'below' / 'above' -- an extrapolation is
    reported rather than silently returned, because 'the taper cannot reach this' is a RESULT
    (s134: the absence of a root in the swept range is a computed verdict, not a malfunction)."""
    if not np.all(np.diff(dB) > 0):
        return float("nan"), "non-monotone"
    if target <= dB[0]:
        return float(Ls[0]), "below"
    if target >= dB[-1]:
        return float(Ls[-1]), "above"
    lo = np.log(np.maximum(Ls, 1e-12))
    return float(math.exp(float(np.interp(target, dB, lo)))), "interp"


def gate_ay3(res, ladder, p, rows, out):
    print("\n-- AY3: reachability -- the solve, and the power-law family GATE K tested --")

    # ---- the known answer, first: solve against the MODEL's own levels -------------------
    print("\n    KNOWN ANSWER: solving against the MODEL's own levels must return the SHIPPED")
    print("    taper.  An inversion has no starting vector, so this cannot be a fixed point.")
    worst_ka, n_ka, ka_sweeps = 0.0, 0, []
    for sw in SWEEPS:
        if sw not in res:
            continue
        Ls, dB = build_dB_of_L(res, sw, ladder, p)
        hits = 0
        for x, _f in ladder:
            if x not in res[sw] or not np.isfinite(res[sw][x][0]) or res[sw][x][0] < MUTE_DB:
                continue
            got, st = invert_dB(Ls, dB, res[sw][x][0])
            want = p(x)
            # A column with no inversion AT ALL contributes nothing here, and must be skipped
            # BEFORE the `want == 0` allowance below -- that allowance exists to admit the L = 0
            # detent, where the status is legitimately 'below' rather than 'interp', and a first
            # draft let it admit 'non-monotone' too.  Found by `_mutate_gate_ay.py::ay2-mute`,
            # which reaches this path by declassifying the mute; unmutated it is unreachable, so
            # the guard was correct only by accident of an upstream filter.
            if st == "non-monotone":
                continue
            if st != "interp" and want != 0.0:
                continue
            # isfinite FIRST and explicitly: `nan > 1e-9` is False, so a non-finite recovery would
            # sail through the tolerance below and the known answer would pass having checked
            # nothing (s106 GATE N3 -- every comparison against nan fails OPEN, the flattering way).
            if not np.isfinite(got):
                sys.exit(f"GATE AY3 FAIL: the known answer recovered a non-finite L at "
                         f"{sw} x={x} (status {st!r}) -- a nan cannot be compared against a "
                         f"tolerance, so this would have passed vacuously")
            worst_ka = max(worst_ka, abs(got - want))
            hits += 1
        if hits:
            n_ka += hits
            ka_sweeps.append(sw)
    if n_ka == 0:
        sys.exit("GATE AY3 FAIL: the known answer checked ZERO points -- it cannot pass or fail, "
                 "so nothing below is licensed (`empty-gate-must-fail`)")
    if worst_ka > 1e-9:
        sys.exit(f"GATE AY3 FAIL: the solve does not return the shipped taper when run against "
                 f"the model's own levels (worst {worst_ka:.3e}) -- the inversion is wrong, so "
                 f"the recovered taper below is not a measurement")
    # Say how many points and WHICH columns, rather than 'all 4 stimulus levels' -- a refused
    # column contributes nothing here and the first draft claimed it anyway.
    print(f"    AY3 OK  recovers the shipped {P_LABEL} to {worst_ka:.2e} over {n_ka} "
          f"(detent x stimulus) "
          f"points\n            in {len(ka_sweeps)} of {len(SWEEPS)} columns: "
          f"{', '.join(s.replace('sweep_', '') for s in ka_sweeps)}")

    # ---- the required taper, per stimulus level -------------------------------------------
    # ---- WHICH stimulus levels can be inverted AT ALL -- named, before the table -----------
    # The inversion needs dB_model(L) strictly monotone.  Where it is not, the whole COLUMN is
    # refused, and a refused column is a membership statement about the floor computed below --
    # not a nan to print silently (s133: a silent estimator and an absent feature look alike).
    usable, refused = [], []
    for sw in SWEEPS:
        if sw not in res:
            refused.append((sw, "no data")); continue
        Ls, dB = build_dB_of_L(res, sw, ladder, p)
        (usable if np.all(np.diff(dB) > 0) else refused).append(
            sw if np.all(np.diff(dB) > 0) else (sw, "dB_model(L) NON-MONOTONE -- not invertible"))
    if not usable:
        sys.exit("GATE AY3 FAIL: no stimulus level has an invertible level law, so there is no "
                 "required taper to recover at all")
    if refused:
        print("\n    ⚠⚠ COLUMNS REFUSED, and this changes what the floor below means:")
        for sw, why in refused:
            print(f"       {sw:<16} {why}")
        hot = SWEEPS[-1]
        if any(sw == hot for sw, _ in refused):
            print(f"       The refused set includes the HOTTEST stimulus ({hot}) -- the column most")
            print( "       likely to disagree with the others (GATE K3/L8: the model's H1 FALLS above")
            print( "       LEVEL noon because b(L) peaks at 0.5, and hard enough at the hottest rung")
            print( "       to break monotonicity outright).  ⇒ THE SPREAD PRINTED BELOW IS A LOWER")
            print( "       BOUND ON THE ARCHITECTURAL FLOOR, not a measurement of it.")

    print("\n    THE REQUIRED TAPER L*(x), solved per stimulus level.  A taper cannot depend on")
    print(f"    the stimulus (GATE L6), so the SPREAD across the {len(usable)} usable column(s) is the")
    print("    floor a knob-keyed curve cannot beat -- the architectural limit in the constant's units.")
    print(f"    {'LEVEL':>7}{'shipped':>10} |" +
          "".join(f"{s.replace('sweep_', ''):>10}" for s in SWEEPS) +
          f" |{'mean':>9}{'spread':>9}{'  reach':>22}")
    need_tap, unreach = {}, []
    for x, _f in ladder:
        if not rows.get(x, {}).get("measurable"):
            continue
        vals, sts = [], []
        for sw in SWEEPS:
            if sw not in usable or x not in res[sw]:
                vals.append(float("nan")); continue
            Ls, dB = build_dB_of_L(res, sw, ladder, p)
            got, st = invert_dB(Ls, dB, res[sw][x][1])
            vals.append(got); sts.append(st)
        good = [v for v in vals if np.isfinite(v)]
        if not good:
            continue
        mean, spread = float(np.mean(good)), float(max(good) - min(good))
        # 'reach' is a statement about the USABLE columns only -- a refused column is reported
        # once, above, and must not reappear here as a per-detent verdict.
        st = "OK" if all(s == "interp" for s in sts) else "/".join(sorted(set(sts)))
        if st != "OK":
            unreach.append((x, st))
        need_tap[x] = {"per_sweep": vals, "mean": mean, "spread": spread, "status": st}
        shipped = p(x)
        print(f"    {x:7.3f}{shipped:10.4f} |" +
              "".join("       -- " if not np.isfinite(v) else f"{v:10.4f}" for v in vals) +
              f" |{mean:9.4f}{spread:9.4f}{st:>22}")

    mono = all(need_tap[a]["mean"] < need_tap[b]["mean"] + 1e-12
               for a, b in zip(sorted(need_tap), sorted(need_tap)[1:]))
    print(f"\n    The required curve L*(x) is {'MONOTONE' if mono else 'NON-MONOTONE'} in the KNOB.")
    print("    ⚠ A DIFFERENT monotonicity from the refused columns above, which is about")
    print("      dB_model(L) at fixed knob.  Two properties, one word -- printed adjacently in the")
    print("      first draft, where they read as a contradiction (s122: a message that could not be")
    print("      true is a defect in the test, even when the tool is sound).")
    if not mono:
        print("    ⚠ A NON-MONOTONE requirement cannot be a pot taper at all, whatever its shape,")
        print("      so a taper is refuted here and the correction must be something else.")

    # ---- the power-law family, re-asked on this epoch ------------------------------------
    print("\n    What a SINGLE EXPONENT can reach -- GATE K's own family, re-asked on this epoch.")
    print("    Objective: rms over the WELL-DEFINED detents of (delivered - pedal) in dB,")
    print("    stimulus-averaged.  The shipped exponent is scored first as the baseline.")

    def score(exp_or_curve):
        # Scored over the USABLE columns only -- the same membership the table above prints, taken
        # from the same list rather than re-derived, so the two cannot drift.
        errs = []
        for sw in usable:
            Ls, dB = build_dB_of_L(res, sw, ladder, p)
            lo = np.log(np.maximum(Ls, 1e-12))
            for x, _f in ladder:
                if not rows.get(x, {}).get("measurable") or x <= 0.0:
                    continue
                Lx = (x ** exp_or_curve) if np.isscalar(exp_or_curve) else (
                    exp_or_curve(x) if callable(exp_or_curve) else exp_or_curve[x])
                got = float(np.interp(math.log(max(Lx, 1e-12)), lo, dB))
                errs.append(got - res[sw][x][1])
        return (float(np.sqrt(np.mean(np.square(errs)))), float(np.max(np.abs(errs))), len(errs))

    ship_rms, ship_worst, n_err = score(p)
    grid = np.linspace(0.8, 4.0, 3201)
    scored = [(score(float(e))[0], float(e)) for e in grid]
    best_rms, best_exp = min(scored)
    best_worst = score(best_exp)[1]
    curve_rms, curve_worst, _ = score({x: need_tap[x]["mean"] for x in need_tap})
    # The floor computed INDEPENDENTLY of the objective, in the same units: a knob-keyed curve can
    # deliver only the stimulus mean, so the per-detent SPREAD is what it structurally cannot.
    # ⚠ Over the detents the solve actually reaches, EXCLUDING the anchor (spread 0 by construction
    # -- including it deflates the rms and would flatter the floor).
    sp = [need_tap[x]["spread"] for x in need_tap if x < TOP]
    floor = float(np.sqrt(np.mean(np.square(sp))))
    floor_worst = float(max(sp)) if sp else 0.0

    print(f"\n    {'family':<34}{'rms dB':>9}{'worst dB':>10}")
    print(f"    {'shipped (' + P_LABEL + ')':<34}{ship_rms:9.3f}{ship_worst:10.3f}")
    print(f"    {'best single exponent, p = ' + f'{best_exp:.4f}':<34}{best_rms:9.3f}{best_worst:10.3f}")
    print(f"    {'free monotone curve (the solve)':<34}{curve_rms:9.3f}{curve_worst:10.3f}")
    print(f"    (n = {n_err} (detent x usable stimulus) errors per family, "
          f"{len(usable)} of {len(SWEEPS)} stimulus levels)")
    print(f"\n    The free curve's residual is NOT zero even though it was solved per detent:")
    print( "    it delivers the stimulus MEAN and the usable columns disagree.")
    print(f"    ⇒ TWO floors, and they are different quantities -- print both:")
    print(f"        the solve's own residual, in dB of delivered level : {curve_rms:.3f} rms")
    print(f"        the required-taper SPREAD, in units of L           : {floor:.4f} rms, "
          f"{floor_worst:.4f} worst")
    print( "      The first is what a knob-keyed curve would actually miss by; the second is the")
    print( "      same limit measured on the constant itself, and neither is a re-statement of the")
    print( "      other.  It is the limit `OdToneRestore` hit (s151 §6) and the one that closed")
    print( "      task A (s161) -- and here it is a LOWER bound, per the refused column above.")

    # ---- THE COMPUTED VERDICT on the three families ---------------------------------------
    # This is the statement the gate exists to make, and the first draft printed three numbers and
    # left the comparison to the reader -- `computed-verdicts-not-narrated`, in the one place it
    # decides an open work item.  GATE K closed this question on the EXPONENT family alone, and
    # "no single exponent reaches" is a different claim from "no monotone taper reaches".
    #
    # ⭐ The bar is NOT invented: it is AY2's own per-detent across-stimulus spread, in the SAME
    # units (dB), rms'd over the same well-defined detents.  A family whose residual is inside that
    # is as close as the target itself is defined -- which is exactly the test that closed task A
    # one session ago (s161 AX6), imported rather than re-derived.
    amb = [rows[x]["need_spread"] for x in rows
           if rows[x].get("measurable") and rows[x].get("verdict") == "WELL-DEFINED"]
    amb_rms = float(np.sqrt(np.mean(np.square(amb)))) if amb else float("nan")
    print(f"\n    VERDICT, against the target's OWN across-stimulus ambiguity ({amb_rms:.3f} dB rms,")
    print( "    AY2's spread column -- not a bar this gate chose):")
    fam_v = {}
    for label, rms in (("shipped exponent", ship_rms), ("best single exponent", best_rms),
                       ("free monotone curve", curve_rms)):
        inside = rms <= amb_rms
        fam_v[label] = bool(inside)
        print(f"      {label:<22}{rms:8.3f} dB  "
              f"{'INSIDE the ambiguity' if inside else f'OUTSIDE it by {rms / amb_rms:.2f}x'}")
    if fam_v["free monotone curve"] and not fam_v["best single exponent"]:
        print("\n    ⇒ THE FAMILY IS WHAT DECIDES IT, not the fit: a free monotone taper lands")
        print("      INSIDE the target's own ambiguity where NO single exponent does.  GATE K's")
        print("      closure (`THE TAPER CANNOT FIX IT`) was measured on the exponent family, and")
        print("      it does not carry over to a segmented curve -- the distinction s115/s146 had")
        print("      already been forced to draw on the neighbouring MASTER pot.")
    elif fam_v["best single exponent"]:
        print("\n    ⇒ AN EXPONENT IS ENOUGH -- the segmented family buys nothing here, so GATE K's")
        print("      question needed only re-asking on this epoch, not a richer family.")
    else:
        print("\n    ⇒ NO family tested reaches the target's own ambiguity, so GATE K's closure")
        print("      (`THE TAPER CANNOT FIX IT`) STANDS on this epoch, for the free curve too.")
    out["ay3"] = {"known_answer": worst_ka, "required_taper": {str(k): v for k, v in need_tap.items()},
                  "monotone": bool(mono), "unreachable": [(x, s) for x, s in unreach],
                  "shipped": {"family": P_LABEL, "rms": ship_rms, "worst": ship_worst},
                  "best_exp": {"exp": best_exp, "rms": best_rms, "worst": best_worst},
                  "free_curve": {"rms": curve_rms, "worst": curve_worst},
                  "spread_floor_rms": floor, "spread_floor_worst": floor_worst,
                  "ambiguity_rms_db": amb_rms, "family_inside_ambiguity": fam_v,
                  "usable_sweeps": list(usable), "refused_sweeps": [s for s, _ in refused],
                  "n_scored": n_err}
    return need_tap, mono, (ship_rms, best_rms, best_exp, curve_rms)


# --------------------------------------------------------------------------------------------
# AY4 -- the recovered curve's own properties
# --------------------------------------------------------------------------------------------
def gate_ay4(need_tap, p, out):
    print("\n-- AY4: the recovered curve's own properties (nothing below is fitted TO these) --")
    xs = sorted(need_tap)
    Lm = {x: need_tap[x]["mean"] for x in xs}

    if TOP in Lm and abs(Lm[TOP] - 1.0) > 1e-9:
        sys.exit(f"GATE AY4 FAIL: the recovered curve gives L(1) = {Lm[TOP]:.6f}, not exactly 1 "
                 f"-- the bleed-free anchor is not preserved and every absolute instrument in the "
                 f"project moves")
    print(f"  AY4 OK  L(1) = 1 exactly, so b(1) = 0 exactly and the bleed-free corner is intact")

    half = Lm.get(NOON)
    if half is not None:
        ship_half = p(NOON)
        band = A_TAPER_LO <= half <= A_TAPER_HI
        ship_band = A_TAPER_LO <= ship_half <= A_TAPER_HI
        print(f"\n  Half-rotation fraction -- the unit a pot is SPECIFIED in, and the same outside")
        print(f"  corroboration s146 used for the MASTER taper:")
        print(f"    shipped   L(0.5) = {ship_half * 100:.2f} %   "
              f"{'INSIDE' if ship_band else 'OUTSIDE'} the textbook A-taper "
              f"{A_TAPER_LO * 100:.0f}-{A_TAPER_HI * 100:.0f} % band")
        print(f"    required  L(0.5) = {half * 100:.2f} %   "
              f"{'INSIDE' if band else 'OUTSIDE'} it")
        moved_in = (not ship_band) and band
        # Derive the band's centre from the band, don't retype it: a literal 0.125 is silently
        # correct only while the band happens to be 10-15 %, and it is the kind of stale copy that
        # survives because nothing moves it (`rebuild-targets-dont-transcribe`).
        centre = (A_TAPER_LO + A_TAPER_HI) / 2.0
        moved_toward = abs(half - centre) < abs(ship_half - centre)
        print(f"    => the requirement moves the pot "
              f"{'INTO' if moved_in else ('TOWARD' if moved_toward else 'AWAY FROM')} the band "
              f"that `circuit.md` says\n       VR2 is (100k A).  Nothing in the "
              f"solve knows what an A taper is.")
        out.setdefault("ay4", {})["half_rotation"] = {
            "shipped": ship_half, "required": half, "in_band": bool(band),
            "shipped_in_band": bool(ship_band), "moved_toward": bool(moved_toward)}

    seg = [(b, (Lm[b] - Lm[a]) / (b - a)) for a, b in zip(xs, xs[1:])]
    rising = all(s2 >= s1 - 1e-12 for (_, s1), (_, s2) in zip(seg, seg[1:]))
    # SIZE the violation, don't just report its existence.  'NOT convex' covers both a curve that
    # genuinely turns over and one that dips by a fraction of a percent on a solve whose own inputs
    # are hand-set knob positions -- and those have completely different consequences.
    drops = [(b, s1, s2) for (_, s1), (b, s2) in zip(seg, seg[1:]) if s2 < s1 - 1e-12]
    worst_drop = max(((s1 - s2) / s1 for _, s1, s2 in drops), default=0.0)
    print(f"\n  Segment slopes: " + " ".join(f"{s:.3f}" for _, s in seg))
    print(f"  The curve is {'CONVEX (slopes rise monotonically)' if rising else 'NOT convex'} "
          f"-- a physically buildable\n  resistive track is convex, and s146 asserts exactly this "
          f"for the MASTER taper.")
    if drops:
        print(f"  ⚠ SIZE THE VIOLATION: {len(drops)} dip(s), worst {worst_drop * 100:.2f} % of the "
              f"preceding slope,")
        for b, s1, s2 in drops:
            print(f"      at x = {b:.3f}: {s1:.4f} -> {s2:.4f}")
        print( "    A sub-percent dip on a curve solved from HAND-SET knob positions is inside the")
        print(f"    input's own uncertainty (s146 measured that floor at 1.075 dB for MASTER); a")
        print( "    turnover is not.  Read the size, not the boolean.")
    out.setdefault("ay4", {}).update({"detents": xs, "L": {str(k): v for k, v in Lm.items()},
                                      "segment_slopes": [s for _, s in seg], "convex": bool(rising),
                                      "convexity_dips": [[b, s1, s2] for b, s1, s2 in drops],
                                      "worst_dip_frac": worst_drop})
    return Lm


# --------------------------------------------------------------------------------------------
# AY5 -- consequences, priced before anything is built
# --------------------------------------------------------------------------------------------
def gate_ay5(Lm, p, out):
    print("\n-- AY5: consequences -- what a taper change drags with it --")

    print("\n  (a) CLEAN FRACTION at BLEND max.  `OdToneRestore`'s shipped law (s156) reads")
    print("      `LevelBlend::cleanFraction()` and keys its 320 Hz cut on it, so moving L moves")
    print("      the stage's own input.  This is a COST, not a defect: it re-stales the s156 fit.")
    print(f"      {'LEVEL':>7}{'  cf shipped':>13}{'  cf required':>14}{'   d cf':>9}")
    worst_cf, cf_rows = 0.0, {}
    for x in sorted(Lm):
        a0, b0 = K.coef_closed(1.0, p(x))
        a1, b1 = K.coef_closed(1.0, Lm[x])
        cf0 = b0 / (a0 + b0) if (a0 + b0) > 0 else 1.0
        cf1 = b1 / (a1 + b1) if (a1 + b1) > 0 else 1.0
        worst_cf = max(worst_cf, abs(cf1 - cf0))
        cf_rows[x] = {"shipped": cf0, "required": cf1, "delta": cf1 - cf0}
        print(f"      {x:7.3f}{cf0:13.4f}{cf1:14.4f}{cf1 - cf0:9.4f}")
    print(f"      worst |d cleanFraction| = {worst_cf:.4f}")

    print("\n  (b) MIX-RATIO SPAN, i.e. the LEVEL sensitivity item 9 is written about.  The")
    print("      clean-re-OD ratio the stage mixes is exactly (1 - L) (GATE L's reduction), so a")
    print("      taper change is exactly a change in how fast the mix sweeps with the knob.")
    matched = [x for x in sorted(Lm) if 0.0 < x < 1.0]
    if matched:
        s_ship = [1.0 - p(x) for x in matched]
        s_req = [1.0 - Lm[x] for x in matched]
        span_ship = max(s_ship) - min(s_ship)
        span_req = max(s_req) - min(s_req)
        fold = span_req / span_ship if span_ship > 0 else float("nan")
        print(f"      (1-L) span over the interior detents: shipped {span_ship:.4f}, "
              f"required {span_req:.4f}")
        print(f"      => fold change {fold:.3f}x")
        print( "      ⚠ A SIZING, NOT A MECHANISM CLAIM (s134).  Item 9's target is a ~2-3x gap in")
        print( "      how far a FEATURE's centre moves across the matched LEVEL detents; this is")
        print( "      the fold change in the mix ratio that drives it, which is a NECESSARY")
        print( "      condition and not the feature measurement.  Whether the feature follows")
        print( "      needs GATE W's locator on a re-render, and this gate does not claim it.")

        # ---- (c) THE HEADROOM BOUND.  The decisive number, and it needs no fit, no threshold
        # and no choice of taper -- it holds over the WHOLE family at once (s145 AM4's pattern:
        # a bound proved over the parameter space does not expire when a constant moves).
        #
        #   L is a pot fraction, so L in [0, 1] and the mixed clean-re-OD ratio (1 - L) is in
        #   [0, 1] too.  A taper with the endpoints pinned -- and they ARE pinned: L(0) = 0 is the
        #   end stop and L(1) = 1 is the bleed-free anchor AY6 asserts -- can push the interior
        #   detents arbitrarily close to those two limits, so the SUPREMUM of the (1 - L) span over
        #   the interior detents is 1.0, approached and never attained.
        #
        # => the largest fold change ANY taper can deliver is 1 / span_shipped.
        sup_fold = 1.0 / span_ship if span_ship > 0 else float("inf")
        print("\n  (c) THE HEADROOM BOUND -- over the WHOLE taper family, not the solved curve.")
        print("      (1-L) is a ratio of pot fractions, so it lives in [0, 1]; the endpoints are")
        print("      PINNED (L(0)=0 is the end stop, L(1)=1 is AY6's bleed-free anchor), so the")
        print("      supremum of the interior span is 1.0 and the most any taper can buy is")
        print(f"          1 / {span_ship:.4f} = {sup_fold:.3f}x   (a supremum -- not attained)")
        # Item 9's own measured sensitivity ratios, pedal / model, both matched-detent reads:
        #   bass notch   30.0 % / 17.2 %  (s125)      treble_notch  24.3 % / 9.1 %  (s133, AE4)
        # Quoted as the pair rather than as "~2-3x" so the bound is graded against measurements.
        targets = {"bass notch (s125)": 30.0 / 17.2, "treble_notch (s133 AE4)": 24.3 / 9.1}
        print("\n      graded against item 9's own matched-detent sensitivity ratios:")
        short = []
        for name, need in sorted(targets.items(), key=lambda kv: kv[1]):
            ratio = sup_fold / need
            verdict = "REACHES" if ratio >= 1.0 else f"{1.0 / ratio:.2f}x SHORT"
            short.append(ratio)
            print(f"        {name:<26} needs {need:.3f}x   sup/need = {ratio:.3f}   {verdict}")
        reaches = [r for r in short if r >= 1.0]
        print()
        if not reaches:
            print(f"      ⇒ 0 of {len(short)} REACH, at the family's own SUPREMUM.  A LEVEL-taper or")
            print( "        mix-law reshape cannot deliver item 9's sensitivity gap for ANY taper,")
            print( "        because the shipped taper already spends "
                  f"{span_ship * 100:.1f} % of a ratio bounded")
            print( "        by 1.  This is s126's bass-peak argument on a second control: a")
            print( "        dose-response locus that cannot CONTAIN the target refutes the lever,")
            print( "        not merely its present setting.")
        else:
            print(f"      ⇒ {len(reaches)} of {len(short)} reach at the supremum -- the lever is not")
            print( "        bounded out, so the fit is worth running.")
        # ⚠⚠ s173: this verdict was NARRATED, not computed -- it read "the two jobs pull OPPOSITE
        # ways ... a SMALLER mix sweep" unconditionally, which was true of the s162 epoch it was
        # written on (fold 0.625x) and is FALSE the moment the shipped taper or the OD:CLEAN ratio
        # moves.  Both have since moved (s163's PWL, s172's `OdMakeup`).  Direction is now read off
        # `fold`, and the two branches say opposite things (`computed-verdicts-not-narrated`, the
        # 5th occurrence).  Item 9's targets are all > 1x, i.e. they always want a LARGER sweep.
        want = "LARGER" if fold > 1.0 else "SMALLER"
        same_way = fold > 1.0
        head = ("AND THE TWO JOBS NOW PULL THE SAME WAY" if same_way
                else "AND THE TWO JOBS PULL OPPOSITE WAYS")
        print(f"\n      ⚠⚠ {head}.  The taper that closes the LEVEL LAW")
        print(f"         wants fold {fold:.3f}x (span {span_ship:.4f} -> {span_req:.4f}), i.e. a")
        print(f"         {want} mix sweep, where the sensitivity gap needs a LARGER one.")
        if same_way:
            print(f"         ⇒ this taper move goes {fold:.3f}x of the way toward item 9's own")
            print( "           target as a SIDE EFFECT, so it is not `one-knob-two-jobs-is-")
            print( "           compensating` on this epoch.  ⛔ NOT a claim that it CLOSES item 9 --")
            print( "           AY5(b)'s own caveat still binds (this is the mix ratio that drives")
            print( "           the feature, not the feature measurement), and the fold is short of")
            print(f"           both targets ({', '.join(f'{v:.3f}x' for v in targets.values())}).")
        else:
            print( "         So even inside the bound they are not one correction:")
            print( "         `one-knob-two-jobs-is-compensating`.")
        out.setdefault("ay5", {})["headroom"] = {
            "span_shipped": span_ship, "span_required": span_req, "fold_required": fold,
            "sup_fold": sup_fold, "targets": targets,
            "sup_over_need": {k: sup_fold / v for k, v in targets.items()},
            "n_reach": len(reaches), "n_targets": len(short)}
        out.setdefault("ay5", {})["mix_span"] = {"shipped": span_ship, "required": span_req,
                                                "fold": fold, "detents": matched}
    out.setdefault("ay5", {})["clean_fraction"] = {str(k): v for k, v in cf_rows.items()}
    out["ay5"]["worst_d_cleanfrac"] = worst_cf


# --------------------------------------------------------------------------------------------
# AY6 -- what must NOT move
# --------------------------------------------------------------------------------------------
def gate_ay6(Lm, p, out):
    print("\n-- AY6: the bleed-free corner must be bit-identical --")
    a0, b0 = K.coef_closed(1.0, p(1.0))
    a1, b1 = K.coef_closed(1.0, Lm.get(TOP, 1.0))
    if (a0, b0) != (a1, b1):
        sys.exit(f"GATE AY6 FAIL: the bleed-free corner moves ({a0}, {b0}) -> ({a1}, {b1}).  "
                 f"GATE K7's ratio, GATE O's A3 ledger, GATE L's |rho|, OdToneRestore's base row "
                 f"and GATE W/AE's membership all read there; a taper that moves it invalidates "
                 f"all of them at once.")
    print(f"  AY6 OK  (od, clean) = ({a1:.1f}, {b1:.1f}) at LEVEL max under both tapers, exactly")
    # And the mutation: a curve that did NOT pin the top must be caught by the same check.
    bad_a, bad_b = K.coef_closed(1.0, 0.9)
    if (bad_a, bad_b) == (a0, b0):
        sys.exit("GATE AY6 FAIL: the corner check cannot discriminate -- L = 0.9 gives the same "
                 "coefficients as L = 1, so the assertion above is vacuous")
    print(f"  MUTATION OK  L = 0.9 would give ({bad_a:.4f}, {bad_b:.4f}), so the check "
          f"discriminates.")
    out["ay6"] = {"od": a1, "clean": b1}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("report")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    out = {"report": args.report}
    print(f"GATE AY -- task D: reshaping the LEVEL taper   [{args.report}]")

    bands, caps = MG.load(args.report)[0], MG.load(args.report)[1]
    idx = [i for i, _b in enumerate(bands)]
    idx = MG.GRADED_IDX(bands) if hasattr(MG, "GRADED_IDX") else idx
    print(f"  {len(caps)} captures, {len(bands)} bands")

    p = gate_ay1(out)
    gate_ay1b(args.report, caps, out)

    absfr, silent = K.absolute_fr(caps, idx)
    groups = K.find_level_groups(caps)
    ladder = max(groups.values(), key=len)
    shared = dict(zip(K.MATCH_KEYS, next(k for k, v in groups.items() if v is ladder)))
    nonhf = [j for j, i in enumerate(idx) if bands[i] < K.HF_HZ]
    print(f"  ladder = {len(ladder)} detents at blend={shared['blend']} drive={shared['drive']} "
          f"grunt={shared['gruntIdx']} attack={shared['attackIdx']}; "
          f"{len(nonhf)} non-HF bands")
    if len(ladder) < 5:
        sys.exit(f"GATE AY FAIL: the LEVEL ladder has only {len(ladder)} detents -- membership is "
                 f"wrong or the report is a subset; a taper cannot be recovered from this")

    res = ladder_re_top(absfr, ladder, nonhf)
    if len(res) != len(SWEEPS):
        sys.exit(f"GATE AY FAIL: only {len(res)} of {len(SWEEPS)} stimulus levels have a LEVEL-max "
                 f"reading, so the across-stimulus spread -- this gate's residual floor -- cannot "
                 f"be computed")

    rows = gate_ay2(res, ladder, out)
    need_tap, mono, scores = gate_ay3(res, ladder, p, rows, out)
    Lm = gate_ay4(need_tap, p, out)
    gate_ay5(Lm, p, out)
    gate_ay6(Lm, p, out)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, sort_keys=True, default=float)
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
