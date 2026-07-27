#!/usr/bin/env python3.11
"""a3_carrier_scan -- A3's carrier REACHABILITY scan, generalised to the whole OD path.

WHY THIS EXISTS
---------------
Session 49 killed the `btC17` candidate with a Pareto scan: over 20 736 settings of
the four bridged-T elements, the ones holding the notch f0 could not lift 250-640 Hz
by >4 dB for less than 3.66 dB of side effect at 1-13 kHz. That argument is about the
NETWORK, not a value, and it cost one session where the value-hunt had cost three.

But it only ever covered the bridged-T. This tool asks the same question of EVERY
element the A3 probe can reach, BEFORE any value is proposed:

    can this element lift 101-508 Hz by ~+5 dB with <= ~1 dB change above 1 kHz?

⭐ WHY IT MEASURES THE REAL CHAIN AND NOT AN ORACLE. Session 49 could use the
`bridged_t_tf` oracle because the bridged-T sits AFTER the clipper, so its transfer
is a pure linear multiplier on the OD path and an oracle delta maps 1:1 onto the OD
delta. That is NOT true of any PRE-clipper element: a +5 dB lift ahead of a
compressive nonlinearity does not arrive as +5 dB at the output, and how much of it
survives is exactly what decides reachability. So every number here comes from
`a3_blend_decompose` -- the same instrument the shape gate uses.

WHAT IT MEASURES. `a3_phase_solve.load_model` returns mu = |OD| / |bleed| per band.
An OD-path element cannot touch the clean bleed (it is a separate tap, and
`processPostBlend(clean, 0)` never runs the OD chain), so

    20 log10 ( mu_candidate / mu_baseline )  ==  the change in |OD|, in dB, exactly.

That is directly comparable to the shape gate's `20 log10 s`, which IS the dB by
which the model's OD must grow at each band. So `resid` below is "how much of A3
would be left if this element moved by this much", with no beta/theta re-fit.

⚠ WHAT IT IS NOT. This is a SCREEN, not an acceptance test. It does not re-fit beta,
it does not solve theta, and it says nothing about phase or about the null. A
survivor goes to `a3_shape_gate` (score + SIDE row), then `a3_lead_fit` (the null),
then the 63-capture matrix, which stays the arbiter. Its job is to stop candidates
that CANNOT work from consuming a session each.

Usage:
    python3.11 analysis/a3_carrier_scan.py --selfcheck      # baseline must reproduce
    python3.11 analysis/a3_carrier_scan.py                  # the full scan
    python3.11 analysis/a3_carrier_scan.py --only trebleC7
"""
import argparse
import math
import os
import subprocess
import sys
import concurrent.futures as cf

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a3_phase_solve as ps                                          # noqa: E402
import a3_shape_gate as sg                                           # noqa: E402

BIN = "build/a3_blend_decompose"
GRUNT_CUT = 1
DBFS = -18.0
OUT = "build/carrier_scan"

# Screening runs three points on the DRIVE axis rather than one, so a candidate
# whose effect is drive-dependent (i.e. it is moving the clipper's operating point
# rather than a linear transfer) is visible as SPREAD instead of being averaged
# away. The full five-drive solve is the shape gate's job, not this one's.
SCAN_DRIVES = [0.00, 0.50, 1.00]

# The C2 target span: the bands where the shape gate says the OD path is 4.4-9.0 dB
# too weak AND `s` is identified. 640/806 are excluded -- their +0.25 dB s-interval
# spans 1.0, so they carry no information (a3_shape_gate INFO). 320 is the
# TrebleAttack notch band, excluded everywhere in A3.
TARGET = [101, 127, 160, 202, 254, 403, 508]
LFBANDS = [20, 25, 32, 40]        # C3, the steep LF half
MIDBANDS = [50, 64, 80]           # the floor region (C1 is measured at its minimum)
SIDEBANDS = sg.SIDE               # 1016..10240, the session-49 monitors

