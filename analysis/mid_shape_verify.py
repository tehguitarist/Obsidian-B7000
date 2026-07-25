#!/usr/bin/env python3.11
"""A2c-2 acceptance — does the plugin's mid stage match the pedal's CURVE, not just
one point?

Matching a peak's height at one band proves very little: GAP #4 fitted the
boost-to-cut SPAN (a height metric) and landed LO-MID 250's peak depth and centre
band exactly on the pedal while its skirts were 4.33 octaves wide against the
pedal's 2.67.  So this checks three separate things at every switch position and
BOTH knob extremes:

  1. PEAK FREQUENCY, interpolated to sub-band resolution.  The 1/3-octave grid
     quantises a peak to +-1/6 octave, so "lands in the right band" is not the
     same claim as "peaks at the same frequency"; a parabolic fit through the
     peak band and its two neighbours (on the log-f axis) resolves it finer.
  2. PEAK GAIN and half-depth BANDWIDTH in octaves — height and width together.
  3. The WHOLE CURVE — band-RMS and worst single band across the stage's active
     range, plus the printed per-band table, so a good summary number cannot hide
     a bad shape.

Everything is measured on the stage's own contribution (capture minus the
all-flat `ref-clean`, differenced within one domain so the rest of the chain and
the report's per-capture gain match cancel), from REAL renders in the report —
not from the oracle.

Usage:
    python3.11 analysis/mid_shape_verify.py [report.json]
    python3.11 analysis/mid_shape_verify.py BEFORE.json AFTER.json   # A/B
    python3.11 analysis/mid_shape_verify.py report.json --curves     # per-band tables
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mid_shape_fit import BANDS, REPORT, load, stage_shape  # noqa: E402

EVAL_LO, EVAL_HI = 100.0, 4100.0
NORM_HZ = 5120.0


def anchored(bands, curve):
    return curve - curve[int(np.argmin(np.abs(bands - NORM_HZ)))]


def peak(bands, curve, m):
    """(gain dB, sub-band peak Hz, half-depth bandwidth in octaves).

    The peak frequency is refined by fitting a parabola to the peak band and its
    two neighbours in log2(f) — on a 1/3-octave grid the raw argmax is only
    accurate to +-1/6 octave, which is too coarse to claim two peaks coincide.
    """
    idx = np.arange(len(bands))[m]
    i = idx[int(np.argmax(np.abs(curve[m])))]
    fpk = bands[i]
    if 0 < i < len(bands) - 1:
        y0, y1, y2 = curve[i - 1], curve[i], curve[i + 1]
        den = y0 - 2 * y1 + y2
        if abs(den) > 1e-9:
            d = 0.5 * (y0 - y2) / den                      # in band steps
            if abs(d) <= 1.0:
                fpk = 2 ** (np.log2(bands[i]) + d * np.log2(bands[i + 1] / bands[i]))
    half = abs(curve[i]) / 2.0
    lo = hi = np.nan
    for j in range(i, 0, -1):
        if abs(curve[j]) <= half:
            lo = 2 ** np.interp(half, [abs(curve[j]), abs(curve[j + 1])],
                                [np.log2(bands[j]), np.log2(bands[j + 1])])
            break
    for j in range(i, len(bands)):
        if abs(curve[j]) <= half:
            hi = 2 ** np.interp(half, [abs(curve[j]), abs(curve[j - 1])],
                                [np.log2(bands[j]), np.log2(bands[j - 1])])
            break
    return curve[i], fpk, (np.log2(hi / lo) if lo == lo and hi == hi else np.nan)


def rows(path):
    bands, by_file = load(path)
    m = (bands >= EVAL_LO) & (bands <= EVAL_HI)
    out = []
    for band in ("LO-MID", "HI-MID"):
        _c32, positions = BANDS[band]
        for label, _c33, f_cut, f_bst in positions:
            for knob, fn in (("cut", f_cut), ("bst", f_bst)):
                ped = anchored(bands, stage_shape(bands, by_file, fn, "pedal_db"))
                plg = anchored(bands, stage_shape(bands, by_file, fn, "plugin_db"))
                d = plg[m] - ped[m]
                out.append(dict(
                    pos=f"{band} {label}", knob=knob, file=fn, bands=bands, m=m,
                    ped=ped, plg=plg,
                    ped_pk=peak(bands, ped, m), plg_pk=peak(bands, plg, m),
                    rms=float(np.sqrt(np.mean(d ** 2))),
                    worst=float(np.max(np.abs(d))),
                    worst_hz=float(bands[m][int(np.argmax(np.abs(d)))])))
    return out


def report(rs, label, prev=None):
    print(f"\n{'='*104}\n{label}\n{'='*104}")
    print(f"{'position':<15}{'knob':<5}| {'PEAK Hz':>19} {'err':>7} | {'PEAK dB':>15} {'err':>6}"
          f" | {'BW oct':>13} | {'curve':>13}")
    print(f"{'':<20}| {'pedal':>9}{'plugin':>10} {'%':>7} | {'pedal':>7}{'plugin':>8} {'dB':>6}"
          f" | {'pedal':>6}{'plugin':>7} | {'RMS':>6}{'worst':>7}")
    print("-" * 104)
    bad = []
    for i, r in enumerate(rs):
        (ppk, pf, pbw), (gpk, gf, gbw) = r["ped_pk"], r["plg_pk"]
        ferr = 100.0 * (gf / pf - 1.0)
        d = f"{prev[i]['rms']:.2f}->" if prev else ""
        print(f"{r['pos']:<15}{r['knob']:<5}| {pf:>9.0f}{gf:>10.0f} {ferr:>+6.1f}% |"
              f" {ppk:>7.1f}{gpk:>8.1f} {gpk-ppk:>+6.1f} | {pbw:>6.2f}{gbw:>7.2f} |"
              f" {d}{r['rms']:>5.2f}{r['worst']:>7.2f}")
        if abs(ferr) > 8.0:
            bad.append(f"{r['pos']} {r['knob']}: peak {ferr:+.1f}% off")
    v = [r["rms"] for r in rs]
    print(f"\n  mean curve RMS {np.mean(v):.3f} dB   worst position {max(v):.3f} dB"
          + (f"   (was {np.mean([p['rms'] for p in prev]):.3f} / "
             f"{max(p['rms'] for p in prev):.3f})" if prev else ""))
    pf_err = [abs(100.0 * (r["plg_pk"][1] / r["ped_pk"][1] - 1.0)) for r in rs]
    print(f"  peak-frequency error: mean {np.mean(pf_err):.1f}%  worst {max(pf_err):.1f}%"
          + (f"   (was {np.mean([abs(100.0*(p['plg_pk'][1]/p['ped_pk'][1]-1.0)) for p in prev]):.1f}% / "
             f"{max(abs(100.0*(p['plg_pk'][1]/p['ped_pk'][1]-1.0)) for p in prev):.1f}%)" if prev else ""))
    bw_err = [r["plg_pk"][2] / r["ped_pk"][2] for r in rs if r["ped_pk"][2] == r["ped_pk"][2]
              and r["plg_pk"][2] == r["plg_pk"][2]]
    if bw_err:
        print(f"  bandwidth ratio plugin/pedal: mean {np.mean(bw_err):.2f}x  worst {max(bw_err):.2f}x"
              "   (1.00 = same width; >1 = plugin too broad)")
    if bad:
        print("  ! peak frequency off by >8% (~1/4 octave): " + "; ".join(bad))


def curves(rs):
    for r in rs:
        b, m = r["bands"], r["m"]
        print(f"\n  {r['pos']} {r['knob']}   ({r['file']})")
        print("    " + "".join(f"{x:>7.0f}" for x in b[m]))
        print("ped " + "".join(f"{x:>7.1f}" for x in r["ped"][m]))
        print("plg " + "".join(f"{x:>7.1f}" for x in r["plg"][m]))
        print("  d " + "".join(f"{x:>7.1f}" for x in (r["plg"][m] - r["ped"][m])))


def main():
    paths = [a for a in sys.argv[1:] if not a.startswith("--")] or [REPORT]
    rs = [rows(p) for p in paths]
    if len(rs) == 1:
        report(rs[0], paths[0])
    else:
        report(rs[0], f"BEFORE — {paths[0]}")
        report(rs[1], f"AFTER — {paths[1]}", prev=rs[0])
    if "--curves" in sys.argv:
        curves(rs[-1])


if __name__ == "__main__":
    main()
