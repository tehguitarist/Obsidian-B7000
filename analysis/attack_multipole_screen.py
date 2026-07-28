#!/usr/bin/env python3.11
"""WHICH element does a MULTI-POLE ATTACK switch have to move, and what is left for the other pole?
A census over the notch-forming leg (session 62, Phase 9 / A3 step 19).

WHERE THIS COMES FROM
---------------------
Session 61 measured the ATTACK network as TWO requirements that one section cannot both meet:

  (A) a BROADBAND gain, boost +8.64 dB / cut -2.39 dB, flat to ~+-1 dB over 80 Hz-1.6 kHz;
  (B) a cancellation NULL that MOVES: cut 316.4 / boost 328.1 / flat 334.0 Hz, depth >= 14.9 /
      32.7 / 16.0 dB.

and then showed (step 18) that (B) IS reachable inside the notch-forming ladder leg while (A) is
NOT reachable there at all -- the best notch-leg setting supplies ~0 dB broadband (-0.14 .. +2.60 dB
against a required +8.64). That is a DIRECTION, not a dead end: it says the switch has more than one
pole, one section in the notch leg and one supplying broadband gain somewhere the ladder is not.
Direct precedent: A2c-3 resolved the mid-frequency selector the same way, by recognising it as
2-POLE after single-element fits could match range *or* centre but never both.

WHAT THIS TOOL ADDS
-------------------
Session 61 tried exactly one notch-leg candidate (`RdampC5`, alone and with `C5`). It hit the notch
triple -- but 2 free values against 2 targets per position hit them BY CONSTRUCTION, which session
61 flagged itself. So the fit was never evidence about WHICH element the switch moves.

This screens the whole notch-leg design space and makes it falsifiable by scoring the thing the
construction cannot buy: after pole 1 is fitted to the notch triple, POLE 2 IS A FLAT SCALAR, so the
part of `h` that pole 1 leaves behind must already be FLAT. Every candidate therefore faces

  6 notch numbers   (3 x f0, 3 x depth)              -- what the fit is aimed at, and
  ~2 x 60 h bins    (the SHAPE of h once its median is removed)   -- what it is TESTED on,

against 6 or 7 free values. The fitted pole-2 gain `g` is then read out and compared with the
measured +8.64 / 0 / -2.39 dB as a PREDICTION -- it is never an input to the fit.

READ THE OUTPUT THIS WAY
------------------------
  * `bb` (the broadband SHAPE cost) is the discriminator. `notch` is nearly free for any 2-element
    pair and means little on its own.
  * `g boost/cut` is out-of-sample. A pair that fits the notch and predicts a `g` far from
    +8.64/-2.39 has explained the notch by borrowing broadband gain it is not allowed to have.
  * A passive tap can only ATTENUATE, so `g boost > g flat > g cut` (i.e. boost = the unattenuated
    throw) is the realisable ordering; anything else needs an ACTIVE second section.

GATES -- none optional
----------------------
  1 SOLVER      the vectorised network solver must reproduce `eq_reference.treble_attack_tf` to
                ~1e-12 dB on random parameter sets. A private fast copy of a shared oracle is a
                silent-divergence trap; this makes the copy provable rather than plausible.
  2 LIVENESS    with the switch doing nothing (identical values in all three positions, C8 = 0) the
                notch spread and `h` must be exactly zero. Without it a null result is
                indistinguishable from a mis-wired probe (session 56's L-009).
  3 SEARCH      recover a target the family DEFINITIONALLY can make (generated from the family
                itself). A family that cannot recover its own parameters makes a residual
                unreadable -- session 57 discarded a whole random-search refutation for this, and
                session 58 caught DE converging to 0.36 dB on a target it had generated.
  4 PATHOLOGY   a dead or wildly-rippling response can fake an arbitrarily deep null (session 57).

SCOPE
-----
  * ATTACK is [ENG] -- the 3-way switch is not on our schematic at all. Nothing here disagrees with
    a drawn circuit; it constrains what to PROPOSE.
  * MAGNITUDE only, and the notch depths are LOWER bounds (two understating mechanisms, probe gate
    1(b)) -- so depth is scored loosely and its RANKING is what carries the claim.
  * The broadband window excludes the MEASURED notch window by name, and uses the UNION of the two
    throws' windows so both are scored on the SAME members (the session-49 item-7 rule).

Usage:  python3.11 analysis/attack_multipole_screen.py [--selftest] [--quick] [--pairs N]
"""
import argparse
import io
import itertools
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from contextlib import redirect_stdout

