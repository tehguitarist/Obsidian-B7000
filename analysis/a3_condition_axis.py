#!/usr/bin/env python3.11
"""a3_condition_axis -- the blend axis run at SEVEN operating points instead of one, to localise
A3's missing element from HARDWARE rather than from a fit (session 54, Phase 9 / A3; Sets B and C).

WHY
---
`a3_blend_axis.py` is the best-conditioned instrument this project has, and it existed at exactly
ONE operating point (DRIVE noon / GRUNT cut / ATTACK flat). Two questions it could not answer:

  * SET B -- IS THE MISSING ELEMENT POST-CLIPPER? A post-clipper LINEAR element multiplies the OD
    path by the same H(f) at every drive, so `H_req = G_ped/G_mdl` must be DRIVE-INDEPENDENT. That
    is the entire basis of session 50 item 2 ("only a post-clipper element can supply s(f)"), and it
    was inferred from a drive solve later found to RAIL at five bands (session 51 item 6) and then
    read backwards (session 53 item 1). Measuring H_req directly at DRIVE min / noon / max on the
    good axis settles it without the railed solve.

  * SET C -- WHICH NETWORK? ATTACK reroutes C8 inside the treble network (the OD path's one genuine
    two-path cancellation); GRUNT swaps the clipper's input coupling caps. If the pedal's measured
    OD transfer moves with ATTACK the carrier is in the treble ladder; if with GRUNT, at the clipper
    input. ⭐ This half is PEDAL-SIDE and MODEL-FREE: it compares the pedal against itself across
    switch positions, so it cannot inherit an error in the model the way every previous A3
    localisation could.

FIVE-POINT LADDERS, NOT FOUR
----------------------------
Each condition gets a full B = 0 / 0.25 / 0.50 / 0.75 / 1.00 ladder: the three interior points are
session 53's new captures, and the B = 1.00 point ALREADY EXISTS in the frozen 63-capture matrix
(`<condition>_base-od.wav` is that condition at BLEND max). So no condition is fitted on a short
ladder, and the 63-matrix is not modified.

THE B = 0 NORMALISER IS SHARED, AND THAT IS TESTED FIRST
--------------------------------------------------------
Every ladder divides by ONE file, `blend-0700_base-od.wav`. The justification is that at BLEND = 0
the wiper sits on the clean pin so the OD path contributes nothing -- which makes the capture
independent of DRIVE, GRUNT and ATTACK alike. Session 53 requested `drive-1700_blend-0700_base-od`
purely to test that, and step 0 below re-runs it per band. If it fails, EVERY number in this file is
invalid, so it gates rather than being reported as a footnote.

INHERITED CAVEATS -- read before quoting anything
-------------------------------------------------
  * theta is identified only up to SIGN (magnitudes cannot see it); `fold()` to [0, 180].
  * the axis is DEGENERATE in the bleed level b0, which is taken from the model. Set D measures it.
  * ⚠ the swept read carries the harmonic-power bias (session 52 item 3b) -- `read_a3_tones.py`
    measures it at ~2 deg over 40-1700 Hz, so it is small here, but it is not zero and these are
    swept captures.
  * ⭐ ATTACK is reachable since session 55 (`a3_blend_decompose ... attackIdx=1|2`), so ALL SEVEN
    conditions now have a model side and step 4 runs the step-2 localiser pedal-vs-MODEL. ⚠ that
    makes step 4 the STRICTER read but NOT the model-free one: step 2 stays as the fallback that
    cannot inherit a model error, and both are printed.

Run:
    python3.11 analysis/a3_condition_axis.py --selftest
    python3.11 analysis/a3_condition_axis.py
"""
import argparse
import cmath
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import a3_blend_axis as AX

REPORT = "analysis/reports/s54_matrix85.json"
SWEEP = "sweep_drv_-18"
TAKE_FLOOR_DB = AX.TAKE_FLOOR_DB
FIT_HI_HZ = AX.FIT_HI_HZ
B0_FILE = "blend-0700_base-od.wav"

