#!/usr/bin/env python3.11
"""read_a3_tones -- A3's complex target measured on TONES, i.e. WITHOUT the harmonic-power bias
that every previous blend-axis number carries (session 54, Phase 9 / A3).

WHAT THIS DECIDES
-----------------
`a3_blend_axis.py` solves `t(B)^2 = 1 + k1.B + k2.B^2` from 1/3-oct band ENERGY. The mixing law
survives harmonics exactly (every OD harmonic carries the same B; the clean tap contributes none),
but the recovered magnitude is then

    r = sqrt(|g1|^2 + H)          H = the band's HARMONIC power

an UPPER BOUND on the fundamental, while `Q = Re g1` stays exact -- so `cos theta = Q/r` is biased
TOWARDS 90 degrees (session 52 item 3b). Session 52's impossibility proof -- that NO causal linear
post-clipper element of any order can supply A3, because the target wants ~38 deg MORE lead than
the min-phase realisation of its own magnitude -- is computed from that biased theta. Session 52
SIZED the bias (reconciling needs H/P of 0.6..265, impossible at 8 of 15 bands) but could not
measure it away, and session 53 item 5 then raised the prior that the flat -38 deg is an artefact:
every physical mechanism tested produces a phase change that GROWS with frequency, while the
measured requirement is FLAT across 40x.

A single tone per band has NO harmonic power inside the measurement -- the fundamental is projected
out at exactly the drive frequency, so `r` becomes the fundamental magnitude and `theta` becomes
unbiased. This tool is therefore the arbiter:

  * excess lead SURVIVES on tones -> session 52 is airtight, the search moves INSIDE/BEFORE the
    clipper (session 53 next-step (c)).
  * excess lead COLLAPSES          -> sessions 47-52 were chasing an instrument artefact and the
    post-clipper region reopens.

WHAT IS AND IS NOT MEASURED FROM THE WAVEFORM
---------------------------------------------
⚠ theta is STILL recovered ALGEBRAICALLY from magnitudes across BLEND, exactly as
`a3_blend_axis.unpack` does -- NOT from the tone's waveform phase. That is deliberate, not laziness:
per-take timing drift makes absolute waveform phase meaningless across separately-recorded files
(the capture request says so explicitly), whereas the |t(B)| ladder is alignment-immune by
construction. What the tones change is the INPUT to that algebra: |fundamental| instead of
sqrt(|fund|^2 + harmonics). Same solve, unbiased data.

Consequences inherited unchanged from the blend axis, and they matter when reading the output:
  * theta is identified only up to SIGN (magnitudes cannot see it) -- `fold()` to [0, 180].
  * the axis is DEGENERATE in the bleed level b0 (3 unknowns, 2 coefficients), so b0 is taken from
    the model and this tool CANNOT challenge beta. Set D is what measures b0.

LEVELS ARE A CONTROL, NEVER AN AVERAGE
--------------------------------------
The stimulus carries every band at -18 dBFS (A3's own operating point) AND -30 dBFS (where the OD
path is ~linear). The recovered transfer must be LEVEL-INDEPENDENT if it is a transfer at all.
Averaging the two would hide exactly the failure that would invalidate the read, so they are solved
and printed separately and their difference is reported as a diagnostic.

Run:
    python3.11 analysis/read_a3_tones.py --selftest        # MANDATORY before believing a number
    python3.11 analysis/read_a3_tones.py                   # Set A (reference condition)
    python3.11 analysis/read_a3_tones.py --set E           # Set E (DRIVE max)
"""
import argparse
import cmath
import math
import os
import sys

import numpy as np
from scipy.io import wavfile
from scipy import signal as sps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gen_a3_tones as GT                      # segment map -- never hand-typed offsets
import a3_blend_axis as AX                     # quad_fit / unpack / fit_taper / fold / model_b0

FS = GT.FS
STIM = "analysis/a3_tones_48k.wav"
CAPDIR = "analysis/captures"
T = GT.segment_times()

