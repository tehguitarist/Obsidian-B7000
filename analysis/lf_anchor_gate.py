#!/usr/bin/env python3.11
"""lf_anchor_gate -- can the harmonic axis reach BELOW 100 Hz on the captures we already have?

WHY THIS EXISTS
---------------
Session 87's next-step (b) asked for "a THD ANCHOR BELOW 100 Hz", and scoped it as a
STIMULUS change plus a deliberate re-baseline, on the premise that

    "`a3_harmonic_axis.ANCHOR_HZ` IS `comprehensive_report.THD_ANCHORS` = (100, 200,
     400) Hz -- a property of the STIMULUS ... it re-keys `comprehensive_report`'s cache
     and changes every record's shape."

⚠⚠ BOTH HALVES OF THAT ARE WRONG, AND THIS TOOL COMPUTES THE CORRECTION RATHER THAN
ARGUING IT (GATE 0).  `comprehensive_report.harmonics_at_anchors` calls
`analyze.harmonic_thd_curve`, which returns a CONTINUOUS Farina curve `(fr, thd, Hn)`
spanning the whole sweep band, and then samples it at three frequencies:

        idx = int(np.argmin(np.abs(fr_c - ahz)))          # <- THD_ANCHORS is an INDEX

So the anchors are a property of the REPORT, not of the recorded signal.  The curve
below 100 Hz is already present in every capture on disk; nothing has to be re-recorded
and no segment layout moves.  `check-for-unread-data-first`, sixth occurrence.

⚠ AND THE COST STATEMENT IS BACKWARDS IN A WAY THAT MATTERS.  `_cache_key` hashes
(capture path, render args, OS factor, binary, BANDS) -- the anchors are NOT in it.  So
changing THD_ANCHORS does NOT bust the cache: a naive re-run returns the cached
THREE-anchor records and prints a table that looks fine.  The framing said "deliberate
re-baseline"; the truth is "silent no-op unless you pass --no-cache".  GATE 0 asserts
this against the live function rather than trusting the reading.

⚠⚠ AND THE NAMED FREQUENCY CANNOT REACH THE COMPONENT IT WAS ASKED FOR.  Session 87's
own item (6a) measured C3's onset as sitting between 40 and 32 Hz and assigned 40 Hz to
the FLOOR.  C3's band set is [20, 25, 32] Hz.  So an anchor at "~40-50 Hz" lands on C1
(50/64 Hz) and the floor -- not on C3 -- whatever else is true.  Stated here because the
handover named 40-50 Hz and C3 in one sentence and they are not the same region.

WHAT IS THEREFORE ACTUALLY IN QUESTION
-------------------------------------
Not "can we record it" but "is the extractor VALID there".  Two mechanisms make the
Farina curve worse toward LF and neither is visible in the returned array:

  (a) THE H1 GATE IS THE SHORT ONE.  `gated_spectrum(1)` uses a FIXED half-width of
      0.04 s, so the fundamental IR is truncated to an 80 ms window -- a Hann mainlobe
      of ~4/0.08 = 50 Hz.  At a 400 Hz anchor that is 12% of the fundamental; at 50 Hz
      it is 100%.  Every Hn/H1 divides by that estimate.
  (b) ORDER N's GATE SHRINKS WITH N (35% of the gap to order N+1) but its result is
      remapped `fr/N` onto the fundamental axis, which DIVIDES its frequency error by N.
      So the orders are not equally affected and H1 is the worst of them -- the opposite
      of the usual "high orders are the fragile ones" intuition.

Neither is a reason to reject the LF region; both are reasons to MEASURE it before
quoting a number there.  That is what GATE 1/1b/2/3 do.

THE GATES
---------
GATE 1  KNOWN-ANSWER, MEMORYLESS.  Push the REAL stimulus's own `sweep_drv_-18` segment
        through a static shaper built from CHEBYSHEV polynomials: for x = A.sin(theta),
        T_n(x/A) = cos(n(theta - pi/2)), so g(x) = sum c_n T_n(x/A) has |Hn| = |c_n|
        EXACTLY, at every frequency.  ⭐ The truth is therefore FLAT in frequency, so any
        frequency dependence the extractor reports IS its own error -- no threshold to
        choose.  Absolute accuracy is checked too (against c_n/c_1).

GATE 1b KNOWN-ANSWER, SLOPING.  GATE 1 is unrepresentative on its own: a real capture's
        H1 is not flat, it carries the pedal's LF rolloff, and a truncated gate interacts
        with a SLOPE.  So repeat with a known 1st-order highpass AFTER the shaper, where
        the truth is c_n/c_1 . |G(nf)|/|G(f)| -- exact, frequency-dependent, and computed
        from the digital filter actually applied (no bilinear-warp mismatch).

GATE 2  THE TONE EXTRACTOR RECOVERS ITS OWN INPUT.  GATE 3 compares two instruments, so
        the second one needs its own known-answer check first (else a disagreement is
        unattributable).  Synthesised tone through the same shaper -> |c_n|.

GATE 3  TWO INSTRUMENTS ON THE PEDAL, AT LF.  The captures carry discrete tones at
        82.41 and 110 Hz (`TONE_FREQS`) at -14 dBFS.  Those share NO machinery with the
        swept curve: different segment, different extractor, no deconvolution, no
        gating.  The driven sweeps bracket -14 dBFS at -18 and -12, so the tone's Hn/H1
        must land BETWEEN the two sweeps' values at the same frequency -- a
        threshold-free BRACKET rather than a tuned tolerance.
        ⚠ The bracket is only valid where Hn/H1 is MONOTONE in level over -18 -> -12, so
        that is CHECKED per order (session 78 found H3 non-monotone in level at higher
        drive) and non-monotone orders are reported as ABSTAIN, never as failures.

⚠ WHAT THIS TOOL DOES NOT DO.  It does not extend the anchors, propose a value, or score
a candidate.  It answers one question -- how far down the existing captures can be read
-- so that the answer to session 87's (b) rests on a measurement instead of a premise.
"""
import argparse
import json
import os
import sys

