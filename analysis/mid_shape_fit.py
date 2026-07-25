#!/usr/bin/env python3.11
"""A2c-2 — fit the mid stage against the pedal's measured SHAPE (not just its span).

GAP #4 (session 22) fitted `midWiperR` against the boost-to-cut SPAN, which is
dominated by the peak's HEIGHT.  A2c's decomposition (mid_centre_range_decompose.py)
shows the surviving residual is neither centre nor range but WIDTH: at LO-MID 250
the plugin now matches the pedal's peak depth and centre EXACTLY (-14.0 dB @ 320 Hz
both) and still carries 3.4 dB RMS, because its skirts are ~1.7x too wide in
octaves.  A series R in the wiper leg is precisely the element that buys range by
damping, i.e. it pays for height with width — oracle BW 3.44 -> 5.29 octaves.

So this fits the whole CURVE (per band, both knob extremes, all six switch
positions at once), which constrains height, centre AND width together, over a
physically-meaningful shared parameter set.  Per-position fudges are excluded by
construction: every parameter is shared across a band's three switch positions,
exactly as in GAP #4.

Usage:
    python3.11 analysis/mid_shape_fit.py [report.json]
    python3.11 analysis/mid_shape_fit.py --scan     # 1-D diagnostic scans only
"""
import contextlib
import io
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):   # eq_reference prints a report on import
    from eq_reference import mid_stage_tf         # noqa: E402

REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "reports", "comprehensive_data.json")
SWEEP = "sweep_clean"
NORM_HZ = 5120.0
FIT_LO, FIT_HI = 100.0, 4100.0
REF, REF_N12 = "ref-clean.wav", "ref-clean_gain-n12.wav"

# band -> [(label, nominal switched cap, cut capture, boost capture)]
BANDS = {
    "LO-MID": (22.0e-9, [   # across-lug cap C32 = 22n (schematic-verified)
        ("250",  47.0e-9, "lomidfreq-250_lomid-0700_base-clean.wav",
                          "lomidfreq-250_lomid-1700_gain-n12_base-clean.wav"),
        ("500",  10.0e-9, "lomid-0700_base-clean.wav",
                          "lomid-1700_gain-n12_base-clean.wav"),
        ("1k",    2.2e-9, "lomidfreq-1k_lomid-0700_base-clean.wav",
                          "lomidfreq-1k_lomid-1700_gain-n12_base-clean.wav"),
    ]),
    "HI-MID": (6.8e-9, [    # across-lug cap C34 = 6n8 (schematic-verified)
        ("750",  15.0e-9, "himidfreq-750_himid-0700_base-clean.wav",
                          "himidfreq-750_himid-1700_gain-n12_base-clean.wav"),
        ("1.5k",  3.3e-9, "himid-0700_base-clean.wav",
                          "himid-1700_gain-n12_base-clean.wav"),
        ("3k",   0.82e-9, "himidfreq-3k_himid-0700_base-clean.wav",
                          "himidfreq-3k_himid-1700_gain-n12_base-clean.wav"),
    ]),
}

# Shipped fitted values (GAP #4, session 22)
SHIPPED = {"LO-MID": dict(rw=33e3, c33=[22.0e-9, 10.0e-9, 2.2e-9]),
           "HI-MID": dict(rw=22e3, c33=[15.0e-9, 3.3e-9, 0.82e-9])}


def load(path):
    with open(path) as fh:
        d = json.load(fh)
    return np.array(d["meta"]["bands"], float), {c["file"]: c for c in d["captures"]}


def stage_shape(bands, by_file, cap, key):
    ref = REF_N12 if "gain-n12" in cap else REF
    s = (np.array(by_file[cap]["fr"][SWEEP][key], float)
         - np.array(by_file[ref]["fr"][SWEEP][key], float))
    return s - s[int(np.argmin(np.abs(bands - NORM_HZ)))]


def oracle(bands, a, c33, c32, **kw):
    h = 20 * np.log10(np.abs(mid_stage_tf(bands, a, C33=c33, C32=c32, **kw)))
    return h - h[int(np.argmin(np.abs(bands - NORM_HZ)))]


def targets(bands, by_file, band):
    c32nom, positions = BANDS[band]
    out = []
    for label, c33nom, f_cut, f_bst in positions:
        if f_cut not in by_file or f_bst not in by_file:
            continue
        out.append((label, c33nom,
                    stage_shape(bands, by_file, f_cut, "pedal_db"),
                    stage_shape(bands, by_file, f_bst, "pedal_db")))
    return c32nom, out


def cost(bands, c32nom, tgts, m, c32scale=1.0, c33scale=1.0, rw=0.0,
         rend=1.0, rflat=1.0, rp=1.0, per_pos=None, detail=False):
    """RMS dB over all positions x both knob extremes."""
    kw = dict(R38=2.2e3 * rend, R39=2.2e3 * rend,
              R40=220e3 * rflat, R41=220e3 * rflat, Rp=100e3 * rp, Rw=rw)
    errs, rows = [], []
    for i, (label, c33nom, ped_cut, ped_bst) in enumerate(tgts):
        c33 = (per_pos[i] if per_pos else c33nom * c33scale)
        c32 = c32nom * c32scale
        # a -> 0 is one extreme, a -> 1 the other; match each to the pedal by sign.
        lo = oracle(bands, 1e-6, c33, c32, **kw)
        hi = oracle(bands, 1 - 1e-6, c33, c32, **kw)
        cut, bst = (lo, hi) if np.sum(lo[m]) < np.sum(hi[m]) else (hi, lo)
        e = np.concatenate([cut[m] - ped_cut[m], bst[m] - ped_bst[m]])
        errs.append(e)
        rows.append((label, c33, float(np.sqrt(np.mean(e ** 2)))))
    e = np.concatenate(errs)
    return (float(np.sqrt(np.mean(e ** 2))), rows) if detail else float(np.sqrt(np.mean(e ** 2)))


