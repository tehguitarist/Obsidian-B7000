#!/usr/bin/env python3.11
"""a3_shape_gate -- A3's WHOLE-BAND shape gate (session 47).

WHAT IT MEASURES, AND WHY IT IS NEW
-----------------------------------
Every A3 gate so far reads ONE feature of the OD/bleed relationship:

    a3_lead_fit          null DEPTH at LF
    a3_drive_axis G1/G2  the DRIVE axis at 40-101 Hz
    a3_level_axis        the LEVEL axis
    crossover_gate       the LF crossover FREQUENCY (GRUNT flat/boost, drive-min)
    GAP #2 sub-gate      the OD/bleed ratio at 250-640 Hz (GRUNT cut, drive noon)

None of them states the OD/bleed ratio as a CURVE over the whole measured band, so
the shape of A3 has never been on one page -- which is how "A3 is below ~200 Hz"
survived to session 46 and how the 250-640 Hz half of it was found by a user
reading an FR chart rather than by a gate.

This tool reads that curve directly. `a3_phase_solve` already solves, per band, the
scale `s` that the MODEL's OD magnitude needs so the pedal's five measured drive
totals are reproduced:

    t_d = beta * |1 + s . mu_d . e^(i.theta)|          d = 1..5

so `s(f)` IS the A3 defect, in dB, band by band -- s = 1 at every band means the
model's OD path has the right level relative to the clean bleed everywhere.

    THE GATE: 20 log10 s(f) = 0 at every CORE band.

⚠ READ THE INTERVAL, NOT THE POINT. `s` is only as identified as the cancellation
is deep. At the shipped state the +0.25 dB joint (s, theta) interval SPANS 1.0 at
640 and 806 Hz, i.e. those bands do not constrain s at all; 320 Hz is the
TrebleAttack-notch band and is excluded outright as everywhere else in A3. The CORE
set below is therefore fixed ONCE, at the shipped baseline, and never re-derived per
candidate -- a score whose own band set moves with the candidate lets the worst
candidate win by shrinking its scoring set (the session-33 self-selecting-score
trap). Bands outside CORE are printed as INFO and do not vote.

⚠ SCOPE. This is a GRUNT-cut, BLEND-max, -18 dBFS measurement (a3_blend_decompose's
own conditions), scored across the five DRIVE captures. It is a level/shape gate, not
a phase gate: theta is solved jointly but is not what is scored here. A candidate
must still clear the null (`a3_lead_fit`), the drive axis, and the full matrix.

Usage:
    python3.11 analysis/a3_shape_gate.py --selfcheck
    python3.11 analysis/a3_shape_gate.py --fit btR23=47e3 --fit btC17=10e-9
    python3.11 analysis/a3_shape_gate.py --scan btR23=33e3,47e3,68e3
"""
import argparse
import math
import os
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a3_phase_solve as ps                                          # noqa: E402

BIN = "build/a3_blend_decompose"
GRUNT_CUT = 1
DBFS = -18.0

# Fixed ONCE from the shipped baseline (see the docstring). 320 = the TrebleAttack
# notch band; 640/806 = the +0.25 dB s-interval spans 1.0, so they carry no
# information about s and must not be scored. Do NOT recompute this per candidate.
CORE = [20, 25, 32, 40, 50, 64, 80, 101, 127, 160, 202, 254, 403, 508]
INFO = [320, 640, 806]

# ⭐ SIDE-EFFECT MONITORS (session 49). These are NOT part of the score and their
# identifiability has deliberately not been argued -- they exist so that a
# candidate which fixes 250-640 Hz by lifting the OD path EVERYWHERE cannot pass
# unseen. Session 47 preferred `btC17=10n + btC16=1.496n` on a CORE score of 3.52
# (vs the shipped 5.81); the full matrix then refused it, because that form adds
# +3.7 dB of OD lift at 3-5 kHz and +1.6 dB at 6.5-13 kHz -- every one of those
# bands sat outside the tool's band list, so the score was blind to the cost by
# construction.  `SIDE_BUDGET_DB` is the flag threshold, not a pass/fail gate:
# the matrix remains the arbiter (session 47 item 8), this only makes the
# side effect VISIBLE next to the score instead of invisible.
#
# ⚠ Do NOT promote these into CORE by weighting them down instead. That is
# exactly session 47 item 3's error (`CORE_HI`/`WEAK_W` de-weighted every band
# above 254 Hz by a frequency cutoff, precisely where the defect was largest).
# Weight by MEASURED identifiability or not at all.
SIDE = [1016, 1613, 2560, 4064, 6451, 10240]
SIDE_BUDGET_DB = 1.5

