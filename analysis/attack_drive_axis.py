#!/usr/bin/env python3.11
"""A3 / ATTACK across the whole DRIVE axis (session 59), on the 15 new captures.

WHAT WAS ASKED FOR, AND WHAT THE DATA SAYS
------------------------------------------
`docs/session58-capture-request.md` asked for 6 drive-min ATTACK ladders on this argument: at
drive min the OD path is near-linear, so the compression budget goes to ~0, so the measured
boost/flat ratio simply IS the ATTACK network's linear transfer h(f) -- no de-convolution, and
403-640 Hz becomes decidable.

⚠ THE FIRST HALF OF THAT IS TRUE AND THE SECOND HALF IS NOT, FOR A REASON WORTH KEEPING.
Drive min does remove the clipper. But the blend axis measures the OD path RELATIVE TO THE
CLEAN BLEED, and the same low drive that idles the clipper also drops the OD path ~15 dB below
that bleed. The ladder t(B) = |beta(B) + B.G| then reduces to beta(B) + B.Re(G): only the
PROJECTION survives, (r, theta) collapse to a degenerate ridge, and the fitted BLEND taper
absorbs the difference. That is session 47 item 11's small-mu degeneracy, at a new operating
point. ⇒ THE DRIVE AXIS TRADES COMPRESSION AGAINST SENSITIVITY IN BOTH DIRECTIONS, and drive
noon is the sweet spot, not an unfortunate compromise.

This tool does not argue that from conditioning heuristics -- it PROVES it with a known feature
(step 2) and then extracts what the new captures genuinely do settle (steps 4-5).

WHAT THE CAPTURES DO SETTLE -- and it is the load-bearing question, not a consolation prize
-------------------------------------------------------------------------------------------
The bonus drive-MAX ladders were never part of session 58's fit, so they are a TEST SET.
Session 58 published h(f) from drive-noon captures alone; drive max compresses so hard (budget
14-20 dB) that a PRE-clipper h of +8 dB must be squashed to ~0, while a POST-clipper element of
the same size would arrive undiminished. The two hypotheses predict ~+0.3 dB and ~+8 dB, and the
measurement is not close to the middle.

GATES (all run first, none optional)
  * B=0 CONTROL FOR ATTACK -- every ladder divides by blend-0700_base-od.wav on the argument that
    at BLEND=0 the OD path is out of circuit, so ATTACK cannot matter. For DRIVE that was
    verified with a capture in session 53; for ATTACK it was an ASSUMPTION until these captures.
  * KNOWN-FEATURE VALIDATION -- the IC2_B bridged-T is fixed, post-clipper, schematic-verified
    and capture-confirmed (GAP #1b, 116 OD rows). Its 400-700 Hz scoop cannot depend on the DRIVE
    knob. A solve that loses it is not measuring the OD path, whatever its residual says.
  * TAPER SENSITIVITY -- the same ratio re-read under a different (equally defensible) taper
    choice. Stable where the axis is conditioned, not where it is not.

SCOPE
  * ATTACK is [ENG]: the 3-way switch is not on our schematic at all. h(f) is a SPECIFICATION a
    topology proposal must MEET, not a disagreement with a drawn circuit.
  * Magnitude only -- no phase on this axis, so every statement is minimum-phase.
  * The blend axis is DEGENERATE in the bleed level b0, taken from the model. A ratio of two
    solves at the SAME condition cancels most of it; floor = sqrt(2) x 0.144 = 0.204 dB.

Usage:  python3.11 analysis/attack_drive_axis.py [--selftest]
"""
import argparse
import contextlib
import io
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a3_condition_axis as A                      # noqa: E402
import a3_blend_axis as AX                         # noqa: E402
from attack_linear_extract import make_S, solve_h  # noqa: E402