# The requirement, from a3_shape_gate's shipped baseline (= the dB of |OD| lift the
# defect asks for). Imported rather than transcribed -- session 33's own trap.
TARGET_DB = sg.BASELINE_DB

# The side-effect budget the matrix has already been shown to enforce: session 49
# measured that +3.69 dB at 1-13 kHz is refused, and that ~1 dB is the level at
# which the Pareto frontier still allows useful lift.
SIDE_BUDGET_DB = 1.0


# ---------------------------------------------------------------------------
# Candidates. Every key here must exist in a3_blend_decompose.cpp::kFitKeys.
# `post` = the element sits AFTER the clipper, so its effect on |OD| is a pure
# linear multiplier; `pre` = ahead of it, so the clipper compresses whatever it
# does and the delivered lift is smaller than the element's own transfer.
# ---------------------------------------------------------------------------
CANDIDATES = [
    # --- POST-clipper linear (a clean multiplicative scale on the OD path) ---
    ("clipC15", "post", [1.0e-9, 2.2e-9, 5.2e-9, 12e-9, 33e-9, 100e-9]),
    # The session-49 controls: these MUST reproduce its result or this tool is wrong.
    ("btC17", "post", [8.0e-9, 10.0e-9, 15.0e-9, 22.0e-9, 47.0e-9]),
    ("btC16", "post", [330e-12, 680e-12, 1.5e-9, 3.3e-9]),
    ("btR22", "post", [47e3, 100e3, 220e3]),
    ("btR23", "post", [10e3, 33e3, 100e3]),

    # --- PRE-clipper linear ---
    ("trebleC7", "pre", [220e-12, 680e-12, 1.5e-9, 3.3e-9, 10e-9, 100e-9]),
    ("trebleLadderDampR", "pre", [0.0, 10e3, 30e3, 100e3, 1.0e6]),

    # --- The clipper's own input network + gain ---
    ("clipC11", "pre", [1.0e-9, 2.2e-9, 3.69e-9, 10e-9, 47e-9]),
    ("clipR16", "pre", [1.0e3, 3.3e3, 6.8e3, 15e3, 33e3]),
    ("clipA0", "pre", [15.0, 20.0, 24.871, 30.0, 40.0]),

    # --- The clipper VTC (a LEVEL lever: these change how hard it compresses) ---
    ("clipSatLo", "pre", [0.22, 0.4377, 0.9, 1.8]),
    ("clipSatHi", "pre", [0.3, 0.59791, 1.2, 2.4]),
    ("clipK", "pre", [1.5, 2.4653, 4.0]),

    # --- The J201 front end ---
    ("jfetGm", "pre", [0.05e-3, 0.10e-3, 0.20e-3, 0.40e-3]),
    ("jfetExpandBeta", "pre", [0.0, 0.46279, 1.5, 4.0]),
    ("jfetCeilPos", "pre", [1.0, 2.0111, 4.0]),
    ("jfetCeilNeg", "pre", [0.33, 0.65743, 1.3]),

    # --- Op-amp rails (1000 = effectively off) ---
    ("railPos", "pre", [2.0, 2.7, 4.0, 1000.0]),
    ("railNeg", "pre", [2.2, 2.9, 4.2, 1000.0]),
]

SHIPPED = {
    "clipC15": 5.2e-9, "btC17": 22.0e-9, "btC16": 680e-12, "btR22": 100e3,
    "btR23": 33e3, "trebleC7": 680e-12, "trebleLadderDampR": 30e3,
    "clipC11": 3.69e-9, "clipR16": 6.8e3, "clipA0": 24.871,
    "clipSatLo": 0.4377, "clipSatHi": 0.59791, "clipK": 2.4653,
    "jfetGm": 0.10e-3, "jfetExpandBeta": 0.46279, "jfetCeilPos": 2.0111,
    "jfetCeilNeg": 0.65743, "railPos": 2.7, "railNeg": 2.9,
}