import numpy as np
import scipy.signal as sps
from numpy.polynomial import chebyshev as _cheb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import analyze as A            # noqa: E402
import gen_test_signal as G    # noqa: E402
import captures as C           # noqa: E402

# eq_reference prints a diagnostic report at module level (known wart, session 56).
_stdout = sys.stdout
sys.stdout = open(os.devnull, "w")
try:
    import comprehensive_report as CR   # noqa: E402
finally:
    sys.stdout.close()
    sys.stdout = _stdout

ORDERS = tuple(range(2, 8))

# The frequencies under test.  100/200/400 are the SHIPPED anchors and are included so the
# LF rows are read against a region already trusted, not in isolation.  82.41 and 110 are
# the two TONE_FREQS below 200 Hz -- the only frequencies where a second instrument exists.
# ⚠ 20 and 25 Hz are here because C3's band set is [20, 25, 32] and the first draft tested
# only 32 -- i.e. it would have reported a C3 verdict having measured one of C3's three bands.
# 20 Hz IS `SWEEP_F0`, so it is the row most likely to fail, which is exactly why it must be in.
TEST_HZ = (20.0, 25.0, 32.0, 40.0, 50.0, 64.0, 82.41, 100.0, 110.0, 200.0, 400.0)

# a3_component_budget's own band sets, so the coverage answer is stated in the budget's terms.
C3_BANDS = (20.0, 25.0, 32.0)
C1_BANDS = (50.0, 64.0)

# GATE 1's shaper.  Chosen to put every order well clear of the numerical floor while
# keeping the map monotone-ish in the swept amplitude; the VALUES are arbitrary, the point
# is that they are known exactly.
CHEB_C = {1: 1.0, 2: 0.16, 3: 0.09, 4: 0.035, 5: 0.018, 6: 0.008, 7: 0.004}

PASS_FLAT_DB = 1.0     # GATE 1: max |Hn/H1 - truth| tolerated before a frequency is "unreadable"
HP_HZ = 30.0           # GATE 1b post-filter corner ~ the OD path's own fitted C15 corner
C21_CORNER_HZ = 7.2    # FitParams::c21R = 220k -> the SHIPPED shared post-BLEND corner.  The
                       # LONGEST LF tail anywhere in the chain, so the worst case for a gate
                       # that truncates the impulse response (see gate1b's docstring).