import numpy as np
from scipy.optimize import differential_evolution

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with redirect_stdout(io.StringIO()):                 # eq_reference prints a report at import
    import eq_reference as E                         # noqa: E402

MEASURED = "analysis/reports/s61_attack_notch.json"
POSITIONS = ["cut", "boost", "flat"]
THROWS = ["boost", "cut"]

# Shipped ladder (circuit.md "Treble network + ATTACK"). RdampC5 is GAP #2's own constant: the
# schematic ideal is 0, session 19 moved it to 30k, session 46 showed 30k destroys the notch.
SHIP = dict(C5=22e-9, C9=22e-9, C6=22e-9, C7=680e-12, C8=220e-12,
            R7=200e3, R8=470e3, R11=470e3, R12=6.8e3, R13=1e6, R14=22e3, RdampC5=30e3)
ELEMS = sorted(SHIP)
ZS = dict(gm=0.10e-3, ro=200e3, Rq2=1e6)             # shipped J201 boundary (session 3)

SEARCH_WIN = (250.0, 400.0)
SHOULDER_WIN = (200.0, 270.0)
BIN_HZ = 48000.0 / 8192.0                            # the measurement's own resolution, 5.86 Hz
DEPTH_FLOOR_DB = 1.0                                 # depth is a bound, not a calibrated dB
BOX = 2.0                                            # search half-width, decades

FSH = np.arange(SHOULDER_WIN[0], SHOULDER_WIN[1] + 0.1, 2.0)
FNO = np.arange(SEARCH_WIN[0], SEARCH_WIN[1] + 0.1, 1.0)
NSH = len(FSH)


# =============================================================================================
# vectorised network solver (GATE 1 proves it equals eq_reference.treble_attack_tf)
# =============================================================================================
def tf_batch(f, zs, position, p):
    """V(Q)/Vth for the treble ladder, all frequencies at once.

    Identical algebra to eq_reference.treble_attack_tf with Zs given (n = 6 unknowns), rewritten as
    ONE stacked np.linalg.solve so a differential-evolution search is affordable. Node order here
    is the oracle's: [M, P, L1, L2, Q, G].
    """
    s = 2j * np.pi * np.asarray(f, dtype=float)
    n = len(s)
    yC5, yC9, yC6 = s * p["C5"], s * p["C9"], s * p["C6"]
    yC7, yC8 = s * p["C7"], s * p["C8"]
    if p["RdampC5"] > 0.0:                           # lossy C5: series Rd + C5 -> one admittance
        yC5 = yC5 / (1.0 + yC5 * p["RdampC5"])
    pos = position.lower()
    gMP = yC8 if pos == "boost" else np.zeros(n)     # C8 bridges R8
    gPg = yC8 if pos == "cut" else np.zeros(n)       # C8 shunts P -> GND
    gS = 1.0 / np.broadcast_to(np.asarray(zs, dtype=complex), (n,))
    g7, g8, g11, g12, g13, g14 = (1.0 / p["R7"], 1.0 / p["R8"], 1.0 / p["R11"],
                                  1.0 / p["R12"], 1.0 / p["R13"], 1.0 / p["R14"])

    A = np.zeros((n, 6, 6), dtype=complex)
    A[:, 0, 0] = g7 + g8 + yC6 + gMP; A[:, 0, 1] = -(g8 + gMP); A[:, 0, 3] = -yC6; A[:, 0, 5] = -g7
    A[:, 1, 1] = g8 + g11 + yC7 + gMP + gPg; A[:, 1, 0] = -(g8 + gMP); A[:, 1, 4] = -yC7
    A[:, 2, 2] = yC5 + yC9 + g12; A[:, 2, 3] = -yC9; A[:, 2, 5] = -yC5
    A[:, 3, 3] = yC9 + yC6 + g14; A[:, 3, 2] = -yC9; A[:, 3, 0] = -yC6
    A[:, 4, 4] = yC7 + g13; A[:, 4, 1] = -yC7
    A[:, 5, 5] = gS + g7 + yC5; A[:, 5, 0] = -g7; A[:, 5, 2] = -yC5
    b = np.zeros((n, 6), dtype=complex)
    b[:, 5] = gS
    return np.linalg.solve(A, b)[:, 4]


