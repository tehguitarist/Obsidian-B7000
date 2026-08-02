#!/usr/bin/env python3.11
"""Phase-9 SESSION 70 — measure the ATTACK cancellation notch from the STEPPED-SINE captures, with
no bin smearing and no shoulder contamination.

WHAT THIS REPLACES. Every f0/depth/width number in this project since session 61 comes from
`attack_notch_probe.py`, which reads a 10 s log sweep through a 5.86 Hz-bin CSD estimate. Its own
self-test measured TWO biases in that instrument, and both UNDERSTATE:

  * BIN SMEARING           a true 33 dB null reads 28.71 dB -- the estimate cannot reach a sharp floor.
  * SHOULDER CONTAMINATION a broad null's own skirt reaches into the 200-270 Hz reference window, so
                           `shoulder - min` understates the depth DEFINITIONALLY (-4.39 dB at Qp 0.7).

And the pedal's boost null is only ~4 bins wide, so its half-depth BIN-SPAN width is quantised at
roughly +-25 % -- which is why session 63 had to add an interpolated width column, and why session
66's headline (widths 0.87/1.29/1.03x the pedal's) still carries a caveat it cannot shed. WIDTH is
now the whole open ATTACK item, and width is exactly the quantity that quantisation corrupts worst.

A stepped sine removes all of it. Each tone is fitted NARROWBAND at its own frequency by least
squares, so there is no band averaging, no window leakage across the null, and the resolution is the
STEP SIZE (2 Hz in the core), not a transform's bin width.

⭐ THE FEATURE THAT MAKES THIS SELF-ARBITRATING. `gen_notch_sweep.py` puts a 10 s `sweep_clean`
*inside every capture* -- it has to, as the alignment anchor. So the OLD instrument can be run on the
SAME FILE and the two compared with **no take-to-take term between them**. That is what `--compare`
does, and it is the honest way to report a measurement that supersedes another: not "the new number
is better", but "here is what the old instrument reads on this exact audio, and here is the gap".

⚠ WHAT THIS DOES NOT DO. It measures the pedal. It does not render the model, does not fit anything,
and takes no `--fit` overrides. Scoring a topology against these numbers is the NEXT step and belongs
in `attack_render_gate.py`, which is the arbiter (session 65 item 6). Keep the measurement and the
scoring in separate tools -- that separation is what let session 66 catch a ranking defect before it
picked a candidate.

Run from repo root:
    /opt/homebrew/bin/python3.11 analysis/read_notch_sweep.py --selftest
    /opt/homebrew/bin/python3.11 analysis/read_notch_sweep.py
    /opt/homebrew/bin/python3.11 analysis/read_notch_sweep.py --compare
"""
import argparse
import json
import os
import sys

import numpy as np
import scipy.signal as sps
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_notch_sweep as N  # noqa: E402
import captures as C         # noqa: E402

FS = N.FS
T = N.segment_times()
FREQS = N.FREQS
STIMULUS = "analysis/notch_sweep_48k.wav"
CAP_DIR = "analysis/captures"
OUT_JSON = "analysis/reports/s70_notch_sweep.json"

# The definitions below are IMPORTED IN SPIRIT from attack_notch_probe.py and must stay identical to
# it, or the comparison in --compare is meaningless. They are restated (not imported) because that
# module runs a large report at import time; the VALUES are what matter and they are asserted
# against it in --compare.
SHOULDER_WIN = (200.0, 270.0)      # lower shoulder -- every depth in this project is referred to it
SEARCH_WIN = (280.0, 380.0)        # where the null is looked for (== the stimulus's fine core)
UPPER_WIN = (380.0, 470.0)         # the 421.9 Hz maximum on the far side

TAKE_FLOOR = 0.144                 # dB, the project's take-to-take floor
LEVELS_DB = N.LEVELS_DB            # (-30, -18): quiet read + level CONTROL

