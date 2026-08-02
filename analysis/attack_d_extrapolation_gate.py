#!/usr/bin/env python3
"""GATE H — does GATE F's D-invariance premise EXTEND to the fitted ladder? (session 98)

⭐⭐ WHY THIS EXISTS. Session 95's absolute-level term `g` is founded on one measured fact: the
downstream transfer `D(f) = render_dB - ladder_dB` is INVARIANT to the ladder, so an absolute
LADDER target can be derived from an absolute RENDER measurement. GATE F checks that — between
`PROP` and `CAL`, two C8=0 ladders that are "very different" from each other but BOTH sit close to
the drawn network (worst |D_cal - D_prop| = 0.183 dB).

The session-97 winner does not. It asks R7 x7.28 and C7 x0.244, well outside the region where the
invariance was ever measured — and session 98's matrix run says the render is **26-47 dB down**
across 20-800 Hz on the bleed-free `level-1700` rows while the screen reports `g` satisfied to
**0.26 dB at every throw**. Those two statements cannot both be about the same quantity unless D
moved. This gate measures D at the CANDIDATE's own ladder and compares it with D at PROP.

⚠ `imposed-checks-cannot-corroborate` / `a calibration tested where it was fitted proves nothing`:
GATE F is an INTERPOLATION check (two mild ladders) being relied on as an EXTRAPOLATION guarantee
(one wild one). That is exactly the gap this measures, and it is the general lesson: **an
invariance is only established over the region it was measured in, and a fit will walk out of that
region precisely because nothing in the objective knows where the region ends.**

Usage:
    python3.11 analysis/attack_d_extrapolation_gate.py                 # uses the s97 winner
    python3.11 analysis/attack_d_extrapolation_gate.py --fits-json X   # any --best output
"""
import argparse
import importlib.util
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_spec = importlib.util.spec_from_file_location("ass", os.path.join(HERE, "attack_shape_screen.py"))
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)

A, M, T, RG = S.A, S.M, S.T, S.RG
OUT_DIR = "build/attack_d_extrap"
DEF_FITS = "analysis/reports/s97_attack_best_posttap.json"

# ⭐ SESSION 99 -- the FitParams -> screen-ladder mapping and the sub-band partition now live in
# ONE place, `attack_shape_screen`, and this gate imports them. They were duplicated here, which
# is precisely how a gate and the thing it gates stop describing the same network (the `resid()`
# lesson of session 97, applied to the ladder and to the bands).
parse_fits = S.ladder_from_fits


def render(tag, pos, fits):
    out = os.path.join(OUT_DIR, "%s_%s.wav" % (tag, pos))
    cmd = [S.RENDER, "analysis/test_signal_48k.wav", out] + S.BASE_ARGS \
        + ["--attack", S.ATTACK_IDX[pos]]
    for f in fits:
        cmd += ["--fit", f]
    # ⚠ `check_stamp(path, expect)` takes argv MINUS the binary and the two paths, and it
    # `sys.exit`s on a mismatch rather than returning a bool. A first draft passed the full `cmd`
    # and used the return value as a cache-hit test: it printed a stamp mismatch listing the two
    # forms side by side, which reads as a stale artefact and is actually the caller's slice bug.
    if os.path.exists(out) and os.path.exists(out + ".args.json"):
        RG.check_stamp(out, cmd[3:])       # exits if the condition really has changed
        return out
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("render failed:\n%s\n%s" % (" ".join(cmd), r.stderr))
    RG.stamp(out, cmd)
    return out