def db(x):
    return 20.0 * np.log10(np.abs(x) + 1e-300)


# =============================================================================================
# the measured record
# =============================================================================================
def load_record():
    """Read the measurement. NEVER transcribe a target -- session 33 lost a sign that way."""
    if not os.path.exists(MEASURED):
        sys.exit("missing %s -- run: python3.11 analysis/attack_notch_probe.py --json %s"
                 % (MEASURED, MEASURED))
    d = json.load(open(MEASURED))
    if "h_curve" not in d:
        sys.exit("%s predates the h_curve field -- regenerate it with attack_notch_probe.py" % MEASURED)
    n = d["notch"]
    tgt = dict(f0={k: float(n[k]["f_bin"]) for k in POSITIONS},
               depth={k: float(n[k]["depth"]) for k in POSITIONS})
    hc = d["h_curve"]
    f = np.asarray(hc["f"], dtype=float)
    lo, hi = d["meta"]["broad_win"]
    # UNION of the two MEASURED notch windows, so boost and cut are scored on the SAME members
    # (an rms over different members is not a comparison -- session 49 item 7).
    wins = [d["broadband"][p]["window"] for p in THROWS]
    excl = (min(w[0] for w in wins), max(w[1] for w in wins))
    keep = (f >= lo) & (f <= hi) & ~((f >= excl[0]) & (f <= excl[1]))
    keep &= np.arange(len(f)) % 2 == 0               # every 2nd bin: 11.7 Hz, still far finer than
    return dict(tgt=tgt, f_bb=f[keep],               # any feature h has outside the notch
                h={p: np.asarray(hc[p], dtype=float)[keep] for p in THROWS},
                excl=excl, broad_win=(lo, hi), floor=float(d["meta"]["diff_floor"]), raw=d)


REC = load_record()
FBB = REC["f_bb"]
FALL = np.concatenate([FSH, FNO, FBB])
ZSA = E.jfet_source_z(FALL, **ZS)
NBB = len(FBB)


# =============================================================================================
# scoring
# =============================================================================================
def notch_of(mag_db):
    """(f0 refined parabolically on the log-f axis, depth below the shoulder)."""
    sh, no = mag_db[:NSH], mag_db[NSH:NSH + len(FNO)]
    i = int(np.argmin(no))
    f0 = FNO[i]
    if 0 < i < len(no) - 1:
        x = np.log2(FNO[i - 1:i + 2])
        y = no[i - 1:i + 2]
        den = y[0] - 2 * y[1] + y[2]
        if abs(den) > 1e-12:
            f0 = float(2.0 ** (x[1] + 0.5 * (y[0] - y[2]) / den * (x[2] - x[1])))
    return f0, float(sh.max() - no[i])