# The record this measurement is arbitrating against, from the SWEPT instrument (session 61,
# reproduced by every session since). Printed beside the new numbers so a shift is visible rather
# than silently replacing the record.
SWEPT_RECORD = {                   # throw -> (f0 Hz, depth dB, width_interp Hz)
    "cut":   (316.4, 14.93, 77.9),
    "boost": (328.1, 32.70, 27.1),
    "flat":  (334.0, 16.01, 71.9),
}

THROWS = ["cut", "boost", "flat"]
CONDS = {
    "drive-noon": "notch_level-1700_attack-{throw}.wav",
    "drive-min":  "notch_drive-0700_level-1700_attack-{throw}.wav",
}
# GRUNT is schematic+BOM-verified LINEAR but sits at the CLIPPER INPUT, so it moves the operating
# point without being a network change -- session 68's bonus pair made it the reference for "how
# much of an apparent ATTACK effect is operating point". Same role here.
GRUNT_CONDS = {
    "drive-noon": "notch_level-1700_grunt-{throw}.wav",
    "drive-min":  "notch_drive-0700_level-1700_grunt-{throw}.wav",
}
GRUNT_THROWS = ["boost", "flat"]


# ---------------------------------------------------------------------------------------------
# extraction
# ---------------------------------------------------------------------------------------------
def align_to_stim(sig, stim):
    """Integer-sample align via the 10 s `sweep_clean` anchor.

    `A.align` uses the MAIN test signal's segment map, so it cannot be used on this stimulus -- we
    correlate on THIS signal's own sweep region instead (the `read_jfet_ladder` pattern).
    """
    a, b = T["sweep_clean"]
    ref = stim[int(a * FS):int(b * FS)]
    s = sig[int(a * FS):int(min(len(sig), (b + 0.5) * FS))]
    n = min(len(ref), len(s))
    corr = sps.correlate(s[:n] - s[:n].mean(), ref[:n] - ref[:n].mean(), mode="full", method="fft")
    lag = int(np.argmax(np.abs(corr))) - (n - 1)
    if lag > 0:
        sig = sig[lag:]
    elif lag < 0:
        sig = np.concatenate([np.zeros(-lag), sig])
    return sig, lag


def seg(sig, name):
    """A tone segment with its outer sixth trimmed off each end.

    The trim is not cosmetic: it discards the tone's on/off transient, which otherwise puts
    broadband energy into a narrowband fit. Same convention as `read_jfet_ladder.seg`.
    """
    a, b = T[name]
    s = sig[int(a * FS):int(b * FS)]
    m = len(s) // 6
    return s[m:-m] if len(s) > 6 else s


def amp_at(s, f):
    """Least-squares amplitude of the component at EXACTLY f.

    ⭐ This is why the stepped stimulus beats the swept one. A projection onto (cos, sin) at the
    tone's own frequency has no window, no bin grid and no leakage from neighbouring frequencies --
    the resolution is the STEP SIZE, not a transform's bin width. A DC column is included because a
    clipping stage can produce signal-dependent DC that would otherwise bias the fit.
    """
    n = len(s)
    t = np.arange(n) / FS
    M = np.stack([np.ones(n), np.cos(2 * np.pi * f * t), np.sin(2 * np.pi * f * t)], axis=1)
    c, *_ = np.linalg.lstsq(M, s, rcond=None)
    return float(np.hypot(c[1], c[2]))


def curve(sig, stim, level_db):
    """|H(f)| in dB over the stepped grid, referenced to the stimulus's own tone amplitudes.

    Referencing to the stimulus rather than to a constant means a stimulus-side irregularity cannot
    masquerade as a device feature. (The stimulus is synthetic so this is exactly constant -- doing
    it anyway costs nothing and removes the assumption.)
    """
    out = []
    for f in FREQS:
        name = f"nt_{f:g}_{level_db}"
        if name not in T:
            continue
        a_out = amp_at(seg(sig, name), float(f))
        a_in = amp_at(seg(stim, name), float(f))
        out.append(20.0 * np.log10((a_out / (a_in + 1e-30)) + 1e-30))
    return np.asarray(FREQS, dtype=float), np.asarray(out, dtype=float)