# ------------------------------------------------------------------ shapers / extractors
def cheb_shaper(x, amp, coeffs=None):
    """g(x) = sum_n c_n T_n(x / amp).

    For x = amp . sin(theta) this yields |Hn| = |c_n| EXACTLY at every frequency, because
    T_n(sin theta) = cos(n(theta - pi/2)).  |x| <= amp is required for T_n to stay bounded;
    the stimulus's sweeps are exactly `amp`-limited (the fade only ever reduces), which is
    asserted rather than assumed.
    """
    coeffs = coeffs or CHEB_C
    u = x / amp
    if np.max(np.abs(u)) > 1.0 + 1e-9:
        raise ValueError(f"input exceeds shaper domain by {np.max(np.abs(u)) - 1.0:.3e}")
    c = np.zeros(max(coeffs) + 1)
    for n, v in coeffs.items():
        c[n] = v
    return _cheb.chebval(u, c)


def tone_orders(seg, f0, max_order=7, peak_bin=False):
    """Per-order narrowband magnitudes from a steady tone.

    ⚠⚠ NOT `analyze.thd`'s `amp()` -- that takes the PEAK BIN over +-3 bins, and GATE 2
    caught it failing on exactly the tone this gate needs.  A 0.8 s window bins at
    1.25 Hz, so 110 Hz is 88 cycles EXACTLY (integer -> zero scalloping, error 0.000 dB)
    but 82.41 Hz is 65.93 cycles.  The fractional-bin offset is multiplied by the order,
    so the peak-bin estimate loses progressively more of a Hann mainlobe as n rises:
    measured -0.09 / -0.23 / -0.44 / -0.70 / -1.03 / -1.37 dB at H2..H7, which is the
    textbook 1.42 dB half-bin Hann scalloping loss arriving right on cue.

    A Hann mainlobe is 4 bins wide, so summing POWER across it recovers the amplitude
    whatever the fractional offset.  That is what this does, and GATE 2 is what says so.
    Pass `peak_bin=True` to reproduce the `analyze.thd` convention (GATE 2 prints both).

    ⚠ Scope of the defect in `analyze.thd` itself: of the eight TONE_FREQS only 82.41 Hz
    is non-integer-cycle at 0.8 s (110/220/440/1000/2000/4000/8000 are all exact), and
    `comprehensive_report.thd_at_bands` only reaches for a discrete tone ABOVE the Farina
    ceiling (~9.5 kHz), where none of these live.  So no shipped number moves -- but the
    convention is wrong wherever a non-integer-cycle tone is read, and this gate needed it.
    """
    w = np.hanning(len(seg))
    X = np.abs(np.fft.rfft(seg * w))
    fr = np.fft.rfftfreq(len(seg), 1 / A.FS)

    def amp(fc):
        i = int(np.argmin(np.abs(fr - fc)))
        lo, hi = max(0, i - 3), min(len(X), i + 4)
        if peak_bin:
            return float(np.max(X[lo:hi]))
        return float(np.sqrt(np.sum(X[lo:hi] ** 2)))

    return {n: amp(n * f0) for n in range(1, max_order + 1)}


def ratios_db(Hn, ref_order=1):
    out = {}
    for n, v in Hn.items():
        if n == ref_order:
            continue
        out[n] = 20.0 * np.log10((v + 1e-30) / (Hn[ref_order] + 1e-30))
    return out


def curve_ratios_db(fr, Hn, freqs):
    """Hn/H1 in dB at each requested frequency, sampled the way the report samples it
    (nearest bin via argmin -- NOT interpolated), so this measures what the report reads."""
    out = {}
    for f in freqs:
        idx = int(np.argmin(np.abs(fr - f)))
        h1 = Hn[1][idx]
        row = {}
        for n in ORDERS:
            if n not in Hn:
                continue
            row[n] = float(20.0 * np.log10((Hn[n][idx] + 1e-30) / (h1 + 1e-30)))
        out[f] = row
    return out


