#!/usr/bin/env python3.11
"""Can ONE pole do both jobs -- if the ATTACK switch MOVES THE OUTPUT TAP along the R7/R8 divider?
A structural proposal screened against the whole ATTACK record (session 62, Phase 9 / A3 step 19).

THE IDEA, AND WHERE IT CAME FROM
--------------------------------
Session 61 concluded the ATTACK switch needs more than one pole: the notch triple is reachable
inside the notch-forming ladder leg, the broadband +8.6/-2.4 dB is not reachable there at all.
That is true of every family in which the switch changes an element VALUE.

But a switch does not have to change a value. It can change a CONNECTION -- and one connection in
this network moves both quantities at once. Measured on the shipped ladder, the top rail's two
nodes differ by

    20log|V(M)/V(P)| = +6.26 dB @80 Hz .. +7.82 @1.6 kHz -- spread 1.67 dB, and IDENTICAL at
    RdampC5 = 0 / 5.5k / 30k, i.e. it does not care about the notch leg at all,

against a required h(boost) of +8.65 dB with a spread of 1.90 dB. A broadband, nearly-flat gain of
about the right size is already sitting in the drawn circuit, as the ratio between two points on the
divider.

⚠ THE ANSWER TO THE TITLE QUESTION IS NO, AND THIS PARAGRAPH USED TO SAY OTHERWISE. The idea was
that moving the tap also re-LOADS the rail, so one action would move the null as well and ATTACK
would be a 1-POLE switch. Measured, it does not: the tap moves h by 3.80 dB and f0 by 0.00 Hz, and a
fitted 1-pole tap leaves the null at 318.8 Hz in all three throws (spread 0.04 Hz against the
pedal's 17.58). The tap's load is C7 + R13 ~ 1 Mohm against a few hundred k of rail, far too light
to disturb the R7-vs-ladder cancellation up at node M. So session 61's "more than one pole" is
CONFIRMED, not superseded -- and the useful part is that this names the second pole and shows the
two sections do not interact (see the SENSITIVITY block, which separates all twelve elements into
gain-only, depth-only and frequency-carrying groups with no overlap).

THE TOPOLOGY UNDER TEST
-----------------------
The drawn R8 (M->P) is split into three, and the switch selects which node the output coupling cap
C7 hangs off. Nothing else changes; C8 is not needed and is omitted (a `--c8` mode keeps it).

    G --R7-- M --Ra-- T1 --Rb-- T2 --Rc-- T3 --R11-- GND         (top rail)
    G --[Rd+C5]-- L1 --C9-- L2 --C6-- M                          (the notch-forming ladder)
    L1 --R12-- GND ;  L2 --R14-- GND
    tap --C7-- Q ;  Q --R13-- GND                                 tap in {T1, T2, T3}

    boost -> T1 (highest = loudest) ;  flat -> T2 ;  cut -> T3 (lowest)

⭐ The throw ORDER is not fitted. `g(boost) > 0 > g(cut)` is measured, and a resistive tap can only
attenuate downward, so boost must be the highest tap. Ra = R8 with Rb = Rc = 0 collapses all three
taps onto node P and IS the drawn network -- the liveness and solver case.

The tool then adds the SECOND pole (`--sw`-style families in the fit table): the notch-forming C5
leg's damping Rd and the cap C5 itself, switched per throw. The final block holds the tap divider
and fits that section against the six notch numbers alone, so the two halves are each scored on
targets the other never saw.

WHY THIS IS A HARDER TEST THAN THE ELEMENT CENSUS
-------------------------------------------------
`attack_multipole_screen.py` fits a per-position element value and then lets a free flat scalar
absorb the broadband LEVEL, scoring only the SHAPE. Here there is no second section and no free
scalar: ONE parameter set, shared across all three positions, has to produce the measured h
including its median, at every bin. So the 6 notch numbers and all %d h bins are scored against a
handful of shared values -- a proposal can no longer buy the notch with gain it is not allowed.

GATES -- none optional
----------------------
  1 SOLVER     with Ra = Rb = 0 and Rc = R8 the tap network must reproduce
               `eq_reference.treble_attack_tf` (flat position) to ~1e-12 dB. A new topology whose
               degenerate case does not equal the old one is a re-derivation error, not a proposal.
  2 LIVENESS   Ra = Rb = 0 must make all three throws identical -- zero notch spread, zero h.
  3 SEARCH     recover a target the family DEFINITIONALLY can make.
  4 PATHOLOGY  a dead or wildly-rippling response can fake an arbitrarily deep null (session 57).

SCOPE
-----
  ATTACK is [ENG]; this proposes a topology, it does not disagree with a drawn one. Magnitude only.
  Notch depths are LOWER bounds (probe gate 1(b)), so a model DEEPER than measured is not an error --
  reported both ways, and the primary cost is the conservative symmetric one.

Usage:  python3.11 analysis/attack_tap_screen.py [--selftest] [--quick] [--json OUT]
"""
import argparse
import io
import json
import os
import sys
from contextlib import redirect_stdout