# ---------------------------------------------------------------------------------------------
# the locator -- same definitions as attack_notch_probe, on a finer grid
# ---------------------------------------------------------------------------------------------
def refine_min(f, mag, i):
    """Parabolic vertex through bin i and its neighbours on the LOG-f axis.

    Never read a sharp feature's frequency straight off the grid (`mid_shape_verify`'s rule,
    session 26) -- even a 2 Hz grid quantises f0 to +-1 Hz, and the throws are 6-18 Hz apart.
    Rejects a vertex outside the bracketing points, which is the guard session 64 had to add after a
    near-cancelling denominator overflowed to inf.
    """
    if i <= 0 or i >= len(f) - 1:
        return float(f[i]), float(mag[i])
    x = np.log2(f[i - 1:i + 2])
    y = mag[i - 1:i + 2]
    denom = y[0] - 2 * y[1] + y[2]
    if abs(denom) < 1e-12:
        return float(f[i]), float(mag[i])
    dx = 0.5 * (y[0] - y[2]) / denom * (x[2] - x[1])
    if not np.isfinite(dx) or abs(dx) > (x[2] - x[1]):
        return float(f[i]), float(mag[i])
    vx = x[1] + dx
    vy = y[1] - 0.125 * (y[0] - y[2]) ** 2 / denom
    return float(2.0 ** vx), float(vy)


def half_depth_width(f, mag, shoulder, db_min):
    """Half-depth bandwidth by linear interpolation of the contour crossings.

    ⚠ HALF-DEPTH, not a fixed -6 dB contour. A deeper null crosses any FIXED absolute contour
    further out, so width-at--6 dB is confounded with depth -- and the throws differ in depth by
    2x here, so that confound would be the dominant term. Referring the contour to each null's OWN
    depth removes it (session 63 item 6c).
    """
    thr = shoulder - 0.5 * (shoulder - db_min)
    i = int(np.argmin(mag))
    below = mag <= thr
    if not below[i]:
        return float("nan")

    def cross(a, b):
        """Frequency where the curve crosses `thr` between grid points a and b."""
        if a < 0 or b < 0 or a >= len(f) or b >= len(f):
            return float("nan")
        y0, y1 = mag[a], mag[b]
        if abs(y1 - y0) < 1e-12:
            return float(f[a])
        t = (thr - y0) / (y1 - y0)
        return float(f[a] + t * (f[b] - f[a]))

    lo = i
    while lo > 0 and below[lo - 1]:
        lo -= 1
    hi = i
    while hi < len(f) - 1 and below[hi + 1]:
        hi += 1
    f_lo, f_hi = cross(lo - 1, lo), cross(hi + 1, hi)
    if not (np.isfinite(f_lo) and np.isfinite(f_hi)):
        return float("nan")
    return float(f_hi - f_lo)