def evaluate(pp, c8_on):
    """pp = {position: full 12-element dict}. -> dict of stats, or None if pathological."""
    out, mags = {}, {}
    for pos in POSITIONS:
        eff = pos if c8_on else "flat"
        m = db(tf_batch(FALL, ZSA, eff, pp[pos]))
        if not np.all(np.isfinite(m)):
            return None
        mags[pos] = m
        out[pos] = notch_of(m)
    flat = mags["flat"]
    # GATE 4 PATHOLOGY: a dead or wildly-rippling curve can fake an arbitrarily deep null.
    if flat.max() < -80.0 or (flat.max() - flat.min()) > 60.0:
        return None
    r = {p: mags[p][-NBB:] - flat[-NBB:] for p in THROWS}
    g = {p: float(np.median(REC["h"][p] - r[p])) for p in THROWS}
    shape = {p: (REC["h"][p] - r[p]) - g[p] for p in THROWS}
    return dict(f0={k: out[k][0] for k in out}, depth={k: out[k][1] for k in out},
                g=g, shape=shape, r=r)


def costs(st):
    """(notch cost, broadband SHAPE cost) -- each dimensionless, 1.0 == at its own resolution."""
    t = REC["tgt"]
    nr = [(st["f0"][p] - t["f0"][p]) / BIN_HZ for p in POSITIONS]
    nr += [(st["depth"][p] - t["depth"][p]) / DEPTH_FLOOR_DB for p in POSITIONS]
    br = np.concatenate([st["shape"][p] for p in THROWS]) / REC["floor"]
    return float(np.sqrt(np.mean(np.square(nr)))), float(np.sqrt(np.mean(np.square(br))))


def total(st):
    n, b = costs(st)
    return float(np.sqrt(0.5 * n * n + 0.5 * b * b))


def unpack(x, sw, shared_rd):
    """x -> {position: 12-element dict}. `sw` = the elements the switch moves, per position."""
    pp = {}
    k = 0
    per = {}
    for e in sw:
        for pos in POSITIONS:
            per[(e, pos)] = SHIP[e] * 10.0 ** x[k]
            k += 1
    rd = SHIP["RdampC5"] * 10.0 ** x[k] if shared_rd else None
    for pos in POSITIONS:
        p = dict(SHIP)
        if shared_rd:
            p["RdampC5"] = rd
        for e in sw:
            p[e] = per[(e, pos)]
        pp[pos] = p
    return pp


class Cost:
    """Top-level callable so a ProcessPoolExecutor can pickle it."""

    def __init__(self, sw, c8_on, target=None):
        self.sw, self.c8_on, self.target = tuple(sw), c8_on, target

    def __call__(self, x):
        shared_rd = "RdampC5" not in self.sw
        st = evaluate(unpack(x, self.sw, shared_rd), self.c8_on)
        if st is None:
            return 1e6
        if self.target is None:
            return total(st)
        return float(np.sqrt(np.mean(np.square(
            (np.array([st["f0"][p] for p in POSITIONS] + [st["depth"][p] for p in POSITIONS])
             - self.target) / np.array([BIN_HZ] * 3 + [DEPTH_FLOOR_DB] * 3)))))


def ndof(sw):
    return 3 * len(sw) + (0 if "RdampC5" in sw else 1)


def fit(sw, c8_on, quick, seed=7):
    fn = Cost(sw, c8_on)
    box = [(-BOX, BOX)] * ndof(sw)
    r = differential_evolution(fn, box, seed=seed, maxiter=90 if quick else 200,
                               popsize=12 if quick else 18, tol=1e-9, polish=True, init="sobol")
    shared_rd = "RdampC5" not in sw
    pp = unpack(r.x, sw, shared_rd)
    return r.fun, r.x, pp, evaluate(pp, c8_on)


def job(a):
    sw, c8_on, quick = a
    f, x, pp, st = fit(sw, c8_on, quick)
    if st is None:
        return sw, c8_on, None
    n, b = costs(st)
    return sw, c8_on, dict(total=f, notch=n, bb=b, g=st["g"],
                           f0=st["f0"], depth=st["depth"], x=list(x),
                           vals={e: {p: pp[p][e] for p in POSITIONS} for e in sw},
                           rd=pp["flat"]["RdampC5"])


