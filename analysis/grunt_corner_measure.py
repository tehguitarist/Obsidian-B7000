#!/usr/bin/env python3.11
"""Phase-7 SESSION 17 — BLEED-FREE measurement of the GRUNT high-pass CORNERS -> clipA0 and clipC11.

WHY. The session-17 joint fit closed the drive-sweep ramp but landed clipA0 = 15.8 (below
circuit.md's 20-30 prior) and clipC11 = 7.0 nF, with a gm-fragile noon. clipA0 and clipC11 are
DEGENERATE in a single-position fit (both move the GRUNT=Cut corner), so the fit's values are not,
on their own, a measurement. This script breaks the degeneracy with an INDEPENDENT measurement that
the fit never saw: the GRUNT corner FREQUENCIES across all three switch positions.

THE KEY. The three GRUNT positions share ONE finite-gain input impedance R18/(1+A0) but differ by
KNOWN cap steps (Cg_cut = C11, Cg_flat = C11+C12, Cg_boost = C11+C13, with C12/C13 schematic-fixed).
Three corners therefore OVER-DETERMINE the two unknowns (A0, C11) — a corner ratio pins A0
independently of any absolute level. The clipper's small-signal transfer (an inverting amp with
finite open-loop gain A0) is:
    Cclip_i(f) = -(Zf/Zin_i) * A0/(A0 + 1 + Zf/Zin_i),
        Zin_i = R16 + 1/(jw*Cg_i),   Zf = R18 || (1/(jw*C14))
and A0 here IS clipA0's meaning (FitParams: clipA0 sets BOTH the closed-loop gain AND the input
impedance R18/(1+A0)).

BLEED-FREE, GAIN-FREE, LEVEL-FREE ESTIMATOR. In a base-od capture the output fundamental is
    Y_i(f) = X(f) * D(f) * [ alpha * Cclip_i(f) + beta * Hclean(f) ]
X = input sweep, D = the common downstream linear chain (recovery/SK/LEVEL/BLEND/EQ/master), alpha =
blend OD coefficient, beta*Hclean = the drive/grunt-INDEPENDENT clean BLEND bleed. The JFET + treble
net upstream of the clipper are grunt-independent and fold into a common factor too. So DIFFERENCES
cancel the bleed, and the RATIO of differences cancels EVERYTHING except the clipper transfers:
    R_bf(f) = (Y_boost - Y_cut) / (Y_flat - Y_cut) = (Cclip_boost - Cclip_cut)/(Cclip_flat - Cclip_cut)
This depends ONLY on (A0, C11). No reference sweep, no bleed model, no EQ model, no level calibration,
no clipper VTC, no makeup enters the answer. It is measured at DRIVE-MIN where the clipper is ~linear
(cut H3-H2 = -23.2 dB, essentially no distortion), and cross-checked at drive-9:30.

⚠ ALIGNMENT (the session-16 trap). A residual delay tau rotates Y_i(f) by exp(-j2pi f tau); the
DIFFERENCE Y_i - Y_cut is sensitive to it. Each take is a separate recording, so each is frac_align'd
to the reference sweep to sub-sample precision (reused pipeline). The three drive-min takes are all at
the SAME drive, so the drive-dependent-lag trap does not apply between them; taus are reported anyway.
A magnitude-only estimator (|R_bf|, which the differences still need alignment to form but which drops
the final phase) runs alongside the complex one — agreement means alignment is not driving the answer.

L-006 SELF-TEST. The identical pipeline runs first on MODEL renders with a KNOWN (clipA0, clipC11).
It must recover them. If it does not, the estimator is broken and the capture numbers mean nothing.

Run:  /opt/homebrew/bin/python3.11 analysis/grunt_corner_measure.py
Log:  analysis/fit_logs/step7_grunt_corner_measure.log
"""
import sys, os, subprocess, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from scipy import signal as sps
from scipy.optimize import least_squares
import analyze as A
import gen_test_signal as G
from captures import parse_capture, render_args, RENDER_BIN