import numpy as np
from scipy.optimize import differential_evolution

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with redirect_stdout(io.StringIO()):
    import eq_reference as E                         # noqa: E402
    import attack_multipole_screen as M              # noqa: E402  (record loader, grids, floors)

POSITIONS, THROWS = M.POSITIONS, M.THROWS
SHIP, ZS, BIN_HZ = M.SHIP, M.ZS, M.BIN_HZ
FALL, ZSA, NSH, NBB, FBB = M.FALL, M.ZSA, M.NSH, M.NBB, M.FBB
REC = M.REC
TAP_OF = dict(boost=0, flat=1, cut=2)                # T1 / T2 / T3 -- measured, not fitted

# Free values, log10 multipliers on these anchors. Ra/Rb split the drawn R8; Rc keeps its remainder.
ANCHOR = dict(R7=200e3, Ra=470e3, Rb=100e3, Rc=270e3, R11=470e3, R12=6.8e3, R14=22e3,
              C5=22e-9, C9=22e-9, C6=22e-9, C7=680e-12, Rd=5.5e3)
FREE = ["Ra", "Rb", "Rc", "R11", "Rd"]               # the core proposal
FREE_WIDE = FREE + ["R7", "C5", "C6", "C9", "C7", "R12", "R14"]


def tf_tap(f, zs, tap, p, c8=0.0):
    """V(Q)/Vth with C7 hung off tap T1/T2/T3. Nodes [M, T1, T2, T3, L1, L2, Q, G]."""
    s = 2j * np.pi * np.asarray(f, dtype=float)
    n = len(s)
    yC5, yC9, yC6, yC7 = s * p["C5"], s * p["C9"], s * p["C6"], s * p["C7"]
    if p["Rd"] > 0.0:
        yC5 = yC5 / (1.0 + yC5 * p["Rd"])
    gS = 1.0 / np.broadcast_to(np.asarray(zs, dtype=complex), (n,))
    g7, ga, gb, gc = 1.0 / p["R7"], 1.0 / p["Ra"], 1.0 / p["Rb"], 1.0 / p["Rc"]
    g11, g12, g13, g14 = 1.0 / p["R11"], 1.0 / p["R12"], 1.0 / SHIP["R13"], 1.0 / p["R14"]
    Mn, T1, T2, T3, L1, L2, Q, G = range(8)
    A = np.zeros((n, 8, 8), dtype=complex)
    A[:, Mn, Mn] = g7 + ga + yC6; A[:, Mn, T1] = -ga; A[:, Mn, G] = -g7; A[:, Mn, L2] = -yC6
    A[:, T1, T1] = ga + gb; A[:, T1, Mn] = -ga; A[:, T1, T2] = -gb
    A[:, T2, T2] = gb + gc; A[:, T2, T1] = -gb; A[:, T2, T3] = -gc
    A[:, T3, T3] = gc + g11; A[:, T3, T2] = -gc
    A[:, L1, L1] = yC5 + yC9 + g12; A[:, L1, L2] = -yC9; A[:, L1, G] = -yC5
    A[:, L2, L2] = yC9 + yC6 + g14; A[:, L2, L1] = -yC9; A[:, L2, Mn] = -yC6
    A[:, Q, Q] = yC7 + g13; A[:, Q, 1 + tap] = -yC7
    A[:, 1 + tap, 1 + tap] += yC7; A[:, 1 + tap, Q] -= yC7
    A[:, G, G] = gS + g7 + yC5; A[:, G, Mn] = -g7; A[:, G, L1] = -yC5
    if c8 > 0.0:                                     # optional: keep the drawn C8 across Ra+Rb+Rc
        yc8 = s * c8
        A[:, Mn, Mn] += yc8; A[:, Mn, T3] -= yc8; A[:, T3, Mn] -= yc8; A[:, T3, T3] += yc8
    b = np.zeros((n, 8), dtype=complex)
    b[:, G] = gS
    return np.linalg.solve(A, b)[:, Q]


