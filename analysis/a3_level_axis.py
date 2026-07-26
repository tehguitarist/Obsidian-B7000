#!/usr/bin/env python3.11
"""a3_level_axis -- Phase 9 / A3 step 3c (session 37): a LEVEL-AXIS gate for the
-12/-6 dBFS over-compression defect, derived from the captures rather than
transcribed from a previous session's prose.

THE DEFECT, AS PREVIOUSLY RECORDED
----------------------------------
Session 34 item (7a) found that `trebleC7` fixes the DRIVE axis at -18 dBFS only
(step-residual RMS 4.72 -> 0.65) and not at -12 (5.36 -> 4.58) or -6 (3.65 ->
4.26 = WORSE), and called the remainder "roughly frequency-flat ~1-2 dB
over-compression". Session 35 item (4) then bounded it: holding the -18-fitted
element fixed, the ORACLE floor (per-band magnitude AND phase free, no causality)
RISES 0.42 -> 0.91 -> 1.14 dB across the three levels, so ~1 dB of it is
unreachable by ANY multiplicative linear element on the OD path at any order.
That is what makes it clipper-side: only a nonlinearity can produce a
level-dependent gain error.

Both of those are DERIVED quantities (a step-profile RMS; an oracle residual).
Neither says, in volts, how much gain the OD path is missing at the hotter
levels -- which is what a candidate has to supply. This tool measures that.

WHY THE LEVEL STEP IS THE RIGHT AXIS, AND WHY IT IS beta-FREE
-------------------------------------------------------------
Per band the pedal's total at BLEND=max, relative to its OWN full-clean capture
(`blend-0700`, the same reference a3_phase_solve uses), is

    T(b, d, L) = beta + 20 log10 | 1 + m(b, d, L) . e^(i.theta(b)) |

with beta the resistive clean-bleed divider ratio. `LevelBlend` has no caps at
all and the whole post-BLEND chain is shared with the reference, so beta is
frequency-flat AND level-independent. Therefore in the LEVEL STEP

    dT(b, d) = T(b, d, L2) - T(b, d, L1)

beta cancels EXACTLY -- for the pedal and for the model alike. So does the
stimulus segment's own nominal level offset, because the reference capture is
measured at the same level. No bleed estimate, no beta fit, nothing carried over
from session 35's standoff. The residual dT_model - dT_pedal is then purely a
statement about how each one's OD path compresses with input level.

  GUARD, computed not assumed: the reference capture must itself be LINEAR
  across the three levels, or the subtraction leaks its nonlinearity into dT.
  Checked below (--verbose prints it): the +6 dB nominal step is recovered to
  +6.000 dB with 0.013-0.028 dB of shape spread, i.e. the clean path is linear
  and beta really is level-independent.

WHAT IT REPORTS
---------------
  1. dT for the pedal and the model, per band x drive, for both level steps.
  2. `need` -- the extra OD-path gain in dB the model would have to have at the
     HOTTER level, per band and drive, to reproduce the pedal's dT exactly:
     solve 20log10|1 + m2.10^(x/20).e^(i.th)| - 20log10|1 + m1.e^(i.th)| = dT_ped
     for x. THIS is the size of the defect in the units a fix has to supply.
     Positive x = the model needs MORE gain there = the model OVER-compresses.
  3. The model's own OD compression 20log10(m2/m1), exactly known from the
     decompose passes -- so "the model compresses by X, it should compress by
     X - need" is readable directly.

  BIMODALITY WARNING (session 31 item 8, re-applied): |1 + m e^(i.th)| is NOT
  monotone in m when cos(theta) < 0 -- it dips through the cancellation and rises
  again -- so solving for x by any unimodal search silently picks a branch. This
  grids x densely, finds EVERY sign change, and marks a band `*` when more than
  one branch fits. A starred band's `need` is one of several answers, not the
  answer.

Self-test (--selftest): synthesise the pedal FROM the model at all three levels.
`need` must come back 0.000 dB at every band and drive, or the solve is wrong.

Usage:
    python3.11 analysis/a3_level_axis.py [--selftest] [--verbose]
Needs build/a3_lvl{-18,-12,-6}_drv{0.0,0.25,0.5,0.75,1.0}.csv from:
    for L in -18 -12 -6; do for d in 0.0 0.25 0.5 0.75 1.0; do
      ./build/a3_blend_decompose 1 $d $L > build/a3_lvl${L}_drv$d.csv & done; done; wait
(grunt=CUT / BLEND max / ATTACK Flat = the ref-od operating point.)
"""
import argparse
import cmath
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a3_phase_solve as ps                                        # noqa: E402

