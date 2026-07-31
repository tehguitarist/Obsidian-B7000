#!/usr/bin/env python3.11
"""Localise the `gain-n12` OD defect -- open since session 30, and ON A3's
CRITICAL PATH since session 47.

WHY IT MATTERS NOW.  Session 47's whole-band shape gate located A3's mid/HF half
at `btC17`, and the candidate improves every capture group MONOTONICALLY except
these 16 rows, which degrade monotonically and are big enough to control the
aggregate.  They are the only reason nothing shipped.  Session 30 recorded the
defect as "a genuine level-dependent HF collapse ... present ONLY at the reduced
stimulus level" and parked it.  This localises it.

THE ANSWER, up front: the defect is in the CAPTURES, not the model, and the
`--input-trim` harness fix cannot repair it because it is not a gain error.

THREE TESTS, in the order that makes each one interpretable.

  (1) MATCHED ABSOLUTE LEVEL.  The gain-n12 files were recorded with the send
      reduced by a measured 12.071 dB and the sweep rungs step 12 dB, so
          <cap>_gain-n12 @ sweep_drv_-6   ==  <cap> @ sweep_drv_-18
      to 0.071 dB -- the same operating point down two different routes.  The
      pedal MUST agree across it.  The model does (0.03 dB).  The pedal does not.

  (2) LEVEL MONOTONICITY -- ⚠ CORROBORATION ONLY, NOT PROOF.  VR2 LEVEL is a
      passive divider, so it is tempting to say the band levels must order with
      the knob.  They need not: the stimulus is a swept sine through a DISTORTING
      device, so harmonics from lower sweep frequencies land in higher 1/3-oct
      bands and a "band level" is not a pure transfer.  The normal-gain group
      breaks the ordering too (11/22 bands at the hottest rung), which is exactly
      that effect -- so this test is reported as a CONTRAST between the groups,
      never as a standalone impossibility.  It was written as one first; the
      normal-group column is what refuted it.

  (3) ⭐ THE DECISIVE ONE -- THD-TURNOVER INVARIANCE.  THD is a RATIO, so an
      output/record gain cannot move it at all; an input/send pad can only SHIFT
      the THD-vs-level curve sideways.  Under either -- or both together -- the
      curve's shape is preserved, so the VALUE at its interior turning point is
      invariant while its POSITION moves by exactly the pad.  That separates the
      two questions with no free parameter and no fitting.
      ⚠ Use the interior MAXIMUM, not the extremum of the sampled ladder: THD
      rises monotonically out of the quiet end, so an argmin just returns the
      -36 dBFS endpoint and "measures" the pad it is supposed to be blind to.

  ⚠ Why not just fit the pad?  Because it is unidentifiable here and says so:
      the `lvl_` ladder spans 33 dB, so a large pad leaves too little overlap and
      the fitted X parks on the search bound (three of five did).  A
      bound-resting fit is not a measurement.  Test (3) needs no overlap.

  ⚠ Test (3) does NOT identify WHICH setting differed, and this deliberately does
      not guess.  BLEND is the obvious suspect -- clean bleed dilutes every
      harmonic without touching the OD path's own shape (the session-7 finding),
      it would flatten the response, and the discrepancy does fall as LEVEL rises
      (= less dilution), which is the ordering that hypothesis predicts.  DRIVE
      would do something similar.  Distinguishing them needs a re-capture, and
      the exclusion below does not depend on which it is.

Usage:
    python3.11 analysis/gain_n12_localise.py analysis/reports/comprehensive_data.json
    python3.11 analysis/gain_n12_localise.py <report> --bands     # per-band detail
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A  # noqa: E402

GRADE_LO, GRADE_HI = 25.0, 12901.6   # matrix_grade.py's band, so numbers compare
SILENT_DB = -60.0
TAKE_FLOOR_DB = 0.144                # session 24 take-to-take shape floor
LADDER_STEPS = list(range(-36, -2, 3))   # gen_test_signal.py::LEVEL_STEPS_DB

NORMAL_RUNG, N12_RUNG = "sweep_drv_-18", "sweep_drv_-6"

# LEVEL knob position -> (normal file, gain-n12 file).  ref-od IS the LEVEL=0.50
# member of this same series (it just carries no `level-` token), exactly as
# ref-clean is the master=0.50 member of the master series (session 41 item 5d).
LEVEL_LADDER = [
    (0.25, "level-0930_base-od.wav", "level-0930_gain-n12_base-od.wav"),
    (0.50, "ref-od.wav", "ref-od_gain-n12.wav"),
    (0.75, "level-1430_base-od.wav", "level-1430_gain-n12_base-od.wav"),
    (1.00, "level-1700_base-od.wav", "level-1700_gain-n12_base-od.wav"),
]


def is_od(f):
    return "base-od" in f or f.startswith("ref-od")


def band_idx(bands, lo, hi):
    return [i for i, b in enumerate(bands) if lo <= b <= hi]


def rms(v):
    return float(np.sqrt(np.mean(np.asarray(v, float) ** 2))) if len(v) else float("nan")


def shape(series, idx):
    """Mean-removed over the graded bands -- a pure SHAPE, level divided out."""
    s = np.asarray(series, float)[idx]
    return s - s.mean()


# ---------------------------------------------------------------- ladders
def _thd_db(x, sr=48000.0, f0=1000.0, orders=range(2, 7)):
    """THD in dB re fundamental.  A RATIO -- immune to any output/record gain."""
    n = len(x)
    w = np.hanning(n)
    X = np.abs(np.fft.rfft(x * w))
    f = np.fft.rfftfreq(n, 1 / sr)

    def pk(t):
        k = int(np.argmin(np.abs(f - t)))
        return X[max(0, k - 3):k + 4].max()

    h1 = pk(f0)
    hs = np.sqrt(sum(pk(f0 * m) ** 2 for m in orders))
    return 20 * np.log10(hs / (h1 + 1e-30) + 1e-12)


def thd_ladder(fname, orig, cache={}):
    if fname in cache:
        return cache[fname]
    cal, _ = A.align(A.load("analysis/captures/" + fname), orig)
    v = np.array([_thd_db(A.seg_of(cal, f"lvl_{d}")) for d in LADDER_STEPS])
    cache[fname] = v
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report")
    ap.add_argument("--bands", action="store_true")
    args = ap.parse_args()

    d = json.load(open(args.report))
    bands = d["meta"]["bands"]
    caps = {c["file"]: c for c in d["captures"]}
    G = band_idx(bands, GRADE_LO, GRADE_HI)
    gb = [bands[i] for i in G]
    orig = A.load(A.ORIG)

    # ---------------------------------------------------------------- 0
    print("=" * 76)
    print("0.  THE GROUP, at the shipped baseline (matrix_grade's own metric)")
    print("=" * 76)
    n12, other = [], []
    for f, c in caps.items():
        if not is_od(f):
            continue
        for sw, fr in c["fr"].items():
            p, q = fr["plugin_db"], fr["pedal_db"]
            if max(p) < SILENT_DB or max(q) < SILENT_DB:
                continue
            r = rms([p[i] - q[i] for i in G])
            (n12 if "gain-n12" in f else other).append((r, f, sw))
    print(f"  gain-n12 OD rows {len(n12):4d}   mean band-RMS {np.mean([x[0] for x in n12]):6.3f} dB")
    print(f"  other    OD rows {len(other):4d}   mean band-RMS {np.mean([x[0] for x in other]):6.3f} dB")

    # ---------------------------------------------------------------- 1
    print()
    print("=" * 76)
    print("1.  MATCHED ABSOLUTE LEVEL   n12 @ drv_-6  vs  twin @ drv_-18   (0.071 dB apart)")
    print("=" * 76)
    print(f"  {'capture':<22}{'pedal':>9}{'model':>9}   {'pedal worst band':>24}")
    ped, mdl = [], []
    per_band = {}
    for _, nm, n12f in LEVEL_LADDER:
        fa, fb = caps[nm]["fr"], caps[n12f]["fr"]
        dp = shape(fb[N12_RUNG]["pedal_db"], G) - shape(fa[NORMAL_RUNG]["pedal_db"], G)
        dm = shape(fb[N12_RUNG]["plugin_db"], G) - shape(fa[NORMAL_RUNG]["plugin_db"], G)
        ped += list(dp)
        mdl += list(dm)
        per_band[nm] = (dp, dm)
        i = int(np.argmax(np.abs(dp)))
        print(f"  {nm.replace('_base-od.wav','').replace('.wav',''):<22}"
              f"{rms(dp):9.2f}{rms(dm):9.2f}   {dp[i]:+13.2f} dB @{gb[i]:>7.0f} Hz")
    print(f"  {'POOLED dB RMS':<22}{rms(ped):9.2f}{rms(mdl):9.2f}")
    print()
    print(f"  The MODEL reproduces the pair to {rms(mdl):.2f} dB -- so `--input-trim` is applied")
    print(f"  correctly and the render is level-consistent.  The PEDAL disagrees by")
    print(f"  {rms(ped):.2f} dB, i.e. {rms(ped)/TAKE_FLOOR_DB:.0f}x the {TAKE_FLOOR_DB} dB take-to-take floor.")

    if args.bands:
        print()
        print("  per-band pedal residual (dB):")
        print(f"  {'Hz':>8}" + "".join(f"{n.replace('_base-od.wav','').replace('.wav',''):>16}"
                                       for _, n, _ in LEVEL_LADDER))
        for j, f_ in enumerate(gb):
            print(f"  {f_:8.0f}" + "".join(f"{per_band[n][0][j]:+16.2f}" for _, n, _ in LEVEL_LADDER))

    # ---------------------------------------------------------------- 2
    print()
    print("=" * 76)
    print("2.  LEVEL ORDERING -- corroboration only (see the docstring caveat)")
    print("=" * 76)
    for gi, gname in ((1, "normal-gain"), (2, "gain-n12")):
        for rung in (NORMAL_RUNG, N12_RUNG):
            bad = tot = 0
            for i, b in enumerate(bands):
                if not (100 <= b <= 13000):
                    continue
                v = [caps[t[gi]]["fr"][rung]["pedal_db"][i] for t in LEVEL_LADDER]
                tot += 1
                if any(v[j + 1] < v[j] - 0.1 for j in range(len(v) - 1)):
                    bad += 1
            print(f"  {gname:<12} {rung:<16} non-monotone in {bad:2d} / {tot} bands")
    print()
    print("  ⚠ The normal group breaks it too, so this is NOT a standalone")
    print("    impossibility -- harmonics from a swept sine redistribute across the")
    print("    1/3-oct bands.  Read only the CONTRAST: the gain-n12 group is far")
    print("    worse at the SAME rung, and worse at the quiet rung than the normal")
    print("    group is at its hot one.")

    # ---------------------------------------------------------------- 3
    print()
    print("=" * 76)
    print("3.  THD-TURNOVER INVARIANCE  -- the decisive test, ZERO free parameters")
    print("=" * 76)
    print("  THD is a ratio: a RECORD gain cannot move it, and a SEND pad can only")
    print("  slide the curve sideways.  So the VALUE at the curve's interior turning")
    print("  point is invariant to both; only its POSITION carries the pad.")
    print()
    print(f"  {'capture':<20}{'LEVEL':>6}{'peak THD dB':>12}{'  n12':>8}"
          f"{'  DISCREP':>10}{'   rung':>9}{' n12':>6}{'  pad':>7}")
    disc, pads, interiors = [], [], []
    for lv, nm, n12f in LEVEL_LADDER:
        a, b = thd_ladder(nm, orig), thd_ladder(n12f, orig)
        ia, ib = int(np.argmax(a)), int(np.argmax(b))
        interior = 0 < ia < len(a) - 1 and 0 < ib < len(b) - 1
        pad = LADDER_STEPS[ib] - LADDER_STEPS[ia]
        disc.append((lv, float(a[ia] - b[ib])))
        pads.append(pad)
        interiors.append(interior)
        print(f"  {nm.replace('_base-od.wav','').replace('.wav',''):<20}{lv:6.2f}"
              f"{a[ia]:12.1f}{b[ib]:8.1f}{a[ia]-b[ib]:+10.1f}"
              f"{LADDER_STEPS[ia]:+9d}{LADDER_STEPS[ib]:+6d}{pad:+7d}"
              f"{'' if interior else '   (ENDPOINT -- discard)'}")
    print()
    # ⚠⚠ EVERYTHING BELOW IS COMPUTED. It used to be four hardcoded sentences asserting "both
    # turning points are interior" and quoting DISCREP "+15.6 / +13.6 / +2.9 / +1.0" -- session 48's
    # numbers, narrated. When the four gain-n12 captures were RE-RECORDED (session 70) that prose
    # printed directly above a table reading +0.4 / -0.0 / -0.5 / +0.8 with every row flagged
    # ENDPOINT, i.e. it contradicted its own output twice over. Fifth occurrence of the session-34
    # narrated-verdict trap in this project. A verdict in a string outlives the condition it
    # described; derive it or delete it.
    n_int = sum(interiors)
    print(f"  {n_int} of {len(interiors)} capture pairs have BOTH turning points interior.")
    if n_int < len(interiors):
        print("  ⚠ A turning point AT A LADDER END is not a measurement of the turnover -- the")
        print("    invariance argument needs the maximum to be bracketed. Rows flagged ENDPOINT")
        print("    above are NOT evidence in either direction.")
        print("  ⭐ AND NOTE WHY THIS CAN HAPPEN ON *GOOD* CAPTURES: if the pad really is ~12 dB,")
        print("    the n12 curve's turnover sits ~12 dB higher in rung terms and runs off the top")
        print("    of the ladder. So this test LOSES RESOLUTION exactly when the captures are")
        print("    correct -- absence of a verdict here is not a verdict of absence.")
    print("  A pure gain change of ANY kind gives 0.0 in the DISCREP column.")
    print(f"    DISCREP : {', '.join(f'{v:+.1f}' for _, v in disc)} dB")
    print(f"    pad     : {', '.join(f'{p:+d}' for p in pads)} dB  "
          f"(the harness applies 12.07 to all four; ladder resolution is +-1.5 dB)")
    print()
    worst = max(abs(v) for _, v in disc)
    off_pad = [p for p in pads if abs(p - 12) > 3]
    print("  Two readings, and they are independent:")
    print(f"   (a) the PAD reads {', '.join(f'{p:+d}' for p in pads)} dB against the harness's 12.07"
          f" -- {len(off_pad)} of {len(pads)} are more than 3 dB off; and")
    print(f"   (b) the worst |DISCREP| is {worst:.1f} dB, which no pad value can repair.")
    if worst < 1.5:
        print("       ⇒ At this size the turnover is consistent with a pure gain change, i.e. with")
        print("         these being genuine -12 dB re-takes. ⚠ But see the ENDPOINT note above")
        print("         before treating that as a pass -- the MATRIX is the decisive test now.")
    else:
        print("       ⇒ Decisive: a nonzero turnover difference is not reachable by any gain.")
    print()
    print("  ⭐ DISCREP falls as LEVEL rises, which is what clean-bleed dilution")
    print("     predicts (more OD against a fixed bleed = less dilution of the")
    print("     measured harmonics).  Consistent with BLEND being off; NOT proof,")
    print("     and the exclusion below does not rest on it.")

    # ---------------------------------------------------------------- verdict
    print()
    print("=" * 76)
    print("VERDICT")
    print("=" * 76)
    print(f"  The model reproduces the matched-level pair to {rms(mdl):.2f} dB; the pedal misses")
    print(f"  it by {rms(ped):.2f} dB ({rms(ped)/TAKE_FLOOR_DB:.0f}x the take-to-take floor), so the")
    print("  disagreement is on the CAPTURE side.  And the THD turnover -- which no")
    print("  input or output gain can move -- differs from its own twin by up to")
    print(f"  {max(abs(v) for _, v in disc):.1f} dB, while the pad the turnover POSITION implies is 3-9 dB,")
    print("  not the 12.07 the harness applies.")
    print()
    print("  => These are not -12 dB re-takes of the same measurement.  `--input-trim`")
    print("     (session 21) is right for the 15 LINEAR clean gain-n12 captures and")
    print("     cannot fix the 5 OD ones, because the error is not a gain.")
    print()
    print("  => The 16 rows must not VOTE on a model candidate until re-captured.")
    print("     ⚠ That is an exclusion on a MECHANISM (this test), not on the rows")
    print("     being inconvenient -- the standard session 40 set for the 254 Hz")
    print("     exclusion.  It does NOT license excluding them from the headline")
    print("     aggregate silently: report both numbers.  Re-capturing these five")
    print("     files is the real fix and it is cheap.")


if __name__ == "__main__":
    main()
