#!/usr/bin/env python3.11
"""A3 / ATTACK: is the [ENG] treble-ladder TOPOLOGY the carrier of the pedal's ATTACK effect?

Session 56 refuted C8 (and a C8 x R7 x R8 frontier) on REACHABILITY, but had to do it by
PREDICTING an output span through a bleed-dilution calculation, at the linear corner only.
This tool asks the same question with the dilution step removed, and adds the discriminator
session 55 sec 5 left open.

THE THREE THINGS IT MEASURES
  1. The pedal's ATTACK effect on the OD path, BLEED-FREE, from the blend axis
     (attack-boost/cut ladders vs the ref ladder), against the ladder's own ratio.
     * The ATTACK switch only reroutes C8's bottom plate, so H(boost)/H(flat) is a PURELY
       LINEAR property of the ladder -- no drive, no clipper, no bleed, no dilution model.
       That makes this a like-for-like comparison in a way session 56's screen could not be.
  2. The LEVEL axis of that ratio -- the (i)-vs-(ii) discriminator.
     * (i) a linear pre-clipper low-mid element the model lacks;  (ii) the pedal's clipper
       operating point being far more HF-sensitive than the model's.
     * A clipper-operating-point mechanism must FADE toward the linear regime. A linear one
       must not. Read the DIRECTION of the level trend, not any single level's number.
  3. REACHABILITY -- can ANY setting of the drawn ladder make the measured shape?
     Differential evolution over all 11 elements, scored on BOTH throws with ONE parameter
     set (they are the same network), swept over box widths to expose saturation.

GUARDS, all of which have already caught something
  * LIVENESS (L-009): C8 = 0 must make both throws EXACTLY flat, and the shipped 220 pF must
    move something. Without this an inert probe reads as a null result.
  * SELF-TEST GATE: the optimiser must recover a synthesised, definitionally-reachable target
    to under the capture floor. A random search FAILED this gate (0.73 dB on a reachable
    target vs 3.04 on the real one -- a 4x separation is not a refutation, it is a weak
    search). Only a gated failure may be read as a refutation.
  * PATHOLOGY GUARD: D and the ratios have the FLAT response in the denominator, so a
    numerically dead flat curve inflates them without resembling the measurement. At +/-9
    decades the unguarded search found flat = -320 dB (C5 = 0.63 F, R11 = 3e14 ohm) and
    reported D = +88 dB at a shape rms of 44 dB. Points whose flat response is implausibly
    small or ripply are rejected.
  * The target is REBUILT LIVE from the captures every run -- never transcribed.

SCOPE, twice
  * The pedal side is a DESCRIBING-function ratio (the OD path is not LTI at the operating
    points in the matrix), so a single condition cannot separate (i) from (ii). The LEVEL
    AXIS is what makes it readable.
  * ATTACK is [ENG] -- the 3-way switch is not on our schematic at all. What a negative
    result here refutes is the ASSUMED topology, which nothing corroborated to begin with.

Usage:  python3.11 analysis/attack_topology_probe.py [--selftest] [--quick]
"""
import argparse
import contextlib
import io
import math
import os
import sys

import numpy as np
from scipy.optimize import differential_evolution

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a3_condition_axis as A            # noqa: E402
import a3_blend_axis as AX               # noqa: E402
with contextlib.redirect_stdout(io.StringIO()):   # eq_reference reports at MODULE level
    import eq_reference as E             # noqa: E402

TAKE_FLOOR_DB = 0.144        # pedal take-to-take repeatability (session 24)
FIT_HI_HZ = 1700.0           # blend axis is untrustworthy above this (session 51 item 5)
NAMES = ["ref (drive noon)", "attack boost", "attack cut"]
LEVELS = ["sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6"]
REPORT_LEVEL = "sweep_drv_-18"

# Shipped ladder. C7 = 680 pF and RdampC5 = 30k are FITTED values, not schematic ones.
SHIP = dict(C8=220e-12, R7=200e3, R8=470e3, R11=470e3, R12=6.8e3, R14=22e3,
            C5=22e-9, C9=22e-9, C6=22e-9, C7=680e-12, RdampC5=30e3)
KEYS = sorted(SHIP)
ZS = dict(gm=0.10e-3, ro=200e3, Rq2=1e6)     # shipped J201 boundary