# condition -> (interior-B files, B=1.00 file, model decompose CSV or None)
# The three interior files are session 53's captures; the B=1 file is the frozen matrix's own.
#
# ⭐ EVERY condition now has a model side (session 55). GRUNT was always reachable
# (`a3_blend_decompose`'s argv[1]) and the CSVs simply had never been rendered; ATTACK was
# genuinely unreachable until `attackIdx=` was added to that tool. Regenerate all seven with:
#     ./build/a3_blend_decompose 1 0.0 -18                        > build/a3_dec_drv0.0.csv
#     ./build/a3_blend_decompose 1 0.5 -18                        > build/a3_dec_drv0.5.csv
#     ./build/a3_blend_decompose 1 1.0 -18                        > build/a3_dec_drv1.0.csv
#     ./build/a3_blend_decompose 2 0.5 -18                        > build/a3_dec_grunt-flat.csv
#     ./build/a3_blend_decompose 0 0.5 -18                        > build/a3_dec_grunt-boost.csv
#     ./build/a3_blend_decompose 1 0.5 -18 attackIdx=1            > build/a3_dec_attack-boost.csv
#     ./build/a3_blend_decompose 1 0.5 -18 attackIdx=2            > build/a3_dec_attack-cut.csv
# ⚠ that binary is built by a hand-written `c++` command, NOT by CMake, so `cmake --build` will
# NOT rebuild it when a header changes -- session 37 item 12's stale-binary trap. Each CSV states
# its own grunt/attack/drive in its header line; check that before trusting one.
CONDITIONS = {
    "ref (drive noon)": (["blend-0930_base-od.wav", "blend-1200_base-od.wav",
                          "blend-1430_base-od.wav"], "ref-od.wav", "build/a3_dec_drv0.5.csv"),
    "drive min":        (["drive-0700_blend-0930_base-od.wav", "drive-0700_blend-1200_base-od.wav",
                          "drive-0700_blend-1430_base-od.wav"], "drive-0700_base-od.wav",
                         "build/a3_dec_drv0.0.csv"),
    "drive max":        (["drive-1700_blend-0930_base-od.wav", "drive-1700_blend-1200_base-od.wav",
                          "drive-1700_blend-1430_base-od.wav"], "drive-1700_base-od.wav",
                         "build/a3_dec_drv1.0.csv"),
    "grunt flat":       (["grunt-flat_blend-0930_base-od.wav", "grunt-flat_blend-1200_base-od.wav",
                          "grunt-flat_blend-1430_base-od.wav"], "grunt-flat_base-od.wav",
                         "build/a3_dec_grunt-flat.csv"),
    "grunt boost":      (["grunt-boost_blend-0930_base-od.wav", "grunt-boost_blend-1200_base-od.wav",
                          "grunt-boost_blend-1430_base-od.wav"], "grunt-boost_base-od.wav",
                         "build/a3_dec_grunt-boost.csv"),
    "attack boost":     (["attack-boost_blend-0930_base-od.wav",
                          "attack-boost_blend-1200_base-od.wav",
                          "attack-boost_blend-1430_base-od.wav"], "attack-boost_base-od.wav",
                         "build/a3_dec_attack-boost.csv"),
    "attack cut":       (["attack-cut_blend-0930_base-od.wav", "attack-cut_blend-1200_base-od.wav",
                          "attack-cut_blend-1430_base-od.wav"], "attack-cut_base-od.wav",
                         "build/a3_dec_attack-cut.csv"),
}


def load_report(path):
    if not os.path.exists(path):
        sys.exit("missing %s -- run: python3.11 analysis/comprehensive_report.py --jobs 8 "
                 "--out %s" % (path, path))
    d = json.load(open(path))
    return d["meta"]["bands"], {c["file"]: c for c in d["captures"]}


def col(caps, fname, key):
    """One capture's per-band dB column.

    ⚠ `plugin_db` carries the report's PER-CAPTURE gain-match and MUST have it un-applied before any
    cross-capture combination, or every BLEND point brings its own scalar and the mixing law fails
    by ~1.5 dB at B = 1 -- which reads as a real finding. `pedal_db` is raw. Same trap as
    `grunt_span_probe`'s (session 23); it cost `a3_blend_axis` its first run.
    """
    if fname not in caps:
        sys.exit("report has no %s" % fname)
    fr = caps[fname]["fr"]
    if SWEEP not in fr:
        sys.exit("%s has no %s" % (fname, SWEEP))
    v = np.asarray(fr[SWEEP][key], dtype=float)
    return v - float(fr[SWEEP]["gain_db_applied"]) if key == "plugin_db" else v


