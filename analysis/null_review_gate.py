#!/usr/bin/env python3.11
"""GATE BD — sub-sample null review over a PRE-REGISTERED select capture set (session 167).

WHAT THIS MEASURES, AND WHAT IT DOES NOT
----------------------------------------
`analyze.null_depth()` optimal-GAIN-MATCHES the render to the capture before subtracting, so the
number below is a TIMBRE / SHAPE / PHASE agreement figure and carries NO information about absolute
level.  Level is graded elsewhere (GATE K/M/O and the LEVEL law); do not read a deep null as "the
levels match".

⚠⚠ THE REFERENCE IS THE NEURAL DSP EMULATION, NOT A HARDWARE B7K ULTRA (`reference-sources.md` §0).
A deep null here means "close to ND".  Per §1 that is the right authority for everything linear and
the WRONG one for even-order harmonic structure, so a driven-sweep null is bounded from below by a
disagreement we deliberately keep (§4: ND's evens sit ~27 dB low).  Quote this as an ND-agreement
figure, never as "distance from the pedal".

SELECTION IS PRE-REGISTERED BY AXIS, NOT BY SCORE
-------------------------------------------------
`self-selecting-scores` (measurement-discipline §2) is the live trap for a "best null" request: a
set chosen after seeing the numbers reports the instrument's own maximum, not the model's.  So the
twelve captures below are fixed by AXIS COVERAGE (clean path, OD reference, both BLEND ends, both
DRIVE ends, bleed-free, both ATTACK throws, both off-flat GRUNT throws) and EVERY row is printed —
best, median and worst.  The headline is the FULL table; the best row is reported as a best-case
bound and labelled as one.

TWO NUMBERS PER CELL
--------------------
  raw            `null_depth()` — what the SHIPPED plugin actually achieves.  This is the honest one.
  lin-removed    `linear_removed_null()` — the floor if every LINEAR (EQ + phase) difference were
                 perfectly matched, from magnitude-squared coherence.  A DIAGNOSTIC, not a shipped
                 figure.  raw >> lin-removed  =>  the residual is mostly linear and is in principle
                 still fittable; raw ~= lin-removed  =>  the residual is nonlinear/capture floor and
                 the shipped plugin is at its limit for that cell.

KNOWN ANSWERS
-------------
  KA1 SELF-NULL       a capture nulled against ITSELF must hit the numerical floor.  Proves the
                      estimator can return a deep number at all.
  KA2 IDENTIFICATION  THRESHOLD-FREE, and it replaced an invented bar.  The first draft asserted
                      "the render nulled against a DIFFERENT capture must be >3 dB shallower", which
                      FAILED at 1.35 dB — and the diagnosis was that the chosen pair was not very
                      different, i.e. a defect in the test (`suspect the mutation before the guard`,
                      s110).  The bar-free replacement asks a RANK question with no number in it:
                      does the render of settings X null capture X better than it nulls any OTHER
                      capture in the set?  That is the only form in which "the null discriminates"
                      is a measurement rather than a threshold, and it doubles as the honest answer
                      to "how good is the null" — see the CROSS-NULL matrix, which shows two
                      genuinely different captures nulling DEEPER than several matched pairs.
"""
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A  # noqa: E402
import captures as C  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(REPO, C.RENDER_BIN)

# Pre-registered: (filename, why this capture is in the set).  Fixed BEFORE any number was read.
SELECT = [
    ("ref-clean.wav",                    "clean path alone (OD out of circuit) — the linear reference"),
    ("ref-od.wav",                       "OD reference baseline: DRIVE noon, LEVEL noon, BLEND max"),
    ("blend-0700_base-od.wav",           "BLEND min — mix axis, clean end"),
    ("drive-0700_base-od.wav",           "DRIVE min — clipper barely engaged"),
    ("drive-1700_base-od.wav",           "DRIVE max — clipper hardest driven"),
    ("level-1700_base-od.wav",           "bleed-free (LEVEL max): the OD path with no clean tap"),
    ("drive-0700_level-1700_base-od.wav", "bleed-free x DRIVE min"),
    ("drive-1700_level-1700_base-od.wav", "bleed-free x DRIVE max"),
    ("attack-boost_base-od.wav",         "ATTACK boost throw"),
    ("attack-cut_base-od.wav",           "ATTACK cut throw"),
    ("level-1700_grunt-boost_base-od.wav", "GRUNT boost, bleed-free"),
    ("level-1700_grunt-flat_base-od.wav",  "GRUNT flat, bleed-free"),
]

SWEEPS = ("sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6")

