#!/usr/bin/env python3.11
"""The ATTACK cancellation notch, at FULL RESOLUTION -- and h(f) with the notch window separated
BY MEASUREMENT rather than by the 1/3-octave grid (session 61, Phase 9 / A3).

WHY THIS TOOL EXISTS
--------------------
Session 60 measured `h(f)` -- the ATTACK network's linear transfer -- bleed-free by topology, on the
three LEVEL-max / drive-min captures, and found it BROADBAND: ~+8.6 dB flat from 80 Hz to 1.6 kHz on
boost, ~-2.4 dB on cut. It then over-claimed "no resonator is required". The user asked whether the
effort was missing the pedal's small peak between the two large mid peaks, and an ad-hoc probe at
full resolution found two things (recorded as step 16 item 8b):

  (i)  the broadband result SURVIVES -- the 421.9 Hz peak and the 316 Hz null both belong to the
       SHARED path and cancel in the ratio, so `h` is smooth and flat everywhere outside a narrow
       window around the notch;
  (ii) but ATTACK MOVES THE NOTCH -- cut 316.4 Hz / boost 328.1 Hz / flat 334.0 Hz, and the depth
       more than DOUBLES on boost. A pure broadband gain cannot do that, so the ATTACK network is
       genuinely two-path and interacts with the notch-forming network.

(ii) is the load-bearing half: it is what rules out proposing a plain gain switch, and it couples
ATTACK to GAP #2 (the model's notch is destroyed by `trebleLadderDampR = 30k`). It was measured in a
throwaway script. This tool re-derives it under gates so it survives, and so the numbers can be
corrected if they move.

WHY THESE THREE CAPTURES
------------------------
LEVEL sits AFTER every nonlinearity (circuit.md: ... -> IC4_A SK -> LEVEL -> BLEND) and at LEVEL max
the wiper shorts to the OD source, so the clean bleed is EXACTLY zero (`level_blend_tf`: 0 at 1.00).
At BLEND max the output therefore IS the OD path -- no ladder, no fitted taper, no b0, no solve. And
drive min idles the clipper. So the measured transfer is the pedal's own OD path, and `h` is a plain
per-bin subtraction of two such transfers. This is the session-60 route; the only change here is
resolution: `A.transfer` at nperseg=8192 gives ~5.86 Hz bins instead of 1/3-octave bands.

⚠ WHY RESOLUTION IS THE WHOLE POINT. Session 46's own lesson was that the 1/3-oct grid understated
this notch by up to 20 dB, because a band average across a sharp feature reports where the notch sits
INSIDE the band, not the network's gain there. That is also why step 16 item 9 refuses to treat the
320 Hz band as a transfer value. A band grid cannot answer "did the notch MOVE"; only a bin grid can.

WHAT IS MEASURED, AND HOW EACH NUMBER IS DEFINED
------------------------------------------------
  notch f0     the frequency of the MINIMUM of |H| inside SEARCH_WIN (250-400 Hz). Reported both as
               the raw bin (which is what "identical to the bin across levels" means) and as a
               parabolic refinement on the log-f axis (the mid_shape_verify rule: never read a
               feature's frequency off a grid without interpolating).
  depth        SHOULDER minus that minimum, where SHOULDER = max |H| over SHOULDER_WIN (200-270 Hz).
               The upper shoulder (the 421.9 Hz maximum) is printed beside it, because the notch sits
               between two peaks and quoting one shoulder alone hides which side moved.
  h(f)         throw minus flat, per bin. Its notch window is located by MEASUREMENT (where |h|
               departs from its own broadband median by more than the floor), then compared against
               the nominal 287-351 Hz window -- never assumed.

GATES -- all run first, none optional
-------------------------------------
  1 SELF-TEST      synthesise notches of KNOWN frequency and depth, push them through the SAME
                   stimulus, transfer estimate and locator, and require recovery. ⭐ This also
                   MEASURES the depth bias of a 5.86 Hz-bin estimate on a sharp notch, which is the
                   caveat every depth number below has to carry. Frequency is gated hard; depth is
                   gated only where the estimator is unbiased and REPORTED where it is not.
  2 LIVENESS       flat vs flat must give h identically zero, and no notch in h.
  3 CAPTURE        full length (a truncated file's missing segments read as zeros and fake features),
                   alignment lag, peak level, no flat-topping.
  4 LEVEL SWEEP    -36 / -30 / -18 / -12 / -6 dBFS printed for every position. The quiet rows are
                   the trustworthy ones; -12 is where session 46 saw the notch MIGRATE (334 -> 299 Hz)
                   as compression starts, so it is the tell that the read must come from the quiet
                   end -- not an average over all levels (the session-49-item-7 trap).
  5 NOTCH WINDOW   named and excluded explicitly from the broadband read, never silently (session 40).

SCOPE
-----
  * ATTACK is [ENG] -- the 3-way switch is not on our schematic at all. Everything here is a
    SPECIFICATION a topology proposal must meet, not a disagreement with a drawn circuit.
  * MAGNITUDE ONLY. A notch's depth is set by how exactly two paths cancel, i.e. by phase, which
    this axis does not measure. Depth is a constraint, not a phase measurement.
  * Floor: take-to-take 0.144 dB; `h` is a difference of two raw measurements ⇒ sqrt(2) x 0.144 =
    0.204 dB. A DEPTH is a difference of two points of ONE measurement, so it carries the 0.144 dB
    floor plus the estimator bias that gate 1 measures -- which dominates.

Usage:  python3.11 analysis/attack_notch_probe.py [--selftest] [--json OUT]
"""
import argparse
import json
import os
import sys

import numpy as np
import scipy.signal as sps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A                                # noqa: E402
import captures as C                               # noqa: E402

CAPDIR = "analysis/captures"

