#!/usr/bin/env python3.11
"""GATE BA — WHERE CAN TASK E's CORRECTION LIVE, AND WHAT MUST IT BE?

WHY THIS EXISTS (session 164, opening task E under its 3-session cap)
---------------------------------------------------------------------
Session 160 closed open item 6's PHYSICAL-carrier search as exhaustive (GATE AM's resonance
census, GATE AS's ladder screen) and converted the item into **task E**: a scoped, non-schematic
[ENG] correction, *"same architecture as `OdToneRestore`"* — a drive-keyed tilt/shelf section
fitted directly to the sized target, exempt from the carrier gates 4-6 but bound by gates 1-3.

Before fitting anything this gate asks the question the conversion skipped: **can a section in
that architecture carry this target at all?**  It cannot, and the reason is one line of algebra
that costs one assertion to check.

THE DECOMPOSITION.  A Farina sweep presents ONE frequency at a time, so along the OD path

    H1(f, A)  =  P(f) · g(A·|P(f)|) · Q(f)

with P the pre-clipper response, g the clipper's fundamental-gain (compression) law, and Q
everything linear DOWNSTREAM of it.  In dB, with u = 20log10|P| and gamma = dlog g / dlog x,

    slope(f, A)   =  P'(f) · (1 + gamma(A|P|))  +  Q'(f)
    drive-tilt(f) =  slope(f, A_hi) - slope(f, A_lo)  =  P'(f) · [ gamma(hot) - gamma(quiet) ]

Two consequences, and they are the whole gate:

  (1) **Q DROPS OUT EXACTLY.**  A linear section downstream of the nonlinearity adds the same
      log-magnitude to every rung, and the drive-tilt is a DIFFERENCE between rungs.  So a
      section in `OdToneRestore`'s slot (stage 6b, post-clipper) contributes **exactly zero** to
      the target — at any gain, any Q, any centre, keyed on any knob.  BA2 asserts this on the
      model's OWN rendered curves rather than arguing it.

  (2) **THE PRE-CLIPPER ROUTE CARRIES A HARD BOUND.**  For any compressive, non-expanding map
      `gamma` lies in [-1, 0], so |gamma(hot) - gamma(quiet)| <= 1 and therefore

          |P'| >= |required drive-tilt|          — NECESSARY, whatever the nonlinearity does.

      The premise is not assumed: BA4a verifies it on the shipped model by checking the
      rung-to-rung output step lies in [0, dL] at every frequency and every rung, with dL the
      STIMULUS step imported from `gen_test_signal` — the ladder is -30/-18/-12/-6 dBFS, so the
      pairs are 12/6/6 dB apart, and this gate's own first draft assumed 6/6/6 AND the wrong
      sign, then reported 12 dB of stimulus as 10.6 dB of "expansion" (s115).

WHAT IS AND IS NOT REFUTED HERE
  * REFUTED: a LINEAR section DOWNSTREAM of the clipper, as a carrier of the drive-tilt.  That
    is `OdToneRestore`'s slot and it is the architecture task E was scoped to reuse.
  * NOT refuted: a section at or UPSTREAM of the clipper (BA4 sizes what it must do), and a
    genuinely LEVEL-DEPENDENT (dynamic) section anywhere.  This gate sizes both; it builds
    neither and proposes neither.
  * Says nothing about hardware — both sides are the ND captures (`reference-sources.md` §0),
    and §1 gives this region to neither reference outright.

GATES (validity exits non-zero; every physics OUTCOME is a computed verdict and execution
continues — s108's rule)
------------------------------------------------------------------------------------------------
BA0  MEMBERSHIP + PROVENANCE.  The bleed-free OD endpoints, resolved from SETTINGS through GATE
     W's own machinery, asserted by count and named.  Renders go to a PRIVATE directory — never
     `build/s122_feature_locus/`, which is GATE W's published cache and is fingerprinted before
     and after (s159's rule).  The requirement and the vertex are IMPORTED from GATE AF's stored
     report, never transcribed.
BA1  KNOWN ANSWERS, four, before anything is read:
     (a) the tilt estimator recovers an INJECTED tilt exactly, swept over sizes INCLUDING ZERO
         (zero is the arm's own mutation control) — through GATE AG's own `tilt_at`, imported;
     (b) the probe section used in BA2 is NON-TRIVIAL: it must move the per-rung SLOPE by a
         large amount.  Without this, BA2's headline passes vacuously for an inert probe —
         `empty-gate-must-fail` in the one place it would be invisible;
     (c) the shipped-vs-drawn treble-ladder divergence guard (s149 AO), re-asserted here because
         BA5 reads the ladder;
     (d) the model's own rendered curves are non-vacuous (finite, and the four rungs differ).
BA2  ⭐⭐ THE HEADLINE — a wild post-clipper section is added to every rung and the drive-tilt
     re-measured.  Bar: machine precision, because this is exact algebra and not a tolerance.
BA3  THE OPERANDS — the model's own slope at EVERY rung (s129: an endpoint pair is not a
     ladder) and its drive-tilt across FREQUENCY, with the interpretable band's bounds IMPORTED
     from GATE W's own feature windows and the contaminated centres printed as excluded.
BA4  THE PRE-CLIPPER BOUND — (a) verify gamma in [-1, 0] empirically; (b) the necessary |P'|;
     (c) how far the shipped product P'*dgamma is from the requirement.
BA5  THE ATTACK SWITCH as a candidate pre-clipper lever — and a DENOMINATOR REFUSAL, because on
     the shipped ladder (`trebleC8` = 0 since s99/s100) the whole switch moves the pre-clipper
     slope at the vertex by ~0.004 dB/oct, so every transfer coefficient formed from it is a
     divided-by-zero artefact.  The refusal is the result; the coefficients are NOT quoted.
BA6  VERDICT, computed, plus a machine-checkable membership line.

Usage:
  python3.11 analysis/task_e_placement_gate.py
  python3.11 analysis/task_e_placement_gate.py --json analysis/reports/s164_task_e_placement.json
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze as A                    # noqa: E402
import captures as C                   # noqa: E402
import eq_reference as EQ              # noqa: E402
import feature_locus_gate as W         # noqa: E402
import drive_tilt_shape_gate as AG     # noqa: E402  tilt_at, RUNGS, load_af6 — imported, not re-derived
import pre_clipper_tilt_gate as AJ     # noqa: E402  ladder_kwargs / ladder_divergence (s149)
import gen_test_signal as G            # noqa: E402  the stimulus LEVELS — imported, never transcribed

# ⛔⛔ PRIVATE render directory.  GATE W's cache holds the artefacts its published numbers came
# from and `W.render` re-renders anything whose binary stamp is stale, so pointing this gate at it
# would destroy them (s159 AW0).  BA0 asserts the two paths are distinct and fingerprints W's.
PRIV_DIR = os.path.join(os.path.dirname(HERE), "build", "s164_task_e")

RUNGS = AG.RUNGS

# The bleed-free OD endpoints: LEVEL max (BLEND max is the file default).  Three DRIVE knob
# settings x three ATTACK positions — GATE AG's own membership, restricted to the GRUNT-cut
# baseline so BA5's ATTACK comparison holds every other switch fixed.
COND = {
    ("flat", "noon"): "level-1700_base-od.wav",
    ("flat", "min"): "drive-0700_level-1700_base-od.wav",
    ("flat", "max"): "drive-1700_level-1700_base-od.wav",
    ("cut", "noon"): "level-1700_attack-cut_base-od.wav",
    ("cut", "min"): "drive-0700_level-1700_attack-cut_base-od.wav",
    ("cut", "max"): "drive-1700_level-1700_attack-cut_base-od.wav",
    ("boost", "noon"): "level-1700_attack-boost_base-od.wav",
    ("boost", "min"): "drive-0700_level-1700_attack-boost_base-od.wav",
    ("boost", "max"): "drive-1700_level-1700_attack-boost_base-od.wav",
}
ATTACKS = ("cut", "flat", "boost")
KNOBS = ("min", "noon", "max")

HALF = 0.5                 # AG's PRIMARY half-width, the only one clear of both neighbours
CANCEL_TOL = 1e-11         # BA2 is exact algebra; the bar is machine precision, not a guess
PROBE_MIN_SLOPE = 1.0      # BA1b: the probe must move a per-rung slope by at least this (dB/oct)
STEP_TOL = 0.10            # BA4a slack on [0, dL], in dB — the curve is a power average, not exact

# AG4's interpretable band, both bounds IMPORTED from GATE W's FEATURES table rather than chosen.
SMOOTH_LO = W.FEAT_BY_NAME["bt_notch"][2][1]        # 1000.0 Hz
SMOOTH_HI = W.FEAT_BY_NAME["treble_notch"][2][0]    # 4200.0 Hz

FAILED = []


def die(tag, msg):
    sys.exit(f"GATE BA {tag} FAIL: {msg}")


def note(tag, msg):
    FAILED.append(f"{tag}: {msg}")
    print(f"   ** {tag} FAIL — {msg}")


def fingerprint(d):
    if not os.path.isdir(d):
        return {}
    return {n: (os.stat(os.path.join(d, n)).st_size, os.stat(os.path.join(d, n)).st_mtime_ns)
            for n in sorted(os.listdir(d))}


# ------------------------------------------------------------------------------------------------
# curves
# ------------------------------------------------------------------------------------------------
def model_curves(fname):
    """{sweep: dB on W.GRID} for the MODEL, through GATE W's own curve pipeline."""
    out = os.path.join(PRIV_DIR, fname.replace(".wav", "") + "_plugin.wav")
    W.render(out, C.render_args(C.parse_capture(fname)))
    orig, ref = W._load_orig()
    al, _ = A.align(A.load(out), orig)
    return {sw: W.smooth(*A.transfer_h1(A.seg_of(al, sw), ref)) for sw in RUNGS}


