#!/usr/bin/env python3.11
"""GATE Y — LOCALISE THE MODEL'S OWN BASS PEAK.  Which shipped constant sets its centre?

WHY THIS EXISTS (session 126, executing session 125's `▶ NEXT` item 0).
GATE W's W4 measured, over the 7-detent LEVEL ladder at `sweep_clean`:

    model bass peak  154.6 - 165.5 Hz   (span 6.6 %,  verdict MIX)
    pedal bass peak  195.7 - 208.9 Hz   (span 6.3 %,  verdict MIX)

and W5b measured the matched-LEVEL ratio at a rock-stable **0.794x +- 0.007 over all 7
detents**.  Session 125 then refuted the standing routing "the bass peak is A3, so it needs
no separate work": the two LEVEL loci are DISJOINT (the pedal's lowest centre is 18.2 %
above the model's highest), LEVEL's full travel moves the feature only 6.6 % against a
~20-26 % gap, and the A3-correcting direction (more OD in the mix) walks the model's centre
165.5 -> 154.6 Hz, i.e. AWAY.  ⇒ the bass peak is its own item, and it had never been
localised on our side.

⭐ THE METHOD IS SESSION 125'S, AND IT IS THE POINT OF THIS TOOL: **localise your own
feature before proposing a mechanism for the mismatch** (`localise-before-fitting-a-constant`,
pointed at the model rather than at the defect).  On the TREBLE peak that cost minutes, gave
2934.8 Hz closed-form against a measured 2977-2983, and retired a whole candidate family in
the same hour by proving the feature is post-clipper LINEAR and therefore cannot move with
drive at all.

⚠⚠ **AND IT IS WHY THIS TOOL IS A RENDER SWEEP, NOT A CLOSED-FORM CASCADE.**  The treble
peak yielded to closed form because every element that makes it is drawn on the schematic
and is post-clipper.  The bass peak is not that kind of feature:
  * it is a MIX CANCELLATION on both sides (W4/W7) — it belongs to no single network, it
    is where `a*OD(f) + b*CLEAN(f)` maximises, so its centre is set by the OD path's LF
    SHAPE against a flat clean tap;
  * the shipped OD path is not the drawn one — session 100 replaced R8/R11 with a fitted
    4-resistor tap ladder and re-fitted 17 treble constants, so `eq_reference.py` (the DRAWN
    oracle) is the wrong network to cascade;
  * and W5's bleed-free endpoints read `n=0, NO DATA` — the feature VANISHES without the
    clean tap, which is the cancellation signature and also means there is no pure-OD
    transfer to read the centre off.
⇒ the honest instrument is a PERTURBATION SWEEP on the shipped renderer: move one constant,
re-locate the centre, and report `dlog(f0)/dlog(param)`.  That measures the shipped stage
rather than a model of it.

WHAT THIS TOOL DOES NOT CLAIM.  It measures WHICH constants move our centre and HOW FAR.
It does NOT propose a value, does not score a candidate against the matrix, and does not
say the pedal's 195-209 Hz is reachable — Y4 states the required move and leaves the
decision, because every constant here is already fitted to something else and the price is
a matrix question this tool cannot see (`the-matrix-is-blind-to-a-pure-level-error` cuts the
other way too: a SHAPE move is exactly what the matrix CAN judge, so that judgement belongs
in `comprehensive_report`, not here).

  Y1  KNOWN ANSWER   reproduce W4's stored model locus from a fresh render.
                     ⚠ the baseline MOVED between s122 and now (session 124 shipped clipK
                     2.4653 -> 2.0), so a bare mismatch is not a failure — Y1 renders the
                     s122 constant as a labelled CONTROL and attributes the difference
                     before anything below is read.  `rebaseline-all-derived-artefacts`, in
                     its baseline-EPOCH form (s118).
  Y2  CONTROLS       a NULL (a post-BLEND common-mode constant CANNOT move a cancellation
                     centre) and a POSITIVE (the LEVEL taper — the mix lever — must).
                     Without both, Y3's zeros are unreadable: a constant that moves nothing
                     and a constant that never reached the DSP look identical.
  Y3  SENSITIVITY    dlog(f0)/dlog(param), two-sided, for every LF-shaping OD-path constant.
  Y4  VERDICT        computed: which constants can carry the required move, and at what multiple
                     of their shipped value.  ⚠ an EXTRAPOLATION from a local slope, labelled so.
  Y5  REACHABILITY   renders that multiple instead of trusting the extrapolation (s98: an
                     invariance is established only over the region it was measured in).
  Y6  STIMULUS AXIS  Y1-Y5 all read `sweep_clean`.  Does a reaching lever survive the other three
                     rungs?  ⚠ it does NOT -- see the gate; this re-scopes Y5's verdict, and it is
                     also the first measurement of the model's bass peak on this axis (GATE W6
                     reads it UNRESOLVED, for a membership reason, not a physical one).
  Y7  COLLATERAL     what else the reaching move breaks, at two captures -- the mix detent and the
                     bleed-free endpoint, because no single capture resolves all seven features.

Usage:
  python3.11 analysis/bass_peak_locus.py                 # full gate
  python3.11 analysis/bass_peak_locus.py --jobs 6
  python3.11 analysis/bass_peak_locus.py --quick         # Y1 known answer + Y2 controls only
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze as A                # noqa: E402
import captures as C               # noqa: E402
import feature_locus_gate as W     # noqa: E402  (locator, render stamp, FEATURES — ONE definition)
from parallel import pmap          # noqa: E402

REPORT = "analysis/reports/s124_ship.json"          # the CURRENT baseline (session 124)
W_REPORT = "analysis/reports/s122_feature_locus.json"  # the stored locus Y1 reproduces
OUT_JSON = "analysis/reports/s126_bass_peak_locus.json"
REN_DIR = "build/s126_bass_peak"
OS_FACTOR = W.OS_FACTOR             # 8, same as GATE W — the locus is quoted against that render
SWEEP = W.SWEEPS[0]                 # `sweep_clean`, W4's own condition.  NAMED, never selected.

FEAT = "bass_peak"
WIN = W.FEAT_BY_NAME[FEAT][2]       # (110, 285) Hz — GATE W's derived window, not re-chosen

# The constant session 124 re-anchored.  Y1 renders THIS to attribute the s122->now delta.
S122_CLIPK = 2.4653

# ---- Y1 tolerances ------------------------------------------------------------------------------
# The locator's own measured agreement is ~0.1 % (GATE W1 vs GATE R, two estimators).  A fresh
# render of the SAME constants against a stored render is a pure determinism check, so the bar is
# the grid, not the physics.  ⚠ NOT a guessed round number: GRID_STEP_FRAC is 1.45 %, and a vertex
# is interpolated inside a cell, so anything under a third of a cell is "the same reading".
KA_TOL_FRAC = W.GRID_STEP_FRAC / 3.0

# ---- Y2 controls --------------------------------------------------------------------------------
# NULL: c21R is the EQ-path input coupling — it sits AFTER the BLEND summing node, so it multiplies
# the OD and clean paths by the SAME transfer.  A common-mode filter cannot move the frequency at
# which two paths cancel; it can only tilt the composite.  A 2x move must therefore leave the
# centre inside the locator's resolution.  ⚠ This is the guard that makes every zero in Y3
# readable — see the module docstring.
NULL_CTRL = ("c21R", 130.0e3, 2.0)
# POSITIVE: the LEVEL taper IS the mix lever, and W4 already measured its full-travel effect at
# 6.6 %.  A taper change re-points the same ladder, so the centre MUST move.
POS_CTRL = ("levelTaperExp", 2.25, 1.6)

# ---- Y3: the candidates -------------------------------------------------------------------------
# ⚠⚠ THIS LIST IS DERIVED, NOT BROWSED.  Membership rule, stated so a later session can check it:
# a constant qualifies iff it is (a) in the OD path, upstream of the BLEND summing node — anything
# downstream is common-mode and is excluded BY THE NULL CONTROL's own argument — and (b) capable of
# shaping the OD path's magnitude or phase within a decade of 165 Hz.  The `why` column is the
# corner it sets, computed from the shipped values, so an implausible entry is visible.
#
# `factor` is the two-sided perturbation.  Kept modest (1.4-2.0x) so the reading is a LOCAL
# sensitivity rather than a different circuit — a 10x move on a fitted constant re-shapes the whole
# OD path and the "centre" it reports is a different feature wearing the same window.
CANDIDATES = (
    # name,            shipped,        factor, why
    ("trebleC7",       755.764e-12,    1.6, "node-P coupling HP into IC2_A, ~181 Hz at R13=1M"),
    ("attackTapR11",   163933.0,       1.6, "the tap ladder's GND leg — sets node P's source R, so C7's corner"),
    ("attackTapRc",    77481.0,        1.6, "T2->T3 tap leg — the other half of node P's divider"),
    ("clipC15",        5.2e-9,         1.6, "post-clipper coupling HP, ~30 Hz into 1.01M"),
    ("clipC11",        3.69e-9,        1.6, "GRUNT always-in cap — sets the clipper's own HP corner"),
    ("clipR16",        6.8e3,          1.6, "clipper input R — moves the GRUNT corner with C11"),
    ("clipA0",         24.871,         1.4, "open-loop gain: node W impedance is R18/(1+A0), so it moves the GRUNT corner"),
    ("trebleC5",       7.95747e-9,     1.6, "treble ladder's first series cap — the ladder's LF end"),
    ("trebleR7",       1.64563e6,      1.6, "top-rail series R — sets the ladder-vs-rail split at LF"),
    ("jfetGm",         0.10e-3,        1.4, "J201 transconductance — sets OD-path LEVEL, hence where it crosses the clean tap"),
    ("driveTaperExp",  1.98,           1.4, "DRIVE taper — same lever as jfetGm, different stage"),
)


# ---- rendering ----------------------------------------------------------------------------------
def _one(args):
    """Render ONE (capture, fit-override) cell and locate the bass peak on the model side."""
    fname, fits, tag = args
    orig, ref = W._load_orig()
    parsed = C.parse_capture(fname)
    ra = C.render_args(parsed)
    for k, v in fits:
        ra += ["--fit", f"{k}={v:.9g}"]
    out = os.path.join(REN_DIR, f"{fname.replace('.wav','')}__{tag}_plugin.wav")
    W.render(out, ra)
    al, _ = A.align(A.load(out), orig)
    f, m = A.transfer_h1(A.seg_of(al, SWEEP), ref)
    d = W.smooth(f, m)
    r = W.locate(d, WIN, "max")
    r["file"] = fname
    r["tag"] = tag
    r["level"] = parsed.get("level")
    return r


def run(cells, jobs):
    return pmap(_one, cells, jobs=jobs)


def _valid(r):
    """A located vertex is only a measurement while it is off the window edge and has depth.

    Same guards GATE W3 applies to its data — and W1b's lesson applies here with force: a
    PERTURBATION ARM gets the same guards as the baseline, or a window that no longer contains the
    moved feature reads as the physics failing."""
    return (not r["edge"]) and r["margin_frac"] >= W.EDGE_MARGIN_FRAC and r["prom"] >= W.MIN_PROM_DB


def _guard(rows, where):
    bad = [r for r in rows if not _valid(r)]
    if bad:
        for r in bad:
            print(f"      ! {r['tag']:<28s} f0 {r['f0']:7.1f}  edge={r['edge']} "
                  f"margin={r['margin_frac']:.3f} prom={r['prom']:.2f} dB")
        sys.exit(f"GATE Y ({where}): {len(bad)} reading(s) are not measurements — fix the window "
                 f"or shrink the perturbation; do NOT read a sensitivity off an edge.")


# ================================ THE GATES ======================================================
def gate_y1(lad, out, jobs):
    """KNOWN ANSWER: reproduce GATE W's stored model locus, and attribute any epoch delta."""
    print("\n" + "=" * 92)
    print("Y1  KNOWN ANSWER -- reproduce GATE W's stored model bass-peak locus")
    print("=" * 92)
    if not os.path.exists(W_REPORT):
        sys.exit(f"GATE Y1: {W_REPORT} is absent -- GATE W must have been run, or there is no "
                 f"stored locus to reproduce and every number below is unvalidated")
    stored = json.load(open(W_REPORT))["w4"][FEAT]
    want = stored["model"]["f0"]
    all_levels = sorted(lad)

    # ⚠⚠ MEMBERSHIP IS MEASURED, NOT ASSUMED.  W4's stored model row has 7 entries against a
    # 9-detent ladder, because W3's validity guards drop two of them -- at LEVEL min the MODEL
    # MUTES (GATE L7: `divRatio(0)` is exactly 0), and at LEVEL max the clean tap is exactly out of
    # circuit so the CANCELLATION FEATURE VANISHES (W5 reads `n=0, NO DATA` there).  Both
    # exclusions are physics, and both are re-DERIVED here from the readings rather than
    # transcribed as "drop the ends" -- a hardcoded index is how a membership change goes silent
    # (s114, `resolve membership from SETTINGS, then ASSERT it`).
    got_all = run([(lad[lv], [], "ship") for lv in all_levels], jobs)
    keep, drop = [], []
    for lv, r in zip(all_levels, got_all):
        (keep if _valid(r) else drop).append((lv, r))
    for lv, r in drop:
        print(f"  dropped LEVEL {lv:.3f} ({lad[lv]}): f0 {r['f0']:7.1f} Hz  edge={r['edge']} "
              f"margin={r['margin_frac']:.3f} prom={r['prom']:.2f} dB -- not a measurement")
    levels = [lv for lv, _ in keep]
    got = [r for _, r in keep]
    print(f"  ladder {len(all_levels)} detents -> {len(levels)} valid readings {levels}")
    if len(want) != len(levels):
        sys.exit(f"GATE Y1: the stored locus has {len(want)} readings and this render has "
                 f"{len(levels)} -- membership moved, so the comparison is not row-for-row "
                 f"(`aggregate-moved-check-membership-first`).  Check WHICH detents dropped "
                 f"above before touching anything else.")
    g = [r["f0"] for r in got]
    err = [abs(a - b) / b for a, b in zip(g, want)]
    print(f"  read at {SWEEP}, --os {OS_FACTOR}, window {WIN[0]:.0f}-{WIN[1]:.0f} Hz "
          f"(GATE W's own, not re-chosen)")
    print(f"\n  {'LEVEL':>7s}  {'stored (s122)':>14s}  {'fresh (s126)':>13s}   delta")
    for lv, a, b in zip(levels, want, g):
        print(f"  {lv:7.3f}  {a:14.2f}  {b:13.2f}   {(b-a)/a*100:+6.2f} %")
    span_s = max(want) / min(want) - 1.0
    span_g = max(g) / min(g) - 1.0
    print(f"  span    {span_s*100:13.1f} %{span_g*100:12.1f} %")
    worst = max(err)
    print(f"\n  worst detent delta {worst*100:.2f} %  vs bar {KA_TOL_FRAC*100:.2f} % "
          f"(a third of the {W.GRID_STEP_FRAC*100:.2f} % grid cell)  "
          f"{'OK -- REPRODUCED' if worst <= KA_TOL_FRAC else 'MOVED'}")

    ctl = None
    if worst > KA_TOL_FRAC:
        # ⚠ NOT a failure yet.  s122 was rendered before session 124 shipped clipK 2.4653 -> 2.0.
        # At --os 8 the OS gate turns ADAA OFF, so clipK is the ONLY shipped constant that reaches
        # this render -- which makes the attribution a one-arm experiment rather than a guess.
        print(f"\n  ⚠ the fresh render does not reproduce the stored one.  Session 124 shipped "
              f"clipK 2.4653 -> 2.0,\n    and at --os {OS_FACTOR} the OS gate turns ADAA OFF, so "
              f"clipK is the ONLY shipped constant reaching this render.\n    Rendering the s122 "
              f"constant as a labelled CONTROL before concluding anything:")
        cc = run([(lad[lv], [("clipK", S122_CLIPK)], "clipK_s122") for lv in levels], jobs)
        _guard(cc, "Y1 control")
        c = [r["f0"] for r in cc]
        cerr = [abs(a - b) / b for a, b in zip(c, want)]
        for lv, a, b in zip(levels, want, c):
            print(f"      {lv:7.3f}  stored {a:8.2f}  at clipK={S122_CLIPK} {b:8.2f}   "
                  f"{(b-a)/a*100:+6.2f} %")
        cw = max(cerr)
        print(f"      worst {cw*100:.2f} %  -> "
              f"{'ATTRIBUTED to the clipK re-anchor' if cw <= KA_TOL_FRAC else 'NOT attributed'}")
        ctl = {"f0": c, "worst_frac": cw, "attributed": bool(cw <= KA_TOL_FRAC)}
        if cw > KA_TOL_FRAC:
            sys.exit("GATE Y1: the stored locus is reproduced by NEITHER the shipped constants nor "
                     "the s122 clipK -- something else moved between the two renders.  Find it "
                     "before reading any sensitivity below; an unattributed baseline shift "
                     "contaminates every perturbation measured against it (s118).")
        print(f"      ⇒ the shipped locus is the s126 column above; quote THAT, not s122's.")

    out["y1"] = {"levels": levels, "stored": want, "fresh": g, "worst_frac": worst,
                 "reproduced": bool(worst <= KA_TOL_FRAC), "span_stored": span_s,
                 "span_fresh": span_g, "clipk_control": ctl}
    return dict(zip(levels, g))