def stats(p, c8=0.0):
    mags = {}
    for pos in POSITIONS:
        m = M.db(tf_tap(FALL, ZSA, TAP_OF[pos], p, c8))
        if not np.all(np.isfinite(m)):
            return None
        mags[pos] = m
    flat = mags["flat"]
    if flat.max() < -80.0 or (flat.max() - flat.min()) > 60.0:      # GATE 4 PATHOLOGY
        return None
    out = {pos: M.notch_of(mags[pos]) for pos in POSITIONS}
    r = {p_: mags[p_][-NBB:] - flat[-NBB:] for p_ in THROWS}
    return dict(f0={k: out[k][0] for k in out}, depth={k: out[k][1] for k in out},
                r=r, resid={p_: REC["h"][p_] - r[p_] for p_ in THROWS})


def costs(st):
    """(notch, broadband ABSOLUTE) -- no free scalar: the topology must supply h's median too."""
    t = REC["tgt"]
    nr = [(st["f0"][p] - t["f0"][p]) / BIN_HZ for p in POSITIONS]
    nr += [(st["depth"][p] - t["depth"][p]) / 1.0 for p in POSITIONS]
    br = np.concatenate([st["resid"][p] for p in THROWS]) / REC["floor"]
    return float(np.sqrt(np.mean(np.square(nr)))), float(np.sqrt(np.mean(np.square(br))))


def build(x, free, sw=()):
    """`free` = values SHARED by all three throws; `sw` = values the FIRST pole switches per throw."""
    p = dict(ANCHOR)
    for k, xi in zip(free, x):
        p[k] = ANCHOR[k] * 10.0 ** xi
    per = {}
    k = len(free)
    for e in sw:
        per[e] = {pos: ANCHOR[e] * 10.0 ** x[k + i] for i, pos in enumerate(POSITIONS)}
        k += len(POSITIONS)
    return p, per


def stats_sw(p, per, c8=0.0):
    """Two-pole: the tap moves (pole 2) AND `per` element values change per throw (pole 1)."""
    if not per:
        return stats(p, c8)
    mags = {}
    for pos in POSITIONS:
        pp = dict(p, **{e: per[e][pos] for e in per})
        m = M.db(tf_tap(FALL, ZSA, TAP_OF[pos], pp, c8))
        if not np.all(np.isfinite(m)):
            return None
        mags[pos] = m
    flat = mags["flat"]
    if flat.max() < -80.0 or (flat.max() - flat.min()) > 60.0:
        return None
    out = {pos: M.notch_of(mags[pos]) for pos in POSITIONS}
    r = {q: mags[q][-NBB:] - flat[-NBB:] for q in THROWS}
    return dict(f0={k: out[k][0] for k in out}, depth={k: out[k][1] for k in out},
                r=r, resid={q: REC["h"][q] - r[q] for q in THROWS})