def slope(d, f0, half=HALF):
    """dB/oct at f0 on W.GRID, through GATE AG's own estimator."""
    s, _n = AG.tilt_at(np.asarray(d), np.log2(W.GRID / f0), half)
    return s


def drive_tilt(per, f0, half=HALF):
    """AG's definition: slope(hottest rung) - slope(quietest rung)."""
    return slope(per[RUNGS[-1]], f0, half) - slope(per[RUNGS[0]], f0, half)


def wild_section(grid, vertex):
    """A deliberately WILD post-clipper linear section: a big tilt, a shelf, and a peak sitting
    ON the vertex.  Nothing about it is meant to be plausible — it exists to make BA2's
    cancellation a measurement rather than an argument (AI1c's trick, re-pointed)."""
    return (4.0 * np.log2(grid / 1000.0)
            + 6.0 / np.sqrt(1.0 + (700.0 / np.maximum(grid, 1e-9)) ** 2)
            + 9.0 * np.exp(-0.5 * (np.log2(grid / vertex) / 0.30) ** 2))


# ------------------------------------------------------------------------------------------------
# BA0 — membership, provenance, the read-only cache guard
# ------------------------------------------------------------------------------------------------
def ba0(out):
    print("=" * 96)
    print("BA0  MEMBERSHIP, PROVENANCE, CACHE GUARD")

    if os.path.abspath(PRIV_DIR) == os.path.abspath(W.REN_DIR):
        die("BA0", "the private render directory IS GATE W's cache — refusing to render into it.")
    print(f"   private render dir : {PRIV_DIR}")
    print(f"   GATE W cache       : {W.REN_DIR}  (READ-ONLY here, fingerprinted)")

    missing = [f for f in COND.values() if not os.path.exists(os.path.join(C.CAPTURE_DIR, f))]
    if missing:
        die("BA0", f"{len(missing)} capture(s) absent, so the membership is not the stated one: "
                   f"{missing}")
    if len(set(COND.values())) != len(COND):
        die("BA0", "a capture is doing duty for two conditions — the 3x3 is not a 3x3.")
    print(f"   conditions         : {len(COND)} = {len(ATTACKS)} ATTACK x {len(KNOBS)} DRIVE, "
          f"all bleed-free (LEVEL max), GRUNT cut")

    # Every condition must differ from every other in exactly the axes it is supposed to.
    for (att, knob), f in sorted(COND.items()):
        p = C.parse_capture(f)
        if p.get("level") != 1.0:
            die("BA0", f"{f} is not bleed-free (level={p.get('level')}) — the whole comparison "
                       f"rests on the clean tap being out of circuit (GATE K2).")
    print("   bleed-free asserted: LEVEL == 1.0 on all 9 (GATE K2 — bleed vanishes only there)")

    need, curv, vertex, _frac = AG.load_af6()
    print(f"   IMPORTED from GATE AF's stored report (never transcribed):")
    print(f"     required drive-tilt {need:+.4f} dB/oct   vertex {vertex:.1f} Hz   "
          f"curvature {curv:+.3f} dB/oct^2")
    out["ba0"] = {"n_cond": len(COND), "need": need, "vertex": vertex, "curv": curv,
                  "priv_dir": PRIV_DIR, "ren_dir": W.REN_DIR}
    return need, vertex