LEVELS = [-18, -12, -6]
SWEEP = {-18: "sweep_drv_-18", -12: "sweep_drv_-12", -6: "sweep_drv_-6"}
DRIVE_NAMES = ["min", "9:30", "noon", "2:30", "max"]

# 320 Hz is the TrebleAttack-notch band (GAP #2, a known separate gap) and is
# excluded from every aggregate, exactly as a3_lead_design/a3_lead_fit do.
EXCLUDE = {320}
CORE_HI = 254          # above this mu < 1 and the total is bleed-dominated


def load_model_levels(prefix="build/a3_lvl"):
    """{level: {drive: {band: (m, theta_rad)}}} from a3_blend_decompose."""
    out = {}
    for L in LEVELS:
        out[L] = {}
        for d, _ in ps.DRIVES:
            path = "%s%d_drv%s.csv" % (prefix, L, d)
            if not os.path.exists(path):
                sys.exit("missing %s -- see this file's docstring for the command" % path)
            rows = {}
            for line in open(path):
                if line.startswith("#") or not line.strip():
                    continue
                v = [float(t) for t in line.strip().split(",")]
                od, cl = complex(v[5], v[6]), complex(v[7], v[8])
                rows[int(v[0])] = (abs(od) / abs(cl), cmath.phase(od) - cmath.phase(cl))
            out[L][d] = rows
    return out


def load_pedal_levels():
    """{level: {band: [T_d]}} -- pedal totals rel. its own full-clean capture."""
    rep = json.load(open(ps.REPORT))
    bands = rep["meta"]["bands"]
    caps = {c["file"]: c for c in rep["captures"]}
    for f in [ps.CLEAN_REF] + [c for _, c in ps.DRIVES]:
        if f not in caps:
            sys.exit("report is missing %s" % f)
    idx = [min(range(len(bands)), key=lambda k: abs(bands[k] - b)) for b in ps.PROBE_BANDS]

    out = {}
    for L in LEVELS:
        sw = SWEEP[L]
        ref = caps[ps.CLEAN_REF]["fr"][sw]["pedal_db"]
        cols = [caps[c]["fr"][sw]["pedal_db"] for _, c in ps.DRIVES]
        out[L] = {b: [c[i] - ref[i] for c in cols] for b, i in zip(ps.PROBE_BANDS, idx)}
    return out


def clean_ref_linearity():
    """The GUARD: is the reference capture itself linear across the three levels?

    Returns [(L2, L1, mean_step_dB, shape_rms_dB, shape_max_dB)]. A nonlinear
    reference would leak into every dT below, so this is reported, not assumed.
    """
    rep = json.load(open(ps.REPORT))
    caps = {c["file"]: c for c in rep["captures"]}
    ref = {L: np.array(caps[ps.CLEAN_REF]["fr"][SWEEP[L]]["pedal_db"]) for L in LEVELS}
    out = []
    for a, b in zip(LEVELS[1:], LEVELS[:-1]):
        dd = ref[a] - ref[b]
        out.append((a, b, float(dd.mean()),
                    float((dd - dd.mean()).std()), float(np.abs(dd - dd.mean()).max())))
    return out


def total_db(m, theta):
    """20log10|1 + m e^(i.theta)| -- the beta-free part of T."""
    return 20.0 * math.log10(max(abs(1.0 + m * cmath.exp(1j * theta)), 1e-12))


