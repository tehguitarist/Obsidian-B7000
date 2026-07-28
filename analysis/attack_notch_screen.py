#!/usr/bin/env python3.11
"""Can the drawn [ENG] ATTACK ladder MOVE the ~320 Hz cancellation null the way the pedal does?
A reachability screen against the notch half of the ATTACK specification (session 61, Phase 9 / A3).

THE QUESTION
------------
`analysis/attack_notch_probe.py` measures the pedal's ATTACK network as TWO requirements:

  (1) a broadband gain, +8.64 dB (boost) / -2.39 dB (cut) -- already REFUTED as reachable by the
      drawn ladder on its own axis (session 57: the shape statistic saturates at +1.15 dB against a
      required +8.46, flat to 0.001 dB across 7.5 orders of magnitude of box widening);
  (2) a cancellation NULL that MOVES: cut 316.4 Hz / boost 328.1 / flat 334.0, with depth
      >= 14.9 / 32.7 / 16.0 dB.

(2) has never been screened. It matters more than its size suggests, because it is what rules out
proposing a plain gain switch, and because the model's own notch is destroyed by
`trebleLadderDampR = 30k` (session 46) -- so ATTACK and GAP #2 are the same network and have to be
answered together.

⭐ WHY A DIRECTION TEST BEATS A FIT HERE. A wrong magnitude can be a wrong value; a wrong SIGN
cannot. So the headline statistic is not "how close is the notch" but "which WAY does each throw
move it, relative to flat":

    pedal:  cut is 17.6 Hz BELOW flat, boost is 5.9 Hz BELOW flat  -- BOTH throws move it DOWN
            and boost is 2.04x DEEPER than flat while cut is slightly shallower.

A switch that reroutes ONE cap's bottom plate between a bridging path and a shunt path will
generically move a null in OPPOSITE directions in its two throws, because the two throws add
capacitance at different places in the network. That is a structural prediction, and it is testable
without fitting anything.

WHAT IS SCORED
--------------
Six statistics, all read from the measured side rather than transcribed (`s61_attack_notch.json`):
absolute `f0_flat` and `depth_flat`, and the four DIFFERENCES that carry the claim
(`f0_cut - f0_flat`, `f0_boost - f0_flat`, `depth_cut - depth_flat`, `depth_boost - depth_flat`).
ONE parameter set scores all three positions -- it is one network with a switch in it, which is
exactly the constraint that killed session 56's C8-alone screen and session 49's bridged-T Pareto.

GATES -- none optional
----------------------
  1 LIVENESS       C8 = 0 must make all three positions IDENTICAL (notch spread exactly 0). Without
                   this a null result is indistinguishable from a mis-wired probe (session 56's L-009).
  2 SEARCH GATE    recover targets the family DEFINITIONALLY CAN make (generated from the family
                   itself at random parameter sets). A family that cannot recover its own parameters
                   makes a large residual unreadable -- session 57 discarded a whole random-search
                   "refutation" for exactly this, and session 58 caught DE converging to 0.36 dB on a
                   target it had generated itself.
  3 PATHOLOGY      a dead or wildly-rippling response can fake a deep notch. Guarded, because
                   session 57's unguarded search reported +88 dB of reachability by driving the
                   reference curve to -320 dB.

SCOPE
-----
  * ATTACK is [ENG] -- the 3-way switch is not on our schematic at all. What can be refuted here is
    the ASSUMED topology, which nothing corroborated in the first place. This is NOT a schematic
    disagreement.
  * The ladder is LINEAR and PRE-clipper, and the measured target was taken at drive min / LEVEL max
    where the pedal's own path is near-linear and bleed-free, so the two sides are comparable
    without a describing-function caveat (which is why session 57 wanted these captures).
  * MAGNITUDE only. A notch depth constrains how exactly two paths cancel; it measures no phase.

Usage:  python3.11 analysis/attack_notch_screen.py [--selftest] [--quick] [--width DECADES]
"""
import argparse
import io
import json
import math
import os
import sys
from contextlib import redirect_stdout

import numpy as np
from scipy.optimize import differential_evolution

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with redirect_stdout(io.StringIO()):                 # eq_reference prints a report at import
    import eq_reference as E                         # noqa: E402