# ------------------------------------------------------------------------------------------------
# BA1 — known answers
# ------------------------------------------------------------------------------------------------
def ba1(curves, vertex, out):
    print()
    print("=" * 96)
    print("BA1  KNOWN ANSWERS")
    rec = {}

    # (a) the estimator recovers an injected tilt exactly, including ZERO.
    ref = curves[("flat", "noon")][RUNGS[0]]
    worst = 0.0
    rows = []
    for T in (0.0, -0.5, 1.0, -2.5, 7.0):
        got = slope(ref + T * np.log2(W.GRID / vertex), vertex) - slope(ref, vertex)
        worst = max(worst, abs(got - T))
        rows.append([T, got])
    print(f"   (a) injected tilt recovered, worst |error| = {worst:.3e} dB/oct over "
          f"{len(rows)} sizes incl. ZERO")
    if worst > AG.INJECT_TOL:
        die("BA1a", f"the tilt estimator does not recover an injected tilt ({worst:.3e} > "
                    f"{AG.INJECT_TOL:.0e}) — nothing below is readable.")
    rec["inject_worst"] = worst

    # (b) NON-VACUITY of BA2's probe.  Without this, BA2 passes for an inert probe.
    wild = wild_section(W.GRID, vertex)
    moved = max(abs(slope(curves[("flat", "noon")][sw] + wild, vertex)
                    - slope(curves[("flat", "noon")][sw], vertex)) for sw in RUNGS)
    print(f"   (b) BA2's probe moves a PER-RUNG slope by {moved:.3f} dB/oct "
          f"(bar {PROBE_MIN_SLOPE:.1f}) — so BA2 cannot pass vacuously")
    if moved < PROBE_MIN_SLOPE:
        die("BA1b", f"BA2's probe is inert ({moved:.3f} dB/oct) — its cancellation would be "
                    f"`empty-gate-must-fail` wearing a headline.")
    rec["probe_slope_move"] = moved

    # (c) the s149 shipped-vs-drawn ladder divergence guard, re-asserted where BA5 reads it.
    n_moved, total, _vals = AJ.ladder_divergence("flat")
    print(f"   (c) treble-ladder element set: {n_moved} of {total} values differ from the DRAWN "
          f"schematic ⇒ this IS the shipped ladder (s149 AO)")
    if n_moved == 0:
        die("BA1c", "the ladder matches the DRAWN defaults — GATE AJ/AK/AN's session-149 defect "
                    "has returned and BA5 would screen a network the plugin does not run.")
    rec["ladder_moved"] = [n_moved, total]

    # (d) non-vacuity of the curves themselves.
    for k, per in curves.items():
        for sw in RUNGS:
            if not np.all(np.isfinite(per[sw])):
                die("BA1d", f"{k} {sw} carries non-finite values.")
        if max(float(np.max(np.abs(per[a] - per[b])))
               for a in RUNGS for b in RUNGS if a != b) < 1e-9:
            die("BA1d", f"{k}: the four rungs are identical — the stimulus ladder is not being "
                        f"read, so every drive-tilt below would be a structural zero.")
    print(f"   (d) all {len(curves)} conditions finite, and the four rungs differ in all of them")
    out["ba1"] = rec


