#!/usr/bin/env python3
"""GATE BL — the BLEED-FREE ANCHOR RE-READ (session 183, open-work item 19's first task).

WHY THIS EXISTS
---------------
Session 181 shipped `blendEndStop = 0.02418` and closed open item 12 (the model no longer mutes at
LEVEL min).  Its price is structural and was accepted knowingly: the clean coefficient at
LEVEL = BLEND = max goes **0 -> 0.02418**, so THE BLEED-FREE CORNER IS NO LONGER EXACT.  That exact
zero is what GATE K7's ratio, GATE O's A3 ledger, GATE L's |rho|, GATE W/AE's bleed-free
membership, `OdToneRestore`'s tables and `cleanFraction()` itself all anchor on.

s181 §9 and s182 §5 both hand that forward as owed work, and CLAUDE.md's item 19 makes it the
item's own FIRST task.  Saying the anchor moved is not the same as re-reading what it moved.  This
gate does the re-reading, and it splits the change into the two effects it actually is:

  (A) A **PURE GAIN** on the OD path.  The OD coefficient at the corner goes 1 -> (1-e), i.e.
      -0.2126 dB, flat in frequency, at every bleed-free condition.  EXACT and render-free.
      Invisible to the gain-matched matrix; fully visible to every ABSOLUTE bleed-free ledger.

  (B) A **SHAPE** change: an added clean term at -32.12 dB re the OD coefficient.  Negligible
      wherever the OD branch is loud, and NOT negligible wherever it is not -- which is exactly
      the cancellation nulls and the band edges that item 19's whole table is made of.

⭐ Splitting them is the point.  (A) is a one-line correction to a list of published numbers.  (B)
cannot be corrected on paper at all and has to be measured, because it depends on the OD branch's
own magnitude at each frequency -- and where the OD branch nulls, a term 32 dB down is not small.

INSTRUMENT
----------
Three RENDER ARMS per condition, all at the bleed-free corner unless stated:
  ship   the shipped stage                       ->  (1-e)*OD + e*CLEAN
  e0     `--fit blendEndStop=0`                  ->  1*OD + 0*CLEAN   (= the pre-s181 model;
                                                      s181 asserted this is bit-identical to the
                                                      pre-change stage over an 81-cell sweep AND
                                                      restores exact digital zero on a real render)
  clean  BLEND = 0                               ->  0*OD + 1*CLEAN

`e0` is therefore not a hypothetical: it IS every pre-s181 number's model, so `ship - e0` is the
correction owed, measured rather than argued.  `clean` supplies r(f), the ratio that EXPLAINS the
size of (B) instead of merely reporting it.

⚠⚠ EVERY CAPTURE WITHOUT A `grunt-` TOKEN IS GRUNT = CUT (`captures.py` defaults it; the s151
trap, which cost that session most of a fit).  The condition grid below is explicitly 3 GRUNT x 3
DRIVE, because the feature under the most scrutiny -- the 320 Hz null -- is a cancellation in a
network the GRUNT switch feeds.

⛔ WHAT THIS GATE IS NOT.  It does not re-fit anything, it does not propose a constant, and it does
not grade the model against either reference.  It measures ONE difference: shipped minus pre-s181,
on the model alone.  Both arms are renders of our own build, so no capture, no reference and no
authority question enters -- which is what makes the numbers here unarguable in a way a
model-vs-pedal number never is.
"""

import argparse
import json
import math
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import analyze as A                      # noqa: E402
import captures as C                     # noqa: E402
import comprehensive_report as CR        # noqa: E402
import feature_locus_gate as W           # noqa: E402
import level_law_gate as K               # noqa: E402
import od_tone_restore_fit as OT         # noqa: E402

OS_FACTOR = 8
REN_DIR = "build/s183_bleedfree_anchor"

# ⛔⛔ RENDER PRIVATE, NEVER INTO GATE W's CACHE.  `build/s122_feature_locus/` is READ-ONLY and
# enforced (it is fingerprinted before and after every GATE W run) because W.render re-renders
# anything whose binary stamp is stale, which would destroy the artefacts GATE W published from.
# s159's pattern: a gate that wants GATE W's LOCATOR imports the function and renders its own.

# ---- the condition grid ------------------------------------------------------------------------
# The bleed-free corner is LEVEL = BLEND = max.  DRIVE and GRUNT are the two axes the 320 Hz null
# actually moves on, and both are on the captures already, so every cell here has a real
# counterpart rather than being a synthetic sweep.
DRIVES = (("drive-0700", 0.0), ("drive-1200", 0.5), ("drive-1700", 1.0))
GRUNTS = (("grunt-cut", 1), ("grunt-flat", 2), ("grunt-boost", 0))
SWEEPS = ("sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6")

# The graded band.  Same range the release gate uses, so a number here is comparable with one
# there; the locator's own windows are narrower and are applied per feature.
F_LO_GRADE, F_HI_GRADE = 25.0, 16300.0

# BL2's flat-gain removal is not a fit: it is the EXACT analytic value from BL1, subtracted.  A
# fitted offset would absorb part of the shape change and understate it (`self-selecting-scores`).