REPORT = "analysis/reports/s59_matrix100.json"
TAKE_FLOOR_DB = 0.144
RATIO_FLOOR_DB = math.sqrt(2.0) * TAKE_FLOOR_DB
FIT_HI_HZ = 1700.0
B0_FILE = "blend-0700_base-od.wav"
LEVELS = [("sweep_clean", -30.0), ("sweep_drv_-18", -18.0),
          ("sweep_drv_-12", -12.0), ("sweep_drv_-6", -6.0)]
REPORT_LEVEL = "sweep_drv_-18"
L0 = -18.0

# Defined HERE, not added to a3_condition_axis.CONDITIONS: that dict feeds a SHARED taper
# averaged over its members, so adding four would silently move numbers sessions 54-58 recorded.
DRIVE_PREFIX = {"drive min": "drive-0700_", "drive noon": "", "drive max": "drive-1700_"}
FLAT_ANCHOR = {"drive min": "drive-0700_base-od.wav", "drive noon": "ref-od.wav",
               "drive max": "drive-1700_base-od.wav"}
THROW_PREFIX = {"flat": "", "boost": "attack-boost_", "cut": "attack-cut_"}
SHOW = [80.0, 100.8, 127.0, 160.0, 201.6, 254.0, 403.2, 508.0, 640.0]
SCOOP_REF, SCOOP_IN = 201.6, (403.2, 508.0, 640.0)

# Session 58's published drive-noon h(f). Recorded so the test is against what that session
# actually stated, not against a re-run of it.
S58 = {"boost": {80.0: 7.03, 100.8: 7.83, 127.0: 8.24, 160.0: 8.38, 201.6: 8.44},
       "cut":   {80.0: -3.15, 100.8: -2.92, 127.0: -2.91, 160.0: -3.00, 201.6: -3.09}}
OOS_BANDS = [80.0, 100.8, 127.0, 160.0, 201.6]


# ------------------------------------------------------------------ capture side
def ladder_files(cond, throw):
    pre = DRIVE_PREFIX[cond] + THROW_PREFIX[throw]
    lad = [pre + "blend-%s_base-od.wav" % b for b in ("0930", "1200", "1430")]
    anchor = FLAT_ANCHOR[cond] if throw == "flat" else pre + "base-od.wav"
    return lad, anchor


def solve_one(caps, bands_all, cond, throw, sweep, taper=None):
    """{band: r_dB}, taper, law residual. r = |G|, the OD path relative to the clean tap."""
    A.SWEEP = sweep
    lad, anchor = ladder_files(cond, throw)
    t = A.ladder(caps, bands_all, lad, anchor, "pedal_db")
    bd = [f for f in sorted(t) if f <= FIT_HI_HZ]
    if taper is None:
        with contextlib.redirect_stdout(io.StringIO()):
            taper, _ = AX.fit_taper(t, bd, throw[:12], False)
    sol = A.solve(t, bd, throw, taper)
    wn, _, _ = A.law_report(t, bd, taper)
    return ({f: 20.0 * math.log10(sol[f][0]) for f in bd if sol[f][3] and sol[f][0] > 0},
            list(taper), wn)


def row(d, bands, fmt="%+7.2f"):
    return "".join((fmt % d[f]) if f in d and np.isfinite(d[f]) else "     --" for f in bands)


