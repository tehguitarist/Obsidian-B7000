#!/usr/bin/env python3.11
"""Phase-7 step 2 cross-check — is the fitted `clipA0` consistent with the GRUNT voicing?

`clipA0` is the CD4049's finite open-loop gain, and circuit.md / Clipper.h flag it as
constrained by TWO independent measurements at once:
  (a) the drive-sweep LEVEL / harmonic profile  -> what fit_nonlinear.py fits, and
  (b) the three GRUNT high-pass CORNERS, because the clipper's input-node impedance is
      R18/(1+A0), which dominates the RC with the cap bank:
          fc = 1 / (2*pi * Cg * (R16 + R18/(1+A0)))
      A0 = 25 -> ~900/144/36 Hz;  a much lower A0 pushes all three corners UP.
FitParams.h says explicitly: "fit it against the GRUNT voicing and the drive-sweep level
together, not either alone." fit_nonlinear.py only exercises (a) — this script is (b).

METHOD — matched-pair differencing (dsp.md "Isolate a coupled control with a MATCHED-PAIR
capture"). GRUNT-flat and GRUNT-boost captures differ from the GRUNT-cut baseline in ONE
knob only, so the difference FR cancels the (identical) clipping character and the whole
rest of the chain, leaving just the cap-bank corner shift. We compute that same difference
from renders at several candidate A0 values and pick the one that tracks the capture.

Run: /opt/homebrew/bin/python3.11 analysis/grunt_a0_check.py [A0 ...]
"""
import sys, os, subprocess, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import analyze as A
from captures import parse_capture, render_args, load_capture, RENDER_BIN

ORIG = "analysis/test_signal_48k.wav"
CAP = "analysis/captures"
SEG = "sweep_drv_-18"          # driven sweep: the GRUNT corner is a pre-clipper HP, so it
                               # must be measured through the drive path, not the clean one.
# Band deliberately starts at 50 Hz, NOT 20: below ~40 Hz the driven-sweep captures are
# measurement noise (the matched-pair diff swings -5..-11 dB there, non-monotonically, and
# disagrees between adjacent bins). An earlier version of this script averaged from 20 Hz and
# read that noise as a "flat position gives LESS bass than cut" result, which looked like the
# GRUNT cap map being wrong — it was not. 50-300 Hz is where the flat/boost corners actually
# live and where capture and render both have real signal.
BAND = (50.0, 300.0)

# (capture file, GRUNT position). ref-od is the baseline = GRUNT cut (C11 4n7 alone).
POSITIONS = [
    ("ref-od.wav",              "cut"),
    ("grunt-flat_base-od.wav",  "flat"),
    ("grunt-boost_base-od.wav", "boost"),
]


def fr(x, orig):
    """1/6-oct-smoothed transfer of a segment vs the same segment of the source signal."""
    f, mag = A.transfer(A.seg_of(x, SEG), A.seg_of(orig, SEG))
    m = (f >= BAND[0]) & (f <= BAND[1])
    return f[m], mag[m]


def separation(f, diffs):
    """Mean (boost - flat) across the band.

    ⚠ **This is a PRE-CLIPPER LEVEL METER, not an A0 discriminator.** An earlier version
    of this docstring claimed it constrained A0; that is WRONG and cost real time.
    Measured (dsp-validator, 2026-07-22), the flat->boost separation vs the amplitude
    arriving at the clipper, at 100 Hz:

        Vin at clipper   A0=25, sat 3.15/3.85   A0=7.28, sat 0.773/1.012
        <= 0.01 V              +4.93 dB                +1.58 dB
           0.1  V              +4.71                   +1.19
           0.3  V              +2.94                   +0.22
           1.0  V              +0.07                   +0.01
        >= 3    V               0.00                   +0.06

    So the quantity collapses with DRIVE LEVEL and is far more sensitive to upstream gain
    (kG0 x drive taper x kInputRef) than to A0 — which is why sweeping A0 from 7.3 to 90
    moves it by only 0.14 dB. The chain currently delivers 0.34/0.40/0.31/0.10 V at
    50/100/200/300 Hz, squarely in the collapse knee, i.e. the model runs 3-10x too hot
    into the clipper. Fitting A0 against this will drive A0 to a wrong value while the
    real error is upstream. Use it to diagnose LEVEL, not A0."""
    return float(np.mean(diffs["boost"] - diffs["flat"]))