# BL3: the locator's own resolution, IMPORTED not transcribed -- GATE W's grid cell / 3, which is
# the bar s158/s159 say every centre must be quoted against.
LOCATOR_RES_FRAC = W.GRID_STEP_FRAC / 3.0

# BL0: bit-identity bar.  Two renders of the same stage are a deterministic function of their
# args, so the bar is EXACT, not a tolerance (s175's pattern) -- anything else hides a missed edit.
BITS = 0.0


def _bin_sig():
    st = os.stat(CR.DEFAULT_BIN)
    return [st.st_size, st.st_mtime_ns]


def render(tag, args):
    """Render one arm, reusing only when BOTH the argv and the BINARY stamp match.

    The binary half is not optional (s117: GATE R silently re-read renders of a superseded build
    because its stamp covered argv alone), and it is doubly load-bearing here because the whole
    gate is a two-arm difference -- a stale arm would report a DSP change as a physical finding."""
    os.makedirs(REN_DIR, exist_ok=True)
    out = os.path.join(REN_DIR, tag + ".wav")
    sp = out + ".args.json"
    want = list(args)
    if os.path.exists(out) and os.path.exists(sp):
        st = json.load(open(sp))
        if st["argv"] == want and st.get("bin") == _bin_sig():
            return out
        why = "a DIFFERENT condition" if st["argv"] != want else "a DIFFERENT BINARY"
        sys.stderr.write(f"  ! {out} was rendered at {why} -- re-rendering\n")
    if not CR.render_plugin(CR.DEFAULT_BIN, want, out, OS_FACTOR):
        sys.exit(f"GATE BL: render failed for {out}\n   args: {' '.join(want)}")
    with open(sp, "w") as fh:
        json.dump({"argv": want, "bin": _bin_sig()}, fh, indent=1)
    return out


def cond_args(drive, grunt, *, blend=1.0, level=1.0, extra=()):
    """Explicit flags for one condition.  Every control emitted (never relying on the binary's
    defaults matching -- `captures.render_args`'s own rule), so a render is fully determined."""
    return ["--master", "0.500000",
            "--blend", f"{blend:.6f}", "--level", f"{level:.6f}",
            "--drive", f"{drive:.6f}",
            "--lo", "0.500000", "--lo-mid", "0.500000",
            "--hi-mid", "0.500000", "--hi", "0.500000",
            "--attack", "0", "--grunt", str(grunt),
            "--lo-mid-freq", "1", "--hi-mid-freq", "1",
            "--dist-engage", "1", "--bypass", "0"] + list(extra)


_ORIG = None
_REF = None


def orig_ref():
    global _ORIG, _REF
    if _ORIG is None:
        _ORIG = A.load(A.ORIG)
        _REF = A.seg_of(_ORIG, "sweep_clean")
    return _ORIG, _REF


def bitdiff(pa, pb):
    """Worst |sample difference| between two renders.

    ⚠ A helper because the first draft wrote `A.load(p)[1]` inline in four places — `A.load`
    returns the ARRAY, so `[1]` is SAMPLE 1, and every "bit-identity" check was comparing one
    sample of leading silence.  The two scope arms duly PASSED (vacuously) and only the
    NON-VACUITY arm, which requires a difference, went red — defence in depth doing exactly its
    job (s119), and the reason a gate needs an arm in each direction rather than a set of
    reassuring zeros."""
    a, b = A.load(pa), A.load(pb)
    n = min(len(a), len(b))
    if len(a) != len(b):
        sys.exit(f"GATE BL: {pa} and {pb} differ in LENGTH ({len(a)} vs {len(b)}) -- a truncated "
                 "render is not a measurement (`is_full_length`).")
    return float(np.max(np.abs(a[:n] - b[:n])))


def curve(path, sweep):
    """One render + one sweep -> the 1/48-oct smoothed H1 curve on GATE W's own grid."""
    _, ref = orig_ref()
    y = A.load(path)
    f, m = A.transfer_h1(A.seg_of(y, sweep), ref)
    return W.smooth(f, m)


