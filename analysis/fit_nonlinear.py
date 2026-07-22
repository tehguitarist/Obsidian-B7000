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
#
# ** `jfetG0` is GONE (2026-07-22 restructure) — it was a lumped voltage gain that silently
# absorbed the J201's output impedance and the treble net's loading. The stage is now a
# transconductance, so the gain parameter is the device `jfetGm` (S). Passing the old key
# makes OfflineRender fail loudly rather than fit something else; nothing here aliases it. **
#
# jfetGm is IN this fit, and jfetRo/jfetRq2 are NOT, on purpose — they are fit by different
# data and it matters which:
#   * gm sets the small-signal drain current, i.e. how hard the chain drives the clipper, and
#     the harmonic profile below is directly sensitive to that. It ALSO sets the degeneration
#     k0 = 1+gm*R6 (the C3 shelf), which analysis/fit_jfet_boundary.py measures from the
#     drive-min SHAPE. So gm is OVER-determined by two independent objectives — that is a
#     feature: if the two disagree, the model is wrong somewhere, and the disagreement is the
#     finding. Cross-check them; do not quietly average them.
#   * ro/rq2 only shape the loading, are near-inert in the harmonic profile, and would just
#     add two flat directions to this search. Held at HELD below (fit_jfet_boundary.py).
#
# ** jfetCeilPos/jfetCeilNeg ADDED 2026-07-22 — the whole reason for this re-run. **
# The previous run's failure was structural, not numerical: the J201 shaper had no
# ceiling, so H2 grew +21.9 dB across the drive sweep where the capture's grows +6,
# and the optimiser drove |a|*s into the monotonicity gate and clipA0 into its floor
# trying to manufacture a bound out of a shape that had none. The ceiling is now an
# explicit pair of params (gate-volt equivalent, x gm for amps; cutoff side and
# load-line side). Judge THIS run by whether |a|*s comes off the gate and clipA0 comes
# off its floor of 3 — if clipA0 still pins, the clipper is the next suspect, not the
# J201. Also worth checking, and deliberately NOT constrained here so it stays an
# independent corroboration: the square law ties the two together as 2*a*ceilNeg = 1.
FIT_KEYS = ["jfetGm", "jfetSatPos", "jfetSatNeg", "jfetCeilPos", "jfetCeilNeg",
            "clipA0", "clipSatLo", "clipSatHi", "driveTaperExp"]
NOMINAL  = [0.69e-3, 0.3, 1.0, 1.0, 0.5, 25.0, 3.15, 3.85, 1.5]
# Params held fixed at every eval, emitted explicitly so a render is never at the mercy of the
# binary's defaults. ** Update from analysis/fit_jfet_boundary.py once its result is committed;
# nominal until then. **
HELD = {"jfetRo": 200.0e3, "jfetRq2": 1.0e6}
# Bounds WIDENED 2026-07-22 after run 1 pinned jfetSatPos exactly at its old 6.0 ceiling and
# pushed clipSatLo (1.317) down near its old 1.2 floor — a param resting ON a bound means the
# optimum is outside the box, so the reported value is an artefact of the box, not a fit.
# clipSat* floors dropped because the R19-dropped 4049 rail is fitting LOWER than the nominal
# ~7 V sum.
#
# ** RESCALED 2026-07-22 with the restructure — the old jfetSat* ranges are meaningless now. **
# The shaper's argument is the effective vgs (REAL gate volts), not a post-gain voltage, so:
#   jfetGm     siemens. Datasheet 0.69 mS; the documented ~5:1 J201 spread plus a decade below
#              it, because the shape fit pushes that way and the box must not decide that.
#   jfetSatPos knee `s` in gate volts — order |Vp| (0.3-1.5 V for a J201), room either side.
#   jfetSatNeg even strength `a` (1/V) = 1/Vov. The real constraint is a PRODUCT/COUPLING,
#              not a box — enforced by monotonic() below.
#   jfetCeilPos load-line ceiling, gate-volt equivalent. Estimated 0.2-0.9 V at the nominal
#              gm and ~7.6x looser at the gm the shape fit prefers, so the box is wide.
#   jfetCeilNeg cutoff ceiling = Vov/2. Physically ties to `a` as 1/(2a); left free so that
#              identity stays an independent check on the result rather than an assumption.
BOUNDS   = [(1.0e-5, 5.0e-3), (0.05, 5.0), (0.0, 10.0), (0.05, 20.0), (0.05, 10.0),
            (3, 30), (0.4, 6.5), (0.4, 7.5), (0.4, 3.0)]
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
    for k, v in HELD.items():
        extra += ["--fit", f"{k}={v:.9g}"]
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


# ---- Monotonicity feasibility gate -----------------------------------------------
# A fold-back (negative slope) inside the signal range is unphysical AND scores
# spuriously well on H2, so it must be excluded explicitly — the bounds cannot do it,
# because the constraint is a coupling between parameters, not a box. This is not
# hypothetical: the 2026-07-22 run-2 best point was exactly such a fold-back.
#
# ** The gate is now a NUMERIC SCAN, not a closed-form product bound. ** With the
# drain-current ceiling in place (JfetStage.h, 2026-07-22) the shipped map is
#     g(w)  = L*tanh(w/L) + (a*s^2/2)*tanh^2(w/s),   L = ceilPos (w>=0) / ceilNeg (w<0)
#     g'(w) = sech^2(w/L) + a*s*tanh(w/s)*sech^2(w/s)
# so the old |a|*s < C test is NECESSARY but no longer SUFFICIENT: the ceiling drags
# the first term below 1 exactly where the second term is most negative, which couples
# s, a AND the ceilings (roughly ceilNeg >~ s; below that the map folds back deep in
# cutoff). For reference the ceiling-OFF closed form is |a|*s < 3*sqrt(3)/2 = 2.598,
# from max|tanh*sech^2| = 2/(3*sqrt(3)) — that is this bump's extremum, NOT the 2.0
# that belonged to the old sech bump. Verified numerically in C++: |a|*s = 2.5 gives
# min slope +0.038, 2.7 gives -0.039.
#
# NOTE this is a REPLICA of JfetStage::waveshape()'s derivative. The C++ side is the
# source of truth (JfetStageTest finite-differences the shipped map); if the shaper
# changes shape again, this must change with it.
# A saturating map's slope legitimately decays to zero far out in the tail, so the
# test is "never NEGATIVE", not "always positive".
_W = np.concatenate([np.linspace(-60, 60, 24001), np.linspace(-3, 3, 6001)])