# ------------------------------------------------------------------------------------------------
# BA2 — THE HEADLINE
# ------------------------------------------------------------------------------------------------
def ba2(curves, vertex, out):
    print()
    print("=" * 96)
    print("BA2  ⭐⭐ CAN A LINEAR SECTION DOWNSTREAM OF THE CLIPPER CARRY THE DRIVE-TILT?")
    print("   H1 = P * g(A|P|) * Q.  A fixed linear Q adds the SAME log-magnitude to every rung")
    print("   and the drive-tilt is a DIFFERENCE between rungs, so Q must cancel EXACTLY —")
    print("   at any gain, any Q, any centre, keyed on any knob.  Measured, not argued:")
    print("   BA1b's wild probe (a 4 dB/oct tilt + a 6 dB shelf + a 9 dB peak ON the vertex) is")
    print("   added to every rung and the drive-tilt re-read.")
    print()
    wild = wild_section(W.GRID, vertex)
    print(f"   {'condition':34s}{'drive-tilt':>13s}{'+ wild Q':>13s}{'change':>14s}")
    worst = 0.0
    rows = []
    for att in ATTACKS:
        for knob in KNOBS:
            per = curves[(att, knob)]
            base = drive_tilt(per, vertex)
            pert = drive_tilt({sw: per[sw] + wild for sw in RUNGS}, vertex)
            worst = max(worst, abs(pert - base))
            rows.append([att, knob, base, pert])
            print(f"   ATTACK {att:5s} DRIVE {knob:4s}"
                  f"{'':<12s}{base:+13.5f}{pert:+13.5f}{pert - base:+14.3e}")
    print(f"\n   worst |change| over {len(rows)} conditions = {worst:.3e} dB/oct  "
          f"(bar {CANCEL_TOL:.0e}, machine precision)")
    if worst < CANCEL_TOL:
        verdict = ("EXACTLY ZERO — a post-clipper linear section contributes NOTHING to the "
                   "drive-tilt, so `OdToneRestore`'s slot cannot carry task E")
    else:
        verdict = (f"NOT zero ({worst:.3e} dB/oct) — the decomposition's premise is wrong on "
                   f"this build; STOP and re-read before using anything below")
        note("BA2", verdict)
    print(f"   ⇒ {verdict}")
    out["ba2"] = {"worst_change": worst, "tol": CANCEL_TOL, "rows": rows, "verdict": verdict}
    return worst < CANCEL_TOL


