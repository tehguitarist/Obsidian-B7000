#!/usr/bin/env python3.11
"""Phase-7 step 4 — validate `driveTaperExp` against the matched-pair DRIVE sweep, LEVEL-based.

Why this exists (dsp.md "Fit the taper SHAPE (p)", "Isolate a coupled control with a MATCHED-PAIR
capture"). Session 10's harmonic-to-harmonic fit (analysis/fit_nonlinear.py) returned
driveTaperExp = 5.45 as a BY-PRODUCT of a harmonic-ratio objective. dsp.md says the taper SHAPE
must be fitted against a matched-pair drive-sweep capture — a LEVEL measurement, orthogonal to the
harmonic ratios — before it can be committed, precisely so the fit can't have traded the taper
against the clipper/JFET gains without a capture noticing.

The matched pair we have: five `base-od` captures identical in EVERYTHING but DRIVE —
    drive-0700 (0.0) / drive-0930 (0.25) / ref-od (0.5) / drive-1430 (0.75) / drive-1700 (1.0)
all at BLEND = max-OD, LEVEL = noon. So the ONLY thing varying across them is the DRIVE gain, which
is exactly what the taper sets: driveResistance(x) = 100k*(1-x)^p, gain = 1 + 330k/(4.3k + Rd).

The orthogonal signal: the 1 kHz LEVEL-STEP ladder (`lvl_-36 .. lvl_-3`, gen_test_signal). At each
drive setting it traces a compression curve (output fundamental vs input level). Two features:
  * LOW input  -> the small-signal DRIVE gain: rises with the knob EXACTLY as the taper dictates.
                  This is the taper discriminator (bleed-free enough: the clean bleed is a fixed
                  drive-INDEPENDENT floor, so the spread ACROSS drives at a fixed low level is OD).
  * HIGH input -> every drive collapses onto the clipper ceiling (~-30.4 dB in the capture),
                  set by clipSatLo/Hi, NOT the taper. So the ceiling is a clipper check, not a taper
                  one; the taper score is weighted toward the drive-dependent (low/mid) levels.

Method. Hold the WHOLE step-3 set (s, a, ceilPos, ceilNeg, clipA0, clipSatLo/Hi + the step-2 held
gm/ro/rq2/levelTaperExp) fixed and vary ONLY driveTaperExp. Render the model's 1 kHz compression
grid (5 drives x N levels) with a synthetic level-ladder that mirrors gen_test_signal.tone(), and
compare to the capture grid. Two outputs:
  (1) PRIMARY validation — overlay the grid at driveTaperExp = 5.45 (the harmonic-fit value).
  (2) INDEPENDENT fit    — sweep p, score the grid, report the LEVEL-optimal p. If it lands near
      5.45 the harmonic-derived taper is corroborated by a measurement the harmonic fit never saw.

Run: /opt/homebrew/bin/python3.11 analysis/drive_taper_validate.py
"""
import sys, os, subprocess, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import analyze as A
from captures import parse_capture, render_args, load_capture, RENDER_BIN
from scipy.io import wavfile

FS = 48000
F0 = 1000.0
CAP = "analysis/captures"
LEVELS_DB = list(range(-36, -2, 3))   # -36,-33,...,-3  (== gen_test_signal LEVEL_STEPS_DB)

# The step-3 fitted set (analysis/fit_logs/step3_harmonic_ratio.log), held fixed; only
# driveTaperExp is varied by this script. gm/ro/rq2/levelTaperExp are the step-2 held values.
STEP3 = {
    "jfetSatPos": 0.22014, "jfetSatNeg": 0.91217,
    "jfetCeilPos": 6.0841, "jfetCeilNeg": 0.4619,
    "clipA0": 24.138, "clipSatLo": 1.9757, "clipSatHi": 2.419,
    "jfetGm": 0.10e-3, "jfetRo": 200.0e3, "jfetRq2": 1.0e6, "levelTaperExp": 2.25,
}
DRIVE_FIT_VALUE = 5.4463   # what fit_nonlinear.py returned; the value under test

DRIVE_CAPS = [
    ("drive-0700_base-od.wav", "min",  0.00),
    ("drive-0930_base-od.wav", "9:30", 0.25),
    ("ref-od.wav",             "noon", 0.50),
    ("drive-1430_base-od.wav", "2:30", 0.75),
    ("drive-1700_base-od.wav", "max",  1.00),
]

LADDER_IN = "/tmp/drive_taper_ladder.wav"
TONE_SEC = 0.6
GAP_SEC = 0.35
LEAD_SEC = 0.5