# ⭐⭐ WHY A BAND-LIMITED NULL IS REPORTED BESIDE THE BROADBAND ONE (session 167 measurement, not a
# convenience).  The log sweep puts ~EQUAL energy in every 1/3-octave band (measured: 3.3 % each),
# so a broadband null is an unweighted average over 30 bands — and on `ref-clean` the per-band
# residual runs -6.70 dB at 22 Hz and -48.63 dB at 905 Hz, a 42 dB spread.  The broadband figure of
# -16.92 dB is therefore set almost entirely by the two band EDGES (44 % of the residual energy is
# in the first 5 % of the sweep, which holds 4.4 % of the signal energy).
#
# ⛔ And the LF edge is a DELIBERATE divergence from this reference, not a defect: session 91
# re-aimed `c21R` 220k -> 130k at the HARDWARE anchor (`reference-sources.md` §2, which records
# HW-ND at -1.4 dB @15 Hz / -1.1 @20 Hz), moving the corner 7.2 -> 12.2 Hz AWAY from ND on purpose.
# §5 rule 2: that is a PASS, not a regression.  Attributed rather than assumed — at 22 Hz the
# measured phase difference is -27.5 deg, and 2*sin(27.5/2) = 0.475 = -6.5 dB, against the -6.70 dB
# residual measured there, i.e. the LF residual is PHASE and is the size a moved HP corner predicts.
# The HF edge is §2's "ND ripple above 6 kHz is an artefact, do not model it" plus the known
# top-octave discretisation droop (`OSFidelity`).
#
# So BOTH are reported.  Broadband is the honest whole-signal figure; the 100 Hz-8 kHz band is the
# release gate's own main graded region and is where a null actually measures the model.
BAND_LO, BAND_HI = 100.0, 8000.0


def band_limit(x, lo=BAND_LO, hi=BAND_HI, fs=48000):
    """Zero everything outside [lo, hi] in the frequency domain. Applied to BOTH sides."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / fs)
    X[(f < lo) | (f > hi)] = 0.0
    return np.fft.irfft(X, len(x))


def render(parsed, os_factor):
    """Render one capture's settings; return the aligned array, or None."""
    args = C.render_args(parsed)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    out = tmp.name
    tmp.close()
    try:
        cmd = [BIN, A.ORIG, out, "--os", str(os_factor)] + args
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            sys.stderr.write(f"  ! render failed: {r.stderr.strip() or r.stdout.strip()}\n")
            return None
        return A.load(out)
    finally:
        if os.path.exists(out):
            os.unlink(out)


XSWEEP = "sweep_drv_-12"   # the sweep the cross-null matrix is built on (mid stimulus rung)


def one_capture(item):
    """Worker: render + null one capture across every sweep.

    Also returns the capture's and the render's XSWEEP segments so the caller can build the
    cross-null matrix without re-rendering (the render is the only expensive step)."""
    fname, why = item
    path = os.path.join(C.CAPTURE_DIR, fname)
    parsed = C.parse_capture(fname)
    orig = A.load(A.ORIG)

    cap = C.load_capture(path)
    if not A.is_full_length(cap, orig):
        return {"file": fname, "why": why, "error": "truncated capture"}
    cap_al, _ = A.align(cap, orig)

    ren = render(parsed, 8)
    if ren is None:
        return {"file": fname, "why": why, "error": "render failed"}
    ren_al, _ = A.align(ren, orig)

    cells = {}
    for sw in SWEEPS:
        cs = A.seg_of(cap_al, sw)
        rs = A.frac_align(A.seg_of(ren_al, sw), cs)
        raw, gain = A.null_depth(cs, rs)
        lin = A.linear_removed_null(rs, cs)
        # band-limited: BOTH sides through the same filter, then re-align (the filter is
        # zero-phase, but frac_align is re-run so the two paths are treated identically)
        cb, rb = band_limit(cs), band_limit(rs)
        band, _ = A.null_depth(cb, A.frac_align(rb, cb))
        cells[sw] = {"raw": float(raw), "band": float(band),
                     "lin": float(lin), "gain_db": float(gain)}

    # KA1 — this capture nulled against itself. Must hit the numerical floor.
    cs = A.seg_of(cap_al, "sweep_clean")
    ka1, _ = A.null_depth(cs, cs.copy())

    return {"file": fname, "why": why, "cells": cells, "ka1": float(ka1),
            "cap_seg": A.seg_of(cap_al, XSWEEP).astype(np.float64),
            "ren_seg": A.seg_of(ren_al, XSWEEP).astype(np.float64)}


