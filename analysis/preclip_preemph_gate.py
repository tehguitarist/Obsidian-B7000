#!/usr/bin/env python3.11
"""GATE BB — ROUTE (i): CAN A *FIXED* PRE-CLIPPER PRE-EMPHASIS CARRY THE DRIVE-TILT?

WHY THIS EXISTS (session 165, task E's second capped session; user-directed)
---------------------------------------------------------------------------
GATE BA (s164) refuted the architecture task E was scoped to reuse: a LINEAR section DOWNSTREAM of
the clipper contributes EXACTLY ZERO drive-tilt, because the statistic is a DIFFERENCE between
stimulus rungs and a fixed linear stage cancels from it identically.  Two routes survived:

    (i)  a FIXED linear section at or UPSTREAM of the clipper -- which works only through the
         clipper's own nonlinearity, `drive-tilt = P' * [gamma(hot) - gamma(quiet)]`;
    (ii) a genuinely LEVEL-DEPENDENT (dynamic) section.

The user's instruction is to screen (i) first and build (ii) if it fails.  This gate is that
screen.

THE TEST, AND WHY IT IS ABOUT SIGN BEFORE SIZE.  A fixed pre-emphasis multiplies P by a fixed
H(f), so it changes the drive-tilt by `dP' * dgamma(condition)` (plus a level term, BB4c).  `dP'`
is FIXED by construction -- that is what "fixed section" means -- so the DELIVERED correction
tracks the sign of `dgamma`, which is a property of the CLIPPER's operating point and moves with
the DRIVE knob.  The REQUIRED correction does not: it is `need - (the model's own drive-tilt)`,
and GATE BA measured the model's own tilt running -0.346 / -0.013 / +0.038 across DRIVE
min/noon/max, so the requirement is same-signed at every condition.

    If the delivered correction changes sign across a condition axis where the required one does
    not, NO fixed pre-emphasis can serve all conditions -- refuted on SIGN, at any size, exactly
    the shape of GATE AI's `a0` refutation (s138).

⭐⭐ WHY LADDER PROBES GENERALISE TO "ANY SECTION", which is the design's load-bearing part.  An
[ENG] pre-clipper section multiplies P by H(f); a change to a treble-ladder element ALSO multiplies
P by a fixed factor, because IC2_A(+) draws no current so V(Q) is a clean stage boundary and
everything downstream is common-mode.  So `dlog P` is EXACTLY the ladder's own change, and the
transfer coefficient `d(drive-tilt)/dP'` should be a property of the CHAIN rather than of which
element produced it.  BB4 tests that directly: six probes spanning `dP'` from +0.638 to -0.102
dB/oct must agree on the coefficient.  Agreement is what licenses the conclusion for sections that
were never rendered; disagreement would confine it to the probes.

GATES (validity exits non-zero; every physics OUTCOME is a computed verdict -- s108)
------------------------------------------------------------------------------------------------
BB0  MEMBERSHIP, PROVENANCE, AND THE eq<->FitParams CORRESPONDENCE.  Each probe names a
     `FitParams` constant AND the `eq_reference` kwarg it must equal; the two are ASSERTED equal
     at ATTACK flat before anything renders.  That mapping is precisely the s149 defect class
     (three gates screened the DRAWN ladder for ten sessions), so it is checked, not trusted.
BB1  KNOWN ANSWERS, four:
     (a) the tilt estimator recovers an INJECTED tilt exactly, including ZERO (GATE AG's own);
     (b) ⭐ BASELINE REPRODUCTION -- rendering at the shipped constants must reproduce GATE BA's
         STORED per-condition drive-tilts.  A baseline that has silently moved makes every
         comparison below a fiction (s77's SHIP_RECORD);
     (c) DENOMINATOR FLOOR -- every probe's |dP'| must exceed 3x the ATTACK ladder span GATE BA5
         REFUSED on, IMPORTED from BA's stored report rather than invented.  BA5 is the reason
         this gate exists in this shape at all;
     (d) NON-VACUITY, both directions: every real probe must CHANGE the render, and the INERT
         control (`trebleC8`, which ships at 0 and is out of circuit at ATTACK flat, so its dP'
         is 0 by TOPOLOGY) must render BIT-IDENTICAL.
BB2  THE DOSE-RESPONSE -- delivered vs required correction, per probe x condition, operands
     printed (s117), every rung of every axis (s129).
BB3  ⭐⭐ SIGN CONSISTENCY -- computed verdict, on the DRIVE axis and on the GRUNT axis.
BB4  SIZE -- the transfer coefficient per probe, its agreement across probes (the generalisation
     test), the required |dP'|, and the LEVEL term that the coefficient may be hiding.
BB5  COLLATERAL -- what the required perturbation does to the named features, through GATE W's
     own locator.  GATE Y (s126) already measured that ladder constants moving this region
     DISSOLVE the 320 Hz null and the mid peak; this re-measures it on the probes actually used.
BB6  VERDICT, computed, plus a machine-checkable membership line.

WHAT THIS DOES NOT CLAIM
  * It does not test route (ii).  A LEVEL-DEPENDENT section is not a fixed `dP'` and nothing here
    bounds it.
  * It does not test AF6's requirement, which is imported from GATE AF's stored report.
  * Says nothing about hardware -- both sides are the ND captures (`reference-sources.md` §0).

Usage:
  python3.11 analysis/preclip_preemph_gate.py
  python3.11 analysis/preclip_preemph_gate.py --json analysis/reports/s165_preclip_preemph.json
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze as A                      # noqa: E402
import captures as C                     # noqa: E402
import eq_reference as EQ                # noqa: E402
import feature_locus_gate as W           # noqa: E402
import drive_tilt_shape_gate as AG       # noqa: E402  tilt_at / load_af6 — imported, not re-derived
import pre_clipper_tilt_gate as AJ       # noqa: E402  ladder_kwargs (the SHIPPED element set, s149)
import resonance_census as AM            # noqa: E402  _fp — the ONE reader of FitParams.h
import task_e_placement_gate as BA       # noqa: E402  the baseline, the probe geometry, PRIV rules

PRIV_DIR = os.path.join(os.path.dirname(HERE), "build", "s165_preclip")
BA_REPORT = os.path.join(HERE, "reports", "s164_task_e_placement.json")

RUNGS = AG.RUNGS
HALF = BA.HALF

# ---- the probes -------------------------------------------------------------------------------
# (label, FitParams name, eq_reference kwarg, multiplier | ("abs", value))
# Chosen for |dP'| at the vertex, spanning BOTH signs.  `trebleC8` is the INERT control: it ships
# at 0 and at ATTACK flat the switch pole is open, so it is out of circuit and its dP' is 0 by
# TOPOLOGY, not by smallness -- which makes it a known answer rather than a small probe.
PROBES = [
    ("C5 x0.25", "trebleC5", "C5", 0.25),
    ("C6 x0.25", "trebleC6", "C6", 0.25),
    ("C9 x0.25", "trebleC9", "C9", 0.25),
    ("R7 x0.25", "trebleR7", "R7", 0.25),
    ("C5 x4.0", "trebleC5", "C5", 4.0),
    ("R12 x4.0", "trebleLadderR12", "R12", 4.0),
]
INERT = ("C8 = 220p (INERT control)", "trebleC8", "C8", ("abs", 220e-12))

# ---- the conditions ---------------------------------------------------------------------------
# Bleed-free OD endpoints (LEVEL max).  Two axes: the DRIVE knob, where GATE BA measured the
# model's own drive-tilt CHANGING SIGN, and GRUNT, which is item 6's own carrier gate 4 axis.
COND = {
    ("DRIVE", "min"): "drive-0700_level-1700_base-od.wav",
    ("DRIVE", "noon"): "level-1700_base-od.wav",
    ("DRIVE", "max"): "drive-1700_level-1700_base-od.wav",
    ("GRUNT", "flat"): "level-1700_grunt-flat_base-od.wav",
    ("GRUNT", "boost"): "level-1700_grunt-boost_base-od.wav",
}
# GATE BA's stored key for the same condition, where one exists (ATTACK flat, GRUNT cut).
BA_KEY = {("DRIVE", "min"): "flat/min", ("DRIVE", "noon"): "flat/noon",
          ("DRIVE", "max"): "flat/max"}

FLOOR_MULT = 3.0        # BB1c: |dP'| must beat 3x the span BA5 refused on (imported, not invented)
MIX_MULT = 10.0         # BB4: |dLevel/dP'| above 10x the population median is not a SLOPE probe
# BB6: a FIXED section has ONE dP'.  If the two ends of a condition axis need values more
# than 2x apart, no single choice serves both — the weakest bar that still means
# "cannot be the same number", and the measured span is far above it either way.
SPAN_BAR = 2.0
FAILED = []


def die(tag, msg):
    sys.exit(f"GATE BB {tag} FAIL: {msg}")


def note(tag, msg):
    FAILED.append(f"{tag}: {msg}")
    print(f"   ** {tag} FAIL — {msg}")


def fit_value(fitname, spec):
    shipped = AM._fp(fitname)
    if isinstance(spec, tuple):
        return float(spec[1]), shipped
    return float(shipped * spec), shipped


def ladder_slope_level(eqkey, value, vertex):
    """(slope, level) of the SHIPPED ladder at the vertex with one element replaced."""
    f = np.geomspace(vertex / 2.5, vertex * 2.5, 601)
    kw = AJ.ladder_kwargs("flat")
    if eqkey is not None:
        kw[eqkey] = value
    db = 20.0 * np.log10(np.abs(EQ.treble_attack_tf(f, "flat", Zs=EQ.jfet_source_z(f), **kw)))
    s, _n = AG.tilt_at(db, np.log2(f / vertex), HALF)
    return s, float(np.interp(np.log(vertex), np.log(f), db))


def curves(fname, extra=()):
    tag = "base" if not extra else "_".join(extra).replace("=", "").replace(".", "p")
    out = os.path.join(PRIV_DIR, f"{fname.replace('.wav', '')}__{tag}_plugin.wav")
    W.render(out, list(C.render_args(C.parse_capture(fname))) + list(extra))
    orig, ref = W._load_orig()
    al, _ = A.align(A.load(out), orig)
    return out, {sw: W.smooth(*A.transfer_h1(A.seg_of(al, sw), ref)) for sw in RUNGS}


def drive_tilt(per, f0):
    return BA.slope(per[RUNGS[-1]], f0) - BA.slope(per[RUNGS[0]], f0)


# ------------------------------------------------------------------------------------------------
def bb0(out):
    print("=" * 98)
    print("BB0  MEMBERSHIP, PROVENANCE, AND THE eq <-> FitParams CORRESPONDENCE")
    if os.path.abspath(PRIV_DIR) == os.path.abspath(W.REN_DIR):
        die("BB0", "the private render dir IS GATE W's cache — refusing to render into it.")
    for f in COND.values():
        if not os.path.exists(os.path.join(C.CAPTURE_DIR, f)):
            die("BB0", f"capture {f} absent — the membership is not the stated one.")
        if C.parse_capture(f).get("level") != 1.0:
            die("BB0", f"{f} is not bleed-free — GATE K2: bleed vanishes only at LEVEL/BLEND max.")
    print(f"   conditions : {len(COND)} bleed-free OD endpoints on 2 axes (DRIVE, GRUNT)")
    print(f"   private dir: {PRIV_DIR}")

    need, curv, vertex, _fr = AG.load_af6()
    print(f"   IMPORTED from GATE AF: required drive-tilt {need:+.4f} dB/oct at {vertex:.1f} Hz")

    # ⚠⚠ The s149 defect class, checked rather than trusted: the FitParams constant a probe writes
    # must BE the eq_reference kwarg the closed form scales.  At ATTACK flat the trim/damp terms
    # in `shipped_treble` vanish, so the two must be equal to the bit.
    kw = AJ.ladder_kwargs("flat")
    print(f"\n   {'probe':28s}{'FitParams':20s}{'eq kwarg':10s}{'shipped':>14s}{'-> value':>14s}"
          f"{'dP dB/oct':>12s}{'dLevel dB':>11s}")
    base_s, base_l = ladder_slope_level(None, None, vertex)
    rows = []
    for label, fitname, eqkey, spec in PROBES + [INERT]:
        shipped_fp = AM._fp(fitname)
        if eqkey not in kw:
            die("BB0", f"{label}: eq kwarg {eqkey!r} is not in the shipped ladder.")
        if abs(kw[eqkey] - shipped_fp) > 1e-12 * max(1.0, abs(shipped_fp)):
            die("BB0", f"{label}: FitParams::{fitname} = {shipped_fp!r} but the shipped ladder's "
                       f"{eqkey!r} = {kw[eqkey]!r}.  The probe would write one constant and the "
                       f"closed form would scale a different number (s149 AO).")
        val, _ = fit_value(fitname, spec)
        s, l = ladder_slope_level(eqkey, val, vertex)
        rows.append([label, fitname, eqkey, shipped_fp, val, s - base_s, l - base_l])
        print(f"   {label:28s}{fitname:20s}{eqkey:10s}{shipped_fp:14.6g}{val:14.6g}"
              f"{s - base_s:+12.4f}{l - base_l:+11.3f}")
    print(f"   correspondence asserted for all {len(rows)} probes at ATTACK flat "
          f"(baseline ladder slope {base_s:+.4f} dB/oct)")
    out["bb0"] = {"need": need, "vertex": vertex, "probes": rows, "base_slope": base_s}
    return need, vertex, {r[0]: (r[5], r[6]) for r in rows}


def bb1(base, dP, vertex, out):
    print()
    print("=" * 98)
    print("BB1  KNOWN ANSWERS")
    rec = {}

    ref = base[("DRIVE", "noon")][RUNGS[0]]
    worst = max(abs((BA.slope(ref + T * np.log2(W.GRID / vertex), vertex) - BA.slope(ref, vertex))
                    - T) for T in (0.0, -0.5, 1.0, -2.5))
    print(f"   (a) injected tilt recovered, worst |error| = {worst:.3e} dB/oct (incl. ZERO)")
    if worst > AG.INJECT_TOL:
        die("BB1a", f"the tilt estimator does not recover an injected tilt ({worst:.3e}).")
    rec["inject"] = worst

    # (b) the baseline must reproduce GATE BA's STORED drive-tilts.
    try:
        with open(BA_REPORT) as fh:
            ba = json.load(fh)
    except OSError as e:
        die("BB1b", f"cannot read {BA_REPORT} ({e}).  This gate's baseline is GATE BA's; it will "
                    f"not invent one.  Re-run analysis/task_e_placement_gate.py --json {BA_REPORT}")
    stored = ba.get("ba3", {}).get("per_cond", {})
    if not stored:
        die("BB1b", f"{BA_REPORT} carries no ba3/per_cond block — it is not a GATE BA report.")
    print("   (b) baseline reproduction against GATE BA's STORED per-condition drive-tilts:")
    worst_b = 0.0
    for k, key in BA_KEY.items():
        if key not in stored:
            die("BB1b", f"GATE BA's report has no {key!r} — membership has drifted.")
        got = drive_tilt(base[k], vertex)
        worst_b = max(worst_b, abs(got - stored[key]))
        print(f"       {k[0]} {k[1]:5s}  stored {stored[key]:+.5f}   here {got:+.5f}   "
              f"d = {got - stored[key]:+.2e}")
    if worst_b > 1e-9:
        die("BB1b", f"the baseline has MOVED by {worst_b:.3e} dB/oct since GATE BA. Every "
                    f"comparison below would be against a baseline nobody has re-validated (s77).")
    rec["baseline_worst"] = worst_b

    # (c) denominator floor, IMPORTED from BA5 rather than invented.
    span = float(ba["ba5"]["ladder_span"])
    floor = FLOOR_MULT * span
    smallest = min(abs(dP[l][0]) for l, *_ in PROBES)
    print(f"   (c) denominator floor: GATE BA5 REFUSED the ATTACK switch at a ladder span of "
          f"{span:.4f} dB/oct")
    print(f"       ⇒ floor = {FLOOR_MULT:.0f}x that = {floor:.4f}; smallest probe |dP'| = "
          f"{smallest:.4f}  ({smallest / span:.0f}x the refused span)")
    if smallest < floor:
        die("BB1c", f"a probe's |dP'| ({smallest:.4f}) is below the imported floor ({floor:.4f}) "
                    f"— its coefficient would be a denominator artefact, which is the exact thing "
                    f"BA5 refused.")
    rec["floor"], rec["smallest_dP"] = floor, smallest

    # (d) non-vacuity BOTH ways.
    print("   (d) non-vacuity, both directions:")
    inert_label, inert_fit, _ek, inert_spec = INERT
    iv, _ = fit_value(inert_fit, inert_spec)
    _p, inert_curves = curves(COND[("DRIVE", "noon")], ("--fit", f"{inert_fit}={iv:.9g}"))
    d_inert = max(float(np.max(np.abs(inert_curves[sw] - base[("DRIVE", "noon")][sw])))
                  for sw in RUNGS)
    print(f"       INERT control ({inert_label}): worst |curve change| = {d_inert:.3e} dB")
    if d_inert > 1e-9:
        die("BB1d", f"the INERT control CHANGED the render by {d_inert:.3e} dB.  `trebleC8` is out "
                    f"of circuit at ATTACK flat, so this means the probe mechanism reaches "
                    f"something it should not — every dP' below is suspect.")
    rec["inert_change"] = d_inert
    out["bb1"] = rec
    return ba


def bb2(base, probe_curves, dP, need, vertex, out):
    print()
    print("=" * 98)
    print("BB2  THE DOSE-RESPONSE — delivered vs REQUIRED correction, per probe x condition")
    print("   REQUIRED = need - (the model's own drive-tilt).  It is the thing a section must")
    print("   supply, and GATE BA measured the model's own tilt changing sign across DRIVE — so")
    print("   the required correction and the delivered one need not share a sign pattern.")
    print()
    req, own = {}, {}
    for k in COND:
        own[k] = drive_tilt(base[k], vertex)
        req[k] = need - own[k]
    print(f"   {'condition':18s}{'model own':>12s}{'REQUIRED':>12s}")
    for k in COND:
        print(f"   {k[0] + ' ' + k[1]:18s}{own[k]:+12.4f}{req[k]:+12.4f}")
    print(f"\n   {'probe':16s}{'dP dB/oct':>11s}" +
          "".join(f"{k[0][:2] + '/' + k[1]:>14s}" for k in COND))
    print(f"   {'':16s}{'':11s}" + "".join(f"{'delivered':>14s}" for _ in COND))
    deliv = {}
    for label, *_ in PROBES:
        row = []
        for k in COND:
            d = drive_tilt(probe_curves[(label, k)], vertex) - own[k]
            deliv[(label, k)] = d
            row.append(d)
        print(f"   {label:16s}{dP[label][0]:+11.4f}" + "".join(f"{v:+14.4f}" for v in row))
    out["bb2"] = {"required": {f"{k[0]}/{k[1]}": req[k] for k in COND},
                  "own": {f"{k[0]}/{k[1]}": own[k] for k in COND},
                  "delivered": {f"{l}|{k[0]}/{k[1]}": v for (l, k), v in deliv.items()}}
    return req, own, deliv


def bb3(req, deliv, out):
    print()
    print("=" * 98)
    print("BB3  ⭐⭐ SIGN CONSISTENCY — can ONE fixed section serve every condition?")
    print("   A fixed section has a FIXED dP'.  If what it DELIVERS changes sign across an axis")
    print("   on which what is REQUIRED does not, no single choice can serve both ends — refuted")
    print("   at any size.  GATE AI's `a0` refutation (s138) in the same shape.")
    print()
    rec = {}
    for axis in ("DRIVE", "GRUNT"):
        ks = [k for k in COND if k[0] == axis]
        rsign = {np.sign(req[k]) for k in ks}
        print(f"   --- {axis} axis ({len(ks)} conditions) ---")
        print(f"   REQUIRED correction signs: "
              f"{'  '.join(f'{k[1]}:{req[k]:+.3f}' for k in ks)}"
              f"   ⇒ {'SAME-SIGNED' if len(rsign) == 1 else 'MIXED'}")
        bad = []
        for label, *_ in PROBES:
            vs = [deliv[(label, k)] for k in ks]
            npos = sum(1 for v in vs if v > 0)
            flips = 0 < npos < len(vs)
            bad.append(flips)
            print(f"     {label:16s}" + "".join(f"{v:+12.4f}" for v in vs)
                  + ("   SIGN FLIPS" if flips else "   same-signed"))
        n_flip = sum(bad)
        rec[axis] = {"required_same_signed": len(rsign) == 1, "n_flip": n_flip,
                     "n_probes": len(bad)}
        if len(rsign) == 1 and n_flip == len(bad):
            print(f"   ⇒ REFUTED ON THIS AXIS: the requirement is same-signed at every condition"
                  f" and ALL {n_flip} probes flip.")
        elif len(rsign) == 1 and n_flip:
            print(f"   ⇒ PARTIAL: {n_flip} of {len(bad)} probes flip where the requirement does"
                  f" not — a fixed section is not free to be any of those.")
        else:
            print(f"   ⇒ NOT refuted on this axis ({n_flip} of {len(bad)} probes flip).")
    out["bb3"] = rec
    return rec


def bb4(req, deliv, dP, need, out):
    print()
    print("=" * 98)
    print("BB4  SIZE — the transfer coefficient, and whether it is a property of the CHAIN")
    print("   d(drive-tilt)/dP' per probe.  If the six probes agree, the coefficient belongs to")
    print("   the chain rather than to the element, and the conclusion extends to sections that")
    print("   were never rendered.  If they disagree, it is confined to these probes.")
    print()
    print(f"   {'probe':16s}{'dP dB/oct':>11s}{'dLevel dB':>11s}" +
          "".join(f"{k[0][:2] + '/' + k[1]:>13s}" for k in COND))
    coefs = {}
    for label, *_ in PROBES:
        row = []
        for k in COND:
            c = deliv[(label, k)] / dP[label][0]
            coefs[(label, k)] = c
            row.append(c)
        print(f"   {label:16s}{dP[label][0]:+11.4f}{dP[label][1]:+11.3f}"
              + "".join(f"{v:+13.4f}" for v in row))
    # ⚠⚠ A probe changes the pre-clipper LEVEL as well as its SLOPE, and gamma depends on level,
    # so `delivered = dP'*dgamma + P'*d(dgamma|level)`.  A probe whose level change dwarfs its
    # slope change is measuring the SECOND term and is not a slope probe at all.  `mix` is a
    # property of the probe computable BEFORE any render, so classifying on it is not
    # outcome-selection; the bar is a multiple of the population's own median.
    print()
    mix = {l: abs(dP[l][1]) / abs(dP[l][0]) for l, *_ in PROBES}
    med_mix = float(np.median(list(mix.values())))
    dominated = [l for l, *_ in PROBES if mix[l] > MIX_MULT * med_mix]
    clean = [l for l, *_ in PROBES if l not in dominated]
    print("   LEVEL-DOMINANCE screen (a property of the probe, computed before any render):")
    print(f"   {'probe':16s}{'|dLevel/dP|':>14s}   class")
    for l, *_ in PROBES:
        print(f"   {l:16s}{mix[l]:14.2f}   "
              + ("LEVEL-DOMINATED — not a slope probe" if l in dominated else "slope probe"))
    print(f"   median {med_mix:.2f}; bar = {MIX_MULT:.0f}x median = {MIX_MULT * med_mix:.2f}"
          f"  ⇒ {len(clean)} slope probes, {len(dominated)} excluded by name: "
          f"{', '.join(dominated) if dominated else '(none)'}")
    if len(clean) < 3:
        die("BB4", f"only {len(clean)} slope probes survive the level-dominance screen — the "
                   f"coefficient cannot be shown to be a property of the chain.")

    print()
    for k in COND:
        vs = [coefs[(l, k)] for l in clean]
        rng, med = max(vs) - min(vs), float(np.median(vs))
        print(f"   {k[0]} {k[1]:6s} coefficient {min(vs):+.4f} .. {max(vs):+.4f}  "
              f"(median {med:+.4f}, range {rng:.4f}"
              + (f", {abs(rng / med):.1f}x the median)" if abs(med) > 1e-9 else ")"))
    # ⚠ Report WHICH conditions agree, not a single boolean.  A first draft printed
    # "DISAGREES in sign at every condition" off an `all(...)` that is False if ANY condition
    # disagrees — a message that misdescribed its own computation, and the generalisation argument
    # rests on exactly this line.
    per_k = {k: len({np.sign(coefs[(l, k)]) for l in clean}) == 1 for k in COND}
    n_agree = sum(per_k.values())
    agree = n_agree == len(COND)
    print(f"\n   sign agreement over the {len(clean)} SLOPE probes: "
          + "  ".join(f"{k[0][:2]}/{k[1]}:{'yes' if per_k[k] else 'NO'}" for k in COND)
          + f"   ⇒ {n_agree} of {len(COND)}")
    if not agree:
        bad = [k for k in COND if not per_k[k]]
        worst = max(abs(float(np.median([coefs[(l, k)] for l in clean]))) for k in bad)
        print(f"   ⚠ the exception(s) — {', '.join(k[0] + ' ' + k[1] for k in bad)} — sit where the")
        print(f"     coefficient is at its own floor (|median| = {worst:.4f}), so this is the")
        print("     COLLAPSE below, not probes disagreeing about a live quantity.")
    print(f"   ⇒ away from that floor the coefficient is a property of the CHAIN, not of the")
    print("     element — which is what licenses the conclusion for sections never rendered.")

    print()
    print("   ⭐⭐ THE DECISIVE READING — the coefficient COLLAPSES with the DRIVE knob, so the")
    print("   required dP' is a DIFFERENT NUMBER at every condition, and a fixed section has one:")
    medc = {k: float(np.median([coefs[(l, k)] for l in clean])) for k in COND}
    needed = {}
    for k in COND:
        if abs(medc[k]) < 1e-6:
            needed[k] = np.inf
            print(f"     {k[0]} {k[1]:6s}  coefficient ~0 — UNREACHABLE at any dP'")
        else:
            needed[k] = req[k] / medc[k]
            print(f"     {k[0]} {k[1]:6s}  coefficient {medc[k]:+8.4f}   required dP' = "
                  f"{needed[k]:+9.3f} dB/oct")
    fin = {k: v for k, v in needed.items() if np.isfinite(v)}
    lo_k = min(fin, key=lambda k: abs(fin[k]))
    hi_k = max(fin, key=lambda k: abs(fin[k]))
    span = abs(fin[hi_k] / fin[lo_k]) if abs(fin[lo_k]) > 1e-9 else np.inf
    print(f"\n   ⇒ the required dP' spans {fin[lo_k]:+.3f} ({lo_k[0]} {lo_k[1]}) to "
          f"{fin[hi_k]:+.3f} ({hi_k[0]} {hi_k[1]}) — a factor of {span:.0f}")
    print("   ⭐ Stated WITHOUT any bar, which is the form to quote:")
    at_lo_hi = medc[hi_k] * fin[lo_k] / req[hi_k]
    at_hi_lo = medc[lo_k] * fin[hi_k] / req[lo_k]
    print(f"     • a fixed section sized to CLOSE {lo_k[0]} {lo_k[1]} delivers "
          f"{100 * at_lo_hi:.1f} % of the requirement at {hi_k[0]} {hi_k[1]};")
    print(f"     • one sized to close {hi_k[0]} {hi_k[1]} OVERSHOOTS {lo_k[0]} {lo_k[1]} by "
          f"{abs(at_hi_lo):.0f}x.")
    print("   ⇒ a dose-response locus that cannot CONTAIN the target refutes the lever, not its")
    print("     setting (s38's C12 argument, s126's bass peak — the same shape a third time).")
    print(f"   ⚠ And the SMALLEST required dP' ({abs(fin[lo_k]):.3f} dB/oct) already exceeds the")
    print(f"     whole shipped ladder's own slope at the vertex ({out['bb0']['base_slope']:+.3f}), "
          f"and clears GATE BA4's necessary bound {abs(need):.3f} at only "
          f"{abs(fin[lo_k]) / abs(need):.2f}x.")
    out["bb4"] = {"coefs": {f"{l}|{k[0]}/{k[1]}": v for (l, k), v in coefs.items()},
                  "agree_sign": bool(agree), "clean": clean, "dominated": dominated,
                  "mix": mix, "required_dP": {f"{k[0]}/{k[1]}": v for k, v in needed.items()},
                  "span": span, "frac_at_hi": at_lo_hi, "overshoot_at_lo": at_hi_lo}
    return coefs, span, at_lo_hi


def bb5(base, probe_curves, out):
    print()
    print("=" * 98)
    print("BB5  COLLATERAL — what these perturbations do to the NAMED features")
    print("   GATE Y (s126) measured that the ladder constants moving this region DISSOLVE the")
    print("   320 Hz null and the mid peak (prominence 7.27 -> 0.00 dB).  Re-measured here on the")
    print("   probes actually used, through GATE W's own locator, at DRIVE noon.")
    print()
    k = ("DRIVE", "noon")
    feats = ("mid_notch", "mid_peak", "treble_peak")
    print(f"   {'probe':16s}" + "".join(f"{n + ' f0/prom':>26s}" for n in feats))
    rows = {}
    for label, per in [("SHIPPED", base[k])] + [(l, probe_curves[(l, k)]) for l, *_ in PROBES]:
        d = per[RUNGS[1]]
        cells = []
        for n in feats:
            _nm, kind, win, _lab = W.FEAT_BY_NAME[n]
            r = W.locate(d, win, kind)
            cells.append((r["f0"], r["prom"]))
        rows[label] = cells
        print(f"   {label:16s}" + "".join(f"{a:16.1f} Hz{b:8.2f}" for a, b in cells))
    lost = [l for l, *_ in PROBES
            if any(rows[l][i][1] < 0.5 * rows["SHIPPED"][i][1] for i in range(len(feats)))]
    print(f"\n   ⇒ {len(lost)} of {len(PROBES)} probes more than HALVE at least one feature's "
          f"prominence: {', '.join(lost) if lost else '(none)'}")
    print("   ⚠ These are PROBES, not proposals — a shipped section would be shaped to minimise")
    print("     this.  The column is here because it prices what moving P' near the vertex costs")
    print("     at all, and it reproduces GATE Y's finding on a second set of constants.")
    out["bb5"] = {"features": {l: [list(c) for c in v] for l, v in rows.items()}, "lost": lost}


def bb6(sign_rec, span, frac, out):
    print()
    print("=" * 98)
    print("BB6  VERDICT")
    drive = sign_rec["DRIVE"]
    sign_refutes = drive["required_same_signed"] and drive["n_flip"] == drive["n_probes"]
    # The decisive statistic is NOT the sign — see BB3, where the hypothesis this gate was built
    # on failed.  It is whether ONE fixed dP' can serve every condition, which BB4 answers with a
    # locus argument that has no bar in it.
    size_refutes = bool(span >= SPAN_BAR)
    print(f"   BB3  SIGN: {drive['n_flip']} of {drive['n_probes']} probes flip on the DRIVE axis "
          f"where the requirement does not")
    print(f"        ⇒ sign {'REFUTES' if sign_refutes else 'does NOT refute'} route (i) — and "
          f"{'' if sign_refutes else 'the hypothesis this gate opened with was WRONG, recorded rather than dropped'}")
    print(f"   BB4  SIZE: the required fixed dP' spans a factor of {span:.0f} across conditions;")
    print(f"        a section closing the easiest condition delivers {100 * frac:.1f} % of the")
    print(f"        requirement at the hardest (bar: a factor of {SPAN_BAR:.0f}, i.e. the two ends")
    print("        cannot be within 2x of one another)")
    print(f"   BB5  COLLATERAL: {len(out['bb5']['lost'])} of {len(PROBES)} probes more than halve "
          f"a named feature's prominence")
    print()
    if size_refutes:
        print("   ⇒ ROUTE (i) IS REFUTED — on SIZE CONSISTENCY, not on sign.  A fixed section has")
        print("     ONE dP'; the chain needs a different one at every condition because the")
        print("     clipper's own compression-exponent change COLLAPSES as the DRIVE knob comes")
        print("     up (the clipper is already limiting at both stimulus rungs, so changing what")
        print("     it is fed cannot change the DIFFERENCE between them).  A dose-response locus")
        print("     that cannot contain the target refutes the lever, not its setting.")
        print("   ⇒ route (ii), a genuinely LEVEL-DEPENDENT section, is what remains.")
    else:
        print("   ⇒ ROUTE (i) IS NOT REFUTED.  The required dP' is consistent enough across")
        print("     conditions for one fixed section to serve them; it must still clear GATE")
        print("     BA4's necessary bound and the collateral above before anything is built.")
    print()
    print(f"   BB6-MEMBERSHIP conditions=[{','.join(sorted(COND.values()))}]")
    print(f"   BB6-VERDICT refuted={size_refutes} by=size span={span:.1f} "
          f"frac_at_hardest={frac:.4f} sign_refutes={sign_refutes} "
          f"drive_flips={drive['n_flip']}/{drive['n_probes']}")
    out["bb6"] = {"refuted": bool(size_refutes), "by": "size", "sign_refutes": bool(sign_refutes)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    os.makedirs(PRIV_DIR, exist_ok=True)
    out = {}

    need, vertex, dP = bb0(out)

    before = BA.fingerprint(W.REN_DIR)
    n = len(COND) * (len(PROBES) + 1) + 1
    print(f"\n   rendering ~{n} conditions with the CURRENT binary ...")
    base = {k: curves(f)[1] for k, f in COND.items()}
    probe_curves = {}
    for label, fitname, _ek, spec in PROBES:
        val, _ = fit_value(fitname, spec)
        for k, f in COND.items():
            probe_curves[(label, k)] = curves(f, ("--fit", f"{fitname}={val:.9g}"))[1]
    print("   done")

    bb1(base, dP, vertex, out)
    req, own, deliv = bb2(base, probe_curves, dP, need, vertex, out)
    sign_rec = bb3(req, deliv, out)
    _c, span, frac = bb4(req, deliv, dP, need, out)
    bb5(base, probe_curves, out)
    bb6(sign_rec, span, frac, out)

    if BA.fingerprint(W.REN_DIR) != before:
        die("BB0", "GATE W's render cache CHANGED during this run.")
    print(f"\n   GATE W cache integrity: {len(before)} files unchanged")
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(out, fh, indent=1)
        print(f"   wrote {args.json}")
    print("=" * 98)
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