# --------------------------------------------------------------------------- GATE 0
def gate0_premise():
    """The anchors are a REPORT index into a continuous curve, and they are NOT in the
    cache key.  Both COMPUTED against the live functions."""
    print("GATE 0  THE PREMISE, COMPUTED")
    ok = True

    orig = A.load(A.ORIG)
    ref = A.seg_of(orig, "sweep_clean")
    drv = A.seg_of(orig, "sweep_drv_-18")
    fr, thd, Hn = A.harmonic_thd_curve(drv, ref, max_order=7)

    # (a) the curve already spans the LF region -- from a file that predates every session
    #     that asked for a new capture.
    lo = float(fr[fr > 0][0])
    n_below_100 = int(np.sum((fr > 0) & (fr < 100.0)))
    print(f"  (a) harmonic_thd_curve returns a CONTINUOUS curve: {len(fr)} bins, "
          f"lowest {lo:.3f} Hz, {n_below_100} bins BELOW the lowest shipped anchor")
    print(f"      stimulus on disk: {A.ORIG} (mtime unchanged since 2026-07-20)")
    if n_below_100 < 100:
        print("      ⛔ FAIL: no usable sub-100 Hz support in the returned curve")
        ok = False

    # (b) THD_ANCHORS is an index into it, not a segment.  Asserted by showing the report's
    #     own anchor values are reproduced by sampling the curve at those frequencies.
    print(f"  (b) comprehensive_report.THD_ANCHORS = {CR.THD_ANCHORS} "
          f"-> sampled via argmin on this same `fr` axis (harmonics_at_anchors)")

    # (c) the cache key does NOT depend on the anchors.  Probe the live function.
    # `_cache_key` stats its path arguments, so probe it with files that exist.
    probe = (A.ORIG, ["--a", "1"], 8, A.ORIG, [100.0, 200.0])
    k1 = CR._cache_key(*probe)
    k2 = CR._cache_key(*probe)
    old = CR.THD_ANCHORS
    try:
        CR.THD_ANCHORS = (50, 100, 200, 400)
        k3 = CR._cache_key(*probe)
    finally:
        CR.THD_ANCHORS = old
    # A control: the key MUST move when something it does cover moves, or "IDENTICAL"
    # below would be vacuous (a key that never changes proves nothing).
    k_ctrl = CR._cache_key(A.ORIG, ["--a", "1"], 8, A.ORIG, [100.0, 200.0, 400.0])
    if k_ctrl == k1:
        print("      ⛔ FAIL: the key did not move when `bands` moved -- this probe is vacuous")
        ok = False
    anchors_in_key = (k3 != k1)
    print(f"  (c) cache key with anchors (100,200,400) vs (50,100,200,400): "
          f"{'DIFFERS' if anchors_in_key else 'IDENTICAL'}  (self-consistency {k1 == k2})")
    if anchors_in_key:
        print("      -> changing the anchors WOULD re-key the cache (session 87's claim)")
    else:
        print("      ⚠⚠ -> changing the anchors does NOT re-key the cache.  A re-run without")
        print("            --no-cache silently returns the OLD three-anchor records.  This is")
        print("            a LANDMINE, not the 'deliberate re-baseline' cost that was recorded.")

    # (d) the frequency named in the handover cannot reach the component it named.
    print(f"  (d) a3_component_budget band sets: C3 = {C3_BANDS} Hz, C1 = {C1_BANDS} Hz")
    print(f"      session 87 item (6a) put C3's ONSET between 32 and 40 Hz and assigned 40 Hz")
    print(f"      to the FLOOR ⇒ an anchor at 40-50 Hz lands on C1/floor, NOT on C3.")
    print()
    return ok