REUSE = False


def render(tag, drive, fits):
    """One a3_blend_decompose pass -> a CSV path. ~9 s each; the caller pools them."""
    path = "%s_%s_%s.csv" % (OUT, tag, drive)
    if REUSE and os.path.exists(path) and os.path.getsize(path) > 0:
        return path                      # --reuse: recompute metrics, do not re-render
    cmd = [BIN, str(GRUNT_CUT), str(drive), str(DBFS)] + ["%s=%r" % (k, v) for k, v in fits]
    with open(path, "w") as fh:
        p = subprocess.run(cmd, stdout=fh, stderr=subprocess.PIPE)
    if p.returncode != 0:
        sys.exit("render failed: %s\n%s" % (" ".join(cmd), p.stderr.decode()))
    return path


def mu_of(tag):
    """mu[drive][band] for a rendered tag."""
    return ps.load_model(SCAN_DRIVES, prefix="%s_%s_" % (OUT, tag))


def delta_db(mu_c, mu_b):
    """20log10(mu_cand/mu_base) per band, averaged over the scanned drives, plus
    the max-minus-min spread across those drives (the drive-dependence tell)."""
    out, spread = {}, {}
    for b in ps.PROBE_BANDS:
        d = [20.0 * math.log10(max(mu_c[k][b][0], 1e-30) / max(mu_b[k][b][0], 1e-30))
             for k in SCAN_DRIVES]
        out[b] = float(np.mean(d))
        spread[b] = float(max(d) - min(d))
    return out, spread