FS = 48000
ORIG = "analysis/test_signal_48k.wav"
LOG = "analysis/fit_logs/step7_grunt_corner_measure.log"
T = G.segment_times()

# Clipper circuit facts (Clipper.h / circuit.md CLIPPER section).
R16, R18, C14 = 6.8e3, 330.0e3, 220.0e-12
C12, C13 = 47.0e-9, 220.0e-9          # GRUNT deltas — schematic-FIXED (only C11 is in question)

# The GRUNT triads at each drive. gruntIdx: 0=Boost, 1=Cut, 2=Flat.
DRIVE_SETS = {
    "min": dict(x=0.0, cut="drive-0700_base-od.wav",
                flat="drive-0700_grunt-flat_base-od.wav", boost="drive-0700_grunt-boost_base-od.wav"),
    "9:30": dict(x=0.25, cut="drive-0930_base-od.wav",
                 flat="drive-0930_grunt-flat_base-od.wav", boost="drive-0930_grunt-boost_base-od.wav"),
}
CAPDIR = "analysis/captures"

# Sweep segment used for the transfer difference. sweep_drv_-18 = the lowest driven sweep -> most
# linear at drive-min while still carrying enough OD level for the (boost-cut) difference SNR.
SWEEP_SEG = "sweep_drv_-18"
# Band: extend DOWN to 25 Hz (the corners are LOW if the coupling is large / A0 is small — a single
# corner can't separate C11 from A0, but the corner RATIOS across positions can, and those ratios
# only resolve where the corners actually sit). Drop the HF end at 1500: above ~the cut corner all
# three positions reach a common plateau, so (boost-cut) and (flat-cut) both -> 0 and R_bf is 0/0.
FIT_LO, FIT_HI = 25.0, 1500.0
HF_ALIGN_HZ = 3000.0                   # relative-delay is estimated from >this (positions identical)

# Self-test ground truth (rendered, then recovered):
SELF_A0, SELF_C11 = 22.0, 6.0e-9
HELD = dict(jfetGm=0.10e-3, jfetRo=200e3, jfetRq2=1e6, levelTaperExp=2.25, driveTaperExp=1.98,
            clipSatLo=2.5, clipSatHi=3.5, clipK=1.8, jfetExpandBeta=1.8)


# ------------------------------------------------------------------ clipper transfer
def cclip(f, A0, Cg):
    """Small-signal transfer of the CD4049 inverter for input cap Cg. Complex, vectorised over f."""
    w = 2.0 * np.pi * np.asarray(f, dtype=float)
    Zin = R16 + 1.0 / (1j * w * Cg)
    Zf = R18 / (1.0 + 1j * w * R18 * C14)
    k = Zf / Zin
    return -k * A0 / (A0 + 1.0 + k)


def model_Rbf(f, A0, C11):
    cut = cclip(f, A0, C11)
    flat = cclip(f, A0, C11 + C12)
    boost = cclip(f, A0, C11 + C13)
    return (boost - cut) / (flat - cut)


# ------------------------------------------------------------------ alignment (reused pattern)
def frac_align(sig, ref):
    """Integer align on the 'sweep_clean' anchor, then parabolic sub-sample refine + phase-ramp."""
    a, b = T["sweep_clean"]
    r = ref[int(a * FS):int(b * FS)]
    s0 = sig[int(a * FS):int(min(len(sig), (b + 0.5) * FS))]
    n = min(len(r), len(s0))
    rr, ss = r[:n] - r[:n].mean(), s0[:n] - s0[:n].mean()
    corr = sps.correlate(ss, rr, mode="full", method="fft")
    k = int(np.argmax(np.abs(corr)))
    lag = k - (n - 1)
    frac = 0.0
    if 0 < k < len(corr) - 1:
        y0, y1, y2 = abs(corr[k - 1]), abs(corr[k]), abs(corr[k + 1])
        den = y0 - 2 * y1 + y2
        if abs(den) > 1e-30:
            frac = 0.5 * (y0 - y2) / den
    total = lag + frac
    N = len(sig)
    Fv = np.fft.rfft(sig)
    wv = 2 * np.pi * np.fft.rfftfreq(N)
    return np.fft.irfft(Fv * np.exp(1j * wv * total), n=N), total