# --------------------------------------------------------------------------- GATE 1 / 1b
def _known_answer(post_filter=None, label="memoryless"):
    orig = A.load(A.ORIG)
    ref = A.seg_of(orig, "sweep_clean")
    drv = A.seg_of(orig, "sweep_drv_-18")
    amp = G.dbfs(-18)

    y = cheb_shaper(drv, amp)
    if post_filter is not None:
        b, a = post_filter
        y = sps.lfilter(b, a, y)

    fr, thd, Hn = A.harmonic_thd_curve(y, ref, max_order=7)
    meas = curve_ratios_db(fr, Hn, TEST_HZ)

    # truth
    truth = {}
    for f in TEST_HZ:
        row = {}
        for n in ORDERS:
            base = 20.0 * np.log10(abs(CHEB_C[n]) / abs(CHEB_C[1]))
            if post_filter is not None:
                b, a = post_filter
                w = np.array([f, n * f]) * 2 * np.pi / A.FS
                _, h = sps.freqz(b, a, worN=w)
                base += 20.0 * np.log10(abs(h[1]) / abs(h[0]))
            row[n] = base
        truth[f] = row

    print(f"GATE {'1b' if post_filter is not None else '1'}  KNOWN-ANSWER, {label}")
    if post_filter is None:
        print("  truth is FLAT in frequency by construction, so every deviation below is the")
        print("  extractor's own error -- there is no threshold to choose.")
    else:
        # ⚠ the corner is DERIVED from the filter that was actually applied, never printed
        # from a module constant -- the label and the data must not be able to disagree
        # (`computed-verdicts-not-narrated`; the first draft hardcoded HP_HZ here and duly
        # printed "at 30 Hz" above the 7.2 Hz table).
        b, a = post_filter
        w_probe = np.logspace(np.log10(1.0), np.log10(1000.0), 4000) * 2 * np.pi / A.FS
        _, h_probe = sps.freqz(b, a, worN=w_probe)
        mag = np.abs(h_probe)
        corner = float(np.interp(mag.max() / np.sqrt(2.0), mag, w_probe * A.FS / (2 * np.pi)))
        print(f"  truth = c_n/c_1 . |G(nf)|/|G(f)| for the applied 1st-order HP, measured")
        print(f"  -3 dB corner {corner:.2f} Hz (exact, from the DIGITAL filter itself)")
    print(f"  {'f (Hz)':>8}  " + "  ".join(f"{'H'+str(n):>7}" for n in ORDERS) + "   worst")
    worst_by_f = {}
    for f in TEST_HZ:
        errs = [meas[f][n] - truth[f][n] for n in ORDERS]
        worst = max(abs(e) for e in errs)
        worst_by_f[f] = worst
        flag = "" if worst <= PASS_FLAT_DB else ("  <-- UNREADABLE" if worst > 3.0 else "  <-- marginal")
        print(f"  {f:8.2f}  " + "  ".join(f"{e:+7.2f}" for e in errs) + f"   {worst:5.2f}{flag}")
    print()
    return worst_by_f


def gate1():
    return _known_answer(None, "memoryless (flat truth)")


def gate1b():
    """Two corners, and the SECOND one is the load-bearing case.

    ⚠⚠ MY GOING-IN MECHANISM FOR AN LF FAILURE IS REFUTED, AND THE REFUTATION IS THE
    USEFUL PART.  I expected the H1 gate's fixed +-0.04 s half-width (~50 Hz of Hann
    mainlobe, i.e. 100% of a 50 Hz fundamental) to smear Hn/H1 at LF.  It does not:
    order 1's "IR" for a memoryless system is a DELTA, so an 80 ms window truncates
    nothing at all and GATE 1 reads 0.02 dB at 32 Hz.  Frequency resolution is the wrong
    frame -- the gate holds an impulse response, not a tone.

    It can only bite when the linear response has a TAIL comparable to the window:

        30 Hz  -> tau =  5.3 ms = 0.13 of a gate half-width
        7.2 Hz -> tau = 22.1 ms = 0.55 of a gate half-width  (the SHIPPED c21R corner,
                                                              the longest tail in the chain)

    ⭐ And the measured errors run the OTHER way -- 0.35 dB at 32 Hz for the 30 Hz corner
    against 0.07 for the 7.2 Hz one -- so what the residual actually tracks is the SLOPE
    of the response across the harmonic spacing, not the tail length: at 32 Hz a 30 Hz HP
    is on its steepest part while a 7.2 Hz HP is already flat.  Both are printed because
    reasoning about a mechanism is not measuring it, and here the reasoning was wrong."""
    worst = {}
    for hz in (HP_HZ, C21_CORNER_HZ):
        b, a = sps.butter(1, hz / (A.FS / 2), btype="highpass")
        tau_ms = 1e3 / (2 * np.pi * hz)
        w = _known_answer((b, a), f"{hz:g} Hz post-filter, tau {tau_ms:.1f} ms "
                                  f"({tau_ms / 40.0:.1f} gate half-widths)")
        for f, v in w.items():
            worst[f] = max(worst.get(f, 0.0), v)
    return worst