# Middle-of-segment window: TONE_SEC is 2.0 s, so this drops 0.25 s each side -- well clear of the
# 5 ms fade and of any settling transient, and 1.5 s gives 30 cycles even at 20 Hz.
WIN_SEC = 1.5
TAKE_FLOOR_DB = AX.TAKE_FLOOR_DB
FIT_HI_HZ = AX.FIT_HI_HZ

# (BLEND knob, filename suffix). Same knob->x mapping as captures.py::_clock_to_x.
_BLEND_CLOCKS = [(0.00, "0700"), (0.25, "0930"), (0.50, "1200"), (0.75, "1430"), (1.00, "1700")]


def set_files(which):
    """Set A = the reference condition. Set E = the same BLEND sweep at DRIVE max.

    ⚠ Set E has no B=0 file of its own and does not need one: at BLEND=0 the wiper sits on the
    clean pin so the OD path contributes nothing and the capture is drive-INDEPENDENT. That is
    verified, not assumed -- session 53b measured `drive-1700_blend-0700` against
    `blend-0700` on the main stimulus and got RMS agreement to 0.07 %.
    """
    if which == "A":
        return [(b, "a3tones_blend-%s.wav" % c) for b, c in _BLEND_CLOCKS]
    if which == "E":
        return [(0.00, "a3tones_blend-0700.wav")] + \
               [(b, "a3tones_drive-1700_blend-%s.wav" % c) for b, c in _BLEND_CLOCKS[1:]]
    sys.exit("unknown set %r (expected A or E)" % which)


# --- I/O + alignment ---------------------------------------------------------------------------
def load(path):
    sr, x = wavfile.read(path)
    if x.dtype.kind in "iu":
        x = x.astype(np.float64) / np.iinfo(x.dtype).max
    else:
        x = x.astype(np.float64)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if sr != FS:
        sys.exit("%s: expected %d Hz, got %d" % (path, FS, sr))
    return x


def align(cap, stim):
    """Integer-sample align on this stimulus's OWN sweep_clean anchor.

    Deliberately not `analyze.align`: that one indexes the MAIN signal's segment map, which has a
    different sweep offset. Using it here would silently read the wrong window and still return a
    confident lag -- the class of error that has cost this project whole sessions.
    """
    a, b = T["sweep_clean"]
    ref = stim[int(a * FS):int(b * FS)]
    seg = cap[int(a * FS):int(min(len(cap), (b + 0.5) * FS))]
    n = min(len(ref), len(seg))
    corr = sps.correlate(seg[:n] - seg[:n].mean(), ref[:n] - ref[:n].mean(),
                         mode="full", method="fft")
    lag = int(np.argmax(np.abs(corr))) - (n - 1)
    if lag > 0:
        cap = cap[lag:]
    elif lag < 0:
        cap = np.concatenate([np.zeros(-lag), cap])
    if len(cap) < len(stim):
        cap = np.concatenate([cap, np.zeros(len(stim) - len(cap))])
    return cap[:len(stim)], lag


# --- narrowband fundamental --------------------------------------------------------------------
def project(x, f):
    """Complex amplitude of the component at EXACTLY f, by Hann-windowed coherent projection.

    Returns `a` such that the component is Re{a . e^(i.2.pi.f.t)}, i.e. |a| is the tone's PEAK
    amplitude. Normalised by sum(w) * 0.5 so the window's own gain divides out.

    Why a projection and not an FFT bin: the tone frequencies (20, 25, 32, ... 1613 Hz) are not
    integer multiples of 1/WIN_SEC, so no FFT bin sits on them and the nearest one would scallop by
    up to 1.4 dB. The projection evaluates the DTFT at the exact frequency instead.

    Leakage from harmonics is the thing this tool exists to exclude: a Hann window over 1.5 s has a
    2.67 Hz main lobe and sidelobes below -80 dB one lobe out, while the nearest contaminant (the
    2nd harmonic) sits f Hz away -- >=20 Hz, i.e. >=15 lobes. The pipeline selftest measures this
    directly rather than trusting the argument.
    """
    n = len(x)
    w = np.hanning(n)
    t = np.arange(n) / FS
    return 2.0 * np.sum(x * w * np.exp(-2j * math.pi * f * t)) / np.sum(w)


