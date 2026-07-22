#!/usr/bin/env python3.11
"""Phase-7 step 2 — fit the CD4049 clipper + J201 shaper constants to the driven captures.

Objective = the tone_220 harmonic profile (THD + H2..H5 dB re fundamental, calibration-and-
gain-staging.md §6b) across the DRIVE sweep. Harmonic RATIOS are level-independent, so this is
valid before makeup (step 5) is set. kInputRef is anchored (step 1); driveTaperExp is held at its
nominal here (taper fit is step 4 — a coupled re-fit may follow).

Speed trick: the capture targets are precomputed CONSTANTS (measured once from the real captures),
so each optimiser eval only renders a SHORT synthetic 220 Hz tone through the plug at each drive
setting — ~20x faster than rendering the full 84 s test signal.

Run: /opt/homebrew/bin/python3.11 analysis/fit_nonlinear.py
"""
import sys, os, subprocess, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import analyze as A
from captures import parse_capture, render_args, load_capture, RENDER_BIN
from scipy.io import wavfile
from scipy.optimize import minimize

FS = 48000
F0 = 220.0
CAP = "analysis/captures"
# driveTaperExp is included because the THD-vs-drive SLOPE (how fast distortion ramps across the
# knob) is set by the drive taper, and is coupled to the clipper/JFET gains — holding it fixed makes
# the fit match the drive extremes while leaving the mid-range too clean (observed). It is nominally
# a step-4 taper param, but it cannot be separated from this fit; step 4 refines it if needed.
# jfetSatPos = square-law knee `s`; jfetSatNeg = even/H2 strength `a` (JfetStage reshape 2026-07-22).
FIT_KEYS = ["jfetG0", "jfetSatPos", "jfetSatNeg", "clipA0", "clipSatLo", "clipSatHi", "driveTaperExp"]
NOMINAL  = [15.0, 3.0, 0.3, 25.0, 3.15, 3.85, 1.5]
# Bounds WIDENED 2026-07-22 after run 1 pinned jfetSatPos exactly at its old 6.0 ceiling and
# pushed clipSatLo (1.317) down near its old 1.2 floor — a param resting ON a bound means the
# optimum is outside the box, so the reported value is an artefact of the box, not a fit.
# jfetSatPos is the square-law knee `s`; a large `s` with a small `a` is a legitimate solution
# (the even bump stays mild, |a|*s is what must stay < 2.598 for monotonicity — asserted in
# JfetStageTest). clipSat* floors dropped because the R19-dropped 4049 rail is fitting LOWER
# than the nominal ~7 V sum.
BOUNDS   = [(2, 16), (1, 20), (0.0, 1.0), (3, 30), (0.4, 6.5), (0.4, 7.5), (0.4, 3.0)]
# drive capture -> label
DRIVE_CAPS = [
    ("drive-0700_base-od.wav", "min"),
    ("drive-0930_base-od.wav", "9:30"),
    ("ref-od.wav",             "noon"),
    ("drive-1430_base-od.wav", "2:30"),
    ("drive-1700_base-od.wav", "max"),
]
# harmonic weights (dB error) — H2/H3 carry clip CHARACTER, weight them; H4/H5 noisier; +THD
W = dict(H2=1.0, H3=1.0, H4=0.5, H5=0.3, THD=0.7)

SHORT_IN = "/tmp/fit_tone220.wav"


def _harm(seg, nmax=6):
    w = np.hanning(len(seg)); X = np.abs(np.fft.rfft(seg * w)); frq = np.fft.rfftfreq(len(seg), 1 / FS)
    def amp(f):
        k = np.argmin(np.abs(frq - f)); return X[max(0, k - 3):k + 4].max()
    h = [amp(F0 * n) for n in range(1, nmax + 1)]
    thd = np.sqrt(sum(a * a for a in h[1:])) / (h[0] + 1e-20)
    return h, thd


def _profile(seg):
    """{H2..H5 dB re fundamental, THD dB} from a steady 220 Hz segment (edges trimmed)."""
    m = len(seg) // 6
    h, thd = _harm(seg[m:-m])
    d = {f"H{i+1}": 20 * np.log10(h[i] / h[0] + 1e-20) for i in range(1, 5)}
    d["THD"] = 20 * np.log10(thd + 1e-20)
    return d


def make_short_input():
    n = int(1.2 * FS)
    t = np.arange(n) / FS
    x = (10 ** (-14 / 20)) * np.sin(2 * np.pi * F0 * t)
    # short fades so the render's smoothers settle before the measured window
    k = int(0.02 * FS); env = np.ones(n); env[:k] = np.linspace(0, 1, k); env[-k:] = np.linspace(1, 0, k)
    wavfile.write(SHORT_IN, FS, (x * env).astype(np.float32))


def capture_targets():
    tg = {}
    for cap, lbl in DRIVE_CAPS:
        c = load_capture(f"{CAP}/{cap}")
        tg[lbl] = _profile(A.seg_of(c, "tone_220"))
    return tg