# ⚠ The flag is on the CHANGE from shipped, not on |20log10 s| itself. The shipped
# model ALREADY reads +11.3/+10.6/+11.1 dB at 1016/2560/10240 Hz, so an
# absolute-magnitude threshold fires on the baseline and discriminates nothing.
# (Those bands are also poorly conditioned -- mu is small behind the two
# Sallen-Key LPFs, the two-phasor fit's rms reaches 5.5 dB at 6451, and 4064 /
# 10240 are not identified at all. So a SIDE delta is an INDICATOR that a
# candidate reaches above 1 kHz, never a measurement of by how much; the
# 63-capture matrix remains the arbiter.)
SIDE_BASELINE_DB = {1016: 11.31, 1613: 4.89, 2560: 10.60,
                    4064: -1.94, 6451: 8.15, 10240: 11.11}

# The bands beta is fitted over = the band set as it stood before session 49.
# Frozen so the SCORE stays comparable to every recorded number; see fit_beta.
BETA_BANDS = CORE + INFO

# The shipped baseline this tool must reproduce with no overrides (--selfcheck).
# 20 log10 s, dB, at the CORE bands, on df14ff3 + the session-45/46 working tree.
BASELINE_DB = {20: 10.39, 25: 6.82, 32: 4.30, 40: 3.15, 50: 2.67, 64: 2.74,
               80: 3.58, 101: 4.45, 127: 5.06, 160: 5.34, 202: 5.20, 254: 4.66,
               403: 7.60, 508: 9.04}
BASELINE_SCORE = 5.80


def render(fits, prefix):
    """Render the five drive CSVs at a candidate, in parallel."""
    procs = []
    for d, _ in ps.DRIVES:
        cmd = [BIN, str(GRUNT_CUT), str(d), str(DBFS)] + [f"{k}={v}" for k, v in fits]
        fh = open(f"{prefix}{d}.csv", "w")
        procs.append((subprocess.Popen(cmd, stdout=fh, stderr=subprocess.PIPE), fh, cmd))
    for p, fh, cmd in procs:
        _, err = p.communicate()
        fh.close()
        if p.returncode != 0:
            sys.exit("render failed: %s\n%s" % (" ".join(cmd), err.decode()))


def s_interval(mu, t, beta_db, slack_db=0.25):
    """Joint (s, theta) region within slack_db of the optimum -> (s_lo, s_hi)."""
    thetas = np.linspace(0.0, math.pi, 721)
    ss = 10.0 ** np.linspace(-1.0, 1.5, 1201)
    z = ss[:, None, None] * mu[None, None, :] * np.exp(1j * thetas[None, :, None])
    pred = beta_db + 20.0 * np.log10(np.maximum(np.abs(1.0 + z), 1e-12))
    rms = np.sqrt(np.mean((pred - t[None, None, :]) ** 2, axis=2))
    ok = np.any(rms <= rms.min() + slack_db, axis=1)
    return ss[ok].min(), ss[ok].max()


def fit_beta(pedal, model, lo=-20.0, hi=-14.0, step=0.1):
    """Fit the pedal's bleed level beta over BETA_BANDS -- the ORIGINAL 17 bands only.

    ⚠ Deliberately NOT ps.PROBE_BANDS. beta is fitted by summing each band's
    residual, so letting the session-49 SIDE monitors into this sum would move
    beta, and beta moves every band's s -- i.e. adding an OBSERVER would silently
    redefine the SCORE and make it incomparable to every number on record
    (BASELINE_SCORE, and session 47's 5.81 -> 3.52 locus). The monitors must
    observe, not participate. Independently: mu is tiny above 1 kHz (two Sallen-Key
    LPFs at 10.7k/3.3k sit in the OD path), so those bands carry almost no
    information about a resistive, frequency-flat bleed anyway.
    """
    best = None
    k = lo
    while k <= hi + 1e-9:
        tot = 0.0
        for b in BETA_BANDS:
            mu = [model[d][b][0] for d, _ in ps.DRIVES]
            (_, j, _), _ = ps.fit_band(pedal[b], mu, k, n_theta=181, n_s=601)
            tot += j
        if best is None or tot < best[1]:
            best = (k, tot)
        k += step
    return best[0]


def evaluate(prefix, sweep, beta_db=None):
    model = ps.load_model([d for d, _ in ps.DRIVES], prefix)
    pedal = ps.load_pedal(sweep)
    beta = fit_beta(pedal, model) if beta_db is None else beta_db
    rows = {}
    for b in ps.PROBE_BANDS:
        mu = np.array([model[d][b][0] for d, _ in ps.DRIVES])
        t = np.array(pedal[b])
        (th, cost, s), _ = ps.fit_band(t, mu, beta)
        lo, hi = s_interval(mu, t, beta)
        rows[b] = dict(s=s, s_db=20.0 * math.log10(s), lo=lo, hi=hi,
                       theta=math.degrees(th), rms=math.sqrt(cost),
                       identified=not (lo <= 1.0 <= hi))
    score = math.sqrt(np.mean([rows[b]["s_db"] ** 2 for b in CORE]))
    return beta, rows, score