def solve_need(m1, th1, m2, th2, dT_target, span=24.0, n=4801):
    """Extra OD gain x (dB) at the HOT level so the model's dT matches the pedal's.

    Returns (x_nearest_zero, n_branches). Grids x -- never a unimodal search:
    with cos(theta) < 0 the level dips through the cancellation and rises again,
    so f(x) can cross the target more than once (session 31 item 8).

    ⚠ Each level uses its OWN theta. A first version averaged the two thetas here
    while `dT_mdl` used them separately, so x = 0 did not reproduce the model's
    own dT and the self-test came back with |need| up to 9.4 dB -- near a null a
    fraction of a degree of phase error is worth several dB of level. Keeping the
    two thetas distinct makes x = 0 exactly the model, which is what makes `need`
    a measurement of the DEFECT rather than of the solver.
    """
    xs = np.linspace(-span, span, n)
    base = total_db(m1, th1)
    f = np.array([total_db(m2 * 10.0 ** (x / 20.0), th2) for x in xs]) - base - dT_target
    roots = [float(x) for x in xs[f == 0.0]]           # exact hits (the self-test's x=0)
    sign = np.sign(f)
    cross = np.nonzero(sign[:-1] * sign[1:] < 0)[0]    # strict changes between nonzero pairs
    for i in cross:                                    # linear interpolation on the bracket
        x0, x1, f0, f1 = xs[i], xs[i + 1], f[i], f[i + 1]
        roots.append(float(x0 - f0 * (x1 - x0) / (f1 - f0)))
    if not roots:                                      # target unreachable at any x
        return (float(np.sign(f[-1]) * span), 0)
    return (min(roots, key=abs), len(roots))


def build_tables(model, pedal, bands):
    """Per level step: dT_ped, dT_mdl, need, model's own OD compression."""
    steps = list(zip(LEVELS[1:], LEVELS[:-1]))         # (hot, cold)
    tabs = {}
    for hot, cold in steps:
        rows = {}
        for b in bands:
            row = []
            for k, (d, _) in enumerate(ps.DRIVES):
                m1, th1 = model[cold][d][b]
                m2, th2 = model[hot][d][b]
                dT_ped = pedal[hot][b][k] - pedal[cold][b][k]
                dT_mdl = total_db(m2, th2) - total_db(m1, th1)
                need, nbr = solve_need(m1, th1, m2, th2, dT_ped)
                row.append(dict(dT_ped=dT_ped, dT_mdl=dT_mdl, need=need, nbr=nbr,
                                odcomp=20.0 * math.log10(m2 / m1), m1=m1, m2=m2,
                                dth=math.degrees(th2 - th1), th=math.degrees(th2)))
            rows[b] = row
        tabs[(hot, cold)] = rows
    return tabs


def agg(rows, bands, key, lo=None, hi=None, drives=None):
    v = []
    for b in bands:
        if b in EXCLUDE:
            continue
        if lo is not None and b < lo:
            continue
        if hi is not None and b > hi:
            continue
        for k, cell in enumerate(rows[b]):
            if drives is not None and k not in drives:
                continue
            v.append(cell[key])
    a = np.array(v, dtype=float)
    return float(np.sqrt(np.mean(a * a))), float(np.mean(a))