# =============================================================================================
# gates
# =============================================================================================
def selftest(quick):
    print("=" * 104)
    print("GATES")
    print("=" * 104)
    ok = True

    print("  1 SOLVER -- the vectorised solver must equal eq_reference.treble_attack_tf")
    rng = np.random.default_rng(5)
    worst = 0.0
    for trial in range(4):
        p = {k: SHIP[k] * 10.0 ** rng.uniform(-1.0, 1.0) for k in ELEMS}
        fs = np.geomspace(20.0, 16000.0, 41)
        zs = E.jfet_source_z(fs, **ZS)
        for pos in POSITIONS:
            a = tf_batch(fs, zs, pos, p)
            b = E.treble_attack_tf(fs, pos, Zs=zs, **p)
            worst = max(worst, float(np.max(np.abs(db(a) - db(b)))),
                        float(np.max(np.abs(np.angle(a) - np.angle(b)))) * 180.0 / np.pi)
    print("      worst |d dB| / |d deg| over 4 random parameter sets x 3 positions: %.3e   %s"
          % (worst, "OK" if worst < 1e-9 else "FAIL -- the fast copy has diverged"))
    ok &= worst < 1e-9

    print("\n  2 LIVENESS -- a switch that moves nothing must give zero spread and zero h")
    pp = {p: dict(SHIP, C8=0.0) for p in POSITIONS}
    st = evaluate(pp, c8_on=True)
    fs = [st["f0"][p] for p in POSITIONS]
    ds = [st["depth"][p] for p in POSITIONS]
    dead = max(max(fs) - min(fs), max(ds) - min(ds))
    rmax = max(float(np.max(np.abs(st["r"][p]))) for p in THROWS)
    print("      C8 = 0, identical values: f0 spread %.2e Hz, depth spread %.2e dB, |r| max %.2e dB"
          % (max(fs) - min(fs), max(ds) - min(ds), rmax))
    live = evaluate({p: dict(SHIP) for p in POSITIONS}, c8_on=True)
    mv = max(abs(live["f0"][p] - live["f0"]["flat"]) for p in THROWS)
    print("      C8 = 220p shipped   : the drawn switch moves f0 by %.2f Hz  %s"
          % (mv, "OK" if mv > 0.5 else "FAIL -- the probe cannot see this switch"))
    print("      %s" % ("OK" if dead < 1e-9 and rmax < 1e-9 else "FAIL"))
    ok &= dead < 1e-9 and rmax < 1e-9

    print("\n  3 SEARCH -- recover a target the family DEFINITIONALLY can make")
    print("      (a family that cannot recover its own parameters makes a residual unreadable)")
    rng = np.random.default_rng(19)
    made, worst_rec = 0, 0.0
    sw = ("RdampC5", "C5")
    while made < (2 if quick else 3):
        x0 = rng.uniform(-1.0, 1.0, ndof(sw))
        st = evaluate(unpack(x0, sw, False), c8_on=True)
        if st is None:
            continue
        # STRUCTURED but not RAILED: a near-zero shift tests nothing, and a null sitting ON the
        # 250-400 Hz search edge is recovered for the wrong reason (session 47/51's boundary rule).
        sh = [st["f0"][p] - st["f0"]["flat"] for p in THROWS]
        if max(abs(v) for v in sh) < 3.0:
            continue
        if any(not (SEARCH_WIN[0] + 3.0 < st["f0"][p] < SEARCH_WIN[1] - 3.0) for p in POSITIONS):
            continue
        made += 1
        t = np.array([st["f0"][p] for p in POSITIONS] + [st["depth"][p] for p in POSITIONS])
        r = differential_evolution(Cost(sw, True, target=t), [(-BOX, BOX)] * ndof(sw),
                                   seed=300 + made, maxiter=90 if quick else 180,
                                   popsize=12 if quick else 16, tol=1e-9, polish=True, init="sobol")
        print("      target %d (shifts %+6.1f / %+6.1f Hz): recovered to %.5f" % (made, sh[0], sh[1], r.fun))
        worst_rec = max(worst_rec, r.fun)
    print("      worst recovery %.5f (1.0 == every residual at its own resolution)   %s"
          % (worst_rec, "GATE PASSES" if worst_rec < 1.0 else "GATE FAILS"))
    ok &= worst_rec < 1.0

    print("\n  %s" % ("GATES PASS" if ok else "GATES FAIL"))
    return ok