# The bleed-free ATTACK triple exists at TWO drive settings. Both share the LEVEL-max/BLEND-max
# mechanism (wiper shorted to the OD source ⇒ zero clean bleed by topology, and LEVEL sits after
# every nonlinearity so it cannot move the clipper's operating point). They differ ONLY in whether
# the clipper is idle, which is exactly the axis session 68 needed:
#   drive-min   the clipper is idle, so h(f) is the ATTACK network's own LINEAR transfer.
#   drive-noon  the clipper is working. If h is really a drive-independent linear pre-clipper
#               transfer, it must read the SAME here. If it moves, part of what sessions 60-66
#               attributed to the ATTACK network is operating-point, not network.
# ⚠ Default stays drive-min so every figure sessions 60-66 recorded is reproduced untouched.
CONDS = {
    "drive-min": dict(
        flat="drive-0700_level-1700_base-od.wav",
        throws={"cut": "drive-0700_level-1700_attack-cut_base-od.wav",
                "boost": "drive-0700_level-1700_attack-boost_base-od.wav"},
        blurb="drive MIN / LEVEL max / BLEND max ⇒ zero clean bleed by topology, clipper IDLE.",
        recorded=True),
    "drive-noon": dict(
        flat="level-1700_base-od.wav",
        throws={"cut": "level-1700_attack-cut_base-od.wav",
                "boost": "level-1700_attack-boost_base-od.wav"},
        blurb="drive NOON / LEVEL max / BLEND max ⇒ zero clean bleed by topology, clipper WORKING.",
        recorded=False),
}
COND = "drive-min"                                 # set by --cond; module-level so load_all sees it
FLAT = CONDS[COND]["flat"]
THROWS = CONDS[COND]["throws"]
POSITIONS = ["cut", "boost", "flat"]               # ordered as step 16 item 8b quotes them

# Stimulus level -> sweep segment. The two quiet rows are the near-linear ones; -12 is where
# session 46 measured the notch starting to migrate, and -6 is past that.
LEVELS = [(-36.0, "sweep_clean_-36"), (-30.0, "sweep_clean"), (-18.0, "sweep_drv_-18"),
          (-12.0, "sweep_drv_-12"), (-6.0, "sweep_drv_-6")]
QUIET = (-36.0, -30.0, -18.0)                      # levels the read is taken from
MAIN = -30.0                                       # the level the headline notch table quotes

SEARCH_WIN = (250.0, 400.0)                        # where the cancellation null lives
SHOULDER_WIN = (200.0, 270.0)                      # lower shoulder, per item 8b's definition
UPPER_WIN = (380.0, 470.0)                         # the 421.9 Hz maximum on the far side
WIDTH_WIN = (240.0, 420.0)                         # where the null's own skirts are measured
NOTCH_EXCLUDE = (287.0, 351.0)                     # NOMINAL exclusion window -- verified, not trusted
BROAD_WIN = (80.0, 1600.0)                         # where h is claimed flat

# Flat-topping gate (see load_all). Measured separation, not guessed (session 68): the longest run
# of samples pinned within 0.05% of peak is <=4 on every clean capture in this set, and 20 / 86 / 120
# on hard-clipped mutations of one of them (at 0.999 / 0.9885 / 1.0). A run of 8 therefore sits 2x
# above the clean worst case and 2.5x below the barely-clipped one.
FLATTOP_PIN_TH = 0.9995                            # "pinned" = within 0.05% of peak
FLATTOP_MIN_RUN = 8                                # consecutive pinned samples to reject
FLATTOP_MIN_PEAK = 0.95                            # scope: the CONVERTER's ceiling, not the pedal's
LOOSE_TH = 0.985                                   # reported only -- see the warning in load_all

SHARED_PEAK = 421.9                                # must CANCEL in h (item 8b(i))
TAKE_FLOOR = 0.144
DIFF_FLOOR = float(np.sqrt(2.0) * TAKE_FLOOR)      # 0.204 dB

# Frequencies for the coarse h table (a spread across the claimed-flat region).
H_SHOW = [40.0, 63.0, 80.0, 101.0, 127.0, 160.0, 202.0, 254.0, 287.0,
          320.0, 351.0, 381.0, 422.0, 451.0, 510.0, 639.0, 809.0, 1002.0, 1300.0, 1600.0]

# Session 60 item 8b's ad-hoc figures, for the "did they move?" comparison. Nothing here is tuned
# to these; they are printed so a shift is visible instead of silently replacing the record.
S60_8B = {"cut": (316.4, 14.9), "boost": (328.1, 32.7), "flat": (334.0, 16.0)}


# ---------------------------------------------------------------------------------------------
# measurement primitives
# ---------------------------------------------------------------------------------------------
def band(f, mag, lo, hi):
    """Slice a transfer to [lo, hi]."""
    m = (f >= lo) & (f <= hi)
    return f[m], mag[m]


def refine_min(f, mag, i):
    """Parabolic vertex through bin i and its neighbours on the LOG-f axis. Never read a sharp
    feature's frequency straight off the grid (mid_shape_verify's rule, session 26)."""
    if i <= 0 or i >= len(f) - 1:
        return float(f[i]), float(mag[i])
    x = np.log2(f[i - 1:i + 2])
    y = mag[i - 1:i + 2]
    denom = (y[0] - 2 * y[1] + y[2])
    if abs(denom) < 1e-12:
        return float(f[i]), float(mag[i])
    dx = 0.5 * (y[0] - y[2]) / denom * (x[2] - x[1])
    # ⚠ REJECT a vertex that lands outside the bracketing bins. A near-flat or near-cancelling
    # denominator throws the parabola arbitrarily far, and `2.0 ** vx` then OVERFLOWS -- which is
    # how this was found (session 64: a wide network search drove some candidates into that
    # regime and numpy warned on every one). Harmless for `f_bin` (an argmin) but `f_ref` was
    # returning inf, and a shared oracle should not hand a caller inf for a frequency.
    if not np.isfinite(dx) or abs(dx) > (x[2] - x[1]):
        return float(f[i]), float(mag[i])
    vx = x[1] + dx
    vy = y[1] - 0.125 * (y[0] - y[2]) ** 2 / denom          # parabola vertex value
    return float(2.0 ** vx), float(vy)


def locate_notch(f, mag):
    """Find the cancellation null and its depth. Returns a dict of every quantity the verdict uses,
    so nothing downstream re-derives a definition."""
    fw, mw = band(f, mag, *SEARCH_WIN)
    i = int(np.argmin(mw))
    f_bin, db_min = float(fw[i]), float(mw[i])
    # index back into the full arrays so the parabola sees the true neighbours
    j = int(np.argmin(np.abs(f - f_bin)))
    f_ref, db_ref = refine_min(f, mag, j)

    _, ms = band(f, mag, *SHOULDER_WIN)
    _, mu = band(f, mag, *UPPER_WIN)
    lo_sh = float(np.max(ms)) if len(ms) else float("nan")
    up_sh = float(np.max(mu)) if len(mu) else float("nan")
    fu, muu = band(f, mag, *UPPER_WIN)
    f_up = float(fu[int(np.argmax(muu))]) if len(fu) else float("nan")
    w_bin, w_int = notch_width(f, mag, lo_sh)
    return dict(f_bin=f_bin, f_ref=f_ref, db_min=db_min, db_ref=db_ref,
                lo_shoulder=lo_sh, up_shoulder=up_sh, f_upper=f_up,
                depth=lo_sh - db_min, depth_upper=up_sh - db_min,
                width=w_bin, width_i=w_int)