def gate(model, pedal, bands, label=""):
    """The compact acceptance summary: NULL placement over drive x level, plus the
    well-conditioned dT residual. Returns a dict so a scan can rank candidates.

    ⚠ The headline is the dT RESIDUAL and the NULL, not `need`. `need` is in the
    right units (dB of OD gain) but is a badly-conditioned estimator wherever
    |d(total)/d(m)| is small -- i.e. exactly at the nulls this gap is about. It
    returns "unreachable" there, and its own control (drive min/9:30, where both
    devices are near-linear) reads up to 2.9 dB against the dT residual's 0.5.
    Rank candidates on dT and the null; read `need` per band, for size only.
    """
    core = [b for b in bands if b not in EXCLUDE and b <= CORE_HI]
    tabs = build_tables(model, pedal, bands)

    res = {}
    for (hot, cold), rows in tabs.items():
        for key, lo, hi, dr in [("ctrl", 0, CORE_HI, [0, 1]),
                                ("noon", 0, CORE_HI, [2]),
                                ("lf_hot", 0, 80, [3, 4]),
                                ("mf_hot", 101, CORE_HI, [3, 4]),
                                ("all", 0, 10 ** 9, list(range(5)))]:
            v = [rows[b][k]["dT_mdl"] - rows[b][k]["dT_ped"]
                 for b in bands if b not in EXCLUDE and lo <= b <= hi for k in dr]
            a = np.array(v, dtype=float)
            res[(hot, key)] = float(np.sqrt(np.mean(a * a)))

    nulls = {}
    for L in LEVELS:
        for k, (d, _) in enumerate(ps.DRIVES):
            pt = [pedal[L][b][k] for b in core]
            mt = [total_db(*model[L][d][b]) for b in core]      # beta-free: shape only
            ip, im = int(np.argmin(pt)), int(np.argmin(mt))
            nulls[(L, k)] = (core[ip], core[im])
    match = sum(1 for v in nulls.values() if v[0] == v[1])

    print("\n" + "=" * 78)
    print("LEVEL-AXIS GATE SUMMARY %s" % label)
    print("=" * 78)
    print("\n  NULL BAND (deepest <=%d Hz), pedal -> model, per stimulus level x drive:" % CORE_HI)
    print("  %-10s %s" % ("", "".join("%14s" % n for n in DRIVE_NAMES)))
    for L in LEVELS:
        cells = []
        for k in range(5):
            p, m = nulls[(L, k)]
            cells.append("%6d->%-4d%s" % (p, m, "=" if p == m else " "))
        print("  %+4d dBFS  %s" % (L, "".join("%14s" % c for c in cells)))
    print("\n  null band matches: %d / %d" % (match, len(nulls)))

    print("\n  dT RESIDUAL rms (model - pedal), dB -- the well-conditioned readout:")
    print("  %-28s %10s %10s" % ("subset", "-18>-12", "-12>-6"))
    for key, nm in [("ctrl", "min+9:30 <=254 (CONTROL)"), ("noon", "noon <=254"),
                    ("lf_hot", "2:30+max <=80 Hz"), ("mf_hot", "2:30+max 101-254"),
                    ("all", "all bands, all drives")]:
        print("  %-28s %10.2f %10.2f" % (nm, res[(-12, key)], res[(-6, key)]))
    return dict(nulls=nulls, match=match, res=res)