def tone_window(x, name):
    a, b = T[name]
    mid = 0.5 * (a + b)
    i0 = int((mid - WIN_SEC / 2) * FS)
    return x[i0:i0 + int(WIN_SEC * FS)]


def gap_window(x, name):
    """The silence immediately AFTER a tone -- used for the noise/hum floor at the same frequency.

    GAP is 0.3 s, so the resolution here is coarse (~6.7 Hz with Hann); it is a floor estimate, not
    a measurement. It matters because mains hum lands on or beside the 50 Hz tone (and its harmonic
    beside 101 Hz), and hum is ADDITIVE at fixed level -- it would inflate the quiet -30 dBFS read
    far more than the -18 one and could masquerade as level-dependence.
    """
    _, b = T[name]
    i0 = int(b * FS)
    return x[i0:i0 + int(GT.GAP * FS)]


def read_tones(path, stim, freqs, levels):
    """{(f, level): (|fund| peak amplitude, snr_dB)} for one capture."""
    cap = load(path)
    if len(cap) < 0.95 * len(stim):
        sys.exit("%s is TRUNCATED (%.1f s vs %.1f s) -- missing segments read as zeros and "
                 "produce confident nonsense" % (path, len(cap) / FS, len(stim) / FS))
    cap, lag = align(cap, stim)
    out = {}
    for db in levels:
        for f in freqs:
            name = "tn_%g_%d" % (f, db)
            a = abs(project(tone_window(cap, name), f))
            nz = abs(project(gap_window(cap, name), f))
            out[(f, db)] = (a, 20.0 * math.log10(a / nz) if nz > 0 else 99.0)
    return out, lag


# --- selftests ---------------------------------------------------------------------------------
def selftest_algebra(b0):
    """Leg 1: the law + solve, on synthesised t(B). Mirrors a3_blend_axis's own selftest."""
    worst_r = worst_t = 0.0
    for r, th_deg in [(0.05, 20.0), (0.5, 95.0), (1.7, 150.0), (0.31, 60.0), (2.4, 178.0)]:
        g = r * cmath.exp(1j * math.radians(th_deg))
        t = [abs((1.0 - B * (1.0 - b0)) + B * g) for B, _ in _BLEND_CLOCKS]
        k1, k2, _, _ = AX.quad_fit(t, [0.25, 0.50, 0.75])
        rr, tt, _ = AX.unpack(k1, k2, b0)
        worst_r = max(worst_r, abs(20 * math.log10(rr / r)))
        worst_t = max(worst_t, abs(AX.fold(tt) - AX.fold(math.radians(th_deg))))
    ok = worst_r < 1e-6 and worst_t < 1e-4
    print("  [1] ALGEBRA   worst |dr| = %.3e dB, worst |dtheta| = %.3e deg -> %s"
          % (worst_r, worst_t, "PASS" if ok else "FAIL"))
    return ok