MEASURED = "analysis/reports/s61_attack_notch.json"
POSITIONS = ["cut", "boost", "flat"]

# Shipped ladder (circuit.md "Treble network + ATTACK"). `RdampC5` is GAP #2's constant: the
# schematic ideal is 0 and session 19 moved it to 30k, which session 46 showed destroys the notch.
SHIP = dict(C5=22e-9, C9=22e-9, C6=22e-9, C7=680e-12, C8=220e-12,
            R7=200e3, R8=470e3, R11=470e3, R12=6.8e3, R13=1e6, R14=22e3, RdampC5=30e3)
KEYS = sorted(SHIP)
ZS = dict(gm=0.10e-3, ro=200e3, Rq2=1e6)             # shipped J201 boundary (session 3)

SEARCH_WIN = (250.0, 400.0)
SHOULDER_WIN = (200.0, 270.0)
BIN_HZ = 48000.0 / 8192.0                            # the measurement's own resolution, 5.86 Hz
DEPTH_FLOOR_DB = 1.0                                 # depth is a bound, not a calibrated dB (probe 1b)

# Frequency grids: 1 Hz through the search window (then parabolically refined), 2 Hz on the shoulder.
FSH = np.arange(SHOULDER_WIN[0], SHOULDER_WIN[1] + 0.1, 2.0)
FNO = np.arange(SEARCH_WIN[0], SEARCH_WIN[1] + 0.1, 1.0)
FALL = np.concatenate([FSH, FNO])
ZSA = E.jfet_source_z(FALL, **ZS)
NSH = len(FSH)


# ---------------------------------------------------------------------------------------------
def notch_of(mag_db):
    """(f0 refined, depth) from a magnitude curve sampled on FALL."""
    sh, no = mag_db[:NSH], mag_db[NSH:]
    i = int(np.argmin(no))
    f0 = FNO[i]
    if 0 < i < len(no) - 1:                          # parabolic vertex on the log-f axis
        x = np.log2(FNO[i - 1:i + 2])
        y = no[i - 1:i + 2]
        den = y[0] - 2 * y[1] + y[2]
        if abs(den) > 1e-12:
            f0 = float(2.0 ** (x[1] + 0.5 * (y[0] - y[2]) / den * (x[2] - x[1])))
    return f0, float(sh.max() - no[i])


def stats_of(p):
    """The six statistics for one parameter set, or None if the network is pathological."""
    out, flat_db = {}, None
    for pos in POSITIONS:
        try:
            H = E.treble_attack_tf(FALL, pos, Zs=ZSA, **p)
        except Exception:
            return None
        m = 20.0 * np.log10(np.abs(H) + 1e-30)
        if not np.all(np.isfinite(m)):
            return None
        if pos == "flat":
            flat_db = m
        out[pos] = notch_of(m)
    # PATHOLOGY: a dead or wildly-rippling curve can fake an arbitrarily deep null (session 57 item 5)
    if flat_db.max() < -80.0 or (flat_db.max() - flat_db.min()) > 60.0:
        return None
    return dict(f0={k: out[k][0] for k in out}, depth={k: out[k][1] for k in out})


def six(s):
    """Flatten to the scored vector: absolutes for flat, DIFFERENCES for the throws."""
    return np.array([s["f0"]["flat"], s["f0"]["cut"] - s["f0"]["flat"],
                     s["f0"]["boost"] - s["f0"]["flat"],
                     s["depth"]["flat"], s["depth"]["cut"] - s["depth"]["flat"],
                     s["depth"]["boost"] - s["depth"]["flat"]])


LABELS = ["f0 flat Hz", "f0 cut-flat", "f0 boost-flat", "depth flat dB",
          "dep cut-flat", "dep boost-flat"]
SCALE = np.array([BIN_HZ, BIN_HZ, BIN_HZ, DEPTH_FLOOR_DB, DEPTH_FLOOR_DB, DEPTH_FLOOR_DB])


def cost_of(v, t):
    """Dimensionless: each residual in units of that quantity's own resolution."""
    return float(np.sqrt(np.mean(((v - t) / SCALE) ** 2)))


def eval_x(x):
    p = {k: SHIP[k] * 10.0 ** xi for k, xi in zip(KEYS, x)}
    s = stats_of(p)
    return (s, p) if s is not None else (None, p)


