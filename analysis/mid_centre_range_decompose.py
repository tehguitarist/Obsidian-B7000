#!/usr/bin/env python3.11
"""A2c-2 — decompose each mid-band capture's residual into CENTRE vs RANGE error.

Why this exists: GAP #4 (session 22) fitted a wiper-leg series R (`midWiperRLo/Hi`)
to close the mid stage's boost-to-cut RANGE, and recorded TWO residuals it
knowingly accepted — (a) one resistor must serve all three switch positions of a
band, (b) Rw pulls each peak's CENTRE down (LO-MID 500 508->403 Hz, HI-MID 750
806->640 Hz). Every capture still failing A2c's target is a mid capture, so
before spending any fitting budget the question is WHICH of those two residuals
each failing capture actually is:

  * CENTRE error  -> the switched-cap table can fix it. That table is [ENG]-
    computed and never schematic-verified (circuit.md mid-band note), so there is
    no ground truth to defer to — the same posture that let LO-MID 250 move
    47n -> 22n in GAP #4.
  * RANGE error   -> already spent by GAP #4's deliberate one-resistor-per-band
    trade. Re-fitting it just reopens that trade; don't.

METHOD.  The stage's own contribution is isolated by differencing the capture
against the all-flat reference in the SAME domain (pedal-vs-pedal,
plugin-vs-plugin), then renormalising at 5.12 kHz where the mid stages do
nothing.  That kills the report's per-capture gain match and every other stage
in the chain, exactly like mid_range_probe.py's span.  Then the pedal's stage
shape is modelled as the plugin's, shifted s octaves and scaled by k:

    S_pedal(f)  ~=  k * S_plugin(f * 2**-s)

and the residual RMS is re-measured with (a) k free / s=0  = the best a pure
RANGE correction could do, (b) s free / k=1 = the best a pure CENTRE correction
could do, (c) both free.  The drop from the total tells you which term the
residual actually is; whatever survives (c) is reachable by neither.

Usage:
    python3.11 analysis/mid_centre_range_decompose.py [report.json]
"""
import json
import os
import sys

import numpy as np

REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "reports", "comprehensive_data.json")

SWEEP = "sweep_clean"
NORM_HZ = 5120.0
# Band the mid stages actually act in.  Below ~100 Hz the two captures approach
# the sweep/cab noise floor; above ~4.1 kHz the 5.12 kHz renormalisation anchor
# is too close to difference against.
EVAL_LO, EVAL_HI = 100.0, 4100.0

# capture -> (label, flat-mid reference capture)
REF_N12 = "ref-clean_gain-n12.wav"
REF = "ref-clean.wav"

CASES = [
    # (capture file, human label, nominal switched cap)
    ("lomidfreq-250_lomid-0700_base-clean.wav",          "LO-MID 250  cut ", 47.0e-9),
    ("lomidfreq-250_lomid-1700_gain-n12_base-clean.wav", "LO-MID 250  bst ", 47.0e-9),
    ("lomid-0700_base-clean.wav",                        "LO-MID 500  cut ", 10.0e-9),
    ("lomid-1700_gain-n12_base-clean.wav",               "LO-MID 500  bst ", 10.0e-9),
    ("lomidfreq-1k_lomid-0700_base-clean.wav",           "LO-MID 1k   cut ", 2.2e-9),
    ("lomidfreq-1k_lomid-1700_gain-n12_base-clean.wav",  "LO-MID 1k   bst ", 2.2e-9),
    ("himidfreq-750_himid-0700_base-clean.wav",          "HI-MID 750  cut ", 15.0e-9),
    ("himidfreq-750_himid-1700_gain-n12_base-clean.wav", "HI-MID 750  bst ", 15.0e-9),
    ("himid-0700_base-clean.wav",                        "HI-MID 1.5k cut ", 3.3e-9),
    ("himid-1700_gain-n12_base-clean.wav",               "HI-MID 1.5k bst ", 3.3e-9),
    ("himidfreq-3k_himid-0700_base-clean.wav",           "HI-MID 3k   cut ", 820.0e-12),
    ("himidfreq-3k_himid-1700_gain-n12_base-clean.wav",  "HI-MID 3k   bst ", 820.0e-12),
]


def load(path):
    with open(path) as fh:
        d = json.load(fh)
    return np.array(d["meta"]["bands"], float), {c["file"]: c for c in d["captures"]}


def stage_shape(bands, by_file, cap, ref, key):
    """The stage's own contribution, in dB, renormalised at NORM_HZ."""
    a = np.array(by_file[cap]["fr"][SWEEP][key], float)
    b = np.array(by_file[ref]["fr"][SWEEP][key], float)
    s = a - b
    return s - s[int(np.argmin(np.abs(bands - NORM_HZ)))]