def _synth(stim, hum=0.0, lag=137):
    """A synthetic capture whose fundamentals are known exactly: each tone carries a 2nd and 3rd
    harmonic at -10 / -14 dB re fundamental (far dirtier than the real path at these bands) plus
    broadband noise, and optionally a 50 Hz mains tone. Returns (audio, {(f,db): true amplitude})."""
    rng = np.random.default_rng(7)
    fake = np.zeros(len(stim) + 500)
    a, b = T["sweep_clean"]
    fake[lag + int(a * FS):lag + int(b * FS)] = stim[int(a * FS):int(b * FS)]
    truth = {}
    for db in GT.TONE_DB:
        for f in GT.TONE_FREQS:
            t0, t1 = T["tn_%g_%d" % (f, db)]
            n = int(t1 * FS) - int(t0 * FS)
            tt = np.arange(n) / FS
            amp = 10.0 ** (db / 20.0) * (0.3 + 0.7 * (f / 1613.0))   # any smooth non-flat transfer
            ph = (f * 0.017) % (2 * math.pi)                          # arbitrary per-tone phase
            fake[lag + int(t0 * FS):lag + int(t0 * FS) + n] = (
                amp * np.sin(2 * math.pi * f * tt + ph)
                + amp * 10 ** (-10 / 20) * np.sin(2 * math.pi * 2 * f * tt + 1.1)
                + amp * 10 ** (-14 / 20) * np.sin(2 * math.pi * 3 * f * tt + 2.3))
            truth[(f, db)] = amp
    tt = np.arange(len(fake)) / FS
    fake += 1e-4 * rng.standard_normal(len(fake))
    if hum > 0.0:
        fake += hum * np.sin(2 * math.pi * 50.0 * tt + 0.4)
    return fake, truth


def _worst_err(cap, truth):
    worst, at = 0.0, None
    for (f, db), a_true in truth.items():
        e = abs(20 * math.log10(abs(project(tone_window(cap, "tn_%g_%d" % (f, db)), f)) / a_true))
        if e > worst:
            worst, at = e, (f, db)
    return worst, at


def selftest_pipeline(stim):
    """Leg 2: the whole read path -- lag, segment offsets, windowing, projection.

    ⭐ SPLIT INTO TWO, because the first draft conflated them and FAILED on the wrong one. A
    same-frequency contaminant (mains hum at 50 Hz, sitting on the 50 Hz tone) is NOT a leak and NO
    projection of any window length can remove it -- it is physically indistinguishable from signal.
    Asserting a tight bound on a run containing hum tests the hum level, not the tool.

      2a HARMONIC REJECTION (pass/fail) -- harmonics + noise only. This IS the tool's central claim:
         if the projection leaked harmonic power into the fundamental it would carry exactly the
         bias this tool exists to remove. Tight bound, no excuses.
      2b HUM SENSITIVITY (reported, not gated) -- adds 50 Hz mains and reports the induced error,
         and checks the gap-based SNR estimator actually SEES it. That estimator is the guard in the
         real run; a number nobody validates is not a guard.
    """
    fake, truth = _synth(stim)
    cap, _ = align(fake, stim)
    worst, at = _worst_err(cap, truth)
    ok_a = worst < 0.02
    print("  [2a] HARMONIC REJECTION  worst |dA| = %.4f dB at %s -> %s"
          % (worst, at, "PASS" if ok_a else "FAIL"))

    hum = 3e-4
    fake_h, truth_h = _synth(stim, hum=hum)
    cap_h, lag = align(fake_h, stim)
    worst_h, at_h = _worst_err(cap_h, truth_h)
    snr_50 = 20 * math.log10(abs(project(tone_window(cap_h, "tn_50_-30"), 50.0))
                             / abs(project(gap_window(cap_h, "tn_50_-30"), 50.0)))
    ok_lag = lag == 137
    print("  [2b] HUM SENSITIVITY     %.0e mains -> worst |dA| = %.3f dB at %s; the gap-SNR "
          "estimator reads %.1f dB there" % (hum, worst_h, at_h, snr_50))
    print("       (NOT a leak and not gated -- a same-frequency contaminant is inseparable from "
          "signal. This is why the real run prints per-band SNR: treat any band under ~30 dB as "
          "suspect rather than trusting its theta.)")
    print("  [2c] ALIGNMENT           recovered lag = %d (expected 137) -> %s"
          % (lag, "PASS" if ok_lag else "FAIL"))
    return ok_a and ok_lag