# =============================================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--pairs", type=int, default=0, help="0 = all pairs; N = the N cheapest singles' pairs")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    t = REC["tgt"]
    print("=" * 104)
    print("WHAT MUST A MULTI-POLE ATTACK SWITCH MOVE? -- a census over the notch-forming leg")
    print("=" * 104)
    print("  target read from %s (measured, never transcribed)" % MEASURED)
    print("  notch    cut %.1f Hz / %.1f dB | boost %.1f / %.1f | flat %.1f / %.1f"
          % (t["f0"]["cut"], t["depth"]["cut"], t["f0"]["boost"], t["depth"]["boost"],
             t["f0"]["flat"], t["depth"]["flat"]))
    print("  h        boost %+0.2f dB | cut %+0.2f dB (medians), scored as SHAPE over %d bins each"
          % (float(np.median(REC["h"]["boost"])), float(np.median(REC["h"]["cut"])), NBB))
    print("  window   %g-%g Hz EXCLUDING the measured notch window %.1f-%.1f Hz (union of both"
          % (REC["broad_win"][0], REC["broad_win"][1], REC["excl"][0], REC["excl"][1]))
    print("           throws, so boost and cut are scored on the SAME members)")
    print("  floors   %.2f Hz bins | depth %.1f dB (a LOWER bound) | h %.3f dB"
          % (BIN_HZ, DEPTH_FLOOR_DB, REC["floor"]))

    if args.selftest and not selftest(args.quick):
        sys.exit(1)

    # ------------------------------------------------------------------ the census
    singles = [(e,) for e in ELEMS]
    pairs = [tuple(sorted(c)) for c in itertools.combinations(ELEMS, 2)]
    tasks = [(sw, True, args.quick) for sw in singles + pairs]
    tasks += [(sw, False, args.quick) for sw in singles + pairs]   # C8 rerouting removed
    print("\n" + "=" * 104)
    print("CENSUS -- %d families (%d subsets x {C8 switch kept, C8 switch removed})"
          % (len(tasks), len(singles) + len(pairs)))
    print("=" * 104)
    print("  Each family: one parameter set per ATTACK position for the switched element(s), plus a")
    print("  SHARED free RdampC5 when the switch does not already move it (GAP #2 says 30k is wrong)")
    print("  -- %d-%d free values against 6 notch numbers AND %d h bins."
          % (ndof(("C5",)), ndof(("C5", "C9")), 2 * NBB))
    print("  ⚠ `notch` is nearly free for any 2-element family: 2 values against 2 targets per")
    print("    position hit them BY CONSTRUCTION. `bb` is the test; `g` is out-of-sample.\n")

    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) - 2)) as ex:
        res = [r for r in ex.map(job, tasks) if r[2] is not None]
    res.sort(key=lambda r: r[2]["bb"])

    hdr = "  %-26s %-4s %7s %7s %8s  %8s %8s   %s"
    print(hdr % ("switched", "C8", "bb", "notch", "total", "g boost", "g cut", "values"))
    print("  " + "-" * 100)
    meas_g = {p: float(np.median(REC["h"][p])) for p in THROWS}
    for sw, c8, r in res[:18]:
        v = "  ".join("%s %s" % (e, "/".join(fmt(r["vals"][e][p]) for p in POSITIONS)) for e in sw)
        print(hdr % ("+".join(sw), "on" if c8 else "off", "%.2f" % r["bb"], "%.2f" % r["notch"],
                     "%.2f" % r["total"], "%+.2f" % r["g"]["boost"], "%+.2f" % r["g"]["cut"], v))
    print("  " + "-" * 100)
    print("  %-26s %-4s %7s %7s %8s  %8s %8s   (the MEASUREMENT)"
          % ("PEDAL", "", "0.00", "0.00", "0.00", "%+.2f" % meas_g["boost"], "%+.2f" % meas_g["cut"]))

    best = res[0]
    print("\n" + "=" * 104)
    print("BEST BY BROADBAND SHAPE: %s (C8 rerouting %s)"
          % ("+".join(best[0]), "kept" if best[1] else "removed"))
    print("=" * 104)
    show_detail(best)

    # ------------------------------------------------------------------ pole 2
    print("\n" + "=" * 104)
    print("POLE 2 -- what the notch section leaves for the other section to supply")
    print("=" * 104)
    print("  `g` is what a FLAT scalar would have to add on top of the fitted notch leg to reproduce")
    print("  the measured h. It is a PREDICTION: nothing in the fit was aimed at it.\n")
    print("  %-30s %9s %9s %9s" % ("family", "g boost", "g cut", "boost-cut"))
    for sw, c8, r in res[:8]:
        print("  %-30s %+9.2f %+9.2f %+9.2f"
              % ("+".join(sw) + (" (C8 on)" if c8 else " (C8 off)"),
                 r["g"]["boost"], r["g"]["cut"], r["g"]["boost"] - r["g"]["cut"]))
    print("  %-30s %+9.2f %+9.2f %+9.2f"
          % ("MEASURED h (medians)", meas_g["boost"], meas_g["cut"],
             meas_g["boost"] - meas_g["cut"]))
    print("\n  A passive tap can only ATTENUATE, so a realisable passive pole 2 needs")
    print("  g(boost) > g(flat) = 0 > g(cut). g(boost) = %+0.2f dB means the flat position must"
          % meas_g["boost"])
    print("  itself carry ~%.1f dB of attenuation that the boost throw removes." % meas_g["boost"])

    if args.json:
        out = dict(measured=dict(notch=t, g=meas_g),
                   families=[dict(switched=list(sw), c8=c8, **{k: v for k, v in r.items()
                                                               if k != "x"}) for sw, c8, r in res])
        os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
        json.dump(out, open(args.json, "w"), indent=1, default=float)
        print("\n  wrote %s" % args.json)