def _fund_db(seg):
    """1 kHz fundamental of a steady tone segment, in dBFS (edges trimmed)."""
    m = len(seg) // 6
    s = seg[m:-m]
    w = np.hanning(len(s))
    X = np.abs(np.fft.rfft(s * w))
    fr = np.fft.rfftfreq(len(s), 1 / FS)
    k = np.argmin(np.abs(fr - F0))
    return 20 * np.log10(X[max(0, k - 3):k + 4].max() / len(s) + 1e-20)


def capture_grid():
    """{drive_label: [fund dB at each LEVELS_DB]} from the real captures' lvl_ segments."""
    grid = {}
    for cap, lbl, _ in DRIVE_CAPS:
        c = load_capture(f"{CAP}/{cap}")
        grid[lbl] = [_fund_db(A.seg_of(c, f"lvl_{db}")) for db in LEVELS_DB]
    return grid


def make_ladder():
    """A synthetic 1 kHz level-ladder mirroring gen_test_signal.tone() (3 ms fade), one tone per
    LEVELS_DB entry, lead + gaps so the plug's per-block smoothers settle before each measured tone."""
    parts = [np.zeros(int(LEAD_SEC * FS))]
    bounds = []
    pos = LEAD_SEC
    n = int(TONE_SEC * FS)
    t = np.arange(n) / FS
    fade = int(0.003 * FS)
    env = np.ones(n); env[:fade] = np.linspace(0, 1, fade); env[-fade:] = np.linspace(1, 0, fade)
    for db in LEVELS_DB:
        x = (10.0 ** (db / 20.0)) * np.sin(2 * np.pi * F0 * t) * env
        parts.append(x)
        bounds.append((pos, pos + TONE_SEC))
        pos += TONE_SEC
        parts.append(np.zeros(int(GAP_SEC * FS)))
        pos += GAP_SEC
    wavfile.write(LADDER_IN, FS, np.concatenate(parts).astype(np.float32))
    return bounds


def render_grid(drive_exp, bounds):
    """{drive_label: [fund dB at each LEVELS_DB]} rendered through the model at driveTaperExp."""
    extra = ["--fit", f"driveTaperExp={drive_exp}"]
    for k, v in STEP3.items():
        extra += ["--fit", f"{k}={v:.9g}"]
    grid = {}
    for cap, lbl, _ in DRIVE_CAPS:
        parsed = parse_capture(cap)
        o = f"/tmp/drive_taper_{lbl.replace(':', '')}.wav"
        subprocess.run([RENDER_BIN, LADDER_IN, o, "--os", "8"] + render_args(parsed, extra),
                       check=True, capture_output=True)
        r = A.load(o)
        row = []
        for (t0, t1) in bounds:
            seg = r[int((t0 + 0.1) * FS):int(t1 * FS)]   # skip the 0.1s attack; measure the steady tail
            row.append(_fund_db(seg))
        grid[lbl] = row
    return grid


def small_signal_rise(grid):
    """Small-signal DRIVE gain vs the knob, in dB re drive-min, read at the LOWEST (most linear)
    input level. This is the taper discriminator with the clipper ceiling factored out."""
    base = grid["min"][0]
    return {lbl: grid[lbl][0] - base for lbl in grid}


def print_grid(title, grid):
    print(f"\n{title}")
    print("drive |" + "".join(f"{db:>6}" for db in LEVELS_DB))
    for _, lbl, _ in DRIVE_CAPS:
        print(f"{lbl:5s} |" + "".join(f"{v:6.1f}" for v in grid[lbl]))


def score(cap, mod):
    """Weighted RMS grid error (dB). Weight toward drive-dependent (low/mid) levels: the taper lives
    there. Weight per (drive,level) = the spread across drives at that level in the CAPTURE, so the
    saturated high-level columns (near-zero spread) contribute little and the ceiling-fit doesn't
    dominate the taper score. NOTE this ABSOLUTE score still folds in the (expected, step-5) makeup
    offset AND the compressed high-drive columns, so it is NOT the clean taper metric — see
    taper_score() for the offset-free/compression-free one that actually isolates p."""
    num = den = 0.0
    for j, _db in enumerate(LEVELS_DB):
        col = [cap[lbl][j] for _, lbl, _ in DRIVE_CAPS]
        w = np.std(col)                      # drive-sensitivity of this level
        for _, lbl, _ in DRIVE_CAPS:
            e = mod[lbl][j] - cap[lbl][j]
            num += w * e * e
            den += w
    return float(np.sqrt(num / den))