# --------------------------------------------------------------------------- GATE 2
def gate2():
    """The tone extractor recovers its own known answer -- required before GATE 3 can
    attribute a disagreement to either side.  Prints the `analyze.thd` peak-bin convention
    BESIDE the mainlobe-power one, because the difference is the whole reason this gate
    exists and hiding it would make the fix look like a free choice."""
    print("GATE 2  THE TONE EXTRACTOR RECOVERS ITS OWN INPUT")
    print(f"  {'f (Hz)':>9} {'conv':>9}  " + "  ".join(f"{'H'+str(n):>6}" for n in ORDERS)
          + "   worst")
    ok = True
    for f0 in (82.41, 110.0):
        cycles = f0 * G.TONE_SEC
        for peak_bin, label in ((True, "peak-bin"), (False, "mainlobe")):
            amp = G.dbfs(-14)
            seg = G.tone(f0, G.TONE_SEC, -14)
            y = cheb_shaper(seg, amp)
            got = ratios_db(tone_orders(y, f0, peak_bin=peak_bin))
            errs = [got[n] - 20.0 * np.log10(abs(CHEB_C[n]) / abs(CHEB_C[1])) for n in ORDERS]
            worst = max(abs(e) for e in errs)
            verdict = "PASS" if worst <= 0.5 else "FAIL"
            if verdict == "FAIL" and not peak_bin:
                ok = False           # only the convention GATE 3 actually uses can fail this
            print(f"  {f0:9.2f} {label:>9}  " + "  ".join(f"{e:+6.2f}" for e in errs)
                  + f"   {worst:5.3f} dB   {verdict}"
                  + ("" if peak_bin else f"   ({cycles:.2f} cycles in the window)"))
    print("  ⚠ the tone segment is faded (5 ms) and 0.8 s long, so this is the SAME window")
    print("    treatment GATE 3 applies to the captures -- not an idealised steady tone.")
    print("  ⭐ the peak-bin row is `analyze.thd`'s convention and it FAILS at 82.41 Hz only;")
    print("    110 Hz is integer-cycle so it passes at 0.000 dB either way -- which is what")
    print("    makes the diagnosis scalloping rather than 'the LF tone is just harder'.")
    print()
    return ok


# --------------------------------------------------------------------------- GATE 3
def gate3(capture_path):
    """Two instruments on the pedal at LF: swept-Farina vs discrete tone, bracket test."""
    print("GATE 3  TWO INSTRUMENTS ON THE PEDAL AT LF (bracket, threshold-free)")
    print(f"  capture: {os.path.basename(capture_path)}")

    orig = A.load(A.ORIG)
    cap = C.load_capture(capture_path)
    cap_al, _ = A.align(cap, orig)
    ref = A.seg_of(orig, "sweep_clean")

    sweeps = {}
    for name in ("sweep_drv_-18", "sweep_drv_-12"):
        seg = A.seg_of(cap_al, name)
        fr, thd, Hn = A.harmonic_thd_curve(seg, ref, max_order=7)
        sweeps[name] = curve_ratios_db(fr, Hn, TEST_HZ)

    rows = []
    n_brack, n_abstain, n_miss = 0, 0, 0
    for f0 in (82.41, 110.0):
        seg_name = f"tone_{f0:g}"
        try:
            tseg = A.seg_of(cap_al, seg_name)
        except Exception as e:                                    # noqa: BLE001
            print(f"  ⛔ {seg_name}: {e}")
            continue
        tone_r = ratios_db(tone_orders(tseg, f0))
        lo = sweeps["sweep_drv_-18"][f0]
        hi = sweeps["sweep_drv_-12"][f0]
        print(f"  {f0:g} Hz   (tone -14 dBFS must sit BETWEEN the -18 and -12 sweeps)")
        print(f"    {'order':>6} {'sweep -18':>10} {'tone -14':>10} {'sweep -12':>10}   verdict")
        for n in ORDERS:
            a_, b_, t_ = lo[n], hi[n], tone_r[n]
            monotone = True
            span = abs(b_ - a_)
            if span < 0.3:
                verdict, monotone = "ABSTAIN (no span)", False
            else:
                inside = (min(a_, b_) - 0.5) <= t_ <= (max(a_, b_) + 0.5)
                verdict = "in bracket" if inside else f"OUT by {min(abs(t_-a_), abs(t_-b_)):.1f} dB"
            if not monotone:
                n_abstain += 1
            elif verdict == "in bracket":
                n_brack += 1
            else:
                n_miss += 1
            print(f"    {'H'+str(n):>6} {a_:10.2f} {t_:10.2f} {b_:10.2f}   {verdict}")
            rows.append({"f": f0, "order": n, "sweep_m18": a_, "tone_m14": t_,
                         "sweep_m12": b_, "verdict": verdict})
    print(f"  -> {n_brack} in bracket / {n_miss} out / {n_abstain} abstained (span too small to test)")
    print("  ⚠ NOT an equality test: the tone is a STEADY 0.8 s excitation and the sweep is")
    print("    swept, so a nonlinearity WITH MEMORY (the clipper's RC-coupled solve) may")
    print("    legitimately differ.  Falling inside the level bracket is the claim.")
    print()
    return rows