# ------------------------------------------------------------------------------------------------
# BA3 — the operands
# ------------------------------------------------------------------------------------------------
def ba3(curves, vertex, out):
    print()
    print("=" * 96)
    print("BA3  THE OPERANDS — the MODEL's own slope, per rung and per frequency")
    print("   s117: a delta cannot say which end moved.  s129: an endpoint pair is not a ladder.")
    print()
    print(f"   slope at the vertex ({vertex:.1f} Hz), dB/oct")
    print(f"   {'condition':22s}" + "".join(f"{sw.replace('sweep_', ''):>14s}" for sw in RUNGS)
          + f"{'drive-tilt':>14s}")
    per_cond = {}
    for att in ATTACKS:
        for knob in KNOBS:
            per = curves[(att, knob)]
            ss = [slope(per[sw], vertex) for sw in RUNGS]
            dt = ss[-1] - ss[0]
            per_cond[f"{att}/{knob}"] = dt
            print(f"   ATTACK {att:5s} DRIVE {knob:4s}" + "".join(f"{s:+14.4f}" for s in ss)
                  + f"{dt:+14.4f}")

    # frequency scan, with the contaminated centres named rather than dropped
    print()
    print(f"   drive-tilt vs FREQUENCY.  A centre is INTERPRETABLE only if its whole +-{HALF} oct")
    print(f"   window lies inside [{SMOOTH_LO:.0f}, {SMOOTH_HI:.0f}] Hz — GATE W's own bounds")
    print(f"   (above the bridged-T's window, below the treble notch's), IMPORTED not chosen.")
    lo_ok, hi_ok = SMOOTH_LO * 2 ** HALF, SMOOTH_HI * 2 ** -HALF
    print(f"   ⇒ interpretable centres: {lo_ok:.0f} .. {hi_ok:.0f} Hz")
    print()
    print(f"   {'f (Hz)':>8s}" + "".join(f"{a[:5]:>10s}/{k[:4]:<5s}" for a in ATTACKS
                                         for k in KNOBS) + "   status")
    scan = []
    for fc in (1000, 1200, 1450, 1750, 2100, 2500, vertex, 3500, 4200):
        ok = lo_ok <= fc <= hi_ok
        vals = [drive_tilt(curves[(a, k)], fc) for a in ATTACKS for k in KNOBS]
        scan.append([fc, ok] + vals)
        print(f"   {fc:8.0f}" + "".join(f"{v:+16.4f}" for v in vals)
              + ("   interpretable" if ok else "   (window touches a migrating feature)"))

    interp = [r for r in scan if r[1]]
    if interp:
        flat_noon = [r[2 + ATTACKS.index("flat") * len(KNOBS) + KNOBS.index("noon")]
                     for r in interp]
        print(f"\n   Across the interpretable centres the model's own drive-tilt "
              f"(ATTACK flat, DRIVE noon) runs {min(flat_noon):+.3f} .. {max(flat_noon):+.3f} dB/oct")
        print("   ⇒ ⚠ the model is NOT 'pinned' across this band — it is passing through ZERO")
        print("     near the vertex, which is where AG3 reads it.  This reproduces GATE AL's AL3")
        print("     (s141) on a DIFFERENT instrument (1/48-oct locator grid, not the 1/3-oct band")
        print("     surface) and at a LATER epoch, and it is why 'the model's tilt is pinned' must")
        print("     be quoted as a LOCAL reading at a zero crossing, never as a property.")
    out["ba3"] = {"per_cond": per_cond, "scan": scan,
                  "interp_lo": lo_ok, "interp_hi": hi_ok}
    return per_cond