class Cost:
    def __init__(self, free, c8=0.0, target=None, sw=()):
        self.free, self.c8, self.target, self.sw = list(free), c8, target, tuple(sw)

    def __call__(self, x):
        p, per = build(x, self.free, self.sw)
        st = stats_sw(p, per, self.c8)
        if st is None:
            return 1e6
        if self.target is not None:
            v = np.array([st["f0"][p_] for p_ in POSITIONS] + [st["depth"][p_] for p_ in POSITIONS])
            return float(np.sqrt(np.mean(np.square((v - self.target)
                                                   / np.array([BIN_HZ] * 3 + [1.0] * 3)))))
        n, b = costs(st)
        return float(np.sqrt(0.5 * n * n + 0.5 * b * b))


def run(free, c8, width, quick, seed=13, sw=()):
    ndim = len(free) + len(POSITIONS) * len(sw)
    r = differential_evolution(Cost(free, c8, sw=sw), [(-width, width)] * ndim, seed=seed,
                               maxiter=90 if quick else 220, popsize=12 if quick else 20,
                               tol=1e-10, polish=True, init="sobol", workers=-1,
                               updating="deferred")
    p, per = build(r.x, free, sw)
    return r.fun, r.x, p, per, stats_sw(p, per, c8)


# =============================================================================================
def selftest(quick):
    print("=" * 104)
    print("GATES")
    print("=" * 104)
    ok = True

    print("  1 SOLVER -- Rb = Rc = 0, Ra = R8 (all three taps collapsed onto P) = the DRAWN network")
    f = np.geomspace(20.0, 16000.0, 41)
    zs = E.jfet_source_z(f, **ZS)
    # The degenerate case is Ra = R8 with Rb = Rc = 0, which puts ALL THREE taps on node P. Two
    # traps were live here and both fired on the first draft: (a) collapsing Ra and Rb instead
    # leaves T1 = T2 = M and T3 = P -- two taps on the WRONG node, which reads as a 6 dB solver
    # "failure" that is really a mis-stated degenerate case; and (b) 1e-12 ohm makes the
    # conductance 1e12 against a 2e-6 rail and the 8x8 solve loses every digit it has, so the gate
    # measures its own arithmetic. 1 milliohm separates the taps by ~1e-9 relative and stays
    # conditioned.
    base = dict(ANCHOR, Ra=SHIP["R8"], Rb=1e-3, Rc=1e-3, Rd=0.0)

    def ref(rd):
        return E.treble_attack_tf(f, "flat", Zs=zs,
                                  **dict(SHIP, C8=0.0, RdampC5=rd, C7=ANCHOR["C7"]))

    # (a) EXACT identity, no numerical shorts at all. Taking the output at T1 with Ra = R8 puts the
    # tap on node P, and the rail below it (Rb + Rc + R11) only has to SUM to the drawn R11 -- so
    # 100k + 100k + 270k reproduces the drawn divider exactly. This is the real derivation check;
    # a short-based one can only ever be as good as its own conditioning.
    worst = 0.0
    for rd in (0.0, 5.5e3, 30e3):
        p = dict(ANCHOR, Ra=SHIP["R8"], Rb=100e3, Rc=100e3, R11=SHIP["R11"] - 200e3, Rd=rd)
        worst = max(worst, float(np.max(np.abs(M.db(tf_tap(f, zs, 0, p)) - M.db(ref(rd))))))
    print("      exact identity (Ra = R8, Rb+Rc+R11 = R11, tap = T1): worst |d dB| = %.3e   %s"
          % (worst, "OK" if worst < 1e-9 else "FAIL -- the tap network is not a generalisation"))
    ok &= worst < 1e-9

    # (b) and the short used by the liveness case below is shown to BE a short, by scaling it: the
    # mismatch must grow in proportion. (Shrinking it does the opposite -- at 1e-5 ohm the 8x8
    # solve is conditioning-limited, which is how the first draft of this gate "failed".)
    print("      collapse-by-short, mismatch vs the drawn network (must grow WITH the short):")
    for short in (1e-3, 1e0, 1e3):
        p = dict(base, Rb=short, Rc=short)
        e = float(np.max(np.abs(M.db(tf_tap(f, zs, TAP_OF["flat"], p)) - M.db(ref(0.0)))))
        print("        %8.0e ohm -> %.3e dB" % (short, e))

    print("\n  2 LIVENESS -- collapsed taps must make all three throws identical")
    st = stats(base)
    fs = [st["f0"][p] for p in POSITIONS]
    ds = [st["depth"][p] for p in POSITIONS]
    rmax = max(float(np.max(np.abs(st["r"][p]))) for p in THROWS)
    dead = max(max(fs) - min(fs), max(ds) - min(ds), rmax)
    live = stats(dict(ANCHOR, Rd=0.0))
    mv = max(abs(live["f0"][p] - live["f0"]["flat"]) for p in THROWS)
    lg = max(abs(float(np.median(live["r"][p]))) for p in THROWS)
    print("      Ra = Rb = 0     : f0/depth/|h| spread %.2e            %s"
          % (dead, "OK" if dead < 1e-7 else "FAIL"))
    # ⚠ The GATE is only that the probe SEES the switch at all. Whether the tap can move the NOTCH
    # is the question being asked, not a precondition -- gating on it would convert a finding into
    # a tool failure (and the first draft of this gate did exactly that).
    print("      split rail      : moves h by %.2f dB                     %s"
          % (lg, "OK" if lg > 1.0 else "FAIL -- the probe cannot see this switch"))
    print("      ...and moves f0 by %.2f Hz  <-- REPORTED, NOT GATED: this is the finding" % mv)
    ok &= dead < 1e-7 and lg > 1.0

    print("\n  3 SEARCH -- recover a target the family DEFINITIONALLY can make")
    rng = np.random.default_rng(23)
    made, worst_rec = 0, 0.0
    while made < (2 if quick else 3):
        x0 = rng.uniform(-0.8, 0.8, len(FREE))
        st = stats(build(x0, FREE)[0])
        if st is None:
            continue
        sh = [st["f0"][p] - st["f0"]["flat"] for p in THROWS]
        if max(abs(v) for v in sh) < 3.0:
            continue
        if any(not (M.SEARCH_WIN[0] + 3.0 < st["f0"][p] < M.SEARCH_WIN[1] - 3.0) for p in POSITIONS):
            continue
        made += 1
        t = np.array([st["f0"][p] for p in POSITIONS] + [st["depth"][p] for p in POSITIONS])
        r = differential_evolution(Cost(FREE, 0.0, target=t), [(-2.0, 2.0)] * len(FREE),
                                   seed=400 + made, maxiter=90 if quick else 200,
                                   popsize=12 if quick else 18, tol=1e-10, polish=True,
                                   init="sobol", workers=-1, updating="deferred")
        print("      target %d (shifts %+6.1f / %+6.1f Hz): recovered to %.5f" % (made, sh[0], sh[1], r.fun))
        worst_rec = max(worst_rec, r.fun)
    print("      worst recovery %.5f   %s" % (worst_rec, "GATE PASSES" if worst_rec < 1.0 else "GATE FAILS"))
    ok &= worst_rec < 1.0
    print("\n  %s" % ("GATES PASS" if ok else "GATES FAIL"))
    return ok