def gate_y2(lad, base, out, jobs):
    """CONTROLS: one constant that MUST NOT move the centre, one that MUST."""
    print("\n" + "=" * 92)
    print("Y2  CONTROLS -- without these, a zero in Y3 is unreadable")
    print("=" * 92)
    # The middle of the VALID ladder (Y1's membership), not of the raw one — the raw ends are the
    # two detents Y1 just dropped as unmeasurable.
    valid = sorted(base)
    lv = valid[len(valid) // 2]
    cap = lad[lv]
    b = base[lv]
    print(f"  both arms at LEVEL {lv:.3f} ({cap}), baseline centre {b:.2f} Hz")

    nk, nv, nf = NULL_CTRL
    pk, pv, pf = POS_CTRL
    rows = run([(cap, [(nk, nv * nf)], f"null_{nk}"),
                (cap, [(pk, pv * pf)], f"pos_{pk}")], jobs)
    _guard(rows, "Y2")
    r_null, r_pos = rows[0], rows[1]
    d_null = (r_null["f0"] - b) / b
    d_pos = (r_pos["f0"] - b) / b
    bar = KA_TOL_FRAC

    print(f"\n  NULL     {nk} x{nf}  ({nv:.4g} -> {nv*nf:.4g})")
    print(f"           centre {b:7.2f} -> {r_null['f0']:7.2f} Hz   {d_null*100:+6.2f} %   "
          f"bar +-{bar*100:.2f} %   {'OK' if abs(d_null) <= bar else 'FAIL'}")
    print(f"           why it must not move: c21R sits AFTER the BLEND summing node, so it is "
          f"common-mode to\n           both paths -- it cannot change the frequency at which they "
          f"cancel, only tilt the sum.")
    print(f"\n  POSITIVE {pk} x{pf}  ({pv:.4g} -> {pv*pf:.4g})")
    print(f"           centre {b:7.2f} -> {r_pos['f0']:7.2f} Hz   {d_pos*100:+6.2f} %   "
          f"needs > {bar*100:.2f} %   {'OK' if abs(d_pos) > bar else 'FAIL'}")
    print(f"           why it must move: LEVEL IS the mix lever, and W4 measured its full-travel "
          f"effect at 6.6 %.")

    if abs(d_null) > bar:
        sys.exit(f"GATE Y2 (null): a post-BLEND common-mode constant moved the centre by "
                 f"{d_null*100:.2f} % -- either the feature is not the cancellation W7 classified "
                 f"it as, or `--fit {nk}` reaches further than the EQ input coupling.  Resolve "
                 f"that before reading Y3: every sensitivity below is quoted against this bar.")
    if abs(d_pos) <= bar:
        sys.exit(f"GATE Y2 (positive): the LEVEL taper did NOT move the centre "
                 f"({d_pos*100:.2f} %) -- the perturbation is not reaching the DSP, so a zero in "
                 f"Y3 would mean nothing (`a mutation that produces no measurement is a distinct "
                 f"hard failure, never a zero`).")
    out["y2"] = {"level": lv, "file": cap, "base_hz": b,
                 "null": {"name": nk, "factor": nf, "f0": r_null["f0"], "d_frac": d_null},
                 "pos": {"name": pk, "factor": pf, "f0": r_pos["f0"], "d_frac": d_pos},
                 "bar_frac": bar}
    return lv, cap, b


def gate_y3(cap, b, out, jobs):
    """SENSITIVITY: dlog(f0)/dlog(param), two-sided, for every LF-shaping OD-path constant."""
    print("\n" + "=" * 92)
    print("Y3  SENSITIVITY -- dlog(f0)/dlog(param), two-sided, at the middle detent")
    print("=" * 92)
    cells = []
    for name, ship, fac, _ in CANDIDATES:
        cells.append((cap, [(name, ship * fac)], f"{name}_up"))
        cells.append((cap, [(name, ship / fac)], f"{name}_dn"))
    rows = run(cells, jobs)
    _guard(rows, "Y3")
    by = {r["tag"]: r for r in rows}

    print(f"  baseline {b:.2f} Hz.  `S` = dlog(f0)/dlog(param): +1 means the centre tracks the "
          f"constant\n  proportionally, 0 means the constant does not set this feature.  "
          f"|S| below the Y2 null bar\n  ({KA_TOL_FRAC*100:.2f} % per reading) is NOT a "
          f"measurement of zero -- it is 'not resolved here'.\n")
    print(f"  {'constant':<15s} {'shipped':>11s} {'x':>4s} {'f0 up':>8s} {'f0 dn':>8s} "
          f"{'S':>7s}  {'|move|':>7s}  what it is")
    res = {}
    for name, ship, fac, why in CANDIDATES:
        up, dn = by[f"{name}_up"], by[f"{name}_dn"]
        # Two-sided log-log slope.  Two-sided rather than one-sided because a cancellation centre
        # is not required to respond symmetrically, and the asymmetry is itself worth printing.
        s = (np.log(up["f0"]) - np.log(dn["f0"])) / (2.0 * np.log(fac))
        mv = max(abs(up["f0"] - b), abs(dn["f0"] - b)) / b
        resolved = mv > KA_TOL_FRAC
        res[name] = {"shipped": ship, "factor": fac, "f0_up": up["f0"], "f0_dn": dn["f0"],
                     "slope": float(s), "max_move_frac": float(mv), "resolved": bool(resolved),
                     "why": why}
        print(f"  {name:<15s} {ship:11.4g} {fac:4.1f} {up['f0']:8.2f} {dn['f0']:8.2f} "
              f"{s:+7.3f}  {mv*100:6.2f}%{'' if resolved else ' -'}  {why}")
    print(f"\n  '-' = the move is under the Y2 bar, i.e. this constant does not resolvably set "
          f"the centre.")
    out["y3"] = res
    return res


def gate_y4(base, sens, out):
    """VERDICT, computed: what move is required, and which constants could carry it."""
    print("\n" + "=" * 92)
    print("Y4  VERDICT -- what is required, and what could carry it")
    print("=" * 92)
    stored = json.load(open(W_REPORT))["w4"][FEAT]
    ped = stored["pedal"]["f0"]
    mod = list(base.values())
    # The requirement is stated the way session 125 stated the refutation: LOCUS vs LOCUS, so it
    # does not depend on which detent is paired with which.  Both are the same 7-detent ladder.
    need_lo = min(ped) / max(mod) - 1.0        # to make the two loci merely TOUCH
    need_med = float(np.median(ped)) / float(np.median(mod)) - 1.0   # to centre them on each other
    print(f"  model locus {min(mod):7.1f} - {max(mod):7.1f} Hz   (median {np.median(mod):7.1f})")
    print(f"  pedal locus {min(ped):7.1f} - {max(ped):7.1f} Hz   (median {np.median(ped):7.1f})")
    print(f"  ⇒ the loci are {'DISJOINT' if min(ped) > max(mod) else 'overlapping'}; our centre "
          f"must rise by {need_lo*100:.1f} % to TOUCH and {need_med*100:.1f} % to MATCH.")
    print(f"  ⚠ LEVEL's whole travel moves it {out['y1']['span_fresh']*100:.1f} % -- see session "
          f"125: the mix lever is ~3x too small AND points the wrong way.\n")

    resolved = [(n, v) for n, v in sens.items() if v["resolved"]]
    resolved.sort(key=lambda kv: -abs(kv[1]["slope"]))
    print(f"  {'constant':<15s} {'S':>7s}  {'x needed to MATCH':>18s}   note")
    rows = []
    for n, v in resolved:
        s = v["slope"]
        # x such that x^S = (1 + need_med).  Reported as a MULTIPLE of the shipped value.
        mult = float(np.exp(np.log(1.0 + need_med) / s)) if abs(s) > 1e-6 else float("inf")
        # ⚠ An extrapolation, and it is labelled as one: S is a LOCAL slope measured over a
        # <=1.6x perturbation, so a required multiple far outside that range is a direction, not a
        # value (`an invariance is established only over the region it was measured in`, s98).
        far = not (1.0 / v["factor"] <= mult <= v["factor"])
        v["mult_needed"] = mult          # Y5 probes THIS, so the two cannot drift apart
        v["extrapolated"] = far
        rows.append({"name": n, "slope": s, "mult_needed": mult, "extrapolated": far})
        print(f"  {n:<15s} {s:+7.3f}  {mult:18.3g}   "
              f"{'EXTRAPOLATED beyond the measured range' if far else 'inside the measured range'}")
    if not resolved:
        print("  (none resolved)")
    print(f"\n  ⚠ every multiple above is quoted from a LOCAL slope over a <= 1.6x perturbation. "
          f"A value\n    outside that range is a DIRECTION, not a proposal -- and none of these "
          f"constants is free:\n    each is already fitted to something else, so the price is a "
          f"matrix question this tool cannot see.")
    out["y4"] = {"need_touch_frac": need_lo, "need_match_frac": need_med,
                 "model_locus": [min(mod), max(mod)], "pedal_locus": [min(ped), max(ped)],
                 "candidates": rows}


def gate_y5(cap, b, sens, out, jobs):
    """REACHABILITY: does Y3's local slope survive out to the multiple Y4 needs?

    ⚠⚠ THIS IS THE GATE THAT MAKES Y4 QUOTABLE, AND WITHOUT IT Y4 IS A BLIND EXTRAPOLATION.
    Y3's `S` is measured over a <= 1.6x perturbation and Y4 then solves `x^S = 1 + need` for
    multiples of 0.28x down to 0.0001x -- between 4x and four ORDERS OF MAGNITUDE outside the
    region the slope was measured in.  The project has paid for exactly this before: session 98
    found GATE F's ladder-invariance, established between two ladders 0.23 decades apart, failing
    by 3.84 dB at a candidate 1.00 decades out (`an invariance is established only over the region
    it was measured in -- re-check the premise AT THE CANDIDATE, not only at the reference points
    that justified it`).  So Y5 renders the candidate.

    A profile, not a point, because the two ways this can end are different findings:
      * the centre keeps rising to the target  -> the lever is REAL, and the question becomes price;
      * the centre SATURATES or the feature dissolves -> the lever cannot reach it AT ALL, which is
        a reachability refutation of the same shape as session 125's LEVEL-locus argument and
        session 38's C12 argument, and is worth far more than a slope.

    ⚠ An invalid reading here is DATA, not a crash: a feature that leaves its window or loses its
    prominence under a large move has stopped existing, which is the saturation answer.  So Y5 does
    NOT call `_guard` -- it reports validity per point and refuses to quote a centre for an invalid
    one (`a bound is not a measurement`, and `locate` always returns something)."""
    print("\n" + "=" * 92)
    print("Y5  REACHABILITY -- does Y3's local slope survive to the multiple Y4 needs?")
    print("=" * 92)
    need = out["y4"]["need_match_frac"]
    target = b * (1.0 + need)
    # The strongest levers, plus one weak one as a contrast.  Ordered by |S|, taken from Y3's own
    # ranking rather than named here, so the selection cannot drift from what Y3 measured.
    rank = sorted(((n, v) for n, v in sens.items() if v["resolved"]),
                  key=lambda kv: -abs(kv[1]["slope"]))
    probe = [n for n, _ in rank[:3]] + [rank[-1][0]]
    print(f"  baseline {b:.2f} Hz, target {target:.2f} Hz (the pedal's median, +{need*100:.1f} %)")
    print(f"  probing {probe} -- Y3's three strongest levers plus its weakest, as a contrast\n")

    cells, plan = [], []
    for name in probe:
        v = sens[name]
        # Geometric ladder from just outside the measured range down to the required multiple,
        # floored at 0.02x -- below that the constant is effectively deleted and the render is a
        # different circuit, not a perturbation of this one.
        lo = float(np.clip(v["mult_needed"], 0.02, 1.0))
        for m in np.geomspace(1.0 / v["factor"], lo, 4):
            tag = f"{name}_x{m:.4g}".replace(".", "p")
            cells.append((cap, [(name, v["shipped"] * float(m))], tag))
            plan.append((name, float(m)))
    rows = run(cells, jobs)
    by = {(n, m): r for (n, m), r in zip(plan, rows)}

    res = {}
    for name in probe:
        ms = [m for n, m in plan if n == name]
        print(f"  {name}  (shipped {sens[name]['shipped']:.4g}, S = {sens[name]['slope']:+.3f})")
        print(f"    {'x':>9s} {'value':>12s} {'f0 Hz':>8s} {'move':>8s} {'predicted':>10s}  valid")
        best, reached = b, False
        for m in ms:
            r = by[(name, m)]
            pred = b * m ** sens[name]["slope"]
            ok = _valid(r)
            if ok:
                best = max(best, r["f0"])
                reached = reached or r["f0"] >= target
                note = "yes"
            else:
                note = f"NO (edge={r['edge']}, margin={r['margin_frac']:.3f}, prom={r['prom']:.2f} dB)"
            print(f"    {m:9.4g} {sens[name]['shipped']*m:12.4g} "
                  f"{r['f0']:8.2f} {(r['f0']-b)/b*100:+7.2f}% {pred:10.2f}  {note}")
        got = (best - b) / b
        print(f"    -> best VALID centre {best:.2f} Hz = {got*100:+.1f} % of the "
              f"{need*100:+.1f} % required   {'REACHES' if reached else 'DOES NOT REACH'}\n")
        res[name] = {"multiples": ms, "best_valid_hz": best, "achieved_frac": got,
                     "reaches": bool(reached)}

    any_reach = any(v["reaches"] for v in res.values())
    print(f"  ⇒ {'at least one single constant REACHES the pedal locus' if any_reach else 'NO single constant reaches the pedal locus, even driven far outside its fitted range'}.")
    if not any_reach:
        print(f"    That is a REACHABILITY result, not a fit result: the model's bass peak cannot be\n"
              f"    walked onto the pedal's by any ONE of the OD path's LF-shaping constants.  Same\n"
              f"    shape as s38's C12 locus argument and s125's LEVEL-locus argument -- a\n"
              f"    dose-response that does not contain the target refutes the lever, not its setting.")
    out["y5"] = {"target_hz": target, "need_frac": need, "probed": probe, "results": res,
                 "any_reaches": bool(any_reach)}


def _all_features(cap, fits, tag):
    """Locate EVERY named GATE W feature on one MODEL render, at EVERY sweep — not just the one we
    came for, and not just at the quietest stimulus.

    ⚠ All four sweeps come out of the SAME render file, so this costs nothing extra — and it is
    required, because several features are simply not present at `sweep_clean` (W4 reads the
    model's `mid_peak` as UNRESOLVED there).  Screening collateral at one sweep would report
    "the feature dissolved" for features that were never resolvable in the first place.

    Uses `W.features_of` rather than re-deriving the read — ONE definition of what a feature
    reading is, shared with GATE W (`rebuild-targets-dont-transcribe`, applied to a code path)."""
    orig, ref = W._load_orig()
    parsed = C.parse_capture(cap)
    ra = C.render_args(parsed)
    for k, v in fits:
        ra += ["--fit", f"{k}={v:.9g}"]
    out = os.path.join(REN_DIR, f"{cap.replace('.wav','')}__{tag}_plugin.wav")
    W.render(out, ra)
    al, _ = A.align(A.load(out), orig)
    res = {}
    for sw in W.SWEEPS:
        res[sw] = W.features_of(al, sw, ref)
        res[sw]["_wide"] = _wide_of(al, sw, ref)
    return res


# ⚠ Y7b's widened windows.  The factor is NOT a new number: it is Y3's own perturbation scale.
# Y3 measured |S| = 0.13-0.18 for the strongest levers, so even a 5.6x move on one of them walks a
# feature by ~1.3x; 1.6x covers that with margin.  Stated so a later session can check it rather
# than inherit it (`search-settings-are-derived-artefacts`).
WIDEN = 1.6


def _best_interior(d, win, kind, grid=W.GRID):
    """The most prominent INTERIOR extremum of `kind` in `win` — the honest MOVED/DISSOLVED test.

    ⚠⚠ Y7b's FIRST DRAFT CALLED `W.locate` ON THE WIDENED WINDOW AND READ ITS `prom`, AND THAT IS
    CIRCULAR.  `locate`'s prominence is `min(left, right)` over a walk outward from the extremum,
    so an extremum sitting ON a window bound has one side of length zero and its prominence is
    **identically 0.00 dB, by construction, for any curve whatsoever**.  The run duly printed
    `prom 3.81 -> 0.00` four times — two different constants, two different multiples, two
    different features, all agreeing to the digit, which is the tell
    (`an-implausible-coincidence-is-a-bug-report`).  "DISSOLVED" was `edge=True` wearing a number:
    a check that an earlier guard already guarantees is not a check (s119 O6b).

    ⇒ the question "is there still a feature here?" must be asked of the window's INTERIOR local
    extrema, where prominence is two-sided and can genuinely come back large.  This can fail in
    both directions, which is what makes it a measurement: a moved-but-intact notch returns its
    real depth, and a flattened one returns a real, small number rather than a structural zero.

    The prominence rule is `locate`'s, applied at a chosen index instead of at the argmin — the
    walk is transcribed deliberately rather than imported, because `locate` couples it to the
    argmin.  Kept identical so the two are comparable; if `locate`'s rule changes, change it here."""
    m = (grid >= win[0]) & (grid <= win[1])
    idx = np.flatnonzero(m)
    dd = d[m] if kind == "min" else -d[m]
    best = None
    for j in range(1, len(dd) - 1):
        if not (dd[j] <= dd[j - 1] and dd[j] <= dd[j + 1]):
            continue
        left = right = 0.0
        for k in range(j - 1, -1, -1):
            left = max(left, dd[k] - dd[j])
            if dd[k] < dd[j]:
                break
        for k in range(j + 1, len(dd)):
            right = max(right, dd[k] - dd[j])
            if dd[k] < dd[j]:
                break
        p = float(min(left, right))
        if best is None or p > best[0]:
            best = (p, j, int(idx[j]))
    if best is None:                      # strictly monotone across the whole widened window
        return {"f0": float("nan"), "prom": 0.0, "n_interior": 0}
    p, j, i = best
    if 0 < i < len(d) - 1:
        y0, y1, y2 = (-d[i - 1], -d[i], -d[i + 1]) if kind == "max" else (d[i - 1], d[i], d[i + 1])
        den = y0 - 2 * y1 + y2
        dl = 0.0 if abs(den) < 1e-12 else float(np.clip(0.5 * (y0 - y2) / den, -1.0, 1.0))
    else:
        dl = 0.0
    step = W.LOG_GRID[1] - W.LOG_GRID[0]
    n_int = sum(1 for j2 in range(1, len(dd) - 1)
                if dd[j2] <= dd[j2 - 1] and dd[j2] <= dd[j2 + 1])
    return {"f0": float(np.exp(W.LOG_GRID[i] + dl * step)), "prom": p, "n_interior": n_int}


def _wide_of(al, sw, ref):
    """Every feature's most prominent INTERIOR extremum in a window widened by `WIDEN`.

    ⚠ Same `W.smooth` as `W.features_of` — only the window and the estimator differ, and both
    differences are the point (see `_best_interior`)."""
    f, m = A.transfer_h1(A.seg_of(al, sw), ref)
    d = W.smooth(f, m)
    return {name: _best_interior(d, (lo / WIDEN, hi * WIDEN), kind)
            for name, kind, (lo, hi), _ in W.FEATURES}


def _af(args):
    cap, fits, tag = args
    return (cap, tag), _all_features(cap, fits, tag)


def _pedal_features(cap):
    """The PEDAL side of one capture, all four sweeps — the same read path as the model's.

    ⚠ Read from the capture Y2/Y3/Y5 actually work on, NOT quoted from GATE W6's stored medians:
    those are a median over the 16 bleed-free ENDPOINTS, a different capture set at a different
    mix, and differencing our one-capture model reading against them would be a mismatched pair
    (`a matched pair is an assumption until something tests it`, s113)."""
    orig, ref = W._load_orig()
    al, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, cap)), orig)
    return {sw: W.features_of(al, sw, ref) for sw in W.SWEEPS}