# ----------------------------------------------------------------- pedal side
def pedal_ratios(sweep):
    """{band: (boost-flat dB, cut-flat dB)} over bands identified in ALL THREE conditions.

    Restricting to a COMMON band set matters: per-condition identifiability differs, and an
    aggregate over different members is not a comparison (the session-49 item-7 trap).
    """
    A.SWEEP = sweep
    bands_all, caps = A.load_report(A.REPORT)
    sol = {}
    for name in NAMES:
        files, b1, _ = A.CONDITIONS[name]
        t = A.ladder(caps, bands_all, files, b1, "pedal_db")
        bd = [f for f in sorted(t) if f <= A.FIT_HI_HZ]
        with contextlib.redirect_stdout(io.StringIO()):
            Bint, _ = AX.fit_taper(t, bd, name[:12], False)
        sol[name] = A.solve(t, bd, name, Bint)
    out = {}
    for f in sorted(sol[NAMES[0]]):
        if f > FIT_HI_HZ or not all(sol[n].get(f, (0, 0, 0, False))[3] for n in NAMES):
            continue
        ref = 20 * math.log10(sol[NAMES[0]][f][0])
        out[f] = (20 * math.log10(sol["attack boost"][f][0]) - ref,
                  20 * math.log10(sol["attack cut"][f][0]) - ref)
    return out


# ----------------------------------------------------------------- model side
def ladder_ratios(bands, p):
    """(boost-flat dB, cut-flat dB) for the LINEAR ladder, plus the flat curve for guarding."""
    zs = E.jfet_source_z(bands, **ZS)
    fl = np.abs(E.treble_attack_tf(bands, 'flat',  Zs=zs, **p))
    bo = np.abs(E.treble_attack_tf(bands, 'boost', Zs=zs, **p))
    cu = np.abs(E.treble_attack_tf(bands, 'cut',   Zs=zs, **p))
    return 20 * np.log10(bo / fl), 20 * np.log10(cu / fl), 20 * np.log10(fl)


def pathological(flat_db):
    """A dead or wildly-ripply FLAT response makes every ratio meaningless (see PATHOLOGY)."""
    return (not np.all(np.isfinite(flat_db))) or flat_db.max() < -80.0 or \
           (flat_db.max() - flat_db.min()) > 60.0


def eval_at(x, bands):
    p = {k: SHIP[k] * 10.0 ** xi for k, xi in zip(KEYS, x)}
    try:
        rb, rc, fl = ladder_ratios(bands, p)
    except Exception:
        return None
    if not (np.all(np.isfinite(rb)) and np.all(np.isfinite(rc))) or pathological(fl):
        return None
    return rb, rc, p


def make_cost(bands, tb, tc):
    def cost(x):
        r = eval_at(x, bands)
        if r is None:
            return 1e6
        rb, rc, _ = r
        return math.sqrt((np.mean((rb - tb) ** 2) + np.mean((rc - tc) ** 2)) / 2)
    return cost


def opt(fn, width, seed, quick):
    box = [(-width, width)] * len(KEYS)
    r = differential_evolution(fn, box, seed=seed, maxiter=120 if quick else 400,
                               popsize=12 if quick else 24, tol=1e-8, polish=True,
                               init='sobol')
    return r.fun, r.x