def main():
    if not os.path.exists(BIN):
        sys.exit(f"OfflineRender not found at {BIN}")

    print("=== GATE BD — select-set sub-sample null review ===")
    print(f"    binary: {BIN}")
    print(f"    render: --os 8   |   captures: {len(SELECT)} (pre-registered by axis)   |   sweeps: {len(SWEEPS)}")
    print("    ⚠ gain-matched: this is SHAPE/PHASE agreement vs the ND emulation, NOT level, NOT hardware.\n")

    with ProcessPoolExecutor(max_workers=min(8, (os.cpu_count() or 4) - 2)) as ex:
        results = list(ex.map(one_capture, SELECT))

    bad = [r for r in results if "error" in r]
    for r in bad:
        print(f"  ! {r['file']}: {r['error']}")
    results = [r for r in results if "error" not in r]
    if not results:
        sys.exit("GATE BD: no capture produced a reading — refusing to print a table (empty-gate-must-fail).")

    # ---- KA1 ---------------------------------------------------------------------------------
    worst_ka1 = max(r["ka1"] for r in results)
    ka1_ok = worst_ka1 < -100.0
    print(f"  KA1 SELF-NULL       worst {worst_ka1:8.1f} dB   (bar < -100)   "
          f"{'PASS' if ka1_ok else 'FAIL'}")

    # ---- KA2 IDENTIFICATION — threshold-free rank test --------------------------------------
    # For every render i, null it against EVERY capture j in the set. If the null is a
    # discriminating instrument, argmin_j must be i: the render of settings X explains capture X
    # better than it explains any other capture. No bar, no tolerance — a rank, or it isn't.
    n = len(results)
    M = np.zeros((n, n))
    for i, ri in enumerate(results):
        for j, rj in enumerate(results):
            cs = rj["cap_seg"]
            rs = A.frac_align(ri["ren_seg"], cs)
            M[i, j], _ = A.null_depth(cs, rs)

    hits = [i for i in range(n) if int(np.argmin(M[i])) == i]
    ident = len(hits)
    print(f"  KA2 IDENTIFICATION  the render of settings X nulls capture X best of {n} candidates:")
    print(f"                      {ident}/{n} correct   (chance = {1}/{n})   — threshold-free rank test")
    for i, r in enumerate(results):
        j = int(np.argmin(M[i]))
        if j != i:
            print(f"        MISIDENTIFIED  render {r['file'][:36]:<37} -> "
                  f"{results[j]['file'][:36]} ({M[i, j]:6.2f} dB vs own {M[i, i]:6.2f})")
    print()

    if not ka1_ok:
        sys.exit("GATE BD: KA1 FAILED — the table below is not interpretable. Refusing.")

    # capture-vs-capture spread: how far apart are the REFERENCES themselves?
    xs = [(results[a]["file"], results[b]["file"],
           A.null_depth(results[b]["cap_seg"], A.frac_align(results[a]["cap_seg"], results[b]["cap_seg"]))[0])
          for a in range(n) for b in range(n) if a < b]
    deepest_cross = min(xs, key=lambda t: t[2])
    print(f"  CROSS-NULL CONTEXT  the two most SIMILAR distinct captures null at "
          f"{deepest_cross[2]:.2f} dB:\n"
          f"                      {deepest_cross[0]} vs {deepest_cross[1]}")
    print("      Read every matched null below against this. A matched null SHALLOWER than the gap\n"
          "      between two genuinely different pedal settings is not resolving the setting.\n")

    # ---- the table ---------------------------------------------------------------------------
    print(f"  BROADBAND (25 Hz-20 kHz) / BAND-LIMITED ({BAND_LO:.0f} Hz-{BAND_HI/1000:.0f} kHz) null, dB")
    print(f"  {'capture':<38}" + "".join(f"{s.replace('sweep_', ''):>15}" for s in SWEEPS))
    print(f"  {'':<38}" + "".join(f"{'broad / band':>15}" for _ in SWEEPS))
    print("  " + "-" * (38 + 15 * len(SWEEPS)))
    for r in sorted(results, key=lambda x: x["cells"]["sweep_clean"]["band"]):
        row = f"  {r['file'][:37]:<38}"
        for sw in SWEEPS:
            c = r["cells"][sw]
            row += f"{c['raw']:7.1f}/{c['band']:7.1f}"
        print(row)

    # ---- summary -----------------------------------------------------------------------------
    flat = [(r["file"], sw, r["cells"][sw]["raw"], r["cells"][sw]["band"], r["cells"][sw]["lin"])
            for r in results for sw in SWEEPS]
    clean_rows = [x for x in flat if x[1] == "sweep_clean"]
    driven_rows = [x for x in flat if x[1] != "sweep_clean"]

    def stat(rows, label):
        broad = np.array([x[2] for x in rows])
        band = np.array([x[3] for x in rows])
        lins = np.array([x[4] for x in rows])
        bb = min(rows, key=lambda x: x[3])
        bw = max(rows, key=lambda x: x[3])
        print(f"    {label:<16} n {len(rows):3d}   broadband median {np.median(broad):7.2f}   "
              f"BAND median {np.median(band):7.2f}   lin-removed median {np.median(lins):7.2f}")
        print(f"      {'best  (band)':<18} {bb[3]:7.2f} dB   {bb[0]} @ {bb[1]}")
        print(f"      {'worst (band)':<18} {bw[3]:7.2f} dB   {bw[0]} @ {bw[1]}")

    print("\n  SUMMARY")
    stat(clean_rows, "CLEAN sweep")
    stat(driven_rows, "DRIVEN sweeps")
    stat(flat, "ALL cells")

    gap = np.median([x[2] for x in driven_rows]) - np.median([x[4] for x in driven_rows])
    print(f"\n  broadband − lin-removed, driven median: {gap:+.2f} dB")
    print("    > 0 means the residual still has a LINEAR component in principle recoverable;")
    print("    ~0 would mean the driven residual is nonlinear/capture floor and this is the limit.")
    print("  ⚠ NOT A GATE. No bar has ever been agreed for null depth on this project; these are")
    print("    reported figures for the 1.0 review, not a pass/fail. The agreed release criterion")
    print("    is `analysis/release_gate.py`.")


if __name__ == "__main__":
    main()