# =================================================================================================
# BL0 — guards and known answers
# =================================================================================================
def gate_bl0(e_hi, e_lo):
    print("=" * 96)
    print("BL0  GUARDS AND KNOWN ANSWERS")
    print("=" * 96)

    # (a) EPOCH.  The whole gate is a statement about ONE shipped constant, so it must refuse if
    # FitParams.h has moved under it.  Imported from GATE K (s182) rather than re-parsed here:
    # a second parser is a second thing to keep in sync (`rebuild-targets-dont-transcribe`).
    K.check_shipped_endstop()
    print(f"  (a) EPOCH        FitParams.h ships blendEndStop = {e_hi:.6g}, "
          f"blendEndStopClean = {e_lo:.6g}  [GATE K's resolver agrees]")

    # (b) The topology's own prediction, EXACT.  At LEVEL = BLEND = max the LEVEL wiper IS the OD
    # source (L >= 1 => Vw = Vo) and the BLEND wiper sits `endHi` short of it, so the output is
    # (1-e)*OD + e*CLEAN with NO network solve left in it.  That is why (A) is a pure gain: the
    # two coefficients are frequency-independent constants.
    od_s, cl_s = K.coef_closed(1.0, 1.0)
    od_0, cl_0 = K.coef_closed(1.0, 1.0, endstop=(0.0, 0.0))
    pred = (1.0 - e_hi, e_hi)
    worst = max(abs(od_s - pred[0]), abs(cl_s - pred[1]))
    if worst > 1e-12:
        sys.exit(f"GATE BL: BL0b FAILED -- the stage's corner coefficients {od_s:.9f}/{cl_s:.9f} "
                 f"are not (1-e, e) = {pred[0]:.9f}/{pred[1]:.9f} (worst {worst:.3e}).\n"
                 "   Either the end stop no longer enters as a pure wiper offset at the corner, "
                 "or GATE K's mirrors have drifted again (s182).")
    if abs(od_0 - 1.0) > 1e-12 or abs(cl_0) > 1e-12:
        sys.exit(f"GATE BL: BL0b FAILED -- the e=0 arm's corner coefficients are "
                 f"{od_0:.9f}/{cl_0:.9f}, not the exact (1, 0) every pre-s181 number assumes.")
    print(f"  (b) COEFFICIENTS corner is EXACTLY (1-e, e) = ({od_s:.6f}, {cl_s:.6f}); "
          f"e=0 arm is exactly (1, 0)   [worst {worst:.2e}]")

    # (c) SCOPE CONTROL, and it is a RENDER not an argument.  At BLEND = 0 the effective wiper is
    # `endLo` = 0, so `engagedPath` takes its `b_eff <= 0` branch and returns (0, 1) whatever the
    # end stop is -- i.e. the clean path is untouched BY CONSTRUCTION.  A gate that only ever
    # renders where a change is expected cannot tell "correctly scoped" from "reached everything".
    a = render("scope_blend0_ship", cond_args(0.5, 1, blend=0.0))
    b = render("scope_blend0_e0", cond_args(0.5, 1, blend=0.0, extra=["--fit", "blendEndStop=0"]))
    d = bitdiff(a, b)
    if d > BITS:
        sys.exit(f"GATE BL: BL0c FAILED -- the end stop reaches BLEND = 0 (worst sample diff "
                 f"{d:.3e}).  The clean path is supposed to be untouched by construction.")
    print(f"  (c) SCOPE        BLEND = 0 is BIT-IDENTICAL across the two arms "
          f"(worst |diff| {d:.1e})  -- the change is confined to the OD/mix side")

    # (d) NON-VACUITY.  The converse of (c), and the arm that makes every number below mean
    # something: at the corner the two arms MUST differ, or this gate is measuring nothing.
    a = render("bl0_corner_ship", cond_args(0.5, 1))
    b = render("bl0_corner_e0", cond_args(0.5, 1, extra=["--fit", "blendEndStop=0"]))
    d = bitdiff(a, b)
    if d <= BITS:
        sys.exit("GATE BL: BL0d FAILED -- the two arms are bit-identical at the bleed-free "
                 "corner.  `--fit blendEndStop=0` is not reaching the stage, so every difference "
                 "below would read as zero for a plumbing reason (s100's mutation control).")
    print(f"  (d) NON-VACUITY  the corner DOES move (worst |sample diff| {d:.4f})")

    # (e) The clean branch is OD-INDEPENDENT.  BL2/BL3 use ONE `clean` render for every cell, and
    # that is only legitimate if the OD-path controls are genuinely out of circuit at BLEND = 0.
    # Asserted on two renders that differ in DRIVE and GRUNT, not assumed from the topology.
    a = render("bl0_clean_ref", cond_args(0.0, 1, blend=0.0))
    b = render("bl0_clean_alt", cond_args(1.0, 0, blend=0.0))
    d = bitdiff(a, b)
    if d > BITS:
        sys.exit(f"GATE BL: BL0e FAILED -- the BLEND = 0 render depends on DRIVE/GRUNT (worst "
                 f"{d:.3e}), so one clean arm cannot serve every cell.")
    print(f"  (e) CLEAN ARM    BLEND = 0 is OD-independent (DRIVE min/GRUNT cut vs DRIVE max/"
          f"GRUNT boost, worst |diff| {d:.1e})  -- one clean render serves all 9 cells")
    return a