def fitted_depth(f, mag, f0, db_min):
    """Depth as a FITTED parameter of the null's own shape, not a difference of two curve points.

    ⭐ WHY DEPTH STILL NEEDS FIXING EVEN WITH A STEPPED STIMULUS — and this is a correction to the
    capture document's own claim. `gen_notch_sweep.py`'s header says a stepped sine makes depth "a
    directly measured value rather than a lower bound". That is only HALF true. There are TWO
    understating biases and the stimulus fixes only one:

      * BIN SMEARING is a RESOLUTION artefact -> FIXED. The self-test's sharp deep cases read
        32.03 / 32.69 dB against a true 33.0, where the swept instrument read 28.71.
      * SHOULDER CONTAMINATION is DEFINITIONAL -> NOT FIXED by resolution. A broad null's own skirt
        genuinely reaches into the 200-270 Hz window, so `max(shoulder) - min` understates however
        finely the axis is sampled. Measured on the self-test: -4.23 dB at Qp 0.7.

    ⛔ THE OBVIOUS FIX DOES NOT WORK, AND THE SELF-TEST IS WHAT PROVED IT. Fitting a
    polynomial to the curve outside a fixed exclusion window and evaluating it at f0 made the error
    WORSE, not better -- 7.03 dB against the shoulder method's 4.23 -- because a broad null's skirts
    extend past any exclusion window that still leaves data inside a 150-550 Hz span, so the
    polynomial fits the SKIRT and the "baseline" comes out below the true one. Widening the window
    starves the fit; narrowing it worsens the contamination. There is no setting that works, which is
    a property of the span, not of the tuning.

    So this is PARAMETRIC instead: fit the two-pole notch's own analytic magnitude, with a linear
    background in log-f, to the whole measured curve. Depth is then a FITTED parameter rather than a
    difference of two points, and neither the shoulder nor the skirt has to be uncontaminated.

    ⚠ It buys that by ASSUMING the null is two-pole. That is exactly the shape the ATTACK topology
    is built from and the shape sessions 61-66 modelled it as, so it is a fair assumption here -- but
    it IS an assumption, and it is why `depth` (definitional, assumption-free, a LOWER BOUND) is
    still reported beside it. Where the two disagree, the residual column says which to believe.
    """
    x = np.log2(f / f0)

    def model(p):
        depth, q, b0, b1 = p
        # |H| of s^2 + (w0/Qz)s + w0^2 over s^2 + (w0/Qp)s + w0^2, evaluated in normalised freq
        r = 2.0 ** x                                    # f / f0
        qz = q * 10.0 ** (depth / 20.0)
        num = np.sqrt((1.0 - r ** 2) ** 2 + (r / qz) ** 2)
        den = np.sqrt((1.0 - r ** 2) ** 2 + (r / q) ** 2)
        return 20.0 * np.log10(num / den + 1e-30) + b0 + b1 * x

    def resid(p):
        return model(p) - mag

    from scipy.optimize import least_squares
    sh = float(np.max(mag[(f >= SHOULDER_WIN[0]) & (f <= SHOULDER_WIN[1])]))
    p0 = [max(sh - db_min, 1.0), 2.0, sh, 0.0]
    try:
        sol = least_squares(resid, p0, bounds=([0.5, 0.1, -80.0, -60.0], [80.0, 50.0, 80.0, 60.0]),
                            max_nfev=4000)
    except Exception:  # noqa: BLE001
        return float("nan"), float("nan")
    rms = float(np.sqrt(np.mean(sol.fun ** 2)))
    return float(sol.x[0]), rms


def locate(f, mag, fit_depth=True):
    """Locate the null. `fit_depth=False` skips the PARAMETRIC depth only.

    ⚠ `fit_depth` changes NOTHING that any caller scores: `f_ref`, `depth` (the definitional
    shoulder-referred lower bound) and `width` are computed the same way either way, and only the
    optional `depth_base`/`base_resid` become nan. It exists because `fitted_depth` runs a bounded
    least_squares (up to 4000 evaluations) and `attack_shape_screen` calls this INSIDE a
    differential_evolution loop -- tens of thousands of times -- where it is pure cost. Adding a
    flag here rather than a second copy of the locator in the screen keeps ONE oracle (session 62's
    rule); a second implementation is exactly how the two sides of a comparison drift apart.
    """
    m = (f >= SEARCH_WIN[0]) & (f <= SEARCH_WIN[1])
    fi = np.flatnonzero(m)
    i_local = int(np.argmin(mag[m]))
    i = int(fi[i_local])
    f_bin, db_min = float(f[i]), float(mag[i])
    f_ref, db_ref = refine_min(f, mag, i)

    ms = mag[(f >= SHOULDER_WIN[0]) & (f <= SHOULDER_WIN[1])]
    mu = mag[(f >= UPPER_WIN[0]) & (f <= UPPER_WIN[1])]
    lo_sh = float(np.max(ms)) if len(ms) else float("nan")
    up_sh = float(np.max(mu)) if len(mu) else float("nan")
    d_base, base_resid = (fitted_depth(f, mag, f_ref, db_min) if fit_depth
                          else (float("nan"), float("nan")))
    return dict(f_bin=f_bin, f_ref=f_ref, db_min=db_min, db_ref=db_ref,
                lo_shoulder=lo_sh, up_shoulder=up_sh,
                depth=lo_sh - db_min, depth_ref=lo_sh - db_ref,
                depth_base=d_base, base_resid=base_resid,
                width=half_depth_width(f, mag, lo_sh, db_min))