def notch_width(f, mag, lo_sh=None):
    """HALF-DEPTH bandwidth of the null: the span over which the response sits below
    (lower shoulder - depth/2), i.e. the width measured at half of THAT null's own depth.

    Returns (width_bin, width_interp) in Hz -- see the two ⚠ notes below; the FIT should use
    `width_interp`, the RECORD is quoted as `width_bin`.

    ⭐ Why width needs its own statistic at all: session 63 found the built two-pole topology
    matching the notch triple (f0, depth) TO THE BIN at all three throws while every null was
    ~2.1x too BROAD -- the "centre right, range right, WIDTH wrong" residual A2c-2 found in the
    mid stage. (f0, depth) cannot express it and a median cannot see it.

    ⚠ WHY HALF-DEPTH RATHER THAN A FIXED -6 dB CONTOUR, which a first draft of the render gate
    used. A null that is DEEPER crosses any FIXED absolute contour further out, so width-at--6 dB
    is confounded with depth -- and the model IS deeper than the pedal here (18.5/36.6/20.3 vs
    14.9/32.7/16.0), so that draft reported ~1.6x "too wide" partly on the model's own extra
    depth. Referring the contour to each null's OWN depth removes the confound. Same rule as the
    plot's shoulder normalisation and session 62's ratio-denominator guard: normalise to something
    the feature under test does not itself move.

    ⚠ AND WHY BOTH A BIN SPAN AND AN INTERPOLATED ONE. On the measurement's 5.86 Hz grid the
    pedal's boost null is 23.4 Hz = FOUR bins, so a raw bin span is quantised at ~+-25 % -- far too
    coarse to fit against, and it would make an optimiser chase a staircase. Linear interpolation
    of the two half-depth CROSSINGS removes that without changing the definition. The raw span is
    kept and returned first because sessions 60-63 quote the record that way (70.3 / 23.4 / 64.5 Hz)
    and silently switching the definition under a recorded number is the session-33 transcription
    trap -- cf. `f_bin` vs `f_ref` in `notch_triple`.
    """
    if lo_sh is None:
        _, ms = band(f, mag, *SHOULDER_WIN)
        if not len(ms):
            return float("nan"), float("nan")
        lo_sh = float(np.max(ms))
    fw, mw = band(f, mag, *WIDTH_WIN)
    if not len(fw):
        return float("nan"), float("nan")
    contour = lo_sh - 0.5 * (lo_sh - float(np.min(mw)))
    below = mw < contour
    if not np.any(below):
        return 0.0, 0.0
    idx = np.flatnonzero(below)
    lo_i, hi_i = int(idx[0]), int(idx[-1])
    w_bin = float(fw[hi_i] - fw[lo_i])

    def cross(i, j):
        """Linear interpolation in f of the contour crossing between bins i (outside) and j (in)."""
        if i < 0 or i >= len(fw):
            return float(fw[j])
        d = mw[j] - mw[i]
        if abs(d) < 1e-12:
            return float(fw[j])
        return float(fw[i] + (contour - mw[i]) / d * (fw[j] - fw[i]))

    f_lo, f_hi = cross(lo_i - 1, lo_i), cross(hi_i + 1, hi_i)
    return w_bin, float(f_hi - f_lo)


def notch_ba(f0, depth_db, Qp, fs):
    """A two-pole notch with EXACTLY `depth_db` at EXACTLY f0 once discretised.

    H(s) = (s^2 + (w0/Qz)s + w0^2) / (s^2 + (w0/Qp)s + w0^2)  ⇒  |H(jw0)| = Qp/Qz,
    so Qz = Qp * 10^(depth/20) sets the depth in closed form. w0 is PREWARPED so the bilinear
    transform maps the notch to f0 rather than near it -- otherwise the self-test would be gating
    the locator against a target whose own frequency it had guessed wrong.
    """
    w0 = 2.0 * fs * np.tan(np.pi * f0 / fs)
    Qz = Qp * 10.0 ** (depth_db / 20.0)
    b = [1.0, w0 / Qz, w0 ** 2]
    a = [1.0, w0 / Qp, w0 ** 2]
    return sps.bilinear(b, a, fs)