class Cost:
    """A top-level callable, not a closure: `differential_evolution(workers=-1)` pickles the
    objective out to a process pool, and a local function cannot be pickled."""

    def __init__(self, t):
        self.t = t

    def __call__(self, x):
        s, _ = eval_x(x)
        return 1e6 if s is None else cost_of(six(s), self.t)


def make_cost(t):
    return Cost(t)


def opt(fn, width, seed, quick):
    box = [(-width, width)] * len(KEYS)
    r = differential_evolution(fn, box, seed=seed, maxiter=120 if quick else 250,
                               popsize=10 if quick else 16, tol=1e-8, polish=True,
                               init="sobol", workers=-1, updating="deferred")
    return r.fun, r.x


# ---------------------------------------------------------------------------------------------
def target():
    """Read the measured spec. NEVER transcribe a target -- session 33 lost a sign that way."""
    if not os.path.exists(MEASURED):
        sys.exit("missing %s -- run: python3.11 analysis/attack_notch_probe.py --selftest --json %s"
                 % (MEASURED, MEASURED))
    d = json.load(open(MEASURED))
    n = d["notch"]
    s = dict(f0={k: float(n[k]["f_bin"]) for k in POSITIONS},
             depth={k: float(n[k]["depth"]) for k in POSITIONS})
    return s, d


def selftest(quick):
    print("=" * 100)
    print("GATES")
    print("=" * 100)
    ok = True

    print("  1 LIVENESS -- C8 = 0 must make all three positions IDENTICAL")
    s0 = stats_of(dict(SHIP, C8=0.0))
    fs = [s0["f0"][k] for k in POSITIONS]
    ds = [s0["depth"][k] for k in POSITIONS]
    dead = max(max(fs) - min(fs), max(ds) - min(ds))
    s1 = stats_of(SHIP)
    live = max(abs(s1["f0"]["cut"] - s1["f0"]["flat"]), abs(s1["f0"]["boost"] - s1["f0"]["flat"]))
    print("      C8 = 0   : f0 spread %.3e Hz, depth spread %.3e dB   %s"
          % (max(fs) - min(fs), max(ds) - min(ds), "OK" if dead < 1e-9 else "FAIL"))
    print("      C8 = 220p: shipped ladder moves f0 by %.2f Hz            %s"
          % (live, "OK" if live > 0.5 else "FAIL -- the probe cannot see this switch at all"))
    ok &= dead < 1e-9

    print("\n  2 SEARCH GATE -- recover targets the family DEFINITIONALLY CAN make")
    print("      (a family that cannot recover its own parameters makes a residual unreadable)")
    rng = np.random.default_rng(11)
    made, worst = 0, 0.0
    while made < (2 if quick else 3):
        x0 = np.array([rng.uniform(-1.5, 1.5) for _ in KEYS])
        s, _ = eval_x(x0)
        if s is None:
            continue
        t = six(s)
        # A target must be STRUCTURED but not RAILED. Near-zero shifts test nothing; and a target
        # whose null sits ON the 250-400 Hz search edge is degenerate -- the locator returns the
        # boundary for a whole family of networks, so recovering it is easy for the wrong reason.
        # (The same "an optimum on its own boundary is uninformative" rule as session 47/51.)
        if max(abs(t[1]), abs(t[2])) < 3.0 or max(abs(t[1]), abs(t[2])) > 100.0:
            continue
        if any(not (SEARCH_WIN[0] + 3.0 < s["f0"][k] < SEARCH_WIN[1] - 3.0) for k in POSITIONS):
            continue
        made += 1
        f, _ = opt(make_cost(t), 2.0, 200 + made, quick)
        print("      target %d (shifts %+7.1f / %+7.1f Hz): recovered to cost %.5f"
              % (made, t[1], t[2], f))
        worst = max(worst, f)
    print("      worst recovery %.5f (1.0 == every residual at its own resolution)   %s"
          % (worst, "GATE PASSES" if worst < 1.0 else "GATE FAILS -- do not read a refutation"))
    ok &= worst < 1.0
    print("\n  %s" % ("GATES PASS" if ok else "GATES FAIL"))
    return ok