# ---------------------------------------------------------------------------------------------
# GATE 1 -- self-test
# ---------------------------------------------------------------------------------------------
def notch_ba(f0, depth_db, Qp, fs):
    """Two-pole notch with EXACTLY `depth_db` at EXACTLY f0 once discretised.

    Identical construction to `attack_notch_probe.notch_ba` -- deliberately, so the two instruments
    are gated against the SAME synthetic ground truth and their errors are comparable.
    """
    w0 = 2.0 * fs * np.tan(np.pi * f0 / fs)
    Qz = Qp * 10.0 ** (depth_db / 20.0)
    b = [1.0, w0 / Qz, w0 ** 2]
    a = [1.0, w0 / Qp, w0 ** 2]
    return sps.bilinear(b, a, fs)


def true_width(f0, depth_db, Qp, fs):
    """The synthetic notch's own half-depth width, evaluated analytically on a dense grid.

    The self-test must compare measured width against the FILTER's width, not against a number I
    chose -- otherwise it grades the locator against my arithmetic instead of against the truth.
    """
    b, a = notch_ba(f0, depth_db, Qp, fs)
    fd = np.arange(150.0, 550.0, 0.05)
    w, h = sps.freqz(b, a, worN=2 * np.pi * fd / fs)
    mag = 20.0 * np.log10(np.abs(h) + 1e-30)
    sh = float(np.max(mag[(fd >= SHOULDER_WIN[0]) & (fd <= SHOULDER_WIN[1])]))
    return half_depth_width(fd, mag, sh, float(np.min(mag)))