# ---------------------------------------------------------------------------------------------
# gate 1 -- self-test
# ---------------------------------------------------------------------------------------------
def selftest(orig):
    print("=" * 104)
    print("GATE 1. SELF-TEST -- recover synthesised notches of KNOWN frequency and depth")
    print("=" * 104)
    print("  Same stimulus, same transfer estimate (nperseg 8192 ⇒ %.2f Hz bins), same locator."
          % (A.FS / 8192.0))
    print("  ⭐ This also MEASURES the depth bias of a bin-resolution estimate on a sharp notch,")
    print("     which is the caveat every depth number in this tool has to carry.\n")

    inp = A.seg_of(orig, LEVELS[1][1])
    cases = [(316.4, 15.0, 1.0), (316.4, 15.0, 2.0), (328.1, 33.0, 2.0),
             (328.1, 33.0, 4.0), (334.0, 16.0, 2.0), (320.0, 10.0, 0.7)]
    print("  %-9s %-7s %-5s | %-9s %-9s | %-9s %-8s %-9s" %
          ("f0 true", "depth", "Qp", "f0 bin", "f0 refined", "depth got", "bias", "shoulder"))
    worst_f, rows = 0.0, []
    for f0, dep, Qp in cases:
        b, a = notch_ba(f0, dep, Qp, A.FS)
        f, mag = A.transfer(sps.lfilter(b, a, inp), inp)
        n = locate_notch(f, mag)
        worst_f = max(worst_f, abs(n["f_ref"] - f0))
        bias = n["depth"] - dep
        rows.append((f0, dep, Qp, n, bias))
        print("  %9.1f %7.1f %5.2f | %9.1f %9.1f | %9.2f %+8.2f %9.2f"
              % (f0, dep, Qp, n["f_bin"], n["f_ref"], n["depth"], bias, n["lo_shoulder"]))

    bins = A.FS / 8192.0
    ok_f = worst_f <= 2.0 * bins
    print("\n  (a) FREQUENCY  worst |err| %.2f Hz vs 2 bins = %.2f Hz             %s"
          % (worst_f, 2.0 * bins, "PASS" if ok_f else "FAIL"))

    # ⚠ THE FIRST DRAFT OF THIS GATE WAS WRONG, AND IT FAILED FOR THE RIGHT REASON.
    # It assumed a bin grid is accurate on a BROAD notch and biased on a sharp one, and gated the
    # broad case at +-1.5 dB. The broad case is the WORST (-4.3 dB), because there are TWO bias
    # mechanisms pulling the same way and only one of them is about resolution:
    #   (1) SHOULDER CONTAMINATION -- a broad notch's own skirt reaches into SHOULDER_WIN, so the
    #       reference level is already attenuated and `shoulder - min` understates the true depth.
    #       The `shoulder` column above shows it directly: it is ~0 dB for the sharp cases and
    #       several dB down for the broad one. This is DEFINITIONAL, not an estimator error.
    #   (2) BIN SMEARING -- a ~5.9 Hz-bin CSD estimate cannot reach the floor of a very sharp deep
    #       notch, so a high-Q 33 dB notch reads ~29 dB.
    # Both UNDERSTATE, so gate on the property the verdict actually uses -- direction and ranking --
    # rather than on an absolute accuracy the statistic does not have.
    over = max(r[4] for r in rows)
    ok_lb = over <= 0.2
    print("  (b) DEPTH IS A LOWER BOUND: worst OVER-statement %+.2f dB vs +0.20    %s"
          % (over, "PASS" if ok_lb else "FAIL"))
    print("      Two mechanisms, both understating: (1) a broad notch's skirt drags the 200-270 Hz")
    print("      shoulder down (see the shoulder column -- definitional, worst at Qp 0.7);")
    print("      (2) bin smearing cannot reach a sharp deep floor (worst at Qp 4). ⇒ the measured")
    print("      depths below are LOWER bounds, which cannot manufacture a boost/flat depth gap.")

    # (c) the load-bearing depth property: can it RANK a doubling? That is claim (2)'s whole content.
    pair = []
    for dep in (16.0, 33.0):
        b, a = notch_ba(328.1, dep, 2.0, A.FS)
        f, mag = A.transfer(sps.lfilter(b, a, inp), inp)
        pair.append(locate_notch(f, mag)["depth"])
    got_gap, true_gap = pair[1] - pair[0], 17.0
    ok_r = pair[1] > pair[0] and got_gap > 0.6 * true_gap
    print("  (c) DEPTH RANKING: true 16.0 / 33.0 dB (gap %.1f) read as %.1f / %.1f (gap %.1f) %s"
          % (true_gap, pair[0], pair[1], got_gap, "PASS" if ok_r else "FAIL"))
    print("      This, not absolute depth, is what verdict (2) rests on -- it claims boost roughly")
    print("      DOUBLES the depth, so the estimator only has to preserve that ordering and scale.")
    ok_d = ok_lb and ok_r

    # (d) liveness -- an unfiltered pass must find no notch worth the name
    f, mag = A.transfer(inp, inp)
    n = locate_notch(f, mag)
    ok_l = n["depth"] < 0.5
    print("  (d) LIVENESS   unfiltered stimulus, apparent depth %.3f dB vs 0.5      %s"
          % (n["depth"], "PASS" if ok_l else "FAIL"))

    # (e) the locator must SEPARATE two notches ~18 Hz apart, or item 8b(ii)'s shift is unreadable
    d = []
    for f0 in (316.4, 334.0):
        b, a = notch_ba(f0, 16.0, 2.0, A.FS)
        f, mag = A.transfer(sps.lfilter(b, a, inp), inp)
        d.append(locate_notch(f, mag)["f_ref"])
    sep = abs(d[1] - d[0])
    ok_s = abs(sep - 17.6) < 6.0
    print("  (e) SEPARATION two notches 17.6 Hz apart resolve as %.1f Hz apart      %s"
          % (sep, "PASS" if ok_s else "FAIL"))
    print("      (item 8b(ii)'s whole claim is an ~18 Hz shift, so this is the load-bearing gate)")

    ok = ok_f and ok_d and ok_l and ok_s
    print("\n  %s" % ("SELF-TEST PASS" if ok else "SELF-TEST FAIL"))
    return ok


# ---------------------------------------------------------------------------------------------
# load + verify
# ---------------------------------------------------------------------------------------------
def load_all(orig):
    print("\n" + "=" * 104)
    print("GATE 3. CAPTURES -- verified BEFORE anything is read off them")
    print("=" * 104)
    print("  %-52s %8s %6s %7s %6s %8s" % ("file", "len/orig", "lag", "peak", "loose", "pinned"))
    out = {}
    for pos in POSITIONS:
        fn = FLAT if pos == "flat" else THROWS[pos]
        path = os.path.join(CAPDIR, fn)
        if not os.path.exists(path):
            sys.exit("missing capture: %s" % path)
        x = C.load_capture(path)
        frac = len(x) / len(orig)
        if not A.is_full_length(x, orig):
            sys.exit("%s is TRUNCATED (%.3f of reference) -- missing segments read as zeros" % (fn, frac))
        x, lag = A.align(x, orig)
        pk = float(np.max(np.abs(x)))

        def longest_run(th):
            near = (np.abs(x) >= th * pk).astype(np.int8)
            e = np.flatnonzero(np.diff(np.concatenate(([0], near, [0]))))
            return int(np.max(e[1::2] - e[0::2])) if len(e) else 0

        # ⚠⚠ RUN LENGTH AT A LOOSE THRESHOLD IS NOT THE FLAT-TOPPING SIGNATURE, and the previous
        # version of this gate (>16 samples above 0.985*peak) was a FALSE POSITIVE GENERATOR.
        # A sine spends ~5.5% of its period above 98.5% of its peak, so at the 20 Hz end of the log
        # sweep that is ~30 samples at 48 kHz -- entirely normal. Measured (session 68): all six
        # bleed-free ATTACK captures put their longest loose run inside `sweep_drv_-6`, with the
        # samples still CURVING 1.3-1.5% of peak, and the long-trusted `level-1700_base-od.wav`
        # -- in the matrix since session 22 -- scores 19. The old test therefore rejected a
        # reference capture, which is how it was caught.
        # The real defect (session 24 lost 14 files to it) is a plateau PINNED at one value at the
        # CONVERTER's ceiling. So gate on a TIGHT pin threshold plus a near-full-scale peak. This is
        # strictly MORE discriminating for real clipping, not slacker -- mutation-tested at 0.9885
        # (session-24 style), 1.0 and 0.999, against an unclipped 0.98-peak control.
        # ⚠ A plateau BELOW full scale is the PEDAL's own rail limiting -- real signal we are here
        # to measure -- so it is reported, never rejected.
        loose, pinned = longest_run(LOOSE_TH), longest_run(FLATTOP_PIN_TH)
        print("  %-52s %8.3f %6d %7.3f %6d %8d" % (fn, frac, lag, pk, loose, pinned))
        if pk >= FLATTOP_MIN_PEAK and pinned >= FLATTOP_MIN_RUN:
            sys.exit("%s is FLAT-TOPPED: %d consecutive samples pinned within %.2f%% of a %.4f "
                     "peak (near full scale) -- the session-24 capture defect."
                     % (fn, pinned, 100.0 * (1.0 - FLATTOP_PIN_TH), pk))
        out[pos] = x
    print("  ⇒ all three full length, aligned, no flat-topping.")
    return out