def metrics(bands, curve, m):
    idx = np.arange(len(bands))[m]
    i = idx[int(np.argmax(np.abs(curve[m])))]
    pk, fc = curve[i], bands[i]
    half = abs(pk) / 2.0
    lo = hi = np.nan
    for j in range(i, 0, -1):
        if abs(curve[j]) <= half:
            lo = bands[j]; break
    for j in range(i, len(bands)):
        if abs(curve[j]) <= half:
            hi = bands[j]; break
    return pk, fc, (np.log2(hi / lo) if lo == lo and hi == hi else np.nan)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = args[0] if args else REPORT
    bands, by_file = load(path)
    m = (bands >= FIT_LO) & (bands <= FIT_HI)

    print(f"report: {path}")
    for band in ("LO-MID", "HI-MID"):
        c32nom, tgts = targets(bands, by_file, band)
        sh = SHIPPED[band]
        print(f"\n\n{'='*86}\n{band}   (across-lug cap nominal {c32nom*1e9:g} nF)\n{'='*86}")

        # --- measured pedal shape vs shipped model, per position -----------
        print(f"\n  measured shape:  {'pos':<6}{'pedal pk':>9}{'@Hz':>7}{'BW oct':>8}"
              f"{'   |':>4}{'model pk':>9}{'@Hz':>7}{'BW oct':>8}")
        for i, (label, c33nom, ped_cut, ped_bst) in enumerate(tgts):
            pk, fc, bw = metrics(bands, ped_cut, m)
            mc = oracle(bands, 1e-6, sh["c33"][i], c32nom, Rw=sh["rw"])
            mc2 = oracle(bands, 1 - 1e-6, sh["c33"][i], c32nom, Rw=sh["rw"])
            mm = mc if np.sum(mc[m]) < np.sum(mc2[m]) else mc2
            mpk, mfc, mbw = metrics(bands, mm, m)
            print(f"{'':19}{label:<6}{pk:>9.1f}{fc:>7.0f}{bw:>8.2f}{'   |':>4}"
                  f"{mpk:>9.1f}{mfc:>7.0f}{mbw:>8.2f}")

        ship = cost(bands, c32nom, tgts, m, rw=sh["rw"], per_pos=sh["c33"])
        nom = cost(bands, c32nom, tgts, m)
        print(f"\n  RMS shape error vs pedal:   nominal (Rw=0) {nom:6.2f} dB"
              f"    SHIPPED (GAP #4) {ship:6.2f} dB")

        # --- 1-D scans -----------------------------------------------------
        def scan(name, **grid):
            key, vals = next(iter(grid.items()))
            best = None
            line = []
            for v in vals:
                c = cost(bands, c32nom, tgts, m, **{key: v})
                line.append(f"{v:g}:{c:.2f}")
                if best is None or c < best[1]:
                    best = (v, c)
            print(f"    {name:<34} best {key}={best[0]:<9.4g} RMS {best[1]:5.2f}   "
                  + " ".join(line[:9]))

        print("\n  1-D scans (each alone, from nominal):")
        scan("A wiper-leg R (the GAP #4 lever)", rw=[0, 4.7e3, 10e3, 22e3, 33e3, 47e3, 68e3, 100e3])
        scan("B across-lug cap x", c32scale=[1, 1.5, 2, 3, 4, 6, 8, 12])
        scan("C switched cap table x", c33scale=[1, 0.7, 0.5, 0.35, 0.25, 0.15, 0.1])
        scan("D end resistors R38/R39 x", rend=[1, 2, 3, 5, 8, 12, 20, 32])
        scan("E flat legs R40/R41 x", rflat=[1, 0.7, 0.5, 0.35, 0.25, 0.15, 0.1])
        scan("F pot value x", rp=[1, 1.5, 2, 3, 5, 8, 0.7, 0.5])

        # --- joint (c32scale, c33scale) grid, Rw = 0 -----------------------
        print("\n  2-D joint: across-lug cap x  vs  switched-cap table x   (Rw = 0)")
        c32g = [1, 1.5, 2, 3, 4, 6, 8]
        c33g = [1, 0.7, 0.5, 0.35, 0.25, 0.18, 0.12]
        print("        c33x " + "".join(f"{v:>7g}" for v in c33g))
        best = None
        for a in c32g:
            cells = []
            for b in c33g:
                c = cost(bands, c32nom, tgts, m, c32scale=a, c33scale=b)
                cells.append(c)
                if best is None or c < best[0]:
                    best = (c, a, b)
            print(f"  c32x {a:>5g} " + "".join(f"{v:>7.2f}" for v in cells))
        print(f"    -> best  c32x={best[1]:g}  c33x={best[2]:g}   RMS {best[0]:.2f} dB")

    print("\n(RMS is over 100 Hz-4.1 kHz, both knob extremes, all three switch positions,")
    print(" every parameter SHARED across a band's positions — no per-position fudge.)")


if __name__ == "__main__":
    main()