def report(tag, p, st, free, per=None):
    t = REC["tgt"]
    n, b = costs(st)
    print("\n  %s -- notch %.2f | broadband %.2f | joint %.2f"
          % (tag, n, b, np.sqrt(0.5 * n * n + 0.5 * b * b)))
    print("  %-7s %-24s %-24s %-16s" % ("pos", "f0 Hz model / pedal", "depth dB model / pedal",
                                        "h median mdl/ped"))
    for pos in POSITIONS:
        hm = "%+7.2f / %-7.2f" % (float(np.median(st["r"][pos])),
                                  float(np.median(REC["h"][pos]))) if pos in THROWS else "  (reference)"
        print("  %-7s %9.1f / %-12.1f %9.2f / %-12.2f %s"
              % (pos, st["f0"][pos], t["f0"][pos], st["depth"][pos], t["depth"][pos], hm))
    fs = [st["f0"][q] for q in POSITIONS]
    print("  f0 spread across the three throws: %.2f Hz (pedal %.2f Hz)"
          % (max(fs) - min(fs), max(t["f0"].values()) - min(t["f0"].values())))
    print("  values: " + ", ".join("%s = %s" % (k, M.fmt(p[k])) for k in free))
    if per:
        for e, d in per.items():
            print("  switched %s: %s" % (e, " / ".join("%s %s" % (q, M.fmt(d[q])) for q in POSITIONS)))
    print("  h residual (pedal - model), the part no value in this family removed:")
    print("  %9s %10s %10s" % ("f Hz", "boost", "cut"))
    for target in (80.0, 128.0, 200.0, 254.0, 404.0, 640.0, 810.0, 1014.0, 1600.0):
        i = int(np.argmin(np.abs(FBB - target)))
        print("  %9.1f %+10.2f %+10.2f" % (FBB[i], st["resid"]["boost"][i], st["resid"]["cut"][i]))
    for pos in THROWS:
        s = st["resid"][pos]
        print("  %-6s rms %.2f dB, peak %+.2f dB (floor %.3f)"
              % (pos, float(np.sqrt(np.mean(s ** 2))), float(s[np.argmax(np.abs(s))]), REC["floor"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    t = REC["tgt"]
    print("=" * 104)
    print("CAN ONE POLE DO BOTH JOBS? -- ATTACK as a MOVING TAP on the R7/R8 divider")
    print("=" * 104)
    print("  target read from %s (measured, never transcribed)" % M.MEASURED)
    print("  notch  cut %.1f/%.1f | boost %.1f/%.1f | flat %.1f/%.1f Hz/dB"
          % (t["f0"]["cut"], t["depth"]["cut"], t["f0"]["boost"], t["depth"]["boost"],
             t["f0"]["flat"], t["depth"]["flat"]))
    print("  h      boost %+0.2f dB | cut %+0.2f dB, scored ABSOLUTELY over %d bins each -- there is"
          % (float(np.median(REC["h"]["boost"])), float(np.median(REC["h"]["cut"])), NBB))
    print("         no free scalar in this family, so the topology must supply the median too")

    if args.selftest and not selftest(args.quick):
        sys.exit(1)

    print("\n" + "=" * 104)
    print("THE FIT")
    print("=" * 104)
    print("  NULL CONTROL first: what a topology that does NOTHING scores, so the fit has a")
    print("  yardstick. (h against zero -- the switch inert.)")
    null_b = float(np.sqrt(np.mean(np.square(
        np.concatenate([REC["h"][p] for p in THROWS]) / REC["floor"]))))
    print("    inert switch: broadband cost %.2f  (%.2f dB rms)" % (null_b, null_b * REC["floor"]))

    print("\n  ⚠ Ra sits ABOVE all three taps, so it scales every position equally and cancels out")
    print("    of h -- which is a RATIO between positions. It is therefore unidentifiable by this")
    print("    measurement BY CONSTRUCTION, and the first runs duly parked it on whichever bound")
    print("    they started nearest (100 ohm and 10 Mohm scored the same). PINNED to the drawn R8")
    print("    below; only the tap divider's RATIOS are claimed. Same for any shared element.")

    out = {}
    runs = [("1-pole tap, Ra pinned", ["Rb", "Rc", "R11"], (), 2.0),
            ("1-pole tap, + notch leg shared", ["Rb", "Rc", "R11", "Rd", "C5"], (), 2.0),
            ("2-POLE: tap + switched Rd", ["Rb", "Rc", "R11"], ("Rd",), 2.0),
            ("2-POLE: tap + switched Rd,C5", ["Rb", "Rc", "R11"], ("Rd", "C5"), 2.0)]
    for tag, free, sw, width in runs:
        f, x, p, per, st = run(free, 0.0, width, args.quick, sw=sw)
        if st is None:
            print("\n  %s -- pathological" % tag)
            continue
        names = list(free) + ["%s[%s]" % (e, q) for e in sw for q in POSITIONS]
        rest = [k for k, xi in zip(names, x) if abs(abs(xi) - width) < 0.02]
        report(tag, p, st, free, per)
        print("  %s" % ("nothing on a bound" if not rest
                        else "ON A BOUND (unidentified): " + ", ".join(rest)))
        n, b = costs(st)
        out[tag] = dict(notch=n, bb=b, joint=f, values={k: p[k] for k in free},
                        switched={e: per[e] for e in per}, f0=st["f0"], depth=st["depth"],
                        h_median={q: float(np.median(st["r"][q])) for q in THROWS})

    print("\n" + "=" * 104)
    print("VERDICT")
    print("=" * 104)
    print("  %-34s %7s %7s %9s   %s" % ("family", "notch", "bb", "bb dB rms", "f0 spread Hz"))
    for k, v in out.items():
        fs = list(v["f0"].values())
        print("  %-34s %7.2f %7.2f %9.2f   %.2f" % (k, v["notch"], v["bb"],
                                                    v["bb"] * REC["floor"], max(fs) - min(fs)))
    print("  %-34s %7s %7s %9.2f   %.2f" % ("INERT SWITCH (control)", "-", "%.2f" % null_b,
                                            null_b * REC["floor"], 0.0))
    print("  %-34s %7s %7s %9s   %.2f" % ("PEDAL", "0.00", "0.00", "0.00",
                                          max(REC["tgt"]["f0"].values()) - min(REC["tgt"]["f0"].values())))
    best = min(out.items(), key=lambda kv: kv[1]["joint"]) if out else None
    if best:
        k, v = best
        print("\n  best joint: %s -- h median boost %+.2f (pedal %+.2f) | cut %+.2f (pedal %+.2f)"
              % (k, v["h_median"]["boost"], float(np.median(REC["h"]["boost"])),
                 v["h_median"]["cut"], float(np.median(REC["h"]["cut"]))))

    # ---------------------------------------------------------------- what a THIRD section needs
    print("\n" + "=" * 104)
    print("SENSITIVITY -- if f0 is the requirement still unmet, WHICH element could a section move?")
    print("=" * 104)
    print("  Perturb each element +-20%% about the fitted 2-pole point and read how far it moves")
    print("  each of the three requirements. The wanted element moves f0 and NOT the other two --")
    print("  the tap already owns the broadband gain and Rd already owns the depth, so anything")
    print("  that drags those has to be undone elsewhere and is not a third section, it is a refit.")
    ref = out.get("2-POLE: tap + switched Rd")
    if ref:
        base = dict(ANCHOR, **{k: v for k, v in ref["values"].items()})
        base["Rd"] = ref["switched"]["Rd"]["flat"]
        s0 = stats(base)
        print("\n  %-8s %11s %11s %11s   %s"
              % ("element", "d f0 Hz", "d depth dB", "d h med dB", "verdict"))
        rows = []
        for e in ("R7", "Ra", "Rb", "Rc", "R11", "R12", "R14", "C5", "C6", "C9", "C7", "Rd"):
            d = []
            for k_ in (0.8, 1.25):
                s = stats(dict(base, **{e: base[e] * k_}))
                if s is None:
                    d = None
                    break
                d.append((s["f0"]["flat"] - s0["f0"]["flat"], s["depth"]["flat"] - s0["depth"]["flat"],
                          float(np.median(s["r"]["boost"])) - float(np.median(s0["r"]["boost"]))))
            if d is None:
                continue
            df = max(abs(v_[0]) for v_ in d)
            dd = max(abs(v_[1]) for v_ in d)
            dh = max(abs(v_[2]) for v_ in d)
            rows.append((e, df, dd, dh))
        for e, df, dd, dh in sorted(rows, key=lambda r_: -r_[1] / (1.0 + r_[2] + r_[3])):
            sel = "moves f0 CLEANLY" if df > 3.0 and dd < 1.0 and dh < 0.3 else (
                "f0 only via depth" if df > 3.0 and dh < 0.3 else
                ("drags the broadband gain" if dh >= 0.3 else "no f0 authority"))
            print("  %-8s %11.2f %11.2f %11.2f   %s" % (e, df, dd, dh, sel))
        print("\n  required: f0 must span %.1f Hz across the three throws while depth spans"
              % (max(REC["tgt"]["f0"].values()) - min(REC["tgt"]["f0"].values())))
        print("  %.1f dB and the broadband medians stay at +8.65 / -2.39 dB."
              % (max(REC["tgt"]["depth"].values()) - min(REC["tgt"]["depth"].values())))

        # ⭐ The joint fit above weighs f0 against depth against 216 h bins, so a shortfall in f0
        # could be the WEIGHTING rather than the topology. Settle it: hold the tap divider at its
        # fitted values (it is broadband-only, sensitivity 0.01-0.02 Hz, so it cannot help or hurt
        # here) and aim a notch-section fit at the SIX notch numbers alone. If that reaches them,
        # the shortfall was arbitration; if it cannot, it is structural.
        print("\n" + "=" * 104)
        print("IS THE f0 SHORTFALL STRUCTURAL, OR JUST THE JOINT FIT'S ARBITRATION?")
        print("=" * 104)
        print("  tap divider HELD at the 2-pole values; the notch section fitted to the 6 notch")
        print("  numbers ONLY. The broadband is then re-read as a CHECK, not a term.\n")
        tgt6 = np.array([REC["tgt"]["f0"][q] for q in POSITIONS]
                        + [REC["tgt"]["depth"][q] for q in POSITIONS])
        held = ["Rb", "Rc", "R11"]
        for sw in (("Rd",), ("Rd", "C5"), ("Rd", "C5", "R12")):
            free = []                                  # nothing shared is free: the tap is HELD
            nd = len(POSITIONS) * len(sw)
            saved = {k: ANCHOR[k] for k in held}
            ANCHOR.update({k: ref["values"][k] for k in held})
            try:
                r = differential_evolution(Cost(free, 0.0, target=tgt6, sw=sw),
                                           [(-2.0, 2.0)] * nd, seed=31,
                                           maxiter=90 if args.quick else 260,
                                           popsize=12 if args.quick else 22, tol=1e-11,
                                           polish=True, init="sobol", workers=-1,
                                           updating="deferred")
                p2, per2 = build(r.x, free, sw)
                st2 = stats_sw(p2, per2, 0.0)
            finally:
                ANCHOR.update(saved)
            if st2 is None:
                continue
            fs = [st2["f0"][q] for q in POSITIONS]
            _, bb2 = costs(st2)
            print("  switch %-14s notch cost %6.3f | f0 %6.1f/%6.1f/%6.1f (pedal %.1f/%.1f/%.1f)"
                  % ("+".join(sw), r.fun, st2["f0"]["cut"], st2["f0"]["boost"], st2["f0"]["flat"],
                     REC["tgt"]["f0"]["cut"], REC["tgt"]["f0"]["boost"], REC["tgt"]["f0"]["flat"]))
            print("  %-21s depth %6.2f/%6.2f/%6.2f (pedal %.2f/%.2f/%.2f) | spread %.1f Hz"
                  % ("", st2["depth"]["cut"], st2["depth"]["boost"], st2["depth"]["flat"],
                     REC["tgt"]["depth"]["cut"], REC["tgt"]["depth"]["boost"],
                     REC["tgt"]["depth"]["flat"], max(fs) - min(fs)))
            print("  %-21s broadband CHECK (not fitted): %.2f dB rms | h med boost %+.2f cut %+.2f"
                  % ("", bb2 * REC["floor"], float(np.median(st2["r"]["boost"])),
                     float(np.median(st2["r"]["cut"]))))
            for e in sw:
                print("  %-21s %s = %s" % ("", e, " / ".join("%s %s" % (q, M.fmt(per2[e][q]))
                                                             for q in POSITIONS)))
    if args.json:
        os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
        json.dump(dict(null_bb=null_b, fits=out), open(args.json, "w"), indent=1, default=float)
        print("\n  wrote %s" % args.json)


if __name__ == "__main__":
    main()
