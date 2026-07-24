#!/usr/bin/env python3.11
"""SCRATCH probe (session 14) — does the clipK lever work once the JFET ceiling is H3-free?

The ceilk pivot FAILED: raising jfetCeilK moves drive-min AND drive-noon H3-H2 the SAME
direction (both fall through an anti-phase null), so the ceiling-hardness lever cannot make
the capture's ramp (-23.2/-21.0/-10.6). But at high jfetCeilK the ceiling's H3 is ~gone and
the CLIPPER-ALONE row ramps the right SHAPE (just ~35 dB too low at min).

Hypothesis: session 12's clipK pivot failed ONLY because the JFET ceiling's anti-phase H3 was
masking the clipper. Remove that (hold jfetCeilK high) and the clipK lever should recover its
signature: softening clipK RAISES noon H3-H2 while min/max stay ~put.

This holds jfetCeilK at a HIGH value (ceiling H3-free but still bounding + making H2) and
sweeps clipK, printing H3-H2 across drive. NOT a committed gate — a diagnostic to decide the
branch after the ceilk pivot STOP.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import fit_nonlinear as F

CEILK_HOLD = 8.0     # ceiling H3 ~ removed (from the ceilk pivot: min H3-H2 = -81 at k=8)
CLIPK_SWEEP = [4.0, 3.0, 2.5, 2.0, 1.75, 1.5, 1.25, 1.0]
# proper clipper + session-11 JFET shape; clipK is the swept var
POINT = [0.246, 2.61, 0.487, 0.274, 25.0, 3.15, 3.85]  # s,a,cp,cn,A0,satLo,satHi


def main():
    F.make_short_input()
    targets = F.capture_targets()
    print("Capture H3-H2 (dB):  " + "  ".join(f"{l}={targets[l]['H3']-targets[l]['H2']:+.1f}"
                                              for l in targets))
    print(f"\njfetCeilK HELD at {CEILK_HOLD} (ceiling H3-free); sweep clipK:")
    labels = list(targets.keys())
    print(f"  {'clipK':>5} | " + " | ".join(f"{l:>6s}" for l in labels))
    rows = {}
    try:
        F.HELD["jfetCeilK"] = CEILK_HOLD
        for ck in CLIPK_SWEEP:
            F.HELD["clipK"] = ck
            prof = F.render_profiles(POINT)
            rows[ck] = [prof[l]["H3"] - prof[l]["H2"] for l in labels]
            print(f"  {ck:>5.2f} | " + " | ".join(f"{v:>6.1f}" for v in rows[ck]))
    finally:
        F.HELD.pop("jfetCeilK", None)
        F.HELD.pop("clipK", None)

    cks = sorted(rows.keys())  # ascending clipK
    noon = [rows[ck][labels.index("noon")] for ck in cks]
    mn = [rows[ck][labels.index("min")] for ck in cks]
    mx = [rows[ck][labels.index("max")] for ck in cks]
    # clipK signature: softening (lower clipK) RAISES noon; min/max move much less
    noon_rise = noon[0] - noon[-1]         # low-clipK minus high-clipK
    print(f"\n  noon rise (clipK {cks[-1]:g}->{cks[0]:g}) : {noon_rise:+.1f} dB (want >0, toward -10.6)")
    print(f"  min span : {max(mn)-min(mn):.1f} dB   max span : {max(mx)-min(mx):.1f} dB")


if __name__ == "__main__":
    main()