def shift(bands, s_curve, s_oct):
    """Resample s_curve onto f * 2**-s_oct (log-frequency interpolation)."""
    if s_oct == 0.0:
        return s_curve
    lf = np.log2(bands)
    return np.interp(lf - s_oct, lf, s_curve)


def rms(v):
    return float(np.sqrt(np.mean(v ** 2)))


def decompose(bands, plug, ped, m):
    """-> (total, range-only, centre-only, joint, s*, k*) RMS dB over mask m."""
    total = rms(plug[m] - ped[m])

    # (a) RANGE only: s = 0, k free  (closed form least squares)
    k0 = float(np.dot(plug[m], ped[m]) / np.dot(plug[m], plug[m])) if np.any(plug[m]) else 1.0
    r_range = rms(k0 * plug[m] - ped[m])

    # (b) CENTRE only: k = 1, s scanned
    grid = np.arange(-1.2, 1.2001, 0.005)
    cs = [rms(shift(bands, plug, s)[m] - ped[m]) for s in grid]
    i = int(np.argmin(cs))
    r_centre, s_c = cs[i], float(grid[i])

    # (c) joint
    best = None
    for s in grid:
        ps = shift(bands, plug, s)[m]
        if not np.any(ps):
            continue
        k = float(np.dot(ps, ped[m]) / np.dot(ps, ps))
        e = rms(k * ps - ped[m])
        if best is None or e < best[0]:
            best = (e, float(s), k)
    return total, r_range, r_centre, best[0], best[1], best[2], k0, s_c


def peak(bands, curve, m):
    idx = np.arange(len(bands))[m][int(np.argmax(np.abs(curve[m])))]
    return curve[idx], bands[idx]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else REPORT
    bands, by_file = load(path)
    m = (bands >= EVAL_LO) & (bands <= EVAL_HI)

    print(f"report: {path}")
    print(f"\nMID STAGE CONTRIBUTION (capture minus flat-mid ref, renormalised at "
          f"{NORM_HZ:.0f} Hz)\nevaluated over {EVAL_LO:.0f} Hz - {EVAL_HI:.0f} Hz\n")
    print(f"{'position':<18}{'pedal pk':>10}{'@Hz':>7}{'plugin pk':>11}{'@Hz':>7}"
          f"{'ctr err':>9}{'rng err':>9}")
    print("-" * 71)
    shapes = {}
    for cap, label, c in CASES:
        if cap not in by_file:
            print(f"{label:<18}  MISSING {cap}")
            continue
        ref = REF_N12 if "gain-n12" in cap else REF
        ped = stage_shape(bands, by_file, cap, ref, "pedal_db")
        plg = stage_shape(bands, by_file, cap, ref, "plugin_db")
        shapes[label] = (plg, ped)
        pp, pf = peak(bands, ped, m)
        gp, gf = peak(bands, plg, m)
        print(f"{label:<18}{pp:>10.1f}{pf:>7.0f}{gp:>11.1f}{gf:>7.0f}"
              f"{np.log2(gf / pf):>+9.2f}{abs(gp) - abs(pp):>+9.1f}")
    print("  ctr err = plugin peak position re pedal, in OCTAVES (- = plugin too low)")
    print("  rng err = plugin |peak| minus pedal |peak|, dB (+ = plugin over-delivers)")

    print(f"\n\nRESIDUAL DECOMPOSITION — RMS dB of (plugin stage - pedal stage)\n")
    print(f"{'position':<18}{'total':>8}{'range-fit':>11}{'centre-fit':>12}"
          f"{'joint':>8}{'s* oct':>9}{'k*':>7}{'verdict':>26}")
    print("-" * 99)
    for cap, label, c in CASES:
        if label not in shapes:
            continue
        plg, ped = shapes[label]
        tot, rr, rc, rj, sj, kj, k0, sc = decompose(bands, plg, ped, m)
        # which single correction buys more of the residual?
        d_range, d_centre = tot - rr, tot - rc
        if tot < 0.6:
            v = "already good"
        elif d_centre > 1.6 * d_range:
            v = "CENTRE-dominated"
        elif d_range > 1.6 * d_centre:
            v = "RANGE-dominated"
        else:
            v = "mixed"
        if rj > 0.55 * tot:
            v += " +irreducible"
        print(f"{label:<18}{tot:>8.2f}{rr:>11.2f}{rc:>12.2f}{rj:>8.2f}"
              f"{sj:>+9.2f}{kj:>7.2f}   {v:<23}")
    print("\n  range-fit  = residual left if a pure RANGE correction were free (k fitted, s=0)")
    print("  centre-fit = residual left if a pure CENTRE correction were free (s fitted, k=1)")
    print("  joint      = residual left with BOTH free; what survives is reachable by neither")
    print("  s* > 0 means the plugin's peak must move UP in frequency to match the pedal")


if __name__ == "__main__":
    main()