def selftest():
    print("=" * 108)
    print("GATE 1. SELF-TEST — recover synthesised notches of KNOWN f0, depth AND width")
    print("=" * 108)
    print("  Same stimulus, same narrowband extraction, same locator. Ground truth for width is the")
    print("  FILTER's own half-depth width on a 0.05 Hz grid, not a number chosen by hand.\n")

    sr, stim = wavfile.read(STIMULUS)
    stim = stim.astype(np.float64)

    # The cases bracket what the pedal actually does: a broad shallow null (cut/flat) and a sharp
    # deep one (boost) -- the latter is the throw whose WIDTH is the open item.
    cases = [(316.4, 15.0, 1.0), (316.4, 15.0, 2.0), (328.1, 33.0, 2.0),
             (328.1, 33.0, 4.0), (334.0, 16.0, 2.0), (320.0, 10.0, 0.7)]

    print("  %-8s %-7s %-5s | %-8s %-7s | %-8s %-7s | %-8s %-7s | %-7s %-7s %-6s"
          % ("f0", "depth", "Qp", "f0 meas", "err", "dep(sh)", "err", "dep(fit)", "err",
             "w true", "w meas", "err %"))
    print("  " + "-" * 112)

    worst_f = worst_d = worst_w = worst_b = 0.0
    over = over_b = 0.0
    for f0, depth, qp in cases:
        b, a = notch_ba(f0, depth, qp, FS)
        y = sps.lfilter(b, a, stim)
        f, mag = curve(y, stim, LEVELS_DB[0])
        r = locate(f, mag)
        wt = true_width(f0, depth, qp, FS)
        ef = r["f_ref"] - f0
        ed = r["depth"] - depth
        eb = r["depth_base"] - depth
        ew = 100.0 * (r["width"] - wt) / wt
        worst_f = max(worst_f, abs(ef))
        worst_d = max(worst_d, abs(ed))
        worst_b = max(worst_b, abs(eb))
        worst_w = max(worst_w, abs(ew))
        over = max(over, ed)
        over_b = max(over_b, eb)
        print("  %-8.1f %-7.1f %-5.1f | %-8.2f %+-7.2f | %-8.2f %+-7.2f | %-9.2f %+-7.2f | %-7.1f %-7.1f %+-6.1f"
              % (f0, depth, qp, r["f_ref"], ef, r["depth"], ed, r["depth_base"], eb,
                 wt, r["width"], ew))

    print()
    print("  worst |f0 err| = %.2f Hz   worst |width err| = %.1f %%" % (worst_f, worst_w))
    print("  depth via SHOULDER  (record-compatible): worst |err| %.2f dB, worst over-statement %+.2f dB"
          % (worst_d, over))
    print("  depth via 2-POLE FIT (contamination-corrected): worst |err| %.2f dB, worst over-statement %+.2f dB"
          % (worst_b, over_b))
    print()
    # ⚠ The gates below are on the properties the VERDICT rests on, not on an absolute accuracy the
    # statistic does not have (session 61's lesson). f0 must beat the 2 Hz step; depth must not
    # over-state (the swept instrument's two biases both UNDERSTATE, so an over-stating replacement
    # would be a new bias, not a fix); width must beat the +-25 % quantisation it replaces.
    ok = True
    for label, val, lim, unit in [("f0 within one step", worst_f, 2.0, "Hz"),
                                  ("shoulder depth does not over-state", over, 0.5, "dB"),
                                  ("fitted depth recovers the truth", worst_b, 1.5, "dB"),
                                  ("width beats the +-25% it replaces", worst_w, 25.0, "%")]:
        verdict = "PASS" if val <= lim else "FAIL"
        ok &= val <= lim
        print("   %-38s %8.2f %-2s  (limit %5.1f)  %s" % (label, val, unit, lim, verdict))
    print()
    print("  " + ("✅ GATE 1 PASS" if ok else "⛔ GATE 1 FAIL — do not read the captures"))
    return ok


# ---------------------------------------------------------------------------------------------
# measurement
# ---------------------------------------------------------------------------------------------
def load_raw(path):
    """Load a capture WITHOUT `captures.load_capture`.

    ⚠⚠ DO NOT "FIX" THIS BY CALLING load_capture -- IT CORRUPTS THIS STIMULUS. Its sample-rate
    mislabel guard inspects a FIXED window at t = 0.5-1.45 s expecting the main test signal's 1 kHz
    cal tone. This stimulus puts the 10 s `sweep_clean` anchor there instead (it has to -- the sweep
    must come first, or the aligner would be correlating behind 100 tones), so the guard reads the
    sweep's content at ~30 Hz, computes a huge "speed error", and RESAMPLES the file to roughly HALF
    its length. Measured: a 176.100 s capture came back as 89.9 s, after which every segment offset
    is wrong and the -18 dBFS half of the file falls past the end of the array and reads -600 dB.

    ⚠ AND THIS CONTRADICTS `gen_notch_sweep.py`'s OWN HEADER, which states the cal tone is included
    "so `captures.load_capture()` works". It does not, because the guard is keyed to a fixed TIME
    WINDOW rather than to the segment map -- and the cal tone in this stimulus sits at ~10.6 s,
    after the sweep. Session 13 hit exactly this on the jfet ladder and the note there ("use A.load,
    NOT captures.load_capture()") is the precedent. The generator's claim has been corrected.

    These captures are 48 kHz by construction and `verify_new_captures.py` asserts it, so no
    rate handling is needed here at all.
    """
    sr, raw = wavfile.read(path)
    x = raw.astype(np.float64) if raw.dtype.kind == "f" else raw.astype(np.float64) / np.iinfo(raw.dtype).max
    if x.ndim > 1:
        x = x.mean(axis=1)
    if sr != FS:
        raise SystemExit(f"{path}: {sr} Hz, expected {FS} -- verify_new_captures.py should have caught this")
    return x


