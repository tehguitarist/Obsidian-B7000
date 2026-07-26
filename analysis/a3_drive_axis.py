#!/usr/bin/env python3.11
"""a3_drive_axis -- Phase 9 / A3 step 3a (session 34): the DRIVE-AXIS gate.

WHY THIS IS THE GATE, AND WHY IT COMES BEFORE THE PHASE
-------------------------------------------------------
Session 33 stopped step 2 because the phase target is fitted against the model's
own `mu_d = |OD_d| / |bleed|` ladder, and that ladder is WRONG on the drive axis
exactly where A3 lives (40-101 Hz): the model's |OD| peaks at drive 2:30 and
FALLS by max, while the pedal's must grow straight through the cancellation null
and out the far side. So a candidate element fitted to that phase target would be
fitted to a known defect. Fix the magnitude ladder first; only then is the phase
target worth designing against.

WHAT IS AND IS NOT OBSERVABLE
-----------------------------
The bleed is DRIVE-INDEPENDENT (verified here, not assumed: the decompose probe's
clean-only column is identical to 1e-3 dB across all five drive settings), so

    d(mu)/d(drive) in dB  ==  d(|OD|)/d(drive) in dB

i.e. the SHAPE of the ladder is a property of the OD path alone and the bleed
level beta cancels out of every step. That is what makes this gate usable while
beta is still open (session 33 item 4) -- but only for the model side, which is
measured directly. The PEDAL's ladder is not measured directly: the captures give
the TOTAL |bleed + OD|, so recovering the pedal's m_d needs beta and theta.

At LF theta ~ 180 deg (session 31: theta(40 Hz) >= 168 deg at every plausible
beta), and there

    T_d = beta + 20log10|1 - m_d|   =>   m_d = 1 +/- r_d,   r_d = 10^((T_d-beta)/20)

which is BIMODAL in m_d at every drive (the same two-phasor bimodality that broke
session 31's first solver). The branch is not free, though: |OD| must be
monotonically increasing in drive, which usually admits only one assignment. This
tool enumerates every branch assignment, keeps the monotone ones, and reports the
resulting 2:30->max step as a RANGE over both the surviving branches and a beta
sweep -- rather than quoting one number derived from one branch at one beta.

THE GATE (what a candidate element must do)
-------------------------------------------
  G1  model |OD| MONOTONICALLY INCREASING in drive at 40, 50, 64, 80, 101 Hz.
      Currently it is not: it turns over at 2:30 at every one of those bands.
  G2  model 2:30->max step at 40 Hz inside the pedal's admissible range.
      Currently -2.5 dB against a requirement of roughly +6..+9 dB.
  G3  do NOT let the mids pay for it: the 202-806 Hz steps must not regress.

Gate on THESE, not on band-RMS -- band-RMS is what let a non-monotone ladder sit
undetected through four sessions.

Usage:
    python3.11 analysis/a3_drive_axis.py                    # target + model, shipped
    python3.11 analysis/a3_drive_axis.py --csv-prefix build/cand_   # a candidate
    python3.11 analysis/a3_drive_axis.py --selftest

Model CSVs come from a3_blend_decompose (one per drive), e.g.
    for d in 0.0 0.25 0.5 0.75 1.0; do
      ./build/a3_blend_decompose 1 $d -18 > build/a3_dec_drv$d.csv; done
"""
import argparse
import cmath
import itertools
import json
import math
import os
import sys

REPORT = "analysis/reports/comprehensive_data.json"

# (drive knob, capture). ref-od IS drive noon (captures.py::_REF_OD).
DRIVES = [
    (0.00, "drive-0700_base-od.wav"),
    (0.25, "drive-0930_base-od.wav"),
    (0.50, "ref-od.wav"),
    (0.75, "drive-1430_base-od.wav"),
    (1.00, "drive-1700_base-od.wav"),
]
DRIVE_NAME = ["min", "9:30", "noon", "2:30", "max"]
CLEAN_REF = "blend-0700_base-od.wav"

PROBE_BANDS = [20, 25, 32, 40, 50, 64, 80, 101, 127, 160, 202, 254,
               320, 403, 508, 640, 806]