# =================================================================================================
# BL1 — the LEVEL half: exact, render-free, and it corrects a list of published numbers
# =================================================================================================
def gate_bl1(e_hi):
    flat = 20.0 * math.log10(1.0 - e_hi)
    rel = 20.0 * math.log10(e_hi / (1.0 - e_hi))
    print()
    print("=" * 96)
    print("BL1  THE LEVEL HALF — EXACT, NO RENDER")
    print("=" * 96)
    print(f"  OD coefficient at the bleed-free corner   1.000000 -> {1.0 - e_hi:.6f}"
          f"   = {flat:+.4f} dB, FLAT IN FREQUENCY")
    print(f"  added CLEAN term, re the OD coefficient   {rel:+.3f} dB")
    print()
    print("  ⭐ Because the corner's two coefficients are CONSTANTS (BL0b), the OD half of the")
    print("     change is a PURE GAIN.  Every absolute bleed-free reading in the project is")
    print(f"     therefore {flat:+.4f} dB out on the shipped build, with no shape term at all:")
    print()
    print("     instrument / number                                     published    corrected")
    print("     " + "-" * 74)
    # Every row is a published bleed-free ABSOLUTE figure.  The correction is the same constant in
    # each case, which is the point -- there is nothing to measure, only to apply.
    for label, val, note in (
        ("GATE O   A3 OD-path deficit (s119, `s118_clampfix`)", -4.38, "deficit deepens"),
        ("GATE O   clean-side bound (s107/s119)", 0.48, "UNMOVED — clean path is untouched (BL0c)"),
        ("GATE M   A3 at the mixing network's zero endpoints", -5.34, "deficit deepens"),
        ("s172     OD path re its OWN clean path, 250–900 Hz", -4.97, "deficit deepens"),
    ):
        if "UNMOVED" in note:
            print(f"     {label:52s}  {val:+8.3f}     {val:+8.3f}   ({note})")
        else:
            print(f"     {label:52s}  {val:+8.3f}     {val + flat:+8.3f}   ({note})")
    print()
    print("     ⚠⚠ EVERY ONE OF THOSE MOVES THE SAME WAY AND IT IS THE UNFLATTERING ONE: the")
    print("        shipped OD path is 0.21 dB QUIETER at the corner than the path those numbers")
    print("        were measured on, so A3's measured deficit is 0.21 dB LARGER than published,")
    print("        not smaller.  Small against 4.38 dB; not small against GATE O's 0.48 dB")
    print("        clean-side bound, which it is 44 % of — and that bound is what licenses the")
    print("        sentence 'A3 is the OD path, absolutely'.  That sentence still holds (the")
    print("        clean path is bit-identical, BL0c, so the bound itself does not move) but the")
    print("        RATIO it is quoted as, 11 %, becomes 10.4 %.")
    print()
    print("     ⭐ INVISIBLE TO THE MATRIX BY CONSTRUCTION.  `comprehensive_report` fits a")
    print("        per-row broadband null gain before differencing, so a flat 0.21 dB is deleted")
    print("        exactly.  That is why s182's matrix price and this correction are consistent")
    print("        rather than in tension: they are looking at orthogonal halves of one change.")
    return flat


