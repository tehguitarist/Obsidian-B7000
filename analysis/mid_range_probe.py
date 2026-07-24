#!/usr/bin/env python3.11
"""GAP #4 — measure the mid stage's boost-to-cut SPAN, pedal vs plugin vs oracle.

The span (full-boost dB − full-cut dB, per 1/3-oct band) is a MATCHED-PAIR
differential (dsp.md "Isolate a coupled control with a MATCHED-PAIR capture"):
every other stage in the chain is identical in the two captures, so it cancels
EXACTLY and what remains is 2× the mid stage's own range. That makes it immune
to the report's per-capture gain-match, to the rest of the EQ voicing, and to
the clean/OD balance — the cleanest possible target for a range fit.

Usage:
    python3.11 analysis/mid_range_probe.py [report.json]
    python3.11 analysis/mid_range_probe.py --scan-rw          # oracle Rw scan
"""
import json
import sys
import os

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eq_reference import mid_stage_tf  # noqa: E402

REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "reports", "comprehensive_data.json")

# position -> (series cap, across-lug cap, boost-capture, cut-capture)
# The two captures differ in the mid GAIN knob only (0700 = one extreme,
# 1700 = the other); which one is boost is determined from the data.
POSITIONS = [
    ("LO-MID 250Hz  (C33=47n)", 47.0e-9, 22.0e-9,
     "lomidfreq-250_lomid-0700_base-clean.wav",
     "lomidfreq-250_lomid-1700_gain-n12_base-clean.wav"),
    ("LO-MID 500Hz  (C33=10n)", 10.0e-9, 22.0e-9,
     "lomid-0700_base-clean.wav",
     "lomid-1700_gain-n12_base-clean.wav"),
    ("LO-MID 1kHz   (C33=2n2)", 2.2e-9, 22.0e-9,
     "lomidfreq-1k_lomid-0700_base-clean.wav",
     "lomidfreq-1k_lomid-1700_gain-n12_base-clean.wav"),
    ("HI-MID 750Hz  (C35=15n)", 15.0e-9, 6.8e-9,
     "himidfreq-750_himid-0700_base-clean.wav",
     "himidfreq-750_himid-1700_gain-n12_base-clean.wav"),
    ("HI-MID 1.5kHz (C35=3n3)", 3.3e-9, 6.8e-9,
     "himid-0700_base-clean.wav",
     "himid-1700_gain-n12_base-clean.wav"),
    ("HI-MID 3kHz   (C35=820p)", 820.0e-12, 6.8e-9,
     "himidfreq-3k_himid-0700_base-clean.wav",
     "himidfreq-3k_himid-1700_gain-n12_base-clean.wav"),
]

SWEEP = "sweep_clean"


def load(report_path):
    with open(report_path) as fh:
        d = json.load(fh)
    bands = np.array(d["meta"]["bands"], float)
    by_file = {c["file"]: c for c in d["captures"]}
    return bands, by_file


def span(by_file, lo_file, hi_file, key):
    """hi-knob curve minus lo-knob curve, per band, for 'plugin_db' or 'pedal_db'."""
    a = np.array(by_file[lo_file]["fr"][SWEEP][key], float)
    b = np.array(by_file[hi_file]["fr"][SWEEP][key], float)
    return b - a


def oracle_span(bands, c_series, c32, rw=0.0, r38=2.2e3, r39=2.2e3,
                r40=220e3, r41=220e3, a_boost=1e-6, a_cut=1.0 - 1e-6):
    """Oracle boost-to-cut span. rw = series R in the wiper/cap leg (0 = shipped)."""
    kw = dict(C33=c_series, C32=c32, R38=r38, R39=r39, R40=r40, R41=r41, Rw=rw)
    hb = mid_stage_tf(bands, a_boost, **kw)
    hc = mid_stage_tf(bands, a_cut, **kw)
    return 20 * np.log10(np.abs(hb)) - 20 * np.log10(np.abs(hc))