# ------------------------------------------------------------------ spectra + ratio
def _seg(sig, seg_name):
    a, b = T[seg_name]
    return sig[int(a * FS):int(b * FS)]


# log-frequency analysis grid + band edges (1/12-octave — many FFT bins per band => real
# noise reduction on the real captures, where per-bin SNR on a 10 s log sweep is poor).
def _log_grid(lo, hi, per_oct=12):
    n = int(np.ceil(np.log2(hi / lo) * per_oct))
    f = lo * 2.0 ** (np.arange(n + 1) / per_oct)
    centres = np.sqrt(f[:-1] * f[1:])
    return centres, f


def band_transfer(y, x, seg_name, grid):
    """Deconvolved, log-band-averaged complex transfer T(f)=Y/X on the grid centres.

    Dividing by the reference sweep spectrum X removes the sweep's own (rapid) phase, so complex
    band-averaging is valid; averaging many bins per 1/12-oct band is the noise reduction the raw
    9-bin linear smooth lacked. eps-regularised where |X| is small (sweep band edges)."""
    ys, xs = _seg(y, seg_name), _seg(x, seg_name)
    n = min(len(ys), len(xs))
    win = np.hanning(n)
    Y = np.fft.rfft(ys[:n] * win)
    X = np.fft.rfft(xs[:n] * win)
    fr = np.fft.rfftfreq(n, 1.0 / FS)
    eps = 1e-6 * np.median(np.abs(X)) + 1e-30
    Tf = Y / np.where(np.abs(X) > eps, X, np.inf)    # 0 where X has no energy (no div warning)
    centres, edges = grid
    out = np.zeros(len(centres), dtype=complex)
    wq = np.zeros(len(centres))
    for i in range(len(centres)):
        m = (fr >= edges[i]) & (fr < edges[i + 1]) & (np.abs(X) > eps)
        if m.any():
            out[i] = Tf[m].mean()
            wq[i] = np.abs(X[m]).mean()      # band SNR proxy = reference energy there
    return centres, out, wq


def relative_align(target, refsig, seg_name):
    """Align `target` to `refsig` on the sweep segment (sub-sample). This is the ONLY alignment
    that matters for R_bf: the difference (Y_i - Y_cut) needs cut/flat/boost on a common time base,
    NOT aligned to the clean reference. Aligning OD-processed captures to the CLEAN sweep is biased
    because each GRUNT position filters the sweep differently (the +3.15 smp boost tau of the
    each-to-ref approach). Cross-correlating the near-identical OD sweeps directly is robust."""
    a, b = T[seg_name]
    r = refsig[int(a * FS):int(b * FS)]
    s = target[int(a * FS):int(b * FS)]
    n = min(len(r), len(s))
    rr, ss = r[:n] - r[:n].mean(), s[:n] - s[:n].mean()
    # HIGH-PASS both before correlating: the GRUNT positions differ only BELOW their corners, so a
    # full-band cross-correlation biases the delay by the very difference we are measuring. Above
    # HF_ALIGN_HZ the positions are identical, so the delay estimate there is unbiased.
    sos = sps.butter(4, HF_ALIGN_HZ / (FS / 2), btype="high", output="sos")
    rr, ss = sps.sosfilt(sos, rr), sps.sosfilt(sos, ss)
    corr = sps.correlate(ss, rr, mode="full", method="fft")
    k = int(np.argmax(np.abs(corr)))
    lag = k - (n - 1)
    frac = 0.0
    if 0 < k < len(corr) - 1:
        y0, y1, y2 = abs(corr[k - 1]), abs(corr[k]), abs(corr[k + 1])
        den = y0 - 2 * y1 + y2
        if abs(den) > 1e-30:
            frac = 0.5 * (y0 - y2) / den
    total = lag + frac
    N = len(target)
    Fv = np.fft.rfft(target)
    wv = 2 * np.pi * np.fft.rfftfreq(N)
    return np.fft.irfft(Fv * np.exp(1j * wv * total), n=N), total