def d_of(paths, base, rd, c5t):
    """D(f) = render_dB - ladder_dB, per throw, on the record's broadband bins."""
    orig = A.load(A.ORIG)
    zb = M.ZSA[-M.NBB:]
    out = {}
    for pos in S.POSITIONS:
        x = A.load(paths[pos])
        x, _ = A.align(x, orig)
        f, m = A.transfer(A.seg_of(x, S.SEG), A.seg_of(orig, S.SEG))
        p = dict(base)
        p["Rd"] = rd[pos]
        p["C5"] = base["C5"] + c5t[pos]
        out[pos] = np.interp(S.FBB, f, m) - M.db(T.tf_tap(S.FBB, zb, T.TAP_OF[pos], p, 0.0))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits-json", default=DEF_FITS)
    ap.add_argument("--json", default="analysis/reports/s99_d_extrapolation.json",
                    help="where to write the record (was hardcoded to the s98 name)")
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)

    d = json.load(open(args.fits_json))
    fits = d.get("fits") or (d.get("best") or {}).get("fits")
    if not fits:
        sys.exit("%s has no 'fits' list (nor best.fits)" % args.fits_json)
    cand, crd, cc5t = parse_fits(fits)

    print("=" * 104)
    print("GATE H  DOES GATE F's D-INVARIANCE EXTEND TO THE FITTED LADDER?")
    print("=" * 104)
    print("  candidate: %s" % os.path.basename(args.fits_json))
    print("  ladder vs PROP: %s"
          % "  ".join("%s x%.3g" % (e, cand[e] / S.PROP[e]) for e in S.SHARED + list(S.TAP)))

    print("\n  rendering PROP and the candidate at the g condition (drive min / LEVEL max /"
          " BLEND max) ...")
    prop_fits = list(S.CAL_FITS)          # placeholder; PROP is rendered from its own fit list
    prop_fits = ["attackTapRa=%.6g" % S.PROP["Ra"], "attackTapRb=%.6g" % S.PROP["Rb"],
                 "attackTapRc=%.6g" % S.PROP["Rc"], "attackTapR11=%.6g" % S.PROP["R11"],
                 "trebleR7=%.6g" % S.PROP["R7"], "trebleLadderR12=%.6g" % S.PROP["R12"],
                 "trebleLadderR14=%.6g" % S.PROP["R14"], "trebleC9=%.6g" % S.PROP["C9"],
                 "trebleC6=%.6g" % S.PROP["C6"], "trebleC7=%.6g" % S.PROP["C7"],
                 "trebleC5=%.6g" % S.PROP["C5"],
                 "attackC5TrimBoost=%.6g" % S.PROP_C5T["boost"],
                 "attackC5TrimCut=%.6g" % S.PROP_C5T["cut"],
                 "trebleLadderDampR=%.6g" % S.PROP_RD["flat"],
                 "attackDampBoost=%.6g" % S.PROP_RD["boost"],
                 "attackDampCut=%.6g" % S.PROP_RD["cut"], "trebleC8=0"]
    pp = {p: render("prop", p, prop_fits) for p in S.POSITIONS}
    cp = {p: render("cand", p, fits) for p in S.POSITIONS}

    dp, dc = d_of(pp, S.PROP, S.PROP_RD, S.PROP_C5T), d_of(cp, cand, crd, cc5t)

    # ⚠ KNOWN ANSWER FIRST: this gate's own D_prop must reproduce GATE F's, or the two are not
    # measuring the same quantity and the comparison below is meaningless. GATE F prints
    # D_prop medians of +30.65 / +30.62 / +30.65; anything materially off that is a setup error
    # in THIS file, not a finding about the candidate.
    print("\n  H1 KNOWN ANSWER -- D at PROP must reproduce GATE F's own D_prop:")
    ok1 = True
    for p in S.POSITIONS:
        med = float(np.median(dp[p]))
        good = 29.0 < med < 32.5
        ok1 &= good
        print("     %-6s median %+7.2f dB   %s" % (p, med, "OK" if good else "OFF -- setup error"))
    if not ok1:
        print("  ⛔ refusing to report H2: this file is not measuring GATE F's quantity.")
        return 1

    print("\n  H2 D AT THE CANDIDATE's OWN LADDER vs D AT PROP:")
    print("     %-6s %11s %11s %11s %11s" % ("throw", "D prop", "D cand", "median Δ", "worst |Δ|"))
    worst = 0.0
    rows = {}
    for p in S.POSITIONS:
        dd = dc[p] - dp[p]
        w = float(np.max(np.abs(dd)))
        worst = max(worst, w)
        rows[p] = dict(d_prop=float(np.median(dp[p])), d_cand=float(np.median(dc[p])),
                       median_delta=float(np.median(dd)), worst=w)
        print("     %-6s %+11.2f %+11.2f %+11.2f %11.2f"
              % (p, np.median(dp[p]), np.median(dc[p]), np.median(dd), w))
    # GATE F's own limit, applied to the region the fit actually reached.
    ok = worst < 1.0
    print("\n     worst |D_cand - D_prop| over the band = %.2f dB (GATE F's limit 1.0, and its"
          " measured 0.183 between PROP and CAL)" % worst)
    print("     ⇒ %s" % ("INVARIANT here too -- the g term transfers, and the matrix regression"
                         " must be explained some other way."
                         if ok else
                         "NOT INVARIANT AT THIS LADDER. GATE F measured the premise between two"
                         " MILD ladders and\n       the fit walked outside that region, so `g`"
                         " was scoring a ladder level that does NOT\n       reach the render."
                         " The absolute term is founded on an INTERPOLATION and was used\n"
                         "       as an EXTRAPOLATION."))
    # --- H3  did the RENDER actually move by what `g` asked for? ---------------------------
    # ⚠⚠ H2 ALONE MUST NOT BE READ AS THE EXPLANATION, and this is the check that stops it being
    # read that way. A non-invariance of 3.84 dB is a real defect in `g`'s foundation, but the
    # matrix regression it is being invoked to explain is 26-47 dB. `aggregate-moved-check-
    # membership-first`'s cousin: a defect that is REAL and a defect that is SUFFICIENT are two
    # different claims, and a gate that finds the first is under enormous pressure to be quoted as
    # having found the second. H3 measures the thing the term actually promised: `g` asked the
    # ladder to move by +Delta, so the candidate render minus the pedal should now be ~0.
    # ⚠⚠ SESSION 99 -- H3 AND H4 HAVE SWAPPED ROLES, AND THAT IS THE POINT, NOT A TIDY-UP.
    # Session 98's H3 asked the sufficiency question against the POOLED median, because that was
    # the term `g` actually shipped; H4 then decomposed it and found the pooled median was the
    # defect. Now that the shipped term IS per sub-band, the promise H3 must test is the
    # per-sub-band one, and the POOLED reading becomes the labelled CONTROL (H4) that shows what
    # the superseded statistic would have said. Testing the retired statistic as though it were
    # the live one would be `verify-the-BASELINE-not-its-LABEL` in reverse.
    print("\n  H3 DID THE RENDER MOVE BY WHAT `g` ASKED FOR, PER SUB-BAND? (the term's promise)")
    rec = S.abs_gain_record()                   # per throw AND per sub-band (session 99)
    orig = A.load(A.ORIG)
    curves = {}
    for p in S.POSITIONS:
        xp = A.load(pp[p]); xp, _ = A.align(xp, orig)
        xc = A.load(cp[p]); xc, _ = A.align(xc, orig)
        fp, mp = A.transfer(A.seg_of(xp, S.SEG), A.seg_of(orig, S.SEG))
        fc, mc = A.transfer(A.seg_of(xc, S.SEG), A.seg_of(orig, S.SEG))
        curves[p] = np.interp(S.FBB, fc, mc) - np.interp(S.FBB, fp, mp)
    h3 = {}
    print("     %14s %6s %11s %11s %11s"
          % ("sub-band", "bins", "cut", "boost", "flat"))
    for i, (lab, lo, hi) in enumerate(S.G_ACTIVE):
        sel = S.G_BAND & (S.FBB >= lo) & (S.FBB < hi)
        vals = [float(rec[p][i] - np.median(curves[p][sel])) for p in S.POSITIONS]
        h3[lab] = dict(bins=int(sel.sum()),
                       shortfall={p: v for p, v in zip(S.POSITIONS, vals)})
        print("     %14s %6d %+11.2f %+11.2f %+11.2f" % (lab, int(sel.sum()), *vals))
    print("     (shortfall = what `g` asked for minus what the render delivered, dB)")
    worst3 = max(max(abs(v) for v in b["shortfall"].values()) for b in h3.values())
    print("\n     worst per-sub-band shortfall %.2f dB. ⇒ %s" % (
        worst3,
        "the render DID follow the ladder target in EVERY sub-band, so `g` did its job at this\n"
        "       condition and a matrix regression is NOT a failure of the absolute term -- look\n"
        "       elsewhere (the matrix grades 25 Hz-16 kHz at many DRIVE settings; `g` is one\n"
        "       condition at drive MIN)."
        if worst3 < 2.0 else
        "the render did NOT follow the ladder target. Either the fit did not reach the\n"
        "       requirement, or the transfer itself moved -- read H2 before choosing."))
    # --- H4  the same measurement, PER SUB-BAND instead of as one median --------------------
    # ⭐⭐ THIS IS THE FINDING. `g_of` is `median(gabs[G_BAND])`, and G_BAND's 100 bins are
    # LINEARLY spaced from 87.9 to 1599.6 Hz: 8 of them lie below 200 Hz and 69 above 800, so the
    # median bin sits at 1019.5 Hz. `g` is therefore a ~1 kHz statistic wearing a broadband name,
    # and it is structurally incapable of registering a low-frequency collapse.
    # ⚠ The source comment beside G_BAND says "a 40 dB collapse below 400 Hz is still fully
    # visible in the 88-175 Hz bins". That is true OF THE BINS and false OF THE MEDIAN OVER THEM --
    # 8 bins in 100 cannot move it. A claim about what a band contains is not a claim about what a
    # statistic computed over it can see.
    # --- H4  the SUPERSEDED pooled statistic, kept as a labelled CONTROL ---------------------
    # ⭐⭐ THIS WAS THE SESSION-98 FINDING AND IT IS NOW THE CONTROL. `g_of` used to be
    # `median(gabs[G_BAND])`, and G_BAND's 100 bins are LINEARLY spaced from 87.9 to 1599.6 Hz:
    # 8 lie below 175 Hz and 92 above 533, so the median bin sits at 1019.5 Hz. That statistic is
    # a ~1 kHz reading wearing a broadband name and is structurally incapable of registering a
    # low-frequency collapse.
    # ⚠ The old comment beside G_BAND said "a 40 dB collapse below 400 Hz is still fully visible
    # in the 88-175 Hz bins". True OF THE BINS, false OF THE MEDIAN OVER THEM -- 8 bins in 100
    # cannot move it. A claim about what a band CONTAINS is not a claim about what a STATISTIC
    # computed over it can see. Printed every run so the two readings stay diff-able and so a
    # pre-session-99 quote can still be reproduced.
    print("\n  H4 CONTROL -- the SUPERSEDED pooled median, on the same renders:")
    pd = S._pooled_delta()
    h4 = {}
    print("     %-6s %11s %11s %11s" % ("throw", "asked +dB", "render got", "shortfall"))
    for p in S.POSITIONS:
        got = float(np.median(curves[p][S.G_BAND]))
        h4[p] = dict(asked=pd[p], got=got, shortfall=pd[p] - got)
        print("     %-6s %+11.2f %+11.2f %+11.2f" % (p, pd[p], got, pd[p] - got))
    pooled_worst = max(abs(v["shortfall"]) for v in h4.values())
    print("\n     the pooled median reports worst %.2f dB where the per-sub-band read reports"
          " %.2f dB." % (pooled_worst, worst3))
    print("     ⇒ %s" % ("the two agree; this candidate does not exercise the blind spot."
                         if worst3 < 2.0 * max(pooled_worst, 0.5) else
                         "THE POOLED MEDIAN HIDES IT -- satisfied at ~1 kHz while the low band is\n"
                         "       %.0f dB short. Same failure mode as session 94's ratio-only\n"
                         "       objective, one level down: a summary statistic that cannot see\n"
                         "       WHERE the damage is." % worst3))
    out = dict(fits_json=args.fits_json, worst=worst, invariant=bool(ok), throws=rows,
               partition=[list(s) for s in S.G_ACTIVE],
               h3={k: v for k, v in h3.items()}, h3_worst=worst3,
               h4_pooled=h4, h4_pooled_worst=pooled_worst,
               g_median_bin_hz=float(np.median(S.FBB[S.G_BAND])),
               ladder_distance=float(S.ladder_distance(cand)),
               ladder={e: cand[e] / S.PROP[e] for e in S.SHARED + list(S.TAP)})
    os.makedirs("analysis/reports", exist_ok=True)
    json.dump(out, open(args.json, "w"), indent=1, default=float)
    print("\n  wrote %s" % args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