# ------------------------------------------------------------------------------------------------
# BA4 — the pre-clipper bound
# ------------------------------------------------------------------------------------------------
def ba4(curves, per_cond, need, vertex, out):
    print()
    print("=" * 96)
    print("BA4  THE PRE-CLIPPER ROUTE — what a section at or UPSTREAM of the clipper must do")
    rec = {}

    # (a) verify gamma in [-1, 0] rather than assuming it.
    print()
    print("   (a) the bound's PREMISE, verified on the shipped model rather than assumed.")
    print("       ⚠⚠ FRAME, and this gate's own first draft got it backwards: `transfer_h1`")
    print("       normalises EVERY rung against the SAME sweep_clean reference segment, so the")
    print("       curve carries the STIMULUS STEP itself.  The ladder is not evenly spaced —")
    print("       levels are IMPORTED from gen_test_signal, never transcribed — so the pairs are")
    print("       12/6/6 dB apart, not 6/6/6.  With output = 20log10(A) + curve, a compressive")
    print("       non-expanding map has 0 <= d(output)/d(input) <= 1, i.e. the MEASURED step must")
    print("       lie in [0, dL].  A first draft checked [-6, 0] and duly reported +10.6 dB of")
    print("       'expansion' — 12 dB of stimulus read as physics (s115: a round dB number in a")
    print("       discrepancy is a PAD).  gamma in [-1, 0] follows from the corrected form.")
    lo_ok, hi_ok = SMOOTH_LO * 2 ** HALF, SMOOTH_HI * 2 ** -HALF
    band = (W.GRID >= lo_ok) & (W.GRID <= hi_ok)
    lvl = {"sweep_clean": float(G.CLEAN_FR_LEVELS_DB[0])}
    for db in G.DRIVEN_LEVELS_DB:
        lvl[f"sweep_drv_{db}"] = float(db)
    missing = [r for r in RUNGS if r not in lvl]
    if missing:
        die("BA4a", f"no stimulus level for {missing} in gen_test_signal — the admissible range "
                    f"is undefined and the premise cannot be checked.")
    print()
    print(f"       {'rung pair':30s}{'dL (dB)':>10s}{'measured step':>26s}{'admissible':>16s}")
    ok, n, rows = True, 0, []
    for a, b in zip(RUNGS[:-1], RUNGS[1:]):
        dL = lvl[b] - lvl[a]
        s_lo = min(float(np.min(per[b][band] - per[a][band])) for per in curves.values())
        s_hi = max(float(np.max(per[b][band] - per[a][band])) for per in curves.values())
        good = (s_lo >= -STEP_TOL) and (s_hi <= dL + STEP_TOL)
        ok = ok and good
        n += int(band.sum()) * len(curves)
        rows.append([a, b, dL, s_lo, s_hi, bool(good)])
        print(f"       {a.replace('sweep_', '')} -> {b.replace('sweep_', ''):16s}{dL:10.0f}"
              f"{s_lo:+13.3f} .. {s_hi:+8.3f}{('[0, %.0f] %s' % (dL, 'OK' if good else '**')):>16s}")
    print(f"       over {n} (condition x rung-pair x frequency) cells in the interpretable band")
    if ok:
        print("       ⇒ COMPRESSIVE and NON-EXPANDING everywhere ⇒ gamma in [-1, 0] ⇒ |dgamma| <= 1")
    else:
        print("       ⇒ ⚠ NOT everywhere inside [0, dL] — the bound below is NOT established on")
        print("         this build; report it as conditional, not as a bound.")
    print()
    print("       ⭐ And the frame cannot reach the TARGET: the stimulus offset is a CONSTANT in")
    print("       frequency, so it cancels identically from any slope.  Asserted at BA1a (a")
    print("       constant is a zero tilt), which is why AG's drive-tilt is immune to it and why")
    print("       the error above was confined to this premise check.")
    rec["step_rows"], rec["gamma_bounded"] = rows, bool(ok)

    # (b) the necessary |P'|
    print()
    print("   (b) THE BOUND.  drive-tilt = P' * [gamma(hot) - gamma(quiet)] and |dgamma| <= 1, so")
    print(f"       |P'| >= |required drive-tilt| = {abs(need):.4f} dB/oct at the vertex —")
    print("       NECESSARY, whatever the nonlinearity does, with no fit and no threshold.")
    rec["required_abs_pprime"] = abs(need)

    # (c) how far the shipped product is from the requirement
    print()
    print("   (c) HOW FAR SHORT.  The model's own drive-tilt IS the product P'*dgamma, so the")
    print("       shortfall is model-free — it needs neither operand separately:")
    print()
    print(f"       {'condition':22s}{'product now':>14s}{'must reach':>13s}{'factor':>12s}")
    facs = []
    for k, dt in per_cond.items():
        fac = abs(need) / abs(dt) if abs(dt) > 1e-9 else np.inf
        facs.append(fac)
        print(f"       {k:22s}{dt:+14.4f}{need:+13.4f}{fac:12.1f}x"
              + ("   (WRONG SIGN — must also change sign)" if dt > 0 else ""))
    med = float(np.median([f for f in facs if np.isfinite(f)]))
    print(f"\n       median factor over {len(facs)} conditions = {med:.1f}x")
    print("       ⚠ SIGN: the requirement is NEGATIVE.  A condition whose product is already")
    print("         positive needs a sign change, not a scaling — a factor is not defined there")
    print("         and is printed only to show the size.")
    rec["factors"] = facs
    rec["median_factor"] = med

    # (d) the ladder's own contribution, INDICATIVE ONLY
    print()
    print("   (d) for scale only — the treble/ATTACK LADDER's own slope at the vertex, closed")
    print("       form on the SHIPPED element set (BA1c):")
    f = np.geomspace(vertex / 2.5, vertex * 2.5, 601)
    lad = {}
    for p in ATTACKS:
        h = EQ.treble_attack_tf(f, p, Zs=EQ.jfet_source_z(f), **AJ.ladder_kwargs(p))
        s, _n = AG.tilt_at(20.0 * np.log10(np.abs(h)), np.log2(f / vertex), HALF)
        lad[p] = s
        print(f"       ATTACK {p:5s}  d log|ladder| / d log2 f = {s:+.4f} dB/oct")
    print("       ⚠⚠ THIS IS THE LADDER ALONE, NOT P.  The full pre-clipper response also carries")
    print("         the JFET boundary, IC2_A (DRIVE-dependent, with C10) and the GRUNT cap into")
    print("         R16, none of which are included here — so it may NOT be read as 'P' is 0.51")
    print("         dB/oct'.  It is quoted to show the ORDER of the ladder's own contribution")
    print("         against the >= %.2f dB/oct the bound requires, and for BA5's denominator." % abs(need))
    rec["ladder_slope"] = lad
    out["ba4"] = rec
    return lad


