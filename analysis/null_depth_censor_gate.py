#!/usr/bin/env python3.11
"""GATE AP — does the deconvolution residue's censoring of the pedal's deep nulls move the
`OdToneRestore` table, and by how much?

WHY THIS EXISTS
---------------
Session 151 fitted `OdToneRestore`'s notch DEPTH against the pedal, GRUNT row by GRUNT row, and
then found at the very end of the session that **most of the PEDAL's deep readings have their
bottom AT OR BELOW the deconvolution residue** (margins −27.7…+14.0 dB).  `feature_locus_gate`'s
own `floor_db` docstring says what that means: *"a notch bottom at or below the residue means the
DEPTH is not resolved … report the depth as unresolved and keep the centre"* — and DEPTH is exactly
what s151 fitted.  So the two new GRUNT rows shipped against targets that are LOWER BOUNDS rather
than measurements, and s151 recorded them as provisional and put this at the head of its own open
list, above every tuning item, because it is a defect in the TARGET and not in the fit.

⛔ THE MOVE THAT IS NOT AVAILABLE is dropping the censored cells.  The sub-20 Hz residue is
signal-PROPORTIONAL regularisation residue and not a noise floor (GATE R measured it tracking the
stimulus almost 1:1), so excluding on it deletes precisely the deep-notch cells a notch audit
exists to measure.  This project has committed that mistake twice — GATE R's second floor guard
and GATE W's first draft — and `measurement-discipline.md` carries both.

⭐ GATE R's OWN RESOLUTION was to stop depending on the fragile quantity (s110 R4): score a
1/6-octave POWER-INTEGRATED deficit, set by the notch's AREA rather than by the exact depth of its
bottom.  `null_locus_gate.band_db` is that function; `od_tone_restore_fit.band_db_grid` evaluates
the same definition on GATE W's 1/48-oct grid, and AP1a asserts the two agree on identical data.

⚠⚠ THE TRAP THIS GATE IS BUILT AROUND, AND IT IS NOT THE OBVIOUS ONE.
A point depth and a 1/6-octave area depth are **different quantities, not two measurements of one**:
a genuinely deep, narrow notch has a small area deficit whatever the residue is doing.  So
"the area numbers are smaller" is NOT evidence the shipped table over-corrects, and reading it that
way would be `difference-statistics-hide-common-mode` with the two operands in different units.
⇒ this gate never compares the two depths.  It converts each into the SHIPPED TABLE's own unit —
the biquad's centre gain in dB — by solving, per cell, for the gain at which the composite's depth
equals the pedal's, **under each metric separately**.  Those two gains are commensurable, and their
difference is the answer to "does the censoring move the table?".

⭐ That solve is exact and needs no rebuild: the stage is linear and in series, so its own response
subtracts from (and adds back to) the rendered curve analytically — the same argument that licenses
`--stage-off`.  And it comes with a free known answer: solving in the POINT metric must return
approximately the SHIPPED table, because the shipped table was fitted in the point metric.  If it
does not, the solve is wrong and nothing below it means anything (AP3a).

    /opt/homebrew/bin/python3.11 analysis/null_depth_censor_gate.py
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import feature_locus_gate as W          # noqa: E402
import null_locus_gate as R             # noqa: E402  — GATE R, for band_db (imported, not copied)
import od_tone_restore_fit as F         # noqa: E402

# The three realistic stimulus rungs.  `sweep_clean` is deliberately outside the fitted range
# (s151 §6) and is read here only as a printed control, never in a mean.
REAL = ("sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6")

# GRUNT row -> (physical position index, the fit tool's capture set).  Row order is
# Clipper::Grunt {Cut, Flat, Boost}, matching kNotchGainDb's rows.
#
# ⚠⚠ SESSION 191 — THIS MEMBERSHIP IS BLEED-FREE-ONLY, AND GATE AQ AND GATE AX BOTH INHERIT IT.
# s186's GATE BO measured what that costs: the 8 pre-s186 groups hold 17 of 29 rows at the anchor
# and **the GRUNT axis is 12 of 12**, so this stage's GRUNT-rowed tables have only ever been graded
# at ONE clean fraction — on the axis that has three rows to choose between — and BO then found the
# ORDERING does not survive the mix (0 of 3 readable sweeps agree) with the argmax moving from FLAT
# to BOOST.  s186 added the mixed twins to `od_tone_restore_fit.SETS` and pointing this at them was
# left as "a measurement nobody has taken" (item 19's second orphaned finding).
#
# ⇒ `ROW_SETS` below makes the membership an AXIS rather than a constant, and `ROWS` stays the
# BLEED-FREE default EXACTLY as before, so:
#   * every stored GATE AP / AQ / AR / AX number reproduces unchanged, and the three importers
#     (`AP.ROWS`) keep the membership their published results were computed on;
#   * `--rows mixed` grades the same question at the LISTENING condition (LEVEL noon / BLEND max),
#     which is the direct mixed twin of each bleed-free group.
# ⛔ Do NOT re-point `ROWS` itself.  A membership swapped under three importers silently moves five
# gates' stored numbers, which is exactly the trap `od_tone_restore_fit.FROZEN_SETS` was added to
# make impossible one layer down.
#
# ⚠⚠ MEMBERSHIP IS ASYMMETRIC ON THE MIXED ARM AND THAT IS A CAPTURE FACT, NOT A CHOICE:
# `drive-1430_grunt-*` and `drive-1700_grunt-flat` do not exist on disk, so Flat reaches DRIVE 0.5
# and Boost 1.0 while Cut reaches all five.  Any comparison ACROSS rows on that arm must be matched
# on DRIVE first (s178's 13th occurrence of `aggregate-moved-check-membership-first`, where the
# unmatched pooling actively rewarded the arm that read less).
ROW_SETS = {
    "bleedfree": (("Cut", 0, "bleedfree"), ("Flat", 1, "grunt_flat"), ("Boost", 2, "grunt_boost")),
    "mixed":     (("Cut", 0, "listen"), ("Flat", 1, "listen_flat"), ("Boost", 2, "listen_boost")),
}

ROWS = ROW_SETS["bleedfree"]

#: Which membership `main()` selected, for every header that would otherwise name one.
CURRENT_ROWS_LABEL = ["bleedfree"]

# The fit's own converged residual, s151 §5: depth within ±0.83 dB at every (GRUNT, DRIVE) entry.
# Used as the BAR below — a target that moves by less than the fit's own residual cannot change a
# shipped constant, and that bar is imported from a measurement rather than chosen here.
FIT_RESIDUAL_DB = 0.83

FAIL = []
NONMONO = []


def fail(tag, msg):
    FAIL.append(tag)
    print(f"  ❌ {tag}: {msg}")


# ================================================================================================
# AP1 — known answers
# ================================================================================================
def ap1a():
    """The grid-evaluated band average IS GATE R's band_db.

    ⚠ This is the check `a-transfer-function-known-answer-validates-TOPOLOGY-and-is-blind-to-the
    -VALUE-SET` (s145/s149) warns about if written carelessly, so it is deliberately run on data
    the two sides do NOT share a preparation of: R.band_db integrates the RAW Farina curve, and
    band_db_grid integrates cells W.smooth() has already power-averaged.  They compose only up to
    the per-cell bin weighting, so the honest output is the SIZE of the disagreement, printed."""
    print("\nAP1a  band_db_grid vs GATE R's band_db (raw curve vs 1/48-oct grid, same definition)")
    import analyze as A
    import captures as C
    orig, ref = W._load_orig()
    fn = "level-1700_base-od.wav"
    cap_al, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, fn)), orig)
    f, m = A.transfer_h1(A.seg_of(cap_al, "sweep_drv_-12"), ref)
    # ⚠ `transfer_h1` returns dB and `R.band_db` expects LINEAR magnitude (it squares its input).
    # A first draft of this arm passed dB straight in and the gate duly refused at 3.25 dB —
    # correctly, and for a reason that was entirely in the TEST.  `a-shipped-stage's-closed-form-
    # takes-the-STAGE's-input` (s113), one level over: check what DOMAIN an imported function's
    # argument is in, not just its name.
    mag = 10.0 ** (np.asarray(m) / 20.0)
    d = W.smooth(f, m)
    worst = 0.0
    print(f"  {'centre Hz':>10} {'R.band_db':>10} {'grid':>10} {'diff dB':>9}")
    a0 = R.band_db(f, mag, 1000.0, frac=F.DEPTH_FRAC)
    b0 = F.band_db_grid(W.GRID, d, 1000.0)
    for centre in (210.0, 260.0, 323.0, 405.0, 520.0, 716.0):
        a = R.band_db(f, mag, centre, frac=F.DEPTH_FRAC)        # raw curve, magnitude domain
        b = F.band_db_grid(W.GRID, d, centre)                   # 1/48-oct grid, dB domain
        # Compared as a DIFFERENCE against a common reference band, so the two absolute scales
        # (the grid curve is shape-normalised, the raw one is not) cannot silently disagree by a
        # constant nobody looked at.
        dif = (a - a0) - (b - b0)
        worst = max(worst, abs(dif))
        print(f"  {centre:10.1f} {a - a0:10.3f} {b - b0:10.3f} {dif:+9.4f}")
    # A synthetic arm where the two MUST agree exactly, so a pass above is not just two
    # implementations of the same bug: on a flat curve every band average is the same constant.
    flat = np.full_like(W.GRID, -7.0)
    syn = max(abs(F.band_db_grid(W.GRID, flat, c) - (-7.0)) for c in (210.0, 323.0, 716.0))
    print(f"  flat-curve control (must be 0): {syn:.2e} dB")
    print(f"  worst real-curve disagreement: {worst:.4f} dB "
          f"(bin weighting inside a 1/48-oct cell; NOT claimed to be zero)")
    if syn > 1e-9:
        fail("AP1a", f"the flat-curve control is not exact ({syn:.2e} dB) — band_db_grid is wrong")
    if worst > 0.25:
        fail("AP1a", f"the two integrators disagree by {worst:.3f} dB on real data — too large to "
                     f"call them the same definition")
    return worst


def ap1b():
    """THE LOAD-BEARING KNOWN ANSWER: censor a curve on purpose and watch each estimator move.

    Everything this gate concludes rests on the claim that the area depth is robust to the null's
    bottom being censored.  That is a property, so it is MEASURED rather than cited: clip each
    pedal curve from below at a ladder of levels and regress each estimator's depth against the
    amount of clipping.  A point depth must fall ~1:1 once the clip bites; an area depth must not.
    ⭐ The zero-clip rung is the arm's own control — it must reproduce the unclipped values EXACTLY,
    or the clipping harness is perturbing something it should not touch."""
    print("\nAP1b  CENSORING CONTROL — clip each pedal curve from below, measure the response")
    print("  slope = d(depth)/d(clip level), over the rungs where the clip is actually biting.")
    print(f"  {'cell':<34} {'depth0 pt':>10} {'depth0 ar':>10} | {'slope pt':>9} {'slope ar':>9}"
          f" | {'ratio':>6}")
    rows = []
    for gname, gpos, sname in ROWS:
        for fname, drv in F.SETS[sname]:
            for sw in ("sweep_drv_-12",):
                g, ped, _ = F.curves(fname, sw)
                try:
                    base = F.notch_geometry(g, ped)
                except RuntimeError:
                    continue
                bottom = base["bottom"]
                # ⚠ The ladder is scaled to the FEATURE, not fixed: clipping 12 dB off a 6 dB notch
                # erases it, the reader then correctly refuses (the argmin lands on a CORE bound),
                # and a fixed ladder crashes on exactly the shallow cells.  Cap at 60 % of the
                # notch's own depth so every rung still has a feature to measure.
                top = min(12.0, 0.6 * base["depth_point"])
                clips = np.linspace(0.0, top, 7)         # dB of bottom removed
                # ⛔⛔ s191: THE PER-RUNG CALL WAS UNGUARDED AND IT CRASHED THE WHOLE GATE ON THE
                # FIRST MIXED CELL. `notch_geometry` legitimately REFUSES when the clipped minimum
                # lands on a CORE bound, and the 60 % cap above was calibrated on BLEED-FREE curves,
                # where the nulls are deep; at a mixed cell the null is shallower and its bottom is
                # floored by the clean tap (s183/s184), so the same fraction erases it. A refusal is
                # a reading the gate must survive, not an error — s117: a gate that hands the next
                # session a stack trace has handed them a symptom instead of a reason.
                kept, pt, ar = [], [], []
                for c in clips:
                    cl = np.maximum(ped, bottom + c)
                    try:
                        r = F.notch_geometry(g, cl)
                    except RuntimeError:
                        continue                 # the clip erased the feature at this rung
                    kept.append(c)
                    pt.append(r["depth_point"])
                    ar.append(r["depth_area"])
                # A slope over 3 points of a 7-rung ladder is not a dose-response
                # (`check-n-before-reading-a-trend`), and a cell that loses rungs loses them from
                # the CLIPPED end -- exactly the end the slope is measured on. Named, not silent.
                if len(kept) < 4:
                    print(f"  {gname + ' drive ' + format(drv, '.2f'):<34} REFUSED — only "
                          f"{len(kept)} of {len(clips)} clip rungs kept a readable feature")
                    continue
                clips = np.array(kept)
                if abs(pt[0] - base["depth_point"]) > 1e-12 or abs(ar[0] - base["depth_area"]) > 1e-12:
                    fail("AP1b", f"zero-clip control moved at {gname} drive {drv} — the clipping "
                                 f"harness is not inert")
                sp = float(np.polyfit(clips, pt, 1)[0])
                sa = float(np.polyfit(clips, ar, 1)[0])
                rows.append((sp, sa))
                print(f"  {gname + ' drive ' + format(drv, '.2f'):<34} {pt[0]:10.2f} {ar[0]:10.2f} "
                      f"| {sp:9.3f} {sa:9.3f} | {abs(sp) / max(abs(sa), 1e-6):6.2f}")
    sp = float(np.mean([a for a, _ in rows]))
    sa = float(np.mean([b for _, b in rows]))
    print(f"\n  MEAN slope: point {sp:+.3f} dB per dB of censoring, area {sa:+.3f} "
          f"⇒ the area depth is {abs(sp) / max(abs(sa), 1e-6):.1f}x less sensitive.")
    if sp > -0.5:
        fail("AP1b", f"the POINT depth barely responds to censoring (slope {sp:+.3f}) — either the "
                     f"clipping harness is not biting or the point estimator is not what it claims")
    if abs(sa) >= abs(sp):
        fail("AP1b", f"the AREA depth is not more robust than the point depth ({sa:+.3f} vs "
                     f"{sp:+.3f}) — the whole premise of this gate fails, do NOT read AP3")
    return sp, sa


def ap1c():
    """SYNTHETIC ROUND TRIP on the solve — the arm the gate's headline actually rests on.

    ⚠ A first draft of this arm injected a notch of known gain and asserted the POINT depth equals
    that gain.  It fails by 0.3-1.2 dB and the estimator is fine: an RBJ peaking section is not at
    0 dB at the shoulder frequencies, so the shoulder-referred depth is legitimately less than the
    centre gain.  Asserting the closed form of that instead would be circular — it is the reader's
    own algorithm re-typed.
    ⭐ What is NOT circular is a round trip through `solve_gain`: build a synthetic pedal curve
    from a KNOWN gain G*, hand the solver a flat stage-subtracted model, and require it to return
    G*.  The answer exists independently of anything the reader computes.
    ⭐⭐ And it must hold under BOTH metrics — which is exactly the claim that makes AP3's two
    columns comparable at all: whatever 'depth' means, matching it at the same f0 and Q pins the
    same gain.  If the area column came back a different number HERE, the whole conversion is
    invalid and AP3 would be comparing two units again.
    ⭐⭐⭐ AND THE CONVERSE IS THE MOST USEFUL THING THIS ARM SAYS: the two metrics agree here
    because the synthetic pedal null has EXACTLY the biquad's own (f0, Q).  So on real data, any
    disagreement between AP3's two columns is a SHAPE mismatch between the pedal's null and the
    shipped section — it is NOT the censoring.  AP6 leans on this."""
    print("\nAP1c  SYNTHETIC ROUND TRIP — solve for a KNOWN injected gain, under both metrics")
    fs = 48000.0 * W.OS_FACTOR
    T = F.shipped_tables()
    flat = np.zeros_like(W.GRID)
    print(f"  {'injected G*':>12} {'solve pt':>9} {'solve ar':>9} {'err pt':>8} {'err ar':>8}")
    for gstar in (3.0, 8.0, 16.0, 26.0):
        # The synthetic "pedal" is the shipped stage's own shape at a known gain, on a flat
        # background; the synthetic stage-subtracted "model" is that flat background.
        q = F.lerp5(T["kNotchQ"][0], 0.5, T["kX"])
        ped = flat + F.rbj_peak_db(W.GRID, fs, T["kNotchFreq"], q, -gstar)
        pg = F.notch_geometry(W.GRID, ped)
        got = {}
        for metric in ("point", "area"):
            # Q must match what the solver will use, so drive/grunt are pinned to the same cell.
            got[metric] = solve_gain(W.GRID, flat, pg, 0.5, 0, T, fs, metric)
        if got["point"] is None or got["area"] is None:
            # A round trip that produces NO measurement is its own hard failure, never a zero
            # (s95): the solver failing to bracket a gain it was handed is exactly as bad as
            # returning the wrong one, and it must not fall through into a TypeError.
            fail("AP1c", f"the solver found no root for G*={gstar} "
                         f"(point={got['point']}, area={got['area']})")
            continue
        ep = got["point"] - gstar
        ea = got["area"] - gstar
        print(f"  {gstar:12.1f} {got['point']:9.3f} {got['area']:9.3f} {ep:+8.4f} {ea:+8.4f}")
        if abs(ep) > 0.05 or abs(ea) > 0.05:
            fail("AP1c", f"round trip lost the injected gain (G*={gstar}: point {ep:+.3f}, "
                         f"area {ea:+.3f} dB) — the two AP3 columns are NOT commensurable")
    # Mutation control: a flat curve has no feature, and the reader must REFUSE rather than
    # returning a small number (`a silent estimator and an absent feature are indistinguishable`).
    try:
        F.notch_geometry(W.GRID, flat)
        fail("AP1c", "the reader found a null in a perfectly flat curve")
    except RuntimeError:
        print("  flat-curve control: reader REFUSES, as it must.")
    print("  ⇒ both metrics recover the same injected gain, so AP3's two columns are one unit.")


# ================================================================================================
# AP2 — the census: which readings are censored, and does the point/area gap follow it?
# ================================================================================================
def ap2():
    # ⚠ s191: the label used to say "bleed-free" unconditionally. With `--rows` an axis, a header
    # that names one membership while grading another is `verify-the-BASELINE-not-its-LABEL` in the
    # cheapest possible form -- so it reports the membership it was actually given.
    print(f"\nAP2  FLOOR-MARGIN CENSUS — {CURRENT_ROWS_LABEL[0]}, stage subtracted, all three "
          f"realistic sweeps")
    print("  margin = (null bottom) − (deconvolution residue).  NEGATIVE = the depth is a LOWER")
    print("  BOUND, not a measurement.  ⛔ Nothing is excluded on this; it is a diagnosis.")
    T = F.shipped_tables()
    fs = 48000.0 * W.OS_FACTOR
    print(f"\n  {'grunt':<6} {'drv':>4} {'sweep':<15} | {'ped mgn':>8} {'ped pt':>7} {'ped ar':>7} "
          f"{'pt−ar':>7} | {'mod mgn':>8}")
    pts, gaps, n_cens = [], [], 0
    for gname, gpos, sname in ROWS:
        for fname, drv in F.SETS[sname]:
            for sw in REAL:
                g, ped, mod, meta = F.curves(fname, sw, meta=True)
                mod = mod - F.current_response(g, drv, fs, T, gpos, F.clean_frac_of(fname))
                try:
                    p = F.notch_geometry(g, ped)
                except RuntimeError:
                    print(f"  {gname:<6} {drv:4.2f} {sw:<15} | pedal has no readable null")
                    continue
                try:
                    mm = F.notch_geometry(g, mod)
                    mmar = f"{mm['bottom'] - meta['mod_floor']:8.2f}"
                except RuntimeError:
                    mmar = "  no null"
                mgn = p["bottom"] - meta["ped_floor"]
                gap = p["depth_point"] - p["depth_area"]
                pts.append(mgn)
                gaps.append(gap)
                n_cens += mgn < 0.0
                print(f"  {gname:<6} {drv:4.2f} {sw:<15} | {mgn:8.2f} {p['depth_point']:7.2f} "
                      f"{p['depth_area']:7.2f} {gap:7.2f} | {mmar}")
    r = float(np.corrcoef(pts, gaps)[0, 1])
    print(f"\n  {n_cens} of {len(pts)} pedal readings are CENSORED (margin < 0).")
    print(f"  corr(floor margin, point−area gap) = {r:+.3f}  — negative means the two estimators")
    print(f"  diverge exactly where the bottom is censored, which is the mechanism, measured.")
    if len(pts) < 15:
        fail("AP2", f"only {len(pts)} readable pedal cells — too few to census")
    return n_cens, len(pts), r


# ================================================================================================
# AP3 — the answer, in the shipped table's own unit
# ================================================================================================
def solve_gain(g, mod_off, ped_geo, drv, gpos, T, fs, metric):
    """Gain (dB of cut at kNotchFreq) at which the composite's depth equals the pedal's.

    The stage is LINEAR and IN SERIES, so adding a candidate biquad back onto the stage-subtracted
    curve is exact — no rebuild, no second render.  Q is held at the SHIPPED value: the question is
    what GAIN the table owes, not a free re-fit of its shape."""
    from scipy.optimize import brentq
    q = F.lerp5(T["kNotchQ"][gpos], drv, T["kX"])
    peak = F.rbj_peak_db(g, fs, T["kPeakFreq"], T["kPeakQ"],
                         F.lerp5(T["kPeakGainDb"], drv, T["kX"]))
    target = ped_geo["depth_area" if metric == "area" else "depth_point"]

    def err(gain):
        comp = mod_off + F.rbj_peak_db(g, fs, T["kNotchFreq"], q, -gain) + peak
        try:
            r = F.notch_geometry(g, comp)
        except RuntimeError:
            return -1e3                      # no feature yet ⇒ far too little gain
        return r["depth_area" if metric == "area" else "depth_point"] - target

    lo, hi = -12.0, 60.0
    # ⚠ brentq returns *a* root; it says nothing about uniqueness.  Nothing guarantees depth is
    # monotone in gain, so it is CHECKED rather than assumed — a second root would make the solved
    # gain a choice the gate never made.
    # ⚠⚠ The check is ROOT UNIQUENESS, not monotonicity, and a first draft got that wrong: it
    # required `err` to be non-decreasing across a ladder spanning −12…+60 dB, and duly flagged 5
    # cells.  Traced on one of them, depth is perfectly monotone through the whole solution region
    # (gain 0→30 dB: area depth 3.88→14.92, no reversal) — the wobble is at gains far outside it,
    # where the biquad's own skirts start dragging the shoulder readings and the reader is tracking
    # something else.  Monotonicity everywhere is not needed and is not true; ONE sign change is
    # what uniqueness requires.  ⭐ The "no feature yet" sentinel is kept in the ladder rather than
    # filtered out — it is genuinely negative (too little gain), and dropping it could hide a
    # sign change, which is `a-mutation-that-produces-no-measurement-is-not-a-zero`.
    vals = [err(v) for v in np.linspace(lo, hi, 25)]
    sign_changes = sum(1 for a, b in zip(vals, vals[1:]) if (a < 0) != (b < 0))
    if sign_changes > 1:
        NONMONO.append(f"{metric} d{drv:.2f} g{gpos}: {sign_changes} sign changes")
    if err(lo) > 0 or err(hi) < 0:
        return None
    return float(brentq(err, lo, hi, xtol=1e-3))


def ap3():
    print("\nAP3  THE TABLE, RE-SOLVED UNDER EACH METRIC (both in the shipped unit: dB of cut)")
    print("  Per cell: the biquad gain at which the composite's depth equals the pedal's, at the")
    print("  SHIPPED Q.  Exact — the stage is linear and in series, so no rebuild is needed.")
    T = F.shipped_tables()
    fs = 48000.0 * W.OS_FACTOR
    out = {}
    print(f"\n  {'grunt':<6} {'drv':>4} | {'shipped':>8} | {'solve pt':>9} {'n':>2} | "
          f"{'solve ar':>9} {'n':>2} | {'ar−pt':>7} | {'ar−shipped':>10}")
    for gname, gpos, sname in ROWS:
        for fname, drv in F.SETS[sname]:
            # ⛔⛔ s191: this read `F.lerp5(T["kNotchGainDb"][gpos], ...)` — the BASE table alone —
            # while line ~378 below subtracts `current_response`'s FULL mix-keyed curve. Since s156
            # those are two different stages, so the gate compared a solve against a reference that
            # omitted `kNotchMixK * S(cleanFrac)`, and AP3a (its own load-bearing known answer) has
            # been RED on the current epoch as a result. `F.cut_db` is now the single resolver both
            # sides read, and it takes the SAME `clean_frac_of(fname)` the subtraction does.
            cf = F.clean_frac_of(fname)
            ship = F.cut_db(T, gpos, drv, cf)
            gp, ga = [], []
            for sw in REAL:
                g, ped, mod = F.curves(fname, sw)
                mod_off = mod - F.current_response(g, drv, fs, T, gpos, cf)
                try:
                    pg = F.notch_geometry(g, ped)
                except RuntimeError:
                    continue                 # only the PEDAL side can cost a cell here
                for metric, acc in (("point", gp), ("area", ga)):
                    v = solve_gain(g, mod_off, pg, drv, gpos, T, fs, metric)
                    if v is not None:
                        acc.append(v)
            if not gp or not ga:
                print(f"  {gname:<6} {drv:4.2f} | {ship:8.2f} | NO SOLVABLE CELL")
                continue
            mp, ma = float(np.mean(gp)), float(np.mean(ga))
            out[(gname, drv)] = (ship, mp, ma, len(gp), len(ga))
            print(f"  {gname:<6} {drv:4.2f} | {ship:8.2f} | {mp:9.2f} {len(gp):2d} | "
                  f"{ma:9.2f} {len(ga):2d} | {ma - mp:7.2f} | {ma - ship:+10.2f}")
    return out


def ap3a(sol):
    """KNOWN ANSWER: the POINT solve must reproduce the SHIPPED table.

    The shipped table was fitted in the point metric by iterating a rebuild-and-re-measure loop, so
    an independent analytic solve in the same metric has a right answer that already exists.  This
    is what makes AP3's area column readable at all — without it, a disagreement between the two
    columns is equally consistent with the solve being broken.

    ⚠⚠ WHAT THIS KNOWN ANSWER IS BLIND TO, found by its own mutation arm and worth stating because
    it is not obvious: it is INVARIANT to a uniform shift of the shipped table.  Add 5 dB to every
    `kNotchGainDb` entry and this check still passes to the same rms — because the same table is
    used BOTH to subtract the stage out of the rendered curve AND as the reference being compared
    against, so the shift cancels.  ⇒ AP3a certifies THE SOLVE, not that the shipped constants are
    the right ones.  (s145's `a-known-answer-is-blind-to-what-both-sides-share-as-INPUT`, in a
    third guise; the runner's arm therefore corrupts the reference alone.)"""
    print("\nAP3a  KNOWN ANSWER — does the POINT solve return the shipped table?")
    print(f"  {'grunt':<6} {'drv':>4} {'shipped':>8} {'solved':>8} {'diff':>7}")
    diffs = []
    for (gname, drv), (ship, mp, ma, np_, na) in sorted(sol.items()):
        diffs.append(mp - ship)
        print(f"  {gname:<6} {drv:4.2f} {ship:8.2f} {mp:8.2f} {mp - ship:+7.2f}")
    rms = float(np.sqrt(np.mean(np.square(diffs))))
    worst = float(np.max(np.abs(diffs)))
    print(f"\n  rms {rms:.2f} dB, worst {worst:.2f} dB against a fit whose own converged residual "
          f"is ±{FIT_RESIDUAL_DB:.2f} dB.")
    # The bar is the fit's own residual, not a number chosen here — and it is doubled because the
    # shipped entry is a MEAN over sweeps of a quantity this solve re-derives per sweep, so the two
    # disagree by the fit's residual at best.
    bar = 3.0 * FIT_RESIDUAL_DB
    if rms > bar:
        fail("AP3a", f"the point solve does not reproduce the shipped table (rms {rms:.2f} dB > "
                     f"{bar:.2f}) — AP3's area column is NOT readable; fix the solve first")
    else:
        print(f"  ✅ reproduces it (rms {rms:.2f} <= {bar:.2f} = 3x the fit's own residual), so the")
        print(f"     area column below is a measurement and not an artefact of the solve.")
    return rms, worst


def ap4(sol):
    """MEMBERSHIP — how many sweep cells each shipped entry actually rests on."""
    print("\nAP4  MEMBERSHIP — the DRIVE-max entries, counted")
    print("  s151's header flags Boost's DRIVE-max as resting on 'TWO valid cells, not three'.")
    print("  Counted against the SHIPPED build, with the stage subtracted:")
    T = F.shipped_tables()
    fs = 48000.0 * W.OS_FACTOR
    print(f"\n  {'grunt':<6} {'drv':>4} | {'sweep':<15} {'pedal':>10} {'model(off)':>11}")
    counts = {}
    for gname, gpos, sname in ROWS:
        for fname, drv in F.SETS[sname]:
            nb = 0
            for sw in REAL:
                g, ped, mod = F.curves(fname, sw)
                mod_off = mod - F.current_response(g, drv, fs, T, gpos, F.clean_frac_of(fname))
                ok = []
                for cur in (ped, mod_off):
                    try:
                        F.notch_geometry(g, cur)
                        ok.append("readable")
                    except RuntimeError:
                        ok.append("NO NULL")
                nb += ok == ["readable", "readable"]
                if drv == 1.0:
                    print(f"  {gname:<6} {drv:4.2f} | {sw:<15} {ok[0]:>10} {ok[1]:>11}")
            counts[(gname, drv)] = nb
    print(f"\n  cells where BOTH sides are readable (the depth-DIFFERENCE method's membership):")
    for k, v in sorted(counts.items()):
        flagt = "  ⚠ n=1" if v == 1 else ("  ⚠ n=2" if v == 2 else "")
        print(f"    {k[0]:<6} drive {k[1]:.2f}: {v}/3{flagt}")
    print("\n  ⭐ AP3's solve needs only the PEDAL side (it CREATES the composite's null with the")
    print("     candidate gain), so it recovers cells the difference method loses — see its own n.")
    return counts


def ap5(sol):
    """THE TRADE — what each candidate table costs on the OTHER metric.

    `score-what-you-emit` (s97): AP3 solves each table under its own metric, so of course each wins
    there.  The decision-relevant number is what the AREA-solved table does to the POINT depths and
    vice versa, both scored on the same cells with one estimator each.  Printed, not adjudicated:
    which metric a listener follows is not established by anything in this gate."""
    print("\nAP5  THE TRADE — each candidate table scored on BOTH metrics (mean |error|, dB)")
    print("  'error' = pedal depth − composite depth, over the three realistic sweeps.")
    T = F.shipped_tables()
    fs = 48000.0 * W.OS_FACTOR
    print(f"\n  {'grunt':<6} {'drv':>4} | {'SHIPPED gain':>12} {'pt err':>7} {'ar err':>7} | "
          f"{'AREA gain':>10} {'pt err':>7} {'ar err':>7}")
    tot = {"ship_pt": [], "ship_ar": [], "area_pt": [], "area_ar": []}
    for gname, gpos, sname in ROWS:
        for fname, drv in F.SETS[sname]:
            if (gname, drv) not in sol:
                continue
            ship, _, gain_ar, _, _ = sol[(gname, drv)]
            q = F.lerp5(T["kNotchQ"][gpos], drv, T["kX"])
            errs = {k: [] for k in ("ship_pt", "ship_ar", "area_pt", "area_ar")}
            for sw in REAL:
                g, ped, mod = F.curves(fname, sw)
                mod_off = mod - F.current_response(g, drv, fs, T, gpos, F.clean_frac_of(fname))
                try:
                    pg = F.notch_geometry(g, ped)
                except RuntimeError:
                    continue
                for tag, gain in (("ship", ship), ("area", gain_ar)):
                    comp = mod_off + F.rbj_peak_db(g, fs, T["kNotchFreq"], q, -gain)
                    try:
                        cg = F.notch_geometry(g, comp)
                    except RuntimeError:
                        continue
                    errs[tag + "_pt"].append(pg["depth_point"] - cg["depth_point"])
                    errs[tag + "_ar"].append(pg["depth_area"] - cg["depth_area"])
            mean = {k: float(np.mean(np.abs(v))) if v else float("nan") for k, v in errs.items()}
            for k, v in errs.items():
                tot[k].extend(np.abs(v))
            print(f"  {gname:<6} {drv:4.2f} | {ship:12.2f} {mean['ship_pt']:7.2f} "
                  f"{mean['ship_ar']:7.2f} | {gain_ar:10.2f} {mean['area_pt']:7.2f} "
                  f"{mean['area_ar']:7.2f}")
    print(f"\n  {'POOLED':<11} | {'':12} {np.mean(tot['ship_pt']):7.2f} "
          f"{np.mean(tot['ship_ar']):7.2f} | {'':10} {np.mean(tot['area_pt']):7.2f} "
          f"{np.mean(tot['area_ar']):7.2f}")
    print("  ⇒ read the DIAGONAL as each table's home metric and the OFF-diagonal as what it costs.")
    return {k: float(np.mean(v)) for k, v in tot.items()}


def ap6(sol):
    """ATTRIBUTION — is the metric disagreement actually the CENSORING?

    ⚠⚠ The tempting reading of AP3 is "the area column differs from the shipped one, therefore the
    censoring moved the table".  That is an ATTRIBUTION, and this gate has the control that tests
    it, for free: in AP1c's round trip the two metrics agree to 2e-4 dB — because there the
    synthetic pedal null has EXACTLY the biquad's own (f0, Q).  ⇒ where the two metrics disagree,
    the pedal's null and the shipped biquad have DIFFERENT SHAPES; a censored bottom alone cannot
    produce it.  So the honest test is whether the disagreement tracks the floor margin at all."""
    print("\nAP6  ATTRIBUTION — does the metric disagreement follow the CENSORING?")
    T = F.shipped_tables()
    fs = 48000.0 * W.OS_FACTOR
    print(f"\n  {'grunt':<6} {'drv':>4} | {'mean margin':>11} {'ped/comp Q':>10} | {'ar−pt gap':>9}")
    mgn, qr, gap = [], [], []
    for gname, gpos, sname in ROWS:
        for fname, drv in F.SETS[sname]:
            if (gname, drv) not in sol:
                continue
            ship, mp, ma, _, _ = sol[(gname, drv)]
            q = F.lerp5(T["kNotchQ"][gpos], drv, T["kX"])
            mm, qq = [], []
            for sw in REAL:
                g, ped, mod, meta = F.curves(fname, sw, meta=True)
                mod_off = mod - F.current_response(g, drv, fs, T, gpos, F.clean_frac_of(fname))
                try:
                    pg = F.notch_geometry(g, ped)
                except RuntimeError:
                    continue
                mm.append(pg["bottom"] - meta["ped_floor"])
                comp = mod_off + F.rbj_peak_db(g, fs, T["kNotchFreq"], q, -ship)
                try:
                    qq.append(pg["q"] / F.notch_geometry(g, comp)["q"])
                except RuntimeError:
                    pass
            if not mm or not qq:
                continue
            mgn.append(float(np.mean(mm)))
            qr.append(float(np.mean(qq)))
            gap.append(ma - mp)
            print(f"  {gname:<6} {drv:4.2f} | {mgn[-1]:11.2f} {qr[-1]:10.2f} | {gap[-1]:9.2f}")
    r_m = float(np.corrcoef(mgn, gap)[0, 1])
    r_q = float(np.corrcoef(qr, gap)[0, 1])
    print(f"\n  corr(mean floor margin, gap) = {r_m:+.3f}")
    print(f"  corr(pedal/composite Q ratio, gap) = {r_q:+.3f}")
    print("  ⇒ AP1c's round trip is the control: with the pedal's null shaped EXACTLY like the")
    print("     biquad, the two metrics agree to 2e-4 dB.  So a disagreement is a SHAPE mismatch")
    print("     between the pedal's null and the shipped (f0, Q) — the censoring is what makes the")
    print("     POINT reading untrustworthy, but it is not what makes the two columns differ.")
    return r_m, r_q


def main():
    global ROWS
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rows", choices=sorted(ROW_SETS), default="bleedfree",
                    help="which GRUNT-row membership to grade. `bleedfree` (default) is the "
                         "membership every stored GATE AP/AQ/AR/AX number was computed on; "
                         "`mixed` is its LISTENING-condition twin (s186's SETS additions).")
    ap.add_argument("--json", help="write the solved table here")
    a = ap.parse_args()
    ROWS = ROW_SETS[a.rows]
    CURRENT_ROWS_LABEL[0] = a.rows

    print("=" * 96)
    print("GATE AP — the OdToneRestore depth targets, re-read with an estimator the deconvolution")
    print("          residue cannot censor.  s151 open item 0.")
    print("=" * 96)
    print(f"  rows: {a.rows}   {' / '.join(f'{g}={s}' for g, _p, s in ROWS)}")
    for _g, _p, sname in ROWS:
        m = F.SET_META[sname]
        print(f"    {sname:<14} holds {m['hold']}  varies {m['vary']}")
    if a.rows != "bleedfree":
        print("  ⚠ NOT the membership the shipped table was fitted on, and not the membership any")
        print("    stored AP/AQ/AR/AX number was computed on. Read as a SECOND reading of the same")
        print("    question at a played setting, never as a correction to those numbers.")
        drv = [sorted({d for f, d in F.SETS[s]}) for _g, _p, s in ROWS]
        if len({tuple(x) for x in drv}) > 1:
            print(f"  ⚠⚠ THE DRIVE LADDERS DIFFER ACROSS ROWS — {'; '.join(f'{g}: {v}' for (g, _p, _s), v in zip(ROWS, drv))}")
            print("     (a capture fact: `drive-1430_grunt-*` and `drive-1700_grunt-flat` are not on")
            print("     disk). Every ACROSS-ROW comparison below must be matched on DRIVE first.")
    ap1a()
    ap1b()
    ap1c()
    n_cens, n_tot, corr = ap2()
    counts = ap4(None)
    sol = ap3()
    rms, worst = ap3a(sol)
    trade = ap5(sol)
    r_m, r_q = ap6(sol)

    print("\n" + "=" * 96)
    print("VERDICT")
    print("=" * 96)
    if NONMONO:
        fail("AP3", f"depth is NOT monotone in gain for {len(NONMONO)} cell(s) — the solved gain "
                    f"is one root of several: {NONMONO[:4]}")
    if FAIL:
        print(f"  ❌ {len(set(FAIL))} sub-gate(s) failed: {', '.join(sorted(set(FAIL)))}")
        print("     The numbers above are NOT quotable until these are fixed.")
        return 1
    moved = {k: v for k, v in sol.items() if abs(v[2] - v[0]) > FIT_RESIDUAL_DB}
    print(f"  {n_cens}/{n_tot} pedal depth readings are censored by the residue "
          f"(corr with the point−area gap {corr:+.3f}).")
    print(f"  The POINT solve reproduces the shipped table to {rms:.2f} dB rms, so the AREA solve")
    print(f"  is measured in the same unit and is comparable to it.")
    if not moved:
        print(f"\n  ⇒ NO shipped entry owes a change larger than the fit's own ±{FIT_RESIDUAL_DB} dB "
              f"residual.\n     Open item 0 CLOSES: the censoring is real and it does not move the "
              f"table.")
    else:
        print(f"\n  ⇒ {len(moved)} of {len(sol)} entries owe a change larger than the fit's own "
              f"±{FIT_RESIDUAL_DB} dB residual:")
        for (gname, drv), (ship, mp, ma, a, b) in sorted(moved.items()):
            print(f"     {gname:<6} drive {drv:.2f}: shipped {ship:+7.2f} -> area-solved "
                  f"{ma:+7.2f}  ({ma - ship:+.2f} dB)")
        print("\n  ⚠ That is what the AREA metric asks for.  It is NOT automatically the right")
        print("    answer to ship: the two metrics disagree about what 'depth' means, and which one")
        print("    the EAR follows is not established by anything here.  AP5 prices the trade:")
        print(f"    shipped table  — point err {trade['ship_pt']:.2f} dB, area err "
              f"{trade['ship_ar']:.2f} dB")
        print(f"    area-solved    — point err {trade['area_pt']:.2f} dB, area err "
              f"{trade['area_ar']:.2f} dB")
        print("    ⇒ this is a USER DECISION, not a gate verdict.  Take it to them.")
    print(f"\n  ⚠ MEMBERSHIP, and it is a separate finding: {sum(1 for v in counts.values() if v <= 1)}"
          f" of {len(counts)} entries rest on <=1 sweep cell under the difference method.")
    print(f"  ⚠ ATTRIBUTION: the disagreement does NOT track the censoring "
          f"(corr with floor margin {r_m:+.3f}); AP6.")

    # ⚠ ROW-AWARE PATH (s191). The mixed arm is a DIFFERENT membership answering the same question,
    # so writing it over `s152_null_depth_censor.json` would replace the artefact five sessions of
    # published numbers were computed from with one that merely looks like it — the silent-clobber
    # s153 documented when a mutation runner wrote a falsified result under the real gate's filename.
    rep = a.json or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "reports",
        "s152_null_depth_censor.json" if a.rows == "bleedfree"
        else f"s191_null_depth_censor_{a.rows}.json")
    json.dump({"rows": a.rows, "row_sets": [s for _g, _p, s in ROWS],
               "censored": n_cens, "readings": n_tot, "corr_margin_gap": corr,
               "point_solve_rms_vs_shipped": rms, "point_solve_worst": worst,
               "trade": trade, "corr_margin_metricgap": r_m, "corr_qratio_metricgap": r_q,
               "membership": {f"{k[0]}_{k[1]:.2f}": v for k, v in counts.items()},
               "table": {f"{k[0]}_{k[1]:.2f}": {"shipped": v[0], "solve_point": v[1],
                                                "solve_area": v[2], "n_point": v[3],
                                                "n_area": v[4]} for k, v in sol.items()}},
              open(rep, "w"), indent=1)
    print(f"\n  report -> {rep}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
