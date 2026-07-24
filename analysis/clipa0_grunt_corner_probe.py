#!/usr/bin/env python3.11
"""Phase-7 SESSION 17 — is `clipA0` the coupling knob, and is its 20-30 acceptance range a PRIOR
that the GRUNT-corner evidence contradicts?

WHY THIS EXISTS. `clipper_input_coupling_gate.py` PASSED and localised the error: at GRUNT=cut the
model needs an effective coupling ~4.6x larger than the schematic's C11 = 4n7 to reach the capture's
drive-noon H3-H2, and the model OVER-produces the GRUNT boost-vs-cut effect (+19.7 dB vs the
capture's +11.6). Both say the same thing — **the model's GRUNT high-pass corner is too HIGH**.

That corner is  1/(2*pi*Cg*(R16 + R18/(1+A0))),  and C11/R16/R18 are all BOM-verified. The one
remaining term is A0. So this probe asks the obvious question: does a LOWER clipA0 — which raises
the input-node impedance R18/(1+A0) and drops the corner — reproduce the capture?

⚠ THE POINT THIS PROBE IS REALLY ABOUT. Session 15 REJECTED a fit for landing at clipA0 = 8.2,
because circuit.md says 20-30. But circuit.md's own GRUNT note says, in as many words, "Fit A0 from
the capture (or the datasheet VTC slope) and re-check the three GRUNT corners against captures" —
i.e. 20-30 is a PRIOR (community/datasheet), never a measurement of THIS unit, and the GRUNT corners
were always the intended way to pin it. This is the third time in three sessions that an acceptance
criterion has turned out to be a frozen, unmeasured prior:
    session 16 — kInputRef (0.87 ADOPTED, degenerate with clipSat, never measured)
    session 16 — clipSat judged alone while K was pinned (half a degenerate pair)
    session 17 — clipA0's 20-30, judged against a prior while the GRUNT corners it was supposed to
                 be fit from were never checked
Each one caused a fit to be rejected for reporting an error it was not allowed to express.

⚠ THE CONFOUND, STATED FIRST. clipA0 does DOUBLE DUTY: it sets the clipper's closed-loop gain AND
(through R18/(1+A0)) the input impedance that positions the GRUNT corner. Lowering it moves those
two in OPPOSITE directions for H3-H2 — less closed-loop gain (less distortion) but a lower corner
(more 220 Hz reaching the clipper). So a sweep is genuinely discriminating: a value that fixes the
GRUNT effect while ALSO improving the drive ramp is real evidence, whereas either alone is not.

PRE-REGISTERED — report all three at the SAME A0, never best-of-each-column (L-003):
  (1) GRUNT effect at noon (boost - cut) -> capture +11.6 dB
  (2) noon/cut H3-H2                     -> capture -10.6 dB
  (3) min->noon leg at cut               -> capture +12.6 dB, and whole-ramp rms vs capture

Run:  /opt/homebrew/bin/python3.11 analysis/clipa0_grunt_corner_probe.py
Log:  analysis/fit_logs/step7_clipa0_grunt_corner.log
"""
import sys, os, math, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import analyze as A
import fit_nonlinear as F
from captures import parse_capture, render_args, load_capture, RENDER_BIN

FS = 48000
LOG = "analysis/fit_logs/step7_clipa0_grunt_corner.log"
LABELS = ["min", "9:30", "noon", "2:30", "max"]
TONE_IN = "/tmp/a0gc_tone220.wav"

# [s, a, ceilPos, ceilNeg, beta, clipA0, satLo, satHi, clipK, kInputRef]
BASE = [0.30, 4.0, 1.0, 0.5, 1.8, 25.0, 3.15, 3.85, 1.5, 0.87]
IA0, IK = 5, 9
A0_SWEEP = [3.0, 5.0, 8.0, 12.0, 18.0, 25.0, 30.0]
K_SWEEP = [0.87, 1.70, 2.40]

R16, R18, C11 = 6.8e3, 330.0e3, 4.7e-9


def corner_hz(a0, cg=C11):
    return 1.0 / (2 * math.pi * cg * (R16 + R18 / (1.0 + a0)))