# The bands the null lives in -- G1/G2 are judged here. 320 is excluded from every
# fit in this file's siblings (TrebleAttack notch band, a known separate gap); it
# is printed but never gated on.
GATE_BANDS = [40, 50, 64, 80, 101]
# G2 is read at 50 and 64 Hz, NOT 40. At 40 Hz the drive setting sitting in the
# null makes m = 1 +/- r with r small, so both roots stay monotone-compatible and
# the step is only bracketed (+5.2..+9.8 dB). At 50/64 the two branches collapse
# onto ONE step value, so the target there is a number rather than a range.
STEP_BANDS = [50, 64]
# theta ~ 180 is only established at LF (session 31: >= 168 deg at 40 Hz), so the
# pedal-side inversion is not run above 101 Hz. These bands are a REGRESSION check
# against the shipped model, not a pedal target.
MID_BANDS = [202, 254, 403, 508, 640, 806]


# ----------------------------------------------------------------------------
# model side -- measured directly, no inference
# ----------------------------------------------------------------------------
def load_model(prefix="build/a3_dec_drv"):
    """{band: dict(od_db=[...], bleed_db=[...], mu_db=[...])} relative to the ref pass."""
    per_drive = []
    for d, _ in DRIVES:
        path = "%s%s.csv" % (prefix, d)
        if not os.path.exists(path):
            sys.exit("missing %s -- regenerate with a3_blend_decompose (see docstring)" % path)
        rows = {}
        for line in open(path):
            if line.startswith("#") or not line.strip():
                continue
            v = [float(t) for t in line.strip().split(",")]
            f = int(v[0])
            ref, od, cl = complex(v[1], v[2]), complex(v[5], v[6]), complex(v[7], v[8])
            rows[f] = (20.0 * math.log10(abs(od) / abs(ref)),
                       20.0 * math.log10(abs(cl) / abs(ref)))
        per_drive.append(rows)

    bands = sorted(set(per_drive[0]).intersection(*[set(r) for r in per_drive[1:]]))
    out = {}
    for b in bands:
        od = [r[b][0] for r in per_drive]
        bl = [r[b][1] for r in per_drive]
        out[b] = dict(od_db=od, bleed_db=bl, mu_db=[o - x for o, x in zip(od, bl)])
    return out


def check_bleed_drive_independent(model, tol_db=1e-3):
    """The whole gate rests on this. Verify it; do not assume it."""
    worst, at = 0.0, None
    for b, r in model.items():
        spread = max(r["bleed_db"]) - min(r["bleed_db"])
        if spread > worst:
            worst, at = spread, b
    return worst, at, worst <= tol_db


# ----------------------------------------------------------------------------
# pedal side -- inferred, so every ambiguity is enumerated rather than chosen
# ----------------------------------------------------------------------------
def load_pedal(sweep):
    """{band: [T_d dB relative to the pedal's own full-clean capture]}."""
    d = json.load(open(REPORT))
    bands = d["meta"]["bands"]
    caps = {c["file"]: c for c in d["captures"]}
    for f in [CLEAN_REF] + [c for _, c in DRIVES]:
        if f not in caps:
            sys.exit("report is missing %s" % f)

    def ped(fname):
        fr = caps[fname]["fr"]
        if sweep not in fr:
            sys.exit("%s has no %s" % (fname, sweep))
        return fr[sweep]["pedal_db"]          # RAW pedal transfer, no gain-match

    ref = ped(CLEAN_REF)
    cols = [ped(c) for _, c in DRIVES]
    out = {}
    for b in PROBE_BANDS:
        i = min(range(len(bands)), key=lambda k: abs(bands[k] - b))
        out[b] = [c[i] - ref[i] for c in cols]
    return out


def pedal_m_branches(t_db, beta_db, theta_deg=180.0):
    """Every m_d ladder consistent with the totals, kept only if monotone rising.

    At theta = 180 exactly, |1 + m e^{i.theta}| = |1 - m|, so each drive admits
    m = 1 +/- r independently -- 2^5 assignments. Monotonicity is the physical
    constraint that prunes them (a gain stage's output cannot fall as its gain
    control rises). Returns [] when nothing survives, which is itself a result:
    it means this beta cannot describe the pedal at this band.
    """
    if abs(theta_deg - 180.0) > 1e-9:
        # general case: |1 + m e^{i.th}|^2 = 1 + 2m cos(th) + m^2 = r^2
        c = math.cos(math.radians(theta_deg))
        out = []
        for t in t_db:
            r2 = 10.0 ** ((t - beta_db) / 10.0)
            disc = c * c - (1.0 - r2)
            if disc < 0:
                return []
            out.append([-c - math.sqrt(disc), -c + math.sqrt(disc)])
        roots = [[m for m in pair if m > 0] for pair in out]
    else:
        roots = []
        for t in t_db:
            r = 10.0 ** ((t - beta_db) / 20.0)
            roots.append([m for m in (1.0 - r, 1.0 + r) if m > 0])

    keep = []
    for combo in itertools.product(*roots):
        if all(b > a for a, b in zip(combo, combo[1:])):
            keep.append([20.0 * math.log10(m) for m in combo])
    return keep