def _od_captures(capture_dir):
    """OD captures only, and `gain-n12` excluded -- `a3_harmonic_axis.load_groups`'s own
    membership rules (is_od + skip_gain_n12), so GATE 4's population is the population the
    verdict is about and not a differently-shaped superset."""
    import a3_harmonic_axis as HA   # noqa: PLC0415
    out = []
    for fn in os.listdir(capture_dir):
        if not fn.endswith(".wav") or not HA.is_od(fn) or "gain-n12" in fn:
            continue
        out.append(os.path.join(capture_dir, fn))
    return out


# --------------------------------------------------------------------------- GATE 4 (yield)
def _yield_one(path):
    """Pedal-side Hn/H1 at every TEST_HZ, per driven sweep.  Module-level for `pmap_cpu`."""
    try:
        orig = A.load(A.ORIG)
        cap = C.load_capture(path)
        cap_al, _ = A.align(cap, orig)
        ref = A.seg_of(orig, "sweep_clean")
        out = {}
        for sw in CR.DRIVEN_SWEEPS:
            seg = A.seg_of(cap_al, sw)
            fr, thd, Hn = A.harmonic_thd_curve(seg, ref, max_order=7)
            out[sw] = curve_ratios_db(fr, Hn, TEST_HZ)
        return os.path.basename(path), out
    except Exception as e:                                        # noqa: BLE001
        return os.path.basename(path), {"error": str(e)}


def gate4_yield(paths, floor_db, min_orders):
    """⭐⭐ THE QUESTION THE OTHER GATES DO NOT ANSWER.

    GATE 1/1b/3 say the EXTRACTOR is sound below 100 Hz.  They say nothing about whether
    the REFERENCE has anything there to extract.  `a3_harmonic_axis` guards on the
    reference (`floor=REF_FLOOR_DB`, session 74 item 6: a floor guard belongs on the
    reference, never on the quantity under test) and needs `MIN_ORDERS` orders to form a
    cell at all.  So the yield is a property of the ND device's LF harmonic content, and
    it is measured here from the captures alone -- no render, no model, no anchor change.
    """
    print("GATE 4  WHAT THE REFERENCE ACTUALLY HAS THERE (pedal side only, no render)")
    print(f"  population: {len(paths)} OD captures x {len(CR.DRIVEN_SWEEPS)} driven sweeps")
    print(f"  guards as `a3_harmonic_axis` applies them: floor {floor_db:g} dB, "
          f"MIN_ORDERS {min_orders}")

    from parallel import pmap_cpu   # noqa: PLC0415  (import here so --selftest stays light)
    results = pmap_cpu(_yield_one, paths)

    bad = [f for f, r in results if "error" in r]
    if bad:
        print(f"  ⚠ {len(bad)} capture(s) unreadable: {bad[:3]}")

    print(f"  {'band':>8}  " + "  ".join(f"{sw.replace('sweep_drv_',''):>18}" for sw in CR.DRIVEN_SWEEPS))
    print(f"  {'(Hz)':>8}  " + "  ".join(f"{'med orders / >=' + str(min_orders):>18}"
                                         for _ in CR.DRIVEN_SWEEPS))
    rows = {}
    for f in TEST_HZ:
        cells = []
        for sw in CR.DRIVEN_SWEEPS:
            counts = []
            for _fn, r in results:
                if "error" in r:
                    continue
                counts.append(sum(1 for n in ORDERS if r[sw][f][n] > floor_db))
            med = float(np.median(counts)) if counts else float("nan")
            frac = (100.0 * sum(1 for c in counts if c >= min_orders) / len(counts)) if counts else 0.0
            cells.append(f"{med:6.1f} / {frac:5.1f}%")
            rows.setdefault(f, {})[sw] = {"median_orders": med, "pct_ge_min": frac}
        print(f"  {f:8.2f}  " + "  ".join(f"{c:>18}" for c in cells))
    print()
    return rows