def ratio(point, cap_file, grunt_idx):
    extra, own = F._split_flags(point)
    parsed = dict(parse_capture(cap_file))
    parsed["gruntIdx"] = grunt_idx
    o = "/tmp/a0gc.wav"
    subprocess.run([RENDER_BIN, TONE_IN, o, "--os", "8"] + own + render_args(parsed, extra),
                   check=True, capture_output=True)
    p = F._profile(A.load(o)[int(0.5 * FS):int(1.15 * FS)])
    return p["H3"] - p["H2"]


def main():
    F._short_tone(TONE_IN, F.F0)
    os.makedirs("analysis/fit_logs", exist_ok=True)
    log = open(LOG, "w")

    def emit(s=""):
        print(s)
        log.write(s + "\n")

    tg = F.capture_targets()
    cap = {l: tg[l]["H3"] - tg[l]["H2"] for l in LABELS}
    cap_boost_noon = F._profile(A.seg_of(load_capture(
        "analysis/captures/grunt-boost_base-od.wav"), "tone_220"))
    cap_gr = (cap_boost_noon["H3"] - cap_boost_noon["H2"]) - cap["noon"]

    emit("=" * 104)
    emit("SESSION-17 — clipA0 as the GRUNT-corner / input-coupling knob")
    emit("=" * 104)
    emit(f"  capture ramp (GRUNT=cut): " + "  ".join(f"{l}={cap[l]:+.1f}" for l in LABELS))
    emit(f"  capture min->noon leg {cap['noon']-cap['min']:+.1f} dB;  "
         f"capture GRUNT effect at noon (boost-cut) {cap_gr:+.1f} dB")
    emit("")
    emit("  small-signal GRUNT corner at Cg = C11 = 4n7, by clipA0:")
    emit("    " + "   ".join(f"A0={a:g}: {corner_hz(a):.0f}Hz" for a in A0_SWEEP))
    emit("    (the 220 Hz fit tone sits BELOW every one of these -> the cut position attenuates it;")
    emit("     how much is exactly what A0 controls)")
    emit("")

    for K in K_SWEEP:
        emit("-" * 104)
        emit(f"K (kInputRef) = {K:.2f} V/FS   ({K/2:.2f} V peak at the -6 dBFS 'hot bass' rung)")
        emit("-" * 104)
        emit(f"  {'clipA0':>7} {'corner':>8} | " + " ".join(f"{l:>7}" for l in LABELS)
             + f" | {'leg':>6} {'rms':>6} | {'noon/cut':>9} {'GRUNTeff':>9}")
        for a0 in A0_SWEEP:
            pt = list(BASE); pt[IA0] = a0; pt[IK] = K
            r = {l: ratio(pt, c, 1) for c, l in F.DRIVE_CAPS}
            boost_noon = ratio(pt, "grunt-boost_base-od.wav", 0)
            leg = r["noon"] - r["min"]
            rms = math.sqrt(np.mean([(r[l] - cap[l]) ** 2 for l in LABELS]))
            emit(f"  {a0:>7.1f} {corner_hz(a0):>7.0f}Hz | "
                 + " ".join(f"{r[l]:>+7.1f}" for l in LABELS)
                 + f" | {leg:>+6.1f} {rms:>6.2f} | {r['noon']:>+9.1f} {boost_noon-r['noon']:>+9.1f}")
        emit(f"  {'CAPTURE':>7} {'':>8} | " + " ".join(f"{cap[l]:>+7.1f}" for l in LABELS)
             + f" | {cap['noon']-cap['min']:>+6.1f} {0.0:>6.2f} | {cap['noon']:>+9.1f} {cap_gr:>+9.1f}")
        emit("")

    emit("=" * 104)
    emit("HOW TO READ")
    emit("=" * 104)
    emit("  Look for ONE row where the GRUNT effect approaches the capture's +11.6 AND noon/cut")
    emit("  approaches -10.6 AND the ramp rms drops. All three at the SAME (A0, K), or it is not")
    emit("  evidence — taking the best cell from each column certifies nothing.")
    emit("  If such a row exists at A0 well below 20, then circuit.md's 20-30 is a PRIOR that this")
    emit("  unit's own GRUNT corners contradict, and the session-15 rejection of clipA0 = 8.2 was")
    emit("  the optimiser being right for a reason nobody had measured. That does NOT license")
    emit("  shipping a low A0 on this evidence alone — it licenses MEASURING the GRUNT corners")
    emit("  bleed-free (harmonics carry no clean bleed) and re-deriving A0 from them properly.")
    log.close()
    print(f"\n[log] {LOG}")


if __name__ == "__main__":
    main()
