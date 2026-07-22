#!/usr/bin/env python3.11
"""Phase-7 step 0 (tail) — fit the J201 output-boundary params `jfetGm`/`jfetRo`/`jfetRq2`.

WHY THESE THREE, AND WHY A SHAPE-ONLY FIT
-----------------------------------------
The 2026-07-22 restructure (docs/phase7-calibration-handover.md) made JfetStage a CURRENT
source whose output impedance `Zout(s) = [ro + Rp||Cp] || Rq2` is stamped into TrebleAttack's
nodal matrix. That replaced the old lumped `jfetG0`/`jfetGmR6` pair, so the new params have
never been fitted — a coarse scan got the OD-path shape error from 6.9 dB to 1.4 dB but sat
at the EDGE of its grid on all three, and that scan was ad-hoc (it does not exist in-tree).
This script is the real fit.

The objective is a SHAPE, deliberately, and it is valid *now* — before makeup (step 5), before
the tapers (step 4), and before the nonlinear re-fit (step 2) — for two independent reasons:

  1. **The pedal is LINEAR at drive-min.** The capture's OD-path shape is identical to
     +-0.15 dB across the -36 and -18 dBFS sweeps, so that shape is the unit's true
     small-signal transfer, not a compressed artefact. It is a hard target.
  2. **Mean-removing the dB curve makes the cost blind to every flat gain in the chain** —
     kOutputMakeup, the LEVEL/MASTER tapers, gm's own transconductance scale, and the
     capture's gain-n12 correction all drop out. Only the frequency SHAPE remains, which is
     exactly what the loading boundary sets.

What each parameter can actually do to the shape (they are not independent knobs):
    k0   = 1 + gm*R6        degeneration factor -> the C3 shelf pole AND Zout's DC/HF ratio
    Zout = [ro*k(s)] || Rq2,  ro*k(s) = ro + Rp||Cp,  Rp = ro*gm*R6,  Rp*Cp = R6*C3 (fixed)
So `gm` enters the SHAPE only through k0 (its gain role is normalised away); `ro` and `Rq2`
set how much of the shelf survives against the treble ladder's falling input Z. Expect `Rq2`
to be weakly identified whenever Rq2 >> ro -- the 1-D scans printed at the end make that
visible rather than letting a confident-looking number hide it.

Run (repo root):
    /opt/homebrew/bin/python3.11 analysis/fit_jfet_boundary.py            # grid + refine
    /opt/homebrew/bin/python3.11 analysis/fit_jfet_boundary.py --quick    # grid only
    /opt/homebrew/bin/python3.11 analysis/fit_jfet_boundary.py --start gm,ro,rq2
"""
import sys, os, subprocess, time, itertools
import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, os.path.dirname(__file__))
import analyze as A
from captures import parse_capture, render_args, load_capture, RENDER_BIN

ORIG = "analysis/test_signal_48k.wav"
CAP_DIR = "analysis/captures"

# drive MIN (7:00) => the most linear OD capture, and the one whose level-independence was
# demonstrated. Everything else in the filename is the baseline (EQ flat, blend full OD).
CAP_FILE = "drive-0700_base-od.wav"
SEG = "sweep_clean_-36"     # lowest-level sweep => furthest from any clipping

# Comparison band. 50 Hz floor: below ~40 Hz the driven-sweep captures are measurement noise
# (see grunt_a0_check.py's note — averaging from 20 Hz there once invented a whole fake
# result). 8 kHz ceiling: the two Sallen-Keys are ~60 dB down by then and the capture's
# swept-sine SNR goes with it.
BAND = (50.0, 8000.0)

# The render only needs `sweep_clean` (align anchor, 1.8-11.8 s) and `sweep_clean_-36`
# (12.1-22.1 s). Trimming the INPUT to 22.6 s keeps every segment offset identical — so
# A.seg_of/A.align work unchanged — while cutting each eval to ~1/4 of a full render.
TRIM_SEC = 22.6
TRIM_IN = "/tmp/fit_jfet_trim.wav"