def selftest():
    print("SELF-TEST: synthesise the pedal FROM the model at all three levels.")
    print("`need` must be 0.000 dB everywhere, and dT_mdl - dT_ped must be 0.\n")
    model = load_model_levels()
    bands = [b for b in ps.PROBE_BANDS]
    fake = {}
    for L in LEVELS:
        fake[L] = {b: [total_db(*model[L][d][b]) for d, _ in ps.DRIVES] for b in bands}
    tabs = build_tables(model, fake, bands)
    worst_need = worst_dt = 0.0
    for _, rows in tabs.items():
        for b in bands:
            for cell in rows[b]:
                worst_need = max(worst_need, abs(cell["need"]))
                worst_dt = max(worst_dt, abs(cell["dT_mdl"] - cell["dT_ped"]))
    print("  worst |need| = %.4f dB   worst |dT_mdl - dT_ped| = %.2e dB"
          % (worst_need, worst_dt))
    ok = worst_need < 0.02 and worst_dt < 1e-9
    print("  %s\n" % ("PASS" if ok else "FAIL -- the level-step solve is not trustworthy"))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--gate-only", action="store_true",
                    help="print just the gate summary (for scanning candidates)")
    ap.add_argument("--label", default="")
    ap.add_argument("--prefix", default="build/a3_lvl")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(0 if selftest() else 1)

    model = load_model_levels(args.prefix)
    pedal = load_pedal_levels()
    bands = list(ps.PROBE_BANDS)

    if args.gate_only:
        gate(model, pedal, bands, args.label)
        return

    print("A3 LEVEL-AXIS GATE -- the -12/-6 dBFS over-compression defect, measured.")
    print("grunt=CUT / BLEND=max / ATTACK=Flat (the ref-od operating point).\n")

    print("GUARD -- is the reference capture linear across levels? (if not, dT is")
    print("contaminated and nothing below means anything)")
    for hot, cold, mean, rms, mx in clean_ref_linearity():
        verdict = "OK" if (abs(mean - 6.0) < 0.1 and rms < 0.1) else "⚠ NOT LINEAR"
        print("  %+d vs %+d dBFS: nominal step %+.3f dB, shape spread rms %.3f / max %.3f  %s"
              % (hot, cold, mean, rms, mx, verdict))
    print()

    tabs = build_tables(model, pedal, bands)

    for (hot, cold), rows in tabs.items():
        print("=" * 78)
        print("LEVEL STEP %+d -> %+d dBFS" % (cold, hot))
        print("=" * 78)
        print("\ndT = T(hot) - T(cold), dB. 0 = the OD/bleed ratio does not change with")
        print("input level, i.e. a linear OD path. beta cancels exactly in this step.\n")
        print("%6s | %s | %s" % ("f", "".join("%7s" % n for n in DRIVE_NAMES),
                                 "".join("%7s" % n for n in DRIVE_NAMES)))
        print("%6s | %-35s | %-35s" % ("", "        PEDAL  dT", "        MODEL  dT"))
        for b in bands:
            mark = "*" if b in EXCLUDE else " "
            print("%5d%s | %s | %s"
                  % (b, mark,
                     "".join("%7.2f" % c["dT_ped"] for c in rows[b]),
                     "".join("%7.2f" % c["dT_mdl"] for c in rows[b])))

        print("\n`need` = extra OD-path gain (dB) the model must have AT THE HOT LEVEL to")
        print("reproduce the pedal's dT. POSITIVE = model over-compresses (needs more).")
        print("`*` = more than one x fits (the |1+m e^ith| branch ambiguity) -- read with care.")
        print("`odcomp` = the model's OWN OD compression over this step, 20log10(m_hot/m_cold).\n")
        print("%6s | %s | %s" % ("f", "".join("%7s" % n for n in DRIVE_NAMES),
                                 "".join("%7s" % n for n in DRIVE_NAMES)))
        print("%6s | %-35s | %-35s" % ("", "        need (dB)", "     model odcomp (dB)"))
        for b in bands:
            mark = "*" if b in EXCLUDE else " "
            print("%5d%s | %s | %s"
                  % (b, mark,
                     "".join("%6.2f%s" % (c["need"], "*" if c["nbr"] > 1 else " ")
                             for c in rows[b]),
                     "".join("%7.2f" % c["odcomp"] for c in rows[b])))

        r_all, m_all = agg(rows, bands, "need")
        r_core, m_core = agg(rows, bands, "need", hi=CORE_HI)
        r_lin, m_lin = agg(rows, bands, "need", hi=CORE_HI, drives=[0, 1])
        r_hot, m_hot = agg(rows, bands, "need", hi=CORE_HI, drives=[3, 4])
        r_noon, m_noon = agg(rows, bands, "need", hi=CORE_HI, drives=[2])
        d_all, _ = agg(rows, bands, "dT_ped")
        print("\n  AGGREGATE `need`  (320 Hz excluded throughout)")
        print("    all bands, all drives            rms %6.2f   mean %+6.2f dB" % (r_all, m_all))
        print("    <=%d Hz, all drives              rms %6.2f   mean %+6.2f dB"
              % (CORE_HI, r_core, m_core))
        print("    <=%d Hz, drive min+9:30 (linear) rms %6.2f   mean %+6.2f dB"
              % (CORE_HI, r_lin, m_lin))
        print("    <=%d Hz, drive noon              rms %6.2f   mean %+6.2f dB"
              % (CORE_HI, r_noon, m_noon))
        print("    <=%d Hz, drive 2:30+max          rms %6.2f   mean %+6.2f dB"
              % (CORE_HI, r_hot, m_hot))
        print("    (for scale: the pedal's own |dT| rms over the same set is %.2f dB)" % d_all)
        print()

    print("=" * 78)
    print("READING THIS")
    print("=" * 78)
    print("""
  * Drive min / 9:30 are the CONTROL. There the OD path is essentially linear in
    both pedal and model, so `need` there measures the method's own noise floor,
    not a defect. A `need` that is large at min/9:30 means something is wrong
    with the measurement, not with the clipper.
  * A defect that is confined to the hot drives and grows with stimulus level is
    a COMPRESSION mismatch and can only be fixed by a nonlinearity -- consistent
    with session 35's oracle floor (0.42 -> 0.91 -> 1.14 dB), which proved no
    linear OD-path element of any order can touch it.
  * `need` is per (band, drive). A fix is only credible if `need` is roughly
    CONSTANT across bands -- a level-dependent but frequency-flat error is a
    clipper gain/ceiling error. If `need` has strong frequency structure the
    element is not a plain VTC parameter.
""")
    gate(model, pedal, bands, args.label)


if __name__ == "__main__":
    main()