def capture_diffs(orig):
    curves = {}
    for fname, pos in POSITIONS:
        c = load_capture(f"{CAP}/{fname}")
        c, _lag = A.align(c, orig)
        f, mag = fr(c, orig)
        curves[pos] = mag
    return f, {p: curves[p] - curves["cut"] for p in ("flat", "boost")}


def render_diffs(orig, a0, fitted):
    curves = {}
    for fname, pos in POSITIONS:
        parsed = parse_capture(fname)
        extra = ["--fit", f"clipA0={a0}"]
        for k, v in fitted.items():
            extra += ["--fit", f"{k}={v}"]
        out = f"/tmp/grunt_{pos}_{a0:g}.wav"
        subprocess.run([RENDER_BIN, ORIG, out, "--os", "8"] + render_args(parsed, extra),
                       check=True, capture_output=True)
        r, _lag = A.align(A.load(out), orig)
        f, mag = fr(r, orig)
        curves[pos] = mag
    return f, {p: curves[p] - curves["cut"] for p in ("flat", "boost")}


def main():
    # Default = fit_nonlinear.py's run-2 best point. Override any of them with
    # `key=value` args to test a different (e.g. physically-nominal) clipper; bare
    # numeric args are the clipA0 values to sweep.
    # ** Reset to NOMINAL 2026-07-22. ** This used to default to fit_nonlinear.py's run-2 best
    # point, which (a) passed `jfetG0`, a key the 2026-07-22 restructure DELETED — so every run
    # of this script died in OfflineRender's arg parser — and (b) was a rejected fit point
    # anyway (physically implausible, and a non-monotone fold-back at |a|*s = 2.456). Nominal is
    # the honest default until step 2 is re-run on the restructured chain; override on the
    # command line to test a candidate.
    fitted = dict(jfetGm=0.69e-3, jfetRo=200e3, jfetRq2=1e6, jfetSatPos=0.5, jfetSatNeg=1.0,
                  clipSatLo=3.15, clipSatHi=3.85, driveTaperExp=1.5)
    a0s = []
    for arg in sys.argv[1:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            fitted[k] = float(v)
        else:
            a0s.append(float(arg))
    a0s = a0s or [9.4, 15.0, 20.0, 25.0]
    print("clipper/JFET params held at: " + ", ".join(f"{k}={v:g}" for k, v in fitted.items()))

    orig = A.load(ORIG)
    fc, cdiff = capture_diffs(orig)
    cap_sep = separation(fc, cdiff)
    print(f"CAPTURE matched-pair diffs (vs GRUNT cut), {SEG}, {BAND[0]:.0f}-{BAND[1]:.0f} Hz:")
    for p in ("flat", "boost"):
        print(f"  {p:5s}: mean {np.mean(cdiff[p]):+6.2f} dB")
    print(f"  boost-flat SEPARATION = {cap_sep:+.2f} dB   <- the A0 discriminator")

    print(f"\n{'A0':>6s} | {'flat-cut':>9s} | {'boost-cut':>9s} | {'sep':>7s} | {'sep err':>8s} | {'RMS err':>8s}")
    print(f"{'CAPTURE':>6s} | {np.mean(cdiff['flat']):+9.2f} | {np.mean(cdiff['boost']):+9.2f} | "
          f"{cap_sep:+7.2f} | {'':>8s} | {'':>8s}")
    for a0 in a0s:
        f, rdiff = render_diffs(orig, a0, fitted)
        sep = separation(f, rdiff)
        err = np.sqrt(np.mean(np.concatenate([(rdiff[p] - cdiff[p]) ** 2 for p in ("flat", "boost")])))
        print(f"{a0:6.1f} | {np.mean(rdiff['flat']):+9.2f} | {np.mean(rdiff['boost']):+9.2f} | "
              f"{sep:+7.2f} | {sep - cap_sep:+8.2f} | {err:8.2f}")


if __name__ == "__main__":
    main()