# --- model reference ----------------------------------------------------------------------------
def load_model(dec_csv):
    """{f: (|G|, theta_rad)} from a3_blend_decompose's EXACT superposition taps -- no solve, signed
    phase. This is the model side of H_req = G_ped / G_mdl."""
    if not os.path.exists(dec_csv):
        return None
    out = {}
    for line in open(dec_csv):
        if line.startswith("#") or not line.strip():
            continue
        v = [float(x) for x in line.split(",")]
        ref, od, cl = complex(v[1], v[2]), complex(v[5], v[6]), complex(v[7], v[8])
        out[v[0]] = (abs(od) / abs(ref), cmath.phase(od) - cmath.phase(cl))
    return out


def load_swept():
    """{f: (r_ped, theta_ped_deg)} from the SWEPT blend axis -- the biased instrument this tool is
    checking. Absent is fine; the comparison is then skipped rather than faked."""
    p = "build/a3_blend_axis_sweep_drv_-18.csv"
    if not os.path.exists(p):
        return None
    out = {}
    for line in open(p):
        if line.startswith("#") or not line.strip():
            continue
        v = line.strip().split(",")
        out[float(v[0])] = (float(v[1]), float(v[2]), int(v[5]))
    return out


def solve(t_by_band, bands, label, fixed):
    Bint, worst = AX.fit_taper(t_by_band, bands, label, fixed)
    res = {}
    for b in t_by_band:
        k1, k2, dres, bad = AX.quad_fit(t_by_band[b], Bint)
        r, th, cos_raw = AX.unpack(k1, k2, AX.model_b0())
        dt = float("nan") if bad else max(abs(x) for x in dres)
        ok = (not bad) and dt <= 0.30 and abs(cos_raw) <= 1.02 and r > 1e-20
        res[b] = (r, th, dt, ok, cos_raw)
    return Bint, worst, res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="A", choices=["A", "E"])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--fixed-taper", action="store_true",
                    help="assume an ideal linear BLEND taper (session 51 item 4 says it is not)")
    ap.add_argument("--dec-csv", default="build/a3_dec_drv0.5.csv")
    args = ap.parse_args()

    b0 = AX.model_b0()

    if args.selftest:
        print("=== SELFTEST ===")
        stim = load(STIM)
        ok = selftest_algebra(b0) & selftest_pipeline(stim)
        print("  VERDICT: %s" % ("PASS" if ok else "FAIL"))
        if not ok:
            sys.exit(1)
        return

    stim = load(STIM)
    files = set_files(args.set)
    freqs, levels = list(GT.TONE_FREQS), list(GT.TONE_DB)

    print("bleed level taken from the model: b0 = %.5f (%+.2f dB). This axis is DEGENERATE in it "
          "(3 unknowns, 2 coefficients)" % (b0, 20 * math.log10(b0)))
    print("-- unchanged from a3_blend_axis. Set D is what measures b0; do not read one off this.\n")

    print("=== 0. CAPTURES ===")
    data = {}
    for B, fn in files:
        p = os.path.join(CAPDIR, fn)
        if not os.path.exists(p):
            sys.exit("missing %s" % p)
        data[B], lag = read_tones(p, stim, freqs, levels)
        snrs = [data[B][(f, db)][1] for f in freqs for db in levels]
        print("  B=%.2f  %-40s lag %+5d smp   SNR min %5.1f dB (worst band %g Hz @ %d dBFS)"
              % (B, fn, lag, min(snrs),
                 *min(((f, db) for f in freqs for db in levels),
                      key=lambda k: data[B][k][1])))

    swept = load_swept()
    mdl = load_model(args.dec_csv)

    per_level = {}
    for db in levels:
        print("\n=== 1. SOLVE at %d dBFS %s ===" % (db, "(A3's operating point)" if db == -18
                                                    else "(near-linear CONTROL)"))
        t = {f: [data[B][(f, db)][0] / data[0.0][(f, db)][0] for B, _ in files] for f in freqs}
        bands = [f for f in freqs if f <= FIT_HI_HZ]
        Bint, worst, res = solve(t, bands, "PEDAL", args.fixed_taper)
        print("  law residual vs the %.3f dB take-to-take floor: %s (worst %.3f dB)"
              % (TAKE_FLOOR_DB, "HOLDS" if worst <= TAKE_FLOOR_DB else "EXCEEDS", worst))
        per_level[db] = res

    print("\n=== 2. LEVEL CONTROL -- a transfer must be level-INDEPENDENT ===")
    print("  If -18 and -30 disagree beyond the floor the tone read is level-contaminated and must")
    print("  be reported as such, NOT averaged. (session 53 item 5's own warning, applied here.)")
    print("      f    r(-18) dB  r(-30) dB     dr     th(-18)  th(-30)    dth")
    drs, dths = [], []
    for f in freqs:
        a, c = per_level[-18][f], per_level[-30][f]
        if not (a[3] and c[3]):
            print("  %5.0f       %s" % (f, "not identified at both levels -- skipped"))
            continue
        dr = 20 * math.log10(a[0] / c[0])
        dth = AX.fold(a[1]) - AX.fold(c[1])
        drs.append(dr)
        dths.append(dth)
        print("  %5.0f   %+9.2f  %+9.2f  %+7.2f    %6.1f   %6.1f  %+7.1f"
              % (f, 20 * math.log10(a[0]), 20 * math.log10(c[0]), dr,
                 AX.fold(a[1]), AX.fold(c[1]), dth))
    if drs:
        print("  |dr| mean %.2f dB worst %.2f  |  |dtheta| mean %.1f deg worst %.1f"
              % (np.mean(np.abs(drs)), np.max(np.abs(drs)),
                 np.mean(np.abs(dths)), np.max(np.abs(dths))))

    print("\n=== 3. THE HEADLINE -- TONES vs the SWEPT (harmonic-biased) instrument ===")
    print("  Both measure the SAME quantity at the SAME operating point. A theta difference IS the")
    print("  bias session 52 could only size indirectly. Positive dtheta = tones read FURTHER from")
    print("  the model, negative = the swept instrument was over-reading the lead.")
    print("      f   r_tone dB  r_swept dB     dr    th_tone  th_swept    dth   ident")
    dth_all = []
    for f in freqs:
        a = per_level[-18][f]
        if swept is None:
            continue
        key = min(swept, key=lambda x: abs(x - f))
        if abs(key - f) > 0.06 * f:
            continue
        rs, ths, ident = swept[key]
        dr = 20 * math.log10(a[0] / rs) if rs > 0 else float("nan")
        dth = AX.fold(a[1]) - ths
        if a[3] and ident:
            dth_all.append((f, dth, dr))
        print("  %5.0f  %+9.2f  %+9.2f  %+7.2f   %6.1f    %6.1f  %+7.1f   %s%s"
              % (f, 20 * math.log10(a[0]), 20 * math.log10(rs), dr,
                 AX.fold(a[1]), ths, dth, "yes" if a[3] else "NO ",
                 "" if ident else "  (swept not identified)"))
    if dth_all:
        band = [d for f, d, _ in dth_all if 40 <= f <= FIT_HI_HZ]
        rband = [d for f, _, d in dth_all if 40 <= f <= FIT_HI_HZ]
        print("  over 40-%.0f Hz, both identified (%d bands): dtheta mean %+.1f deg, "
              "rms %.1f, worst %+.1f" % (FIT_HI_HZ, len(band), np.mean(band),
                                         float(np.sqrt(np.mean(np.square(band)))),
                                         max(band, key=abs)))
        print("                                              dr     mean %+.2f dB, "
              "rms %.2f, worst %+.2f" % (np.mean(rband),
                                         float(np.sqrt(np.mean(np.square(rband)))),
                                         max(rband, key=abs)))

    if mdl is not None:
        print("\n=== 4. THE REQUIRED CORRECTION H_req = G_ped / G_mdl, ON TONES ===")
        print("  Model side = a3_blend_decompose's EXACT superposition taps (signed phase, no")
        print("  solve). arg H_req is what session 52 found no causal linear element can supply.")
        print("  ⚠ theta_ped is identified only up to SIGN, so BOTH branches are shown; session 52")
        print("  found the + branch beats - by 2.6-4x at every order, but that was on biased data.")
        print("      f    |H| dB   argH(+)  argH(-)   th_ped  th_mdl")
        rows = []
        for f in freqs:
            a = per_level[-18][f]
            key = min(mdl, key=lambda x: abs(x - f))
            if abs(key - f) > 0.06 * f or not a[3]:
                continue
            rm, thm = mdl[key]
            tp = AX.fold(a[1])
            hp = tp - math.degrees(thm)
            hm = -tp - math.degrees(thm)
            wrap = lambda d: (d + 180.0) % 360.0 - 180.0                      # noqa: E731
            rows.append((f, 20 * math.log10(a[0] / rm), wrap(hp), wrap(hm)))
            print("  %5.0f  %+8.2f  %+8.1f %+8.1f   %6.1f  %6.1f"
                  % (f, rows[-1][1], rows[-1][2], rows[-1][3], tp, math.degrees(thm)))
        fit = [r for r in rows if 40 <= r[0] <= FIT_HI_HZ]
        if fit:
            print("  over 40-%.0f Hz (%d bands): |H| mean %+.2f dB | argH(+) mean %+.1f deg "
                  "(spread %.1f) | argH(-) mean %+.1f (spread %.1f)"
                  % (FIT_HI_HZ, len(fit), np.mean([r[1] for r in fit]),
                     np.mean([r[2] for r in fit]), np.ptp([r[2] for r in fit]),
                     np.mean([r[3] for r in fit]), np.ptp([r[3] for r in fit])))

    out = "build/a3_tones_set%s.csv" % args.set
    with open(out, "w") as fh:
        fh.write("# read_a3_tones set %s: the PEDAL's OD-path transfer from NARROWBAND TONES\n"
                 "# (no harmonic-power bias). theta identified only up to sign; b0 = %.5f fixed.\n"
                 "# f,level_dbfs,r_ped,theta_ped_deg,law_resid_db,identified,snr_db\n"
                 % (args.set, b0))
        for db in levels:
            for f in freqs:
                r, th, dt, ok, _ = per_level[db][f]
                fh.write("%.0f,%d,%.6e,%.3f,%.4f,%d,%.1f\n"
                         % (f, db, r, AX.fold(th), dt, int(ok), data[1.00][(f, db)][1]))
    print("\n  wrote %s" % out)

    # ⭐ Also emit the -18 dBFS target in a3_blend_axis's EXACT CSV schema, so session 52's
    # impossibility test (`a3_correction_fit.py --sweep tones-set<X>`) can be re-run on the UNBIASED
    # target with ZERO changes to that tool. Deliberate: the question is whether the RESULT moves,
    # and editing the instrument in the same step would confound the two.
    alias = "build/a3_blend_axis_tones-set%s.csv" % args.set
    with open(alias, "w") as fh:
        fh.write("# read_a3_tones set %s, -18 dBFS, in a3_blend_axis's schema so a3_correction_fit\n"
                 "# can consume it unmodified. r/theta from NARROWBAND TONES (no harmonic bias);\n"
                 "# r_mdl/theta_mdl copied from the model's exact taps (%s).\n"
                 "# f,r_ped,theta_ped_deg,r_mdl,theta_mdl_deg,identified\n" % (args.set, args.dec_csv))
        for f in freqs:
            r, th, _, ok, _ = per_level[-18][f]
            if mdl is None:
                continue
            key = min(mdl, key=lambda x: abs(x - f))
            if abs(key - f) > 0.06 * f:
                continue
            rm, thm = mdl[key]
            fh.write("%.0f,%.6e,%.3f,%.6e,%.3f,%d\n"
                     % (f, r, AX.fold(th), rm, AX.fold(thm), int(ok)))
    print("  wrote %s  (feeds: python3.11 analysis/a3_correction_fit.py --sweep tones-set%s)"
          % (alias, args.set))


if __name__ == "__main__":
    main()