def render_profiles(params):
    """Render the short tone through the plug at each drive setting; return {label: profile}."""
    extra = []
    for k, v in zip(FIT_KEYS, params):
        extra += ["--fit", f"{k}={v}"]
    out = {}
    for cap, lbl in DRIVE_CAPS:
        parsed = parse_capture(cap)
        o = f"/tmp/fit_{lbl.replace(':','')}.wav"
        subprocess.run([RENDER_BIN, SHORT_IN, o, "--os", "8"] + render_args(parsed, extra),
                       check=True, capture_output=True)
        r = A.load(o)
        # steady window: last ~0.6 s (after smoother settle), trimmed
        seg = r[int(0.5 * FS):int(1.15 * FS)]
        out[lbl] = _profile(seg)
    return out


# JfetStage's square-law shaper g(w) = w + a*s^2*(1-sech(w/s)) has
# g'(w) = 1 + a*s*sech(w/s)*tanh(w/s), and max|sech*tanh| = 1/2, so it is monotonic
# **iff |a|*s < 2**. Outside that the map FOLDS BACK inside the signal range, which is
# unphysical and produces a spuriously good H2 match. This is not hypothetical: the
# 2026-07-22 run-2 best point (s=10.585, a=0.232 -> |a|*s = 2.456, min slope -0.21) was
# exactly such a fold-back, and the bounds alone do not exclude it because it is a
# PRODUCT constraint, not a box. Hence this explicit feasibility gate.
MONO_LIMIT = 2.0


def monotonic(params):
    s = params[FIT_KEYS.index("jfetSatPos")]
    a = params[FIT_KEYS.index("jfetSatNeg")]
    return abs(a) * s < MONO_LIMIT


def cost(params, targets, verbose=False):
    if not monotonic(params):
        # infeasible: non-monotone (fold-back) waveshaper. Keep the return SHAPE
        # consistent so a verbose call on an infeasible point can't TypeError.
        return (1e6, None) if verbose else 1e6
    try:
        prof = render_profiles(params)
    except subprocess.CalledProcessError:
        return 1e6
    total = 0.0
    for lbl in targets:
        for key, w in W.items():
            e = prof[lbl][key] - targets[lbl][key]
            total += w * e * e
    if verbose:
        return total, prof
    return total


def main():
    make_short_input()
    targets = capture_targets()
    print("Capture targets (tone_220, dB re fundamental):")
    for lbl, p in targets.items():
        print(f"  {lbl:5s} THD={p['THD']:6.1f} H2={p['H2']:6.1f} H3={p['H3']:6.1f} H4={p['H4']:6.1f} H5={p['H5']:6.1f}")

    c0 = cost(NOMINAL, targets)
    print(f"\nNominal cost = {c0:.1f}")

    # Nelder-Mead from nominal, then a light restart.
    # `--start a,b,c,...` refines from ONE explicit point instead (used to re-run a previous
    # best under WIDENED bounds — a param that came back resting on a bound must be re-fit,
    # not committed).
    best = None
    starts = [
        [8, 3.0, 0.15, 25, 3.15, 3.85, 1.0],  # moderate gain, mild even, nominal clipper
        [6, 2.5, 0.20, 20, 3.0, 3.6, 1.2],
        [10, 3.5, 0.10, 15, 3.0, 4.0, 0.8],
    ]
    for arg in sys.argv[1:]:
        if arg.startswith("--start="):
            starts = [[float(v) for v in arg.split("=", 1)[1].split(",")]]
    for start in starts:
        res = minimize(cost, start, args=(targets,), method="Nelder-Mead",
                       bounds=BOUNDS, options=dict(maxiter=400, xatol=0.02, fatol=0.3))
        if best is None or res.fun < best.fun:
            best = res
        print(f"  start {[round(s,1) for s in start]} -> cost {res.fun:.1f}")

    print(f"\nBest cost = {best.fun:.1f}  (nominal {c0:.1f})")
    print("Fitted params:")
    for k, v, nom in zip(FIT_KEYS, best.x, NOMINAL):
        print(f"  {k:12s} {v:7.3f}   (nominal {nom})")

    _, prof = cost(best.x, targets, verbose=True)
    if prof is None:
        print("\n** every start was INFEASIBLE (|a|*s >= 2, fold-back shaper) — no profile **")
        return
    print("\nFITTED plug vs capture (tone_220, dB re fundamental):")
    print(f"{'drive':6s} | {'THD c/p':>13s} | {'H2 c/p':>13s} | {'H3 c/p':>13s} | {'H4 c/p':>13s}")
    for lbl in targets:
        t, p = targets[lbl], prof[lbl]
        print(f"{lbl:6s} | {t['THD']:5.1f}/{p['THD']:5.1f} | {t['H2']:5.1f}/{p['H2']:5.1f} | "
              f"{t['H3']:5.1f}/{p['H3']:5.1f} | {t['H4']:5.1f}/{p['H4']:5.1f}")


if __name__ == "__main__":
    main()