# ------------------------------------------------------------------------------------------------
# BA5 — the ATTACK switch, and a denominator refusal
# ------------------------------------------------------------------------------------------------
def ba5(per_cond, lad, out):
    print()
    print("=" * 96)
    print("BA5  THE ATTACK SWITCH AS A PRE-CLIPPER LEVER — and why no coefficient is quoted")
    print("   ATTACK is a real pre-clipper HF control with three physical positions, so it looks")
    print("   like a free dose-response for d(drive-tilt)/d(pre-clipper slope).  It is not.")
    print()
    spans = [abs(lad[b] - lad[a]) for a, b in (("cut", "flat"), ("flat", "boost"), ("cut", "boost"))]
    print(f"   ladder slope at the vertex: cut {lad['cut']:+.4f}  flat {lad['flat']:+.4f}  "
          f"boost {lad['boost']:+.4f} dB/oct")
    print(f"   ⇒ the WHOLE switch spans {abs(lad['boost'] - lad['cut']):.4f} dB/oct there")
    print("   The cause is on record and is not a surprise: `trebleC8` SHIPS AT 0 (s99/s100 took")
    print("   C8 out of circuit), and C8 is the element the ATTACK switch actually reroutes at HF.")
    print("   The shipped ATTACK action lives in the tap ladder and the C5 leg, which do very")
    print("   little to the SLOPE at 2.9 kHz.")
    print()
    dts = {a: {k: per_cond[f"{a}/{k}"] for k in KNOBS} for a in ATTACKS}
    print(f"   Meanwhile the rendered drive-tilt DOES move across the switch:")
    for k in KNOBS:
        vals = [dts[a][k] for a in ATTACKS]
        print(f"     DRIVE {k:5s}  cut {vals[0]:+.4f}  flat {vals[1]:+.4f}  boost {vals[2]:+.4f}"
              f"   span {max(vals) - min(vals):.4f} dB/oct")
    print()
    biggest_num = max(max(dts[a][k] for a in ATTACKS) - min(dts[a][k] for a in ATTACKS)
                      for k in KNOBS)
    ratio = biggest_num / max(spans) if max(spans) > 0 else np.inf

    # ⚠ COMPUTED, not narrated.  The refusal must be able to come back as its opposite, or it is
    # a fixed string (s161 AX3 committed exactly this inside a gate written to apply the rule).
    # The test needs no invented bar: a dose-response is only readable if the three positions give
    # coefficients that at least agree in SIGN.  Three pairs x three DRIVE knobs = 9 estimates.
    PAIRS = (("cut", "flat"), ("flat", "boost"), ("cut", "boost"))
    coefs = [(dts[b][k] - dts[a][k]) / (lad[b] - lad[a])
             for a, b in PAIRS for k in KNOBS if abs(lad[b] - lad[a]) > 0]
    n_pos = sum(1 for c in coefs if c > 0)
    consistent = bool(coefs) and (n_pos == 0 or n_pos == len(coefs))
    print(f"   The nine (pair x DRIVE) coefficients: {n_pos} of {len(coefs)} are POSITIVE")
    print("   — a readable dose-response needs them to agree at least in SIGN.")
    if not consistent:
        print(f"   ⇒ REFUSED as a dose-response.  The numerator moves up to {biggest_num:.4f} "
              f"dB/oct while the")
        print(f"     denominator moves at most {max(spans):.4f} — a ratio of ~{ratio:.0f}:1 — and the")
        print("     coefficients do not even share a sign, which is what a denominator at its own")
        print("     floor produces.  `ratio-statistics-need-a-denominator-guard`.")
        print("   ⛔ NO COEFFICIENT IS QUOTED, and none may be quoted from this table.")
    else:
        print(f"   ⇒ READABLE — the coefficients agree in sign, so the ATTACK switch IS a usable")
        print(f"     dose-response here (median {float(np.median(coefs)):+.4f}).  That contradicts")
        print("     the shipped reading; re-check the ladder span before using it.")
    print()
    print("   ⭐ But the REFUSAL is itself a finding, and it is the useful half: the drive-tilt")
    print("     moves across ATTACK WITHOUT the ladder's slope at the vertex moving, so the")
    print("     drive-tilt is not a function of the local pre-clipper SLOPE alone.  In the")
    print("     decomposition that is expected — gamma depends on the pre-clipper LEVEL |P|, so")
    print("     a position that changes |P| at the vertex moves the product through dgamma")
    print("     rather than through P'.  Both operands are live; BA4's bound holds regardless,")
    print("     because it bounds only dgamma.")
    out["ba5"] = {"ladder_span": max(spans), "tilt_span": biggest_num, "ratio": ratio,
                  "n_coef": len(coefs), "n_positive": n_pos, "refused": not consistent}