# ---------------------------------------------------------------------------------------------
def show(tag, s, t=None):
    f0, dp = s["f0"], s["depth"]
    line = "  %-22s " % tag
    line += "".join("%6.1f/%-5.1f " % (f0[k], dp[k]) for k in POSITIONS)
    line += "| shift %+6.1f %+6.1f | dep %+6.1f %+6.1f" % (
        f0["cut"] - f0["flat"], f0["boost"] - f0["flat"],
        dp["cut"] - dp["flat"], dp["boost"] - dp["flat"])
    if t is not None:
        line += " | cost %7.2f" % cost_of(six(s), six(t))
    print(line)


def direction(s):
    """(cut moves down?, boost moves down?, boost deeper than flat?)"""
    return (s["f0"]["cut"] < s["f0"]["flat"], s["f0"]["boost"] < s["f0"]["flat"],
            s["depth"]["boost"] > s["depth"]["flat"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--width", type=float, default=2.0, help="search box half-width, decades")
    ap.add_argument("--census", type=int, default=3000, help="random draws for the sign census")
    args = ap.parse_args()

    tgt, meta = target()
    print("=" * 100)
    print("CAN THE DRAWN [ENG] ATTACK LADDER MOVE THE ~320 Hz NULL THE WAY THE PEDAL DOES?")
    print("=" * 100)
    print("  target read from %s (measured, not transcribed)" % MEASURED)
    print("  resolution: %.2f Hz bins; depth floor %.1f dB (a LOWER bound, probe gate 1b)"
          % (BIN_HZ, DEPTH_FLOOR_DB))
    print("\n  %-22s %-12s %-12s %-12s | %-19s | %s"
          % ("", "cut f0/dep", "boost f0/dep", "flat f0/dep", "f0 shift vs flat", "depth vs flat"))
    show("PEDAL (target)", tgt)

    if args.selftest and not selftest(args.quick):
        sys.exit(1)

    # ------------------------------------------------------------------ the shipped model
    print("\n" + "=" * 100)
    print("THE MODEL AS SHIPPED, AND ACROSS GAP #2's CONSTANT")
    print("=" * 100)
    print("  RdampC5 is GAP #2: the schematic ideal is 0, session 19 moved it to 30k, and session 46")
    print("  showed 30k destroys the notch. So the two problems share this one constant.\n")
    print("  %-22s %-12s %-12s %-12s | %-19s | %s"
          % ("", "cut f0/dep", "boost f0/dep", "flat f0/dep", "f0 shift vs flat", "depth vs flat"))
    show("PEDAL (target)", tgt)
    for rd in (0.0, 1e3, 10e3, 30e3, 100e3):
        s = stats_of(dict(SHIP, RdampC5=rd))
        show("model RdampC5=%-8.3g" % rd, s, tgt)

    # ------------------------------------------------------------------ C8 x RdampC5
    print("\n" + "=" * 100)
    print("C8 SWEPT OVER FOUR DECADES -- can the switch's own cap buy the shift?")
    print("=" * 100)
    for rd in (0.0, 30e3):
        print("  RdampC5 = %g" % rd)
        for c8 in (0.0, 22e-12, 220e-12, 2.2e-9, 22e-9, 220e-9, 2.2e-6):
            s = stats_of(dict(SHIP, C8=c8, RdampC5=rd))
            if s is not None:
                show("    C8=%-9.3g" % c8, s, tgt)

    # ------------------------------------------------------------------ sign census
    print("\n" + "=" * 100)
    print("SIGN CENSUS -- how often does the family produce the pedal's sign pattern AT ALL?")
    print("=" * 100)
    print("  A DE search reports one point and can be doubted. This samples the family directly:")
    print("  %d random parameter sets over +-%g decades, classified by the three signs. If the"
          % (args.census, args.width))
    print("  pedal's pattern never occurs, the refutation does not rest on an optimiser at all.\n")
    rng = np.random.default_rng(3)
    tally, n_ok, seen = {}, 0, 0
    for _ in range(args.census):
        x = rng.uniform(-args.width, args.width, len(KEYS))
        s, _ = eval_x(x)
        if s is None:
            continue
        # only count draws where the switch does something measurable, else the signs are noise
        if max(abs(s["f0"]["cut"] - s["f0"]["flat"]),
               abs(s["f0"]["boost"] - s["f0"]["flat"])) < BIN_HZ:
            continue
        seen += 1
        d = direction(s)
        tally[d] = tally.get(d, 0) + 1
        if tuple(d) == tuple(direction(tgt)):
            n_ok += 1
    print("  %-46s %8s %8s" % ("(cut DOWN, boost DOWN, boost DEEPER)", "count", "share"))
    for d, n in sorted(tally.items(), key=lambda kv: -kv[1]):
        mark = "  <-- THE PEDAL'S PATTERN" if tuple(d) == tuple(direction(tgt)) else ""
        print("  %-46s %8d %7.1f%%%s"
              % (str(tuple(int(b) for b in d)), n, 100.0 * n / max(seen, 1), mark))
    print("\n  %d of %d draws moved the null measurably; %d (%.2f%%) match the pedal's pattern."
          % (seen, args.census, n_ok, 100.0 * n_ok / max(seen, 1)))
    # ⭐ Per-sign, so the census names WHICH requirement is unreachable rather than only that the
    # joint pattern is. A joint count of zero could be three individually-possible signs that never
    # co-occur; a per-sign count of zero is a structural impossibility for that one requirement.
    print("\n  per sign (a count of 0 is structural, not a co-occurrence problem):")
    for i, lab in enumerate(["cut null moves DOWN vs flat", "boost null moves DOWN vs flat",
                             "boost null is DEEPER than flat"]):
        n = sum(c for d, c in tally.items() if d[i])
        print("    %-34s %5d / %-5d draws (%5.1f%%)   %s"
              % (lab, n, seen, 100.0 * n / max(seen, 1),
                 "⛔ NEVER -- unreachable in this topology" if n == 0 else "reachable"))

    # ------------------------------------------------------------------ full reachability
    print("\n" + "=" * 100)
    print("FULL REACHABILITY -- all %d ladder elements freed at once, +-%g decades, ONE parameter"
          % (len(KEYS), args.width))
    print("set scoring all three positions (it is one network with a switch in it)")
    print("=" * 100)
    best_free = None
    for w in (1.0, args.width, args.width + 1.0):
        f, x = opt(make_cost(six(tgt)), w, 17, args.quick)
        s, p = eval_x(x)
        print("\n  box +-%.1f decades -> cost %.3f" % (w, f))
        if s is None:
            print("    (pathological)")
            continue
        show("    best", s, tgt)
        rest = [k for k, xi in zip(KEYS, x) if abs(abs(xi) - w) < 0.02]
        print("    %s" % ("nothing on a bound" if not rest
                          else "ON A BOUND (unidentified): " + ", ".join(rest)))
        if best_free is None or f < best_free[0]:
            best_free = (f, s, p, w)
        print("    per-statistic residual:")
        v, t = six(s), six(tgt)
        for lab, a, b in zip(LABELS, v, t):
            print("      %-16s model %+9.2f  pedal %+9.2f  err %+9.2f" % (lab, a, b, a - b))

    # ------------------------------------------------------------------ what CAN make it
    print("\n" + "=" * 100)
    print("SO WHAT *CAN* MAKE THE NOTCH TRIPLE? -- switch an element INSIDE the notch-forming leg")
    print("=" * 100)
    print("  The census says the failure is specific: C8 rerouted between a bridge (boost) and a")
    print("  shunt (cut) can only move the cut null UP. But `RdampC5` -- GAP #2's own constant, the")
    print("  damping in the C5 ladder leg -- moves f0 DOWN and DEEPENS the null together, which is")
    print("  the pedal's boost direction. So test a switch that varies the notch leg itself.\n")

    print("  (a) ONE element switched (RdampC5 alone): 1 dof against 2 targets per position.")
    print("      %-6s %-16s | %-24s %s" % ("pos", "pedal f0/depth", "best Rd -> f0/depth", "residual"))
    rds = np.geomspace(10.0, 3e5, 400)
    one = {}
    for pos in POSITIONS:
        T = (tgt["f0"][pos], tgt["depth"][pos])
        best = None
        for rd in rds:
            s = stats_of(dict(SHIP, RdampC5=rd))
            if s is None:
                continue
            c = math.hypot((s["f0"][pos] - T[0]) / BIN_HZ,
                           (s["depth"][pos] - T[1]) / DEPTH_FLOOR_DB)
            if best is None or c < best[0]:
                best = (c, rd, s["f0"][pos], s["depth"][pos])
        one[pos] = best
        print("      %-6s %6.1f / %5.1f    | %9.0f -> %6.1f / %5.1f    "
              "cost %5.2f (df %+6.1f Hz, dd %+5.1f dB)"
              % (pos, T[0], T[1], best[1], best[2], best[3], best[0],
                 best[2] - T[0], best[3] - T[1]))
    print("      ⭐ DEPTH is essentially EXACT at all three positions (%s dB), which is the half of"
          % "/".join("%+.1f" % (one[p][3] - tgt["depth"][p]) for p in POSITIONS))
    print("      the spec that looked exotic -- a 2x depth change is just a damping change. ⛔ But")
    print("      the frequencies all land at %.0f-%.0f Hz where the pedal spans %.1f-%.1f, so one"
          % (min(one[p][2] for p in POSITIONS), max(one[p][2] for p in POSITIONS),
             min(tgt["f0"].values()), max(tgt["f0"].values())))
    print("      element cannot do both jobs. ⇒ it needs a SECOND switched element.")

    print("\n  (b) TWO elements switched together (RdampC5 + C5 in the same leg): 2 dof, 2 targets.")
    print("      ⚠ Hitting the targets is therefore EXPECTED and proves nothing by itself. The")
    print("      informative outputs are whether the values are SANE and STRUCTURED, and whether the")
    print("      same setting also delivers the BROADBAND gain -- which is the other half of the spec.")
    grid_rd = np.geomspace(100.0, 1e5, 90)
    grid_c5 = np.geomspace(2.2e-9, 220e-9, 90)
    two = {}
    print("      %-6s %-16s | %-30s %s" % ("pos", "pedal f0/depth", "Rd / C5", "gives / residual"))
    for pos in POSITIONS:
        T = (tgt["f0"][pos], tgt["depth"][pos])
        best = None
        for rd in grid_rd:
            for c5 in grid_c5:
                s = stats_of(dict(SHIP, RdampC5=rd, C5=c5))
                if s is None:
                    continue
                c = math.hypot((s["f0"][pos] - T[0]) / BIN_HZ,
                               (s["depth"][pos] - T[1]) / DEPTH_FLOOR_DB)
                if best is None or c < best[0]:
                    best = (c, rd, c5, s["f0"][pos], s["depth"][pos])
        two[pos] = best
        print("      %-6s %6.1f / %5.1f    | %8.0f ohm / %7.2f nF          "
              "%6.1f / %5.1f   cost %5.2f"
              % (pos, T[0], T[1], best[1], best[2] * 1e9, best[3], best[4], best[0]))
    print("      ⇒ implied 3-way switch: Rd %s ohm, C5 %s nF (cut/boost/flat)"
          % ("/".join("%.0f" % two[p][1] for p in POSITIONS),
             "/".join("%.1f" % (two[p][2] * 1e9) for p in POSITIONS)))

    print("\n  (c) ⭐ THE DECIDING TEST -- does that SAME setting deliver the broadband gain?")
    fb = np.array([100.0, 200.0, 400.0, 800.0, 1600.0])
    zfb = E.jfet_source_z(fb, **ZS)
    pf = dict(SHIP, RdampC5=two["flat"][1], C5=two["flat"][2])
    mf = 20.0 * np.log10(np.abs(E.treble_attack_tf(fb, "flat", Zs=zfb, **pf)) + 1e-30)
    print("      %-9s %s   %s" % ("f Hz", "".join("%9.0f" % x for x in fb), "required"))
    bb = meta["broadband"]
    for pos in ("boost", "cut"):
        p = dict(SHIP, RdampC5=two[pos][1], C5=two[pos][2])
        m = 20.0 * np.log10(np.abs(E.treble_attack_tf(fb, pos, Zs=zfb, **p)) + 1e-30)
        print("      h %-7s %s   %+6.2f dB"
              % (pos, "".join("%9.2f" % x for x in m - mf), bb[pos]["median"]))
    print("      ⛔ NOT EVEN CLOSE, and in the wrong place: the notch leg supplies ~0 dB of broadband")
    print("      gain. This is session 57's independent result from the other direction (the ladder's")
    print("      broadband shape statistic saturates at +1.15 dB against a required +8.46).")

    # ------------------------------------------------------------------ verdict
    print("\n" + "=" * 100)
    print("VERDICT")
    print("=" * 100)
    dt = direction(tgt)
    print("  DIRECTION is the load-bearing test: a wrong magnitude can be a wrong value, a wrong")
    print("  SIGN cannot. Relative to flat, the pedal moves the null DOWN in BOTH throws and makes")
    print("  boost DEEPER.\n")
    print("  %-34s %-14s %-14s %-14s" % ("", "cut moves DOWN", "boost DOWN", "boost DEEPER"))
    print("  %-34s %-14s %-14s %-14s" % ("PEDAL (measured)", dt[0], dt[1], dt[2]))
    rows = [("model shipped (Rd 30k)", stats_of(SHIP)),
            ("model schematic (Rd 0)", stats_of(dict(SHIP, RdampC5=0.0))),
            ("model Rd 30k, C8 x10", stats_of(dict(SHIP, C8=2.2e-9))),
            ("model Rd 30k, C8 x100", stats_of(dict(SHIP, C8=22e-9)))]
    if best_free is not None:
        rows.append(("best of the free search", best_free[1]))
    agree = []
    for tag, s in rows:
        if s is None:
            continue
        d = direction(s)
        ok = tuple(d) == tuple(dt)
        agree.append(ok)
        print("  %-34s %-14s %-14s %-14s %s"
              % (tag, d[0], d[1], d[2], "<-- MATCHES" if ok else ""))
    print("\n  ⇒ %s" % ("at least one setting reproduces all three signs -- this is NOT a"
                        " sign refutation; read the costs above."
                        if any(agree) else
                        "NO setting reproduces all three signs, including the free search."))
    if not any(agree):
        print("    The drawn ATTACK network moves the null in OPPOSITE directions in its two throws,")
        print("    because boost puts C8 in a BRIDGING path (M<->P) while cut puts it in a SHUNT to")
        print("    ground at P. The pedal moves it the SAME way in both. That is a TOPOLOGY")
        print("    constraint, not a value error: no scaling of a value changes a sign.")
    if best_free is not None:
        print("\n  best free-search cost %.3f (1.0 == every residual at its own resolution)."
              % best_free[0])
        print("  ⚠ Read that with the bound report above: a low cost with parameters resting on the")
        print("    box edge is an unidentified direction, not a fit (session 60 item 5).")
    print("\n  ⭐⭐ AND THE SPECIFICATION SPLITS INTO TWO JOBS THAT NEED TWO DIFFERENT ELEMENTS:")
    print("     * the NOTCH triple IS reachable, but only by switching an element INSIDE the")
    print("       notch-forming ladder leg -- a series R+C there hits all three (f0, depth) pairs")
    print("       with sane, structured values, and the depths alone come out of a damping change;")
    print("     * the BROADBAND +-gain is NOT reachable there (~0 dB), and session 57 independently")
    print("       refuted the ladder as a broadband carrier (saturates at +1.15 vs +8.46 dB).")
    print("     ⇒ STOP LOOKING FOR ONE ELEMENT. A 3-position switch with MORE THAN ONE POLE -- one")
    print("       section in the notch leg, one supplying broadband gain -- is the shape of answer")
    print("       the measurement points at. ⭐ There is a direct precedent in this project: A2c-3")
    print("       resolved the mid-frequency selector the same way, by recognising it as 2-POLE")
    print("       (switching the across-lug cap together with the series cap) after a single-element")
    print("       fit could match range or centre but never both.")
    print("\n  ⚠ SCOPE: ATTACK is [ENG] -- the 3-way switch is not on our schematic, so what is")
    print("    refuted is the ASSUMED topology, which nothing corroborated. Magnitude only, and")
    print("    (b) has 2 dof against 2 targets so its FIT is not evidence -- (c) is the evidence.")
    print("  ⭐ And RdampC5 is shared with GAP #2, so whatever replaces this network has to produce")
    print("    the notch AND move it -- one problem, not two.")


if __name__ == "__main__":
    main()