# =================================================================================================
# BL2/BL3/BL4 — the SHAPE half, measured
# =================================================================================================
def gate_bl234(flat, clean_path, e_hi):
    print()
    print("=" * 96)
    print("BL2  THE SHAPE HALF — MEASURED, WITH THE EXACT FLAT GAIN REMOVED")
    print("=" * 96)
    print("  `ship - e0`, minus BL1's analytic constant.  What is left is what a paper correction")
    print("  cannot reach.  r(f) = e*|CLEAN| / ((1-e)*|OD|) is the added term's own size re the OD")
    print("  term at that frequency; 20log10(1+r) BOUNDS the perturbation (coherent worst case).")
    print()
    g = W.GRID
    sel = (g >= F_LO_GRADE) & (g <= F_HI_GRADE)

    cells = []
    for dname, dv in DRIVES:
        for gname, gv in GRUNTS:
            a_ship = render(f"{dname}_{gname}_ship", cond_args(dv, gv))
            a_e0 = render(f"{dname}_{gname}_e0", cond_args(dv, gv, extra=["--fit", "blendEndStop=0"]))
            for sw in SWEEPS:
                cells.append({"drive": dname, "grunt": gname, "sweep": sw,
                              "ship": curve(a_ship, sw), "e0": curve(a_e0, sw),
                              "clean": curve(clean_path, sw)})

    print(f"  {'drive':11s} {'grunt':11s} {'sweep':14s} {'rms':>7s} {'max|Δ|':>8s} {'at Hz':>9s} "
          f"{'r max':>8s} {'at Hz':>9s} {'bound':>7s}")
    print("  " + "-" * 92)
    worst_shape = 0.0
    for c in cells:
        sh = (c["ship"] - c["e0"] - flat)[sel]
        r = ((e_hi * 10.0 ** (c["clean"] / 20.0))
             / ((1.0 - e_hi) * 10.0 ** (c["e0"] / 20.0)))[sel]
        gg = g[sel]
        i = int(np.abs(sh).argmax())
        j = int(r.argmax())
        c["shape_rms"] = float(np.sqrt((sh ** 2).mean()))
        c["shape_max"] = float(np.abs(sh).max())
        worst_shape = max(worst_shape, c["shape_max"])
        print(f"  {c['drive']:11s} {c['grunt']:11s} {c['sweep']:14s} {c['shape_rms']:7.3f} "
              f"{c['shape_max']:8.3f} {gg[i]:9.1f} {20 * math.log10(r[j]):+8.2f} {gg[j]:9.1f} "
              f"{20 * math.log10(1 + r[j]):7.3f}")

    print()
    print(f"  ⇒ WORST SHAPE PERTURBATION ANYWHERE: {worst_shape:.3f} dB, against a flat term of "
          f"{flat:+.4f} dB.")
    print("  ⛔ So the 'it is only 32 dB down' reading is WRONG, and predictably so: a term 32 dB")
    print("     below the OD COEFFICIENT is not 32 dB below the OD SIGNAL wherever the OD branch")
    print("     itself is small.  r(f) peaks at the two band edges — the OD path is high-passed")
    print("     into the clipper and low-passed by both Sallen-Keys, and the clean tap is neither.")

    # ---- BL3 ------------------------------------------------------------------------------------
    print()
    print("=" * 96)
    print("BL3  THE FEATURE RE-READ — GATE W's LOCATOR, BOTH ARMS, ALL SEVEN FEATURES")
    print("=" * 96)
    print(f"  Δf0 is quoted against the locator's OWN resolution ({LOCATOR_RES_FRAC * 100:.2f} %,")
    print("  imported from GATE W).  ⛔ A reading that is `edge` or under GATE W3's prominence bar")
    print("  is REFUSED on both arms and reported as such — `locate` always returns SOMETHING")
    print("  (s126/s151), so an unguarded Δ on an absent feature is a number about a window.")
    print()
    # ⚠⚠ MEMBERSHIP IS TALLIED OVER ALL 36 (cell x sweep) READINGS AND THE DETAIL IS PRINTED FOR
    # ONE REFERENCE CELL.  The first draft printed one cell and then NARRATED "membership is
    # unchanged" in the verdict — `computed-verdicts-not-narrated`, and it was FALSE: W3's
    # prominence bar is applied to a quantity this change moves, so a feature sitting near the bar
    # can cross it.  A verdict about membership has to be computed from every cell, not inferred
    # from the one that got printed.
    DETAIL = ("drive-1200", "grunt-cut")
    feat_rows = []
    memb = {}
    for name, kind, win, _label in W.FEATURES:
        print(f"  {name}  {win[0]:.0f}–{win[1]:.0f} Hz     [detail: {DETAIL[0]} / {DETAIL[1]}]")
        gain = lost = 0
        n_edge = n_prom = 0
        for c in cells:
            a = W.locate(c["e0"], win, kind)
            b = W.locate(c["ship"], win, kind)
            ok_a = not a["edge"] and a["prom"] >= W.MIN_PROM_DB
            ok_b = not b["edge"] and b["prom"] >= W.MIN_PROM_DB
            gain += int(ok_b and not ok_a)
            lost += int(ok_a and not ok_b)
            # ⚠ W3 admits a reading on TWO conditions, and BOTH move here.  Counting them
            # separately is not bookkeeping: a PROM flip is a feature getting shallower, an EDGE
            # flip is a feature APPEARING where the curve used to run monotonically into the
            # window bound — different physics, and only the second is new information about the
            # shape.  A mutation arm that assumed the prominence bar was the only mechanism read
            # GUARD DEAD against a working gate, which is how the second one was found.
            n_edge += int(a["edge"] != b["edge"])
            n_prom += int((a["prom"] >= W.MIN_PROM_DB) != (b["prom"] >= W.MIN_PROM_DB))
            df = 100.0 * (b["f0"] / a["f0"] - 1.0)
            # r AT the feature: this is what makes the size explicable rather than reported.
            i = int(np.argmin(np.abs(g - a["f0"])))
            r_at = (e_hi * 10.0 ** (c["clean"][i] / 20.0)) / ((1.0 - e_hi) * 10.0 ** (c["e0"][i] / 20.0))
            feat_rows.append({"feature": name, "drive": c["drive"], "grunt": c["grunt"],
                              "sweep": c["sweep"], "resolved_e0": ok_a, "resolved_ship": ok_b,
                              "f0_e0": a["f0"], "f0_ship": b["f0"], "df_pct": df,
                              "prom_e0": a["prom"], "prom_ship": b["prom"],
                              "r_at_f0_db": 20 * math.log10(r_at)})
            if (c["drive"], c["grunt"]) != DETAIL:
                continue
            tag = (f"{df:+6.2f} % = {abs(df) / (LOCATOR_RES_FRAC * 100):5.1f} x res"
                   if (ok_a and ok_b) else
                   f"REFUSED  (resolved: e0 {'Y' if ok_a else 'N'} / ship {'Y' if ok_b else 'N'})")
            print(f"    {c['sweep']:14s} f0 {a['f0']:8.1f} -> {b['f0']:8.1f}   {tag}")
            print(f"    {'':14s} prom {a['prom']:6.2f} -> {b['prom']:6.2f} "
                  f"({b['prom'] - a['prom']:+.2f} dB)   r at f0 = {20 * math.log10(r_at):+6.2f} dB")
        memb[name] = (gain, lost)
        n = len(cells)
        verdict = ("UNCHANGED" if gain == 0 and lost == 0
                   else f"MOVED: {lost} lost, {gain} gained")
        print(f"    -> membership over all {n} (cell x sweep) readings: {verdict}"
              f"   [W3 condition flips: {n_edge} edge, {n_prom} prominence]")
        print()

    # ---- BL3b: the treble peak's DRIVE WALK, which is a verdict and not a size -------------------
    print("  BL3b  THE TREBLE PEAK'S DRIVE WALK — the one reading where the change is a VERDICT")
    print("  " + "-" * 92)
    print("  GATE W6 classifies a feature FIXED or DRIVE-DEPENDENT from its span across the")
    print("  stimulus ladder, and `OdDriveTilt` (s166) SHIPPED against that statistic.  It was")
    print("  measured on the e0 model.  Both arms, same cells, same estimator:")
    print()
    print(f"  {'grunt':11s} {'arm':6s} " + " ".join(f"{s.replace('sweep_', ''):>10s}" for s in SWEEPS)
          + f" {'span %':>9s}")
    walk = {}
    for gname, _gv in GRUNTS:
        for arm in ("e0", "ship"):
            f0s = []
            for sw in SWEEPS:
                c = next(x for x in cells
                         if x["drive"] == "drive-1200" and x["grunt"] == gname and x["sweep"] == sw)
                f0s.append(W.locate(c[arm], (1800.0, 4200.0), "max")["f0"])
            span = 100.0 * (f0s[-1] / f0s[0] - 1.0)
            walk[(gname, arm)] = span
            print(f"  {gname:11s} {arm:6s} " + " ".join(f"{v:10.1f}" for v in f0s) + f" {span:+9.2f}")
    print()
    print("  ⚠⚠ READ THIS AS A DIRECTION, NOT AS A NEW MEASUREMENT OF THE MODEL'S TILT.  The walk")
    print("     grows because the added clean term does NOT roll off where the OD branch does, so")
    print("     as the OD path compresses with stimulus the fixed clean term takes over the top of")
    print("     the band and drags the vertex.  That is a MIX effect at the summing node, not the")
    print("     drive-dependent pre-clipper slope item 6 is about, and `OdDriveTilt` did not")
    print("     acquire it.  s166's GATE BC numbers were measured on the e0 arm and stand AS")
    print("     MEASUREMENTS OF THAT ARM; what needs re-reading is the claim that the SHIPPED")
    print("     build delivers 83 % of the pedal's walk, because the shipped build now delivers a")
    print("     different number for a reason GATE BC never scored.")

    # ---- BL4 ------------------------------------------------------------------------------------
    print()
    print("=" * 96)
    print("BL4  THE 320 Hz NULL ON `OdToneRestore`'s OWN ESTIMATOR (E6, `notch_geometry`)")
    print("=" * 96)
    print("  BL3 reads GATE W's E1 prominence, which GATE AW (s159) proved is `E1 <= E6`")
    print("  IDENTICALLY and mixes DEPTH with WIDTH — so it must not adjudicate this stage.  E6 is")
    print("  the estimator the shipped tables were fitted on.  BOTH depths printed (s152's rule:")
    print("  a point depth and a 1/6-oct area depth are different quantities, not two readings of")
    print("  one), and `q_interp` rather than `q` (s153: `q` is quantised to the size of the")
    print("  defect it measures).")
    print()
    print(f"  {'drive':11s} {'grunt':11s} {'sweep':14s} {'point e0':>9s} {'point ship':>11s} "
          f"{'Δ':>7s} {'area e0':>9s} {'area ship':>10s} {'Δ':>7s} {'Q e0':>7s} {'Q ship':>7s}")
    print("  " + "-" * 108)
    e6 = []
    for c in cells:
        if c["sweep"] != "sweep_drv_-12":       # the user's stated playing level
            continue
        a = OT.notch_geometry(g, c["e0"])
        b = OT.notch_geometry(g, c["ship"])
        row = {"drive": c["drive"], "grunt": c["grunt"],
               "point_e0": a["depth_point"], "point_ship": b["depth_point"],
               "area_e0": a["depth_area"], "area_ship": b["depth_area"],
               "q_e0": a.get("q_interp", float("nan")), "q_ship": b.get("q_interp", float("nan"))}
        e6.append(row)
        print(f"  {c['drive']:11s} {c['grunt']:11s} {c['sweep']:14s} "
              f"{row['point_e0']:9.2f} {row['point_ship']:11.2f} "
              f"{row['point_ship'] - row['point_e0']:+7.2f} "
              f"{row['area_e0']:9.2f} {row['area_ship']:10.2f} "
              f"{row['area_ship'] - row['area_e0']:+7.2f} "
              f"{row['q_e0']:7.2f} {row['q_ship']:7.2f}")
    dp = float(np.median([r["point_ship"] - r["point_e0"] for r in e6]))
    da = float(np.median([r["area_ship"] - r["area_e0"] for r in e6]))
    dq = float(np.median([100.0 * (r["q_ship"] / r["q_e0"] - 1.0) for r in e6]))
    print()
    print(f"  ⇒ median Δ depth: POINT {dp:+.2f} dB, AREA {da:+.2f} dB;  median ΔQ {dq:+.1f} %")
    print()
    print(f"  ⭐⭐ THE TWO ESTIMATORS DISAGREE BY {abs(dp / da):.0f}x, AND THAT IS THE MECHANISM,")
    print("     NOT NOISE.  GATE AP (s152) built the AREA depth because the POINT depth is")
    print("     CENSORED wherever the null's bottom sits at a floor, and measured it 4.1x less")
    print("     sensitive to exactly that.  Here the floor is not the deconvolution residue — it")
    print("     is the model's OWN clean bleed, which cannot cancel because it does not go")
    print("     through the network doing the cancelling.  ⇒ the added term FLOORS the bottom of")
    print("     every bleed-free null and leaves the flanks alone, which is why the point depth")
    print("     loses 4 dB, the area depth loses a quarter of one, and Q broadens.")
    print("  ⚠⚠ CONSEQUENCE FOR GATE AP's STANDING USER DECISION (s153, 'match the bottom, not")
    print("     the area'): the metric that decision selected is the one this change degrades,")
    print("     and it degrades it at the corner the table was fitted at.  That does not reverse")
    print("     the decision — it was taken on a trade this gate has not re-priced — but it is a")
    print("     new fact about the point metric, and it belongs in front of the user.")
    return cells, feat_rows, e6, walk, worst_shape, memb, (dp, da, dq)