KEYS = ["jfetGm", "jfetRo", "jfetRq2"]
NOMINAL = [0.69e-3, 200.0e3, 1.0e6]
# Bounds are wide on purpose. gm: datasheet 0.69 mS with the documented ~5:1 J201 spread,
# opened another decade DOWN because the coarse scan pushed that way (0.06 mS) — the point of
# the fit is to find out whether the data really demands that, not to forbid it. ro/rq2: a few
# hundred k is the physical expectation; two decades either side.
BOUNDS = [(1.0e-5, 5.0e-3), (1.0e4, 1.0e7), (1.0e4, 1.0e8)]

OS = 8
_cache = {}


# --- target / measurement ---------------------------------------------------------------
def log_grid(n_per_oct=12):
    lo, hi = BAND
    n = int(np.round(np.log2(hi / lo) * n_per_oct)) + 1
    return lo * 2.0 ** (np.arange(n) / n_per_oct)


FGRID = log_grid()


def shape(x, orig):
    """Mean-removed dB transfer of SEG, on a log frequency grid.

    Mean-removal (not normalise-to-one-bin) is the free-gain quotient: it makes the cost a
    pure shape metric AND spreads the reference over the whole band instead of betting the
    whole curve on one possibly-noisy bin. The log grid stops the linear-spaced Welch bins
    from weighting 4-8 kHz ~30x more than 50-100 Hz.
    """
    f, mag = A.transfer(A.seg_of(x, SEG), A.seg_of(orig, SEG))
    m = np.interp(FGRID, f, mag)
    return m - m.mean()


def cost_of(curve, target):
    return float(np.sqrt(np.mean((curve - target) ** 2)))


# --- render -----------------------------------------------------------------------------
def make_trim(orig):
    from scipy.io import wavfile
    n = int(TRIM_SEC * A.FS)
    wavfile.write(TRIM_IN, A.FS, orig[:n].astype(np.float32))
    return orig[:n]


def render_shape(params, trim_orig, tag="p"):
    key = tuple(round(float(v), 12) for v in params)
    if key in _cache:
        return _cache[key]
    parsed = parse_capture(CAP_FILE)
    extra = []
    for k, v in zip(KEYS, params):
        extra += ["--fit", f"{k}={v:.9g}"]
    out = f"/tmp/fit_jfet_{tag}.wav"
    subprocess.run([RENDER_BIN, TRIM_IN, out, "--os", str(OS)] + render_args(parsed, extra),
                   check=True, capture_output=True)
    r, _lag = A.align(A.load(out), trim_orig)
    s = shape(r, trim_orig)
    _cache[key] = s
    return s


# --- search -----------------------------------------------------------------------------
def clip_bounds(p):
    return [float(np.clip(v, lo, hi)) for v, (lo, hi) in zip(p, BOUNDS)]