def ladder(caps, bands, files, b1, key):
    """{band: [t(B)] normalised to the shared B=0 capture} for one condition."""
    cols = [col(caps, B0_FILE, key)] + [col(caps, f, key) for f in files] + \
           [col(caps, b1, key)]
    ref = cols[0]
    return {b: [10.0 ** ((c[i] - ref[i]) / 20.0) for c in cols]
            for i, b in enumerate(bands) if all(np.isfinite(c[i]) for c in cols)}


def load_model_csv(path):
    if path is None or not os.path.exists(path):
        return None
    out = {}
    for line in open(path):
        if line.startswith("#") or not line.strip():
            continue
        v = [float(x) for x in line.split(",")]
        ref, od, cl = complex(v[1], v[2]), complex(v[5], v[6]), complex(v[7], v[8])
        out[v[0]] = (abs(od) / abs(ref), cmath.phase(od) - cmath.phase(cl))
    return out


def hreq_of(solved_map, name, bands):
    """{f: (|H_req| dB, argH_req deg)} for one condition, or {} if it has no model CSV.

    `H_req = G_ped / G_mdl` -- what a correction element would have to supply, at THIS condition.
    Factored out (session 55) because it is now computed four ways: two taper variants x two
    axes (DRIVE in step 3, the SWITCHES in step 4), and four copies of a phase-fold is how a
    sign convention drifts between two halves of the same verdict.
    """
    mdl = load_model_csv(CONDITIONS[name][2])
    if mdl is None:
        return {}
    h = {}
    for f in bands:
        if not solved_map[name].get(f, (0, 0, 0, False))[3]:
            continue
        key = min(mdl, key=lambda x: abs(x - f))
        if abs(key - f) > 0.06 * f:          # the model grid is the tool's own band list
            continue
        rm, thm = mdl[key]
        h[f] = (20 * math.log10(solved_map[name][f][0] / rm),
                ((AX.fold(solved_map[name][f][1]) - math.degrees(thm)) + 180) % 360 - 180)
    return h


# ⚠⚠ A dB residual at a band sitting in a deep cancellation null is NOT a law failure.
# `fit_taper`'s COST already guards against this (it divides by t, "so a deep null cannot dominate
# the fit") -- but the `worst |dt|` statistic it PRINTS is raw dB and has no such guard. Reading
# that number as the law's verdict is how session 54's first pass wrongly concluded the law FAILED
# for GRUNT flat/boost: their worst bands were 32 Hz (min|t| = 0.028) and 25 Hz (0.050), while every
# band above 50 Hz sat at <=0.10 dB. GRUNT boost/flat push far more bass into the clipper, so |OD|
# approaches the bleed at LF and the cancellation deepens -- physically expected, and it makes the
# dB residual explode for a fixed absolute error. Same class as session 49 item 7 and session 52
# item 1: the aggregate's RANGE was the problem, not its membership.
NULL_GUARD = 0.15          # |t| below this => null-dominated, reported separately, never in the verdict


def law_report(t, bands, Bint):
    """(worst dB over non-null bands, worst over null-dominated bands, list of null bands)."""
    wn = wnull = 0.0
    nulls = []
    for b in bands:
        _, _, res, bad = AX.quad_fit(t[b], Bint)
        if bad:
            continue
        r = max(abs(x) for x in res)
        if min(t[b][1:]) < NULL_GUARD:
            nulls.append(b)
            wnull = max(wnull, r)
        else:
            wn = max(wn, r)
    return wn, wnull, nulls


def turning_points(vals):
    """Count interior turning points (sign changes in successive differences) of a t(B) ladder."""
    d = np.diff(np.asarray(vals, dtype=float))
    s = np.sign(d)
    s = s[s != 0]
    return int(np.sum(s[1:] != s[:-1]))