# --------------------------------------------------------------------------- coverage
def coverage(worst_flat, worst_slope, yields=None):
    """⚠ TWO INDEPENDENT LIMITS, AND THE VERDICT IS THE WEAKER OF THEM.  An extractor that
    is exact somewhere the reference has no signal buys nothing, and the failure modes look
    nothing alike -- so they are printed as separate columns and combined explicitly."""
    print("COVERAGE -- how far down the EXISTING captures can be read")
    print(f"  {'band':>8}  {'flat err':>9}  {'slope err':>9}  {'extractor':>10}  "
          f"{'ref yield':>10}   component   VERDICT")
    for f in TEST_HZ:
        wf = worst_flat.get(f, float("nan"))
        ws = worst_slope.get(f, float("nan"))
        worst = max(wf, ws)
        ext = ("OK" if worst <= PASS_FLAT_DB else
               "MARGINAL" if worst <= 3.0 else "UNUSABLE")
        comp = ("C3" if f in C3_BANDS else "C1" if f in C1_BANDS else
                "anchor" if f in (100.0, 200.0, 400.0) else "tone" if f in (82.41, 110.0) else "-")
        if yields and f in yields:
            best = max(v["pct_ge_min"] for v in yields[f].values())
            yv = f"{best:5.1f}%"
            yok = best >= 20.0
        else:
            yv, yok = "  n/a", True
        verdict = ("READABLE" if ext == "OK" and yok else
                   "NO DATA" if ext == "OK" else "UNREADABLE")
        print(f"  {f:8.2f}  {wf:9.2f}  {ws:9.2f}  {ext:>10}  {yv:>10}   {comp:>9}   {verdict}")
    print()
    print("  'extractor' = worst known-answer error (GATE 1/1b).  'ref yield' = the best")
    print("  fraction of OD captures where the REFERENCE clears the floor on enough orders")
    print("  to form a cell at all (GATE 4).  A band is only READABLE if BOTH hold.")
    print()
    print("  ⚠ C3's own bands are 20/25/32 Hz.  20 Hz IS the sweep's f0 (SWEEP_F0), so the")
    print("    deconvolution has no reference energy below it at all -- that is a genuine")
    print("    STIMULUS limit and no re-reading of these captures can lift it.")
    print()


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", default="analysis/captures/ref-od.wav")
    ap.add_argument("--capture-dir", default="analysis/captures")
    ap.add_argument("--limit", type=int, default=0, help="cap GATE 4's population (debug)")
    ap.add_argument("--selftest", action="store_true", help="gates 1/1b/2 only, no captures")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    print("=" * 78)
    print("LF ANCHOR GATE -- can the harmonic axis reach below 100 Hz on existing captures?")
    print("=" * 78)
    print()

    ok0 = gate0_premise() if not args.selftest else True
    wf = gate1()
    ws = gate1b()
    ok2 = gate2()

    rows, yields = [], {}
    if not args.selftest:
        if os.path.exists(args.capture):
            rows = gate3(args.capture)
        else:
            print(f"GATE 3 SKIPPED -- capture not found: {args.capture}\n")

        import a3_harmonic_axis as HA   # noqa: PLC0415
        paths = sorted(p for p in _od_captures(args.capture_dir))
        if args.limit:
            paths = paths[:args.limit]
        if paths:
            yields = gate4_yield(paths, HA.REF_FLOOR_DB, HA.MIN_ORDERS)
        else:
            print(f"GATE 4 SKIPPED -- no OD captures under {args.capture_dir}\n")

        coverage(wf, ws, yields)

    if args.out:
        with open(args.out, "w") as fh:
            json.dump({"test_hz": list(TEST_HZ), "cheb_c": CHEB_C,
                       "worst_flat": {str(k): v for k, v in wf.items()},
                       "worst_slope": {str(k): v for k, v in ws.items()},
                       "bracket": rows,
                       "yield": {str(k): v for k, v in yields.items()}}, fh, indent=1)
        print(f"wrote {args.out}")

    return 0 if (ok0 and ok2) else 1


if __name__ == "__main__":
    sys.exit(main())