# The taper is a SMALL-SIGNAL DRIVE-gain shape. Isolate it from the two confounds the grid score
# can't shed: (1) the global makeup deficit (step-5, drive-independent) — killed by referencing
# every rise to drive-min; (2) clipper compression — killed by scoring ONLY the knob positions that
# are still linear at the lowest input. A capture column is "linear" when its lvl_-36 -> lvl_-33
# step is ~3 dB (input step); at higher drive the step collapses (compression) and the small-signal
# gain is masked. min/9:30/noon pass; 2:30/max do not. So the clean taper signal is the min-
# referenced rise at {9:30, noon} — offset-free, compression-free, and (bleed is a fixed floor the
# MODEL also reproduces) a like-for-like measurement of p.
LINEAR_LABELS = ["9:30", "noon"]   # confirmed linear at lvl_-36 (see linear_check())


def linear_check(cap):
    """Print each drive's lvl_-36 -> lvl_-33 step; ~3 dB == still linear (usable for the taper)."""
    print("\nLinearity at the low end (lvl_-36 -> lvl_-33 step; ~3.0 dB = linear, usable for taper):")
    for _, lbl, _ in DRIVE_CAPS:
        step = cap[lbl][1] - cap[lbl][0]
        tag = "linear" if step > 2.7 else "COMPRESSED — excluded"
        print(f"  {lbl:5s}: {step:+.1f} dB   ({tag})")


def taper_score(cap, mod):
    """RMS error (dB) of the min-referenced small-signal rise at the linear interior knob points.
    This is THE taper metric: offset-free, compression-free."""
    e2 = []
    for lbl in LINEAR_LABELS:
        rc = cap[lbl][0] - cap["min"][0]
        rm = mod[lbl][0] - mod["min"][0]
        e2.append((rm - rc) ** 2)
    return float(np.sqrt(np.mean(e2)))


def main():
    bounds = make_ladder()
    cap = capture_grid()
    print_grid("CAPTURE grid (1 kHz fundamental dBFS out; columns = input dBFS):", cap)
    linear_check(cap)
    print("\nCapture small-signal gain vs knob (dB re drive-min, at lvl_-36):")
    ssr_c = small_signal_rise(cap)
    print("  " + "  ".join(f"{lbl}:{ssr_c[lbl]:+.1f}" for _, lbl, _ in DRIVE_CAPS))

    # (1) PRIMARY — render at the harmonic-fit value.
    mod = render_grid(DRIVE_FIT_VALUE, bounds)
    print_grid(f"MODEL grid at driveTaperExp = {DRIVE_FIT_VALUE} (the harmonic-fit value):", mod)
    ssr_m = small_signal_rise(mod)
    print("\nModel small-signal gain vs knob (dB re drive-min, at lvl_-36):")
    print("  " + "  ".join(f"{lbl}:{ssr_m[lbl]:+.1f}" for _, lbl, _ in DRIVE_CAPS))
    print(f"\nAt p={DRIVE_FIT_VALUE}:  grid err {score(cap, mod):.2f} dB (absolute, confounded)   "
          f"CLEAN taper err {taper_score(cap, mod):.2f} dB (the metric)")

    # (2) INDEPENDENT fit — sweep p; report BOTH the confounded grid score and the clean taper score.
    print("\nIndependent LEVEL sweep of driveTaperExp:")
    print(f"  {'p':>5} | {'grid':>5} | {'TAPER':>5} | small-signal rise vs knob (dB re min)  "
          f"[capture 9:30:{ssr_c['9:30']:+.1f} noon:{ssr_c['noon']:+.1f}]")
    results = []
    for p in [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.5, 5.4463, 6.5]:
        g = render_grid(p, bounds)
        results.append((p, score(cap, g), taper_score(cap, g), g))
        ssr = small_signal_rise(g)
        print(f"  {p:>5.2f} | {results[-1][1]:>5.2f} | {results[-1][2]:>5.2f} | "
              + "  ".join(f"{lbl}:{ssr[lbl]:+.1f}" for _, lbl, _ in DRIVE_CAPS))
    best_grid = min(results, key=lambda r: r[1])
    best_taper = min(results, key=lambda r: r[2])
    print(f"\nCLEAN-taper-optimal p = {best_taper[0]:.2f}  (taper err {best_taper[2]:.2f} dB) "
          f"<- the trustworthy taper estimate")
    print(f"Confounded grid-optimal p = {best_grid[0]:.2f}  (grid err {best_grid[1]:.2f} dB) "
          f"<- pulled steep by compressed high-drive columns")
    print(f"Harmonic-fit p            = {DRIVE_FIT_VALUE:.2f}  (fit_nonlinear.py, session 10)")


if __name__ == "__main__":
    main()
