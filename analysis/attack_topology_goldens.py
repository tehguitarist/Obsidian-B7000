#!/usr/bin/env python3.11
"""Golden values for TrebleAttackTest Test 8 -- the TWO-POLE ATTACK topology, cross-checked
against the UNCOLLAPSED 8-node solve (session 63, Phase 9 / A3 step 20).

WHY THIS EXISTS
---------------
src/dsp/TrebleAttack.h realises session 62's two-pole ATTACK proposal WITHOUT adding nodes, by
collapsing the split top rail per throw:

    G -R7- M -Ra- T1 -Rb- T2 -Rc- T3 -R11- GND,  C7 hung off the SELECTED tap

    ==>  M -Rtop- P -Rbot- GND   with P = that tap, because T1/T2/T3 are otherwise BARE
         interior points of one series chain and series resistors with no loaded intermediate
         node combine exactly:
             boost (T1): Rtop = Ra            Rbot = Rb + Rc + R11
             flat  (T2): Rtop = Ra + Rb       Rbot = Rc + R11
             cut   (T3): Rtop = Ra + Rb + Rc  Rbot = R11

That collapse is the one piece of NEW algebra in the C++ stage, so it is the thing a golden table
copied out of the same derivation could not catch. This script therefore checks it against a
genuinely independent implementation -- `attack_tap_screen.tf_tap`, which solves the uncollapsed
8-node network directly and was written for a different purpose (session 62's screen) -- and only
then emits the C++ table.

⚠ It is NOT enough to check the collapse at the DEFAULT values: there Ra = R8 and Rb = Rc = 0, so
all three taps sit on one node and every throw is the drawn network. The identity has to be checked
where the taps are genuinely SPLIT, which is what the proposal point below does (Rb = 506k,
Rc = 78.5k are both large).

⚠ C8 is at 0 here, matching what session 62 actually screened. Where C8 IS in circuit the two
implementations DISAGREE BY CONSTRUCTION and that is not a bug: the C++ stage hangs it off the
selected tap (faithful to the drawn circuit, where C8's top plate and C7 share node P), while
attack_tap_screen's optional `--c8` mode spans M<->T3, the whole rail. The proposal used neither, so
the two never had to be reconciled -- but do not "fix" one to match the other without deciding which
is the physical claim.

Usage:  python3.11 analysis/attack_topology_goldens.py
"""
import io
import os
import sys
from contextlib import redirect_stdout

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with redirect_stdout(io.StringIO()):
    import eq_reference as E
    import attack_tap_screen as T

# ---- session 62's proposed point (docs/phase9-validation.md §4 "A3 step 19" §1) -------------
# Realised as FitParams: trebleC5 = the base cap, attackC5Trim* = additive parallel trims.
PROP = dict(Ra=470.0e3, Rb=506.0e3, Rc=78.5e3, R11=212.0e3,
            C5base=19.7e-9, C5trimBoost=1.1e-9, C5trimCut=2.7e-9,
            RdFlat=6.14e3, RdBoost=478.0, RdCut=6.04e3)
C8 = 0.0

# NOMINAL J201 boundary -- TrebleAttackTest constructs the stage directly, with no FitParams, so
# it runs JfetStage's nominal gm. (attack_*_screen.py use the SHIPPED gm = 0.10 mS instead; using
# that here would make the golden table disagree with the C++ stage for a reason unrelated to the
# topology.)
ZSKW = dict(gm=0.69e-3, ro=200.0e3, Rq2=1.0e6)
FREQS = [50.0, 100.0, 200.0, 320.0, 500.0, 1000.0, 2000.0]
POS = ["boost", "flat", "cut"]
TAP_IDX = dict(boost=0, flat=1, cut=2)


def rail(pos):
    """The per-throw series collapse -- the identity under test."""
    ra, rb, rc, r11 = PROP["Ra"], PROP["Rb"], PROP["Rc"], PROP["R11"]
    return {"boost": (ra, rb + rc + r11),
            "flat": (ra + rb, rc + r11),
            "cut": (ra + rb + rc, r11)}[pos]


def leg(pos):
    """Pole B per throw: (C5, Rd)."""
    return {"boost": (PROP["C5base"] + PROP["C5trimBoost"], PROP["RdBoost"]),
            "flat": (PROP["C5base"], PROP["RdFlat"]),
            "cut": (PROP["C5base"] + PROP["C5trimCut"], PROP["RdCut"])}[pos]