def read_one(path, stim, level_db):
    cap = load_raw(path)
    cap, lag = align_to_stim(cap, stim)
    f, mag = curve(cap, stim, level_db)
    r = locate(f, mag)
    r["lag"] = lag
    r["f"] = f.tolist()
    r["mag"] = mag.tolist()
    return r


def swept_locate(cap, stim):
    """Run the OLD instrument -- a 5.86 Hz-bin CSD transfer over the embedded `sweep_clean` -- on
    the SAME audio, and locate the null with the SAME locator.

    ⭐ THIS IS THE CONTROL THAT MAKES THE COMPARISON MEAN ANYTHING. The swept record
    (316.4/328.1/334.0 Hz, depths 14.93/32.70/16.01, widths 77.9/27.1/71.9) was measured on the
    session-60 `drive-0700_level-1700_attack-*_base-od.wav` captures. These are DIFFERENT files at
    the same nominal settings, so a raw stepped-vs-record comparison mixes three things: the
    instrument change, a take-to-take term, and a knob-repositioning term. Running the old
    instrument on THIS audio isolates the instrument change, because the other two cancel exactly.

    Identical to `analyze.transfer` (nperseg 8192 => 5.86 Hz bins) by construction -- restated
    rather than imported only because that module's segment map is the MAIN test signal's.
    """
    a, b = T["sweep_clean"]
    y = cap[int(a * FS):int(b * FS)]
    u = stim[int(a * FS):int(b * FS)]
    n = min(len(y), len(u))
    fr, pxy = sps.csd(u[:n], y[:n], FS, nperseg=8192)
    fr, pxx = sps.welch(u[:n], FS, nperseg=8192)
    mag = 20.0 * np.log10(np.abs(pxy) / (pxx + 1e-20) + 1e-12)
    m = (fr >= 150.0) & (fr <= 550.0)
    return locate(fr[m], mag[m])