def target_step(pedal, band, betas, theta_deg=180.0):
    """Admissible 2:30->max step in |OD| (dB) at `band`, over beta and branch."""
    steps, ladders = [], []
    for beta in betas:
        for lad in pedal_m_branches(pedal[band], beta, theta_deg):
            steps.append(lad[4] - lad[3])
            ladders.append((beta, lad))
    return steps, ladders


# ----------------------------------------------------------------------------
def selftest():
    """Synthesise totals FROM a known ladder and confirm the truth SURVIVES the
    pruning -- and that the pruning does not claim more uniqueness than it has.

    ⚠ The first version of this asserted the surviving ladder was UNIQUE and
    equal to the truth. It failed, and the failure is a real property of the
    problem, not a bug: at the drive setting sitting in the null, m = 1 +/- r
    with r small, so BOTH roots are monotone-compatible with their neighbours.
    The totals therefore do not determine the 2:30->max step -- they bound it.
    That is why `target_step` returns a RANGE and G2 gates on containment.
    Session 33's single "+6.2 dB" is one of the two branches, not the answer.
    """
    ok = True
    beta = -16.93
    truth = [0.15, 0.30, 0.62, 1.30, 2.70]        # monotone, crosses 1 -> a real null
    t = [beta + 20.0 * math.log10(abs(1.0 - m)) for m in truth]
    lads = pedal_m_branches(t, beta)
    truth_db = [20.0 * math.log10(m) for m in truth]
    hit = any(max(abs(a - b) for a, b in zip(l, truth_db)) < 1e-9 for l in lads)
    print("selftest branch-prune: truth survives=%s among %d monotone ladder(s) -- %s"
          % (hit, len(lads), "PASS" if hit and lads else "FAIL"))
    ok &= hit

    # The surviving steps must BRACKET the true step, or G2 would reject a
    # correct candidate.
    steps = [l[4] - l[3] for l in lads]
    true_step = truth_db[4] - truth_db[3]
    br = min(steps) - 1e-9 <= true_step <= max(steps) + 1e-9
    print("selftest step bracket: true %+.2f dB in [%+.2f, %+.2f] -- %s"
          % (true_step, min(steps), max(steps), "PASS" if br else "FAIL"))
    ok &= br

    # A ladder that never crosses 1 (no null) must stay ambiguous, not be forced.
    truth2 = [0.10, 0.15, 0.22, 0.33, 0.50]
    t2 = [beta + 20.0 * math.log10(abs(1.0 - m)) for m in truth2]
    n2 = len(pedal_m_branches(t2, beta))
    print("selftest no-null ambiguity: %d ladder(s) survive (expect >1) -- %s"
          % (n2, "PASS" if n2 > 1 else "FAIL"))
    ok &= n2 > 1

    # A total DEEPER than any |1-m| can reach at this beta must return nothing
    # rather than silently clamping.
    n3 = len(pedal_m_branches([beta - 400.0] * 5, beta))
    print("selftest unreachable total: %d ladder(s) (expect 0) -- %s"
          % (n3, "PASS" if n3 == 0 else "FAIL"))
    ok &= n3 == 0
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", default="sweep_drv_-18")
    ap.add_argument("--csv-prefix", default="build/a3_dec_drv")
    ap.add_argument("--betas", default="-15.5,-16.93,-18.5",
                    help="bleed levels to enumerate (session 33 item 4: still open)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(0 if selftest() else 1)

    betas = [float(x) for x in args.betas.split(",")]
    model = load_model(args.csv_prefix)
    pedal = load_pedal(args.sweep)

    spread, at, ok = check_bleed_drive_independent(model)
    print("# a3_drive_axis  sweep=%s  csv=%s*" % (args.sweep, args.csv_prefix))
    print("# bleed drive-independence: worst spread %.2e dB (band %s) -- %s"
          % (spread, at, "OK" if ok else "FAIL: the gate below is invalid"))
    if not ok:
        sys.exit(1)

    print("\nMODEL |OD| re full-clean ref, dB (bleed cancels from every STEP)")
    print("%6s %s   %7s  %s" % ("f", "".join("%8s" % n for n in DRIVE_NAME),
                                "2:30>max", "monotone"))
    fails = []
    for b in sorted(model):
        od = model[b]["od_db"]
        mono = all(y > x for x, y in zip(od, od[1:]))
        if b in GATE_BANDS and not mono:
            fails.append(b)
        print("%6d %s   %+7.2f  %s"
              % (b, "".join("%8.2f" % v for v in od), od[4] - od[3],
                 "yes" if mono else "NO"))

    # --- beta admissibility: a NEW constraint, and it is decisive -------------
    # At LF the OD SUBTRACTS (theta ~ 180), so the total must sit BELOW the bleed
    # at every drive where the OD is small. A beta below the pedal's own drive-MIN
    # total therefore forces m(min) > 2 -- an OD already 6 dB ABOVE the bleed at
    # the bottom of the knob, which then has to FALL to reach the null. No monotone
    # ladder exists. This is what prunes beta from the magnitude side alone.
    print("\nBETA ADMISSIBILITY (does ANY monotone ladder exist?)")
    print("%6s %s" % ("f", "".join("%12s" % ("b=%.2f" % b) for b in betas)))
    for b in GATE_BANDS:
        row = []
        for beta in betas:
            n = sum(len(pedal_m_branches(pedal[b], beta, th)) for th in (170.0, 175.0, 180.0))
            row.append("ok" if n else "REFUTED")
        print("%6d %s" % (b, "".join("%12s" % x for x in row)))
    print("  (checked at theta = 170/175/180 deg; 'REFUTED' = none admissible at any)")

    print("\nPEDAL requirement (theta=180; branch-pruned by monotone |OD|)")
    print("%6s %10s  %-22s %s" % ("f", "beta", "2:30->max step, dB", "ladders"))
    targets = {}
    for b in GATE_BANDS:
        allsteps = []
        for beta in betas:
            steps, _ = target_step(pedal, b, [beta])
            allsteps += steps
            rng = ("none" if not steps else
                   "%+.2f" % steps[0] if len(set(round(s, 6) for s in steps)) == 1 else
                   "%+.2f .. %+.2f" % (min(steps), max(steps)))
            print("%6d %10.2f  %-22s %d" % (b, beta, rng, len(steps)))
        targets[b] = allsteps

    print("\nGATE")
    print("  G1 monotone |OD| in drive at %s: %s"
          % (GATE_BANDS, "PASS" if not fails else "FAIL at %s" % fails))
    g2 = True
    for b in STEP_BANDS:
        t, m = targets.get(b, []), model[b]["od_db"][4] - model[b]["od_db"][3]
        if not t:
            print("  G2 %3d Hz: no admissible pedal ladder -- widen --betas" % b)
            g2 = False
            continue
        lo, hi = min(t), max(t)
        ok = lo - 0.5 <= m <= hi + 0.5
        g2 &= ok
        print("  G2 %3d Hz 2:30->max: model %+.2f vs pedal %+.2f..%+.2f dB -- %s"
              % (b, m, lo, hi, "PASS" if ok else "FAIL (short %.2f dB)" % (lo - m)))
    print("  G2 overall: %s   (40 Hz, bracketed only: model %+.2f vs %+.2f..%+.2f)"
          % ("PASS" if g2 else "FAIL",
             model[40]["od_db"][4] - model[40]["od_db"][3],
             min(targets[40]) if targets[40] else float("nan"),
             max(targets[40]) if targets[40] else float("nan")))
    mids = [(b, model[b]["od_db"][4] - model[b]["od_db"][3]) for b in MID_BANDS if b in model]
    print("  G3 mid 2:30->max steps (regression check vs shipped, no pedal target): %s"
          % "  ".join("%d:%+.2f" % (b, s) for b, s in mids))


if __name__ == "__main__":
    main()