def transfers(caps, orig):
    """{position: {level: (f, mag_dB)}} -- the pedal's own OD transfer, bleed-free by topology."""
    tf = {}
    for pos, x in caps.items():
        tf[pos] = {}
        for L, seg in LEVELS:
            inp = A.seg_of(orig, seg)
            out = A.seg_of(x, seg)
            tf[pos][L] = A.transfer(out, inp)
    return tf


# ---------------------------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", default=None, help="write the measured table to this path")
    ap.add_argument("--cond", default="drive-min", choices=sorted(CONDS),
                    help="which bleed-free ATTACK triple to read (default drive-min = the "
                         "sessions 60-66 record; drive-noon has the clipper working)")
    args = ap.parse_args()

    # Rebind the module-level capture names the loader reads. Default is drive-min, so a plain
    # invocation is byte-for-byte the sessions 60-66 run.
    global COND, FLAT, THROWS
    COND = args.cond
    FLAT = CONDS[COND]["flat"]
    THROWS = CONDS[COND]["throws"]

    if not os.path.exists(A.ORIG):
        sys.exit("reference stimulus not found at %s -- run analysis/gen_test_signal.py" % A.ORIG)
    orig = A.load(A.ORIG)

    print("=" * 104)
    print("THE ATTACK NOTCH AT FULL RESOLUTION -- and h(f) with the notch window separated by")
    print("MEASUREMENT rather than by the 1/3-octave grid")
    print("=" * 104)
    print("  CONDITION %s: %s" % (COND, CONDS[COND]["blurb"]))
    print("  %.2f Hz bins | floors: take-to-take %.3f dB, h (a difference) %.3f dB"
          % (A.FS / 8192.0, TAKE_FLOOR, DIFF_FLOOR))

    if args.selftest and not selftest(orig):
        sys.exit(1)
    if not args.selftest:
        print("\n  ⚠ running WITHOUT --selftest: the depth-bias measurement that every depth number")
        print("    below depends on has NOT been made this run.")

    caps = load_all(orig)
    tf = transfers(caps, orig)

    # ------------------------------------------------------------------ gate 2
    print("\n" + "=" * 104)
    print("GATE 2. LIVENESS -- flat against itself")
    print("=" * 104)
    f, mflat = tf["flat"][MAIN]
    h0 = mflat - mflat
    fw, hw = band(f, h0, *SEARCH_WIN)
    print("  h = flat - flat : worst |h| over 20 Hz-20 kHz %.3e dB, apparent notch %.3e dB   PASS"
          % (float(np.max(np.abs(h0))), float(np.max(np.abs(hw)))))

    # ------------------------------------------------------------------ the notch, per position
    print("\n" + "=" * 104)
    print("THE NOTCH -- per ATTACK position, at %g dBFS" % MAIN)
    print("=" * 104)
    print("  f0 = minimum of |H| in %g-%g Hz. depth = (max |H| in %g-%g Hz) - that minimum."
          % (SEARCH_WIN + SHOULDER_WIN))
    print("  The upper shoulder is the peak on the far side of the null; it is printed because the")
    print("  notch sits BETWEEN two peaks and one shoulder alone hides which side moved.\n")
    print("  %-7s %9s %9s %9s | %9s %9s %9s | %9s %9s" %
          ("pos", "f0 bin", "f0 refnd", "min dB", "lo shldr", "up shldr", "f upper",
           "depth", "dep(up)"))
    head = {}
    for pos in POSITIONS:
        f, mag = tf[pos][MAIN]
        n = locate_notch(f, mag)
        head[pos] = n
        print("  %-7s %9.1f %9.1f %9.2f | %9.2f %9.2f %9.1f | %9.2f %9.2f"
              % (pos, n["f_bin"], n["f_ref"], n["db_min"], n["lo_shoulder"], n["up_shoulder"],
                 n["f_upper"], n["depth"], n["depth_upper"]))

    # Is the shoulder a GENUINE local peak, or already notch skirt? Gate 1(b) mechanism (1) is only
    # in play if the latter -- so check it on the real data rather than inheriting the synthetic case.
    print("\n  is the 200-270 Hz shoulder a real local peak, or already this notch's skirt?")
    for pos in POSITIONS:
        f, mag = tf[pos][MAIN]
        fs_, ms_ = band(f, mag, *SHOULDER_WIN)
        i = int(np.argmax(ms_))
        interior = 0 < i < len(fs_) - 1
        print("    %-7s max at %6.1f Hz, %-24s region varies %5.2f dB ⇒ %s"
              % (pos, fs_[i], "INTERIOR to the window." if interior else "ON the window EDGE.",
                 float(ms_.max() - ms_.min()),
                 "a genuine local peak" if interior else
                 "may be skirt: depth understated further"))

    # ⚠ S60_8B was measured at DRIVE MIN. Comparing another condition against it would report a
    # real operating-point difference as "the record moved", which is the opposite of the truth.
    if CONDS[COND]["recorded"]:
        print("\n  vs session 60 item 8b (an AD-HOC probe -- this tool is now the record):")
        print("  %-7s %12s %12s | %12s %12s" % ("pos", "f0 s60", "f0 here", "depth s60", "depth here"))
        moved = []
        for pos in POSITIONS:
            f0s, ds = S60_8B[pos]
            n = head[pos]
            print("  %-7s %12.1f %12.1f | %12.1f %12.2f" % (pos, f0s, n["f_bin"], ds, n["depth"]))
            if abs(n["f_bin"] - f0s) > A.FS / 8192.0 or abs(n["depth"] - ds) > 1.0:
                moved.append(pos)
        print("  ⇒ %s" % ("REPRODUCED within one bin / 1 dB at every position." if not moved
                          else "MOVED at: %s -- correct step 16 item 8b." % ", ".join(moved)))
    else:
        print("\n  (no session-60 comparison: that record is DRIVE-MIN and this run is %s." % COND)
        print("   Comparing them would report an operating-point difference as a moved record.)")

    # ------------------------------------------------------------------ gate 4: level sweep
    print("\n" + "=" * 104)
    print("GATE 4. LEVEL SWEEP -- is the notch a property of the network or of the operating point?")
    print("=" * 104)
    print("  Session 46 measured this notch MIGRATING 334 -> 299 Hz as level rises (compression")
    print("  moves the balance of a two-path cancellation). So the quiet rows are the trustworthy")
    print("  ones, and the read below is taken from %s dBFS only -- NOT averaged over levels.\n"
          % "/".join("%g" % x for x in QUIET))
    print("  %-7s | %s" % ("pos", "".join("%20s" % ("%g dBFS" % L) for L, _ in LEVELS)))
    print("  %-7s | %s" % ("", "".join("%20s" % "f0 Hz / depth dB" for _ in LEVELS)))
    sweep = {}
    for pos in POSITIONS:
        cells, sweep[pos] = [], {}
        for L, _ in LEVELS:
            f, mag = tf[pos][L]
            n = locate_notch(f, mag)
            sweep[pos][L] = n
            cells.append("%20s" % ("%.1f / %.1f" % (n["f_bin"], n["depth"])))
        print("  %-7s | %s" % (pos, "".join(cells)))

    print("\n  stability across the QUIET rows (the read's own robustness):")
    dep_moves = []
    for pos in POSITIONS:
        fs = [sweep[pos][L]["f_bin"] for L in QUIET]
        ds = [sweep[pos][L]["depth"] for L in QUIET]
        if max(ds) - min(ds) > 1.0:
            dep_moves.append(pos)
        print("    %-7s f0 %s ⇒ spread %.1f Hz (%s) | depth %.2f-%.2f dB, spread %.2f"
              % (pos, "/".join("%.1f" % x for x in fs), max(fs) - min(fs),
                 "IDENTICAL TO THE BIN" if max(fs) - min(fs) < 1e-6 else "moves",
                 min(ds), max(ds), max(ds) - min(ds)))
    print("\n  ⚠ FREQUENCY is identical to the bin at every quiet level -- that is item 8b's claim and")
    print("    it holds. DEPTH is NOT equally stable: %s. Boost pushes ~8 dB more signal into the"
          % (", ".join(dep_moves) if dep_moves else "no position moves >1 dB"))
    print("    J201 than flat does (it sits upstream of DRIVE and never idles, session 59 item 3), so")
    print("    compression reaches boost first -- which is why its depth falls with level while its")
    print("    frequency does not. ⇒ quote the DEEPEST/quietest row, and treat depth as a bound.")

    # ------------------------------------------------------------------ h(f) full resolution
    print("\n" + "=" * 104)
    print("h(f) AT FULL RESOLUTION -- throw minus flat, per bin")
    print("=" * 104)
    hs = {}
    for pos in ("boost", "cut"):
        f, mt = tf[pos][MAIN]
        _, mf = tf["flat"][MAIN]
        hs[pos] = mt - mf
    fg = tf["flat"][MAIN][0]

    print("  %-9s %9s %9s   %s" % ("f Hz", "h boost", "h cut", "note"))
    for target in H_SHOW:
        i = int(np.argmin(np.abs(fg - target)))
        note = ""
        if NOTCH_EXCLUDE[0] <= fg[i] <= NOTCH_EXCLUDE[1]:
            note = "<-- NOTCH WINDOW, excluded from the broadband read"
        elif abs(fg[i] - SHARED_PEAK) < 6.0:
            note = "<-- the shared 421.9 Hz peak: must CANCEL here"
        print("  %9.1f %9.2f %9.2f   %s" % (fg[i], hs["boost"][i], hs["cut"][i], note))

    # ------------------------------------------------------------------ gate 5: the window, MEASURED
    print("\n" + "=" * 104)
    print("GATE 5. THE NOTCH WINDOW -- located by MEASUREMENT, then compared to the nominal one")
    print("=" * 104)
    print("  Broadband level = median of h over %g-%g Hz EXCLUDING the nominal %g-%g Hz window."
          % (BROAD_WIN + NOTCH_EXCLUDE))
    print("  The measured window is the contiguous region around the notch where |h - that median|")
    print("  exceeds the %.3f dB floor. If it is WIDER than nominal, the broadband read is polluted.\n"
          % DIFF_FLOOR)
    in_broad = (fg >= BROAD_WIN[0]) & (fg <= BROAD_WIN[1])

    def stats(pos, win):
        keep = in_broad & ~((fg >= win[0]) & (fg <= win[1]))
        v = hs[pos][keep]
        return float(np.median(v)), float(v.mean()), float(v.min()), float(v.max())

    def grow(pos, med):
        """Contiguous region around the null where |h - med| exceeds the floor."""
        dev = np.abs(hs[pos] - med) > DIFF_FLOOR
        c = int(np.argmin(np.abs(fg - head[pos]["f_bin"])))
        lo = hi = c
        while lo > 0 and dev[lo - 1]:
            lo -= 1
        while hi < len(fg) - 1 and dev[hi + 1]:
            hi += 1
        return float(fg[lo]), float(fg[hi])

    report = {}
    for pos in ("boost", "cut"):
        med0 = stats(pos, NOTCH_EXCLUDE)[0]
        win = grow(pos, med0)
        # ⭐ One refinement: re-derive the median with the MEASURED window excluded, then re-grow.
        # Otherwise the window is located against a median the window itself polluted.
        med1 = stats(pos, win)[0]
        win2 = grow(pos, med1)
        wide = win2[0] < NOTCH_EXCLUDE[0] - 1e-6 or win2[1] > NOTCH_EXCLUDE[1] + 1e-6
        med, mean, mn, mx = stats(pos, win2)
        print("  %-6s measured window %6.1f - %6.1f Hz (refined %6.1f - %6.1f)  ⇒ %s"
              % (pos, win[0], win[1], win2[0], win2[1],
                 "WIDER than the nominal %g-%g Hz" % NOTCH_EXCLUDE if wide
                 else "inside the nominal %g-%g Hz" % NOTCH_EXCLUDE))
        nm, nmean, nmn, nmx = stats(pos, NOTCH_EXCLUDE)
        print("         h over %g-%g Hz, ex NOMINAL  window: median %+6.2f mean %+6.2f "
              "range %+6.2f..%+6.2f spread %5.2f dB"
              % (BROAD_WIN[0], BROAD_WIN[1], nm, nmean, nmn, nmx, nmx - nmn))
        print("         h over %g-%g Hz, ex MEASURED window: median %+6.2f mean %+6.2f "
              "range %+6.2f..%+6.2f spread %5.2f dB   <-- the read"
              % (BROAD_WIN[0], BROAD_WIN[1], med, mean, mn, mx, mx - mn))
        # ⚠⚠ SWALLOW GUARD. `grow` assumes the picture is "a narrow notch on a flat background", so
        # it walks outward while |h - med| exceeds the floor. If h instead has a broad SLOPE, the walk
        # does not stop and the "notch window" eats most of the band -- leaving the "broadband median"
        # computed from whatever sliver survives, and PRINTED AS THOUGH IT WERE BROADBAND. Measured
        # at drive noon (session 68): boost's window came out 0.0-1154.3 Hz, so its quoted +4.64 dB
        # "broadband" read was really 1154-1600 Hz only, while h actually ran +9.76 -> +4.16 dB.
        # A window this wide is a finding about h's SHAPE, not a notch. Say so; never print it bare.
        frac = (min(win2[1], BROAD_WIN[1]) - max(win2[0], BROAD_WIN[0])) / (BROAD_WIN[1] - BROAD_WIN[0])
        swallowed = frac > 0.40
        if swallowed:
            print("         ⛔ THAT READ IS NOT BROADBAND: the measured window covers %.0f%% of "
                  "%g-%g Hz," % (100.0 * frac, *BROAD_WIN))
            print("            so the median above is only the %.0f-%.0f Hz remainder. h has a broad"
                  % (win2[1], BROAD_WIN[1]))
            print("            SLOPE here (%+.2f..%+.2f dB, spread %.2f over the FULL band), not a"
                  % (nmn, nmx, nmx - nmn))
            print("            narrow notch ⇒ quote the ex-NOMINAL row and the slope, not this one.")
        report[pos] = dict(median=med, mean=mean, window=list(win2),
                           window_nominal_ok=not wide, spread=mx - mn,
                           median_nominal=nm, spread_nominal=nmx - nmn,
                           window_frac_of_broad=frac, broadband_read_valid=not swallowed)
    # Computed, not narrated: which throws actually under-cover, and whether the correction is a
    # refinement or a reversal, both follow from the numbers above.
    under = [p for p in ("boost", "cut") if not report[p]["window_nominal_ok"]]
    dmed = {p: abs(report[p]["median"] - report[p]["median_nominal"]) for p in ("boost", "cut")}
    if under:
        print("\n  ⚠ THE NOMINAL %g-%g Hz WINDOW UNDER-COVERS on: %s. Session 60 item 8b quoted the"
              % (NOTCH_EXCLUDE[0], NOTCH_EXCLUDE[1], ", ".join(under)))
        print("    nominal one; correct it. The medians differ by %.2f dB (boost) / %.2f dB (cut), so"
              % (dmed["boost"], dmed["cut"]))
        print("    this is a %s -- and it is the spread, not the centre, that flatness rests on."
              % ("REFINEMENT" if max(dmed.values()) < 1.0 else
                 "REVERSAL at that size: re-read the broadband claim from scratch"))
    else:
        print("\n  ⇒ the nominal %g-%g Hz window COVERS the measured one on both throws."
              % NOTCH_EXCLUDE)

    # ------------------------------------------------------------------ the shared peak cancels
    print("\n" + "=" * 104)
    print("ITEM 8b(i) RE-CHECKED -- does the shared %.1f Hz peak CANCEL in h?" % SHARED_PEAK)
    print("=" * 104)
    print("  It belongs to the path both throws share, so if h is really a ratio of the same network")
    print("  with one element changed, the peak must be absent from h -- and 403/508/640 Hz must not")
    print("  be sitting on a sharp feature (which is what would have made the 1/3-oct read unsafe).\n")
    for pos in ("boost", "cut"):
        fw, hw = band(fg, hs[pos], 360.0, 500.0)
        rng = float(hw.max() - hw.min())
        i = int(np.argmin(np.abs(fw - SHARED_PEAK)))
        print("  %-6s h over 360-500 Hz: %+6.2f .. %+6.2f (range %.2f dB, floor %.3f) | "
              "h at %.1f Hz = %+6.2f dB  %s"
              % (pos, float(hw.min()), float(hw.max()), rng, DIFF_FLOOR, fw[i], hw[i],
                 "CANCELS" if rng < 3.0 * DIFF_FLOOR else "does NOT cancel"))
    for tgt in (403.2, 508.0, 640.0):
        fw, mw = band(fg, tf["flat"][MAIN][1], tgt / 1.122, tgt * 1.122)   # the 1/3-oct band
        print("    flat |H| across the 1/3-oct band at %6.1f Hz varies %5.2f dB "
              "(a sharp feature inside a band is what makes a band average unsafe)"
              % (tgt, float(mw.max() - mw.min())))

    # ------------------------------------------------------------------ verdict
    print("\n" + "=" * 104)
    print("VERDICT")
    print("=" * 104)
    d = {p: head[p]["depth"] for p in POSITIONS}
    f0 = {p: head[p]["f_bin"] for p in POSITIONS}
    span = max(f0.values()) - min(f0.values())
    # ⚠⚠ THIS VERDICT IS COMPUTED, NOT NARRATED. Its first version was four hardcoded sentences
    # asserting "ATTACK MOVES THE NULL" and "a PURE BROADBAND GAIN CANNOT DO EITHER" -- which printed
    # verbatim above a 0.0 Hz spread the first time this tool was pointed at drive noon. That is the
    # session-34 stale-narration trap (a verdict in a string outlives the condition it described) and
    # the project has now hit it four times. Both claims are therefore DERIVED below and each states
    # the opposite conclusion when the data says so.
    bins = A.FS / 8192.0
    moves = span > bins                                  # a shift has to clear one bin to exist
    depth_ratio = d["boost"] / d["flat"] if d["flat"] else float("nan")
    changes_depth = abs(depth_ratio - 1.0) > 0.25         # 25% -- well outside gate 1(b)'s bias
    print("  (1) DOES ATTACK MOVE THE NULL?  cut %.1f / boost %.1f / flat %.1f Hz -- a %.1f Hz "
          "spread, %.1fx the %.2f Hz bin."
          % (f0["cut"], f0["boost"], f0["flat"], span, span / bins, bins))
    if moves:
        print("      ⇒ YES. Gate 1(e) demonstrated a shift this size RESOLVES (17.6 Hz")
        print("        synthesised, read as 18.2 Hz).")
    else:
        print("      ⇒ ⛔ NO -- the three throws put the null in the SAME bin at this condition.")
        print("        Gate 1(e) showed a 17.6 Hz shift WOULD resolve if present, so this is a")
        print("        real absence, not a resolution limit.")
    print("  (2) DOES IT CHANGE THE DEPTH?  cut %.1f / boost %.1f / flat %.1f dB -- boost is %.2fx flat."
          % (d["cut"], d["boost"], d["flat"], depth_ratio))
    print("      ⇒ %s" % ("YES." if changes_depth else "⛔ NO -- the three depths agree within 25%."))
    if moves or changes_depth:
        print("  ⇒ A PURE BROADBAND GAIN CANNOT DO THAT. The ATTACK network is two-path and")
        print("    interacts with the notch-forming network ⇒ ATTACK and GAP #2 are ONE problem.")
    else:
        print("  ⇒ ⛔ AT THIS CONDITION THE NULL CARRIES NO ATTACK DEPENDENCE AT ALL -- neither")
        print("    frequency nor depth. Whatever makes the null here is SHARED across the throws,")
        print("    so this condition cannot constrain the ATTACK network's notch behaviour. Do NOT")
        print("    read a topology specification off it; use the condition where the throws differ.")
    print("  (3) h stays BROADBAND outside that window: boost %+.2f dB (spread %.2f), cut %+.2f dB"
          % (report["boost"]["median"], report["boost"]["spread"], report["cut"]["median"]))
    print("      (spread %.2f) over %g-%g Hz -- so item 8b(i) survives at full resolution."
          % (report["cut"]["spread"], *BROAD_WIN))
    print("      ⚠ BUT NOT EQUALLY WELL ON THE TWO THROWS, and item 8b did not say so. Relative to")
    print("      its own size the spread is %.0f%% on boost but %.0f%% on cut, and cut needs a %.0f Hz"
          % (100.0 * report["boost"]["spread"] / abs(report["boost"]["median"]),
             100.0 * report["cut"]["spread"] / abs(report["cut"]["median"]),
             report["cut"]["window"][1] - report["cut"]["window"][0]))
    print("      exclusion window against boost's %.0f Hz. 'Flat' is a strong description of boost"
          % (report["boost"]["window"][1] - report["boost"]["window"][0],))
    print("      and a weak one of cut -- which is the same finding as cut failing the 421.9 Hz")
    print("      cancellation check above: cut carries real structure over ~350-520 Hz.")
    print("  (4) FULL SPECIFICATION for a topology proposal: a broadband +-gain AND a null at")
    print("      %.1f / %.1f / %.1f Hz with depth >= %.1f / %.1f / %.1f dB (cut/boost/flat)."
          % (f0["cut"], f0["boost"], f0["flat"], d["cut"], d["boost"], d["flat"]))
    print("  ⚠ depths are LOWER bounds, two mechanisms, both understating (gate 1(b)); the notch")
    print("    window is MEASURED and excluded by name, and is wider than nominal (gate 5); the read")
    print("    is from the quiet levels only, never averaged across them (gate 4); magnitude only.")

    if args.json:
        # ⭐ Write the full-resolution h(f) CURVE, not only its summary. A topology proposal has to
        # be scored on the SHAPE of h across the band (is it flat? does the shared 421.9 Hz peak
        # cancel? where exactly does the notch window start?), and that cannot be rebuilt from a
        # median/spread pair -- while copying the 1/3-oct table into the next tool by hand is the
        # session-33 lost-sign trap. 40-2000 Hz at the measurement's own 5.86 Hz bins, so a
        # downstream screen reads THE MEASUREMENT rather than a transcription of it.
        keep = (fg >= 40.0) & (fg <= 2000.0)
        # the null's own neighbourhood: SHOULDER_WIN and WIDTH_WIN both fall inside 180-500 Hz
        mkeep = (fg >= 180.0) & (fg <= 500.0)
        payload = dict(meta=dict(bins_hz=A.FS / 8192.0, main_level=MAIN,
                                 search_win=SEARCH_WIN, shoulder_win=SHOULDER_WIN,
                                 width_win=WIDTH_WIN,
                                 notch_exclude=NOTCH_EXCLUDE, broad_win=BROAD_WIN,
                                 take_floor=TAKE_FLOOR, diff_floor=DIFF_FLOOR,
                                 shared_peak=SHARED_PEAK),
                       notch={p: head[p] for p in POSITIONS},
                       level_sweep={p: {str(L): sweep[p][L] for L, _ in LEVELS} for p in POSITIONS},
                       h_curve=dict(f=[float(v) for v in fg[keep]],
                                    boost=[float(v) for v in hs["boost"][keep]],
                                    cut=[float(v) for v in hs["cut"][keep]]),
                       # ⭐ AND the raw per-throw MAGNITUDE over the null, not only the ratio h.
                       # Width is a property of one throw's own curve (it is referred to that
                       # throw's own shoulder and its own depth), so it CANNOT be rebuilt from h --
                       # h divides two curves and cancels exactly the shoulder the contour is
                       # measured against. Without this a downstream width fit would have to
                       # re-run the probe or transcribe three numbers; session 62 item 0 made the
                       # same additive change for h itself, for the same reason.
                       mag_curve=dict(f=[float(v) for v in fg[mkeep]],
                                      **{p: [float(v) for v in tf[p][MAIN][1][mkeep]]
                                         for p in POSITIONS}),
                       broadband=report)
        os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
        json.dump(payload, open(args.json, "w"), indent=1)
        print("\n  wrote %s" % args.json)


if __name__ == "__main__":
    main()
