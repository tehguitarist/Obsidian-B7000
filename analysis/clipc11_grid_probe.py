#!/usr/bin/env python3.11
"""Session 17 — clipC11 x kInputRef grid at a FIXED PHYSICAL clipper.

Confirms (cheaply, before the long joint fit) the re-diagnosis lever: the GRUNT=Cut coupling cap
C11 (schematic 4n7) is too small, so the Cut high-pass corner strangles the bass and the clipper
never turns on as DRIVE rises -> the model is structurally flat across drive min..noon (+1.1 dB)
while the capture ramps +12.6 dB (handover §3v.4).

Reuses fit_nonlinear's EXACT profile machinery (same tone, window, harmonic extraction, capture
targets), varying ONLY clipC11 (nF) and kInputRef (V/FS) with every other parameter pinned at a
FULLY PHYSICAL clipper + the session-15 beta-shaped JFET core. Read: look for ONE cell where the
min->noon leg approaches the capture's +12.6 AND the ramp rms drops AND clipC11 stays physical.

Renders only — no fit, no code path the fit doesn't use. Independent temp files so it can run while
a fit is going (it does not touch /tmp/fit_*.wav).
"""
import sys
import numpy as np

sys.path.insert(0, "analysis")
import fit_nonlinear as F

# Fixed, fully-physical clipper + the session-15 beta-shaped JFET core (the point session 15
# reached before the clipper-level blocker). Order = F.FIT_KEYS:
#   jfetSatPos jfetSatNeg jfetCeilPos jfetCeilNeg jfetExpandBeta clipA0 clipSatLo clipSatHi clipK
#   kInputRef clipC11(nF)
BASE = {
    "jfetSatPos": 0.33, "jfetSatNeg": 1.69, "jfetCeilPos": 1.43, "jfetCeilNeg": 0.49,
    "jfetExpandBeta": 1.8, "clipA0": 25.0, "clipSatLo": 3.15, "clipSatHi": 3.85, "clipK": 1.5,
}
C11_GRID = [4.7, 12.0, 22.0, 33.0, 47.0]   # nF; schematic 4.7
K_GRID = [0.87, 1.60, 2.40, 3.40]          # V/FS; 0.87 = old adopted, 2.40 = onset-gate best rms

LEGS = ["min", "9:30", "noon", "2:30", "max"]


def profile_row(params):
    prof = F.render_profiles(params)
    return {lbl: prof[lbl]["H3"] - prof[lbl]["H2"] for lbl in LEGS}


def main():
    tgt = F.capture_targets()
    cap = {lbl: tgt[lbl]["H3"] - tgt[lbl]["H2"] for lbl in LEGS}
    cap_leg = cap["noon"] - cap["min"]

    print("=" * 100)
    print("clipC11 x kInputRef grid — GRUNT=Cut, fixed physical clipper. H3-H2 (dB) at 220 Hz.")
    print(f"  fixed: clipA0=25  clipSat=3.15/3.85 (7.0 V)  clipK=1.5  beta=1.8  (all physical)")
    print("=" * 100)
    print(f"  CAPTURE  |  " + "  ".join(f"{cap[l]:+6.1f}" for l in LEGS) +
          f"  |  min->noon leg {cap_leg:+5.1f}   ramp-rms 0.00")
    print("-" * 100)
    print(f"  {'C11nF':>5} {'K':>5} | " + "  ".join(f"{l:>6}" for l in LEGS) +
          f"  |  {'leg':>5}  {'noon/cut':>8}  {'rms':>5}")
    print("-" * 100)

    for c11 in C11_GRID:
        for k in K_GRID:
            p = dict(BASE)
            p["kInputRef"] = k
            p["clipC11"] = c11
            vec = [p[key] for key in F.FIT_KEYS]
            row = profile_row(vec)
            leg = row["noon"] - row["min"]
            rms = np.sqrt(np.mean([(row[l] - cap[l]) ** 2 for l in LEGS]))
            mark = "  <--" if abs(leg - cap_leg) < 3.0 and abs(row["noon"] - cap["noon"]) < 3.0 else ""
            print(f"  {c11:5.1f} {k:5.2f} | " + "  ".join(f"{row[l]:+6.1f}" for l in LEGS) +
                  f"  |  {leg:+5.1f}  {row['noon']:+8.1f}  {rms:5.2f}{mark}")
        print()

    print("READING: a '<--' marks a cell whose min->noon leg AND absolute noon both land within")
    print("3 dB of the capture. If those cells cluster at clipC11 well above 4.7 nF, the Cut")
    print("coupling corner is the missing lever and the joint fit should confirm a raised C11.")
    print("If NO cell closes even at 47 nF, the coupling is not sufficient alone — STOP and report.")


if __name__ == "__main__":
    main()