# ----------------------------------------------------------------- the gate
def selftest(bands, quick):
    """Two gates. Neither is optional: a probe that cannot move, or a search that cannot
    find, both produce a 'refutation' that is really an instrument failure."""
    ok = True
    print("=== LIVENESS (L-009) ===")
    zb, zc, _ = ladder_ratios(bands, dict(SHIP, C8=0.0))
    sb, sc, _ = ladder_ratios(bands, SHIP)
    dead = max(np.abs(zb).max(), np.abs(zc).max())
    live = max(np.abs(sb).max(), np.abs(sc).max())
    print("  C8 = 0 must make BOTH throws identical to flat: worst %.3e dB   %s"
          % (dead, "OK" if dead < 1e-9 else "FAIL"))
    print("  shipped C8 = 220 pF must move something:        worst %.2f dB    %s"
          % (live, "OK" if live > 0.5 else "FAIL"))
    ok &= dead < 1e-9 and live > 0.5

    print("\n=== SEARCH GATE: recover targets the topology CAN make ===")
    print("  (only structured targets count -- recovering a near-zero target tests nothing)")
    rng = np.random.default_rng(7)
    made, worst = 0, 0.0
    while made < (2 if quick else 3):
        x0 = np.array([rng.uniform(-3.0, 3.0) for _ in KEYS])
        r = eval_at(x0, bands)
        if r is None:
            continue
        tb, tc, _ = r
        if max(np.abs(tb).max(), np.abs(tc).max()) < 3.0:
            continue
        made += 1
        f, _ = opt(make_cost(bands, tb, tc), 3.0, 100 + made, quick)
        print("  target %d (peak |ratio| %5.2f dB): recovered to rms %.4f dB"
              % (made, max(np.abs(tb).max(), np.abs(tc).max()), f))
        worst = max(worst, f)
    print("  worst recovery %.4f dB (floor %.3f) -- %s"
          % (worst, TAKE_FLOOR_DB,
             "GATE PASSES" if worst < TAKE_FLOOR_DB else "GATE FAILS, do not read a refutation"))
    return ok and worst < TAKE_FLOOR_DB


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--quick", action="store_true", help="smaller DE budget; gate still applies")
    args = ap.parse_args()

    tgt = pedal_ratios(REPORT_LEVEL)
    bands = np.array(sorted(tgt))
    tb = np.array([tgt[f][0] for f in bands])
    tc = np.array([tgt[f][1] for f in bands])

    if args.selftest:
        sys.exit(0 if selftest(bands, args.quick) else 1)
    gate_ok = selftest(bands, args.quick)

    sb, sc, _ = ladder_ratios(bands, SHIP)
    print("\n=== 1. PEDAL (bleed-free OD transfer, drive noon, %s) vs the LINEAR LADDER ==="
          % REPORT_LEVEL)
    print("  The switch only moves C8's plate, so the ladder's ratio is a fixed linear curve.")
    print("  %6s | %8s %8s %8s | %8s %8s %8s"
          % ("f Hz", "ped B", "mdl B", "err B", "ped C", "mdl C", "err C"))
    for i, f in enumerate(bands):
        print("  %6.0f | %+8.2f %+8.2f %+8.2f | %+8.2f %+8.2f %+8.2f"
              % (f, tb[i], sb[i], tb[i] - sb[i], tc[i], sc[i], tc[i] - sc[i]))
    print("  rms error: boost %.2f dB | cut %.2f dB   (floor %.3f)"
          % (math.sqrt(np.mean((tb - sb) ** 2)), math.sqrt(np.mean((tc - sc) ** 2)),
             TAKE_FLOOR_DB))

    print("\n=== 2. LEVEL AXIS -- the (i) linear pre-clipper vs (ii) clipper-operating-point test ===")
    print("  (ii) requires the effect to FADE toward the linear regime. Read the DIRECTION.")
    show = [f for f in bands if f <= 700]
    for throw, idx in (("BOOST", 0), ("CUT", 1)):
        print("\n  ATTACK %s ratio (dB) by stimulus level:" % throw)
        print("    %-14s%s" % ("level", "".join("%8.0f" % f for f in show)))
        for lv in LEVELS:
            try:
                r = pedal_ratios(lv)
            except SystemExit:
                print("    %-14s(unavailable)" % lv)
                continue
            cells = []
            for f in show:
                key = min(r, key=lambda x: abs(x - f)) if r else None
                cells.append("%+8.2f" % r[key][idx]
                             if key is not None and abs(key - f) <= 0.06 * f else "      --")
            print("    %-14s%s" % (lv, "".join(cells)))
        lin = sb if idx == 0 else sc
        print("    %-14s%s" % ("LINEAR ladder",
                               "".join("%+8.2f" % lin[list(bands).index(f)] for f in show)))

    print("\n=== 3. REACHABILITY -- can ANY setting of the drawn ladder make this shape? ===")
    print("  All 11 elements freed at once (freeing schematic-verified parts only makes a")
    print("  negative result stronger), both throws scored with ONE parameter set.")
    widths = (3.0, 6.0) if args.quick else (1.5, 3.0, 6.0, 9.0)
    cost = make_cost(bands, tb, tc)
    print("  %-16s %14s" % ("box (decades)", "joint rms dB"))
    for w in widths:
        f, _ = opt(cost, w, 1, args.quick)
        print("  +/-%-13.1f %14.3f" % (w, f))
    print("  requirement: <= %.3f dB (the capture floor)" % TAKE_FLOOR_DB)
    if not gate_ok:
        print("\n  ⛔ THE GATE DID NOT PASS -- the numbers above measure the instrument, not the pedal.")


if __name__ == "__main__":
    main()