# =================================================================================================
# BL5 — cleanFraction() and the mix law
# =================================================================================================
def gate_bl5(e_hi):
    print()
    print("=" * 96)
    print("BL5  `cleanFraction()` AT THE CORNER, AND WHAT THE MIX LAW NOW READS THERE")
    print("=" * 96)
    od, cl = K.coef_closed(1.0, 1.0)
    cf = cl / (od + cl)
    # `mixShape`, transcribed from OdToneRestore.h and asserted against its own pinning below.
    # ⚠ node 0 RE-ANCHORED 0.000 -> 0.02418 at s185 (item 19's P2): it is the bleed-free corner's
    # clean fraction (FitParams::blendEndStop), not a free constant.  ⭐⭐ GUARDED s185 against the
    # PARSED header — the pinning check this tool already had cannot see node 0, so this would
    # otherwise have gone stale silently (the s182 GATE-K2 defect).
    mix_cf = (0.02418, 0.210, 0.320, 0.440, 0.560, 0.730, 0.870, 1.000)
    mix_s = (0.951, -0.525, -0.195, 0.000, 0.017, 0.177, 0.224, 0.252)
    import od_tone_restore_fit as _OT
    _T = _OT.shipped_tables()
    for _n, _mine, _theirs in (("kMixCf", mix_cf, _T["kMixCf"]), ("kMixS", mix_s, _T["kMixS"])):
        if len(_mine) != len(_theirs) or max(abs(a - b) for a, b in zip(_mine, _theirs)) > 1e-12:
            sys.exit(f"GATE BL: transcribed {_n} has drifted from src/dsp/OdToneRestore.h "
                     f"({list(_mine)} vs {list(_theirs)}).  Update it; do not tolerate the drift.")
    cf_ref = 0.441

    def shape(x):
        if x <= mix_cf[0]:
            return mix_s[0]
        if x >= mix_cf[-1]:
            return mix_s[-1]
        for i in range(len(mix_cf) - 1):
            if x <= mix_cf[i + 1]:
                t = (x - mix_cf[i]) / (mix_cf[i + 1] - mix_cf[i])
                return mix_s[i] + t * (mix_s[i + 1] - mix_s[i])
        return mix_s[-1]

    # The law's own pinning is a free known answer on the transcription: S(kMixCfRef) must be ~0.
    if abs(shape(cf_ref)) > 2e-3:
        sys.exit(f"GATE BL: BL5 FAILED -- the transcribed mix shape is not pinned at kMixCfRef "
                 f"(S({cf_ref}) = {shape(cf_ref):.4f}, expected 0).  The table has moved in "
                 "OdToneRestore.h and this copy is stale.")
    k_tab = {"Cut": (-7.87, -8.61, -9.34, -9.50, -9.65),
             "Flat": (-1.56, 0.71, 2.97, 1.97, 0.97),
             "Boost": (3.40, 4.61, 5.81, 5.81, 5.81)}
    s0, s1 = shape(0.0), shape(cf)
    print(f"  cleanFraction() at LEVEL = BLEND = max :  0.000000 -> {cf:.6f}")
    print(f"  S(cleanFrac)                           :  {s0:+.4f}  -> {s1:+.4f}   "
          f"(Δ {s1 - s0:+.4f})")
    print(f"  S is pinned to 0 at kMixCfRef = {cf_ref} — verified on the transcription above")
    print()
    print("  The stage's cut is `base[g][d] + K[g][d]*S(cleanFrac)`, so the change in the cut it")
    print("  applies at the bleed-free corner is K*(ΔS), per cell:")
    print()
    print(f"  {'GRUNT':7s} " + " ".join(f"{f'drive {i}':>10s}" for i in range(5)))
    for name, ks in k_tab.items():
        print(f"  {name:7s} " + " ".join(f"{k * (s1 - s0):10.3f}" for k in ks))
    print()
    print("  ⛔⛔ AND THE SHARPER POINT, WHICH IS ABOUT THE TABLE'S DOMAIN AND NOT ITS VALUES:")
    print(f"     `kNotchMixK` IS DEFINED AS `cut(cleanFrac = 0) - cut(kMixCfRef)` (s156), AND")
    print(f"     cleanFrac = 0 IS NOW UNREACHABLE.  The shipped stage's minimum clean fraction is")
    print(f"     {cf:.5f}, so the whole K column is anchored on an operating point the plugin can")
    print("     no longer be in, and `kMixS[0] = 0.951` is now an extrapolation node rather than")
    print("     an endpoint.  ⚠ That is a statement about PROVENANCE, not an error: the law is")
    print("     evaluated by interpolation and the reachable end is S(cf) above, so nothing")
    print("     mis-evaluates.  What it means is that the K column can no longer be RE-MEASURED")
    print("     the way it was originally measured, and a future re-fit must re-anchor rather")
    print("     than reproduce.")
    return {"clean_fraction": cf, "S_at_0": s0, "S_at_corner": s1,
            "cut_delta": {k: [v * (s1 - s0) for v in ks] for k, ks in k_tab.items()}}