def main():
    f = np.array(FREQS, dtype=float)
    zs = E.jfet_source_z(f, **ZSKW)

    print("=" * 96)
    print("GATE -- the series collapse vs the UNCOLLAPSED 8-node solve (attack_tap_screen.tf_tap)")
    print("=" * 96)
    print("  at the SPLIT proposal point (Rb = 506k, Rc = 78.5k), C8 = 0")
    print("  %-6s %10s %14s %14s %12s" % ("pos", "Rtop k", "Rbot k", "worst |d dB|", "verdict"))
    worst_all = 0.0
    collapsed = {}
    for pos in POS:
        rtop, rbot = rail(pos)
        c5, rd = leg(pos)
        # (a) COLLAPSED: the two-resistor rail, through the shared analytic oracle. This is what
        #     the C++ stage builds -- R8 := Rtop, R11 := Rbot.
        col = zs * E.treble_attack_tf(f, pos, Zs=zs, R8=rtop, R11=rbot, C5=c5, RdampC5=rd,
                                      C7=T.ANCHOR["C7"], C8=C8)
        # (b) UNCOLLAPSED: the 8-node split rail, an independent implementation.
        p = dict(T.ANCHOR, Ra=PROP["Ra"], Rb=PROP["Rb"], Rc=PROP["Rc"], R11=PROP["R11"],
                 C5=c5, Rd=rd)
        unc = zs * T.tf_tap(f, zs, TAP_IDX[pos], p, c8=C8)
        d = float(np.max(np.abs(20.0 * np.log10(np.abs(col)) - 20.0 * np.log10(np.abs(unc)))))
        worst_all = max(worst_all, d)
        print("  %-6s %10.1f %14.1f %14.3e %12s"
              % (pos, rtop / 1e3, rbot / 1e3, d, "OK" if d < 1e-9 else "FAIL"))
        collapsed[pos] = 20.0 * np.log10(np.abs(col))
    ok = worst_all < 1e-9
    print("  worst over all three throws: %.3e dB  -- %s"
          % (worst_all, "GATE PASSES: the collapse is exact"
             if ok else "GATE FAILS: the collapse is NOT the same network"))

    # A control: if the collapse were wrong in a way that only shows when the taps are split, the
    # DEFAULT point would still pass. Show that it does, so the gate above is known to be the
    # informative one rather than the easy one.
    print("\n  CONTROL -- the same check at the DEFAULT (collapsed) point, where every throw is")
    print("  the drawn network. This passes even for a WRONG collapse, which is why it is not the")
    print("  gate: it is here only to show the gate above is the harder case.")
    dflt = 0.0
    for pos in POS:
        col = zs * E.treble_attack_tf(f, pos, Zs=zs, C7=T.ANCHOR["C7"], C8=C8)
        p = dict(T.ANCHOR, Ra=470.0e3, Rb=1e-3, Rc=1e-3, R11=470.0e3, Rd=0.0)
        unc = zs * T.tf_tap(f, zs, TAP_IDX[pos], p, c8=C8)
        dflt = max(dflt, float(np.max(np.abs(20 * np.log10(np.abs(col))
                                            - 20 * np.log10(np.abs(unc))))))
    print("      worst |d dB| = %.3e  (a numerical short, so ~1e-7 not ~1e-15 -- session 62)" % dflt)

    # ---- the table the C++ test asserts against --------------------------------------------
    print("\n" + "=" * 96)
    print("GOLDEN TABLE for tests/TrebleAttackTest.cpp Test 8 (dB re 1 ohm, transimpedance)")
    print("=" * 96)
    print("static const std::vector<Ref> kRefTwoPole = {")
    print("    //  f Hz     boost       flat        cut")
    for i, fi in enumerate(FREQS):
        print("    { %8.1f, %9.4f, %9.4f, %9.4f }," %
              (fi, collapsed["boost"][i], collapsed["flat"][i], collapsed["cut"][i]))
    print("};")

    print("\n  broadband h implied by this point (model, re flat):")
    for i, fi in enumerate(FREQS):
        print("    %7.1f Hz   boost %+7.2f dB   cut %+7.2f dB"
              % (fi, collapsed["boost"][i] - collapsed["flat"][i],
                 collapsed["cut"][i] - collapsed["flat"][i]))
    print("  (the pedal's measured medians are boost +8.65 / cut -2.39 dB; the 320 Hz row sits ON")
    print("   the notch and is NOT a broadband number -- session 60 item 9)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
