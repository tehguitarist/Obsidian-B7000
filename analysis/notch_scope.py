#!/usr/bin/env python3.11
"""SESSION 14 (tail) — scope the ~320 Hz treble-net notch discrepancy in the ASSEMBLED chain.

The handover ("STILL OPEN — the ~320 Hz treble-net notch") flags that the notch is ~-28 dB in the
ISOLATED analytic treble stage but the CAPTURE shows only -3.4 dB, and notes it is much SHALLOWER in
the assembled chain (~-5.6 dB) than isolated — and to RE-MEASURE it after the gm/ro fit before
spending more on it. The gm/ro fix is done (jfetGm held 0.10 mS). This quantifies the CURRENT
model-vs-capture discrepancy so session 15 knows whether the notch fix is small or a front-end redo.

Method (reuses fit_jfet_boundary.py's approach): the pedal is LINEAR at drive-min (capture OD-path
shape identical +-0.15 dB across -36/-18 dBFS sweeps), so the drive-min OD-path FR is the unit's true
small-signal treble transfer. Render the current model drive-min, transfer both against the dry input,
mean-remove (free-gain quotient), and report the dip depth in 250-400 Hz relative to a local baseline.

Run (repo root): /opt/homebrew/bin/python3.11 analysis/notch_scope.py
"""
import sys, os, subprocess
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import analyze as A
from captures import parse_capture, render_args, load_capture, RENDER_BIN

CAP_DIR = "analysis/captures"
CAP_FILE = "drive-0700_base-od.wav"   # drive-min OD = most linear OD capture
SEG = "sweep_clean_-36"
ORIG = "analysis/test_signal_48k.wav"
OS = 8
# Held params matching fit_nonlinear.py HELD (gm re-anchored, tapers measured). jfetCeilK defaults
# to 2 in FitParams; ceiling is the placeholder nominal — this measures the LINEAR treble net, which
# is upstream of and independent of the ceiling shape at drive-min small signal.
HELD = {"jfetGm": 0.10e-3, "jfetRo": 200.0e3, "jfetRq2": 1.0e6,
        "levelTaperExp": 2.25, "driveTaperExp": 2.5}


def notch_depth(f, mag, band=(250.0, 400.0), shoulder=(180.0, 600.0)):
    """Dip depth (dB) = min in `band` minus the shoulder baseline (linear fit across `shoulder`
    excluding the band), so a broadband tilt doesn't masquerade as a notch."""
    inb = (f >= band[0]) & (f <= band[1])
    insh = (f >= shoulder[0]) & (f <= shoulder[1]) & ~inb
    # linear baseline (in log-f) from the shoulders
    lf = np.log10(f)
    coef = np.polyfit(lf[insh], mag[insh], 1)
    base = np.polyval(coef, lf[inb])
    dip = mag[inb] - base
    kmin = int(np.argmin(dip))
    return float(dip[kmin]), float(f[inb][kmin])


def main():
    orig = A.load(ORIG)

    # Capture OD-path shape
    cap = load_capture(f"{CAP_DIR}/{CAP_FILE}")
    fc, mc = A.transfer(A.seg_of(cap, SEG), A.seg_of(orig, SEG))

    # Model render at current held params, drive-min
    parsed = parse_capture(CAP_FILE)
    extra = []
    for k, v in HELD.items():
        extra += ["--fit", f"{k}={v:.9g}"]
    out = "/tmp/notch_scope_model.wav"
    subprocess.run([RENDER_BIN, ORIG, out, "--os", str(OS)] + render_args(parsed, extra),
                   check=True, capture_output=True)
    r, lag = A.align(A.load(out), orig)
    fm, mm = A.transfer(A.seg_of(r, SEG), A.seg_of(orig, SEG))

    # Common grid, mean-removed shapes
    fg = np.logspace(np.log10(120), np.log10(2000), 200)
    cg = np.interp(fg, fc, mc); cg -= cg.mean()
    mg = np.interp(fg, fm, mm); mg -= mg.mean()

    # TWO notches in the model, both "-28 dB isolated" open items, both in H3 bands:
    #   ~320 Hz treble-net notch (C5/C9/C6+R7)  -> the 110 Hz tone's H3 (330 Hz)
    #   ~717 Hz bridged-T notch  (RecoveryBridgedT) -> the 220 Hz tone's H3 (660 Hz)
    # 440 Hz tone's H3 (1320 Hz) is clear of both.
    for name, band, sh in [("treble-net ~320", (250, 400), (180, 600)),
                           ("bridged-T ~717", (620, 820), (450, 1100))]:
        cd, cf = notch_depth(fg, cg, band, sh)
        md, mf = notch_depth(fg, mg, band, sh)
        print(f"[{name}] capture dip {cd:+.1f} dB @ {cf:.0f} Hz | model dip {md:+.1f} dB @ {mf:.0f} Hz "
              f"| model deeper by {md - cd:+.1f} dB")
    print("\n  freq   capture   model   (mean-removed dB)")
    for f0 in [150, 200, 250, 290, 320, 330, 360, 400, 500, 600, 660, 717, 800, 1000, 1320]:
        c = float(np.interp(f0, fg, cg)); m = float(np.interp(f0, fg, mg))
        mark = ""
        if 250 <= f0 <= 400: mark = "  <- treble-net notch / 110-H3"
        elif 620 <= f0 <= 820: mark = "  <- bridged-T notch / 220-H3"
        elif f0 == 1320: mark = "  <- 440-H3 (clean)"
        print(f"  {f0:4d}   {c:+6.2f}   {m:+6.2f}{mark}")


if __name__ == "__main__":
    main()
