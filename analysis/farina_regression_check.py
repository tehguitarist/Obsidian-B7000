#!/usr/bin/env python3
"""Prove the order-limit fix cannot disturb any existing THD fit.

The order limit only masks order N above SWEEP_F1*margin/N, and the lowest
such cut is H7 at 19000/7 = 2714 Hz -- so nothing below 2714 Hz can move.
Assert that rather than claim it.

Run from repo root:
    python3 analysis/farina_regression_check.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A
import gen_test_signal as G
import captures as C

CUT_HZ = G.SWEEP_F1 * A.ORDER_LIMIT_MARGIN / 7.0


def main():
    orig = A.load(A.ORIG)
    ref = A.seg_of(orig, "sweep_clean")
    caps = C.find_captures()
    if not caps:
        sys.exit("no captures found")

    print("FARINA ORDER-LIMIT REGRESSION CHECK")
    print(f"  lowest order-limit boundary = SWEEP_F1*{A.ORDER_LIMIT_MARGIN}/7 = {CUT_HZ:.0f} Hz")
    print("  every project THD fit is anchored at 100/200 Hz -> must be bit-identical\n")
    print(f"{'capture':<42}{'max|d| <2714Hz':>16}{'max|d| @100/200':>17}{'verdict':>9}")

    worst = 0.0
    for path, parsed in caps:
        cap = C.load_capture(path)
        if not A.is_full_length(cap, orig):
            continue
        cap_al, _ = A.align(cap, orig)
        seg = A.seg_of(cap_al, "sweep_drv_-12")
        fr, thd_new, _ = A.harmonic_thd_curve(seg, ref, max_order=7, order_limit=True)
        _, thd_old, _ = A.harmonic_thd_curve(seg, ref, max_order=7, order_limit=False)

        below = fr < CUT_HZ
        d_below = float(np.max(np.abs(thd_new[below] - thd_old[below])))
        d_anch = max(
            abs(float(np.interp(f, fr, thd_new)) - float(np.interp(f, fr, thd_old)))
            for f in (100.0, 200.0)
        )
        worst = max(worst, d_below)
        ok = "IDENTICAL" if d_below == 0.0 else ("ok" if d_below < 1e-9 else "CHANGED")
        name = os.path.basename(path)[:40]
        print(f"{name:<42}{d_below:>16.2e}{d_anch:>17.2e}{ok:>9}")

    print()
    if worst == 0.0:
        print(f"PASS -- below {CUT_HZ:.0f} Hz the curve is bit-identical on every capture.")
        print("       No existing fit moves.")
    else:
        print(f"FAIL -- max deviation {worst:.3e} below {CUT_HZ:.0f} Hz. Investigate.")
        sys.exit(1)


if __name__ == "__main__":
    main()