def gate_y6(cap, sens, out, jobs):
    """STIMULUS AXIS: Y5 read ONE sweep.  Does the reaching lever survive the other three?

    ⚠⚠ THIS GATE EXISTS BECAUSE THE FIRST RUN'S Y7 CONTRADICTED Y5 BY ACCIDENT.  Y1-Y5 are all
    read at `sweep_clean`, and correctly so — it is GATE W4's own condition, NAMED rather than
    selected.  But a lever measured at one stimulus level is a claim about that level, and the
    collateral screen (which reads the loudest sweep the baseline supports) happened to read the
    SAME capture and the SAME candidate at `sweep_drv_-6` and got **+2.1 %** where Y5 got
    **+25.6 %**.  That is `gate-domain-must-cover-candidate-reach` (s49) on the STIMULUS axis
    rather than the frequency axis: Y5's domain is one rung of a four-rung ladder, and a candidate
    whose benefit lands only on that rung scores full marks there.

    ⭐ IT IS ALSO THE FIRST MEASUREMENT OF THE MODEL'S BASS PEAK ON THIS AXIS.  GATE W6 reports it
    `UNRESOLVED` — not because it is fixed, but because W6 reads the bleed-free ENDPOINTS, and a
    mix cancellation has no bleed-free reading at all (W5: `n=0, NO DATA`).  So W6's silence here
    is a membership property, not a physical one, and nothing has ever asked whether our bass peak
    moves with drive.  The pedal's does: W6 measured `DRIVE-DEPENDENT`, span 7.8 %.

    Both sides are read from the SAME capture at the same four sweeps, so each gap is a matched
    pair.  The verdict is computed per sweep and the gate does NOT pool it — a lever that closes
    the gap at one stimulus and not another is exactly the finding pooling would erase
    (`a wash-out cannot say which end moved`, s117)."""
    print("\n" + "=" * 92)
    print("Y6  STIMULUS AXIS -- Y5 read ONE sweep; does the lever survive the other three?")
    print("=" * 92)
    reach = [n for n in out["y5"]["probed"] if out["y5"]["results"][n]["reaches"]]
    picks = {n: float(np.clip(sens[n]["mult_needed"], 0.02, 1.0)) for n in reach}
    cells = [(cap, [], "ship")] + [(cap, [(n, sens[n]["shipped"] * picks[n])],
                                    f"{n}_x{picks[n]:.4g}".replace(".", "p")) for n in reach]
    got = {t: v for (_c, t), v in pmap(_af, cells, jobs=jobs)}
    ped = _pedal_features(cap)
    base = got["ship"]

    print(f"  at {cap}, feature `{FEAT}`.  Both sides read from this ONE capture, so every gap "
          f"below is a\n  matched pair.  Y1-Y5 live in the `clean` column alone.\n")
    hdr = f"  {'sweep':<10s} {'pedal':>9s} {'model':>9s} {'gap':>8s}"
    for n in reach:
        hdr += f" | {n + ' x' + format(picks[n], '.3g'):>20s} {'gap':>8s}"
    print(hdr)

    rows, ship_valid = {}, {}
    for sw in W.SWEEPS:
        p, m = ped[sw][FEAT], base[sw][FEAT]
        ok = _valid(p) and _valid(m)
        ship_valid[sw] = ok
        if not ok:
            why = []
            if not _valid(p):
                why.append("pedal")
            if not _valid(m):
                why.append("model")
            print(f"  {sw.replace('sweep_',''):<10s} {p['f0']:9.1f} {m['f0']:9.1f} "
                  f"{'--':>8s}   NOT A MEASUREMENT on the shipped render ({'+'.join(why)}) "
                  f"-- not screened")
            rows[sw] = None
            continue
        g0 = p["f0"] / m["f0"] - 1.0
        line = f"  {sw.replace('sweep_',''):<10s} {p['f0']:9.1f} {m['f0']:9.1f} {g0*100:+7.1f}%"
        r = {"pedal": p["f0"], "model_ship": m["f0"], "gap_ship": g0, "cand": {}}
        for n in reach:
            tag = f"{n}_x{picks[n]:.4g}".replace(".", "p")
            c = got[tag][sw][FEAT]
            cv = _valid(c)
            g1 = p["f0"] / c["f0"] - 1.0
            r["cand"][n] = {"f0": c["f0"], "gap": g1, "valid": bool(cv),
                            "closes": bool(cv and abs(g1) < abs(g0))}
            line += f" | {c['f0']:19.1f}{'!' if not cv else ' '} {g1*100:+7.1f}%"
        print(line)
        rows[sw] = r

    n_ok = sum(1 for v in rows.values() if v)
    print(f"\n  {n_ok} of {len(W.SWEEPS)} sweeps are measurable on both sides of the shipped "
          f"render.")
    res = {}
    for n in reach:
        closes = [sw for sw, v in rows.items() if v and v["cand"][n]["closes"]]
        worse = [sw for sw, v in rows.items() if v and not v["cand"][n]["closes"]]
        moves = [abs(v["cand"][n]["f0"] / v["model_ship"] - 1.0) for v in rows.values() if v]
        uniform = len(worse) == 0 and n_ok >= 2
        print(f"    {n} x{picks[n]:.3g}: closes the gap at {len(closes)}/{n_ok} measurable "
              f"sweeps {[s.replace('sweep_','') for s in closes]}")
        print(f"      its own effect spans {min(moves)*100:.1f} % to {max(moves)*100:.1f} % "
              f"across those sweeps  -> {'UNIFORM' if uniform else 'CONDITION-SPECIFIC'}")
        res[n] = {"pick": picks[n], "closes_at": closes, "worse_at": worse,
                  "move_min_frac": min(moves), "move_max_frac": max(moves),
                  "uniform": bool(uniform)}
    if reach and not any(v["uniform"] for v in res.values()):
        print(f"\n  ⇒ NO reaching candidate closes the gap at every measurable stimulus level.\n"
              f"    Y5's `REACHES` is therefore a claim about `{SWEEP}` ALONE and must be quoted "
              f"with that\n    condition attached.  A constant whose effect on the centre varies "
              f"this much with stimulus is\n    not acting as a fixed corner -- which is itself "
              f"evidence about what this feature is.")
    elif reach:
        print(f"\n  ⇒ at least one candidate closes the gap at every measurable stimulus level.")
    out["y6"] = {"capture": cap, "feature": FEAT, "picks": picks, "rows": rows, "verdict": res}