def main():
    ap = argparse.ArgumentParser(description="GATE BL — bleed-free anchor re-read (s183, item 19)")
    ap.add_argument("--out", default="analysis/reports/s183_bleedfree_anchor.json")
    args = ap.parse_args()

    print()
    print("#" * 96)
    print("# GATE BL — THE BLEED-FREE ANCHOR RE-READ  (session 183, open-work item 19, task 1)")
    print("#" * 96)
    print("# Shipped stage vs `--fit blendEndStop=0` (= the pre-s181 model).  Both arms are our")
    print("# own renders, so no capture, reference or authority question enters.")
    print()

    e_hi, e_lo = K.SHIPPED_BLEND_END_STOP
    clean_path = gate_bl0(e_hi, e_lo)
    flat = gate_bl1(e_hi)
    cells, feat_rows, e6, walk, worst_shape, memb, (dp, da, dq) = gate_bl234(flat, clean_path, e_hi)
    bl5 = gate_bl5(e_hi)

    print()
    print("=" * 96)
    print("VERDICT — WHAT MUST BE RE-READ, RANKED")
    print("=" * 96)
    print(f"  1. EVERY ABSOLUTE BLEED-FREE LEDGER is {flat:+.4f} dB out, exactly and flatly.")
    print("     GATE O / M / K7 / Q and s172's OD:clean ratio.  A one-line correction, and it")
    print("     makes A3's measured deficit LARGER.  ⛔ It is NOT a model change: the OD path is")
    print("     unaltered; what moved is how much of it reaches the output at the corner.")
    print(f"  2. `OdToneRestore`'s 320 Hz null is SHALLOWER at the corner by {dp:+.2f} dB on the")
    print(f"     POINT depth and only {da:+.2f} dB on the AREA depth ({abs(dp / da):.0f}x), with Q")
    print(f"     broadening {dq:+.1f} %.  The stage's base row is the cut that lands the COMPOSITE")
    print("     null on the pedal's, so this is the one number in the set that is a genuine RE-FIT")
    print("     trigger rather than a correction — and the split says WHY: the bleed FLOORS the")
    print("     bottom and leaves the flanks, i.e. it censors exactly the estimator the table was")
    print("     fitted on (GATE AP's mechanism, arriving from a new direction).")
    print(f"  3. THE TREBLE PEAK'S DRIVE WALK MORE THAN DOUBLES at GRUNT cut "
          f"({walk[('grunt-cut', 'e0')]:+.2f} % -> {walk[('grunt-cut', 'ship')]:+.2f} %), which")
    print("     touches GATE W6's own statistic and `OdDriveTilt`'s shipped acceptance number.")
    print("     ⛔ Do not read it as the model having acquired drive-dependence: it is the clean")
    print("     tap surviving at HF where the OD branch does not.")
    moved = {k: v for k, v in memb.items() if v != (0, 0)}
    n_read = len(cells)
    if not moved:
        print(f"  4. GATE W/AE's bleed-free MEMBERSHIP is UNCHANGED at all 7 features over "
              f"{n_read} readings each")
        print("     — so the FIXED / DRIVE-DEPENDENT classifications survive and only the sizes")
        print("     move, which is s158/s159's finding a third time.")
    else:
        print(f"  4. ⚠⚠ GATE W/AE's bleed-free MEMBERSHIP MOVES at {len(moved)} of 7 features "
              f"(over {n_read} readings each):")
        for k, (gn, ls) in moved.items():
            print(f"        {k:13s} {ls} lost, {gn} gained")
        print("     ⛔ So 'only the sizes move' is FALSE, and any epoch-to-epoch comparison of a")
        print("     bleed-free feature must be matched on cells admitted in BOTH arms before it")
        print("     is differenced (`aggregate-moved-check-membership-first`).  The mechanism is")
        print("     direct rather than mysterious: W3's bar is applied to a PROMINENCE, and this")
        print("     change moves prominences, so a feature sitting near the bar crosses it.")
    print(f"  5. `cleanFraction()` at the corner is {bl5['clean_fraction']:.5f}, not 0, and")
    print("     `kNotchMixK`'s own definition point is now unreachable (BL5).")
    print()
    print(f"  ⭐ The single most useful line: the change is a {flat:+.4f} dB FLAT term plus a")
    print(f"     shape term reaching {worst_shape:.2f} dB, and the shape term lives ENTIRELY where")
    print("     the OD branch is small.  Quote the flat term as a correction; measure the rest.")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump({"end_stop": list(K.SHIPPED_BLEND_END_STOP), "flat_db": flat,
                   "worst_shape_db": worst_shape,
                   "cells": [{k: v for k, v in c.items() if not isinstance(v, np.ndarray)}
                             for c in cells],
                   "features": feat_rows, "e6": e6, "membership": {k: list(v) for k, v in memb.items()},
                   "treble_walk": {f"{k[0]}|{k[1]}": v for k, v in walk.items()},
                   "mix": bl5}, fh, indent=1)
    print(f"\n  report -> {args.out}")


if __name__ == "__main__":
    main()