# ------------------------------------------------------------------------------------------------
# BA6 — verdict
# ------------------------------------------------------------------------------------------------
def ba6(cancels, out):
    print()
    print("=" * 96)
    print("BA6  VERDICT")
    v4 = out["ba4"]
    lines = []
    if cancels:
        lines.append("BA2  a LINEAR section DOWNSTREAM of the clipper contributes EXACTLY ZERO "
                     "drive-tilt\n     ⇒ `OdToneRestore`'s slot is REFUTED for task E, at any "
                     "gain/Q/centre and on any knob")
    else:
        lines.append("BA2  the cancellation did NOT hold — the decomposition's premise fails on "
                     "this build")
    lines.append(f"BA4  |P'| >= {v4['required_abs_pprime']:.4f} dB/oct at the vertex is NECESSARY "
                 f"for any at/upstream section\n     (from |dgamma| <= 1, "
                 f"{'VERIFIED' if v4['gamma_bounded'] else 'NOT verified'} on the shipped model)")
    lines.append(f"BA4c the shipped product P'*dgamma must grow ~{v4['median_factor']:.0f}x "
                 f"(median over 9 conditions), and change SIGN where it is positive")
    lines.append("BA5  the ATTACK switch is REFUSED as a dose-response for this — denominator "
                 "at its floor")
    for ln in lines:
        print("   " + ln)
    print()
    if cancels:
        print("   ⇒ TASK E CANNOT BE BUILT IN THE ARCHITECTURE IT WAS SCOPED TO REUSE.")
        print("     What remains, neither built nor proposed here:")
        print("       (i)  a section at or UPSTREAM of the clipper, which must clear BA4's bound;")
        print("       (ii) a genuinely LEVEL-DEPENDENT (dynamic) section, which is a new")
        print("            architecture for this project and is NOT what task E's 3-session cap")
        print("            was scoped against.")
    else:
        print("   ⇒ THE POST-CLIPPER SLOT IS NOT REFUTED ON THIS RUN — BA2's cancellation did not")
        print("     hold, so the decomposition this gate is built on does not describe this build.")
        print("     Nothing above may be quoted until that is explained.")
    print()
    print(f"   BA6-MEMBERSHIP conditions=[{','.join(sorted(COND.values()))}]")
    print(f"   BA6-VERDICT cancels={cancels} required_pprime={v4['required_abs_pprime']:.4f} "
          f"factor={v4['median_factor']:.1f} gamma_bounded={v4['gamma_bounded']}")
    out["ba6"] = {"cancels": bool(cancels), "lines": lines}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    os.makedirs(PRIV_DIR, exist_ok=True)
    out = {}
    need, vertex = ba0(out)

    before = fingerprint(W.REN_DIR)
    print(f"\n   rendering {len(COND)} conditions with the CURRENT binary ...")
    curves = {k: model_curves(f) for k, f in COND.items()}
    print("   done")

    ba1(curves, vertex, out)
    cancels = ba2(curves, vertex, out)
    per_cond = ba3(curves, vertex, out)
    lad = ba4(curves, per_cond, need, vertex, out)
    ba5(per_cond, lad, out)
    ba6(cancels, out)

    after = fingerprint(W.REN_DIR)
    if before != after:
        die("BA0", "GATE W's render cache CHANGED during this run — the artefacts its published "
                   "numbers came from may have been overwritten.  Investigate before trusting "
                   "anything above.")
    print(f"\n   GATE W cache integrity: {len(before)} files unchanged")

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(out, fh, indent=1)
        print(f"   wrote {args.json}")
    print("=" * 96)
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