def gate_y7(cap, lad, sens, out, jobs):
    """COLLATERAL: what else does the reaching move break?

    ⚠⚠ Y3-Y5 SCORE ONLY THE BENEFIT AND ARE BLIND TO THE COST BY CONSTRUCTION -- they read ONE
    window.  That is `gate-domain-must-cover-candidate-reach` (s49) exactly: a score computed over
    the band the fix helps will always prefer the candidate whose damage lands elsewhere.  The
    constants that reach are the treble ladder's, and the treble ladder feeds the WHOLE OD path,
    so the features it can disturb include two the project currently has RIGHT:
       * `mid_notch` -- the 320 Hz null, GAP #2, measured by GATE W at 1.007x (its centre was
         never wrong; only its depth/width are);
       * `mid_peak`  -- the one feature whose DRIVE dependence already TRACKS the pedal (~2.5 %),
         which session 125 called the localising clue for open item 6.
    A move that fixes the bass peak by breaking either is a compensating error, not a fix.

    ⚠ This is a SHAPE screen at two conditions, not a price. The real price is the 162-capture
    matrix, which this tool cannot see and must not pretend to."""
    print("\n" + "=" * 92)
    print("Y7  COLLATERAL -- what else moves?  (Y3-Y5 read ONE window and are blind to the rest)")
    print("=" * 92)
    reach = [n for n in out["y5"]["probed"] if out["y5"]["results"][n]["reaches"]]
    if not reach:
        print("  no candidate reached, so there is no move to price.")
        out["y7"] = {"reaching": [], "rows": {}}
        return
    # ⚠⚠ TWO SCREENING CAPTURES, AND THE SECOND IS NOT OPTIONAL.  The first draft screened at the
    # mix detent alone and reported `mid_notch`, `mid_peak` and `bt_notch` as NOT MEASURABLE -- i.e.
    # it could not screen the two features this gate exists to protect.  That is not a defect in
    # the data, it is the same physics W5/W7 classified: the bass features are MIX CANCELLATIONS
    # and live only where the clean tap is present, while the mid/bridged-T features are the ones
    # GATE W resolves BLEED-FREE.  No single capture carries both, so the screen takes the LEVEL
    # ladder's own bleed-free endpoint (LEVEL = 1, where the clean coefficient is exactly zero --
    # GATE K2) as a second condition.  Derived from the ladder, not named.
    screen = [cap]
    bf = lad.get(1.0)
    if bf and bf != cap:
        screen.append(bf)
    picks = {n: float(np.clip(sens[n]["mult_needed"], 0.02, 1.0)) for n in reach}
    tags = {n: f"{n}_x{picks[n]:.4g}".replace(".", "p") for n in reach}
    cells = [(c, [], "ship") for c in screen]
    cells += [(c, [(n, sens[n]["shipped"] * picks[n])], tags[n]) for c in screen for n in reach]
    got = dict(pmap(_af, cells, jobs=jobs))
    names = [f[0] for f in W.FEATURES]

    # ⚠⚠ VALIDITY IS ESTABLISHED ON THE BASELINE FIRST, AND THE FIRST DRAFT DID NOT DO IT.  It
    # found `mid_peak`/`mid_notch` invalid on the CANDIDATE and printed "(dissolved)" -- attributing
    # to the candidate a reading that is not a measurement on the SHIPPED render either.  That is
    # `an unguarded arm reading is how a window defect reads as the physics failing` (s122 W1b)
    # pointed at the baseline instead of the arm.  Each feature is screened at the first
    # (capture, sweep) -- mix capture before bleed-free, loudest sweep first -- where the SHIPPED
    # render gives a valid reading, and reported NOT MEASURABLE if there is none.  Never as damage.
    ref = {}
    for fn in names:
        ref[fn] = next(((c, sw) for c in screen for sw in reversed(W.SWEEPS)
                        if _valid(got[(c, "ship")][sw][fn])), None)
    unmeasurable = [fn for fn in names if ref[fn] is None]
    print(f"  screened at {len(screen)} captures: {screen[0]} (the MIX detent -- where the bass\n"
          f"  cancellations live) and {screen[1] if len(screen) > 1 else '(none)'} (BLEED-FREE, "
          f"LEVEL = 1 -- where GATE W resolves the mid\n  and bridged-T features).  Each column "
          f"names the (capture, sweep) its baseline is valid at.")
    if unmeasurable:
        print(f"  NOT MEASURABLE on the shipped render at either capture (so NOT screened, and "
              f"NOT 'damaged'): {unmeasurable}")
    print()
    print("  " + f"{'candidate':<22s}" + " ".join(f"{n.replace('_',''):>11s}" for n in names))
    print("  " + f"{'capture':<22s}" +
          " ".join(f"{('mix' if ref[n] and ref[n][0] == cap else 'bleedfree' if ref[n] else '-'):>11s}"
                   for n in names))
    print("  " + f"{'sweep':<22s}" +
          " ".join(f"{(ref[n][1].replace('sweep_','') if ref[n] else '-'):>11s}" for n in names))
    print("  " + f"{'shipped (Hz)':<22s}" +
          " ".join((f"{got[(ref[n][0], 'ship')][ref[n][1]][n]['f0']:11.1f}" if ref[n]
                    else f"{'-':>11s}") for n in names))
    rows = {}
    for n in reach:
        cells_out, r = [], {}
        for fn in names:
            if ref[fn] is None:
                r[fn] = None
                cells_out.append(f"{'-':>11s}")
                continue
            c, sw = ref[fn]
            b = got[(c, "ship")][sw][fn]["f0"]
            cur = got[(c, tags[n])][sw][fn]
            dv = (cur["f0"] - b) / b
            ok = _valid(cur)
            r[fn] = {"capture": c, "sweep": sw, "f0": cur["f0"], "d_frac": dv, "valid": bool(ok)}
            cells_out.append(f"{dv*100:+10.1f}%" if ok else f"{dv*100:+10.1f}!")
        print("  " + f"{n + ' x' + format(picks[n], '.3g'):<22s}" + " ".join(cells_out))
        rows[n] = r
    print(f"  '!' = valid on the shipped render and NOT on this one -- the candidate dissolved it, "
          f"which is\n        damage the % alone does not show.")

    # ---- Y7b -----------------------------------------------------------------------------------
    # ⚠⚠ AN INVALID READING ABOVE IS NOT YET A FINDING, AND THE FIRST RUN'S OUTPUT SAID SO OUT LOUD:
    # BOTH candidates, at DIFFERENT constants and DIFFERENT multiples, reported the SAME two deltas
    # (+6.8 %, -14.1 %).  Two independent moves cannot agree to the digit
    # (`an-implausible-coincidence-is-a-bug-report`), and the cause is that `mid_notch` (a min over
    # 285-358) ran to 352.0 and `mid_peak` (a max over 358-620) ran to 357.1 -- both pinned to the
    # SHARED 358 Hz boundary, from opposite sides.  So the table was reporting a WINDOW EDGE twice,
    # not a measurement, and "DISSOLVED" was an inference from it.
    #
    # ⇒ MOVED and DISSOLVED are different findings with different consequences -- a notch that
    # slid 15 % is a re-tune, a notch that flattened is the loss of GAP #2 -- and an edge reading
    # cannot tell them apart (s122 W1b: a window that no longer contains the moved feature reads as
    # the physics failing).  So each invalidated feature is re-located in a window widened by
    # `WIDEN`, and the discriminator is PROMINENCE, printed against the shipped render's own.
    print(f"\n  Y7b  every reading marked '!' above, re-asked of the most prominent INTERIOR "
          f"extremum in a\n       {WIDEN:.1f}x-widened window -- MOVED (still prominent, just "
          f"relocated) or DISSOLVED (flattened)?")
    print(f"       ⚠ BOTH sides are read with the SAME estimator in the SAME widened window, so "
          f"the two\n       prominences are a matched pair; the narrow-window `prom` is not "
          f"comparable to a wide one.")
    # ⚠⚠ KNOWN ANSWER FIRST, AND IT IS THE ONLY THING THAT MAKES "DISSOLVED" BELIEVABLE.  A silent
    # estimator is indistinguishable from an absent feature, so before `_best_interior`'s silence
    # on a CANDIDATE is read as damage, it must be shown to FIND the feature on the BASELINE --
    # in the same widened window, where it has far more room to go wrong.  The bar is the locator's
    # own agreement with itself: the wide interior search must land on the narrow `locate` centre.
    # (This is also the mutation that matters here: the estimator demonstrably returns a large
    # prominence in one arm and zero in the other, so it can fail in both directions.)
    for fn in sorted({f for n in reach for f in names
                      if rows[n][f] is not None and not rows[n][f]["valid"]}):
        c, sw = ref[fn]
        nar = got[(c, "ship")][sw][fn]
        wid = got[(c, "ship")][sw]["_wide"][fn]
        agree = (np.isfinite(wid["f0"]) and abs(wid["f0"] - nar["f0"]) / nar["f0"] <= KA_TOL_FRAC)
        print(f"       KA  {fn:<10s} shipped: narrow {nar['f0']:7.1f} Hz -> wide-interior "
              f"{wid['f0']:7.1f} Hz  ({wid['n_interior']} interior extrema, prom "
              f"{wid['prom']:.2f} dB)  {'OK' if agree else 'FAIL'}")
        if not agree:
            sys.exit(f"GATE Y7b: the widened interior search does not recover `{fn}` on the "
                     f"SHIPPED render ({wid['f0']:.1f} vs {nar['f0']:.1f} Hz).  It is therefore "
                     f"not measuring the same feature, and its silence on a candidate is a "
                     f"property of the estimator, not of the candidate -- fix it before reading "
                     f"any MOVED/DISSOLVED verdict below.")

    wide = {}
    for n in reach:
        for fn in names:
            v = rows[n][fn]
            if v is None or v["valid"]:
                continue
            c, sw = ref[fn]
            w_ship = got[(c, "ship")][sw]["_wide"][fn]
            w_cand = got[(c, tags[n])][sw]["_wide"][fn]
            lo, hi = W.FEAT_BY_NAME[fn][2]
            moved = w_cand["prom"] >= W.MIN_PROM_DB
            dv = ((w_cand["f0"] - w_ship["f0"]) / w_ship["f0"]
                  if np.isfinite(w_cand["f0"]) and np.isfinite(w_ship["f0"]) else float("nan"))
            wide[(n, fn)] = {"f0": w_cand["f0"], "prom": w_cand["prom"],
                             "f0_ship": w_ship["f0"], "prom_ship": w_ship["prom"],
                             "n_interior": w_cand["n_interior"],
                             "moved": bool(moved), "d_frac": dv}
            verdict = (f"MOVED {dv*100:+.1f} %" if moved else
                       f"DISSOLVED (best interior prominence {w_cand['prom']:.2f} dB is under the "
                       f"{W.MIN_PROM_DB:.1f} dB bar; {w_cand['n_interior']} interior extrema)")
            print(f"       {n:<13s} {fn:<10s} {lo:.0f}-{hi:.0f} -> {lo/WIDEN:.0f}-{hi*WIDEN:.0f} Hz:"
                  f"  {w_ship['f0']:7.1f} -> {w_cand['f0']:7.1f} Hz   "
                  f"prom {w_ship['prom']:5.2f} -> {w_cand['prom']:5.2f} dB   {verdict}")
    if not wide:
        print("       (nothing was invalidated -- no re-location needed)")

    print(f"\n  the ones GATE W says we currently have RIGHT, and which this move must not break:")
    verdicts = {}
    for n in reach:
        verdict = "CLEAN"
        for fn in ("mid_notch", "mid_peak"):
            v = rows[n][fn]
            if v is None:
                print(f"    {n:<15s} {fn:<10s} NOT MEASURABLE on the baseline -- unscreened")
                verdict = "UNSCREENED" if verdict == "CLEAN" else verdict
                continue
            w = wide.get((n, fn))
            where = (f"{v['sweep'].replace('sweep_','')}/"
                     f"{'mix' if v['capture'] == cap else 'bleedfree'}")
            if w is None:                       # valid in its own window: the % IS the damage
                print(f"    {n:<15s} {fn:<10s} {v['d_frac']*100:+6.1f} % at {where}")
                if abs(v["d_frac"]) > W.GRID_STEP_FRAC:
                    verdict = "PAYS"
            elif w["moved"]:
                print(f"    {n:<15s} {fn:<10s} MOVED {w['d_frac']*100:+6.1f} % at {where} "
                      f"(prom {w['prom_ship']:.2f} -> {w['prom']:.2f} dB)")
                if abs(w["d_frac"]) > W.GRID_STEP_FRAC:
                    verdict = "PAYS"
            else:
                print(f"    {n:<15s} {fn:<10s} DISSOLVED at {where} "
                      f"(prom {w['prom_ship']:.2f} -> {w['prom']:.2f} dB, and nothing prominent "
                      f"in the widened window)")
                verdict = "PAYS"
        print(f"    {n:<15s} -> {verdict}")
        verdicts[n] = verdict
    print(f"\n  ⚠ a SHAPE screen at TWO captures. It cannot price the move -- that is the "
          f"162-capture\n    matrix's job, and it is deliberately NOT run here "
          f"(`score the candidate you will actually emit`).")
    out["y7"] = {"reaching": reach, "picks": picks, "screen": screen,
                 "ref": {n: (list(ref[n]) if ref[n] else None) for n in names},
                 "unmeasurable": unmeasurable, "verdicts": verdicts,
                 "widen": WIDEN,
                 "y7b": {f"{n}|{fn}": v for (n, fn), v in wide.items()},
                 "shipped": {n: (got[(ref[n][0], "ship")][ref[n][1]][n]["f0"] if ref[n] else None)
                             for n in names},
                 "rows": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=REPORT)
    ap.add_argument("--jobs", type=int, default=None)
    ap.add_argument("--quick", action="store_true", help="Y1 + Y2 only")
    ap.add_argument("--out", default=OUT_JSON)
    a = ap.parse_args()

    if not os.path.exists(a.report):
        sys.exit(f"GATE Y: {a.report} is absent -- the LEVEL ladder's membership is resolved from "
                 f"the report's own settings, never from filenames (s114).")
    # Keyed by filename the way GATE W keys it — ONE definition of the ladder's membership.
    caps = {c["file"]: c for c in json.load(open(a.report))["captures"]}
    lad = W.level_ladder(caps)
    if len(lad) < 6:
        sys.exit(f"GATE Y: the LEVEL ladder has only {len(lad)} detents -- Y1's locus needs the "
                 f"ladder, and a short one is a membership defect, not a weak result.")
    os.makedirs(REN_DIR, exist_ok=True)
    print("=" * 92)
    print("GATE Y -- LOCALISE THE MODEL'S BASS PEAK (session 126, s125 NEXT item 0)")
    print("=" * 92)
    print(f"  report {a.report}   ladder {len(lad)} detents {sorted(lad)}")

    out = {"report": a.report, "w_report": W_REPORT, "sweep": SWEEP, "os": OS_FACTOR,
           "window": list(WIN), "candidates": [list(c) for c in CANDIDATES]}
    base = gate_y1(lad, out, a.jobs)
    lv, cap, b = gate_y2(lad, base, out, a.jobs)
    if not a.quick:
        sens = gate_y3(cap, b, out, a.jobs)
        gate_y4(base, sens, out)
        gate_y5(cap, b, sens, out, a.jobs)
        gate_y6(cap, sens, out, a.jobs)
        gate_y7(cap, lad, sens, out, a.jobs)
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
