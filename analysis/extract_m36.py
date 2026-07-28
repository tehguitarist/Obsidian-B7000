#!/usr/bin/env python3.11
"""Extract the -36 dBFS clean sweep as a 5th stimulus level (session 60).

WHY THIS EXISTS
---------------
`gen_test_signal.py` writes TWO clean-end sweeps -- `sweep_clean` at -30 dBFS and
`sweep_clean_-36` at -36 -- but `comprehensive_report.py` analyses only four levels
(`ALL_SWEEP_LEVELS = ("sweep_clean",) + DRIVEN_SWEEPS`), so the -36 point has been sitting
unread in EVERY capture in the matrix since the first capture session.

It matters here because session 60's h(f) still moves with stimulus level at 508 and 640 Hz
after de-convolution, and the only way to tell "converged to the linear limit" from "still
compressing" is another, quieter point. -36 dBFS is 6 dB below the quietest level the report
has ever looked at.

⚠ DELIBERATELY NOT A CHANGE TO `comprehensive_report.py`. That file is a shared oracle with
seven-plus importers, and adding a sweep to `ALL_SWEEP_LEVELS` would change the shape of every
report record and silently re-key the result cache. This tool writes a SEPARATE small JSON and
leaves the matrix alone.

PEDAL SIDE ONLY -- no rendering, so no OfflineRender dependency and no model staleness risk.
`pedal_db` comes entirely from the capture.

CONVENTION -- and why it does not matter which one is used
----------------------------------------------------------
`comprehensive_report.fr_at_bands` deconvolves EVERY sweep against the `sweep_clean` (-30 dBFS)
input segment, so its `pedal_db` at level L carries a constant (L + 30) dB offset. This tool
deconvolves the -36 sweep against its OWN input segment, so it carries no offset. Both are fine
here because every quantity built from these numbers is a DIFFERENCE of two captures at the SAME
level (throw minus flat, or flat minus pure-clean), and a common constant cancels exactly. The
self-test below asserts that equivalence rather than asserting it in a comment.

Usage:  python3.11 analysis/extract_m36.py [--selftest]
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A                                # noqa: E402

OUT = "analysis/reports/s60_m36.json"
SEG = "sweep_clean_-36"
FILES = [
    "blend-0700_base-od.wav",
    "drive-0700_level-1700_base-od.wav",
    "drive-0700_level-1700_attack-boost_base-od.wav",
    "drive-0700_level-1700_attack-cut_base-od.wav",
    "drive-0700_level-1700_grunt-flat_base-od.wav",
    "drive-0700_level-1700_grunt-boost_base-od.wav",
]
CAPDIR = "analysis/captures"


def band_db(cap_al, orig, seg, bands):
    inp = A.seg_of(orig, seg)
    out = A.seg_of(cap_al, seg)
    f, H = A.transfer(out, inp)
    return [float(np.interp(b, f, H)) for b in bands]


def selftest(orig, bands):
    """The convention claim, tested rather than asserted: for a fixed sweep, changing which input
    segment it is deconvolved against shifts every band by ONE constant, so any difference of two
    captures at that level is unchanged."""
    print("=" * 92)
    print("SELF-TEST -- the reference-segment convention cancels in a difference")
    print("=" * 92)
    cap = A.load(os.path.join(CAPDIR, FILES[1]))
    cap_al, _ = A.align(cap, orig)
    own = np.array(band_db(cap_al, orig, SEG, bands))
    f, H = A.transfer(A.seg_of(cap_al, SEG), A.seg_of(orig, "sweep_clean"))
    alt = np.array([float(np.interp(b, f, H)) for b in bands])
    d = own - alt
    spread = float(np.nanmax(d) - np.nanmin(d))
    print("  offset between the two conventions : mean %+.3f dB, spread %.3e dB   %s"
          % (float(np.nanmean(d)), spread, "PASS" if spread < 1e-6 else "FAIL"))
    print("  (a constant offset ⇒ cancels in throw-minus-flat and flat-minus-clean)")
    return spread < 1e-6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--report", default="analysis/reports/s60_matrix104.json")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    bands = json.load(open(args.report))["meta"]["bands"]
    orig = A.load(A.ORIG)

    if args.selftest and not selftest(orig, bands):
        sys.exit(1)
    print()

    rec = {}
    for fn in FILES:
        p = os.path.join(CAPDIR, fn)
        if not os.path.exists(p):
            sys.exit("missing capture %s" % p)
        cap_al, lag = A.align(A.load(p), orig)
        rec[fn] = band_db(cap_al, orig, SEG, bands)
        print("  %-52s lag %4d smp   80 Hz %+7.2f dB" % (fn, lag, rec[fn][bands.index(80.0)]))

    json.dump({"meta": {"bands": bands, "segment": SEG, "level_dbfs": -36.0,
                        "note": "pedal_db only, deconvolved against the -36 input segment"},
               "pedal_db": rec}, open(args.out, "w"), indent=1)
    print("\n  wrote %s" % args.out)


if __name__ == "__main__":
    main()