def report(tag, beta, rows, score):
    print(f"\n=== {tag} ===")
    print(f"fitted pedal bleed beta = {beta:.2f} dB")
    print(f"{'f':>6} {'s':>7} {'20log10 s':>10} {'[s_lo, s_hi] +0.25dB':>24} "
          f"{'theta':>7} {'rms':>6}  ident")
    for b in ps.PROBE_BANDS:
        r = rows[b]
        mark = ("" if b in CORE else
                "   (SIDE-EFFECT monitor, not scored)" if b in SIDE else
                "   (INFO, not scored)")
        print(f"{b:6d} {r['s']:7.3f} {r['s_db']:+10.2f}   [{r['lo']:6.3f},{r['hi']:7.3f}]   "
              f"{r['theta']:7.1f} {r['rms']:6.3f}   {'Y' if r['identified'] else 'n'}{mark}")
    print(f"\nSCORE (RMS of 20log10 s over the {len(CORE)} CORE bands) = {score:.3f} dB"
          f"   [shipped baseline {BASELINE_SCORE:.3f}]")
    worst = max(CORE, key=lambda b: abs(rows[b]["s_db"]))
    print(f"worst CORE band {worst} Hz at {rows[worst]['s_db']:+.2f} dB")

    # The side-effect read. A candidate that improves CORE by lifting the OD path
    # broadband shows up here and nowhere else in this tool -- see the SIDE comment.
    have = [b for b in SIDE if b in rows]
    if have:
        dev = {b: rows[b]["s_db"] - SIDE_BASELINE_DB[b] for b in have}
        worst_s = max(have, key=lambda b: abs(dev[b]))
        span = max(abs(dev[b]) for b in have)
        print(f"SIDE-EFFECT bands 1-10 kHz: worst CHANGE vs shipped = {dev[worst_s]:+.2f} dB "
              f"at {worst_s} Hz   [flag above {SIDE_BUDGET_DB:.1f}]")
        print("  " + "  ".join(f"{b}:{dev[b]:+.2f}" for b in have)
              + "   (CHANGE from shipped, not |s|; see SIDE_BASELINE_DB)")
        if span > SIDE_BUDGET_DB:
            print(f"  ⚠ FLAG: this candidate moves the OD path by >{SIDE_BUDGET_DB:.1f} dB above "
                  "1 kHz.\n    That is a matrix question, not a shape-gate one -- grade the full "
                  "63-capture\n    matrix before reading the CORE score as an improvement "
                  "(session 47/49).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", default="sweep_drv_-18")
    ap.add_argument("--fit", action="append", default=[], metavar="KEY=VALUE")
    ap.add_argument("--scan", default=None, metavar="KEY=v1,v2,...")
    ap.add_argument("--beta-db", type=float, default=None)
    ap.add_argument("--selfcheck", action="store_true",
                    help="reproduce the shipped baseline before any candidate is trusted")
    args = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="a3shape_")
    prefix = os.path.join(tmp, "dec")

    if args.selfcheck:
        render([], prefix)
        beta, rows, score = evaluate(prefix, args.sweep, args.beta_db)
        report("SELFCHECK -- no overrides", beta, rows, score)
        worst = max(abs(rows[b]["s_db"] - BASELINE_DB[b]) for b in CORE)
        print(f"\nworst deviation from the recorded baseline = {worst:.3f} dB")
        print("PASS" if worst < 0.05 and abs(score - BASELINE_SCORE) < 0.05
              else "FAIL -- this tool does not reproduce the baseline; do not read a locus")
        return

    if args.scan:
        key, vals = args.scan.split("=", 1)
        base = [tuple(f.split("=", 1)) for f in args.fit]
        print(f"scan {key}: {vals}   (plus fixed {base})")
        print(f"{'value':>12} {'score':>8} {'beta':>7}  " +
              " ".join(f"{b:>6}" for b in CORE))
        for v in vals.split(","):
            render(base + [(key, v)], prefix)
            beta, rows, score = evaluate(prefix, args.sweep, args.beta_db)
            print(f"{v:>12} {score:8.3f} {beta:7.2f}  " +
                  " ".join(f"{rows[b]['s_db']:+6.2f}" for b in CORE))
        return

    fits = [tuple(f.split("=", 1)) for f in args.fit]
    render(fits, prefix)
    beta, rows, score = evaluate(prefix, args.sweep, args.beta_db)
    report(" ".join(f"{k}={v}" for k, v in fits) or "shipped defaults", beta, rows, score)


if __name__ == "__main__":
    main()