def bad_take_scan(t, bands):
    """⭐ A THRESHOLD-FREE structural test for a defective capture, from the law's own geometry.

    For a FIXED complex G, `t(B) = |beta(B) + B.G| = |(1-B(1-b0)) + B.G|` traces a STRAIGHT LINE in
    the complex plane as B runs 0 -> 1. The modulus along a straight line is a hyperbola: it can
    fall to the line's closest approach to the origin and rise again, but it has AT MOST ONE
    interior minimum and NO interior maximum. So a ladder with two or more turning points is
    unreachable by ANY G, at any bleed level, under any taper -- it cannot be a circuit difference
    and must be a defective capture.

    That is strictly stronger than the level/flatness heuristic it replaces, which the fitted taper
    could absorb (it drove attack-cut's taper to a degenerate 0.957/0.980/0.905 and then the
    residual no longer looked flat, so the heuristic missed the very file it was written for).

    Returns {band: n_turning_points} for the offending bands.
    """
    bad = {}
    for b in bands:
        n = turning_points(t[b])
        if n >= 2:
            bad[b] = n
    return bad


def solve(t, bands, label, Bint):
    """⚠ A band is `identified` only if it is NOT null-dominated. Gating on the raw dB residual
    alone (the previous rule) silently rejected exactly the LF bands whose residual is large for a
    legitimate reason -- and kept no record of why."""
    res = {}
    for b in t:
        k1, k2, dres, bad = AX.quad_fit(t[b], Bint)
        r, th, cos_raw = AX.unpack(k1, k2, AX.model_b0())
        dt = float("nan") if bad else max(abs(x) for x in dres)
        ok = ((not bad) and min(t[b][1:]) >= NULL_GUARD and dt <= 0.30
              and abs(cos_raw) <= 1.02 and r > 1e-20)
        res[b] = (r, th, dt, ok)
    return res