def min_slope(s, a, cp, cn):
    L = np.where(_W >= 0.0, cp, cn)
    ceil_slope = np.where(L >= 1.0e6, 1.0, 1.0 / np.cosh(np.clip(_W / L, -350, 350)) ** 2)
    x = np.clip(_W / s, -350, 350)
    bump_slope = a * s * np.tanh(x) / np.cosh(x) ** 2
    return float(np.min(ceil_slope + bump_slope))


def monotonic(params):
    g = dict(zip(FIT_KEYS, params))
    return min_slope(g["jfetSatPos"], g["jfetSatNeg"],
                     g["jfetCeilPos"], g["jfetCeilNeg"]) > -1.0e-9


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
    # Starts RESCALED for the restructured stage (gm in siemens, s/a in gate volts). The three
    # gm values deliberately straddle the open question: datasheet-nominal, the decade-lower
    # value the drive-min SHAPE fit prefers (fit_jfet_boundary.py), and the midpoint — so this
    # objective gets to vote on gm independently instead of inheriting the shape fit's answer.
    # Ceiling starts (cols 4/5) straddle "loose" and "biting": the whole question this
    # run answers is whether the fit WANTS a tight J201 ceiling. Start 1 is nominal,
    # start 2 pairs the low gm with a tight cutoff ceiling, start 3 starts nearly
    # unbounded so the optimiser has to earn the ceiling rather than inherit it.
    starts = [
        [0.69e-3, 0.3, 1.0, 1.0, 0.5, 25, 3.15, 3.85, 1.0],
        [0.09e-3, 0.2, 2.0, 0.5, 0.3, 20, 3.0, 3.6, 1.2],
        [0.22e-3, 0.5, 0.8, 6.0, 3.0, 15, 3.0, 4.0, 0.8],
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
    # %g, not %7.3f — jfetGm is ~7e-4 and a fixed-point format prints it as "0.001".
    for k, v, nom in zip(FIT_KEYS, best.x, NOMINAL):
        print(f"  {k:12s} {v:12.5g}   (nominal {nom:g})")
    print(f"  held: " + ", ".join(f"{k}={v:g}" for k, v in HELD.items()))

    # ---- Acceptance diagnostics -------------------------------------------------
    # The previous run was rejected by exactly these, so print them rather than
    # leaving them to be re-derived by hand from the parameter dump.
    g = dict(zip(FIT_KEYS, best.x))
    print("\nAcceptance checks (phase7-calibration-handover.md, 'STEP 2 RE-FIT'):")
    print(f"  |a|*s          = {abs(g['jfetSatNeg']) * g['jfetSatPos']:.4f}   "
          f"(was PINNED at the 1.9997 gate -> must now be off it)")
    print(f"  min slope      = {min_slope(g['jfetSatPos'], g['jfetSatNeg'], g['jfetCeilPos'], g['jfetCeilNeg']):+.3e}   "
          f"(>= 0; a fold-back is infeasible)")
    a0pin = " ** STILL PINNED -> suspect the CLIPPER, not the J201 **" if g["clipA0"] < 3.05 else ""
    print(f"  clipA0         = {g['clipA0']:.3f}   (floor 3.0; circuit.md says 20-30){a0pin}")
    print(f"  clipSatLo+Hi   = {g['clipSatLo'] + g['clipSatHi']:.3f} V   (R19-dropped rail ~7 V)")
    print(f"  jfetGm         = {g['jfetGm'] * 1e3:.4f} mS   "
          f"(drive-min SHAPE fit + level cross-check say ~0.090 mS)")
    print(f"  2*a*ceilNeg    = {2 * g['jfetSatNeg'] * g['jfetCeilNeg']:.3f}   "
          f"(square law says 1.0 — NOT constrained in the fit, so this is a real check)")
    print(f"  ceilNeg / s    = {g['jfetCeilNeg'] / g['jfetSatPos']:.2f}   "
          f"(monotonicity needs >~ 1; resting AT 1 means the ceiling is on a constraint)")
    # 1% of the bound, not 0.1%: Nelder-Mead stops NEAR a bound it is pushing against
    # rather than exactly on it (the 2026-07-22 ceiling run returned driveTaperExp
    # 2.9938 against a ceiling of 3.0 — 0.2% off, and a 0.1% test missed it).
    for k, v, (lo, hi) in zip(FIT_KEYS, best.x, BOUNDS):
        if abs(v - lo) < 1e-2 * max(abs(lo), 1e-9) or abs(v - hi) < 1e-2 * abs(hi):
            print(f"  ** {k} is RESTING ON ITS BOUND ({v:g} in [{lo:g}, {hi:g}]) — the optimum is "
                  f"outside the box, so this value is a property of the box, not the pedal. **")

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