def summarise(d, spread):
    lift = float(np.mean([d[b] for b in TARGET]))
    side = float(max(abs(d[b]) for b in SIDEBANDS))
    lf = float(np.mean([d[b] for b in LFBANDS]))
    mid = float(np.mean([d[b] for b in MIDBANDS]))
    # What would be LEFT of A3 at the CORE bands if this element moved this far.
    left = np.array([TARGET_DB[b] - d[b] for b in sg.CORE])
    resid = float(math.sqrt(np.mean(left ** 2)))
    # ⭐ `shape` is the number to rank on, and `resid` is the trap.
    # The shape gate re-fits the pedal's bleed level beta for EVERY candidate, and
    # beta enters as an additive dB offset -- so any FLAT part of `left` is absorbed
    # by beta re-solving and never appears in the score. Ranking on `resid` therefore
    # credits a candidate for a broadband lift that the gate will simply hand back.
    # Measured, session 50: `resid` put clipC11=10n at 3.26 and jfetGm=0.4m at 2.88
    # against the shipped 5.81, but the real gate scored them 5.922 (WORSE) and 5.661
    # (nil) -- both had moved beta by 0.7 dB. Mean-removing makes the screen invariant
    # to exactly what beta can undo, so it measures the SHAPE match alone.
    shape = float(math.sqrt(np.mean((left - left.mean()) ** 2)))
    drv = float(max(spread[b] for b in TARGET))
    return dict(lift=lift, side=side, lf=lf, mid=mid, resid=resid, shape=shape,
                drive_spread=drv)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="restrict to one fit key")
    ap.add_argument("--selfcheck", action="store_true",
                    help="render the shipped defaults twice and assert 0.000 dB")
    ap.add_argument("--jobs", type=int, default=9)
    ap.add_argument("--reuse", action="store_true",
                    help="recompute metrics from cached build/carrier_scan_*.csv "
                         "instead of re-rendering (only valid if the binary and the "
                         "candidate table have not changed since they were written)")
    args = ap.parse_args()
    global REUSE
    REUSE = args.reuse

    os.makedirs("build", exist_ok=True)
    pool = cf.ThreadPoolExecutor(max_workers=args.jobs)

    # ---- baseline (no overrides) ------------------------------------------
    list(pool.map(lambda d: render("base", d, []), SCAN_DRIVES))
    mu_b = mu_of("base")

    if args.selfcheck:
        # ⚠ The session-37 trap, in both directions: a default render must be
        # bit-identical to an EXPLICIT-shipped-value render (proves the override
        # plumbing reaches the stage) AND an off-value must provably differ
        # (proves the flag is not being silently ignored).
        fits = [(k, v) for k, v in SHIPPED.items()]
        list(pool.map(lambda d: render("explicit", d, fits), SCAN_DRIVES))
        d, _ = delta_db(mu_of("explicit"), mu_b)
        worst = max(abs(v) for v in d.values())
        print("explicit-shipped vs default: worst |delta| = %.6f dB" % worst)
        off = [("btC17", 10.0e-9)]
        list(pool.map(lambda dd: render("off", dd, off), SCAN_DRIVES))
        d2, _ = delta_db(mu_of("off"), mu_b)
        moved = max(abs(v) for v in d2.values())
        print("btC17=10n vs default:        worst |delta| = %.6f dB" % moved)
        ok = worst < 1e-6 and moved > 1.0
        print("SELFCHECK %s" % ("PASS" if ok else "FAIL"))
        return 0 if ok else 1

    print("# A3 carrier reachability scan -- GRUNT cut, %.0f dBFS, drives %s"
          % (DBFS, SCAN_DRIVES))
    print("# TARGET = mean |OD| lift over %s Hz; the defect asks for +%.2f dB there."
          % (TARGET, float(np.mean([TARGET_DB[b] for b in TARGET]))))
    print("# SIDE   = max |change| over %s Hz; budget %.1f dB (session 49).\n"
          % (SIDEBANDS, SIDE_BUDGET_DB))
    print("%-20s %-5s %10s %7s %7s %7s %7s %7s %7s %s"
          % ("element", "loc", "value", "LIFT", "SIDE", "LF", "MID", "shape", "drvspr", ""))
    print("%-20s %-5s %10s %7s %7s %7s %7s %7.2f %7s %s"
          % ("(shipped)", "", "-", "0.00", "0.00", "0.00", "0.00",
             float(np.std([TARGET_DB[b] for b in sg.CORE])), "-", "<- A3 as it stands"))

    rows = []
    for key, loc, values in CANDIDATES:
        if args.only and key != args.only:
            continue
        print()
        for v in values:
            tag = "%s_%g" % (key, v)
            list(pool.map(lambda d: render(tag, d, [(key, v)]), SCAN_DRIVES))
            d, spread = delta_db(mu_of(tag), mu_b)
            s = summarise(d, spread)
            ship = " *" if abs(v - SHIPPED.get(key, float("nan"))) < 1e-12 else "  "
            # A candidate is only interesting if it lifts the target span AND stays
            # inside the side budget. Efficiency = dB of lift per dB of side effect.
            flag = ""
            if s["lift"] > 1.0 and s["side"] <= SIDE_BUDGET_DB:
                flag = "<== REACHES"
            elif s["lift"] > 1.0:
                flag = "(lift, but SIDE %.1f dB)" % s["side"]
            print("%-20s %-5s %10.4g %+7.2f %7.2f %+7.2f %+7.2f %7.2f %7.2f %s%s"
                  % (key, loc, v, s["lift"], s["side"], s["lf"], s["mid"],
                     s["shape"], s["drive_spread"], ship, flag))
            rows.append((key, loc, v, s))

    # ---- the frontier ------------------------------------------------------
    print("\n=== settings that lift the target span at all (LIFT > +1 dB) ===")
    hits = [r for r in rows if r[3]["lift"] > 1.0]
    if not hits:
        print("NONE. No reachable element lifts 101-508 Hz by even 1 dB.")
    for key, loc, v, s in sorted(hits, key=lambda r: r[3]["shape"]):
        print("  %-20s %-5s %10.4g  lift %+6.2f  side %5.2f  shape %5.2f  (resid %5.2f)"
              % (key, loc, v, s["lift"], s["side"], s["shape"], s["resid"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