def fmt(v):
    if v >= 1e3:
        return "%.3gk" % (v / 1e3)
    if v >= 1.0:
        return "%.3g" % v
    if v >= 1e-9:
        return "%.3gn" % (v * 1e9)
    return "%.3gp" % (v * 1e12)


def show_detail(entry):
    sw, c8, r = entry
    t = REC["tgt"]
    pp = unpack(np.array(r["x"]), sw, "RdampC5" not in sw)
    st = evaluate(pp, c8)
    print("  %-8s %-22s %-22s | %s" % ("pos", "f0 Hz  model / pedal", "depth dB model / pedal",
                                       "switched values"))
    for p in POSITIONS:
        v = ", ".join("%s = %s" % (e, fmt(pp[p][e])) for e in sw)
        print("  %-8s %9.1f / %-10.1f %9.2f / %-10.2f | %s"
              % (p, st["f0"][p], t["f0"][p], st["depth"][p], t["depth"][p], v))
    if "RdampC5" not in sw:
        print("  shared   RdampC5 = %s (schematic 0, shipped 30k -- GAP #2's own constant)"
              % fmt(pp["flat"]["RdampC5"]))
    print("\n  broadband residual after removing the fitted flat gain g (this is what pole 2 CANNOT fix):")
    print("  %9s %10s %10s" % ("f Hz", "boost", "cut"))
    for target in (80.0, 128.0, 200.0, 254.0, 404.0, 640.0, 810.0, 1014.0, 1600.0):
        i = int(np.argmin(np.abs(FBB - target)))
        print("  %9.1f %+10.2f %+10.2f" % (FBB[i], st["shape"]["boost"][i], st["shape"]["cut"][i]))
    for p in THROWS:
        s = st["shape"][p]
        print("  %-6s rms %.2f dB, peak %+.2f dB  (floor %.3f)"
              % (p, float(np.sqrt(np.mean(s ** 2))), float(s[np.argmax(np.abs(s))]), REC["floor"]))


if __name__ == "__main__":
    main()