def measured_Rbf(cut, flat, boost, ref, seg_name=None):
    """R_bf(f) via deconvolved, log-band transfers. cut is absolute-aligned to the reference (for
    Y/X); flat/boost are relative-aligned to cut (only their RELATIVE delay corrupts the ratio)."""
    seg_name = seg_name or SWEEP_SEG
    ca, ta = frac_align(cut, ref)                    # absolute -> enables clean Y/X deconvolution
    fa, tf = relative_align(flat, ca, seg_name)      # relative to cut: kills per-take jitter
    ba, tb = relative_align(boost, ca, seg_name)
    grid = _log_grid(FIT_LO, FIT_HI)
    fr, Tc, wq = band_transfer(ca, ref, seg_name, grid)
    _, Tf, _ = band_transfer(fa, ref, seg_name, grid)
    _, Tb, _ = band_transfer(ba, ref, seg_name, grid)
    num, den = Tb - Tc, Tf - Tc
    R = num / den
    wgt = np.abs(den) * (wq / (wq.max() + 1e-30))    # weight by both diff strength AND band SNR
    wgt = wgt / (wgt.max() + 1e-30)
    return fr, R, wgt, (ta, tf, tb)


# ------------------------------------------------------------------ fit (A0, C11)
def fit_A0_C11(fr, R, wgt, complex_fit=True):
    """Least-squares (A0, C11) to measured R_bf. complex_fit=False -> magnitude-only."""
    m = wgt > 0.05
    frm, Rm, wm = fr[m], R[m], np.sqrt(wgt[m])

    def resid(p):
        A0, c11n = p
        Rmod = model_Rbf(frm, A0, c11n * 1e-9)
        if complex_fit:
            d = (Rmod - Rm) * wm
            return np.concatenate([d.real, d.imag])
        return (np.abs(Rmod) - np.abs(Rm)) * wm

    sol = least_squares(resid, [20.0, 5.0], bounds=([2.0, 1.0], [45.0, 100.0]),
                        method="trf", max_nfev=20000)
    return sol.x[0], sol.x[1], float(np.sqrt(np.mean(sol.fun ** 2)))


# ------------------------------------------------------------------ model self-test render
def render_grunt(x, grunt_cap, out):
    parsed = parse_capture(grunt_cap)      # picks up the right gruntIdx from the filename
    parsed["drive"] = x
    extra = []
    for k, v in HELD.items():
        extra += ["--fit", f"{k}={v:.9g}"]
    extra += ["--fit", f"clipA0={SELF_A0:.9g}", "--fit", f"clipC11={SELF_C11:.9g}"]
    subprocess.run([RENDER_BIN, ORIG, out, "--os", "8"] + render_args(parsed, extra),
                   check=True, capture_output=True)
    return A.load(out)