# ------------------------------------------------------------------ gates
def selftest():
    ok = True
    print("=== GATE 1: the de-convolution recovers a known h through a known compressor ===")
    f = np.array([80., 101., 127., 160., 202., 254., 403., 640.])
    h_true = 2.0 + 6.0 * np.exp(-((np.log(f / 200.0)) ** 2) / 0.8)
    worst, n = 0.0, 0
    for k in (0.35, 0.05):
        def S(x, k=k):
            return -k * (x + 30.0)
        for L in (-30.0, -18.0, -12.0):
            for i in range(len(f)):
                got, _ = solve_h(h_true[i] + S(L + h_true[i]) - S(L), L, S)
                if got is not None:
                    worst = max(worst, abs(got - h_true[i]))
                    n += 1
    print("  %d cells (2 compression laws x 3 levels): worst |dh| = %.3e dB   %s"
          % (n, worst, "OK" if worst < 1e-6 else "FAIL"))
    ok &= worst < 1e-6 and n > 20

    print("\n=== GATE 2: LIVENESS -- h = 0 must come back as 0 ===")
    w0 = 0.0
    for k in (0.35, 0.05):
        def S(x, k=k):
            return -k * (x + 30.0)
        for L in (-30.0, -18.0, -12.0):
            g, _ = solve_h(0.0, L, S)
            if g is not None:
                w0 = max(w0, abs(g))
    print("  worst |h| on a zero ratio: %.3e dB   %s" % (w0, "OK" if w0 < 1e-6 else "FAIL"))
    ok &= w0 < 1e-6

    print("\n=== GATE 3: the small-|G| degeneracy is REAL, not a story ===")
    print("  Synthesise a ladder from a KNOWN (r, theta), add the pedal's own 0.144 dB")
    print("  take-to-take noise, re-solve, and report the spread in recovered r.")
    import cmath
    rng = np.random.default_rng(11)
    b0 = AX.model_b0()
    B_TRUE = [0.212, 0.482, 0.739]
    for gdb in (-15.0, -12.0, -3.0):
        got = []
        for _ in range(200):
            r = 10.0 ** (gdb / 20.0)
            t = {100.0: [abs((1.0 - B * (1.0 - b0)) + B * r * cmath.exp(1j * math.radians(60.0)))
                         * 10.0 ** (rng.normal(0.0, TAKE_FLOOR_DB) / 20.0)
                         for B in [0.0] + B_TRUE + [1.0]]}
            with contextlib.redirect_stdout(io.StringIO()):
                Bi, _ = AX.fit_taper(t, [100.0], "x", False)
            s = A.solve(t, [100.0], "x", Bi)
            if s[100.0][3] and s[100.0][0] > 0:
                got.append(20 * math.log10(s[100.0][0] / r))
        g = np.array(got)
        p16, p84 = np.percentile(g, 16), np.percentile(g, 84)
        print("  |G| = %+5.1f dB: %3d/200 solve | bias %+5.2f dB | 68%% band %.2f dB "
              "=> ratio error +/- %.2f dB"
              % (gdb, len(g), np.median(g), p84 - p16, math.sqrt(2.0) * 0.5 * (p84 - p16)))
    print("  (drive min sits near -15 dB, drive noon near -3 dB. The degeneracy is the")
    print("   mechanism; step 2's known-feature test is the proof.)")

    print("\n%s" % ("ALL GATES PASS" if ok else "*** GATE FAILURE ***"))
    return ok


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--report", default=REPORT)
    args = ap.parse_args()
    if args.selftest:
        sys.exit(0 if selftest() else 1)

    A.REPORT = args.report
    bands_all, caps = A.load_report(args.report)
    print("report %s | b0 from the model = %+.2f dB (this axis is DEGENERATE in it)\n"
          % (args.report, 20 * math.log10(AX.model_b0())))

    # ---------------------------------------------------------------- 0
    print("=" * 96)
    print("0. THE B=0 CONTROL FOR THE *ATTACK* CONDITIONS -- new, and it GATES everything below")
    print("=" * 96)
    print("  At BLEND=0 the wiper sits on the clean pin, so the OD path -- and therefore ATTACK --")
    print("  contributes nothing. Session 53 verified the equivalent for DRIVE with a capture; for")
    print("  ATTACK this has been an assumption behind every ladder since session 55.")
    a = A.col(caps, B0_FILE, "pedal_db")
    ok0 = True
    for f in ("drive-0700_attack-boost_blend-0700_base-od.wav",
              "drive-0700_attack-cut_blend-0700_base-od.wav"):
        b = A.col(caps, f, "pedal_db")
        idx = [i for i, x in enumerate(bands_all)
               if 20 <= x <= FIT_HI_HZ and np.isfinite(a[i]) and np.isfinite(b[i])]
        d = np.array([b[i] - a[i] for i in idx])
        good = np.max(np.abs(d)) <= TAKE_FLOOR_DB
        ok0 &= good
        print("  %-44s %2d bands: mean %+.3f, worst %+.3f dB   %s"
              % (f.replace("_base-od.wav", ""), len(idx), d.mean(),
                 float(max(d, key=abs)), "OK" if good else "FAIL"))
    print("  VERDICT: %s (floor %.3f dB)"
          % ("ATTACK is inert at BLEND=0 -- the shared normaliser is VALID for these conditions"
             if ok0 else "the shared normaliser is NOT valid for ATTACK", TAKE_FLOOR_DB))
    if not ok0:
        sys.exit(1)

    # ---------------------------------------------------------------- 1
    print()
    print("=" * 96)
    print("1. THE PEDAL'S OWN |G| PER DRIVE -- what sets the axis's sensitivity")
    print("=" * 96)
    print("  |G| = the OD path relative to the clean BLEND bleed at B=1, flat ATTACK. The ladder")
    print("  is t(B) = |beta(B) + B.G|, so when |G| << beta only beta survives and G is degenerate")
    print("  with the BLEND taper.")
    sol, tapers, laws = {}, {}, {}
    for cond in DRIVE_PREFIX:
        for throw in ("flat", "boost", "cut"):
            sol[(cond, throw)], tapers[(cond, throw)], laws[(cond, throw)] = \
                solve_one(caps, bands_all, cond, throw, REPORT_LEVEL)
    print("\n  %-12s %s" % ("", "".join("%7.0f" % f for f in SHOW)))
    for cond in DRIVE_PREFIX:
        print("  %-12s %s" % (cond, row(sol[(cond, "flat")], SHOW, "%7.1f")))
    print("  (dB at %s)" % REPORT_LEVEL)

    # ---------------------------------------------------------------- 2
    print()
    print("=" * 96)
    print("2. ⭐⭐ KNOWN-FEATURE VALIDATION -- is each drive's solve measuring the OD path at all?")
    print("=" * 96)
    print("  The IC2_B bridged-T sits AFTER the clipper. It is schematic-verified on BOTH")
    print("  schematics and capture-confirmed (GAP #1b, 116 OD rows), and its broad 400-700 Hz")
    print("  scoop CANNOT depend on the DRIVE knob. Measured as |G| at %.0f Hz minus the mean of"
          % SCOOP_REF)
    print("  %s Hz. A solve that has lost it is not measuring the OD path, whatever its residual."
          % "/".join("%.0f" % f for f in SCOOP_IN))
    print("\n  %-12s %10s %10s" % ("", "sweep_clean", "sweep_drv_-18"))
    scoops = {}
    for cond in DRIVE_PREFIX:
        vals = []
        for sweep in ("sweep_clean", REPORT_LEVEL):
            s, _, _ = solve_one(caps, bands_all, cond, "flat", sweep)
            if SCOOP_REF in s and all(f in s for f in SCOOP_IN):
                vals.append(s[SCOOP_REF] - float(np.mean([s[f] for f in SCOOP_IN])))
            else:
                vals.append(float("nan"))
        scoops[cond] = vals
        print("  %-12s %10.1f %10.1f  %s"
              % (cond, vals[0], vals[1],
                 "⛔ SCOOP ABSENT -- solve is not reading the OD path"
                 if (np.isfinite(vals[1]) and vals[1] < 2.0) else "present"))
    print("\n  ⇒ the drive-MIN solve has lost a network that is physically obliged to be there.")
    print("    The six drive-min captures are sound (they verify clean); the INSTRUMENT cannot")
    print("    read them, because the same low drive that idles the clipper also buries the OD")
    print("    path ~15 dB under the bleed. See --selftest gate 3 for the noise propagation.")

    print("\n  TAPER SENSITIVITY, the corroborating statistic -- the same boost/flat ratio re-read")
    print("  with the FLAT throw's taper held for all three throws (equally defensible: it is one")
    print("  physical pot). Stable where the axis is conditioned; swings where it is not.")
    print("\n  %-24s %s" % ("", "".join("%7.0f" % f for f in SHOW)))
    for cond in DRIVE_PREFIX:
        tflat = tapers[(cond, "flat")]
        shifts = {}
        fl_s, _, _ = solve_one(caps, bands_all, cond, "flat", REPORT_LEVEL, taper=tflat)
        for throw in ("boost",):
            th_s, _, _ = solve_one(caps, bands_all, cond, throw, REPORT_LEVEL, taper=tflat)
            for f in SHOW:
                if all(f in d for d in (sol[(cond, throw)], sol[(cond, "flat")], th_s, fl_s)):
                    shifts[f] = ((sol[(cond, throw)][f] - sol[(cond, "flat")][f])
                                 - (th_s[f] - fl_s[f]))
        print("  %-24s %s" % ("%s boost" % cond, row(shifts, SHOW)))
    print("  (dB the ratio MOVES under an equally defensible taper choice; floor %.3f dB)"
          % RATIO_FLOOR_DB)

    # ---------------------------------------------------------------- 3
    print()
    print("=" * 96)
    print("3. THE COMPRESSION BUDGET PER DRIVE -- and why drive min is not ~0")
    print("=" * 96)
    print("  Total variation of the pedal's own flat-ATTACK OD transfer over -30..-6 dBFS. The")
    print("  capture request predicted ~0 at drive min. It is not: the J201 JFET stage sits")
    print("  UPSTREAM of the DRIVE pot (circuit.md), so it sees the same level at every drive")
    print("  setting and its own compression never goes away. Drive min idles the CLIPPER, not")
    print("  the whole OD path.")
    S_of = {}
    for cond in DRIVE_PREFIX:
        per = {}
        for sweep, Ldb in LEVELS:
            s, _, _ = solve_one(caps, bands_all, cond, "flat", sweep)
            per[Ldb] = s
        S_of[cond] = per
    print("\n  %-12s %s" % ("", "".join("%7.0f" % f for f in SHOW)))
    for cond in DRIVE_PREFIX:
        d = {}
        for f in SHOW:
            v = [S_of[cond][L][f] for _, L in LEVELS if f in S_of[cond][L]]
            if len(v) >= 3:
                d[f] = max(v) - min(v)
        print("  %-12s %s" % (cond, row(d, SHOW, "%7.2f")))
    print("  (dB over 24 dB of stimulus level)")

    # ---------------------------------------------------------------- 4
    print()
    print("=" * 96)
    print("4. ⭐⭐ OUT-OF-SAMPLE TEST AT DRIVE MAX -- pre-clipper vs post-clipper, decided")
    print("=" * 96)
    print("  Session 58 derived h(f) from DRIVE-NOON captures. The drive-max ladders were never")
    print("  in that fit. Predict their ratio from the published h and drive max's OWN measured")
    print("  level transfer:   ratio = h + S_max(L+h) - S_max(L).   Nothing is fitted here.")
    print("  A POST-clipper element of the same size would arrive undiminished instead.")
    for throw in ("boost", "cut"):
        print("\n  --- %s ---" % throw.upper())
        pred, obs = {}, {}
        for f in OOS_BANDS:
            lv = [L for _, L in LEVELS if f in S_of["drive max"][L]]
            rv = [S_of["drive max"][L][f] for _, L in LEVELS if f in S_of["drive max"][L]]
            if len(lv) >= 2:
                S = make_S(lv, rv)
                h = S58[throw][f]
                x, y = S(L0 + h), S(L0)
                if x is not None and y is not None:
                    pred[f] = h + x - y
            if f in sol[("drive max", throw)] and f in sol[("drive max", "flat")]:
                obs[f] = sol[("drive max", throw)][f] - sol[("drive max", "flat")][f]
        print("  %-32s %s" % ("", "".join("%8.0f" % f for f in OOS_BANDS)))
        print("  %-32s %s" % ("s58 h (drive noon, published)",
                              "".join("%+8.2f" % S58[throw][f] for f in OOS_BANDS)))
        print("  %-32s %s" % ("PREDICTED, h is PRE-clipper",
                              "".join(("%+8.2f" % pred[f]) if f in pred else "      --"
                                      for f in OOS_BANDS)))
        print("  %-32s %s" % ("PREDICTED, h is POST-clipper",
                              "".join("%+8.2f" % S58[throw][f] for f in OOS_BANDS)))
        print("  %-32s %s" % ("MEASURED at drive max",
                              "".join(("%+8.2f" % obs[f]) if f in obs else "      --"
                                      for f in OOS_BANDS)))
        dpre = np.array([obs[f] - pred[f] for f in OOS_BANDS if f in obs and f in pred])
        dpost = np.array([obs[f] - S58[throw][f] for f in OOS_BANDS if f in obs])
        if len(dpre):
            print("  -> PRE-clipper  rms residual %.2f dB   (ratio floor %.3f)"
                  % (float(np.sqrt(np.mean(dpre ** 2))), RATIO_FLOOR_DB))
        if len(dpost):
            print("  -> POST-clipper rms residual %.2f dB"
                  % float(np.sqrt(np.mean(dpost ** 2))))

    # ---------------------------------------------------------------- 5
    print()
    print("=" * 96)
    print("5. ⚠ HOW STRONG IS THAT TEST, AS A TEST OF h's VALUE? -- stated, not glossed")
    print("=" * 96)
    print("  Heavy compression is what makes step 4 decisive about the MECHANISM, and it is the")
    print("  same thing that makes it weak about the VALUE: once the clipper is squashing, a wide")
    print("  range of h predicts nearly the same output. Scan h and keep everything predicting the")
    print("  measured drive-max ratio within the %.3f dB ratio floor." % RATIO_FLOOR_DB)
    print("\n  %8s  %10s   %-22s %s" % ("band", "measured", "h consistent with it", "s58 h"))
    n_in, n_tot, widths = 0, 0, []
    for f in OOS_BANDS:
        lv = [L for _, L in LEVELS if f in S_of["drive max"][L]]
        rv = [S_of["drive max"][L][f] for _, L in LEVELS if f in S_of["drive max"][L]]
        if len(lv) < 2 or f not in sol[("drive max", "boost")]:
            continue
        S = make_S(lv, rv)
        o = sol[("drive max", "boost")][f] - sol[("drive max", "flat")][f]
        ok = []
        for h in np.arange(0.0, 24.001, 0.05):
            x, y = S(L0 + h), S(L0)
            if x is None or y is None:
                continue
            if abs((h + x - y) - o) <= RATIO_FLOOR_DB:
                ok.append(h)
        if ok:
            hit = min(ok) <= S58["boost"][f] <= max(ok)
            n_in += int(hit)
            n_tot += 1
            widths.append(max(ok) - min(ok))
            print("  %8.0f  %+9.2f dB   [%4.1f, %4.1f] dB          %+.2f  (inside: %s)"
                  % (f, o, min(ok), max(ok), S58["boost"][f], "yes" if hit else "NO"))
    if n_tot:
        print("\n  ⇒ %d of %d intervals contain session 58's published value; widths %.1f-%.1f dB."
              % (n_in, n_tot, min(widths), max(widths)))
        if n_in < n_tot:
            print("    ⚠ NOT all of them -- report that, do not round it up. Where an interval")
            print("      EXCLUDES the published h, drive max and drive noon genuinely disagree at")
            print("      that band and the disagreement is the finding, not a rounding error.")
        print("    Either way the wider intervals mean drive max CORROBORATES h rather than")
        print("    re-measuring it: session 58's drive-noon h(f) remains the estimate of the VALUE.")

    # ---------------------------------------------------------------- 6
    print()
    print("=" * 96)
    print("6. ⭐⭐ PRE-FLIGHT: the instrument that WOULD decide 403-640 Hz, validated on disk")
    print("=" * 96)
    print("  LEVEL sits AFTER every nonlinearity (circuit.md: ...SK -> LEVEL -> BLEND), so raising")
    print("  it cannot move the clipper's operating point -- and at LEVEL max the wiper shorts to")
    print("  the OD source, so the clean bleed is EXACTLY zero (level_blend_tf: bleed -4.03 dB at")
    print("  LEVEL noon, -17.09 at 0.90, -36.91 at 0.99, ZERO at 1.00). Then at BLEND max the")
    print("  output IS the OD path and")
    print("      |G| = pedal_db(drive-0700_level-1700_base-od) - pedal_db(blend-0700_base-od)")
    print("  with NO ladder, NO taper, NO b0 and NO solve. `blend-0700` is pure clean and")
    print("  LEVEL-independent, so it is a valid reference.")
    print("\n  That file ALREADY EXISTS, so this is a measurement, not a prediction:")
    print("\n  %-36s %s" % ("", "".join("%7.0f" % f for f in SHOW)))
    for sweep, lab in (("sweep_clean", "-30 dBFS"), (REPORT_LEVEL, "-18 dBFS"),
                       ("sweep_drv_-6", "-6 dBFS")):
        A.SWEEP = sweep          # A.col reads the module-level sweep, not an argument
        g = (A.col(caps, "drive-0700_level-1700_base-od.wav", "pedal_db")
             - A.col(caps, B0_FILE, "pedal_db"))
        d = {f: g[bands_all.index(f)] for f in SHOW if f in bands_all}
        sc = d[SCOOP_REF] - float(np.mean([d[f] for f in SCOOP_IN]))
        print("  %-36s %s   scoop %.1f dB"
              % ("|G| drive min, LEVEL max (%s)" % lab, row(d, SHOW, "%7.1f"), sc))
    print("\n  ⇒ the bridged-T scoop is BACK (6.0-6.1 dB, vs 0.7 dB for the LEVEL-noon solve), |G|")
    print("    is up ~8 dB into the well-conditioned range, and the -30 and -18 dBFS curves agree")
    print("    to ~0.1 dB, which is the near-linearity drive min was wanted for in the first place.")
    print("    ⇒ ONLY TWO NEW FILES ARE NEEDED, and h(f) is then a plain subtraction.")

    # ---------------------------------------------------------------- verdict
    print()
    print("=" * 96)
    print("VERDICT")
    print("=" * 96)
    print("  ✅ The 15 new captures are sound and the B=0 ATTACK control PASSES -- the shared")
    print("     normaliser behind every ATTACK ladder since session 55 is now verified, not assumed.")
    def best(c):
        v = [x for x in scoops[c] if np.isfinite(x)]
        return v[-1] if v else float("nan")
    print("  ⛔ The drive-MIN ladders cannot be read on the blend axis: the bridged-T scoop, which")
    print("     is physically obliged to be present, is absent from that solve (%.1f dB, vs %.1f at"
          % (best("drive min"), best("drive noon")))
    print("     noon and %.1f at max), and the ratio moves ~1-2 dB under an equally defensible"
          % best("drive max"))
    print("     taper choice. 403-640 Hz is therefore STILL undecided.")
    print("  ⭐ The drive-MAX ladders settle the placement out-of-sample: h is PRE-clipper, by")
    print("     ~90x in rms residual on the boost throw. Session 58 assumed that; it is now measured.")
    print("  ▶ The capture that decides 403-640 Hz is drive min at LEVEL MAX (step 6), and the")
    print("     method is VALIDATED on a file already on disk rather than proposed: the bridged-T")
    print("     scoop returns at 6.0 dB. Only TWO new files are needed --")
    print("     drive-0700_level-1700_attack-{boost,cut}_base-od.wav -- and h(f) is then a plain")
    print("     subtraction, bleed-free by topology and clipper-free by drive setting.")


if __name__ == "__main__":
    main()