def summarise(bands, sp, label):
    """Peak span + its band, plus the value renormalised to the 5.1 kHz band."""
    i5k = int(np.argmin(np.abs(bands - 5120.0)))
    sp = sp - sp[i5k]
    # Search 160 Hz .. 4.1 kHz — the band the mid stages actually act in. Below
    # ~160 Hz the two captures sit near the sweep/noise floor and their difference
    # is meaningless (an apparent −20 dB "peak" at 25 Hz is that artefact, not the
    # stage); above ~4 kHz the 5.1 kHz renormalisation reference is too close.
    m = (bands >= 160.0) & (bands <= 4100.0)
    idx = np.arange(len(bands))[m][int(np.argmax(np.abs(sp[m])))]
    return sp, sp[idx], bands[idx], label


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    report_path = args[0] if args else REPORT
    bands, by_file = load(report_path)

    scan_rw = "--scan-rw" in sys.argv

    print(f"report: {report_path}")
    print(f"\nBOOST-TO-CUT SPAN (dB, renormalised at 5120 Hz) — full pot travel.")
    print(f"The stage's ±range is half the span.\n")
    print(f"{'position':<26} {'pedal span':>11} {'@Hz':>7} "
          f"{'plugin span':>12} {'@Hz':>7} {'oracle Rw=0':>12} {'excess':>8}")
    print("-" * 92)

    rows = []
    for label, c33, c32, f_lo, f_hi in POSITIONS:
        missing = [f for f in (f_lo, f_hi) if f not in by_file]
        if missing:
            print(f"{label:<26}  MISSING: {missing}")
            continue
        ped_raw = span(by_file, f_lo, f_hi, "pedal_db")
        plg_raw = span(by_file, f_lo, f_hi, "plugin_db")
        orc_raw = oracle_span(bands, c33, c32, rw=0.0)

        ped, pp, pf, _ = summarise(bands, ped_raw, label)
        plg, gp, gf, _ = summarise(bands, plg_raw, label)
        orc, op, of_, _ = summarise(bands, orc_raw, label)
        rows.append((label, c33, c32, bands, ped, plg, orc, pp, pf, gp, gf, op, of_))
        print(f"{label:<26} {pp:>10.1f} {pf:>7.0f} {gp:>11.1f} {gf:>7.0f} "
              f"{op:>11.1f} {abs(gp) - abs(pp):>7.1f}")

    if scan_rw:
        print("\n\nORACLE SCAN — series R in the wiper/cap leg (Rw), effect on span + centre")
        print(f"{'Rw':>9} " + " ".join(f"{lab.split()[0]+lab.split()[1]:>14}" for lab, *_ in POSITIONS))
        for rw in [0, 2.2e3, 4.7e3, 10e3, 22e3, 33e3, 47e3, 68e3, 100e3, 150e3, 220e3]:
            cells = []
            for label, c33, c32, f_lo, f_hi in POSITIONS:
                sp = oracle_span(bands, c33, c32, rw=rw)
                sp, pk, fq, _ = summarise(bands, sp, label)
                cells.append(f"{pk:>7.1f}@{fq:>5.0f}")
            print(f"{rw/1e3:>8.1f}k " + " ".join(f"{c:>14}" for c in cells))

    return rows


if __name__ == "__main__":
    main()


# =============================================================================
# Candidate fit — which SHARED element reproduces the pedal's span at all six
# positions at once? Objective = RMS over the 6 positions x bands 160Hz-4.1kHz
# of (oracle span - pedal span), both renormalised at 5.12 kHz.
# Every parameter is SHARED across all six positions (a per-position fudge would
# be meaningless); the cap table stays at its [ENG] values unless stated.
# =============================================================================
FIT_LO, FIT_HI = 160.0, 4100.0


def _targets(bands, by_file):
    out = []
    for label, c33, c32, f_lo, f_hi in POSITIONS:
        if f_lo not in by_file or f_hi not in by_file:
            continue
        sp, _, _, _ = summarise(bands, span(by_file, f_lo, f_hi, "pedal_db"), label)
        out.append((label, c33, c32, sp))
    return out


def _cost(bands, targets, **kw):
    m = (bands >= FIT_LO) & (bands <= FIT_HI)
    errs = []
    for label, c33, c32, ped in targets:
        c32s = c32 * kw.pop("_c32scale", 1.0) if False else c32 * kw.get("c32scale", 1.0)
        sp = oracle_span(bands, c33 * kw.get("c33scale", 1.0), c32s,
                         rw=kw.get("rw", 0.0),
                         r38=2.2e3 * kw.get("rend", 1.0), r39=2.2e3 * kw.get("rend", 1.0),
                         r40=220e3 * kw.get("rflat", 1.0), r41=220e3 * kw.get("rflat", 1.0))
        sp, _, _, _ = summarise(bands, sp, label)
        errs.append(sp[m] - ped[m])
    e = np.concatenate(errs)
    return float(np.sqrt(np.mean(e ** 2)))


def fit_report():
    bands, by_file = load(REPORT)
    targets = _targets(bands, by_file)
    print("\n\nCANDIDATE FIT — RMS span error (dB) over 6 positions x 160Hz-4.1kHz")
    print(f"  shipped (all nominal): {_cost(bands, targets):.2f}\n")

    def scan(name, key, values, **fixed):
        best = None
        print(f"  {name}:")
        for v in values:
            kw = dict(fixed); kw[key] = v
            c = _cost(bands, targets, **kw)
            flag = ""
            if best is None or c < best[1]:
                best = (v, c); flag = " <-"
            print(f"    {key}={v:<10.4g}  RMS {c:6.2f}{flag}")
        return best

    scan("A. wiper-leg series R (Rw)", "rw",
         [0, 4.7e3, 10e3, 22e3, 33e3, 47e3, 68e3, 100e3, 150e3])
    scan("B. R38/R39 end resistors (x nominal 2k2)", "rend",
         [1, 2, 3, 5, 8, 12, 20, 32, 50])
    scan("C. R40/R41 flat legs (x nominal 220k)", "rflat",
         [1, 0.7, 0.5, 0.35, 0.25, 0.18, 0.12, 0.08])
    scan("D. C32/C34 across-lug caps (x nominal)", "c32scale",
         [1, 1.5, 2, 3, 5, 8, 12, 20])
    scan("E. switched-cap table (x nominal, all six)", "c33scale",
         [1, 0.7, 0.5, 0.35, 0.25, 0.15, 0.1])


if __name__ == "__main__" and "--fit" in sys.argv:
    fit_report()
