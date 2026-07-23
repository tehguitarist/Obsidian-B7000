#!/usr/bin/env python3.11
"""Session-11 discriminating check (handover §3j) — does the clipper-hardness `k`
"pivot" signature survive the FULL chain?

The session-11 diagnosis: the clipper VTC's single per-side tanh couples small-signal
gain and knee hardness into one parameter (a0), which is why the step-3/4 fits pinned
clipA0 at its ceiling and still fell ~8 dB short of the capture's H3-H2 at DRIVE-noon.
The predicted signature of the fix (a separate hardness `k`, Clipper.h session-11
reshape) comes from a CLIPPER-ALONE probe: softer shapes raise H3 in the moderate-drive
region while staying ~inert at full saturation.

This script is the required check BEFORE re-running the fit: sweep `k` at fixed
a0 = 25 (all other params nominal, HELD set identical to fit_nonlinear.py) through the
WHOLE chain (JFET + mixer + clipper), and confirm the pivot:

    min / max drive H3-H2 stay ~put   while   noon H3-H2 rises as k drops.

If softening k moves noon AND max together (no pivot), the diagnosis is wrong — STOP
and do not proceed to the fit. Uses only existing captures (the drive sweep + ref-od).

Run: /opt/homebrew/bin/python3.11 analysis/clipk_pivot_check.py [--point=s,a,cp,cn,A0,satLo,satHi]
     --point defaults to NOMINAL; pass the session-11 step4_joint_refit best point to
     probe the pivot AT the operating point where the noon deficit was diagnosed
     (at nominal, gm-held 0.10 mS barely drives the clipper at noon, so the sweep
     sits in a different regime than the one the fit actually failed in).
Log: analysis/fit_logs/step4b_clipk_pivot.log
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import fit_nonlinear as F

# k values to sweep. 2.0 is the new shipped anchor; tanh (the old shape) behaved like
# k ~= 2.5-3, so the top of the range recovers roughly the pre-reshape behaviour.
K_SWEEP = [4.0, 3.0, 2.5, 2.0, 1.75, 1.5, 1.25, 1.0]


def main():
    point = list(F.NOMINAL)
    for arg in sys.argv[1:]:
        if arg.startswith("--point="):
            point = [float(v) for v in arg.split("=", 1)[1].split(",")]
    F.make_short_input()
    targets = F.capture_targets()

    print("Capture targets (tone_220, dB):")
    print(f"  {'drive':5s}  {'H3-H2':>7}")
    for lbl, p in targets.items():
        print(f"  {lbl:5s}  {p['H3'] - p['H2']:>7.1f}")

    print("\nFull-chain H3-H2 (dB) vs clipK — HELD as in the fit; sweep point:")
    print("  " + ", ".join(f"{k}={v:g}" for k, v in zip(F.FIT_KEYS, point)))
    labels = list(targets.keys())
    print(f"  {'k':>5} | " + " | ".join(f"{l:>6s}" for l in labels))
    rows = {}
    try:
        for k in K_SWEEP:
            F.HELD["clipK"] = k
            prof = F.render_profiles(point)
            rows[k] = [prof[l]["H3"] - prof[l]["H2"] for l in labels]
            print(f"  {k:>5.2f} | " + " | ".join(f"{v:>6.1f}" for v in rows[k]))
    finally:
        F.HELD.pop("clipK", None)

    # ---- Pivot verdict -------------------------------------------------------
    # noon must RISE monotonically (within tolerance) as k drops; min and max must
    # move much less than noon does over the same sweep.
    ks = sorted(rows.keys())                      # ascending k
    noon = [rows[k][labels.index("noon")] for k in ks]
    mn = [rows[k][labels.index("min")] for k in ks]
    mx = [rows[k][labels.index("max")] for k in ks]
    noon_rise = noon[0] - noon[-1]                # low-k minus high-k
    min_move = max(mn) - min(mn)
    max_move = max(mx) - min(mx)
    # monotone-with-tolerance: each step down in k should not LOWER noon by > 0.3 dB
    steps = [noon[i] - noon[i + 1] for i in range(len(ks) - 1)]  # toward lower k
    monotone = all(s > -0.3 for s in steps)

    print(f"\nPivot verdict:")
    print(f"  noon rise (k={ks[-1]:g} -> {ks[0]:g}) : {noon_rise:+.1f} dB "
          f"(monotone-with-tol: {'YES' if monotone else 'NO'})")
    print(f"  min  span over sweep        : {min_move:.1f} dB")
    print(f"  max  span over sweep        : {max_move:.1f} dB")
    ok = noon_rise > 2.0 and monotone and max_move < 0.5 * noon_rise
    print(f"  PIVOT {'CONFIRMED' if ok else '** NOT CONFIRMED — STOP, diagnosis wrong **'}: "
          f"noon moves {'and max stays put' if ok else 'the wrong way or max moves with it'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