def selftest():
    """Synthesise each condition's ladder through the law from a KNOWN (r, theta) that DIFFERS per
    condition, then check the solve recovers each one and that the per-condition comparison reports
    the true difference. Catches a mis-ordered file list or a mis-shared normaliser -- the two ways
    this tool could be silently wrong while every number still looks plausible."""
    b0 = AX.model_b0()
    worst_r = worst_t = worst_d = 0.0
    for i, name in enumerate(CONDITIONS):
        truth = {f: (0.2 + 0.05 * i + 0.3 * (f / 1000.0), math.radians(40.0 + 7.0 * i + f / 60.0))
                 for f in (40.0, 101.0, 254.0, 640.0, 1613.0)}
        t = {f: [abs((1.0 - B * (1.0 - b0)) + B * truth[f][0] * cmath.exp(1j * truth[f][1]))
                 for B in (0.0, 0.25, 0.50, 0.75, 1.00)] for f in truth}
        res = solve(t, list(truth), name, [0.25, 0.50, 0.75])
        for f, (r, th) in truth.items():
            worst_r = max(worst_r, abs(20 * math.log10(res[f][0] / r)))
            worst_t = max(worst_t, abs(AX.fold(res[f][1]) - AX.fold(th)))
            if i > 0:                       # the reported cross-condition delta must be exact too
                base = 40.0 + f / 60.0
                worst_d = max(worst_d, abs((AX.fold(res[f][1]) - base) - 7.0 * i))
    ok = worst_r < 1e-6 and worst_t < 1e-4 and worst_d < 1e-3
    print("  worst |dr| = %.3e dB, |dtheta| = %.3e deg, cross-condition |ddelta| = %.3e deg -> %s"
          % (worst_r, worst_t, worst_d, "PASS" if ok else "FAIL"))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--report", default=REPORT)
    ap.add_argument("--shared-taper", action="store_true", default=True)
    args = ap.parse_args()

    if args.selftest:
        print("=== SELFTEST ===")
        sys.exit(0 if selftest() else 1)

    b0 = AX.model_b0()
    bands_all, caps = load_report(args.report)
    print("bleed level from the model: b0 = %.5f (%+.2f dB); this axis is DEGENERATE in it.\n"
          % (b0, 20 * math.log10(b0)))

    # ---- step 0: the shared-normaliser control. GATES everything below. ----
    print("=== 0. B=0 CONTROL -- is the shared normaliser valid? ===")
    print("  At BLEND=0 the OD path contributes nothing, so this capture must be independent of")
    print("  DRIVE. Every ladder below divides by blend-0700, so a failure here invalidates all of")
    print("  it. (Session 53 asked for this file purely to test the assumption.)")
    a = col(caps, B0_FILE, "pedal_db")
    b = col(caps, "drive-1700_blend-0700_base-od.wav", "pedal_db")
    idx = [i for i, f in enumerate(bands_all) if 20 <= f <= FIT_HI_HZ
           and np.isfinite(a[i]) and np.isfinite(b[i])]
    d = np.array([b[i] - a[i] for i in idx])
    print("  drive max minus drive min at B=0, over %d bands 20-%.0f Hz: mean %+.3f dB, "
          "worst %+.3f dB" % (len(idx), FIT_HI_HZ, d.mean(), max(d, key=abs)))
    ok0 = np.max(np.abs(d)) <= TAKE_FLOOR_DB
    print("  VERDICT: %s (floor %.3f dB)\n"
          % ("VALID -- shared normalisation stands" if ok0 else
             "⛔ INVALID -- do not read anything below", TAKE_FLOOR_DB))
    if not ok0:
        sys.exit(1)

    # ---- step 1: solve every condition ----
    print("=== 1. PER-CONDITION SOLVE ===")
    print("  The BLEND pot is the SAME physical pot in every capture, so its fitted taper must NOT")
    print("  move with the condition. Fitting it per condition and reporting the spread is a")
    print("  self-check: a taper that wanders is absorbing a condition-dependent defect.")
    print("  ⚠ the law verdict EXCLUDES null-dominated bands (min|t| < %.2f) -- see NULL_GUARD.\n"
          % NULL_GUARD)
    fitted, tapers, good = {}, {}, []
    for name, (files, b1, _) in CONDITIONS.items():
        t = ladder(caps, bands_all, files, b1, "pedal_db")
        bands = [f for f in sorted(t) if f <= FIT_HI_HZ]
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            Bint, _ = AX.fit_taper(t, bands, name[:12], False)
        wn, wnull, nulls = law_report(t, bands, Bint)
        bad = bad_take_scan(t, bands)
        suspect = len(bad) >= 0.3 * len(bands)      # a defect shows at MOST bands, not one or two
        ok = (wn <= TAKE_FLOOR_DB) and not suspect
        print("  %-16s taper %.3f/%.3f/%.3f | law %6.3f dB (non-null, %2d bands) | "
              "null bands %-22s %s"
              % (name, Bint[0], Bint[1], Bint[2], wn, len(bands) - len(nulls),
                 ("%s (worst %.2f)" % ([int(x) for x in nulls], wnull)) if nulls else "none",
                 "OK" if ok else ("⛔ BAD TAKE" if suspect else "⚠ law > floor")))
        if suspect:
            ex = sorted(bad)[:4]
            print("      ⛔ STRUCTURALLY IMPOSSIBLE at %d of %d bands (e.g. %s): the t(B) ladder"
                  " has >=2 turning points, which NO complex G can produce at any bleed level or"
                  " taper. A defective capture, not a circuit difference."
                  % (len(bad), len(bands), ", ".join("%.0f Hz" % f for f in ex)))
            for f in ex[:2]:
                print("         %5.0f Hz  t(B) = %s" % (f, "  ".join("%.3f" % x for x in t[f])))
            # localise: if dropping ONE interior point restores a structurally-possible ladder at
            # every band, that single capture is the defect and only it needs re-taking.
            culprit = None
            for j in (1, 2, 3):
                if all(turning_points([v for k, v in enumerate(t[b]) if k != j]) < 2
                       for b in bands):
                    culprit = j
                    break
            if culprit is not None:
                print("         -> LOCALISED to ONE file: %s  (dropping it makes every band"
                      " structurally possible again; the other two are fine)" % files[culprit - 1])
            else:
                print("         -> re-capture all three: %s" % ", ".join(files))
        tapers[name] = Bint
        fitted[name] = (t, Bint, wn)
        if ok:
            good.append(name)

    if not good:
        sys.exit("no condition passes the law -- nothing below would be meaningful")
    arr = np.array([tapers[n] for n in good])
    print("\n  taper spread across the %d PASSING conditions: %s"
          % (len(good), "  ".join("B%.2f: %.4f..%.4f (ptp %.4f)"
                                  % (n, arr[:, i].min(), arr[:, i].max(), np.ptp(arr[:, i]))
                                  for i, n in enumerate((0.25, 0.50, 0.75)))))
    shared = list(arr.mean(axis=0))
    print("  -> SHARED taper %.4f/%.4f/%.4f, averaged over PASSING conditions only."
          % tuple(shared))
    print("     ⚠ averaging in a failing condition poisons this and NaNs every comparison below;"
          " that is what session 54's first pass did.")

    # ⭐ PER-CONDITION tapers are the PRIMARY read, and that is a deliberately CONSERVATIVE choice
    # for the question in step 3. Letting each condition fit its own taper gives the data the
    # maximum freedom to make H_req look DRIVE-INDEPENDENT; if drive-dependence survives even that,
    # it is not an artefact of the nuisance parameter. The shared taper is reported as a
    # sensitivity check below rather than used to generate the headline.
    solved, solved_shared = {}, {}
    for name, (t, Bint, _) in fitted.items():
        bl = [f for f in sorted(t) if f <= FIT_HI_HZ]
        solved[name] = solve(t, bl, name, Bint)
        solved_shared[name] = solve(t, bl, name, shared)

    # ---- step 2: the model-free localiser ----
    print("\n=== 2. ⭐ MODEL-FREE LOCALISER -- does the PEDAL's OD transfer move with the switch? ===")
    print("  Pedal vs pedal across switch positions. Large dtheta under ATTACK => the carrier is in")
    print("  the treble ladder; under GRUNT => at the clipper input; under DRIVE => it is not a")
    print("  linear element at all. Reference = drive noon / grunt cut / attack flat.")
    ref = solved["ref (drive noon)"]
    bands = [f for f in sorted(ref) if 40 <= f <= FIT_HI_HZ]
    print("\n  %-14s %s" % ("condition", "".join("%8.0f" % f for f in bands[:9])))
    for name in CONDITIONS:
        if name == "ref (drive noon)":
            continue
        row = []
        for f in bands[:9]:
            if ref[f][3] and solved[name].get(f, (0, 0, 0, False))[3]:
                row.append(AX.fold(solved[name][f][1]) - AX.fold(ref[f][1]))
            else:
                row.append(float("nan"))
        print("  %-14s %s" % (name, "".join("%+8.1f" % x for x in row)))
    print("  (dtheta in degrees vs the reference condition, per band)")

    print("\n  summary over 40-%.0f Hz, both identified:" % FIT_HI_HZ)
    for name in CONDITIONS:
        if name == "ref (drive noon)":
            continue
        dth = [AX.fold(solved[name][f][1]) - AX.fold(ref[f][1]) for f in bands
               if ref[f][3] and solved[name].get(f, (0, 0, 0, False))[3]]
        dr = [20 * math.log10(solved[name][f][0] / ref[f][0]) for f in bands
              if ref[f][3] and solved[name].get(f, (0, 0, 0, False))[3]]
        if dth:
            print("    %-14s dtheta mean %+6.1f deg  rms %5.1f  worst %+6.1f   |   "
                  "dr mean %+6.2f dB  rms %5.2f  (%d bands)"
                  % (name, np.mean(dth), float(np.sqrt(np.mean(np.square(dth)))),
                     max(dth, key=abs), np.mean(dr),
                     float(np.sqrt(np.mean(np.square(dr)))), len(dth)))

    # ---- step 3: session 50 item 2's own test ----
    print("\n=== 3. IS H_req DRIVE-INDEPENDENT? (session 50 item 2's premise, measured directly) ===")
    print("  A post-clipper LINEAR element multiplies |OD| by the same H(f) at every drive. So if")
    print("  the missing element is post-clipper, H_req = G_ped/G_mdl must be IDENTICAL at drive")
    print("  min, noon and max. A drive-dependent H_req rules the whole post-clipper class out.")
    DRIVES = ("drive min", "ref (drive noon)", "drive max")
    hreq = {n: h for n in DRIVES if (h := hreq_of(solved, n, bands))}
    # sensitivity: repeat H_req under the SHARED taper so the verdict cannot rest on the nuisance
    hreq_sh = {n: h for n in DRIVES if (h := hreq_of(solved_shared, n, bands))}

    common = sorted(set.intersection(*[set(h) for h in hreq.values()])) if len(hreq) == 3 else []
    if common:
        print("\n      f   |H| min   noon    max    spread  |  argH min   noon     max   spread")
        sm, sp = [], []
        for f in common:
            m = [hreq[n][f][0] for n in ("drive min", "ref (drive noon)", "drive max")]
            p = [hreq[n][f][1] for n in ("drive min", "ref (drive noon)", "drive max")]
            sm.append(np.ptp(m))
            sp.append(np.ptp(p))
            print("  %5.0f  %+7.2f %+7.2f %+7.2f   %6.2f  | %+8.1f %+7.1f %+7.1f  %6.1f"
                  % (f, m[0], m[1], m[2], sm[-1], p[0], p[1], p[2], sp[-1]))
        print("\n  |H| spread across DRIVE: mean %.2f dB, worst %.2f dB (floor %.3f)"
              % (np.mean(sm), max(sm), TAKE_FLOOR_DB))
        print("  argH spread across DRIVE: mean %.1f deg, worst %.1f deg" % (np.mean(sp), max(sp)))
        print("  VERDICT: H_req is %s"
              % ("DRIVE-INDEPENDENT -- consistent with a post-clipper linear element"
                 if max(sm) <= 3 * TAKE_FLOOR_DB and max(sp) <= 10 else
                 "⛔ DRIVE-DEPENDENT -- NO post-clipper linear element can produce this, whatever "
                 "its order"))
        c2 = sorted(set.intersection(*[set(h) for h in hreq_sh.values()])) if len(hreq_sh) == 3 \
            else []
        if c2:
            sm2 = [np.ptp([hreq_sh[n][f][0] for n in hreq_sh]) for f in c2]
            sp2 = [np.ptp([hreq_sh[n][f][1] for n in hreq_sh]) for f in c2]
            print("  SENSITIVITY (shared taper, %d bands): |H| spread mean %.2f dB worst %.2f | "
                  "argH mean %.1f deg worst %.1f"
                  % (len(c2), np.mean(sm2), max(sm2), np.mean(sp2), max(sp2)))
            print("  -> the conclusion %s with the nuisance taper."
                  % ("HOLDS" if (max(sm2) > 3 * TAKE_FLOOR_DB) == (max(sm) > 3 * TAKE_FLOOR_DB)
                     else "⚠ CHANGES"))

    # ---- step 4: step 2's localiser, run pedal-vs-MODEL (session 55) ----
    print("\n=== 4. ⭐ THE LOCALISER, PEDAL-vs-MODEL -- does H_req move with the SWITCHES? ===")
    print("  Step 2 asks whether the PEDAL's OD transfer moves with a switch. It always does, and")
    print("  its own caveat is that it does not normalise for how big each perturbation is (ATTACK")
    print("  moves 220 pF; GRUNT moves 47n/220n), so a small dtheta under ATTACK is ambiguous")
    print("  between 'the ladder is not the carrier' and 'the ladder barely moved'.")
    print("  Differencing H_req instead removes whatever the model ALREADY reproduces, so what is")
    print("  left is only the part of each switch's effect the model gets WRONG -- which is the")
    print("  quantity a carrier hypothesis is actually about.")
    print("  A post-clipper linear element sits downstream of the treble ladder AND the clipper")
    print("  input, so it multiplies the OD path identically in every position ⇒ H_req must be")
    print("  SWITCH-INDEPENDENT, exactly as step 3 requires it to be drive-independent.")
    href = hreq_of(solved, "ref (drive noon)", bands)
    SWITCHES = [n for n in CONDITIONS if n != "ref (drive noon)" and n not in DRIVES]
    hsw = {n: hreq_of(solved, n, bands) for n in SWITCHES}
    mdl_ref = load_model_csv(CONDITIONS["ref (drive noon)"][2])

    # ⚠⚠ ONE COMMON BAND SET, or the rows are not comparable. Per-condition band sets differ
    # (grunt boost identifies 8 bands where the others identify 12, because its deeper LF
    # cancellation costs it identifiability), and an rms over DIFFERENT members is not a ranking
    # -- that is session 49 item 7 / session 52 item 1 / session 54 item 6, three times over. The
    # per-condition counts are printed too, so the restriction cannot hide a condition that is
    # mostly unidentified.
    common4 = sorted(set(href) & set.intersection(*[set(h) for h in hsw.values()])) if hsw else []
    if not common4:
        print("  no band is identified in every condition -- step 4 cannot run")
        return
    print("\n  Decomposed on ONE common band set (%d bands, %.0f-%.0f Hz): what the PEDAL does"
          % (len(common4), common4[0], common4[-1]))
    print("  across the switch, what the MODEL does, and the residual (= the H_req move).")
    print("\n  %-14s %-22s %-22s  bands" % ("condition", "d|G| dB  ped / mdl / RESID",
                                            "dtheta deg ped / mdl / RESID"))
    sw_rows = []
    for name in SWITCHES:
        h, mdl = hsw[name], load_model_csv(CONDITIONS[name][2])
        dm = [h[f][0] - href[f][0] for f in common4]
        dp = [((h[f][1] - href[f][1]) + 180) % 360 - 180 for f in common4]
        # the model's OWN response to this switch, so "the perturbation is small" and "the model
        # gets it wrong" are separated on the page instead of only in a caveat below.
        mk = lambda m, f: m[min(m, key=lambda x: abs(x - f))]
        dmm = [20 * math.log10(mk(mdl, f)[0] / mk(mdl_ref, f)[0]) for f in common4]
        dpm = [((math.degrees(mk(mdl, f)[1] - mk(mdl_ref, f)[1])) + 180) % 360 - 180
               for f in common4]
        dpp = [x + y for x, y in zip(dp, dpm)]          # pedal side = resid + model side
        dmp = [x + y for x, y in zip(dm, dmm)]
        rms = lambda v: float(np.sqrt(np.mean(np.square(v))))
        sw_rows.append((name, dm, dp, common4))
        print("  %-14s %6.2f /%6.2f /%6.2f      %6.1f /%6.1f /%6.1f          %2d"
              % (name, rms(dmp), rms(dmm), rms(dm), rms(dpp), rms(dpm), rms(dp), len(hsw[name])))
    print("  (rms over the common bands; RESID = ped - mdl = the d(H_req) a correction must absorb)")
    if sw_rows:
        wm = max(max(abs(x) for x in dm) for _, dm, _, _ in sw_rows)
        wp = max(max(abs(x) for x in dp) for _, _, dp, _ in sw_rows)
        print("\n  worst across the four switch conditions: |H_req| %.2f dB (floor %.3f), "
              "argH %.1f deg" % (wm, TAKE_FLOOR_DB, wp))
        print("  VERDICT: H_req is %s"
              % ("SWITCH-INDEPENDENT -- consistent with a post-clipper linear element"
                 if wm <= 3 * TAKE_FLOOR_DB and wp <= 10 else
                 "⛔ SWITCH-DEPENDENT -- no post-clipper linear element of any order reproduces "
                 "this"))
        # ⚠ STATE IT EXACTLY, and no stronger. H_req = G_ped/G_mdl moves if EITHER the pedal has an
        # element the model lacks OR the model's own response to the switch is wrong -- and the
        # model's ATTACK/GRUNT response has never been gated on its own. So what a switch-dependent
        # H_req falsifies is "pedal_OD = model_OD x ONE switch-independent linear H", nothing more.
        # It does NOT separate "the model's switch response is wrong" from "there is a pre-clipper
        # element", and it does NOT identify which network carries it -- the SIZE of the row is not
        # a ranking, because a bigger perturbation can still produce a bigger residual under a
        # single shared cause. Same shape of caveat as step 3's, one axis over.
        print("  ⚠ falsifies 'pedal_OD = model_OD x ONE switch-independent linear H' and no more:")
        print("    H_req also moves if the MODEL's own ATTACK/GRUNT response is wrong (never gated")
        print("    on its own), so this does not separate that from a pre-clipper element, and the")
        print("    row sizes are NOT a ranking of which network carries it.")
        print("  ⚠ step 2 (pedal-vs-pedal) remains the model-free fallback; where the two disagree,")
        print("    step 2 is the one that cannot inherit a model error.")


if __name__ == "__main__":
    main()