def main():
    args = sys.argv[1:]
    quick = "--quick" in args
    start = None
    for a in args:
        if a.startswith("--start"):
            start = [float(v) for v in a.split("=", 1)[1].split(",")]

    orig = A.load(ORIG)
    trim_orig = make_trim(orig)

    # --- target -------------------------------------------------------------------------
    cap = load_capture(f"{CAP_DIR}/{CAP_FILE}")
    cap, lag = A.align(cap, orig)
    target = shape(cap, orig)
    print(f"target: {CAP_FILE} [{SEG}], {BAND[0]:.0f}-{BAND[1]:.0f} Hz, "
          f"{len(FGRID)} log bins, align lag {lag}")

    # Level-independence check on the CAPTURE — this is what licenses a small-signal fit.
    alt = shape_at(cap, orig, "sweep_drv_-18")
    print(f"capture level-independence (this SEG vs sweep_drv_-18): "
          f"{cost_of(alt, target):.2f} dB RMS  (expect << 1)")

    t0 = time.time()
    nom = render_shape(NOMINAL, trim_orig, "nom")
    dt = time.time() - t0
    print(f"nominal cost = {cost_of(nom, target):.3f} dB RMS   ({dt:.1f} s/eval)\n")

    # --- coarse grid, log-spaced --------------------------------------------------------
    if start is None:
        grid = [np.geomspace(lo, hi, n) for (lo, hi), n in zip(BOUNDS, (7, 6, 5))]
        best, best_c = None, np.inf
        for i, p in enumerate(itertools.product(*grid)):
            c = cost_of(render_shape(list(p), trim_orig, "g"), target)
            if c < best_c:
                best, best_c = list(p), c
                print(f"  grid[{i:3d}] gm={p[0]*1e3:8.4f} mS  ro={p[1]/1e3:9.1f} k  "
                      f"rq2={p[2]/1e3:10.1f} k  -> {c:.3f} dB")
        print(f"\ncoarse best {best_c:.3f} dB")
        # Flag a grid-edge optimum explicitly: that was exactly how the previous ad-hoc scan
        # produced an untrustworthy gm, and it is easy to miss in a wall of numbers.
        for k, v, (lo, hi) in zip(KEYS, best, BOUNDS):
            if v <= lo * 1.001 or v >= hi * 0.999:
                print(f"  !! {k} sits ON its bound ({v:g}) — widen BOUNDS before trusting this")
    else:
        best, best_c = clip_bounds(start), None
        print(f"starting from {best}")

    if quick:
        report(best, target, trim_orig)
        return

    # --- Nelder-Mead refine in log space (all three span decades) -------------------------
    lb = np.log10([b[0] for b in BOUNDS])
    ub = np.log10([b[1] for b in BOUNDS])

    def f(z):
        p = 10.0 ** np.clip(z, lb, ub)
        return cost_of(render_shape(list(p), trim_orig, "n"), target)

    res = minimize(f, np.log10(best), method="Nelder-Mead",
                   options=dict(xatol=2e-3, fatol=2e-3, maxfev=250, disp=True))
    best = list(10.0 ** np.clip(res.x, lb, ub))
    print(f"\nrefined cost {res.fun:.3f} dB after {res.nfev} evals")
    report(best, target, trim_orig)


def shape_at(x, orig, seg):
    global SEG
    keep, SEG = SEG, seg
    try:
        return shape(x, orig)
    finally:
        SEG = keep


def report(best, target, trim_orig):
    print("\n" + "=" * 72)
    print("BEST FIT")
    for k, v, nom in zip(KEYS, best, NOMINAL):
        unit = "mS" if k == "jfetGm" else "kohm"
        sc = 1e3 if k == "jfetGm" else 1e-3
        print(f"  {k:9s} = {v*sc:12.4f} {unit:5s}  ({v/nom:6.3f}x nominal)")
    print(f"  gm*R6   = {best[0] * 3.3e3:.3f}   (nominal 2.277; << 1 means the C3 shelf "
          f"and the source degeneration are both essentially absent)")
    c = cost_of(render_shape(best, trim_orig, "best"), target)
    print(f"  cost    = {c:.3f} dB RMS shape error")

    # --- 1-D identifiability scans ------------------------------------------------------
    # A parameter whose cost barely moves across a decade is NOT measured by this data, and
    # its fitted value should be reported as such rather than committed as a finding.
    print("\n1-D scans about the optimum (cost, dB RMS):")
    for i, k in enumerate(KEYS):
        row = []
        for mul in (0.25, 0.5, 1.0, 2.0, 4.0):
            p = list(best)
            p[i] = float(np.clip(best[i] * mul, *BOUNDS[i]))
            row.append(f"{mul:>4g}x {cost_of(render_shape(p, trim_orig, 's'), target):5.2f}")
        print(f"  {k:9s} " + " | ".join(row))

    print("\nresidual shape error by frequency (render - capture, dB):")
    r = render_shape(best, trim_orig, "best") - target
    for f0 in (50, 82, 110, 200, 300, 500, 1000, 2000, 3000, 5000, 8000):
        i = int(np.argmin(np.abs(FGRID - f0)))
        print(f"  {f0:5d} Hz {r[i]:+6.2f}")
    print("\ncommit with:  --fit " + " --fit ".join(f"{k}={v:.6g}" for k, v in zip(KEYS, best)))


if __name__ == "__main__":
    main()