# ------------------------------------------------------------------ main
def main():
    os.makedirs("analysis/fit_logs", exist_ok=True)
    log = open(LOG, "w")

    def emit(s=""):
        print(s)
        log.write(s + "\n")

    emit("=" * 96)
    emit("GRUNT high-pass CORNER measurement -> independent clipA0 & clipC11 (session 17)")
    emit("=" * 96)
    emit("Estimator: R_bf(f) = (Yboost-Ycut)/(Yflat-Ycut) = (Cboost-Ccut)/(Cflat-Ccut), a function")
    emit("of ONLY (A0, C11). Bleed, blend, downstream chain, input sweep, JFET all cancel. Measured")
    emit(f"at DRIVE-MIN (clipper ~linear), band [{FIT_LO:.0f}, {FIT_HI:.0f}] Hz, sweep '{SWEEP_SEG}'.")
    emit(f"Fixed: R16={R16/1e3:.1f}k R18={R18/1e3:.0f}k C14={C14*1e12:.0f}p  C12={C12*1e9:.0f}n "
         f"C13={C13*1e9:.0f}n (schematic).  Fit clipA0=15.8 / clipC11=7.0nF; circuit.md A0 20-30.")
    emit("")

    ref = A.load(ORIG)

    # ---- L-006 SELF-TEST ---------------------------------------------------------------
    emit("-" * 96)
    emit(f"L-006 SELF-TEST — recover a KNOWN model (clipA0={SELF_A0}, clipC11={SELF_C11*1e9:.1f}nF)")
    emit("-" * 96)
    s = DRIVE_SETS["min"]
    mc = render_grunt(s["x"], s["cut"], "/tmp/gcm_mcut.wav")
    mf = render_grunt(s["x"], s["flat"], "/tmp/gcm_mflat.wav")
    mb = render_grunt(s["x"], s["boost"], "/tmp/gcm_mboost.wav")
    emit(f"  Truth: A0={SELF_A0}, C11={SELF_C11*1e9:.1f}nF. Sweeping sweep segments to find the")
    emit(f"  LINEAR one (lower level -> less clipping -> the difference is bleed-free AND clip-free):")
    emit(f"  {'segment':>16} | {'A0 cx':>7} {'C11 cx':>7} | {'A0 mag':>7} {'C11 mag':>7} | rms | verdict")
    best = None
    for seg in ["sweep_clean_-36", "sweep_clean", "sweep_drv_-18", "sweep_drv_-12"]:
        if seg not in T:
            continue
        fr, R, wgt, taus = measured_Rbf(mc, mf, mb, ref, seg)
        a0c, c11c, rmsc = fit_A0_C11(fr, R, wgt, complex_fit=True)
        a0m, c11m, rmsm = fit_A0_C11(fr, R, wgt, complex_fit=False)
        eA = abs(a0c - SELF_A0) / SELF_A0
        eC = abs(c11c - SELF_C11 * 1e9) / (SELF_C11 * 1e9)
        # A0 is the scientifically decisive number (is the real pedal ~16 or ~25?); the estimator
        # recovers it to <2% at the linear levels. C11 is softer (a single-bin smoothing wrinkle
        # near the flat corner costs ~12%), and ~20% on C11 is ample to tell 4.7 from 7 from 12 nF.
        vok = eA < 0.08 and eC < 0.20
        emit(f"  {seg:>16} | {a0c:>7.2f} {c11c:>7.2f} | {a0m:>7.2f} {c11m:>7.2f} | {rmsc:.1e} | "
             f"A0 {eA*100:4.1f}% C11 {eC*100:4.1f}%  {'OK' if vok else 'biased'}")
        if vok and best is None:
            best = seg
    emit("")
    # measured-vs-true R_bf dump on the best (or lowest) segment, to localise any residual bias
    diag_seg = best or "sweep_clean_-36"
    fr, R, wgt, _ = measured_Rbf(mc, mf, mb, ref, diag_seg)
    Rt = model_Rbf(fr, SELF_A0, SELF_C11)
    emit(f"  measured vs TRUE R_bf on '{diag_seg}' (should match if the estimator is unbiased):")
    emit(f"  {'f(Hz)':>7} | {'|meas|':>7} {'|true|':>7} | {'phase meas':>10} {'phase true':>10}")
    for ftgt in (100, 200, 400, 700, 1200, 2000, 3000):
        idx = int(np.argmin(np.abs(fr - ftgt)))
        emit(f"  {fr[idx]:>7.0f} | {abs(R[idx]):>7.3f} {abs(Rt[idx]):>7.3f} | "
             f"{np.degrees(np.angle(R[idx])):>9.1f}d {np.degrees(np.angle(Rt[idx])):>9.1f}d")
    emit("")
    if best is None:
        emit("  ** SELF-TEST FAILED at every level — estimator biased regardless of clipping. STOP. **")
        log.close(); print(f"[log] {LOG}"); return 2
    emit(f"  SELF-TEST PASSED on '{best}' — using it for the capture measurement below.")
    globals()["SWEEP_SEG"] = best
    emit("")

    # ---- THE MEASUREMENT ---------------------------------------------------------------
    emit("-" * 96)
    emit("MEASUREMENT — the REAL pedal's GRUNT corners")
    emit("-" * 96)
    emit(f"  Using SWEEP_SEG='{SWEEP_SEG}' (self-test winner); also reporting the runner-up level.")
    emit(f"  {'drive':>5} {'seg':>16} | {'A0 cx':>7} {'A0 mag':>7} | {'C11 cx':>7} {'C11 mag':>7} | "
         f"{'cut fc':>7} | rms   | rel-taus f/b")
    results = {}
    for lbl, s in DRIVE_SETS.items():
        paths = [f"{CAPDIR}/{s[k]}" for k in ("cut", "flat", "boost")]
        if not all(os.path.exists(p) for p in paths):
            emit(f"  {lbl:>5} | MISSING one of {paths}")
            continue
        cut, flat, boost = (A.load(p) for p in paths)
        for seg in [SWEEP_SEG, "sweep_clean" if SWEEP_SEG != "sweep_clean" else "sweep_clean_-36"]:
            fr, R, wgt, taus = measured_Rbf(cut, flat, boost, ref, seg)
            a0c, c11c, rmsc = fit_A0_C11(fr, R, wgt, complex_fit=True)
            a0m, c11m, rmsm = fit_A0_C11(fr, R, wgt, complex_fit=False)
            Z = R18 / (1.0 + a0c)
            fc = 1.0 / (2 * np.pi * (c11c * 1e-9) * (R16 + Z))
            emit(f"  {lbl:>5} {seg:>16} | {a0c:>7.2f} {a0m:>7.2f} | {c11c:>7.2f} {c11m:>7.2f} | "
                 f"{fc:>6.0f}H | {rmsc:.1e} | {taus[1]:+.2f}/{taus[2]:+.2f}")
            if seg == SWEEP_SEG:
                results[lbl] = (a0c, c11c, a0m, c11m)
                # shape dump on the primary segment for the min drive
                if lbl == "min":
                    Rt = model_Rbf(fr, a0c, c11c * 1e-9)
                    emit(f"        measured vs FITTED-model R_bf (|.| and phase):")
                    for ftgt in (100, 200, 400, 700, 1200, 2000, 3000):
                        idx = int(np.argmin(np.abs(fr - ftgt)))
                        emit(f"          {fr[idx]:>6.0f}Hz  |meas| {abs(R[idx]):5.2f} |mdl| {abs(Rt[idx]):5.2f}"
                             f"   ph {np.degrees(np.angle(R[idx])):+6.1f} / {np.degrees(np.angle(Rt[idx])):+6.1f}"
                             f"   w {wgt[idx]:.2f}")
        emit("")

    emit("=" * 96)
    emit("READ-OUT")
    emit("=" * 96)
    if "min" in results and "9:30" in results:
        a0_min, c11_min = results["min"][0], results["min"][1]
        a0_930, c11_930 = results["9:30"][0], results["9:30"][1]
        emit(f"  A0:  drive-min {a0_min:.1f}   drive-9:30 {a0_930:.1f}   "
             f"(a LINEAR corner must NOT move with drive — agreement validates the read)")
        emit(f"  C11: drive-min {c11_min:.2f} nF   drive-9:30 {c11_930:.2f} nF")
        emit("")
        emit(f"  vs the joint fit (clipA0 15.8, clipC11 7.0 nF) and circuit.md's A0 20-30 prior:")
        emit(f"    - If measured A0 ~ 16 and C11 ~ 7 nF: the fit is CORROBORATED; the 20-30 prior is")
        emit(f"      wrong for THIS unit (R19-dropped supply lowers the 4049 gain). Accept, then ship.")
        emit(f"    - If measured A0 ~ 25 (in prior) and C11 larger: the fit's low A0 was compensating;")
        emit(f"      re-fit with clipA0 fenced to [20,30] and C11 free.")
        emit(f"    - If A0 disagrees between drives: the drive-min clipper was not linear enough or the")
        emit(f"      alignment failed — do NOT trust either number; report and reconsider.")
    log.close()
    print(f"\n[log] {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