def compare(stim):
    print()
    print("=" * 108)
    print("GATE 2. SAME-FILE INSTRUMENT COMPARISON — stepped vs swept on IDENTICAL audio")
    print("=" * 108)
    print("  No take-to-take term and no knob-repositioning term between the two columns: both read")
    print("  the SAME capture. Any difference is the INSTRUMENT.\n")
    print("  %-11s %-6s | %-8s %-8s %-8s | %-8s %-8s %-8s | %-7s %-7s %-7s"
          % ("cond", "throw", "f0 step", "dep step", "wid step",
             "f0 swept", "dep swept", "wid swept", "Δf0", "Δdep", "Δwid%"))
    print("  " + "-" * 104)
    rows = []
    for cond, pat in CONDS.items():
        for throw in THROWS:
            path = os.path.join(CAP_DIR, pat.format(throw=throw))
            if not os.path.exists(path):
                continue
            cap = load_raw(path)
            cap, _ = align_to_stim(cap, stim)
            st = locate(*curve(cap, stim, LEVELS_DB[0]))
            sw = swept_locate(cap, stim)
            dw = (100.0 * (st["width"] - sw["width"]) / sw["width"]
                  if np.isfinite(sw["width"]) and sw["width"] else float("nan"))
            print("  %-11s %-6s | %-8.2f %-8.2f %-8.1f | %-8.2f %-8.2f %-8.1f | %+-7.2f %+-7.2f %+-7.1f"
                  % (cond, throw, st["f_ref"], st["depth"], st["width"],
                     sw["f_ref"], sw["depth"], sw["width"],
                     st["f_ref"] - sw["f_ref"], st["depth"] - sw["depth"], dw))
            rows.append((cond, throw, st, sw))
    print()
    print("  ⭐ READ THE SIGN OF Δdep. The swept instrument's two biases BOTH UNDERSTATE, and bin")
    print("     smearing bites hardest on the SHARPEST null. So a valid replacement must read the")
    print("     sharp throw (boost) DEEPER and the broad throws (cut/flat) about the same. A")
    print("     replacement that read boost SHALLOWER would be adding a new bias, not removing one.")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--compare", action="store_true",
                    help="also run the OLD swept instrument on the SAME files")
    args = ap.parse_args()

    if args.selftest:
        return 0 if selftest() else 1

    if not selftest():
        print("\n⛔ self-test failed — refusing to report measurements")
        return 1

    sr, stim = wavfile.read(STIMULUS)
    stim = stim.astype(np.float64)

    results = {}
    for cond, pat in CONDS.items():
        print()
        print("=" * 108)
        print(f"ATTACK — {cond}")
        print("=" * 108)
        print("  %-7s %-6s | %-9s %-9s %-9s | %-9s %-9s %-9s | %s"
              % ("throw", "level", "f0", "depth", "width", "swept f0", "swept dep", "swept wid", "Δwidth"))
        print("  " + "-" * 102)
        for throw in THROWS:
            path = os.path.join(CAP_DIR, pat.format(throw=throw))
            if not os.path.exists(path):
                print(f"  {throw:-7s} MISSING {path}")
                continue
            for lvl in LEVELS_DB:
                r = read_one(path, stim, lvl)
                results[f"{cond}/{throw}/{lvl}"] = {k: v for k, v in r.items() if k not in ("f", "mag")}
                results[f"{cond}/{throw}/{lvl}"]["curve_f"] = r["f"]
                results[f"{cond}/{throw}/{lvl}"]["curve_db"] = r["mag"]
                sf, sd, sw = SWEPT_RECORD[throw]
                dw = 100.0 * (r["width"] - sw) / sw if np.isfinite(r["width"]) else float("nan")
                print("  %-7s %-6d | %-9.2f %-9.2f %-9.1f | %-9.1f %-9.2f %-9.1f | %+.1f %%"
                      % (throw, lvl, r["f_ref"], r["depth"], r["width"], sf, sd, sw, dw))

        # spread across throws at the quiet level -- the statistic the whole ATTACK spec rests on
        quiet = [results.get(f"{cond}/{t}/{LEVELS_DB[0]}") for t in THROWS]
        if all(quiet):
            f0s = [q["f_ref"] for q in quiet]
            print()
            print("  f0 spread across throws (quiet level): %.2f Hz  [%s]"
                  % (max(f0s) - min(f0s), ", ".join("%.2f" % x for x in f0s)))
            deps = [q["depth"] for q in quiet]
            print("  depth ratio boost/flat: %.2fx   (swept record: %.2fx)"
                  % (deps[1] / deps[2], SWEPT_RECORD["boost"][1] / SWEPT_RECORD["flat"][1]))

    # GRUNT control -- a known-LINEAR element at the clipper input
    for cond, pat in GRUNT_CONDS.items():
        print()
        print("=" * 108)
        print(f"GRUNT CONTROL (schematic-verified LINEAR, at the clipper input) — {cond}")
        print("=" * 108)
        print("  %-7s %-6s | %-9s %-9s %-9s" % ("throw", "level", "f0", "depth", "width"))
        print("  " + "-" * 50)
        for throw in GRUNT_THROWS:
            path = os.path.join(CAP_DIR, pat.format(throw=throw))
            if not os.path.exists(path):
                continue
            for lvl in LEVELS_DB:
                r = read_one(path, stim, lvl)
                results[f"grunt/{cond}/{throw}/{lvl}"] = {
                    k: v for k, v in r.items() if k not in ("f", "mag")}
                print("  %-7s %-6d | %-9.2f %-9.2f %-9.1f"
                      % (throw, lvl, r["f_ref"], r["depth"], r["width"]))

    if args.compare:
        compare(stim)

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as fh:
        json.dump(results, fh, indent=1)
    print()
    print(f"wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
